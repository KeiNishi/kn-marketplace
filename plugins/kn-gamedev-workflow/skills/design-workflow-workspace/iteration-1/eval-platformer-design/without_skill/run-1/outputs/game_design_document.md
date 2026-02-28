# Cat & Fish: A 2D Mobile Platformer
## Game Design Document (GDD)

**Version:** 1.0
**Date:** 2026-02-28
**Platform:** Unity Mobile (iOS & Android)
**Genre:** 2D Side-Scrolling Platformer

---

## 1. Game Overview

### 1.1 Concept
Cat & Fish is a charming 2D side-scrolling platformer for mobile devices. The player controls a cat character navigating colorful environments, collecting fish while avoiding dangerous dogs. The game features 5 progressively challenging levels, pick-up-and-play accessibility, and satisfying movement mechanics optimized for touch input.

### 1.2 Target Audience
- Age: 8 and up
- Casual to mid-core mobile gamers
- Fans of cute animal aesthetics
- Players who enjoy arcade-style platformers

### 1.3 Unique Selling Points
- Intuitive one-thumb control scheme for mobile
- Expressive cat character with fluid animations
- Variety of fish types with different point values
- Escalating challenge with distinct dog enemy behaviors
- Colorful, cartoonish art direction

---

## 2. Gameplay Design

### 2.1 Core Loop
1. Player navigates a level by running and jumping
2. Collect fish to earn points and progress toward level completion
3. Avoid or escape from dog enemies
4. Reach the end of the level (or collect a required number of fish) to advance
5. Repeat with increasing difficulty

### 2.2 Win & Fail Conditions
- **Win:** Collect the required fish quota AND reach the exit portal/goal
- **Fail:** Getting caught by a dog (touched), falling into a pit/hazard
- **Retry:** Instant retry button on death, no long load screens

### 2.3 Scoring System
| Fish Type | Points |
|-----------|--------|
| Sardine (common) | 10 |
| Salmon (uncommon) | 30 |
| Tuna (rare) | 50 |
| Golden Fish (bonus) | 100 |

- **Star Rating:** 1–3 stars per level based on fish collected and time
  - 1 Star: Complete level (meet minimum fish quota)
  - 2 Stars: Collect 75% of all fish in level
  - 3 Stars: Collect 100% of all fish in level within time limit

---

## 3. Player Character: The Cat

### 3.1 Character Description
- Name: Nyan (working title)
- A small, expressive orange tabby cat
- Large eyes that emote during gameplay (idle, scared, happy)
- Wears a little scarf (visual personality touch)

### 3.2 Movement Mechanics
| Action | Description | Control |
|--------|-------------|---------|
| Run | Auto-run from left to right; direction can be reversed | Left/Right virtual buttons |
| Jump | Single jump with variable height | Jump button (hold for higher jump) |
| Double Jump | Unlocked after Level 2 | Second press of Jump button mid-air |
| Wall Slide | Slow fall when pressing against a wall | Hold into wall direction |
| Wall Jump | Jump off walls | Jump while wall sliding |

#### Mobile Control Layout
- Left half of screen: Left/Right directional buttons (thumb-friendly)
- Right side: Jump button (large, prominent)
- Optional swipe gestures as accessibility alternative

### 3.3 Physics Parameters (Design Targets)
| Parameter | Value (design intent) |
|-----------|----------------------|
| Run Speed | 5 units/sec (base), 7 units/sec (sprinting) |
| Jump Height | ~3.5 platform-units (single), ~5.5 (double) |
| Gravity Scale | 2.5x (snappy, not floaty) |
| Coyote Time | 0.1 seconds |
| Jump Buffer | 0.15 seconds |

**Note:** "Coyote Time" allows the player to jump briefly after walking off a ledge; "Jump Buffer" queues a jump input slightly before landing. Both improve game feel.

### 3.4 Animations
- Idle (sitting, tail flick loop)
- Run (4-legged gallop cycle)
- Jump (stretch up)
- Fall (curl/wide eyes)
- Land (squash)
- Wall Slide (claws-out slide)
- Collect Fish (quick happy spin)
- Hit by Dog (flail, knocked back)
- Death (star burst, cute)

---

## 4. Fish (Collectibles)

### 4.1 Fish Placement Philosophy
- Sardines are scattered throughout as the baseline collectible
- Salmon and Tuna placed in moderately risky locations (over gaps, near dogs)
- Golden Fish placed in the most challenging or hidden spots
- Every level has a "secret" Golden Fish requiring exploration or precise platforming

### 4.2 Fish Behaviors
- Static placement (most fish): floating/bobbing in place
- Moving fish (later levels): fish swimming back and forth on a path
- Fish jars (bonus): a sealed container the cat must break open for multiple fish inside

### 4.3 Fish Magnet Power-Up
- Temporary collectible that attracts all nearby fish to the player
- Lasts 5 seconds
- Visual: glowing aura around the cat

---

## 5. Enemies: The Dogs

### 5.1 Dog Types

#### Type 1: Poodle Patrol (Levels 1-3)
- Walks back and forth on a platform
- Turns around at ledge edges or walls
- Cannot jump
- Alert range: 4 units horizontal

#### Type 2: Bulldog Chase (Levels 2-5)
- Stationary until cat enters alert radius (6 units)
- Charges in a straight line when alerted
- Stops at platform edge; cannot fall off
- Slower but has large body (wider hitbox)

#### Type 3: Terrier Jumper (Levels 3-5)
- Can jump between platforms
- Patrols a set vertical and horizontal range
- Faster than other dogs

