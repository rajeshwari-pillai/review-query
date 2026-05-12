#!/usr/bin/env bash
set -e

SKILL_DIR="$HOME/.claude/skills/query-review"

echo "Uninstalling query-review..."

if [ -d "$SKILL_DIR" ]; then
  rm -rf "$SKILL_DIR"
  echo "Done. query-review removed from $SKILL_DIR"
else
  echo "query-review is not installed at $SKILL_DIR"
fi