# Empty

Copy Page

[Previous](/docs/components/dropdown-menu)[Next](/docs/components/field)

Use the Empty component to display an empty state.

No Projects Yet

You haven't created any projects yet. Get started by creating your first project.

Create ProjectImport Project

Learn More 

Copy
    
    
    import { IconFolderCode } from "@tabler/icons-react"
    import { ArrowUpRightIcon } from "lucide-react"
    
    import { Button } from "@/components/ui/button"
    import {
      Empty,
      EmptyContent,
      EmptyDescription,
      EmptyHeader,
      EmptyMedia,
      EmptyTitle,
    } from "@/components/ui/empty"
    
    export function EmptyDemo() {
      return (
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <IconFolderCode />
            </EmptyMedia>
            <EmptyTitle>No Projects Yet</EmptyTitle>
            <EmptyDescription>
              You haven&apos;t created any projects yet. Get started by creating
              your first project.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <div className="flex gap-2">
              <Button>Create Project</Button>
              <Button variant="outline">Import Project</Button>
            </div>
          </EmptyContent>
          <Button
            variant="link"
            asChild
            className="text-muted-foreground"
            size="sm"
          >
            <a href="#">
              Learn More <ArrowUpRightIcon />
            </a>
          </Button>
        </Empty>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add empty

Copy

## Usage
    
    
    Copyimport {
      Empty,
      EmptyContent,
      EmptyDescription,
      EmptyHeader,
      EmptyMedia,
      EmptyTitle,
    } from "@/components/ui/empty"
    
    
    Copy<Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <Icon />
        </EmptyMedia>
        <EmptyTitle>No data</EmptyTitle>
        <EmptyDescription>No data found</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button>Add data</Button>
      </EmptyContent>
    </Empty>

## Examples

### Outline

Use the `border` utility class to create an outline empty state.

Cloud Storage Empty

Upload files to your cloud storage to access them anywhere.

Upload Files

Copy
    
    
    import { IconCloud } from "@tabler/icons-react"
    
    import { Button } from "@/components/ui/button"
    import {
      Empty,
      EmptyContent,
      EmptyDescription,
      EmptyHeader,
      EmptyMedia,
      EmptyTitle,
    } from "@/components/ui/empty"
    
    export function EmptyOutline() {
      return (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <IconCloud />
            </EmptyMedia>
            <EmptyTitle>Cloud Storage Empty</EmptyTitle>
            <EmptyDescription>
              Upload files to your cloud storage to access them anywhere.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button variant="outline" size="sm">
              Upload Files
            </Button>
          </EmptyContent>
        </Empty>
      )
    }
    

### Background

Use the `bg-*` and `bg-gradient-*` utilities to add a background to the empty state.

No Notifications

You're all caught up. New notifications will appear here.

Refresh

Copy
    
    
    import { IconBell } from "@tabler/icons-react"
    import { RefreshCcwIcon } from "lucide-react"
    
    import { Button } from "@/components/ui/button"
    import {
      Empty,
      EmptyContent,
      EmptyDescription,
      EmptyHeader,
      EmptyMedia,
      EmptyTitle,
    } from "@/components/ui/empty"
    
    export function EmptyMuted() {
      return (
        <Empty className="from-muted/50 to-background h-full bg-gradient-to-b from-30%">
          <EmptyHeader>
            <EmptyMedia variant="icon">
              <IconBell />
            </EmptyMedia>
            <EmptyTitle>No Notifications</EmptyTitle>
            <EmptyDescription>
              You&apos;re all caught up. New notifications will appear here.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button variant="outline" size="sm">
              <RefreshCcwIcon />
              Refresh
            </Button>
          </EmptyContent>
        </Empty>
      )
    }
    

### Avatar

Use the `EmptyMedia` component to display an avatar in the empty state.

LR

User Offline

This user is currently offline. You can leave a message to notify them or try again later.

Leave Message

Copy
    
    
    import {
      Avatar,
      AvatarFallback,
      AvatarImage,
    } from "@/components/ui/avatar"
    import { Button } from "@/components/ui/button"
    import {
      Empty,
      EmptyContent,
      EmptyDescription,
      EmptyHeader,
      EmptyMedia,
      EmptyTitle,
    } from "@/components/ui/empty"
    
    export function EmptyAvatar() {
      return (
        <Empty>
          <EmptyHeader>
            <EmptyMedia variant="default">
              <Avatar className="size-12">
                <AvatarImage
                  src="https://github.com/shadcn.png"
                  className="grayscale"
                />
                <AvatarFallback>LR</AvatarFallback>
              </Avatar>
            </EmptyMedia>
            <EmptyTitle>User Offline</EmptyTitle>
            <EmptyDescription>
              This user is currently offline. You can leave a message to notify them
              or try again later.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button size="sm">Leave Message</Button>
          </EmptyContent>
        </Empty>
      )
    }
    

### Avatar Group

Use the `EmptyMedia` component to display an avatar group in the empty state.

CNLRER

No Team Members

Invite your team to collaborate on this project.

Invite Members

Copy
    
    
    import { PlusIcon } from "lucide-react"
    
    import {
      Avatar,
      AvatarFallback,
      AvatarImage,
    } from "@/components/ui/avatar"
    import { Button } from "@/components/ui/button"
    import {
      Empty,
      EmptyContent,
      EmptyDescription,
      EmptyHeader,
      EmptyMedia,
      EmptyTitle,
    } from "@/components/ui/empty"
    
    export function EmptyAvatarGroup() {
      return (
        <Empty>
          <EmptyHeader>
            <EmptyMedia>
              <div className="*:data-[slot=avatar]:ring-background flex -space-x-2 *:data-[slot=avatar]:size-12 *:data-[slot=avatar]:ring-2 *:data-[slot=avatar]:grayscale">
                <Avatar>
                  <AvatarImage src="https://github.com/shadcn.png" alt="@shadcn" />
                  <AvatarFallback>CN</AvatarFallback>
                </Avatar>
                <Avatar>
                  <AvatarImage
                    src="https://github.com/maxleiter.png"
                    alt="@maxleiter"
                  />
                  <AvatarFallback>LR</AvatarFallback>
                </Avatar>
                <Avatar>
                  <AvatarImage
                    src="https://github.com/evilrabbit.png"
                    alt="@evilrabbit"
                  />
                  <AvatarFallback>ER</AvatarFallback>
                </Avatar>
              </div>
            </EmptyMedia>
            <EmptyTitle>No Team Members</EmptyTitle>
            <EmptyDescription>
              Invite your team to collaborate on this project.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button size="sm">
              <PlusIcon />
              Invite Members
            </Button>
          </EmptyContent>
        </Empty>
      )
    }
    

### InputGroup

You can add an `InputGroup` component to the `EmptyContent` component.

404 - Not Found

The page you're looking for doesn't exist. Try searching for what you need below.

`/`

Need help? Contact support

Copy
    
    
    import { SearchIcon } from "lucide-react"
    
    import {
      Empty,
      EmptyContent,
      EmptyDescription,
      EmptyHeader,
      EmptyTitle,
    } from "@/components/ui/empty"
    import {
      InputGroup,
      InputGroupAddon,
      InputGroupInput,
    } from "@/components/ui/input-group"
    import { Kbd } from "@/components/ui/kbd"
    
    export function EmptyInputGroup() {
      return (
        <Empty>
          <EmptyHeader>
            <EmptyTitle>404 - Not Found</EmptyTitle>
            <EmptyDescription>
              The page you&apos;re looking for doesn&apos;t exist. Try searching for
              what you need below.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <InputGroup className="sm:w-3/4">
              <InputGroupInput placeholder="Try searching for pages..." />
              <InputGroupAddon>
                <SearchIcon />
              </InputGroupAddon>
              <InputGroupAddon align="inline-end">
                <Kbd>/</Kbd>
              </InputGroupAddon>
            </InputGroup>
            <EmptyDescription>
              Need help? <a href="#">Contact support</a>
            </EmptyDescription>
          </EmptyContent>
        </Empty>
      )
    }
    

## API Reference

### Empty

The main component of the empty state. Wraps the `EmptyHeader` and `EmptyContent` components.

Prop| Type| Default  
---|---|---  
`className`| `string`|   
      
    
    Copy<Empty>
      <EmptyHeader />
      <EmptyContent />
    </Empty>

### EmptyHeader

The `EmptyHeader` component wraps the empty media, title, and description.

Prop| Type| Default  
---|---|---  
`className`| `string`|   
      
    
    Copy<EmptyHeader>
      <EmptyMedia />
      <EmptyTitle />
      <EmptyDescription />
    </EmptyHeader>

### EmptyMedia

Use the `EmptyMedia` component to display the media of the empty state such as an icon or an image. You can also use it to display other components such as an avatar.

Prop| Type| Default  
---|---|---  
`variant`| `"default" | "icon"`| `default`  
`className`| `string`|   
      
    
    Copy<EmptyMedia variant="icon">
      <Icon />
    </EmptyMedia>
    
    
    Copy<EmptyMedia>
      <Avatar>
        <AvatarImage src="..." />
        <AvatarFallback>CN</AvatarFallback>
      </Avatar>
    </EmptyMedia>

### EmptyTitle

Use the `EmptyTitle` component to display the title of the empty state.

Prop| Type| Default  
---|---|---  
`className`| `string`|   
      
    
    Copy<EmptyTitle>No data</EmptyTitle>

### EmptyDescription

Use the `EmptyDescription` component to display the description of the empty state.

Prop| Type| Default  
---|---|---  
`className`| `string`|   
      
    
    Copy<EmptyDescription>You do not have any notifications.</EmptyDescription>

### EmptyContent

Use the `EmptyContent` component to display the content of the empty state such as a button, input or a link.

Prop| Type| Default  
---|---|---  
`className`| `string`|   
      
    
    Copy<EmptyContent>
      <Button>Add Project</Button>
    </EmptyContent>

[ Dropdown Menu](/docs/components/dropdown-menu)[Field ](/docs/components/field)
