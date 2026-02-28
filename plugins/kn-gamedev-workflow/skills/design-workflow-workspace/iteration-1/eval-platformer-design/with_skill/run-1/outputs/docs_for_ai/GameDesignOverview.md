# Game Design Document: Purrfect Run

## 1. Game Overview

| Field | Value |
|-------|-------|
| **Title** | Purrfect Run |
| **Genre** | 2D Platformer |
| **Platform** | Mobile (iOS / Android) |
| **Engine/Framework** | Unity 6.3 LTS |
| **Target Audience** | Casual gamers, ages 8+ |
| **Estimated Playtime** | [EXAMPLE: 30-60 minutes] (5 levels) |

## 2. Core Concept

### 2.1 Elevator Pitch
A cute 2D mobile platformer where players control a nimble cat running through colorful stages, collecting fish for points and dodging aggressive dogs to reach the goal.

### 2.2 Unique Selling Points
- Charming cat protagonist with fluid run-and-jump feel optimized for touch controls
- Risk-reward fish collection alongside dog avoidance creates moment-to-moment tension
- Five hand-crafted levels with increasing challenge and distinct visual themes

### 2.3 Inspiration/References
- Crossy Road (casual mobile charm)
- Super Mario Bros. (classic platformer loop)
- Neko Atsume (cat aesthetics and appeal)

## 3. World and Setting

### 3.1 Setting Overview
A cheerful neighborhood world seen from the side. The cat journeys through backyards, fish markets, alleyways, rooftops, and a final park finale. The tone is light and comedic — dogs are bumbling chasers, not threats.

### 3.2 Visual Style
2D cartoon sprites with bold outlines and bright colors. Simple parallax backgrounds. Mobile-friendly large sprites and high-contrast visuals for small screens.

### 3.3 Audio Direction
Upbeat, playful chiptune or light jazz music per level. Satisfying sound effects for fish pickups (chime), dog contact (cartoon "bonk"), jumps, and level completion jingle.

## 4. Design File Manifest

| # | File | Domain | Description |
|---|------|--------|-------------|
| 01 | [01_Player_Design.md](./game_design/01_Player_Design.md) | Player | Cat movement, jump mechanics, touch controls |
| 02 | [02_Collectibles_Design.md](./game_design/02_Collectibles_Design.md) | Collectibles | Fish types, scoring, collection effects |
| 03 | [03_Enemies_Design.md](./game_design/03_Enemies_Design.md) | Enemies | Dog behavior, patrol patterns, interaction |
| 04 | [04_LevelContent_Design.md](./game_design/04_LevelContent_Design.md) | Levels | Level themes, layouts, progression across 5 stages |

## 5. Cross-Cutting Concerns

### 5.1 Score and Star Rating
Each level tracks fish collected and time elapsed. A 1-3 star rating is awarded at level completion based on fish count. Stars persist in save data. Affects all levels and the UI.

### 5.2 Save System
Level unlock state and star ratings are saved to device persistent storage. The game autosaves on level completion. No cloud save in initial scope.

### 5.3 Touch Input
All gameplay input is handled by on-screen touch buttons (virtual D-pad left/right + jump button). Must work cleanly on both phones and tablets.

## 6. Technical Requirements

### 6.1 Performance Targets
- Frame Rate: [EXAMPLE: 60 FPS] on supported devices
- Resolution: Auto-scaled to device screen (portrait or landscape)
- Load Time: [EXAMPLE: < 3 seconds] per level

### 6.2 Technical Constraints
- Mobile-first: minimize memory usage, avoid heavy shaders
- Sprite atlases for all character and environment art to reduce draw calls
- No real-time lighting — use pre-baked sprite shading only

### 6.3 External Dependencies
- Unity 2D Physics (Rigidbody2D / BoxCollider2D)
- Unity Input System (mobile touch)
- Unity UI Toolkit or uGUI for HUD

## 7. Content Scope Summary

| Category | Count | Details |
|----------|-------|---------|
| Levels/Stages | 5 | Backyard, Fish Market, Alleyway, Rooftops, Park |
| Characters/Entities | 3 | Cat (player), Dog (enemy), Fish (collectible) |
| Items/Collectibles | [EXAMPLE: 10-20 per level] | Small fish (1pt), Big fish (3pt), Golden fish (5pt) |

## 8. Notes

- Values marked with [EXAMPLE: X] are subject to change during playtesting
- This document provides an overview; see detail files in `game_design/` for specifics
- See ImplementationPlanOverview.md for HOW to build it
