# useAnimationFrame

`useAnimationFrame` runs a callback once every animation frame.

```
useAnimationFrame((time) => {
  ref.current.style.transform = `rotateY(${time}deg)`
})
```

The callback is provided two arguments:

* `time`, the total duration of time since the callback was first called.
* `delta`, the total duration of time since the last animation frame.

```
import { useAnimationFrame } from "motion/react"

function Component() {
  const ref = useRef(null)

  useAnimationFrame((time, delta) => {
    ref.current.style.transform = `rotateY(${time}deg)`
  })

  return <div ref={ref} />
}
```

`useAnimationFrame` runs a callback once every animation frame.

```
useAnimationFrame((time) => {
  ref.current.style.transform = `rotateY(${time}deg)`
})
```

The callback is provided two arguments:

* `time`, the total duration of time since the callback was first called.
* `delta`, the total duration of time since the last animation frame.

```
import { useAnimationFrame } from "motion/react"

function Component() {
  const ref = useRef(null)

  useAnimationFrame((time, delta) => {
    ref.current.style.transform = `rotateY(${time}deg)`
  })

  return <div ref={ref} />
}
```

`useAnimationFrame` runs a callback once every animation frame.

```
useAnimationFrame((time) => {
  ref.current.style.transform = `rotateY(${time}deg)`
})
```

The callback is provided two arguments:

* `time`, the total duration of time since the callback was first called.
* `delta`, the total duration of time since the last animation frame.

```
import { useAnimationFrame } from "motion/react"

function Component() {
  const ref = useRef(null)

  useAnimationFrame((time, delta) => {
    ref.current.style.transform = `rotateY(${time}deg)`
  })

  return <div ref={ref} />
}
```

[useAnimate](./react-use-animate)

Next

[useDragControls](./react-use-drag-controls)