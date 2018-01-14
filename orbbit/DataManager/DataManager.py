#!/usr/bin/python3

import sys
import os
from   pkg_resources  import resource_filename
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
#                              EXCHANGES SETUP                              #
#############################################################################

#\todo Check exchange.hasFetchOHLCV
exchange = ccxt.hitbtc2({'verbose': False})

def print_markets():
    markets = exchange.load_markets()
    print(exchange.id, markets)


def symbol_os(symbol):
    if os.name == 'nt':
        return symbol.replace('/USDT', '/USD')
    else:
        return symbol        

def fetch_ticker():
    return exchange.fetch_ticker(symbol_os('BTC/USDT'))



#%%##########################################################################
#                              DATABASE SETUP                               #
#############################################################################

def get_datamanager_info(info):
    """Get the 'info' field from the 'datamanager_info' collection at the db.

    It stores parameters that should be kept between runs of the program.

    Args:
        info (str): info field identifier.
            Valid identifiers:
                'fetching_symbols' dict key : PAIR
                                   dict val : list TIMEFRAME

    Returns:
        Structure stored under 'info'. Can be any data structure.

    Note:
        To delete all database contents use the following command. Use with caution!
        datamanager_db_connection.drop_database(datamanager_db_key['database'])
    """

    try:
        return datamanager_info.find( {info: {'$exists': True}} )[0][info]
    except IndexError:
        # if the database is empty, fetch these datasets by default
        datamanager_info.insert_one(
            {'fetching_symbols':
                {'BTC/USDT': ['1m', '3m', '5m', '15m', '30m', '1h', '4h'],
                 'ETH/USDT': ['1m', '3m', '5m', '15m', '30m', '1h', '4h'],
                 'ETC/USDT': ['1m', '3m', '5m', '15m', '30m', '1h', '4h'],
                }
            }
        )
        return datamanager_info.find( {info: {'$exists': True}} )[0][info]



datamanager_db_route = resource_filename('orbbit', 'DataManager/datamanager_db.key')

with open(datamanager_db_route) as f:
    datamanager_db_key = json.load(f)

datamanager_db_connection = pymongo.MongoClient(datamanager_db_key['url'], datamanager_db_key['port'])
datamanager_db = datamanager_db_connection[datamanager_db_key['database']]
datamanager_db.authenticate(datamanager_db_key['user'], datamanager_db_key['password'])

datamanager_info = datamanager_db['datamanager_info']
fetching_symbols = get_datamanager_info('fetching_symbols')



def get_db_ohlcv(symbol, timeframe, from_millis, to_millis):
    """Get 'ohlcv' documents from db.

    Args:
        symbol, timeframe, from_millis, to_millis
    Returns:
        pymongo cursor pointing to the docs
    """
    projection = {'date8061': True, 'ohlcv': True}

    symbol_db = symbol.replace('/', '_')
    collection = datamanager_db[symbol_db]

    query = {'ohlcv': {'$exists': True},
             'timeframe': timeframe,
             'date8061': {'$gt': from_millis, '$lt': to_millis}
            }

    return collection.find(query, projection).sort('date8061', pymongo.ASCENDING)




#%%##########################################################################
#                             GENERIC FUNCTIONS                             #
#############################################################################

def current_millis():
    return time.time() * 1000



def cursor_to_list(db_cursor):
    destination_list = []
    for doc in db_cursor:
        destination_list.append(doc)
    return destination_list



def timeframe_to_millis(timeframe):
    """ Convert from readable string to milliseconds.
    Args:

        timeframe (str): Valid values:
                             '*m' minutes
                             '*s' seconds
    Returns:
    """
    if   'M' in timeframe:
        return int(timeframe.replace('d', '')) * 30 * 24 * 60 * 60 * 1000
    elif 'w' in timeframe:
        return int(timeframe.replace('d', '')) * 7  * 24 * 60 * 60 * 1000
    elif 'd' in timeframe:
        return int(timeframe.replace('d', '')) * 24 * 60 * 60 * 1000
    elif 'h' in timeframe:
        return int(timeframe.replace('h', '')) * 60 * 60 * 1000
    elif 'm' in timeframe:
        return int(timeframe.replace('m', '')) * 60 * 1000
    elif 's' in timeframe:
        return int(timeframe.replace('s', '')) * 1000
    else:
        raise ValueError('Invalid representation.')



def candle_to_document(candle, timeframe):
    """ Convert exchange candles (ohlcv) to database documents.
    Args:
        candle: as output by ccxt ohlcv
        timeframe: see timeframe_to_millis for valid values
    Returns:
        document for MongoDB.
    """
    new_row = {}
    new_row['open']      = candle[1]
    new_row['high']      = candle[2]
    new_row['low']       = candle[3]
    new_row['close']     = candle[4]
    new_row['volume']    = candle[5]

    return {'_id': (timeframe + '_' + str(candle[0])),
            'timeframe': timeframe,
            'date8061': candle[0],
            'ohlcv': new_row,
           }



