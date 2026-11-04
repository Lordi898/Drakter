Card – Radix Themes

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

# Card

Container that groups related content and actions.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/card.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Card] Issue)[View in Playground](/themes/playground#card)

Teodros Girmay

Engineering

```
<Box maxWidth="240px">



<Card>



<Flex gap="3" align="center">



<Avatar
				size="3"
				src="https://images.unsplash.com/photo-1607346256330-dee7af15f7c5?&w=64&h=64&dpr=2&q=70&crop=focalpoint&fp-x=0.67&fp-y=0.5&fp-z=1.4&fit=crop"
				radius="full"
				fallback="T"
			/>



<Box>



<Text as="div" size="2" weight="bold">



Teodros Girmay



</Text>



<Text as="div" size="2" color="gray">



Engineering



</Text>



</Box>



</Flex>



</Card>



</Box>
```

## [API Reference](#api-reference)

This component is based on the `div` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3" | "4" | "5">` | `"1"` |
| `variant` Prop description | `"surface" | "classic" | "ghost"` | `"surface"` |

## [Examples](#examples)

### [As another element](#as-another-element)

Use the `asChild` prop to render the card as a link or a button. This prop adds styles for the interactive states, like hover and focus.

[Quick start

Start building your next project in minutes](#)

```
<Box maxWidth="350px">



<Card asChild>



<a href="#">



<Text as="div" size="2" weight="bold">



Quick start



</Text>



<Text as="div" color="gray" size="2">



Start building your next project in minutes



</Text>



</a>



</Card>



</Box>
```

### [Size](#size)

Use the `size` prop to control the size.

Teodros Girmay

Engineering

Teodros Girmay

Engineering

Teodros Girmay

Engineering

```
<Flex gap="3" direction="column">



<Box width="350px">



<Card size="1">



<Flex gap="3" align="center">



<Avatar size="3" radius="full" fallback="T" color="indigo" />



<Box>



<Text as="div" size="2" weight="bold">



Teodros Girmay



</Text>



<Text as="div" size="2" color="gray">



Engineering



</Text>



</Box>



</Flex>



</Card>



</Box>



<Box width="400px">



<Card size="2">



<Flex gap="4" align="center">



<Avatar size="4" radius="full" fallback="T" color="indigo" />



<Box>



<Text as="div" weight="bold">



Teodros Girmay



</Text>



<Text as="div" color="gray">



Engineering



</Text>



</Box>



</Flex>



</Card>



</Box>



<Box width="500px">



<Card size="3">



<Flex gap="4" align="center">



<Avatar size="5" radius="full" fallback="T" color="indigo" />



<Box>



<Text as="div" size="4" weight="bold">



Teodros Girmay



</Text>



<Text as="div" size="4" color="gray">



Engineering



</Text>



</Box>



</Flex>



</Card>



</Box>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

Quick start

Start building your next project in minutes

Quick start

Start building your next project in minutes

```
<Flex direction="column" gap="3" maxWidth="350px">



<Card variant="surface">



<Text as="div" size="2" weight="bold">



Quick start



</Text>



<Text as="div" color="gray" size="2">



Start building your next project in minutes



</Text>



</Card>



<Card variant="classic">



<Text as="div" size="2" weight="bold">



Quick start



</Text>



<Text as="div" color="gray" size="2">



Start building your next project in minutes



</Text>



</Card>



</Flex>
```

### [With inset content](#with-inset-content)

Use the [Inset](/themes/docs/components/inset) component to align content flush with the sides of the card.

![Bold typography](https://images.unsplash.com/photo-1617050318658-a9a3175e34cb?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=600&q=80)

**Typography** is the art and technique of arranging type to make written language legible, readable and appealing when displayed.

```
<Box maxWidth="240px">



<Card size="2">



<Inset clip="padding-box" side="top" pb="current">



<img
				src="https://images.unsplash.com/photo-1617050318658-a9a3175e34cb?ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D&auto=format&fit=crop&w=600&q=80"
				alt="Bold typography"
				style={{
					display: "block",
					objectFit: "cover",
					width: "100%",
					height: 140,
					backgroundColor: "var(--gray-5)",
				}}
			/>



</Inset>



<Text as="p" size="3">



<Strong>Typography</Strong> is the art and technique of arranging type to



make written language legible, readable and appealing when displayed.



</Text>



</Card>



</Box>
```

#### Quick nav

Previous[Callout](/themes/docs/components/callout)

Next[Checkbox](/themes/docs/components/checkbox)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/card.mdx "Edit this page on GitHub.")
