---
name: unity-testing
description: Automated testing for Unity projects with the Unity Test Framework and command-line batchmode. Use when writing or running Unity tests, setting up Unity Test Framework / EditMode / PlayMode tests, creating test assembly definitions (.asmdef), running Unity in batchmode or CI, or when the user asks to test Unity code or verify a Unity project without opening the editor. Also triggers on mentions of [Test], [UnityTest], NUnit in Unity, the Unity Test Runner, or NUnit results XML.
---

# Unity Testing

Write Unity Test Framework tests and run them headlessly from the command
line, without opening the Unity editor.

## Quick Start

1. Put pure-logic tests in an EditMode test assembly; put scene/component
   behavior tests in a PlayMode test assembly (decision tree below).
2. Write NUnit tests using Arrange-Act-Assert.
3. Run them headlessly:

   ```
   python3 scripts/run_unity_tests.py --project-path <unity-project> --test-platform EditMode
   ```

   (On Windows, use `py -3` if `python3` is not available.) The script
   locates the Unity executable, runs the tests in batchmode, parses the
   NUnit results XML, and prints a summary of failures.
4. If any test fails: read the failure messages, fix the code or the test,
   and re-run. Only proceed when all tests pass.

## Decision tree

- **Pure C# logic** (damage formulas, inventory rules, state machines, plain
  classes with no UnityEngine lifecycle)? -> **EditMode tests**. Fastest;
  run without entering Play mode. Prefer this: design logic as plain C#
  classes so it lands here.
- **MonoBehaviour or scene behavior** (physics, coroutines, animation,
  anything needing `Update()` frames)? -> **PlayMode tests** with
  `[UnityTest]` coroutines.
- **CI / "verify the project without opening the editor"?** -> run both
  platforms via batchmode CLI (below), parse the results XML, fail the build
  on any failed test.

## Structuring tests

### Folders and assembly definitions

Tests require their own assembly definitions (.asmdef) referencing the
Unity Test Framework:

```
Assets/_Project/
  Scripts/
    Gameplay/
      Gameplay.asmdef
  Tests/
    EditMode/
      EditModeTests.asmdef     # "includePlatforms": ["Editor"]
    PlayMode/
      PlayModeTests.asmdef     # no platform restriction
```

Both test asmdefs need, in `references`: the production assembly under test
(e.g. `Gameplay` - production code MUST be in its own asmdef to be
referenced) and `UnityEngine.TestRunner` / `UnityEditor.TestRunner`, with
`"precompiledReferences": ["nunit.framework.dll"]` and
`"overrideReferences": true`. EditMode asmdefs also set
`"includePlatforms": ["Editor"]`.

### [Test] vs [UnityTest]

- `[Test]`: synchronous NUnit test. Use for all pure C# logic.
- `[UnityTest]`: returns `IEnumerator`; `yield return null` advances one
  frame, so the test can span frames, physics steps, and async operations.
  PlayMode tests that wait on behavior need this.

```csharp
[Test]
public void TakeDamage_ReducesHealthByAmount()
{
    // Arrange
    var health = new Health(maxHealth: 100);
    // Act
    health.TakeDamage(30);
    // Assert
    Assert.That(health.Current, Is.EqualTo(70));
}

[UnityTest]
public IEnumerator Player_FallsUnderGravity()
{
    var go = new GameObject("player", typeof(Rigidbody));
    var startY = go.transform.position.y;

    yield return new WaitForFixedUpdate();
    yield return new WaitForFixedUpdate();

    Assert.That(go.transform.position.y, Is.LessThan(startY));
    Object.Destroy(go);
}
```

Rules:

- Arrange-Act-Assert in every test; one behavior per test.
- Name tests `Method_ExpectedBehavior_WhenCondition` (or
  `Method_ExpectedBehavior` when unconditional).
- Use NUnit constraint syntax: `Assert.That(x, Is.EqualTo(y))`,
  `Is.LessThan`, `Throws.ArgumentException`, etc.
- PlayMode tests must clean up spawned GameObjects (`Object.Destroy`) so
  tests stay independent.
- Expected error logs must be declared: `LogAssert.Expect(LogType.Error, ...)`,
  otherwise the test fails on the log message.

## Running tests in batchmode

The underlying invocation (the script wraps this):

```
<UnityPath> -batchmode -projectPath <path> -runTests -testPlatform EditMode -testResults results.xml -logFile -
```

- `-testPlatform` is `EditMode` or `PlayMode`.
- `-testResults` must be an absolute path; Unity writes NUnit-format XML.
- `-logFile -` streams the editor log to stdout (useful for compile errors).
- Do not pass `-quit` with `-runTests`; the test runner exits on its own.
- Another Unity instance holding the project open will make the run fail
  with a lock error - close the editor first.

### Locating the Unity executable

Default Unity Hub install locations (always write paths with forward
slashes, including on Windows):

- Windows: `C:/Program Files/Unity/Hub/Editor/<version>/Editor/Unity.exe`
- macOS: `/Applications/Unity/Hub/Editor/<version>/Unity.app/Contents/MacOS/Unity`
- Linux: `~/Unity/Hub/Editor/<version>/Editor/Unity`

Match `<version>` to `m_EditorVersion` in
`<project>/ProjectSettings/ProjectVersion.txt`. `scripts/run_unity_tests.py`
does this automatically (override with `--unity-bin` or the `UNITY_PATH`
environment variable).

### Reading the results XML

The NUnit XML root `<test-run>` carries `result`, `total`, `passed`,
`failed`, `skipped` attributes. Each failed `<test-case>` has a `fullname`
and a `<failure><message>` (plus `<stack-trace>`). The script prints exactly
this summary; when inspecting manually, read those nodes rather than the
whole file.

## The feedback loop

1. Run the tests (script above).
2. If Unity itself failed (compile errors), fix the compile errors first -
   the log output shows them.
3. For each failed test: read the failure message and stack trace, decide
   whether the production code or the test is wrong, and fix the root cause.
   Never delete or `[Ignore]` a failing test to get to green.
4. Re-run. Repeat until the run reports 0 failed.
5. Only declare the task complete when the latest run is green.

## Design for testability

Consistent with the unity-gamedev skill:

- Keep MonoBehaviours humble: they read input and forward to plain C#
  classes that hold the logic. The plain classes get EditMode tests.
- Inject dependencies via constructors or `[SerializeField]` references -
  no static singletons reached from inside logic classes.
- Put tunable data in ScriptableObjects; tests create instances with
  `ScriptableObject.CreateInstance<T>()` and set fields directly.
- If a behavior is hard to test without a scene, that is a design smell:
  extract the logic before writing an elaborate PlayMode test.

## Verification checklist

Before declaring testing work complete, confirm:

- [ ] Tests live under a test asmdef (EditMode and/or PlayMode) that
      references the production assembly and `nunit.framework.dll`.
- [ ] EditMode/PlayMode choice matches the decision tree (logic -> EditMode,
      frames/physics -> PlayMode `[UnityTest]`).
- [ ] Every test is Arrange-Act-Assert with a descriptive name and NUnit
      constraint asserts.
- [ ] The full suite was actually executed via batchmode (or the editor Test
      Runner if the user prefers) and the final run has 0 failures.
- [ ] No test was skipped, ignored, or deleted to force a green run.
