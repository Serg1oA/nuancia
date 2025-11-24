from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import json
import re

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

GEMINI_API_KEY = os.environ.get('TRANSLATION_PROMPT_API_KEY')

def analyze_emotion(text):
    """Analyze emotion using Gemini API"""
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    prompt = f"""Analyze the emotions in this text: "{text}"

Identify the primary emotions present and assign a confidence score (0.0 to 1.0) for each emotion.

Respond ONLY with a JSON array in this exact format (no other text):
[
  {{"label": "joy", "score": 0.8}},
  {{"label": "surprise", "score": 0.3}}
]

Use these emotion labels: joy, sadness, anger, fear, surprise, disgust, neutral.
Only include emotions with score >= 0.1"""

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(
            API_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(data),
            timeout=30,
        )
        response.raise_for_status()
        json_response = response.json()
        
        emotion_text = json_response['candidates'][0]['content']['parts'][0]['text'].strip()
        emotion_text = re.sub(r'```json\s*|\s*```', '', emotion_text).strip()
        emotions = json.loads(emotion_text)
        
        return [emotions]
        
    except Exception as e:
        app.logger.error(f"Emotion analysis failed: {e}")
        return {'error': str(e)}

def translate_text_multiple_ways(text, target_language, top_emotions):
    """Generate 3 translations using Gemini API with emotional context"""
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    
    language_names = {
        "arabic": "Arabic",
        "chinese": "Chinese",
        "dutch": "Dutch",
        "french": "French",
        "german": "German",
        "italian": "Italian",
        "japanese": "Japanese",
        "polish": "Polish",
        "portuguese_brazil": "Portuguese (Brazil)",
        "portuguese_portugal": "Portuguese (Portugal, European)",
        "romanian": "Romanian",
        "russian": "Russian",
        "spanish_latin_america": "Spanish (Latin America)",
        "spanish_spain": "Spanish (Spain, European)",
        "ukranian": "Ukranian"
    }
    
    language_name = language_names.get(target_language)
    if not language_name:
        return [f"Unsupported language: {target_language}"] * 3
    
    emotion_description = ""
    if top_emotions:
        emotion_parts = []
        for emotion in top_emotions:
            percentage = f"{emotion['score'] * 100:.1f}%"
            emotion_parts.append(f"{percentage} of {emotion['label'].lower()}")
        emotion_description = f" ({', '.join(emotion_parts)})"
    
    prompt = f"""You are a world-class translator and linguist with a deep understanding of emotional nuance and cultural context. Your task is to provide three distinct, high-quality translations of the provided text.

Original Text: "{text}"
Source Emotions Detected: "{emotion_description}"
Target Language: "{language_name}"

First, analyze the original text and its context to pinpoint the precise emotional undertone. Then, using your deep knowledge of the target language, generate three unique translations that each capture the source emotion.

Each translation should represent a different stylistic approach:
1.  **The Literal Translation:** A direct, precise translation that maintains the emotional intent and is faithful to the original wording and structure.
2.  **The Idiomatic Translation:** A natural-sounding translation that a native speaker of the target language would use to express the same emotion. This version should feel authentic and fluid, even if it deviates from the original phrasing.
3.  **The Poetic Translation:** A more evocative and nuanced translation that focuses on the underlying feeling or mood. This version may use figurative language, metaphor, or a different rhythm to convey the emotion on a deeper level.

Please provide exactly and only three translations, each on a new line, numbered 1, 2, and 3, without any additional commentary."""

    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(
            API_URL,
            headers={"Content-Type": "application/json"},
            data=json.dumps(data),
            timeout=60,
        )
        response.raise_for_status()
        json_response = response.json()
        
        full_response = json_response['candidates'][0]['content']['parts'][0]['text']
        
        # Parse the response to extract the 3 translations
        translations = []
        lines = full_response.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line:
                clean_line = re.sub(r'^[0-9]+[\.\:\)]\s*\*?\*?', '', line)
                clean_line = re.sub(r'\*\*.*?\*\*:?\s*', '', clean_line)
                if clean_line:
                    translations.append(clean_line)
        
        # Ensure we have exactly 3 translations
        if len(translations) < 3:
            parts = re.split(r'[0-9]+[\.\:\)]\s*', full_response)
            translations = [part.strip() for part in parts if part.strip()]
        
        while len(translations) < 3:
            translations.append(full_response.strip())
        
        return translations[:3]
        
    except Exception as e:
        app.logger.error(f"Translation failed: {e}")
        return [f"Translation error: {str(e)}"] * 3

@app.route('/api/translate', methods=['POST'])
def translate_with_emotions():
    """Main endpoint for emotion-aware translation"""
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        target_language = data.get('target_language', 'spanish_spain')

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # Analyze emotions
        emotion_analysis = analyze_emotion(text)
        
        top_emotions = []
        if emotion_analysis and 'error' not in emotion_analysis:
            try:
                all_emotions = sorted(emotion_analysis[0], key=lambda x: x['score'], reverse=True)
                top_emotions = [
                    {
                        'label': emotion['label'].capitalize(),
                        'score': emotion['score']
                    }
                    for emotion in all_emotions if emotion['score'] >= 0.1
                ]
            except (IndexError, KeyError, TypeError) as e:
                app.logger.warning(f"Could not process emotions: {e}")

        # Generate translations
        translation_results = translate_text_multiple_ways(text, target_language, top_emotions)
        
        translations = [
            {'type': '', 'text': translation_text}
            for translation_text in translation_results
        ]

        return jsonify({
            'original_text': text,
            'top_emotions': top_emotions,
            'translations': translations
        })

    except Exception as e:
        app.logger.error(f"Request failed: {e}")
        return jsonify({'error': f'Translation failed: {str(e)}'}), 500

@app.route("/")
def serve_static():
    return send_from_directory(app.static_folder, 'index.html')

@app.route("/style.css")
def serve_css():
    return send_from_directory(app.static_folder, 'style.css', mimetype='text/css')

@app.route("/script.js")
def serve_js():
    return send_from_directory(app.static_folder, 'script.js', mimetype='application/javascript')

if __name__ == '__main__':
    if not GEMINI_API_KEY:
        raise ValueError("TRANSLATION_PROMPT_API_KEY environment variable is required")
    
    host = '0.0.0.0' if os.environ.get('RENDER') else '127.0.0.1'
    app.run(debug=False, host=host, port=5000)