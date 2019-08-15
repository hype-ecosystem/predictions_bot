
import sys
import requests
import json
import pandas as pd
import numpy as np
import datetime
import calendar
import time

def fetch_data(start, stop, symbol, interval, tick_limit):    
    td = (datetime.datetime.fromtimestamp(stop / 1000) - datetime.datetime.fromtimestamp(start / 1000))  
    total_hours = td.days * 24 + td.seconds // 3600
    data = []
    while(total_hours):
        bucket_size = total_hours if tick_limit > total_hours else tick_limit
        total_hours -= bucket_size
        end = start + bucket_size * 3600 * 1000
        query = (f"https://api.bitfinex.com/v2/candles/trade:{interval}:"
        f"{symbol}/hist?limit={tick_limit}&start={start}&end={end}&sort=-1")        
        res = requests.get(query).json()
        data.extend(res)
        print('Retrieving data from {} to {} for {}'.format(pd.to_datetime(start, unit='ms'), pd.to_datetime(end, unit='ms'), symbol))
        start = end                                                            
        time.sleep(1.5)
    
    return data

def append_1h_history(start, symbol, file_path):
    t_stop = calendar.timegm(datetime.datetime.utcnow().timetuple()) * 1000 # s -> ms   
    bin_size = '1h'
    limit = 5000
    pair_data = fetch_data(start=start, stop=t_stop, symbol=symbol, interval=bin_size, tick_limit=limit)        
    # Remove error messages
    ind = [np.ndim(x) != 0 for x in pair_data]
    pair_data = [i for (i, v) in zip(pair_data, ind) if v]
    # Create pandas data frame and clean data
    names = ['time', 'open', 'close', 'high', 'low', 'volume']
    df = pd.DataFrame(pair_data, columns=names)
    df.drop_duplicates(inplace=True)
    df.set_index('time', inplace=True, drop=False)
    df.sort_index(inplace=True)
    # Append to history file
    with open(file_path, 'a') as f:        
        df.to_csv(f, header=False, index=False) 
    # Return data 
    return df  


def main(argv):
    usage = "usage: {} start_date end_date market_symbol csv_file_path".format(argv[0])    
    if len(argv) != 5:
        print(usage)
        sys.exit(1)
    format = "%Y-%m-%d"
    t_start = calendar.timegm(datetime.datetime.strptime(argv[1], format).timetuple()) * 1000 # s-> ms 
    t_stop = calendar.timegm(datetime.datetime.strptime(argv[2], format).timetuple()) * 1000 # s -> ms   
    bin_size = '1h'
    limit = 5000                
    
    pair_data = fetch_data(start=t_start, stop=t_stop, symbol=argv[3], interval=bin_size, tick_limit=limit)        
    # Remove error messages
    ind = [np.ndim(x) != 0 for x in pair_data]
    pair_data = [i for (i, v) in zip(pair_data, ind) if v]
    if(len(pair_data) == 0):
        print("Failed to download history data.")
        sys.exit(1)
    # Create pandas data frame and clean data
    names = ['time', 'open', 'close', 'high', 'low', 'volume']
    df = pd.DataFrame(pair_data, columns=names)
    df.drop_duplicates(inplace=True)
    # df['time'] = pd.to_datetime(df['time'], unit='ms')
    df.set_index('time', inplace=True)
    df.sort_index(inplace=True)
    df.to_csv(argv[4], header=False)     
    print('Done retrieving data.')

if __name__== "__main__":
    main(sys.argv)
