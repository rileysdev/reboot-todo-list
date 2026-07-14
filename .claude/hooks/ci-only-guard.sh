#!/usr/bin/env bash
# PreToolUse guard: the Routine sandbox has no Docker and no way to download
# an Envoy binary (the network policy blocks the release hosts), so any
# attempt to bootstrap either is wasted turns. Block those command classes
# outright and point the session at the policy: Envoy-dependent test suites
# are CI-only.
#
# Fail open on anything unexpected — a broken hook must never break the
# session (exit 0 allows the tool call; exit 2 blocks it and shows stderr to
# the session).

INPUT=$(cat) || exit 0

COMMAND=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    print(json.load(sys.stdin).get("tool_input", {}).get("command", ""))
except Exception:
    pass
') || exit 0

[ -z "$COMMAND" ] && exit 0

if printf '%s' "$COMMAND" | grep -qE '(^|[;&| ])docker([ ;&|]|$)|envoyproxy|getenvoy|tetratelabs|func-e|(curl|wget)[^;&|]*envoy'; then
  echo "Blocked by repo policy: Docker and Envoy are unavailable in this sandbox and must not be bootstrapped. Envoy-dependent test suites are CI-only — run the checks that work here (type checkers, frontend builds, Envoy-free pytest suites) and state in the PR body which checks are deferred to CI." >&2
  exit 2
fi

exit 0
