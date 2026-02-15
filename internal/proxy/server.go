package proxy

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"strings"
	"time"

	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/microck/bansho/internal/audit"
	"github.com/microck/bansho/internal/auth"
	"github.com/microck/bansho/internal/config"
	"github.com/microck/bansho/internal/policy"
	"github.com/microck/bansho/internal/ratelimit"
	"github.com/microck/bansho/internal/storage"
	"github.com/modelcontextprotocol/go-sdk/jsonrpc"
	"github.com/modelcontextprotocol/go-sdk/mcp"
	"github.com/redis/go-redis/v9"
)

const (
	unauthorizedMessage    = "Unauthorized"
	forbiddenMessage       = "Forbidden"
	tooManyRequestsMessage = "Too Many Requests"
	internalErrorMessage   = "Internal Server Error"
	upstreamFailureMessage = "Upstream request failed"
	notEvaluatedReason     = "not_evaluated"
	unknownRole            = "unknown"
	unknownToolName        = "__unknown_tool__"
)

type AuthContext struct {
	APIKeyID string
	Role     string
}

func RunStdioGateway(settings config.Settings) error {
	ctx := context.Background()

	policyPath := strings.TrimSpace(os.Getenv("BANSHO_POLICY_PATH"))
	if policyPath == "" {
		policyPath = policy.DefaultPolicyPath
	}
	pol, err := policy.LoadPolicy(policyPath)
	if err != nil {
		return err
	}

	pool, err := storage.GetPostgresPool(ctx, settings.PostgresDSN)
	if err != nil {
		return err
	}
	if err := storage.EnsureSchema(ctx, pool); err != nil {
		return err
	}

	redisClient, err := storage.GetRedisClient(settings.RedisURL)
	if err != nil {
		return err
	}
	if err := storage.PingRedis(ctx, redisClient); err != nil {
		return err
	}

	auditLogger := &audit.Logger{Pool: pool}
	upstream := NewUpstream(settings)
	defer upstream.Close()

	session, err := upstream.Connect(ctx)
	if err != nil {
		return err
	}
	init := session.InitializeResult()
	if init == nil {
		return fmt.Errorf("upstream initialize result missing")
	}

	upstreamTools, toolNameSet, err := fetchAllTools(ctx, session)
	if err != nil {
		return err
	}

	impl := &mcp.Implementation{Name: "bansho", Version: "dev"}
	if init.ServerInfo != nil {
		impl.Name = init.ServerInfo.Name
		impl.Version = init.ServerInfo.Version
	}

	opts := &mcp.ServerOptions{
		Instructions: init.Instructions,
		Capabilities: init.Capabilities,
	}
	server := mcp.NewServer(impl, opts)

	g := &gateway{
		settings:    settings,
		policy:      pol,
		auditLogger: auditLogger,
		pool:        pool,
		redis:       redisClient,
		upstream:    session,
		knownTools:  toolNameSet,
		policyPath:  policyPath,
	}

	for _, tool := range upstreamTools {
		name := tool.Name
		server.AddTool(tool, g.makeToolHandler(name))
	}
	server.AddReceivingMiddleware(g.middleware())

	fmt.Fprintf(os.Stderr,
		"bansho_proxy_start listen_addr=%s:%d upstream_transport=%s upstream_target=%s policy_path=%s\n",
		settings.BanshoListenHost,
		settings.BanshoListenPort,
		settings.UpstreamTransport,
		upstreamTarget(settings),
		policyPath,
	)

	return server.Run(ctx, &mcp.StdioTransport{})
}

func upstreamTarget(settings config.Settings) string {
	if settings.UpstreamTransport == config.UpstreamTransportHTTP {
		return settings.UpstreamURL
	}
	return settings.UpstreamCmd
}

type gateway struct {
	settings    config.Settings
	policy      policy.Policy
	auditLogger *audit.Logger
	pool        *pgxpool.Pool
	redis       *redis.Client
	upstream    *mcp.ClientSession
	knownTools  map[string]struct{}
	policyPath  string
}

