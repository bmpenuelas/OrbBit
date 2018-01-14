#!/usr/bin/python3

# Subscriber example:
#   1- Tell the API which data stream you want to subscribe to.
#   2- Listen for new data timely delivered in the returned IP, PORT

import orbbit as orb

import socket
import sys
import requests
import json
import time
import matplotlib.pyplot as plt


# ORBBIT_HOST = socket.gethostbyname( 'localhost' )
ORBBIT_HOST = '172.31.31.52'

#%% Start DataManager
orb.DM.start_API()

# start the fetchers that ask the exchange for new data
time.sleep(5)
r = requests.get('http://' + ORBBIT_HOST + ':5000/datamanager/fetch/start')
time.sleep(5)

#%% request subscription
jsonreq = {'res':'macd', 'params':{'symbol':'BTC/USDT', 'timeframe':'1m', 'ema_fast': 5, 'ema_slow': 12}}
r = requests.get('http://' + ORBBIT_HOST + ':5000/datamanager/subscribe/add', json=jsonreq)
response_dict = r.json()
print(response_dict)

#%% keep only the (IP, PORT) part of the response, the socket expects a tuple.
subs = list( response_dict.values() )[0]
ip_port_tuple = tuple(subs)

#%% connect socket
time.sleep(5)
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error:
    print('Failed to create socket')
    sys.exit()

time.sleep(5)
s.connect( ip_port_tuple )
print('Connected')

#%% get new data as soon as it is generated
date8061 = []
ema_fast = []
ema_slow = []

while 1:
    reply = s.recv(4096) # waits here until new data is received
    reply_dict = json.loads(reply.decode('ascii')) # turn string into data structure
    print('Live new data:')
    print(reply_dict)

    date8061.append(reply_dict['date8061'])
    ema_fast.append(reply_dict['macd']['ema_fast'])
    ema_slow.append(reply_dict['macd']['ema_slow'])


plt.plot(date8061, ema_fast)
plt.plot(date8061, ema_slow)
plt.show
