# Server Advanced

Middleware, composition, transforms, pagination, versioning, visibility, background tasks, and telemetry.

## Contents
- Middleware
- Server Composition
- Transforms
- Code Mode
- Tool Search
- Pagination
- Versioning
- Visibility
- Background Tasks
- OpenTelemetry

## Middleware

Middleware intercepts and modifies requests/responses.

### Basic Middleware

```python
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext

class LoggingMiddleware(Middleware):
    async def on_message(self, context: MiddlewareContext, call_next):
        print(f"→ {context.method}")
        result = await call_next(context)
        print(f"← {context.method}")
        return result

mcp = FastMCP("MyServer")
mcp.add_middleware(LoggingMiddleware())
```

### Middleware Context

| Attribute | Description |
|-----------|-------------|
| `method` | MCP method name (e.g., `"tools/call"`) |
| `source` | Origin: `"client"` or `"server"` |
| `type` | Message type: `"request"` or `"notification"` |
| `message` | The MCP message data |
| `timestamp` | When the request was received |
| `fastmcp_context` | FastMCP context object |

### Hooks

| Hook | Description |
|------|-------------|
| `on_message` | All MCP traffic |
| `on_request` | Requests expecting responses |
| `on_notification` | Fire-and-forget notifications |
| `on_call_tool` | Tool execution |
| `on_read_resource` | Resource reads |
| `on_get_prompt` | Prompt retrieval |
| `on_list_tools` | Tool listing |
| `on_list_resources` | Resource listing |
| `on_list_prompts` | Prompt listing |
| `on_initialize` | Client connection |

### Example: Timing Middleware

```python
import time

class TimingMiddleware(Middleware):
    async def on_request(self, context: MiddlewareContext, call_next):
        start = time.time()
        result = await call_next(context)
        duration = time.time() - start
        print(f"{context.method}: {duration:.3f}s")
        return result
```

### Example: Auth Middleware

```python
from mcp.types import McpError, ErrorData

class AuthMiddleware(Middleware):
    async def on_request(self, context: MiddlewareContext, call_next):
        token = context.message.get("token")
        if not self.validate_token(token):
            raise McpError(ErrorData(code=-32000, message="Unauthorized"))
        return await call_next(context)
```

### Built-in Middleware

```python
from fastmcp.server.middleware.caching import ResponseCachingMiddleware
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from fastmcp.server.middleware.response_limiting import ResponseLimitingMiddleware
from fastmcp.server.middleware.ping import PingMiddleware

# Cache responses
mcp.add_middleware(ResponseCachingMiddleware(
    cache_storage=cache_store,
    ttl_seconds=3600
))

# Rate limiting
mcp.add_middleware(RateLimitingMiddleware(
    requests_per_minute=60
))

# Response size limiting
mcp.add_middleware(ResponseLimitingMiddleware(
    max_response_size=1_000_000  # 1MB
))

# Keepalive ping
mcp.add_middleware(PingMiddleware())
```

## Server Composition

Mount servers to create hierarchical structures.

### Basic Mounting

```python
parent = FastMCP("Parent")
child = FastMCP("Child")

@child.tool
def child_tool() -> str:
    return "from child"

parent.mount(child, namespace="child")
# Tool becomes: child_child_tool
```

### Multiple Servers

```python
main = FastMCP("Main")
auth_server = FastMCP("Auth")
data_server = FastMCP("Data")

main.mount(auth_server, namespace="auth")
main.mount(data_server, namespace="data")

# Tools: auth_*, data_*
```

### Composition with Transforms

```python
# Get the provider for further customization
mount = parent.mount(child, namespace="api")
mount.add_transform(ToolTransform({...}))
```

## Transforms

Modify how components are exposed to clients.

### Namespace Transform

Prefix component names:

```python
from fastmcp.server.transforms import Namespace

mcp.add_transform(Namespace("api"))
# tool_name -> api_tool_name
# data://resource -> data://api/resource
```

### Prompts as Tools

Expose prompts as callable tools for tool-only clients:

