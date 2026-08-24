---
name: se
description: Generate a sound effect end to end - requirement, candidates on Stable Audio 3, post-processing, and review - honoring the asset's auto or manual mode.
argument-hint: "<description of the sound> [--duration N] [--mode auto|manual]"
---

# Audio Pipeline SE Command

Take one sound effect from a description to shipped files.

Follow the `audio-pipeline-overview` skill: read "THE TWO MODES" first and run
the branch that matches the asset's mode (auto infers the requirement and never
stops; manual elicits it, presents 3 candidates, and waits for the user's
choice). The generate stage itself is the `se-generation` skill; the post stage
is `loop-and-postprocess`.

Stop and report if `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" --stack sa3`
reports a failed check.
