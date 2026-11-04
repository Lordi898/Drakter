# Drag animation

Drag animations allow users to move elements with their pointer.

Motion provides a suite of features to create app-quality drag animations with a simple API:

* Momentum
* Axis control
* Elastic constraints
* Direction locking
* Optional imperative start/stop controls

Although browsers provide a native [Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API), it can be challenging to create a pleasant experience, with an odd "ghost image" effect. On the other hand, it also contains native dropzone functionality - which isn't yet in Motion.

In this guide we'll take a look at all Motion's drag features and how to customise them.

## [The `drag` prop](#the-drag-prop)

The simplest way to make a component draggable is to add the `drag` prop to a `motion` component.

```
<motion.div drag />
```

### [Axis locking](#axis-locking)

To lock dragging to a single axis, you can set the prop to `"x"` or `"y"`.

```
<motion.div drag="x" />
```

## [Visual feedback with `whileDrag`](#visual-feedback-with-whiledrag)

You can animate to an animation state while an element is being dragged using the `whileDrag` prop.

When the gesture starts, the component will animate to the state defined in `whileDrag`. When it ends, it will animate back to its default `animate` state.

This is great for creating a "lift" effect, for instance by increasing the element's scale and adding a box shadow.

```
<motion.div
  drag
  whileDrag={{
    scale: 1.1,
    boxShadow: "0px 10px 20px rgba(0,0,0,0.2)"
  }}
/>
```

## [Momentum](#momentum)

By default, when a user releases a draggable element, it has **momentum**. It will perform an inertia animation based on the velocity of the pointer, creating a realistic, physical feel.

You can disable this behaviour by setting the `dragMomentum` prop to `false`.

```
<motion.div drag dragMomentum={false} />
```

You can also customise the physics of this inertia animation with the `dragTransition` prop. This is useful for creating a heavier or bouncier feel.

```
<motion.div
  drag
  dragTransition={{
    bounceStiffness: 600,
    bounceDamping: 10
  }}
/>
```

## [Constraints](#constraints)

You can constrain the movement of a draggable element using the `dragConstraints` prop.

### [Pixel constraints](#pixel-constraints)

The simplest way to apply constraints is by passing an object of `top`, `left`, `right`, and `bottom` values, measured in pixels.

```
<motion.div
  drag
  dragConstraints={{
    top: -50,
    left: -50,
    right: 50,
    bottom: 50,
  }}
/>
```

### [Ref-based constraints](#ref-based-constraints)

For more dynamic constraints, you can pass a `ref` to another component. The draggable element will then be constrained to the bounding box of that element.

```
import { motion } from "motion/react"
import { useRef } from "react"

export function DragContainer() {
  const constraintsRef = useRef(null)

  return (
    <motion.div ref={constraintsRef} style={{ width: 300, height: 200 }}>
      <motion.div drag dragConstraints={constraintsRef} />
    </motion.div>
  )
}
```

### [Elastic constraints](#elastic-constraints)

By default, dragging an element beyond its constraints will "tug" with some elasticity. You can change this behavior with the `dragElastic` prop, which accepts a value between `0` (no movement) and `1` (full movement).

```
<motion.div
  drag
  dragConstraints={{ left: 0, right: 300 }}
  dragElastic={0.1}
/>
```

## [Direction locking](#direction-locking)

You can lock an element to the first axis it's dragged on by setting the `dragDirectionLock` prop to `true`.

```
<motion.div
  drag="x"
  dragDirectionLock
  onDirectionLock={axis => console.log(`Locked to ${axis} axis`)}
/>
```

## [Drag events](#drag-events)

You can listen to the lifecycle of a drag gesture with a set of event listeners. These are useful for updating other parts of your UI in response to a drag.

The main events are `onDragStart`, `onDrag`, and `onDragEnd`.

Each callback is provided with the original `PointerEvent`, and an `info` object containing valuable data about the gesture's state:

* `point`: The `x` and `y` coordinates of the pointer.
* `delta`: The distance moved since the last event.
* `offset`: The distance from the element's origin.
* `velocity`: The current velocity of the pointer.

```
function onDrag(event, info) {
  console.log(info.point.x, info.point.y)
}

<motion.div drag onDrag={onDrag} />
```

## [Manual control with `useDragControls`](#manual-control-with-usedragcontrols)

In some cases, you might want to initiate a drag from a different element, like a handle or a video scrubber. You can achieve this with the `useDragControls` hook.

The hook returns a set of `dragControls` that you can pass to the draggable element. You can then call the `controls.start()` method from any event to begin the gesture.

```
import { motion, useDragControls } from "motion/react"

export function Scrubber() {
  const dragControls = useDragControls()

  function startDrag(event) {
    // Start the drag gesture imperatively
    dragControls.start(event, { snapToCursor: true })
  }

  return (
    <>
      <div onPointerDown={startDrag} className="scrubber-track" />
      <motion.div
        drag="x"
        dragControls={dragControls}
        dragListener={false} // Disable the default drag handler
        className="scrubber-handle"
      />
    </>
  )
}
```

