//+------------------------------------------------------------------+
//| SYNCHRO Bridge EA - File-Based Polling                          |
//| External bridge architecture: EA <-> Files <-> Python Bridge     |
//+------------------------------------------------------------------+
#property copyright "SYNCHRO Trading System"
#property link      "https://synchro.trade"
#property version   "1.0.0"
#property strict

#include <Trade\Trade.mqh>
#include <Files\Files.mqh>

//--- Input parameters
input group "=== SYNCHRO Bridge Settings ==="
input string   BridgeRoot       = "C:\\SynchroBridge";  // Bridge directory
input int      MagicNumber      = 123456;               // Magic number for orders
input double   DefaultVolume    = 0.10;                 // Default lot size
input int      DefaultSLPips    = 200;                  // Default SL in pips
input int      DefaultTPIps     = 300;                  // Default TP in pips
input int      BreakevenPips    = 100;                  // Breakeven trigger (pips)
input int      TrailingPips     = 50;                   // Trailing stop (pips)
input double   PartialCloseRatio = 0.5;                 // Partial close ratio
input int      PollIntervalMs   = 500;                  // File polling interval
input int      CloudTimeoutMs   = 60000;                // Cloud heartbeat timeout
input bool     EnableProtective = true;                 // Enable protective mode

//--- Global variables
CTrade trade;
string g_commands_dir;
string g_responses_dir;
string g_heartbeat_dir;
string g_state_dir;
string g_config_dir;

datetime g_last_cloud_heartbeat = 0;
datetime g_last_bridge_heartbeat = 0;
bool g_protective_mode = false;
bool g_cloud_connected = false;
string g_last_command_id = "";
long g_nonce_count = 0;

//--- Position tracking
struct PositionInfo {
   ulong ticket;
   string symbol;
   ENUM_ORDER_TYPE type;
   double volume;
   double open_price;
   double sl;
   double tp;
   bool breakeven_triggered;
   bool trailing_active;
   bool partial_closed;
};

PositionInfo g_positions[];
int g_position_count = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit() {
   // Set directories
   g_commands_dir = BridgeRoot + "\\commands\\";
   g_responses_dir = BridgeRoot + "\\responses\\";
   g_heartbeat_dir = BridgeRoot + "\\heartbeat\\";
   g_state_dir = BridgeRoot + "\\state\\";
   g_config_dir = BridgeRoot + "\\config\\";
   
   // Create directories if they don't exist
   CreateDirectories();
   
   // Initialize trade object
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetDeviationInPoints(10);
   trade.SetAsyncMode(true);
   
   // Set timer for polling (500ms = 2Hz)
   EventSetMillisecondTimer(PollIntervalMs);
   
   // Load bridge config
   LoadBridgeConfig();
   
   // Initialize position tracking
   RefreshPositions();
   
   // Write initial heartbeat
   WriteEAHeartbeat();
   
   Print("SYNCHRO Bridge EA initialized. Bridge root: ", BridgeRoot);
   Print("Magic: ", MagicNumber, " | Poll: ", PollIntervalMs, "ms");
   
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   EventKillTimer();
   Print("SYNCHRO Bridge EA deinitialized. Reason: ", reason);
}

//+------------------------------------------------------------------+
//| Timer function - main polling loop                               |
//+------------------------------------------------------------------+
void OnTimer() {
   // 1. Check cloud heartbeat timeout
   if (g_last_bridge_heartbeat > 0) {
      long elapsed = GetTickCount64() - g_last_bridge_heartbeat;
      if (elapsed > CloudTimeoutMs && EnableProtective) {
         if (!g_protective_mode) {
            EnterProtectiveMode();
         }
      } else if (g_protective_mode && elapsed <= CloudTimeoutMs) {
         // Cloud reconnected
         ExitProtectiveMode();
      }
   }
   
   // 2. Check bridge heartbeat
   CheckBridgeHeartbeat();
   
   // 3. Poll for new commands
   ProcessPendingCommands();
   
   // 4. Manage positions (breakeven, trailing)
   ManagePositions();
   
   // 5. Write EA heartbeat
   WriteEAHeartbeat();
   
   // 6. Update position tracking
   RefreshPositions();
}