```python
from fastmcp.server.transforms import PromptsAsTools

mcp.add_transform(PromptsAsTools(mcp))
# Creates: list_prompts, get_prompt tools
```

### Resources as Tools

Expose resources as callable tools:

```python
from fastmcp.server.transforms import ResourcesAsTools

mcp.add_transform(ResourcesAsTools(mcp))
# Creates: list_resources, read_resource tools
```

### Tool Transformation

Modify tool schemas and behavior:

```python
from fastmcp.server.transforms import ToolTransform
from fastmcp.tools.tool_transform import ToolTransformConfig, ArgTransform

mcp.add_transform(ToolTransform({
    "verbose_name": ToolTransformConfig(
        name="short",
        description="Cleaner description",
    )
}))

# Rename/hide arguments
from fastmcp.tools import Tool, tool

@tool
def search(q: str, limit: int = 10) -> list[str]:
    """Search for items."""
    return []

better = Tool.from_tool(
    search,
    name="find_items",
    transform_args={
        "q": ArgTransform(name="query", description="Search terms"),
        "limit": ArgTransform(hide=True, default=20),
    }
)
```

### Custom Transform Functions

```python
from fastmcp.tools.tool_transform import forward

async def safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        raise ValueError("Cannot divide by zero")
    return await forward(numerator=numerator, denominator=denominator)

safe_division = Tool.from_tool(
    divide,
    name="safe_divide",
    transform_fn=safe_divide,
)
```

## Code Mode

Let LLMs write Python to orchestrate tools in a sandbox.

Install: `pip install "fastmcp[code-mode]"`

### Basic Setup

```python
from fastmcp import FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode

mcp = FastMCP("Server", transforms=[CodeMode()])

@mcp.tool
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y
```

Clients see meta-tools for discovering and executing code:
- `search` - Find tools by query
- `get_schema` - Get parameter details
- `execute` - Run Python code that calls tools

### Discovery Patterns

**Three-Stage (default):** Search → Get schema → Execute

```python
# Default pattern
mcp = FastMCP("Server", transforms=[CodeMode()])
```

**Two-Stage:** Search with inline schemas → Execute

```python
from fastmcp.experimental.transforms.code_mode import Search, GetSchemas

code_mode = CodeMode(
    discovery_tools=[Search(default_detail="detailed"), GetSchemas()],
)
```

**Four-Stage:** GetTags → Search → Get schema → Execute

```python
from fastmcp.experimental.transforms.code_mode import GetTags, Search, GetSchemas

code_mode = CodeMode(
    discovery_tools=[GetTags(), Search(), GetSchemas()],
)
```

### Sandbox Resource Limits

```python
from fastmcp.experimental.transforms.code_mode import MontySandboxProvider

sandbox = MontySandboxProvider(
    limits={
        "max_duration_secs": 10,
        "max_memory": 50_000_000,
        "max_recursion_depth": 100,
    }
)

mcp = FastMCP("Server", transforms=[CodeMode(sandbox_provider=sandbox)])
```

## Tool Search

Replace large tool catalogs with on-demand search.

### Regex Search

```python
from fastmcp.server.transforms.search import RegexSearchTransform

mcp = FastMCP("Server", transforms=[RegexSearchTransform()])

# LLM uses: search_tools(pattern="database")
```

### BM25 Search

```python
from fastmcp.server.transforms.search import BM25SearchTransform

mcp = FastMCP("Server", transforms=[BM25SearchTransform()])

# LLM uses: search_tools(query="tools for deleting things from the database")
```

### Configuration

```python
# Limit results
mcp.add_transform(BM25SearchTransform(max_results=10))

# Pin some tools always visible
mcp.add_transform(RegexSearchTransform(
    always_visible=["help", "status"],
))

# Custom tool names
mcp.add_transform(BM25SearchTransform(
    search_tool_name="find_tools",
    call_tool_name="run_tool",
))
```

## Pagination

Handle large result sets with MCP-compliant pagination.

### Server-Side Pagination

```python
mcp = FastMCP("Server", pagination_limit=100)

@mcp.tool
def list_items(cursor: str | None = None) -> list:
    # Return items with optional cursor-based pagination
    ...
```

