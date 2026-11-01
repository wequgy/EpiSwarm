"""Launch EpiSwarm Streamlit App."""

import sys
import subprocess
from pathlib import Path


def main():
    app_path = Path(__file__).resolve().parent.parent / "src" / "episwarm" / "app" / "streamlit_app.py"
    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port=8501",
        "--server.headless=true",
        "--theme.base=light",
    ]
    print(f"Starting EpiSwarm Streamlit UI on http://localhost:8501 ...")
    subprocess.run(cmd)


if __name__ == "__main__":
    main()

