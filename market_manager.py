from dbmanager import DatabaseManager
from tgbot import Bot
from market import Market
import threading
import datetime
import sys
import logging
import logging.handlers
import queue
from apscheduler.schedulers.background import BackgroundScheduler

class MarketManager:

    def __init__(self, path, bot):
        self._bot = bot
        self._logger = logging.getLogger('MarketManagerLogger')
        self._logger.setLevel(logging.ERROR)
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        self._logger.addHandler(handler)
        self._db = DatabaseManager()
        self._path = path
        self._scheduler = BackgroundScheduler()
        self._scheduler.add_job(self._predictions_job, trigger='cron', hour='*')
        self._scheduler.add_job(self._bot_job, trigger='cron', minute='*')
        self._markets = dict()
        self._message_queue = queue.Queue()

    def process_market_message(self):
        try:
            message = self._message_queue.get()
            chats = self._db.get_chat_list()
            self._bot.send_message(message, chats)
            self._message_queue.task_done()
        except Exception:
            self._logger.exception(f"Failed to process market message.")

    def _predictions_job(self):        
        markets_list = self._db.get_markets()
        # Create thread for each market
        for m in markets_list:
            if(m in self._markets and self._markets[m].is_alive()):                
                self._logger.error(f"Thread for market {m} is still alive.")
                continue
            else:
                t = threading.Thread(target=market_thread_func, args=(m, self._path, self._message_queue))       
                t.start()
                self._markets[m] = t
    
    def _bot_job(self):
        try:
            chats = self._bot.get_chat_list()
            for c in chats:
                self._db.add_chat(c)
        except Exception:
            self._logger.exception(f"Failed to collect bot chats.")
    

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
   
    bot = Bot(argv[2])
    manager = MarketManager(argv[1], bot)
    manager.start()
    while True:
        manager.process_market_message()

if __name__ == "__main__":
    main(sys.argv)
