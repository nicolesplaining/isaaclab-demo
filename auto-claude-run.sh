#!/usr/bin/env bash
# Launch Claude Code under auto-claude with the allow-all policy (hands-off).
# Usage: ./auto-claude-run.sh [extra claude args...]
exec ~/.local/bin/auto-claude \
  -policy ~/.config/auto-claude/policy.yaml \
  -log-dir ~/auto-claude-logs \
  -- claude "$@"
