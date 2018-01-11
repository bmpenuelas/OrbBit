#%% Start DataManager API
import orbbit as orb
orb.DM.start_API()

#%% Import modules used by these snippets (before sending queries to the API)
import requests
import time
import ccxt
import matplotlib.pyplot as plt

#%% Start fetchers
r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')
print(r.json())
time.sleep(10)

#%% request subscription
jsonreq = {'res':'ohlcv', 'params':{'symbol':'XRP/USD','timeframe':'5m'}}
r = requests.get('http://127.0.0.1:5000/datamanager/subscribe/add', json=jsonreq)
subs = r.json()

#%% Get OHLCV
jsonreq = {'res':'ohlcv', 'params':{'symbol':'BTC/USD','timeframe':'1m'}}
r = requests.get('http://127.0.0.1:5000/datamanager/get/', json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))

#%% plot history
date8061 = [ row['date8061'] for row in ohlcv]
close = [ row['ohlcv']['close'] for row in ohlcv]
plt.plot(date8061, close)

#%% Get EMA
jsonreq = {'res':'ema', 'params':{'symbol':'BTC/USD','timeframe':'1m', 'ema_samples': 12}}
r = requests.get('http://127.0.0.1:5000/datamanager/get/', json=jsonreq)
ema_dict_a = r.json()
print(len(ema_dict_a))

jsonreq = {'res':'ema', 'params':{'symbol':'BTC/USD','timeframe':'1m', 'ema_samples': 5}}
r = requests.get('http://127.0.0.1:5000/datamanager/get/', json=jsonreq)
ema_dict_b = r.json()
print(len(ema_dict_b))

#%% plot EMA
date8061 = [ row['date8061'] for row in ema_dict_a]
ema_a = [ row['ema'] for row in ema_dict_a]
ema_b = [ row['ema'] for row in ema_dict_b]
plt.plot(date8061, ema_a, 'b')
plt.plot(date8061, ema_b, 'g')

#%% export json to file
with open('./save.json', 'w') as f:
    json.dump(ohlcv, f)

#%% Add pair
jsonreq = {'res':'ohlcv', 'params':{'symbol':'LTC/USD','timeframe':'15m'}}
r = requests.get('http://127.0.0.1:5000/datamanager/fetch/add', json=jsonreq)
print(r.json())

#%% DataManager status
r = requests.get('http://127.0.0.1:5000/datamanager')
print(r.json())

#%% Start spyder (cli)

activate orb_conda

spyder

#%%



