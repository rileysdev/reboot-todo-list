#!/usr/bin/env bash
# Liveness heartbeat to the coding-loop control plane (a Claude Code
# PostToolUse hook, so it fires every turn — before and after any git push).
#
# Fail-open by design: a heartbeat is advisory and nothing here may ever break
# the Routine's session — every failure path exits 0. Fires only on
# control-plane branches (claude/loop-*), so a human's Claude session in this
# repo never posts.
#
# The URL is a committed literal, set ONCE in the template repo and inherited
# by every project created from it — static config, deliberately not
# per-dispatch injection (see the control plane's docs/heartbeat-design.md).
# Use a stable host (a named cloudflared tunnel or reserved ngrok domain):
# quick tunnels mint a new URL per run, which would mean editing every repo.
# The control plane resolves the branch to its loop.

CONTROL_PLANE_HEARTBEAT_URL="https://REPLACE-WITH-YOUR-CONTROL-PLANE-HOST/heartbeat"

branch="$(git branch --show-current 2>/dev/null)" || exit 0
case "$branch" in
    claude/loop-*) ;;
    *) exit 0 ;;
esac

curl --silent --output /dev/null --max-time 5 \
    -X POST "$CONTROL_PLANE_HEARTBEAT_URL" \
    -H "Content-Type: application/json" \
    -d "{\"branch\": \"$branch\", \"last_seen_ms\": $(date +%s%3N)}" || true
