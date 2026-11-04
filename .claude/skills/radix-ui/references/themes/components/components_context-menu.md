Context Menu – Radix Themes

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[ThemesThemes](/)[PrimitivesPrimitives](/primitives)[IconsIcons](/icons)[ColorsColors](/colors)

[Documentation](/themes/docs/overview/getting-started)[Playground](/themes/playground)[Blog](/blog)

#### Overview

[Getting started](/themes/docs/overview/getting-started)[Styling](/themes/docs/overview/styling)[Layout](/themes/docs/overview/layout)[Releases](/themes/docs/overview/releases)[Resources](/themes/docs/overview/resources)

#### Theme

[Overview](/themes/docs/theme/overview)[Color](/themes/docs/theme/color)[Dark mode](/themes/docs/theme/dark-mode)[Typography](/themes/docs/theme/typography)[Spacing](/themes/docs/theme/spacing)[Breakpoints](/themes/docs/theme/breakpoints)[Radius](/themes/docs/theme/radius)[Shadows](/themes/docs/theme/shadows)[Cursors](/themes/docs/theme/cursors)

#### Layout

[Box](/themes/docs/components/box)[Flex](/themes/docs/components/flex)[Grid](/themes/docs/components/grid)[Container](/themes/docs/components/container)[Section](/themes/docs/components/section)

#### Typography

[Text](/themes/docs/components/text)[Heading](/themes/docs/components/heading)[Blockquote](/themes/docs/components/blockquote)[Code](/themes/docs/components/code)[Em](/themes/docs/components/em)[Kbd](/themes/docs/components/kbd)[Link](/themes/docs/components/link)[Quote](/themes/docs/components/quote)[Strong](/themes/docs/components/strong)

#### Components

[Alert Dialog](/themes/docs/components/alert-dialog)[Aspect Ratio](/themes/docs/components/aspect-ratio)[Avatar](/themes/docs/components/avatar)[Badge](/themes/docs/components/badge)[Button](/themes/docs/components/button)[Callout](/themes/docs/components/callout)[Card](/themes/docs/components/card)[Checkbox](/themes/docs/components/checkbox)[Checkbox Group](/themes/docs/components/checkbox-group)[Checkbox Cards](/themes/docs/components/checkbox-cards)[Context Menu](/themes/docs/components/context-menu)[Data List](/themes/docs/components/data-list)[Dialog](/themes/docs/components/dialog)[Dropdown Menu](/themes/docs/components/dropdown-menu)[Hover Card](/themes/docs/components/hover-card)[Icon Button](/themes/docs/components/icon-button)[Inset](/themes/docs/components/inset)[Popover](/themes/docs/components/popover)[Progress](/themes/docs/components/progress)[Radio](/themes/docs/components/radio)[Radio Group](/themes/docs/components/radio-group)[Radio Cards](/themes/docs/components/radio-cards)[Scroll Area](/themes/docs/components/scroll-area)[Segmented Control](/themes/docs/components/segmented-control)[Select](/themes/docs/components/select)[Separator](/themes/docs/components/separator)[Skeleton](/themes/docs/components/skeleton)[Slider](/themes/docs/components/slider)[Spinner](/themes/docs/components/spinner)[Switch](/themes/docs/components/switch)[Table](/themes/docs/components/table)[Tabs](/themes/docs/components/tabs)[Tab Nav](/themes/docs/components/tab-nav)[Text Area](/themes/docs/components/text-area)[Text Field](/themes/docs/components/text-field)[Tooltip](/themes/docs/components/tooltip)

#### Utilities

[Accessible Icon](/themes/docs/components/accessible-icon)[Portal](/themes/docs/components/portal)[Reset](/themes/docs/components/reset)[Slot](/themes/docs/components/slot)[Theme](/themes/docs/components/theme)[Visually Hidden](/themes/docs/components/visually-hidden)

Components

# Context Menu

