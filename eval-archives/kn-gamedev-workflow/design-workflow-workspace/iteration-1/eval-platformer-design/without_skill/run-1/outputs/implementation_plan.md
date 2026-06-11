# Cat & Fish: Unity Implementation Plan

**Version:** 1.0
**Date:** 2026-02-28
**Engine:** Unity 2022 LTS
**Platform:** iOS & Android (Mobile)

---

## 1. Technology Stack

| Category | Technology |
|----------|------------|
| Engine | Unity 2022.3 LTS |
| Language | C# |
| Rendering | Universal Render Pipeline (URP) 2D |
| Physics | Unity 2D Physics (Rigidbody2D + Collider2D) |
| Animation | Unity Animator (Sprite-based) |
| Audio | Unity Audio Mixer |
| Input | Unity Input System (New Input System package) |
| UI | Unity UI Toolkit or uGUI |
| Version Control | Git + GitHub/GitLab |
| CI/CD | Unity Cloud Build (or GitHub Actions) |

---

## 2. Project Structure

```
Assets/
  _Project/
    Scripts/
      Player/
        PlayerController.cs
        PlayerAnimator.cs
        PlayerHealth.cs
      Enemies/
        DogBase.cs
        PoodlePatrol.cs
        BulldogChase.cs
        TerrierJumper.cs
        SheepdogBoss.cs
      Collectibles/
        Fish.cs
        FishMagnet.cs
        FishSpawner.cs
      Level/
        LevelManager.cs
        Checkpoint.cs
        LevelExit.cs
        MovingPlatform.cs
      UI/
        HUDController.cs
        PauseMenu.cs
        LevelSelectUI.cs
        GameOverUI.cs
        LevelCompleteUI.cs
      GameManagement/
        GameManager.cs
        ScoreManager.cs
        SaveSystem.cs
        AudioManager.cs
        InputManager.cs
    Prefabs/
      Player/
      Enemies/
      Collectibles/
      UI/
      Level/
    Scenes/
      MainMenu.unity
      LevelSelect.unity
      Level_01.unity
      Level_02.unity
      Level_03.unity
      Level_04.unity
      Level_05.unity
      GameOver.unity
    Art/
      Sprites/
        Player/
        Enemies/
        Collectibles/
        Environment/
        UI/
      Animations/
      Tilemaps/
    Audio/
      Music/
      SFX/
    Tilemaps/
      Level01_Tileset/
      ...
    ScriptableObjects/
      FishData/
      EnemyData/
      LevelData/
```

---

## 3. Core Systems Implementation

### 3.1 Player Controller (`PlayerController.cs`)

**Responsibilities:**
- Horizontal movement (left/right)
- Jump (variable height, double jump)
- Wall slide and wall jump
- Ground and wall detection via raycasts or overlap checks
- Coyote time and jump buffering

**Key Implementation Notes:**

```csharp
// Coyote time implementation sketch
private float coyoteTimeCounter;
private float jumpBufferCounter;

void Update()
{
    // Coyote time: allow jump briefly after leaving ground
    if (IsGrounded()) coyoteTimeCounter = coyoteTime;
    else coyoteTimeCounter -= Time.deltaTime;

    // Jump buffer: queue jump input
    if (Input.JumpPressed) jumpBufferCounter = jumpBufferTime;
    else jumpBufferCounter -= Time.deltaTime;

    if (jumpBufferCounter > 0 && coyoteTimeCounter > 0)
    {
        PerformJump();
        jumpBufferCounter = 0;
    }
}
```

**Ground Detection:**
- Use `Physics2D.BoxCast` downward from player feet
- Layer mask for "Ground" layer
- Small skin width to avoid false positives

**Wall Detection:**
- `Physics2D.BoxCast` left and right from player body
- Wall slide activates when pressing into wall while airborne

### 3.2 Enemy System

**Class Hierarchy:**
```
DogBase (MonoBehaviour)
  ├── PoodlePatrol
  ├── BulldogChase
  ├── TerrierJumper
  └── SheepdogBoss
```

**DogBase responsibilities:**
- Alert state machine (Idle → Alert → Chase → Return)
- Player detection radius check (using `Physics2D.OverlapCircle`)
- On-touch player damage event
- Abstract `UpdateBehavior()` method for subclasses

**State Machine Pattern:**
```csharp
public enum DogState { Patrol, Alert, Chase, Return }

protected DogState currentState;

void Update()
{
    switch (currentState)
    {
        case DogState.Patrol: Patrol(); break;
        case DogState.Alert: Alert(); break;
        case DogState.Chase: Chase(); break;
        case DogState.Return: ReturnToStart(); break;
    }
    DetectPlayer();
}
```

