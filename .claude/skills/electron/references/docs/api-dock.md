# Source: https://www.electronjs.org/docs/latest/api/dock

On this page

## Class: Dock[â](#class-dock "Direct link to Class: Dock")

> Control your app in the macOS dock

Process: [Main](/docs/latest/glossary#main-process)
*This class is not exported from the `'electron'` module. It is only available as a return value of other methods in the Electron API.*

tip

See also: [A detailed guide about how to implement Dock menus](/docs/latest/tutorial/macos-dock).

### Instance Methods[â](#instance-methods "Direct link to Instance Methods")

#### `dock.bounce([type])` *macOS*[â](#dockbouncetype-macos "Direct link to dockbouncetype-macos")

* `type` string (optional) - Can be `critical` or `informational`. The default is
`informational`

Returns `Integer` - an ID representing the request.

When `critical` is passed, the dock icon will bounce until either the
application becomes active or the request is canceled.

When `informational` is passed, the dock icon will bounce for one second.
However, the request remains active until either the application becomes active
or the request is canceled.

note

This method can only be used while the app is not focused; when the app is focused it will return -1.

#### `dock.cancelBounce(id)` *macOS*[â](#dockcancelbounceid-macos "Direct link to dockcancelbounceid-macos")

* `id` Integer

Cancel the bounce of `id`.

#### `dock.downloadFinished(filePath)` *macOS*[â](#dockdownloadfinishedfilepath-macos "Direct link to dockdownloadfinishedfilepath-macos")

* `filePath` string

Bounces the Downloads stack if the filePath is inside the Downloads folder.

#### `dock.setBadge(text)` *macOS*[â](#docksetbadgetext-macos "Direct link to docksetbadgetext-macos")

* `text` string

Sets the string to be displayed in the dockâs badging area.

info

You need to ensure that your application has the permission to display notifications for this method to work.

#### `dock.getBadge()` *macOS*[â](#dockgetbadge-macos "Direct link to dockgetbadge-macos")

Returns `string` - The badge string of the dock.

#### `dock.hide()` *macOS*[â](#dockhide-macos "Direct link to dockhide-macos")

Hides the dock icon.

#### `dock.show()` *macOS*[â](#dockshow-macos "Direct link to dockshow-macos")

Returns `Promise<void>` - Resolves when the dock icon is shown.

#### `dock.isVisible()` *macOS*[â](#dockisvisible-macos "Direct link to dockisvisible-macos")

Returns `boolean` - Whether the dock icon is visible.

#### `dock.setMenu(menu)` *macOS*[â](#docksetmenumenu-macos "Direct link to docksetmenumenu-macos")

* `menu` [Menu](/docs/latest/api/menu)

Sets the application's [dock menu](https://developer.apple.com/design/human-interface-guidelines/dock-menus).

#### `dock.getMenu()` *macOS*[â](#dockgetmenu-macos "Direct link to dockgetmenu-macos")

Returns `Menu | null` - The application's [dock menu](https://developer.apple.com/design/human-interface-guidelines/dock-menus).

#### `dock.setIcon(image)` *macOS*[â](#dockseticonimage-macos "Direct link to dockseticonimage-macos")

* `image` ([NativeImage](/docs/latest/api/native-image) | string)

Sets the `image` associated with this dock icon.

* [Class: Dock](#class-dock)
+ [Instance Methods](#instance-methods)
- [`bounce`](#dockbouncetype-macos)- [`cancelBounce`](#dockcancelbounceid-macos)- [`downloadFinished`](#dockdownloadfinishedfilepath-macos)- [`setBadge`](#docksetbadgetext-macos)- [`getBadge`](#dockgetbadge-macos)- [`hide`](#dockhide-macos)- [`show`](#dockshow-macos)- [`isVisible`](#dockisvisible-macos)- [`setMenu`](#docksetmenumenu-macos)- [`getMenu`](#dockgetmenu-macos)- [`setIcon`](#dockseticonimage-macos)