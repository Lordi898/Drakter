import { Check, Plus, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { DueBadge, StatusBadge } from './TaskBadges'
import type { TaskDetail, TaskNode } from './types'

export interface SubtasksTabProps {
  readonly detail: TaskDetail
  readonly onAdd: (parent: { id: string; title: string }) => void
  readonly onToggle: (node: TaskNode) => void
  readonly onOpen: (id: string) => void
}

export function SubtasksTab({ detail, onAdd, onToggle, onOpen }: SubtasksTabProps) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">
          {detail.subtasks.length === 0
            ? 'Esta tarea no tiene subtareas.'
            : `${detail.completed_subtask_count} de ${detail.subtask_count} completadas.`}
        </p>
        <Button size="sm" variant="outline" onClick={() => onAdd({ id: detail.id, title: detail.title })}>
          <Plus aria-hidden="true" />
          Añadir subtarea
        </Button>
      </div>
      {detail.subtasks.length > 0 ? (
        <ul role="tree" aria-label="Subtareas" className="flex flex-col">
          {detail.subtasks.map((node) => (
            <SubtaskItem key={node.id} node={node} level={0} onAdd={onAdd} onToggle={onToggle} onOpen={onOpen} />
          ))}
        </ul>
      ) : null}
    </div>
  )
}

interface ItemProps {
  readonly node: TaskNode
  readonly level: number
  readonly onAdd: SubtasksTabProps['onAdd']
  readonly onToggle: SubtasksTabProps['onToggle']
  readonly onOpen: SubtasksTabProps['onOpen']
}

function SubtaskItem({ node, level, onAdd, onToggle, onOpen }: ItemProps) {
  const done = node.status === 'completed'
  return (
    <li role="treeitem" aria-level={level + 1} aria-selected={false} aria-expanded={node.children.length > 0 ? true : undefined}>
      <div
        className="flex items-center gap-2 border-b py-2"
        style={{ paddingInlineStart: `${level * 20}px` }}
      >
        <Button
          variant="outline"
          size="icon-xs"
          disabled={node.status === 'cancelled'}
          aria-label={done ? `Reabrir «${node.title}»` : `Completar «${node.title}»`}
          onClick={() => onToggle(node)}
        >
          {done ? <RotateCcw aria-hidden="true" /> : <Check aria-hidden="true" />}
        </Button>
        <button
          type="button"
          onClick={() => onOpen(node.id)}
          className={cn('min-w-0 flex-1 truncate rounded-sm text-left text-sm', done && 'text-muted-foreground line-through')}
        >
          {node.title}
        </button>
        <DueBadge task={node} />
        <StatusBadge status={node.status} />
        <Button
          variant="ghost"
          size="icon-xs"
          aria-label={`Añadir subtarea dentro de «${node.title}»`}
          onClick={() => onAdd({ id: node.id, title: node.title })}
        >
          <Plus aria-hidden="true" />
        </Button>
      </div>
      {node.children.length > 0 ? (
        <ul role="group">
          {node.children.map((child) => (
            <SubtaskItem key={child.id} node={child} level={level + 1} onAdd={onAdd} onToggle={onToggle} onOpen={onOpen} />
          ))}
        </ul>
      ) : null}
    </li>
  )
}
