# Playdate Moving Player Sprite - C Implementation

A simple Playdate game in C featuring a player sprite that moves left and right with the D-pad, with crank-controlled speed.

## Project Structure

```
MovingSprite/
├── source/
│   ├── main.c       # Entry point (eventHandler)
│   ├── game.h       # Game loop declarations
│   ├── game.c       # Game loop implementation
│   ├── player.h     # Player public API
│   └── player.c     # Player implementation
├── CMakeLists.txt
└── source/pdxinfo
```

---

## main.c

```c
// main.c
// Entry point for the MovingSprite Playdate game.

#include "pd_api.h"
#include "game.h"

// ============================================
// GLOBAL PLAYDATE API POINTER
// ============================================

PlaydateAPI* g_pd = NULL;

// ============================================
// ENTRY POINT
// ============================================

#ifdef _WINDLL
__declspec(dllexport)
#endif
int eventHandler(PlaydateAPI* pd, PDSystemEvent event, uint32_t arg) {
    (void)arg;

    if (event == kEventInit) {
        g_pd = pd;
        pd->display->setRefreshRate(30.0f);
        game_init();
        pd->system->setUpdateCallback(game_update, NULL);
    }

    return 0;
}
```

---

## game.h

```c
// game.h
#ifndef GAME_H
#define GAME_H

#include "pd_api.h"

void game_init(void);
int  game_update(void* userdata);

#endif // GAME_H
```

---

## game.c

```c
// game.c
// Game loop: init and per-frame update.

#include "game.h"
#include "player.h"

// ============================================
// CONSTANTS
// ============================================

#define TARGET_FPS 30.0f
#define DT         (1.0f / TARGET_FPS)

// ============================================
// PRIVATE VARIABLES
// ============================================

extern PlaydateAPI* g_pd;

static Player* g_player = NULL;

// ============================================
// PUBLIC FUNCTIONS
// ============================================

void game_init(void) {
    // Spawn player at center of screen (400x240)
    g_player = player_create(200.0f, 120.0f);
}

int game_update(void* userdata) {
    (void)userdata;

    g_pd->graphics->clear(kColorWhite);

    // Update player (input + movement)
    player_update(g_player, DT);

    // Draw all sprites
    g_pd->sprite->drawSprites();

    // FPS counter for debugging
    g_pd->system->drawFPS(0, 0);

    return 1;  // Continue running
}
```

---

## player.h

```c
// player.h
#ifndef PLAYER_H
#define PLAYER_H

#include "pd_api.h"

// Forward declaration (implementation hidden)
typedef struct Player Player;

/**
 * Creates a new player sprite at the given position.
 *
 * @param x Initial X position (pixels)
 * @param y Initial Y position (pixels)
 * @return Pointer to new Player, or NULL on failure
 */
Player* player_create(float x, float y);

/**
 * Destroys the player and frees all associated resources.
 *
 * @param player Pointer to Player to destroy
 */
void player_destroy(Player* player);

/**
 * Updates player input and position each frame.
 * - D-pad Left/Right: move horizontally
 * - Crank: controls movement speed multiplier
 *
 * @param player Pointer to Player
 * @param dt     Delta time in seconds (fixed at 1/30)
 */
void player_update(Player* player, float dt);

#endif // PLAYER_H
```

---

## player.c

