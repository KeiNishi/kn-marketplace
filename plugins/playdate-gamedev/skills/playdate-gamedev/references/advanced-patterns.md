# Advanced Patterns

Advanced implementation patterns for Playdate game development.

## State Machine

### Game State Management

```c
typedef enum {
    STATE_MENU,
    STATE_PLAYING,
    STATE_PAUSED,
    STATE_GAME_OVER
} GameState;

typedef struct {
    GameState current_state;
    void (*state_enter)(void);
    void (*state_update)(float dt);
    void (*state_draw)(void);
    void (*state_exit)(void);
} StateMachine;

static StateMachine state_machine = {0};

// State function declarations
static void menu_enter(void);
static void menu_update(float dt);
static void menu_draw(void);
static void menu_exit(void);

static void game_enter(void);
static void game_update(float dt);
static void game_draw(void);
static void game_exit(void);

// Change state
void change_state(GameState new_state) {
    // Exit current state
    if (state_machine.state_exit) {
        state_machine.state_exit();
    }

    state_machine.current_state = new_state;

    // Set new state functions
    switch (new_state) {
        case STATE_MENU:
            state_machine.state_enter = menu_enter;
            state_machine.state_update = menu_update;
            state_machine.state_draw = menu_draw;
            state_machine.state_exit = menu_exit;
            break;
        case STATE_PLAYING:
            state_machine.state_enter = game_enter;
            state_machine.state_update = game_update;
            state_machine.state_draw = game_draw;
            state_machine.state_exit = game_exit;
            break;
        // ... other states
    }

    // Enter new state
    if (state_machine.state_enter) {
        state_machine.state_enter();
    }
}

// Main update
int main_update(void* userdata) {
    float dt = 1.0f / 30.0f;

    if (state_machine.state_update) {
        state_machine.state_update(dt);
    }
    if (state_machine.state_draw) {
        state_machine.state_draw();
    }

    return 1;
}
```

### Entity State Machine

```c
typedef enum {
    ENEMY_IDLE,
    ENEMY_PATROL,
    ENEMY_CHASE,
    ENEMY_ATTACK,
    ENEMY_DEAD
} EnemyState;

typedef struct Enemy {
    float x, y;
    EnemyState state;
    float state_timer;
    // ... other fields
} Enemy;

void enemy_update(Enemy* e, float dt) {
    switch (e->state) {
        case ENEMY_IDLE:
            e->state_timer -= dt;
            if (e->state_timer <= 0) {
                e->state = ENEMY_PATROL;
                e->state_timer = 3.0f;
            }
            if (player_in_range(e)) {
                e->state = ENEMY_CHASE;
            }
            break;

        case ENEMY_PATROL:
            patrol_move(e, dt);
            if (player_in_range(e)) {
                e->state = ENEMY_CHASE;
            }
            break;

        case ENEMY_CHASE:
            chase_player(e, dt);
            if (player_in_attack_range(e)) {
                e->state = ENEMY_ATTACK;
            }
            if (!player_in_range(e)) {
                e->state = ENEMY_IDLE;
                e->state_timer = 1.0f;
            }
            break;

        case ENEMY_ATTACK:
            perform_attack(e, dt);
            if (!player_in_attack_range(e)) {
                e->state = ENEMY_CHASE;
            }
            break;

        case ENEMY_DEAD:
            // Do nothing or play death animation
            break;
    }
}
```

## Scene Management

