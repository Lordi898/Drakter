# Scroll Area

Copy Page

[Previous](/docs/components/resizable)[Next](/docs/components/select)

Augments native scroll functionality for custom, cross-browser styling.

[Docs ](https://www.radix-ui.com/docs/primitives/components/scroll-area)[API Reference ](https://www.radix-ui.com/docs/primitives/components/scroll-area#api-reference)

#### Tags

v1.2.0-beta.50

v1.2.0-beta.49

v1.2.0-beta.48

v1.2.0-beta.47

v1.2.0-beta.46

v1.2.0-beta.45

v1.2.0-beta.44

v1.2.0-beta.43

v1.2.0-beta.42

v1.2.0-beta.41

v1.2.0-beta.40

v1.2.0-beta.39

v1.2.0-beta.38

v1.2.0-beta.37

v1.2.0-beta.36

v1.2.0-beta.35

v1.2.0-beta.34

v1.2.0-beta.33

v1.2.0-beta.32

v1.2.0-beta.31

v1.2.0-beta.30

v1.2.0-beta.29

v1.2.0-beta.28

v1.2.0-beta.27

v1.2.0-beta.26

v1.2.0-beta.25

v1.2.0-beta.24

v1.2.0-beta.23

v1.2.0-beta.22

v1.2.0-beta.21

v1.2.0-beta.20

v1.2.0-beta.19

v1.2.0-beta.18

v1.2.0-beta.17

v1.2.0-beta.16

v1.2.0-beta.15

v1.2.0-beta.14

v1.2.0-beta.13

v1.2.0-beta.12

v1.2.0-beta.11

v1.2.0-beta.10

v1.2.0-beta.9

v1.2.0-beta.8

v1.2.0-beta.7

v1.2.0-beta.6

v1.2.0-beta.5

v1.2.0-beta.4

v1.2.0-beta.3

v1.2.0-beta.2

v1.2.0-beta.1

Copy
    
    
    import * as React from "react"
    
    import { ScrollArea } from "@/components/ui/scroll-area"
    import { Separator } from "@/components/ui/separator"
    
    const tags = Array.from({ length: 50 }).map(
      (_, i, a) => `v1.2.0-beta.${a.length - i}`
    )
    
    export function ScrollAreaDemo() {
      return (
        <ScrollArea className="h-72 w-48 rounded-md border">
          <div className="p-4">
            <h4 className="mb-4 text-sm leading-none font-medium">Tags</h4>
            {tags.map((tag) => (
              <React.Fragment key={tag}>
                <div className="text-sm">{tag}</div>
                <Separator className="my-2" />
              </React.Fragment>
            ))}
          </div>
        </ScrollArea>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add scroll-area

Copy

## Usage
    
    
    Copyimport { ScrollArea } from "@/components/ui/scroll-area"
    
    
    Copy<ScrollArea className="h-[200px] w-[350px] rounded-md border p-4">
      Jokester began sneaking into the castle in the middle of the night and leaving
      jokes all over the place: under the king's pillow, in his soup, even in the
      royal toilet. The king was furious, but he couldn't seem to stop Jokester. And
      then, one day, the people of the kingdom discovered that the jokes left by
      Jokester were so funny that they couldn't help but laugh. And once they
      started laughing, they couldn't stop.
    </ScrollArea>

## Examples

### Horizontal Scrolling

![Photo by Ornella Binni](/_next/image?url=https%3A%2F%2Fimages.unsplash.com%2Fphoto-1465869185982-5a1a7522cbcb%3Fauto%3Dformat%26fit%3Dcrop%26w%3D300%26q%3D80&w=640&q=75)

Photo by Ornella Binni

![Photo by Tom Byrom](/_next/image?url=https%3A%2F%2Fimages.unsplash.com%2Fphoto-1548516173-3cabfa4607e9%3Fauto%3Dformat%26fit%3Dcrop%26w%3D300%26q%3D80&w=640&q=75)

Photo by Tom Byrom

![Photo by Vladimir Malyavko](/_next/image?url=https%3A%2F%2Fimages.unsplash.com%2Fphoto-1494337480532-3725c85fd2ab%3Fauto%3Dformat%26fit%3Dcrop%26w%3D300%26q%3D80&w=640&q=75)

Photo by Vladimir Malyavko

Copy
    
    
    import * as React from "react"
    import Image from "next/image"
    
    import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
    
    export interface Artwork {
      artist: string
      art: string
    }
    
    export const works: Artwork[] = [
      {
        artist: "Ornella Binni",
        art: "https://images.unsplash.com/photo-1465869185982-5a1a7522cbcb?auto=format&fit=crop&w=300&q=80",
      },
      {
        artist: "Tom Byrom",
        art: "https://images.unsplash.com/photo-1548516173-3cabfa4607e9?auto=format&fit=crop&w=300&q=80",
      },
      {
        artist: "Vladimir Malyavko",
        art: "https://images.unsplash.com/photo-1494337480532-3725c85fd2ab?auto=format&fit=crop&w=300&q=80",
      },
    ]
    
    export function ScrollAreaHorizontalDemo() {
      return (
        <ScrollArea className="w-96 rounded-md border whitespace-nowrap">
          <div className="flex w-max space-x-4 p-4">
            {works.map((artwork) => (
              <figure key={artwork.artist} className="shrink-0">
                <div className="overflow-hidden rounded-md">
                  <Image
                    src={artwork.art}
                    alt={`Photo by ${artwork.artist}`}
                    className="aspect-[3/4] h-fit w-fit object-cover"
                    width={300}
                    height={400}
                  />
                </div>
                <figcaption className="text-muted-foreground pt-2 text-xs">
                  Photo by{" "}
                  <span className="text-foreground font-semibold">
                    {artwork.artist}
                  </span>
                </figcaption>
              </figure>
            ))}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>
      )
    }
    

[ Resizable](/docs/components/resizable)[Select ](/docs/components/select)
