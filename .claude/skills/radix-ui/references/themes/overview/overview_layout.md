Layout – Radix Themes

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

Overview

# Layout

Get the layout concerns right.

## [Layout components](#layout-components)

Layout components are used to separate layout responsibilities from content and interactivity. This is *the* separation of concerns that makes your app maintainable and easy to reason about, and understanding these principles is key to building your interfaces effectively.

### [Box](#box)

[Box](/themes/docs/components/box) is the most fundamental layout component. Box is used to:

* Provide spacing to child elements.
* Impose sizing constraints on content.
* Control layout behaviour within flex and grid containers.
* Hide content based on screen size using its responsive `display` prop.

### [Flex](#flex)

[Flex](/themes/docs/components/flex) component does everything that Box can do, but comes with an additional set of props to organize items along an axis. It provides convenient access to the CSS [flexbox properties](https://css-tricks.com/snippets/css/a-guide-to-flexbox/)

### [Grid](#grid)

[Grid](/themes/docs/components/grid) is used to organize the content in columns and rows. Like Box and Flex, it’s made to provide convenient access to the underlying CSS [grid properties](https://css-tricks.com/snippets/css/complete-guide-grid/) without any magic of its own.

### [Section](#section)

[Section](/themes/docs/components/section) provides a consistent vertical spacing between the larger parts of your page content, creating a sense of hierarchy and separation. There’s just a few pre-defined sizes for different spacing levels to keep things simple and consistent.

### [Container](#container)

[Container](/themes/docs/components/container)’s sole responsibility is to provide a consistent `max-width` to the content it wraps. Like Section, it comes just with a couple of pre-defined sizes that work well with common breakpoints and typical content widths for comfortable reading.

## [Common layout props](#common-layout-props)

Each layout component has a set of it’s own specialized props and also a shared set of common layout props. All layout props support [responsive object values](/themes/docs/theme/breakpoints).

### [Padding](#padding)

Padding props can access the [space scale steps](/themes/docs/theme/spacing) or accept any valid [CSS padding value](https://developer.mozilla.org/en-US/docs/Web/CSS/padding).

```
<Box p="4" />



<Box p="100px">



<Box p={{ sm: '6', lg: '9' }}>
```

| Prop | Type | Default |
| --- | --- | --- |
| `p` | `Responsive<enum | string>` See full type | No default value |
| `px` | `Responsive<enum | string>` See full type | No default value |
| `py` | `Responsive<enum | string>` See full type | No default value |
| `pt` | `Responsive<enum | string>` See full type | No default value |
| `pr` | `Responsive<enum | string>` See full type | No default value |
| `pb` | `Responsive<enum | string>` See full type | No default value |
| `pl` | `Responsive<enum | string>` See full type | No default value |

### [Width](#width)

Width props accept any valid [CSS width value](https://developer.mozilla.org/en-US/docs/Web/CSS/width).

```
<Box width="100px" />



<Box width={{ md: '100vw', xl: '1400px' }} />
```

| Prop | Type | Default |
| --- | --- | --- |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | No default value |

### [Height](#height)

Height props accept any valid [CSS height value](https://developer.mozilla.org/en-US/docs/Web/CSS/height).

```
<Box height="100px" />



<Box height={{ md: '100vh', xl: '600px' }} />
```

| Prop | Type | Default |
| --- | --- | --- |
| `height` | `Responsive<string>` | No default value |
| `minHeight` | `Responsive<string>` | No default value |
| `maxHeight` | `Responsive<string>` | No default value |

### [Positioning](#positioning)

Positioning props can change how the element is placed relative to the normal flow of the document. As usual, the corresponding CSS values are accepted for each property, and the [space scale steps](/themes/docs/theme/spacing) can be used for the offset values.

```
<Box position="relative" />



<Box position={{ initial: "relative", lg: "sticky" }} />



<Box inset="4" />



<Box inset={{ initial: "0", xl: "auto" }} />



<Box left="4" />



<Box left={{ initial: "0", xl: "auto" }} />
```

| Prop | Type | Default |
| --- | --- | --- |
| `position` | `Responsive<enum>` See full type | No default value |
| `inset` | `Responsive<enum | string>` See full type | No default value |
| `top` | `Responsive<enum | string>` See full type | No default value |
| `right` | `Responsive<enum | string>` See full type | No default value |
| `bottom` | `Responsive<enum | string>` See full type | No default value |
| `left` | `Responsive<enum | string>` See full type | No default value |

### [Flex children](#flex-children)

Each layout component has props used to control the style when it is a child of a flex container.

```
<Box flexBasis="100%" />



<Box flexShrink="0">



<Box flexGrow={{ initial: "0", lg: "1" }} />
```

| Prop | Type | Default |
| --- | --- | --- |
| `flexBasis` | `Responsive<string>` | No default value |
| `flexShrink` | `Responsive<enum | string>` See full type | No default value |
| `flexGrow` | `Responsive<enum | string>` See full type | No default value |

### [Grid children](#grid-children)

Each layout component has props used to control the style when it is a child of a grid container.

```
<Box gridArea="header" />



<Box gridColumn="1 / 3" />



<Box gridColumnStart="2">



<Box gridColumnEnd={{ initial: "-1", md: "3", lg: "auto" }} />



<Box gridRow="1 / 3" />



<Box gridRowStart="2">



<Box gridRowEnd={{ initial: "-1", md: "3", lg: "auto" }} />
```

| Prop | Type | Default |
| --- | --- | --- |
| `gridArea` | `Responsive<string>` | No default value |
| `gridColumn` | `Responsive<string>` | No default value |
| `gridColumnStart` | `Responsive<string>` | No default value |
| `gridColumnEnd` | `Responsive<string>` | No default value |
| `gridRow` | `Responsive<string>` | No default value |
| `gridRowStart` | `Responsive<string>` | No default value |
| `gridRowEnd` | `Responsive<string>` | No default value |

## [Margin props](#margin-props)

Margin props are available on most components in order to provide spacing around the elements. They are not exclusive to layout components.

Margin props can access the [space scale steps](/themes/docs/theme/spacing) or accept any valid [CSS margin value](https://developer.mozilla.org/en-US/docs/Web/CSS/margin)

```
<Button m="4" />



<Button m="100px">



<Button m={{ sm: '6', lg: '9' }}>
```

| Prop | Type | Default |
| --- | --- | --- |
| `m` | `Responsive<enum | string>` See full type | No default value |
| `mx` | `Responsive<enum | string>` See full type | No default value |
| `my` | `Responsive<enum | string>` See full type | No default value |
| `mt` | `Responsive<enum | string>` See full type | No default value |
| `mr` | `Responsive<enum | string>` See full type | No default value |
| `mb` | `Responsive<enum | string>` See full type | No default value |
| `ml` | `Responsive<enum | string>` See full type | No default value |

The margin props may be unavailable on components that don’t render a HTML node or rely on their Root part for layout.

## [Standalone usage](#standalone-usage)

If needed, it’s possible to use *just* the layout component from Radix Themes. Just make sure that JavaScript tree-shaking works on your side, and import the CSS that powers the layout styles:

```
import "@radix-ui/themes/layout.css";
```

You’ll still have to wrap your app with `Theme` to provide the space scale and scaling factor settings.

#### Quick nav

Previous[Styling](/themes/docs/overview/styling)

Next[Releases](/themes/docs/overview/releases)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/overview/layout.mdx "Edit this page on GitHub.")
