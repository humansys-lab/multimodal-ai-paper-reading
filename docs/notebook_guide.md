# Notebookの操作

## 02：OpenAI APIで文章・画像・PDFを使う

CPUで動きます。必要なのは教員から個別に受け取ったAPIキーとNotebookです。**接続YAML、Activityの指定、記録・保存セルはありません。**

1. **ライブラリ**：INSTALLをチェックして実行。追加するのは`openai==2.54.0`だけ。
2. **モデルとキー**：モデルを選び、CONNECTをチェックして実行。伏字欄へキーを入れる。この操作ではAPIへ質問を送らない。
3. **文章で質問**：三重引用符の間に質問を書き、SENDをTrueにして実行する。
4. **画像・PDFの選択**：UPLOADをチェックして実行し、1ファイルを選ぶ。拡張子から形式を判別するので、形式の選択やパスのコピーは不要。
5. **ファイルについて質問**：三重引用符の間に質問を書き、SENDをTrueにして実行する。同じファイルなら5だけ、別ファイルなら4→5。

画像はPNG・JPEG、PDFは**全ページ**を送ります。PDFを絞りたい場合は必要なページだけのファイルを先に用意します。アップロードのキャンセル・形式の不一致は停止し、前のファイルを送りません。自分のPCで実行する場合だけ、4のコードにある`local_path`へパスを指定します。

各送信は独立した質問で、過去の対話は含めません。記録はメモ帳等に、質問・モデル・入力資料・回答・自分で確かめたことを残します。共通論文の読解記録と別論文の結果を区別してください。

### モデル・出力長・エラー

選択肢は`gpt-6-luna`、`gpt-6-sol`、`gpt-4.1-mini`の3つ。モデルや出力上限を変えたら2も実行します。CONNECTを外せばキーを入力し直さず設定だけ変更できます。各質問は新規なので、以前のモデルの会話は混ざりません。

`incomplete`の理由が`max_output_tokens`なら、2の上限を増やすか質問を絞って再実行します。401・403は認証やモデル許可、429は利用上限や混雑を教員・TAへ確認してください。タイムアウト時の課金は不明です。失敗時の自動再試行・モデル切替はありません。

回答の表示だけでは内容の正しさは保証されません。原図・本文・出典で確認します。Web検索は実行しません。利用上限は教員がAPI側で管理します。キーはコードやメモへ書かず、他者へ共有しません。

### コードを読むとき

3・5の`client.responses.create`が送信箇所です。`input_text`が質問、`input_image`が画像、`input_file`がPDFです。`show_response`は回答と状態を表示するだけの短い関数です。必要なコードはすべて02内にあります。

2の`settings`がモデル・出力長・推論の設定です。GPT-4.1 miniでは`settings['temperature'] = 0.7`等を追加してばらつきを試せます。モデルの条件や旧モデルの機能は[対応機能](capability_audit.md)へ。

## 01：文章で対話を続ける（必要な場合）

01は以前の記録機能を保持しています。短いAPI入門には上の02を使います。

1. 1aでINSTALLをチェックして実行、1bで関数を準備。
2. 2でUPLOAD_CONNECTIONをチェックして実行し、個別に配布された`connection.local.yaml`を選ぶ。モデル・活動を選ぶ。キーは送信時の伏字欄へ入れる。
3. 3aに質問・原文・ページや節を書いて実行。3bで新規/継続を選び、送信内容を確認する。
4. 4のSENDで送信。必要なら5のSAVE・DOWNLOADでMarkdown/JSONLをZIPに保存する。

質問を変えるときは3aから。Homework切替は末尾の補足セルです。選定条件は[課題要項](../assignments/homework.md)を参照してください。

## 00：朝と相互説明後の記録

朝は`record_stage='朝：AIなしで読む'`。共通の論文・版・範囲・3問を確認し、`annotations`へ自分の説明・根拠・不明点を記入します。`None`は前の記入を保持。`SAVE=True`でJSONLとMarkdownを保存します。APIは呼びません。

15:40の相互説明後は`'午後：説明し直す'`へ変更して範囲の確認セルを実行し、説明を記入して保存します。朝と午後は別々の記録で、同じファイルへ保存できます。朝の記録は保存直後にダウンロードしてください。ランタイムが再起動した場合、午後のファイルと手元の朝のファイルを並べて見比べます。

## 03：中の計算を観察する

1. `INSTALL=True`でtorch 2.8.0・torchvision 0.23.0・Transformers 4.57.6を一度導入し、**必ずランタイムを再起動**。`INSTALL=False`に戻し、冒頭の保存先・関数定義セルを再実行してから「2」へ進む。`DEVICE='cuda'`はColab、`'mps'`はMac。初回取得は`ALLOW_DOWNLOAD=True`。`LOAD_MODEL=True`で、確認済みのライブラリ版を検査してから読み込む。機種や版が合わなければ停止する。
2. `OBSERVE=True`で、トークン→埋込み→softmaxによる次の候補確率を順に見る。計算コードは各セルにある。
3. 生成設定の`temperature`・`top_k`・`top_p`・`seed`は固定。意味は[用語集](glossary.md#notebookの生成設定を読む)で確認できる。`PROMPT`へ自分の問いを書き、`PREVIEW=True`で会話テンプレートを確認。`RUN=True`で生成する。問いを変えたら再プレビューする。
4. 本人の説明を`annotations`に記入し、`SAVE=True`で生回答と一緒にJSONへ保存する。保存OFFでは書き換わらず、同じ実行のファイルは上書きしない。

`output_limit`は出力上限で止まった途中の回答です。入力は2,048、出力は128トークン以下。失敗時に以前の回答を今回の結果として保存できません。

論文の読解記録も必要なら、**生成前に**`activity_id`を指定します。`SAVE=True`で、生のJSONに加えてJSONLとMarkdownも一度に保存します。生成時の活動・資料・入力位置を保存し、後から違う活動へ付け替えません。観察だけなら`activity_id=None`で構いません。

## 参照・検証

Colabの[標準フォーム](https://colab.research.google.com/notebooks/forms.ipynb)でモデルやチェック項目を選び、[files.upload](https://github.com/googlecolab/colabtools/blob/main/google/colab/files.py)でファイルを選びます。複数行の質問はコード欄で改行を保持します。画面用の追加ライブラリはありません。

OpenAI公式：[基本操作](https://developers.openai.com/api/docs/quickstart)・[画像入力](https://developers.openai.com/api/docs/guides/images-vision)・[PDF入力](https://developers.openai.com/api/docs/guides/file-inputs)。新しい02の実測範囲は[検証記録](verification.md)へ。
