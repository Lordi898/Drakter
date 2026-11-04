Button – Radix Themes

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

# Button

Trigger an action or event, such as submitting a form or displaying a dialog.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/button.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Button] Issue)[View in Playground](/themes/playground#button)

Bookmark

```
<Button>



<BookmarkIcon /> Bookmark



</Button>
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

Edit profileEdit profileEdit profile

```
<Flex gap="3" align="center">



<Button size="1" variant="soft">



Edit profile



</Button>



<Button size="2" variant="soft">



Edit profile



</Button>



<Button size="3" variant="soft">



Edit profile



</Button>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style of the button.

Edit profileEdit profileEdit profileEdit profileEdit profile

```
<Flex align="center" gap="3">



<Button variant="classic">Edit profile</Button>



<Button variant="solid">Edit profile</Button>



<Button variant="soft">Edit profile</Button>



<Button variant="surface">Edit profile</Button>



<Button variant="outline">Edit profile</Button>



</Flex>
```

#### Ghost

Use the `ghost` variant to display a button without chrome. Ghost buttons behave like text in layout, as they use a negative margin to optically align themselves against their siblings while maintaining the padding in active and hover states.

Edit profile

```
<Button variant="ghost">Edit profile</Button>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

Edit profileEdit profileEdit profileEdit profile

```
<Flex gap="3">



<Button color="indigo" variant="soft">



Edit profile



</Button>



<Button color="cyan" variant="soft">



Edit profile



</Button>



<Button color="orange" variant="soft">



Edit profile



</Button>



<Button color="crimson" variant="soft">



Edit profile



</Button>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

Edit profileEdit profileEdit profileEdit profileEdit profile

Edit profileEdit profileEdit profileEdit profileEdit profile

```
<Flex direction="column" gap="3">



<Flex gap="3">



<Button color="gray" variant="classic">



Edit profile



</Button>



<Button color="gray" variant="solid">



Edit profile



</Button>



<Button color="gray" variant="soft">



Edit profile



</Button>



<Button color="gray" variant="surface">



Edit profile



</Button>



<Button color="gray" variant="outline">



Edit profile



</Button>



</Flex>



<Flex gap="3">



<Button color="gray" variant="classic" highContrast>



Edit profile



</Button>



<Button color="gray" variant="solid" highContrast>



Edit profile



</Button>



<Button color="gray" variant="soft" highContrast>



Edit profile



</Button>



<Button color="gray" variant="surface" highContrast>



Edit profile



</Button>



<Button color="gray" variant="outline" highContrast>



Edit profile



</Button>



</Flex>



</Flex>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

Edit profileEdit profileEdit profile

```
<Flex gap="3">



<Button radius="none" variant="soft">



Edit profile



</Button>



<Button radius="large" variant="soft">



Edit profile



</Button>



<Button radius="full" variant="soft">



Edit profile



</Button>



</Flex>
```

### [With icons](#with-icons)

You can nest icons directly inside the button. An appropriate gap is provided automatically.

Bookmark Bookmark Bookmark Bookmark Bookmark

```
<Flex gap="3">



<Button variant="classic">



<BookmarkIcon /> Bookmark



</Button>



<Button variant="solid">



<BookmarkIcon /> Bookmark



</Button>



<Button variant="soft">



<BookmarkIcon /> Bookmark



</Button>



<Button variant="surface">



<BookmarkIcon /> Bookmark



</Button>



<Button variant="outline">



<BookmarkIcon /> Bookmark



</Button>



</Flex>
```

### [Loading](#loading)

Use the `loading` prop to display a loading spinner in place of button content, preserving the original size of the button in its normal state. The button will be disabled while loading.

BookmarkBookmarkBookmarkBookmarkBookmarkBookmarkBookmarkBookmarkBookmarkBookmark

```
<Flex gap="3">



<Button loading variant="classic">



Bookmark



</Button>



<Button loading variant="solid">



Bookmark



</Button>



<Button loading variant="soft">



Bookmark



</Button>



<Button loading variant="surface">



Bookmark



</Button>



<Button loading variant="outline">



Bookmark



</Button>



</Flex>
```

If you have an icon inside the button, you can use the button’s `disabled` state and wrap the icon in a standalone [Spinner](/themes/docs/components/spinner) to achieve a more sophisticated design.

BookmarkBookmarkBookmarkBookmarkBookmark

```
<Flex gap="3">



<Button disabled variant="classic">



<Spinner loading>



<BookmarkIcon />



</Spinner>



Bookmark



</Button>



<Button disabled variant="solid">



<Spinner loading>



<BookmarkIcon />



</Spinner>



Bookmark



</Button>



<Button disabled variant="soft">



<Spinner loading>



<BookmarkIcon />



</Spinner>



Bookmark



</Button>



<Button disabled variant="surface">



<Spinner loading>



<BookmarkIcon />



</Spinner>



Bookmark



</Button>



<Button disabled variant="outline">



<Spinner loading>



<BookmarkIcon />



</Spinner>



Bookmark



</Button>



</Flex>
```

#### Quick nav

Previous[Badge](/themes/docs/components/badge)

Next[Callout](/themes/docs/components/callout)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/button.mdx "Edit this page on GitHub.")
