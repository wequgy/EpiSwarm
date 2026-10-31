"""Headless verification of Streamlit Studio app covering Simulate and Plan modes across all steps (Spec 3.1 & Phase 12)."""

from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest


def test_streamlit_studio_all_steps_headless():
    """Verify that both Simulate and Plan modes run cleanly across all 8 workflow steps."""
    app_path = Path(__file__).resolve().parent.parent / "src" / "episwarm" / "app" / "streamlit_app.py"
    at = AppTest.from_file(str(app_path), default_timeout=30)
    at.run()
    assert not at.exception, f"Initial step failed: {at.exception}"

    # Verify mode selector and workflow navigation radios exist
    assert len(at.sidebar.radio) >= 2, "Expected Studio Mode and Workflow Navigation radios"

    mode_radio = at.sidebar.radio[0]
    nav_radio = at.sidebar.radio[1]

    # Test across both Studio Modes
    for mode_opt in mode_radio.options:
        mode_radio.set_value(mode_opt)
        at.run()
        assert not at.exception, f"Error switching to mode '{mode_opt}': {at.exception}"

        # Step through every workflow step in this mode
        for step_opt in nav_radio.options:
            nav_radio.set_value(step_opt)
            at.run()
            assert not at.exception, f"Error on page '{step_opt}' in mode '{mode_opt}': {at.exception}"
