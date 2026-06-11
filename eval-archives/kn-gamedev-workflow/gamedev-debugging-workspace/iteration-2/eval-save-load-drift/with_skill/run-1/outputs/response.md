# Save/Load Inventory Drift — Debugging Report

## What You Described

> After saving and reloading, inventory is occasionally wrong — items swap slots or a stack count is off by one. Can't reproduce locally. Tempted to re-sort the inventory on load to hide it.

**Stop.** Re-sorting on load is a textbook workaround — it would mask the symptom while the serialization defect persists and manifests in other ways (item loss, ability state corruption, quest flags). The SKILL.md Iron Law applies: no fix without a reproduced root cause first. This report delivers the full pipeline: reproduction harness, ranked hypotheses with disproof tests, and the correct fix for the leading hypothesis — so you can act the moment the harness confirms a cause.

---

## Phase 1 — Reproduce

The bug is intermittent and cannot be reproduced locally. That combination almost always means one of:

- The reproduction depends on **data state** not present locally (a particular inventory configuration that exposes the bug).
- The reproduction depends on **timing** — a race in async save/load, or different code path ordering.
- The reproduction depends on **platform or build differences** (different serialization library behavior in release vs. debug, different dictionary/map iteration order on a different runtime or OS).

### Reproduction Harness (engine-agnostic pseudocode)

Create `/tmp/eval-work/save-w2/repro_harness.gd` (Godot example; adapt for your engine):

```gdscript
# repro_harness.gd
# Run this in a test scene. It cycles save→load N times and asserts
# the inventory round-trips identically each time.
# Gate behind a compile flag or a hidden debug menu so it never ships.

extends Node

const CYCLES := 200
const SEED   := 42        # fixed seed — eliminates RNG as a variable

func _ready() -> void:
    randomize_seed(SEED)
    var inventory := _build_test_inventory()
    var failures  := 0
    for i in range(CYCLES):
        var saved  := SaveSystem.serialize(inventory)
        var loaded := SaveSystem.deserialize(saved)
        if not _inventories_equal(inventory, loaded):
            failures += 1
            print("[REPRO] Cycle %d FAILED" % i)
            _diff_inventories(inventory, loaded)
    print("[REPRO] %d / %d cycles failed" % [failures, CYCLES])

func _build_test_inventory() -> Array:
    # Replicate the exact slot count and stack sizes players report failing with.
    # Start with a full 30-slot inventory, mixed stackable and unique items.
    var inv := []
    for slot in range(30):
        inv.append({
            "item_id": "item_%02d" % (slot % 10),
            "count":   (slot % 5) + 1,
            "slot":    slot,
        })
    return inv

func _inventories_equal(a: Array, b: Array) -> bool:
    if a.size() != b.size():
        return false
    for i in range(a.size()):
        if a[i] != b[i]:
            return false
    return true

func _diff_inventories(expected: Array, actual: Array) -> void:
    for i in range(max(expected.size(), actual.size())):
        var e = expected[i] if i < expected.size() else null
        var ac = actual[i]  if i < actual.size()  else null
        if e != ac:
            print("  slot %d: expected %s  got %s" % [i, str(e), str(ac)])
```

**What this does:** forces 200 save/load cycles with a fixed RNG seed, fixed inventory state, and prints a slot-level diff on the first failure. A bug that fires 1-in-20 manually will fire within ~200 automated cycles.

**What gates progress:** run the harness. If it fires — you have a captured failing case and can proceed to Phase 2. If it does not fire after 200 cycles, the bug is data-dependent; collect the actual save file from a player who hit it and replay with that file's inventory as the starting state.

---

## Phase 2 — Isolate

Once the harness fires, answer these bisection questions to shrink the search space:

1. **Does it fail with a single-item inventory?** If yes → the slot/count serialization itself is broken. If only with many items → ordering or indexing is the issue.
2. **Does it fail with only unique (non-stackable) items?** Isolates count drift from slot drift.
3. **Does it fail only with stackable items?** If yes → count serialization path is suspect.
4. **Does it fail if you serialize/deserialize to a plain dictionary instead of your save-file format?** Isolates the serializer from the format-writer.
5. **Log the frame counter and the wall-clock timestamp** at save and load calls. If those are ever interleaved (async), you have a race.

---

## Phase 3 — Root-Cause Hypotheses (Ranked)

These are ranked by how commonly each causes exactly this symptom (slot swap + off-by-one count, intermittent, not reproducible locally).

### Hypothesis 1 — Dictionary/Array Iteration Order Is Non-Deterministic (Most Likely)

**Statement:** "Slots are written to the save file by iterating a dictionary or set whose iteration order is undefined; on some platforms or engine versions, iteration order differs between save and load, so slots arrive in a different order."

**Why this fits:** slot swaps (not just missing items) are the canonical fingerprint of this bug. Stack counts would also drift if the swapped items have different counts. Intermittent because dictionary ordering can be consistent within a session and diverge only after a restart or on a different machine.

**Disproof test:** Add a log line at save time that prints the slot iteration order (the sequence of slot indices as they are written). Add the same log at load time. If the sequences differ even once → confirmed.

