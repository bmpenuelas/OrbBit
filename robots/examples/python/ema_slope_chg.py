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

#%% 
date8061 = [ row['date8061'] for row in ohlcv]
close = [ row['ohlcv']['close'] for row in ohlcv]
plt.plot(date8061, close)


ema = ExpMovingAverage(close,5)
plt.plot(date8061, ema)

ema_slope_chgs = []

i = 1
up = 1 if ema[i] > ema[i-1] else 0

while i < len(ema)-1:
    if (up and (ema[i] < ema[i-1])) or (not up and (ema[i] > ema[i-1])):
        up = not up
        
        ema_slope_chgs.append(date8061[i+1])
        plt.plot(date8061[i+1], ema[i+1], 'g*')
        plt.plot(date8061[i+1], close[date8061.index(date8061[i+1])], 'ro')
        
    i += 1



plt.show()
