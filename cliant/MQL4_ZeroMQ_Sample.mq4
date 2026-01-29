//+------------------------------------------------------------------+
//|                                          MQL4_ZeroMQ_Sample.mq4  |
//|              MT4-Python 自動売買システム クライアント（設計書準拠）   |
//|                                                                  |
//| 設計書: docs/設計書.md                                            |
//| 通信: ZeroMQ のみ。ポート5555=PUSH(MT4→Python)、5556=PULL(Python→MT4) |
//| メッセージ: ティック=CSV "SYMBOL,BID,ASK,SPREAD,TIME"             |
//|            注文/決済=JSON（設計書 3.2 節）                         |
//| 必要なライブラリ:                                                   |
//|   - mql-zmq (https://github.com/dingmaotu/mql-zmq)               |
//|   - libzmq.dll, libsodium.dll をMT4のLibrariesフォルダに配置       |
//+------------------------------------------------------------------+
#property copyright "MT4-Python Trading System"
#property link      ""
#property version   "1.10"
#property strict

#include <Zmq/Zmq.mqh>

//--- 入力パラメータ（設計書 3.1 / 11.2: setting.ini と同様にポート等を変更可能に）
input string   ServerAddress = "tcp://localhost";  // Pythonサーバーアドレス
input int      PushPort = 5555;                    // データ送信ポート（MT4 PUSH → Python PULL）
input int      PullPort = 5556;                    // コマンド受信ポート（Python PUSH → MT4 PULL）
input int      SendIntervalMs = 100;               // ティック送信間隔（ミリ秒）
input int      MagicNumber = 12345;               // 注文識別マジック番号
input bool     EnableReconnect = true;             // 切断時再接続を試行する
input int      ReconnectIntervalSec = 5;           // 再接続試行間隔（秒）

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
    pullSocket.setReceiveTimeout(1);  // 1ms タイムアウト（設計書 3.3）

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
//| ティック送信（設計書 3.2.1: CSV "SYMBOL,BID,ASK,SPREAD,TIME"）      |
//+------------------------------------------------------------------+
void SendTickData()
{
    string tickData = Symbol() + "," +
                      DoubleToString(Bid, Digits) + "," +
                      DoubleToString(Ask, Digits) + "," +
                      IntegerToString(MarketInfo(Symbol(), MODE_SPREAD)) + "," +
                      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);

    ZmqMsg message(tickData);
    if(!pushSocket.send(message, true))
    {
        Print("ティック送信失敗");
        if(EnableReconnect) isConnected = false;
    }
}

//+------------------------------------------------------------------+
//| コマンド受信（設計書 3.2.2〜3.2.4: ORDER / CLOSE 等 JSON）          |
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
    if(StringFind(jsonCommand, "\"action\": \"ORDER\"") >= 0)
        ProcessOrderCommand(jsonCommand);
    else if(StringFind(jsonCommand, "\"action\": \"CLOSE\"") >= 0)
        ProcessCloseCommand(jsonCommand);
    else if(StringFind(jsonCommand, "\"action\": \"SUBSCRIBE\"") >= 0)
        Print("購読リクエスト受信（必要に応じて実装）");
    else
        Print("不明なコマンド: ", jsonCommand);
}

//+------------------------------------------------------------------+
//| 注文コマンド（設計書 3.2.2: type=BUY/SELL, lots, sl/tp=0は未指定）   |
//+------------------------------------------------------------------+
void ProcessOrderCommand(string jsonCommand)
{
    string symbol = ExtractJsonString(jsonCommand, "symbol");
    string orderType = ExtractJsonString(jsonCommand, "type");
    double lots = ExtractJsonDouble(jsonCommand, "lots");
    double sl = ExtractJsonDouble(jsonCommand, "sl");
    double tp = ExtractJsonDouble(jsonCommand, "tp");

    if(symbol == "") symbol = Symbol();
    if(lots <= 0) lots = 0.01;

    int cmd = -1;
    double price = 0;

    if(orderType == "BUY")
    {
        cmd = OP_BUY;
        price = MarketInfo(symbol, MODE_ASK);
    }
    else if(orderType == "SELL")
    {
        cmd = OP_SELL;
        price = MarketInfo(symbol, MODE_BID);
    }

    if(cmd < 0) return;

    if(sl == 0) sl = 0;  // 設計書: 0の場合は未指定
    if(tp == 0) tp = 0;

    int ticket = OrderSend(symbol, cmd, lots, price, 3, sl, tp,
                          "ZeroMQ Order", MagicNumber, 0, clrGreen);

    if(ticket > 0)
    {
        Print("注文成功: チケット#", ticket, " ", symbol, " ", orderType, " ", lots, "ロット");
        SendOrderResult(ticket, "SUCCESS");
    }
    else
    {
        int err = GetLastError();
        Print("注文失敗: エラー ", err, " - ", ErrorDescription(err));
        SendOrderResult(-1, "FAILED:" + IntegerToString(err));
    }
}

