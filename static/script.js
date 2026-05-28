const state = {
    sourceText: '',
    referenceTranslation: '',
    translations: [],
    complexity: null,
    highlightedProvider: null,
    costNote: '',
    copiedIndex: null,
    isGenerating: false,
    isDark: false,
    errorMessage: '',
};

const sourceInput = document.getElementById('source-input');
const referenceTranslationInput = document.getElementById('reference-translation-input');
const languageSelect = document.getElementById('language-select');
const generateBtn = document.getElementById('generate-btn');
const resultsSection = document.getElementById('results-section');
const resultsContainer = document.getElementById('results-container');
const themeToggle = document.getElementById('theme-toggle');
const errorBanner = document.getElementById('error-banner');
const metricsHint = document.getElementById('metrics-hint');
const complexityBanner = document.getElementById('complexity-banner');

function init() {
    initializeTheme();
    sourceInput.addEventListener('input', (e) => {
        state.sourceText = e.target.value;
        updateUI();
    });
    referenceTranslationInput.addEventListener('input', (e) => {
        state.referenceTranslation = e.target.value;
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
    state.translations = [];
    state.complexity = null;
    state.highlightedProvider = null;
    state.costNote = '';
    updateUI();

    try {
        const response = await fetch('/api/check-translations', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                source_text: source,
                reference_translation: state.referenceTranslation.trim() || undefined,
                target_language: languageSelect.value,
            }),
        });

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            throw new Error(data.error || `Request failed (${response.status})`);
        }

        state.translations = data.translations || [];
        state.complexity = data.complexity || null;
        state.highlightedProvider = data.highlighted_provider || null;
        state.costNote = data.cost_note || '';
    } catch (err) {
        setError(err.message || 'Something went wrong.');
        state.translations = [];
        state.complexity = null;
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

function escapeHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

function renderResults() {
    resultsContainer.innerHTML = '';
    const rtl = shouldUseRtl();
    const hasReference = state.referenceTranslation.trim().length > 0;

    state.translations.forEach((item, index) => {
        const isCopied = state.copiedIndex === index;
        const card = document.createElement('div');
        card.className = `result-card ${item.highlighted ? 'result-card--highlighted' : ''}`;
        if (rtl) card.setAttribute('dir', 'rtl');
        else card.removeAttribute('dir');

        const cost = item.cost || {};
        const costTooltip =
            cost.unit_type === 'characters'
                ? `Estimated from ${cost.input_units ?? 0} characters × $${Number(cost.rate_per_unit_usd || 0).toFixed(6)} per character`
                : `Estimated from ${cost.input_units ?? 0} input tokens and ${cost.output_units ?? 0} output tokens. Rates: $${Number(cost.input_rate_per_million_usd || 0).toFixed(2)}/1M input tokens and $${Number(cost.output_rate_per_million_usd || 0).toFixed(2)}/1M output tokens`;
        const costLabel =
            cost.unit_type === 'characters'
                ? `Chars: ${cost.input_units ?? 0}`
                : `Tokens in/out: ${cost.input_units ?? 0}/${cost.output_units ?? 0}`;

        const chrfChip =
            hasReference && typeof item.chrf_vs_reference === 'number'
                ? `<span class="metric-chip" title="Character n-gram F-score against your reference translation (0-100)">ChrF: <strong>${item.chrf_vs_reference}</strong></span>`
                : '';
        const recommendedBadge = item.highlighted
            ? `<span class="recommended-badge">Recommended (${(state.complexity || '').toLowerCase()})</span>`
            : '';

        card.innerHTML = `
      <div class="result-card-content">
        <div class="result-main">
          <p class="result-label">${escapeHtml(item.label || `Translation ${index + 1}`)} ${recommendedBadge}</p>
          <p class="result-text">${escapeHtml(item.text || '')}</p>
          <div class="metric-row">
            <span class="metric-chip" title="${escapeHtml(item.quality_tooltip || 'Calculated with Gemini')}">Quality (Gemini): <strong>${item.quality_score ?? '-'}</strong></span>
            <span class="metric-chip" title="${escapeHtml(costTooltip)}">Estimated cost: <strong>$${Number(cost.amount_usd || 0).toFixed(6)}</strong></span>
            <span class="metric-chip" title="${escapeHtml(costTooltip)}">${escapeHtml(costLabel)}</span>
            ${chrfChip}
          </div>
        </div>
        <button type="button" class="copy-button ${isCopied ? 'copied' : ''}" data-index="${index}">
          ${isCopied ? createCheckIcon() : createCopyIcon()}
          ${isCopied ? 'Copied!' : 'Copy'}
        </button>
      </div>
    `;

        card.querySelector('.copy-button').addEventListener('click', () => {
            copyToClipboard(item.text, index);
        });
        resultsContainer.appendChild(card);
    });
}

function updateUI() {
    const hasSource = state.sourceText.trim().length > 0;
    generateBtn.disabled = !hasSource || state.isGenerating;
    generateBtn.textContent = state.isGenerating ? 'Analyzing…' : 'Translate & Analyze';
    generateBtn.classList.toggle('loading', state.isGenerating);

    if (state.translations.length > 0 && !state.errorMessage) {
        resultsSection.style.display = 'flex';
        const ruleLabel =
            state.complexity === 'COMPLEX'
                ? 'Complexity is COMPLEX, so Gemini is highlighted.'
                : 'Complexity is SIMPLE, so DeepL is highlighted.';
        complexityBanner.textContent = state.complexity
            ? `Complexity: ${state.complexity}. ${ruleLabel}`
            : '';
        metricsHint.textContent = state.costNote || '';
        renderResults();
    } else {
        resultsSection.style.display = 'none';
        complexityBanner.textContent = '';
        metricsHint.textContent = '';
    }
}

document.addEventListener('DOMContentLoaded', init);
