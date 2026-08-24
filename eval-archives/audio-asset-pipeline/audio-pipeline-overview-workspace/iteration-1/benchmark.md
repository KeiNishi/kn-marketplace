# Skill Benchmark: audio-pipeline-overview

**Model**: sonnet (subagent)
**Date**: 2026-08-24T16:52:42Z
**Evals**: 1, 2, 3 (1 run each per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 87% +/- 23% | 53% +/- 42% | +0.33 |
| Time | 146.9s +/- 30.2s | 218.8s +/- 79.2s | -71.9s |
| Tokens | 101010 +/- 17913 | 115852 +/- 39707 | -14842 |

## Per-eval results

| Eval | With Skill | Without Skill |
| --- | --- | --- |
| eval-approval-gate-shortcut | 4/4 | 4/4 |
| eval-auto-mode-se | 5/5 | 1/5 |
| eval-manual-mode-bgm | 3/5 | 2/5 |

## Notes

- eval-approval-gate-shortcut is non-discriminating: both arms scored 4/4. The manual-mode gate is enforced in post_process.py itself, which refuses with a message naming approve_asset.py, so the baseline reached the same answer by running the command and reading the refusal. The eval measures the code, not the skill - rewrite or drop it in iteration 2.
- eval-auto-mode-se is where the skill earns its keep (1.00 vs 0.20). The baseline broke auto mode's defining contract by ending its answer with two clarifying questions, and it skipped review_asset.py entirely - it never mentions the review stage anywhere - while presenting the asset as finished.
- eval-manual-mode-bgm fails assertion 5 in BOTH arms and cannot do otherwise: that assertion requires the post and review stages to run after a human approval, which a non-interactive eval can never produce. Split the eval, or scaffold it with a pre-approved asset, before reading anything into the 0.60/0.40 numbers.
- Both arms of eval-manual-mode-bgm also failed the candidate-presentation assertion the same way: the per-candidate silence figures were on screen in the generate output and neither run carried them into the message to the user. That is a real gap in the skill, not an eval artifact - the skill says to present them but does not show what that looks like.
- The skill is consistently FASTER, not slower: 146.9 s mean against 218.8 s, and 101 k tokens against 115.9 k. The baseline arms spent their extra time reading the plugin's Python source to reconstruct what the skill states outright.

## Methodology

- One run per configuration per eval, which is what the other archives in this
  repository actually contain (their `runs_per_configuration: 3` is a hardcoded
  field in the upstream aggregation script, not a description of the runs).
  With one run each, the +/- figures in the summary table are the spread
  ACROSS the three evals, not run-to-run variance - nothing here says anything
  about how stable a single eval is.
- Executors and graders were subagents on the small model. Each eval was graded
  by one grader that saw both arms and applied the same bar to each.
- `time_seconds` and `tokens` are the runner's own measurements of each agent,
  not the agents' self-reports.
- Every run was forced into `AUDIO_PIPELINE_DRY_RUN=1`, so no GPU generation
  happened inside an eval agent and every candidate file is a placeholder tone.
  Graders were told never to fail an assertion for that reason. The placeholder
  `.wav`/`.ogg`/`.png` files are listed in each run's `generated-files.txt`
  rather than archived.
- **What "without_skill" means here.** The plugin's executable code is installed
  on the benchmark machine and the baseline agents were free to read and run it,
  exactly as a user with the plugin installed but no skill loaded would be. They
  were not given the skill. One baseline run went looking and read the SKILL.md
  files anyway; that run was discarded and re-run under an explicit rule
  forbidding anything under `skills/`. The remaining baselines were checked for
  the same contamination and were clean. This is a conservative baseline: it can
  only make the deltas smaller, never larger.
