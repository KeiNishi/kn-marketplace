---
name: setup-audio
description: Create or repair the per-backend Python environment (Stable Audio 3, ACE-Step, MiniMax-Music3) that the audio generate stage runs in.
argument-hint: "[--stack sa3|acestep|minimax|all] [--check-only]"
---

# Audio Pipeline Setup Command

Build the virtual environment for a generation backend under
`~/.claude/audio-pipeline/venvs/<stack>`. Nothing is installed into the game
workspace and nothing is written into the repository.

Run (on Windows, use `py -3` if `python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/setup_env.py" $ARGUMENTS
```

Tell the user the download size and the expected wait before starting, then
verify with `/audio-asset-pipeline:check-audio`. Secrets such as `HF_TOKEN`
belong in `~/.claude/audio-pipeline/.env`, never in the repository or the
manifest.
