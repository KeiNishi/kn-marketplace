---
name: playdate-build
description: Build a Playdate project using make. Use this command when the user asks to "build", "compile", "make" a Playdate game, or when you need to build the .pdx bundle.
argument-hint: "[--device] [--clean] [--run]"
allowed-tools: Bash, Read, Glob
---

# Playdate Project Build

Build a Playdate C project using the SDK's build system.

## Instructions

When the user runs `/playdate-build` or when you need to build a Playdate project:

1. **Locate the project**:
   - Look for `Makefile` in the current directory or parent directories
   - Verify it's a Playdate project by checking for `common.mk` include or `pdxinfo`
   - If no Playdate project found, inform the user

2. **Parse arguments**:
   - `--device`: Build for Playdate device hardware
   - `--clean`: Run `make clean` before building
   - `--run`: Launch simulator after successful build

3. **Execute build**:

   **Standard simulator build**:
   ```bash
   make
   ```

   **Device build** (with `--device`):
   ```bash
   make DEVICE=1
   ```

   **Clean build** (with `--clean`):
   ```bash
   make clean && make
   ```

4. **Check build results**:
   - Look for the `.pdx` bundle in the `builds/` directory
   - Report any compilation errors clearly
   - Suggest fixes for common errors

5. **Run simulator** (if `--run` specified and build succeeded):
   ```bash
   "${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" builds/<GameName>.pdx
   ```
   On Windows:
   ```bash
   "${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator.exe" builds/<GameName>.pdx
   ```

## Common Build Errors

### SDK not found
```
Error: PLAYDATE_SDK_PATH not set
```
**Solution**: Set the environment variable:
```bash
# Linux/macOS
export PLAYDATE_SDK_PATH=/path/to/PlaydateSDK

# Windows (PowerShell)
$env:PLAYDATE_SDK_PATH = "C:\path\to\PlaydateSDK"
```

### Missing source files
```
Error: No rule to make target 'Source/xxx.c'
```
**Solution**: Check that all files listed in `SRC` variable in Makefile exist.

### Header not found
```
Error: pd_api.h: No such file or directory
```
**Solution**: Verify `PLAYDATE_SDK_PATH` is correctly set and contains `C_API/pd_api.h`.

### Undefined reference errors
```
Error: undefined reference to 'function_name'
```
**Solution**: Add the missing source file to `SRC` in Makefile or check function declarations.

## Build Output

On successful build:
- `.pdx` bundle created in `builds/` directory
- Report the path to the bundle
- Show file size information

On failed build:
- Display error messages clearly
- Identify the source file and line number
- Suggest potential fixes based on error type

## Notes

- Always run from the project root directory (where Makefile is located)
- Build artifacts go to `builds/` directory
- The `.pdx` bundle is what runs on the device/simulator
- Device builds produce ARM binaries, simulator builds produce native binaries
