Radio Cards – Radix Themes

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

# Radio Cards

Set of interactive cards where only one can be selected at a time.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/radio-cards.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[RadioCards] Issue)[View in Playground](/themes/playground#radio-cards)

8-core CPU32 GB RAM

6-core CPU24 GB RAM

4-core CPU16 GB RAM

```
<Box maxWidth="600px">



<RadioCards.Root defaultValue="1" columns={{ initial: "1", sm: "3" }}>



<RadioCards.Item value="1">



<Flex direction="column" width="100%">



<Text weight="bold">8-core CPU</Text>



<Text>32 GB RAM</Text>



</Flex>



</RadioCards.Item>



<RadioCards.Item value="2">



<Flex direction="column" width="100%">



<Text weight="bold">6-core CPU</Text>



<Text>24 GB RAM</Text>



</Flex>



</RadioCards.Item>



<RadioCards.Item value="3">



<Flex direction="column" width="100%">



<Text weight="bold">4-core CPU</Text>



<Text>16 GB RAM</Text>



</Flex>



</RadioCards.Item>



</RadioCards.Root>



</Box>
```

## [API Reference](#api-reference)

This component inherits props from the [Radio Group primitive](/primitives/docs/components/radio-group) and supports [common margin props](/themes/docs/overview/layout#margin-props).

### [Root](#root)

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"surface" | "classic"` | `"surface"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `columns` | `Responsive<enum | string>` See full type | `"repeat(auto-fit, minmax(160px, 1fr))"` |
| `gap` | `Responsive<enum | string>` See full type | `"4"` |

### [Item](#item)

An item in the group that can be checked.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

8-core CPU

8-core CPU

8-core CPU

```
<Flex align="center" gap="3">



<RadioCards.Root size="1">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root size="2">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root size="3">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

8-core CPU

8-core CPU

```
<Flex direction="column" gap="3" maxWidth="200px">



<RadioCards.Root variant="surface">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root variant="classic">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

8-core CPU

8-core CPU

8-core CPU

8-core CPU

```
<Flex direction="column" gap="3" maxWidth="200px">



<RadioCards.Root defaultValue="1" color="indigo">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="cyan">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="orange">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="crimson">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

8-core CPU

8-core CPU

8-core CPU

8-core CPU

8-core CPU

8-core CPU

8-core CPU

8-core CPU

```
<Grid columns="2" gap="3" display="inline-grid">



<RadioCards.Root defaultValue="1" color="indigo">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="indigo" highContrast>



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="cyan">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="cyan" highContrast>



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="orange">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="orange" highContrast>



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="crimson">



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root defaultValue="1" color="crimson" highContrast>



<RadioCards.Item value="1">8-core CPU</RadioCards.Item>



</RadioCards.Root>



</Grid>
```

### [Disabled](#disabled)

OffOn

OffOn

```
<Flex direction="column" gap="4" maxWidth="450px">



<RadioCards.Root columns="2" defaultValue="2">



<RadioCards.Item value="1">Off</RadioCards.Item>



<RadioCards.Item value="2">On</RadioCards.Item>



</RadioCards.Root>



<RadioCards.Root columns="2" defaultValue="2">



<RadioCards.Item value="1" disabled>



Off



</RadioCards.Item>



<RadioCards.Item value="2" disabled>



On



</RadioCards.Item>



</RadioCards.Root>



</Flex>
```

#### Quick nav

Previous[Radio Group](/themes/docs/components/radio-group)

Next[Scroll Area](/themes/docs/components/scroll-area)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/radio-cards.mdx "Edit this page on GitHub.")