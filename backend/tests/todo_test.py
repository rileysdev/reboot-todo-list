"""End-to-end tests, one per user-facing story, run against the real
servicers and their real authorizers (identity is impersonated, auth is
never weakened)."""

import unittest

from reboot.aio.aborted import Aborted
from reboot.aio.applications import Application
from reboot.aio.auth.oauth_providers import Anonymous
from reboot.aio.tests import OAuthProviderForTest, Reboot
from servicers.todo import TaskServicer, TodoListServicer, UserServicer

from todo.v1.todo import (
    InvalidPriorityError,
    OrderMismatchError,
    UnknownSubtaskError,
)
from todo.v1.todo_rbt import Task, TodoList, User


class TestTodo(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self) -> None:
        self.rbt = Reboot()
        await self.rbt.start()
        await self.rbt.up(
            Application(
                servicers=[UserServicer, TodoListServicer, TaskServicer],
                oauth=OAuthProviderForTest(Anonymous()),
            ),
            # These tests exercise actor methods over gRPC only; skipping
            # the local Envoy proxy (one server, since multi-server
            # routing needs Envoy) lets them run where Docker (or an
            # `envoy` executable) is unavailable.
            local_envoy=False,
            servers=1,
        )
        self.user_id = "alice"
        self.context = self.rbt.create_external_context(
            name=f"test-{self.id()}",
            bearer_token=self.rbt.make_valid_oauth_access_token(
                user_id=self.user_id,
            ),
        )
        # Production creates the User front door via the MCP session hook;
        # tests trigger it manually.
        await UserServicer._auto_construct(self.context, state_id=self.user_id)

    async def asyncTearDown(self) -> None:
        await self.rbt.stop()

    async def _create_list(self, name: str = "Work") -> str:
        response = await User.ref(self.user_id).create_list(
            self.context, name=name
        )
        return response.list_id

    async def test_user_creates_a_list_and_sees_it_listed(self) -> None:
        list_id = await self._create_list("Groceries")

        response = await User.ref(self.user_id).lists(self.context)
        self.assertEqual(len(response.lists), 1)
        self.assertEqual(response.lists[0].id, list_id)
        self.assertEqual(response.lists[0].name, "Groceries")
        self.assertEqual(response.lists[0].task_count, 0)

    async def test_user_adds_tasks_and_sees_them_in_order(self) -> None:
        list_id = await self._create_list()
        await TodoList.ref(list_id).add_task(
            self.context, title="First", priority="high"
        )
        await TodoList.ref(list_id).add_task(self.context, title="Second")

        view = await TodoList.ref(list_id).get(self.context)
        self.assertEqual([t.title for t in view.tasks], ["First", "Second"])
        self.assertEqual(view.tasks[0].priority, "high")

        summary = await User.ref(self.user_id).lists(self.context)
        self.assertEqual(summary.lists[0].task_count, 2)
        self.assertEqual(summary.lists[0].completed_count, 0)

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

        summary = await User.ref(self.user_id).lists(self.context)
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
            self.context,
            title="Final",
            notes="with a note",
            priority="medium",
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

    async def test_another_user_cannot_access_my_list(self) -> None:
        list_id = await self._create_list()
        intruder_context = self.rbt.create_external_context(
            name=f"intruder-{self.id()}",
            bearer_token=self.rbt.make_valid_oauth_access_token(
                user_id="mallory",
            ),
        )

        with self.assertRaises(Aborted):
            await TodoList.ref(list_id).get(intruder_context)
        with self.assertRaises(Aborted):
            await TodoList.ref(list_id).rename(intruder_context, name="hacked")
