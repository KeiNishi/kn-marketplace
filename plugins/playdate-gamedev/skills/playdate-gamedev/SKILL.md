---
name: playdate-gamedev
description: This skill should be used when the user asks to "create a Playdate game", "set up a Playdate project", "write C code for Playdate", mentions "Playdate SDK", ".pdx", "pdc compiler", or works with Playdate APIs like sprites, graphics, crank input, or sound. Also triggers on "/playdate" command or questions about Playdate game development patterns and optimization.
allowed-tools: Bash(cmake*), Bash(nmake*), Bash(make*), Bash(pdc*), Bash(mkdir*), Bash(ls*), Read, Write, Edit, Glob, Grep, Task
---

# Playdate Game Development Guide

Comprehensive guide for Playdate C language game development. Covers project setup, coding standards, Playdate SDK APIs, asset management, and performance optimization.

## Prerequisites

### Required Tools

**Windows**:
- Visual Studio 2019 or 2022 with C/C++ tools
- GNU Arm Embedded Toolchain (`gcc-arm-none-eabi`)
- CMake (added to PATH)

**Linux/macOS**:
- GCC or Clang compiler
- GNU Arm Embedded Toolchain (`gcc-arm-none-eabi`)
- CMake and Make

### Environment Setup

- Playdate SDK installed
- Environment variable `PLAYDATE_SDK_PATH` configured
- Basic C language knowledge

## Project Structure

Recommended directory layout for Playdate projects:

```
YourGame/
├── CMakeLists.txt             # Build configuration (CMake)
├── Source/                    # Source code
│   ├── main.c                 # Entry point
│   ├── game.c/h               # Game logic
│   ├── player.c/h             # Player
│   ├── utils.c/h              # Utilities
│   └── pdxinfo                # Game metadata
├── assets/                    # Raw assets (pre-build)
│   ├── images/
│   ├── sounds/
│   └── fonts/
└── build/                     # Build artifacts (gitignore)
```

For detailed templates and initialization commands, see `references/project-structure.md`.

## Coding Standards

### Naming Conventions

```c
// Constants: SCREAMING_SNAKE_CASE
#define MAX_ENEMIES 100

// Types: PascalCase
typedef struct Player {
    float x, y;
    int health;
} Player;

// Functions: snake_case
void update_player(Player* player, float dt);

// Variables: snake_case
int enemy_count = 0;

// Global variables: g_ prefix
static PlaydateAPI* g_pd = NULL;
```

### File Organization Pattern

**Header files (.h)**: Public API declarations with include guards
**Implementation files (.c)**: Struct definitions and function implementations

For complete coding standards including error handling patterns, see `references/coding-standards.md`.

## Build Workflow

**Windows**: Use "x64 Native Tools Command Prompt for VS 2019/2022"

### Simulator Build

```bash
# Windows
mkdir build && cd build
cmake .. -G "NMake Makefiles"
nmake
"%PLAYDATE_SDK_PATH%\bin\PlaydateSimulator.exe" YourGame.pdx

# Linux/macOS
mkdir build && cd build
cmake ..
make
"${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" YourGame.pdx
```

### Device Build

```bash
# Windows
cmake .. -G "NMake Makefiles" --toolchain="%PLAYDATE_SDK_PATH%/C_API/buildsupport/arm.cmake"
nmake

# Linux/macOS
cmake .. --toolchain="${PLAYDATE_SDK_PATH}/C_API/buildsupport/arm.cmake"
make
```

### Clean Build

```bash
# Remove build directory and rebuild
rm -rf build && mkdir build && cd build
cmake .. -G "NMake Makefiles"  # Windows
cmake ..                        # Linux/macOS
```

### Debug Logging

```c
g_pd->system->logToConsole("Player pos: %.2f, %.2f", player->x, player->y);
g_pd->system->error("Fatal error occurred");  // Stops execution
```

## Core API Patterns

### Entry Point (main.c)

```c
#include "pd_api.h"
#include "game.h"

PlaydateAPI* g_pd = NULL;

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

### Game Loop

```c
int game_update(void* userdata) {
    (void)userdata;
    float dt = 1.0f / 30.0f;

    g_pd->graphics->clear(kColorWhite);

    // Update logic
    player_update(player, dt);

    // Draw
    player_draw(player);
    g_pd->system->drawFPS(0, 0);

    return 1;  // Continue running
}
```

### Input Handling

```c
PDButtons current, pushed, released;
g_pd->system->getButtonState(&current, &pushed, &released);

