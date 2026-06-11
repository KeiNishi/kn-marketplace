# Save/Load Inventory Drift — Root Cause Analysis & Fix

## On the temptation to re-sort on load

Do not do it. Re-sorting on load is exactly the kind of workaround that masks the
bug rather than fixing it. Players who deliberately place items in specific slots
(hotbar muscle-memory, crafting quick-access, etc.) would see their layout
silently scrambled every reload. And the off-by-one stack count would still be
there, just hidden inside a tidied-up layout. The root cause must be fixed at the
serialisation boundary.

---

## Root causes

Two independent bugs combine to produce the intermittent symptoms.

### Bug 1 — Slot index not preserved during save

The most common pattern in buggy save code looks like this:

```python
# BUGGY
items = []
for slot in self.slots:
    if slot is not None:
        items.append({"item_id": slot.item_id, "count": slot.count})
save_to_disk({"items": items})
```

Only non-empty slots are written, with no record of *which* slot index they
occupied. On load, items are re-inserted sequentially into slots 0, 1, 2, …
regardless of gaps in the original inventory:

```
Original:   [sword, EMPTY, arrow, potion, EMPTY]
Saved JSON: [sword, arrow, potion]          ← indices lost
Restored:   [sword, arrow, potion, EMPTY, EMPTY]  ← shifted left
```

Every item that originally lived after an empty slot ends up one position earlier.
This explains the "items swap slots" report. It reproduces only when the player
has at least one gap in their inventory — which is why it cannot be reproduced on
a freshly-filled test inventory.

### Bug 2 — Float count causes off-by-one on reload

Stack counts become floats somewhere in the game logic (common sources: integer
division with `//` that later gets mixed with `/`, physics/time-step arithmetic
applied to counts, or a scripting bridge that returns all numbers as floats).
The value `64` becomes `63.9999…` in floating-point. When the loader casts with
`int()` (truncation, not rounding), `int(63.999…)` → `63`. The stack appears to
have lost one item after every save/load cycle.

---

## The fix

Fix both issues at the serialisation boundary — the save and load functions.

### Fixed save: store slot index explicitly, cast count to int

```python
def save(self) -> str:
    slots_data = []
    for idx, slot in enumerate(self.slots):
        if slot is None:
            slots_data.append({"slot": idx, "empty": True})
        else:
            slots_data.append({
                "slot": idx,
                "empty": False,
                "item_id": slot.item_id,
                "count": int(slot.count),   # explicit cast; kills float drift
            })
    return json.dumps({"version": 1, "size": self.size, "slots": slots_data})
```

Key decisions:
- **Every slot is written**, including empty ones. The slot index is the primary
  key; order in the JSON array is irrelevant.
- `int(slot.count)` at the write boundary means no float can survive into the
  file. If you want to catch upstream float counts early, add an assertion:
  `assert isinstance(slot.count, int), f"Non-int count in slot {idx}"`.
- A `version` field and a `size` field are included so the loader can validate
  the save before touching live data.

### Fixed load: restore by index, validate before writing

```python
def load(self, data: str) -> None:
    parsed = json.loads(data)
    if parsed.get("version") != 1:
        raise ValueError(f"Unsupported save version: {parsed.get('version')}")
    if parsed["size"] != self.size:
        raise ValueError(
            f"Inventory size mismatch: save={parsed['size']}, current={self.size}"
        )
    new_slots = [None] * self.size
    for entry in parsed["slots"]:
        idx = entry["slot"]
        if idx < 0 or idx >= self.size:
            raise ValueError(f"Slot index {idx} out of range.")
        if not entry["empty"]:
            new_slots[idx] = ItemStack(
                item_id=entry["item_id"],
                count=int(entry["count"]),
            )
    self.slots = new_slots   # atomic swap — old data kept until fully validated
```

Key decisions:
- Items are placed at `parsed["slot"]`, not at the insertion cursor. Gaps are
  preserved automatically.
- All validation happens before `self.slots` is modified (atomic swap at the end).
  A corrupt save file cannot leave the inventory in a half-written state.
- `int(entry["count"])` on load as a second line of defence, in case a legacy
  save file slipped a float through.

---

## Complete self-contained reference implementation

The file below is a runnable Python module (no game engine required) that
demonstrates both the buggy and fixed paths and asserts the correct behaviour.

