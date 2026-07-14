"""Servicers for the web todo app: Account front door, TodoList, Task.

Authorization is intentionally a development placeholder. This app has no
identity provider wired yet, so every servicer declares `allow()` — an
explicit "this endpoint is currently public and unauthenticated." That is
the honest description of the app today and, unlike omitting `authorizer()`
(which `rbt dev` permits but the production-mode test harness and
`rbt serve` deny), it behaves the same everywhere.

Before serving real users: wire a `token_verifier=` on the Application and
replace these `allow()` rules with ownership rules keyed on the
authenticated account id (see the web-app auth sequence).
"""

import uuid

from reboot.aio.auth.authorizers import allow
from reboot.aio.contexts import (
    ReaderContext,
    TransactionContext,
    WriterContext,
)

from todo.v1.todo import (
    InvalidPriorityError,
    ListSummary,
    OrderMismatchError,
    Subtask,
    TaskView,
    UnknownSubtaskError,
)
from todo.v1.todo_rbt import Account, Task, TodoList

# The fixed priority vocabulary, defined once at the boundary where a
# priority enters from the client; downstream code trusts it.
VALID_PRIORITIES = ("none", "low", "medium", "high")


def _normalize_priority(raw: str) -> str:
    """Empty priority means 'none'; otherwise fold to a canonical token."""
    return raw.strip().lower() or "none"


class AccountServicer(Account.Servicer):

    def authorizer(self):
        return allow()

    async def create(self, context: WriterContext) -> None:
        # Empty state (list_ids defaults to []). The factory exists so the
        # SPA can construct the account on login.
        pass

    async def create_list(
        self,
        context: TransactionContext,
        request: Account.CreateListRequest,
    ) -> Account.CreateListResponse:
        todo_list, _ = await TodoList.create(context, name=request.name)
        self.state.list_ids.append(todo_list.state_id)
        return Account.CreateListResponse(list_id=todo_list.state_id)

    async def lists(
        self,
        context: ReaderContext,
    ) -> Account.ListsResponse:
        summaries = []
        for list_id in self.state.list_ids:
            summary = await TodoList.ref(list_id).summary(context)
            summaries.append(
                ListSummary(
                    id=list_id,
                    name=summary.name,
                    task_count=summary.task_count,
                    completed_count=summary.completed_count,
                )
            )
        return Account.ListsResponse(lists=summaries)


class TodoListServicer(TodoList.Servicer):

    def authorizer(self):
        return allow()

    async def create(
        self,
        context: WriterContext,
        request: TodoList.CreateRequest,
    ) -> None:
        if context.constructor:
            self.state.name = request.name

    async def get(
        self,
        context: ReaderContext,
    ) -> TodoList.GetResponse:
        # Composing reader: hydrate each task actor in stored order.
        tasks = []
        for task_id in self.state.task_ids:
            task = await Task.ref(task_id).get(context)
            tasks.append(
                TaskView(
                    id=task_id,
                    title=task.title,
                    notes=task.notes,
                    completed=task.completed,
                    priority=task.priority,
                    subtasks=list(task.subtasks),
                )
            )
        return TodoList.GetResponse(name=self.state.name, tasks=tasks)

    async def summary(
        self,
        context: ReaderContext,
    ) -> TodoList.SummaryResponse:
        completed_count = 0
        for task_id in self.state.task_ids:
            task = await Task.ref(task_id).get(context)
            if task.completed:
                completed_count += 1
        return TodoList.SummaryResponse(
            name=self.state.name,
            task_count=len(self.state.task_ids),
            completed_count=completed_count,
        )

    async def add_task(
        self,
        context: TransactionContext,
        request: TodoList.AddTaskRequest,
    ) -> TodoList.AddTaskResponse:
        priority = _normalize_priority(request.priority)
        if priority not in VALID_PRIORITIES:
            raise TodoList.AddTaskAborted(
                InvalidPriorityError(priority=request.priority)
            )
        task, _ = await Task.create(
            context, title=request.title, priority=priority
        )
        self.state.task_ids.append(task.state_id)
        return TodoList.AddTaskResponse(task_id=task.state_id)

    async def reorder_tasks(
        self,
        context: WriterContext,
        request: TodoList.ReorderTasksRequest,
    ) -> None:
        # A valid reorder is a permutation of the current task set — same
        # IDs, each exactly once. Reject anything else so a stale client
        # can't silently drop or duplicate a task.
        if sorted(request.task_ids) != sorted(self.state.task_ids):
            raise TodoList.ReorderTasksAborted(
                OrderMismatchError(
                    expected_count=len(self.state.task_ids),
                    got_count=len(request.task_ids),
                )
            )
        self.state.task_ids = list(request.task_ids)

    async def remove_task(
        self,
        context: WriterContext,
        request: TodoList.RemoveTaskRequest,
    ) -> None:
        if request.task_id in self.state.task_ids:
            self.state.task_ids.remove(request.task_id)

    async def rename(
        self,
        context: WriterContext,
        request: TodoList.RenameRequest,
    ) -> None:
        self.state.name = request.name


