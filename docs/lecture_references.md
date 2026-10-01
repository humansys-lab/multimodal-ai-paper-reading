# 講義の説明と原著論文の対応

学生が読む研究論文はPaper2AgentとThe AI Scientistの2報。下の基礎論文は説明の根拠で、追加の必読課題ではない。図を転載する場合の利用条件は別に確認する。原著の性能値を、今回のモデル・日本語読解へそのまま当てはめない。

| 講義で説明すること | 原著・公式資料と見る場所 | 説明の範囲 |
|---|---|---|
| トークンから文脈を使って次を予測 | Vaswani et al., [Attention Is All You Need](https://arxiv.org/abs/1706.03762), §3; Brown et al., [Language Models are Few-Shot Learners](https://arxiv.org/abs/2005.14165), §2 | Transformer原著は翻訳用encoder–decoder。講義の自己回帰生成の概念図と同じ構造だとは説明しない |
| 指示に応えるための事後学習 | Ouyang et al., [Training language models to follow instructions with human feedback](https://arxiv.org/abs/2203.02155), §3, Fig.2 | 教師データ・人の比較・学習の流れを示す。現行の全サービスが同じ工程とは限らない |
| Zero-shot / Few-shot | Brown et al. (2020), §2.1, Fig.2.1 | 入力に例を入れる。会話中に重みを再学習することとは区別 |
| 例示の何が効くか | Min et al., [Rethinking the Role of Demonstrations](https://aclanthology.org/2022.emnlp-main.759/), §3–4 | 入力分布・ラベル・形式の影響を調べた分類等の実験。誤った例が一般に有効とは言わない |
| 説明過程を例として与えるCoT | Wei et al., [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903), §2, Fig.1, §3 | 途中の説明を含む少数例。課題・モデル規模によって結果が変わる |
| 例なしで段階的な説明を促す | Kojima et al., [Large Language Models are Zero-Shot Reasoners](https://arxiv.org/abs/2205.11916), §3, Fig.2 | Zero-shot CoT。原著の二段階の手順と、授業の短い指示の比較を区別 |
| 説明文と内部の計算は一致するとは限らない | Turpin et al., [Language Models Don't Always Say What They Think](https://arxiv.org/abs/2305.04388), §3–4 | もっともらしい理由も原文で確かめる。非公開思考の取得を課題にしない |
| 道具の実行結果を次の判断へ返す | Yao et al., [ReAct](https://arxiv.org/abs/2210.03629), §2, Fig.1 | 計画・行動・観察を概念として説明。発言中の「検索した」と実行履歴を区別 |
| 検索した資料を回答に使う | Lewis et al., [Retrieval-Augmented Generation](https://arxiv.org/abs/2005.11401), §2 | 必要になった時の用語補足。検索器・生成器の実装は授業で行わない |
| MCPのホスト・クライアント・サーバ | [MCP Architecture overview](https://modelcontextprotocol.io/docs/2026-07-28/learn/architecture) | 通信規約の公式説明。論文の実装と仕様版が一致すると仮定しない |
| 図を処理する視覚言語モデル | Liu et al., [Visual Instruction Tuning](https://arxiv.org/abs/2304.08485), §3, Fig.1 | 画像の特徴と言語を結ぶ一例。全VLMの非公開内部構造を代弁しない |
| PDFをAPIに送るときの処理 | [OpenAI File inputs](https://developers.openai.com/api/docs/guides/file-inputs) | テキストと各ページ画像の入力を説明。授業中継の実測とは別 |
| 画像生成と視覚言語行動モデル | Ho et al., [Denoising Diffusion Probabilistic Models](https://arxiv.org/abs/2006.11239), §2–3; Brohan et al., [RT-2](https://arxiv.org/abs/2307.15818), §3 | 画像出力・動作出力への拡張を概念紹介。実装・ロボット操作は行わない |
| 論文を使える道具にする | Miao et al., [Paper2Agent](https://doi.org/10.1038/s41586-026-11044-y), Fig.1–2、Methods | Overview・具体例・検証の範囲を分ける |
| 研究の工程を自動化する | Lu et al., [The AI Scientist](https://doi.org/10.1038/s41586-026-10265-5), Fig.1、Human evaluation results、Limitations | 自動査読・人間の査読・人の選別を分ける |

## Prompt Engineering Guideの使い方

[日本語版](https://www.promptingguide.ai/jp)の[Few-shot](https://www.promptingguide.ai/jp/techniques/fewshot)と[CoT](https://www.promptingguide.ai/jp/techniques/cot)を、説明順や短い例の参考にする。技術的主張の出典は上の原著に戻る。Webガイドの例や原図を無断で丸ごと転載しない。

## 授業用の比較例（初回読解後に提示）

次の人工例は仕組みの説明用。実際のモデル応答をまだ埋めていない。

| 条件 | 学生が実際に入力する例 |
|---|---|
| 例なし | 「文を予定／報告に分類してください。文：明日実験します。分類：」 |
| 少数例付き | 「文：明日提出します。分類：予定／文：昨日提出しました。分類：報告／文：明日実験します。分類：」 |
| 答えだけの例 | 「赤2個と青1個の合計は？ 答え：3個。赤3個と青2個の合計は？」 |
| 途中の説明付きの例 | 「赤2個と青1個の合計は？ 説明：2+1=3。答え：3個。赤3個と青2個の合計は？」 |

少数例とCoTを一度に全部変えず、同じ問題・モデル・新規会話で一つずつ比較する。簡単な例なので差が出ない可能性もある。改善や失敗を捏造せず、実際の結果を記録する。

論文へ戻る時は「どの記述からそう言えるか」「図注と本文のどこが必要か」「背景知識とこの論文の結果を分けて説明してほしい」を自分の問いに合わせて書く。CoT原著の数理課題での改善を、論文読解の改善の証明にはしない。

書誌データ：[references.bib](../materials/references.bib)。参照確認日2026-10-01。
