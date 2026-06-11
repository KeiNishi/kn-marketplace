# playdate-gamedev

A Claude Code plugin for developing [Panic Playdate](https://play.date/) games in C.
It bundles project setup, build workflow, coding standards, SDK API patterns, asset
management, and performance optimization guidance into one skill plus two slash commands.

## What's Included

| Component | Description |
|-----------|-------------|
| Skill `playdate-gamedev` | Core workflow and rules; auto-triggers on Playdate topics (`.pdx`, `pd_api.h`, `pdc`, crank, sprites, PlaydateSDK) |
| Command `/playdate-init` | Create a new project from the [kn-pd-template-c](https://github.com/KeiNishi/kn-pd-template-c) template (with a manual fallback if cloning is not possible) |
| Command `/playdate-build` | Build the `.pdx` bundle for simulator or device, with troubleshooting for common errors |

### Reference Library

Loaded on demand from `skills/playdate-gamedev/references/`:

- `project-structure.md` - Directory layout, `CMakeLists.txt`, `pdxinfo`, and full source file templates
- `coding-standards.md` - Naming conventions, file organization, error handling
- `playdate-api.md` - Graphics, sprites, input (buttons/crank), sound, file I/O, menus
- `asset-management.md` - Images, audio, fonts, sprite sheets, animations
- `performance.md` - Memory management, drawing optimization, object pooling, profiling
- `advanced-patterns.md` - State machines, scenes, data-driven design, custom allocators, ECS

## Prerequisites

- [Playdate SDK](https://play.date/dev/) installed and `PLAYDATE_SDK_PATH` set
- CMake on PATH
- GNU Arm Embedded Toolchain (`gcc-arm-none-eabi`) for device builds
- Compiler:
  - Linux/macOS: GCC or Clang + Make
  - Windows: Visual Studio 2019/2022 with C/C++ tools (NMake)

## Quick Start

```
/playdate-init MyGame
/playdate-build --run
```

Or just ask: "Create a Playdate game where the crank controls a paddle."

## Key Conventions Enforced by the Skill

- All allocation through `playdate->system->realloc` (no stdlib `malloc`/`free`)
- No dynamic allocation in the update loop - object pools instead
- 30 fps target for battery efficiency
- Sprite system over manual full-screen redraws
- NULL-check and free every loaded resource
- `SCREAMING_SNAKE_CASE` constants, `PascalCase` types, `snake_case` functions, `g_` globals

## Portability

The skill body is agent-portable (Claude Code and OpenAI Codex CLI) and works on
Windows, macOS, and Linux. The slash commands are Claude Code conveniences; the
skill describes the same workflows so any agent can follow them manually.

## Resources

- [Playdate SDK Documentation](https://sdk.play.date/)
- [Inside Playdate with C](https://sdk.play.date/inside-playdate-with-c/)
- [Playdate Developer Forum](https://devforum.play.date/)
