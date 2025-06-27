// --- STATE VARIABLES ---
let currentUsername = null;
let currentUserId = null;
const QUIZ_LENGTH = 5;
const API_BASE_URL = 'https://gre-vocab-backend-apjd.onrender.com';

// --- State for "Guess the Definition" Quiz ---
let gtCurrentWordId = null;
let gtScore = 0;
let gtQuestionsAnswered = 0;

// --- State for "Fill in the Blank" Quiz ---
let fibCurrentCorrectAnswer = null;
let fibScore = 0;
let fibQuestionsAnswered = 0;

// --- DOM ELEMENTS (Get all elements from both quiz modes) ---
const loginContainer = document.getElementById('login-container');
const usernameInput = document.getElementById('username-input');
const loginButton = document.getElementById('login-button');
const registerButton = document.getElementById('register-button');
const loginError = document.getElementById('login-error');

const modeSelectionContainer = document.getElementById('mode-selection-container');
const guessDefinitionButton = document.getElementById('guess-definition-button');
const fillBlankButton = document.getElementById('fill-blank-button');

// "Guess the Definition" DOM Elements
const appContainer = document.getElementById('app-container');
const logoutButton = document.getElementById('logout-button');
const welcomeMessage = document.getElementById('welcome-message');
const quizContainer = document.getElementById('quiz-container');
const summaryContainer = document.getElementById('summary-container');
const wordDisplay = document.getElementById('word-display');
const optionsContainer = document.getElementById('options-container');
const feedbackDiv = document.getElementById('feedback');
const finalScoreDisplay = document.getElementById('final-score');
const newQuizButton = document.getElementById('new-quiz-button');
const nextQuestionButton = document.getElementById('next-question-button');
const generateSentencesButton = document.getElementById('generate-sentences-button');
const sentencesContainer = document.getElementById('sentences-container');
const statsContainer = document.getElementById('stats-container');

// "Fill in the Blank" DOM Elements
const fillInBlankContainer = document.getElementById('fill-in-blank-container');
const welcomeMessageFib = document.getElementById('welcome-message-fib');
const logoutButtonFib = document.getElementById('logout-button-fib');
const fibQuizContainer = document.getElementById('fib-quiz-container');
const fibSummaryContainer = document.getElementById('fib-summary-container');
const fibSentenceDisplay = document.getElementById('fib-sentence-display');
const fibOptionsContainer = document.getElementById('fib-options-container');
const fibFeedback = document.getElementById('fib-feedback');
const fibFinalScore = document.getElementById('fib-final-score');
const fibNewQuizButton = document.getElementById('fib-new-quiz-button');
const fibNextQuestionButton = document.getElementById('fib-next-question-button');

// ======================================================
// --- CONSOLIDATED EVENT LISTENERS ---
// All event listeners are now in one place for clarity and reliability.
// ======================================================

// --- Global & Login Listeners ---
loginButton.addEventListener('click', () => handleLogin('login'));
registerButton.addEventListener('click', () => handleLogin('register'));
usernameInput.addEventListener('keyup', (event) => { if (event.key === "Enter") loginButton.click(); });
logoutButton.addEventListener('click', handleLogout);
logoutButtonFib.addEventListener('click', handleLogout);

// --- Mode Selection Listeners ---
guessDefinitionButton.addEventListener('click', startGtQuiz);
fillBlankButton.addEventListener('click', startFibQuiz);

// --- "Guess the Definition" Quiz Listeners ---
newQuizButton.addEventListener('click', () => {
    appContainer.style.display = 'none';
    modeSelectionContainer.style.display = 'block';
});
nextQuestionButton.addEventListener('click', fetchGtQuestion);
generateSentencesButton.addEventListener('click', handleGenerateSentences);

// --- "Fill in the Blank" Quiz Listeners ---
fibNewQuizButton.addEventListener('click', () => {
    fillInBlankContainer.style.display = 'none';
    modeSelectionContainer.style.display = 'block';
});
fibNextQuestionButton.addEventListener('click', fetchFibQuestion);


// ======================================================
// --- FUNCTIONS ---
// ======================================================

