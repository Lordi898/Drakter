---
name: react-arborist
description: React tree view component with drag-and-drop, virtualization, inline editing, and filtering. Use when building tree views, file explorers, sidebar navigation, folder browsers, hierarchical data displays, layer panels (like Figma/Sketch), or any UI that renders nested/tree-like data structures in React. Triggers on react-arborist, Tree component, node rendering, tree DnD, and tree API usage.
---

# React Arborist

Tree view component for React. Provides behavior (virtualization, DnD, selection, editing, filtering) with styling left to the developer.

**Version**: 3.4.3 | **Peer deps**: React >= 16.14, React DOM >= 16.14

```
npm install react-arborist
```

## Data Shape

Tree data is an array of node objects with `id`, `name`, and optional `children`:

```js
const data = [
  { id: "1", name: "Unread" },
  { id: "2", name: "Threads" },
  {
    id: "3", name: "Chat Rooms",
    children: [
      { id: "c1", name: "General" },
      { id: "c2", name: "Random" },
    ],
  },
];
```

Custom property names via `idAccessor` and `childrenAccessor` props.

## Two Modes

### Uncontrolled (use `initialData`)

Tree manages all state internally. Simplest setup:

```jsx
<Tree initialData={data} />
```

### Controlled (use `data`)

You own the state. Must provide handler callbacks for all mutations:

```jsx
<Tree
  data={data}
  onCreate={({ parentId, index, type }) => {}}
  onRename={({ id, name }) => {}}
  onMove={({ dragIds, parentId, index }) => {}}
  onDelete={({ ids }) => {}}
/>
```

## Custom Node Rendering

The most common task. Pass a component as the `children` of `<Tree>`:

```jsx
<Tree initialData={data} width={600} height={1000} indent={24} rowHeight={36}>
  {Node}
</Tree>

function Node({ node, style, dragHandle }) {
  return (
    <div style={style} ref={dragHandle}>
      {node.isLeaf ? "📄" : node.isOpen ? "📂" : "📁"}
      {node.isEditing ? (
        <input
          autoFocus
          defaultValue={node.data.name}
          onBlur={() => node.submit(node.data.name)}
          onKeyDown={(e) => {
            if (e.key === "Enter") node.submit(e.currentTarget.value);
            if (e.key === "Escape") node.reset();
          }}
        />
      ) : (
        <span onClick={() => node.handleClick()}>{node.data.name}</span>
      )}
    </div>
  );
}
```

Key `NodeRendererProps`: `style` (indent padding), `node` (NodeApi), `tree` (TreeApi), `dragHandle` (ref for drag).

## Selection Sync

Pass an id to `selection` prop — tree auto-selects and scrolls when it changes:

```jsx
const chatId = useCurrentChatId();
<Tree initialData={data} selection={chatId} />;
```

## Tree API via Ref

Access imperative methods through a ref:

```jsx
const treeRef = useRef();
<Tree initialData={data} ref={treeRef} />;

treeRef.current.selectAll();
treeRef.current.scrollTo("node-id", "center");
treeRef.current.openAll();
```

## Filtering

```jsx
<Tree data={data} searchTerm={term} searchMatch={(node, t) =>
  node.data.name.toLowerCase().includes(t.toLowerCase())
} />
```

## Dynamic Sizing

```jsx
const { ref, width, height } = useResizeObserver();
<div ref={ref}><Tree height={height} width={width} data={data} /></div>
```

## Reference Files

Read these when detailed API info is needed:

- **references/api-tree-props.md** — Complete props table for the `<Tree>` component
- **references/api-node.md** — NodeApi: state booleans, methods, editing, selection
- **references/api-tree.md** — TreeApi (via ref): accessors, selection, visibility, scrolling
- **references/api-renderers.md** — Custom renderer prop types (Node, Row, DragPreview, Cursor)
- **references/api-handlers.md** — Callback signatures (onCreate, onMove, onRename, onDelete)
- **references/examples.md** — 8 working code patterns
