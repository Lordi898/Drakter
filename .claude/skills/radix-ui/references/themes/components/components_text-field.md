Text Field – Radix Themes

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

# Text Field

Captures user input with an optional slot for buttons and icons.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/text-field.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[TextField] Issue)[View in Playground](/themes/playground#text-field)

```
<TextField.Root placeholder="Search the docs…">



<TextField.Slot>



<MagnifyingGlassIcon height="16" width="16" />



</TextField.Slot>



</TextField.Root>
```

## [API Reference](#api-reference)

### [Root](#root)

Groups Slot and Input parts. This component is based on the `div` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"classic" | "surface" | "soft"` | `"surface"` |
| `color` Prop description | `enum` See full type | No default value |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |

### [Slot](#slot)

Contains icons or buttons associated with an Input.

| Prop | Type | Default |
| --- | --- | --- |
| `side` | `"left" | "right"` | No default value |
| `color` Prop description | `enum` See full type | No default value |
| `gap` | `Responsive<enum | string>` See full type | No default value |
| `px` | `Responsive<enum | string>` See full type | No default value |
| `pl` | `Responsive<enum | string>` See full type | No default value |
| `pr` | `Responsive<enum | string>` See full type | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

```
<Flex direction="column" gap="3">



<Box maxWidth="200px">



<TextField.Root size="1" placeholder="Search the docs…" />



</Box>



<Box maxWidth="250px">



<TextField.Root size="2" placeholder="Search the docs…" />



</Box>



<Box maxWidth="300px">



<TextField.Root size="3" placeholder="Search the docs…" />



</Box>



</Flex>
```

Use matching component sizes when composing Text Field with buttons. However, don’t use size 1 inputs with buttons—at this size, there is not enough vertical space to nest other interactive elements.

```
<Flex direction="column" gap="3" maxWidth="400px">



<Box maxWidth="200px">



<TextField.Root placeholder="Search the docs…" size="1">



<TextField.Slot>



<MagnifyingGlassIcon height="16" width="16" />



</TextField.Slot>



</TextField.Root>



</Box>



<Box maxWidth="250px">



<TextField.Root placeholder="Search the docs…" size="2">



<TextField.Slot>



<MagnifyingGlassIcon height="16" width="16" />



</TextField.Slot>



<TextField.Slot>



<IconButton size="1" variant="ghost">



<DotsHorizontalIcon height="14" width="14" />



</IconButton>



</TextField.Slot>



</TextField.Root>



</Box>



<Box maxWidth="300px">



<TextField.Root placeholder="Search the docs…" size="3">



<TextField.Slot>



<MagnifyingGlassIcon height="16" width="16" />



</TextField.Slot>



<TextField.Slot pr="3">



<IconButton size="2" variant="ghost">



<DotsHorizontalIcon height="16" width="16" />



</IconButton>



</TextField.Slot>



</TextField.Root>



</Box>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

```
<Flex direction="column" gap="3" maxWidth="250px">



<TextField.Root variant="surface" placeholder="Search the docs…" />



<TextField.Root variant="classic" placeholder="Search the docs…" />



<TextField.Root variant="soft" placeholder="Search the docs…" />



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex direction="column" gap="3" maxWidth="250px">



<TextField.Root
		color="indigo"
		variant="soft"
		placeholder="Search the docs…"
	/>



<TextField.Root color="green" variant="soft" placeholder="Search the docs…" />



<TextField.Root color="red" variant="soft" placeholder="Search the docs…" />



</Flex>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

```
<Flex direction="column" gap="3" maxWidth="250px">



<TextField.Root radius="none" placeholder="Search the docs…" />



<TextField.Root radius="large" placeholder="Search the docs…" />



<TextField.Root radius="full" placeholder="Search the docs…" />



</Flex>
```

#### Quick nav

Previous[Text Area](/themes/docs/components/text-area)

Next[Tooltip](/themes/docs/components/tooltip)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/text-field.mdx "Edit this page on GitHub.")
