Section – Radix Themes

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

# Section

Denotes a section of page content.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/section.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Section] Issue)

```
<Box
	py="8"
	style={{ backgroundColor: "var(--gray-a2)", borderRadius: "var(--radius-3)" }}
>



<DecorativeBox asChild>



<Section size="2" />



</DecorativeBox>



</Box>
```

## [API Reference](#api-reference)

This component is based on the `section` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3" | "4">` | `"3"` |
| `display` | `Responsive<"none" | "initial">` | No default value |

The following props are shared between [Box](/themes/docs/components/box), [Flex](/themes/docs/components/flex), [Grid](/themes/docs/components/grid), [Container](/themes/docs/components/container) and [Section](/themes/docs/components/section) components. Read more about layout components in [Layout](/themes/docs/overview/layout).

| Prop | Type | Default |
| --- | --- | --- |
| `p` | `Responsive<enum | string>` See full type | No default value |
| `px` | `Responsive<enum | string>` See full type | No default value |
| `py` | `Responsive<enum | string>` See full type | No default value |
| `pt` | `Responsive<enum | string>` See full type | No default value |
| `pr` | `Responsive<enum | string>` See full type | No default value |
| `pb` | `Responsive<enum | string>` See full type | No default value |
| `pl` | `Responsive<enum | string>` See full type | No default value |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | No default value |
| `height` | `Responsive<string>` | No default value |
| `minHeight` | `Responsive<string>` | No default value |
| `maxHeight` | `Responsive<string>` | No default value |
| `position` | `Responsive<enum>` See full type | No default value |
| `inset` | `Responsive<enum | string>` See full type | No default value |
| `top` | `Responsive<enum | string>` See full type | No default value |
| `right` | `Responsive<enum | string>` See full type | No default value |
| `bottom` | `Responsive<enum | string>` See full type | No default value |
| `left` | `Responsive<enum | string>` See full type | No default value |
| `overflow` | `Responsive<enum>` See full type | No default value |
| `overflowX` | `Responsive<enum>` See full type | No default value |
| `overflowY` | `Responsive<enum>` See full type | No default value |
| `flexBasis` | `Responsive<string>` | No default value |
| `flexShrink` | `Responsive<enum | string>` See full type | No default value |
| `flexGrow` | `Responsive<enum | string>` See full type | No default value |
| `gridArea` | `Responsive<string>` | No default value |
| `gridColumn` | `Responsive<string>` | No default value |
| `gridColumnStart` | `Responsive<string>` | No default value |
| `gridColumnEnd` | `Responsive<string>` | No default value |
| `gridRow` | `Responsive<string>` | No default value |
| `gridRowStart` | `Responsive<string>` | No default value |
| `gridRowEnd` | `Responsive<string>` | No default value |

#### Quick nav

Previous[Container](/themes/docs/components/container)

Next[Text](/themes/docs/components/text)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/section.mdx "Edit this page on GitHub.")
