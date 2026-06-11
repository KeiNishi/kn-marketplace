---
name: gamedev-debugging
description: This skill should be used when debugging a game bug, crash, glitch, freeze, desync, soft-lock, or visual artifact, or when the user mentions a bug that only happens sometimes, only at low or high FPS, only after loading a save, only in builds (not in the editor), or only on one platform. Covers frame-dependent bugs, physics/timestep issues, race conditions in async loading, state-machine corruption, save/load determinism, and platform-specific rendering differences. Triggers on phrases like "fix this bug", "the game crashes", "random crash", "can't reproduce", "heisenbug", "flickering", "objects fall through the floor", "tunneling", "physics goes crazy", "input feels different at high FPS", "save file is corrupted", "works in editor but not in build", "stuck in an animation state". Engine agnostic - works with Unity, Godot, Playdate, or custom engines.
---

# Game Debugging Discipline

Systematic root-cause debugging for game bugs. Game bugs are uniquely hostile to guesswork: they depend on frame timing, floating-point accumulation, asset load order, and platform quirks. Discipline beats intuition.

## The Iron Law

**NO FIX WITHOUT A REPRODUCED ROOT CAUSE FIRST.**

You may not change a line of game code as a "fix" until you can:
1. Reproduce the bug on demand (or have a captured failing case), AND
2. State the root cause as a specific, evidence-backed sentence ("X happens because Y"), not a guess ("maybe the timing is off").

If you cannot reproduce it, your job is to make it reproducible — that IS the debugging task. A fix applied to an unreproduced bug is a guess wearing a fix's clothing.

## Phase 1: Reproduce

Goal: make the bug happen deterministically, every time.

1. **Get the exact recipe**: steps, platform, build vs. editor, save file, hardware, frequency. Ask the user for anything missing (use the AskUserQuestion tool if available; otherwise ask in a plain message and wait).
2. **Pin down sources of nondeterminism** until the bug fires reliably:
   - **Fix the random seed** — seed all RNGs (gameplay, particles, AI) with a constant.
   - **Fix the timestep** — force a constant delta time or run the simulation in fixed-update-only mode; many "random" bugs are frame-rate-dependent.
   - **Frame-step** — pause and advance one frame at a time around the failure (editor pause/step, or a debug key that ticks one update).
   - **Capture state** — a save file, scene snapshot, or replay/input recording taken just before the failure is a reusable reproduction.
3. **Vary the suspected dimension**: if it "only happens sometimes", try forcing low FPS (vsync off + artificial load) and high FPS, slow asset loading (simulate slow disk), and repeated load/unload cycles. The condition that flips it from sometimes to always is your first clue.

A bug that reproduces 1 time in 20 is not yet reproduced. Keep tightening until it is reliable, or capture enough logging that one failing run tells the full story.

## Phase 2: Isolate

Goal: shrink the haystack before looking for the needle.

- **Bisect by disabling systems**: turn off AI, particles, audio, post-processing, networking — half at a time — until the bug disappears. The last system whose removal kills the bug owns it (or interacts with it).
- **Bisect by content**: minimal scene/level, one entity instead of fifty, default assets instead of project assets.
- **Bisect by history**: if it appeared "after some change", binary-search the commits or recent changes.
- **Log-then-binary-search**: add a small number of high-value log lines (state transitions, load completion, frame number, entity ID), run, then move the logs to bracket the failure point. Repeat — each pass halves the search space. Always log the frame counter or timestamp; ordering is usually the story.
- **Data bug or logic bug?** Reproduce the same logic with different data (another level, another save, another prefab/scene). Breaks everywhere → logic bug. Breaks with one asset → data bug; diff the failing asset/config against a working one instead of staring at code.

## Phase 3: Root-cause

Goal: one confirmed cause, not a list of suspects.

1. Form a single hypothesis: "X happens because Y."
2. Design the cheapest test that can DISPROVE it (a log line, an assertion, a forced value, a frame-step inspection).
3. Run it. If disproved, form the next hypothesis. One hypothesis at a time — never change two things per test.
4. Confirmed when you can predict the bug: "if I set Z, it will/will not happen" — and it does.

Common game root-cause families to check against the evidence:

