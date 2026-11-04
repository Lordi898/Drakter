# Textarea

Copy Page

[Previous](/docs/components/tabs)[Next](/docs/components/toast)

Displays a form textarea or a component that looks like a textarea.

Copy
    
    
    import { Textarea } from "@/components/ui/textarea"
    
    export function TextareaDemo() {
      return <Textarea placeholder="Type your message here." />
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add textarea

Copy

## Usage
    
    
    Copyimport { Textarea } from "@/components/ui/textarea"
    
    
    Copy<Textarea />

## Examples

### Default

Copy
    
    
    import { Textarea } from "@/components/ui/textarea"
    
    export function TextareaDemo() {
      return <Textarea placeholder="Type your message here." />
    }
    

### Disabled

Copy
    
    
    import { Textarea } from "@/components/ui/textarea"
    
    export function TextareaDisabled() {
      return <Textarea placeholder="Type your message here." disabled />
    }
    

### With Label

Your message

Copy
    
    
    import { Label } from "@/components/ui/label"
    import { Textarea } from "@/components/ui/textarea"
    
    export function TextareaWithLabel() {
      return (
        <div className="grid w-full gap-3">
          <Label htmlFor="message">Your message</Label>
          <Textarea placeholder="Type your message here." id="message" />
        </div>
      )
    }
    

### With Text

Your Message

Your message will be copied to the support team.

Copy
    
    
    import { Label } from "@/components/ui/label"
    import { Textarea } from "@/components/ui/textarea"
    
    export function TextareaWithText() {
      return (
        <div className="grid w-full gap-3">
          <Label htmlFor="message-2">Your Message</Label>
          <Textarea placeholder="Type your message here." id="message-2" />
          <p className="text-muted-foreground text-sm">
            Your message will be copied to the support team.
          </p>
        </div>
      )
    }
    

### With Button

Send message

Copy
    
    
    import { Button } from "@/components/ui/button"
    import { Textarea } from "@/components/ui/textarea"
    
    export function TextareaWithButton() {
      return (
        <div className="grid w-full gap-2">
          <Textarea placeholder="Type your message here." />
          <Button>Send message</Button>
        </div>
      )
    }
    

[ Tabs](/docs/components/tabs)[Toast ](/docs/components/toast)
