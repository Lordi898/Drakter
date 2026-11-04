---
name: fastapi
description: "FastAPI web framework for building APIs with Python. Use when working with FastAPI applications including: (1) Creating REST APIs and web services, (2) Implementing path operations and routing, (3) Working with request/response handling, parameters, and bodies, (4) Setting up authentication and security (OAuth2, JWT, API keys), (5) Implementing dependencies and dependency injection, (6) Testing FastAPI applications, (7) Deploying FastAPI apps, (8) Working with WebSockets, middleware, or background tasks. Based on FastAPI 0.129+ with Python 3.10+, Pydantic v2, and Starlette 0.40+."
---

# FastAPI

Modern, high-performance Python web framework for building APIs with automatic OpenAPI documentation.

## Quick Start

### Installation

```bash
pip install "fastapi[standard]"
```

### Basic Application

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    is_offer: bool | None = None

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_name": item.name, "item_id": item_id}
```

### Run Development Server

```bash
fastapi dev main.py
```

### Run Production Server

```bash
fastapi run main.py
```

## Core Concepts

### Path Operations

Decorators define HTTP methods and paths:
- `@app.get("/")` - GET request
- `@app.post("/")` - POST request
- `@app.put("/")` - PUT request
- `@app.delete("/")` - DELETE request
- `@app.patch("/")` - PATCH request

### Parameter Types

| Type | Declaration | Source |
|------|-------------|--------|
| Path | `item_id: int` in route | URL path |
| Query | `q: str \| None = None` | URL query string |
| Body | `item: Item` (Pydantic model) | Request body |
| Header | `user_agent: str = Header()` | HTTP headers |
| Cookie | `session_id: str = Cookie()` | HTTP cookies |
| Form | `username: str = Form()` | Form data |
| File | `file: UploadFile = File()` | File uploads |

### Dependency Injection

```python
from fastapi import Depends

