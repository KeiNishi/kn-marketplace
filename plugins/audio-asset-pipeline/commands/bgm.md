---
name: bgm
description: Generate background music end to end - requirement, candidates on ACE-Step or MiniMax-Music3, loop post-processing, and review - honoring the asset's auto or manual mode.
argument-hint: "<description of the music> [--duration N] [--bpm N] [--mode auto|manual]"
---

# Audio Pipeline BGM Command

Take one music asset from a description to shipped, loop-exact files.

Follow the `audio-pipeline-overview` skill: read "THE TWO MODES" and run the
matching branch, then "Backend Routing Table" to choose between ACE-Step (the
default) and MiniMax-Music3. The generate stage is the `bgm-generation` skill;
the post stage is `loop-and-postprocess`.

Before routing anything to MiniMax-Music3, tell the user about its UI
attribution license and its render cost - both are in the routing table.
