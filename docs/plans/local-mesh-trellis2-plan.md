# Plan: Local Mesh Generation (TRELLIS.2) for 3d-asset-pipeline

Status: DONE (implemented and verified 2026-07-13; plugin 0.5.0, marketplace 1.6.0)

Verification record (Chunk 3):
- Dry-run E2E: init -> concept (dry) -> approve -> mesh local (dry) all exit 0;
  manifest records vendor local:trellis2-spz, backend, local: true, dryRun: true.
- Real E2E on the live local server: rapid/1024, --target-polys 30000 -> exit 0
  in 45s (warm model), 9.2MB GLB, 29,090 triangles for the 30k budget, PBR
  material with baseColor + metallicRoughness textures; progress logging worked.
- doctor.py: 13 ok / 1 warn / 0 fail with the server running; REPLICATE token
  downgrade logic in place.
- Executor note: Chunks 1-2 were implemented by Claude Sonnet subagents (Codex
  was rate-limited and its CLI outdated); reviewed by the supervisor. CRLF line
  endings introduced by the Chunk 2 editor were normalized back to LF.

## Goal

Add a fully local (no online service) mesh + texture generation vendor to Stage 2 of
`plugins/3d-asset-pipeline`, while keeping the existing cloud workflow (Hunyuan 3.1 via
Replicate / Meshy v5 / Tripo3D) unchanged and keeping the user experience identical:
the whole workflow stays conversational inside Claude Code / Codex.

Non-goals:
- No changes to Stage 1 (concept, OpenAI), Stages 3-4 (rig/animate, Meshy), Stage 5-6.
- No changes to other plugins or skills.
- No NPR-specific texture stage in this release. NPR is served by style preservation
  from the (stylized) canonical concept image; documented, with MV-Adapter noted as a
  possible future extension.

## Selected backend (decision record)

**IgorAherne/TRELLIS.2-stableprojectorz** (low-VRAM fork of Microsoft TRELLIS.2-4B),
pinned to a specific release (v22, 2026-04-06, or newest verified in Chunk 0).

Why (vs alternatives researched 2026-07-12):
- Quality: TRELLIS.2 is the top-rated open-weight model for texture/PBR fidelity;
  full 4-channel PBR output (albedo/roughness/metallic/opacity), up to 1536^3.
- VRAM: fork is engineered for 8GB GPUs (chunked decoder, per-level offload) — ample
  headroom on the target RTX 4070 Ti 12GB / 64GB RAM.
- Windows: self-contained installer (bundled Python 3.11 / Torch 2.8 / CUDA 12.8),
  no Visual Studio, no CUDA Toolkit, no admin rights.
