import { CircleCheck, CircleDashed, CircleMinus, CircleX, type LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '@/lib/utils'
import { navigateTo } from '@/navigation/route'
import type { SectionId } from '@/navigation/sections'
import type { Section, TodayAgendaEntry, TodayHabit, TodayProject, TodayResponse, TodayTask } from './contract'
import { DimensionLine } from './DimensionLine'
import { clockOf, overdueLabel, plural, taskTime, yearOf } from './format'

const ROW_BUTTON =
  'flex w-full items-baseline gap-4 rounded-sm px-2 py-2 text-left outline-none transition-colors hover:bg-accent/60 focus-visible:ring-[3px] focus-visible:ring-ring/50'

type NounKey = 'tasks' | 'projects' | 'agenda' | 'habits'

const UNAVAILABLE: Record<NounKey, string> = {
  tasks: 'Las tareas todavía no están disponibles.',
  projects: 'Los proyectos todavía no están disponibles.',
  agenda: 'La agenda todavía no está disponible.',
  habits: 'Los hábitos todavía no están disponibles.'
}

interface BlockProps<T> {
  readonly id: string
  readonly title: string
  readonly section: Section<T>
  readonly noun: NounKey
  readonly emptyText: string
  readonly link?: { readonly label: string; readonly to: SectionId }
  readonly children: (items: readonly T[]) => ReactNode
}

function Block<T>({ id, title, section, noun, emptyText, link, children }: BlockProps<T>) {
  const headingId = `today-${id}`
  let body: ReactNode
  if (section.status === 'unavailable') {
    body = (
      <p className="text-muted-foreground">
        {section.reason === 'failed' ? 'No se pudo leer esta parte.' : UNAVAILABLE[noun]}
      </p>
    )
  } else if (section.items.length === 0) {
    body = (
      <p className="text-muted-foreground">
        {emptyText}
        {link ? (
          <>
            {' '}
            <button
              type="button"
              onClick={() => navigateTo(link.to)}
              className="rounded-sm text-foreground underline underline-offset-4 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
            >
              {link.label}
            </button>
          </>
        ) : null}
      </p>
    )
  } else {
    body = (
      <>
        {children(section.items)}
        {section.truncated ? (
          <p className="mt-2 px-2 text-sm text-muted-foreground">
            Mostrando {section.items.length} de {section.total}.
          </p>
        ) : null}
      </>
    )
  }
  return (
    <section aria-labelledby={headingId}>
      <h2 id={headingId} className="mb-3 border-b border-plan-line/50 pb-2 text-lg font-semibold text-foreground">
        {title}
      </h2>
      {body}
    </section>
  )
}

function Title({ text, className }: { readonly text: string; readonly className?: string }) {
  return (
    <span className={cn('block min-w-0 truncate', className)} title={text}>
      {text}
    </span>
  )
}

function TaskMain({ task }: { readonly task: TodayTask }) {
  return (
    <span className="min-w-0 flex-1">
      <Title text={task.title} />
      {task.project_name ? <Title text={task.project_name} className="text-sm text-muted-foreground" /> : null}
    </span>
  )
}

function OverdueList({ tasks, timeZone }: { readonly tasks: readonly TodayTask[]; readonly timeZone: string }) {
  return (
    <ul>
      {tasks.map((task) => (
        <li key={task.id} className="border-l border-destructive">
          <button type="button" onClick={() => navigateTo('tasks')} className={ROW_BUTTON}>
            <TaskMain task={task} />
            <span className="shrink-0 text-sm text-destructive">{overdueLabel(task, timeZone)}</span>
          </button>
        </li>
      ))}
    </ul>
  )
}

function priorityText(task: TodayTask): string | null {
  if (task.priority === 'urgent') return 'Urgente'
  if (task.priority === 'high') return 'Alta'
  return null
}

function DueTodayList({ tasks, timeZone }: { readonly tasks: readonly TodayTask[]; readonly timeZone: string }) {
  return (
    <ul>
      {tasks.map((task) => {
        const time = taskTime(task, timeZone)
        const priority = priorityText(task)
        return (
          <li key={task.id}>
            <button type="button" onClick={() => navigateTo('tasks')} className={ROW_BUTTON}>
              <TaskMain task={task} />
              <span className="flex shrink-0 gap-3 text-sm text-muted-foreground">
                {task.status === 'on_hold' ? <span>En pausa</span> : null}
                {priority ? <span className="font-medium text-foreground">{priority}</span> : null}
                {time ? <span className="tabular-nums">{time}</span> : null}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

function ProjectList({
  projects,
  currentYear
}: {
  readonly projects: readonly TodayProject[]
  readonly currentYear: number | null
}) {
  return (
    <ul>
      {projects.map((project) => (
        <li key={project.id}>
          <button
            type="button"
            onClick={() => navigateTo('projects')}
            className={cn(ROW_BUTTON, 'flex-col items-stretch gap-1')}
          >
            <span className="flex items-baseline justify-between gap-4">
              <Title text={project.name} className="flex-1" />
              <span className="shrink-0 text-sm text-muted-foreground">
                {project.open_tasks} {plural(project.open_tasks, 'abierta', 'abiertas')}
                {project.overdue_tasks > 0 ? (
                  <span className="text-destructive">
                    {' '}
                    y {project.overdue_tasks} {plural(project.overdue_tasks, 'vencida', 'vencidas')}
                  </span>
                ) : null}
              </span>
            </span>
            <DimensionLine project={project} currentYear={currentYear} />
          </button>
        </li>
      ))}
    </ul>
  )
}

const HEX_COLOR = /^#[0-9a-fA-F]{6}$/

function AgendaRow({ entry }: { readonly entry: TodayAgendaEntry }) {
  const start = clockOf(entry.display_start)
  const end = clockOf(entry.display_end)
  const color = entry.color && HEX_COLOR.test(entry.color) ? entry.color : null
  return (
    <button type="button" onClick={() => navigateTo('calendar')} className={ROW_BUTTON}>
      {color ? (
        <span
          aria-hidden="true"
          className="size-2 shrink-0 translate-y-[-1px] self-center rounded-full"
          style={{ backgroundColor: color }}
        />
      ) : null}
      <span className="min-w-0 flex-1">
        <Title text={entry.title} />
        {entry.room ? <Title text={entry.room} className="text-sm text-muted-foreground" /> : null}
      </span>
      {entry.all_day ? null : start ? (
        <span className="shrink-0 text-sm tabular-nums text-muted-foreground">{end ? `${start} a ${end}` : start}</span>
      ) : null}
    </button>
  )
}

function AgendaList({ entries }: { readonly entries: readonly TodayAgendaEntry[] }) {
  const allDay = entries.filter((entry) => entry.all_day)
  const timed = entries.filter((entry) => !entry.all_day)
  return (
    <>
      {allDay.length > 0 ? (
        <ul className="mb-3">
          {allDay.map((entry) => (
            <li key={entry.occurrence_id}>
              <AgendaRow entry={entry} />
            </li>
          ))}
        </ul>
      ) : null}
      {timed.length > 0 ? (
        <ul className="ml-2 border-l border-plan-line">
          {timed.map((entry) => (
            <li key={entry.occurrence_id} className="relative pl-2">
              <span aria-hidden="true" className="absolute top-[1.15rem] -left-[4px] h-px w-[7px] bg-plan-line" />
              <AgendaRow entry={entry} />
            </li>
          ))}
        </ul>
      ) : null}
    </>
  )
}

const HABIT_STATE: Record<NonNullable<TodayHabit['today_status']> | 'pending', { text: string; Icon: LucideIcon }> = {
  pending: { text: 'Pendiente', Icon: CircleDashed },
  done: { text: 'Hecho', Icon: CircleCheck },
  skipped: { text: 'Omitido', Icon: CircleMinus },
  missed: { text: 'No hecho', Icon: CircleX }
}

function HabitList({ habits }: { readonly habits: readonly TodayHabit[] }) {
  return (
    <ul>
      {habits.map((habit) => {
        const { text, Icon } = HABIT_STATE[habit.today_status ?? 'pending']
        const time = clockOf(habit.preferred_local_time)
        return (
          <li key={habit.id}>
            <button type="button" onClick={() => navigateTo('habits')} className={cn(ROW_BUTTON, 'items-center')}>
              <Icon aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
              <Title text={habit.name} className="flex-1" />
              <span className="flex shrink-0 gap-3 text-sm text-muted-foreground">
                {time ? <span className="tabular-nums">{time}</span> : null}
                <span>{text}</span>
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

export function TodaySections({ data }: { readonly data: TodayResponse }) {
  const currentYear = yearOf(data.date)
  return (
    <div className="grid grid-cols-1 gap-x-14 gap-y-10 @3xl:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <div className="flex min-w-0 flex-col gap-10">
        <Block
          id="overdue"
          title="Vencidas"
          section={data.overdue}
          noun="tasks"
          emptyText="Nada vencido."
          link={{ label: 'Ver tareas', to: 'tasks' }}
        >
          {(items) => <OverdueList tasks={items} timeZone={data.timezone} />}
        </Block>
        <Block
          id="due"
          title="De hoy"
          section={data.due_today}
          noun="tasks"
          emptyText="Nada para hoy."
          link={{ label: 'Ver tareas', to: 'tasks' }}
        >
          {(items) => <DueTodayList tasks={items} timeZone={data.timezone} />}
        </Block>
        <Block
          id="projects"
          title="Proyectos activos"
          section={data.projects}
          noun="projects"
          emptyText="Sin proyectos activos."
          link={{ label: 'Ver proyectos', to: 'projects' }}
        >
          {(items) => <ProjectList projects={items} currentYear={currentYear} />}
        </Block>
      </div>
      <div className="flex min-w-0 flex-col gap-10">
        <Block
          id="agenda"
          title="Agenda"
          section={data.agenda}
          noun="agenda"
          emptyText="Nada en la agenda."
          link={{ label: 'Ver calendario', to: 'calendar' }}
        >
          {(items) => <AgendaList entries={items} />}
        </Block>
        <Block
          id="habits"
          title="Hábitos"
          section={data.habits}
          noun="habits"
          emptyText="Sin hábitos para hoy."
          link={{ label: 'Ver hábitos', to: 'habits' }}
        >
          {(items) => <HabitList habits={items} />}
        </Block>
      </div>
    </div>
  )
}
