#!/usr/bin/python3

import sys
import time
import threading
import queue
import numpy as np
import socket
from   flask          import Flask, jsonify, abort, make_response, request
from   flask_httpauth import HTTPBasicAuth
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
    return make_response(jsonify({'error': 'URL not found'}), 404)

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

@app.route('/ordermanager', methods=['POST'])
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

@app.route('/ordermanager/get', methods=['POST'])
def get():
    """ List ordermanager available data.

    Trhough 'get', you can retrieve sets of past data stored in the database.
    To receive the latest data see '/ordermanager/subscribe'

    Args:

    Returns:
      Available OHLCV symbols and timeframes.
    """

    # \todo List of available data, fetched and processed

    # print('RECEIVED REQ /ordermanager/get')
    # print(request.json)

    return jsonify({'balance': {'STRAT': 4.57623799, 'BTC': 4e-08, 'QTUM': 2.0, 'OMG': 9.05145261, 'EMC2': 104.84758895, 'WAVES': 10.48232595, 'PTOY': 151.82511483, 'ETH': 0.03701968, 'USDT': 0.00286782}})



#----------------------------------------------------------------------------
#   Route /ordermanager/get/<command>
#----------------------------------------------------------------------------

@app.route('/ordermanager/get/', methods=['POST'])
def get_commands():
    """ Serve data collected by the OrderManager block.

    Args:

    Returns:
        trade_history (dict)
            symbol
            amount
            price

    Note:
        hitbtc exchange needs to merge fetchClosedOrders() with fetchMyTrades().
        bittrex exchange needs to merge fetchOrders() + fetchOpenOrders().
        binance won't allow to fetch them all at once, you have to iterate over your symbols.

    Example:
        get_resource = 'trade_history'
        get_parameters = {'user': 'farolillo', 'exchange': 'hitbtc'}

        get_resource = 'trade_history'
        get_parameters = {'user': 'linternita', 'exchange': 'bittrex'}

        get_resource = 'balance'
        get_parameters = {'user': 'linternita', 'exchange': 'bittrex'}

        get_resource = 'balance_usd'
        get_parameters = {'user': 'farolillo', 'exchange': 'hitbtc'}

    """
    # print('RECEIVED REQ /ordermanager/get/')
    # print(request.json)

    get_resource = request.json['res']
    get_parameters = request.json['params']


    # Resource 'balance'
    if get_resource == 'balance':
        user = get_parameters['user']
        exchange_id = get_parameters['exchange']

        exchange = user_exchanges[user][exchange_id]

        balance = get_balance(exchange)

        return jsonify({'balance': balance})


    # Resource 'balance_usd'
    if get_resource == 'balance_usd':
        user = get_parameters['user']
        exchange_id = get_parameters['exchange']

        exchange = user_exchanges[user][exchange_id]

        balance = get_balance(exchange)

        balance_usd = [{coin: get_current_price_usd(coin, exchange) * balance[coin]} for coin in balance]
        total_usd = sum([list(coin_balance.values())[0] for coin_balance in balance_usd])

        return jsonify({'balance_usd': balance_usd, 'total_usd': total_usd})


    # Resource 'trade_history'
    elif get_resource == 'trade_history':
        user = get_parameters['user']
        exchange_id = get_parameters['exchange']

        trade_history = []

        if exchange_id == 'hitbtc':
            api_my_trades = user_exchanges[user][exchange_id].fetchMyTrades(limit=1000)
            trade_history = api_my_trades

        elif exchange_id == 'hitbtc':
            api_orders = user_exchanges[user][exchange_id].fetchOrders(limit=1000)
            trade_history = api_orders

        else:
            return jsonify({'error': 'Trade history not available for this exchange.'})

        return jsonify({'trade_history': trade_history})


    # Resource 'open_orders'
    elif get_resource == 'open_orders':
        user = get_parameters['user']
        exchange_id = get_parameters['exchange']

        open_orders = []

        if exchange_id == 'hitbtc':
            api_closed_orders = user_exchanges[user][exchange_id].fetchClosedOrders(limit=1000)
            open_orders = [order for order in api_closed_orders if order['status'] == 'open']

        elif exchange_id == 'hitbtc':
            api_open_orders = user_exchanges[user][exchange_id].fetchOpenOrders(limit=1000)
            open_orders = api_open_orders
            # create one and cancel, see what happens

        else:
            return jsonify({'error': 'Open orders not available for this exchange.'})

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
