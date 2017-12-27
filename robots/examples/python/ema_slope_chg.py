# -*- coding: utf-8 -*-
"""Example Robot: Execute buy/sell at EMA slope changes.

Set the desired OHLC timeframe and the desired EMA periods for smoothing the curve.


Attributes:
    EMA_SAMPLES (int): Higher value gives smoother curves but more delayed response.
    TIMEFRAME (str): See datamanager 'timeframe_to_ms' valid values.

"""

#%% Imports
import orbbit as orb

import numpy as np
import matplotlib.pyplot as plt

import requests
import time


#%%##########################################################################
#                   EMA SLOPE DETECTOR DEFINITIONS                          #
#############################################################################
class slope_detector():
    """Instantiate a slope change detector with hystereis.

    With a slope change it will execute a trade (sell if new slope is descending,
    buy if new slope is ascending). 
    Then it will set hysteresis bands for upper and lower bounds.
    If the curr value surpasses the bands it will:
      - Clear the bands if value went in the desired direction. A profit equal
        to the band minus 2 txn fees is guaranteed.
      - Make the inverse transaction. A loss equal to the band plus 2 txn fees 
        will occur.

    Args:

    Attributes:
        curr_slope (int): +1 ascending, -1 descending
    """

    fee_pcnt = 0.001
    valid_status = ('stop', 'wait_slope_chg', 'wait_in_band',)
    valid_direction = (+1, -1)
    valid_event = ('enter', 'exit')
    
    def __init__(self, order_volume, ema_samples, time_stamp, curr_value):

        self.time_stamps = [time_stamp]
        self.curr_time_stamp = time_stamp

        self.history = [curr_value]
        self.prev_value = curr_value
        self.curr_value = curr_value

        self.ema_samples = ema_samples
        self.ema = curr_value
        self.prev_ema_value = curr_value
        self.curr_ema_value = curr_value

        # hysteresis
        self.event_dir = 'enter'
        self.event_dir = +1
        self.continue_coef = self.fee_pcnt
        self.continue_level = self.curr_value
        self.reverse_coef = 2 * self.fee_pcnt
        self.reverse_level = self.curr_value


        self.buy_history = []
        self.sell_history = []

        self.order_volume = order_volume # in quote currency
        self.initial_balance = 3 * order_volume
        self.quote_balance = self.initial_balance
        self.base_balance = self.initial_balance / self.curr_value # same base/quote bal


        self.curr_status = 'stop'

        self.first_slope_acquired = 1
        self.prev_slope = +1
        self.curr_slope = +1



    def updt_status(self):
        if self.curr_status == 'stop':

            self.acq_first_slope()

            if self.first_slope_acquired:
                self.curr_status = 'wait_slope_chg'


        elif self.curr_status == 'wait_slope_chg':
            
            self.updt_ema_slope()
            
            if self.prev_slope != self.curr_slope:
                self.event = 'enter'
                self.event_dir = self.prev_slope

                self.new_trade()

                self.curr_status = 'wait_in_band'


        elif self.curr_status == 'wait_in_band':
            
            self.updt_ema_slope()

            if  ((self.event_dir == +1) and (self.curr_value > self.continue_level))  \
             or ((self.event_dir == -1) and (self.curr_value < self.continue_level)):
                self.event = 'exit'
                self.event_dir = self.curr_slope

                self.new_trade()
                self.curr_status = 'wait_in_band'

            elif ((self.event_dir == -1) and (self.curr_value > self.reverse_level))  \
             or  ((self.event_dir == +1) and (self.curr_value < self.reverse_level)):
                self.curr_status = 'wait_slope_chg'
 
        else:
            raise NameError ('Invalid status.')



    def tick(self, curr_time_stamp, curr_value):
        self.updt_values(curr_time_stamp, curr_value)
        self.updt_status()
        print(self.curr_status)



    def updt_values(self, curr_time_stamp, curr_value):
        self.prev_value = self.curr_value
        self.prev_ema_value = self.curr_ema_value

        self.history.append(curr_value)
        self.time_stamps.append(curr_time_stamp)

        history_len = len(self.history)-1
        curr_ema_samples = min(history_len, self.ema_samples)
        self.ema = ExpMovingAverage(self.history, curr_ema_samples)

        self.curr_time_stamp = self.time_stamps[-1]
        self.curr_value = self.history[-1]
        self.curr_ema_value = self.ema[-1]


    def updt_ema_slope(self):
        self.prev_slope = self.curr_slope
        if self.curr_ema_value > self.prev_ema_value:
            self.curr_slope = +1
        elif self.curr_ema_value < self.prev_ema_value:
            self.curr_slope = -1

        return 0
        

    def new_trade(self):
        self.trade(self.event, self.event_dir)

        self.continue_level = self.curr_value * (1 + self.event_dir * self.continue_coef)
        self.reverse_level  = self.curr_value * (1 - self.event_dir * self.reverse_coef)


    def acq_first_slope(self):
        pass
        return 0


    def trade(self, event, direction):
        if (direction not in self.valid_direction) or (event not in self.valid_event):
            raise ValueError

        if ((event == 'enter') and (direction == +1)) \
         or ((event == 'exit') and (direction == -1)):
            self.new_order('buy')
        elif ((event == 'enter') and (direction == -1)) \
         or ((event == 'exit') and (direction == +1)):
            self.new_order('sell')
        else:
            raise ValueError
        return 0

    def new_order(self, order_type):
        if order_type == 'buy':
            self.quote_balance -= self.order_volume * (1 + self.fee_pcnt)
            self.base_balance += self.order_volume / self.curr_value

            self.buy_history.append([self.curr_time_stamp, self.curr_value])

        elif order_type == 'sell':
            self.quote_balance += self.order_volume * (1 - self.fee_pcnt)
            self.base_balance -= self.order_volume / self.curr_value

            self.sell_history.append([self.curr_time_stamp, self.curr_value])

        else:
            raise ValueError



