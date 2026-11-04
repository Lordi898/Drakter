Blockquote – Radix Themes

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

# Blockquote

Block-level quotation from another source.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/blockquote.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Blockquote] Issue)[View in Playground](/themes/playground#blockquote)

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

```
<Blockquote>



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>
```

## [API Reference](#api-reference)

This component is based on the `blockquote` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<enum>` See full type | No default value |
| `weight` | `Responsive<"light" | "regular" | "medium" | "bold">` | No default value |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `truncate` Prop description | `boolean` | No default value |
| `wrap` Prop description | `Responsive<"wrap" | "nowrap" | "pretty" | "balance">` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

```
<Flex direction="column" gap="5">



<Box maxWidth="300px">



<Blockquote size="1">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



<Box maxWidth="350px">



<Blockquote size="2">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



<Box maxWidth="400px">



<Blockquote size="3">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



<Box maxWidth="450px">



<Blockquote size="4">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



<Box maxWidth="500px">



<Blockquote size="5">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



<Box maxWidth="550px">



<Blockquote size="6">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



<Box maxWidth="600px">



<Blockquote size="7">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



<Box maxWidth="650px">



<Blockquote size="8">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



<Box maxWidth="1000px">



<Blockquote size="9">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Box>



</Flex>
```

### [Weight](#weight)

Use the `weight` prop to set the text weight.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

```
<Flex direction="column" gap="3" maxWidth="500px">



<Blockquote weight="regular">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



<Blockquote weight="medium">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



<Blockquote weight="bold">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

```
<Flex direction="column" gap="3" maxWidth="500px">



<Blockquote color="indigo">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



<Blockquote color="cyan">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



<Blockquote color="orange">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



<Blockquote color="crimson">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

```
<Flex direction="column" gap="3" maxWidth="500px">



<Blockquote color="gray">



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



<Blockquote color="gray" highContrast>



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Flex>
```

### [Truncate](#truncate)

Use the `truncate` prop to truncate text with an ellipsis when it overflows its container.

> Perfect typography is certainly the most elusive of all arts. Sculpture in stone alone comes near it in obstinacy.

```
<Flex maxWidth="500px">



<Blockquote truncate>



Perfect typography is certainly the most elusive of all arts. Sculpture in



stone alone comes near it in obstinacy.



</Blockquote>



</Flex>
```

#### Quick nav

Previous[Heading](/themes/docs/components/heading)

Next[Code](/themes/docs/components/code)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/blockquote.mdx "Edit this page on GitHub.")
