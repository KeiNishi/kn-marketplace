# Skill Benchmark: se-generation

**Model**: sonnet (subagent)
**Date**: 2026-08-24T16:52:42Z
**Evals**: 1, 2, 3 (1 run each per configuration)

## Summary

| Metric | With Skill | Without Skill | Delta |
|--------|------------|---------------|-------|
| Pass Rate | 87% +/- 12% | 47% +/- 46% | +0.40 |
| Time | 193.8s +/- 21.7s | 298.9s +/- 59.4s | -105.1s |
| Tokens | 86618 +/- 10781 | 132166 +/- 20177 | -45548 |

## Per-eval results

| Eval | With Skill | Without Skill |
| --- | --- | --- |
| eval-door-creak | 5/5 | 5/5 |
| eval-footstep-variations | 4/5 | 1/5 |
| eval-medium-model-request | 4/5 | 1/5 |

## Notes

- eval-door-creak is non-discriminating on its current assertions (5/5 both arms): generating one sound effect is reachable from the argparse help alone. The visible difference was prompt hygiene - the baseline wrote 'no music, no voice' into the positive prompt and never used --negative-prompt at all - and no assertion checks that. Add one.
- eval-medium-model-request is the sharpest result (0.80 vs 0.20). The baseline read generate_sa3.py's source, concluded from the auto-routing that 'medium' is a BGM-only checkpoint, and silently substituted small-sfx for the user's explicit instruction. It never ran doctor.py and never mentioned Flash Attention 2. The source alone genuinely misleads here; the skill's model table is what prevents the wrong conclusion.
- eval-footstep-variations separates on structure rather than wording (0.80 vs 0.20): the skill's Variation Batches section produces one asset with five seeded candidates, while the baseline reasoned from the source that --candidates is for picking a best take and built five separate assets with five different prompts - the exact thing the skill warns against, because it yields five unrelated sounds instead of five takes of one. The baseline then presented them as ready to ship, with no instruction to audition.
- The with_skill arm's one miss is worth fixing in the skill: it read the sentence about re-generation appending rather than overwriting candidates and still did not pass it on to the user.
- Same shape as the overview skill: with_skill is faster and cheaper, 193.8 s and 87 k tokens against 298.9 s and 132 k. Reconstructing the skill's knowledge from the Python source costs more than reading it.
- The first without_skill run of this eval was discarded and re-run: that agent found and read the plugin's SKILL.md files directly, so it was not a baseline at all. The replacement was explicitly forbidden to open anything under skills/. See the methodology note below.

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
