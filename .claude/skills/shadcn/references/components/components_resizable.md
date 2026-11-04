# Resizable

Copy Page

[Previous](/docs/components/radio-group)[Next](/docs/components/scroll-area)

Accessible resizable panel groups and layouts with keyboard support.

[Docs ](https://github.com/bvaughn/react-resizable-panels)[API Reference ](https://github.com/bvaughn/react-resizable-panels/tree/main/packages/react-resizable-panels)

One

Two

Three

Copy
    
    
    import {
      ResizableHandle,
      ResizablePanel,
      ResizablePanelGroup,
    } from "@/components/ui/resizable"
    
    export function ResizableDemo() {
      return (
        <ResizablePanelGroup
          direction="horizontal"
          className="max-w-md rounded-lg border md:min-w-[450px]"
        >
          <ResizablePanel defaultSize={50}>
            <div className="flex h-[200px] items-center justify-center p-6">
              <span className="font-semibold">One</span>
            </div>
          </ResizablePanel>
          <ResizableHandle />
          <ResizablePanel defaultSize={50}>
            <ResizablePanelGroup direction="vertical">
              <ResizablePanel defaultSize={25}>
                <div className="flex h-full items-center justify-center p-6">
                  <span className="font-semibold">Two</span>
                </div>
              </ResizablePanel>
              <ResizableHandle />
              <ResizablePanel defaultSize={75}>
                <div className="flex h-full items-center justify-center p-6">
                  <span className="font-semibold">Three</span>
                </div>
              </ResizablePanel>
            </ResizablePanelGroup>
          </ResizablePanel>
        </ResizablePanelGroup>
      )
    }
    

## About

The `Resizable` component is built on top of [react-resizable-panels](https://github.com/bvaughn/react-resizable-panels) by [bvaughn](https://github.com/bvaughn).

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add resizable

Copy

## Usage
    
    
    Copyimport {
      ResizableHandle,
      ResizablePanel,
      ResizablePanelGroup,
    } from "@/components/ui/resizable"
    
    
    Copy<ResizablePanelGroup direction="horizontal">
      <ResizablePanel>One</ResizablePanel>
      <ResizableHandle />
      <ResizablePanel>Two</ResizablePanel>
    </ResizablePanelGroup>

## Examples

### Vertical

Use the `direction` prop to set the direction of the resizable panels.

Header

Content

Copy
    
    
    import {
      ResizableHandle,
      ResizablePanel,
      ResizablePanelGroup,
    } from "@/components/ui/resizable"
    
    export function ResizableDemo() {
      return (
        <ResizablePanelGroup
          direction="vertical"
          className="min-h-[200px] max-w-md rounded-lg border md:min-w-[450px]"
        >
          <ResizablePanel defaultSize={25}>
            <div className="flex h-full items-center justify-center p-6">
              <span className="font-semibold">Header</span>
            </div>
          </ResizablePanel>
          <ResizableHandle />
          <ResizablePanel defaultSize={75}>
            <div className="flex h-full items-center justify-center p-6">
              <span className="font-semibold">Content</span>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      )
    }
    
    
    
    Copyimport {
      ResizableHandle,
      ResizablePanel,
      ResizablePanelGroup,
    } from "@/components/ui/resizable"
     
    export default function Example() {
      return (
        <ResizablePanelGroup direction="vertical">
          <ResizablePanel>One</ResizablePanel>
          <ResizableHandle />
          <ResizablePanel>Two</ResizablePanel>
        </ResizablePanelGroup>
      )
    }

### Handle

You can set or hide the handle by using the `withHandle` prop on the `ResizableHandle` component.

Sidebar

Content

Copy
    
    
    import {
      ResizableHandle,
      ResizablePanel,
      ResizablePanelGroup,
    } from "@/components/ui/resizable"
    
    export function ResizableHandleDemo() {
      return (
        <ResizablePanelGroup
          direction="horizontal"
          className="min-h-[200px] max-w-md rounded-lg border md:min-w-[450px]"
        >
          <ResizablePanel defaultSize={25}>
            <div className="flex h-full items-center justify-center p-6">
              <span className="font-semibold">Sidebar</span>
            </div>
          </ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel defaultSize={75}>
            <div className="flex h-full items-center justify-center p-6">
              <span className="font-semibold">Content</span>
            </div>
          </ResizablePanel>
        </ResizablePanelGroup>
      )
    }
    
    
    
    Copyimport {
      ResizableHandle,
      ResizablePanel,
      ResizablePanelGroup,
    } from "@/components/ui/resizable"
     
    export default function Example() {
      return (
        <ResizablePanelGroup direction="horizontal">
          <ResizablePanel>One</ResizablePanel>
          <ResizableHandle withHandle />
          <ResizablePanel>Two</ResizablePanel>
        </ResizablePanelGroup>
      )
    }

[ Radio Group](/docs/components/radio-group)[Scroll Area ](/docs/components/scroll-area)
