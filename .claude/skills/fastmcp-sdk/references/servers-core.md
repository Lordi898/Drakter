# Server Core

Server basics, tools, resources, prompts, context, providers, and testing.

## Contents
- Creating a Server
- Tools
- Resources
- Prompts
- Context
- Providers
- Testing

## Creating a Server

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

# Run with different transports
mcp.run()  # stdio (default)
mcp.run(transport="http", port=8000)
```

### Server Constructor

```python
mcp = FastMCP(
    name="My Server",              # Server name
    version="1.0.0",               # Optional version
    instructions="...",            # Optional instructions for LLM
    auth=auth_provider,            # Optional authentication
    tasks=True,                    # Enable background tasks globally
    log_level="INFO",              # Logging level
    on_duplicate_tools="warn",     # Duplicate handling
    on_duplicate_resources="warn",
    on_duplicate_prompts="warn",
    strict_input_validation=False, # Strict parameter validation
    pagination_limit=None,         # Max items per page
    mask_error_details=False,      # Mask internal errors
    transforms=[...],              # Server-level transforms
)
```

### Duplicate Behavior Options

- `"warn"` (default): Logs warning, new replaces old
- `"error"`: Raises ValueError
- `"replace"`: Silently replaces
- `"ignore"`: Keeps original

### Custom Routes (HTTP)

```python
from starlette.requests import Request
from starlette.responses import PlainTextResponse

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")
```

## Tools

Tools are Python functions exposed to LLMs via MCP.

### Basic Tool

```python
@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b
```

### Tool with Metadata

```python
@mcp.tool(
    name="search_products",
    description="Search the product catalog",
    tags={"catalog", "search"},
    timeout=30.0,  # seconds
    version="1.0.0",
)
def search(query: str, limit: int = 10) -> list[dict]:
    return search_products(query, limit)
```

### @tool Decorator Arguments

| Argument | Description |
|----------|-------------|
| `name` | Custom tool name |
| `description` | Custom description |
| `tags` | Set of tags for filtering |
| `annotations` | ToolAnnotations dict |
| `meta` | Custom metadata dict |
| `timeout` | Execution timeout (seconds) |
| `version` | Version identifier |
| `output_schema` | JSON schema for output |
| `task` | Enable background execution |

### Type Annotations

FastMCP supports all Pydantic types:

| Type | Example |
|------|---------|
| Basic | `int`, `float`, `str`, `bool` |
| Binary | `bytes` |
| DateTime | `datetime`, `date`, `timedelta` |
| Collections | `list[str]`, `dict[str, int]`, `set[int]` |
| Optional | `str \| None`, `Optional[str]` |
| Union | `str \| int`, `Union[str, int]` |
| Enums | `Literal["A", "B"]`, `Enum` |
| Paths | `Path` |
| UUIDs | `UUID` |
| Models | Pydantic `BaseModel` |

### Parameter Metadata

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def search(
    query: Annotated[str, Field(min_length=1, max_length=100, description="Search query")],
    limit: Annotated[int, Field(ge=1, le=100)] = 10,
) -> list[dict]:
    return search_database(query, limit)

# Simple string description
def process(
    image_url: Annotated[str, "URL of the image to process"],
    resize: Annotated[bool, "Whether to resize"] = False,
) -> dict:
    ...
```

### Hiding Parameters from LLM

```python
from fastmcp.dependencies import Depends

def get_user_id() -> str:
    return "user_123"  # Injected at runtime

@mcp.tool
def get_user_details(user_id: str = Depends(get_user_id)) -> str:
    # user_id is injected by server, not provided by LLM
    return f"Details for {user_id}"
```

### Async Tools

```python
@mcp.tool
async def fetch_data(url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
```

Sync functions automatically run in a threadpool.

### Return Values

FastMCP converts return values to MCP content blocks:

```python
from fastmcp.utilities.types import Image, Audio, File

# String -> TextContent
@mcp.tool
def text_tool() -> str:
    return "Hello"

# bytes -> Base64 encoded
@mcp.tool
def binary_tool() -> bytes:
    return b"\x00\x01\x02"

# Image -> ImageContent
@mcp.tool
def image_tool() -> Image:
    return Image(path="chart.png")

# Multiple items
@mcp.tool
def multi_tool() -> list:
    return [Image(path="chart.png"), "Analysis text"]
```

### Media Helper Classes

```python
from fastmcp.utilities.types import Image, Audio, File

# From path
Image(path="chart.png")

# From data
Image(data=b"...", format="png")

# Audio
Audio(path="recording.wav")

# File
File(path="document.pdf")
File(data=b"...", format="pdf", name="doc.pdf")
```

### Structured Output

Return type annotations enable structured output:

```python
from dataclasses import dataclass

@dataclass
class UserProfile:
    name: str
    age: int

@mcp.tool
def get_profile(user_id: str) -> UserProfile:
    return UserProfile(name="Alice", age=30)

# Client receives structuredContent alongside content
```

