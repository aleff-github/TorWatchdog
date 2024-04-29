import telebot
from telebot import types
import configparser
import sqlite3
import re
import requests
from datetime import datetime
import threading
from time import sleep
import logging
import random


# Read the Telegram TOKEN
config = configparser.ConfigParser()
config.read('config.ini')
TOKEN = config['telegram']['token']

# Fingerprint Pattern
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


# Logger configuration
logging.basicConfig(filename='error.log', level=logging.ERROR)

def check_relay_status(user_id, fingerprint):
    """
    Checks the status of a Tor relay with the given fingerprint.

    Args:
        user_id (int): The ID of the user to whom the status message will be sent.
        fingerprint (str): The fingerprint of the Tor relay to check.

    Returns:
        None

    Raises:
        None

    Sends a message to the user indicating the status of the Tor relay with the given fingerprint.
    If the relay is offline, it sends a message indicating that it's offline.
    If there is no information available for the fingerprint, it sends a corresponding message.
    If an error occurs while fetching information for the fingerprint, it sends an error message.

    Note:
        This function assumes the existence of the `ONIONOO` variable, which is the URL of the Onionoo service.
        It also assumes the existence of the `bot` object, which is used to send messages to users.
    """
    try:
        response = requests.get(f"{ONIONOO}{fingerprint}")

        if response.status_code == 200:
            data = response.json()
            relays = data.get('relays', [])

            if relays:
                relay = relays[0]
                is_running = relay.get("running", False)

                if not is_running:
                    message = f"The relay with fingerprint `{fingerprint}` is offline"
            else:
                message = f"No information available for fingerprint: `{fingerprint}`"
        else:
            message = f"Failed to fetch information for fingerprint: `{fingerprint}`"
    except requests.RequestException as e:
        message = f"Error fetching information for fingerprint `{fingerprint}`: {e}"

    bot.send_message(user_id, message, parse_mode='MarkdownV2')

def run_thread():
    """
    Executes a thread to continuously check the status of Tor relays.

    Connects to the SQLite database 'tor_watchdog.db' using a context.
    Retrieves records from the 'TorWatchdog' table and checks the status of Tor relays.
    Sleeps for 12 hours after processing all records.

    Args:
        None

    Returns:
        None

    Raises:
        None

    Note:
        This function continuously runs in a loop to monitor the status of Tor relays.
        It fetches records from the 'TorWatchdog' table and checks the status of relays associated with each user.
        If an error occurs during the execution of the thread, it logs the error using the logging module.

    Debugging:
        During debugging, the sleep time can be reduced to 5 seconds by uncommenting the line 'sleep(5)'.
    """
    try:
        # Connecting to the SQLite database using a context
        with sqlite3.connect('tor_watchdog.db') as conn:
            cursor = conn.cursor()

            while True:
                # Selecting records from the TorWatchdog table
                cursor.execute('SELECT * FROM TorWatchdog')
                rows = cursor.fetchall()

                for row in rows:
                    user_id, node_list = row
                    fingerprints = node_list.split()

                    for fingerprint in fingerprints:
                        check_relay_status(user_id, fingerprint)

                # Sleep for 12 
                sleep(43200)
                # Sleep for 5 seconds Debugging
                #sleep(5)
    except Exception as e:
        # Error log instead of printing it to stdout
        logging.error("Error during thread execution: %s", e)

