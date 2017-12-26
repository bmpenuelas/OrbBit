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
import json


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

    fee_pcnt = 0.1
    valid_status = ('stop', 'wait_slope_chg', 'new_trade', 'wait_in_band',)
    valid_direction = (+1, -1)
    valid_event = ('enter', 'exit')
    process_latency = 5
    
    def __init__(self, order_volume, history):

        self.history = history
        self.prev_value = history[-2]
        self.curr_value = history[-1]

        # hysteresis
        self.event_dir = 'enter'
        self.event_dir = +1
        self.continue_coef = self.fee_pcnt
        self.continue_level = self.curr_value
        self.reverse_coef = 2 * self.fee_pcnt
        self.reverse_level = self.curr_value


        self.order_volume = order_volume # in quote currency
        self.quote_balance = 3 * order_volume
        # start with same balance on base / quote
        self.base_balance = self.quote_balance / self.curr_value


        self.curr_status = 'stop'

        self.first_slope_acquired = 0
        self.prev_slope = +1
        self.curr_slope = +1



    def updt_status(self):
        if self.curr_status == 'stop':

            self.acq_first_slope()

            if self.first_slope_acquired:
                self.curr_status = 'wait_slope_chg'


        elif self.curr_status == 'wait_slope_chg':
            
            self.updt_slope()
            
            if self.prev_slope != self.curr_slope:
                self.event = 'enter'
                self.event_dir = self.prev_slope
                self.curr_status = 'new_trade'


        elif self.curr_status == 'new_trade':

            self.trade(self.event, self.event_dir)

            self.continue_level = self.curr_value * (1 + self.event_dir * self.continue_coef)
            self.reverse_level  = self.curr_value * (1 - self.event_dir * self.reverse_coef)

            self.curr_status = 'wait_in_band'


        elif self.curr_status == 'wait_in_band':
            
            self.updt_slope()

            if  ((self.event_dir == +1) and self.curr_value > self.continue_level)  \
             or ((self.event_dir == -1) and self.curr_value < self.continue_level):
                self.event = 'exit'
                self.event_dir = self.curr_slope
                self.curr_status = 'new_trade'

            elif ((self.event_dir == -1) and self.curr_value > self.reverse_level)  \
             or  ((self.event_dir == +1) and self.curr_value < self.reverse_level):
                self.curr_status = 'wait_slope_chg'

            else:
                raise ValueError
 
        else:
            raise NameError ('Invalid status.')



    def tick(self, curr_value):
        self.prev_value = self.curr_value
        self.curr_value = curr_value

        i = 0
        while i < self.process_latency:
            self.updt_status()
            print(self.curr_status)
            i += 1



    def updt_slope(self):
        self.prev_slope = self.curr_slope
        self.curr_slope = +1 if self.curr_value > self.prev_value else -1
        return 0
        

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
            self.order_volume += self.order_volume / self.curr_value

        elif order_type == 'buy':
            self.quote_balance += self.order_volume * (1 - self.fee_pcnt)
            self.order_volume -= self.order_volume / self.curr_value

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


def ExpMovingAverage(values, window):
    """ Numpy implementation of EMA
    """
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a




#############################################################################
#                                 SCRIPT                                    #
#############################################################################

#%% Start OrbBit
orb.DM.start_API()

#%% Start fetchers
r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')
print(r.json())

#%% Get OHLCV
jsonreq = {'symbol':'ETC/USD','timeframe':'1m'}
r = requests.get('http://127.0.0.1:5000/datamanager/get/ohlcv',json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))

#%% calculate EMA and find slope changes
date8061 = [ row['date8061'] for row in ohlcv]
close = [ row['ohlcv']['close'] for row in ohlcv]

fig = plt.figure()
line, = plt.plot(date8061, close, 'b')
fig.canvas.mpl_connect('pick_event', DataCursor(plt.gca()))
line.set_picker(1) # Tolerance in points
plt.show()


#%%
with open('./save.json', 'w') as f:
    json.dump(ohlcv, f)