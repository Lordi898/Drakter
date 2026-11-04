# Deployment

HTTP deployment, ASGI integration, storage backends, telemetry, and hosting.

## Contents
- HTTP Deployment
- ASGI Integration
- Middleware
- Storage Backends
- Background Tasks
- OpenTelemetry
- Production Checklist

## HTTP Deployment

### Basic HTTP Server

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
```

### HTTP Options

| Option | Default | Description |
|--------|---------|-------------|
| `host` | 127.0.0.1 | Network interface |
| `port` | 8000 | Port number |
| `path` | /mcp | Endpoint path |
| `log_level` | INFO | Logging level |

### CLI

```bash
# Basic HTTP
fastmcp run server.py --transport http

# Custom port/host
fastmcp run server.py --transport http --port 3000 --host 0.0.0.0

# Custom path
fastmcp run server.py --transport http --path /api/mcp

# Auto-reload on file changes
fastmcp run server.py --transport http --reload
```

## ASGI Integration

### Create ASGI App

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

# Create ASGI application
app = mcp.asgi_app()
```

### With Starlette

```python
from starlette.applications import Starlette
from starlette.routing import Mount
from fastmcp import FastMCP

mcp = FastMCP("MCP Server")

app = Starlette(
    routes=[
        Mount("/mcp", app=mcp.asgi_app()),
    ]
)
```

### With FastAPI

```python
from fastapi import FastAPI
from fastmcp import FastMCP

mcp = FastMCP("MCP Server")
app = FastAPI()

# Mount MCP at /mcp
app.mount("/mcp", mcp.asgi_app())

# Regular FastAPI routes
@app.get("/health")
def health():
    return {"status": "ok"}
```

### With Lifespan

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastmcp import FastMCP

mcp = FastMCP("MCP Server")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await mcp.setup()
    yield
    # Shutdown
    await mcp.shutdown()

app = FastAPI(lifespan=lifespan)
app.mount("/mcp", mcp.asgi_app())
```

## Middleware

### CORS

```python
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

mcp = FastMCP("My Server")

# Run with CORS
mcp.run(
    transport="http",
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
    ]
)
```

### Custom Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = request.headers.get("Authorization")
        if not token:
            return JSONResponse({"error": "Unauthorized"}, 401)
        return await call_next(request)

mcp.run(transport="http", middleware=[Middleware(AuthMiddleware)])
```

## Storage Backends

FastMCP uses pluggable storage backends for caching and OAuth state management. Storage is powered by **py-key-value-aio**.

### In-Memory Storage (Default)

**Best for:** Development, testing, single-process deployments

```python
from key_value.aio.stores.memory import MemoryStore

# Used by default - no configuration needed
store = MemoryStore()
```

**Characteristics:**
- ✅ No setup required
- ✅ Very fast
- ❌ Data lost on restart
- ❌ Not suitable for multi-process deployments

### File Storage

**Best for:** Single-server production deployments, persistent caching

Persists data to filesystem as one JSON file per key.

```python
from pathlib import Path
from key_value.aio.stores.filetree import (
    FileTreeStore,
    FileTreeV1KeySanitizationStrategy,
    FileTreeV1CollectionSanitizationStrategy,
)
from fastmcp.server.middleware.caching import ResponseCachingMiddleware

storage_dir = Path("/var/cache/fastmcp")
store = FileTreeStore(
    data_directory=storage_dir,
    key_sanitization_strategy=FileTreeV1KeySanitizationStrategy(storage_dir),
    collection_sanitization_strategy=FileTreeV1CollectionSanitizationStrategy(storage_dir),
)

# Persistent response cache
middleware = ResponseCachingMiddleware(cache_storage=store)
```

**Characteristics:**
- ✅ Data persists across restarts
- ✅ No external dependencies
- ✅ Human-readable files on disk
- ❌ Not suitable for distributed deployments

### Redis

**Best for:** Distributed production deployments, shared caching

Install: `pip install 'py-key-value-aio[redis]'`

```python
from key_value.aio.stores.redis import RedisStore
from fastmcp.server.middleware.caching import ResponseCachingMiddleware

# Distributed response cache
middleware = ResponseCachingMiddleware(
    cache_storage=RedisStore(host="redis.example.com", port=6379)
)
```

With authentication:

```python
cache_store = RedisStore(
    host="redis.example.com",
    port=6379,
    password="your-redis-password"
)
```

**Characteristics:**
- ✅ Distributed and highly available
- ✅ Fast in-memory performance
- ✅ Works across multiple server instances
- ✅ Built-in TTL support
- ❌ Requires Redis infrastructure

### Other Backends

py-key-value-aio also supports:
- **DynamoDB** - AWS distributed database
- **MongoDB** - NoSQL document store
- **Elasticsearch** - Distributed search
- **Memcached** - Distributed memory caching
- **RocksDB** - Embedded high-performance store
- **Valkey** - Redis-compatible server

