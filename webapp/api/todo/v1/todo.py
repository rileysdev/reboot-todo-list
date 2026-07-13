"""API for the standalone web todo app.

Three actors:

- `Account` — the per-user front door. Holds only the IDs of the lists
  it owns. (Named `Account`, not Reboot's reserved `User`, because a
  browser app defers identity until a real token verifier is wired; a
  plain type lets us omit auth during development and add it later
  without the reserved type's always-on rules.)
- `TodoList` — one named list. Owns its tasks' order (`task_ids`) so a
  drag reorder is a single cheap rewrite.
- `Task` — one todo item; its own actor so a checkbox toggle or edit
  touches only that task.

No `mcp=` / `UI()` here — this API is consumed only by the generated
TypeScript React client.
"""

from reboot.api import (
    API,
    Field,
    Methods,
    Model,
    Reader,
    Transaction,
    Type,
    Writer,
)

# ─── Shared value objects ────────────────────────────────────────────


class InvalidPriorityError(Model):
    """Raised when a priority outside the fixed vocabulary is supplied."""

    priority: str = Field(tag=1, default="")


class OrderMismatchError(Model):
    """Raised when a reorder request isn't a permutation of the current tasks."""

    expected_count: int = Field(tag=1, default=0)
    got_count: int = Field(tag=2, default=0)


class TaskView(Model):
    """A fully hydrated task, as the board renders it."""

    id: str = Field(tag=1, default="")
    title: str = Field(tag=2, default="")
    notes: str = Field(tag=3, default="")
    completed: bool = Field(tag=4, default=False)
    priority: str = Field(tag=5, default="")


class ListSummary(Model):
    """A one-line summary of a list, for the dashboard."""

    id: str = Field(tag=1, default="")
    name: str = Field(tag=2, default="")
    task_count: int = Field(tag=3, default=0)
    completed_count: int = Field(tag=4, default=0)


# ─── Account ─────────────────────────────────────────────────────────


class AccountState(Model):
    list_ids: list[str] = Field(tag=1, default_factory=list)


class CreateListRequest(Model):
    name: str = Field(tag=1, default="")


class CreateListResponse(Model):
    list_id: str = Field(tag=1, default="")


class ListsResponse(Model):
    lists: list[ListSummary] = Field(tag=1, default_factory=list)


# ─── TodoList ────────────────────────────────────────────────────────


class TodoListState(Model):
    name: str = Field(tag=1, default="")
    task_ids: list[str] = Field(tag=2, default_factory=list)


class CreateTodoListRequest(Model):
    name: str = Field(tag=1, default="")


class TodoListView(Model):
    name: str = Field(tag=1, default="")
    tasks: list[TaskView] = Field(tag=2, default_factory=list)


class SummaryResponse(Model):
    name: str = Field(tag=1, default="")
    task_count: int = Field(tag=2, default=0)
    completed_count: int = Field(tag=3, default=0)


class AddTaskRequest(Model):
    title: str = Field(tag=1, default="")
    priority: str = Field(tag=2, default="")


class AddTaskResponse(Model):
    task_id: str = Field(tag=1, default="")


class ReorderTasksRequest(Model):
    task_ids: list[str] = Field(tag=1, default_factory=list)


class RemoveTaskRequest(Model):
    task_id: str = Field(tag=1, default="")


class RenameRequest(Model):
    name: str = Field(tag=1, default="")


# ─── Task ────────────────────────────────────────────────────────────


class TaskState(Model):
    title: str = Field(tag=1, default="")
    notes: str = Field(tag=2, default="")
    completed: bool = Field(tag=3, default=False)
    priority: str = Field(tag=4, default="")


class CreateTaskRequest(Model):
    title: str = Field(tag=1, default="")
    priority: str = Field(tag=2, default="")


class TaskResponse(Model):
    title: str = Field(tag=1, default="")
    notes: str = Field(tag=2, default="")
    completed: bool = Field(tag=3, default=False)
    priority: str = Field(tag=4, default="")


class SetCompletedRequest(Model):
    completed: bool = Field(tag=1, default=False)


class EditRequest(Model):
    title: str = Field(tag=1, default="")
    notes: str = Field(tag=2, default="")
    priority: str = Field(tag=3, default="")


# ─── API ─────────────────────────────────────────────────────────────

api = API(
    Account=Type(
        state=AccountState,
        methods=Methods(
            # Explicit factory so the SPA can ensure the account exists
            # on login (a browser app has no MCP host to auto-construct
            # it, and no `initialize` hook runs it).
            create=Writer(
                request=None,
                response=None,
                factory=True,
                mcp=None,
            ),
            create_list=Transaction(
                request=CreateListRequest,
                response=CreateListResponse,
                mcp=None,
            ),
            lists=Reader(
                request=None,
                response=ListsResponse,
                mcp=None,
            ),
        ),
    ),
    TodoList=Type(
        state=TodoListState,
        methods=Methods(
            create=Writer(
                request=CreateTodoListRequest,
                response=None,
                factory=True,
                mcp=None,
            ),
            get=Reader(
                request=None,
                response=TodoListView,
                mcp=None,
            ),
            summary=Reader(
                request=None,
                response=SummaryResponse,
                mcp=None,
            ),
            add_task=Transaction(
                request=AddTaskRequest,
                response=AddTaskResponse,
                errors=[InvalidPriorityError],
                mcp=None,
            ),
            reorder_tasks=Writer(
                request=ReorderTasksRequest,
                response=None,
                errors=[OrderMismatchError],
                mcp=None,
            ),
            remove_task=Writer(
                request=RemoveTaskRequest,
                response=None,
                mcp=None,
            ),
            rename=Writer(
                request=RenameRequest,
                response=None,
                mcp=None,
            ),
        ),
    ),
    Task=Type(
        state=TaskState,
        methods=Methods(
            create=Writer(
                request=CreateTaskRequest,
                response=None,
                factory=True,
                mcp=None,
            ),
            get=Reader(
                request=None,
                response=TaskResponse,
                mcp=None,
            ),
            set_completed=Writer(
                request=SetCompletedRequest,
                response=None,
                mcp=None,
            ),
            edit=Writer(
                request=EditRequest,
                response=None,
                errors=[InvalidPriorityError],
                mcp=None,
            ),
        ),
    ),
)
