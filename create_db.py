import sqlite3

def create_database():
    # Connessione al database (crea il database se non esiste)
    conn = sqlite3.connect('tor_watchdog.db')
    c = conn.cursor()

    # Creazione della tabella TorWatchdog
    c.execute('''CREATE TABLE IF NOT EXISTS TorWatchdog
                 (TelegramUserID INTEGER PRIMARY KEY,
                 NodeList TEXT)''')

    # Chiusura della connessione
    conn.close()

if __name__ == "__main__":
    create_database()
    print("Database successfully created.")
