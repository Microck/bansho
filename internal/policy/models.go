package policy

import (
	"fmt"
	"strings"
)

const ToolWildcard = "*"

type RoleToolPolicy struct {
	Allow []string `yaml:"allow"`
}

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

type RolesPolicy struct {
	Admin    RoleToolPolicy `yaml:"admin"`
	User     RoleToolPolicy `yaml:"user"`
	Readonly RoleToolPolicy `yaml:"readonly"`
}

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

type RateLimitWindow struct {
	Requests      int `yaml:"requests"`
	WindowSeconds int `yaml:"window_seconds"`
}

func (w *RateLimitWindow) Defaults(requests int, windowSeconds int) {
	if w.Requests == 0 {
		w.Requests = requests
	}
	if w.WindowSeconds == 0 {
		w.WindowSeconds = windowSeconds
	}
}

func (w *RateLimitWindow) Validate() error {
	if w.Requests <= 0 {
		return fmt.Errorf("requests must be > 0")
	}
	if w.WindowSeconds <= 0 {
		return fmt.Errorf("window_seconds must be > 0")
	}
	return nil
}

type ToolRateLimitPolicy struct {
	Default   RateLimitWindow            `yaml:"default"`
	Overrides map[string]RateLimitWindow `yaml:"overrides"`
}

func (p *ToolRateLimitPolicy) Defaults() {
	p.Default.Defaults(30, 60)
	if p.Overrides == nil {
		p.Overrides = map[string]RateLimitWindow{}
	}
}

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

type RateLimitsPolicy struct {
	PerAPIKey RateLimitWindow     `yaml:"per_api_key"`
	PerTool   ToolRateLimitPolicy `yaml:"per_tool"`
}

func (p *RateLimitsPolicy) Defaults() {
	p.PerAPIKey.Defaults(120, 60)
	p.PerTool.Defaults()
}

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

type Policy struct {
	Roles      RolesPolicy      `yaml:"roles"`
	RateLimits RateLimitsPolicy `yaml:"rate_limits"`
}

func (p *Policy) Defaults() {
	p.Roles.Defaults()
	p.RateLimits.Defaults()
}

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
