// Application state
let state = {
    inputText: '',
    results: [],
    copiedIndex: null,
    isGenerating: false,
    isDark: false,
    topEmotions: []
};

// DOM elements
const textInput = document.getElementById('text-input');
const generateBtn = document.getElementById('generate-btn');
const resultsSection = document.getElementById('results-section');
const resultsContainer = document.getElementById('results-container');
const themeToggle = document.getElementById('theme-toggle');
const emotionBarsContainer = document.getElementById('emotion-bars');

// Initialize the application
function init() {
    initializeTheme();

    textInput.addEventListener('input', handleInputChange);
    generateBtn.addEventListener('click', handleGenerate);
    themeToggle.addEventListener('click', toggleTheme);

    updateUI();
}

// Initialize theme
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const shouldBeDark = savedTheme === 'dark' || (!savedTheme && prefersDark);

    state.isDark = shouldBeDark;
    document.documentElement.classList.toggle('dark', state.isDark);
}

// Toggle theme
function toggleTheme() {
    state.isDark = !state.isDark;
    document.documentElement.classList.toggle('dark', state.isDark);
    localStorage.setItem('theme', state.isDark ? 'dark' : 'light');
}

// Handle input changes
function handleInputChange(event) {
    state.inputText = event.target.value;
    updateUI();
}

// Handle generate button click
async function handleGenerate() {
    if (!state.inputText.trim() || state.isGenerating) return;

    const languageSelect = document.getElementById('language-select');
    const targetLanguage = languageSelect.value;

    state.isGenerating = true;
    updateUI();

    try {
        const response = await fetch('http://localhost:5000/api/translate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: state.inputText,
                target_language: targetLanguage
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Check if data and translations exist
        if (data && data.translations) {
            state.results = data.translations.map(trans => ({
                type: trans.type,
                text: trans.text
            }));
            // Extract top emotions
            state.topEmotions = data.top_emotions;
        } else {
            state.results = [{
                type: 'Error',
                text: 'No translation data received.'
            }];
            state.topEmotions = [];
        }

    } catch (error) {
        state.results = [{
            type: 'Error',
            text: `Translation failed: ${error.message}`
        }];
        state.topEmotions = [];
    } finally {
        state.isGenerating = false;
        updateUI();
    }
}

// Handle copy to clipboard
async function copyToClipboard(text, index) {
    try {
        await navigator.clipboard.writeText(text);
        state.copiedIndex = index;
        updateUI();

        // Reset copied state after 2 seconds
        setTimeout(() => {
            state.copiedIndex = null;
            updateUI();
        }, 2000);
    } catch (err) {
        // Fallback for older browsers
        fallbackCopyTextToClipboard(text, index);
    }
}

// Fallback copy method for older browsers
function fallbackCopyTextToClipboard(text, index) {
    const textArea = document.createElement("textarea");
    textArea.value = text;

    // Avoid scrolling to bottom
    textArea.style.top = "0";
    textArea.style.left = "0";
    textArea.style.position = "fixed";

    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();

    try {
        document.execCommand('copy');
        state.copiedIndex = index;
        updateUI();

        setTimeout(() => {
            state.copiedIndex = null;
            updateUI();
        }, 2000);
    } catch (err) {
        console.error('Fallback: Oops, unable to copy', err);
    }

    document.body.removeChild(textArea);
}

// Create copy icon SVG
function createCopyIcon() {
    return `
    <svg class="icon" viewBox="0 0 24 24">
      <rect width="14" height="14" x="3" y="3" rx="2" ry="2"/>
      <path d="m11 11 2 2 4-4"/>
    </svg>
  `;
}

// Create check icon SVG
function createCheckIcon() {
    return `
    <svg class="icon" viewBox="0 0 24 24">
      <path d="m9 12 2 2 4-4"/>
    </svg>
  `;
}

// Generate emotion bars
function generateEmotionBars() {
    if (!state.topEmotions || state.topEmotions.length === 0) {
        return '';
    }

    const maxScore = Math.max(...state.topEmotions.map(e => e.score));

    const bars = state.topEmotions.map(emotion => {
        const percentage = (emotion.score / maxScore) * 100;
        return `
            <div class="emotion-bar">
                <div class="emotion-bar-inner" style="width: ${percentage}%;">
                    <span class="emotion-label">${emotion.label}</span>
                    <span class="emotion-percentage">${percentage.toFixed(1)}%</span>
                </div>
            </div>
        `;
    }).join('');

    return bars;
}

// Update the UI based on current state
function updateUI() {
    // Update generate button
    const hasText = state.inputText.trim().length > 0;
    generateBtn.disabled = !hasText || state.isGenerating;
    generateBtn.textContent = state.isGenerating ? 'Thinking...' : 'Translate Using AI';

    if (state.isGenerating) {
        generateBtn.classList.add('loading');
    } else {
        generateBtn.classList.remove('loading');
    }

    // Update results section visibility
    if (state.results.length > 0) {
        resultsSection.style.display = 'flex';
        renderResults();
    } else {
        resultsSection.style.display = 'none';
    }

    // Render emotion bars
    emotionBarsContainer.innerHTML = generateEmotionBars();
}

// Render the results
function renderResults() {
    resultsContainer.innerHTML = '';

    state.results.forEach((result, index) => {
        const isCopied = state.copiedIndex === index;

        const resultCard = document.createElement('div');
        resultCard.className = 'result-card';

        // Conditionally set the dir attribute for RTL languages like Arabic
        const languageSelect = document.getElementById('language-select');
        const targetLanguage = languageSelect.value;
        if (targetLanguage === 'arabic') {
            resultCard.setAttribute('dir', 'rtl');
        } else {
            resultCard.removeAttribute('dir'); // Ensure LTR for other languages
        }

        resultCard.innerHTML = `
      <div class="result-card-content">
        <p class="result-text">${result.text}</p>
        <button class="copy-button ${isCopied ? 'copied' : ''}" data-index="${index}">
          ${isCopied ? createCheckIcon() : createCopyIcon()}
          ${isCopied ? 'Copied!' : 'Copy'}
        </button>
      </div>
    `;

        // Add event listener to copy button
        const copyButton = resultCard.querySelector('.copy-button');
        copyButton.addEventListener('click', () => {
            copyToClipboard(result.text, index);
        });

        resultsContainer.appendChild(resultCard);
    });
}

// Start the application
document.addEventListener('DOMContentLoaded', init);