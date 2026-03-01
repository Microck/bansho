package ui

import (
	"bytes"
	"context"
	"embed"
	"encoding/json"
	"fmt"
	"html"
	"html/template"
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

//go:embed dashboard.html banshologo.svg banshohorizontal.svg
var uiFS embed.FS

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

type templateData struct {
	HeaderHTML    template.HTML
	FilterBarHTML template.HTML
	RowsHTML      template.HTML
	FooterHTML    template.HTML
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

	// Read the horizontal logo SVG (contains wordmark)
	logoSVG, _ := uiFS.ReadFile("banshohorizontal.svg")

	// ── Count stats for header KPI ──
	totalEvents := len(events)
	var okCount, errCount, rateCount int
	for _, e := range events {
		if e.Status >= 200 && e.Status <= 299 {
			okCount++
		} else if e.Status == 401 || e.Status == 403 || e.Status >= 500 {
			errCount++
		} else if e.Status == 429 {
			rateCount++
		}
	}

	// ── Build header (logo + inline KPI + key badge + theme toggle) ──
	keyShort := authCtx.APIKeyID
	if len(keyShort) > 8 {
		keyShort = keyShort[:8]
	}
	headerHTML := fmt.Sprintf(
		`<div class="hdr">`+
			`<div class="hdr-logo">%s</div>`+
			`<div class="hdr-sep"></div>`+
			`<div class="hdr-kpi">`+
			`<div class="hdr-kpi-item"><span class="hdr-kpi-label">Events</span><span class="hdr-kpi-val">%d</span></div>`+
			`<div class="hdr-kpi-item"><span class="hdr-kpi-label">OK</span><span class="hdr-kpi-val">%d</span></div>`+
			`<div class="hdr-kpi-item"><span class="hdr-kpi-label">Denied</span><span class="hdr-kpi-val">%d</span></div>`+
			`<div class="hdr-kpi-item"><span class="hdr-kpi-label">Rate</span><span class="hdr-kpi-val">%d</span></div>`+
			`</div>`+
			`<div class="hdr-spacer"></div>`+
			`<span class="hdr-badge">%s…</span>`+
			`<div class="hdr-toggle">`+
			`<button data-theme="dark" onclick="setTheme('dark')">Dark</button>`+
			`<button data-theme="light" onclick="setTheme('light')">Light</button>`+
			`</div>`+
			`</div>`,
		string(logoSVG),
		totalEvents, okCount, errCount, rateCount,
		html.EscapeString(keyShort))

	// ── Build filter bar ──
	apiKeyIDValue := ""
	if filters.APIKeyID != nil {
		apiKeyIDValue = *filters.APIKeyID
	}
	toolNameValue := ""
	if filters.ToolName != nil {
		toolNameValue = *filters.ToolName
	}
	filterBarHTML := fmt.Sprintf(
		`<form class="fbar" method="get" action="/dashboard">`+
			`<label>Key</label>`+
			`<input type="text" name="api_key_id" placeholder="uuid…" value="%s">`+
			`<label>Tool</label>`+
			`<input type="text" name="tool_name" placeholder="tool…" value="%s">`+
			`<label>Limit</label>`+
			`<input type="number" class="narrow" min="1" max="%d" name="limit" value="%d">`+
			`<button type="submit" class="fbar-btn">Filter</button>`+
			`<div class="fbar-sep"></div>`+
			`<div class="fbar-toggle"><input type="checkbox" id="toggle-row-color" checked><span class="sw" onclick="this.previousElementSibling.click()"></span><label for="toggle-row-color">Row color</label></div>`+
			`<div class="fbar-sep"></div>`+
			`<label>Refresh</label>`+
			`<select id="auto-refresh" class="fbar-select">`+
			`<option value="0">Off</option>`+
			`<option value="5">5s</option>`+
			`<option value="10">10s</option>`+
			`<option value="30">30s</option>`+
			`<option value="60">60s</option>`+
			`</select>`+
			`<div class="fbar-sep"></div>`+
			`<div class="fbar-toggle"><input type="checkbox" id="toggle-density" checked><span class="sw" onclick="this.previousElementSibling.click()"></span><label for="toggle-density">Compact</label></div>`+
			`<span class="fbar-spacer"></span>`+
			`<button type="button" class="fbar-icon-btn" id="btn-col-vis" title="Column visibility">⚙</button>`+
			`<button type="button" class="fbar-icon-btn" id="btn-export-csv" title="Export CSV">↓csv</button>`+
			`<button type="button" class="fbar-icon-btn" id="btn-export-json" title="Export JSON">↓json</button>`+
			`<button type="button" class="fbar-icon-btn" id="btn-kbd-help" title="Keyboard shortcuts (?)">?</button>`+
			`<a href="%s" class="fbar-link">API</a>`+
			`</form>`+
			`<div id="col-vis-menu" class="col-vis-menu" style="display:none"></div>`,
		html.EscapeString(apiKeyIDValue),
		html.EscapeString(toolNameValue),
		maxEventLimit,
		filters.Limit,
		html.EscapeString(apiHref))

	// ── Build rows (with row-level status class + data attrs for sorting + hidden detail JSON) ──
	rows := ""
	for i, e := range events {
		decisionJSON, _ := json.Marshal(e.Decision)
		requestJSON, _ := json.Marshal(e.Request)
		responseJSON, _ := json.Marshal(e.Response)

		// Build detail object for row expansion
		detail := map[string]any{
			"decision": e.Decision,
			"request":  e.Request,
			"response": e.Response,
		}
		detailJSON, _ := json.Marshal(detail)

		stClass := "st-other"
		rowClass := ""
		if e.Status >= 200 && e.Status <= 299 {
			stClass = "st-ok"
			rowClass = "row-ok"
		} else if e.Status == 401 || e.Status == 403 {
			stClass = "st-auth"
			rowClass = "row-auth"
		} else if e.Status == 429 {
			stClass = "st-rate"
			rowClass = "row-rate"
		} else if e.Status >= 500 {
			stClass = "st-err"
			rowClass = "row-err"
		}

		_ = requestJSON
		_ = responseJSON

		rows += fmt.Sprintf(
			`<tr class="%s" data-idx="%d" data-ts="%s" data-status="%d" data-latency="%d" data-key="%s" data-role="%s" data-method="%s" data-tool="%s">`+
				`<td class="ts">%s</td>`+
				`<td class="key">%s</td>`+
				`<td class="role">%s</td>`+
				`<td class="method">%s</td>`+
				`<td class="tool">%s</td>`+
				`<td><span class="st %s">%d</span></td>`+
				`<td class="lat">%dms</td>`+
				`<td class="dec" title="%s">%s</td>`+
				`<td class="detail-json" style="display:none">%s</td>`+
				`</tr>`,
			rowClass, i,
			html.EscapeString(e.TS), e.Status, e.LatencyMS,
			html.EscapeString(deref(e.APIKeyID)),
			html.EscapeString(displayRole(e.Role)),
			html.EscapeString(e.Method),
			html.EscapeString(e.ToolName),
			html.EscapeString(e.TS),
			html.EscapeString(deref(e.APIKeyID)),
			html.EscapeString(displayRole(e.Role)),
			html.EscapeString(e.Method),
			html.EscapeString(e.ToolName),
			stClass, e.Status,
			e.LatencyMS,
			html.EscapeString(string(decisionJSON)),
			html.EscapeString(string(decisionJSON)),
			html.EscapeString(string(detailJSON)))
	}
	if rows == "" {
		rows = `<tr><td colspan="8" class="empty">No audit events match the current filters.</td></tr>`
	}

	// ── Footer ──
	footerHTML := fmt.Sprintf(
		`<div class="ftr">`+
			`<span>%d events loaded</span>`+
			`<span>Bansho Security Gateway</span>`+
			`</div>`,
		totalEvents)

	// ── Execute template ──
	tmplData, _ := uiFS.ReadFile("dashboard.html")
	tmpl, err := template.New("dashboard").Parse(string(tmplData))
	if err != nil {
		return fmt.Sprintf("template error: %v", err)
	}

	var buf bytes.Buffer
	err = tmpl.Execute(&buf, templateData{
		HeaderHTML:    template.HTML(headerHTML),
		FilterBarHTML: template.HTML(filterBarHTML),
		RowsHTML:      template.HTML(rows),
		FooterHTML:    template.HTML(footerHTML),
	})
	if err != nil {
		return fmt.Sprintf("render error: %v", err)
	}
	return buf.String()
}

func deref(v *string) string {
	if v == nil {
		return ""
	}
	return *v
}

// displayRole formats internal role names for human display.
func displayRole(role string) string {
	switch strings.ToLower(strings.TrimSpace(role)) {
	case "readonly":
		return "Read-only"
	default:
		if role == "" {
			return ""
		}
		// Capitalize first letter
		return strings.ToUpper(role[:1]) + role[1:]
	}
}
