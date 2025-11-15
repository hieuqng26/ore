"""
Configuration constants for ORELab Excel-to-ORE converter.
"""

from pathlib import Path

# Base paths
ORELAB_ROOT = Path(__file__).parent.parent
INPUT_PATH = ORELAB_ROOT / "Input"
STATIC_PATH = INPUT_PATH / "Static"
OUTPUT_PATH = ORELAB_ROOT / "Output"

# Supported trade types
TRADE_TYPES = {
    "InterestRateSwaps": "Swap",
    "FXForwards": "FxForward",
    "FXOptions": "FxOption",
    "CrossCurrencySwaps": "Swap"  # CCS is also TradeType=Swap but with 2 currencies
}

# Excel sheet names
SHEET_NAMES = {
    "SWAPS": "InterestRateSwaps",
    "FX_FORWARDS": "FXForwards",
    "FX_OPTIONS": "FXOptions",
    "CCS": "CrossCurrencySwaps",
    "NETTING": "NettingSets"
}

# Required columns per trade type
REQUIRED_COLUMNS = {
    "InterestRateSwaps": [
        "TradeId", "CounterParty", "Currency", "Notional",
        "StartDate", "EndDate", "PayerOrReceiver",
        "FixedRate", "FixedTenor", "FixedDayCounter",
        "FloatingIndex", "FloatingTenor", "FloatingDayCounter"
    ],
    "FXForwards": [
        "TradeId", "CounterParty", "ValueDate",
        "BoughtCurrency", "BoughtAmount",
        "SoldCurrency", "SoldAmount"
    ],
    "FXOptions": [
        "TradeId", "CounterParty", "ExerciseDate",
        "LongShort", "OptionType", "Style",
        "BoughtCurrency", "BoughtAmount",
        "SoldCurrency", "SoldAmount"
    ],
    "CrossCurrencySwaps": [
        "TradeId", "CounterParty",
        "StartDate", "EndDate",
        "Currency1", "Notional1", "Index1", "Spread1",
        "Currency2", "Notional2", "Index2", "Spread2",
        "InitialExchange", "FinalExchange"
    ],
    "NettingSets": [
        "NettingSetId", "CounterParty"
    ]
}

# Default values
DEFAULTS = {
    "PaymentConvention": "MF",  # Modified Following
    "Calendar": "TARGET",
    "Convention": "MF",
    "TermConvention": "MF",
    "Rule": "Forward",
    "FixingDays": 2,
    "IsInArrears": False,
    "Settlement": "Cash",
    "PayOffAtExpiry": False,
    # Netting defaults
    "CSAThreshold": 0.0,
    "CSAMta": 0.0,
    "CollateralCurrency": "EUR",
    "MarginCallFrequency": "1D",
    "MarginPostFrequency": "1D"
}

# Date format
DATE_FORMAT = "%Y%m%d"
DATE_FORMAT_DISPLAY = "%Y-%m-%d"

# Temp folder prefix
TEMP_FOLDER_PREFIX = "temp_"

# Validation settings
VALIDATION_SETTINGS = {
    "skip_invalid_trades": True,
    "warn_on_skip": True,
    "strict_mode": False  # If True, raise exception on invalid trade
}
