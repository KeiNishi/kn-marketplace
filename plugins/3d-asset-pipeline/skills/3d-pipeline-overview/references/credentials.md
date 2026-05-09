# Credentials

API keys must stay outside the marketplace repository.

Use this user-level file:

```text
~/.claude/3d-pipeline/.env
```

On Windows:

```text
%USERPROFILE%\.claude\3d-pipeline\.env
```

Required for stages 1, 2, 5, and 6 (concept, mesh, Godot import, review):

```dotenv
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...
```

Optional, but required for stages 3 and 4 (auto-rig and auto-animation):

```dotenv
MESHY_API_KEY=msy_...
```

When `MESHY_API_KEY` is missing, humanoid and quadruped runs must fall back
to prop mode so the rig and animate stages stay `skipped`. The plugin
surfaces this fallback at pre-flight rather than failing partway through.

Optional, used only as a quadruped fallback when Hunyuan output is unsatisfactory:

```dotenv
TRIPO_API_KEY=tsk_...
```

Scripts must use `scripts/_credentials.py` and must never read `.env` files from the current working directory, plugin directory, repository root, or asset output folder.
