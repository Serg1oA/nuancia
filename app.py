from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

# Updated variable name to be consistent
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Using Gemini 2.5 Flash - working as of June 2026
MODEL_ID = "gemini-2.5-flash"

def get_gemini_response(prompt, is_json=True):
    """Helper to handle Google API calls with optional JSON mode"""
    API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}:generateContent?key={GEMINI_API_KEY}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.2, # Lower temperature for consistency
        }
    }
    
    if is_json:
        payload["generationConfig"]["response_mime_type"] = "application/json"

    response = requests.post(
        API_URL,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    response.raise_for_status()
    res_json = response.json()
    return res_json['candidates'][0]['content']['parts'][0]['text']

def analyze_emotion(text):
    """Analyze emotion using Gemini API with strict JSON mode"""
    prompt = f"""Analyze the emotions in this text: "{text}"
    Respond with a JSON array of objects with "label" and "score" (0.0 to 1.0).
    Labels: joy, sadness, anger, fear, surprise, disgust, neutral.
    Only include emotions with score >= 0.1."""
    
    try:
        raw_output = get_gemini_response(prompt, is_json=True)
        return json.loads(raw_output) # Returns a list of dicts
    except Exception as e:
        app.logger.error(f"Emotion analysis failed: {e}")
        return {"error": str(e)}

def translate_text_multiple_ways(text, target_language, top_emotions):
    """Generate 3 translations using Gemini API with structural JSON enforcement"""
    language_names = {
        "arabic": "Arabic", "chinese": "Chinese", "dutch": "Dutch",
        "french": "French", "german": "German", "italian": "Italian",
        "japanese": "Japanese", "polish": "Polish", "portuguese_brazil": "Portuguese (Brazil)",
        "portuguese_portugal": "Portuguese (Portugal)", "romanian": "Romanian",
        "russian": "Russian", "spanish_latin_america": "Spanish (Latin America)",
        "spanish_spain": "Spanish (Spain)", "ukranian": "Ukrainian"
    }
    
    lang_name = language_names.get(target_language, "Spanish")
    emotion_str = ", ".join([f"{e['label']} ({e['score']})" for e in top_emotions])

    prompt = f"""Translate this text into {lang_name}: "{text}"
    Contextual Emotions: {emotion_str}
    
    Provide 3 distinct translations in a JSON object with the following keys:
    "literal": A precise direct translation.
    "idiomatic": How a native speaker would naturally say it.
    "poetic": Evocative, focusing on the mood.
    
    Respond ONLY with the JSON object."""

    try:
        raw_output = get_gemini_response(prompt, is_json=True)
        return json.loads(raw_output)
    except Exception as e:
        app.logger.error(f"Translation failed: {e}")
        return None

@app.route('/api/translate', methods=['POST'])
def translate_with_emotions():
    try:
        data = request.get_json()
        text = data.get('text', '').strip()
        target_lang = data.get('target_language', 'spanish_spain')

        if not text:
            return jsonify({'error': 'No text provided'}), 400

        # 1. Get Emotions
        emotions_data = analyze_emotion(text)
        if isinstance(emotions_data, dict) and 'error' in emotions_data:
            return jsonify(emotions_data), 500
        
        # Sort and Format for the UI
        top_emotions = sorted(emotions_data, key=lambda x: x['score'], reverse=True)
        formatted_emotions = [
            {'label': e['label'].capitalize(), 'score': e['score']} 
            for e in top_emotions
        ]

        # 2. Get Translations
        translations_dict = translate_text_multiple_ways(text, target_lang, formatted_emotions)
        
        if not translations_dict:
            return jsonify({'error': 'Translation failed'}), 500

        # Format translations for your frontend expectations
        response_translations = [
            {'type': 'Literal', 'text': translations_dict.get('literal')},
            {'type': 'Idiomatic', 'text': translations_dict.get('idiomatic')},
            {'type': 'Poetic', 'text': translations_dict.get('poetic')}
        ]

        return jsonify({
            'original_text': text,
            'top_emotions': formatted_emotions,
            'translations': response_translations
        })

    except Exception as e:
        app.logger.error(f"Request failed: {e}")
        return jsonify({'error': str(e)}), 500

# --- Static File Serving ---
@app.route("/")
def serve_index(): return send_from_directory(app.static_folder, 'index.html')

@app.route("/<path:path>")
def serve_static(path): return send_from_directory(app.static_folder, path)

if __name__ == '__main__':
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    # Check if running on Render.com or locally
    host = '0.0.0.0' if os.environ.get('RENDER') else '127.0.0.1'
    app.run(debug=False, host=host, port=5000)