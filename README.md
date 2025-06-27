# GRE Vocab Agent

An intelligent web application designed to help users master GRE vocabulary using a scientifically-backed Spaced Repetition System (SRS). This tool provides an interactive quiz experience, tracks user progress, and leverages the Google Gemini API to generate dynamic example sentences, providing crucial context for each word.

**🌐 [Live Demo](https://gre-vocab-backend-apjd.onrender.com/)**  
*(Also embedded in a personal portfolio website [anishdeshpande.com](https://anishdeshpande.com/))*

---

## 🚀 Key Features

- **🧠 Spaced Repetition System (SRS)**  
  Adaptive learning algorithm that shows difficult words more often and mastered ones less frequently.

- **📝 Interactive Quizzing**  
  Multiple-choice format to test your knowledge of word definitions.

- **🤖 AI-Powered Sentence Generation**  
  One-click example sentence generation using Google Gemini API for contextual understanding.

- **📊 User Progress Tracking**  
  Persistent user system with login/register, tracking individual mastery levels using a MySQL database.

- **📈 Visual Progress Dashboard**  
  A colorful and intuitive interface showing your progress across the entire vocabulary bank.

- **🔀 Multiple Quiz Modes**  
  Currently supports "Guess the Definition" mode. "Fill in the Blank" mode is planned.

---

## 🧰 Tech Stack

### Backend:
- Python (Flask)
- Gunicorn (for production deployment)
- Google Gemini API
- dotenv

### Frontend:
- HTML/CSS/JavaScript
- Vanilla JS (interactive quiz logic)
- Embedded in a Netlify-hosted portfolio site

### Database & APIs:
- MySQL (users, words, user_progress)
- Google Gemini (example sentence generation)

### Deployment:
- **Render** (Flask backend as Web Service)
- **Netlify** (static frontend site)
- **cron-job.org** (keep-alive ping every 14 mins)

---

## 🛠 Local Setup & Installation

### 1. Prerequisites

- Python 3.9+
- `pip` (Python package manager)
- A running MySQL server instance

---

### 2. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/GRE_Vocab_Agent.git
cd GRE_Vocab_Agent
```

### 3. Create a Virtual Environment

```bash
# Create the virtual environment
python3 -m venv venv

# Activate it (macOS/Linux)
source venv/bin/activate

# Activate it (Windows)
.\venv\Scripts\activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

```ini
# .env

# Google Gemini API Key
GOOGLE_API_KEY="your_gemini_api_key_here"

# MySQL Database Connection
UCMAS_AWS_AD141_DB_ADMIN_HOST="your_database_host"
UCMAS_AWS_AD141_DB_ADMIN_USER="your_database_user"
UCMAS_AWS_AD141_DB_ADMIN_PW="your_database_password"
UCMAS_AWS_AD141_DB_ADMIN_PORT="3306"
UCMAS_AWS_AD141_DB_ADMIN_DBNAME="your_database_name"
```

### 6. Prepare and migrate the database

Ensure `magoosh_1000.csv` is in the project root, then run:
```bash
python migrate_to_mysql.py
```

### 7. Run application locally

```bash
flask run
# or
python app.py
```





