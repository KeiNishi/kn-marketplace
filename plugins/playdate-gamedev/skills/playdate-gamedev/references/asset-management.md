# Asset Management

Asset handling, formats, and animations for Playdate games.

## Image Assets

### Supported Formats

- **PNG**: Recommended, auto-converted to 1-bit
- **GIF**: Supported, including animated GIFs

### Size Recommendations

- **Sprites**: 32x32, 64x64 (power of 2 preferred)
- **Background**: 400x240 (full screen)
- **Tiles**: 16x16, 32x32 for tile maps

### Dithering

Playdate displays 1-bit (black and white) only. Grayscale images are automatically dithered during build.

### Directory Structure

```
Source/
└── images/          # Assets copied to build
    ├── player.png
    ├── enemy.png
    └── tileset.png
```

### Loading Images

```c
// Path without extension (SDK adds it)
LCDBitmap* bitmap = g_pd->graphics->loadBitmap("images/player", NULL);

if (bitmap) {
    g_pd->graphics->drawBitmap(bitmap, x, y, kBitmapUnflipped);
    g_pd->graphics->freeBitmap(bitmap);
}
```

## Sprite Sheets / Animations

### Bitmap Table Format

Create image files named with `-table-W-H` suffix:
- `player-table-32-32.png` for 32x32 frames

### Loading Sprite Sheets

```c
typedef struct {
    LCDBitmapTable* bitmap_table;
    LCDSprite* sprite;
    int current_frame;
    int frame_count;
    float frame_time;      // Seconds per frame
    float elapsed;
} AnimatedSprite;

AnimatedSprite* animated_sprite_create(const char* table_path) {
    AnimatedSprite* anim = g_pd->system->realloc(NULL, sizeof(AnimatedSprite));
    if (!anim) return NULL;

    const char* err = NULL;
    anim->bitmap_table = g_pd->graphics->loadBitmapTable(table_path, &err);
    if (!anim->bitmap_table) {
        g_pd->system->logToConsole("Failed to load bitmap table: %s", err);
        g_pd->system->realloc(anim, 0);
        return NULL;
    }

    anim->frame_count = g_pd->graphics->getTableBitmapCount(anim->bitmap_table);
    anim->current_frame = 0;
    anim->frame_time = 1.0f / 10.0f;  // 10 FPS animation
    anim->elapsed = 0;

    anim->sprite = g_pd->sprite->newSprite();
    LCDBitmap* first_frame = g_pd->graphics->getTableBitmap(
        anim->bitmap_table, 0
    );
    g_pd->sprite->setImage(anim->sprite, first_frame, kBitmapUnflipped);

    return anim;
}

void animated_sprite_update(AnimatedSprite* anim, float dt) {
    if (!anim) return;

    anim->elapsed += dt;
    if (anim->elapsed >= anim->frame_time) {
        anim->elapsed = 0;
        anim->current_frame = (anim->current_frame + 1) % anim->frame_count;

        LCDBitmap* frame = g_pd->graphics->getTableBitmap(
            anim->bitmap_table, anim->current_frame
        );
        g_pd->sprite->setImage(anim->sprite, frame, kBitmapUnflipped);
    }
}

void animated_sprite_destroy(AnimatedSprite* anim) {
    if (!anim) return;

    if (anim->sprite) {
        g_pd->sprite->freeSprite(anim->sprite);
    }
    if (anim->bitmap_table) {
        g_pd->graphics->freeBitmapTable(anim->bitmap_table);
    }
    g_pd->system->realloc(anim, 0);
}
```

### Animation State Machine

```c
typedef enum {
    ANIM_IDLE,
    ANIM_WALK,
    ANIM_JUMP,
    ANIM_ATTACK
} AnimationState;

typedef struct {
    AnimationState state;
    LCDBitmapTable* tables[4];  // One per state
    int frame_counts[4];
    float frame_times[4];
    int current_frame;
    float elapsed;
    LCDSprite* sprite;
} AnimatedCharacter;

void animated_character_set_state(AnimatedCharacter* c, AnimationState state) {
    if (c->state == state) return;

    c->state = state;
    c->current_frame = 0;
    c->elapsed = 0;

    // Set first frame of new animation
    LCDBitmap* frame = g_pd->graphics->getTableBitmap(
        c->tables[state], 0
    );
    g_pd->sprite->setImage(c->sprite, frame, kBitmapUnflipped);
}
```

