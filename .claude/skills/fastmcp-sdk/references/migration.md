# Migration

Upgrade guides for FastMCP and MCP configuration.

## Contents
- Upgrading from MCP SDK
- MCP Configuration Format
- MCPConfig Classes

## Upgrading from MCP SDK

If your server starts with `from mcp.server.fastmcp import FastMCP`, you're using FastMCP 1.0 (bundled with v1 of the `mcp` package). Upgrading is straightforward.

### Quick Upgrade

```python
# Before
from mcp.server.fastmcp import FastMCP

# After
from fastmcp import FastMCP
```

Install the standalone package:

```bash
pip install --upgrade fastmcp
# or
uv add fastmcp
```

### Constructor Changes

Transport settings moved from constructor to `run()`:

```python
# Before
mcp = FastMCP("my-server", host="0.0.0.0", port=8080)
mcp.run()

# After
mcp = FastMCP("my-server")
mcp.run(transport="http", host="0.0.0.0", port=8080)
```

### Prompts

Use FastMCP's `Message` class instead of `mcp.types.PromptMessage`:

```python
# Before
from mcp.types import PromptMessage, TextContent

@mcp.prompt
def review(code: str):
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=f"Review: {code}")
    )

# After (simple string)
@mcp.prompt
def review(code: str) -> str:
    return f"Please review this code:\n\n{code}"

# After (multi-turn)
from fastmcp.prompts import Message

@mcp.prompt
def debug(error: str) -> list[Message]:
    return [
        Message(f"I'm seeing this error:\n\n{error}"),
        Message("I'll help debug that. Share the code?", role="assistant"),
    ]
```

### Type Imports

| mcp Package | FastMCP Equivalent |
|-------------|-------------------|
| `mcp.types.TextContent(type="text", text=str(x))` | Just return `x` from tool |
| `mcp.types.ImageContent(...)` | `fastmcp.utilities.types.Image` |
| `mcp.types.PromptMessage(...)` | `fastmcp.prompts.Message` |
| `from mcp.server.stdio import stdio_server` | Not needed - `mcp.run()` handles it |

### Decorated Functions

Decorators now return the original function (callable for testing):

```python
@mcp.tool
def greet(name: str) -> str:
    return f"Hello, {name}!"

# This works now
assert greet("World") == "Hello, World!"
```

For legacy behavior, set `FASTMCP_DECORATOR_MODE=object` (temporary compatibility).

### Verify Upgrade

```bash
# Check version
fastmcp version

# Run server
python my_server.py

# Inspect components
fastmcp inspect my_server.py
```

## MCP Configuration Format

The canonical MCP configuration format for server definitions.

### Basic Structure

```json
{
    "mcpServers": {
        "my-server": {
            "command": "uv",
            "args": ["run", "fastmcp", "run", "server.py"],
            "env": {"API_KEY": "secret"},
            "timeout": 30000,
            "description": "My MCP server"
        }
    }
}
```

### StdioMCPServer

For local subprocess servers:

```json
{
    "command": "python",
    "args": ["server.py"],
    "env": {"API_KEY": "secret"},
    "cwd": "/path/to/project",
    "timeout": 30000,
    "description": "Local server"
}
```

### RemoteMCPServer

For HTTP/SSE servers:

```json
{
    "url": "https://api.example.com/mcp",
    "headers": {
        "Authorization": "Bearer token"
    },
    "timeout": 30000,
    "description": "Remote server"
}
```

## MCPConfig Classes

### StdioMCPServer

```python
from fastmcp.mcp_config import StdioMCPServer

server = StdioMCPServer(
    command="python",
    args=["server.py"],
    env={"API_KEY": "secret"},
    timeout=30000
)

# Convert to transport
transport = server.to_transport()
```

### RemoteMCPServer

```python
from fastmcp.mcp_config import RemoteMCPServer

server = RemoteMCPServer(
    url="https://api.example.com/mcp",
    headers={"Authorization": "Bearer token"}
)

# Convert to transport (auto-detects http vs sse)
transport = server.to_transport()
```

### MCPConfig

```python
from fastmcp.mcp_config import MCPConfig

# Create from dict
config = MCPConfig.from_dict({
    "mcpServers": {
        "weather": {"url": "https://weather.example.com/mcp"},
        "calendar": {"url": "https://calendar.example.com/mcp"}
    }
})

# Add a server
config.add_server("tasks", StdioMCPServer(
    command="python",
    args=["tasks_server.py"]
))

# Save to file
config.write_to_file(Path("mcp.json"))

# Load from file
config = MCPConfig.from_file(Path("mcp.json"))

# Convert to dict
data = config.to_dict()
```

### CanonicalMCPConfig

Strictly canonical format (no FastMCP extensions):

```python
from fastmcp.mcp_config import CanonicalMCPConfig

config = CanonicalMCPConfig.from_file(Path("mcp.json"))
```

### Utility Functions

```python
from fastmcp.mcp_config import (
    infer_transport_type_from_url,
    update_config_file
)

# Infer transport from URL
transport_type = infer_transport_type_from_url("https://api.example.com/sse")
# Returns: "sse" or "http"

# Update config file preserving existing fields
update_config_file(
    Path("mcp.json"),
    "my-server",
    StdioMCPServer(command="python", args=["new_server.py"])
)
```

## Transforming Configurations

MCPConfig supports tool transformations and filtering:

```python
from fastmcp.mcp_config import MCPConfig, TransformingStdioMCPServer
from fastmcp.server.transforms import NamespaceTransform

server = TransformingStdioMCPServer(
    command="python",
    args=["server.py"],
    transforms=[NamespaceTransform(prefix="api")]
)
```
