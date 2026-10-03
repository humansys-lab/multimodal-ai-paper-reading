# マルチモーダルAIの活用方法と限界を知る

京都大学 2026年度 機械システム学セミナー No.16。
担当：加藤祥太、加納学
Paper2Agentの図1・2とMethodsで論文の読み方を学び、The AI Scientistへ応用します。共通の初読・再読は、全員が同じPaper2Agentの版・範囲・3問を使います。

第1日：2026年10月3日 10:00–17:30（17:30–18:00は任意相談）。第2日：10月31日 10:00–17:00。

## 最初に開くもの

**[当日の短い手順書](docs/student_quickstart.md)**に、最終スライドに対応するNotebook・入力ファイル・操作順・提出方法をまとめました。学生向けZIPは教員から配布します。接続設定と個別キーは別途受け取ってください。

- [事前学習](docs/prework.md) → [当日の進め方](docs/start_here.md) → [演習カード](activities/day1.md)
- [GUIの使い方](docs/gui_guide.md)・[Notebookの操作とFAQ](docs/notebook_guide.md)・[困ったとき](docs/troubleshooting.md)
- [読解の記録](worksheets/reading_record.md)・[Methodsと別論文の記録](worksheets/methods_and_transfer.md)
- [課題](assignments/homework.md)・[発表](assignments/presentation.md)・[最終レポート](assignments/report.md)
- [用語集](docs/glossary.md)・[説明と原著論文の対応](docs/lecture_references.md)

## Colabで開く

**02はOpenAI APIの入門実習用です。** 文章・画像・PDFで質問する5つのセルに整理しました。質問・回答・気付きは各自のメモ帳へ残します。番号はファイルの識別用です。

| 使う時間・目的 | Notebook | 固定版へのリンク |
|---|---|---|
| 任意：自分の説明をNotebookで保存 | [00 準備と記録](notebooks/00_setup.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/00_setup.ipynb) |
| OpenAI APIの使い方：文章→画像・PDF | [02 API入門](notebooks/02_document_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/02_document_lab.ipynb) |
| 11:45：トークン・数値・候補確率を観察 | [03 小型モデル](notebooks/03_open_weight_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/03_open_weight_lab.ipynb) |
| 15:20：Methodsの必要な段落と対話 | [01 質問と対話](notebooks/01_dialogue_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/01_dialogue_lab.ipynb) |

1. 00〜02はCPU、03は「ランタイムのタイプを変更」でT4 GPUを選びます。個人PCへのGPU導入は不要です。
2. 各Notebookは1ファイルで実行できます。入出力例を読み、上からセルを実行します。00は追加ライブラリ不要。01・02は冒頭、03はモデル準備の`INSTALL=True`で必要なライブラリだけを入れます。教材コードのダウンロードやAPI送信は行いません。**03は導入後に必ずランタイムを再起動**し、`INSTALL=False`に戻して冒頭の保存先・関数定義セルを再実行してから「2」へ進みます。
3. **02は個別APIキーだけで準備できます。接続ファイルは不要です。** 2でモデルを選んでキーを伏字欄へ入力し、3で文章を送ります。4で配布資料の画像・PDFを選び、5で質問します。PDFは全ページを送ります。通常は`gpt-6-luna`、ほかに`gpt-6-sol`・`gpt-4.1-mini`を選べます。
4. 01を使う場合は別途`connection.local.yaml`が必要です。00・01・03の保存機能は必要に応じて利用できます。02の回答は各自でメモしてください。

各冊の入出力例と[Notebookガイド](docs/notebook_guide.md)を参照してください。APIの公式仕様・実測・未確認項目は[対応機能](docs/capability_audit.md)と[検証記録](docs/verification.md)へ。

## 実行状態・費用・提出

教材とNotebookは検査したコミットに固定し、mainの未検証更新を自動では取り込みません。公開の接続見本は空で、送信できません。直接APIとMacでの実測、新規Colab・講義用中継の未確認項目は[検証記録](docs/verification.md)に示します。

共通GUIはGemini for Education。個人の有料契約は必須ではありません。講義用APIは期間全体で1人10 USD分を確保し、学生全体にも使用量上限があります。利用期限は11月14日23:59（日本時間）。キーと接続情報は他者へ共有せず、接続ファイルは自分の講義用Colabでのみ使い、[利用案内](docs/api_usage.md)を確認してください。

HW1とHW2は両方必須。第2日は各5分の発表と5分の質疑、合わせて10枚以下です。発表資料は10月30日23:59、最終レポートは11月14日23:59までに、指定SlackチャンネルへPDFを提出します。個人記録は手元に保存し、自動収集・自動採点は行いません。

## 開発時の確認

```bash
uv sync --frozen
uv run pytest -q -m "not live"
uv run python scripts/check_course.py --mode structure
uv run python scripts/check_notebooks.py --execute-offline
uv run python scripts/embed_notebook_support.py --check
uv run python scripts/check_public_release.py
```

配布準備は別に`uv run python scripts/check_course.py --mode readiness`で確認します。未検証・未確認項目があれば終了コード1です。[実装状況](IMPLEMENTATION_STATUS.md)・[確認事項](DECISIONS.md)を参照してください。

[授業仕様](PLAN.md)・[自習ガイド](docs/self_study.md)・[利用条件](LICENSES.md)。原論文PDF、元PPTX、解答付き資料、秘密設定、個人記録は公開対象に含めません。
