# Getting Started

Installation, quickstart, project configuration, and upgrading.

## Contents
- Installation
- Quickstart
- Project Configuration (fastmcp.json)
- Versioning Policy
- Upgrading
- LLM-Friendly Docs

## Installation

```bash
pip install fastmcp
# Or with uv:
uv add fastmcp
```

### Optional Extras

```bash
pip install "fastmcp[tasks]"  # Background tasks
pip install "fastmcp[apps]"   # Prefab UI apps
pip install "fastmcp[azure]"  # Azure OBO features
```

### Verify Installation

```bash
fastmcp version
```

Output:
```
FastMCP version:                           3.0.0
MCP version:                               1.25.0
Python version:                            3.12.2
Platform:            macOS-15.3.1-arm64-arm-64bit
```

## Quickstart

### Create a Server

```python
from fastmcp import FastMCP

mcp = FastMCP("My MCP Server")

@mcp.tool
def greet(name: str) -> str:
    """Greet someone by name"""
    return f"Hello, {name}!"

if __name__ == "__main__":
    mcp.run()
```

### Run the Server

```bash
# stdio (default)
python server.py

# HTTP
python server.py  # with: mcp.run(transport="http", port=8000)

# Or with CLI
fastmcp run server.py
fastmcp run server.py --transport http --port 8000
```

### Connect with Client

```python
import asyncio
from fastmcp import Client

client = Client("http://localhost:8000/mcp")

async def main():
    async with client:
        result = await client.call_tool("greet", {"name": "World"})
        print(result)

asyncio.run(main())
```

### Deploy to Prefect Horizon

1. Push `server.py` to GitHub
2. Sign in to [Prefect Horizon](https://horizon.prefect.io)
3. Create project from repository with entrypoint `server.py:mcp`
4. Get URL like `https://your-project.fastmcp.app/mcp`

## Project Configuration (fastmcp.json)

Declarative configuration for reproducible deployments.

### File Structure

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "python": ">=3.10",
    "dependencies": ["pandas", "numpy"]
  },
  "deployment": {
    "transport": "stdio",
    "log_level": "INFO"
  }
}
```

### Source Configuration

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Source type: `"filesystem"` (default) |
| `path` | string | Path to Python file |
| `entrypoint` | string | Server instance name (defaults to `mcp`, `server`, or `app`) |

### Environment Configuration

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Environment type: `"uv"` (default) |
| `python` | string | Python version constraint |
| `dependencies` | list[str] | Pip packages with version specifiers |
| `requirements` | string | Path to requirements.txt |
| `project` | string | Path to project directory |
| `editable` | list[str] | Packages to install in editable mode |

### Deployment Configuration

| Field | Type | Description |
|-------|------|-------------|
| `transport` | string | Protocol: `"stdio"`, `"http"`, `"sse"` |
| `host` | string | Network interface (e.g., `"127.0.0.1"`) |
| `port` | integer | Port number |
| `path` | string | URL path for MCP endpoint |
| `log_level` | string | Verbosity: `"DEBUG"`, `"INFO"`, `"WARNING"`, `"ERROR"` |
| `env` | object | Environment variables |
| `cwd` | string | Working directory |
| `args` | list[str] | Command-line arguments |

### Environment Variable Interpolation

```json
{
  "deployment": {
    "env": {
      "API_URL": "https://api.${ENVIRONMENT}.example.com",
      "DATABASE_URL": "postgres://${DB_USER}@${DB_HOST}/mydb"
    }
  }
}
```

### Usage

```bash
# Auto-detect fastmcp.json
fastmcp run

# Explicit file
fastmcp run prod.fastmcp.json

# Override settings
fastmcp run fastmcp.json --port 8080 --transport http

# Skip environment setup
fastmcp run fastmcp.json --skip-env
```

### Pre-Building Environments

```bash
# Create persistent environment
fastmcp project prepare fastmcp.json --output-dir ./env

# Run with pre-built environment
fastmcp run fastmcp.json --project ./env
```

### Example Configurations

**Development:**
```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {"path": "src/server.py", "entrypoint": "app"},
  "environment": {"python": "3.12", "editable": ["."]},
  "deployment": {"transport": "http", "log_level": "DEBUG"}
}
```

**Production:**
```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {"path": "app/main.py", "entrypoint": "mcp_server"},
  "environment": {"requirements": "requirements/production.txt"},
  "deployment": {
    "transport": "http",
    "host": "0.0.0.0",
    "port": 3000,
    "log_level": "INFO"
  }
}
```

## Versioning Policy

FastMCP follows semantic versioning with pragmatic adaptations for the rapidly evolving MCP ecosystem.

**For production, pin to exact versions:**

```
fastmcp==3.0.0  # Good
fastmcp>=3.0.0  # Risky - may include breaking changes
```

## Upgrading

### From FastMCP 2.0

See the [upgrade guide](https://gofastmcp.com/getting-started/upgrading/from-fastmcp-2) for breaking changes and migration steps.

### From MCP SDK (FastMCP 1.0)

Usually a single import change:

```python
# Old
from mcp.server.fastmcp import FastMCP

# New
from fastmcp import FastMCP
```

See the [migration guide](https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk) for details.

## LLM-Friendly Docs

### MCP Server

Access docs via MCP at `https://gofastmcp.com/mcp`:

```python
from fastmcp import Client

async with Client("https://gofastmcp.com/mcp") as client:
    result = await client.call_tool(
        "SearchFastMcp",
        {"query": "deploy a FastMCP server"}
    )
```

### Text Formats

- [llms.txt](https://gofastmcp.com/llms.txt) - Sitemap of all pages
- [llms-full.txt](https://gofastmcp.com/llms-full.txt) - Entire docs in one file

Any page as markdown: append `.md` to URL (e.g., `/getting-started/quickstart.md`)

Copy page as markdown: `Cmd+C` / `Ctrl+C`
