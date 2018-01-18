#!/usr/bin/python3

import sys
import time
import threading
import queue
import numpy as np
import socket
from   flask          import Flask, jsonify, abort, make_response, request
from   flask_httpauth import HTTPBasicAuth
import ccxt
import pymongo
import json

from   orbbit.common.common import *



#%%##########################################################################
#                               CONFIGURATION                               #
#############################################################################

#%%--------------------------------------------------------------------------
# NETWORK
#----------------------------------------------------------------------------

# API
ORDERMANAGER_API_IP = '0.0.0.0'
ORDERMANAGER_API_PORT = 5001




#%%##########################################################################
#                              DATABASE SETUP                               #
#############################################################################

ordermanager_db = database_connection('ordermanager')




#%%##########################################################################
#                              EXCHANGES SETUP                              #
#############################################################################

user_info = get_database_info('ordermanager', 'user_info')

user_exchanges = {}
for user in user_info:
    user_exchanges[user] = {exchange: exchange_id_to_user_exchange(exchange, user) for exchange in user_info[user]['exchanges']}




#%%##########################################################################
#                              ORDERMANAGER API                              #
#############################################################################

#----------------------------------------------------------------------------
# Flask App error funcs redefinition
#----------------------------------------------------------------------------

app = Flask(__name__)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)



#----------------------------------------------------------------------------
# AUTHENTICATION
#----------------------------------------------------------------------------

auth = HTTPBasicAuth()
""" Add @auth.login_required to a route/method definition to make it
    password-protected.
"""

@auth.get_password
def get_password(username):
    if username == 'rob':
        return 'bot'
    return None

@auth.error_handler
def unauthorized():
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)




#----------------------------------------------------------------------------
# ROUTES AND METHODS
#----------------------------------------------------------------------------
#----------------------------------------------------------------------------
#   Route /ordermanager
#----------------------------------------------------------------------------

@app.route('/ordermanager', methods=['GET'])
def ordermanager_status():
    """ Get ordermanager status.
    Args:

    Returns:
        Status of the OrderManager API and processes.
    """

    return jsonify({'status': 'aaaaa'})



#----------------------------------------------------------------------------
#   Route /datamanager/get
#----------------------------------------------------------------------------

@app.route('/datamanager/get', methods=['GET'])
def get():
    """ List DataManager available data.

    Trhough 'get', you can retrieve sets of past data stored in the database.
    To receive the latest data see '/datamanager/subscribe'

    Args:

    Returns:
      Available OHLCV symbols and timeframes.
    """

    # \todo List of available data, fetched and processed

    return jsonify({'valid_resources': ['trade_history']})



#----------------------------------------------------------------------------
#   Route /ordermanager/get/<command>
#----------------------------------------------------------------------------

@app.route('/ordermanager/get/', methods=['GET'])
def get_commands():
    """ Serve data collected by the OrderManager block.

    Args:

    Returns:
        Requested data.
    """
    get_resource = request.json['res']
    get_parameters = request.json['params']


    # Resource 'balance'
    if get_resource == 'balance':
        user = get_parameters['user']
        exchange = get_parameters['exchange']

        balance = user_exchanges[user][exchange].fetchBalance()

        return jsonify({'balance': balance})


    # Resource 'trade_history'
    elif get_resource == 'trade_history':
        user = get_parameters['user']
        exchange = get_parameters['exchange']

        trade_history = user_exchanges[user][exchange].fetchMyTrades(limit=1000)

        return jsonify({'trade_history': trade_history})
        

    else:
        return jsonify({'error': 'Resource not found.'})




#%%--------------------------------------------------------------------------
# PUBLIC METHODS
#----------------------------------------------------------------------------

class ordermanager_API (threading.Thread):
    def __init__(self, threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID

    def run(self):
        print('OrderManager API STARTED with threadID ' + self.name)
        app.run(host=ORDERMANAGER_API_IP, port=ORDERMANAGER_API_PORT, debug=False)
        print('OrderManager API STOPPED with threadID ' + self.name)


thread_ordermanager_API = ordermanager_API('thread_ordermanager_API')


def start_API():
    """ Start OrderManager API Server
    Starts in a separate subprocess.

    Args:

    Returns:
    """
    print("Starting OrderManager API Server.")
    thread_ordermanager_API.start()


#----------------------------------------------------------------------------
# Script mode
#----------------------------------------------------------------------------
if __name__ == '__main__':
    print("OrderManager in script mode.")
    start_API()
