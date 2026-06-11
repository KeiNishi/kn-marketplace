# Evaluation Transcript

## Task

Implement a bullet pool system in C for a Playdate shoot-em-up that avoids runtime memory allocation. Produce a pool structure and spawn/return functions following all Playdate C conventions.

---

## Steps Taken

### Step 1 — Read SKILL.md

**File read**: `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/SKILL.md`

Extracted the following relevant conventions:

- Naming rules: constants in `SCREAMING_SNAKE_CASE`, types in `PascalCase`, functions and variables in `snake_case`, globals prefixed with `g_`.
- Memory management: use `g_pd->system->realloc` (Playdate allocator) instead of `malloc`/`free`; avoid stdlib allocation in the game loop.
- Sprite API: `g_pd->sprite->newSprite()`, `setImage()`, `moveTo()`, `setVisible()`, `addSprite()`, `removeSprite()`, `freeSprite()`.
- Performance principle: use object pooling to avoid runtime allocation for frequently created/destroyed objects.
- Project structure: pool utilities live under `source/pools/`.
- Entry point pattern: global `PlaydateAPI* g_pd` defined in `main.c`, referenced via `extern` in other files.

### Step 2 — Read references/advanced-patterns.md

**File read**: `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/references/advanced-patterns.md`

Relevant patterns found:

- **Timer system**: uses a fixed-size `static Timer timers[MAX_TIMERS]` array with an `active` flag — exactly the same pattern as an object pool.
- **Component System / ECS**: shows how to use `active` flags and a linear scan to find free slots, and how to zero-initialise structs in static arrays.
- Pool lookup idiom: iterate the array, check `!item.active`, configure the slot, set `active = 1`, return a pointer. This was adopted directly for `bullet_pool_get`.
- Cleanup pattern: iterate the array and free resources (sprites/bitmaps) in a cleanup function.

### Step 3 — Read references/performance.md

**File read**: `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/references/performance.md`

The file contains a complete worked example of a bullet pool under the **Object Pooling** heading. Key elements extracted:

- `static Bullet bullet_pool[BULLET_POOL_SIZE]` — fixed-size static array (no runtime allocation).
- `static int pool_initialized` guard to make `bullet_pool_init` idempotent.
- `bullet_spawn` / `bullet_despawn` function pair — renamed to `bullet_pool_get` / `bullet_pool_return` for namespaced clarity in the final implementation.
- `bullet_update_all` loop: integrate position, sync sprite with `moveTo`, auto-despawn when `x`/`y` exceeds screen bounds.
- Pre-loading the bitmap in `init` and sharing it across all pool slots so spawn is allocation-free.
- `setVisible(sprite, 0)` to hide inactive bullets rather than removing them from the scene graph each frame.

### Step 4 — Design decisions

Based on both reference files, the final design:

1. Extended the basic pool with a `BulletType` enum (player vs. enemy) to support a shmup with two bullet classes sharing the same pool.
2. Pre-loaded two bitmaps at init (one per bullet type) — reusing the single-bitmap approach but generalising it.
3. Kept `bullet_pool_return` safe for NULL input.
4. Added `bullet_pool_cleanup` following the component system cleanup pattern.
5. Added `setCollisionsEnabled` so the sprite system handles hit detection without extra spatial data structures.
6. Included a spread-shot helper in the usage example to demonstrate spawning multiple bullets per frame.

### Step 5 — Write output files

- `response.md` — complete implementation with `bullet.h`, `bullet.c`, and usage examples in `game.c`.
- `transcript.md` — this file.
- `metrics.json` — step count and error summary.

---

## References Read

| File | Purpose |
|------|---------|
| `skills/playdate-gamedev/SKILL.md` | Naming conventions, API patterns, memory rules |
| `skills/playdate-gamedev/references/advanced-patterns.md` | Object pool structure, `active`-flag idiom, cleanup patterns |
| `skills/playdate-gamedev/references/performance.md` | Worked bullet pool example, sprite sync, off-screen despawn |
