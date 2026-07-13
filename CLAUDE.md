# Ground truth

There is no greater sin than asserting as fact something which is factually
incorrect. All factual assertions must be grounded in reality. If you have not
verified a claim — against the code, the references, or a documented source —
say so plainly and mark it as unverified. Never dress a guess as a fact, and
never invent a capability, API, or product to make an idea work.

In this repo that includes the PR body: a claim of verification that did not
happen poisons the loop's review, and the next revision round inherits the
lie. If tests fail, say so with the output.

# Conventions

## 1. No backwards compatibility (until this project first deploys)

While nothing is deployed, incompatibility costs nothing. Rename API/schema
fields and methods freely for logical naming — no shims, aliases, or
wire-compat. Once real users or data exist, this convention is renegotiated.

## 2. One name — and one home — per concept

Each concept has exactly one name, used in code, comments, and prose. A value
keeps that name across every hop — return, variable, parameter, stored field —
unless genuinely transformed; one concept under several names
(`verdict()`→`decision`→`result`) is a defect. Same for values: define a fact
(default, interval, vocabulary) once and read it through one path. Never
mirror one knob in both an env var and a config field.

Don't alias imports (`import x as y`) — an alias mints a second name for
something that already has one. Import a module by its real name and reference
it through that. On an import-name conflict, disambiguate with the package
namespace that already exists, never by minting an alias.

## 3. Say what you mean — no metaphors, no opaque labels

Name the exact concept: not `gate` but `stopping_condition`, `invariant`,
`precondition`, or `authority`. Refer to things by name, never by a code or
index that forces a lookup. More words are welcome when they add specificity;
shorthand the reader must decode — metaphor or index — is not.

## 4. Descriptive names — no abbreviations, nothing generic

Spell words out (`observation`, not `obs`); length is irrelevant within the
width limit. Reject placeholders — `objs` is lazy, `objects` no better
(everything is an object). Name what it holds: `blocker_findings`,
`pending_task_ids`.

## 5. Comments: why, not what

Comment only what the code can't say — rationale, invariants, non-obvious
constraints. A comment restating the next line is duplicated logic that rots;
delete it.

## 6. No speculative generality — delete on sight

No field, parameter, branch, or knob without a concrete use. Tolerate
duplication until the third occurrence before abstracting. Unused code is a
false claim about the system — delete it.

## 7. Make illegal states unrepresentable

Values from a fixed vocabulary (status, severity, phase) get an
`enum`/`Literal`/union type so a typo won't construct. Parse string→type once
at the boundary, then trust it downstream. (Reboot projects: schema fields are
protobuf scalars with zero defaults — parse at the Python logic/servicer
layer, not the field definition.)

## 8. Errors fail fast and narrow

No bare `except`, no swallowing into a default. Catch the one error you can
handle; let the rest surface where they occur. Better: design the error out of
existence. An intentional no-op catch names its exact exception and says why.

# The autonomous loop: how sessions in this repo work

This repository is operated by an autonomous coding loop. A control plane
dispatches you (a Claude Code session) onto a `claude/loop-*` branch with one
task; your instructions are the task description, the findings to fix (on a
revision round), and an implementation plan — all handed to you in the dispatch
payload. Commit the plan to `plans/task-<K>.md` on your branch as your first
commit (so it rides in the PR for review), then implement it. The control plane
never writes to this repository except to merge your PR — everything you push
goes through the branch you were given.

## Keep your context clean: investigate through subagents

Delegate exploration to subagents (the Task/Agent tool) and keep your primary
context for decisions and edits: locating code across many files, tracing how
a subsystem works, researching an unfamiliar library or error. Ask the
subagent for conclusions — file paths, the relevant invariant, the answer —
never for file dumps. You run under a hard turn cap (see below); a session
that spends forty turns grepping is the session that gets killed
mid-implementation. Read directly only what you are about to change or must
verify yourself.

## Converge when warned: the turn budget is real

Your session is hard-killed at its turn cap with no grace period — unpushed
work is lost, and the control plane redispatches the task from scratch, so
everything unpushed is paid for twice. A hook injects TURN BUDGET warnings as
you approach the cap. When warned: stop starting things, finish the smallest
shippable piece, run the checks, commit, push, open the PR. State any
unfinished remainder plainly in the PR body — the revision round carries it
forward.

## The pull request is your only exit

Work happens only on the branch you were dispatched to; never push to any
other branch, never merge anything. When the work is ready (or the turn
budget forces convergence), push and open a PR against the default branch —
the control plane observes it, waits for CI and the Copilot review, and
merges or dispatches a revision round itself. The PR body must state: what
was done, how it was verified (paste real command output), and anything
unfinished. On a revision round, address every finding you were dispatched
with — each unresolved finding costs another full round, and a blocker that
survives a round escalates to a human.

## When you cannot proceed: ask, don't guess

If the task cannot be finished without the human — a required resource is
missing (an API key, a paid account, credentials you cannot assume) or it
demands a decision between genuinely diverging approaches — do NOT guess past
it or silently pick a side. Push whatever partial work exists and open the PR
with a fenced `needs-attention` block in its body: a `kind:` line
(`blocked_on_resource` or `decision_needed`) followed by the exact question.

    ```needs-attention
    kind: blocked_on_resource
    A Stripe API key is required to finish the checkout wiring; which
    account should this use?
    ```

The control plane pauses the task on your question and routes it to the human;
their answer comes back to the next attempt. Reserve this for real blocks, not
ordinary uncertainty you can state as an assumption and proceed.

## Never modify the loop's own machinery

Do not edit anything under `.github/` or `.claude/` — CI is merge authority
and those files are the loop's governance; the reviewer is instructed to
scrutinize such changes hardest. Do not edit `plans/` — plans are the control
plane's record. If the plan or a finding is wrong, say so in the PR body
instead of working around it silently.

---

Projects append their own build conventions below this line.
