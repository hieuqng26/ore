"""
FX Forward trade builder.
"""

from lxml import etree
from .base import BaseTradeBuilder
from ..utils import format_date_for_ore


class FxForwardBuilder(BaseTradeBuilder):
    """
    Build FX Forward trade XML.

    Required fields:
    - TradeId
    - CounterParty
    - ValueDate
    - BoughtCurrency
    - BoughtAmount
    - SoldCurrency
    - SoldAmount
    """

    def build(self) -> etree.Element:
        """
        Build FX Forward trade XML element.

        Returns:
            XML Element for FX Forward trade
        """
        # Create root Trade element
        trade = etree.Element("Trade", id=self._get_required("TradeId"))

        # TradeType
        etree.SubElement(trade, "TradeType").text = "FxForward"

        # Envelope
        self._create_envelope(trade)

        # FxForwardData
        fx_data = etree.SubElement(trade, "FxForwardData")

        # ValueDate
        value_date = self._get_required("ValueDate")
        value_date_formatted = format_date_for_ore(value_date)
        etree.SubElement(fx_data, "ValueDate").text = value_date_formatted

        # BoughtCurrency and BoughtAmount
        bought_ccy = self._get_required("BoughtCurrency")
        bought_amt = self._get_required("BoughtAmount")
        etree.SubElement(fx_data, "BoughtCurrency").text = str(bought_ccy)
        etree.SubElement(fx_data, "BoughtAmount").text = str(bought_amt)

        # SoldCurrency and SoldAmount
        sold_ccy = self._get_required("SoldCurrency")
        sold_amt = self._get_required("SoldAmount")
        etree.SubElement(fx_data, "SoldCurrency").text = str(sold_ccy)
        etree.SubElement(fx_data, "SoldAmount").text = str(sold_amt)

        return trade
