# Player Implementation

**Back to:** [ImplementationPlanOverview.md](../ImplementationPlanOverview.md)

## Architecture
- PlayerController.cs - Input handling and movement
- PlayerModel.cs - Stats and state

## Phase 1: Core Movement

### Task 1: Player Movement
- Files: `Assets/_Project/Scripts/Player/PlayerController.cs`, `Assets/_Project/Scripts/Player/PlayerModel.cs`
- Implement WASD/arrow key movement with Rigidbody
- Add jump mechanic with space bar

### Task 2: Animation
- Files: `Assets/_Project/Scripts/Player/PlayerView.cs`
- Connect animations to state

## Dependencies
- Unity Rigidbody2D
- UniTask
