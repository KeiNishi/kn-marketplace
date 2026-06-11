# インストールガイド

新規プロジェクトでKN Marketplaceのプラグインを使用する方法を説明します。

## 方法1: マーケットプレイスとして追加（推奨）

Claude Codeの公式プラグイン機能を使用する方法です。

### 1. マーケットプレイスを追加

**GitHubリポジトリから追加する場合：**
```bash
/plugin marketplace add github:KeiNishi/kn-marketplace
```

**ローカルパスから追加する場合：**
```bash
/plugin marketplace add D:\Projects\kn-marketplace
```

### 2. プラグインをインストール

```bash
# 利用可能なプラグイン一覧を確認
/plugin list

# プラグインをインストール
/plugin install godot-gdscript-patterns@kn-marketplace
/plugin install unity-gamedev-standards@kn-marketplace
```

### 3. マーケットプレイスを更新

```bash
/plugin marketplace update
```

---

## 方法2: Git Submoduleとして追加

プロジェクトにマーケットプレイスをサブモジュールとして含める場合：

### 1. Marketplaceをサブモジュールとして追加

```bash
cd /path/to/your-new-project
git submodule add <このリポジトリのURL> .claude/marketplace
git submodule update --init --recursive
```

### 2. ローカルマーケットプレイスとして登録

```bash
/plugin marketplace add .claude/marketplace
```

### 3. サブモジュールの更新

```bash
cd .claude/marketplace
git pull origin main
cd ../..
git add .claude/marketplace
git commit -m "Update marketplace submodule"
```

---

## 方法3: シンボリックリンクを作成

複数プロジェクトで共有する場合：

### 1. Marketplaceをクローン（一度だけ）

```bash
cd ~/Documents
git clone <このリポジトリのURL> kn-marketplace
```

### 2. 新規プロジェクトにリンクを作成

**Windowsの場合:**
```powershell
cd D:\Projects\your-new-project
New-Item -ItemType SymbolicLink -Path ".claude\marketplace" -Target "D:\Projects\kn-marketplace"
```

または管理者権限のコマンドプロンプトで:
```cmd
cd D:\Projects\your-new-project
mklink /D .claude\marketplace D:\Projects\kn-marketplace
```

**macOS/Linuxの場合:**
```bash
cd /path/to/your-new-project
ln -s ~/Documents/kn-marketplace .claude/marketplace
```

### 3. マーケットプレイスとして登録

```bash
/plugin marketplace add .claude/marketplace
```

---

## 方法4: OpenAI Codex CLI で使用する

このマーケットプレイスのスキルは Claude Code と OpenAI Codex の両方で動作するよう設計されています。Codex にはプラグイン機構がなく、スキルディレクトリ（`~/.agents/skills` または旧 `~/.codex/skills`）から `SKILL.md` を読み込みます。

### インストールスクリプトを実行

```bash
# リポジトリのクローン後、リポジトリ直下で実行
python3 tools/install-codex-skills.py
```

**Windowsの場合（python3が無い環境）:**
```powershell
py -3 tools\install-codex-skills.py
```

### 主なオプション

```bash
# インストール先を指定
python3 tools/install-codex-skills.py --dest ~/.codex/skills

# 特定プラグインのみインストール
python3 tools/install-codex-skills.py --plugins unity-gamedev-standards godot-gdscript-patterns

# 実行内容の事前確認（コピーしない）
python3 tools/install-codex-skills.py --dry-run

# 既存インストールを上書き（更新時）
python3 tools/install-codex-skills.py --force

# スキルを直下にフラット配置（再帰探索しない旧Codex向け）
python3 tools/install-codex-skills.py --flatten
```

### 注意事項

- コピー方式（symlink不使用）のため、Windowsでも管理者権限・開発者モード不要で動作します
- マーケットプレイス更新後は `--force` を付けて再実行してください
- 新しいスキルを認識させるには Codex セッションの再起動が必要です
- Claude Code 専用コンポーネント（`commands/`, `agents/`, `hooks/`）は Codex では動作しないためコピーされません。スキル本文はこれらに依存しない設計になっています

---

## 推奨される構造

各プロジェクトで以下のような構造を作ることをお勧めします：