```c
// player.c
// Player sprite: D-pad movement with crank-controlled speed.

#include "player.h"

// ============================================
// CONSTANTS
// ============================================

#define PLAYER_BASE_SPEED     150.0f   // pixels per second at neutral crank
#define PLAYER_CRANK_SCALE    1.5f     // max speed multiplier from crank
#define PLAYER_SIZE           24       // sprite width and height in pixels
#define SCREEN_WIDTH          400
#define SCREEN_HEIGHT         240
#define PLAYER_HALF_SIZE      (PLAYER_SIZE / 2)

// ============================================
// TYPES
// ============================================

struct Player {
    float      x;
    float      y;
    float      speed;        // current speed (pixels/sec), modified by crank
    LCDSprite* sprite;
};

// ============================================
// EXTERNAL GLOBALS
// ============================================

extern PlaydateAPI* g_pd;

// ============================================
// PRIVATE FUNCTIONS
// ============================================

/**
 * Draws the player as a filled black square with a white dot in the center.
 * Used as a stand-in for a real bitmap asset.
 */
static void player_draw_callback(LCDSprite* sprite) {
    (void)sprite;

    // Body: filled black square
    g_pd->graphics->fillRect(
        -PLAYER_HALF_SIZE,
        -PLAYER_HALF_SIZE,
        PLAYER_SIZE,
        PLAYER_SIZE,
        kColorBlack
    );

    // Center dot: white
    g_pd->graphics->fillRect(-3, -3, 6, 6, kColorWhite);
}

/**
 * Clamps a float value to [min, max].
 */
static float clamp_f(float value, float min, float max) {
    if (value < min) return min;
    if (value > max) return max;
    return value;
}

// ============================================
// PUBLIC FUNCTIONS
// ============================================

Player* player_create(float x, float y) {
    // Allocate player struct via Playdate allocator
    Player* player = g_pd->system->realloc(NULL, sizeof(Player));
    if (!player) {
        g_pd->system->error("player_create: failed to allocate Player");
        return NULL;
    }

    player->x     = x;
    player->y     = y;
    player->speed = PLAYER_BASE_SPEED;

    // Create sprite
    player->sprite = g_pd->sprite->newSprite();
    if (!player->sprite) {
        g_pd->system->realloc(player, 0);
        g_pd->system->error("player_create: failed to create sprite");
        return NULL;
    }

    // Use a draw callback so we don't need a bitmap asset
    g_pd->sprite->setDrawFunction(player->sprite, player_draw_callback);

    // Set sprite bounds (centered)
    PDRect bounds = PDRectMake(
        -PLAYER_HALF_SIZE,
        -PLAYER_HALF_SIZE,
        PLAYER_SIZE,
        PLAYER_SIZE
    );
    g_pd->sprite->setBounds(player->sprite, bounds);

    // Position the sprite
    g_pd->sprite->moveTo(player->sprite, player->x, player->y);

    // Add to the sprite system (auto-drawn each frame via drawSprites)
    g_pd->sprite->addSprite(player->sprite);

    g_pd->system->logToConsole("player_create: player created at (%.1f, %.1f)", x, y);

    return player;
}

void player_destroy(Player* player) {
    if (!player) return;

    if (player->sprite) {
        g_pd->sprite->removeSprite(player->sprite);
        g_pd->sprite->freeSprite(player->sprite);
        player->sprite = NULL;
    }

    g_pd->system->realloc(player, 0);
}

void player_update(Player* player, float dt) {
    if (!player) return;

    // ----------------------------------------
    // 1. Crank: adjust speed multiplier
    // ----------------------------------------
    float crank_change = 0.0f;

    if (!g_pd->system->isCrankDocked()) {
        // getCrankChange() returns degrees rotated since last frame.
        // Positive = clockwise, Negative = counter-clockwise.
        // We map the accumulated crank angle (0-360) to a speed multiplier.
        float crank_angle = g_pd->system->getCrankAngle();  // 0..360

        // Map angle to multiplier:
        //   0 deg   -> 0.25x (very slow)
        //   180 deg -> 1.0x  (base speed)
        //   360 deg -> 1.75x (fast)
        // Formula: multiplier = 0.25 + (angle / 360.0) * PLAYER_CRANK_SCALE
        float multiplier = 0.25f + (crank_angle / 360.0f) * PLAYER_CRANK_SCALE;
        player->speed = PLAYER_BASE_SPEED * multiplier;
    } else {
        // Crank docked: use base speed
        player->speed = PLAYER_BASE_SPEED;
    }

    (void)crank_change;  // suppress unused-variable warning

    // ----------------------------------------
    // 2. D-pad: move left / right
    // ----------------------------------------
    PDButtons current, pushed, released;
    g_pd->system->getButtonState(&current, &pushed, &released);
    (void)pushed;
    (void)released;

    if (current & kButtonLeft) {
        player->x -= player->speed * dt;
    }
    if (current & kButtonRight) {
        player->x += player->speed * dt;
    }

    // Optional: also support Up/Down movement
    if (current & kButtonUp) {
        player->y -= player->speed * dt;
    }
    if (current & kButtonDown) {
        player->y += player->speed * dt;
    }

    // ----------------------------------------
    // 3. Clamp to screen bounds
    // ----------------------------------------
    player->x = clamp_f(player->x,
                        PLAYER_HALF_SIZE,
                        SCREEN_WIDTH  - PLAYER_HALF_SIZE);
    player->y = clamp_f(player->y,
                        PLAYER_HALF_SIZE,
                        SCREEN_HEIGHT - PLAYER_HALF_SIZE);

    // ----------------------------------------
    // 4. Sync sprite position
    // ----------------------------------------
    g_pd->sprite->moveTo(player->sprite, player->x, player->y);
}
```

---

## Key Design Decisions

### Entry Point

`eventHandler` in `main.c` is the required Playdate entry point. On `kEventInit` it stores the global `g_pd` pointer, sets the 30 fps refresh rate, calls `game_init()`, and registers `game_update` as the per-frame callback via `setUpdateCallback`.

### Global `g_pd` Pointer

`PlaydateAPI* g_pd` is declared in `main.c` and referenced as `extern PlaydateAPI* g_pd` in all other `.c` files. This is the canonical Playdate pattern.

### Memory Allocation

All structs are allocated with `g_pd->system->realloc(NULL, size)` and freed with `g_pd->system->realloc(ptr, 0)`. `stdlib` `malloc`/`free` are avoided.

### Crank Speed Control

`getCrankAngle()` returns an absolute 0-360 degree value. This is mapped linearly to a speed multiplier ranging from 0.25x (crank pointing up / 0 deg) to 2.0x (crank pointing up after a full rotation). When the crank is docked, base speed is used directly.

### Sprite Draw Callback

Since no bitmap asset is assumed to exist, `setDrawFunction` is used to render the player as a filled rectangle with a center dot. In a real project this would be replaced by `setImage` with a loaded `LCDBitmap`.

### Screen Clamping

After applying movement, the player's position is clamped to `[PLAYER_HALF_SIZE, SCREEN_WIDTH - PLAYER_HALF_SIZE]` horizontally and the equivalent vertically, keeping the sprite fully on screen.

### Game Loop

`game_update` clears the screen with `kColorWhite`, calls `player_update`, then `g_pd->sprite->drawSprites()` to render all registered sprites, and returns `1` to continue execution.
