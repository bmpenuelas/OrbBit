try:
    orbbit_started
except NameError:

    import orbbit as orb

    import socket
    import sys
    import requests
    import json
    import time
    import matplotlib.pyplot as plt

    #%% Start DataManager
    orb.DM.start_API()

    # start the fetchers that ask the exchange for new data
    r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')
    time.sleep(10)

    orbbit_started = 1



#%% params
symbol = 'BTC/USDT'
timeframe = '1m'
ema_samples = 100


#%% Get EMA
jsonreq = {'res':'ema', 'params':{'symbol':symbol, 'exchange': 'hitbtc2', 'timeframe':timeframe, 'ema_samples': ema_samples}}
r = requests.post('http://127.0.0.1:5000/datamanager/get/', json=jsonreq)
ema_dict = r.json()

#%% plot EMA
date8061 = [ row['date8061'] for row in ema_dict]
ema = [ row['ema'] for row in ema_dict]

date8061 = date8061[-1000:]
ema = ema[-1000:]


plt.plot(date8061, ema, 'b')

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
i = 2
while i < len(ema):
    slope = 1 if (ema[i] > ema[i-1]) else 0
    slope_previous = 1 if (ema[i-1] > ema[i-2]) else 0

    if slope != slope_previous:
        for entry in ohlcv:
            if entry['date8061'] == date8061[i]:
                if slope > slope_previous: # buy
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


