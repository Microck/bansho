package config

import (
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/joho/godotenv"
)

type UpstreamTransport string

const (
	UpstreamTransportStdio UpstreamTransport = "stdio"
	UpstreamTransportHTTP  UpstreamTransport = "http"
)

type Settings struct {
	BanshoListenHost string
	BanshoListenPort int
	DashboardHost    string
	DashboardPort    int

	UpstreamTransport UpstreamTransport
	UpstreamCmd       string
	UpstreamURL       string

	PostgresDSN string
	RedisURL    string
}

func Load() (Settings, error) {
	// Best-effort `.env` support for local dev parity. If missing, continue.
	_ = godotenv.Overload()

	s := Settings{
		BanshoListenHost: "127.0.0.1",
		BanshoListenPort: 9000,
		DashboardHost:    "127.0.0.1",
		DashboardPort:    9100,

		UpstreamTransport: UpstreamTransportStdio,
		UpstreamCmd:       "",
		UpstreamURL:       "",

		PostgresDSN: "postgresql://bansho:bansho@127.0.0.1:5433/bansho",
		RedisURL:    "redis://127.0.0.1:6379/0",
	}

	s.BanshoListenHost = getEnvString("BANSHO_LISTEN_HOST", s.BanshoListenHost)
	if v, ok, err := getEnvInt("BANSHO_LISTEN_PORT"); err != nil {
		return Settings{}, fmt.Errorf("BANSHO_LISTEN_PORT: %w", err)
	} else if ok {
		s.BanshoListenPort = v
	}

	s.DashboardHost = getEnvString("DASHBOARD_HOST", s.DashboardHost)
	if v, ok, err := getEnvInt("DASHBOARD_PORT"); err != nil {
		return Settings{}, fmt.Errorf("DASHBOARD_PORT: %w", err)
	} else if ok {
		s.DashboardPort = v
	}

	if t := strings.TrimSpace(os.Getenv("UPSTREAM_TRANSPORT")); t != "" {
		transport := UpstreamTransport(strings.ToLower(t))
		switch transport {
		case UpstreamTransportStdio, UpstreamTransportHTTP:
			s.UpstreamTransport = transport
		default:
			return Settings{}, fmt.Errorf("UPSTREAM_TRANSPORT must be one of: stdio, http")
		}
	}
	s.UpstreamCmd = strings.TrimSpace(os.Getenv("UPSTREAM_CMD"))
	s.UpstreamURL = strings.TrimSpace(os.Getenv("UPSTREAM_URL"))

	s.PostgresDSN = getEnvString("POSTGRES_DSN", s.PostgresDSN)
	s.RedisURL = getEnvString("REDIS_URL", s.RedisURL)

	return s, nil
}

func getEnvString(key, fallback string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return fallback
}

func getEnvInt(key string) (value int, ok bool, err error) {
	raw := strings.TrimSpace(os.Getenv(key))
	if raw == "" {
		return 0, false, nil
	}
	parsed, parseErr := strconv.Atoi(raw)
	if parseErr != nil {
		return 0, true, errors.New("must be an integer")
	}
	return parsed, true, nil
}
