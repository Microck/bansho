package policy

import (
	"fmt"
	"strings"
)

// ToolWildcard is the wildcard pattern that allows access to all tools.
const ToolWildcard = "*"

// RoleToolPolicy defines which tools a role is allowed to invoke.
type RoleToolPolicy struct {
	Allow []string `yaml:"allow"`
}

// Allows reports whether the given tool name is permitted by this role policy.
func (p RoleToolPolicy) Allows(toolName string) bool {
	n := strings.TrimSpace(toolName)
	if n == "" {
		return false
	}
	for _, allowed := range p.Allow {
		if allowed == ToolWildcard {
			return true
		}
		if allowed == n {
			return true
		}
	}
	return false
}

// Normalize deduplicates and validates the tool allow list.
func (p *RoleToolPolicy) Normalize() error {
	var out []string
	for _, raw := range p.Allow {
		name := strings.TrimSpace(raw)
		if name == "" {
			return fmt.Errorf("tool names in role allow lists must be non-empty")
		}
		if name == ToolWildcard {
			p.Allow = []string{ToolWildcard}
			return nil
		}
		seen := false
		for _, existing := range out {
			if existing == name {
				seen = true
				break
			}
		}
		if !seen {
			out = append(out, name)
		}
	}
	p.Allow = out
	return nil
}

// RolesPolicy holds tool-access policies for the admin, user, and readonly roles.
type RolesPolicy struct {
	Admin    RoleToolPolicy `yaml:"admin"`
	User     RoleToolPolicy `yaml:"user"`
	Readonly RoleToolPolicy `yaml:"readonly"`
}

// Defaults populates nil allow lists with their zero-value defaults.
func (p *RolesPolicy) Defaults() {
	if p.Admin.Allow == nil {
		p.Admin.Allow = []string{ToolWildcard}
	}
	if p.User.Allow == nil {
		p.User.Allow = []string{}
	}
	if p.Readonly.Allow == nil {
		p.Readonly.Allow = []string{}
	}
}

// Normalize validates and normalizes all role tool policies.
func (p *RolesPolicy) Normalize() error {
	p.Defaults()
	if err := p.Admin.Normalize(); err != nil {
		return err
	}
	if err := p.User.Normalize(); err != nil {
		return err
	}
	if err := p.Readonly.Normalize(); err != nil {
		return err
	}
	return nil
}

// ForRole returns the RoleToolPolicy for the named role, or nil if unknown.
func (p *RolesPolicy) ForRole(role string) *RoleToolPolicy {
	switch strings.ToLower(strings.TrimSpace(role)) {
	case "admin":
		return &p.Admin
	case "user":
		return &p.User
	case "readonly":
		return &p.Readonly
	default:
		return nil
	}
}

// RateLimitWindow defines a fixed-window rate limit with request count and duration.
type RateLimitWindow struct {
	Requests      int `yaml:"requests"`
	WindowSeconds int `yaml:"window_seconds"`
}

// Defaults sets zero-valued fields to the provided fallbacks.
func (w *RateLimitWindow) Defaults(requests int, windowSeconds int) {
	if w.Requests == 0 {
		w.Requests = requests
	}
	if w.WindowSeconds == 0 {
		w.WindowSeconds = windowSeconds
	}
}

// Validate ensures the rate limit window values are positive.
func (w *RateLimitWindow) Validate() error {
	if w.Requests <= 0 {
		return fmt.Errorf("requests must be > 0")
	}
	if w.WindowSeconds <= 0 {
		return fmt.Errorf("window_seconds must be > 0")
	}
	return nil
}

// ToolRateLimitPolicy configures per-tool rate limits with a default and optional overrides.
type ToolRateLimitPolicy struct {
	Default   RateLimitWindow            `yaml:"default"`
	Overrides map[string]RateLimitWindow `yaml:"overrides"`
}

// Defaults populates zero-valued fields with sensible defaults for tool rate limits.
func (p *ToolRateLimitPolicy) Defaults() {
	p.Default.Defaults(30, 60)
	if p.Overrides == nil {
		p.Overrides = map[string]RateLimitWindow{}
	}
}

// Normalize validates and normalizes default and override tool rate limits.
func (p *ToolRateLimitPolicy) Normalize() error {
	p.Defaults()
	if err := p.Default.Validate(); err != nil {
		return fmt.Errorf("per_tool.default: %w", err)
	}

	normalized := make(map[string]RateLimitWindow, len(p.Overrides))
	for k, v := range p.Overrides {
		name := strings.TrimSpace(k)
		if name == "" {
			return fmt.Errorf("tool override names must be non-empty")
		}
		v2 := v
		v2.Defaults(p.Default.Requests, p.Default.WindowSeconds)
		if err := v2.Validate(); err != nil {
			return fmt.Errorf("per_tool.overrides.%s: %w", name, err)
		}
		normalized[name] = v2
	}
	p.Overrides = normalized
	return nil
}

// ForTool returns the rate limit window for the given tool, falling back to the default.
func (p *ToolRateLimitPolicy) ForTool(toolName string) RateLimitWindow {
	n := strings.TrimSpace(toolName)
	if n == "" {
		return p.Default
	}
	if v, ok := p.Overrides[n]; ok {
		return v
	}
	return p.Default
}

// RateLimitsPolicy groups per-API-key and per-tool rate limit configuration.
type RateLimitsPolicy struct {
	PerAPIKey RateLimitWindow     `yaml:"per_api_key"`
	PerTool   ToolRateLimitPolicy `yaml:"per_tool"`
}

// Defaults sets zero-valued rate limit fields to their default values.
func (p *RateLimitsPolicy) Defaults() {
	p.PerAPIKey.Defaults(120, 60)
	p.PerTool.Defaults()
}

// Normalize validates all rate limit settings.
func (p *RateLimitsPolicy) Normalize() error {
	p.Defaults()
	if err := p.PerAPIKey.Validate(); err != nil {
		return fmt.Errorf("per_api_key: %w", err)
	}
	if err := p.PerTool.Normalize(); err != nil {
		return err
	}
	return nil
}

// Policy is the top-level configuration for role-based access control and rate limiting.
type Policy struct {
	Roles      RolesPolicy      `yaml:"roles"`
	RateLimits RateLimitsPolicy `yaml:"rate_limits"`
}

// Defaults initializes nil sub-policies with their default values.
func (p *Policy) Defaults() {
	p.Roles.Defaults()
	p.RateLimits.Defaults()
}

// Normalize validates the entire policy and enforces constraints such as wildcard-only-for-admin.
func (p *Policy) Normalize() error {
	p.Defaults()
	if err := p.Roles.Normalize(); err != nil {
		return err
	}
	if err := p.RateLimits.Normalize(); err != nil {
		return err
	}
	// Enforce wildcard only for admin role.
	if containsWildcard(p.Roles.User.Allow) || containsWildcard(p.Roles.Readonly.Allow) {
		return fmt.Errorf("tool wildcard '*' is only allowed for admin role")
	}
	return nil
}

// IsToolAllowed checks whether the given role is permitted to use the named tool.
func (p Policy) IsToolAllowed(role string, toolName string) bool {
	rolePolicy := p.Roles.ForRole(role)
	if rolePolicy == nil {
		return false
	}
	return rolePolicy.Allows(toolName)
}

func containsWildcard(values []string) bool {
	for _, v := range values {
		if v == ToolWildcard {
			return true
		}
	}
	return false
}
