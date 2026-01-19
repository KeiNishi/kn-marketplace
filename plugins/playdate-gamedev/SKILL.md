---
name: playdate-gamedev
description: Playdate C言語ゲーム開発の包括的ガイド。プロジェクト初期化、ビルドフロー、コーディング規約、Playdate API使用パターン、アセット管理、パフォーマンス最適化を含む。初心者から経験者まで対応。Playdateのゲームプロジェクトの実装計画・実装・コードレビューをするときに必ず参照すること。
---

# Playdate Game Development Guide

Playdate向けC言語ゲーム開発の包括的なガイド。高速かつ可読性の高いコードを実現するためのベストプラクティス集。

## 前提条件

- Playdate SDK がインストールされていること
- 環境変数 `PLAYDATE_SDK_PATH` が設定されていること
- C言語の基礎知識

---

## プロジェクト構造

### 推奨ディレクトリ構成

```
YourGame/
├── Source/                    # ソースコード
│   ├── main.c                # エントリーポイント
│   ├── game.c/h              # ゲームロジック
│   ├── player.c/h            # プレイヤー
│   ├── enemy.c/h             # 敵
│   ├── utils.c/h             # ユーティリティ
│   └── assets/               # ソースから参照するアセット
├── assets/                   # 生アセット（ビルド前）
│   ├── images/
│   │   ├── player.png
│   │   └── tileset.png
│   ├── sounds/
│   │   ├── bgm.wav
│   │   └── sfx/
│   └── fonts/
│       └── custom-font/
├── builds/                   # ビルド成果物（gitignore推奨）
├── Makefile                  # ビルド設定
├── pdxinfo                   # ゲームメタデータ
└── README.md
```

### pdxinfo テンプレート

```ini
# pdxinfo - ゲームのメタデータ
name=Your Game Name
author=Your Name
description=Game description
bundleID=com.yourname.yourgame
version=1.0
buildNumber=1
imagePath=assets/images/
```

### Makefile テンプレート

```makefile
# Playdate SDK path
SDK = ${PLAYDATE_SDK_PATH}

# ゲーム名（.pdxが作成される）
GAME = YourGame

# ソースファイル
SRC = Source/main.c \
      Source/game.c \
      Source/player.c \
      Source/enemy.c \
      Source/utils.c

# インクルードパス
INCLUDE = -ISource

# コンパイラフラグ
CFLAGS = -O2 -Wall -Wextra -Werror

# Playdate SDK の Makefile をインクルード
include $(SDK)/C_API/buildsupport/common.mk
```

### プロジェクト初期化コマンド

```bash
# 新規プロジェクト作成
mkdir -p YourGame/{Source,assets/{images,sounds,fonts},builds}
cd YourGame

# pdxinfo作成
cat > pdxinfo << 'EOF'
name=YourGame
author=YourName
description=A Playdate Game
bundleID=com.yourname.yourgame
version=1.0
buildNumber=1
imagePath=assets/images/
EOF

# 基本Makefile作成（上記テンプレート参照）

# main.c作成（後述のテンプレート参照）
```

---

## コーディング規約

### 命名規則

```c
// グローバル定数: SCREAMING_SNAKE_CASE
#define MAX_ENEMIES 100
#define SCREEN_WIDTH 400

// 型定義: PascalCase
typedef struct {
    float x;
    float y;
} Vector2;

typedef struct Player {
    Vector2 position;
    int health;
} Player;

// 関数: snake_case
void init_game(void);
void update_player(Player* player, float dt);
static void handle_collision(void);  // static は内部関数

// 変数: snake_case
int enemy_count = 0;
float delta_time = 0.0f;
Player* player = NULL;

// グローバル変数: g_プレフィックス（推奨）
static PlaydateAPI* g_pd = NULL;
static Player* g_player = NULL;
```

### ファイル構成パターン

**ヘッダーファイル (.h)**

```c
// player.h
#ifndef PLAYER_H
#define PLAYER_H

#include "pd_api.h"

// 型定義
typedef struct Player Player;

// 公開API
Player* player_create(float x, float y);
void player_destroy(Player* player);
void player_update(Player* player, float dt);
void player_draw(Player* player);

#endif // PLAYER_H
```

