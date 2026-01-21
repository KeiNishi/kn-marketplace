---
name: playdate-init
description: Initialize a new Playdate C project by cloning the official template and configuring project name
argument-hint: "[project-name]"
allowed-tools: Bash, Write, Read, Glob, Edit
---

# Playdate Project Initialization

Initialize a new Playdate C project by cloning the official template repository.

## Template Repository

**Repository**: https://github.com/KeiNishi/kn-pd-template-c.git

This template includes:
- Pre-configured CMakeLists.txt for the official SDK build system
- VSCode tasks for one-click build (Ctrl+Shift+B)
- Starter source code templates
- Recommended directory structure
- .gitignore configuration

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

1. **Determine project name**:
   - If `[project-name]` is provided, use it
   - If not provided, ask the user for a project name
   - Validate the name (alphanumeric and underscores only recommended)

2. **Clone the template repository**:
   ```bash
   git clone https://github.com/KeiNishi/kn-pd-template-c.git ProjectName
   ```

3. **Remove .git directory to start fresh**:
   ```bash
   cd ProjectName
   rm -rf .git
   ```

4. **Update project name in files**:

   Replace the template name with the user's project name in the following files:

   ### Source/pdxinfo
   Update the following fields:
   - `name=ProjectName`
   - `bundleID=com.developer.projectname` (lowercase)

   ### CMakeLists.txt
   Update the game name variables:
   ```cmake
   set(PLAYDATE_GAME_NAME ProjectName)
   set(PLAYDATE_GAME_DEVICE ProjectName_DEVICE)
   ```

5. **Initialize new git repository** (optional, ask user):
   ```bash
   git init
   git add .
   git commit -m "Initial commit from kn-pd-template-c"
   ```

6. **Provide next steps**:

   ```
   ✓ Project "ProjectName" has been created!

   Next steps:
   1. Open the project folder in VSCode
   2. Press Ctrl+Shift+B to build
   3. Select "Playdate: Build Simulator" for simulator build
   4. The .pdx bundle will be created in the build directory

   To run in simulator:
   - Windows: "%PLAYDATE_SDK_PATH%\bin\PlaydateSimulator.exe" build/ProjectName.pdx
   - macOS/Linux: "${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" build/ProjectName.pdx
   ```

## Project Structure (Template)

After cloning, the project structure will be:

```
ProjectName/
├── .vscode/
│   └── tasks.json           # VSCode build tasks (Ctrl+Shift+B)
├── CMakeLists.txt           # Build configuration
├── Source/
│   ├── main.c               # Entry point with eventHandler
│   ├── game.h               # Game header
│   ├── game.c               # Game loop implementation
│   └── pdxinfo              # Game metadata
├── assets/
│   ├── images/
│   ├── sounds/
│   └── fonts/
└── .gitignore
```

## Files to Update After Clone

### Source/pdxinfo
```ini
name=ProjectName
author=Developer
description=A Playdate Game
bundleID=com.developer.projectname
version=1.0
buildNumber=1
```

### CMakeLists.txt (Game Name Section)
```cmake
# Game Name Customization
set(PLAYDATE_GAME_NAME ProjectName)
set(PLAYDATE_GAME_DEVICE ProjectName_DEVICE)
```

## Important Notes

- Always update both `pdxinfo` and `CMakeLists.txt` with the new project name
- The `bundleID` should be lowercase and use reverse domain notation
- VSCode tasks are pre-configured - use Ctrl+Shift+B to build
- The template targets 30 FPS by default (recommended for battery life)
- All source files go in the `Source/` directory
- Assets are placed in `assets/` subdirectories
- For more examples, refer to `$PLAYDATE_SDK_PATH/C_API/Examples/`
