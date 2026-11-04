Slider – Radix Themes

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

# Slider

Provides user selection from a range of values.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/slider.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Slider] Issue)[View in Playground](/themes/playground#slider)

```
<Slider defaultValue={[50]} />
```

## [API Reference](#api-reference)

This component inherits props from the [Slider primitive](/primitives/docs/components/slider) and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"classic" | "surface" | "soft"` | `"surface"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

```
<Flex direction="column" gap="4" maxWidth="300px">



<Slider defaultValue={[25]} size="1" />



<Slider defaultValue={[50]} size="2" />



<Slider defaultValue={[75]} size="3" />



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

```
<Flex direction="column" gap="4" maxWidth="300px">



<Slider defaultValue={[25]} variant="surface" />



<Slider defaultValue={[50]} variant="classic" />



<Slider defaultValue={[75]} variant="soft" />



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex direction="column" gap="4" maxWidth="300px">



<Slider defaultValue={[20]} color="indigo" />



<Slider defaultValue={[40]} color="cyan" />



<Slider defaultValue={[60]} color="orange" />



<Slider defaultValue={[80]} color="crimson" />



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast in light mode.

```
<Grid columns="2" gap="4">



<Slider defaultValue={[10]} color="indigo" />



<Slider defaultValue={[10]} color="indigo" highContrast />



<Slider defaultValue={[30]} color="cyan" />



<Slider defaultValue={[30]} color="cyan" highContrast />



<Slider defaultValue={[50]} color="orange" />



<Slider defaultValue={[50]} color="orange" highContrast />



<Slider defaultValue={[70]} color="crimson" />



<Slider defaultValue={[70]} color="crimson" highContrast />



<Slider defaultValue={[90]} color="gray" />



<Slider defaultValue={[90]} color="gray" highContrast />



</Grid>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

```
<Flex direction="column" gap="4" maxWidth="300px">



<Slider defaultValue={[25]} radius="none" />



<Slider defaultValue={[50]} radius="small" />



<Slider defaultValue={[75]} radius="full" />



</Flex>
```

### [Range](#range)

Provide multiple values to create a range slider.

```
<Slider defaultValue={[25, 75]} />
```

#### Quick nav

Previous[Skeleton](/themes/docs/components/skeleton)

Next[Spinner](/themes/docs/components/spinner)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/slider.mdx "Edit this page on GitHub.")
