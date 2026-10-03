# APIとモデルの対応確認

## 採用モデル（2026-10-03）

教員の最新指定に合わせ、GPT-6.1 SolからGPT-6 Solへ訂正。教員は次の3モデルを採用し、API側の許可を設定したと申告。通常Notebookの選択肢をこの3つに限定します。料金はUSD／100万トークン、通常処理・短い入力・キャッシュなし。実費は利用量、推論量、画像/PDF処理で変わります。

| モデル・公式仕様 | 入力／出力料金 | Notebookの初期設定 | 直接APIの実測 |
|---|---|---|---|
| [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna) | 0.10／0.50 | reasoning.effort=none | pass：15:17 JSTの文章1回。画像・PDF・継続は未確認 |
| [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol) | 2.00／10.00 | reasoning.effort=low | pass：文章1回。継続・PNG・PDF・保存往復はこのモデルで未実施 |
| [GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini) | 0.40／1.60 | reasoningなし | pass：文章・継続・PNG・PDF、temperature=0.7、保存往復 |

2026-10-03 15:17 JST、Lunaは直接APIの短い文章送信に成功（HTTP 200／completed、3.13秒）。以前の403は今回発生しませんでした。確認範囲は[検証記録](verification.md)に示します。

最新の3モデル再確認はSDKを介さない直接HTTP／Responses API／store=False／再試行0。以前の画像・PDF試験はOpenAI SDK 2.54.0を使用。GPT-6.1 Solの以前の成功をGPT-6 Solへ流用しません。モデル名が返す実際の名前も記録します。GPT-4.1 miniはgpt-4.1-mini-2025-04-14が返ることを確認しました。別のモデルや未知の版を同じものとして受理しません。

- [推論設定の仕様](https://developers.openai.com/api/docs/guides/deployment-checklist)：LunaとGPT-6 Solはnoneを含む（[GPT-6 Solの仕様](https://developers.openai.com/api/docs/models/gpt-6-sol)）。推論有効時にtemperature・top_pは使えません。対応しない設定を黙って削除せず、エラーにします。
- [推論と使用量](https://developers.openai.com/api/docs/guides/reasoning)：推論トークンも出力上限・出力料金に含む。store=Falseでの継続用に暗号化データを受け取りますが、内部思考本文を表示する機能ではありません。
- [PDF入力](https://developers.openai.com/api/docs/guides/file-inputs)：PDFの本文とページ画像を扱う。detail未指定のautoはGPT-5.6以降でhigh、以前でlow。モデル比較には処理条件の差も含まれます。
- [旧モデルのPredicted Outputs](https://developers.openai.com/api/docs/guides/predicted-outputs)：GPT-4.1 mini等で既知文章の部分修正を速める機能。Chat Completions専用のため、このNotebookには実装せず参考メモとして紹介します。

高額なGPT-6 AstraやProモードは選択肢へ追加していません。回数・金額のhard limitは教員がAPI側で管理します。学生のキーでの利用可否、Colabや講義中継はこの直接試験とは別です。[今回の検証](verification.md)。

以下は過去の検証記録です。GPT-4.1（miniでないもの）は現在の採用モデルに含みません。

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
