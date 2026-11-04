# Server Authentication

Secure your FastMCP server with authentication.

## Contents
- Authentication Patterns
- Token Verification
- OAuth Proxy
- Remote OAuth
- OIDC Proxy
- Full OAuth Server
- Multi-Auth
- Authorization

## Authentication Patterns

FastMCP supports three authentication responsibility levels:

### 1. Token Validation
Validate tokens created by external systems (simplest approach).

```python
from fastmcp.server.auth.providers.jwt import JWTVerifier

auth = JWTVerifier(
    jwks_uri="https://auth.example.com/.well-known/jwks.json",
    issuer="https://auth.example.com",
    audience="my-mcp-server"
)

mcp = FastMCP("Protected Server", auth=auth)
```

### 2. External Identity Providers
Coordinate with OAuth providers for seamless authentication.

```python
# DCR-supported providers (Descope, WorkOS AuthKit)
from fastmcp.server.auth.providers.workos import AuthKitProvider

auth = AuthKitProvider(
    authkit_domain="https://your-project.authkit.app",
    base_url="https://your-server.com"
)

# Non-DCR providers (GitHub, Google, Azure)
from fastmcp.server.auth.providers.github import GitHubProvider

auth = GitHubProvider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    base_url="https://your-server.com"
)
```

### 3. Full OAuth Implementation
Build a complete OAuth server (advanced, rarely needed).

## Token Verification

### JWTVerifier

Validate JWT tokens from known issuers:

```python
from fastmcp.server.auth.providers.jwt import JWTVerifier

auth = JWTVerifier(
    jwks_uri="https://auth.example.com/.well-known/jwks.json",
    issuer="https://auth.example.com",
    audience="my-mcp-server"
)
```

### Symmetric Key Verification (HMAC)

For internal microservices with shared secret:

```python
auth = JWTVerifier(
    public_key="your-shared-secret-min-32-chars",  # Despite parameter name
    issuer="internal-auth-service",
    audience="mcp-internal-api",
    algorithm="HS256"  # or HS384, HS512
)
```

### IntrospectionTokenVerifier

For opaque tokens via RFC 7662 introspection:

```python
from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier

auth = IntrospectionTokenVerifier(
    introspection_url="https://auth.example.com/oauth/introspect",
    client_id="mcp-resource-server",
    client_secret="your-client-secret",
    required_scopes=["api:read", "api:write"],
    client_auth_method="client_secret_basic"  # or "client_secret_post"
)
```

### StaticTokenVerifier

For development with fixed tokens:

```python
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

auth = StaticTokenVerifier(
    tokens={
        "dev-token-123": {"sub": "user1", "scopes": ["read", "write"]},
        "dev-token-456": {"sub": "user2", "scopes": ["read"]},
    }
)
```

### DebugTokenVerifier

For testing/prototyping with custom validation:

```python
from fastmcp.server.auth.providers.debug import DebugTokenVerifier

# Accept all tokens
auth = DebugTokenVerifier()

# Custom validation
auth = DebugTokenVerifier(
    validate=lambda token: token.startswith("dev-"),
    client_id="development-client",
    scopes=["read", "write"]
)

# Async validation
async def validate_token(token: str) -> bool:
    return await redis.exists(f"valid_tokens:{token}")

auth = DebugTokenValidator(validate=validate_token)
```

### RSAKeyPair (Development)

Generate keys for testing:

```python
from fastmcp.server.auth.providers.jwt import RSAKeyPair

key_pair = RSAKeyPair.generate()
access_token = key_pair.create_token(audience="my-server")

auth = JWTVerifier(
    public_key=key_pair.public_key,
    audience="my-server"
)
```

### HTTP Client Customization

For connection pooling and custom TLS:

```python
import httpx
from fastmcp.server.auth.providers.introspection import IntrospectionTokenVerifier

http_client = httpx.AsyncClient(
    timeout=10,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
)

auth = IntrospectionTokenVerifier(
    introspection_url="https://auth.example.com/introspect",
    client_id="my-service",
    client_secret="secret",
    http_client=http_client,
)
```

Note: When providing `http_client`, manage its lifecycle via server lifespan.

## OAuth Proxy

Bridge traditional OAuth providers (GitHub, Google, Azure, AWS) to work with MCP.

### Basic Setup

```python
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier

auth = OAuthProxy(
    # Provider's OAuth endpoints
    upstream_authorization_endpoint="https://github.com/login/oauth/authorize",
    upstream_token_endpoint="https://github.com/login/oauth/access_token",
    
    # Your registered app credentials
    upstream_client_id="your-client-id",
    upstream_client_secret="your-client-secret",
    
    # Token validation
    token_verifier=JWTVerifier(...),
    
    # Your server's public URL
    base_url="https://your-server.com"
)

mcp = FastMCP("My Server", auth=auth)
```

### OAuthProxy Parameters

| Parameter | Description |
|-----------|-------------|
| `upstream_authorization_endpoint` | Provider's authorization URL |
| `upstream_token_endpoint` | Provider's token URL |
| `upstream_client_id` | Your app's client ID |
| `upstream_client_secret` | Your app's client secret |
| `token_verifier` | TokenVerifier instance |
| `base_url` | Your server's public URL |
| `redirect_path` | Callback path (default: `/auth/callback`) |
| `issuer_url` | Issuer URL for metadata |
| `forward_pkce` | Forward PKCE to provider (default: True) |

### Provider-Specific Examples

