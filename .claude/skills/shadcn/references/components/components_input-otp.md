# Input OTP

Copy Page

[Previous](/docs/components/input-group)[Next](/docs/components/input)

Accessible one-time password component with copy paste functionality.

[Docs ](https://input-otp.rodz.dev)

Copy
    
    
    import {
      InputOTP,
      InputOTPGroup,
      InputOTPSeparator,
      InputOTPSlot,
    } from "@/components/ui/input-otp"
    
    export function InputOTPDemo() {
      return (
        <InputOTP maxLength={6}>
          <InputOTPGroup>
            <InputOTPSlot index={0} />
            <InputOTPSlot index={1} />
            <InputOTPSlot index={2} />
          </InputOTPGroup>
          <InputOTPSeparator />
          <InputOTPGroup>
            <InputOTPSlot index={3} />
            <InputOTPSlot index={4} />
            <InputOTPSlot index={5} />
          </InputOTPGroup>
        </InputOTP>
      )
    }
    

## About

Input OTP is built on top of [input-otp](https://github.com/guilhermerodz/input-otp) by [@guilherme_rodz](https://twitter.com/guilherme_rodz).

## Installation

CLIManual

### Run the following command:
    
    
    pnpmnpmyarnbun
    
    
    pnpm dlx shadcn@latest add input-otp

Copy

## Usage
    
    
    Copyimport {
      InputOTP,
      InputOTPGroup,
      InputOTPSeparator,
      InputOTPSlot,
    } from "@/components/ui/input-otp"
    
    
    Copy<InputOTP maxLength={6}>
      <InputOTPGroup>
        <InputOTPSlot index={0} />
        <InputOTPSlot index={1} />
        <InputOTPSlot index={2} />
      </InputOTPGroup>
      <InputOTPSeparator />
      <InputOTPGroup>
        <InputOTPSlot index={3} />
        <InputOTPSlot index={4} />
        <InputOTPSlot index={5} />
      </InputOTPGroup>
    </InputOTP>

## Examples

### Pattern

Use the `pattern` prop to define a custom pattern for the OTP input.

Copy
    
    
    "use client"
    
    import { REGEXP_ONLY_DIGITS_AND_CHARS } from "input-otp"
    
    import {
      InputOTP,
      InputOTPGroup,
      InputOTPSlot,
    } from "@/components/ui/input-otp"
    
    export function InputOTPPattern() {
      return (
        <InputOTP maxLength={6} pattern={REGEXP_ONLY_DIGITS_AND_CHARS}>
          <InputOTPGroup>
            <InputOTPSlot index={0} />
            <InputOTPSlot index={1} />
            <InputOTPSlot index={2} />
            <InputOTPSlot index={3} />
            <InputOTPSlot index={4} />
            <InputOTPSlot index={5} />
          </InputOTPGroup>
        </InputOTP>
      )
    }
    
    
    
    Copyimport { REGEXP_ONLY_DIGITS_AND_CHARS } from "input-otp"
     
    ...
     
    <InputOTP
      maxLength={6}
      pattern={REGEXP_ONLY_DIGITS_AND_CHARS}
    >
      <InputOTPGroup>
        <InputOTPSlot index={0} />
        {/* ... */}
      </InputOTPGroup>
    </InputOTP>

### Separator

You can use the `<InputOTPSeparator />` component to add a separator between the input groups.

Copy
    
    
    import React from "react"
    
    import {
      InputOTP,
      InputOTPGroup,
      InputOTPSeparator,
      InputOTPSlot,
    } from "@/components/ui/input-otp"
    
    export function InputOTPWithSeparator() {
      return (
        <InputOTP maxLength={6}>
          <InputOTPGroup>
            <InputOTPSlot index={0} />
            <InputOTPSlot index={1} />
          </InputOTPGroup>
          <InputOTPSeparator />
          <InputOTPGroup>
            <InputOTPSlot index={2} />
            <InputOTPSlot index={3} />
          </InputOTPGroup>
          <InputOTPSeparator />
          <InputOTPGroup>
            <InputOTPSlot index={4} />
            <InputOTPSlot index={5} />
          </InputOTPGroup>
        </InputOTP>
      )
    }
    
    
    
    Copyimport {
      InputOTP,
      InputOTPGroup,
      InputOTPSeparator,
      InputOTPSlot,
    } from "@/components/ui/input-otp"
     
    ...
     
    <InputOTP maxLength={4}>
      <InputOTPGroup>
        <InputOTPSlot index={0} />
        <InputOTPSlot index={1} />
      </InputOTPGroup>
      <InputOTPSeparator />
      <InputOTPGroup>
        <InputOTPSlot index={2} />
        <InputOTPSlot index={3} />
      </InputOTPGroup>
    </InputOTP>

### Controlled

You can use the `value` and `onChange` props to control the input value.

Enter your one-time password.

Copy
    
    
    "use client"
    
    import * as React from "react"
    
    import {
      InputOTP,
      InputOTPGroup,
      InputOTPSlot,
    } from "@/components/ui/input-otp"
    
    export function InputOTPControlled() {
      const [value, setValue] = React.useState("")
    
      return (
        <div className="space-y-2">
          <InputOTP
            maxLength={6}
            value={value}
            onChange={(value) => setValue(value)}
          >
            <InputOTPGroup>
              <InputOTPSlot index={0} />
              <InputOTPSlot index={1} />
              <InputOTPSlot index={2} />
              <InputOTPSlot index={3} />
              <InputOTPSlot index={4} />
              <InputOTPSlot index={5} />
            </InputOTPGroup>
          </InputOTP>
          <div className="text-center text-sm">
            {value === "" ? (
              <>Enter your one-time password.</>
            ) : (
              <>You entered: {value}</>
            )}
          </div>
        </div>
      )
    }
    

### Form

Component `input-otp-form` not found in registry.

## Changelog

### 2024-03-19 Composition

We've made some updates and replaced the render props pattern with composition. Here's how to update your code if you prefer the composition pattern.

**Note:** You are not required to update your code if you are using the `render` prop. It is still supported.

### Update to the latest version of `input-otp`.
    
    
    pnpmnpmyarnbun
    
    
    pnpm add input-otp@latest

Copy

### Update `input-otp.tsx`

input-otp.tsx
    
    
    Copy- import { OTPInput, SlotProps } from "input-otp"
    + import { OTPInput, OTPInputContext } from "input-otp"
     
     const InputOTPSlot = React.forwardRef<
       React.ElementRef<"div">,
    -   SlotProps & React.ComponentPropsWithoutRef<"div">
    -  >(({ char, hasFakeCaret, isActive, className, ...props }, ref) => {
    +   React.ComponentPropsWithoutRef<"div"> & { index: number }
    +  >(({ index, className, ...props }, ref) => {
    +   const inputOTPContext = React.useContext(OTPInputContext)
    +   const { char, hasFakeCaret, isActive } = inputOTPContext.slots[index]

### Then replace the `render` prop in your code.
    
    
    Copy<InputOTP maxLength={6}>
      <InputOTPGroup>
        <InputOTPSlot index={0} />
        <InputOTPSlot index={1} />
        <InputOTPSlot index={2} />
      </InputOTPGroup>
      <InputOTPSeparator />
      <InputOTPGroup>
        <InputOTPSlot index={3} />
        <InputOTPSlot index={4} />
        <InputOTPSlot index={5} />
      </InputOTPGroup>
    </InputOTP>

### 2024-03-19 Disabled

To add a disabled state to the input, update `<InputOTP />` as follows:

input-otp.tsx
    
    
    Copyconst InputOTP = React.forwardRef<
      React.ElementRef<typeof OTPInput>,
      React.ComponentPropsWithoutRef<typeof OTPInput>
    >(({ className, containerClassName, ...props }, ref) => (
      <OTPInput
        ref={ref}
        containerClassName={cn(
          "flex items-center gap-2 has-[:disabled]:opacity-50",
          containerClassName
        )}
        className={cn("disabled:cursor-not-allowed", className)}
        {...props}
      />
    ))
    InputOTP.displayName = "InputOTP"

[ Input Group](/docs/components/input-group)[Input ](/docs/components/input)
