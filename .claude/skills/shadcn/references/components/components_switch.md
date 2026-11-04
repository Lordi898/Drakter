# Switch

Copy Page

[Previous](/docs/components/spinner)[Next](/docs/components/table)

A control that allows the user to toggle between checked and not checked.

[Docs ](https://www.radix-ui.com/docs/primitives/components/switch)[API Reference ](https://www.radix-ui.com/docs/primitives/components/switch#api-reference)

Airplane Mode

Copy
    
    
    import { Label } from "@/components/ui/label"
    import { Switch } from "@/components/ui/switch"
    
    export function SwitchDemo() {
      return (
        <div className="flex items-center space-x-2">
          <Switch id="airplane-mode" />
          <Label htmlFor="airplane-mode">Airplane Mode</Label>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add switch

Copy

## Usage
    
    
    Copyimport { Switch } from "@/components/ui/switch"
    
    
    Copy<Switch />

[ Spinner](/docs/components/spinner)[Table ](/docs/components/table)
