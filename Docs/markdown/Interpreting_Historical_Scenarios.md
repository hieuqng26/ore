# Interpreting Historical Scenarios CSV File

## Overview

The `scenarios.csv` file contains historical market data used for Historical Simulation VaR calculations. Each row represents a complete snapshot of the market at a specific date, with columns representing different risk factors (yield curves, FX rates, etc.).

---

## File Structure

### Header Row (Column Names)
```
Date, Scenario, Numeraire, DiscountCurve/EUR/0, DiscountCurve/EUR/1, ..., DiscountCurve/USD/0, ..., IndexCurve/EUR-EONIA/0, ..., FXSpot/USDEUR/0
```

### Data Rows (Market Snapshots)
```
01/09/2016, 1, 1, 1.00013288, 1.00028576, 1.00086746, ..., 0.8929
02/09/2016, 1, 1, 1.00013272, 1.00028664, 1.00088575, ..., 0.8961
```

---

## Column Interpretation

### 1. Metadata Columns

| Column | Description | Example Value |
|--------|-------------|---------------|
| `Date` | Market date for this snapshot | 01/09/2016 |
| `Scenario` | Scenario number (always 1 for historical data) | 1 |
| `Numeraire` | Numeraire value (always 1 for historical scenarios) | 1 |

---

### 2. DiscountCurve Columns: `DiscountCurve/EUR/0`, `DiscountCurve/EUR/1`, etc.

**Format:** `DiscountCurve/{Currency}/{Index}`

**Meaning:** These columns store **zero-coupon discount factors** for different tenors on the discount curve.

#### What is a Discount Factor?

A discount factor DF(t) represents the present value of 1 unit of currency to be received at time t:

```
DF(t) = 1 / (1 + r(t))^t

where r(t) is the zero rate for maturity t
```

#### Index to Tenor Mapping

Based on the simulation configuration file ([simulation.xml](../../Examples/MarketRisk/Input/HistSimVar/simulation.xml:10)), the tenor structure is:

```xml
<Tenors>2W, 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 10Y, 15Y, 20Y, 30Y</Tenors>
```

**Mapping Table:**

| Index | Column Name | Tenor | Description |
|-------|-------------|-------|-------------|
| 0 | `DiscountCurve/EUR/0` | **2W** | 2-week discount factor |
| 1 | `DiscountCurve/EUR/1` | **1M** | 1-month discount factor |
| 2 | `DiscountCurve/EUR/2` | **3M** | 3-month discount factor |
| 3 | `DiscountCurve/EUR/3` | **6M** | 6-month discount factor |
| 4 | `DiscountCurve/EUR/4` | **1Y** | 1-year discount factor |
| 5 | `DiscountCurve/EUR/5` | **2Y** | 2-year discount factor |
| 6 | `DiscountCurve/EUR/6` | **3Y** | 3-year discount factor |
| 7 | `DiscountCurve/EUR/7` | **5Y** | 5-year discount factor |
| 8 | `DiscountCurve/EUR/8` | **10Y** | 10-year discount factor |
| 9 | `DiscountCurve/EUR/9` | **15Y** | 15-year discount factor |
| 10 | `DiscountCurve/EUR/10` | **20Y** | 20-year discount factor |
| 11 | `DiscountCurve/EUR/11` | **30Y** | 30-year discount factor |

---

### 3. Example: EUR Discount Curve on 01/09/2016

From the scenarios.csv file, for date 01/09/2016:

| Tenor | Discount Factor | Implied Zero Rate (approx) | Interpretation |
|-------|----------------|---------------------------|----------------|
| 2W | 1.00013288 | **-0.35% p.a.** | €1 in 2 weeks is worth €1.00013 today (negative rates!) |
| 1M | 1.00028576 | **-0.34% p.a.** | €1 in 1 month is worth €1.00029 today |
| 3M | 1.00086746 | **-0.35% p.a.** | €1 in 3 months is worth €1.00087 today |
| 6M | 1.00182186 | **-0.36% p.a.** | €1 in 6 months is worth €1.00182 today |
| 1Y | 1.00401245 | **-0.40% p.a.** | €1 in 1 year is worth €1.00401 today |
| 2Y | 1.00891951 | **-0.44% p.a.** | €1 in 2 years is worth €1.00892 today |
| 3Y | 1.01382496 | **-0.46% p.a.** | €1 in 3 years is worth €1.01382 today |
| 5Y | 1.02041018 | **-0.41% p.a.** | €1 in 5 years is worth €1.02041 today |
| 10Y | 0.99782009 | **+0.22% p.a.** | €1 in 10 years is worth €0.99782 today (positive rate) |
| 15Y | 0.94463063 | **+0.38% p.a.** | €1 in 15 years is worth €0.94463 today |
| 20Y | 0.89610906 | **+0.55% p.a.** | €1 in 20 years is worth €0.89611 today |
| 30Y | 0.83419271 | **+0.60% p.a.** | €1 in 30 years is worth €0.83419 today |

