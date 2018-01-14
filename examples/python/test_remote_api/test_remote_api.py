#!/usr/bin/python3

import requests
import time
import ccxt
import matplotlib.pyplot as plt
import socket

ORBBIT_HOST = '172.31.31.52'

#%% DataManager status
r = requests.get('http://' + ORBBIT_HOST + ':5000/datamanager')
print(r.json())
