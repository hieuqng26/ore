# ORELab - Excel to ORE Converter

A Python package for converting Excel trade data into ORE (Open Source Risk Engine) XML format and running risk analytics.

## Features

- **Excel-based trade input**: Define trades in Excel spreadsheets with separate sheets per trade type
- **Automatic XML generation**: Converts Excel data to ORE portfolio.xml and netting.xml
- **Trade validation**: Validates trades before XML generation with configurable error handling
- **Context manager API**: Pythonic interface with automatic cleanup
- **Supported trade types**:
  - Interest Rate Swaps (fixed vs floating)
  - FX Forwards
  - FX Options
  - Cross-Currency Swaps
- **Netting sets**: CSA configuration for counterparty credit risk

## Installation

Ensure you have the required dependencies:

```bash
pip install -r requirements.txt
```

Required packages:
- pandas
- openpyxl
- lxml
- open-source-risk-engine (ORE Python bindings)

## Quick Start

### 1. Prepare Excel File

Use the provided sample template or create your own:

```python
from orelab.create_template import create_sample_excel_template

# Create sample Excel file
create_sample_excel_template("my_trades.xlsx")
```

The Excel file should have the following sheets:

- **InterestRateSwaps**: Fixed vs floating rate swaps
- **FXForwards**: Foreign exchange forwards
- **FXOptions**: FX options (calls/puts)
- **CrossCurrencySwaps**: Multi-currency swaps with notional exchanges
- **NettingSets**: Counterparty CSA details

### 2. Convert Excel to ORE XML

```python
from orelab import OREConverter

# Basic usage with context manager
with OREConverter('my_trades.xlsx', cleanup=True) as converter:
    ore_config = converter.ore_config_path
    print(f"ORE config ready at: {ore_config}")

    # Run ORE here or inspect generated files
    # Temporary folder cleaned up automatically on exit
```

### 3. Run ORE Analytics (Optional)

```python
import ORE
from orelab import OREConverter

with OREConverter('my_trades.xlsx', cleanup=False) as converter:
    # Load ORE configuration
    params = ORE.Parameters()
    params.fromFile(str(converter.ore_config_path))

    # Run analytics
    app = ORE.OREApp(params, True)
    app.run()

    print("Analytics completed! Check Output folder for results.")
```

## Excel File Format

### Interest Rate Swaps Sheet

Required columns:
- `TradeId`: Unique identifier
- `CounterParty`: Counterparty name
- `Currency`: Currency code (e.g., EUR, USD)
- `Notional`: Notional amount
- `StartDate`: Start date (YYYYMMDD or YYYY-MM-DD)
- `EndDate`: End date (YYYYMMDD or YYYY-MM-DD)
- `PayerOrReceiver`: "Payer" (pay fixed) or "Receiver" (receive fixed)
- `FixedRate`: Fixed rate (e.g., 0.01 for 1%)
- `FixedTenor`: Fixed leg payment frequency (e.g., "1Y", "6M")
- `FixedDayCounter`: Day count convention (e.g., "30/360", "ACT/360")
- `FloatingIndex`: Floating rate index (e.g., "EUR-EURIBOR-6M")
- `FloatingTenor`: Floating leg payment frequency
- `FloatingDayCounter`: Floating leg day counter
- `FloatingSpread`: Spread on floating leg (optional, default: 0)

### FX Forwards Sheet

Required columns:
- `TradeId`: Unique identifier
- `CounterParty`: Counterparty name
- `ValueDate`: Settlement date
- `BoughtCurrency`: Currency being bought
- `BoughtAmount`: Amount bought
- `SoldCurrency`: Currency being sold
- `SoldAmount`: Amount sold

### FX Options Sheet

Required columns:
- `TradeId`: Unique identifier
- `CounterParty`: Counterparty name
- `ExerciseDate`: Exercise date
- `LongShort`: "Long" or "Short"
- `OptionType`: "Call" or "Put"
- `Style`: "European", "American", or "Bermudan"
- `BoughtCurrency`: Underlying bought currency
- `BoughtAmount`: Underlying bought amount
- `SoldCurrency`: Underlying sold currency
- `SoldAmount`: Underlying sold amount

### Cross-Currency Swaps Sheet

Required columns:
- `TradeId`: Unique identifier
- `CounterParty`: Counterparty name
- `StartDate`: Start date
- `EndDate`: End date
- `Currency1`, `Notional1`: First leg currency and notional
- `Index1`, `Spread1`: First leg index and spread
- `Tenor1`, `DayCounter1`: First leg tenor and day counter
- `Currency2`, `Notional2`: Second leg currency and notional
- `Index2`, `Spread2`: Second leg index and spread
- `Tenor2`, `DayCounter2`: Second leg tenor and day counter
- `InitialExchange`: Initial notional exchange (True/False)
- `FinalExchange`: Final notional exchange (True/False)

### Netting Sets Sheet

Required columns:
- `NettingSetId`: Unique netting set identifier
- `CounterParty`: Counterparty name

Optional columns:
- `CSAThreshold`: Credit Support Annex threshold
- `CSAMta`: Minimum Transfer Amount
- `CollateralCurrency`: Currency for collateral

## API Reference

### OREConverter

Main conversion engine with context manager interface.

```python
OREConverter(
    excel_path: str,
    template_ore_xml: Optional[str] = None,
    output_path: Optional[str] = None,
    cleanup: bool = True,
    skip_invalid: bool = True,
    warn_on_skip: bool = True
)
```

**Parameters:**
- `excel_path`: Path to Excel file with trade data
- `template_ore_xml`: Path to template ore.xml (default: db/ore.xml)
- `output_path`: Output path for ORE results (default: Output/)
- `cleanup`: Whether to cleanup temp folder on exit (default: True)
- `skip_invalid`: Skip invalid trades instead of raising error (default: True)
- `warn_on_skip`: Print warnings for skipped trades (default: True)

