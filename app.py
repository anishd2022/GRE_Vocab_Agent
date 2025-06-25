import os
from flask import Flask, jsonify, request
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime, timedelta
import random

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# --- SRS Configuration ---
# Mastery Level -> Time until next review
SRS_INTERVALS = {
    0: timedelta(minutes=0),   # Immediately available
    1: timedelta(minutes=20),  # 20 minutes
    2: timedelta(minutes=45),  # 45 minutes
    3: timedelta(hours=2),     # 2 hours
    4: timedelta(hours=12),    # 12 hours
    5: timedelta(days=1),      # 1 day
    6: timedelta(days=5),      # 5 days
    7: timedelta(days=14),     # 2 weeks
    8: timedelta(days=30)      # 1 month (approximated)
}


# --- Database Connection Function ---
def get_db_connection():
    """Creates and returns a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(
            host=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_HOST'),
            user=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_USER'),
            password=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_PW'),
            port=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_PORT'),
            database=os.environ.get('UCMAS_AWS_AD141_DB_ADMIN_DBNAME') 
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Something went wrong: {err}")
        return None

# --- API Endpoints ---
@app.route("/")
def index():
    """A simple endpoint to show that the API is running."""
    return jsonify({"status": "API is running. Use /api/question and /api/answer."})


@app.route("/api/question")
def get_quiz_question():
    """
    Gets a quiz question for a given user based on the SRS algorithm.
    Expects a username as a query parameter, e.g., /api/question?user=anish
    """
    username = request.args.get('user')
    if not username:
        return jsonify({"error": "Username must be provided as a query parameter. e.g., ?user=your_name"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)

    try:
        # --- Find User ID ---
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"error": "User not found"}), 404
        user_id = user_result['id']

        # --- SRS Logic using SQL to select a word ---
        # (This logic remains the same as before)
        query = """
            SELECT w.id, w.word, up.next_review_date
            FROM words w
            LEFT JOIN user_progress up ON w.id = up.word_id AND up.user_id = %s
            WHERE up.next_review_date <= NOW() OR up.next_review_date IS NULL
            ORDER BY up.next_review_date ASC
            LIMIT 1
        """
        cursor.execute(query, (user_id,))
        word_to_quiz = cursor.fetchone()

        if not word_to_quiz:
            query = """
                SELECT w.id, w.word, up.next_review_date
                FROM user_progress up JOIN words w ON w.id = up.word_id
                WHERE up.user_id = %s ORDER BY up.next_review_date ASC LIMIT 1
            """
            cursor.execute(query, (user_id,))
            word_to_quiz = cursor.fetchone()

        if not word_to_quiz:
            return jsonify({"error": "Could not select a word to quiz. Check user progress."}), 500
            
        # --- Generate Question (Word and Distractors) ---
        cursor.execute("SELECT definition FROM words WHERE id = %s", (word_to_quiz['id'],))
        correct_definition = cursor.fetchone()['definition']
        
        cursor.execute("SELECT definition FROM words WHERE id != %s ORDER BY RAND() LIMIT 3", (word_to_quiz['id'],))
        distractors = [row['definition'] for row in cursor.fetchall()]
        
        options = distractors + [correct_definition]
        random.shuffle(options)
        
        question = {
            "user_id": user_id, # Also return user_id for convenience
            "word_id": word_to_quiz['id'],
            "word": word_to_quiz['word'],
            "options": options
        }
        
        return jsonify(question)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# --- NEW: The endpoint to submit an answer ---
@app.route("/api/answer", methods=['POST'])
def submit_answer():
    """
    Submits an answer for a user and word, and updates their SRS progress.
    Expects a JSON body with: user_id, word_id, and answer.
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['user_id', 'word_id', 'answer']):
        return jsonify({"error": "Missing required fields: user_id, word_id, answer"}), 400

    user_id = data['user_id']
    word_id = data['word_id']
    user_answer = data['answer']

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)

    try:
        # --- Step 1: Get the correct answer and current mastery level ---
        cursor.execute("SELECT definition FROM words WHERE id = %s", (word_id,))
        correct_answer_row = cursor.fetchone()
        if not correct_answer_row:
            return jsonify({"error": "Word not found"}), 404
        correct_answer = correct_answer_row['definition']

        cursor.execute("SELECT mastery_level FROM user_progress WHERE user_id = %s AND word_id = %s", (user_id, word_id))
        progress_row = cursor.fetchone()
        current_mastery = progress_row['mastery_level'] if progress_row else 0

        # --- Step 2: Check if the answer is correct and calculate new mastery ---
        is_correct = (user_answer == correct_answer)
        if is_correct:
            new_mastery = min(current_mastery + 1, max(SRS_INTERVALS.keys()))
        else:
            new_mastery = max(current_mastery - 1, 0)
        
        # --- Step 3: Calculate new review date and update the database ---
        interval = SRS_INTERVALS[new_mastery]
        next_review_date = datetime.now() + interval

        update_query = """
            INSERT INTO user_progress (user_id, word_id, mastery_level, next_review_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                mastery_level = VALUES(mastery_level),
                next_review_date = VALUES(next_review_date)
        """
        cursor.execute(update_query, (user_id, word_id, new_mastery, next_review_date.isoformat()))
        conn.commit()

        # --- Step 4: Return feedback to the user ---
        return jsonify({
            "correct": is_correct,
            "correct_answer": correct_answer
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()


# --- Main execution block ---
if __name__ == '__main__':
    app.run(debug=True)