//+------------------------------------------------------------------+
//| Create required directories                                       |
//+------------------------------------------------------------------+
void CreateDirectories() {
   string dirs[] = {
      g_commands_dir + "pending\\",
      g_commands_dir + "processing\\",
      g_commands_dir + "completed\\",
      g_responses_dir + "pending\\",
      g_responses_dir + "processing\\",
      g_responses_dir + "completed\\",
      g_heartbeat_dir,
      g_state_dir,
      g_config_dir
   };
   
   for (int i = 0; i < ArraySize(dirs); i++) {
      if (!FileIsExist(dirs[i], FILE_DIRECTORY)) {
         if (DirectoryCreate(dirs[i])) {
            Print("Created directory: ", dirs[i]);
         } else {
            Print("Warning: Could not create directory: ", dirs[i], " Error: ", GetLastError());
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Load bridge configuration                                         |
//+------------------------------------------------------------------+
void LoadBridgeConfig() {
   string config_file = g_config_dir + "bridge_config.json";
   if (FileIsExist(config_file)) {
      int handle = FileOpen(config_file, FILE_READ | FILE_BIN | FILE_ANSI);
      if (handle != INVALID_HANDLE) {
         string json = FileReadString(handle, FileSize(handle));
         FileClose(handle);
         Print("Loaded bridge config: ", json);
         // Parse JSON config here if needed
      }
   } else {
      Print("No bridge config found, using defaults");
   }
}

//+------------------------------------------------------------------+
//| Check bridge heartbeat                                            |
//+------------------------------------------------------------------+
void CheckBridgeHeartbeat() {
   string heartbeat_file = g_heartbeat_dir + "bridge_heartbeat.json";
   if (FileIsExist(heartbeat_file)) {
      int handle = FileOpen(heartbeat_file, FILE_READ | FILE_BIN | FILE_ANSI);
      if (handle != INVALID_HANDLE) {
         string json = FileReadString(handle, FileSize(handle));
         FileClose(handle);
         
         // Simple JSON parsing for timestamp
         // In production, use a proper JSON parser
         g_last_bridge_heartbeat = GetTickCount64();
         g_cloud_connected = true;
      }
   } else {
      g_cloud_connected = false;
   }
}

//+------------------------------------------------------------------+
//| Write EA heartbeat                                                |
//+------------------------------------------------------------------+
void WriteEAHeartbeat() {
   string heartbeat_file = g_heartbeat_dir + "ea_heartbeat.json";
   int handle = FileOpen(heartbeat_file, FILE_WRITE | FILE_BIN | FILE_ANSI | FILE_TXT);
   if (handle != INVALID_HANDLE) {
      double balance = AccountInfoDouble(ACCOUNT_BALANCE);
      double equity = AccountInfoDouble(ACCOUNT_EQUITY);
      double margin_free = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
      
      string json = "{";
      json += "\"ea_version\":\"1.0.0\",";
      json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES | TIME_SECONDS) + "\",";
      json += "\"account\":" + (string)AccountInfoInteger(ACCOUNT_LOGIN) + ",";
      json += "\"balance\":" + DoubleToString(balance, 2) + ",";
      json += "\"equity\":" + DoubleToString(equity, 2) + ",";
      json += "\"margin_free\":" + DoubleToString(margin_free, 2) + ",";
      json += "\"open_positions\":" + (string)g_position_count + ",";
      json += "\"cloud_connected\":" + (g_cloud_connected ? "true" : "false") + ",";
      json += "\"last_command_processed\":\"" + g_last_command_id + "\",";
      json += "\"protective_mode\":" + (g_protective_mode ? "true" : "false");
      json += "}";
      
      FileWriteString(handle, json, StringLen(json));
      FileClose(handle);
   }
}

//+------------------------------------------------------------------+
//| Process pending commands from bridge                              |
//+------------------------------------------------------------------+
void ProcessPendingCommands() {
   string pending_dir = g_commands_dir + "pending\\";
   
   int handle = FileFindFirst(pending_dir + "*.json", 0);
   if (handle == INVALID_HANDLE) {
      return; // No files
   }
   
   do {
      string filename = FileFindNext(handle);
      if (filename == "") continue;
      
      string filepath = pending_dir + filename;
      ProcessCommandFile(filepath);
      
   } while (FileFindNext(handle));
   FileFindClose(handle);
}

//+------------------------------------------------------------------+
//| Process a single command file                                     |
//+------------------------------------------------------------------+
void ProcessCommandFile(string filepath) {
   int handle = FileOpen(filepath, FILE_READ | FILE_BIN | FILE_ANSI);
   if (handle == INVALID_HANDLE) return;
   
   string json = FileReadString(handle, FileSize(handle));
   FileClose(handle);
   
   // Parse command (simplified - in production use JSON parser)
   // For now, extract command type and payload manually
   string cmd_type = ExtractJSONValue(json, "type");
   string command_id = ExtractJSONValue(json, "command_id");
   string payload_json = ExtractJSONObject(json, "payload");
   
   g_last_command_id = command_id;
   
   // Move to processing
   string filename = FileNameFromPath(filepath);
   string processing_path = g_commands_dir + "processing\\" + filename;
   if (!FileMove(filepath, processing_path)) {
      Print("Failed to move to processing: ", GetLastError());
      return;
   }
   
   // Execute command
   ResponseResult result = ExecuteCommand(cmd_type, payload_json);
   
   // Write response
   WriteResponse(command_id, result);
   
   // Move to completed
   string completed_path = g_commands_dir + "completed\\" + filename;
   FileMove(processing_path, completed_path);
}

//+------------------------------------------------------------------+
//| Execute a command                                                 |
//+------------------------------------------------------------------+
ResponseResult ExecuteCommand(string cmd_type, string payload) {
   ResponseResult result;
   result.success = false;
   result.error_code = 0;
   result.error_message = "";
   result.ticket = 0;
   result.price = 0;
   result.volume = 0;
   
   if (g_protective_mode && cmd_type != "CLOSE" && cmd_type != "PARTIAL_CLOSE" && cmd_type != "HEARTBEAT") {
      result.success = false;
      result.error_code = 10004;
      result.error_message = "Protective mode active";
      return result;
   }
   
   if (cmd_type == "OPEN") {
      return ExecuteOpen(payload);
   } else if (cmd_type == "CLOSE") {
      return ExecuteClose(payload);
   } else if (cmd_type == "PARTIAL_CLOSE") {
      return ExecutePartialClose(payload);
   } else if (cmd_type == "MODIFY") {
      return ExecuteModify(payload);
   } else if (cmd_type == "BREAKEVEN") {
      return ExecuteBreakeven(payload);
   } else if (cmd_type == "TRAILING") {
      return ExecuteTrailing(payload);
   } else if (cmd_type == "HEARTBEAT") {
      result.success = true;
      result.error_code = 0;
      return result;
   } else if (cmd_type == "SHUTDOWN") {
      EnterProtectiveMode();
      result.success = true;
      return result;
   }
   
   result.success = false;
   result.error_code = 10000;
   result.error_message = "Unknown command type: " + cmd_type;
   return result;
}

//+------------------------------------------------------------------+
//| Execute OPEN command                                              |
//+------------------------------------------------------------------+
ResponseResult ExecuteOpen(string payload) {
   ResponseResult result;
   result.success = false;
   
   // Extract payload values (simplified parsing)
   string symbol = ExtractJSONValue(payload, "symbol");
   string direction = ExtractJSONValue(payload, "direction");
   double volume = StringToDouble(ExtractJSONValue(payload, "volume"));
   double sl = StringToDouble(ExtractJSONValue(payload, "sl"));
   double tp = StringToDouble(ExtractJSONValue(payload, "tp"));
   string comment = ExtractJSONValue(payload, "comment");
   int magic = (int)StringToDouble(ExtractJSONValue(payload, "magic"));
   
   // Validate symbol
   if (!IsSymbolAllowed(symbol)) {
      result.error_code = 10005;
      result.error_message = "Symbol not allowed: " + symbol;
      return result;
   }
   
   // Check position limits
   if (g_position_count >= 5) { // max_positions from config
      result.error_code = 10006;
      result.error_message = "Max positions reached";
      return result;
   }
   
   // Calculate SL/TP if not provided
   double price = (direction == "BUY") ? SymbolInfoDouble(symbol, SYMBOL_ASK) : SymbolInfoDouble(symbol, SYMBOL_BID);
   if (sl == 0) {
      sl = direction == "BUY" ? price - DefaultSLPips * _Point * 10 : price + DefaultSLPips * _Point * 10;
   }
   if (tp == 0) {
      tp = direction == "BUY" ? price + DefaultTPIps * _Point * 10 : price - DefaultTPIps * _Point * 10;
   }
   
   // Send order
   ENUM_ORDER_TYPE order_type = (direction == "BUY") ? ORDER_TYPE_BUY : ORDER_TYPE_SELL;
   if (trade.Open(order_type, symbol, volume, price, sl, tp, comment, magic)) {
      result.success = true;
      result.ticket = trade.ResultOrder();
      result.price = trade.ResultPrice();
      result.volume = volume;
      Print("Order opened: ", result.ticket, " ", symbol, " ", direction, " ", DoubleToString(volume, 2));
      RefreshPositions();
   } else {
      result.error_code = (int)trade.ResultRetcode();
      result.error_message = "Order failed: " + (string)trade.ResultRetcode();
   }
   
   return result;
}

//+------------------------------------------------------------------+
//| Execute CLOSE command                                             |
//+------------------------------------------------------------------+
ResponseResult ExecuteClose(string payload) {
   ResponseResult result;
   result.success = false;
   
   ulong ticket = (ulong)StringToDouble(ExtractJSONValue(payload, "ticket"));
   double volume = StringToDouble(ExtractJSONValue(payload, "volume"));
   
   if (volume <= 0) volume = PositionGetVolumeByTicket(ticket);
   
   if (trade.PositionClose(ticket, volume)) {
      result.success = true;
      result.ticket = ticket;
      result.volume = volume;
      Print("Position closed: ", ticket);
      RefreshPositions();
   } else {
      result.error_code = (int)trade.ResultRetcode();
      result.error_message = "Close failed: " + (string)trade.ResultRetcode();
   }
   
   return result;
}

//+------------------------------------------------------------------+
//| Execute PARTIAL_CLOSE command                                     |
//+------------------------------------------------------------------+
ResponseResult ExecutePartialClose(string payload) {
   ResponseResult result;
   result.success = false;
   
   ulong ticket = (ulong)StringToDouble(ExtractJSONValue(payload, "ticket"));
   double volume = StringToDouble(ExtractJSONValue(payload, "volume"));
   
   if (volume <= 0) {
      double pos_volume = PositionGetVolumeByTicket(ticket);
      volume = pos_volume * PartialCloseRatio;
   }
   
   if (trade.PositionClose(ticket, volume)) {
      result.success = true;
      result.ticket = ticket;
      result.volume = volume;
      Print("Partial close: ", ticket, " volume: ", volume);
      RefreshPositions();
   } else {
      result.error_code = (int)trade.ResultRetcode();
      result.error_message = "Partial close failed";
   }
   
   return result;
}

//+------------------------------------------------------------------+
//| Execute MODIFY command                                            |
//+------------------------------------------------------------------+
ResponseResult ExecuteModify(string payload) {
   ResponseResult result;
   result.success = false;
   
   ulong ticket = (ulong)StringToDouble(ExtractJSONValue(payload, "ticket"));
   double sl_new = StringToDouble(ExtractJSONValue(payload, "sl_new"));
   double tp_new = StringToDouble(ExtractJSONValue(payload, "tp_new"));
   
   if (trade.PositionModify(ticket, sl_new, tp_new)) {
      result.success = true;
      result.ticket = ticket;
      Print("Position modified: ", ticket, " SL: ", sl_new, " TP: ", tp_new);
   } else {
      result.error_code = (int)trade.ResultRetcode();
      result.error_message = "Modify failed";
   }
   
   return result;
}

//+------------------------------------------------------------------+
//| Execute BREAKEVEN command                                         |
//+------------------------------------------------------------------+
ResponseResult ExecuteBreakeven(string payload) {
   ResponseResult result;
   result.success = false;
   
   ulong ticket = (ulong)StringToDouble(ExtractJSONValue(payload, "ticket"));
   
   if (!SelectPosition(ticket)) {
      result.error_code = 10007;
      result.error_message = "Position not found";
      return result;
   }
   
   double open_price = PositionGetDouble(POSITION_PRICE_OPEN);
   ENUM_POSITION_TYPE pos_type = (ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE);
   double sl = (pos_type == POSITION_TYPE_BUY) ? 
               open_price + BreakevenPips * _Point * 10 : 
               open_price - BreakevenPips * _Point * 10;
   double tp = PositionGetDouble(POSITION_TAKEPROFIT);
   
   if (trade.PositionModify(ticket, sl, tp)) {
      result.success = true;
      result.ticket = ticket;
      Print("Breakeven set: ", ticket, " SL: ", sl);
      // Mark in position tracking
      UpdatePositionBreakeven(ticket, true);
   } else {
      result.error_code = (int)trade.ResultRetcode();
      result.error_message = "Breakeven failed";
   }
   
   return result;
}

//+------------------------------------------------------------------+
//| Execute TRAILING command                                          |
//+------------------------------------------------------------------+
ResponseResult ExecuteTrailing(string payload) {
   ResponseResult result;
   result.success = false;
   
   ulong ticket = (ulong)StringToDouble(ExtractJSONValue(payload, "ticket"));
   
   if (!SelectPosition(ticket)) {
      result.error_code = 10007;
      result.error_message = "Position not found";
      return result;
   }
   
   // Mark for trailing - actual trailing happens in ManagePositions()
   UpdatePositionTrailing(ticket, true);
   result.success = true;
   result.ticket = ticket;
   Print("Trailing activated: ", ticket);
   
   return result;
}

//+------------------------------------------------------------------+
//| Manage positions (breakeven, trailing)                            |
//+------------------------------------------------------------------+
void ManagePositions() {
   for (int i = 0; i < g_position_count; i++) {
      PositionInfo pos = g_positions[i];
      
      if (!SelectPosition(pos.ticket)) continue;
      
      double current_price = (pos.type == ORDER_TYPE_BUY) ? 
                             SymbolInfoDouble(pos.symbol, SYMBOL_BID) : 
                             SymbolInfoDouble(pos.symbol, SYMBOL_ASK);
      double open_price = pos.open_price;
      double profit_pips = (pos.type == ORDER_TYPE_BUY) ? 
                           (current_price - open_price) / (_Point * 10) : 
                           (open_price - current_price) / (_Point * 10);
      
      // Breakeven logic
      if (!pos.breakeven_triggered && profit_pips >= BreakevenPips) {
         double new_sl = (pos.type == ORDER_TYPE_BUY) ? 
                         open_price + 10 * _Point * 10 : 
                         open_price - 10 * _Point * 10;
         double tp = PositionGetDouble(POSITION_TAKEPROFIT);
         if (trade.PositionModify(pos.ticket, new_sl, tp)) {
            Print("Auto-breakeven: ", pos.ticket, " SL: ", new_sl);
            g_positions[i].breakeven_triggered = true;
            g_positions[i].sl = new_sl;
         }
      }
      
      // Trailing logic
      if (pos.trailing_active && profit_pips > TrailingPips) {
         double new_sl = (pos.type == ORDER_TYPE_BUY) ? 
                         current_price - TrailingPips * _Point * 10 : 
                         current_price + TrailingPips * _Point * 10;
         // Only move SL in profitable direction
         if ((pos.type == ORDER_TYPE_BUY && new_sl > pos.sl) || 
             (pos.type == ORDER_TYPE_SELL && new_sl < pos.sl)) {
            double tp = PositionGetDouble(POSITION_TAKEPROFIT);
            if (trade.PositionModify(pos.ticket, new_sl, tp)) {
               Print("Trailing update: ", pos.ticket, " SL: ", new_sl);
               g_positions[i].sl = new_sl;
            }
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Write response file                                               |
//+------------------------------------------------------------------+
void WriteResponse(string command_id, ResponseResult result) {
   string response_file = g_responses_dir + "pending\\" + command_id + ".json";
   int handle = FileOpen(response_file, FILE_WRITE | FILE_BIN | FILE_ANSI | FILE_TXT);
   if (handle != INVALID_HANDLE) {
      string json = "{";
      json += "\"command_id\":\"" + command_id + "\",";
      json += "\"status\":\"" + (result.success ? "SUCCESS" : "ERROR") + "\",";
      json += "\"timestamp\":\"" + TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES | TIME_SECONDS) + "\",";
      json += "\"result\":{";
      json += "\"ticket\":" + (string)result.ticket + ",";
      json += "\"price\":" + DoubleToString(result.price, 5) + ",";
      json += "\"volume\":" + DoubleToString(result.volume, 2) + ",";
      json += "\"sl\":" + DoubleToString(0, 5) + ",";
      json += "\"tp\":" + DoubleToString(0, 5) + ",";
      json += "\"profit\":" + DoubleToString(0, 2) + ",";
      json += "\"swap\":0.0,";
      json += "\"comment\":\"SYNCHRO_5_5\"";
      json += "},";
      json += "\"error_code\":" + (string)result.error_code + ",";
      json += "\"error_message\":\"" + result.error_message + "\",";
      json += "\"hmac\":\"\",";
      json += "\"nonce\":\"" + GenerateNonce() + "\"";
      json += "}";
      
      FileWriteString(handle, json, StringLen(json));
      FileClose(handle);
   }
}

//+------------------------------------------------------------------+
//| Enter protective mode                                             |
//+------------------------------------------------------------------+
void EnterProtectiveMode() {
   g_protective_mode = true;
   Print("!!! PROTECTIVE MODE ACTIVATED - Closing all positions !!!");
   
   // Close all positions
   for (int i = 0; i < g_position_count; i++) {
      trade.PositionClose(g_positions[i].ticket);
   }
   
   // Write protective mode flag
   string flag_file = g_state_dir + "protective_mode.flag";
   int handle = FileOpen(flag_file, FILE_WRITE | FILE_TXT);
   if (handle != INVALID_HANDLE) {
      FileWriteString(handle, "1", 1);
      FileClose(handle);
   }
   
   RefreshPositions();
}

//+------------------------------------------------------------------+
//| Exit protective mode                                              |
//+------------------------------------------------------------------+
void ExitProtectiveMode() {
   g_protective_mode = false;
   Print("Protective mode deactivated - Cloud reconnected");
   
   // Remove flag
   string flag_file = g_state_dir + "protective_mode.flag";
   if (FileIsExist(flag_file)) {
      FileDelete(flag_file);
   }
}

//+------------------------------------------------------------------+
//| Refresh position tracking                                         |
//+------------------------------------------------------------------+
void RefreshPositions() {
   g_position_count = 0;
   ArrayResize(g_positions, 0);
   
   for (int i = 0; i < PositionsTotal(); i++) {
      ulong ticket = PositionGetTicket(i);
      if (PositionGetInteger(POSITION_MAGIC) == MagicNumber) {
         PositionInfo pos;
         pos.ticket = ticket;
         pos.symbol = PositionGetString(POSITION_SYMBOL);
         pos.type = (ENUM_ORDER_TYPE)PositionGetInteger(POSITION_TYPE);
         pos.volume = PositionGetDouble(POSITION_VOLUME);
         pos.open_price = PositionGetDouble(POSITION_PRICE_OPEN);
         pos.sl = PositionGetDouble(POSITION_SL);
         pos.tp = PositionGetDouble(POSITION_TAKEPROFIT);
         pos.breakeven_triggered = false; // Would need persistent storage
         pos.trailing_active = false;
         pos.partial_closed = false;
         
         ArrayResize(g_positions, g_position_count + 1);
         g_positions[g_position_count] = pos;
         g_position_count++;
      }
   }
}

//+------------------------------------------------------------------+
//| Helper: Select position by ticket                                 |
//+------------------------------------------------------------------+
bool SelectPosition(ulong ticket) {
   return PositionSelectByTicket(ticket);
}

//+------------------------------------------------------------------+
//| Helper: Get position volume by ticket                             |
//+------------------------------------------------------------------+
double PositionGetVolumeByTicket(ulong ticket) {
   if (PositionSelectByTicket(ticket)) {
      return PositionGetDouble(POSITION_VOLUME);
   }
   return 0;
}

//+------------------------------------------------------------------+
//| Helper: Update position breakeven flag                            |
//+------------------------------------------------------------------+
void UpdatePositionBreakeven(ulong ticket, bool triggered) {
   for (int i = 0; i < g_position_count; i++) {
      if (g_positions[i].ticket == ticket) {
         g_positions[i].breakeven_triggered = triggered;
         break;
      }
   }
}

//+------------------------------------------------------------------+
//| Helper: Update position trailing flag                             |
//+------------------------------------------------------------------+
void UpdatePositionTrailing(ulong ticket, bool active) {
   for (int i = 0; i < g_position_count; i++) {
      if (g_positions[i].ticket == ticket) {
         g_positions[i].trailing_active = active;
         break;
      }
   }
}

//+------------------------------------------------------------------+
//| Helper: Check if symbol is allowed                                |
//+------------------------------------------------------------------+
bool IsSymbolAllowed(string symbol) {
   // In production, load from config
   string allowed[] = {"R_75", "R_100", "R_50", "R_25", "R_10", 
                       "frxEURUSD", "frxGBPUSD", "frxUSDJPY", "frxAUDUSD", "frxUSDCAD"};
   for (int i = 0; i < ArraySize(allowed); i++) {
      if (symbol == allowed[i]) return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Helper: Extract JSON value (simplified)                           |
//+------------------------------------------------------------------+
string ExtractJSONValue(string json, string key) {
   string search = "\"" + key + "\":";
   int start = StringFind(json, search);
   if (start == -1) return "";
   start += StringLen(search);
   
   // Skip whitespace
   while (start < StringLen(json) && (json[start] == ' ' || json[start] == '\t' || json[start] == '\n')) start++;
   
   if (start >= StringLen(json)) return "";
   
   bool is_string = json[start] == '"';
   int end = start;
   if (is_string) {
      end++; // Skip opening quote
      while (end < StringLen(json) && json[end] != '"') end++;
      end++; // Include closing quote
   } else {
      while (end < StringLen(json) && json[end] != ',' && json[end] != '}' && json[end] != ']') end++;
   }
   
   return StringSubstr(json, start, end - start);
}

//+------------------------------------------------------------------+
//| Helper: Extract JSON object                                       |
//+------------------------------------------------------------------+
string ExtractJSONObject(string json, string key) {
   string search = "\"" + key + "\":";
   int start = StringFind(json, search);
   if (start == -1) return "";
   start += StringLen(search);
   
   // Skip whitespace
   while (start < StringLen(json) && (json[start] == ' ' || json[start] == '\t' || json[start] == '\n')) start++;
   
   if (start >= StringLen(json)) return "";
   
   if (json[start] == '{') {
      int brace_count = 1;
      int end = start + 1;
      while (end < StringLen(json) && brace_count > 0) {
         if (json[end] == '{') brace_count++;
         else if (json[end] == '}') brace_count--;
         end++;
      }
      return StringSubstr(json, start, end - start);
   }
   
   return "";
}

//+------------------------------------------------------------------+
//| Helper: Extract filename from path                                |
//+------------------------------------------------------------------+
string FileNameFromPath(string path) {
   int pos = StringFind(path, "\\", StringLen(path) - 1);
   if (pos == -1) pos = StringFind(path, "/", StringLen(path) - 1);
   if (pos == -1) return path;
   return StringSubstr(path, pos + 1);
}

//+------------------------------------------------------------------+
//| Generate nonce                                                    |
//+------------------------------------------------------------------+
string GenerateNonce() {
   g_nonce_count++;
   return "nonce_" + LongToString(TimeCurrent()) + "_" + LongToString(g_nonce_count);
}

//+------------------------------------------------------------------+
//| Response result structure                                         |
//+------------------------------------------------------------------+
struct ResponseResult {
   bool success;
   int error_code;
   string error_message;
   ulong ticket;
   double price;
   double volume;
};