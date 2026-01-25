# Project Structure

Detailed project setup templates and configuration for Playdate C development.

## Template Repository

**Recommended**: Use the official template repository for new projects.

**Repository**: https://github.com/KeiNishi/kn-pd-template-c.git

Run `/playdate-init [project-name]` to create a new project from this template.

The template includes:
- Pre-configured CMakeLists.txt for the official SDK build system
- VSCode tasks for one-click build (Ctrl+Shift+B)
- Starter source code templates with utility libraries
- Recommended directory structure
- Build setup scripts for Windows
- .gitignore configuration

## Directory Structure

```
YourGame/
├── .vscode/
│   └── tasks.json             # VSCode build tasks (Ctrl+Shift+B)
├── source/                    # Source code and resources (bundled into .pdx)
│   ├── main.c                 # Entry point (eventHandler)
│   ├── game.c/h               # Game loop (init, update)
│   ├── types.h                # Common type definitions (fixed-point, Vector2, etc.)
│   ├── pools/                 # Object pool utilities
│   │   └── pool.h             # Generic macro-based object pool
│   ├── utils/                 # Utility libraries
│   │   ├── math_utils.c/h     # Math functions
│   │   ├── rng.c/h            # Random number generation
│   │   └── spatial_grid.c/h   # Spatial partitioning for collision
│   ├── resources/             # Game assets (images, sounds, fonts)
│   │   ├── fonts/             # Custom bitmap fonts
│   │   ├── images/            # Image assets (PNG/GIF)
│   │   ├── sounds/            # Audio files (WAV/MP3)
│   │   └── <custom>/          # Custom asset folders (e.g., player/, enemies/)
│   ├── pdxinfo                # Game metadata
│   └── README.md              # Source directory documentation (optional)
├── CMakeLists.txt             # Build configuration (CMake)
├── build-dev-setup.bat        # Windows: Create build-dev directory
├── build-sim-setup.bat        # Windows: Create build-sim directory
├── .gitignore                 # Git ignore rules
└── README.md                  # Project documentation
```

## Directory Descriptions

### source/
The main source directory containing all C code and resources. Everything in this directory is bundled into the final `.pdx` file.

### source/pools/
Contains object pool utilities for efficient memory management. Pools avoid dynamic allocation (malloc) which is problematic on Playdate's limited memory.

- **pool.h**: Generic macro-based pool implementation for reusable object management (bullets, particles, enemies, etc.)

### source/utils/
Contains utility libraries for common game development tasks.

- Math utilities, random number generation, spatial partitioning for collision detection, and other reusable helper functions.

### source/resources/
Contains all game assets. Subdirectories can be organized by type (fonts, images, sounds) or by game entity (player, enemies, ui).

