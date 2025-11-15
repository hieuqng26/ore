"""
Cross-Currency Swap trade builder.
"""

from lxml import etree
from .base import BaseTradeBuilder
from ..utils import format_date_for_ore
from ..config import DEFAULTS


class CrossCurrencySwapBuilder(BaseTradeBuilder):
    """
    Build Cross-Currency Swap trade XML.

    A CCS has two floating legs in different currencies with
    optional initial and final notional exchanges.

    Required fields:
    - TradeId
    - CounterParty
    - StartDate
    - EndDate
    - Currency1, Notional1, Index1, Spread1, Tenor1, DayCounter1
    - Currency2, Notional2, Index2, Spread2, Tenor2, DayCounter2
    - InitialExchange (True/False)
    - FinalExchange (True/False)

    Optional fields:
    - Calendar (default: TARGET)
    - PaymentConvention (default: MF)
    - FixingDays (default: 2)
    """

    def build(self) -> etree.Element:
        """
        Build Cross-Currency Swap trade XML element.

        Returns:
            XML Element for CCS trade
        """
        # Create root Trade element
        trade = etree.Element("Trade", id=self._get_required("TradeId"))

        # TradeType
        etree.SubElement(trade, "TradeType").text = "Swap"

        # Envelope
        self._create_envelope(trade)

        # SwapData
        swap_data = etree.SubElement(trade, "SwapData")

        # Get common parameters
        start_date = format_date_for_ore(self._get_required("StartDate"))
        end_date = format_date_for_ore(self._get_required("EndDate"))
        calendar = self._get_optional("Calendar", DEFAULTS["Calendar"])
        payment_conv = self._get_optional("PaymentConvention", DEFAULTS["PaymentConvention"])

        # Get exchange flags
        initial_exchange = self._get_optional("InitialExchange", True)
        final_exchange = self._get_optional("FinalExchange", True)

        # Create Leg 1
        self._create_floating_leg(
            swap_data,
            leg_num=1,
            payer=False,  # Receive leg 1
            start_date=start_date,
            end_date=end_date,
            calendar=calendar,
            payment_conv=payment_conv,
            initial_exchange=initial_exchange,
            final_exchange=final_exchange
        )

        # Create Leg 2
        self._create_floating_leg(
            swap_data,
            leg_num=2,
            payer=True,  # Pay leg 2
            start_date=start_date,
            end_date=end_date,
            calendar=calendar,
            payment_conv=payment_conv,
            initial_exchange=initial_exchange,
            final_exchange=final_exchange
        )

        return trade

    def _create_floating_leg(
        self,
        swap_data: etree.Element,
        leg_num: int,
        payer: bool,
        start_date: str,
        end_date: str,
        calendar: str,
        payment_conv: str,
        initial_exchange: bool,
        final_exchange: bool
    ) -> None:
        """Create floating leg for CCS."""
        leg = etree.SubElement(swap_data, "LegData")

        # Leg type
        etree.SubElement(leg, "LegType").text = "Floating"

        # Payer flag
        etree.SubElement(leg, "Payer").text = str(payer).lower()

        # Currency
        currency = self._get_required(f"Currency{leg_num}")
        etree.SubElement(leg, "Currency").text = currency

        # Notionals with exchanges
        notionals = etree.SubElement(leg, "Notionals")
        notional = self._get_required(f"Notional{leg_num}")
        etree.SubElement(notionals, "Notional").text = str(notional)

        # Exchanges
        exchanges = etree.SubElement(notionals, "Exchanges")
        etree.SubElement(exchanges, "NotionalInitialExchange").text = str(initial_exchange).lower()
        etree.SubElement(exchanges, "NotionalFinalExchange").text = str(final_exchange).lower()

        # DayCounter
        day_counter = self._get_required(f"DayCounter{leg_num}")
        etree.SubElement(leg, "DayCounter").text = day_counter

        # PaymentConvention
        etree.SubElement(leg, "PaymentConvention").text = payment_conv

        # FloatingLegData
        floating_data = etree.SubElement(leg, "FloatingLegData")

        # Index
        index = self._get_required(f"Index{leg_num}")
        etree.SubElement(floating_data, "Index").text = index

        # Spreads
        spreads = etree.SubElement(floating_data, "Spreads")
        spread = self._get_required(f"Spread{leg_num}")
        etree.SubElement(spreads, "Spread").text = str(spread)

        # IsInArrears
        is_in_arrears = self._get_optional("IsInArrears", DEFAULTS["IsInArrears"])
        etree.SubElement(floating_data, "IsInArrears").text = str(is_in_arrears).lower()

        # FixingDays
        fixing_days = self._get_optional("FixingDays", DEFAULTS["FixingDays"])
        etree.SubElement(floating_data, "FixingDays").text = str(fixing_days)

        # ScheduleData
        tenor = self._get_required(f"Tenor{leg_num}")
        self._create_schedule(
            leg,
            start_date,
            end_date,
            tenor,
            calendar,
            payment_conv
        )

    def _create_schedule(
        self,
        leg: etree.Element,
        start_date: str,
        end_date: str,
        tenor: str,
        calendar: str,
        convention: str
    ) -> None:
        """Create schedule data for leg."""
        schedule_data = etree.SubElement(leg, "ScheduleData")
        rules = etree.SubElement(schedule_data, "Rules")

        etree.SubElement(rules, "StartDate").text = start_date
        etree.SubElement(rules, "EndDate").text = end_date
        etree.SubElement(rules, "Tenor").text = tenor
        etree.SubElement(rules, "Calendar").text = calendar
        etree.SubElement(rules, "Convention").text = convention
        etree.SubElement(rules, "TermConvention").text = convention
        etree.SubElement(rules, "Rule").text = DEFAULTS["Rule"]