```python
"""
inventory.py — Reference implementation showing the BUGGY patterns and their fixes.
Run with:  python inventory.py
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Optional

MAX_STACK = 64


@dataclass
class ItemStack:
    item_id: str
    count: int

    def to_dict(self) -> dict:
        return {"item_id": self.item_id, "count": self.count}

    @staticmethod
    def from_dict(d: dict) -> "ItemStack":
        return ItemStack(item_id=d["item_id"], count=d["count"])


@dataclass
class Inventory:
    size: int
    slots: list[Optional[ItemStack]] = field(default_factory=list)

    def __post_init__(self):
        if not self.slots:
            self.slots = [None] * self.size

    # ── BUGGY version ──────────────────────────────────────────────────────────

    def save_buggy(self) -> str:
        items = []
        for slot in self.slots:
            if slot is not None:
                items.append({"item_id": slot.item_id, "count": float(slot.count)})
        return json.dumps({"items": items})  # NO slot index stored!

    def load_buggy(self, data: str) -> None:
        parsed = json.loads(data)
        self.slots = [None] * self.size
        insert_pos = 0
        for entry in parsed["items"]:
            if insert_pos >= self.size:
                break
            self.slots[insert_pos] = ItemStack(
                item_id=entry["item_id"],
                count=int(entry["count"]),   # truncates float → off-by-one
            )
            insert_pos += 1

    # ── FIXED version ─────────────────────────────────────────────────────────

    def save_fixed(self) -> str:
        slots_data = []
        for idx, slot in enumerate(self.slots):
            if slot is None:
                slots_data.append({"slot": idx, "empty": True})
            else:
                slots_data.append({
                    "slot": idx,
                    "empty": False,
                    "item_id": slot.item_id,
                    "count": int(slot.count),
                })
        return json.dumps({"version": 1, "size": self.size, "slots": slots_data})

    def load_fixed(self, data: str) -> None:
        parsed = json.loads(data)
        if parsed.get("version") != 1:
            raise ValueError(f"Unsupported save version: {parsed.get('version')}")
        saved_size = parsed["size"]
        if saved_size != self.size:
            raise ValueError(
                f"Inventory size mismatch: save has {saved_size} slots, "
                f"current inventory has {self.size}."
            )
        new_slots: list[Optional[ItemStack]] = [None] * self.size
        for entry in parsed["slots"]:
            idx = entry["slot"]
            if idx < 0 or idx >= self.size:
                raise ValueError(f"Slot index {idx} out of range for size {self.size}.")
            if not entry["empty"]:
                new_slots[idx] = ItemStack(
                    item_id=entry["item_id"],
                    count=int(entry["count"]),
                )
        self.slots = new_slots


# ─────────────────────────────────────────────
# Demonstration / self-test
# ─────────────────────────────────────────────

def make_inventory() -> Inventory:
    inv = Inventory(size=5)
    inv.slots[0] = ItemStack("sword", 1)
    # slot 1 intentionally empty (gap)
    inv.slots[2] = ItemStack("arrow", 64)
    inv.slots[3] = ItemStack("potion", 3)
    # slot 4 intentionally empty
    return inv


def slots_equal(a: Inventory, b: Inventory) -> bool:
    if len(a.slots) != len(b.slots):
        return False
    for sa, sb in zip(a.slots, b.slots):
        if sa is None and sb is None:
            continue
        if sa is None or sb is None:
            return False
        if sa.item_id != sb.item_id or sa.count != sb.count:
            return False
    return True


def run_demo():
    original = make_inventory()

    saved_buggy = original.save_buggy()
    restored_buggy = Inventory(size=5)
    restored_buggy.load_buggy(saved_buggy)

    print("=== BUGGY round-trip ===")
    for i, (orig, rest) in enumerate(zip(original.slots, restored_buggy.slots)):
        orig_str = f"{orig.item_id}×{orig.count}" if orig else "EMPTY"
        rest_str = f"{rest.item_id}×{rest.count}" if rest else "EMPTY"
        match = "OK" if orig_str == rest_str else "MISMATCH <──"
        print(f"  slot {i}: orig={orig_str:20s}  restored={rest_str:20s}  {match}")

    saved_fixed = original.save_fixed()
    restored_fixed = Inventory(size=5)
    restored_fixed.load_fixed(saved_fixed)

    print("\n=== FIXED round-trip ===")
    for i, (orig, rest) in enumerate(zip(original.slots, restored_fixed.slots)):
        orig_str = f"{orig.item_id}×{orig.count}" if orig else "EMPTY"
        rest_str = f"{rest.item_id}×{rest.count}" if rest else "EMPTY"
        match = "OK" if orig_str == rest_str else "MISMATCH <──"
        print(f"  slot {i}: orig={orig_str:20s}  restored={rest_str:20s}  {match}")

    assert not slots_equal(original, restored_buggy), "Bug demo: expected mismatch"
    assert slots_equal(original, restored_fixed),     "Fix demo: expected match"
    print("\nAll assertions passed.")


if __name__ == "__main__":
    run_demo()
```

