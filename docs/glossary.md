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

## 質問の工夫と学習

| 用語 | 最初の説明 | 参照 |
|---|---|---|
| パラメータ／重み | 学習で調整する数値。数が多いことだけでは、今回の問いで正しい保証にならない | Brown et al. (2020) |
| 事前学習 | 大量のデータから予測の仕組みを学ぶ工程 | Brown et al. (2020) |
| 事後学習 | 指示や人の評価等を使って振る舞いを調整する工程 | Ouyang et al. (2022) |
| Zero-shot | 解答例を入れずに作業を指示すること | Brown et al. (2020) |
| Few-shot | 少数の解答例を入力に添えること | Brown et al. (2020) |
| In-context learning | 入力中の指示や例に応じた振る舞い。ここでは重みの更新を伴わない | Brown et al. (2020) |
| Chain-of-thought（CoT） | 途中の説明を含む例や指示を使う方法。出力された説明を内部計算の完全な記録とは扱わない | Wei et al. (2022)、Kojima et al. (2022)、Turpin et al. (2023) |
| Softmax | 候補の数値を、合計1の確率へ変換する関数 | Vaswani et al. (2017) |
| Open weight | モデルの重みを入手できること。学習データ・全コードの公開とは別 | Qwenモデルカード |
| SLM | 比較的小さい言語モデル。全モデル共通の厳密な規模の境界ではない | この講義ではQwen3-0.6Bを使用 |

## 研究のMethodsで必要な用語

| 用語 | この講義での意味 |
|---|---|
| Tutorial | 手法の使い方を具体例で示す実行例 |
| Ground truth | 評価時に照合する参照結果。どのように作ったかも確認する |
| Rubric | 採点項目・基準を事前に定めたもの |
| Ablation study | 一部の仕組みを外すなどして、その部分の寄与を調べる実験 |
| Hyperparameter | 学習・実験の前に人や探索手順が設定する値 |
| Balanced accuracy | 各クラスの再現率を平均した指標。単純な全件正答率と区別する |
| VLA | 画像・言語から動作を扱う視覚言語行動モデル |

出典へのリンクと対象箇所は[講義の参考文献](lecture_references.md)にまとめる。初出時はスライドにも日本語の説明を付ける。
