import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type FC,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { Link } from "react-router-dom";
import { useTask, useTodoList } from "@api/todo/v1/todo_rbt_react";
import css from "./Board.module.css";

type SubtaskData = {
  id: string;
  title: string;
  completed: boolean;
};

type TaskData = {
  id: string;
  title: string;
  notes: string;
  completed: boolean;
  priority: string;
  subtasks: SubtaskData[];
};

const PRIORITY_ORDER = ["none", "low", "medium", "high"] as const;
const PRIORITY_LABEL: Record<string, string> = {
  none: "No priority",
  low: "Low",
  medium: "Medium",
  high: "High",
};

type Rect = { top: number; height: number };

// The index the dragged row would settle into given how far it has moved,
// measured against the static centers of the other rows.
function computeTarget(fromIndex: number, dy: number, rects: Rect[]): number {
  const from = rects[fromIndex];
  if (!from) return fromIndex;
  const draggedCenter = from.top + from.height / 2 + dy;
  let target = fromIndex;
  for (let j = 0; j < rects.length; j++) {
    if (j === fromIndex) continue;
    const center = rects[j].top + rects[j].height / 2;
    if (j > fromIndex && draggedCenter > center) target = Math.max(target, j);
    if (j < fromIndex && draggedCenter < center) target = Math.min(target, j);
  }
  return target;
}

function sameSet(a: string[], b: string[]): boolean {
  if (a.length !== b.length) return false;
  const set = new Set(a);
  return b.every((x) => set.has(x));
}

// ── Icons ───────────────────────────────────────────────────────────

const GripIcon: FC = () => (
  <svg width="10" height="16" viewBox="0 0 10 16" aria-hidden="true">
    {[2, 8, 14].map((y) =>
      [2, 8].map((x) => (
        <circle key={`${x}-${y}`} cx={x} cy={y} r="1.4" fill="currentColor" />
      ))
    )}
  </svg>
);

