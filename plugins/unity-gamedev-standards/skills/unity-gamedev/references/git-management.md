# Git Management

Git configuration and best practices for Unity projects.

## .gitignore

Standard Unity .gitignore:

```gitignore
# Unity generated
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
[Mm]emoryCaptures/
[Rr]ecordings/

# Asset meta data (shouldn't be ignored, but these specific ones)
*.pidb.meta
*.pdb.meta
*.mdb.meta

# Unity3D generated assemblies
Assembly-CSharp*.csproj
*.sln
*.suo
*.tmp
*.user
*.userprefs
*.pidb
*.booproj
*.svd
*.pdb
*.mdb
*.opendb
*.VC.db

# Builds
*.apk
*.aab
*.unitypackage
*.app

# Crashlytics
crashlytics-build.properties

# IDE
.idea/
.vs/
.vscode/
*.code-workspace

# OS
.DS_Store
Thumbs.db

# Rider
.idea/
*.DotSettings.user

# Visual Studio
*.csproj.user
*.unityproj
*.suo
*.tmp
*.user
*.userprefs
*.pidb
```

## Git LFS Configuration

### .gitattributes

Configure Git LFS for large binary files:

```gitattributes
# Images
*.png filter=lfs diff=lfs merge=lfs -text
*.jpg filter=lfs diff=lfs merge=lfs -text
*.jpeg filter=lfs diff=lfs merge=lfs -text
*.psd filter=lfs diff=lfs merge=lfs -text
*.tga filter=lfs diff=lfs merge=lfs -text
*.tif filter=lfs diff=lfs merge=lfs -text
*.tiff filter=lfs diff=lfs merge=lfs -text
*.exr filter=lfs diff=lfs merge=lfs -text
*.hdr filter=lfs diff=lfs merge=lfs -text

# Audio
*.wav filter=lfs diff=lfs merge=lfs -text
*.mp3 filter=lfs diff=lfs merge=lfs -text
*.ogg filter=lfs diff=lfs merge=lfs -text
*.aif filter=lfs diff=lfs merge=lfs -text
*.aiff filter=lfs diff=lfs merge=lfs -text

# Video
*.mp4 filter=lfs diff=lfs merge=lfs -text
*.mov filter=lfs diff=lfs merge=lfs -text
*.avi filter=lfs diff=lfs merge=lfs -text
*.webm filter=lfs diff=lfs merge=lfs -text

# 3D Models
*.fbx filter=lfs diff=lfs merge=lfs -text
*.obj filter=lfs diff=lfs merge=lfs -text
*.blend filter=lfs diff=lfs merge=lfs -text
*.max filter=lfs diff=lfs merge=lfs -text
*.ma filter=lfs diff=lfs merge=lfs -text
*.mb filter=lfs diff=lfs merge=lfs -text
*.dae filter=lfs diff=lfs merge=lfs -text

# Fonts
*.ttf filter=lfs diff=lfs merge=lfs -text
*.otf filter=lfs diff=lfs merge=lfs -text

# Unity specific
*.unitypackage filter=lfs diff=lfs merge=lfs -text
*.cubemap filter=lfs diff=lfs merge=lfs -text
*.asset filter=lfs diff=lfs merge=lfs -text

# Archives
*.zip filter=lfs diff=lfs merge=lfs -text
*.rar filter=lfs diff=lfs merge=lfs -text
*.7z filter=lfs diff=lfs merge=lfs -text

# Executables
*.dll filter=lfs diff=lfs merge=lfs -text
*.so filter=lfs diff=lfs merge=lfs -text
*.dylib filter=lfs diff=lfs merge=lfs -text

# Force text handling for Unity files
*.meta text eol=lf
*.unity text eol=lf
*.prefab text eol=lf
*.mat text eol=lf
*.anim text eol=lf
*.controller text eol=lf
*.overrideController text eol=lf
*.physicMaterial text eol=lf
*.physicsMaterial2D text eol=lf
*.playable text eol=lf
*.mask text eol=lf
*.brush text eol=lf
*.flare text eol=lf
*.fontsettings text eol=lf
*.guiskin text eol=lf
*.giparams text eol=lf
*.renderTexture text eol=lf
*.spriteatlas text eol=lf
*.terrainlayer text eol=lf
*.mixer text eol=lf
*.shadervariants text eol=lf
*.preset text eol=lf
*.signal text eol=lf
```

### Installing Git LFS

```bash
# Install Git LFS
git lfs install

# Initialize in repository
git lfs install --local

# Track specific file types
git lfs track "*.png"
git lfs track "*.fbx"

# Verify tracked patterns
git lfs track
```

## Unity Project Settings

### Asset Serialization

In Edit > Project Settings > Editor:
- **Asset Serialization**: Force Text
- **Version Control Mode**: Visible Meta Files

### .meta Files

- Always commit .meta files
- Never delete .meta files manually
- If Unity recreates a .meta file, something is wrong

## Branch Strategy

### Recommended Branch Structure

```
main (or master)
├── develop
│   ├── feature/player-movement
│   ├── feature/inventory-system
│   └── feature/ui-redesign
├── release/v1.0
└── hotfix/critical-bug
```

### Branch Naming

```
feature/  - New features
bugfix/   - Bug fixes
hotfix/   - Critical production fixes
release/  - Release preparation
chore/    - Maintenance tasks
```

## Commit Messages

### Format

```
<type>: <short description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation |
| style | Formatting (no code change) |
| refactor | Code refactoring |
| test | Adding tests |
| chore | Maintenance |
| perf | Performance improvement |

### Examples

```
feat: Add player double jump ability

fix: Resolve null reference in inventory system

refactor: Extract weapon logic to separate class

chore: Update Unity to 6.3.1
```

## Merge Conflicts

### Common Unity Conflicts

**.unity (Scene) files:**
- Coordinate with team
- Use prefabs to reduce conflicts
- Consider scene splitting

**.prefab files:**
- Keep prefabs small and focused
- Use prefab variants
- Avoid nested prefab modifications

**.meta files:**
- Usually safe to keep either version
- Be careful with GUID changes

### Resolution Tips

```bash
# Use Unity's YAML merge tool
# Add to .gitconfig:
[merge]
    tool = unityyamlmerge

[mergetool "unityyamlmerge"]
    trustExitCode = false
    cmd = '<Unity>/Editor/Data/Tools/UnityYAMLMerge.exe' merge -p "$BASE" "$REMOTE" "$LOCAL" "$MERGED"
```

## Best Practices

### Do's

- Commit .meta files with their assets
- Use Force Text serialization
- Use Git LFS for large binaries
- Make small, focused commits
- Write meaningful commit messages
- Pull before starting new work

### Don'ts

- Don't commit Library/ folder
- Don't ignore .meta files
- Don't commit untracked assets (check for missing .meta)
- Don't use binary serialization
- Don't make huge commits with many changes
- Don't commit broken/non-compiling code to main

## Pre-Commit Checklist

Before committing:

1. [ ] Project compiles without errors
2. [ ] No missing .meta files (check console)
3. [ ] Scene changes are intentional
4. [ ] No debug code left in
5. [ ] Meaningful commit message
6. [ ] Correct branch

## Repository Setup Commands

```bash
# Initialize new repo
git init
git lfs install

# Add Unity gitignore
curl -o .gitignore https://raw.githubusercontent.com/github/gitignore/main/Unity.gitignore

# Add LFS attributes
# (copy .gitattributes content above)

# Initial commit
git add .gitignore .gitattributes
git commit -m "chore: Initial repository setup"

# Add Unity project
git add .
git commit -m "feat: Initial Unity project"
```
