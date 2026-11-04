Getting started – Radix Themes

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

Overview

# Getting started

Install Radix Themes and start building in minutes.

Radix Themes is a pre-styled component library that is designed to work out of the box with minimal configuration. If you are looking for the unstyled components, go to [Radix Primitives](/primitives).

## [Installation](#installation)

Getting up and running is quick and easy.

### [1. Install Radix Themes](#1-install-radix-themes)

Install the package from your command line.

npmnpmyarnyarnpnpmpnpm

```
npm install @radix-ui/themes
```

### [2. Import the CSS file](#2-import-the-css-file)

Import the global CSS file at the root of your application.

```
import "@radix-ui/themes/styles.css";
```

### [3. Add the Theme component](#3-add-the-theme-component)

Add `Theme` to your application, wrapping the root component inside of `body`.

```
import { Theme } from "@radix-ui/themes";



export default function () {



return (



<html>



<body>



<Theme>



<MyApp />



</Theme>



</body>



</html>



);



}
```

### [4. Start building](#4-start-building)

You are now ready to use Radix Themes components.

```
import { Flex, Text, Button } from "@radix-ui/themes";



export default function MyApp() {



return (



<Flex direction="column" gap="2">



<Text>Hello from Radix Themes :)</Text>



<Button>Let's go</Button>



</Flex>



);



}
```

## [Customizing your theme](#customizing-your-theme)

Configuration is managed and applied via the [Theme](/themes/docs/components/theme) component.

### [Basic configuration](#basic-configuration)

Pass [configuration](/themes/docs/components/theme) to the `Theme` to customize appearance.

```
<Theme accentColor="crimson" grayColor="sand" radius="large" scaling="95%">



<MyApp />



</Theme>
```

### [Using the theme panel](#using-the-theme-panel)

`ThemePanel` is a drop-in component that allows you to preview the theme in real time. Visit the [component playground](/themes/playground) to see it in action.

To add `ThemePanel` to your app, import it from the package and drop it inside your root `Theme`.

```
import { Theme, ThemePanel } from "@radix-ui/themes";



export default function () {



return (



<Theme>



<MyApp />



<ThemePanel />



</Theme>



);



}
```

### [Take it further](#take-it-further)

Get the most out of Radix Themes by exploring more concepts and features.

[Styling

Learn how to approach styling and overrides with Radix Themes.](/themes/docs/overview/styling)[Layout

Get to know the layout primitives and their available properties.](/themes/docs/overview/layout)[Theme overview

Anatomy of a theme and how to create the perfect style for your app.](/themes/docs/theme/overview)[Color

Understand the color system and its application in your theme.](/themes/docs/theme/color)[Dark mode

Integrate a great looking dark mode into your app using appearances.](/themes/docs/theme/dark-mode)[Typography

Add custom typefaces and fine tune typographic details.](/themes/docs/theme/typography)

#### Quick nav

Next[Styling](/themes/docs/overview/styling)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/overview/getting-started.mdx "Edit this page on GitHub.")
