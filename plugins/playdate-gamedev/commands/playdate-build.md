---
name: playdate-build
description: Build a Playdate project using VSCode tasks. Use this command when the user asks to "build", "compile", "make" a Playdate game, or when you need to build the .pdx bundle.
argument-hint: "[--device] [--clean] [--run]"
allowed-tools: Bash, Read, Glob
---

# Playdate Project Build

Build a Playdate C project using VSCode's integrated build tasks.

## Prerequisites

Before building, ensure the following tools are installed:

### Windows
1. **Visual Studio 2019 or 2022** with C/C++ tools
2. **GNU Arm Embedded Toolchain** (`gcc-arm-none-eabi`) - Download from developer.arm.com and add to PATH
3. **CMake** - Download from cmake.org and add to PATH

### Linux/macOS
1. **GCC or Clang** compiler
2. **GNU Arm Embedded Toolchain** (`gcc-arm-none-eabi`)
3. **CMake**
4. **Make**

### Environment Variable
Set `PLAYDATE_SDK_PATH` to your SDK installation directory.

## Instructions

When the user runs `/playdate-build` or when you need to build a Playdate project:

1. **Detect and locate project**:
   - Look for `CMakeLists.txt` in the current directory or parent directories
   - Verify it's a Playdate project by checking for Playdate SDK references or `pdxinfo`
   - Verify `.vscode/tasks.json` exists for VSCode build tasks
   - If no Playdate project found, inform the user

2. **Parse arguments**:
   - `--device`: Build for Playdate device hardware (ARM)
   - `--clean`: Remove build directory before building
   - `--run`: Launch simulator after successful build

3. **Execute build using VSCode tasks**:

   ### Recommended Method: VSCode Build Tasks

   The template project includes pre-configured VSCode tasks. Users can build directly from VSCode:

   1. Open the project in VSCode
   2. Press **Ctrl+Shift+B** (or Cmd+Shift+B on macOS)
   3. Select the appropriate build task:
      - **Playdate: Build Simulator** - Build for simulator (default)
      - **Playdate: Build Device** - Build for Playdate hardware
      - **Playdate: Clean Build** - Remove build directory and rebuild
      - **Playdate: Run Simulator** - Build and launch simulator

   ### Build Task Execution

   If the user wants to trigger the build programmatically or from command line:

   **For Simulator build**:
   The VSCode task runs the equivalent of:
   ```bash
   # Windows (from x64 Native Tools Command Prompt)
   mkdir build 2>nul
   cd build
   cmake .. -G "NMake Makefiles"
   nmake

   # Linux/macOS
   mkdir -p build
   cd build
   cmake ..
   make
   ```

   **For Device build** (with `--device`):
   ```bash
   # Windows
   cmake .. -G "NMake Makefiles" --toolchain="%PLAYDATE_SDK_PATH%/C_API/buildsupport/arm.cmake"
   nmake

   # Linux/macOS
   cmake .. --toolchain="${PLAYDATE_SDK_PATH}/C_API/buildsupport/arm.cmake"
   make
   ```

4. **Check build results**:
   - Look for the `.pdx` bundle in the build output directory
   - Report any compilation errors clearly
   - Suggest fixes for common errors

5. **Run simulator** (if `--run` specified and build succeeded):

   **Windows**:
   ```bash
   "%PLAYDATE_SDK_PATH%\bin\PlaydateSimulator.exe" build/<GameName>.pdx
   ```

   **Linux/macOS**:
   ```bash
   "${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" build/<GameName>.pdx
   ```

## VSCode Tasks Configuration

The template includes `.vscode/tasks.json` with the following tasks:

| Task Name | Description | Shortcut |
|-----------|-------------|----------|
| Playdate: Build Simulator | Build for simulator | Ctrl+Shift+B → Select |
| Playdate: Build Device | Build for hardware | Ctrl+Shift+B → Select |
| Playdate: Clean Build | Clean and rebuild | Ctrl+Shift+B → Select |
| Playdate: Run Simulator | Build and run | Ctrl+Shift+B → Select |

## Common Build Errors

### SDK not found
```
Error: PLAYDATE_SDK_PATH not set
```
**Solution**: Set the environment variable:

**Windows (System Environment Variables)**:
1. Search "environment variables" in Start menu
2. Open System Properties panel
3. Click "Environment Variables" button
4. Create new variable `PLAYDATE_SDK_PATH` pointing to SDK directory

**Windows (PowerShell - temporary)**:
```powershell
$env:PLAYDATE_SDK_PATH = "C:\Users\<Username>\Documents\PlaydateSDK"
```

**Linux/macOS**:
```bash
export PLAYDATE_SDK_PATH=/path/to/PlaydateSDK
```

### CMake not found
```
Error: 'cmake' is not recognized as an internal or external command
```
**Solution**:
- Download CMake from https://cmake.org/download/
- During installation, select "Add CMake to the system PATH"
- Or manually add CMake's bin directory to PATH

### NMake not found (Windows)
```
Error: 'nmake' is not recognized as an internal or external command
```
**Solution**:
- The VSCode tasks are configured to use the Visual Studio environment
- Ensure Visual Studio 2019/2022 with C++ tools is installed
- If running manually, use **"x64 Native Tools Command Prompt for VS 2019/2022"**

### ARM toolchain not found (Device build)
```
Error: arm-none-eabi-gcc not found
```
**Solution**:
- Download GNU Arm Embedded Toolchain from https://developer.arm.com/downloads/-/gnu-rm
- Add the toolchain's `bin` directory to your PATH

### Header not found
```
Error: pd_api.h: No such file or directory
```
**Solution**: Verify `PLAYDATE_SDK_PATH` is correctly set and contains `C_API/pd_api.h`.

### Undefined reference errors
```
Error: undefined reference to 'function_name'
```
**Solution**: Ensure all source files are listed in `CMakeLists.txt` and function declarations match definitions.

## Build Output

On successful build:
- `.pdx` bundle created in the `build/` directory
- Report the path to the bundle
- Show file size information

On failed build:
- Display error messages clearly
- Identify the source file and line number
- Suggest potential fixes based on error type

## Notes

- **VSCode tasks are the recommended build method** - use Ctrl+Shift+B
- The `build/` directory contains all build artifacts and can be safely deleted for a clean build
- The `.pdx` bundle is what runs on the device/simulator
- Device builds produce ARM binaries, simulator builds produce native (x64) binaries
- On Windows, the Playdate SDK typically installs to `C:\Users\<Username>\Documents\PlaydateSDK`
- Optionally add `<SDK_PATH>/bin` to PATH for easy access to `pdc`, `pdutil`, and the simulator
