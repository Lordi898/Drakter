# Client

Connect to MCP servers with the FastMCP client.

## Contents
- Creating a Client
- Transports
- Calling Tools
- Reading Resources
- Getting Prompts
- Authentication (OAuth, Bearer, CIMD)
- Sampling
- Elicitation
- Progress Monitoring
- Background Tasks
- Notifications
- Logging
- Client Roots
- Multi-Server Configuration

## Creating a Client

The client automatically selects transport based on what you pass:

```python
from fastmcp import Client
import asyncio

async def main():
    # In-memory (for testing)
    async with Client("server.py") as client:
        ...

    # HTTP server
    async with Client("http://localhost:8000/mcp") as client:
        ...

    # From config
    async with Client("fastmcp.json") as client:
        ...

asyncio.run(main())
```

### Connection Lifecycle

```python
async with Client(mcp) as client:
    # Initialization already happened
    print(f"Server: {client.initialize_result.serverInfo.name}")
    print(f"Instructions: {client.initialize_result.instructions}")

# Manual initialization
client = Client("server.py", auto_initialize=False)
async with client:
    result = await client.initialize(timeout=10.0)
    print(f"Server: {result.serverInfo.name}")
```

## Transports

### STDIO Transport

```python
from fastmcp.client.transports import StdioTransport

transport = StdioTransport(
    command="python",
    args=["my_server.py", "--verbose"],
    env={"API_KEY": "secret"},
    cwd="/path/to/server",
    keep_alive=True,  # Reuse subprocess (default)
)
client = Client(transport)
```

**Note**: STDIO servers run in isolated environments. Pass env vars explicitly.

### HTTP Transport

```python
from fastmcp.client.transports import StreamableHttpTransport

transport = StreamableHttpTransport(
    url="http://localhost:8000/mcp",
    headers={"X-Custom": "value"},
    auth="oauth",  # or BearerAuth(token)
)
client = Client(transport)
```

### In-Memory Transport

```python
from fastmcp import FastMCP, Client

mcp = FastMCP("TestServer")
client = Client(mcp)  # Direct connection, no subprocess
```

### Multi-Server Configuration

```python
config = {
    "mcpServers": {
        "weather": {
            "url": "https://weather.example.com/mcp",
        },
        "assistant": {
            "command": "python",
            "args": ["./assistant.py"],
            "env": {"LOG_LEVEL": "INFO"}
        }
    }
}

client = Client(config)

async with client:
    # Tools prefixed by server name
    weather = await client.call_tool("weather_get_forecast", {"city": "NYC"})
    answer = await client.call_tool("assistant_ask", {"question": "What?"})
```

## Calling Tools

```python
# List tools
tools = await client.list_tools()

# Call a tool
result = await client.call_tool("add", {"a": 5, "b": 3})

# With timeout
result = await client.call_tool("slow_tool", {}, timeout=60)

# With progress handler
result = await client.call_tool(
    "long_running_task",
    {"param": "value"},
    progress_handler=my_progress_handler
)
```

### Structured Results

The `.data` property provides fully hydrated Python objects:

```python
result = await client.call_tool("get_weather", {"city": "London"})

# Structured data (automatically deserialized)
weather = result.data
print(f"Temperature: {weather.temperature}C")

# Raw structured JSON
print(f"Raw: {result.structured_content}")

# Standard MCP content blocks
print(result.content[0].text)
```

**Result Properties:**

| Property | Description |
|----------|-------------|
| `.data` | Fully hydrated Python objects |
| `.content` | Standard MCP content blocks |
| `.structured_content` | Raw JSON dict |
| `.is_error` | Boolean indicating failure |

### Error Handling

```python
from fastmcp.exceptions import ToolError

try:
    result = await client.call_tool("potentially_failing_tool", {})
except ToolError as e:
    print(f"Tool failed: {e}")

# Or disable automatic raising
result = await client.call_tool("tool", {}, raise_on_error=False)
if result.is_error:
    print(f"Failed: {result.content[0].text}")
```

### Sending Metadata

```python
result = await client.call_tool(
    name="send_email",
    arguments={"to": "user@example.com"},
    meta={
        "trace_id": "abc-123",
        "request_source": "mobile_app"
    }
)
```

### Version Selection

```python
# Get highest version (default)
result = await client.call_tool("my_tool", {})

# Get specific version
result = await client.call_tool("my_tool", {}, version="1.0")
```

## Reading Resources

