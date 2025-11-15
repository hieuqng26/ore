# ORELab Quick Start Guide

## 1. Generate Sample Excel Template

```python
from orelab.create_template import create_sample_excel_template

# Creates templates/sample_trades.xlsx with example trades
create_sample_excel_template()
```

## 2. Basic Conversion (Recommended)

```python
from orelab import OREConverter

# Simple conversion with automatic cleanup
with OREConverter('templates/sample_trades.xlsx') as converter:
    print(f"ORE config: {converter.ore_config_path}")
    print(f"Portfolio:  {converter.portfolio_path}")
    # Temp folder auto-cleaned on exit
```

## 3. Keep Files for Inspection

```python
from orelab import OREConverter

# Keep temporary files after conversion
with OREConverter('templates/sample_trades.xlsx', cleanup=False) as converter:
    print(f"Inspect files at: {converter.temp_folder}")
    # Files remain after exit
```

## 4. Run ORE Analytics

```python
import ORE
from orelab import OREConverter

with OREConverter('templates/sample_trades.xlsx', cleanup=False) as converter:
    # Load configuration
    params = ORE.Parameters()
    params.fromFile(str(converter.ore_config_path))

    # Run ORE
    app = ORE.OREApp(params, True)
    app.run()

    print("Results in Output/ folder")
```

## 5. Excel File Format

Your Excel file should have these sheets:

### InterestRateSwaps
| TradeId | CounterParty | Currency | Notional | StartDate | EndDate | PayerOrReceiver | FixedRate | ... |
|---------|-------------|----------|----------|-----------|---------|-----------------|-----------|-----|
| IRS_001 | CPTY_A | EUR | 10000000 | 20160301 | 20260301 | Receiver | 0.01 | ... |

### FXForwards
| TradeId | CounterParty | ValueDate | BoughtCurrency | BoughtAmount | SoldCurrency | SoldAmount |
|---------|-------------|-----------|----------------|--------------|--------------|------------|
| FXF_001 | CPTY_A | 2017-02-05 | EUR | 1000000 | USD | 1100000 |

### FXOptions
| TradeId | CounterParty | ExerciseDate | LongShort | OptionType | Style | BoughtCurrency | ... |
|---------|-------------|--------------|-----------|------------|-------|----------------|-----|
| FXO_001 | CPTY_A | 2017-02-05 | Long | Call | European | EUR | ... |

### CrossCurrencySwaps
| TradeId | CounterParty | StartDate | EndDate | Currency1 | Notional1 | Index1 | Currency2 | ... |
|---------|-------------|-----------|---------|-----------|-----------|--------|-----------|-----|
| CCS_001 | CPTY_A | 20160205 | 20260205 | USD | 100000000 | USD-LIBOR-6M | EUR | ... |

### NettingSets
| NettingSetId | CounterParty | CSAThreshold | CSAMta | CollateralCurrency |
|--------------|-------------|--------------|--------|-------------------|
| CPTY_A | CPTY_A | 0 | 0 | EUR |

## 6. Command Line Usage

```bash
# From ORELab directory
cd /Users/hieunguyen/Downloads/projects/ORE/ORELab

# Run example
python example_usage.py

# Or use in Python script
python -c "
from orelab import OREConverter
with OREConverter('templates/sample_trades.xlsx') as conv:
    print(conv.ore_config_path)
"
```

## 7. File Locations

After conversion:
```
ORELab/                     # Run ORE from here!
├── db/
│   ├── temp_<timestamp>/   # Temporary folder
│   │   ├── ore.xml        # ORE configuration
│   │   ├── portfolio.xml  # Generated portfolio
│   │   └── netting.xml    # Generated netting sets
│   └── Static/            # Reused static configs
├── Output/
│   └── temp_<timestamp>/  # Results for this conversion
└── ...
```

**Run ORE from ORELab root:**
```bash
cd /path/to/ORELab
ore db/temp_YYYYMMDD_HHMMSS/ore.xml
```

## 8. Troubleshooting

**Missing columns**: Check Excel sheet has all required columns
**Date errors**: Use YYYYMMDD (20160205) or YYYY-MM-DD (2016-02-05)
**Invalid trades**: Check validation warnings, fix data or set `skip_invalid=True`

## 9. Key Features

✓ Context manager with auto-cleanup
✓ Trade validation with helpful errors
✓ Support for 4 trade types + netting
✓ Reuses existing Static/ configurations
✓ Multiple concurrent conversions safe
✓ Detailed conversion summary

## 10. Next Steps

- Review [README.md](README.md) for full documentation
- Check [example_usage.py](example_usage.py) for more examples
- Edit [templates/sample_trades.xlsx](templates/sample_trades.xlsx) with your trades
- Run conversion and inspect generated XML files
- Execute ORE analytics on your portfolio

---

For detailed API reference, see [README.md](README.md)
