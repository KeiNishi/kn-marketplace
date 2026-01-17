# KN Marketplace for Claude Code

ClaudeCode用の個人Skillマーケットプレイスです。

## ディレクトリ構造

```
kn-marketplace/
├── skills/              # スキルファイルを配置するディレクトリ
│   ├── example/
│   │   └── skill.md
│   └── your-skill/
│       └── skill.md
├── marketplace.json     # マーケットプレイスの設定ファイル
└── README.md
```

## 外部からskills.mdをコピーして使う方法

### 1. スキルファイルの配置

外部から入手した `skills.md` や `skill.md` ファイルは以下の場所に配置してください：

```
skills/<skill-name>/skill.md
```

例：
- `skills/pdf-converter/skill.md`
- `skills/code-review/skill.md`
- `skills/git-helper/skill.md`

### 2. マーケットプレイスへの登録

`marketplace.json` にスキル情報を追加します：

```json
{
  "skills": [
    {
      "id": "your-skill-name",
      "name": "Your Skill Display Name",
      "description": "スキルの説明",
      "path": "skills/your-skill-name/skill.md",
      "version": "1.0.0",
      "author": "Your Name",
      "tags": ["tag1", "tag2"]
    }
  ]
}
```

### 3. スキルの使い方

ClaudeCodeでスキルを使用する際は、`skill.md`ファイルのパスを指定します。

## 例

`skills/example/skill.md` にサンプルスキルを用意しています。参考にしてください。
