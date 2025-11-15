"""
Utility functions for ORELab Excel-to-ORE converter.
"""

from datetime import datetime
from pathlib import Path
from typing import Union
import shutil

from .config import TEMP_FOLDER_PREFIX, DATE_FORMAT, DATE_FORMAT_DISPLAY


def generate_timestamp() -> str:
    """
    Generate timestamp string for temp folder names.

    Returns:
        Timestamp string in format YYYYMMDD_HHMMSS
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def create_temp_folder(base_path: Union[str, Path]) -> Path:
    """
    Create a temporary folder with timestamp.

    Args:
        base_path: Base directory where temp folder will be created

    Returns:
        Path to created temp folder
    """
    base_path = Path(base_path)
    timestamp = generate_timestamp()
    temp_path = base_path / f"{TEMP_FOLDER_PREFIX}{timestamp}"
    temp_path.mkdir(parents=True, exist_ok=True)
    return temp_path


def cleanup_temp_folder(temp_path: Union[str, Path]) -> None:
    """
    Remove temporary folder and all its contents.

    Args:
        temp_path: Path to temp folder to remove
    """
    temp_path = Path(temp_path)
    if temp_path.exists() and TEMP_FOLDER_PREFIX in temp_path.name:
        shutil.rmtree(temp_path)


def format_date_for_ore(date_value: Union[str, datetime]) -> str:
    """
    Format date for ORE XML (YYYYMMDD format).

    Args:
        date_value: Date as string or datetime object

    Returns:
        Date string in YYYYMMDD format

    Raises:
        ValueError: If date format is invalid
    """
    if isinstance(date_value, datetime):
        return date_value.strftime(DATE_FORMAT)

    # If already string, validate and return
    date_str = str(date_value).strip()

    # Try parsing common formats
    for fmt in [DATE_FORMAT, DATE_FORMAT_DISPLAY, "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"]:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime(DATE_FORMAT)
        except ValueError:
            continue

    # If no format worked, raise error
    raise ValueError(f"Invalid date format: {date_value}. Expected YYYYMMDD or YYYY-MM-DD")


def safe_float(value, default=0.0) -> float:
    """
    Safely convert value to float with default fallback.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Float value or default
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_int(value, default=0) -> int:
    """
    Safely convert value to int with default fallback.

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Int value or default
    """
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_str(value, default="") -> str:
    """
    Safely convert value to string with default fallback.

    Args:
        value: Value to convert
        default: Default value if value is None/NaN

    Returns:
        String value or default
    """
    if value is None or (isinstance(value, float) and str(value) == 'nan'):
        return default
    return str(value).strip()


def validate_currency(currency: str) -> bool:
    """
    Validate currency code (basic 3-letter check).

    Args:
        currency: Currency code to validate

    Returns:
        True if valid, False otherwise
    """
    return isinstance(currency, str) and len(currency) == 3 and currency.isalpha()


def get_relative_path(from_path: Union[str, Path], to_path: Union[str, Path]) -> str:
    """
    Get relative path from one location to another.

    Args:
        from_path: Starting path
        to_path: Target path

    Returns:
        Relative path as string
    """
    from_path = Path(from_path)
    to_path = Path(to_path)

    try:
        rel_path = to_path.relative_to(from_path)
        return str(rel_path)
    except ValueError:
        # If not relative, try to find common parent
        try:
            rel_path = Path(".").joinpath(to_path.relative_to(from_path.parent))
            return str(rel_path)
        except ValueError:
            # Fall back to absolute path
            return str(to_path.absolute())