func (g *gateway) middleware() mcp.Middleware {
	return func(next mcp.MethodHandler) mcp.MethodHandler {
		return func(ctx context.Context, method string, req mcp.Request) (mcp.Result, error) {
			switch method {
			case "tools/list":
				listReq, ok := req.(*mcp.ListToolsRequest)
				if !ok {
					return nil, &jsonrpc.Error{Code: 500, Message: internalErrorMessage}
				}
				authCtx, err := g.authenticate(ctx, listReq.Extra, metaFromParams(listReq.Params))
				if err != nil {
					return nil, err
				}
				res, err := next(ctx, method, req)
				if err != nil {
					return nil, err
				}
				listRes, ok := res.(*mcp.ListToolsResult)
				if !ok {
					return nil, &jsonrpc.Error{Code: 500, Message: internalErrorMessage}
				}
				filtered := make([]*mcp.Tool, 0, len(listRes.Tools))
				for _, t := range listRes.Tools {
					if t == nil {
						continue
					}
					if g.policy.IsToolAllowed(authCtx.Role, t.Name) {
						filtered = append(filtered, t)
					}
				}
				return &mcp.ListToolsResult{Tools: filtered, NextCursor: listRes.NextCursor}, nil
			case "resources/list":
				r2, ok := req.(*mcp.ListResourcesRequest)
				if !ok {
					return nil, &jsonrpc.Error{Code: 500, Message: internalErrorMessage}
				}
				params := r2.Params
				if params == nil {
					params = &mcp.ListResourcesParams{}
				}
				return g.upstream.ListResources(ctx, params)
			case "resources/read":
				r2, ok := req.(*mcp.ReadResourceRequest)
				if !ok {
					return nil, &jsonrpc.Error{Code: 500, Message: internalErrorMessage}
				}
				params := r2.Params
				if params == nil {
					params = &mcp.ReadResourceParams{}
				}
				return g.upstream.ReadResource(ctx, params)
			case "prompts/list":
				r2, ok := req.(*mcp.ListPromptsRequest)
				if !ok {
					return nil, &jsonrpc.Error{Code: 500, Message: internalErrorMessage}
				}
				params := r2.Params
				if params == nil {
					params = &mcp.ListPromptsParams{}
				}
				return g.upstream.ListPrompts(ctx, params)
			case "prompts/get":
				r2, ok := req.(*mcp.GetPromptRequest)
				if !ok {
					return nil, &jsonrpc.Error{Code: 500, Message: internalErrorMessage}
				}
				params := r2.Params
				if params == nil {
					params = &mcp.GetPromptParams{}
				}
				return g.upstream.GetPrompt(ctx, params)
			default:
				return next(ctx, method, req)
			}
		}
	}
}

func (g *gateway) makeToolHandler(toolName string) mcp.ToolHandler {
	return func(ctx context.Context, req *mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		started := time.Now()
		statusCode := int64(500)
		upstreamCalled := false

		decision := defaultDecisionPayload()
		var responseJSON any = safeErrorPayload(int(statusCode), internalErrorMessage)
		var authCtx *AuthContext

		defer func() {
			latencyMS := int(time.Since(started).Milliseconds())
			if latencyMS < 0 {
				latencyMS = 0
			}
			apiKeyID := (*string)(nil)
			role := unknownRole
			if authCtx != nil {
				apiKeyID = &authCtx.APIKeyID
				role = authCtx.Role
			}
			event := audit.Event{
				TS:         time.Now().UTC(),
				APIKeyID:   apiKeyID,
				Role:       role,
				Method:     "tools/call",
				ToolName:   toolName,
				Request:    map[string]any{"name": toolName, "arguments": rawArgs(req)},
				Response:   responseJSON,
				Decision:   decision,
				StatusCode: int(statusCode),
				LatencyMS:  latencyMS,
			}
			if err := g.auditLogger.LogEvent(context.Background(), event); err != nil {
				fmt.Fprintf(os.Stderr, "audit_log_failed method=%s tool=%s status=%d error_type=%T\n", event.Method, event.ToolName, event.StatusCode, err)
			}
		}()

		// Authentication
		authCtx, err := g.authenticate(ctx, req.Extra, metaFromParams(req.Params))
		if err != nil {
			if werr := asWireError(err); werr != nil {
				statusCode = werr.Code
				responseJSON = safeErrorPayload(int(statusCode), werr.Message)
				if statusCode == 401 {
					decision["auth"] = map[string]any{"allowed": false, "reason": "unauthorized"}
				}
			}
			return nil, err
		}
		decision["auth"] = map[string]any{"allowed": true, "api_key_id": authCtx.APIKeyID, "role": authCtx.Role}

		// Authorization
		authz := g.authorize(authCtx, toolName)
		decision["authz"] = authz
		if allowed, _ := authz["allowed"].(bool); !allowed {
			statusCode = 403
			responseJSON = safeErrorPayload(int(statusCode), forbiddenMessage)
			return nil, &jsonrpc.Error{Code: statusCode, Message: forbiddenMessage}
		}

		// Rate limiting
		rateDecision, err := g.enforceRateLimit(ctx, authCtx, toolName)
		if err != nil {
			statusCode = 429
			responseJSON = safeErrorPayload(int(statusCode), tooManyRequestsMessage)
			decision["rate"] = map[string]any{"allowed": false, "reason": "too_many_requests"}
			return nil, &jsonrpc.Error{Code: statusCode, Message: tooManyRequestsMessage}
		}
		decision["rate"] = rateDecision

		// Forward to upstream
		upstreamCalled = true
		args := map[string]any{}
		if req.Params != nil && len(req.Params.Arguments) > 0 {
			_ = json.Unmarshal(req.Params.Arguments, &args)
		}
		res, err := g.upstream.CallTool(ctx, &mcp.CallToolParams{Name: toolName, Arguments: args})
		if err != nil {
			statusCode = 502
			responseJSON = safeExceptionPayload(int(statusCode), err)
			if upstreamCalled {
				return nil, &jsonrpc.Error{Code: statusCode, Message: upstreamFailureMessage}
			}
			return nil, &jsonrpc.Error{Code: 500, Message: internalErrorMessage}
		}

		statusCode = 200
		responseJSON = res
		return res, nil
	}
}