```c
typedef struct Scene {
    void (*init)(void);
    void (*update)(float dt);
    void (*draw)(void);
    void (*cleanup)(void);
} Scene;

static Scene* current_scene = NULL;

// Scene definitions
static Scene menu_scene = {
    .init = menu_init,
    .update = menu_update,
    .draw = menu_draw,
    .cleanup = menu_cleanup
};

static Scene game_scene = {
    .init = game_init,
    .update = game_update,
    .draw = game_draw,
    .cleanup = game_cleanup
};

void scene_set(Scene* new_scene) {
    if (current_scene && current_scene->cleanup) {
        current_scene->cleanup();
    }

    current_scene = new_scene;

    if (current_scene && current_scene->init) {
        current_scene->init();
    }
}

int main_update(void* userdata) {
    float dt = 1.0f / 30.0f;

    if (current_scene) {
        if (current_scene->update) current_scene->update(dt);
        if (current_scene->draw) current_scene->draw();
    }

    return 1;
}

// Usage
void start_game(void) {
    scene_set(&game_scene);
}

void return_to_menu(void) {
    scene_set(&menu_scene);
}
```

## Timer System

```c
#define MAX_TIMERS 32

typedef struct {
    float duration;
    float elapsed;
    int active;
    int repeating;
    void (*callback)(void* userdata);
    void* userdata;
} Timer;

static Timer timers[MAX_TIMERS];

Timer* timer_start(float duration, void (*callback)(void*), void* userdata) {
    for (int i = 0; i < MAX_TIMERS; i++) {
        if (!timers[i].active) {
            timers[i].duration = duration;
            timers[i].elapsed = 0;
            timers[i].callback = callback;
            timers[i].userdata = userdata;
            timers[i].active = 1;
            timers[i].repeating = 0;
            return &timers[i];
        }
    }
    return NULL;
}

Timer* timer_start_repeating(float interval, void (*callback)(void*), void* userdata) {
    Timer* t = timer_start(interval, callback, userdata);
    if (t) t->repeating = 1;
    return t;
}

void timer_stop(Timer* timer) {
    if (timer) timer->active = 0;
}

void timer_update_all(float dt) {
    for (int i = 0; i < MAX_TIMERS; i++) {
        if (!timers[i].active) continue;

        timers[i].elapsed += dt;
        if (timers[i].elapsed >= timers[i].duration) {
            if (timers[i].callback) {
                timers[i].callback(timers[i].userdata);
            }

            if (timers[i].repeating) {
                timers[i].elapsed = 0;
            } else {
                timers[i].active = 0;
            }
        }
    }
}

// Usage
void spawn_enemy_callback(void* userdata) {
    spawn_enemy();
}

void start_spawning(void) {
    timer_start_repeating(2.0f, spawn_enemy_callback, NULL);
}
```

## Data-Driven Design

### JSON Configuration

```c
// Example: levels/level1.json
// { "enemies": [{"type": "slime", "x": 100, "y": 50}] }

typedef struct {
    char type[32];
    float x;
    float y;
} EnemySpawnData;

void load_level_from_json(const char* path) {
    // Read file
    SDFile* file = g_pd->file->open(path, kFileRead);
    if (!file) return;

    g_pd->file->seek(file, 0, SEEK_END);
    int size = g_pd->file->tell(file);
    g_pd->file->seek(file, 0, SEEK_SET);

    char* json = g_pd->system->realloc(NULL, size + 1);
    g_pd->file->read(file, json, size);
    json[size] = '\0';
    g_pd->file->close(file);

    // Parse JSON using Playdate's json API
    // Note: Simplified example - actual parsing is more complex
    // Consider using a simple custom format instead

    g_pd->system->realloc(json, 0);
}
```

### Simple Custom Format

```c
// levels/level1.dat - Binary format
// [enemy_count:int][enemy1:EnemyData][enemy2:EnemyData]...

typedef struct {
    int type;
    float x;
    float y;
    int health;
} EnemyData;

void load_level_binary(const char* path) {
    SDFile* file = g_pd->file->open(path, kFileRead);
    if (!file) return;

    int enemy_count = 0;
    g_pd->file->read(file, &enemy_count, sizeof(int));

    for (int i = 0; i < enemy_count; i++) {
        EnemyData data;
        g_pd->file->read(file, &data, sizeof(EnemyData));
        spawn_enemy_from_data(&data);
    }

    g_pd->file->close(file);
}
```

