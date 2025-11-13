# Sensitivity Analysis in ORE

## Table of Contents

1. [Overview](#overview)
2. [Architecture and Components](#architecture-and-components)
3. [Mandatory vs Optional Parameters](#mandatory-vs-optional-parameters)
4. [Risk Factor Types](#risk-factor-types)
5. [Shift Types and Shift Schemes](#shift-types-and-shift-schemes)
6. [Configuration Reference](#configuration-reference)
7. [Default Behaviors](#default-behaviors)
8. [Sensitivity Analytics Types](#sensitivity-analytics-types)
9. [Output and Reports](#output-and-reports)
10. [Advanced Features](#advanced-features)
11. [Examples](#examples)
12. [Integration Flow](#integration-flow)

---

## Overview

ORE's sensitivity analysis framework computes first-order (delta) and second-order (gamma) risk sensitivities by applying systematic market data shifts and repricing the portfolio. This "bump-and-revalue" approach is configurable, comprehensive, and supports both zero-rate and par-rate sensitivities.

### Key Capabilities

- **Delta Sensitivities**: First-order sensitivities to market risk factors
- **Gamma Sensitivities**: Second-order sensitivities (optional)
- **Cross-Gamma**: Cross-sensitivities between different risk factors (optional)
- **Par Conversion**: Convert zero-rate sensitivities to par-rate sensitivities
- **Multiple Analytics**: Standard sensitivity, stress testing, XVA sensitivity, parametric VaR
- **Flexible Configuration**: XML-driven with extensive customization options

### Main Configuration File

Sensitivity analysis is configured via `sensitivity.xml` (or similar), which specifies:
- Which risk factors to shift
- How much to shift them
- Which shift scheme to use (Forward, Backward, Central)
- Par conversion specifications (optional)
- Cross-gamma filters (optional)

---

## Architecture and Components

### Core Classes

#### 1. SensitivityAnalysis

**Location**: [OREAnalytics/orea/engine/sensitivityanalysis.hpp](../../../OREAnalytics/orea/engine/sensitivityanalysis.hpp)

Main orchestrator for sensitivity calculation:

```cpp
class SensitivityAnalysis {
public:
    SensitivityAnalysis(
        const boost::shared_ptr<ore::data::Portfolio>& portfolio,
        const boost::shared_ptr<ore::data::Market>& market,
        const std::string& marketConfiguration,
        const boost::shared_ptr<ore::data::EngineData>& engineData,
        const boost::shared_ptr<SensitivityScenarioData>& scenarioData,
        const bool recalibrateModels = false,
        const boost::shared_ptr<ScenarioSimMarketParameters>& simMarketData = nullptr,
        const boost::shared_ptr<ReferenceDataManager>& referenceData = nullptr,
        const ore::data::IborFallbackConfig& iborFallbackConfig =
            ore::data::IborFallbackConfig::defaultConfig(),
        const bool continueOnError = false
    );

    // Main execution
    void generateSensitivities();

    // Results
    boost::shared_ptr<SensitivityCube> sensitivityCube() const;
};
```

#### 2. SensitivityScenarioData

**Location**: [OREAnalytics/orea/scenario/sensitivityscenariodata.hpp](../../../OREAnalytics/orea/scenario/sensitivityscenariodata.hpp)

Configuration data structure parsed from `sensitivity.xml`:

```cpp
class SensitivityScenarioData {
public:
    // Configuration accessors
    bool computeGamma() const;
    const std::set<std::pair<RiskFactorKey, RiskFactorKey>>& crossGammaFilter() const;

    // Shift data per risk factor type
    const std::vector<DiscountCurveShiftData>& discountCurveShiftData() const;
    const std::vector<IndexCurveShiftData>& indexCurveShiftData() const;
    const std::vector<FxShiftData>& fxShiftData() const;
    // ... and many more

    // Par conversion
    bool parConversion() const;
    const std::set<RiskFactorKey::KeyType>& parConversionExcludes() const;
};
```

#### 3. SensitivityScenarioGenerator

**Location**: [OREAnalytics/orea/scenario/sensitivityscenariogenerator.hpp](../../../OREAnalytics/orea/scenario/sensitivityscenariogenerator.hpp)

Generates shift scenarios based on configuration:

```cpp
class SensitivityScenarioGenerator {
public:
    SensitivityScenarioGenerator(
        const boost::shared_ptr<SensitivityScenarioData>& scenarioData,
        const boost::shared_ptr<Scenario>& baseScenario,
        const boost::shared_ptr<ScenarioSimMarketParameters>& simMarketData,
        const boost::shared_ptr<ScenarioFactory>& scenarioFactory
    );

    // Generate all scenarios
    void generateScenarios();

    // Access scenarios
    std::vector<boost::shared_ptr<Scenario>> scenarios() const;
    std::map<RiskFactorKey, Real> shiftSizes() const;
};
```

#### 4. SensitivityCube

**Location**: [OREAnalytics/orea/cube/sensitivitycube.hpp](../../../OREAnalytics/orea/cube/sensitivitycube.hpp)

Stores sensitivity results:

```cpp
class SensitivityCube {
public:
    // Access sensitivities
    Real delta(const std::string& tradeId, const RiskFactorKey& key) const;
    Real gamma(const std::string& tradeId,
               const RiskFactorKey& key1,
               const RiskFactorKey& key2) const;

    // Export
    void toFile(const std::string& fileName) const;
};
```

### Execution Flow

```
sensitivity.xml (configuration)
         ↓
SensitivityScenarioData::fromXML()
         ↓
SensitivityScenarioGenerator::generateScenarios()
         ↓
[Create UP and DOWN scenarios for each risk factor]
         ↓
SensitivityAnalysis::generateSensitivities()
         ↓
For each scenario:
    ├─ Apply shift to ScenarioSimMarket
    ├─ Rebuild yield curves, vol surfaces, etc.
    ├─ Optionally recalibrate models
    ├─ Reprice all trades
    └─ Store NPV differences
         ↓
SensitivityCalculator (compute deltas/gammas)
         ↓
Optional: ParSensitivityAnalysis (convert to par sensitivities)
         ↓
SensitivityCube (results)
         ↓
Output reports (CSV, XML, in-memory)
```

---

## Mandatory vs Optional Parameters

### Global Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| **Risk Factor Shifts** | **YES** | N/A | At least one risk factor type must be configured |
| `ComputeGamma` | NO | `true` | Whether to compute second-order sensitivities |
| `ParConversion` | NO | `true` | Whether to perform par conversion |
| `CrossGammaFilter` | NO | Empty (all) | Filter for cross-gamma pairs |
| `ParConversionExcludes` | NO | Empty | Risk factor types to exclude from par conversion |

### Per Risk Factor Parameters

#### Always Mandatory

| Parameter | Description | Values |
|-----------|-------------|--------|
| **ShiftType** | How to shift the risk factor | `Absolute`, `Relative` |
| **ShiftSize** | Magnitude of shift | Decimal value (e.g., `0.0001` for 1bp) |

#### Conditionally Mandatory

| Parameter | Required For | Description |
|-----------|-------------|-------------|
| **ShiftTenors** | Curves | Comma-separated tenor points (e.g., "1Y,2Y,5Y,10Y") |
| **ShiftExpiries** | Volatility surfaces | Expiry points for vol surfaces |
| **ShiftStrikes** | Vol surfaces (ATM if omitted) | Strike points for vol surfaces |
| **ShiftTerms** | Swaption vols, base correlations | Underlying term/maturity points |
| **ShiftLossLevels** | Base correlations | Loss attachment points |
| **Index** | Cap/Floor volatilities | IBOR index name |
| **Currency** | Credit curves | Currency of the credit curve |

#### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| **ShiftScheme** | `Forward` | Shift direction: `Forward`, `Backward`, `Central` |
| **IsRelative** | N/A | Special flag for volatility shifts |
| **ParConversion** | Inherited from global | Per-factor par conversion specification |

### Summary Table: Mandatory vs Optional

```
┌─────────────────────┬──────────────┬──────────────┬─────────────┐
│ Parameter           │ Mandatory    │ Default      │ Notes       │
├─────────────────────┼──────────────┼──────────────┼─────────────┤
│ ShiftType           │ YES          │ None         │ Must specify│
│ ShiftSize           │ YES          │ None         │ Must specify│
│ ShiftScheme         │ NO           │ Forward      │ Auto-set    │
│ ShiftTenors         │ For curves   │ None         │ Curve-only  │
│ ShiftExpiries       │ For vols     │ None         │ Vol-only    │
│ ShiftStrikes        │ For vols     │ {0.0} (ATM)  │ Vol-only    │
│ ShiftTerms          │ For some vols│ None         │ Special     │
│ ShiftLossLevels     │ BaseCorr only│ None         │ BaseCorr    │
│ Index               │ CapFloor vols│ None         │ CapFloor    │
│ Currency            │ Credit curves│ None         │ Credit      │
│ ParConversion       │ NO           │ true (global)│ Advanced    │
└─────────────────────┴──────────────┴──────────────┴─────────────┘
```

---

## Risk Factor Types

ORE supports sensitivity analysis for the following risk factor types:

### 1. Interest Rate Risk Factors

#### Discount Curves

**Purpose**: OIS/discounting curves for each currency

**Configuration**:
```xml
<DiscountCurves>
  <DiscountCurve ccy="EUR">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
    <ShiftTenors>6M,1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y</ShiftTenors>
  </DiscountCurve>
</DiscountCurves>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftTenors`
**Optional**: `ShiftScheme`, `ParConversion`

#### Index Curves

**Purpose**: IBOR forward curves (e.g., EURIBOR, LIBOR)

**Configuration**:
```xml
<IndexCurves>
  <IndexCurve index="EUR-EURIBOR-6M">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
    <ShiftTenors>6M,1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y</ShiftTenors>
  </IndexCurve>
</IndexCurves>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftTenors`
**Optional**: `ShiftScheme`, `ParConversion`

#### Yield Curves

**Purpose**: Generic yield curves (bonds, government curves)

**Configuration**:
```xml
<YieldCurves>
  <YieldCurve name="BondCurve/USD">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
    <ShiftTenors>1Y,2Y,3Y,5Y,7Y,10Y,20Y,30Y</ShiftTenors>
  </YieldCurve>
</YieldCurves>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftTenors`

### 2. FX Risk Factors

#### FX Spots

**Purpose**: Foreign exchange spot rates

**Configuration**:
```xml
<FxSpots>
  <FxSpot ccypair="EURUSD">
    <ShiftType>Relative</ShiftType>
    <ShiftSize>0.01</ShiftSize>  <!-- 1% shift -->
  </FxSpot>
</FxSpots>
```

**Mandatory**: `ShiftType`, `ShiftSize`
**Optional**: `ShiftScheme`

**Note**: Use `Relative` shift type for FX spots (standard market practice)

#### FX Volatilities

**Purpose**: FX option implied volatilities

**Configuration**:
```xml
<FxVolatilities>
  <FxVolatility ccypair="EURUSD">
    <ShiftType>Relative</ShiftType>
    <ShiftSize>0.01</ShiftSize>
    <ShiftExpiries>1M,3M,6M,1Y,2Y,5Y</ShiftExpiries>
    <ShiftStrikes>0.75,0.90,0.95,ATM,1.05,1.10,1.25</ShiftStrikes>
  </FxVolatility>
</FxVolatilities>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftExpiries`
**Optional**: `ShiftStrikes` (defaults to ATM only)

### 3. Equity Risk Factors

#### Equity Spots

**Purpose**: Equity/stock prices

**Configuration**:
```xml
<EquitySpots>
  <EquitySpot equity="SPX">
    <ShiftType>Relative</ShiftType>
    <ShiftSize>0.01</ShiftSize>
  </EquitySpot>
</EquitySpots>
```

**Mandatory**: `ShiftType`, `ShiftSize`

#### Equity Volatilities

**Purpose**: Equity option implied volatilities

**Configuration**:
```xml
<EquityVolatilities>
  <EquityVolatility equity="SPX">
    <ShiftType>Relative</ShiftType>
    <ShiftSize>0.01</ShiftSize>
    <ShiftExpiries>1M,3M,6M,1Y,2Y,5Y</ShiftExpiries>
    <ShiftStrikes>0.8,0.9,0.95,ATM,1.05,1.1,1.2</ShiftStrikes>
  </EquityVolatility>
</EquityVolatilities>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftExpiries`
**Optional**: `ShiftStrikes`

#### Dividend Yields

**Purpose**: Dividend yield curves for equities

**Configuration**:
```xml
<DividendYieldCurves>
  <DividendYieldCurve equity="SPX">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
    <ShiftTenors>6M,1Y,2Y,3Y,5Y,7Y,10Y</ShiftTenors>
  </DividendYieldCurve>
</DividendYieldCurves>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftTenors`

### 4. Volatility Risk Factors

#### Swaption Volatilities

**Purpose**: Interest rate swaption implied volatilities

**Configuration**:
```xml
<SwaptionVolatilities>
  <SwaptionVolatility ccy="EUR">
    <ShiftType>Relative</ShiftType>
    <ShiftSize>0.01</ShiftSize>
    <ShiftExpiries>1Y,2Y,3Y,5Y,7Y,10Y</ShiftExpiries>
    <ShiftTerms>1Y,2Y,5Y,10Y,20Y</ShiftTerms>
    <ShiftStrikes/>  <!-- ATM only -->
  </SwaptionVolatility>
</SwaptionVolatilities>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftExpiries`, `ShiftTerms`
**Optional**: `ShiftStrikes` (defaults to ATM)

#### Cap/Floor Volatilities

**Purpose**: Interest rate cap/floor volatilities

**Configuration**:
```xml
<CapFloorVolatilities>
  <CapFloorVolatility ccy="EUR">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
    <ShiftExpiries>1Y,2Y,3Y,5Y,7Y,10Y</ShiftExpiries>
    <ShiftStrikes>0.01,0.02,0.03,0.04,0.05</ShiftStrikes>
    <Index>EUR-EURIBOR-6M</Index>
  </CapFloorVolatility>
</CapFloorVolatilities>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftExpiries`, `Index`
**Optional**: `ShiftStrikes`

### 5. Credit Risk Factors

#### Credit Curves

**Purpose**: Survival probability/hazard rate curves

**Configuration**:
```xml
<CreditCurves>
  <CreditCurve name="CPTY_A">
    <Currency>USD</Currency>
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
    <ShiftTenors>6M,1Y,2Y,3Y,5Y,7Y,10Y</ShiftTenors>
  </CreditCurve>
</CreditCurves>
```

**Mandatory**: `Currency`, `ShiftType`, `ShiftSize`, `ShiftTenors`
**Optional**: `ParConversion`

#### CDS Volatilities

**Purpose**: CDS option/index volatilities

**Configuration**:
```xml
<CDSVolatilities>
  <CDSVolatility name="CDX.IG">
    <ShiftType>Relative</ShiftType>
    <ShiftSize>0.01</ShiftSize>
    <ShiftExpiries>3M,6M,1Y,2Y,3Y,5Y</ShiftExpiries>
  </CDSVolatility>
</CDSVolatilities>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftExpiries`

#### Base Correlations

**Purpose**: CDO tranche base correlations

**Configuration**:
```xml
<BaseCorrelations>
  <BaseCorrelation indexName="CDX.IG">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.01</ShiftSize>
    <ShiftLossLevels>0.03,0.06,0.10,0.20,1.0</ShiftLossLevels>
    <ShiftTerms>1Y,3Y,5Y,7Y,10Y</ShiftTerms>
  </BaseCorrelation>
</BaseCorrelations>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftLossLevels`, `ShiftTerms`

### 6. Inflation Risk Factors

#### Zero Inflation Curves

**Purpose**: Zero-coupon inflation index curves

**Configuration**:
```xml
<ZeroInflationIndexCurves>
  <ZeroInflationIndexCurve index="EUHICPXT">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
    <ShiftTenors>1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y</ShiftTenors>
  </ZeroInflationIndexCurve>
</ZeroInflationIndexCurves>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftTenors`

#### YoY Inflation Curves

**Purpose**: Year-on-year inflation curves

**Configuration**:
```xml
<YYInflationIndexCurves>
  <YYInflationIndexCurve index="UKRPI">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
    <ShiftTenors>1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y</ShiftTenors>
  </YYInflationIndexCurve>
</YYInflationIndexCurves>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftTenors`

### 7. Commodity Risk Factors

#### Commodity Curves

**Purpose**: Commodity forward curves

**Configuration**:
```xml
<CommodityCurves>
  <CommodityCurve name="BRENT">
    <ShiftType>Relative</ShiftType>
    <ShiftSize>0.01</ShiftSize>
    <ShiftTenors>1M,3M,6M,1Y,2Y,3Y,5Y</ShiftTenors>
  </CommodityCurve>
</CommodityCurves>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftTenors`

#### Commodity Volatilities

**Purpose**: Commodity option volatilities

**Configuration**:
```xml
<CommodityVolatilities>
  <CommodityVolatility name="BRENT">
    <ShiftType>Relative</ShiftType>
    <ShiftSize>0.01</ShiftSize>
    <ShiftExpiries>1M,3M,6M,1Y,2Y,5Y</ShiftExpiries>
    <ShiftStrikes/>
  </CommodityVolatility>
</CommodityVolatilities>
```

**Mandatory**: `ShiftType`, `ShiftSize`, `ShiftExpiries`

### 8. Other Risk Factors

#### Security Spreads

**Purpose**: Bond/security credit spreads

**Configuration**:
```xml
<SecuritySpreads>
  <SecuritySpread security="ISIN:US912828XG93">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.0001</ShiftSize>
  </SecuritySpread>
</SecuritySpreads>
```

**Mandatory**: `ShiftType`, `ShiftSize`

#### Correlations

**Purpose**: Correlation matrices

**Configuration**:
```xml
<Correlations>
  <Correlation index1="EQ-SPX" index2="EQ-FTSE">
    <ShiftType>Absolute</ShiftType>
    <ShiftSize>0.01</ShiftSize>
  </Correlation>
</Correlations>
```

**Mandatory**: `ShiftType`, `ShiftSize`

---

## Shift Types and Shift Schemes

### Shift Types

**Definition**: How the shift is applied to the risk factor value.

**Location**: [QuantExt/qle/termstructures/scenario.hpp](../../../QuantExt/qle/termstructures/scenario.hpp)

```cpp
enum class ShiftType {
    Absolute,  // Add shift to base value
    Relative   // Multiply by (1 + shift)
};
```

#### Absolute Shift

```
Shifted Value = Base Value + Shift Size
```

**Example**: Interest rate shift
- Base: 2.00% (0.02)
- Shift Size: 0.0001 (1 basis point)
- Shifted: 2.01% (0.0201)

**Use Cases**:
- Interest rates (discount curves, index curves, yield curves)
- Credit spreads
- Inflation rates
- Basis point shifts

**Typical Shift Sizes**:
- **1 bp**: `0.0001` (standard for rates)
- **10 bp**: `0.001` (for finite difference products)
- **1%**: `0.01` (for large shifts)

#### Relative Shift

```
Shifted Value = Base Value × (1 + Shift Size)
```

**Example**: FX spot shift
- Base: 1.20 EUR/USD
- Shift Size: 0.01 (1%)
- Shifted: 1.20 × 1.01 = 1.212

**Use Cases**:
- FX spots
- Equity prices
- Commodity prices
- Volatilities (multiplicative)
- Dividend yields

**Typical Shift Sizes**:
- **1%**: `0.01` (standard for relative shifts)
- **5%**: `0.05` (stress scenarios)
- **10%**: `0.10` (extreme stress)

### Shift Schemes

**Definition**: Direction of the shift for delta calculation.

```cpp
enum class ShiftScheme {
    Forward,   // Shift up only
    Backward,  // Shift down only
    Central    // Shift both up and down
};
```

#### Forward Scheme (Default)

```
Delta = (NPV_shifted_up - NPV_base) / Shift_Size
```

**Scenarios Generated**: 1 per risk factor (UP only)

**Advantages**:
- Most efficient (half the scenarios of Central)
- Standard market practice
- Works well for linear products

**Disadvantages**:
- Less accurate for non-linear products
- Asymmetric around current value

**Example**:
```xml
<ShiftScheme>Forward</ShiftScheme>
```

#### Backward Scheme

```
Delta = (NPV_base - NPV_shifted_down) / Shift_Size
```

**Scenarios Generated**: 1 per risk factor (DOWN only)

**Use Cases**:
- When upward shifts are problematic (e.g., near zero rates)
- Reverse sensitivity checks

**Example**:
```xml
<ShiftScheme>Backward</ShiftScheme>
```

#### Central Scheme

```
Delta = (NPV_shifted_up - NPV_shifted_down) / (2 × Shift_Size)
```

**Scenarios Generated**: 2 per risk factor (UP and DOWN)

**Advantages**:
- More accurate for non-linear products
- Symmetric estimate
- Better for options and other convex products

**Disadvantages**:
- Twice as many scenarios (2× computational cost)

**Example**:
```xml
<ShiftScheme>Central</ShiftScheme>
```

**When to Use Central**:
- Options (high gamma)
- Callable bonds
- Complex derivatives
- When accuracy is more important than speed

### Product-Specific Overrides

You can override shift parameters for specific product types using the `key` attribute:

```xml
<DiscountCurve ccy="EUR">
  <ShiftType>Absolute</ShiftType>

  <!-- Standard shift: 1bp -->
  <ShiftSize>0.0001</ShiftSize>

  <!-- Larger shift for finite difference products: 10bp -->
  <ShiftSize key="IR_FD">0.001</ShiftSize>

  <!-- Forward scheme for most products -->
  <ShiftScheme>Forward</ShiftScheme>

  <!-- Central scheme for finite difference products -->
  <ShiftScheme key="IR_FD">Central</ShiftScheme>

  <ShiftTenors>6M,1Y,2Y,5Y,10Y,30Y</ShiftTenors>
</DiscountCurve>
```

**Common Keys**:
- `IR_FD`: Interest rate finite difference products
- Custom keys defined in your application

---

## Configuration Reference

### Complete XML Structure

```xml
<?xml version="1.0"?>
<SensitivityAnalysis>
  <!-- Global Settings -->
  <ParConversionExcludes>
    <Type>OptionletVolatility</Type>
    <Type>FXVolatility</Type>
  </ParConversionExcludes>

  <!-- Interest Rate Risk Factors -->
  <DiscountCurves>
    <DiscountCurve ccy="EUR">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftScheme>Forward</ShiftScheme>
      <ShiftTenors>6M,1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y</ShiftTenors>
      <!-- Optional: Par Conversion -->
      <ParConversion>
        <Instruments>OIS,OIS,OIS,OIS,OIS,OIS,OIS,OIS,OIS,OIS</Instruments>
        <SingleCurve>true</SingleCurve>
        <Conventions>
          <Convention id="OIS">EUR-OIS-CONVENTIONS</Convention>
        </Conventions>
      </ParConversion>
    </DiscountCurve>
  </DiscountCurves>

  <IndexCurves>
    <IndexCurve index="EUR-EURIBOR-6M">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>6M,1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y</ShiftTenors>
      <ParConversion>
        <Instruments>DEP,DEP,IRS,IRS,IRS,IRS,IRS,IRS,IRS,IRS</Instruments>
        <SingleCurve>false</SingleCurve>
        <DiscountCurve>EUR-EONIA</DiscountCurve>
        <Conventions>
          <Convention id="DEP">EUR-EURIBOR-CONVENTIONS</Convention>
          <Convention id="IRS">EUR-6M-SWAP-CONVENTIONS</Convention>
        </Conventions>
      </ParConversion>
    </IndexCurve>
  </IndexCurves>

  <!-- FX Risk Factors -->
  <FxSpots>
    <FxSpot ccypair="EURUSD">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
    </FxSpot>
  </FxSpots>

  <FxVolatilities>
    <FxVolatility ccypair="EURUSD">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
      <ShiftExpiries>1M,3M,6M,1Y,2Y,5Y</ShiftExpiries>
      <ShiftStrikes/>  <!-- ATM only -->
    </FxVolatility>
  </FxVolatilities>

  <!-- Volatility Risk Factors -->
  <SwaptionVolatilities>
    <SwaptionVolatility ccy="EUR">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
      <ShiftExpiries>1Y,2Y,3Y,5Y,7Y,10Y</ShiftExpiries>
      <ShiftTerms>1Y,2Y,5Y,10Y,20Y</ShiftTerms>
      <ShiftStrikes/>
    </SwaptionVolatility>
  </SwaptionVolatilities>

  <CapFloorVolatilities>
    <CapFloorVolatility ccy="EUR">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftExpiries>1Y,2Y,3Y,5Y,7Y,10Y</ShiftExpiries>
      <ShiftStrikes>0.01,0.02,0.03,0.04,0.05</ShiftStrikes>
      <Index>EUR-EURIBOR-6M</Index>
    </CapFloorVolatility>
  </CapFloorVolatilities>

  <!-- Credit Risk Factors -->
  <CreditCurves>
    <CreditCurve name="BANK_A">
      <Currency>USD</Currency>
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>6M,1Y,2Y,3Y,5Y,7Y,10Y</ShiftTenors>
    </CreditCurve>
  </CreditCurves>

  <CDSVolatilities>
    <CDSVolatility name="CDX.IG">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
      <ShiftExpiries>6M,1Y,2Y,3Y,5Y</ShiftExpiries>
    </CDSVolatility>
  </CDSVolatilities>

  <BaseCorrelations>
    <BaseCorrelation indexName="CDX.IG">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.01</ShiftSize>
      <ShiftLossLevels>0.03,0.06,0.10,0.20,1.0</ShiftLossLevels>
      <ShiftTerms>1Y,3Y,5Y,7Y,10Y</ShiftTerms>
    </BaseCorrelation>
  </BaseCorrelations>

  <!-- Equity Risk Factors -->
  <EquitySpots>
    <EquitySpot equity="SPX">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
    </EquitySpot>
  </EquitySpots>

  <EquityVolatilities>
    <EquityVolatility equity="SPX">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
      <ShiftExpiries>1M,3M,6M,1Y,2Y,5Y</ShiftExpiries>
      <ShiftStrikes/>
    </EquityVolatility>
  </EquityVolatilities>

  <DividendYieldCurves>
    <DividendYieldCurve equity="SPX">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>6M,1Y,2Y,3Y,5Y,7Y,10Y</ShiftTenors>
    </DividendYieldCurve>
  </DividendYieldCurves>

  <!-- Inflation Risk Factors -->
  <ZeroInflationIndexCurves>
    <ZeroInflationIndexCurve index="EUHICPXT">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y</ShiftTenors>
    </ZeroInflationIndexCurve>
  </ZeroInflationIndexCurves>

  <!-- Commodity Risk Factors -->
  <CommodityCurves>
    <CommodityCurve name="BRENT">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
      <ShiftTenors>1M,3M,6M,1Y,2Y,3Y,5Y</ShiftTenors>
    </CommodityCurve>
  </CommodityCurves>

  <CommodityVolatilities>
    <CommodityVolatility name="BRENT">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
      <ShiftExpiries>1M,3M,6M,1Y,2Y,5Y</ShiftExpiries>
    </CommodityVolatility>
  </CommodityVolatilities>

  <!-- Security Spreads -->
  <SecuritySpreads>
    <SecuritySpread security="BOND_123">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
    </SecuritySpread>
  </SecuritySpreads>

  <!-- Advanced: Cross-Gamma Filter -->
  <CrossGammaFilter>
    <Pair>DiscountCurve/EUR,DiscountCurve/EUR</Pair>
    <Pair>IndexCurve/EUR-EURIBOR-6M,IndexCurve/EUR-EURIBOR-6M</Pair>
    <Pair>DiscountCurve/EUR,IndexCurve/EUR-EURIBOR-6M</Pair>
  </CrossGammaFilter>
</SensitivityAnalysis>
```

---

## Default Behaviors

### When Parameters Are Not Specified

#### 1. ShiftScheme

**Default**: `Forward`

**Code** (from [sensitivityscenariodata.cpp](../../../OREAnalytics/orea/scenario/sensitivityscenariodata.cpp)):
```cpp
if (shiftSchemeEmptyKey == shiftSchemeKeys.end())
    data.shiftScheme = ShiftScheme::Forward;
```

**Impact**: Only UP scenarios generated (one per risk factor)

#### 2. ShiftStrikes (Volatilities)

**Default**: `{0.0}` (ATM only)

**Code**:
```cpp
vector<QuantLib::Real> shiftStrikes({0.0});
```

**Impact**: Only at-the-money volatility shifts, no smile/skew shifts

#### 3. ComputeGamma

**Default**: `true`

**Code**:
```cpp
SensitivityScenarioData(bool parConversion = true)
    : computeGamma_(true), ...
```

**Impact**: Second-order sensitivities computed automatically

#### 4. ParConversion

**Default**: `true` (global setting)

**Impact**: Zero-rate sensitivities converted to par-rate sensitivities when possible

#### 5. CrossGammaFilter

**Default**: Empty (no filtering)

**Impact**: All cross-gamma combinations computed (can be very expensive)

**Recommendation**: Specify a filter to reduce computational cost:
```xml
<CrossGammaFilter>
  <!-- Only same-curve cross gammas -->
  <Pair>DiscountCurve/EUR,DiscountCurve/EUR</Pair>
  <Pair>DiscountCurve/USD,DiscountCurve/USD</Pair>
</CrossGammaFilter>
```

#### 6. ParConversionExcludes

**Default**: Empty (all types eligible for par conversion)

**Impact**: Par conversion attempted for all risk factor types

**Common Exclusions**:
```xml
<ParConversionExcludes>
  <Type>OptionletVolatility</Type>
  <Type>FXVolatility</Type>
  <Type>SwaptionVolatility</Type>
  <Type>EquityVolatility</Type>
</ParConversionExcludes>
```

### Default Behaviors Summary Table

| Parameter | Default Value | Set By | Impact |
|-----------|--------------|--------|--------|
| ShiftScheme | `Forward` | Code | 1 scenario per factor (UP only) |
| ShiftStrikes | `{0.0}` | Code | ATM volatility only |
| ComputeGamma | `true` | Constructor | Gamma sensitivities computed |
| ParConversion | `true` | Constructor arg | Par conversion enabled |
| CrossGammaFilter | Empty | XML | All cross-gammas computed |
| ParConversionExcludes | Empty | XML | All types converted |

---

## Sensitivity Analytics Types

ORE provides several sensitivity-related analytics, each with different purposes.

### 1. Standard Sensitivity Analysis

**Analytic Type**: `sensitivity`

**Purpose**: Compute delta and gamma sensitivities for portfolio trades

**Configuration** (in `ore.xml`):
```xml
<Analytics>
  <Analytic type="sensitivity">
    <Parameter name="sensitivityConfigFile">Input/sensitivity.xml</Parameter>
    <Parameter name="pricingEnginesFile">Input/pricingengine.xml</Parameter>
    <Parameter name="marketConfigFile">Input/todaysmarket.xml</Parameter>
    <Parameter name="recalibrateModels">false</Parameter>
  </Analytic>
</Analytics>
```

**Key Files**:
- `sensitivity.xml`: Risk factor shift configuration
- `pricingengine.xml`: Pricing engine selection
- `todaysmarket.xml`: Market object configuration
- `portfolio.xml`: Portfolio of trades

**Output**:
- `sensitivity.csv`: Trade-level sensitivities
- `sensitivitypar.csv`: Par-converted sensitivities (if enabled)

**Class**: [SensitivityAnalysis](../../../OREAnalytics/orea/engine/sensitivityanalysis.hpp)

### 2. Par Sensitivity Analysis

**Analytic Type**: Integrated into standard sensitivity

**Purpose**: Convert zero-rate sensitivities to par-rate sensitivities

**How It Works**:
1. Compute zero-rate sensitivities via standard sensitivity analysis
2. Build Jacobian matrix: ∂zero_rates/∂par_rates
3. Apply matrix transformation: delta_par = J^(-1) × delta_zero

**Configuration**: Via `<ParConversion>` elements in `sensitivity.xml`

**Example**:
```xml
<DiscountCurve ccy="EUR">
  <ShiftType>Absolute</ShiftType>
  <ShiftSize>0.0001</ShiftSize>
  <ShiftTenors>1Y,2Y,3Y,5Y,7Y,10Y</ShiftTenors>
  <ParConversion>
    <Instruments>OIS,OIS,OIS,OIS,OIS,OIS</Instruments>
    <SingleCurve>true</SingleCurve>
    <Conventions>
      <Convention id="OIS">EUR-OIS-CONVENTIONS</Convention>
    </Conventions>
  </ParConversion>
</DiscountCurve>
```

**Instrument Types**:
- `DEP`: Deposit
- `FRA`: Forward Rate Agreement
- `FUT`: Interest rate future
- `OIS`: Overnight Indexed Swap
- `IRS`: Interest Rate Swap
- `CDS`: Credit Default Swap
- `ZIS`: Zero-Inflation Swap

**Class**: [ParSensitivityAnalysis](../../../OREAnalytics/orea/engine/parsensitivityanalysis.hpp)

### 3. Stress Testing

**Analytic Type**: `stress`

**Purpose**: Apply pre-defined stress scenarios to portfolio

**Configuration** (in `ore.xml`):
```xml
<Analytics>
  <Analytic type="stress">
    <Parameter name="stressConfigFile">Input/stresstest.xml</Parameter>
    <Parameter name="sensitivityConfigFile">Input/sensitivity.xml</Parameter>
  </Analytic>
</Analytics>
```

**Stress Configuration** (`stresstest.xml`):
```xml
<StressTestData>
  <StressTest id="2008_Crisis">
    <Label>2008 Financial Crisis</Label>
    <StressType>Scenario</StressType>
    <Shifts>
      <Shift type="DiscountCurve">
        <Currency>USD</Currency>
        <Tenor>ALL</Tenor>
        <ShiftType>Absolute</ShiftType>
        <ShiftSize>0.01</ShiftSize>  <!-- 100bp up -->
      </Shift>
      <Shift type="FXSpot">
        <CurrencyPair>EURUSD</CurrencyPair>
        <ShiftType>Relative</ShiftType>
        <ShiftSize>0.15</ShiftSize>  <!-- 15% depreciation -->
      </Shift>
      <Shift type="EquitySpot">
        <Equity>SPX</Equity>
        <ShiftType>Relative</ShiftType>
        <ShiftSize>-0.30</ShiftSize>  <!-- 30% down -->
      </Shift>
    </Shifts>
  </StressTest>
</StressTestData>
```

**Output**: Stress test P&L per scenario

**Class**: [StressTestAnalytic](../../../OREAnalytics/orea/app/analytics/stresstestanalytic.hpp)

### 4. Sensitivity + Stress Combined

**Analytic Type**: `sensitivitystress`

**Purpose**: Both sensitivity and stress test analytics

**Class**: [SensitivityStressAnalytic](../../../OREAnalytics/orea/app/analytics/sensitivitystressanalytic.hpp)

### 5. XVA Sensitivity

**Analytic Type**: `xvasensitivity`

**Purpose**: Sensitivities of XVA metrics (CVA, DVA, FVA, etc.) to market risk factors

**Configuration**:
```xml
<Analytics>
  <Analytic type="xvasensitivity">
    <Parameter name="sensitivityConfigFile">Input/xvasensitivity.xml</Parameter>
    <Parameter name="baseCurrency">EUR</Parameter>
    <Parameter name="calculationType">Symmetric</Parameter>
  </Analytic>
</Analytics>
```

**Output**:
- CVA sensitivities
- DVA sensitivities
- Netting set level sensitivities
- Both zero-rate and par-rate sensitivities

**Class**: [XvaSensitivityAnalytic](../../../OREAnalytics/orea/app/analytics/xvasensitivityanalytic.hpp)

### 6. Parametric VaR

**Analytic Type**: `parametricvar`

**Purpose**: Value-at-Risk calculation using sensitivity-covariance approach

**How It Works**:
```
VaR = z_α × sqrt(Δ^T × Σ × Δ)

where:
  z_α: Confidence level quantile (e.g., 2.33 for 99%)
  Δ: Vector of sensitivities
  Σ: Covariance matrix of risk factor returns
```

**Configuration**:
```xml
<Analytics>
  <Analytic type="parametricvar">
    <Parameter name="sensitivityConfigFile">Input/sensitivity.xml</Parameter>
    <Parameter name="covarianceFile">Input/covariance.csv</Parameter>
    <Parameter name="confidenceLevel">0.99</Parameter>
    <Parameter name="timeHorizon">10</Parameter>  <!-- days -->
  </Analytic>
</Analytics>
```

**Class**: Part of sensitivity framework

---

## Output and Reports

### Output Formats

ORE supports multiple output formats for sensitivity results:

#### 1. CSV Format (Default)

**File**: `Output/sensitivity.csv`

**Structure**:
```csv
TradeId,RiskFactorType,RiskFactorName,Tenor,Delta,DeltaBase,Gamma
SWAP_001,DiscountCurve,EUR,1Y,1250.50,1000000,0.15
SWAP_001,DiscountCurve,EUR,2Y,2340.20,1000000,0.28
SWAP_001,IndexCurve,EUR-EURIBOR-6M,1Y,-980.30,1000000,0.12
FX_OPT_002,FXSpot,EURUSD,,15000.70,500000,850.25
```

**Columns**:
- `TradeId`: Trade identifier
- `RiskFactorType`: Type of risk factor (DiscountCurve, FXSpot, etc.)
- `RiskFactorName`: Name/identifier (currency, index, ccypair, etc.)
- `Tenor`: Tenor point (for curves) or empty (for spots)
- `Delta`: First-order sensitivity (∂NPV/∂risk_factor)
- `DeltaBase`: Base NPV for reference
- `Gamma`: Second-order sensitivity (∂²NPV/∂risk_factor²)

#### 2. Par Sensitivity CSV

**File**: `Output/sensitivitypar.csv`

**Structure**: Same as above, but sensitivities are to par rates/spreads instead of zero rates

**Example**:
```csv
TradeId,RiskFactorType,RiskFactorName,Tenor,Instrument,Delta,Gamma
SWAP_001,DiscountCurve,EUR,5Y,OIS,2500.80,0.42
SWAP_001,IndexCurve,EUR-EURIBOR-6M,5Y,IRS,-1200.30,0.25
```

**Additional Column**:
- `Instrument`: Par instrument type (OIS, IRS, CDS, etc.)

#### 3. In-Memory Stream

**Class**: [SensitivityInMemoryStream](../../../OREAnalytics/orea/engine/sensitivityinmemorystream.hpp)

**Use Case**: Access sensitivities programmatically in C++ or Python

```cpp
auto stream = boost::make_shared<SensitivityInMemoryStream>();
sensitivityAnalysis->setSensitivityStream(stream);
sensitivityAnalysis->generateSensitivities();

// Access results
const auto& records = stream->getRecords();
for (const auto& record : records) {
    std::cout << record.tradeId << ": "
              << record.key << " = "
              << record.delta << std::endl;
}
```

#### 4. Sensitivity Cube

**Class**: [SensitivityCube](../../../OREAnalytics/orea/cube/sensitivitycube.hpp)

**Purpose**: Multi-dimensional storage for sensitivities

**Dimensions**:
- Trade ID
- Risk factor key
- Shift scenario (UP, DOWN)

**Access**:
```cpp
auto cube = sensitivityAnalysis->sensitivityCube();
Real delta = cube->delta(tradeId, riskFactorKey);
Real gamma = cube->gamma(tradeId, key1, key2);
```

### Report Types

#### 1. Trade-Level Sensitivities

Sensitivities for each individual trade in the portfolio.

**Aggregation**: None

**Use Case**:
- Understanding risk drivers per trade
- Trade-level risk limits
- Trader attribution

#### 2. Netting Set Sensitivities

Aggregated sensitivities per netting set (counterparty group).

**Aggregation**: Sum over trades in netting set

**Use Case**:
- Counterparty exposure management
- XVA hedging
- CVA sensitivities

#### 3. Portfolio Sensitivities

Total sensitivities across entire portfolio.

**Aggregation**: Sum over all trades

**Use Case**:
- Enterprise risk management
- Portfolio hedging
- Regulatory reporting (e.g., FRTB)

#### 4. Cross-Gamma Matrix

Second-order cross-sensitivities between different risk factors.

**Structure**: Sparse matrix format

**Example**:
```csv
TradeId,RiskFactor1,RiskFactor2,CrossGamma
SWAP_001,DiscountCurve/EUR/5Y,DiscountCurve/EUR/10Y,15.2
SWAP_001,DiscountCurve/EUR/5Y,IndexCurve/EUR-EURIBOR-6M/5Y,-8.7
```

**Use Case**:
- Advanced risk management
- Gamma hedging
- Curvature risk (FRTB)

#### 5. Sensitivity Breakdown

Decomposition of sensitivities by risk factor type.

**Example**:
```
Portfolio Summary:
  Total IR Delta: €2,500,000
  Total FX Delta: €1,200,000
  Total Equity Delta: €800,000
  Total Vega: €150,000
```

### Output Customization

You can customize output via the sensitivity stream interface:

```cpp
// Filter by trade
auto filteredStream = boost::make_shared<FilteredSensitivityStream>(
    baseStream,
    tradeFilter
);

// Decompose by type
auto decomposedStream = boost::make_shared<DecomposedSensitivityStream>(
    baseStream
);

// Write to file
auto fileStream = boost::make_shared<SensitivityFileStream>(
    "Output/sensitivity.csv"
);
```

---

## Advanced Features

### 1. Par Conversion

**Purpose**: Convert zero-rate sensitivities to par-rate sensitivities

**Why**:
- Traders hedge with par instruments (swaps, CDS, bonds)
- Zero rates are not directly tradeable
- Par sensitivities more actionable

**Mathematical Approach**:

```
Zero Sensitivity: ∂NPV/∂z_i  (sensitivity to zero rate at tenor i)
Par Sensitivity:  ∂NPV/∂p_j  (sensitivity to par rate of instrument j)

Relationship: ∂NPV/∂p_j = Σ_i (∂NPV/∂z_i) × (∂z_i/∂p_j)

where Jacobian J_ij = ∂z_i/∂p_j is computed by:
  1. Build par instrument j (swap, CDS, etc.)
  2. Bump par rate p_j by small amount
  3. Re-bootstrap curve
  4. Measure change in zero rate z_i
  5. J_ij = Δz_i / Δp_j
```

**Configuration Example**:

```xml
<DiscountCurve ccy="EUR">
  <ShiftType>Absolute</ShiftType>
  <ShiftSize>0.0001</ShiftSize>
  <ShiftTenors>1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y</ShiftTenors>

  <ParConversion>
    <!-- One instrument per tenor -->
    <Instruments>OIS,OIS,OIS,OIS,OIS,OIS,OIS,OIS,OIS</Instruments>

    <!-- Single curve (no separate discounting) -->
    <SingleCurve>true</SingleCurve>

    <!-- Market conventions -->
    <Conventions>
      <Convention id="OIS">EUR-OIS-CONVENTIONS</Convention>
    </Conventions>
  </ParConversion>
</DiscountCurve>
```

**Instrument Types**:
- `DEP`: Cash deposit
- `FRA`: Forward Rate Agreement
- `FUT`: Interest rate future
- `OIS`: Overnight Indexed Swap
- `IRS`: Interest Rate Swap
- `BS`: Basis Swap
- `CDS`: Credit Default Swap
- `ZIS`: Zero-Inflation Swap

**Advanced Options**:

```xml
<ParConversion>
  <Instruments>DEP,FRA,IRS,IRS,IRS,IRS,IRS,IRS,IRS</Instruments>
  <SingleCurve>false</SingleCurve>

  <!-- Specify discount curve for dual-curve setup -->
  <DiscountCurve>EUR-EONIA</DiscountCurve>

  <!-- For cross-currency instruments -->
  <OtherCurrency>USD</OtherCurrency>

  <Conventions>
    <Convention id="DEP">EUR-EURIBOR-CONVENTIONS</Convention>
    <Convention id="FRA">EUR-FRA-CONVENTIONS</Convention>
    <Convention id="IRS">EUR-6M-SWAP-CONVENTIONS</Convention>
  </Conventions>
</ParConversion>
```

### 2. Cross-Gamma Filtering

**Purpose**: Reduce computational cost by limiting cross-gamma calculations

**Problem**:
- For n risk factors, full cross-gamma requires n×(n-1)/2 combinations
- For 100 factors: 4,950 cross-gammas
- Most cross-gammas are negligible

**Solution**: Specify which cross-gamma pairs to compute

**Example**:
```xml
<CrossGammaFilter>
  <!-- Same-curve cross-gammas only -->
  <Pair>DiscountCurve/EUR,DiscountCurve/EUR</Pair>
  <Pair>DiscountCurve/USD,DiscountCurve/USD</Pair>
  <Pair>IndexCurve/EUR-EURIBOR-6M,IndexCurve/EUR-EURIBOR-6M</Pair>

  <!-- Cross-currency basis risk -->
  <Pair>DiscountCurve/EUR,DiscountCurve/USD</Pair>

  <!-- FX-Interest rate cross risk -->
  <Pair>FXSpot/EURUSD,DiscountCurve/EUR</Pair>
  <Pair>FXSpot/EURUSD,DiscountCurve/USD</Pair>
</CrossGammaFilter>
```

**Format**: `RiskFactorType/Identifier`

**Wildcard Matching**: Not directly supported; must list all pairs explicitly

**Impact**:
- Filtered: Only specified pairs computed
- Unfiltered (default): All pairs computed

### 3. Model Recalibration

**Purpose**: Optionally recalibrate model parameters for each shifted scenario

**Trade-off**:
- **Recalibrate = true**: More accurate (models fit shifted market), but slower
- **Recalibrate = false** (default): Faster, but model parameters unchanged

**Configuration**:
```cpp
SensitivityAnalysis analysis(
    portfolio, market, config, engineData, scenarioData,
    true  // recalibrateModels
);
```

**Use Cases for Recalibration**:
- Models with calibrated parameters (Heston, SABR, etc.)
- When model fit is critical for pricing
- Regulatory calculations requiring market-consistent models

**Use Cases for No Recalibration**:
- Simple models (Black-Scholes with constant vol)
- Fast sensitivity calculations
- When model parameters are fixed/given

### 4. Scenario Simulation Market

**Purpose**: Efficiently manage market data for multiple scenarios

**Class**: [ScenarioSimMarket](../../../OREAnalytics/orea/scenario/scenariosimmarket.hpp)

**How It Works**:

```
Base Market (TodaysMarket)
         ↓
ScenarioSimMarket (wrapper)
         ↓
For each scenario:
    ├─ Load scenario data
    ├─ Update market quotes
    ├─ Rebuild affected curves/surfaces
    └─ Provide to pricing engines
```

**Optimization**:
- Only rebuilds affected market objects
- Caches unchanged objects
- Supports incremental updates

**Configuration**: Via `simulation.xml` or `scenariosimmarket.xml`

### 5. Sensitivity Calculator

**Purpose**: Compute sensitivities from scenario NPVs

**Class**: [SensitivityCalculator](../../../OREAnalytics/orea/engine/sensitivitycalculator.hpp)

**Calculations**:

```cpp
// Delta (Forward scheme)
delta = (NPV_up - NPV_base) / shift_size

// Delta (Central scheme)
delta = (NPV_up - NPV_down) / (2 * shift_size)

// Gamma
gamma = (NPV_up - 2*NPV_base + NPV_down) / (shift_size^2)

// Cross-Gamma
cross_gamma = (NPV_up1_up2 - NPV_up1_base - NPV_base_up2 + NPV_base_base)
              / (shift_size_1 * shift_size_2)
```

**T0 vs Future Dates**:
- **T0 (Standard)**: Sensitivities at current valuation date
- **Future Dates**: Conditional sensitivities at future simulation dates (for XVA)

---

## Examples

### Example 1: Basic Interest Rate Sensitivity

**Objective**: Compute EUR interest rate sensitivities for a swap portfolio

**Portfolio**: 10 EUR fixed-float swaps

**Configuration** (`sensitivity.xml`):
```xml
<?xml version="1.0"?>
<SensitivityAnalysis>
  <DiscountCurves>
    <DiscountCurve ccy="EUR">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>  <!-- 1 bp -->
      <ShiftScheme>Forward</ShiftScheme>
      <ShiftTenors>1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y</ShiftTenors>
    </DiscountCurve>
  </DiscountCurves>

  <IndexCurves>
    <IndexCurve index="EUR-EURIBOR-6M">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y</ShiftTenors>
    </IndexCurve>
  </IndexCurves>
</SensitivityAnalysis>
```

**Expected Output**:
- 18 scenarios (9 discount + 9 index, each UP only)
- Sensitivities to each tenor point
- Gamma sensitivities (if computed)

**Runtime**: ~10 seconds for 10 swaps × 18 scenarios

### Example 2: Multi-Asset Sensitivity with Par Conversion

**Objective**: FX option portfolio with EUR, USD, EURUSD

**Configuration**:
```xml
<SensitivityAnalysis>
  <!-- EUR Discount Curve with Par Conversion -->
  <DiscountCurves>
    <DiscountCurve ccy="EUR">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>1Y,2Y,5Y,10Y</ShiftTenors>
      <ParConversion>
        <Instruments>OIS,OIS,OIS,OIS</Instruments>
        <SingleCurve>true</SingleCurve>
        <Conventions>
          <Convention id="OIS">EUR-OIS-CONVENTIONS</Convention>
        </Conventions>
      </ParConversion>
    </DiscountCurve>

    <DiscountCurve ccy="USD">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>1Y,2Y,5Y,10Y</ShiftTenors>
      <ParConversion>
        <Instruments>OIS,OIS,OIS,OIS</Instruments>
        <SingleCurve>true</SingleCurve>
        <Conventions>
          <Convention id="OIS">USD-OIS-CONVENTIONS</Convention>
        </Conventions>
      </ParConversion>
    </DiscountCurve>
  </DiscountCurves>

  <!-- FX Spot -->
  <FxSpots>
    <FxSpot ccypair="EURUSD">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
    </FxSpot>
  </FxSpots>

  <!-- FX Volatility -->
  <FxVolatilities>
    <FxVolatility ccypair="EURUSD">
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>
      <ShiftExpiries>1M,3M,6M,1Y,2Y</ShiftExpiries>
      <ShiftStrikes/>  <!-- ATM only -->
    </FxVolatility>
  </FxVolatilities>
</SensitivityAnalysis>
```

**Scenarios**:
- EUR discount: 4 tenors
- USD discount: 4 tenors
- FX spot: 1
- FX vol: 5 expiries
- **Total**: 14 scenarios (28 with Central scheme)

**Output Files**:
- `sensitivity.csv`: Zero-rate sensitivities
- `sensitivitypar.csv`: Par OIS sensitivities

### Example 3: Comprehensive Multi-Asset Portfolio

**Objective**: Full FRTB-style sensitivity for complex portfolio

**Asset Classes**: IR, FX, EQ, Credit

**Configuration** (abbreviated):
```xml
<SensitivityAnalysis>
  <!-- Interest Rates: EUR, USD, GBP -->
  <DiscountCurves>
    <!-- 3 currencies × 10 tenors = 30 scenarios -->
  </DiscountCurves>

  <!-- FX: 3 currency pairs -->
  <FxSpots>
    <!-- 3 pairs = 3 scenarios -->
  </FxSpots>

  <FxVolatilities>
    <!-- 3 pairs × 6 expiries = 18 scenarios -->
  </FxVolatilities>

  <!-- Equity: 5 indices -->
  <EquitySpots>
    <!-- 5 equities = 5 scenarios -->
  </EquitySpots>

  <EquityVolatilities>
    <!-- 5 equities × 8 expiries = 40 scenarios -->
  </EquityVolatilities>

  <!-- Credit: 10 names -->
  <CreditCurves>
    <!-- 10 names × 7 tenors = 70 scenarios -->
  </CreditCurves>

  <!-- Volatilities -->
  <SwaptionVolatilities>
    <!-- 3 currencies × 6 expiries × 4 terms = 72 scenarios -->
  </SwaptionVolatilities>

  <!-- Total: ~250 scenarios -->
  <!-- With Central scheme: ~500 scenarios -->

  <!-- Cross-Gamma Filter to reduce cost -->
  <CrossGammaFilter>
    <Pair>DiscountCurve/EUR,DiscountCurve/EUR</Pair>
    <Pair>DiscountCurve/USD,DiscountCurve/USD</Pair>
    <Pair>DiscountCurve/GBP,DiscountCurve/GBP</Pair>
  </CrossGammaFilter>
</SensitivityAnalysis>
```

**Runtime Estimate**:
- Portfolio: 500 trades
- Scenarios: 250 (Forward) or 500 (Central)
- Total valuations: 125,000 to 250,000
- Time: 10-30 minutes (depending on trade complexity)

### Example 4: XVA Sensitivity

**Objective**: CVA sensitivities for counterparty exposure

**Configuration**:
```xml
<Analytics>
  <Analytic type="xvasensitivity">
    <Parameter name="sensitivityConfigFile">Input/xvasensitivity.xml</Parameter>
    <Parameter name="baseCurrency">EUR</Parameter>
  </Analytic>
</Analytics>
```

**xvasensitivity.xml**:
```xml
<SensitivityAnalysis>
  <!-- Only credit spreads for CVA sensitivity -->
  <CreditCurves>
    <CreditCurve name="COUNTERPARTY_A">
      <Currency>USD</Currency>
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>1Y,3Y,5Y,7Y,10Y</ShiftTenors>
    </CreditCurve>
  </CreditCurves>

  <!-- Interest rates affect discounting in CVA -->
  <DiscountCurves>
    <DiscountCurve ccy="EUR">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>1Y,2Y,5Y,10Y</ShiftTenors>
    </DiscountCurve>
  </DiscountCurves>
</SensitivityAnalysis>
```

**Output**:
- CVA delta to counterparty credit spreads
- CVA delta to interest rates
- Netting set level sensitivities

---

## Integration Flow

### End-to-End Sensitivity Calculation

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: Configuration Loading                               │
├─────────────────────────────────────────────────────────────┤
│ 1. Load ore.xml (main config)                               │
│ 2. Load sensitivity.xml (risk factor shifts)                │
│ 3. Load pricingengine.xml (engine selection)                │
│ 4. Load todaysmarket.xml (market object config)             │
│ 5. Load portfolio.xml (trades)                              │
│ 6. Load market data (CSV files)                             │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Market Building                                     │
├─────────────────────────────────────────────────────────────┤
│ 1. Parse market data quotes                                 │
│ 2. Bootstrap yield curves                                   │
│ 3. Build volatility surfaces                                │
│ 4. Construct TodaysMarket object                            │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: Portfolio Building                                  │
├─────────────────────────────────────────────────────────────┤
│ 1. Parse trades from portfolio.xml                          │
│ 2. Build EngineFactory with pricing engines                 │
│ 3. For each trade: trade->build(engineFactory)              │
│ 4. Compute base NPVs                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: Scenario Generation                                 │
├─────────────────────────────────────────────────────────────┤
│ SensitivityScenarioGenerator::generateScenarios()           │
│                                                              │
│ For each risk factor type:                                  │
│   For each configured shift:                                │
│     Create UP scenario (always)                             │
│     Create DOWN scenario (if Central or Backward)           │
│                                                              │
│ Result: Vector of scenarios (100-1000 typical)              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: Scenario Simulation Market Setup                    │
├─────────────────────────────────────────────────────────────┤
│ ScenarioSimMarket initialization:                           │
│   - Wraps TodaysMarket                                      │
│   - Prepares for scenario application                       │
│   - Sets up curve/surface rebuilding logic                  │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: Scenario Valuation Loop                             │
├─────────────────────────────────────────────────────────────┤
│ For each scenario:                                          │
│   1. Apply scenario to ScenarioSimMarket                    │
│   2. Rebuild affected yield curves/vol surfaces             │
│   3. Optionally recalibrate models (if flag set)            │
│   4. For each trade:                                        │
│      - Reprice with shifted market                          │
│      - Store NPV in scenario cube                           │
│   5. Record scenario completion                             │
│                                                              │
│ Progress: [################        ] 75% (187/250)          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 7: Sensitivity Calculation                             │
├─────────────────────────────────────────────────────────────┤
│ SensitivityCalculator::calculate()                          │
│                                                              │
│ For each trade:                                             │
│   For each risk factor:                                     │
│     Extract NPV_base, NPV_up, NPV_down                      │
│     Compute delta = f(NPV_up, NPV_down, shift_size)         │
│     If gamma enabled: compute gamma                         │
│   If cross-gamma filter: compute cross-gammas               │
│                                                              │
│ Store in SensitivityCube                                    │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 8: Par Conversion (Optional)                           │
├─────────────────────────────────────────────────────────────┤
│ ParSensitivityAnalysis::convert()                           │
│                                                              │
│ For each curve with ParConversion config:                   │
│   1. Build Jacobian matrix:                                 │
│      For each par instrument:                               │
│        - Bump par rate                                      │
│        - Re-bootstrap curve                                 │
│        - Measure zero rate changes                          │
│        - Store in Jacobian J[i][j]                          │
│   2. Invert Jacobian: J_inv                                 │
│   3. Transform sensitivities:                               │
│      delta_par = J_inv × delta_zero                         │
│                                                              │
│ Store in par sensitivity cube                               │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 9: Report Generation                                   │
├─────────────────────────────────────────────────────────────┤
│ 1. Write sensitivity.csv (zero sensitivities)               │
│ 2. Write sensitivitypar.csv (par sensitivities)             │
│ 3. Write cross-gamma reports (if computed)                  │
│ 4. Generate summary statistics                              │
│ 5. Optional: Export to database/risk system                 │
└─────────────────────────────────────────────────────────────┘
```

### Key Integration Points

#### 1. Market Data Loading

**Flow**:
```
CSV Files (marketdata.csv, fixings.csv)
    ↓
Loader (CSVLoader or BinaryLoader)
    ↓
TodaysMarket::TodaysMarket()
    ↓
Curve bootstrapping
    ↓
ScenarioSimMarket wrapping
```

#### 2. Portfolio Building

**Flow**:
```
portfolio.xml
    ↓
Portfolio::fromXML()
    ↓
For each trade: Trade::fromXML()
    ↓
EngineFactory::build(trade)
    ↓
Attach pricing engine to trade
    ↓
trade->instrument()->NPV()
```

#### 3. Scenario Application

**Key Class**: ScenarioSimMarket

**Method**:
```cpp
void ScenarioSimMarket::applyScenario(
    const boost::shared_ptr<Scenario>& scenario
) {
    // Update market quotes
    for (auto& [key, value] : scenario->data()) {
        quotes_[key]->setValue(value);
    }

    // Rebuild affected curves/surfaces
    update();
}
```

#### 4. Parallel Execution

ORE supports parallel scenario valuation:

```cpp
SensitivityAnalysis analysis(...);
analysis.setParallelScenarios(true);
analysis.setNumThreads(8);
analysis.generateSensitivities();
```

**Benefits**:
- 8× speedup on 8-core machine (typical)
- Linear scaling up to ~16 cores
- Memory usage increases linearly with threads

---

## File Locations Reference

| Component | File Path |
|-----------|-----------|
| **Core Classes** | |
| SensitivityAnalysis | [OREAnalytics/orea/engine/sensitivityanalysis.hpp](../../../OREAnalytics/orea/engine/sensitivityanalysis.hpp) |
| SensitivityScenarioData | [OREAnalytics/orea/scenario/sensitivityscenariodata.hpp](../../../OREAnalytics/orea/scenario/sensitivityscenariodata.hpp) |
| SensitivityScenarioGenerator | [OREAnalytics/orea/scenario/sensitivityscenariogenerator.hpp](../../../OREAnalytics/orea/scenario/sensitivityscenariogenerator.hpp) |
| SensitivityCube | [OREAnalytics/orea/cube/sensitivitycube.hpp](../../../OREAnalytics/orea/cube/sensitivitycube.hpp) |
| SensitivityCalculator | [OREAnalytics/orea/engine/sensitivitycalculator.hpp](../../../OREAnalytics/orea/engine/sensitivitycalculator.hpp) |
| ParSensitivityAnalysis | [OREAnalytics/orea/engine/parsensitivityanalysis.hpp](../../../OREAnalytics/orea/engine/parsensitivityanalysis.hpp) |
| **Enums and Types** | |
| ShiftType, ShiftScheme | [QuantExt/qle/termstructures/scenario.hpp](../../../QuantExt/qle/termstructures/scenario.hpp) |
| RiskFactorKey | [QuantExt/qle/termstructures/scenario.hpp](../../../QuantExt/qle/termstructures/scenario.hpp) |
| **Analytics** | |
| SensitivityStressAnalytic | [OREAnalytics/orea/app/analytics/sensitivitystressanalytic.hpp](../../../OREAnalytics/orea/app/analytics/sensitivitystressanalytic.hpp) |
| XvaSensitivityAnalytic | [OREAnalytics/orea/app/analytics/xvasensitivityanalytic.hpp](../../../OREAnalytics/orea/app/analytics/xvasensitivityanalytic.hpp) |
| **Examples** | |
| Example 15 (Basic) | [Examples/Legacy/Example_15/Input/sensitivity.xml](../../../Examples/Legacy/Example_15/Input/sensitivity.xml) |
| Market Risk Example | [Examples/MarketRisk/Input/sensitivity.xml](../../../Examples/MarketRisk/Input/sensitivity.xml) |
| **Tests** | |
| Sensitivity Test Suite | [OREAnalytics/test/sensitivityanalysis.cpp](../../../OREAnalytics/test/sensitivityanalysis.cpp) |

---

## Quick Reference Card

### Minimal Configuration

```xml
<SensitivityAnalysis>
  <DiscountCurves>
    <DiscountCurve ccy="EUR">
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>
      <ShiftTenors>1Y,5Y,10Y</ShiftTenors>
    </DiscountCurve>
  </DiscountCurves>
</SensitivityAnalysis>
```

### Typical Shift Sizes

| Risk Factor Type | ShiftType | Typical ShiftSize | Units |
|------------------|-----------|-------------------|-------|
| Interest Rates | Absolute | 0.0001 | 1 basis point |
| Credit Spreads | Absolute | 0.0001 | 1 basis point |
| FX Spots | Relative | 0.01 | 1% |
| Equity Prices | Relative | 0.01 | 1% |
| Volatilities | Relative | 0.01 | 1% (of vol level) |
| Inflation Rates | Absolute | 0.0001 | 1 basis point |

### Parameter Checklist

- [ ] ShiftType specified (Absolute or Relative)
- [ ] ShiftSize specified (appropriate for risk factor)
- [ ] ShiftTenors specified (for curves)
- [ ] ShiftExpiries specified (for volatilities)
- [ ] ShiftScheme specified or defaulted (Forward recommended)
- [ ] ParConversion configured (if needed)
- [ ] CrossGammaFilter specified (if needed)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-12
**ORE Version**: v13+
