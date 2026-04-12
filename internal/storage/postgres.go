// Package storage provides singleton PostgreSQL pool and Redis client management, plus schema migrations.
package storage

import (
	"context"
	"sync"

	"github.com/jackc/pgx/v5/pgxpool"
)

var (
	postgresMu   sync.Mutex
	postgresPool *pgxpool.Pool
	postgresDSN  string
)

// GetPostgresPool returns a singleton PostgreSQL connection pool, creating one if needed.
func GetPostgresPool(ctx context.Context, dsn string) (*pgxpool.Pool, error) {
	postgresMu.Lock()
	defer postgresMu.Unlock()

	if postgresPool != nil && postgresDSN == dsn {
		return postgresPool, nil
	}
	if postgresPool != nil {
		postgresPool.Close()
		postgresPool = nil
		postgresDSN = ""
	}

	pool, err := pgxpool.New(ctx, dsn)
	if err != nil {
		return nil, err
	}
	postgresPool = pool
	postgresDSN = dsn
	return postgresPool, nil
}

// ClosePostgresPool closes and resets the global PostgreSQL connection pool.
func ClosePostgresPool() {
	postgresMu.Lock()
	defer postgresMu.Unlock()
	if postgresPool != nil {
		postgresPool.Close()
	}
	postgresPool = nil
	postgresDSN = ""
}
