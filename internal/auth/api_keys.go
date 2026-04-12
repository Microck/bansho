// Package auth provides API key creation, verification, and management backed by PostgreSQL.
package auth

import (
	"context"
	"strings"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

// DefaultAPIKeyRole is the role assigned to newly created API keys when no role is specified.
const DefaultAPIKeyRole = "readonly"

// ResolvedKey holds the identity and role resolved from a verified API key.
type ResolvedKey struct {
	APIKeyID string
	Role     string
}

// ListedKey represents an API key entry returned by ListAPIKeys.
type ListedKey struct {
	APIKeyID string
	Role     string
	Revoked  bool
}

// CreateAPIKey generates a new API key, hashes it, and stores it in the database.
func CreateAPIKey(ctx context.Context, pool *pgxpool.Pool, role string) (apiKeyID string, apiKey string, err error) {
	normalizedRole := normalizeRole(role)
	apiKey, err = GenerateAPIKey(APIKeyPrefix)
	if err != nil {
		return "", "", err
	}
	apiKeyHash, err := HashAPIKey(apiKey, PBKDF2Iterations)
	if err != nil {
		return "", "", err
	}
	id := uuid.New()
	_, err = pool.Exec(ctx, "INSERT INTO api_keys (id, key_hash, role) VALUES ($1, $2, $3);", id, apiKeyHash, normalizedRole)
	if err != nil {
		return "", "", err
	}
	return id.String(), apiKey, nil
}

// ResolveAPIKey looks up the presented key against all non-revoked keys and returns the matching identity.
func ResolveAPIKey(ctx context.Context, pool *pgxpool.Pool, presentedKey string) (*ResolvedKey, error) {
	if strings.TrimSpace(presentedKey) == "" {
		return nil, nil
	}
	rows, err := pool.Query(ctx, "SELECT id, key_hash, role FROM api_keys WHERE revoked_at IS NULL;")
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var resolved *ResolvedKey
	for rows.Next() {
		var (
			id      uuid.UUID
			keyHash string
			role    string
		)
		if scanErr := rows.Scan(&id, &keyHash, &role); scanErr != nil {
			return nil, scanErr
		}
		if VerifyAPIKey(presentedKey, keyHash) {
			resolved = &ResolvedKey{APIKeyID: id.String(), Role: role}
		}
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return resolved, nil
}

// ListAPIKeys returns all API keys ordered by creation time descending.
func ListAPIKeys(ctx context.Context, pool *pgxpool.Pool) ([]ListedKey, error) {
	rows, err := pool.Query(ctx, `
		SELECT id, role, (revoked_at IS NOT NULL) AS revoked
		FROM api_keys
		ORDER BY created_at DESC;
	`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []ListedKey
	for rows.Next() {
		var (
			id      uuid.UUID
			role    string
			revoked bool
		)
		if scanErr := rows.Scan(&id, &role, &revoked); scanErr != nil {
			return nil, scanErr
		}
		out = append(out, ListedKey{APIKeyID: id.String(), Role: role, Revoked: revoked})
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return out, nil
}

// RevokeAPIKey marks the specified API key as revoked; returns true if a key was revoked.
func RevokeAPIKey(ctx context.Context, pool *pgxpool.Pool, apiKeyID string) (bool, error) {
	parsed, err := uuid.Parse(strings.TrimSpace(apiKeyID))
	if err != nil {
		return false, nil
	}
	cmd, err := pool.Exec(ctx, `
		UPDATE api_keys
		SET revoked_at = NOW()
		WHERE id = $1 AND revoked_at IS NULL;
	`, parsed)
	if err != nil {
		return false, err
	}
	return cmd.RowsAffected() > 0, nil
}

func normalizeRole(role string) string {
	normalized := strings.TrimSpace(role)
	if normalized != "" {
		return normalized
	}
	return DefaultAPIKeyRole
}
