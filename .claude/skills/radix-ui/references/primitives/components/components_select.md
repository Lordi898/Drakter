Select â€“ Radix Primitives

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

# Select

Displays a list of options for the user to pick fromâ€”triggered by a button.

Select a fruitâ€¦

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { Select } from "radix-ui";



import classnames from "classnames";



import {
	CheckIcon,
	ChevronDownIcon,
	ChevronUpIcon,
} from "@radix-ui/react-icons";



import "./styles.css";



const SelectDemo = () => (



<Select.Root>



<Select.Trigger className="SelectTrigger" aria-label="Food">



<Select.Value placeholder="Select a fruitâ€¦" />



<Select.Icon className="SelectIcon">



<ChevronDownIcon />



</Select.Icon>



</Select.Trigger>



<Select.Portal>



<Select.Content className="SelectContent">



<Select.ScrollUpButton className="SelectScrollButton">



<ChevronUpIcon />



</Select.ScrollUpButton>



<Select.Viewport className="SelectViewport">



<Select.Group>



<Select.Label className="SelectLabel">Fruits</Select.Label>



<SelectItem value="apple">Apple</SelectItem>



<SelectItem value="banana">Banana</SelectItem>



<SelectItem value="blueberry">Blueberry</SelectItem>



<SelectItem value="grapes">Grapes</SelectItem>



<SelectItem value="pineapple">Pineapple</SelectItem>



</Select.Group>



<Select.Separator className="SelectSeparator" />



<Select.Group>



<Select.Label className="SelectLabel">Vegetables</Select.Label>



<SelectItem value="aubergine">Aubergine</SelectItem>



<SelectItem value="broccoli">Broccoli</SelectItem>



<SelectItem value="carrot" disabled>



Carrot



</SelectItem>



<SelectItem value="courgette">Courgette</SelectItem>



<SelectItem value="leek">Leek</SelectItem>



</Select.Group>



<Select.Separator className="SelectSeparator" />



<Select.Group>



<Select.Label className="SelectLabel">Meat</Select.Label>



<SelectItem value="beef">Beef</SelectItem>



<SelectItem value="chicken">Chicken</SelectItem>



<SelectItem value="lamb">Lamb</SelectItem>



<SelectItem value="pork">Pork</SelectItem>



</Select.Group>



</Select.Viewport>



<Select.ScrollDownButton className="SelectScrollButton">



<ChevronDownIcon />



</Select.ScrollDownButton>



</Select.Content>



</Select.Portal>



</Select.Root>



);



const SelectItem = React.forwardRef(



({ children, className, ...props }, forwardedRef) => {



return (



<Select.Item
				className={classnames("SelectItem", className)}
				{...props}
				ref={forwardedRef}
			>



<Select.ItemText>{children}</Select.ItemText>



<Select.ItemIndicator className="SelectItemIndicator">



<CheckIcon />



</Select.ItemIndicator>



</Select.Item>



);



},



);



export default SelectDemo;



Expand code
```

## Features

Can be controlled or uncontrolled.

Offers 2 positioning modes.

Supports items, labels, groups of items.

Focus is fully managed.

Full keyboard navigation.

Supports custom placeholder.

Typeahead support.

Supports Right to Left direction.

## Component Reference Links

Version: 2.2.6

Size: [34.89 kB](https://bundlephobia.com/package/@radix-ui/react-select@2.2.6)

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/select/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

[ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/listbox)

## [Installation](#installation)

Install the component from your command line.

```
npm install @radix-ui/react-select
```

## [Anatomy](#anatomy)

Import all parts and piece them together.

```
import { Select } from "radix-ui";



