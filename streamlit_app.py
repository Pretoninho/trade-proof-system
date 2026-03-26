# streamlit_app.py
# Entry-point for Streamlit Cloud deployment.
#
# Run locally with:
#   streamlit run streamlit_app.py
#
# Delegates execution to dashboard/app.py so that all logic
# remains in one place and there is no code duplication.

import pathlib
import runpy

runpy.run_path(
    str(pathlib.Path(__file__).parent / "dashboard" / "app.py"),
    run_name="__main__",
)