**実装ファイル (.c)**

```c
// player.c
#include "player.h"
#include <stdlib.h>

// 構造体の実装（ヘッダーでは前方宣言のみ）
struct Player {
    float x;
    float y;
    int health;
    LCDSprite* sprite;
};

// グローバルPlaydateAPI（main.cで初期化）
extern PlaydateAPI* g_pd;

// 生成
Player* player_create(float x, float y) {
    Player* player = g_pd->system->realloc(NULL, sizeof(Player));
    if (!player) return NULL;

    player->x = x;
    player->y = y;
    player->health = 100;
    player->sprite = g_pd->sprite->newSprite();

    return player;
}

// 破棄
void player_destroy(Player* player) {
    if (!player) return;

    if (player->sprite) {
        g_pd->sprite->freeSprite(player->sprite);
    }
    g_pd->system->realloc(player, 0);
}

// 更新
void player_update(Player* player, float dt) {
    if (!player) return;

    // プレイヤーロジック
    PDButtons current, pushed, released;
    g_pd->system->getButtonState(&current, &pushed, &released);

    if (current & kButtonLeft) {
        player->x -= 100.0f * dt;
    }
    if (current & kButtonRight) {
        player->x += 100.0f * dt;
    }
}

// 描画
void player_draw(Player* player) {
    if (!player || !player->sprite) return;

    g_pd->sprite->moveTo(player->sprite, player->x, player->y);
    g_pd->sprite->drawSprite(player->sprite, (int)player->x, (int)player->y);
}
```

### エラーハンドリング

```c
// ✅ 良い例：NULLチェックと早期リターン
void update_entity(Entity* entity, float dt) {
    if (!entity) {
        g_pd->system->logToConsole("ERROR: entity is NULL");
        return;
    }

    // 処理
}

// ✅ 良い例：リソース割り当て失敗のチェック
Enemy* enemy_create(void) {
    Enemy* enemy = g_pd->system->realloc(NULL, sizeof(Enemy));
    if (!enemy) {
        g_pd->system->error("Failed to allocate memory for enemy");
        return NULL;
    }

    enemy->sprite = g_pd->sprite->newSprite();
    if (!enemy->sprite) {
        g_pd->system->realloc(enemy, 0);  // メモリ解放
        g_pd->system->error("Failed to create sprite");
        return NULL;
    }

    return enemy;
}

// ✅ 良い例：アサーション（開発時のみ）
#ifdef DEBUG
#define ASSERT(condition, message) \
    if (!(condition)) { \
        g_pd->system->error("ASSERTION FAILED: %s", message); \
    }
#else
#define ASSERT(condition, message)
#endif
```

---

## ビルド・実行フロー

### Simulator用ビルド

```bash
# ビルド
make

# Simulator起動
open builds/YourGame.pdx  # macOS
# または
"${PLAYDATE_SDK_PATH}/bin/PlaydateSimulator" builds/YourGame.pdx  # Windows/Linux
```

### デバイス用ビルド

```bash
# デバイス用にビルド（最適化有効）
make DEVICE=1

# デバイスにサイドロード
# Playdate デバイスをUSB接続して、Simulator経由でアップロード
```

### クリーンビルド

```bash
make clean
make
```

### デバッグログ出力

```c
// ログ出力
g_pd->system->logToConsole("Player position: %.2f, %.2f", player->x, player->y);

// エラー出力（実行停止）
g_pd->system->error("Fatal error occurred");

// デバッグビルドのみログ出力
#ifdef DEBUG
g_pd->system->logToConsole("Debug info: %d", value);
#endif
```

---

## Playdate API 使用パターン

### main.c エントリーポイント

