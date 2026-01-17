# インストールガイド

新規プロジェクトでKN Marketplaceのプラグインを使用する方法を説明します。

## 方法1: Git Submoduleとして追加（推奨）

新規プロジェクトでこのMarketplaceを参照する場合：

### 1. Marketplaceをサブモジュールとして追加

```bash
cd /path/to/your-new-project
git submodule add <このリポジトリのURL> .claude/marketplace
git submodule update --init --recursive
```

### 2. プラグインを参照

```bash
# プラグイン全体を使用
claude --plugin .claude/marketplace/plugins/godot-gdscript-patterns

# 特定のスキルのみ使用
claude --skill .claude/marketplace/plugins/godot-gdscript-patterns/skills/my-skill/SKILL.md
```

### 3. サブモジュールの更新

```bash
cd .claude/marketplace
git pull origin main
cd ../..
git add .claude/marketplace
git commit -m "Update marketplace submodule"
```

## 方法2: シンボリックリンクを作成

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

### 3. プラグインを参照

```bash
claude --plugin .claude/marketplace/plugins/godot-gdscript-patterns
```

## 方法3: 直接コピー

特定のプラグインだけを使いたい場合：

### 1. 必要なプラグインをコピー

```bash
cd /path/to/your-new-project
mkdir -p .claude/plugins
cp -r D:\Projects\kn-marketplace\plugins\godot-gdscript-patterns .claude/plugins/
```

### 2. プラグインを参照

```bash
claude --plugin .claude/plugins/godot-gdscript-patterns
```

## 方法4: 環境変数で共通パスを設定

### 1. 環境変数を設定

**Windowsの場合:**
```powershell
# PowerShellプロファイルに追加 (~\Documents\PowerShell\Microsoft.PowerShell_profile.ps1)
$env:CLAUDE_MARKETPLACE_PATH = "D:\Projects\kn-marketplace"
```

**macOS/Linuxの場合:**
```bash
# ~/.bashrc または ~/.zshrc に追加
export CLAUDE_MARKETPLACE_PATH="$HOME/Documents/kn-marketplace"
```

### 2. プラグインを参照（どのプロジェクトからでも）

```bash
claude --plugin $env:CLAUDE_MARKETPLACE_PATH/plugins/godot-gdscript-patterns  # PowerShell
claude --plugin $CLAUDE_MARKETPLACE_PATH/plugins/godot-gdscript-patterns      # bash/zsh
```

## 推奨される構造

各プロジェクトで以下のような構造を作ることをお勧めします：

```
your-project/
├── .claude/
│   ├── marketplace/          # サブモジュールまたはシンボリックリンク
│   │   ├── plugins/
│   │   └── marketplace.json
│   └── project-plugins/      # プロジェクト固有のプラグイン
│       └── custom-plugin/
│           └── .claude-plugin/
│               └── plugin.json
├── src/
└── README.md
```

## 利用可能なプラグイン一覧の確認

```bash
# marketplace.jsonを確認
cat .claude/marketplace/marketplace.json

# または、JSONを整形して表示（jqが必要）
cat .claude/marketplace/marketplace.json | jq '.plugins[] | {id, name, description}'
```

**Windows PowerShellの場合:**
```powershell
Get-Content .claude\marketplace\marketplace.json | ConvertFrom-Json | Select-Object -ExpandProperty plugins | Format-Table id, name, description
```

## プラグインの使用例

### ClaudeCodeでプラグインを直接指定

```bash
# Godot GDScriptプラグインを使用
claude code --plugin .claude/marketplace/plugins/godot-gdscript-patterns

# PR作成プラグインを使用
claude code --plugin .claude/marketplace/plugins/create-pr
```

### 特定のスキルだけを使用

```bash
# プラグイン内の特定のスキルを使用
claude code --skill .claude/marketplace/plugins/godot-gdscript-patterns/skills/state-machine/SKILL.md
```

### プロジェクト内でのエイリアス作成

**PowerShellの場合 (プロジェクトルートで):**
```powershell
# plugins-alias.ps1
function Use-GodotPlugin {
    claude code --plugin .claude/marketplace/plugins/godot-gdscript-patterns $args
}

function Use-PRPlugin {
    claude code --plugin .claude/marketplace/plugins/create-pr $args
}

# 使用方法
. .\plugins-alias.ps1
Use-GodotPlugin "Create a player controller"
```

**Bash/Zshの場合:**
```bash
# .envrc または .aliases
alias claude-godot='claude code --plugin .claude/marketplace/plugins/godot-gdscript-patterns'
alias claude-pr='claude code --plugin .claude/marketplace/plugins/create-pr'

# 使用方法
source .aliases
claude-godot "Create a player controller"
```

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

## 外部からSKILL.mdをコピーする場合

外部から入手した `SKILL.md` ファイルをプラグインとして追加する方法：

### 1. プラグイン構造を作成

```bash
cd D:\Projects\kn-marketplace
mkdir -p plugins/my-new-plugin/.claude-plugin
mkdir -p plugins/my-new-plugin/skills/my-skill
```

### 2. plugin.jsonを作成

```bash
# plugins/my-new-plugin/.claude-plugin/plugin.json
{
  "name": "my-new-plugin",
  "version": "1.0.0",
  "description": "プラグインの説明",
  "author": "Your Name",
  "tags": ["tag1"]
}
```

### 3. SKILL.mdをコピー

```bash
cp /path/to/SKILL.md plugins/my-new-plugin/skills/my-skill/
```

### 4. marketplace.jsonに登録

```json
{
  "plugins": [
    {
      "id": "my-new-plugin",
      "name": "My New Plugin",
      "description": "プラグインの説明",
      "path": "plugins/my-new-plugin",
      "version": "1.0.0",
      "author": "Your Name",
      "tags": ["tag1"],
      "created": "2026-01-18",
      "updated": "2026-01-18"
    }
  ]
}
```

## トラブルシューティング

### サブモジュールが空の場合

```bash
git submodule update --init --recursive
```

### シンボリックリンクが機能しない場合（Windows）

管理者権限が必要です。または開発者モードを有効にしてください：
- 設定 → 更新とセキュリティ → 開発者向け → 開発者モード

### パスが見つからない場合

絶対パスを使用してください：
```bash
claude --plugin D:\Projects\kn-marketplace\plugins\godot-gdscript-patterns
```

### プラグインが認識されない場合

`.claude-plugin/plugin.json` が正しく配置されているか確認：
```bash
# 正しい構造
plugins/my-plugin/.claude-plugin/plugin.json  ✓

# 間違った構造
plugins/my-plugin/plugin.json                  ✗
```

## 更新の取得

### サブモジュールを使用している場合

```bash
cd .claude/marketplace
git pull origin main
```

### シンボリックリンクを使用している場合

```bash
cd ~/Documents/kn-marketplace  # または D:\Projects\kn-marketplace
git pull origin main
```

これで全てのプロジェクトに自動的に反映されます！

## 📚 参考資料

- [公式Plugin作成ガイド](https://code.claude.com/docs/en/plugins)
- [Plugin Marketplace公式ドキュメント](https://code.claude.com/docs/ja/plugin-marketplaces)
- [Skills vs Plugins解説記事](https://www.youngleaders.tech/p/claude-skills-commands-subagents-plugins)
