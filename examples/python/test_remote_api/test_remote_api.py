#!/usr/bin/python3

import requests

#ORBBIT_HOST = 'orbbit.hopto.org'
#ORBBIT_HOST = socket.gethostbyname( 'localhost' )
ORBBIT_HOST = '127.0.0.1'
DATAMANAGERPORT = ':5000'
ORDERMANAGERPORT = ':5001'

#%% DataManager status
r = requests.get('http://' + ORBBIT_HOST + DATAMANAGERPORT + '/datamanager')
print(r.json())
