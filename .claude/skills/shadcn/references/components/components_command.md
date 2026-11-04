# Command

Copy Page

[Previous](/docs/components/combobox)[Next](/docs/components/context-menu)

Fast, composable, unstyled command menu for React.

[Docs ](https://cmdk.paco.me)

No results found.

Suggestions

Calendar

Search Emoji

Calculator

Settings

Profile⌘P

Billing⌘B

Settings⌘S

Copy
    
    
    import {
      Calculator,
      Calendar,
      CreditCard,
      Settings,
      Smile,
      User,
    } from "lucide-react"
    
    import {
      Command,
      CommandEmpty,
      CommandGroup,
      CommandInput,
      CommandItem,
      CommandList,
      CommandSeparator,
      CommandShortcut,
    } from "@/components/ui/command"
    
    export function CommandDemo() {
      return (
        <Command className="rounded-lg border shadow-md md:min-w-[450px]">
          <CommandInput placeholder="Type a command or search..." />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            <CommandGroup heading="Suggestions">
              <CommandItem>
                <Calendar />
                <span>Calendar</span>
              </CommandItem>
              <CommandItem>
                <Smile />
                <span>Search Emoji</span>
              </CommandItem>
              <CommandItem disabled>
                <Calculator />
                <span>Calculator</span>
              </CommandItem>
            </CommandGroup>
            <CommandSeparator />
            <CommandGroup heading="Settings">
              <CommandItem>
                <User />
                <span>Profile</span>
                <CommandShortcut>⌘P</CommandShortcut>
              </CommandItem>
              <CommandItem>
                <CreditCard />
                <span>Billing</span>
                <CommandShortcut>⌘B</CommandShortcut>
              </CommandItem>
              <CommandItem>
                <Settings />
                <span>Settings</span>
                <CommandShortcut>⌘S</CommandShortcut>
              </CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      )
    }
    

## About

The `<Command />` component uses the [`cmdk`](https://cmdk.paco.me) component by [pacocoursey](https://twitter.com/pacocoursey).

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add command

Copy

## Usage
    
    
    Copyimport {
      Command,
      CommandDialog,
      CommandEmpty,
      CommandGroup,
      CommandInput,
      CommandItem,
      CommandList,
      CommandSeparator,
      CommandShortcut,
    } from "@/components/ui/command"
    
    
    Copy<Command>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        <CommandGroup heading="Suggestions">
          <CommandItem>Calendar</CommandItem>
          <CommandItem>Search Emoji</CommandItem>
          <CommandItem>Calculator</CommandItem>
        </CommandGroup>
        <CommandSeparator />
        <CommandGroup heading="Settings">
          <CommandItem>Profile</CommandItem>
          <CommandItem>Billing</CommandItem>
          <CommandItem>Settings</CommandItem>
        </CommandGroup>
      </CommandList>
    </Command>

## Examples

### Dialog

Press `⌘J`

## Command Palette

Search for a command to run...

Copy
    
    
    "use client"
    
    import * as React from "react"
    import {
      Calculator,
      Calendar,
      CreditCard,
      Settings,
      Smile,
      User,
    } from "lucide-react"
    
    import {
      CommandDialog,
      CommandEmpty,
      CommandGroup,
      CommandInput,
      CommandItem,
      CommandList,
      CommandSeparator,
      CommandShortcut,
    } from "@/components/ui/command"
    
    export function CommandDialogDemo() {
      const [open, setOpen] = React.useState(false)
    
      React.useEffect(() => {
        const down = (e: KeyboardEvent) => {
          if (e.key === "j" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault()
            setOpen((open) => !open)
          }
        }
    
        document.addEventListener("keydown", down)
        return () => document.removeEventListener("keydown", down)
      }, [])
    
      return (
        <>
          <p className="text-muted-foreground text-sm">
            Press{" "}
            <kbd className="bg-muted text-muted-foreground pointer-events-none inline-flex h-5 items-center gap-1 rounded border px-1.5 font-mono text-[10px] font-medium opacity-100 select-none">
              <span className="text-xs">⌘</span>J
            </kbd>
          </p>
          <CommandDialog open={open} onOpenChange={setOpen}>
            <CommandInput placeholder="Type a command or search..." />
            <CommandList>
              <CommandEmpty>No results found.</CommandEmpty>
              <CommandGroup heading="Suggestions">
                <CommandItem>
                  <Calendar />
                  <span>Calendar</span>
                </CommandItem>
                <CommandItem>
                  <Smile />
                  <span>Search Emoji</span>
                </CommandItem>
                <CommandItem>
                  <Calculator />
                  <span>Calculator</span>
                </CommandItem>
              </CommandGroup>
              <CommandSeparator />
              <CommandGroup heading="Settings">
                <CommandItem>
                  <User />
                  <span>Profile</span>
                  <CommandShortcut>⌘P</CommandShortcut>
                </CommandItem>
                <CommandItem>
                  <CreditCard />
                  <span>Billing</span>
                  <CommandShortcut>⌘B</CommandShortcut>
                </CommandItem>
                <CommandItem>
                  <Settings />
                  <span>Settings</span>
                  <CommandShortcut>⌘S</CommandShortcut>
                </CommandItem>
              </CommandGroup>
            </CommandList>
          </CommandDialog>
        </>
      )
    }
    

To show the command menu in a dialog, use the `<CommandDialog />` component.

components/example-command-menu.tsx
    
    
    Copyexport function CommandMenu() {
      const [open, setOpen] = React.useState(false)
     
      React.useEffect(() => {
        const down = (e: KeyboardEvent) => {
          if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
            e.preventDefault()
            setOpen((open) => !open)
          }
        }
        document.addEventListener("keydown", down)
        return () => document.removeEventListener("keydown", down)
      }, [])
     
      return (
        <CommandDialog open={open} onOpenChange={setOpen}>
          <CommandInput placeholder="Type a command or search..." />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            <CommandGroup heading="Suggestions">
              <CommandItem>Calendar</CommandItem>
              <CommandItem>Search Emoji</CommandItem>
              <CommandItem>Calculator</CommandItem>
            </CommandGroup>
          </CommandList>
        </CommandDialog>
      )
    }

### Combobox

You can use the `<Command />` component as a combobox. See the [Combobox](/docs/components/combobox) page for more information.

[ Combobox](/docs/components/combobox)[Context Menu ](/docs/components/context-menu)
