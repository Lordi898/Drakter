Icon Button – Radix Themes

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

# Icon Button

Button designed specifically for usage with a single icon.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/icon-button.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[IconButton] Issue)[View in Playground](/themes/playground#icon-button)

```
<IconButton>



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>
```

## [API Reference](#api-reference)

This component is based on the `button` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3" | "4">` | `"2"` |
| `variant` Prop description | `enum` See full type | `"solid"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |
| `loading` | `boolean` | `false` |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the button.

```
<Flex align="center" gap="3">



<IconButton size="1" variant="soft">



<MagnifyingGlassIcon width="15" height="15" />



</IconButton>



<IconButton size="2" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton size="3" variant="soft">



<MagnifyingGlassIcon width="22" height="22" />



</IconButton>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style of the button.

```
<Flex gap="3">



<IconButton variant="classic">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton variant="solid">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton variant="surface">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton variant="outline">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



</Flex>
```

#### Ghost

Use the `ghost` variant to display a button without chrome. Ghost buttons behave like text in layout, as they use a negative margin to optically align themselves against their siblings while maintaining the padding in active and hover states.

```
<IconButton variant="ghost">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex gap="3">



<IconButton color="crimson" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="indigo" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="grass" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="orange" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

```
<Flex direction="column" gap="3">



<Flex gap="3">



<IconButton color="gray" variant="classic">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="gray" variant="solid">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="gray" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="gray" variant="surface">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="gray" variant="outline">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



</Flex>



<Flex gap="3">



<IconButton color="gray" variant="classic" highContrast>



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="gray" variant="solid" highContrast>



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="gray" variant="soft" highContrast>



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="gray" variant="surface" highContrast>



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton color="gray" variant="outline" highContrast>



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



</Flex>



</Flex>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

```
<Flex gap="3">



<IconButton radius="none" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton radius="large" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton radius="full" variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



</Flex>
```

### [Loading](#loading)

Use the `loading` prop to display a loading spinner in place of button content. The button will be disabled while loading.

```
<Flex gap="3">



<IconButton loading variant="classic">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton loading variant="solid">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton loading variant="soft">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton loading variant="surface">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



<IconButton loading variant="outline">



<MagnifyingGlassIcon width="18" height="18" />



</IconButton>



</Flex>
```

#### Quick nav

Previous[Hover Card](/themes/docs/components/hover-card)

Next[Inset](/themes/docs/components/inset)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/icon-button.mdx "Edit this page on GitHub.")
