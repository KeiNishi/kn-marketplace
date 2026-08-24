---
name: init-audio
description: Initialize the manifest for one audio asset (BGM or sound effect) before running the generate, post, or review stages.
argument-hint: "<slug> --type bgm|se [--mode auto|manual] [--prompt ...] [--duration N]"
---

# Audio Pipeline Init Command

Create `audio-pipeline-output/<slug>/pipeline.json` for a new asset. The mode
chosen here decides whether the pipeline stops for approval later, so pick it
deliberately: `manual` asks and waits, `auto` never does.

Run (on Windows, use `py -3` if `python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/init_asset.py" $ARGUMENTS
```

Then follow the `audio-pipeline-overview` skill: "THE TWO MODES" for what to ask
(or infer) before this runs, and "Stage Order" for what comes next.