- **fonts/**: Custom bitmap fonts
- **images/**: Sprite images, backgrounds, UI elements (PNG/GIF format)
- **sounds/**: Sound effects (WAV) and background music (MP3)
- **Custom folders**: Organize assets by feature or entity as needed

## pdxinfo Template

Game metadata file in `source/` directory:

```ini
# pdxinfo - Game metadata
name=Your Game Name
author=Your Name
description=Game description
bundleID=com.yourname.yourgame
version=1.0
buildNumber=1
```

## CMakeLists.txt Template

Standard Playdate CMake configuration:

```cmake
cmake_minimum_required(VERSION 3.14)
set(CMAKE_C_STANDARD 11)

# Find SDK path
set(ENVSDK $ENV{PLAYDATE_SDK_PATH})

if (NOT ${ENVSDK} STREQUAL "")
    # Convert path from Windows
    file(TO_CMAKE_PATH ${ENVSDK} SDK)
else()
    execute_process(
        COMMAND bash -c "egrep '^\\s*SDKRoot' $HOME/.Playdate/config"
        COMMAND head -n 1
        COMMAND cut -c9-
        OUTPUT_VARIABLE SDK
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
endif()

if (NOT EXISTS ${SDK})
    message(FATAL_ERROR "SDK Path not found; set ENV value PLAYDATE_SDK_PATH")
    return()
endif()

set(CMAKE_CONFIGURATION_TYPES "Debug;Release")
set(CMAKE_XCODE_GENERATE_SCHEME TRUE)

# Game Name Customization
set(PLAYDATE_GAME_NAME YourGame)
set(PLAYDATE_GAME_DEVICE YourGame_DEVICE)

project(${PLAYDATE_GAME_NAME} C ASM)

# Source files
file(GLOB SOURCES
    source/*.c
)

if (TOOLCHAIN STREQUAL "armgcc")
    add_executable(${PLAYDATE_GAME_DEVICE} ${SOURCES})
else()
    add_library(${PLAYDATE_GAME_NAME} SHARED ${SOURCES})
endif()

include(${SDK}/C_API/buildsupport/playdate_game.cmake)
```

## Project Initialization

### Using Template (Recommended)

```bash
# Clone the template
git clone https://github.com/KeiNishi/kn-pd-template-c.git YourGame

# Remove the template's git history
cd YourGame
rm -rf .git

# Update project name in source/pdxinfo and CMakeLists.txt
# (The /playdate-init command does this automatically)

# Initialize new git repository (optional)
git init
git add .
git commit -m "Initial commit"
```

### Manual Setup (Alternative)

Create a new project from scratch:

```bash
# Create directories
mkdir -p YourGame/{source/{pools,utils,resources/{fonts,images,sounds}},.vscode}
cd YourGame

# Create source/pdxinfo
cat > source/pdxinfo << 'EOF'
name=YourGame
author=YourName
description=A Playdate Game
bundleID=com.yourname.yourgame
version=1.0
buildNumber=1
EOF

# Create CMakeLists.txt (see template above)
# Create main.c template (see below)
# Create .vscode/tasks.json (see VSCode Tasks section)
```

## main.c Template

Minimal entry point:

```c
// main.c
#include "pd_api.h"
#include "game.h"

// Global Playdate API (extern from other files)
PlaydateAPI* g_pd = NULL;

#ifdef _WINDLL
__declspec(dllexport)
#endif
int eventHandler(PlaydateAPI* pd, PDSystemEvent event, uint32_t arg) {
    (void)arg;  // Mark unused parameter

    if (event == kEventInit) {
        g_pd = pd;

        // Set FPS (default 30, max 50 recommended)
        pd->display->setRefreshRate(30.0f);

        // Initialize game
        game_init();

        // Set update callback
        pd->system->setUpdateCallback(game_update, NULL);
    }

    return 0;
}
```

## game.h Template

```c
// game.h
#ifndef GAME_H
#define GAME_H

#include "pd_api.h"

// Global Playdate API
extern PlaydateAPI* g_pd;

// Game functions
void game_init(void);
int game_update(void* userdata);

#endif // GAME_H
```

## game.c Template

```c
// game.c
#include "game.h"

void game_init(void) {
    g_pd->system->logToConsole("Game initialized!");
}

int game_update(void* userdata) {
    (void)userdata;

    // Clear screen
    g_pd->graphics->clear(kColorWhite);

    // Draw text
    g_pd->graphics->drawText("Hello Playdate!", 15, kASCIIEncoding, 150, 110);

    // Show FPS (debug)
    g_pd->system->drawFPS(0, 0);

    return 1;  // Return 1 to continue, 0 to stop
}
```

## types.h Template

Common type definitions for Playdate C games:

```c
// types.h
#ifndef TYPES_H
#define TYPES_H

#include <stdint.h>
#include <stdbool.h>

// =============================================================================
// Fixed-Point Math (16.16 format)
// =============================================================================

typedef int32_t fixed16;

#define FP_SHIFT 16
#define FP_ONE (1 << FP_SHIFT)
#define FP_HALF (1 << (FP_SHIFT - 1))

// Conversion macros
#define INT_TO_FP(x) ((fixed16)((x) << FP_SHIFT))
#define FP_TO_INT(x) ((int)((x) >> FP_SHIFT))
#define FLOAT_TO_FP(x) ((fixed16)((x) * FP_ONE))
#define FP_TO_FLOAT(x) ((float)(x) / FP_ONE)

// Fixed-point arithmetic (64-bit intermediate to prevent overflow)
#define FP_MUL(a, b) ((fixed16)(((int64_t)(a) * (b)) >> FP_SHIFT))
#define FP_DIV(a, b) ((fixed16)(((int64_t)(a) << FP_SHIFT) / (b)))

// =============================================================================
// Vector2 (Fixed-Point)
// =============================================================================

typedef struct {
    fixed16 x;
    fixed16 y;
} Vector2;

static inline Vector2 vec2_create(fixed16 x, fixed16 y) {
    Vector2 v = { x, y };
    return v;
}

static inline Vector2 vec2_add(Vector2 a, Vector2 b) {
    Vector2 v = { a.x + b.x, a.y + b.y };
    return v;
}

static inline Vector2 vec2_sub(Vector2 a, Vector2 b) {
    Vector2 v = { a.x - b.x, a.y - b.y };
    return v;
}

// =============================================================================
// Entity ID (Generic)
// =============================================================================

typedef uint16_t EntityId;
#define ENTITY_INVALID 0xFFFF

// =============================================================================
// Utility Macros
// =============================================================================

#define MIN(a, b) ((a) < (b) ? (a) : (b))
#define MAX(a, b) ((a) > (b) ? (a) : (b))
#define CLAMP(x, lo, hi) MIN(MAX(x, lo), hi)
#define ARRAY_SIZE(arr) (sizeof(arr) / sizeof((arr)[0]))

// Playdate screen dimensions
#define SCREEN_WIDTH 400
#define SCREEN_HEIGHT 240

#endif // TYPES_H
```

## .gitignore Template

```gitignore
# Build artifacts
build/
build-dev/
build-sim/
*.pdx/

# Playdate Simulator cache
*.pdx.zip

# IDE (keep .vscode for tasks.json)
.vscode/*
!.vscode/tasks.json
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Debug
*.log
```

## VSCode Tasks Configuration

The template includes `.vscode/tasks.json` for one-click building.

### Build Commands (Ctrl+Shift+B)

| Task Name | Description |
|-----------|-------------|
| Playdate: Build Simulator | Build for simulator (default) |
| Playdate: Build Device | Build for Playdate hardware |
| Playdate: Clean Build | Remove build directory and rebuild |
| Playdate: Run Simulator | Build and launch simulator |

### Run in Simulator

```bash
# Windows
"%PLAYDATE_SDK_PATH%\bin\PlaydateSimulator.exe" build/YourGame.pdx

# macOS
open build/YourGame.pdx

# Linux
"${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" build/YourGame.pdx
```
