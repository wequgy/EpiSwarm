"""Data loaders for CSV and multi-sheet Excel files."""

from pathlib import Path
from typing import Dict, Union
import pandas as pd

from episwarm.importers.templates import CSV_CONTRACTS


def load_csv_table(file_path: Union[str, Path]) -> pd.DataFrame:
    """Load a CSV file with automatic delimiter and encoding detection."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Fallback encoding attempts
    encodings = ["utf-8", "latin1", "cp1252"]
    for enc in encodings:
        try:
            return pd.read_csv(file_path, encoding=enc)
        except UnicodeDecodeError:
            continue

    raise ValueError(f"Could not decode file {file_path} with supported encodings {encodings}")


def load_excel_workbook(file_path: Union[str, Path]) -> Dict[str, pd.DataFrame]:
    """Load an Excel workbook, matching sheet names to known CSV contracts."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Workbook not found: {file_path}")

    xls = pd.ExcelFile(file_path)
    tables: Dict[str, pd.DataFrame] = {}

    for sheet_name in xls.sheet_names:
        clean_name = sheet_name.strip().lower()
        # Match sheet name to contract
        matched_filename = None
        for contract_file in CSV_CONTRACTS.keys():
            stem = contract_file.replace(".csv", "")
            if clean_name == stem or clean_name == contract_file:
                matched_filename = contract_file
                break

        target_key = matched_filename if matched_filename else f"{clean_name}.csv"
        tables[target_key] = pd.read_excel(xls, sheet_name=sheet_name)

    return tables