#%%##########################################################################
#                         GENERIC DEFINITIONS                               #
#############################################################################
class DataCursor(object):
    text_template = 'x: %0.2f\ny: %0.2f'
    x, y = 0.0, 0.0
    xoffset, yoffset = -20, 20
    text_template = 'x: %0.2f\ny: %0.2f'

    def __init__(self, ax):
        self.ax = ax
        self.annotation = ax.annotate(self.text_template, 
                xy=(self.x, self.y), xytext=(self.xoffset, self.yoffset), 
                textcoords='offset points', ha='right', va='bottom',
                bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.5),
                arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0')
                )
        self.annotation.set_visible(False)

    def __call__(self, event):
        self.event = event
        # xdata, ydata = event.artist.get_data()
        # self.x, self.y = xdata[event.ind], ydata[event.ind]
        self.x, self.y = event.mouseevent.xdata, event.mouseevent.ydata
        if self.x is not None:
            self.annotation.xy = self.x, self.y
            self.annotation.set_text(self.text_template % (self.x, self.y))
            self.annotation.set_visible(True)
            event.canvas.draw()



def plot_w_cursor(list_x_y):
    fig = plt.figure()
    for x_y in list_x_y:
        line, = plt.plot(*x_y)
        fig.canvas.mpl_connect('pick_event', DataCursor(plt.gca()))
        line.set_picker(1) # Tolerance in points
        plt.show()



def ExpMovingAverage(values, window):
    """ Numpy implementation of EMA
    """
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a




#%%##########################################################################
#                                 SCRIPT                                    #
#############################################################################
#plt.close("all")

# %% Run parameters
SYMBOL = 'ETC/USD'
EMA_SAMPLES = 12
TIMEFRAME = '1m'

#%% Start OrbBit
try:
    orbbit_started
except NameError:
    orb.DM.start_API()
    orbbit_started = 1

r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')
print(r.json())

time.sleep(5)

#%% Get OHLCV
jsonreq = {'symbol': SYMBOL,'timeframe': TIMEFRAME}
r = requests.get('http://127.0.0.1:5000/datamanager/get/ohlcv',json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))

#%% Plot history
date8061 = [ row['date8061'] for row in ohlcv]
close = [ row['ohlcv']['close'] for row in ohlcv]
ema = ExpMovingAverage(close, EMA_SAMPLES)

#%% Run detector
bot = slope_detector(order_volume = 1, ema_samples = 5, time_stamp = date8061[0], curr_value = close[0])

i = 1
samples = len(close)
while i < samples:
    bot.tick(date8061[i], close[i])
    print ('Sample ' + str(i) + ' time_stamp ' + str(date8061[i]))
    i += 1


# %% Results

sale_x = [sale[0] for sale in bot.sell_history]
sale_y = [sale[1] for sale in bot.sell_history]
sale_style = 'rx'

purchase_x = [purchase[0] for purchase in bot.buy_history]
purchase_y = [purchase[1] for purchase in bot.buy_history]
purchase_style = 'go'

plot_w_cursor([[bot.time_stamps, bot.history, 'b'], 
               [bot.time_stamps, bot.ema, 'r'], 
               [sale_x, sale_y, sale_style],
               [purchase_x, purchase_y, purchase_style],
              ]
             )



profit = (bot.quote_balance + bot.base_balance * bot.curr_value)  \
         / (2 * bot.initial_balance) - 1

print('RESULT profit ' + str(profit))

