#!/usr/bin/python3

import sys
import threading
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
LOCAL_HOST = socket.gethostbyname( 'localhost' )

#----------------------------------------------------------------------------
# LOG
#----------------------------------------------------------------------------

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)



#%%##########################################################################
#                                   INIT                                    #
#############################################################################

bot_token_route = resource_filename('orbbit', 'UserInterface/telegram_bot/keys/bot_token.key')
with open(bot_token_route) as f:
    bot_token_key = json.load(f)

updater = []
dispatcher = []
job_queue = []

def init_bot():
    global updater
    global dispatcher
    global job_queue

    updater = Updater(token = bot_token_key['token'])
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue



#############################################################################
#                                  GLOBALS                                  #
#############################################################################

active_chats = set()





#############################################################################
#                             EXAMPLE HANDLERS                              #
#############################################################################

def command_start(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="You are now subscribed to signal alerts.")
    active_chats.add(update.message.chat_id)

def add_start_handler():
    start_handler = CommandHandler('start', command_start)
    dispatcher.add_handler(start_handler)



def command_stop(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text="You will not receive more signal alerts.")
    active_chats.remove(update.message.chat_id)

def add_stop_handler():
    stop_handler = CommandHandler('stop', command_stop)
    dispatcher.add_handler(stop_handler)



def command_echo(bot, update):
    bot.send_message(chat_id=update.message.chat_id, text=update.message.text)

def add_echo_handler():
    echo_handler = MessageHandler(Filters.text, command_echo)
    dispatcher.add_handler(echo_handler)



def command_caps(bot, update, args):
    text_caps = ' '.join(args).upper()
    bot.send_message(chat_id=update.message.chat_id, text=text_caps)

def add_caps_handler():
    caps_handler = CommandHandler('caps', command_caps, pass_args=True)
    dispatcher.add_handler(caps_handler)




#############################################################################
#                               BOT COMMANDS                                #
#############################################################################

def command_alert_macd(bot, update, args):
    text = 'Starting MACD cross monitoring with params: '
    for arg in args:
        text += (arg + ' ')
    bot.send_message(chat_id=update.message.chat_id, text=text)

    user_requesting = update.message.chat_id

    symbol = args[0]
    timeframe = args[1]
    ema_fast = int(args[2])
    ema_slow = int(args[3])

    # macd subscription required params
    params = {'symbol': symbol, 'timeframe': timeframe, 'ema_fast': ema_fast, 'ema_slow': ema_slow}


    new_macd_thread = alert_macd(user_requesting, params)
    new_macd_thread.start()


def add_command_alert_macd_handler():
    command_alert_macd_handler = CommandHandler('macd_alert', command_alert_macd, pass_args=True)
    dispatcher.add_handler(command_alert_macd_handler)



class alert_macd(threading.Thread):
    """ Thread that subscribes to MACD and sends an alert on cross.

    Args:
        user_requesting (id) telegram bot user id
        params (dict) params as expected by macd subscription
    """
    def __init__(self, user_requesting, params):
        threading.Thread.__init__(self)

        self.user_requesting = user_requesting
        self.params = params


        #%% request subscription
        jsonreq = {'res':'macd', 'params':params}
        r = requests.post('http://' + LOCAL_HOST + ':5000/datamanager/subscribe/add', json=jsonreq)
        response_dict = r.json()
        print(response_dict)

        #%% keep only the (IP, PORT) part of the response, the socket expects a tuple.
        subs = list( response_dict.values() )[0]
        ip_port_tuple = tuple(subs)

        #%% connect socket
        try:
            self.subscription_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error:
            print('Failed to create socket')
            sys.exit()

        self.subscription_socket.connect( ip_port_tuple )
        print('Bot connected to MACD subscription socket')

    def run(self):

        #%% get new data as soon as it is generated
        while 1:
            reply = self.subscription_socket.recv(4096) # waits here until new data is received
            reply_dict = json.loads(reply.decode('ascii')) # turn string into data structure
            # print('Telegram bot alert_macd thread got new subs data.')
            # print(reply_dict)

            if reply_dict['macd']['cross']:
                buy_sell = 'buy' if reply_dict['macd']['rising'] else 'sell'
                price = reply_dict['ohlcv']['close']
                print('Sending Telegram bot alert_macd.')

                macd_message(updater.bot, self.user_requesting, self.params['symbol'], self.params['timeframe'], buy_sell, price)



def macd_message(bot, user, symbol, timeframe, buy_sell, price):
    bot.send_message(chat_id=user,
                     text="ALERT: MACD cross - " + buy_sell + ' @ ' + str(price) + ' (' + symbol + ' ' + timeframe + ')'
                    )



def callback_minute(bot, job):
    for chat in active_chats:
        bot.send_message(chat_id=chat, text='One message every minute')




#%%--------------------------------------------------------------------------
# ADD ALL HANDLERS
#----------------------------------------------------------------------------


def add_all_handlers():
    add_start_handler()
    add_stop_handler()
    add_echo_handler()
    add_caps_handler()
    add_command_alert_macd_handler()




#%%##########################################################################
#                                 START BOT                                 #
#############################################################################
def start():
    init_bot()
    add_all_handlers()
    updater.start_polling()


#%%##########################################################################
#                                SCRIPT MODE                                #
#############################################################################
if __name__ == '__main__':
    print("Telegram Bot in script mode.")
    start()
    job_minute = job_queue.run_repeating(callback_minute, interval=2, first=0)
