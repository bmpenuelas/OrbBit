#!/usr/bin/python3

import sys
import os
import math
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
from   orbbit.DataManager.data_transform.data_transform import *


#%%##########################################################################
#                               CONFIGURATION                               #
#############################################################################

#%%--------------------------------------------------------------------------
# NETWORK
#----------------------------------------------------------------------------

serverName = socket.gethostname()
print('ORBBIT DataManager Server Name:' + serverName)

# ORBBIT_HOST = socket.gethostbyname( 'localhost' )
ORBBIT_HOST = socket.gethostbyname(serverName)
print('ORBBIT DataManager on IP ' + ORBBIT_HOST)


# API
DATAMANAGER_API_IP = '0.0.0.0'
DATAMANAGER_API_PORT = 5000

# Subscriptions
SUBS_PORT_BASE = 5100
SUBS_PORT_LIMIT = 6000




#%%##########################################################################
#                              DATABASE SETUP                               #
#############################################################################

fetching_symbols = get_database_info('datamanager', 'fetching_symbols')




#%%##########################################################################
#                              EXCHANGES SETUP                              #
#############################################################################

fetch_exchanges = get_database_info('datamanager', 'fetch_exchanges')

exchanges = {new_exchange: exchange_id_to_exchange(new_exchange) for new_exchange in fetch_exchanges}




#############################################################################
#                             DATAMANAGER TASKS                             #
#############################################################################

#%%##########################################################################
#                                DATA FETCH                                 #
#############################################################################

def start_fetch():
    """ Start all the fetchers which are registered in the database.

    Args:

    Returns:
      List of symbols that are being fetched.

    """

    fetching_symbols = get_database_info('datamanager', 'fetching_symbols')
    for exchange_id in fetching_symbols:
        for symbol in fetching_symbols[exchange_id]:
            for timeframe in fetching_symbols[exchange_id][symbol]:
                params = {'symbol': symbol, 'exchange': exchange_id, 'timeframe': timeframe}
                new_fetch_thread_ohlcv = fetch_thread_ohlcv(params)
                new_fetch_thread_ohlcv.start()

    return jsonify({'fetching_symbols': get_database_info('datamanager', 'fetching_symbols')})



class fetch_thread_ohlcv(threading.Thread):
    """ Thread that fetches data for a given symbol/timeframe.

    On start, it will try to fill missing data points.

    Args:
        params (dict)
            symbol (str)
            timeframe (str)

    """

    def __init__(self, params):
        threading.Thread.__init__(self)
        self.params = params


        self.exchange_id = params['exchange']
        self.exchange = exchanges[self.exchange_id]

        self.stream_id = res_params_to_stream_id('ohlcv', params)
        self.symbol_db = self.params['symbol'].replace('/', '_')

        self.fetch_interval = int(timeframe_to_millis(self.params['timeframe'])*0.9)
        self.retry_on_xchng_err_interval = 1

        self.last_fetch = 0

        collection_name = self.exchange_id + '_' + self.symbol_db
        self.collection = datamanager_db[collection_name]


    def run(self):
        # print('Started fetcher for ' + self.params['symbol'] + ' ' + self.params['timeframe'])

        # first, try to fill missing data
        now = current_millis()
        nxt_fetch = now - (now % timeframe_to_millis(self.params['timeframe']))

        data_limit = min([1000, self.exchange.rateLimit]) - 1
        fill_from = int(now - timeframe_to_millis(self.params['timeframe']) * data_limit)

        filled = fill_ohlcv(self.params['symbol'], self.params['exchange'], self.params['timeframe'], fill_from)
        if filled: print('Filled ' + str(filled) + ' missing entries in ' + self.params['symbol'] +' @ '+ self.params['exchange'] +' '+ self.params['timeframe'])


        # keep asking for candles
        while 1:
            fetch_from_API_success = 0
            while not(fetch_from_API_success):
                try:
                    # print('Exchange query for ' + self.params['symbol'] +' '+ self.params['timeframe'])
                    ohlcv = self.exchange.fetch_ohlcv(symbol_os(self.params['symbol'], self.exchange_id), self.params['timeframe'], int(nxt_fetch))
                    fetch_from_API_success = 1
                except:
                    print('ERR ' + self.exchange_id + ' query for ' + self.params['symbol'] +' '+ self.params['timeframe'])
                    time.sleep(self.retry_on_xchng_err_interval)

            if ohlcv:
                for candle in ohlcv:
                    new_document = candle_to_document(candle, self.params['timeframe'])

                    # send to subscribers
                    new_data = {'date8061': new_document['date8061'], 'ohlcv': new_document['ohlcv']}
                    send_to_subscribers(self.stream_id, new_data)

                    # save in database
                    try:
                        self.collection.insert_one(new_document)
                    except pymongo.errors.DuplicateKeyError as e:
                        # print("Duplicate value, skipping.")
                        pass

                    if new_document['date8061'] > self.last_fetch:
                        self.last_fetch = new_document['date8061']

                nxt_fetch = self.last_fetch + timeframe_to_millis(self.params['timeframe'])
                time.sleep( self.fetch_interval / 1000 )