const CheckIcon: FC = () => (
  <svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true">
    <path
      d="M2.5 6.8 L5.2 9.5 L10.5 3.5"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// ── One task row ────────────────────────────────────────────────────

const TaskRow: FC<{
  task: TaskData;
  dragging: boolean;
  style: CSSProperties;
  onDragStart: (id: string, e: ReactPointerEvent) => void;
  onDelete: (id: string) => void;
  setRowEl: (id: string, el: HTMLDivElement | null) => void;
}> = ({ task, dragging, style, onDragStart, onDelete, setRowEl }) => {
  const actor = useTask({ id: task.id });
  const [editingTitle, setEditingTitle] = useState(false);
  const [titleDraft, setTitleDraft] = useState(task.title);
  const [notesOpen, setNotesOpen] = useState(false);
  const [notesDraft, setNotesDraft] = useState(task.notes);
  const [addingSubtask, setAddingSubtask] = useState(false);
  const [subtaskDraft, setSubtaskDraft] = useState("");

  useEffect(() => {
    if (!editingTitle) setTitleDraft(task.title);
  }, [task.title, editingTitle]);
  useEffect(() => {
    if (!notesOpen) setNotesDraft(task.notes);
  }, [task.notes, notesOpen]);

  const toggle = () => {
    void actor.setCompleted({ completed: !task.completed });
  };

  const toggleSubtask = (subtask: SubtaskData) => {
    void actor.setSubtaskCompleted({
      subtaskId: subtask.id,
      completed: !subtask.completed,
    });
  };

  const commitSubtask = () => {
    const title = subtaskDraft.trim();
    setSubtaskDraft("");
    if (!title) {
      setAddingSubtask(false);
      return;
    }
    void actor.addSubtask({ title });
  };

  const cyclePriority = () => {
    const i = PRIORITY_ORDER.indexOf(
      task.priority as (typeof PRIORITY_ORDER)[number]
    );
    const next = PRIORITY_ORDER[(i + 1) % PRIORITY_ORDER.length];
    void actor.edit({ title: task.title, notes: task.notes, priority: next });
  };

  const commitTitle = () => {
    setEditingTitle(false);
    const next = titleDraft.trim();
    if (!next || next === task.title) {
      setTitleDraft(task.title);
      return;
    }
    void actor.edit({ title: next, notes: task.notes, priority: task.priority });
  };

  const commitNotes = () => {
    setNotesOpen(false);
    if (notesDraft === task.notes) return;
    void actor.edit({
      title: task.title,
      notes: notesDraft,
      priority: task.priority,
    });
  };

  const doneSubtasks = task.subtasks.filter((s) => s.completed).length;

  return (
    <div
      ref={(el) => setRowEl(task.id, el)}
      className={[
        css.item,
        dragging ? css.rowDragging : "",
        task.completed ? css.rowDone : "",
      ].join(" ")}
      style={style}
    >
      <div className={css.row}>
      <button
        className={css.handle}
        onPointerDown={(e) => onDragStart(task.id, e)}
        aria-label="Drag to reorder"
        type="button"
      >
        <GripIcon />
      </button>

      <button
        className={[css.check, task.completed ? css.checkOn : ""].join(" ")}
        onClick={toggle}
        aria-label={task.completed ? "Mark incomplete" : "Mark complete"}
        type="button"
      >
        {task.completed && <CheckIcon />}
      </button>

      <div className={css.body}>
        {editingTitle ? (
          <input
            autoFocus
            className={css.titleInput}
            value={titleDraft}
            onChange={(e) => setTitleDraft(e.target.value)}
            onBlur={commitTitle}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitTitle();
              if (e.key === "Escape") {
                setTitleDraft(task.title);
                setEditingTitle(false);
              }
            }}
          />
        ) : (
          <span
            className={css.title}
            onClick={() => setEditingTitle(true)}
            title="Click to edit"
          >
            {task.title}
          </span>
        )}

        {task.notes && !notesOpen && (
          <span className={css.notes} onClick={() => setNotesOpen(true)}>
            {task.notes}
          </span>
        )}
        {notesOpen && (
          <textarea
            autoFocus
            className={css.notesInput}
            value={notesDraft}
            placeholder="Add a note…"
            rows={2}
            onChange={(e) => setNotesDraft(e.target.value)}
            onBlur={commitNotes}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                setNotesDraft(task.notes);
                setNotesOpen(false);
              }
            }}
          />
        )}
      </div>

      {task.subtasks.length > 0 && (
        <span
          className={css.subtaskCount}
          title={`${doneSubtasks} of ${task.subtasks.length} subtasks done`}
        >
          {doneSubtasks}/{task.subtasks.length}
        </span>
      )}

      <button
        className={css.prio}
        data-level={task.priority}
        onClick={cyclePriority}
        title={`Priority: ${
          PRIORITY_LABEL[task.priority] ?? "No priority"
        } — click to change`}
        type="button"
      >
        <span className={css.prioDot} />
        {task.priority !== "none" && task.priority !== "" && (
          <span className={css.prioLabel}>{PRIORITY_LABEL[task.priority]}</span>
        )}
      </button>

      <button
        className={css.noteBtn}
        onClick={() => setNotesOpen((v) => !v)}
        aria-label="Edit note"
        title="Add / edit note"
        type="button"
      >
        <svg width="15" height="15" viewBox="0 0 15 15" aria-hidden="true">
          <path
            d="M2.5 11 L2.5 12.5 L4 12.5 L11 5.5 L9.5 4 Z M9.5 4 L11 2.5 L12.5 4 L11 5.5 Z"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.2"
            strokeLinejoin="round"
          />
        </svg>
      </button>

      <button
        className={css.subtaskBtn}
        onClick={() => setAddingSubtask((v) => !v)}
        aria-label="Add subtask"
        title="Add subtask"
        type="button"
      >
        <svg width="15" height="15" viewBox="0 0 15 15" aria-hidden="true">
          <path
            d="M7.5 3.5 L7.5 11.5 M3.5 7.5 L11.5 7.5"
            stroke="currentColor"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      </button>

      <button
        className={css.delete}
        onClick={() => onDelete(task.id)}
        aria-label="Delete task"
        title="Delete"
        type="button"
      >
        <svg width="13" height="13" viewBox="0 0 13 13" aria-hidden="true">
          <path
            d="M3 3 L10 10 M10 3 L3 10"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
        </svg>
      </button>
      </div>

      {(task.subtasks.length > 0 || addingSubtask) && (
        <div className={css.subtasks}>
          {task.subtasks.map((subtask) => (
            <div
              key={subtask.id}
              className={[
                css.subtaskRow,
                subtask.completed ? css.subtaskDone : "",
              ].join(" ")}
            >
              <button
                className={[
                  css.check,
                  css.subtaskCheck,
                  subtask.completed ? css.checkOn : "",
                ].join(" ")}
                onClick={() => toggleSubtask(subtask)}
                aria-label={
                  subtask.completed
                    ? `Mark subtask "${subtask.title}" incomplete`
                    : `Mark subtask "${subtask.title}" complete`
                }
                type="button"
              >
                {subtask.completed && <CheckIcon />}
              </button>
              <span className={css.subtaskTitle}>{subtask.title}</span>
              <button
                className={css.delete}
                onClick={() =>
                  void actor.removeSubtask({ subtaskId: subtask.id })
                }
                aria-label={`Delete subtask "${subtask.title}"`}
                title="Delete subtask"
                type="button"
              >
                <svg width="11" height="11" viewBox="0 0 13 13" aria-hidden="true">
                  <path
                    d="M3 3 L10 10 M10 3 L3 10"
                    stroke="currentColor"
                    strokeWidth="1.6"
                    strokeLinecap="round"
                  />
                </svg>
              </button>
            </div>
          ))}
          {addingSubtask && (
            <input
              autoFocus
              className={css.subtaskInput}
              value={subtaskDraft}
              placeholder="Add a subtask and press Enter…"
              onChange={(e) => setSubtaskDraft(e.target.value)}
              onBlur={commitSubtask}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitSubtask();
                if (e.key === "Escape") {
                  setSubtaskDraft("");
                  setAddingSubtask(false);
                }
              }}
            />
          )}
        </div>
      )}
    </div>
  );
};

