# Bullet Pool System in C for Playdate Shoot-em-up

A bullet pool pre-allocates all bullets at startup and reuses them, eliminating runtime `malloc`/`free` calls which are slow and can cause fragmentation on constrained hardware like the Playdate.

---

## Pool Structure

```c
#include <stdint.h>
#include <stdbool.h>
#include <string.h>

#define MAX_BULLETS 64

typedef struct {
    float x;
    float y;
    float vx;       // velocity x
    float vy;       // velocity y
    float speed;
    bool  active;
    uint8_t damage;
    uint8_t owner;  // 0 = player, 1 = enemy
} Bullet;

typedef struct {
    Bullet  bullets[MAX_BULLETS];
    int     count;      // total pool size (always MAX_BULLETS)
    int     active_count;
} BulletPool;

// Global pool instance (or embed in your game state struct)
static BulletPool g_bullet_pool;
```

---

## Initialization

```c
void BulletPool_Init(BulletPool *pool) {
    memset(pool, 0, sizeof(BulletPool));
    pool->count = MAX_BULLETS;
    pool->active_count = 0;
}
```

---

## Spawn a Bullet (Get from Pool)

Scans for the first inactive slot and initializes it. Returns `NULL` if the pool is exhausted.

```c
Bullet *BulletPool_Spawn(BulletPool *pool,
                         float x, float y,
                         float vx, float vy,
                         uint8_t damage, uint8_t owner) {
    for (int i = 0; i < pool->count; i++) {
        if (!pool->bullets[i].active) {
            Bullet *b = &pool->bullets[i];
            b->x      = x;
            b->y      = y;
            b->vx     = vx;
            b->vy     = vy;
            b->speed  = 0.0f; // unused if vx/vy encode speed already
            b->damage = damage;
            b->owner  = owner;
            b->active = true;
            pool->active_count++;
            return b;
        }
    }
    // Pool exhausted — caller can silently drop the bullet
    return NULL;
}
```

---

## Return a Bullet (Deactivate)

```c
void BulletPool_Return(BulletPool *pool, Bullet *b) {
    if (b == NULL) return;
    // Verify pointer is actually inside this pool (safety check)
    if (b < &pool->bullets[0] || b >= &pool->bullets[MAX_BULLETS]) return;

    b->active = false;
    pool->active_count--;
    if (pool->active_count < 0) pool->active_count = 0; // guard against underflow
}
```

---

## Update Loop

Called once per frame. Moves all active bullets and culls those that have left the screen.

```c
#define SCREEN_W 400
#define SCREEN_H 240

void BulletPool_Update(BulletPool *pool) {
    for (int i = 0; i < pool->count; i++) {
        Bullet *b = &pool->bullets[i];
        if (!b->active) continue;

        b->x += b->vx;
        b->y += b->vy;

        // Return bullet if it leaves the screen bounds
        if (b->x < 0 || b->x > SCREEN_W ||
            b->y < 0 || b->y > SCREEN_H) {
            BulletPool_Return(pool, b);
        }
    }
}
```

---

## Draw Loop

```c
// Assumes you have access to pd->graphics (Playdate SDK)
void BulletPool_Draw(BulletPool *pool, PlaydateAPI *pd) {
    for (int i = 0; i < pool->count; i++) {
        Bullet *b = &pool->bullets[i];
        if (!b->active) continue;

        // Draw a 4x4 filled rectangle for each bullet
        pd->graphics->fillRect((int)b->x - 2, (int)b->y - 2, 4, 4, kColorBlack);
    }
}
```

---

## Collision Check Example

```c
// Returns the first active bullet that overlaps rect (x,y,w,h), or NULL
Bullet *BulletPool_CheckCollision(BulletPool *pool,
                                  float rx, float ry,
                                  float rw, float rh,
                                  uint8_t target_owner) {
    for (int i = 0; i < pool->count; i++) {
        Bullet *b = &pool->bullets[i];
        if (!b->active) continue;
        if (b->owner == target_owner) continue; // friendly fire guard

        if (b->x >= rx && b->x <= rx + rw &&
            b->y >= ry && b->y <= ry + rh) {
            return b;
        }
    }
    return NULL;
}
```

---

## Wiring into Your Game Loop

```c
// game.c

static BulletPool g_bullets;

void game_init(PlaydateAPI *pd) {
    BulletPool_Init(&g_bullets);
}

int game_update(PlaydateAPI *pd) {
    // --- Player fires ---
    if (player_pressed_fire()) {
        BulletPool_Spawn(&g_bullets,
                         player.x, player.y - 8,
                         0.0f, -8.0f,   // straight up
                         10, 0);         // damage=10, owner=player
    }

    // --- Move all bullets ---
    BulletPool_Update(&g_bullets);

    // --- Check enemy collisions ---
    for (int e = 0; e < enemy_count; e++) {
        Bullet *hit = BulletPool_CheckCollision(
            &g_bullets,
            enemies[e].x, enemies[e].y, 16, 16,
            1  // target_owner=enemy (so player bullets hit)
        );
        if (hit) {
            enemies[e].hp -= hit->damage;
            BulletPool_Return(&g_bullets, hit);
        }
    }

    // --- Draw ---
    BulletPool_Draw(&g_bullets, pd);

    return 1; // request another update
}
```

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Fixed-size array of structs | No heap allocation; cache-friendly linear scan |
| `bool active` flag | O(1) return; no linked-list pointer chasing |
| `active_count` bookkeeping | Lets you bail out of the scan early when `active_count == 0` |
| Pointer bounds check in `Return` | Prevents stale/dangling pointer bugs in release builds |
| `MAX_BULLETS 64` | Fits comfortably within Playdate's 16 MB RAM; tune as needed |

---

## Tips for Playdate Specifically

- The Playdate CPU (Cortex-M7 @ 180 MHz) has no hardware FPU in the base configuration — consider using fixed-point integers (`int16_t` in units of 1/256 pixel) for `x`, `y`, `vx`, `vy` if you need maximum throughput.
- Keep `MAX_BULLETS` a power of 2 so the compiler can optimize modulo operations if you later switch to a ring-buffer variant.
- Profile with the Playdate Simulator's performance overlay before optimizing — 64 bullets with a linear scan is almost certainly fast enough at 30 fps.
