import os
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime, timedelta, timezone
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


# --- NEW /api/login Endpoint ---
@app.route("/api/login", methods=['POST'])
def handle_login():
    """
    Handles user login and registration.
    Now pre-populates progress for new users.
    """
    data = request.get_json()
    if not data or not all(k in data for k in ['username', 'mode']):
        return jsonify({"error": "Missing 'username' or 'mode'"}), 400
    
    username = data['username'].strip()
    mode = data['mode']
    
    if not username:
        return jsonify({"error": "Username cannot be empty"}), 400

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if mode == 'login':
            if user:
                return jsonify({"status": "success", "message": f"Welcome back, {username}!"})
            else:
                return jsonify({"error": "Username not found."}), 404
        
        elif mode == 'register':
            if user:
                return jsonify({"error": "Username already exists."}), 409 # 409 Conflict
            else:
                # --- THIS IS THE NEW LOGIC ---
                # 1. Create the new user
                print(f"Creating new user: {username}")
                cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
                new_user_id = cursor.lastrowid # Get the ID of the user we just created

                # 2. Pre-populate their progress for all words at once
                print(f"Pre-populating progress for user_id: {new_user_id}")
                populate_progress_query = """
                    INSERT INTO user_progress (user_id, word_id, mastery_level, next_review_date)
                    SELECT %s, id, 0, NULL
                    FROM words
                """
                cursor.execute(populate_progress_query, (new_user_id,))
                
                # 3. Commit all changes to the database
                conn.commit()
                print("Population complete.")
                # --- END OF NEW LOGIC ---
                
                return jsonify({"status": "success", "message": f"New user '{username}' created!"}), 201 # 201 Created
        
        else:
            return jsonify({"error": "Invalid mode specified"}), 400
            
    except Exception as e:
        print(f"Error during login/register: {e}") # Added more detailed logging
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


# --- MODIFIED /api/question Endpoint ---
@app.route("/api/question")
def get_quiz_question():
    """
    Gets a quiz question for a given user using the CORRECTED SRS priority.
    Priority: 1. Due Words, 2. New Words, 3. Future Words.
    """
    username = request.args.get('user')
    if not username:
        return jsonify({"error": "Username must be provided as a query parameter. e.g., ?user=your_name"}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)

    try:
        # Find User ID
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"error": "User not found"}), 404
        user_id = user_result['id']

        # --- SRS Logic with CORRECTED Priority Order ---
        query = """
            SELECT
                w.id,
                w.word,
                up.mastery_level,
                -- This CASE statement creates the CORRECTED priority order
                CASE
                    WHEN up.next_review_date <= NOW() THEN 0  -- Priority 1: Due words (highest priority)
                    WHEN up.next_review_date IS NULL THEN 1  -- Priority 2: New words
                    ELSE 2                                    -- Priority 3: Words for future review (lowest priority)
                END as priority,
                up.next_review_date
            FROM
                words w
            LEFT JOIN
                user_progress up ON w.id = up.word_id AND up.user_id = %s
            ORDER BY
                priority ASC,          -- Order by our priority cases (Due, then New, then Future)
                up.next_review_date ASC  -- For Due words, pick the most overdue. For Future words, pick the one coming up soonest.
            LIMIT 1;
        """
        cursor.execute(query, (user_id,))
        word_to_quiz = cursor.fetchone()

        if not word_to_quiz:
            return jsonify({"error": "Could not select a word to quiz. The database might be empty."}), 500
        
        # Determine the "reason" for showing this word based on the priority
        priority = word_to_quiz.get('priority', 0)
        mastery_level = word_to_quiz.get('mastery_level')
        # Note: The 'reason' text now corresponds to the corrected priority
        if priority == 0:
            reason = f"This word (Mastery {mastery_level}) is due for review."
        elif priority == 1:
            reason = "Let's try a new word!"
        else:
            reason = f"Reviewing an early word (Mastery {mastery_level})."
            
        # --- Generate Question (Word and Distractors) ---
        cursor.execute("SELECT definition FROM words WHERE id = %s", (word_to_quiz['id'],))
        correct_definition = cursor.fetchone()['definition']
        
        cursor.execute("SELECT definition FROM words WHERE id != %s ORDER BY RAND() LIMIT 3", (word_to_quiz['id'],))
        distractors = [row['definition'] for row in cursor.fetchall()]
        
        options = distractors + [correct_definition]
        random.shuffle(options)
        
        question = {
            "user_id": user_id,
            "word_id": word_to_quiz['id'],
            "word": word_to_quiz['word'],
            "options": options,
            "correct_answer": correct_definition,
            "reason": reason
        }
        
        return jsonify(question)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()


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
    """
    Submits an answer for a user and word, and updates their SRS progress.
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
        
        # THIS IS THE CRITICAL FIX: Use the current UTC time for all calculations.
        next_review_date = datetime.now(timezone.utc) + interval

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

if __name__ == '__main__':
    app.run(debug=True)