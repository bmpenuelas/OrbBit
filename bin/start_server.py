#!/usr/bin/python3

import orbbit as orb

import socket
import sys
import requests
import json
import time



#%% Start DataManager
orb.DM.start_API()

#%% Start OrderManager
orb.OM.start_API()

#%% Start UserInterface
# orb.UI.start_API()
orb.UI.telegram_bot.start()


# Start fetching data from the exchanges 
time.sleep(5)
ORBBIT_HOST = socket.gethostbyname('localhost')

r = requests.post('http://' + ORBBIT_HOST + ':5000/datamanager/fetch/start')
print(r.json())

