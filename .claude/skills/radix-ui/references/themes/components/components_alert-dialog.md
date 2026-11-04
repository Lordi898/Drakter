Alert Dialog – Radix Themes

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

# Alert Dialog

Modal confirmation dialog that interrupts the user and expects a response.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/alert-dialog.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[AlertDialog] Issue)[View in Playground](/themes/playground#alert-dialog)

Revoke access

```
<AlertDialog.Root>



<AlertDialog.Trigger>



<Button color="red">Revoke access</Button>



</AlertDialog.Trigger>



<AlertDialog.Content maxWidth="450px">



<AlertDialog.Title>Revoke access</AlertDialog.Title>



<AlertDialog.Description size="2">



Are you sure? This application will no longer be accessible and any



existing sessions will be expired.



</AlertDialog.Description>



<Flex gap="3" mt="4" justify="end">



<AlertDialog.Cancel>



<Button variant="soft" color="gray">



Cancel



</Button>



</AlertDialog.Cancel>



<AlertDialog.Action>



<Button variant="solid" color="red">



Revoke access



</Button>



</AlertDialog.Action>



</Flex>



</AlertDialog.Content>



</AlertDialog.Root>
```

## [API Reference](#api-reference)

This component inherits parts and props from the [Alert Dialog primitive](/primitives/docs/components/alert-dialog) and is visually identical to [Dialog](/themes/docs/components/dialog), though with differing semantics and behavior.

### [Root](#root)

Contains all the parts of the dialog.

### [Trigger](#trigger)

Wraps the control that will open the dialog.

### [Content](#content)

Contains the content of the dialog. This component is based on the `div` element.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | No default value |
| `align` | `"start" | "center"` | `"center"` |
| `size` | `Responsive<"1" | "2" | "3" | "4">` | `"3"` |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | `"600px"` |
| `height` | `Responsive<string>` | No default value |
| `minHeight` | `Responsive<string>` | No default value |
| `maxHeight` | `Responsive<string>` | No default value |

### [Title](#title)

An accessible title that is announced when the dialog is opened. This part is based on the [Heading](/themes/docs/components/heading) component with a pre-defined font size and leading trim on top.

### [Description](#description)

An optional accessible description that is announced when the dialog is opened. This part is based on the [Text](/themes/docs/components/text) component with a pre-defined font size.

If you want to remove the description entirely, remove this part and pass `aria-describedby={undefined}` to `Content`.

### [Action](#action)

Wraps the control that will close the dialog. This should be distinguished visually from the `Cancel` control.

### [Cancel](#cancel)

Wraps the control that will close the dialog. This should be distinguished visually from the `Action` control.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control size of the dialog. It will affect the `padding` and `border-radius` of the Content.
Use it in conjunction with the `width`, `minWidth` and `maxWidth` props to control the width of the dialog.

Size 1Size 2Size 3Size 4

```
<Flex gap="4" align="center">



<AlertDialog.Root>



<AlertDialog.Trigger>



<Button variant="soft">Size 1</Button>



</AlertDialog.Trigger>



<AlertDialog.Content size="1" maxWidth="300px">



<Text as="p" trim="both" size="1">



The quick brown fox jumps over the lazy dog.



</Text>



</AlertDialog.Content>



</AlertDialog.Root>



<AlertDialog.Root>



<AlertDialog.Trigger>



<Button variant="soft">Size 2</Button>



</AlertDialog.Trigger>



<AlertDialog.Content size="2" maxWidth="400px">



<Text as="p" trim="both" size="2">



The quick brown fox jumps over the lazy dog.



</Text>



</AlertDialog.Content>



</AlertDialog.Root>



<AlertDialog.Root>



<AlertDialog.Trigger>



<Button variant="soft">Size 3</Button>



</AlertDialog.Trigger>



<AlertDialog.Content size="3" maxWidth="500px">



<Text as="p" trim="both" size="3">



The quick brown fox jumps over the lazy dog.



</Text>



</AlertDialog.Content>



</AlertDialog.Root>



<AlertDialog.Root>



<AlertDialog.Trigger>



<Button variant="soft">Size 4</Button>



</AlertDialog.Trigger>



<AlertDialog.Content size="4">



<Text as="p" trim="both" size="4">



The quick brown fox jumps over the lazy dog.



</Text>



</AlertDialog.Content>



</AlertDialog.Root>



</Flex>
```

### [With inset content](#with-inset-content)

Use the [Inset](/themes/docs/components/inset) component to align content flush with the sides of the dialog.

Delete users

```
<AlertDialog.Root>



<AlertDialog.Trigger>



<Button color="red">Delete users</Button>



</AlertDialog.Trigger>



<AlertDialog.Content maxWidth="500px">



<AlertDialog.Title>Delete Users</AlertDialog.Title>



<AlertDialog.Description size="2">



Are you sure you want to delete these users? This action is permanent and



cannot be undone.



</AlertDialog.Description>



<Inset side="x" my="5">



<Table.Root>



<Table.Header>



<Table.Row>



<Table.ColumnHeaderCell>Full name</Table.ColumnHeaderCell>



<Table.ColumnHeaderCell>Email</Table.ColumnHeaderCell>



<Table.ColumnHeaderCell>Group</Table.ColumnHeaderCell>



</Table.Row>



</Table.Header>



<Table.Body>



<Table.Row>



<Table.RowHeaderCell>Danilo Sousa</Table.RowHeaderCell>



<Table.Cell>danilo@example.com</Table.Cell>



<Table.Cell>Developer</Table.Cell>



</Table.Row>



<Table.Row>



<Table.RowHeaderCell>Zahra Ambessa</Table.RowHeaderCell>



<Table.Cell>zahra@example.com</Table.Cell>



<Table.Cell>Admin</Table.Cell>



</Table.Row>



</Table.Body>



</Table.Root>



</Inset>



<Flex gap="3" justify="end">



<AlertDialog.Cancel>



<Button variant="soft" color="gray">



Cancel



</Button>



</AlertDialog.Cancel>



<AlertDialog.Action>



<Button color="red">Delete users</Button>



</AlertDialog.Action>



</Flex>



</AlertDialog.Content>



</AlertDialog.Root>
```

#### Quick nav

Previous[Strong](/themes/docs/components/strong)

Next[Aspect Ratio](/themes/docs/components/aspect-ratio)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/alert-dialog.mdx "Edit this page on GitHub.")
