# View animations

Checking Motion+ status…

Unlocks for everyone in

14 Days 09 Hours 15 Minutes

Or

[Get Motion+ for instant access](../plus)

Already joined?

[Login](https://plus.motion.dev/login)

Checking Motion+ status…

Unlocks for everyone in

14 Days 09 Hours 15 Minutes

Or

[Get Motion+ for instant access](../plus)

Already joined?

[Login](https://plus.motion.dev/login)

Checking Motion+ status…

Unlocks for everyone in

14 Days 09 Hours 15 Minutes

Or

[Get Motion+ for instant access](../plus)

Already joined?

[Login](https://plus.motion.dev/login)

Motion's `animateView()` function makes it simple to animate between two different views or layouts.

```
// Crossfade
animateView(update).enter({ opacity: 1 })
```

View animations have a number of unique superpowers:

**Layout:** Animate discrete changes in layout, like switching `justify-content` between `"flex-start"` and `"flex-end"`.

**Shared element transitions:** Animate entirely different elements across two views. For example, this underline element moves like a single element, but each is generated entirely with CSS on the `.selected` tab.

**Page effects:** Add effects to the entire viewport, like wipes, slides and crossfades:

`animateView()` is built on the browser's native [View Transition API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API) for small filesize and great performance.

It aims to remove the complexity of, and expand upon, the View Transition API:

* Cleaner API
* Spring animations
* Interruption handling/queuing

**Important:** `animateView()` is currently in alpha, which means the API might change. It's also exclusive to [Motion+ members](../plus), who are encouraged to help us shape the API via our private Discord.

As an early access API, there are many more features to come, such as:

* Automatic `view-transition-name` management
* Enter/exit animations

Previous

[scroll](./scroll)

Next

[Easing functions](./easing-functions)