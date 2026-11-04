Dropdown Menu â€“ Radix Primitives

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

# Dropdown Menu

Displays a menu to the userâ€”such as a set of actions or functionsâ€”triggered by
a button.

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { DropdownMenu } from "radix-ui";



import {
	HamburgerMenuIcon,
	DotFilledIcon,
	CheckIcon,
	ChevronRightIcon,
} from "@radix-ui/react-icons";



import "./styles.css";



const DropdownMenuDemo = () => {



const [bookmarksChecked, setBookmarksChecked] = React.useState(true);



const [urlsChecked, setUrlsChecked] = React.useState(false);



const [person, setPerson] = React.useState("pedro");



return (



<DropdownMenu.Root>



<DropdownMenu.Trigger asChild>



<button className="IconButton" aria-label="Customise options">



<HamburgerMenuIcon />



</button>



</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content className="DropdownMenuContent" sideOffset={5}>



<DropdownMenu.Item className="DropdownMenuItem">



New Tab <div className="RightSlot">âŒ˜+T</div>



</DropdownMenu.Item>



<DropdownMenu.Item className="DropdownMenuItem">



New Window <div className="RightSlot">âŒ˜+N</div>



</DropdownMenu.Item>



<DropdownMenu.Item className="DropdownMenuItem" disabled>



New Private Window <div className="RightSlot">â‡§+âŒ˜+N</div>



</DropdownMenu.Item>



<DropdownMenu.Sub>



<DropdownMenu.SubTrigger className="DropdownMenuSubTrigger">



More Tools



<div className="RightSlot">



<ChevronRightIcon />



</div>



</DropdownMenu.SubTrigger>



<DropdownMenu.Portal>



<DropdownMenu.SubContent
								className="DropdownMenuSubContent"
								sideOffset={2}
								alignOffset={-5}
							>



<DropdownMenu.Item className="DropdownMenuItem">



Save Page Asâ€¦ <div className="RightSlot">âŒ˜+S</div>



</DropdownMenu.Item>



<DropdownMenu.Item className="DropdownMenuItem">



Create Shortcutâ€¦



</DropdownMenu.Item>



<DropdownMenu.Item className="DropdownMenuItem">



Name Windowâ€¦



</DropdownMenu.Item>



<DropdownMenu.Separator className="DropdownMenu.Separator" />



<DropdownMenu.Item className="DropdownMenuItem">



Developer Tools



</DropdownMenu.Item>



</DropdownMenu.SubContent>



</DropdownMenu.Portal>



</DropdownMenu.Sub>



<DropdownMenu.Separator className="DropdownMenuSeparator" />



<DropdownMenu.CheckboxItem
						className="DropdownMenuCheckboxItem"
						checked={bookmarksChecked}
						onCheckedChange={setBookmarksChecked}
					>



<DropdownMenu.ItemIndicator className="DropdownMenuItemIndicator">



<CheckIcon />



</DropdownMenu.ItemIndicator>



Show Bookmarks <div className="RightSlot">âŒ˜+B</div>



</DropdownMenu.CheckboxItem>



<DropdownMenu.CheckboxItem
						className="DropdownMenuCheckboxItem"
						checked={urlsChecked}
						onCheckedChange={setUrlsChecked}
					>



<DropdownMenu.ItemIndicator className="DropdownMenuItemIndicator">



<CheckIcon />



</DropdownMenu.ItemIndicator>



Show Full URLs



</DropdownMenu.CheckboxItem>



<DropdownMenu.Separator className="DropdownMenuSeparator" />



<DropdownMenu.Label className="DropdownMenuLabel">



People



</DropdownMenu.Label>



<DropdownMenu.RadioGroup value={person} onValueChange={setPerson}>



<DropdownMenu.RadioItem
							className="DropdownMenuRadioItem"
							value="pedro"
						>



<DropdownMenu.ItemIndicator className="DropdownMenuItemIndicator">



<DotFilledIcon />



</DropdownMenu.ItemIndicator>



Pedro Duarte



</DropdownMenu.RadioItem>



<DropdownMenu.RadioItem
							className="DropdownMenuRadioItem"
							value="colm"
						>



<DropdownMenu.ItemIndicator className="DropdownMenuItemIndicator">



<DotFilledIcon />



</DropdownMenu.ItemIndicator>



Colm Tuite



</DropdownMenu.RadioItem>



</DropdownMenu.RadioGroup>



<DropdownMenu.Arrow className="DropdownMenuArrow" />



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);



};



export default DropdownMenuDemo;



