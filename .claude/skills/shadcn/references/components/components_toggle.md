# Toggle

Copy Page

[Previous](/docs/components/toggle-group)[Next](/docs/components/tooltip)

A two-state button that can be either on or off.

[Docs ](https://www.radix-ui.com/docs/primitives/components/toggle)[API Reference ](https://www.radix-ui.com/docs/primitives/components/toggle#api-reference)

Bookmark

Copy
    
    
    import { BookmarkIcon } from "lucide-react"
    
    import { Toggle } from "@/components/ui/toggle"
    
    export function ToggleDemo() {
      return (
        <Toggle
          aria-label="Toggle bookmark"
          size="sm"
          variant="outline"
          className="data-[state=on]:bg-transparent data-[state=on]:*:[svg]:fill-blue-500 data-[state=on]:*:[svg]:stroke-blue-500"
        >
          <BookmarkIcon />
          Bookmark
        </Toggle>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add toggle

Copy

## Usage
    
    
    Copyimport { Toggle } from "@/components/ui/toggle"
    
    
    Copy<Toggle>Toggle</Toggle>

## Examples

### Default

Bookmark

Copy
    
    
    import { BookmarkIcon } from "lucide-react"
    
    import { Toggle } from "@/components/ui/toggle"
    
    export function ToggleDemo() {
      return (
        <Toggle
          aria-label="Toggle bookmark"
          size="sm"
          variant="outline"
          className="data-[state=on]:bg-transparent data-[state=on]:*:[svg]:fill-blue-500 data-[state=on]:*:[svg]:stroke-blue-500"
        >
          <BookmarkIcon />
          Bookmark
        </Toggle>
      )
    }
    

### Outline

Copy
    
    
    import { Italic } from "lucide-react"
    
    import { Toggle } from "@/components/ui/toggle"
    
    export function ToggleOutline() {
      return (
        <Toggle variant="outline" aria-label="Toggle italic">
          <Italic />
        </Toggle>
      )
    }
    

### With Text

Italic

Copy
    
    
    import { Italic } from "lucide-react"
    
    import { Toggle } from "@/components/ui/toggle"
    
    export function ToggleWithText() {
      return (
        <Toggle aria-label="Toggle italic">
          <Italic />
          Italic
        </Toggle>
      )
    }
    

### Small

Copy
    
    
    import { Italic } from "lucide-react"
    
    import { Toggle } from "@/components/ui/toggle"
    
    export function ToggleSm() {
      return (
        <Toggle size="sm" aria-label="Toggle italic">
          <Italic />
        </Toggle>
      )
    }
    

### Large

Copy
    
    
    import { Italic } from "lucide-react"
    
    import { Toggle } from "@/components/ui/toggle"
    
    export function ToggleLg() {
      return (
        <Toggle size="lg" aria-label="Toggle italic">
          <Italic />
        </Toggle>
      )
    }
    

### Disabled

Copy
    
    
    import { Underline } from "lucide-react"
    
    import { Toggle } from "@/components/ui/toggle"
    
    export function ToggleDisabled() {
      return (
        <Toggle aria-label="Toggle italic" disabled>
          <Underline className="h-4 w-4" />
        </Toggle>
      )
    }
    

[ Toggle Group](/docs/components/toggle-group)[Tooltip ](/docs/components/tooltip)
