# AnimateActivity

Checking Motion+ status…

Unlocks for everyone in

83 Days 09 Hours 27 Minutes

Or

[Get Motion+ for instant access](../plus)

Already joined?

[Login](https://plus.motion.dev/login)

Checking Motion+ status…

Unlocks for everyone in

83 Days 09 Hours 27 Minutes

Or

[Get Motion+ for instant access](../plus)

Already joined?

[Login](https://plus.motion.dev/login)

Checking Motion+ status…

Unlocks for everyone in

83 Days 09 Hours 27 Minutes

Or

[Get Motion+ for instant access](../plus)

Already joined?

[Login](https://plus.motion.dev/login)

`AnimateActivity` is an animated version of React's `Activity` component. It allows you to add exit animations when hiding elements.

Whereas `AnimatePresence` animates elements when they're **added** and **removed** from the tree, `AnimateActivity` uses the `Activity` component to **show** and **hide** the children with `display: none`, maintaining their internal state.

```
<AnimateActivity mode={isVisible ? "visible" : "hidden"}>
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    exit={{ opacity: 0 }}
  />
</AnimateActivity>
```

`AnimateActivity` is currently available in [Motion+](../plus) Early Access. As an Early Access API, expect changes as we receive feedback.

## [Install](#install)

First, add the `motion-plus` package to your project using your [private token](https://plus.motion.dev). You need to be a [Motion+ member](../plus) to generate a private token.

```
npm install "https://api.motion.dev/registry.tgz?package=motion-plus&version=2.0.2&token=YOUR_AUTH_TOKEN"
```

Once installed, `AnimateActivity` can be imported via `motion-plus/animate-activity`.

`AnimateActivity` requires `motion@12.23.24` and `react@19.2.0` or above.

Once out of alpha, `AnimateActivity` will be imported from the main `"motion"` package.

## [Usage](#usage)

`AnimateActivity` shares the same API as `Activity`. By switching the `mode` prop from `"visible"` to `"hidden"`, its child element will be hidden with `display: none` **after** child exit animations have completed.

```
<AnimateActivity mode={isVisible ? "visible" : "hidden"}>
  <Tab />
</AnimateActivity>
```

```
function Tab() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
    />
  )
}
```

### [Sequencing](#sequencing)

As with `AnimatePresence`, we can use [variants](https://motion.dev/docs/react-animation#variants) to sequence exit animations through a tree.

```
<AnimateActivity mode={isVisible ? "visible" : "hidden"}>
  <motion.ul
    exit="hidden"
    variants={{
      hidden: { delayChildren: stagger(0.1) }
    }}
  >
    {items.map(item => (
      <motion.li
        variants={{ hidden: { opacity: 0 }}}
      >
        {item.title}
      </motion.li>
    ))}
  </motion.ul>
</AnimateActivity>
```

## [Layout](#layout)

By default, exiting children will maintain their default styles in the DOM. This means that if they're `position: static` or in some way affecting the layout of the elements around them, they continue to do so until the exit animation is complete.

We can change this by setting `layoutMode` to `"pop"`. This will immediately pop the element out of its layout, allowing surrounding elements to reflow while it exits.

```
<AnimateActivity
  mode={isVisible ? "visible" : "hidden"}
  layoutMode="pop"
/>
```

[Motion component](./react-motion-component)

Next

[AnimatePresence](./react-animate-presence)