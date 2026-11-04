How to use Radix Colors â€“ Radix Colors

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[ThemesThemes](/)[PrimitivesPrimitives](/primitives)[IconsIcons](/icons)[ColorsColors](/colors)

[Documentation](/colors/docs)[Custom palette](/colors/custom)[Blog](/blog)

#### Overview

[Installation](/colors/docs/overview/installation)[Usage](/colors/docs/overview/usage)[Aliasing](/colors/docs/overview/aliasing)[Custom palettes](/colors/docs/overview/custom-palettes)[Releases](/colors/docs/overview/releases)

#### Palette composition

[Scales](/colors/docs/palette-composition/scales)[Composing a palette](/colors/docs/palette-composition/composing-a-palette)[Understanding the scale](/colors/docs/palette-composition/understanding-the-scale)

# Usage

How to use Radix Colors with various styling solutions.

Radix Colors scales are just simple JavaScript objects, so you can use them with your preferred styling solution easily. Below you can find usage examples for popular styling solutions.

## [Vanilla CSS](#vanilla-css)

Radix Colors provides the colors bundled as raw CSS files. You can import them directly in your files when using a bundler, such as Parcel or Webpack.

```
/* Import only the scales you need */



@import "@radix-ui/colors/gray.css";



@import "@radix-ui/colors/blue.css";



@import "@radix-ui/colors/green.css";



@import "@radix-ui/colors/red.css";



@import "@radix-ui/colors/gray-dark.css";



@import "@radix-ui/colors/blue-dark.css";



@import "@radix-ui/colors/green-dark.css";



@import "@radix-ui/colors/red-dark.css";



/* Use the colors as CSS variables */



.button {



background-color: var(--blue-4);



color: var(--blue-11);



border-color: var(--blue-7);



}



.button:hover {



background-color: var(--blue-5);



border-color: var(--blue-8);



}
```

```
<!-- For dark mode, apply a `.dark` class to <body> or a parent. -->



<body class="dark">



<button class="button">Button</button>



</body>
```

Light scales apply their CSS variables to the `:root` element and to the
`.light` and `.light-theme` classes. Dark scales apply their CSS variables to
the `.dark` and `.dark-theme` classes.

## [styled-components](#styled-components)

```
import {
	gray,
	blue,
	red,
	green,
	grayDark,
	blueDark,
	redDark,
	greenDark,
} from "@radix-ui/colors";



import styled, { ThemeProvider } from "styled-components";



// Create your theme



const theme = {



colors: {



...gray,



...blue,



...red,



...green,



},



};



// Create your dark theme



const darkTheme = {



colors: {



...grayDark,



...blueDark,



...redDark,



...greenDark,



},



};



// Use the colors in your styles



const Button = styled.button`
	background-color: ${(props) => props.theme.colors.blue4};
	color: ${(props) => props.theme.colors.blue11};
	border-color: ${(props) => props.theme.colors.blue7};
	&:hover {
		background-color: ${(props) => props.theme.colors.blue5};
		border-color: ${(props) => props.theme.colors.blue8};
	}
`;



// Wrap your app with the theme provider and apply your theme to it



export default function App() {



return (



<ThemeProvider theme={theme}>



<Button>Radix Colors</Button>



</ThemeProvider>



);



}
```

## [emotion](#emotion)

Usage with emotion is almost identical to the styled-components docs above, aside from the different imports.

```
import {
	gray,
	blue,
	red,
	green,
	grayDark,
	blueDark,
	redDark,
	greenDark,
} from "@radix-ui/colors";



import { ThemeProvider } from "@emotion/react";



import styled from "@emotion/styled";
```

## [vanilla-extract](#vanilla-extract)

```
import {
	gray,
	blue,
	red,
	green,
	grayDark,
	blueDark,
	redDark,
	greenDark,
} from "@radix-ui/colors";



import { createTheme } from "@vanilla-extract/css";



export const [theme, vars] = createTheme({



colors: {



...gray,



...blue,



...red,



...green,



},



});



export const darkTheme = createTheme(vars, {



colors: {



...grayDark,



...blueDark,



...redDark,



...greenDark,



},



});



// Use the colors in your styles



export const styles = {



button: style({



backgroundColor: vars.colors.blue4,



color: vars.colors.blue11,



borderColor: vars.colors.blue7,



":hover": {



backgroundColor: vars.colors.blue5,



borderColor: vars.colors.blue8,



},



}),



};



// Apply your theme to it



export default function App() {



return (



<body className={theme}>



<button className={styles.button}>Radix Colors</button>



</body>



);



}
```

#### Quick nav

Previous[Installation](/colors/docs/overview/installation)

Next[Aliasing](/colors/docs/overview/aliasing)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/colors/docs/overview/usage.mdx "Edit this page on GitHub.")
