# Notebookの操作：準備・質問・確認・保存

説明文の下にPythonの実行欄（セル）が並びます。上から順に実行します。`True`は実行、`False`は実行しない指定です。質問は自分で書き、資料・履歴を送信前に確認します。

| Notebook | 使う場面 | 必要なライブラリ |
|---|---|---|
| 00 準備と記録 | 朝のAIなしの説明を保存 | 設定と保存の補助。API送信なし |
| 01 対話 | 質問・例示・根拠の比較、再読、Methods、別論文 | OpenAI SDKと設定・記録の補助 |
| 02 画像・PDF | 元画像と縮小画像の比較、明示したPDFページ | 画像を使うセルでPillow、PDFを使うセルでpypdf |
| 03 公開重みモデル | パラメータ数、トークン、埋込み、確率、短い生成 | PyTorchとTransformers。accelerateや量子化ライブラリは使わない |

## 最初の準備

Colabは[README](../README.md#colabで開く)の固定版を開き、`PREPARE_COLAB=True`で取得します。準備コードと教材ZIPはハッシュを照合します。Macでは教材フォルダの仮想環境を使い、Falseのまま実行します。公開準備が未完了の版は、Colab取得をエラーで止めます。

00〜02はCPU。03はColab T4を指定します。Colab実機の動作・10名のGPU割当ては未確認です。

## 00：AIを使わない記録

共通の論文・版・範囲・3問を確認し、`annotations`へ自分の説明・根拠・不明点を記入します。`None`は前の記入を保持。`SAVE=True`でJSONLとMarkdownを保存します。APIは呼びません。

## 01・02：明示した条件で1回送る

1. 教員が配布する検証済み`runtime_path`と活動を指定。質問は`question`へ記入。
2. 01は`source_excerpt`と元位置。02は`PREPARE_IMAGE=True`で画像表示、必要なときだけ`RESIZE=True`で指定幅へ縮小。PDFは別セルの`PREPARE_PDF=True`と物理ページ番号を使う。
3. プレビューで送信する質問・全履歴・入力の由来を確認。比較時は`conversation_mode='new'`にする。
4. 教員が案内した送信許可を設定し、`SEND=True`で1回送信。キーは専用入力欄に入れる。公開の空設定では停止する。
5. `annotations`へ本人の説明・根拠・修正を書く。`SAVE=True`で保存。次の質問は`START_NEXT_RUN=True`で新しい番号を作る。

モデルを比べる場合は、モデルごとの検証済み設定ファイルを明示して新規会話にします。失敗しても別モデルに自動変更しません。同じ実行番号を再送できません。

### 教員が案内する送信許可の書式

実際の承認者・対象・認証経路・回数・上限を教員が埋めて案内します。空欄や対象不一致のままでは送信できません。金額停止はサーバで別に検証する必要があります。

```python
permission = LivePermission(
    approved_by='', scope='', route=runtime['route'], model=runtime['model'],
    authentication_route='', usd_limit=0, request_limit=0,
)
```

## 03：中の計算を観察する

`INSTALL=True`は依存取得時だけ。`DEVICE='cuda'`はColab、`'mps'`はMac。初回取得だけ`ALLOW_DOWNLOAD=True`。`LOAD_MODEL=True`で読みます。GPUが使えない場合は停止します。

`OBSERVE=True`で、実パラメータ数→トークン→埋込み→softmaxによる次トークン確率の順に見ます。`PROMPT`を記入し`PREVIEW=True`でテンプレートを確認。`RUN=True`で生成します。出力が`output_limit`なら未完了です。

`SAVE=True`は生結果のJSON保存。論文比較は`SAVE_READING=True`でJSONL/Markdownも保存できます。MethodsとThe AI Scientistは、朝と再読の記録から分離されます。入力上限2,048、出力上限128トークン。長い論文全体は送らず、必要な段落を明示的に選びます。

## 閉じる前に

ColabのFiles欄から、教材フォルダ内の`outputs/`の保存ファイルをダウンロードします。再起動で消える場合があります。個人の記録・キー・接続情報を公開共有しません。課題の提出は指定SlackへのPDFです。
