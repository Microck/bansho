package auth

import (
	"crypto/hmac"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"strconv"
	"strings"

	"golang.org/x/crypto/pbkdf2"
)

const (
	PBKDF2Scheme     = "pbkdf2_sha256"
	PBKDF2Iterations = 210_000
	APIKeyPrefix     = "msl_"

	saltBytes   = 16
	tokenBytes  = 32
	digestBytes = 32
)

func GenerateAPIKey(prefix string) (string, error) {
	if strings.TrimSpace(prefix) == "" {
		prefix = APIKeyPrefix
	}
	buf := make([]byte, tokenBytes)
	if _, err := rand.Read(buf); err != nil {
		return "", err
	}
	return prefix + base64.RawURLEncoding.EncodeToString(buf), nil
}

func HashAPIKey(apiKey string, iterations int) (string, error) {
	if iterations <= 0 {
		iterations = PBKDF2Iterations
	}
	salt := make([]byte, saltBytes)
	if _, err := rand.Read(salt); err != nil {
		return "", err
	}
	digest := pbkdf2.Key([]byte(apiKey), salt, iterations, digestBytes, sha256.New)
	return PBKDF2Scheme + "$" + strconv.Itoa(iterations) + "$" + toB64(salt) + "$" + toB64(digest), nil
}

func VerifyAPIKey(apiKey string, storedHash string) bool {
	parts := strings.SplitN(storedHash, "$", 4)
	if len(parts) != 4 {
		return false
	}
	if parts[0] != PBKDF2Scheme {
		return false
	}
	iterations, err := strconv.Atoi(parts[1])
	if err != nil || iterations < 1 {
		return false
	}
	salt, err := fromB64(parts[2])
	if err != nil {
		return false
	}
	expectedDigest, err := fromB64(parts[3])
	if err != nil {
		return false
	}
	actualDigest := pbkdf2.Key([]byte(apiKey), salt, iterations, len(expectedDigest), sha256.New)
	return hmac.Equal(actualDigest, expectedDigest)
}

func toB64(raw []byte) string {
	return base64.StdEncoding.EncodeToString(raw)
}

func fromB64(encoded string) ([]byte, error) {
	return base64.StdEncoding.Strict().DecodeString(encoded)
}
