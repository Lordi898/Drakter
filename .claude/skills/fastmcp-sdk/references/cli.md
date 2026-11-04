# CLI

FastMCP command-line interface reference.

## Contents
- Running Servers
- Development Mode (Inspector)
- Installing Servers
- Inspecting Servers
- Client Commands
- Generate CLI
- Project Commands
- Background Tasks

## Running Servers

```bash
# stdio (default)
fastmcp run server.py

# HTTP
fastmcp run server.py --transport http --port 8000

# From configuration
fastmcp run fastmcp.json
```

### Entrypoints

```bash
# Inferred instance (looks for mcp, server, or app)
fastmcp run server.py

# Explicit instance
fastmcp run server.py:my_server

# Factory function
fastmcp run server.py:create_server

# Remote URL (starts local proxy)
fastmcp run https://example.com/mcp
```

### Run Options

| Option | Flag | Description |
|--------|------|-------------|
| Transport | `--transport`, `-t` | `stdio`, `http`, or `sse` |
| Host | `--host` | HTTP host (default: 127.0.0.1) |
| Port | `--port`, `-p` | HTTP port (default: 8000) |
| Path | `--path` | HTTP path (default: /mcp/) |
| Log Level | `--log-level`, `-l` | DEBUG, INFO, WARNING, ERROR, CRITICAL |
| No Banner | `--no-banner` | Suppress startup banner |
| Auto-Reload | `--reload` / `--no-reload` | Watch for file changes |
| Reload Dirs | `--reload-dir` | Directories to watch (repeatable) |
| Skip Env | `--skip-env` | Don't set up uv environment |
| Python | `--python` | Python version (e.g., 3.11) |
| Extra Packages | `--with` | Additional packages (repeatable) |
| Project | `--project` | Run within a uv project directory |
| Requirements | `--with-requirements` | Install from requirements file |

### Examples

```bash
# HTTP on custom port
fastmcp run server.py -t http -p 3000

# With dependencies
fastmcp run server.py --with pandas --with requests

# With environment
fastmcp run server.py --env API_KEY=secret

# Watch for changes
fastmcp run server.py --reload --reload-dir ./src

# Pass arguments to server
fastmcp run config_server.py -- --config config.json

# Skip environment setup
fastmcp run fastmcp.json --skip-env
```

## Development Mode (Inspector)

Run with the MCP Inspector UI:

```bash
# Launch with Inspector
fastmcp dev inspector server.py

# With dependencies
fastmcp dev inspector server.py --with pandas

# Watch for changes (default: on)
fastmcp dev inspector server.py --reload
```

### Dev Options

| Option | Flag | Description |
|--------|------|-------------|
| Editable Package | `--with-editable`, `-e` | Install in editable mode |
| Extra Packages | `--with` | Additional packages (repeatable) |
| Inspector Version | `--inspector-version` | MCP Inspector version |
| UI Port | `--ui-port` | Port for Inspector UI |
| Server Port | `--server-port` | Port for Inspector proxy |
| Auto-Reload | `--reload` / `--no-reload` | File watching (default: on) |
| Reload Dirs | `--reload-dir` | Directories to watch |
| Python | `--python` | Python version |
| Project | `--project` | Run within a uv project directory |

**Note**: The Inspector connects over stdio only. Select "STDIO" from the transport dropdown.

## Installing Servers

Install servers to MCP clients:

```bash
# Claude Desktop
fastmcp install claude-desktop server.py

# Claude Code
fastmcp install claude-code server.py

# Cursor
fastmcp install cursor server.py

# Gemini CLI
fastmcp install gemini-cli server.py

# Goose
fastmcp install goose server.py

# Generate MCP JSON
fastmcp install mcp-json server.py
```

### Install Options

| Option | Flag | Description |
|--------|------|-------------|
| Server Name | `--server-name`, `-n` | Custom name for the server |
| Editable Package | `--with-editable`, `-e` | Install in editable mode |
| Extra Packages | `--with` | Additional packages (repeatable) |
| Environment Variables | `--env` | KEY=VALUE pairs (repeatable) |
| Environment File | `--env-file`, `-f` | Load from .env file |
| Python | `--python` | Python version (e.g., 3.11) |
| Project | `--project` | Run within a uv project directory |
| Requirements | `--with-requirements` | Install from requirements file |

