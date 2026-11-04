# Transitions

A `transition` defines the type of animation used when animating between two values.

```
const transition = {
  duration: 0.8,
  delay: 0.5,
  ease: [0, 0.71, 0.2, 1.01],
}
```

```
// Motion component
<motion.div
  animate={{ x: 100 }}
  transition={transition}
/>

// animate() function
animate(".box", { x: 100 }, transition)
```

## [Setting a transition](#setting-a-transition)

`transition` can be set on any animation prop, and that transition will be used when the animation fires.

```
<motion.div
  whileHover={{
    scale: 1.1,
    transition: { duration: 0.2 }
  }}
/>
```

### [Value-specific transitions](#value-specific-transitions)

When animating multiple values, each value can be animated with a different transition, with `default` handling all other values:

```
// Motion component
<motion.li
  animate={{
    x: 0,
    opacity: 1,
    transition: {
      default: { type: "spring" },
      opacity: { ease: "linear" }
    }
  }}
/>

// animate() function
animate("li", { x: 0, opacity: 1 }, {
  default: { type: "spring" },
  opacity: { ease: "linear" }
})
```

### [Default transitions](#default-transitions)

It's possible to set default transitions via the `transition` prop. Either for specific `motion` components:

```
<motion.div
  animate={{ x: 100 }}
  transition={{ type: "spring", stiffness: 100 }}
/>
```

Or for a group of `motion` components [via](./react-motion-config#transition) `MotionConfig`:

```
<MotionConfig transition={{ duration: 0.4, ease: "easeInOut" }}>
  <App />
</MotionConfig>
```

## [Transition settings](#transition-settings)

#### [`type`](#type)

**Default:** Dynamic

`type` decides the type of animation to use. It can be `"tween"`, `"spring"` or `"inertia"`.

**Tween** animations are set with a duration and an easing curve.

**Spring** animations are either physics-based or duration-based.

Physics-based spring animations are set via `stiffness`, `damping` and `mass`, and these incorporate the velocity of any existing gestures or animations for natural feedback.

Duration-based spring animations are set via a `duration` and `bounce`. These don't incorporate velocity but are easier to understand.

**Inertia** animations decelerate a value based on its initial velocity, usually used to implement inertial scrolling.

```
<motion.path
  animate={{ pathLength: 1 }}
  transition={{ duration: 2, type: "tween" }}
/>
```

#### [Spring visualiser](#spring-visualiser)

TimePhysics

DurationBounceUse visual duration

### [Tween](#tween)

#### [`duration`](#duration)

**Default:** `0.3` (or `0.8` if multiple keyframes are defined)

The duration of the animation. Can also be used for `"spring"` animations when `bounce` is also set.

```
animate("ul > li", { opacity: 1 }, { duration: 1 })
```

#### [`ease`](#ease)

The easing function to use with tween animations. Accepts:

* Easing function name. E.g `"linear"`
* An array of four numbers to define a cubic bezier curve. E.g `[.17,.67,.83,.67]`
* A [JavaScript easing function](./easing-functions), that accepts and returns a value `0`-`1`.

These are the available easing function names:

* `"linear"`
* `"easeIn"`, `"easeOut"`, `"easeInOut"`
* `"circIn"`, `"circOut"`, `"circInOut"`
* `"backIn"`, `"backOut"`, `"backInOut"`
* `"anticipate"`

When animating keyframes, `ease` can optionally be set as an array of easing functions to set different easings between each value:

```
<motion.div
  animate={{
    x: [0, 100, 0],
    transition: { ease: ["easeIn", "easeOut"] }
  }}
/>
```

For immediate visual feedback, you can edit CSS or Motion easing curves directly in your code editor with the [Motion extension](./studio-install).

#### [`times`](#times)

When animating multiple keyframes, `times` can be used to adjust the position of each keyframe throughout the animation.

Each value in `times` is a value between `0` and `1`, representing the start and end of the animation.

```
<motion.div
  animate={{
    x: [0, 100, 0],
    transition: { times: [0, 0.3, 1] }
  }}
/>
```

There must be the same number of `times` as there are keyframes. Defaults to an array of evenly-spread durations.

### [Spring](#spring)

#### [`bounce`](#bounce)

**Default:** `0.25`

`bounce` determines the "bounciness" of a spring animation.

`0` is no bounce, and `1` is extremely bouncy.

`bounce` and `duration` will be overridden if `stiffness`, `damping` or `mass` are set.

```
<motion.div
  animate={{ rotateX: 90 }}
  transition={{ type: "spring", bounce: 0.25 }}
/>
```

#### [`visualDuration`](#visualduration)

If `visualDuration` is set, this will override `duration`.

The visual duration is a time, **set in seconds**, that the animation will take to visually appear to reach its target.

In other words, the bulk of the transition will occur before this time, and the "bouncy bit" will mostly happen after.

This makes it easier to edit a spring, as well as visually coordinate it with other time-based animations.

```
<motion.div
  animate={{ rotateX: 90 }}
  transition={{
    type: "spring",
    visualDuration: 0.5,
    bounce: 0.25
  }}
/>
```

#### [`damping`](#damping)

**Default:** `10`

Strength of opposing force. If set to 0, spring will oscillate indefinitely.

```
<motion.a
  animate={{ rotate: 180 }}
  transition={{ type: 'spring', damping: 300 }}
/>
```

#### [`mass`](#mass)

**Default:** `1`

Mass of the moving object. Higher values will result in more lethargic movement.

```
<motion.feTurbulence
  animate={{ baseFrequency: 0.5 }}
  transition={{ type: "spring", mass: 0.5 }}
/>
```

#### [`stiffness`](#stiffness)

**Default:** `1`

Stiffness of the spring. Higher values will create more sudden movement.

```
<motion.section
  animate={{ rotate: 180 }}
  transition={{ type: 'spring', stiffness: 50 }}
/>
```