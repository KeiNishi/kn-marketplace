# KN Marketplace - エージェント用ガイドライン

- すべての作業前にgitのステータスを確認し、更新があるならgit pullする。

## バージョン管理ルール

### 必須: 変更時のバージョン更新

MarketplaceやPluginの内容を編集した場合、**必ず**該当するファイルのVersionを更新すること。

### 更新対象ファイル

- **Marketplace全体**: `.claude-plugin/marketplace.json` の `metadata.version`
- **個別Plugin**:
  - `plugins/<plugin-name>/.claude-plugin/plugin.json` の `version`
  - `.claude-plugin/marketplace.json` 内の該当プラグインエントリの `version`

### バージョン番号の形式

`MAJOR.MINOR.PATCH` (例: `3.0.0`)

### カウントアップのルール

| 変更の種類 | 更新する位 | 例 |
|-----------|-----------|-----|
| 細かい変更（typo修正、微調整、ドキュメント更新など） | 一の位 (PATCH) | `3.0.0` → `3.0.1` |
| 大きな内容変更（機能追加、構造変更など） | 十の位 (MINOR) | `3.0.1` → `3.1.0` |
| メジャーバージョン変更（破壊的変更、大幅なリニューアル） | 百の位 (MAJOR) | `3.1.0` → `4.0.0` |

### メジャーバージョン更新時の確認

**メジャーバージョン（百の位）を上げる場合は、必ずユーザーに確認を行うこと。**

確認例:
> 「この変更は破壊的変更を含むため、メジャーバージョンを 3.x.x → 4.0.0 に上げる必要があります。よろしいですか？」

### 同期の注意

Pluginを更新した場合、以下の2箇所のバージョンを**必ず同期**させること:
1. `plugins/<plugin-name>/.claude-plugin/plugin.json`
2. `.claude-plugin/marketplace.json` 内の該当エントリ

## スキル記述時のルール

- **必ず英語で記述すること**

## プラグイン開発・レビュー時のルール

### 必須: 公式ドキュメントへの準拠

スキル、コマンド、エージェント、フックなどのプラグインコンポーネントを作成・編集・レビューする際は、**必ずClaude Code公式ドキュメントの記載に沿って行うこと**。

### 参照すべき公式ドキュメント

#### プラグイン・マーケットプレース関連

| コンポーネント | 公式ドキュメントURL |
|---------------|-------------------|
| Plugins (プラグイン作成) | https://code.claude.com/docs/en/plugins |
| Plugins Reference (プラグイン仕様) | https://code.claude.com/docs/en/plugins-reference |
| Plugin Marketplaces (マーケットプレース作成) | https://code.claude.com/docs/en/plugin-marketplaces |
| Discover Plugins (プラグインのインストール) | https://code.claude.com/docs/en/discover-plugins |

#### コンポーネント別

| コンポーネント | 公式ドキュメントURL |
|---------------|-------------------|
| Skills (スキル) | https://code.claude.com/docs/en/skills |
| Sub-agents (サブエージェント) | https://code.claude.com/docs/en/sub-agents |
| Hooks Guide (フック入門) | https://code.claude.com/docs/en/hooks-guide |
| Hooks Reference (フック仕様) | https://code.claude.com/docs/en/hooks |
| MCP (外部ツール連携) | https://code.claude.com/docs/en/mcp |

#### 設定・その他

| コンポーネント | 公式ドキュメントURL |
|---------------|-------------------|
| Settings (設定) | https://code.claude.com/docs/en/settings |
| Memory (CLAUDE.md) | https://code.claude.com/docs/en/memory |
| IAM (権限管理) | https://code.claude.com/docs/en/iam |

### 注意事項

- 公式ドキュメントに記載されていないフィールドやオプションを使用しないこと
- 不明な点がある場合は、推測せず公式ドキュメントを確認すること
- レビュー時に公式ドキュメントと矛盾する指摘をしないこと