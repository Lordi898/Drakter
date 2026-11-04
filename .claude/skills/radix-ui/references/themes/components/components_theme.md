Theme – Radix Themes

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

# Theme

Wraps all or part of a React tree to provide theme configuration.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/theme.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Theme] Issue)

## [API Reference](#api-reference)

For an overview of theming see the [overview page](/themes/docs/theme/overview).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `hasBackground` Prop description | `boolean` | `true` |
| `appearance` Prop description | `"inherit" | "light" | "dark"` | `"inherit"` |
| `accentColor` Prop description | `enum` See full type | `"indigo"` |
| `grayColor` Prop description | `enum` See full type | `"auto"` |
| `panelBackground` | `"solid" | "translucent"` | `"translucent"` |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | `"medium"` |
| `scaling` Prop description | `"90%" | "95%" | "100%" | "105%" | "110%"` | `"100%"` |

## [Examples](#examples)

### [Basic configuration](#basic-configuration)

Wrap a component tree in the `Theme` component to provide or modify configuration for all children.

Feedback

Attach screenshot?

BackSend

```
<Box maxWidth="400px">



<Card size="2">



<Flex direction="column" gap="3">



<Grid gap="1">



<Text as="div" weight="bold" size="2" mb="1">



Feedback



</Text>



<TextArea placeholder="Write your feedback…" />



</Grid>



<Flex asChild justify="between">



<label>



<Text color="gray" size="2">



Attach screenshot?



</Text>



<Switch size="1" defaultChecked />



</label>



</Flex>



<Grid columns="2" gap="2">



<Button variant="surface">Back</Button>



<Button>Send</Button>



</Grid>



</Flex>



</Card>



</Box>
```

### [Nesting](#nesting)

Nest another theme to modify configuration for a specific subtree. Configuration is inherited from the parent.

##### Global

Feedback

Send

##### Child

Feedback

Send

##### Grandchild

Feedback

Send

```
<Card size="2">



<Flex gap="6">



<Flex direction="column" gap="3">



<Heading as="h5" size="2">



Global



</Heading>



<Grid gap="1">



<Text as="div" weight="bold" size="2" mb="1">



Feedback



</Text>



<TextArea placeholder="Write your feedback…" />



</Grid>



<Button>Send</Button>



</Flex>



<Theme accentColor="cyan" radius="full">



<Card size="2">



<Flex gap="6">



<Flex direction="column" gap="3">



<Heading as="h5" size="2">



Child



</Heading>



<Grid gap="1">



<Text as="div" weight="bold" size="2" mb="1">



Feedback



</Text>



<TextArea placeholder="Write your feedback…" />



</Grid>



<Button>Send</Button>



</Flex>



<Theme accentColor="orange">



<Card size="2">



<Flex direction="column" gap="3">



<Heading as="h5" size="2">



Grandchild



</Heading>



<Grid gap="1">



<Text as="div" weight="bold" size="2" mb="1">



Feedback



</Text>



<TextArea placeholder="Write your feedback…" />



</Grid>



<Button>Send</Button>



</Flex>



</Card>



</Theme>



</Flex>



</Card>



</Theme>



</Flex>



</Card>
```

### [Component overrides](#component-overrides)

Override configuration per component by passing any supported prop directly to that component.

Feedback

Attach screenshot?

BackSend

```
<Box maxWidth="400px">



<Card size="2">



<Flex direction="column" gap="3">



<Grid gap="1">



<Text as="div" weight="bold" size="2" mb="1">



Feedback



</Text>



<TextArea placeholder="Write your feedback…" />



</Grid>



<Flex asChild justify="between">



<label>



<Text color="gray" size="2">



Attach screenshot?



</Text>



<Switch
						size="1"
						color="orange"
						radius="full"
						defaultChecked
					/>



</label>



</Flex>



<Grid columns="2" gap="2">



<Button variant="surface">Back</Button>



<Button color="cyan" radius="full">



Send



</Button>



</Grid>



</Flex>



</Card>



</Box>
```

#### Quick nav

Previous[Slot](/themes/docs/components/slot)

Next[Visually Hidden](/themes/docs/components/visually-hidden)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/theme.mdx "Edit this page on GitHub.")
