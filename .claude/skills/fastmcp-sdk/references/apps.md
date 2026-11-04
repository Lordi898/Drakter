# Apps

Give your tools interactive UIs rendered directly in the conversation.

## Contents
- Overview
- Prefab Apps (Recommended)
- Custom HTML Apps
- Patterns (Charts, Tables, Forms, Status, Tabs)
- Security
- Complete Examples

## Overview

MCP Apps let your tools return interactive UIs rendered in a sandboxed iframe inside the host client. Instead of plain text, tools can show charts, tables, forms, or anything HTML can build.

FastMCP provides two approaches:

1. **Prefab Apps** - Declarative UI with Python DSL (recommended)
2. **Custom HTML Apps** - Full control with HTML/CSS/JavaScript

## Prefab Apps

Prefab UI is a declarative framework for building UIs in Python.

### Installation

```bash
pip install "fastmcp[apps]"
```

**Important**: Pin `prefab-ui` to a specific version in production:
```toml
dependencies = [
    "fastmcp[apps]",
    "prefab-ui==0.8.0",  # pin to a known working version
]
```

### Basic Prefab App

```python
from prefab_ui.components import Column, Heading, BarChart, ChartSeries
from prefab_ui.app import PrefabApp
from fastmcp import FastMCP

mcp = FastMCP("Dashboard")

@mcp.tool(app=True)
def sales_chart(year: int) -> PrefabApp:
    """Show sales data as an interactive chart."""
    data = get_sales_data(year)

    with Column(gap=4, css_class="p-6") as view:
        Heading(f"{year} Sales")
        BarChart(
            data=data,
            series=[ChartSeries(data_key="revenue", label="Revenue")],
            x_axis="month",
        )

    return PrefabApp(view=view)
```

### Return Types

**Components directly** (simplest for visual data):
```python
@mcp.tool(app=True)
def status_badge() -> Column:
    with Column(gap=2) as view:
        Heading("Status")
        Badge("Healthy", variant="success")
    return view
```

**PrefabApp** (when you need state or control):
```python
@mcp.tool(app=True)
def toggle_demo() -> PrefabApp:
    with Column(gap=4, css_class="p-6") as view:
        Button("Toggle", on_click=ToggleState("show"))
        with If("{{ show }}"):
            Badge("Visible!", variant="success")
    return PrefabApp(view=view, state={"show": False})
```

**ToolResult** (for LLM understanding):
```python
from fastmcp.tools import ToolResult

@mcp.tool(app=True)
def sales_overview(year: int) -> ToolResult:
    data = get_sales_data(year)
    total = sum(row["revenue"] for row in data)

    with Column(gap=4, css_class="p-6") as view:
        Heading("Sales Overview")
        BarChart(data=data, series=[ChartSeries(data_key="revenue")])

    return ToolResult(
        content=f"Total revenue for {year}: ${total:,}",
        structured_content=view,
    )
```

## Chart Components

### Bar Chart

```python
from prefab_ui.components import BarChart, ChartSeries

BarChart(
    data=[
        {"quarter": "Q1", "revenue": 42000, "costs": 28000},
        {"quarter": "Q2", "revenue": 51000, "costs": 31000},
    ],
    series=[
        ChartSeries(data_key="revenue", label="Revenue"),
        ChartSeries(data_key="costs", label="Costs"),
    ],
    x_axis="quarter",
    show_legend=True,
    stacked=True,       # Optional: stack bars
    horizontal=True,    # Optional: flip axes
)
```

### Area/Line Chart

```python
from prefab_ui.components import AreaChart, ChartSeries

AreaChart(
    data=[
        {"date": "Feb 1", "requests": 1200},
        {"date": "Feb 2", "requests": 1350},
    ],
    series=[ChartSeries(data_key="requests", label="Requests")],
    x_axis="date",
    curve="smooth",  # "linear", "smooth", "step"
    show_dots=True,
    height=250,
)
```

### Pie/Donut Chart

```python
from prefab_ui.components import PieChart

PieChart(
    data=[
        {"category": "Bug", "count": 23},
        {"category": "Feature", "count": 15},
    ],
    data_key="count",
    name_key="category",
    show_legend=True,
    inner_radius=60,  # Donut chart when set
)
```

## Data Tables

```python
from prefab_ui.components import DataTable, DataTableColumn

DataTable(
    columns=[
        DataTableColumn(key="name", header="Name", sortable=True),
        DataTableColumn(key="department", header="Department", sortable=True),
        DataTableColumn(key="role", header="Role"),
        DataTableColumn(key="location", header="Office", sortable=True),
    ],
    rows=employees,
    searchable=True,
    paginated=True,
    page_size=15,
)
```

## Forms

Forms require two tools: one to render, one to handle submission.

### Manual Form

