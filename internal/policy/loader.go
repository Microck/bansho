package policy

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

const DefaultPolicyPath = "config/policies.yaml"

type LoadError struct {
	Path string
	Err  error
}

func (e *LoadError) Error() string {
	if e.Err == nil {
		return fmt.Sprintf("policy load failed: %s", e.Path)
	}
	return fmt.Sprintf("policy load failed: %s: %v", e.Path, e.Err)
}

func (e *LoadError) Unwrap() error {
	return e.Err
}

func LoadPolicy(path string) (Policy, error) {
	resolved := path
	if resolved == "" {
		resolved = DefaultPolicyPath
	}
	resolved = filepath.Clean(resolved)

	raw, err := os.ReadFile(resolved)
	if err != nil {
		return Policy{}, &LoadError{Path: resolved, Err: err}
	}

	var p Policy
	if err := yaml.Unmarshal(raw, &p); err != nil {
		return Policy{}, &LoadError{Path: resolved, Err: err}
	}
	if err := p.Normalize(); err != nil {
		return Policy{}, &LoadError{Path: resolved, Err: err}
	}

	return p, nil
}