**Fix (if confirmed):**
```gdscript
# Instead of iterating the inventory dict directly:
func serialize(inventory: Dictionary) -> Dictionary:
    var out := {}
    # Sort by slot index explicitly before serializing.
    var slots := inventory.keys()
    slots.sort()          # <-- makes order deterministic regardless of dict internals
    for slot in slots:
        out[str(slot)] = inventory[slot]
    return out

func deserialize(data: Dictionary) -> Dictionary:
    var inv := {}
    # Sort keys numerically on load too.
    var keys := data.keys()
    keys.sort_custom(func(a, b): return int(a) < int(b))
    for k in keys:
        inv[int(k)] = data[k]
    return inv
```

The fix is: **always sort by slot index before serializing, and sort numerically by key when deserializing.** Never rely on dictionary insertion order for persistence.

---

### Hypothesis 2 — Unserialized Field Carries Default Value on Load (Second Most Likely)

**Statement:** "One or more inventory fields (e.g., `count`, a sub-object field) is not included in the serialized payload; on load it initializes to a default (typically 0 or 1), producing the off-by-one."

**Why this fits:** off-by-one count drift is the canonical fingerprint of a missing serialized field that happens to have a default of 1. Intermittent if the field is only set on certain item types (rare items, items acquired via a code path that sets an optional field).

**Disproof test:** Add an assertion immediately after load: for every item, assert `loaded_item.count == expected_item.count`. Log the full serialized JSON blob for any item whose count differs. If the count is missing from the JSON blob → confirmed.

**Fix (if confirmed):** Audit the serialization function against the full item struct definition. Add every field explicitly. Use a schema validation step that asserts all expected keys are present before accepting the loaded data.

---

### Hypothesis 3 — Float-to-Int Precision Loss in Count Field

**Statement:** "Stack count is serialized as a float (e.g., JSON `number` type) and deserialized back to int; floating-point representation of certain integers is imprecise and floors to N-1."

**Why this fits:** off-by-one that goes in one direction (always one less, never more). Affects only certain counts (e.g., counts that are powers of 2 minus 1 are fine; specific values near float precision boundaries are not).

**Disproof test:** Log `typeof(data["count"])` after deserialization. If it returns `TYPE_FLOAT` instead of `TYPE_INT` → confirmed. Also check whether the off-by-one always goes in the same direction; float truncation is directional.

**Fix (if confirmed):**
```gdscript
# Explicit cast on deserialize:
item.count = int(data["count"])   # not just data["count"]
```
And/or: use integer-preserving serialization (e.g., mark count fields as int in your schema, or use a binary format instead of JSON).

---

### Hypothesis 4 — Async Load Race (Least Likely Given Symptom, Worth Ruling Out)

**Statement:** "The inventory is read back before the async deserialization coroutine completes; the game sees a partially-initialized inventory and the rest fills in with defaults."

**Why this fits:** intermittent, not reproducible locally (local disk is fast; player's disk or platform I/O scheduler may be slower). Would produce larger corruption than off-by-one, but a partial race at the end of the array could produce exactly one wrong slot.

**Disproof test:** Add a log line inside the deserialization coroutine at its very last line (`print("LOAD COMPLETE frame=%d" % Engine.get_process_frames())`), and a log line when the calling code first reads the inventory. If LOAD COMPLETE ever appears *after* the read log → confirmed.

**Fix (if confirmed):** Await the load coroutine fully before allowing the game to read inventory state. Use a loading gate/flag that prevents any inventory read until load is complete.

---

## Phase 4 — Fix + Verify Checklist

Once the harness fires and a hypothesis is confirmed:

- [ ] Bug reproduced on demand via the harness (200-cycle test fires) before any fix is written
- [ ] Root cause stated as a specific, evidence-backed sentence (hypothesis number above)
- [ ] Exactly one hypothesis was confirmed by a test that could have disproved it
- [ ] Fix targets the root cause (serialization order / missing field / type cast / async gate), not the symptom
- [ ] Re-run the 200-cycle harness after the fix — it must complete with 0 failures
- [ ] Re-enable all game systems (not just the test scene) and do a manual save/load cycle with a full inventory
- [ ] Test with an old save file (pre-fix) against the new load code — backward compat
- [ ] Remove or gate behind a debug flag: the harness, any extra log lines, forced RNG seed
- [ ] No Red Flag pattern used: the fix does NOT include re-sorting on load (symptom masking)

---

## Why Re-Sorting on Load Is Prohibited

Re-sorting on load is exactly the workaround the SKILL prohibits. Analysis:

> "If you take this fix away, does the problem come back?" → Yes. The serialization defect remains; re-sorting merely hides the slot-swap symptom while the root cause continues to corrupt data in subtler ways (e.g., if two items of the same type swap, re-sorting does not detect or fix it; if the count field is wrong, re-sorting does nothing; if this is an async race, re-sorting may re-sort a partially-loaded inventory and produce different corruption).

The correct response to "I'm tempted to re-sort to hide it" is: that impulse is diagnostic information. Slot swaps that re-sorting would fix are strong evidence for Hypothesis 1 (non-deterministic iteration order). Use that evidence to confirm H1 and apply the sort-at-serialize fix instead.

---

## Summary

| Phase | Status | Next Action |
|---|---|---|
| Reproduce | Not yet — bug is intermittent | Run the 200-cycle harness; collect a player save file if harness doesn't fire |
| Isolate | Pending repro | Bisect: single item, unique vs. stackable, log iteration order |
| Root-cause | H1 (dict order) is leading candidate | Disproof test: log slot iteration order at save vs. load |
| Fix | Staged (sort-by-slot-index in serializer) | Apply only after H1 is confirmed by the disproof test |
| Verify | Pending | 200-cycle harness must show 0 failures post-fix |
