---
name: motion
description: Comprehensive Motion animation library guide for React, JavaScript (vanilla), and Vue. Use when building web animations, including simple transforms, scroll-triggered effects, gesture-driven interactions, layout animations, SVG path animations, or any production-grade UI animations. Covers the complete Motion API including motion components, hooks, transitions, springs, and all animation patterns. Triggers include building animations, animating elements, implementing scroll effects, creating interactive gestures, or working with the Motion/Framer Motion library.
---

# Motion Animation Library

This skill provides comprehensive documentation for Motion (formerly Framer Motion), a production-grade animation library for React, JavaScript, and Vue.

## Overview

Motion is a powerful, production-ready animation library that provides:

- **Declarative API**: Simple prop-based animations that scale from basic to complex
- **Hardware acceleration**: 120fps GPU-accelerated animations
- **Hybrid engine**: Combines browser performance with JavaScript flexibility
- **Complete feature set**: Transforms, scroll effects, gestures, layout animations, SVG paths, and more
- **Framework support**: First-class React, JavaScript (vanilla), and Vue packages

## When to Use This Skill

Use this skill when you need to:

- Build any type of web animation (simple hover effects to complex sequences)
- Implement scroll-triggered or scroll-linked animations
- Create gesture-driven interactions (hover, tap, drag)
- Animate layout changes or shared element transitions
- Work with SVG path animations or morphing
- Integrate Motion with UI libraries (Radix, Base UI, Tailwind)
- Migrate from GSAP or other animation libraries
- Optimize animation performance

## Quick Start Patterns

### React

```javascript
import { motion } from "motion/react"

function Component() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    />
  )
}
```

### JavaScript (Vanilla)

```javascript
import { animate } from "motion"

animate(".box", 
  { opacity: 1, x: 100 },
  { duration: 1, easing: "ease-out" }
)
```

### Vue

```vue
<script setup>
import { motion } from "motion-v"
</script>

<template>
  <motion.div
    :initial="{ opacity: 0 }"
    :animate="{ opacity: 1 }"
  />
</template>
```

## Documentation Organization

The complete Motion documentation is organized into three framework-specific sections:

### React Documentation (`references/react/`)

45 comprehensive guides covering:

- **Getting Started**: Installation, first animations, configuration
- **Animation**: Transforms, keyframes, transitions, SVG, scroll, layout
- **Gestures**: Hover, tap, drag, touch interactions
- **Components**: motion, AnimatePresence, LayoutGroup, Reorder, MotionConfig
- **Motion Values**: useMotionValue, useTransform, useScroll, useSpring
- **Hooks**: useAnimate, useInView, useAnimationFrame, useDragControls
- **Integrations**: Framer, Figma, Tailwind, Radix, Base UI
- **Premium APIs**: AnimateNumber, Carousel, Cursor, Ticker, Typewriter

**Key files**:
- `references/react/react.md` - Complete getting started guide
- `references/react/react-animation.md` - Core animation concepts
- `references/react/react-motion-component.md` - The motion component API
- `references/react/react-scroll-animations.md` - Scroll effects
- `references/react/react-layout-animations.md` - Layout animations
- `references/react/react-gestures.md` - Gesture handling

### JavaScript Documentation (`references/javascript/`)

35 guides for vanilla JavaScript usage:

- **Animation**: animate(), scroll(), easing functions
- **Gestures & Events**: hover, inView, press, resize
- **Utils**: delay, stagger, spring, transform, splitText
- **Motion Values**: motionValue, transformValue, springValue
- **Renderers**: styleEffect, attrEffect, svgEffect
- **Integrations**: CSS, Webflow, WordPress, Squarespace
- **Guides**: Performance, GSAP migration, FAQs

**Key files**:
- `references/javascript/quick-start.md` - Getting started with vanilla JS
- `references/javascript/animate.md` - Core animation function
- `references/javascript/scroll.md` - Scroll animations
- `references/javascript/spring.md` - Spring physics

### Vue Documentation (`references/vue/`)

30 guides for Vue integration:

- **Getting Started**: Installation, Nuxt support, first animations
- **Animation**: Core concepts, gestures, layout, scroll, transitions
- **Components**: motion, AnimatePresence, LayoutGroup, MotionConfig
- **Motion Values**: useMotionValue, useTransform, useScroll, useSpring
- **Hooks**: useAnimate, useInView, useDragControls
- **Integrations**: Radix-Vue
- **Premium APIs**: AnimateNumber, Cursor, Ticker, Typewriter

