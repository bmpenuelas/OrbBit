#!/usr/bin/python3

import sys
import time
import threading
import queue
import numpy as np
import socket
from   flask      import Flask, jsonify, abort, make_response, request
from   flask_cors import CORS
import asyncio
import ccxt.async as ccxt
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
# Flask app error funcs redefinition
#----------------------------------------------------------------------------

ordermanager_flask_app = Flask(__name__)
CORS(ordermanager_flask_app)

@ordermanager_flask_app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'URL not found'}), 404)

@ordermanager_flask_app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)



#----------------------------------------------------------------------------
# ROUTES AND METHODS
#----------------------------------------------------------------------------
#----------------------------------------------------------------------------
#   Route /ordermanager
#----------------------------------------------------------------------------

@ordermanager_flask_app.route('/ordermanager', methods=['POST'])
def ordermanager_status():
    """ Get ordermanager status.
    Args:

    Returns:
        Status of the OrderManager API and processes.
    """

    return jsonify({'status': 'aaaaa'})



#----------------------------------------------------------------------------
#   Route /ordermanager/get
#----------------------------------------------------------------------------

@ordermanager_flask_app.route('/ordermanager/get', methods=['POST'])
def get():
    """ List ordermanager available data.

    Trhough 'get', you can retrieve sets of past data stored in the database.
    To receive the latest data see '/ordermanager/subscribe'

    Args:

    Returns:
      Available OHLCV symbols and timeframes.
    """

    # \todo List of available data, fetched and processed

    return jsonify({'valid_resources': ['balance', 'balance_usd', 'trade_history', 'balance_norm_price_history', 'open_orders']})



#----------------------------------------------------------------------------
#   Route /ordermanager/get/<command>
#----------------------------------------------------------------------------

@ordermanager_flask_app.route('/ordermanager/get/', methods=['POST'])
def get_commands():
    """ Serve data collected by the OrderManager block.

    Args:

    Returns:
        trade_history (dict)
            symbol
            amount
            price

    Example:
        get_resource = 'trade_history'
        get_parameters = {'user': 'farolillo', 'exchange': 'hitbtc2'}

        get_resource = 'trade_history'
        get_parameters = {'user': 'linternita', 'exchange': 'bittrex'}

        get_resource = 'balance'
        get_parameters = {'user': 'linternita', 'exchange': 'bittrex'}

        get_resource = 'balance_usd'
        get_parameters = {'user': 'farolillo', 'exchange': 'hitbtc2'}

    
    """

    # print('RECEIVED REQ /ordermanager/get/')
    # print(request.json)

    get_resource = request.json['res']
    get_parameters = request.json['params']


    # Resource 'balance'
    if get_resource == 'balance':
        user        = get_parameters['user']
        exchange_id = get_parameters.get('exchange', None)

        if exchange_id:
            exchange_list = [ user_exchanges[user][exchange_id] ]
        else:
            exchange_list = [user_exchanges[user][exchange] for exchange in user_exchanges[user]]
            print(user_exchanges[user])


        total_balance = {}
        for exchange in exchange_list:
            balance = get_balance(exchange)
            for coin in balance:
                if coin in total_balance:
                    total_balance[coin] += balance[coin]
                else:
                    total_balance[coin] = balance[coin]

        return jsonify({'balance': balance})


    # Resource 'balance_usd'
    if get_resource == 'balance_usd':
        user          = get_parameters['user']
        exchange_id   = get_parameters['exchange']
        min_usd_value = get_parameters.get('min_usd_value', 0.0)

        balance_usd, total_usd, balance = get_balance_usd(user_exchanges[user][exchange_id], min_usd_value=min_usd_value)

        return jsonify({'balance_usd': balance_usd, 'total_usd': total_usd})


    # Resource 'trade_history'
    elif get_resource == 'trade_history':
        user        = get_parameters['user']
        exchange_id = get_parameters['exchange'] if 'exchange' in get_parameters else None
        symbol      = get_parameters['symbol']   if 'symbol'   in get_parameters else None

        if exchange_id:
            trade_history = get_trade_history(user_exchanges[user][exchange_id], symbol)
        else:
            for exchange_id in user_exchanges[user]:
                trade_history = get_trade_history(user_exchanges[user][exchange_id], symbol)

        return jsonify({'trade_history': trade_history})


    # Resource 'balance_norm_price_history'
    elif get_resource == 'balance_norm_price_history':
        user          = get_parameters['user']
        exchange_id   = get_parameters['exchange']
        timeframe     = get_parameters['timeframe']
        min_usd_value = get_parameters.get('min_usd_value', 0.0)

        balance_norm_price_history = get_balance_norm_price_history(user_exchanges[user][exchange_id], timeframe, min_usd_value)

        return jsonify({'balance_norm_price_history': balance_norm_price_history})       


    # Resource 'open_orders'
    elif get_resource == 'open_orders':
        user        = get_parameters['user']
        exchange_id = get_parameters['exchange']

        open_orders = get_open_orders(user_exchanges[user][exchange_id])

        return jsonify({'open_orders': open_orders})

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
        ordermanager_flask_app.run(host=ORDERMANAGER_API_IP, port=ORDERMANAGER_API_PORT, debug=False)
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
