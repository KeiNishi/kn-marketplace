# Godot GDScript Patterns

Production patterns, testing, and headless verification for Godot 4.x game
development with GDScript. The plugin ships two skills that load automatically
when a conversation touches Godot, GDScript, `.gd`/`.tscn`/`.tres` files, or
game-architecture questions.

## Skills

### godot-gdscript-patterns

Architecture patterns and non-negotiable GDScript rules: signals up / calls
down, typed GDScript everywhere, Resource for data instead of Node,
composition over inheritance, and Godot 4 syntax only. A decision tree routes
each task to one of eleven reference guides:

| Reference | Covers |
|-----------|--------|
| `state-machine.md` | Node-based state machines for entity behavior |
| `autoload-singletons.md` | Game manager and event bus autoloads |
| `resource-data.md` | Resource-based data containers (`.tres`) |
| `object-pooling.md` | Pooling for frequently spawned objects |
| `component-system.md` | Health, hitbox, and hurtbox components |
| `scene-management.md` | Async scene loading with transitions |
| `save-system.md` | Encrypted save/load with saveable nodes |
| `node-alternatives.md` | Object vs RefCounted vs Resource vs Node |
| `godot-interfaces.md` | Duck typing, groups, type-safe access |
| `notifications-lifecycle.md` | `_init`/`_ready` order, input flow |
| `performance-and-loading.md` | Hot-path tips, preload vs load, level streaming |

The skill ends with a verification checklist (static typing, no cross-scene
`get_node()` coupling, consistent signal connections) the agent must satisfy
before declaring GDScript work complete.

### godot-testing

Automated testing and a headless verification loop for Godot 4 projects:

- **GdUnit4 by default** (GUT as an escape hatch if already installed), with
  setup instructions and a minimal `GdUnitTestSuite` example.
- **Headless execution** via
  `godot --headless --path <project> -d -s addons/gdUnit4/bin/GdUnitCmdTool.gd -a test -c --ignoreHeadlessMode`,
  including how to locate the Godot executable on Windows
  (`C:/Godot/Godot_v4.x...exe`), Linux (`godot4`), and macOS, and the
  `GODOT_BIN` convention.
- **Bundled runner**: `skills/godot-testing/scripts/run_godot_tests.py`
  (Python stdlib, Windows-safe) locates Godot, runs the suite headless,
  parses the JUnit XML report (`reports/report_<N>/results.xml`), and exits
  non-zero with an actionable message on failure.
- **Smoke testing**: boot the game or a single scene headless with
  `--quit-after <frames>` and scan output for `SCRIPT ERROR` lines.
- **Core loop**: implement → run tests headless → fix → re-run; only proceed
  when green.

## Usage

Install the plugin from this marketplace; both skills are discovered
automatically. To run an existing GdUnit4 suite directly:

```
python3 skills/godot-testing/scripts/run_godot_tests.py --project <project-dir>
```

(on Windows, use `py -3` if `python3` is unavailable)

## Compatibility

- Godot 4.x (Godot 4.2+ assumed for GdUnit4 CLI invocations)
- Works in Claude Code and OpenAI Codex CLI; all commands are
  shell-agnostic and Windows-compatible (forward slashes throughout)

## Evals

Each skill ships `evals/evals.json` scenarios used for with-skill vs
without-skill benchmarking. Benchmark artifacts live under
`eval-archives/godot-gdscript-patterns/` at the repository root.
