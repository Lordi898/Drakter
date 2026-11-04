Checkbox Group – Radix Themes

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

# Checkbox Group

Set of interactive buttons where multiple options can be selected at a time.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/checkbox-group.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[CheckboxGroup] Issue)[View in Playground](/themes/playground#checkbox-group)

FunSeriousSmart

```
<CheckboxGroup.Root defaultValue={["1"]} name="example">



<CheckboxGroup.Item value="1">Fun</CheckboxGroup.Item>



<CheckboxGroup.Item value="2">Serious</CheckboxGroup.Item>



<CheckboxGroup.Item value="3">Smart</CheckboxGroup.Item>



</CheckboxGroup.Root>
```

## [API Reference](#api-reference)

This component is based on the `div` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

### [Root](#root)

Contains all the parts of a checkbox group.

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

Use the `size` prop to control the checkbox size.

```
<Flex align="center" gap="2">



<CheckboxGroup.Root size="1" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root size="2" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root size="3" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style of the checkboxes.

```
<Flex gap="2">



<Flex direction="column" asChild gap="2">



<CheckboxGroup.Root variant="surface" defaultValue="1">



<CheckboxGroup.Item value="1" />



<CheckboxGroup.Item value="2" />



</CheckboxGroup.Root>



</Flex>



<Flex direction="column" asChild gap="2">



<CheckboxGroup.Root variant="classic" defaultValue="1">



<CheckboxGroup.Item value="1" />



<CheckboxGroup.Item value="2" />



</CheckboxGroup.Root>



</Flex>



<Flex direction="column" asChild gap="2">



<CheckboxGroup.Root variant="soft" defaultValue="1">



<CheckboxGroup.Item value="1" />



<CheckboxGroup.Item value="2" />



</CheckboxGroup.Root>



</Flex>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex gap="2">



<CheckboxGroup.Root color="indigo" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="cyan" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="orange" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="crimson" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

```
<Grid rows="2" gap="2" display="inline-grid" flow="column">



<CheckboxGroup.Root color="indigo" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="indigo" defaultValue="1" highContrast>



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="cyan" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="cyan" defaultValue="1" highContrast>



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="orange" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="orange" defaultValue="1" highContrast>



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="crimson" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="crimson" defaultValue="1" highContrast>



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="gray" defaultValue="1">



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



<CheckboxGroup.Root color="gray" defaultValue="1" highContrast>



<CheckboxGroup.Item value="1" />



</CheckboxGroup.Root>



</Grid>
```

### [Alignment](#alignment)

Composing `CheckboxGroup.Item` within `Text` automatically centers it with the first line of text.

Default

Compact

Default

Compact

Default

Compact

```
<Flex direction="column" gap="3">



<CheckboxGroup.Root size="1" defaultValue="1">



<Text as="label" size="2">



<Flex gap="2">



<CheckboxGroup.Item value="1" /> Default



</Flex>



</Text>



<Text as="label" size="2">



<Flex gap="2">



<CheckboxGroup.Item value="2" /> Compact



</Flex>



</Text>



</CheckboxGroup.Root>



<CheckboxGroup.Root size="2" defaultValue="1">



<Text as="label" size="3">



<Flex gap="2">



<CheckboxGroup.Item value="1" /> Default



</Flex>



</Text>



<Text as="label" size="3">



<Flex gap="2">



<CheckboxGroup.Item value="2" /> Compact



</Flex>



</Text>



</CheckboxGroup.Root>



<CheckboxGroup.Root size="3" defaultValue="1">



<Text as="label" size="4">



<Flex gap="2">



<CheckboxGroup.Item value="1" /> Default



</Flex>



</Text>



<Text as="label" size="4">



<Flex gap="2">



<CheckboxGroup.Item value="2" /> Compact



</Flex>



</Text>



</CheckboxGroup.Root>



</Flex>
```

It is automatically well-aligned with multi-line text too.

### [Disabled](#disabled)

Use the native `disabled` attribute to create a disabled checkbox.

OffOn

OffOn

```
<Flex direction="column" gap="2">



<CheckboxGroup.Root defaultValue="2">



<CheckboxGroup.Item value="1">Off</CheckboxGroup.Item>



<CheckboxGroup.Item value="2">On</CheckboxGroup.Item>



</CheckboxGroup.Root>



<CheckboxGroup.Root defaultValue="2">



<CheckboxGroup.Item value="1" disabled>



Off



</CheckboxGroup.Item>



<CheckboxGroup.Item value="2" disabled>



On



</CheckboxGroup.Item>



</CheckboxGroup.Root>



</Flex>
```

#### Quick nav

Previous[Checkbox](/themes/docs/components/checkbox)

Next[Checkbox Cards](/themes/docs/components/checkbox-cards)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/checkbox-group.mdx "Edit this page on GitHub.")
