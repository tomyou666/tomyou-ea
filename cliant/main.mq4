//+------------------------------------------------------------------+
//|                                          main.mq4                |
//|         MT4-Python 自動売買システム クライアント（設計書準拠）   |
//|                                                                  |
//|  docs/設計書.md                                                  |
//| 通信: ZeroMQ のみ。ポート5555=PUSH(MT4→Python)、5556=PULL(Python→MT4) |
//| メッセージ: ティック=CSV "SYMBOL,BID,ASK,SPREAD,TIME"             |
//|            注文/決済=JSON                                        |
//| 必要なライブラリ:                                                |
//|   - mql-zmq (https://github.com/dingmaotu/mql-zmq)               |
//|   - JAson (https://github.com/vivazzi/JAson) JSONのシリアライズ  |
//|   - libzmq.dll, libsodium.dll をMT4のLibrariesフォルダに配置     |
//+------------------------------------------------------------------+
#property copyright "MT4-Python Trading System"
#property link      ""
#property version   "1.10"
#property strict

#include <Zmq/Zmq.mqh>
#include <JAson.mqh>

//--- 入力パラメータ（ setting.ini と同様にポート等を変更可能に）
input string ServerAddress = "tcp://localhost"; // Pythonサーバーアドレス
input int PushPort = 5555; // データ送信ポート（MT4 PUSH → Python PULL）
input int PullPort = 5556; // コマンド受信ポート（Python PUSH → MT4 PULL）
input int SendIntervalMs = 100; // ティック送信間隔（ミリ秒）
input int MagicNumber = 12345; // 注文識別マジック番号
input bool EnableReconnect = true; // 切断時再接続を試行する
input int ReconnectIntervalSec = 5; // 再接続試行間隔（秒）
input int OrderRetryCount = 3; // 注文リトライ回数（0 = リトライなし）
input int OrderRetryDelayMs = 500; // リトライ間隔（ミリ秒）

//--- ZeroMQ
Context context;
Socket pushSocket(context, ZMQ_PUSH);
Socket pullSocket(context, ZMQ_PULL);

//--- 状態
bool isConnected = false;
datetime lastSendTime = 0;
datetime lastReconnectTry = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit()
{
    if(!ConnectSockets())
    return INIT_FAILED;

    Comment("ZeroMQ接続済み\nPUSH: ", ServerAddress, ":", PushPort,
    "\nPULL: ", ServerAddress, ":", PullPort);

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| ソケット接続（初期化・再接続で共用）                                 |
//+------------------------------------------------------------------+
bool ConnectSockets()
{
    string pushAddress = ServerAddress + ":" + IntegerToString(PushPort);
    if(!pushSocket.connect(pushAddress))
    {
        Print("エラー: PUSHソケット接続失敗 - ", pushAddress);
        return false;
    }
    Print("PUSHソケット接続成功: ", pushAddress);

    string pullAddress = ServerAddress + ":" + IntegerToString(PullPort);
    pullSocket.setReceiveTimeout(1); // 1ms タイムアウト

    if(!pullSocket.connect(pullAddress))
    {
        Print("警告: PULLソケット接続失敗 - ", pullAddress);
    }
    else
    {
        Print("PULLソケット接続成功: ", pullAddress);
    }

    isConnected = true;
    return true;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    pushSocket.disconnect(ServerAddress + ":" + IntegerToString(PushPort));
    pullSocket.disconnect(ServerAddress + ":" + IntegerToString(PullPort));
    isConnected = false;
    Print("ZeroMQソケット切断完了");
    Comment("");
}

//+------------------------------------------------------------------+
//| Expert tick function                                              |
//+------------------------------------------------------------------+
void OnTick()
{
    if(!isConnected)
    {
        if(EnableReconnect && (TimeCurrent() - lastReconnectTry >= ReconnectIntervalSec))
        {
            lastReconnectTry = TimeCurrent();
            pushSocket.disconnect(ServerAddress + ":" + IntegerToString(PushPort));
            pullSocket.disconnect(ServerAddress + ":" + IntegerToString(PullPort));
            if(ConnectSockets())
            Print("再接続成功");
        }
        return;
    }

    if(GetTickCount() - lastSendTime >= SendIntervalMs)
    {
        SendTickData();
        lastSendTime = GetTickCount();
    }

    ReceiveCommands();
}

//+------------------------------------------------------------------+
//| ティック送信（ CSV "SYMBOL,BID,ASK,SPREAD,TIME"）      |
//+------------------------------------------------------------------+
void SendTickData()
{
    string tickData = Symbol() + ", " +
    DoubleToString(Bid, Digits) + ", " +
    DoubleToString(Ask, Digits) + ", " +
    IntegerToString(MarketInfo(Symbol(), MODE_SPREAD)) + ", " +
    TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);

    ZmqMsg message(tickData);
    if(!pushSocket.send(message, true))
    {
        Print("ティック送信失敗");
        if(EnableReconnect)
        isConnected = false;
    }
}