**PoodlePatrol specifics:**
- Moves between two patrol points (serialized in Inspector)
- Flips sprite direction at each point
- Never leaves platform (edge detection raycast)

**BulldogChase specifics:**
- Stationary until player enters radius
- Charges in straight line (no pathfinding needed)
- Stops at platform edge (downward raycast check)

**TerrierJumper specifics:**
- Simple patrol + jump logic
- Uses Rigidbody2D.AddForce for jumps
- Navigates between predefined waypoints

**SheepdogBoss specifics:**
- Phase-based behavior (timed phases, not HP-based)
- Bone projectile: instantiate `BonePrefab`, apply velocity toward player position at fire time
- 30-second endurance timer triggers level exit unlock

### 3.3 Fish Collectible System

**Fish.cs:**
- ScriptableObject data reference (`FishData`: type, points, sprite)
- `OnTriggerEnter2D` detection with player layer
- Trigger `ScoreManager.AddScore(points)`
- Trigger `LevelManager.OnFishCollected()`
- Play collect animation (tween scale to 0, then destroy)
- Play SFX via AudioManager

**FishMagnet.cs (power-up):**
- OnPickup: Start coroutine for 5-second duration
- During duration: Find all Fish in radius, move them toward player with `Vector2.MoveTowards`
- OnExpiry: Remove magnet effect

**LevelManager fish tracking:**
```csharp
private int totalFish;
private int collectedFish;
private int requiredFish;

public void OnFishCollected()
{
    collectedFish++;
    HUDController.UpdateFishCount(collectedFish, requiredFish);
    if (collectedFish >= requiredFish) EnableLevelExit();
}
```

### 3.4 Level Manager (`LevelManager.cs`)

**Responsibilities:**
- Initialize level (fish count, required quota)
- Manage checkpoints
- Track level state (playing, paused, complete, failed)
- Handle player death → respawn at last checkpoint
- Handle level complete → show summary screen
- Calculate star rating

**Checkpoint system:**
```csharp
// Checkpoint.cs
void OnTriggerEnter2D(Collider2D other)
{
    if (other.CompareTag("Player"))
    {
        LevelManager.Instance.SetCheckpoint(this.transform.position);
        // Visual: animate checkpoint flag raising
    }
}
```

**Star Rating Calculation:**
```csharp
int CalculateStars(int collected, int total, float completionTime, float targetTime)
{
    if (collected == total && completionTime <= targetTime) return 3;
    if ((float)collected / total >= 0.75f) return 2;
    return 1; // Minimum: completed level at all
}
```

### 3.5 Input System (Mobile)

**Approach:** Unity's New Input System with on-screen UI buttons

**InputManager.cs:**
- Reads from virtual buttons mapped to Input Actions
- Exposes: `MoveInput (float -1 to 1)`, `JumpPressed (bool)`, `JumpHeld (bool)`

**On-Screen Controls:**
- Left area: Two buttons (Left arrow, Right arrow) using `OnScreenButton` or custom UI
- Right area: Large Jump button
- All buttons semi-transparent to minimize screen obstruction
- Touch areas sized 80px+ for comfortable thumb use

**Alternative input for testing:**
- Keyboard WASD / Arrow keys + Space for editor testing
- Handled automatically by Input System action bindings

### 3.6 Save System (`SaveSystem.cs`)

**Save Data Structure:**
```csharp
[Serializable]
public class SaveData
{
    public int highestUnlockedLevel;
    public int[] levelStars; // index 0-4 for levels 1-5
    public int[] levelHighScores;
}
```

**Storage:** `PlayerPrefs` with JSON serialization (via `JsonUtility`)
- Simple, sufficient for this scope
- Alternative for larger scope: `Application.persistentDataPath` + file write

**Save triggers:**
- On level complete
- On returning to main menu
- Auto-save every 60 seconds during play

### 3.7 Audio Manager (`AudioManager.cs`)

**Singleton pattern**

**Features:**
- Play/stop music tracks with fade transitions (Coroutine + AudioSource volume lerp)
- Play one-shot SFX
- Global volume controls (Music volume, SFX volume) persisted in PlayerPrefs
- Supports 2D audio (mobile game, no spatial audio needed)

---

## 4. Scene Setup

### 4.1 Each Level Scene Contains:
- Tilemap GameObjects (Background, Ground, Foreground layers)
- Player spawn point (empty GameObject with tag "SpawnPoint")
- Camera: Cinemachine Virtual Camera following player with horizontal dampening
- Fish prefab instances placed via Scene editor
- Enemy prefab instances with patrol points configured
- Checkpoint triggers
- Level exit trigger
- UI Canvas (HUD overlay)
- Audio Source for level music

