# Separator

Copy Page

[Previous](/docs/components/select)[Next](/docs/components/sheet)

Visually or semantically separates content.

[Docs ](https://www.radix-ui.com/docs/primitives/components/separator)[API Reference ](https://www.radix-ui.com/docs/primitives/components/separator#api-reference)

#### Radix Primitives

An open-source UI component library.

Blog

Docs

Source

Copy
    
    
    import { Separator } from "@/components/ui/separator"
    
    export function SeparatorDemo() {
      return (
        <div>
          <div className="space-y-1">
            <h4 className="text-sm leading-none font-medium">Radix Primitives</h4>
            <p className="text-muted-foreground text-sm">
              An open-source UI component library.
            </p>
          </div>
          <Separator className="my-4" />
          <div className="flex h-5 items-center space-x-4 text-sm">
            <div>Blog</div>
            <Separator orientation="vertical" />
            <div>Docs</div>
            <Separator orientation="vertical" />
            <div>Source</div>
          </div>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add separator

Copy

## Usage
    
    
    Copyimport { Separator } from "@/components/ui/separator"
    
    
    Copy<Separator />

[ Select](/docs/components/select)[Sheet ](/docs/components/sheet)
