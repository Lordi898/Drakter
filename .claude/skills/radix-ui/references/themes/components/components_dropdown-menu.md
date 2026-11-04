Dropdown Menu – Radix Themes

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

# Dropdown Menu

Menu representing a set of actions, triggered by a button.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/dropdown-menu.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[DropdownMenu] Issue)[View in Playground](/themes/playground#dropdown-menu)

Options

```
<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="soft">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content>



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



<DropdownMenu.Sub>



<DropdownMenu.SubTrigger>More</DropdownMenu.SubTrigger>



<DropdownMenu.SubContent>



<DropdownMenu.Item>Move to project…</DropdownMenu.Item>



<DropdownMenu.Item>Move to folder…</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item>Advanced options…</DropdownMenu.Item>



</DropdownMenu.SubContent>



</DropdownMenu.Sub>



<DropdownMenu.Separator />



<DropdownMenu.Item>Share</DropdownMenu.Item>



<DropdownMenu.Item>Add to favorites</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>
```

## [API Reference](#api-reference)

This component inherits props from the [Dropdown Menu primitive](/primitives/docs/components/dropdown-menu).

### [Root](#root)

Contains all the parts of a dropdown menu.

### [Trigger](#trigger)

Wraps the control that will open the dropdown menu.

### [Trigger Icon](#trigger-icon)

An optional icon part.

### [Content](#content)

The component that pops out when the dropdown menu is open.

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2">` | `"2"` |
| `variant` Prop description | `"solid" | "soft"` | `"solid"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

### [Label](#label)

Used to render a label. It won't be focusable using arrow keys.

### [Item](#item)

The component that contains the dropdown menu items.

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

An item that opens a submenu. Must be rendered inside `DropdownMenu.Sub`.

### [SubContent](#subcontent)

The component that pops out when a submenu is open. Must be rendered inside `DropdownMenu.Sub`.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

OptionsOptions

```
<Flex gap="3" align="center">



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="soft" size="1">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content size="1">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="soft" size="2">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content size="2">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to customize the visual style of the dropdown menu.

OptionsOptions

```
<Flex gap="3" align="center">



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="solid">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content variant="solid">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="soft">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content variant="soft">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ ⌫" color="red">



Delete



</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color). You can also pass `color` to a specific item to override for semantic reasons (ie. destruction action).

OptionsOptionsOptionsOptions

```
<Flex gap="3">



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="soft" color="indigo">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content variant="soft" color="indigo">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="soft" color="cyan">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content variant="soft" color="cyan">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="soft" color="orange">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content variant="soft" color="orange">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button variant="soft" color="crimson">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content variant="soft" color="crimson">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

OptionsOptionsOptionsOptions

```
<Grid columns="2" gap="3" display="inline-grid">



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button color="gray">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content color="gray">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button color="gray" highContrast>



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content color="gray" highContrast>



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button color="gray" variant="soft">



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content color="gray" variant="soft">



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



<DropdownMenu.Root>



<DropdownMenu.Trigger>



<Button color="gray" variant="soft" highContrast>



Options



<DropdownMenu.TriggerIcon />



</Button>



</DropdownMenu.Trigger>



<DropdownMenu.Content color="gray" variant="soft" highContrast>



<DropdownMenu.Item shortcut="⌘ E">Edit</DropdownMenu.Item>



<DropdownMenu.Item shortcut="⌘ D">Duplicate</DropdownMenu.Item>



<DropdownMenu.Separator />



<DropdownMenu.Item shortcut="⌘ N">Archive</DropdownMenu.Item>



</DropdownMenu.Content>



</DropdownMenu.Root>



</Grid>
```

#### Quick nav

Previous[Dialog](/themes/docs/components/dialog)

Next[Hover Card](/themes/docs/components/hover-card)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/dropdown-menu.mdx "Edit this page on GitHub.")