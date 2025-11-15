"""
Validators for trade data.
"""

from typing import Dict, List, Tuple, Any
from datetime import datetime

from .config import REQUIRED_COLUMNS, DATE_FORMAT, DATE_FORMAT_DISPLAY
from .utils import validate_currency


class ValidationResult:
    """Result of validation check."""

    def __init__(self, is_valid: bool = True, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def add_error(self, error: str):
        """Add error message."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        """Add warning message."""
        self.warnings.append(warning)

    def __bool__(self):
        """Return validation status."""
        return self.is_valid


class TradeValidator:
    """
    Validate trade data before XML generation.

    Performs moderate validation:
    - Required fields present
    - Date formats valid
    - Currency codes valid (3 letters)
    - Numeric fields are numeric
    - Basic business logic (positive notionals, valid rates)
    """

    @staticmethod
    def validate_trade(trade_data: Dict[str, Any], trade_type: str) -> ValidationResult:
        """
        Validate a single trade.

        Args:
            trade_data: Dictionary of trade parameters
            trade_type: Type of trade (sheet name)

        Returns:
            ValidationResult with errors/warnings
        """
        result = ValidationResult()
        trade_id = trade_data.get("TradeId", "Unknown")

        # Check required columns
        if trade_type in REQUIRED_COLUMNS:
            for col in REQUIRED_COLUMNS[trade_type]:
                if col not in trade_data or trade_data[col] is None or str(trade_data[col]).strip() == "":
                    result.add_error(f"Missing required field: {col}")

        # If basic validation failed, don't continue
        if not result.is_valid:
            return result

        # Type-specific validation
        validator_map = {
            "InterestRateSwap": TradeValidator._validate_swap,
            "FxForward": TradeValidator._validate_fx_forward,
            "FxOption": TradeValidator._validate_fx_option,
            "CrossCurrencySwap": TradeValidator._validate_ccs,
            "NettingSets": TradeValidator._validate_netting,
        }

        if trade_type in validator_map:
            validator_map[trade_type](trade_data, result)

        return result

    @staticmethod
    def _validate_swap(trade_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate Interest Rate Swap."""
        # Validate currency
        currency = trade_data.get("Currency", "")
        if not validate_currency(currency):
            result.add_error(f"Invalid currency code: {currency}")

        # Validate notional is positive
        try:
            notional = float(trade_data.get("Notional", 0))
            if notional <= 0:
                result.add_error(f"Notional must be positive: {notional}")
        except (ValueError, TypeError):
            result.add_error(f"Invalid notional: {trade_data.get('Notional')}")

        # Validate dates
        TradeValidator._validate_date(trade_data.get("StartDate"), "StartDate", result)
        TradeValidator._validate_date(trade_data.get("EndDate"), "EndDate", result)

        # Validate fixed rate
        try:
            fixed_rate = float(trade_data.get("FixedRate", 0))
            if fixed_rate < -1 or fixed_rate > 1:
                result.add_warning(f"Unusual fixed rate: {fixed_rate} (expected range: -1 to 1)")
        except (ValueError, TypeError):
            result.add_error(f"Invalid fixed rate: {trade_data.get('FixedRate')}")

        # Validate payer/receiver
        payer_receiver = str(trade_data.get("PayerOrReceiver", "")).lower()
        if payer_receiver not in ["payer", "receiver", "pay", "receive"]:
            result.add_error(f"Invalid PayerOrReceiver: {trade_data.get('PayerOrReceiver')} (expected Payer or Receiver)")

        # Validate tenors
        TradeValidator._validate_tenor(trade_data.get("FixedTenor"), "FixedTenor", result)
        TradeValidator._validate_tenor(trade_data.get("FloatingTenor"), "FloatingTenor", result)

    @staticmethod
    def _validate_fx_forward(trade_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate FX Forward."""
        # Validate currencies
        bought_ccy = trade_data.get("BoughtCurrency", "")
        sold_ccy = trade_data.get("SoldCurrency", "")

        if not validate_currency(bought_ccy):
            result.add_error(f"Invalid bought currency: {bought_ccy}")
        if not validate_currency(sold_ccy):
            result.add_error(f"Invalid sold currency: {sold_ccy}")

        if bought_ccy == sold_ccy:
            result.add_error(f"Bought and sold currencies must be different")

        # Validate amounts
        try:
            bought_amt = float(trade_data.get("BoughtAmount", 0))
            if bought_amt <= 0:
                result.add_error(f"BoughtAmount must be positive: {bought_amt}")
        except (ValueError, TypeError):
            result.add_error(f"Invalid BoughtAmount: {trade_data.get('BoughtAmount')}")

        try:
            sold_amt = float(trade_data.get("SoldAmount", 0))
            if sold_amt <= 0:
                result.add_error(f"SoldAmount must be positive: {sold_amt}")
        except (ValueError, TypeError):
            result.add_error(f"Invalid SoldAmount: {trade_data.get('SoldAmount')}")

        # Validate value date
        TradeValidator._validate_date(trade_data.get("ValueDate"), "ValueDate", result)

    @staticmethod
    def _validate_fx_option(trade_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate FX Option."""
        # Similar to FX Forward for currencies and amounts
        TradeValidator._validate_fx_forward(trade_data, result)

        # Additional validation for option parameters
        long_short = str(trade_data.get("LongShort", "")).lower()
        if long_short not in ["long", "short"]:
            result.add_error(f"Invalid LongShort: {trade_data.get('LongShort')} (expected Long or Short)")

        option_type = str(trade_data.get("OptionType", "")).lower()
        if option_type not in ["call", "put"]:
            result.add_error(f"Invalid OptionType: {trade_data.get('OptionType')} (expected Call or Put)")

        style = str(trade_data.get("Style", "european")).lower()
        if style not in ["european", "american", "bermudan"]:
            result.add_warning(f"Unusual option style: {trade_data.get('Style')}")

        # Validate exercise date
        TradeValidator._validate_date(trade_data.get("ExerciseDate"), "ExerciseDate", result)

    @staticmethod
    def _validate_ccs(trade_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate Cross-Currency Swap."""
        # Validate currencies
        ccy1 = trade_data.get("Currency1", "")
        ccy2 = trade_data.get("Currency2", "")

        if not validate_currency(ccy1):
            result.add_error(f"Invalid Currency1: {ccy1}")
        if not validate_currency(ccy2):
            result.add_error(f"Invalid Currency2: {ccy2}")

        if ccy1 == ccy2:
            result.add_error(f"Currency1 and Currency2 must be different for cross-currency swap")

        # Validate notionals
        for leg in [1, 2]:
            try:
                notional = float(trade_data.get(f"Notional{leg}", 0))
                if notional <= 0:
                    result.add_error(f"Notional{leg} must be positive: {notional}")
            except (ValueError, TypeError):
                result.add_error(f"Invalid Notional{leg}: {trade_data.get(f'Notional{leg}')}")

            # Validate spreads
            try:
                spread = float(trade_data.get(f"Spread{leg}", 0))
                if spread < -1 or spread > 1:
                    result.add_warning(f"Unusual Spread{leg}: {spread}")
            except (ValueError, TypeError):
                result.add_error(f"Invalid Spread{leg}: {trade_data.get(f'Spread{leg}')}")

        # Validate dates
        TradeValidator._validate_date(trade_data.get("StartDate"), "StartDate", result)
        TradeValidator._validate_date(trade_data.get("EndDate"), "EndDate", result)

        # Validate tenors
        TradeValidator._validate_tenor(trade_data.get("Tenor1"), "Tenor1", result)
        TradeValidator._validate_tenor(trade_data.get("Tenor2"), "Tenor2", result)

    @staticmethod
    def _validate_netting(trade_data: Dict[str, Any], result: ValidationResult) -> None:
        """Validate Netting Set."""
        # Validate CSA threshold and MTA
        try:
            threshold = float(trade_data.get("CSAThreshold", 0))
            if threshold < 0:
                result.add_warning(f"CSA threshold is negative: {threshold}")
        except (ValueError, TypeError):
            # Optional field, just warn
            result.add_warning(f"Invalid CSA threshold: {trade_data.get('CSAThreshold')}")

        try:
            mta = float(trade_data.get("CSAMta", 0))
            if mta < 0:
                result.add_warning(f"CSA MTA is negative: {mta}")
        except (ValueError, TypeError):
            result.add_warning(f"Invalid CSA MTA: {trade_data.get('CSAMta')}")

        # Validate collateral currency if present
        coll_ccy = trade_data.get("CollateralCurrency")
        if coll_ccy and not validate_currency(coll_ccy):
            result.add_error(f"Invalid collateral currency: {coll_ccy}")

    @staticmethod
    def _validate_date(date_value: Any, field_name: str, result: ValidationResult) -> None:
        """Validate date format."""
        if not date_value:
            return

        date_str = str(date_value).strip()

        # Try parsing common formats
        valid = False
        for fmt in [DATE_FORMAT, DATE_FORMAT_DISPLAY, "%Y/%m/%d", "%d/%m/%Y", "%m/%d/%Y"]:
            try:
                datetime.strptime(date_str, fmt)
                valid = True
                break
            except ValueError:
                continue

        if not valid:
            result.add_error(f"Invalid date format for {field_name}: {date_value} (expected YYYYMMDD or YYYY-MM-DD)")

    @staticmethod
    def _validate_tenor(tenor: Any, field_name: str, result: ValidationResult) -> None:
        """Validate tenor format (e.g., 1Y, 6M, 3M)."""
        if not tenor:
            return

        tenor_str = str(tenor).strip().upper()

        # Basic tenor validation: should end with D, W, M, or Y
        if not tenor_str or tenor_str[-1] not in ["D", "W", "M", "Y"]:
            result.add_error(f"Invalid tenor format for {field_name}: {tenor} (expected format like 1Y, 6M, 3M)")
            return

        # Check number part
        try:
            int(tenor_str[:-1])
        except ValueError:
            result.add_error(f"Invalid tenor format for {field_name}: {tenor} (expected format like 1Y, 6M, 3M)")
