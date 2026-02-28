# Evaluation Transcript

## Task

Create a simple Playdate game in C with a moving player sprite. The player moves left/right with the D-pad; the crank controls their speed.

---

## Steps Taken

### Step 1: Read SKILL.md

**File**: `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/SKILL.md`

Learned:
- Required entry point: `eventHandler` (not `main`)
- Global pointer pattern: `PlaydateAPI* g_pd = NULL;`
- Naming conventions: `snake_case` functions, `g_` prefix for globals, `PascalCase` types, `SCREAMING_SNAKE_CASE` constants
- Memory: `g_pd->system->realloc(NULL, size)` to allocate, `realloc(ptr, 0)` to free
- Game loop registration: `pd->system->setUpdateCallback(game_update, NULL)`
- 30 fps target: `pd->display->setRefreshRate(30.0f)`
- Project structure: `main.c`, `game.c/h`, player module files

### Step 2: Read references/playdate-api.md

**File**: `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/references/playdate-api.md`

Learned:
- Sprite creation: `g_pd->sprite->newSprite()`, `addSprite`, `moveTo`, `drawSprites`
- Setting sprite image: `setImage` with `LCDBitmap`, or `setDrawFunction` for a draw callback
- Sprite bounds: `setBounds` with `PDRect`
- Button input: `g_pd->system->getButtonState(&current, &pushed, &released)`, `kButtonLeft`, `kButtonRight`, `kButtonUp`, `kButtonDown`
- Crank input: `isCrankDocked()`, `getCrankAngle()` (0-360 absolute), `getCrankChange()` (delta per frame)
- Screen clear: `g_pd->graphics->clear(kColorWhite)`
- Drawing primitives: `fillRect`, `drawRect`, `fillEllipse`
- FPS display: `g_pd->system->drawFPS(0, 0)`

### Step 3: Read references/coding-standards.md

**File**: `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/references/coding-standards.md`

Learned:
- Header guard pattern: `#ifndef PLAYER_H` / `#define PLAYER_H` / `#endif`
- Forward declaration pattern in headers: `typedef struct Player Player;`
- Struct definition hidden in `.c` file: `struct Player { ... };`
- `extern PlaydateAPI* g_pd;` to reference global from other files
- Error handling: NULL-check every pointer, log with `logToConsole`, fatal with `error`
- Region comments: `// ====... SECTION ...====`
- Include order: own header, pd_api.h, project headers, stdlib

### Step 4: Design the Implementation

Based on the references, planned 5 files:

| File | Purpose |
|------|---------|
| `main.c` | `eventHandler` entry point, `g_pd` global |
| `game.h` | `game_init`, `game_update` declarations |
| `game.c` | Game loop: clear, update, drawSprites |
| `player.h` | Public player API with forward declaration |
| `player.c` | Player struct, create/destroy/update with D-pad + crank |

### Step 5: Implement main.c

- Declared `PlaydateAPI* g_pd = NULL;` at file scope
- Added `#ifdef _WINDLL __declspec(dllexport) #endif` guard
- `eventHandler` handles `kEventInit`: stores `g_pd`, sets 30fps, calls `game_init()`, registers `game_update`

### Step 6: Implement game.c

- `game_init()`: creates player at screen center (200, 120)
- `game_update()`: clears screen, calls `player_update`, calls `drawSprites`, shows FPS counter, returns 1

### Step 7: Implement player.c

- `player_create`: allocates with `realloc(NULL, sizeof(Player))`, creates sprite, sets draw callback and bounds, calls `addSprite`
- `player_destroy`: removes and frees sprite, frees struct
- `player_update`:
  1. Reads crank angle via `getCrankAngle()` and maps 0-360 to a speed multiplier (0.25x to 2.0x)
  2. Falls back to base speed when crank is docked (`isCrankDocked()`)
  3. Reads D-pad via `getButtonState`, applies `speed * dt` to X (and Y for up/down)
  4. Clamps position to screen bounds
  5. Syncs sprite position with `moveTo`

### Step 8: Write output files

- `response.md`: full implementation with all 5 source files and design notes
- `transcript.md`: this file
- `metrics.json`: step count and error count

---

## References Consulted

1. `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/SKILL.md`
2. `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/references/playdate-api.md`
3. `/home/user/kn-marketplace/plugins/playdate-gamedev/skills/playdate-gamedev/references/coding-standards.md`

## Conventions Applied

| Convention | Applied |
|-----------|---------|
| `eventHandler` entry point | Yes - `main.c` |
| `PlaydateAPI* g_pd` global | Yes - declared in `main.c`, `extern` in `.c` files |
| `snake_case` functions | Yes - `player_create`, `player_update`, `game_init`, etc. |
| `g_` prefix for globals | Yes - `g_pd`, `g_player` |
| `PascalCase` types | Yes - `Player`, `GameState` |
| `SCREAMING_SNAKE_CASE` constants | Yes - `PLAYER_BASE_SPEED`, `SCREEN_WIDTH`, etc. |
| `g_pd->system->realloc` for memory | Yes - all allocations and frees |
| `setUpdateCallback` for game loop | Yes - registered in `eventHandler` |
| `getCrankChange()` / `getCrankAngle()` | Yes - crank speed mapping in `player_update` |
| NULL checks on all pointers | Yes - every function entry |
| Include guards in headers | Yes |
| Forward declarations in headers | Yes - `typedef struct Player Player;` |
