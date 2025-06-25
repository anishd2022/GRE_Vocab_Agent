import os
import json
from dotenv import load_dotenv
import mysql.connector

# --- Configuration ---
# The names of our source JSON files
WORDS_JSON_FILE = 'gre_words.json'
USERS_JSON_FILE = 'users.json'

def migrate_to_mysql():
    """
    Connects directly to a pre-existing MySQL database, creates tables,
    and populates them with data from local JSON files.
    """
    # Load environment variables from .env file
    load_dotenv()
    
    # --- Step 1: Connect directly to your specific database ---
    try:
        print("Connecting to your MySQL database...")
        # MODIFICATION: Added the 'database' parameter to the connection call
        db_connection = mysql.connector.connect(
            host=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_HOST'),
            user=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_USER'),
            password=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_PW'),
            port=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_PORT'),
            database=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_DBNAME') 
        )
        cursor = db_connection.cursor()
        print("Connection successful!")
    except mysql.connector.Error as err:
        print(f"FATAL ERROR: Failed to connect to MySQL database: {err}")
        print("Please check that the database name in your .env file is correct and that you have access to it.")
        return

    # --- Step 2: Create the tables (The CREATE DATABASE step has been removed) ---
    try:
        print("Creating tables: 'users', 'words', 'user_progress'...")
        
        # Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL
            )
        """)
        
        # Words Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS words (
                id INT AUTO_INCREMENT PRIMARY KEY,
                word VARCHAR(255) UNIQUE NOT NULL,
                definition TEXT,
                example TEXT
            )
        """)
        
        # User Progress Table (linking users and words)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INT,
                word_id INT,
                mastery_level INT DEFAULT 0,
                next_review_date DATETIME,
                PRIMARY KEY (user_id, word_id),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
            )
        """)
        db_connection.commit()
        print("Tables created successfully.")
    except mysql.connector.Error as err:
        print(f"FATAL ERROR: Failed to create tables: {err}")
        db_connection.close()
        return
        
    # --- Step 3: Load data from JSON and populate the tables ---
    try:
        print("Populating 'words' table...")
        with open(WORDS_JSON_FILE, 'r', encoding='utf-8') as f:
            words_data = json.load(f)
        
        word_insert_query = "INSERT IGNORE INTO words (word, definition, example) VALUES (%s, %s, %s)"
        for word_item in words_data:
            cursor.execute(word_insert_query, (word_item['word'], word_item['definition'], word_item.get('example', '')))
        db_connection.commit()
        print(f"Populated {len(words_data)} words.")

        print("Populating 'users' and 'user_progress' tables...")
        with open(USERS_JSON_FILE, 'r', encoding='utf-8') as f:
            users_data = json.load(f)
            
        for username, data in users_data.items():
            # Insert user and get their new ID
            cursor.execute("INSERT IGNORE INTO users (username) VALUES (%s)", (username,))
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_id = cursor.fetchone()[0]

            # Insert their progress
            for word, progress in data.get('progress', {}).items():
                cursor.execute("SELECT id FROM words WHERE word = %s", (word,))
                word_result = cursor.fetchone()
                if word_result:
                    word_id = word_result[0]
                    cursor.execute(
                        """
                        INSERT IGNORE INTO user_progress (user_id, word_id, mastery_level, next_review_date)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (user_id, word_id, progress.get('mastery_level'), progress.get('next_review_date'))
                    )
        db_connection.commit()
        print(f"Populated data for {len(users_data)} users.")

    except FileNotFoundError as err:
        print(f"Warning: Could not find JSON file: {err}. Skipping population for that file.")
    except Exception as err:
        print(f"An error occurred during data population: {err}")
    
    # --- Final step: Close the connection ---
    finally:
        cursor.close()
        db_connection.close()
        print("\nMigration complete! Database connection closed.")


if __name__ == "__main__":
    migrate_to_mysql()