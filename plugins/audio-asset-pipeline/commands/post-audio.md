---
name: post-audio
description: Run the post stage on the selected audio candidate - trim, bar-exact loop with a seam crossfade, EBU R128 normalization, and WAV/OGG export.
argument-hint: "<slug> [--candidate generate/cand-NN.wav] [--skip-loop] [--target-rate 44100|48000]"
---

# Audio Pipeline Post Command

Turn the selected candidate into the files a game engine loads.

Run (on Windows, use `py -3` if `python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/post_process.py" $ARGUMENTS
```

The workflow, the flags and every failure this stage can report are in the
`loop-and-postprocess` skill. A manual-mode asset must be approved first
(`/audio-asset-pipeline:approve`); an auto-mode asset with several candidates
picks one itself and logs the choice.