```python
from prefab_ui.components import (
    Column, Heading, Row, Muted, Badge, Input, Select,
    Textarea, Button, Form, ForEach, Separator,
)
from prefab_ui.actions import ShowToast
from prefab_ui.actions.mcp import CallTool

@mcp.tool(app=True)
def contact_form() -> PrefabApp:
    with Column(gap=6, css_class="p-6") as view:
        Heading("Contacts")
        with ForEach("contacts"):
            with Row(gap=2, align="center"):
                Muted("{{ name }}")
                Muted("{{ email }}")
                Badge("{{ category }}")
        Separator()
        with Form(
            on_submit=CallTool(
                "save_contact",
                result_key="contacts",
                on_success=ShowToast("Contact saved!", variant="success"),
                on_error=ShowToast("{{ $error }}", variant="error"),
            )
        ):
            Input(name="name", label="Full Name", required=True)
            Input(name="email", label="Email", input_type="email", required=True)
            Select(
                name="category",
                label="Category",
                options=["Customer", "Vendor", "Partner", "Other"],
            )
            Textarea(name="notes", label="Notes", placeholder="Optional notes...")
            Button("Save Contact")
    return PrefabApp(view=view, state={"contacts": list(contacts_db)})

@mcp.tool
def save_contact(name: str, email: str, category: str = "Other", notes: str = "") -> list[dict]:
    """Save a new contact and return the updated list."""
    contacts_db.append({"name": name, "email": email, "category": category, "notes": notes})
    return list(contacts_db)
```

### Pydantic Model Form

```python
from pydantic import BaseModel, Field
from prefab_ui.components import Column, Heading, Form
from prefab_ui.actions.mcp import CallTool

class BugReport(BaseModel):
    title: str = Field(title="Bug Title")
    severity: Literal["low", "medium", "high", "critical"] = Field(
        title="Severity", default="medium"
    )
    description: str = Field(title="Description")
    steps_to_reproduce: str = Field(title="Steps to Reproduce")

@mcp.tool(app=True)
def report_bug() -> PrefabApp:
    with Column(gap=4, css_class="p-6") as view:
        Heading("Report a Bug")
        Form.from_model(BugReport, on_submit=CallTool("create_bug_report"))
    return PrefabApp(view=view)

@mcp.tool
def create_bug_report(data: dict) -> str:
    """Create a bug report from the form submission."""
    report = BugReport(**data)
    return f"Created bug report: {report.title}"
```

## Status Displays

```python
from prefab_ui.components import (
    Column, Row, Grid, Heading, Text, Muted, Badge,
    Card, CardContent, Progress, Separator,
)

@mcp.tool(app=True)
def system_status() -> PrefabApp:
    services = [
        {"name": "API Gateway", "status": "healthy", "ok": True, "latency_ms": 12, "uptime_pct": 99.9},
        {"name": "Database", "status": "healthy", "ok": True, "latency_ms": 3, "uptime_pct": 99.99},
        {"name": "Cache", "status": "degraded", "ok": False, "latency_ms": 45, "uptime_pct": 98.2},
    ]
    all_ok = all(s["ok"] for s in services)

    with Column(gap=4, css_class="p-6") as view:
        with Row(gap=2, align="center"):
            Heading("System Status")
            Badge(
                "All Healthy" if all_ok else "Degraded",
                variant="success" if all_ok else "destructive",
            )
        Separator()
        with Grid(columns=2, gap=4):
            for svc in services:
                with Card():
                    with CardContent():
                        with Row(gap=2, align="center"):
                            Text(svc["name"], css_class="font-medium")
                            Badge(svc["status"], variant="success" if svc["ok"] else "destructive")
                        Muted(f"Response: {svc['latency_ms']}ms")
                        Progress(value=svc["uptime_pct"])
    return PrefabApp(view=view)
```

## Conditional Content

```python
from prefab_ui.components import Column, Heading, Switch, Separator, Alert, If

@mcp.tool(app=True)
def feature_flags() -> PrefabApp:
    with Column(gap=4, css_class="p-6") as view:
        Heading("Feature Flags")
        Switch(name="dark_mode", label="Dark Mode")
        Switch(name="beta_features", label="Beta Features")
        Separator()
        with If("{{ dark_mode }}"):
            Alert(title="Dark mode enabled", description="UI will use dark theme.")
        with If("{{ beta_features }}"):
            Alert(
                title="Beta features active",
                description="Experimental features are now visible.",
                variant="warning",
            )
    return PrefabApp(view=view, state={"dark_mode": False, "beta_features": False})
```

## Tabs

```python
from prefab_ui.components import (
    Column, Heading, Text, Muted, Badge, Row,
    DataTable, DataTableColumn, Tabs, Tab, ForEach,
)

@mcp.tool(app=True)
def project_overview(project_id: str) -> PrefabApp:
    with Column(gap=4, css_class="p-6") as view:
        Heading(project["name"])
        with Tabs():
            with Tab("Overview"):
                Text(project["description"])
                with Row(gap=4):
                    Badge(project["status"])
                    Muted(f"Created: {project['created_at']}")
            with Tab("Members"):
                DataTable(
                    columns=[
                        DataTableColumn(key="name", header="Name", sortable=True),
                        DataTableColumn(key="role", header="Role"),
                    ],
                    rows=project["members"],
                )
            with Tab("Activity"):
                with ForEach("activity"):
                    with Row(gap=2):
                        Muted("{{ timestamp }}")
                        Text("{{ message }}")
    return PrefabApp(view=view, state={"activity": project["activity"]})
```