def fill_ohlcv(symbol, exchange_id, timeframe, from_millis=0):
    """ Attempt to fill gaps in the DataManager database by fetching many data at once.
        It is limited by how back in time the exchange API provides data.

    Args:
        symbol, timeframe, from_millis: See fetch_thread_ohlcv.

    Returns:
        filled: gaps successfully filled.
        missing: gaps that could not be filled.

    Example:
        symbol = 'BTC/USDT'
        exchange_id = 'binance'
        timeframe = '1m'
        from_millis = current_millis() - timeframe_to_millis(timeframe) * 1000
        fill_ohlcv(symbol, exchange_id, timeframe, from_millis)

    """

    retry_on_xchng_err_interval = 1

    exchange = exchanges[exchange_id]
    data_limit = min([1000, exchange.rateLimit]) - 1

    symbol_db = symbol.replace('/', '_')
    collection_name = exchange_id + '_' + symbol_db
    collection = datamanager_db[collection_name]


    # calculate number of requests needed
    fill_parts = math.ceil(((current_millis() - from_millis) / timeframe_to_millis(timeframe)) / data_limit)

    from_parts = [from_millis + i * data_limit for i in range(fill_parts)]

    filled = 0

    for from_part in from_parts:
        fetch_from_API_success = 0
        while not fetch_from_API_success:
            try:
                # print('Filling ' + symbol + ' ' + timeframe + ' from ' + str(from_part))
                ohlcv = exchange.fetch_ohlcv(symbol_os(symbol, exchange_id), timeframe, since=from_part, limit=data_limit)
                fetch_from_API_success = 1
            except:
                print('ERR Exchange - Fill OHLCV ' + symbol + ' @ ' + exchange_id + ' ' + timeframe + ' from ' + str(from_part) + ' n ' + str(data_limit))
                time.sleep(retry_on_xchng_err_interval)

        new_documents = [candle_to_document(candle, timeframe) for candle in ohlcv]

        inserted = 0
        while not inserted:
          try:
              insertion_result = collection.insert_many(new_documents, ordered = False )
              filled += len(insertion_result.inserted_ids)
              inserted = 1
          except pymongo.errors.BulkWriteError as ex:
              filled += ex.details['nInserted']
          except pymongo.errors.AutoReconnect as ex:
              pass

    # \todo chech for holes in data
    return filled




#%%##########################################################################
#                              DATA TRANSFORM                               #
#############################################################################

