# Plan: Add subtasks to TODO items with cascading completion

## Goal
Enable users to create subtasks under a TODO item and display them visually as related (indented). Implement cascade rules:
- When a parent TODO is checked, all of its subtasks are checked.
- When all subtasks are checked, the parent TODO is automatically checked.
- When any subtask is unchecked, the parent TODO is automatically unchecked.
- When a parent TODO is unchecked, all of its subtasks are unchecked (assumption to ensure the parent can be unchecked even if all children were checked).

## Assumptions
- The repository contains a TODO app (likely React/Next.js on the frontend). There may or may not be a backend/API.
- There is an existing TODO entity/model with at least: id, title/text, completed (boolean), and persistence (localStorage or backend DB via an API).
- We will support a single level of nesting (one parent with its subtasks). If a deeper hierarchy exists or is desired later, this design can extend naturally by using a parentId.
- If there is a backend and DB, we will prefer a normalized model with parentId. If the app is client-only (localStorage), we can either use a parentId in a flat list or embed subtasks in a parent’s subtasks array. Prefer parentId if list operations already exist; otherwise, embedding is acceptable. Steps below describe both; choose the path that matches the repo.

Where the repo specifics are unclear, look for:
- Frontend components: files like components/TodoItem(.tsx/.jsx), components/TodoList, pages/index(.tsx) or app/page(.tsx), etc.
- State management: Redux slice (e.g., src/store/todosSlice.ts), Zustand, Context, or simple component state.
- Persistence: services/api files (e.g., services/todos.ts), API routes (Next.js /pages/api/todos or /app/api/todos), or localStorage utilities.
- Data model/types: types/Todo.ts, models/Todo.ts, Prisma schema.prisma, Sequelize models, or Mongoose schemas.
- Tests: Jest/RTL in __tests__ or *.test.(ts|tsx|js), or E2E (Cypress/Playwright).

## Implementation Steps

1) Audit the codebase
- Identify the TODO data model/type and where completion toggle and create/delete are implemented.
- Identify how the list is rendered and how a single TODO item UI is composed.
- Determine persistence strategy:
  - Backend present? Identify ORM and migration system (Prisma/Mongoose/Sequelize/Knex), and the REST/GraphQL endpoints for todos.
  - Client-only? Identify localStorage helper(s) and state management (Redux/Context/hooks).

2) Update the data model to support subtasks
Option A (preferred when a backend/DB exists):
- Add a nullable parentId field to the Todo model.
  - Migration: add parentId referencing the same table (self-referential foreign key). Ensure onDelete: CASCADE (or implement manual cascade on delete to prevent orphan subtasks).
  - Update ORM model/types to include parentId?: string | null (or number | null depending on id type).
- Adjust any DTOs and API validators to accept parentId.
Option B (client-only or simplest path):
- Extend the Todo type to include subtasks?: Array<{ id: string; title: string; completed: boolean }>. Keep id generation consistent with existing todos.
- Initialize subtasks to [] for existing todos when loading from storage.

3) API changes (if a backend exists)
- Creation:
  - Allow creating a subtask via existing POST /todos by including parentId in payload.
  - Ensure GET endpoints return subtasks grouped with their parent. Two approaches:
    1) Return a flat list with parentId and let the client group, or
    2) Return parents with embedded subtasks. Choose the approach consistent with existing responses. If responses are flat, keep them flat and group on the client.
- Toggle completion:
  - Implement cascade logic in the backend service layer for atomicity:
    - When toggling a parent to completed=true, set completed=true for all children (by parentId) in the same transaction.
    - When toggling a parent to completed=false, set completed=false for all children.
    - When toggling a subtask, recompute the parent’s completed as: completed = all(subtasks.completed). If any subtask is false, set parent=false.
- Deletion (optional but recommended):
  - When deleting a parent, also delete its subtasks (cascade) or forbid deletion until subtasks are removed. Prefer cascade.

4) State management changes
- Update types to include parentId (Option A) or subtasks array (Option B).
- Add selectors/helpers:
  - getSubtasks(parentId)
  - areAllSubtasksComplete(parentId)
- Add actions/handlers:
  - addSubtask(parentId, title)
  - toggleParentWithCascade(parentId, completed)
  - toggleSubtask(id, completed) that recomputes the parent’s completed status.
