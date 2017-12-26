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

# %% Generic definitions
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



# %% EMA Slope Detector definitions
class slope_detector():
    """Instantiate a slope change detector with hystereis.

    With a slope change it will execute a trade (sell if new slope is descending,
    buy if new slope is ascending). 
    Then it will set hysteresis bands for upper and lower bounds.
    If the current value surpasses the bands it will:
      - Clear the bands if value went in the desired direction. A profit equal
        to the band minus 2 txn fees is guaranteed.
      - Make the inverse transaction. A loss equal to the band plus 2 txn fees 
        will occur.

    Args:

    Attributes:
        curr_slope (int): +1 ascending, -1 descending
    """

    valid_status = ('stop', 'wait_slope_chg', 'new_trade', 'wait_in_band',)
    
    def __init__(self, order_volume, history, continue_level, reverse_level):

        self.history = history

        # hysteresis
        self.dir_enter = +1
        self.continue_level = continue_level
        self.reverse_level = reverse_level


        self.order_volume = order_volume
        self.balance = 3 * order_volume


        self.current_status = 'stop'

        self.first_slope_acquired = 0
        self.prev_slope = +1
        self.curr_slope = +1



    def updt_status():
        if self.current_status == 'stop':

            self.acq_first_slope()

            if self.first_slope_acquired:
                self.current_status = 'wait_slope_chg'


        elif self.current_status == 'wait_slope_chg':
            
            self.updt_slope()
            
            if self.prev_slope != self.curr_slope:
                self.dir_enter = self.prev_slope
                self.current_status = 'new_trade'


        elif self.current_status == 'new_trade':

            trade(self.dir_enter)

            self.current_status = 


        elif self.current_status == 'wait_in_band':

            self.current_status = 
        else:
            raise NameError ('Invalid status.')

    def tick(current_value):
      pass




    def acq_first_slope():
        pass


    def trade(direction, ):
        if direction = +1:
            self.trade('sell')
        elif direction = -1:
            self.trade('buy')
        else:
            raise ValueError ('Direction can only be +1 or -1.')

        return 0



def ExpMovingAverage(values, window):
    """ Numpy implementation of EMA
    """
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a


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
