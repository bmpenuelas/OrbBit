# -*- coding: utf-8 -*-
"""Example Robot: Execute buy/sell at EMA slope changes.

Set the desired OHLC timeframe and the desired EMA periods for smoothing the curve.


Attributes:
    EMA_SAMPLES (int): Higher value gives smoother curves but more delayed response.
    TIMEFRAME (str): See datamanager 'timeframe_to_ms' valid values.

"""


import orbbit as orb

import requests

#%% Start OrbBit
orb.start_DataManager_API()

r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')
print(r.json())

#%% 