## Accordion

```python
from prefab_ui.components import (
    Column, Heading, Row, Text, Badge, Progress,
    Accordion, AccordionItem,
)

@mcp.tool(app=True)
def api_health() -> PrefabApp:
    with Column(gap=4, css_class="p-6") as view:
        Heading("API Health")
        with Accordion(multiple=True):
            for ep in endpoints:
                with AccordionItem(ep["path"]):
                    with Row(gap=4):
                        Badge(f"{ep['status']}", variant="success" if ep["healthy"] else "destructive")
                        Text(f"Avg: {ep['avg_ms']}ms")
                        Text(f"P99: {ep['p99_ms']}ms")
                    Progress(value=ep["uptime_pct"])
    return PrefabApp(view=view)
```

## Custom HTML Apps

For custom rendering (maps, 3D, video), use the MCP Apps extension directly.

### Basic Structure

```python
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig

mcp = FastMCP("My App Server")
VIEW_URI = "ui://my-app/view.html"

@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def generate_data(data: list[float]) -> str:
    """Generate data for the UI"""
    return json.dumps({"values": data})

@mcp.resource(VIEW_URI)
def view() -> str:
    """Interactive UI"""
    return """<!DOCTYPE html>
<html>
<head><style>body { font-family: sans-serif; padding: 20px; }</style></head>
<body>
  <div id="output"></div>
  <script type="module">
    import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";
    const app = new App({ name: "My App", version: "1.0.0" });
    app.ontoolresult = ({ content }) => {
      const text = content?.find(c => c.type === 'text');
      if (text) document.getElementById('output').textContent = text.text;
    };
    await app.connect();
  </script>
</body>
</html>"""
```

### AppConfig Fields

| Field | Type | Description |
|-------|------|-------------|
| `resource_uri` | str | URI of UI resource (tools only) |
| `visibility` | list[str] | Where tool appears: `"model"`, `"app"`, or both |
| `csp` | ResourceCSP | Content Security Policy |
| `permissions` | ResourcePermissions | Iframe sandbox permissions |
| `domain` | str | Stable sandbox origin |
| `prefers_border` | bool | Whether UI prefers visible border |

### CSP Configuration

```python
from fastmcp.server.apps import AppConfig, ResourceCSP

@mcp.resource(
    "ui://my-app/view.html",
    app=AppConfig(
        csp=ResourceCSP(
            connect_domains=["https://api.example.com"],      # fetch, XHR, WebSocket
            resource_domains=["https://unpkg.com"],           # Scripts, images, styles
            frame_domains=["https://embed.example.com"],      # Nested iframes
            base_uri_domains=["https://example.com"],         # Document base URI
        )
    ),
)
def view() -> str:
    return "<html>...</html>"
```

### Checking Client Support

```python
from fastmcp import Context
from fastmcp.server.apps import UI_EXTENSION_ID

@mcp.tool(app=AppConfig(resource_uri="ui://my-app/view.html"))
async def my_tool(ctx: Context) -> str:
    if ctx.client_supports_extension(UI_EXTENSION_ID):
        return rich_response()
    else:
        return plain_text_response()
```

## Complete Example: QR Code Server

```python
import base64
import io
import qrcode
from fastmcp import FastMCP
from fastmcp.server.apps import AppConfig, ResourceCSP
from mcp import types
from fastmcp.tools import ToolResult

mcp = FastMCP("QR Code Server")
VIEW_URI = "ui://qr-server/view.html"

@mcp.tool(app=AppConfig(resource_uri=VIEW_URI))
def generate_qr(text: str = "https://gofastmcp.com") -> ToolResult:
    """Generate a QR code from text."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image()
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return ToolResult(
        content=[types.ImageContent(type="image", data=b64, mimeType="image/png")]
    )

@mcp.resource(
    VIEW_URI,
    app=AppConfig(csp=ResourceCSP(resource_domains=["https://unpkg.com"])),
)
def view() -> str:
    return """<!DOCTYPE html>
<html>
<head>
  <style>
    body { display: flex; justify-content: center; align-items: center;
           height: 340px; width: 340px; margin: 0; background: transparent; }
    img { width: 300px; height: 300px; border-radius: 8px; }
  </style>
</head>
<body>
  <div id="qr"></div>
  <script type="module">
    import { App } from "https://unpkg.com/@modelcontextprotocol/ext-apps@0.4.0/app-with-deps";
    const app = new App({ name: "QR View", version: "1.0.0" });
    app.ontoolresult = ({ content }) => {
      const img = content?.find(c => c.type === 'image');
      if (img) {
        const el = document.createElement('img');
        el.src = `data:${img.mimeType};base64,${img.data}`;
        el.alt = "QR Code";
        document.getElementById('qr').replaceChildren(el);
      }
    };
    await app.connect();
  </script>
</body>
</html>"""
```
