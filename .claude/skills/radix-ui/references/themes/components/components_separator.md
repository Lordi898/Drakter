Separator – Radix Themes

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

# Separator

Visually or semantically separates content.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/separator.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Separator] Issue)[View in Playground](/themes/playground#separator)

Tools for building high-quality, accessible UI.

ThemesPrimitivesIconsColors

```
<Text size="2">



Tools for building high-quality, accessible UI.



<Separator my="3" size="4" />



<Flex gap="3" align="center">



Themes



<Separator orientation="vertical" />



Primitives



<Separator orientation="vertical" />



Icons



<Separator orientation="vertical" />



Colors



</Flex>



</Text>
```

## [API Reference](#api-reference)

This component inherits props from the [Separator primitive](/primitives/docs/components/separator) and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `orientation` | `Responsive<"horizontal" | "vertical">` | `"horizontal"` |
| `size` | `Responsive<"1" | "2" | "3" | "4">` | `"1"` |
| `color` Prop description | `enum` See full type | `"gray"` |
| `decorative` | `boolean` | `true` |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the separator. The largest step takes full width or height of the container.

```
<Flex direction="column" gap="4">



<Separator orientation="horizontal" size="1" />



<Separator orientation="horizontal" size="2" />



<Separator orientation="horizontal" size="3" />



<Separator orientation="horizontal" size="4" />



</Flex>
```

```
<Flex align="center" gap="4" height="96px">



<Separator orientation="vertical" size="1" />



<Separator orientation="vertical" size="2" />



<Separator orientation="vertical" size="3" />



<Separator orientation="vertical" size="4" />



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex direction="column" gap="3">



<Separator color="indigo" size="4" />



<Separator color="cyan" size="4" />



<Separator color="orange" size="4" />



<Separator color="crimson" size="4" />



</Flex>
```

### [Orientation](#orientation)

Use the `orientation` prop to control whether the separator is horizontal or vertical.

```
<Flex align="center" gap="4">



<Separator orientation="horizontal" />



<Separator orientation="vertical" />



</Flex>
```

#### Quick nav

Previous[Select](/themes/docs/components/select)

Next[Skeleton](/themes/docs/components/skeleton)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/separator.mdx "Edit this page on GitHub.")
