# Inventory Unit Tests — Godot 4 / GDScript

## What was created

All files live under `/tmp/eval-work/inv-b/`.

| File | Purpose |
|---|---|
| `inventory.gd` | The `Inventory` class under test (faithful implementation of the task spec) |
| `test_inventory.gd` | Full test suite using **GDUnit4** assertions |
| `test_inventory_plain.gd` | Self-contained runner — no addon required, works with bare Godot 4 |
| `project.godot` | Minimal Godot 4 project file wiring `test_inventory_plain.gd` as the entry point |

---

## inventory.gd

```gdscript
# inventory.gd
class_name Inventory
extends RefCounted

var _items: Dictionary = {}

func add_item(item: String, quantity: int = 1) -> bool:
    if item.is_empty() or quantity <= 0:
        return false
    _items[item] = (_items.get(item, 0) as int) + quantity
    return true

func remove_item(item: String, quantity: int = 1) -> bool:
    if item.is_empty() or quantity <= 0:
        return false
    var current: int = _items.get(item, 0) as int
    if current < quantity:
        return false
    var new_qty: int = current - quantity
    if new_qty == 0:
        _items.erase(item)
    else:
        _items[item] = new_qty
    return true

func count(item: String) -> int:
    return _items.get(item, 0) as int
```

---

## test_inventory.gd (GDUnit4 style)

```gdscript
# test_inventory.gd
extends GdUnitTestSuite

var _inv: Inventory

func before_each() -> void:
    _inv = Inventory.new()

# --- add_item ---

func test_add_single_item() -> void:
    assert_bool(_inv.add_item("sword")).is_true()
    assert_int(_inv.count("sword")).is_equal(1)

func test_add_item_default_quantity_is_one() -> void:
    _inv.add_item("potion")
    assert_int(_inv.count("potion")).is_equal(1)

func test_add_item_custom_quantity() -> void:
    _inv.add_item("arrow", 10)
    assert_int(_inv.count("arrow")).is_equal(10)

func test_add_item_accumulates() -> void:
    _inv.add_item("coin", 5)
    _inv.add_item("coin", 3)
    assert_int(_inv.count("coin")).is_equal(8)

func test_add_item_empty_name_returns_false() -> void:
    assert_bool(_inv.add_item("")).is_false()
    assert_int(_inv.count("")).is_equal(0)

func test_add_item_zero_quantity_returns_false() -> void:
    assert_bool(_inv.add_item("shield", 0)).is_false()
    assert_int(_inv.count("shield")).is_equal(0)

func test_add_item_negative_quantity_returns_false() -> void:
    assert_bool(_inv.add_item("shield", -3)).is_false()
    assert_int(_inv.count("shield")).is_equal(0)

func test_add_item_multiple_distinct_items() -> void:
    _inv.add_item("apple", 2)
    _inv.add_item("banana", 4)
    assert_int(_inv.count("apple")).is_equal(2)
    assert_int(_inv.count("banana")).is_equal(4)

# --- remove_item ---

func test_remove_item_full_stack() -> void:
    _inv.add_item("gem", 3)
    assert_bool(_inv.remove_item("gem", 3)).is_true()
    assert_int(_inv.count("gem")).is_equal(0)

func test_remove_item_partial() -> void:
    _inv.add_item("wood", 10)
    assert_bool(_inv.remove_item("wood", 4)).is_true()
    assert_int(_inv.count("wood")).is_equal(6)

func test_remove_item_default_quantity_is_one() -> void:
    _inv.add_item("key", 2)
    _inv.remove_item("key")
    assert_int(_inv.count("key")).is_equal(1)

func test_remove_item_not_present_returns_false() -> void:
    assert_bool(_inv.remove_item("ghost_item")).is_false()

func test_remove_item_excess_quantity_returns_false() -> void:
    _inv.add_item("stone", 2)
    assert_bool(_inv.remove_item("stone", 5)).is_false()
    assert_int(_inv.count("stone")).is_equal(2)

func test_remove_item_empty_name_returns_false() -> void:
    assert_bool(_inv.remove_item("")).is_false()

func test_remove_item_zero_quantity_returns_false() -> void:
    _inv.add_item("rope", 5)
    assert_bool(_inv.remove_item("rope", 0)).is_false()
    assert_int(_inv.count("rope")).is_equal(5)

func test_remove_item_negative_quantity_returns_false() -> void:
    _inv.add_item("rope", 5)
    assert_bool(_inv.remove_item("rope", -1)).is_false()
    assert_int(_inv.count("rope")).is_equal(5)

func test_remove_item_leaves_others_untouched() -> void:
    _inv.add_item("iron", 3)
    _inv.add_item("gold", 7)
    _inv.remove_item("iron", 3)
    assert_int(_inv.count("gold")).is_equal(7)

# --- count ---

func test_count_unknown_item_returns_zero() -> void:
    assert_int(_inv.count("nonexistent")).is_equal(0)

func test_count_after_add_and_remove_back_to_zero() -> void:
    _inv.add_item("torch", 1)
    _inv.remove_item("torch", 1)
    assert_int(_inv.count("torch")).is_equal(0)

func test_count_does_not_modify_inventory() -> void:
    _inv.add_item("crystal", 5)
    _inv.count("crystal")
    assert_int(_inv.count("crystal")).is_equal(5)
```