if (current & kButtonLeft) { /* Held */ }
if (pushed & kButtonA) { /* Just pressed */ }

// Crank
float angle = g_pd->system->getCrankAngle();      // 0-360 degrees
float change = g_pd->system->getCrankChange();    // degrees/frame
```

For comprehensive API patterns including graphics, sprites, collision, sound, and file I/O, see `references/playdate-api.md`.

## Memory Management

Always use Playdate's allocator:

```c
// Allocate
void* ptr = g_pd->system->realloc(NULL, sizeof(Player));

// Free
g_pd->system->realloc(ptr, 0);
```

Avoid stdlib malloc/free when possible.

## Asset Management

### Supported Formats

- **Images**: PNG/GIF (auto-converted to 1-bit)
- **Audio**: WAV (effects), MP3 (BGM)
- **Fonts**: Custom bitmap fonts

### Loading Assets

```c
// Bitmap
LCDBitmap* bmp = g_pd->graphics->loadBitmap("images/player", NULL);

// Sound effect
AudioSample* sample = g_pd->sound->sample->load("sounds/jump", NULL);

// BGM
FilePlayer* player = g_pd->sound->fileplayer->newPlayer();
g_pd->sound->fileplayer->loadIntoPlayer(player, "sounds/bgm");
```

For detailed asset management including sprite sheets and animations, see `references/asset-management.md`.

## Performance Optimization

### Key Principles

1. **30fps target** - Balance battery and smoothness
2. **Minimize screen clears** - Update dirty regions only
3. **Use sprite system** - Auto-culling and z-ordering
4. **Object pooling** - Avoid runtime allocation
5. **Cache calculations** - Avoid per-frame recomputation

### Sprite Optimization

```c
// Z-ordering
g_pd->sprite->setZIndex(foreground, 10);
g_pd->sprite->setZIndex(background, 0);

// Visibility culling
g_pd->sprite->setVisible(offscreen_sprite, 0);
```

For advanced optimization including object pools and custom allocators, see `references/performance.md`.

## Best Practices

### Do's

- Use global `PlaydateAPI* g_pd` referenced via extern
- Always NULL-check pointers before use
- Free all allocated memory with `realloc(ptr, 0)`
- Leverage sprite system for automatic rendering and collision
- Target 30fps for battery efficiency
- Use `logToConsole()` for debugging

### Don'ts

- Avoid stdlib malloc/free in favor of Playdate API
- Don't clear entire screen every frame
- Don't hold large bitmaps in memory unnecessarily
- Don't use complex collision detection when sprite system suffices
- Don't abuse global variables - use structs for organization
- Never skip error handling on resource allocation

## Advanced Patterns

For advanced implementation patterns including:
- State machines for game flow
- Object pools for bullets/particles
- Data-driven design with JSON
- Custom allocators
- Lua bindings from C

See `references/advanced-patterns.md`.

## Troubleshooting

### Common Build Errors

```bash
# "SDK Path not found" - Set environment variable
# Windows (System Environment Variables or PowerShell)
$env:PLAYDATE_SDK_PATH = "C:\Users\<Username>\Documents\PlaydateSDK"

# Linux/macOS
export PLAYDATE_SDK_PATH=/path/to/PlaydateSDK

# "nmake not found" (Windows)
# Use "x64 Native Tools Command Prompt for VS 2019/2022"

# CMakeLists.txt must include
include(${SDK}/C_API/buildsupport/playdate_game.cmake)
```

### Runtime Issues

- **NULL pointer crashes**: Add defensive NULL checks
- **Memory allocation failures**: Check return values, release unused resources
- **Low FPS**: Profile with `getCurrentTimeMilliseconds()`, reduce draw calls

## Additional Resources

### Reference Files

Detailed documentation in `references/`:
- **`project-structure.md`** - Project templates, pdxinfo, CMakeLists.txt
- **`coding-standards.md`** - Complete coding conventions
- **`playdate-api.md`** - Comprehensive API patterns
- **`asset-management.md`** - Asset handling and animations
- **`performance.md`** - Optimization techniques
- **`advanced-patterns.md`** - State machines, pools, data-driven design

### External Links

- [Playdate SDK Documentation](https://sdk.play.date/)
- [Playdate Developer Forum](https://devforum.play.date/)
- [Inside Playdate](https://sdk.play.date/inside-playdate/)