class transform_thread_macd(threading.Thread):
    """ Calculate MACD.

    Difference between two EMA with different sample number.

    Args:
        exchange_id (str)
        symbol (str)
        timeframe (str)
        ema_fast (int)
        ema_slow (int)
    Returns:
        macd (double)
        ema_fast (double)
        ema_slow (double)
        cross (1 / 0)
        rising (1 / 0)

    """

    def __init__(self, stream_parameters):
        threading.Thread.__init__(self)
        parameters = stream_parameters

        self.symbol      = parameters['symbol']
        self.exchange_id = parameters['exchange']
        self.timeframe   = parameters['timeframe']
        self.ema_fast    = parameters['ema_fast']
        self.ema_slow    = parameters['ema_slow']

        self.stream_id = res_params_to_stream_id('macd', parameters)

        # subscribe to fetcher
        ohlcv_params = {'symbol': self.symbol, 'exchange': self.exchange_id, 'timeframe': self.timeframe}
        stream_id_ohlcv = res_params_to_stream_id('ohlcv', ohlcv_params)

        self.ohlcv_queue = new_subscriber_queue(stream_id_ohlcv)


    def run(self):
        # get enough previous values to calculate each EMA
        from_millis = current_millis() - (self.ema_slow + 6) * timeframe_to_millis(self.timeframe)
        to_millis = current_millis() + 10e3

        ohlcv_cursor = get_db_ohlcv(self.symbol, self.exchange_id, self.timeframe, int(from_millis), int(to_millis))
        ohlcv = cursor_to_list(ohlcv_cursor)


        if len(ohlcv) < self.ema_slow:
            raise ValueError('Data for MACD not available.')
        else:
            # EMA will be calculated with 'close' price
            close = [ row['ohlcv']['close'] for row in ohlcv]


        history_vals = close[-self.ema_slow :]
        ema_fast_val = EMA_history(self.ema_fast, history_vals[-self.ema_fast :])[-1]
        ema_slow_val = EMA_history(self.ema_slow, history_vals)[-1]

        macd_prev = ema_fast_val - ema_slow_val


        while True:
            # new fetcher data
            new_ohlcv = self.ohlcv_queue.get()
            new_close = new_ohlcv['ohlcv']['close']
            new_date8061 = new_ohlcv['date8061']

            # calc EMA and MACD
            ema_fast_val_previous = ema_fast_val
            ema_slow_val_previous = ema_slow_val

            ema_fast_val = EMA_tick(self.ema_fast, new_close, ema_fast_val_previous)
            ema_slow_val = EMA_tick(self.ema_slow, new_close, ema_slow_val_previous)

            macd = ema_fast_val - ema_slow_val

            if (macd_prev > 0) != (macd > 0):
                cross = 1
            else:
                cross = 0

            rising = 1 if (macd > 0) else 0


            macd_dict = {
                         'date8061': new_date8061,
                         'macd':     {
                                      'macd': macd,
                                      'ema_fast': ema_fast_val,
                                      'ema_slow': ema_slow_val,
                                      'cross': cross,
                                      'rising': rising,
                                     },
                         'ohlcv':    new_ohlcv['ohlcv']
                        }

            macd_prev = macd
            self.ohlcv_queue.task_done()

            # send to subscribers
            send_to_subscribers(self.stream_id, macd_dict)




#%%##########################################################################
#                              DATAMANAGER API                              #
#############################################################################

#----------------------------------------------------------------------------
# Flask app error funcs redefinition
#----------------------------------------------------------------------------

datamanager_flask_app = Flask(__name__)

@datamanager_flask_app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)

@datamanager_flask_app.errorhandler(400)
def bad_request(error):
    return make_response(jsonify({'error': 'Bad request'}), 400)



#----------------------------------------------------------------------------
# ROUTES AND METHODS
#----------------------------------------------------------------------------
#----------------------------------------------------------------------------
#   Route /datamanager
#----------------------------------------------------------------------------

