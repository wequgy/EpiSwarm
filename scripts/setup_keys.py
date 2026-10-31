"""Interactive setup script to safely configure API keys in local .env file.

Uses getpass for secure hidden entry. Never prints or logs credentials.
"""

import getpass
import os
from pathlib import Path


def main():
    env_path = Path(".env")
    print("==============================================================")
    print("          EpiSwarm Studio - Secure Local API Setup            ")
    print("==============================================================")
    print("This utility securely stores your keys in your local .env file.")
    print("Your keys are NEVER printed, logged, or sent to any server.")
    print("Press Enter to skip any key you do not wish to configure.\n")

    current_env = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                current_env[k.strip()] = v.strip()

    # 1. Google Gemini Key
    gemini_prompt = "Google Gemini API Key (Enter to keep current / skip): "
    gemini_key = getpass.getpass(prompt=gemini_prompt).strip()
    if gemini_key:
        current_env["GEMINI_API_KEY"] = gemini_key
    elif "GEMINI_API_KEY" not in current_env:
        current_env["GEMINI_API_KEY"] = ""

    if "GEMINI_MODEL" not in current_env:
        current_env["GEMINI_MODEL"] = "gemini-1.5-flash"

    # 2. Local LLM Endpoint
    local_url = input(f"Local LLM URL [default: {current_env.get('LOCAL_LLM_BASE_URL', 'http://localhost:11434')}]: ").strip()
    if local_url:
        current_env["LOCAL_LLM_BASE_URL"] = local_url
    elif "LOCAL_LLM_BASE_URL" not in current_env:
        current_env["LOCAL_LLM_BASE_URL"] = "http://localhost:11434"

    local_model = input(f"Local LLM Model [default: {current_env.get('LOCAL_LLM_MODEL', 'llama3.2:1b')}]: ").strip()
    if local_model:
        current_env["LOCAL_LLM_MODEL"] = local_model
    elif "LOCAL_LLM_MODEL" not in current_env:
        current_env["LOCAL_LLM_MODEL"] = "llama3.2:1b"

    # 3. TypeSafe AI Jev Key (Optional)
    jev_key = getpass.getpass(prompt="TypeSafe AI Jev Key (Optional, Enter to skip): ").strip()
    if jev_key:
        current_env["TYPESAFE_API_KEY"] = jev_key
    elif "TYPESAFE_API_KEY" not in current_env:
        current_env["TYPESAFE_API_KEY"] = ""

    # Write securely
    lines = [
        "# EpiSwarm Studio Local Configuration",
        "# Generated securely by scripts/setup_keys.py",
        f"GEMINI_API_KEY={current_env.get('GEMINI_API_KEY', '')}",
        f"GEMINI_MODEL={current_env.get('GEMINI_MODEL', 'gemini-1.5-flash')}",
        f"LOCAL_LLM_BASE_URL={current_env.get('LOCAL_LLM_BASE_URL', 'http://localhost:11434')}",
        f"LOCAL_LLM_MODEL={current_env.get('LOCAL_LLM_MODEL', 'llama3.2:1b')}",
        f"TYPESAFE_API_KEY={current_env.get('TYPESAFE_API_KEY', '')}",
        f"TYPESAFE_API_URL={current_env.get('TYPESAFE_API_URL', 'https://api.typesafe.ai/v1/systemone')}",
        f"OPENAI_COMPAT_API_KEY={current_env.get('OPENAI_COMPAT_API_KEY', '')}",
        f"OPENAI_COMPAT_BASE_URL={current_env.get('OPENAI_COMPAT_BASE_URL', 'https://api.openai.com/v1')}",
        f"OPENAI_COMPAT_MODEL={current_env.get('OPENAI_COMPAT_MODEL', 'gpt-4o-mini')}",
    ]
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n[SUCCESS] Configuration written to .env safely.")
    print("You can verify connectivity at any time with: python scripts/check_apis.py")


if __name__ == "__main__":
    main()
