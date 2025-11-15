"""
Base trade builder class.
"""

from abc import ABC, abstractmethod
from lxml import etree
from typing import Dict, Any


class BaseTradeBuilder(ABC):
    """
    Abstract base class for trade builders.

    Each trade builder converts a dictionary of trade data
    into an XML element representing the trade in ORE format.
    """

    def __init__(self, trade_data: Dict[str, Any]):
        """
        Initialize trade builder.

        Args:
            trade_data: Dictionary containing trade parameters
        """
        self.trade_data = trade_data

    @abstractmethod
    def build(self) -> etree.Element:
        """
        Build trade XML element.

        Returns:
            XML Element representing the trade

        Raises:
            ValueError: If trade data is invalid
        """
        pass

    def _create_envelope(self, parent: etree.Element) -> etree.Element:
        """
        Create Envelope element common to all trades.

        Args:
            parent: Parent XML element

        Returns:
            Created Envelope element
        """
        envelope = etree.SubElement(parent, "Envelope")

        # CounterParty
        counterparty = self.trade_data.get("CounterParty", "")
        etree.SubElement(envelope, "CounterParty").text = counterparty

        # NettingSetId - use CounterParty as default
        netting_set = self.trade_data.get("NettingSetId", counterparty)
        etree.SubElement(envelope, "NettingSetId").text = netting_set

        return envelope

    def _get_required(self, key: str, field_name: str = None) -> Any:
        """
        Get required field from trade data.

        Args:
            key: Dictionary key
            field_name: Human-readable field name for error messages

        Returns:
            Field value

        Raises:
            ValueError: If field is missing or empty
        """
        value = self.trade_data.get(key)
        if value is None or value == "" or str(value).strip() == "":
            field_name = field_name or key
            trade_id = self.trade_data.get("TradeId", "Unknown")
            raise ValueError(f"Trade {trade_id}: Missing required field '{field_name}'")
        return value

    def _get_optional(self, key: str, default: Any = None) -> Any:
        """
        Get optional field from trade data with default.

        Args:
            key: Dictionary key
            default: Default value if field is missing

        Returns:
            Field value or default
        """
        value = self.trade_data.get(key, default)
        if value is None or value == "" or str(value).strip() == "":
            return default
        return value

    def _create_text_element(
        self,
        parent: etree.Element,
        tag: str,
        text: Any
    ) -> etree.Element:
        """
        Create XML element with text content.

        Args:
            parent: Parent XML element
            tag: Element tag name
            text: Text content

        Returns:
            Created element
        """
        elem = etree.SubElement(parent, tag)
        elem.text = str(text)
        return elem

    def to_xml_string(self, pretty_print: bool = True) -> str:
        """
        Build trade and return as XML string.

        Args:
            pretty_print: Whether to format XML with indentation

        Returns:
            XML string
        """
        trade_elem = self.build()
        return etree.tostring(
            trade_elem,
            encoding='unicode',
            pretty_print=pretty_print
        )
