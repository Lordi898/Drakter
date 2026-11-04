# Project Structure

Best practices for organizing Python projects. See SKILL.md for quick reference.

## The src Layout (Recommended)

### Why src Layout?

1. **Avoids import issues** - Tests run against installed package
2. **Better isolation** - No accidental imports from project root
3. **Works with editable installs** - `pip install -e .`
4. **Industry standard** - Recommended by PyPA

### Standard Structure

```
my-project/
├── src/
│   └── mypackage/
│       ├── __init__.py           # Package initialization
│       ├── core/
│       │   ├── __init__.py
│       │   ├── service.py
│       │   └── repository.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── routes.py
│       │   └── schemas.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── user.py
│       └── utils/
│           ├── __init__.py
│           └── helpers.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   └── test_service.py
│   └── integration/
│       └── test_api.py
├── docs/
│   └── index.md
├── pyproject.toml
├── README.md
├── LICENSE
└── .gitignore
```

## Flat Layout (Simple Projects Only)

```
simple-project/
├── mypackage.py      # Single module
├── test_mypackage.py
├── pyproject.toml
└── README.md
```

## pyproject.toml Example

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mypackage"
version = "1.0.0"
description = "A Python package"
readme = "README.md"
requires-python = ">=3.10"
license = "MIT"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
dependencies = [
    "httpx>=0.25.0",
    "pydantic>=2.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "mypy>=1.0.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/mypackage"]
```

## Package Organization Patterns

### By Feature (Recommended)

```
src/shop/
├── products/           # Product feature
│   ├── __init__.py
│   ├── service.py
│   ├── repository.py
│   └── models.py
├── orders/             # Order feature
│   ├── __init__.py
│   ├── service.py
│   ├── repository.py
│   └── models.py
├── users/              # User feature
│   ├── __init__.py
│   ├── service.py
│   └── models.py
└── shared/             # Shared utilities
    ├── __init__.py
    ├── db.py
    └── config.py
```

### By Layer (Alternative)

```
src/shop/
├── models/             # All data models
│   ├── product.py
│   ├── order.py
│   └── user.py
├── services/           # All business logic
│   ├── product_service.py
│   ├── order_service.py
│   └── user_service.py
├── repositories/       # All data access
│   └── ...
└── api/               # All routes/handlers
    └── ...
```

## __init__.py Patterns

### Minimal Init

```python
# src/mypackage/__init__.py
"""My Package - A brief description."""

__version__ = "1.0.0"
```

### Expose Public API

```python
# src/mypackage/__init__.py
"""My Package - A brief description."""

from mypackage.core.service import UserService
from mypackage.models.user import User

__version__ = "1.0.0"
__all__ = ["UserService", "User"]
```

### Lazy Imports

```python
# src/mypackage/__init__.py
def __getattr__(name: str):
    if name == "UserService":
        from mypackage.core.service import UserService
        return UserService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
```

## Test Organization

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── fixtures/                # Test data files
│   └── sample_data.json
├── unit/                    # Fast, isolated tests
│   ├── test_service.py
│   └── test_utils.py
├── integration/             # Slower, real dependencies
│   ├── test_api.py
│   └── test_database.py
└── e2e/                     # End-to-end tests
    └── test_user_flow.py
```

## Anti-Patterns to Avoid

### Deep Nesting

```
# BAD: Too deep
src/app/modules/users/management/permissions/handlers/
    └── user_permission_handler.py

# GOOD: Flatter structure
src/app/users/permissions.py
```

### Generic Names

```
# BAD: Unhelpful names
src/utils/           # What utilities?
src/helpers.py       # Helpers for what?
src/common/          # Common what?
src/misc.py          # Junk drawer

# GOOD: Specific names
src/shared/validation.py
src/shared/database.py
src/infrastructure/logging.py
```

### Circular Dependencies

```
# BAD: Circular import
# models/user.py
from models.order import Order

# models/order.py
from models.user import User

# GOOD: Use TYPE_CHECKING or restructure
# models/user.py
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.order import Order
```

## Quick Reference

| Project Size | Recommended Structure |
|-------------|----------------------|
| Single file | Flat layout |
| Small package | src/package/ with flat modules |
| Medium project | src/package/ with feature folders |
| Large project | src/package/ with nested packages |

### Key Rules

1. Always use `src/` layout for packages
2. Organize by feature, not by file type
3. Keep `__init__.py` minimal
4. Tests mirror source structure
5. Avoid deep nesting (max 3-4 levels)
6. Use specific, meaningful names
