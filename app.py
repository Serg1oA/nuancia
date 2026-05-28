from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv
import os
import time
import requests
import json
import math

load_dotenv()

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)

def env_var(name: str, fallback: str = "") -> str:
    return os.environ.get(name) or os.environ.get(name.lower()) or fallback


GEMINI_API_KEY = env_var("GEMINI_API_KEY")
DEEPL_API_KEY = env_var("DEEPL_API_KEY")
# Free keys end with :fx and must use api-free.deepl.com; override with DEEPL_API_URL if needed.
_default_deepl_base = (
    "https://api-free.deepl.com"
    if DEEPL_API_KEY.endswith(":fx")
    else "https://api.deepl.com"
)
DEEPL_API_URL = env_var("DEEPL_API_URL", _default_deepl_base).rstrip("/")
CHEAP_MODEL_ID = env_var("CHEAP_MODEL_ID", "gemini-2.5-flash")
# Pro model kept for future use; all Gemini calls currently use CHEAP_MODEL_ID.
EXPENSIVE_MODEL_ID = env_var("EXPENSIVE_MODEL_ID", "gemini-2.5-pro")

# Defaults are rough estimates and can be overridden through env vars.
DEEPL_COST_PER_CHAR_USD = float(env_var("DEEPL_COST_PER_CHAR_USD", "0.00002"))
CHEAP_INPUT_COST_PER_MILLION_USD = float(
    env_var("CHEAP_INPUT_COST_PER_MILLION_USD", "0.1")
)
CHEAP_OUTPUT_COST_PER_MILLION_USD = float(
    env_var("CHEAP_OUTPUT_COST_PER_MILLION_USD", "0.4")
)
EXPENSIVE_INPUT_COST_PER_MILLION_USD = float(
    env_var("EXPENSIVE_INPUT_COST_PER_MILLION_USD", "1.25")
)
EXPENSIVE_OUTPUT_COST_PER_MILLION_USD = float(
    env_var("EXPENSIVE_OUTPUT_COST_PER_MILLION_USD", "10.0")
)

LANGUAGE_CONFIG = {
    "arabic": {"name": "Arabic", "deepl": "AR"},
    "chinese": {"name": "Chinese (Simplified)", "deepl": "ZH"},
    "dutch": {"name": "Dutch", "deepl": "NL"},
    "french": {"name": "French", "deepl": "FR"},
    "german": {"name": "German", "deepl": "DE"},
    "italian": {"name": "Italian", "deepl": "IT"},
    "japanese": {"name": "Japanese", "deepl": "JA"},
    "polish": {"name": "Polish", "deepl": "PL"},
    "portuguese_brazil": {"name": "Portuguese (Brazil)", "deepl": "PT-BR"},
    "portuguese_portugal": {"name": "Portuguese (Portugal, European)", "deepl": "PT-PT"},
    "romanian": {"name": "Romanian", "deepl": "RO"},
    "russian": {"name": "Russian", "deepl": "RU"},
    "spanish_latin_america": {"name": "Spanish (Latin America)", "deepl": "ES-419"},
    "spanish_spain": {"name": "Spanish (Spain, European)", "deepl": "ES"},
    "ukranian": {"name": "Ukrainian", "deepl": "UK"},
}


def get_gemini_response(model_id: str, prompt: str, is_json: bool = True) -> str:
    api_url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}"
        f":generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }
    if is_json:
        payload["generationConfig"]["response_mime_type"] = "application/json"

    max_attempts = 4
    retryable_statuses = {429, 500, 503}
    last_response = None

    for attempt in range(1, max_attempts + 1):
        response = requests.post(
            api_url,
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=90,
        )
        last_response = response
        if response.status_code not in retryable_statuses:
            response.raise_for_status()
            body = response.json()
            return body["candidates"][0]["content"]["parts"][0]["text"]

        if attempt < max_attempts:
            wait_s = 2 ** attempt
            app.logger.warning(
                "Gemini model %s returned %s; retrying in %ss (attempt %s/%s)",
                model_id,
                response.status_code,
                wait_s,
                attempt,
                max_attempts,
            )
            time.sleep(wait_s)

    last_response.raise_for_status()


