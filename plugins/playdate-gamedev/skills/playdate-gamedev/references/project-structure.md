# Project Structure

Detailed project setup templates and configuration for Playdate C development.

## Directory Structure

```
YourGame/
├── CMakeLists.txt             # Build configuration (CMake)
├── Source/                    # Source code
│   ├── main.c                 # Entry point
│   ├── game.c/h               # Game logic
│   ├── player.c/h             # Player
│   ├── enemy.c/h              # Enemies
│   ├── utils.c/h              # Utilities
│   ├── pdxinfo                # Game metadata
│   └── images/                # Assets copied to build
│       ├── player.png
│       └── tileset.png
├── assets/                    # Raw assets (pre-build)
│   ├── images/
│   ├── sounds/
│   │   ├── bgm.wav
│   │   └── sfx/
│   └── fonts/
│       └── custom-font/
└── build/                     # Build artifacts (gitignore)
```

## pdxinfo Template

Game metadata file in `Source/` directory:

```ini
# pdxinfo - Game metadata
name=Your Game Name
author=Your Name
description=Game description
bundleID=com.yourname.yourgame
version=1.0
buildNumber=1
imagePath=images/
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
    Source/*.c
)

if (TOOLCHAIN STREQUAL "armgcc")
    add_executable(${PLAYDATE_GAME_DEVICE} ${SOURCES})
else()
    add_library(${PLAYDATE_GAME_NAME} SHARED ${SOURCES})
endif()

include(${SDK}/C_API/buildsupport/playdate_game.cmake)
```

## Project Initialization Commands

Create a new project from scratch:

```bash
# Create directories
mkdir -p YourGame/{Source,assets/{images,sounds,fonts}}
cd YourGame

# Create Source/pdxinfo
cat > Source/pdxinfo << 'EOF'
name=YourGame
author=YourName
description=A Playdate Game
bundleID=com.yourname.yourgame
version=1.0
buildNumber=1
EOF

# Create CMakeLists.txt (see template above)
# Create main.c template (see below)
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
#include "player.h"

static Player* player = NULL;

void game_init(void) {
    // Create player at center of screen
    player = player_create(200.0f, 120.0f);
}

int game_update(void* userdata) {
    (void)userdata;

    float dt = 1.0f / 30.0f;  // Assuming 30fps

    // Clear screen
    g_pd->graphics->clear(kColorWhite);

    // Update
    player_update(player, dt);

    // Draw
    player_draw(player);

    // Show FPS (debug)
    g_pd->system->drawFPS(0, 0);

    return 1;  // Return 1 to continue, 0 to stop
}
```

## .gitignore Template

```gitignore
# Build artifacts
build/
*.pdx/

# Playdate Simulator cache
*.pdx.zip

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Debug
*.log
```

## Build Commands

**Windows**: Use "x64 Native Tools Command Prompt for VS 2019/2022"

### Simulator Build

```bash
# Windows
mkdir build
cd build
cmake .. -G "NMake Makefiles"
nmake

# Linux/macOS
mkdir build
cd build
cmake ..
make
```

### Run in Simulator

```bash
# Windows
"%PLAYDATE_SDK_PATH%\bin\PlaydateSimulator.exe" YourGame.pdx

# macOS
open YourGame.pdx

# Linux
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

### Clean and Rebuild

```bash
# Remove build directory and rebuild
rm -rf build
mkdir build
cd build
cmake .. -G "NMake Makefiles"  # Windows
cmake ..                        # Linux/macOS
```

### Watch Mode (with entr - Linux/macOS)

```bash
# Auto-rebuild on file changes
find Source -name '*.c' -o -name '*.h' | entr -c sh -c 'cd build && make'
```
