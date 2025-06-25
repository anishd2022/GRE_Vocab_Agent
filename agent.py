import json
import os
import random
import datetime
import google.generativeai as genai
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# --- File Names for our Databases ---
WORD_BANK_FILE = 'gre_words.json'
USER_DATA_FILE = 'users.json'


class VocabAgent:
    def __init__(self):
        """Initializes the agent by loading data files and setting up Gemini."""
        self.word_bank = self._load_word_bank()
        self.users = self._load_user_data()
        self.current_user = None
        self.user_progress = None
        self._setup_gemini()


    def _load_word_bank(self):
        """
        Loads the essential word bank from gre_words.json.
        If the file doesn't exist, the program cannot run.
        """
        try:
            with open(WORD_BANK_FILE, 'r', encoding='utf-8') as f:
                print(f"Successfully loaded word bank from '{WORD_BANK_FILE}'.")
                return json.load(f)
        except FileNotFoundError:
            print(f"FATAL ERROR: The required data file '{WORD_BANK_FILE}' was not found.")
            print("Please run the 'convert_csv_to_json.py' script first to create it.")
            exit()  # Stop the program if the main data file is missing.
        except json.JSONDecodeError:
            print(f"FATAL ERROR: The file '{WORD_BANK_FILE}' is corrupted or not a valid JSON file.")
            exit()
    
    
    def _load_user_data(self):
        """
        Loads user data. If the file doesn't exist, creates an empty one.
        This behavior is kept because new user files can be created on the fly.
        """
        if not os.path.exists(USER_DATA_FILE):
            print(f"User data file '{USER_DATA_FILE}' not found. A new one will be created.")
            with open(USER_DATA_FILE, 'w') as f:
                json.dump({}, f) # Create an empty JSON object
        
        with open(USER_DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)


    def _setup_gemini(self):
        """Sets up the Gemini API with the API key and enables JSON mode."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY environment variable not set.")
        genai.configure(api_key=api_key)
        
        # This is the key change: we tell the model to always output JSON.
        json_mode_config = genai.GenerationConfig(response_mime_type="application/json")
        
        self.model = genai.GenerativeModel(
            'gemini-1.5-flash-latest',
            generation_config=json_mode_config
        )


    def _load_json(self, filename, default_data):
        """Loads a JSON file. If it doesn't exist, creates it with default data."""
        if not os.path.exists(filename):
            print(f"File '{filename}' not found. Creating it now.")
            with open(filename, 'w') as f:
                json.dump(default_data, f, indent=4)
        with open(filename, 'r') as f:
            return json.load(f)


    def _save_users(self):
        """Saves the current state of user data to the file."""
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(self.users, f, indent=4)


    def login_or_create_user(self):
        """Handles user login or creation of a new user profile."""
        username = input("Welcome to the GRE Vocab Tutor! Please enter your username: ").strip()
        if username in self.users:
            print(f"Welcome back, {username}!")
            self.current_user = username
            self.user_progress = self.users.get(username, {}).get('progress', {})
        else:
            print(f"Creating a new profile for {username}.")
            self.current_user = username
            self.users.setdefault(username, {"progress": {}})
            self.user_progress = self.users.get(username, {}).get('progress', {})

        # Initialize progress for any new words added to the bank
        for word_data in self.word_bank:
            word = word_data['word']
            if word not in self.user_progress:
                self.user_progress.setdefault(word, {"mastery_level": 0, "last_seen": None, "correct_streak": 0})


    # Mastery Level -> Time until next review
    SRS_INTERVALS = {
        0: timedelta(minutes=0),   # Immediately available for review
        1: timedelta(minutes=1),  # 20 minutes
        2: timedelta(minutes=45),  # 45 minutes
        3: timedelta(hours=2),     # 2 hours
        4: timedelta(hours=12),    # 12 hours
        5: timedelta(days=1),      # 1 day
        6: timedelta(days=5),      # 5 days
        7: timedelta(days=14),     # 2 weeks
        8: timedelta(days=30)      # 1 month (approximated)
    }
    
    def select_word_for_quiz(self):
        """
        Selects a word using a Spaced Repetition System (SRS) algorithm.
        This version includes print statements for debugging.
        """
        now = datetime.now()
        print("\n--- Running select_word_for_quiz ---")
        print(f"Current Time (now): {now.isoformat()}")

        due_words = []
        new_words = []
        future_review_words = []

        # Limit the debug printout to a few words to avoid spamming the console
        words_to_debug = ["proscribe", "abate", "laconic", "austere"] # Add any other words you're testing

        for word, stats in self.user_progress.items():
            is_debug_word = word in words_to_debug

            next_review_date_str = stats.get("next_review_date")
            if not next_review_date_str:
                new_words.append(word)
                if is_debug_word:
                    print(f"  - Word '{word}' is NEW.")
                continue

            next_review_date = datetime.fromisoformat(next_review_date_str)

            if is_debug_word:
                print(f"  - Checking '{word}': Review date is {next_review_date.isoformat()}")

            if next_review_date <= now:
                due_words.append((word, next_review_date))
                if is_debug_word:
                    print(f"    -> RESULT: DUE (Review date is in the past)")
            else:
                future_review_words.append((word, next_review_date))
                if is_debug_word:
                    print(f"    -> RESULT: NOT DUE (Review date is in the future)")

        print(f"Found {len(due_words)} due words, {len(new_words)} new words.")
        
        # --- The rest of the selection logic is the same ---
        if due_words:
            due_words.sort(key=lambda x: x[1])
            print(f"--> Selecting from due words: '{due_words[0][0]}'")
            return due_words[0][0]

        if new_words:
            selected_word = random.choice(new_words)
            print(f"--> Selecting from new words: '{selected_word}'")
            return selected_word

        if future_review_words:
            future_review_words.sort(key=lambda x: x[1])
            print(f"--> No words are due. Selecting soonest future word: '{future_review_words[0][0]}'")
            return future_review_words[0][0]

        fallback_word = random.choice([w['word'] for w in self.word_bank])
        print(f"--> Fallback: Selecting random word: '{fallback_word}'")
        return fallback_word


    def generate_question(self, word):
        """Generates a multiple-choice question for a given word."""
        correct_definition = next((w['definition'] for w in self.word_bank if w['word'] == word), None)
        if not correct_definition:
            return None

        distractors = [w['definition'] for w in self.word_bank if w['definition'] != correct_definition]
        random.shuffle(distractors)
        options = distractors[:3] + [correct_definition]
        random.shuffle(options)

        return {
            "word": word,
            "options": options,
            "correct_answer": correct_definition
        }


    def get_example_sentences(self, word, num_sentences=3):
        """
        Uses Gemini to generate a structured JSON object of example sentences.
        """
        # 1. Create a highly specific prompt defining the desired JSON structure.
        prompt = f"""
        Generate exactly {num_sentences} diverse example sentences for the word '{word}'.
        
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
            response = self.model.generate_content(prompt)
            
            # 2. Use a robust JSON parser with error handling.
            # The response.text will be a raw JSON string.
            data = json.loads(response.text)
            
            # 3. Safely extract the data from the parsed dictionary.
            # The .get() method prevents errors if the key is missing.
            sentences = data.get("examples", [])
            
            if isinstance(sentences, list) and sentences:
                return sentences
            else:
                print(f"Error generating examples for '{word}': JSON was valid but the 'examples' key was missing or empty.")
                return []

        except json.JSONDecodeError as e:
            # This catches errors if the model fails to return valid JSON.
            print(f"Error parsing JSON response for '{word}': {e}")
            print(f"Received text: {response.text}")
            return []
        except Exception as e:
            # This catches general API communication errors.
            print(f"Error communicating with Gemini for '{word}': {e}")
            return []


    def run_quiz(self, num_questions=5):
        """Runs a quiz session, with the correct SRS logic for updating progress."""
        if not self.current_user:
            print("No user is logged in.")
            return

        print(f"\nStarting a new quiz for {self.current_user} with {num_questions} questions.")
        score = 0
        for i in range(num_questions):
            word_to_test = self.select_word_for_quiz()
            if not word_to_test:
                print("No words available to quiz. The word bank might be empty.")
                break

            question = self.generate_question(word_to_test)
            if not question:
                print(f"Could not generate a question for '{word_to_test}'. Skipping.")
                continue

            print(f"\n--- Question {i+1} ---")
            print(f"What is the definition of: {question['word']}")
            for idx, option in enumerate(question['options']):
                print(f"  {idx + 1}. {option}")

            try:
                user_choice = int(input("Your answer (1-4): "))
                user_answer = question['options'][user_choice - 1]

                current_mastery = self.user_progress[word_to_test].get('mastery_level', 0)
                
                if user_answer == question['correct_answer']:
                    print("Correct! Great job.")
                    score += 1
                    
                    new_mastery = min(current_mastery + 1, max(self.SRS_INTERVALS.keys()))
                    self.user_progress[word_to_test]['mastery_level'] = new_mastery
                    self.user_progress[word_to_test]['correct_streak'] += 1
                    
                else:
                    print(f"Not quite. The correct answer was: '{question['correct_answer']}'")

                    new_mastery = max(current_mastery - 1, 0)
                    self.user_progress[word_to_test]['mastery_level'] = new_mastery
                    self.user_progress[word_to_test]['correct_streak'] = 0

                # --- THIS IS THE CRUCIAL LOGIC THAT WAS MISSING ---
                # It calculates the next review date based on the new mastery level
                interval = self.SRS_INTERVALS[new_mastery]
                next_review_date = datetime.now() + interval
                self.user_progress[word_to_test]['next_review_date'] = next_review_date.isoformat()
                # --- END OF CRUCIAL LOGIC ---
                
                # Show original example sentence from our JSON file
                original_example = next((w.get('example') for w in self.word_bank if w.get('word') == word_to_test), None)
                if original_example:
                    print(f"\nExample: {original_example}")
                
                # Try to get more examples from Gemini
                example_sentences = self.get_example_sentences(word_to_test)
                if example_sentences:
                    print("\n--- More Examples ---")
                    for ex in example_sentences:
                        print(f"- {ex}")

            except (ValueError, IndexError):
                print("Invalid input. Skipping question.")

        print(f"\nQuiz finished! Your score: {score}/{num_questions}")
        self._save_users()
        print("Your progress has been saved.")





if __name__ == "__main__":
    agent = VocabAgent()
    try:
        agent.login_or_create_user()
        # Run a quiz session
        agent.run_quiz(5)

        # Example of how a user could continue
        print("\nYou can take another quiz or close the program.")
        # agent.run_quiz(5)
    except EnvironmentError as e:
        print(f"Error: {e}")
        print("Please make sure you have set the GOOGLE_API_KEY environment variable.")

