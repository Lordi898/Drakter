---
name: shadcn
description: Comprehensive guide for working with shadcn/ui components, theming, CLI, and registries. Use when building UIs with shadcn/ui, installing components, customizing themes, working with component registries, integrating with React Hook Form or TanStack Form, or needing documentation about any shadcn/ui component (Accordion, Alert, Avatar, Badge, Button, Card, Chart, Dialog, Form, Input, Select, Table, Sidebar, etc.). Also use when exploring third-party shadcn registries or setting up custom registries.
---

# shadcn/ui Skill

Comprehensive documentation and utilities for working with shadcn/ui - a collection of re-usable components built with Radix UI and Tailwind CSS.

## Overview

This skill provides:
- Complete documentation for all 60+ shadcn/ui components
- Setup and configuration guides (installation, theming, CLI, dark mode)
- Registry system documentation for custom component libraries
- Form integration guides (React Hook Form, TanStack Form)
- Utility scripts for fetching latest documentation and exploring registries
- Information about 94+ third-party component registries

## When to Use This Skill

Trigger this skill when:
- Installing or configuring shadcn/ui components
- Looking up component APIs, props, or usage examples
- Customizing themes, colors, or implementing dark mode
- Setting up the CLI or working with components.json
- Integrating forms with React Hook Form or TanStack Form
- Creating or publishing custom component registries
- Finding third-party registries for specialized components
- Debugging component issues or understanding best practices

## Documentation Structure

All documentation is organized in the `references/` folder by category. Load only the relevant files for the task at hand.

### Setup & Configuration (references/setup/)

**When to use**: Setting up shadcn/ui, configuring themes, or working with the CLI.

Key files:
- `installation.md` - Installation guide for Next.js, Vite, Remix, etc.
- `cli.md` - CLI commands and usage (add, init, diff)
- `theming.md` - Customizing themes, colors, and design tokens
- `dark-mode.md` - Implementing dark mode with next-themes
- `components-json.md` - Understanding and configuring components.json
- `monorepo.md` - Setup for monorepo/workspace projects
- `javascript.md` - Using shadcn/ui with JavaScript (non-TypeScript)
- `blocks.md` - Pre-built component blocks
- `figma.md` - Figma design system integration
- `mcp.md` - MCP Server integration

### Components (references/components/)

**When to use**: Implementing specific UI components or looking up component APIs.

Contains 60 component documentation files including:
- **Form Components**: Input, Select, Checkbox, Radio Group, Switch, Textarea, Combobox, Date Picker
- **Layout**: Card, Separator, Tabs, Accordion, Collapsible, Resizable
- **Navigation**: Breadcrumb, Navigation Menu, Menubar, Pagination, Sidebar
- **Overlays**: Dialog, Sheet, Drawer, Popover, Hover Card, Tooltip
- **Feedback**: Alert, Toast, Sonner, Progress, Spinner, Skeleton
- **Data Display**: Table, Data Table, Chart, Avatar, Badge, Typography
- **Interactive**: Button, Button Group, Dropdown Menu, Context Menu, Command

Each file contains:
- Component description and use cases
- Installation instructions
- Complete code examples
- Props/API documentation
- Accessibility notes

**Usage pattern**: Load specific component files as needed:
```
For button questions → references/components/components_button.md
For form questions → references/components/components_form.md
For table questions → references/components/components_table.md
```

### Forms (references/forms/)

**When to use**: Integrating shadcn/ui with form libraries.

Files:
- `_docs_forms.md` - General forms documentation and patterns
- `forms_react-hook-form.md` - React Hook Form integration guide
- `forms_tanstack-form.md` - TanStack Form integration guide

### Registry System (references/registry/)

**When to use**: Working with component registries, creating custom registries, or publishing components.

Files:
- `registry.md` - Introduction to the registry system
- `registry_getting-started.md` - Building your own registry
- `registry_namespace.md` - Configuring namespaces (@your-org)
- `registry_authentication.md` - Securing registries with auth
- `registry_examples.md` - Example configurations
- `registry_registry-json.md` - registry.json schema specification
- `registry_registry-item-json.md` - registry-item.json schema
- `registry_registry-index.md` - Adding registries to the directory
- `registry_open-in-v0.md` - v0 integration for registries
- `registry_mcp.md` - MCP Server for registries

