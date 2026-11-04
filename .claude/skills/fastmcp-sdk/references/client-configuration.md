# Client Configuration

Generate MCP client configurations for Claude, Cursor, VS Code, and other MCP clients.

## Contents
- MCP JSON Generation
- Client-Specific Setup
- Configuration Options
- Examples

## MCP JSON Generation

Generate configuration for any MCP-compatible client:

```bash
fastmcp install mcp-json server.py
```

Output:

```json
{
  "My Server": {
    "command": "uv",
    "args": [
      "run",
      "--with",
      "fastmcp",
      "fastmcp",
      "run",
      "/absolute/path/to/server.py"
    ]
  }
}
```

## Client-Specific Setup

### Claude Code

```bash
fastmcp install claude-code server.py
```

### Claude Desktop

```bash
fastmcp install claude-desktop server.py
```

### Cursor

```bash
fastmcp install cursor server.py
```

### Manual Configuration

Add generated JSON to client's configuration file:

| Client | Config Location |
|--------|-----------------|
| Claude Desktop | `~/.claude/claude_desktop_config.json` |
| Cursor | `~/.cursor/mcp.json` |
| VS Code | `.vscode/mcp.json` |

## Configuration Options

### Server Name

```bash
# Use server's built-in name
fastmcp install mcp-json server.py

# Override with custom name
fastmcp install mcp-json server.py --name "Custom Server Name"
```

### Dependencies

```bash
# Single package
fastmcp install mcp-json server.py --with pandas

# Multiple packages
fastmcp install mcp-json server.py --with pandas --with requests --with httpx

# Editable local package
fastmcp install mcp-json server.py --with-editable ./my-package

# From requirements file
fastmcp install mcp-json server.py --with-requirements requirements.txt
```

### Environment Variables

```bash
# Individual variables
fastmcp install mcp-json server.py \
  --env API_KEY=your-key \
  --env DEBUG=true

# From .env file
fastmcp install mcp-json server.py --env-file .env
```

### Python Version and Project

```bash
# Use specific Python version
fastmcp install mcp-json server.py --python 3.11

# Run within project directory
fastmcp install mcp-json server.py --project /path/to/project
```

### Server Object Selection

```bash
# Auto-detect (looks for 'mcp', 'server', or 'app')
fastmcp install mcp-json server.py

# Explicit server object
fastmcp install mcp-json server.py:my_custom_server
```

## Clipboard Integration

Copy configuration directly:

```bash
fastmcp install mcp-json server.py --copy
```

Note: Requires `pyperclip` package.

## Examples

### Basic Server

```bash
fastmcp install mcp-json dice_server.py
```

### Production Server with Dependencies

```bash
fastmcp install mcp-json api_server.py \
  --name "Production API Server" \
  --with requests \
  --with python-dotenv \
  --env API_BASE_URL=https://api.example.com \
  --env TIMEOUT=30
```

Output:

```json
{
  "Production API Server": {
    "command": "uv",
    "args": [
      "run",
      "--with",
      "fastmcp",
      "--with",
      "python-dotenv",
      "--with",
      "requests",
      "fastmcp",
      "run",
      "/home/user/api_server.py"
    ],
    "env": {
      "API_BASE_URL": "https://api.example.com",
      "TIMEOUT": "30"
    }
  }
}
```

### Advanced Configuration

```bash
fastmcp install mcp-json ml_server.py \
  --name "ML Analysis Server" \
  --python 3.11 \
  --with-requirements requirements.txt \
  --project /home/user/ml-project \
  --env GPU_DEVICE=0
```

### Pipeline Usage

Save to file:

```bash
fastmcp install mcp-json server.py > mcp-config.json
```

Use in shell scripts:

```bash
#!/bin/bash
CONFIG=$(fastmcp install mcp-json server.py --name "CI Server")
echo "$CONFIG" | jq '."CI Server".command'
```

## Configuration Format

The output uses the standard `mcpServers` format:

```json
{
  "<server-name>": {
    "command": "<executable>",
    "args": ["<arg1>", "<arg2>", "..."],
    "env": {
      "<ENV_VAR>": "<value>"
    }
  }
}
```

To use with a client, add to the `mcpServers` object:

```json
{
  "mcpServers": {
    "My Server": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp", "fastmcp", "run", "/path/to/server.py"]
    }
  }
}
```

## fastmcp.json Configuration

For complex configurations, use a `fastmcp.json` file:

```json
{
  "$schema": "https://gofastmcp.com/public/schemas/fastmcp.json/v1.json",
  "source": {
    "path": "server.py",
    "entrypoint": "mcp"
  },
  "environment": {
    "dependencies": ["pandas", "matplotlib", "seaborn"],
    "python": "3.11"
  }
}
```

Then:

```bash
fastmcp install mcp-json fastmcp.json
```

## Requirements

- **uv**: Must be installed and in PATH
- **pyperclip** (optional): For `--copy` functionality

Install uv:

```bash
# macOS
brew install uv

# Linux/Windows
curl -LsSf https://astral.sh/uv/install.sh | sh
```
