Accordion â€“ Radix Primitives

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

# Accordion

A vertically stacked set of interactive headings that each reveal an
associated section of content.

### Is it accessible?

Yes. It adheres to the WAI-ARIA design pattern.

### Is it unstyled?

### Can it be animated?

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { Accordion } from "radix-ui";



import classNames from "classnames";



import { ChevronDownIcon } from "@radix-ui/react-icons";



import "./styles.css";



const AccordionDemo = () => (



<Accordion.Root
		className="AccordionRoot"
		type="single"
		defaultValue="item-1"
		collapsible
	>



<Accordion.Item className="AccordionItem" value="item-1">



<AccordionTrigger>Is it accessible?</AccordionTrigger>



<AccordionContent>



Yes. It adheres to the WAI-ARIA design pattern.



</AccordionContent>



</Accordion.Item>



<Accordion.Item className="AccordionItem" value="item-2">



<AccordionTrigger>Is it unstyled?</AccordionTrigger>



<AccordionContent>



Yes. It's unstyled by default, giving you freedom over the look and



feel.



</AccordionContent>



</Accordion.Item>



<Accordion.Item className="AccordionItem" value="item-3">



<AccordionTrigger>Can it be animated?</AccordionTrigger>



<Accordion.Content className="AccordionContent">



<div className="AccordionContentText">



Yes! You can animate the Accordion with CSS or JavaScript.



</div>



</Accordion.Content>



</Accordion.Item>



</Accordion.Root>



);



const AccordionTrigger = React.forwardRef(



({ children, className, ...props }, forwardedRef) => (



<Accordion.Header className="AccordionHeader">



<Accordion.Trigger
				className={classNames("AccordionTrigger", className)}
				{...props}
				ref={forwardedRef}
			>



{children}



<ChevronDownIcon className="AccordionChevron" aria-hidden />



</Accordion.Trigger>



</Accordion.Header>



),



);



const AccordionContent = React.forwardRef(



({ children, className, ...props }, forwardedRef) => (



<Accordion.Content
			className={classNames("AccordionContent", className)}
			{...props}
			ref={forwardedRef}
		>



<div className="AccordionContentText">{children}</div>



</Accordion.Content>



),



);



export default AccordionDemo;



Expand code
```

## Features

Full keyboard navigation.

Supports horizontal/vertical orientation.

Supports Right to Left direction.

Can expand one or multiple items.

Can be controlled or uncontrolled.

## Component Reference Links

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/accordion/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

[ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/accordion)

## [Installation](#installation)

Install the component from your command line.

```
npm install @radix-ui/react-accordion
```

## [Anatomy](#anatomy)

Import all parts and piece them together.

```
import { Accordion } from "radix-ui";



