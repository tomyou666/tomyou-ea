//+------------------------------------------------------------------+
//|                                          MQL4_ZeroMQ_Sample.mq4  |
//|                                    MQL4 + ZeroMQ サンプルプログラム |
//|                                                                  |
//| 必要なライブラリ:                                                   |
//|   - mql-zmq (https://github.com/dingmaotu/mql-zmq)               |
//|   - libzmq.dll, libsodium.dll をMT4のLibrariesフォルダに配置       |
//+------------------------------------------------------------------+
#property copyright "Sample"
#property link      ""
#property version   "1.00"
#property strict

// ZeroMQライブラリをインクルード
#include <Zmq/Zmq.mqh>

// 設定
input string   ServerAddress = "tcp://localhost";  // Pythonサーバーアドレス
input int      PushPort = 5555;                    // データ送信ポート（Python PULL）
input int      PullPort = 5556;                    // コマンド受信ポート（Python PUSH）
input int      SendIntervalMs = 100;               // ティック送信間隔（ミリ秒）

// ZeroMQオブジェクト
Context context;
Socket pushSocket(context, ZMQ_PUSH);  // Pythonへデータを送信
Socket pullSocket(context, ZMQ_PULL);  // Pythonからコマンドを受信

// 状態管理
bool isConnected = false;
datetime lastSendTime = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                     |
//+------------------------------------------------------------------+
int OnInit()
{
    // PUSHソケット接続（Pythonサーバーへデータ送信用）
    string pushAddress = ServerAddress + ":" + IntegerToString(PushPort);
    if(!pushSocket.connect(pushAddress))
    {
        Print("エラー: PUSHソケット接続失敗 - ", pushAddress);
        return INIT_FAILED;
    }
    Print("PUSHソケット接続成功: ", pushAddress);

    // PULLソケット設定（Pythonサーバーからコマンド受信用）
    string pullAddress = ServerAddress + ":" + IntegerToString(PullPort);

    // 非ブロッキング受信設定
    pullSocket.setReceiveTimeout(1);  // 1ms タイムアウト

    // connectを使用（Pythonサーバー側がbindしている）
    if(!pullSocket.connect(pullAddress))
    {
        Print("警告: PULLソケット接続失敗 - ", pullAddress);
        // 接続失敗でも続行（コマンド受信なしで動作）
    }
    else
    {
        Print("PULLソケット接続成功: ", pullAddress);
    }

    isConnected = true;

    // チャートにステータス表示
    Comment("ZeroMQ接続済み\nPUSH: ", pushAddress, "\nPULL: ポート ", PullPort);

    return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                   |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
    // ソケットクローズ
    pushSocket.disconnect(ServerAddress + ":" + IntegerToString(PushPort));
    pullSocket.disconnect(ServerAddress + ":" + IntegerToString(PullPort));

    Print("ZeroMQソケット切断完了");
    Comment("");
}

//+------------------------------------------------------------------+
//| Expert tick function                                               |
//+------------------------------------------------------------------+
void OnTick()
{
    if(!isConnected) return;

    // ティックデータ送信（間隔制御）
    if(GetTickCount() - lastSendTime >= SendIntervalMs)
    {
        SendTickData();
        lastSendTime = GetTickCount();
    }

    // コマンド受信チェック
    ReceiveCommands();
}

//+------------------------------------------------------------------+
//| ティックデータをPythonサーバーに送信                                  |
//+------------------------------------------------------------------+
void SendTickData()
{
    // フォーマット: "SYMBOL,BID,ASK,SPREAD,TIME"
    string tickData = Symbol() + "," +
                      DoubleToString(Bid, Digits) + "," +
                      DoubleToString(Ask, Digits) + "," +
                      IntegerToString(MarketInfo(Symbol(), MODE_SPREAD)) + "," +
                      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS);

    // ZeroMQ経由で送信
    ZmqMsg message(tickData);
    if(pushSocket.send(message, true))  // 非ブロッキング送信
    {
        // 送信成功（デバッグ用、本番では無効化推奨）
        // Print("送信: ", tickData);
    }
}

