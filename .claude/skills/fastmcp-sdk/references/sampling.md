# Sampling

Request LLM text generation from the client or a configured provider.

## Contents
- Overview
- System Prompts
- Model Preferences
- Multi-Turn Conversations
- Fallback Handlers
- Structured Output
- Tool Use
- Advanced Control

## Overview

The simplest use of sampling is passing a prompt string to `ctx.sample()`:

```python
from fastmcp import FastMCP, Context

mcp = FastMCP()

@mcp.tool
async def summarize(content: str, ctx: Context) -> str:
    """Generate a summary of the provided content."""
    result = await ctx.sample(f"Please summarize this:\n\n{content}")
    return result.text or ""
```

The `SamplingResult` provides:
- `.text` - The generated text (or JSON for structured output)
- `.result` - The typed result (same as `.text` for plain text, or validated object for structured)
- `.history` - All messages exchanged during sampling

## System Prompts

Control the LLM's role and behavior:

```python
@mcp.tool
async def generate_code(concept: str, ctx: Context) -> str:
    """Generate a Python code example for a concept."""
    result = await ctx.sample(
        messages=f"Write a Python example demonstrating '{concept}'.",
        system_prompt=(
            "You are an expert Python programmer. "
            "Provide concise, working code without explanations."
        ),
        temperature=0.7,
        max_tokens=300
    )
    return f"```python\n{result.text}\n```"
```

Parameters:
- `temperature` - Controls randomness (0.0 = deterministic, 1.0 = creative)
- `max_tokens` - Maximum tokens to generate

## Model Preferences

Hint which LLM the client should use:

```python
@mcp.tool
async def technical_analysis(data: str, ctx: Context) -> str:
    """Analyze data using a reasoning-focused model."""
    result = await ctx.sample(
        messages=f"Analyze this data:\n\n{data}",
        model_preferences=["claude-opus-4-5", "gpt-5-2"],
        temperature=0.2,
    )
    return result.text or ""
```

Model preferences are hints, not requirements - the actual model depends on client availability.

## Multi-Turn Conversations

Construct a list of `SamplingMessage` objects for context:

```python
from mcp.types import SamplingMessage, TextContent

@mcp.tool
async def contextual_analysis(query: str, data: str, ctx: Context) -> str:
    """Analyze data with conversational context."""
    messages = [
        SamplingMessage(
            role="user",
            content=TextContent(type="text", text=f"Here's my data: {data}"),
        ),
        SamplingMessage(
            role="assistant",
            content=TextContent(type="text", text="I see the data. What would you like to know?"),
        ),
        SamplingMessage(
            role="user",
            content=TextContent(type="text", text=query),
        ),
    ]
    result = await ctx.sample(messages=messages)
    return result.text or ""
```

## Fallback Handlers

Client support for sampling is optional. Configure a fallback handler for guaranteed support:

```python
from fastmcp import FastMCP
from fastmcp.client.sampling.handlers.openai import OpenAISamplingHandler

server = FastMCP(
    name="My Server",
    sampling_handler=OpenAISamplingHandler(default_model="gpt-4o-mini"),
    sampling_handler_behavior="fallback",
)
```

The `sampling_handler_behavior` parameter:
- `"fallback"` (default) - Use handler only when client doesn't support sampling
- `"always"` - Always use handler, bypassing the client

Install handlers with: `pip install fastmcp[openai]` or `pip install fastmcp[anthropic]`

## Structured Output

Use `result_type` for validated, typed data:

```python
from pydantic import BaseModel

class SentimentResult(BaseModel):
    sentiment: str
    confidence: float
    reasoning: str

@mcp.tool
async def analyze_sentiment(text: str, ctx: Context) -> SentimentResult:
    """Analyze text sentiment with structured output."""
    result = await ctx.sample(
        messages=f"Analyze the sentiment of: {text}",
        result_type=SentimentResult,
    )
    return result.result  # A validated SentimentResult object
```

`result_type` accepts:
- Pydantic models
- Dataclasses
- Basic types: `int`, `list[str]`, `dict[str, int]`

### Structured Output with Tools

Combine structured output with tools for agentic workflows:

```python
class ResearchResult(BaseModel):
    summary: str
    sources: list[str]
    confidence: float

def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

def fetch_url(url: str) -> str:
    """Fetch content from a URL."""
    return f"Content from: {url}"

@mcp.tool
async def research(topic: str, ctx: Context) -> ResearchResult:
    """Research a topic and return structured findings."""
    result = await ctx.sample(
        messages=f"Research: {topic}",
        tools=[search, fetch_url],
        result_type=ResearchResult,
    )
    return result.result
```

## Tool Use

Enable agentic workflows where the LLM can call functions:

### Defining Tools

