# Utilities

Exceptions, decorators, experimental features, and contrib modules.

## Contents
- Exceptions
- Decorators
- Experimental Features
- Code Mode
- Contrib Modules

## Exceptions

FastMCP provides a hierarchy of exceptions:

```python
from fastmcp.exceptions import (
    FastMCPError,     # Base exception
    ValidationError,  # Parameter validation errors
    ResourceError,    # Resource operation errors
    ToolError,        # Tool operation errors
    PromptError,      # Prompt operation errors
    InvalidSignature, # Invalid function signature
    ClientError,      # Client operation errors
    NotFoundError,    # Object not found
    DisabledError,    # Object is disabled
    AuthorizationError, # Authorization check failed
)
```

### Using Exceptions

```python
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError, NotFoundError

mcp = FastMCP("Example")

@mcp.tool
def get_user(user_id: str) -> dict:
    user = find_user(user_id)
    if not user:
        raise NotFoundError(f"User {user_id} not found")
    return user

@mcp.tool
def protected_action(ctx: Context) -> str:
    if not is_authorized(ctx):
        raise AuthorizationError("Unauthorized access")
    return "success"
```

## Decorators

Shared decorator utilities.

### resolve_task_config

```python
from fastmcp.decorators import resolve_task_config

# Resolve task parameter to config
config = resolve_task_config(task=True)  # Returns TaskConfig
config = resolve_task_config(task=None)  # Returns False
config = resolve_task_config(task={"ttl": 60000})  # Returns TaskConfig
```

### get_fastmcp_meta

```python
from fastmcp.decorators import get_fastmcp_meta

# Extract metadata from decorated function
meta = get_fastmcp_meta(my_tool)
if meta:
    print(f"Tool name: {meta.name}")
```

### HasFastMCPMeta Protocol

```python
from fastmcp.decorators import HasFastMCPMeta

def accepts_tool(fn: HasFastMCPMeta):
    # Function has __fastmcp_tool__ attribute
    meta = fn.__fastmcp_tool__
    return meta.name
```

## Experimental Features

Experimental features are in `fastmcp.experimental`:

```python
from fastmcp.experimental.transforms.code_mode import CodeMode
```

## Code Mode

Transform tools into discovery + execute meta-tools for LLM-driven code execution.

### Basic Setup

```python
from fastmcp import FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode

mcp = FastMCP("Server")

# Add tools...

# Apply code mode transform
mcp.add_transform(CodeMode())
```

This replaces all tools with:
- `search` - Find tools by query
- `get_schema` - Get tool schemas
- `execute` - Run Python code with `call_tool()` in scope

### SandboxProvider

Code runs in a sandbox (never use plain `exec()`):

```python
from fastmcp.experimental.transforms.code_mode import (
    CodeMode,
    MontySandboxProvider
)

sandbox = MontySandboxProvider(
    limits={
        "max_duration_secs": 5.0,
        "max_allocations": 1000,
        "max_memory": 10 * 1024 * 1024,  # 10MB
        "max_recursion_depth": 100
    }
)

mcp.add_transform(CodeMode(sandbox_provider=sandbox))
```

### Discovery Tools

Customize discovery tools:

```python
from fastmcp.experimental.transforms.code_mode import (
    CodeMode,
    Search,
    GetSchemas,
    GetTags,
    ListTools
)

mcp.add_transform(CodeMode(
    discovery_tools=[
        Search(default_detail="brief", default_limit=10),
        GetSchemas(default_detail="detailed"),
        GetTags(default_detail="full"),
        ListTools(default_detail="brief")
    ]
))
```

### Detail Levels

| Level | Description |
|-------|-------------|
| `brief` | Names and descriptions only |
| `detailed` | Compact markdown with schemas |
| `full` | Complete JSON definitions |

### Custom Sandbox

```python
from fastmcp.experimental.transforms.code_mode import SandboxProvider

class MySandbox(SandboxProvider):
    def run(self, code: str) -> Any:
        # Execute in your sandbox
        # WARNING: code is untrusted LLM output
        return my_sandbox.execute(code)
```

## Contrib Modules

Community-contributed modules in `fastmcp.contrib`:

```python
from fastmcp.contrib import my_module
```

### Contributing

To contribute a module:

1. Create directory in `src/fastmcp/contrib/your_module/`
2. Add tests in `tests/contrib/your_module/`
3. Include README.md with usage and examples
4. Submit pull request

Ideal contrib modules:
- Solve specific use cases
- Follow FastMCP coding standards
- Have comprehensive documentation
- Include tests
- Document additional dependencies

## Dependency Injection

FastMCP provides dependency injection via `Depends`:

```python
from fastmcp.dependencies import Depends

def get_database():
    return Database()

@mcp.tool
def query(db = Depends(get_database)) -> list:
    return db.query("SELECT * FROM data")
```

### Context Dependencies

```python
from fastmcp.dependencies import CurrentContext, CurrentFastMCP

@mcp.tool
def with_context(
    ctx = CurrentContext(),
    mcp = CurrentFastMCP()
) -> str:
    return f"Request: {ctx.request_id}"
```

### Docket Dependencies

For task-related dependencies (requires `fastmcp[tasks]`):

```python
from fastmcp.dependencies import CurrentDocket, CurrentWorker
```
