"""API for a drag-and-drop todo app.

Three actors:

- `User` — the front door. Holds only the IDs of the lists it owns and
  the methods to create/locate them.
- `TodoList` — one named list. Owns its tasks' order (`task_ids`), so
  reordering is a single cheap rewrite of that ordered list.
- `Task` — one todo item. Its own actor so a checkbox toggle or an edit
  touches only that task, not the whole list.
"""

from reboot.api import (
    API,
    UI,
    Field,
    Methods,
    Model,
    Reader,
    Tool,
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


class UnknownSubtaskError(Model):
    """Raised when a subtask ID doesn't belong to the task it was sent to."""

    subtask_id: str = Field(tag=1, default="")


class Subtask(Model):
    """One subtask of a task: a title and a checkbox, one level deep.

    Subtasks live inside their parent task's state (not as their own
    actors) so the completion cascade between a task and its subtasks
    is a single-actor write, atomic by construction.
    """

    id: str = Field(tag=1, default="")
    title: str = Field(tag=2, default="")
    completed: bool = Field(tag=3, default=False)


class TaskView(Model):
    """A fully hydrated task, as the board UI renders it."""

    id: str = Field(tag=1, default="")
    title: str = Field(tag=2, default="")
    notes: str = Field(tag=3, default="")
    completed: bool = Field(tag=4, default=False)
    priority: str = Field(tag=5, default="")
    subtasks: list[Subtask] = Field(tag=6, default_factory=list)


class ListSummary(Model):
    """A one-line summary of a list, for the overview dashboard."""

    id: str = Field(tag=1, default="")
    name: str = Field(tag=2, default="")
    task_count: int = Field(tag=3, default=0)
    completed_count: int = Field(tag=4, default=0)


# ─── User ────────────────────────────────────────────────────────────


class UserState(Model):
    # IDs of the TodoLists this user owns, in creation order. A person's
    # set of lists is small and always read whole, so a plain ordered
    # list of IDs (not a paginated map) is the right container.
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
    owner_user_id: str = Field(tag=2, default="")
    # Ordered IDs of this list's tasks. Order lives here: dragging to
    # reorder is just rewriting this list.
    task_ids: list[str] = Field(tag=3, default_factory=list)


class CreateTodoListRequest(Model):
    name: str = Field(tag=1, default="")
    owner_user_id: str = Field(tag=2, default="")


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
    owner_user_id: str = Field(tag=5, default="")
    subtasks: list[Subtask] = Field(tag=6, default_factory=list)


class CreateTaskRequest(Model):
    title: str = Field(tag=1, default="")
    priority: str = Field(tag=2, default="")
    owner_user_id: str = Field(tag=3, default="")


class TaskResponse(Model):
    title: str = Field(tag=1, default="")
    notes: str = Field(tag=2, default="")
    completed: bool = Field(tag=3, default=False)
    priority: str = Field(tag=4, default="")
    subtasks: list[Subtask] = Field(tag=5, default_factory=list)


class SetCompletedRequest(Model):
    completed: bool = Field(tag=1, default=False)


class EditRequest(Model):
    title: str = Field(tag=1, default="")
    notes: str = Field(tag=2, default="")
    priority: str = Field(tag=3, default="")


class AddSubtaskRequest(Model):
    title: str = Field(tag=1, default="")


class AddSubtaskResponse(Model):
    subtask_id: str = Field(tag=1, default="")


class SetSubtaskCompletedRequest(Model):
    subtask_id: str = Field(tag=1, default="")
    completed: bool = Field(tag=2, default=False)


class RemoveSubtaskRequest(Model):
    subtask_id: str = Field(tag=1, default="")


# ─── API ─────────────────────────────────────────────────────────────

api = API(
    User=Type(
        state=UserState,
        methods=Methods(
            create_list=Transaction(
                request=CreateListRequest,
                response=CreateListResponse,
                description=(
                    "Create a new todo list with the given name. Returns "
                    "the new list's ID. That ID is opaque; pass it to "
                    "future tool calls, but there's no need to show it to "
                    "the human."
                ),
                mcp=Tool(),
            ),
            lists=Reader(
                request=None,
                response=ListsResponse,
                description=(
                    "List all of this user's todo lists with their task "
                    "counts and completion progress."
                ),
                mcp=Tool(),
            ),
            overview=UI(
                request=None,
                path="web/ui/overview",
                title="My Lists",
                description=(
                    "Open the visual dashboard of all the user's todo "
                    "lists and their progress."
                ),
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
                description=(
                    "Get one todo list's name and its tasks in order."
                ),
                mcp=Tool(),
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
                description=(
                    "Add a task to this list. `priority` is one of "
                    "'none', 'low', 'medium', 'high' (defaults to "
                    "'none'). Returns the new task's ID."
                ),
                mcp=Tool(),
            ),
            reorder_tasks=Writer(
                request=ReorderTasksRequest,
                response=None,
                errors=[OrderMismatchError],
                description=(
                    "Set the full new order of this list's tasks. Pass "
                    "every existing task ID exactly once, in the desired "
                    "order."
                ),
                mcp=Tool(),
            ),
            remove_task=Writer(
                request=RemoveTaskRequest,
                response=None,
                description="Remove a task from this list.",
                mcp=Tool(),
            ),
            rename=Writer(
                request=RenameRequest,
                response=None,
                description="Rename this todo list.",
                mcp=Tool(),
            ),
            show=UI(
                request=None,
                path="web/ui/board",
                title="Todo Board",
                description=(
                    "Open the interactive drag-and-drop board for this "
                    "todo list."
                ),
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
                description=(
                    "Mark this task complete or incomplete. Cascades to "
                    "subtasks: completing the task completes every "
                    "subtask, and un-completing it un-completes every "
                    "subtask."
                ),
                mcp=Tool(),
            ),
            edit=Writer(
                request=EditRequest,
                response=None,
                errors=[InvalidPriorityError],
                description=(
                    "Edit this task's title, notes, and priority "
                    "('none', 'low', 'medium', 'high')."
                ),
                mcp=Tool(),
            ),
            add_subtask=Writer(
                request=AddSubtaskRequest,
                response=AddSubtaskResponse,
                description=(
                    "Add a subtask to this task. Returns the new "
                    "subtask's ID. The new subtask starts incomplete, so "
                    "a completed task becomes incomplete again."
                ),
                mcp=Tool(),
            ),
            set_subtask_completed=Writer(
                request=SetSubtaskCompletedRequest,
                response=None,
                errors=[UnknownSubtaskError],
                description=(
                    "Mark one subtask complete or incomplete. The task "
                    "itself follows its subtasks: it becomes complete "
                    "exactly when every subtask is complete."
                ),
                mcp=Tool(),
            ),
            remove_subtask=Writer(
                request=RemoveSubtaskRequest,
                response=None,
                description="Remove a subtask from this task.",
                mcp=Tool(),
            ),
        ),
    ),
)
