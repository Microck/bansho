package auth

import (
	"strings"
	"testing"
)

func TestHashAndVerifyAPIKey(t *testing.T) {
	key, err := GenerateAPIKey(APIKeyPrefix)
	if err != nil {
		t.Fatalf("GenerateAPIKey: %v", err)
	}

	h, err := HashAPIKey(key, PBKDF2Iterations)
	if err != nil {
		t.Fatalf("HashAPIKey: %v", err)
	}
	if !strings.HasPrefix(h, PBKDF2Scheme+"$") {
		t.Fatalf("expected hash scheme prefix, got %q", h)
	}
	if !VerifyAPIKey(key, h) {
		t.Fatalf("expected VerifyAPIKey to succeed")
	}
	if VerifyAPIKey(key+"x", h) {
		t.Fatalf("expected VerifyAPIKey to fail for wrong key")
	}
}
