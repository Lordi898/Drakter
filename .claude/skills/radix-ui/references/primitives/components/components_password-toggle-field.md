Password Toggle Field â€“ Radix Primitives

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[ThemesThemes](/)[PrimitivesPrimitives](/primitives)[IconsIcons](/icons)[ColorsColors](/colors)

[Documentation](/primitives/docs)[Case studies](/primitives/case-studies)[Blog](/blog)

Search

`/`

#### Overview

[Introduction](/primitives/docs/overview/introduction)[Getting started](/primitives/docs/overview/getting-started)[Accessibility](/primitives/docs/overview/accessibility)[Releases](/primitives/docs/overview/releases)

#### Guides

[Styling](/primitives/docs/guides/styling)[Animation](/primitives/docs/guides/animation)[Composition](/primitives/docs/guides/composition)[Server-side rendering](/primitives/docs/guides/server-side-rendering)

#### Components

[Accordion](/primitives/docs/components/accordion)[Alert Dialog](/primitives/docs/components/alert-dialog)[Aspect Ratio](/primitives/docs/components/aspect-ratio)[Avatar](/primitives/docs/components/avatar)[Checkbox](/primitives/docs/components/checkbox)[Collapsible](/primitives/docs/components/collapsible)[Context Menu](/primitives/docs/components/context-menu)[Dialog](/primitives/docs/components/dialog)[Dropdown Menu](/primitives/docs/components/dropdown-menu)[Form

Preview](/primitives/docs/components/form)[Hover Card](/primitives/docs/components/hover-card)[Label](/primitives/docs/components/label)[Menubar](/primitives/docs/components/menubar)[Navigation Menu](/primitives/docs/components/navigation-menu)[One-Time Password Field

Preview](/primitives/docs/components/one-time-password-field)[Password Toggle Field

Preview](/primitives/docs/components/password-toggle-field)[Popover](/primitives/docs/components/popover)[Progress](/primitives/docs/components/progress)[Radio Group](/primitives/docs/components/radio-group)[Scroll Area](/primitives/docs/components/scroll-area)[Select](/primitives/docs/components/select)[Separator](/primitives/docs/components/separator)[Slider](/primitives/docs/components/slider)[Switch](/primitives/docs/components/switch)[Tabs](/primitives/docs/components/tabs)[Toast](/primitives/docs/components/toast)[Toggle](/primitives/docs/components/toggle)[Toggle Group](/primitives/docs/components/toggle-group)[Toolbar](/primitives/docs/components/toolbar)[Tooltip](/primitives/docs/components/tooltip)

#### Utilities

[Accessible Icon](/primitives/docs/utilities/accessible-icon)[Direction Provider](/primitives/docs/utilities/direction-provider)[Portal](/primitives/docs/utilities/portal)[Slot](/primitives/docs/utilities/slot)[Visually Hidden](/primitives/docs/utilities/visually-hidden)

Components

# Password Toggle Field

A password input field with an integrated button to toggle the value's
visibility.

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { unstable_PasswordToggleField as PasswordToggleField } from "radix-ui";



import { EyeClosedIcon, EyeOpenIcon } from "@radix-ui/react-icons";



const PasswordToggleFieldDemo = () => (



<PasswordToggleField.Root>



<div className="Root">



<PasswordToggleField.Input className="Input" />



<PasswordToggleField.Toggle className="Toggle">



<PasswordToggleField.Icon
					visible={<EyeOpenIcon />}
					hidden={<EyeClosedIcon />}
				/>



</PasswordToggleField.Toggle>



</div>



</PasswordToggleField.Root>



);



export default PasswordToggleFieldDemo;



Expand code
```

## Features

Returns focus to the input when toggling with a pointer

Maintains button focus when toggling with keyboard or virtual navigation

Resets visibility to hidden after form submission to prevent accidental storage

Implicit accessible labeling for icon-based toggle buttons

## Component Reference Links

Version: 0.1.3

Size: [5.19 kB](https://bundlephobia.com/package/@radix-ui/react-password-toggle-field@0.1.3)

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/password-toggle-field/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

## [Anatomy](#anatomy)

Import all parts and piece them together.

```
import { unstable_PasswordToggleField as PasswordToggleField } from "radix-ui";



import { EyeClosedIcon, EyeOpenIcon } from "@radix-ui/react-icons";



export default () => (



<PasswordToggleField.Root>



<PasswordToggleField.Input />



<PasswordToggleField.Toggle>



<PasswordToggleField.Icon
				visible={<EyeOpenIcon />}
				hidden={<EyeClosedIcon />}
			/>



</PasswordToggleField.Toggle>



</PasswordToggleField.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of a password toggle field.

| Prop | Type | Default |
| --- | --- | --- |
| `id` Prop description | `string` | No default value |
| `visible` Prop description | `boolean` | No default value |
| `defaultVisible` Prop description | `boolean` | No default value |
| `onVisiblityChange` Prop description | `function` See full type | No default value |

### [Input](#input)

Renders a the input containing the password value.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `autoComplete` Prop description | `enum` See full type | `"current-password"` |

### [Toggle](#toggle)

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Slot](#slot)

| Prop | Type | Default |
| --- | --- | --- |
| `render` Prop description | `function` See full type | No default value |
| `visible` Prop description | `boolean` | No default value |
| `hidden` Prop description | `boolean` | No default value |

### [Icon](#icon)

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `visible*` Prop description | `boolean` | No default value |
| `hidden*` Prop description | `boolean` | No default value |

## [Examples](#examples)

### [Basic usage](#basic-usage)

```
<PasswordToggleField.Root>



<PasswordToggleField.Input />



<PasswordToggleField.Toggle>



<PasswordToggleField.Icon
			visible={<EyeOpenIcon />}
			hidden={<EyeClosedIcon />}
		/>



</PasswordToggleField.Toggle>



</PasswordToggleField.Root>
```

### [With `Slot`](#with-slot)

```
<PasswordToggleField.Root>



<PasswordToggleField.Input />



<PasswordToggleField.Toggle>



<PasswordToggleField.Slot visible="ðŸ™Š" hidden="ðŸ™ˆ" />



</PasswordToggleField.Toggle>



</PasswordToggleField.Root>
```

### [With `Slot` + `render` prop](#with-slot--render-prop)

```
<PasswordToggleField.Root>



<PasswordToggleField.Input />



<PasswordToggleField.Toggle>



<PasswordToggleField.Slot
			render={({ visible }) => (
				<svg aria-hidden viewBox="0 0 2 2" xmlns="http://www.w3.org/2000/svg">
					<path d={visible ? "M1 1 L2 2" : "M2 1 L1 2"} />
				</svg>
			)}
		/>



</PasswordToggleField.Toggle>



</PasswordToggleField.Root>
```

#### Quick nav

Previous[One-Time Password Field](/primitives/docs/components/one-time-password-field)

Next[Popover](/primitives/docs/components/popover)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/password-toggle-field.mdx "Edit this page on GitHub.")
