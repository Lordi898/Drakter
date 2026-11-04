# Popover

Copy Page

[Previous](/docs/components/pagination)[Next](/docs/components/progress)

Displays rich content in a portal, triggered by a button.

[Docs ](https://www.radix-ui.com/docs/primitives/components/popover)[API Reference ](https://www.radix-ui.com/docs/primitives/components/popover#api-reference)

Open popover

Copy
    
    
    import { Button } from "@/components/ui/button"
    import { Input } from "@/components/ui/input"
    import { Label } from "@/components/ui/label"
    import {
      Popover,
      PopoverContent,
      PopoverTrigger,
    } from "@/components/ui/popover"
    
    export function PopoverDemo() {
      return (
        <Popover>
          <PopoverTrigger asChild>
            <Button variant="outline">Open popover</Button>
          </PopoverTrigger>
          <PopoverContent className="w-80">
            <div className="grid gap-4">
              <div className="space-y-2">
                <h4 className="leading-none font-medium">Dimensions</h4>
                <p className="text-muted-foreground text-sm">
                  Set the dimensions for the layer.
                </p>
              </div>
              <div className="grid gap-2">
                <div className="grid grid-cols-3 items-center gap-4">
                  <Label htmlFor="width">Width</Label>
                  <Input
                    id="width"
                    defaultValue="100%"
                    className="col-span-2 h-8"
                  />
                </div>
                <div className="grid grid-cols-3 items-center gap-4">
                  <Label htmlFor="maxWidth">Max. width</Label>
                  <Input
                    id="maxWidth"
                    defaultValue="300px"
                    className="col-span-2 h-8"
                  />
                </div>
                <div className="grid grid-cols-3 items-center gap-4">
                  <Label htmlFor="height">Height</Label>
                  <Input
                    id="height"
                    defaultValue="25px"
                    className="col-span-2 h-8"
                  />
                </div>
                <div className="grid grid-cols-3 items-center gap-4">
                  <Label htmlFor="maxHeight">Max. height</Label>
                  <Input
                    id="maxHeight"
                    defaultValue="none"
                    className="col-span-2 h-8"
                  />
                </div>
              </div>
            </div>
          </PopoverContent>
        </Popover>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add popover

Copy

## Usage
    
    
    Copyimport {
      Popover,
      PopoverContent,
      PopoverTrigger,
    } from "@/components/ui/popover"
    
    
    Copy<Popover>
      <PopoverTrigger>Open</PopoverTrigger>
      <PopoverContent>Place content for the popover here.</PopoverContent>
    </Popover>

[ Pagination](/docs/components/pagination)[Progress ](/docs/components/progress)
