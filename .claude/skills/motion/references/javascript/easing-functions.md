# Easing functions

Easing functions are used to change the speed of an animation throughout the course of its duration. Different easing functions provide your animations with different "feelings".

Both the `animate` [function](./animate) and Motion for React's `motion` [component](./react-motion-component) have the following easing functions built-in and you can just refer to them by name.

```
// Named easing
ease: "easeIn"

// Bezier curve
ease: [0.39, 0.24, 0.3, 1]
```

But you can still import them separately to use them directly, either for use with the tiny `animate` function from `"motion/dom"` or for novel use-cases.

## [Usage](#usage)

All of Motion's easing functions can be imported straight from `"motion"`:

```
import { easeIn } from "motion"
```

By passing a `0`-`1` progress value to these functions, you'll receive an eased progress back.

```
const eased = easeIn(0.75)
```

## [Functions](#functions)

Motion provides a number of built-in easing functions:

* `cubicBezier`
* `easeIn`/`easeOut`/`easeInOut`
* `backIn`/`backOut`/`backInOut`
* `circIn`/`circOut`/`circInOut`
* `anticipate`
* `linear`
* `steps`