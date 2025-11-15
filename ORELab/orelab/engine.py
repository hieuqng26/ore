"""
Main Excel-to-ORE conversion engine.
"""

import os
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import warnings
import pandas as pd
from datetime import datetime
import ORE

from .excel_reader import ExcelTradeReader
from .xml_generators import PortfolioGenerator, NettingGenerator, OREConfigGenerator
from .config import INPUT_PATH, STATIC_PATH, OUTPUT_PATH, DATE_FORMAT_DISPLAY
from .utils import create_temp_folder, cleanup_temp_folder, format_date_for_ore


class OREXlsxConverter:
    """
    Excel to ORE converter with context manager interface.

    Usage:
        with OREXlsxConverter('trades.xlsx', cleanup=True) as converter:
            ore_config_path = converter.ore_config_path
            # Run ORE with the generated configuration
            # Temp folder will be cleaned up automatically on exit

        # Override asofDate in ore.xml
        with OREXlsxConverter('trades.xlsx', asof_date='2024-03-15') as converter:
            ore_config_path = converter.ore_config_path

    The converter:
    1. Reads Excel file with trade data
    2. Validates trades
    3. Generates portfolio.xml and netting.xml
    4. Creates ore.xml with updated paths
    5. Optionally overrides asofDate parameter
    6. Returns path to temporary folder with all configs
    """

    def __init__(
        self,
        excel_path: str,
        asof_date: str,
        template_ore_xml: Optional[str] = None,
        cleanup: bool = True,
        skip_invalid: bool = True,
        warn_on_skip: bool = True
    ):
        """
        Initialize OREXlsxConverter.

        Args:
            excel_path: Path to Excel file with trade data
            asof_date: As-of date to override in ore.xml (YYYY-MM-DD or YYYYMMDD format)
            template_ore_xml: Path to template ore.xml (default: Input/ore.xml)
            cleanup: Whether to cleanup temp folder on exit
            skip_invalid: Whether to skip invalid trades
            warn_on_skip: Whether to print warnings for skipped trades

        Raises:
            FileNotFoundError: If Excel file doesn't exist
            ValueError: If asof_date format is invalid
        """
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        # Set template path
        if template_ore_xml:
            self.template_ore_xml = Path(template_ore_xml)
        else:
            self.template_ore_xml = INPUT_PATH / "ore.xml"

        # Validate and store asof_date
        if asof_date:
            # Validate and convert to YYYY-MM-DD format for ore.xml
            try:
                # format_date_for_ore returns YYYYMMDD, we need to convert to YYYY-MM-DD
                validated_date = format_date_for_ore(asof_date)
                dt = datetime.strptime(validated_date, "%Y%m%d")
                self.asof_date = dt.strftime(DATE_FORMAT_DISPLAY)
            except ValueError as e:
                raise ValueError(f"Invalid asof_date format: {asof_date}. {str(e)}")
        else:
            self.asof_date = None

        self.cleanup = cleanup
        self.skip_invalid = skip_invalid
        self.warn_on_skip = warn_on_skip

        # Will be set during conversion
        self.temp_folder: Optional[Path] = None
        self.ore_config_path: Optional[Path] = None
        self.portfolio_path: Optional[Path] = None
        self.netting_path: Optional[Path] = None

        # Components
        self.reader: Optional[ExcelTradeReader] = None
        self.portfolio_generator: Optional[PortfolioGenerator] = None
        self.netting_generator: Optional[NettingGenerator] = None

    def __enter__(self):
        """
        Enter context manager - perform conversion.

        Returns:
            Self with temp_folder and ore_config_path set
        """
        self.convert()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context manager - cleanup if requested.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        if self.cleanup and self.temp_folder:
            cleanup_temp_folder(self.temp_folder)
            print(f"✓ Cleaned up temporary folder: {self.temp_folder}")

    def convert(self) -> Path:
        """
        Perform full conversion from Excel to ORE XML files.

        Returns:
            Path to generated ore.xml configuration file

        Raises:
            ValueError: If conversion fails
        """
        print("\n" + "=" * 60)
        print("Excel to ORE Conversion")
        print("=" * 60)
        print(f"Excel file: {self.excel_path}")
        print()

        # Step 1: Read Excel file
        print("Step 1: Reading Excel file...")
        self.reader = ExcelTradeReader(str(self.excel_path))
        trade_data = self.reader.read_all()

        if self.reader.get_warnings():
            print("Excel Reader Warnings:")
            for warning in self.reader.get_warnings():
                print(f"  ⚠️  {warning}")

        self.reader.print_summary()

        # Step 2: Create temporary folder
        print("Step 2: Creating temporary folder...")
        self.temp_folder = create_temp_folder(INPUT_PATH)
        print(f"✓ Created: {self.temp_folder}")
        print()

        # Step 3: Generate portfolio.xml
        print("Step 3: Generating portfolio.xml...")
        self.portfolio_generator = PortfolioGenerator(
            skip_invalid=self.skip_invalid,
            warn_on_skip=self.warn_on_skip
        )

        portfolio_elem = self.portfolio_generator.generate(
            swaps=self.reader.get_swaps(),
            fx_forwards=self.reader.get_fx_forwards(),
            fx_options=self.reader.get_fx_options(),
            cross_currency_swaps=self.reader.get_cross_currency_swaps()
        )

        self.portfolio_path = self.temp_folder / "portfolio.xml"
        self.portfolio_generator.save_to_file(portfolio_elem, self.portfolio_path)
        print(f"✓ Saved: {self.portfolio_path}")

        self.portfolio_generator.print_summary()

        # Step 4: Generate netting.xml (if netting data exists)
        netting_df = self.reader.get_netting_sets()
        if netting_df is not None and not netting_df.empty:
            print("Step 4: Generating netting.xml...")
            self.netting_generator = NettingGenerator()
            netting_elem = self.netting_generator.generate(netting_df)

            self.netting_path = self.temp_folder / "netting.xml"
            self.netting_generator.save_to_file(netting_elem, self.netting_path)
            print(f"✓ Saved: {self.netting_path}")
            print()
        else:
            print("Step 4: No netting data found, skipping netting.xml")
            print()

        # Step 5: Generate ore.xml
        print("Step 5: Generating ore.xml configuration...")
        ore_generator = OREConfigGenerator(self.template_ore_xml)
        ore_generator.load_template()

        # Update paths - ORE runs from ORELab root directory
        self.output_path = os.path.join(OUTPUT_PATH, self.temp_folder.name)

        ore_generator.update_paths(
            asof_date=self.asof_date,
            input_path=str(INPUT_PATH),
            output_path=str(self.output_path),
            portfolio_file=str(self.portfolio_path) if self.portfolio_path else None,
            netting_file=str(self.netting_path) if self.netting_path else None,
            static_path_prefix=str(STATIC_PATH)+'/'
        )

        self.ore_config_path = self.temp_folder / "ore.xml"
        ore_generator.save_to_file(self.ore_config_path)
        print(f"✓ Saved: {self.ore_config_path}")
        print()

        # Summary
        print("=" * 60)
        print("Conversion Complete!")
        print("=" * 60)
        print(f"Temporary folder: {self.temp_folder}")
        print(f"ORE config file: {self.ore_config_path}")
        print(f"Portfolio file: {self.portfolio_path}")
        if self.netting_path:
            print(f"Netting file: {self.netting_path}")
        print(f"Output folder: {self.output_path}")
        print("=" * 60 + "\n")

        return self.ore_config_path

    def get_generated_files(self) -> dict:
        """
        Get dictionary of generated file paths.

        Returns:
            Dictionary with paths to generated files
        """
        return {
            "temp_folder": self.temp_folder,
            "ore_config": self.ore_config_path,
            "portfolio": self.portfolio_path,
            "netting": self.netting_path
        }

    def get_summary(self) -> dict:
        """
        Get summary of conversion process.

        Returns:
            Dictionary with conversion statistics
        """
        summary = {
            "excel_file": str(self.excel_path),
            "temp_folder": str(self.temp_folder) if self.temp_folder else None,
            "files_generated": {}
        }

        if self.portfolio_generator:
            summary["portfolio"] = self.portfolio_generator.get_summary()

        if self.reader:
            summary["excel_warnings"] = self.reader.get_warnings()

        return summary


