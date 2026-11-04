Collapsible â€“ Radix Primitives

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[ThemesThemes](/)[PrimitivesPrimitives](/primitives)[IconsIcons](/icons)[ColorsColors](/colors)

[Documentation](/primitives/docs)[Case studies](/primitives/case-studies)[Blog](/blog)

Search

`/`

#### Overview

[Introduction](/primitives/docs/overview/introduction)[Getting started](/primitives/docs/overview/getting-started)[Accessibility](/primitives/docs/overview/accessibility)[Releases](/primitives/docs/overview/releases)

#### Guides

[Styling](/primitives/docs/guides/styling)[Animation](/primitives/docs/guides/animation)[Composition](/primitives/docs/guides/composition)[Server-side rendering](/primitives/docs/guides/server-side-rendering)

#### Components

[Accordion](/primitives/docs/components/accordion)[Alert Dialog](/primitives/docs/components/alert-dialog)[Aspect Ratio](/primitives/docs/components/aspect-ratio)[Avatar](/primitives/docs/components/avatar)[Checkbox](/primitives/docs/components/checkbox)[Collapsible](/primitives/docs/components/collapsible)[Context Menu](/primitives/docs/components/context-menu)[Dialog](/primitives/docs/components/dialog)[Dropdown Menu](/primitives/docs/components/dropdown-menu)[Form

Preview](/primitives/docs/components/form)[Hover Card](/primitives/docs/components/hover-card)[Label](/primitives/docs/components/label)[Menubar](/primitives/docs/components/menubar)[Navigation Menu](/primitives/docs/components/navigation-menu)[One-Time Password Field

Preview](/primitives/docs/components/one-time-password-field)[Password Toggle Field

Preview](/primitives/docs/components/password-toggle-field)[Popover](/primitives/docs/components/popover)[Progress](/primitives/docs/components/progress)[Radio Group](/primitives/docs/components/radio-group)[Scroll Area](/primitives/docs/components/scroll-area)[Select](/primitives/docs/components/select)[Separator](/primitives/docs/components/separator)[Slider](/primitives/docs/components/slider)[Switch](/primitives/docs/components/switch)[Tabs](/primitives/docs/components/tabs)[Toast](/primitives/docs/components/toast)[Toggle](/primitives/docs/components/toggle)[Toggle Group](/primitives/docs/components/toggle-group)[Toolbar](/primitives/docs/components/toolbar)[Tooltip](/primitives/docs/components/tooltip)

#### Utilities

[Accessible Icon](/primitives/docs/utilities/accessible-icon)[Direction Provider](/primitives/docs/utilities/direction-provider)[Portal](/primitives/docs/utilities/portal)[Slot](/primitives/docs/utilities/slot)[Visually Hidden](/primitives/docs/utilities/visually-hidden)

Components

# Collapsible

An interactive component which expands/collapses a panel.

@peduarte starred 3 repositories

@radix-ui/primitives

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { Collapsible } from "radix-ui";



import { RowSpacingIcon, Cross2Icon } from "@radix-ui/react-icons";



import "./styles.css";



const CollapsibleDemo = () => {



const [open, setOpen] = React.useState(false);



return (



<Collapsible.Root
			className="CollapsibleRoot"
			open={open}
			onOpenChange={setOpen}
		>



<div
				style={{
					display: "flex",
					alignItems: "center",
					justifyContent: "space-between",
				}}
			>



<span className="Text" style={{ color: "white" }}>



@peduarte starred 3 repositories



</span>



<Collapsible.Trigger asChild>



<button className="IconButton">



{open ? <Cross2Icon /> : <RowSpacingIcon />}



</button>



</Collapsible.Trigger>



</div>



<div className="Repository">



<span className="Text">@radix-ui/primitives</span>



</div>



<Collapsible.Content>



<div className="Repository">



<span className="Text">@radix-ui/colors</span>



</div>



<div className="Repository">



<span className="Text">@radix-ui/themes</span>



</div>



</Collapsible.Content>



</Collapsible.Root>



);



};



export default CollapsibleDemo;



Expand code
```

## Features

Full keyboard navigation.

Can be controlled or uncontrolled.

## Component Reference Links

Version: 1.1.12

Size: [4.82 kB](https://bundlephobia.com/package/@radix-ui/react-collapsible@1.1.12)

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/collapsible/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

[ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure)

## [Installation](#installation)

Install the component from your command line.

```
npm install @radix-ui/react-collapsible
```

## [Anatomy](#anatomy)

Import the components and piece the parts together.

```
import { Collapsible } from "radix-ui";



export default () => (



<Collapsible.Root>



<Collapsible.Trigger />



<Collapsible.Content />



</Collapsible.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of a collapsible.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `defaultOpen` Prop description | `boolean` | No default value |
| `open` Prop description | `boolean` | No default value |
| `onOpenChange` Prop description | `function` See full type | No default value |
| `disabled` Prop description | `boolean` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |

### [Trigger](#trigger)

The button that toggles the collapsible.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |

### [Content](#content)

The component that contains the collapsible content.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `forceMount` Prop description | `boolean` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |

| CSS Variable | Description |
| --- | --- |
| `--radix-collapsible-content-width` | The width of the content when it opens/closes |
| `--radix-collapsible-content-height` | The height of the content when it opens/closes |

## [Examples](#examples)

### [Animating content size](#animating-content-size)

Use the `--radix-collapsible-content-width` and/or `--radix-collapsible-content-height` CSS variables to animate the size of the content when it opens/closes. Here's a demo:

```
// index.jsx



import { Collapsible } from "radix-ui";



import "./styles.css";



export default () => (



<Collapsible.Root>



<Collapsible.Trigger>â€¦</Collapsible.Trigger>



<Collapsible.Content className="CollapsibleContent">



â€¦



</Collapsible.Content>



</Collapsible.Root>



);
```

```
/* styles.css */



.CollapsibleContent {



overflow: hidden;



}



.CollapsibleContent[data-state="open"] {



animation: slideDown 300ms ease-out;



}



.CollapsibleContent[data-state="closed"] {



animation: slideUp 300ms ease-out;



}



@keyframes slideDown {



from {



height: 0;



}



to {



height: var(--radix-collapsible-content-height);



}



}



@keyframes slideUp {



from {



height: var(--radix-collapsible-content-height);



}



to {



height: 0;



}



}
```

## [Accessibility](#accessibility)

Adheres to the [Disclosure WAI-ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/disclosure).

### [Keyboard Interactions](#keyboard-interactions)

| Key | Description |
| --- | --- |
| `Space` | Opens/closes the collapsible. |
| `Enter` | Opens/closes the collapsible. |

#### Quick nav

Previous[Checkbox](/primitives/docs/components/checkbox)

Next[Context Menu](/primitives/docs/components/context-menu)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/collapsible.mdx "Edit this page on GitHub.")
