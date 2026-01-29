# uv add fastapi uvicorn websockets pyzmq
# 実行: uv run fastapi dev main.py --port 8000
# 監視ページ: http://localhost:8000/monitor

"""
MQL4 + ZeroMQ + WebSocket サンプルプログラム

アーキテクチャ:
    MQL4 (MT4) <--ZeroMQ--> Python Server <--WebSocket--> Web Browser

機能:
    1. MQL4からZeroMQ経由で価格データを受信
    2. 受信したデータをWebSocket経由でブラウザにリアルタイム配信
    3. ブラウザからの注文をMQL4に送信
"""

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime

import zmq
import zmq.asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========== ZeroMQ設定 ==========
ZMQ_RECV_PORT = 5555  # MQL4からデータを受信するポート
ZMQ_SEND_PORT = 5556  # MQL4へコマンドを送信するポート


# ========== WebSocket接続管理 ==========
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket接続: 現在{len(self.active_connections)}クライアント")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket切断: 現在{len(self.active_connections)}クライアント")

    async def broadcast(self, message: str):
        """全クライアントにメッセージを送信"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)


manager = ConnectionManager()


# ========== ZeroMQ送信用ソケット（遅延初期化） ==========
zmq_context: zmq.Context | None = None
zmq_push_socket: zmq.Socket | None = None


def init_zmq_push_socket():
    """ZeroMQ PUSHソケットを初期化（lifespan内で呼び出す）"""
    global zmq_context, zmq_push_socket
    if zmq_push_socket is None:
        zmq_context = zmq.Context()
        zmq_push_socket = zmq_context.socket(zmq.PUSH)
        zmq_push_socket.bind(f"tcp://*:{ZMQ_SEND_PORT}")
        logger.info(f"ZeroMQ PUSH ソケット起動: ポート {ZMQ_SEND_PORT}")


def cleanup_zmq_push_socket():
    """ZeroMQ PUSHソケットをクリーンアップ"""
    global zmq_context, zmq_push_socket
    if zmq_push_socket is not None:
        zmq_push_socket.close()
        zmq_push_socket = None
    if zmq_context is not None:
        zmq_context.term()
        zmq_context = None


def send_to_mql4(command: str):
    """MQL4にコマンドを送信"""
    if zmq_push_socket is None:
        logger.error("ZeroMQソケット未初期化")
        return False
    try:
        zmq_push_socket.send_string(command, zmq.NOBLOCK)
        logger.info(f"MQL4へ送信: {command}")
        return True
    except zmq.ZMQError as e:
        logger.error(f"送信エラー: {e}")
        return False


# ========== ZeroMQ受信タスク ==========
async def zmq_receiver():
    """MQL4からZeroMQ経由でデータを受信し、WebSocketにブロードキャスト"""
    context = zmq.asyncio.Context()
    socket = context.socket(zmq.PULL)
    socket.bind(f"tcp://*:{ZMQ_RECV_PORT}")
    logger.info(f"ZeroMQ PULL ソケット起動: ポート {ZMQ_RECV_PORT}")

    try:
        while True:
            try:
                message = await socket.recv_string()
                logger.info(f"ZeroMQ受信: {message}")

                # WebSocketクライアントにブロードキャスト
                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                broadcast_data = json.dumps(
                    {"type": "tick", "data": message, "time": timestamp},
                    ensure_ascii=False,
                )
                await manager.broadcast(broadcast_data)

            except zmq.ZMQError as e:
                logger.error(f"ZeroMQエラー: {e}")
                await asyncio.sleep(1)
    finally:
        socket.close()
        context.term()


# ========== FastAPIアプリケーション ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーション起動時にZeroMQソケットを初期化"""
    # ZeroMQソケット初期化（ここで初めてbindする）
    init_zmq_push_socket()

    # 受信タスク開始
    task = asyncio.create_task(zmq_receiver())
    logger.info("ZeroMQ受信タスク開始")

    yield

    # クリーンアップ
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    cleanup_zmq_push_socket()
    logger.info("ZeroMQリソース解放完了")


app = FastAPI(lifespan=lifespan)


# ========== REST API ==========
class OrderRequest(BaseModel):
    symbol: str
    type: str  # "BUY" or "SELL"
    lots: float
    price: float = 0.0
    sl: float = 0.0
    tp: float = 0.0


