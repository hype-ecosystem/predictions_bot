import sys
import os
import pwd
import psycopg2
import pandas as pd
import numpy as np
from io import StringIO

class DMError(Exception):
    def __init__(self, msg, original_exception=None):
        if(msg is None):
            msg = "Database error:"
        if(original_exception is None):
            super(DMError, self).__init__(msg)
        else:
            super(DMError, self).__init__(msg + f": {original_exception}")

class DatabaseManager:

    def __init__(self): 
        try:
            user = pwd.getpwuid(os.getuid())[0]
            self._connection = psycopg2.connect(user=user, password="", 
            database="markets")
        except (Exception, psycopg2.Error) as error :
            raise DMError(None, error)

    def __del__(self):
        if getattr(self, '_connection', None):       
            self._connection.close()

    def add_chat(self, chat_id):
        try:
            query = "INSERT INTO \"public\".chats(id) VALUES(%s) ON CONFLICT (id) DO NOTHING;"
            with self._connection:
                with self._connection.cursor() as c:
                    c.execute(query, (chat_id,))
        except (Exception, psycopg2.Error) as error :
            raise DMError("Failed to add bot chat id. ", error)

    def get_chat_list(self):
        try:
            query = "SELECT id FROM \"public\".chats;"
            with self._connection.cursor() as c:
                c.execute(query)
                return [item[0] for item in c.fetchall()]
        except (Exception, psycopg2.Error) as error :
            raise DMError("Failed to get chats. ", error)

    def get_markets(self):
        try:
            query = "SELECT bitfinex_api_symbol FROM \"public\".market_info;"
            with self._connection.cursor() as c:
                c.execute(query)
                return [item[0] for item in c.fetchall()]
        except (Exception, psycopg2.Error) as error :
            raise DMError("Failed to get markets. ", error)       
    
    def get_market_id(self, market_symbol):
        try:
            query = "SELECT id FROM \"public\".market_info WHERE bitfinex_api_symbol=%s;"
            with self._connection.cursor() as c:
                c.execute(query, (market_symbol,))
                record = c.fetchone()
                if(record[0] is None):
                    raise RuntimeError("no data.")
                else:
                    return record[0]
        except (Exception, psycopg2.Error) as error :
            raise DMError(f"Failed to get id for market {market_symbol}", error)       

    def get_last_predictions_ts(self, market_symbol):
        try:
            query = """SELECT extract(epoch from max(time_stamp))::integer 
            FROM "public".market_predictions 
            WHERE market_id=(SELECT id FROM "public".market_info 
            WHERE bitfinex_api_symbol=%s);"""
            with self._connection.cursor() as c:
                c.execute(query, (market_symbol,))
                return c.fetchone()[0]
        except (Exception, psycopg2.Error) as error :
            raise DMError(f"Failed to get last predictions timestamp for market {market_symbol}", error)       

    def get_last_history_ts(self, market_symbol):
        try:
            query = """SELECT extract(epoch from max(time_stamp))::integer 
            FROM "public".market_history 
            WHERE market_id=(SELECT id FROM "public".market_info 
            WHERE bitfinex_api_symbol=%s);"""
            with self._connection.cursor() as c:
                c.execute(query, (market_symbol,))
                record = c.fetchone()
                if(record[0] is None):
                    raise RuntimeError("no data.")    
                else:
                    return record[0]
        except (Exception, psycopg2.Error) as error :
            raise DMError(f"Failed to get last history timestamp for market {market_symbol}", error)       

    def append_market_history(self, df, market_symbol):
        try:            
            id = self.get_market_id(market_symbol)
            del df['volume']
            df["market_id"] = id
            df["time"]=(pd.to_datetime(df["time"], unit='ms', utc=True)) 
            df.rename(columns={'time': 'time_stamp'}, inplace=True)
            # Initialize a string buffer
            sio = StringIO()
            sio.write(df.to_csv(index=None, header=None))  # Write the Pandas DataFrame as a csv to the buffer
            sio.seek(0)  # Be sure to reset the position to the start of the stream
            with self._connection:
                with self._connection.cursor() as c:
                    c.copy_from(sio, "public.market_history", columns=df.columns, sep=',')                
        except (Exception, psycopg2.Error) as error :
            raise DMError(f"Failed to append history for market {market_symbol}", error)                         

    def update_predictions(self, predictions, market_symbol):  
        # As predictions are for next hours, one prediction will not have a 
        # record in history     
        """WITH m AS (SELECT id FROM "public".market_info WHERE name = 'BTCUSD')
        INSERT INTO "public".market_predictions(time_stamp, market_id, genotick_prediction)
        SELECT to_timestamp(tmp.ts/1000) AT TIME ZONE 'UTC', (SELECT id FROM m), tmp.pred FROM (VALUES 
        (1565010000000, 0)
        ) AS tmp(ts, pred) """
        try:           
            query = r"""WITH m AS (SELECT id FROM "public".market_info WHERE name = %s)
            INSERT INTO "public".market_predictions(time_stamp, market_id, genotick_prediction)
            SELECT to_timestamp(tmp.ts) AT TIME ZONE 'UTC', (SELECT id FROM m), tmp.pred FROM (VALUES 
            """
            query_params = [market_symbol[1:]]
            for p in predictions:
                query += "(%s, %s),"
                # Prediction for next hour
                val = (0 if p[1] == "OUT" else (-1 if p[1] == "DOWN" else 1))                
                print("TS:", int(p[0]), "VAL:", val, p[1])
                query_params.extend([int(p[0]), val])            
            query = query[:-1]
            query += r""" ) AS tmp(ts, pred);"""
            with self._connection:
                with self._connection.cursor() as c:
                    c.execute(query, query_params)       
        except (Exception, psycopg2.Error) as error :
            raise DMError(f"Failed to update predictions for market {market_symbol}", error)                         

    def get_24h_plot_data(self, market_symbol):
        try:
            query = r"""SELECT h.time_stamp, h.close, p.genotick_prediction
            FROM market_history h
            INNER JOIN market_predictions p
            ON h.market_id = p.market_id AND h.time_stamp = p.time_stamp
            WHERE h.market_id=(SELECT id FROM market_info WHERE bitfinex_api_symbol=%s)
            AND
            h.time_stamp >= ((now() at time zone 'utc') - interval '24 hours') at time zone 'utc'
            ORDER BY h.time_stamp ASC;
            """
            with self._connection.cursor() as c:
                c.execute(query, (market_symbol,))
                return np.array(c.fetchall())
        except (Exception, psycopg2.Error) as error :
            raise DMError(f"Failed to get data for 24h plot for market {market_symbol}", error)                         
              
          

def main(argv):
    print(argv)

if __name__== "__main__":
    main(sys.argv)