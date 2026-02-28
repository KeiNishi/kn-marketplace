# Execution Transcript

## Task

Implement a Unity C# `PlayerController` MonoBehaviour with WASD/arrow key movement, space bar jumping, and camera follow using a `Rigidbody` for physics — following all conventions from the unity-gamedev-standards skill.

---

## Steps Taken

### Step 1: Read SKILL.md

**File read**: `/home/user/kn-marketplace/plugins/unity-gamedev-standards/skills/unity-gamedev/SKILL.md`

Key conventions extracted:
- Private fields use `_camelCase` prefix
- `[SerializeField]` fields require `[Tooltip]` attributes
- Physics operations belong in `FixedUpdate()`
- Camera follow MUST use `LateUpdate()` — using `Update()` causes 1-frame jitter
- Use `#region` sections: Inspector Fields, Private Fields, Properties, Events, Unity Lifecycle, Public Methods, Private Methods
- Cache component references in `Awake()`
- Unsubscribe events in `OnDisable()` to prevent memory leaks
- Do NOT override Rigidbody/component properties in `Awake()` or `Start()` — Inspector is source of truth
- Use `[Header]` to group Inspector fields
- Use `[Range]` when values have logical bounds

### Step 2: Read references/coding-rules.md

**File read**: `/home/user/kn-marketplace/plugins/unity-gamedev-standards/skills/unity-gamedev/references/coding-rules.md`

Key conventions confirmed and added:
- Naming: classes = PascalCase, private fields = `_camelCase`, constants = `SCREAMING_SNAKE_CASE`, methods = PascalCase, parameters/locals = camelCase
- All serialized fields require `[Tooltip]`
- `[Range]` attribute required when values have logical bounds
- `[Header]` groups related Inspector fields
- Standard `#region` structure confirmed: Inspector Fields → Private Fields → Properties → Events → Unity Lifecycle → Public Methods → Private Methods
- Unity lifecycle order: `Awake()` → `OnEnable()` → `Start()` → `FixedUpdate()` → `Update()` → `LateUpdate()` → `OnDisable()` → `OnDestroy()`
- Event pattern: subscribe in `OnEnable()`, unsubscribe in `OnDisable()`
- Use `TryGetComponent<T>()` instead of `GetComponent<T>() != null`
- Never leave empty Unity callbacks (overhead cost)
- Prefer `[SerializeField] private` over `public` fields

### Step 3: Read references/camera-systems.md

**File read**: `/home/user/kn-marketplace/plugins/unity-gamedev-standards/skills/unity-gamedev/references/camera-systems.md`

Critical requirements extracted:
- Camera follow position/rotation MUST be in `LateUpdate()` — never `Update()` or `FixedUpdate()`
- When following a Rigidbody-based character, the target Rigidbody MUST have `Interpolation = Interpolate` set in the Inspector (not in code)
- Use `[DefaultExecutionOrder(100)]` on camera scripts to guarantee they run after all default-order scripts in `LateUpdate()`
- Reference `FollowCamera` pattern confirmed: `Vector3.Lerp` for smooth position, `LookAt` for rotation, null check on target
- Input reading (e.g., mouse input for orbit) goes in `Update()`; camera position/rotation goes in `LateUpdate()`

### Step 4: Plan Implementation

Based on the documentation review, the implementation was designed as two separate MonoBehaviours:

1. **`PlayerController`** — handles input in `Update()` and physics in `FixedUpdate()`
   - `HandleMovementInput()`: reads `Input.GetAxisRaw("Horizontal")` and `Input.GetAxisRaw("Vertical")`
   - `HandleJumpInput()`: sets `_jumpRequested = true` on Space when grounded
   - `CheckGrounded()`: uses `Physics.Raycast` downward; fires `OnLanded` event on landing
   - `ApplyMovement()`: sets `_rigidbody.linearVelocity` preserving Y
   - `ApplyJump()`: applies `ForceMode.Impulse` upward, fires `OnJumped` event

2. **`PlayerFollowCamera`** — camera follow exclusively in `LateUpdate()`
   - `UpdateCameraPosition()`: `Vector3.Lerp` toward `_target.position + _offset`
   - `UpdateCameraRotation()`: `Quaternion.Slerp` toward `LookRotation` for smooth look-at

### Step 5: Write Implementation

Applied all conventions:
- `#region` sections in both classes
- `[SerializeField]` + `[Tooltip]` + `[Range]` on all inspector fields
- `[Header]` groups for organization
- `_camelCase` for all private fields
- PascalCase for all methods and properties
- `Awake()` used only for caching `_rigidbody = GetComponent<Rigidbody>()`
- `OnDisable()` unsubscribes/clears events
- No Rigidbody property values set in code (Inspector is source of truth)
- `[RequireComponent(typeof(Rigidbody))]` on `PlayerController`
- `[DefaultExecutionOrder(100)]` on `PlayerFollowCamera`
- Camera uses `LateUpdate()` exclusively for position/rotation
- Jump flag (`_jumpRequested`) bridges `Update()` input detection to `FixedUpdate()` application
- Setup instructions note to enable `Rigidbody > Interpolation` in the Inspector

### Step 6: Save Output Files

- Saved `response.md` with full C# implementation and setup instructions
- Saved `transcript.md` (this file) with steps taken
- Saved `metrics.json` with execution metrics

---

## References Consulted

| File | Purpose |
|------|---------|
| `SKILL.md` | Primary standards overview — naming, regions, lifecycle, camera rules |
| `references/coding-rules.md` | Complete naming conventions, region structure, event pattern, null handling |
| `references/camera-systems.md` | Camera `LateUpdate()` requirement, `DefaultExecutionOrder`, Rigidbody interpolation |
