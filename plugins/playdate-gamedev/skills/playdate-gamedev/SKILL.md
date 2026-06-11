---
name: playdate-gamedev
description: This skill should be used when developing games in C for the Panic Playdate handheld. Use when the user asks to "create a Playdate game", "set up a Playdate project", "write C code for Playdate", or mentions Playdate, PlaydateSDK, the Playdate SDK, ".pdx" bundles, "pd_api.h", the "pdc" compiler, PLAYDATE_SDK_PATH, PlaydateAPI calls such as "playdate->graphics" or "pd->system", crank input, or Playdate sprites, sound, asset, and performance questions. Also triggers on "/playdate" commands.
allowed-tools: Bash(cmake*), Bash(nmake*), Bash(make*), Bash(pdc*), Bash(mkdir*), Bash(ls*), Read, Write, Edit, Glob, Grep, Task
---

# Playdate Game Development Guide

Playdate C game development: project setup, build workflow, coding standards, SDK API patterns, asset management, and performance optimization.

## Prerequisites

- Playdate SDK installed and `PLAYDATE_SDK_PATH` environment variable set
- CMake on PATH; GNU Arm Embedded Toolchain (`gcc-arm-none-eabi`) for device builds
- Compiler: GCC or Clang + Make (Linux/macOS), or Visual Studio 2019/2022 with C/C++ tools + NMake (Windows)

If `PLAYDATE_SDK_PATH` is not set:

```bash
export PLAYDATE_SDK_PATH=/path/to/PlaydateSDK
```

(Windows PowerShell: `$env:PLAYDATE_SDK_PATH = "C:/Users/<Username>/Documents/PlaydateSDK"`, or set it permanently via System Properties > Environment Variables.)

## Quick Start: New Project

1. Clone the template repository:

   ```bash
   git clone https://github.com/KeiNishi/kn-pd-template-c.git YourGame
   ```

2. Delete the cloned `.git` directory to start fresh.
3. Rename the project: in `source/pdxinfo` set `name` and `bundleID` (lowercase reverse-domain), and in `CMakeLists.txt` set `PLAYDATE_GAME_NAME` and `PLAYDATE_GAME_DEVICE`.
4. Build and run (next section).

In Claude Code, the `/playdate-init` command automates steps 1-3; otherwise perform them manually as above.

**Fallback — if the clone fails or the user prefers no template**: create the minimal project by hand: a `source/` directory containing `main.c`, `game.c`/`game.h`, and `pdxinfo`, plus a root `CMakeLists.txt` that includes `${SDK}/C_API/buildsupport/playdate_game.cmake`. Copy the complete file templates (`CMakeLists.txt`, `pdxinfo`, `main.c`, `game.c/h`, `types.h`, `.vscode/tasks.json`, `.gitignore`) from `references/project-structure.md`.

Layout in one line: everything under `source/` (C code, `resources/` assets, `pdxinfo` metadata) is bundled into the `.pdx`; `CMakeLists.txt` lives at the project root.

## Build and Run

Default (Linux/macOS):

```bash
mkdir -p build && cd build
cmake .. && make                                                                  # simulator build
cmake .. --toolchain="${PLAYDATE_SDK_PATH}/C_API/buildsupport/arm.cmake" && make  # device build
```

(Windows: run from the "x64 Native Tools Command Prompt for VS 2019/2022", use `cmake .. -G "NMake Makefiles"` and `nmake` instead of `cmake ..` and `make`.)

If the project has `.vscode/tasks.json` (the template does), Ctrl+Shift+B in VSCode offers the tasks "Playdate: Build Simulator", "Build Device", "Clean Build", and "Run Simulator".

Run the simulator on the built `.pdx`:

```bash
"${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" build/YourGame.pdx
```

(macOS: `open build/YourGame.pdx`; Windows PowerShell: `& "$env:PLAYDATE_SDK_PATH/bin/PlaydateSimulator.exe" build/YourGame.pdx`.)

## Reference Routing

Load the matching file from `references/` on demand:

- Creating project files, `CMakeLists.txt`, `pdxinfo`, VSCode tasks, full source templates → `references/project-structure.md`
- Naming conventions, header/file organization, error handling, code style → `references/coding-standards.md`
- Calling SDK APIs: graphics/drawing, sprites and collision, input (buttons and crank), sound, file I/O, system menu → `references/playdate-api.md`
- Adding images, audio, or fonts; sprite sheets and animations; loading strategies → `references/asset-management.md`
- Low FPS, memory pressure, object pooling, profiling, dirty-rect drawing → `references/performance.md`
- State machines, scene management, timers, data-driven design, custom allocators, lightweight ECS, events, tweens → `references/advanced-patterns.md`

## Core Rules

Apply these in all Playdate C code:

1. One global `PlaydateAPI* g_pd`, assigned in `eventHandler` on `kEventInit`, referenced via `extern` elsewhere.
2. Allocate through Playdate, not stdlib: `g_pd->system->realloc(NULL, size)` to allocate, `g_pd->system->realloc(ptr, 0)` to free. Avoid `malloc`/`free`.
3. No dynamic allocation inside the update loop — preallocate at init and use object pools.
4. Target 30 fps (`pd->display->setRefreshRate(30.0f)`) for battery efficiency.
5. NULL-check every resource load and allocation; log failures with `g_pd->system->logToConsole()` (use `g_pd->system->error()` only for fatal stops).
6. Naming: `SCREAMING_SNAKE_CASE` constants, `PascalCase` types, `snake_case` functions and variables, `g_` prefix for globals.
7. Prefer the sprite system (automatic culling, z-ordering, collision) over manual full-screen redraws; avoid clearing the whole screen every frame.
8. Free everything allocated: bitmaps, samples, and players via their matching `free*` functions.

## Troubleshooting

- "pd_api.h: No such file" or "SDK path not found" → `PLAYDATE_SDK_PATH` is unset or wrong; the directory must contain `C_API/pd_api.h`.
- "nmake is not recognized" (Windows) → run from the "x64 Native Tools Command Prompt for VS 2019/2022".
- Undefined reference errors → ensure every `.c` file is listed in `CMakeLists.txt` and declarations match definitions.
- Build configures but produces no `.pdx` → `CMakeLists.txt` must `include(${SDK}/C_API/buildsupport/playdate_game.cmake)`.
- Low FPS at runtime → profile with `getCurrentTimeMilliseconds()` and see `references/performance.md`.

## Verification Checklist

Before declaring a Playdate task complete, confirm:

- [ ] Simulator build succeeds and produces a `.pdx` bundle
- [ ] Device build succeeds with the `arm.cmake` toolchain
- [ ] Game runs in the simulator with no errors in the console
- [ ] All allocation goes through `g_pd->system->realloc` (no stdlib `malloc`/`free`)
- [ ] No dynamic allocation inside the update loop
- [ ] Every loaded resource is NULL-checked and eventually freed
- [ ] `pdxinfo` has correct `name` and a lowercase reverse-domain `bundleID`

## External Resources

- Playdate SDK documentation: https://sdk.play.date/ (C API guide: https://sdk.play.date/inside-playdate-with-c/)
- Playdate Developer Forum: https://devforum.play.date/
- SDK examples: `$PLAYDATE_SDK_PATH/C_API/Examples/`
