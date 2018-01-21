#%% Start DataManager API
import orbbit as orb
orb.OM.start_API()
orb.DM.start_API()

#%% Import modules used by these snippets (before sending queries to the API)
import requests
import time
import ccxt
import matplotlib.pyplot as plt
import socket

ORBBIT_HOST = socket.gethostbyname( 'localhost' )
DATAMANAGERPORT = ':5000'
ORDERMANAGERPORT = ':5001'

#%% get balance
jsonreq = {'res':'balance', 'params':{'user':'linternita', 'exchange': 'bittrex'}}
r = requests.post('http://' + ORBBIT_HOST + ORDERMANAGERPORT + '/ordermanager/get/', json=jsonreq)
rjson = r.json()
balance = rjson['balance']
coins = balance.keys()
print(balance)

#%% get trade hist
jsonreq = {'res':'trade_history', 'params':{'user':'linternita', 'exchange': 'bittrex'}}
r = requests.post('http://' + ORBBIT_HOST + ORDERMANAGERPORT + '/ordermanager/get/', json=jsonreq)
trade_history = r.json()
print(trade_history)

#%% Start fetchers
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/fetch/start')
print(r.json())
time.sleep(10)

#%% Get OHLCV
jsonreq = {'res':'ohlcv', 'params':{'symbol':'BTC/USDT', 'exchange': 'bittrex', 'timeframe':'1m'}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/get/', json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))

#%% Get OHLCV
jsonreq = {'res':'ohlcv', 'params':{'symbol':'BTC/USDT', 'exchange': 'hitbtc', 'timeframe':'1m'}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/get/', json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))

#%% plot history
date8061 = [ row['date8061'] for row in ohlcv]
close = [ row['ohlcv']['close'] for row in ohlcv]
plt.plot(date8061, close)

#%% request subscription
jsonreq = {'res':'ohlcv', 'params':{'symbol':'BTC/USDT', 'exchange': 'bittrex', 'timeframe':'5m'}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/subscribe/add', json=jsonreq)
subs = r.json()

#%% Get EMA
jsonreq = {'res':'ema', 'params':{'symbol':'BTC/USDT', 'exchange': 'bittrex', 'timeframe':'1m', 'ema_samples': 12}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/get/', json=jsonreq)
ema_dict_a = r.json()
print(len(ema_dict_a))

jsonreq = {'res':'ema', 'params':{'symbol':'BTC/USDT', 'exchange': 'bittrex', 'timeframe':'1m', 'ema_samples': 5}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/get/', json=jsonreq)
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
jsonreq = {'res':'ohlcv', 'params':{'symbol':'BTG/USDT', 'exchange': 'bittrex', 'timeframe':'5m'}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/fetch/add', json=jsonreq)
print(r.json())

#%% DataManager status
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager')
print(r.json())

#%% Ordermanager get
r = requests.post('http://127.0.0.1:5001/datamanager/get')
print(r.json())

#%% Start spyder (cli)

activate orb_conda

spyder

#%%



