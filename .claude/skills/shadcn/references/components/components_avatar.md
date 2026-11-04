# Avatar

Copy Page

[Previous](/docs/components/aspect-ratio)[Next](/docs/components/badge)

An image element with a fallback for representing the user.

[Docs ](https://www.radix-ui.com/docs/primitives/components/avatar)[API Reference ](https://www.radix-ui.com/docs/primitives/components/avatar#api-reference)

CNER

CNLRER

Copy
    
    
    import {
      Avatar,
      AvatarFallback,
      AvatarImage,
    } from "@/components/ui/avatar"
    
    export function AvatarDemo() {
      return (
        <div className="flex flex-row flex-wrap items-center gap-12">
          <Avatar>
            <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
            <AvatarFallback>CN</AvatarFallback>
          </Avatar>
          <Avatar className="rounded-lg">
            <AvatarImage
              src="https://github.com/evilrabbit.png"
              alt="@evilrabbit"
            />
            <AvatarFallback>ER</AvatarFallback>
          </Avatar>
          <div className="*:data-[slot=avatar]:ring-background flex -space-x-2 *:data-[slot=avatar]:ring-2 *:data-[slot=avatar]:grayscale">
            <Avatar>
              <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
              <AvatarFallback>CN</AvatarFallback>
            </Avatar>
            <Avatar>
              <AvatarImage
                src="https://github.com/maxleiter.png"
                alt="@maxleiter"
              />
              <AvatarFallback>LR</AvatarFallback>
            </Avatar>
            <Avatar>
              <AvatarImage
                src="https://github.com/evilrabbit.png"
                alt="@evilrabbit"
              />
              <AvatarFallback>ER</AvatarFallback>
            </Avatar>
          </div>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add avatar

Copy

## Usage
    
    
    Copyimport { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
    
    
    Copy<Avatar>
      <AvatarImage src="https://github.com/shadcn.png" />
      <AvatarFallback>CN</AvatarFallback>
    </Avatar>

[ Aspect Ratio](/docs/components/aspect-ratio)[Badge ](/docs/components/badge)
