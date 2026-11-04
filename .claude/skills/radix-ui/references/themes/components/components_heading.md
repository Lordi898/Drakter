Heading – Radix Themes

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

# Heading

Semantic heading element.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/heading.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Heading] Issue)[View in Playground](/themes/playground#heading)

# The quick brown fox jumps over the lazy dog

```
<Heading>The quick brown fox jumps over the lazy dog</Heading>
```

## [API Reference](#api-reference)

This component is based on the `h1` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `as` Prop description | `"h1" | "h2" | "h3" | "h4" | "h5" | "h6"` | `"h1"` |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<enum>` See full type | `"6"` |
| `weight` | `Responsive<"light" | "regular" | "medium" | "bold">` | No default value |
| `align` Prop description | `Responsive<"left" | "center" | "right">` | No default value |
| `trim` Prop description | `Responsive<"normal" | "start" | "end" | "both">` | No default value |
| `truncate` Prop description | `boolean` | No default value |
| `wrap` Prop description | `Responsive<"wrap" | "nowrap" | "pretty" | "balance">` | No default value |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

## [Examples](#examples)

### [As another element](#as-another-element)

Use the `as` prop to change the heading level. This prop is purely semantic and does not change the visual appearance.

# Level 1

## Level 2

### Level 3

```
<Heading as="h1">Level 1</Heading>



<Heading as="h2">Level 2</Heading>



<Heading as="h3">Level 3</Heading>
```

### [Size](#size)

Use the `size` prop to control the size of the heading. The prop also provides correct line height and corrective letter spacing—as text size increases, the relative line height and letter spacing decrease.

Heading sizes match [Text](/themes/components/text) sizes. However, the line heights are set a bit tighter as headings tend to be shorter than running text.

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

```
<Flex direction="column" gap="3">



<Heading size="1">The quick brown fox jumps over the lazy dog</Heading>



<Heading size="2">The quick brown fox jumps over the lazy dog</Heading>



<Heading size="3">The quick brown fox jumps over the lazy dog</Heading>



<Heading size="4">The quick brown fox jumps over the lazy dog</Heading>



<Heading size="5">The quick brown fox jumps over the lazy dog</Heading>



<Heading size="6">The quick brown fox jumps over the lazy dog</Heading>



<Heading size="7">The quick brown fox jumps over the lazy dog</Heading>



<Heading size="8">The quick brown fox jumps over the lazy dog</Heading>



<Heading size="9">The quick brown fox jumps over the lazy dog</Heading>



</Flex>
```

### [Weight](#weight)

Use the `weight` prop to set the text weight.

# The quick brown fox jumps over the lazy dog.

# The quick brown fox jumps over the lazy dog.

# The quick brown fox jumps over the lazy dog.

```
<Heading weight="regular">



The quick brown fox jumps over the lazy dog.



</Heading>



<Heading weight="medium">



The quick brown fox jumps over the lazy dog.



</Heading>



<Heading weight="bold">



The quick brown fox jumps over the lazy dog.



</Heading>
```

### [Align](#align)

Use the `align` prop to set text alignment.

# Left-aligned

# Center-aligned

# Right-aligned

```
<Heading align="left">Left-aligned</Heading>



<Heading align="center">Center-aligned</Heading>



<Heading align="right">Right-aligned</Heading>
```

### [Trim](#trim)

Use the `trim` prop to trim the leading space at the start, end, or both sides of the text box.

The prop works similarly to the upcoming [half-leading control](https://www.w3.org/TR/css-inline-3/#leading-trim) spec, but uses a common [negative margin workaround](https://seek-oss.github.io/capsize/) under the hood for cross-browser support.

# Without trim

# With trim

```
<Flex direction="column" gap="3">



<Heading
		trim="normal"
		style={{
			background: "var(--gray-a2)",
			borderTop: "1px dashed var(--gray-a7)",
			borderBottom: "1px dashed var(--gray-a7)",
		}}
	>



Without trim



</Heading>



<Heading
		trim="both"
		style={{
			background: "var(--gray-a2)",
			borderTop: "1px dashed var(--gray-a7)",
			borderBottom: "1px dashed var(--gray-a7)",
		}}
	>



With trim



</Heading>



</Flex>
```

Trimming the leading is useful when dialing in vertical spacing in cards or other “boxy” components. Otherwise, padding looks larger on top and bottom than on the sides.

# Without trim

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant.

# With trim

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant.

```
<Flex direction="column" gap="3">



<Box
		style={{
			background: "var(--gray-a2)",
			border: "1px dashed var(--gray-a7)",
		}}
		p="4"
	>



<Heading mb="1" size="3">



Without trim



</Heading>



<Text>



The goal of typography is to relate font size, line height, and line width



in a proportional way that maximizes beauty and makes reading easier and



more pleasant.



</Text>



</Box>



<Box
		p="4"
		style={{
			background: "var(--gray-a2)",
			border: "1px dashed var(--gray-a7)",
		}}
	>



<Heading mb="1" size="3" trim="start">



With trim



</Heading>



<Text trim="end">



The goal of typography is to relate font size, line height, and line width



in a proportional way that maximizes beauty and makes reading easier and



more pleasant.



</Text>



</Box>



</Flex>
```

The default trim values are configured for the system font stack that’s used by Radix Themes. If you are using custom fonts, you can [adjust](/themes/docs/theme/typography#customization) the trim values using the corresponding CSS variables.

```
.radix-themes {



--default-leading-trim-start: 0.42em;



--default-leading-trim-end: 0.36em;



--heading-leading-trim-start: 0.42em;



--heading-leading-trim-end: 0.36em;



}
```

### [Truncate](#truncate)

Use the `truncate` prop to truncate text with an ellipsis when it overflows its container.

# The quick brown fox jumps over the lazy dog

```
<Flex maxWidth="300px">



<Heading truncate>The quick brown fox jumps over the lazy dog</Heading>



</Flex>
```

### [Wrap](#wrap)

Use the `wrap` prop to control text wrapping.

# The quick brown fox jumps over the lazy dog

```
<Flex maxWidth="300px">



<Heading wrap="nowrap">The quick brown fox jumps over the lazy dog</Heading>



</Flex>
```

# The quick brown fox jumps over the lazy dog

```
<Flex maxWidth="300px">



<Heading wrap="balance">The quick brown fox jumps over the lazy dog</Heading>



</Flex>
```

# The quick brown fox jumps over the lazy dog

```
<Flex maxWidth="300px">



<Heading wrap="pretty">The quick brown fox jumps over the lazy dog</Heading>



</Flex>
```

`text-wrap: pretty` is an experimental value that is [not yet supported in all browsers](https://developer.mozilla.org/en-US/docs/Web/CSS/text-wrap#browser_compatibility). However, it can be treated as a progressive enhancement for browsers that do support it.

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color). The text colors are designed to achieve at least Lc 60 APCA contrast over common background colors.

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

# The quick brown fox jumps over the lazy dog

```
<Flex direction="column">



<Heading color="indigo">The quick brown fox jumps over the lazy dog</Heading>



<Heading color="cyan">The quick brown fox jumps over the lazy dog</Heading>



<Heading color="orange">The quick brown fox jumps over the lazy dog</Heading>



<Heading color="crimson">The quick brown fox jumps over the lazy dog</Heading>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

# The quick brown fox jumps over the lazy dog.

# The quick brown fox jumps over the lazy dog.

```
<Flex direction="column">



<Heading color="gray">The quick brown fox jumps over the lazy dog.</Heading>



<Heading color="gray" highContrast>



The quick brown fox jumps over the lazy dog.



</Heading>



</Flex>
```

#### Quick nav

Previous[Text](/themes/docs/components/text)

Next[Blockquote](/themes/docs/components/blockquote)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/heading.mdx "Edit this page on GitHub.")