#### Type 4: Sheepdog Boss (Level 5 only)
- Large enemy covering a wide area
- Throws bones as projectiles
- Has 3 phase behavior (patrol → chase → frantic)
- Requires avoiding for 30 seconds to clear zone (not defeated, just outlasted)

### 5.2 Dog Encounter Design Principles
- Dogs should feel threatening but fair
- Player always has an escape route
- Dogs do not permanently follow the player across the entire level
- Alert state is clearly communicated (exclamation mark icon + bark SFX)

---

## 6. Level Design

### 6.1 Level Progression Overview

| Level | Name | Setting | New Mechanic | Dog Types | Fish Quota |
|-------|------|---------|--------------|-----------|------------|
| 1 | The Sunny Yard | Suburban backyard | Run & Jump basics | Poodle Patrol | 10/20 fish |
| 2 | The Rooftop Chase | City rooftops | Double Jump | Poodle + Bulldog | 15/25 fish |
| 3 | The Rainy Alley | Wet urban alley | Wall Slide & Jump | All basic types | 20/30 fish |
| 4 | The Haunted Park | Spooky park at night | Moving platforms | All types | 25/35 fish |
| 5 | The Junkyard Finale | Industrial junkyard | Sheepdog Boss zone | All + Sheepdog | 30/40 fish |

### 6.2 Level Structure (per level)
- **Length:** ~90–120 seconds to complete at average pace
- **Layout:** Horizontal scroll, some vertical climbing sections
- **Checkpoints:** 2 per level (placed after difficult sections)
- **Exit:** Glowing cat door / portal at the end

### 6.3 Level 1: The Sunny Yard (Detailed Breakdown)
- **Goal:** Introduce run and jump. Safe, tutorial-style.
- **Sections:**
  1. Flat run with spaced platforms — teaches jumping over gaps
  2. Short vertical section — jump up flower pots and fence posts
  3. First Poodle Patrol — wide platform, easy to jump over
  4. Sardine collection zone — rewarding, safe fish cluster
  5. Goal: Cat door in a shed wall
- **Fish count:** 20 Sardines, 0 Salmon, 0 Tuna, 0 Golden
- **Fish quota to advance:** 10

### 6.4 Level 5: The Junkyard Finale (Detailed Breakdown)
- **Goal:** Culminate all mechanics. Challenging but fair.
- **Sections:**
  1. Obstacle gauntlet — Terriers + moving platforms
  2. Bulldog maze — narrow corridors requiring precise timing
  3. Hidden Golden Fish zone — optional, high-risk area
  4. Sheepdog Boss zone — 30-second endurance section avoiding bone throws
  5. Final sprint to exit — escape sequence feel, exciting music change
- **Fish count:** 15 Sardines, 10 Salmon, 10 Tuna, 5 Golden
- **Fish quota to advance:** 30

---

## 7. Visual Design

### 7.1 Art Direction
- **Style:** Cartoon 2D sprite art, bright and saturated
- **Inspiration:** Early Flash games, Nitrome aesthetic, Neko Atsume charm
- **Resolution Target:** 1920x1080 base, scaled for mobile screens
- **Sprite Size:** Player ~64x64 px logical; environments tile at 32x32

### 7.2 Color Palette per Level
| Level | Primary Color | Mood |
|-------|--------------|------|
| 1 | Warm yellows, greens | Cheerful, safe |
| 2 | Blues, grays, orange sunset | Adventurous |
| 3 | Dark blues, purple rain | Tense, moody |
| 4 | Deep purples, oranges, fireflies | Eerie, whimsical |
| 5 | Browns, rusted metal, sparks | Industrial, dramatic |

### 7.3 UI/HUD
- Fish counter (top left): icon + current/quota count
- Score display (top center)
- Lives/health indicator: 3 fish icons (cat has 3 lives)
- Touch controls: Semi-transparent, unobtrusive
- No persistent UI clutter; level name shown only at start

---

## 8. Audio Design

### 8.1 Music
- Upbeat, looping background tracks per level
- Level 1: Acoustic/ukulele
- Level 2: Upbeat synth
- Level 3: Jazz/blues with rain ambience
- Level 4: Playful spooky (pizzicato strings, theremin)
- Level 5: Rock/chase music
- Boss sequence: High-energy action track

### 8.2 Sound Effects
- Cat meow on jump (light, not annoying)
- Fish collection chime (sparkle SFX)
- Dog bark on alert
- Dog chase growl (looping)
- Hit: yelp + knockback
- Level complete: happy cat purr jingle

### 8.3 Haptic Feedback (Mobile)
- Light tap: Fish collected
- Medium pulse: Jump
- Strong vibration: Hit by dog / death

---

## 9. Progression & Retention

### 9.1 Level Unlock System
- Levels unlock sequentially (complete Level N to unlock N+1)
- One-time unlock: No grinding required

### 9.2 Replay Incentives
- 3-star system encourages replays for perfectionists
- Total star count displayed on level select screen
- Potential future: leaderboard scores per level

### 9.3 Metagame (Optional Future Scope)
- Costume shop: Unlock cat skins with collected stars
- Gallery: Unlock fish artwork as you collect types
- These are out of scope for v1.0 but noted for roadmap

---

## 10. Accessibility

- Adjustable touch control size (small/medium/large)
- Colorblind-friendly fish icons (distinct shapes, not just colors)
- Option to disable haptic feedback
- Pause available at any time
- Checkpoint system reduces punishment for failure
