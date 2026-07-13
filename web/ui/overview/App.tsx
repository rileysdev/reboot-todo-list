import { type FC } from "react";
import { useUser } from "@api/todo/v1/todo_rbt_react";
import css from "./App.module.css";

type ListSummary = {
  id: string;
  name: string;
  taskCount: number;
  completedCount: number;
};

export const OverviewApp: FC = () => {
  const user = useUser();
  const { response, isLoading } = user.useLists();

  const lists: ListSummary[] = (response?.lists ?? []).map((l) => ({
    id: l.id,
    name: l.name,
    taskCount: l.taskCount,
    completedCount: l.completedCount,
  }));

  if (isLoading && response === undefined) {
    return (
      <div className={css.page}>
        <div className={css.loading}>Loading your lists…</div>
      </div>
    );
  }

  const totalTasks = lists.reduce((n, l) => n + l.taskCount, 0);
  const totalDone = lists.reduce((n, l) => n + l.completedCount, 0);

  return (
    <div className={css.page}>
      <header className={css.header}>
        <span className={css.kicker}>Overview</span>
        <h1 className={css.title}>My Lists</h1>
        {lists.length > 0 && (
          <p className={css.sub}>
            {lists.length} {lists.length === 1 ? "list" : "lists"} ·{" "}
            {totalDone}/{totalTasks} tasks done
          </p>
        )}
      </header>

      {lists.length === 0 ? (
        <div className={css.empty}>
          <div className={css.emptyMark}>✦</div>
          <p>No lists yet.</p>
          <p className={css.emptySub}>
            Ask to create one — like “start a Groceries list”.
          </p>
        </div>
      ) : (
        <div className={css.grid}>
          {lists.map((l) => {
            const pct =
              l.taskCount === 0
                ? 0
                : Math.round((l.completedCount / l.taskCount) * 100);
            const complete = l.taskCount > 0 && l.completedCount === l.taskCount;
            return (
              <article key={l.id} className={css.card}>
                <div className={css.cardTop}>
                  <h2 className={css.cardName}>{l.name || "Untitled list"}</h2>
                  {complete && <span className={css.done}>✓ done</span>}
                </div>
                <div className={css.cardCount}>
                  <span className={css.big}>{l.completedCount}</span>
                  <span className={css.of}>/ {l.taskCount}</span>
                  <span className={css.tasksWord}>
                    {l.taskCount === 1 ? "task" : "tasks"}
                  </span>
                </div>
                <div className={css.bar}>
                  <div
                    className={[css.barFill, complete ? css.barDone : ""].join(" ")}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className={css.pct}>{pct}%</div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
};
