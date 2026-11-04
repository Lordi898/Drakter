Tabs – Radix Themes

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

# Tabs

Set of content sections to be displayed one at a time.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/tabs.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Tabs] Issue)[View in Playground](/themes/playground#tabs)

AccountAccountDocumentsDocumentsSettingsSettings

Make changes to your account.

```
<Tabs.Root defaultValue="account">



<Tabs.List>



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



<Box pt="3">



<Tabs.Content value="account">



<Text size="2">Make changes to your account.</Text>



</Tabs.Content>



<Tabs.Content value="documents">



<Text size="2">Access and update your documents.</Text>



</Tabs.Content>



<Tabs.Content value="settings">



<Text size="2">Edit your profile or update contact information.</Text>



</Tabs.Content>



</Box>



</Tabs.Root>
```

## [API Reference](#api-reference)

This component inherits props from the [Tabs primitive](/primitives/docs/components/tabs) and supports [common margin props](/themes/docs/overview/layout#margin-props).

### [Root](#root)

Contains all component parts.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |

### [List](#list)

Contains the triggers that sit alongside the active content.

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2">` | `"2"` |
| `wrap` | `Responsive<"nowrap" | "wrap" | "wrap-reverse">` | No default value |
| `justify` | `Responsive<"start" | "center" | "end">` | No default value |
| `color` Prop description | `enum` See full type | No default value |
| `highContrast` Prop description | `boolean` | No default value |

### [Trigger](#trigger)

The button that activates its associated content.

### [Content](#content)

Contains the content associated with each trigger.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the tab list.

AccountAccountDocumentsDocumentsSettingsSettings

AccountAccountDocumentsDocumentsSettingsSettings

```
<Flex direction="column" gap="4" pb="2">



<Tabs.Root defaultValue="account">



<Tabs.List size="1">



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



</Tabs.Root>



<Tabs.Root defaultValue="account">



<Tabs.List size="2">



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



</Tabs.Root>



</Flex>
```

### [Color](#color)

Use the `color` prop to assign a specific [color](/themes/docs/theme/color) to the tab list.

AccountAccountDocumentsDocumentsSettingsSettings

AccountAccountDocumentsDocumentsSettingsSettings

AccountAccountDocumentsDocumentsSettingsSettings

AccountAccountDocumentsDocumentsSettingsSettings

```
<Flex direction="column" gap="4" pb="2">



<Tabs.Root defaultValue="account">



<Tabs.List color="indigo">



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



</Tabs.Root>



<Tabs.Root defaultValue="account">



<Tabs.List color="cyan">



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



</Tabs.Root>



<Tabs.Root defaultValue="account">



<Tabs.List color="orange">



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



</Tabs.Root>



<Tabs.Root defaultValue="account">



<Tabs.List color="crimson">



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



</Tabs.Root>



</Flex>
```

### [High-contrast](#high-contrast)

Use the `highContrast` prop to increase color contrast with the background.

AccountAccountDocumentsDocumentsSettingsSettings

AccountAccountDocumentsDocumentsSettingsSettings

```
<Flex direction="column" gap="4" pb="2">



<Tabs.Root defaultValue="account">



<Tabs.List color="gray">



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



</Tabs.Root>



<Tabs.Root defaultValue="account">



<Tabs.List color="gray" highContrast>



<Tabs.Trigger value="account">Account</Tabs.Trigger>



<Tabs.Trigger value="documents">Documents</Tabs.Trigger>



<Tabs.Trigger value="settings">Settings</Tabs.Trigger>



</Tabs.List>



</Tabs.Root>



</Flex>
```

### [Navigation](#navigation)

Tabs should not be used for page navigation. Use [Tab Nav](/themes/docs/components/tab-nav) instead, which is designed for this purpose and has equivalent styles.

#### Quick nav

Previous[Table](/themes/docs/components/table)

Next[Tab Nav](/themes/docs/components/tab-nav)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/tabs.mdx "Edit this page on GitHub.")
