# tomyou-ea

MT4（MetaTrader 4）と Python を ZeroMQ で接続し、ティック配信・注文送受信を行う**自動売買システム**のリポジトリです。

## 概要

- **MT4 クライアント（EA）**: `client/main.mq4` — ティックを CSV で送信し、注文コマンドを JSON で受信
- **Python サーバー**: FastAPI + ZeroMQ — ティックを受信して戦略・コアロジックで処理し、注文を JSON で MT4 に送信

通信は **ZeroMQ（PUSH/PULL）** で、デフォルトでは **5555**（MT4→Python 受信）、**5556**（Python→MT4 送信）を使用します。

## セットアップ後にできること

- **Python サーバーだけ**: この README の手順でサーバーを立ち上げ、`http://localhost:8000/docs` で API が動作していることを確認できます。
- **MT4 と連携する場合**: EA を導入し、ティック配信・注文送受信まで一通りつなげます。

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
│   │   ├── models/trading/    # DTO（TickDto, OrderCommand 等）
│   │   ├── routers/           # FastAPI ルーター
│   │   ├── domain/
│   │   │   ├── order/         # 注文送信（mock / mt4）
│   │   │   ├── sender/        # 命令部（payload 送信）
│   │   │   ├── strategy/     # 戦略（simple, ma_crossover）
│   │   │   └── ...
│   │   ├── application/      # ProcessService, TradingService
│   │   ├── infrastructure/   # 送信・repository
│   │   └── main.py
│   ├── resources/             # setting.ini（本番用）
│   ├── resources.develop/     # setting.ini（開発用）
│   ├── tests/
│   └── pyproject.toml
├── docs/
│   ├── 設計書.md
│   └── インターフェース設計書.md
└── README.md
```

## 必要環境

### Python 側

- **Python 3.11+**
- **uv**（パッケージ・仮想環境の管理に使用。本プロジェクトでは必須です。）
  - インストール: [uv 公式](https://docs.astral.sh/uv/) の手順に従ってください（例: `pip install uv` または公式のインストールスクリプト）。

### MT4 側

- MetaTrader 4
- **mql-zmq**（[dingmaotu/mql-zmq](https://github.com/dingmaotu/mql-zmq)）
- **JAson**（[vivazzi/JAson](https://github.com/vivazzi/JAson)）— JSON シリアライズ
- `libzmq.dll`, `libsodium.dll` を MT4 の Libraries フォルダに配置

## セットアップ・起動

### 1. Python サーバー

```bash
cd server
uv sync
uv run fastapi dev app_server/main.py --port 8000
```

- 初回の `uv sync` で依存関係がインストールされます。
- 起動後は **API**: `http://localhost:8000`（Swagger UI: `http://localhost:8000/docs`）。

### 2. MT4 EA の導入

1. `client/main.mq4` を MT4 の `Experts` フォルダに配置する。
2. 必要なライブラリ（mql-zmq, JAson）と DLL（`Libraries/libzmq.dll`, `Libraries/libsodium.dll`,`Include/JAson.mqh`）を MT4 の Libraries に導入する。
3. MT4 を起動し、チャートに EA をアタッチする。
4. EA の入力パラメータで以下を Python サーバーと合わせる。
   - **ServerAddress**: 例 `tcp://localhost`
   - **PushPort**: 5555（MT4→Python）
   - **PullPort**: 5556（Python→MT4）

### 3. 環境変数（オプション）

`server/.env.example` をコピーして `server/.env` を作成し設定できます。

## 設定

- **設定ファイル**: `server/resources/setting.ini` が本番用、`server/resources.develop/setting.ini` が開発用です。開発時は `resources.develop/setting.ini` を編集して使います。
- **[ZMQ]**: `recv_port`（受信: デフォルト 5555）、`send_port`（送信: デフォルト 5556）、`response_timeout_sec`、`retry_count` を変更できます。
- **[TRADING]**: 売買結果・損益集計の出力先ディレクトリや、結果ファイルを日単位で分けるかなどの設定があります。
- **環境変数**: 上記のとおり `server/.env` で JWT 等を設定します。

## 動作確認・テスト

### サーバーの動作確認

1. 上記「セットアップ・起動」の手順でサーバーを起動する。
2. ブラウザで `http://localhost:8000/docs` を開き、FastAPI の API 一覧が表示されれば OK です。

### テストの実行

```bash
cd server
uv run pytest
```

## ドキュメント・次のステップ

- [設計書](docs/設計書.md) — アーキテクチャ・レイヤー・データフロー
- [インターフェース設計書](docs/インターフェース設計書.md) — MT4–Python 間のデータ形式・ポート・DTO 対応

戦略を変えたい場合は `server/app_server/domain/strategy/`、ティックや CSV の処理は `application/process_service/` を参照してください。

## ライセンス

プロジェクト固有のライセンス表記が無い場合は、利用時は各依存ライブラリのライセンスに従ってください。
