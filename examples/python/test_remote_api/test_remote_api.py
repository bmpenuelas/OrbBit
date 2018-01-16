#!/usr/bin/python3

import requests
import time
import ccxt
import matplotlib.pyplot as plt
import socket

ORBBIT_HOST = 'orbbit.hopto.org'

#%% DataManager status
r = requests.get('http://' + ORBBIT_HOST + ':5000/datamanager')
print(r.json())
