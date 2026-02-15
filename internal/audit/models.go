package audit

import (
	"encoding/json"
	"fmt"
	"math"
	"strings"
	"time"
)

const (
	MaxJSONBytes       = 4096
	MaxJSONDepth       = 6
	MaxJSONItems       = 40
	MaxJSONKeyChars    = 64
	MaxJSONStringChars = 512

	RedactedValue  = "[REDACTED]"
	TruncatedValue = "[TRUNCATED]"
)

var sensitiveKeys = map[string]struct{}{
	"api_key":        {},
	"authorization":  {},
	"password":       {},
	"secret":         {},
	"token":          {},
	"x-api-key":      {},
	"x_api_key":      {},
	"xapikey":        {},
	"x-api-key-id":   {},
	"x_api_key_id":   {},
	"x-api-keyid":    {},
	"x_api_keyid":    {},
	"x-api-key_hash": {},
}

type Event struct {
	TS         time.Time
	APIKeyID   *string
	Role       string
	Method     string
	ToolName   string
	Request    any
	Response   any
	Decision   any
	StatusCode int
	LatencyMS  int
}

type InsertValues struct {
	TS           time.Time
	APIKeyID     *string
	Role         string
	Method       string
	ToolName     string
	RequestJSON  string
	ResponseJSON string
	DecisionJSON string
	StatusCode   int
	LatencyMS    int
}

func (e Event) NormalizeAndBound() (InsertValues, error) {
	role := normalizeTextOr(e.Role, "unknown")
	method := strings.ToUpper(strings.TrimSpace(e.Method))
	if method == "" {
		return InsertValues{}, fmt.Errorf("method must be a non-empty string")
	}
	tool := strings.TrimSpace(e.ToolName)
	if tool == "" {
		return InsertValues{}, fmt.Errorf("tool_name must be a non-empty string")
	}
	if e.StatusCode < 0 || e.StatusCode > 999 {
		return InsertValues{}, fmt.Errorf("status_code must be between 0 and 999")
	}
	if e.LatencyMS < 0 {
		return InsertValues{}, fmt.Errorf("latency_ms must be >= 0")
	}

	apiKeyID := normalizeOptionalText(e.APIKeyID)
	request := boundJSONPayload(e.Request)
	response := boundJSONPayload(e.Response)
	decision := boundJSONPayload(e.Decision)

	requestJSON := serializeJSON(request)
	responseJSON := serializeJSON(response)
	decisionJSON := serializeJSON(decision)

	ts := e.TS
	if ts.IsZero() {
		ts = time.Now().UTC()
	}

	return InsertValues{
		TS:           ts,
		APIKeyID:     apiKeyID,
		Role:         role,
		Method:       method,
		ToolName:     tool,
		RequestJSON:  requestJSON,
		ResponseJSON: responseJSON,
		DecisionJSON: decisionJSON,
		StatusCode:   e.StatusCode,
		LatencyMS:    e.LatencyMS,
	}, nil
}

func normalizeOptionalText(value *string) *string {
	if value == nil {
		return nil
	}
	n := strings.TrimSpace(*value)
	if n == "" {
		return nil
	}
	n = truncateText(n, MaxJSONStringChars)
	return &n
}

func normalizeTextOr(value string, fallback string) string {
	n := strings.TrimSpace(value)
	if n == "" {
		return fallback
	}
	return truncateText(n, MaxJSONStringChars)
}

func boundJSONPayload(value any) any {
	sanitized := sanitizeJSONValue(value, 0)
	encoded := serializeJSON(sanitized)
	if len([]byte(encoded)) <= MaxJSONBytes {
		return sanitized
	}
	previewChars := MaxJSONBytes / 2
	if previewChars < 1 {
		previewChars = 1
	}
	if previewChars > MaxJSONStringChars {
		previewChars = MaxJSONStringChars
	}
	return map[string]any{
		"truncated":      true,
		"original_bytes": len([]byte(encoded)),
		"preview":        truncateText(encoded, previewChars),
	}
}

func sanitizeJSONValue(value any, depth int) any {
	if depth >= MaxJSONDepth {
		return TruncatedValue
	}
	if value == nil {
		return nil
	}

	switch v := value.(type) {
	case bool:
		return v
	case int:
		return v
	case int64:
		return v
	case float64:
		if math.IsInf(v, 0) || math.IsNaN(v) {
			return truncateText(fmt.Sprintf("%v", v), MaxJSONStringChars)
		}
		return v
	case string:
		return truncateText(v, MaxJSONStringChars)
	case []byte:
		return truncateText(string(v), MaxJSONStringChars)
	case map[string]any:
		return sanitizeMap(v, depth)
	case map[any]any:
		converted := map[string]any{}
		for k2, v2 := range v {
			converted[fmt.Sprintf("%v", k2)] = v2
		}
		return sanitizeMap(converted, depth)
	case []any:
		return sanitizeList(v, depth)
	default:
		// Try best-effort JSON marshal; if it works, sanitize again from decoded representation.
		b, err := json.Marshal(value)
		if err == nil {
			var decoded any
			if err := json.Unmarshal(b, &decoded); err == nil {
				return sanitizeJSONValue(decoded, depth+1)
			}
		}
		return truncateText(fmt.Sprintf("%#v", value), MaxJSONStringChars)
	}
}

func sanitizeMap(m map[string]any, depth int) any {
	out := map[string]any{}
	count := 0
	for k, v := range m {
		if count >= MaxJSONItems {
			out["_truncated_items"] = fmt.Sprintf("%d omitted", len(m)-MaxJSONItems)
			break
		}
		count++

		keyText := truncateText(fmt.Sprintf("%v", k), MaxJSONKeyChars)
		if _, ok := sensitiveKeys[strings.ToLower(keyText)]; ok {
			out[keyText] = RedactedValue
			continue
		}
		out[keyText] = sanitizeJSONValue(v, depth+1)
	}
	return out
}

func sanitizeList(values []any, depth int) any {
	out := make([]any, 0, minInt(len(values), MaxJSONItems))
	for i, item := range values {
		if i >= MaxJSONItems {
			out = append(out, TruncatedValue)
			break
		}
		out = append(out, sanitizeJSONValue(item, depth+1))
	}
	return out
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func truncateText(text string, maxChars int) string {
	if maxChars <= 0 {
		return ""
	}
	if len(text) <= maxChars {
		return text
	}
	marker := "..."
	if maxChars <= len(marker) {
		return marker[:maxChars]
	}
	return text[:maxChars-len(marker)] + marker
}

func serializeJSON(value any) string {
	b, err := json.Marshal(value)
	if err == nil {
		return string(b)
	}
	preview := truncateText(fmt.Sprintf("%#v", value), MaxJSONStringChars)
	fallback, _ := json.Marshal(map[string]any{
		"unserializable": true,
		"preview":        preview,
	})
	return string(fallback)
}
