Table – Radix Themes

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

# Table

Semantic table element for presenting data.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/table.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Table] Issue)[View in Playground](/themes/playground#table)

| Full name | Email | Group |
| --- | --- | --- |
| Danilo Sousa | danilo@example.com | Developer |
| Zahra Ambessa | zahra@example.com | Admin |
| Jasper Eriksson | jasper@example.com | Developer |

```
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



<Table.Row>



<Table.RowHeaderCell>Jasper Eriksson</Table.RowHeaderCell>



<Table.Cell>jasper@example.com</Table.Cell>



<Table.Cell>Developer</Table.Cell>



</Table.Row>



</Table.Body>



</Table.Root>
```

## [API Reference](#api-reference)

### [Root](#root)

Groups the `Header` and `Body` parts. This component is based on the `table` element and supports [common margin props](/themes/docs/overview/layout#margin-props).

| Prop | Type | Default |
| --- | --- | --- |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"surface" | "ghost"` | `"ghost"` |
| `layout` | `Responsive<"auto" | "fixed">` | No default value |

### [Header](#header)

Contains the column headings for the table, based on the `thead` element.

### [Body](#body)

Displays the table data. This component is based on the `tbody` element.

### [Row](#row)

A row of table cells. Based on the `tr` element.

| Prop | Type | Default |
| --- | --- | --- |
| `align` | `Responsive<"start" | "center" | "end" | "baseline">` | No default value |

### [Cell](#cell)

A basic table cell. This component is based on the `td` element, but uses `justify` instead of `align` to control how horizontal space is distributed within the table cell.

| Prop | Type | Default |
| --- | --- | --- |
| `justify` | `Responsive<"start" | "center" | "end">` | No default value |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | No default value |
| `p` | `Responsive<enum | string>` See full type | No default value |
| `px` | `Responsive<enum | string>` See full type | No default value |
| `py` | `Responsive<enum | string>` See full type | No default value |
| `pt` | `Responsive<enum | string>` See full type | No default value |
| `pr` | `Responsive<enum | string>` See full type | No default value |
| `pb` | `Responsive<enum | string>` See full type | No default value |
| `pl` | `Responsive<enum | string>` See full type | No default value |

### [ColumnHeaderCell](#columnheadercell)

The header of a table column. Based on the `th` element and provides the same props interface as the `Cell` part.

| Prop | Type | Default |
| --- | --- | --- |
| `justify` | `Responsive<"start" | "center" | "end">` | No default value |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | No default value |
| `p` | `Responsive<enum | string>` See full type | No default value |
| `px` | `Responsive<enum | string>` See full type | No default value |
| `py` | `Responsive<enum | string>` See full type | No default value |
| `pt` | `Responsive<enum | string>` See full type | No default value |
| `pr` | `Responsive<enum | string>` See full type | No default value |
| `pb` | `Responsive<enum | string>` See full type | No default value |
| `pl` | `Responsive<enum | string>` See full type | No default value |

### [RowHeaderCell](#rowheadercell)

The header of a table row. Based on the `th` element and provides the same props interface as the `Cell` part.

| Prop | Type | Default |
| --- | --- | --- |
| `justify` | `Responsive<"start" | "center" | "end">` | No default value |
| `width` | `Responsive<string>` | No default value |
| `minWidth` | `Responsive<string>` | No default value |
| `maxWidth` | `Responsive<string>` | No default value |
| `p` | `Responsive<enum | string>` See full type | No default value |
| `px` | `Responsive<enum | string>` See full type | No default value |
| `py` | `Responsive<enum | string>` See full type | No default value |
| `pt` | `Responsive<enum | string>` See full type | No default value |
| `pr` | `Responsive<enum | string>` See full type | No default value |
| `pb` | `Responsive<enum | string>` See full type | No default value |
| `pl` | `Responsive<enum | string>` See full type | No default value |

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control how large the text and padding of the table cells should be.

| Full name | Email |
| --- | --- |
| Danilo Sousa | danilo@example.com |
| Zahra Ambessa | zahra@example.com |

| Full name | Email |
| --- | --- |
| Danilo Sousa | danilo@example.com |
| Zahra Ambessa | zahra@example.com |

| Full name | Email |
| --- | --- |
| Danilo Sousa | danilo@example.com |
| Zahra Ambessa | zahra@example.com |

```
<Flex direction="column" gap="5" maxWidth="350px">



<Table.Root size="1">



<Table.Header>



<Table.Row>



<Table.ColumnHeaderCell>Full name</Table.ColumnHeaderCell>



<Table.ColumnHeaderCell>Email</Table.ColumnHeaderCell>



</Table.Row>



</Table.Header>



<Table.Body>



<Table.Row>



<Table.RowHeaderCell>Danilo Sousa</Table.RowHeaderCell>



<Table.Cell>danilo@example.com</Table.Cell>



</Table.Row>



<Table.Row>



<Table.RowHeaderCell>Zahra Ambessa</Table.RowHeaderCell>



<Table.Cell>zahra@example.com</Table.Cell>



</Table.Row>



</Table.Body>



</Table.Root>



<Table.Root size="2">



<Table.Header>



<Table.Row>



<Table.ColumnHeaderCell>Full name</Table.ColumnHeaderCell>



<Table.ColumnHeaderCell>Email</Table.ColumnHeaderCell>



</Table.Row>



</Table.Header>



<Table.Body>



<Table.Row>



<Table.RowHeaderCell>Danilo Sousa</Table.RowHeaderCell>



<Table.Cell>danilo@example.com</Table.Cell>



</Table.Row>



<Table.Row>



<Table.RowHeaderCell>Zahra Ambessa</Table.RowHeaderCell>



<Table.Cell>zahra@example.com</Table.Cell>



</Table.Row>



</Table.Body>



</Table.Root>



<Table.Root size="3">



<Table.Header>



<Table.Row>



<Table.ColumnHeaderCell>Full name</Table.ColumnHeaderCell>



<Table.ColumnHeaderCell>Email</Table.ColumnHeaderCell>



</Table.Row>



</Table.Header>



<Table.Body>



<Table.Row>



<Table.RowHeaderCell>Danilo Sousa</Table.RowHeaderCell>



<Table.Cell>danilo@example.com</Table.Cell>



</Table.Row>



<Table.Row>



<Table.RowHeaderCell>Zahra Ambessa</Table.RowHeaderCell>



<Table.Cell>zahra@example.com</Table.Cell>



</Table.Row>



</Table.Body>



</Table.Root>



</Flex>
```

### [With a backplate](#with-a-backplate)

Use `variant="surface"` to add a visually enclosed backplate to the table.

| Full name | Email | Group |
| --- | --- | --- |
| Danilo Sousa | danilo@example.com | Developer |
| Zahra Ambessa | zahra@example.com | Admin |
| Jasper Eriksson | jasper@example.com | Developer |

```
<Table.Root variant="surface">



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



<Table.Row>



<Table.RowHeaderCell>Jasper Eriksson</Table.RowHeaderCell>



<Table.Cell>jasper@example.com</Table.Cell>



<Table.Cell>Developer</Table.Cell>



</Table.Row>



</Table.Body>



</Table.Root>
```

#### Quick nav

Previous[Switch](/themes/docs/components/switch)

Next[Tabs](/themes/docs/components/tabs)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/table.mdx "Edit this page on GitHub.")
