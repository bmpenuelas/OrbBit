
import sys
import logging
import time
import socket
import json
import requests
from   pkg_resources import resource_filename
from   telegram.ext  import Updater, CommandHandler, MessageHandler, Filters



#----------------------------------------------------------------------------
# LOG
#----------------------------------------------------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)



#%%##########################################################################
#                                   INIT                                    #
#############################################################################

bot_token_route = resource_filename('orbbit', 'UserInterface/telegram_bot/bot_token.key')
with open(bot_token_route) as f:
    bot_token_key = json.load(f)

updater = Updater(token = bot_token_key['token'])
dispatcher = updater.dispatcher


#############################################################################
#                               BOT COMMANDS                                #
#############################################################################

def start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="Dame amorsito.")

start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)

echo_handler = MessageHandler(Filters.text, echo)
dispatcher.add_handler(echo_handler)


def caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    bot.send_message(chat_id=update.message.chat_id, text=text_caps)

caps_handler = CommandHandler('caps', caps, pass_args=True)
dispatcher.add_handler(caps_handler)



macd_requests = []
def macd_alert(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="MACD.")

    if not update.message.chat_id in macd_requests:
        macd_requests.append(update.message.chat_id)

start_handler = CommandHandler('macd_alert', macd_alert)
dispatcher.add_handler(start_handler)



def macd_message(bot, user, symbol, timeframe, buy_sell, price):
    bot.send_message(chat_id=user,
                     text="ALERT: MACD cross - " + buy_sell + ' @ ' + str(price) + ' (' + symbol + ' ' + timeframe + ')'
                    )


#%%--------------------------------------------------------------------------
# Script mode
#----------------------------------------------------------------------------
if __name__ == '__main__':
    print("UserInterface in script mode.")
    updater.start_polling()

    import orbbit as orb
    orb.DM.start_API()


    # start the fetchers that ask the exchange for new data
    r = requests.get('http://127.0.0.1:5000/datamanager/fetch/start')
    time.sleep(10)

    #%% request subscription
    jsonreq = {'res':'macd', 'params':{'symbol':'BTC/USD', 'timeframe':'1m', 'ema_fast': 5, 'ema_slow': 12}}
    r = requests.get('http://127.0.0.1:5000/datamanager/subscribe/add', json=jsonreq)
    response_dict = r.json()
    print(response_dict)

    #%% keep only the (IP, PORT) part of the response, the socket expects a tuple.
    subs = list( response_dict.values() )[0]
    ip_port_tuple = tuple(subs)

    #%% connect socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    except socket.error:
        print('Failed to create socket')
        sys.exit()

    s.connect( ip_port_tuple )
    print('Connected')

    #%% get new data as soon as it is generated
    date8061 = []
    ema_fast = []
    ema_slow = []

    while 1:
        reply = s.recv(4096) # waits here until new data is received
        reply_dict = json.loads(reply.decode('ascii')) # turn string into data structure
        print('Live new data:')
        print(reply_dict)

        if reply_dict['macd']['cross']:
            symbol = 'BTC/USD'
            timeframe = '1m'
            buy_sell = 'buy' if reply_dict['macd']['rising'] else 'sell'
            price = reply_dict['ohlcv']['close']

            for user in macd_requests:
                macd_message(updater.bot, user, symbol, timeframe, buy_sell, price)


