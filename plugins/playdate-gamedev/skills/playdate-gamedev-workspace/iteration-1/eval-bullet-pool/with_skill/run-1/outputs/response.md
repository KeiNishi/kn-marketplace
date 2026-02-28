# Bullet Pool System for Playdate Shoot-em-up

This implementation provides a complete bullet pool system in C for Playdate, using a fixed-size static array to avoid any runtime memory allocation.

---

## bullet.h — Public API

```c
#pragma once

#include "pd_api.h"

// Maximum number of simultaneous bullets in the pool.
// Increase if bullets are exhausted during heavy fire.
#define MAX_BULLETS 128

// Bullet type flags — distinguish player and enemy bullets.
typedef enum {
    BULLET_TYPE_PLAYER = 0,
    BULLET_TYPE_ENEMY  = 1
} BulletType;

// A single bullet entry inside the pool.
// Keep fields compact; the whole array lives in BSS (zero cost at startup).
typedef struct {
    float      x;
    float      y;
    float      vel_x;
    float      vel_y;
    BulletType type;
    int        active;      // 0 = free slot, 1 = in use
    LCDSprite* sprite;
} Bullet;

// Pool lifecycle
void   bullet_pool_init(void);
void   bullet_pool_cleanup(void);

// Spawn a bullet from the pool. Returns NULL when the pool is exhausted.
Bullet* bullet_pool_get(float x, float y, float vel_x, float vel_y, BulletType type);

// Return a bullet to the pool (deactivate and hide its sprite).
void   bullet_pool_return(Bullet* bullet);

// Per-frame update: move all active bullets and auto-return off-screen ones.
void   bullet_pool_update(float dt);
```

---

## bullet.c — Implementation

