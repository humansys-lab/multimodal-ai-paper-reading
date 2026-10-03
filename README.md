# マルチモーダルAIの活用方法と限界を知る

京都大学 2026年度 機械システム学セミナー No.16。
担当：加藤祥太、加納学
Paper2Agentの図1・2とMethodsで論文の読み方を学び、The AI Scientistへ応用します。共通の初読・再読は、全員が同じPaper2Agentの版・範囲・3問を使います。

第1日：2026年10月3日 10:00–17:30（17:30–18:00は任意相談）。第2日：10月31日 10:00–17:00。

## 最初に開くもの

**[当日の短い手順書](docs/student_quickstart.md)**に、最終スライドに対応するNotebook・入力ファイル・操作順・提出方法をまとめました。学生向けZIPと個別APIキーは教員から受け取ってください。02はキーだけで準備できます。01を使う場合は、別途配布する接続設定も使います。

- [事前学習](docs/prework.md) → [当日の進め方](docs/start_here.md) → [演習カード](activities/day1.md)
- [GUIの使い方](docs/gui_guide.md)・[Notebookの操作とFAQ](docs/notebook_guide.md)・[困ったとき](docs/troubleshooting.md)
- [読解の記録](worksheets/reading_record.md)・[Methodsと別論文の記録](worksheets/methods_and_transfer.md)
- [課題](assignments/homework.md)・[発表](assignments/presentation.md)・[最終レポート](assignments/report.md)
- [用語集](docs/glossary.md)・[説明と原著論文の対応](docs/lecture_references.md)

## Colabで開く

### まず02で、OpenAI APIを使う

**[02：文章・画像・PDFの実習をColabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/02_document_lab.ipynb)**

CPUで動きます。必要なのはNotebookと個別APIキー。追加するライブラリは`openai`だけで、`connection.local.yaml`やActivityの指定は不要です。

1. **ライブラリを準備**：1の`INSTALL`をチェックして実行する。
2. **モデルとキーを入力**：2でモデルを選び、`CONNECT`をチェックして実行。伏字の欄へ個別キーを入れる。
3. **文章で質問**：3の三重引用符の間に質問を書き、`SEND = True`で実行する。
4. **画像・PDFを選ぶ**：4の`UPLOAD`をチェックして実行し、配布資料から1ファイルを選ぶ。
5. **ファイルについて質問**：5に質問を書き、`SEND = True`で実行する。

**質問・回答・気付きは各自のメモ帳へ残します。** 記録・保存セルはありません。各質問は独立しており、過去の対話を含めません。同じ資料に別の質問をするなら5だけ、資料を変えるなら4→5を実行します。

- 画像はPNG・JPEG、**PDFは選んだファイルの全ページ**を送ります。ファイル名と質問の例はNotebook冒頭にあります。
- 通常は`gpt-6-luna`。`gpt-6-sol`・`gpt-4.1-mini`も選べます。変更したセルは再実行してください。
- 料金がかかるのは3・5の送信時です。キーはコード・質問・メモへ書かず、伏字の欄で入力します。

### Notebook一覧

番号はファイルの識別用です。必要な1冊を開いてください。

| 目的 | Notebook | 固定版へのリンク |
|---|---|---|
| OpenAI APIの使い方：文章→画像・PDF | [02 API入門](notebooks/02_document_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/02_document_lab.ipynb) |
| トークン・数値・候補確率を観察 | [03 小型モデル](notebooks/03_open_weight_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/03_open_weight_lab.ipynb) |
| Methodsの必要な段落を貼り、対話を続ける | [01 質問と対話](notebooks/01_dialogue_lab.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/01_dialogue_lab.ipynb) |
| 任意：自分の説明をNotebookで保存 | [00 準備と記録](notebooks/00_setup.ipynb) | [Colabで開く](https://colab.research.google.com/github/humansys-lab/multimodal-ai-paper-reading/blob/5957354d27a6a3f75054467bcd5f334c99470996/notebooks/00_setup.ipynb) |

各Notebookは1ファイルで実行できます。00〜02はCPU、03はT4 GPUを使います。個人PCへのGPU導入は不要です。

- **03**：モデル用ライブラリを`INSTALL=True`で導入後、**必ずランタイムを再起動**。`INSTALL=False`へ戻し、冒頭の保存先・関数定義セルを再実行してから「2」へ進みます。
- **01**：個別キーに加えて、教員から受け取った`connection.local.yaml`を使います。
- **00・01・03**：保存機能は必要に応じて利用できます。00は追加ライブラリ不要です。

詳しくは[Notebookの操作とFAQ](docs/notebook_guide.md)へ。APIの公式仕様・実測・未確認項目は[対応機能](docs/capability_audit.md)と[検証記録](docs/verification.md)に分けています。

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
