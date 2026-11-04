# Input

Copy Page

[Previous](/docs/components/input-otp)[Next](/docs/components/item)

Displays a form input field or a component that looks like an input field.

Copy
    
    
    import { Input } from "@/components/ui/input"
    
    export function InputDemo() {
      return <Input type="email" placeholder="Email" />
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add input

Copy

## Usage
    
    
    Copyimport { Input } from "@/components/ui/input"
    
    
    Copy<Input />

## Examples

### Default

Copy
    
    
    import { Input } from "@/components/ui/input"
    
    export function InputDemo() {
      return <Input type="email" placeholder="Email" />
    }
    

### File

Picture

Copy
    
    
    import { Input } from "@/components/ui/input"
    import { Label } from "@/components/ui/label"
    
    export function InputFile() {
      return (
        <div className="grid w-full max-w-sm items-center gap-3">
          <Label htmlFor="picture">Picture</Label>
          <Input id="picture" type="file" />
        </div>
      )
    }
    

### Disabled

Copy
    
    
    import { Input } from "@/components/ui/input"
    
    export function InputDisabled() {
      return <Input disabled type="email" placeholder="Email" />
    }
    

### With Label

Email

Copy
    
    
    import { Input } from "@/components/ui/input"
    import { Label } from "@/components/ui/label"
    
    export function InputWithLabel() {
      return (
        <div className="grid w-full max-w-sm items-center gap-3">
          <Label htmlFor="email">Email</Label>
          <Input type="email" id="email" placeholder="Email" />
        </div>
      )
    }
    

### With Button

Subscribe

Copy
    
    
    import { Button } from "@/components/ui/button"
    import { Input } from "@/components/ui/input"
    
    export function InputWithButton() {
      return (
        <div className="flex w-full max-w-sm items-center gap-2">
          <Input type="email" placeholder="Email" />
          <Button type="submit" variant="outline">
            Subscribe
          </Button>
        </div>
      )
    }
    

## Changelog

### 2025-09-18 Remove `flex` class

Edit `input.tsx` and remove the `flex` class from the input component. This is no longer needed.

[ Input OTP](/docs/components/input-otp)[Item ](/docs/components/item)
