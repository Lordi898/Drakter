# Label

Copy Page

[Previous](/docs/components/kbd)[Next](/docs/components/menubar)

Renders an accessible label associated with controls.

[Docs ](https://www.radix-ui.com/docs/primitives/components/label)[API Reference ](https://www.radix-ui.com/docs/primitives/components/label#api-reference)

Accept terms and conditions

Copy
    
    
    import { Checkbox } from "@/components/ui/checkbox"
    import { Label } from "@/components/ui/label"
    
    export function LabelDemo() {
      return (
        <div>
          <div className="flex items-center space-x-2">
            <Checkbox id="terms" />
            <Label htmlFor="terms">Accept terms and conditions</Label>
          </div>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add label

Copy

## Usage
    
    
    Copyimport { Label } from "@/components/ui/label"
    
    
    Copy<Label htmlFor="email">Your email address</Label>

[ Kbd](/docs/components/kbd)[Menubar ](/docs/components/menubar)