### Constructor Option

```python
mcp = FastMCP("Server", pagination_limit=50)  # 50 items per page max
```

### Client-Side Pagination

```python
from fastmcp import Client

async def fetch_all_items():
    async with Client("server.py") as client:
        cursor = None
        all_items = []
        while True:
            result = await client.list_tools(cursor=cursor)
            all_items.extend(result.tools)
            cursor = result.next_cursor
            if not cursor:
                break
        return all_items
```

## Versioning

Maintain multiple implementations of the same component.

### Declaring Versions

```python
@mcp.tool(version="1.0")
def calculate(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y

@mcp.tool(version="2.0")
def calculate(x: int, y: int, z: int = 0) -> int:
    """Add two or three numbers."""
    return x + y + z
```

### Versioned API Surfaces

```python
from fastmcp.server.transforms import VersionFilter

# Create servers with different version filters
api_v1 = FastMCP("API v1", providers=[components])
api_v1.add_transform(VersionFilter(version_lt="2.0"))

api_v2 = FastMCP("API v2", providers=[components])
api_v2.add_transform(VersionFilter(version_gte="2.0"))
```

### Version Filter Options

```python
# Versions < 3.0
VersionFilter(version_lt="3.0")

# Versions >= 2.0
VersionFilter(version_gte="2.0")

# Versions in range [2.0, 3.0)
VersionFilter(version_gte="2.0", version_lt="3.0")
```

### Requesting Specific Versions

**FastMCP Client:**
```python
result = await client.call_tool("calculate", {"x": 1, "y": 2}, version="1.0")
```

**MCP Protocol:**
```json
{
  "x": 1,
  "y": 2,
  "_meta": {"fastmcp": {"version": "1.0"}}
}
```

### Version Comparison

- PEP 440 versions (`"1.0"`, `"2.1.3"`): Semantic comparison
- Other formats (dates, custom): Lexicographic string comparison
- `"v"` prefix is stripped before comparison

## Visibility

Control which components are visible to clients.

### Enable/Disable Components

```python
# Disable specific components
mcp.disable(keys={"tool:sensitive_tool"})
mcp.disable(keys={"resource:secret://data"})

# Disable by tag
mcp.disable(tags={"internal"})

# Enable only specific tags (allowlist mode)
mcp.enable(tags={"public"}, only=True)
```

### Component Keys

| Component | Key Format |
|-----------|------------|
| Tool | `tool:{name}` |
| Resource | `resource:{uri}` |
| Template | `template:{uri}` |
| Prompt | `prompt:{name}` |

### Tag-Based Visibility

```python
@mcp.tool(tags={"public"})
def public_tool() -> str:
    return "public"

@mcp.tool(tags={"internal"})
def internal_tool() -> str:
    return "internal"

# Only show public tools
mcp.enable(tags={"public"}, only=True)
```

### Per-Session Visibility

```python
from fastmcp import Context

@mcp.tool(tags={"premium"})
def premium_analysis(data: str) -> str:
    return f"Premium analysis of: {data}"

@mcp.tool
async def unlock_premium(ctx: Context) -> str:
    await ctx.enable_components(tags={"premium"})
    return "Premium features unlocked"

@mcp.tool
async def reset_features(ctx: Context) -> str:
    await ctx.reset_visibility()
    return "Features reset"

# Disable premium globally by default
mcp.disable(tags={"premium"})
```

### Session Visibility Methods

| Method | Description |
|--------|-------------|
| `ctx.enable_components(...)` | Enable matching components for this session |
| `ctx.disable_components(...)` | Disable matching components for this session |
| `ctx.reset_visibility()` | Clear all session rules |

### Filter Criteria

| Parameter | Description |
|-----------|-------------|
| `names` | Component names or URIs |
| `keys` | Component keys (e.g., `{"tool:my_tool"}`) |
| `tags` | Tags to match |
| `version` | Version specification |
| `components` | Types: `{"tool"}`, `{"resource"}`, `{"prompt"}` |
| `match_all` | Match all components |

## Background Tasks