Drag animations allow users to move elements with their pointer.

Motion provides a suite of features to create app-quality drag animations with a simple API:

* Momentum
* Axis control
* Elastic constraints
* Direction locking
* Optional imperative start/stop controls

Although browsers provide a native [Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API), it can be challenging to create a pleasant experience, with an odd "ghost image" effect. On the other hand, it also contains native dropzone functionality - which isn't yet in Motion.

In this guide we'll take a look at all Motion's drag features and how to customise them.

## [The `drag` prop](#the-drag-prop)

The simplest way to make a component draggable is to add the `drag` prop to a `motion` component.

```
<motion.div drag />
```

### [Axis locking](#axis-locking)

To lock dragging to a single axis, you can set the prop to `"x"` or `"y"`.

```
<motion.div drag="x" />
```

## [Visual feedback with `whileDrag`](#visual-feedback-with-whiledrag)

You can animate to an animation state while an element is being dragged using the `whileDrag` prop.

When the gesture starts, the component will animate to the state defined in `whileDrag`. When it ends, it will animate back to its default `animate` state.

This is great for creating a "lift" effect, for instance by increasing the element's scale and adding a box shadow.

```
<motion.div
  drag
  whileDrag={{
    scale: 1.1,
    boxShadow: "0px 10px 20px rgba(0,0,0,0.2)"
  }}
/>
```

## [Momentum](#momentum)

By default, when a user releases a draggable element, it has **momentum**. It will perform an inertia animation based on the velocity of the pointer, creating a realistic, physical feel.

You can disable this behaviour by setting the `dragMomentum` prop to `false`.

```
<motion.div drag dragMomentum={false} />
```

You can also customise the physics of this inertia animation with the `dragTransition` prop. This is useful for creating a heavier or bouncier feel.

```
<motion.div
  drag
  dragTransition={{
    bounceStiffness: 600,
    bounceDamping: 10
  }}
/>
```

## [Constraints](#constraints)

You can constrain the movement of a draggable element using the `dragConstraints` prop.

### [Pixel constraints](#pixel-constraints)

The simplest way to apply constraints is by passing an object of `top`, `left`, `right`, and `bottom` values, measured in pixels.

```
<motion.div
  drag
  dragConstraints={{
    top: -50,
    left: -50,
    right: 50,
    bottom: 50,
  }}
/>
```

### [Ref-based constraints](#ref-based-constraints)

For more dynamic constraints, you can pass a `ref` to another component. The draggable element will then be constrained to the bounding box of that element.

```
import { motion } from "motion/react"
import { useRef } from "react"

export function DragContainer() {
  const constraintsRef = useRef(null)

  return (
    <motion.div ref={constraintsRef} style={{ width: 300, height: 200 }}>
      <motion.div drag dragConstraints={constraintsRef} />
    </motion.div>
  )
}
```

### [Elastic constraints](#elastic-constraints)

By default, dragging an element beyond its constraints will "tug" with some elasticity. You can change this behavior with the `dragElastic` prop, which accepts a value between `0` (no movement) and `1` (full movement).

```
<motion.div
  drag
  dragConstraints={{ left: 0, right: 300 }}
  dragElastic={0.1}
/>
```

## [Direction locking](#direction-locking)

You can lock an element to the first axis it's dragged on by setting the `dragDirectionLock` prop to `true`.

```
<motion.div
  drag="x"
  dragDirectionLock
  onDirectionLock={axis => console.log(`Locked to ${axis} axis`)}
/>
```

## [Drag events](#drag-events)

You can listen to the lifecycle of a drag gesture with a set of event listeners. These are useful for updating other parts of your UI in response to a drag.

The main events are `onDragStart`, `onDrag`, and `onDragEnd`.

Each callback is provided with the original `PointerEvent`, and an `info` object containing valuable data about the gesture's state:

* `point`: The `x` and `y` coordinates of the pointer.
* `delta`: The distance moved since the last event.
* `offset`: The distance from the element's origin.
* `velocity`: The current velocity of the pointer.

```
function onDrag(event, info) {
  console.log(info.point.x, info.point.y)
}

<motion.div drag onDrag={onDrag} />
```

## [Manual control with `useDragControls`](#manual-control-with-usedragcontrols)

In some cases, you might want to initiate a drag from a different element, like a handle or a video scrubber. You can achieve this with the `useDragControls` hook.

The hook returns a set of `dragControls` that you can pass to the draggable element. You can then call the `controls.start()` method from any event to begin the gesture.

```
import { motion, useDragControls } from "motion/react"

export function Scrubber() {
  const dragControls = useDragControls()

  function startDrag(event) {
    // Start the drag gesture imperatively
    dragControls.start(event, { snapToCursor: true })
  }

  return (
    <>
      <div onPointerDown={startDrag} className="scrubber-track" />
      <motion.div
        drag="x"
        dragControls={dragControls}
        dragListener={false} // Disable the default drag handler
        className="scrubber-handle"
      />
    </>
  )
}
```

Drag animations allow users to move elements with their pointer.

