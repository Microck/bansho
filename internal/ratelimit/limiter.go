package ratelimit

import (
	"context"
	"fmt"
	"strconv"
	"strings"
	"time"

	"github.com/microck/bansho/internal/storage"
	"github.com/redis/go-redis/v9"
)

const FixedWindowIncrScript = "local current = redis.call(\"INCR\", KEYS[1])\nif current == 1 then\n  redis.call(\"EXPIRE\", KEYS[1], ARGV[1])\nend\nreturn current"

const (
	unknownAPIKeySegment = "__unknown_key__"
	unknownToolSegment   = "__unknown_tool__"
)

type RateLimitResult struct {
	Allowed   bool
	Remaining int
	ResetS    int
}

func CheckAPIKeyLimit(ctx context.Context, client *redis.Client, apiKeyID string, requests int, windowSeconds int, nowS *int64) (RateLimitResult, error) {
	currentEpoch := currentEpoch(nowS)
	windowBucket, err := windowBucket(currentEpoch, windowSeconds)
	if err != nil {
		return RateLimitResult{}, err
	}
	key := apiKeyRateLimitKey(apiKeyID, windowBucket)
	return checkFixedWindowLimit(ctx, client, key, requests, windowSeconds, currentEpoch)
}

func CheckToolLimit(ctx context.Context, client *redis.Client, apiKeyID string, toolName string, requests int, windowSeconds int, nowS *int64) (RateLimitResult, error) {
	currentEpoch := currentEpoch(nowS)
	windowBucket, err := windowBucket(currentEpoch, windowSeconds)
	if err != nil {
		return RateLimitResult{}, err
	}
	key := toolRateLimitKey(apiKeyID, toolName, windowBucket)
	return checkFixedWindowLimit(ctx, client, key, requests, windowSeconds, currentEpoch)
}

func apiKeyRateLimitKey(apiKeyID string, windowBucket int64) string {
	n := normalizeSegment(apiKeyID, unknownAPIKeySegment)
	return fmt.Sprintf("rl:%s:%d", n, windowBucket)
}

func toolRateLimitKey(apiKeyID string, toolName string, windowBucket int64) string {
	nKey := normalizeSegment(apiKeyID, unknownAPIKeySegment)
	nTool := normalizeSegment(toolName, unknownToolSegment)
	return fmt.Sprintf("rl:%s:%s:%d", nKey, nTool, windowBucket)
}

func checkFixedWindowLimit(ctx context.Context, client *redis.Client, key string, requests int, windowSeconds int, currentEpoch int64) (RateLimitResult, error) {
	if requests <= 0 {
		return RateLimitResult{}, fmt.Errorf("requests must be greater than 0")
	}
	if windowSeconds <= 0 {
		return RateLimitResult{}, fmt.Errorf("window_seconds must be greater than 0")
	}
	resetS := secondsUntilReset(currentEpoch, int64(windowSeconds))

	rawCount, err := storage.RedisEval(ctx, client, FixedWindowIncrScript, []string{key}, []any{resetS})
	if err != nil {
		return RateLimitResult{}, err
	}
	currentCount, err := coerceInt(rawCount)
	if err != nil {
		return RateLimitResult{}, err
	}

	remaining := requests - currentCount
	if remaining < 0 {
		remaining = 0
	}
	return RateLimitResult{
		Allowed:   currentCount <= requests,
		Remaining: remaining,
		ResetS:    int(resetS),
	}, nil
}

func windowBucket(currentEpoch int64, windowSeconds int) (int64, error) {
	if windowSeconds <= 0 {
		return 0, fmt.Errorf("window_seconds must be greater than 0")
	}
	return currentEpoch / int64(windowSeconds), nil
}

func secondsUntilReset(currentEpoch int64, windowSeconds int64) int64 {
	remainder := currentEpoch % windowSeconds
	if remainder == 0 {
		return windowSeconds
	}
	return windowSeconds - remainder
}

func currentEpoch(nowS *int64) int64 {
	if nowS == nil {
		return time.Now().Unix()
	}
	return *nowS
}

func normalizeSegment(value string, fallback string) string {
	n := strings.TrimSpace(value)
	if n == "" {
		return fallback
	}
	return n
}

func coerceInt(value any) (int, error) {
	switch v := value.(type) {
	case int:
		return v, nil
	case int64:
		return int(v), nil
	case float64:
		return int(v), nil
	case string:
		// go-redis can return a string for integer replies in some cases.
		parsed, err := strconv.ParseInt(v, 10, 64)
		if err != nil {
			return 0, fmt.Errorf("unexpected counter value")
		}
		return int(parsed), nil
	default:
		return 0, fmt.Errorf("unexpected counter value")
	}
}