### Examples

```bash
# With environment variables
fastmcp install claude-desktop server.py \
    --server-name "My Server" \
    --env API_KEY=secret \
    --env DEBUG=true

# With dependencies
fastmcp install cursor server.py --with pandas

# Workspace installation (Cursor only)
fastmcp install cursor server.py --workspace .

# From config
fastmcp install claude-desktop fastmcp.json
```

### Supported Clients

| Client | Install Method |
|--------|---------------|
| `claude-code` | Claude Code's built-in MCP management |
| `claude-desktop` | Direct config file modification |
| `cursor` | Deeplink that opens Cursor for confirmation |
| `gemini-cli` | Gemini CLI's built-in MCP management |
| `goose` | Deeplink that opens Goose for confirmation |
| `mcp-json` | Generates standard MCP JSON config |

## Inspecting Servers

View server capabilities:

```bash
# Basic inspection
fastmcp inspect server.py

# JSON output (FastMCP format)
fastmcp inspect server.py --format fastmcp

# JSON output (MCP protocol format)
fastmcp inspect server.py --format mcp

# Save to file
fastmcp inspect server.py --format mcp -o manifest.json
```

### Inspect Options

| Option | Flag | Description |
|--------|------|-------------|
| Format | `--format`, `-f` | `fastmcp` or `mcp` |
| Output File | `--output`, `-o` | Save to file |

### Entrypoints

```bash
fastmcp inspect server.py                  # inferred instance
fastmcp inspect server.py:my_server        # explicit entrypoint
fastmcp inspect server.py:create_server    # factory function
fastmcp inspect fastmcp.json               # config file
```

## Client Commands

### Listing Tools

```bash
# List tools from a server
fastmcp list http://localhost:8000/mcp
fastmcp list server.py
fastmcp list weather  # name-based resolution

# With input schemas
fastmcp list server.py --input-schema

# With resources and prompts
fastmcp list server.py --resources --prompts

# JSON output
fastmcp list server.py --json
```

### List Options

| Option | Flag | Description |
|--------|------|-------------|
| Command | `--command` | Connect via stdio |
| Transport | `--transport`, `-t` | Force `http` or `sse` |
| Resources | `--resources` | Include resources |
| Prompts | `--prompts` | Include prompts |
| Input Schema | `--input-schema` | Show full input schemas |
| Output Schema | `--output-schema` | Show full output schemas |
| JSON | `--json` | Structured JSON output |
| Timeout | `--timeout` | Connection timeout |
| Auth | `--auth` | `oauth`, bearer token, or `none` |

### Calling Tools

```bash
# Basic call
fastmcp call server.py greet name=World

# With complex arguments
fastmcp call server.py create_item '{"name": "Widget", "tags": ["sale"]}'

# With base JSON and overrides
fastmcp call server.py search --input-json '{"query": "hello", "limit": 5}' limit=10

# JSON output
fastmcp call server.py get_weather city=London --json

# Skip authentication
fastmcp call http://localhost:8000/mcp my_tool --auth none
```

### Call Options

| Option | Flag | Description |
|--------|------|-------------|
| Command | `--command` | Connect via stdio |
| Transport | `--transport`, `-t` | Force `http` or `sse` |
| Input JSON | `--input-json` | Base arguments as JSON |
| JSON | `--json` | Raw JSON output |
| Timeout | `--timeout` | Connection timeout |
| Auth | `--auth` | `oauth`, bearer token, or `none` |

### Discovering Configured Servers

Find MCP servers configured in your editors:

```bash
fastmcp discover

# Filter by source
fastmcp discover --source claude-code
fastmcp discover --source cursor --source gemini --json
```

Scans: Claude Desktop, Claude Code, Cursor, Gemini CLI, Goose, and project `mcp.json`.

### Name-Based Resolution

Refer to configured servers by name:

```bash
fastmcp list weather
fastmcp call weather get_forecast city=London

# Disambiguate with source prefix
fastmcp list claude-code:my-server
fastmcp call cursor:weather get_forecast city=London
```

