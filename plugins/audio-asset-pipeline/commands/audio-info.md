---
name: audio-info
description: Print the pipeline.json status for one audio asset -- stage statuses, backend, candidates, selection and approval, outputs, and the review verdict.
argument-hint: "<slug>"
---

# Audio Pipeline Info Command

Print the current manifest status for one asset. Require `<slug>` as the first
argument; if it is missing, print
`Usage: /audio-asset-pipeline:audio-info <slug>` and stop.

Read `audio-pipeline-output/<slug>/pipeline.json`. If it is missing, print
`No pipeline.json found for <slug>. Run /audio-asset-pipeline:init-audio first.`
and stop.

Print the header fields `slug`, `assetType`, `mode`, `dryRun`, `updatedAt`, then
a table of the four stages:

```text
Stage        Status     Detail
requirement  done       bgm, 30s, loop, -16 LUFS
generate     done       acestep, 3 candidates, selected cand-01, approved false
post         done       15 bars, 25.714s, -16.00 LUFS, seam 0.013
review       failed     verdict fail: duration
```

Take each row from `stages.<stage>`. For `post` use `loopProcessing` and
`normalize`; for `review` use `verdict` and the names of any failing `checks`.
Print `-` where a field is not recorded, and add an indented line for
`failureKind` when a stage has one. Then say which stage runs next, following
"Manifest-driven Resume" in the `audio-pipeline-overview` skill.
