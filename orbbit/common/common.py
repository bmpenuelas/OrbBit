
import os
import sys
import time
import json
import pymongo
from   pkg_resources  import resource_filename
import ccxt



#%%--------------------------------------------------------------------------
# Import keys
#----------------------------------------------------------------------------

def dict_from_key(route):
    key_route = resource_filename('orbbit', route)

    with open(key_route) as f:
        key_dict = json.load(f)

    return key_dict




#%%--------------------------------------------------------------------------
# Setup Databases
#----------------------------------------------------------------------------
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
                    {'hitbtc':  {'BTC/USDT': ['1m',],# '5m', '30m', '1h', '1d',],
                                 #'ETH/USDT': ['1m',], '5m', '30m', '1h', '1d',],
                                },
                     'bittrex': {'BTC/USDT': ['1m',],# '5m', '30m', '1h', '1d',],
                                 #'ETH/USDT': ['1m',], '5m', '30m', '1h', '1d',],
                                },
                    }
                },
                {'fetch_exchanges':
                    ['hitbtc', 'bittrex', 'binance', 'kraken']
                },
            ]
        elif database_name == 'ordermanager':
            new_documents = [
                {   'user_info': {
                        'farolillo': {
                            'exchanges': ['hitbtc',],
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




#%%##########################################################################
#                              EXCHANGES SETUP                              #
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
    if exchange_id == 'hitbtc':
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

    if exchange_id == 'hitbtc':
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
    if (exchange_id == 'hitbtc' or exchange_id == 'hitbtc2') and os.name == 'nt':
        return symbol.replace('/USDT', '/USD')
    else:
        return symbol



def read_symbol_os(symbol, exchange_id):
    if exchange_id == 'hitbtc' and os.name == 'nt':
        return symbol.replace('/USD', '/USDT')
    else:
        return symbol



def get_balance(exchange, symbol=None):
    retry = 3
    retry_interval = 0.2

    while retry > 0:
        try:
            api_balance = exchange.fetchBalance()
            break
        except Exception as ex:
            print(sys.exc_info()[0])
            retry -= 1
            time.sleep(retry_interval)
    if retry == 0:
        return -1

    totals = api_balance['total']

    balance = {coin:totals[coin] for coin in totals if totals[coin] > 0.0 }

    if symbol:
        if symbol in balance:
            return balance[symbol]
        else:
            return 0.0

    else:
        return balance



def get_current_price(symbol, exchange):
    """Get current price.

    Args:
        symbol
        exchange (ccxt.Exchange)

    Returns:
        price (double)

    Example:
        exchange = user_exchanges['farolillo']['hitbtc']
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
              print(sys.exc_info()[0])
              retry -= 1
              time.sleep(retry_interval)
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
        exchange = user_exchanges['farolillo']['hitbtc']
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
        exchange = user_exchanges['farolillo']['hitbtc']
        get_current_price_usd(coin, exchange)

        prefer_double_conversion = True
        coin = 'OMG'
        exchange = user_exchanges['farolillo']['hitbtc']
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
              quote_price = get_current_price( (quote + '/' + 'USD'), exchange )

              return base_price * quote_price

        return -1

    else:
        for quote in usual_quote_currencies:
            if (coin + '/' + quote) in symbols:
              base_price  = get_current_price( (coin + '/' + quote), exchange )
              quote_price = get_current_price( (quote + '/' + 'USD'), exchange )

              return base_price * quote_price

        for quote in usd_equivalents:
            if (coin + '/' + quote) in symbols:
              return get_current_price( (coin + '/' + quote), exchange )

        return -1
