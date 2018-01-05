# Subscriber example:
#   1- Tell the API which data stream you want to subscribe to.
#   2- Listen for new data timely delivered in the returned IP, PORT

import orbbit as orb

import socket
import sys 
import requests
import json


#%% Start DataManager
orb.DM.start_API()

# start the fetchers that ask the exchange for new data
r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')

#%% request subscription
jsonreq = {'res':'ohlcv', 'params':{'symbol':'BTC/USD','timeframe':'1m'}}
r = requests.get('http://127.0.0.1:5000/datamanager/subscribe/add', json=jsonreq)
response_dict = r.json()
print(response_dict)

#%% keep only the (IP, PORT) part of the response, the socket expects a tuple.
subs = list( response_dict.values() )[0] 
ip_port_tuple = tuple(subs)

#%% connect socket
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except socket.error:
    print('Failed to create socket')
    sys.exit()

s.connect( ip_port_tuple )
print('Connected')

#%% get new data as soon as it is generated
while 1:
    reply = s.recv(4096) # waits here until new data is received
    reply_dict = json.loads(reply.decode('ascii')) # turn string into data structure
    print('Live new data:')
    print(reply_dict)
