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
const optionsContainer = document.getElementById('options-container');
const feedbackDiv = document.getElementById('feedback');
const finalScoreDisplay = document.getElementById('final-score');
const newQuizButton = document.getElementById('new-quiz-button');
const nextQuestionButton = document.getElementById('next-question-button');
const generateSentencesButton = document.getElementById('generate-sentences-button');
const statsContainer = document.getElementById('stats-container');
// --- NEW --- Get the sentences container element
const sentencesContainer = document.getElementById('sentences-container');


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
nextQuestionButton.addEventListener('click', fetchQuestion);
// --- MODIFIED --- Event listener now calls the new Gemini API function
generateSentencesButton.addEventListener('click', handleGenerateSentences);


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
    nextQuestionButton.style.display = 'none';
    feedbackDiv.innerHTML = '';
    feedbackDiv.className = '';
    optionsContainer.innerHTML = '';
    // --- NEW --- Clear the sentences from the previous question
    sentencesContainer.innerHTML = ''; 
    wordDisplay.textContent = `Loading question ${questionsAnswered + 1} of ${QUIZ_LENGTH}...`;

    try {
        const response = await fetch(`/api/question?user=${currentUsername}`);
        if (!response.ok) throw new Error('Failed to fetch question.');
        
        const question = await response.json();
        
        currentUserId = question.user_id;
        currentWordId = question.word_id;
        currentCorrectAnswer = question.correct_answer;
        
        wordDisplay.textContent = question.word;

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
        nextQuestionButton.style.display = 'inline-block';
    } else {
        setTimeout(showQuizSummary, 1500);
    }
}

function showQuizSummary() {
    quizContainer.style.display = 'none';
    finalScoreDisplay.textContent = `Your Score: ${score} out of ${QUIZ_LENGTH}`;
    summaryContainer.style.display = 'block';
}

async function updateStatsDashboard() {
    statsContainer.innerHTML = 'Loading stats...';
    try {
        const response = await fetch(`/api/stats?user=${currentUsername}`);
        const stats = await response.json();

        statsContainer.innerHTML = '';
        const unseenCount = stats.unseen || 0;
        statsContainer.innerHTML += `<p>Unseen Words: ${unseenCount}</p>`;
        for(let i=0; i<9; i++) {
             const levelKey = `level_${i}`;
             const count = stats[levelKey] || 0;
             if(count > 0) {
                statsContainer.innerHTML += `<p>Mastery Level ${i}: ${count}</p>`;
             }
        }
    } catch (error) {
        statsContainer.innerHTML = 'Could not load stats.';
        console.error("Failed to update stats dashboard:", error);
    }
}


// --- NEW --- Function to call Gemini API and display sentences
async function handleGenerateSentences() {
    const word = wordDisplay.textContent;
    // ... (show loading message) ...

    try {
        // 1. Call YOUR OWN backend, not Google's API directly.
        const response = await fetch('/api/generate-sentences', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            // 2. Send the word to your server.
            body: JSON.stringify({ word: word })
        });

        const data = await response.json();

        if (!response.ok) {
            // Display errors that came from your server
            throw new Error(data.error || 'An unknown error occurred.');
        }

        // 3. Display the sentences received from your server.
        const sentences = data.examples;
        if (sentences && sentences.length > 0) {
            sentencesContainer.innerHTML = '<ul>' + sentences.map(s => `<li>${s}</li>`).join('') + '</ul>';
        } else {
            throw new Error("Received an empty list of examples from the server.");
        }

    } catch (error) {
        // ... (handle and display errors) ...
    } finally {
        // ... (re-enable button) ...
    }
}