Expand code
```

## Features

Can be controlled or uncontrolled.

Supports submenus with configurable reading direction.

Supports items, labels, groups of items.

Supports checkable items (single or multiple) with optional indeterminate state.

Supports modal and non-modal modes.

Customize side, alignment, offsets, collision handling.

Optionally render a pointing arrow.

Focus is fully managed.

Full keyboard navigation.

Typeahead support.

Dismissing and layering behavior is highly customizable.

## Component Reference Links

Version: 2.1.16

Size: [32.12 kB](https://bundlephobia.com/package/@radix-ui/react-dropdown-menu@2.1.16)

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/dropdown-menu/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

[ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/)

## [Installation](#installation)

Install the component from your command line.

```
npm install @radix-ui/react-dropdown-menu
```

## [Anatomy](#anatomy)

Import all parts and piece them together.

```
import { DropdownMenu } from "radix-ui";



export default () => (



<DropdownMenu.Root>



<DropdownMenu.Trigger />



<DropdownMenu.Portal>



<DropdownMenu.Content>



<DropdownMenu.Label />



<DropdownMenu.Item />



<DropdownMenu.Group>



<DropdownMenu.Item />



</DropdownMenu.Group>



<DropdownMenu.CheckboxItem>



<DropdownMenu.ItemIndicator />



</DropdownMenu.CheckboxItem>



<DropdownMenu.RadioGroup>



<DropdownMenu.RadioItem>



<DropdownMenu.ItemIndicator />



</DropdownMenu.RadioItem>



</DropdownMenu.RadioGroup>



<DropdownMenu.Sub>



<DropdownMenu.SubTrigger />



<DropdownMenu.Portal>



<DropdownMenu.SubContent />



</DropdownMenu.Portal>



</DropdownMenu.Sub>



<DropdownMenu.Separator />



<DropdownMenu.Arrow />



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of a dropdown menu.

| Prop | Type | Default |
| --- | --- | --- |
| `defaultOpen` Prop description | `boolean` | No default value |
| `open` Prop description | `boolean` | No default value |
| `onOpenChange` Prop description | `function` See full type | No default value |
| `modal` Prop description | `boolean` | `true` |
| `dir` Prop description | `enum` See full type | No default value |

### [Trigger](#trigger)

The button that toggles the dropdown menu. By default, the `DropdownMenu.Content` will position itself against the trigger.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-disabled]` | Present when disabled |

### [Portal](#portal)

When used, portals the content part into the `body`.

| Prop | Type | Default |
| --- | --- | --- |
| `forceMount` Prop description | `boolean` | No default value |
| `container` Prop description | `HTMLElement` | `document.body` |

### [Content](#content)

The component that pops out when the dropdown menu is open.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `loop` Prop description | `boolean` | `false` |
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
| `[data-orientation]` | `"vertical" | "horizontal"` |

| CSS Variable | Description |
| --- | --- |
| `--radix-dropdown-menu-content-transform-origin` | The `transform-origin` computed from the content and arrow positions/offsets |
| `--radix-dropdown-menu-content-available-width` | The remaining width between the trigger and the boundary edge |
| `--radix-dropdown-menu-content-available-height` | The remaining height between the trigger and the boundary edge |
| `--radix-dropdown-menu-trigger-width` | The width of the trigger |
| `--radix-dropdown-menu-trigger-height` | The height of the trigger |

### [Arrow](#arrow)

An optional arrow element to render alongside the dropdown menu. This can be used to help visually link the trigger with the `DropdownMenu.Content`. Must be rendered inside `DropdownMenu.Content`.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `width` Prop description | `number` | `10` |
| `height` Prop description | `number` | `5` |

### [Item](#item)

The component that contains the dropdown menu items.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `disabled` Prop description | `boolean` | No default value |
| `onSelect` Prop description | `function` See full type | No default value |
| `textValue` Prop description | `string` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-orientation]` | `"vertical" | "horizontal"` |
| `[data-highlighted]` | Present when highlighted |
| `[data-disabled]` | Present when disabled |

### [Group](#group)

