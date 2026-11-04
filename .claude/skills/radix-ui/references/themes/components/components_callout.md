Callout – Radix Themes

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

# Callout

Short message to attract user’s attention.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/callout.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Callout] Issue)[View in Playground](/themes/playground#callout)

You will need admin privileges to install and access this application.

```
<Callout.Root>



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need admin privileges to install and access this application.



</Callout.Text>



</Callout.Root>
```

## [API Reference](#api-reference)

### [Root](#root)

Groups Icon and Text parts. This component is based on the `div` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"soft" | "surface" | "outline"` | `"soft"` |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

### [Icon](#icon)

Provides width and height for the icon associated with the callout. This component is based on the `div` element.

### [Text](#text)

Renders the callout text. This component is based on the `p` element.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size.

You will need admin privileges to install and access this application.

You will need admin privileges to install and access this application.

You will need admin privileges to install and access this application.

```
<Flex direction="column" gap="3" align="start">



<Callout.Root size="1">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need admin privileges to install and access this application.



</Callout.Text>



</Callout.Root>



<Callout.Root size="2">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need admin privileges to install and access this application.



</Callout.Text>



</Callout.Root>



<Callout.Root size="3">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need admin privileges to install and access this application.



</Callout.Text>



</Callout.Root>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style.

You will need [admin privileges](#) to install and access this application.

You will need [admin privileges](#) to install and access this application.

You will need [admin privileges](#) to install and access this application.

```
<Flex direction="column" gap="3">



<Callout.Root variant="soft">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need <Link href="#">admin privileges</Link> to install and access



this application.



</Callout.Text>



</Callout.Root>



<Callout.Root variant="surface">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need <Link href="#">admin privileges</Link> to install and access



this application.



</Callout.Text>



</Callout.Root>



<Callout.Root variant="outline">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need <Link href="#">admin privileges</Link> to install and access



this application.



</Callout.Text>



</Callout.Root>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color).

You will need [admin privileges](#) to install and access this application.

You will need [admin privileges](#) to install and access this application.

You will need [admin privileges](#) to install and access this application.

```
<Flex direction="column" gap="3">



<Callout.Root color="blue">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need <Link href="#">admin privileges</Link> to install and access



this application.



</Callout.Text>



</Callout.Root>



<Callout.Root color="green">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need <Link href="#">admin privileges</Link> to install and access



this application.



</Callout.Text>



</Callout.Root>



<Callout.Root color="red">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



You will need <Link href="#">admin privileges</Link> to install and access



this application.



</Callout.Text>



</Callout.Root>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `HighContrast` prop to add additional contrast.

An update to Radix Themes is available. See what’s new in version 3.2.0.

An update to Radix Themes is available. See what’s new in version 3.2.0.

```
<Flex direction="column" gap="3">



<Callout.Root color="gray" variant="soft">



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



An update to Radix Themes is available. See what’s new in version 3.2.0.



</Callout.Text>



</Callout.Root>



<Callout.Root color="gray" variant="soft" highContrast>



<Callout.Icon>



<InfoCircledIcon />



</Callout.Icon>



<Callout.Text>



An update to Radix Themes is available. See what’s new in version 3.2.0.



</Callout.Text>



</Callout.Root>



</Flex>
```

### [As alert](#as-alert)

Add a native [WAI-ARIA `alert` role](https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Roles/alert_role) to the callout when the user’s immediate attention is required, like when an error message appears. The screen reader will be interrupted, announcing the new content immediately.

Access denied. Please contact the network administrator to view this page.

```
<Callout.Root color="red" role="alert">



<Callout.Icon>



<ExclamationTriangleIcon />



</Callout.Icon>



<Callout.Text>



Access denied. Please contact the network administrator to view this page.



</Callout.Text>



</Callout.Root>
```

#### Quick nav

Previous[Button](/themes/docs/components/button)

Next[Card](/themes/docs/components/card)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/callout.mdx "Edit this page on GitHub.")
