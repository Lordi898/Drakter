# Aspect Ratio

Copy Page

[Previous](/docs/components/alert)[Next](/docs/components/avatar)

Displays content within a desired ratio.

[Docs ](https://www.radix-ui.com/docs/primitives/components/aspect-ratio)[API Reference ](https://www.radix-ui.com/docs/primitives/components/aspect-ratio#api-reference)

![Photo by Drew Beamer](/_next/image?url=https%3A%2F%2Fimages.unsplash.com%2Fphoto-1588345921523-c2dcdb7f1dcd%3Fw%3D800%26dpr%3D2%26q%3D80&w=3840&q=75)

Copy
    
    
    import Image from "next/image"
    
    import { AspectRatio } from "@/components/ui/aspect-ratio"
    
    export function AspectRatioDemo() {
      return (
        <AspectRatio ratio={16 / 9} className="bg-muted rounded-lg">
          <Image
            src="https://images.unsplash.com/photo-1588345921523-c2dcdb7f1dcd?w=800&dpr=2&q=80"
            alt="Photo by Drew Beamer"
            fill
            className="h-full w-full rounded-lg object-cover dark:brightness-[0.2] dark:grayscale"
          />
        </AspectRatio>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add aspect-ratio

Copy

## Usage
    
    
    Copyimport { AspectRatio } from "@/components/ui/aspect-ratio"
    
    
    Copy<AspectRatio ratio={16 / 9}>
      <Image src="..." alt="Image" className="rounded-md object-cover" />
    </AspectRatio>

[ Alert](/docs/components/alert)[Avatar ](/docs/components/avatar)
