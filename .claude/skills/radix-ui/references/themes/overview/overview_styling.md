Styling – Radix Themes

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

# Styling

How to approach styling with Radix Themes.

## [Introduction](#introduction)

Radix Themes does not come with a built-in styling system. There’s no `css` or `sx` prop, and it does not use any styling libraries internally. Under the hood, it’s built with vanilla CSS.

There’s no overhead when it comes to picking a styling technology for your app.

## [What you get](#what-you-get)

The components in Radix Themes are relatively closed—they come with a set of styles that aren’t always easily overridden. They are customizable within what’s allowed by their props and the theme configuration.

However, you also get access to the same CSS variables that power the Radix Themes components. You can use these tokens to create custom components that naturally feel at home in the original theme. Changes to the token system are treated as breaking.

For more information on specific tokens, refer to the corresponding guides in the [Theme section](/themes/docs/theme/overview).

Color system

# ABCD

# ABCDEFG

# ABCDEFGHI

# ABCDEFGHIJ

# ABCDEFGHIJKL

A wonderful serenity has taken possession of my entire soul, like these sweet mornings of spring which I enjoy with my whole heart. I am alone, and feel the charm of existence in this spot, which was created for the bliss of souls like mine. I am so happy, my dear friend, so absorbed in the exquisite sense of mere tranquil existence, that I neglect my talents. I should be incapable of drawing a single stroke at the present moment; and yet I feel that I never was a greater artist than now. When, while the lovely valley teems with vapour around me, and the meridian sun strikes the upper surface of the impenetrable foliage of my trees, and but a few stray gleams steal into the inner sanctuary, I throw myself down among the tall grass by the trickling stream; and, as I lie close to the earth, a thousand unknown plants are noticed by me: when I hear the buzz of the little world among the stalks, and grow familiar with the countless indescribable forms of the insects and flies, then I feel the presence of the Almighty, who formed us in his own image, and the breath

# Ambiguous voice of a heart which prefers kiwi bowls to a zephyr.

Typography examples

Shadow and radius examples

## [Overriding styles](#overriding-styles)

Beyond simple style overrides, we recommend using the components as-is, or create your own versions using the same building blocks.

Most components do have `className` and `style` props, but if you find yourself needing to override a lot of styles, it’s a good sign that you should either:

* Try to achieve what you need with the existing props and theme configuration.
* See whether you can achieve your design by tweaking the underlying token system.
* Create your own component using lower-level building blocks, such [Primitives](/primitives) and [Colors](/colors).
* Reconsider whether Radix Themes is the right fit for your project.

### [Tailwind](#tailwind)

Tailwind is *great*. Yet, if you plan to use Radix Themes with Tailwind, keep in mind how its ergonomics may encourage you to create complex styles on the fly, sometimes reaching into the component internals without friction.

Tailwind is a different styling paradigm, which may not mix well with the idea of a closed component system where customization is achieved through props, tokens, and creating new components on top of a shared set of building blocks.

## [Custom components](#custom-components)

If you need to create a custom component, use the same building blocks that Radix Themes uses:

* [Theme](/themes/docs/theme/overview) tokens that power the components
* [Radix Primitives](/primitives), a library of accessible, unstyled components
* [Radix Colors](/colors), a color system for building beautiful websites and apps