### 4.2 Camera Setup (Cinemachine)
- Follow target: Player transform
- Confiner 2D: Set to level bounding box collider
- Horizontal deadzone: small (player can move slightly before camera follows)
- Vertical follow: lookahead enabled (camera peeks in movement direction)
- Orthographic size: tuned per level (e.g., 6-7 units for mobile aspect ratios)

### 4.3 Tilemap Layers
| Layer | Z-Order | Purpose |
|-------|---------|---------|
| Background | -2 | Non-interactive scenery |
| Background Detail | -1 | Parallax elements |
| Ground | 0 | Interactive platforms (has TilemapCollider2D) |
| Foreground | 1 | In-front-of-player decorative elements |

---

## 5. Development Milestones

### Phase 1: Prototype (Week 1-2)
- [ ] Unity project setup, URP 2D configured
- [ ] Basic PlayerController (run, jump, ground detection)
- [ ] Placeholder sprites (colored rectangles)
- [ ] One flat test scene
- [ ] Collectible pickup trigger
- [ ] Basic enemy patrol behavior

**Milestone Criteria:** Cat can move, jump, collect items, and be "caught" by a patrolling rectangle enemy.

### Phase 2: Core Systems (Week 3-4)
- [ ] All player movement mechanics (double jump, wall slide, wall jump)
- [ ] All dog enemy types implemented
- [ ] Fish variety with ScriptableObjects
- [ ] LevelManager: fish quota, win/fail state
- [ ] Checkpoint system
- [ ] SaveSystem (PlayerPrefs)
- [ ] Input System: virtual mobile buttons working
- [ ] HUD: fish count, score display

**Milestone Criteria:** Full gameplay loop playable with placeholder art. Mobile touch controls functional.

### Phase 3: Content (Week 5-7)
- [ ] All 5 levels designed and built in Unity (tilemap layout)
- [ ] Fish placed in all levels
- [ ] Enemy instances placed and configured
- [ ] Moving platforms in Level 4
- [ ] Sheepdog Boss sequence in Level 5
- [ ] Level complete / game over screens

**Milestone Criteria:** All 5 levels playable start to finish with placeholder art.

### Phase 4: Art & Audio Integration (Week 8-10)
- [ ] Final player sprite sheet and Animator setup
- [ ] All enemy sprite sheets and Animators
- [ ] Fish sprites and collect animations
- [ ] Tileset art for all 5 level themes
- [ ] UI art assets
- [ ] Music tracks integrated
- [ ] SFX integrated
- [ ] Haptic feedback implemented

**Milestone Criteria:** Game looks and sounds like the final product.

### Phase 5: Polish & QA (Week 11-12)
- [ ] Cinemachine camera tuning
- [ ] Game feel tuning (coyote time, jump feel, gravity tweaks)
- [ ] Difficulty balancing (enemy speed, alert radius, fish placement)
- [ ] Performance profiling on target devices (aim: 60fps on mid-range phones)
- [ ] Bug fixing
- [ ] Accessibility options (control size, haptics toggle)
- [ ] App store metadata preparation (icon, screenshots, description)

**Milestone Criteria:** Game passes internal QA playthrough. No crash bugs. Runs at 60fps on test devices.

### Phase 6: Release (Week 13-14)
- [ ] Unity Cloud Build: iOS & Android builds
- [ ] TestFlight / Play Store internal track testing
- [ ] Final bug fixes from beta feedback
- [ ] App store submission
- [ ] Marketing material (GIF/video of gameplay)

---

## 6. Performance Targets & Optimization

### 6.1 Targets
- 60 FPS on mid-range devices (iPhone 11, Android with Snapdragon 660 equivalent)
- Max draw calls per frame: ~50
- Max memory usage: ~250 MB

### 6.2 Optimization Strategies
- **Sprite Atlasing:** Pack all sprites per level into sprite atlases to reduce draw calls
- **Object Pooling:** Fish and bone projectiles use object pools (avoid Instantiate/Destroy each frame)
- **Tilemap batching:** URP handles tilemap batching automatically; verify in Frame Debugger
- **Audio compression:** Music as Ogg Vorbis (streaming), SFX as compressed PCM
- **Physics layers:** Limit collision matrix — enemies don't collide with each other, only with ground and player
- **Camera culling:** Objects outside camera view automatically culled; trust Unity's frustum culling

