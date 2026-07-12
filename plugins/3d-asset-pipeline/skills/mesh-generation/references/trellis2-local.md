# Local TRELLIS.2 Backend (trellis2-stableprojectorz)

## What It Is

`IgorAherne/TRELLIS.2-stableprojectorz` is a low-VRAM Windows fork of Microsoft's TRELLIS.2-4B image-to-3D model (MIT license). It ships a one-click installer and runs a FastAPI server on `127.0.0.1:7960` by default. This is the vendor behind `--vendor local` (`mesh_trellis_local.py`, vendor tag `local:trellis2-spz`).

## Install

- Download `trellis2-stableprojectorz_v22.zip` from the fork's GitHub releases, tag `latest`.
- Extract to a SHORT path. Example: `D:\AI\trellis2-spz` (example install path only, not a repo requirement).
- Run `run-stableprojectorz\run-stableprojectorz.bat` once by double-clicking it.
- The first run installs Python dependencies and downloads about 18GB of model weights into the install folder. Everything is self-contained under the install directory; total disk use is about 40GB.
- Do not launch the shipped `.bat` from a terminal in a different working directory; see Troubleshooting.

## Configuration

Two optional plain-config values live in `~/.claude/3d-pipeline/.env`, the same file as the API keys, but these are not secrets:

- `TRELLIS2_SPZ_URL` — backend base URL. Default `http://127.0.0.1:7960`.
- `TRELLIS2_SPZ_HOME` — install directory. When set, the plugin can auto-start the server if it is not already running.

## Windows Only

The backend and its auto-start path require Windows (`cmd`/`.bat` launch). There is no macOS or Linux path for this vendor in this release.

## Measured Performance

Measured on an RTX 4070 Ti (12GB), 2026-07, bundled example image, `mesh_simplify=50` (50k budget), `texture_size=2048`, `apply_texture=true`:

| Mode | Resolution | Wall time | Peak VRAM | Output |
| --- | --- | --- | --- | --- |
| rapid | 1024 | 107s (includes first model load to GPU) | 8.2 GB | 13.7MB GLB |
| pro | 1536 | 294s (steady state) | 9.8 GB | 13.8MB GLB |

The output GLB uses a glTF PBR metallic-roughness material with `baseColorTexture` and `metallicRoughnessTexture` (two embedded PNGs), `NORMAL` and `TEXCOORD_0` attributes. `mesh_simplify` is honored: a 50k budget produced 46,903 triangles. No OOM was observed at either resolution; the texture stage stayed within the 12GB budget.

## API Behavior Notes

- Single-job server: one generation at a time, guarded by a `busy` flag reported from `GET /ping`. Check `busy` before submitting.
- `POST /generate_no_preview` is synchronous: it blocks until the generation completes and returns the final result in the response body. That response is the source of truth for success or failure.
- `GET /status` shows `FAILED` when the server is idle (its default state before any generation has run). This is not an error; only a `FAILED` seen after a submission, or the POST response itself, indicates a real failure.

## Licensing Notes

The model and the fork are both MIT licensed. The texture-bake path depends on NVIDIA `nvdiffrast`, whose source is available under a non-commercial NVIDIA license; this is an unresolved upstream question tracked at `microsoft/TRELLIS.2` issue #22. Bundled helpers include RMBG-2.0 (CC BY-NC 4.0) and DINOv3 (Meta's custom license). The plugin does not redistribute any of these components; users should make their own licensing assessment before using local generation output commercially.

## Troubleshooting

- **Server won't start when launched from an agent or CI shell.** Some hosts (including Claude Code shells) set the `NoDefaultCurrentDirectoryInExePath` environment variable, which stops `cmd.exe` from resolving `.bat` files through the current directory; the fork's launcher chain relies on relative `call` lookups and fails with "'projectorz-internal.bat' is not recognized". Start the server by double-clicking `run-stableprojectorz.bat` in Explorer, or rely on the plugin's auto-start, which invokes `tools/projectorz-internal.bat` by absolute path and removes that variable from the child environment.
- **First ping can take 30-60s after launch.** The server needs time to load models onto the GPU; do not treat an early unreachable `/ping` as a hard failure during auto-start.
- **NVIDIA "Sysmem Fallback".** Enable this driver setting as an OOM safety net if a generation runs out of VRAM; it lets the driver spill into system memory instead of failing outright.
- **`mesh_simplify` valid range is 10-1000** (thousands of faces). Values outside that range are clamped.

## NPR / Stylized Note

Stylized concept art is preserved in the generated textures; there is no separate NPR texture stage in this version. If the canonical concept image is stylized, the local backend's texture bake keeps that style rather than normalizing toward photorealism.