Used to group multiple `DropdownMenu.Item`s.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Label](#label)

Used to render a label. It won't be focusable using arrow keys.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [CheckboxItem](#checkboxitem)

An item that can be controlled and rendered like a checkbox.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `checked` Prop description | `boolean | 'indeterminate'` | No default value |
| `onCheckedChange` Prop description | `function` See full type | No default value |
| `disabled` Prop description | `boolean` | No default value |
| `onSelect` Prop description | `function` See full type | No default value |
| `textValue` Prop description | `string` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"checked" | "unchecked" | "indeterminate"` |
| `[data-highlighted]` | Present when highlighted |
| `[data-disabled]` | Present when disabled |

### [RadioGroup](#radiogroup)

Used to group multiple `DropdownMenu.RadioItem`s.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `value` Prop description | `string` | No default value |
| `onValueChange` Prop description | `function` See full type | No default value |

### [RadioItem](#radioitem)

An item that can be controlled and rendered like a radio.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `value*` Prop description | `string` | No default value |
| `disabled` Prop description | `boolean` | No default value |
| `onSelect` Prop description | `function` See full type | No default value |
| `textValue` Prop description | `string` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"checked" | "unchecked" | "indeterminate"` |
| `[data-highlighted]` | Present when highlighted |
| `[data-disabled]` | Present when disabled |

### [ItemIndicator](#itemindicator)

Renders when the parent `DropdownMenu.CheckboxItem` or `DropdownMenu.RadioItem` is checked. You can style this element directly, or you can use it as a wrapper to put an icon into, or both.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `forceMount` Prop description | `boolean` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"checked" | "unchecked" | "indeterminate"` |

### [Separator](#separator)

Used to visually separate items in the dropdown menu.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Sub](#sub)

Contains all the parts of a submenu.

| Prop | Type | Default |
| --- | --- | --- |
| `defaultOpen` Prop description | `boolean` | No default value |
| `open` Prop description | `boolean` | No default value |
| `onOpenChange` Prop description | `function` See full type | No default value |

### [SubTrigger](#subtrigger)

An item that opens a submenu. Must be rendered inside `DropdownMenu.Sub`.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `disabled` Prop description | `boolean` | No default value |
| `textValue` Prop description | `string` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |
| `[data-highlighted]` | Present when highlighted |
| `[data-disabled]` | Present when disabled |

| CSS Variable | Description |
| --- | --- |
| `--radix-dropdown-menu-content-transform-origin` | The `transform-origin` computed from the content and arrow positions/offsets |
| `--radix-dropdown-menu-content-available-width` | The remaining width between the trigger and the boundary edge |
| `--radix-dropdown-menu-content-available-height` | The remaining height between the trigger and the boundary edge |
| `--radix-dropdown-menu-trigger-width` | The width of the trigger |
| `--radix-dropdown-menu-trigger-height` | The height of the trigger |

### [SubContent](#subcontent)

The component that pops out when a submenu is open. Must be rendered inside `DropdownMenu.Sub`.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `loop` Prop description | `boolean` | `false` |
| `onEscapeKeyDown` Prop description | `function` See full type | No default value |
| `onPointerDownOutside` Prop description | `function` See full type | No default value |
| `onFocusOutside` Prop description | `function` See full type | No default value |
| `onInteractOutside` Prop description | `function` See full type | No default value |
| `forceMount` Prop description | `boolean` | No default value |
| `sideOffset` Prop description | `number` | `0` |
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
| `[data-orientation]` | `"vertical" | "horizontal"` |

## [Examples](#examples)

### [With submenus](#with-submenus)

You can create submenus by using `DropdownMenu.Sub` in combination with its parts.

```
<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content>



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Sub>



<DropdownMenu.SubTrigger>Sub menu â†’</DropdownMenu.SubTrigger>



<DropdownMenu.Portal>



<DropdownMenu.SubContent>



<DropdownMenu.Item>Sub menu item</DropdownMenu.Item>



<DropdownMenu.Item>Sub menu item</DropdownMenu.Item>



<DropdownMenu.Arrow />



</DropdownMenu.SubContent>



</DropdownMenu.Portal>



</DropdownMenu.Sub>



<DropdownMenu.Separator />



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>
```

### [With disabled items](#with-disabled-items)

You can add special styles to disabled items via the `data-disabled` attribute.

```
// index.jsx



import { DropdownMenu } from "radix-ui";



import "./styles.css";



export default () => (



<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content>



<DropdownMenu.Item className="DropdownMenuItem" disabled>



â€¦



</DropdownMenu.Item>



<DropdownMenu.Item className="DropdownMenuItem">â€¦</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);
```

```
/* styles.css */



.DropdownMenuItem[data-disabled] {



color: gainsboro;



}
```

### [With separators](#with-separators)

Use the `Separator` part to add a separator between items.

```
<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content>



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>
```

### [With labels](#with-labels)

Use the `Label` part to help label a section.

```
<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content>



<DropdownMenu.Label>Label</DropdownMenu.Label>



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>
```

### [With checkbox items](#with-checkbox-items)

Use the `CheckboxItem` part to add an item that can be checked.

```
import * as React from "react";



import { CheckIcon } from "@radix-ui/react-icons";



import { DropdownMenu } from "radix-ui";



export default () => {



const [checked, setChecked] = React.useState(true);



return (



<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content>



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



<DropdownMenu.Item>â€¦</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.CheckboxItem
						checked={checked}
						onCheckedChange={setChecked}
					>



<DropdownMenu.ItemIndicator>



<CheckIcon />



</DropdownMenu.ItemIndicator>



Checkbox item



</DropdownMenu.CheckboxItem>



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);



};
```

### [With radio items](#with-radio-items)

Use the `RadioGroup` and `RadioItem` parts to add an item that can be checked amongst others.

```
import * as React from "react";



import { CheckIcon } from "@radix-ui/react-icons";



import { DropdownMenu } from "radix-ui";



export default () => {



const [color, setColor] = React.useState("blue");



return (



<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content>



<DropdownMenu.RadioGroup value={color} onValueChange={setColor}>



<DropdownMenu.RadioItem value="red">



<DropdownMenu.ItemIndicator>



<CheckIcon />



</DropdownMenu.ItemIndicator>



Red



</DropdownMenu.RadioItem>



<DropdownMenu.RadioItem value="blue">



<DropdownMenu.ItemIndicator>



<CheckIcon />



</DropdownMenu.ItemIndicator>



Blue



</DropdownMenu.RadioItem>



<DropdownMenu.RadioItem value="green">



<DropdownMenu.ItemIndicator>



<CheckIcon />



</DropdownMenu.ItemIndicator>



Green



</DropdownMenu.RadioItem>



</DropdownMenu.RadioGroup>



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);



};
```

### [With complex items](#with-complex-items)

You can add extra decorative elements in the `Item` parts, such as images.

```
import { DropdownMenu } from "radix-ui";



export default () => (



<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content>



<DropdownMenu.Item>



<img src="â€¦" />



Adolfo Hess



</DropdownMenu.Item>



<DropdownMenu.Item>



<img src="â€¦" />



Miyah Myles



</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);
```

### [Constrain the content/sub-content size](#constrain-the-contentsub-content-size)

You may want to constrain the width of the content (or sub-content) so that it matches the trigger (or sub-trigger) width. You may also want to constrain its height to not exceed the viewport.

We expose several CSS custom properties such as `--radix-dropdown-menu-trigger-width` and `--radix-dropdown-menu-content-available-height` to support this. Use them to constrain the content dimensions.

```
// index.jsx



import { DropdownMenu } from "radix-ui";



import "./styles.css";



export default () => (



<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content className="DropdownMenuContent" sideOffset={5}>



â€¦



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);
```

```
/* styles.css */



.DropdownMenuContent {



width: var(--radix-dropdown-menu-trigger-width);



max-height: var(--radix-dropdown-menu-content-available-height);



}
```

### [Origin-aware animations](#origin-aware-animations)

We expose a CSS custom property `--radix-dropdown-menu-content-transform-origin`. Use it to animate the content from its computed origin based on `side`, `sideOffset`, `align`, `alignOffset` and any collisions.

```
// index.jsx



import { DropdownMenu } from "radix-ui";



import "./styles.css";



export default () => (



<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content className="DropdownMenuContent">



â€¦



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);
```

```
/* styles.css */



.DropdownMenuContent {



transform-origin: var(--radix-dropdown-menu-content-transform-origin);



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



import { DropdownMenu } from "radix-ui";



import "./styles.css";



export default () => (



<DropdownMenu.Root>



<DropdownMenu.Trigger>â€¦</DropdownMenu.Trigger>



<DropdownMenu.Portal>



<DropdownMenu.Content className="DropdownMenuContent">



â€¦



</DropdownMenu.Content>



</DropdownMenu.Portal>



</DropdownMenu.Root>



);
```

```
/* styles.css */



.DropdownMenuContent {



animation-duration: 0.6s;



animation-timing-function: cubic-bezier(0.16, 1, 0.3, 1);



}



.DropdownMenuContent[data-side="top"] {



animation-name: slideUp;



}



.DropdownMenuContent[data-side="bottom"] {



animation-name: slideDown;



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
```

## [Accessibility](#accessibility)

Adheres to the [Menu Button WAI-ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/menu-button/) and uses [roving tabindex](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/#kbd_roving_tabindex) to manage focus movement among menu items.

### [Keyboard Interactions](#keyboard-interactions)

| Key | Description |
| --- | --- |
| `Space` | When focus is on `DropdownMenu.Trigger`, opens the dropdown menu and focuses the first item. When focus is on an item, activates the focused item. |
| `Enter` | When focus is on `DropdownMenu.Trigger`, opens the dropdown menu and focuses the first item. When focus is on an item, activates the focused item. |
| `ArrowDown` | When focus is on `DropdownMenu.Trigger`, opens the dropdown menu. When focus is on an item, moves focus to the next item. |
| `ArrowUp` | When focus is on an item, moves focus to the previous item. |
| `ArrowRight``ArrowLeft` | When focus is on `DropdownMenu.SubTrigger`, opens or closes the submenu depending on reading direction. |
| `Esc` | Closes the dropdown menu and moves focus to `DropdownMenu.Trigger`. |

## [Custom APIs](#custom-apis)

Create your own API by abstracting the primitive parts into your own component.

### [Abstract the arrow and item indicators](#abstract-the-arrow-and-item-indicators)

This example abstracts the `DropdownMenu.Arrow` and `DropdownMenu.ItemIndicator` parts. It also wraps implementation details for `CheckboxItem` and `RadioItem`.

#### Usage

```
import {
	DropdownMenu,
	DropdownMenuTrigger,
	DropdownMenuContent,
	DropdownMenuLabel,
	DropdownMenuItem,
	DropdownMenuGroup,
	DropdownMenuCheckboxItem,
	DropdownMenuRadioGroup,
	DropdownMenuRadioItem,
	DropdownMenuSeparator,
} from "./your-dropdown-menu";



export default () => (



<DropdownMenu>



<DropdownMenuTrigger>DropdownMenu trigger</DropdownMenuTrigger>



<DropdownMenuContent>



<DropdownMenuItem>Item</DropdownMenuItem>



<DropdownMenuLabel>Label</DropdownMenuLabel>



<DropdownMenuGroup>Group</DropdownMenuGroup>



<DropdownMenuCheckboxItem>CheckboxItem</DropdownMenuCheckboxItem>



<DropdownMenuSeparator>Separator</DropdownMenuSeparator>



<DropdownMenuRadioGroup>



<DropdownMenuRadioItem>RadioItem</DropdownMenuRadioItem>



<DropdownMenuRadioItem>RadioItem</DropdownMenuRadioItem>



</DropdownMenuRadioGroup>



</DropdownMenuContent>



</DropdownMenu>



);
```

#### Implementation

```
// your-dropdown-menu.jsx



import * as React from "react";



import { DropdownMenu as DropdownMenuPrimitive } from "radix-ui";



import { CheckIcon, DividerHorizontalIcon } from "@radix-ui/react-icons";



export const DropdownMenu = DropdownMenuPrimitive.Root;



export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger;



export const DropdownMenuContent = React.forwardRef(



({ children, ...props }, forwardedRef) => {



return (



<DropdownMenuPrimitive.Portal>



<DropdownMenuPrimitive.Content {...props} ref={forwardedRef}>



{children}



<DropdownMenuPrimitive.Arrow />



</DropdownMenuPrimitive.Content>



</DropdownMenuPrimitive.Portal>



);



},



);



export const DropdownMenuLabel = DropdownMenuPrimitive.Label;



export const DropdownMenuItem = DropdownMenuPrimitive.Item;



export const DropdownMenuGroup = DropdownMenuPrimitive.Group;



export const DropdownMenuCheckboxItem = React.forwardRef(



({ children, ...props }, forwardedRef) => {



return (



<DropdownMenuPrimitive.CheckboxItem {...props} ref={forwardedRef}>



{children}



<DropdownMenuPrimitive.ItemIndicator>



{props.checked === "indeterminate" && <DividerHorizontalIcon />}



{props.checked === true && <CheckIcon />}



</DropdownMenuPrimitive.ItemIndicator>



</DropdownMenuPrimitive.CheckboxItem>



);



},



);



export const DropdownMenuRadioGroup = DropdownMenuPrimitive.RadioGroup;



export const DropdownMenuRadioItem = React.forwardRef(



({ children, ...props }, forwardedRef) => {



return (



<DropdownMenuPrimitive.RadioItem {...props} ref={forwardedRef}>



{children}



<DropdownMenuPrimitive.ItemIndicator>



<CheckIcon />



</DropdownMenuPrimitive.ItemIndicator>



</DropdownMenuPrimitive.RadioItem>



);



},



);



export const DropdownMenuSeparator = DropdownMenuPrimitive.Separator;
```

#### Quick nav

Previous[Dialog](/primitives/docs/components/dialog)

Next[Form](/primitives/docs/components/form)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/dropdown-menu.mdx "Edit this page on GitHub.")