### 6.3 Object Pool Example

```csharp
// Simple object pool for bone projectiles
public class BonePool : MonoBehaviour
{
    [SerializeField] private GameObject bonePrefab;
    [SerializeField] private int poolSize = 10;
    private Queue<GameObject> pool = new Queue<GameObject>();

    void Start()
    {
        for (int i = 0; i < poolSize; i++)
        {
            var bone = Instantiate(bonePrefab);
            bone.SetActive(false);
            pool.Enqueue(bone);
        }
    }

    public GameObject GetBone()
    {
        if (pool.Count > 0)
        {
            var bone = pool.Dequeue();
            bone.SetActive(true);
            return bone;
        }
        return Instantiate(bonePrefab); // fallback
    }

    public void ReturnBone(GameObject bone)
    {
        bone.SetActive(false);
        pool.Enqueue(bone);
    }
}
```

---

## 7. ScriptableObject Data Design

### FishData (ScriptableObject)
```csharp
[CreateAssetMenu(menuName = "CatFish/FishData")]
public class FishData : ScriptableObject
{
    public string fishName;
    public FishType fishType; // Sardine, Salmon, Tuna, Golden
    public int pointValue;
    public Sprite sprite;
    public AudioClip collectSound;
}
```

### EnemyData (ScriptableObject)
```csharp
[CreateAssetMenu(menuName = "CatFish/EnemyData")]
public class EnemyData : ScriptableObject
{
    public string enemyName;
    public float moveSpeed;
    public float alertRadius;
    public float chaseSpeed;
    public Sprite[] sprites;
}
```

### LevelData (ScriptableObject)
```csharp
[CreateAssetMenu(menuName = "CatFish/LevelData")]
public class LevelData : ScriptableObject
{
    public string levelName;
    public int levelIndex;
    public int totalFish;
    public int requiredFish;
    public float targetCompletionTime; // for 3-star rating
    public string sceneName;
}
```

---

## 8. Testing Strategy

### 8.1 Unit Tests (Unity Test Framework)
- SaveSystem: Save and load data integrity
- ScoreManager: Score calculation and star rating
- Fish quota logic: Win condition triggers at correct count

### 8.2 Play Mode Tests
- Player can traverse each level without clipping through geometry
- All fish collectible triggers fire correctly
- Enemy state transitions work correctly

### 8.3 Manual QA Checklist (per level)
- [ ] Level loads without errors
- [ ] All fish are collectable
- [ ] Minimum fish quota triggers exit unlock
- [ ] All enemies behave as designed
- [ ] No geometry gaps player can fall through
- [ ] Checkpoint saves position correctly
- [ ] Level complete screen shows correct star rating
- [ ] Touch controls responsive (test on physical device)
- [ ] No framerate drops during busy scenes

### 8.4 Device Testing Matrix
| Device | OS | Priority |
|--------|----|----------|
| iPhone 15 | iOS 17 | High |
| iPhone 11 | iOS 16 | High |
| Samsung Galaxy S21 | Android 13 | High |
| Mid-range Android (e.g., Pixel 5a) | Android 12 | Medium |
| iPad Air | iPadOS 17 | Low (verify layout) |

---

## 9. Build & Deployment

### 9.1 Unity Build Settings
- **iOS:** Target minimum iOS 14.0, ARM64 architecture
- **Android:** Minimum API Level 24 (Android 7.0), IL2CPP scripting backend, ARM64 + ARMv7
- **Orientation:** Landscape only (locked)

### 9.2 Build Variants
| Variant | Purpose |
|---------|---------|
| Development | Debug logs, Unity Profiler enabled |
| Staging | No debug logs, ad placeholder |
| Release | Fully optimized, store-ready |

### 9.3 Build Pipeline (GitHub Actions or Unity Cloud Build)
1. Trigger on `main` branch push
2. Run Unity Test Framework tests
3. Build iOS (requires macOS runner + Xcode)
4. Build Android (APK + AAB)
5. Upload artifacts to staging
6. Notify team on success/failure

---

## 10. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Touch controls feel imprecise | Medium | High | Early prototype on physical device; adjust button sizes and layout iteratively |
| Level 5 boss too hard for casual players | Medium | Medium | Extensive playtesting; add 3-phase telegraphing; adjustable window |
| Art scope exceeds timeline | Medium | High | Use placeholder art until Phase 4; art can be scope-reduced |
| Performance issues on older Android | Low | Medium | Profile early (Phase 2) not just at end |
| App store rejection | Low | High | Follow App Store / Play Store guidelines from day 1; no third-party SDKs that cause issues |
