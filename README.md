# Target-repo template

This directory mirrors, file for file, the **GitHub template repository** every
coding-loop project is created from. Copy its contents into a repo, mark that
repo as a template (Settings → Template repository), and base new projects on
it with "Use this template". (This README doubles as the template's README —
replace it with the project's own after creating a repo.)

Several pieces here are inherited from a predecessor autonomous loop
(in-person-queue) — its operational scar tissue, kept: the Copilot review
instructions, the turn-budget hook, rulesets-as-code, and the merge settings.

## What the template carries (files — inherited automatically)

- **`CLAUDE.md`** — the ground-truth preamble and eight code conventions
  (shared with the control plane's own CLAUDE.md), plus the loop operating
  contract: delegate investigation to subagents to keep the primary context
  clean, converge when the turn budget warns, the PR is the only exit, never
  touch the loop's own machinery. Projects append their own build conventions
  below it.
- **`.claude/settings.json`** — pins every session in the repo to the Fable
  model at `xhigh` effort (the highest level the `effortLevel` setting
  accepts — `ultracode` is session-only, per the model-config documentation),
  and wires the hooks for the Routine's Claude Code sessions: a `PreToolUse`
  guard plus two `PostToolUse` hooks.
  Caveat: a Routine uses the model chosen in its creation form on every run
  (per the routines documentation), so these keys govern headless and human
  sessions; whether a Routine respects the repo's `effortLevel` is
  undocumented.
- **`.claude/hooks/ci-only-guard.sh`** — deterministically blocks Docker
  invocations and Envoy downloads (`exit 2` on a `PreToolUse` match). The
  Routine sandbox has neither Docker nor network access to the Envoy release
  hosts; this hook stops a session from burning turns bootstrapping either.
  Pair it with a conftest guard in the project that forces the Reboot test
  harness to run without its Envoy proxy when no Envoy source is available
  (the suites run in full over gRPC — see reboot-todo-list's
  `backend/tests/conftest.py` for the pattern); CI, which has Docker, also
  exercises the Envoy-fronted path and is the merge authority.
- **`.claude/hooks/heartbeat.sh`** — POSTs `{"branch", "last_seen_ms"}` to the
  control plane's `/heartbeat` route (async, so it never blocks a tool call).
  Fail-open (a heartbeat is advisory; nothing may ever break the session) and
  silent on non-`claude/loop-*` branches, so a human's Claude session never
  posts. **Configure once, in the template:**
  `./set-heartbeat-url.sh https://<your-host>/heartbeat` stamps the control
  plane's public URL into the hook. Use a stable host (named cloudflared
  tunnel or reserved ngrok domain) — quick-tunnel URLs rotate per run, which
  would mean re-stamping every project repo.
- **`.claude/hooks/turn-budget.sh`** — injects converge-now warnings as a
  session nears its turn cap. A capped session dies mid-action with unpushed
  work lost, and the control plane then redispatches the task from scratch —
  the predecessor loop paid for that cycle repeatedly. The cap default (120)
  is PROVISIONAL until the Routines session contract is confirmed; override
  with `LOOP_MAX_TURNS`.
- **`.github/copilot-instructions.md`** — tunes the loop's only code reviewer:
  every inline comment must carry a concrete failure scenario (comments are
  machine-parsed into findings, and each surviving finding costs a full
  revision round), no style nits, scrutinize `.github/` changes hardest.
- **`.github/workflows/ci.yml`** — a placeholder pull-request workflow. The
  control plane's merge rule aggregates GitHub Actions check-runs on the PR
  head, so every project must run *something* on PRs; replace the placeholder
  echo with the project's real checks. The Envoy-dependent suites MUST run
  here: sessions skip them in the sandbox (see the CI-only guard above), so a
  placeholder CI would merge them untested.
- **`rulesets/*.json`** — rulesets-as-code, applied per repo by
  `setup-github.sh` (a ruleset is a repository setting, which "Use this
  template" does not copy).

## Per new repo, once: `./setup-github.sh <owner/repo>`

Applies the committed rulesets (Copilot auto-review on every PR targeting the
default branch — requires a Copilot Pro/Pro+/Max plan) and patches merge
settings: squash merging allowed (the control plane merges by squash) and
**auto-delete head branches** (each loop round dispatches a fresh branch;
without this they accumulate forever). Requires `gh` with admin access.

Then **onboard the repo in the control-plane dashboard** — task queue, project
brief, optionally the Routine endpoint/API key. When creating the Routine,
**select Fable in its model selector**: a Routine runs on the model chosen at
creation, not the repo's `.claude/settings.json` (which covers headless and
human sessions).

## Checklist / cautions

- **Branch protection**: the control plane merges PRs itself via the API. A
  required-human-approval rule on the default branch will make every merge
  fail — leave it off, or make requirements Copilot can satisfy.
- **The agent can edit its own checks** (predecessor's warning): a Routine
  could modify `.github/workflows/` or these hooks on its branch, and CI is
  merge authority. The Copilot instructions tell the reviewer to scrutinize
  exactly that; the only hard block is a *push ruleset* restricting
  `.github/**` to yourself (Settings → Rules → Push rulesets — not committed
  as JSON because push rulesets need a per-repo actor id).
- **Authorization**: the heartbeat (like the whole control plane) currently
  relies on `rbt dev`'s warn-and-allow authorization; a heartbeat token lands
  with the control plane's deferred auth work and will become a second
  stamped literal next to the URL.
