// --- STATE VARIABLES ---
let currentUsername = null;
let currentUserId = null;
let currentWordId = null;
let currentCorrectAnswer = null;
let score = 0;
let questionsAnswered = 0;
const QUIZ_LENGTH = 5;

// --- DOM ELEMENTS ---
const loginContainer = document.getElementById('login-container');
const appContainer = document.getElementById('app-container');
const usernameInput = document.getElementById('username-input');
const loginButton = document.getElementById('login-button');
const registerButton = document.getElementById('register-button');
const loginError = document.getElementById('login-error');
const logoutButton = document.getElementById('logout-button');
const welcomeMessage = document.getElementById('welcome-message');

const quizContainer = document.getElementById('quiz-container');
const summaryContainer = document.getElementById('summary-container');
const wordDisplay = document.getElementById('word-display');
const reasonDisplay = document.getElementById('reason-display'); // <-- NEW DOM ELEMENT
const optionsContainer = document.getElementById('options-container');
const feedbackDiv = document.getElementById('feedback');
const finalScoreDisplay = document.getElementById('final-score');
const newQuizButton = document.getElementById('new-quiz-button');

// --- EVENT LISTENERS ---
loginButton.addEventListener('click', () => handleLogin('login'));
registerButton.addEventListener('click', () => handleLogin('register'));
logoutButton.addEventListener('click', handleLogout);
newQuizButton.addEventListener('click', startQuiz);
usernameInput.addEventListener('keyup', function(event) {
    if (event.key === "Enter") {
        loginButton.click();
    }
});

// --- LOGIN/LOGOUT LOGIC ---
async function handleLogin(mode) {
    const username = usernameInput.value.trim();
    if (!username) {
        loginError.textContent = 'Please enter a username.';
        return;
    }
    loginError.textContent = '...';

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, mode }),
        });
        const data = await response.json();

        if (response.ok) {
            currentUsername = username;
            loginContainer.style.display = 'none';
            appContainer.style.display = 'block';
            welcomeMessage.textContent = `Welcome, ${currentUsername}!`;
            startQuiz();
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
    loginContainer.style.display = 'block';
    usernameInput.value = '';
    loginError.textContent = '';
}

// --- QUIZ LOGIC ---
function startQuiz() {
    score = 0;
    questionsAnswered = 0;
    summaryContainer.style.display = 'none';
    quizContainer.style.display = 'block';
    updateStatsDashboard();
    fetchQuestion();
}

async function fetchQuestion() {
    feedbackDiv.innerHTML = '';
    optionsContainer.innerHTML = '';
    reasonDisplay.textContent = ''; // Clear previous reason
    wordDisplay.textContent = `Loading question ${questionsAnswered + 1} of ${QUIZ_LENGTH}...`;

    try {
        const response = await fetch(`/api/question?user=${currentUsername}`);
        if (!response.ok) throw new Error('Failed to fetch question.');
        
        const question = await response.json();
        
        currentUserId = question.user_id;
        currentWordId = question.word_id;
        currentCorrectAnswer = question.correct_answer;
        
        wordDisplay.textContent = question.word;
        reasonDisplay.textContent = question.reason; // <-- UPDATE THE REASON DISPLAY

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
    
    await fetch('/api/answer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: currentUserId,
            word_id: currentWordId,
            answer: chosenAnswer,
        }),
    });

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

async function updateStatsDashboard() {
    const statsGrid = document.getElementById('stats-grid');
    statsGrid.innerHTML = 'Loading stats...';
    try {
        const response = await fetch(`/api/stats?user=${currentUsername}`);
        const stats = await response.json();

        statsGrid.innerHTML = `
            <div>Unseen</div><div>${stats.unseen || 0}</div>
            <div>Level 0</div><div>${stats.level_0 || 0}</div>
            <div>Level 1</div><div>${stats.level_1 || 0}</div>
            <div>Level 2</div><div>${stats.level_2 || 0}</div>
            <div>Level 3</div><div>${stats.level_3 || 0}</div>
        `;
        let level4plus = 0;
        for (const key in stats) {
            if (key.startsWith('level_') && parseInt(key.split('_')[1]) >= 4) {
                level4plus += stats[key];
            }
        }
        statsGrid.innerHTML += `<div>Level 4+</div><div>${level4plus}</div>`;

    } catch (error) {
        statsGrid.innerHTML = 'Could not load stats.';
    }
}