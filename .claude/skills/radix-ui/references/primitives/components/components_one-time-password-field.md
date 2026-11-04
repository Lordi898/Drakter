One-Time Password Field â€“ Radix Primitives

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

# One-Time Password Field

A group of single-character text inputs to handle one-time password
verification.

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { unstable_OneTimePasswordField as OneTimePasswordField } from "radix-ui";



const OneTimePasswordFieldDemo = () => (



<OneTimePasswordField.Root className="OTPRoot">



<OneTimePasswordField.Input className="OTPInput" />



<OneTimePasswordField.Input className="OTPInput" />



<OneTimePasswordField.Input className="OTPInput" />



<OneTimePasswordField.Input className="OTPInput" />



<OneTimePasswordField.Input className="OTPInput" />



<OneTimePasswordField.Input className="OTPInput" />



<OneTimePasswordField.HiddenInput />



</OneTimePasswordField.Root>



);



export default OneTimePasswordFieldDemo;



Expand code
```

## Features

Keyboard navigation mimicking the behavior of a single input field

Overriding values on paste

Password manager autofill support

Input validation for numeric and alphanumeric values

Auto-submit on completion

Hidden input to provide a single value to form data

## Component Reference Links

Version: 0.1.8

Size: [11.94 kB](https://bundlephobia.com/package/@radix-ui/react-one-time-password-field@0.1.8)

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/one-time-password-field/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

## [Anatomy](#anatomy)

Import all parts and piece them together.

```
import { unstable_OneTimePasswordField as OneTimePasswordField } from "radix-ui";



export default () => (



<OneTimePasswordField.Root>



{/* one Input for each character of the value */}



<OneTimePasswordField.Input />



{/* single HiddenInput to store the full value */}



<OneTimePasswordField.HiddenInput />



</OneTimePasswordField.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of a one-time password field.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `autoComplete` Prop description | `enum` See full type | `one-time-code` |
| `autoFocus` Prop description | `boolean` | No default value |
| `value` Prop description | `string` | No default value |
| `defaultValue` Prop description | `string` | No default value |
| `onValueChange` Prop description | `function` See full type | No default value |
| `autoSubmit` Prop description | `boolean` | `false` |
| `onAutoSubmit` Prop description | `function` See full type | No default value |
| `disabled` Prop description | `boolean` | `false` |
| `dir` Prop description | `enum` See full type | `"ltr"` |
| `orientation` Prop description | `enum` See full type | `"vertical"` |
| `form` Prop description | `string` | No default value |
| `name` Prop description | `string` | No default value |
| `placeholder` Prop description | `string` | No default value |
| `readOnly` Prop description | `boolean` | `false` |
| `sanitizeValue` Prop description | `function` See full type | No default value |
| `type` Prop description | `enum` See full type | `"text"` |
| `validationType` Prop description | `enum` See full type | `"numeric"` |

| Data attribute | Values |
| --- | --- |
| `[data-orientation]` | `"vertical" | "horizontal"` |

### [Input](#input)

Renders a text input representing a single character in the value.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-index]` | The index corresponding with the index of the character relative to the root field value |

### [HiddenInput](#hiddeninput)

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

## [Examples](#examples)

### [Basic usage](#basic-usage)

```
// This will render a field with 6 inputs, for use with



// 6-character passwords. Render an Input component for



// each character of accepted password's length.



<OneTimePasswordField.Root>



<OneTimePasswordField.Input />



<OneTimePasswordField.Input />



<OneTimePasswordField.Input />



<OneTimePasswordField.Input />



<OneTimePasswordField.Input />



<OneTimePasswordField.Input />



<OneTimePasswordField.HiddenInput />



</OneTimePasswordField.Root>
```

### [Segmented controls](#segmented-controls)

The `Root` component accepts arbitrary children, so rendering a visually segmented list is as simple as rendering separators between inputs. We recommend hiding decorative elements from assistive tech with `aria-hidden` and avoid rendering other meaningful content within `Root` since each child element is expected to belong to the parent with the `group` role.

```
<OneTimePasswordField.Root>



