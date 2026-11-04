# Authentication

Secure FastMCP servers with OAuth, bearer tokens, and JWT verification.

## Contents
- Overview
- Bearer Token Authentication
- OAuth Providers
- Provider Configuration
- Token Verification
- Production Configuration

## Overview

FastMCP supports multiple authentication methods:

1. **Bearer Token** - Simple token validation
2. **OAuth Proxy** - Bridge traditional OAuth with MCP
3. **Remote OAuth** - Use external OAuth providers

## Bearer Token Authentication

```python
from fastmcp import FastMCP
from fastmcp.server.auth import BearerTokenAuth

auth = BearerTokenAuth(token="your-secret-token")
mcp = FastMCP("Protected Server", auth=auth)
```

### Environment Variables

```python
import os
from fastmcp.server.auth import BearerTokenAuth

auth = BearerTokenAuth(token=os.environ["MCP_AUTH_TOKEN"])
mcp = FastMCP("Protected Server", auth=auth)
```

## OAuth Providers

### GitHub

```python
from fastmcp.server.auth.providers.github import GitHubProvider

auth = GitHubProvider(
    client_id="Ov23liAbcDefGhiJkLmN",
    client_secret="github_pat_...",
    base_url="http://localhost:8000",
)

mcp = FastMCP("GitHub Secured App", auth=auth)
```

**Setup:**
1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App
3. Set callback URL: `http://localhost:8000/auth/callback`
4. Note Client ID and Client Secret

### Google

```python
from fastmcp.server.auth.providers.google import GoogleProvider

auth = GoogleProvider(
    client_id="123456789.apps.googleusercontent.com",
    client_secret="GOCSPX-abc123...",
    base_url="http://localhost:8000",
    required_scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],
)

mcp = FastMCP("Google Secured App", auth=auth)
```

**Setup:**
1. Go to Google Cloud Console → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: `http://localhost:8000/auth/callback`

### Auth0

```python
from fastmcp.server.auth.providers.auth0 import Auth0Provider

auth = Auth0Provider(
    config_url="https://YOUR_DOMAIN/.well-known/openid-configuration",
    client_id="tv2ObNgaZAWWhhycr7Bz1LU2mxlnsmsB",
    client_secret="vPYqbjemq...",
    audience="https://your-api",
    base_url="http://localhost:8000",
)

mcp = FastMCP("Auth0 Secured App", auth=auth)
```

### AWS Cognito

```python
from fastmcp.server.auth.providers.aws import AWSCognitoProvider

auth = AWSCognitoProvider(
    user_pool_id="eu-central-1_XXXXXXXXX",
    aws_region="eu-central-1",
    client_id="your-app-client-id",
    client_secret="your-app-client-secret",
    base_url="http://localhost:8000",
)

mcp = FastMCP("AWS Cognito Secured App", auth=auth)
```

**Setup:**
1. Create User Pool in AWS Cognito
2. Create App Client (Traditional web application)
3. Configure callback URL
4. Create resource server with your MCP endpoint URL

### Azure (Microsoft Entra ID)

```python
from fastmcp.server.auth.providers.azure import AzureProvider

auth = AzureProvider(
    client_id="835f09b6-0f0f-40cc-85cb-f32c5829a149",
    client_secret="your-client-secret",
    tenant_id="08541b6e-646d-43de-a0eb-834e6713d6d5",
    base_url="http://localhost:8000",
    required_scopes=["mcp-access"],
    additional_authorize_scopes=["User.Read"],
)

mcp = FastMCP("Azure Secured App", auth=auth)
```

**Setup:**
1. Register app in Azure Portal → Microsoft Entra ID → App registrations
2. Set redirect URI: `http://localhost:8000/auth/callback`
3. Configure Expose an API scopes
4. Set `requestedAccessTokenVersion` to 2 in Manifest

### Azure OBO (On-Behalf-Of)