**Attributes:**
- `temp_folder`: Path to temporary folder with generated files
- `ore_config_path`: Path to generated ore.xml
- `portfolio_path`: Path to generated portfolio.xml
- `netting_path`: Path to generated netting.xml

**Methods:**
- `convert()`: Perform conversion and return path to ore.xml
- `get_generated_files()`: Get dictionary of all generated file paths
- `get_summary()`: Get conversion statistics

## File Structure

```
ORELab/
├── orelab/                      # Main package
│   ├── __init__.py
│   ├── engine.py               # OREConverter class
│   ├── excel_reader.py         # Excel reading logic
│   ├── validators.py           # Trade validation
│   ├── config.py               # Configuration constants
│   ├── utils.py                # Utility functions
│   ├── create_template.py      # Template generator
│   ├── trade_builders/         # XML builders for each trade type
│   │   ├── base.py
│   │   ├── swap.py
│   │   ├── fx_forward.py
│   │   ├── fx_option.py
│   │   └── cross_currency_swap.py
│   └── xml_generators/         # XML file generators
│       ├── portfolio.py
│       ├── netting.py
│       └── ore_config.py
├── templates/                   # Sample Excel templates
│   └── sample_trades.xlsx
├── db/                          # Configuration and temp folders
│   ├── ore.xml                 # Template ORE configuration
│   ├── netting.xml             # Sample netting configuration
│   ├── Static/                 # Static ORE configuration files
│   └── temp_*/                 # Temporary folders (created/cleaned)
├── Output/                      # ORE results
├── example_usage.py            # Usage examples
└── README.md                   # This file
```

## Path Configuration

The converter handles paths carefully:

1. **Temporary folder**: Created as `db/temp_<timestamp>/`
2. **Generated files**: portfolio.xml, netting.xml, ore.xml in temp folder
3. **Static files**: Referenced as `Static/` (relative to db/)
4. **Input path**: Set to `db` in ore.xml (ORE runs from ORELab root)
5. **Output path**: `Output/temp_<timestamp>/` (separate output per conversion)

**ORE runs from the ORELab root directory** with paths configured as:
- `inputPath = db` → base path for all relative files
- `portfolioFile = temp_20251114_xxx/portfolio.xml` → relative to db/ ✓
- `csaFile = temp_20251114_xxx/netting.xml` → relative to db/ ✓
- `marketDataFile = Static/market_xxx.txt` → relative to db/ ✓
- `outputPath = Output/temp_20251114_xxx` → relative output path ✓

**Example from ORELab root:**
```bash
cd /path/to/ORELab
ore db/temp_20251114_xxx/ore.xml
```

This structure ensures:
- Static configuration files are shared across conversions
- Multiple conversions can run concurrently with separate outputs
- Cleanup is simple (delete temp folder)
- ORE finds all files using paths relative to db/

## Validation

The converter performs moderate validation:

**Required field checks:**
- All mandatory fields must be present
- Trade IDs must be unique

**Data type validation:**
- Dates in valid format (YYYYMMDD or YYYY-MM-DD)
- Currencies are 3-letter codes
- Numeric fields contain valid numbers
- Tenors in valid format (e.g., 1Y, 6M)

**Business logic validation:**
- Notionals must be positive
- Dates must be parseable
- FX trades have different currencies
- Rates within reasonable ranges

**Invalid trades:**
- Configurable: skip and warn, or raise error
- Skipped trades reported in summary

Complex validation (curve consistency, market data availability) is delegated to ORE.

## Examples

See [example_usage.py](example_usage.py) for complete examples including:

1. Basic conversion with auto-cleanup
2. Conversion keeping files for inspection
3. Manual conversion without context manager
4. Running ORE analytics on converted data
5. Custom configuration options

## Troubleshooting

### Excel File Issues

**Problem**: "Excel file not found"
- Solution: Check file path is correct and file exists

**Problem**: "Missing required field"
- Solution: Ensure all required columns are present in Excel sheets

### Validation Errors

**Problem**: "Invalid date format"
- Solution: Use YYYYMMDD or YYYY-MM-DD format (e.g., 20160205 or 2016-02-05)

**Problem**: "Invalid currency code"
- Solution: Use 3-letter ISO currency codes (EUR, USD, GBP, etc.)

### Path Issues

**Problem**: ORE can't find Static files
- Solution: Ensure db/Static/ folder exists with required configuration files

**Problem**: Output folder doesn't exist
- Solution: The converter creates it automatically, but check permissions

## Advanced Usage

### Custom Template

Use a custom ore.xml template:

```python
converter = OREConverter(
    'trades.xlsx',
    template_ore_xml='path/to/custom_ore.xml'
)
```

### Disable Cleanup for Debugging

Keep temporary files for inspection:

```python
with OREConverter('trades.xlsx', cleanup=False) as converter:
    print(f"Inspect files at: {converter.temp_folder}")
```

### Strict Validation Mode

Raise error on first invalid trade:

```python
converter = OREConverter(
    'trades.xlsx',
    skip_invalid=False  # Raise error instead of skipping
)
```

## Contributing

To extend the converter with new trade types:

1. Add trade type to `config.py` (TRADE_TYPES, REQUIRED_COLUMNS)
2. Create trade builder in `trade_builders/`
3. Add validation logic in `validators.py`
4. Update portfolio generator to use new builder
5. Add sample data to Excel template

## License

This package is part of the ORE (Open Source Risk Engine) project and follows the same Modified BSD License.

## Support

For issues and questions:
- Check existing examples in `example_usage.py`
- Review ORE documentation at http://opensourcerisk.org
- Consult the main ORE user guide in `Docs/userguide.pdf`