@app.post("/order")
async def send_order(order: OrderRequest):
    """注文をMQL4に送信"""
    command = json.dumps(
        {
            "action": "ORDER",
            "symbol": order.symbol,
            "type": order.type,
            "lots": order.lots,
            "price": order.price,
            "sl": order.sl,
            "tp": order.tp,
        }
    )
    success = send_to_mql4(command)
    return {"status": "sent" if success else "failed", "command": command}


@app.get("/status")
async def get_status():
    """接続状態を取得"""
    return {
        "websocket_clients": len(manager.active_connections),
        "zmq_recv_port": ZMQ_RECV_PORT,
        "zmq_send_port": ZMQ_SEND_PORT,
    }


# ========== WebSocketエンドポイント ==========
@app.websocket("/ws/market")
async def websocket_market(websocket: WebSocket):
    """マーケットデータのWebSocket接続"""
    await manager.connect(websocket)
    try:
        # 接続確認メッセージ
        await websocket.send_text(json.dumps({"type": "connected", "message": "WebSocket接続完了"}))

        while True:
            # クライアントからのコマンドを受信
            data = await websocket.receive_text()
            logger.info(f"WebSocket受信: {data}")

            try:
                cmd = json.loads(data)
                if cmd.get("action") == "ORDER":
                    # 注文コマンドをMQL4に転送
                    success = send_to_mql4(data)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "order_response",
                                "status": "sent" if success else "failed",
                            }
                        )
                    )
                elif cmd.get("action") == "SUBSCRIBE":
                    # シンボル購読（MQL4に通知）
                    send_to_mql4(data)
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "subscribed",
                                "symbol": cmd.get("symbol"),
                            }
                        )
                    )
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "Invalid JSON"}))

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ========== 監視用HTMLページ ==========
@app.get("/monitor")
async def get_monitor_page():
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>MQL4 マーケットモニター</title>
        <style>
            * { box-sizing: border-box; }
            body { font-family: 'Segoe UI', Arial, sans-serif; margin: 0; padding: 20px; background: #1a1a2e; color: #eee; }
            h1 { color: #00d4ff; margin-bottom: 20px; }
            .container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; max-width: 1200px; margin: 0 auto; }
            .panel { background: #16213e; border-radius: 10px; padding: 20px; }
            .panel h2 { color: #00d4ff; margin-top: 0; font-size: 1.2em; border-bottom: 1px solid #0f3460; padding-bottom: 10px; }
            #tickData { height: 300px; overflow-y: auto; font-family: monospace; font-size: 14px; }
            .tick { padding: 5px 10px; border-bottom: 1px solid #0f3460; }
            .tick:hover { background: #0f3460; }
            .tick-time { color: #888; }
            .tick-bid { color: #00ff88; }
            .tick-ask { color: #ff6b6b; }
            .status { display: flex; align-items: center; gap: 10px; margin-bottom: 15px; }
            .status-dot { width: 12px; height: 12px; border-radius: 50%; }
            .status-dot.connected { background: #00ff88; box-shadow: 0 0 10px #00ff88; }
            .status-dot.disconnected { background: #ff6b6b; }
            .order-form { display: grid; gap: 10px; }
            .form-row { display: grid; grid-template-columns: 100px 1fr; align-items: center; gap: 10px; }
            input, select { background: #0f3460; border: 1px solid #00d4ff; color: #fff; padding: 8px 12px; border-radius: 5px; }
            input:focus, select:focus { outline: none; border-color: #00ff88; }
            .btn { padding: 10px 20px; border: none; border-radius: 5px; cursor: pointer; font-weight: bold; transition: all 0.3s; }
            .btn-buy { background: #00ff88; color: #000; }
            .btn-sell { background: #ff6b6b; color: #fff; }
            .btn:hover { transform: scale(1.05); }
            .btn-connect { background: #00d4ff; color: #000; }
            #log { height: 150px; overflow-y: auto; font-family: monospace; font-size: 12px; background: #0f3460; padding: 10px; border-radius: 5px; }
            .log-entry { padding: 2px 0; border-bottom: 1px solid #16213e; }
        </style>
    </head>
    <body>
        <h1>MQL4 マーケットモニター</h1>

        <div class="container">
            <div class="panel">
                <h2>リアルタイムティックデータ</h2>
                <div class="status">
                    <div id="statusDot" class="status-dot disconnected"></div>
                    <span id="statusText">未接続</span>
                    <button class="btn btn-connect" onclick="connect()">接続</button>
                </div>
                <div id="tickData"></div>
            </div>

            <div class="panel">
                <h2>注文パネル</h2>
                <div class="order-form">
                    <div class="form-row">
                        <label>シンボル:</label>
                        <input type="text" id="symbol" value="USDJPY" placeholder="USDJPY">
                    </div>
                    <div class="form-row">
                        <label>ロット:</label>
                        <input type="number" id="lots" value="0.01" step="0.01" min="0.01">
                    </div>
                    <div class="form-row">
                        <label>S/L:</label>
                        <input type="number" id="sl" value="0" step="0.001">
                    </div>
                    <div class="form-row">
                        <label>T/P:</label>
                        <input type="number" id="tp" value="0" step="0.001">
                    </div>
                    <div style="display: flex; gap: 10px; margin-top: 10px;">
                        <button class="btn btn-buy" onclick="sendOrder('BUY')">BUY</button>
                        <button class="btn btn-sell" onclick="sendOrder('SELL')">SELL</button>
                    </div>
                </div>

                <h2 style="margin-top: 20px;">ログ</h2>
                <div id="log"></div>
            </div>
        </div>

        <script>
            let ws = null;

            function connect() {
                if (ws && ws.readyState === WebSocket.OPEN) {
                    ws.close();
                    return;
                }

                ws = new WebSocket(`ws://${location.host}/ws/market`);

                ws.onopen = () => {
                    document.getElementById('statusDot').className = 'status-dot connected';
                    document.getElementById('statusText').textContent = '接続中';
                    addLog('WebSocket接続完了');

                    // シンボル購読
                    const symbol = document.getElementById('symbol').value;
                    ws.send(JSON.stringify({action: 'SUBSCRIBE', symbol: symbol}));
                };

                ws.onclose = () => {
                    document.getElementById('statusDot').className = 'status-dot disconnected';
                    document.getElementById('statusText').textContent = '切断';
                    addLog('WebSocket切断');
                };

                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);

                    if (data.type === 'tick') {
                        addTick(data);
                    } else if (data.type === 'order_response') {
                        addLog(`注文応答: ${data.status}`);
                    } else if (data.type === 'subscribed') {
                        addLog(`${data.symbol} 購読開始`);
                    } else if (data.type === 'connected') {
                        addLog(data.message);
                    }
                };

                ws.onerror = (error) => {
                    addLog('エラー発生');
                };
            }

            function addTick(data) {
                const container = document.getElementById('tickData');
                const div = document.createElement('div');
                div.className = 'tick';

                // データをパース（例: "USDJPY,150.123,150.125"）
                const parts = data.data.split(',');
                if (parts.length >= 3) {
                    div.innerHTML = `
                        <span class="tick-time">${data.time}</span>
                        <strong>${parts[0]}</strong>
                        Bid: <span class="tick-bid">${parts[1]}</span>
                        Ask: <span class="tick-ask">${parts[2]}</span>
                    `;
                } else {
                    div.innerHTML = `<span class="tick-time">${data.time}</span> ${data.data}`;
                }

                container.insertBefore(div, container.firstChild);

                // 最大100件保持
                while (container.children.length > 100) {
                    container.removeChild(container.lastChild);
                }
            }

            function sendOrder(type) {
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    addLog('エラー: WebSocket未接続');
                    return;
                }

                const order = {
                    action: 'ORDER',
                    symbol: document.getElementById('symbol').value,
                    type: type,
                    lots: parseFloat(document.getElementById('lots').value),
                    sl: parseFloat(document.getElementById('sl').value),
                    tp: parseFloat(document.getElementById('tp').value)
                };

                ws.send(JSON.stringify(order));
                addLog(`${type}注文送信: ${order.symbol} ${order.lots}ロット`);
            }

            function addLog(message) {
                const container = document.getElementById('log');
                const div = document.createElement('div');
                div.className = 'log-entry';
                const time = new Date().toLocaleTimeString();
                div.textContent = `[${time}] ${message}`;
                container.insertBefore(div, container.firstChild);

                while (container.children.length > 50) {
                    container.removeChild(container.lastChild);
                }
            }

            // ページ読み込み時に自動接続
            // connect();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)
