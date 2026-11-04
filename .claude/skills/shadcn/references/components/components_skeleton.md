# Skeleton

Copy Page

[Previous](/docs/components/sidebar)[Next](/docs/components/slider)

Use to show a placeholder while content is loading.

Copy
    
    
    import { Skeleton } from "@/components/ui/skeleton"
    
    export function SkeletonDemo() {
      return (
        <div className="flex items-center space-x-4">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-[250px]" />
            <Skeleton className="h-4 w-[200px]" />
          </div>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add skeleton

Copy

## Usage
    
    
    Copyimport { Skeleton } from "@/components/ui/skeleton"
    
    
    Copy<Skeleton className="h-[20px] w-[100px] rounded-full" />

## Examples

### Card

Copy
    
    
    import { Skeleton } from "@/components/ui/skeleton"
    
    export function SkeletonCard() {
      return (
        <div className="flex flex-col space-y-3">
          <Skeleton className="h-[125px] w-[250px] rounded-xl" />
          <div className="space-y-2">
            <Skeleton className="h-4 w-[250px]" />
            <Skeleton className="h-4 w-[200px]" />
          </div>
        </div>
      )
    }
    

[ Sidebar](/docs/components/sidebar)[Slider ](/docs/components/slider)
