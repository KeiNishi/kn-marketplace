# Save/Load Inventory Drift — Debugging Walkthrough

## First: The Proposed Workaround Is Off The Table

> "I'm tempted to just re-sort the inventory on load to hide it."

This is a textbook workaround: it masks the symptom (wrong slot/count after load) without finding why the data is wrong. Per the debugging discipline, this is forbidden. The re-sort would hide the evidence, make root-cause investigation harder in the future, and leave the real corruption silently in the save file. We do not proceed with it.

---

## Where We Are: Phase 1 — Reproduce

**The Iron Law applies.** We have a bug report but no reproduction. The symptom is:

- After save → reload, inventory items occasionally swap slots or a stack count is off by one.
- Cannot be reproduced locally.
- Reported by players, so it is not universal but not rare.

Before writing any code, we must make this happen deterministically. Here is the exact plan.

---

## Phase 1: Making the Bug Reproducible

### Step 1 — Get the Exact Recipe (Information Needed From the User)

I need the following before doing anything else:

1. **Engine and version** (Unity, Godot, custom, etc.)
2. **Save format** (JSON, binary, custom serializer, engine built-in?)
3. **Platform** where players are seeing this — PC only, mobile, console? Any pattern?
4. **Frequency** — 1 in 5 saves? 1 in 50? Always on a specific item type?
5. **Affected item types** — does it happen with stackable items only? Equipped items? Any item?
6. **Any recent changes** to the save system or inventory system? (If yes, when?)

Since the user has not provided these and the debugging skill says to ask — but also to keep going where possible — I will proceed with the analysis using the information we do have, and flag where each missing piece would gate further progress.

### Step 2 — Pin Down Nondeterminism

The symptom ("occasionally wrong") and the "can't reproduce locally" together strongly suggest one or more sources of nondeterminism. The candidates for a save/load inventory bug are well-known:

| Nondeterminism source | How to pin it |
|---|---|
| Dictionary/hash-map iteration order | Use a deterministic ordered structure for serialization (sorted array, not a dict) |
| Uninitialized or unserialized fields | Add logging of every field on save and on load; compare the two |
| Float precision across platforms/builds | Log raw serialized bytes; compare save file hex between platforms |
| Version mismatch between save schema and current code | Log schema version on save; assert it matches on load |
| Race condition on async save | Log save start/complete with frame number; check if game state mutates during the write |
| Stack count off-by-one | Classic sign of a fence-post error or an "add item before/after save flush" race |

**The first experiment to run:**

Add a canonical "inventory checksum" — a simple sum of (slot_index * item_id + stack_count) for every slot — computed:
1. Immediately before the save write begins.
2. Immediately after the load completes.

Log both values with a frame counter. If they ever differ, you have a captured failing case. This is cheap to add and gives a reusable reproduction trigger.

```
// Pseudocode — engine-agnostic
int InventoryChecksum(Inventory inv) {
    int sum = 0;
    for (int i = 0; i < inv.slots.Count; i++) {
        if (inv.slots[i] != null) {
            sum += i * inv.slots[i].itemId + inv.slots[i].stackCount;
        }
    }
    return sum;
}

// On save:
Log("SAVE checksum=" + InventoryChecksum(playerInventory) + " frame=" + frameCount);
SaveToDisk(playerInventory);

// On load complete:
LoadFromDisk(playerInventory);
Log("LOAD checksum=" + InventoryChecksum(playerInventory) + " frame=" + frameCount);
```

**Gate:** If the checksums match, the save file itself is fine and the bug is in post-load logic. If they differ, the serialization or deserialization is the source. This single log line cuts the search space in half.

### Step 3 — Stress the Suspected Condition

Because it "only happens sometimes", run a stress loop in a test build:

```
// Pseudocode
for (int i = 0; i < 1000; i++) {
    FillInventoryWithTestItems();   // deterministic, same items every time
    Save();
    Load();
    AssertInventoryMatchesExpected();  // hard assert, crash on first mismatch
}
```

Run this with:
- A fixed random seed for any RNG involved in inventory generation.
- A fixed timestep / no async (synchronous save and load, blocking).

If the stress loop reproduces it, you now have a deterministic test. If it does not, the bug depends on something the loop is not exercising — the most likely culprits then are:
- **Async timing**: the game mutates the inventory while the save is still writing.
- **Platform difference**: the bug only triggers on the player's hardware/OS due to float or dictionary-order differences.

---

## Phase 2: Isolate (Conditional on Reproduction)

Once the checksum log catches a mismatch, the next steps are:

