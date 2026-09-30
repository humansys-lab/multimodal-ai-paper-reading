# 短い用語集

| 用語 | この講義での意味 |
|---|---|
| 機械学習 | データを使ってモデルの振る舞いを調整する方法 |
| 推論 | 学習済みのモデルを入力に適用して出力を得ること |
| token | モデルが文章を扱う単位。単語・文字と一対一とは限らない |
| embedding | token等を計算用の数値ベクトルへ対応付けた表現 |
| attention | 入力の各位置の情報を参照し、表現を更新する仕組み |
| Transformer | attention等を積み重ねて入力を処理するモデル構造 |
| LLM | 大量の言語データ等で学習した言語モデル |
| VLM | 画像と言語を関連付けて処理するモデル |
| 文脈 | 現在の入力、会話履歴、添付内容などモデルへ与える情報 |
| PDF | 文書の保存形式。モデルへ渡す際の処理方式とは別 |
| 根拠 | 判断を支える本文・図・数値・注記の具体的な位置 |
| thinking | 一部モデルで推論時の計算量等を調整する設定。正確さを保証しない |

[MLCC](prework.md)、[Attention Is All You Need](https://arxiv.org/abs/1706.03762)、[Visual Instruction Tuning](https://arxiv.org/abs/2304.08485)を参照。製品ごとの非公開内部構造を断定するための用語集ではない。

## Paper2Agentを読むための補足

[エージェントとMCP](agents_and_mcp.md)はP1終了後に使う。agentは目標に応じてツールの実行と結果確認を進める仕組み、MCPはAIアプリとツール・データをつなぐ共通の通信規約。論文中の意味はFig.1と照合する。

## 図2で必要になったときに参照する用語

| 用語 | 短い説明 | 一次資料 |
|---|---|---|
| 遺伝子の発現調節 | 遺伝子が、いつ・どこで・どれほど使われるかを調整する過程 | [NHGRI](https://www.genome.gov/genetics-glossary/Gene-Regulation) |
| ゲノムワイド関連解析（GWAS） | 多くの人の遺伝的な違いと、病気や特徴との統計的関連を調べる方法。関連だけで原因は確定しない | [NHGRI](https://www.genome.gov/genetics-glossary/Genome-Wide-Association-Studies-GWAS) |
| 標準偏差 | 個々の値がどれほどばらつくかを表す量 | [NISTの平均と区間推定](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| 平均の標準誤差 | 平均値の推定がどれほどばらつくかを表す量。個々の値のばらつきや信頼区間とは区別する | [NIST](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |

2026-10-01確認。図の点・棒・誤差棒が何を表すかは、その論文の図注で確かめる。
