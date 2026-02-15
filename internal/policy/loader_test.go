package policy

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestLoadPolicyDemoFile(t *testing.T) {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		t.Fatalf("runtime.Caller failed")
	}
	candidate := filepath.Dir(file)
	repoRoot := ""
	for i := 0; i < 8; i++ {
		candidatePath := filepath.Join(candidate, "demo", "policies_demo.yaml")
		if _, err := os.Stat(candidatePath); err == nil {
			repoRoot = candidate
			break
		}
		parent := filepath.Dir(candidate)
		if parent == candidate {
			break
		}
		candidate = parent
	}
	if repoRoot == "" {
		t.Fatalf("could not locate demo/policies_demo.yaml")
	}
	path := filepath.Join(repoRoot, "demo", "policies_demo.yaml")

	p, err := LoadPolicy(path)
	if err != nil {
		t.Fatalf("LoadPolicy: %v", err)
	}

	if !p.IsToolAllowed("readonly", "list_customers") {
		t.Fatalf("expected readonly to allow list_customers")
	}
	if p.IsToolAllowed("readonly", "delete_customer") {
		t.Fatalf("expected readonly to deny delete_customer")
	}

	if p.RateLimits.PerAPIKey.Requests <= 0 || p.RateLimits.PerAPIKey.WindowSeconds <= 0 {
		t.Fatalf("expected per_api_key rate limits")
	}
	window := p.RateLimits.PerTool.ForTool("list_customers")
	if window.Requests != 1 {
		t.Fatalf("expected list_customers requests=1 override, got %d", window.Requests)
	}
}