**Key files**:
- `references/vue/vue.md` - Complete Vue getting started guide
- `references/vue/vue-animation.md` - Vue animation patterns
- `references/vue/vue-motion-component.md` - Vue motion component API
- `references/vue/vue-gestures.md` - Vue gesture handling

## How to Use This Skill

### 1. Choose Your Framework

Based on the user's tech stack or question context, determine which framework they're using:
- React/Next.js → Use React documentation
- Vanilla HTML/JS or no framework → Use JavaScript documentation  
- Vue/Nuxt → Use Vue documentation

### 2. Find Relevant Documentation

When a user asks about a specific Motion feature:

1. **Identify the topic**: Animation type, component, hook, or integration
2. **Read the relevant reference file**: Use the framework-specific path
3. **Provide code examples**: From the documentation with explanations
4. **Link to related topics**: When applicable

**Example workflow**:
- User asks: "How do I create scroll-triggered animations in React?"
- Read: `references/react/react-scroll-animations.md`
- Provide: Code examples for whileInView and useScroll
- Mention: Related layout animations if relevant

### 3. Common Patterns

**Basic animation**:
```javascript
// React
<motion.div animate={{ x: 100 }} />

// JavaScript
animate(".box", { x: 100 })

// Vue
<motion.div :animate="{ x: 100 }" />
```

**Scroll-triggered**:
```javascript
// React
<motion.div whileInView={{ opacity: 1 }} />

// JavaScript
inView(".box", ({ target }) => {
  animate(target, { opacity: 1 })
})

// Vue
<motion.div :whileInView="{ opacity: 1 }" />
```

**Gestures**:
```javascript
// React
<motion.button whileHover={{ scale: 1.1 }} whileTap={{ scale: 0.95 }} />

// Vue
<motion.button :whileHover="{ scale: 1.1 }" :whilePress="{ scale: 0.95 }" />
```

**Layout animations**:
```javascript
// React/Vue
<motion.div layout />
```

### 4. Advanced Topics

For complex scenarios, combine multiple documentation files:

- **Scroll + Layout**: Read both scroll and layout animation docs
- **Complex sequences**: Combine animation docs with useAnimate hook
- **Performance optimization**: Reference performance guide and lazy loading

### 5. Best Practices

When providing Motion solutions:

- **Start simple**: Begin with basic patterns, add complexity as needed
- **Use spring physics**: Default to springs for natural-feeling animations
- **Hardware acceleration**: Prefer transforms (x, y, scale) over CSS properties
- **Reduce motion**: Respect prefers-reduced-motion user settings
- **Progressive enhancement**: Ensure core functionality works without animations

## Key Concepts

### Motion Values

Motion values track animation state and velocity. They're performant because they update outside the React render cycle:

```javascript
const x = useMotionValue(0)
const xVelocity = useVelocity(x)
```

### Variants

Variants enable coordinated animations across components:

```javascript
const variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 }
}

<motion.div variants={variants} animate="visible" />
```

### AnimatePresence

AnimatePresence enables exit animations:

```javascript
<AnimatePresence>
  {show && <motion.div exit={{ opacity: 0 }} />}
</AnimatePresence>
```

### Layout Animations

Layout prop creates smooth transitions between layout states:

```javascript
<motion.div layout />
```

## Framework-Specific Installation

**React**:
```bash
npm install motion
```
```javascript
import { motion } from "motion/react"
```

**JavaScript**:
```bash
npm install motion
```
```javascript
import { animate } from "motion"
```

**Vue**:
```bash
npm install motion-v
```
```javascript
import { motion } from "motion-v"
```

## Documentation Navigation

All documentation files are markdown-formatted and contain:
- Code examples with explanations
- API references for components and hooks
- Common patterns and best practices
- Links to related topics

Read reference files as needed based on the user's question. The documentation is comprehensive but concise - each file focuses on a specific topic.

## Version Information

This documentation covers Motion v12+ (the latest major version as of December 2025, which unified Framer Motion under the "Motion" brand). For legacy Framer Motion questions, the concepts remain the same but import paths may differ.

## Support Resources

While this skill provides complete API documentation, users can also:
- Browse examples at motion.dev/examples
- Check GitHub issues for common problems
- Reference Motion Studio for visual animation editing
- Access Motion+ for premium components and advanced examples
