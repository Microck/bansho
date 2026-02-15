package storage

import (
	"context"

	"github.com/jackc/pgx/v5/pgxpool"
)

var schemaStatements = []string{
	`
	CREATE TABLE IF NOT EXISTS api_keys (
		id uuid PRIMARY KEY,
		key_hash text NOT NULL UNIQUE,
		role text NOT NULL,
		created_at timestamptz NOT NULL DEFAULT NOW(),
		revoked_at timestamptz
	);
	`,
	`
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
	);
	`,
	`
	ALTER TABLE audit_events
	ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'unknown';
	`,
	`
	ALTER TABLE audit_events
	ADD COLUMN IF NOT EXISTS decision jsonb NOT NULL DEFAULT '{}'::jsonb;
	`,
}

func EnsureSchema(ctx context.Context, pool *pgxpool.Pool) error {
	for _, stmt := range schemaStatements {
		if _, err := pool.Exec(ctx, stmt); err != nil {
			return err
		}
	}
	return nil
}