# Start the thread
thread = threading.Thread(target=run_thread)
thread.daemon = True
thread.start()


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """
    Handles the 'start' command by registering the user in the database if not already registered.

    Connects to the SQLite database 'tor_watchdog.db' using a context.
    Creates the 'TorWatchdog' table if it does not already exist.
    Checks if the user is already in the database.
    Inserts a new record into the database if the user is not found.
    Sends a welcome message to the user indicating whether their ID is registered or not.

    Args:
        message: The message object representing the 'start' command.

    Returns:
        None

    Raises:
        None

    Note:
        This function is triggered when the user sends the '/start' command to the bot.
        It checks if the user is already registered in the database and registers them if not.
        If an error occurs during the execution of the function, it is logged using the logging module.
    """
    try:
        # Connecting to the SQLite database using a context
        with sqlite3.connect('tor_watchdog.db') as conn:
            cursor = conn.cursor()

            # Creating the table if it does not already exist
            cursor.execute('''CREATE TABLE IF NOT EXISTS TorWatchdog (
                                TelegramUserID INTEGER PRIMARY KEY,
                                NodeList TEXT
                                )''')

            user_id = message.from_user.id
            # Checks whether the user is already in the database
            cursor.execute('SELECT * FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
            user_exists = cursor.fetchone()

            if not user_exists:
                # Inserting a new tuple into the database for the user
                cursor.execute('INSERT INTO TorWatchdog (TelegramUserID, NodeList) VALUES (?, ?)', (user_id, ''))
                bot.reply_to(message, "Welcome! Your ID has been registered in the database", reply_markup=keyboard, parse_mode='MarkdownV2')
            else:
                bot.reply_to(message, "Welcome back! Your ID is already in the database", reply_markup=keyboard, parse_mode='MarkdownV2')

            # Commit changes to the database
            conn.commit()
    except Exception as e:
        # Error management
        logging.error("Error during the start function: %s", e)

def add_node_fingerprint(message):
    """
    Adds a node fingerprint to the user's list of monitored nodes.

    Extracts the user ID and fingerprint from the message object.
    Checks if the fingerprint matches the expected pattern using FINGERPRINT_PATTERN.
    Connects to the SQLite database 'tor_watchdog.db' using a context.
    Retrieves the existing node list for the user from the 'TorWatchdog' table.
    Checks if the node fingerprint is already in the user's list.
    If the fingerprint is not in the list, adds it to the list and updates the database.
    Sends a confirmation message to the user indicating that the node has been added.

    Args:
        message: The message object containing the user ID and fingerprint.

    Returns:
        None

    Raises:
        None

    Note:
        This function is typically triggered when the user adds a new node fingerprint.
        It ensures that the fingerprint matches the expected format and updates the user's list in the database.
        If an error occurs during database access, it is logged using the logging module.
    """
    user_id = message.from_user.id
    fingerprint = message.text.strip()

    if FINGERPRINT_PATTERN.match(fingerprint):
        try:
            # Connecting to the SQLite database using a context
            with sqlite3.connect('tor_watchdog.db') as conn:
                cursor = conn.cursor()

                # Retrieves the existing node list for the user
                cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
                row = cursor.fetchone()
                node_list = row[0] if row else ""

                # Checks whether the node has already been entered
                if fingerprint in node_list.split():
                    bot.reply_to(message, rf"The node you indicated is already in the list of nodes you are checking", parse_mode='MarkdownV2')
                else:
                    # Add fingerprint to the node list, separating with a space
                    node_list += (" " if node_list else "") + fingerprint

                    # Update the list of nodes in the database
                    cursor.execute('UPDATE TorWatchdog SET NodeList = ? WHERE TelegramUserID = ?', (node_list, user_id))
                    conn.commit()

                    bot.reply_to(message, rf"The node with fingerprint `{fingerprint}` has been added to your list", parse_mode='MarkdownV2')
        except sqlite3.Error as e:
            logging.error("An error occurred while accessing the database: %s", e)
    else:
        logging.error("The fingerprint you indicated does not match the expected format")

def remove_node_fingerprint(message):
    """
    Removes a node fingerprint from the user's list of monitored nodes.

    Extracts the user ID and fingerprint from the message object.
    Checks if the fingerprint matches the expected pattern using FINGERPRINT_PATTERN.
    Connects to the SQLite database 'tor_watchdog.db' using a context.
    Retrieves the existing node list for the user from the 'TorWatchdog' table.
    Removes the fingerprint from the node list if present.
    Updates the database with the modified node list.
    Sends a confirmation message to the user indicating that the node has been removed.

    Args:
        message: The message object containing the user ID and fingerprint.

    Returns:
        None

    Raises:
        None

    Note:
        This function is typically triggered when the user removes a node fingerprint.
        It ensures that the fingerprint matches the expected format and updates the user's list in the database.
        If the fingerprint is not found in the list, it sends a corresponding message to the user.
        If an error occurs during database access, it is logged using the logging module.
    """
    user_id = message.from_user.id
    fingerprint = message.text.strip()

    if FINGERPRINT_PATTERN.match(fingerprint):
        try:
            # Connecting to the SQLite database using a context
            with sqlite3.connect('tor_watchdog.db') as conn:
                cursor = conn.cursor()

                # Retrieves the existing node list for the user
                cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
                row = cursor.fetchone()
                if row:
                    node_list = row[0]
                    
                    # Removes the fingerprint from the node list, if present
                    node_list = node_list.replace(" " + fingerprint, "").replace(fingerprint, "")
                    node_list = node_list.strip()

                    # Update the list of nodes in the database
                    cursor.execute('UPDATE TorWatchdog SET NodeList = ? WHERE TelegramUserID = ?', (node_list, user_id))
                    conn.commit()

                    bot.reply_to(message, rf"The node with fingerprint `{fingerprint}` has been removed from your list", parse_mode='MarkdownV2')
                else:
                    bot.reply_to(message, rf"You don't have any nodes in your list", parse_mode='MarkdownV2')
        except sqlite3.Error as e:
            logging.error("An error occurred while accessing the database: %s", e)
    else:
        bot.reply_to(message, rf"The fingerprint you indicated does not match the expected format", parse_mode='MarkdownV2')

def list_nodes(message):
    """
    Lists the nodes registered by the user.

    Extracts the user ID from the message object.
    Connects to the SQLite database 'tor_watchdog.db' using a context.
    Retrieves the node list for the user from the 'TorWatchdog' table.
    Formats the node list and sends it as a message to the user.

    Args:
        message: The message object representing the user's request.

    Returns:
        None

    Raises:
        None

    Note:
        This function is typically triggered when the user requests to list their registered nodes.
        It retrieves the node list from the database, formats it, and sends it as a reply to the user.
        If the user is not registered in the database, it sends a corresponding message.
        If an error occurs during database access, it is logged using the logging module.
    """
    user_id = message.from_user.id

    try:
        # Connecting to the SQLite database using a context
        with sqlite3.connect('tor_watchdog.db') as conn:
            cursor = conn.cursor()

            # Retrieve the node list for the user
            cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
            row = cursor.fetchone()

            if row:
                node_list = row[0]

                if node_list:
                    # Split of the node list into individual fingerprints and sorting
                    fingerprints = sorted(node_list.split())

                    # Creating a formatted list of fingerprints
                    formatted_list = "\n".join([rf"\- `{fingerprint}`" for fingerprint in fingerprints])
                    reply_message = f"Your nodes:\n{formatted_list}"
                else:
                    reply_message = "You have no nodes in your list"
            else:
                reply_message = "You are not registered in the database. Please use /start command to register"

            bot.reply_to(message, text=reply_message, parse_mode='MarkdownV2')
    except sqlite3.Error as e:
        logging.error("An error occurred while accessing the database: %s", e)

def convert_bandwidth(bandwidth_rate):
    """
    Converts the given bandwidth rate to a human-readable format.

    Args:
        bandwidth_rate (int): The bandwidth rate to be converted, in bytes per second.

    Returns:
        str: A string representing the converted bandwidth rate in a human-readable format.

    Raises:
        None

    Note:
        This function calculates the appropriate unit prefix (Bytes, KBytes, MBytes, GBytes) 
        for the given bandwidth rate and formats the result accordingly.
    """
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

def get_uptime(last_restarted):
    """
    Calculates the uptime based on the last restart time.

    Args:
        last_restarted (str): The timestamp of the last restart in ISO 8601 format.

    Returns:
        str: A string representing the uptime in a human-readable format.

    Raises:
        None

    Note:
        This function calculates the uptime based on the difference between the current time and the last restart time.
        It converts the time difference into days, hours, minutes, and seconds, and formats the result accordingly.
        If the uptime exceeds one month, it also calculates the number of months.
    """
    delta = datetime.now() - datetime.fromisoformat(last_restarted)
    raw = delta.total_seconds()
    days = int(raw // (24 * 3600))
    hours = int((raw % (24 * 3600)) // 3600)
    minutes = int((raw % 3600) // 60)
    seconds = int(raw % 60)

    # Calculate the number of months
    months = days // 30
    remaining_days = days % 30

    # Format the output
    formatted_time = ""

    if months > 0:
        formatted_time = "{:d} months, {:d} days, {:02d}:{:02d}:{:02d}".format(months, remaining_days, hours, minutes, seconds)
    elif days > 0:
        formatted_time = "{:d} days, {:02d}:{:02d}:{:02d}".format(remaining_days, hours, minutes, seconds)
    else:
        formatted_time = "{:02d}:{:02d}:{:02d}".format(hours, minutes, seconds)

    return formatted_time

def get_status_of_relay(fingerprint):
    """
    Retrieves the status of a relay based on its fingerprint.

    Args:
        fingerprint (str): The fingerprint of the relay.

    Returns:
        str: A string containing the status information of the relay in a formatted manner.

    Raises:
        None

    Note:
        This function makes a request to the Onionoo API to fetch information about the relay.
        It then extracts relevant information such as status, nickname, country, bandwidth, and uptime.
        If the request is successful and the relay information is available, it formats the status information accordingly.
        If the request fails or encounters an exception, it logs an error message.
    """
    relay_status = ""
    try:
        response = requests.get(f"{ONIONOO}{fingerprint}")

        if response.status_code == 200:
            data = response.json()
            if 'relays' in data and data['relays']:
                relay = data['relays'][0]
                uptime = get_uptime(relay.get('last_restarted', ''))

                relay_status = f"Fingerprint: `{fingerprint}`\n" \
                                    f"Status: {'Running ✅' if relay.get('running') else 'Offline ❌'}\n" \
                                    f"Nickname: {relay.get('nickname', 'N/A')}\n" \
                                    f"Country: {relay.get('country_name', 'N/A')}\n" \
                                    f"Bandwidth: {convert_bandwidth(relay.get('bandwidth_rate'))} bytes/s\n" \
                                    f"Uptime: {uptime}"
            else:
                relay_status = rf"No information available for fingerprint: `{fingerprint}`"
        else:
            relay_status = rf"Failed to fetch information for fingerprint: `{fingerprint}`"
        
        return relay_status.replace(".", "\.")
    except requests.RequestException as e:
        logging.error(rf"Error fetching information for fingerprint {fingerprint}: {e}")

def verify_all_nodes_status(message):
    """
    Verifies the status of all nodes registered by the user and sends the status information as messages.

    Args:
        message: The message object representing the user's request.

    Returns:
        None

    Raises:
        None

    Note:
        This function retrieves the node list for the user from the SQLite database.
        It then iterates through each node in the list, fetching and sending its status information using the `get_status_of_relay` function.
        If the user is not registered in the database, it sends a corresponding message.
        If an error occurs during database access, it sends an error message to the user.
    """
    user_id = message.from_user.id

    try:
        # Connecting to the SQLite database using a context
        with sqlite3.connect('tor_watchdog.db') as conn:
            cursor = conn.cursor()

            # Retrieve the node list for the user
            cursor.execute('SELECT NodeList FROM TorWatchdog WHERE TelegramUserID = ?', (user_id,))
            row = cursor.fetchone()

            relay_status = ""

            if row:
                node_list = row[0]

                if node_list:
                    fingerprints = node_list.split()

                    for fingerprint in fingerprints:
                        relay_status = get_status_of_relay(fingerprint=fingerprint)
                        bot.send_message(chat_id=user_id, text=relay_status, parse_mode='MarkdownV2')
                else:
                    relay_status = "You have no nodes in your list"
            else:
                relay_status = "You are not registered in the database. Please use /start command to register"
    except sqlite3.Error as e:
        bot.reply_to(message, rf"An error occurred while accessing the database: {e}", parse_mode='MarkdownV2')

@bot.message_handler(func=lambda message: True)
def handle_buttons(message):
    """
    Handles button commands received from the user.

    Parses the message text and routes it to the appropriate function based on the command.
    Supports commands such as adding a node, removing a node, listing nodes, checking nodes' status,
    displaying help, and providing guidance on using the correct format.

    Args:
        message: The message object containing the user's command.

    Returns:
        None

    Raises:
        None

    Note:
        This function is a handler for button commands received from the user.
        It checks the text of the message against predefined commands and invokes corresponding functions.
        If the message text does not match any command, it provides guidance on using the correct format.
    """
    # Add node
    if message.text == "[+] Node":
        bot.reply_to(message, "Write down the fingerprint of the node you want to look at", parse_mode='MarkdownV2')
        bot.register_next_step_handler(message, add_node_fingerprint)
    # Remove node
    elif message.text == "[-] Node":
        bot.reply_to(message, "Write the fingerprint of the node you no longer want to control", parse_mode='MarkdownV2')
        bot.register_next_step_handler(message, remove_node_fingerprint)
    # List nodes
    elif message.text == "List Nodes":
        list_nodes(message=message)
    # Get nodes status
    elif message.text == "Status Nodes":
        verify_all_nodes_status(message=message)
    elif message.text == "/help":
        send_help(message)
    else:
        bot.reply_to(message=message, text="Please respect the required format, if you don't know the formats invoke the /help command")


@bot.message_handler(commands=['help'])
def send_help(message):
    """
    Handles the /help command
    """
    help_message = "You can manage nodes using the following commands (By clicking on the buttons):\n" \
                   "[+] Node: Add a new Node\n" \
                   "[-] Node: Remove a Node\n" \
                   "List Nodes: View the list of nodes\n" \
                   "Status Nodes: View the status of nodes"
    bot.reply_to(message, help_message, reply_markup=keyboard)

# Run the bot
bot.infinity_polling()