// ── The board ───────────────────────────────────────────────────────

export const Board: FC<{ listId: string }> = ({ listId }) => {
  const list = useTodoList({ id: listId });
  const { response, isLoading, aborted } = list.useGet();

  const serverTasks: TaskData[] = (response?.tasks ?? []).map((t) => ({
    id: t.id,
    title: t.title,
    notes: t.notes,
    completed: t.completed,
    priority: t.priority,
    subtasks: (t.subtasks ?? []).map((s) => ({
      id: s.id,
      title: s.title,
      completed: s.completed,
    })),
  }));
  const serverIds = serverTasks.map((t) => t.id);
  const serverJoin = serverIds.join(",");
  const name = response?.name ?? "";

  const [optimisticOrder, setOptimisticOrder] = useState<string[] | null>(null);
  const [drag, setDrag] = useState<{
    id: string;
    fromIndex: number;
    dy: number;
  } | null>(null);

  const rowEls = useRef<Map<string, HTMLDivElement>>(new Map());
  const rectsRef = useRef<Rect[]>([]);
  const gapRef = useRef(0);
  const snapshotOrderRef = useRef<string[]>([]);
  const draggingRef = useRef(false);
  const pendingJoinRef = useRef<string | null>(null);

  useEffect(() => {
    if (draggingRef.current) return;
    if (pendingJoinRef.current !== null) {
      const pendingIds = pendingJoinRef.current.split(",").filter(Boolean);
      if (pendingJoinRef.current === serverJoin) {
        pendingJoinRef.current = null;
        setOptimisticOrder(null);
      } else if (!sameSet(pendingIds, serverIds)) {
        pendingJoinRef.current = null;
        setOptimisticOrder(null);
      }
      return;
    }
    setOptimisticOrder(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serverJoin]);

  const setRowEl = useCallback((id: string, el: HTMLDivElement | null) => {
    if (el) rowEls.current.set(id, el);
    else rowEls.current.delete(id);
  }, []);

  const handleDragStart = (id: string, e: ReactPointerEvent) => {
    if (e.button !== 0) return;
    const currentOrder = optimisticOrder ?? serverIds;
    const fromIndex = currentOrder.indexOf(id);
    if (fromIndex < 0) return;

    const rects = currentOrder.map((tid) => {
      const el = rowEls.current.get(tid);
      const r = el?.getBoundingClientRect();
      return { top: r?.top ?? 0, height: r?.height ?? 0 };
    });
    rectsRef.current = rects;
    gapRef.current =
      rects.length > 1
        ? Math.max(0, rects[1].top - rects[0].top - rects[0].height)
        : 0;
    snapshotOrderRef.current = currentOrder;
    draggingRef.current = true;
    setOptimisticOrder(currentOrder);
    setDrag({ id, fromIndex, dy: 0 });

    const startY = e.clientY;

    const onMove = (ev: PointerEvent) => {
      setDrag((d) => (d ? { ...d, dy: ev.clientY - startY } : d));
    };
    const onUp = (ev: PointerEvent) => {
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
      const target = computeTarget(
        fromIndex,
        ev.clientY - startY,
        rectsRef.current
      );
      draggingRef.current = false;
      setDrag(null);
      if (target !== fromIndex) {
        const newOrder = [...snapshotOrderRef.current];
        const [moved] = newOrder.splice(fromIndex, 1);
        newOrder.splice(target, 0, moved);
        setOptimisticOrder(newOrder);
        pendingJoinRef.current = newOrder.join(",");
        void list.reorderTasks({ taskIds: newOrder });
      } else {
        setOptimisticOrder(null);
      }
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
    e.preventDefault();
  };

  const handleDelete = (id: string) => {
    void list.removeTask({ taskId: id });
  };

  // Rename.
  const [renaming, setRenaming] = useState(false);
  const [nameDraft, setNameDraft] = useState(name);
  useEffect(() => {
    if (!renaming) setNameDraft(name);
  }, [name, renaming]);
  const commitName = () => {
    setRenaming(false);
    const next = nameDraft.trim();
    if (!next || next === name) {
      setNameDraft(name);
      return;
    }
    void list.rename({ name: next });
  };

  // Add task.
  const [newTitle, setNewTitle] = useState("");
  const [newPriority, setNewPriority] = useState<string>("none");
  const addTask = () => {
    const title = newTitle.trim();
    if (!title) return;
    setNewTitle("");
    const priority = newPriority;
    setNewPriority("none");
    void list.addTask({ title, priority });
  };

  const order = optimisticOrder ?? serverIds;
  const taskById = new Map(serverTasks.map((t) => [t.id, t]));
  const orderedTasks = order
    .map((id) => taskById.get(id))
    .filter((t): t is TaskData => Boolean(t));

  const total = serverTasks.length;
  const done = serverTasks.filter((t) => t.completed).length;
  const pct = total === 0 ? 0 : Math.round((done / total) * 100);

  const rects = rectsRef.current;
  const dragTarget = drag ? computeTarget(drag.fromIndex, drag.dy, rects) : -1;
  const shift =
    drag && rects[drag.fromIndex]
      ? rects[drag.fromIndex].height + gapRef.current
      : 0;

  const styleFor = (index: number): CSSProperties => {
    if (!drag) return {};
    if (index === drag.fromIndex) {
      return {
        transform: `translateY(${drag.dy}px)`,
        transition: "none",
        zIndex: 30,
        position: "relative",
      };
    }
    let ty = 0;
    if (
      drag.fromIndex < dragTarget &&
      index > drag.fromIndex &&
      index <= dragTarget
    )
      ty = -shift;
    else if (
      dragTarget < drag.fromIndex &&
      index >= dragTarget &&
      index < drag.fromIndex
    )
      ty = shift;
    return { transform: `translateY(${ty}px)` };
  };

  if (aborted && !isLoading && response === undefined) {
    return (
      <div className={css.page}>
        <Link to="/" className={css.back}>
          ← All lists
        </Link>
        <div className={css.notFound}>
          <div className={css.emptyMark}>✦</div>
          <p>This list couldn’t be found.</p>
          <p className={css.emptySub}>It may have been removed.</p>
        </div>
      </div>
    );
  }

  if (isLoading && response === undefined) {
    return (
      <div className={css.page}>
        <div className={css.loading}>Loading your board…</div>
      </div>
    );
  }

  return (
    <div className={[css.page, drag ? css.pageDragging : ""].join(" ")}>
      <Link to="/" className={css.back}>
        ← All lists
      </Link>

      <header className={css.header}>
        <div className={css.headTop}>
          <span className={css.kicker}>Todo list</span>
          <span className={css.count}>
            {done}/{total} done
          </span>
        </div>
        {renaming ? (
          <input
            autoFocus
            className={css.nameInput}
            value={nameDraft}
            onChange={(e) => setNameDraft(e.target.value)}
            onBlur={commitName}
            onKeyDown={(e) => {
              if (e.key === "Enter") commitName();
              if (e.key === "Escape") {
                setNameDraft(name);
                setRenaming(false);
              }
            }}
          />
        ) : (
          <h1
            className={css.title}
            onClick={() => setRenaming(true)}
            title="Click to rename"
          >
            {name || "Untitled list"}
          </h1>
        )}
        <div className={css.progress}>
          <div className={css.progressFill} style={{ width: `${pct}%` }} />
        </div>
      </header>

      <div className={css.list}>
        {orderedTasks.length === 0 ? (
          <div className={css.empty}>
            <div className={css.emptyMark}>✦</div>
            <p>Nothing here yet.</p>
            <p className={css.emptySub}>Add your first task below.</p>
          </div>
        ) : (
          orderedTasks.map((task, index) => (
            <TaskRow
              key={task.id}
              task={task}
              dragging={drag?.id === task.id}
              style={styleFor(index)}
              onDragStart={handleDragStart}
              onDelete={handleDelete}
              setRowEl={setRowEl}
            />
          ))
        )}
      </div>

      <div className={css.addBar}>
        <button
          className={css.addPrio}
          data-level={newPriority}
          onClick={() => {
            const i = PRIORITY_ORDER.indexOf(
              newPriority as (typeof PRIORITY_ORDER)[number]
            );
            setNewPriority(PRIORITY_ORDER[(i + 1) % PRIORITY_ORDER.length]);
          }}
          title={`New task priority: ${PRIORITY_LABEL[newPriority]} — click to change`}
          type="button"
        >
          <span className={css.prioDot} />
        </button>
        <input
          className={css.addInput}
          value={newTitle}
          placeholder="Add a task and press Enter…"
          onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") addTask();
          }}
        />
        <button
          className={css.addBtn}
          onClick={addTask}
          disabled={!newTitle.trim()}
          type="button"
        >
          Add
        </button>
      </div>
    </div>
  );
};