//+------------------------------------------------------------------+
//| コマンド受信（ ORDER / CLOSE 等 JSON）          |
//+------------------------------------------------------------------+
void ReceiveCommands()
{
    ZmqMsg message;
    if(!pullSocket.recv(message, true))
    return;

    string command = message.getData();
    Print("受信コマンド: ", command);
    ProcessCommand(command);
}

//+------------------------------------------------------------------+
//| コマンド振り分け（action: ORDER / CLOSE / SUBSCRIBE）               |
//+------------------------------------------------------------------+
void ProcessCommand(string jsonCommand)
{
    CJAVal cmd;
    if(!cmd.Deserialize(jsonCommand))
    {
        Print("JSONデシリアライズ失敗: ", jsonCommand);
        return;
    }

    string action = cmd["action"].ToStr();
    if(action == "ORDER")
    ProcessOrderCommand(cmd);
    else
    if(action == "CLOSE")
    ProcessCloseCommand(cmd);
    else
    if(action == "SUBSCRIBE")
    Print("購読リクエスト受信（必要に応じて実装）");
    else
    Print("不明なコマンド: ", jsonCommand);
}

//+------------------------------------------------------------------+
//| 注文コマンド（成行 BUY/SELL、指値 BUY_LIMIT/SELL_LIMIT、逆指値 BUY_STOP/SELL_STOP） |
//+------------------------------------------------------------------+
void ProcessOrderCommand(CJAVal &data)
{
    string symbol = data["symbol"].ToStr();
    string orderType = data["type"].ToStr();
    double lots = data["lots"].ToDbl();
    double sl = data["sl"].ToDbl();
    double tp = data["tp"].ToDbl();
    double priceFromCmd = data["price"].ToDbl();

    if(symbol == "")
    symbol = Symbol();
    if(lots <= 0)
    lots = 0.01;

    int cmd = - 1;
    double price = 0;
    bool isPending = false; // 指値・逆指値は発動価格固定のためリトライ時に価格を更新しない

    RefreshRates();
    if(orderType == "BUY")
    {
        cmd = OP_BUY;
        price = (symbol == Symbol()) ? Ask : MarketInfo(symbol, MODE_ASK);
    }
    else
    if(orderType == "SELL")
    {
        cmd = OP_SELL;
        price = (symbol == Symbol()) ? Bid : MarketInfo(symbol, MODE_BID);
    }
    else
    if(orderType == "BUY_LIMIT")
    {
        cmd = OP_BUYLIMIT;
        isPending = true;
        if(priceFromCmd <= 0)
        {
            Print("指値買い: price が未指定または 0");
            SendOrderResult( - 1, "FAILED:129"); // Invalid price
            return;
        }
        price = priceFromCmd;
    }
    else
    if(orderType == "SELL_LIMIT")
    {
        cmd = OP_SELLLIMIT;
        isPending = true;
        if(priceFromCmd <= 0)
        {
            Print("指値売り: price が未指定または 0");
            SendOrderResult( - 1, "FAILED:129");
            return;
        }
        price = priceFromCmd;
    }
    else
    if(orderType == "BUY_STOP")
    {
        cmd = OP_BUYSTOP;
        isPending = true;
        if(priceFromCmd <= 0)
        {
            Print("逆指値買い: price が未指定または 0");
            SendOrderResult( - 1, "FAILED:129");
            return;
        }
        price = priceFromCmd;
    }
    else
    if(orderType == "SELL_STOP")
    {
        cmd = OP_SELLSTOP;
        isPending = true;
        if(priceFromCmd <= 0)
        {
            Print("逆指値売り: price が未指定または 0");
            SendOrderResult( - 1, "FAILED:129");
            return;
        }
        price = priceFromCmd;
    }

    if(cmd < 0)
    {
        Print("不明な注文種別: ", orderType);
        SendOrderResult( - 1, "FAILED:INVALID_ORDER_TYPE");
        return;
    }

    if(sl == 0)
    sl = 0;
    if(tp == 0)
    tp = 0;

    int ticket = - 1;
    int attempt = 0;
    int maxAttempts = (OrderRetryCount > 0) ? (OrderRetryCount + 1) : 1;
    int slippage = isPending ? 0 : 5;

    while(attempt < maxAttempts)
    {
        if(attempt > 0)
        {
            Sleep(OrderRetryDelayMs);
            RefreshRates();
            if(!isPending)
            price = (symbol == Symbol())
            ? ((cmd == OP_BUY) ? Ask : Bid)
            : ((cmd == OP_BUY) ? MarketInfo(symbol, MODE_ASK) : MarketInfo(symbol, MODE_BID));
        }

        ticket = OrderSend(symbol, cmd, lots, price, slippage, sl, tp,
        "ZeroMQ Order", MagicNumber, 0, clrGreen);

        if(ticket > 0)
        break;

        int err = GetLastError();
        bool retryable = (err == 128 || err == 129 || err == 135 || err == 136 || err == 138 || err == 146);

        if(!retryable || attempt >= maxAttempts - 1)
        {
            Print("注文失敗: エラー ", err, " - ", ErrorDescription(err),
            (attempt > 0 ? " (リトライ " + IntegerToString(attempt) + "回後)" : ""));
            SendOrderResult( - 1, "FAILED:" + IntegerToString(err));
            return;
        }

        Print("注文リトライ: エラー ", err, " (", attempt + 1, " / ", maxAttempts - 1, ") - ", ErrorDescription(err));
        attempt++;
    }

    if(ticket > 0)
    {
        Print("注文成功: チケット#", ticket, " ", symbol, " ", orderType, " ", lots, "ロット",
        (attempt > 0 ? " (リトライ " + IntegerToString(attempt) + "回後)" : ""));
        SendOrderResult(ticket, "SUCCESS");
    }
}

