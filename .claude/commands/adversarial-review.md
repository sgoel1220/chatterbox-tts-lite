Run an adversarial review of the current changes using Codex's model.

Execute this command and wait for it to complete (do NOT run in background):

```bash
CODEX_DIR="$(find "${CLAUDE_PLUGINS_DIR:-$HOME/.claude/plugins}/cache/openai-codex/codex" -name "codex-companion.mjs" -print -quit 2>/dev/null)" && node "$CODEX_DIR" adversarial-review --wait $ARGUMENTS
```

After it completes, read and report all findings. Then implement every actionable finding before proceeding. If any finding conflicts with the bead's intent, stop and ask the user — do not silently ignore it.
