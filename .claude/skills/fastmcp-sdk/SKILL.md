---
name: fastmcp-sdk
description: FastMCP Python SDK for building MCP (Model Context Protocol) servers, clients, and applications. Use when working with FastMCP to create MCP servers with tools, resources, and prompts; connecting to MCP servers with the FastMCP client; building interactive apps with Prefab UI or custom HTML; implementing authentication (OAuth, bearer tokens, JWT); deploying MCP servers via HTTP, SSE, or stdio; or integrating with Claude Desktop, Cursor, Anthropic API, or other MCP hosts. This is the standard framework for building MCP applications in Python.
---

# FastMCP SDK

The fast, Pythonic way to build MCP servers, clients, and applications.

## Overview

FastMCP is the standard framework for building MCP (Model Context Protocol) applications. It provides:

- **Servers**: Expose tools, resources, and prompts to LLMs
- **Clients**: Connect to any MCP server (local or remote)
- **Apps**: Give your tools interactive UIs rendered in the conversation

## Quick Start

### Installation

```bash
pip install fastmcp
# Optional extras:
pip install "fastmcp[tasks]"  # Background tasks
pip install "fastmcp[apps]"   # Prefab UI apps
```

### Create a Server

```python
from fastmcp import FastMCP

mcp = FastMCP("My Server")

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.resource("resource://greeting")
def greeting() -> str:
    return "Hello from FastMCP!"

if __name__ == "__main__":
    mcp.run()  # stdio by default
```

### Run the Server

```bash
# stdio (default, for local clients)
python server.py

# HTTP (for remote access)
python server.py --transport http --port 8000
# Or use the CLI:
fastmcp run server.py --transport http --port 8000
```

### Connect a Client

```python
from fastmcp import Client
import asyncio

async def main():
    # In-memory (testing)
    async with Client("server.py") as client:
        result = await client.call_tool("add", {"a": 5, "b": 3})
        print(result)  # 8

    # HTTP server
    async with Client("http://localhost:8000/mcp") as client:
        tools = await client.list_tools()
        result = await client.call_tool("add", {"a": 5, "b": 3})

asyncio.run(main())
```

## Core Concepts

### Components

FastMCP servers expose three main component types:

- **Tools**: Functions the LLM can call to perform actions
- **Resources**: Data sources the LLM can read (files, APIs, databases)
- **Prompts**: Reusable prompt templates for common tasks

### The Context Object

Access MCP features inside tools, resources, and prompts:

```python
from fastmcp import Context

@mcp.tool
async def my_tool(ctx: Context) -> str:
    # Logging
    await ctx.info("Processing request")
    
    # Progress reporting
    await ctx.report_progress(50, 100)
    
    # Access client info
    client_info = ctx.client_id
    
    return "Done"
```

### Transport Options

- **stdio**: Local servers, launched by the client
- **http**: Remote servers with Streamable HTTP transport
- **sse**: Server-Sent Events (legacy HTTP)

## When to Use Each Reference

### Getting Started & Configuration
- **references/getting-started.md**: Installation, upgrade guides, project configuration with fastmcp.json
- **references/migration.md**: Upgrading from MCP SDK to standalone FastMCP, MCP configuration format

### Server Development
- **references/servers-core.md**: Server basics, tools, resources, prompts, context, providers
- **references/servers-advanced.md**: Middleware, composition, transforms, pagination, versioning, visibility, background tasks, telemetry
- **references/servers-auth.md**: Authentication (OAuth, JWT, bearer tokens, token verification)
- **references/sampling.md**: LLM sampling from tools (ctx.sample, structured output, tool use, multi-turn)
- **references/prompts-api.md**: Detailed prompts API (Message, PromptResult, FunctionPrompt)

### Client Development
- **references/clients.md**: Client connections, transports, tools, resources, sampling, elicitation, tasks, message handlers
- **references/client-configuration.md**: Client configuration options, connection settings, timeout configuration

### Apps (Interactive UIs)
- **references/apps.md**: Prefab UI apps, custom HTML apps, chart/table/form patterns

### CLI & Deployment
- **references/cli.md**: CLI commands (run, dev, install, inspect, generate-cli, discover)
- **references/deployment.md**: HTTP deployment, ASGI integration, storage backends, Prefect Horizon

### Integrations
- **references/integrations-auth.md**: Auth providers (Auth0, Azure, Cognito, GitHub, Google, etc.)
- **references/integrations-clients.md**: Client integrations (Claude Desktop, Cursor, ChatGPT, Gemini, etc.)
- **references/integrations-apis.md**: API integrations (Anthropic, OpenAI, FastAPI, OpenAPI), MCP configuration format

### Utilities
- **references/utilities.md**: Exceptions, decorators, experimental features (Code Mode), contrib modules

## Common Patterns

### Tool with Validation

```python
from typing import Annotated
from pydantic import Field

@mcp.tool
def search(
    query: Annotated[str, Field(min_length=1, max_length=100)],
    limit: Annotated[int, Field(ge=1, le=100)] = 10
) -> list[dict]:
    """Search with validated parameters"""
    return search_database(query, limit)
```

### Resource Template

```python
@mcp.resource("users://{user_id}/profile")
def get_user_profile(user_id: str) -> str:
    """Get user profile by ID"""
    return json.dumps(fetch_user(user_id))
```

### Background Task

```python
@mcp.tool(task=True)
async def process_large_file(file_path: str) -> str:
    """Long-running operation with background execution"""
    for i in range(100):
        await asyncio.sleep(1)
        # Client can poll for status
    return "Complete"
```

### Authenticated Server

```python
from fastmcp.server.auth import JWTVerifier

auth = JWTVerifier(
    public_key="-----BEGIN PUBLIC KEY-----...",
    audience="my-api"
)

mcp = FastMCP("Secure Server", auth=auth)
```

### HTTP Deployment with CORS

```python
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

mcp.run(transport="http", middleware=middleware)
```

## Key Links

- Documentation: https://gofastmcp.com
- GitHub: https://github.com/fastmcp/fastmcp
- MCP Spec: https://modelcontextprotocol.io
- Prefect Horizon (hosting): https://www.prefect.io/horizon
