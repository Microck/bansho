package main

import (
	"fmt"
	"os"

	"github.com/microck/bansho/internal/config"
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
	_, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Config error: %v\n", err)
		return 1
	}
	fmt.Fprintln(os.Stderr, "serve: not implemented yet")
	return 1
}

func runDashboard(_ []string) int {
	_, err := config.Load()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Config error: %v\n", err)
		return 1
	}
	fmt.Fprintln(os.Stderr, "dashboard: not implemented yet")
	return 1
}

func runKeys(args []string) int {
	if len(args) == 0 {
		fmt.Fprintln(os.Stderr, "Missing keys subcommand (create|list|revoke)")
		return 2
	}
	fmt.Fprintln(os.Stderr, "keys: not implemented yet")
	return 1
}
