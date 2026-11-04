Dark mode – Radix Themes

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

# Dark mode

Using appearance to manage and integrate dark mode.

## [Overview](#overview)

Light and dark modes are supported out of the box, allowing you to easily switch appearance without additional design or styling.

![](https://workos.imgix.net/images/e35b46dc-4384-43d1-932c-24fa44e212cd.png?auto=format&fit=clip&q=80)

### King Krule – The OOZ

A dark and introspective album that showcases a distinctive blend of genres.

Listen Now

![](https://workos.imgix.net/images/e35b46dc-4384-43d1-932c-24fa44e212cd.png?auto=format&fit=clip&q=80)

### King Krule – The OOZ

A dark and introspective album that showcases a distinctive blend of genres.

Listen Now

## [Basic usage](#basic-usage)

By default, the root `Theme` appearance is `light`. To set a different appearance pass it via the `appearance` prop. This will force the theme to use the specified setting.

```
<Theme appearance="dark">



<MyApp />



</Theme>
```

## [Inheriting system appearance](#inheriting-system-appearance)

A common requirement is to inherit the appearance setting from a user’s system preferences.

This is a deceptively complex problem to solve given SSR, SSG and client side hydration considerations. To make implementation easier, we recommend integrating with a theme switching library.

### [With next-themes](#with-next-themes)

Integration with `next-themes` is simple and straightforward because Radix Themes implements matching class names.

To enable dark mode, use `<ThemeProvider>` from `next-themes` with `attribute="class"`.

```
import { Theme } from "@radix-ui/themes";



import { ThemeProvider } from "next-themes";



export default function () {



return (



<ThemeProvider attribute="class">



<Theme>



<MyApp />



</Theme>



</ThemeProvider>



);



}
```

**Do not** try to set `<Theme appearance={resolvedTheme}>`. Instead, rely just on class switching that `next-themes` provides. This way `next-themes` can prevent the appearance flash during initial render.

### [With other libraries](#with-other-libraries)

Any library that supports class switching is compatible. You’ll just need to ensure that the appended class names match those supported by Radix Themes:

* `className="light"`
* `className="light-theme"`
* `className="dark"`
* `className="dark-theme"`

#### Quick nav

Previous[Color](/themes/docs/theme/color)

Next[Typography](/themes/docs/theme/typography)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/theme/dark-mode.mdx "Edit this page on GitHub.")
