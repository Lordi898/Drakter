# Checkbox

Copy Page

[Previous](/docs/components/chart)[Next](/docs/components/collapsible)

A control that allows the user to toggle between checked and not checked.

[Docs ](https://www.radix-ui.com/docs/primitives/components/checkbox)[API Reference ](https://www.radix-ui.com/docs/primitives/components/checkbox#api-reference)

Accept terms and conditions

Accept terms and conditions

By clicking this checkbox, you agree to the terms and conditions.

Enable notifications

Enable notifications

You can enable or disable notifications at any time.

Copy
    
    
    "use client"
    
    import { Checkbox } from "@/components/ui/checkbox"
    import { Label } from "@/components/ui/label"
    
    export function CheckboxDemo() {
      return (
        <div className="flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <Checkbox id="terms" />
            <Label htmlFor="terms">Accept terms and conditions</Label>
          </div>
          <div className="flex items-start gap-3">
            <Checkbox id="terms-2" defaultChecked />
            <div className="grid gap-2">
              <Label htmlFor="terms-2">Accept terms and conditions</Label>
              <p className="text-muted-foreground text-sm">
                By clicking this checkbox, you agree to the terms and conditions.
              </p>
            </div>
          </div>
          <div className="flex items-start gap-3">
            <Checkbox id="toggle" disabled />
            <Label htmlFor="toggle">Enable notifications</Label>
          </div>
          <Label className="hover:bg-accent/50 flex items-start gap-3 rounded-lg border p-3 has-[[aria-checked=true]]:border-blue-600 has-[[aria-checked=true]]:bg-blue-50 dark:has-[[aria-checked=true]]:border-blue-900 dark:has-[[aria-checked=true]]:bg-blue-950">
            <Checkbox
              id="toggle-2"
              defaultChecked
              className="data-[state=checked]:border-blue-600 data-[state=checked]:bg-blue-600 data-[state=checked]:text-white dark:data-[state=checked]:border-blue-700 dark:data-[state=checked]:bg-blue-700"
            />
            <div className="grid gap-1.5 font-normal">
              <p className="text-sm leading-none font-medium">
                Enable notifications
              </p>
              <p className="text-muted-foreground text-sm">
                You can enable or disable notifications at any time.
              </p>
            </div>
          </Label>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add checkbox

Copy

## Usage
    
    
    Copyimport { Checkbox } from "@/components/ui/checkbox"
    
    
    Copy<Checkbox />

[ Chart](/docs/components/chart)[Collapsible ](/docs/components/collapsible)
