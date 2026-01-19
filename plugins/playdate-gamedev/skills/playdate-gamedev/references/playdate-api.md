# Playdate API Patterns

Comprehensive API usage patterns for Playdate SDK.

## Graphics

### Basic Drawing

```c
// Clear screen
g_pd->graphics->clear(kColorWhite);  // or kColorBlack

// Lines
g_pd->graphics->drawLine(0, 0, 100, 100, 2, kColorBlack);  // width=2

// Rectangles
g_pd->graphics->fillRect(50, 50, 100, 100, kColorBlack);   // Filled
g_pd->graphics->drawRect(50, 50, 100, 100, kColorBlack);   // Outline

// Circles/Ellipses
g_pd->graphics->fillEllipse(200, 120, 50, 50, 0, 360, kColorBlack);

// Text
g_pd->graphics->drawText("Hello Playdate!", strlen("Hello Playdate!"),
                         kASCIIEncoding, 10, 10);
```

### Bitmap Drawing

```c
void draw_bitmap(const char* path, int x, int y) {
    const char* err = NULL;
    LCDBitmap* bitmap = g_pd->graphics->loadBitmap(path, &err);

    if (bitmap) {
        g_pd->graphics->drawBitmap(bitmap, x, y, kBitmapUnflipped);
        g_pd->graphics->freeBitmap(bitmap);
    } else {
        g_pd->system->logToConsole("Failed to load bitmap: %s", err);
    }
}

// Flip modes: kBitmapUnflipped, kBitmapFlippedX, kBitmapFlippedY, kBitmapFlippedXY
```

### Drawing Modes

```c
// Set draw mode
g_pd->graphics->setDrawMode(kDrawModeCopy);      // Default
g_pd->graphics->setDrawMode(kDrawModeInverted);  // Invert colors
g_pd->graphics->setDrawMode(kDrawModeXOR);       // XOR blend
```

## Sprites

### Basic Sprite Management

```c
typedef struct {
    LCDSprite* sprite;
    float x, y;
    float vel_x, vel_y;
} GameObject;

GameObject* gameobject_create(const char* image_path) {
    GameObject* obj = g_pd->system->realloc(NULL, sizeof(GameObject));
    if (!obj) return NULL;

    // Create sprite
    obj->sprite = g_pd->sprite->newSprite();

    // Load and set bitmap
    LCDBitmap* bitmap = g_pd->graphics->loadBitmap(image_path, NULL);
    if (bitmap) {
        g_pd->sprite->setImage(obj->sprite, bitmap, kBitmapUnflipped);
        g_pd->graphics->freeBitmap(bitmap);  // Sprite keeps copy
    }

    // Set collision rect
    PDRect bounds = { 0, 0, 32, 32 };
    g_pd->sprite->setCollideRect(obj->sprite, bounds);

    // Add to sprite list (auto draw/collision)
    g_pd->sprite->addSprite(obj->sprite);

    obj->x = 0;
    obj->y = 0;
    obj->vel_x = 0;
    obj->vel_y = 0;

    return obj;
}

void gameobject_update(GameObject* obj, float dt) {
    if (!obj) return;

    obj->x += obj->vel_x * dt;
    obj->y += obj->vel_y * dt;

    g_pd->sprite->moveTo(obj->sprite, obj->x, obj->y);
}

void gameobject_destroy(GameObject* obj) {
    if (!obj) return;

    if (obj->sprite) {
        g_pd->sprite->removeSprite(obj->sprite);
        g_pd->sprite->freeSprite(obj->sprite);
    }
    g_pd->system->realloc(obj, 0);
}
```

### Sprite Collision

```c
// Collision response callback
static SpriteCollisionResponseType collision_response(
    LCDSprite* sprite1,
    LCDSprite* sprite2,
    void* userdata
) {
    (void)userdata;

    // Response types:
    // kCollisionTypeSlide   - Slide along collision
    // kCollisionTypeBounce  - Bounce off
    // kCollisionTypeFreeze  - Stop movement
    // kCollisionTypeOverlap - Allow overlap (detection only)

    return kCollisionTypeSlide;
}

void setup_collision(void) {
    g_pd->sprite->setCollisionResponseFunction(collision_response);
}

// Update with collision
void update_with_collision(void) {
    // Move all sprites with collision
    g_pd->sprite->moveSprites();

    // Or check individual sprite
    int count = 0;
    SpriteCollisionInfo* collisions = g_pd->sprite->checkCollisions(
        player_sprite, 0, 0, NULL, &count
    );

    for (int i = 0; i < count; i++) {
        g_pd->system->logToConsole("Collision at (%.2f, %.2f)",
                                   collisions[i].move.x,
                                   collisions[i].move.y);
    }
}
```

### Z-Ordering

```c
g_pd->sprite->setZIndex(foreground_sprite, 10);  // Draw on top
g_pd->sprite->setZIndex(player_sprite, 5);       // Middle
g_pd->sprite->setZIndex(background_sprite, 0);   // Draw first
```

## Input

### Button Input

