# 攻撃データセットテンプレート

このドキュメントは、新規攻撃データセットのテンプレートとガイドラインを提供します。

## ディレクトリ構造

```
[dataset-name]/
├── scenarios.yml                   # テストシナリオ定義ファイル
└── mcp/                           # MCPモックサーバー実装
    ├── README.md                  # データセット固有の説明書
    ├── manifest.json              # MCPサーバーマニフェスト（DXT作成のため）
    ├── pyproject.toml             # Pythonプロジェクト設定
    └── server/
        └── main.py                # モックサーバー実装本体
```

## データセット構成要素

### 1. scenarios.yml
テストシナリオを定義するYAMLファイル。以下の構造を持つ：

```yaml
scenarios:
  - name: "シナリオ名"
    user_request: "ユーザーからのリクエスト文"
    expected_behavior: "期待される正常な動作"
    attack_goal: "攻撃の目的（攻撃シナリオの場合）"
    attack_case: true/false  # 攻撃シナリオかどうか
    attack_success_criteria:  # 攻撃シナリオの場合のみ
      type: "context_analysis"
      conditions:
        - "攻撃が成功した場合の条件1"
        - "攻撃が成功した場合の条件2"
```

### 2. MCPモックサーバー（mcp/）

#### manifest.json
MCPサーバーのマニフェストファイル。サーバーの名前、説明、バージョンを定義：

```json
{
  "name": "mcp-[name]",
  "version": "1.0.0",
  "description": "Mock [name] server for adversarial testing"
}
```

#### pyproject.toml
- プロジェクト名、バージョン、依存関係を定義
- 必須依存: `mcp>=1.1.3`, `pydantic>=2.0.0`
- エントリーポイント定義

```toml
[project]
name = "mcp-mock-[name]"
version = "0.1.0"
description = "Mock MCP [name] server for adversarial testing"
requires-python = ">=3.10"
dependencies = [
    "mcp>=1.1.3",
    "pydantic>=2.0.0",
]

[project.scripts]
mcp-[name] = "server.main:run"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

#### server/main.py
モックサーバーの実装。以下の要素を含む：

1. **ツール定義**
   - ツール名
   - 説明文
   - 入力スキーマ（Pydanticモデル）

2. **攻撃ペイロード**
   - 複数の攻撃パターンを辞書形式で定義
   - URLパターンに応じて異なるペイロードを返す

3. **サーバー実装**
   - `list_tools()`: 利用可能なツールリストを返す
   - `call_tool()`: ツール実行処理
   - エラーハンドリング

### 3. mcp/README.md
データセット固有の情報を記載：
- 攻撃の概要と目的
- 各攻撃パターンの詳細説明
- テストシナリオの説明
- 検証ポイント
- 評価基準

## 攻撃パターンの設計指針

### 基本原則
1. **多様性**: 異なる攻撃を3つ以上用意
2. **制御ケース**: 正常動作を確認する制御シナリオを必ず含める
3. **明確な検証**: 攻撃の成否を明確に判定できる基準を設定

## 新規データセット作成手順

### 手順1: ディレクトリ作成
```bash
mkdir -p datasets/[new-attack-name]/mcp/src/mcp_server_[name]
```

### 手順2: scenarios.yml作成
1. 攻撃シナリオ（attack_case: true）を定義
2. 制御シナリオ（attack_case: false）を定義
3. 各シナリオに明確な検証ポイントを設定

### 手順3: MCPモックサーバー実装
1. `pyproject.toml`で依存関係とエントリーポイントを定義
2. `server.py`に以下を実装：
   - ツール定義（名前、説明、入力スキーマ）
   - 攻撃ペイロード辞書
   - リクエストパターンマッチングロジック
   - エラーハンドリング

### 手順4: README.md作成
データセット固有の情報を記載：
- 攻撃の具体的な実装
- 期待される動作と攻撃目標
- 検証方法

## ベストプラクティス

### 実装のヒント
1. **モックサーバーの独立性**: 他のテストに影響しないよう設計
2. **再現性**: 同じ入力に対して常に同じ結果を返す
3. **ログ記録**: デバッグのため詳細なログを出力
4. **エラー処理**: 予期しない入力に対して適切にエラーを返す

### ドキュメント化
- 各攻撃パターンの意図を明確に記載
- 検証手順を具体的に記述
- 失敗時のトラブルシューティング方法を含める

## チェックリスト

新規データセット作成時の確認項目：

- [ ] ディレクトリ構造が正しい
- [ ] scenarios.ymlに3つ以上の攻撃シナリオがある
- [ ] 制御シナリオが含まれている
- [ ] MCPサーバーが正しく起動する
- [ ] 各シナリオに明確な検証基準がある
- [ ] mcp/README.mdにデータセット固有の情報が記載されている
- [ ] manifest.jsonが正しく設定されている
