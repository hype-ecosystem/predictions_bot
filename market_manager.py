from dbmanager import DatabaseManager
from tgbot import Bot
from market import Market
from plot_provider import PlotProvider
import threading
import datetime
import sys
import logging
import logging.handlers
import queue
from apscheduler.schedulers.background import BackgroundScheduler

class MarketManager:

    def __init__(self, path, bot_token):
        self._bot_token = bot_token
        self._logger = logging.getLogger('MarketManagerLogger')
        self._logger.setLevel(logging.ERROR)
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        self._logger.addHandler(handler)
        self._db = DatabaseManager()
        self._path = path
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(self._dayly_market_plot_job, trigger='cron', hour='0')
        self._scheduler.add_job(self._predictions_job, trigger='cron', hour='*')
        self._scheduler.add_job(self._bot_job, trigger='cron', minute='*')
        self._markets = dict()
        self._message_queue = queue.Queue()

    def process_market_message(self):
        try:
            db = DatabaseManager()
            bot = Bot(self._bot_token)
            message = self._message_queue.get()
            chats = db.get_chat_list()
            if(message["type"] == "text"):
                bot.send_text_message(message["data"], chats)
            elif(message["type"] == "image"):
                bot.send_image(message["data"], chats)
            self._message_queue.task_done()
        except Exception:
            self._logger.exception(f"Failed to process market message.")

    def _predictions_job(self): 
        try: 
            db = DatabaseManager()    
            markets_list = db.get_markets()
            # Create thread for each market
            for m in markets_list:
                if(m in self._markets and self._markets[m].is_alive()):                
                    self._logger.error(f"Thread for market {m} is still alive.")
                    continue
                else:
                    t = threading.Thread(target=market_thread_func, args=(m, self._path, self._message_queue))       
                    t.start()
                    self._markets[m] = t
        except Exception:            
            self._logger.exception("Failed to start predictions job.")
    
    def _bot_job(self):
        try:
            db = DatabaseManager()
            bot = Bot(self._bot_token)
            chats = bot.get_chat_list()
            for c in chats:
                db.add_chat(c)
        except Exception:            
            self._logger.exception("Failed to collect bot chats.")
    
    def _dayly_market_plot_job(self):
        try:
            db = DatabaseManager()
            pp = PlotProvider()
            markets = db.get_markets()
            for m in markets:
                data = db.get_24h_plot_data(m)
                image = pp.get_market_24plot(data, m[1:])
                self._message_queue.put({'type': 'image', 'data': image})
        except Exception:
            self._logger.exception("Failed to push daily market plots.")

    def start(self):
        self._scheduler.start()

def market_thread_func(market_symbol, path, queue):
    m = Market(path, market_symbol, queue)
    m.genotick_predict_and_train()

def main(argv):
    usage = "usage: {} path bot_token".format(argv[0])    
    if len(argv) != 3:
        print(usage)
        sys.exit(1)
       
    manager = MarketManager(argv[1], argv[2])
    manager.start()
    while True:
        manager.process_market_message()

if __name__ == "__main__":
    main(sys.argv)
