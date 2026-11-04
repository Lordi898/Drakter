# Prompts API

Detailed API for FastMCP prompts.

## Contents
- Message Class
- PromptResult
- PromptArgument
- FunctionPrompt
- Prompt Decorator
- Docket Integration

## Message Class

Wrapper for prompt messages with auto-serialization.

```python
from fastmcp.prompts import Message

# String content
msg = Message("Hello, World!")

# With role (defaults to "user")
msg = Message("I can help with that", role="assistant")

# Complex content (auto-serialized to JSON)
msg = Message({"data": [1, 2, 3], "count": 3})

# Convert to MCP format
mcp_msg = msg.to_mcp_prompt_message()
```

Message accepts any content type:
- Strings pass through
- Dicts/lists are JSON-serialized
- Pydantic models are JSON-serialized

## PromptResult

Canonical result type for prompt rendering with explicit control.

```python
from fastmcp.prompts import PromptResult, Message

# Single message
result = PromptResult(messages=[Message("Analyze this code")])

# With description
result = PromptResult(
    description="Code review prompt",
    messages=[
        Message("Review this code:"),
        Message(code_content)
    ]
)

# With metadata
result = PromptResult(
    messages=[Message("Hello")],
    meta={"version": "1.0"}
)

# Convert to MCP format
mcp_result = result.to_mcp_prompt_result()
```

## PromptArgument

Define arguments that prompts accept.

```python
from fastmcp.prompts import PromptArgument

arg = PromptArgument(
    name="code",
    description="The code to analyze",
    required=True
)

arg_optional = PromptArgument(
    name="language",
    description="Programming language",
    required=False
)
```

## FunctionPrompt

A prompt created from a Python function.

```python
from fastmcp.prompts import FunctionPrompt, Message

@mcp.prompt
def analyze(code: str, language: str = "python") -> list[Message]:
    """Analyze code for issues"""
    return [
        Message(f"Analyze this {language} code:"),
        Message(code)
    ]

# Access the prompt object
prompt = FunctionPrompt.from_function(analyze)

# Render with arguments
result = prompt.render({"code": "def hello(): pass", "language": "python"})
```

### Return Types

Functions can return:
- `str` → Wrapped as single user Message
- `list[Message | str]` → Converted to list[Message]
- `PromptResult` → Used directly

### From Function

```python
from fastmcp.prompts import FunctionPrompt

def my_prompt_fn(text: str) -> str:
    return f"Process: {text}"

prompt = FunctionPrompt.from_function(my_prompt_fn)
```

## Prompt Decorator

Standalone decorator to mark functions as prompts.

```python
from fastmcp.prompts import prompt

@prompt
def summarize(text: str) -> str:
    """Summarize text"""
    return f"Summarize:\n\n{text}"

# Register with server
mcp.add_prompt(summarize)
```

### Decorator with Options

```python
@prompt(name="custom_name", description="Custom prompt")
def my_prompt(text: str) -> str:
    return text
```

### PromptMeta

Metadata attached by the decorator:

```python
from fastmcp.prompts import PromptMeta

# Access metadata
meta: PromptMeta = my_prompt.__fastmcp_prompt__
print(meta.name)
print(meta.description)
```

## Docket Integration

Register prompts for background execution.

### Register with Docket

```python
from fastmcp.prompts import FunctionPrompt

prompt = FunctionPrompt.from_function(my_prompt_fn)

# Register with docket
prompt.register_with_docket(docket)
```

### Schedule for Execution

```python
# Schedule background execution
execution = prompt.add_to_docket(
    docket=docket,
    arguments={"text": "long text to process"},
    task_key="task-123",
    ttl=60000  # Result available for 60 seconds
)
```

## Complete Example

```python
from fastmcp import FastMCP
from fastmcp.prompts import Message, PromptResult

mcp = FastMCP("Code Review")

@mcp.prompt
def code_review(code: str) -> PromptResult:
    """Review code for potential issues"""
    return PromptResult(
        description="Code review assistant",
        messages=[
            Message("You are a code reviewer. Analyze the following code:"),
            Message(code, role="user"),
            Message("Provide feedback on:", role="assistant"),
            Message("- Bugs and errors", role="assistant"),
            Message("- Code style and readability", role="assistant"),
            Message("- Performance concerns", role="assistant"),
        ]
    )

@mcp.prompt
def debug_session(error: str, code: str = "") -> list[Message]:
    """Start a debugging session"""
    messages = [
        Message(f"I encountered this error:\n```\n{error}\n```"),
    ]
    if code:
        messages.append(Message(f"Here's the relevant code:\n```\n{code}\n```"))
    return messages

@mcp.prompt
def translate(text: str, source: str = "en", target: str = "es") -> str:
    """Translate text between languages"""
    return f"Translate from {source} to {target}:\n\n{text}"

if __name__ == "__main__":
    mcp.run()
```
