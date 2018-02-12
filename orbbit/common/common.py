#!/usr/bin/python3

import os
import sys
import time
from   datetime       import timedelta
from   flask          import make_response, request, current_app
from   functools      import update_wrapper
import json
import pymongo
from   pkg_resources  import resource_filename
import ccxt
from   flask_httpauth import HTTPBasicAuth


#%%##########################################################################
#                          CONFIGURATION PARAMETERS                         #
#############################################################################

default_fetch_timeframes = ['1m',]

typical_quote_currencies = ['USDT', 'BTC', 'ETH']

typical_exchanges = ['hitbtc2', 'bittrex', 'binance', 'kraken']


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
        return int(timeframe.replace('M', '')) * 30 * 24 * 60 * 60 * 1000
    elif 'w' in timeframe:
        return int(timeframe.replace('w', '')) * 7  * 24 * 60 * 60 * 1000
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
    """ Convert candles (ohlcv) to database documents.
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



# Types that are implemented
valid_subscribtion_resources = {'fetched': ['ohlcv',],
                                'transformed': ['macd',],
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




#%%##########################################################################
#                                IMPORT KEYS                                #
#############################################################################

def dict_from_key(route):
    key_route = resource_filename('orbbit', route)

    with open(key_route) as f:
        key_dict = json.load(f)

    return key_dict




#%%##########################################################################
#                              SETUP DATABASES                              #
#############################################################################
    """
    Note:
        To delete all database contents run the following block. Use with caution!

        db_key = dict_from_key('DataManager/keys/db.key')
        database_names = db_key.keys()
        for database_name in database_names:
            db_connection = pymongo.MongoClient(db_key[database_name]['url'], db_key[database_name]['port'])
            db = db_connection[database_name]
            db.authenticate(db_key[database_name]['user'], db_key[database_name]['password'])
            db_connection.drop_database(database_name)

    """

def database_connection(database_name):

    db_key = dict_from_key('DataManager/keys/db.key')
    # print(db_key)
    db_connection = pymongo.MongoClient(db_key[database_name]['url'], db_key[database_name]['port'])

    db = db_connection[database_name]
    db.authenticate(db_key[database_name]['user'], db_key[database_name]['password'])
    return db



def database_info_connection(database):
    return database['info']



def get_database_info(database_name, info):
    """Get the 'info' field from the 'info' collection at the db.

    It stores parameters that should be kept between runs of the program.

    Args:
        info (str): info field identifier.

    Returns:
        Structure stored under 'info'. Can be any data structure.


    Example:
        database_name = 'datamanager'
        info = 'fetching_symbols'
        get_database_info(database_name, info)

        database_name = 'ordermanager'
        info = 'user_info'
        get_database_info(database_name, info)

    """

    db_conn = database_connection(database_name)
    info_connection = database_info_connection(db_conn)

    try:
        return info_connection.find( {info: {'$exists': True}} )[0][info]
    except IndexError:
        # if the database is empty, use these config by default
        if database_name == 'datamanager':
            new_documents = [
                {'fetching_symbols':
                    {'hitbtc2': {'BTC/USDT':   default_fetch_timeframes,
                                 'ETH/USDT':   default_fetch_timeframes,
                                },
                     'bittrex': {'BTC/USDT':   default_fetch_timeframes,
                                 'ETH/USDT':   default_fetch_timeframes,
                                },
                    }
                },
                {'fetch_exchanges':
                    typical_exchanges
                },
            ]
        elif database_name == 'ordermanager':
            new_documents = [
                {   'user_info': {
                        'farolillo': {
                            'exchanges': ['hitbtc2', 'binance'],
                        },
                        'linternita': {
                            'exchanges': ['bittrex',],
                        },
                    }
                },
            ]
        info_connection.insert_many(new_documents, ordered = False )
        return info_connection.find( {info: {'$exists': True}} )[0][info]



def update_database_info(database_name, key, value):
    info_connection = database_info_connection( database_connection(database_name) )
    info_connection.update_one( {key: {'$exists': True}}, {"$set": {key: value, }}, upsert=True )




def add_fetching_symbol(exchange_id, symbol, timeframe):
    """Add a fetcher to the db.

    Example:
        exchange_id = 'bittrex'
        symbol = 'BTC/USDT'
        timeframe = '1m'
        fetching_symbols = add_fetching_symbol(exchange_id, symbol, timeframe)

    Args:

    Returns:

    """

    database_name = 'datamanager'

    fetching_symbols = get_database_info(database_name, 'fetching_symbols')

    if not timeframe in ( fetching_symbols.get(exchange_id, {}) ).get(symbol, {}):
        is_new = 1

        fetching_symbols.setdefault(exchange_id, {})
        fetching_symbols[exchange_id].setdefault(symbol, [])
        fetching_symbols[exchange_id][symbol].append(timeframe)


        update_database_info('datamanager', 'fetching_symbols', fetching_symbols)
        print('Adding fetcher for ' + symbol + ' ' + timeframe + ' @ ' + exchange_id)

    return fetching_symbols



#----------------------------------------------------------------------------
#   Get information sets from DB
#----------------------------------------------------------------------------

def get_db_ohlcv(symbol, exchange_id, timeframe, from_millis, to_millis):
    """Get 'ohlcv' documents from db.

    Example:
        symbol = 'BTC/USDT'
        exchange_id = 'bittrex'
        timeframe = '1m'
        from_millis = current_millis() - 15 * timeframe_to_millis(timeframe)
        to_millis = current_millis() + 10e3
        ohlcv_cursor = get_db_ohlcv(symbol, exchange_id, timeframe, from_millis, to_millis)
    Args:
        symbol, timeframe, from_millis, to_millis
    Returns:
        pymongo cursor pointing to the docs

    """

    projection = {'date8061': True, 'ohlcv': True}

    symbol_db = symbol.replace('/', '_')

    collection_name = exchange_id + '_' + symbol_db
    collection = datamanager_db[collection_name]

    query = {'ohlcv': {'$exists': True},
             'timeframe': timeframe,
             'date8061': {'$gt': from_millis, '$lt': to_millis}
            }

    # print('get_db_ohlcv '+ str(len(cursor_to_list(collection.find(query, projection).sort('date8061', pymongo.ASCENDING)))))
    return collection.find(query, projection).sort('date8061', pymongo.ASCENDING)




#----------------------------------------------------------------------------
#   Databases Connections
#----------------------------------------------------------------------------

datamanager_db = database_connection('datamanager')

ordermanager_db = database_connection('ordermanager')




#%%##########################################################################
#                              SETUP EXCHANGES                              #
#############################################################################

#def add_exchange(exchange_id, exchanges, user):
#    fetch_exchanges = get_database_info(datamanager_info, 'fetch_exchanges')
#    if not exchange_id in fetch_exchanges:
#        fetch_exchanges.append(exchange_id)
#        update_datamanager_info('fetch_exchanges', fetch_exchanges)
#
#    exchanges = {new_exchange: exchange_id_to_exchange(new_exchange) for new_exchange in fetch_exchanges}
#
#    new_exchange = exchange_id_to_exchange(exchange_id)
#    if new_exchange != -1:
#        exchanges[exchange_id] = new_exchange
#    else:
#        return exchanges



def exchange_id_to_exchange(exchange_id):
    if exchange_id == 'hitbtc2':
        return ccxt.hitbtc2({'verbose': False})
    if exchange_id == 'bittrex':
        return ccxt.bittrex({'verbose': False})
    if exchange_id == 'binance':
        return ccxt.binance({'verbose': False})
    if exchange_id == 'kraken':
        return ccxt.kraken({'verbose': False})
    else:
        return -1

def exchange_id_to_user_exchange(exchange_id, user):
    exchanges_key = dict_from_key('OrderManager/keys/exchanges.key')

    if exchange_id == 'hitbtc2':
        return ccxt.hitbtc2({   'verbose': False,
                                'apiKey': exchanges_key[user][exchange_id]['key'],
                                'secret': exchanges_key[user][exchange_id]['secret']
                            })
    if exchange_id == 'bittrex':
        return ccxt.bittrex({   'verbose': False,
                                'apiKey': exchanges_key[user][exchange_id]['key'],
                                'secret': exchanges_key[user][exchange_id]['secret']
                            })
    if exchange_id == 'binance':
        return ccxt.binance({   'verbose': False,
                                'apiKey': exchanges_key[user][exchange_id]['key'],
                                'secret': exchanges_key[user][exchange_id]['secret']
                            })
    if exchange_id == 'kraken':
        return ccxt.kraken( {   'verbose': False,
                                'apiKey': exchanges_key[user][exchange_id]['key'],
                                'secret': exchanges_key[user][exchange_id]['secret']
                            })
    else:
        return -1



def symbol_os(symbol, exchange_id):
    if (exchange_id == 'hitbtc2' or exchange_id == 'hitbtc2') and os.name == 'nt':
        return symbol.replace('/USDT', '/USD')
    else:
        return symbol



def read_symbol_os(symbol, exchange_id):
    if (exchange_id == 'hitbtc2' or exchange_id == 'hitbtc2') and os.name == 'nt':
        return symbol.replace('/USD', '/USDT')
    else:
        return symbol



def symbol_base(symbol, exchange_id):
    return read_symbol_os(symbol, exchange_id).split('/')[0]



def symbol_quote(symbol, exchange_id):
    return read_symbol_os(symbol, exchange_id).split('/')[1]



def get_balance(exchange, coin=None, add_missing_fetchers=True):
    retry = 3
    retry_interval = 0.2

    while retry > 0:
        try:
            api_balance = exchange.fetchBalance()
            break
        except Exception as ex:
            retry -= 1
            time.sleep(retry_interval)
    if retry == 0:
        print('Retried but failed get_balance ' + exchange.id)
        return -1

    totals = api_balance['total']

    balance = {holding_coin:totals[holding_coin] for holding_coin in totals if totals[holding_coin] > 0.0 }

    if add_missing_fetchers:
        for timeframe in default_fetch_timeframes:
            for holding_coin in balance:
                possible_symbols = [holding_coin + '/' + quote for quote in typical_quote_currencies]
                symbols = [symbol for symbol in possible_symbols if symbol_os(symbol, exchange.id) in exchange.symbols]
                for symbol in symbols:
                    add_fetching_symbol(exchange.id, symbol, timeframe)


    if coin:
        if coin in balance:
            return balance[coin]
        else:
            return 0.0

    else:
        return balance



def get_balance_usd(exchange, coin=None, min_usd_value=0.0):
    balance = get_balance(exchange, coin)

    balance_usd = {coin: get_current_price_usd(coin, exchange) * balance[coin] for coin in balance}
    total_usd = sum(list(balance_usd.values()))
    if min_usd_value:
        balance_usd = {coin: balance_usd[coin] for coin in balance_usd if balance_usd[coin] > min_usd_value}
        balance     = {coin: balance[coin] for coin in balance_usd}

    return balance_usd, total_usd, balance



def get_trade_history(exchange, symbol=None):
    """ Get trade history.

    Note:
        To get all the orders:
            hitbtc exchange needs to merge fetchClosedOrders() with fetchMyTrades().
            bittrex exchange needs to merge fetchOrders() + fetchOpenOrders().
            binance won't allow to fetch them all at once, you have to iterate over your symbols.

    Args:
        exchange

    Returns:
        trade_history (dict)
            symbol
            amount
            price

    Example:
        exchange = user_exchanges['farolillo']['binance']
        get_trade_history(exchange)

    """

    trade_history = []

    if exchange.id == 'hitbtc2':
        api_my_trades = exchange.fetchMyTrades(limit=1000)
        trade_history = api_my_trades

    elif exchange.id == 'bittrex':
        api_orders = exchange.fetchOrders(limit=1000)
        trade_history = api_orders

    elif exchange.id == 'binance':
        coin = symbol_base(symbol, exchange.id) if symbol else None
        balance = get_balance(exchange, coin)
        for holding_coin in balance:
            possible_symbols = [holding_coin + '/' + quote for quote in typical_quote_currencies if (holding_coin + '/' + quote) in exchange.symbols]
            for next_symbol in possible_symbols:
                api_my_trades = exchange.fetchMyTrades(symbol=next_symbol, limit=1000)
                trade_history.append(api_my_trades)

    else:
        return -1

    if symbol:
        return [trade for trade in trade_history if read_symbol_os(trade['symbol'], exchange.id) == symbol]
    else:
        return trade_history



def get_sell_history(exchange, symbol=None):
    """
    Example:
        exchange = user_exchanges['farolillo']['hitbtc2']
        symbol = 'XRP/USDT'
        get_sell_history(exchange, symbol)
    """
    trade_history = get_trade_history(exchange, symbol)
    return [trade for trade in trade_history if trade['side'] == 'sell']



def get_buy_history(exchange, symbol=None):
    """
    Example:
        exchange = user_exchanges['farolillo']['binance']
        symbol = 'XRP/USDT'
        buy_history = get_buy_history(exchange), symbol)
    """
    trade_history = get_trade_history(exchange, symbol)

    buy_history = []
    try:
        buy_history = [trade for trade in trade_history if trade['side'] == 'buy']
    except:
        print('ERR get_buy_history : Could not process trade list.')
        print(trade_history)
    return buy_history



def get_open_orders(exchange):
    open_orders = []

    if exchange.id == 'hitbtc2':
        api_closed_orders = exchange.fetchClosedOrders(limit=1000)
        open_orders = [order for order in api_closed_orders if order['status'] == 'open']

    elif exchange.id == 'bittrex':
        api_open_orders = exchange.fetchOpenOrders(limit=1000)
        open_orders = api_open_orders
        #\todo create one and cancel, see what happens

    else:
        return -1

    return open_orders



def get_current_price(symbol, exchange):
    """Get current price.

    Args:
        symbol
        exchange (ccxt.Exchange)

    Returns:
        price (double)

    Example:
        exchange = user_exchanges['farolillo']['hitbtc2']
        symbol = 'LIFE/BTC'
        get_current_price(symbol, exchange)

    """

    if exchange.has['fetchTicker']:
        retry = 3
        retry_interval = 0.2

        while retry > 0:
            try:
                api_ticker = exchange.fetchTicker( symbol_os(symbol, exchange.id) )
                return api_ticker['last']
            except Exception as ex:
                retry -= 1
                time.sleep(retry_interval)
        print('Retried but failed get_current_price ' + symbol)
        return -1

    else:
        return -1



def get_coin_symbols(coin, exchange):
    """Get pairs in which 'coin' can be traded.

    Args:
        coin
        exchange (ccxt.Exchange)

    Returns:
        price (double)

    Example:
        coin = 'LIFE'
        exchange = user_exchanges['farolillo']['hitbtc2']
        get_coin_symbols(coin, exchange)

    """

    return [symbol for symbol in exchange.symbols if (coin+'/') in symbol]


def get_current_price_usd(coin, exchange, prefer_double_conversion=False):
    """Get current price in USD.

    Double conversion with coins usually used as quote currency,
    to USD or USDT.

    Args:
        coin
        exchange (ccxt.Exchange)

    Returns:
        price (double)

    Example:
        prefer_double_conversion = False
        coin = 'OMG'
        exchange = user_exchanges['farolillo']['hitbtc2']
        get_current_price_usd(coin, exchange)

        prefer_double_conversion = True
        coin = 'OMG'
        exchange = user_exchanges['farolillo']['hitbtc2']
        get_current_price_usd(coin, exchange)

    """

    usd_equivalents = ('USD', 'USDT')
    usual_quote_currencies = ('BTC', 'ETH', 'BCC')

    symbols = get_coin_symbols(coin, exchange)


    if (coin == 'USD' or coin == 'USDT'):
      return 1

    if not prefer_double_conversion:
        for quote in usd_equivalents:
            if (coin + '/' + quote) in symbols:
              return get_current_price( (coin + '/' + quote), exchange )

        for quote in usual_quote_currencies:
            if (coin + '/' + quote) in symbols:
              base_price  = get_current_price( (coin + '/' + quote), exchange )
              quote_price = get_current_price( (quote + '/' + 'USDT'), exchange )

              return base_price * quote_price

        return -1

    else:
        for quote in usual_quote_currencies:
            if (coin + '/' + quote) in symbols:
              base_price  = get_current_price( (coin + '/' + quote), exchange )
              quote_price = get_current_price( (quote + '/' + 'USDT'), exchange )

              return base_price * quote_price

        for quote in usd_equivalents:
            if (coin + '/' + quote) in symbols:
              return get_current_price( (coin + '/' + quote), exchange )

        return -1


def get_holdings_cost(exchange, min_usd_value=0.0):
    """Get aggregated buy cost for every coin in balance.

    Args:

    Returns:

    Example:
        exchange = user_exchanges['farolillo']['hitbtc2']
        holdings_cost = get_holdings_cost(exchange)

    """

    if min_usd_value:
        balance_usd, total_usd, balance = get_balance_usd(exchange, min_usd_value=min_usd_value)
    else:
        balance = get_balance(exchange)


    balance_remaining = balance

    buy_history = get_buy_history(exchange)

    coin_cost = {coin: {} for coin in balance}
    for trade in buy_history:
        for coin in balance:
            if coin == symbol_base(trade['symbol'], exchange.id) and balance_remaining[coin] > 0.0:
                if trade['amount'] <= balance_remaining[coin]:
                    valid_amount = trade['amount']
                    balance_remaining[coin] -= valid_amount
                    cost = trade['cost']
                else:
                    valid_amount = balance_remaining[coin]
                    balance_remaining[coin] = 0.0
                    cost = valid_amount * trade['price']

                if not symbol_quote(trade['symbol'], exchange.id) in coin_cost[coin]:
                    coin_cost[coin][symbol_quote(trade['symbol'], exchange.id)] = {'amount': valid_amount,
                                                                                   'cost': cost,
                                                                                   'first_buy': trade['timestamp']
                                                                                  }
                else:
                    coin_cost[coin][symbol_quote(trade['symbol'], exchange.id)]['amount']    += valid_amount
                    coin_cost[coin][symbol_quote(trade['symbol'], exchange.id)]['cost']      += cost
                    coin_cost[coin][symbol_quote(trade['symbol'], exchange.id)]['first_buy']  = trade['timestamp']

    coin_cost = {coin: coin_cost[coin] for coin in coin_cost if len(coin_cost[coin]) > 0}

    for coin in coin_cost:
        for quote in coin_cost[coin]:
            # print(coin + '/' + quote)
            coin_cost[coin][quote]['average_price'] = coin_cost[coin][quote]['cost'] / coin_cost[coin][quote]['amount']

    return coin_cost



def get_balance_norm_price_history(exchange, timeframe, min_usd_value=0.0):
    """
    Example:
        exchange = user_exchanges['farolillo']['hitbtc2']
        timeframe = '1h'
        normalized = get_balance_norm_price_history(exchange, timeframe)

        import matplotlib.pyplot as plt
        for symbol in normalized:
            plt.plot( normalized[symbol]['date8061'], normalized[symbol]['price'])
    """

    coin_cost = get_holdings_cost(exchange, min_usd_value)

    normalized = {}
    for coin in coin_cost:
        for quote in coin_cost[coin]:
            symbol = coin + '/' + quote
            average_price = coin_cost[coin][quote]['average_price']
            first_buy = coin_cost[coin][quote]['first_buy']
            normalized[symbol] = norm_price_history(symbol, average_price, first_buy, timeframe, exchange)

    max_len = 0
    for symbol in normalized:
        if len(normalized[symbol]['date8061']) > max_len:
            max_len = len(normalized[symbol]['date8061'])

    for symbol in normalized:
        for field in normalized[symbol]:
            normalized[symbol][field] = [None] * (max_len - len(normalized[symbol][field])) + normalized[symbol][field]

    return normalized


def norm_price_history(symbol, average_price, first_buy, timeframe, exchange):
    history_cursor = get_db_ohlcv(symbol, exchange.id, timeframe, first_buy, (current_millis() + 10e3))
    history = cursor_to_list(history_cursor)

    if len(history) > 0:
        date8061 = [ row['date8061'] for row in history]
        if date8061[0] > (first_buy + timeframe_to_millis(timeframe)):
            print('ERR norm_price_history: First_buy is older than first data logged.')

        close = [ row['ohlcv']['close'] for row in history]

        norm_price = [value / average_price for value in close]

    else:
        print('ERR norm_price_history ' + symbol)
        date8061 = []
        close = []
        norm_price = []

    return {'date8061': date8061, 'price': close, 'norm_price': norm_price}



#%%##########################################################################
#                                 FLASK API                                 #
#############################################################################

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




