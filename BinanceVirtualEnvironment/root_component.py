import tkinter as tk
from styling import *
from logging_component import Logging
from datetime import datetime
from binance_futures import BinanceFuturesClient
from watchlist_component import *
from trades_component import *
from strategy_component import *
import logging

logger = logging.getLogger()

class Root(tk.Tk):
    def __init__(self, binance: BinanceFuturesClient):
        super().__init__()

        self.binance = binance
        

        self.title("Trading Bot")

        self.configure(bg=BackGround_Colour)

        self._left_frame = tk.Frame(self, bg=BackGround_Colour)
        self._left_frame.pack(side=tk.LEFT)

        self._right_frame = tk.Frame(self, bg=BackGround_Colour)
        self._right_frame.pack(side=tk.LEFT)

        self._watchlist_frame = Watchlist(self.binance.contracts,  self._left_frame, bg=BackGround_Colour)
        self._watchlist_frame.pack(side=tk.TOP)

        self.logging_frame = Logging(self._left_frame, bg=BackGround_Colour)
        self.logging_frame.pack(side=tk.TOP)

        self._strategy_frame = StrategyEditor(self, self.binance,self._right_frame, bg=BackGround_Colour)
        self._strategy_frame.pack(side=tk.TOP)

        self._trades_frame = TradesWatch(self._right_frame, bg=BackGround_Colour)
        self._trades_frame.pack(side=tk.TOP)

        self._update_ui()

   
   
    def _update_ui(self):

        # Logs
        for log in self.binance.logs:
            if not log['displayed']:
                self.logging_frame.add_log(log['log'])
                log['displayed'] = True

        # Watchlist prices

        try:
            for key, value in self._watchlist_frame.body_widgets['symbol'].items():

                symbol = self._watchlist_frame.body_widgets['symbol'][key].cget("text")
                exchange = self._watchlist_frame.body_widgets['exchange'][key].cget("text")

                if exchange == "Binance":
                    if symbol not in self.binance.contracts:
                        continue

                    if symbol not in self.binance.prices:
                        self.binance.get_bid_ask(self.binance.contracts[symbol])
                        continue

                    precision = self.binance.contracts[symbol].price_decimals

                    prices = self.binance.prices[symbol]

                

                else:
                    continue

                if prices['bid'] is not None:
                    price_str = "{0:.{prec}f}".format(prices['bid'], prec=precision)
                    self._watchlist_frame.body_widgets['bid_var'][key].set(price_str)
                if prices['ask'] is not None:
                    price_str = "{0:.{prec}f}".format(prices['ask'], prec=precision)
                    self._watchlist_frame.body_widgets['ask_var'][key].set(price_str)

        except RuntimeError as e:
            logger.error("Error while looping through watchlist dictionary: %s", e)


        self.after(1000, self._update_ui)