```c
// main.c
#include "pd_api.h"
#include "game.h"

// グローバルPlaydateAPI（他のファイルからextern参照）
PlaydateAPI* g_pd = NULL;

#ifdef _WINDLL
__declspec(dllexport)
#endif
int eventHandler(PlaydateAPI* pd, PDSystemEvent event, uint32_t arg) {
    (void)arg;  // 未使用パラメータを明示

    if (event == kEventInit) {
        g_pd = pd;

        // FPS設定（デフォルトは30fps、最大50fps推奨）
        pd->display->setRefreshRate(30.0f);

        // ゲーム初期化
        game_init();

        // 更新コールバック設定
        pd->system->setUpdateCallback(game_update, NULL);
    }

    return 0;
}
```

### ゲームループパターン

```c
// game.c
#include "game.h"
#include "player.h"
#include "enemy.h"

static Player* player = NULL;
static Enemy* enemies[MAX_ENEMIES];
static int enemy_count = 0;

void game_init(void) {
    // プレイヤー生成
    player = player_create(200.0f, 120.0f);

    // 敵生成
    for (int i = 0; i < 10; i++) {
        enemies[i] = enemy_create(rand() % 400, rand() % 240);
        enemy_count++;
    }
}

int game_update(void* userdata) {
    (void)userdata;

    // デルタタイム取得（秒単位）
    float dt = 1.0f / 30.0f;  // 30fps想定

    // クリア
    g_pd->graphics->clear(kColorWhite);

    // 更新
    player_update(player, dt);
    for (int i = 0; i < enemy_count; i++) {
        enemy_update(enemies[i], dt);
    }

    // 描画
    player_draw(player);
    for (int i = 0; i < enemy_count; i++) {
        enemy_draw(enemies[i]);
    }

    // FPS表示（デバッグ用）
    g_pd->system->drawFPS(0, 0);

    return 1;  // 1を返すと次フレームも呼ばれる
}
```

### グラフィックス描画

```c
// 基本的な図形描画
void draw_shapes(void) {
    // 線
    g_pd->graphics->drawLine(0, 0, 100, 100, 2, kColorBlack);

    // 矩形（塗りつぶし）
    g_pd->graphics->fillRect(50, 50, 100, 100, kColorBlack);

    // 矩形（枠線のみ）
    g_pd->graphics->drawRect(50, 50, 100, 100, kColorBlack);

    // 円（塗りつぶし）
    g_pd->graphics->fillEllipse(200, 120, 50, 50, 0, 360, kColorBlack);

    // テキスト
    g_pd->graphics->drawText("Hello Playdate!", strlen("Hello Playdate!"),
                             kASCIIEncoding, 10, 10);
}

// ビットマップ描画
void draw_bitmap(void) {
    const char* err = NULL;
    LCDBitmap* bitmap = g_pd->graphics->loadBitmap("images/player", &err);

    if (bitmap) {
        g_pd->graphics->drawBitmap(bitmap, 100, 100, kBitmapUnflipped);
        g_pd->graphics->freeBitmap(bitmap);
    } else {
        g_pd->system->logToConsole("Failed to load bitmap: %s", err);
    }
}
```

### スプライト管理

```c
// スプライト生成・管理
typedef struct {
    LCDSprite* sprite;
    float x;
    float y;
    float vel_x;
    float vel_y;
} GameObject;

GameObject* gameobject_create(const char* image_path) {
    GameObject* obj = g_pd->system->realloc(NULL, sizeof(GameObject));
    if (!obj) return NULL;

    // スプライト生成
    obj->sprite = g_pd->sprite->newSprite();

    // ビットマップ読み込み
    LCDBitmap* bitmap = g_pd->graphics->loadBitmap(image_path, NULL);
    if (bitmap) {
        g_pd->sprite->setImage(obj->sprite, bitmap, kBitmapUnflipped);
        g_pd->graphics->freeBitmap(bitmap);  // スプライトにコピー済み
    }

    // 衝突判定矩形設定
    g_pd->sprite->setCollideRect(obj->sprite, PDRect{0, 0, 32, 32});

    // スプライトリストに追加（自動描画・衝突判定）
    g_pd->sprite->addSprite(obj->sprite);

    obj->x = 0;
    obj->y = 0;
    obj->vel_x = 0;
    obj->vel_y = 0;

    return obj;
}

void gameobject_update(GameObject* obj, float dt) {
    if (!obj) return;

    // 位置更新
    obj->x += obj->vel_x * dt;
    obj->y += obj->vel_y * dt;

    // スプライト位置更新
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

### スプライト衝突判定

```c
// 衝突判定コールバック
static SpriteCollisionResponseType collision_response(
    LCDSprite* sprite1,
    LCDSprite* sprite2,
    void* userdata
) {
    (void)userdata;

    g_pd->system->logToConsole("Collision detected!");

    // kCollisionTypeSlide: スライドして衝突回避
    // kCollisionTypeBounce: 跳ね返る
    // kCollisionTypeFreeze: 停止
    // kCollisionTypeOverlap: 重なりを許可（衝突検出のみ）
    return kCollisionTypeSlide;
}

