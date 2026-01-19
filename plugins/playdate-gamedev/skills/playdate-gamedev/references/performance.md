# Performance Optimization

Performance optimization techniques for Playdate games.

## Memory Management

### Playdate Allocator

Always prefer Playdate's allocator over stdlib:

```c
// Allocate
void* ptr = g_pd->system->realloc(NULL, 1024);

// Reallocate
ptr = g_pd->system->realloc(ptr, 2048);

// Free
g_pd->system->realloc(ptr, 0);

// Why: Playdate tracks allocations and can report leaks
```

### Memory Usage Tracking

```c
void log_memory_stats(void) {
    // Log current allocation
    g_pd->system->logToConsole("Heap check point");
}
```

### Avoiding Allocations

```c
// BAD: Allocate every frame
void update_bad(void) {
    char* buffer = g_pd->system->realloc(NULL, 256);
    sprintf(buffer, "Score: %d", score);
    g_pd->graphics->drawText(buffer, strlen(buffer), kASCIIEncoding, 10, 10);
    g_pd->system->realloc(buffer, 0);
}

// GOOD: Pre-allocate buffer
static char text_buffer[256];
void update_good(void) {
    sprintf(text_buffer, "Score: %d", score);
    g_pd->graphics->drawText(text_buffer, strlen(text_buffer), kASCIIEncoding, 10, 10);
}
```

## Drawing Optimization

### Dirty Rectangle Updates

Only redraw what changed:

```c
// Instead of clearing entire screen
// g_pd->graphics->clear(kColorWhite);

// Mark only changed regions
g_pd->graphics->markUpdatedRows(player_y - 32, player_y + 32);
```

### Sprite System Benefits

The sprite system automatically:
- Culls off-screen sprites
- Sorts by Z-index
- Only redraws changed areas

```c
// Let sprites handle drawing
void game_update(void* userdata) {
    // Update sprite positions
    g_pd->sprite->moveTo(player_sprite, player_x, player_y);

    // Draw all sprites (automatic culling)
    g_pd->sprite->drawSprites();

    return 1;
}
```

### Minimize Draw Calls

```c
// BAD: Many individual draws
for (int i = 0; i < 100; i++) {
    g_pd->graphics->drawBitmap(tile, tiles[i].x, tiles[i].y, kBitmapUnflipped);
}

// GOOD: Pre-render tilemap to single bitmap
// Or use sprite system which batches internally
```

## FPS Management

### Target Frame Rate

```c
// 30 FPS is recommended (battery + smoothness balance)
g_pd->display->setRefreshRate(30.0f);

// 50 FPS max for demanding games
g_pd->display->setRefreshRate(50.0f);

// Lower for menu screens
g_pd->display->setRefreshRate(20.0f);
```

### Frame Time Budget

At 30 FPS: ~33ms per frame
At 50 FPS: ~20ms per frame

```c
void update_with_profiling(void) {
    unsigned int start = g_pd->system->getCurrentTimeMilliseconds();

    // Game logic
    update_game();

    // Drawing
    draw_game();

    unsigned int elapsed = g_pd->system->getCurrentTimeMilliseconds() - start;
    if (elapsed > 30) {  // Exceeding 30ms budget
        g_pd->system->logToConsole("SLOW FRAME: %u ms", elapsed);
    }
}
```

### Fixed Timestep

For consistent physics regardless of frame drops:

```c
static float accumulator = 0.0f;
const float FIXED_DT = 1.0f / 30.0f;

int game_update(void* userdata) {
    // Approximate frame time
    static unsigned int last_time = 0;
    unsigned int now = g_pd->system->getCurrentTimeMilliseconds();
    float frame_time = (now - last_time) / 1000.0f;
    last_time = now;

    // Clamp to avoid spiral of death
    if (frame_time > 0.1f) frame_time = 0.1f;

    accumulator += frame_time;

    // Fixed timestep updates
    while (accumulator >= FIXED_DT) {
        update_physics(FIXED_DT);
        accumulator -= FIXED_DT;
    }

    // Render (can interpolate for smoothness)
    render_game();

    return 1;
}
```

## Object Pooling

Avoid runtime allocation for frequently created/destroyed objects:

```c
#define BULLET_POOL_SIZE 100

typedef struct {
    float x, y;
    float vel_x, vel_y;
    int active;
    LCDSprite* sprite;
} Bullet;

static Bullet bullet_pool[BULLET_POOL_SIZE];
static int pool_initialized = 0;

void bullet_pool_init(void) {
    if (pool_initialized) return;

    for (int i = 0; i < BULLET_POOL_SIZE; i++) {
        bullet_pool[i].active = 0;
        bullet_pool[i].sprite = g_pd->sprite->newSprite();

        LCDBitmap* bmp = g_pd->graphics->loadBitmap("images/bullet", NULL);
        g_pd->sprite->setImage(bullet_pool[i].sprite, bmp, kBitmapUnflipped);
        g_pd->graphics->freeBitmap(bmp);

        g_pd->sprite->setVisible(bullet_pool[i].sprite, 0);
    }

    pool_initialized = 1;
}

Bullet* bullet_spawn(float x, float y, float vel_x, float vel_y) {
    for (int i = 0; i < BULLET_POOL_SIZE; i++) {
        if (!bullet_pool[i].active) {
            bullet_pool[i].x = x;
            bullet_pool[i].y = y;
            bullet_pool[i].vel_x = vel_x;
            bullet_pool[i].vel_y = vel_y;
            bullet_pool[i].active = 1;

            g_pd->sprite->moveTo(bullet_pool[i].sprite, x, y);
            g_pd->sprite->setVisible(bullet_pool[i].sprite, 1);

            return &bullet_pool[i];
        }
    }
    return NULL;  // Pool exhausted
}

void bullet_despawn(Bullet* bullet) {
    if (!bullet) return;
    bullet->active = 0;
    g_pd->sprite->setVisible(bullet->sprite, 0);
}

void bullet_update_all(float dt) {
    for (int i = 0; i < BULLET_POOL_SIZE; i++) {
        if (!bullet_pool[i].active) continue;

        bullet_pool[i].x += bullet_pool[i].vel_x * dt;
        bullet_pool[i].y += bullet_pool[i].vel_y * dt;

        g_pd->sprite->moveTo(bullet_pool[i].sprite,
                             bullet_pool[i].x,
                             bullet_pool[i].y);

        // Remove if off-screen
        if (bullet_pool[i].x < -10 || bullet_pool[i].x > 410 ||
            bullet_pool[i].y < -10 || bullet_pool[i].y > 250) {
            bullet_despawn(&bullet_pool[i]);
        }
    }
}
```

## Profiling

### Timing Sections

```c
#define PROFILE_START(name) \
    unsigned int _profile_##name = g_pd->system->getCurrentTimeMilliseconds()

#define PROFILE_END(name) \
    g_pd->system->logToConsole(#name ": %u ms", \
        g_pd->system->getCurrentTimeMilliseconds() - _profile_##name)

void game_update(void* userdata) {
    PROFILE_START(update);
    update_logic();
    PROFILE_END(update);

    PROFILE_START(draw);
    draw_game();
    PROFILE_END(draw);

    return 1;
}
```

### FPS Display

```c
// Built-in FPS counter
g_pd->system->drawFPS(0, 0);

// Custom with more detail
static int frame_count = 0;
static unsigned int last_fps_time = 0;
static int last_fps = 0;

void display_fps(void) {
    frame_count++;
    unsigned int now = g_pd->system->getCurrentTimeMilliseconds();

    if (now - last_fps_time >= 1000) {
        last_fps = frame_count;
        frame_count = 0;
        last_fps_time = now;
    }

    char fps_text[16];
    sprintf(fps_text, "FPS: %d", last_fps);
    g_pd->graphics->drawText(fps_text, strlen(fps_text), kASCIIEncoding, 0, 0);
}
```

## Common Bottlenecks

### 1. Full Screen Clear Every Frame

```c
// Slow
g_pd->graphics->clear(kColorWhite);

// Better: Use sprite system or dirty rects
```

### 2. Loading Assets Every Frame

```c
// Slow
void draw(void) {
    LCDBitmap* bmp = g_pd->graphics->loadBitmap("image", NULL);
    // ...
    g_pd->graphics->freeBitmap(bmp);
}

// Better: Cache at init
static LCDBitmap* cached_bmp = NULL;
void init(void) {
    cached_bmp = g_pd->graphics->loadBitmap("image", NULL);
}
```

### 3. String Operations

```c
// Slow: String formatting every frame
sprintf(buffer, "Score: %d", score);

// Better: Only update when score changes
static int last_score = -1;
if (score != last_score) {
    sprintf(score_buffer, "Score: %d", score);
    last_score = score;
}
```

### 4. Complex Collision Detection

```c
// Slow: Check every pair
for (int i = 0; i < n; i++) {
    for (int j = i + 1; j < n; j++) {
        check_collision(i, j);
    }
}

// Better: Use spatial partitioning or sprite system's built-in collision
```

## Optimization Checklist

- [ ] Using 30 FPS unless more is needed
- [ ] Not clearing full screen every frame
- [ ] Assets loaded at init, not per-frame
- [ ] Using object pools for bullets/particles
- [ ] Sprite system handles drawing when possible
- [ ] No allocations in update loop
- [ ] String buffers pre-allocated
- [ ] Profiling identifies actual bottlenecks
