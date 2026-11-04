Reset – Radix Themes

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[Radix Homepage](/)[Made by WorkOS](https://workos.com)

[ThemesThemes](/)[PrimitivesPrimitives](/primitives)[IconsIcons](/icons)[ColorsColors](/colors)

[Documentation](/themes/docs/overview/getting-started)[Playground](/themes/playground)[Blog](/blog)

#### Overview

[Getting started](/themes/docs/overview/getting-started)[Styling](/themes/docs/overview/styling)[Layout](/themes/docs/overview/layout)[Releases](/themes/docs/overview/releases)[Resources](/themes/docs/overview/resources)

#### Theme

[Overview](/themes/docs/theme/overview)[Color](/themes/docs/theme/color)[Dark mode](/themes/docs/theme/dark-mode)[Typography](/themes/docs/theme/typography)[Spacing](/themes/docs/theme/spacing)[Breakpoints](/themes/docs/theme/breakpoints)[Radius](/themes/docs/theme/radius)[Shadows](/themes/docs/theme/shadows)[Cursors](/themes/docs/theme/cursors)

#### Layout

[Box](/themes/docs/components/box)[Flex](/themes/docs/components/flex)[Grid](/themes/docs/components/grid)[Container](/themes/docs/components/container)[Section](/themes/docs/components/section)

#### Typography

[Text](/themes/docs/components/text)[Heading](/themes/docs/components/heading)[Blockquote](/themes/docs/components/blockquote)[Code](/themes/docs/components/code)[Em](/themes/docs/components/em)[Kbd](/themes/docs/components/kbd)[Link](/themes/docs/components/link)[Quote](/themes/docs/components/quote)[Strong](/themes/docs/components/strong)

#### Components

[Alert Dialog](/themes/docs/components/alert-dialog)[Aspect Ratio](/themes/docs/components/aspect-ratio)[Avatar](/themes/docs/components/avatar)[Badge](/themes/docs/components/badge)[Button](/themes/docs/components/button)[Callout](/themes/docs/components/callout)[Card](/themes/docs/components/card)[Checkbox](/themes/docs/components/checkbox)[Checkbox Group](/themes/docs/components/checkbox-group)[Checkbox Cards](/themes/docs/components/checkbox-cards)[Context Menu](/themes/docs/components/context-menu)[Data List](/themes/docs/components/data-list)[Dialog](/themes/docs/components/dialog)[Dropdown Menu](/themes/docs/components/dropdown-menu)[Hover Card](/themes/docs/components/hover-card)[Icon Button](/themes/docs/components/icon-button)[Inset](/themes/docs/components/inset)[Popover](/themes/docs/components/popover)[Progress](/themes/docs/components/progress)[Radio](/themes/docs/components/radio)[Radio Group](/themes/docs/components/radio-group)[Radio Cards](/themes/docs/components/radio-cards)[Scroll Area](/themes/docs/components/scroll-area)[Segmented Control](/themes/docs/components/segmented-control)[Select](/themes/docs/components/select)[Separator](/themes/docs/components/separator)[Skeleton](/themes/docs/components/skeleton)[Slider](/themes/docs/components/slider)[Spinner](/themes/docs/components/spinner)[Switch](/themes/docs/components/switch)[Table](/themes/docs/components/table)[Tabs](/themes/docs/components/tabs)[Tab Nav](/themes/docs/components/tab-nav)[Text Area](/themes/docs/components/text-area)[Text Field](/themes/docs/components/text-field)[Tooltip](/themes/docs/components/tooltip)

#### Utilities

[Accessible Icon](/themes/docs/components/accessible-icon)[Portal](/themes/docs/components/portal)[Reset](/themes/docs/components/reset)[Slot](/themes/docs/components/slot)[Theme](/themes/docs/components/theme)[Visually Hidden](/themes/docs/components/visually-hidden)

Components

# Reset

Removes default browser styles from any component.

[View source](https://github.com/radix-ui/themes/blob/main/packages/radix-ui-themes/src/components/reset.tsx)[Report an issue](https://github.com/radix-ui/themes/issues/new?title=[Reset] Issue)

## [API Reference](#api-reference)

Reset component is used to aggressively reset browser styles on a specific element.

It renders a [Slot primitive](/primitives/docs/utilities/slot) that:

* Accepts a single React element as its child
* Removes opinionated browser styles
* Sets idiomatic layout defaults, like `display: block` for images or `width: stretch` for inputs
* Sets the [cursor](/themes/docs/theme/cursors) style according to your theme settings
* Adds `box-sizing: border-box`

## [Examples](#examples)

### [Anchor](#anchor)

[Anchor](#)

```
<Reset>



<a href="#">Anchor</a>



</Reset>
```

### [Abbreviation](#abbreviation)

ABR

```
<Reset>



<abbr title="Abbreviation">ABR</abbr>



</Reset>
```

### [Address](#address)

Address

```
<Reset>



<address>Address</address>



</Reset>
```

### [Article](#article)

Article

```
<Reset>



<article>Article</article>



</Reset>
```

### [Aside](#aside)

Aside content

```
<Reset>



<aside>Aside content</aside>



</Reset>
```

### [Bold](#bold)

**Bold text**

```
<Reset>



<b>Bold text</b>



</Reset>
```

### [Bi-directional isolation](#bi-directional-isolation)

Bi-directional isolation

```
<Reset>



<bdi>Bi-directional isolation</bdi>



</Reset>
```

### [Bi-directional override](#bi-directional-override)

Bi-directional override

```
<Reset>



<bdo>Bi-directional override</bdo>



</Reset>
```

### [Block quote](#block-quote)

> Block quote

```
<Reset>



<blockquote>Block quote</blockquote>



</Reset>
```

### [Button](#button)

Button

```
<Reset>



<button>Button</button>



</Reset>
```

### [Citation](#citation)

Citation

```
<Reset>



<cite>Citation</cite>



</Reset>
```

### [Code](#code)

`Computer code`

```
<Reset>



<code>Computer code</code>



</Reset>
```

### [Data](#data)

Machine-readable equivalent

```
<Reset>



<data>Machine-readable equivalent</data>



</Reset>
```

### [Deleted text](#deleted-text)

~~Deleted text~~

```
<Reset>



<del>Deleted text</del>



</Reset>
```

### [Details](#details)

Summary for a details elementAdditional details

```
<Reset>



<details>



<summary>Summary for a details element</summary>



Additional details



</details>



</Reset>
```

### [Definition](#definition)

Definition

```
<Reset>



<dfn>Definition</dfn>



</Reset>
```

### [Div](#div)

Div

```
<Reset>



<div>Div</div>



</Reset>
```

### [Emphasized text](#emphasized-text)

*Emphasized text*

```
<Reset>



<em>Emphasized text</em>



</Reset>
```

### [Fieldset](#fieldset)

Fieldset

```
<Reset>



<fieldset>Fieldset</fieldset>



</Reset>
```

### [Figure](#figure)

Figure

```
<Reset>



<figure>Figure</figure>



</Reset>
```

### [Figure caption](#figure-caption)

Figure caption

```
<Reset>



<figcaption>Figure caption</figcaption>



</Reset>
```

### [Footer](#footer)

Footer

```
<Reset>



<footer>Footer</footer>



</Reset>
```

### [Form](#form)

Form

```
<Reset>



<form>Form</form>



</Reset>
```

### [Heading](#heading)

# Heading

```
<Reset>



<h1>Heading</h1>



</Reset>
```

### [Header](#header)

Header

```
<Reset>



<header>Header</header>



</Reset>
```

### [Italic text](#italic-text)

*Italic text*

```
<Reset>



<i>Italic text</i>



</Reset>
```

### [Inline frame](#inline-frame)

When reset, `<iframe>` elements get `display: block` and `width: stretch`.

```
<Reset>



<iframe src="https://example.com" />



</Reset>
```

### [Image](#image)

When reset, `<img>` elements get `display: block` and `max-width: 100%`.

![](https://images.unsplash.com/photo-1556825578-5813abf36e34?q=80&w=3864&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D)

```
<Reset>



<img src="https://images.unsplash.com/photo-1556825578-5813abf36e34?q=80&w=3864&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D" />



</Reset>
```

### [Input](#input)

When reset, textual `<input>` types get `display: block` and `width: stretch`.

```
<Reset>



<input placeholder="Input control" />



</Reset>
```

### [Inserted text](#inserted-text)

Inserted text

```
<Reset>



<ins>Inserted text</ins>



</Reset>
```

### [Keyboard input](#keyboard-input)

`Keyboard input`

```
<Reset>



<kbd>Keyboard input</kbd>



</Reset>
```

### [Label](#label)

Label

```
<Reset>



<label>Label</label>



</Reset>
```

### [Legend](#legend)

Legend

```
<Reset>



<legend>Legend</legend>



</Reset>
```

### [List item](#list-item)

- List item

```
<Reset>



<li>List item</li>



</Reset>
```

### [Main](#main)

Main

```
<Reset>



<main>Main</main>



</Reset>
```

### [Marked text](#marked-text)

Marked text

```
<Reset>



<mark>Marked text</mark>



</Reset>
```

### [Navigation](#navigation)

Navigation

```
<Reset>



<nav>Navigation</nav>



</Reset>
```

### [Ordered list](#ordered-list)

1. Coffee
2. Tea
3. Milk

```
<Reset>



<ol>



<li>Coffee</li>



<li>Tea</li>



<li>Milk</li>



</ol>



</Reset>
```

### [Output](#output)

Output

```
<Reset>



<output>Output</output>



</Reset>
```

### [Paragraph](#paragraph)

Paragraph

```
<Reset>



<p>Paragraph</p>



</Reset>
```

### [Preformatted text](#preformatted-text)

```
Preformatted text: "    "
```

```
<Reset>



<pre>{'Preformatted text: "    "'}</pre>



</Reset>
```

### [Quote](#quote)

"Quote"

```
<Reset>



<q>Quote</q>



</Reset>
```

### [Strikethrough text](#strikethrough-text)

~~Strikethrough text~~

```
<Reset>



<s>Strikethrough text</s>



</Reset>
```

### [Sample output](#sample-output)

`Sample output`

```
<Reset>



<samp>Sample output</samp>



</Reset>
```

### [Section](#section)

Section

```
<Reset>



<section>Section</section>



</Reset>
```

### [Select](#select)

Option 1Option 2Option 3Option 4

```
<Reset>



<select>



<option value="1">Option 1</option>



<option value="2">Option 2</option>



<option value="3">Option 3</option>



<option value="4">Option 4</option>



</select>



</Reset>
```

### [Small text](#small-text)

Small text

```
<Reset>



<small>Small text</small>



</Reset>
```

### [Span](#span)

Span

```
<Reset>



<span>Span</span>



</Reset>
```

### [Strong text](#strong-text)

**Strong text**

```
<Reset>



<strong>Strong text</strong>



</Reset>
```

### [Subscript text](#subscript-text)

Subscript text

```
<Reset>



<sub>Subscript text</sub>



</Reset>
```

### [Superscript text](#superscript-text)

Superscript text

```
<Reset>



<sup>Superscript text</sup>



</Reset>
```

### [SVG](#svg)

When reset, `<svg>` elements get `display: block`, `max-width: 100%`, and `flex-shrink: 0`.

```
<Reset>



<svg
		width="76"
		height="24"
		viewBox="0 0 76 24"
		fill="currentcolor"
		xmlns="http://www.w3.org/2000/svg"
	>



<path d="M43.9022 20.0061H46.4499C46.2647 19.0375 46.17 18.1161 46.17 17.0058V12.3753C46.17 9.25687 44.3893 7.72127 41.1943 7.72127C38.3003 7.72127 36.3324 9.23324 36.0777 11.8083H38.9254C39.0181 10.698 39.8052 9.96561 41.1017 9.96561C42.4446 9.96561 43.3243 10.6743 43.3243 12.1391V12.7061L39.8052 13.1077C37.4206 13.3912 35.5684 14.3834 35.5684 16.7931C35.5684 18.9666 37.2353 20.2659 39.5274 20.2659C41.4027 20.2659 42.9845 19.4863 43.6401 18.1161C43.6689 18.937 43.9022 20.0061 43.9022 20.0061ZM40.3377 18.1634C39.157 18.1634 38.5087 17.5727 38.5087 16.6278C38.5087 15.3757 39.4579 15.0922 40.7082 14.9268L43.3243 14.6197V15.352C43.3243 17.242 41.8658 18.1634 40.3377 18.1634ZM56.2588 20.0061H59.176V3H56.2125V9.96561C55.6569 8.76075 54.3141 7.72127 52.4851 7.72127C49.3058 7.72127 47.099 10.2963 47.099 14.0054C47.099 17.7381 49.3058 20.2896 52.4851 20.2896C54.2678 20.2896 55.68 19.2973 56.2588 18.0925V20.0061ZM56.282 14.218C56.282 16.5569 55.1938 18.0689 53.3185 18.0689C51.3969 18.0689 50.1856 16.486 50.1856 14.0054C50.1856 11.5485 51.3969 9.94198 53.3185 9.94198C55.1938 9.94198 56.282 11.454 56.282 13.7928V14.218ZM60.9066 5.97304H64.0553V3.01996H60.9066V5.97304ZM60.9992 20.0061H63.9627V8.00476H60.9992V20.0061ZM67.6638 20.0061L70.6041 15.8954L73.5212 20.0061H76.9246L72.3636 13.7219L76.5542 8.00476H73.3823L70.7661 11.7138L68.1731 8.00476H64.7697L69.0066 13.8637L64.4919 20.0061H67.6638Z" />



<path
			fillRule="evenodd"
			clipRule="evenodd"
			d="M24.9132 20V14.0168H28.7986L32.4513 20H35.7006L31.6894 13.5686C33.5045 12.986 35.0955 11.507 35.0955 9.01961C35.0955 5.7479 32.7994 4 28.9571 4H22V20H24.9132ZM24.9132 6.35294V11.6863H28.821C31.0395 11.6863 32.1599 10.7675 32.1599 9.01961C32.1599 7.27171 30.9395 6.35294 28.621 6.35294H24.9132Z"
		/>



<path d="M7 23C3.13401 23 0 19.6422 0 15.5C0 11.3578 3.13401 8 7 8V23Z" />



<path d="M7 0H0V7H7V0Z" />



<path d="M11.5 7C13.433 7 15 5.433 15 3.5C15 1.567 13.433 0 11.5 0C9.56704 0 8 1.567 8 3.5C8 5.433 9.56704 7 11.5 7Z" />



</svg>



</Reset>
```

### [Table](#table)

Table caption

| Column header | Column header |
| --- | --- |
| Row header | Cell data |
| Row header | Cell data |
|  |  |
| --- | --- |
| Row header | Cell data |

```
<Reset>



<table>



<Reset>



<caption>Table caption</caption>



</Reset>



<Reset>



<thead>



<Reset>



<tr>



<Reset>



<th scope="col">Column header</th>



</Reset>



<Reset>



<th scope="col">Column header</th>



</Reset>



</tr>



</Reset>



</thead>



</Reset>



<Reset>



<tbody>



<Reset>



<tr>



<Reset>



<th scope="row">Row header</th>



</Reset>



<Reset>



<td>Cell data</td>



</Reset>



</tr>



</Reset>



<Reset>



<tr>



<Reset>



<th scope="row">Row header</th>



</Reset>



<Reset>



<td>Cell data</td>



</Reset>



</tr>



</Reset>



</tbody>



</Reset>



<Reset>



<tfoot>



<Reset>



<tr>



<Reset>



<th scope="row">Row header</th>



</Reset>



<Reset>



<td>Cell data</td>



</Reset>



</tr>



</Reset>



</tfoot>



</Reset>



</table>



</Reset>
```

### [Text area](#text-area)

```
<Reset>



<textarea placeholder="Text area" />



</Reset>
```

### [Time](#time)

Time

```
<Reset>



<time dateTime="2021-01-01">Time</time>



</Reset>
```

### [Unarticulated annotation](#unarticulated-annotation)

Unarticulated annotation

```
<Reset>



<u>Unarticulated annotation</u>



</Reset>
```

### [Unordered list](#unordered-list)

* Coffee
* Tea
* Milk

```
<Reset>



<ul>



<li>Coffee</li>



<li>Tea</li>



<li>Milk</li>



</ul>



</Reset>
```

### [Variable](#variable)

Variable

```
<Reset>



<var>Variable</var>



</Reset>
```

#### Quick nav

Previous[Portal](/themes/docs/components/portal)

Next[Slot](/themes/docs/components/slot)

[Edit this page on GitHub.](https://github.com/radix-ui/website/edit/main/data/themes/docs/components/reset.mdx "Edit this page on GitHub.")
