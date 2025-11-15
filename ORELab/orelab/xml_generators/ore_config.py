"""
ORE configuration XML generator.

Generates ore.xml with updated paths for temporary folders.
"""

from lxml import etree
from pathlib import Path
from typing import Optional, Dict


class OREConfigGenerator:
    """
    Generate ore.xml configuration file.

    Uses existing ore.xml as template and updates paths
    for portfolio and netting files in temporary folder.
    """

    def __init__(self, template_path: Optional[Path] = None):
        """
        Initialize ORE config generator.

        Args:
            template_path: Path to template ore.xml file.
                          If None, creates minimal configuration.
        """
        self.template_path = template_path
        self._config_tree = None

    def load_template(self) -> None:
        """Load template ore.xml file."""
        if self.template_path and self.template_path.exists():
            parser = etree.XMLParser(remove_blank_text=True)
            self._config_tree = etree.parse(str(self.template_path), parser)
        else:
            # Create minimal config if no template
            self._config_tree = self._create_minimal_config()

    def update_paths(
        self,
        asof_date: str,
        input_path: str,
        output_path: str,
        portfolio_file: Optional[str] = None,
        netting_file: Optional[str] = None,
        static_path_prefix: str = ""
    ) -> None:
        """
        Update paths in configuration.

        Args:
            asof_date: asofDate in YYYY-MM-DD format
            input_path: Base input path (relative or absolute)
            output_path: Output path for results
            portfolio_file: Portfolio XML filename (relative to input_path)
            netting_file: Netting XML filename (relative to input_path)
            static_path_prefix: Prefix for Static file paths (e.g., "../Static/")
        """
        if self._config_tree is None:
            self.load_template()

        root = self._config_tree.getroot()

        # Update Setup parameters
        setup = root.find("Setup")
        if setup is not None:
            self._update_parameter(setup, "asofDate", asof_date)
            self._update_parameter(setup, "inputPath", input_path)
            self._update_parameter(setup, "outputPath", output_path)

            if portfolio_file:
                self._update_parameter(setup, "portfolioFile", portfolio_file)

            # Update Static file paths if prefix provided
            if static_path_prefix:
                static_files = [
                    "marketDataFile",
                    "fixingDataFile",
                    "curveConfigFile",
                    "conventionsFile",
                    "marketConfigFile",
                    "pricingEnginesFile",
                    "calendarAdjustment",
                    "currencyConfiguration"
                ]

                for param_name in static_files:
                    param = setup.find(f"Parameter[@name='{param_name}']")
                    if param is not None and param.text:
                        # Only update if it starts with "Static/"
                        if param.text.startswith("Static/"):
                            filename = param.text[len("Static/"):]
                            param.text = f"{static_path_prefix}{filename}"

        # Update netting file in XVA analytic if it exists
        if netting_file:
            analytics = root.find("Analytics")
            if analytics is not None:
                for analytic in analytics.findall("Analytic"):
                    if analytic.get("type") == "xva":
                        self._update_parameter(analytic, "csaFile", netting_file)

        # Update Static file paths in Analytics section (e.g., simulation analytic)
        if static_path_prefix:
            analytics = root.find("Analytics")
            if analytics is not None:
                for analytic in analytics.findall("Analytic"):
                    # Handle simulation analytic parameters
                    if analytic.get("type") == "simulation":
                        for param_name in ["simulationConfigFile", "pricingEnginesFile"]:
                            param = analytic.find(f"Parameter[@name='{param_name}']")
                            if param is not None and param.text:
                                # Only update if it starts with "Static/"
                                if param.text.startswith("Static/"):
                                    filename = param.text[len("Static/"):]
                                    param.text = f"{static_path_prefix}{filename}"

    def set_base_currency(self, currency: str) -> None:
        """
        Set base currency for analytics.

        Args:
            currency: Base currency code (e.g., EUR, USD)
        """
        if self._config_tree is None:
            self.load_template()

        root = self._config_tree.getroot()
        analytics = root.find("Analytics")
        if analytics is not None:
            for analytic in analytics.findall("Analytic"):
                # Update base currency for relevant analytics
                if analytic.get("type") in ["npv", "simulation", "xva"]:
                    self._update_parameter(analytic, "baseCurrency", currency)

    def enable_analytics(self, analytics_list: list) -> None:
        """
        Enable specific analytics.

        Args:
            analytics_list: List of analytic types to enable
                          (e.g., ['npv', 'cashflow', 'xva'])
        """
        if self._config_tree is None:
            self.load_template()

        root = self._config_tree.getroot()
        analytics = root.find("Analytics")
        if analytics is not None:
            for analytic in analytics.findall("Analytic"):
                analytic_type = analytic.get("type")
                active_value = "Y" if analytic_type in analytics_list else "N"
                self._update_parameter(analytic, "active", active_value)

    def save_to_file(self, output_path: Path) -> None:
        """
        Save configuration to file.

        Args:
            output_path: Path to output file
        """
        if self._config_tree is None:
            self.load_template()

        self._config_tree.write(
            str(output_path),
            encoding='utf-8',
            xml_declaration=True,
            pretty_print=True
        )

    def _update_parameter(self, parent: etree.Element, param_name: str, value: str) -> None:
        """
        Update or create parameter element.

        Args:
            parent: Parent XML element
            param_name: Parameter name
            value: Parameter value
        """
        # Find existing parameter
        param = parent.find(f"Parameter[@name='{param_name}']")

        if param is not None:
            # Update existing
            param.text = value
        else:
            # Create new
            param = etree.SubElement(parent, "Parameter", name=param_name)
            param.text = value

    def _create_minimal_config(self) -> etree.ElementTree:
        """
        Create minimal ORE configuration.

        Returns:
            Minimal ORE configuration tree
        """
        ore = etree.Element("ORE")

        # Setup section
        setup = etree.SubElement(ore, "Setup")
        params = {
            "asofDate": "2016-02-05",
            "inputPath": "Input",
            "outputPath": "Output",
            "logFile": "log.txt",
            "logMask": "31",
            "marketDataFile": "Static/market_20160205.txt",
            "fixingDataFile": "Static/fixings_20160205.txt",
            "implyTodaysFixings": "Y",
            "curveConfigFile": "Static/curveconfig.xml",
            "conventionsFile": "Static/conventions.xml",
            "marketConfigFile": "Static/todaysmarket.xml",
            "pricingEnginesFile": "Static/pricingengine.xml",
            "portfolioFile": "portfolio.xml",
            "observationModel": "None",
            "continueOnError": "false",
            "calendarAdjustment": "Static/calendaradjustment.xml",
            "currencyConfiguration": "Static/currencies.xml"
        }

        for name, value in params.items():
            etree.SubElement(setup, "Parameter", name=name).text = value

        # Markets section
        markets = etree.SubElement(ore, "Markets")
        market_params = {
            "lgmcalibration": "collateral_inccy",
            "fxcalibration": "xois_eur",
            "pricing": "xois_eur",
            "simulation": "xois_eur"
        }

        for name, value in market_params.items():
            etree.SubElement(markets, "Parameter", name=name).text = value

        # Analytics section
        analytics = etree.SubElement(ore, "Analytics")

        # NPV analytic
        npv = etree.SubElement(analytics, "Analytic", type="npv")
        etree.SubElement(npv, "Parameter", name="active").text = "Y"
        etree.SubElement(npv, "Parameter", name="baseCurrency").text = "EUR"
        etree.SubElement(npv, "Parameter", name="outputFileName").text = "npv.csv"

        # Cashflow analytic
        cashflow = etree.SubElement(analytics, "Analytic", type="cashflow")
        etree.SubElement(cashflow, "Parameter", name="active").text = "Y"
        etree.SubElement(cashflow, "Parameter", name="outputFileName").text = "flows.csv"

        return etree.ElementTree(ore)
