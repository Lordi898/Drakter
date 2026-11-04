Use cases â€“ Radix Colors

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[ThemesThemes](/)[PrimitivesPrimitives](/primitives)[IconsIcons](/icons)[ColorsColors](/colors)

[Documentation](/colors/docs)[Custom palette](/colors/custom)[Blog](/blog)

#### Overview

[Installation](/colors/docs/overview/installation)[Usage](/colors/docs/overview/usage)[Aliasing](/colors/docs/overview/aliasing)[Custom palettes](/colors/docs/overview/custom-palettes)[Releases](/colors/docs/overview/releases)

#### Palette composition

[Scales](/colors/docs/palette-composition/scales)[Composing a palette](/colors/docs/palette-composition/composing-a-palette)[Understanding the scale](/colors/docs/palette-composition/understanding-the-scale)

# Understanding the scale

Learn which scale step is the most appropriate for each use case.

## [Use cases](#use-cases)

There are 12 steps in each scale. Each step was designed for at least one specific use case.

This table is a simple overview of the most common use case for each step. However, there are many exceptions and caveats to factor in, which are covered in further detail below.

| Step | Use Case |
| --- | --- |
| 1 | App background |
| 2 | Subtle background |
| 3 | UI element background |
| 4 | Hovered UI element background |
| 5 | Active / Selected UI element background |
| 6 | Subtle borders and separators |
| 7 | UI element border and focus rings |
| 8 | Hovered UI element border |
| 9 | Solid backgrounds |
| 10 | Hovered solid backgrounds |
| 11 | Low-contrast text |
| 12 | High-contrast text |

## [Steps 1â€“2: Backgrounds](#steps-12-backgrounds)

1

2

Steps `1` and `2` are designed for app backgrounds and subtle component backgrounds. You can use them interchangeably, depending on the vibe you're going for.

Appropriate applications include:

* Main app background
* Striped table background
* Code block background
* Card background
* Sidebar background
* Canvas area background

You may want to use white for your app background in light mode, and Step `1`
or `2` from a gray or coloured scale in dark mode. In this case, set up a
[mutable alias](/colors/docs/overview/aliasing#mutable-aliases) for `AppBg`
and map it to a different color for each color mode.

## [Steps 3â€“5: Component backgrounds](#steps-35-component-backgrounds)

3

4

5

Steps `3`, `4`, and `5` are designed for UI component backgrounds.

* Step `3` is for normal states.
* Step `4` is for hover states.
* Step `5` is for pressed or selected states.

Menu itemSecond menu itemThird menu item

Menu itemSecond menu itemThird menu item

If your component has a transparent background in its default state, you can use Step `3` for its hover state.

Steps `11` and `12`â€”which are designed for textâ€”are guaranteed to Lc 60 and Lc
90 APCA contrast ratio on top of a step `2` background from the same scale.

## [Steps 6â€“8: Borders](#steps-68-borders)

6

7

8

Steps `6`, `7`, and `8` are designed for borders.

* Step `6` is designed for subtle borders on components which are not interactive. For example sidebars, headers, cards, alerts, and separators.
* Step `7` is designed for subtle borders on interactive components.
* Step `8` is designed for stronger borders on interactive components and focus rings.

GoldBronzeBrownYellowAmberOrangeTomatoRedRubyCrimsonPinkPlumPurpleVioletIrisIndigoBlueCyanTealJadeGreenGrassLimeMintSky

## [Steps 9â€“10: Solid backgrounds](#steps-910-solid-backgrounds)

9

10

Steps `9` and `10` are designed for solid backgrounds.

Step `9` has the highest chroma of all steps in the scale. In other words, it's the purest step, the step mixed with the least amount of white or black. Because `9` is the purest step, it has a wide range of applications:

* Website/App backgrounds
* Website section backgrounds
* Header backgrounds
* Component backgrounds
* Graphics/Logos
* Overlays
* Coloured shadows
* Accent borders

Step `10` is designed for component hover states, where step `9` is the component's normal state background.

Most step 9 colors are designed for white foreground text. `Sky`, `Mint`,
`Lime`, `Yellow`, and `Amber` are designed for dark foreground text and steps
`9` and `10`.

GoldBronzeBrownYellowAmberOrangeTomatoRedRubyCrimsonPinkPlumPurpleVioletIrisIndigoBlueCyanTealJadeGreenGrassLimeMintSky

## [Steps 11â€“12: Text](#steps-1112-text)

11

12

Steps `11` and `12` are designed for text.

* Step `11` is designed for low-contrast text.
* Step `12` is designed for high-contrast text.

This text is Pink 11This text is Slate 11This text is Gray 11This text is Pink 12This text is Slate 12This text is Gray 12

#### Quick nav

Previous[Composing a palette](/colors/docs/palette-composition/composing-a-palette)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/colors/docs/palette-composition/understanding-the-scale.mdx "Edit this page on GitHub.")
