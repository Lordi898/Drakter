# Table

Copy Page

[Previous](/docs/components/switch)[Next](/docs/components/tabs)

A responsive table component.

A list of your recent invoices.Invoice| Status| Method| Amount  
---|---|---|---  
INV001| Paid| Credit Card| $250.00  
INV002| Pending| PayPal| $150.00  
INV003| Unpaid| Bank Transfer| $350.00  
INV004| Paid| Credit Card| $450.00  
INV005| Paid| PayPal| $550.00  
INV006| Pending| Bank Transfer| $200.00  
INV007| Unpaid| Credit Card| $300.00  
Total| $2,500.00  
  
Copy
    
    
    import {
      Table,
      TableBody,
      TableCaption,
      TableCell,
      TableFooter,
      TableHead,
      TableHeader,
      TableRow,
    } from "@/components/ui/table"
    
    const invoices = [
      {
        invoice: "INV001",
        paymentStatus: "Paid",
        totalAmount: "$250.00",
        paymentMethod: "Credit Card",
      },
      {
        invoice: "INV002",
        paymentStatus: "Pending",
        totalAmount: "$150.00",
        paymentMethod: "PayPal",
      },
      {
        invoice: "INV003",
        paymentStatus: "Unpaid",
        totalAmount: "$350.00",
        paymentMethod: "Bank Transfer",
      },
      {
        invoice: "INV004",
        paymentStatus: "Paid",
        totalAmount: "$450.00",
        paymentMethod: "Credit Card",
      },
      {
        invoice: "INV005",
        paymentStatus: "Paid",
        totalAmount: "$550.00",
        paymentMethod: "PayPal",
      },
      {
        invoice: "INV006",
        paymentStatus: "Pending",
        totalAmount: "$200.00",
        paymentMethod: "Bank Transfer",
      },
      {
        invoice: "INV007",
        paymentStatus: "Unpaid",
        totalAmount: "$300.00",
        paymentMethod: "Credit Card",
      },
    ]
    
    export function TableDemo() {
      return (
        <Table>
          <TableCaption>A list of your recent invoices.</TableCaption>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[100px]">Invoice</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Method</TableHead>
              <TableHead className="text-right">Amount</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {invoices.map((invoice) => (
              <TableRow key={invoice.invoice}>
                <TableCell className="font-medium">{invoice.invoice}</TableCell>
                <TableCell>{invoice.paymentStatus}</TableCell>
                <TableCell>{invoice.paymentMethod}</TableCell>
                <TableCell className="text-right">{invoice.totalAmount}</TableCell>
              </TableRow>
            ))}
          </TableBody>
          <TableFooter>
            <TableRow>
              <TableCell colSpan={3}>Total</TableCell>
              <TableCell className="text-right">$2,500.00</TableCell>
            </TableRow>
          </TableFooter>
        </Table>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add table

Copy

## Usage
    
    
    Copyimport {
      Table,
      TableBody,
      TableCaption,
      TableCell,
      TableHead,
      TableHeader,
      TableRow,
    } from "@/components/ui/table"
    
    
    Copy<Table>
      <TableCaption>A list of your recent invoices.</TableCaption>
      <TableHeader>
        <TableRow>
          <TableHead className="w-[100px]">Invoice</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Method</TableHead>
          <TableHead className="text-right">Amount</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        <TableRow>
          <TableCell className="font-medium">INV001</TableCell>
          <TableCell>Paid</TableCell>
          <TableCell>Credit Card</TableCell>
          <TableCell className="text-right">$250.00</TableCell>
        </TableRow>
      </TableBody>
    </Table>

## Data Table

You can use the `<Table />` component to build more complex data tables. Combine it with [@tanstack/react-table](https://tanstack.com/table/v8) to create tables with sorting, filtering and pagination.

See the [Data Table](/docs/components/data-table) documentation for more information.

You can also see an example of a data table in the [Tasks](/examples/tasks) demo.

[ Switch](/docs/components/switch)[Tabs ](/docs/components/tabs)
