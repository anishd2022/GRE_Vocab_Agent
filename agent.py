import json
import os
import random
import datetime
import google.generativeai as genai

# --- File Names for our Databases ---
WORD_BANK_FILE = 'gre_words.json'
USER_DATA_FILE = 'users.json'

# --- Initial GRE Word List (Can be greatly expanded) ---
INITIAL_WORDS = [
    {
        "word": "Aberration",
        "definition": "A departure from what is normal, usual, or expected, typically unwelcome.",
        "example": "The single poor grade on his report card was an aberration.",
        "difficulty": "uncommon"
    },
    {
        "word": "Ephemeral",
        "definition": "Lasting for a very short time.",
        "example": "The beauty of the cherry blossoms is ephemeral.",
        "difficulty": "common"
    },
    {
        "word": "Garrulous",
        "definition": "Excessively talkative, especially on trivial matters.",
        "example": "He was so garrulous that he could barely let anyone else get a word in.",
        "difficulty": "uncommon"
    },
    {
        "word": "Pusillanimous",
        "definition": "Showing a lack of courage or determination; timid.",
        "example": "The pusillanimous leader was afraid to make any difficult decisions.",
        "difficulty": "rare"
    },
    {
        "word": "Laconic",
        "definition": "Using very few words.",
        "example": "His laconic reply suggested a lack of interest in the topic.",
        "difficulty": "common"
    },
    {
        "word": "Iconoclast",
        "definition": "A person who attacks cherished beliefs or institutions.",
        "example": "As an iconoclast, the artist was not afraid to mock the conventions of the art world.",
        "difficulty": "uncommon"
    },
    {
        "word": "Erudite",
        "definition": "Having or showing great knowledge or learning.",
        "example": "The erudite professor could answer any question on ancient history.",
        "difficulty": "common"
    },
    {
        "word": "Profligate",
        "definition": "Recklessly extravagant or wasteful in the use of resources.",
        "example": "The profligate monarch quickly depleted the kingdom's treasury.",
        "difficulty": "rare"
    }
]

class VocabAgent:
    def __init__(self):
        """Initializes the agent by loading or creating the necessary data files and setting up Gemini."""
        self.word_bank = self._load_json(WORD_BANK_FILE, INITIAL_WORDS)
        self.users = self._load_json(USER_DATA_FILE, {})
        self.current_user = None
        self.user_progress = None
        self._setup_gemini()

    def _setup_gemini(self):
        """Sets up the Gemini API with the API key from environment variables."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise EnvironmentError("GOOGLE_API_KEY environment variable not set.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

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

    def select_word_for_quiz(self):
        """
        The core 'intelligent' logic for selecting a word.
        It prioritizes words with the lowest mastery level.
        """
        min_mastery = float('inf')
        for word, stats in self.user_progress.items():
            if stats.get('mastery_level', 0) < min_mastery:
                min_mastery = stats.get('mastery_level', 0)

        candidate_words = [word for word, stats in self.user_progress.items() if stats.get('mastery_level', 0) == min_mastery]

        if not candidate_words:
            # If all words have some mastery, pick one to review (simplistic approach)
            candidate_words = list(self.user_progress.keys())

        return random.choice(candidate_words) if candidate_words else None

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
        """Uses Gemini to generate example sentences for a given word."""
        try:
            prompt = f"Generate {num_sentences} diverse example sentences using the word '{word}'."
            response = self.model.generate_content(prompt)
            print(response)
            if response.parts and hasattr(response.parts[-1], 'text'):
                sentences = [part.text.strip() for part in response.parts if hasattr(part, 'text')]
                # Split into individual sentences if the response is one long string
                all_sentences = []
                for s in sentences:
                    all_sentences.extend(s.split('. '))
                # Filter out empty strings and take the first num_sentences
                valid_sentences = [s.strip() for s in all_sentences if s.strip()]
                return valid_sentences[:num_sentences]
            else:
                print(f"Error generating examples for '{word}': No text in response.")
                return []
        except Exception as e:
            print(f"Error communicating with Gemini for '{word}': {e}")
            return []

    def run_quiz(self, num_questions=5):
        """Runs a quiz session for the logged-in user."""
        if not self.current_user:
            print("No user is logged in.")
            return

        print(f"\nStarting a new quiz for {self.current_user} with {num_questions} questions.")
        score = 0
        for i in range(num_questions):
            word_to_test = self.select_word_for_quiz()
            if not word_to_test:
                print("No words available in the word bank.")
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

                if user_answer == question['correct_answer']:
                    print("Correct! Great job.")
                    score += 1
                    self.user_progress.setdefault(word_to_test, {"mastery_level": 0, "last_seen": None, "correct_streak": 0})
                    self.user_progress.get(word_to_test)['mastery_level'] += 1
                    self.user_progress.get(word_to_test)['correct_streak'] = self.user_progress.get(word_to_test, {}).get('correct_streak', 0) + 1
                else:
                    print(f"Not quite. The correct answer was: '{question['correct_answer']}'")
                    self.user_progress.setdefault(word_to_test, {"mastery_level": 0, "last_seen": None, "correct_streak": 0})
                    self.user_progress.get(word_to_test)['correct_streak'] = 0 # Reset streak

                self.user_progress.setdefault(word_to_test, {"mastery_level": 0, "last_seen": None, "correct_streak": 0})
                self.user_progress.get(word_to_test)['last_seen'] = datetime.datetime.now().isoformat()

                # Generate and display example sentences using Gemini
                print("\n--- Example Sentences ---")
                example_sentences = self.get_example_sentences(word_to_test)
                if example_sentences:
                    for sentence in example_sentences:
                        print(f"- {sentence}")
                else:
                    print("Could not retrieve example sentences.")

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