**GitHub:**
```python
from fastmcp.server.auth.providers.github import GitHubProvider

auth = GitHubProvider(
    client_id="Ov23li...",
    client_secret="abc123...",
    base_url="https://your-server.com"
)
```

**Google:**
```python
from fastmcp.server.auth.providers.google import GoogleProvider

auth = GoogleProvider(
    client_id="your-client-id.apps.googleusercontent.com",
    client_secret="your-client-secret",
    base_url="https://your-server.com"
)
```

## Remote OAuth

For providers with Dynamic Client Registration (DCR) support:

```python
from fastmcp.server.auth.providers.workos import AuthKitProvider

auth = AuthKitProvider(
    authkit_domain="https://your-project.authkit.app",
    base_url="https://your-server.com"
)
```

## OIDC Proxy

Auto-discover configuration from OIDC providers:

```python
from fastmcp.server.auth import OIDCProxy

auth = OIDCProxy(
    oidc_config_url="https://auth.example.com/.well-known/openid-configuration",
    client_id="your-client-id",
    client_secret="your-client-secret",
    base_url="https://your-server.com"
)
```

## Multi-Auth

Accept tokens from multiple sources:

```python
from fastmcp.server.auth import MultiAuth, OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier

auth = MultiAuth(
    server=OAuthProxy(...),  # Primary OAuth provider
    verifiers=[
        JWTVerifier(  # Additional token sources
            jwks_uri="https://internal.example.com/.well-known/jwks.json",
            issuer="https://internal.example.com",
            audience="my-server",
        ),
    ],
)

mcp = FastMCP("My Server", auth=auth)
```

## Authorization

Control access to components using callable-based auth checks.

### require_scopes

Require specific OAuth scopes:

```python
from fastmcp import FastMCP
from fastmcp.server.auth import require_scopes

mcp = FastMCP("Scoped Server")

@mcp.tool(auth=require_scopes("admin"))
def admin_operation() -> str:
    """Requires 'admin' scope."""
    return "Admin action completed"

@mcp.tool(auth=require_scopes("read", "write"))
def read_write_operation() -> str:
    """Requires both 'read' AND 'write' scopes."""
    return "Read/write action completed"
```

### restrict_tag

Tag-based scope requirements:

```python
from fastmcp import FastMCP
from fastmcp.server.auth import restrict_tag
from fastmcp.server.middleware import AuthMiddleware

mcp = FastMCP(
    "Tagged Server",
    middleware=[
        AuthMiddleware(auth=restrict_tag("admin", scopes=["admin"]))
    ]
)

@mcp.tool(tags={"admin"})
def admin_tool() -> str:
    """Tagged 'admin', requires 'admin' scope."""
    return "Admin only"

@mcp.tool(tags={"public"})
def public_tool() -> str:
    """Not tagged 'admin', no scope required."""
    return "Anyone can access"
```

### Custom Auth Checks

```python
from fastmcp.server.auth import AuthContext

def require_premium_user(ctx: AuthContext) -> bool:
    if ctx.token is None:
        return False
    return ctx.token.claims.get("premium", False) is True

def require_access_level(minimum_level: int):
    def check(ctx: AuthContext) -> bool:
        if ctx.token is None:
            return False
        return ctx.token.claims.get("level", 0) >= minimum_level
    return check

@mcp.tool(auth=require_premium_user)
def premium_feature() -> str:
    return "Premium content"

@mcp.tool(auth=require_access_level(5))
def advanced_feature() -> str:
    return "Advanced feature"
```

### Async Auth Checks

```python
async def check_user_permissions(ctx: AuthContext) -> bool:
    if ctx.token is None:
        return False
    user_id = ctx.token.claims.get("sub")
    permissions = await fetch_user_permissions(user_id)
    return "admin" in permissions
```

### Combining Checks

Multiple checks combine with AND logic:

```python
@mcp.tool(auth=[require_scopes("admin"), require_scopes("write")])
def secure_admin_action() -> str:
    """Requires both 'admin' AND 'write' scopes."""
    return "Secure admin action"
```

### Server-Level Authorization with Middleware

```python
from fastmcp.server.middleware import AuthMiddleware

mcp = FastMCP(
    "Enforced Auth Server",
    middleware=[AuthMiddleware(auth=require_scopes("api"))]
)
```

### Error Handling

Raise `AuthorizationError` for explicit denial:

```python
from fastmcp.exceptions import AuthorizationError

def require_verified_email(ctx: AuthContext) -> bool:
    if ctx.token is None:
        raise AuthorizationError("Authentication required")
    if not ctx.token.claims.get("email_verified"):
        raise AuthorizationError("Email verification required")
    return True
```

## Accessing Token Info

```python
from fastmcp.server.dependencies import get_access_token

@mcp.tool
async def protected_tool() -> dict:
    token = get_access_token()
    
    return {
        "user": token.claims.get("sub"),
        "scopes": token.claims.get("scope", "").split(),
        "issuer": token.claims.get("iss"),
    }
```

## Production Configuration

For production, use persistent token storage:

```python
import os
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url=os.environ["BASE_URL"],
    
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
```

## Choosing Authentication

| Use Case | Recommended Approach |
|----------|---------------------|
| Existing JWT infrastructure | JWTVerifier |
| GitHub integration | GitHubProvider |
| Google integration | GoogleProvider |
| Azure/AD integration | AzureProvider |
| WorkOS AuthKit | AuthKitProvider |
| Auth0 | Auth0Provider |
| Multiple token sources | MultiAuth |
| Custom OAuth server | OAuthProvider (advanced) |