```python
# List resources
resources = await client.list_resources()

# Read a resource
content = await client.read_resource("resource://config")

# Read from template
content = await client.read_resource("users://123/profile")

# Specific version
content = await client.read_resource("data://config", version="1.0")
```

### Content Types

```python
content = await client.read_resource("resource://data")

for item in content:
    if hasattr(item, 'text'):
        print(f"Text: {item.text}")
        print(f"MIME: {item.mimeType}")
    elif hasattr(item, 'blob'):
        print(f"Binary: {len(item.blob)} bytes")
        with open("downloaded.png", "wb") as f:
            f.write(item.blob)
```

## Getting Prompts

```python
# List prompts
prompts = await client.list_prompts()

# Get a prompt
result = await client.get_prompt("analyze_code", {"code": "def hello(): pass"})

# Access messages
for message in result.messages:
    print(f"{message.role}: {message.content}")
```

### Argument Serialization

Complex arguments are automatically serialized to JSON:

```python
from dataclasses import dataclass

@dataclass
class UserData:
    name: str
    age: int

result = await client.get_prompt("analyze_user", {
    "user": UserData(name="Alice", age=30),  # Serialized
    "preferences": {"theme": "dark"},         # Serialized
})
```

## Authentication

### OAuth (Default)

```python
from fastmcp.client.auth import OAuth

async with Client(
    "http://localhost:8000/mcp",
    auth="oauth"  # or OAuth(scopes=["user"])
) as client:
    await client.ping()
```

**OAuth Parameters:**

| Parameter | Description |
|-----------|-------------|
| `scopes` | OAuth scopes to request |
| `client_name` | Name for dynamic registration |
| `client_id` | Pre-registered client ID |
| `client_secret` | Client secret for confidential clients |
| `client_metadata_url` | CIMD URL |
| `token_storage` | Storage backend for tokens |
| `callback_port` | Fixed callback port |

### Token Storage

```python
from key_value.aio.stores.disk import DiskStore
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper
from cryptography.fernet import Fernet
import os

encrypted_storage = FernetEncryptionWrapper(
    key_value=DiskStore(directory="~/.fastmcp/oauth-tokens"),
    fernet=Fernet(os.environ["OAUTH_STORAGE_ENCRYPTION_KEY"])
)

oauth = OAuth(token_storage=encrypted_storage)
```

### CIMD (Client ID Metadata Documents)

```python
from fastmcp.client.auth import OAuth

async with Client(
    "http://mcp-server.example.com/mcp",
    auth=OAuth(
        client_metadata_url="https://myapp.example.com/oauth/client.json",
    )
) as client:
    await client.ping()
```

### Pre-Registered Clients

```python
oauth = OAuth(
    client_id="my-registered-client-id",
    client_secret="my-client-secret",  # Optional for public clients
)
```

### Bearer Token

```python
from fastmcp.client.auth import BearerAuth

async with Client(
    "http://localhost:8000/mcp",
    auth=BearerAuth(token="your-token")
) as client:
    await client.ping()

# Or as string
async with Client("http://localhost:8000/mcp", auth="your-token") as client:
    await client.ping()
```

### Custom Headers

```python
from fastmcp.client.transports import StreamableHttpTransport

async with Client(
    transport=StreamableHttpTransport(
        "http://localhost:8000/mcp",
        headers={"X-API-Key": "your-token"},
    )
) as client:
    await client.ping()
```

## Sampling

Request LLM completions through the client:

### Handler Template

```python
from fastmcp.client.sampling import SamplingMessage, SamplingParams, RequestContext

async def sampling_handler(
    messages: list[SamplingMessage],
    params: SamplingParams,
    context: RequestContext
) -> str:
    # Extract message content
    conversation = []
    for message in messages:
        content = message.content.text if hasattr(message.content, 'text') else str(message.content)
        conversation.append(f"{message.role}: {content}")
    
    # Use the system prompt if provided
    system_prompt = params.systemPrompt or "You are a helpful assistant."
    
    # Integrate with your LLM service
    return "Generated response"

client = Client("server.py", sampling_handler=sampling_handler)
```

### Built-in Handlers

**OpenAI:**
```python
from fastmcp.client.sampling.handlers.openai import OpenAISamplingHandler

client = Client(
    "server.py",
    sampling_handler=OpenAISamplingHandler(default_model="gpt-4o"),
)
```

