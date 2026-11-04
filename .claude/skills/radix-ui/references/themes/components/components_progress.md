Progress – Radix Themes

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

# Progress

Displays a progress bar related to a task.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/progress.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Progress] Issue)[View in Playground](/themes/playground#progress)

```
<Box maxWidth="300px">



<Progress />



</Box>
```

## [API Reference](#api-reference)

This component inherits props from the [Progress primitive](/primitives/docs/components/progress) and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"classic" | "surface" | "soft"` | `"surface"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |
| `duration` | `string` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

```
<Flex direction="column" gap="4" maxWidth="300px">



<Progress value={25} size="1" />



<Progress value={50} size="2" />



<Progress value={75} size="3" />



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

```
<Flex direction="column" gap="4" maxWidth="300px">



<Progress value={25} variant="classic" />



<Progress value={50} variant="surface" />



<Progress value={75} variant="soft" />



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex direction="column" gap="4" maxWidth="300px">



<Progress value={20} color="indigo" />



<Progress value={40} color="cyan" />



<Progress value={60} color="orange" />



<Progress value={80} color="crimson" />



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

```
<Grid columns="2" gap="4">



<Progress value={10} color="indigo" />



<Progress value={10} color="indigo" highContrast />



<Progress value={30} color="cyan" />



<Progress value={30} color="cyan" highContrast />



<Progress value={50} color="orange" />



<Progress value={50} color="orange" highContrast />



<Progress value={70} color="crimson" />



<Progress value={70} color="crimson" highContrast />



<Progress value={90} color="gray" />



<Progress value={90} color="gray" highContrast />



</Grid>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

```
<Flex direction="column" gap="4" maxWidth="300px">



<Progress value={25} radius="none" />



<Progress value={50} radius="small" />



<Progress value={75} radius="full" />



</Flex>
```

### [With controlled value](#with-controlled-value)

Use the `value` prop to provide a precise indication of the task progress.

```
<Progress value={75} />
```

### [With custom duration](#with-custom-duration)

Use the `duration` prop to indicate an approximate duration of an indeterminate task. Once the duration times out, the progress bar will start an indeterminate animation.

```
<Progress duration="30s" />
```

When an approximate duration can be estimated, the Progress component is still useful over [Spinner](/themes/docs/components/spinner), which doesn’t provide any visual cues towards the progress of the task.

#### Quick nav

Previous[Popover](/themes/docs/components/popover)

Next[Radio](/themes/docs/components/radio)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/progress.mdx "Edit this page on GitHub.")
