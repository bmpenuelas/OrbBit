#%% Start spyder (cli)

activate orb_conda

spyder

#%% Start DataManager API
import orbbit as orb
orb.DM.start_API()

#%% Import modules used by these snippets (before sending queries to the API)
import requests 
import ccxt

#%% Get BTC/USD OHLCV 5m
jsonreq = {'symbol':'BTC/USD','timeframe':'5m'}
r = requests.get('http://127.0.0.1:5000/datamanager/get/ohlcv',json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))

#%% Add pair
jsonreq = {'symbol':'ETC/USD','timeframe':'1m'}
r = requests.get('http://127.0.0.1:5000/datamanager/fetch/add',json=jsonreq)
print(r.json())

#%% DataManager status
r = requests.get('http://127.0.0.1:5000/datamanager')
print(r.json())

#%% Start fetchers
r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')
print(r.json())
