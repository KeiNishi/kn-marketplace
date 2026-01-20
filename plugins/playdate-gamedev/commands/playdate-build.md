---
name: playdate-build
description: Build a Playdate project using CMake and NMake. Use this command when the user asks to "build", "compile", "make" a Playdate game, or when you need to build the .pdx bundle.
argument-hint: "[--device] [--clean] [--run]"
allowed-tools: Bash, Read, Glob
---

# Playdate Project Build

Build a Playdate C project using the SDK's official CMake build system.

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

1. **Detect platform and locate project**:
   - Determine if running on Windows or Unix (Linux/macOS)
   - Look for `CMakeLists.txt` in the current directory or parent directories
   - Verify it's a Playdate project by checking for Playdate SDK references or `pdxinfo`
   - If no Playdate project found, inform the user

2. **Parse arguments**:
   - `--device`: Build for Playdate device hardware (ARM)
   - `--clean`: Remove build directory before building
   - `--run`: Launch simulator after successful build

3. **Execute build**:

   ### Windows

   **IMPORTANT**: On Windows, you MUST use the **"x64 Native Tools Command Prompt for VS 2019/2022"** for building. This is required for 64-bit simulator builds.

   **Setup build directory** (first time only):
   ```bash
   mkdir build
   cd build
   ```

   **Simulator build** (default):
   ```bash
   cmake .. -G "NMake Makefiles"
   nmake
   ```

   **Device build** (with `--device`):
   ```bash
   cmake .. -G "NMake Makefiles" --toolchain="%PLAYDATE_SDK_PATH%/C_API/buildsupport/arm.cmake"
   nmake
   ```

   **Release build** (optimized):
   ```bash
   cmake .. -G "NMake Makefiles" -DCMAKE_BUILD_TYPE=Release
   nmake
   ```

   **Clean build** (with `--clean`):
   ```bash
   rd /s /q build
   mkdir build
   cd build
   cmake .. -G "NMake Makefiles"
   nmake
   ```

   ### Unix (Linux/macOS)

   **Setup build directory** (first time only):
   ```bash
   mkdir build
   cd build
   ```

   **Simulator build** (default):
   ```bash
   cmake ..
   make
   ```

   **Device build** (with `--device`):
   ```bash
   cmake .. --toolchain="${PLAYDATE_SDK_PATH}/C_API/buildsupport/arm.cmake"
   make
   ```

   **Release build** (optimized):
   ```bash
   cmake .. -DCMAKE_BUILD_TYPE=Release
   make
   ```

   **Clean build** (with `--clean`):
   ```bash
   rm -rf build
   mkdir build
   cd build
   cmake ..
   make
   ```

4. **Check build results**:
   - Look for the `.pdx` bundle in the build output directory
   - Report any compilation errors clearly
   - Suggest fixes for common errors

5. **Run simulator** (if `--run` specified and build succeeded):

   **Windows**:
   ```bash
   "%PLAYDATE_SDK_PATH%\bin\PlaydateSimulator.exe" <GameName>.pdx
   ```

   **Unix (Linux/macOS)**:
   ```bash
   "${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" <GameName>.pdx
   ```

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
- You must run commands from **"x64 Native Tools Command Prompt for VS 2019/2022"**
- Find it in Start Menu under Visual Studio folder
- Do NOT use regular Command Prompt or PowerShell

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

### Generator not available
```
Error: CMake Error: Could not create named generator NMake Makefiles
```
**Solution**:
- On Windows, ensure you're using the Visual Studio developer command prompt
- Check that Visual Studio C++ tools are installed

## Build Output

On successful build:
- `.pdx` bundle created in the build directory
- Report the path to the bundle
- Show file size information

On failed build:
- Display error messages clearly
- Identify the source file and line number
- Suggest potential fixes based on error type

## Notes

- On Windows, always use **"x64 Native Tools Command Prompt for VS 2019/2022"**
- The `build` directory contains all build artifacts and can be safely deleted for a clean build
- The `.pdx` bundle is what runs on the device/simulator
- Device builds produce ARM binaries, simulator builds produce native (x64) binaries
- On Windows, the Playdate SDK typically installs to `C:\Users\<Username>\Documents\PlaydateSDK`
- Optionally add `<SDK_PATH>/bin` to PATH for easy access to `pdc`, `pdutil`, and the simulator
