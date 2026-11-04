Text – Radix Themes

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

# Text

Foundational text primitive.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/text.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Text] Issue)[View in Playground](/themes/playground#text)

The quick brown fox jumps over the lazy dog.

```
<Text>The quick brown fox jumps over the lazy dog.</Text>
```

## [API Reference](#api-reference)

This component is based on the `span` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `as` Prop description | `"span" | "div" | "label" | "p"` | `"span"` |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<enum>` See full type | No default value |
| `weight` | `Responsive<"light" | "regular" | "medium" | "bold">` | No default value |
| `align` Prop description | `Responsive<"left" | "center" | "right">` | No default value |
| `trim` Prop description | `Responsive<"normal" | "start" | "end" | "both">` | No default value |
| `truncate` Prop description | `boolean` | No default value |
| `wrap` Prop description | `Responsive<"wrap" | "nowrap" | "pretty" | "balance">` | No default value |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

## [Examples](#examples)

### [As another element](#as-another-element)

Use the `as` prop to render text as a `p`, `label`, `div` or `span`. This prop is purely semantic and does not alter visual appearance.

This is a **paragraph** element.

This is a **label** element.

This is a **div** element.

This is a **span** element.

```
<Text as="p">This is a <Strong>paragraph</Strong> element.</Text>



<Text as="label">This is a <Strong>label</Strong> element.</Text>



<Text as="div">This is a <Strong>div</Strong> element.</Text>



<Text as="span">This is a <Strong>span</Strong> element.</Text>
```

### [Size](#size)

Use the `size` prop to control text size. This prop also provides correct line height and corrective letter spacing—as text size increases, the relative line height and letter spacing decrease.

The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.

```
<Flex direction="column" gap="3">



<Text size="1">The quick brown fox jumps over the lazy dog.</Text>



<Text size="2">The quick brown fox jumps over the lazy dog.</Text>



<Text size="3">The quick brown fox jumps over the lazy dog.</Text>



<Text size="4">The quick brown fox jumps over the lazy dog.</Text>



<Text size="5">The quick brown fox jumps over the lazy dog.</Text>



<Text size="6">The quick brown fox jumps over the lazy dog.</Text>



<Text size="7">The quick brown fox jumps over the lazy dog.</Text>



<Text size="8">The quick brown fox jumps over the lazy dog.</Text>



<Text size="9">The quick brown fox jumps over the lazy dog.</Text>



</Flex>
```

Sizes 2–4 are designed to work well for long-form content.

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant. The question is: What proportion(s) will give us the best results? The golden ratio is often observed in nature where beauty and utility intersect; perhaps we can use this “divine” proportion to enhance these attributes in our typography.

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant. The question is: What proportion(s) will give us the best results? The golden ratio is often observed in nature where beauty and utility intersect; perhaps we can use this “divine” proportion to enhance these attributes in our typography.

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant. The question is: What proportion(s) will give us the best results? The golden ratio is often observed in nature where beauty and utility intersect; perhaps we can use this “divine” proportion to enhance these attributes in our typography.

```
<Text as="p" mb="5" size="4">



The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant. The question is: What proportion(s) will give us the best results? The golden ratio is often observed in nature where beauty and utility intersect; perhaps we can use this “divine” proportion to enhance these attributes in our typography.



</Text>



<Text as="p" mb="5" size="3">



The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant. The question is: What proportion(s) will give us the best results? The golden ratio is often observed in nature where beauty and utility intersect; perhaps we can use this “divine” proportion to enhance these attributes in our typography.



</Text>



<Text as="p" size="2" color="gray">



The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant. The question is: What proportion(s) will give us the best results? The golden ratio is often observed in nature where beauty and utility intersect; perhaps we can use this “divine” proportion to enhance these attributes in our typography.



</Text>
```

Sizes 1–3 are designed to work well for UI labels.

Get startedStart your next project in minutes

Get startedStart your next project in minutes

Get startedStart your next project in minutes

Get startedStart your next project in minutes

```
<Grid align="center" columns="2" gap="5" p="3">



<Flex direction="column">



<Text size="3" weight="bold">



Get started



</Text>



<Text color="gray" size="2">



Start your next project in minutes



</Text>



</Flex>



<Flex direction="column">



<Text size="2" weight="bold">



Get started



</Text>



<Text color="gray" size="2">



Start your next project in minutes



</Text>



</Flex>



<Flex direction="column">



<Text size="2" weight="bold">



Get started



</Text>



<Text color="gray" size="1">



Start your next project in minutes



</Text>



</Flex>



<Flex direction="column">



<Text size="1" weight="bold">



Get started



</Text>



<Text color="gray" size="1">



Start your next project in minutes



</Text>



</Flex>



</Grid>
```

### [Weight](#weight)

Use the `weight` prop to set the text weight.

The quick brown fox jumps over the lazy dog.

The quick brown fox jumps over the lazy dog.

The quick brown fox jumps over the lazy dog.

```
<Text weight="regular" as="div">



The quick brown fox jumps over the lazy dog.



</Text>



<Text weight="medium" as="div">



The quick brown fox jumps over the lazy dog.



</Text>



<Text weight="bold" as="div">



The quick brown fox jumps over the lazy dog.



</Text>
```

### [Align](#align)

Use the `align` prop to set text alignment.

Left-aligned

Center-aligned

Right-aligned

```
<Text align="left" as="div">Left-aligned</Text>



<Text align="center" as="div">Center-aligned</Text>



<Text align="right" as="div">Right-aligned</Text>
```

### [Trim](#trim)

Use the `trim` prop to trim the leading space at the start, end, or both sides of the text box.

The prop works similarly to the upcoming [half-leading control](https://www.w3.org/TR/css-inline-3/#leading-trim) spec, but uses a common [negative margin workaround](https://seek-oss.github.io/capsize/) under the hood for cross-browser support.

Without trimWith trim

```
<Flex direction="column" gap="3">



<Text
		trim="normal"
		style={{
			background: "var(--gray-a2)",
			borderTop: "1px dashed var(--gray-a7)",
			borderBottom: "1px dashed var(--gray-a7)",
		}}
	>



Without trim



</Text>



<Text
		trim="both"
		style={{
			background: "var(--gray-a2)",
			borderTop: "1px dashed var(--gray-a7)",
			borderBottom: "1px dashed var(--gray-a7)",
		}}
	>



With trim



</Text>



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

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant.

```
<Flex maxWidth="300px">



<Text truncate>



The goal of typography is to relate font size, line height, and line width



in a proportional way that maximizes beauty and makes reading easier and



more pleasant.



</Text>



</Flex>
```

### [Wrap](#wrap)

Use the `wrap` prop to control text wrapping.

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant.

```
<Flex maxWidth="270px">



<Text wrap="nowrap">



The goal of typography is to relate font size, line height, and line width



in a proportional way that maximizes beauty and makes reading easier and



more pleasant.



</Text>



</Flex>
```

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant.

```
<Flex maxWidth="270px">



<Text wrap="balance">



The goal of typography is to relate font size, line height, and line width



in a proportional way that maximizes beauty and makes reading easier and



more pleasant.



</Text>



</Flex>
```

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant.

```
<Flex maxWidth="270px">



<Text wrap="pretty">



The goal of typography is to relate font size, line height, and line width



in a proportional way that maximizes beauty and makes reading easier and



more pleasant.



</Text>



</Flex>
```

`text-wrap: pretty` is an experimental value that is [not yet supported in all browsers](https://developer.mozilla.org/en-US/docs/Web/CSS/text-wrap#browser_compatibility). However, it can be treated as a progressive enhancement for browsers that do support it.

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color). The text colors are designed to achieve at least Lc 60 APCA contrast over common background colors.

The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.

```
<Flex direction="column">



<Text color="indigo">The quick brown fox jumps over the lazy dog.</Text>



<Text color="cyan">The quick brown fox jumps over the lazy dog.</Text>



<Text color="orange">The quick brown fox jumps over the lazy dog.</Text>



<Text color="crimson">The quick brown fox jumps over the lazy dog.</Text>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

The quick brown fox jumps over the lazy dog.The quick brown fox jumps over the lazy dog.

```
<Flex direction="column">



<Text color="gray">The quick brown fox jumps over the lazy dog.</Text>



<Text color="gray" highContrast>



The quick brown fox jumps over the lazy dog.



</Text>



</Flex>
```

### [With formatting](#with-formatting)

Compose `Text` with formatting components to add emphasis and structure to content.

Look, such a helpful [link](#), an *italic emphasis*, a piece of computer `code`, and even a hotkey combination `⇧⌘A` within the text.

```
<Text as="p">



Look, such a helpful <Link href="#">link</Link>, an <Em>italic emphasis</Em>,



a piece of computer <Code>code</Code>, and even a hotkey combination{" "}



<Kbd>⇧⌘A</Kbd> within the text.



</Text>
```

### [With form controls](#with-form-controls)

Composing `Text` with a form control like [`Checkbox`](/themes/docs/components/checkbox), [`RadioGroup`](/themes/docs/components/radio-group), or [`Switch`](/themes/docs/components/switch) automatically centers the control with the first line of text, even when the text is multi-line.

I understand that these documents are confidential and cannot be shared with a third party.

```
<Box maxWidth="300px">



<Text as="label" size="3">



<Flex gap="2">



<Checkbox defaultChecked /> I understand that these documents are



confidential and cannot be shared with a third party.



</Flex>



</Text>



</Box>
```

#### Quick nav

Previous[Section](/themes/docs/components/section)

Next[Heading](/themes/docs/components/heading)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/text.mdx "Edit this page on GitHub.")