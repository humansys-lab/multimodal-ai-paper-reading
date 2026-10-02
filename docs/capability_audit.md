# APIとモデルの対応確認

更新：2026-10-02。公式資料で確認した仕様と、経路を通した実測を区別します。[検証記録](verification.md)に試験条件・費用・残項目をまとめています。

| 対象 | 公式の仕様・一次資料 | この教材での実測 | 未確認 |
|---|---|---|---|
| GPT-4.1 mini / GPT-4.1 | [mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)、[4.1](https://developers.openai.com/api/docs/models/gpt-4.1)：Responses、テキスト・画像入力、2025-04-14固定版 | OpenAI SDK 2.54.0から直接接続。新規・継続対話、2モデルの同じ質問、保存 | Colab→講義用LiteLLM |
| 画像・PDF | [画像入力](https://developers.openai.com/api/docs/guides/images-vision)、[PDF入力](https://developers.openai.com/api/docs/guides/file-inputs)：PDFは本文とページ画像を扱う | 元PNG・明示した縮小PNG・選択ページPDFで応答取得。縮小画像とPDFで数値の誤読も観察 | 論文全体の精度、講義用中継での対応 |
| データの保持 | [OpenAIのデータ管理](https://developers.openai.com/api/docs/guides/your-data)：APIデータを既定で学習しない。`store=False`でも不正利用監視用の保持等は別 | 今回は全送信で`store=False`、Files APIを使わずインライン入力 | 中継のログ・保持・削除条件 |
| Qwen3-0.6B | [固定版モデルカード](https://huggingface.co/Qwen/Qwen3-0.6B/blob/c1899de289a04d12100db370d81485cdf75e47ca/README.md)：公開重み、テキストモデル、Apache 2.0 | torch 2.8.0、transformers 4.57.6。Mac MPS、通信禁止で観察・生成・保存 | Colab T4の実行・ピークメモリ |
| 複数人の利用 | [Colab FAQ](https://research.google.com/colaboratory/faq.html)：GPU割当て・利用可能量は変動 | 2026-10-01に直接APIの独立10セッションが成功した記録あり | 学生10名のT4割当て、中継の同時利用・予算停止・DB停止 |

モデル・経路・入力方式を自動で切り替える処理はありません。公開の接続様式は未設定で、送信できません。直接APIの成功から、授業用中継の対応や予算制限の成功を推定しません。

## 単価と実費の区別

上記公式モデル資料の単価は、100万トークンあたりminiが入力0.40・出力1.60 USD、GPT-4.1が入力2・出力8 USDです。返却された利用量から試験費用を概算し、請求画面で確認した金額とは区別します。
