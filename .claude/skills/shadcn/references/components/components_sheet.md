# Sheet

Copy Page

[Previous](/docs/components/separator)[Next](/docs/components/sidebar)

Extends the Dialog component to display content that complements the main content of the screen.

[Docs ](https://www.radix-ui.com/docs/primitives/components/dialog)[API Reference ](https://www.radix-ui.com/docs/primitives/components/dialog#api-reference)

Open

Copy
    
    
    import { Button } from "@/components/ui/button"
    import { Input } from "@/components/ui/input"
    import { Label } from "@/components/ui/label"
    import {
      Sheet,
      SheetClose,
      SheetContent,
      SheetDescription,
      SheetFooter,
      SheetHeader,
      SheetTitle,
      SheetTrigger,
    } from "@/components/ui/sheet"
    
    export function SheetDemo() {
      return (
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="outline">Open</Button>
          </SheetTrigger>
          <SheetContent>
            <SheetHeader>
              <SheetTitle>Edit profile</SheetTitle>
              <SheetDescription>
                Make changes to your profile here. Click save when you&apos;re done.
              </SheetDescription>
            </SheetHeader>
            <div className="grid flex-1 auto-rows-min gap-6 px-4">
              <div className="grid gap-3">
                <Label htmlFor="sheet-demo-name">Name</Label>
                <Input id="sheet-demo-name" defaultValue="Pedro Duarte" />
              </div>
              <div className="grid gap-3">
                <Label htmlFor="sheet-demo-username">Username</Label>
                <Input id="sheet-demo-username" defaultValue="@peduarte" />
              </div>
            </div>
            <SheetFooter>
              <Button type="submit">Save changes</Button>
              <SheetClose asChild>
                <Button variant="outline">Close</Button>
              </SheetClose>
            </SheetFooter>
          </SheetContent>
        </Sheet>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add sheet

Copy

### Usage
    
    
    Copyimport {
      Sheet,
      SheetContent,
      SheetDescription,
      SheetHeader,
      SheetTitle,
      SheetTrigger,
    } from "@/components/ui/sheet"
    
    
    Copy<Sheet>
      <SheetTrigger>Open</SheetTrigger>
      <SheetContent>
        <SheetHeader>
          <SheetTitle>Are you absolutely sure?</SheetTitle>
          <SheetDescription>
            This action cannot be undone. This will permanently delete your account
            and remove your data from our servers.
          </SheetDescription>
        </SheetHeader>
      </SheetContent>
    </Sheet>

## Examples

### Side

Use the `side` property to `<SheetContent />` to indicate the edge of the screen where the component will appear. The values can be `top`, `right`, `bottom` or `left`.

### Size

You can adjust the size of the sheet using CSS classes:
    
    
    Copy<Sheet>
      <SheetTrigger>Open</SheetTrigger>
      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle>Are you absolutely sure?</SheetTitle>
          <SheetDescription>
            This action cannot be undone. This will permanently delete your account
            and remove your data from our servers.
          </SheetDescription>
        </SheetHeader>
      </SheetContent>
    </Sheet>

[ Separator](/docs/components/separator)[Sidebar ](/docs/components/sidebar)
