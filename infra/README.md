# Bansho Azure Infrastructure

This directory contains Azure deployment templates for Bansho.

## What Gets Deployed

- **Azure Cache for Redis** - Replaces local Redis for rate limiting
- **Azure Database for PostgreSQL Flexible Server** - Replaces local PostgreSQL for API keys and audit logs
- **Azure App Service** - Hosts the Bansho gateway container

## Prerequisites

- Azure CLI (`az`)
- Azure subscription
- Docker (for building container image)

## Deployment Steps

### 1. Login to Azure

```bash
az login
az account set --subscription <your-subscription-id>
```

### 2. Create Resource Group

```bash
az group create \
  --name bansho-rg \
  --location eastus
```

### 3. Deploy Infrastructure

```bash
az deployment group create \
  --resource-group bansho-rg \
  --template-file infra/main.bicep \
  --parameters environmentName=prod
```

This will output:
- `redisHostName` - Azure Cache for Redis hostname
- `postgresHostName` - Azure Database for PostgreSQL hostname
- `appServiceUrl` - Your deployed Bansho gateway URL

### 4. Initialize Database Schema

The PostgreSQL database needs the `api_keys` and `audit_events` tables. Run the schema initialization:

```bash
# Get connection string from deployment outputs
POSTGRES_HOST=$(az deployment group show \
  --resource-group bansho-rg \
  --name main \
  --query properties.outputs.postgresHostName.value -o tsv)

# Connect and run schema
psql "postgresql://bansho:BanshoSecure123!@${POSTGRES_HOST}:5432/bansho?sslmode=require" \
  -f internal/storage/schema.sql
```

### 5. Build and Push Container

```bash
# Build container
docker build -t ghcr.io/microck/bansho:latest .

# Push to GitHub Container Registry
docker push ghcr.io/microck/bansho:latest
```

### 6. Restart App Service

```bash
az webapp restart \
  --resource-group bansho-rg \
  --name $(az deployment group show \
    --resource-group bansho-rg \
    --name main \
    --query properties.outputs.appServiceName.value -o tsv)
```

## Environment Variables

The deployment automatically configures:

| Variable | Value |
|----------|-------|
| `POSTGRES_DSN` | Azure Database for PostgreSQL connection string with SSL |
| `REDIS_URL` | Azure Cache for Redis connection string with TLS |
| `BANSHO_LISTEN_HOST` | `0.0.0.0` |
| `BANSHO_LISTEN_PORT` | `8080` |
| `UPSTREAM_TRANSPORT` | `http` (configure via App Service settings) |

## Cost Estimate

| Resource | SKU | Monthly Cost (USD) |
|----------|-----|-------------------|
| Azure Cache for Redis | Basic C0 | ~$16 |
| Azure Database for PostgreSQL | Burstable B1ms | ~$12 |
| App Service | Basic B1 | ~$13 |
| **Total** | | **~$41/month** |

## Security Notes

- PostgreSQL uses SSL/TLS by default (`sslmode=require`)
- Redis uses TLS by default (port 6380)
- App Service enforces HTTPS only
- Change the default PostgreSQL password in production
- Use Azure Key Vault for secrets in production deployments

## Cleanup

To delete all resources:

```bash
az group delete --name bansho-rg --yes --no-wait
```
