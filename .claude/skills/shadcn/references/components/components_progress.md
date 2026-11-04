# Progress

Copy Page

[Previous](/docs/components/popover)[Next](/docs/components/radio-group)

Displays an indicator showing the completion progress of a task, typically displayed as a progress bar.

[Docs ](https://www.radix-ui.com/docs/primitives/components/progress)[API Reference ](https://www.radix-ui.com/docs/primitives/components/progress#api-reference)

Copy
    
    
    "use client"
    
    import * as React from "react"
    
    import { Progress } from "@/components/ui/progress"
    
    export function ProgressDemo() {
      const [progress, setProgress] = React.useState(13)
    
      React.useEffect(() => {
        const timer = setTimeout(() => setProgress(66), 500)
        return () => clearTimeout(timer)
      }, [])
    
      return <Progress value={progress} className="w-[60%]" />
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add progress

Copy

## Usage
    
    
    Copyimport { Progress } from "@/components/ui/progress"
    
    
    Copy<Progress value={33} />

[ Popover](/docs/components/popover)[Radio Group ](/docs/components/radio-group)
