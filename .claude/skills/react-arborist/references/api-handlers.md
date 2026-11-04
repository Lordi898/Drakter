# Handler Callbacks

Callbacks used in controlled mode (when `data` prop is provided instead of `initialData`).

## onCreate

```ts
type CreateHandler<T> = (args: {
  parentId: string | null;  // null when creating at root level
  index: number;            // Position among siblings
  type: "internal" | "leaf"; // What kind of node to create
}) => void;
```

## onRename

```ts
type RenameHandler<T> = (args: {
  id: string;      // Node being renamed
  name: string;    // New name value
}) => void;
```

## onMove

```ts
type MoveHandler<T> = (args: {
  dragIds: string[];        // All dragged node ids
  parentId: string | null;  // New parent (null = root)
  index: number;            // New position among siblings
}) => void;
```

## onDelete

```ts
type DeleteHandler<T> = (args: {
  ids: string[];   // All node ids to delete
}) => void;
```
