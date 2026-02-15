package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"os/exec"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	serverPath := flag.String("server", "./bin/vulnerable-server", "Path to vulnerable MCP server binary")
	flag.Parse()

	ctx := context.Background()
	client := mcp.NewClient(&mcp.Implementation{Name: "demo-attack", Version: "0.1.0"}, nil)
	transport := &mcp.CommandTransport{Command: exec.Command(*serverPath)}
	session, err := client.Connect(ctx, transport, nil)
	if err != nil {
		log.Fatal(err)
	}
	defer session.Close()

	res, err := session.CallTool(ctx, &mcp.CallToolParams{
		Name: "delete_customer",
		Arguments: map[string]any{
			"customer_id": "cust_before_01",
		},
	})
	if err != nil {
		log.Fatalf("before-state call failed: %v", err)
	}
	if res.IsError {
		log.Fatal("before-state call returned error")
	}

	text := firstText(res)
	if text == "" {
		log.Fatal("before-state call returned empty payload")
	}

	fmt.Printf("[before] unauthorized sensitive call succeeded: %s\n", text)
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