void setup_collision(void) {
    // 衝突判定コールバック設定
    g_pd->sprite->setCollisionResponseFunction(collision_response);
}

void update_with_collision(void) {
    // 全スプライトの衝突判定を実行
    g_pd->sprite->moveSprites();

    // または個別にチェック
    int len = 0;
    SpriteCollisionInfo* collisions = g_pd->sprite->checkCollisions(
        player_sprite, 0, 0, NULL, &len
    );

    for (int i = 0; i < len; i++) {
        // 衝突処理
        g_pd->system->logToConsole("Hit sprite at (%.2f, %.2f)",
                                   collisions[i].move.x,
                                   collisions[i].move.y);
    }
}
```

### 入力処理

```c
// ボタン入力
void handle_input(void) {
    PDButtons current, pushed, released;
    g_pd->system->getButtonState(&current, &pushed, &released);

    // 押しっぱなし判定
    if (current & kButtonA) {
        // Aボタンが押されている
    }

    // 押した瞬間判定
    if (pushed & kButtonB) {
        // Bボタンが押された
    }

    // 離した瞬間判定
    if (released & kButtonUp) {
        // 上ボタンが離された
    }

    // 複合入力
    if ((current & kButtonA) && (current & kButtonB)) {
        // AとBが同時に押されている
    }
}

// クランク入力
void handle_crank(void) {
    // クランクがドックされているか
    if (g_pd->system->isCrankDocked()) {
        g_pd->system->logToConsole("Crank is docked");
        return;
    }

    // クランクの絶対角度（0-360度）
    float angle = g_pd->system->getCrankAngle();

    // クランクの変化量（度/秒）
    float change = g_pd->system->getCrankChange();

    g_pd->system->logToConsole("Crank angle: %.2f, change: %.2f",
                               angle, change);
}

// 加速度センサー
void handle_accelerometer(void) {
    float ax, ay, az;
    g_pd->system->getAccelerometer(&ax, &ay, &az);

    g_pd->system->logToConsole("Accel: %.2f, %.2f, %.2f", ax, ay, az);
}
```

### サウンド

```c
// 効果音再生
void play_sound_effect(void) {
    const char* err = NULL;
    SamplePlayer* player = g_pd->sound->sampleplayer->newPlayer();

    AudioSample* sample = g_pd->sound->sample->load("sounds/jump", &err);
    if (!sample) {
        g_pd->system->logToConsole("Failed to load sound: %s", err);
        return;
    }

    g_pd->sound->sampleplayer->setSample(player, sample);
    g_pd->sound->sampleplayer->play(player, 1, 1.0f);  // repeat=1, rate=1.0
}

// BGM再生（FilePlayer使用）
static FilePlayer* bgm_player = NULL;

void play_bgm(const char* path) {
    if (!bgm_player) {
        bgm_player = g_pd->sound->fileplayer->newPlayer();
    }

    g_pd->sound->fileplayer->loadIntoPlayer(bgm_player, path);
    g_pd->sound->fileplayer->play(bgm_player, 0);  // 0 = ループ再生
}

