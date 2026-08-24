---
name: review-audio
description: Review an audio asset's post-stage outputs - decode, duration, loudness, true peak, silence and loop seam - and render a spectrogram of each shipped WAV.
argument-hint: "<slug> [--base <workspace>]"
---

# Audio Pipeline Review Command

Measure what was actually shipped and record a verdict.

Run (on Windows, use `py -3` if `python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/review_asset.py" $ARGUMENTS
```

Print the script output, then look at the spectrogram PNGs it wrote into
`audio-pipeline-output/<slug>/review/` - dropouts, band-limiting and dead bars
show up there and in no scalar check. Exit `0` is a pass; exit `2` means the
verdict is `fail`, and each failing check names its own remedy. Fix the cause,
never the check - see "Manifest-driven Resume" in the `audio-pipeline-overview`
skill.