// --- LOGIN & LOGOUT LOGIC ---
async function handleLogin(mode) {
    const username = usernameInput.value.trim();
    if (!username) { loginError.textContent = 'Please enter a username.'; return; }
    loginError.textContent = '...'; 

    try {
        const response = await fetch(`${API_BASE_URL}/api/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, mode }),
        });
        const data = await response.json();
        if (response.ok) {
            currentUsername = username;
            loginContainer.style.display = 'none';
            modeSelectionContainer.style.display = 'block'; 
            welcomeMessage.textContent = `Welcome, ${currentUsername}!`;
            welcomeMessageFib.textContent = `Welcome, ${currentUsername}!`;
        } else {
            loginError.textContent = data.error || 'An unknown error occurred.';
        }
    } catch (error) {
        loginError.textContent = 'Failed to connect to the server.';
    }
}

function handleLogout() {
    currentUsername = null;
    currentUserId = null;
    appContainer.style.display = 'none';
    fillInBlankContainer.style.display = 'none';
    modeSelectionContainer.style.display = 'none';
    loginContainer.style.display = 'block';
    usernameInput.value = '';
    loginError.textContent = '';
}

// --- "GUESS THE DEFINITION" QUIZ LOGIC ---

function startGtQuiz() {
    gtScore = 0;
    gtQuestionsAnswered = 0;
    modeSelectionContainer.style.display = 'none';
    summaryContainer.style.display = 'none';
    quizContainer.style.display = 'block';
    appContainer.style.display = 'block';
    updateStatsDashboard();
    fetchGtQuestion();
}

async function fetchGtQuestion() {
    nextQuestionButton.style.display = 'none';
    feedbackDiv.innerHTML = '';
    optionsContainer.innerHTML = '';
    sentencesContainer.innerHTML = ''; // Clear old sentences
    wordDisplay.textContent = `Loading question ${gtQuestionsAnswered + 1} of ${QUIZ_LENGTH}...`;
    try {
        const response = await fetch(`${API_BASE_URL}/api/question?user=${currentUsername}`);
        if (!response.ok) throw new Error('Failed to fetch question.');
        const question = await response.json();
        currentUserId = question.user_id;
        gtCurrentWordId = question.word_id;
        wordDisplay.textContent = question.word;
        const correctAnswer = question.correct_answer;
        question.options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option;
            button.onclick = () => submitGtAnswer(option, correctAnswer);
            optionsContainer.appendChild(button);
        });
    } catch (error) {
        wordDisplay.textContent = 'Error';
        feedbackDiv.textContent = error.message;
    }
}

async function submitGtAnswer(chosenAnswer, correctAnswer) {
    gtQuestionsAnswered++;
    document.querySelectorAll('#options-container button').forEach(b => b.disabled = true);
    if (chosenAnswer === correctAnswer) {
        gtScore++;
        feedbackDiv.textContent = 'Correct!';
        feedbackDiv.className = 'correct';
    } else {
        feedbackDiv.textContent = `Incorrect. The correct answer was: "${correctAnswer}"`;
        feedbackDiv.className = 'incorrect';
    }
    await fetch(`${API_BASE_URL}/api/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: currentUserId, word_id: gtCurrentWordId, answer: chosenAnswer }),
    });
    await updateStatsDashboard();
    if (gtQuestionsAnswered < QUIZ_LENGTH) {
        nextQuestionButton.style.display = 'inline-block';
    } else {
        setTimeout(showGtQuizSummary, 1500);
    }
}

function showGtQuizSummary() {
    quizContainer.style.display = 'none';
    finalScoreDisplay.textContent = `Your Score: ${gtScore} out of ${QUIZ_LENGTH}`;
    summaryContainer.style.display = 'block';
}

async function updateStatsDashboard() {
    statsContainer.innerHTML = 'Loading stats...';
    try {
        const response = await fetch(`${API_BASE_URL}/api/stats?user=${currentUsername}`);
        const stats = await response.json();
        statsContainer.innerHTML = '';
        const unseenCount = stats.unseen || 0;
        if (unseenCount > 0) {
            statsContainer.innerHTML += `<div class="stat-item unseen-stat"><span>Unseen Words</span><span class="stat-count">${unseenCount}</span></div>`;
        }
        for (let i = 0; i < 9; i++) {
             const levelKey = `level_${i}`;
             const count = stats[levelKey] || 0;
             if (count > 0) {
                statsContainer.innerHTML += `<div class="stat-item mastery-${i}"><span>Mastery Level ${i}</span><span class="stat-count">${count}</span></div>`;
             }
        }
    } catch (error) {
        statsContainer.innerHTML = '<p>Could not load stats.</p>';
        console.error("Failed to update stats dashboard:", error);
    }
}

