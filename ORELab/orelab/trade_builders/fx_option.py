"""
FX Option trade builder.
"""

from lxml import etree
from .base import BaseTradeBuilder
from ..utils import format_date_for_ore
from ..config import DEFAULTS


class FxOptionBuilder(BaseTradeBuilder):
    """
    Build FX Option trade XML.

    Required fields:
    - TradeId
    - CounterParty
    - ExerciseDate
    - LongShort
    - OptionType (Call/Put)
    - Style (European/American)
    - BoughtCurrency
    - BoughtAmount
    - SoldCurrency
    - SoldAmount
    """

    def build(self) -> etree.Element:
        """
        Build FX Option trade XML element.

        Returns:
            XML Element for FX Option trade
        """
        # Create root Trade element
        trade = etree.Element("Trade", id=self._get_required("TradeId"))

        # TradeType
        etree.SubElement(trade, "TradeType").text = "FxOption"

        # Envelope
        self._create_envelope(trade)

        # FxOptionData
        fx_opt_data = etree.SubElement(trade, "FxOptionData")

        # OptionData section
        option_data = etree.SubElement(fx_opt_data, "OptionData")

        # LongShort
        long_short = self._get_required("LongShort")
        etree.SubElement(option_data, "LongShort").text = str(long_short)

        # OptionType
        option_type = self._get_required("OptionType")
        etree.SubElement(option_data, "OptionType").text = str(option_type)

        # Style
        style = self._get_optional("Style", "European")
        etree.SubElement(option_data, "Style").text = str(style)

        # Settlement
        settlement = self._get_optional("Settlement", DEFAULTS["Settlement"])
        etree.SubElement(option_data, "Settlement").text = str(settlement)

        # PayOffAtExpiry
        payoff = self._get_optional("PayOffAtExpiry", DEFAULTS["PayOffAtExpiry"])
        etree.SubElement(option_data, "PayOffAtExpiry").text = str(payoff).lower()

        # ExerciseDates
        exercise_dates = etree.SubElement(option_data, "ExerciseDates")
        exercise_date = self._get_required("ExerciseDate")
        exercise_date_formatted = format_date_for_ore(exercise_date)
        etree.SubElement(exercise_dates, "ExerciseDate").text = exercise_date_formatted

        # BoughtCurrency and BoughtAmount
        bought_ccy = self._get_required("BoughtCurrency")
        bought_amt = self._get_required("BoughtAmount")
        etree.SubElement(fx_opt_data, "BoughtCurrency").text = str(bought_ccy)
        etree.SubElement(fx_opt_data, "BoughtAmount").text = str(bought_amt)

        # SoldCurrency and SoldAmount
        sold_ccy = self._get_required("SoldCurrency")
        sold_amt = self._get_required("SoldAmount")
        etree.SubElement(fx_opt_data, "SoldCurrency").text = str(sold_ccy)
        etree.SubElement(fx_opt_data, "SoldAmount").text = str(sold_amt)

        return trade