@datamanager_flask_app.route('/datamanager', methods=['POST'])
def datamanager_status():
    """ Get datamanager status.
    Args:

    Returns:
        Status of the DataManager API and processes.

    """

    return jsonify({'fetching_symbols': get_database_info('datamanager', 'fetching_symbols')})



#----------------------------------------------------------------------------
#   Route /datamanager/fetch
#----------------------------------------------------------------------------

@datamanager_flask_app.route('/datamanager/fetch', methods=['POST'])
def fetch():
    return jsonify({'fetching_symbols': get_database_info('datamanager', 'fetching_symbols')})


#----------------------------------------------------------------------------
#   Route /datamanager/fetch/<command>
#----------------------------------------------------------------------------

@datamanager_flask_app.route('/datamanager/fetch/<string:command>', methods=['POST'])
def fetch_commands(command):
    """ Fetcher commands.

    Args:
        start: starts one fetcher per symbol and timeframe as set in fetching_symbols.

        add: add new symbol/timeframe fetcher and start it.

    Returns:
        Symbols/timeframes being fetched.

    """

    # Command <start>
    if command == 'start':
        return start_fetch()


    # Command <add>
    elif command == 'add':
        params      = request.json['params']

        exchange_id = params['exchange']
        symbol      = params['symbol']
        timeframe   = params['timeframe']

        fetching_symbols, is_new = add_fetching_symbol(exchange_id, symbol, timeframe)

        if is_new:
            new_symbol_fetcher = fetch_thread_ohlcv(params)
            new_symbol_fetcher.start()


        return jsonify({'fetching_symbols': fetching_symbols})



    else:
        return jsonify({'error': 'Invalid command.'})




#----------------------------------------------------------------------------
#   Route /datamanager/get
#----------------------------------------------------------------------------

@datamanager_flask_app.route('/datamanager/get', methods=['POST'])
def get():
    """ List DataManager available data.

    Trhough 'get', you can retrieve sets of past data stored in the database.
    To receive the latest data see '/datamanager/subscribe'

    Args:

    Returns:
      Available OHLCV symbols and timeframes.

    """

    # \todo List of available data, fetched and processed

    return jsonify({'valid_resources': ['ohlcv', 'ema']})


#----------------------------------------------------------------------------
#   Route /datamanager/get/<command>
#----------------------------------------------------------------------------

@datamanager_flask_app.route('/datamanager/get/', methods=['POST'])
def get_commands():
    """ Serve data collected by the DataManager block.

    Args:

    Returns:
        Requested data.

    """
    get_resource = request.json['res']
    get_parameters = request.json['params']


    # Resource 'ohlcv'
    if get_resource == 'ohlcv':
        exchange_id = get_parameters['exchange']
        symbol      = get_parameters['symbol']
        timeframe   = get_parameters['timeframe']

        if 'from' in get_parameters:
            from_millis = get_parameters['from']
            from_millis -= (from_millis % timeframe_to_millis(timeframe))
        else:
            from_millis = 0

        if 'to' in get_parameters:
            to_millis = get_parameters['to']
            to_millis -= (to_millis % timeframe_to_millis(timeframe))
        else:
            to_millis = current_millis() + 10e3


        ohlcv_cursor = get_db_ohlcv(symbol, exchange_id, timeframe, from_millis, to_millis)

        ohlcv = cursor_to_list(ohlcv_cursor)

        if ohlcv == []:
            return jsonify({'error': 'Data not available.'})
        else:
            return jsonify(ohlcv)


    elif get_resource == 'ema':
        exchange_id = get_parameters['exchange']
        symbol      = get_parameters['symbol']
        timeframe   = get_parameters['timeframe']
        ema_samples = get_parameters['ema_samples']

        if 'from' in get_parameters:
            from_millis = get_parameters['from']
            from_millis -= (from_millis % timeframe_to_millis(timeframe))
        else:
            from_millis = 0

        if 'to' in get_parameters:
            to_millis = get_parameters['to']
            to_millis -= (to_millis % timeframe_to_millis(timeframe))
        else:
            to_millis = current_millis() + 10e3


        ohlcv_cursor = get_db_ohlcv(symbol, exchange_id, timeframe, from_millis, to_millis)

        ohlcv = cursor_to_list(ohlcv_cursor)

        if ohlcv == []:
            return jsonify({'error': 'Data not available.'})
        else:
            # EMA will be calculated with 'close' price
            date8061 = [ row['date8061'] for row in ohlcv]
            close = [ row['ohlcv']['close'] for row in ohlcv]
            ema = EMA_history(ema_samples, close)

            ema_dict = [{'date8061': date8061[i], 'ema': ema[i]} for i in range(len(ema))]

            return jsonify(ema_dict)


    else:
        return jsonify({'error': 'Resource not found.'})




