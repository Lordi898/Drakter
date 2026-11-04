Hover Card – Radix Themes

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

# Hover Card

For sighted users to preview content available behind a link.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/hover-card.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[HoverCard] Issue)[View in Playground](/themes/playground#hover-card)

Follow [@radix\_ui](https://twitter.com/radix_ui) for updates.

```
<Text>



Follow{" "}



<HoverCard.Root>



<HoverCard.Trigger>



<Link href="https://twitter.com/radix_ui" target="_blank">



@radix_ui



</Link>



</HoverCard.Trigger>



<HoverCard.Content maxWidth="300px">



<Flex gap="4">



<Avatar
					size="3"
					fallback="R"
					radius="full"
					src="https://pbs.twimg.com/profile_images/1337055608613253126/r_eiMp2H_400x400.png"
				/>



<Box>



<Heading size="3" as="h3">



Radix



</Heading>



<Text as="div" size="2" color="gray" mb="2">



@radix_ui



</Text>



<Text as="div" size="2">



React components, icons, and colors for building high-quality,



accessible UI.



</Text>



</Box>



</Flex>



</HoverCard.Content>



</HoverCard.Root>{" "}



for updates.



</Text>
```

## [API Reference](#api-reference)

This component inherits props from the [Hover Card primitive](/primitives/docs/components/hover-card).

### [Root](#root)

Contains all the parts of the hover card.

### [Trigger](#trigger)

Wraps the link that will open the hover card.

### [Content](#content)

Contains the content of the open hover card. This component is based on the `div` element.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | `"480px"` |
| `height` | `Responsive<string>` | No default value |
| `minHeight` | `Responsive<string>` | No default value |
| `maxHeight` | `Responsive<string>` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

[Size 1](#)[Size 2](#)[Size 3](#)

```
<Flex gap="4">



<HoverCard.Root>



<HoverCard.Trigger>



<Link href="#">Size 1</Link>



</HoverCard.Trigger>



<HoverCard.Content size="1" maxWidth="240px">



<Text as="div" size="1" trim="both">



<Strong>Typography</Strong> is the art and technique of arranging type



to make written language legible, readable and appealing when displayed.



</Text>



</HoverCard.Content>



</HoverCard.Root>



<HoverCard.Root>



<HoverCard.Trigger>



<Link href="#">Size 2</Link>



</HoverCard.Trigger>



<HoverCard.Content size="2" maxWidth="280px">



<Text as="div" size="2" trim="both">



<Strong>Typography</Strong> is the art and technique of arranging type



to make written language legible, readable and appealing when displayed.



</Text>



</HoverCard.Content>



</HoverCard.Root>



<HoverCard.Root>



<HoverCard.Trigger>



<Link href="#">Size 3</Link>



</HoverCard.Trigger>



<HoverCard.Content size="3" maxWidth="320px">



<Text as="div" size="3" trim="both">



<Strong>Typography</Strong> is the art and technique of arranging type



to make written language legible, readable and appealing when displayed.



</Text>



</HoverCard.Content>



</HoverCard.Root>



</Flex>
```

### [With inset content](#with-inset-content)

Use the [Inset](/themes/docs/components/inset) component to align content flush with the sides of the hover card.

Technology revolutionized [typography](#) in the latter twentieth century.

```
<Text>



Technology revolutionized{" "}



<HoverCard.Root>



<HoverCard.Trigger>



<Link href="#">typography</Link>



</HoverCard.Trigger>



<HoverCard.Content width="450px">



<Flex>



<Box asChild flexShrink="0">



<Inset side="left" pr="current">



<img
							src="https://images.unsplash.com/photo-1617050318658-a9a3175e34cb?&auto=format&fit=crop&w=300&q=90"
							alt="Bold typography"
							style={{
								display: "block",
								objectFit: "cover",
								height: "100%",
								width: 150,
								backgroundColor: "var(--gray-5)",
							}}
						/>



</Inset>



</Box>



<Text size="2" as="p">



<Strong>Typography</Strong> is the art and technique of arranging type



to make written language legible, readable and appealing when



displayed. The arrangement of type involves selecting typefaces, point



sizes, line lengths, line-spacing (leading), and letter-spacing



(tracking)…



</Text>



</Flex>



</HoverCard.Content>



</HoverCard.Root>{" "}



in the latter twentieth century.



</Text>
```

#### Quick nav

Previous[Dropdown Menu](/themes/docs/components/dropdown-menu)

Next[Icon Button](/themes/docs/components/icon-button)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/hover-card.mdx "Edit this page on GitHub.")