void stop_bgm(void) {
    if (bgm_player) {
        g_pd->sound->fileplayer->stop(bgm_player);
    }
}
```

### ファイルI/O

```c
// ファイル書き込み
void save_game(int score) {
    SDFile* file = g_pd->file->open("save.dat", kFileWrite);
    if (!file) {
        g_pd->system->error("Failed to open file for writing");
        return;
    }

    g_pd->file->write(file, &score, sizeof(int));
    g_pd->file->close(file);
}

// ファイル読み込み
int load_game(void) {
    SDFile* file = g_pd->file->open("save.dat", kFileRead);
    if (!file) {
        g_pd->system->logToConsole("Save file not found");
        return 0;
    }

    int score = 0;
    g_pd->file->read(file, &score, sizeof(int));
    g_pd->file->close(file);

    return score;
}

// JSON読み込み（設定ファイルなど）
void load_config(void) {
    SDFile* file = g_pd->file->open("config.json", kFileRead);
    if (!file) return;

    // ファイルサイズ取得
    g_pd->file->seek(file, 0, SEEK_END);
    int size = g_pd->file->tell(file);
    g_pd->file->seek(file, 0, SEEK_SET);

    // バッファ確保
    char* buffer = g_pd->system->realloc(NULL, size + 1);
    g_pd->file->read(file, buffer, size);
    buffer[size] = '\0';
    g_pd->file->close(file);

    // JSON解析
    json_decoder decoder = {0};
    json_value value = json_decode(buffer, &decoder);

    // 使用後解放
    g_pd->system->realloc(buffer, 0);
}
```

---

## アセット管理

### 画像ファイル

```bash
# PNG/GIF画像を Playdate形式に変換
# Playdate SDK の pdc コマンドが自動変換

# 推奨サイズ
# - スプライト: 32x32, 64x64 など2の累乗
# - 背景: 400x240（画面全体）

# ディザリング
# - 1bit（白黒）のみサポート
# - グレースケールPNGは自動的にディザリング変換される
```

**アセット配置**

```
Source/
└── images/          # ビルド時にコピーされる
    ├── player.png
    ├── enemy.png
    └── tileset.png
```

**コードから読み込み**

```c
// "images/"は自動的にプレフィックス
LCDBitmap* bitmap = g_pd->graphics->loadBitmap("images/player", NULL);
```

### スプライトシート

```c
// スプライトシート（アニメーション）
typedef struct {
    LCDBitmapTable* bitmap_table;
    LCDSprite* sprite;
    int current_frame;
    int frame_count;
    float frame_time;
    float elapsed;
} AnimatedSprite;

