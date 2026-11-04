# Radio Group

Copy Page

[Previous](/docs/components/progress)[Next](/docs/components/resizable)

A set of checkable buttons—known as radio buttons—where no more than one of the buttons can be checked at a time.

[Docs ](https://www.radix-ui.com/docs/primitives/components/radio-group)[API Reference ](https://www.radix-ui.com/docs/primitives/components/radio-group#api-reference)

Default

Comfortable

Compact

Copy
    
    
    import { Label } from "@/components/ui/label"
    import {
      RadioGroup,
      RadioGroupItem,
    } from "@/components/ui/radio-group"
    
    export function RadioGroupDemo() {
      return (
        <RadioGroup defaultValue="comfortable">
          <div className="flex items-center gap-3">
            <RadioGroupItem value="default" id="r1" />
            <Label htmlFor="r1">Default</Label>
          </div>
          <div className="flex items-center gap-3">
            <RadioGroupItem value="comfortable" id="r2" />
            <Label htmlFor="r2">Comfortable</Label>
          </div>
          <div className="flex items-center gap-3">
            <RadioGroupItem value="compact" id="r3" />
            <Label htmlFor="r3">Compact</Label>
          </div>
        </RadioGroup>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add radio-group

Copy

## Usage
    
    
    Copyimport { Label } from "@/components/ui/label"
    import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
    
    
    Copy<RadioGroup defaultValue="option-one">
      <div className="flex items-center space-x-2">
        <RadioGroupItem value="option-one" id="option-one" />
        <Label htmlFor="option-one">Option One</Label>
      </div>
      <div className="flex items-center space-x-2">
        <RadioGroupItem value="option-two" id="option-two" />
        <Label htmlFor="option-two">Option Two</Label>
      </div>
    </RadioGroup>

[ Progress](/docs/components/progress)[Resizable ](/docs/components/resizable)
