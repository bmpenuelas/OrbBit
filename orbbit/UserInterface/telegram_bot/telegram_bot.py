
import logging
import json
from   pkg_resources import resource_filename
from   telegram.ext  import Updater, CommandHandler, MessageHandler, Filters



logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)



bot_token_route = resource_filename('orbbit', 'UserInterface/telegram_bot/bot_token.key')
with open(bot_token_route) as f:
    bot_token_key = json.load(f)

updater = Updater(token = bot_token_key['token'])
dispatcher = updater.dispatcher



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



updater.start_polling()