def classify_complexity(source_text: str, target_language_name: str) -> str:
    prompt = f"""Classify translation complexity for this source text into exactly one label: SIMPLE or COMPLEX.

Target language: {target_language_name}
Source text:
\"\"\"{source_text}\"\"\"

Guideline:
- SIMPLE: direct wording, low ambiguity, short/moderate sentence structure.
- COMPLEX: idioms, dense syntax, ambiguity, nuanced tone, specialized terminology, or high context load.

Return JSON only:
{{"complexity":"SIMPLE"}} or {{"complexity":"COMPLEX"}}"""
    raw = get_gemini_response(CHEAP_MODEL_ID, prompt, is_json=True)
    parsed = json.loads(raw)
    complexity = str(parsed.get("complexity", "SIMPLE")).strip().upper()
    return "COMPLEX" if complexity == "COMPLEX" else "SIMPLE"


def translate_with_deepl(source_text: str, target_lang_code: str) -> str:
    response = requests.post(
        f"{DEEPL_API_URL}/v2/translate",
        data={"text": source_text, "target_lang": target_lang_code},
        headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
        timeout=90,
    )
    response.raise_for_status()
    payload = response.json()
    translations = payload.get("translations") or []
    if not translations:
        raise ValueError("DeepL returned an empty response.")
    return str(translations[0].get("text", "")).strip()


def translate_with_gemini(source_text: str, target_language_name: str) -> str:
    prompt = f"""Translate the source text into {target_language_name}.
Return only the translation text. No explanations.

Source text:
\"\"\"{source_text}\"\"\""""
    return get_gemini_response(CHEAP_MODEL_ID, prompt, is_json=False).strip()


def estimate_tokens(text: str) -> int:
    # Rough estimate for mixed-language text.
    return max(1, math.ceil(len(text) / 4))


def estimate_gemini_cost(input_text: str, output_text: str, in_rate: float, out_rate: float):
    in_tokens = estimate_tokens(input_text)
    out_tokens = estimate_tokens(output_text)
    total = (in_tokens / 1_000_000.0) * in_rate + (out_tokens / 1_000_000.0) * out_rate
    return {
        "unit_type": "tokens",
        "input_units": in_tokens,
        "output_units": out_tokens,
        "input_rate_per_million_usd": in_rate,
        "output_rate_per_million_usd": out_rate,
        "amount_usd": round(total, 6),
    }


def estimate_deepl_cost(source_text: str):
    chars = len(source_text)
    total = chars * DEEPL_COST_PER_CHAR_USD
    return {
        "unit_type": "characters",
        "input_units": chars,
        "output_units": None,
        "rate_per_unit_usd": DEEPL_COST_PER_CHAR_USD,
        "amount_usd": round(total, 6),
    }


def char_ngrams(text: str, n: int):
    compact = " ".join(text.strip().split())
    if len(compact) < n:
        return {}
    counts = {}
    for i in range(len(compact) - n + 1):
        ng = compact[i : i + n]
        counts[ng] = counts.get(ng, 0) + 1
    return counts


def chrf_score(reference: str, hypothesis: str, max_n: int = 6, beta: float = 2.0):
    if not reference or not hypothesis:
        return None
    eps = 1e-9
    f_scores = []
    for n in range(1, max_n + 1):
        ref_counts = char_ngrams(reference, n)
        hyp_counts = char_ngrams(hypothesis, n)
        if not ref_counts or not hyp_counts:
            f_scores.append(0.0)
            continue
        overlap = 0
        for ng, h_count in hyp_counts.items():
            overlap += min(h_count, ref_counts.get(ng, 0))
        precision = overlap / (sum(hyp_counts.values()) + eps)
        recall = overlap / (sum(ref_counts.values()) + eps)
        denom = (beta * beta * precision) + recall + eps
        f_val = ((1 + beta * beta) * precision * recall) / denom
        f_scores.append(f_val)
    return round((sum(f_scores) / max_n) * 100.0, 2)