//+------------------------------------------------------------------+
//| 決済コマンド（設計書 3.2.3: action=CLOSE, ticket）                  |
//+------------------------------------------------------------------+
void ProcessCloseCommand(string jsonCommand)
{
    int ticket = ExtractJsonInt(jsonCommand, "ticket");

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

    double closePrice = (OrderType() == OP_BUY)
        ? MarketInfo(OrderSymbol(), MODE_BID)
        : MarketInfo(OrderSymbol(), MODE_ASK);

    if(OrderClose(ticket, OrderLots(), closePrice, 3, clrRed))
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
//| 注文結果送信（設計書 3.2.4: type=order_result, ticket, status）      |
//+------------------------------------------------------------------+
void SendOrderResult(int ticket, string status)
{
    string result = "{\"type\":\"order_result\",\"ticket\":" + IntegerToString(ticket) +
                    ",\"status\":\"" + status + "\"}";
    ZmqMsg message(result);
    if(!pushSocket.send(message, true) && EnableReconnect)
        isConnected = false;
}

//+------------------------------------------------------------------+
//| JSON 文字列抽出                                                    |
//+------------------------------------------------------------------+
string ExtractJsonString(string json, string key)
{
    string searchKey = "\"" + key + "\": \"";
    int start = StringFind(json, searchKey);
    if(start < 0) return "";

    start += StringLen(searchKey);
    int end = StringFind(json, "\"", start);
    if(end < 0) return "";

    return StringSubstr(json, start, end - start);
}

//+------------------------------------------------------------------+
//| JSON 数値抽出（double）                                            |
//+------------------------------------------------------------------+
double ExtractJsonDouble(string json, string key)
{
    string searchKey = "\"" + key + "\": ";
    int start = StringFind(json, searchKey);
    if(start < 0) return 0;

    start += StringLen(searchKey);
    int end = start;
    while(end < StringLen(json))
    {
        ushort ch = StringGetCharacter(json, end);
        if(ch != '.' && ch != '-' && (ch < '0' || ch > '9'))
            break;
        end++;
    }

    return StringToDouble(StringSubstr(json, start, end - start));
}

//+------------------------------------------------------------------+
//| JSON 整数抽出（チケット番号用）                                     |
//+------------------------------------------------------------------+
int ExtractJsonInt(string json, string key)
{
    string searchKey = "\"" + key + "\": ";
    int start = StringFind(json, searchKey);
    if(start < 0) return 0;

    start += StringLen(searchKey);
    int end = start;
    while(end < StringLen(json))
    {
        ushort ch = StringGetCharacter(json, end);
        if(ch != '-' && (ch < '0' || ch > '9'))
            break;
        end++;
    }

    return StringToInteger(StringSubstr(json, start, end - start));
}

//+------------------------------------------------------------------+
//| エラー説明                                                         |
//+------------------------------------------------------------------+
string ErrorDescription(int error)
{
    switch(error)
    {
        case 0:   return "No error";
        case 1:   return "No error, trade conditions not changed";
        case 2:   return "Common error";
        case 3:   return "Invalid trade parameters";
        case 4:   return "Trade server is busy";
        case 5:   return "Old version of the client terminal";
        case 6:   return "No connection with trade server";
        case 7:   return "Not enough rights";
        case 8:   return "Too frequent requests";
        case 9:   return "Malfunctional trade operation";
        case 64:  return "Account disabled";
        case 65:  return "Invalid account";
        case 128: return "Trade timeout";
        case 129: return "Invalid price";
        case 130: return "Invalid stops";
        case 131: return "Invalid trade volume";
        case 132: return "Market is closed";
        case 133: return "Trade is disabled";
        case 134: return "Not enough money";
        case 135: return "Price changed";
        case 136: return "Off quotes";
        case 137: return "Broker is busy";
        case 138: return "Requote";
        case 139: return "Order is locked";
        case 140: return "Long positions only allowed";
        case 141: return "Too many requests";
        case 145: return "Modification denied because order too close to market";
        case 146: return "Trade context is busy";
        case 147: return "Expirations are denied by broker";
        case 148: return "Too many open and pending orders";
        default:  return "Unknown error";
    }
}
//+------------------------------------------------------------------+
