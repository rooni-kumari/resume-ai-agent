"""llm.py - the ONLY file that talks to the Gemini API."""
import os
import re
import json
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
# Optional backup model, used on alternate tries when the main one is overloaded (503)
FALLBACK = os.getenv("GEMINI_FALLBACK_MODEL")
MODELS = [MODEL] + ([FALLBACK] if FALLBACK else [])
_client = None


def _get_key():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        try:  # when deployed on Streamlit Cloud the key lives in st.secrets
            import streamlit as st
            key = st.secrets.get("GEMINI_API_KEY")
        except Exception:
            key = None
    return key


def get_client():
    global _client
    if _client is None:
        key = _get_key()
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY not found. Create a .env file with "
                "GEMINI_API_KEY=your_key (see the guide, Part 2)."
            )
        _client = genai.Client(api_key=key)
    return _client


def parse_json(text):
    """Turn the model's reply into a Python dict/list, even if it adds ```json fences."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = min([i for i in (text.find("{"), text.find("[")) if i != -1] or [0])
        end = max(text.rfind("}"), text.rfind("]")) + 1
        return json.loads(text[start:end])


def ask(prompt, system=None, as_json=False, retries=6):
    """Send one prompt to Gemini. Returns text, or a dict/list if as_json=True."""
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=0.3,
        response_mime_type="application/json" if as_json else "text/plain",
    )
    last_error = None
    for attempt in range(retries):
        model = MODELS[attempt % len(MODELS)]
        try:
            response = get_client().models.generate_content(
                model=model, contents=prompt, config=config
            )
            text = response.text or ""
            return parse_json(text) if as_json else text
        except Exception as e:  # overloaded (503), rate limit (429), bad JSON ...
            last_error = e
            if attempt < retries - 1:
                time.sleep(min(4 * (attempt + 1), 15))  # wait 4s, 8s, 12s, 15s ...
    raise RuntimeError(f"Gemini call failed after {retries} tries: {last_error}")