def quality_scores_with_cheap_model(source_text: str, target_language_name: str, deepl_text: str, model_text: str):
    prompt = f"""You are grading translation quality from 0 to 100.
Score each translation for adequacy, fluency, terminology, grammar, and register.

Source text:
\"\"\"{source_text}\"\"\"

Target language: {target_language_name}

Translation A (provider=DEEPL):
\"\"\"{deepl_text}\"\"\"

Translation B (provider=MODEL):
\"\"\"{model_text}\"\"\"

Return JSON only:
{{
  "deepl_quality_score": <integer 0-100>,
  "model_quality_score": <integer 0-100>
}}"""
    raw = get_gemini_response(CHEAP_MODEL_ID, prompt, is_json=True)
    parsed = json.loads(raw)
    deepl_score = int(parsed.get("deepl_quality_score", 0))
    model_score = int(parsed.get("model_quality_score", 0))
    deepl_score = max(0, min(100, deepl_score))
    model_score = max(0, min(100, model_score))
    return deepl_score, model_score


@app.route("/api/check-translations", methods=["POST"])
def check_translations():
    try:
        data = request.get_json() or {}
        source = (data.get("source_text") or data.get("text") or "").strip()
        reference_tr = (data.get("reference_translation") or "").strip()
        target_lang = data.get("target_language") or "spanish_spain"

        if not source:
            return jsonify({"error": "Source text is required"}), 400

        lang_cfg = LANGUAGE_CONFIG.get(target_lang) or LANGUAGE_CONFIG["spanish_spain"]
        target_name = lang_cfg["name"]
        target_deepl_code = lang_cfg["deepl"]

        complexity = classify_complexity(source, target_name)
        deepl_translation = translate_with_deepl(source, target_deepl_code)
        model_translation = translate_with_gemini(source, target_name)
        deepl_quality, model_quality = quality_scores_with_cheap_model(
            source, target_name, deepl_translation, model_translation
        )

        deepl_cost = estimate_deepl_cost(source)
        # Translation runs on flash for now; cost demo uses pro-tier rates.
        gemini_cost = estimate_gemini_cost(
            input_text=source,
            output_text=model_translation,
            in_rate=EXPENSIVE_INPUT_COST_PER_MILLION_USD,
            out_rate=EXPENSIVE_OUTPUT_COST_PER_MILLION_USD,
        )

        highlight_provider = "deepl" if complexity == "SIMPLE" else "model"

        deepl_chrf = chrf_score(reference_tr, deepl_translation) if reference_tr else None
        model_chrf = chrf_score(reference_tr, model_translation) if reference_tr else None

        return jsonify(
            {
                "source_text": source,
                "target_language": target_lang,
                "complexity": complexity,
                "highlighted_provider": highlight_provider,
                "reference_translation": reference_tr if reference_tr else None,
                "translations": [
                    {
                        "provider": "deepl",
                        "label": "DeepL",
                        "text": deepl_translation,
                        "highlighted": highlight_provider == "deepl",
                        "quality_score": deepl_quality,
                        "quality_tooltip": "Quality score from Gemini (0-100).",
                        "chrf_vs_reference": deepl_chrf,
                        "cost": deepl_cost,
                    },
                    {
                        "provider": "model",
                        "label": "Gemini",
                        "text": model_translation,
                        "highlighted": highlight_provider == "model",
                        "quality_score": model_quality,
                        "quality_tooltip": "Quality score from Gemini (0-100).",
                        "chrf_vs_reference": model_chrf,
                        "cost": gemini_cost,
                    },
                ],
                "cost_note": "Cost values are estimated and can differ from final billing.",
            }
        )

    except requests.HTTPError as e:
        app.logger.error("Upstream HTTP error: %s", e)
        detail = str(e)
        if e.response is not None:
            try:
                detail = e.response.json()
            except Exception:
                detail = (e.response.text or str(e))[:300]
        return jsonify({"error": "AI service request failed", "detail": detail}), 502
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
    if not DEEPL_API_KEY:
        raise ValueError("DEEPL_API_KEY environment variable is required")

    host = "0.0.0.0" if os.environ.get("RENDER") else "127.0.0.1"
    app.run(debug=False, host=host, port=5000)
