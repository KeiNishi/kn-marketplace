---
name: doctor
description: Health check for the 3D asset pipeline -- verifies Python, deps, credentials file, required keys, git, and (optionally) network reachability of OpenAI, Replicate, Meshy.
argument-hint: "[--network]"
allowed-tools: Bash
---

# 3D Pipeline Doctor Command

Run the deterministic health checker for the plugin.

## Usage

```text
/3d-pipeline:doctor [--network]
```

Pass all command arguments through to the script.

Run:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/doctor.py" $ARGUMENTS
```

Capture the exit code and output.

Print the script output first.

Then interpret the exit code:

- Exit `0`: all required checks passed; the pipeline environment is healthy.
- Exit `2`: one or more checks failed; action is required before running paid or long-running stages.
- Any other exit code: unexpected error; check the Python installation and rerun the command.

When `--network` is provided, explain that the command also checks reachability for OpenAI, Replicate, and Meshy endpoints.

Never print credential values.
