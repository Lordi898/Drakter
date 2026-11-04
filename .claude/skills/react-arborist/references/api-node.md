# Node API Reference

Access via the `node` prop in a `NodeRenderer`, or via `tree.get(id)`.

## State Properties (booleans)

| Property | Description |
|----------|-------------|
| `node.isRoot` | True if this is the internal root node (not shown in UI). |
| `node.isLeaf` | True if no children array exists. |
| `node.isInternal` | True if children is an array. |
| `node.isOpen` | True if internal and open. |
| `node.isEditing` | True if currently being renamed. Use in NodeRenderer to show edit form. |
| `node.isSelected` | True if selected. |
| `node.isSelectedStart` | True if first of a contiguous selected group (for styling). |
| `node.isSelectedEnd` | True if last of a contiguous selected group (for styling). |
| `node.isOnlySelection` | True if this is the only selected node. |
| `node.isFocused` | True if focused. |
| `node.isDragging` | True if being dragged. |
| `node.willReceiveDrop` | True if internal and a dragged node hovers over it. |
| `node.state` | Object with all above as keys. Useful with clsx/classnames. |

```ts
type NodeState = {
  isEditing: boolean;
  isDragging: boolean;
  isSelected: boolean;
  isSelectedStart: boolean;
  isSelectedEnd: boolean;
  isFocused: boolean;
  isOpen: boolean;
  isClosed: boolean;
  isLeaf: boolean;
  isInternal: boolean;
  willReceiveDrop: boolean;
};
```

## Accessors

| Accessor | Returns | Description |
|----------|---------|-------------|
| `node.childIndex` | `number` | Index among siblings. |
| `node.next` | `NodeApi \| null` | Next visible node (below in tree). |
| `node.prev` | `NodeApi \| null` | Previous visible node (above in tree). |
| `node.nextSibling` | `NodeApi \| null` | Next sibling in data. |

## Data Access

| Accessor | Description |
|----------|-------------|
| `node.id` | The node's unique id. |
| `node.data` | The original data object for this node. |
| `node.level` | Depth level in the tree (0-based). |
| `node.parent` | Parent NodeApi or null. |
| `node.children` | Array of child NodeApi or null for leaves. |

## Selection Methods

| Method | Description |
|--------|-------------|
| `node.select()` | Select only this node. |
| `node.deselect()` | Deselect this node (others may remain selected). |
| `node.selectMulti()` | Select this node while keeping other selections. |
| `node.selectContiguous()` | Range-select from anchor to this node. |

## Activation Methods

| Method | Description |
|--------|-------------|
| `node.activate()` | Triggers the `onActivate` callback. |
| `node.focus()` | Focus this node. |

## Open/Close Methods

| Method | Description |
|--------|-------------|
| `node.open()` | Open this internal node. |
| `node.close()` | Close this internal node. |
| `node.toggle()` | Toggle open/closed state. |
| `node.openParents()` | Open all ancestor nodes. |

## Editing Methods

| Method | Description |
|--------|-------------|
| `node.edit()` | Enter editing state (`isEditing` becomes true). |
| `node.submit(newName)` | Submit new name via `onRename` handler, exits editing. |
| `node.reset()` | Exit editing without submitting. |

## Event Handling

| Method | Description |
|--------|-------------|
| `node.handleClick(event)` | Standard click handler: meta→multiSelect, shift→contiguous, else→select+activate. |