def res_params_to_stream_id(res, params):
    """
    Example:
    res = 'macd'
    params = {
              'symbol': 'BTC/USDT',
              'timeframe': '15m',
              'ema_fast': 12,
              'ema_slow': 5,
             }
    res_params_to_stream_id(res, params)
    """
    for valid_resources in valid_subscribtion_resources.values():
        for val in valid_resources:
            if val == res:
                param_values = [params[key] for key in sorted(params.keys())]
                stream_id = res
                for param_value in param_values:
                    stream_id += '_' + str(param_value)
                return stream_id
    return -1




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
    fetching_symbols = get_datamanager_info('fetching_symbols')
    for symbol in fetching_symbols:
        for timeframe in fetching_symbols[symbol]:
            params = {'symbol': symbol, 'timeframe': timeframe}
            new_fetch_thread_ohlcv = fetch_thread_ohlcv(params)
            new_fetch_thread_ohlcv.start()

    return jsonify({'fetching_symbols': get_datamanager_info('fetching_symbols')})



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

        self.stream_id = res_params_to_stream_id('ohlcv', params)
        self.symbol_db = self.params['symbol'].replace('/', '_')

        self.curr_time_8061 = current_millis()

        self.fetch_interval = int(timeframe_to_millis(self.params['timeframe'])*0.9)
        self.retry_on_xchng_err_interval = 1

        self.last_fetch = 0

    def run(self):
        # print('Started fetcher for ' + self.params['symbol'] +' '+ self.params['timeframe'])

        collection = datamanager_db[self.symbol_db]
        nxt_fetch = self.curr_time_8061

        filled = fill_ohlcv(self.params['symbol'], self.params['timeframe'], exchange.parse8601('2017-01-01 00:00:00'))
        if filled: print('Filled ' + str(filled) + ' missing entries in ' + self.params['symbol'] +' '+ self.params['timeframe'])

        while 1:
            fetch_from_API_success = 0
            while not(fetch_from_API_success):
                try:
                    # print('Exchange query for ' + self.params['symbol'] +' '+ self.params['timeframe'])
                    ohlcv = exchange.fetch_ohlcv(symbol_os(self.params['symbol']), self.params['timeframe'], nxt_fetch)
                    fetch_from_API_success = 1
                except:
                    print('Exchange query ERR for ' + self.params['symbol'] +' '+ self.params['timeframe'])
                    time.sleep(self.retry_on_xchng_err_interval)

            if ohlcv:
                for candle in ohlcv:
                    new_document = candle_to_document(candle, self.params['timeframe'])

                    # send to subscribers
                    new_data = {'date8061': new_document['date8061'], 'ohlcv': new_document['ohlcv']}
                    send_to_subscribers(self.stream_id, new_data)

                    # save in database
                    try:
                        collection.insert_one(new_document)
                    except pymongo.errors.DuplicateKeyError as e:
                        # print("Duplicate value, skipping.")
                        pass

                    if new_document['date8061'] > self.last_fetch:
                        self.last_fetch = new_document['date8061']

                nxt_fetch = self.last_fetch + self.fetch_interval
                time.sleep( self.fetch_interval / 1000 )



def fill_ohlcv(symbol, timeframe, from_millis=0):
    """ Attempt to fill gaps in the DataManager database by fetching many data at once.
        It is limited by how back in time the exchange API provides data.

    Example:
        symbol = 'ETC/USDT'
        timeframe = '15m'
        from_millis = exchange.parse8601('2017-01-24 00:00:00')
        fill_ohlcv(symbol, timeframe, from_millis)
    Args:
        symbol, timeframe, from_millis: See fetch_thread_ohlcv.
    Returns:
        filled: gaps successfully filled.
        missing: gaps that could not be filled.
    """

    symbol_db = symbol.replace('/', '_')
    collection = datamanager_db[symbol_db]

    retry_on_xchng_err_interval = 1

    filled = 0
    fetch_from_API_success = 0
    while not fetch_from_API_success:
        try:
            # print('Filling ' + symbol +' '+ timeframe)
            ohlcv = exchange.fetch_ohlcv(symbol_os(symbol), timeframe, since=from_millis, limit=1000)
            fetch_from_API_success = 1
        except:
            print('Exchange ERR. Could not load data to fill OHLCV ' + symbol +' '+ timeframe)
            time.sleep(retry_on_xchng_err_interval)

    new_documents = [candle_to_document(candle, timeframe) for candle in ohlcv]
    try:
        insertion_result = collection.insert_many(new_documents, ordered = False )
        filled = len(insertion_result.inserted_ids)
    except pymongo.errors.BulkWriteError as ex:
        filled = ex.details['nInserted']
    # \todo chech for holes in data
    return filled




#%%##########################################################################
#                              DATA TRANSFORM                               #
#############################################################################

