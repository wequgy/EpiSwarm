"""Headless verification of Streamlit Studio app using AppTest."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


def test_streamlit_studio_all_steps_headless():
    app_path = Path(__file__).resolve().parent.parent / "src" / "episwarm" / "app" / "streamlit_app.py"
    at = AppTest.from_file(str(app_path), default_timeout=30)
    at.run()
    assert not at.exception, f"Initial step failed: {at.exception}"

    # Verify radio buttons exist
    assert len(at.sidebar.radio) > 0
    radio = at.sidebar.radio[0]
    options = radio.options

    # Step through every workflow step in the UI
    for opt in options:
        radio.set_value(opt)
        at.run()
        assert not at.exception, f"Error on page '{opt}': {at.exception}"
