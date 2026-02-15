package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"log"
	"os"
	"os/exec"
	"strings"

	"github.com/modelcontextprotocol/go-sdk/jsonrpc"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

const (
	sensitiveTool   = "delete_customer"
	rateLimitedTool = "list_customers"
)

func main() {
	banshoPath := flag.String("bansho", "./bin/bansho", "Path to bansho binary")
	flag.Parse()

	readonlyKey := os.Getenv("DEMO_READONLY_API_KEY")
	adminKey := os.Getenv("DEMO_ADMIN_API_KEY")
	if strings.TrimSpace(readonlyKey) == "" || strings.TrimSpace(adminKey) == "" {
		log.Fatal("missing DEMO_READONLY_API_KEY or DEMO_ADMIN_API_KEY")
	}

	ctx := context.Background()
	client := mcp.NewClient(&mcp.Implementation{Name: "demo-after", Version: "0.1.0"}, nil)
	cmd := exec.Command(*banshoPath, "serve")
	cmd.Env = os.Environ()
	transport := &mcp.CommandTransport{Command: cmd}
	session, err := client.Connect(ctx, transport, nil)
	if err != nil {
		log.Fatal(err)
	}
	defer session.Close()

	// 401: missing key
	_, err = callTool(ctx, session, rateLimitedTool, map[string]any{}, "")
	expectWireError(err, 401, "401 check (missing API key)")

	// 403: readonly key on sensitive tool
	_, err = callTool(ctx, session, sensitiveTool, map[string]any{"customer_id": "cust_blocked_01"}, readonlyKey)
	expectWireError(err, 403, "403 check (readonly on sensitive tool)")

	// 429: rate-limited tool twice
	if _, err := callTool(ctx, session, rateLimitedTool, map[string]any{}, readonlyKey); err != nil {
		log.Fatalf("429 check: first call should succeed: %v", err)
	}
	fmt.Println("[after] 429 check: first readonly call succeeded")
	_, err = callTool(ctx, session, rateLimitedTool, map[string]any{}, readonlyKey)
	expectWireError(err, 429, "429 check (second readonly call)")

	// 200: admin sensitive call succeeds
	res, err := callTool(ctx, session, sensitiveTool, map[string]any{"customer_id": "cust_allowed_01"}, adminKey)
	if err != nil {
		log.Fatalf("200 check failed: %v", err)
	}
	if res.IsError {
		log.Fatal("200 check: admin sensitive call returned error")
	}
	adminText := firstText(res)
	if strings.TrimSpace(adminText) == "" {
		log.Fatal("200 check: admin sensitive call returned empty payload")
	}
	fmt.Println("[after] 200 check (admin sensitive call) succeeded")
	fmt.Printf("[after] admin response: %s\n", adminText)
	fmt.Println("After-state checks complete: 401 / 403 / 429 / 200")
}

func callTool(ctx context.Context, session *mcp.ClientSession, name string, args map[string]any, apiKey string) (*mcp.CallToolResult, error) {
	params := &mcp.CallToolParams{Name: name, Arguments: args}
	if strings.TrimSpace(apiKey) != "" {
		params.Meta = mcp.Meta{"headers": map[string]any{"X-API-Key": apiKey}}
	}
	return session.CallTool(ctx, params)
}

func expectWireError(err error, expectedCode int64, label string) {
	if err == nil {
		log.Fatalf("%s: expected error code %d", label, expectedCode)
	}
	var werr *jsonrpc.Error
	if !errors.As(err, &werr) {
		log.Fatalf("%s: expected wire error, got %T: %v", label, err, err)
	}
	if werr.Code != expectedCode {
		log.Fatalf("%s: expected %d, got %d", label, expectedCode, werr.Code)
	}
	fmt.Printf("[after] %s: got expected %d\n", label, expectedCode)
}

func firstText(res *mcp.CallToolResult) string {
	if res == nil {
		return ""
	}
	for _, c := range res.Content {
		if t, ok := c.(*mcp.TextContent); ok {
			if t.Text != "" {
				return t.Text
			}
		}
	}
	return ""
}