- If there is Redux or similar, add corresponding reducers and thunk/sagas to call APIs. If local state, implement the same logic in the component or a custom hook.
- Ensure no infinite loops: parent toggle triggers children update; child toggle triggers parent recompute but not vice-versa unless state actually changes.

5) UI changes
- In the TodoItem component:
  - Render the parent TODO as before.
  - Render its subtasks below, indented visually (e.g., a left padding/margin). Keep accessibility (nested list or role=listitem for subtasks).
  - Add an "Add subtask" control on each parent row:
    - Either an inline input that appears when the user clicks a "+ Subtask" button, or a small text field with an Add button.
    - On submit, call addSubtask with the parentId (Option A) or push into the parent’s subtasks (Option B), then persist.
- Checkbox behaviors:
  - On parent checkbox change:
    - If checked -> toggleParentWithCascade(parentId, true)
    - If unchecked -> toggleParentWithCascade(parentId, false)
  - On subtask checkbox change:
    - toggleSubtask(id, completed)
    - After updating the subtask, recompute parent status and update/persist if needed.
- Optional but helpful: show a small counter like (3/5) next to the parent to indicate progress.

6) Persistence layer updates
- Backend present:
  - Update services/repositories to handle filtering by parentId and bulk updates for cascade operations.
  - Ensure endpoints used by the UI return consistent shapes; add any necessary includes/expansions.
  - Wrap cascade updates in a transaction to keep parent/children in sync.
- Client-only/localStorage:
  - Update serialization/deserialization to include parentId or subtasks.
  - For existing data, when loading, default missing subtasks to [] (Option B) or default parentId to null (Option A flat list).

7) Edge cases and decisions (document in code comments)
- Unchecking parent unchecks all children (chosen to avoid conflict with the rule that a parent auto-checks when all children are checked; otherwise, unchecking the parent while children are all checked would immediately re-check it).
- Adding a subtask to a completed parent will set parent to unchecked (since not all subtasks are complete). This follows the auto-check rule and keeps logic consistent.
- Prevent a subtask from having its own subtasks in this iteration (single level). If parentId is used, enforce at UI level by only offering "Add subtask" on items with parentId == null.
- Deletion: if deleting a parent, delete its subtasks as well (backend cascade or client logic). If deleting a subtask, only that subtask is removed, and parent completion is recomputed.

8) Styling
- Add a CSS class for subtasks with indentation (e.g., padding-left or a nested list style).
- Ensure keyboard accessibility: tab order allows reaching subtask controls; label/checkbox associations are correct.

9) Tests
Add/extend tests matching the project’s test stack. Look for existing patterns and place tests accordingly.
- Unit tests for logic helpers:
  - toggleParentWithCascade(true) marks all children completed.
  - toggleParentWithCascade(false) marks all children not completed.
  - toggleSubtask: parent becomes completed when all children completed; becomes not completed when any child not completed.
- Component tests (React Testing Library):
  - Rendering: subtasks appear indented under parent.
  - Interactions: checking parent checks all subtasks; unchecking parent unchecks all subtasks; checking all subtasks auto-checks parent.
  - Adding a subtask: creates under the correct parent and affects parent completion as described.
- API tests (if backend):
  - POST with parentId creates a child.
  - Toggling parent cascades to children (verify children states).
  - Toggling a child recomputes parent.
  - Deleting parent deletes children.
- E2E (if present):
  - User flow: create parent, add subtasks, check/uncheck as per rules and verify UI reflects correctly.

10) Manual verification checklist
- Create a TODO, add two subtasks. Verify subtasks display under the parent, indented.
- Check the parent: both subtasks become checked; parent shows checked.
- Uncheck the parent: both subtasks become unchecked; parent unchecked.
- Check only one subtask: parent remains unchecked.
- Check all subtasks: parent automatically becomes checked.
- Add a new subtask to a completed parent: new subtask is unchecked and parent becomes unchecked.
- Refresh the page: structure and states persist correctly.

## Notes for the implementer
- Favor a normalized model with parentId when a backend exists; it is simpler to extend later and allows multi-level trees if needed.
- If the app uses a flat list with sorting, ensure subtasks render immediately under their parent. You can compute the nested structure in a selector: group by parentId, then map parents and their children.
- Be careful to avoid race conditions in async updates; prefer backend to perform cascade updates atomically. If client-only, batch state updates together and then persist once.
- Document the chosen assumptions in code comments and, if applicable, in a README update.
