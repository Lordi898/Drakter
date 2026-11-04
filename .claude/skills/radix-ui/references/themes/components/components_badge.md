Badge – Radix Themes

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

# Badge

Stylized badge element.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/badge.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Badge] Issue)[View in Playground](/themes/playground#badge)

In progressIn reviewComplete

```
<Flex gap="2">



<Badge color="orange">In progress</Badge>



<Badge color="blue">In review</Badge>



<Badge color="green">Complete</Badge>



</Flex>
```

## [API Reference](#api-reference)

This component is based on the `span` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3">` | `"1"` |
| `variant` Prop description | `"solid" | "soft" | "surface" | "outline"` | `"soft"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

NewNewNew

```
<Flex align="center" gap="2">



<Badge size="1" color="indigo">



New



</Badge>



<Badge size="2" color="indigo">



New



</Badge>



<Badge size="3" color="indigo">



New



</Badge>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

NewNewNewNew

```
<Flex gap="2">



<Badge variant="solid" color="indigo">



New



</Badge>



<Badge variant="soft" color="indigo">



New



</Badge>



<Badge variant="surface" color="indigo">



New



</Badge>



<Badge variant="outline" color="indigo">



New



</Badge>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

NewNewNewNew

```
<Flex gap="2">



<Badge color="indigo">New</Badge>



<Badge color="cyan">New</Badge>



<Badge color="orange">New</Badge>



<Badge color="crimson">New</Badge>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

NewNewNewNew

NewNewNewNew

```
<Flex direction="column" gap="2">



<Flex gap="2">



<Badge color="gray" variant="solid">



New



</Badge>



<Badge color="gray" variant="soft">



New



</Badge>



<Badge color="gray" variant="surface">



New



</Badge>



<Badge color="gray" variant="outline">



New



</Badge>



</Flex>



<Flex gap="2">



<Badge color="gray" variant="solid" highContrast>



New



</Badge>



<Badge color="gray" variant="soft" highContrast>



New



</Badge>



<Badge color="gray" variant="surface" highContrast>



New



</Badge>



<Badge color="gray" variant="outline" highContrast>



New



</Badge>



</Flex>



</Flex>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

NewNewNew

```
<Flex gap="2">



<Badge variant="solid" radius="none" color="indigo">



New



</Badge>



<Badge variant="solid" radius="large" color="indigo">



New



</Badge>



<Badge variant="solid" radius="full" color="indigo">



New



</Badge>



</Flex>
```

#### Quick nav

Previous[Avatar](/themes/docs/components/avatar)

Next[Button](/themes/docs/components/button)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/badge.mdx "Edit this page on GitHub.")
