Getting started â€“ Radix Primitives

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

Overview

# Getting started

A quick tutorial to get you up and running with Radix Primitives.

## [Implementing a Popover](#implementing-a-popover)

In this quick tutorial, we will install and style the [Popover](/primitives/docs/components/popover) component.

### [1. Install the primitive](#1-install-the-primitive)

Install Radix Primitives from your command line.

```
npm install radix-ui@latest
```

### [2. Import the parts](#2-import-the-parts)

Import and structure the parts.

```
// index.jsx



import * as React from "react";



import { Popover } from "radix-ui";



const PopoverDemo = () => (



<Popover.Root>



<Popover.Trigger>More info</Popover.Trigger>



<Popover.Portal>



<Popover.Content>



Some more infoâ€¦



<Popover.Arrow />



</Popover.Content>



</Popover.Portal>



</Popover.Root>



);



export default PopoverDemo;
```

### [3. Add your styles](#3-add-your-styles)

Add styles where desired.

```
// index.jsx



import * as React from "react";



import { Popover } from "radix-ui";



import "./styles.css";



const PopoverDemo = () => (



<Popover.Root>



<Popover.Trigger className="PopoverTrigger">Show info</Popover.Trigger>



<Popover.Portal>



<Popover.Content className="PopoverContent">



Some content



<Popover.Arrow className="PopoverArrow" />



</Popover.Content>



</Popover.Portal>



</Popover.Root>



);



export default PopoverDemo;
```

```
/* styles.css */



.PopoverTrigger {



background-color: white;



border-radius: 4px;



}



.PopoverContent {



border-radius: 4px;



padding: 20px;



width: 260px;



background-color: white;



}



.PopoverArrow {



fill: white;



}
```

### [Demo](#demo)

Here's a complete demo.

More info

index.jsxindex.jsxstyles.cssstyles.css

```
import * as React from "react";



import { Popover } from "radix-ui";



import "./styles.css";



const PopoverDemo = () => (



<Popover.Root>



<Popover.Trigger className="PopoverTrigger">More info</Popover.Trigger>



<Popover.Portal>



<Popover.Content className="PopoverContent" sideOffset={5}>



Some more infoâ€¦



<Popover.Arrow className="PopoverArrow" />



</Popover.Content>



</Popover.Portal>



</Popover.Root>



);



export default PopoverDemo;



Expand code
```

## [Summary](#summary)

The steps above outline briefly what's involved in using a Radix Primitive in your application.

These components are low-level enough to give you control over how you want to wrap them. You're free to introduce your own high-level API to better suit the needs of your team and product.

In a few simple steps, we've implemented a fully accessible Popover component, without having to worry about many of its complexities.

* Adheres to [WAI-ARIA](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal) design pattern.
* Can be controlled or uncontrolled.
* Customize side, alignment, offsets, collision handling.
* Optionally render a pointing arrow.
* Focus is fully managed and customizable.
* Dismissing and layering behavior is highly customizable.

#### Quick nav

Previous[Introduction](/primitives/docs/overview/introduction)

Next[Accessibility](/primitives/docs/overview/accessibility)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/primitives/docs/overview/getting-started.mdx "Edit this page on GitHub.")