- License: MIT (model + fork). Caveat shared with all TRELLIS.2 derivatives: the
  texture bake path uses NVIDIA nvdiffrast (non-commercial source license; see
  microsoft/TRELLIS.2#22) — documented to users, not hidden.
- Integration: ships an API server mode (`run-stableprojectorz.bat`) and a Gradio
  mode (`run-gradio.bat`); either exposes HTTP endpoints that fit the existing
  `_common.poll()` vendor-polling pattern.

Rejected: Hunyuan3D 2.1 (EU/UK/KR license exclusion, VS2022 CUDA kernel builds,
texture-stage OOM on 12GB), Pixal3D (no stylized-input track record, hardest Windows
setup, unanswered commercial-license question — revisit later as a second local
vendor), Hi3DGen+MV-Adapter (integration complexity), TripoSG/SPAR3D (quality).

The local backend client is designed as a small pluggable interface so a future
vendor (e.g., Pixal3D once mature) can be added without restructuring.

## Architecture

New files under `plugins/3d-asset-pipeline/`:

- `scripts/_local_backend.py` — minimal client for a local generation server:
  `health()`, `submit(image_path, options) -> job`, `poll(job)`, `download(job) -> glb bytes`.
  Base URL from optional env `TRELLIS2_SPZ_URL` (default determined in Chunk 0),
  optional `TRELLIS2_SPZ_HOME` pointing at the fork install dir so the script can
  auto-start the server (spawn the .bat, wait for health) when it is not running.
  These are configuration values, not secrets; they live in the existing
  `~/.claude/3d-pipeline/.env` alongside `GODOT_BIN` (same precedent).
- `scripts/mesh_trellis_local.py` — Stage 2 vendor script, pattern-identical to
  `mesh_hunyuan.py`: manifest validation + concept-approval gate -> `in_progress`
  -> generate via `_local_backend` -> write `mesh/<slug>.glb` -> `done`/`failed`.
  Vendor id: `local:trellis2-spz`. Extra manifest fields on the mesh stage:
  `backend: "trellis2-stableprojectorz"`, `local: true` (additive; schema stays 1.2).
  Dry-run copies the existing `scripts/fixtures/mesh/dryrun.glb` like other vendors.
  No credentials required or read for this vendor.
- `skills/mesh-generation/references/trellis2-local.md` — install + operations
  reference: download/pin of the fork release, disk (~40GB) and VRAM expectations,
  recommended settings for 12GB, NVIDIA "Sysmem Fallback" tip, licensing notes
  (MIT + nvdiffrast caveat), troubleshooting.

Modified files:

- `commands/generate-mesh.md` + `skills/mesh-generation/SKILL.md` — add
  `--vendor local` routing (cloud default unchanged), pre-flight = server health
  instead of API key, poller/timeout guidance (local generation: minutes-scale
  timeout, no cost preamble line — local runs are $0).
- `commands/run-pipeline.md` — vendor routing + cost preamble reflects $0 mesh when
  local vendor selected.
- `scripts/doctor.py` + `commands/check-pipeline.md` — Stage 2 requirement becomes
  "REPLICATE_API_TOKEN present OR local TRELLIS.2 backend reachable"; add local
  backend check (URL reachable / HOME dir exists) without demoting existing checks.
- `README.md` — new "Local mesh generation (no API key)" section: setup, scope
  (Stage 2 only), license notes, hardware guidance (12GB VRAM verified target).
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` — version 0.5.0,
  description/keywords updated to mention local TRELLIS.2 support (final chunk only,
  both files synced).

## Chunk plan

Chunk 0 — Backend spike (no repo changes; Claude-led, needs user machine + consent):
  1. Download the pinned fork release zip to D: (~several GB; ~40GB after weights).
  2. Start API server mode; capture the actual HTTP API surface (endpoints, params,
     output format) for both server modes; pick the stabler one.
  3. Generate a real mesh from an existing concept image; record peak VRAM, wall
     time, output GLB properties (PBR channels present, polycount) on the 4070 Ti.
  4. Decide: default voxel resolution (1024 vs 1536), default texture settings,
     auto-start behavior, port/URL default. Findings appended to this file.

Chunk 1 — Core scripts (delegate implementation per Codex-delegation workflow;
  Claude writes the brief and reviews):
  `_local_backend.py`, `mesh_trellis_local.py`, dry-run path, error taxonomy
  (`backend_unreachable`, `generation_failed`, `timeout`, `oom_suspected`),
  no-credential preflight. Reviewed against existing vendor script conventions.

Chunk 2 — Command/skill/doctor integration (delegate; use plugin-dev skills per
  CLAUDE.md): generate-mesh.md, SKILL.md, trellis2-local.md reference, doctor.py,
  check-pipeline.md, run-pipeline.md.

Chunk 3 — Docs, versions, validation (Claude-led):
  README section, version bumps 0.4.0 -> 0.5.0 in both plugin.json and
  marketplace.json, plugin-validator run, end-to-end dry-run test, one real
  concept->mesh->import->review run with the local vendor, update this plan to DONE.

Per versioning memory: no version bumps during chunks 0-2; single MINOR bump in
Chunk 3 when the feature ships.

## Chunk 0 findings (in progress, 2026-07-12)

Verified from the fork source (gh api) and the extracted v22 installer at `D:\AI\trellis2-spz`:

- Release used: `trellis2-stableprojectorz_v22.zip` (tag `latest`, 2026-04-06, 736MB).
  Extracted to `D:\AI\trellis2-spz`. A newer `spz` tag zip (2026-04-20) exists; the
  README's one-click installer link points at `latest`, so v22 was chosen.
- Server: FastAPI (`code/api_spz/main_api.py`), default `127.0.0.1:7960`
  (`--host/--port/--device` flags). Launched via `run-stableprojectorz/run-stableprojectorz.bat`
  -> `tools/projectorz-internal.bat` -> first run executes `install.py`
  (pip deps + dinov3/RMBG-2.0 zips + HF snapshot of TRELLIS.2-4B and
  TRELLIS-image-large into `code/models`), then `python api_spz/main_api.py`.
  Everything self-contained under the install dir (HF_HOME=code/models).
- API surface (confirmed in code and bundled api-documentation.html):
  - `GET /ping` -> `{status:"running", busy:bool}` (health)
  - `GET /status` -> `{status: PROCESSING|PREVIEW_READY|COMPLETE|FAILED, progress, message, busy}`
  - `POST /generate_no_preview` (multipart form: `file` or `image_base64`; params:
    `seed`, `guidance_scale` 1-10 (default 7.5), `num_inference_steps` 1-50 (default 12),
    `resolution` -> snapped to 512/1024/1536 pipeline, `mesh_simplify` 10-1000
    thousands of faces (default 50 = 50k), `apply_texture` (default true),
    `texture_size` (default 2048), `output_format`="glb" only)
  - `GET /download/model` -> `model.glb` (media type model/gltf-binary)
  - `POST /interrupt`
- Single-job server: no job ids; one generation at a time guarded by a lock
  (`busy`). Client must check `busy` before submit.
- IMPORTANT client caveat: before any generation has run, `/status` reports
  `FAILED` (server default state). The client must poll only after a successful
  submit, and treat pre-submit FAILED as idle, not as an error.
- Windows launch gotcha (root cause identified 2026-07-13, fixed in 0.5.1):
  the Claude Code shell environment sets `NoDefaultCurrentDirectoryInExePath=1`,
  which stops cmd.exe from resolving `.bat` files via the current directory.
  The fork's launcher chain uses relative `call` lookups, so every spawn from
  this environment failed with "'...bat' is not recognized" (double-click from
  Explorer works because that variable is absent there). Fix in
  `_local_backend._spawn_server`: invoke `tools/projectorz-internal.bat` by
  ABSOLUTE path and pop `NoDefaultCurrentDirectoryInExePath` from the child
  env so the fork's own nested relative calls resolve.
  Also: the internal bats call `pause` on failure - auto-start must use a
  timeout + `/ping` probe rather than waiting for process exit.
- Param mapping decided: `--target-polys N` -> `mesh_simplify = round(N/1000)`
  (clamped 10-1000); `--mode rapid` -> resolution 1024, `--mode pro` -> 1536;
  `--no-pbr` -> `apply_texture=false`; `--seed` -> `seed`.

Measured on the target machine (RTX 4070 Ti 12GB, 2026-07-12, bundled example
image, mesh_simplify=50, texture_size=2048, apply_texture=true):

| Setting | Wall time | Peak VRAM | Output |
| --- | --- | --- | --- |
| resolution 1024 (rapid) | 107s (incl. first model load to GPU) | 8.2 GB | 13.7MB GLB |
| resolution 1536 (pro) | 294s (steady state) | 9.8 GB | 13.8MB GLB |

Output GLB verified: glTF PBR metallic-roughness material with baseColorTexture
+ metallicRoughnessTexture (2 embedded PNGs), NORMAL + TEXCOORD_0 attributes,
46,903 triangles for the 50k budget (mesh_simplify honored). Ready for Godot 4
native import; no OOM at either resolution; texture stage stayed within 12GB.

CRITICAL API BEHAVIOR (drives _local_backend.py design):
`POST /generate_no_preview` is SYNCHRONOUS - it blocks until generation
finishes and returns the final status in the response body. Design: submit the
POST on a worker thread with a long timeout (>= 1800s), poll `GET /status`
from the main thread only for progress logging, and treat the POST response as
the source of truth. Do not interpret a pre/early-poll `FAILED` (the server's
idle default) as a real failure; only the POST response or a FAILED observed
after PROCESSING counts.

Chunk 0 status: COMPLETE. All open questions resolved; defaults chosen:
rapid=1024, pro=1536, texture_size 2048, base URL http://127.0.0.1:7960.

## Risks / mitigations

- Fork API surface undocumented -> Chunk 0 verifies before any code is written;
  release pinned to avoid drift.
- Single-maintainer fork -> pin release zip; document manual fallback (Gradio UI).
- Texture-stage VRAM spikes (industry-wide failure mode) -> 12GB has 4GB headroom
  over the fork's 8GB design point; document Sysmem Fallback driver setting.
- nvdiffrast license (non-commercial source license inside the texture bake path,
  upstream-wide issue) -> surfaced prominently in README and reference doc so users
  can make their own call; plugin itself redistributes nothing from the fork.
- Server not running when user asks for mesh -> auto-start via TRELLIS2_SPZ_HOME,
  clear conversational error otherwise (no tracebacks, matching house style).
