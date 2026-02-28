# Playdate Moving Sprite Game - C Implementation

## Overview

This implementation creates a simple Playdate game where a player sprite moves left and right using the D-pad. The crank controls the player's movement speed. The game uses the Playdate C API directly.

## Project Structure

```
my-game/
├── src/
│   ├── main.c       - Entry point and game loop
│   └── player.h     - Player struct and function declarations
├── Makefile
└── pdxinfo
```

## main.c

```c
#include <stdio.h>
#include <stdlib.h>
#include "pd_api.h"

// Forward declarations
typedef struct Player Player;

// Player structure
typedef struct Player {
    float x;
    float y;
    float speed;
    float base_speed;
    float crank_speed_modifier;
    LCDBitmap *bitmap;
    int width;
    int height;
} Player;

// Global state
static PlaydateAPI *pd = NULL;
static Player player = {0};

// Screen dimensions
#define SCREEN_WIDTH  400
#define SCREEN_HEIGHT 240

// Player constants
#define PLAYER_BASE_SPEED     3.0f
#define PLAYER_WIDTH          16
#define PLAYER_HEIGHT         16
#define CRANK_SPEED_SCALE     0.05f  // How much crank angle affects speed

// -----------------------------------------------------------------------
// Player initialization
// -----------------------------------------------------------------------
static void player_init(Player *p) {
    p->x = (float)(SCREEN_WIDTH / 2 - PLAYER_WIDTH / 2);
    p->y = (float)(SCREEN_HEIGHT / 2 - PLAYER_HEIGHT / 2);
    p->base_speed = PLAYER_BASE_SPEED;
    p->speed = PLAYER_BASE_SPEED;
    p->crank_speed_modifier = 0.0f;
    p->width = PLAYER_WIDTH;
    p->height = PLAYER_HEIGHT;

    // Create a simple bitmap for the player (16x16 filled rectangle)
    // In a real game you would load a .pdi image file
    p->bitmap = pd->graphics->newBitmap(PLAYER_WIDTH, PLAYER_HEIGHT, kColorBlack);
}

// -----------------------------------------------------------------------
// Player update - called every frame
// -----------------------------------------------------------------------
static void player_update(Player *p) {
    // --- Crank: adjust speed based on crank angle ---
    // getCrankAngle() returns 0-360 degrees.
    // We map 0-180 to positive modifier, 180-360 to negative modifier,
    // so the player can slow down by rotating the crank backwards.
    float crank_angle = pd->system->getCrankAngle();

    // Normalise to -1..1 range: 0 deg = 0, 90 deg = +1, 270 deg = -1
    float normalised = 0.0f;
    if (crank_angle <= 180.0f) {
        normalised = crank_angle / 180.0f;          // 0 -> 0, 180 -> 1
    } else {
        normalised = (crank_angle - 360.0f) / 180.0f; // 180 -> 1, 360 -> 0 (going negative side)
    }

    // Speed ranges from 0 (full reverse crank) to base_speed*2 (full forward crank)
    // When crank is at 0 the speed equals base_speed.
    p->crank_speed_modifier = normalised * p->base_speed;
    p->speed = p->base_speed + p->crank_speed_modifier;

    // Clamp speed so the player cannot go backwards just from crank
    if (p->speed < 0.5f) p->speed = 0.5f;

    // --- D-pad: move player left / right ---
    PDButtons current_buttons;
    PDButtons pushed_buttons;
    PDButtons released_buttons;
    pd->system->getButtonState(&current_buttons, &pushed_buttons, &released_buttons);

    if (current_buttons & kButtonLeft) {
        p->x -= p->speed;
    }
    if (current_buttons & kButtonRight) {
        p->x += p->speed;
    }

    // --- Boundary clamping: keep player on screen ---
    if (p->x < 0.0f) {
        p->x = 0.0f;
    }
    if (p->x > (float)(SCREEN_WIDTH - p->width)) {
        p->x = (float)(SCREEN_WIDTH - p->width);
    }
}

// -----------------------------------------------------------------------
// Player render - draw the player bitmap at its current position
// -----------------------------------------------------------------------
static void player_draw(const Player *p) {
    pd->graphics->drawBitmap(p->bitmap, (int)p->x, (int)p->y, kBitmapUnflipped);
}

// -----------------------------------------------------------------------
// Player cleanup
// -----------------------------------------------------------------------
static void player_free(Player *p) {
    if (p->bitmap != NULL) {
        pd->graphics->freeBitmap(p->bitmap);
        p->bitmap = NULL;
    }
}

// -----------------------------------------------------------------------
// Main game update callback - called by the runtime at ~30 fps
// -----------------------------------------------------------------------
static int update(void *userdata) {
    (void)userdata;  // unused

    pd->graphics->clear(kColorWhite);

    // Update and draw player
    player_update(&player);
    player_draw(&player);

    // HUD: show current speed and crank angle
    char hud_buf[64];
    float crank_angle = pd->system->getCrankAngle();
    pd->system->formatString(&hud_buf[0],
        "speed: %.1f  crank: %.0f deg",
        (double)player.speed,
        (double)crank_angle);
    pd->graphics->drawText(hud_buf, sizeof(hud_buf), kASCIIEncoding, 4, 4);

    // Tell the runtime we drew something
    return 1;
}

// -----------------------------------------------------------------------
// eventHandler - Playdate entry point
// -----------------------------------------------------------------------
#ifdef _WINDLL
__declspec(dllexport)
#endif
int eventHandler(PlaydateAPI *api, PDSystemEvent event, uint32_t arg) {
    (void)arg;

    switch (event) {
        case kEventInit:
            pd = api;

            // Initialise player
            player_init(&player);

            // Register the update callback
            pd->system->setUpdateCallback(update, NULL);
            break;

        case kEventTerminate:
            player_free(&player);
            break;

        default:
            break;
    }

    return 0;
}
```

