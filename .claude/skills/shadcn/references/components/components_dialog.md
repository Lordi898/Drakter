# Dialog

Copy Page

[Previous](/docs/components/date-picker)[Next](/docs/components/drawer)

A window overlaid on either the primary window or another dialog window, rendering the content underneath inert.

[Docs ](https://www.radix-ui.com/docs/primitives/components/dialog)[API Reference ](https://www.radix-ui.com/docs/primitives/components/dialog#api-reference)

Open Dialog

Copy
    
    
    import { Button } from "@/components/ui/button"
    import {
      Dialog,
      DialogClose,
      DialogContent,
      DialogDescription,
      DialogFooter,
      DialogHeader,
      DialogTitle,
      DialogTrigger,
    } from "@/components/ui/dialog"
    import { Input } from "@/components/ui/input"
    import { Label } from "@/components/ui/label"
    
    export function DialogDemo() {
      return (
        <Dialog>
          <form>
            <DialogTrigger asChild>
              <Button variant="outline">Open Dialog</Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[425px]">
              <DialogHeader>
                <DialogTitle>Edit profile</DialogTitle>
                <DialogDescription>
                  Make changes to your profile here. Click save when you&apos;re
                  done.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-4">
                <div className="grid gap-3">
                  <Label htmlFor="name-1">Name</Label>
                  <Input id="name-1" name="name" defaultValue="Pedro Duarte" />
                </div>
                <div className="grid gap-3">
                  <Label htmlFor="username-1">Username</Label>
                  <Input id="username-1" name="username" defaultValue="@peduarte" />
                </div>
              </div>
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Cancel</Button>
                </DialogClose>
                <Button type="submit">Save changes</Button>
              </DialogFooter>
            </DialogContent>
          </form>
        </Dialog>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add dialog

Copy

## Usage
    
    
    Copyimport {
      Dialog,
      DialogContent,
      DialogDescription,
      DialogHeader,
      DialogTitle,
      DialogTrigger,
    } from "@/components/ui/dialog"
    
    
    Copy<Dialog>
      <DialogTrigger>Open</DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Are you absolutely sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. This will permanently delete your account
            and remove your data from our servers.
          </DialogDescription>
        </DialogHeader>
      </DialogContent>
    </Dialog>

## Examples

### Custom close button

Share

Copy
    
    
    import { Button } from "@/components/ui/button"
    import {
      Dialog,
      DialogClose,
      DialogContent,
      DialogDescription,
      DialogFooter,
      DialogHeader,
      DialogTitle,
      DialogTrigger,
    } from "@/components/ui/dialog"
    import { Input } from "@/components/ui/input"
    import { Label } from "@/components/ui/label"
    
    export function DialogCloseButton() {
      return (
        <Dialog>
          <DialogTrigger asChild>
            <Button variant="outline">Share</Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Share link</DialogTitle>
              <DialogDescription>
                Anyone who has this link will be able to view this.
              </DialogDescription>
            </DialogHeader>
            <div className="flex items-center gap-2">
              <div className="grid flex-1 gap-2">
                <Label htmlFor="link" className="sr-only">
                  Link
                </Label>
                <Input
                  id="link"
                  defaultValue="https://ui.shadcn.com/docs/installation"
                  readOnly
                />
              </div>
            </div>
            <DialogFooter className="sm:justify-start">
              <DialogClose asChild>
                <Button type="button" variant="secondary">
                  Close
                </Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )
    }
    

## Notes

To use the `Dialog` component from within a `Context Menu` or `Dropdown Menu`, you must encase the `Context Menu` or `Dropdown Menu` component in the `Dialog` component.

components/example-dialog-context-menu.tsx
    
    
    Copy<Dialog>
      <ContextMenu>
        <ContextMenuTrigger>Right click</ContextMenuTrigger>
        <ContextMenuContent>
          <ContextMenuItem>Open</ContextMenuItem>
          <ContextMenuItem>Download</ContextMenuItem>
          <DialogTrigger asChild>
            <ContextMenuItem>
              <span>Delete</span>
            </ContextMenuItem>
          </DialogTrigger>
        </ContextMenuContent>
      </ContextMenu>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Are you absolutely sure?</DialogTitle>
          <DialogDescription>
            This action cannot be undone. Are you sure you want to permanently
            delete this file from our servers?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button type="submit">Confirm</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

[ Date Picker](/docs/components/date-picker)[Drawer ](/docs/components/drawer)
