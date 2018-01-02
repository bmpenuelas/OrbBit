import sys
import time
import threading

import numpy as np

import socket

from   flask import Flask, jsonify, abort, make_response, request
from   flask_httpauth import HTTPBasicAuth

import ccxt

import pymongo
import json



#%%--------------------------------------------------------------------------
# EXCHANGES SETUP
#----------------------------------------------------------------------------

#\todo Check exchange.hasFetchOHLCV
exchange = ccxt.hitbtc2({'verbose': False})

def print_markets():
    markets = exchange.load_markets()
    print(exchange.id, markets)


def fetch_ticker():
    return exchange.fetch_ticker('BTC/USD')


#%%--------------------------------------------------------------------------
# DATABASE SETUP
#----------------------------------------------------------------------------

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
                {'BTC/USD': ['1m', '3m', '5m', '15m', '30m', '1h', '4h'],
                 'ETH/USD': ['1m', '3m', '5m', '15m', '30m', '1h', '4h'],
                 'ETC/USD': ['1m', '3m', '5m', '15m', '30m', '1h', '4h'],
                }
            }
        )
        return datamanager_info.find( {info: {'$exists': True}} )[0][info]



from pkg_resources import resource_filename
datamanager_db_route = resource_filename('orbbit', 'DataManager/datamanager_db.key')

with open(datamanager_db_route) as f:
    datamanager_db_key = json.load(f)

datamanager_db_connection = pymongo.MongoClient(datamanager_db_key['url'], datamanager_db_key['port'])
datamanager_db = datamanager_db_connection[datamanager_db_key['database']]
datamanager_db.authenticate(datamanager_db_key['user'], datamanager_db_key['password'])

datamanager_info = datamanager_db['datamanager_info']
fetching_symbols = get_datamanager_info('fetching_symbols')



#%%--------------------------------------------------------------------------
# Generic functions
#----------------------------------------------------------------------------

def current_millis():
    return time.time() * 1000


def timeframe_to_ms(timeframe):
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
        timeframe: see timeframe_to_ms for valid values
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



#%%##########################################################################
#                        DATAMANAGER TASKS                                  #
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
            thread_save_ohlcv = save_ohlcv(symbol, timeframe)
            thread_save_ohlcv.start()

    return jsonify({'fetching_symbols': get_datamanager_info('fetching_symbols')})



class save_ohlcv(threading.Thread):
    """ Thread that fetches data for a given symbol/timeframe.

    On start, it will try to fill missing data points.

    Args:
        symbol (str)
        timeframe (str)
    """
    def __init__(self, symbol, timeframe):
        threading.Thread.__init__(self)
        self.symbol = symbol
        self.symbol_db = symbol.replace('/', '_')
        self.timeframe = timeframe

        self.curr_time_8061 = current_millis()

        self.fetch_interval = int(timeframe_to_ms(self.timeframe)*0.9)
        self.retry_on_xchng_err_interval = 1

        self.last_fetch = 0

    def run(self):
        print('Started fetcher for ' + self.symbol +' '+ self.timeframe)

        collection = datamanager_db[self.symbol_db]
        nxt_fetch = self.curr_time_8061

        filled = fill_ohlcv(self.symbol, self.timeframe, exchange.parse8601('2017-01-01 00:00:00'))
        if filled: print('Filled ' + str(filled) + ' missing entries in ' + self.symbol +' '+ self.timeframe)

        while 1:
            fetch_from_API_success = 0
            while not(fetch_from_API_success):
                try:
                    # print('Exchange query for ' + self.symbol +' '+ self.timeframe)
                    ohlcv = exchange.fetch_ohlcv(self.symbol, self.timeframe, nxt_fetch)
                    fetch_from_API_success = 1
                except:
                    print('Exchange query ERR for ' + self.symbol +' '+ self.timeframe)
                    time.sleep(self.retry_on_xchng_err_interval)

            if ohlcv:
                for candle in ohlcv:
                    new_document = candle_to_document(candle, self.timeframe)

                    # print("Fetched OHLCV " + self.symbol + new_document['_id'])

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
        symbol = 'ETC/USD'
        timeframe = '15m'
        from_millis = exchange.parse8601('2017-01-24 00:00:00')
        fill_ohlcv(symbol, timeframe, from_millis)
    Args:
        symbol, timeframe, from_millis: See save_ohlcv.
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
            print('Filling ' + symbol +' '+ timeframe)
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, since=from_millis, limit=1000)
            fetch_from_API_success = 1
        except:
            print('Exchange ERR. Could not load data to fill OHLCV ' + symbol +' '+ timeframe)
            time.sleep(retry_on_xchng_err_interval)

    new_documents = [candle_to_document(candle, timeframe) for candle in ohlcv]
    try:
        insertion_result = collection.insert_many(new_documents, ordered = False )
        filled = len(insertion_result.inserted_ids)
    except pymongo.errors.BulkWriteError as ex:
        print('Nothing to fill ' + symbol +' '+ timeframe)
        filled = ex.details['nInserted']
    # \todo chech for holes in data
    return filled




#%%##########################################################################
#                          DATAMANAGER API                                  #
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
        symbol = request.json['symbol']
        timeframe = request.json['timeframe']

        fetching_symbols = get_datamanager_info('fetching_symbols')

        if symbol in fetching_symbols:
            print(fetching_symbols[symbol])
            if timeframe not in fetching_symbols[symbol]:
                fetching_symbols[symbol].append(timeframe)
                datamanager_info.update_one({'fetching_symbols': {'$exists': True}},
                                            {"$set": {'fetching_symbols': fetching_symbols, }},
                                            upsert=True
                                           )
                new_symbol_fetcher = save_ohlcv(symbol, timeframe)
                new_symbol_fetcher.start()
        else:
            fetching_symbols[symbol] = [timeframe]
            datamanager_info.update_one({'fetching_symbols': {'$exists': True}},
                                        {"$set": {'fetching_symbols': fetching_symbols, } },
                                        upsert=True
                                       )
            new_symbol_fetcher = save_ohlcv(symbol, timeframe)
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