class transform_thread_macd(threading.Thread):
    """ Calculate MACD.

    Difference between two EMA with different sample number.

    Args:
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

        self.symbol = parameters['symbol']
        self.timeframe = parameters['timeframe']
        self.ema_fast = parameters['ema_fast']
        self.ema_slow = parameters['ema_slow']

        self.stream_id = res_params_to_stream_id('macd', parameters)

        # subscribe to fetcher
        ohlcv_params = {'symbol': self.symbol, 'timeframe': self.timeframe}
        stream_id_ohlcv = res_params_to_stream_id('ohlcv', ohlcv_params)

        self.ohlcv_queue = new_subscriber_queue(stream_id_ohlcv)


    def run(self):
        # get enough previous values to calculate each EMA
        from_millis = current_millis() - (self.ema_slow + 3) * timeframe_to_millis(self.timeframe)
        to_millis = current_millis() + 10e3

        ohlcv_cursor = get_db_ohlcv(self.symbol, self.timeframe, from_millis, to_millis)
        ohlcv = cursor_to_list(ohlcv_cursor)

        if len(ohlcv) < self.ema_slow:
            raise ValueError('Data for MACD not available.')
        else:
            # EMA will be calculated with 'close' price
            close = [ row['ohlcv']['close'] for row in ohlcv]


        history_vals = close[-self.ema_slow :]

        macd_prev = EMA_tick(self.ema_fast, history_vals[-self.ema_fast :])  \
                    - EMA_tick(self.ema_slow, history_vals)


        while True:
            # new fetcher data
            new_ohlcv = self.ohlcv_queue.get()
            new_close = new_ohlcv['ohlcv']['close']
            new_date8061 = new_ohlcv['date8061']

            # calc EMA and MACD
            history_vals = history_vals[1 :]
            history_vals.append(new_close)

            ema_fast_val = EMA_tick(self.ema_fast, history_vals[-self.ema_fast :])
            ema_slow_val = EMA_tick(self.ema_slow, history_vals)

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
            # macd_dict = {'aaa': 123}

            macd_prev = macd
            self.ohlcv_queue.task_done()

            # send to subscribers
            send_to_subscribers(self.stream_id, macd_dict)




#%%##########################################################################
#                              DATAMANAGER API                              #
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
#   Route /datamanager
#----------------------------------------------------------------------------

@app.route('/datamanager', methods=['GET'])
def datamanager_status():
    """ Get datamanager status.
    Args:

    Returns:
        Status of the DataManager API and processes.
    """

    return jsonify({'fetching_symbols': get_datamanager_info('fetching_symbols')})



#----------------------------------------------------------------------------
#   Route /datamanager/fetch
#----------------------------------------------------------------------------

@app.route('/datamanager/fetch', methods=['GET'])
def fetch():
    return jsonify({'fetching_symbols': get_datamanager_info('fetching_symbols')})


#----------------------------------------------------------------------------
#   Route /datamanager/fetch/<command>
#----------------------------------------------------------------------------

@app.route('/datamanager/fetch/<string:command>', methods=['GET'])
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
        params = request.json['params']
        symbol = params['symbol']
        timeframe = params['timeframe']

        fetching_symbols = get_datamanager_info('fetching_symbols')

        if symbol in fetching_symbols:
            print(fetching_symbols[symbol])
            if timeframe not in fetching_symbols[symbol]:
                fetching_symbols[symbol].append(timeframe)
                datamanager_info.update_one({'fetching_symbols': {'$exists': True}},
                                            {"$set": {'fetching_symbols': fetching_symbols, }},
                                            upsert=True
                                           )
                new_symbol_fetcher = fetch_thread_ohlcv(params)
                new_symbol_fetcher.start()
        else:
            fetching_symbols[symbol] = [timeframe]
            datamanager_info.update_one({'fetching_symbols': {'$exists': True}},
                                        {"$set": {'fetching_symbols': fetching_symbols, } },
                                        upsert=True
                                       )
            new_symbol_fetcher = fetch_thread_ohlcv(params)
            new_symbol_fetcher.start()

        return jsonify({'fetching_symbols': fetching_symbols})

    else:
        return jsonify({'error': 'Invalid command.'})




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

    return jsonify({'fetching_symbols': get_datamanager_info('fetching_symbols')})


#----------------------------------------------------------------------------
#   Route /datamanager/get/<command>
#----------------------------------------------------------------------------

@app.route('/datamanager/get/', methods=['GET'])
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


        ohlcv_cursor = get_db_ohlcv(symbol, timeframe, from_millis, to_millis)

        ohlcv = cursor_to_list(ohlcv_cursor)

        if ohlcv == []:
            return jsonify({'error': 'Data not available.'})
        else:
            return jsonify(ohlcv)


    elif get_resource == 'ema':
        symbol      = get_parameters['symbol']
        timeframe   = get_parameters['timeframe']
        ema_samples   = get_parameters['ema_samples']

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


        ohlcv_cursor = get_db_ohlcv(symbol, timeframe, from_millis, to_millis)

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

@app.route('/datamanager/subscribe', methods=['GET'])
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


# Types that are implemented
valid_subscribtion_resources = {'fetched': ['ohlcv',],
                                'transformed': ['macd',],
                               }



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


@app.route('/datamanager/subscribe/<string:command>', methods=['GET'])
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
#   Route /ticker
#----------------------------------------------------------------------------

@app.route('/ticker', methods=['GET'])
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
        app.run(host=DATAMANAGER_API_IP, port=DATAMANAGER_API_PORT, debug=False)
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
