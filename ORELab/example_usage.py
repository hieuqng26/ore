"""
Example usage of ORELab Excel-to-ORE converter.

This script demonstrates how to:
1. Convert Excel trade data to ORE XML format
2. Run ORE analytics on the generated portfolio
3. Read and display results
"""

from pathlib import Path
from orelab import OREXlsxConverter, ORERunner
import ORE


# Example 1: Basic usage with context manager (auto cleanup)
def example_basic():
    """Basic conversion with automatic cleanup."""
    print("\n" + "=" * 70)
    print("Example 1: Basic Conversion with Auto Cleanup")
    print("=" * 70)

    excel_file = "templates/sample_trades.xlsx"

    with OREXlsxConverter(excel_file, cleanup=True) as converter:
        # Inside the context, temp folder exists
        print(f"\nTemporary folder created: {converter.temp_folder}")
        print(f"ORE config file: {converter.ore_config_path}")

        # You can run ORE here
        # import ORE
        # params = ORE.Parameters()
        # params.fromFile(str(converter.ore_config_path))
        # app = ORE.OREApp(params, True)
        # app.run()

    print("\nContext exited - temporary folder cleaned up automatically")


# Example 2: Conversion without cleanup (keep files for inspection)
def example_no_cleanup():
    """Conversion keeping temporary files for inspection."""
    print("\n" + "=" * 70)
    print("Example 2: Conversion without Cleanup")
    print("=" * 70)

    excel_file = "templates/sample_trades.xlsx"

    with OREXlsxConverter(excel_file, cleanup=False) as converter:
        print(f"\nGenerated files:")
        print(f"  • ORE config: {converter.ore_config_path}")
        print(f"  • Portfolio:  {converter.portfolio_path}")
        print(f"  • Netting:    {converter.netting_path}")

        # Get summary
        summary = converter.get_summary()
        print(f"\nPortfolio summary:")
        print(f"  • Generated trades: {summary['portfolio']['generated_count']}")
        print(f"  • Skipped trades:   {summary['portfolio']['skipped_count']}")

    print(f"\nTemporary folder kept for inspection: {converter.temp_folder}")


# Example 3: Manual conversion (no context manager)
def example_manual():
    """Manual conversion without context manager."""
    print("\n" + "=" * 70)
    print("Example 3: Manual Conversion")
    print("=" * 70)

    excel_file = "templates/sample_trades.xlsx"

    # Create converter
    converter = OREXlsxConverter(
        excel_file,
        skip_invalid=True,
        warn_on_skip=True,
        cleanup=False  # We'll clean up manually
    )

    # Perform conversion
    ore_config = converter.convert()
    print(f"\nORE configuration ready at: {ore_config}")

    # Access generated files
    files = converter.get_generated_files()
    print(f"\nAll generated files:")
    for file_type, path in files.items():
        if path:
            print(f"  • {file_type:15s}: {path}")

    # Manual cleanup if desired
    # from orelab.utils import cleanup_temp_folder
    # cleanup_temp_folder(converter.temp_folder)


# Example 4: Custom configuration
def example_custom_config():
    """Conversion with custom settings."""
    print("\n" + "=" * 70)
    print("Example 4: Custom Configuration")
    print("=" * 70)

    excel_file = "templates/sample_trades.xlsx"

    # Use custom template ore.xml
    custom_template = "Input/ore.xml"

    # Custom output path
    custom_output = Path("Output/excel_conversion")
    custom_output.mkdir(parents=True, exist_ok=True)

    converter = OREXlsxConverter(
        excel_file,
        template_ore_xml=custom_template,
        output_path=str(custom_output),
        skip_invalid=True,
        warn_on_skip=True,
        cleanup=False
    )

    converter.convert()

    print(f"\nResults will be saved to: {custom_output}")
    print(f"Temporary config folder: {converter.temp_folder}")


# Example 5: Running ORE with converted data
def example_run_ore():
    """Convert and run ORE analytics."""
    print("\n" + "=" * 70)
    print("Example 5: Convert and Run ORE")
    print("=" * 70)

    excel_file = "templates/sample_trades.xlsx"

    # Use custom template ore.xml
    custom_template = "Input/ore.xml"

    try:
        with OREXlsxConverter(
            excel_file,
            template_ore_xml=custom_template,
            # skip_invalid=True,
            # warn_on_skip=True,
            # cleanup=False
        ) as converter:
            print(f"\nRunning ORE with config: {converter.ore_config_path}")

            # Load parameters
            params = ORE.Parameters()
            params.fromFile(str(converter.ore_config_path))

            # Run ORE
            print("\nExecuting ORE analytics...")
            app = ORE.OREApp(params, True)
            app.run()

            print("\n✓ ORE analytics completed!")
            print(f"\nResults saved to output folder")

    except ImportError:
        print("\n⚠️  ORE Python module not available.")
        print("Install ORE Python bindings to run this example.")


