from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
load_dotenv()
import os
import requests
import json
import re

app = Flask(__name__, static_folder="static", static_url_path="")  # important
CORS(app)

HF_TOKEN = os.environ.get('HF_TOKEN')
TRANSLATION_PROMPT_API_KEY = os.environ.get('TRANSLATION_PROMPT_API_KEY')

def analyze_emotion(text):
    # Analyze emotion using HuggingFace API
    try:
        response = requests.post(
            "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base",
            headers={"Authorization": f"Bearer {HF_TOKEN}"},
            json={"inputs": text},
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result
    except requests.exceptions.RequestException as e:
        return {'error': f"Emotion analysis failed: {e}"}

def translate_text_multiple_ways(text, target_language, top_emotions):
    # Translate text in 3 different ways using the Gemini 2.0 Flash API
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={TRANSLATION_PROMPT_API_KEY}"

    # Map target language to language name
    language_names = {
        "arabic": "Arabic",
        "chinese": "Chinese",
        "french": "French",
        "german": "German",
        "japanese": "Japanese",
        "portuguese_portugal": "Portuguese (Portugal, European)",
        "portuguese_brazil": "Portuguese (Brazil)",
        "russian": "Russian",
        "spanish_spain": "Spanish (Spain, European)",
        "spanish_latin_america": "Spanish (Latin America)",
    }

    language_name = language_names.get(target_language)

    if not language_name:
        return [{"error": f"No language name found for '{target_language}'"}] * 3

    # Create emotion description for the prompt
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
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
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

        try:
            full_response = json_response['candidates'][0]['content']['parts'][0]['text']
            
            # Parse the response to extract the 3 translations
            translations = []
            lines = full_response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line:
                    # Remove numbering (1., 2., 3., 1:, 2:, 3:, etc.)
                    clean_line = re.sub(r'^[0-9]+[\.\:\)]\s*', '', line)
                    if clean_line:
                        translations.append(clean_line)
            
            # Ensure we have exactly 3 translations
            if len(translations) < 3:
                # If we couldn't parse properly, split by common patterns
                parts = re.split(r'[0-9]+[\.\:\)]\s*', full_response)
                translations = [part.strip() for part in parts if part.strip()]
            
            # Take first 3 or pad if needed
            while len(translations) < 3:
                translations.append(full_response.strip())
            
            return translations[:3]
            
        except (KeyError, IndexError, TypeError) as json_err:
            error_msg = f"Translation failed: Invalid JSON response - {json_err}"
            return [error_msg] * 3

    except requests.exceptions.RequestException as e:
        error_msg = f"Translation failed: {e}"
        return [error_msg] * 3

@app.route('/api/translate', methods=['POST'])
def translate_with_emotions():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        target_language = data.get('target_language', 'spanish')

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # 1. Analyze emotions of the original text using HuggingFace
        emotion_analysis = analyze_emotion(text)
        
        if not emotion_analysis or 'error' in emotion_analysis:
            return jsonify({'error': 'Emotion analysis failed'}), 500

        # Sort emotions by score
        try:
            all_emotions = sorted(emotion_analysis[0], key=lambda x: x['score'], reverse=True)
            # Filter emotions with score >= 0.1 (10%) and capitalize labels
            top_emotions = []
            for emotion in all_emotions:
                if emotion['score'] >= 0.1:
                    top_emotions.append({
                        'label': emotion['label'].capitalize(),
                        'score': emotion['score']
                    })
        except (IndexError, KeyError, TypeError):
            # Fallback if emotion analysis format is unexpected
            top_emotions = []

        # 2. Generate 3 translations using Gemini with emotion context
        translation_results = translate_text_multiple_ways(text, target_language, top_emotions)
        
        # Format the translations
        translations = []
        for i, translation_text in enumerate(translation_results):
            translations.append({
                'type': '',
                'text': translation_text
            })

        return jsonify({
            'original_text': text,
            'top_emotions': top_emotions,
            'translations': translations
        })

    except Exception as e:
        return jsonify({'error': f'Translation failed: {str(e)}'}), 500

@app.route("/")
def serve_static():
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    host = '0.0.0.0' if os.environ.get('RENDER') else '127.0.0.1'
    app.run(debug=True, host=host, port=5000)