# Tree API Reference

Access via a ref: `const treeRef = useRef(); <Tree ref={treeRef} />`. Stable across re-renders.

## Node Accessors

| Accessor | Returns | Description |
|----------|---------|-------------|
| `tree.get(id)` | `NodeApi \| null` | Get visible node by id. |
| `tree.at(index)` | `NodeApi \| null` | Get visible node by index. |
| `tree.visibleNodes` | `NodeApi[]` | Array of all currently visible nodes. |
| `tree.firstNode` | `NodeApi \| null` | First visible node. |
| `tree.lastNode` | `NodeApi \| null` | Last visible node. |
| `tree.focusedNode` | `NodeApi \| null` | Currently focused node. |
| `tree.mostRecentNode` | `NodeApi \| null` | Most recently selected node. |
| `tree.nextNode` | `NodeApi \| null` | Node after focusedNode. |
| `tree.prevNode` | `NodeApi \| null` | Node before focusedNode. |

## Focus Methods

| Method | Returns | Description |
|--------|---------|-------------|
| `tree.hasFocus` | `boolean` | True if tree has focus. |
| `tree.focus(id)` | — | Focus node by id. |
| `tree.isFocused(id)` | `boolean` | Check if node is focused. |
| `tree.pageUp()` | — | Move focus up one page. |
| `tree.pageDown()` | — | Move focus down one page. |

## Selection Methods

| Method/Prop | Returns | Description |
|-------------|---------|-------------|
| `tree.selectedIds` | `Set<string>` | Set of selected node ids. |
| `tree.selectedNodes` | `NodeApi[]` | Array of selected nodes. |
| `tree.hasNoSelection` | `boolean` | True if nothing selected. |
| `tree.hasSingleSelection` | `boolean` | True if exactly one selection. |
| `tree.hasMultipleSelections` | `boolean` | True if multiple selections. |
| `tree.isSelected(id)` | `boolean` | Check selection by id. |
| `tree.select(id)` | — | Select only this node. |
| `tree.deselect(id)` | — | Deselect node by id. |
| `tree.selectMulti(id)` | — | Add node to selection. |
| `tree.selectContiguous(id)` | — | Range select from anchor to id. |
| `tree.deselectAll()` | — | Deselect all nodes. |
| `tree.selectAll()` | — | Select all nodes. |

## Visibility (Open/Close)

| Method | Description |
|--------|-------------|
| `tree.open(id)` | Open node by id. |
| `tree.close(id)` | Close node by id. |
| `tree.toggle(id)` | Toggle node open/closed. |
| `tree.openParents(id)` | Open all parents of node. |
| `tree.openSiblings(id)` | Open all siblings of node. |
| `tree.openAll()` | Open all internal nodes. |
| `tree.closeAll()` | Close all internal nodes. |
| `tree.isOpen(id)` | Check if node is open. |

## Drag and Drop

| Method | Returns | Description |
|--------|---------|-------------|
| `tree.isDragging(id)` | `boolean` | True if node is being dragged. |
| `tree.willReceiveDrop(id)` | `boolean` | True if node is under dragged node. |

## Scrolling

| Method | Description |
|--------|-------------|
| `tree.scrollTo(id, align?)` | Scroll to node. Opens parents if needed. Align: `"auto" \| "smart" \| "center" \| "end" \| "start"`. |

## Properties

| Prop | Returns | Description |
|------|---------|-------------|
| `tree.isEditing` | `boolean` | True if a node is being edited. |
| `tree.isFiltered` | `boolean` | True if searchTerm is non-empty. |
| `tree.props` | `TreeProps` | All props passed to Tree. |
| `tree.root` | `NodeApi` | Root node. Its children are the data array nodes. |
