import telebot
from telebot import types
import configparser


# Read the Telegram TOKEN
config = configparser.ConfigParser()
config.read('config.ini')
TOKEN = config['telegram']['token']
ONIONOO = "https://onionoo.torproject.org/details?search="
START_MESSAGE = "Welcome back! Your ID is already in the database. Click /help to find out what you can do."
ADD_MESSAGE = "> Write down the fingerprint of the node you want to look at.\n> 47B72187844C00AA5D524415E52E3BE81E63056B\n> The node with fingerprint 47B72187844C00AA5D524415E52E3BE81E63056B has been added to your list."
REMOVE_MESSAGE = "> Write the fingerprint of the node you no longer want to control.\n> 47B72187844C00AA5D524415E52E3BE81E63056B\n> (If present...) The node with fingerprint 47B72187844C00AA5D524415E52E3BE81E63056B has been removed from your list."
LIST_MESSAGE = "Your nodes:\n47B72187844C00AA5D524415E52E3BE81E63056B"
STATUS_MESSAGE = "Fingerprint: 47B72187844C00AA5D524415E52E3BE81E63056B\n\
    Running...\n\
    Nickname: Aleff\n\
    Country: Germany\n\
    Bandwidth: 10.00 MBytes bytes/s\n\
    Uptime: 4 hours 39 minutes"

# Create a bot object
bot = telebot.TeleBot(TOKEN)

# Create the buttons
keyboard = types.ReplyKeyboardMarkup(row_width=2)
button_add = types.KeyboardButton("[+] Node")
button_remove = types.KeyboardButton("[-] Node")
button_list = types.KeyboardButton("List Nodes")
button_status = types.KeyboardButton("Status Nodes")
keyboard.add(button_add, button_remove, button_list, button_status)

"""
Handles the /help command
"""
@bot.message_handler(commands=['help'])
def send_help(message):
    help_message = "You can manage nodes using the following commands (by clicking the buttons):\n" \
                   "[+] Node: Add a new Node\n" \
                   "[-] Node: Remove a Node\n" \
                   "List Nodes: View the list of nodes\n" \
                   "Status Nodes: View the status of nodes"
    bot.send_message(chat_id=message.chat.id, text=help_message, reply_markup=keyboard)

"""
Handle the /start command
"""
@bot.message_handler(commands=['start'])
def send_welcome(message):
    a = "Currently for security reasons backand has been disabled so no record is saved on users using this bot not allowing them to use the service for which it was born."

    b = "Despite this, however, you can test the commands which will always return the same result which will allow you to understand what kind of functionality was intended."

    c = "Of course there is the possibility of adding many features but the basic concept is to allow users to keep track of their nodes. In fact in the whole code there is another feature not present in the demo that is to check every X seconds whether the nodes under observation are online or not."

    bot.send_message(chat_id=message.chat.id, text=a)
    bot.send_message(chat_id=message.chat.id, text=b)
    bot.send_message(chat_id=message.chat.id, text=c)
    bot.send_message(chat_id=message.chat.id, text="Demo started...")
    bot.send_message(chat_id=message.chat.id, text=START_MESSAGE)

"""
Command Manager
"""
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    # Add node
    if message.text == "[+] Node":
        bot.send_message(chat_id=message.chat.id, text=ADD_MESSAGE, reply_markup=keyboard)
    # Remove node
    elif message.text == "[-] Node":
        bot.send_message(chat_id=message.chat.id, text=REMOVE_MESSAGE, reply_markup=keyboard)
    # List nodes
    elif message.text == "List Nodes":
        bot.send_message(chat_id=message.chat.id, text=LIST_MESSAGE, reply_markup=keyboard)
    # Get nodes status
    elif message.text == "Status Nodes":
        bot.send_message(chat_id=message.chat.id, text=STATUS_MESSAGE, reply_markup=keyboard)

# Run the bot
bot.polling()
