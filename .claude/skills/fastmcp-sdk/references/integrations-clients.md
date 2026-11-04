# Client Integrations

Connect FastMCP servers to LLM clients and applications.

## Contents
- Claude Desktop
- Claude Code
- Cursor
- ChatGPT
- Gemini
- Anthropic API
- OpenAI API

## Claude Desktop

```bash
# Install server
fastmcp install server.py --client claude-desktop

# With environment
fastmcp install server.py --client claude-desktop --env API_KEY=secret
```

### Manual Configuration

Edit Claude's config file:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp", "fastmcp", "run", "server.py"]
    }
  }
}
```

### With Environment Variables

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp", "fastmcp", "run", "server.py"],
      "env": {
        "API_KEY": "your-api-key"
      }
    }
  }
}
```

## Claude Code

```bash
# Install server
fastmcp install server.py --client claude-code

# With scope
fastmcp install server.py --client claude-code --scope project
```

### Manual Configuration

Add to `.claude/settings.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "server.py"]
    }
  }
}
```

## Cursor

```bash
# Install to current project
fastmcp install server.py --client cursor

# With dependencies
fastmcp install server.py --client cursor --with pandas
```

### Manual Configuration

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": ["run", "fastmcp", "run", "server.py"]
    }
  }
}
```

## ChatGPT

ChatGPT supports MCP servers via the Actions feature.

1. Deploy your server with HTTP transport
2. Add the server URL to ChatGPT Actions
3. Configure authentication if needed

## Gemini

### Gemini CLI

```bash
# Add to Gemini CLI
fastmcp install server.py --client gemini-cli
```

### Gemini API

Use the FastMCP client to connect from your Gemini application:

```python
from fastmcp import Client
import google.generativeai as genai

async def call_mcp_tool(prompt: str):
    async with Client("http://localhost:8000/mcp") as mcp:
        tools = await mcp.list_tools()
        # Use tools with Gemini
```

## Anthropic API

Connect FastMCP servers to the Anthropic Messages API:

```python
import anthropic
from fastmcp import FastMCP

mcp = FastMCP("Dice Roller")

@mcp.tool
def roll_dice(n_dice: int) -> list[int]:
    """Roll n_dice 6-sided dice."""
    return [random.randint(1, 6) for _ in range(n_dice)]

# Use with Anthropic
client = anthropic.Anthropic()

response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Roll some dice!"}],
    mcp_servers=[
        {
            "type": "url",
            "url": "http://localhost:8000/mcp/",
            "name": "dice-server",
        }
    ],
    extra_headers={"anthropic-beta": "mcp-client-2025-04-04"}
)
```

### With Authentication

```python
response = client.beta.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{"role": "user", "content": "Roll some dice!"}],
    mcp_servers=[
        {
            "type": "url",
            "url": "http://localhost:8000/mcp/",
            "name": "dice-server",
            "authorization_token": "your-token"
        }
    ],
    extra_headers={"anthropic-beta": "mcp-client-2025-04-04"}
)
```

## OpenAI API

Connect via the FastMCP client:

```python
from openai import OpenAI
from fastmcp import Client

async def use_mcp_with_openai():
    async with Client("http://localhost:8000/mcp") as mcp:
        # Get tools from MCP server
        tools = await mcp.list_tools()
        
        # Convert to OpenAI format
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
        
        # Use with OpenAI
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": "Hello!"}],
            tools=openai_tools
        )
```

## MCP JSON Configuration

Standard MCP configuration format for any client:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "uv",
      "args": [
        "run",
        "--with", "fastmcp",
        "fastmcp", "run",
        "/path/to/server.py"
      ],
      "env": {
        "API_KEY": "your-key"
      }
    },
    "remote-server": {
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer token"
      }
    }
  }
}
```

## Common Configuration Patterns

### Local Development

```json
{
  "mcpServers": {
    "dev-server": {
      "command": "python",
      "args": ["server.py"],
      "cwd": "/path/to/project"
    }
  }
}
```

### Production HTTP

```json
{
  "mcpServers": {
    "prod-server": {
      "url": "https://api.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${API_KEY}"
      }
    }
  }
}
```

### With Docker

```json
{
  "mcpServers": {
    "docker-server": {
      "command": "docker",
      "args": [
        "run", "--rm",
        "-e", "API_KEY",
        "my-mcp-server:latest"
      ],
      "env": {
        "API_KEY": "your-key"
      }
    }
  }
}
```
