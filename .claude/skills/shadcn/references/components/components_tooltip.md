# Tooltip

Copy Page

[Previous](/docs/components/toggle)[Next](/docs/components/typography)

A popup that displays information related to an element when the element receives keyboard focus or the mouse hovers over it.

[Docs ](https://www.radix-ui.com/docs/primitives/components/tooltip)[API Reference ](https://www.radix-ui.com/docs/primitives/components/tooltip#api-reference)

Hover

Copy
    
    
    import { Button } from "@/components/ui/button"
    import {
      Tooltip,
      TooltipContent,
      TooltipTrigger,
    } from "@/components/ui/tooltip"
    
    export function TooltipDemo() {
      return (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button variant="outline">Hover</Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>Add to library</p>
          </TooltipContent>
        </Tooltip>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add tooltip

Copy

## Usage
    
    
    Copyimport {
      Tooltip,
      TooltipContent,
      TooltipTrigger,
    } from "@/components/ui/tooltip"
    
    
    Copy<Tooltip>
      <TooltipTrigger>Hover</TooltipTrigger>
      <TooltipContent>
        <p>Add to library</p>
      </TooltipContent>
    </Tooltip>

* * *

## Changelog

### 2025-09-22 Update tooltip colors

We've updated the tooltip colors to use the foreground color for the background and the background color for the foreground.

Replace `bg-primary text-primary-foreground` with `bg-foreground text-background` for both `<TooltipContent />` and `<TooltipArrow />`.

[ Toggle](/docs/components/toggle)[Typography ](/docs/components/typography)
