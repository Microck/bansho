package main

import (
	"context"
	"flag"
	"fmt"
	"os"

	"github.com/microck/bansho/internal/auth"
	"github.com/microck/bansho/internal/config"
	"github.com/microck/bansho/internal/proxy"
	"github.com/microck/bansho/internal/storage"
	"github.com/microck/bansho/internal/ui"
)

var Version = "dev"

func main() {
	os.Exit(run(os.Args[1:]))
}

func run(args []string) int {
	if len(args) == 0 {
		printHelp()
		return 0
	}

	switch args[0] {
	case "--version", "-version", "version":
		fmt.Printf("bansho %s\n", Version)
		return 0
	case "serve":
		return runServe(args[1:])
	case "dashboard":
		return runDashboard(args[1:])
	case "keys":
		return runKeys(args[1:])
	case "help", "-h", "--help":
		printHelp()
		return 0
	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", args[0])
		printHelp()
		return 2
	}
}

func printHelp() {
	fmt.Println("bansho - MCP security gateway")
	fmt.Println("")
	fmt.Println("Usage:")
	fmt.Println("  bansho serve")
	fmt.Println("  bansho dashboard")
	fmt.Println("  bansho keys create|list|revoke")
	fmt.Println("")
}

func runServe(_ []string) int {
	settings, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Config error: %v\n", err)
		return 1
	}
	if err := proxy.RunStdioGateway(settings); err != nil {
		fmt.Fprintf(os.Stderr, "Serve error: %v\n", err)
		return 1
	}
	return 0
}

func runDashboard(_ []string) int {
	settings, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Config error: %v\n", err)
		return 1
	}
	if err := ui.RunDashboard(settings); err != nil {
		fmt.Fprintf(os.Stderr, "Dashboard error: %v\n", err)
		return 1
	}
	return 0
}

func runKeys(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "Missing keys subcommand (create|list|revoke)")
		return 2
	}

	settings, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Config error: %v\n", err)
		return 1
	}

	ctx := context.Background()
	pool, err := storage.GetPostgresPool(ctx, settings.PostgresDSN)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Postgres error: %v\n", err)
		return 1
	}
	defer storage.ClosePostgresPool()

	if err := storage.EnsureSchema(ctx, pool); err != nil {
		fmt.Fprintf(os.Stderr, "Schema error: %v\n", err)
		return 1
	}

	switch args[0] {
	case "create":
		fs := flag.NewFlagSet("bansho keys create", flag.ContinueOnError)
		fs.SetOutput(os.Stderr)
		role := fs.String("role", auth.DefaultAPIKeyRole, "Role for the new API key (default: readonly)")
		if parseErr := fs.Parse(args[1:]); parseErr != nil {
			return 2
		}
		apiKeyID, apiKey, err := auth.CreateAPIKey(ctx, pool, *role)
		if err != nil {
			fmt.Fprintln(os.Stderr, "Failed to create API key.")
			return 1
		}
		fmt.Printf("api_key_id: %s\n", apiKeyID)
		fmt.Printf("api_key: %s\n", apiKey)
		return 0
	case "list":
		keys, err := auth.ListAPIKeys(ctx, pool)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Failed to list API keys: %v\n", err)
			return 1
		}
		if len(keys) == 0 {
			fmt.Println("No API keys found.")
			return 0
		}
		fmt.Println("api_key_id\trole\trevoked")
		for _, k := range keys {
			revokedText := "no"
			if k.Revoked {
				revokedText = "yes"
			}
			fmt.Printf("%s\t%s\t%s\n", k.APIKeyID, k.Role, revokedText)
		}
		return 0
	case "revoke":
		if len(args) < 2 {
			fmt.Fprintln(os.Stderr, "Missing api_key_id")
			return 2
		}
		revoked, err := auth.RevokeAPIKey(ctx, pool, args[1])
		if err != nil {
			fmt.Fprintf(os.Stderr, "Failed to revoke API key: %v\n", err)
			return 1
		}
		if revoked {
			fmt.Printf("Revoked API key: %s\n", args[1])
			return 0
		}
		fmt.Fprintf(os.Stderr, "API key not found or already revoked: %s\n", args[1])
		return 1
	default:
		fmt.Fprintf(os.Stderr, "Unsupported keys command: %s\n", args[0])
		return 2
	}
}
