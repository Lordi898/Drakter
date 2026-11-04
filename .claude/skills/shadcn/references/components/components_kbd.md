# Kbd

Copy Page

[Previous](/docs/components/item)[Next](/docs/components/label)

Used to display textual user input from keyboard.

``⌘``⇧``⌥``⌃````Ctrl`+`B``

Copy
    
    
    import { Kbd, KbdGroup } from "@/components/ui/kbd"
    
    export function KbdDemo() {
      return (
        <div className="flex flex-col items-center gap-4">
          <KbdGroup>
            <Kbd>⌘</Kbd>
            <Kbd>⇧</Kbd>
            <Kbd>⌥</Kbd>
            <Kbd>⌃</Kbd>
          </KbdGroup>
          <KbdGroup>
            <Kbd>Ctrl</Kbd>
            <span>+</span>
            <Kbd>B</Kbd>
          </KbdGroup>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add kbd

Copy

## Usage
    
    
    Copyimport { Kbd } from "@/components/ui/kbd"
    
    
    Copy<Kbd>Ctrl</Kbd>

## Examples

### Group

Use the `KbdGroup` component to group keyboard keys together.

Use ``Ctrl + B``Ctrl + K`` to open the command palette

Copy
    
    
    import { Kbd, KbdGroup } from "@/components/ui/kbd"
    
    export function KbdGroupExample() {
      return (
        <div className="flex flex-col items-center gap-4">
          <p className="text-muted-foreground text-sm">
            Use{" "}
            <KbdGroup>
              <Kbd>Ctrl + B</Kbd>
              <Kbd>Ctrl + K</Kbd>
            </KbdGroup>{" "}
            to open the command palette
          </p>
        </div>
      )
    }
    

### Button

Use the `Kbd` component inside a `Button` component to display a keyboard key inside a button.

Accept `⏎`Cancel `Esc`

Copy
    
    
    import { Button } from "@/components/ui/button"
    import { Kbd } from "@/components/ui/kbd"
    
    export function KbdButton() {
      return (
        <div className="flex flex-wrap items-center gap-4">
          <Button variant="outline" size="sm" className="pr-2">
            Accept <Kbd>⏎</Kbd>
          </Button>
          <Button variant="outline" size="sm" className="pr-2">
            Cancel <Kbd>Esc</Kbd>
          </Button>
        </div>
      )
    }
    

### Tooltip

You can use the `Kbd` component inside a `Tooltip` component to display a tooltip with a keyboard key.

SavePrint

Copy
    
    
    import { Button } from "@/components/ui/button"
    import { ButtonGroup } from "@/components/ui/button-group"
    import { Kbd, KbdGroup } from "@/components/ui/kbd"
    import {
      Tooltip,
      TooltipContent,
      TooltipTrigger,
    } from "@/components/ui/tooltip"
    
    export function KbdTooltip() {
      return (
        <div className="flex flex-wrap gap-4">
          <ButtonGroup>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button size="sm" variant="outline">
                  Save
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <div className="flex items-center gap-2">
                  Save Changes <Kbd>S</Kbd>
                </div>
              </TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button size="sm" variant="outline">
                  Print
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <div className="flex items-center gap-2">
                  Print Document{" "}
                  <KbdGroup>
                    <Kbd>Ctrl</Kbd>
                    <Kbd>P</Kbd>
                  </KbdGroup>
                </div>
              </TooltipContent>
            </Tooltip>
          </ButtonGroup>
        </div>
      )
    }
    

### Input Group

You can use the `Kbd` component inside a `InputGroupAddon` component to display a keyboard key inside an input group.

`⌘``K`

Copy
    
    
    import { SearchIcon } from "lucide-react"
    
    import {
      InputGroup,
      InputGroupAddon,
      InputGroupInput,
    } from "@/components/ui/input-group"
    import { Kbd } from "@/components/ui/kbd"
    
    export function KbdInputGroup() {
      return (
        <div className="flex w-full max-w-xs flex-col gap-6">
          <InputGroup>
            <InputGroupInput placeholder="Search..." />
            <InputGroupAddon>
              <SearchIcon />
            </InputGroupAddon>
            <InputGroupAddon align="inline-end">
              <Kbd>⌘</Kbd>
              <Kbd>K</Kbd>
            </InputGroupAddon>
          </InputGroup>
        </div>
      )
    }
    

## API Reference

### Kbd

Use the `Kbd` component to display a keyboard key.

Prop| Type| Default  
---|---|---  
`className`| `string`| ``  
      
    
    Copy<Kbd>Ctrl</Kbd>

### KbdGroup

Use the `KbdGroup` component to group `Kbd` components together.

Prop| Type| Default  
---|---|---  
`className`| `string`| ``  
      
    
    Copy<KbdGroup>
      <Kbd>Ctrl</Kbd>
      <Kbd>B</Kbd>
    </KbdGroup>

[ Item](/docs/components/item)[Label ](/docs/components/label)
