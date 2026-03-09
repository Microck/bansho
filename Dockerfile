# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /build

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source
COPY . .

# Build binary
RUN CGO_ENABLED=0 GOOS=linux go build -o bansho ./cmd/bansho

# Runtime stage
FROM alpine:3.19

# Install ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy binary from builder
COPY --from=builder /build/bansho .

# Copy config files
COPY config/ ./config/

# Expose port
EXPOSE 8080

# Run as non-root
RUN adduser -D -u 1000 bansho && \
    chown -R bansho:bansho /app
USER bansho

ENTRYPOINT ["./bansho", "serve"]