func (g *gateway) authenticate(ctx context.Context, extra *mcp.RequestExtra, meta map[string]any) (*AuthContext, error) {
	presented := extractAPIKey(extra, meta)
	if presented == "" {
		return nil, &jsonrpc.Error{Code: 401, Message: unauthorizedMessage}
	}
	resolved, err := auth.ResolveAPIKey(ctx, g.pool, presented)
	if err != nil || resolved == nil {
		return nil, &jsonrpc.Error{Code: 401, Message: unauthorizedMessage}
	}
	return &AuthContext{APIKeyID: resolved.APIKeyID, Role: resolved.Role}, nil
}

func (g *gateway) authorize(authCtx *AuthContext, toolName string) map[string]any {
	role := strings.ToLower(strings.TrimSpace(authCtx.Role))
	normalizedTool := strings.TrimSpace(toolName)
	if normalizedTool == "" {
		return map[string]any{
			"allowed":      false,
			"role":         role,
			"reason":       "empty_tool_name",
			"matched_rule": "deny:empty_tool_name",
		}
	}
	rolePolicy := g.policy.Roles.ForRole(role)
	if rolePolicy == nil {
		return map[string]any{
			"allowed":      false,
			"role":         role,
			"reason":       "unknown_role",
			"matched_rule": "deny:unknown_role",
		}
	}
	if g.policy.IsToolAllowed(role, normalizedTool) {
		matched := normalizedTool
		if role == "admin" {
			for _, v := range rolePolicy.Allow {
				if v == policy.ToolWildcard {
					matched = policy.ToolWildcard
					break
				}
			}
		}
		return map[string]any{
			"allowed":      true,
			"role":         role,
			"reason":       "allowed",
			"matched_rule": fmt.Sprintf("roles.%s.allow:%s", role, matched),
		}
	}
	if _, ok := g.knownTools[normalizedTool]; !ok {
		return map[string]any{
			"allowed":      false,
			"role":         role,
			"reason":       "unknown_tool",
			"matched_rule": "deny:unknown_tool",
		}
	}
	return map[string]any{
		"allowed":      false,
		"role":         role,
		"reason":       "tool_not_allowed_for_role",
		"matched_rule": fmt.Sprintf("roles.%s.allow", role),
	}
}

func (g *gateway) enforceRateLimit(ctx context.Context, authCtx *AuthContext, toolName string) (map[string]any, error) {
	tool := strings.TrimSpace(toolName)
	if tool == "" {
		tool = unknownToolName
	}

	redisClient := g.redis
	if redisClient == nil {
		return nil, errors.New("redis client not configured")
	}
	perKey := g.policy.RateLimits.PerAPIKey
	perTool := g.policy.RateLimits.PerTool.ForTool(tool)

	perKeyRes, err := ratelimit.CheckAPIKeyLimit(ctx, redisClient, authCtx.APIKeyID, perKey.Requests, perKey.WindowSeconds, nil)
	if err != nil {
		return nil, err
	}
	if !perKeyRes.Allowed {
		return nil, errors.New("too_many_requests")
	}
	perToolRes, err := ratelimit.CheckToolLimit(ctx, redisClient, authCtx.APIKeyID, tool, perTool.Requests, perTool.WindowSeconds, nil)
	if err != nil {
		return nil, err
	}
	if !perToolRes.Allowed {
		return nil, errors.New("too_many_requests")
	}

	return map[string]any{
		"allowed":   true,
		"reason":    "within_limits",
		"tool_name": tool,
		"per_api_key": map[string]any{
			"allowed":   perKeyRes.Allowed,
			"remaining": perKeyRes.Remaining,
			"reset_s":   perKeyRes.ResetS,
		},
		"per_tool": map[string]any{
			"allowed":   perToolRes.Allowed,
			"remaining": perToolRes.Remaining,
			"reset_s":   perToolRes.ResetS,
		},
	}, nil
}