| Symptom pattern | Likely family |
|---|---|
| Worse at low FPS, fast objects pass through walls | Missing delta-time scaling, or per-frame collision checks (tunneling) — needs continuous/swept collision or fixed timestep |
| Different behavior at high FPS | Logic in render update that belongs in fixed update; per-frame (not per-second) accumulation |
| Only after loading a scene/save, or first run after boot | Async load race: code uses an asset/object before its load completes; initialization order |
| Character stuck, animation never exits, ability locked | State machine corruption: missing transition, re-entrant event during a transition, state changed from two places |
| Save → load → subtle drift or corruption | Save/load nondeterminism: unserialized field, float precision, dictionary/iteration order, version mismatch |
| Only on one platform/GPU | Driver or precision differences, sRGB/color-space, texture compression, undefined shader behavior, case-sensitive file paths |

## Phase 4: Fix + Verify

1. Fix the root cause, minimally. No drive-by refactors in the same change.
2. Re-run the exact reproduction from Phase 1: the bug must be gone.
3. Re-enable everything you disabled in Phase 2 and reproduce again in the full game.
4. Remove temporary debug logging, forced seeds, and forced timesteps you added (or gate them behind an existing debug flag).
5. Check neighbors: other call sites of the fixed code, other states of the fixed state machine, old save files against new load code.
6. Record the bug pattern (symptom → root cause → fix) in the project's progress log or notes if the project keeps one (e.g. `docs_for_ai/TaskProgress.md`).

## Rationalization Table

| Excuse | Reality |
|---|---|
| "I can't reproduce it, but this change probably fixes it" | You have no way to know. Make it reproducible first; that is the task. |
| "It's just a timing issue, I'll add a small delay" | Delays shrink the race window; they never close it. Find the missing ordering guarantee. |
| "It only happens on the user's machine, must be their hardware" | Their machine is revealing a real assumption in your code (FPS, disk speed, driver). Simulate it. |
| "Adding a null check makes the error go away" | The null is the symptom. Why is it null at that moment? That is the bug. |
| "I'll clamp/limit the value so it can't explode" | The value exploding is evidence of broken math upstream. Clamping hides the evidence. |
| "It's random, so it must be the engine's fault" | Engine bugs exist but are rare. Fix the seed and timestep; "random" almost always becomes deterministic. |
| "I changed five things and it works now" | You don't know which change mattered or what the other four broke. Revert and re-apply one at a time. |
| "It stopped happening, so it's fixed" | A heisenbug that hid is not a bug that died. Without a root cause, it will return in a release build. |

## Red Flags — STOP

If you catch yourself doing any of the following, stop and return to the current phase:

- Writing a fix before reproducing the bug
- Adding a `sleep`/delay/frame-wait to "fix" ordering
- Adding try/catch, null checks, or clamps around the crash site without explaining why the bad value exists
- Retrying an operation until it succeeds
- Changing more than one variable per experiment
- Saying "probably", "maybe", or "should fix" in your root-cause statement
- Disabling the feature, the test, or the assertion that exposes the bug
- Blaming the engine, the platform, or cosmic rays without a disproof test
- Proposing "restart the editor / reimport assets" as the resolution rather than a diagnostic step

When stopped: state which phase you are in, what evidence you actually have, and run the next single experiment.

## Verification Checklist

Before declaring the bug fixed, verify ALL of the following:

- [ ] The bug was reproduced on demand (or via a captured failing case) before any fix was written
- [ ] The root cause is stated as a specific, evidence-backed sentence — and the evidence is in the conversation
- [ ] Exactly one hypothesis was confirmed by a test that could have disproved it
- [ ] The fix targets the root cause, not the symptom site
- [ ] The original reproduction no longer triggers the bug, with all systems re-enabled
- [ ] Frame-rate sensitivity checked: behavior is correct at both low and high FPS if timing was involved
- [ ] Temporary debug scaffolding (logs, fixed seeds, forced timestep) removed or gated
- [ ] No Red Flag pattern (delay, swallow, clamp, retry, disable) is part of the fix
- [ ] The bug pattern is recorded in the project's progress log/notes if one exists

If any item fails, the bug is not fixed. Return to the failing phase.
