Segmented Control – Radix Themes

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

# Segmented Control

Toggle buttons for switching between different values or views.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/segmented-control.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[SegmentedControl] Issue)[View in Playground](/themes/playground#segmented-control)

InboxInboxDraftsDraftsSentSent

```
<SegmentedControl.Root defaultValue="inbox">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>
```

## [API Reference](#api-reference)

This component inherits props and functionality from the [Toggle Group primitive](/primitives/docs/components/toggle-group). It supports [common margin props](/themes/docs/overview/layout#margin-props).

### [Root](#root)

Contains the items of the control.

| Prop | Type | Default |
| --- | --- | --- |
| `disabled` | `boolean` | `false` |
| `size` | `Responsive<"1" | "2" | "3">` | `"2"` |
| `variant` Prop description | `"surface" | "classic"` | `"surface"` |
| `radius` Prop description | `"none" | "small" | "medium" | "large" | "full"` | No default value |

### [Item](#item)

Represents individual values of the control.

## [Examples](#examples)

### [Size](#size)

Use the `size` prop to control the size of the control.

InboxInboxDraftsDraftsSentSent

InboxInboxDraftsDraftsSentSent

InboxInboxDraftsDraftsSentSent

```
<Flex align="start" direction="column" gap="4">



<SegmentedControl.Root defaultValue="inbox" size="1">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



<SegmentedControl.Root defaultValue="inbox" size="2">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



<SegmentedControl.Root defaultValue="inbox" size="3">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



</Flex>
```

### [Variant](#variant)

Use the `variant` prop to control the visual style of the control.

InboxInboxDraftsDraftsSentSent

InboxInboxDraftsDraftsSentSent

```
<Flex align="start" direction="column" gap="4">



<SegmentedControl.Root defaultValue="inbox" variant="surface">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



<SegmentedControl.Root defaultValue="inbox" variant="classic">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



</Flex>
```

### [Radius](#radius)

Use the `radius` prop to assign a specific radius value.

InboxInboxDraftsDraftsSentSent

InboxInboxDraftsDraftsSentSent

InboxInboxDraftsDraftsSentSent

InboxInboxDraftsDraftsSentSent

InboxInboxDraftsDraftsSentSent

```
<Flex align="start" direction="column" gap="4">



<SegmentedControl.Root defaultValue="inbox" radius="none">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



<SegmentedControl.Root defaultValue="inbox" radius="small">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



<SegmentedControl.Root defaultValue="inbox" radius="medium">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



<SegmentedControl.Root defaultValue="inbox" radius="large">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



<SegmentedControl.Root defaultValue="inbox" radius="full">



<SegmentedControl.Item value="inbox">Inbox</SegmentedControl.Item>



<SegmentedControl.Item value="drafts">Drafts</SegmentedControl.Item>



<SegmentedControl.Item value="sent">Sent</SegmentedControl.Item>



</SegmentedControl.Root>



</Flex>
```

#### Quick nav

Previous[Scroll Area](/themes/docs/components/scroll-area)

Next[Select](/themes/docs/components/select)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/segmented-control.mdx "Edit this page on GitHub.")
