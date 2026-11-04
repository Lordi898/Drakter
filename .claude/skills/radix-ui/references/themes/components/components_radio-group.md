Radio Group – Radix Themes

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

# Radio Group

Set of interactive radio buttons where only one can be selected at a time.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/radio-group.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[RadioGroup] Issue)[View in Playground](/themes/playground#radio-group)

DefaultComfortableCompact

```
<RadioGroup.Root defaultValue="1" name="example">



<RadioGroup.Item value="1">Default</RadioGroup.Item>



<RadioGroup.Item value="2">Comfortable</RadioGroup.Item>



<RadioGroup.Item value="3">Compact</RadioGroup.Item>



</RadioGroup.Root>
```

## [API Reference](#api-reference)

This component inherits props from the [Radio Group primitive](/primitives/docs/components/radio-group) and supports [common margin props](/themes/docs/overview/layout#margin-props).

### [Root](#root)

Contains all the parts of a radio group.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"classic" | "surface" | "soft"` | `"surface"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

### [Item](#item)

An item in the group that can be checked.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the radiobutton size.

```
<Flex align="center" gap="2">



<RadioGroup.Root size="1" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root size="2" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root size="3" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style of the radio buttons.

```
<Flex gap="2">



<Flex direction="column" asChild gap="2">



<RadioGroup.Root variant="surface" defaultValue="1">



<RadioGroup.Item value="1" />



<RadioGroup.Item value="2" />



</RadioGroup.Root>



</Flex>



<Flex direction="column" asChild gap="2">



<RadioGroup.Root variant="classic" defaultValue="1">



<RadioGroup.Item value="1" />



<RadioGroup.Item value="2" />



</RadioGroup.Root>



</Flex>



<Flex direction="column" asChild gap="2">



<RadioGroup.Root variant="soft" defaultValue="1">



<RadioGroup.Item value="1" />



<RadioGroup.Item value="2" />



</RadioGroup.Root>



</Flex>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex gap="2">



<RadioGroup.Root color="indigo" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="cyan" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="orange" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="crimson" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

```
<Grid rows="2" gap="2" display="inline-grid" flow="column">



<RadioGroup.Root color="indigo" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="indigo" defaultValue="1" highContrast>



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="cyan" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="cyan" defaultValue="1" highContrast>



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="orange" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="orange" defaultValue="1" highContrast>



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="crimson" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="crimson" defaultValue="1" highContrast>



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="gray" defaultValue="1">



<RadioGroup.Item value="1" />



</RadioGroup.Root>



<RadioGroup.Root color="gray" defaultValue="1" highContrast>



<RadioGroup.Item value="1" />



</RadioGroup.Root>



</Grid>
```

### [Alignment](#alignment)

Composing `RadioGroup.Item` within `Text` automatically centers it with the first line of text.

Default

Compact

Default

Compact

Default

Compact

```
<Flex direction="column" gap="3">



<RadioGroup.Root size="1" defaultValue="1">



<Text as="label" size="2">



<Flex gap="2">



<RadioGroup.Item value="1" /> Default



</Flex>



</Text>



<Text as="label" size="2">



<Flex gap="2">



<RadioGroup.Item value="2" /> Compact



</Flex>



</Text>



</RadioGroup.Root>



<RadioGroup.Root size="2" defaultValue="1">



<Text as="label" size="3">



<Flex gap="2">



<RadioGroup.Item value="1" /> Default



</Flex>



</Text>



<Text as="label" size="3">



<Flex gap="2">



<RadioGroup.Item value="2" /> Compact



</Flex>



</Text>



</RadioGroup.Root>



<RadioGroup.Root size="3" defaultValue="1">



<Text as="label" size="4">



<Flex gap="2">



<RadioGroup.Item value="1" /> Default



</Flex>



</Text>



<Text as="label" size="4">



<Flex gap="2">



<RadioGroup.Item value="2" /> Compact



</Flex>



</Text>



</RadioGroup.Root>



</Flex>
```

It is automatically well-aligned with multi-line text too.

### [Disabled](#disabled)

Use the native `disabled` attribute to create a disabled radiobutton.

OffOn

OffOn

```
<Flex direction="column" gap="2">



<RadioGroup.Root defaultValue="2">



<RadioGroup.Item value="1">Off</RadioGroup.Item>



<RadioGroup.Item value="2">On</RadioGroup.Item>



</RadioGroup.Root>



<RadioGroup.Root defaultValue="2">



<RadioGroup.Item value="1" disabled>



Off



</RadioGroup.Item>



<RadioGroup.Item value="2" disabled>



On



</RadioGroup.Item>



</RadioGroup.Root>



</Flex>
```

#### Quick nav

Previous[Radio](/themes/docs/components/radio)

Next[Radio Cards](/themes/docs/components/radio-cards)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/radio-group.mdx "Edit this page on GitHub.")
