const state = {
    sourceText: '',
    userTranslation: '',
    suggestions: [],
    userBleu: null,
    metricsNote: '',
    copiedIndex: null,
    isGenerating: false,
    isDark: false,
    errorMessage: '',
};

const sourceInput = document.getElementById('source-input');
const userTranslationInput = document.getElementById('user-translation-input');
const contentTypeSelect = document.getElementById('content-type-select');
const languageSelect = document.getElementById('language-select');
const generateBtn = document.getElementById('generate-btn');
const resultsSection = document.getElementById('results-section');
const resultsContainer = document.getElementById('results-container');
const userScorePanel = document.getElementById('user-score-panel');
const userScoreBody = document.getElementById('user-score-body');
const themeToggle = document.getElementById('theme-toggle');
const errorBanner = document.getElementById('error-banner');
const metricsHint = document.getElementById('metrics-hint');

function init() {
    initializeTheme();
    sourceInput.addEventListener('input', (e) => {
        state.sourceText = e.target.value;
        updateUI();
    });
    userTranslationInput.addEventListener('input', (e) => {
        state.userTranslation = e.target.value;
        updateUI();
    });
    generateBtn.addEventListener('click', handleGenerate);
    themeToggle.addEventListener('click', toggleTheme);
    updateUI();
}

function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const shouldBeDark = savedTheme === 'dark' || (!savedTheme && prefersDark);
    state.isDark = shouldBeDark;
    document.documentElement.classList.toggle('dark', state.isDark);
}

function toggleTheme() {
    state.isDark = !state.isDark;
    document.documentElement.classList.toggle('dark', state.isDark);
    localStorage.setItem('theme', state.isDark ? 'dark' : 'light');
}

function setError(msg) {
    state.errorMessage = msg || '';
    if (msg) {
        errorBanner.hidden = false;
        errorBanner.textContent = msg;
    } else {
        errorBanner.hidden = true;
        errorBanner.textContent = '';
    }
}

async function handleGenerate() {
    const source = state.sourceText.trim();
    if (!source || state.isGenerating) return;

    state.isGenerating = true;
    setError('');
    state.suggestions = [];
    state.userBleu = null;
    state.metricsNote = '';
    updateUI();

    try {
        const response = await fetch('/api/check-translations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_text: source,
                user_translation: state.userTranslation.trim() || undefined,
                content_type: contentTypeSelect.value,
                target_language: languageSelect.value,
            }),
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.error || `Request failed (${response.status})`);
        }

        state.suggestions = data.suggestions || [];
        state.userBleu = data.user_bleu_vs_reference ?? null;
        state.metricsNote = data.metrics_note || '';
    } catch (err) {
        setError(err.message || 'Something went wrong.');
        state.suggestions = [];
        state.userBleu = null;
    } finally {
        state.isGenerating = false;
        updateUI();
    }
}

async function copyToClipboard(text, index) {
    try {
        await navigator.clipboard.writeText(text);
        state.copiedIndex = index;
        updateUI();
        setTimeout(() => {
            state.copiedIndex = null;
            updateUI();
        }, 2000);
    } catch {
        fallbackCopyTextToClipboard(text, index);
    }
}

function fallbackCopyTextToClipboard(text, index) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.top = '0';
    textArea.style.left = '0';
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
    } catch (e) {
        console.error(e);
    }
    document.body.removeChild(textArea);
}

function createCopyIcon() {
    return `
    <svg class="icon" viewBox="0 0 24 24">
      <rect width="14" height="14" x="3" y="3" rx="2" ry="2"/>
      <path d="m11 11 2 2 4-4"/>
    </svg>
  `;
}

function createCheckIcon() {
    return `
    <svg class="icon" viewBox="0 0 24 24">
      <path d="m9 12 2 2 4-4"/>
    </svg>
  `;
}

function shouldUseRtl() {
    return languageSelect.value === 'arabic';
}

function renderUserPanel() {
    const hasUser = state.userTranslation.trim().length > 0;
    const show =
        state.suggestions.length > 0 &&
        hasUser &&
        (state.userBleu !== null && state.userBleu !== undefined) &&
        !state.errorMessage;
    if (!show) {
        userScorePanel.style.display = 'none';
        return;
    }
    userScorePanel.style.display = 'flex';
    if (shouldUseRtl()) {
        userScoreBody.setAttribute('dir', 'rtl');
    } else {
        userScoreBody.removeAttribute('dir');
    }
    userScoreBody.innerHTML = `
      <div class="result-card user-translation-card">
        <div class="result-card-content">
          <div class="result-main">
            <p class="result-label">Your text</p>
            <p class="result-text">${escapeHtml(state.userTranslation.trim())}</p>
            <div class="metric-row">
              <span class="metric-chip" title="Sentence-level BLEU vs the same model baseline used for AI suggestions">BLEU (vs baseline): <strong>${state.userBleu}</strong></span>
            </div>
          </div>
        </div>
      </div>
    `;
}

function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

function renderResults() {
    resultsContainer.innerHTML = '';
    const rtl = shouldUseRtl();
    const hasUser = state.userTranslation.trim().length > 0;

    state.suggestions.forEach((sug, index) => {
        const isCopied = state.copiedIndex === index;
        const card = document.createElement('div');
        card.className = 'result-card';
        if (rtl) card.setAttribute('dir', 'rtl');
        else card.removeAttribute('dir');

        const dist =
            hasUser && typeof sug.edit_distance_from_user === 'number'
                ? `<span class="metric-chip" title="Levenshtein edit distance between your translation and this suggestion">Edit distance from yours: <strong>${sug.edit_distance_from_user}</strong></span>`
                : '';

        card.innerHTML = `
      <div class="result-card-content">
        <div class="result-main">
          <p class="result-label">${escapeHtml(sug.label || `Suggestion ${sug.rank || index + 1}`)}</p>
          <p class="result-text">${escapeHtml(sug.text || '')}</p>
          <div class="metric-row">
            <span class="metric-chip" title="Sentence-level BLEU vs an internal model baseline translation">BLEU: <strong>${sug.bleu_vs_reference}</strong></span>
            ${dist}
          </div>
        </div>
        <button type="button" class="copy-button ${isCopied ? 'copied' : ''}" data-index="${index}">
          ${isCopied ? createCheckIcon() : createCopyIcon()}
          ${isCopied ? 'Copied!' : 'Copy'}
        </button>
      </div>
    `;

        card.querySelector('.copy-button').addEventListener('click', () => {
            copyToClipboard(sug.text, index);
        });
        resultsContainer.appendChild(card);
    });
}

function updateUI() {
    const hasSource = state.sourceText.trim().length > 0;
    generateBtn.disabled = !hasSource || state.isGenerating;
    generateBtn.textContent = state.isGenerating ? 'Analyzing…' : 'Get AI suggestions & scores';
    generateBtn.classList.toggle('loading', state.isGenerating);

    if (state.suggestions.length > 0 && !state.errorMessage) {
        resultsSection.style.display = 'flex';
        metricsHint.textContent = state.metricsNote || '';
        renderResults();
    } else {
        resultsSection.style.display = 'none';
        metricsHint.textContent = '';
    }

    renderUserPanel();
}

document.addEventListener('DOMContentLoaded', init);
