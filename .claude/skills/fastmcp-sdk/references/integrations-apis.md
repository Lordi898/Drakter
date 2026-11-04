# API and Client Integrations

Integrate FastMCP with APIs, LLM providers, and MCP clients.

## Contents
- OpenAPI Integration
- FastAPI Integration
- LLM Provider Integrations
- MCP Client Integrations
- Proxy Servers

## OpenAPI Integration

Create FastMCP tools from an OpenAPI specification:

```python
from fastmcp import FastMCP
from fastmcp.server.openapi import OpenAPIProvider, RouteMap, MCPType

mcp = FastMCP("API Server")

mcp.add_provider(OpenAPIProvider(
    spec_url="https://api.example.com/openapi.json",
    base_url="https://api.example.com"
))
```

### From Local File

```python
mcp.add_provider(OpenAPIProvider(
    spec_path="./openapi.json",
    base_url="https://api.example.com"
))
```

### With Authentication

```python
mcp.add_provider(OpenAPIProvider(
    spec_url="https://api.example.com/openapi.json",
    base_url="https://api.example.com",
    headers={"Authorization": "Bearer your-token"}
))
```

### Custom Route Mapping

```python
from fastmcp.server.openapi import RouteMap, MCPType

mcp = FastMCP.from_openapi(
    spec_url="https://api.example.com/openapi.json",
    base_url="https://api.example.com",
    route_maps=[
        # GET with path params → ResourceTemplates
        RouteMap(
            methods=["GET"], 
            pattern=r".*\{.*\}.*", 
            mcp_type=MCPType.RESOURCE_TEMPLATE
        ),
        # Other GETs → Resources
        RouteMap(
            methods=["GET"], 
            pattern=r".*", 
            mcp_type=MCPType.RESOURCE
        ),
    ],
)
```

### Filter Operations

```python
provider = OpenAPIProvider(
    spec_url="https://api.example.com/openapi.json",
    base_url="https://api.example.com",
    include_operations=["get_user", "create_user"],
    # exclude_operations=["delete_user"]
)
```

## FastAPI Integration

### Generate MCP from FastAPI

```python
from fastmcp import FastMCP

# Convert existing FastAPI app
mcp = FastMCP.from_fastapi(app=app)

# Add additional tools
@mcp.tool
def custom_tool() -> str:
    return "result"
```

### Mount MCP in FastAPI

```python
from fastapi import FastAPI
from fastmcp import FastMCP

mcp = FastMCP("Analytics Tools")
mcp_app = mcp.http_app(path="/")

app = FastAPI(lifespan=mcp_app.lifespan)  # Required!
app.mount("/mcp", mcp_app)

@app.get("/api/hello")
def hello():
    return {"message": "Hello"}
```

### Offer Both REST and MCP

```python
mcp = FastMCP.from_fastapi(app=app, name="E-commerce MCP")
mcp_app = mcp.http_app(path="/")

combined_app = FastAPI(
    routes=[*mcp_app.routes, *app.routes],
    lifespan=mcp_app.lifespan,
)
```

## LLM Provider Integrations

### Anthropic API

FastMCP servers work with Anthropic's MCP connector:

```python
import anthropic

client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Roll dice!"}],
    mcp_servers=[{
        "type": "url",
        "url": "http://localhost:8000/mcp/",
        "name": "dice-server",
    }],
    extra_headers={"anthropic-beta": "mcp-client-2025-04-04"}
)
```

**With Authentication:**
```python
mcp_servers=[{
    "type": "url",
    "url": "http://localhost:8000/mcp/",
    "name": "dice-server",
    "authorization_token": "your-token"
}]
```

### Gemini SDK

```python
from fastmcp import Client
from google import genai

mcp_client = Client("server.py")
gemini_client = genai.Client()

async with mcp_client:
    response = await gemini_client.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents="Roll 3 dice!",
        config=genai.types.GenerateContentConfig(
            temperature=0,
            tools=[mcp_client.session],
        ),
    )
```

**Remote/Authenticated:**
```python
from fastmcp.client.auth import BearerAuth

mcp_client = Client(
    "https://my-server.com/mcp/",
    auth=BearerAuth("<your-token>"),
)
```

### OpenAI API

Convert MCP tools to OpenAI format:

