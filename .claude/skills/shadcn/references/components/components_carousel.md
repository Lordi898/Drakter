# Carousel

Copy Page

[Previous](/docs/components/card)[Next](/docs/components/chart)

A carousel with motion and swipe built using Embla.

[Docs ](https://www.embla-carousel.com/get-started/react)[API Reference ](https://www.embla-carousel.com/api)

1

2

3

4

5

Previous slideNext slide

Copy
    
    
    import * as React from "react"
    
    import { Card, CardContent } from "@/components/ui/card"
    import {
      Carousel,
      CarouselContent,
      CarouselItem,
      CarouselNext,
      CarouselPrevious,
    } from "@/components/ui/carousel"
    
    export function CarouselDemo() {
      return (
        <Carousel className="w-full max-w-xs">
          <CarouselContent>
            {Array.from({ length: 5 }).map((_, index) => (
              <CarouselItem key={index}>
                <div className="p-1">
                  <Card>
                    <CardContent className="flex aspect-square items-center justify-center p-6">
                      <span className="text-4xl font-semibold">{index + 1}</span>
                    </CardContent>
                  </Card>
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
          <CarouselPrevious />
          <CarouselNext />
        </Carousel>
      )
    }
    

## About

The carousel component is built using the [Embla Carousel](https://www.embla-carousel.com/) library.

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add carousel

Copy

## Usage
    
    
    Copyimport {
      Carousel,
      CarouselContent,
      CarouselItem,
      CarouselNext,
      CarouselPrevious,
    } from "@/components/ui/carousel"
    
    
    Copy<Carousel>
      <CarouselContent>
        <CarouselItem>...</CarouselItem>
        <CarouselItem>...</CarouselItem>
        <CarouselItem>...</CarouselItem>
      </CarouselContent>
      <CarouselPrevious />
      <CarouselNext />
    </Carousel>

## Examples

### Sizes

To set the size of the items, you can use the `basis` utility class on the `<CarouselItem />`.

1

2

3

4

5

Previous slideNext slide

Copy
    
    
    import * as React from "react"
    
    import { Card, CardContent } from "@/components/ui/card"
    import {
      Carousel,
      CarouselContent,
      CarouselItem,
      CarouselNext,
      CarouselPrevious,
    } from "@/components/ui/carousel"
    
    export function CarouselSize() {
      return (
        <Carousel
          opts={{
            align: "start",
          }}
          className="w-full max-w-sm"
        >
          <CarouselContent>
            {Array.from({ length: 5 }).map((_, index) => (
              <CarouselItem key={index} className="md:basis-1/2 lg:basis-1/3">
                <div className="p-1">
                  <Card>
                    <CardContent className="flex aspect-square items-center justify-center p-6">
                      <span className="text-3xl font-semibold">{index + 1}</span>
                    </CardContent>
                  </Card>
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
          <CarouselPrevious />
          <CarouselNext />
        </Carousel>
      )
    }
    
    
    
    Copy// 33% of the carousel width.
    <Carousel>
      <CarouselContent>
        <CarouselItem className="basis-1/3">...</CarouselItem>
        <CarouselItem className="basis-1/3">...</CarouselItem>
        <CarouselItem className="basis-1/3">...</CarouselItem>
      </CarouselContent>
    </Carousel>
    
    
    Copy// 50% on small screens and 33% on larger screens.
    <Carousel>
      <CarouselContent>
        <CarouselItem className="md:basis-1/2 lg:basis-1/3">...</CarouselItem>
        <CarouselItem className="md:basis-1/2 lg:basis-1/3">...</CarouselItem>
        <CarouselItem className="md:basis-1/2 lg:basis-1/3">...</CarouselItem>
      </CarouselContent>
    </Carousel>

### Spacing

To set the spacing between the items, we use a `pl-[VALUE]` utility on the `<CarouselItem />` and a negative `-ml-[VALUE]` on the `<CarouselContent />`.

**Why:** I tried to use the `gap` property or a `grid` layout on the ` <CarouselContent />` but it required a lot of math and mental effort to get the spacing right. I found `pl-[VALUE]` and `-ml-[VALUE]` utilities much easier to use.

You can always adjust this in your own project if you need to.

1

2

3

4

5

Previous slideNext slide

Copy
    
    
    import * as React from "react"
    
    import { Card, CardContent } from "@/components/ui/card"
    import {
      Carousel,
      CarouselContent,
      CarouselItem,
      CarouselNext,
      CarouselPrevious,
    } from "@/components/ui/carousel"
    
    export function CarouselSpacing() {
      return (
        <Carousel className="w-full max-w-sm">
          <CarouselContent className="-ml-1">
            {Array.from({ length: 5 }).map((_, index) => (
              <CarouselItem key={index} className="pl-1 md:basis-1/2 lg:basis-1/3">
                <div className="p-1">
                  <Card>
                    <CardContent className="flex aspect-square items-center justify-center p-6">
                      <span className="text-2xl font-semibold">{index + 1}</span>
                    </CardContent>
                  </Card>
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
          <CarouselPrevious />
          <CarouselNext />
        </Carousel>
      )
    }
    
    
    
    Copy<Carousel>
      <CarouselContent className="-ml-4">
        <CarouselItem className="pl-4">...</CarouselItem>
        <CarouselItem className="pl-4">...</CarouselItem>
        <CarouselItem className="pl-4">...</CarouselItem>
      </CarouselContent>
    </Carousel>
    
    
    Copy<Carousel>
      <CarouselContent className="-ml-2 md:-ml-4">
        <CarouselItem className="pl-2 md:pl-4">...</CarouselItem>
        <CarouselItem className="pl-2 md:pl-4">...</CarouselItem>
        <CarouselItem className="pl-2 md:pl-4">...</CarouselItem>
      </CarouselContent>
    </Carousel>

### Orientation

Use the `orientation` prop to set the orientation of the carousel.

1

2

3

4

5

Previous slideNext slide

Copy
    
    
    import * as React from "react"
    
    import { Card, CardContent } from "@/components/ui/card"
    import {
      Carousel,
      CarouselContent,
      CarouselItem,
      CarouselNext,
      CarouselPrevious,
    } from "@/components/ui/carousel"
    
    export function CarouselOrientation() {
      return (
        <Carousel
          opts={{
            align: "start",
          }}
          orientation="vertical"
          className="w-full max-w-xs"
        >
          <CarouselContent className="-mt-1 h-[200px]">
            {Array.from({ length: 5 }).map((_, index) => (
              <CarouselItem key={index} className="pt-1 md:basis-1/2">
                <div className="p-1">
                  <Card>
                    <CardContent className="flex items-center justify-center p-6">
                      <span className="text-3xl font-semibold">{index + 1}</span>
                    </CardContent>
                  </Card>
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
          <CarouselPrevious />
          <CarouselNext />
        </Carousel>
      )
    }
    
    
    
    Copy<Carousel orientation="vertical | horizontal">
      <CarouselContent>
        <CarouselItem>...</CarouselItem>
        <CarouselItem>...</CarouselItem>
        <CarouselItem>...</CarouselItem>
      </CarouselContent>
    </Carousel>

## Options

You can pass options to the carousel using the `opts` prop. See the [Embla Carousel docs](https://www.embla-carousel.com/api/options/) for more information.
    
    
    Copy<Carousel
      opts={{
        align: "start",
        loop: true,
      }}
    >
      <CarouselContent>
        <CarouselItem>...</CarouselItem>
        <CarouselItem>...</CarouselItem>
        <CarouselItem>...</CarouselItem>
      </CarouselContent>
    </Carousel>

## API

Use a state and the `setApi` props to get an instance of the carousel API.

1

2

3

4

5

Previous slideNext slide

Slide 0 of 0

Copy
    
    
    "use client"
    
    import * as React from "react"
    
    import { Card, CardContent } from "@/components/ui/card"
    import {
      Carousel,
      CarouselContent,
      CarouselItem,
      CarouselNext,
      CarouselPrevious,
      type CarouselApi,
    } from "@/components/ui/carousel"
    
    export function CarouselDApiDemo() {
      const [api, setApi] = React.useState<CarouselApi>()
      const [current, setCurrent] = React.useState(0)
      const [count, setCount] = React.useState(0)
    
      React.useEffect(() => {
        if (!api) {
          return
        }
    
        setCount(api.scrollSnapList().length)
        setCurrent(api.selectedScrollSnap() + 1)
    
        api.on("select", () => {
          setCurrent(api.selectedScrollSnap() + 1)
        })
      }, [api])
    
      return (
        <div className="mx-auto max-w-xs">
          <Carousel setApi={setApi} className="w-full max-w-xs">
            <CarouselContent>
              {Array.from({ length: 5 }).map((_, index) => (
                <CarouselItem key={index}>
                  <Card>
                    <CardContent className="flex aspect-square items-center justify-center p-6">
                      <span className="text-4xl font-semibold">{index + 1}</span>
                    </CardContent>
                  </Card>
                </CarouselItem>
              ))}
            </CarouselContent>
            <CarouselPrevious />
            <CarouselNext />
          </Carousel>
          <div className="text-muted-foreground py-2 text-center text-sm">
            Slide {current} of {count}
          </div>
        </div>
      )
    }
    
    
    
    Copyimport { type CarouselApi } from "@/components/ui/carousel"
     
    export function Example() {
      const [api, setApi] = React.useState<CarouselApi>()
      const [current, setCurrent] = React.useState(0)
      const [count, setCount] = React.useState(0)
     
      React.useEffect(() => {
        if (!api) {
          return
        }
     
        setCount(api.scrollSnapList().length)
        setCurrent(api.selectedScrollSnap() + 1)
     
        api.on("select", () => {
          setCurrent(api.selectedScrollSnap() + 1)
        })
      }, [api])
     
      return (
        <Carousel setApi={setApi}>
          <CarouselContent>
            <CarouselItem>...</CarouselItem>
            <CarouselItem>...</CarouselItem>
            <CarouselItem>...</CarouselItem>
          </CarouselContent>
        </Carousel>
      )
    }

## Events

You can listen to events using the api instance from `setApi`.
    
    
    Copyimport { type CarouselApi } from "@/components/ui/carousel"
     
    export function Example() {
      const [api, setApi] = React.useState<CarouselApi>()
     
      React.useEffect(() => {
        if (!api) {
          return
        }
     
        api.on("select", () => {
          // Do something on select.
        })
      }, [api])
     
      return (
        <Carousel setApi={setApi}>
          <CarouselContent>
            <CarouselItem>...</CarouselItem>
            <CarouselItem>...</CarouselItem>
            <CarouselItem>...</CarouselItem>
          </CarouselContent>
        </Carousel>
      )
    }

See the [Embla Carousel docs](https://www.embla-carousel.com/api/events/) for more information on using events.

## Plugins

You can use the `plugins` prop to add plugins to the carousel.
    
    
    Copyimport Autoplay from "embla-carousel-autoplay"
     
    export function Example() {
      return (
        <Carousel
          plugins={[
            Autoplay({
              delay: 2000,
            }),
          ]}
        >
          // ...
        </Carousel>
      )
    }

1

2

3

4

5

Previous slideNext slide

Copy
    
    
    "use client"
    
    import * as React from "react"
    import Autoplay from "embla-carousel-autoplay"
    
    import { Card, CardContent } from "@/components/ui/card"
    import {
      Carousel,
      CarouselContent,
      CarouselItem,
      CarouselNext,
      CarouselPrevious,
    } from "@/components/ui/carousel"
    
    export function CarouselPlugin() {
      const plugin = React.useRef(
        Autoplay({ delay: 2000, stopOnInteraction: true })
      )
    
      return (
        <Carousel
          plugins={[plugin.current]}
          className="w-full max-w-xs"
          onMouseEnter={plugin.current.stop}
          onMouseLeave={plugin.current.reset}
        >
          <CarouselContent>
            {Array.from({ length: 5 }).map((_, index) => (
              <CarouselItem key={index}>
                <div className="p-1">
                  <Card>
                    <CardContent className="flex aspect-square items-center justify-center p-6">
                      <span className="text-4xl font-semibold">{index + 1}</span>
                    </CardContent>
                  </Card>
                </div>
              </CarouselItem>
            ))}
          </CarouselContent>
          <CarouselPrevious />
          <CarouselNext />
        </Carousel>
      )
    }
    

See the [Embla Carousel docs](https://www.embla-carousel.com/api/plugins/) for more information on using plugins.

[ Card](/docs/components/card)[Chart ](/docs/components/chart)
