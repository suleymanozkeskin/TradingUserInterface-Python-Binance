

class Balance:
    def __init__(self,info):
        #self.initial_margin = float(info["initial_margin"])
        self.maintenance_margin = float(info["maintMargin"])
        self.margin_balance = float(info["marginBalance"])
        self.wallet_balance = float(info["walletBalance"])
        self.unrealized_pnl = float(info["unrealizedProfit"])



class Candle:
    def __init__(self, candle_info, timeframe, exchange):
        if exchange == "binance":
            self.timestamp = candle_info[0]
            self.open = float(candle_info[1])
            self.high = float(candle_info[2])
            self.low = float(candle_info[3])
            self.close = float(candle_info[4])
            self.volume = float(candle_info[5])

        

        elif exchange == "parse_trade":
            self.timestamp = candle_info['ts']
            self.open = candle_info['open']
            self.high = candle_info['high']
            self.low = candle_info['low']
            self.close = candle_info['close']
            self.volume = candle_info['volume']



def tick_to_decimals(tick_size: float) -> int:
    tick_size_str = "{0:.8f}".format(tick_size)
    while tick_size_str[-1] == "0":
        tick_size_str = tick_size_str[:-1]

    split_tick = tick_size_str.split(".")

    if len(split_tick) > 1:
        return len(split_tick[1])
    else:
        return 0



class Contract:
    def __init__(self,contract_info):
        self.symbol = contract_info["symbol"]
        self.status = contract_info["status"]
        self.base_asset = contract_info["baseAsset"]
        self.quote_asset = contract_info["quoteAsset"]
        self.margin_asset = contract_info["marginAsset"]
        self.price_precision = contract_info["pricePrecision"]
        self.quantity_precision = contract_info["quantityPrecision"]
        self.base_asset_precision = contract_info["baseAssetPrecision"]
        self.quote_precision = contract_info["quotePrecision"]
        
        
        
        self.filters = contract_info["filters"]
        self.order_types = contract_info["orderTypes"]
        self.time_in_force = contract_info["timeInForce"]

        
class OrderStatus:
    def __init__(self,order_info):
        self.order_id = order_info["orderId"]
        self.symbol = order_info["symbol"]
        self.client_order_id = order_info["clientOrderId"]
        self.price = float(order_info["price"])
        self.orig_qty = float(order_info["origQty"])
        self.executed_qty = float(order_info["executedQty"])
        self.cummulative_quote_qty = float(order_info["cummulativeQuoteQty"])
        self.status = order_info["status"]
        self.time_in_force = order_info["timeInForce"]
        self.type = order_info["type"]
        self.side = order_info["side"]
        self.stop_price = float(order_info["stopPrice"])
        self.iceberg_qty = float(order_info["icebergQty"])
        self.time = int(order_info["time"])
        self.update_time = int(order_info["updateTime"])
        self.is_working = order_info["isWorking"]
        self.orig_quote_order_qty = float(order_info["origQuoteOrderQty"])
        self.orig_client_order_id = order_info["origClientOrderId"]

class Trade:
    def __init__(self, trade_info):
        self.time: int = trade_info['time']
        self.contract: Contract = trade_info['contract']
        self.strategy: str = trade_info['strategy']
        self.side: str = trade_info['side']
        self.entry_price: float = trade_info['entry_price']
        self.status: str = trade_info['status']
        self.pnl: float = trade_info['pnl']
        self.quantity = trade_info['quantity']
        self.entry_id = trade_info['entry_id']