Menu representing a set of actions, displayed at the point of right click or long press.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/context-menu.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[ContextMenu] Issue)[View in Playground](/themes/playground#context-menu)

Right-click here

```
<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone style={{ height: 150 }} />



</ContextMenu.Trigger>



<ContextMenu.Content>



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Sub>



<ContextMenu.SubTrigger>More</ContextMenu.SubTrigger>



<ContextMenu.SubContent>



<ContextMenu.Item>Move to project…</ContextMenu.Item>



<ContextMenu.Item>Move to folder…</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item>Advanced options…</ContextMenu.Item>



</ContextMenu.SubContent>



</ContextMenu.Sub>



<ContextMenu.Separator />



<ContextMenu.Item>Share</ContextMenu.Item>



<ContextMenu.Item>Add to favorites</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>
```

## [API Reference](#api-reference)

This component inherits props from the [Context Menu primitive](/primitives/docs/components/context-menu).

### [Root](#root)

Contains all the parts of a context menu.

### [Trigger](#trigger)

Wraps the element that will open the context menu.

### [Content](#content)

The component that pops out when the context menu is open.

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2">` | `"2"` |
| `variant` Prop description | `"solid" | "soft"` | `"solid"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

### [Label](#label)

Used to render a label. It won't be focusable using arrow keys.

### [Item](#item)

The component that contains the context menu items.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `color` Prop description | `enum` See full type | No default value |
| `shortcut` Prop description | `string` | No default value |

### [Group](#group)

Used to group multiple `Item` parts.

### [RadioGroup](#radiogroup)

Used to group multiple `RadioItem` parts.

### [RadioItem](#radioitem)

An item that can be controlled and rendered like a radio.

| Prop | Type | Default |
| --- | --- | --- |
| `color` Prop description | `enum` See full type | No default value |

### [CheckboxItem](#checkboxitem)

An item that can be controlled and rendered like a checkbox.

| Prop | Type | Default |
| --- | --- | --- |
| `color` Prop description | `enum` See full type | No default value |
| `shortcut` Prop description | `string` | No default value |

### [Sub](#sub)

Contains all the parts of a submenu.

### [SubTrigger](#subtrigger)

An item that opens a submenu. Must be rendered inside `ContextMenu.Sub`.

### [SubContent](#subcontent)

The component that pops out when a submenu is open. Must be rendered inside `ContextMenu.Sub`.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

Size oneRight-click here

Size twoRight-click here

```
<Grid columns="2" gap="3">



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Size one" />



</ContextMenu.Trigger>



<ContextMenu.Content size="1">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Size two" />



</ContextMenu.Trigger>



<ContextMenu.Content size="2">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



</Grid>
```

### [Variant](#variant)

Use the `variant` prop to customize the visual style of the context menu.

SolidRight-click here

SoftRight-click here

```
<Grid columns="2" gap="3">



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Solid" />



</ContextMenu.Trigger>



<ContextMenu.Content variant="solid">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Soft" />



</ContextMenu.Trigger>



<ContextMenu.Content variant="soft">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



</Grid>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color). You can also pass `color` to a specific item to override for semantic reasons (i.e. a destructive action).

IndigoRight-click here

CyanRight-click here

OrangeRight-click here

CrimsonRight-click here

```
<Grid columns="2" gap="3">



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Indigo" />



</ContextMenu.Trigger>



<ContextMenu.Content color="indigo">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Cyan" />



</ContextMenu.Trigger>



<ContextMenu.Content color="cyan">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Orange" />



</ContextMenu.Trigger>



<ContextMenu.Content color="orange">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Crimson" />



</ContextMenu.Trigger>



<ContextMenu.Content color="crimson">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



</Grid>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

StandardRight-click here

High-contrastRight-click here

```
<Grid columns="2" gap="3">



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="Standard" />



</ContextMenu.Trigger>



<ContextMenu.Content color="gray">



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



<ContextMenu.Root>



<ContextMenu.Trigger>



<RightClickZone title="High-contrast" />



</ContextMenu.Trigger>



<ContextMenu.Content color="gray" highContrast>



<ContextMenu.Item shortcut="⌘ E">Edit</ContextMenu.Item>



<ContextMenu.Item shortcut="⌘ D">Duplicate</ContextMenu.Item>



<ContextMenu.Separator />



<ContextMenu.Item shortcut="⌘ N">Archive</ContextMenu.Item>



</ContextMenu.Content>



</ContextMenu.Root>



</Grid>
```

#### Quick nav

Previous[Checkbox Cards](/themes/docs/components/checkbox-cards)

Next[Data List](/themes/docs/components/data-list)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/context-menu.mdx "Edit this page on GitHub.")