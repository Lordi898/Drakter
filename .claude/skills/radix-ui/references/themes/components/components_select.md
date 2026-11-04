Select – Radix Themes

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

# Select

Displays a list of options for the user to pick from—triggered by a button.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/select.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Select] Issue)[View in Playground](/themes/playground#select)

```
<Select.Root defaultValue="apple">



<Select.Trigger />



<Select.Content>



<Select.Group>



<Select.Label>Fruits</Select.Label>



<Select.Item value="orange">Orange</Select.Item>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="grape" disabled>



Grape



</Select.Item>



</Select.Group>



<Select.Separator />



<Select.Group>



<Select.Label>Vegetables</Select.Label>



<Select.Item value="carrot">Carrot</Select.Item>



<Select.Item value="potato">Potato</Select.Item>



</Select.Group>



</Select.Content>



</Select.Root>
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of a select. It inherits props from the Select primitive [Root](/primitives/docs/components/select#root) part.

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |

### [Trigger](#trigger)

The button that toggles the select. This component inherits props from the Select primitive [Trigger](/primitives/docs/components/select#trigger) and [Value](/primitives/docs/components/select#value) parts. It supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `variant` Prop description | `"classic" | "surface" | "soft" | "ghost"` | `"surface"` |
| `color` Prop description | `enum` See full type | No default value |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |
| `placeholder` | `string` | No default value |

### [Content](#content)

The component that pops out when the select is open. It inherits props from the [Select.Portal primitive](/primitives/docs/components/select#portal) and [Select.Content primitive](/primitives/docs/components/select#content) parts.

| Prop | Type | Default |
| --- | --- | --- |
| `variant` Prop description | `"solid" | "soft"` | `"solid"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

### [Item](#item)

The component that contains the select items. It inherits props from the [Select.Item primitive](/primitives/docs/components/select#item) part.

### [Group](#group)

Used to group multiple items. It inherits props from the [Select.Group primitive](/primitives/docs/components/select#group) part. Use in conjunction with `Select.Label` to ensure good accessibility via automatic labelling.

### [Label](#label)

Used to render the label of a group, it isn't focusable using arrow keys. It inherits props from the [Select.Label primitive](/primitives/docs/components/select#label) part.

### [Separator](#separator)

Used to visually separate items in the Select. It inherits props from the [Select.Separator primitive](/primitives/docs/components/select#separator) part.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

```
<Flex gap="3" align="center">



<Select.Root size="1" defaultValue="apple">



<Select.Trigger />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root size="2" defaultValue="apple">



<Select.Trigger />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root size="3" defaultValue="apple">



<Select.Trigger />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop on `Trigger` and `Content` to customize the visual style.

```
<Flex gap="3" align="center">



<Select.Root defaultValue="apple">



<Select.Trigger variant="surface" />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger variant="classic" />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger variant="soft" />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



</Flex>
```

#### Ghost

Use the `ghost` trigger variant to render the trigger without a visually containing element. Ghost triggers behave differently in layout as they use a negative margin to optically align themselves against their siblings while maintaining their padded active and hover states.

```
<Flex gap="3" align="center">



<Select.Root defaultValue="apple">



<Select.Trigger variant="surface" />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger variant="ghost" />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



</Flex>
```

### [Color](#color)

Use the `color` prop on `Trigger` and `Content` to assign a specific color value.

```
<Flex gap="3">



<Select.Root defaultValue="apple">



<Select.Trigger color="indigo" variant="soft" />



<Select.Content color="indigo">



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger color="cyan" variant="soft" />



<Select.Content color="cyan">



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger color="orange" variant="soft" />



<Select.Content color="orange">



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger color="crimson" variant="soft" />



<Select.Content color="crimson">



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop on `Content` to increase item contrast.

```
<Flex gap="3">



<Select.Root defaultValue="apple">



<Select.Trigger color="gray" />



<Select.Content color="gray" variant="solid">



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger color="gray" />



<Select.Content color="gray" variant="solid" highContrast>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



</Flex>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

```
<Flex gap="3">



<Select.Root defaultValue="apple">



<Select.Trigger radius="none" />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger radius="large" />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



<Select.Root defaultValue="apple">



<Select.Trigger radius="full" />



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



</Flex>
```

### [Placeholder](#placeholder)

Use the `placeholder` prop to create a `Trigger` that doesn’t need an initial value.

Pick a fruit

```
<Select.Root>



<Select.Trigger placeholder="Pick a fruit" />



<Select.Content>



<Select.Group>



<Select.Label>Fruits</Select.Label>



<Select.Item value="orange">Orange</Select.Item>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="grape" disabled>



Grape



</Select.Item>



</Select.Group>



<Select.Separator />



<Select.Group>



<Select.Label>Vegetables</Select.Label>



<Select.Item value="carrot">Carrot</Select.Item>



<Select.Item value="potato">Potato</Select.Item>



</Select.Group>



</Select.Content>



</Select.Root>
```

### [Position](#position)

Set `position="popper"` prop to position the select menu below the trigger.

```
<Select.Root defaultValue="apple">



<Select.Trigger />



<Select.Content position="popper">



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>
```

### [With SSR](#with-ssr)

When using server-side rendering, you might notice a layout shift after hydration. This is because Trigger executes client-side code to display the selected item’s text. To avoid that layout shift, you can render it manually by mapping values.

Apple

```
() => {



const data = {



apple: "Apple",



orange: "Orange",



};



const [value, setValue] = React.useState("apple");



return (



<Select.Root value={value} onValueChange={setValue}>



<Select.Trigger>{data[value]}</Select.Trigger>



<Select.Content>



<Select.Item value="apple">Apple</Select.Item>



<Select.Item value="orange">Orange</Select.Item>



</Select.Content>



</Select.Root>



);



};
```

### [With an icon](#with-an-icon)

You can customise how Trigger renders the value by controlling its children manually. For example, you can render an icon next to the selected item’s text.

Light

```
() => {



const data = {



light: { label: "Light", icon: <SunIcon /> },



dark: { label: "Dark", icon: <MoonIcon /> },



};



const [value, setValue] = React.useState("light");



return (



<Flex direction="column" maxWidth="160px">



<Select.Root value={value} onValueChange={setValue}>



<Select.Trigger>



<Flex as="span" align="center" gap="2">



{data[value].icon}



{data[value].label}



</Flex>



</Select.Trigger>



<Select.Content position="popper">



<Select.Item value="light">Light</Select.Item>



<Select.Item value="dark">Dark</Select.Item>



</Select.Content>



</Select.Root>



</Flex>



);



};
```

#### Quick nav

Previous[Segmented Control](/themes/docs/components/segmented-control)

Next[Separator](/themes/docs/components/separator)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/select.mdx "Edit this page on GitHub.")