```c
#include "bullet.h"

// Playdate screen bounds with a margin so bullets fully exit before despawning.
#define SCREEN_W        400
#define SCREEN_H        240
#define OFFSCREEN_MARGIN 12

// Bitmap paths — place 1-bit PNG files under source/resources/images/.
#define BITMAP_PLAYER_BULLET "images/bullet_player"
#define BITMAP_ENEMY_BULLET  "images/bullet_enemy"

// -------------------------------------------------------------------------
// Global API pointer — defined once in main.c, referenced via extern here.
// -------------------------------------------------------------------------
extern PlaydateAPI* g_pd;

// -------------------------------------------------------------------------
// The pool itself: a fixed-size static array, zero-initialised at program
// start. No malloc, no realloc — all memory is committed at compile time.
// -------------------------------------------------------------------------
static Bullet g_bullet_pool[MAX_BULLETS];
static int    g_pool_initialized = 0;

// Pre-loaded bitmaps shared across all bullets of the same type.
static LCDBitmap* g_bmp_player = NULL;
static LCDBitmap* g_bmp_enemy  = NULL;

// -------------------------------------------------------------------------
// bullet_pool_init
// Call once during game_init(). Creates sprites for every slot and loads
// shared bitmaps so no allocation ever happens at spawn time.
// -------------------------------------------------------------------------
void bullet_pool_init(void) {
    if (g_pool_initialized) return;

    // Load shared bitmaps once.
    const char* err = NULL;
    g_bmp_player = g_pd->graphics->loadBitmap(BITMAP_PLAYER_BULLET, &err);
    if (!g_bmp_player) {
        g_pd->system->error("bullet_pool_init: failed to load %s (%s)",
                            BITMAP_PLAYER_BULLET, err ? err : "unknown");
    }

    g_bmp_enemy = g_pd->graphics->loadBitmap(BITMAP_ENEMY_BULLET, &err);
    if (!g_bmp_enemy) {
        g_pd->system->error("bullet_pool_init: failed to load %s (%s)",
                            BITMAP_ENEMY_BULLET, err ? err : "unknown");
    }

    // Pre-create one sprite per pool slot. Sprites are hidden until spawned.
    for (int i = 0; i < MAX_BULLETS; i++) {
        g_bullet_pool[i].active = 0;
        g_bullet_pool[i].x      = 0.0f;
        g_bullet_pool[i].y      = 0.0f;
        g_bullet_pool[i].vel_x  = 0.0f;
        g_bullet_pool[i].vel_y  = 0.0f;
        g_bullet_pool[i].type   = BULLET_TYPE_PLAYER;

        g_bullet_pool[i].sprite = g_pd->sprite->newSprite();
        if (!g_bullet_pool[i].sprite) {
            g_pd->system->error("bullet_pool_init: failed to create sprite at index %d", i);
            continue;
        }

        // Default image; updated to the correct type in bullet_pool_get().
        if (g_bmp_player) {
            g_pd->sprite->setImage(g_bullet_pool[i].sprite, g_bmp_player, kBitmapUnflipped);
        }

        // Hide and add to scene graph — the sprite system culls invisible sprites.
        g_pd->sprite->setVisible(g_bullet_pool[i].sprite, 0);
        g_pd->sprite->addSprite(g_bullet_pool[i].sprite);

        // Enable collision on the sprite so bullet hit detection works via
        // the sprite system without additional spatial queries.
        g_pd->sprite->setCollisionsEnabled(g_bullet_pool[i].sprite, 1);
    }

    g_pool_initialized = 1;
    g_pd->system->logToConsole("bullet_pool_init: %d slots ready", MAX_BULLETS);
}

// -------------------------------------------------------------------------
// bullet_pool_cleanup
// Call when leaving the game scene. Frees sprites and bitmaps.
// -------------------------------------------------------------------------
void bullet_pool_cleanup(void) {
    if (!g_pool_initialized) return;

    for (int i = 0; i < MAX_BULLETS; i++) {
        if (g_bullet_pool[i].sprite) {
            g_pd->sprite->removeSprite(g_bullet_pool[i].sprite);
            g_pd->sprite->freeSprite(g_bullet_pool[i].sprite);
            g_bullet_pool[i].sprite = NULL;
        }
        g_bullet_pool[i].active = 0;
    }

    if (g_bmp_player) {
        g_pd->graphics->freeBitmap(g_bmp_player);
        g_bmp_player = NULL;
    }
    if (g_bmp_enemy) {
        g_pd->graphics->freeBitmap(g_bmp_enemy);
        g_bmp_enemy = NULL;
    }

    g_pool_initialized = 0;
}

// -------------------------------------------------------------------------
// bullet_pool_get
// Finds the first inactive slot, configures it, and returns a pointer.
// Returns NULL if the pool is exhausted — caller should handle gracefully.
// -------------------------------------------------------------------------
Bullet* bullet_pool_get(float x, float y, float vel_x, float vel_y, BulletType type) {
    for (int i = 0; i < MAX_BULLETS; i++) {
        if (g_bullet_pool[i].active) continue;  // Slot is in use, skip.

        Bullet* b = &g_bullet_pool[i];

        // Assign bullet state.
        b->x     = x;
        b->y     = y;
        b->vel_x = vel_x;
        b->vel_y = vel_y;
        b->type  = type;
        b->active = 1;

        // Point sprite to the correct pre-loaded bitmap.
        LCDBitmap* bmp = (type == BULLET_TYPE_PLAYER) ? g_bmp_player : g_bmp_enemy;
        if (bmp) {
            g_pd->sprite->setImage(b->sprite, bmp, kBitmapUnflipped);
        }

        // Position and reveal.
        g_pd->sprite->moveTo(b->sprite, x, y);
        g_pd->sprite->setVisible(b->sprite, 1);

        return b;
    }

    // Pool exhausted — log once so it is visible in the console.
    g_pd->system->logToConsole("bullet_pool_get: pool exhausted (MAX_BULLETS=%d)", MAX_BULLETS);
    return NULL;
}

// -------------------------------------------------------------------------
// bullet_pool_return
// Deactivates a bullet and hides its sprite, returning the slot to the pool.
// Safe to call with NULL.
// -------------------------------------------------------------------------
void bullet_pool_return(Bullet* bullet) {
    if (!bullet) return;

    bullet->active = 0;
    bullet->x      = 0.0f;
    bullet->y      = 0.0f;
    bullet->vel_x  = 0.0f;
    bullet->vel_y  = 0.0f;

    if (bullet->sprite) {
        g_pd->sprite->setVisible(bullet->sprite, 0);
        // Move off-screen so any stale collision bounds don't trigger.
        g_pd->sprite->moveTo(bullet->sprite, -100.0f, -100.0f);
    }
}

// -------------------------------------------------------------------------
// bullet_pool_update
// Called every frame from game_update(). Moves active bullets and despawns
// any that travel off-screen. No allocation occurs here.
// -------------------------------------------------------------------------
void bullet_pool_update(float dt) {
    for (int i = 0; i < MAX_BULLETS; i++) {
        if (!g_bullet_pool[i].active) continue;

        Bullet* b = &g_bullet_pool[i];

        // Integrate position.
        b->x += b->vel_x * dt;
        b->y += b->vel_y * dt;

        // Sync sprite position.
        g_pd->sprite->moveTo(b->sprite, b->x, b->y);

        // Auto-return if off-screen.
        if (b->x < -OFFSCREEN_MARGIN || b->x > SCREEN_W + OFFSCREEN_MARGIN ||
            b->y < -OFFSCREEN_MARGIN || b->y > SCREEN_H + OFFSCREEN_MARGIN) {
            bullet_pool_return(b);
        }
    }
}
```

