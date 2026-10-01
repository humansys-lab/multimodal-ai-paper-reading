# マルチモーダルAIの活用方法と限界を知る

京都大学 2026年度 機械システム学セミナーの教材。Paper2Agentの図1・2とMethodsで読み方を学び、The AI Scientistへ応用します。共通初読・再読は同じPaper2Agentの版・範囲・3問です。

## 学生向けの入口

- [最初に読む案内](docs/start_here.md)・[事前学習](docs/prework.md)・[GUIの操作](docs/gui_guide.md)・[Notebookの操作](docs/notebook_guide.md)
- [当日の演習](activities/day1.md)・[読解の記録](worksheets/reading_record.md)
- [課題](assignments/homework.md)・[発表](assignments/presentation.md)・[最終レポート](assignments/report.md)
- Notebook：[00 準備](notebooks/00_setup.ipynb)、[01 対話](notebooks/01_dialogue_lab.ipynb)、[02 画像とPDF](notebooks/02_document_lab.ipynb)、[03 公開重みモデル](notebooks/03_open_weight_lab.ipynb)

## Colabで開く

[Notebookの操作とFAQ](docs/notebook_guide.md)・[2026-10-02の動作確認](docs/notebook_verification.md)。

| Notebook | 固定版へのリンク |
|---|---|
| 00 準備とAIなしの記録 | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/25cfb8ba2d831dd0af9e91ac97652bff90d8cb96/notebooks/00_setup.ipynb) |
| 01 質問と対話 | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/25cfb8ba2d831dd0af9e91ac97652bff90d8cb96/notebooks/01_dialogue_lab.ipynb) |
| 02 画像・PDFの入力 | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/25cfb8ba2d831dd0af9e91ac97652bff90d8cb96/notebooks/02_document_lab.ipynb) |
| 03 公開重みモデルの観察 | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/25cfb8ba2d831dd0af9e91ac97652bff90d8cb96/notebooks/03_open_weight_lab.ipynb) |

1. 00〜02はCPUで開きます。03だけは「ランタイムのタイプを変更」でT4 GPUを選びます。
2. 冒頭セルの `PREPARE_COLAB` をTrueにして実行します。ハッシュを検査して固定版の教材と依存関係を取得します。APIは呼びません。
3. 質問・送信する資料・新規/継続を自分で設定します。API接続情報と利用許可は教員の案内に従います。公開の空設定では送信できません。
4. 保存セルを実行し、00〜02はJSONLとMarkdown、03は生のJSON（読解記録を作る場合はJSONL/Markdownも）をColabのファイル欄からダウンロードします。再起動するとランタイム内のファイルは失われます。

Notebookと教材コードは検査したコミットに固定しています。mainの更新を自動では追いません。実際のColab/T4での起動はログイン待ちで未検証です。今回GitHubから再取得した版を、ローカルの準備済み環境で検査しています。


## 実行状態

授業用APIの接続設定は教員が個別に案内します。公開の空設定では送信できません。既定のNotebookは有料API・モデル取得・推論を実行しません。[検査の範囲](docs/verification.md)を確認してください。

GPUは必須ではありません。公開重みモデルの観察だけはColab T4を対象にしています。講義用APIは1人10 USD分を確保し、学生全体にも利用量上限があります。キーと接続情報は共有・アップロードしないでください。

発表とレポートは指定SlackチャンネルへPDFを提出します。個人の対話は手元へ保存し、自動収集や自動採点は行いません。

## 開発時の確認

```bash
uv sync --frozen
uv run pytest -q -m "not live"
uv run python scripts/check_course.py --mode structure
uv run python scripts/check_notebooks.py --execute-offline
uv run python scripts/check_public_release.py
```

配布準備は別に `uv run python scripts/check_course.py --mode readiness` で確認します。未検証項目があれば終了コード1です。

[授業の仕様](PLAN.md)は教員の正本から学生向けの節を抜粋しています。原資料、解答付きスライド、内部運用履歴、秘密設定は公開対象外です。[利用条件](LICENSES.md)を確認してください。

## 2報版への改訂

[演習カード](activities/day1.md)、[Methods](materials/papers/paper2agent_methods.md)、[別論文への応用](materials/papers/ai_scientist.md)、[説明と原著論文の対応](docs/lecture_references.md)。新しい範囲・設問は教員確認前。固定Colabリンクは2報版へ更新済みです。