Run long-running operations asynchronously with progress tracking.

Install: `pip install "fastmcp[tasks]"`

### Basic Usage

```python
@mcp.tool(task=True)
async def slow_computation(duration: int) -> str:
    """A long-running operation."""
    for i in range(duration):
        await asyncio.sleep(1)
    return f"Completed in {duration} seconds"
```

### Execution Modes

```python
from fastmcp.server.tasks import TaskConfig

# Optional (default): sync or background
@mcp.tool(task=TaskConfig(mode="optional"))
async def flexible_task() -> str:
    return "Works either way"

# Required: must be background
@mcp.tool(task=TaskConfig(mode="required"))
async def must_be_background() -> str:
    return "Only runs as background task"

# Forbidden: never background
@mcp.tool(task=TaskConfig(mode="forbidden"))
async def sync_only() -> str:
    return "Never runs as background task"
```

### Poll Interval

```python
from datetime import timedelta

@mcp.tool(task=TaskConfig(
    mode="optional",
    poll_interval=timedelta(seconds=2)
))
async def quick_task() -> str:
    return "Done"
```

### Progress Reporting

```python
from fastmcp.dependencies import Progress

@mcp.tool(task=True)
async def process_files(files: list[str], progress: Progress = Progress()) -> str:
    await progress.set_total(len(files))

    for file in files:
        await progress.set_message(f"Processing {file}")
        # ... do work ...
        await progress.increment()

    return f"Processed {len(files)} files"
```

### Backends

**In-Memory (default):**
- URL: `memory://`
- No external dependencies
- Single process only

**Redis:**
- URL: `redis://localhost:6379`
- Persistent, scalable, distributed
- Required for horizontal scaling

```bash
FASTMCP_DOCKET_URL=redis://localhost:6379 fastmcp tasks worker server.py
```

### Workers

```bash
# Start additional workers
fastmcp tasks worker server.py

# With concurrency
FASTMCP_DOCKET_CONCURRENCY=20 fastmcp tasks worker server.py
```

## OpenTelemetry

Native OpenTelemetry instrumentation for distributed tracing.

### Enable Tracing

```bash
pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install

opentelemetry-instrument \
  --service_name my-fastmcp-server \
  --exporter_otlp_endpoint http://localhost:4317 \
  fastmcp run server.py
```

### Programmatic Configuration

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4317"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# Now import and use FastMCP
from fastmcp import FastMCP
```

### Span Names

| Span Name | Description |
|-----------|-------------|
| `tools/call {name}` | Tool execution |
| `resources/read {uri}` | Resource read |
| `prompts/get {name}` | Prompt render |
| `delegate {name}` | Delegation to mounted server |

### Custom Spans

```python
from fastmcp.telemetry import get_tracer

@mcp.tool()
async def complex_operation(input: str) -> str:
    tracer = get_tracer()

    with tracer.start_as_current_span("parse_input") as span:
        span.set_attribute("input.length", len(input))
        parsed = parse(input)

    with tracer.start_as_current_span("process_data") as span:
        span.set_attribute("data.count", len(parsed))
        result = process(parsed)

    return result
```

### Attributes Reference

**MCP Semantic Conventions:**
| Attribute | Value |
|-----------|-------|
| `rpc.system` | `"mcp"` |
| `rpc.service` | Server name |
| `mcp.method.name` | MCP method |
| `mcp.session.id` | Session identifier |
| `mcp.resource.uri` | Resource URI |

**FastMCP Custom:**
| Attribute | Description |
|-----------|-------------|
| `fastmcp.server.name` | Server name |
| `fastmcp.component.type` | `tool`, `resource`, `prompt`, `template` |
| `fastmcp.component.key` | Full component identifier |
| `fastmcp.provider.type` | Provider class name |

### Local Development

**otel-desktop-viewer:**
```bash
brew install nico-barbas/brew/otel-desktop-viewer
otel-desktop-viewer
```

**Jaeger:**
```bash
docker run -d --name jaeger \
  -p 16686:16686 -p 4317:4317 \
  jaegertracing/all-in-one:latest
```
