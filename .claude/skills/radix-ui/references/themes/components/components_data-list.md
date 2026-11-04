Data List – Radix Themes

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

# Data List

Displays metadata as a list of key-value pairs.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/data-list.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[DataList] Issue)[View in Playground](/themes/playground#data-list)

Status
:   Authorized

ID
:   `u_2J89JSA4GJ`

Name
:   Vlad Moroz

Email
:   [vlad@workos.com](mailto:vlad@workos.com)

Company
:   [WorkOS](https://workos.com)

```
<DataList.Root>



<DataList.Item align="center">



<DataList.Label minWidth="88px">Status</DataList.Label>



<DataList.Value>



<Badge color="jade" variant="soft" radius="full">



Authorized



</Badge>



</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">ID</DataList.Label>



<DataList.Value>



<Flex align="center" gap="2">



<Code variant="ghost">u_2J89JSA4GJ</Code>



<IconButton
					size="1"
					aria-label="Copy value"
					color="gray"
					variant="ghost"
				>



<CopyIcon />



</IconButton>



</Flex>



</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Name</DataList.Label>



<DataList.Value>Vlad Moroz</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Email</DataList.Label>



<DataList.Value>



<Link href="mailto:vlad@workos.com">vlad@workos.com</Link>



</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Company</DataList.Label>



<DataList.Value>



<Link target="_blank" href="https://workos.com">



WorkOS



</Link>



</DataList.Value>



</DataList.Item>



</DataList.Root>
```

## [API Reference](#api-reference)

This component is based on the `dl` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

### [Root](#root)

Contains all the parts of the data list.

| Prop | Type | Default |
| --- | --- | --- |
| `orientation` | `Responsive<"horizontal" | "vertical">` | `"horizontal"` |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `trim` Prop description | `Responsive<"normal" | "start" | "end" | "both">` | No default value |

### [Item](#item)

Wraps a key-value pair.

| Prop | Type | Default |
| --- | --- | --- |
| `align` | `Responsive<enum>` See full type | No default value |

### [Label](#label)

Contains the key of the key-value pair.

| Prop | Type | Default |
| --- | --- | --- |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | No default value |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

### [Value](#value)

Contains the value of the key-value pair.

## [Examples](#examples)

### [Orientation](#orientation)

Use the `orientation` prop to change the way the data list is layed-out.

Name
:   Vlad Moroz

Email
:   [vlad@workos.com](mailto:vlad@workos.com)

Company
:   [WorkOS](https://workos.com)

```
<DataList.Root orientation={{ initial: "vertical", sm: "horizontal" }}>



<DataList.Item>



<DataList.Label minWidth="88px">Name</DataList.Label>



<DataList.Value>Vlad Moroz</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Email</DataList.Label>



<DataList.Value>



<Link href="mailto:vlad@workos.com">vlad@workos.com</Link>



</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Company</DataList.Label>



<DataList.Value>



<Link target="_blank" href="https://workos.com">



WorkOS



</Link>



</DataList.Value>



</DataList.Item>



</DataList.Root>
```

### [Size](#size)

Use the `size` prop to change the size of the data list.

Name
:   Vlad Moroz

Email
:   [vlad@workos.com](mailto:vlad@workos.com)

Company
:   [WorkOS](https://workos.com)

Name
:   Vlad Moroz

Email
:   [vlad@workos.com](mailto:vlad@workos.com)

Company
:   [WorkOS](https://workos.com)

Name
:   Vlad Moroz

Email
:   [vlad@workos.com](mailto:vlad@workos.com)

Company
:   [WorkOS](https://workos.com)

```
<Flex direction="column" gap="6">



<DataList.Root size="1">



<DataList.Item>



<DataList.Label minWidth="88px">Name</DataList.Label>



<DataList.Value>Vlad Moroz</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Email</DataList.Label>



<DataList.Value>



<Link href="mailto:vlad@workos.com">vlad@workos.com</Link>



</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Company</DataList.Label>



<DataList.Value>



<Link target="_blank" href="https://workos.com">



WorkOS



</Link>



</DataList.Value>



</DataList.Item>



</DataList.Root>



<DataList.Root size="2">



<DataList.Item>



<DataList.Label minWidth="88px">Name</DataList.Label>



<DataList.Value>Vlad Moroz</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Email</DataList.Label>



<DataList.Value>



<Link href="mailto:vlad@workos.com">vlad@workos.com</Link>



</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Company</DataList.Label>



<DataList.Value>



<Link target="_blank" href="https://workos.com">



WorkOS



</Link>



</DataList.Value>



</DataList.Item>



</DataList.Root>



<DataList.Root size="3">



<DataList.Item>



<DataList.Label minWidth="88px">Name</DataList.Label>



<DataList.Value>Vlad Moroz</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Email</DataList.Label>



<DataList.Value>



<Link href="mailto:vlad@workos.com">vlad@workos.com</Link>



</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label minWidth="88px">Company</DataList.Label>



<DataList.Value>



<Link target="_blank" href="https://workos.com">



WorkOS



</Link>



</DataList.Value>



</DataList.Item>



</DataList.Root>



</Flex>
```

### [Color](#color)

Use the `color` prop on the Label part to assign a specific [color](/themes/docs/theme/color).

Name
:   Indigo

Name
:   Cyan

Name
:   Orange

Name
:   Crimson

```
<DataList.Root orientation="vertical">



<DataList.Item>



<DataList.Label color="indigo">Name</DataList.Label>



<DataList.Value>Indigo</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="cyan">Name</DataList.Label>



<DataList.Value>Cyan</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="orange">Name</DataList.Label>



<DataList.Value>Orange</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="crimson">Name</DataList.Label>



<DataList.Value>Crimson</DataList.Value>



</DataList.Item>



</DataList.Root>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop increase color contrast with the background.

Name
:   Indigo

Name
:   Cyan

Name
:   Orange

Name
:   Crimson

Name
:   Indigo

Name
:   Cyan

Name
:   Orange

Name
:   Crimson

```
<Flex gap="9">



<DataList.Root orientation="vertical">



<DataList.Item>



<DataList.Label color="indigo">Name</DataList.Label>



<DataList.Value>Indigo</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="cyan">Name</DataList.Label>



<DataList.Value>Cyan</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="orange">Name</DataList.Label>



<DataList.Value>Orange</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="crimson">Name</DataList.Label>



<DataList.Value>Crimson</DataList.Value>



</DataList.Item>



</DataList.Root>



<DataList.Root orientation="vertical">



<DataList.Item>



<DataList.Label color="indigo" highContrast>



Name



</DataList.Label>



<DataList.Value>Indigo</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="cyan" highContrast>



Name



</DataList.Label>



<DataList.Value>Cyan</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="orange" highContrast>



Name



</DataList.Label>



<DataList.Value>Orange</DataList.Value>



</DataList.Item>



<DataList.Item>



<DataList.Label color="crimson" highContrast>



Name



</DataList.Label>



<DataList.Value>Crimson</DataList.Value>



</DataList.Item>



</DataList.Root>



</Flex>
```

#### Quick nav

Previous[Context Menu](/themes/docs/components/context-menu)

Next[Dialog](/themes/docs/components/dialog)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/data-list.mdx "Edit this page on GitHub.")