//+------------------------------------------------------------------+
//| 決済コマンド（ action=CLOSE, ticket）。ポジションは OrderClose、未約定注文は OrderDelete |
//+------------------------------------------------------------------+
void ProcessCloseCommand(CJAVal &data)
{
    int ticket = (int)data["ticket"].ToInt();

    if(ticket <= 0)
    {
        SendOrderResult(0, "INVALID_TICKET");
        return;
    }

    if(!OrderSelect(ticket, SELECT_BY_TICKET))
    {
        Print("決済失敗: チケット#", ticket, " が見つかりません");
        SendOrderResult(ticket, "TICKET_NOT_FOUND");
        return;
    }

    int otype = OrderType();
    bool closed = false;

    if(otype == OP_BUY || otype == OP_SELL)
    {
        double closePrice = (otype == OP_BUY)
        ? MarketInfo(OrderSymbol(), MODE_BID)
        : MarketInfo(OrderSymbol(), MODE_ASK);
        closed = OrderClose(ticket, OrderLots(), closePrice, 3, clrRed);
    }
    else
    if(otype == OP_BUYLIMIT || otype == OP_SELLLIMIT || otype == OP_BUYSTOP || otype == OP_SELLSTOP)
    {
        closed = OrderDelete(ticket, clrRed);
    }

    if(closed)
    {
        Print("決済成功: チケット#", ticket);
        SendOrderResult(ticket, "CLOSED");
    }
    else
    {
        Print("決済失敗: チケット#", ticket);
        SendOrderResult(ticket, "CLOSE_FAILED");
    }
}

//+------------------------------------------------------------------+
//| 注文結果送信（ type=order_result, ticket, status）      |
//+------------------------------------------------------------------+
void SendOrderResult(int ticket, string status)
{
    CJAVal result;
    result["type"] = "order_result";
    result["ticket"] = ticket;
    result["status"] = status;
    string resultStr = result.Serialize();
    ZmqMsg message(resultStr);
    if(!pushSocket.send(message, true) && EnableReconnect)
    isConnected = false;
}

//+------------------------------------------------------------------+
//| エラー説明                                                         |
//+------------------------------------------------------------------+
string ErrorDescription(int error)
{
    switch(error)
    {
        case 0:
        return "No error";
        case 1:
        return "No error, trade conditions not changed";
        case 2:
        return "Common error";
        case 3:
        return "Invalid trade parameters";
        case 4:
        return "Trade server is busy";
        case 5:
        return "Old version of the client terminal";
        case 6:
        return "No connection with trade server";
        case 7:
        return "Not enough rights";
        case 8:
        return "Too frequent requests";
        case 9:
        return "Malfunctional trade operation";
        case 64:
        return "Account disabled";
        case 65:
        return "Invalid account";
        case 128:
        return "Trade timeout";
        case 129:
        return "Invalid price";
        case 130:
        return "Invalid stops";
        case 131:
        return "Invalid trade volume";
        case 132:
        return "Market is closed";
        case 133:
        return "Trade is disabled";
        case 134:
        return "Not enough money";
        case 135:
        return "Price changed";
        case 136:
        return "Off quotes";
        case 137:
        return "Broker is busy";
        case 138:
        return "Requote";
        case 139:
        return "Order is locked";
        case 140:
        return "Long positions only allowed";
        case 141:
        return "Too many requests";
        case 145:
        return "Modification denied because order too close to market";
        case 146:
        return "Trade context is busy";
        case 147:
        return "Expirations are denied by broker";
        case 148:
        return "Too many open and pending orders";
        default:
        return "Unknown error";
    }
}
//+------------------------------------------------------------------+
