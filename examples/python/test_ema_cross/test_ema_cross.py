# import orbbit as orb
#
# import socket
# import sys
# import requests
# import json
# import time
# import matplotlib.pyplot as plt
#
# #%% Start DataManager
# orb.DM.start_API()
#
# ## start the fetchers that ask the exchange for new data
# #r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')
# #time.sleep(10)

#%% params
symbol = 'BTC/USDT'
timeframe = '1h'
ema_samples_fast = 2
ema_samples_slow = 5


#%% Get EMA
jsonreq = {'res':'ema', 'params':{'symbol':symbol, 'exchange': 'hitbtc2', 'timeframe':timeframe, 'ema_samples': ema_samples_fast}}
r = requests.post('http://127.0.0.1:5000/datamanager/get/', json=jsonreq)
ema_dict_a = r.json()

jsonreq = {'res':'ema', 'params':{'symbol':symbol, 'exchange': 'hitbtc2', 'timeframe':timeframe, 'ema_samples': ema_samples_slow}}
r = requests.post('http://127.0.0.1:5000/datamanager/get/', json=jsonreq)
ema_dict_b = r.json()

#%% plot EMA
date8061 = [ row['date8061'] for row in ema_dict_a]
ema_fast = [ row['ema'] for row in ema_dict_a]
ema_slow = [ row['ema'] for row in ema_dict_b]

date8061 = date8061[-1000:]
ema_fast = ema_fast[-1000:]
ema_slow = ema_slow[-1000:]


plt.plot(date8061, ema_fast, 'b')
plt.plot(date8061, ema_slow, 'g')

#%% ohlcv
jsonreq = {'res':'ohlcv', 'params':{'symbol':symbol, 'exchange': 'hitbtc2', 'timeframe':timeframe}}
r = requests.post('http://127.0.0.1:5000/datamanager/get/', json=jsonreq)
ohlcv = r.json()

#%% cross
initial_price = 0
for entry in ohlcv:
    if entry['date8061'] == date8061[0]:
        initial_price = entry['ohlcv']['close']
        break

base_balanace = 50 / initial_price
quote_balanace = 50

fee = 0.1 / 100
txns = []
total_hist = []
i = 1
while i < len(ema_fast):
    if ((ema_fast[i] - ema_slow[i]) > 0) != ((ema_fast[i-1] - ema_slow[i-1]) > 0):
        for entry in ohlcv:
            if entry['date8061'] == date8061[i]:
                if ((ema_fast[i] - ema_slow[i]) > 0): # buy
                    price = entry['ohlcv']['close']

                    base_balanace += (quote_balanace / price) * (1 - fee)
                    quote_balanace = 0

                    plt.plot(date8061[i], price, 'go')
                else: # sell
                    price = entry['ohlcv']['close']

                    quote_balanace += (base_balanace * price) * (1 - fee)
                    base_balanace = 0

                    plt.plot(date8061[i], price, 'bx')

                txns.append(price)
                total_hist.append(quote_balanace + (base_balanace * price) * (1 - fee))
                break
    i += 1

#%% profit
total = quote_balanace + (base_balanace * price) * (1 - fee)

print('bot')
print((total-100) / 100)


final_price = 0
for entry in ohlcv:
    if entry['date8061'] == date8061[-1]:
        final_price = entry['ohlcv']['close']
        break

print('hold')
print((final_price-initial_price) / initial_price)


plt.figure()
plt.plot(total_hist)


