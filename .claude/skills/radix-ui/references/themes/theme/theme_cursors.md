Cursors – Radix Themes

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

# Cursors

Customizing cursors used for interactive elements.

## [Default cursors](#default-cursors)

By default, interactive elements that don’t link to another page use the regular arrow cursor. This also matches the browser defaults. However, disabled elements use an explicit disabled cursor.

Button[Link](#)Disabled

Ghost button[Link](#)

```
<Flex align="center" gap="4" wrap="wrap">



<Flex align="center" gap="3" wrap="wrap">



<Button>Button</Button>



<Button asChild>



<a href="#">Link</a>



</Button>



<Button disabled>Disabled</Button>



</Flex>



<Button variant="ghost">Ghost button</Button>



<Link href="#" size="2">



Link



</Link>



<Checkbox defaultChecked />



<Switch defaultChecked />



<Switch defaultChecked disabled />



</Flex>
```

## [Cursor tokens](#cursor-tokens)

Cursor settings can be accessed using CSS variables. You can use these tokens to style your custom components, ensuring they are accessible and consistent with the rest of your theme.

```
/* Available cursor tokens */



var(--cursor-button);



var(--cursor-checkbox);



var(--cursor-disabled);



var(--cursor-link);



var(--cursor-menu-item);



var(--cursor-radio);



var(--cursor-slider-thumb);



var(--cursor-slider-thumb-active);



var(--cursor-switch);
```

## [Customization](#customization)

It’s common to use a pointer cursor for interactive elements. Radix Themes cursors can be customized by overriding the corresponding CSS variables of the token system.

Here’s an example of how you can customize the cursor tokens to set `cursor: pointer` for most interactive elements in the theme:

```
.radix-themes {



--cursor-button: pointer;



--cursor-checkbox: pointer;



--cursor-disabled: default;



--cursor-link: pointer;



--cursor-menu-item: pointer;



--cursor-radio: pointer;



--cursor-slider-thumb: grab;



--cursor-slider-thumb-active: grabbing;



--cursor-switch: pointer;



}
```

Make sure that your CSS is applied after the Radix Themes styles so that it takes precedence.

#### Quick nav

Previous[Shadows](/themes/docs/theme/shadows)

Next[Box](/themes/docs/components/box)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/theme/cursors.mdx "Edit this page on GitHub.")
