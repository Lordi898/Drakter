# Tree Component Props

All props accepted by the `<Tree>` component.

## Data Options

| Prop | Type | Description |
|------|------|-------------|
| `data` | `readonly T[]` | Controlled data prop. Tree becomes controlled — handle all mutations via callbacks. |
| `initialData` | `readonly T[]` | Uncontrolled data prop. Tree manages state internally. |

## Data Handlers (for controlled trees)

| Prop | Type | Description |
|------|------|-------------|
| `onCreate` | `handlers.CreateHandler<T>` | Called when a new node is created. |
| `onMove` | `handlers.MoveHandler<T>` | Called when nodes are moved via drag-and-drop. |
| `onRename` | `handlers.RenameHandler<T>` | Called when a node is renamed inline. |
| `onDelete` | `handlers.DeleteHandler<T>` | Called when nodes are deleted. |

## Renderers

| Prop | Type | Description |
|------|------|-------------|
| `children` | `ElementType<NodeRendererProps<T>>` | Custom node renderer. Passed as `<Tree>{MyNode}</Tree>` |
| `renderRow` | `ElementType<RowRendererProps<T>>` | Custom row renderer (wraps each node row). |
| `renderDragPreview` | `ElementType<DragPreviewProps>` | Custom drag ghost element. |
| `renderCursor` | `ElementType<CursorProps>` | Custom drop cursor indicator. |
| `renderContainer` | `ElementType<{}>` | Custom outer container. |

## Sizes

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `width` | `number \| string` | — | Tree width |
| `height` | `number` | — | Tree height (required for virtualization) |
| `rowHeight` | `number` | — | Height of each row |
| `indent` | `number` | — | Indentation per level in pixels |
| `overscanCount` | `number` | — | Extra rows rendered outside viewport |
| `paddingTop` | `number` | — | Top padding inside the list |
| `paddingBottom` | `number` | — | Bottom padding inside the list |
| `padding` | `number` | — | Sets both paddingTop and paddingBottom |

## Configuration

| Prop | Type | Description |
|------|------|-------------|
| `childrenAccessor` | `string \| ((d: T) => T[] \| null)` | Property name or function to get children array. |
| `idAccessor` | `string \| ((d: T) => string)` | Property name or function to get node id. |
| `openByDefault` | `boolean` | Whether internal nodes start open. |
| `selectionFollowsFocus` | `boolean` | Select node when it receives focus. |
| `disableMultiSelection` | `boolean` | Prevent shift/cmd-click multi-select. |
| `disableEdit` | `string \| boolean \| BoolFunc<T>` | Disable inline editing on specific/all nodes. |
| `disableDrag` | `string \| boolean \| BoolFunc<T>` | Disable dragging on specific/all nodes. |
| `disableDrop` | `string \| boolean \| ((args) => boolean)` | Disable dropping on specific nodes. Args: `{ parentNode, dragNodes, index }` |

## Event Handlers

| Prop | Type | Description |
|------|------|-------------|
| `onActivate` | `(node: NodeApi<T>) => void` | Fires when node is activated (Enter or double-click). |
| `onSelect` | `(nodes: NodeApi<T>[]) => void` | Fires when selection changes. |
| `onScroll` | `(props: ListOnScrollProps) => void` | Fires on scroll. |
| `onToggle` | `(id: string) => void` | Fires when a node is toggled open/closed. |
| `onFocus` | `(node: NodeApi<T>) => void` | Fires when focus changes. |

## Selection & State

| Prop | Type | Description |
|------|------|-------------|
| `selection` | `string` | Id of the selected node. Changes sync selection + scroll. |
| `initialOpenState` | `OpenMap` | Initial open/closed state for specific nodes. |

## Search / Filtering

| Prop | Type | Description |
|------|------|-------------|
| `searchTerm` | `string` | Filter nodes by this term. Parents of matches stay visible. |
| `searchMatch` | `(node: NodeApi<T>, term: string) => boolean` | Custom match function. Default: case-insensitive name match. |

## Extra

| Prop | Type | Description |
|------|------|-------------|
| `className` | `string` | Class name for outer container. |
| `rowClassName` | `string` | Class name for each row. |
| `ref` | `Ref<TreeApi>` | Access the Tree API instance. |
| `dndRootElement` | `globalThis.Node` | Root element for drag-and-drop events. |
| `onClick` | `MouseEventHandler` | Click handler for the tree container. |
| `onContextMenu` | `MouseEventHandler` | Context menu handler. |
| `dndManager` | `DragDropManager` | Custom drag-and-drop manager. |