**Key Observation:** This snapshot shows the European negative interest rate environment of September 2016!
- Short-term rates (up to 5Y): Negative (DF > 1.0)
- Long-term rates (10Y+): Positive (DF < 1.0)

---

### 4. Why Discount Factors > 1.0?

**Discount factors greater than 1.0 indicate negative interest rates**, which were prevalent in Europe from 2014-2022.

#### Relationship to Zero Rates

For a given tenor t (in years), the discount factor DF and zero rate r are related by:

```
DF(t) = e^(-r × t)     (continuous compounding)

If r < 0 (negative rate):
  → DF(t) > 1.0

Example: 1-year tenor with -0.40% rate
  DF(1Y) = e^(-(-0.004) × 1) = e^(0.004) = 1.00401 ✓
```

#### Economic Interpretation

When DF > 1.0:
- Lenders pay borrowers to hold their money
- Central bank policy rates are negative
- Depositors are charged to hold cash in banks

**Historical Context:** The ECB (European Central Bank) deposit rate was:
- June 2014: -0.10%
- Sept 2016: -0.40% (around the time of this snapshot)
- Sept 2019: -0.50% (peak negative)

---

### 5. IndexCurve Columns

**Format:** `IndexCurve/{Index-Name}/{Index}`

Similar structure to DiscountCurve, but for forward rate curves used for floating rate instruments:

| Curve | Description | Columns |
|-------|-------------|---------|
| `IndexCurve/EUR-EONIA/0` to `/11` | EUR Overnight Index Average (overnight rate) | 12 tenors |
| `IndexCurve/EUR-EURIBOR-3M/0` to `/11` | EUR 3-month EURIBOR forward rates | 12 tenors |
| `IndexCurve/EUR-EURIBOR-6M/0` to `/11` | EUR 6-month EURIBOR forward rates | 12 tenors |
| `IndexCurve/USD-FedFunds/0` to `/11` | USD Federal Funds Rate (overnight) | 12 tenors |
| `IndexCurve/USD-LIBOR-3M/0` to `/11` | USD 3-month LIBOR forward rates | 12 tenors |

These represent the forward-looking discount factors for each index at different projection tenors.

---

### 6. FXSpot Column

**Format:** `FXSpot/USDEUR/0`

**Meaning:** FX spot exchange rate for USD/EUR (how many EUR per 1 USD)

**Example from 01/09/2016:**
```
FXSpot/USDEUR/0 = 0.8929
```

This means: **1 USD = 0.8929 EUR** (or equivalently, **1 EUR = 1.1200 USD**)

---

## Complete Column List

The scenarios.csv file contains **87 columns total**:

```
3 metadata columns:
  - Date
  - Scenario
  - Numeraire

84 market data columns:
  - DiscountCurve/EUR/0 to /11     (12 columns)
  - DiscountCurve/USD/0 to /11     (12 columns)
  - IndexCurve/EUR-EONIA/0 to /11  (12 columns)
  - IndexCurve/EUR-EURIBOR-3M/0 to /11  (12 columns)
  - IndexCurve/EUR-EURIBOR-6M/0 to /11  (12 columns)
  - IndexCurve/USD-FedFunds/0 to /11    (12 columns)
  - IndexCurve/USD-LIBOR-3M/0 to /11    (12 columns)
  - FXSpot/USDEUR/0                (1 column)
```

---

## How Historical Scenarios are Used in VaR

### Step 1: Load Historical Scenarios

The `HistoricalScenarioGenerator` reads all rows from scenarios.csv, creating a time series of complete market states from 2017-01-17 to 2019-12-30 (approximately 760 business days).

### Step 2: Calculate MPOR Returns

For a 10-day Margin Period of Risk (MPOR), ORE calculates returns between date t and date t+10:

```
Return(risk_factor, t→t+10) = Scenario(t+10, risk_factor) / Scenario(t, risk_factor)

Example for DiscountCurve/EUR/5 (2-year tenor):
  Date t=01/09/2016:     DF = 1.00891951
  Date t+10=15/09/2016:  DF = 1.00795432  (hypothetical)

  Return = 1.00795432 / 1.00891951 = 0.999043

  This return is applied to today's 2Y discount factor
```

### Step 3: Apply Returns to Today's Market

```
Shocked_Scenario(today) = Base_Scenario(today) × Return(t→t+10)

If today's EUR 2Y DF = 0.98500
Shocked DF = 0.98500 × 0.999043 = 0.98406

This represents a scenario where the 2Y rate shifted similarly to the
historical 10-day move from 01/09/2016 to 15/09/2016
```

### Step 4: Reprice Portfolio

For each historical scenario:
1. Apply all risk factor shocks to today's market
2. Rebuild all curves with shocked discount factors
3. Reprice entire portfolio to get NPV under shocked scenario
4. Calculate P&L = NPV(shocked) - NPV(base)

### Step 5: Calculate VaR

With ~700 P&L scenarios, VaR is the empirical quantile:
```
VaR_99% = 99th percentile of P&L distribution
```

---

## Practical Example: Cross-Currency Swap Valuation

Given the swap in the portfolio (EUR/USD):
- **EUR leg:** Pays EUR-EURIBOR-6M on EUR 30M notional
- **USD leg:** Receives USD-LIBOR-3M on USD 33.9M notional

**Risk Factors Used:**
1. `DiscountCurve/EUR/*` - For discounting EUR cashflows
2. `DiscountCurve/USD/*` - For discounting USD cashflows
3. `IndexCurve/EUR-EURIBOR-6M/*` - For projecting EUR floating rates
4. `IndexCurve/USD-LIBOR-3M/*` - For projecting USD floating rates
5. `FXSpot/USDEUR/0` - For converting USD to EUR

**Scenario Shock Example (Hypothetical):**

| Risk Factor | Today's Value | Historical Return | Shocked Value |
|-------------|---------------|-------------------|---------------|
| EUR 1Y DF | 0.99200 | 1.00401/1.00450 = 0.99512 | 0.99200 × 0.99512 = 0.98716 |
| USD 1Y DF | 0.98500 | 0.98707/0.98900 = 0.99805 | 0.98500 × 0.99805 = 0.98308 |
| EURUSD FX | 1.1200 | 0.8961/0.8929 = 1.00358 | 1.1200 × 1.00358 = 1.1240 |

The swap is then repriced with these shocked curves and FX rate to determine its value in this historical scenario.

---

## Key Takeaways

1. **Index = Tenor Position**: The number after the slash (e.g., `/0`, `/1`, `/11`) maps to the tenor grid defined in simulation.xml

2. **Discount Factors, Not Rates**: Columns contain discount factors (DF), not interest rates. Convert using:
   ```
   Zero Rate r = -ln(DF) / t
   ```

3. **Negative Rates → DF > 1**: Discount factors greater than 1.0 are normal for negative interest rate environments

4. **Complete Market Snapshot**: Each row is a complete, internally consistent market state that can be used for full portfolio revaluation

5. **Time Series**: The file contains a time series of daily market snapshots, enabling realistic historical scenario generation with actual market moves

6. **Granular Curve Representation**: 12 points per curve provide sufficient granularity to capture the yield curve shape accurately

---

## Configuration Files

- **Scenario File:** [Examples/MarketRisk/Input/HistSimVar/scenarios.csv](../../Examples/MarketRisk/Input/HistSimVar/scenarios.csv)
- **Tenor Mapping:** [Examples/MarketRisk/Input/HistSimVar/simulation.xml](../../Examples/MarketRisk/Input/HistSimVar/simulation.xml:10)
- **VaR Configuration:** [Examples/MarketRisk/Input/ore_histsimvar.xml](../../Examples/MarketRisk/Input/ore_histsimvar.xml)

---

## Further Reading

For the complete implementation flow, see:
- [ORE VaR Implementation Documentation](ORE_VaR_Implementation.md)
- [ORE User Guide](../userguide.pdf) - Section on Historical Simulation

---

**Document Version:** 1.0
**Last Updated:** 2025-11-09
