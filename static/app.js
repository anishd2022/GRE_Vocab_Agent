// --- STATE VARIABLES ---
let currentUserId = null;
let currentWordId = null;
let currentCorrectAnswer = null;
let score = 0;
let questionsAnswered = 0;
const QUIZ_LENGTH = 5;
const USERNAME = "anish";

// --- DOM ELEMENTS ---
const wordDisplay = document.getElementById('word-display');
const reasonDisplay = document.getElementById('reason-display');
const optionsContainer = document.getElementById('options-container');
const feedbackDiv = document.getElementById('feedback');
const quizContainer = document.getElementById('quiz-container');
const summaryContainer = document.getElementById('summary-container');
const finalScoreDisplay = document.getElementById('final-score');
const newQuizButton = document.getElementById('new-quiz-button');

// --- EVENT LISTENERS ---
newQuizButton.addEventListener('click', startQuiz);
document.addEventListener('DOMContentLoaded', startQuiz);

// --- MAIN FUNCTIONS ---

function startQuiz() {
    score = 0;
    questionsAnswered = 0;
    summaryContainer.style.display = 'none';
    quizContainer.style.display = 'block';
    updateStatsDashboard(); // Update stats at the start
    fetchQuestion();
}

async function fetchQuestion() {
    feedbackDiv.innerHTML = '';
    optionsContainer.innerHTML = '';
    reasonDisplay.textContent = '';
    wordDisplay.textContent = `Loading question ${questionsAnswered + 1} of ${QUIZ_LENGTH}...`;

    try {
        const response = await fetch(`/api/question?user=${USERNAME}`);
        if (!response.ok) throw new Error('Failed to fetch question.');
        
        const question = await response.json();
        
        currentUserId = question.user_id;
        currentWordId = question.word_id;
        currentCorrectAnswer = question.correct_answer;
        
        wordDisplay.textContent = question.word;
        reasonDisplay.textContent = question.reason; // Display the reason

        question.options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option;
            button.onclick = () => submitAnswer(option);
            optionsContainer.appendChild(button);
        });

    } catch (error) {
        wordDisplay.textContent = 'Error';
        feedbackDiv.textContent = error.message;
    }
}

async function submitAnswer(chosenAnswer) {
    questionsAnswered++;
    document.querySelectorAll('#options-container button').forEach(button => button.disabled = true);

    if (chosenAnswer === currentCorrectAnswer) {
        score++;
        feedbackDiv.textContent = 'Correct!';
        feedbackDiv.className = 'correct';
    } else {
        feedbackDiv.textContent = `Incorrect. The correct answer was: "${currentCorrectAnswer}"`;
        feedbackDiv.className = 'incorrect';
    }
    
    // Update the database in the background
    await fetch('/api/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: currentUserId,
            word_id: currentWordId,
            answer: chosenAnswer,
        }),
    });

    // Refresh the dashboard after submitting the answer
    await updateStatsDashboard();
    
    if (questionsAnswered < QUIZ_LENGTH) {
        setTimeout(fetchQuestion, 2000);
    } else {
        setTimeout(showQuizSummary, 2000);
    }
}

function showQuizSummary() {
    quizContainer.style.display = 'none';
    finalScoreDisplay.textContent = `Your Score: ${score} out of ${QUIZ_LENGTH}`;
    summaryContainer.style.display = 'block';
}

// --- NEW: Function to update the stats dashboard ---
async function updateStatsDashboard() {
    try {
        const response = await fetch(`/api/stats?user=${USERNAME}`);
        const stats = await response.json();

        // Calculate a "Level 4+" category
        let level4plus = 0;
        for (const level in stats) {
            if (level.startsWith('level_') && parseInt(level.split('_')[1]) >= 4) {
                level4plus += stats[level];
            }
        }

        document.getElementById('stats-unseen').textContent = stats.unseen || 0;
        document.getElementById('stats-level_0').textContent = stats.level_0 || 0;
        document.getElementById('stats-level_1').textContent = stats.level_1 || 0;
        document.getElementById('stats-level_2').textContent = stats.level_2 || 0;
        document.getElementById('stats-level_3').textContent = stats.level_3 || 0;
        document.getElementById('stats-level_4_plus').textContent = level4plus;

    } catch (error) {
        console.error("Failed to update stats dashboard:", error);
    }
}