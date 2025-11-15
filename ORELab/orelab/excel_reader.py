"""
Excel reader module for loading trade data from Excel files.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional, List
import warnings

from .config import SHEET_NAMES, REQUIRED_COLUMNS


class ExcelTradeReader:
    """
    Read trade data from Excel file.

    Expected Excel structure:
    - Multiple sheets, one per trade type
    - Sheet names defined in config.SHEET_NAMES
    - Each sheet has columns defined in config.REQUIRED_COLUMNS
    """

    def __init__(self, excel_path: str):
        """
        Initialize Excel reader.

        Args:
            excel_path: Path to Excel file

        Raises:
            FileNotFoundError: If Excel file doesn't exist
        """
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        self._data: Dict[str, pd.DataFrame] = {}
        self._trade_types: List[str] = []
        self._warnings: List[str] = []

    def read_all(self) -> Dict[str, pd.DataFrame]:
        """
        Read all trade sheets from Excel file.

        Returns:
            Dictionary mapping sheet names to DataFrames

        Raises:
            ValueError: If Excel file cannot be read
        """
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(self.excel_path, engine='openpyxl')
            available_sheets = excel_file.sheet_names

            for sheet_name in available_sheets:
                df = pd.read_excel(
                    excel_file,
                    sheet_name=sheet_name,
                    dtype=str  # Read as strings initially for validation
                )

                # Basic cleanup
                df = self._clean_dataframe(df)

                # Validate columns
                if 'TradeType' in df.columns:
                    trade_type = df['TradeType'].unique()
                    if len(trade_type) > 1:
                        self._warnings.append(
                            f"Sheet '{sheet_name}': Multiple TradeTypes found {trade_type}. "
                            "This may lead to validation issues."
                        )
                    else:
                        sheet_name = trade_type[0]
                        self._trade_types.append(sheet_name)
                        missing_cols = self._validate_columns(sheet_name, df)
                        if missing_cols:
                            self._warnings.append(
                                f"Sheet '{sheet_name}': Missing columns {missing_cols}. "
                                "Trades may fail validation."
                            )

                # Store non-empty dataframes
                if not df.empty:
                    self._data[sheet_name] = df
                else:
                    self._warnings.append(f"Sheet '{sheet_name}' is empty, skipping.")

            excel_file.close()

            # Warn if no data found
            if not self._data:
                warnings.warn("No trade data found in Excel file")

            return self._data

        except Exception as e:
            raise ValueError(f"Error reading Excel file: {str(e)}")

    def get_sheet(self, sheet_name: str) -> Optional[pd.DataFrame]:
        """
        Get specific sheet data.

        Args:
            sheet_name: Name of sheet to retrieve

        Returns:
            DataFrame or None if sheet not found
        """
        return self._data.get(sheet_name)
    
    def get_all_trades(self) -> Dict[str, pd.DataFrame]:
        """Get all trade data."""
        return {k: self.get_sheet(k) for k in self._trade_types}
    
    def get_trades(self, trade_type: str) -> Optional[pd.DataFrame]:
        """Get trades of a specific type."""
        return self.get_sheet(trade_type)

    def get_netting_sets(self) -> Optional[pd.DataFrame]:
        """Get Netting Sets data."""
        return self.get_sheet(SHEET_NAMES["NETTING"])

    def get_warnings(self) -> List[str]:
        """
        Get list of warnings encountered during reading.

        Returns:
            List of warning messages
        """
        return self._warnings

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean dataframe by removing empty rows and stripping whitespace.

        Args:
            df: Input dataframe

        Returns:
            Cleaned dataframe
        """
        # Remove completely empty rows
        df = df.dropna(how='all')

        # Strip whitespace from string columns
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].astype(str).str.strip()

        # Replace 'nan' strings with actual NaN
        df = df.replace('nan', pd.NA)

        return df

    def _validate_columns(self, sheet_name: str, df: pd.DataFrame) -> List[str]:
        """
        Validate that required columns are present.

        Args:
            sheet_name: Name of the sheet being validated
            df: DataFrame to validate

        Returns:
            List of missing column names (empty if all present)
        """
        if sheet_name not in REQUIRED_COLUMNS:
            return []

        required = set(REQUIRED_COLUMNS[sheet_name])
        present = set(df.columns)
        missing = required - present

        return list(missing)

    def print_summary(self) -> None:
        """Print summary of loaded data."""
        print("\n" + "=" * 60)
        print("Excel Trade Data Summary")
        print("=" * 60)
        print(f"File: {self.excel_path}")
        print()

        if not self._data:
            print("No data loaded.")
        else:
            for sheet_name, df in self._data.items():
                print(f"{sheet_name:30s}: {len(df):4d} rows")

        if self._warnings:
            print("\nWarnings:")
            for warning in self._warnings:
                print(f"  • {warning}")

        print("=" * 60 + "\n")