```python
from openai import OpenAI
from fastmcp import Client
import json

async def mcp_to_openai():
    async with Client("server.py") as mcp:
        tools = await mcp.list_tools()
        
        openai_tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            }
            for tool in tools
        ]
        
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello!"}],
            tools=openai_tools
        )
        
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                result = await mcp.call_tool(
                    tool_call.function.name,
                    json.loads(tool_call.function.arguments)
                )
```

## MCP Client Integrations

### ChatGPT

ChatGPT supports MCP in **Chat Mode** (Developer Mode) and **Deep Research Mode**.

**Chat Mode (with Developer Mode):**
1. Enable Developer Mode in Settings → Connectors → Advanced
2. Create connector with server URL
3. Enable in chat via Developer Mode

**Deep Research Mode (requires search + fetch tools):**
```python
@mcp.tool()
def search(query: str) -> dict:
    """Search for records. Must return {"ids": [...]}"""
    return {"ids": ["id1", "id2"]}

@mcp.tool()
def fetch(id: str) -> dict:
    """Fetch a record by ID."""
    return {"id": id, "content": "..."}
```

**Skip confirmations for read-only tools:**
```python
@mcp.tool(annotations={"readOnlyHint": True})
def get_status() -> str:
    return "OK"
```

### Claude Code

```bash
# Install with FastMCP CLI
fastmcp install claude-code server.py

# With dependencies
fastmcp install claude-code server.py --with pandas

# With environment variables
fastmcp install claude-code server.py --env API_KEY=secret
```

### Claude Desktop

```bash
# Install with FastMCP CLI
fastmcp install claude-desktop server.py

# With dependencies
fastmcp install claude-desktop server.py --with pandas --env API_KEY=secret
```

**Note**: `uv` must be installed globally. On macOS: `brew install uv`

### Cursor

```bash
# Install with FastMCP CLI
fastmcp install cursor server.py

# Workspace installation
fastmcp install cursor server.py --workspace .
```

### Gemini CLI

```bash
# Install with FastMCP CLI
fastmcp install gemini-cli server.py
```

### Goose

```bash
# Install with FastMCP CLI
fastmcp install goose server.py
```

**Note**: Goose uses `uvx` instead of `uv run`.

### Generate MCP JSON

For any MCP-compatible client:

```bash
# Generate configuration
fastmcp install mcp-json server.py

# Copy to clipboard
fastmcp install mcp-json server.py --copy
```

## Proxy Servers

### Proxy to Remote Server

```python
from fastmcp import Client
from fastmcp.server import create_proxy

# Simple proxy
proxy = create_proxy(
    "https://remote-server.com/mcp",
    name="Remote Server Proxy"
)

if __name__ == "__main__":
    proxy.run()
```

### Authenticated Proxy

```python
from fastmcp import Client
from fastmcp.client.auth import BearerAuth
from fastmcp.server import create_proxy

client = Client(
    "https://api.example.com/mcp",
    auth=BearerAuth(token="your-access-token")
)

proxy = create_proxy(client, name="Authenticated Proxy")

if __name__ == "__main__":
    proxy.run()
```

### Claude Desktop with Remote Server

Create a local proxy that forwards to a remote HTTP server:

```python
# proxy.py
from fastmcp.server import create_proxy

proxy = create_proxy(
    "https://remote-server.com/mcp",
    name="Remote Proxy"
)

if __name__ == "__main__":
    proxy.run()  # Runs via STDIO
```

Then install in Claude Desktop:
```bash
fastmcp install claude-desktop proxy.py
```

## Custom Providers

```python
from fastmcp.server.providers import BaseProvider
from fastmcp.tools import Tool

class MyAPIProvider(BaseProvider):
    async def get_tools(self) -> list[Tool]:
        return [
            Tool(
                name="api_status",
                description="Check API status",
                parameters={},
                handler=self.check_status
            )
        ]
    
    async def check_status(self) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/status")
            return response.text

mcp.add_provider(MyAPIProvider())
```

## Integration Summary

| Target | Method |
|--------|--------|
| Anthropic | MCP connector in Messages API |
| ChatGPT | HTTP server with Developer Mode |
| Claude Code | `fastmcp install claude-code` |
| Claude Desktop | `fastmcp install claude-desktop` |
| Cursor | `fastmcp install cursor` |
| Gemini CLI | `fastmcp install gemini-cli` |
| Goose | `fastmcp install goose` |
| OpenAI | Manual tool conversion |
| Generic client | `fastmcp install mcp-json` |