1. **Log every slot on save and on load** (slot index, item ID, stack count). Compare the two logs side by side. The first diverging slot is the failure point.

2. **Bisect: is this a single item type?** Test with only stackable items, then only unique items, then only equipped items. If one category reproduces and another does not, the bug is in the serialization path for that category.

3. **Bisect: is this slot-order or count?**
   - Items in wrong slots → likely an ordering bug (dictionary iteration order, or items sorted differently on load).
   - Stack count off by one → likely a fence-post or a mutation race (item added/removed during the save window).

4. **Diff the save file directly.** Open the raw save file (JSON or hex) from a failing session. Does it contain the wrong data, or does the right data get mis-read on load?
   - Wrong data in file → the bug is in the save path (mutation during write, or serialization logic).
   - Correct data in file → the bug is in the load path (deserialization, field mapping, version migration).

---

## Phase 3: Root-Cause Hypotheses (Most Likely Given the Symptoms)

The symptom signature — "items swap slots OR stack count off by one, occasionally, not reproducible locally" — maps to a small set of known root-cause families:

### Hypothesis A (Most Likely): Dictionary/Map Iteration Order

If inventory slots are stored in a `Dictionary<int, Item>` (or equivalent hash map) and serialized by iterating the dictionary, the iteration order is not guaranteed to be consistent across platforms, engine versions, or even runs. Items saved in one order get loaded in another order, appearing to "swap slots."

**Disproof test:** Replace the dictionary serialization with an explicitly sorted array (sorted by slot index). If the bug disappears, this was it.

### Hypothesis B (Second Most Likely): Mutation Race During Async Save

If save is async (writes to disk on a background thread or coroutine), and game code can add/remove items while the save is in progress, the serialized data captures a torn state. Stack count off by one is a classic sign: an item was added (incrementing the count) between when the slot was read for serialization and when the write completed.

**Disproof test:** Make save synchronous and blocking (freeze the game loop, disable all inventory mutations, then write). If the bug disappears in the stress loop, the race is confirmed.

### Hypothesis C: Unserialized Field / Default Value On Load

A field on the item or slot struct is not included in the serialization schema. On load, it gets its default value (0, null, or false), which shifts the apparent slot or count. This is common after a schema change where a new field was added to the struct but not added to the save/load code.

**Disproof test:** Log every field of every item on save and on load. Find the field that differs.

### Hypothesis D: Off-By-One In Stack Count During Save

The stack count serialization uses `count - 1` or `count + 1` by mistake, or a "pick up one" action fires during the save frame and is double-counted.

**Disproof test:** The checksum log will catch this. Once caught, inspect the raw serialized value in the save file vs. the in-memory value at the moment of save.

---

## Phase 4: Fix Pattern (After Root Cause Is Confirmed)

The fix depends entirely on which hypothesis is confirmed. But the pattern for each is:

| Root cause | Correct fix |
|---|---|
| Dictionary iteration order | Serialize inventory as a sorted array `[(slotIndex, itemId, stackCount), ...]`, not a dict |
| Async mutation race | Snapshot the inventory into an immutable struct before starting the async write; write from the snapshot, not from live state |
| Unserialized field | Add the field to the serialization schema; add a migration step for old save files |
| Off-by-one in count | Fix the arithmetic at the exact site; verify with the stress loop |

In all cases: the fix is minimal and targets only the confirmed cause. No drive-by refactors.

---

## Current Status: Blocked at Phase 1 — Reproduction Not Yet Achieved

**What I actually have:** A bug report with symptom description. No save file, no stack trace, no log output, no confirmed reproduction steps.

**What gates progress:**

1. Add the checksum log to the save and load paths (can be done now — see pseudocode above).
2. Run the stress loop in a test build.
3. If neither catches it locally, deploy the checksum log to players and collect a failing log.

**Do not write any inventory sorting, clamping, or default-value-filling logic yet.** That is the workaround path. The task right now is to catch the bug in the act.

---

## Files Created for Reference

The following file contains the checksum and stress-loop pseudocode in a copyable form:

`/tmp/eval-work/save-w/debug_inventory_checksum.md`

---

## What I Would Run (If the Engine Were Available)

```bash
# 1. Build a test scene with a fixed inventory and a save/load loop
# 2. Run 1000 iterations with a fixed seed
# 3. Assert checksum matches after every load
# Game engines not installed in this environment — the above would be the
# first shell command once the project is open in the engine editor.
```

Because game engines are not installed in this environment, I cannot execute the stress loop directly. The steps above describe exactly what to run and what each result means. The debugging discipline is fully applied: no fix has been written, the workaround has been rejected, and the next concrete action is the checksum log.
