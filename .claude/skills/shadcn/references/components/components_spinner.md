# Spinner

Copy Page

[Previous](/docs/components/sonner)[Next](/docs/components/switch)

An indicator that can be used to show a loading state.

Processing payment...

$100.00

Copy
    
    
    import {
      Item,
      ItemContent,
      ItemMedia,
      ItemTitle,
    } from "@/components/ui/item"
    import { Spinner } from "@/components/ui/spinner"
    
    export function SpinnerDemo() {
      return (
        <div className="flex w-full max-w-xs flex-col gap-4 [--radius:1rem]">
          <Item variant="muted">
            <ItemMedia>
              <Spinner />
            </ItemMedia>
            <ItemContent>
              <ItemTitle className="line-clamp-1">Processing payment...</ItemTitle>
            </ItemContent>
            <ItemContent className="flex-none justify-end">
              <span className="text-sm tabular-nums">$100.00</span>
            </ItemContent>
          </Item>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add spinner

Copy

## Usage
    
    
    Copyimport { Spinner } from "@/components/ui/spinner"
    
    
    Copy<Spinner />

## Customization

You can replace the default spinner icon with any other icon by editing the `Spinner` component.

Copy
    
    
    import { LoaderIcon } from "lucide-react"
    
    import { cn } from "@/lib/utils"
    
    function Spinner({ className, ...props }: React.ComponentProps<"svg">) {
      return (
        <LoaderIcon
          role="status"
          aria-label="Loading"
          className={cn("size-4 animate-spin", className)}
          {...props}
        />
      )
    }
    
    export function SpinnerCustom() {
      return (
        <div className="flex items-center gap-4">
          <Spinner />
        </div>
      )
    }
    

components/ui/spinner.tsx
    
    
    Copyimport { LoaderIcon } from "lucide-react"
     
    import { cn } from "@/lib/utils"
     
    function Spinner({ className, ...props }: React.ComponentProps<"svg">) {
      return (
        <LoaderIcon
          role="status"
          aria-label="Loading"
          className={cn("size-4 animate-spin", className)}
          {...props}
        />
      )
    }
     
    export { Spinner }

## Examples

### Size

Use the `size-*` utility class to change the size of the spinner.

Copy
    
    
    import { Spinner } from "@/components/ui/spinner"
    
    export function SpinnerSize() {
      return (
        <div className="flex items-center gap-6">
          <Spinner className="size-3" />
          <Spinner className="size-4" />
          <Spinner className="size-6" />
          <Spinner className="size-8" />
        </div>
      )
    }
    

### Color

Use the `text-` utility class to change the color of the spinner.

Copy
    
    
    import { Spinner } from "@/components/ui/spinner"
    
    export function SpinnerColor() {
      return (
        <div className="flex items-center gap-6">
          <Spinner className="size-6 text-red-500" />
          <Spinner className="size-6 text-green-500" />
          <Spinner className="size-6 text-blue-500" />
          <Spinner className="size-6 text-yellow-500" />
          <Spinner className="size-6 text-purple-500" />
        </div>
      )
    }
    

### Button

Add a spinner to a button to indicate a loading state. The `<Button />` will handle the spacing between the spinner and the text.

Loading...Please waitProcessing

Copy
    
    
    import { Button } from "@/components/ui/button"
    import { Spinner } from "@/components/ui/spinner"
    
    export function SpinnerButton() {
      return (
        <div className="flex flex-col items-center gap-4">
          <Button disabled size="sm">
            <Spinner />
            Loading...
          </Button>
          <Button variant="outline" disabled size="sm">
            <Spinner />
            Please wait
          </Button>
          <Button variant="secondary" disabled size="sm">
            <Spinner />
            Processing
          </Button>
        </div>
      )
    }
    

### Badge

You can also use a spinner inside a badge.

SyncingUpdatingProcessing

Copy
    
    
    import { Badge } from "@/components/ui/badge"
    import { Spinner } from "@/components/ui/spinner"
    
    export function SpinnerBadge() {
      return (
        <div className="flex items-center gap-4 [--radius:1.2rem]">
          <Badge>
            <Spinner />
            Syncing
          </Badge>
          <Badge variant="secondary">
            <Spinner />
            Updating
          </Badge>
          <Badge variant="outline">
            <Spinner />
            Processing
          </Badge>
        </div>
      )
    }
    

### Input Group

Input Group can have spinners inside `<InputGroupAddon>`.

Validating...Send

Copy
    
    
    import { ArrowUpIcon } from "lucide-react"
    
    import {
      InputGroup,
      InputGroupAddon,
      InputGroupButton,
      InputGroupInput,
      InputGroupTextarea,
    } from "@/components/ui/input-group"
    import { Spinner } from "@/components/ui/spinner"
    
    export function SpinnerInputGroup() {
      return (
        <div className="flex w-full max-w-md flex-col gap-4">
          <InputGroup>
            <InputGroupInput placeholder="Send a message..." disabled />
            <InputGroupAddon align="inline-end">
              <Spinner />
            </InputGroupAddon>
          </InputGroup>
          <InputGroup>
            <InputGroupTextarea placeholder="Send a message..." disabled />
            <InputGroupAddon align="block-end">
              <Spinner /> Validating...
              <InputGroupButton className="ml-auto" variant="default">
                <ArrowUpIcon />
                <span className="sr-only">Send</span>
              </InputGroupButton>
            </InputGroupAddon>
          </InputGroup>
        </div>
      )
    }
    

### Empty

Processing your request

Please wait while we process your request. Do not refresh the page.

Cancel

Copy
    
    
    import { Button } from "@/components/ui/button"
    import {
      Empty,
      EmptyContent,
      EmptyDescription,
      EmptyHeader,
      EmptyMedia,
      EmptyTitle,
    } from "@/components/ui/empty"
    import { Spinner } from "@/components/ui/spinner"
    
    export function SpinnerEmpty() {
      return (
        <Empty className="w-full">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <Spinner />
            </EmptyMedia>
            <EmptyTitle>Processing your request</EmptyTitle>
            <EmptyDescription>
              Please wait while we process your request. Do not refresh the page.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button variant="outline" size="sm">
              Cancel
            </Button>
          </EmptyContent>
        </Empty>
      )
    }
    

### Item

Use the spinner inside `<ItemMedia>` to indicate a loading state.

Downloading...

129 MB / 1000 MB

Cancel

Copy
    
    
    import { Button } from "@/components/ui/button"
    import {
      Item,
      ItemActions,
      ItemContent,
      ItemDescription,
      ItemFooter,
      ItemMedia,
      ItemTitle,
    } from "@/components/ui/item"
    import { Progress } from "@/components/ui/progress"
    import { Spinner } from "@/components/ui/spinner"
    
    export function SpinnerItem() {
      return (
        <div className="flex w-full max-w-md flex-col gap-4 [--radius:1rem]">
          <Item variant="outline">
            <ItemMedia variant="icon">
              <Spinner />
            </ItemMedia>
            <ItemContent>
              <ItemTitle>Downloading...</ItemTitle>
              <ItemDescription>129 MB / 1000 MB</ItemDescription>
            </ItemContent>
            <ItemActions className="hidden sm:flex">
              <Button variant="outline" size="sm">
                Cancel
              </Button>
            </ItemActions>
            <ItemFooter>
              <Progress value={75} />
            </ItemFooter>
          </Item>
        </div>
      )
    }
    

## API Reference

### Spinner

Use the `Spinner` component to display a spinner.

Prop| Type| Default  
---|---|---  
`className`| `string`| ``  
      
    
    Copy<Spinner />

[ Sonner](/docs/components/sonner)[Switch ](/docs/components/switch)
