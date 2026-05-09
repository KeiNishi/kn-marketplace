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

Required for the complete pipeline:

```dotenv
OPENAI_API_KEY=sk-...
REPLICATE_API_TOKEN=r8_...
MESHY_API_KEY=msy_...
```

Optional:

```dotenv
TRIPO_API_KEY=tsk_...
```

Scripts must use `scripts/_credentials.py` and must never read `.env` files from the current working directory, plugin directory, repository root, or asset output folder.
