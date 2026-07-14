"""Servicers for the todo app: User front door, TodoList, and Task."""

import uuid

import rbt.v1alpha1.errors_pb2 as errors_pb2
from reboot.aio.auth.authorizers import (
    allow_if,
    is_app_internal,
)
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
from todo.v1.todo_rbt import Task, TodoList, User

# The fixed priority vocabulary. Defined once here, at the boundary
# where a priority enters from the AI; downstream code trusts it.
VALID_PRIORITIES = ("none", "low", "medium", "high")


def _normalize_priority(raw: str) -> str:
    """Empty priority means 'none'; otherwise fold to a canonical token."""
    return raw.strip().lower() or "none"


def is_owner(*, context, state, request, **kwargs):
    """Allow only the user whose ID matches the actor's `owner_user_id`."""
    if context.auth is None or context.auth.user_id is None:
        return errors_pb2.Unauthenticated()
    if state is not None and state.owner_user_id == context.auth.user_id:
        return errors_pb2.Ok()
    return errors_pb2.PermissionDenied()


class UserServicer(User.Servicer):
    # No custom `authorizer()`: the framework default for a `User` type
    # (`state_id_is_user_id` + `is_app_internal`) is already correct —
    # a user reaches only their own front door.

    async def create_list(
        self,
        context: TransactionContext,
        request: User.CreateListRequest,
    ) -> User.CreateListResponse:
        # A `User` actor's state ID is the caller's user ID, so it is the
        # owner of every list it creates.
        owner_user_id = self.ref().state_id
        todo_list, _ = await TodoList.create(
            context,
            name=request.name,
            owner_user_id=owner_user_id,
        )
        self.state.list_ids.append(todo_list.state_id)
        return User.CreateListResponse(list_id=todo_list.state_id)

    async def lists(
        self,
        context: ReaderContext,
    ) -> User.ListsResponse:
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
        return User.ListsResponse(lists=summaries)


class TodoListServicer(TodoList.Servicer):

    def authorizer(self):
        # The owner may act on their list; internal hops (creation, the
        # composing readers) are also allowed.
        return allow_if(any=[is_owner, is_app_internal])

    async def create(
        self,
        context: WriterContext,
        request: TodoList.CreateRequest,
    ) -> None:
        if context.constructor:
            self.state.name = request.name
            self.state.owner_user_id = request.owner_user_id

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
            context,
            title=request.title,
            priority=priority,
            owner_user_id=self.state.owner_user_id,
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
        return allow_if(any=[is_owner, is_app_internal])

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
            self.state.owner_user_id = request.owner_user_id

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
        # The task's completion state flows down: subtasks follow their
        # task in both directions. (Unchecking must cascade too —
        # otherwise all-complete subtasks would immediately re-complete
        # the task via the all-subtasks-complete rule.)
        for subtask in self.state.subtasks:
            subtask.completed = request.completed

    async def add_subtask(
        self,
        context: WriterContext,
        request: Task.AddSubtaskRequest,
    ) -> Task.AddSubtaskResponse:
        subtask = Subtask(id=str(uuid.uuid4()), title=request.title)
        self.state.subtasks.append(subtask)
        # A new subtask starts incomplete, so the task no longer has
        # every subtask complete.
        self.state.completed = False
        return Task.AddSubtaskResponse(subtask_id=subtask.id)

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
        # Completion flows up: the task is complete exactly when every
        # subtask is complete.
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
            # Tolerate an already-removed subtask, mirroring
            # `TodoList.remove_task`.
            return
        self.state.subtasks = remaining_subtasks
        # Recompute completion from the remaining subtasks. When none
        # remain the task keeps its current state — an empty task has no
        # subtasks to imply anything.
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