<OneTimePasswordField.Input />



<Separator.Root aria-hidden />



<OneTimePasswordField.Input />



<Separator.Root aria-hidden />



<OneTimePasswordField.Input />



<Separator.Root aria-hidden />



<OneTimePasswordField.Input />



<OneTimePasswordField.HiddenInput />



</OneTimePasswordField.Root>
```

### [Auto-submit form when password is entered](#auto-submit-form-when-password-is-entered)

Use the `autoSubmit` prop to submit an associated form when all inputs are filled.

```
function Verify({ validCode }) {



const PASSWORD_LENGTH = 6;



function handleSubmit(event) {



event.preventDefault();



const formData = event.formData;



if (formData.get("otp") === validCode) {



redirect("/authenticated");



} else {



window.alert("Invalid code");



}



}



return (



<form onSubmit={handleSubmit}>



<OneTimePasswordField.Root name="otp" autoSubmit>



{PASSWORD_LENGTH.map((_, i) => (



<OneTimePasswordField.Input key={i} />



))}



{/* HiddenInput is required for the form to have data associated with the field */}



<OneTimePasswordField.HiddenInput />



</OneTimePasswordField.Root>



<button>Submit</button>



</form>



);



}
```

### [Controlled value](#controlled-value)

```
function Verify({ validCode }) {



const [value, setValue] = React.useState("");



const PASSWORD_LENGTH = 6;



function handleSubmit() {



if (value === validCode) {



redirect("/authenticated");



} else {



window.alert("Invalid code");



}



}



return (



<OneTimePasswordField.Root
			autoSubmit
			value={value}
			onAutoSubmit={handleSubmit}
			onValueChange={setValue}
		>



{PASSWORD_LENGTH.map((_, i) => (



<OneTimePasswordField.Input key={i} />



))}



</OneTimePasswordField.Root>



);



}
```

## [Accessibility](#accessibility)

At the time of writing, there is no singular established pattern in WCAG guidelines for implementing one-time password fields as separate inputs. The behavior aims to get as close as possible to having the field act as a single input, with a few exceptions to match user expectations based on our initial research, testing, and gathering feedback.

This component is implemented as `input` elements within a container with a role of `group` to indicate that child inputs are related. Inputs can be navigated and focused using direction keys, and typing input will move focus to the next input until the last input is reached.

Pasting a value into the field will replace the contents of all inputs, regardless of the currently focused input. Based on our research this seems to align with most user expectations, where values are often pasted from password-managers or an email.

### [Keyboard Interactions](#keyboard-interactions)

| Key | Description |
| --- | --- |
| `Enter` | Attempts to submit an associated `form` if one is found |
| `Tab` | Moves focus to the next focusable element outside of the `Root` |
| `Shift + Tab` | Moves focus to the previous focusable element outside of the `Root` |
| `ArrowDown` | Moves focus to the next `Input` when `orientation` is `vertical`. |
| `ArrowUp` | Moves focus to the previous `Input` when `orientation` is `vertical`. |
| `ArrowRight` | Moves focus to the next `Input` when `orientation` is `horizontal`. |
| `ArrowLeft` | Moves focus to the previous `Input` when `orientation` is `horizontal`. |
| `Home` | Moves focus to the first `Input`. |
| `End` | Moves focus to the last `Input`. |
| `Delete` | Removes the character in the currently focused `Input` and shifts later values back |
| `Backspace` | Removes the character in the currently focused `Input` and moves focus to the previous `Input` |
| `Command + Backspace` | Clears the value of all `Input` elements |

#### Quick nav

Previous[Navigation Menu](/primitives/docs/components/navigation-menu)

Next[Password Toggle Field](/primitives/docs/components/password-toggle-field)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/one-time-password-field.mdx "Edit this page on GitHub.")
