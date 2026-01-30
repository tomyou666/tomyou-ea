# 未実装項目（TODO）

インターフェース設計書で定義済みだが、まだ実装されていない項目をまとめる。

---

## 一覧

| 項目 | 設計書での定義 | 備考 |
|------|----------------|------|
| **応答待ち・タイムアウト・リトライ・リクエストID** | 3.0 応答待ち・タイムアウト・リトライとリクエストID | 応答待ち最大時間デフォルト 3 秒、リトライ 3 回、リクエスト/レスポンスに request_id を追加して id で検証。3 回すべて失敗時はエラー。MT4 側（応答に request_id を含める）・Python 側（タイムアウト・リトライ・request_id 検証）ともに未実装 |
| **PriceInfo** | 2.3 価格情報応答 / 3.1.3 価格情報取得（action = "PRICE_INFO"） | Python → MT4 で `PRICE_INFO` + **request_id** 送信、MT4 → Python で **request_id**, point, digits, pips を JSON 返却。request_id で応答を検証。MT4 EA 側・Python 側ともに未実装 |
| **OrderInfo** | 2.4 注文情報応答 / 3.1.4 注文情報取得（action = "ORDER_INFO"） | Python → MT4 で `ORDER_INFO` + **request_id**（+ ticket）送信、MT4 → Python で **request_id**, count, orders（ticket, status, symbol, order_type, lots, open_price, sl, tp, open_time, close_time, profit 等）を JSON 返却。request_id で応答を検証。MT4 EA 側・Python 側ともに未実装 |
| **ペンディング約定通知（pending_opened）** | 2.5 ペンディング約定通知 | 指値・逆指値のペンディングが約定してポジションがオープンした際に、MT4 が Python へリアルタイムで `type: "pending_opened"` の JSON を PUSH 送信。Python 側で `on_pending_opened` 等のコールバックで受信・処理。MT4 EA 側（OnTick 内での検知・送信）・Python 側ともに未実装 |

---

*随時、実装完了した項目は削除または「完了」に更新する。*