```
your-project/
├── .claude/
│   ├── marketplace/          # サブモジュールまたはシンボリックリンク
│   │   ├── .claude-plugin/
│   │   │   └── marketplace.json
│   │   └── plugins/
│   └── project-plugins/      # プロジェクト固有のプラグイン
│       └── custom-plugin/
│           └── .claude-plugin/
│               └── plugin.json
├── src/
└── README.md
```

---

## 利用可能なプラグイン一覧の確認

```bash
# Claude Codeで利用可能なプラグイン一覧
/plugin list

# marketplace.jsonを直接確認する場合
cat .claude/marketplace/.claude-plugin/marketplace.json
```

**Windows PowerShellの場合:**
```powershell
Get-Content .claude\marketplace\.claude-plugin\marketplace.json | ConvertFrom-Json | Select-Object -ExpandProperty plugins | Format-Table name, description
```

---

## プラグインの使用方法

### インストール後の使用

プラグインをインストールすると、自動的にClaude Codeで利用可能になります：

```bash
# プラグインをインストール
/plugin install godot-gdscript-patterns@kn-marketplace

# スキルは自動的に利用可能に
# コマンドは `/コマンド名` で実行可能
```

---

## Plugin構造の理解

各プラグインは以下の構造を持ちます：

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json          # メタデータ（必須）
├── skills/                   # スキル（オプション）
│   └── my-skill/
│       └── SKILL.md
├── commands/                 # スラッシュコマンド（オプション）
├── agents/                   # 専用エージェント（オプション）
├── hooks/                    # イベントハンドラ（オプション）
└── README.md
```

⚠️ **注意**: `skills/`, `commands/`, `agents/`, `hooks/` は `.claude-plugin/` の**外側**に配置します！

---

## 外部からSKILL.mdをコピーする場合

外部から入手した `SKILL.md` ファイルをプラグインとして追加する方法：

### 1. プラグイン構造を作成

```bash
cd D:\Projects\kn-marketplace
mkdir -p plugins/my-new-plugin/.claude-plugin
mkdir -p plugins/my-new-plugin/skills/my-skill
```

### 2. plugin.jsonを作成

`plugins/my-new-plugin/.claude-plugin/plugin.json`:
```json
{
  "name": "my-new-plugin",
  "version": "1.0.0",
  "description": "プラグインの説明",
  "author": {
    "name": "Your Name"
  },
  "tags": ["tag1"]
}
```

### 3. SKILL.mdをコピー

```bash
cp /path/to/SKILL.md plugins/my-new-plugin/skills/my-skill/
```

### 4. marketplace.jsonに登録

`.claude-plugin/marketplace.json` に追加:
```json
{
  "plugins": [
    {
      "name": "my-new-plugin",
      "source": "./plugins/my-new-plugin",
      "description": "プラグインの説明",
      "version": "1.0.0",
      "author": {
        "name": "Your Name"
      },
      "tags": ["tag1"]
    }
  ]
}
```

---

## トラブルシューティング

### サブモジュールが空の場合

```bash
git submodule update --init --recursive
```

### シンボリックリンクが機能しない場合（Windows）

管理者権限が必要です。または開発者モードを有効にしてください：
- 設定 → 更新とセキュリティ → 開発者向け → 開発者モード

### プラグインが認識されない場合

`.claude-plugin/plugin.json` が正しく配置されているか確認：
```bash
# 正しい構造
plugins/my-plugin/.claude-plugin/plugin.json  ✓

# 間違った構造
plugins/my-plugin/plugin.json                  ✗
```

### マーケットプレイスが読み込まれない場合

- `.claude-plugin/marketplace.json` が存在するか確認
- JSONの構文エラーがないか確認
- `source` フィールドのパスが正しいか確認

---

## 更新の取得

### サブモジュールを使用している場合

```bash
cd .claude/marketplace
git pull origin main
```

### マーケットプレイスの更新

```bash
/plugin marketplace update
```

これで最新のプラグインが利用可能になります！

---

## 📚 参考資料

- [公式Plugin作成ガイド](https://code.claude.com/docs/en/plugins)
- [Plugin Marketplace公式ドキュメント](https://code.claude.com/docs/ja/plugin-marketplaces)
- [プラグインの検出とインストール](https://code.claude.com/docs/ja/discover-plugins)
