#!/usr/bin/env bash
# Stamp the control plane's public heartbeat URL into the heartbeat hook:
#
#   ./set-heartbeat-url.sh https://your-control-plane-host/heartbeat
#
# Run once in the TEMPLATE repo — every project created from it inherits the
# stamped hook. If the control plane's host ever changes, re-run here and in
# each existing project (which is why a stable host is worth having; see
# README.md).

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "usage: $0 <control-plane-heartbeat-url>" >&2
    exit 1
fi

heartbeat_url="$1"
hook="$(dirname "$0")/.claude/hooks/heartbeat.sh"

case "$heartbeat_url" in
    https://*/heartbeat | http://*/heartbeat) ;;
    *)
        echo "expected an absolute URL ending in /heartbeat (the control" >&2
        echo "plane's route), got: $heartbeat_url" >&2
        exit 1
        ;;
esac

sed -i "s|^CONTROL_PLANE_HEARTBEAT_URL=.*|CONTROL_PLANE_HEARTBEAT_URL=\"$heartbeat_url\"|" "$hook"
grep "^CONTROL_PLANE_HEARTBEAT_URL=" "$hook"
