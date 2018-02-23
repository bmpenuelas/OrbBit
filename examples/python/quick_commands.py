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

#%% get balance_usd
jsonreq = {'res':'balance_usd', 'params':{'user':'linternita', 'exchange': 'bittrex'}}
jsonreq = {'res':'balance_usd', 'params':{'user':'farolillo', 'exchange': 'binance', }}
jsonreq = {'res':'balance_usd', 'params':{'user':'farolillo', 'exchange': 'hitbtc2', }}
r = requests.post('http://' + ORBBIT_HOST + ORDERMANAGERPORT + '/ordermanager/get/', json=jsonreq)
rjson = r.json()
balance_usd = rjson['balance_usd']
print(balance_usd)
coins = balance_usd.keys()
total_usd = rjson['total_usd']
print(total_usd)

#%% get balance
jsonreq = {'res':'balance', 'params':{'user':'linternita', 'exchange': 'bittrex'}}
jsonreq = {'res':'balance', 'params':{'user':'farolillo', 'exchange': 'hitbtc2'}}
r = requests.post('http://' + ORBBIT_HOST + ORDERMANAGERPORT + '/ordermanager/get/', json=jsonreq)
rjson = r.json()
balance = rjson['balance']
coins = balance.keys()
print(balance)

#%% get balance norm trade hist
jsonreq = {'res':'balance_norm_price_history', 'params':{'user':'farolillo', 'exchange': 'hitbtc2', 'timeframe': '1h', 'min_usd_value': 3.0}}
r = requests.post('http://' + ORBBIT_HOST + ORDERMANAGERPORT + '/ordermanager/get/', json=jsonreq)
trade_history = r.json()

#%% get trade hist
jsonreq = {'res':'trade_history', 'params':{'user':'farolillo', 'exchange': 'hitbtc2', 'symbol': 'XRP/USDT'}}
jsonreq = {'res':'trade_history', 'params':{'user':'farolillo', 'exchange': 'hitbtc2'}}
r = requests.post('http://' + ORBBIT_HOST + ORDERMANAGERPORT + '/ordermanager/get/', json=jsonreq)
trade_history = r.json()
print(trade_history)

#%% Get OHLCV
jsonreq = {'res':'ohlcv', 'params':{'symbol':'BTC/USDT', 'exchange': 'bittrex', 'timeframe':'1m'}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/get/', json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))

#%% Get OHLCV
jsonreq = {'res':'ohlcv', 'params':{'symbol':'ETH/USDT', 'exchange': 'hitbtc2', 'timeframe':'1m'}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/get/', json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))

#%% Get ticker
jsonreq = {'res':'ticker', 'params':{'symbol':'BTC/USDT', 'exchange': 'hitbtc2'}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/get/', json=jsonreq)
ticker = r.json()
print(ticker)

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
r = requests.post('http://127.0.0.1:5001/ordermanager/get')
print(r.json())

#%% Start spyder (cli)

activate orb_conda

spyder

#%%

