# Examples

## Minimal Uncontrolled Tree

```jsx
import { Tree } from 'react-arborist';

const data = [
  { id: "1", name: "Unread" },
  { id: "2", name: "Threads" },
  {
    id: "3",
    name: "Chat Rooms",
    children: [
      { id: "c1", name: "General" },
      { id: "c2", name: "Random" },
    ],
  },
];

function App() {
  return <Tree initialData={data} />;
}
```

## Custom Node Appearance

```jsx
function App() {
  return (
    <Tree
      initialData={data}
      openByDefault={false}
      width={600}
      height={1000}
      indent={24}
      rowHeight={36}
      overscanCount={1}
      paddingTop={30}
      paddingBottom={10}
      padding={25}
    >
      {Node}
    </Tree>
  );
}

function Node({ node, style, dragHandle }) {
  return (
    <div style={style} ref={dragHandle}>
      {node.isLeaf ? "🍁" : "🗀"}
      {node.data.name}
    </div>
  );
}
```

## Controlled Tree

```jsx
function App() {
  const onCreate = ({ parentId, index, type }) => { /* mutate data */ };
  const onRename = ({ id, name }) => { /* mutate data */ };
  const onMove = ({ dragIds, parentId, index }) => { /* mutate data */ };
  const onDelete = ({ ids }) => { /* mutate data */ };

  return (
    <Tree
      data={data}
      onCreate={onCreate}
      onRename={onRename}
      onMove={onMove}
      onDelete={onDelete}
    />
  );
}
```

## Tree Filtering

```jsx
function App() {
  const term = useSearchTermString();
  return (
    <Tree
      data={data}
      searchTerm={term}
      searchMatch={(node, term) =>
        node.data.name.toLowerCase().includes(term.toLowerCase())
      }
    />
  );
}
```

## Selection Sync

Synchronize tree selection with external state (e.g., current chat room):

```jsx
function App() {
  const chatId = useCurrentChatId();
  // When chatId changes, tree auto-selects and scrolls to that node
  return <Tree initialData={data} selection={chatId} />;
}
```

## Tree API via Ref

```jsx
function App() {
  const treeRef = useRef();

  useEffect(() => {
    const tree = treeRef.current;
    tree.selectAll();
    // Access all Tree API methods
  }, []);

  return <Tree initialData={data} ref={treeRef} />;
}
```

## Custom Data Accessors

When data uses different property names:

```jsx
const data = [
  {
    category: "Food",
    subCategories: [
      { category: "Restaurants" },
      { category: "Groceries" },
    ],
  },
];

<Tree
  data={data}
  idAccessor="category"
  childrenAccessor={(d) => d.subCategories}
/>;
```

## Custom Renderers

Replace every visual part of the tree:

```jsx
<Tree
  data={data}
  renderRow={MyRow}
  renderDragPreview={MyDragPreview}
  renderCursor={MyCursor}
>
  {MyNode}
</Tree>
```

## Dynamic Sizing

Use with `use-resize-observer` for responsive trees:

```jsx
import { useResizeObserver } from 'use-resize-observer';

function App() {
  const { ref, width, height } = useResizeObserver();

  return (
    <div className="parent" ref={ref}>
      <Tree height={height} width={width} data={data} />
    </div>
  );
}
```