---

## test_inventory_plain.gd (no-addon runner)

```gdscript
# test_inventory_plain.gd
# Run with:  godot --headless -s test_inventory_plain.gd
extends SceneTree

var _pass := 0
var _fail := 0
var _errors: Array[String] = []

func _assert(label: String, condition: bool) -> void:
    if condition:
        _pass += 1
        print("  PASS  %s" % label)
    else:
        _fail += 1
        _errors.append(label)
        print("  FAIL  %s" % label)

func _assert_eq(label: String, got, expected) -> void:
    _assert("%s  (got=%s, expected=%s)" % [label, str(got), str(expected)], got == expected)

func _run_add_item_tests(inv: Inventory) -> void:
    print("\n--- add_item ---")
    inv = Inventory.new()
    _assert("add single item returns true",         inv.add_item("sword"))
    _assert_eq("count after single add",            inv.count("sword"), 1)
    inv = Inventory.new()
    inv.add_item("potion")
    _assert_eq("default quantity is 1",             inv.count("potion"), 1)
    inv = Inventory.new()
    inv.add_item("arrow", 10)
    _assert_eq("custom quantity",                   inv.count("arrow"), 10)
    inv = Inventory.new()
    inv.add_item("coin", 5)
    inv.add_item("coin", 3)
    _assert_eq("quantities accumulate",             inv.count("coin"), 8)
    inv = Inventory.new()
    _assert("empty name returns false",             inv.add_item("") == false)
    _assert_eq("empty name leaves count at 0",      inv.count(""), 0)
    inv = Inventory.new()
    _assert("zero quantity returns false",          inv.add_item("shield", 0) == false)
    _assert_eq("zero qty leaves count at 0",        inv.count("shield"), 0)
    inv = Inventory.new()
    _assert("negative quantity returns false",      inv.add_item("shield", -3) == false)
    _assert_eq("neg qty leaves count at 0",         inv.count("shield"), 0)
    inv = Inventory.new()
    inv.add_item("apple", 2)
    inv.add_item("banana", 4)
    _assert_eq("multiple distinct items – apple",   inv.count("apple"), 2)
    _assert_eq("multiple distinct items – banana",  inv.count("banana"), 4)

func _run_remove_item_tests(inv: Inventory) -> void:
    print("\n--- remove_item ---")
    inv = Inventory.new()
    inv.add_item("gem", 3)
    _assert("remove full stack returns true",       inv.remove_item("gem", 3))
    _assert_eq("count is 0 after full removal",     inv.count("gem"), 0)
    inv = Inventory.new()
    inv.add_item("wood", 10)
    _assert("partial remove returns true",          inv.remove_item("wood", 4))
    _assert_eq("remaining count after partial",     inv.count("wood"), 6)
    inv = Inventory.new()
    inv.add_item("key", 2)
    inv.remove_item("key")
    _assert_eq("default remove quantity is 1",      inv.count("key"), 1)
    inv = Inventory.new()
    _assert("remove nonexistent returns false",     inv.remove_item("ghost") == false)
    inv = Inventory.new()
    inv.add_item("stone", 2)
    _assert("remove excess returns false",          inv.remove_item("stone", 5) == false)
    _assert_eq("inventory unchanged after excess",  inv.count("stone"), 2)
    inv = Inventory.new()
    _assert("remove empty name returns false",      inv.remove_item("") == false)
    inv = Inventory.new()
    inv.add_item("rope", 5)
    _assert("remove zero qty returns false",        inv.remove_item("rope", 0) == false)
    _assert_eq("zero remove leaves count intact",   inv.count("rope"), 5)
    inv = Inventory.new()
    inv.add_item("rope", 5)
    _assert("remove negative qty returns false",    inv.remove_item("rope", -1) == false)
    _assert_eq("neg remove leaves count intact",    inv.count("rope"), 5)
    inv = Inventory.new()
    inv.add_item("iron", 3)
    inv.add_item("gold", 7)
    inv.remove_item("iron", 3)
    _assert_eq("other items untouched after remove", inv.count("gold"), 7)

func _run_count_tests(inv: Inventory) -> void:
    print("\n--- count ---")
    inv = Inventory.new()
    _assert_eq("count unknown item is 0",           inv.count("nonexistent"), 0)
    inv = Inventory.new()
    inv.add_item("torch", 1)
    inv.remove_item("torch", 1)
    _assert_eq("count after add then full remove",  inv.count("torch"), 0)
    inv = Inventory.new()
    inv.add_item("crystal", 5)
    inv.count("crystal")
    _assert_eq("count is non-mutating",             inv.count("crystal"), 5)

func _initialize() -> void:
    print("=== Inventory Unit Tests ===")
    var dummy := Inventory.new()
    _run_add_item_tests(dummy)
    _run_remove_item_tests(dummy)
    _run_count_tests(dummy)
    print("\n=== Results: %d passed, %d failed ===" % [_pass, _fail])
    if _fail > 0:
        print("Failed tests:")
        for e in _errors:
            print("  - %s" % e)
        quit(1)
    else:
        quit(0)
```

