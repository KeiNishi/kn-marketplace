# KN Marketplace for Claude Code

ClaudeCode用の個人Pluginマーケットプレイスです。

## 🚀 クイックスタート

新規プロジェクトでこのMarketplaceを使いたい場合は、[INSTALL.md](INSTALL.md)を参照してください。

## ディレクトリ構造

```
kn-marketplace/
├── plugins/                    # プラグインを配置するディレクトリ
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
├── marketplace.json           # マーケットプレイスの設定ファイル
├── INSTALL.md                 # インストールガイド
└── README.md
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
  "author": "Your Name",
  "tags": ["tag1", "tag2"]
}
```

### 3. マーケットプレイスへの登録

`marketplace.json` にプラグイン情報を追加します：

```json
{
  "plugins": [
    {
      "id": "your-plugin-name",
      "name": "Your Plugin Display Name",
      "description": "プラグインの説明",
      "path": "plugins/your-plugin-name",
      "version": "1.0.0",
      "author": "Your Name",
      "tags": ["tag1", "tag2"],
      "created": "2026-01-18",
      "updated": "2026-01-18"
    }
  ]
}
```

### 4. Pluginの使い方

ClaudeCodeでプラグインを使用する際は、プラグインディレクトリを指定します：

```bash
# プラグイン全体をロード
claude --plugin plugins/your-plugin-name

# 特定のスキルだけを使用
claude --skill plugins/your-plugin-name/skills/my-skill/SKILL.md
```

## 📚 参考リンク

- [公式Plugin作成ガイド](https://code.claude.com/docs/en/plugins)
- [Plugin Marketplace公式ドキュメント](https://code.claude.com/docs/ja/plugin-marketplaces)

## 例

`plugins/example/` にサンプルプラグインを用意しています。参考にしてください。
