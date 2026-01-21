# Project Structure

Detailed project setup templates and configuration for Playdate C development.

## Template Repository

**Recommended**: Use the official template repository for new projects.

**Repository**: https://github.com/KeiNishi/kn-pd-template-c.git

Run `/playdate-init [project-name]` to create a new project from this template.

The template includes:
- Pre-configured CMakeLists.txt for the official SDK build system
- VSCode tasks for one-click build (Ctrl+Shift+B)
- Starter source code templates
- Recommended directory structure
- .gitignore configuration

## Directory Structure

```
YourGame/
├── .vscode/
│   └── tasks.json             # VSCode build tasks (Ctrl+Shift+B)
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

## Project Initialization

### Using Template (Recommended)

```bash
# Clone the template
git clone https://github.com/KeiNishi/kn-pd-template-c.git YourGame

# Remove the template's git history
cd YourGame
rm -rf .git

# Update project name in Source/pdxinfo and CMakeLists.txt
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
mkdir -p YourGame/{Source,assets/{images,sounds,fonts},.vscode}
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