Feel free to explore the [source code](https://github.com/radix-ui/themes/tree/main/packages/radix-ui-themes) of Radix Themes to see how it is built.

## [Common issues](#common-issues)

### [z-index conflicts](#z-index-conflicts)

Out of the box, portalled Radix Themes components can be nested and stacked in any order without conflicts. For example, you can open a popover that opens a dialog, which in turn opens another popover. They all stack on top of each other in the order they were opened:

Recursive popover

When building your own components, use the following rules to avoid z-index conflicts:

* Don’t use `z-index` values other than `auto`, `0`, or `-1` in rare cases.
* Render the elements that should stack on top of each other in portals.

Your main content and portalled content are separated by the stacking context that the styles of the root `<Theme>` component create. This allows you to stack portalled content on top of the main content without worrying about z-indices.

### [Next.js import order](#nextjs-import-order)

As of Next.js 13.0 to 14.1, the import order of CSS files in `app/**/layout.tsx` is not guaranteed, so Radix Themes may overwrite your own styles even when written correctly:

```
import "@radix-ui/themes/styles.css";



import "./my-styles.css";
```

This Next.js issue may come and go sporadically, or happen only in development or production.

As a workaround, you can merge all the CSS into a single file first via [postcss-import](https://github.com/postcss/postcss-import) and import just that into your layout. Alternatively, importing the styles directly in `page.tsx` files also works.

### [Tailwind base styles](#tailwind-base-styles)

As of Tailwind v3, styles produced by the `@tailwind` directive are usually appended after any imported CSS, no matter the original import order. In particular, Tailwind’s [button reset](https://github.com/tailwindlabs/tailwindcss/blob/7361468f77500105b0559e879e121f34306e8da2/src/css/preflight.css#L197-L204) style may interfere with Radix Themes buttons, rendering certain buttons without a background color.

Workarounds:

* Don’t use `@tailwind base`
* Set up separate CSS [layers](https://developer.mozilla.org/en-US/docs/Web/CSS/@layer) for Tailwind and Radix Themes
* Set up [postcss-import](https://github.com/postcss/postcss-import) and manually import Tailwind base styles via `@import tailwindcss/base` before Radix Themes styles. [Example setup](https://github.com/radix-ui/themes/issues/109#issuecomment-1747345743)

### [Missing styles in portals](#missing-styles-in-portals)

When you render a custom portal in a Radix Themes project, it will naturally appear outside of the root `<Theme>` component, which means it won’t have access to most of the theme tokens and styles. To fix that, wrap the portal content with another `<Theme>`:

```
// Implementation example of a custom dialog using the low-level Dialog primitive



// Refer to https://www.radix-ui.com/primitives/docs/components/dialog



import { Dialog } from "radix-ui";



import { Theme } from "@radix-ui/themes";



function MyCustomDialog() {



return (



<Dialog.Root>



<Dialog.Trigger>Open</Dialog.Trigger>



<Dialog.Portal>



<Theme>



<Dialog.Overlay />



<Dialog.Content>



<Dialog.Title />



<Dialog.Description />



<Dialog.Close />



</Dialog.Content>



</Theme>



</Dialog.Portal>



</Dialog.Root>



);



}
```

Components like Dialog and Popover in Radix Themes already handle this for you, so this is only necessary when creating your own portalled components.

### [Complex CSS precedence](#complex-css-precedence)

Usually, you’d want your custom CSS to override Radix Themes styles. However, there are cases when it is natural to expect the opposite.

Consider a simple paragraph style that just resets the browser’s default margin:

```
.my-paragraph {



margin: 0;



}
```

You might apply the margin prop from a `Box` onto your custom paragraph via `asChild`:

```
import "@radix-ui/themes/styles.css";



import "./my-styles.css";



function MyApp() {



return (



<Theme>



<Box asChild m="5">



<p className="my-paragraph">My custom paragraph</p>



</Box>



</Theme>



);



}
```

Yet, this won’t work intuitively. The custom styles are imported after Radix Themes styles, so they will override the margin prop. As a workaround, Radix Themes provides separate `tokens.css`, `components.css`, and `utilities.css` files that the original `styles.css` is built upon:

```
import "@radix-ui/themes/tokens.css";



import "@radix-ui/themes/components.css";



import "@radix-ui/themes/utilities.css";
```

You can import `utilities.css` after your custom styles to ensure that the layout props work as expected with your custom styles. However, if you use Next.js, keep in mind the [import order issue](/themes/docs/overview/styling#nextjs-import-order) that’s mentioned above.

If you use [standalone layout components](/themes/docs/overview/layout#standalone-usage), split CSS files are also available for them:

```
import "@radix-ui/themes/layout/tokens.css";



import "@radix-ui/themes/layout/components.css";



import "@radix-ui/themes/layout/utilities.css";
```

#### Quick nav

Previous[Getting started](/themes/docs/overview/getting-started)

Next[Layout](/themes/docs/overview/layout)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/overview/styling.mdx "Edit this page on GitHub.")