AnimatedSprite* animated_sprite_create(const char* table_path) {
    AnimatedSprite* anim = g_pd->system->realloc(NULL, sizeof(AnimatedSprite));

    const char* err = NULL;
    anim->bitmap_table = g_pd->graphics->loadBitmapTable(table_path, &err);
    if (!anim->bitmap_table) {
        g_pd->system->logToConsole("Failed to load bitmap table: %s", err);
        g_pd->system->realloc(anim, 0);
        return NULL;
    }

    anim->frame_count = g_pd->graphics->getTableBitmapCount(anim->bitmap_table);
    anim->current_frame = 0;
    anim->frame_time = 1.0f / 10.0f;  // 10fps
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
```

### 音声ファイル

```bash
# サポート形式
# - WAV (非圧縮 PCM, 16-bit, 22050Hz または 44100Hz 推奨)
# - MP3 (BGM用、FilePlayer使用)

# ファイルサイズ削減
# - 効果音: WAV, モノラル, 22050Hz
# - BGM: MP3, ステレオ, 128kbps

# 配置
Source/
└── sounds/
    ├── jump.wav
    ├── hit.wav
    └── bgm.mp3
```

### フォント

```bash
# カスタムフォント作成
# 1. Caps フォルダを作成
mkdir -p Source/fonts/MyFont

# 2. 画像ファイル配置（各文字を画像化）
# fonts/MyFont/A.png, B.png, C.png ...

# 3. コードから読み込み
```

```c
LCDFont* font = g_pd->graphics->loadFont("fonts/MyFont", NULL);
if (font) {
    g_pd->graphics->setFont(font);
    g_pd->graphics->drawText("HELLO", 5, kASCIIEncoding, 10, 10);
}
```

---

## パフォーマンス最適化

### メモリ管理

```c
// ✅ 推奨: Playdate API の realloc を使用
void* ptr = g_pd->system->realloc(NULL, 1024);  // 確保
g_pd->system->realloc(ptr, 0);                   // 解放

// ❌ 避ける: stdlib の malloc/free（使用可能だが推奨されない）
void* ptr = malloc(1024);
free(ptr);

// メモリ使用量ログ
void log_memory_usage(void) {
    g_pd->system->logToConsole("Memory used: %d bytes",
                               g_pd->system->getBatteryVoltage());
}
```

### 描画最適化

```c
// ✅ ダーティ領域のみ更新
void optimized_draw(void) {
    // 変更があった領域のみマーク
    g_pd->graphics->markUpdatedRows(0, 239);  // 全画面

    // または部分的に
    g_pd->graphics->markUpdatedRows(50, 100);  // 50-100行目のみ
}

// ✅ スプライト描画の最適化
void sprite_optimization(void) {
    // 画面外スプライトは自動的にスキップされる
    // Z-orderで描画順序制御
    g_pd->sprite->setZIndex(player_sprite, 10);   // 前面
    g_pd->sprite->setZIndex(background_sprite, 0); // 背景

    // 不可視スプライトは描画スキップ
    g_pd->sprite->setVisible(hidden_sprite, 0);
}

// ❌ 避ける: 毎フレーム画面全クリア
void bad_draw(void) {
    g_pd->graphics->clear(kColorWhite);  // 重い
    // 代わりにスプライトシステムに任せる
}
```

### FPS維持

```c
// 30fps維持（推奨）
g_pd->display->setRefreshRate(30.0f);

// 高FPSが必要な場合は50fps（最大）
g_pd->display->setRefreshRate(50.0f);

// 処理負荷計測
void measure_performance(void) {
    unsigned int start = g_pd->system->getCurrentTimeMilliseconds();

    // 処理
    heavy_calculation();

    unsigned int end = g_pd->system->getCurrentTimeMilliseconds();
    g_pd->system->logToConsole("Processing time: %u ms", end - start);
}

// フレームドロップ対策
int update_callback(void* userdata) {
    static float accumulator = 0.0f;
    const float fixed_dt = 1.0f / 30.0f;

    // 経過時間取得
    float frame_time = get_delta_time();  // 実装必要
    accumulator += frame_time;

    // 固定タイムステップで更新
    while (accumulator >= fixed_dt) {
        update_game(fixed_dt);
        accumulator -= fixed_dt;
    }

    render_game();
    return 1;
}
```

### プロファイリング

```c
// デバッグ統計表示
void show_debug_stats(void) {
    // FPS表示
    g_pd->system->drawFPS(0, 0);

    // カスタム統計
    char stats[100];
    sprintf(stats, "Enemies: %d\nMemory: %d KB",
            enemy_count, get_memory_usage() / 1024);
    g_pd->graphics->drawText(stats, strlen(stats),
                             kASCIIEncoding, 10, 30);
}
```

---

## 高度なパターン（経験者向け）

### ステートマシン

```c
// ゲーム状態管理
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
    void (*state_exit)(void);
} StateMachine;

static StateMachine state_machine;

// 状態遷移
void change_state(GameState new_state) {
    // 現在の状態から退出
    if (state_machine.state_exit) {
        state_machine.state_exit();
    }

    state_machine.current_state = new_state;

    // 新しい状態の関数を設定
    switch (new_state) {
        case STATE_MENU:
            state_machine.state_enter = menu_enter;
            state_machine.state_update = menu_update;
            state_machine.state_exit = menu_exit;
            break;
        case STATE_PLAYING:
            state_machine.state_enter = game_enter;
            state_machine.state_update = game_update;
            state_machine.state_exit = game_exit;
            break;
        // ...
    }

    // 新しい状態に入る
    if (state_machine.state_enter) {
        state_machine.state_enter();
    }
}