## Custom Allocator

### Stack Allocator

For temporary per-frame allocations:

```c
typedef struct {
    uint8_t* buffer;
    size_t size;
    size_t offset;
} StackAllocator;

static StackAllocator temp_allocator;

void stack_allocator_init(size_t size) {
    temp_allocator.buffer = g_pd->system->realloc(NULL, size);
    temp_allocator.size = size;
    temp_allocator.offset = 0;
}

void* stack_alloc(size_t size) {
    // Align to 8 bytes
    size_t aligned_size = (size + 7) & ~7;

    if (temp_allocator.offset + aligned_size > temp_allocator.size) {
        g_pd->system->error("Stack allocator overflow!");
        return NULL;
    }

    void* ptr = temp_allocator.buffer + temp_allocator.offset;
    temp_allocator.offset += aligned_size;
    return ptr;
}

void stack_allocator_reset(void) {
    temp_allocator.offset = 0;
}

void stack_allocator_cleanup(void) {
    g_pd->system->realloc(temp_allocator.buffer, 0);
}

// Usage - reset at start of each frame
int game_update(void* userdata) {
    stack_allocator_reset();

    // Temporary allocations during frame
    int* temp_data = stack_alloc(sizeof(int) * 100);
    // Use temp_data...
    // Automatically "freed" on next reset

    return 1;
}
```

## Component System (Lightweight ECS)

```c
#define MAX_ENTITIES 256

// Component flags
typedef enum {
    COMP_POSITION  = 1 << 0,
    COMP_VELOCITY  = 1 << 1,
    COMP_SPRITE    = 1 << 2,
    COMP_HEALTH    = 1 << 3,
    COMP_PLAYER    = 1 << 4,
    COMP_ENEMY     = 1 << 5
} ComponentType;

// Components
typedef struct { float x, y; } Position;
typedef struct { float x, y; } Velocity;
typedef struct { LCDSprite* sprite; } SpriteComp;
typedef struct { int current, max; } Health;

// Entity manager
typedef struct {
    unsigned int flags[MAX_ENTITIES];
    Position positions[MAX_ENTITIES];
    Velocity velocities[MAX_ENTITIES];
    SpriteComp sprites[MAX_ENTITIES];
    Health healths[MAX_ENTITIES];
    int count;
} EntityManager;

static EntityManager em = {0};

int entity_create(unsigned int components) {
    if (em.count >= MAX_ENTITIES) return -1;

    int id = em.count++;
    em.flags[id] = components;
    return id;
}

void entity_destroy(int id) {
    // Move last entity to this slot
    int last = em.count - 1;
    if (id != last) {
        em.flags[id] = em.flags[last];
        em.positions[id] = em.positions[last];
        em.velocities[id] = em.velocities[last];
        em.sprites[id] = em.sprites[last];
        em.healths[id] = em.healths[last];
    }
    em.count--;
}

// System: Movement
void system_movement(float dt) {
    for (int i = 0; i < em.count; i++) {
        if ((em.flags[i] & (COMP_POSITION | COMP_VELOCITY)) ==
            (COMP_POSITION | COMP_VELOCITY)) {
            em.positions[i].x += em.velocities[i].x * dt;
            em.positions[i].y += em.velocities[i].y * dt;
        }
    }
}

// System: Sprite sync
void system_sprite_sync(void) {
    for (int i = 0; i < em.count; i++) {
        if ((em.flags[i] & (COMP_POSITION | COMP_SPRITE)) ==
            (COMP_POSITION | COMP_SPRITE)) {
            g_pd->sprite->moveTo(em.sprites[i].sprite,
                                 em.positions[i].x,
                                 em.positions[i].y);
        }
    }
}

// Usage
void create_player(float x, float y) {
    int id = entity_create(COMP_POSITION | COMP_VELOCITY | COMP_SPRITE | COMP_HEALTH | COMP_PLAYER);
    em.positions[id] = (Position){ x, y };
    em.velocities[id] = (Velocity){ 0, 0 };
    em.healths[id] = (Health){ 100, 100 };
    // Setup sprite...
}
```