### Output Schemas

Explicitly define output schema:

```python
@mcp.tool(output_schema={
    "type": "object",
    "properties": {
        "data": {"type": "string"},
        "metadata": {"type": "object"}
    }
})
def custom_schema_tool() -> dict:
    return {"data": "Hello", "metadata": {"version": "1.0"}}
```

### ToolResult for Full Control

```python
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

@mcp.tool
def advanced_tool() -> ToolResult:
    return ToolResult(
        content=[TextContent(type="text", text="Human-readable summary")],
        structured_content={"data": "value", "count": 42},
        meta={"execution_time_ms": 145}
    )
```

### Custom Serialization

```python
import yaml
from fastmcp.tools.tool import ToolResult

@mcp.tool
def get_config() -> ToolResult:
    data = {"api_key": "abc123", "debug": True}
    return ToolResult(
        content=yaml.dump(data),
        structured_content=data
    )
```

### Timeouts

```python
@mcp.tool(timeout=30.0)
async def fetch_data(url: str) -> dict:
    # If this takes longer than 30 seconds,
    # the client receives an MCP error
    ...
```

### MCP Annotations

Communicate tool behavior to clients:

```python
@mcp.tool(annotations={
    "title": "Calculate Sum",
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": False
})
def calculate_sum(a: float, b: float) -> float:
    return a + b
```

| Annotation | Type | Default | Purpose |
|------------|------|---------|---------|
| `title` | string | - | Display name |
| `readOnlyHint` | boolean | false | Only reads without changes |
| `destructiveHint` | boolean | true | Changes are destructive |
| `idempotentHint` | boolean | false | Same result for repeated calls |
| `openWorldHint` | boolean | true | Interacts with external systems |

### Component Visibility

```python
@mcp.tool(tags={"admin"})
def admin_action() -> str:
    return "Done"

@mcp.tool(tags={"public"})
def public_action() -> str:
    return "Done"

# Disable by key
mcp.disable(keys={"tool:admin_action"})

# Disable by tag
mcp.disable(tags={"admin"})

# Allowlist mode
mcp.enable(tags={"public"}, only=True)
```

### Validation Modes

```python
# Strict validation (rejects type mismatches)
mcp = FastMCP("StrictServer", strict_input_validation=True)

# Flexible (default) - coerces compatible inputs
mcp = FastMCP("FlexibleServer", strict_input_validation=False)
```

### Using with Methods

```python
from fastmcp import FastMCP
from fastmcp.tools import tool

class Calculator:
    @tool()
    def multiply(self, x: int) -> int:
        """Multiply x by instance multiplier."""
        return x * self.multiplier

calc = Calculator(3)
mcp = FastMCP()
mcp.add_tool(calc.multiply)
```

## Resources

Resources provide read-only access to data.

### Basic Resource

```python
@mcp.resource("resource://config")
def get_config() -> str:
    return json.dumps({"version": "1.0"})
```

### Resource Template

```python
@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    return json.dumps(fetch_user(user_id))
```

### Wildcard Parameters

Match multiple path segments:

```python
@mcp.resource("files://{filepath*}")
def get_file(filepath: str) -> str:
    # Matches: files://docs/server/resources.mdx
    return read_file(filepath)
```

### Query Parameters

Optional parameters via query string:

```python
@mcp.resource("data://{id}{?format}")
def get_data(id: str, format: str = "json") -> str:
    if format == "xml":
        return f"<data id='{id}' />"
    return f'{{"id": "{id}"}}'

# data://123 -> default format
# data://123?format=xml -> xml format
```

Query parameters must be optional (have defaults).

### Multiple Query Parameters

```python
@mcp.resource("api://{endpoint}{?version,limit,offset}")
def call_api(
    endpoint: str,
    version: int = 1,
    limit: int = 10,
    offset: int = 0
) -> dict:
    return {"endpoint": endpoint, "version": version, "limit": limit}
```

### Query + Wildcard

```python
@mcp.resource("files://{path*}{?encoding,lines}")
def read_file(path: str, encoding: str = "utf-8", lines: int = 100) -> str:
    return read_file_content(path, encoding, lines)
```

### Multiple Templates per Function

```python
def lookup_user(name: str | None = None, email: str | None = None) -> dict:
    if email:
        return find_user_by_email(email)
    elif name:
        return find_user_by_name(name)
    return {"error": "No parameters"}

mcp.resource("users://email/{email}")(lookup_user)
mcp.resource("users://name/{name}")(lookup_user)
```

### Resource Error Handling

```python
from fastmcp.exceptions import ResourceError

@mcp.resource("resource://data")
def get_data() -> str:
    # ResourceError always sent to client
    raise ResourceError("Data not found")

@mcp.resource("resource://sensitive")
def get_sensitive() -> str:
    # Masked if mask_error_details=True
    raise ValueError("Sensitive internal error")
```

## Prompts

Reusable message templates for LLM interactions.

