"""Diagnostic script to test external LLM / decision API connectivity.

Never prints API keys or credentials.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()


def check_typesafe_api() -> bool:
    """Test connection to TypeSafe AI Jev endpoint."""
    key = os.getenv("TYPESAFE_API_KEY")
    url = os.getenv("TYPESAFE_API_URL", "https://api.typesafe.ai/v1/systemone")

    if not key:
        print("[TYPESAFE AI JEV] SKIPPED: TYPESAFE_API_KEY not configured in .env")
        return False

    import requests
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "jev-latest",
        "question": "Should non-essential travel be reduced?",
        "options": ["yes", "no"]
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=5)
        if resp.status_code == 200:
            print("[TYPESAFE AI JEV] OK: Connected and returned 200")
            return True
        else:
            print(f"[TYPESAFE AI JEV] FAIL: Server returned status {resp.status_code}")
            return False
    except Exception as e:
        print(f"[TYPESAFE AI JEV] FAIL: Connection error ({type(e).__name__})")
        return False


def check_gemini_api() -> bool:
    """Test connection to Google Gemini API."""
    key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    if not key:
        print("[GOOGLE GEMINI]   SKIPPED: GEMINI_API_KEY not configured in .env")
        return False

    import requests
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    payload = {
        "contents": [{"parts": [{"text": "ping"}]}]
    }
    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=5)
        if resp.status_code == 200:
            print(f"[GOOGLE GEMINI]   OK: Connected to {model} (200 OK)")
            return True
        else:
            print(f"[GOOGLE GEMINI]   FAIL: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"[GOOGLE GEMINI]   FAIL: Connection error ({type(e).__name__})")
        return False


def check_openai_compat_api() -> bool:
    """Test connection to OpenAI-compatible endpoint."""
    key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    if not key:
        print("[OPENAI COMPAT]   SKIPPED: OPENAI_API_KEY not configured in .env")
        return False

    import requests
    url = f"{base_url.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {key}"}
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            print(f"[OPENAI COMPAT]   OK: Connected to {base_url} (200 OK)")
            return True
        else:
            print(f"[OPENAI COMPAT]   FAIL: Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"[OPENAI COMPAT]   FAIL: Connection error ({type(e).__name__})")
        return False


def main():
    print("=== EpiSwarm API Health Check ===")
    results = [
        check_typesafe_api(),
        check_gemini_api(),
        check_openai_compat_api()
    ]
    configured_any = any(os.getenv(k) for k in ["TYPESAFE_API_KEY", "GEMINI_API_KEY", "OPENAI_API_KEY"])
    if not configured_any:
        print("\nNotice: No external LLM keys configured in .env. Engine will utilize RulePolicy by default.")


if __name__ == "__main__":
    main()