```python
from fastmcp.server.auth.providers.azure import AzureProvider, EntraOBOToken
import httpx

auth = AzureProvider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    tenant_id="your-tenant-id",
    base_url="http://localhost:8000",
    required_scopes=["mcp-access"],
    additional_authorize_scopes=[
        "https://graph.microsoft.com/Mail.Read",
        "https://graph.microsoft.com/User.Read",
    ],
)

mcp = FastMCP("Email Reader", auth=auth)

@mcp.tool
async def get_emails(
    graph_token: str = EntraOBOToken(["https://graph.microsoft.com/Mail.Read"]),
) -> list[dict]:
    """Get recent emails from Microsoft Graph."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.microsoft.com/v1.0/me/messages?$top=10",
            headers={"Authorization": f"Bearer {graph_token}"},
        )
        return response.json().get("value", [])
```

### Discord

```python
from fastmcp.server.auth.providers.discord import DiscordProvider

auth = DiscordProvider(
    client_id="12345",
    client_secret="your-client-secret",
    base_url="http://localhost:8000",
    required_scopes=["identify", "email"],
)

mcp = FastMCP("Discord Secured App", auth=auth)
```

### WorkOS AuthKit

```python
from fastmcp.server.auth.providers.workos import AuthKitProvider

auth = AuthKitProvider(
    authkit_domain="https://your-project-12345.authkit.app",
    base_url="http://localhost:8000",
)

mcp = FastMCP("AuthKit Secured App", auth=auth)
```

### Descope

```python
from fastmcp.server.auth.providers.descope import DescopeProvider

auth = DescopeProvider(
    config_url="https://.../.well-known/openid-configuration",
    base_url="http://localhost:8000",
)

mcp = FastMCP("Descope Protected Server", auth=auth)
```

## JWT Verification

For cases where you only need to validate incoming tokens:

```python
from fastmcp import FastMCP
from fastmcp.server.auth import RemoteAuthProvider
from fastmcp.server.auth.providers.azure import AzureJWTVerifier
from pydantic import AnyHttpUrl

verifier = AzureJWTVerifier(
    client_id="your-client-id",
    tenant_id="your-tenant-id",
    required_scopes=["access_as_user"],
)

auth = RemoteAuthProvider(
    token_verifier=verifier,
    authorization_servers=[
        AnyHttpUrl(f"https://login.microsoftonline.com/{tenant_id}/v2.0")
    ],
    base_url="https://your-server.com",
)

mcp = FastMCP("Azure MI App", auth=auth)
```

## Accessing User Info in Tools

```python
from fastmcp.server.dependencies import get_access_token

@mcp.tool
async def get_user_info() -> dict:
    """Get the authenticated user's information."""
    token = get_access_token()
    return {
        "user_id": token.claims.get("sub"),
        "email": token.claims.get("email"),
        "name": token.claims.get("name"),
    }
```

## Provider Parameters

### Common Parameters

| Parameter | Description |
|-----------|-------------|
| `client_id` | OAuth client identifier |
| `client_secret` | OAuth client secret |
| `base_url` | Your server's URL |
| `required_scopes` | Scopes required for access |
| `redirect_path` | Callback path (default: `/auth/callback`) |

### Production Parameters

| Parameter | Description |
|-----------|-------------|
| `jwt_signing_key` | Key for signing tokens issued to clients |
| `client_storage` | Storage backend for OAuth tokens |

## Production Configuration

**Critical**: Configure persistent token storage for production:

```python
import os
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url="https://your-server.com",
    
    # Production token management
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    client_storage=FernetEncryptionWrapper(
        key_value=RedisStore(
            host=os.environ["REDIS_HOST"],
            port=int(os.environ["REDIS_PORT"])
        ),
        fernet=Fernet(os.environ["STORAGE_ENCRYPTION_KEY"])
    )
)

mcp = FastMCP("Production Server", auth=auth)
```

**Requirements:**
1. **jwt_signing_key** - For signing tokens issued to clients
2. **client_storage** with encryption - For persisting OAuth tokens

Wrap storage in `FernetEncryptionWrapper` to encrypt tokens at rest.

## Testing Authentication

```python
from fastmcp import Client
from fastmcp.client.auth import OAuth

async def test():
    async with Client("http://localhost:8000/mcp", auth="oauth") as client:
        result = await client.call_tool("get_user_info")
        print(f"User: {result['email']}")

# First run: browser opens for OAuth login
# Subsequent runs: uses cached tokens
```
