package proxy

import (
	"context"
	"fmt"
	"os/exec"
	"strings"

	"github.com/google/shlex"
	"github.com/microck/bansho/internal/config"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type Upstream struct {
	settings config.Settings
	client   *mcp.Client
	session  *mcp.ClientSession
}

func NewUpstream(settings config.Settings) *Upstream {
	return &Upstream{settings: settings}
}

func (u *Upstream) Connect(ctx context.Context) (*mcp.ClientSession, error) {
	if u.session != nil {
		return u.session, nil
	}
	if u.client == nil {
		u.client = mcp.NewClient(&mcp.Implementation{Name: "bansho-upstream"}, nil)
	}

	transport, err := u.buildTransport()
	if err != nil {
		return nil, err
	}
	session, err := u.client.Connect(ctx, transport, nil)
	if err != nil {
		return nil, err
	}
	u.session = session
	return u.session, nil
}

func (u *Upstream) Close() {
	if u.session != nil {
		_ = u.session.Close()
	}
	u.session = nil
}

func (u *Upstream) InitializeResult(ctx context.Context) (*mcp.InitializeResult, error) {
	session, err := u.Connect(ctx)
	if err != nil {
		return nil, err
	}
	init := session.InitializeResult()
	if init == nil {
		return nil, fmt.Errorf("upstream session missing initialize result")
	}
	return init, nil
}

func (u *Upstream) buildTransport() (mcp.Transport, error) {
	if u.settings.UpstreamTransport == config.UpstreamTransportHTTP {
		if strings.TrimSpace(u.settings.UpstreamURL) == "" {
			return nil, fmt.Errorf("UPSTREAM_URL is required when UPSTREAM_TRANSPORT=http")
		}
		return &mcp.StreamableClientTransport{Endpoint: u.settings.UpstreamURL}, nil
	}

	cmdText := strings.TrimSpace(u.settings.UpstreamCmd)
	if cmdText == "" {
		return nil, fmt.Errorf("UPSTREAM_CMD is required when UPSTREAM_TRANSPORT=stdio")
	}
	parts, err := shlex.Split(cmdText)
	if err != nil {
		return nil, fmt.Errorf("UPSTREAM_CMD parse failed: %w", err)
	}
	if len(parts) == 0 {
		return nil, fmt.Errorf("UPSTREAM_CMD is required when UPSTREAM_TRANSPORT=stdio")
	}
	cmd := exec.Command(parts[0], parts[1:]...)
	return &mcp.CommandTransport{Command: cmd}, nil
}
