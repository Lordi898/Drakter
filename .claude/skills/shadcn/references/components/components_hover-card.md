# Hover Card

Copy Page

[Previous](/docs/components/form)[Next](/docs/components/input-group)

For sighted users to preview content available behind a link.

[Docs ](https://www.radix-ui.com/docs/primitives/components/hover-card)[API Reference ](https://www.radix-ui.com/docs/primitives/components/hover-card#api-reference)

@nextjs

Copy
    
    
    import { CalendarIcon } from "lucide-react"
    
    import {
      Avatar,
      AvatarFallback,
      AvatarImage,
    } from "@/components/ui/avatar"
    import { Button } from "@/components/ui/button"
    import {
      HoverCard,
      HoverCardContent,
      HoverCardTrigger,
    } from "@/components/ui/hover-card"
    
    export function HoverCardDemo() {
      return (
        <HoverCard>
          <HoverCardTrigger asChild>
            <Button variant="link">@nextjs</Button>
          </HoverCardTrigger>
          <HoverCardContent className="w-80">
            <div className="flex justify-between gap-4">
              <Avatar>
                <AvatarImage src="https://github.com/vercel.png" />
                <AvatarFallback>VC</AvatarFallback>
              </Avatar>
              <div className="space-y-1">
                <h4 className="text-sm font-semibold">@nextjs</h4>
                <p className="text-sm">
                  The React Framework – created and maintained by @vercel.
                </p>
                <div className="text-muted-foreground text-xs">
                  Joined December 2021
                </div>
              </div>
            </div>
          </HoverCardContent>
        </HoverCard>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add hover-card

Copy

## Usage
    
    
    Copyimport {
      HoverCard,
      HoverCardContent,
      HoverCardTrigger,
    } from "@/components/ui/hover-card"
    
    
    Copy<HoverCard>
      <HoverCardTrigger>Hover</HoverCardTrigger>
      <HoverCardContent>
        The React Framework – created and maintained by @vercel.
      </HoverCardContent>
    </HoverCard>

[ Form](/docs/components/form)[Input Group ](/docs/components/input-group)
