# Renderer Props

## Node Renderer (`children`)

The primary renderer. Passed as `<Tree>{MyNode}</Tree>`. Responsible for drag handle, indentation style, visual appearance, and edit state.

```ts
type NodeRendererProps<T> = {
  style: CSSProperties;     // Includes indent padding
  node: NodeApi<T>;         // Node API for state/data/methods
  tree: TreeApi<T>;         // Tree API for global operations
  dragHandle?: (el: HTMLDivElement | null) => void;  // Attach to draggable element
  preview?: boolean;        // True when rendering drag preview
};
```

**Typical pattern:**

```tsx
function Node({ node, style, dragHandle }) {
  return (
    <div style={style} ref={dragHandle}>
      <span onClick={(e) => node.handleClick(e)}>
        {node.isLeaf ? "📄" : node.isOpen ? "📂" : "📁"}
      </span>
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
        <span>{node.data.name}</span>
      )}
    </div>
  );
}
```

## Row Renderer (`renderRow`)

Wraps each node row. Responsible for drop ref, positioning, and ARIA attributes.

```ts
type RowRendererProps<T> = {
  node: NodeApi<T>;
  innerRef: (el: HTMLDivElement | null) => void;  // Drop target ref
  attrs: HTMLAttributes<any>;                      // ARIA attributes
  children: ReactElement;                          // The node renderer output
};
```

## Drag Preview Renderer (`renderDragPreview`)

Shows the "ghost" following the cursor during drag.

```ts
type DragPreviewProps = {
  offset: XYCoord | null;   // Mouse offset from drag start
  mouse: XYCoord | null;    // Current mouse position
  id: string | null;        // Primary dragged node id
  dragIds: string[];        // All dragged node ids (multi-select)
  isDragging: boolean;      // Whether drag is active
};
```

## Cursor Renderer (`renderCursor`)

The line showing where a drop will land.

```ts
type CursorProps = {
  top: number;    // Y position in pixels
  left: number;   // X position in pixels
  indent: number; // Indentation level for the drop position
};
```
