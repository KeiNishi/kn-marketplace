# Codex CLI Concept Backend

## Contents

- [Overview](#overview)
- [Selection Precedence](#selection-precedence)
- [Auto Detection](#auto-detection)
- [Forcing the Codex Backend](#forcing-the-codex-backend)
- [Runtime Failure Policy](#runtime-failure-policy)
- [Reference Chaining](#reference-chaining)
- [Manifest Fields](#manifest-fields)
- [Usage Limit Cost Note](#usage-limit-cost-note)
- [Sandboxing](#sandboxing)
- [Prompt Contract](#prompt-contract)
- [Provenance Verification](#provenance-verification)
- [Dry-Run Mode](#dry-run-mode)

## Overview

`scripts/concept_openai.py` (Stage 1) supports two image-generation backends,
resolved by `scripts/_codex_backend.py`'s `resolve_backend`:

- **codex** — shells out to `codex exec` per angle, using the Codex CLI's
  built-in `gpt-image-2` image tool. Covered by an active ChatGPT
  subscription; no `OPENAI_API_KEY` needed.
- **openai** — the OpenAI Images API (`OPENAI_API_KEY` from
  `~/.claude/3d-pipeline/.env`), pay-per-use. Behavior is unchanged from
  before this feature existed.

## Selection Precedence

Highest to lowest:

1. `--backend {auto,codex,openai}` CLI flag.
2. `PIPELINE_CONCEPT_BACKEND` environment variable (`codex`, `openai`, or
   `auto`).
3. Auto detection (see below).

## Auto Detection

Auto mode picks **codex** when both are true:

- The `codex` CLI is found on `PATH`.
- `codex login status` reports `Logged in using ChatGPT` (subscription auth).

Otherwise it picks **openai**, silently — this is the same behavior the
script had before the codex backend existed, so existing automation and
dry-run fixtures are unaffected.

An API-key Codex login (rather than a ChatGPT subscription login) does
**not** count as an active subscription and does not trigger the codex
backend in auto mode.

## Forcing the Codex Backend

Passing `--backend codex` (or setting `PIPELINE_CONCEPT_BACKEND=codex`) skips
auto detection and requires codex to work:

- If the codex CLI is missing from `PATH`, or the subscription is not
  active, this is treated as a **user error**: the script exits with the
  user-error exit code and the concept stage is marked `failed`.
- There is no silent fallback to `openai` when the backend is forced.

## Runtime Failure Policy

This is a deliberate design choice, not a gap: if the codex backend is
selected (explicitly or via auto detection) and then fails during image
generation, the stage errors out immediately. There is **no automatic
fallback** to the pay-per-use OpenAI API, so a failing subscription backend
never silently turns into unexpected API spend.

Two distinct failure kinds are recorded on the concept stage:

- `failureKind: "codex_usage_limit"` — the ChatGPT subscription's usage
  limit is exhausted. Codex prints a message containing
  `"You've hit your usage limit ... try again at <date>"`. Recovery options:
  - Wait for the reset time shown in the error, then retry.
  - Buy additional usage credits.
  - Re-run the concept stage with `--backend openai` to use the pay-per-use
    API instead.
- `failureKind: "codex_error"` — any other codex failure: the CLI exited
  non-zero for a different reason, or it exited 0 but did not produce a
  valid PNG at the expected path. Recovery options:
  - Inspect the recorded `error` text in `pipeline.json` for the underlying
    codex output.
  - Retry the same command.
  - Re-run with `--backend openai` to fall back to the API path.

## Reference Chaining

The codex backend generates the `front` view first, then attaches it to
each remaining angle's `codex exec` session as a reference image (`-i`),
with a prompt clause requiring the exact same design — proportions,
silhouette, colors, materials, and distinctive details — changed only to
the requested camera angle. Every angle's prompt also requires exactly ONE
view per image (never a turnaround sheet or grid).

Measured effect (same asset description, with vs. without chaining): the
four views go from "same palette but drifting proportions and moving
parts" to a near-identical single design across all views, and the
occasional multi-view turnaround sheet output disappears. This helps both
Stage 2 (a cleaner canonical for image-to-3D) and Stage 6 (a stable
comparison baseline for multimodal review).

Chaining is codex-only: the openai backend's Images Generations endpoint
accepts no image input, so its behavior is unchanged. If the `front`
generation fails, the whole stage fails (standard error-stop policy);
there is no partial fallback to unchained generation.

## Manifest Fields

When the codex backend is used, the concept stage records:

- `vendor: "codex:gpt-image-2"`
- `endpoint: "codex-cli"`
- `requestIds: []` (codex has no per-request API ids to record)

`--model` / `PIPELINE_OPENAI_IMAGE_MODEL` apply only to the `openai` backend.
The codex backend always uses Codex's built-in `gpt-image-2` tool and
ignores both.

## Usage Limit Cost Note

Codex image-generation turns consume ChatGPT subscription usage limits
noticeably faster than ordinary text turns — roughly 3-5x the usage per
turn. Generating all four concept angles through the codex backend can use
up a meaningful share of a session's or day's usage budget; keep this in
mind before recommending the codex backend for repeated re-rolls.

## Sandboxing

Each `codex exec` invocation runs with `--sandbox workspace-write`,
`--skip-git-repo-check`, and `cwd` set to a fresh, empty temporary staging
directory (`tempfile.mkdtemp(prefix="codex-concept-")`) — never inside the
pipeline workspace. The prompt is delivered on stdin (`codex exec -`), not
as a command-line argument: on Windows the codex CLI is an npm `.cmd` shim
and cmd.exe truncates a multi-line argv at the first newline, which would
silently drop everything after the first prompt line. This matters because this same plugin's skills are
also installed into Codex on this machine: if `codex exec` ran inside
`3d-pipeline-output/<slug>/concept/`, the agent could see
`../pipeline.json` and the pipeline's own scripts and "helpfully" try to
run them, derailing the turn. Running in an isolated directory means the
agent cannot see `pipeline.json` or any plugin script, and any runtime
artifacts it creates (including stray `.git`, `.agents`, or `.codex`
directories) are confined to the staging directory rather than the
pipeline's output tree.

The agent does NOT copy any file into place. Files created by the
sandboxed shell inside `codex exec` can stay read-locked by the Codex
process tree long after `codex exec` exits (observed on Windows for well
over two minutes: readable never, deletable yes), so collecting the output
through an agent-side copy is structurally unreliable. Instead the agent's
only job is to run the built-in image tool once, and `_codex_backend.py`
collects the image directly from the Codex CLI's own artifact at
`$CODEX_HOME/generated_images/<session-uuid>/call_*.png` — written by the
codex main process, not the sandbox — validates it, and writes it
atomically to the real destination,
`3d-pipeline-output/<slug>/concept/<angle>.png`. A residual bounded retry
(120 seconds) still guards the artifact read against transient locks. The
staging directory is always removed in a `finally` block afterward via
`shutil.rmtree(..., ignore_errors=True)`, regardless of success or
failure, which also discards any pollution left behind.

## Prompt Contract

The prompt sent to `codex exec` follows the Codex system imagegen skill's
own schema: a `Use case: stylized-concept` line, an asset-type line, a
labeled `Primary request:` section carrying the style/lighting/constraint
text, and an `Execution requirements:` block. This alignment improves
routing determinism against the skill's use-case taxonomy.

The `Execution requirements:` block also carries a fail-loud,
anti-improvisation contract, proven out by a controlled probe:

- The agent is told the request is issued programmatically by the
  3d-asset-pipeline's own scripts, and that it must not invoke any
  3d-asset-pipeline skill, command, or script, and must not read or modify
  any files other than the single output image. This directly prevents the
  workspace-contamination failure mode described above.
- It must use its built-in image generation tool (`image_gen`,
  `gpt-image-2`) to generate exactly one image and print `IMAGEGEN_OK`. It
  is told the tool's saved output is collected automatically and that it
  must not move, copy, or save any files itself.
- If the built-in `image_gen` tool is not available in its tool list, it
  must print exactly `IMAGEGEN_UNAVAILABLE` and stop — it must never draw
  or synthesize the image with code (no Pillow, no SVG, no matplotlib, no
  scripts); a code-drawn image is explicitly called out as a failure, not
  a creative fallback.
- It must not create any other files; moving/copying the generated image
  into place is expected and allowed.

The sentinel is checked against the agent's final message only, captured
via `codex exec --output-last-message <staging>/last-message.txt` — never
against raw stdout, because `codex exec` echoes the full prompt (which
itself names the sentinel) to stdout and a stdout scan would always
self-trigger. If the final message contains `IMAGEGEN_UNAVAILABLE`,
`_codex_backend.py` raises a specific `CodexBackendError` (checked before
the staging-file-exists check) explaining that the built-in image
generation tool was unavailable in the session, and suggesting
`--backend openai`.

## Provenance Verification

A code-drawn PNG (for example, one hand-drawn with Pillow because the
agent decided to "help" instead of stopping) can still pass a PNG-magic
check, since Pillow output is a structurally valid PNG. The backend rules
this out by making the Codex CLI's own image-generation artifact the ONLY
accepted source of the image:

- Before launching `codex exec`, it snapshots the subdirectory names under
  `$CODEX_HOME/generated_images` (default `~/.codex/generated_images` when
  `CODEX_HOME` is unset; a missing root counts as an empty set). Codex
  writes each `image_gen` tool call's output under
  `<root>/<session-uuid>/call_*.png`.
- After `codex exec` exits 0 (and the `IMAGEGEN_UNAVAILABLE` sentinel is
  absent), the script requires at least one new subdirectory (relative to
  the snapshot) containing at least one `*.png`. The newest such PNG is
  read, validated against the PNG magic bytes, and written atomically to
  the destination. Nothing the agent wrote in its working directory is
  ever collected.
- If no new artifact appeared, the run is treated as failed:
  `_codex_backend.py` raises `CodexBackendError` stating that codex
  finished without using the built-in image generation tool, so there is
  no trusted image to collect.
- This failure is recorded with `failureKind: "codex_error"`, the same
  failure kind used for other non-usage-limit codex failures — provenance
  failures are not a new failure kind, just a new reason within the
  existing one.

Combined with the fail-loud prompt contract above, a code-drawn
counterfeit PNG can never be accepted: it is not just detected and
rejected, it is never even a candidate for collection.

One caveat: the artifact root is shared per user, so if another Codex
session generates images concurrently with a pipeline run, the newest new
artifact could in principle come from that other session. Concept
generation runs one angle at a time in the foreground, so in practice this
requires deliberately generating images elsewhere at the same moment.

## Dry-Run Mode

`PIPELINE_DRY_RUN=1` behavior is completely unchanged by this feature:
placeholder PNGs are written, the manifest vendor is always recorded as
`openai:<model>`, and no backend detection (`codex login status`, `PATH`
lookup) runs at all in dry-run mode.
