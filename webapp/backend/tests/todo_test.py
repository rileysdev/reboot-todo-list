"""End-to-end tests, one per user-facing story, run against the real
servicers via the in-process harness.

Authorization is deferred in this build (no token verifier yet), so tests
use a plain external context — there's no identity to impersonate. When a
verifier and ownership rules are added, these gain a bearer token per the
impersonation pattern.
"""

import unittest

from reboot.aio.applications import Application
from reboot.aio.tests import Reboot
from servicers.todo import AccountServicer, TaskServicer, TodoListServicer

from todo.v1.todo import (
    InvalidPriorityError,
    OrderMismatchError,
    UnknownSubtaskError,
)
from todo.v1.todo_rbt import Account, Task, TodoList


class TestTodo(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.rbt = Reboot()
        await self.rbt.start()
        await self.rbt.up(
            Application(
                servicers=[AccountServicer, TodoListServicer, TaskServicer],
            ),
            # These tests exercise actor methods over gRPC only; skipping
            # the local Envoy proxy (one server, since multi-server
            # routing needs Envoy) lets them run where Docker (or an
            # `envoy` executable) is unavailable.
            local_envoy=False,
            servers=1,
        )
        self.context = self.rbt.create_external_context(name=f"test-{self.id()}")
        self.account_id = "acct-alice"
        # A browser app constructs the account on login; tests do the same.
        await Account.create(self.context, self.account_id)

    async def asyncTearDown(self) -> None:
        await self.rbt.stop()

    async def _create_list(self, name: str = "Work", account_id: str = "") -> str:
        response = await Account.ref(account_id or self.account_id).create_list(
            self.context, name=name
        )
        return response.list_id

    async def test_account_creates_a_list_and_sees_it_listed(self) -> None:
        list_id = await self._create_list("Groceries")

        response = await Account.ref(self.account_id).lists(self.context)
        self.assertEqual(len(response.lists), 1)
        self.assertEqual(response.lists[0].id, list_id)
        self.assertEqual(response.lists[0].name, "Groceries")
        self.assertEqual(response.lists[0].task_count, 0)

    async def test_lists_are_scoped_per_account(self) -> None:
        await self._create_list("Alice list", account_id="acct-alice")
        await Account.create(self.context, "acct-bob")
        await self._create_list("Bob list", account_id="acct-bob")

        alice = await Account.ref("acct-alice").lists(self.context)
        bob = await Account.ref("acct-bob").lists(self.context)
        self.assertEqual([s.name for s in alice.lists], ["Alice list"])
        self.assertEqual([s.name for s in bob.lists], ["Bob list"])

    async def test_add_tasks_and_see_them_in_order(self) -> None:
        list_id = await self._create_list()
        await TodoList.ref(list_id).add_task(
            self.context, title="First", priority="high"
        )
        await TodoList.ref(list_id).add_task(self.context, title="Second")

        view = await TodoList.ref(list_id).get(self.context)
        self.assertEqual([t.title for t in view.tasks], ["First", "Second"])
        self.assertEqual(view.tasks[0].priority, "high")

    async def test_default_priority_is_none(self) -> None:
        list_id = await self._create_list()
        await TodoList.ref(list_id).add_task(self.context, title="No priority")

        view = await TodoList.ref(list_id).get(self.context)
        self.assertEqual(view.tasks[0].priority, "none")

    async def test_completing_a_task_updates_progress(self) -> None:
        list_id = await self._create_list()
        added = await TodoList.ref(list_id).add_task(self.context, title="Do it")

        await Task.ref(added.task_id).set_completed(self.context, completed=True)

        view = await TodoList.ref(list_id).get(self.context)
        self.assertTrue(view.tasks[0].completed)
        summary = await Account.ref(self.account_id).lists(self.context)
        self.assertEqual(summary.lists[0].completed_count, 1)

    async def test_reordering_tasks_changes_their_order(self) -> None:
        list_id = await self._create_list()
        task_ids = []
        for title in ["A", "B", "C"]:
            added = await TodoList.ref(list_id).add_task(
                self.context, title=title
            )
            task_ids.append(added.task_id)

        new_order = [task_ids[2], task_ids[0], task_ids[1]]
        await TodoList.ref(list_id).reorder_tasks(
            self.context, task_ids=new_order
        )

        view = await TodoList.ref(list_id).get(self.context)
        self.assertEqual([t.id for t in view.tasks], new_order)

    async def test_reorder_with_wrong_task_set_is_rejected(self) -> None:
        list_id = await self._create_list()
        added = await TodoList.ref(list_id).add_task(self.context, title="Only")

        with self.assertRaises(TodoList.ReorderTasksAborted) as caught:
            await TodoList.ref(list_id).reorder_tasks(
                self.context, task_ids=[added.task_id, "bogus-id"]
            )
        self.assertIsInstance(caught.exception.error, OrderMismatchError)

    async def test_renaming_a_list(self) -> None:
        list_id = await self._create_list("Old name")
        await TodoList.ref(list_id).rename(self.context, name="New name")

        view = await TodoList.ref(list_id).get(self.context)
        self.assertEqual(view.name, "New name")

    async def test_removing_a_task(self) -> None:
        list_id = await self._create_list()
        await TodoList.ref(list_id).add_task(self.context, title="Keep")
        drop = await TodoList.ref(list_id).add_task(self.context, title="Drop")

        await TodoList.ref(list_id).remove_task(
            self.context, task_id=drop.task_id
        )

        view = await TodoList.ref(list_id).get(self.context)
        self.assertEqual([t.title for t in view.tasks], ["Keep"])

    async def test_editing_a_task(self) -> None:
        list_id = await self._create_list()
        added = await TodoList.ref(list_id).add_task(self.context, title="Draft")

        await Task.ref(added.task_id).edit(
            self.context, title="Final", notes="with a note", priority="medium"
        )

        view = await TodoList.ref(list_id).get(self.context)
        task = view.tasks[0]
        self.assertEqual(task.title, "Final")
        self.assertEqual(task.notes, "with a note")
        self.assertEqual(task.priority, "medium")

    async def test_invalid_priority_on_add_is_rejected(self) -> None:
        list_id = await self._create_list()
        with self.assertRaises(TodoList.AddTaskAborted) as caught:
            await TodoList.ref(list_id).add_task(
                self.context, title="X", priority="urgent"
            )
        self.assertIsInstance(caught.exception.error, InvalidPriorityError)

    async def test_invalid_priority_on_edit_is_rejected(self) -> None:
        list_id = await self._create_list()
        added = await TodoList.ref(list_id).add_task(self.context, title="X")
        with self.assertRaises(Task.EditAborted) as caught:
            await Task.ref(added.task_id).edit(
                self.context, title="X", notes="", priority="soon"
            )
        self.assertIsInstance(caught.exception.error, InvalidPriorityError)

    async def _create_task_with_subtasks(
        self, subtask_titles: list[str]
    ) -> tuple[str, list[str]]:
        """A task on a fresh list, with one subtask per title given."""
        list_id = await self._create_list()
        added = await TodoList.ref(list_id).add_task(
            self.context, title="Parent"
        )
        subtask_ids = []
        for title in subtask_titles:
            response = await Task.ref(added.task_id).add_subtask(
                self.context, title=title
            )
            subtask_ids.append(response.subtask_id)
        return added.task_id, subtask_ids

    async def test_subtasks_appear_under_their_task_in_order(self) -> None:
        task_id, subtask_ids = await self._create_task_with_subtasks(
            ["First", "Second"]
        )

        task = await Task.ref(task_id).get(self.context)
        self.assertEqual([s.title for s in task.subtasks], ["First", "Second"])
        self.assertEqual([s.id for s in task.subtasks], subtask_ids)
        self.assertEqual([s.completed for s in task.subtasks], [False, False])

    async def test_completing_a_task_completes_its_subtasks(self) -> None:
        task_id, _ = await self._create_task_with_subtasks(["A", "B"])

        await Task.ref(task_id).set_completed(self.context, completed=True)

        task = await Task.ref(task_id).get(self.context)
        self.assertTrue(task.completed)
        self.assertEqual([s.completed for s in task.subtasks], [True, True])

    async def test_uncompleting_a_task_uncompletes_its_subtasks(self) -> None:
        task_id, _ = await self._create_task_with_subtasks(["A", "B"])
        await Task.ref(task_id).set_completed(self.context, completed=True)

        await Task.ref(task_id).set_completed(self.context, completed=False)

        task = await Task.ref(task_id).get(self.context)
        self.assertFalse(task.completed)
        self.assertEqual([s.completed for s in task.subtasks], [False, False])

    async def test_completing_every_subtask_completes_the_task(self) -> None:
        task_id, subtask_ids = await self._create_task_with_subtasks(["A", "B"])

        await Task.ref(task_id).set_subtask_completed(
            self.context, subtask_id=subtask_ids[0], completed=True
        )
        task = await Task.ref(task_id).get(self.context)
        self.assertFalse(task.completed)

        await Task.ref(task_id).set_subtask_completed(
            self.context, subtask_id=subtask_ids[1], completed=True
        )
        task = await Task.ref(task_id).get(self.context)
        self.assertTrue(task.completed)

    async def test_uncompleting_a_subtask_uncompletes_the_task(self) -> None:
        task_id, subtask_ids = await self._create_task_with_subtasks(["A", "B"])
        await Task.ref(task_id).set_completed(self.context, completed=True)

        await Task.ref(task_id).set_subtask_completed(
            self.context, subtask_id=subtask_ids[0], completed=False
        )

        task = await Task.ref(task_id).get(self.context)
        self.assertFalse(task.completed)
        self.assertEqual([s.completed for s in task.subtasks], [False, True])

    async def test_adding_a_subtask_to_a_completed_task_uncompletes_it(
        self,
    ) -> None:
        task_id, _ = await self._create_task_with_subtasks(["A"])
        await Task.ref(task_id).set_completed(self.context, completed=True)

        await Task.ref(task_id).add_subtask(self.context, title="B")

        task = await Task.ref(task_id).get(self.context)
        self.assertFalse(task.completed)
        self.assertEqual([s.completed for s in task.subtasks], [True, False])

    async def test_removing_the_last_incomplete_subtask_completes_the_task(
        self,
    ) -> None:
        task_id, subtask_ids = await self._create_task_with_subtasks(["A", "B"])
        await Task.ref(task_id).set_subtask_completed(
            self.context, subtask_id=subtask_ids[0], completed=True
        )

        await Task.ref(task_id).remove_subtask(
            self.context, subtask_id=subtask_ids[1]
        )

        task = await Task.ref(task_id).get(self.context)
        self.assertTrue(task.completed)
        self.assertEqual([s.id for s in task.subtasks], [subtask_ids[0]])

    async def test_removing_every_subtask_keeps_the_tasks_own_state(
        self,
    ) -> None:
        task_id, subtask_ids = await self._create_task_with_subtasks(["A"])

        await Task.ref(task_id).remove_subtask(
            self.context, subtask_id=subtask_ids[0]
        )

        task = await Task.ref(task_id).get(self.context)
        self.assertFalse(task.completed)
        self.assertEqual(list(task.subtasks), [])

    async def test_completing_an_unknown_subtask_is_rejected(self) -> None:
        task_id, _ = await self._create_task_with_subtasks(["A"])

        with self.assertRaises(Task.SetSubtaskCompletedAborted) as caught:
            await Task.ref(task_id).set_subtask_completed(
                self.context, subtask_id="bogus-id", completed=True
            )
        self.assertIsInstance(caught.exception.error, UnknownSubtaskError)

    async def test_subtasks_ride_along_in_the_list_view(self) -> None:
        list_id = await self._create_list()
        added = await TodoList.ref(list_id).add_task(
            self.context, title="Parent"
        )
        await Task.ref(added.task_id).add_subtask(self.context, title="Child")

        view = await TodoList.ref(list_id).get(self.context)
        self.assertEqual([s.title for s in view.tasks[0].subtasks], ["Child"])