## Event System

```c
#define MAX_LISTENERS 32

typedef enum {
    EVENT_PLAYER_DIED,
    EVENT_ENEMY_KILLED,
    EVENT_ITEM_COLLECTED,
    EVENT_LEVEL_COMPLETE,
    EVENT_COUNT
} EventType;

typedef void (*EventCallback)(void* data);

typedef struct {
    EventCallback callbacks[MAX_LISTENERS];
    int count;
} EventListeners;

static EventListeners listeners[EVENT_COUNT] = {0};

void event_subscribe(EventType type, EventCallback callback) {
    EventListeners* l = &listeners[type];
    if (l->count < MAX_LISTENERS) {
        l->callbacks[l->count++] = callback;
    }
}

void event_fire(EventType type, void* data) {
    EventListeners* l = &listeners[type];
    for (int i = 0; i < l->count; i++) {
        l->callbacks[i](data);
    }
}

// Usage
void on_player_died(void* data) {
    change_state(STATE_GAME_OVER);
}

void on_enemy_killed(void* data) {
    score += 100;
}

void setup_events(void) {
    event_subscribe(EVENT_PLAYER_DIED, on_player_died);
    event_subscribe(EVENT_ENEMY_KILLED, on_enemy_killed);
}

// Fire event when enemy dies
void enemy_die(Enemy* e) {
    event_fire(EVENT_ENEMY_KILLED, e);
    enemy_destroy(e);
}
```

## Tween System

Simple tweening for animations:

```c
typedef enum {
    EASE_LINEAR,
    EASE_IN_QUAD,
    EASE_OUT_QUAD,
    EASE_IN_OUT_QUAD
} EaseType;

typedef struct {
    float* target;
    float start;
    float end;
    float duration;
    float elapsed;
    EaseType ease;
    int active;
    void (*on_complete)(void*);
    void* userdata;
} Tween;

#define MAX_TWEENS 32
static Tween tweens[MAX_TWEENS] = {0};

float ease_value(float t, EaseType ease) {
    switch (ease) {
        case EASE_LINEAR:
            return t;
        case EASE_IN_QUAD:
            return t * t;
        case EASE_OUT_QUAD:
            return t * (2 - t);
        case EASE_IN_OUT_QUAD:
            return t < 0.5f ? 2 * t * t : -1 + (4 - 2 * t) * t;
        default:
            return t;
    }
}

Tween* tween_to(float* target, float end, float duration, EaseType ease) {
    for (int i = 0; i < MAX_TWEENS; i++) {
        if (!tweens[i].active) {
            tweens[i].target = target;
            tweens[i].start = *target;
            tweens[i].end = end;
            tweens[i].duration = duration;
            tweens[i].elapsed = 0;
            tweens[i].ease = ease;
            tweens[i].active = 1;
            tweens[i].on_complete = NULL;
            return &tweens[i];
        }
    }
    return NULL;
}

void tween_update_all(float dt) {
    for (int i = 0; i < MAX_TWEENS; i++) {
        if (!tweens[i].active) continue;

        tweens[i].elapsed += dt;
        float t = tweens[i].elapsed / tweens[i].duration;

        if (t >= 1.0f) {
            t = 1.0f;
            *tweens[i].target = tweens[i].end;
            tweens[i].active = 0;

            if (tweens[i].on_complete) {
                tweens[i].on_complete(tweens[i].userdata);
            }
        } else {
            float eased = ease_value(t, tweens[i].ease);
            *tweens[i].target = tweens[i].start +
                               (tweens[i].end - tweens[i].start) * eased;
        }
    }
}

// Usage
void start_fade_in(void) {
    tween_to(&screen_alpha, 1.0f, 0.5f, EASE_OUT_QUAD);
}
```
