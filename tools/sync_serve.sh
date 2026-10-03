#!/usr/bin/env bash
# Keeps the served brain-sim worktree (~/.cache/brain-sim-serve, the process on port 8000)
# at master's HEAD whenever that is safe. The server reads ui/ from disk on every request
# (StaticFiles), so UI and record changes reach the page without a restart and the running
# network is untouched. Changes to brainsim/, server/ or run.py need a process restart, which
# resets the running network: those are only flagged here, never done.
#
# Installed as .git/hooks/post-commit by `tools/sync_serve.sh --install`; acts only for commits
# on master in the main worktree (linked worktrees and branches are ignored). `--force` runs
# the sync by hand from anywhere.
set -u
unset GIT_DIR GIT_WORK_TREE GIT_INDEX_FILE
REPO=/home/lucas/Workspaces/brain-sim
SERVE=/home/lucas/.cache/brain-sim-serve

if [ "${1:-}" = "--install" ]; then
  printf '#!/bin/sh\nexec %s/tools/sync_serve.sh\n' "$REPO" > "$REPO/.git/hooks/post-commit"
  chmod +x "$REPO/.git/hooks/post-commit"
  echo "sync_serve: installed $REPO/.git/hooks/post-commit"
  exit 0
fi

if [ "${1:-}" != "--force" ]; then
  top=$(git rev-parse --show-toplevel 2>/dev/null)
  branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [ "$top" != "$REPO" ] || [ "$branch" != "master" ]; then
    exit 0
  fi
fi

[ -d "$SERVE" ] || { echo "sync_serve: $SERVE missing; nothing served to sync" >&2; exit 0; }
target=$(git -C "$REPO" rev-parse master)
served=$(git -C "$SERVE" rev-parse HEAD)
[ "$served" = "$target" ] && exit 0

if [ -n "$(git -C "$SERVE" status --porcelain)" ]; then
  echo "sync_serve: $SERVE has local changes; NOT synced" >&2
  exit 0
fi
if ! git -C "$REPO" diff --quiet "$served" "$target" -- brainsim server run.py; then
  echo "sync_serve: brainsim/, server/ or run.py changed between served ${served:0:7} and master ${target:0:7}." >&2
  echo "sync_serve: the running process must be restarted to serve master (that resets the running network); UI NOT synced." >&2
  exit 0
fi
if git -C "$SERVE" checkout -q --detach "$target"; then
  echo "sync_serve: served page now at ${target:0:7} (process untouched)"
else
  echo "sync_serve: checkout of ${target:0:7} in $SERVE failed" >&2
fi
exit 0
