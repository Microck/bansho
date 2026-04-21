package storage

import (
	"context"
	"sync"

	"github.com/redis/go-redis/v9"
)

var (
	redisMu     sync.Mutex
	redisClient *redis.Client
	redisURL    string
)

// GetRedisClient returns the RedisClient.
func GetRedisClient(url string) (*redis.Client, error) {
	redisMu.Lock()
	defer redisMu.Unlock()

	if redisClient != nil && redisURL == url {
		return redisClient, nil
	}
	if redisClient != nil {
		_ = redisClient.Close()
		redisClient = nil
		redisURL = ""
	}

	opts, err := redis.ParseURL(url)
	if err != nil {
		return nil, err
	}
	redisClient = redis.NewClient(opts)
	redisURL = url
	return redisClient, nil
}

// CloseRedisClient closes the connection and releases resources.
func CloseRedisClient() {
	redisMu.Lock()
	defer redisMu.Unlock()
	if redisClient != nil {
		_ = redisClient.Close()
	}
	redisClient = nil
	redisURL = ""
}

// PingRedis implements the ping redis logic.
func PingRedis(ctx context.Context, client *redis.Client) error {
	return client.Ping(ctx).Err()
}

// RedisEval implements the redis eval logic.
func RedisEval(ctx context.Context, client *redis.Client, script string, keys []string, args []any) (any, error) {
	return client.Eval(ctx, script, keys, args...).Result()
}
