Popover â€“ Radix Primitives

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

# Popover

Displays rich content in a portal, triggered by a button.

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { Popover } from "radix-ui";



import { MixerHorizontalIcon, Cross2Icon } from "@radix-ui/react-icons";



import "./styles.css";



const PopoverDemo = () => (



<Popover.Root>



<Popover.Trigger asChild>



<button className="IconButton" aria-label="Update dimensions">



<MixerHorizontalIcon />



</button>



</Popover.Trigger>



<Popover.Portal>



<Popover.Content className="PopoverContent" sideOffset={5}>



<div style={{ display: "flex", flexDirection: "column", gap: 10 }}>



<p className="Text" style={{ marginBottom: 10 }}>



Dimensions



</p>



<fieldset className="Fieldset">



<label className="Label" htmlFor="width">



Width



</label>



<input className="Input" id="width" defaultValue="100%" />



</fieldset>



<fieldset className="Fieldset">



<label className="Label" htmlFor="maxWidth">



Max. width



</label>



<input className="Input" id="maxWidth" defaultValue="300px" />



</fieldset>



<fieldset className="Fieldset">



<label className="Label" htmlFor="height">



Height



</label>



<input className="Input" id="height" defaultValue="25px" />



</fieldset>



<fieldset className="Fieldset">



<label className="Label" htmlFor="maxHeight">



Max. height



</label>



<input className="Input" id="maxHeight" defaultValue="none" />



</fieldset>



</div>



<Popover.Close className="PopoverClose" aria-label="Close">



<Cross2Icon />



</Popover.Close>



<Popover.Arrow className="PopoverArrow" />



</Popover.Content>



</Popover.Portal>



</Popover.Root>



);



export default PopoverDemo;



Expand code
```

## Features

Can be controlled or uncontrolled.

Customize side, alignment, offsets, collision handling.

Optionally render a pointing arrow.

Focus is fully managed and customizable.

Supports modal and non-modal modes.

Dismissing and layering behavior is highly customizable.

## Component Reference Links

Version: 1.1.15

Size: [28.73 kB](https://bundlephobia.com/package/@radix-ui/react-popover@1.1.15)

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/popover/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

[ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal)

## [Installation](#installation)

Install the component from your command line.

```
npm install @radix-ui/react-popover
```

## [Anatomy](#anatomy)

Import all parts and piece them together.

```
import { Popover } from "radix-ui";



export default () => (



<Popover.Root>



<Popover.Trigger />



<Popover.Anchor />



<Popover.Portal>



<Popover.Content>



<Popover.Close />



<Popover.Arrow />



</Popover.Content>



</Popover.Portal>



</Popover.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of a popover.

| Prop | Type | Default |
| --- | --- | --- |
| `defaultOpen` Prop description | `boolean` | No default value |
| `open` Prop description | `boolean` | No default value |
| `onOpenChange` Prop description | `function` See full type | No default value |
| `modal` Prop description | `boolean` | `false` |

### [Trigger](#trigger)

The button that toggles the popover. By default, the `Popover.Content` will position itself against the trigger.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |

### [Anchor](#anchor)

An optional element to position the `Popover.Content` against. If this part is not used, the content will position alongside the `Popover.Trigger`.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Portal](#portal)

When used, portals the content part into the `body`.

| Prop | Type | Default |
| --- | --- | --- |
| `forceMount` Prop description | `boolean` | No default value |
| `container` Prop description | `HTMLElement` | `document.body` |

### [Content](#content)

The component that pops out when the popover is open.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `onOpenAutoFocus` Prop description | `function` See full type | No default value |
| `onCloseAutoFocus` Prop description | `function` See full type | No default value |
| `onEscapeKeyDown` Prop description | `function` See full type | No default value |
| `onPointerDownOutside` Prop description | `function` See full type | No default value |
| `onFocusOutside` Prop description | `function` See full type | No default value |
| `onInteractOutside` Prop description | `function` See full type | No default value |
| `forceMount` Prop description | `boolean` | No default value |
| `side` Prop description | `enum` See full type | `"bottom"` |
| `sideOffset` Prop description | `number` | `0` |
| `align` Prop description | `enum` See full type | `"center"` |
| `alignOffset` Prop description | `number` | `0` |
| `avoidCollisions` Prop description | `boolean` | `true` |
| `collisionBoundary` Prop description | `Boundary` See full type | `[]` |
| `collisionPadding` Prop description | `number | Padding` See full type | `0` |
| `arrowPadding` Prop description | `number` | `0` |
| `sticky` Prop description | `enum` See full type | `"partial"` |
| `hideWhenDetached` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-side]` | `"left" | "right" | "bottom" | "top"` |
| `[data-align]` | `"start" | "end" | "center"` |

| CSS Variable | Description |
| --- | --- |
| `--radix-popover-content-transform-origin` | The `transform-origin` computed from the content and arrow positions/offsets |
| `--radix-popover-content-available-width` | The remaining width between the trigger and the boundary edge |
| `--radix-popover-content-available-height` | The remaining height between the trigger and the boundary edge |
| `--radix-popover-trigger-width` | The width of the trigger |
| `--radix-popover-trigger-height` | The height of the trigger |

### [Arrow](#arrow)

An optional arrow element to render alongside the popover. This can be used to help visually link the anchor with the `Popover.Content`. Must be rendered inside `Popover.Content`.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `width` Prop description | `number` | `10` |
| `height` Prop description | `number` | `5` |

### [Close](#close)

The button that closes an open popover.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

## [Examples](#examples)

### [Constrain the content size](#constrain-the-content-size)

You may want to constrain the width of the content so that it matches the trigger width. You may also want to constrain its height to not exceed the viewport.

We expose several CSS custom properties such as `--radix-popover-trigger-width` and `--radix-popover-content-available-height` to support this. Use them to constrain the content dimensions.

```
// index.jsx