## Scripts

All scripts are in `scripts/` and require Python 3.8+ with dependencies: `cloudscraper`, `html2text`, `beautifulsoup4`.

### common_scraper.py

Reusable web scraping utility with Cloudflare bypass and HTML-to-Markdown conversion.

**When to use**: Need to fetch custom documentation URLs or update references.

Functions:
- `fetch_url(url)` - Fetch HTML content
- `html_to_markdown(html)` - Convert HTML to clean Markdown
- `fetch_and_convert(url)` - Fetch and convert in one call
- `save_markdown(content, filepath)` - Save Markdown to file
- `fetch_and_save(url, filepath)` - Fetch, convert, and save

Example:
```bash
python scripts/common_scraper.py https://ui.shadcn.com/docs/components/button output.md
```

### scrape_shadcn_directory.py

Extracts all registries from the shadcn/ui directory with names, descriptions, and links.

**When to use**: Need current list of available third-party registries.

Output: JSON array with 94+ registries including @clerk, @magicui, @aceternity, @supabase, etc.

Example:
```bash
python scripts/scrape_shadcn_directory.py > registries.json
```

### fetch_shadcn_docs.py

Automated documentation fetcher that downloads all shadcn/ui docs as Markdown.

**When to use**: Updating the skill with latest documentation.

Features:
- Fetches all 87+ documentation pages
- Organizes by category (setup, components, forms, registry)
- Includes metadata.json with page index
- Configurable delay between requests

Example:
```bash
python scripts/fetch_shadcn_docs.py --output-dir updated_docs --delay 0.5
```

## Common Workflows

### Installing a Component

1. Reference `references/setup/cli.md` for CLI usage
2. Reference `references/components/components_<name>.md` for specific component
3. Check `references/setup/components-json.md` if configuration needed

### Setting Up Dark Mode

1. Reference `references/setup/dark-mode.md` for implementation
2. Reference `references/setup/theming.md` for theme customization
3. Check component-specific dark mode notes if needed

### Creating Custom Forms

1. Reference `references/forms/forms_react-hook-form.md` or `forms_tanstack-form.md`
2. Reference form component docs: `components_form.md`, `components_input.md`, etc.
3. Check `references/components/components_field.md` for field composition

### Building a Custom Registry

1. Reference `references/registry/registry_getting-started.md`
2. Reference `references/registry/registry_registry-json.md` for schema
3. Reference `references/registry/registry_namespace.md` for branding
4. Reference `references/registry/registry_authentication.md` if needed

### Finding Third-Party Components

1. Run `scripts/scrape_shadcn_directory.py` for current registry list
2. Use output to find specialized registries (AI components, animations, forms, etc.)
3. Reference `references/registry/registry.md` for integration guide

## Tips for Effective Use

1. **Load only what you need**: Don't load all 60 component files - be selective
2. **Check setup first**: Most issues come from incorrect configuration
3. **Use metadata.json**: Contains index of all pages with titles and URLs
4. **Update periodically**: Run fetch_shadcn_docs.py to get latest docs
5. **Explore registries**: Many common needs are solved by third-party registries

## Third-Party Registries

The skill includes access to 94+ third-party registries via `scripts/scrape_shadcn_directory.py`. Notable categories:

- **AI/Chat**: @assistant-ui, @gaia, @prompt-kit, @ai-elements, @manifest
- **Animations**: @magicui, @motion-primitives, @aceternity, @cult-ui, @smoothui
- **Forms**: @formcn, @better-upload, @billingsdk
- **Data**: @lytenyte (grids), chart components
- **Design Systems**: @basecn, @coss, @react-aria, @taki
- **Specialized**: @clerk (auth), @supabase (backend), @plate (editor), @algolia (search)

## Keeping Documentation Current

The shadcn/ui project updates frequently. To refresh documentation:

```bash
cd scripts/
python fetch_shadcn_docs.py --output-dir ../references_new
# Review changes, then replace old references
```

## Related Resources

- Official site: https://ui.shadcn.com
- GitHub: https://github.com/shadcn-ui/ui
- Registry directory: https://ui.shadcn.com/docs/directory
- Component explorer: https://ui.shadcn.com/docs/components
