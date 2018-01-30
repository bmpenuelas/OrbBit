#!/usr/bin/python3

try:
    initialized
except NameError:
    import requests
    import time
    import ccxt
    import matplotlib.pyplot as plt
    import socket

    from keras.layers.core import Dense, Activation, Dropout
    from keras.layers.recurrent import LSTM
    from keras.models import Sequential

    import numpy as np


    # Start OrbBit APIs
    import orbbit as orb
    orb.OM.start_API()
    orb.DM.start_API()

    ORBBIT_HOST = socket.gethostbyname( 'localhost' )
    DATAMANAGERPORT = ':5000'
    ORDERMANAGERPORT = ':5001'

    initialized = 1



#%% Get OHLCV and training data
SYMBOL = 'BTC/USDT'
EXCHANGE = 'hitbtc2'
TIMEFRAME = '1m'


FEE = 0.0025
MIN_TRADE_PROFIT = 0.0025


buy_coef  = (1 + (MIN_TRADE_PROFIT + 2 * FEE)) # if price will be higher than this you should buy
sell_coef = (1 - (MIN_TRADE_PROFIT + 2 * FEE)) # if price will be lower than this you should sell


jsonreq = {'res':'ohlcv', 'params':{'symbol': SYMBOL, 'exchange': EXCHANGE, 'timeframe': TIMEFRAME}}
r = requests.post('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager/get/', json=jsonreq)
ohlcv = r.json()
print(len(ohlcv))


#%%
N_SAMPLES = 1000

date8061 = [ row['date8061'] for row in ohlcv[-N_SAMPLES:]]
o        = [ row['ohlcv']['open'] for row in ohlcv[-N_SAMPLES:]]
h        = [ row['ohlcv']['high'] for row in ohlcv[-N_SAMPLES:]]
l        = [ row['ohlcv']['low'] for row in ohlcv[-N_SAMPLES:]]
c        = [ row['ohlcv']['close'] for row in ohlcv[-N_SAMPLES:]]
v        = [ row['ohlcv']['volume'] for row in ohlcv[-N_SAMPLES:]]


# plt.figure(0)
# plt.ylabel('OHLCV')
# plt.plot(date8061, o)
# plt.plot(date8061, h)
# plt.plot(date8061, l)
# plt.plot(date8061, c)
# plt.show()


# Output data: 0 if you should sell because price will go down at least sell_coef, 1 if you should buy
# because it will rise by buy_coef


# Y contains the absolutely ideal buy and sell spots (0 for buy, 1 for sell)
Y = [0]
future_samples = [0]

for i in range(len(c)):
    current_price = c[i]
    for j in range(i+1, len(c)): # see what happens first
        if Y[-1] == 1:
            if c[j] < current_price:
                Y.append( Y[-1] )
                future_samples.append(j-i)
                break
            elif c[j] > current_price * buy_coef:
                Y.append( 0 )
                future_samples.append(j-i)
                break
            elif j >= len(c) - 1:
                Y.append( Y[-1] )
                future_samples.append(j-i)
        elif Y[-1] == 0:
            if c[j] > current_price:
                Y.append( Y[-1] )
                future_samples.append(j-i)
                break
            elif c[j] < current_price * sell_coef:
                Y.append( 1 )
                future_samples.append(j-i)
                break
            elif j >= len(c) - 1:
                Y.append( Y[-1] )
                future_samples.append(j-i)

Y = Y[1:]+[Y[-1]]
future_samples = future_samples[1:]+[future_samples[-1]]


# plt.figure(1)
# plt.ylabel('Future samples used in prediction')
# plt.plot(future_samples)
# plt.show()


# plt.figure(2)
# plt.ylabel('Buys (o) and sells (x)')
# plt.plot(date8061, c)
# for i in range(1, len(c)):
#     if Y[i-1] == 0 and Y[i] == 1: # sell
#         plt.plot(date8061[i], c[i], 'bx')
#     elif Y[i-1] == 1 and Y[i] == 0: # buy
#         plt.plot(date8061[i], c[i], 'go')
# plt.show()


# Generate windows for training
WINDOW_SIZE = 50


def gen_window(samples, window_size):
    i = 0
    while i < len(samples) - window_size:
        sample_list = samples[i : i + window_size]
        yield [[sample, v[i]] for sample in sample_list]
        i += 1

date8061_gen_list = list( gen_window(date8061, WINDOW_SIZE) )
o_gen_list        = list( gen_window(o, WINDOW_SIZE) )
h_gen_list        = list( gen_window(h, WINDOW_SIZE) )
l_gen_list        = list( gen_window(l, WINDOW_SIZE) )
c_gen_list        = list( gen_window(c, WINDOW_SIZE) )
v_gen_list        = list( gen_window(v, WINDOW_SIZE) )



# Select data for ML input
# X = np.array([ [o_gen_list[i], h_gen_list[i], l_gen_list[i], c_gen_list[i], v_gen_list[i]] for i in range(len(c_gen_list))])
X = np.array(c_gen_list)
Y = Y[-len(c_gen_list) : ]
Y = np.array(Y)


#%% TF Model operation
# create model
model = Sequential()

model.add(LSTM(input_dim=2, output_dim=50, return_sequences=True))
model.add(Dropout(0.2))

model.add(LSTM(100, return_sequences=False))
model.add(Dropout(0.2))

model.add(Dense(output_dim=1))
model.add(Activation("sigmoid"))


model.compile(loss="mse", optimizer="rmsprop", metrics=['accuracy'])


# Fit the model
model.fit(X, Y, batch_size=len(Y), epochs=10, validation_split=0.1)

# evaluate the model
scores = model.evaluate(X, Y)
print("\n%s: %.2f%%" % (model.metrics_names[1], scores[1]*100))
