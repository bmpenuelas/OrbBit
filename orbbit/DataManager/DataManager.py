import sys
import time
import threading

import numpy as np

from   flask import Flask, jsonify, abort, make_response, request
from   flask_httpauth import HTTPBasicAuth

import ccxt

import pymongo
import json



#----------------------------------------------------------------------------
# EXCHANGES SETUP
#----------------------------------------------------------------------------

#\todo Check exchange.hasFetchOHLCV
exchange = ccxt.hitbtc2({'verbose': False})
  
def print_markets():
    hitbtc_markets = exchange.load_markets()
    print(exchange.id, hitbtc_markets)


def fetch_ticker():
    return exchange.fetch_ticker('BTC/USD')


#----------------------------------------------------------------------------
# DATABASE SETUP
#----------------------------------------------------------------------------

def get_datamanager_info(info):
    """Get the 'info' field from the 'datamanager_info' collection.

    It stores parameters that should be kept between runs of the program.

    Args:
        info (str): info field identifier

    Returns:
        Structure stored under 'info'. Can be any data structure.
    """

    try:

        return list( datamanager_info.find({info:{'$exists': True}}) )[0][info]
    except IndexError:
        datamanager_info.insert_one( {'fetching_symbols':['BTC/USD', 'ETH/USD',], } )
        return list( datamanager_info.find({info:{'$exists': True}}) )[0][info]



from pkg_resources import resource_filename
datamanager_db_route = resource_filename('orbbit', 'DataManager/datamanager_db.key')

with open(datamanager_db_route) as f:
    datamanager_db_key = json.load(f)    

datamanager_db_connection = pymongo.MongoClient(datamanager_db_key['url'], datamanager_db_key['port'])
datamanager_db = datamanager_db_connection[datamanager_db_key['database']]
datamanager_db.authenticate(datamanager_db_key['user'], datamanager_db_key['password'])

datamanager_info = datamanager_db['datamanager_info']
fetching_symbols = get_datamanager_info('fetching_symbols')



#############################################################################
#                        DATAMANAGER TASKS                                  #
#############################################################################

def start_fetch():
    """ Start the fetcher.
    Return all data available in json format.

    Args:


    Returns:
      Json-formatted data.

    """
    fetching_symbols = get_datamanager_info('fetching_symbols')
    thread_save_ohlcv = [save_ohlcv(symbol, time.time()*1000) for symbol in fetching_symbols]

    for symbol_fetch in thread_save_ohlcv:
        symbol_fetch.start()


    return jsonify({'fetching_symbols': get_datamanager_info('fetching_symbols')})



class save_ohlcv(threading.Thread):
    def __init__(self, symbol, curr_time_8061):
        threading.Thread.__init__(self)
        self.symbol = symbol
        self.curr_time_8061 = curr_time_8061

    def run(self):
        print('Started fetcher for ' + self.symbol)

        collection = datamanager_db[self.symbol]
        nxt_fetch = self.curr_time_8061

        while 1:
            fetch_from_API_success = 0
            while not(fetch_from_API_success):
                try:
                    ohlcvs = exchange.fetch_ohlcv(self.symbol.replace('_', '/'), '1m', nxt_fetch)
                    fetch_from_API_success = 1
                except:
                    time.sleep(1)
        
            if ohlcvs:
                new_row = {}
                for candle in ohlcvs:
                    new_row['_id']      = candle[0]
                    new_row['date8061'] = candle[0]
                    new_row['open']     = candle[1]
                    new_row['high']     = candle[2]
                    new_row['low']      = candle[3]
                    new_row['close']    = candle[4]
                    new_row['volume']   = candle[5]
                
                    print("Inserted " + str(new_row['date8061']))
                    try:
                        collection.insert_one(new_row)
                    except pymongo.errors.DuplicateKeyError as e:
                        print("Duplicate value, skipping.")
                  
                    nxt_fetch += 60 * 1000
            else:
                time.sleep(10)




#############################################################################
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
def get_fetching_symbols():
    """ Get all data.
    Return all data available in json format.

    Args:


    Returns:
      Json-formatted data.

    """
    return jsonify({'fetching_symbols': get_datamanager_info('fetching_symbols')})


#----------------------------------------------------------------------------
#   Route /datamanager/fetch
#----------------------------------------------------------------------------

@app.route('/datamanager/fetch', methods=['GET'])
def fetch():
    return jsonify({'fetching_symbols': get_datamanager_info('fetching_symbols')})


#----------------------------------------------------------------------------
#   Route /datamanager/fetch/start
#----------------------------------------------------------------------------

@app.route('/datamanager/fetch/start', methods=['GET'])
def fetch_start():
    return start_fetch()


#----------------------------------------------------------------------------
#   Route /datamanager/fetch/add
#----------------------------------------------------------------------------

@app.route('/datamanager/fetch/add/<string:new_symbol>', methods=['GET'])
def add_fetching_symbol(new_symbol):
    fetching_symbols = get_datamanager_info('fetching_symbols')

    if not( new_symbol.replace('_', '/') in fetching_symbols ):
        fetching_symbols.append(new_symbol.replace('_', '/'))
        datamanager_info.update_one({'fetching_symbols':{'$exists': True}}, {"$set": {'fetching_symbols':fetching_symbols, } }, upsert=True)
        new_symbol_fetcher = save_ohlcv(new_symbol.replace('_', '/'), time.time()*1000)
        new_symbol_fetcher.start()

    return jsonify({'fetching_symbols': fetching_symbols})



# POST, PUT, DELETE examples
@app.route('/datamanager', methods=['POST'])
def create_task():
    if not request.json or not 'title' in request.json:
        print(request.json)
        abort(400)
    task = {
        'id': tasks[-1]['id'] + 1,
        'title': request.json['title'],
        'description': request.json.get('description', ""),
        'done': False
    }
    tasks.append(task)
    return jsonify({'task': task}), 201


@app.route('/datamanager/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    if not request.json:
        abort(400)
    if 'title' in request.json and type(request.json['title']) != unicode:
        abort(400)
    if 'description' in request.json and type(request.json['description']) is not unicode:
        abort(400)
    if 'done' in request.json and type(request.json['done']) is not bool:
        abort(400)
    task[0]['title'] = request.json.get('title', task[0]['title'])
    task[0]['description'] = request.json.get('description', task[0]['description'])
    task[0]['done'] = request.json.get('done', task[0]['done'])
    return jsonify({'task': task[0]})


@app.route('/datamanager/<int:task_id>', methods=['DELETE'])
@auth.login_required
def delete_task(task_id):
    task = [task for task in tasks if task['id'] == task_id]
    if len(task) == 0:
        abort(404)
    tasks.remove(task[0])
    return jsonify({'result': True})



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




#----------------------------------------------------------------------------
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



def start_DataManager_API():
    """ Start DataManager API Server
    Starts in a separate subprocess.

    Args:

    Returns:
      Subprocess ID.
    """

    print("Starting API Server.")
    thread_DataManager_API.start()



#----------------------------------------------------------------------------
# Script-run mode
#----------------------------------------------------------------------------
if __name__ == '__main__':
    print("DataManager Started.")
