from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
import re
import requests
import json
import math
from collections import Counter

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL_ID = "gemini-2.5-flash"

CONTENT_TYPE_GUIDANCE = {
    "marketing": "Marketing copy: punchy, brand-safe, persuasive, audience-focused; keep slogans and CTAs natural.",
    "legal": "Legal register: precise terminology, conservative wording, no unintended commitments; mirror formal structure.",
    "technical": "Technical documentation: clarity, consistency, correct domain terms, unambiguous instructions.",
    "literary": "Literary style: voice, rhythm, imagery, and idiomatic richness appropriate to narrative or dialogue.",
}

LANGUAGE_NAMES = {
    "arabic": "Arabic",
    "chinese": "Chinese (Simplified)",
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
    "ukranian": "Ukrainian",
}


def get_gemini_response(prompt, is_json=True):
    API_URL = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_ID}"
        f":generateContent?key={GEMINI_API_KEY}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.35,
        },
    }

    if is_json:
        payload["generationConfig"]["response_mime_type"] = "application/json"

    response = requests.post(
        API_URL,
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=90,
    )
    response.raise_for_status()
    res_json = response.json()
    return res_json["candidates"][0]["content"]["parts"][0]["text"]


def tokenize_bleu(text):
    if not text:
        return []
    return re.findall(r"\w+|[^\w\s]", text.lower(), flags=re.UNICODE)


def ngram_counts(tokens, n):
    if len(tokens) < n:
        return Counter()
    return Counter(tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1))


def sentence_bleu(reference, hypothesis, max_n=4):
    """
    Sentence-level BLEU (0–100) against a single reference, with epsilon smoothing
    when an n-gram order has zero clipped count.
    """
    ref_t = tokenize_bleu(reference)
    hyp_t = tokenize_bleu(hypothesis)
    if not hyp_t or not ref_t:
        return 0.0

    weights = [1.0 / max_n] * max_n
    log_precisions = []
    eps = 1e-9
    for n in range(1, max_n + 1):
        hyp_counts = ngram_counts(hyp_t, n)
        ref_counts = ngram_counts(ref_t, n)
        if not hyp_counts:
            log_precisions.append(math.log(eps))
            continue
        clipped = 0
        total = 0
        for ng, cnt in hyp_counts.items():
            total += cnt
            clipped += min(cnt, ref_counts.get(ng, 0))
        if clipped == 0:
            clipped = eps
            total = max(total, 1.0)
        log_precisions.append(math.log(clipped / total))

    r_len, h_len = len(ref_t), len(hyp_t)
    if h_len > r_len:
        bp = 1.0
    else:
        bp = math.exp(1.0 - float(r_len) / max(h_len, 1))

    log_geo = sum(w * lp for w, lp in zip(weights, log_precisions))
    score = bp * math.exp(log_geo)
    return max(0.0, min(100.0, score * 100.0))


def levenshtein_distance(a: str, b: str) -> int:
    """Character-level edit distance (insert/delete/substitute)."""
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            cur.append(
                min(
                    prev[j] + 1,
                    cur[j - 1] + 1,
                    prev[j - 1] + cost,
                )
            )
        prev = cur
    return prev[-1]


def fetch_translation_suggestions(source_text, target_language, content_type):
    lang_name = LANGUAGE_NAMES.get(target_language, "Spanish (Spain, European)")
    style_guide = CONTENT_TYPE_GUIDANCE.get(
        content_type, CONTENT_TYPE_GUIDANCE["technical"]
    )

    prompt = f"""You are an expert translator and translation-quality advisor.

Source text (translate FROM this language — preserve meaning and appropriate register):
\"\"\"{source_text}\"\"\"

Target language: {lang_name}
Content type: {content_type.replace("_", " ").title()}
Style and constraints: {style_guide}

Return a JSON object with exactly these keys:
- "reference_for_scoring": one faithful, fluent translation in {lang_name} that best preserves the source meaning. This string is used only as an automatic scoring reference; it should be a strong baseline translation.
- "suggestions": an array of exactly 3 objects, each with:
  - "label": a short human-readable label for the approach (e.g. "Concise marketing", "Formal legal")
  - "text": the full translation in {lang_name}

The three suggestions must be distinct high-quality options appropriate to the content type, ranked from best overall fit (index 0) to still-strong alternatives (index 2).

Respond ONLY with valid JSON, no markdown."""

    raw = get_gemini_response(prompt, is_json=True)
    data = json.loads(raw)
    ref = (
        (data.get("reference_for_scoring") or data.get("reference_for_bleu") or data.get("reference_translation") or "")
        .strip()
    )
    items = data.get("suggestions") or []
    cleaned = []
    for it in items[:3]:
        if isinstance(it, dict) and it.get("text"):
            cleaned.append(
                {
                    "label": (it.get("label") or "Suggestion").strip(),
                    "text": str(it["text"]).strip(),
                }
            )
    return ref, cleaned


@app.route("/api/check-translations", methods=["POST"])
def check_translations():
    try:
        data = request.get_json() or {}
        source = (data.get("source_text") or data.get("text") or "").strip()
        user_tr = (data.get("user_translation") or "").strip()
        content_type = (data.get("content_type") or "technical").lower()
        target_lang = data.get("target_language") or "spanish_spain"

        if not source:
            return jsonify({"error": "Source text is required"}), 400

        if content_type not in CONTENT_TYPE_GUIDANCE:
            return jsonify({"error": "Invalid content_type"}), 400

        reference, suggestions = fetch_translation_suggestions(
            source, target_lang, content_type
        )

        if len(suggestions) < 3 or not reference:
            return jsonify({"error": "Could not obtain three suggestions from the model"}), 500

        ai_rows = []
        for i, sug in enumerate(suggestions):
            bleu_ai = sentence_bleu(reference, sug["text"])
            row = {
                "rank": i + 1,
                "label": sug["label"],
                "text": sug["text"],
                "bleu_vs_reference": round(bleu_ai, 2),
            }
            if user_tr:
                row["edit_distance_from_user"] = levenshtein_distance(user_tr, sug["text"])
            ai_rows.append(row)

        user_bleu = None
        if user_tr:
            user_bleu = round(sentence_bleu(reference, user_tr), 2)

        return jsonify(
            {
                "source_text": source,
                "content_type": content_type,
                "target_language": target_lang,
                "user_translation": user_tr if user_tr else None,
                "user_bleu_vs_reference": user_bleu,
                "suggestions": ai_rows,
                "metrics_note": "BLEU is sentence-level against a model baseline translation (reference_for_scoring), on a 0–100 scale. Higher means closer to that baseline, not necessarily subjective 'better'.",
            }
        )

    except requests.HTTPError as e:
        app.logger.error("Gemini HTTP error: %s", e)
        return jsonify({"error": "AI service request failed"}), 502
    except Exception as e:
        app.logger.error("check_translations failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/")
def serve_index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")

    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    app.run(debug=False, host=host, port=5000)