//+------------------------------------------------------------------+
//| Pythonサーバーからのコマンドを受信・処理                              |
//+------------------------------------------------------------------+
void ReceiveCommands()
{
    ZmqMsg message;

    // 非ブロッキングで受信試行
    if(pullSocket.recv(message, true))
    {
        string command = message.getData();
        Print("コマンド受信: ", command);

        // JSONパース（簡易実装）
        ProcessCommand(command);
    }
}

//+------------------------------------------------------------------+
//| コマンド処理                                                        |
//+------------------------------------------------------------------+
void ProcessCommand(string jsonCommand)
{
    // 簡易JSONパース
    // 実際の運用ではJAsonライブラリの使用を推奨

    if(StringFind(jsonCommand, "\"action\":\"ORDER\"") >= 0)
    {
        ProcessOrderCommand(jsonCommand);
    }
    else if(StringFind(jsonCommand, "\"action\":\"SUBSCRIBE\"") >= 0)
    {
        Print("購読リクエスト受信");
        // 購読処理（必要に応じて実装）
    }
    else if(StringFind(jsonCommand, "\"action\":\"CLOSE\"") >= 0)
    {
        ProcessCloseCommand(jsonCommand);
    }
}

//+------------------------------------------------------------------+
//| 注文コマンド処理                                                    |
//+------------------------------------------------------------------+
void ProcessOrderCommand(string jsonCommand)
{
    // JSONから値を抽出（簡易実装）
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

    if(cmd >= 0)
    {
        int ticket = OrderSend(symbol, cmd, lots, price, 3, sl, tp, "ZeroMQ Order", 12345, 0, clrGreen);

        if(ticket > 0)
        {
            Print("注文成功: チケット#", ticket, " ", symbol, " ", orderType, " ", lots, "ロット");
            SendOrderResult(ticket, "SUCCESS");
        }
        else
        {
            int error = GetLastError();
            Print("注文失敗: エラー ", error, " - ", ErrorDescription(error));
            SendOrderResult(-1, "FAILED:" + IntegerToString(error));
        }
    }
}

//+------------------------------------------------------------------+
//| 決済コマンド処理                                                    |
//+------------------------------------------------------------------+
void ProcessCloseCommand(string jsonCommand)
{
    int ticket = (int)ExtractJsonDouble(jsonCommand, "ticket");

    if(ticket > 0 && OrderSelect(ticket, SELECT_BY_TICKET))
    {
        double closePrice = 0;
        if(OrderType() == OP_BUY)
            closePrice = MarketInfo(OrderSymbol(), MODE_BID);
        else
            closePrice = MarketInfo(OrderSymbol(), MODE_ASK);

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
}

//+------------------------------------------------------------------+
//| 注文結果をPythonに送信                                              |
//+------------------------------------------------------------------+
void SendOrderResult(int ticket, string status)
{
    string result = "{\"type\":\"order_result\",\"ticket\":" + IntegerToString(ticket) +
                    ",\"status\":\"" + status + "\"}";

    ZmqMsg message(result);
    pushSocket.send(message, true);
}

//+------------------------------------------------------------------+
//| JSON文字列値抽出（簡易実装）                                         |
//+------------------------------------------------------------------+
string ExtractJsonString(string json, string key)
{
    string searchKey = "\"" + key + "\":\"";
    int start = StringFind(json, searchKey);
    if(start < 0) return "";

    start += StringLen(searchKey);
    int end = StringFind(json, "\"", start);
    if(end < 0) return "";

    return StringSubstr(json, start, end - start);
}

//+------------------------------------------------------------------+
//| JSON数値抽出（簡易実装）                                            |
//+------------------------------------------------------------------+
double ExtractJsonDouble(string json, string key)
{
    string searchKey = "\"" + key + "\":";
    int start = StringFind(json, searchKey);
    if(start < 0) return 0;

    start += StringLen(searchKey);

    // 数値の終端を探す
    int end = start;
    while(end < StringLen(json))
    {
        ushort ch = StringGetCharacter(json, end);
        if(ch != '.' && ch != '-' && (ch < '0' || ch > '9'))
            break;
        end++;
    }

    string value = StringSubstr(json, start, end - start);
    return StringToDouble(value);
}

//+------------------------------------------------------------------+
//| エラー説明取得                                                      |
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
