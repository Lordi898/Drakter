Avatar – Radix Themes

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

# Avatar

Profile picture, user initials or fallback icon.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/avatar.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Avatar] Issue)[View in Playground](/themes/playground#avatar)

```
<Flex gap="2">



<Avatar
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



<Avatar fallback="A" />



</Flex>
```

## [API Reference](#api-reference)

This component inherits props from the [Avatar primitive](/primitives/docs/components/avatar).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<enum>` See full type | `"3"` |
| `variant` Prop description | `"solid" | "soft"` | `"soft"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |
| `fallback*` Prop description | `ReactNode` | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the avatar.

```
<Flex align="center" gap="4">



<Avatar
		size="1"
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



<Avatar
		size="2"
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



<Avatar
		size="3"
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



<Avatar
		size="4"
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



<Avatar
		size="5"
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



<Avatar
		size="6"
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



<Avatar
		size="7"
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



<Avatar
		size="8"
		src="https://images.unsplash.com/photo-1502823403499-6ccfcf4fb453?&w=256&h=256&q=70&crop=focalpoint&fp-x=0.5&fp-y=0.3&fp-z=1&fit=crop"
		fallback="A"
	/>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style of the avatar.

```
<Flex gap="2">



<Avatar variant="solid" fallback="A" />



<Avatar variant="soft" fallback="A" />



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

```
<Flex gap="2">



<Avatar variant="solid" color="indigo" fallback="A" />



<Avatar variant="solid" color="cyan" fallback="A" />



<Avatar variant="solid" color="orange" fallback="A" />



<Avatar variant="solid" color="crimson" fallback="A" />



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

```
<Grid rows="2" gap="2" display="inline-grid" flow="column">



<Avatar variant="solid" color="indigo" fallback="A" />



<Avatar variant="solid" color="indigo" fallback="A" highContrast />



<Avatar variant="solid" color="cyan" fallback="A" />



<Avatar variant="solid" color="cyan" fallback="A" highContrast />



<Avatar variant="solid" color="orange" fallback="A" />



<Avatar variant="solid" color="orange" fallback="A" highContrast />



<Avatar variant="solid" color="crimson" fallback="A" />



<Avatar variant="solid" color="crimson" fallback="A" highContrast />



<Avatar variant="solid" color="gray" fallback="A" />



<Avatar variant="solid" color="gray" fallback="A" highContrast />



</Grid>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

```
<Flex gap="2">



<Avatar radius="none" fallback="A" />



<Avatar radius="large" fallback="A" />



<Avatar radius="full" fallback="A" />



</Flex>
```

### [Fallback](#fallback)

Use the `fallback` prop to modify the rendered fallback element.

```
<Flex gap="2">



<Avatar fallback="A" />



<Avatar fallback="AB" />



<Avatar
		fallback={
			<Box width="24px" height="24px">
				<svg viewBox="0 0 64 64" fill="currentColor">
					<path d="M41.5 14c4.687 0 8.5 4.038 8.5 9s-3.813 9-8.5 9S33 27.962 33 23 36.813 14 41.5 14zM56.289 43.609C57.254 46.21 55.3 49 52.506 49c-2.759 0-11.035 0-11.035 0 .689-5.371-4.525-10.747-8.541-13.03 2.388-1.171 5.149-1.834 8.07-1.834C48.044 34.136 54.187 37.944 56.289 43.609zM37.289 46.609C38.254 49.21 36.3 52 33.506 52c-5.753 0-17.259 0-23.012 0-2.782 0-4.753-2.779-3.783-5.392 2.102-5.665 8.245-9.472 15.289-9.472S35.187 40.944 37.289 46.609zM21.5 17c4.687 0 8.5 4.038 8.5 9s-3.813 9-8.5 9S13 30.962 13 26 16.813 17 21.5 17z" />
				</svg>
			</Box>
		}
	/>



</Flex>
```

#### Quick nav

Previous[Aspect Ratio](/themes/docs/components/aspect-ratio)

Next[Badge](/themes/docs/components/badge)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/avatar.mdx "Edit this page on GitHub.")
