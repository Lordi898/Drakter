---
name: radix-ui
description: Comprehensive documentation for Radix UI - a complete design system including Themes (pre-styled components), Primitives (unstyled accessible components), and Colors (color system). Use when building React applications with Radix UI components, implementing accessible UI patterns, theming applications, or working with Radix's color system. Covers installation, components, styling, theming, accessibility, animations, and best practices.
---

# Radix UI

Complete reference documentation for the Radix UI design system, including Themes, Primitives, and Colors.

## What is Radix UI?

Radix UI is a comprehensive design system consisting of three main products:

- **Radix Themes**: Pre-styled, production-ready React components with built-in theming
- **Radix Primitives**: Unstyled, accessible UI component primitives for custom designs
- **Radix Colors**: A comprehensive color system designed for UI design

## Documentation Structure

All documentation is organized into three main sections in the `references/` directory:

### 1. Radix Themes (`references/themes/`)

Pre-styled component library designed to work out of the box with minimal configuration.

**When to use Themes**: Building applications that need production-ready styled components with theming support.

- **`overview/`** - Installation, getting started, styling approaches, layout system
- **`theme/`** - Theming system (colors, typography, spacing, breakpoints, radius, shadows, dark mode)
- **`components/`** - All 56 Themes components (Button, Dialog, Select, etc.)

**Start here for Themes**: `references/themes/overview/overview_getting-started.md`

### 2. Radix Primitives (`references/primitives/`)

Unstyled, accessible component primitives for building custom design systems.

**When to use Primitives**: Building custom-styled components while maintaining accessibility and behavior standards.

- **`overview/`** - Introduction, getting started, accessibility principles
- **`components/`** - All 30 primitive components (Accordion, Dialog, Dropdown Menu, etc.)
- **`guides/`** - Styling, animation, composition, server-side rendering
- **`utilities/`** - Helper utilities (Portal, Slot, Visually Hidden, etc.)

**Start here for Primitives**: `references/primitives/overview/overview_introduction.md`

### 3. Radix Colors (`references/colors/`)

Color system with extensive palettes designed for UI design and accessibility.

**When to use Colors**: Implementing color systems, theming, ensuring accessible color contrast.

- **`overview/`** - Installation, usage, aliasing, custom palettes
- **`palette-composition/`** - Understanding scales, composing palettes

**Start here for Colors**: `references/colors/overview/overview_installation.md`

## How to Use This Skill

### Quick Component Lookup

When working with a specific component:

1. **For styled components**: Check `references/themes/components/components_<component-name>.md`
2. **For unstyled primitives**: Check `references/primitives/components/components_<component-name>.md`

### Implementation Workflows

**Starting a new project with Radix Themes**:
1. Read `references/themes/overview/overview_getting-started.md` for installation
2. Read `references/themes/theme/theme_overview.md` for theming basics
3. Browse component docs as needed in `references/themes/components/`

**Building custom components with Primitives**:
1. Read `references/primitives/overview/overview_getting-started.md` for installation
2. Read `references/primitives/guides/guides_styling.md` for styling approaches
3. Find your component in `references/primitives/components/`
4. Check `references/primitives/guides/guides_animation.md` for animation patterns

**Setting up colors and theming**:
1. Read `references/colors/overview/overview_installation.md` for Colors setup
2. Read `references/themes/theme/theme_color.md` for Themes color system
3. Read `references/themes/theme/theme_dark-mode.md` for dark mode implementation

### Common Questions

- **Component API reference**: Component docs include props, examples, accessibility features
- **Theming and customization**: See `references/themes/theme/` directory
- **Accessibility**: See `references/primitives/overview/overview_accessibility.md`
- **Styling approaches**: See `references/primitives/guides/guides_styling.md` and `references/themes/overview/overview_styling.md`
- **Animation**: See `references/primitives/guides/guides_animation.md`
- **SSR/Next.js**: See `references/primitives/guides/guides_server-side-rendering.md`

## Scripts

This skill includes utility scripts for maintaining and updating documentation:

- `discover_docs.py` - Discover all documentation URLs from Radix UI websites
- `scrape_all_docs.py` - Scrape all documentation for a section (themes/primitives/colors)
- `scrape_url.py` - Scrape a single URL to markdown

These scripts are primarily for skill maintenance and updates.