// メインループから呼ぶ
int main_update(void* userdata) {
    float dt = 1.0f / 30.0f;

    if (state_machine.state_update) {
        state_machine.state_update(dt);
    }

    return 1;
}
```

### オブジェクトプール

```c
// 弾丸プール（頻繁に生成・破棄されるオブジェクトの最適化）
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

        // ビットマップ設定
        LCDBitmap* bmp = g_pd->graphics->loadBitmap("images/bullet", NULL);
        g_pd->sprite->setImage(bullet_pool[i].sprite, bmp, kBitmapUnflipped);
        g_pd->graphics->freeBitmap(bmp);

        // 初期状態は非表示
        g_pd->sprite->setVisible(bullet_pool[i].sprite, 0);
    }

    pool_initialized = 1;
}

Bullet* bullet_spawn(float x, float y, float vel_x, float vel_y) {
    // 未使用の弾丸を探す
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

    // プールが満杯
    g_pd->system->logToConsole("Bullet pool exhausted!");
    return NULL;
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

        // 画面外で削除
        if (bullet_pool[i].x < 0 || bullet_pool[i].x > 400 ||
            bullet_pool[i].y < 0 || bullet_pool[i].y > 240) {
            bullet_despawn(&bullet_pool[i]);
        }
    }
}
```

### データ駆動設計

```c
// JSON設定ファイル駆動の敵配置
typedef struct {
    char* type;
    float x;
    float y;
    int health;
} EnemyConfig;

void load_enemy_config(const char* path) {
    SDFile* file = g_pd->file->open(path, kFileRead);
    if (!file) return;

    // JSONパース（簡略化）
    // 実際にはPlaydate JSON APIを使用

    // 例: {"enemies": [{"type": "slime", "x": 100, "y": 50, "health": 10}]}

    // 各敵を生成
    for (int i = 0; i < enemy_count; i++) {
        Enemy* enemy = enemy_create_from_config(&configs[i]);
        // ...
    }

    g_pd->file->close(file);
}
```

### カスタムアロケータ

```c
// スタックアロケータ（一時メモリ確保用）
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
    if (temp_allocator.offset + size > temp_allocator.size) {
        g_pd->system->error("Stack allocator overflow!");
        return NULL;
    }

    void* ptr = temp_allocator.buffer + temp_allocator.offset;
    temp_allocator.offset += size;
    return ptr;
}

void stack_allocator_reset(void) {
    temp_allocator.offset = 0;
}

// 使用例（フレーム開始時にリセット）
int game_update(void* userdata) {
    stack_allocator_reset();

    // 一時配列確保
    int* temp_data = stack_alloc(sizeof(int) * 100);
    // 使用
    // フレーム終了時に自動的に解放（次フレームでリセット）

    return 1;
}
```

### Luaバインディング（上級）

Playdate SDK は Lua をサポートしていますが、C言語からLuaを呼び出すことも可能です。

```c
// Lua関数をCから呼ぶ
void call_lua_function(void) {
    // Luaランタイム取得
    lua_State* L = g_pd->lua->getLuaState();

    // グローバル関数取得
    lua_getglobal(L, "myLuaFunction");

    // 引数をプッシュ
    lua_pushnumber(L, 42);
    lua_pushstring(L, "hello");

    // 関数呼び出し（引数2個、戻り値1個）
    if (lua_pcall(L, 2, 1, 0) != 0) {
        const char* err = lua_tostring(L, -1);
        g_pd->system->logToConsole("Lua error: %s", err);
        lua_pop(L, 1);
        return;
    }

    // 戻り値取得
    int result = (int)lua_tonumber(L, -1);
    lua_pop(L, 1);

    g_pd->system->logToConsole("Lua returned: %d", result);
}

// C関数をLuaに登録
static int my_c_function(lua_State* L) {
    int arg = (int)lua_tonumber(L, 1);

    g_pd->system->logToConsole("Called from Lua with arg: %d", arg);

    lua_pushnumber(L, arg * 2);
    return 1;  // 戻り値の数
}

