from email import header
import logging
import symbol
import time
import requests
import pprint
import hmac
import hashlib
import websocket, threading , json
from urllib.parse import urlparse, urlencode
from models import OrderStatus, Contract, Candle, Balance
import typing


logger = logging.getLogger()

url_for_futures = "https://fapi.binance.com"  ## api for futures
url_for_testnet_futures =  "https://testnet.binancefuture.com"  ## api for testnet binance futures
wss_url_for_testnet_futures = "wss://stream.binancefuture.com/ws"  ## websocket url for futures

# TO CONNECT TO THE BINANCE WEB SOCKET (SO THAT WE HAVE CONSTATNTLY UPDATED DATA AS OPPOSED TO RESTFUL API'S)
# WE NEED TO USE THE WEBSOCKET  PROTOCOL INSTEAD OF HTTP

"wss://fstream.binance.com"  ## web socket protocol for futures



# def get_contracts():
#     url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
#     response = requests.get(url)
#     # pprint.pprint(response.json())
#     # pprint.pprint(response.json()["symbols"]) # THIS WILL PRINT ALL THE SYMBOLS IN THE MARKET ONE BY ONE
#     # print(response.status_code)
    
#     contracts = [] # WE INITIALIZE AN EMPTY LIST TO STORE THE CONTRACTS

    

#     for contract in response.json()["symbols"]:
#             #print(contract["pair"])  # THIS WILL PRINT ALL THE PAIRS IN BINANCE FUTURES MARKET.
#             contracts.append(contract["pair"]) # WE APPEND THE PAIRS TO THE LIST WE CREATED EARLIER

#     return contracts


# print(get_contracts())



