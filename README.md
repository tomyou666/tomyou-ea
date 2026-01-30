# tomyou-ea

MT4（MetaTrader 4）と Python を ZeroMQ で接続し、ティック配信・注文送受信を行う**自動売買システム**のリポジトリです。

## 概要

- **MT4 クライアント（EA）**: `client/main.mq4` — ティックを CSV で送信し、注文コマンドを JSON で受信
- **Python サーバー**: FastAPI + ZeroMQ — ティックを受信して戦略・コアロジックで処理し、注文を JSON で MT4 に送信

通信は **ZeroMQ（PUSH/PULL）** のみで、デフォルトでは **5555**（MT4→Python 受信）、**5556**（Python→MT4 送信）を使用します。

## 主な機能

| 機能 | 説明 |
|------|------|
| ティック配信 | MT4 が指定間隔で Bid/Ask/スプレッド/時刻を CSV で Python に送信 |
| 注文送信 | Python から成行・指値・逆指値の新規注文、および決済を JSON で MT4 に指示 |
| 注文結果通知 | MT4 が注文成否・決済結果を JSON で Python に返却 |
| 戦略 | サンプルとして Simple 戦略・MA クロスオーバー戦略を実装 |
| バックテスト | CSV ヒストリカルデータを用いたバックテスト対応（processor / core_logic） |

## ディレクトリ構成

```
tomyou-ea/
├── client/                    # MT4 EA（MQL4）
│   └── main.mq4
├── server/                    # Python サーバー
│   ├── app_server/
│   │   ├── config/            # 設定（DI・trading_settings）
│   │   ├── model/trading/     # DTO（TickDto, OrderCommand 等）
│   │   ├── routers/           # FastAPI ルーター
│   │   ├── service/
│   │   │   ├── core_logic/    # 戦略実行・注文判断
│   │   │   ├── order/         # 注文送信（mock / mt4）
│   │   │   ├── processor/     # ティック・CSV 処理
│   │   │   └── strategy/     # 戦略（simple, ma_crossover）
│   │   └── main.py
│   ├── resources/             # setting.ini 等
│   ├── tests/
│   └── pyproject.toml
├── docs/                      # 設計書・TODO
│   ├── インターフェース設計書.md
│   └── TODO.md
└── README.md
```

## 必要環境

### MT4 側

- MetaTrader 4
- **mql-zmq**（[dingmaotu/mql-zmq](https://github.com/dingmaotu/mql-zmq)）
- **JAson**（[vivazzi/JAson](https://github.com/vivazzi/JAson)）— JSON シリアライズ
- `libzmq.dll`, `libsodium.dll` を MT4 の Libraries フォルダに配置

### Python 側

- Python 3.11+
- パッケージ管理: **uv** 推奨（`pyproject.toml` / `uv.lock`）

## セットアップ・起動

### 1. Python サーバー

```bash
cd server
uv sync
# 開発時は resources.develop/setting.ini を編集可能
uv run uvicorn app_server.main:app --host 0.0.0.0 --port 8000
```

- ZeroMQ: 受信ポート **5555**、送信ポート **5556**（`resources/setting.ini` または `resources.develop/setting.ini` の `[ZMQ]` で変更可能）
- API: `http://localhost:8000`（FastAPI）

### 2. MT4 EA

1. `client/main.mq4` を MT4 の `Experts` に配置
2. 必要なライブラリ（mql-zmq, JAson, DLL）を導入
3. チャートに EA をアタッチ
4. 入力パラメータで `ServerAddress`（例: `tcp://localhost`）、`PushPort`（5555）、`PullPort`（5556）を Python サーバーと一致させる

### 3. 環境変数（オプション）

`server/.env.example` をコピーして `.env` を作成し、JWT・DB 等を設定。ティック＋注文のみ利用する場合は必須ではありません。

## 通信仕様（概要）

| 方向 | 内容 | 形式 |
|------|------|------|
| MT4 → Python | ティック | CSV: `symbol,bid,ask,spread,time` |
| MT4 → Python | 注文結果 | JSON: `{"type":"order_result","ticket":...,"status":"SUCCESS"}` 等 |
| Python → MT4 | 注文・決済 | JSON: `{"action":"ORDER",...}` / `{"action":"CLOSE","ticket":...}` |

詳細は [docs/インターフェース設計書.md](docs/インターフェース設計書.md) を参照してください。

## テスト

```bash
cd server
uv run pytest
```

## ドキュメント

- [インターフェース設計書](docs/インターフェース設計書.md) — MT4–Python 間のデータ形式・ポート・DTO 対応
- [TODO](docs/TODO.md) — 未実装項目（例: PriceInfo）

## ライセンス

プロジェクト固有のライセンス表記が無い場合は、利用時は各依存ライブラリのライセンスに従ってください。
