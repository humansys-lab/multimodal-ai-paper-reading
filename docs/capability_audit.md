# 機能・経路の確認記録

確認日：2026-09-30〜2026-10-01。公式説明と、この教材で通した処理を分ける。費用・応答時間・失敗の詳細は[検査結果](verification.md)を参照。

| 機能・モデル | 一次資料で確認した仕様 | 今回の実測 | 授業経路の状態 |
|---|---|---|---|
| OpenAI gpt-4.1-mini | [モデル資料](https://developers.openai.com/api/docs/models/gpt-4.1-mini)：Responses対応、画像入力、固定版2025-04-14、入力0.40・出力1.60 USD/100万トークン | SDK 2.54.0、直接OpenAI。短文・履歴・PNGとNotebook送信/保存を確認。計30回の内訳は検査結果参照 | Colab→LiteLLMはnot_run |
| PDF入力 | [公式ガイド](https://developers.openai.com/api/docs/guides/file-inputs)：テキストと各ページ画像が入力になる | ラベル付き2条件pass、図読取・形式違反4条件fail。ラベルなしPNGはpass。HTTP成功や文字ラベルの回答だけで図の理解を認定しない | PDF対応を実測済みにしない。原因未特定 |
| 保存・保持 | [公式資料](https://developers.openai.com/api/docs/guides/your-data)：store=Falseでも不正利用監視ログ等の保持は別 | 全30回store=False。自作PDF 1件をFiles APIへ作成し、そのIDだけ削除して確認 | 講義用中継のログ・保持は未確認 |
| Qwen3-0.6B | [公開元](https://huggingface.co/Qwen/Qwen3-0.6B)：公開重み、テキストモデル、Apache 2.0 | revision c1899de289a04d12100db370d81485cdf75e47ca、torch 2.8.0、transformers 4.57.6。Mac MPSでトークン・埋め込み・候補・生成・保存pass。明示したCPUでも観察・生成pass | Colab T4（16 GB）は対象確定、実機not_run |
| 10セッションの同時利用 | 公式説明から授業中継の性能は仮定しない | 直接APIの独立した10セッションで10/10 pass、最大3.117秒。1回の限定試験 | 講義中継・DB停止・個人別予算はnot_run |
| Colab GPU | [Google公式FAQ](https://research.google.com/colaboratory/faq.html)：利用可能量と割当て機種は変動 | 今回はMacだけで実測 | T4の利用可能性・ピーク使用量・10名同時割当ては未確認 |

試験用の直接接続設定はGit対象外。配布用のモデルID・機能・中継版・予算停止を、今回の結果から自動確定しない。別モデル・固定回答・別入力方式への自動フォールバックは実装していない。

## 新時間割の2モデル比較に向けた限定試験（2026-10-01）

[GPT-4.1公式資料](https://developers.openai.com/api/docs/models/gpt-4.1)と[mini公式資料](https://developers.openai.com/api/docs/models/gpt-4.1-mini)でResponses・画像入力・固定版・単価を確認。`gpt-4.1-2025-04-14`と`gpt-4.1-mini-2025-04-14`を直接OpenAIへ各2回、同じ自作短文とPNGで実測し、4/4成功。出力上限512、再試行0。返却トークンによる概算計0.0032468 USD。請求画面は未確認。

授業中継、Colab、論文入力、PDF、長いMethodsの正確性の成功には読み替えない。`second_api_model`の授業配布判定はnot_runのまま。最初の出力上限200の設定は送信前に拒否され、APIを呼んでいない。確認済み512へ明示的に修正して上の試験を行った。