class BinanceFuturesClient:
    def __init__(self,public_key: str ,secret_key: str ,testnet: bool):
        if testnet:
            self._base_url = url_for_testnet_futures
            self._wss_url = wss_url_for_testnet_futures
        else:
            self._base_url = url_for_futures
               
        
        self._public_key = public_key
        self._secret_key = secret_key
        
        self._headers = {"X-MBX-APIKEY": self._public_key}
        
        self.contracts = self.get_contracts()
        self.balances = self.get_balances()

        self.prices = dict()

        self.logs = []

        self._ws_id = 1
        #self.ws: websocket.WebSocketApp
        self.reconnect = True
        self.ws_connected = False
        self.ws_subscriptions = {"bookTicker": [], "aggTrade": []}
        self._ws = None

        t = threading.Thread(target=self._start_ws)
        t.start()

        
        logger.info("Binance Futures Client successfully initialized")


    def _add_log(self, message: str):

        """
        Add a log to the list so that it can be picked by the update_ui() method of the root component.
        :param messageg:
        :return:
        """

        logger.info("%s", message)
        self.logs.append({"log": message, "displayed": False})

    def _generate_signature(self, data: typing.Dict): #✅
        return hmac.new(self._secret_key.encode(), urlencode(data).encode(), hashlib.sha256).hexdigest()

    


    def _make_request(self, method: str, endpoint: str, data: typing.Dict): #✅
        
        if method == "GET":
            try:
                response = requests.get(self._base_url + endpoint, params=data,headers=self._headers)
            except Exception as e:
                logger.error("Error while making %s request to %s: %s", method, endpoint, e)
                return None # WE CAN RETURN NONE BECAUSE THERE WILL BE NOTHING TO PARSE , NOT EVEN AN HTTP RESPONSE STATUS CODE


        
        elif method == "POST":
            try:
                response = requests.post(self._base_url + endpoint, params=data,headers=self._headers)
            except Exception as e:
                logger.error("Error while making %s request to %s: %s", method, endpoint, e)
                return None

        
        elif method == "DELETE":
            try:
                response = requests.delete(self._base_url + endpoint, params=data,headers=self._headers)
            except Exception as e:
                logger.error("Error while making %s request to %s: %s", method, endpoint, e)
                return None 


        else:
            raise ValueError()
        
        if response.status_code == 200:
            return response.json()
        
        else:
            logger.error("Error while making %s request to %s: %s (error code %s)", method, endpoint, response.json(),response.status_code)
            return None


    def _start_ws(self):
        self._ws = websocket.WebSocketApp(wss_url_for_testnet_futures, on_open = self._on_open , on_message=self._on_message, on_error=self._on_error, on_close=self._on_close)

        while True:
            try:
                self._ws.run_forever()
            except Exception as e:
                logger.info("Binance error in run_forever() method: %s", e)
                time.sleep(3)
        
            


    def _on_open(self,ws):
        logger.info("Binance connection opened")

        self.ws_connected = True

        # The aggTrade channel is subscribed to in the _switch_strategy() method of strategy_component.py

        for channel in ["bookTicker", "aggTrade"]:
            for symbol in self.ws_subscriptions[channel]:
                self.subscribe_channel([self.contracts[symbol]], channel, reconnection=True)

        if "BTCUSDT" not in self.ws_subscriptions["bookTicker"]:
            self.subscribe_channel([self.contracts["BTCUSDT"]], "bookTicker")



    def _on_message(self,ws,message: str):
        
        data = json.loads(message) #json.loads() method can be used to parse a valid JSON string and convert it into a Python Dictionary.
        
        if "e" in data and data["e"] == "bookTicker":
            symbol = data["s"]

            

            if symbol not in self.prices:
                self.prices[symbol] = {"bid": float(data["b"]), "ask": float(data["a"])}
            else:
                self.prices[symbol]["bid"] = float(data["b"])
                self.prices[symbol]["ask"] = float(data["a"])
            print(self.prices[symbol])


    def _on_error(self,ws,error: str):
        logger.error("Binance connection error: %s", error)

    def _on_close(self,ws):
        logger.warning("Binance Websocket connection closed")
        self.ws_connected = False

    def subscribe_channel(self, contracts: typing.List[Contract], channel: str , reconnection =False):
        
        
        
        if len(contracts) > 200:
            logger.warning("Subscribing to more than 200 contracts will mostl likely fail.Consider subscribing only when adding a symbol to your Watchlist or when starting a strategy for a symbol.")
            
        
        data = dict()
        data["method"] = "SUBSCRIBE"
        data["params"] = []
        
        if len(contracts) == 0:
            data['params'].append(channel)
        else:
            for contract in contracts:
                if contract.symbol not in self.ws_subscriptions[channel] or reconnection:
                    data['params'].append(contract.symbol.lower() + "@" + channel)
                    if contract.symbol not in self.ws_subscriptions[channel]:
                        self.ws_subscriptions[channel].append(contract.symbol)

            if len(data['params']) == 0:
                return

        data['id'] = self._ws_id

        try:
            self._ws.send(json.dumps(data))
        except Exception as e:
            logger.error("Websocket error while subscribing to channel %s: %s updates : %s", len(contracts),channel,e)
            return False

        self._ws_id += 1

        return data 
    


    ### MARKET DATA ###


    def get_contracts(self): #✅
        exchange_info = self._make_request("GET", "/fapi/v1/exchangeInfo", None)
        contracts = dict()


        if exchange_info is not None:
            for contract_data in exchange_info["symbols"]:
                contracts[contract_data["pair"]] = Contract(contract_data)

       

        return contracts




    def get_historical_candles(self, contract: Contract, interval): #✅ Since we have created a Contract object, a contract data model could be used to replace symbol variable that we used earlier.
        data = dict()
        data["symbol"] = contract.symbol
        data["interval"] = interval
        data["limit"] = 1000

        raw_candles = self._make_request("GET", "/fapi/v1/klines", data)
        candles = []

        if raw_candles is not None:
            for candle in raw_candles:
                candles.append(Candle(candle)) # WE CREATE A CANDLE OBJECT FOR EACH CANDLE AND APPEND IT TO THE LIST WE CREATED EARLIER
        
        # candles[-1].close() # WE GET THE CLOSE PRICE OF THE LAST CANDLE.

        return candles



    def get_bid_ask(self,contract: Contract): #✅
        data = dict()
        data["symbol"] = contract.symbol
        

        obtained_data = self._make_request("GET", "/fapi/v1/ticker/bookTicker", data)

        if obtained_data is not None:
            if contract.symbol not in self.prices:
                self.prices[contract.symbol] = {"bid": float(obtained_data["bidPrice"]), "ask": float(obtained_data["askPrice"])}
            else:
                self.prices[contract.symbol]["bid"] = float(obtained_data["bidPrice"])
                self.prices[contract.symbol]["ask"] = float(obtained_data["askPrice"])


        return self.prices[contract.symbol]

    
    
    
    ### ACCOUNT DATA ###

    def futures_account_balance(self):  #✅
        data = dict()
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)

        account_balance = self._make_request("GET", "/fapi/v2/balance", data)

        return account_balance

    def get_balances(self):  #✅
        data = dict()
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)

        balances = dict()

        account_data = self._make_request("GET", "/fapi/v2/account", data)

        if account_data is not None:
            for assets in account_data["assets"]:
                balances[assets["asset"]] = Balance(assets)
                
        print(balances["USDT"].wallet_balance)
            
        return balances


    ### ORDER MANAGEMENT ###

    def get_open_orders(self):  #✅
        data = dict()
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)
        open_orders = self._make_request("GET", "/fapi/v1/openOrders", data)

        return open_orders


    def get_all_orders(self,contract: Contract ,start_date = None ,end_date = None, limit = None): # NOT WORKING AT THE MOMENT
        data = dict()
        data["symbol"] = contract.symbol
        data["timestamp"] = int(time.time() * 1000)
        data["signature"] = self._generate_signature(data)
        data["recvWindow"] = 5000
        data["startTime"] = start_date
        data["endTime"] = end_date
        if limit >1000:
            limit = 1000
            print("Limit cannot be more than 1000")
        data["limit"] = limit

        

        all_orders = self._make_request("GET", "/fapi/v1/allOrders", data)

        return all_orders

    def get_order_status(self, contract: Contract, order_id): #✅
        data = dict()
        data["symbol"] = contract.symbol
        data["orderId"] = order_id
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)
        order_status = self._make_request("GET", "/fapi/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status)

        return order_status

    def get_position(self, contract: Contract): #✅ THIS METHOD GETS A LIST OF ALL TICKERS EVEN IF THERE IS NO OPEN POSITION FOR THAT TICKER.
        data = dict()
        data["symbol"] = contract.symbol
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)
        position = self._make_request("GET", "/fapi/v2/positionRisk", data)

        return position

    def get_open_positions(self): #✅
        data = dict()
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)

        all_tickers = self._make_request("GET", "/fapi/v2/positionRisk", data)  
        
        open_positions = []

        for item in all_tickers:
            if float(item["positionAmt"])  > 0:
                open_positions.append(item)       

        return open_positions

    ## MARKET INFORMATION ##
    
    def get_account(self): #✅ GET CURRENT ACCOUNT INFORMATION
        data = dict()
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)

        account = self._make_request("GET", "/fapi/v2/account", data)

        return account

    def get_funding_rate(self, contract: Contract): #✅ STILL WORKS BUT NOT VISIBLE ON BINANCE DOCUMENTATION.
        data = dict()
        data["symbol"] = symbol

        funding_rate = self._make_request("GET", "/fapi/v1/fundingRate", data)

        return funding_rate

    


    def get_recent_trades(self, contract: Contract,limit = None): #✅ THIS GETS THE LAST TRADES FROM EXCHANGE(EVERYONE)
        data = dict()
        data["symbol"] = contract.symbol

        trades = self._make_request("GET", "/fapi/v1/trades", data)

        return trades

    def get_liquidation_orders(self, contract: Contract): # 'The endpoint has been out of maintenance'}
        data = dict()
        data["symbol"] = contract.symbol

        liquidation_orders = self._make_request("GET", "/fapi/v1/allForceOrders", data)

        return liquidation_orders

    def get_open_interest(self, contract: Contract): #✅
        data = dict()
        data["symbol"] = contract.symbol

        open_interest = self._make_request("GET", "/fapi/v1/openInterest", data)

        return open_interest

    def get_open_interest_hist(self, contract: Contract): #NOT WORKING AT THE MOMENT
        data = dict()
        data["symbol"] = contract.symbol

        open_interest_hist = self._make_request("GET", "/fapi/v1/openInterestHist", data)

        return open_interest_hist

    def get_top_long_short_accounts(self, contract: Contract): #
        data = dict()
        data["symbol"] = contract.symbol

        top_long_short_accounts = self._make_request("GET", "/fapi/v1/topLongShortAccountRatio", data)

        return top_long_short_accounts

    def get_trade_volume(self, contract: Contract):
        data = dict()
        data["symbol"] = contract.symbol

        trade_volume = self._make_request("GET", "/fapi/v1/tradeVolume", data)

        return trade_volume

    def get_taker_buy_sell_volume(self, contract: Contract):
        data = dict()
        data["symbol"] = contract.symbol

        taker_buy_sell_volume = self._make_request("GET", "/fapi/v1/takerBuySellVol", data)

        return taker_buy_sell_volume
    
    def get_historical_trades(self, contract: Contract): #✅ 
        data = dict()
        data["symbol"] = contract.symbol

        historical_trades = self._make_request("GET", "/fapi/v1/historicalTrades", data)

        return historical_trades

    def get_force_orders(self, contract: Contract, timestamp): #✅ # FIGURE OUT HOW TO USE TIMESTAMP HERE
        data = dict()
        data["symbol"] = contract.symbol
        data["timestamp"] = timestamp
        data["signature"] = self._generate_signature(data)

        force_orders = self._make_request("GET", "/fapi/v1/forceOrders", data)

        return force_orders

    def get_agg_trades(self, contract: Contract): #✅
        data = dict()
        data["symbol"] = contract.symbol

        agg_trades = self._make_request("GET", "/fapi/v1/aggTrades", data)

        return agg_trades



    ### POSITIONS ###

    def get_current_position_mode(self,timestamp=None): #Get user's position mode (Hedge Mode or One-way Mode ) on EVERY symbol
        data = dict()
        if timestamp == None:
            data["timestamp"] = int(time.time() * 1000)
        
        data["recvWindow"] = 5000

        data["signature"] = self._generate_signature(data)

        position_mode = self._make_request("GET", "/fapi/v2/positionSide/dual", data)

        return position_mode

    def change_position_mode(self, dual_side_position,timestamp):
        data = dict()
        data["dualSidePosition"] = dual_side_position
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000

        data["signature"] = self._generate_signature(data)

        position_mode = self._make_request("POST", "/fapi/v2/positionSide/dual", data)

        return position_mode


    


    def modify_isolated_position_margin(self, contract: Contract, position_side, amount, type):
        data = dict()
        data["symbol"] = contract.symbol
        data["positionSide"] = position_side
        data["amount"] = amount
        data["type"] = type
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000

        position_margin = self._make_request("POST", "/fapi/v1/positionMargin", data)

        return position_margin

    def get_position_margin_change_history(self, contract: Contract, position_side, startTime, endTime, limit):
        data = dict()
        data["symbol"] = contract.symbol
        data["positionSide"] = position_side
        data["startTime"] = startTime
        data["endTime"] = endTime
        data["limit"] = limit
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000

        position_margin_history = self._make_request("GET", "/fapi/v1/positionMargin/history", data)

        return position_margin_history

    def get_position_information(self, contract: Contract):
        data = dict()
        data["symbol"] = contract.symbol
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000

        position_info = self._make_request("GET", "/fapi/v2/positionRisk", data)

        return position_info

    def change_leverage(self, contract: Contract, leverage):
        data = dict()
        data["symbol"] = contract.symbol
        data["leverage"] = leverage
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000

        leverage = self._make_request("POST", "/fapi/v1/leverage", data)

        return leverage

    
    
    
    ### ORDERS ###

    def place_order(self, contract: Contract,side,quantity,order_type,price=None,tif=None):
        data = dict()
        data["symbol"] = contract.symbol
        data["side"] = side
        data["quantity"] = quantity
        data["type"] = order_type
        
        if price is not None:
            data["price"] = price
        if tif is not None: 
            data["timeInForce"] = tif

        data["timestamp"] = int(time.time() * 1000)
        data["signature"] = self._generate_signature(data)

        order_status = self._make_request("POST", "/fapi/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status)

        return order_status
    
    
    # def place_new_order(self, symbol, side, type, quantity, price=None, time_in_force=None, new_client_order_id=None, stop_price=None, iceberg_qty=None, new_order_resp_type=None, recv_window=None, timestamp=None):
    #     data = dict()
    #     data["symbol"] = symbol
    #     data["side"] = side
    #     data["type"] = type
    #     data["quantity"] = quantity
    #     data["signature"] = self._generate_signature(data)
    #     if price:
    #         data["price"] = price
    #     if time_in_force:
    #         data["timeInForce"] = time_in_force
    #     if new_client_order_id:
    #         data["newClientOrderId"] = new_client_order_id
    #     if stop_price:
    #         data["stopPrice"] = stop_price
    #     if iceberg_qty:
    #         data["icebergQty"] = iceberg_qty
    #     if new_order_resp_type:
    #         data["newOrderRespType"] = new_order_resp_type
    #     if recv_window:
    #         data["recvWindow"] = recv_window
    #     if timestamp:
    #         data["timestamp"] = timestamp
    #     else:
    #         data["timestamp"] = int(time.time() * 1000)

    #     order = self._make_request("POST", "/fapi/v1/order", data)

    #     return order


    def place_multiple_orders(self, orders):
        data = dict()
        data["orders"] = orders
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000

        order = self._make_request("POST", "/fapi/v1/batchOrders", data)

        return order

    
    def query_order(self, contract: Contract, order_id=None, orig_client_order_id=None, recv_window=None, timestamp=None):
        data = dict()
        data["symbol"] = contract.symbol
        data["signature"] = self._generate_signature(data)
        if order_id:
            data["orderId"] = order_id
        if orig_client_order_id:
            data["origClientOrderId"] = orig_client_order_id
        if recv_window:
            data["recvWindow"] = recv_window
        if timestamp:
            data["timestamp"] = timestamp
        else:
            data["timestamp"] = int(time.time() * 1000)

        order = self._make_request("GET", "/fapi/v1/order", data)

        return order


    def query_current_open_order(self, contract: Contract):
        data = dict()
        data["symbol"] = contract.symbol
        data["order_id"] = order_id
        data["origClientOrderId"] = orig_client_order_id
        data["recvWindow"] = 5000
        data["timestamp"] = int(time.time() * 1000)

    def current_all_open_orders(self, contract: Contract):
        data = dict()
        data["symbol"] = contract.symbol
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000

        open_orders = self._make_request("GET", "/fapi/v1/openOrders", data)

        return open_orders

    def get_all_orders(self, contract: Contract, start_time=None, end_time=None, limit=None, recv_window=None, timestamp=None):
        data = dict()
        data["symbol"] = contract.symbol
        if start_time:
            data["startTime"] = start_time
        if end_time:
            data["endTime"] = end_time
        if limit:
            data["limit"] = limit
        if recv_window:
            data["recvWindow"] = recv_window
        if timestamp:
            data["timestamp"] = timestamp
        else:
            data["timestamp"] = int(time.time() * 1000)

        orders = self._make_request("GET", "/fapi/v1/allOrders", data)

        return orders

    


    def cancel_order(self, contract: Contract, order_id=None, orig_client_order_id=None, new_client_order_id=None, recv_window=None, timestamp=None):

        data = dict()
        data["symbol"] = contract.symbol
        if order_id:
            data["orderId"] = order_id
        if orig_client_order_id:
            data["origClientOrderId"] = orig_client_order_id
        if new_client_order_id:
            data["newClientOrderId"] = new_client_order_id
        if recv_window:
            data["recvWindow"] = recv_window
        if timestamp:
            data["timestamp"] = timestamp
        else:
            data["timestamp"] = int(time.time() * 1000)

        order_status = self._make_request("DELETE", "/fapi/v1/order", data)

        if order_status is not None:
            order_status = OrderStatus(order_status)


        return order_status

    # def cancel_multiple_orders(self, symbol, orders):


    def cancel_all_open_orders(self, contract: Contract):
        data = dict()
        data["symbol"] = contract.symbol
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)

        open_orders = self._make_request("DELETE", "/fapi/v1/allOpenOrders", data)

        return open_orders

    def auto_cancel_all_open_orders(self, contract: Contract,countdownTime=int):
        data = dict()
        data["symbol"] = contract.symbol
        data["countdownTime"] = 1000 * countdownTime # countdown time, 1000 for 1 second. 0 to cancel the timer
        data["timestamp"] = int(time.time() * 1000)
        data["recvWindow"] = 5000
        data["signature"] = self._generate_signature(data)

        open_orders = self._make_request("DELETE", "/fapi/v1/openOrders", data)

        return open_orders

    ### PRICE ###

    def get_mark_price(self, contract: Contract): #✅ THIS GETS THE MARK PRICE AND FUNDING RATE.
        data = dict()
        data["symbol"] = contract.symbol

        mark_price = self._make_request("GET", "/fapi/v1/premiumIndex", data)

        return mark_price
