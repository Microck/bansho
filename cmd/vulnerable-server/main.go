package main

import (
	"context"
	"log"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type ListCustomersArgs struct{}

type DeleteCustomerArgs struct {
	CustomerID string `json:"customer_id" jsonschema:"ID of the customer to delete"`
}

func listCustomers(_ context.Context, _ *mcp.CallToolRequest, _ ListCustomersArgs) (*mcp.CallToolResult, any, error) {
	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: "customers: cust_001, cust_002"},
		},
	}, nil, nil
}

func deleteCustomer(_ context.Context, _ *mcp.CallToolRequest, in DeleteCustomerArgs) (*mcp.CallToolResult, any, error) {
	return &mcp.CallToolResult{
		Content: []mcp.Content{
			&mcp.TextContent{Text: "deleted customer: " + in.CustomerID},
		},
	}, nil, nil
}

func main() {
	server := mcp.NewServer(&mcp.Implementation{Name: "vulnerable-demo", Version: "0.1.0"}, &mcp.ServerOptions{})
	// Intentionally vulnerable: no auth, no rate limiting.
	mcp.AddTool(server, &mcp.Tool{Name: "list_customers", Description: "List customers"}, listCustomers)
	mcp.AddTool(server, &mcp.Tool{Name: "delete_customer", Description: "Delete a customer"}, deleteCustomer)

	if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Fatal(err)
	}
}