#----------------------------------------------------------------------------
#   Route /datamanager/subscribe
#----------------------------------------------------------------------------

@datamanager_flask_app.route('/datamanager/subscribe', methods=['POST'])
def subscribe():
    """ List data streams you can subscribe to.

    When you subscribe, you will be given an IP, PORT tuple where you can
    listen for the updated data.

    Args:

    Returns:
        valid_subscribtion_resources (str list)
        active_subscription_services (str list)

    """

    return jsonify({'valid_subscribtion_resources': valid_subscribtion_resources,
                    'active_subscription_services': active_subscription_services,
                   })



#----------------------------------------------------------------------------
#   Route /datamanager/subscribe/<command>
#----------------------------------------------------------------------------

SUBS_CLIENTS_WAITING_MAX = 10

active_subscription_services = {} #dict {'stream_id_a': (HOST, PORT), 'stream_id_b': [(...

transform_data_threads = []
subscription_threads = {} # dict {'stream_id_a': thread, ... }
subscriber_queues = {} # dict {'stream_id_a': [list of queues], ... }
subscribers = [] # list of threads

def send_to_subscribers(stream_id, data):
    """ Sends new data to all subscribed processes.

    Note: When instantiating a new subscriber, a new queue must be added to the
    'subscriber_queues' list and passed to the subscriber thread.

    Args:
        stream_id (str) unique stream identifier
        data (dict) json-like structure containing the new data

    Returns:

    """

    if stream_id in subscriber_queues:
        for subs_queue in subscriber_queues[stream_id]:
            subs_queue.put( data )



@datamanager_flask_app.route('/datamanager/subscribe/<string:command>', methods=['POST'])
def subscribe_commands(command):
    """ Manage subscriptions to live data.

    Once a request is received, it returns the IP, PORT tuple where the
    server is serving new data for the desired stream.

    Args:

    Returns:
        IP (str)
        port (int)

    """

    # Command <add>
    if command == 'add':
        stream_resource = request.json['res']
        stream_parameters = request.json['params']

        stream_id   = res_params_to_stream_id(stream_resource, stream_parameters)
        if stream_id == -1:
            return jsonify({'error': 'Invalid stream_resource.'})

        if stream_id in active_subscription_services:
            return jsonify({stream_id: active_subscription_services[stream_id]})
        else:
            port = SUBS_PORT_BASE

            available = 0
            while available == 0:
                available = 1
                for used_type, used_tuple in active_subscription_services.items():
                    if port == used_tuple[1]:
                        available = 0
                        port += 1
                        break

            active_subscription_services[stream_id] = (ORBBIT_HOST, port)

            subscription_threads[stream_id] = subscription_thread(stream_resource, stream_parameters, ORBBIT_HOST, port)
            subscription_threads[stream_id].start()

            return jsonify({stream_id: (ORBBIT_HOST, port)})

    else:
        return jsonify({'error': 'Command not found.'})



