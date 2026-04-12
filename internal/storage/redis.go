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

// GetRedisClient returns a singleton Redis client, creating one if needed.
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

// CloseRedisClient closes and resets the global Redis client.
func CloseRedisClient() {
	redisMu.Lock()
	defer redisMu.Unlock()
	if redisClient != nil {
		_ = redisClient.Close()
	}
	redisClient = nil
	redisURL = ""
}

// PingRedis verifies connectivity to the Redis server.
func PingRedis(ctx context.Context, client *redis.Client) error {
	return client.Ping(ctx).Err()
}

// RedisEval executes a Redis Lua script with the given keys and arguments.
func RedisEval(ctx context.Context, client *redis.Client, script string, keys []string, args []any) (any, error) {
	return client.Eval(ctx, script, keys, args...).Result()
}