## Key Design Decisions

### Entry Point: `eventHandler`

The Playdate SDK requires a function named `eventHandler` as the game entry point. It receives lifecycle events:

- `kEventInit` - Game is starting; set up state and register the update callback
- `kEventTerminate` - Game is shutting down; free resources

### Update Loop: `update`

Registered via `pd->system->setUpdateCallback()`. Called by the runtime at the target frame rate (default 30 fps on hardware). Must return `1` if the screen was modified, `0` otherwise.

### Player Update Logic (`player_update`)

1. **Crank speed control**
   - `pd->system->getCrankAngle()` returns the current crank position in degrees (0–360).
   - We normalise the angle to a –1…+1 range, then add a speed modifier to the base speed.
   - At 0° (crank resting position) the modifier is 0 and the player moves at `PLAYER_BASE_SPEED`.
   - Rotating the crank clockwise (toward 90°) increases speed; counter-clockwise (toward 270°) decreases it.
   - Speed is clamped to a minimum of 0.5 so the player can always move.

2. **D-pad movement**
   - `pd->system->getButtonState()` fills three bitmasks: currently held, just pressed, just released.
   - Holding `kButtonLeft` decrements `x`; holding `kButtonRight` increments `x`.
   - The delta applied each frame equals `player.speed` (which incorporates the crank modifier).

3. **Boundary clamping**
   - `x` is clamped to `[0, SCREEN_WIDTH - PLAYER_WIDTH]` so the sprite stays on screen.

### Bitmap Creation

`pd->graphics->newBitmap(width, height, kColorBlack)` creates a solid black rectangle. In a production game you would load a `.pdi` image with `pd->graphics->loadBitmap("images/player", &err)`.

## Makefile (minimal)

```makefile
HEAP_SIZE      = 8388208
STACK_SIZE     = 61800

PRODUCT = MyGame.pdx

SDK = $(shell awk '/^\s*SDKRoot/{print $$2}' ~/.Playdate/config 2>/dev/null || echo $(PLAYDATE_SDK_PATH))

VPATH += src
SRC    = src/main.c

include $(SDK)/C_API/buildsupport/common.mk
```

## pdxinfo

```
name=Moving Sprite Demo
author=Developer
description=D-pad moves the player, crank changes speed
bundleID=com.example.movingsprite
version=1.0
buildNumber=1
imagePath=images
```

## Building and Running

```bash
# Set SDK path (if not in config)
export PLAYDATE_SDK_PATH=/path/to/PlaydateSDK

# Build
make

# Run in simulator
open MyGame.pdx   # macOS
# or
/path/to/PlaydateSDK/bin/PlaydateSimulator MyGame.pdx
```

## Notes

- The Playdate screen is 400x240 pixels, 1-bit (black and white).
- The Playdate C API header is `pd_api.h`, included from the SDK's `C_API/` directory.
- The crank is a unique Playdate input device; always handle the `kEventLock`/`kEventUnlock` events if you rely heavily on crank input in a shipping game to pause gracefully when the device is locked.
