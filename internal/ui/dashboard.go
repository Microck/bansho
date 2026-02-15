package ui

import (
	"context"
	"encoding/json"
	"fmt"
	"html"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"

	"github.com/microck/bansho/internal/audit"
	"github.com/microck/bansho/internal/auth"
	"github.com/microck/bansho/internal/config"
	"github.com/microck/bansho/internal/storage"
)

const (
	defaultEventLimit = 50
	maxEventLimit     = 200
)

type DashboardAuthContext struct {
	APIKeyID string
	Role     string
}

func RunDashboard(settings config.Settings) error {
	ctx := context.Background()
	pool, err := storage.GetPostgresPool(ctx, settings.PostgresDSN)
	if err != nil {
		return err
	}

	if err := storage.EnsureSchema(ctx, pool); err != nil {
		return err
	}

	logger := &audit.Logger{Pool: pool}
	addr := fmt.Sprintf("%s:%d", settings.DashboardHost, settings.DashboardPort)

	mux := http.NewServeMux()
	mux.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) { handleDashboard(logger, w, r) })
	mux.HandleFunc("/dashboard", func(w http.ResponseWriter, r *http.Request) { handleDashboard(logger, w, r) })
	mux.HandleFunc("/api/events", func(w http.ResponseWriter, r *http.Request) { handleEventsAPI(logger, w, r) })

	srv := &http.Server{
		Addr:              addr,
		Handler:           mux,
		ReadHeaderTimeout: 5 * time.Second,
	}
	return srv.ListenAndServe()
}

func handleDashboard(logger *audit.Logger, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusNotFound, map[string]any{"error": map[string]any{"code": 404, "message": "Not Found"}})
		return
	}

	authCtx, filters, events, ok := handleAuthAndQuery(logger, w, r)
	if !ok {
		return
	}

	body := renderDashboardHTML(authCtx, filters, events)
	writeHTML(w, http.StatusOK, body)
}

func handleEventsAPI(logger *audit.Logger, w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeJSON(w, http.StatusNotFound, map[string]any{"error": map[string]any{"code": 404, "message": "Not Found"}})
		return
	}

	_, filters, events, ok := handleAuthAndQuery(logger, w, r)
	if !ok {
		return
	}

	writeJSON(w, http.StatusOK, map[string]any{
		"count": len(events),
		"filters": map[string]any{
			"api_key_id": filters.APIKeyID,
			"tool_name":  filters.ToolName,
			"limit":      filters.Limit,
		},
		"events": events,
	})
}

type dashboardFilters struct {
	APIKeyID *string
	ToolName *string
	Limit    int
}

func handleAuthAndQuery(logger *audit.Logger, w http.ResponseWriter, r *http.Request) (DashboardAuthContext, dashboardFilters, []audit.RecentEvent, bool) {
	query := r.URL.Query()
	apiKey := extractPresentedAPIKey(r, query)
	if apiKey == "" {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"error": map[string]any{"code": 401, "message": "Unauthorized"}})
		return DashboardAuthContext{}, dashboardFilters{}, nil, false
	}

	resolved, err := auth.ResolveAPIKey(r.Context(), logger.Pool, apiKey)
	if err != nil || resolved == nil {
		writeJSON(w, http.StatusUnauthorized, map[string]any{"error": map[string]any{"code": 401, "message": "Unauthorized"}})
		return DashboardAuthContext{}, dashboardFilters{}, nil, false
	}
	if strings.ToLower(strings.TrimSpace(resolved.Role)) != "admin" {
		writeJSON(w, http.StatusForbidden, map[string]any{"error": map[string]any{"code": 403, "message": "Forbidden"}})
		return DashboardAuthContext{}, dashboardFilters{}, nil, false
	}
	authCtx := DashboardAuthContext{APIKeyID: resolved.APIKeyID, Role: resolved.Role}

	filters, err := parseFilters(query)
	if err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": map[string]any{"code": 400, "message": err.Error()}})
		return DashboardAuthContext{}, dashboardFilters{}, nil, false
	}

	events, err := logger.FetchRecentEvents(r.Context(), audit.RecentQuery{Limit: filters.Limit, APIKeyID: filters.APIKeyID, ToolName: filters.ToolName})
	if err != nil {
		writeJSON(w, http.StatusInternalServerError, map[string]any{"error": map[string]any{"code": 500, "message": "Dashboard query failed"}})
		return DashboardAuthContext{}, dashboardFilters{}, nil, false
	}

	return authCtx, filters, events, true
}

func extractPresentedAPIKey(r *http.Request, query url.Values) string {
	authorization := strings.TrimSpace(r.Header.Get("Authorization"))
	if authorization != "" {
		parts := strings.SplitN(authorization, " ", 2)
		if len(parts) == 2 && strings.ToLower(parts[0]) == "bearer" {
			if token := strings.TrimSpace(parts[1]); token != "" {
				return token
			}
		}
	}
	if v := strings.TrimSpace(r.Header.Get("X-API-Key")); v != "" {
		return v
	}
	if v := strings.TrimSpace(query.Get("api_key")); v != "" {
		return v
	}
	return ""
}