func fetchAllTools(ctx context.Context, session *mcp.ClientSession) ([]*mcp.Tool, map[string]struct{}, error) {
	toolByName := map[string]*mcp.Tool{}
	cursor := ""
	for {
		params := &mcp.ListToolsParams{Cursor: cursor}
		res, err := session.ListTools(ctx, params)
		if err != nil {
			return nil, nil, err
		}
		for _, t := range res.Tools {
			if t == nil {
				continue
			}
			toolByName[t.Name] = t
		}
		if res.NextCursor == "" {
			break
		}
		cursor = res.NextCursor
	}
	known := map[string]struct{}{}
	out := make([]*mcp.Tool, 0, len(toolByName))
	for name, t := range toolByName {
		known[name] = struct{}{}
		out = append(out, t)
	}
	return out, known, nil
}

func defaultDecisionPayload() map[string]any {
	return map[string]any{
		"auth": map[string]any{
			"allowed": false,
			"reason":  notEvaluatedReason,
		},
		"authz": map[string]any{
			"allowed": false,
			"reason":  notEvaluatedReason,
		},
		"rate": map[string]any{
			"allowed": false,
			"reason":  notEvaluatedReason,
		},
	}
}

func safeErrorPayload(code int, message string) map[string]any {
	return map[string]any{
		"error": map[string]any{
			"code":    code,
			"message": message,
		},
	}
}

func safeExceptionPayload(statusCode int, err error) map[string]any {
	message := internalErrorMessage
	if statusCode == 502 {
		message = upstreamFailureMessage
	}
	return map[string]any{
		"error": map[string]any{
			"code":    statusCode,
			"message": message,
			"type":    fmt.Sprintf("%T", err),
		},
	}
}

func rawArgs(req *mcp.CallToolRequest) map[string]any {
	out := map[string]any{}
	if req == nil || req.Params == nil || len(req.Params.Arguments) == 0 {
		return out
	}
	_ = json.Unmarshal(req.Params.Arguments, &out)
	return out
}

func metaFromParams(params any) map[string]any {
	if params == nil {
		return nil
	}
	if p, ok := params.(interface{ GetMeta() map[string]any }); ok {
		return p.GetMeta()
	}
	return nil
}

func extractAPIKey(extra *mcp.RequestExtra, meta map[string]any) string {
	headers := map[string]string{}

	if meta != nil {
		mergeStringMapping(headers, meta["headers"])
		mergeStringMapping(headers, meta["header"])
	}
	if extra != nil {
		for k, vv := range extra.Header {
			if len(vv) == 0 {
				continue
			}
			headers[strings.ToLower(strings.TrimSpace(k))] = strings.TrimSpace(vv[0])
		}
	}

	if bearer := extractBearer(headers["authorization"]); bearer != "" {
		return bearer
	}
	if v := strings.TrimSpace(headers["x-api-key"]); v != "" {
		return v
	}

	query := map[string]string{}
	if meta != nil {
		mergeStringMapping(query, meta["query"])
		mergeStringMapping(query, meta["query_params"])
	}
	if v := strings.TrimSpace(query["api_key"]); v != "" {
		return v
	}
	return ""
}

func extractBearer(authHeader string) string {
	n := strings.TrimSpace(authHeader)
	if n == "" {
		return ""
	}
	parts := strings.SplitN(n, " ", 2)
	if len(parts) != 2 {
		return ""
	}
	if strings.ToLower(parts[0]) != "bearer" {
		return ""
	}
	return strings.TrimSpace(parts[1])
}

func mergeStringMapping(target map[string]string, source any) {
	m, ok := source.(map[string]any)
	if !ok {
		return
	}
	for k, v := range m {
		vs, ok := v.(string)
		if !ok {
			continue
		}
		k2 := strings.ToLower(strings.TrimSpace(k))
		v2 := strings.TrimSpace(vs)
		if k2 == "" || v2 == "" {
			continue
		}
		target[k2] = v2
	}
}

func asWireError(err error) *jsonrpc.Error {
	var werr *jsonrpc.Error
	if errors.As(err, &werr) {
		return werr
	}
	return nil
}
