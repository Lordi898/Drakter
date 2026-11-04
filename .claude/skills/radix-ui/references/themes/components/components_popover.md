Popover – Radix Themes

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

# Popover

Floating element for displaying rich content, triggered by a button.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/popover.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Popover] Issue)[View in Playground](/themes/playground#popover)

Comment

```
<Popover.Root>



<Popover.Trigger>



<Button variant="soft">



<ChatBubbleIcon width="16" height="16" />



Comment



</Button>



</Popover.Trigger>



<Popover.Content width="360px">



<Flex gap="3">



<Avatar
				size="2"
				src="https://images.unsplash.com/photo-1607346256330-dee7af15f7c5?&w=64&h=64&dpr=2&q=70&crop=focalpoint&fp-x=0.67&fp-y=0.5&fp-z=1.4&fit=crop"
				fallback="A"
				radius="full"
			/>



<Box flexGrow="1">



<TextArea placeholder="Write a comment…" style={{ height: 80 }} />



<Flex gap="3" mt="3" justify="between">



<Flex align="center" gap="2" asChild>



<Text as="label" size="2">



<Checkbox />



<Text>Send to group</Text>



</Text>



</Flex>



<Popover.Close>



<Button size="1">Comment</Button>



</Popover.Close>



</Flex>



</Box>



</Flex>



</Popover.Content>



</Popover.Root>
```

## [API Reference](#api-reference)

This component inherits props from the [Popover primitive](/primitives/docs/components/popover).

### [Root](#root)

Contains all the parts of a popover.

### [Trigger](#trigger)

Wraps the control that will open the popover.

### [Content](#content)

Contains content to be rendered in the open popover. This component is based on the `div` element.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3" | "4">` | `"2"` |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | `"480px"` |
| `height` | `Responsive<string>` | No default value |
| `minHeight` | `Responsive<string>` | No default value |
| `maxHeight` | `Responsive<string>` | No default value |

### [Close](#close)

Wraps the control that will close the popover.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control size of the popover. It will affect the `padding` and `border-radius` of the Content.
Use it in conjunction with the `width`/`minWidth`/`maxWidth` and `height`/`minHeight`/`maxHeight` props to control the size of the popover.

Size 1Size 2Size 3Size 4

```
<Flex gap="4" align="center">



<Popover.Root>



<Popover.Trigger>



<Button variant="soft">Size 1</Button>



</Popover.Trigger>



<Popover.Content size="1" maxWidth="300px">



<Text as="p" trim="both" size="1">



The quick brown fox jumps over the lazy dog.



</Text>



</Popover.Content>



</Popover.Root>



<Popover.Root>



<Popover.Trigger>



<Button variant="soft">Size 2</Button>



</Popover.Trigger>



<Popover.Content size="2" maxWidth="400px">



<Text as="p" trim="both" size="2">



The quick brown fox jumps over the lazy dog.



</Text>



</Popover.Content>



</Popover.Root>



<Popover.Root>



<Popover.Trigger>



<Button variant="soft">Size 3</Button>



</Popover.Trigger>



<Popover.Content size="3" maxWidth="500px">



<Text as="p" trim="both" size="3">



The quick brown fox jumps over the lazy dog.



</Text>



</Popover.Content>



</Popover.Root>



<Popover.Root>



<Popover.Trigger>



<Button variant="soft">Size 4</Button>



</Popover.Trigger>



<Popover.Content size="4">



<Text as="p" trim="both" size="4">



The quick brown fox jumps over the lazy dog.



</Text>



</Popover.Content>



</Popover.Root>



</Flex>
```

### [With inset content](#with-inset-content)

Use the [Inset](/themes/docs/components/inset) component to align content flush with the sides of the popover.

Share image

```
<Popover.Root>



<Popover.Trigger>



<Button variant="soft">



<Share2Icon width="16" height="16" />



Share image



</Button>



</Popover.Trigger>



<Popover.Content width="360px">



<Grid columns="130px 1fr">



<Inset side="left" pr="current">



<img
					src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?&auto=format&fit=crop&w=400&q=80"
					style={{ objectFit: "cover", width: "100%", height: "100%" }}
				/>



</Inset>



<div>



<Heading size="2" mb="1">



Share this image



</Heading>



<Text as="p" size="2" mb="4" color="gray">



Minimalistic 3D rendering wallpaper.



</Text>



<Flex direction="column" align="stretch">



<Popover.Close>



<Button size="1" variant="soft">



<Link1Icon width="16" height="16" />



Copy link



</Button>



</Popover.Close>



</Flex>



</div>



</Grid>



</Popover.Content>



</Popover.Root>
```

#### Quick nav

Previous[Inset](/themes/docs/components/inset)

Next[Progress](/themes/docs/components/progress)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/popover.mdx "Edit this page on GitHub.")
