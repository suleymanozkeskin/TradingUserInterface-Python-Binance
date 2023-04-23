from asyncore import file_dispatcher
import formatter
import time
import pandas as pd
import tkinter as tk
from tkinter import ttk
import logging
import formatter
import pprint
from root_component import Root

from binance_futures import BinanceFuturesClient

logger = logging.getLogger()

#logger.critical("This message is about a critical error that will stop the program")

logger.setLevel(logging.INFO)

stream_handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s :: %(message)s')
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

file_handler = logging.FileHandler('info.log')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

logger.addHandler(stream_handler)
logger.addHandler(file_handler)

# logger.debug("This message is important only when debugging the program")
# logger.info("This message just shows basic information")
# logger.warning("this message is about something you should pay attention to")
# logger.error("This message helps to debug an error that occureed in your program")

# write_log()

# root = tk.Tk()

# root.mainloop()


# if __name__ == '__main__':
#     logger.info("this is logged only if we execute main.py file")
#     root = tk.Tk()
#     root.mainloop()

pp = pprint.PrettyPrinter(width=100, compact=True)

if __name__ == '__main__':

    binance = BinanceFuturesClient('cf2fcb604fdcf8fc1ebac7d7af4c65a3409d8817deef908f5b07ce1c19065794',
                                    '52522abadc1f5e8b1d5b1eab5c701e9b38c8f917266bec9870aca96ea0324fb7',True)

    
    #print(binance.cancel_all_open_orders("BTCUSDT"))
    #print(binance.futures_account_balance())
    #print((binance.place_order("LINKUSDT","BUY",15,"LIMIT",7.52,"GTC")))
    #pp.pprint(binance.get_balances())
    #print(binance.get_open_positions())
    #print(binance.get_order_status("LINKUSDT","121523285"))
    #print(binance.get_mark_price("LINKUSDT"))
    #pp.pprint(binance.get_current_position_mode())
    #print(binance.get_funding_history("BTCUSDT"))
    #pp.pprint(binance.place_order("ETHUSDT","SELL",6,"TAKE_PROFIT","1480","GTC"))
    #pp.pprint(binance.get_open_positions())
    
    
    root = Root(binance)
    root.mainloop()