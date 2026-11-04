Switch – Radix Themes

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

# Switch

Toggle switch alternative to the checkbox.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/switch.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Switch] Issue)[View in Playground](/themes/playground#switch)

```
<Switch defaultChecked />
```

## [API Reference](#api-reference)

This component inherits props from the [Switch primitive](/primitives/docs/components/switch) and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"classic" | "surface" | "soft"` | `"surface"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the switch.

```
<Flex align="center" gap="2">



<Switch size="1" defaultChecked />



<Switch size="2" defaultChecked />



<Switch size="3" defaultChecked />



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style of the switch.

```
<Flex gap="2">



<Flex direction="column" gap="3">



<Switch variant="surface" />



<Switch variant="classic" />



<Switch variant="soft" />



</Flex>



<Flex direction="column" gap="3">



<Switch variant="surface" defaultChecked />



<Switch variant="classic" defaultChecked />



<Switch variant="soft" defaultChecked />



</Flex>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex gap="2">



<Switch color="indigo" defaultChecked />



<Switch color="cyan" defaultChecked />



<Switch color="orange" defaultChecked />



<Switch color="crimson" defaultChecked />



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast in light mode.

```
<Grid rows="2" gapX="2" gapY="3" display="inline-grid" flow="column">



<Switch color="indigo" defaultChecked />



<Switch color="indigo" defaultChecked highContrast />



<Switch color="cyan" defaultChecked />



<Switch color="cyan" defaultChecked highContrast />



<Switch color="orange" defaultChecked />



<Switch color="orange" defaultChecked highContrast />



<Switch color="crimson" defaultChecked />



<Switch color="crimson" defaultChecked highContrast />



<Switch color="gray" defaultChecked />



<Switch color="gray" defaultChecked highContrast />



</Grid>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

```
<Flex gap="3">



<Switch radius="none" defaultChecked />



<Switch radius="small" defaultChecked />



<Switch radius="full" defaultChecked />



</Flex>
```

### [Alignment](#alignment)

Composing `Switch` within `Text` automatically centers it with the first line of text.

Sync settings

Sync settings

Sync settings

```
<Flex direction="column" gap="3">



<Text as="label" size="2">



<Flex gap="2">



<Switch size="1" defaultChecked /> Sync settings



</Flex>



</Text>



<Text as="label" size="3">



<Flex gap="2">



<Switch size="2" defaultChecked /> Sync settings



</Flex>



</Text>



<Text as="label" size="4">



<Flex gap="2">



<Switch size="3" defaultChecked /> Sync settings



</Flex>



</Text>



</Flex>
```

It is automatically well-aligned with multi-line text too.

### [Disabled](#disabled)

Use the native `disabled` attribute to create a disabled switch.

Off

On

On

Off

```
<Flex direction="column" gap="2">



<Text as="label" size="2">



<Flex gap="2">



<Switch size="1" />



Off



</Flex>



</Text>



<Text as="label" size="2">



<Flex gap="2">



<Switch size="1" defaultChecked />



On



</Flex>



</Text>



<Text as="label" size="2" color="gray">



<Flex gap="2">



<Switch size="1" disabled />



On



</Flex>



</Text>



<Text as="label" size="2" color="gray">



<Flex gap="2">



<Switch size="1" disabled defaultChecked />



Off



</Flex>



</Text>



</Flex>
```

#### Quick nav

Previous[Spinner](/themes/docs/components/spinner)

Next[Table](/themes/docs/components/table)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/switch.mdx "Edit this page on GitHub.")