export default () => (



<Accordion.Root>



<Accordion.Item>



<Accordion.Header>



<Accordion.Trigger />



</Accordion.Header>



<Accordion.Content />



</Accordion.Item>



</Accordion.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of an accordion.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `type*` Prop description | `enum` See full type | No default value |
| `value` Prop description | `string` | No default value |
| `defaultValue` Prop description | `string` | No default value |
| `onValueChange` Prop description | `function` See full type | No default value |
| `value` Prop description | `string[]` | `[]` |
| `defaultValue` Prop description | `string[]` | `[]` |
| `onValueChange` Prop description | `function` See full type | No default value |
| `collapsible` Prop description | `boolean` | `false` |
| `disabled` Prop description | `boolean` | `false` |
| `dir` Prop description | `enum` See full type | `"ltr"` |
| `orientation` Prop description | `enum` See full type | `"vertical"` |

| Data attribute | Values |
| --- | --- |
| `[data-orientation]` | `"vertical" | "horizontal"` |

### [Item](#item)

Contains all the parts of a collapsible section.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `disabled` Prop description | `boolean` | `false` |
| `value*` Prop description | `string` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |
| `[data-orientation]` | `"vertical" | "horizontal"` |

### [Header](#header)

Wraps an `Accordion.Trigger`. Use the `asChild` prop to update it to the appropriate heading level for your page.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |
| `[data-orientation]` | `"vertical" | "horizontal"` |

### [Trigger](#trigger)

Toggles the collapsed state of its associated item. It should be nested inside of an `Accordion.Header`.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |
| `[data-orientation]` | `"vertical" | "horizontal"` |

### [Content](#content)

Contains the collapsible content for an item.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `forceMount` Prop description | `boolean` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |
| `[data-orientation]` | `"vertical" | "horizontal"` |

| CSS Variable | Description |
| --- | --- |
| `--radix-accordion-content-width` | The width of the content when it opens/closes |
| `--radix-accordion-content-height` | The height of the content when it opens/closes |

## [Examples](#examples)

### [Expanded by default](#expanded-by-default)

Use the `defaultValue` prop to define the open item by default.

```
<Accordion.Root type="single" defaultValue="item-2">



<Accordion.Item value="item-1">â€¦</Accordion.Item>



<Accordion.Item value="item-2">â€¦</Accordion.Item>



</Accordion.Root>
```

### [Allow collapsing all items](#allow-collapsing-all-items)

Use the `collapsible` prop to allow all items to close.

```
<Accordion.Root type="single" collapsible>



<Accordion.Item value="item-1">â€¦</Accordion.Item>



<Accordion.Item value="item-2">â€¦</Accordion.Item>



</Accordion.Root>
```

### [Multiple items open at the same time](#multiple-items-open-at-the-same-time)

Set the `type` prop to `multiple` to enable opening multiple items at once.

```
<Accordion.Root type="multiple">



<Accordion.Item value="item-1">â€¦</Accordion.Item>



<Accordion.Item value="item-2">â€¦</Accordion.Item>



</Accordion.Root>
```

### [Rotated icon when open](#rotated-icon-when-open)

You can add extra decorative elements, such as chevrons, and rotate it when the item is open.

```
// index.jsx



import { Accordion } from "radix-ui";



import { ChevronDownIcon } from "@radix-ui/react-icons";



import "./styles.css";



export default () => (



<Accordion.Root type="single">



<Accordion.Item value="item-1">



<Accordion.Header>



<Accordion.Trigger className="AccordionTrigger">



<span>Trigger text</span>



<ChevronDownIcon className="AccordionChevron" aria-hidden />



</Accordion.Trigger>



</Accordion.Header>



<Accordion.Content>â€¦</Accordion.Content>



</Accordion.Item>



</Accordion.Root>



);
```

```
/* styles.css */



.AccordionChevron {



transition: transform 300ms;



}



.AccordionTrigger[data-state="open"] > .AccordionChevron {



transform: rotate(180deg);



}
```

### [Horizontal orientation](#horizontal-orientation)

Use the `orientation` prop to create a horizontal accordion.

```
<Accordion.Root orientation="horizontal">



<Accordion.Item value="item-1">â€¦</Accordion.Item>



<Accordion.Item value="item-2">â€¦</Accordion.Item>



</Accordion.Root>
```

### [Animating content size](#animating-content-size)

Use the `--radix-accordion-content-width` and/or `--radix-accordion-content-height` CSS variables to animate the size of the content when it opens/closes:

```
// index.jsx



import { Accordion } from "radix-ui";



import "./styles.css";



export default () => (



<Accordion.Root type="single">



<Accordion.Item value="item-1">



<Accordion.Header>â€¦</Accordion.Header>



<Accordion.Content className="AccordionContent">â€¦</Accordion.Content>



</Accordion.Item>



</Accordion.Root>



);
```

```
/* styles.css */



.AccordionContent {



overflow: hidden;



}



.AccordionContent[data-state="open"] {



animation: slideDown 300ms ease-out;



}



.AccordionContent[data-state="closed"] {



animation: slideUp 300ms ease-out;



}



@keyframes slideDown {



from {



height: 0;



}



to {



height: var(--radix-accordion-content-height);



}



}



@keyframes slideUp {



from {



height: var(--radix-accordion-content-height);



}



to {



height: 0;



}



}
```

## [Accessibility](#accessibility)

Adheres to the [Accordion WAI-ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/accordion).

### [Keyboard Interactions](#keyboard-interactions)

| Key | Description |
| --- | --- |
| `Space` | When focus is on an `Accordion.Trigger` of a collapsed section, expands the section. |
| `Enter` | When focus is on an `Accordion.Trigger` of a collapsed section, expands the section. |
| `Tab` | Moves focus to the next focusable element. |
| `Shift + Tab` | Moves focus to the previous focusable element. |
| `ArrowDown` | Moves focus to the next `Accordion.Trigger` when `orientation` is `vertical`. |
| `ArrowUp` | Moves focus to the previous `Accordion.Trigger` when `orientation` is `vertical`. |
| `ArrowRight` | Moves focus to the next `Accordion.Trigger` when `orientation` is `horizontal`. |
| `ArrowLeft` | Moves focus to the previous `Accordion.Trigger` when `orientation` is `horizontal`. |
| `Home` | When focus is on an `Accordion.Trigger`, moves focus to the first `Accordion.Trigger`. |
| `End` | When focus is on an `Accordion.Trigger`, moves focus to the last `Accordion.Trigger`. |

#### Quick nav

Previous[Server-side rendering](/primitives/docs/guides/server-side-rendering)

Next[Alert Dialog](/primitives/docs/components/alert-dialog)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/accordion.mdx "Edit this page on GitHub.")
