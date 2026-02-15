package audit

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5/pgxpool"
)

type Logger struct {
	Pool *pgxpool.Pool
}

func (l *Logger) LogEvent(ctx context.Context, event Event) error {
	if l == nil || l.Pool == nil {
		return fmt.Errorf("audit logger is not configured")
	}
	values, err := event.NormalizeAndBound()
	if err != nil {
		return err
	}

	// Preserve the python behavior: if api_key_id is not a valid UUID, store NULL.
	var apiKeyID any = nil
	if values.APIKeyID != nil {
		if parsed, err := uuid.Parse(*values.APIKeyID); err == nil {
			apiKeyID = parsed
		}
	}

	_, err = l.Pool.Exec(ctx, `
		INSERT INTO audit_events (
			id, ts, api_key_id, role, method, tool_name,
			request_json, response_json, decision,
			status_code, latency_ms
		) VALUES (
			$1, $2, $3, $4, $5, $6,
			$7::jsonb, $8::jsonb, $9::jsonb,
			$10, $11
		);
	`, uuid.New(), values.TS, apiKeyID, values.Role, values.Method, values.ToolName,
		values.RequestJSON, values.ResponseJSON, values.DecisionJSON,
		values.StatusCode, values.LatencyMS,
	)
	return err
}

type RecentEvent struct {
	TS        string         `json:"ts"`
	APIKeyID  *string        `json:"api_key_id"`
	Role      string         `json:"role"`
	Method    string         `json:"method"`
	ToolName  string         `json:"tool_name"`
	Status    int            `json:"status_code"`
	LatencyMS int            `json:"latency_ms"`
	Decision  map[string]any `json:"decision"`
	Request   map[string]any `json:"request_json"`
	Response  map[string]any `json:"response_json"`
}

type RecentQuery struct {
	Limit    int
	APIKeyID *string
	ToolName *string
}

func (l *Logger) FetchRecentEvents(ctx context.Context, q RecentQuery) ([]RecentEvent, error) {
	if l == nil || l.Pool == nil {
		return nil, fmt.Errorf("audit logger is not configured")
	}
	limit := q.Limit
	if limit <= 0 {
		limit = 50
	}
	if limit > 200 {
		limit = 200
	}

	conditions := ""
	args := []any{}
	arg := func(v any) string {
		args = append(args, v)
		return fmt.Sprintf("$%d", len(args))
	}

	if q.APIKeyID != nil {
		conditions += " AND api_key_id::text = " + arg(*q.APIKeyID)
	}
	if q.ToolName != nil {
		conditions += " AND tool_name = " + arg(*q.ToolName)
	}
	limitPlaceholder := arg(limit)

	sql := `
		SELECT
			ts,
			api_key_id::text AS api_key_id,
			role,
			method,
			tool_name,
			status_code,
			latency_ms,
			decision,
			request_json,
			response_json
		FROM audit_events
		WHERE 1=1` + conditions + `
		ORDER BY ts DESC
		LIMIT ` + limitPlaceholder + `;
	`

	rows, err := l.Pool.Query(ctx, sql, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []RecentEvent
	for rows.Next() {
		var (
			ts          time.Time
			apiKeyID    *string
			role        string
			method      string
			tool        string
			status      int
			latency     int
			decisionRaw []byte
			requestRaw  []byte
			responseRaw []byte
		)
		if err := rows.Scan(&ts, &apiKeyID, &role, &method, &tool, &status, &latency, &decisionRaw, &requestRaw, &responseRaw); err != nil {
			return nil, err
		}

		decision := map[string]any{}
		_ = json.Unmarshal(decisionRaw, &decision)
		request := map[string]any{}
		_ = json.Unmarshal(requestRaw, &request)
		response := map[string]any{}
		_ = json.Unmarshal(responseRaw, &response)

		tsStr := ts.UTC().Format(time.RFC3339Nano)
		out = append(out, RecentEvent{
			TS:        tsStr,
			APIKeyID:  apiKeyID,
			Role:      role,
			Method:    method,
			ToolName:  tool,
			Status:    status,
			LatencyMS: latency,
			Decision:  decision,
			Request:   request,
			Response:  response,
		})
	}
	if rows.Err() != nil {
		return nil, rows.Err()
	}
	return out, nil
}
