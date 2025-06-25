import os
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime, timedelta
import random

# (Your load_dotenv, app = Flask(__name__), and SRS_INTERVALS dictionary remain the same)
load_dotenv()
app = Flask(__name__)
SRS_INTERVALS = {
    0: timedelta(minutes=0), 1: timedelta(minutes=20), 2: timedelta(minutes=45),
    3: timedelta(hours=2), 4: timedelta(hours=12), 5: timedelta(days=1),
    6: timedelta(days=5), 7: timedelta(days=14), 8: timedelta(days=30)
}

# (get_db_connection and index functions remain the same)
def get_db_connection():
    # ... (no changes here)
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

@app.route("/")
def index():
    return render_template('index.html')


# --- MODIFIED /api/question Endpoint ---
@app.route("/api/question")
def get_quiz_question():
    username = request.args.get('user')
    # ... (username and db connection checks are the same)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Find User ID
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result: return jsonify({"error": "User not found"}), 404
        user_id = user_result['id']

        word_to_quiz = None
        reason = ""

        # Priority 1: Find words that are due for review
        query = """
            SELECT w.id, w.word, up.mastery_level FROM words w
            JOIN user_progress up ON w.id = up.word_id AND up.user_id = %s
            WHERE up.next_review_date <= NOW() ORDER BY up.next_review_date ASC LIMIT 1
        """
        cursor.execute(query, (user_id,))
        word_to_quiz = cursor.fetchone()
        if word_to_quiz:
            reason = f"This word (Mastery {word_to_quiz['mastery_level']}) is due for review."

        # Priority 2: If no words are due, find a new, unseen word
        if not word_to_quiz:
            query = """
                SELECT w.id, w.word FROM words w
                WHERE w.id NOT IN (SELECT up.word_id FROM user_progress up WHERE up.user_id = %s)
                ORDER BY RAND() LIMIT 1
            """
            cursor.execute(query, (user_id,))
            word_to_quiz = cursor.fetchone()
            if word_to_quiz:
                reason = "Let's try a new word!"

        # Priority 3: If all words have been seen and none are due, review the one with the soonest review date
        if not word_to_quiz:
            query = """
                SELECT w.id, w.word, up.mastery_level FROM user_progress up
                JOIN words w ON w.id = up.word_id WHERE up.user_id = %s
                ORDER BY up.next_review_date ASC LIMIT 1
            """
            cursor.execute(query, (user_id,))
            word_to_quiz = cursor.fetchone()
            if word_to_quiz:
                reason = f"Reviewing an early word (Mastery {word_to_quiz['mastery_level']})."

        if not word_to_quiz:
            return jsonify({"error": "Could not select a word."}), 500
        
        # --- Generate Question ---
        cursor.execute("SELECT definition FROM words WHERE id = %s", (word_to_quiz['id'],))
        correct_definition = cursor.fetchone()['definition']
        cursor.execute("SELECT definition FROM words WHERE id != %s ORDER BY RAND() LIMIT 3", (word_to_quiz['id'],))
        distractors = [row['definition'] for row in cursor.fetchall()]
        
        options = distractors + [correct_definition]
        random.shuffle(options)
        
        question = {
            "user_id": user_id, "word_id": word_to_quiz['id'],
            "word": word_to_quiz['word'], "options": options,
            "correct_answer": correct_definition,
            "reason": reason  # Add the reason to the response
        }
        return jsonify(question)
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()


# --- NEW /api/stats Endpoint ---
@app.route("/api/stats")
def get_user_stats():
    username = request.args.get('user')
    if not username: return jsonify({"error": "Username required"}), 400
    
    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        # Find User ID
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result: return jsonify({"error": "User not found"}), 404
        user_id = user_result['id']
        
        # Get count of words at each mastery level
        query = """
            SELECT mastery_level, COUNT(*) as count
            FROM user_progress WHERE user_id = %s GROUP BY mastery_level
        """
        cursor.execute(query, (user_id,))
        mastery_results = cursor.fetchall()
        
        # Calculate unseen words
        cursor.execute("SELECT COUNT(*) as count FROM words")
        total_words = cursor.fetchone()['count']
        
        seen_words = sum([res['count'] for res in mastery_results])
        unseen_words = total_words - seen_words
        
        # Format the stats for easy frontend use
        stats = {f"level_{res['mastery_level']}": res['count'] for res in mastery_results}
        stats['unseen'] = unseen_words
        
        return jsonify(stats)
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()


# (/api/answer and the main execution block remain the same)
@app.route("/api/answer", methods=['POST'])
def submit_answer():
    # ... (no changes here)
    data = request.get_json()
    if not data or not all(k in data for k in ['user_id', 'word_id', 'answer']):
        return jsonify({"error": "Missing required fields"}), 400

    user_id = data['user_id']
    word_id = data['word_id']
    user_answer = data['answer']

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "DB connection failed"}), 500
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT definition FROM words WHERE id = %s", (word_id,))
        correct_answer_row = cursor.fetchone()
        if not correct_answer_row: return jsonify({"error": "Word not found"}), 404
        correct_answer = correct_answer_row['definition']

        cursor.execute("SELECT mastery_level FROM user_progress WHERE user_id = %s AND word_id = %s", (user_id, word_id))
        progress_row = cursor.fetchone()
        current_mastery = progress_row['mastery_level'] if progress_row else 0

        is_correct = (user_answer == correct_answer)
        if is_correct:
            new_mastery = min(current_mastery + 1, max(SRS_INTERVALS.keys()))
        else:
            new_mastery = max(current_mastery - 1, 0)
        
        interval = SRS_INTERVALS[new_mastery]
        next_review_date = datetime.now() + interval

        update_query = """
            INSERT INTO user_progress (user_id, word_id, mastery_level, next_review_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE mastery_level = VALUES(mastery_level), next_review_date = VALUES(next_review_date)
        """
        cursor.execute(update_query, (user_id, word_id, new_mastery, next_review_date.isoformat()))
        conn.commit()

        return jsonify({"correct": is_correct, "correct_answer": correct_answer})
    finally:
        if conn and conn.is_connected(): cursor.close(); conn.close()

if __name__ == '__main__':
    app.run(debug=True)