#!/usr/bin/env bash
# PostToolUse hook: warn a loop session as it approaches its turn-cap kill.
#
# Why: a session that hits its harness turn cap dies mid-action — no wrap-up,
# unpushed work abandoned. The control plane then sees a silent death and
# redispatches the task FROM SCRATCH, so everything unpushed is paid for twice
# (this exact cycle was observed in the predecessor loop: a session died at its
# cap with nothing landed). This hook makes the budget visible from inside:
# past a threshold it injects a converge-now warning after each tool call, so
# the session lands a shippable piece instead of being killed silently.
#
# Mechanics (verified against real transcripts in the predecessor loop): Claude
# Code invokes PostToolUse hooks with JSON on stdin (incl. transcript_path);
# printing {"hookSpecificOutput":{"hookEventName":"PostToolUse",
# "additionalContext":...}} on exit 0 injects the text into context. The
# transcript is JSONL with one line per assistant CONTENT BLOCK, so raw line
# counts overcount — turns = unique assistant message ids.
#
# Fail-open everywhere: this is advisory and must never break a session.

set -euo pipefail

# Only loop sessions run under a turn cap; stay silent for a human's session.
branch="$(git branch --show-current 2>/dev/null)" || exit 0
case "$branch" in
    claude/loop-*) ;;
    *) exit 0 ;;
esac

command -v jq >/dev/null 2>&1 || exit 0

input="$(cat)"
transcript="$(jq -r '.transcript_path // empty' <<<"${input}" 2>/dev/null || echo '')"
[ -n "${transcript}" ] && [ -r "${transcript}" ] || exit 0

# The Routine harness's turn cap. PROVISIONAL default until the Routines
# session contract is confirmed; override via env if the real cap differs.
limit="${LOOP_MAX_TURNS:-120}"
turns="$(jq -rs '[.[] | select(.type=="assistant") | .message.id] | unique | length' "${transcript}" 2>/dev/null || echo '')"
[[ "${limit}" =~ ^[0-9]+$ ]] && [[ "${turns}" =~ ^[0-9]+$ ]] || exit 0

remaining=$(( limit - turns ))
[ "${remaining}" -lt 0 ] && remaining=0

if [ "${remaining}" -le 8 ]; then
  # Critical zone: repeat on every tool call — the kill is imminent.
  msg="TURN BUDGET CRITICAL: ~${turns} of ${limit} turns used — ${remaining} left before a HARD KILL mid-action (no wrap-up; unpushed work is lost and the control plane redispatches this task from scratch). STOP new work NOW. Commit and push what exists and open the PR; state the unfinished remainder plainly in the PR body so the review round carries it forward."
elif [ "${remaining}" -le 25 ]; then
  # Warning zone: nudge every ~5 turns, not every tool call.
  [ $(( remaining % 5 )) -eq 0 ] || exit 0
  msg="TURN BUDGET WARNING: ~${turns} of ${limit} turns used. The session is hard-killed at ${limit} with no grace period — converge now. Finish the smallest shippable piece, run the checks, push, open the PR. Do not start anything new; if the task cannot finish in ~${remaining} turns, land what works and state the remainder in the PR body."
else
  exit 0
fi

jq -n --arg ctx "${msg}" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $ctx}}'
