
#!/usr/bin/python

import sys
import time
import ccxt
import pymongo
import json




with open('../../../OrbBit_noVC/keys/db/db_info.txt') as f:
  db_info = json.load(f)    


pair = 'NEO/USD'


connection = pymongo.MongoClient(db_info['url'], db_info['port'])
db = connection[db_info['database']]
db.authenticate(db_info['user'], db_info['password'])

db_NEO_USD = db[pair]


exchange = ccxt.hitbtc2({'verbose': False})


previous_fetch = time.time()*1000

if exchange.hasFetchOHLCV:
  while 1:
    ohlcvs = exchange.fetch_ohlcv(pair, '1m', previous_fetch)

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
      
        print("Inserted ")
        print(db_NEO_USD.insert_one(new_row).inserted_id )
        
        previous_fetch = time.time()*1000
    else:
      print("Waiting...")
      time.sleep(25)
      print("Go for next...")
       
  print('DONE.')

else:
  print('ERR: No OHLCV data in this exchange.')






