# Coding Standards

Complete coding conventions for Playdate C development.

## Naming Conventions

### Constants

```c
// SCREAMING_SNAKE_CASE
#define MAX_ENEMIES 100
#define SCREEN_WIDTH 400
#define SCREEN_HEIGHT 240
```

### Types

```c
// PascalCase for type definitions
typedef struct {
    float x;
    float y;
} Vector2;

typedef struct Player {
    Vector2 position;
    int health;
} Player;

typedef enum {
    STATE_MENU,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAME_OVER
} GameState;
```

### Functions

```c
// snake_case
void init_game(void);
void update_player(Player* player, float dt);

// Static functions for internal use
static void handle_collision(void);
```

### Variables

```c
// Local and struct members: snake_case
int enemy_count = 0;
float delta_time = 0.0f;
Player* player = NULL;

// Global variables: g_ prefix (recommended)
static PlaydateAPI* g_pd = NULL;
static Player* g_player = NULL;
```

## File Organization

### Header File Pattern (.h)

```c
// player.h
#ifndef PLAYER_H
#define PLAYER_H

#include "pd_api.h"

// Forward declaration (hide implementation)
typedef struct Player Player;

// Public API
Player* player_create(float x, float y);
void player_destroy(Player* player);
void player_update(Player* player, float dt);
void player_draw(Player* player);

// Getters (if needed)
float player_get_x(const Player* player);
float player_get_y(const Player* player);

#endif // PLAYER_H
```

### Implementation File Pattern (.c)

```c
// player.c
#include "player.h"
#include <stdlib.h>

// Struct definition (hidden from header)
struct Player {
    float x;
    float y;
    int health;
    LCDSprite* sprite;
};

// Reference global Playdate API
extern PlaydateAPI* g_pd;

// Constructor
Player* player_create(float x, float y) {
    Player* player = g_pd->system->realloc(NULL, sizeof(Player));
    if (!player) return NULL;

    player->x = x;
    player->y = y;
    player->health = 100;
    player->sprite = g_pd->sprite->newSprite();

    return player;
}

// Destructor
void player_destroy(Player* player) {
    if (!player) return;

    if (player->sprite) {
        g_pd->sprite->freeSprite(player->sprite);
    }
    g_pd->system->realloc(player, 0);
}

// Update
void player_update(Player* player, float dt) {
    if (!player) return;

    PDButtons current, pushed, released;
    g_pd->system->getButtonState(&current, &pushed, &released);

    if (current & kButtonLeft) {
        player->x -= 100.0f * dt;
    }
    if (current & kButtonRight) {
        player->x += 100.0f * dt;
    }
}

// Draw
void player_draw(Player* player) {
    if (!player || !player->sprite) return;

    g_pd->sprite->moveTo(player->sprite, player->x, player->y);
}
```

## Error Handling

### NULL Checks

```c
// Always check pointers before use
void update_entity(Entity* entity, float dt) {
    if (!entity) {
        g_pd->system->logToConsole("ERROR: entity is NULL");
        return;
    }

    // Safe to use entity
    entity->x += entity->vel_x * dt;
}
```

### Resource Allocation

```c
Enemy* enemy_create(void) {
    // Allocate struct
    Enemy* enemy = g_pd->system->realloc(NULL, sizeof(Enemy));
    if (!enemy) {
        g_pd->system->error("Failed to allocate memory for enemy");
        return NULL;
    }

    // Allocate sprite
    enemy->sprite = g_pd->sprite->newSprite();
    if (!enemy->sprite) {
        // Clean up on partial failure
        g_pd->system->realloc(enemy, 0);
        g_pd->system->error("Failed to create sprite");
        return NULL;
    }

    return enemy;
}
```

### Debug Assertions

```c
#ifdef DEBUG
#define ASSERT(condition, message) \
    if (!(condition)) { \
        g_pd->system->error("ASSERTION FAILED: %s", message); \
    }
#else
#define ASSERT(condition, message)
#endif

// Usage
void player_set_health(Player* player, int health) {
    ASSERT(player != NULL, "player is NULL");
    ASSERT(health >= 0, "health cannot be negative");
    player->health = health;
}
```

## Code Organization

### Region Comments

```c
// ============================================
// CONSTANTS
// ============================================

#define MAX_ENEMIES 100
#define SPAWN_INTERVAL 2.0f

// ============================================
// TYPES
// ============================================

typedef struct Enemy Enemy;

// ============================================
// PRIVATE VARIABLES
// ============================================

static Enemy* enemies[MAX_ENEMIES];
static int enemy_count = 0;

// ============================================
// PRIVATE FUNCTIONS
// ============================================

static void spawn_enemy(void);
static void update_enemies(float dt);

// ============================================
// PUBLIC FUNCTIONS
// ============================================

void enemy_system_init(void);
void enemy_system_update(float dt);
```

### Function Order

1. Static/private helper functions first
2. Public API functions after
3. Or group by functionality

### Include Order

```c
// 1. Corresponding header
#include "player.h"

// 2. Playdate API
#include "pd_api.h"

// 3. Project headers
#include "game.h"
#include "utils.h"

// 4. Standard library (if needed)
#include <stdlib.h>
#include <string.h>
```

## Comments

### Function Documentation

```c
/**
 * Creates a new player at the specified position.
 *
 * @param x Initial X position
 * @param y Initial Y position
 * @return Pointer to new Player, or NULL on failure
 */
Player* player_create(float x, float y);
```

### Inline Comments

```c
// Use sparingly for non-obvious code
float angle = atan2f(dy, dx);  // Returns radians, -PI to PI
```

### TODO Comments

```c
// TODO: Implement collision response
// FIXME: Memory leak when player dies
// HACK: Temporary workaround for sprite flicker
```

## Best Practices

### Do's

- Use consistent naming throughout project
- Keep functions focused and small (<50 lines ideal)
- Use forward declarations in headers
- Initialize all variables
- Free all allocated resources
- Use const for read-only parameters

### Don'ts

- Don't use magic numbers (use #define)
- Don't nest more than 3 levels deep
- Don't use global variables excessively
- Don't ignore compiler warnings
- Don't skip error handling
