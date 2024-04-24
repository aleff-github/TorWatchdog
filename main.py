import telebot
from telebot import types
import configparser
import sqlite3


# Read the Telegram TOKEN
config = configparser.ConfigParser()
config.read('config.ini')
TOKEN = config['telegram']['token']

# Crea un oggetto bot
bot = telebot.TeleBot(TOKEN)



# Memorizza i nodi
nodes = []

# Crea i pulsanti
keyboard = types.ReplyKeyboardMarkup(row_width=2)
button_add = types.KeyboardButton("[+] Node")
button_remove = types.KeyboardButton("[-] Node")
button_list = types.KeyboardButton("List Nodes")
button_status = types.KeyboardButton("Status Nodes")
keyboard.add(button_add, button_remove, button_list, button_status)

# Handle the /start command
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Connessione al database SQLite
    conn = sqlite3.connect('tor_watchdog.db')
    cursor = conn.cursor()

    # Creazione della tabella se non esiste già
    cursor.execute('''CREATE TABLE IF NOT EXISTS TorWatchdog (
                    TelegramUserID INTEGER PRIMARY KEY,
                    NodeList TEXT
                    )''')
    conn.commit()

    user_id = message.from_user.id
    # Check if the user is already in the database
    cursor.execute('SELECT * FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
    user_exists = cursor.fetchone()
    if not user_exists:
        # Insert a new tuple into the database for the user
        cursor.execute('INSERT INTO TorWatchdog (TelegramUserID, NodeList) VALUES (?, ?)', (user_id, ''))
        conn.commit()
        bot.reply_to(message, "Welcome! Your ID has been registered in the database.", reply_markup=keyboard)
    else:
        bot.reply_to(message, "Welcome back! Your ID is already in the database.", reply_markup=keyboard)

    # Close the database connection
    conn.close()

# Function to handle the fingerprint of the node
def add_node_fingerprint(message):
    user_id = message.from_user.id
    fingerprint = message.text.strip()
    
    # Connection to the SQLite database
    conn = sqlite3.connect('tor_watchdog.db')
    cursor = conn.cursor()

    # Retrieve the existing node list for the user
    cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
    node_list = cursor.fetchone()[0]

    # Add the fingerprint to the node list, separating with space
    node_list += (" " if node_list else "") + fingerprint

    # Update the node list in the database
    cursor.execute('UPDATE TorWatchdog SET NodeList = ? WHERE TelegramUserID = ?', (node_list, user_id))
    conn.commit()

    bot.reply_to(message, f"The node with fingerprint {fingerprint} has been added to your list.")

    # Close the database connection
    conn.close()

# Gestisce l'aggiunta e la rimozione dei nodi
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    if message.text == "[+] Node":
        bot.reply_to(message, "Write down the fingerprint of the node you want to look at.")
        # Registering the user's response as a handler
        bot.register_next_step_handler(message, add_node_fingerprint)
    elif message.text == "[-] Node":
        if nodes:
            nodes.pop()
            bot.reply_to(message, "Node successfully removed.", reply_markup=keyboard)
        else:
            bot.reply_to(message, "No nodes to be removed.", reply_markup=keyboard)
    elif message.text == "List Nodes":
        if nodes:
            nodes_list = "\n".join(nodes)
            bot.reply_to(message, f"The nodes are:\n{nodes_list}", reply_markup=keyboard)
        else:
            bot.reply_to(message, "No nodes present.", reply_markup=keyboard)
    elif message.text == "Status Nodes":
        if nodes:
            bot.reply_to(message, f"The number of nodes is: {len(nodes)}", reply_markup=keyboard)
        else:
            bot.reply_to(message, "No nodes present.", reply_markup=keyboard)

# Gestisce il comando /help
@bot.message_handler(commands=['help'])
def send_help(message):
    help_message = "You can manage nodes using the following commands:\n" \
                   "[+] Node: Add a new Node\n" \
                   "[-] Node: Remove a Node\n" \
                   "List Nodes: View the list of nodes\n" \
                   "Status Nodes: View the status of nodes"
    bot.reply_to(message, help_message, reply_markup=keyboard)

# Avvia il bot
bot.polling()