async function handleGenerateSentences() {
    const word = wordDisplay.textContent;
    if (!word || word.startsWith('Loading')) {
        sentencesContainer.innerHTML = '<p>Please wait for a word to be loaded.</p>';
        return;
    }
    sentencesContainer.innerHTML = '<p>Generating example sentences...</p>';
    generateSentencesButton.disabled = true;
    try {
        const response = await fetch(`${API_BASE_URL}/api/generate-sentences`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word: word })
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'An unknown error occurred.');
        }
        const sentences = data.examples;
        if (sentences && sentences.length > 0) {
            sentencesContainer.innerHTML = '<ul>' + sentences.map(s => `<li>${s}</li>`).join('') + '</ul>';
        } else {
            throw new Error("Received an empty list of examples from the server.");
        }
    } catch (error) {
        console.error("Error generating sentences:", error);
        sentencesContainer.innerHTML = `<p style="color: red;">Error: ${error.message}</p>`;
    } finally {
        generateSentencesButton.disabled = false;
    }
}

// --- "FILL IN THE BLANK" QUIZ LOGIC ---

function startFibQuiz() {
    fibScore = 0;
    fibQuestionsAnswered = 0;
    modeSelectionContainer.style.display = 'none';
    fibSummaryContainer.style.display = 'none';
    fibQuizContainer.style.display = 'block';
    fillInBlankContainer.style.display = 'block';
    fetchFibQuestion();
}

// --- THIS IS THE FIXED FUNCTION ---
async function fetchFibQuestion() {
    fibNextQuestionButton.style.display = 'none';
    fibFeedback.innerHTML = '';
    fibOptionsContainer.innerHTML = '';
    fibSentenceDisplay.textContent = `Loading question ${fibQuestionsAnswered + 1} of ${QUIZ_LENGTH}...`;
    try {
        // const response = await fetch(`http://127.0.0.1:5000/api/fill-in-the-blank-question`);
        const response = await fetch(`${API_BASE_URL}/api/fill-in-the-blank-question`);
        // This is the new, robust error handling block.
        // It checks if the request failed (e.g., 404 Not Found).
        if (!response.ok) {
            // It throws a clear error with the status, which is always available.
            // This prevents the code from trying to parse the error page as JSON.
            throw new Error(`Network response was not ok, status: ${response.status}`);
        }

        const question = await response.json();
        
        // Add a check to ensure the data from the server is valid
        if (!question.sentence || !question.options || !question.correct_answer) {
             throw new Error("Received invalid question data from the server.");
        }

        fibCurrentCorrectAnswer = question.correct_answer;
        fibSentenceDisplay.innerHTML = question.sentence;
        question.options.forEach(option => {
            const button = document.createElement('button');
            button.textContent = option;
            button.onclick = () => submitFibAnswer(option);
            fibOptionsContainer.appendChild(button);
        });
    } catch (error) {
        fibSentenceDisplay.textContent = 'Error loading question.';
        // The error message displayed to the user will now be much more helpful.
        // For example: "Network response was not ok, status: 404"
        fibFeedback.textContent = error.message;
        console.error("Error in fetchFibQuestion:", error); // Log the full error for more detail
    }
}

function submitFibAnswer(chosenWord) {
    fibQuestionsAnswered++;
    document.querySelectorAll('#fib-options-container button').forEach(button => button.disabled = true);
    if (chosenWord === fibCurrentCorrectAnswer) {
        fibScore++;
        fibFeedback.textContent = 'Correct!';
        fibFeedback.className = 'correct';
    } else {
        fibFeedback.textContent = `Incorrect. The correct answer was: "${fibCurrentCorrectAnswer}"`;
        fibFeedback.className = 'incorrect';
    }
    if (fibQuestionsAnswered < QUIZ_LENGTH) {
        fibNextQuestionButton.style.display = 'inline-block';
    } else {
        setTimeout(showFibQuizSummary, 1500);
    }
}

function showFibQuizSummary() {
    fibQuizContainer.style.display = 'none';
    fibFinalScore.textContent = `Your Score: ${fibScore} out of ${QUIZ_LENGTH}`;
    fibSummaryContainer.style.display = 'block';
}