class subscription_thread(threading.Thread):
    """ Subscription socket server.

    One server is created per stream_id, to serve all clients subscribed to it (subscribers).

    Args:

    Returns:

    """
    def __init__(self, stream_resource, stream_parameters, host, port):
        threading.Thread.__init__(self)
        self.stream_resource = stream_resource
        self.stream_parameters = stream_parameters
        self.host = host
        self.port = port

        self.stream_id = res_params_to_stream_id(self.stream_resource, self.stream_parameters)

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind( (self.host, self.port) )
        except socket.error as msg:
            return jsonify({'error': 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]})

        # Accept new subscribers for this stream_id
        s.listen(SUBS_CLIENTS_WAITING_MAX)

        while True:
            conn, addr = s.accept()
            print('Subscribtion ' + self.stream_id + ' requested by ' + addr[0] + ':' + str(addr[1]))

            new_subs_q = new_subscriber_queue(self.stream_id)
            new_subscriber_thread(new_subs_q, conn)

            if self.stream_resource in valid_subscribtion_resources['fetched']:
                # fetchers update the queue when they get new data
                pass
            elif self.stream_resource in valid_subscribtion_resources['transformed']:
                # start the data transformation thread, it will subscribe to one or more fetchers
                # and update the transformed data queue.
                if self.stream_resource == 'macd':
                    new_transform_thread( transform_thread_macd(self.stream_parameters) )

            else:
                return jsonify({'error': 'Stream resource not valid.'})




def new_subscriber_queue(stream_id):
    """ Return a new queue where new 'stream_id' data can be fed and retrieved.
    """
    new_queue = queue.Queue()

    if stream_id in subscriber_queues:
        subscriber_queues[stream_id].append(new_queue)
    else:
        subscriber_queues[stream_id] = [new_queue]

    return new_queue


def new_subscriber_thread(new_queue, conn):
    """ Create thread that sends new data in the queue through the conn.
    """
    subscribers.append( subscriber_thread(new_queue, conn) )
    subscribers[-1].start()


def new_transform_thread(new_trhead):
    """ Create thread that sends new data in the queue through the conn.
    """
    transform_data_threads.append( new_trhead )
    transform_data_threads[-1].start()


class subscriber_thread(threading.Thread):
    """ Subscriber socket server.

    One is created per subscriber to send them new data as soon as it is made
    available trough it's queue.

    Args:

    Returns:

    """

    def __init__(self, queue, conn):
        threading.Thread.__init__(self)
        self.queue = queue
        self.conn = conn

    def run(self):
        print('New subscriber thread.')
        while True:
            new_data = self.queue.get()
            self.conn.sendall( json.dumps(new_data).encode('ascii') )
            self.queue.task_done()




#----------------------------------------------------------------------------
#   Route /...
#----------------------------------------------------------------------------

@datamanager_flask_app.route('/ticker', methods=['POST'])
def get_ticker():
    """ Get BTC/USDT ticker info.

    Args:

    Returns:
      Json-formatted data.

    """

    return jsonify({'ticker': fetch_ticker()})




#%%--------------------------------------------------------------------------
# PUBLIC METHODS
#----------------------------------------------------------------------------

class DataManager_API (threading.Thread):
    def __init__(self, threadID):
        threading.Thread.__init__(self)
        self.threadID = threadID

    def run(self):
        print('DataManager_API STARTED with threadID ' + self.name)
        datamanager_flask_app.run(host=DATAMANAGER_API_IP, port=DATAMANAGER_API_PORT, debug=False)
        print('DataManager_API STOPPED with threadID ' + self.name)


thread_DataManager_API = DataManager_API('thread_DataManager_API')


def start_API():
    """ Start DataManager API Server
    Starts in a separate subprocess.

    Args:

    Returns:

    """

    print("Starting DataManager API Server.")
    thread_DataManager_API.start()


#----------------------------------------------------------------------------
# Script mode
#----------------------------------------------------------------------------
if __name__ == '__main__':
    print("DataManager in script mode.")
    start_API()
