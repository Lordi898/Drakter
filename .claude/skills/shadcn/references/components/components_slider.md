# Slider

Copy Page

[Previous](/docs/components/skeleton)[Next](/docs/components/sonner)

An input where the user selects a value from within a given range.

[Docs ](https://www.radix-ui.com/docs/primitives/components/slider)[API Reference ](https://www.radix-ui.com/docs/primitives/components/slider#api-reference)

Copy
    
    
    import { cn } from "@/lib/utils"
    import { Slider } from "@/components/ui/slider"
    
    type SliderProps = React.ComponentProps<typeof Slider>
    
    export function SliderDemo({ className, ...props }: SliderProps) {
      return (
        <Slider
          defaultValue={[50]}
          max={100}
          step={1}
          className={cn("w-[60%]", className)}
          {...props}
        />
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add slider

Copy

## Usage
    
    
    Copyimport { Slider } from "@/components/ui/slider"
    
    
    Copy<Slider defaultValue={[33]} max={100} step={1} />

[ Skeleton](/docs/components/skeleton)[Sonner ](/docs/components/sonner)
