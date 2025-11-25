# Nuancia
### Live demo: https://nuancia.onrender.com

## 🔤 What is this project about?
Nuancia is an emotion-aware translation tool that analyzes the emotional tone of text and generates three different translation styles: literal, idiomatic, and poetic. It uses AI to detect emotions like joy, sadness, or anger in the source text and adapts the translation to preserve emotional nuance across 15 languages.

## 💻 Technologies Utilized
- **Backend**: Flask, Python
- **AI/ML**: Google Gemini 2.0 Flash API for emotion analysis and translation
- **Frontend**: Vanilla JavaScript, CSS with dark mode support
- **Deployment**: Render

## ✨ Current Features / Functionality
- Emotion detection with confidence scores (joy, sadness, anger, fear, surprise, disgust, neutral)
- Three translation variants per request (literal, idiomatic, poetic)
- Visual emotion bars showing detected emotional content
- Support for 15 languages including Arabic (RTL support), Chinese, Spanish, French, German, and more
- Dark/light theme toggle with localStorage persistence
- Copy-to-clipboard functionality for translations

## 🛠️ Upcoming Features / Improvements
- Translation history tracking
- Custom emotion-to-style mapping preferences
