import telebot
from telebot import types
import configparser
import sqlite3
import re
import requests
from datetime import datetime
import threading
from time import sleep


# Read the Telegram TOKEN
config = configparser.ConfigParser()
config.read('config.ini')
TOKEN = config['telegram']['token']
FINGERPRINT_REGEX = "^[A-Za-z0-9]{40}$"
FINGERPRINT_PATTERN = re.compile(FINGERPRINT_REGEX)
ONIONOO = "https://onionoo.torproject.org/details?search="

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
Function to check relay status
"""
def check_relay_status(user_id, fingerprint):
    response = requests.get(f"{ONIONOO}{fingerprint}")
    if response.status_code == 200:
        data = response.json()
        if 'relays' in data and len(data['relays']) > 0:
            relay = data['relays'][0]
            if relay.get("running", False) == False:
                bot.send_message(user_id, f"The relay with fingerprint {fingerprint} is offline.")
            else:
                bot.send_message(user_id, f"Debug: Relay {fingerprint} online")
        else:
            bot.send_message(user_id, f"No information available for fingerprint: {fingerprint}")
    else:
        bot.send_message(user_id, f"Failed to fetch information for fingerprint: {fingerprint}")

"""
Function to run the thread
"""
def run_thread():
    # Connection to the SQLite database
    conn = sqlite3.connect('tor_watchdog.db')
    cursor = conn.cursor()

    while True:
        try:
            # Retrieve all tuples from the database
            cursor.execute('SELECT * FROM TorWatchdog')
            rows = cursor.fetchall()

            # For each tuple, check the status of each fingerprint
            for row in rows:
                user_id = row[0]
                node_list = row[1]
                fingerprints = node_list.split()

                for fingerprint in fingerprints:
                    check_relay_status(user_id, fingerprint)

            # Sleep for 12 hours
            sleep(43200)
        except Exception as e:
            print("Error:", e)

# Start the thread
thread = threading.Thread(target=run_thread)
thread.daemon = True
thread.start()

"""
Handle the /start command
"""
@bot.message_handler(commands=['start'])
def send_welcome(message):
    # Connection to SQLite database
    conn = sqlite3.connect('tor_watchdog.db')
    cursor = conn.cursor()

    # Creating the table if it does not already exist
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

"""
Function to handle the fingerprint of the node
"""
def add_node_fingerprint(message):
    user_id = message.from_user.id
    fingerprint = message.text.strip()

    if FINGERPRINT_PATTERN.match(fingerprint):
        # Connection to the SQLite database
        conn = sqlite3.connect('tor_watchdog.db')
        cursor = conn.cursor()

        # Retrieve the existing node list for the user
        cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
        node_list = cursor.fetchone()[0]

        # Checks whether the node has already been entered
        if fingerprint in node_list:
            bot.reply_to(message, f"The node you indicated is already in the list of nodes you are checking.")
        else:
            # Add the fingerprint to the node list, separating with space
            node_list += (" " if node_list else "") + fingerprint

            # Update the node list in the database
            cursor.execute('UPDATE TorWatchdog SET NodeList = ? WHERE TelegramUserID = ?', (node_list, user_id))
            conn.commit()

            bot.reply_to(message, f"The node with fingerprint {fingerprint} has been added to your list.")

        # Close the database connection
        conn.close()
    else:
        bot.reply_to(message, f"The fingerprint you indicated does not match the expected format.")

"""
Function to handle the fingerprint of the node to be removed
"""
def remove_node_fingerprint(message):
    user_id = message.from_user.id
    fingerprint = message.text.strip()
    
    if FINGERPRINT_PATTERN.match(fingerprint):
        # Connection to the SQLite database
        conn = sqlite3.connect('tor_watchdog.db')
        cursor = conn.cursor()

        # Retrieve the existing node list for the user
        cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
        node_list = cursor.fetchone()[0]

        # Remove the fingerprint from the node list, if present
        node_list = node_list.replace(" " + fingerprint, "").replace(fingerprint, "")
        node_list = node_list.strip()

        # Update the node list in the database
        cursor.execute('UPDATE TorWatchdog SET NodeList = ? WHERE TelegramUserID = ?', (node_list, user_id))
        conn.commit()

        bot.reply_to(message, f"(If present...) The node with fingerprint {fingerprint} has been removed from your list.")

        # Close the database connection
        conn.close()
    else:
        bot.reply_to(message, f"The fingerprint you indicated does not match the expected format.")

"""
List all the nodes you are observing
"""
def list_nodes(message):
    user_id = message.from_user.id

    # Connection to the SQLite database
    conn = sqlite3.connect('tor_watchdog.db')
    cursor = conn.cursor()

    # Retrieve the node list for the user
    cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
    node_list = cursor.fetchone()[0]

    # Close the database connection
    conn.close()

    if node_list:
        # Split the node list into individual fingerprints
        fingerprints = sorted(node_list.split())

        # Create a formatted list of fingerprints
        formatted_list = "\n-".join(fingerprints)

        reply_message = f"Your nodes:\n{formatted_list}"
    else:
        reply_message = "You have no nodes in your list."

    bot.reply_to(message, reply_message)

def convert_bandwidth(bandwidth_rate):
    # Define prefixes for unit measurements
    prefixes = {
        0: 'Bytes',
        1: 'KBytes',
        2: 'MBytes',
        3: 'GBytes'
    }

    # Initialize the prefix index
    prefix_index = 0

    # Calculate the correct prefix
    while bandwidth_rate >= 1024 and prefix_index < 3:
        bandwidth_rate /= 1024
        prefix_index += 1

    # Format the result
    result = f"{bandwidth_rate:.2f} {prefixes[prefix_index]}"

    return result

"""
Verify all nodes status
"""
def verify_all_nodes_status(message):
    user_id = message.from_user.id

    # Connection to the SQLite database
    conn = sqlite3.connect('tor_watchdog.db')
    cursor = conn.cursor()

    # Retrieve the node list for the user
    cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
    node_list = cursor.fetchone()[0]

    # Close the database connection
    conn.close()

    if node_list:
        # Split the node list into individual fingerprints
        fingerprints = node_list.split()

        # Perform a GET request for each fingerprint
        status_messages = []
        for fingerprint in fingerprints:
            response = requests.get(f"{ONIONOO}{fingerprint}")
            if response.status_code == 200:
                data = response.json()
                if 'relays' in data and len(data['relays']) > 0:
                    relay = data['relays'][0]
                    row_date = datetime.now() - datetime.fromisoformat(relay.get('last_restarted'))
                    status_message = f"Fingerprint: {fingerprint}\n" \
                                     f"{"Running..." if relay.get("running") else "Offline!"}\n" \
                                     f"Nickname: {relay.get('nickname', 'N/A')}\n" \
                                     f"Country: {relay.get('country_name', 'N/A')}\n" \
                                     f"Bandwidth: {convert_bandwidth(relay.get('bandwidth_rate'))} bytes/s\n" \
                                     f"Uptime: {f"{row_date.days} days" if row_date.days > 0 else f"{row_date.seconds // 3600} hours {(row_date.seconds % 3600) // 60} minutes"}"
                    status_messages.append(status_message)
                else:
                    status_messages.append(f"No information available for fingerprint: {fingerprint}")
            else:
                status_messages.append(f"Failed to fetch information for fingerprint: {fingerprint}")

        reply_message = "\n\n".join(status_messages)
    else:
        reply_message = "You have no nodes in your list."

    bot.reply_to(message, reply_message)

"""
Command Manager
"""
@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    # Add node
    if message.text == "[+] Node":
        bot.reply_to(message, "Write down the fingerprint of the node you want to look at.")
        bot.register_next_step_handler(message, add_node_fingerprint)
    # Remove node
    elif message.text == "[-] Node":
        bot.reply_to(message, "Write the fingerprint of the node you no longer want to control.")
        bot.register_next_step_handler(message, remove_node_fingerprint)
    # List nodes
    elif message.text == "List Nodes":
        list_nodes(message=message)
    # Get nodes status
    elif message.text == "Status Nodes":
        verify_all_nodes_status(message=message)

"""
Handles the /help command
"""
@bot.message_handler(commands=['help'])
def send_help(message):
    help_message = "You can manage nodes using the following commands:\n" \
                   "[+] Node: Add a new Node\n" \
                   "[-] Node: Remove a Node\n" \
                   "List Nodes: View the list of nodes\n" \
                   "Status Nodes: View the status of nodes"
    bot.reply_to(message, help_message, reply_markup=keyboard)

# Run the bot
bot.polling()
