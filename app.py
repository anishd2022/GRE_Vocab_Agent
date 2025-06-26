import os
import json
from flask import Flask, jsonify, request, render_template
from dotenv import load_dotenv
import mysql.connector
from datetime import datetime, timedelta, timezone
import random
import google.generativeai as genai
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')
CORS(app)

# --- Configure Gemini API ---
try:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise EnvironmentError("GOOGLE_API_KEY environment variable not set.")
    genai.configure(api_key=api_key)
    
    json_mode_config = genai.GenerationConfig(response_mime_type="application/json")
    model = genai.GenerativeModel(
        'gemini-1.5-flash-latest',
        generation_config=json_mode_config
    )
    print("Gemini API configured successfully.")
except Exception as e:
    print(f"FATAL ERROR: Could not configure Gemini API: {e}")
    model = None

# Spaced Repetition System Intervals
SRS_INTERVALS = {
    0: timedelta(minutes=0), 1: timedelta(minutes=20), 2: timedelta(minutes=45),
    3: timedelta(hours=2), 4: timedelta(hours=12), 5: timedelta(days=1),
    6: timedelta(days=5), 7: timedelta(days=14), 8: timedelta(days=30)
}

def get_db_connection():
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
        print(f"Database connection error: {err}")
        return None

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/api/generate-sentences", methods=['POST'])
def generate_sentences_proxy():
    if model is None:
        return jsonify({"error": "Gemini API is not configured on the server."}), 503

    data = request.get_json()
    if not data or 'word' not in data:
        return jsonify({"error": "Missing 'word' in request"}), 400
    
    word = data['word']
    num_sentences = 3
    
    prompt = f"""
    Generate exactly {num_sentences} diverse unique example sentences for the word '{word}'. 
    Your output MUST be a valid JSON object.
    The JSON object should have a single key, "examples", which is a list of strings.
    Example for the word 'happy':
    {{
    "examples": [
        "She was happy to see her friends.",
        "The happy dog wagged its tail.",
        "This is a happy occasion."
    ]
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        gemini_response = json.loads(response.text)
        return jsonify(gemini_response)

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Gemini: {e}")
        print(f"Received text: {response.text}")
        return jsonify({"error": "Failed to parse response from AI model."}), 500
    except Exception as e:
        print(f"Error communicating with Gemini: {e}")
        return jsonify({"error": "An error occurred while generating sentences."}), 500

@app.route("/api/login", methods=['POST'])
def handle_login():
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
                return jsonify({"error": "Username already exists."}), 409
            else:
                print(f"Creating new user: {username}")
                cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
                new_user_id = cursor.lastrowid

                print(f"Pre-populating progress for user_id: {new_user_id}")
                populate_progress_query = """
                    INSERT INTO user_progress (user_id, word_id, mastery_level, next_review_date)
                    SELECT %s, id, 0, NULL
                    FROM words
                """
                cursor.execute(populate_progress_query, (new_user_id,))
                
                conn.commit()
                print("Population complete.")
                return jsonify({"status": "success", "message": f"New user '{username}' created!"}), 201
        
        else:
            return jsonify({"error": "Invalid mode specified"}), 400
            
    except Exception as e:
        print(f"Error during login/register: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/api/question")
def get_quiz_question():
    username = request.args.get('user')
    if not username:
        return jsonify({"error": "Username must be provided."}), 400

    conn = get_db_connection()
    if conn is None:
        return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        user_result = cursor.fetchone()
        if not user_result:
            return jsonify({"error": "User not found"}), 404
        user_id = user_result['id']

        query = """
            SELECT
                w.id, w.word, up.mastery_level,
                CASE
                    WHEN up.next_review_date <= NOW() THEN 0
                    WHEN up.next_review_date IS NULL THEN 1
                    ELSE 2
                END as priority, up.next_review_date
            FROM words w
            LEFT JOIN user_progress up ON w.id = up.word_id AND up.user_id = %s
            ORDER BY priority ASC, RAND()
            LIMIT 1;
        """
        cursor.execute(query, (user_id,))
        word_to_quiz = cursor.fetchone()

        if not word_to_quiz:
            return jsonify({"error": "Could not select a word."}), 500
        
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
            "correct_answer": correct_definition
        }
        
        return jsonify(question)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()

# --- NEW --- Added the /api/stats endpoint back
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

@app.route("/api/answer", methods=['POST'])
def submit_answer():
    data = request.get_json()
    user_id, word_id, user_answer = data['user_id'], data['word_id'], data['answer']

    conn = get_db_connection()
    if conn is None: return jsonify({"error": "Database connection failed"}), 500
    
    cursor = conn.cursor(dictionary=True)

    try:
        cursor.execute("SELECT definition FROM words WHERE id = %s", (word_id,))
        correct_answer = cursor.fetchone()['definition']

        cursor.execute("SELECT mastery_level FROM user_progress WHERE user_id = %s AND word_id = %s", (user_id, word_id))
        current_mastery = (cursor.fetchone() or {}).get('mastery_level', 0)

        is_correct = (user_answer == correct_answer)
        new_mastery = min(current_mastery + 1, 8) if is_correct else max(current_mastery - 1, 0)
        
        interval = SRS_INTERVALS[new_mastery]
        next_review_date = datetime.now(timezone.utc) + interval

        update_query = """
            INSERT INTO user_progress (user_id, word_id, mastery_level, next_review_date)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE mastery_level = VALUES(mastery_level), next_review_date = VALUES(next_review_date)
        """
        cursor.execute(update_query, (user_id, word_id, new_mastery, next_review_date.isoformat()))
        conn.commit()

        return jsonify({"correct": is_correct, "correct_answer": correct_answer})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

@app.route("/health")
def health_check():
    """
    A simple endpoint that the cron job can hit to keep the server alive.
    """
    return jsonify({"status": "healthy"}), 200




if __name__ == '__main__':
    app.run(debug=True)