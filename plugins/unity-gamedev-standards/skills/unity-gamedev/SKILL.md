---
name: unity-gamedev
description: This skill should be used when writing or reviewing Unity game code - creating a Unity project, writing C# scripts (.cs), implementing MonoBehaviour or ScriptableObject classes, working with scenes (.unity), prefabs (.prefab), or asset files (.asset), using UniTask async, optimizing Unity performance, or any Unity 6 / Unity 6.3 LTS development task. Triggers on mentions of Unity, C#, MonoBehaviour, ScriptableObject, GameObject, Rigidbody, Animator, prefab, UniTask, ECS/DOTS, camera follow, or object pooling. Also triggers on the /unity-setup command and questions about Unity game development patterns.
allowed-tools: Bash(dotnet*), Bash(mkdir*), Bash(ls*), Read, Write, Edit, Glob, Grep, Task
---

# Unity GameDev Standards

Standards for Unity 6.3 LTS+ development. Apply the core rules below to all
Unity code. Before non-trivial work in an area, load the matching file from
`references/` (routing table below) - detailed patterns and full code
examples live there, not here.

## Core Rules (always apply)

### Naming

- Classes, structs, methods, properties, public fields: `PascalCase`;
  interfaces: `IPascalCase`.
- Private fields: `_camelCase` (including `[SerializeField]` fields);
  constants: `SCREAMING_SNAKE_CASE`; parameters and locals: `camelCase`.
- Event handler methods: `On` + event name (`OnEnemyDied`).

### Inspector

- Every `[SerializeField]` field gets a `[Tooltip]`; bounded numeric values
  get `[Range]`; group related fields with `[Header]`.
- The Inspector is the source of truth for component configuration. Never
  hardcode Inspector-configurable component values (Rigidbody mass, damping,
  etc.) in `Awake()`/`Start()` - `Awake()` is only for caching references and
  initializing internal state. When a component value must change, change it
  in the editor (use Unity MCP tools if available; otherwise instruct the
  user to change it in the Inspector).
- Never create `PhysicsMaterial` or similar configuration assets in code -
  use project assets.

### Lifecycle and timing

- Physics and Rigidbody manipulation in `FixedUpdate()`; input and
  per-frame logic in `Update()`; camera follow/position code in
  `LateUpdate()` only - `Update()` causes 1-frame jitter.
- Enable Rigidbody Interpolation (in the Inspector) on targets followed by a
  camera.
- Cache component references in `Awake()` with `GetComponent`; subscribe to
  events in `OnEnable()` and always unsubscribe in `OnDisable()`.
- Organize MonoBehaviours with `#region` sections in this order: Inspector
  Fields, Private Fields, Properties, Events, Unity Lifecycle, Public
  Methods, Private Methods.

### Performance

- No allocations in `Update` loops: no `FindObjectsOfType`, no string
  concatenation, no `new` collections per frame. Pre-allocate and reuse
  lists/StringBuilder; use the non-allocating
  `FindObjectsByType(..., results)` overloads when a search is unavoidable.
- Use `UnityEngine.Pool.ObjectPool<T>` for frequently instantiated objects
  (bullets, effects).
- Hash Animator parameter names once: `Animator.StringToHash("Speed")`.
- Prefer `TryGetComponent<T>(out var c)` over `GetComponent<T>() != null`.

### Architecture

- Game configuration data lives in `ScriptableObject` assets
  (`[CreateAssetMenu]`, `PascalCase` public fields, tooltips).
- Characters use MVC layering with one-way dependency:
  Controller (input/AI) -> Model (stats/logic) -> View (animation/effects).
- Keep MonoBehaviours thin; put game logic in plain C# classes so it can be
  unit tested (see the unity-testing skill for writing and running tests).
- Never skip null checks on external/serialized references.

## Routing: which reference to load

| Working on... | Load |
| --- | --- |
| Project setup, folder layout, asset naming, assembly definitions | `references/project-structure.md` |
| C# style details: naming, regions, events, null and string handling | `references/coding-rules.md` |
| Animation, Update/FixedUpdate/LateUpdate order, Root Motion, Animator modes | `references/animation-timing.md` |
| Camera follow/orbit/side-scroll, camera jitter, execution order | `references/camera-systems.md` |
| Component configuration, "value set in code vs Inspector" questions | `references/inspector-workflow.md` |
| ScriptableObject data containers, event channels, variables, databases | `references/scriptable-objects.md` |
| GC pressure, pooling, physics/rendering optimization, profiling | `references/performance.md` |
| Character/player/enemy structure, swapping player vs AI control | `references/character-mvc.md` |
| async/await, UniTask, cancellation tokens, coroutine interop | `references/async-unitask.md` |
| ECS/DOTS, Burst, Jobs, authoring and baking | `references/ecs-patterns.md` |
| EditMode/PlayMode test code patterns | `references/testing-standards.md` (running tests headlessly: unity-testing skill) |
| Custom inspectors, property drawers, editor windows, menu items | `references/editor-extensions.md` |
| .gitignore, Git LFS, scene/prefab merge conflicts | `references/git-management.md` |

If several areas apply, load only the files needed for the current step.

## Recommended project layout

Top-level shape (full tree and naming prefixes in
`references/project-structure.md`):

```
Assets/
  _Project/        # project assets: Art/, Audio/, Prefabs/, Scenes/,
                   # ScriptableObjects/, Scripts/{Core,Gameplay,UI,Utilities}/, Settings/
  Plugins/         # third-party
  Editor/          # editor-only scripts
```

## Verification checklist

Before declaring Unity code complete, confirm:

- [ ] Naming follows the conventions above (`_camelCase` private fields,
      `PascalCase` members).
- [ ] Every `[SerializeField]` has `[Tooltip]`; bounded values have `[Range]`.
- [ ] Physics code is in `FixedUpdate()`; camera code is in `LateUpdate()`.
- [ ] No per-frame allocations or `FindObjectsOfType` in `Update` loops.
- [ ] Component references cached in `Awake()`; every event subscription has
      a matching unsubscribe in `OnDisable()`.
- [ ] No Inspector-configurable component values overwritten in code.
- [ ] New logic that can live in plain C# does, and is covered by tests when
      the project has a test assembly (unity-testing skill).
