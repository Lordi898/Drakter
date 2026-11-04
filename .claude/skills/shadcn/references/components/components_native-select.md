# Native Select

Copy Page

[Previous](/docs/components/menubar)[Next](/docs/components/navigation-menu)

A styled native HTML select element with consistent design system integration.

For a styled select component, see the [Select](/docs/components/select) component.

Select statusTodoIn ProgressDoneCancelled

Copy
    
    
    import {
      NativeSelect,
      NativeSelectOption,
    } from "@/components/ui/native-select"
    
    export function NativeSelectDemo() {
      return (
        <NativeSelect>
          <NativeSelectOption value="">Select status</NativeSelectOption>
          <NativeSelectOption value="todo">Todo</NativeSelectOption>
          <NativeSelectOption value="in-progress">In Progress</NativeSelectOption>
          <NativeSelectOption value="done">Done</NativeSelectOption>
          <NativeSelectOption value="cancelled">Cancelled</NativeSelectOption>
        </NativeSelect>
      )
    }
    

## Installation

CLIManual
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add native-select

Copy

## Usage
    
    
    Copyimport {
      NativeSelect,
      NativeSelectOptGroup,
      NativeSelectOption,
    } from "@/components/ui/native-select"
    
    
    Copy<NativeSelect>
      <NativeSelectOption value="">Select a fruit</NativeSelectOption>
      <NativeSelectOption value="apple">Apple</NativeSelectOption>
      <NativeSelectOption value="banana">Banana</NativeSelectOption>
      <NativeSelectOption value="blueberry">Blueberry</NativeSelectOption>
      <NativeSelectOption value="grapes" disabled>
        Grapes
      </NativeSelectOption>
      <NativeSelectOption value="pineapple">Pineapple</NativeSelectOption>
    </NativeSelect>

## Examples

### With Groups

Organize options using `NativeSelectOptGroup` for better categorization.

Select departmentFrontendBackendDevOpsSales RepAccount ManagerSales DirectorCustomer SupportProduct ManagerOperations Manager

Copy
    
    
    import {
      NativeSelect,
      NativeSelectOptGroup,
      NativeSelectOption,
    } from "@/components/ui/native-select"
    
    export function NativeSelectGroups() {
      return (
        <NativeSelect>
          <NativeSelectOption value="">Select department</NativeSelectOption>
          <NativeSelectOptGroup label="Engineering">
            <NativeSelectOption value="frontend">Frontend</NativeSelectOption>
            <NativeSelectOption value="backend">Backend</NativeSelectOption>
            <NativeSelectOption value="devops">DevOps</NativeSelectOption>
          </NativeSelectOptGroup>
          <NativeSelectOptGroup label="Sales">
            <NativeSelectOption value="sales-rep">Sales Rep</NativeSelectOption>
            <NativeSelectOption value="account-manager">
              Account Manager
            </NativeSelectOption>
            <NativeSelectOption value="sales-director">
              Sales Director
            </NativeSelectOption>
          </NativeSelectOptGroup>
          <NativeSelectOptGroup label="Operations">
            <NativeSelectOption value="support">
              Customer Support
            </NativeSelectOption>
            <NativeSelectOption value="product-manager">
              Product Manager
            </NativeSelectOption>
            <NativeSelectOption value="ops-manager">
              Operations Manager
            </NativeSelectOption>
          </NativeSelectOptGroup>
        </NativeSelect>
      )
    }
    
    
    
    Copy<NativeSelect>
      <NativeSelectOption value="">Select a food</NativeSelectOption>
      <NativeSelectOptGroup label="Fruits">
        <NativeSelectOption value="apple">Apple</NativeSelectOption>
        <NativeSelectOption value="banana">Banana</NativeSelectOption>
        <NativeSelectOption value="blueberry">Blueberry</NativeSelectOption>
      </NativeSelectOptGroup>
      <NativeSelectOptGroup label="Vegetables">
        <NativeSelectOption value="carrot">Carrot</NativeSelectOption>
        <NativeSelectOption value="broccoli">Broccoli</NativeSelectOption>
        <NativeSelectOption value="spinach">Spinach</NativeSelectOption>
      </NativeSelectOptGroup>
    </NativeSelect>

### Disabled State

Disable individual options or the entire select component.

Select priorityLowMediumHighCritical

