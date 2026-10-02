# マルチモーダルAIの活用方法と限界を知る

京都大学 2026年度 機械システム学セミナー No.16。担当：加藤祥太。Paper2Agentの図1・2とMethodsで論文の読み方を学び、The AI Scientistへ応用します。共通の初読・再読は、全員が同じPaper2Agentの版・範囲・3問を使います。

第1日：2026年10月3日 10:00–17:30（17:30–18:00は任意相談）。第2日：10月31日 10:00–17:00。

## 最初に開くもの

- [事前学習](docs/prework.md) → [当日の進め方](docs/start_here.md) → [演習カード](activities/day1.md)
- [GUIの使い方](docs/gui_guide.md)・[Notebookの操作とFAQ](docs/notebook_guide.md)・[困ったとき](docs/troubleshooting.md)
- [読解の記録](worksheets/reading_record.md)・[Methodsと別論文の記録](worksheets/methods_and_transfer.md)
- [課題](assignments/homework.md)・[発表](assignments/presentation.md)・[最終レポート](assignments/report.md)
- [用語集](docs/glossary.md)・[説明と原著論文の対応](docs/lecture_references.md)

## Colabで開く

最初に使う順に並べています。00は相互説明後、01は再読と別論文への応用でも再利用します。番号はファイルの識別用です。

| 使う時間・目的 | Notebook | 固定版へのリンク |
|---|---|---|
| 10:15・15:40後：自分の説明を朝と午後に保存 | [00 準備と記録](notebooks/00_setup.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/a330f4cfb335c67c4092e564c75f26e8b1baca6c/notebooks/00_setup.ipynb) |
| 11:45：トークン・数値・候補確率を観察 | [03 小型モデル](notebooks/03_open_weight_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/a330f4cfb335c67c4092e564c75f26e8b1baca6c/notebooks/03_open_weight_lab.ipynb) |
| 11:57・15:10・16:15：質問の比較、再読、別論文 | [01 質問と対話](notebooks/01_dialogue_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/a330f4cfb335c67c4092e564c75f26e8b1baca6c/notebooks/01_dialogue_lab.ipynb) |
| 13:30・14:20：図2、元画像と縮小画像を比較 | [02 画像・PDF](notebooks/02_document_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/a330f4cfb335c67c4092e564c75f26e8b1baca6c/notebooks/02_document_lab.ipynb) |

1. 00〜02はCPU、03は「ランタイムのタイプを変更」でT4 GPUを選びます。個人PCへのGPU導入は不要です。
2. 各Notebookは1ファイルで実行できます。入出力例を読み、上からセルを実行します。00は追加ライブラリ不要。01・02は冒頭、03はモデル準備の`INSTALL=True`で必要なライブラリだけを入れます。教材コードのダウンロードやAPI送信は行いません。
3. 01・02は教員から`connection.local.yaml`と個別APIキーを別々に受け取ります。02の論文画像は`paper2agent_page4.png`です。各Notebook冒頭に、ファイル一覧・Colabへのアップロード・記入欄・実行順を載せています。キーは送信時の専用入力欄にだけ入れます。公開の`connection.example.yaml`は学生用の接続設定ではありません。
4. 保存セルを実行し、Files欄から`outputs/`の記録をダウンロードします。Colabのランタイムが削除されると、そこに保存したファイルも消えます。

朝の最初のAI利用は教員が案内するGUIです。03は初回のモデル取得に時間がかかるため、教員の案内に合わせて演習前に準備します。操作の詳細は[Notebookガイド](docs/notebook_guide.md)にあります。

## 実行状態・費用・提出

教材とNotebookは検査したコミットに固定し、mainの未検証更新を自動では取り込みません。公開の接続見本は空で、送信できません。直接APIとMacでの実測、新規Colab・講義用中継の未確認項目は[検証記録](docs/verification.md)に示します。

共通GUIはGemini for Education。個人の有料契約は必須ではありません。講義用APIは期間全体で1人10 USD分を確保し、学生全体にも使用量上限があります。利用期限は11月14日23:59（日本時間）。キーと接続情報は共有・アップロードせず、[利用案内](docs/api_usage.md)を確認してください。

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
