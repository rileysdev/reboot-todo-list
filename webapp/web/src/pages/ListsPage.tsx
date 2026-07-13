import { useState, type FC } from "react";
import { useNavigate } from "react-router-dom";
import { useAccount } from "@api/todo/v1/todo_rbt_react";
import { useProfile } from "../profile";
import css from "./ListsPage.module.css";

type ListSummary = {
  id: string;
  name: string;
  taskCount: number;
  completedCount: number;
};

export const ListsPage: FC = () => {
  const { profile } = useProfile();
  const navigate = useNavigate();
  const account = useAccount({ id: profile!.accountId });
  const { response, isLoading } = account.useLists();

  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const lists: ListSummary[] = (response?.lists ?? []).map((l) => ({
    id: l.id,
    name: l.name,
    taskCount: l.taskCount,
    completedCount: l.completedCount,
  }));

  const createList = async () => {
    const name = newName.trim();
    if (!name || creating) return;
    setCreating(true);
    try {
      const result = await account.createList({ name });
      if (result.response) {
        setNewName("");
        navigate(`/list/${result.response.listId}`);
      }
    } finally {
      setCreating(false);
    }
  };

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

      <div className={css.addBar}>
        <input
          className={css.addInput}
          value={newName}
          placeholder="Name a new list — Groceries, This Week…"
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void createList();
          }}
        />
        <button
          className={css.addBtn}
          onClick={() => void createList()}
          disabled={!newName.trim() || creating}
          type="button"
        >
          Create list
        </button>
      </div>

      {isLoading && response === undefined ? (
        <div className={css.loading}>Loading your lists…</div>
      ) : lists.length === 0 ? (
        <div className={css.empty}>
          <div className={css.emptyMark}>✦</div>
          <p>No lists yet.</p>
          <p className={css.emptySub}>Create your first one above.</p>
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
              <button
                key={l.id}
                className={css.card}
                onClick={() => navigate(`/list/${l.id}`)}
                type="button"
              >
                <div className={css.cardTop}>
                  <h2 className={css.cardName}>{l.name || "Untitled list"}</h2>
                  {complete && <span className={css.done}>✓</span>}
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
                    className={[css.barFill, complete ? css.barDone : ""].join(
                      " "
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <div className={css.pct}>{pct}%</div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
};
