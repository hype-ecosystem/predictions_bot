import subprocess as sp
import datetime
import sys
import re
import os
import pwd
import logging
import logging.handlers
import bitfinex_api
from dbmanager import DatabaseManager
from plot_provider import PlotProvider
import queue


class Market:

    def __init__(self, path, symbol, message_queue):
        self._message_queue = message_queue
        
        # Configure logger
        self._logger = logging.getLogger(f"{symbol}_MarketLogger")
        self._logger.setLevel(logging.ERROR)
        handler = logging.handlers.SysLogHandler(address='/dev/log')
        self._logger.addHandler(handler)

        self._plotProvider = PlotProvider()
        # Path structure:
        # path
        #  - genotick/
        #    - genotick.jar
        #  - <market_name>/
        #    - config.txt
        #    - data/
        #      - <market_symbol>.csv
        #    - robots/
        #      - robot files  
        self._path = os.path.abspath(path)
        self._symbol = symbol
        self._db = DatabaseManager()
        self._genotick_path = fr"{self._path}/genotick/genotick.jar"
        self._data_path = fr"{self._path}/{self._symbol}/data/{self._symbol}.csv"
        self._reverse_data_path = fr"{self._path}/{self._symbol}/data/reverse_{self._symbol}.csv"
        self._gen_config_path = fr"{self._path}/{self._symbol}/config.txt"

    def genotick_predict_and_train(self):
        try:
            ts_prediction_start = self._db.get_last_predictions_ts(self._symbol)
            ts_history_start = self._db.get_last_history_ts(self._symbol) * 1000            
            if(ts_prediction_start is None):
                ts_prediction_start = ts_history_start
            else:
                ts_prediction_start *= 1000
            ts_history_start += 60 * 60 * 1000
            print("Collecting history data...")
            history = bitfinex_api.append_1h_history(
                ts_history_start, self._symbol, self._data_path)
            print("Adding data to database...")
            self._db.append_market_history(history, self._symbol)
            print("Configuring genotick for prediction...")
            self._configure_genotick_prediction(ts_prediction_start)
            print("Creating reverse data file...")
            self._make_reverse_data_file()
            print("Running genotick for prediction...")
            predictions = self._parse_prediction_output(self._genotick_predict())
            if(len(predictions) == 0):
                self._logger.info(f"No predictions for market {self._symbol}")
                return
            print("Queuing predictions and plot to bot queue...")
            self._enqueue_predictions(predictions)
            self._enqueue_market_plot()
            print("Updating predictions in database...")
            self._db.update_predictions(predictions, self._symbol)            
            print("Configuring genotick for training...")
            self._configure_genotick_training(ts_history_start)
            print("Running genotick for training...")
            self._genotick_train()
        except Exception:
            self._logger.exception(f"Failed to predict and train with genotick for market {self._symbol}")

    def _get_custom_env(self):
        result = os.environ.copy()
        result["GENOTICK_LOG_FILE"] = f"{self._symbol}_genotick_log.txt"
        return result

    def _genotick_predict(self):
        command = ["java",
                   "-jar",
                   self._genotick_path,
                   f"input=file:{self._gen_config_path}"]
        cp = sp.run(command, env=self._get_custom_env(), universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if(cp.returncode != 0):
            raise RuntimeError(f"Failed to run genotick in prediction mode for market {self._symbol}.", cp.stdout, cp.stderr)
        return cp.stdout

    def _parse_prediction_output(self, output):
        pattern = re.compile(
            fr"^[\w\/\s]+\/{self._symbol}\.[\sa-z]+(\d+)[a-z\s]+\:\s(OUT|UP|DOWN)$", re.MULTILINE)
        items = pattern.findall(output)
        # Add one hour for predictions timestamp
        predictions = list()
        for item in items:
            predictions.append((int(item[0])/1000 + 60 * 60, item[1]))
        return predictions

    def _enqueue_predictions(self, predictions):
        for p in predictions:
            ts = datetime.datetime.utcfromtimestamp(int(p[0])).strftime('%Y-%m-%d %H:%M:%S')
            message = f"{ts} {self._symbol[1:]} {p[1]}"
            self._message_queue.put({'type': 'text', 'data': message})
    
    def _enqueue_market_plot(self):
        data = self._db.get_24h_plot_data(self._symbol)
        image = self._plotProvider.get_market_24plot(data, self._symbol)
        self._message_queue.put({'type': 'image', 'data': image})

    def _remove_old_reverse_data_file(self):
        command = ["rm", "-f", self._reverse_data_path]
        cp = sp.run(command, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if(cp.returncode != 0):
            raise RuntimeError(f"Failed to remove reverse data file for market {self._symbol}.", cp.stdout, cp.stderr)

    def _make_reverse_data_file(self):
        self._remove_old_reverse_data_file()
        command = ["java",
                   "-jar",
                   self._genotick_path,
                   f"reverse={self._data_path}"]
        cp = sp.run(command, env=self._get_custom_env(), universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if(cp.returncode != 0):
            raise RuntimeError(f"Genotick failed to create reverse data file for market {self._symbol}. ", cp.stdout, cp.stderr)

    def _configure_genotick_prediction(self, start):
        command = ["sed",
                   "-i",
                   "-e",
                   r"s:\([#\s]*\)\(performTraining\s\+\)\(.\+\):\2false:",
                   "-e",
                   fr"s:\([#\s]*\)\(startTimePoint\s\+\)\(.\+\):\2{start}:",
                   "-e",
                   r"s/^[^#]*endTimePoint/#&/",
                   self._gen_config_path]
        cp = sp.run(command, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if(cp.returncode != 0):
            raise RuntimeError(f"Failed to configure genotick for prediction for market {self._symbol}.", cp.stdout, cp.stderr)

    def _configure_genotick_training(self, start):
        command = ["sed",
                   "-i",
                   "-e",
                   r"s:\([#\s]*\)\(performTraining\s\+\)\(.\+\):\2true:",
                   "-e",
                   fr"s:\([#\s]*\)\(startTimePoint\s\+\)\(.\+\):\2{start}:",
                   "-e",
                   r"s/^[^#]*endTimePoint/#&/",
                   self._gen_config_path]
        cp = sp.run(command, universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if(cp.returncode != 0):
            raise RuntimeError(f"Failed to configure genotick for training for market {self._symbol}.", cp.stdout, cp.stderr)

    def _genotick_train(self):
        command = ["java",
                   "-jar",
                   self._genotick_path,
                   f"input=file:{self._gen_config_path}"]
        cp = sp.run(command, env=self._get_custom_env(), universal_newlines=True, stdout=sp.PIPE, stderr=sp.PIPE)
        if(cp.returncode != 0):
            raise RuntimeError(f"Failed to train genotick for market {self._symbol}.", cp.stdout, cp.stderr)


def main(argv):
    usage = "usage: {} market_symbol market_path".format(argv[0])
    if len(argv) != 3:
        print(usage)
        sys.exit(1)
    market = Market(argv[2], argv[1], queue.Queue())
    market.genotick_predict_and_train()

if __name__ == "__main__":
    main(sys.argv)