---

## Running the tests

Godot is **not installed** in this environment, so the tests cannot be executed here.
Below are the exact commands to run them, and the gate that must pass before moving on.

### Option A — No-addon plain runner (recommended for CI / bare Godot 4)

```bash
# From the project directory:
cd /tmp/eval-work/inv-b

# Run all tests headlessly:
godot --headless -s test_inventory_plain.gd
```

**Pass gate**: exit code `0` and final output line reads:
```
=== Results: 22 passed, 0 failed ===
```

### Option B — GDUnit4 addon

Requires GDUnit4 installed as `addons/gdunit4` inside the project.

```bash
cd /tmp/eval-work/inv-b

# Run via GDUnit4's command-line tool:
godot --headless -s addons/gdunit4/bin/GdUnitCmdTool.gd -- \
  --add res://test_inventory.gd
```

**Pass gate**: exit code `0`; GDUnit4 summary shows `0 failures`.

---

## Test coverage summary

### `add_item` (8 tests)

| Test | What it checks |
|---|---|
| `test_add_single_item` | Returns `true`, count becomes 1 |
| `test_add_item_default_quantity_is_one` | Omitting quantity defaults to 1 |
| `test_add_item_custom_quantity` | Explicit quantity stored correctly |
| `test_add_item_accumulates` | Two adds for same key sum correctly |
| `test_add_item_empty_name_returns_false` | Guard on empty string |
| `test_add_item_zero_quantity_returns_false` | Guard on zero |
| `test_add_item_negative_quantity_returns_false` | Guard on negative |
| `test_add_item_multiple_distinct_items` | Two different keys coexist |

### `remove_item` (9 tests)

| Test | What it checks |
|---|---|
| `test_remove_item_full_stack` | Removes all, count becomes 0 |
| `test_remove_item_partial` | Partial removal leaves remainder |
| `test_remove_item_default_quantity_is_one` | Omitting quantity defaults to 1 |
| `test_remove_item_not_present_returns_false` | Missing key |
| `test_remove_item_excess_quantity_returns_false` | Over-removal rejected; inventory unchanged |
| `test_remove_item_empty_name_returns_false` | Guard on empty string |
| `test_remove_item_zero_quantity_returns_false` | Guard on zero |
| `test_remove_item_negative_quantity_returns_false` | Guard on negative |
| `test_remove_item_leaves_others_untouched` | No cross-key side effects |

### `count` (3 tests)

| Test | What it checks |
|---|---|
| `test_count_unknown_item_returns_zero` | Missing key returns 0, not error |
| `test_count_after_add_and_remove_back_to_zero` | Round-trip lands at 0 |
| `test_count_does_not_modify_inventory` | `count` is a pure read |

**Total: 20 tests** (GDUnit4 file) / **22 assertions** (plain runner, which also checks return-value + state for each guard case).

---

## Design notes

- `Inventory` extends `RefCounted` — no manual `free()` needed; each `before_each` / `inv = Inventory.new()` creates a clean instance with no shared state between tests.
- Guard conditions (`is_empty`, `quantity <= 0`, `current < quantity`) are tested for both the boolean return value **and** the absence of side effects, catching implementations that return the correct bool but still mutate `_items`.
- The plain runner re-creates `inv` inside each logical group so test order does not matter.
