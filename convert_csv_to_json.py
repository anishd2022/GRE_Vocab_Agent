import csv
import json

# --- Configuration ---
# The name of your source CSV file
INPUT_CSV_FILE = 'magoosh_1000.csv' 
# The name of the JSON file we want to create
OUTPUT_JSON_FILE = 'gre_words.json' 

def convert_csv_to_json():
    """
    Reads a CSV file with GRE words and converts it into a JSON database.
    Assumes the CSV has columns: 'word', 'definition', 'sentence'.
    """
    word_database = []
    print(f"Reading from '{INPUT_CSV_FILE}'...")

    try:
        # Open the CSV file for reading
        with open(INPUT_CSV_FILE, mode='r', encoding='utf-8') as csv_file:
            # Use DictReader to read rows as dictionaries
            csv_reader = csv.DictReader(csv_file)
            
            for row in csv_reader:
                # Create a dictionary for each word with the desired structure.
                # The .get() method safely retrieves data, and .strip() removes whitespace.
                word_entry = {
                    "word": row.get('word', '').strip(),
                    "definition": row.get('definition', '').strip(),
                    "example": row.get('sentence', '').strip(),
                    # We can assign a default difficulty level here.
                    "difficulty": "uncommon" 
                }
                
                # Ensure the word field is not empty before adding
                if word_entry["word"]:
                    word_database.append(word_entry)

        print(f"Successfully processed {len(word_database)} words.")
        print(f"Writing to '{OUTPUT_JSON_FILE}'...")

        # Open the output JSON file for writing
        with open(OUTPUT_JSON_FILE, mode='w', encoding='utf-8') as json_file:
            # Dump the list of dictionaries into the JSON file with nice formatting
            json.dump(word_database, json_file, indent=4)
        
        print("Conversion complete!")

    except FileNotFoundError:
        print(f"Error: The file '{INPUT_CSV_FILE}' was not found.")
        print("Please make sure it's in the same folder as this script.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    convert_csv_to_json()