```python
from fastmcp import FastMCP, Context

def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

def get_time() -> str:
    """Get the current time."""
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")

mcp = FastMCP()

@mcp.tool
async def research(question: str, ctx: Context) -> str:
    """Answer questions using available tools."""
    result = await ctx.sample(
        messages=question,
        tools=[search, get_time],
    )
    return result.text or ""
```

FastMCP automatically handles the tool execution loop.

### Custom Tool Definitions

```python
from fastmcp.server.sampling import SamplingTool

tool = SamplingTool.from_function(
    my_func,
    name="custom_name",
    description="Custom description"
)

result = await ctx.sample(messages="...", tools=[tool])
```

### Error Handling

By default, tool errors are sent back to the LLM. Use `mask_error_details=True` for security:

```python
result = await ctx.sample(
    messages=question,
    tools=[search],
    mask_error_details=True,  # Generic error messages only
)
```

Use `ToolError` to provide specific error messages that bypass masking:

```python
from fastmcp.exceptions import ToolError

def search(query: str) -> str:
    if not query.strip():
        raise ToolError("Search query cannot be empty")
    return f"Results for: {query}"
```

### Concurrent Tool Execution

By default, tools execute sequentially. Enable parallel execution:

```python
result = await ctx.sample(
    messages="Research these three topics",
    tools=[search, fetch_url],
    tool_concurrency=0,  # Unlimited parallel execution
)
```

`tool_concurrency` values:
- `None` (default) - Sequential execution
- `0` - Unlimited parallel execution
- `N > 0` - At most N tools concurrently

Mark tools that must not run concurrently:

```python
db_writer = SamplingTool.from_function(
    write_to_db,
    sequential=True,  # Forces sequential execution
)
```

## Advanced Control

Use `sample_step()` for fine-grained control over each step.

### Basic Loop

```python
from mcp.types import SamplingMessage

@mcp.tool
async def controlled_agent(question: str, ctx: Context) -> str:
    """Agent with manual loop control."""
    messages: list[str | SamplingMessage] = [question]

    while True:
        step = await ctx.sample_step(
            messages=messages,
            tools=[search, get_time],
        )

        if step.is_tool_use:
            for call in step.tool_calls:
                print(f"Called tool: {call.name}")

        if not step.is_tool_use:
            return step.text or ""

        messages = step.history
```

### SampleStep Properties

| Property | Description |
|----------|-------------|
| `is_tool_use` | True if the LLM requested tool calls |
| `tool_calls` | List of tool calls requested (if any) |
| `text` | The text content (if any) |
| `history` | All messages exchanged so far |

### Manual Tool Execution

```python
from mcp.types import SamplingMessage, ToolResultContent, TextContent

step = await ctx.sample_step(
    messages=messages,
    tools=list(tools.values()),
    execute_tools=False,  # Don't auto-execute
)

if step.is_tool_use:
    tool_results = []
    for call in step.tool_calls:
        fn = tools[call.name]
        result = fn(**call.input)
        tool_results.append(
            ToolResultContent(
                type="tool_result",
                toolUseId=call.id,
                content=[TextContent(type="text", text=result)],
            )
        )

    messages = list(step.history)
    messages.append(SamplingMessage(role="user", content=tool_results))
```

Report errors with `isError=True`:

```python
tool_result = ToolResultContent(
    type="tool_result",
    toolUseId=call.id,
    content=[TextContent(type="text", text="Permission denied")],
    isError=True,
)
```

## Method Reference

### ctx.sample()

Request text generation, running to completion automatically.

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `messages` | `str \| list[str \| SamplingMessage]` | The prompt to send |
| `system_prompt` | `str \| None` | Instructions for LLM behavior |
| `temperature` | `float \| None` | Randomness (0.0-1.0) |
| `max_tokens` | `int \| None` | Maximum tokens to generate |
| `model_preferences` | `str \| list[str] \| None` | Hints for model selection |
| `tools` | `list[Callable] \| None` | Functions the LLM can call |
| `result_type` | `type[T] \| None` | Type for validated structured output |
| `mask_error_details` | `bool \| None` | Mask detailed error messages |
| `tool_concurrency` | `int \| None` | Parallel tool execution control |

**Returns:** `SamplingResult[T]`
- `.text` - Raw text response
- `.result` - Typed result (validated for structured output)
- `.history` - All messages exchanged

### ctx.sample_step()

Make a single LLM sampling call for fine-grained control.

**Additional Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `tool_choice` | `str \| None` | `"auto"`, `"required"`, or `"none"` |
| `execute_tools` | `bool` | Execute tool calls automatically (default: True) |

**Returns:** `SampleStep`
- `.response` - Raw LLM response
- `.history` - All messages exchanged
- `.is_tool_use` - True if tool calls requested
- `.tool_calls` - List of tool calls (if any)
- `.text` - Text content (if any)
