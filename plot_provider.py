import matplotlib.pyplot as plt
from io import BytesIO
from dbmanager import DatabaseManager
import sys
from pandas.plotting import register_matplotlib_converters
import matplotlib.dates as mdates
from tgbot import Bot

class PlotProvider:

    def __init__(self):
        register_matplotlib_converters()
        plt.style.use('dark_background')

    def get_market_24plot(self, data, market_name):
        # data[0] - datetime
        # data[1] - close
        # data[2] - predictions: -1, 0, 1 
        fig,ax = plt.subplots()      
        plt.plot(data[:, 0], data[:, 1], lw=2, ls='-', c='blue')
        plt.grid(True)
        plt.title(market_name)
        plt.xticks(rotation=45)
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%b %d %H:%M'))

        # Draw market down
        filtered = data[data[:, 2] == -1]
        if(len(filtered) > 0):
            plt.plot(filtered[:, 0], filtered[:, 1], marker='v', 
            linestyle = 'None', color='red', mew=1, mec='lightgray', ms=10)
        # # Draw market out
        filtered = data[data[:, 2] == 0]
        if(len(filtered) > 0):
            plt.plot(filtered[:, 0], filtered[:, 1], marker='s', 
            linestyle = 'None', color='gray', mew=1, mec='lightgray', ms=10)
        # # Draw market up
        filtered = data[data[:, 2] == 1]
        if(len(filtered) > 0):
            plt.plot(filtered[:, 0], filtered[:, 1], marker='^', 
            linestyle = 'None', color='black', mew=1, mec='lightgray', ms=10)
       
        # Save to buffer
        bio = BytesIO()
        bio.name = 'plot.png'
        plt.savefig(bio, bbox_inches='tight')
        bio.seek(0)
        return bio

def main(argv):
    usage = "usage: {} market_symbol".format(argv[0])
    if len(argv) != 2:
        print(usage)
        sys.exit(1)
    db = DatabaseManager()                  
    pp = PlotProvider()
    image = pp.get_market_24plot(db.get_24h_plot_data(argv[1]), argv[1][1:])   
    
if __name__ == "__main__":
    main(sys.argv)            

        