```c
void handle_input(void) {
    PDButtons current, pushed, released;
    g_pd->system->getButtonState(&current, &pushed, &released);

    // Held down
    if (current & kButtonA) {
        // A button is held
    }

    // Just pressed
    if (pushed & kButtonB) {
        // B button just pressed this frame
    }

    // Just released
    if (released & kButtonUp) {
        // Up button just released
    }

    // Multiple buttons
    if ((current & kButtonA) && (current & kButtonB)) {
        // A and B both held
    }
}

// Button constants:
// kButtonLeft, kButtonRight, kButtonUp, kButtonDown
// kButtonA, kButtonB
```

### Crank Input

```c
void handle_crank(void) {
    // Check if docked
    if (g_pd->system->isCrankDocked()) {
        return;  // Crank is stored
    }

    // Absolute angle (0-360 degrees)
    float angle = g_pd->system->getCrankAngle();

    // Change since last frame (degrees)
    float change = g_pd->system->getCrankChange();

    // Use for rotation controls, scrolling, etc.
}
```

### Accelerometer

```c
void handle_accelerometer(void) {
    float ax, ay, az;
    g_pd->system->getAccelerometer(&ax, &ay, &az);

    // Values range from -1.0 to 1.0
    // Use for tilt controls
}
```

## Sound

### Sound Effects (SamplePlayer)

```c
void play_sound_effect(const char* path) {
    const char* err = NULL;
    SamplePlayer* player = g_pd->sound->sampleplayer->newPlayer();

    AudioSample* sample = g_pd->sound->sample->load(path, &err);
    if (!sample) {
        g_pd->system->logToConsole("Failed to load sound: %s", err);
        return;
    }

    g_pd->sound->sampleplayer->setSample(player, sample);
    g_pd->sound->sampleplayer->play(player, 1, 1.0f);  // repeat=1, rate=1.0
}
```

### Background Music (FilePlayer)

```c
static FilePlayer* bgm_player = NULL;

void play_bgm(const char* path) {
    if (!bgm_player) {
        bgm_player = g_pd->sound->fileplayer->newPlayer();
    }

    g_pd->sound->fileplayer->loadIntoPlayer(bgm_player, path);
    g_pd->sound->fileplayer->play(bgm_player, 0);  // 0 = loop forever
}

void stop_bgm(void) {
    if (bgm_player) {
        g_pd->sound->fileplayer->stop(bgm_player);
    }
}

void set_bgm_volume(float volume) {
    if (bgm_player) {
        g_pd->sound->fileplayer->setVolume(bgm_player, volume, volume);
    }
}
```

## File I/O

### Binary File Write

```c
void save_game(int score, int level) {
    SDFile* file = g_pd->file->open("save.dat", kFileWrite);
    if (!file) {
        g_pd->system->error("Failed to open file for writing");
        return;
    }

    g_pd->file->write(file, &score, sizeof(int));
    g_pd->file->write(file, &level, sizeof(int));
    g_pd->file->close(file);
}
```

### Binary File Read

```c
int load_game(int* score, int* level) {
    SDFile* file = g_pd->file->open("save.dat", kFileRead);
    if (!file) {
        return 0;  // No save file
    }

    g_pd->file->read(file, score, sizeof(int));
    g_pd->file->read(file, level, sizeof(int));
    g_pd->file->close(file);

    return 1;  // Success
}
```

### Text File Read

```c
char* read_text_file(const char* path) {
    SDFile* file = g_pd->file->open(path, kFileRead);
    if (!file) return NULL;

    // Get file size
    g_pd->file->seek(file, 0, SEEK_END);
    int size = g_pd->file->tell(file);
    g_pd->file->seek(file, 0, SEEK_SET);

    // Allocate buffer
    char* buffer = g_pd->system->realloc(NULL, size + 1);
    g_pd->file->read(file, buffer, size);
    buffer[size] = '\0';
    g_pd->file->close(file);

    return buffer;  // Caller must free
}
```

## System

### Timing

```c
// Get current time in milliseconds
unsigned int now = g_pd->system->getCurrentTimeMilliseconds();

// Measure execution time
unsigned int start = g_pd->system->getCurrentTimeMilliseconds();
// ... expensive operation ...
unsigned int elapsed = g_pd->system->getCurrentTimeMilliseconds() - start;
g_pd->system->logToConsole("Took %u ms", elapsed);
```

### FPS Control

```c
// Set refresh rate (default 30, max 50)
g_pd->display->setRefreshRate(30.0f);

// Display FPS counter
g_pd->system->drawFPS(0, 0);
```

### Dirty Rectangles

```c
// Mark specific rows for redraw (optimization)
g_pd->graphics->markUpdatedRows(start_y, end_y);
```

## Menu System

```c
// Add menu item
PDMenuItem* menu_item = g_pd->system->addMenuItem(
    "Option", menu_callback, NULL
);

// Callback function
void menu_callback(void* userdata) {
    g_pd->system->logToConsole("Menu item selected");
}

// Remove menu item
g_pd->system->removeMenuItem(menu_item);
```
