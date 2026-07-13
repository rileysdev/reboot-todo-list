#!/usr/bin/env bash
# Per-new-repo GitHub configuration — the things "Use this template" cannot
# carry, because they are repository settings rather than files:
#
#   ./setup-github.sh <owner/repo>
#
# 1. Applies every ruleset under rulesets/ (committed JSON — rulesets-as-code).
#    rulesets/copilot-review.json auto-requests a Copilot code review on every
#    PR targeting the default branch; the control plane's review phase waits on
#    that review, so without it every review waits out the full timeout.
#    Requires a Copilot plan that includes code review (Pro/Pro+/Max). Note:
#    GitHub couples the copilot_code_review rule to "require a PR before
#    merging" (observed in the predecessor loop's setup).
# 2. Patches merge settings: squash merging allowed (the control plane merges
#    every PR by squash) and head branches auto-deleted on merge (each loop
#    round dispatches a fresh branch; without this they accumulate forever).
#
# Requires `gh` authenticated with admin access to the repo.

set -euo pipefail

if [ $# -ne 1 ]; then
    echo "usage: $0 <owner/repo>" >&2
    exit 1
fi

repo="$1"
rulesets_directory="$(dirname "$0")/rulesets"

for ruleset in "$rulesets_directory"/*.json; do
    echo "applying ruleset $(basename "$ruleset")..."
    gh api "repos/$repo/rulesets" --method POST --input "$ruleset"
done

echo "patching merge settings (allow squash, auto-delete head branches)..."
gh api "repos/$repo" --method PATCH \
    --field allow_squash_merge=true \
    --field delete_branch_on_merge=true

echo "done: $repo is configured for the control plane"
