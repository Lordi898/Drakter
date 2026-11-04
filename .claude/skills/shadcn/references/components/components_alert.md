# Alert

Copy Page

[Previous](/docs/components/alert-dialog)[Next](/docs/components/aspect-ratio)

Displays a callout for user attention.

Success! Your changes have been saved

This is an alert with icon, title and description.

This Alert has a title and an icon. No description.

Unable to process your payment.

Please verify your billing information and try again.

  * Check your card details
  * Ensure sufficient funds
  * Verify billing address

Copy
    
    
    import { AlertCircleIcon, CheckCircle2Icon, PopcornIcon } from "lucide-react"
    
    import {
      Alert,
      AlertDescription,
      AlertTitle,
    } from "@/components/ui/alert"
    
    export function AlertDemo() {
      return (
        <div className="grid w-full max-w-xl items-start gap-4">
          <Alert>
            <CheckCircle2Icon />
            <AlertTitle>Success! Your changes have been saved</AlertTitle>
            <AlertDescription>
              This is an alert with icon, title and description.
            </AlertDescription>
          </Alert>
          <Alert>
            <PopcornIcon />
            <AlertTitle>
              This Alert has a title and an icon. No description.
            </AlertTitle>
          </Alert>
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertTitle>Unable to process your payment.</AlertTitle>
            <AlertDescription>
              <p>Please verify your billing information and try again.</p>
              <ul className="list-inside list-disc text-sm">
                <li>Check your card details</li>
                <li>Ensure sufficient funds</li>
                <li>Verify billing address</li>
              </ul>
            </AlertDescription>
          </Alert>
        </div>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add alert

Copy

## Usage
    
    
    Copyimport { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
    
    
    Copy<Alert variant="default | destructive">
      <Terminal />
      <AlertTitle>Heads up!</AlertTitle>
      <AlertDescription>
        You can add components and dependencies to your app using the cli.
      </AlertDescription>
    </Alert>

[ Alert Dialog](/docs/components/alert-dialog)[Aspect Ratio ](/docs/components/aspect-ratio)
