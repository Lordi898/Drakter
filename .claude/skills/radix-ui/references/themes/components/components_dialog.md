Dialog – Radix Themes

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

# Dialog

Modal dialog window displayed above the page.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/dialog.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Dialog] Issue)[View in Playground](/themes/playground#dialog)

Edit profile

```
<Dialog.Root>



<Dialog.Trigger>



<Button>Edit profile</Button>



</Dialog.Trigger>



<Dialog.Content maxWidth="450px">



<Dialog.Title>Edit profile</Dialog.Title>



<Dialog.Description size="2" mb="4">



Make changes to your profile.



</Dialog.Description>



<Flex direction="column" gap="3">



<label>



<Text as="div" size="2" mb="1" weight="bold">



Name



</Text>



<TextField.Root
					defaultValue="Freja Johnsen"
					placeholder="Enter your full name"
				/>



</label>



<label>



<Text as="div" size="2" mb="1" weight="bold">



Email



</Text>



<TextField.Root
					defaultValue="freja@example.com"
					placeholder="Enter your email"
				/>



</label>



</Flex>



<Flex gap="3" mt="4" justify="end">



<Dialog.Close>



<Button variant="soft" color="gray">



Cancel



</Button>



</Dialog.Close>



<Dialog.Close>



<Button>Save</Button>



</Dialog.Close>



</Flex>



</Dialog.Content>



</Dialog.Root>
```

## [API Reference](#api-reference)

This component inherits props from the [Dialog primitive](/primitives/docs/components/dialog).

Note that this dialog is designed around the modal pattern, so the `modal` prop is unavailable.

### [Root](#root)

Contains all the parts of a dialog.

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

### [Close](#close)

Wraps the control that will close the dialog.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control size of the dialog. It will affect the `padding` and `border-radius` of the Content.
Use it in conjunction with the `width`, `minWidth` and `maxWidth` props to control the width of the dialog.

Size 1Size 2Size 3Size 4

```
<Flex gap="4" align="center">



<Dialog.Root>



<Dialog.Trigger>



<Button variant="soft">Size 1</Button>



</Dialog.Trigger>



<Dialog.Content size="1" maxWidth="300px">



<Text as="p" trim="both" size="1">



The quick brown fox jumps over the lazy dog.



</Text>



</Dialog.Content>



</Dialog.Root>



<Dialog.Root>



<Dialog.Trigger>



<Button variant="soft">Size 2</Button>



</Dialog.Trigger>



<Dialog.Content size="2" maxWidth="400px">



<Text as="p" trim="both" size="2">



The quick brown fox jumps over the lazy dog.



</Text>



</Dialog.Content>



</Dialog.Root>



<Dialog.Root>



<Dialog.Trigger>



<Button variant="soft">Size 3</Button>



</Dialog.Trigger>



<Dialog.Content size="3" maxWidth="500px">



<Text as="p" trim="both" size="3">



The quick brown fox jumps over the lazy dog.



</Text>



</Dialog.Content>



</Dialog.Root>



<Dialog.Root>



<Dialog.Trigger>



<Button variant="soft">Size 4</Button>



</Dialog.Trigger>



<Dialog.Content size="4">



<Text as="p" trim="both" size="4">



The quick brown fox jumps over the lazy dog.



</Text>



</Dialog.Content>



</Dialog.Root>



</Flex>
```

### [With inset content](#with-inset-content)

Use the [Inset](/themes/docs/components/inset) component to align content flush with the sides of the dialog.

View users

```
<Dialog.Root>



<Dialog.Trigger>



<Button>View users</Button>



</Dialog.Trigger>



<Dialog.Content>



<Dialog.Title>Users</Dialog.Title>



<Dialog.Description>



The following users have access to this project.



</Dialog.Description>



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



<Dialog.Close>



<Button variant="soft" color="gray">



Close



</Button>



</Dialog.Close>



</Flex>



</Dialog.Content>



</Dialog.Root>
```

#### Quick nav

Previous[Data List](/themes/docs/components/data-list)

Next[Dropdown Menu](/themes/docs/components/dropdown-menu)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/dialog.mdx "Edit this page on GitHub.")