func parseFilters(query url.Values) (dashboardFilters, error) {
	filters := dashboardFilters{}
	if v := strings.TrimSpace(query.Get("api_key_id")); v != "" {
		filters.APIKeyID = &v
	}
	if v := strings.TrimSpace(query.Get("tool_name")); v != "" {
		filters.ToolName = &v
	}
	limitValue := strings.TrimSpace(query.Get("limit"))
	if limitValue == "" {
		filters.Limit = defaultEventLimit
		return filters, nil
	}
	parsed, err := strconv.Atoi(limitValue)
	if err != nil {
		return dashboardFilters{}, fmt.Errorf("limit must be an integer")
	}
	if parsed < 1 || parsed > maxEventLimit {
		return dashboardFilters{}, fmt.Errorf("limit must be between 1 and %d", maxEventLimit)
	}
	filters.Limit = parsed
	return filters, nil
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	b, _ := json.Marshal(payload)
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write(b)
}

func writeHTML(w http.ResponseWriter, status int, body string) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(status)
	_, _ = w.Write([]byte(body))
}

func renderDashboardHTML(authCtx DashboardAuthContext, filters dashboardFilters, events []audit.RecentEvent) string {
	query := url.Values{}
	query.Set("limit", fmt.Sprintf("%d", filters.Limit))
	if filters.APIKeyID != nil {
		query.Set("api_key_id", *filters.APIKeyID)
	}
	if filters.ToolName != nil {
		query.Set("tool_name", *filters.ToolName)
	}
	apiHref := "/api/events?" + query.Encode()

	rows := ""
	for _, e := range events {
		decisionJSON, _ := json.Marshal(e.Decision)
		rows += "<tr>" +
			"<td>" + html.EscapeString(e.TS) + "</td>" +
			"<td>" + html.EscapeString(deref(e.APIKeyID)) + "</td>" +
			"<td>" + html.EscapeString(e.Role) + "</td>" +
			"<td>" + html.EscapeString(e.Method) + "</td>" +
			"<td>" + html.EscapeString(e.ToolName) + "</td>" +
			"<td>" + fmt.Sprintf("%d", e.Status) + "</td>" +
			"<td>" + fmt.Sprintf("%d", e.LatencyMS) + "</td>" +
			"<td><code>" + html.EscapeString(string(decisionJSON)) + "</code></td>" +
			"</tr>"
	}
	if rows == "" {
		rows = "<tr><td colspan='8'>No audit events found for the current filters.</td></tr>"
	}

	apiKeyIDValue := ""
	if filters.APIKeyID != nil {
		apiKeyIDValue = *filters.APIKeyID
	}
	toolNameValue := ""
	if filters.ToolName != nil {
		toolNameValue = *filters.ToolName
	}

	return "<!doctype html>" +
		"<html lang='en'>" +
		"<head>" +
		"<meta charset='utf-8'>" +
		"<meta name='viewport' content='width=device-width, initial-scale=1'>" +
		"<title>MCP Bansho Audit Dashboard</title>" +
		"<style>" +
		"body{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace;margin:24px;background:#f5f7fb;color:#111827;}" +
		"h1{margin:0 0 12px 0;font-size:24px;}" +
		"p{margin:0 0 16px 0;}" +
		"form{display:flex;flex-wrap:wrap;gap:12px;margin:0 0 16px 0;padding:12px;background:#ffffff;border:1px solid #d1d5db;border-radius:8px;}" +
		"label{display:flex;flex-direction:column;font-size:12px;gap:6px;}" +
		"input{padding:8px;border:1px solid #9ca3af;border-radius:6px;min-width:220px;}" +
		"button{padding:8px 12px;border:1px solid #374151;background:#111827;color:#fff;border-radius:6px;cursor:pointer;}" +
		"a{color:#1d4ed8;text-decoration:none;}" +
		"table{width:100%;border-collapse:collapse;background:#fff;border:1px solid #d1d5db;}" +
		"th,td{padding:8px;vertical-align:top;border-bottom:1px solid #e5e7eb;text-align:left;}" +
		"th{background:#f3f4f6;font-size:12px;text-transform:uppercase;letter-spacing:0.04em;}" +
		"code{font-size:12px;white-space:pre-wrap;word-break:break-word;}" +
		"</style>" +
		"</head>" +
		"<body>" +
		"<h1>MCP Bansho Audit Dashboard</h1>" +
		"<p>Authenticated as admin key ID: <strong>" + html.EscapeString(authCtx.APIKeyID) + "</strong></p>" +
		"<form method='get' action='/dashboard'>" +
		"<label>API Key ID<input type='text' name='api_key_id' value='" + html.EscapeString(apiKeyIDValue) + "'></label>" +
		"<label>Tool Name<input type='text' name='tool_name' value='" + html.EscapeString(toolNameValue) + "'></label>" +
		"<label>Limit<input type='number' min='1' max='" + fmt.Sprintf("%d", maxEventLimit) + "' name='limit' value='" + fmt.Sprintf("%d", filters.Limit) + "'></label>" +
		"<button type='submit'>Apply filters</button>" +
		"<a href='" + html.EscapeString(apiHref) + "'>JSON API</a>" +
		"</form>" +
		"<table><thead><tr>" +
		"<th>Timestamp</th><th>API Key ID</th><th>Role</th><th>Method</th><th>Tool</th><th>Status</th><th>Latency (ms)</th><th>Decision</th>" +
		"</tr></thead><tbody>" + rows + "</tbody></table>" +
		"</body></html>"
}

func deref(v *string) string {
	if v == nil {
		return ""
	}
	return *v
}
