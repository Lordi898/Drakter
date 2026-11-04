Alert Dialog â€“ Radix Primitives

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

# Alert Dialog

A modal dialog that interrupts the user with important content and expects a
response.

Delete account

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { AlertDialog } from "radix-ui";



import "./styles.css";



const AlertDialogDemo = () => (



<AlertDialog.Root>



<AlertDialog.Trigger asChild>



<button className="Button violet">Delete account</button>



</AlertDialog.Trigger>



<AlertDialog.Portal>



<AlertDialog.Overlay className="AlertDialogOverlay" />



<AlertDialog.Content className="AlertDialogContent">



<AlertDialog.Title className="AlertDialogTitle">



Are you absolutely sure?



</AlertDialog.Title>



<AlertDialog.Description className="AlertDialogDescription">



This action cannot be undone. This will permanently delete your



account and remove your data from our servers.



</AlertDialog.Description>



<div style={{ display: "flex", gap: 25, justifyContent: "flex-end" }}>



<AlertDialog.Cancel asChild>



<button className="Button mauve">Cancel</button>



</AlertDialog.Cancel>



<AlertDialog.Action asChild>



<button className="Button red">Yes, delete account</button>



</AlertDialog.Action>



</div>



</AlertDialog.Content>



</AlertDialog.Portal>



</AlertDialog.Root>



);



export default AlertDialogDemo;



Expand code
```

## Features

Focus is automatically trapped.

Can be controlled or uncontrolled.

Manages screen reader announcements with `Title` and `Description` components.

Esc closes the component automatically.

## Component Reference Links

Version: 1.1.15

Size: [13.9 kB](https://bundlephobia.com/package/@radix-ui/react-alert-dialog@1.1.15)

[View source](https://github.com/radix-ui/primitives/tree/main/packages/react/alert-dialog/src)

[Report an issue](https://github.com/radix-ui/primitives/issues/new/choose)

[ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/alertdialog)

## [Installation](#installation)

Install the component from your command line.

```
npm install @radix-ui/react-alert-dialog
```

## [Anatomy](#anatomy)

Import all parts and piece them together.

```
import { AlertDialog } from "radix-ui";



export default () => (



<AlertDialog.Root>



<AlertDialog.Trigger />



<AlertDialog.Portal>



<AlertDialog.Overlay />



<AlertDialog.Content>



<AlertDialog.Title />



<AlertDialog.Description />



<AlertDialog.Cancel />



<AlertDialog.Action />



</AlertDialog.Content>



</AlertDialog.Portal>



</AlertDialog.Root>



);
```

## [API Reference](#api-reference)

### [Root](#root)

Contains all the parts of an alert dialog.

| Prop | Type | Default |
| --- | --- | --- |
| `defaultOpen` Prop description | `boolean` | No default value |
| `open` Prop description | `boolean` | No default value |
| `onOpenChange` Prop description | `function` See full type | No default value |

### [Trigger](#trigger)

A button that opens the dialog.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |

### [Portal](#portal)

When used, portals your overlay and content parts into the `body`.

| Prop | Type | Default |
| --- | --- | --- |
| `forceMount` Prop description | `boolean` | No default value |
| `container` Prop description | `HTMLElement` | `document.body` |

### [Overlay](#overlay)

A layer that covers the inert portion of the view when the dialog is open.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `forceMount` Prop description | `boolean` | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |

### [Content](#content)

Contains content to be rendered when the dialog is open.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |
| `forceMount` Prop description | `boolean` | No default value |
| `onOpenAutoFocus` Prop description | `function` See full type | No default value |
| `onCloseAutoFocus` Prop description | `function` See full type | No default value |
| `onEscapeKeyDown` Prop description | `function` See full type | No default value |

| Data attribute | Values |
| --- | --- |
| `[data-state]` | `"open" | "closed"` |

### [Cancel](#cancel)

A button that closes the dialog. This button should be distinguished visually from `AlertDialog.Action` buttons.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Action](#action)

A button that closes the dialog. These buttons should be distinguished visually from the `AlertDialog.Cancel` button.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Title](#title)

An accessible name to be announced when the dialog is opened. Alternatively, you can provide `aria-label` or `aria-labelledby` to `AlertDialog.Content` and exclude this component.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

### [Description](#description)

An accessible description to be announced when the dialog is opened. Alternatively, you can provide `aria-describedby` to `AlertDialog.Content` and exclude this component.

| Prop | Type | Default |
| --- | --- | --- |
| `asChild` Prop description | `boolean` | `false` |

## [Examples](#examples)

### [Close after asynchronous form submission](#close-after-asynchronous-form-submission)

Use the controlled props to programmatically close the Alert Dialog after an async operation has completed.

```
import * as React from "react";



import { AlertDialog } from "radix-ui";



const wait = () => new Promise((resolve) => setTimeout(resolve, 1000));



export default () => {



const [open, setOpen] = React.useState(false);



return (



<AlertDialog.Root open={open} onOpenChange={setOpen}>



<AlertDialog.Trigger>Open</AlertDialog.Trigger>



<AlertDialog.Portal>



<AlertDialog.Overlay />



<AlertDialog.Content>



<form
						onSubmit={(event) => {
							wait().then(() => setOpen(false));
							event.preventDefault();
						}}
					>



{/** some inputs */}



<button type="submit">Submit</button>



</form>



</AlertDialog.Content>



</AlertDialog.Portal>



</AlertDialog.Root>



);



};
```

### [Custom portal container](#custom-portal-container)

Customise the element that your alert dialog portals into.

```
export default () => {



const [container, setContainer] = React.useState(null);



return (



<div>



<AlertDialog.Root>



<AlertDialog.Trigger />



<AlertDialog.Portal container={container}>



<AlertDialog.Overlay />



<AlertDialog.Content>...</AlertDialog.Content>



</AlertDialog.Portal>



</AlertDialog.Root>



<div ref={setContainer} />



</div>



);



};
```

## [Accessibility](#accessibility)

Adheres to the [Alert and Message Dialogs WAI-ARIA design pattern](https://www.w3.org/WAI/ARIA/apg/patterns/alertdialog).

### [Keyboard Interactions](#keyboard-interactions)

| Key | Description |
| --- | --- |
| `Space` | Opens/closes the dialog. |
| `Enter` | Opens/closes the dialog. |
| `Tab` | Moves focus to the next focusable element. |
| `Shift + Tab` | Moves focus to the previous focusable element. |
| `Esc` | Closes the dialog and moves focus to `AlertDialog.Trigger`. |

#### Quick nav

Previous[Accordion](/primitives/docs/components/accordion)

Next[Aspect Ratio](/primitives/docs/components/aspect-ratio)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/components/alert-dialog.mdx "Edit this page on GitHub.")
