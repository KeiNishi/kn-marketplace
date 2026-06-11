# Godot Scene-Load Race Condition — Debugging Analysis

## Short answer: No, do not keep the wait.

The 0.5-second `await`/`yield` is a textbook workaround that shrinks the race window rather than closing it. On a slow machine, a long load, or under future changes, the window will widen again and the crash will return—likely in a shipped build where it is hardest to diagnose. The Rationalization Table entry applies directly here:

> "It's just a timing issue, I'll add a small delay" — Delays shrink the race window; they never close it. Find the missing ordering guarantee.

Below is the full systematic path to the real fix.

---

## Phase 1: Reproduce

**Current state:** Crashes ~1 in 10 times. That is not yet a reliable reproduction.

**Goal:** Make it crash every time (or capture one full failing run with enough logging to read the story).

### Steps to make it deterministic

1. **Force slow loading** — Godot's `ResourceLoader` can be throttled or you can load from a slow path. In the editor, add an artificial stall to your scene-loading code:
   ```gdscript
   # TEMP DEBUG ONLY — remove before shipping
   OS.delay_msec(1)  # forces a one-frame yield, widens the race window
   ```
   Or strip the `await` entirely and run on the slowest device available. The goal is to make the window large enough that it fires reliably.

2. **Run repeated load/unload cycles in a loop** — Add a debug key that repeatedly switches scenes 50 times. The crash should appear within the first few cycles:
   ```gdscript
   # debug_runner.gd  (attach temporarily, delete afterward)
   func _input(event):
       if event.is_action_pressed("ui_accept"):
           for i in range(50):
               get_tree().change_scene_to_file("res://your_scene.tscn")
               await get_tree().process_frame
   ```

3. **Enable full error logging** before running the loop. In Godot: **Project → Project Settings → Debug → Settings → Verbose stdout = ON**. Capture the terminal output so you have the frame number and call stack for the failing run.

**Gate:** Do not proceed to Phase 2 until you can trigger the crash in ≤5 attempts. If you cannot, add more logging (see Phase 2 below) and capture one failing run's full output.

---

## Phase 2: Isolate

Once you can trigger the crash reliably (or have a captured failing run), locate the exact ordering violation.

### Add high-value log lines

Instrument the two sides of the race: the scene load completion and the first code that touches enemies.

```gdscript
# In your scene-loading code (wherever you call change_scene / instantiate enemies):
print("[FRAME %d] scene_load: starting enemy spawn" % Engine.get_process_frames())

# In each enemy's _ready():
print("[FRAME %d] enemy_ready: node=%s" % [Engine.get_process_frames(), name])

# In the code that USES enemies after the scene loads (the crash site):
print("[FRAME %d] consumer: about to access enemies, count=%d" % [
    Engine.get_process_frames(), enemies.size()])
for e in enemies:
    print("[FRAME %d] consumer: enemy valid=%s" % [Engine.get_process_frames(), is_instance_valid(e)])
```

**What to read in the log:** On a failing run you will see the consumer frame number appear *before* all `enemy_ready` frame numbers. That ordering is the race.

### Bisect by system

If you cannot immediately tell from the logs which code path runs first, disable systems one at a time:
- Remove enemies from the scene entirely → no crash → enemies are the subject (expected).
- Leave one enemy in a minimal scene → crash still fires → the bug is not enemy-count-dependent, it is ordering-dependent.
- Replace the spawned enemies with a static `Node` that has no logic → crash disappears → the issue is in enemy initialization (`_ready` or deferred calls), not in the scene tree itself.

---

## Phase 3: Root-Cause

**Hypothesis (consistent with all evidence):**

> The scene-loading code accesses or iterates the enemy list (or calls methods on enemy nodes) *before* those nodes have finished initializing — specifically before their `_ready()` functions have run — because `change_scene_to_file` / `add_child` defers `_ready` to the next frame, but the consuming code runs in the same frame as `add_child`.

**Why the 0.5 s wait "fixes" it:** It delays the consumer by enough frames that `_ready` has always run by then. But this is coincidental — the ordering is still not guaranteed by the engine, just made very unlikely.

**The disproof test:**

Add an assertion at the crash site before any enemy access:

