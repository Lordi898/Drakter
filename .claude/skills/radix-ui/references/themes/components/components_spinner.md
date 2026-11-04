Spinner – Radix Themes

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

# Spinner

Displays an animated loading indicator.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/spinner.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Spinner] Issue)[View in Playground](/themes/playground#spinner)

```
<Spinner />
```

## [API Reference](#api-reference)

This component is based on the `span` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `loading` Prop description | `boolean` | `true` |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the spinner.

```
<Flex align="center" gap="4">



<Spinner size="1" />



<Spinner size="2" />



<Spinner size="3" />



</Flex>
```

### [With children](#with-children)

Use the `loading` prop to control whether the spinner or its children are displayed. Spinner preserves the dimensions of children when they are hidden and disables interactive elements.

```
<Flex gap="4">



<Spinner loading={true}>



<Switch defaultChecked />



</Spinner>



<Spinner loading={false}>



<Switch defaultChecked />



</Spinner>



</Flex>
```

### [With buttons](#with-buttons)

[Buttons](/themes/docs/components/button) have their own `loading` prop that automatically composes a spinner.

BookmarkBookmark

```
<Button loading>Bookmark</Button>
```

If you have an icon inside the button, you can use the button’s `disabled` state and wrap the icon in a standalone `<Spinner>` to achieve a more sophisticated design.

Bookmark

```
<Button disabled>



<Spinner loading>



<BookmarkIcon />



</Spinner>



Bookmark



</Button>
```

#### Quick nav

Previous[Slider](/themes/docs/components/slider)

Next[Switch](/themes/docs/components/switch)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/spinner.mdx "Edit this page on GitHub.")