class TaskServicer(Task.Servicer):

    def authorizer(self):
        return allow()

    async def create(
        self,
        context: WriterContext,
        request: Task.CreateRequest,
    ) -> None:
        if context.constructor:
            # `priority` was validated at the list-level boundary before
            # this task was created; trust it here.
            self.state.title = request.title
            self.state.priority = request.priority

    async def get(
        self,
        context: ReaderContext,
    ) -> Task.GetResponse:
        return Task.GetResponse(
            title=self.state.title,
            notes=self.state.notes,
            completed=self.state.completed,
            priority=self.state.priority,
            subtasks=list(self.state.subtasks),
        )

    async def set_completed(
        self,
        context: WriterContext,
        request: Task.SetCompletedRequest,
    ) -> None:
        self.state.completed = request.completed
        # Cascade both ways: completing the task completes every subtask,
        # and un-completing it un-completes every subtask. The downward
        # un-complete keeps the two cascade rules consistent — otherwise
        # un-completing a task whose subtasks are all complete would be
        # immediately undone by the "all subtasks complete" rule.
        for subtask in self.state.subtasks:
            subtask.completed = request.completed

    async def add_subtask(
        self,
        context: WriterContext,
        request: Task.AddSubtaskRequest,
    ) -> Task.AddSubtaskResponse:
        subtask_id = str(uuid.uuid4())
        self.state.subtasks.append(
            Subtask(id=subtask_id, title=request.title, completed=False)
        )
        # A task is complete exactly when every subtask is; the new
        # subtask is incomplete, so the task is now incomplete.
        self.state.completed = False
        return Task.AddSubtaskResponse(subtask_id=subtask_id)

    async def set_subtask_completed(
        self,
        context: WriterContext,
        request: Task.SetSubtaskCompletedRequest,
    ) -> None:
        for subtask in self.state.subtasks:
            if subtask.id == request.subtask_id:
                subtask.completed = request.completed
                break
        else:
            raise Task.SetSubtaskCompletedAborted(
                UnknownSubtaskError(subtask_id=request.subtask_id)
            )
        self.state.completed = all(
            subtask.completed for subtask in self.state.subtasks
        )

    async def remove_subtask(
        self,
        context: WriterContext,
        request: Task.RemoveSubtaskRequest,
    ) -> None:
        remaining_subtasks = [
            subtask
            for subtask in self.state.subtasks
            if subtask.id != request.subtask_id
        ]
        if len(remaining_subtasks) == len(self.state.subtasks):
            return
        self.state.subtasks = remaining_subtasks
        # Removing the last incomplete subtask completes the task — but a
        # task with no subtasks left keeps its own completion state
        # rather than being auto-completed by `all([])`.
        if remaining_subtasks:
            self.state.completed = all(
                subtask.completed for subtask in remaining_subtasks
            )

    async def edit(
        self,
        context: WriterContext,
        request: Task.EditRequest,
    ) -> None:
        priority = _normalize_priority(request.priority)
        if priority not in VALID_PRIORITIES:
            raise Task.EditAborted(
                InvalidPriorityError(priority=request.priority)
            )
        self.state.title = request.title
        self.state.notes = request.notes
        self.state.priority = priority