import { Popover } from "radix-ui";



import "./styles.css";



export default () => (



<Popover.Root>



<Popover.Trigger>â€¦</Popover.Trigger>



<Popover.Portal>



<Popover.Content className="PopoverContent" sideOffset={5}>



â€¦



</Popover.Content>



</Popover.Portal>



</Popover.Root>



);
```

```
/* styles.css */



.PopoverContent {



width: var(--radix-popover-trigger-width);



max-height: var(--radix-popover-content-available-height);



}
```

### [Origin-aware animations](#origin-aware-animations)

We expose a CSS custom property `--radix-popover-content-transform-origin`. Use it to animate the content from its computed origin based on `side`, `sideOffset`, `align`, `alignOffset` and any collisions.

```
// index.jsx



import { Popover } from "radix-ui";



import "./styles.css";



export default () => (



<Popover.Root>



<Popover.Trigger>â€¦</Popover.Trigger>



<Popover.Portal>



<Popover.Content className="PopoverContent">â€¦</Popover.Content>



</Popover.Portal>



</Popover.Root>



);
```

```
/* styles.css */



.PopoverContent {



transform-origin: var(--radix-popover-content-transform-origin);



animation: scaleIn 0.5s ease-out;



}



@keyframes scaleIn {



from {



opacity: 0;



transform: scale(0);



}



to {



opacity: 1;



transform: scale(1);



}



}
```

### [Collision-aware animations](#collision-aware-animations)

We expose `data-side` and `data-align` attributes. Their values will change at runtime to reflect collisions. Use them to create collision and direction-aware animations.

```
// index.jsx



import { Popover } from "radix-ui";



import "./styles.css";



export default () => (



<Popover.Root>



<Popover.Trigger>â€¦</Popover.Trigger>



<Popover.Portal>



<Popover.Content className="PopoverContent">â€¦</Popover.Content>



</Popover.Portal>



</Popover.Root>



);
```

```
/* styles.css */



.PopoverContent {



animation-duration: 0.6s;



animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);



}



.PopoverContent[data-side="top"] {



animation-name: slideUp;



}



.PopoverContent[data-side="bottom"] {



animation-name: slideDown;



}



@keyframes slideDown {



from {



opacity: 0;



transform: translateY(-10px);



}



to {



opacity: 1;



transform: translateY(0);



}



}



@keyframes slideUp {



from {



opacity: 0;



transform: translateY(10px);



}



to {



opacity: 1;



transform: translateY(0);



}



}
```

### [With custom anchor](#with-custom-anchor)

You can anchor the content to another element if you do not want to use the trigger as the anchor.

```
// index.jsx



import { Popover } from "radix-ui";



import "./styles.css";



export default () => (



<Popover.Root>



<Popover.Anchor asChild>



<div className="Row">



Row as anchor <Popover.Trigger>Trigger</Popover.Trigger>



</div>



</Popover.Anchor>



<Popover.Portal>



<Popover.Content>â€¦</Popover.Content>



</Popover.Portal>



</Popover.Root>



);
```

```
/* styles.css */



.Row {



background-color: gainsboro;



padding: 20px;



}
```

## [Accessibility](#accessibility)

Adheres to the [Dialog WAI-ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal).

### [Keyboard Interactions](#keyboard-interactions)

| Key | Description |
| --- | --- |
| `Space` | Opens/closes the popover. |
| `Enter` | Opens/closes the popover. |
| `Tab` | Moves focus to the next focusable element |
| `Shift + Tab` | Moves focus to the previous focusable element |
| `Esc` | Closes the popover and moves focus to `Popover.Trigger`. |

## [Custom APIs](#custom-apis)

Create your own API by abstracting the primitive parts into your own component.

#### Abstract the arrow and set default configuration

This example abstracts the `Popover.Arrow` part and sets a default `sideOffset` configuration.

#### Usage

```
import { Popover, PopoverTrigger, PopoverContent } from "./your-popover";



export default () => (



<Popover>



<PopoverTrigger>Popover trigger</PopoverTrigger>



<PopoverContent>Popover content</PopoverContent>



</Popover>



);
```

#### Implementation

```
// your-popover.jsx



import * as React from "react";



import { Popover as PopoverPrimitive } from "radix-ui";



export const Popover = PopoverPrimitive.Root;



export const PopoverTrigger = PopoverPrimitive.Trigger;



export const PopoverContent = React.forwardRef(



({ children, ...props }, forwardedRef) => (



<PopoverPrimitive.Portal>



<PopoverPrimitive.Content sideOffset={5} {...props} ref={forwardedRef}>



{children}



<PopoverPrimitive.Arrow />



</PopoverPrimitive.Content>



</PopoverPrimitive.Portal>



),



);
```

#### Quick nav

Previous[Password Toggle Field](/primitives/docs/components/password-toggle-field)

Next[Progress](/primitives/docs/components/progress)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/popover.mdx "Edit this page on GitHub.")
