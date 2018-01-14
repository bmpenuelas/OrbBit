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
# orb.OM.start_API()

#%% Start UserInterface
# orb.UI.start_API()
orb.UI.telegram_bot.start()