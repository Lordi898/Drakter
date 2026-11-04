# Button

Copy Page

[Previous](/docs/components/button-group)[Next](/docs/components/calendar)

Displays a button or a component that looks like a button.

**Updated:** We have updated the button component to add new sizes: `icon-sm` and `icon-lg`. See the [changelog](/docs/components/button#changelog) for more details. Follow the instructions to update your project.

Button

Copy
    
    
    import { ArrowUpIcon } from "lucide-react"
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonDemo() {
      return (
        <div className="flex flex-wrap items-center gap-2 md:flex-row">
          <Button variant="outline">Button</Button>
          <Button variant="outline" size="icon" aria-label="Submit">
            <ArrowUpIcon />
          </Button>
        </div>
      )
    }
    
    
    
    Copy<Button variant="outline">Button</Button>
    <Button variant="outline" size="icon" aria-label="Submit">
      <ArrowUpIcon />
    </Button>

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add button

Copy

## Usage
    
    
    Copyimport { Button } from "@/components/ui/button"
    
    
    Copy<Button variant="outline">Button</Button>

## Cursor

Tailwind v4 [switched](https://tailwindcss.com/docs/upgrade-guide#buttons-use-the-default-cursor) from `cursor: pointer` to `cursor: default` for the button component.

If you want to keep the `cursor: pointer` behavior, add the following code to your CSS file:

globals.css
    
    
    Copy@layer base {
      button:not(:disabled),
      [role="button"]:not(:disabled) {
        cursor: pointer;
      }
    }

## Examples

### Size

Small

Default

Large

Copy
    
    
    import { ArrowUpRightIcon } from "lucide-react"
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonSize() {
      return (
        <div className="flex flex-col items-start gap-8 sm:flex-row">
          <div className="flex items-start gap-2">
            <Button size="sm" variant="outline">
              Small
            </Button>
            <Button size="icon-sm" aria-label="Submit" variant="outline">
              <ArrowUpRightIcon />
            </Button>
          </div>
          <div className="flex items-start gap-2">
            <Button variant="outline">Default</Button>
            <Button size="icon" aria-label="Submit" variant="outline">
              <ArrowUpRightIcon />
            </Button>
          </div>
          <div className="flex items-start gap-2">
            <Button variant="outline" size="lg">
              Large
            </Button>
            <Button size="icon-lg" aria-label="Submit" variant="outline">
              <ArrowUpRightIcon />
            </Button>
          </div>
        </div>
      )
    }
    
    
    
    Copy// Small
    <Button size="sm" variant="outline">Small</Button>
    <Button size="icon-sm" aria-label="Submit" variant="outline">
      <ArrowUpRightIcon />
    </Button>
     
    // Medium
    <Button variant="outline">Default</Button>
    <Button size="icon" aria-label="Submit" variant="outline">
      <ArrowUpRightIcon />
    </Button>
     
    // Large
    <Button size="lg" variant="outline">Large</Button>
    <Button size="icon-lg" aria-label="Submit" variant="outline">
      <ArrowUpRightIcon />
    </Button>

### Default

Button

Copy
    
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonDefault() {
      return <Button>Button</Button>
    }
    
    
    
    Copy<Button>Button</Button>

### Outline

Outline

Copy
    
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonOutline() {
      return <Button variant="outline">Outline</Button>
    }
    
    
    
    Copy<Button variant="outline">Outline</Button>

### Secondary

Secondary

Copy
    
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonSecondary() {
      return <Button variant="secondary">Secondary</Button>
    }
    
    
    
    Copy<Button variant="secondary">Secondary</Button>

### Ghost

Ghost

Copy
    
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonGhost() {
      return <Button variant="ghost">Ghost</Button>
    }
    
    
    
    Copy<Button variant="ghost">Ghost</Button>

### Destructive

Destructive

Copy
    
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonDestructive() {
      return <Button variant="destructive">Destructive</Button>
    }
    
    
    
    Copy<Button variant="destructive">Destructive</Button>

### Link

Link

Copy
    
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonLink() {
      return <Button variant="link">Link</Button>
    }
    
    
    
    Copy<Button variant="link">Link</Button>

### Icon

Copy
    
    
    import { CircleFadingArrowUpIcon } from "lucide-react"
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonIcon() {
      return (
        <Button variant="outline" size="icon">
          <CircleFadingArrowUpIcon />
        </Button>
      )
    }
    
    
    
    Copy<Button variant="outline" size="icon" aria-label="Submit">
      <CircleFadingArrowUpIcon />
    </Button>

### With Icon

The spacing between the icon and the text is automatically adjusted based on the size of the button. You do not need any margin on the icon.

New Branch

Copy
    
    
    import { IconGitBranch } from "@tabler/icons-react"
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonWithIcon() {
      return (
        <Button variant="outline" size="sm">
          <IconGitBranch /> New Branch
        </Button>
      )
    }
    
    
    
    Copy<Button variant="outline" size="sm">
      <IconGitBranch /> New Branch
    </Button>

### Rounded

Use the `rounded-full` class to make the button rounded.

Copy
    
    
    import { ArrowUpIcon } from "lucide-react"
    
    import { Button } from "@/components/ui/button"
    
    export function ButtonRounded() {
      return (
        <div className="flex flex-col gap-8">
          <Button variant="outline" size="icon" className="rounded-full">
            <ArrowUpIcon />
          </Button>
        </div>
      )
    }
    
    
    
    Copy<Button variant="outline" size="icon" className="rounded-full">
      <ArrowUpRightIcon />
    </Button>

### Spinner

Submit

Copy
    
    
    import { Button } from "@/components/ui/button"
    import { Spinner } from "@/components/ui/spinner"
    
    export function ButtonLoading() {
      return (
        <Button size="sm" variant="outline" disabled>
          <Spinner />
          Submit
        </Button>
      )
    }
    
    
    
    Copy<Button size="sm" variant="outline" disabled>
      <Spinner />
      Submit
    </Button>

### Button Group

To create a button group, use the `ButtonGroup` component. See the [Button Group](/docs/components/button-group) documentation for more details.

ArchiveReport

Snooze

Copy
    
    
    "use client"
    
    import * as React from "react"
    import {
      ArchiveIcon,
      ArrowLeftIcon,
      CalendarPlusIcon,
      ClockIcon,
      ListFilterIcon,
      MailCheckIcon,
      MoreHorizontalIcon,
      TagIcon,
      Trash2Icon,
    } from "lucide-react"
    
    import { Button } from "@/components/ui/button"
    import { ButtonGroup } from "@/components/ui/button-group"
    import {
      DropdownMenu,
      DropdownMenuContent,
      DropdownMenuGroup,
      DropdownMenuItem,
      DropdownMenuRadioGroup,
      DropdownMenuRadioItem,
      DropdownMenuSeparator,
      DropdownMenuSub,
      DropdownMenuSubContent,
      DropdownMenuSubTrigger,
      DropdownMenuTrigger,
    } from "@/components/ui/dropdown-menu"
    
    export function ButtonGroupDemo() {
      const [label, setLabel] = React.useState("personal")
    
      return (
        <ButtonGroup>
          <ButtonGroup className="hidden sm:flex">
            <Button variant="outline" size="icon" aria-label="Go Back">
              <ArrowLeftIcon />
            </Button>
          </ButtonGroup>
          <ButtonGroup>
            <Button variant="outline">Archive</Button>
            <Button variant="outline">Report</Button>
          </ButtonGroup>
          <ButtonGroup>
            <Button variant="outline">Snooze</Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon" aria-label="More Options">
                  <MoreHorizontalIcon />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-52">
                <DropdownMenuGroup>
                  <DropdownMenuItem>
                    <MailCheckIcon />
                    Mark as Read
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <ArchiveIcon />
                    Archive
                  </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem>
                    <ClockIcon />
                    Snooze
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <CalendarPlusIcon />
                    Add to Calendar
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <ListFilterIcon />
                    Add to List
                  </DropdownMenuItem>
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger>
                      <TagIcon />
                      Label As...
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      <DropdownMenuRadioGroup
                        value={label}
                        onValueChange={setLabel}
                      >
                        <DropdownMenuRadioItem value="personal">
                          Personal
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="work">
                          Work
                        </DropdownMenuRadioItem>
                        <DropdownMenuRadioItem value="other">
                          Other
                        </DropdownMenuRadioItem>
                      </DropdownMenuRadioGroup>
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem variant="destructive">
                    <Trash2Icon />
                    Trash
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </ButtonGroup>
        </ButtonGroup>
      )
    }
    
    
    
    Copy<ButtonGroup>
      <ButtonGroup>
        <Button variant="outline" size="icon" aria-label="Go Back">
          <ArrowLeftIcon />
        </Button>
      </ButtonGroup>
      <ButtonGroup>
        <Button variant="outline">Archive</Button>
        <Button variant="outline">Report</Button>
      </ButtonGroup>
      <ButtonGroup>
        <Button variant="outline">Snooze</Button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="icon" aria-label="More Options">
              <MoreHorizontalIcon />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent />
        </DropdownMenu>
      </ButtonGroup>
    </ButtonGroup>

### Link

You can use the `asChild` prop to make another component look like a button. Here's an example of a link that looks like a button.
    
    
    Copyimport Link from "next/link"
     
    import { Button } from "@/components/ui/button"
     
    export function LinkAsButton() {
      return (
        <Button asChild>
          <Link href="/login">Login</Link>
        </Button>
      )
    }

## API Reference

### Button

The `Button` component is a wrapper around the `button` element that adds a variety of styles and functionality.

Prop| Type| Default  
---|---|---  
`variant`| `"default" | "outline" | "ghost" | "destructive" | "secondary" | "link"`| `"default"`  
`size`| `"default" | "sm" | "lg" | "icon" | "icon-sm" | "icon-lg"`| `"default"`  
`asChild`| `boolean`| `false`  
  
## Changelog

### 2025-09-24 New sizes

We have added two new sizes to the button component: `icon-sm` and `icon-lg`. These sizes are used to create icon buttons. To add them, edit `button.tsx` and add the following code under `size` in `buttonVariants`:

components/ui/button.tsx
    
    
    Copyconst buttonVariants = cva("...", {
      variants: {
        size: {
          // ...
          "icon-sm": "size-8",
          "icon-lg": "size-10",
          // ...
        },
      },
    })

[ Button Group](/docs/components/button-group)[Calendar ](/docs/components/calendar)
