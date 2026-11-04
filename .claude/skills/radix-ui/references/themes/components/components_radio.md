Radio – Radix Themes

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

# Radio

Standalone radio button that can be used in any layout.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/radio-group.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Radio] Issue)[View in Playground](/themes/playground#radio)

DefaultComfortableCompact

```
<Flex align="start" direction="column" gap="1">



<Flex asChild gap="2">



<Text as="label" size="2">



<Radio name="example" value="1" defaultChecked />



Default



</Text>



</Flex>



<Flex asChild gap="2">



<Text as="label" size="2">



<Radio name="example" value="2" />



Comfortable



</Text>



</Flex>



<Flex asChild gap="2">



<Text as="label" size="2">



<Radio name="example" value="3" />



Compact



</Text>



</Flex>



</Flex>
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

Use the `size` prop to control the radio button size.

```
<Flex align="center" gap="4">



<Flex gap="2">



<Radio size="1" name="size-1" value="1" defaultChecked />



<Radio size="1" name="size-1" value="2" />



</Flex>



<Flex gap="2">



<Radio size="2" name="size-2" value="1" defaultChecked />



<Radio size="2" name="size-2" value="2" />



</Flex>



<Flex gap="2">



<Radio size="3" name="size-3" value="1" defaultChecked />



<Radio size="3" name="size-3" value="2" />



</Flex>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style of the radio buttons.

```
<Flex align="center" gap="4">



<Flex gap="2">



<Radio variant="surface" name="surface" value="1" defaultChecked />



<Radio variant="surface" name="surface" value="2" />



</Flex>



<Flex gap="2">



<Radio variant="classic" name="classic" value="1" defaultChecked />



<Radio variant="classic" name="classic" value="2" />



</Flex>



<Flex gap="2">



<Radio variant="soft" name="soft" value="1" defaultChecked />



<Radio variant="soft" name="soft" value="2" />



</Flex>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex as="span" gap="2">



<Radio color="indigo" defaultChecked />



<Radio color="cyan" defaultChecked />



<Radio color="orange" defaultChecked />



<Radio color="crimson" defaultChecked />



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

```
<Grid columns="5" display="inline-grid" gap="2">



<Radio color="indigo" defaultChecked />



<Radio color="cyan" defaultChecked />



<Radio color="orange" defaultChecked />



<Radio color="crimson" defaultChecked />



<Radio color="gray" defaultChecked />



<Radio color="indigo" defaultChecked highContrast />



<Radio color="cyan" defaultChecked highContrast />



<Radio color="orange" defaultChecked highContrast />



<Radio color="crimson" defaultChecked highContrast />



<Radio color="gray" defaultChecked highContrast />



</Grid>
```

### [Alignment](#alignment)

Composing `Radio` within `Text` automatically centers it with the first line of text. It is automatically well-aligned with multi-line text too.

DefaultCompact

DefaultCompact

DefaultCompact

```
<Flex direction="column" gap="3">



<Flex align="start" direction="column" gap="1">



<Flex asChild gap="2">



<Text as="label" size="2">



<Radio size="1" name="alignment-1" value="1" defaultChecked />



Default



</Text>



</Flex>



<Flex asChild gap="2">



<Text as="label" size="2">



<Radio size="1" name="alignment-1" value="2" />



Compact



</Text>



</Flex>



</Flex>



<Flex align="start" direction="column" gap="1">



<Flex asChild gap="2">



<Text as="label" size="3">



<Radio size="2" name="alignment-2" value="1" defaultChecked />



Default



</Text>



</Flex>



<Flex asChild gap="2">



<Text as="label" size="3">



<Radio size="2" name="alignment-2" value="2" />



Compact



</Text>



</Flex>



</Flex>



<Flex align="start" direction="column" gap="1">



<Flex asChild gap="2">



<Text as="label" size="4">



<Radio size="3" name="alignment-3" value="1" defaultChecked />



Default



</Text>



</Flex>



<Flex asChild gap="2">



<Text as="label" size="4">



<Radio size="3" name="alignment-3" value="2" />



Compact



</Text>



</Flex>



</Flex>



</Flex>
```

### [Disabled](#disabled)

Use the native `disabled` attribute to create a disabled radio button.

OnOff

OnOff

```
<Flex direction="column" gap="3">



<Flex align="start" direction="column" gap="1">



<Flex asChild gap="2">



<Text as="label" size="2">



<Radio name="enabled" value="1" defaultChecked />



On



</Text>



</Flex>



<Flex asChild gap="2">



<Text as="label" size="2">



<Radio name="enabled" value="2" />



Off



</Text>



</Flex>



</Flex>



<Flex align="start" direction="column" gap="1">



<Flex asChild gap="2">



<Text as="label" size="2" color="gray">



<Radio disabled name="disabled" value="1" defaultChecked />



On



</Text>



</Flex>



<Flex asChild gap="2">



<Text as="label" size="2" color="gray">



<Radio disabled name="disabled" value="2" />



Off



</Text>



</Flex>



</Flex>



</Flex>
```

#### Quick nav

Previous[Progress](/themes/docs/components/progress)

Next[Radio Group](/themes/docs/components/radio-group)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/radio.mdx "Edit this page on GitHub.")