Copy
    
    
    import {
      NativeSelect,
      NativeSelectOption,
    } from "@/components/ui/native-select"
    
    export function NativeSelectDisabled() {
      return (
        <NativeSelect disabled>
          <NativeSelectOption value="">Select priority</NativeSelectOption>
          <NativeSelectOption value="low">Low</NativeSelectOption>
          <NativeSelectOption value="medium">Medium</NativeSelectOption>
          <NativeSelectOption value="high">High</NativeSelectOption>
          <NativeSelectOption value="critical">Critical</NativeSelectOption>
        </NativeSelect>
      )
    }
    

### Invalid State

Show validation errors with the `aria-invalid` attribute and error styling.

Select roleAdminEditorViewerGuest

Copy
    
    
    import {
      NativeSelect,
      NativeSelectOption,
    } from "@/components/ui/native-select"
    
    export function NativeSelectInvalid() {
      return (
        <NativeSelect aria-invalid="true">
          <NativeSelectOption value="">Select role</NativeSelectOption>
          <NativeSelectOption value="admin">Admin</NativeSelectOption>
          <NativeSelectOption value="editor">Editor</NativeSelectOption>
          <NativeSelectOption value="viewer">Viewer</NativeSelectOption>
          <NativeSelectOption value="guest">Guest</NativeSelectOption>
        </NativeSelect>
      )
    }
    
    
    
    Copy<NativeSelect aria-invalid="true">
      <NativeSelectOption value="">Select a country</NativeSelectOption>
      <NativeSelectOption value="us">United States</NativeSelectOption>
      <NativeSelectOption value="uk">United Kingdom</NativeSelectOption>
      <NativeSelectOption value="ca">Canada</NativeSelectOption>
    </NativeSelect>

### Form Integration

Use with form libraries like React Hook Form for controlled components.

Component `native-select-form` not found in registry.

### Input Group Integration

Combine with `InputGroup` for complex input layouts.

Component `native-select-input-group` not found in registry.

## Native Select vs Select

  * Use `NativeSelect` when you need native browser behavior, better performance, or mobile-optimized dropdowns.
  * Use `Select` when you need custom styling, animations, or complex interactions.

The `NativeSelect` component provides native HTML select functionality with consistent styling that matches your design system.

## Accessibility

  * The component maintains all native HTML select accessibility features.
  * Screen readers can navigate through options using arrow keys.
  * The chevron icon is marked as `aria-hidden="true"` to avoid duplication.
  * Use `aria-label` or `aria-labelledby` for additional context when needed.

    
    
    Copy<NativeSelect aria-label="Choose your preferred language">
      <NativeSelectOption value="en">English</NativeSelectOption>
      <NativeSelectOption value="es">Spanish</NativeSelectOption>
      <NativeSelectOption value="fr">French</NativeSelectOption>
    </NativeSelect>

## API Reference

### NativeSelect

The main select component that wraps the native HTML select element.

Prop| Type| Default  
---|---|---  
`className`| `string`|   
  
All other props are passed through to the underlying `<select>` element.
    
    
    Copy<NativeSelect>
      <NativeSelectOption value="option1">Option 1</NativeSelectOption>
      <NativeSelectOption value="option2">Option 2</NativeSelectOption>
    </NativeSelect>

### NativeSelectOption

Represents an individual option within the select.

Prop| Type| Default  
---|---|---  
`value`| `string`|   
`disabled`| `boolean`| `false`  
`className`| `string`|   
  
All other props are passed through to the underlying `<option>` element.
    
    
    Copy<NativeSelectOption value="apple">Apple</NativeSelectOption>
    <NativeSelectOption value="banana" disabled>
      Banana
    </NativeSelectOption>

### NativeSelectOptGroup

Groups related options together for better organization.

Prop| Type| Default  
---|---|---  
`label`| `string`|   
`disabled`| `boolean`| `false`  
`className`| `string`|   
  
All other props are passed through to the underlying `<optgroup>` element.
    
    
    Copy<NativeSelectOptGroup label="Fruits">
      <NativeSelectOption value="apple">Apple</NativeSelectOption>
      <NativeSelectOption value="banana">Banana</NativeSelectOption>
    </NativeSelectOptGroup>

[ Menubar](/docs/components/menubar)[Navigation Menu ](/docs/components/navigation-menu)
