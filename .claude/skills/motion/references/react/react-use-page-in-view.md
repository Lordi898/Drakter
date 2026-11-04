# usePageInView

`usePageInView` is a tiny utility hook for tracking page/document visibility. This is useful for improving performance by pausing animations, video playback, or other activity when the user navigates to another tab, and resuming on return.

This saves CPU cycles, improves battery life, and helps ensure a smooth user experience.

## [Usage](#usage)

Import from `"motion/react"`:

```
import { usePageInView } from "motion/react"
```

`usePageInView` returns `true` when the current page is the user's active tab, and defaults to `true` on the server and initial client render before a measurement can be made.

```
const isPageInView = usePageInView()
```

This state can be used to pause animations or videos when the page is hidden:

```
const videoRef = useRef(null)
const isInView = usePageInView()

useEffect(() => {
  const videoElement = videoRef.current
  if (!videoElement) return

  if (isInView) {
    videoElement.play()
  } else {
    videoElement.pause()
  }
}, [isInView])
```

Or starting/stopping animation loops created with `useAnimationFrame`.

```
useAnimationFrame(isPageInView ? update : undefined)
```

`usePageInView` is a tiny utility hook for tracking page/document visibility. This is useful for improving performance by pausing animations, video playback, or other activity when the user navigates to another tab, and resuming on return.

This saves CPU cycles, improves battery life, and helps ensure a smooth user experience.

## [Usage](#usage)

Import from `"motion/react"`:

```
import { usePageInView } from "motion/react"
```

`usePageInView` returns `true` when the current page is the user's active tab, and defaults to `true` on the server and initial client render before a measurement can be made.

```
const isPageInView = usePageInView()
```

This state can be used to pause animations or videos when the page is hidden:

```
const videoRef = useRef(null)
const isInView = usePageInView()

useEffect(() => {
  const videoElement = videoRef.current
  if (!videoElement) return

  if (isInView) {
    videoElement.play()
  } else {
    videoElement.pause()
  }
}, [isInView])
```

Or starting/stopping animation loops created with `useAnimationFrame`.

```
useAnimationFrame(isPageInView ? update : undefined)
```

`usePageInView` is a tiny utility hook for tracking page/document visibility. This is useful for improving performance by pausing animations, video playback, or other activity when the user navigates to another tab, and resuming on return.

This saves CPU cycles, improves battery life, and helps ensure a smooth user experience.

## [Usage](#usage)

Import from `"motion/react"`:

```
import { usePageInView } from "motion/react"
```

`usePageInView` returns `true` when the current page is the user's active tab, and defaults to `true` on the server and initial client render before a measurement can be made.

```
const isPageInView = usePageInView()
```

This state can be used to pause animations or videos when the page is hidden:

```
const videoRef = useRef(null)
const isInView = usePageInView()

useEffect(() => {
  const videoElement = videoRef.current
  if (!videoElement) return

  if (isInView) {
    videoElement.play()
  } else {
    videoElement.pause()
  }
}, [isInView])
```

Or starting/stopping animation loops created with `useAnimationFrame`.

```
useAnimationFrame(isPageInView ? update : undefined)
```

[useInView](./react-use-in-view)

Next

[useReducedMotion](./react-use-reduced-motion)