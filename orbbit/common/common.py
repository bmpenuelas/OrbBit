
import os
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
                            'exchanges': [],
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


def symbol_os(exchange_id, symbol):
    if exchange_id == 'hitbtc' and os.name == 'nt':
        return symbol.replace('/USDT', '/USD')
    else:
        return symbol



def read_symbol_os(exchange_id, symbol):
    if exchange_id == 'hitbtc' and os.name == 'nt':
        return symbol.replace('/USD', '/USDT')
    else:
        return symbol