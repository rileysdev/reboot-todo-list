# Copilot instructions

This repository is operated by an autonomous coding loop. Copilot is the
loop's **only code reviewer**: every inline comment you leave is parsed into a
structured finding, and any surviving finding triggers a full revision round —
a fresh implementation session, a new PR, a new review. A trivial comment
costs an entire cycle of compute and latency. Make each comment worth a cycle.

## What a comment must contain

A concrete failure scenario: what input, event, or state produces what wrong
outcome. Comments are machine-parsed into (claim, evidence) findings, so state
the defect in one sentence and back it with the file/line or the failing
scenario.

## Only comment on

Issues likely to result in **bugs, misconfigurations, security problems, or
genuine confusion**.

## Do NOT comment on

- style, formatting, or naming taste
- wording preferences in comments/docs — unless the text is factually wrong
- hypothetical concerns with no plausible failure path in this repo
- suggestions that add machinery without preventing a nameable failure

## Scrutinize hardest

- changes under `.github/` or `.claude/` or to verification commands: in an
  autonomous loop, CI is merge authority and the `.claude/` hooks are the
  loop's liveness and convergence machinery — a change that weakens either
  can merge anything or blind the control plane
- swallowed errors and fail-open defaults: unknown or unreadable state must
  halt or skip, never pass
- claims in code comments or docs that the diff makes false

## Out of scope — never comment on these

- **`plans/`** — implementation plans committed by the control plane; they are
  instructions already executed, not review targets.
