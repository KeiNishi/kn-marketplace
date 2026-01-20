---
name: playdate-init
description: Initialize a new Playdate C project with recommended structure, CMakeLists.txt, pdxinfo, and starter code templates
argument-hint: "[project-name]"
allowed-tools: Bash, Write, Read, Glob
---

# Playdate Project Initialization

Initialize a new Playdate C project with the official CMake build system and starter templates.

## Prerequisites

Before creating a project, ensure the following are installed:

### Windows
1. **Visual Studio 2019 or 2022** with C/C++ tools
2. **GNU Arm Embedded Toolchain** (`gcc-arm-none-eabi`) - Download from developer.arm.com
3. **CMake** - Download from cmake.org
4. **PLAYDATE_SDK_PATH** environment variable set

### Linux/macOS
1. **GCC or Clang** compiler
2. **GNU Arm Embedded Toolchain** (`gcc-arm-none-eabi`)
3. **CMake** and **Make**
4. **PLAYDATE_SDK_PATH** environment variable set

## Instructions

When the user runs `/playdate-init [project-name]`:

1. **Determine project name and location**:
   - If `[project-name]` is provided, use it
   - If not provided, ask the user for a project name
   - Create the project in the current working directory

2. **Create directory structure**:
   ```
   ProjectName/
   ├── CMakeLists.txt
   ├── Source/
   │   ├── main.c
   │   ├── game.h
   │   ├── game.c
   │   └── pdxinfo
   └── assets/
       ├── images/
       ├── sounds/
       └── fonts/
   ```

3. **Create Source/pdxinfo** with user-provided or default values:
   ```ini
   name=ProjectName
   author=Developer
   description=A Playdate Game
   bundleID=com.developer.projectname
   version=1.0
   buildNumber=1
   ```

4. **Create CMakeLists.txt** (official SDK build system):
   ```cmake
   cmake_minimum_required(VERSION 3.14)
   set(CMAKE_C_STANDARD 11)

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
   set(PLAYDATE_GAME_NAME ProjectName)
   set(PLAYDATE_GAME_DEVICE ProjectName_DEVICE)

   project(${PLAYDATE_GAME_NAME} C ASM)

   # Source files
   file(GLOB SOURCES Source/*.c)

   if (TOOLCHAIN STREQUAL "armgcc")
       add_executable(${PLAYDATE_GAME_DEVICE} ${SOURCES})
   else()
       add_library(${PLAYDATE_GAME_NAME} SHARED ${SOURCES})
   endif()

   include(${SDK}/C_API/buildsupport/playdate_game.cmake)
   ```

5. **Create starter source files**:
   - `Source/main.c` - Entry point with eventHandler
   - `Source/game.h` - Game header with declarations
   - `Source/game.c` - Basic game loop implementation

6. **Create .gitignore**:
   ```
   build/
   *.pdx/
   ```

7. **Provide next steps**:

   **Windows** (use "x64 Native Tools Command Prompt for VS 2019/2022"):
   ```bash
   cd ProjectName
   mkdir build
   cd build
   cmake .. -G "NMake Makefiles"
   nmake
   ```

   **Linux/macOS**:
   ```bash
   cd ProjectName
   mkdir build
   cd build
   cmake ..
   make
   ```

   **Run in simulator**:
   ```bash
   "${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" ProjectName.pdx
   ```

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

- **Windows**: Always use **"x64 Native Tools Command Prompt for VS 2019/2022"** for building
- Ensure `PLAYDATE_SDK_PATH` environment variable is set before building
- The project uses 30 FPS by default (recommended for battery life)
- All source files go in the `Source/` directory
- The `pdxinfo` file must be in the `Source/` directory
- Assets are placed in `assets/` subdirectories (copied to .pdx during build)
- Build output goes to `build/` directory
- The `.pdx` bundle is generated after successful build
- For more examples, refer to `$PLAYDATE_SDK_PATH/C_API/Examples/`