export default () => (



<Select.Root>



<Select.Trigger>



<Select.Value />



<Select.Icon />



</Select.Trigger>



<Select.Portal>



<Select.Content>



<Select.ScrollUpButton />



<Select.Viewport>



<Select.Item>



<Select.ItemText />



<Select.ItemIndicator />



</Select.Item>



<Select.Group>



<Select.Label />



<Select.Item>



<Select.ItemText />



<Select.ItemIndicator />



</Select.Item>



</Select.Group>



<Select.Separator />



</Select.Viewport>



<Select.ScrollDownButton />



<Select.Arrow />



</Select.Content>



</Select.Portal>



</Select.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of a select.

| Prop | Type | Default |
| --- | --- | --- |
| `defaultValue` Prop description | `string` | No default value |
| `value` Prop description | `string` | No default value |
| `onValueChange` Prop description | `function` See full type | No default value |
| `defaultOpen` Prop description | `boolean` | No default value |
| `open` Prop description | `boolean` | No default value |
| `onOpenChange` Prop description | `function` See full type | No default value |
| `dir` Prop description | `enum` See full type | No default value |
| `name` Prop description | `string` | No default value |
| `disabled` Prop description | `boolean` | No default value |
| `required` Prop description | `boolean` | No default value |

### [Trigger](#trigger)

The button that toggles the select. The `Select.Content` will position itself by aligning over the trigger.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |
| `[data-placeholder]` | Present when has placeholder |

### [Value](#value)

The part that reflects the selected value. By default the selected item's text will be rendered. if you require more control, you can instead control the select and pass your own `children`. It should not be styled to ensure correct positioning. An optional `placeholder` prop is also available for when the select has no value.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `placeholder` Prop description | `ReactNode` | No default value |

### [Icon](#icon)

A small icon often displayed next to the value as a visual affordance for the fact it can be open. By default renders â–¼ but you can use your own icon via `asChild` or use `children`.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Portal](#portal)

When used, portals the content part into the `body`.

| Prop | Type | Default |
| --- | --- | --- |
| `container` Prop description | `HTMLElement` | `document.body` |

### [Content](#content)

The component that pops out when the select is open.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `onCloseAutoFocus` Prop description | `function` See full type | No default value |
| `onEscapeKeyDown` Prop description | `function` See full type | No default value |
| `onPointerDownOutside` Prop description | `function` See full type | No default value |
| `position` Prop description | `enum` See full type | `"item-aligned"` |
| `side` Prop description | `enum` See full type | `"bottom"` |
| `sideOffset` Prop description | `number` | `0` |
| `align` Prop description | `enum` See full type | `"start"` |
| `alignOffset` Prop description | `number` | `0` |
| `avoidCollisions` Prop description | `boolean` | `true` |
| `collisionBoundary` Prop description | `Boundary` See full type | `[]` |
| `collisionPadding` Prop description | `number | Padding` See full type | `10` |
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
| `--radix-select-content-transform-origin` | The `transform-origin` computed from the content and arrow positions/offsets. Only present when `position="popper"`. |
| `--radix-select-content-available-width` | The remaining width between the trigger and the boundary edge. Only present when `position="popper"`. |
| `--radix-select-content-available-height` | The remaining height between the trigger and the boundary edge. Only present when `position="popper"`. |
| `--radix-select-trigger-width` | The width of the trigger. Only present when `position="popper"`. |
| `--radix-select-trigger-height` | The height of the trigger. Only present when `position="popper"`. |

### [Viewport](#viewport)

The scrolling viewport that contains all of the items.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Item](#item)

The component that contains the select items.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `value*` Prop description | `string` | No default value |
| `disabled` Prop description | `boolean` | No default value |
| `textValue` Prop description | `string` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"checked" | "unchecked"` |
| `[data-highlighted]` | Present when highlighted |
| `[data-disabled]` | Present when disabled |

### [ItemText](#itemtext)

The textual part of the item. It should only contain the text you want to see in the trigger when that item is selected. It should not be styled to ensure correct positioning.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [ItemIndicator](#itemindicator)

Renders when the item is selected. You can style this element directly, or you can use it as a wrapper to put an icon into, or both.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [ScrollUpButton](#scrollupbutton)

An optional button used as an affordance to show the viewport overflow as well as functionaly enable scrolling upwards.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [ScrollDownButton](#scrolldownbutton)

An optional button used as an affordance to show the viewport overflow as well as functionaly enable scrolling downwards.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Group](#group)

Used to group multiple items. use in conjunction with `Select.Label` to ensure good accessibility via automatic labelling.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Label](#label)

Used to render the label of a group. It won't be focusable using arrow keys.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Separator](#separator)

Used to visually separate items in the select.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Arrow](#arrow)

An optional arrow element to render alongside the content. This can be used to help visually link the trigger with the `Select.Content`. Must be rendered inside `Select.Content`. Only available when `position` is set to `popper`.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `width` Prop description | `number` | `10` |
| `height` Prop description | `number` | `5` |

## [Examples](#examples)

### [Change the positioning mode](#change-the-positioning-mode)

By default, `Select` will behave similarly to a native MacOS menu by positioning `Select.Content` relative to the active item. If you would prefer an alternative positioning approach similar to `Popover` or `DropdownMenu` then you can set `position` to `popper` and make use of additional alignment options such as `side`, `sideOffset` and more.

```
// index.jsx



import { Select } from "radix-ui";



export default () => (



<Select.Root>



<Select.Trigger>â€¦</Select.Trigger>



<Select.Portal>



<Select.Content position="popper" sideOffset={5}>



â€¦



</Select.Content>



</Select.Portal>



</Select.Root>



);
```

### [Constrain the content size](#constrain-the-content-size)

When using `position="popper"` on `Select.Content`, you may want to constrain the width of the content so that it matches the trigger width. You may also want to constrain its height to not exceed the viewport.

We expose several CSS custom properties such as `--radix-select-trigger-width` and `--radix-select-content-available-height` to support this. Use them to constrain the content dimensions.

```
// index.jsx



import { Select } from "radix-ui";



import "./styles.css";



export default () => (



<Select.Root>



<Select.Trigger>â€¦</Select.Trigger>



<Select.Portal>



<Select.Content
				className="SelectContent"
				position="popper"
				sideOffset={5}
			>



â€¦



</Select.Content>



</Select.Portal>



</Select.Root>



);
```

```
/* styles.css */



.SelectContent {



width: var(--radix-select-trigger-width);



max-height: var(--radix-select-content-available-height);



}
```

### [With disabled items](#with-disabled-items)

You can add special styles to disabled items via the `data-disabled` attribute.

```
// index.jsx



import { Select } from "radix-ui";



import "./styles.css";



export default () => (



<Select.Root>



<Select.Trigger>â€¦</Select.Trigger>



<Select.Portal>



<Select.Content>



<Select.Viewport>



<Select.Item className="SelectItem" disabled>



â€¦



</Select.Item>



<Select.Item>â€¦</Select.Item>



<Select.Item>â€¦</Select.Item>



</Select.Viewport>



</Select.Content>



</Select.Portal>



</Select.Root>



);
```

```
/* styles.css */



.SelectItem[data-disabled] {



color: "gainsboro";



}
```

### [With a placeholder](#with-a-placeholder)

You can use the `placeholder` prop on `Value` for when the select has no value. There's also a `data-placeholder` attribute on `Trigger` to help with styling.

```
// index.jsx



import { Select } from "radix-ui";



import "./styles.css";



export default () => (



<Select.Root>



<Select.Trigger className="SelectTrigger">



<Select.Value placeholder="Pick an option" />



<Select.Icon />



</Select.Trigger>



<Select.Portal>



<Select.Content>â€¦</Select.Content>



</Select.Portal>



</Select.Root>



);
```

```
/* styles.css */



.SelectTrigger[data-placeholder] {



color: "gainsboro";



}
```

### [With separators](#with-separators)

Use the `Separator` part to add a separator between items.

```
<Select.Root>



<Select.Trigger>â€¦</Select.Trigger>



<Select.Portal>



<Select.Content>



<Select.Viewport>



<Select.Item>â€¦</Select.Item>



<Select.Item>â€¦</Select.Item>



<Select.Item>â€¦</Select.Item>



<Select.Separator />



<Select.Item>â€¦</Select.Item>



<Select.Item>â€¦</Select.Item>



</Select.Viewport>



</Select.Content>



</Select.Portal>



</Select.Root>
```

### [With grouped items](#with-grouped-items)

Use the `Group` and `Label` parts to group items in a section.

```
<Select.Root>



<Select.Trigger>â€¦</Select.Trigger>



<Select.Portal>



<Select.Content>



<Select.Viewport>



<Select.Group>



<Select.Label>Label</Select.Label>



<Select.Item>â€¦</Select.Item>



<Select.Item>â€¦</Select.Item>



<Select.Item>â€¦</Select.Item>



</Select.Group>



</Select.Viewport>



</Select.Content>



</Select.Portal>



</Select.Root>
```

### [With complex items](#with-complex-items)

You can use custom content in your items.

```
import { Select } from "radix-ui";



export default () => (



<Select.Root>



<Select.Trigger>â€¦</Select.Trigger>



<Select.Portal>



<Select.Content>



<Select.Viewport>



<Select.Item>



<Select.ItemText>



<img src="â€¦" />



Adolfo Hess



</Select.ItemText>



<Select.ItemIndicator>â€¦</Select.ItemIndicator>



</Select.Item>



<Select.Item>â€¦</Select.Item>



<Select.Item>â€¦</Select.Item>



</Select.Viewport>



</Select.Content>



</Select.Portal>



</Select.Root>



);
```

### [Controlling the value displayed in the trigger](#controlling-the-value-displayed-in-the-trigger)

By default the trigger will automatically display the selected item `ItemText`'s content. You can control what appears by chosing to put things inside/outside the `ItemText` part.

If you need more flexibility, you can control the component using `value`/`onValueChange` props and passing `children` to `SelectValue`. Remember to make sure what you put in there is accessible.

```
const countries = { france: "ðŸ‡«ðŸ‡·", "united-kingdom": "ðŸ‡¬ðŸ‡§", spain: "ðŸ‡ªðŸ‡¸" };



export default () => {



const [value, setValue] = React.useState("france");



return (



<Select.Root value={value} onValueChange={setValue}>



<Select.Trigger>



<Select.Value aria-label={value}>



{countries[value]}



</Select.Value>



<Select.Icon />



</Select.Trigger>



<Select.Portal>



<Select.Content>



<Select.Viewport>



<Select.Item value="france">



<Select.ItemText>France</Select.ItemText>



<Select.ItemIndicator>â€¦</Select.ItemIndicator>



</Select.Item>



<Select.Item value="united-kingdom">



<Select.ItemText>United Kingdom</Select.ItemText>



<Select.ItemIndicator>â€¦</Select.ItemIndicator>



</Select.Item>



<Select.Item value="spain">



<Select.ItemText>Spain</Select.ItemText>



<Select.ItemIndicator>â€¦</Select.ItemIndicator>



</Select.Item>



</Select.Viewport>



</Select.Content>



</Select.Portal>



</Select.Root>



);



};
```

### [With custom scrollbar](#with-custom-scrollbar)

The native scrollbar is hidden by default as we recommend using the `ScrollUpButton` and `ScrollDownButton` parts for the best UX. If you do not want to use these parts, compose your select with our [Scroll Area](/primitives/docs/components/scroll-area) primitive.

```
// index.jsx



import { Select, ScrollArea } from "radix-ui";



import "./styles.css";



export default () => (



<Select.Root>



<Select.Trigger>â€¦</Select.Trigger>



<Select.Portal>



<Select.Content>



<ScrollArea.Root className="ScrollAreaRoot" type="auto">



<Select.Viewport asChild>



<ScrollArea.Viewport className="ScrollAreaViewport">



<StyledItem>â€¦</StyledItem>



<StyledItem>â€¦</StyledItem>



<StyledItem>â€¦</StyledItem>



</ScrollArea.Viewport>



</Select.Viewport>



<ScrollArea.Scrollbar
						className="ScrollAreaScrollbar"
						orientation="vertical"
					>



<ScrollArea.Thumb className="ScrollAreaThumb" />



</ScrollArea.Scrollbar>



</ScrollArea.Root>



</Select.Content>



</Select.Portal>



</Select.Root>



);
```

```
/* styles.css */



.ScrollAreaRoot {



width: 100%;



height: 100%;



}



.ScrollAreaViewport {



width: 100%;



height: 100%;



}



.ScrollAreaScrollbar {



width: 4px;



padding: 5px 2px;



}



.ScrollAreaThumb {



background: rgba(0, 0, 0, 0.3);



border-radius: 3px;



}
```

## [Accessibility](#accessibility)

Adheres to the [ListBox WAI-ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/listbox).

See the W3C [Select-Only Combobox](https://www.w3.org/TR/wai-aria-practices/examples/combobox/combobox-select-only.html) example for more information.

### [Keyboard Interactions](#keyboard-interactions)

| Key | Description |
| --- | --- |
| `Space` | When focus is on `Select.Trigger`, opens the select and focuses the selected item. When focus is on an item, selects the focused item. |
| `Enter` | When focus is on `Select.Trigger`, opens the select and focuses the first item. When focus is on an item, selects the focused item. |
| `ArrowDown` | When focus is on `Select.Trigger`, opens the select. When focus is on an item, moves focus to the next item. |
| `ArrowUp` | When focus is on `Select.Trigger`, opens the select. When focus is on an item, moves focus to the previous item. |
| `Esc` | Closes the select and moves focus to `Select.Trigger`. |

### [Labelling](#labelling)

Use our [Label](/primitives/docs/components/label) component in order to offer a visual and accessible label for the select.

```
import { Select, Label } from "radix-ui";



export default () => (



<>



<Label>



Country



<Select.Root>â€¦</Select.Root>



</Label>



{/* or */}



<Label htmlFor="country">Country</Label>



<Select.Root>



<Select.Trigger id="country">â€¦</Select.Trigger>



<Select.Portal>



<Select.Content>â€¦</Select.Content>



</Select.Portal>



</Select.Root>



</>



);
```

## [Custom APIs](#custom-apis)

Create your own API by abstracting the primitive parts into your own component.

### [Abstract down to `Select` and `SelectItem`](#abstract-down-to-select-and-selectitem)

This example abstracts most of the parts.

#### Usage

```
import { Select, SelectItem } from "./your-select";



export default () => (



<Select defaultValue="2">



<SelectItem value="1">Item 1</SelectItem>



<SelectItem value="2">Item 2</SelectItem>



<SelectItem value="3">Item 3</SelectItem>



</Select>



);
```

#### Implementation

```
// your-select.jsx



import * as React from "react";



import { Select as SelectPrimitive } from "radix-ui";



import {
	CheckIcon,
	ChevronDownIcon,
	ChevronUpIcon,
} from "@radix-ui/react-icons";



export const Select = React.forwardRef(



({ children, ...props }, forwardedRef) => {



return (



<SelectPrimitive.Root {...props}>



<SelectPrimitive.Trigger ref={forwardedRef}>



<SelectPrimitive.Value />



<SelectPrimitive.Icon>



<ChevronDownIcon />



</SelectPrimitive.Icon>



</SelectPrimitive.Trigger>



<SelectPrimitive.Portal>



<SelectPrimitive.Content>



<SelectPrimitive.ScrollUpButton>



<ChevronUpIcon />



</SelectPrimitive.ScrollUpButton>



<SelectPrimitive.Viewport>{children}</SelectPrimitive.Viewport>



<SelectPrimitive.ScrollDownButton>



<ChevronDownIcon />



</SelectPrimitive.ScrollDownButton>



</SelectPrimitive.Content>



</SelectPrimitive.Portal>



</SelectPrimitive.Root>



);



},



);



export const SelectItem = React.forwardRef(



({ children, ...props }, forwardedRef) => {



return (



<SelectPrimitive.Item {...props} ref={forwardedRef}>



<SelectPrimitive.ItemText>{children}</SelectPrimitive.ItemText>



<SelectPrimitive.ItemIndicator>



<CheckIcon />



</SelectPrimitive.ItemIndicator>



</SelectPrimitive.Item>



);



},



);
```

#### Quick nav

Previous[Scroll Area](/primitives/docs/components/scroll-area)

Next[Separator](/primitives/docs/components/separator)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/select.mdx "Edit this page on GitHub.")
