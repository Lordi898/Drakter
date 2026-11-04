# Pagination

Copy Page

[Previous](/docs/components/navigation-menu)[Next](/docs/components/popover)

Pagination with page navigation, next and previous links.

  * Previous
  * 1
  * 2
  * 3
  * More pages
  * Next

Copy
    
    
    import {
      Pagination,
      PaginationContent,
      PaginationEllipsis,
      PaginationItem,
      PaginationLink,
      PaginationNext,
      PaginationPrevious,
    } from "@/components/ui/pagination"
    
    export function PaginationDemo() {
      return (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious href="#" />
            </PaginationItem>
            <PaginationItem>
              <PaginationLink href="#">1</PaginationLink>
            </PaginationItem>
            <PaginationItem>
              <PaginationLink href="#" isActive>
                2
              </PaginationLink>
            </PaginationItem>
            <PaginationItem>
              <PaginationLink href="#">3</PaginationLink>
            </PaginationItem>
            <PaginationItem>
              <PaginationEllipsis />
            </PaginationItem>
            <PaginationItem>
              <PaginationNext href="#" />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add pagination

Copy

## Usage
    
    
    Copyimport {
      Pagination,
      PaginationContent,
      PaginationEllipsis,
      PaginationItem,
      PaginationLink,
      PaginationNext,
      PaginationPrevious,
    } from "@/components/ui/pagination"
    
    
    Copy<Pagination>
      <PaginationContent>
        <PaginationItem>
          <PaginationPrevious href="#" />
        </PaginationItem>
        <PaginationItem>
          <PaginationLink href="#">1</PaginationLink>
        </PaginationItem>
        <PaginationItem>
          <PaginationEllipsis />
        </PaginationItem>
        <PaginationItem>
          <PaginationNext href="#" />
        </PaginationItem>
      </PaginationContent>
    </Pagination>

### Next.js

By default the `<PaginationLink />` component will render an `<a />` tag.

To use the Next.js `<Link />` component, make the following updates to `pagination.tsx`.
    
    
    Copy+ import Link from "next/link"
     
    - type PaginationLinkProps = ... & React.ComponentProps<"a">
    + type PaginationLinkProps = ... & React.ComponentProps<typeof Link>
     
    const PaginationLink = ({...props }: ) => (
      <PaginationItem>
    -   <a>
    +   <Link>
          // ...
    -   </a>
    +   </Link>
      </PaginationItem>
    )
     

**Note:** We are making updates to the cli to automatically do this for you.

[ Navigation Menu](/docs/components/navigation-menu)[Popover ](/docs/components/popover)
