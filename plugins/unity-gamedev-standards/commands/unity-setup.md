---
name: unity-setup
description: Check Unity project structure against recommended standards and provide improvement suggestions
argument-hint: "[path-to-assets-folder]"
allowed-tools: Bash, Read, Glob, Grep
---

# Unity Project Structure Check

Analyze the current Unity project structure and provide recommendations based on unity-gamedev-standards best practices.

## Instructions

When the user runs `/unity-setup`:

1. **Locate the Unity project**:
   - If path argument provided, use it
   - Otherwise, look for Assets/ folder in current directory or parent directories
   - Verify it's a Unity project (has Assets/ folder)

2. **Check folder structure**:
   - Look for `Assets/_Project/` (recommended)
   - Check for proper subdirectories:
     - `Scripts/` (with Core/, Gameplay/, UI/, Utilities/)
     - `Art/` (with Animations/, Materials/, Models/, Sprites/)
     - `Audio/` (with Music/, SFX/)
     - `Prefabs/`
     - `Scenes/`
     - `ScriptableObjects/`
   - Check for `Editor/` folder (should exist if custom editors needed)

3. **Check for common issues**:
   - Scripts outside organized structure
   - Missing .meta files (warn about potential issues)
   - Large files that should be in Git LFS
   - Resources/ folder usage (recommend Addressables)

4. **Check coding conventions** (sample a few .cs files):
   - Namespace usage
   - Naming conventions (PascalCase classes, _camelCase fields)
   - [Tooltip] attribute usage on SerializeField
   - [Header] grouping

5. **Generate report**:
   - Current structure summary
   - Recommendations for improvements
   - Priority of changes (critical, recommended, nice-to-have)

6. **Offer to help**:
   - Ask if user wants to create missing folders
   - Suggest next steps

## Analysis Checks

### Folder Structure

```
✓ Assets/_Project/ exists
✗ Missing Assets/_Project/Scripts/Core/
✗ Missing Assets/_Project/ScriptableObjects/
```

### Asset Naming

```
✓ Prefabs use PFB_ prefix
✗ Found materials without MAT_ prefix: Ground.mat
```

### Code Quality

```
✓ Namespaces used consistently
✗ Missing [Tooltip] on 15 SerializeField properties
```

## Report Format

```
=== Unity Project Structure Report ===

Project: [Project Name]
Unity Version: [if detectable from ProjectSettings]

## Current Structure

[tree-like view of Assets/ folder]

## Issues Found

### Critical
- [issues that may cause problems]

### Recommended
- [improvements for better organization]

### Nice to Have
- [minor suggestions]

## Recommendations

1. Create missing folders:
   - Assets/_Project/Scripts/Core/
   - Assets/_Project/ScriptableObjects/

2. Rename assets to follow conventions:
   - Ground.mat → MAT_Ground.mat

3. Add [Tooltip] attributes to:
   - PlayerController._moveSpeed
   - EnemyAI._detectionRange

## Next Steps

Would you like me to:
[ ] Create the recommended folder structure
[ ] Show the full unity-gamedev-standards skill
[ ] Review specific scripts for coding standards
```

## Important Notes

- This command is read-only by default (only analyzes)
- Will not make changes without explicit user confirmation
- Focus on actionable, prioritized recommendations
- Reference the unity-gamedev skill for detailed standards
