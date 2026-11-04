# Integrate Motion with Radix

[Radix-Vue](https://reka-ui.com/) is one of the most popular component libraries for Vue, and it takes just a couple steps to use Motion for Vue for animations.

In this guide, we'll learn how to use `motion` [components](./vue-motion-component) with Radix primitives, as well as specific setups for exit and layout animations.

## [Setup `motion` components](#setup-motion-components)

Most Radix components render and control their own DOM elements. But they also provide [the](https://reka-ui.com/docs/guides/composition#composition) `asChild` [prop](https://reka-ui.com/docs/guides/composition#composition) that, when set to `true`, will make the component use the first provided child as its DOM node instead.

By passing a `motion` [component](./react-motion-component) as this child, we can now use all of its animation props as normal:

```
<template>
  <ToastRoot :as-child="true">
    <Motion
      :initial="{ opacity: 0 }"
      :animate="{ opacity: 1 }"
      layout
    >
```

## [Exit animations](#exit-animations)

Many Radix components, like [Toast](https://reka-ui.com/docs/components/toast#toast) or [Tooltip](https://reka-ui.com/docs/components/tooltip#tooltip), would be perfect for exit animations, but can't perform them without Motion's `AnimatePresence`.

`AnimatePresence` is built on top of Vue's Transition component,This is how it tracks which components are exiting:

```
<template>
  <AnimatePresence>
    <Motion
      v-if="isOpen"
      :exit="{ opacity: 0 }"
    />
  </AnimatePresence>
</template>
```

Using exit animations with Motion Vue and Radix components is straightforward. Just wrap your unmounting component with `AnimatePresence`, and it can detect the direct child DOM unmounting and trigger exit animations.

For example, works with the Tooltip component：

```
 <Tooltip.Provider>
        <Tooltip.Root>
          <Tooltip.Trigger class="tooltip-trigger">
              Hover or focus
          </Tooltip.Trigger>
          <Tooltip.Portal>
            <AnimatePresence>
              <Tooltip.Content as-child :side-offset="10">
                <motion.div
                  class="tooltip-content"
                  :initial="{ opacity: 0, y: 20, scale: 0.8 }"
                  :animate="{ opacity: 1, y: 0, scale: 1 }"
                  :exit="{ opacity: 0,y: 20,}"
                >
                  Add to library
                  <Tooltip.Arrow class="tooltip-arrow" />
                </motion.div>
              </Tooltip.Content>
            </AnimatePresence>
          </Tooltip.Portal>
        </Tooltip.Root>
  </Tooltip.Provider>
```

## [Layout animations](#layout-animations)

Layout animations also require this same pattern of hoisting state out of the component.

```
<script setup>
const tab = ref('account')
</script>

<template>
  <Tabs.Root
    v-model="tab"
    as-child
  >
    <motion.div layout>
```

This is to ensure `motion` components know to perform layout animations when the state changes. You can even pass this state to `layoutDependency` for better performance.

```
<motion.div layout :layoutDependency="tab">
```

## [Motion+ examples](#motion-examples)

[Motion+](../plus) is a one-time payment, lifetime membership that gains you access to the source code of an ever-growing library of [examples](https://motion.dev/examples?platform=vue#radix), as well as premium components like `Cursor` and `AnimateNumber`.

[useReducedMotion](./vue-use-reduced-motion)

Next

[Get started with Motion for React](./react)