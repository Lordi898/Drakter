Radius – Radix Themes

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

Guides

# Radius

Choosing the right radius setting in your theme.

## [Theme setting](#theme-setting)

Theme `radius` setting manages the radius factor applied to the components:

```
<Theme radius="medium">



<TextField.Root size="3" placeholder="Reply…">



<TextField.Slot side="right" px="1">



<Button size="2">Send</Button>



</TextField.Slot>



</TextField.Root>



</Theme>
```

`none`

Send

`small`

Send

`medium`

Send

`large`

Send

`full`

Send

The resulting `border-radius` is contextual and differs depending on the component. For example, when set to `full`, a [Button](/themes/docs/components/button) becomes pill-shaped, while a [Checkbox](/themes/docs/components/checkbox) will never become fully rounded to prevent any confusion between it and a [Radio](/themes/docs/components/radio).

Save

```
<Theme radius="full">



<Flex align="center" gap="3">



<Button>Save</Button>



<Switch defaultChecked />



<Checkbox defaultChecked />



</Flex>



</Theme>
```

## [Radius overrides](#radius-overrides)

Certain components allow you to override the radius factor using their own `radius` prop.

SaveSaveSaveSaveSave

```
<Flex align="center" gap="3">



<Button radius="none">Save</Button>



<Button radius="small">Save</Button>



<Button radius="medium">Save</Button>



<Button radius="large">Save</Button>



<Button radius="full">Save</Button>



</Flex>
```

Components that render panels, like Card, Dialog, and Popover, among others, won’t have the `radius` prop, but will inherit the radius setting from the theme. The `radius` prop is also unavailable on most text-based components.

## [Radius scale](#radius-scale)

Radius values used in the components are derived from a 6-step scale.

1

2

3

4

5

6

While you can’t use a specific step on a particular component directly—the `radius` prop is used to set just the radius factor—you can use the radius scale to style your own components.

Radius tokens are accessed using CSS variables. You can use these tokens to style your custom components, ensuring they are consistent with the rest of your theme.

```
/* Radius values that automatically respond to the radius factor */



var(--radius-1);



var(--radius-2);



var(--radius-3);



var(--radius-4);



var(--radius-5);



var(--radius-6);



/* A multiplier that controls the theme radius */



var(--radius-factor);



/*



* A variable used to calculate a fully rounded radius.



* Usually used within a CSS `max()` function.



*/



var(--radius-full);



/*



* A variable used to calculate radius of a thumb element.



* Usually used within a CSS `max()` function.



*/



var(--radius-thumb);
```

#### Quick nav

Previous[Breakpoints](/themes/docs/theme/breakpoints)

Next[Shadows](/themes/docs/theme/shadows)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/theme/radius.mdx "Edit this page on GitHub.")
