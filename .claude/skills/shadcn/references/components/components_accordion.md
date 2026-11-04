# Accordion

Copy Page

[Previous](/docs/components)[Next](/docs/components/alert-dialog)

A vertically stacked set of interactive headings that each reveal a section of content.

[Docs ](https://www.radix-ui.com/docs/primitives/components/accordion)[API Reference ](https://www.radix-ui.com/docs/primitives/components/accordion#api-reference)

### Product Information

Our flagship product combines cutting-edge technology with sleek design. Built with premium materials, it offers unparalleled performance and reliability.

Key features include advanced processing capabilities, and an intuitive user interface designed for both beginners and experts.

### Shipping Details

### Return Policy

Copy
    
    
    import {
      Accordion,
      AccordionContent,
      AccordionItem,
      AccordionTrigger,
    } from "@/components/ui/accordion"
    
    export function AccordionDemo() {
      return (
        <Accordion
          type="single"
          collapsible
          className="w-full"
          defaultValue="item-1"
        >
          <AccordionItem value="item-1">
            <AccordionTrigger>Product Information</AccordionTrigger>
            <AccordionContent className="flex flex-col gap-4 text-balance">
              <p>
                Our flagship product combines cutting-edge technology with sleek
                design. Built with premium materials, it offers unparalleled
                performance and reliability.
              </p>
              <p>
                Key features include advanced processing capabilities, and an
                intuitive user interface designed for both beginners and experts.
              </p>
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-2">
            <AccordionTrigger>Shipping Details</AccordionTrigger>
            <AccordionContent className="flex flex-col gap-4 text-balance">
              <p>
                We offer worldwide shipping through trusted courier partners.
                Standard delivery takes 3-5 business days, while express shipping
                ensures delivery within 1-2 business days.
              </p>
              <p>
                All orders are carefully packaged and fully insured. Track your
                shipment in real-time through our dedicated tracking portal.
              </p>
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="item-3">
            <AccordionTrigger>Return Policy</AccordionTrigger>
            <AccordionContent className="flex flex-col gap-4 text-balance">
              <p>
                We stand behind our products with a comprehensive 30-day return
                policy. If you&apos;re not completely satisfied, simply return the
                item in its original condition.
              </p>
              <p>
                Our hassle-free return process includes free return shipping and
                full refunds processed within 48 hours of receiving the returned
                item.
              </p>
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add accordion

Copy

## Usage
    
    
    Copyimport {
      Accordion,
      AccordionContent,
      AccordionItem,
      AccordionTrigger,
    } from "@/components/ui/accordion"
    
    
    Copy<Accordion type="single" collapsible>
      <AccordionItem value="item-1">
        <AccordionTrigger>Is it accessible?</AccordionTrigger>
        <AccordionContent>
          Yes. It adheres to the WAI-ARIA design pattern.
        </AccordionContent>
      </AccordionItem>
    </Accordion>

[ Components](/docs/components)[Alert Dialog ](/docs/components/alert-dialog)
