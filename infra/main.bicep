// Bansho Azure Infrastructure
// Deploys Azure Cache for Redis, Azure Database for PostgreSQL, and App Service

@description('Location for all resources')
param location string = resourceGroup().location

@description('Environment name (dev, staging, prod)')
param environmentName string = 'dev'

@description('Unique suffix for resource names')
param uniqueSuffix string = uniqueString(resourceGroup().id)

// Variables
var redisName = 'bansho-redis-${environmentName}-${uniqueSuffix}'
var postgresName = 'bansho-postgres-${environmentName}-${uniqueSuffix}'
var appServicePlanName = 'bansho-plan-${environmentName}-${uniqueSuffix}'
var appServiceName = 'bansho-app-${environmentName}-${uniqueSuffix}'

// Azure Cache for Redis
resource redis 'Microsoft.Cache/redis@2023-08-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

// Azure Database for PostgreSQL Flexible Server
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: postgresName
  location: location
  sku: {
    name: 'Standard_B1ms'
    tier: 'Burstable'
  }
  properties: {
    version: '16'
    administratorLogin: 'bansho'
    administratorLoginPassword: 'BanshoSecure123!' // Change in production
    storage: {
      storageSizeGB: 32
    }
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: {
      mode: 'Disabled'
    }
  }
}

// PostgreSQL Database
resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  parent: postgres
  name: 'bansho'
  properties: {
    charset: 'UTF8'
    collation: 'en_US.utf8'
  }
}

// PostgreSQL Firewall Rule (allow Azure services)
resource postgresFirewall 'Microsoft.DBforPostgreSQL/flexibleServers/firewallRules@2023-03-01-preview' = {
  parent: postgres
  name: 'AllowAzureServices'
  properties: {
    startIpAddress: '0.0.0.0'
    endIpAddress: '0.0.0.0'
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  sku: {
    name: 'B1'
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true
  }
}

// App Service (for hosting Bansho)
resource appService 'Microsoft.Web/sites@2023-01-01' = {
  name: appServiceName
  location: location
  kind: 'app,linux,container'
  properties: {
    serverFarmId: appServicePlan.id
    siteConfig: {
      linuxFxVersion: 'DOCKER|ghcr.io/microck/bansho:latest'
      appSettings: [
        {
          name: 'POSTGRES_DSN'
          value: 'postgresql://bansho:BanshoSecure123!@${postgres.properties.fullyQualifiedDomainName}:5432/bansho?sslmode=require'
        }
        {
          name: 'REDIS_URL'
          value: 'rediss://:${redis.listKeys().primaryKey}@${redis.properties.hostName}:6380/0?ssl=true'
        }
        {
          name: 'BANSHO_LISTEN_HOST'
          value: '0.0.0.0'
        }
        {
          name: 'BANSHO_LISTEN_PORT'
          value: '8080'
        }
        {
          name: 'UPSTREAM_TRANSPORT'
          value: 'http'
        }
      ]
      alwaysOn: true
    }
    httpsOnly: true
  }
}

// Outputs
output redisHostName string = redis.properties.hostName
output redisPrimaryKey string = redis.listKeys().primaryKey
output postgresHostName string = postgres.properties.fullyQualifiedDomainName
output appServiceUrl string = 'https://${appService.properties.defaultHostName}'
output appServiceName string = appService.name
