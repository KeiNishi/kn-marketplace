# Project Structure

Detailed folder organization and asset naming conventions for Unity projects.

## Folder Structure

```
Assets/
├── _Project/                 # Project-specific (underscore = top of list)
│   ├── Art/
│   │   ├── Animations/       # Animation clips and controllers
│   │   ├── Materials/        # Materials and shaders
│   │   ├── Models/           # 3D models
│   │   ├── Sprites/          # 2D sprites and atlases
│   │   └── UI/               # UI sprites and assets
│   ├── Audio/
│   │   ├── Music/            # Background music
│   │   └── SFX/              # Sound effects
│   ├── Prefabs/
│   │   ├── Characters/       # Character prefabs
│   │   ├── Environment/      # Environment prefabs
│   │   └── UI/               # UI prefabs
│   ├── Scenes/
│   │   ├── _Init/            # Initialization scenes
│   │   ├── Levels/           # Game levels
│   │   └── UI/               # UI-only scenes
│   ├── ScriptableObjects/
│   │   ├── Configs/          # Configuration assets
│   │   └── Data/             # Game data assets
│   ├── Scripts/
│   │   ├── Core/             # Core game systems
│   │   ├── Gameplay/         # Gameplay logic
│   │   ├── UI/               # UI controllers
│   │   └── Utilities/        # Helper utilities
│   └── Settings/             # Project settings
├── Plugins/                  # Third-party plugins
├── Resources/                # Runtime-loadable assets (use sparingly)
├── StreamingAssets/          # Files to copy as-is to build
└── Editor/                   # Editor-only scripts
    └── _Project/             # Project-specific editor scripts
```

## Asset Naming Conventions

### Prefixes by Type

| Type | Prefix | Example |
|------|--------|---------|
| Prefab | `PFB_` | `PFB_Player.prefab` |
| Material | `MAT_` | `MAT_Ground.mat` |
| Texture | `TEX_` | `TEX_Player_Diffuse.png` |
| Animation Clip | `ANIM_` | `ANIM_Player_Run.anim` |
| Animator Controller | `AC_` | `AC_Player.controller` |
| ScriptableObject | `SO_` | `SO_WeaponData.asset` |
| Scene | `SCN_` | `SCN_Level01.unity` |
| Audio Clip | `SFX_` / `BGM_` | `SFX_Jump.wav`, `BGM_MainTheme.mp3` |
| Sprite | `SPR_` | `SPR_Icon_Health.png` |
| Font | `FNT_` | `FNT_MainUI.ttf` |

### Texture Suffixes

| Purpose | Suffix | Example |
|---------|--------|---------|
| Diffuse/Albedo | `_Diffuse` | `TEX_Character_Diffuse.png` |
| Normal | `_Normal` | `TEX_Character_Normal.png` |
| Metallic | `_Metallic` | `TEX_Character_Metallic.png` |
| Roughness | `_Roughness` | `TEX_Character_Roughness.png` |
| Ambient Occlusion | `_AO` | `TEX_Character_AO.png` |
| Height/Displacement | `_Height` | `TEX_Character_Height.png` |
| Emission | `_Emission` | `TEX_Character_Emission.png` |

### Animation Naming

```
ANIM_{Character}_{Action}_{Variant}
```

Examples:
- `ANIM_Player_Idle.anim`
- `ANIM_Player_Run.anim`
- `ANIM_Player_Attack_Combo1.anim`
- `ANIM_Enemy_Death_Explosion.anim`

## Script Organization

### Namespace Structure

```csharp
namespace YourGame.Core { }
namespace YourGame.Gameplay { }
namespace YourGame.UI { }
namespace YourGame.Utilities { }
```

### Script Categories

**Core/** - Fundamental systems
- GameManager.cs
- AudioManager.cs
- SaveLoadManager.cs
- SceneLoader.cs

**Gameplay/** - Game mechanics
- PlayerController.cs
- EnemyAI.cs
- WeaponSystem.cs
- InventorySystem.cs

**UI/** - User interface
- MainMenuController.cs
- HUDController.cs
- SettingsPanel.cs
- DialogueUI.cs

**Utilities/** - Helper classes
- ObjectPool.cs
- Timer.cs
- MathUtils.cs
- Extensions.cs

## Assembly Definitions

Create Assembly Definition files for better compilation:

```
Scripts/
├── Core/
│   └── YourGame.Core.asmdef
├── Gameplay/
│   └── YourGame.Gameplay.asmdef
├── UI/
│   └── YourGame.UI.asmdef
└── Utilities/
    └── YourGame.Utilities.asmdef
```

Example `.asmdef`:
```json
{
    "name": "YourGame.Gameplay",
    "rootNamespace": "YourGame.Gameplay",
    "references": [
        "YourGame.Core",
        "YourGame.Utilities"
    ],
    "autoReferenced": true
}
```

## Special Folders

### Resources/
- Assets loadable at runtime via `Resources.Load()`
- Use sparingly - increases build size
- Better alternative: Addressables

### StreamingAssets/
- Files copied as-is to build
- Use for: JSON configs, video files, custom data

### Editor/
- Scripts only used in Unity Editor
- Not included in builds
- CustomEditors, PropertyDrawers, EditorWindows

### Plugins/
- Third-party assets and plugins
- Native plugins (.dll, .so, .dylib)
- Keep separate from project code
