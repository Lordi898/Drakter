Tabs â€“ Radix Primitives

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

# Tabs

A set of layered sections of contentâ€”known as tab panelsâ€”that are displayed
one at a time.

AccountPassword

Make changes to your account here. Click save when you're done.

NameUsername

Save changes

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { Tabs } from "radix-ui";



import "./styles.css";



const TabsDemo = () => (



<Tabs.Root className="TabsRoot" defaultValue="tab1">



<Tabs.List className="TabsList" aria-label="Manage your account">



<Tabs.Trigger className="TabsTrigger" value="tab1">



Account



</Tabs.Trigger>



<Tabs.Trigger className="TabsTrigger" value="tab2">



Password



</Tabs.Trigger>



</Tabs.List>



<Tabs.Content className="TabsContent" value="tab1">



<p className="Text">



Make changes to your account here. Click save when you're done.



</p>



<fieldset className="Fieldset">



<label className="Label" htmlFor="name">



Name



</label>



<input className="Input" id="name" defaultValue="Pedro Duarte" />



</fieldset>



<fieldset className="Fieldset">



<label className="Label" htmlFor="username">



Username



</label>



<input className="Input" id="username" defaultValue="@peduarte" />



</fieldset>



<div
				style={{ display: "flex", marginTop: 20, justifyContent: "flex-end" }}
			>



<button className="Button green">Save changes</button>



</div>



</Tabs.Content>



<Tabs.Content className="TabsContent" value="tab2">



<p className="Text">



Change your password here. After saving, you'll be logged out.



</p>



<fieldset className="Fieldset">



<label className="Label" htmlFor="currentPassword">



Current password



</label>



<input className="Input" id="currentPassword" type="password" />



</fieldset>



<fieldset className="Fieldset">



<label className="Label" htmlFor="newPassword">



New password



</label>



<input className="Input" id="newPassword" type="password" />



</fieldset>



<fieldset className="Fieldset">



<label className="Label" htmlFor="confirmPassword">



Confirm password



</label>



<input className="Input" id="confirmPassword" type="password" />



</fieldset>



<div
				style={{ display: "flex", marginTop: 20, justifyContent: "flex-end" }}
			>



<button className="Button green">Change password</button>



</div>



</Tabs.Content>



</Tabs.Root>



);



export default TabsDemo;



Expand code
```

## Features

Can be controlled or uncontrolled.

Supports horizontal/vertical orientation.

Supports automatic/manual activation.

Full keyboard navigation.

## Component Reference Links

Version: 1.1.13

Size: [9.69 kB](https://bundlephobia.com/package/@radix-ui/react-tabs@1.1.13)

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/tabs/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

[ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs)

## [Installation](#installation)

Install the component from your command line.

```
npm install @radix-ui/react-tabs
```

## [Anatomy](#anatomy)

Import all parts and piece them together.

```
import { Tabs } from "radix-ui";



export default () => (



<Tabs.Root>



<Tabs.List>



<Tabs.Trigger />



</Tabs.List>



<Tabs.Content />



</Tabs.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the tabs component parts.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `defaultValue` Prop description | `string` | No default value |
| `value` Prop description | `string` | No default value |
| `onValueChange` Prop description | `function` See full type | No default value |
| `orientation` Prop description | `enum` See full type | `"horizontal"` |
| `dir` Prop description | `enum` See full type | No default value |
| `activationMode` Prop description | `enum` See full type | `"automatic"` |

| Data attribute | Values |
| --- | --- |
| `[data-orientation]` | `"vertical" | "horizontal"` |

### [List](#list)

Contains the triggers that are aligned along the edge of the active content.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `loop` Prop description | `boolean` | `true` |

| Data attribute | Values |
| --- | --- |
| `[data-orientation]` | `"vertical" | "horizontal"` |

### [Trigger](#trigger)

The button that activates its associated content.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `value*` Prop description | `string` | No default value |
| `disabled` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"active" | "inactive"` |
| `[data-disabled]` | Present when disabled |
| `[data-orientation]` | `"vertical" | "horizontal"` |

### [Content](#content)

Contains the content associated with each trigger.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `value*` Prop description | `string` | No default value |
| `forceMount` Prop description | `boolean` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"active" | "inactive"` |
| `[data-orientation]` | `"vertical" | "horizontal"` |

## [Examples](#examples)

### [Vertical](#vertical)

You can create vertical tabs by using the `orientation` prop.

```
import { Tabs } from "radix-ui";



export default () => (



<Tabs.Root defaultValue="tab1" orientation="vertical">



<Tabs.List aria-label="tabs example">



<Tabs.Trigger value="tab1">One</Tabs.Trigger>



<Tabs.Trigger value="tab2">Two</Tabs.Trigger>



<Tabs.Trigger value="tab3">Three</Tabs.Trigger>



</Tabs.List>



<Tabs.Content value="tab1">Tab one content</Tabs.Content>



<Tabs.Content value="tab2">Tab two content</Tabs.Content>



<Tabs.Content value="tab3">Tab three content</Tabs.Content>



</Tabs.Root>



);
```

## [Accessibility](#accessibility)

Adheres to the [Tabs WAI-ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs).

### [Keyboard Interactions](#keyboard-interactions)

| Key | Description |
| --- | --- |
| `Tab` | When focus moves onto the tabs, focuses the active trigger. When a trigger is focused, moves focus to the active content. |
| `ArrowDown` | Moves focus to the next trigger depending on `orientation` and activates its associated content. |
| `ArrowRight` | Moves focus to the next trigger depending on `orientation` and activates its associated content. |
| `ArrowUp` | Moves focus to the previous trigger depending on `orientation` and activates its associated content. |
| `ArrowLeft` | Moves focus to the previous trigger depending on `orientation` and activates its associated content. |
| `Home` | Moves focus to the first trigger and activates its associated content. |
| `End` | Moves focus to the last trigger and activates its associated content. |

#### Quick nav

Previous[Switch](/primitives/docs/components/switch)

Next[Toast](/primitives/docs/components/toast)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/tabs.mdx "Edit this page on GitHub.")
