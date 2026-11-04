# Badge

Copy Page

[Previous](/docs/components/avatar)[Next](/docs/components/breadcrumb)

Displays a badge or a component that looks like a badge.

BadgeSecondaryDestructiveOutline

Verified89920+

Copy
    
    
    import { AlertCircleIcon, BadgeCheckIcon, CheckIcon } from "lucide-react"
    
    import { Badge } from "@/components/ui/badge"
    
    export function BadgeDemo() {
      return (
        <div className="flex flex-col items-center gap-2">
          <div className="flex w-full flex-wrap gap-2">
            <Badge>Badge</Badge>
            <Badge variant="secondary">Secondary</Badge>
            <Badge variant="destructive">Destructive</Badge>
            <Badge variant="outline">Outline</Badge>
          </div>
          <div className="flex w-full flex-wrap gap-2">
            <Badge
              variant="secondary"
              className="bg-blue-500 text-white dark:bg-blue-600"
            >
              <BadgeCheckIcon />
              Verified
            </Badge>
            <Badge className="h-5 min-w-5 rounded-full px-1 font-mono tabular-nums">
              8
            </Badge>
            <Badge
              className="h-5 min-w-5 rounded-full px-1 font-mono tabular-nums"
              variant="destructive"
            >
              99
            </Badge>
            <Badge
              className="h-5 min-w-5 rounded-full px-1 font-mono tabular-nums"
              variant="outline"
            >
              20+
            </Badge>
          </div>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add badge

Copy

## Usage
    
    
    Copyimport { Badge } from "@/components/ui/badge"
    
    
    Copy<Badge variant="default | outline | secondary | destructive">Badge</Badge>

### Link

You can use the `asChild` prop to make another component look like a badge. Here's an example of a link that looks like a badge.
    
    
    Copyimport Link from "next/link"
     
    import { Badge } from "@/components/ui/badge"
     
    export function LinkAsBadge() {
      return (
        <Badge asChild>
          <Link href="/">Badge</Link>
        </Badge>
      )
    }

[ Avatar](/docs/components/avatar)[Breadcrumb ](/docs/components/breadcrumb)
