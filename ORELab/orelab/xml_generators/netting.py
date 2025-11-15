"""
Netting XML generator.
"""

from lxml import etree
from pathlib import Path
from typing import Optional
import pandas as pd

from ..config import DEFAULTS


class NettingGenerator:
    """
    Generate netting.xml from netting set data.

    Creates CSA (Credit Support Annex) configuration for counterparties.
    """

    def generate(self, netting_df: pd.DataFrame) -> etree.Element:
        """
        Generate netting XML from DataFrame.

        Args:
            netting_df: DataFrame with netting set data

        Returns:
            NettingSetDefinitions XML element
        """
        # Create root element
        netting_sets = etree.Element("NettingSetDefinitions")

        for idx, row in netting_df.iterrows():
            netting_data = row.to_dict()
            netting_set = self._create_netting_set(netting_data)
            netting_sets.append(netting_set)

        return netting_sets

    def _create_netting_set(self, netting_data: dict) -> etree.Element:
        """
        Create a single netting set definition.

        Args:
            netting_data: Dictionary with netting set parameters

        Returns:
            NettingSetDefinition XML element
        """
        # Get netting set ID
        netting_id = netting_data.get("NettingSetId", "")
        if not netting_id:
            raise ValueError("NettingSetId is required")

        # Create NettingSetDefinition
        netting_set = etree.Element("NettingSetDefinition", id=netting_id)

        # CounterpartyId
        counterparty = netting_data.get("CounterParty", netting_id)
        etree.SubElement(netting_set, "CounterpartyId").text = counterparty

        # ActiveCSAFlag
        etree.SubElement(netting_set, "ActiveCSAFlag").text = "true"

        # CSADetails
        csa_details = etree.SubElement(netting_set, "CSADetails")

        # Collateral Currency
        coll_ccy = netting_data.get("CollateralCurrency", DEFAULTS["CollateralCurrency"])
        etree.SubElement(csa_details, "CollateralCurrency").text = coll_ccy

        # Thresholds
        threshold = netting_data.get("CSAThreshold", DEFAULTS["CSAThreshold"])
        etree.SubElement(csa_details, "Threshold").text = str(threshold)

        # Minimum Transfer Amount (MTA)
        mta = netting_data.get("CSAMta", DEFAULTS["CSAMta"])
        etree.SubElement(csa_details, "MinimumTransferAmount").text = str(mta)

        # Independent Amount
        independent_amt = netting_data.get("IndependentAmount", 0)
        etree.SubElement(csa_details, "IndependentAmount").text = str(independent_amt)

        # Margin Call Frequency
        margin_call_freq = netting_data.get("MarginCallFrequency", DEFAULTS["MarginCallFrequency"])
        etree.SubElement(csa_details, "MarginCallFrequency").text = margin_call_freq

        # Margin Post Frequency
        margin_post_freq = netting_data.get("MarginPostFrequency", DEFAULTS["MarginPostFrequency"])
        etree.SubElement(csa_details, "MarginPostFrequency").text = margin_post_freq

        # Margin Period of Risk (days)
        mpr = netting_data.get("MarginPeriodOfRisk", 14)
        etree.SubElement(csa_details, "MarginPeriodOfRisk").text = str(mpr)

        return netting_set

    def save_to_file(self, netting_sets: etree.Element, output_path: Path) -> None:
        """
        Save netting XML to file.

        Args:
            netting_sets: NettingSetDefinitions XML element
            output_path: Path to output file
        """
        tree = etree.ElementTree(netting_sets)
        tree.write(
            str(output_path),
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        )
