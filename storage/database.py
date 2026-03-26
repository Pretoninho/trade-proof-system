# storage/database.py
# Local CSV-based persistence layer for trade signals.
#
# Signals are appended to a CSV file so that the track record survives
# across Streamlit restarts.  Upgrade to a proper database (SQLite,
# PostgreSQL, …) by replacing these two functions without touching the
# rest of the codebase.

from __future__ import annotations

import os

import pandas as pd

DB_FILE = "signals.csv"


def save_signal(signal_data: dict) -> None:
    """Append *signal_data* as a new row to the signals CSV.

    Args:
        signal_data: Dictionary whose keys become column names.  Must
                     contain at least the fields produced by
                     :func:`models.tracking.create_signal_record`.
    """
    df = pd.DataFrame([signal_data])

    if os.path.exists(DB_FILE):
        df.to_csv(DB_FILE, mode="a", header=False, index=False)
    else:
        df.to_csv(DB_FILE, index=False)


def load_signals() -> pd.DataFrame:
    """Load all stored signals from the CSV.

    Returns:
        :class:`pandas.DataFrame` with all signal rows, or an empty
        DataFrame when no signals have been saved yet.
    """
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)

    return pd.DataFrame()
