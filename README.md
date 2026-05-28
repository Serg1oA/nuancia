# Nuancia
### Live demo: https://nuancia.onrender.com/

## 🔤 What is this project about?
Nuancia is a dual-engine translation analyzer. You provide source text, optionally add a reference translation, and pick a target language. The app always generates two translations (DeepL and Gemini), classifies the source complexity with a cheap Gemini model, highlights the preferred translation based on that complexity rule, and shows quality and cost estimates side by side.

## 💻 Technologies Utilized
- **Backend**: Flask, Python
- **AI/ML**: Google Gemini (flash model for complexity, translation, and quality scoring)
- **Translation API**: DeepL API
- **Frontend**: Vanilla JavaScript, HTML, CSS
- **Metrics**: ChrF (0-100, optional reference-based) + Gemini quality score (0-100)
- **Deployment**: Render + Gunicorn

## ✨ Current Features / Functionality
- Source text + optional reference translation workflow
- Complexity routing (SIMPLE / COMPLEX) using the cheap Gemini model
- Two translation outputs per request:
  - DeepL translation
  - Gemini translation
- Rule-based highlighting:
  - SIMPLE => highlight DeepL
  - COMPLEX => highlight Gemini
- Estimated cost per translation with tooltips:
  - DeepL: characters and cost per character
  - Gemini: estimated input/output tokens and per-million-token rates
- Optional ChrF metric shown for each translation when a reference is provided
- Gemini quality score (0-100) shown for each translation, with tooltip attribution
- Support for 15 target languages, including RTL rendering for Arabic
- Dark/light theme toggle with localStorage persistence and copy-to-clipboard actions

## 🛠️ Upcoming Features / Improvements
- Translation history and saved comparison sessions
- Better token accounting via provider-native token counting endpoints
- Customizable complexity routing rules and quality prompts
