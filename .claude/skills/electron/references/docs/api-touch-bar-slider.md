# Source: https://www.electronjs.org/docs/latest/api/touch-bar-slider

On this page

## Class: TouchBarSlider[â](#class-touchbarslider "Direct link to Class: TouchBarSlider")

> Create a slider in the touch bar for native macOS applications

Process: [Main](/docs/latest/glossary#main-process)
*This class is not exported from the `'electron'` module. It is only available as a return value of other methods in the Electron API.*

### `new TouchBarSlider(options)`[â](#new-touchbarslideroptions "Direct link to new-touchbarslideroptions")

* `options` Object
+ `label` string (optional) - Label text.
+ `value` Integer (optional) - Selected value.
+ `minValue` Integer (optional) - Minimum value.
+ `maxValue` Integer (optional) - Maximum value.
+ `change` Function (optional) - Function to call when the slider is changed.
- `newValue` number - The value that the user selected on the Slider.

### Instance Properties[â](#instance-properties "Direct link to Instance Properties")

The following properties are available on instances of `TouchBarSlider`:

#### `touchBarSlider.label`[â](#touchbarsliderlabel "Direct link to touchbarsliderlabel")

A `string` representing the slider's current text. Changing this value immediately updates the slider
in the touch bar.

#### `touchBarSlider.value`[â](#touchbarslidervalue "Direct link to touchbarslidervalue")

A `number` representing the slider's current value. Changing this value immediately updates the slider
in the touch bar.

#### `touchBarSlider.minValue`[â](#touchbarsliderminvalue "Direct link to touchbarsliderminvalue")

A `number` representing the slider's current minimum value. Changing this value immediately updates the
slider in the touch bar.

#### `touchBarSlider.maxValue`[â](#touchbarslidermaxvalue "Direct link to touchbarslidermaxvalue")

A `number` representing the slider's current maximum value. Changing this value immediately updates the
slider in the touch bar.

* [Class: TouchBarSlider](#class-touchbarslider)
+ [`new TouchBarSlider(options)`](#new-touchbarslideroptions)+ [Instance Properties](#instance-properties)
- [`label`](#touchbarsliderlabel)- [`value`](#touchbarslidervalue)- [`minValue`](#touchbarsliderminvalue)- [`maxValue`](#touchbarslidermaxvalue)