Link – Radix Themes

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

# Link

Semantic element for navigation between pages.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/link.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Link] Issue)[View in Playground](/themes/playground#link)

[Sign up](#)

```
<Link href="#">Sign up</Link>
```

## [API Reference](#api-reference)

This component is based on the `a` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<enum>` See full type | No default value |
| `weight` | `Responsive<"light" | "regular" | "medium" | "bold">` | No default value |
| `trim` Prop description | `Responsive<"normal" | "start" | "end" | "both">` | No default value |
| `truncate` Prop description | `boolean` | No default value |
| `wrap` Prop description | `Responsive<"wrap" | "nowrap" | "pretty" | "balance">` | No default value |
| `underline` Prop description | `"auto" | "always" | "hover" | "none"` | `"auto"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the link. The prop also provides correct line height and corrective letter spacing—as text size increases, the relative line height and letter spacing decrease.

[Sign up](#)[Sign up](#)[Sign up](#)[Sign up](#)[Sign up](#)[Sign up](#)[Sign up](#)[Sign up](#)[Sign up](#)

```
<Flex direction="column" gap="3">



<Link href="#" size="1">



Sign up



</Link>



<Link href="#" size="2">



Sign up



</Link>



<Link href="#" size="3">



Sign up



</Link>



<Link href="#" size="4">



Sign up



</Link>



<Link href="#" size="5">



Sign up



</Link>



<Link href="#" size="6">



Sign up



</Link>



<Link href="#" size="7">



Sign up



</Link>



<Link href="#" size="8">



Sign up



</Link>



<Link href="#" size="9">



Sign up



</Link>



</Flex>
```

### [Weight](#weight)

Use the `weight` prop to set the text weight.

[Sign up](#)[Sign up](#)[Sign up](#)

```
<Flex direction="column">



<Link href="#" weight="regular">



Sign up



</Link>



<Link href="#" weight="medium">



Sign up



</Link>



<Link href="#" weight="bold">



Sign up



</Link>



</Flex>
```

### [Truncate](#truncate)

Use the `truncate` prop to truncate text with an ellipsis when it overflows its container.

[Sign up to the newsletter](#)

```
<Flex maxWidth="150px">



<Link href="#" truncate>



Sign up to the newsletter



</Link>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

[Sign up](#)[Sign up](#)[Sign up](#)[Sign up](#)

```
<Flex direction="column">



<Link href="#" color="indigo">



Sign up



</Link>



<Link href="#" color="cyan">



Sign up



</Link>



<Link href="#" color="orange">



Sign up



</Link>



<Link href="#" color="crimson">



Sign up



</Link>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

[Sign up](#)[Sign up](#)

```
<Flex direction="column">



<Link href="#" color="gray">



Sign up



</Link>



<Link href="#" color="gray" highContrast>



Sign up



</Link>



</Flex>
```

### [Underline](#underline)

Use the `underline` prop to manage the visibility of the underline affordance.

[Sign up](#)[Sign up](#)

```
<Flex direction="column">



<Link href="#" underline="hover">



Sign up



</Link>



<Link href="#" underline="always">



Sign up



</Link>



</Flex>
```

#### Quick nav

Previous[Kbd](/themes/docs/components/kbd)

Next[Quote](/themes/docs/components/quote)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/link.mdx "Edit this page on GitHub.")