void register_c_functions(void) {
    lua_State* L = g_pd->lua->getLuaState();

    lua_register(L, "myCFunction", my_c_function);
}
```

---

## ベストプラクティス

### Do's

- **グローバルPlaydateAPIを使用** - `extern PlaydateAPI* g_pd` で各ファイルから参照
- **NULLチェックを徹底** - ポインタ操作の前に必ずチェック
- **メモリは必ず解放** - `realloc(ptr, 0)` で解放
- **スプライトシステムを活用** - 自動描画・衝突判定で効率化
- **FPSは30fps推奨** - バッテリー消費とパフォーマンスのバランス
- **アセットはビルド時に変換** - PNG/WAVは自動的に最適化される
- **デバッグログを活用** - `logToConsole()` で問題を早期発見

### Don'ts

- **stdlib の malloc/free を多用しない** - Playdate API の realloc を使用
- **毎フレーム画面全クリアしない** - 必要な領域のみ更新
- **巨大なビットマップをメモリに保持しない** - 必要時にロード、使用後解放
- **過度に複雑な衝突判定を避ける** - スプライトシステムの衝突判定を活用
- **グローバル変数を乱用しない** - 構造体にまとめて管理
- **エラーハンドリングを省略しない** - 必ず戻り値とNULLをチェック

---

## よくあるパターン

### シーン管理

```c
typedef struct Scene {
    void (*init)(void);
    void (*update)(float dt);
    void (*draw)(void);
    void (*cleanup)(void);
} Scene;

static Scene* current_scene = NULL;

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
```

### タイマー

```c
typedef struct {
    float duration;
    float elapsed;
    int active;
    void (*callback)(void);
} Timer;

static Timer timers[MAX_TIMERS];

Timer* timer_start(float duration, void (*callback)(void)) {
    for (int i = 0; i < MAX_TIMERS; i++) {
        if (!timers[i].active) {
            timers[i].duration = duration;
            timers[i].elapsed = 0;
            timers[i].callback = callback;
            timers[i].active = 1;
            return &timers[i];
        }
    }
    return NULL;
}

void timer_update_all(float dt) {
    for (int i = 0; i < MAX_TIMERS; i++) {
        if (!timers[i].active) continue;

        timers[i].elapsed += dt;
        if (timers[i].elapsed >= timers[i].duration) {
            if (timers[i].callback) {
                timers[i].callback();
            }
            timers[i].active = 0;
        }
    }
}
```

---

## トラブルシューティング

### ビルドエラー

```bash
# "SDK not found" エラー
export PLAYDATE_SDK_PATH=/path/to/PlaydateSDK

# Makefileが見つからない
# Makefile に以下を追加
include $(SDK)/C_API/buildsupport/common.mk
```

### 実行時エラー

```c
// "Sprite is NULL" エラー
// → NULLチェック不足
if (!sprite) {
    g_pd->system->logToConsole("ERROR: sprite is NULL");
    return;
}

// "Memory allocation failed" エラー
// → メモリ不足、解放漏れをチェック
void* ptr = g_pd->system->realloc(NULL, size);
if (!ptr) {
    g_pd->system->error("Out of memory!");
    return;
}
```

### パフォーマンス問題

```c
// FPSが低い場合
// 1. FPS表示で確認
g_pd->system->drawFPS(0, 0);

// 2. 処理時間計測
unsigned int start = g_pd->system->getCurrentTimeMilliseconds();
// 重い処理
unsigned int end = g_pd->system->getCurrentTimeMilliseconds();
g_pd->system->logToConsole("Time: %u ms", end - start);

// 3. 最適化ポイント
// - スプライト数を削減
// - 毎フレームの画面クリアを避ける
// - 衝突判定を最適化
// - オブジェクトプール使用
```

---

## 参考リンク

- [Playdate SDK Documentation](https://sdk.play.date/)
- [Playdate Developer Forum](https://devforum.play.date/)
- [Inside Playdate (公式ドキュメント)](https://sdk.play.date/inside-playdate/)