```gdscript
for e in enemies:
    assert(e != null and e.is_inside_tree(),
        "RACE: enemy not ready at frame %d" % Engine.get_process_frames())
```

- If this assertion fires on a crashing run: **hypothesis confirmed** — the consumer runs before nodes are ready.
- If it never fires even on a crashing run: the null comes from somewhere else (e.g., an enemy that was freed mid-frame by another system). Form a new hypothesis and test it.

Run this without the 0.5 s wait. If the assertion fires, root cause is confirmed.

---

## Phase 4: Fix

Once the root cause is confirmed — "consumer code accesses enemy nodes before their `_ready` has run because `add_child` defers `_ready` to the end of the frame" — the correct fix depends on which side of the race you control:

### Option A: Use the engine's load-complete signal (preferred)

If you are using `ResourceLoader` in background/threaded mode, use the signal it provides rather than a frame count:

```gdscript
# Loading side
func _load_scene():
    ResourceLoader.load_threaded_request("res://enemy_scene.tscn")

func _process(_delta):
    var status = ResourceLoader.load_threaded_get_status("res://enemy_scene.tscn")
    if status == ResourceLoader.THREAD_LOAD_LOADED:
        var packed = ResourceLoader.load_threaded_get("res://enemy_scene.tscn")
        var enemy = packed.instantiate()
        add_child(enemy)
        # enemy._ready() has NOT run yet here — do not touch it
        # Instead, call your setup method from enemy._ready() itself,
        # or connect to its own "ready" signal:
        enemy.ready.connect(_on_enemy_ready.bind(enemy))

func _on_enemy_ready(enemy: Node):
    # Safe: _ready has run, node is fully initialized
    enemies.append(enemy)
    _start_wave()
```

### Option B: Move consumer logic into `_ready` of the spawned scene's root node

If enemies are the root of the scene being loaded, put the "register with manager" call inside the enemy's own `_ready`:

```gdscript
# enemy.gd
func _ready():
    # By the time _ready runs, the node is fully inside the tree
    GameManager.register_enemy(self)
```

The manager then only accesses enemies after they self-register — no race possible.

### Option C: Use `call_deferred` on the consumer side

If the consumer must run at `add_child` time, defer the access to end-of-frame (after `_ready` runs):

```gdscript
add_child(enemy)
call_deferred("_setup_enemy", enemy)  # runs after _ready

func _setup_enemy(enemy: Node):
    enemies.append(enemy)
```

**Note:** `call_deferred` guarantees the call runs after `_ready` for that node, because Godot processes deferred calls after the scene-tree notifications flush. This is an ordering guarantee, not a timing guess.

### What NOT to do

```gdscript
# DO NOT DO THIS — this is exactly the workaround you asked about
await get_tree().create_timer(0.5).timeout
_setup_enemies()
```

This has no engine guarantee. A slow machine, a heavy frame, or a different load path will break it again.

---

## Verification Checklist

Before declaring the bug fixed:

- [ ] Crash was reproduced on demand (loop test, no wait) before any fix was written
- [ ] Root cause stated as: "consumer accesses enemy nodes in the same frame as `add_child`, before `_ready` runs" — confirmed by the assertion firing on failing runs
- [ ] The fix uses an engine ordering guarantee (`ready` signal, self-registration in `_ready`, or `call_deferred`) — not a timer
- [ ] The loop test (50 scene switches) runs without a single crash after the fix
- [ ] The 0.5 s wait and all debug logging are removed
- [ ] Behavior verified at both low and high FPS (run with `Engine.max_fps = 10` and `Engine.max_fps = 0`)
- [ ] No null checks or try/catch were added around the crash site without explaining why the null existed

---

## Summary

| | Workaround (keep the wait) | Correct fix |
|---|---|---|
| Closes the race? | No — shrinks the window | Yes — removes the window |
| Shipping risk | Crashes in builds on slow hardware | None |
| Engine guarantee | None | `_ready` signal / deferred call ordering |
| Code complexity | One line | ~3–5 lines, properly structured |

Do not keep the wait. Reproduce the crash without it, confirm the ordering violation with the assertion, then apply whichever Option (A/B/C) fits your architecture.