See [py-key-value-aio documentation](https://github.com/strawgate/py-key-value) for details.

## Use Cases

### OAuth Token Storage

Default behavior (development):
- **Mac/Windows**: Keys auto-managed via system keyring, storage on disk
- **Linux**: Keys ephemeral, storage in memory

Production configuration with encryption:

```python
import os
from fastmcp.server.auth.providers.github import GitHubProvider
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url="https://your-server.com",
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    client_storage=FernetEncryptionWrapper(
        key_value=RedisStore(host="redis.example.com", port=6379),
        fernet=Fernet(os.environ["STORAGE_ENCRYPTION_KEY"])
    )
)
```

**Always wrap storage in `FernetEncryptionWrapper` for OAuth tokens** to encrypt at rest.

### Response Caching Middleware

```python
from pathlib import Path
from fastmcp import FastMCP
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from key_value.aio.stores.filetree import FileTreeStore

mcp = FastMCP("My Server")

cache_dir = Path("cache")
cache_store = FileTreeStore(data_directory=cache_dir)

mcp.add_middleware(ResponseCachingMiddleware(cache_storage=cache_store))
```

### Multi-Server Namespacing

```python
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.prefix_collections import PrefixCollectionsWrapper

base_store = RedisStore(host="redis.example.com")
namespaced_store = PrefixCollectionsWrapper(
    key_value=base_store,
    prefix="my-server"
)

middleware = ResponseCachingMiddleware(cache_storage=namespaced_store)
```

### Client-Side Token Storage

```python
from pathlib import Path
from fastmcp.client.auth import OAuthClientProvider
from key_value.aio.stores.filetree import FileTreeStore

token_dir = Path("~/.local/share/fastmcp/tokens").expanduser()
token_storage = FileTreeStore(data_directory=token_dir)

oauth_provider = OAuthClientProvider(
    mcp_url="https://your-mcp-server.com/mcp/sse",
    token_storage=token_storage
)
```

## Choosing a Backend

| Backend | Development | Single Server | Multi-Server | Cloud Native |
|---------|-------------|---------------|--------------|--------------|
| Memory | ✅ Best | ⚠️ Limited | ❌ | ❌ |
| File | ✅ Good | ✅ Recommended | ❌ | ⚠️ |
| Redis | ⚠️ Overkill | ✅ Good | ✅ Best | ✅ Best |
| DynamoDB | ❌ | ⚠️ | ✅ | ✅ Best (AWS) |
| MongoDB | ❌ | ⚠️ | ✅ | ✅ Good |

**Decision tree:**
1. **Just starting?** Use Memory (default)
2. **Single server, needs persistence?** Use File
3. **Multiple servers or cloud?** Use Redis or DynamoDB

## Event Store (Resumability)

Enable resumable connections:

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

mcp.run(
    transport="http",
    event_store=my_event_store  # Implement EventStore
)
```

## Background Tasks

Background tasks require Redis backend for production.

### In-Memory Backend

Default (`memory://`), single-process only:
- No external dependencies
- Tasks lost on restart
- ~250ms task pickup latency

### Redis Backend

```bash
FASTMCP_DOCKET_URL=redis://localhost:6379 fastmcp tasks worker server.py
```

Advantages:
- Tasks survive restarts
- Single-digit millisecond latency
- Horizontal scaling with multiple workers

### Worker Configuration

```bash
# Start worker
fastmcp tasks worker server.py

# With concurrency
FASTMCP_DOCKET_CONCURRENCY=20 fastmcp tasks worker server.py
```

## OpenTelemetry

Enable distributed tracing:

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install

opentelemetry-instrument \
  --service_name my-fastmcp-server \
  --exporter_otlp_endpoint http://localhost:4317 \
  fastmcp run server.py
```

Or configure programmatically:

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Now import FastMCP
from fastmcp import FastMCP
```

## Production Checklist

- [ ] Use HTTPS (reverse proxy or TLS termination)
- [ ] Configure authentication
- [ ] Set up persistent storage (Redis/File)
- [ ] Add CORS if needed for browser clients
- [ ] Configure logging
- [ ] Set up OpenTelemetry monitoring
- [ ] Use environment variables for secrets
- [ ] Pin FastMCP version
- [ ] Configure OAuth token encryption

## Example: Production Setup

```python
import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from key_value.aio.stores.redis import RedisStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet

mcp = FastMCP("Production Server")

auth = GitHubProvider(
    client_id=os.environ["GITHUB_CLIENT_ID"],
    client_secret=os.environ["GITHUB_CLIENT_SECRET"],
    base_url=os.environ["BASE_URL"],
    jwt_signing_key=os.environ["JWT_SIGNING_KEY"],
    client_storage=FernetEncryptionWrapper(
        key_value=RedisStore(host=os.environ["REDIS_HOST"]),
        fernet=Fernet(os.environ["STORAGE_ENCRYPTION_KEY"])
    )
)
mcp = FastMCP("Production Server", auth=auth)

if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        log_level="INFO"
    )
```

## Running with Gunicorn

```bash
gunicorn server:app -w 4 -k uvicorn.workers.UvicornWorker
```

Note: For multi-worker deployments, use Redis backend for storage.

## Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .

RUN pip install fastmcp[redis]

ENV FASTMCP_DOCKET_URL=redis://redis:6379

CMD ["fastmcp", "run", "server.py", "--transport", "http", "--host", "0.0.0.0"]
```