**Anthropic:**
```python
from fastmcp.client.sampling.handlers.anthropic import AnthropicSamplingHandler

client = Client(
    "server.py",
    sampling_handler=AnthropicSamplingHandler(default_model="claude-sonnet-4-5"),
)
```

**Google Gemini:**
```python
from fastmcp.client.sampling.handlers.google_genai import GoogleGenAISamplingHandler

client = Client(
    "server.py",
    sampling_handler=GoogleGenAISamplingHandler(default_model="gemini-2.0-flash"),
)
```

Install extras: `pip install fastmcp[openai]`, `fastmcp[anthropic]`, or `fastmcp[gemini]`.

## Elicitation

Handle server requests for user input:

```python
from fastmcp.client.elicitation import ElicitResult

async def elicitation_handler(
    message: str,
    response_type: type | None,
    params,
    context
) -> ElicitResult | object:
    print(f"Server asks: {message}")
    user_response = input("Your response: ")
    
    if not user_response:
        return ElicitResult(action="decline")
    if user_response == "cancel":
        return ElicitResult(action="cancel")
    
    return response_type(value=user_response)  # Implicit accept

client = Client("server.py", elicitation_handler=elicitation_handler)
```

**Actions:** `accept`, `decline`, `cancel`

## Progress Monitoring

```python
async def progress_handler(progress: float, total: float | None, message: str | None):
    if total is not None:
        percentage = (progress / total) * 100
        print(f"Progress: {percentage:.1f}% - {message or ''}")
    else:
        print(f"Progress: {progress}")

# Client-level
client = Client("server.py", progress_handler=progress_handler)

# Per-call
result = await client.call_tool(
    "long_operation",
    {},
    progress_handler=my_progress_handler
)
```

## Background Tasks

```python
# Start a background task
task = await client.call_tool("slow_computation", {"duration": 10}, task=True)

print(f"Task started: {task.task_id}")

# Check status
status = await task.status()
print(f"{status.status}: {status.statusMessage}")

# Wait for result
result = await task.result()

# Or with timeout
status = await task.wait(timeout=30.0, state="completed")

# Cancel
await task.cancel()
```

### Status Callbacks

```python
def on_status_change(status):
    print(f"Task {status.taskId}: {status.status} - {status.statusMessage}")

task.on_status_change(on_status_change)
```

### Graceful Degradation

```python
task = await client.call_tool("my_tool", args, task=True)

if task.returned_immediately:
    print("Server executed immediately (no background support)")
else:
    print("Running in background")

result = await task.result()  # Works either way
```

## Notifications

### Simple Handler

```python
async def message_handler(message):
    if hasattr(message, 'root'):
        method = message.root.method
        if method == "notifications/tools/list_changed":
            print("Tools have changed")

client = Client("server.py", message_handler=message_handler)
```

### MessageHandler Class

```python
from fastmcp.client.messages import MessageHandler
import mcp.types

class MyHandler(MessageHandler):
    async def on_tool_list_changed(self, notification):
        print("Tool list changed")

    async def on_resource_list_changed(self, notification):
        print("Resource list changed")

    async def on_progress(self, notification):
        print(f"Progress: {notification.progress}")

client = Client("server.py", message_handler=MyHandler())
```

## Logging

```python
from fastmcp.client.logging import LogMessage

async def log_handler(message: LogMessage):
    msg = message.data.get('msg')
    extra = message.data.get('extra')
    level = message.level.upper()
    print(f"[{level}] {msg}")

client = Client("server.py", log_handler=log_handler)
```

## Client Roots

Provide filesystem roots to the server:

```python
# Static
client = Client("server.py", roots=["/path/to/root1", "/path/to/root2"])

# Dynamic
from fastmcp.client.roots import RequestContext

async def roots_callback(context: RequestContext) -> list[str]:
    return ["/path/to/root1", "/path/to/root2"]

client = Client("server.py", roots=roots_callback)
```

## Complete Example

```python
from fastmcp import Client
from fastmcp.client.auth import OAuth
import asyncio

async def main():
    async with Client(
        "http://localhost:8000/mcp",
        auth=OAuth(scopes=["user"])
    ) as client:
        # Discover capabilities
        tools = await client.list_tools()
        print(f"Available tools: {[t.name for t in tools]}")
        
        # Call a tool
        result = await client.call_tool("add", {"a": 5, "b": 3})
        print(f"Result: {result.data}")
        
        # Read a resource
        config = await client.read_resource("resource://config")
        print(f"Config: {config[0].text}")

asyncio.run(main())
```
