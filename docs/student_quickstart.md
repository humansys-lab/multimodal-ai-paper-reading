# 当日の手順書

京都大学「マルチモーダルAIの活用方法と限界を知る」／2026年10月3日

## 1. 最初に開くもの

配布ZIPを展開し、`day1_student_script_aligned.pdf`を開きます。スライドの指示に沿って読み、質問・回答・自分の考えは**各自のメモ帳等**に残します。

| ファイル | 役割 |
|---|---|
| `day1_student_script_aligned.pdf` | 教員が確定した講義スライド |
| `02_document_lab.ipynb` | OpenAI APIの入門：文章→画像・PDFで質問する |
| `03_open_weight_lab.ipynb` | トークン・数値・次の候補確率を観察する |
| `01_dialogue_lab.ipynb` | 必要な段落を貼り、対話を続ける場合に使う |
| `00_setup.ipynb` | Notebookで読解記録を残したい場合に使う |
| `materials/` | 原論文PDF 2報、図2の比較PNG 2枚 |

[GitHubの教材入口](https://github.com/humansys-lab/multimodal-ai-paper-reading)から「Colabで開く」を押します。手元のipynbなら、[Colab](https://colab.research.google.com/)の「ノートブックを開く」→「アップロード」で選べます。使う1冊だけ開けばよく、PCへのPython導入は不要です。

### 共通論文で読む範囲

Paper2Agentの**要旨p1、図1a・bと図注p3、p2右段の指定本文**です。本文は「We implemented Paper2Agent...」から「...across multiple papers simultaneously.」まで。朝と再読では同じ版・範囲・3問（主張・根拠・不明点）を使います。

AIの回答と本人の説明を分け、根拠となるページ・図をメモしてください。別論文についての結果は、この共通論文の記録と分けます。

<!-- PAGEBREAK -->

## 2. 02でAPIを使う

**CPUで実行できます。必要なのは個別APIキーです。02では接続ファイルは使いません。**

1. **1のINSTALL**をチェックして実行。OpenAIのライブラリを入れる。
2. **2のモデル**を選び、CONNECTをチェックして実行。伏字の欄へキーを入れる。
3. **3の三重引用符の間**に質問を書き、SENDをTrueにして実行。文章の回答を読む。
4. **4のUPLOAD**をチェックして実行し、画像・PDFを1つ選ぶ。
5. **5の三重引用符の間**にファイルへの質問を書き、SENDをTrueにして実行する。

料金がかかるのは3・5の送信だけです。質問を変える場合は3または5、資料を変える場合は4→5。毎回独立した質問で、前の会話は送りません。出力はメモ帳へ必要な部分をコピーします。

### ファイルと質問の例

| ファイル | 質問の例・確かめること |
|---|---|
| なし（3で文章だけ） | 「APIとは何ですか。身近な例を挙げて3文で説明してください。」 |
| `materials/fig2_full.png` | 「図2bの縦軸と横軸は何を表しますか。」原図のラベルと照合 |
| `materials/fig2_quarter.png` | 同じ質問をして、読める情報がどう変わるか確認 |
| `materials/Paper2Agent_Nature.pdf` | 「図1aのMCPサーバーの役割を、根拠のPDFページとともに説明してください。」 |
| `materials/ai_scientist_nature.pdf` | 自分で理解したい点を質問し、本文や図で確かめる |

これらは質問の例で、実測結果・模範解答ではありません。PNGは元の画像、**PDFは全ページを送信**します。ページを絞るなら、必要なページだけのPDFを先に用意します。

### モデルとエラー

通常はgpt-6-luna。gpt-6-sol、gpt-4.1-miniも選べます。変更したら2を再実行します。出力がincompleteなら理由を確認し、max_output_tokensによる終了の場合は2の上限を増やすか質問を絞ります。エラー時の自動再送はありません。

401・403はキーとモデル許可、429は利用上限や混雑を教員・TAへ確認します。タイムアウト時の課金は不明です。キーを画面写真・メモ・質問・GitHub・Slack・他のAIへ載せないでください。

<!-- PAGEBREAK -->

## 3. ほかのNotebookと提出

### 03：モデルの中の計算を観察する

ColabはT4 GPUを選びます。INSTALLをTrueにしてライブラリを導入後、**ランタイムを再起動**。INSTALLをFalseへ戻し、冒頭の保存先・関数セルを再実行してから2へ進みます。初回はALLOW_DOWNLOADをTrue、DEVICEはcuda、LOAD_MODELをTrueにします。

TEXTを書き、OBSERVEをTrueにして、トークン→埋め込み→候補確率を観察します。例として「京都の名物は」と「京都の観光名所は」を1文ずつ比べ、気付きをメモします。

### 01・00を使う場合

01は1aでライブラリ、1bで関数を準備し、2で別途受け取った`connection.local.yaml`を選びます。3aへ問い・原文・ページを記入、3bで内容確認、4で送信します。前の会話を続ける選択もできます。

00・01・03には任意で使える保存機能があります。保存した記録はランタイム終了前にPCへダウンロードします。操作の詳細はGitHubの「Notebookの操作とFAQ」へ。APIキー・接続設定は共通ZIPに含めません。

講義期間全体で1人10 USD分を確保し、学生全体にも上限があります。APIの利用は11月14日23:59まで。上限は教員がAPI側で管理します。

### Homeworkと提出

- **HW1・HW2は両方必須**。HW1はNature本誌またはScience本誌の掲載済みOpen Access原著から、Paper2Agent以外の関心ある1報を選び、研究内容と理解した過程を説明する。HW2は日常業務・学業・研究から用途を一つ選び、AIの使い方・確認結果・限界を説明する。
- **10月31日の発表**：HW1 5分＋HW2 5分＋質疑5分。2課題を合わせて10枚以下。発表PDFは**10月30日23:59**までに指定Slackへ。
- **最終レポート**：本文A4・4ページ以内。読解手順を含め、参考文献・必要なログは別添。**11月14日23:59**までに指定SlackへPDFを提出する。時刻は日本時間。

### 同梱原資料の出典

- **Paper2Agent**：Miao, J., Davis, J.R., Zhang, Y. et al., Nature (2026). [DOI:10.1038/s41586-026-11044-y](https://doi.org/10.1038/s41586-026-11044-y)。Nature掲載版PDF（2026-09-30取得）。[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/)。PDFは無改変。比較PNGは同じPDF p4全体を画像化・画素数変更したもので、内容の追記・切り取りはしていません。非商用授業用の共有です。
- **The AI Scientist**：Lu, C., Lu, C., Lange, R.T. et al., Nature 651, 914–919 (2026). [DOI:10.1038/s41586-026-10265-5](https://doi.org/10.1038/s41586-026-10265-5)。Nature掲載版PDF（2026-10-01取得）。[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。PDFは無改変。

資料はそれぞれの利用条件に従います。スライド・原論文を含む共通ZIPと、公開GitHubのNotebook・手順書は配布範囲が異なります。APIへの入力は教員が案内した経路・条件で行ってください。