## Audio Assets

### Sound Effects (WAV)

- **Format**: WAV, PCM 16-bit
- **Sample Rate**: 22050Hz or 44100Hz
- **Channels**: Mono recommended for effects
- **Size**: Keep small for memory

### Background Music (MP3)

- **Format**: MP3
- **Bitrate**: 128kbps recommended
- **Channels**: Stereo supported

### Directory Structure

```
Source/
└── sounds/
    ├── jump.wav        # Effect
    ├── hit.wav         # Effect
    └── bgm.mp3         # Music
```

### Preloading Audio

```c
// Preload frequently used samples
static AudioSample* sfx_jump = NULL;
static AudioSample* sfx_hit = NULL;
static SamplePlayer* sfx_player = NULL;

void audio_init(void) {
    sfx_jump = g_pd->sound->sample->load("sounds/jump", NULL);
    sfx_hit = g_pd->sound->sample->load("sounds/hit", NULL);
    sfx_player = g_pd->sound->sampleplayer->newPlayer();
}

void audio_play(AudioSample* sample) {
    g_pd->sound->sampleplayer->setSample(sfx_player, sample);
    g_pd->sound->sampleplayer->play(sfx_player, 1, 1.0f);
}

void audio_cleanup(void) {
    if (sfx_jump) g_pd->sound->sample->freeSample(sfx_jump);
    if (sfx_hit) g_pd->sound->sample->freeSample(sfx_hit);
    if (sfx_player) g_pd->sound->sampleplayer->freePlayer(sfx_player);
}
```

## Fonts

### Custom Bitmap Fonts

Create a folder with individual character images:

```
Source/
└── fonts/
    └── MyFont/
        ├── A.png
        ├── B.png
        ├── C.png
        └── ...
```

### Loading Custom Fonts

```c
LCDFont* custom_font = NULL;

void font_init(void) {
    custom_font = g_pd->graphics->loadFont("fonts/MyFont", NULL);
}

void draw_with_font(const char* text, int x, int y) {
    if (custom_font) {
        g_pd->graphics->setFont(custom_font);
    }
    g_pd->graphics->drawText(text, strlen(text), kASCIIEncoding, x, y);
}
```

## Asset Loading Strategies

### Lazy Loading

Load assets only when needed:

```c
static LCDBitmap* cached_bitmap = NULL;

LCDBitmap* get_bitmap(void) {
    if (!cached_bitmap) {
        cached_bitmap = g_pd->graphics->loadBitmap("images/large", NULL);
    }
    return cached_bitmap;
}
```

### Level-Based Loading

Load/unload assets per level:

```c
typedef struct {
    LCDBitmap* background;
    LCDBitmap* tileset;
    AudioSample* bgm;
} LevelAssets;

static LevelAssets current_level = {0};

void load_level_assets(int level) {
    char path[64];

    // Unload previous
    unload_level_assets();

    // Load new
    sprintf(path, "levels/%d/background", level);
    current_level.background = g_pd->graphics->loadBitmap(path, NULL);

    sprintf(path, "levels/%d/tileset", level);
    current_level.tileset = g_pd->graphics->loadBitmap(path, NULL);
}

void unload_level_assets(void) {
    if (current_level.background) {
        g_pd->graphics->freeBitmap(current_level.background);
        current_level.background = NULL;
    }
    // ... unload others
}
```

### Asset Manifest

Use a simple manifest for organized loading:

```c
typedef struct {
    const char* name;
    const char* path;
    LCDBitmap** target;
} AssetEntry;

static LCDBitmap* bmp_player = NULL;
static LCDBitmap* bmp_enemy = NULL;

static AssetEntry assets[] = {
    { "player", "images/player", &bmp_player },
    { "enemy", "images/enemy", &bmp_enemy },
    { NULL, NULL, NULL }  // Terminator
};

void load_all_assets(void) {
    for (int i = 0; assets[i].name != NULL; i++) {
        *assets[i].target = g_pd->graphics->loadBitmap(
            assets[i].path, NULL
        );
        if (!*assets[i].target) {
            g_pd->system->logToConsole("Failed to load: %s", assets[i].name);
        }
    }
}
```
