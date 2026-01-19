---
name: playdate-init
description: Initialize a new Playdate C project with recommended structure, Makefile, pdxinfo, and starter code templates
argument-hint: "[project-name]"
allowed-tools: Bash, Write, Read, Glob
---

# Playdate Project Initialization

Initialize a new Playdate C project with the recommended directory structure and starter templates.

## Instructions

When the user runs `/playdate-init [project-name]`:

1. **Determine project name and location**:
   - If `[project-name]` is provided, use it
   - If not provided, ask the user for a project name
   - Create the project in the current working directory

2. **Create directory structure**:
   ```
   ProjectName/
   ├── Source/
   ├── assets/
   │   ├── images/
   │   ├── sounds/
   │   └── fonts/
   └── builds/
   ```

3. **Create pdxinfo** with user-provided or default values:
   ```ini
   name=ProjectName
   author=Developer
   description=A Playdate Game
   bundleID=com.developer.projectname
   version=1.0
   buildNumber=1
   ```

4. **Create Makefile**:
   ```makefile
   SDK = ${PLAYDATE_SDK_PATH}
   GAME = ProjectName
   SRC = Source/main.c Source/game.c
   INCLUDE = -ISource
   CFLAGS = -O2 -Wall -Wextra -Werror
   include $(SDK)/C_API/buildsupport/common.mk
   ```

5. **Create starter source files**:
   - `Source/main.c` - Entry point with eventHandler
   - `Source/game.h` - Game header with declarations
   - `Source/game.c` - Basic game loop implementation

6. **Create .gitignore** for builds/ directory

7. **Provide next steps**:
   - How to build: `make`
   - How to run: `"${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" builds/ProjectName.pdx`
   - Suggest reading the playdate-gamedev skill for coding standards

## Source File Templates

### main.c

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

### game.h

```c
#ifndef GAME_H
#define GAME_H

#include "pd_api.h"

extern PlaydateAPI* g_pd;

void game_init(void);
int game_update(void* userdata);

#endif
```

### game.c

```c
#include "game.h"

void game_init(void) {
    g_pd->system->logToConsole("Game initialized!");
}

int game_update(void* userdata) {
    (void)userdata;

    g_pd->graphics->clear(kColorWhite);
    g_pd->graphics->drawText("Hello Playdate!", 15, kASCIIEncoding, 150, 110);
    g_pd->system->drawFPS(0, 0);

    return 1;
}
```

## Important Notes

- Ensure PLAYDATE_SDK_PATH environment variable is set before building
- The project uses 30 FPS by default (recommended for battery life)
- All source files go in the Source/ directory
- Assets are placed in assets/ subdirectories
- Build output goes to builds/ (gitignored)
