Checkbox Cards – Radix Themes

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

# Checkbox Cards

Set of interactive cards where multiple options can be selected at a time.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/checkbox-cards.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[CheckboxCards] Issue)[View in Playground](/themes/playground#checkbox-cards)

A1 KeyboardUS Layout

Pro MouseZero-lag wireless

Lightning MatWireless charging

```
<Box maxWidth="600px">



<CheckboxCards.Root defaultValue={["1"]} columns={{ initial: "1", sm: "3" }}>



<CheckboxCards.Item value="1">



<Flex direction="column" width="100%">



<Text weight="bold">A1 Keyboard</Text>



<Text>US Layout</Text>



</Flex>



</CheckboxCards.Item>



<CheckboxCards.Item value="2">



<Flex direction="column" width="100%">



<Text weight="bold">Pro Mouse</Text>



<Text>Zero-lag wireless</Text>



</Flex>



</CheckboxCards.Item>



<CheckboxCards.Item value="3">



<Flex direction="column" width="100%">



<Text weight="bold">Lightning Mat</Text>



<Text>Wireless charging</Text>



</Flex>



</CheckboxCards.Item>



</CheckboxCards.Root>



</Box>
```

## [API Reference](#api-reference)

This component is based on the `div` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

### [Root](#root)

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"surface" | "classic"` | `"surface"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |
| `columns` | `Responsive<enum | string>` See full type | `"repeat(auto-fit, minmax(200px, 1fr))"` |
| `gap` | `Responsive<enum | string>` See full type | `"4"` |

### [Item](#item)

An item in the group that can be checked.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

Agree to Terms

Agree to Terms

Agree to Terms

```
<Flex align="center" gap="3">



<CheckboxCards.Root defaultValue={["1"]} size="1">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} size="2">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} size="3">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

Agree to Terms

Agree to Terms

```
<Flex direction="column" gap="3" maxWidth="200px">



<CheckboxCards.Root defaultValue={["1"]} variant="surface">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} variant="classic">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

Agree to Terms

Agree to Terms

Agree to Terms

Agree to Terms

```
<Flex direction="column" gap="3" maxWidth="200px">



<CheckboxCards.Root defaultValue={["1"]} color="indigo">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="cyan">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="orange">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="crimson">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

Agree to Terms

Agree to Terms

Agree to Terms

Agree to Terms

Agree to Terms

Agree to Terms

Agree to Terms

Agree to Terms

```
<Grid columns="2" gap="3" display="inline-grid">



<CheckboxCards.Root defaultValue={["1"]} color="indigo">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="indigo" highContrast>



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="cyan">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="cyan" highContrast>



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="orange">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="orange" highContrast>



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="crimson">



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root defaultValue={["1"]} color="crimson" highContrast>



<CheckboxCards.Item value="1">Agree to Terms</CheckboxCards.Item>



</CheckboxCards.Root>



</Grid>
```

### [Disabled](#disabled)

OffOn

OffOn

```
<Flex direction="column" gap="4" maxWidth="450px">



<CheckboxCards.Root columns="2" defaultValue="2">



<CheckboxCards.Item value="1">Off</CheckboxCards.Item>



<CheckboxCards.Item value="2">On</CheckboxCards.Item>



</CheckboxCards.Root>



<CheckboxCards.Root columns="2" defaultValue="2">



<CheckboxCards.Item value="1" disabled>



Off



</CheckboxCards.Item>



<CheckboxCards.Item value="2" disabled>



On



</CheckboxCards.Item>



</CheckboxCards.Root>



</Flex>
```

#### Quick nav

Previous[Checkbox Group](/themes/docs/components/checkbox-group)

Next[Context Menu](/themes/docs/components/context-menu)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/checkbox-cards.mdx "Edit this page on GitHub.")
