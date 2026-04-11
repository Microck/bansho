package storage

import (
	"context"
	"fmt"

	"github.com/jackc/pgx/v5/pgxpool"
)

// migrations defines the ordered set of schema migrations.
// Each migration has a unique ID and a SQL statement.
// The schema_migrations table tracks which IDs have been applied.
var migrations = []struct {
	ID  string
	SQL string
}{
	{
		ID: "001_create_api_keys",
		SQL: `
		CREATE TABLE IF NOT EXISTS api_keys (
			id uuid PRIMARY KEY,
			key_hash text NOT NULL UNIQUE,
			role text NOT NULL,
			created_at timestamptz NOT NULL DEFAULT NOW(),
			revoked_at timestamptz
		);`,
	},
	{
		ID: "002_create_audit_events",
		SQL: `
		CREATE TABLE IF NOT EXISTS audit_events (
			id uuid PRIMARY KEY,
			ts timestamptz NOT NULL DEFAULT NOW(),
			api_key_id uuid REFERENCES api_keys(id) ON DELETE SET NULL,
			role text NOT NULL DEFAULT 'unknown',
			method text NOT NULL,
			tool_name text NOT NULL,
			request_json jsonb NOT NULL DEFAULT '{}'::jsonb,
			response_json jsonb NOT NULL DEFAULT '{}'::jsonb,
			decision jsonb NOT NULL DEFAULT '{}'::jsonb,
			status_code integer NOT NULL,
			latency_ms integer NOT NULL CHECK (latency_ms >= 0)
		);`,
	},
	{
		ID: "003_audit_events_role_column",
		SQL: `
		ALTER TABLE audit_events
		ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'unknown';`,
	},
	{
		ID: "004_audit_events_decision_column",
		SQL: `
		ALTER TABLE audit_events
		ADD COLUMN IF NOT EXISTS decision jsonb NOT NULL DEFAULT '{}'::jsonb;`,
	},
	{
		ID: "005_schema_migrations",
		SQL: `
		CREATE TABLE IF NOT EXISTS schema_migrations (
			id text PRIMARY KEY,
			applied_at timestamptz NOT NULL DEFAULT NOW()
		);`,
	},
}

// EnsureSchema applies any pending migrations in order.
// It creates the schema_migrations table first (if needed), then
// runs each migration that hasn't been applied yet.
// This is idempotent — safe to call on every startup.
func EnsureSchema(ctx context.Context, pool *pgxpool.Pool) error {
	// Ensure the migrations tracking table exists before anything else.
	createMigrationsTable := `
		CREATE TABLE IF NOT EXISTS schema_migrations (
			id text PRIMARY KEY,
			applied_at timestamptz NOT NULL DEFAULT NOW()
		);`
	if _, err := pool.Exec(ctx, createMigrationsTable); err != nil {
		return fmt.Errorf("create schema_migrations: %w", err)
	}

	// Build the set of already-applied migration IDs.
	applied := make(map[string]bool, len(migrations))
	rows, err := pool.Query(ctx, "SELECT id FROM schema_migrations")
	if err != nil {
		return fmt.Errorf("read schema_migrations: %w", err)
	}
	defer rows.Close()
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return fmt.Errorf("scan migration id: %w", err)
		}
		applied[id] = true
	}
	if rows.Err() != nil {
		return fmt.Errorf("iterate schema_migrations: %w", err)
	}

	// Apply pending migrations in order.
	for _, m := range migrations {
		if applied[m.ID] {
			continue
		}
		if _, err := pool.Exec(ctx, m.SQL); err != nil {
			return fmt.Errorf("apply migration %s: %w", m.ID, err)
		}
		if _, err := pool.Exec(ctx, "INSERT INTO schema_migrations (id) VALUES ($1)", m.ID); err != nil {
			return fmt.Errorf("record migration %s: %w", m.ID, err)
		}
	}

	return nil
}