## Generate CLI

Scaffold a standalone typed CLI from server tool schemas:

```bash
fastmcp generate-cli server.py --output my_cli
```

Creates a typed CLI where tool names become subcommands with proper argument parsing.

## Project Commands

### Prepare Environment

```bash
# Create persistent environment
fastmcp project prepare fastmcp.json --output-dir ./env

# Run with pre-built environment
fastmcp run fastmcp.json --project ./env
```

### Configuration

```bash
# Validate configuration
fastmcp project validate fastmcp.json

# Show resolved config
fastmcp project show fastmcp.json
```

## Background Tasks

```bash
# Start a worker
fastmcp tasks worker server.py

# With concurrency
FASTMCP_DOCKET_CONCURRENCY=20 fastmcp tasks worker server.py
```

## Client Commands

Query and invoke MCP servers directly from the CLI.

### List Tools

```bash
# List tools on a server
fastmcp list server.py
fastmcp list http://localhost:8000/mcp

# JSON output
fastmcp list server.py --json

# List resources
fastmcp list server.py --resources

# List prompts
fastmcp list server.py --prompts

# With specific transport
fastmcp list http://server/mcp --transport sse

# Via command
fastmcp list --command 'npx -y @mcp/server'
```

### Call Tools

```bash
# Call a tool with arguments
fastmcp call server.py greet name=World

# Call with JSON input
fastmcp call server.py analyze --input-json '{"data": [1,2,3]}'

# Read a resource (URI contains ://)
fastmcp call server.py resource://docs/readme

# Get a prompt
fastmcp call server.py summarize --prompt data='[1,2,3]'
```

### Discover Servers

```bash
# Discover MCP servers from editor configs
fastmcp discover

# Filter by source
fastmcp discover --source claude-code
fastmcp discover --source cursor --source gemini --json

# Use discovered server
fastmcp list weather
fastmcp call cursor:weather get_forecast city=London
```

Discovery scans:
- Claude Desktop config
- Claude Code config
- Cursor config
- Gemini CLI config
- Goose config
- Project mcp.json files

## Generate CLI

Generate standalone CLI scripts from MCP servers:

```bash
# Generate CLI script
fastmcp generate-cli weather

# Specify output file
fastmcp generate-cli server.py my_cli.py

# From URL
fastmcp generate-cli http://localhost:8000/mcp

# Force overwrite
fastmcp generate-cli weather output.py -f

# Skip SKILL.md generation
fastmcp generate-cli weather --no-skill
```

This creates a Python script that can invoke the server's tools directly, plus a SKILL.md file for agent integration.

## CIMD (Client ID Metadata Document)

Generate and validate OAuth Client ID Metadata Documents:

```bash
# Generate CIMD for hosting
fastmcp cimd create

# Validate a hosted CIMD
fastmcp cimd validate https://myapp.example.com/oauth/client.json
```

The CIMD document describes your OAuth client configuration. Host it at an HTTPS URL with a non-root path, and that URL becomes your client_id.

## Authentication

When targeting HTTP URLs:

```bash
# OAuth (default)
fastmcp list http://localhost:8000/mcp

# Skip authentication
fastmcp list http://localhost:8000/mcp --auth none

# Bearer token
fastmcp list http://localhost:8000/mcp --auth "Bearer sk-..."
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `FASTMCP_DOCKET_URL` | Task backend URL |
| `FASTMCP_DOCKET_CONCURRENCY` | Worker concurrency |
| `FASTMCP_LOG_LEVEL` | Default log level |
| `FASTMCP_STATELESS_HTTP` | Enable stateless HTTP mode |

## Quick Reference

```bash
# Run
fastmcp run server.py                    # stdio
fastmcp run server.py -t http -p 8000    # HTTP

# Dev
fastmcp dev inspector server.py          # With Inspector

# Install
fastmcp install claude-desktop server.py
fastmcp install cursor server.py
fastmcp install claude-code server.py

# Inspect
fastmcp inspect server.py --json

# Client
fastmcp list server.py --resources --prompts
fastmcp call server.py tool_name arg=value
fastmcp discover
```
