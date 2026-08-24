---
name: check-audio
description: Health check for the audio pipeline -- verifies Python, ffmpeg, the per-stack virtual environments, GPU and VRAM, disk space, and the private env file.
argument-hint: "[--stack sa3|acestep|minimax|all] [--json]"
---

# Audio Pipeline Check Command

Run the deterministic health checker before any long-running or first-time
generation.

Run (on Windows, use `py -3` if `python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" $ARGUMENTS
```

Print the script output first, then interpret the exit code: `0` means the
environment is healthy, `2` means one or more required checks failed and must be
fixed - usually with `/audio-asset-pipeline:setup-audio` - before generating.
Never print credential values.