---

## Usage Example in game.c

```c
#include "bullet.h"

// ---- Initialization ----
void game_init(void) {
    bullet_pool_init();
    // ... other init
}

// ---- Spawn (called when player fires) ----
void player_shoot(float player_x, float player_y) {
    // Fire straight up at 300 px/s.
    Bullet* b = bullet_pool_get(player_x, player_y - 16.0f,
                                0.0f, -300.0f,
                                BULLET_TYPE_PLAYER);
    if (!b) {
        // Pool exhausted — ignore or apply back-pressure logic.
        return;
    }
    // b is now live; bullet_pool_update() drives it each frame.
}

// ---- Spread shot example (three-way) ----
void player_shoot_spread(float player_x, float player_y) {
    bullet_pool_get(player_x,        player_y - 16.0f,  -80.0f, -280.0f, BULLET_TYPE_PLAYER);
    bullet_pool_get(player_x,        player_y - 16.0f,    0.0f, -300.0f, BULLET_TYPE_PLAYER);
    bullet_pool_get(player_x,        player_y - 16.0f,   80.0f, -280.0f, BULLET_TYPE_PLAYER);
}

// ---- Per-frame update ----
int game_update(void* userdata) {
    (void)userdata;
    float dt = 1.0f / 30.0f;

    // Update all active bullets (move + auto-despawn off-screen).
    bullet_pool_update(dt);

    // Sprite system draws and collision-checks bullets automatically.
    g_pd->sprite->updateAndDrawSprites();

    g_pd->system->drawFPS(0, 0);
    return 1;
}

// ---- Hit detection (collision callback or manual query) ----
void on_bullet_hit_enemy(Bullet* b, Enemy* e) {
    enemy_take_damage(e, 1);
    bullet_pool_return(b);  // Return bullet to pool immediately.
}

// ---- Cleanup ----
void game_cleanup(void) {
    bullet_pool_cleanup();
    // ... other cleanup
}
```

---

## Key Design Decisions

### Why a fixed-size static array?

`static Bullet g_bullet_pool[MAX_BULLETS]` is allocated in BSS at link time. There is no `malloc`, no `realloc`, and no fragmentation. Every frame is allocation-free inside the pool update loop, which is the most critical constraint on Playdate hardware.

### Why pre-create sprites at init?

`g_pd->sprite->newSprite()` involves an internal allocation. Doing it once during `bullet_pool_init()` means `bullet_pool_get()` never allocates — it only flips `active = 1`, sets the bitmap reference, and calls `moveTo` + `setVisible`, all O(1) operations.

### Why share bitmaps across all pool slots?

A single `LCDBitmap*` per bullet type is loaded once. Each sprite's `setImage` call simply stores a pointer; no pixel data is duplicated. This keeps peak memory proportional to the number of bitmap *types*, not the pool size.

### Linear scan for a free slot

With `MAX_BULLETS = 128` the worst-case scan is 128 iterations — negligible at 30 fps. If profiling shows this is a bottleneck, maintain a free-list index array alongside the pool. For most shmup designs the simple scan is sufficient.

### Naming conventions

All symbols follow Playdate project conventions established in the skill guide:
- Constants: `SCREAMING_SNAKE_CASE` (`MAX_BULLETS`, `BULLET_TYPE_PLAYER`)
- Types: `PascalCase` (`Bullet`, `BulletType`)
- Functions: `snake_case` (`bullet_pool_get`, `bullet_pool_return`)
- Global state: `g_` prefix (`g_bullet_pool`, `g_bmp_player`)