class ORERunner:
    """
    End-to-end ORE execution from Excel to results.

    This class orchestrates the complete workflow:
    1. Convert Excel to XML using OREXlsxConverter
    2. Run OREApp to execute analytics
    3. Parse and store NPV and exposure results
    4. Provide accessor methods for results
    5. Clean up temporary files

    Usage:
        with ORERunner('trades.xlsx') as runner:
            runner.run()

            # Access results
            npv_df = runner.get_npv()
            xva_df = runner.get_xva()

            # Get specific trade data
            trade_npv = runner.get_trade_npv('Trade_123')
            trade_epe = runner.get_trade_exposure('Trade_123')

            # Optionally save results before cleanup
            runner.save_results('/path/to/permanent/location')
        # Auto-cleanup removes temp folders

        # Override asofDate in ore.xml
        with ORERunner('trades.xlsx', asof_date='2024-03-15') as runner:
            runner.run()
    """

    def __init__(
        self,
        excel_path: str,
        cleanup: bool = True,
        **converter_kwargs
    ):
        """
        Initialize ORERunner.

        Args:
            excel_path: Path to Excel file with trade data
            cleanup: Whether to cleanup temp folders on exit (default: True)
            **converter_kwargs: Additional arguments passed to OREXlsxConverter
                (e.g., template_ore_xml, asof_date, skip_invalid, warn_on_skip)

        Raises:
            FileNotFoundError: If Excel file doesn't exist
        """
        self.excel_path = Path(excel_path)
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Excel file not found: {excel_path}")

        self.cleanup = cleanup
        self.converter_kwargs = converter_kwargs

        # Components
        self.converter: Optional[OREXlsxConverter] = None
        self.output_path: Optional[Path] = None

        # Cached results (lazy-loaded)
        self._npv_df: Optional[pd.DataFrame] = None
        self._xva_df: Optional[pd.DataFrame] = None
        self._exposure_trade_df: Optional[pd.DataFrame] = None
        self._exposure_nettingset_df: Optional[pd.DataFrame] = None

        # Execution state
        self._executed: bool = False

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - cleanup if requested."""
        if self.cleanup:
            self.cleanup_files()

    def run(self) -> None:
        """
        Execute the complete ORE workflow.

        Steps:
        1. Convert Excel to XML files
        2. Run ORE analytics
        3. Parse result files

        Raises:
            RuntimeError: If ORE execution fails
            ImportError: If ORE module not available
        """
        if self._executed:
            warnings.warn("ORE has already been executed. Skipping re-run.")
            return

        # Step 1: Convert Excel to XML
        print("=" * 60)
        print("STEP 1: Excel to XML Conversion")
        print("=" * 60)

        # Use OREXlsxConverter but don't auto-cleanup (we'll manage it)
        self.converter = OREXlsxConverter(
            excel_path=str(self.excel_path),
            cleanup=False,  # We'll handle cleanup
            **self.converter_kwargs
        )

        ore_config_path = self.converter.convert()
        self.output_path = Path(self.converter.output_path)

        # Step 2: Run ORE
        print("=" * 60)
        print("STEP 2: Running ORE Analytics")
        print("=" * 60)

        print(f"Loading configuration: {ore_config_path}")
        params = ORE.Parameters()
        params.fromFile(str(ore_config_path))

        print("Executing ORE...")
        app = ORE.OREApp(params, True)  # True = console mode
        app.run()

        print("\n✓ ORE execution completed")
        print(f"✓ Results written to: {self.output_path}")
        print()

        # Step 3: Parse results
        print("=" * 60)
        print("STEP 3: Parsing Results")
        print("=" * 60)
        self._parse_results()

        self._executed = True

    def _parse_results(self) -> None:
        """Parse ORE output files into DataFrames."""
        if not self.output_path or not self.output_path.exists():
            warnings.warn(f"Output path not found: {self.output_path}")
            return
        
        self._parse_npv()
        self._parse_xva()
        self._parse_exposures()

    def _parse_npv(self) -> None:
        """Parse NPV results."""
        try:
            npv_file = self.output_path / "npv.csv"
            if not npv_file.exists():
                raise FileNotFoundError(f"NPV file not found: {npv_file}")

            self._npv_df = pd.read_csv(npv_file)

            print("  ✓ Parsed NPV results")
        except FileNotFoundError:
            print("  ⚠️  NPV results file not found")

    def _parse_xva(self) -> None:
        """Parse XVA results."""
        try:
            xva_file = self.output_path / "xva.csv"
            if not xva_file.exists():
                raise FileNotFoundError(f"XVA file not found: {xva_file}")
            self._xva_df = pd.read_csv(xva_file)

            print("  ✓ Parsed XVA results")
        except FileNotFoundError:
            print("  ⚠️  XVA results file not found")

    def _parse_exposures(self) -> None:
        """Parse exposure results (trade and netting set)."""
        for exposure_type in ['trade', 'nettingset']:
            try:
                pattern = f"exposure_{exposure_type}_*.csv"
                exposure_files = list(self.output_path.glob(pattern))

                if not exposure_files:
                    continue

                # Read and combine all exposure files
                dfs = []
                for file in exposure_files:
                    df = pd.read_csv(file)
                    dfs.append(df)

                combined_df = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]

                # Cache result
                if exposure_type == 'trade':
                    self._exposure_trade_df = combined_df
                else:
                    self._exposure_nettingset_df = combined_df

                print(f"  ✓ Parsed {exposure_type} exposure results")
            except Exception as e:
                print(f"  ⚠️  Failed to parse {exposure_type} exposure files: {e}")

    def get_npv(self) -> pd.DataFrame:
        """
        Get NPV results as DataFrame.
        """
        return self._npv_df

    def get_xva(self) -> pd.DataFrame:
        """
        Get XVA results as DataFrame.
        """
        return self._xva_df

    def get_exposures(self, exposure_type: str = 'trade') -> pd.DataFrame:
        """
        Get exposure profiles (EPE/ENE) as DataFrame.
        """
        if exposure_type == 'trade':
            return self._exposure_trade_df
        if exposure_type == 'nettingset':
            return self._exposure_nettingset_df
        else:
            raise ValueError(f"Invalid exposure_type: {exposure_type}. Use 'trade' or 'nettingset'")

    def save_results(self, destination: str) -> None:
        """
        Copy results to a permanent location before cleanup.

        Args:
            destination: Destination directory path

        Raises:
            ValueError: If results haven't been generated yet
        """
        if not self._executed:
            raise ValueError("Cannot save results - ORE hasn't been executed yet. Call run() first.")

        if not self.output_path or not self.output_path.exists():
            raise ValueError(f"Output path not found: {self.output_path}")

        dest_path = Path(destination)
        dest_path.mkdir(parents=True, exist_ok=True)

        print(f"Copying results to: {dest_path}")

        # Copy all files from output folder
        for file in self.output_path.glob("*"):
            if file.is_file():
                shutil.copy2(file, dest_path / file.name)

        print(f"✓ Results saved to: {dest_path}")

    def cleanup_files(self) -> None:
        """
        Remove temporary input and output folders.
        """
        removed = []

        # Clean up converter's temp folder (input)
        if self.converter and self.converter.temp_folder:
            if self.converter.temp_folder.exists():
                cleanup_temp_folder(self.converter.temp_folder)
                removed.append(f"Input: {self.converter.temp_folder}")

        # Clean up output folder
        if self.output_path and self.output_path.exists():
            cleanup_temp_folder(self.output_path)
            removed.append(f"Output: {self.output_path}")

        if removed:
            print("✓ Cleaned up temporary folders:")
            for path in removed:
                print(f"  - {path}")

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of execution and results.

        Returns:
            Dictionary with execution statistics and result counts
        """
        summary = {
            "excel_file": str(self.excel_path),
            "executed": self._executed,
            "output_path": str(self.output_path) if self.output_path else None,
        }

        if self._executed and self.output_path and self.output_path.exists():
            # Add result counts
            try:
                npv_df = self.get_npv()
                summary["num_trades"] = len(npv_df)
            except FileNotFoundError:
                pass

            try:
                xva_df = self.get_xva()
                summary["xva_available"] = True
            except FileNotFoundError:
                summary["xva_available"] = False

        # Add converter summary if available
        if self.converter:
            summary["converter"] = self.converter.get_summary()

        return summary