### Basic Prompt

```python
@mcp.prompt
def analyze_code(code: str) -> str:
    """Analyze code for issues"""
    return f"Please analyze this code for potential issues:\n\n{code}"
```

### Prompt with Multiple Messages

```python
from mcp.types import PromptMessage
from mcp.types import TextContent

@mcp.prompt
def code_review(code: str) -> list[PromptMessage]:
    return [
        PromptMessage(
            role="user",
            content=TextContent(type="text", text=f"Review this code:\n{code}")
        ),
    ]
```

### Prompt Arguments

```python
@mcp.prompt(
    name="translate",
    description="Translate text between languages"
)
def translate(
    text: str,
    source_lang: str = "en",
    target_lang: str = "es"
) -> str:
    return f"Translate the following from {source_lang} to {target_lang}:\n\n{text}"
```

## Context

Access MCP features inside components:

```python
from fastmcp import Context

@mcp.tool
async def my_tool(ctx: Context) -> str:
    # Logging
    await ctx.info("Processing")
    await ctx.debug("Details...")
    await ctx.warning("Warning!")
    await ctx.error("Error!")

    # Progress reporting
    await ctx.report_progress(progress=50, total=100)

    # Read resources
    resource = await ctx.read_resource("data://config")

    # LLM sampling
    result = await ctx.sample("Summarize this...")

    # Request info
    request_id = ctx.request_id
    client_id = ctx.client_id

    return result.text or ""
```

### Context Methods

| Method | Description |
|--------|-------------|
| `ctx.debug(msg)` | Debug logging |
| `ctx.info(msg)` | Info logging |
| `ctx.warning(msg)` | Warning logging |
| `ctx.error(msg)` | Error logging |
| `ctx.report_progress(p, t)` | Report progress |
| `ctx.read_resource(uri)` | Read a resource |
| `ctx.sample(...)` | LLM sampling |
| `ctx.set_state(key, value)` | Store session state |
| `ctx.get_state(key)` | Retrieve session state |

### Custom Dependencies

```python
from fastmcp.dependencies import Depends

def get_db():
    return Database()

@mcp.tool
def query_data(db: Database = Depends(get_db)) -> list:
    return db.query("SELECT * FROM data")
```

## Providers

Providers are sources of MCP components.

### LocalProvider (Default)

Components registered directly on the server:

```python
mcp = FastMCP("My Server")

@mcp.tool
def my_tool() -> str:
    return "result"
```

### FastMCPProvider

Mount another FastMCP server:

```python
from fastmcp.server.providers import FastMCPProvider

child = FastMCP("Child")
@child.tool
def child_tool() -> str:
    return "from child"

provider = FastMCPProvider(child)
mcp.add_provider(provider)

# Or via mount
mcp.mount(child, namespace="child")
```

### ProxyProvider

Proxy to a remote MCP server:

```python
from fastmcp.server.providers.proxy import ProxyProvider

mcp.add_provider(ProxyProvider(
    url="https://remote-server.com/mcp",
    headers={"Authorization": "Bearer token"}
))
```

### OpenAPIProvider

Create tools from OpenAPI spec:

```python
from fastmcp.server.providers.openapi import OpenAPIProvider

mcp.add_provider(OpenAPIProvider(
    spec_url="https://api.example.com/openapi.json",
    base_url="https://api.example.com"
))
```

### FileSystemProvider

Discover tools from a directory:

```python
from fastmcp.server.providers.filesystem import FileSystemProvider

mcp.add_provider(FileSystemProvider(
    path="./tools",
    watch=True  # Hot-reload on changes
))
```

### Provider-Level Transforms

```python
provider = FastMCPProvider(child)
provider.add_transform(Namespace("api"))
provider.disable(tags={"internal"})
mcp.add_provider(provider)
```

## Testing

Test your FastMCP server with pytest.

### Setup

```bash
pip install pytest-asyncio
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

### Testing with Client

```python
import pytest
from fastmcp.client import Client
from fastmcp.client.transports import FastMCPTransport

from my_project.main import mcp

@pytest.fixture
async def client():
    async with Client(transport=mcp) as client:
        yield client

async def test_list_tools(client: Client):
    tools = await client.list_tools()
    assert len(tools) == 5

async def test_call_tool(client: Client):
    result = await client.call_tool(
        name="add",
        arguments={"a": 1, "b": 2}
    )
    assert result.data == 3
```

### Parametrized Tests

```python
@pytest.mark.parametrize("a,b,expected", [
    (1, 2, 3),
    (2, 3, 5),
    (3, 4, 7),
])
async def test_add(a: int, b: int, expected: int, client: Client):
    result = await client.call_tool("add", {"a": a, "b": b})
    assert result.data == expected
```

### With inline-snapshot

```python
from inline_snapshot import snapshot

async def test_list_tools(client: Client):
    tools = await client.list_tools()
    assert tools == snapshot()  # Run with --inline-snapshot=fix
```