def common_params(q: str | None = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
def read_items(commons: dict = Depends(common_params)):
    return commons
```

### Response Models

```python
from typing import List

@app.get("/items/", response_model=List[Item])
def read_items():
    return items

@app.post("/items/", response_model=Item, status_code=201)
def create_item(item: Item):
    return item
```

## Documentation Index

### Tutorial - User Guide

Foundational concepts, read in order for best understanding.

- **Getting Started**: `references/tutorial/index.md`
- **First Steps**: `references/tutorial/first-steps.md`
- **Path Parameters**: `references/tutorial/path-params.md`, `references/tutorial/path-params-numeric-validations.md`
- **Query Parameters**: `references/tutorial/query-params.md`, `references/tutorial/query-params-str-validations.md`, `references/tutorial/query-param-models.md`
- **Request Body**: `references/tutorial/body.md`, `references/tutorial/body-fields.md`, `references/tutorial/body-multiple-params.md`, `references/tutorial/body-nested-models.md`, `references/tutorial/body-updates.md`
- **Headers & Cookies**: `references/tutorial/header-params.md`, `references/tutorial/header-param-models.md`, `references/tutorial/cookie-params.md`, `references/tutorial/cookie-param-models.md`
- **Forms & Files**: `references/tutorial/request-forms.md`, `references/tutorial/request-form-models.md`, `references/tutorial/request-files.md`, `references/tutorial/request-forms-and-files.md`
- **Response Handling**: `references/tutorial/response-model.md`, `references/tutorial/response-status-code.md`, `references/tutorial/schema-extra-example.md`
- **Dependencies**: `references/tutorial/dependencies/index.md`
  - Classes as dependencies: `references/tutorial/dependencies/classes-as-dependencies.md`
  - Sub-dependencies: `references/tutorial/dependencies/sub-dependencies.md`
  - Dependencies with yield: `references/tutorial/dependencies/dependencies-with-yield.md`
  - Global dependencies: `references/tutorial/dependencies/global-dependencies.md`
  - In decorators: `references/tutorial/dependencies/dependencies-in-path-operation-decorators.md`
- **Security**: `references/tutorial/security/index.md`
  - OAuth2 with JWT: `references/tutorial/security/oauth2-jwt.md`
  - OAuth2 passwords: `references/tutorial/security/oauth2-password-flow.md`
  - API keys: `references/tutorial/security/api-keys.md`
- **Application Structure**: `references/tutorial/bigger-applications.md`
- **Background Tasks**: `references/tutorial/background-tasks.md`
- **Middleware**: `references/tutorial/middleware.md`
- **CORS**: `references/tutorial/cors.md`
- **SQL Databases**: `references/tutorial/sql-databases.md`
- **Testing**: `references/tutorial/testing.md`
- **Error Handling**: `references/tutorial/handling-errors.md`
- **Metadata**: `references/tutorial/metadata.md`
- **Static Files**: `references/tutorial/static-files.md`

### Advanced User Guide

Additional features for complex use cases.

- **Overview**: `references/advanced/index.md`
- **Custom Responses**: `references/advanced/custom-response.md`, `references/advanced/additional-responses.md`, `references/advanced/response-directly.md`, `references/advanced/response-cookies.md`, `references/advanced/response-headers.md`, `references/advanced/response-change-status-code.md`
- **Advanced Dependencies**: `references/advanced/advanced-dependencies.md`
- **Security**: `references/advanced/security/index.md`
  - OAuth2 scopes: `references/advanced/security/oauth2-scopes.md`
  - HTTP Basic Auth: `references/advanced/security/http-basic-auth.md`
- **WebSockets**: `references/advanced/websockets.md`
- **Middleware**: `references/advanced/middleware.md`
- **Events (Startup/Shutdown)**: `references/advanced/events.md`
- **Templates (Jinja2)**: `references/advanced/templates.md`
- **Sub-applications**: `references/advanced/sub-applications.md`
- **Behind a Proxy**: `references/advanced/behind-a-proxy.md`
- **Settings**: `references/advanced/settings.md`
- **Testing**: `references/advanced/async-tests.md`, `references/advanced/testing-dependencies.md`, `references/advanced/testing-events.md`, `references/advanced/testing-websockets.md`
- **OpenAPI**: `references/advanced/openapi-callbacks.md`, `references/advanced/openapi-webhooks.md`
- **Generate Clients**: `references/advanced/generate-clients.md`
- **Advanced Config**: `references/advanced/path-operation-advanced-configuration.md`, `references/advanced/additional-status-codes.md`
- **Dataclasses**: `references/advanced/dataclasses.md`
- **Request Object**: `references/advanced/using-request-directly.md`
- **WSGI**: `references/advanced/wsgi.md`

### API Reference

Classes, functions, and parameters for detailed implementation.

- **Overview**: `references/reference/index.md`
- **FastAPI Class**: `references/reference/fastapi.md`
- **APIRouter**: `references/reference/apirouter.md`
- **Parameters**: `references/reference/parameters.md`
- **Request**: `references/reference/request.md`
- **Response**: `references/reference/response.md`, `references/reference/responses.md`
- **Dependencies**: `references/reference/dependencies.md`
- **Exceptions**: `references/reference/exceptions.md`
- **Background Tasks**: `references/reference/background.md`
- **Middleware**: `references/reference/middleware.md`
- **WebSockets**: `references/reference/websockets.md`
- **TestClient**: `references/reference/testclient.md`
- **Security**: `references/reference/security/index.md`
- **OpenAPI**: `references/reference/openapi/index.md`, `references/reference/openapi/docs.md`, `references/reference/openapi/models.md`
- **Static Files**: `references/reference/staticfiles.md`
- **Templating**: `references/reference/templating.md`
- **Encoders**: `references/reference/encoders.md`
- **Status Codes**: `references/reference/status.md`
- **UploadFile**: `references/reference/uploadfile.md`
- **HTTPConnection**: `references/reference/httpconnection.md`

### How-To Guides

Task-specific solutions.

- **Overview**: `references/how-to/index.md`
- **GraphQL**: `references/how-to/graphql.md`
- **Database Testing**: `references/how-to/testing-database.md`
- **Extending OpenAPI**: `references/how-to/extending-openapi.md`
- **Separate Schemas**: `references/how-to/separate-openapi-schemas.md`
- **Conditional OpenAPI**: `references/how-to/conditional-openapi.md`
- **Configure Swagger UI**: `references/how-to/configure-swagger-ui.md`
- **Custom Docs UI**: `references/how-to/custom-docs-ui-assets.md`
- **Custom Request/Route**: `references/how-to/custom-request-and-route.md`
- **Auth Error Status**: `references/how-to/authentication-error-status-code.md`
- **General Patterns**: `references/how-to/general.md`
- **Pydantic v1→v2 Migration**: `references/how-to/migrate-from-pydantic-v1-to-pydantic-v2.md`

### Deployment

Production deployment guides.

- **Overview**: `references/deployment/index.md`
- **Concepts**: `references/deployment/concepts.md`
- **Docker**: `references/deployment/docker.md`
- **HTTPS**: `references/deployment/https.md`
- **Server Workers**: `references/deployment/server-workers.md`
- **Cloud Deployment**: `references/deployment/cloud.md`
- **Manual Deployment**: `references/deployment/manually.md`
- **Version Management**: `references/deployment/versions.md`

### Additional Topics

- **Async/Await**: `references/async.md`
- **Python Types**: `references/python-types.md`
- **Virtual Environments**: `references/virtual-environments.md`
- **Environment Variables**: `references/environment-variables.md`
- **FastAPI CLI**: `references/fastapi-cli.md`
- **Project Generation**: `references/project-generation.md`
- **Features Overview**: `references/features.md`
- **History & Design**: `references/history-design-future.md`
- **Alternatives Comparison**: `references/alternatives.md`
- **Benchmarks**: `references/benchmarks.md`

## Common Patterns

### Full CRUD Example

```python
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from typing import List

app = FastAPI()

class ItemCreate(BaseModel):
    name: str
    price: float

class Item(ItemCreate):
    id: int

items_db: dict[int, Item] = {}
item_id_counter = 0

@app.post("/items/", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate):
    global item_id_counter
    item_id_counter += 1
    new_item = Item(id=item_id_counter, **item.model_dump())
    items_db[item_id_counter] = new_item
    return new_item

@app.get("/items/", response_model=List[Item])
def list_items(skip: int = 0, limit: int = 100):
    return list(items_db.values())[skip:skip+limit]

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: ItemCreate):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = Item(id=item_id, **item.model_dump())
    items_db[item_id] = updated
    return updated

@app.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
```

### Dependency with Database Session

```python
from fastapi import Depends
from sqlalchemy.orm import Session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/")
def read_users(db: Session = Depends(get_db)):
    return db.query(User).all()
```

### OAuth2 Password Flow

```python
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # Validate user and return token
    return {"access_token": token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(token: str = Depends(oauth2_scheme)):
    # Validate token and return user
    return user
```

## Requirements (v0.129+)

- Python 3.10+ (Python 3.9 support dropped)
- Pydantic v2 only
- Starlette 0.40.0+
