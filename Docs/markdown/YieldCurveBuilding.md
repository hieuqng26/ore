# How ORE Builds Yield Curves

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture & Components](#architecture--components)
3. [Configuration Files](#configuration-files)
4. [Curve Types & Segments](#curve-types--segments)
5. [The Building Process](#the-building-process)
6. [Interpolation Methods](#interpolation-methods)
7. [Advanced Topics](#advanced-topics)
8. [Practical Examples](#practical-examples)
9. [Code References](#code-references)
10. [Troubleshooting](#troubleshooting)

---

## Introduction

### What are Yield Curves?

In ORE (Open Source Risk Engine), yield curves are fundamental building blocks for pricing interest rate derivatives and performing risk analytics. A yield curve represents the relationship between interest rates (or discount factors) and time to maturity.

### The Multi-Curve Framework

ORE implements a **multi-curve framework** to reflect the post-2008 financial crisis reality where:
- **Discount curves** (e.g., OIS curves) are used for present value calculations
- **Forwarding curves** (e.g., LIBOR/EURIBOR curves) are used to project future index fixings
- These curves differ due to credit and liquidity spreads

### Key Capabilities

ORE's yield curve building system supports:
- **Multiple curve types**: Discount, zero, forwarding, cross-currency, tenor basis
- **Diverse instruments**: Deposits, FRAs, futures, swaps, OIS, basis swaps
- **Flexible interpolation**: 20+ interpolation methods including LogLinear, Cubic, ConvexMonotone
- **Advanced bootstrapping**: Handles circular dependencies, segment priorities, and multi-curve simultaneous solving
- **QuantLib integration**: Built on QuantLib's robust term structure framework with QuantExt extensions

---

## Architecture & Components

### Overview

The yield curve building architecture consists of four main layers:

```
┌─────────────────────────────────────────────────────────┐
│          Configuration Layer (XML Parsing)              │
│  YieldCurveConfig, Conventions, TodaysMarketParameters  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          Market Data Layer (Data Loading)               │
│         Loader, CSVLoader, MarketDataLoader             │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          Building Layer (Curve Construction)            │
│       TodaysMarket, YieldCurve, YieldCurveBuilder       │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│          QuantLib/QuantExt Foundation                   │
│   RateHelpers, PiecewiseYieldCurve, Interpolations      │
└─────────────────────────────────────────────────────────┘
```

### Core Classes

#### 1. YieldCurveConfig

**Location**: [OREData/ored/configuration/yieldcurveconfig.hpp](../OREData/ored/configuration/yieldcurveconfig.hpp)

The `YieldCurveConfig` class represents the parsed configuration from `curveconfig.xml`. It contains:

- **Curve identification**: Currency, curve ID, description
- **Discount curve reference**: Which curve to use for discounting
- **Segments**: Vector of `YieldCurveSegment` objects defining curve instruments
- **Interpolation settings**:
  - `InterpolationVariable`: Zero, Discount, or Forward
  - `InterpolationMethod`: LogLinear, Cubic, ConvexMonotone, etc.
- **Bootstrap configuration**: Tolerance, accuracy, max attempts
- **Day counter and extrapolation**: Day count convention and extrapolation flag

**Key segment types**:
- `DirectYieldCurveSegment`: For Zero and Discount quotes
- `SimpleYieldCurveSegment`: For Deposits, FRAs, Futures, OIS, Swaps
- `AverageOISYieldCurveSegment`: For composite OIS curves
- `TenorBasisYieldCurveSegment`: For tenor basis swaps
- `CrossCcyYieldCurveSegment`: For cross-currency basis swaps
- `ZeroSpreadedYieldCurveSegment`: For spread curves

#### 2. YieldCurve

**Location**: [OREData/ored/marketdata/yieldcurve.hpp](../OREData/ored/marketdata/yieldcurve.hpp) and [yieldcurve.cpp](../OREData/ored/marketdata/yieldcurve.cpp)

The `YieldCurve` class is the curve builder that:

1. Takes configuration and market data as input
2. Creates QuantLib `RateHelper` objects for each instrument
3. Instantiates a `PiecewiseYieldCurve` with appropriate template parameters
4. Performs bootstrapping to solve for the curve
5. Returns a `Handle<YieldTermStructure>`

**Key methods**:
- `buildBootstrappedCurve()`: Main bootstrapping logic for instrument-based curves
- `buildZeroCurve()`, `buildDiscountCurve()`: Direct curve building from quotes
- `buildZeroSpreadedCurve()`, `buildDiscountRatioCurve()`: Derived curves
- `addDeposits()`, `addFras()`, `addFutures()`, `addOISs()`, `addSwaps()`: Add rate helpers for each instrument type
- `buildPiecewiseCurve()`: Template instantiation of QuantLib curve with chosen interpolation
- `flattenPiecewiseCurve()`: Convert piecewise curve to detached interpolated curve

#### 3. TodaysMarket

**Location**: [OREData/ored/marketdata/todaysmarket.hpp](../OREData/ored/marketdata/todaysmarket.hpp) and [todaysmarket.cpp](../OREData/ored/marketdata/todaysmarket.cpp)

`TodaysMarket` orchestrates the entire market building process:

**Constructor responsibilities**:
1. Load historical fixings and dividends
2. Build FX triangulation from FX spot quotes
3. Parse all configurations to build dependency graph
4. Topologically sort dependencies to determine build order
5. Build curves sequentially (or simultaneously for circular dependencies)
6. Handle errors and provide diagnostics

**Key features**:
- **Lazy building**: Optional lazy evaluation of market objects
- **Error handling**: Continue-on-error mode for partial market builds
- **Calibration info**: Optional storage of calibration instruments and results
- **Quote linkage**: Preserve links to live market quotes for sensitivity calculations

#### 4. Loader Interface

**Location**: [OREData/ored/marketdata/loader.hpp](../OREData/ored/marketdata/loader.hpp)

Abstract interface for loading market data. Key implementations:

- **CSVLoader** ([csvloader.hpp](../OREData/ored/marketdata/csvloader.hpp)): Loads from CSV/TXT files
- **InMemoryLoader**: Stores quotes in memory
- **BinaryLoader**: Loads from binary format for performance

**Loader capabilities**:
- `loadQuotes(date)`: Load all quotes for a specific date
- `get(quoteName, date)`: Get a specific quote
- `get(wildcard, date)`: Get quotes matching a pattern
- `loadFixings()`: Load historical index fixings
- `has()`, `hasQuotes()`: Check quote existence

---

## Configuration Files

### 1. curveconfig.xml

The main curve configuration file defines how each curve should be built.

#### Basic Structure

```xml
<CurveConfiguration>
  <YieldCurves>
    <YieldCurve>
      <CurveId>EUR1D</CurveId>
      <CurveDescription>EUR discount curve bootstrapped from EONIA</CurveDescription>
      <Currency>EUR</Currency>
      <DiscountCurve>EUR1D</DiscountCurve>
      <Segments>
        <!-- Curve segments go here -->
      </Segments>
      <InterpolationVariable>Discount</InterpolationVariable>
      <InterpolationMethod>LogLinear</InterpolationMethod>
      <YieldCurveDayCounter>A365</YieldCurveDayCounter>
      <Tolerance>0.000000000001</Tolerance>
      <Extrapolation>true</Extrapolation>
    </YieldCurve>
  </YieldCurves>
</CurveConfiguration>
```

#### Key Elements

- **CurveId**: Unique identifier for the curve
- **Currency**: Currency denomination
- **DiscountCurve**: Which curve to use for discounting cash flows (can be self-referencing)
- **Segments**: Ordered list of instrument segments
- **InterpolationVariable**: What to interpolate (Discount, Zero, or Forward)
- **InterpolationMethod**: How to interpolate (LogLinear, Cubic, etc.)
- **YieldCurveDayCounter**: Day count convention for zero rates
- **Tolerance**: Bootstrap tolerance
- **Extrapolation**: Enable/disable extrapolation beyond last pillar

#### Simple Segment Example (Deposits)

```xml
<Simple>
  <Type>Deposit</Type>
  <Quotes>
    <Quote>MM/RATE/EUR/0D/1D</Quote>
  </Quotes>
  <Conventions>EUR-EONIA-CONVENTIONS</Conventions>
</Simple>
```

#### Simple Segment Example (OIS)

```xml
<Simple>
  <Type>OIS</Type>
  <Quotes>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/1W</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/2W</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/1M</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/2M</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/3M</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/6M</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/1Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/2Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/3Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/4Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/5Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/10Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/15Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/20Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/30Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/50Y</Quote>
  </Quotes>
  <Conventions>EUR-OIS-CONVENTIONS</Conventions>
</Simple>
```

#### Multi-Curve Example (Forwarding Curve)

For a EURIBOR-6M forwarding curve that uses EUR1D for discounting:

```xml
<YieldCurve>
  <CurveId>EUR6M</CurveId>
  <CurveDescription>EUR 6M forwarding curve</CurveDescription>
  <Currency>EUR</Currency>
  <DiscountCurve>EUR1D</DiscountCurve>  <!-- Uses OIS for discounting -->
  <Segments>
    <Simple>
      <Type>Deposit</Type>
      <Quotes>
        <Quote>MM/RATE/EUR/2D/6M</Quote>
      </Quotes>
      <Conventions>EUR-EURIBOR-CONVENTIONS</Conventions>
      <ProjectionCurve>EUR6M</ProjectionCurve>  <!-- Self-referencing -->
    </Simple>
    <Simple>
      <Type>Swap</Type>
      <Quotes>
        <Quote>IR_SWAP/RATE/EUR/2D/6M/1Y</Quote>
        <Quote>IR_SWAP/RATE/EUR/2D/6M/2Y</Quote>
        <Quote>IR_SWAP/RATE/EUR/2D/6M/3Y</Quote>
        <Quote>IR_SWAP/RATE/EUR/2D/6M/5Y</Quote>
        <Quote>IR_SWAP/RATE/EUR/2D/6M/10Y</Quote>
        <Quote>IR_SWAP/RATE/EUR/2D/6M/15Y</Quote>
        <Quote>IR_SWAP/RATE/EUR/2D/6M/20Y</Quote>
        <Quote>IR_SWAP/RATE/EUR/2D/6M/30Y</Quote>
      </Quotes>
      <Conventions>EUR-6M-SWAP-CONVENTIONS</Conventions>
      <ProjectionCurve>EUR6M</ProjectionCurve>
    </Simple>
  </Segments>
  <InterpolationVariable>Discount</InterpolationVariable>
  <InterpolationMethod>LogLinear</InterpolationMethod>
  <YieldCurveDayCounter>A365</YieldCurveDayCounter>
</YieldCurve>
```

#### Tenor Basis Segment Example

```xml
<TenorBasis>
  <Type>TenorBasis</Type>
  <Quotes>
    <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/2Y</Quote>
    <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/3Y</Quote>
    <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/5Y</Quote>
    <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/10Y</Quote>
  </Quotes>
  <Conventions>EUR-TENOR-BASIS-CONVENTIONS</Conventions>
  <ProjectionCurvePay>EUR3M</ProjectionCurvePay>
  <ProjectionCurveReceive>EUR6M</ProjectionCurveReceive>
</TenorBasis>
```

#### Cross-Currency Basis Segment Example

```xml
<CrossCcyBasis>
  <Type>CrossCcyBasis</Type>
  <Quotes>
    <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/2Y</Quote>
    <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/3Y</Quote>
    <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/5Y</Quote>
  </Quotes>
  <Conventions>EUR-USD-XCCY-BASIS</Conventions>
  <DiscountCurve>EUR1D</DiscountCurve>
  <SpotRate>FX/RATE/EUR/USD</SpotRate>
  <ForeignDiscountCurve>USD1D</ForeignDiscountCurve>
  <ProjectionCurveDomestic>EUR3M</ProjectionCurveDomestic>
  <ProjectionCurveForeign>USD3M</ProjectionCurveForeign>
</CrossCcyBasis>
```

#### Segment Priorities

When multiple segments overlap, use priorities:

```xml
<Segments>
  <Simple>
    <Type>Deposit</Type>
    <Quotes>...</Quotes>
    <Conventions>...</Conventions>
    <Priority>1</Priority>  <!-- Higher priority -->
  </Simple>
  <Simple>
    <Type>Swap</Type>
    <Quotes>...</Quotes>
    <Conventions>...</Conventions>
    <Priority>2</Priority>  <!-- Lower priority -->
    <MinDistance>1M</MinDistance>  <!-- Must be 1M away from priority 1 -->
  </Simple>
</Segments>
```

### 2. conventions.xml

Defines market conventions for each instrument type.

#### Deposit Conventions

```xml
<Deposit>
  <Id>EUR-EONIA-CONVENTIONS</Id>
  <IndexBased>true</IndexBased>
  <Index>EUR-EONIA</Index>
</Deposit>

<Deposit>
  <Id>USD-DEPOSIT-CONVENTIONS</Id>
  <IndexBased>false</IndexBased>
  <Calendar>US</Calendar>
  <Convention>ModifiedFollowing</Convention>
  <EOM>false</EOM>
  <DayCounter>ACT/360</DayCounter>
</Deposit>
```

#### OIS Conventions

```xml
<OIS>
  <Id>EUR-OIS-CONVENTIONS</Id>
  <SpotLag>2</SpotLag>
  <Index>EUR-EONIA</Index>
  <FixedDayCounter>A360</FixedDayCounter>
  <PaymentLag>1</PaymentLag>
  <EOM>false</EOM>
  <FixedFrequency>Annual</FixedFrequency>
  <FixedConvention>Following</FixedConvention>
  <FixedPaymentConvention>Following</FixedPaymentConvention>
  <Rule>Backward</Rule>
</OIS>
```

#### Swap Conventions

```xml
<Swap>
  <Id>EUR-6M-SWAP-CONVENTIONS</Id>
  <FixedCalendar>TARGET</FixedCalendar>
  <FixedFrequency>Annual</FixedFrequency>
  <FixedConvention>ModifiedFollowing</FixedConvention>
  <FixedDayCounter>30/360</FixedDayCounter>
  <Index>EUR-EURIBOR-6M</Index>
  <Spread>0.0</Spread>
</Swap>
```

#### FRA Conventions

```xml
<FRA>
  <Id>USD-FRA-CONVENTIONS</Id>
  <Index>USD-LIBOR-3M</Index>
</FRA>
```

#### Tenor Basis Conventions

```xml
<TenorBasisSwap>
  <Id>EUR-TENOR-BASIS-CONVENTIONS</Id>
  <Calendar>TARGET</Calendar>
  <LongFixedFrequency>Annual</LongFixedFrequency>
  <LongFixedConvention>ModifiedFollowing</LongFixedConvention>
  <LongFixedDayCounter>30/360</LongFixedDayCounter>
  <LongIndex>EUR-EURIBOR-6M</LongIndex>
  <ShortFixedFrequency>Semiannual</ShortFixedFrequency>
  <ShortFixedConvention>ModifiedFollowing</ShortFixedConvention>
  <ShortFixedDayCounter>30/360</ShortFixedDayCounter>
  <ShortIndex>EUR-EURIBOR-3M</ShortIndex>
  <LongMinusShort>true</LongMinusShort>
</TenorBasisSwap>
```

### 3. Market Data Files

Market data files provide the actual quote values.

#### CSV Format

```
# File: market.txt or marketdata.csv
# Format: Date QuoteID Value

20160205 MM/RATE/EUR/0D/1D 0.0002
20160205 IR_SWAP/RATE/EUR/2D/1D/1W 0.0002
20160205 IR_SWAP/RATE/EUR/2D/1D/2W 0.0002
20160205 IR_SWAP/RATE/EUR/2D/1D/1M 0.0002
20160205 IR_SWAP/RATE/EUR/2D/1D/2M 0.0002
20160205 IR_SWAP/RATE/EUR/2D/1D/3M 0.0002
20160205 IR_SWAP/RATE/EUR/2D/1D/6M 0.0003
20160205 IR_SWAP/RATE/EUR/2D/1D/1Y 0.0004
20160205 IR_SWAP/RATE/EUR/2D/1D/2Y 0.0005
20160205 IR_SWAP/RATE/EUR/2D/1D/3Y 0.0007
20160205 IR_SWAP/RATE/EUR/2D/1D/5Y 0.0012
20160205 IR_SWAP/RATE/EUR/2D/1D/10Y 0.0020
20160205 IR_SWAP/RATE/EUR/2D/1D/20Y 0.0025
20160205 IR_SWAP/RATE/EUR/2D/1D/30Y 0.0026
```

#### Quote Naming Conventions

**Deposit quotes**:
- Format: `MM/RATE/{CCY}/{SpotLag}/{Tenor}`
- Example: `MM/RATE/EUR/0D/1D` (EONIA overnight)
- Example: `MM/RATE/USD/2D/3M` (3-month USD deposit)

**OIS quotes**:
- Format: `IR_SWAP/RATE/{CCY}/{SpotLag}/{IndexTenor}/{SwapTenor}`
- Example: `IR_SWAP/RATE/EUR/2D/1D/5Y` (5Y EONIA OIS)
- Example: `IR_SWAP/RATE/USD/2D/1D/10Y` (10Y SOFR OIS)

**Swap quotes**:
- Format: `IR_SWAP/RATE/{CCY}/{SpotLag}/{IndexTenor}/{SwapTenor}`
- Example: `IR_SWAP/RATE/EUR/2D/6M/10Y` (10Y EURIBOR-6M swap)
- Example: `IR_SWAP/RATE/USD/2D/3M/5Y` (5Y LIBOR-3M swap)

**FRA quotes**:
- Format: `FRA/RATE/{CCY}/{FwdStart}/{Tenor}`
- Example: `FRA/RATE/EUR/3M/6M` (3x9 FRA)

**Futures quotes**:
- Format: `IR_FUTURE/PRICE/{CCY}/{Expiry}` or `OI_FUTURE/PRICE/{CCY}/{Expiry}/{Exchange}/{Tenor}`
- Example: `IR_FUTURE/PRICE/USD/2024-03-15`
- Example: `OI_FUTURE/PRICE/USD/2024-06-15/CME/3M`

**Tenor basis quotes**:
- Format: `BASIS_SWAP/BASIS_SPREAD/{CCY}/{SpotLag}/{LongTenor}/{ShortTenor}/{SwapTenor}`
- Example: `BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/5Y`

**Cross-currency basis quotes**:
- Format: `CC_BASIS/BASIS_SPREAD/{DomCCY}/{ForCCY}/{Tenor}/{SwapTenor}`
- Example: `CC_BASIS/BASIS_SPREAD/EUR/USD/3M/5Y`

---

## Curve Types & Segments

### Bootstrapped Curves

Bootstrapped curves are built from market instrument quotes using iterative solving.

#### 1. Deposit Segment

**Purpose**: Short-end of the curve (overnight to 1 year)

**Instruments**: Cash deposits, money market rates

**Configuration**:
```xml
<Simple>
  <Type>Deposit</Type>
  <Quotes>
    <Quote>MM/RATE/EUR/0D/1D</Quote>
    <Quote>MM/RATE/EUR/2D/1W</Quote>
    <Quote>MM/RATE/EUR/2D/1M</Quote>
    <Quote>MM/RATE/EUR/2D/3M</Quote>
    <Quote>MM/RATE/EUR/2D/6M</Quote>
  </Quotes>
  <Conventions>EUR-DEPOSIT-CONVENTIONS</Conventions>
</Simple>
```

**Implementation**: Creates `DepositRateHelper` objects from QuantLib

#### 2. FRA Segment

**Purpose**: Forward rate agreements (typically 3 months to 2 years forward)

**Configuration**:
```xml
<Simple>
  <Type>FRA</Type>
  <Quotes>
    <Quote>FRA/RATE/USD/3M/6M</Quote>  <!-- 3x9 FRA -->
    <Quote>FRA/RATE/USD/6M/6M</Quote>  <!-- 6x12 FRA -->
  </Quotes>
  <Conventions>USD-FRA-CONVENTIONS</Conventions>
  <ProjectionCurve>USD3M</ProjectionCurve>
</Simple>
```

**Implementation**: Creates `FraRateHelper` objects

#### 3. Future Segment

**Purpose**: Short-term interest rate futures or overnight index futures

**Configuration**:
```xml
<Simple>
  <Type>Future</Type>
  <Quotes>
    <Quote>IR_FUTURE/PRICE/USD/2024-03-15</Quote>
    <Quote>IR_FUTURE/PRICE/USD/2024-06-15</Quote>
    <Quote>IR_FUTURE/PRICE/USD/2024-09-15</Quote>
  </Quotes>
  <Conventions>USD-FUTURE-CONVENTIONS</Conventions>
  <ProjectionCurve>USD3M</ProjectionCurve>
</Simple>
```

**Implementation**: Creates `FuturesRateHelper` or `OvernightIndexFutureRateHelper`

#### 4. OIS Segment

**Purpose**: Overnight indexed swaps (typically used for discount curves)

**Configuration**:
```xml
<Simple>
  <Type>OIS</Type>
  <Quotes>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/1Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/2Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/5Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/10Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/1D/30Y</Quote>
  </Quotes>
  <Conventions>EUR-OIS-CONVENTIONS</Conventions>
</Simple>
```

**Implementation**: Creates `OISRateHelper` objects

#### 5. Swap Segment

**Purpose**: Standard interest rate swaps (for forwarding curves)

**Configuration**:
```xml
<Simple>
  <Type>Swap</Type>
  <Quotes>
    <Quote>IR_SWAP/RATE/EUR/2D/6M/2Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/6M/3Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/6M/5Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/6M/10Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/6M/20Y</Quote>
    <Quote>IR_SWAP/RATE/EUR/2D/6M/30Y</Quote>
  </Quotes>
  <Conventions>EUR-6M-SWAP-CONVENTIONS</Conventions>
  <ProjectionCurve>EUR6M</ProjectionCurve>
</Simple>
```

**Implementation**: Creates `SwapRateHelper` objects

#### 6. AverageOIS Segment

**Purpose**: USD-style average overnight indexed swaps with composite quotes

**Configuration**:
```xml
<AverageOIS>
  <Type>AverageOIS</Type>
  <Quotes>
    <CompositeQuote>
      <SpreadQuote>BASIS_SWAP/BASIS_SPREAD/USD/2D/3M/1D/2Y</SpreadQuote>
      <RateQuote>IR_SWAP/RATE/USD/2D/3M/2Y</RateQuote>
    </CompositeQuote>
  </Quotes>
  <Conventions>USD-AVERAGE-OIS-CONVENTIONS</Conventions>
  <ProjectionCurve>USD3M</ProjectionCurve>
</AverageOIS>
```

**Implementation**: Creates `AverageOISRateHelper` from QuantExt

#### 7. TenorBasis Segment

**Purpose**: Basis swaps between different tenors of the same currency

**Configuration**:
```xml
<TenorBasis>
  <Type>TenorBasis</Type>
  <Quotes>
    <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/2Y</Quote>
    <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/5Y</Quote>
    <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/10Y</Quote>
  </Quotes>
  <Conventions>EUR-TENOR-BASIS-CONVENTIONS</Conventions>
  <ProjectionCurvePay>EUR3M</ProjectionCurvePay>
  <ProjectionCurveReceive>EUR6M</ProjectionCurveReceive>
</TenorBasis>
```

**Implementation**: Creates `TenorBasisSwapHelper` or `BasisTwoSwapHelper` from QuantExt

#### 8. CrossCcyBasis Segment

**Purpose**: Cross-currency basis swaps

**Configuration**:
```xml
<CrossCcyBasis>
  <Type>CrossCcyBasis</Type>
  <Quotes>
    <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/2Y</Quote>
    <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/5Y</Quote>
    <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/10Y</Quote>
  </Quotes>
  <Conventions>EUR-USD-XCCY-BASIS</Conventions>
  <DiscountCurve>EUR1D</DiscountCurve>
  <SpotRate>FX/RATE/EUR/USD</SpotRate>
  <ForeignDiscountCurve>USD1D</ForeignDiscountCurve>
  <ProjectionCurveDomestic>EUR3M</ProjectionCurveDomestic>
  <ProjectionCurveForeign>USD3M</ProjectionCurveForeign>
</CrossCcyBasis>
```

**Implementation**: Creates `CrossCcyBasisSwapHelper` or `CrossCcyFixFloatSwapHelper` from QuantExt

### Direct Curves

Direct curves are built from quotes without bootstrapping.

#### 1. Zero Curve

**Purpose**: Direct interpolation on zero rates

**Configuration**:
```xml
<YieldCurve>
  <CurveId>USD-ZERO</CurveId>
  <Currency>USD</Currency>
  <DiscountCurve/>
  <Segments>
    <Direct>
      <Type>Zero</Type>
      <Quotes>
        <Quote>ZERO/RATE/USD/1Y</Quote>
        <Quote>ZERO/RATE/USD/2Y</Quote>
        <Quote>ZERO/RATE/USD/5Y</Quote>
        <Quote>ZERO/RATE/USD/10Y</Quote>
      </Quotes>
    </Direct>
  </Segments>
  <InterpolationVariable>Zero</InterpolationVariable>
  <InterpolationMethod>Linear</InterpolationMethod>
</YieldCurve>
```

#### 2. Discount Curve

**Purpose**: Direct interpolation on discount factors

**Configuration**:
```xml
<Direct>
  <Type>Discount</Type>
  <Quotes>
    <Quote>DISCOUNT/RATE/EUR/1Y</Quote>
    <Quote>DISCOUNT/RATE/EUR/2Y</Quote>
    <Quote>DISCOUNT/RATE/EUR/5Y</Quote>
  </Quotes>
</Direct>
```

#### 3. ZeroSpread Curve

**Purpose**: Add zero spreads to a reference curve

**Configuration**:
```xml
<ZeroSpread>
  <Type>ZeroSpread</Type>
  <Quotes>
    <Quote>ZERO_SPREAD/SPREAD/EUR/1Y</Quote>
    <Quote>ZERO_SPREAD/SPREAD/EUR/5Y</Quote>
    <Quote>ZERO_SPREAD/SPREAD/EUR/10Y</Quote>
  </Quotes>
  <ReferenceCurve>EUR-BENCHMARK</ReferenceCurve>
</ZeroSpread>
```

**Implementation**: Uses `PiecewiseZeroSpreadedTermStructure` from QuantLib

#### 4. DiscountRatio Curve

**Purpose**: Build curve from ratio of other curves

**Formula**: `DF(t) = baseCurve(t) * numeratorCurve(t) / denominatorCurve(t)`

**Configuration**:
```xml
<YieldCurve>
  <CurveId>EUR-IMPLIED</CurveId>
  <Currency>EUR</Currency>
  <DiscountCurve/>
  <DiscountRatio>
    <BaseCurve>EUR-OIS</BaseCurve>
    <NumeratorCurve>EUR-GOVBOND</NumeratorCurve>
    <DenominatorCurve>EUR-BENCHMARK</DenominatorCurve>
  </DiscountRatio>
</YieldCurve>
```

**Implementation**: Uses `DiscountRatioModifiedCurve` from QuantExt

#### 5. FittedBond Curve

**Purpose**: Fit parametric curve to bond prices

**Configuration**:
```xml
<YieldCurve>
  <CurveId>USD-GOVBOND</CurveId>
  <Currency>USD</Currency>
  <DiscountCurve>USD1D</DiscountCurve>
  <FittedBond>
    <BondBasket>
      <Security>BOND_US912828A</Security>
      <Security>BOND_US912828B</Security>
      <Security>BOND_US912828C</Security>
    </BondBasket>
    <FittingMethod>ExponentialSplines</FittingMethod>
    <!-- Other options: NelsonSiegel, Svensson, SimplePolynomial -->
  </FittedBond>
</YieldCurve>
```

**Fitting methods**:
- ExponentialSplines
- NelsonSiegel
- Svensson
- SimplePolynomial

#### 6. WeightedAverage Curve

**Purpose**: Weighted combination of two curves

**Formula**: `DF(t) = weight1 * DF1(t) + weight2 * DF2(t)`

**Configuration**:
```xml
<YieldCurve>
  <CurveId>EUR-BLENDED</CurveId>
  <Currency>EUR</Currency>
  <DiscountCurve/>
  <WeightedAverage>
    <Curve1>EUR-OIS</Curve1>
    <Curve2>EUR-GOVBOND</Curve2>
    <Weight1>0.7</Weight1>
    <Weight2>0.3</Weight2>
  </WeightedAverage>
</YieldCurve>
```

#### 7. IborFallback Curve

**Purpose**: IBOR transition to RFR with fallback spread

**Formula**: OIS curve + fallback spread

**Configuration**:
```xml
<YieldCurve>
  <CurveId>USD-LIBOR-FALLBACK</CurveId>
  <Currency>USD</Currency>
  <DiscountCurve/>
  <IborFallback>
    <RfrCurve>USD-SOFR</RfrCurve>
    <RfrIndex>USD-SOFR</RfrIndex>
    <IborIndex>USD-LIBOR-3M</IborIndex>
    <Spread>0.00266</Spread>  <!-- ARRC fallback spread -->
  </IborFallback>
</YieldCurve>
```

#### 8. BondYieldShifted Curve

**Purpose**: Shift bond yield curve by a constant or term-structured spread

**Configuration**:
```xml
<YieldCurve>
  <CurveId>EUR-BOND-SHIFTED</CurveId>
  <Currency>EUR</Currency>
  <DiscountCurve/>
  <BondYieldShifted>
    <ReferenceCurve>EUR-GOVBOND</ReferenceCurve>
    <ShiftQuotes>
      <Quote>SHIFT/SPREAD/EUR/1Y</Quote>
      <Quote>SHIFT/SPREAD/EUR/5Y</Quote>
      <Quote>SHIFT/SPREAD/EUR/10Y</Quote>
    </ShiftQuotes>
  </BondYieldShifted>
</YieldCurve>
```

---

## The Building Process

### Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                  USER CONFIGURATION                         │
├─────────────────────────────────────────────────────────────┤
│ curveconfig.xml      conventions.xml      market.txt/csv    │
│ - CurveId            - Deposit            - Date            │
│ - Currency           - OIS                - QuoteID         │
│ - Segments           - Swap               - Value           │
│ - Interpolation      - FRA, Future, etc.                    │
└────────────┬────────────────────┬──────────────┬────────────┘
             │                    │              │
             ▼                    ▼              ▼
┌────────────────────┐  ┌─────────────────┐  ┌──────────────┐
│ YieldCurveConfig   │  │  Conventions    │  │  CSVLoader   │
│  ::fromXML()       │  │  ::fromXML()    │  │  (Loader)    │
└────────┬───────────┘  └────────┬────────┘  └──────┬───────┘
         │                       │                   │
         └───────────────────────┴───────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   TodaysMarket         │
                    │   Constructor          │
                    │  - Load fixings        │
                    │  - Build FX            │
                    │  - Build dep graph     │
                    │  - Topological sort    │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │   YieldCurve           │
                    │   Constructor          │
                    └───────────┬────────────┘
                                │
         ┌──────────────────────┴──────────────────────┐
         │                                             │
         ▼                                             ▼
┌────────────────────┐                    ┌────────────────────┐
│ Direct Curves      │                    │ Bootstrapped       │
│ - buildZeroCurve   │                    │ Curves             │
│ - buildDiscount    │                    └─────────┬──────────┘
│ - buildZeroSpread  │                              │
│ - buildDiscountRatio│                             ▼
│ - buildFittedBond  │              ┌────────────────────────────┐
│ - buildWeighted    │              │ buildBootstrappedCurve()   │
└────────┬───────────┘              │  1. For each segment:      │
         │                          │     - addDeposits()        │
         │                          │     - addFras()            │
         │                          │     - addFutures()         │
         │                          │     - addOISs()            │
         │                          │     - addSwaps()           │
         │                          │     - addTenorBasis()      │
         │                          │     - addCrossCcy()        │
         │                          │  2. Remove duplicates      │
         │                          │  3. Apply priorities       │
         │                          │  4. Sort instruments       │
         │                          └───────────┬────────────────┘
         │                                      │
         │                                      ▼
         │                          ┌────────────────────────────┐
         │                          │ buildPiecewiseCurve()      │
         │                          │  - Create RateHelpers      │
         │                          │  - Instantiate             │
         │                          │    PiecewiseYieldCurve<>   │
         │                          │  - Apply interpolation     │
         │                          │    (LogLinear, Cubic, etc) │
         │                          │  - Bootstrap               │
         │                          │    (Iterative/Global)      │
         │                          └───────────┬────────────────┘
         │                                      │
         └──────────────────┬───────────────────┘
                            │
                            ▼
              ┌─────────────────────────────┐
              │ flattenPiecewiseCurve()     │
              │  - Convert to               │
              │    InterpolatedZeroCurve or │
              │    InterpolatedDiscountCurve│
              │  - Detach from quotes       │
              └──────────────┬──────────────┘
                             │
                             ▼
              ┌─────────────────────────────┐
              │  Handle<YieldTermStructure> │
              │  - Enable extrapolation     │
              │  - Build calibration info   │
              │  - Store in TodaysMarket    │
              └─────────────────────────────┘
```

### Step-by-Step Process

#### Step 1: Configuration Parsing

**File**: [OREData/ored/configuration/yieldcurveconfig.cpp](../OREData/ored/configuration/yieldcurveconfig.cpp)

The `YieldCurveConfig::fromXML()` method parses the XML configuration:

```cpp
// Pseudo-code
void YieldCurveConfig::fromXML(XMLNode* node) {
    curveID_ = XMLUtils::getChildValue(node, "CurveId");
    currency_ = XMLUtils::getChildValue(node, "Currency");
    discountCurveID_ = XMLUtils::getChildValue(node, "DiscountCurve");

    // Parse segments
    XMLNode* segmentsNode = XMLUtils::getChildNode(node, "Segments");
    for (XMLNode* child : XMLUtils::getChildrenNodes(segmentsNode)) {
        if (child->name() == "Simple")
            segments_.push_back(parseSimpleSegment(child));
        else if (child->name() == "TenorBasis")
            segments_.push_back(parseTenorBasisSegment(child));
        // ... etc
    }

    // Parse interpolation settings
    interpolationVariable_ = parseInterpolationVariable(
        XMLUtils::getChildValue(node, "InterpolationVariable"));
    interpolationMethod_ = parseInterpolationMethod(
        XMLUtils::getChildValue(node, "InterpolationMethod"));
}
```

#### Step 2: Market Data Loading

**File**: [OREData/ored/marketdata/csvloader.cpp](../OREData/ored/marketdata/csvloader.cpp)

The `CSVLoader` reads market data files:

```cpp
// Pseudo-code
void CSVLoader::loadFile(const string& filename) {
    ifstream file(filename);
    string line;
    while (getline(file, line)) {
        if (line[0] == '#') continue;  // Skip comments

        vector<string> tokens = split(line);
        Date date = parseDate(tokens[0]);
        string quoteName = tokens[1];
        Real value = parseReal(tokens[2]);

        auto quote = make_shared<SimpleQuote>(value);
        data_[make_pair(quoteName, date)] = quote;
    }
}
```

#### Step 3: Dependency Graph Building

**File**: [OREData/ored/marketdata/todaysmarket.cpp](../OREData/ored/marketdata/todaysmarket.cpp:148-194)

`TodaysMarket` builds a dependency graph:

```cpp
// Pseudo-code
void TodaysMarket::buildDependencyGraph() {
    DependencyGraph graph;

    // Add all curves as nodes
    for (auto& config : curveConfigs) {
        graph.addNode(config->curveID());
    }

    // Add edges for dependencies
    for (auto& config : curveConfigs) {
        // Discount curve dependency
        if (!config->discountCurveID().empty())
            graph.addEdge(config->curveID(), config->discountCurveID());

        // Projection curve dependencies
        for (auto& segment : config->segments()) {
            if (segment->projectionCurve())
                graph.addEdge(config->curveID(), segment->projectionCurve());
        }

        // Reference curve dependencies
        if (config->referenceCurve())
            graph.addEdge(config->curveID(), config->referenceCurve());
    }

    // Topologically sort
    buildOrder_ = graph.topologicalSort();
}
```

#### Step 4: Curve Construction

**File**: [OREData/ored/marketdata/yieldcurve.cpp](../OREData/ored/marketdata/yieldcurve.cpp)

The `YieldCurve` constructor initiates building:

```cpp
YieldCurve::YieldCurve(
    Date asof,
    YieldCurveSpec spec,
    CurveConfigurations& curveConfigs,
    Loader& loader,
    map<string, Handle<YieldTermStructure>>& requiredCurves,
    const FXTriangulation& fxSpots,
    const ReferenceDataManager& referenceData) {

    // Get configuration
    auto config = curveConfigs.yieldCurveConfig(spec.curveConfigID());

    // Determine curve type and build
    if (config->type() == YieldCurveConfig::Type::Discount ||
        config->type() == YieldCurveConfig::Type::Yield) {
        buildBootstrappedCurve(config, loader, requiredCurves);
    } else if (config->type() == YieldCurveConfig::Type::DiscountRatio) {
        buildDiscountRatioCurve(config, requiredCurves);
    } else if (config->type() == YieldCurveConfig::Type::ZeroSpread) {
        buildZeroSpreadedCurve(config, loader, requiredCurves);
    }
    // ... etc
}
```

#### Step 5: Building Bootstrapped Curves

**File**: [OREData/ored/marketdata/yieldcurve.cpp:1210-1402](../OREData/ored/marketdata/yieldcurve.cpp)

The `buildBootstrappedCurve()` method:

```cpp
// Pseudo-code (simplified)
void YieldCurve::buildBootstrappedCurve(...) {
    vector<shared_ptr<RateHelper>> instruments;

    // Step 1: Build instrument sets per segment
    for (auto& segment : config->segments()) {
        switch (segment->type()) {
            case YieldCurveSegment::Type::Deposit:
                addDeposits(segment, instruments);
                break;
            case YieldCurveSegment::Type::FRA:
                addFras(segment, instruments);
                break;
            case YieldCurveSegment::Type::Future:
                addFutures(segment, instruments);
                break;
            case YieldCurveSegment::Type::OIS:
                addOISs(segment, instruments);
                break;
            case YieldCurveSegment::Type::Swap:
                addSwaps(segment, instruments);
                break;
            case YieldCurveSegment::Type::TenorBasis:
                addTenorBasisSwaps(segment, instruments);
                break;
            case YieldCurveSegment::Type::CrossCcyBasis:
                addCrossCcyBasisSwaps(segment, instruments);
                break;
            // ... etc
        }
    }

    // Step 2: Remove duplicate pillar dates
    removeDuplicates(instruments);

    // Step 3: Apply segment priorities
    applyPriorities(instruments, config->segments());

    // Step 4: Sort instruments by pillar date
    sort(instruments.begin(), instruments.end(),
         [](auto& a, auto& b) { return a->pillarDate() < b->pillarDate(); });

    // Step 5: Build piecewise curve
    auto [yieldts, contributions] = buildPiecewiseCurve(instruments);

    // Step 6: Flatten curve (detach from quotes)
    curve_ = flattenPiecewiseCurve(yieldts);
}
```

#### Step 6: Adding Rate Helpers (Example: Deposits)

**File**: [OREData/ored/marketdata/yieldcurve.cpp:1771-1841](../OREData/ored/marketdata/yieldcurve.cpp)

```cpp
void YieldCurve::addDeposits(
    shared_ptr<YieldCurveSegment> segment,
    vector<shared_ptr<RateHelper>>& instruments) {

    auto depositSegment = dynamic_pointer_cast<SimpleYieldCurveSegment>(segment);

    // Get deposit conventions
    auto conventions = InstrumentConventions::instance()
        .conventions()->get(segment->conventionsID());
    auto depositConvention = dynamic_pointer_cast<DepositConvention>(conventions);

    // Loop through quotes
    for (auto& quoteID : depositSegment->quotes()) {
        // Load quote from market data
        auto marketQuote = loader_.get(quoteID, asofDate_);
        auto depositQuote = dynamic_pointer_cast<MoneyMarketQuote>(marketQuote);

        Period term = depositQuote->term();
        Natural fwdStart = depositQuote->fwdStart();

        // Create rate helper
        shared_ptr<RateHelper> helper;
        if (depositConvention->indexBased()) {
            // Index-based deposit (e.g., EONIA, FedFunds)
            auto index = parseIborIndex(depositConvention->index());
            helper = make_shared<DepositRateHelper>(
                depositQuote->quote(),
                term,
                fwdStart,
                index->fixingCalendar(),
                index->businessDayConvention(),
                index->endOfMonth(),
                index->dayCounter()
            );
        } else {
            // Explicit convention deposit
            helper = make_shared<DepositRateHelper>(
                depositQuote->quote(),
                term,
                fwdStart,
                depositConvention->calendar(),
                depositConvention->convention(),
                depositConvention->eom(),
                depositConvention->dayCounter()
            );
        }

        instruments.push_back(helper);
    }
}
```

#### Step 7: Building Piecewise Curve

**File**: [OREData/ored/marketdata/yieldcurve.cpp:546-792](../OREData/ored/marketdata/yieldcurve.cpp)

```cpp
// Heavily simplified pseudo-code
pair<Handle<YieldTermStructure>, vector<Contribution>>
YieldCurve::buildPiecewiseCurve(
    const vector<shared_ptr<RateHelper>>& instruments) {

    shared_ptr<YieldTermStructure> yieldts;

    // Select interpolation based on configuration
    if (interpolationVariable_ == InterpolationVariable::Discount) {
        if (interpolationMethod_ == InterpolationMethod::LogLinear) {
            // Instantiate PiecewiseYieldCurve<Discount, LogLinear>
            yieldts = make_shared<
                PiecewiseYieldCurve<Discount, LogLinear, IterativeBootstrap>>(
                    asofDate_,
                    instruments,
                    zeroDayCounter_,
                    LogLinear(),
                    accuracy_
                );
        } else if (interpolationMethod_ == InterpolationMethod::Linear) {
            yieldts = make_shared<
                PiecewiseYieldCurve<Discount, Linear, IterativeBootstrap>>(
                    asofDate_,
                    instruments,
                    zeroDayCounter_,
                    Linear(),
                    accuracy_
                );
        }
        // ... many more interpolation combinations
    } else if (interpolationVariable_ == InterpolationVariable::Zero) {
        // Similar logic for Zero interpolation
    } else if (interpolationVariable_ == InterpolationVariable::Forward) {
        // Similar logic for Forward interpolation
    }

    // Enable extrapolation if configured
    if (extrapolation_)
        yieldts->enableExtrapolation();

    return {Handle<YieldTermStructure>(yieldts), contributions};
}
```

#### Step 8: Flattening the Curve

**File**: [OREData/ored/marketdata/yieldcurve.cpp](../OREData/ored/marketdata/yieldcurve.cpp)

```cpp
// Pseudo-code
Handle<YieldTermStructure> YieldCurve::flattenPiecewiseCurve(
    Handle<YieldTermStructure> piecewise) {

    // Extract pillars and values from piecewise curve
    vector<Date> dates = piecewise->dates();
    vector<Real> values;

    if (interpolationVariable_ == InterpolationVariable::Discount) {
        for (auto& date : dates)
            values.push_back(piecewise->discount(date));

        // Create interpolated discount curve
        return make_shared<InterpolatedDiscountCurve>(
            dates, values, zeroDayCounter_, Calendar(), interpolation_);
    } else if (interpolationVariable_ == InterpolationVariable::Zero) {
        for (auto& date : dates) {
            Time t = zeroDayCounter_.yearFraction(asofDate_, date);
            values.push_back(piecewise->zeroRate(t, Continuous));
        }

        // Create interpolated zero curve
        return make_shared<InterpolatedZeroCurve>(
            dates, values, zeroDayCounter_, Calendar(), interpolation_);
    }
}
```

### Dependency Resolution Details

#### Circular Dependencies

When curves have circular dependencies (e.g., EUR3M and EUR6M both need each other for tenor basis), ORE uses **simultaneous multi-curve bootstrapping**:

```cpp
// Pseudo-code
if (hasCircularDependency(curve1, curve2)) {
    // Create both curves with iterative bootstrap
    auto helper1 = createRateHelpers(curve1Config);
    auto helper2 = createRateHelpers(curve2Config);

    // Create multi-curve bootstrap coordinator
    auto bootstrap = make_shared<MultiCurveBootstrap>(
        vector<vector<RateHelper>>{helper1, helper2},
        tolerance
    );

    // Bootstrap simultaneously
    bootstrap->calculate();
}
```

#### Topological Sorting

TodaysMarket performs topological sorting to determine the valid build order:

1. Create directed graph with curves as nodes
2. Add edges for all dependencies
3. Detect cycles (multi-curve groups)
4. Sort non-cyclic dependencies
5. Build curves in sorted order
6. Build multi-curve groups simultaneously

---

## Interpolation Methods

### Interpolation Variables

ORE supports three interpolation variables:

#### 1. Discount Factor Interpolation

**Most common choice** - Interpolates on discount factors `DF(t)`

```xml
<InterpolationVariable>Discount</InterpolationVariable>
```

**Advantages**:
- Guarantees positive discount factors (with appropriate method)
- Most intuitive for present value calculations
- Log-linear interpolation ensures positive forward rates

**Typical methods**: LogLinear, LogCubic, ConvexMonotone

#### 2. Zero Rate Interpolation

Interpolates on continuously compounded zero rates `r(t)`

```xml
<InterpolationVariable>Zero</InterpolationVariable>
```

**Relationship**: `DF(t) = exp(-r(t) * t)`

**Advantages**:
- Common in academic literature
- Simple linear interpolation acceptable

**Typical methods**: Linear, Cubic, CubicSpline

#### 3. Forward Rate Interpolation

Interpolates on instantaneous forward rates `f(t)`

```xml
<InterpolationVariable>Forward</InterpolationVariable>
```

**Relationship**: `DF(t) = exp(-∫[0,t] f(s) ds)`

**Advantages**:
- Direct control over forward curve shape
- Useful for specific modeling requirements

**Typical methods**: Linear, Cubic (can create negative discount factors if not careful)

### Interpolation Methods

ORE supports 20+ interpolation methods. Key methods:

#### LogLinear

**Configuration**: `<InterpolationMethod>LogLinear</InterpolationMethod>`

**Formula**: Linear interpolation on `log(DF(t))`

**Characteristics**:
- **Most popular method** for discount curve interpolation
- Guarantees positive discount factors
- Guarantees positive forward rates
- Continuous but not smooth (kinked forward curve)
- Very stable numerically

**Use cases**: Default choice for OIS discount curves

#### Linear

**Configuration**: `<InterpolationMethod>Linear</InterpolationMethod>`

**Formula**: `y = y1 + (y2-y1) * (x-x1)/(x2-x1)`

**Characteristics**:
- Simple linear interpolation
- Not smooth (kinked)
- May produce negative forward rates with discount interpolation
- Acceptable for zero rate interpolation

**Use cases**: Zero rate curves, simple applications

#### NaturalCubic

**Configuration**: `<InterpolationMethod>NaturalCubic</InterpolationMethod>`

**Formula**: Cubic spline with natural boundary conditions (second derivative = 0 at endpoints)

**Characteristics**:
- Smooth interpolation (continuous first and second derivatives)
- Can produce negative forward rates
- Stable and well-behaved

**Use cases**: When smoothness is important and negative rates are acceptable

#### FinancialCubic

**Configuration**: `<InterpolationMethod>FinancialCubic</InterpolationMethod>`

**Formula**: Cubic spline with financial boundary conditions

**Characteristics**:
- Smooth interpolation optimized for financial curves
- Better behaved than natural cubic for rate curves
- Can still produce negative forward rates

**Use cases**: Smooth yield curves where negative rates are monitored

#### ConvexMonotone

**Configuration**: `<InterpolationMethod>ConvexMonotone</InterpolationMethod>`

**Formula**: Hagan-West monotone convex interpolation

**Characteristics**:
- **Guarantees positive forward rates** when used with discount interpolation
- Maintains local monotonicity
- Produces smooth-looking curves
- More complex algorithm but very stable

**Use cases**: When positive forward rates are mandatory (e.g., option pricing models)

#### Hermite

**Configuration**: `<InterpolationMethod>Hermite</InterpolationMethod>`

**Formula**: Hermite interpolation (cubic with specified derivatives)

**Characteristics**:
- Smooth interpolation
- Local control (changing one point doesn't affect distant points)
- Can be configured for monotonicity

**Use cases**: When local control is desired

#### CubicSpline

**Configuration**: `<InterpolationMethod>CubicSpline</InterpolationMethod>`

**Formula**: Natural cubic spline

**Characteristics**:
- Very smooth
- Minimizes curvature
- Can oscillate between points

**Use cases**: Smooth curves, when oscillation is not a concern

#### LogCubic Variants

**Configuration**: `<InterpolationMethod>LogNaturalCubic</InterpolationMethod>`, `LogFinancialCubic`, `LogCubicSpline`

**Formula**: Cubic interpolation on `log(DF)` or `log(r)`

**Characteristics**:
- Combines smoothness of cubic with log guarantee of positivity
- Very popular for discount curves
- Ensures positive forward rates

**Use cases**: Smooth discount curves with guaranteed positivity

#### Mixed Methods

**Configuration**: `<InterpolationMethod>DefaultLogMixedLinearCubic</InterpolationMethod>`

**Formula**: Log-linear for short end, log-cubic for long end

**Characteristics**:
- Combines stability of linear with smoothness of cubic
- Cutoff configurable via `MixedInterpolationCutoff`
- Popular in practice

**Use cases**: When short-end stability and long-end smoothness both matter

**Example configuration**:
```xml
<InterpolationMethod>DefaultLogMixedLinearCubic</InterpolationMethod>
<MixedInterpolationCutoff>5Y</MixedInterpolationCutoff>
```

#### MonotonicLogCubicSpline

**Configuration**: `<InterpolationMethod>MonotonicLogCubicSpline</InterpolationMethod>`

**Characteristics**:
- Ensures monotonicity (no oscillations)
- Smooth cubic interpolation
- Stable and well-behaved

**Use cases**: When both smoothness and monotonicity are required

### Choosing an Interpolation Method

**Decision tree**:

1. **Do you need guaranteed positive forward rates?**
   - Yes → Use LogLinear, LogCubic variants, or ConvexMonotone
   - No → Consider Linear, Cubic variants

2. **Do you need smoothness (for sensitivities, Greeks)?**
   - Yes → Use Cubic, LogCubic, ConvexMonotone, Hermite
   - No → LogLinear or Linear is fine

3. **Is the curve for pricing or risk?**
   - Pricing → Prefer stable methods (LogLinear, ConvexMonotone)
   - Risk (sensitivity calculations) → Prefer smooth methods (LogCubic)

4. **What is market practice?**
   - OIS discount curves → LogLinear or LogCubic
   - Government bond curves → Cubic or CubicSpline
   - Credit curves → LogLinear

**Common combinations**:
- **Conservative**: `Discount` + `LogLinear` (most common)
- **Smooth**: `Discount` + `LogNaturalCubic`
- **Guaranteed positive**: `Discount` + `ConvexMonotone`
- **Academic**: `Zero` + `Linear`
- **Hybrid**: `Discount` + `DefaultLogMixedLinearCubic`

---

## Advanced Topics

### 1. Segment Priorities

When multiple segments have overlapping tenors, priorities control which instruments are used.

**Configuration**:
```xml
<Segments>
  <Simple>
    <Type>Swap</Type>
    <Quotes>...</Quotes>
    <Conventions>...</Conventions>
    <Priority>1</Priority>  <!-- Higher priority (built first) -->
  </Simple>
  <Simple>
    <Type>Swap</Type>
    <Quotes>...</Quotes>
    <Conventions>...</Conventions>
    <Priority>2</Priority>  <!-- Lower priority -->
    <MinDistance>1M</MinDistance>  <!-- Must be 1M away from priority 1 -->
  </Simple>
</Segments>
```

**Algorithm** (simplified):
1. Build rate helpers for all segments
2. Group helpers by segment priority
3. For each priority level (low to high):
   - Check if helper's pillar date is within `MinDistance` of higher priority pillar
   - If yes, remove this helper
   - If no, keep this helper

**Use case**: Combine liquid (on-the-run) and illiquid (off-the-run) instruments

**Example**: Use most liquid swap tenors (1Y, 2Y, 5Y, 10Y, 30Y) with priority 1, fill gaps with less liquid tenors (3Y, 4Y, 7Y, 15Y) with priority 2.

### 2. Bootstrap Configuration

**Configuration**:
```xml
<BootstrapConfig>
  <Accuracy>1.0e-12</Accuracy>
  <GlobalAccuracy>1.0e-10</GlobalAccuracy>
  <DontThrow>true</DontThrow>
  <MaxAttempts>100</MaxAttempts>
  <MaxFactor>2.0</MaxFactor>
  <MinFactor>2.0</MinFactor>
  <DontThrowSteps>10</DontThrowSteps>
  <Global>false</Global>
</BootstrapConfig>
```

**Parameters**:
- **Accuracy**: Target accuracy for iterative bootstrap (default: 1.0e-12)
- **GlobalAccuracy**: Target accuracy for global bootstrap
- **DontThrow**: Continue if bootstrap fails for some instruments
- **MaxAttempts**: Maximum iterations before giving up
- **MaxFactor**, **MinFactor**: Bounds for adjustment factors
- **DontThrowSteps**: Number of steps before giving up
- **Global**: Use `GlobalBootstrap` instead of `IterativeBootstrap`

**Bootstrap Algorithms**:

1. **IterativeBootstrap** (default, from QuantExt):
   - Bootstraps pillar by pillar sequentially
   - More robust than QuantLib's default
   - Handles most cases well
   - Faster than global

2. **GlobalBootstrap** (from QuantLib):
   - Solves all pillars simultaneously using multi-dimensional root finding
   - More stable for problematic curves
   - Slower than iterative
   - Can handle pathological cases

**When to use Global**:
- Curve fails with iterative bootstrap
- Instruments are very sensitive to each other
- Unusual curve shapes (inverted, humped)

### 3. Duplicate Pillar Handling

Within a segment, if two instruments have the same pillar date, ORE removes the earlier one (assumes later quote is more relevant).

**Example**:
```xml
<Quotes>
  <Quote>IR_SWAP/RATE/EUR/2D/6M/5Y</Quote>  <!-- Pillar: 5Y -->
  <Quote>IR_SWAP/RATE/EUR/2D/6M/60M</Quote>  <!-- Pillar: 5Y (duplicate) -->
</Quotes>
```

Second quote kept, first removed.

### 4. Multi-Curve Bootstrapping

When curves have circular dependencies, ORE uses simultaneous bootstrapping.

**Example**: EUR 3M/6M tenor basis

- EUR3M needs EUR6M for tenor basis instruments
- EUR6M needs EUR3M for tenor basis instruments

**Solution**:
1. Identify circular dependency
2. Create `MultiCurveBootstrap` coordinator
3. Provide all rate helpers for both curves
4. Solve simultaneously using Newton-Raphson

**Implementation**: Automatic - ORE detects circular dependencies and handles them.

### 5. Wildcard Quotes

Loader supports wildcard quote matching:

```cpp
// Get all EUR swap quotes
auto quotes = loader.get("IR_SWAP/RATE/EUR/2D/6M/*", asofDate);
```

**Use case**: Dynamically load all available tenors without hardcoding

### 6. Calibration Information

ORE can store calibration details for diagnostics:

**Configuration** (in TodaysMarket):
```cpp
auto market = make_shared<TodaysMarket>(
    asof, params, loader, curveConfigs,
    continueOnError, loadFixings, lazyBuild,
    referenceData, preserveQuoteLinkage,
    true  // buildCalibrationInfo = true
);
```

**Stored information**:
- Pillar dates
- Quote IDs used
- Instrument types
- Market quote values
- Calibrated curve values at pillars
- Calibration errors

**Access**:
```cpp
auto calibInfo = market->calibrationInfo();
for (auto& [curveID, info] : calibInfo) {
    for (size_t i = 0; i < info.pillarDates.size(); ++i) {
        cout << "Pillar: " << info.pillarDates[i]
             << ", Quote: " << info.quoteIDs[i]
             << ", Value: " << info.quoteValues[i]
             << ", Error: " << info.errors[i] << endl;
    }
}
```

### 7. Lazy Building

For large markets, building all curves upfront can be slow. Lazy building defers curve construction until needed.

**Configuration**:
```cpp
auto market = make_shared<TodaysMarket>(
    asof, params, loader, curveConfigs,
    continueOnError, loadFixings,
    true  // lazyBuild = true
);
```

**Behavior**:
- Curves not built in constructor
- Built on first access (e.g., `market->discountCurve("EUR")`)
- Dependencies built recursively
- Subsequent accesses use cached curve

**Use case**: Large multi-currency portfolios where only subset of markets needed

### 8. Error Handling

**Continue on Error**:
```cpp
auto market = make_shared<TodaysMarket>(
    asof, params, loader, curveConfigs,
    true  // continueOnError = true
);
```

- Catches exceptions during curve building
- Logs errors but continues with other curves
- Failed curves return null handles
- Useful for debugging partial market data

**Checking for failures**:
```cpp
auto curve = market->discountCurve("EUR");
if (curve.empty()) {
    cerr << "EUR discount curve failed to build" << endl;
}
```

### 9. Quote Linkage Preservation

For sensitivity calculations, ORE can preserve links to original market quotes:

**Configuration**:
```cpp
auto market = make_shared<TodaysMarket>(
    asof, params, loader, curveConfigs,
    continueOnError, loadFixings, lazyBuild, referenceData,
    true  // preserveQuoteLinkage = true
);
```

**Behavior**:
- Curves remain linked to `SimpleQuote` objects
- Changing quote values updates curve automatically
- Enables bump-and-revalue sensitivities
- Slightly higher memory usage

**Without linkage**:
- Curves flattened and detached from quotes
- More efficient for pricing-only workflows
- Sensitivities require full rebuild

---

## Practical Examples

### Example 1: Simple EUR OIS Discount Curve

**Goal**: Build EUR discount curve from EONIA overnight deposits and OIS swaps

#### curveconfig.xml
```xml
<YieldCurves>
  <YieldCurve>
    <CurveId>EUR-OIS</CurveId>
    <CurveDescription>EUR discount curve from EONIA</CurveDescription>
    <Currency>EUR</Currency>
    <DiscountCurve>EUR-OIS</DiscountCurve>
    <Segments>
      <!-- Short end: overnight deposit -->
      <Simple>
        <Type>Deposit</Type>
        <Quotes>
          <Quote>MM/RATE/EUR/0D/1D</Quote>
        </Quotes>
        <Conventions>EUR-EONIA-CONVENTIONS</Conventions>
      </Simple>
      <!-- Long end: OIS swaps -->
      <Simple>
        <Type>OIS</Type>
        <Quotes>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/1W</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/2W</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/1M</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/3M</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/6M</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/1Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/2Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/3Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/5Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/10Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/15Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/20Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/1D/30Y</Quote>
        </Quotes>
        <Conventions>EUR-OIS-CONVENTIONS</Conventions>
      </Simple>
    </Segments>
    <InterpolationVariable>Discount</InterpolationVariable>
    <InterpolationMethod>LogLinear</InterpolationMethod>
    <YieldCurveDayCounter>A365</YieldCurveDayCounter>
    <Tolerance>1.0e-12</Tolerance>
    <Extrapolation>true</Extrapolation>
  </YieldCurve>
</YieldCurves>
```

#### conventions.xml
```xml
<Conventions>
  <!-- EONIA deposit -->
  <Deposit>
    <Id>EUR-EONIA-CONVENTIONS</Id>
    <IndexBased>true</IndexBased>
    <Index>EUR-EONIA</Index>
  </Deposit>

  <!-- EONIA OIS -->
  <OIS>
    <Id>EUR-OIS-CONVENTIONS</Id>
    <SpotLag>2</SpotLag>
    <Index>EUR-EONIA</Index>
    <FixedDayCounter>A360</FixedDayCounter>
    <PaymentLag>1</PaymentLag>
    <EOM>false</EOM>
    <FixedFrequency>Annual</FixedFrequency>
    <FixedConvention>Following</FixedConvention>
    <FixedPaymentConvention>Following</FixedPaymentConvention>
    <Rule>Backward</Rule>
  </OIS>

  <!-- EONIA index -->
  <OvernightIndex>
    <Id>EUR-EONIA</Id>
    <FixingCalendar>TARGET</FixingCalendar>
    <DayCounter>A360</DayCounter>
    <SettlementDays>0</SettlementDays>
  </OvernightIndex>
</Conventions>
```

#### market.txt
```
20231115 MM/RATE/EUR/0D/1D 0.0390
20231115 IR_SWAP/RATE/EUR/2D/1D/1W 0.0390
20231115 IR_SWAP/RATE/EUR/2D/1D/2W 0.0390
20231115 IR_SWAP/RATE/EUR/2D/1D/1M 0.0390
20231115 IR_SWAP/RATE/EUR/2D/1D/3M 0.0388
20231115 IR_SWAP/RATE/EUR/2D/1D/6M 0.0382
20231115 IR_SWAP/RATE/EUR/2D/1D/1Y 0.0365
20231115 IR_SWAP/RATE/EUR/2D/1D/2Y 0.0320
20231115 IR_SWAP/RATE/EUR/2D/1D/3Y 0.0285
20231115 IR_SWAP/RATE/EUR/2D/1D/5Y 0.0255
20231115 IR_SWAP/RATE/EUR/2D/1D/10Y 0.0260
20231115 IR_SWAP/RATE/EUR/2D/1D/15Y 0.0275
20231115 IR_SWAP/RATE/EUR/2D/1D/20Y 0.0285
20231115 IR_SWAP/RATE/EUR/2D/1D/30Y 0.0290
```

### Example 2: Multi-Curve Setup (OIS + EURIBOR-6M)

**Goal**: Build EUR discount curve (OIS) and EUR 6M forwarding curve

#### curveconfig.xml
```xml
<YieldCurves>
  <!-- Discount curve (same as Example 1) -->
  <YieldCurve>
    <CurveId>EUR-OIS</CurveId>
    <!-- ... as above ... -->
  </YieldCurve>

  <!-- Forwarding curve for EURIBOR-6M -->
  <YieldCurve>
    <CurveId>EUR-EURIBOR-6M</CurveId>
    <CurveDescription>EUR 6M forwarding curve</CurveDescription>
    <Currency>EUR</Currency>
    <DiscountCurve>EUR-OIS</DiscountCurve>  <!-- Uses OIS for discounting -->
    <Segments>
      <!-- Short end: 6M deposit -->
      <Simple>
        <Type>Deposit</Type>
        <Quotes>
          <Quote>MM/RATE/EUR/2D/6M</Quote>
        </Quotes>
        <Conventions>EUR-EURIBOR-6M-DEPOSIT</Conventions>
        <ProjectionCurve>EUR-EURIBOR-6M</ProjectionCurve>
      </Simple>
      <!-- Long end: 6M swaps -->
      <Simple>
        <Type>Swap</Type>
        <Quotes>
          <Quote>IR_SWAP/RATE/EUR/2D/6M/1Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/6M/2Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/6M/3Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/6M/5Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/6M/10Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/6M/15Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/6M/20Y</Quote>
          <Quote>IR_SWAP/RATE/EUR/2D/6M/30Y</Quote>
        </Quotes>
        <Conventions>EUR-6M-SWAP-CONVENTIONS</Conventions>
        <ProjectionCurve>EUR-EURIBOR-6M</ProjectionCurve>
      </Simple>
    </Segments>
    <InterpolationVariable>Discount</InterpolationVariable>
    <InterpolationMethod>LogLinear</InterpolationMethod>
    <YieldCurveDayCounter>A365</YieldCurveDayCounter>
  </YieldCurve>
</YieldCurves>
```

#### conventions.xml (additional)
```xml
<!-- EURIBOR-6M deposit -->
<Deposit>
  <Id>EUR-EURIBOR-6M-DEPOSIT</Id>
  <IndexBased>true</IndexBased>
  <Index>EUR-EURIBOR-6M</Index>
</Deposit>

<!-- EURIBOR-6M swap -->
<Swap>
  <Id>EUR-6M-SWAP-CONVENTIONS</Id>
  <FixedCalendar>TARGET</FixedCalendar>
  <FixedFrequency>Annual</FixedFrequency>
  <FixedConvention>ModifiedFollowing</FixedConvention>
  <FixedDayCounter>30/360</FixedDayCounter>
  <Index>EUR-EURIBOR-6M</Index>
</Swap>

<!-- EURIBOR-6M index -->
<IborIndex>
  <Id>EUR-EURIBOR-6M</Id>
  <FixingCalendar>TARGET</FixingCalendar>
  <DayCounter>A360</DayCounter>
  <SettlementDays>2</SettlementDays>
  <Tenor>6M</Tenor>
</IborIndex>
```

#### market.txt (additional)
```
20231115 MM/RATE/EUR/2D/6M 0.0405
20231115 IR_SWAP/RATE/EUR/2D/6M/1Y 0.0380
20231115 IR_SWAP/RATE/EUR/2D/6M/2Y 0.0335
20231115 IR_SWAP/RATE/EUR/2D/6M/3Y 0.0300
20231115 IR_SWAP/RATE/EUR/2D/6M/5Y 0.0270
20231115 IR_SWAP/RATE/EUR/2D/6M/10Y 0.0275
20231115 IR_SWAP/RATE/EUR/2D/6M/15Y 0.0290
20231115 IR_SWAP/RATE/EUR/2D/6M/20Y 0.0300
20231115 IR_SWAP/RATE/EUR/2D/6M/30Y 0.0305
```

**Dependency**: EUR-EURIBOR-6M depends on EUR-OIS (for discounting), so EUR-OIS must be built first.

### Example 3: Tenor Basis Curve

**Goal**: Build EUR 3M forwarding curve using 3M/6M tenor basis

#### curveconfig.xml
```xml
<YieldCurve>
  <CurveId>EUR-EURIBOR-3M</CurveId>
  <CurveDescription>EUR 3M forwarding curve from tenor basis</CurveDescription>
  <Currency>EUR</Currency>
  <DiscountCurve>EUR-OIS</DiscountCurve>
  <Segments>
    <!-- Short end: 3M deposit -->
    <Simple>
      <Type>Deposit</Type>
      <Quotes>
        <Quote>MM/RATE/EUR/2D/3M</Quote>
      </Quotes>
      <Conventions>EUR-EURIBOR-3M-DEPOSIT</Conventions>
      <ProjectionCurve>EUR-EURIBOR-3M</ProjectionCurve>
    </Simple>
    <!-- Tenor basis: pay 3M, receive 6M + spread -->
    <TenorBasis>
      <Type>TenorBasis</Type>
      <Quotes>
        <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/2Y</Quote>
        <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/3Y</Quote>
        <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/5Y</Quote>
        <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/10Y</Quote>
        <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/15Y</Quote>
        <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/20Y</Quote>
        <Quote>BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/30Y</Quote>
      </Quotes>
      <Conventions>EUR-TENOR-BASIS-3M-6M</Conventions>
      <ProjectionCurvePay>EUR-EURIBOR-3M</ProjectionCurvePay>
      <ProjectionCurveReceive>EUR-EURIBOR-6M</ProjectionCurveReceive>
    </TenorBasis>
  </Segments>
  <InterpolationVariable>Discount</InterpolationVariable>
  <InterpolationMethod>LogLinear</InterpolationMethod>
  <YieldCurveDayCounter>A365</YieldCurveDayCounter>
</YieldCurve>
```

#### conventions.xml (additional)
```xml
<TenorBasisSwap>
  <Id>EUR-TENOR-BASIS-3M-6M</Id>
  <Calendar>TARGET</Calendar>
  <LongFixedFrequency>Semiannual</LongFixedFrequency>
  <LongFixedConvention>ModifiedFollowing</LongFixedConvention>
  <LongFixedDayCounter>A360</LongFixedDayCounter>
  <LongIndex>EUR-EURIBOR-6M</LongIndex>
  <ShortFixedFrequency>Quarterly</ShortFixedFrequency>
  <ShortFixedConvention>ModifiedFollowing</ShortFixedConvention>
  <ShortFixedDayCounter>A360</ShortFixedDayCounter>
  <ShortIndex>EUR-EURIBOR-3M</ShortIndex>
  <LongMinusShort>true</LongMinusShort>
</TenorBasisSwap>
```

#### market.txt (additional)
```
20231115 MM/RATE/EUR/2D/3M 0.0395
20231115 BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/2Y -0.0015
20231115 BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/3Y -0.0015
20231115 BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/5Y -0.0015
20231115 BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/10Y -0.0015
20231115 BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/15Y -0.0015
20231115 BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/20Y -0.0015
20231115 BASIS_SWAP/BASIS_SPREAD/EUR/2D/6M/3M/30Y -0.0015
```

**Dependencies**: EUR-EURIBOR-3M depends on both EUR-OIS and EUR-EURIBOR-6M.

### Example 4: Cross-Currency Basis Curve

**Goal**: Build USD 3M forwarding curve implied from EUR curves and EUR/USD cross-currency basis

#### curveconfig.xml
```xml
<YieldCurve>
  <CurveId>USD-EURIBOR-3M-IMPLIED</CurveId>
  <CurveDescription>USD 3M curve from EUR/USD basis</CurveDescription>
  <Currency>USD</Currency>
  <DiscountCurve>USD-OIS</DiscountCurve>
  <Segments>
    <CrossCcyBasis>
      <Type>CrossCcyBasis</Type>
      <Quotes>
        <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/2Y</Quote>
        <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/3Y</Quote>
        <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/5Y</Quote>
        <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/10Y</Quote>
        <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/15Y</Quote>
        <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/20Y</Quote>
        <Quote>CC_BASIS/BASIS_SPREAD/EUR/USD/3M/30Y</Quote>
      </Quotes>
      <Conventions>EUR-USD-XCCY-BASIS</Conventions>
      <DiscountCurve>EUR-OIS</DiscountCurve>
      <SpotRate>FX/RATE/EUR/USD</SpotRate>
      <ForeignDiscountCurve>USD-OIS</ForeignDiscountCurve>
      <ProjectionCurveDomestic>EUR-EURIBOR-3M</ProjectionCurveDomestic>
      <ProjectionCurveForeign>USD-EURIBOR-3M-IMPLIED</ProjectionCurveForeign>
    </CrossCcyBasis>
  </Segments>
  <InterpolationVariable>Discount</InterpolationVariable>
  <InterpolationMethod>LogLinear</InterpolationMethod>
  <YieldCurveDayCounter>A365</YieldCurveDayCounter>
</YieldCurve>
```

#### conventions.xml (additional)
```xml
<CrossCcyBasisSwap>
  <Id>EUR-USD-XCCY-BASIS</Id>
  <SettlementDays>2</SettlementDays>
  <SettlementCalendar>TARGET,US</SettlementCalendar>
  <RollConvention>ModifiedFollowing</RollConvention>
  <FlatIndex>EUR-EURIBOR-3M</FlatIndex>
  <SpreadIndex>USD-LIBOR-3M</SpreadIndex>
  <EOM>false</EOM>
</CrossCcyBasisSwap>
```

#### market.txt (additional)
```
20231115 FX/RATE/EUR/USD 1.0875
20231115 CC_BASIS/BASIS_SPREAD/EUR/USD/3M/2Y 0.0025
20231115 CC_BASIS/BASIS_SPREAD/EUR/USD/3M/3Y 0.0025
20231115 CC_BASIS/BASIS_SPREAD/EUR/USD/3M/5Y 0.0025
20231115 CC_BASIS/BASIS_SPREAD/EUR/USD/3M/10Y 0.0025
20231115 CC_BASIS/BASIS_SPREAD/EUR/USD/3M/15Y 0.0025
20231115 CC_BASIS/BASIS_SPREAD/EUR/USD/3M/20Y 0.0025
20231115 CC_BASIS/BASIS_SPREAD/EUR/USD/3M/30Y 0.0025
```

**Dependencies**:
- EUR-OIS (domestic discount)
- USD-OIS (foreign discount)
- EUR-EURIBOR-3M (domestic projection)
- FX spot

---

## Code References

### Key Files and Line Numbers

#### Configuration Layer

- **[OREData/ored/configuration/yieldcurveconfig.hpp](../OREData/ored/configuration/yieldcurveconfig.hpp:61-718)**: All curve configuration classes
  - `YieldCurveSegment`: Base class (lines 61-136)
  - `SimpleYieldCurveSegment`: Deposits, swaps, etc. (lines 176-207)
  - `TenorBasisYieldCurveSegment`: Tenor basis (lines 259-292)
  - `CrossCcyYieldCurveSegment`: Cross-currency (lines 304-343)
  - `YieldCurveConfig`: Main config class (lines 651-718)

- **[OREData/ored/configuration/yieldcurveconfig.cpp](../OREData/ored/configuration/yieldcurveconfig.cpp)**: XML parsing implementation

- **[OREData/ored/configuration/conventions.hpp](../OREData/ored/configuration/conventions.hpp)**: Convention classes

#### Market Data Layer

- **[OREData/ored/marketdata/loader.hpp](../OREData/ored/marketdata/loader.hpp)**: Abstract loader interface

- **[OREData/ored/marketdata/csvloader.hpp](../OREData/ored/marketdata/csvloader.hpp:41-111)**: CSV loader

- **[OREData/ored/marketdata/todaysmarket.hpp](../OREData/ored/marketdata/todaysmarket.hpp:80-172)**: TodaysMarket class

- **[OREData/ored/marketdata/todaysmarket.cpp:100-200](../OREData/ored/marketdata/todaysmarket.cpp)**: Market building orchestration

#### Curve Building Layer

- **[OREData/ored/marketdata/yieldcurve.hpp](../OREData/ored/marketdata/yieldcurve.hpp:63-224)**: YieldCurve class
  - `InterpolationVariable` enum (line 66)
  - `InterpolationMethod` enum (lines 69-90)

- **[OREData/ored/marketdata/yieldcurve.cpp](../OREData/ored/marketdata/yieldcurve.cpp)**: Curve building implementation
  - `buildBootstrappedCurve()`: lines 1210-1402
  - `buildPiecewiseCurve()`: lines 546-792
  - `addDeposits()`: lines 1771-1841
  - `addSwaps()`: lines 2071+
  - `addTenorBasisSwaps()`: Search for "addTenorBasisSwaps"
  - `addCrossCcyBasisSwaps()`: Search for "addCrossCcyBasisSwaps"

#### QuantExt Extensions

- **[QuantExt/qle/termstructures/](../QuantExt/qle/termstructures/)**: QuantExt term structure extensions
  - Rate helpers: `averageoisratehelper.hpp`, `tenorbasisswaphelper.hpp`, `crossccybasisswaphelper.hpp`
  - Special curves: `discountratiomodifiedcurve.hpp`, `iborfallbackcurve.hpp`
  - Bootstrap: `iterativebootstrap.hpp`

### Important Method Signatures

#### YieldCurve Constructor

```cpp
YieldCurve(
    Date asof,
    YieldCurveSpec spec,
    const CurveConfigurations& curveConfigs,
    const Loader& loader,
    const map<string, Handle<YieldTermStructure>>& requiredYieldCurves,
    const FXTriangulation& fxSpots,
    const ReferenceDataManager& referenceData = ReferenceDataManager()
);
```

#### TodaysMarket Constructor

```cpp
TodaysMarket(
    const Date& asof,
    const shared_ptr<TodaysMarketParameters>& params,
    const shared_ptr<Loader>& loader,
    const shared_ptr<CurveConfigurations>& curveConfigs,
    const bool continueOnError = false,
    const bool loadFixings = true,
    const bool lazyBuild = false,
    const shared_ptr<ReferenceDataManager>& referenceData = nullptr,
    const bool preserveQuoteLinkage = false,
    const bool buildCalibrationInfo = false
);
```

#### Building Bootstrapped Curve

```cpp
void buildBootstrappedCurve(
    const shared_ptr<YieldCurveConfig>& config,
    const Loader& loader,
    const map<string, Handle<YieldTermStructure>>& requiredCurves
);
```

#### Adding Rate Helpers

```cpp
void addDeposits(
    const shared_ptr<YieldCurveSegment>& segment,
    vector<shared_ptr<RateHelper>>& instruments
);

void addSwaps(
    const shared_ptr<YieldCurveSegment>& segment,
    vector<shared_ptr<RateHelper>>& instruments
);

void addTenorBasisSwaps(
    const shared_ptr<YieldCurveSegment>& segment,
    vector<shared_ptr<RateHelper>>& instruments
);
```

---

## Troubleshooting

### Common Configuration Errors

#### Error: "Curve [ID] not found"

**Cause**: Discount or projection curve referenced but not defined

**Solution**: Check that all referenced curves exist in `curveconfig.xml`:
```xml
<DiscountCurve>EUR-OIS</DiscountCurve>  <!-- EUR-OIS must be defined -->
<ProjectionCurve>EUR6M</ProjectionCurve>  <!-- EUR6M must be defined -->
```

#### Error: "Quote [ID] not found in market data"

**Cause**: Quote specified in configuration but missing from market data file

**Solution**:
1. Check quote name spelling in both files
2. Ensure date matches
3. Make quote optional if it's not always available:
```cpp
loader.get(quoteName, asofDate, true);  // true = optional
```

#### Error: "Circular dependency detected"

**Cause**: Two curves depend on each other, but ORE can't handle the cycle

**Solution**: Usually ORE handles this automatically. If not:
- Check for unnecessary circular references
- Ensure both curves are truly circular (e.g., tenor basis)
- Use global bootstrap: `<Global>true</Global>` in `BootstrapConfig`

#### Error: "Bootstrap failed - root not found"

**Cause**: Curve bootstrapping algorithm couldn't solve for the curve

**Solution**:
1. **Check market data quality**: Are quotes realistic? Any typos?
2. **Increase accuracy tolerance**:
   ```xml
   <Tolerance>1.0e-8</Tolerance>  <!-- Relax from 1.0e-12 -->
   ```
3. **Switch to global bootstrap**:
   ```xml
   <BootstrapConfig>
     <Global>true</Global>
   </BootstrapConfig>
   ```
4. **Check conventions**: Are day counts, calendars, frequencies correct?
5. **Check interpolation method**: Try LogLinear if using exotic method

#### Error: "Pillar date before asof date"

**Cause**: Instrument's maturity is before the valuation date

**Solution**:
1. Remove stale quotes from market data
2. Check spot lag in conventions
3. Verify asof date is correct

### Bootstrap Failures

#### Symptoms: Curve fails to build, throws exception

**Diagnostic steps**:

1. **Enable detailed logging**: Set log level to debug
2. **Check each quote individually**: Comment out quotes one by one to isolate problem
3. **Verify instruments are reasonable**: Print pillar dates and check for gaps or overlaps
4. **Test with simpler interpolation**: Start with LogLinear, then try more complex
5. **Check for negative rates**: If rates go negative, some interpolations may fail

**Common causes**:
- **Inverted curve**: Short rates higher than long rates (can cause issues with some interpolations)
- **Gaps in quotes**: Missing key tenors
- **Inconsistent quotes**: Deposit-swap basis doesn't match
- **Wrong conventions**: Mismatch between quote and convention

#### Example: Debugging with calibration info

```cpp
// Enable calibration info
auto market = make_shared<TodaysMarket>(
    asof, params, loader, curveConfigs,
    false, true, false, nullptr, true, true  // last true = buildCalibrationInfo
);

// Access calibration results
auto calibInfo = market->calibrationInfo();
auto& info = calibInfo["EUR-OIS"];

for (size_t i = 0; i < info.pillarDates.size(); ++i) {
    cout << "Pillar " << i << ": " << info.pillarDates[i] << endl;
    cout << "  Quote ID: " << info.quoteIDs[i] << endl;
    cout << "  Market value: " << info.quoteValues[i] << endl;
    cout << "  Calibrated value: " << info.curveValues[i] << endl;
    cout << "  Error: " << info.errors[i] << endl;

    if (abs(info.errors[i]) > 1.0e-6)
        cerr << "WARNING: Large calibration error!" << endl;
}
```

### Missing Market Data

#### Error: "Required fixing [INDEX] on [DATE] not found"

**Cause**: Trade requires historical index fixing that's not in fixings file

**Solution**:
1. Add fixing to `fixings.txt`:
   ```
   20231110 EUR-EURIBOR-6M 0.0405
   ```
2. Or disable fixing requirement (not recommended for production):
   ```cpp
   Settings::instance().enforcesTodaysHistoricFixings() = false;
   ```

#### Warning: "Quote [ID] not found, using default value"

**Cause**: Optional quote missing from market data

**Solution**:
- Provide the quote if available
- Or accept default behavior (may use previous value or interpolate)

### Performance Issues

#### Problem: Curve building is slow

**Solutions**:

1. **Use lazy building**:
   ```cpp
   auto market = make_shared<TodaysMarket>(..., true);  // lazyBuild = true
   ```

2. **Disable calibration info**:
   ```cpp
   auto market = make_shared<TodaysMarket>(..., false);  // buildCalibrationInfo = false
   ```

3. **Simplify interpolation**: Use LogLinear instead of ConvexMonotone or Global bootstrap

4. **Reduce quotes**: Use fewer pillar points if possible

5. **Disable quote linkage** (if not needed for sensitivities):
   ```cpp
   auto market = make_shared<TodaysMarket>(..., false);  // preserveQuoteLinkage = false
   ```

### Debugging Tips

1. **Start simple**: Build simplest possible curve first (just deposits, linear interpolation)

2. **Add complexity incrementally**: Add swaps, then basis, then change interpolation

3. **Compare to market**: Check a few key discount factors match market expectations

4. **Visualize the curve**: Plot zero rates or forward rates to spot anomalies

5. **Check sensitivities**: Bump quotes and verify curve moves as expected

6. **Use examples**: Start from working examples in `Examples/` directory

7. **Enable continue-on-error**: To see which curves fail:
   ```cpp
   auto market = make_shared<TodaysMarket>(..., true);  // continueOnError = true
   ```

---

## Summary

ORE's yield curve building system is a sophisticated, production-ready framework that:

1. **Separates configuration from computation**: XML defines structure, C++ does calculation
2. **Supports diverse curve types**: From simple zero curves to complex multi-currency basis curves
3. **Handles dependencies automatically**: Topological sorting ensures correct build order
4. **Provides flexibility**: 20+ interpolation methods, multiple bootstrap algorithms
5. **Integrates with QuantLib**: Leverages proven financial engineering library
6. **Extends QuantLib**: Adds practical features like tenor basis, cross-currency basis, IBOR fallback
7. **Enables robust workflows**: Error handling, lazy building, calibration diagnostics

The system is designed for both simplicity (can build basic curves with minimal configuration) and power (can handle complex multi-curve setups with circular dependencies).

**Key takeaways**:
- Start with simple OIS discount curves
- Use multi-curve framework for post-crisis pricing
- Choose interpolation carefully (LogLinear is safe default)
- Leverage examples in `Examples/` directory
- Use calibration info for debugging
- Understand dependencies to optimize build order

For more information, see:
- [User Guide](../userguide.pdf): Section on curve configuration
- [Examples/](../../Examples/): Concrete working examples
- [QuantLib documentation](http://quantlib.org): Foundation library
- [ORE website](http://opensourcerisk.org): Project home
