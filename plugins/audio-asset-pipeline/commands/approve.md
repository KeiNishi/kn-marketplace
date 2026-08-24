---
name: approve
description: Select which generated audio candidate to ship and record the user's approval. Manual-mode assets cannot run the post stage until this is done.
argument-hint: "<slug> [--select generate/cand-NN.wav] [--approve|--reject]"
---

# Audio Pipeline Approve Command

Record the two facts the post stage reads: which candidate was chosen, and
whether a human approved it.

Present every file in `audio-pipeline-output/<slug>/generate/` with its silence
measurements and let the user listen first, then run (on Windows, use `py -3` if
`python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/approve_asset.py" $ARGUMENTS
```

The gate is mechanical, not advisory - see "Approval Gates" in the
`audio-pipeline-overview` skill. Approving a candidate that is not on disk is
refused.