Running `python inventory.py` produces:

```
=== BUGGY round-trip ===
  slot 0: orig=sword×1               restored=sword×1               OK
  slot 1: orig=EMPTY                 restored=arrow×64              MISMATCH <──
  slot 2: orig=arrow×64              restored=potion×3              MISMATCH <──
  slot 3: orig=potion×3              restored=EMPTY                 MISMATCH <──
  slot 4: orig=EMPTY                 restored=EMPTY                 OK

=== FIXED round-trip ===
  slot 0: orig=sword×1               restored=sword×1               OK
  slot 1: orig=EMPTY                 restored=EMPTY                 OK
  slot 2: orig=arrow×64              restored=arrow×64              OK
  slot 3: orig=potion×3              restored=potion×3              OK
  slot 4: orig=EMPTY                 restored=EMPTY                 OK

All assertions passed.
```

---

## Why you cannot reproduce it locally

Both bugs are gap-dependent:

- Bug 1 only manifests when there is at least one empty slot *before* a filled slot.
  A sequential test inventory (`[A, B, C, D, E]`) has no gaps and loads perfectly.
- Bug 2 depends on float arithmetic upstream. If your local test path constructs
  `ItemStack` with integer literals, the float never appears.

**How to reproduce locally:**

1. Give the player an inventory with at least one gap (e.g., pick up items into
   slots 0 and 2, leave 1 empty).
2. For Bug 2: apply any calculation to the stack count that could return a float
   (crafting yield, split-stack logic using `/`).
3. Save, quit, reload, and inspect slot positions and stack counts.

---

## Migration plan for existing save files

If players already have saves in the buggy format you need a migration step:

```python
def load_with_migration(self, data: str) -> None:
    parsed = json.loads(data)
    version = parsed.get("version", 0)
    if version == 0:
        # Legacy format: sequential insertion, no slot indices
        # We cannot recover the original slot positions — tell the player.
        self._load_legacy_v0(parsed)
    elif version == 1:
        self.load_fixed(data)
    else:
        raise ValueError(f"Unknown save version {version}")

def _load_legacy_v0(self, parsed: dict) -> None:
    """
    Best-effort load of old saves. Items are placed sequentially from slot 0.
    A one-time warning should be shown to the player that their layout has been
    reset; their item types and counts (minus any float truncation) are preserved.
    """
    self.slots = [None] * self.size
    for i, entry in enumerate(parsed.get("items", [])):
        if i >= self.size:
            break
        self.slots[i] = ItemStack(
            item_id=entry["item_id"],
            count=round(entry["count"]),   # round, not int(), to fix truncation
        )
```

Use `round()` instead of `int()` in the legacy loader to recover the off-by-one
counts from old saves. From v1 onwards, the format stores clean ints so `int()`
and `round()` are equivalent.

---

## Checklist before closing the bug

- [ ] Save function writes `slot` index for every entry (including empty slots).
- [ ] Count is cast to `int` at the write boundary and guarded with `round()` in
      the legacy loader.
- [ ] Load function places items at `entry["slot"]`, not at an insertion cursor.
- [ ] Load function validates `version` and `size` before modifying live data.
- [ ] At least one test exercises an inventory with gaps (empty slots between filled ones).
- [ ] Existing save files are migrated or players are warned about layout reset.
- [ ] Re-sort-on-load workaround is NOT applied (it hides symptoms, does not fix the cause).
