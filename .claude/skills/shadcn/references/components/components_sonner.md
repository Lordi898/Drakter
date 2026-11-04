# Sonner

Copy Page

[Previous](/docs/components/slider)[Next](/docs/components/spinner)

An opinionated toast component for React.

[Docs ](https://sonner.emilkowal.ski)

Show Toast

Copy
    
    
    "use client"
    
    import { toast } from "sonner"
    
    import { Button } from "@/components/ui/button"
    
    export function SonnerDemo() {
      return (
        <Button
          variant="outline"
          onClick={() =>
            toast("Event has been created", {
              description: "Sunday, December 03, 2023 at 9:00 AM",
              action: {
                label: "Undo",
                onClick: () => console.log("Undo"),
              },
            })
          }
        >
          Show Toast
        </Button>
      )
    }
    

## About

Sonner is built and maintained by [emilkowalski](https://twitter.com/emilkowalski).

## Installation

CLIManual

### Run the following command:
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add sonner

Copy

### Add the Toaster component

app/layout.tsx
    
    
    Copyimport { Toaster } from "@/components/ui/sonner"
     
    export default function RootLayout({ children }) {
      return (
        <html lang="en">
          <head />
          <body>
            <main>{children}</main>
            <Toaster />
          </body>
        </html>
      )
    }

## Usage
    
    
    Copyimport { toast } from "sonner"
    
    
    Copytoast("Event has been created.")

## Examples

DefaultSuccessInfoWarningErrorPromise

Copy
    
    
    "use client"
    
    import { toast } from "sonner"
    
    import { Button } from "@/components/ui/button"
    
    export function SonnerTypes() {
      return (
        <div className="flex flex-wrap gap-2">
          <Button variant="outline" onClick={() => toast("Event has been created")}>
            Default
          </Button>
          <Button
            variant="outline"
            onClick={() => toast.success("Event has been created")}
          >
            Success
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              toast.info("Be at the area 10 minutes before the event time")
            }
          >
            Info
          </Button>
          <Button
            variant="outline"
            onClick={() =>
              toast.warning("Event start time cannot be earlier than 8am")
            }
          >
            Warning
          </Button>
          <Button
            variant="outline"
            onClick={() => toast.error("Event has not been created")}
          >
            Error
          </Button>
          <Button
            variant="outline"
            onClick={() => {
              toast.promise<{ name: string }>(
                () =>
                  new Promise((resolve) =>
                    setTimeout(() => resolve({ name: "Event" }), 2000)
                  ),
                {
                  loading: "Loading...",
                  success: (data) => `${data.name} has been created`,
                  error: "Error",
                }
              )
            }}
          >
            Promise
          </Button>
        </div>
      )
    }
    

## Changelog

### 2025-10-13 Icons

We've updated the Sonner component to use icons from `lucide`. Update your `sonner.tsx` file to use the new icons.

components/ui/sonner.tsx
    
    
    Copy"use client"
     
    import {
      CircleCheckIcon,
      InfoIcon,
      Loader2Icon,
      OctagonXIcon,
      TriangleAlertIcon,
    } from "lucide-react"
    import { useTheme } from "next-themes"
    import { Toaster as Sonner, ToasterProps } from "sonner"
     
    const Toaster = ({ ...props }: ToasterProps) => {
      const { theme = "system" } = useTheme()
     
      return (
        <Sonner
          theme={theme as ToasterProps["theme"]}
          className="toaster group"
          icons={{
            success: <CircleCheckIcon className="size-4" />,
            info: <InfoIcon className="size-4" />,
            warning: <TriangleAlertIcon className="size-4" />,
            error: <OctagonXIcon className="size-4" />,
            loading: <Loader2Icon className="size-4 animate-spin" />,
          }}
          style={
            {
              "--normal-bg": "var(--popover)",
              "--normal-text": "var(--popover-foreground)",
              "--normal-border": "var(--border)",
              "--border-radius": "var(--radius)",
            } as React.CSSProperties
          }
          {...props}
        />
      )
    }
     
    export { Toaster }

[ Slider](/docs/components/slider)[Spinner ](/docs/components/spinner)
