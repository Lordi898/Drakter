Typography – Radix Themes

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

# Typography

Guidance for using and tuning typography.

## [Base components](#base-components)

Use [Text](/themes/docs/components/text) and [Heading](/themes/docs/components/heading) components to render titles and body copy. These components share `size` and `weight` props and map to the underlying type system to ensure consistent typography throughout your app.

# Typographic principles

The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant.

```
<Heading mb="2" size="4">Typographic principles</Heading>



<Text>The goal of typography is to relate font size, line height, and line width in a proportional way that maximizes beauty and makes reading easier and more pleasant.</Text>
```

## [Formatting components](#formatting-components)

Compose formatting components to add [emphasis](/themes/docs/components/em), [signal importance](/themes/docs/components/strong), present [code](/themes/docs/components/code) and more.

The *most* important thing to remember is, **stay positive**.

```
<Text>



The <Em>most</Em> important thing to remember is,{" "}



<Strong>stay positive</Strong>.



</Text>
```

## [Type scale](#type-scale)

The typographic system is based on a 9-step `size` scale. Every step has a corresponding font size, line height and letter spacing value which are all designed to be used in combination.

Aa

1

Aa

2

Aa

3

Aa

4

Aa

5

Aa

6

Aa

7

Aa

8

Aa

9

The quick brown fox jumps over the lazy dog.

```
<Text size="6">The quick brown fox jumps over the lazy dog.</Text>
```

| Step | Size | Letter spacing | Line height |
| --- | --- | --- | --- |
| 1 | `12px` | `0.0025em` | `16px` |
| 2 | `14px` | `0em` | `20px` |
| 3 | `16px` | `0em` | `24px` |
| 4 | `18px` | `-0.0025em` | `26px` |
| 5 | `20px` | `-0.005em` | `28px` |
| 6 | `24px` | `-0.00625em` | `30px` |
| 7 | `28px` | `-0.0075em` | `36px` |
| 8 | `35px` | `-0.01em` | `40px` |
| 9 | `60px` | `-0.025em` | `60px` |

## [Font weight](#font-weight)

The following weights are supported. Weights can be [customized](/themes/docs/theme/typography#custom-font-weights) to map to your own typeface.

LightRegularMediumBold

```
<Text size="6">



<Flex direction="column">



<Text weight="light">Light</Text>



<Text weight="regular">Regular</Text>



<Text weight="medium">Medium</Text>



<Text weight="bold">Bold</Text>



</Flex>



</Text>
```

| Weight | Default value |
| --- | --- |
| Light | `300` |
| Regular | `400` |
| Medium | `500` |
| Bold | `700` |

## [Font family](#font-family)

By default, Radix Themes uses a system font stack for portability and legibility. Continue to the next section to learn about customizing your theme with a custom font.

| Type | Default value |
| --- | --- |
| Text | `-apple-system, BlinkMacSystemFont, 'Segoe UI (Custom)', Roboto, 'Helvetica Neue', 'Open Sans (Custom)', system-ui, sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji'` |
| Code | `'Menlo', 'Consolas (Custom)', 'Bitstream Vera Sans Mono', monospace, 'Apple Color Emoji', 'Segoe UI Emoji'` |
| Emphasis | `'Times New Roman', 'Times', serif` |
| Quote | `'Times New Roman', 'Times', serif` |

## [Customization](#customization)

Radix Themes typography can be customized by overriding the corresponding CSS variables of the token system. Refer to the [source code](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/styles/tokens/typography.css) for the full list of the typographic tokens.

Make sure that your CSS is applied after the Radix Themes styles so that it takes precedence.

### [Custom fonts](#custom-fonts)

You can provide your own fonts, however, how you choose to import and serve them is up to you. It is only required that you specify your named fonts using the correct syntax.

To customize the font family used in your theme, remap the corresponding `font-family` tokens:

```
.radix-themes {



--default-font-family:  /* Your custom default font */ --heading-font-family:



/* Your custom font for <Heading> components */ --code-font-family:



/* Your custom font for <Code> components */ --strong-font-family:



/* Your custom font for <Strong> components */ --em-font-family:



/* Your custom font for <Em> components */ --quote-font-family:



/* Your custom font for <Quote> components */;



}
```

### [With next/font](#with-nextfont)

To load custom fonts via [next/font](https://nextjs.org/docs/app/api-reference/components/font), use the [`variable`](https://nextjs.org/docs/app/api-reference/components/font#variable) option to define a CSS variable name. Then, add that CSS variable class to your HTML document.

```
import { Inter } from "next/font/google";



const inter = Inter({



subsets: ["latin"],



display: "swap",



variable: "--font-inter",



});



export default function RootLayout({ children }) {



return (



<html lang="en" className={inter.variable}>



<body>{children}</body>



</html>



);



}
```

Finally, assign the CSS variable in your custom CSS:

```
.radix-themes {



--default-font-family: var(--font-inter);



}
```

Be aware that you may encounter css import order issues if you are running the app router. See [common styling issues](/themes/docs/overview/styling#nextjs-import-order) for more information.

### [Custom font weights](#custom-font-weights)

To customize the exact font weights used in your theme, remap the corresponding `font-weight` tokens to your own values:

```
.radix-themes {



--font-weight-light: 200;



--font-weight-regular: 300;



--font-weight-medium: 600;



--font-weight-bold: 800;



}
```

### [Advanced settings](#advanced-settings)

There’s a number of advanced typographic features that can be customized. These include a font size multiplier for certain components, font style, letter spacing, and leading trim. For example, you can customize the headings to render with a relatively larger font size than your default font, different leading trim values, and tighter letter spacing:

```
.radix-themes {



--heading-font-family: "Untitled Sans", sans-serif;



--heading-font-size-adjust: 1.05;



--heading-font-style: normal;



--heading-leading-trim-start: 0.42em;



--heading-leading-trim-end: 0.38em;



--heading-letter-spacing: -0.01em;



}
```

#### Quick nav

Previous[Dark mode](/themes/docs/theme/dark-mode)

Next[Spacing](/themes/docs/theme/spacing)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/theme/typography.mdx "Edit this page on GitHub.")
