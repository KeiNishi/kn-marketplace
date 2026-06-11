# KN Marketplace for Claude Code

ClaudeCode用の個人Pluginマーケットプレイスです。全スキルは **Claude Code と OpenAI Codex の両方**、および **Windows / macOS / Linux** で動作するよう設計されています。

## 🚀 クイックスタート

新規プロジェクトでこのMarketplaceを使いたい場合は、[INSTALL.md](INSTALL.md)を参照してください。

- **Claude Code**: `/plugin marketplace add github:KeiNishi/kn-marketplace`
- **OpenAI Codex**: `python3 tools/install-codex-skills.py`（詳細はINSTALL.md 方法4）

## 📐 スキル執筆標準

スキル・プラグインの作成/編集は [docs/SKILL-AUTHORING.md](docs/SKILL-AUTHORING.md) の標準に従ってください（クロスエージェント互換・Windows互換・progressive disclosure・評価必須などのルールを規定）。

## 📊 評価成果物

各スキルの with/without ベンチマーク実行ログは `eval-archives/`（リポジトリ直下）に保管しています。プラグイン配布物には含まれません。

## ディレクトリ構造

```
kn-marketplace/
├── .claude-plugin/
│   └── marketplace.json       # マーケットプレイスの設定ファイル
├── upstream/
│   └── claude-plugins-official/  # git submodule (anthropics/claude-plugins-official)
│       └── plugins/               # sparse-checkout: skill-creator のみ取得
│           └── skill-creator/
│               ├── .claude-plugin/
│               │   └── plugin.json
│               └── skills/
├── plugins/                    # プラグインを配置するディレクトリ
│   ├── skill-creator -> ../upstream/claude-plugins-official/plugins/skill-creator  # symlink
│   ├── example/
│   │   ├── .claude-plugin/
│   │   │   └── plugin.json    # プラグインメタデータ
│   │   ├── skills/            # スキルディレクトリ（オプション）
│   │   │   └── my-skill/
│   │   │       └── SKILL.md
│   │   ├── commands/          # スラッシュコマンド（オプション）
│   │   ├── agents/            # 専用エージェント（オプション）
│   │   └── README.md
│   └── your-plugin/
│       └── .claude-plugin/
│           └── plugin.json
├── INSTALL.md                 # インストールガイド
└── README.md
```

### submodule について

`plugins/skill-creator` は [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) の `plugins/skill-creator/` を git submodule + シンボリックリンクで参照しています。ローカルでは編集せず、upstream の変更のみを取り込みます。

**クローン時の注意:**

```bash
git clone --recurse-submodules <repo-url>
# または既存クローン後に
git submodule update --init
```

**skill-creator を upstream の最新版に更新する方法:**

```bash
git submodule update --remote upstream/claude-plugins-official
git add upstream/claude-plugins-official
git commit -m "sync: update skill-creator from upstream"
git push
```

## 📦 Plugin構造について

ClaudeCodeのPluginは以下の構造を持ちます：

### 必須ファイル
- `.claude-plugin/plugin.json` - プラグインのメタデータ（必須）

### オプショナルディレクトリ
- `skills/` - Agent Skillsを配置
- `commands/` - スラッシュコマンド
- `agents/` - 専用エージェント
- `hooks/` - イベントハンドラ
- `.mcp.json` - 外部ツール設定

⚠️ **重要**: これらのディレクトリは `.claude-plugin/` の**外側**に配置します！

## 外部からPluginをコピーして使う方法

### 1. Pluginファイルの配置

外部から入手したPluginは以下の場所に配置してください：

```
plugins/<plugin-name>/
├── .claude-plugin/
│   └── plugin.json
└── ... (その他のファイル)
```

### 2. Skills専用の場合

外部から `SKILL.md` だけを入手した場合：

```bash
mkdir -p plugins/my-plugin/.claude-plugin
mkdir -p plugins/my-plugin/skills/my-skill

# plugin.jsonを作成
# SKILL.mdをコピー
cp path/to/SKILL.md plugins/my-plugin/skills/my-skill/
```

**plugin.jsonの例:**
```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "プラグインの説明",
  "author": {
    "name": "Your Name"
  },
  "tags": ["tag1", "tag2"]
}
```

### 3. マーケットプレイスへの登録

`.claude-plugin/marketplace.json` にプラグイン情報を追加します：

```json
{
  "plugins": [
    {
      "name": "your-plugin-name",
      "source": "./plugins/your-plugin-name",
      "description": "プラグインの説明",
      "version": "1.0.0",
      "author": {
        "name": "Your Name"
      },
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

### 4. Pluginの使い方

ClaudeCodeでプラグインをインストールするには：

```bash
# マーケットプレイスを追加
/plugin marketplace add <マーケットプレイスのパスまたはURL>

# プラグインをインストール
/plugin install your-plugin-name@kn-marketplace
```

## 📚 参考リンク

- [公式Plugin作成ガイド](https://code.claude.com/docs/en/plugins)
- [Plugin Marketplace公式ドキュメント](https://code.claude.com/docs/ja/plugin-marketplaces)

## 例

`plugins/example/` にサンプルプラグインを用意しています。参考にしてください。
