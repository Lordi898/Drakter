Code – Radix Themes

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

# Code

Marks text to signify a short fragment of computer code.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/code.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Code] Issue)[View in Playground](/themes/playground#code)

`console.log()`

```
<Code>console.log()</Code>
```

## [API Reference](#api-reference)

This component is based on the `code` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<enum>` See full type | No default value |
| `variant` Prop description | `"solid" | "soft" | "outline" | "ghost"` | `"soft"` |
| `weight` | `Responsive<"light" | "regular" | "medium" | "bold">` | No default value |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `truncate` Prop description | `boolean` | No default value |
| `wrap` Prop description | `Responsive<"wrap" | "nowrap" | "pretty" | "balance">` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control text size. This prop also provides correct line height and corrective letter spacing—as text size increases, the relative line height and letter spacing decrease.

`console.log()``console.log()``console.log()``console.log()``console.log()``console.log()``console.log()``console.log()``console.log()`

```
<Flex direction="column" gap="3" align="start">



<Code size="1">console.log()</Code>



<Code size="2">console.log()</Code>



<Code size="3">console.log()</Code>



<Code size="4">console.log()</Code>



<Code size="5">console.log()</Code>



<Code size="6">console.log()</Code>



<Code size="7">console.log()</Code>



<Code size="8">console.log()</Code>



<Code size="9">console.log()</Code>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

`console.log()``console.log()``console.log()``console.log()`

```
<Flex direction="column" align="start" gap="2">



<Code variant="solid">console.log()</Code>



<Code variant="soft">console.log()</Code>



<Code variant="outline">console.log()</Code>



<Code variant="ghost">console.log()</Code>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

`console.log()``console.log()``console.log()``console.log()`

```
<Flex direction="column" align="start" gap="2">



<Code color="indigo">console.log()</Code>



<Code color="crimson">console.log()</Code>



<Code color="cyan">console.log()</Code>



<Code color="orange">console.log()</Code>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

`console.log()``console.log()``console.log()``console.log()`

`console.log()``console.log()``console.log()``console.log()`

```
<Flex gap="3">



<Flex direction="column" align="start" gap="2">



<Code color="gray" variant="solid">



console.log()



</Code>



<Code color="gray" variant="soft">



console.log()



</Code>



<Code color="gray" variant="outline">



console.log()



</Code>



<Code color="gray" variant="ghost">



console.log()



</Code>



</Flex>



<Flex direction="column" align="start" gap="2">



<Code color="gray" variant="solid" highContrast>



console.log()



</Code>



<Code color="gray" variant="soft" highContrast>



console.log()



</Code>



<Code color="gray" variant="outline" highContrast>



console.log()



</Code>



<Code color="gray" variant="ghost" highContrast>



console.log()



</Code>



</Flex>



</Flex>
```

### [Weight](#weight)

Use the `weight` prop to set the text weight.

`console.log()``console.log()`

```
<Flex direction="column" gap="2" align="start">



<Code weight="regular">console.log()</Code>



<Code weight="bold">console.log()</Code>



</Flex>
```

### [Truncate](#truncate)

Use the `truncate` prop to truncate text with an ellipsis when it overflows its container.

`linear-gradient(red, orange, yellow, green, blue);`

```
<Flex maxWidth="200px">



<Code truncate>linear-gradient(red, orange, yellow, green, blue);</Code>



</Flex>
```

#### Quick nav

Previous[Blockquote](/themes/docs/components/blockquote)

Next[Em](/themes/docs/components/em)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/code.mdx "Edit this page on GitHub.")