@app.route('/datamanager/get/<string:command>', methods=['GET'])
def get_commands(command):
    """ Serve data collected by the DataManager block.

    Args:

    Returns:
        Requested data.
    """


    # Command <ohlcv>
    if command == 'ohlcv':
        projection = {'ohlcv': True, 'date8061': True, '_id': False}

        symbol      = request.json['symbol']
        timeframe   = request.json['timeframe']

        if 'from' in request.json:
            from_millis = request.json['from']
            from_millis -= (from_millis / timeframe_to_ms(timeframe))
        else:
            from_millis = 0

        if 'to' in request.json:
            to_millis   = request.json['to']
            to_millis   -= (to_millis / timeframe_to_ms(timeframe))
        else:
            to_millis = current_millis() + 10e3

        symbol_db = symbol.replace('/', '_')
        collection = datamanager_db[symbol_db]

        query = {'ohlcv': {'$exists': True},
                 'timeframe': timeframe,
                 'date8061': {'$gt': from_millis, '$lt': to_millis}
                }

        ohlcv_cursor = collection.find(query, projection).sort('date8061', pymongo.ASCENDING)

        ohlcv = []
        for doc in ohlcv_cursor:
            ohlcv.append(doc)

        if ohlcv == []:
            return jsonify({'error': 'Data not available.'})
        else:
            return jsonify(ohlcv)

    else:
        return jsonify({'error': 'Command not found.'})




#----------------------------------------------------------------------------
#   Route /datamanager/subscribe
#----------------------------------------------------------------------------

valid_subscribe_streams = ('ohlcv',)

@app.route('/datamanager/subscribe', methods=['GET'])
def subscribe():
    """ List data streams you can subscribe to.

    When you subscribe, you will be given an IP, PORT tuple where you can
    listen for the updated data.

    Args:

    Returns:
        valid_subscribe_streams (str list)
        active_subscriptions (dict)
    """

    return jsonify({'valid_subscribe_streams': list(valid_subscribe_streams),
                    'active_subscriptions': active_subscriptions,
                   })


#----------------------------------------------------------------------------
#   Route /datamanager/subscribe/<command>
#----------------------------------------------------------------------------

SUBS_CLIENTS_WAITING_MAX = 10

SUBS_HOST = socket.gethostbyname( 'localhost' )
SUBS_PORT_BASE = 5100
SUBS_PORT_LIMIT = 6000

active_subscriptions = {} #dict {'stream_type_a': (HOST, PORT), 'stream_type_b': [(...

subscription_threads = {} # dict {'stream_type_a': thread, ... }
subscribers = [] # list of threads


@app.route('/datamanager/subscribe/<string:command>', methods=['GET'])
def subscribe_commands(command):
    """ Serve data collected by the DataManager block.

    Args:

    Returns:
        IP (str)
        port (int)
    """

    # Command <stream>
    if command == 'stream':
        stream_type = request.json['type']

        if stream_type in active_subscriptions:
            return jsonify({stream_type: active_subscriptions[stream_type]})
        else:
            port = SUBS_PORT_BASE

            available = 0
            while available == 0:
                available = 1
                for used_type, used_tuple in active_subscriptions.items():
                    if port == used_tuple[1]:
                        available = 0
                        port += 1
                        break

            active_subscriptions[stream_type] = (SUBS_HOST, port)

            subscription_threads[stream_type] = subscription_thread(stream_type, SUBS_HOST, port)
            subscription_threads[stream_type].start()

            return jsonify({stream_type: (SUBS_HOST, port)})


    else:
        return jsonify({'error': 'Command not found.'})


class subscription_thread(threading.Thread):
    """ Subscription socket server

    One server is created per stream_type, to serve all clients subscribed to it (subscribers).

    Args:

    Returns:
    """
    def __init__(self, stream_type, host, port):
        threading.Thread.__init__(self)
        self.stream_type = stream_type
        self.host = host
        self.port = port

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind( (self.host, self.port) )
        except socket.error as msg:
            return jsonify({'error': 'Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1]})

        s.listen(SUBS_CLIENTS_WAITING_MAX)

        while True:
            conn, addr = s.accept()
            print('Connected with ' + addr[0] + ':' + str(addr[1]))

            subscribers.append( subscriber_thread(self.stream_type, conn, addr) )
            subscribers[-1].start()



class subscriber_thread(threading.Thread):
    """ Subscriber socket server
    .
    One is created per subscriber to send them new data as soon as it is made
    available trough it's queue.

    Args:

    Returns:
    """
    def __init__(self, stream_type, conn, addr):
        threading.Thread.__init__(self)
        self.stream_type = stream_type
        self.conn = conn
        self.addr = addr

    def run(self):
        print('Subscriber thread for ' + self.stream_type + ' at ' + self.addr[0] + ':' + str(self.addr[1]) )
        i = 0
        while True:
            time.sleep(1)
            self.conn.sendall(str(i).encode('ascii'))




#----------------------------------------------------------------------------
#   Route /ticker
#----------------------------------------------------------------------------

@app.route('/ticker', methods=['GET'])
def get_ticker():
    """ Get BTC/USD ticker info.

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
        app.run(debug=False)
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
# Script-run mode
#----------------------------------------------------------------------------
if __name__ == '__main__':
    print("DataManager in script mode.")
