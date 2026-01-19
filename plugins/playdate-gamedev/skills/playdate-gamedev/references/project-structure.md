# Project Structure

Detailed project setup templates and configuration for Playdate C development.

## Directory Structure

```
YourGame/
├── Source/                    # Source code
│   ├── main.c                 # Entry point
│   ├── game.c/h               # Game logic
│   ├── player.c/h             # Player
│   ├── enemy.c/h              # Enemies
│   ├── utils.c/h              # Utilities
│   └── assets/                # Assets referenced from source
├── assets/                    # Raw assets (pre-build)
│   ├── images/
│   │   ├── player.png
│   │   └── tileset.png
│   ├── sounds/
│   │   ├── bgm.wav
│   │   └── sfx/
│   └── fonts/
│       └── custom-font/
├── builds/                    # Build artifacts (gitignore)
├── Makefile                   # Build configuration
├── pdxinfo                    # Game metadata
└── README.md
```

## pdxinfo Template

Game metadata file at project root:

```ini
# pdxinfo - Game metadata
name=Your Game Name
author=Your Name
description=Game description
bundleID=com.yourname.yourgame
version=1.0
buildNumber=1
imagePath=assets/images/
```

## Makefile Template

Standard Playdate Makefile:

```makefile
# Playdate SDK path
SDK = ${PLAYDATE_SDK_PATH}

# Game name (.pdx will be created)
GAME = YourGame

# Source files
SRC = Source/main.c \
      Source/game.c \
      Source/player.c \
      Source/enemy.c \
      Source/utils.c

# Include paths
INCLUDE = -ISource

# Compiler flags
CFLAGS = -O2 -Wall -Wextra -Werror

# Include Playdate SDK Makefile
include $(SDK)/C_API/buildsupport/common.mk
```

## Project Initialization Commands

Create a new project from scratch:

```bash
# Create directories
mkdir -p YourGame/{Source,assets/{images,sounds,fonts},builds}
cd YourGame

# Create pdxinfo
cat > pdxinfo << 'EOF'
name=YourGame
author=YourName
description=A Playdate Game
bundleID=com.yourname.yourgame
version=1.0
buildNumber=1
imagePath=assets/images/
EOF

# Create Makefile
cat > Makefile << 'EOF'
SDK = ${PLAYDATE_SDK_PATH}
GAME = YourGame
SRC = Source/main.c Source/game.c
INCLUDE = -ISource
CFLAGS = -O2 -Wall -Wextra -Werror
include $(SDK)/C_API/buildsupport/common.mk
EOF

# Create main.c template (see main.c template below)
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
builds/
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

### Simulator Build

```bash
# Build for simulator
make

# Run in simulator (macOS)
open builds/YourGame.pdx

# Run in simulator (Windows/Linux)
"${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" builds/YourGame.pdx
```

### Device Build

```bash
# Build for device (optimized)
make DEVICE=1
```

### Clean and Rebuild

```bash
make clean
make
```

### Watch Mode (with entr)

```bash
# Auto-rebuild on file changes
find Source -name '*.c' -o -name '*.h' | entr -c make
```
