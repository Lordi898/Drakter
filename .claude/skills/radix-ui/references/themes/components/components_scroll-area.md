Scroll Area – Radix Themes

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

# Scroll Area

Custom-styled scrollable area using native functionality.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/scroll-area.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[ScrollArea] Issue)[View in Playground](/themes/playground#scroll-area)

# Principles of the typographic craft

Three fundamental aspects of typography are legibility, readability, and aesthetics. Although in a non-technical sense “legible” and “readable” are often used synonymously, typographically they are separate but related concepts.

Legibility describes how easily individual characters can be distinguished from one another. It is described by Walter Tracy as “the quality of being decipherable and recognisable”. For instance, if a “b” and an “h”, or a “3” and an “8”, are difficult to distinguish at small sizes, this is a problem of legibility.

Typographers are concerned with legibility insofar as it is their job to select the correct font to use. Brush Script is an example of a font containing many characters that might be difficult to distinguish. The selection of cases influences the legibility of typography because using only uppercase letters (all-caps) reduces legibility.

```
<ScrollArea type="always" scrollbars="vertical" style={{ height: 180 }}>



<Box p="2" pr="8">



<Heading size="4" mb="2" trim="start">



Principles of the typographic craft



</Heading>



<Flex direction="column" gap="4">



<Text as="p">



Three fundamental aspects of typography are legibility, readability, and



aesthetics. Although in a non-technical sense “legible” and “readable”



are often used synonymously, typographically they are separate but



related concepts.



</Text>



<Text as="p">



Legibility describes how easily individual characters can be



distinguished from one another. It is described by Walter Tracy as “the



quality of being decipherable and recognisable”. For instance, if a “b”



and an “h”, or a “3” and an “8”, are difficult to distinguish at small



sizes, this is a problem of legibility.



</Text>



<Text as="p">



Typographers are concerned with legibility insofar as it is their job to



select the correct font to use. Brush Script is an example of a font



containing many characters that might be difficult to distinguish. The



selection of cases influences the legibility of typography because using



only uppercase letters (all-caps) reduces legibility.



</Text>



</Flex>



</Box>



</ScrollArea>
```

## [API Reference](#api-reference)

This component inherits props from the ScrollArea primitive [Root](/primitives/docs/components/scroll-area#root) and [Viewport](/primitives/docs/components/scroll-area#viewport) parts. It supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3">` | `"1"` |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |
| `scrollbars` Prop description | `"vertical" | "horizontal" | "both"` | `"both"` |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the scrollbar handles.

```
<Flex direction="column" gap="2">



<ScrollArea
		size="1"
		type="always"
		scrollbars="horizontal"
		style={{ width: 300, height: 12 }}
	>



<Box width="800px" height="1px" />



</ScrollArea>



<ScrollArea
		size="2"
		type="always"
		scrollbars="horizontal"
		style={{ width: 350, height: 16 }}
	>



<Box width="900px" height="1px" />



</ScrollArea>



<ScrollArea
		size="3"
		type="always"
		scrollbars="horizontal"
		style={{ width: 400, height: 20 }}
	>



<Box width="1000px" height="1px" />



</ScrollArea>



</Flex>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius to the handles.

```
<Flex direction="column" gap="3">



<ScrollArea
		radius="none"
		type="always"
		scrollbars="horizontal"
		style={{ width: 350, height: 20 }}
	>



<Box width="800px" height="1px" />



</ScrollArea>



<ScrollArea
		radius="full"
		type="always"
		scrollbars="horizontal"
		style={{ width: 350, height: 20 }}
	>



<Box width="800px" height="1px" />



</ScrollArea>



</Flex>
```

### [Scrollbars](#scrollbars)

Use the `scrollbars` prop to limit scrollable axes.

Three fundamental aspects of typography are legibility, readability, and aesthetics. Although in a non-technical sense "legible" and "readable" are often used synonymously, typographically they are separate but related concepts.Legibility describes how easily individual characters can be distinguished from one another. It is described by Walter Tracy as "the quality of being decipherable and recognisable". For instance, if a "b" and an "h", or a "3" and an "8", are difficult to distinguish at small sizes, this is a problem of legibility.

Three fundamental aspects of typography are legibility, readability, and aesthetics. Although in a non-technical sense "legible" and "readable" are often used synonymously, typographically they are separate but related concepts.Legibility describes how easily individual characters can be distinguished from one another. It is described by Walter Tracy as "the quality of being decipherable and recognisable". For instance, if a "b" and an "h", or a "3" and an "8", are difficult to distinguish at small sizes, this is a problem of legibility.

```
<Grid columns="2" gap="2">



<ScrollArea type="always" scrollbars="vertical" style={{ height: 150 }}>



<Flex p="2" pr="8" direction="column" gap="4">



<Text size="2" trim="both">



Three fundamental aspects of typography are legibility, readability, and



aesthetics. Although in a non-technical sense "legible" and "readable"



are often used synonymously, typographically they are separate but



related concepts.



</Text>



<Text size="2" trim="both">



Legibility describes how easily individual characters can be



distinguished from one another. It is described by Walter Tracy as "the



quality of being decipherable and recognisable". For instance, if a "b"



and an "h", or a "3" and an "8", are difficult to distinguish at small



sizes, this is a problem of legibility.



</Text>



</Flex>



</ScrollArea>



<ScrollArea type="always" scrollbars="horizontal" style={{ height: 150 }}>



<Flex gap="4" p="2" width="700px">



<Text size="2" trim="both">



Three fundamental aspects of typography are legibility, readability, and



aesthetics. Although in a non-technical sense "legible" and "readable"



are often used synonymously, typographically they are separate but



related concepts.



</Text>



<Text size="2" trim="both">



Legibility describes how easily individual characters can be



distinguished from one another. It is described by Walter Tracy as "the



quality of being decipherable and recognisable". For instance, if a "b"



and an "h", or a "3" and an "8", are difficult to distinguish at small



sizes, this is a problem of legibility.



</Text>



</Flex>



</ScrollArea>



</Flex>
```

#### Quick nav

Previous[Radio Cards](/themes/docs/components/radio-cards)

Next[Segmented Control](/themes/docs/components/segmented-control)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/scroll-area.mdx "Edit this page on GitHub.")
