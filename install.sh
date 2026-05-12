#!/usr/bin/env bash
set -e

SKILL_DIR="$HOME/.claude/skills/query-review"
COMMANDS_DIR="$HOME/.claude/commands"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing query-review skill..."
mkdir -p "$SKILL_DIR"
cp "$REPO_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"

echo "Installing query-review commands..."
mkdir -p "$COMMANDS_DIR"
for cmd_file in "$REPO_DIR/commands/"*.md; do
  cmd_name="query-review-$(basename "$cmd_file")"
  cp "$cmd_file" "$COMMANDS_DIR/$cmd_name"
done

echo ""
echo "Done. Installed:"
echo "  Skill  → $SKILL_DIR/SKILL.md"
echo "  Commands → $COMMANDS_DIR/query-review-*.md"
echo ""
echo "Commands available in Claude Code:"
echo "  /query-review-file path/to/file.py"
echo "  /query-review-function fetch_orders in orders/helpers/query_helpers.py"
echo "  /query-review-scan payments/"
echo "  /query-review-check-n1 path/to/file.py"
echo "  /query-review-check-injection path/to/file.py"
echo "  /query-review-check-unbounded path/to/file.py"
echo "  /query-review-check-timeout path/to/file.py"