---
name: check-pipeline
description: Health check for the 3D asset pipeline -- verifies Python, deps, credentials file, required keys, git, and (optionally) network reachability of OpenAI, Replicate, Meshy.
argument-hint: "[--network]"
allowed-tools: Bash
---

# 3D Pipeline Check-Pipeline Command

Run the deterministic health checker for the plugin.

## Usage

```text
/3d-pipeline:check-pipeline [--network]
```

Pass all command arguments through to the script.

Run (on Windows, use `py -3` if `python3` is not available):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" $ARGUMENTS
```

Capture the exit code and output.

Print the script output first.

Then interpret the exit code:

- Exit `0`: all required checks passed; the pipeline environment is healthy.
- Exit `2`: one or more checks failed; action is required before running paid or long-running stages.
- Any other exit code: unexpected error; check the Python installation and rerun the command.

When `--network` is provided, explain that the command also checks reachability for OpenAI, Replicate, and Meshy endpoints.

The checker also reports whether the local TRELLIS.2 mesh backend (`--vendor local`, no API key) is reachable. This check never fails; it is informational, since local mesh generation is optional. When the local backend is reachable, a missing `REPLICATE_API_TOKEN` is reported as `[WARN]` instead of `[FAIL]`, since Stage 2 can still run through the local vendor.

Never print credential values.
