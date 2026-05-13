# Nuancia
### Live demo: https://nuancia.onrender.com/

## 🔤 What is this project about?
Nuancia is an AI-assisted translation quality checker. You provide source text, choose a content type and target language, and the app generates three ranked translation suggestions. If you paste your own translation, Nuancia compares it against the same model baseline using sentence-level BLEU and edit-distance metrics so you can quickly evaluate and refine your draft.

## 💻 Technologies Utilized
- **Backend**: Flask, Python
- **AI/ML**: Google Gemini 2.5 Flash API for translation suggestions and scoring reference generation
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Metrics**: Sentence-level BLEU (0-100) + Levenshtein edit distance
- **Deployment**: Render + Gunicorn

## ✨ Current Features / Functionality
- Three AI translation suggestions per request, ranked by overall fit
- Content-type aware outputs for marketing, legal, technical, and literary text
- Optional user-translation scoring with BLEU vs the internal model baseline
- Character-level edit distance between your translation and each AI suggestion
- Support for 15 target languages, including RTL rendering for Arabic
- Dark/light theme toggle with localStorage persistence and copy-to-clipboard actions

## 🛠️ Upcoming Features / Improvements
- Translation history and saved comparison sessions
- Additional quality metrics (for example, semantic similarity and terminology consistency checks)
