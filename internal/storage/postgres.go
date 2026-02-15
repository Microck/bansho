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

func ClosePostgresPool() {
	postgresMu.Lock()
	defer postgresMu.Unlock()
	if postgresPool != nil {
		postgresPool.Close()
	}
	postgresPool = nil
	postgresDSN = ""
}
