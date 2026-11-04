# stagger

When animating elements with the [animate](./animate) function, it's possible to stagger animations across them using `stagger()`.

```
import { animate, stagger } from "motion"

animate(
  "li",
  { opacity: 1 },
  { delay: stagger(0.1) }
)
```

## [Usage](#usage)

Import `stagger` from Motion.

```
import { animate, stagger } from "motion"
```

By passing a duration, in seconds, to `stagger`, the `delay` of each element will be increased by that amount for each animation.

```
animate(
  "li",
  { opacity: 1 },
  { delay: stagger(0.1) }
)
```

## [Options](#options)

`stagger` accepts options via its second argument.

### [`startDelay`](#startdelay)

**Default:** `0`

The initial delay from which to calculate subsequent delays.

```
stagger(0.1, { startDelay: 0.2 }) // 0.2, 0.3, 0.4...
```

### [`from`](#from)

**Default:** `"first"`

Specifies which element in the array from which to stagger. Can be set as `"first"`, `"center"`, `"last"`, or a number to specify an index.

### [`ease`](#ease)

**Default:** `"linear"`

By passing an easing function, staggers can be redistributed through the total stagger time.

Any easing function or [Motion easing](./easing-functions) is accepted, like a cubic bezier definition:

```
stagger(0.1, { ease: [.32, .23, .4, .9] })
```

Name of an easing function:

```
stagger(0.1, { ease: "easeOut" })
```

Or a custom easing function:

```
stagger(0.1, { ease: p => Math.sin(p) })
```

When animating elements with the [animate](./animate) function, it's possible to stagger animations across them using `stagger()`.

```
import { animate, stagger } from "motion"

animate(
  "li",
  { opacity: 1 },
  { delay: stagger(0.1) }
)
```

## [Usage](#usage)

Import `stagger` from Motion.

```
import { animate, stagger } from "motion"
```

By passing a duration, in seconds, to `stagger`, the `delay` of each element will be increased by that amount for each animation.

```
animate(
  "li",
  { opacity: 1 },
  { delay: stagger(0.1) }
)
```

## [Options](#options)

`stagger` accepts options via its second argument.

### [`startDelay`](#startdelay)

**Default:** `0`

The initial delay from which to calculate subsequent delays.

```
stagger(0.1, { startDelay: 0.2 }) // 0.2, 0.3, 0.4...
```

### [`from`](#from)

**Default:** `"first"`

Specifies which element in the array from which to stagger. Can be set as `"first"`, `"center"`, `"last"`, or a number to specify an index.

### [`ease`](#ease)

**Default:** `"linear"`

By passing an easing function, staggers can be redistributed through the total stagger time.

Any easing function or [Motion easing](./easing-functions) is accepted, like a cubic bezier definition:

```
stagger(0.1, { ease: [.32, .23, .4, .9] })
```

Name of an easing function:

```
stagger(0.1, { ease: "easeOut" })
```

Or a custom easing function:

```
stagger(0.1, { ease: p => Math.sin(p) })
```

When animating elements with the [animate](./animate) function, it's possible to stagger animations across them using `stagger()`.

```
import { animate, stagger } from "motion"

animate(
  "li",
  { opacity: 1 },
  { delay: stagger(0.1) }
)
```

## [Usage](#usage)

Import `stagger` from Motion.

```
import { animate, stagger } from "motion"
```

By passing a duration, in seconds, to `stagger`, the `delay` of each element will be increased by that amount for each animation.

```
animate(
  "li",
  { opacity: 1 },
  { delay: stagger(0.1) }
)
```

## [Options](#options)

`stagger` accepts options via its second argument.

### [`startDelay`](#startdelay)

**Default:** `0`

The initial delay from which to calculate subsequent delays.

```
stagger(0.1, { startDelay: 0.2 }) // 0.2, 0.3, 0.4...
```

### [`from`](#from)

**Default:** `"first"`

Specifies which element in the array from which to stagger. Can be set as `"first"`, `"center"`, `"last"`, or a number to specify an index.

### [`ease`](#ease)

**Default:** `"linear"`

By passing an easing function, staggers can be redistributed through the total stagger time.

Any easing function or [Motion easing](./easing-functions) is accepted, like a cubic bezier definition:

```
stagger(0.1, { ease: [.32, .23, .4, .9] })
```

Name of an easing function:

```
stagger(0.1, { ease: "easeOut" })
```

Or a custom easing function:

```
stagger(0.1, { ease: p => Math.sin(p) })
```

Previous

[spring](./spring)

Next

[transform](./transform)