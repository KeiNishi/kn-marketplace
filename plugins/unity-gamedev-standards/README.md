# Unity GameDev Standards

A Claude Code / Codex plugin providing Unity 6 (6.3 LTS+) development
standards: C# coding conventions, MonoBehaviour and ScriptableObject
patterns, performance rules, and automated testing workflows. All skills are
portable across Claude Code and OpenAI Codex CLI, and work on Windows,
macOS, and Linux.

## Contents

| Component | Type | Purpose |
| --- | --- | --- |
| `unity-gamedev` | Skill | Coding and architecture standards for Unity work |
| `unity-testing` | Skill | Writing and running Unity Test Framework tests headlessly |
| `/unity-setup` | Command | Audit a Unity project's structure against the standards |

## Skill: unity-gamedev

Activates when working with Unity code or assets (`.cs`, `.unity`,
`.prefab`, `.asset`, MonoBehaviour, ScriptableObject, UniTask, ECS/DOTS).

The skill body holds the always-on core rules - naming conventions,
Inspector discipline (tooltips, never hardcoding Inspector values in code),
lifecycle timing (physics in `FixedUpdate`, camera in `LateUpdate`),
allocation-free update loops, and MVC character architecture - plus a
routing table into 13 detailed reference files:

- Project structure and asset naming
- Coding rules (naming, regions, events, null/string handling)
- Animation timing and Root Motion
- Camera systems
- Inspector workflow
- ScriptableObject patterns (data, event channels, variables)
- Performance (GC, pooling, physics, rendering, profiling)
- Character MVC design
- Async with UniTask
- ECS/DOTS patterns
- Testing standards (test code patterns)
- Editor extensions
- Git management (.gitignore, LFS, merge conflicts)

## Skill: unity-testing

Activates when writing or running Unity tests, setting up EditMode/PlayMode
test assemblies, or verifying a Unity project in CI without opening the
editor.

Covers:

- EditMode vs PlayMode decision tree (pure C# logic vs frame/physics
  behavior)
- Test assembly (.asmdef) setup, `[Test]` vs `[UnityTest]`,
  Arrange-Act-Assert with NUnit constraints
- Headless batchmode runs:
  `Unity -batchmode -projectPath <path> -runTests -testPlatform EditMode -testResults results.xml -logFile -`
- `scripts/run_unity_tests.py` - a stdlib-only Python helper that locates
  the Unity executable (argument, `UNITY_PATH`, or default Hub install
  paths per OS), runs the tests, parses the NUnit results XML, and prints a
  failure summary with a non-zero exit on failure
- The run -> parse failures -> fix -> re-run feedback loop (only proceed
  when green)
- Design-for-testability rules consistent with the unity-gamedev skill

## Command: /unity-setup

```
/unity-setup [path-to-assets-folder]
```

Read-only audit of a Unity project: checks the folder layout against the
recommended `Assets/_Project/` structure, asset naming prefixes, and coding
conventions in sampled scripts, then reports prioritized recommendations.
It makes no changes without explicit confirmation.

## Conventions

- All content is written in English and saved as UTF-8 without BOM.
- Paths use forward slashes everywhere, including in Windows examples.
- Bundled scripts are Python standard library only; invoke with `python3`
  (on Windows, `py -3` if `python3` is unavailable).
