# 小型モデルでLLMの計算を観察する

[観察Notebook](../notebooks/03_open_weight_lab.ipynb)は、11:45からの12分間で使います。個人PCへのGPU導入は不要です。実行手順は[Notebook操作ガイド](notebook_guide.md#03中の計算を観察する)にまとめています。

## 何を見るか

1. 「京都の名物は」をトークンとIDへ分ける。文字数とトークン数を比べる。
2. 各IDに対応する数値の列（埋込み）を見る。行数はトークン数、列数はモデルの表現の次元。
3. 次のトークン候補を確率へ変換する。上位5件の確率の合計と、語彙全体の合計を区別する。

時間に余裕があれば、文や質問を一つ変えて生成します。候補確率は事実の正しさを表す確率ではありません。計算が完了しても誤答はあり、生回答と自分の説明を分けて保存します。

## モデルと環境

[Qwen3-0.6B](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/README.md)の公開重みを固定版で使います。実パラメータ数596,049,920。Apache 2.0、`trust_remote_code=False`、safetensors、思考モードOFF。導入するのはPyTorch 2.8.0、対応するtorchvision 0.23.0、Transformers 4.57.6です。

| 環境 | 明示する設定 | 確認状況 |
|---|---|---|
| Colab T4（16 GB） | `DEVICE='cuda'`、float16 | 対象環境。実機試験は未実施 |
| 教員のMac | `DEVICE='mps'`、float16 | キャッシュから読込み、観察・生成・保存を実測 |
| CPU | `DEVICE='cpu'`、float32 | Macで短い入力5件、Linuxで実Notebookの9セルを確認。GPU障害時に自動選択しない |

入力は2,048、出力は128トークン以下。重みだけで約1.2 GBあり、計算用メモリは別に必要です。[Colab公式FAQ](https://research.google.com/colaboratory/faq.html)のとおり、GPU機種・利用枠・割当ては変動します。

## 取得と保存

初回はネット接続が必要です。今回のMacでは、新しいキャッシュへの取得から読込みまで約119秒でした。Colabや教室の回線の所要時間は未確認なので、12分の観察前に準備を終えます。教材の準備後に`INSTALL=True`で依存を導入した後、必ずランタイムを再起動します。`INSTALL=False`へ戻して冒頭の保存先・関数定義セルを再実行し、「2」で`ALLOW_DOWNLOAD=True`で固定した重みを取得します。取得済みのローカル環境では両方をOFFにし、`LOAD_MODEL=True`で読み込みます。選んだ機種を使えない場合は停止します。

推論はモデルを読み込んだ計算機で行います。外部APIへの送信・API料金はありません。Colab自体の利用枠とは別です。

`SAVE=True`で`outputs/open-weight/`へJSONを新規保存します。説明を書き直して再保存しても以前のファイルは残ります。論文の読解記録を作る場合は生成前に活動を指定し、`SAVE=True`でJSONLとMarkdownも一度に保存します。終了前にFiles欄からダウンロードしてください。

[検証記録](verification.md)は実測の条件と未実施項目を示します。自分で観察した後に[教員の実測例](../examples/README.md)も参照できます。
