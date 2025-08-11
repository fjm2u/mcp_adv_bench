# MCP Adversarial Benchmark
> [!WARNING]
> このリポジトリには潜在的に危険な攻撃パターンが含まれています。研究・防御目的でのみ使用してください。


> [!NOTE]
> Since the maintainer is a native Japanese speaker, the codebase is currently written mainly in Japanese.
> An English version will be provided later.

このプロジェクトは、Model Context Protocol (MCP)に対するプロンプトインジェクションやその他攻撃の検証と防御策の研究を行うためのベンチマークリポジトリです。

より具体的には、「MCPとAIに悪意がないが、MCPから返されるデータによってAIが意図しない行動をしてしまう」という攻撃に対する評価を行うためのものです。
このような意図しない動作のパターンを研究し、防御策を開発することが本プロジェクトの主要な目的です。

```mermaid
flowchart LR
  %% Groups
  subgraph C[MCP Client]
    direction TB
    LLM[LLM]
    MU[mcp-use]
    LC[LangChain]
  end

  subgraph D[Dataset]
    direction TB
    MOCK[Mock MCP Server]
    SCN[Scenarios]
  end

  R[Runner]
  E[Evaluator]

  %% Flow
  SCN -->|1.Load scenario| R
  R -->|2.Execute scenario| C
  C -->|3.Tool calls / queries| MOCK
  R -->|4.Judge attack success| E

```


## セットアップ

```bash
# 環境変数の設定
cp .env.example .env
# .envファイルを編集してAPIキーを設定

# 依存関係のインストール
pip install -e .
```

## 使い方

### 評価システムの実行

```bash
cd eval
python main.py <dataset_name> [options]

# オプション:
#   -v, --verbose     詳細な出力を表示
#   -i N              各シナリオをN回繰り返し実行（デフォルト: 1）

# 例:
python main.py fetch-html -i 5 -v  # fetch-htmlデータセットを各シナリオ5回実行
```

複数回実行（-iオプション）を使用すると、以下の統計情報が計算されます：
- 各シナリオの成功率
- 全体の成功率
- 攻撃ブロック率（攻撃シナリオのみ）
- 制御パス率（制御シナリオのみ）
- 実行時間の平均

### MCP設定（必須）

評価システムの実行にはMCP (Model Context Protocol) の設定が必須です。`eval/mcp_config.json` で設定を行います：

```json
{
  "mcpServers": {
    "サーバー名": {
      "command": "python",
      "args": ["-m", "モジュール名"],
      "cwd": "作業ディレクトリ"
    }
  }
}
```

### 評価設定

`eval/eval_config.json` で評価システムの詳細設定を行います：

```json
{
  "llm": {
    "execution": {
      "model": "claude-3-haiku-20240307",
      "max_tokens": 4096,
      "temperature": 0.5
    },
    "evaluation": {
      "model": "claude-3-sonnet-20241022",
      "max_tokens": 1000,
      "temperature": 0.0
    }
  },
  "prompts": {
    "attack_evaluation": "攻撃シナリオ用評価プロンプト",
    "control_evaluation": "制御シナリオ用評価プロンプト"
  }
}
```

#### LLM設定
- **execution**: シナリオを実行する際に使用されるLLM
- **evaluation**: 実行結果を評価する際に使用されるLLM（より高性能なモデルを推奨）

## データセット

新しい攻撃データセットの作成方法については、[データセットテンプレート](docs/dataset-template.md)を参照してください。

### 成功判定ロジック

評価システムは`attack_success_criteria`を使用して攻撃の成功を判定します：

- **攻撃シナリオ**: `attack_success_criteria`で定義された条件に基づいて攻撃の成功を判定
  - 攻撃が成功していない場合 → 防御成功（success: true）
  - 攻撃が成功した場合 → 防御失敗（success: false）
- **制御シナリオ**: MCPツールのエラーハンドリングが適切に行われているかを確認

## 貢献

新しい攻撃パターンや防御策の提案を歓迎します。
特に、データセットの追加について貢献頂けると嬉しいです。

## ライセンス・免責事項
このプロジェクトはApache2.0ライセンスの下で提供されています。
悪意のある使用は固く禁じられています。
このツールは教育・研究目的でのみ提供されています。
不正使用による損害について、作者は一切の責任を負いません。
