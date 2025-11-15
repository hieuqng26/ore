"""
Script to create sample Excel template with example trades.
Run this to generate the template file.
"""

import pandas as pd
from pathlib import Path


def create_sample_excel_template(output_path: str = None):
    """Create sample Excel template with example trades."""

    if output_path is None:
        templates_dir = Path(__file__).parent.parent / "templates"
        templates_dir.mkdir(exist_ok=True)
        output_path = templates_dir / "sample_trades.xlsx"
    else:
        output_path = Path(output_path)

    # Interest Rate Swaps sheet
    swaps_data = {
        "TradeId": ["IRS_EUR_10Y_A", "IRS_USD_5Y_B"],
        "CounterParty": ["CPTY_A", "CPTY_B"],
        "Currency": ["EUR", "USD"],
        "Notional": [10000000, 5000000],
        "StartDate": ["20160301", "20160315"],
        "EndDate": ["20260301", "20210315"],
        "PayerOrReceiver": ["Receiver", "Payer"],  # Receiver = receive fixed, pay floating
        "FixedRate": [0.01, 0.015],
        "FixedTenor": ["1Y", "6M"],
        "FixedDayCounter": ["30/360", "ACT/360"],
        "FloatingIndex": ["EUR-EURIBOR-6M", "USD-LIBOR-3M"],
        "FloatingTenor": ["6M", "3M"],
        "FloatingDayCounter": ["A360", "A360"],
        "FloatingSpread": [0.0, 0.001],  # Optional spread on floating leg
    }
    df_swaps = pd.DataFrame(swaps_data)

    # FX Forwards sheet
    fx_fwd_data = {
        "TradeId": ["FXFWD_EURUSD_1Y_A", "FXFWD_GBPUSD_6M_B"],
        "CounterParty": ["CPTY_A", "CPTY_B"],
        "ValueDate": ["2017-02-05", "2016-08-05"],
        "BoughtCurrency": ["EUR", "GBP"],
        "BoughtAmount": [1000000, 500000],
        "SoldCurrency": ["USD", "USD"],
        "SoldAmount": [1100000, 700000],
    }
    df_fx_fwd = pd.DataFrame(fx_fwd_data)

    # FX Options sheet
    fx_opt_data = {
        "TradeId": ["FXOPT_EURUSD_CALL_A", "FXOPT_GBPUSD_PUT_B"],
        "CounterParty": ["CPTY_A", "CPTY_B"],
        "ExerciseDate": ["2017-02-05", "2016-12-05"],
        "LongShort": ["Long", "Long"],
        "OptionType": ["Call", "Put"],
        "Style": ["European", "European"],
        "BoughtCurrency": ["EUR", "GBP"],
        "BoughtAmount": [1000000, 500000],
        "SoldCurrency": ["USD", "USD"],
        "SoldAmount": [1100000, 650000],
    }
    df_fx_opt = pd.DataFrame(fx_opt_data)

    # Cross-Currency Swaps sheet
    ccs_data = {
        "TradeId": ["CCS_EURUSD_10Y_A", "CCS_GBPUSD_5Y_B"],
        "CounterParty": ["CPTY_A", "CPTY_B"],
        "StartDate": ["20160205", "20160301"],
        "EndDate": ["20260205", "20210301"],
        "Currency1": ["USD", "GBP"],
        "Notional1": [100000000, 50000000],
        "Index1": ["USD-LIBOR-6M", "GBP-LIBOR-6M"],
        "Spread1": [0.0, 0.0],
        "Tenor1": ["6M", "6M"],
        "DayCounter1": ["A360", "A365"],
        "Currency2": ["EUR", "USD"],
        "Notional2": [88312931.57, 70000000],
        "Index2": ["EUR-EURIBOR-6M", "USD-LIBOR-6M"],
        "Spread2": [0.015, 0.01],
        "Tenor2": ["6M", "6M"],
        "DayCounter2": ["A360", "A360"],
        "InitialExchange": [True, True],
        "FinalExchange": [True, True],
    }
    df_ccs = pd.DataFrame(ccs_data)

    # Netting Sets sheet
    netting_data = {
        "NettingSetId": ["CPTY_A", "CPTY_B", "CPTY_C"],
        "CounterParty": ["CPTY_A", "CPTY_B", "CPTY_C"],
        "CSAThreshold": [0, 100000, 50000],
        "CSAMta": [0, 10000, 5000],
        "CollateralCurrency": ["EUR", "USD", "EUR"],
    }
    df_netting = pd.DataFrame(netting_data)

    # Write to Excel with multiple sheets
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        df_swaps.to_excel(writer, sheet_name='InterestRateSwaps', index=False)
        df_fx_fwd.to_excel(writer, sheet_name='FXForwards', index=False)
        df_fx_opt.to_excel(writer, sheet_name='FXOptions', index=False)
        df_ccs.to_excel(writer, sheet_name='CrossCurrencySwaps', index=False)
        df_netting.to_excel(writer, sheet_name='NettingSets', index=False)

    print(f"✓ Sample Excel template created: {output_path}")
    return output_path


if __name__ == "__main__":
    create_sample_excel_template()