Motion provides a suite of features to create app-quality drag animations with a simple API:

* Momentum
* Axis control
* Elastic constraints
* Direction locking
* Optional imperative start/stop controls

Although browsers provide a native [Drag and Drop API](https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API), it can be challenging to create a pleasant experience, with an odd "ghost image" effect. On the other hand, it also contains native dropzone functionality - which isn't yet in Motion.

In this guide we'll take a look at all Motion's drag features and how to customise them.

## [The `drag` prop](#the-drag-prop)

The simplest way to make a component draggable is to add the `drag` prop to a `motion` component.

```
<motion.div drag />
```

### [Axis locking](#axis-locking)

To lock dragging to a single axis, you can set the prop to `"x"` or `"y"`.

```
<motion.div drag="x" />
```

## [Visual feedback with `whileDrag`](#visual-feedback-with-whiledrag)

You can animate to an animation state while an element is being dragged using the `whileDrag` prop.

When the gesture starts, the component will animate to the state defined in `whileDrag`. When it ends, it will animate back to its default `animate` state.

This is great for creating a "lift" effect, for instance by increasing the element's scale and adding a box shadow.

```
<motion.div
  drag
  whileDrag={{
    scale: 1.1,
    boxShadow: "0px 10px 20px rgba(0,0,0,0.2)"
  }}
/>
```

## [Momentum](#momentum)

By default, when a user releases a draggable element, it has **momentum**. It will perform an inertia animation based on the velocity of the pointer, creating a realistic, physical feel.

You can disable this behaviour by setting the `dragMomentum` prop to `false`.

```
<motion.div drag dragMomentum={false} />
```

You can also customise the physics of this inertia animation with the `dragTransition` prop. This is useful for creating a heavier or bouncier feel.

```
<motion.div
  drag
  dragTransition={{
    bounceStiffness: 600,
    bounceDamping: 10
  }}
/>
```

## [Constraints](#constraints)

You can constrain the movement of a draggable element using the `dragConstraints` prop.

### [Pixel constraints](#pixel-constraints)

The simplest way to apply constraints is by passing an object of `top`, `left`, `right`, and `bottom` values, measured in pixels.

```
<motion.div
  drag
  dragConstraints={{
    top: -50,
    left: -50,
    right: 50,
    bottom: 50,
  }}
/>
```

### [Ref-based constraints](#ref-based-constraints)

For more dynamic constraints, you can pass a `ref` to another component. The draggable element will then be constrained to the bounding box of that element.

```
import { motion } from "motion/react"
import { useRef } from "react"

export function DragContainer() {
  const constraintsRef = useRef(null)

  return (
    <motion.div ref={constraintsRef} style={{ width: 300, height: 200 }}>
      <motion.div drag dragConstraints={constraintsRef} />
    </motion.div>
  )
}
```

### [Elastic constraints](#elastic-constraints)

By default, dragging an element beyond its constraints will "tug" with some elasticity. You can change this behavior with the `dragElastic` prop, which accepts a value between `0` (no movement) and `1` (full movement).

```
<motion.div
  drag
  dragConstraints={{ left: 0, right: 300 }}
  dragElastic={0.1}
/>
```

## [Direction locking](#direction-locking)

You can lock an element to the first axis it's dragged on by setting the `dragDirectionLock` prop to `true`.

```
<motion.div
  drag="x"
  dragDirectionLock
  onDirectionLock={axis => console.log(`Locked to ${axis} axis`)}
/>
```

## [Drag events](#drag-events)

You can listen to the lifecycle of a drag gesture with a set of event listeners. These are useful for updating other parts of your UI in response to a drag.

The main events are `onDragStart`, `onDrag`, and `onDragEnd`.

Each callback is provided with the original `PointerEvent`, and an `info` object containing valuable data about the gesture's state:

* `point`: The `x` and `y` coordinates of the pointer.
* `delta`: The distance moved since the last event.
* `offset`: The distance from the element's origin.
* `velocity`: The current velocity of the pointer.

```
function onDrag(event, info) {
  console.log(info.point.x, info.point.y)
}

<motion.div drag onDrag={onDrag} />
```

## [Manual control with `useDragControls`](#manual-control-with-usedragcontrols)

In some cases, you might want to initiate a drag from a different element, like a handle or a video scrubber. You can achieve this with the `useDragControls` hook.

The hook returns a set of `dragControls` that you can pass to the draggable element. You can then call the `controls.start()` method from any event to begin the gesture.

```
import { motion, useDragControls } from "motion/react"

export function Scrubber() {
  const dragControls = useDragControls()

  function startDrag(event) {
    // Start the drag gesture imperatively
    dragControls.start(event, { snapToCursor: true })
  }

  return (
    <>
      <div onPointerDown={startDrag} className="scrubber-track" />
      <motion.div
        drag="x"
        dragControls={dragControls}
        dragListener={false} // Disable the default drag handler
        className="scrubber-handle"
      />
    </>
  )
}
```

[Hover animation](./react-hover-animation)

Next

[Motion component](./react-motion-component)