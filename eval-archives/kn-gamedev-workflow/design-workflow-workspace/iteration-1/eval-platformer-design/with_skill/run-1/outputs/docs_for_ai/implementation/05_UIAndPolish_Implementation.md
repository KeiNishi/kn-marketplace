> Part of [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

# UI and Polish Implementation: Purrfect Run

## Architecture

### HUDController
```
Purpose: In-game HUD showing fish score and current level name

Properties:
- _scoreText: TMP_Text - displays current score
- _levelNameText: TMP_Text - displays level name

Methods:
- Awake(): void - subscribe to ScoreManager.OnScoreChanged
- OnDisable(): void - unsubscribe from ScoreManager.OnScoreChanged
- UpdateScore(int score): void - update _scoreText
```

### LevelCompletePanel
```
Purpose: Displayed on level complete; shows star rating and navigation buttons

Properties:
- _starImages: Image[3] - star icons (filled vs empty)
- _nextLevelButton: Button
- _replayButton: Button
- _menuButton: Button

Methods:
- Show(int starCount): void - activate panel, fill stars, configure buttons
- OnNextLevel(): void - call SceneLoader.LoadNextLevel()
- OnReplay(): void - call SceneLoader.ReloadCurrentScene()
- OnMenu(): void - call SceneLoader.LoadScene("SCN_MainMenu")
```

### LevelSelectController
```
Purpose: Level selection screen; reads save data to show locked/unlocked state and stars

Properties:
- _levelButtons: LevelButton[] - array of per-level button components

Methods:
- Start(): void - read SaveManager; configure each LevelButton
```

### LevelButton
```
Purpose: Single level entry on level select screen

Properties:
- _levelIndex: int - assigned in Inspector
- _lockIcon: GameObject
- _starImages: Image[3]
- _button: Button

Methods:
- Configure(bool isUnlocked, int stars): void - show/hide lock; fill star images
```

### AudioManager
```
Purpose: Singleton; manages BGM and SFX playback

Properties:
- _bgmSource: AudioSource - looping music source
- _sfxSource: AudioSource - one-shot SFX source

Methods:
- Awake(): void - register singleton, DontDestroyOnLoad
- PlayBGM(AudioClip clip): void - fade old BGM, play new
- PlaySFX(AudioClip clip): void - _sfxSource.PlayOneShot()
- StopBGM(): void - stop background music
```

### SaveManager
```
Purpose: Singleton; persist level unlock state and star ratings using PlayerPrefs

Methods:
- Awake(): void - register singleton
- SaveStars(int levelIndex, int stars): void - store with PlayerPrefs
- LoadStars(int levelIndex): int - return saved stars (0 if not set)
- IsLevelUnlocked(int levelIndex): bool - level 1 always true; others require previous completed
- UnlockNextLevel(int currentLevelIndex): void - set unlock flag for currentLevelIndex + 1
```

## Tasks

### Phase 5: UI and Polish (Priority: Medium)

**Goal**: Full UI flow from main menu to level select to gameplay HUD to level complete screen

- [ ] Implement `HUDController.cs` with score display; subscribe to ScoreManager events
- [ ] Implement `LevelCompletePanel.cs` with star display and navigation buttons
- [ ] Implement `LevelSelectController.cs` and `LevelButton.cs`
- [ ] Implement `AudioManager.cs` singleton with BGM/SFX methods; assign per-level BGM in LevelManager
- [ ] Implement `SaveManager.cs` using PlayerPrefs
- [ ] Wire `LevelManager.OnLevelComplete` to `LevelCompletePanel.Show()`
- [ ] Wire `SaveManager` calls to `LevelManager.OnGoalReached()` flow
- [ ] Create `SCN_MainMenu.unity` with Play button leading to level select
- [ ] Create touch button UI prefabs for `TouchInputHandler` (left, right, jump)
- [ ] Add screen shake on dog contact (camera shake coroutine in `CameraFollow`)
- [ ] Add particle effects for fish collection (use `FishData.CollectEffect`)

**Deliverables**:
- Full game loop: menu → level select → gameplay → level complete → menu/next; save/load works across sessions

## Asset Requirements

### Graphics

| Asset | Format | Dimensions | Priority |
|-------|--------|------------|----------|
| SPR_Star_Full | PNG | [EXAMPLE: 64x64] | P1 |
| SPR_Star_Empty | PNG | [EXAMPLE: 64x64] | P1 |
| SPR_Lock_Icon | PNG | [EXAMPLE: 48x48] | P1 |
| SPR_Button_Left | PNG | [EXAMPLE: 128x128] | P1 |
| SPR_Button_Right | PNG | [EXAMPLE: 128x128] | P1 |
| SPR_Button_Jump | PNG | [EXAMPLE: 128x128] | P1 |
| SPR_UI_Panel_BG | PNG | [EXAMPLE: 512x256] | P2 |

### Audio

| Asset | Type | Format | Priority |
|-------|------|--------|----------|
| BGM_MainMenu | BGM | MP3 | P2 |
| SFX_ButtonClick | SFX | WAV | P2 |
| SFX_StarEarned | SFX | WAV | P2 |

## Dependencies
- **Design**: [04_LevelContent_Design.md](../game_design/04_LevelContent_Design.md) - Level names and unlock sequence
- **Related Implementation**: [02_Collectibles_Implementation.md](./02_Collectibles_Implementation.md) - ScoreManager.OnScoreChanged feeds HUD
- **Related Implementation**: [04_LevelContent_Implementation.md](./04_LevelContent_Implementation.md) - LevelManager.OnLevelComplete triggers LevelCompletePanel; SceneLoader used by all UI navigation
