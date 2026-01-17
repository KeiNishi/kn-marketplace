# インストールガイド

新規プロジェクトでKN Marketplaceのスキルを使用する方法を説明します。

## 方法1: Git Submoduleとして追加（推奨）

新規プロジェクトでこのMarketplaceを参照する場合：

### 1. Marketplaceをサブモジュールとして追加

```bash
cd /path/to/your-new-project
git submodule add <このリポジトリのURL> .claude/marketplace
git submodule update --init --recursive
```

### 2. スキルを参照

```bash
# 例: Godot GDScriptスキルを使用
claude --skill .claude/marketplace/skills/godot-gdscript-patterns/skill.md
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

### 3. スキルを参照

```bash
claude --skill .claude/marketplace/skills/godot-gdscript-patterns/skill.md
```

## 方法3: 直接コピー

特定のスキルだけを使いたい場合：

### 1. 必要なスキルをコピー

```bash
cd /path/to/your-new-project
mkdir -p .claude/skills
cp D:\Projects\kn-marketplace\skills/godot-gdscript-patterns/skill.md .claude/skills/
```

### 2. スキルを参照

```bash
claude --skill .claude/skills/skill.md
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

### 2. スキルを参照（どのプロジェクトからでも）

```bash
claude --skill $env:CLAUDE_MARKETPLACE_PATH/skills/godot-gdscript-patterns/skill.md  # PowerShell
claude --skill $CLAUDE_MARKETPLACE_PATH/skills/godot-gdscript-patterns/skill.md      # bash/zsh
```

## 推奨される構造

各プロジェクトで以下のような構造を作ることをお勧めします：

```
your-project/
├── .claude/
│   ├── marketplace/          # サブモジュールまたはシンボリックリンク
│   │   ├── skills/
│   │   └── marketplace.json
│   └── project-skills/       # プロジェクト固有のスキル
│       └── custom-skill.md
├── src/
└── README.md
```

## 利用可能なスキル一覧の確認

```bash
# marketplace.jsonを確認
cat .claude/marketplace/marketplace.json

# または、JSONを整形して表示
cat .claude/marketplace/marketplace.json | jq '.skills[] | {id, name, description}'
```

## スキルの使用例

### ClaudeCodeでスキルを直接指定

```bash
# Godot GDScriptパターンを使用
claude code --skill .claude/marketplace/skills/godot-gdscript-patterns/skill.md "Implement a state machine"

# PR作成スキルを使用
claude code --skill .claude/marketplace/skills/create-pr/skill.md "Create PR for feature X"
```

### プロジェクト内でのエイリアス作成

**PowerShellの場合 (プロジェクトルートで):**
```powershell
# skills-alias.ps1
function Use-GodotSkill {
    claude code --skill .claude/marketplace/skills/godot-gdscript-patterns/skill.md $args
}

function Use-PRSkill {
    claude code --skill .claude/marketplace/skills/create-pr/skill.md $args
}

# 使用方法
. .\skills-alias.ps1
Use-GodotSkill "Create a player controller"
```

**Bash/Zshの場合:**
```bash
# .envrc または .aliases
alias claude-godot='claude code --skill .claude/marketplace/skills/godot-gdscript-patterns/skill.md'
alias claude-pr='claude code --skill .claude/marketplace/skills/create-pr/skill.md'

# 使用方法
source .aliases
claude-godot "Create a player controller"
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
claude --skill D:\Projects\kn-marketplace\skills\godot-gdscript-patterns\skill.md
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
