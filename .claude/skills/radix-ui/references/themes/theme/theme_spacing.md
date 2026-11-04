Spacing – Radix Themes

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

# Spacing

Overview of the space scale and scaling options.

## [Space scale](#space-scale)

Spacing values are derived from a 9-step scale, which is used for props such as margin and padding. These props accept numeric strings from `"1"` to `"9"`, which correspond to the steps in the scale below.

1

2

3

4

5

6

7

8

9

| Step | Base value |
| --- | --- |
| 1 | `4px` |
| 2 | `8px` |
| 3 | `12px` |
| 4 | `16px` |
| 5 | `24px` |
| 6 | `32px` |
| 7 | `40px` |
| 8 | `48px` |
| 9 | `64px` |

#### Space scale tokens

Space scale tokens can be also accessed using CSS variables. You can use these tokens to style your custom components, ensuring they are consistent with the rest of your theme.

```
/* Space scale */



var(--space-1);



var(--space-2);



var(--space-3);



var(--space-4);



var(--space-5);



var(--space-6);



var(--space-7);



var(--space-8);



var(--space-9);
```

## [Scaling](#scaling)

Values which affect layout (spacing, font size, line height) scale relatively to each other based on the `scaling` value defined in your Theme. This setting allows you to scale the UI density uniformly across your entire application.

```
<Theme scaling="100%">



<Card variant="surface">



<Flex gap="3" align="center">



<Avatar size="3" src={person.image} fallback={person.name} />



<Box>



<Text as="div" size="2" weight="bold">



{person.name}



</Text>



<Text as="div" size="2" color="gray">



Approved invoice <Link>#3461</Link>



</Text>



</Box>



</Flex>



</Card>



</Theme>
```

`90%`

Danilo Sousa

Approved invoice [#3461](#)

`95%`

Danilo Sousa

Approved invoice [#3461](#)

`100%`

Danilo Sousa

Approved invoice [#3461](#)

`105%`

Danilo Sousa

Approved invoice [#3461](#)

`110%`

Danilo Sousa

Approved invoice [#3461](#)

#### Scaling factor

The scaling factor token can be accessed using the `--scaling` CSS variable. If you need to use different scaling factors in your app, you can use this token in your custom styles, ensuring they are consistent with the rest of your theme.

```
.MyCustomComponent {



width: calc(200px * var(--scaling));



}
```

#### Quick nav

Previous[Typography](/themes/docs/theme/typography)

Next[Breakpoints](/themes/docs/theme/breakpoints)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/theme/spacing.mdx "Edit this page on GitHub.")