# Example 6: End-to-end execution with ORERunner
def example_ore_runner():
    """
    Complete workflow using ORERunner.

    ORERunner handles:
    - Excel to XML conversion
    - ORE execution
    - Result parsing and storage
    - Automatic cleanup
    """
    print("\n" + "=" * 70)
    print("Example 6: Complete Workflow with ORERunner")
    print("=" * 70)

    excel_file = "templates/sample_trades.xlsx"

    try:
        # ORERunner handles the complete workflow
        with ORERunner(excel_file, asof_date='2025-02-05', cleanup=True) as runner:
            # Execute: Convert → Run ORE → Parse results
            runner.run()

            # Access NPV results
            print("\n" + "=" * 70)
            print("NPV Results")
            print("=" * 70)
            npv_df = runner.get_npv()
            print(npv_df.head())
            print(f"\nTotal trades: {len(npv_df)}")

            # Access XVA results
            try:
                print("\n" + "=" * 70)
                print("XVA Results")
                print("=" * 70)
                xva_df = runner.get_xva()
                print(xva_df.head())
            except FileNotFoundError:
                print("\nXVA results not available (requires XVA analytics enabled)")

            # Access exposure profiles
            try:
                print("\n" + "=" * 70)
                print("Exposure Profiles")
                print("=" * 70)
                exposure_df = runner.get_exposures(exposure_type='trade')
                print(f"Exposure data shape: {exposure_df.shape}")
                print(exposure_df.head())
            except FileNotFoundError:
                print("\nExposure data not available (requires simulation)")

            # Get execution summary
            print("\n" + "=" * 70)
            print("Execution Summary")
            print("=" * 70)
            summary = runner.get_summary()
            print(f"Excel file: {summary['excel_file']}")
            print(f"Executed: {summary['executed']}")
            if 'num_trades' in summary:
                print(f"Number of trades: {summary['num_trades']}")
            if 'xva_available' in summary:
                print(f"XVA available: {summary['xva_available']}")

        # Temp folders cleaned up automatically after exiting context
        print("\n✓ Temporary folders cleaned up automatically")

    except ImportError:
        print("\n⚠️  ORE Python module not available.")
        print("Install ORE Python bindings to run this example.")
    except FileNotFoundError as e:
        print(f"\n⚠️  File not found: {e}")


# Example 7: ORERunner with custom settings and result preservation
def example_ore_runner_advanced():
    """
    Advanced ORERunner usage with custom settings and result preservation.
    """
    print("\n" + "=" * 70)
    print("Example 7: Advanced ORERunner with Result Preservation")
    print("=" * 70)

    excel_file = "templates/sample_trades.xlsx"
    results_dir = "Output/preserved_results"

    try:
        # ORERunner with custom converter settings
        with ORERunner(
            excel_file,
            asof_date='2016-02-05',
            cleanup=True,
            # Pass additional args to OREXlsxConverter
            template_ore_xml="Input/ore.xml",
            skip_invalid=True,
            warn_on_skip=True
        ) as runner:
            # Execute workflow
            runner.run()

            # Get results
            npv_df = runner.get_npv()
            print(f"\nProcessed {len(npv_df)} trades")

            # Save results to permanent location before cleanup
            runner.save_results(results_dir)
            print(f"\n✓ Results preserved at: {results_dir}")

        print("\n✓ Temporary folders cleaned up, but results preserved")

    except ImportError:
        print("\n⚠️  ORE Python module not available.")
        print("Install ORE Python bindings to run this example.")
    except Exception as e:
        print(f"\n⚠️  Error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ORELab Excel-to-ORE Converter - Example Usage")
    print("=" * 70)

    # Run examples
    # example_basic()
    # example_no_cleanup()
    # example_manual()
    # example_custom_config()
    # example_run_ore()

    # New ORERunner examples - Complete end-to-end workflow
    example_ore_runner()
    # example_ore_runner_advanced()

    print("\n" + "=" * 70)
    print("Examples completed!")
    print("=" * 70 + "\n")
