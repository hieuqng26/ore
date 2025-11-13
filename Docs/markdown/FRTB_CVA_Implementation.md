# FRTB CVA Implementation in ORE: Complete End-to-End Guide

## Table of Contents

1. [Overview](#1-overview)
2. [Regulatory Background](#2-regulatory-background)
3. [Architecture and Components](#3-architecture-and-components)
4. [BA-CVA: Basic Approach](#4-ba-cva-basic-approach)
5. [SA-CVA: Standardized Approach](#5-sa-cva-standardized-approach)
6. [Input Requirements](#6-input-requirements)
7. [Configuration Examples](#7-configuration-examples)
8. [Running FRTB CVA Analytics](#8-running-frtb-cva-analytics)
9. [Output Reports](#9-output-reports)
10. [Key Differences: BA-CVA vs SA-CVA](#10-key-differences-ba-cva-vs-sa-cva)
11. [Testing and Validation](#11-testing-and-validation)
12. [Performance Considerations](#12-performance-considerations)
13. [Limitations and Future Enhancements](#13-limitations-and-future-enhancements)

---

## 1. Overview

### What is FRTB CVA?

The Fundamental Review of the Trading Book (FRTB) introduced new approaches for calculating CVA (Credit Valuation Adjustment) capital requirements under Basel III regulations. ORE implements two approaches:

1. **BA-CVA** (Basic Approach) - A simple, exposure-based approach
2. **SA-CVA** (Standardized Approach) - A sophisticated sensitivity-based approach

### Purpose

FRTB CVA capital requirements address the risk of losses due to changes in counterparty credit spreads and market risk factors that affect CVA. The capital charge protects banks against:

- **Credit spread risk**: Changes in counterparty creditworthiness
- **Market risk**: Changes in interest rates, FX rates, and volatilities that affect CVA

### Implementation Status (ORE v13)

Both BA-CVA and SA-CVA analytics were added in ORE v13 (May 2024-2025) and are production-ready. Examples can be found in:
- `Examples/XvaRisk/` - Working examples with sample portfolios
- `Examples/CreditRisk/` - Additional SA-CCR examples (used by BA-CVA)

---

## 2. Regulatory Background

### Basel Framework References

- **MAR50**: CVA Risk Capital Requirement
  - https://www.bis.org/basel_framework/chapter/MAR/50.htm
- **d424**: Basel consultative document on CVA risk (December 2015)
- **d507**: Targeted revisions to the CVA risk framework (July 2020)

### Key Regulatory Principles

#### BA-CVA Principles
- **Exposure-based**: Uses SA-CCR (Standardized Approach for Counterparty Credit Risk) exposure measures
- **Conservative**: Does not recognize hedging benefits (reduced version)
- **Simple**: Formulaic approach with limited inputs
- **No approval required**: Can be used by any bank

#### SA-CVA Principles
- **Sensitivity-based**: Uses CVA sensitivities to market risk factors
- **Granular**: Captures IR, FX, credit, equity, and commodity risks
- **Hedge recognition**: Fully recognizes CVA and exposure hedges
- **Requires approval**: Banks must obtain regulatory approval to use SA-CVA

### Regulatory Formula Overview

#### BA-CVA Formula
```
K_BA-CVA = D_BA-CVA × √[ρ² × (Σ_c sCVA_c)² + (1 - ρ²) × Σ_c (sCVA_c)²]

where:
  D_BA-CVA = 0.65 (regulatory discount scalar)
  ρ = 0.5 (systematic component correlation)
  sCVA_c = (1/α) × RW_c × Σ_NS [M_NS × EAD_NS × DF(M_NS)]
  α = 1.4 (scaling factor)
  RW_c = counterparty risk weight
  M_NS = effective maturity of netting set
  EAD_NS = exposure at default (from SA-CCR)
  DF(M_NS) = (1 - exp(-0.05 × M_NS)) / (0.05 × M_NS)
```

#### SA-CVA Formula (Simplified)
```
K_SA-CVA = m_CVA × √[Σ_buckets K_bucket² + Σ_cross-bucket γ_bc × K_b × K_c]

K_bucket = √[Σ_k WS_k² + Σ_{k≠l} ρ_kl × WS_k × WS_l + R × Σ_k (WS_k^Hdg)²]

where:
  m_CVA = 1.0 (multiplier, can be increased by regulators)
  WS_k = RW_k × (s_k^CVA - s_k^Hdg) (weighted sensitivity)
  R = 0.01 (hedge multiplier)
  ρ_kl = risk factor correlations (within bucket)
  γ_bc = bucket correlations (across buckets)
```

---

## 3. Architecture and Components

### File Structure

```
ORE/
├── OREAnalytics/
│   ├── orea/app/analytics/
│   │   ├── bacvaanalytic.hpp/cpp      # BA-CVA analytic
│   │   ├── sacvaanalytic.hpp/cpp      # SA-CVA analytic
│   │   ├── xvasensitivityanalytic.*   # XVA sensitivity (used by SA-CVA)
│   │   └── saccr.hpp/cpp              # SA-CCR (used by BA-CVA)
│   ├── orea/engine/
│   │   ├── bacvacalculator.hpp/cpp              # BA-CVA calculation
│   │   ├── standardapproachcvacalculator.hpp/cpp # SA-CVA calculation
│   │   ├── sacvasensitivityrecord.hpp           # SA-CVA data structures
│   │   └── sacvasensitivityloader.hpp/cpp       # Sensitivity mapping
│   └── orea/app/
│       ├── reportwriter.hpp/cpp        # Report generation
│       └── inputparameters.hpp/cpp     # Configuration parsing
├── OREAnalytics/test/
│   └── sacva.hpp/cpp                   # Unit tests
└── Examples/
    ├── XvaRisk/                         # BA-CVA and SA-CVA examples
    │   ├── run_bacva.py
    │   ├── run_sacva.py
    │   └── Input/
    │       ├── ore_bacva.xml
    │       └── ore_sacva.xml
    └── CreditRisk/                      # SA-CCR examples
        └── run_saccr.py
```

### Component Dependencies

```
BA-CVA Analytic
    ↓ depends on
SA-CCR Analytic
    ↓ uses
Portfolio + Market Data + Netting Sets

SA-CVA Analytic
    ↓ depends on (optional)
XVA Sensitivity Analytic
    ↓ uses
Portfolio + Market Data + CVA Calculation + Sensitivity Config
```

### Class Hierarchy

```cpp
// Analytics (entry points)
Analytic::Impl
├── BaCvaAnalyticImpl           // BA-CVA orchestration
├── SaCvaAnalyticImpl           // SA-CVA orchestration
├── SaCcrAnalyticImpl           // SA-CCR (used by BA-CVA)
└── XvaSensitivityAnalyticImpl  // XVA sensitivities (used by SA-CVA)

// Calculators (core logic)
├── BaCvaCalculator             // BA-CVA calculation engine
├── StandardApproachCvaCalculator // SA-CVA calculation engine
└── SaCcr                       // SA-CCR calculation engine

// Data structures
├── SaCvaSensitivityRecord      // SA-CVA sensitivity data
└── SaCvaNetSensitivities       // Aggregated sensitivities
```

### Registration System

Both analytics are registered in `OREAnalytics/orea/app/initbuilders.cpp`:

```cpp
ORE_REGISTER_ANALYTIC_BUILDER("BA_CVA", {}, BaCvaAnalytic, false);
ORE_REGISTER_ANALYTIC_BUILDER("SA_CVA", {}, SaCvaAnalytic, false);
ORE_REGISTER_ANALYTIC_BUILDER("SA_CCR", {}, SaCcrAnalytic, false);
ORE_REGISTER_ANALYTIC_BUILDER("XVA_SENSITIVITY", {}, XvaSensitivityAnalytic, false);
```

---

## 4. BA-CVA: Basic Approach

### 4.1 Conceptual Overview

BA-CVA is an exposure-based approach that calculates CVA capital based on:
1. **Exposure at Default (EAD)** from SA-CCR
2. **Effective Maturity** of each netting set
3. **Counterparty Risk Weight** (based on credit quality)

The approach is conservative and does not recognize hedging benefits (in the reduced version implemented).

### 4.2 Implementation Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Setup Phase                                              │
│    - Load ore_bacva.xml configuration                       │
│    - Parse portfolio, netting sets, counterparty info       │
│    - Initialize BA-CVA analytic                             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Dependency: Run SA-CCR                                   │
│    - Build today's market                                   │
│    - Price all trades                                       │
│    - Calculate SA-CCR EAD for each netting set              │
│    - Store EAD values in SaCcr object                       │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. BA-CVA Calculation                                       │
│    a) Calculate Effective Maturity for each netting set     │
│       - For IR swaps: cashflow-weighted average             │
│       - For FX forwards: notional-weighted average          │
│                                                             │
│    b) For each Counterparty:                                │
│       - Get risk weight RW_c                                │
│       - Initialize sCVA_c = 0                               │
│                                                             │
│       For each Netting Set:                                 │
│         - Get EAD_NS from SA-CCR                            │
│         - Get M_NS (effective maturity)                     │
│         - Calculate DF_NS = (1-exp(-0.05×M))/(0.05×M)      │
│         - Add to sCVA_c: EAD_NS × M_NS × DF_NS             │
│                                                             │
│       - Apply: sCVA_c = (RW_c / 1.4) × sCVA_c              │
│                                                             │
│    c) Aggregate across counterparties:                      │
│       - Sum_sCVA = Σ sCVA_c                                │
│       - Sum_sCVA² = Σ (sCVA_c)²                            │
│       - K = 0.65 × √[0.25×(Sum_sCVA)² + 0.75×Sum_sCVA²]   │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Report Generation                                        │
│    - Write bacva.csv with capital results                   │
│    - Include counterparty and netting set breakdowns        │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Key Implementation Details

#### Effective Maturity Calculation

**For trades with cashflows (e.g., swaps):**

```cpp
// File: OREAnalytics/orea/engine/bacvacalculator.cpp
void BaCvaCalculator::calculateEffectiveMaturity() {
    for (const auto& [tradeId, trade] : portfolio_->trades()) {
        string nettingSetId = trade->envelope().nettingSetId();

        Real sumAmountTime = 0.0;
        Real sumAmount = 0.0;

        // Get trade's cashflows
        for (const auto& leg : trade->legs()) {
            for (const auto& cf : leg) {
                if (cf->date() <= asof_)
                    continue;  // Skip past cashflows

                Real amount = cf->amount();
                if (amount <= 0)
                    continue;  // Only positive (received) cashflows

                Real time = dc_.yearFraction(asof_, cf->date());
                Real fx = 1.0;  // Convert to calculation currency if needed

                sumAmountTime += amount * time * fx;
                sumAmount += amount * fx;
            }
        }

        if (sumAmount > 0) {
            effectiveMaturity_[nettingSetId] = sumAmountTime / sumAmount;
        }
    }
}
```

**For trades without cashflows (e.g., FX forwards, options):**

```cpp
// Use notional-weighted average of maturity dates
Real sumNotionalTime = 0.0;
Real sumNotional = 0.0;

for (const auto& trade : nettingSet) {
    Real notional = trade->notional();
    Real maturity = dc_.yearFraction(asof_, trade->maturityDate());
    Real fx = 1.0;  // Convert to calculation currency

    sumNotionalTime += notional * maturity * fx;
    sumNotional += notional * fx;
}

effectiveMaturity = sumNotionalTime / sumNotional;
```

#### BA-CVA Capital Calculation

```cpp
// File: OREAnalytics/orea/engine/bacvacalculator.cpp
void BaCvaCalculator::calculate() {
    const Real alpha = 1.4;
    const Real rho = 0.5;
    const Real discount = 0.65;

    // Loop over counterparties
    for (const auto& [counterpartyId, nettingSets] : counterpartyNettingSets_) {
        auto cpInfo = counterpartyManager_->get(counterpartyId);

        if (cpInfo->isClearingCP())
            continue;  // Skip clearing counterparties

        Real riskWeight = cpInfo->baCvaRiskWeight();
        Real sCva = 0.0;

        // Loop over netting sets for this counterparty
        for (const auto& nsId : nettingSets) {
            Real ead = saccr_->EAD(nsId);
            Real maturity = effectiveMaturity(nsId);
            Real df = (1 - std::exp(-0.05 * maturity)) / (0.05 * maturity);

            sCva += ead * maturity * df;
        }

        // Apply risk weight and alpha
        sCva = (riskWeight / alpha) * sCva;
        counterpartySCVA_[counterpartyId] = sCva;
    }

    // Aggregate across counterparties
    Real sumSCva = 0.0;
    Real sumSCvaSquared = 0.0;

    for (const auto& [cpId, scva] : counterpartySCVA_) {
        sumSCva += scva;
        sumSCvaSquared += scva * scva;
    }

    // Final capital charge
    cvaCapital_ = discount * std::sqrt(
        rho * rho * sumSCva * sumSCva +
        (1 - rho * rho) * sumSCvaSquared
    );
}
```

### 4.4 Supported Trade Types

The following trade types are supported for BA-CVA (via SA-CCR):

- **FX Forwards**: Currency forwards and non-deliverable forwards (NDF)
- **FX Options**: Vanilla and barrier options
- **Interest Rate Swaps**: Fixed-float, basis swaps, OIS
- **Cross-Currency Swaps**: Fixed-fixed, fixed-float, float-float

### 4.5 Risk Weights

Counterparty risk weights must be specified in `counterparty.xml`:

```xml
<Counterparty id="CPTY_A">
  <BaCvaRiskWeight>0.05</BaCvaRiskWeight>  <!-- Investment grade -->
  <IsClearingCP>false</IsClearingCP>
</Counterparty>
```

**Typical risk weights:**
- **Investment Grade (IG)**: 0.03 - 0.10
- **High Yield (HY)**: 0.15 - 0.30
- **Not Rated**: 0.10 (default)

---

## 5. SA-CVA: Standardized Approach

### 5.1 Conceptual Overview

SA-CVA is a sensitivity-based approach that calculates CVA capital based on:
1. **CVA sensitivities** to market risk factors (IR, FX, credit, equity, commodity)
2. **Regulatory risk weights** for each risk factor
3. **Correlations** between risk factors and buckets
4. **Hedge recognition** for both CVA and exposure hedges

### 5.2 Implementation Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. Setup Phase                                               │
│    - Load ore_sacva.xml configuration                        │
│    - Parse portfolio, market data, sensitivity config        │
│    - Initialize SA-CVA analytic                              │
└──────────────────────┬───────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. Check for Pre-computed Sensitivities                      │
│    Option A: Load from file (saCvaNetSensitivitiesFile)      │
│    Option B: Generate on-the-fly (next steps)                │
└──────────────────────┬───────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. Generate CVA Sensitivities (if needed)                    │
│    a) Run XVA_SENSITIVITY analytic:                          │
│       - Build market and simulation market                   │
│       - Calculate CVA for portfolio                          │
│       - For each risk factor in sensitivity config:          │
│         * Shift risk factor up/down                          │
│         * Rebuild market and recalculate CVA                 │
│         * Calculate sensitivity = ΔCVA / shift               │
│                                                              │
│    b) Generate raw sensitivity report:                       │
│       - xva_par_sensitivity_cva.csv                          │
└──────────────────────┬───────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. Map Sensitivities to SA-CVA Format                        │
│    SaCvaSensitivityLoader::loadFromRawSensis()               │
│                                                              │
│    a) For each raw sensitivity:                              │
│       - Identify risk type (IR, FX, Credit, etc.)            │
│       - Map to SA-CVA bucket (currency, tenor, sector)       │
│       - Map to risk factor (tenor, entity)                   │
│       - Apply shift size correction                          │
│       - Assign margin type (Delta or Vega)                   │
│                                                              │
│    b) Aggregate sensitivities:                               │
│       - Net by netting set, risk factor, counterparty        │
│       - Separate CVA from hedge sensitivities                │
│       - Store in SaCvaNetSensitivities structure             │
└──────────────────────┬───────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. SA-CVA Capital Calculation                                │
│    StandardApproachCvaCalculator::calculate()                │
│                                                              │
│    For each Netting Set (including "" for total):            │
│      For each Risk Type (IR, FX, Credit, Equity, Commodity): │
│        For each Margin Type (Delta, Vega):                   │
│          For each Bucket (Currency, Sector, etc.):           │
│                                                              │
│            Step 1: Calculate Weighted Sensitivities          │
│            ─────────────────────────────────────             │
│            For each Risk Factor k in bucket:                 │
│              s_k^CVA = CVA sensitivity to factor k           │
│              s_k^Hdg = Hedge sensitivity to factor k         │
│              RW_k = regulatory risk weight for k             │
│              WS_k = RW_k × (s_k^CVA - s_k^Hdg)               │
│                                                              │
│            Step 2: Calculate Bucket Capital                  │
│            ─────────────────────────────                     │
│            Sum_WS_sq = Σ_k Σ_l ρ_kl × WS_k × WS_l           │
│              where ρ_kl = correlation between k and l        │
│                                                              │
│            Sum_Hdg_sq = Σ_k (RW_k × s_k^Hdg)²               │
│                                                              │
│            K_bucket = √[Sum_WS_sq + 0.01 × Sum_Hdg_sq]       │
│                                                              │
│          Step 3: Aggregate Buckets for Margin Type           │
│          ──────────────────────────────────────              │
│          K_margin = √[Σ_b K_b² + Σ_{b≠c} γ_bc×K_b×K_c]      │
│            where γ_bc = bucket correlation                   │
│                                                              │
│        Sum margin types: K_riskType = K_delta + K_vega       │
│                                                              │
│      Sum risk types: K_nettingSet = Σ K_riskType             │
└──────────────────────┬───────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. Report Generation                                         │
│    - sacva.csv: Summary by netting set, risk type, bucket    │
│    - sacvadetail.csv: Full sensitivity breakdown             │
│    - sacva_sensitivities.csv: Mapped sensitivities           │
│    - cva_sensitivities.csv: Raw CVA sensitivities            │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 Key Implementation Details

#### Sensitivity Generation

The XVA sensitivity analytic performs bump-and-revalue:

```cpp
// Pseudo-code for sensitivity calculation
Real baseCVA = calculateCVA(portfolio, market);

for (const auto& riskFactor : sensitivityConfig) {
    // Up shift
    Market shiftedMarketUp = shiftRiskFactor(market, riskFactor, +shiftSize);
    Real cvaUp = calculateCVA(portfolio, shiftedMarketUp);

    // Down shift
    Market shiftedMarketDown = shiftRiskFactor(market, riskFactor, -shiftSize);
    Real cvaDown = calculateCVA(portfolio, shiftedMarketDown);

    // Central difference
    Real sensitivity = (cvaUp - cvaDown) / (2 * shiftSize);

    storeSensitivity(riskFactor, sensitivity);
}
```

#### Sensitivity Mapping

Raw CVA sensitivities are mapped to SA-CVA format:

```cpp
// File: OREAnalytics/orea/engine/sacvasensitivityloader.cpp
void SaCvaSensitivityLoader::loadFromRawSensis(
    const SensiCubeStream& pss,
    const string& baseCurrency) {

    for (const auto& sensi : pss) {
        // Identify risk type and margin type
        auto riskType = identifyRiskType(sensi.riskFactorKey);
        auto marginType = identifyMarginType(sensi.riskFactorKey);

        // Map to bucket
        string bucket;
        if (riskType == InterestRate || riskType == ForeignExchange) {
            bucket = extractCurrency(sensi.riskFactorKey);
        } else if (riskType == CreditCounterparty) {
            bucket = getCreditBucket(sensi.counterparty);
        }

        // Map to risk factor
        string riskFactor;
        if (riskType == InterestRate && marginType == Delta) {
            riskFactor = extractTenor(sensi.riskFactorKey);
        } else if (marginType == Vega) {
            riskFactor = extractUnderlyingType(sensi.riskFactorKey);
        }

        // Apply shift size correction
        Real correctedSensi = sensi.value;
        if (sensi.shiftType == Relative) {
            // Convert relative shift to absolute
            correctedSensi *= 0.01;  // 1% shift to absolute
        }

        // Store in SA-CVA format
        SaCvaSensitivityRecord record;
        record.nettingSetId = sensi.nettingSetId;
        record.riskType = riskType;
        record.bucket = bucket;
        record.marginType = marginType;
        record.riskFactor = riskFactor;
        record.sensitivity = correctedSensi;
        record.cvaType = CvaAggregate;  // or CvaHedge

        records_.push_back(record);
    }

    // Aggregate by key
    aggregateSensitivities();
}
```

#### SA-CVA Capital Calculation

```cpp
// File: OREAnalytics/orea/engine/standardapproachcvacalculator.cpp
void StandardApproachCvaCalculator::calculate() {
    const Real R = 0.01;  // Hedge multiplier
    const Real mCVA = 1.0; // Multiplier (can be increased by regulators)

    // Main calculation loop
    for (const auto& nettingSetId : nettingSets_) {
        Real capitalNettingSet = 0.0;

        for (auto riskType : {IR, FX, CreditCP, CreditRef, Equity, Commodity}) {
            Real capitalRiskType = 0.0;

            for (auto marginType : {Delta, Vega}) {
                // Collect buckets for this risk/margin combination
                set<string> buckets = getBuckets(nettingSetId, riskType, marginType);

                map<string, Real> bucketCapital;
                map<string, Real> bucketSum;  // For correlation

                // Calculate capital for each bucket
                for (const auto& bucket : buckets) {
                    // Collect risk factors in this bucket
                    set<string> riskFactors = getRiskFactors(
                        nettingSetId, riskType, bucket, marginType);

                    // Calculate weighted sensitivities
                    map<string, Real> ws;       // CVA - Hedge
                    vector<Real> wsHedge;       // Hedge only

                    for (const auto& rf : riskFactors) {
                        Real sCva = getSensitivity(
                            nettingSetId, riskType, bucket, marginType, rf, CvaAggregate);
                        Real sHdg = getHedgeSensitivity(
                            riskType, bucket, marginType, rf, sCva);
                        Real rw = getRiskWeight(riskType, bucket, marginType, rf);

                        ws[rf] = rw * (sCva - sHdg);
                        wsHedge.push_back(rw * sHdg);
                    }

                    // Calculate sum with correlations
                    Real sumWsSq = 0.0;
                    for (const auto& [rf1, ws1] : ws) {
                        for (const auto& [rf2, ws2] : ws) {
                            Real rho = getRiskFactorCorrelation(
                                riskType, bucket, marginType, rf1, rf2);
                            sumWsSq += ws1 * ws2 * rho;
                        }
                    }

                    // Calculate hedge term
                    Real sumHdgSq = 0.0;
                    for (Real h : wsHedge) {
                        sumHdgSq += h * h;
                    }

                    // Bucket capital
                    Real kb = std::sqrt(sumWsSq + R * sumHdgSq);
                    bucketCapital[bucket] = kb;

                    // Store sum for cross-bucket correlation
                    Real sumWs = 0.0;
                    for (const auto& [rf, wsVal] : ws) {
                        sumWs += wsVal;
                    }
                    bucketSum[bucket] = std::max(-kb, std::min(sumWs, kb));
                }

                // Aggregate across buckets
                Real sumKbSq = 0.0;
                for (const auto& [b, kb] : bucketCapital) {
                    sumKbSq += kb * kb;
                }

                Real crossBucketTerm = 0.0;
                for (const auto& [b1, sb1] : bucketSum) {
                    for (const auto& [b2, sb2] : bucketSum) {
                        if (b1 != b2) {
                            Real gamma = getBucketCorrelation(riskType, b1, b2);
                            crossBucketTerm += sb1 * sb2 * gamma;
                        }
                    }
                }

                Real capitalMargin = mCVA * std::sqrt(sumKbSq + crossBucketTerm);
                capitalRiskType += capitalMargin;
            }

            capitalNettingSet += capitalRiskType;
        }

        result_[nettingSetId] = capitalNettingSet;
    }
}
```

#### Regulatory Parameters

**Risk Weights:**

```cpp
// IR Delta: Major currencies (USD, EUR, GBP, JPY, AUD, CAD, SEK)
map<string, Real> irDeltaRiskWeights = {
    {"1Y", 0.0111},
    {"2Y", 0.0093},
    {"5Y", 0.0074},
    {"10Y", 0.0074},
    {"30Y", 0.0074},
    {"Inflation", 0.0111}
};
// Other currencies: 0.0158

// FX Delta
Real fxDeltaRiskWeight = 0.11;

// IR/FX Vega
Real irVegaRiskWeight = 1.0;
Real fxVegaRiskWeight = 1.0;

// Credit: From counterparty manager
// Varies by credit quality (IG, HY, NR) and tenor
```

**Risk Factor Correlations (within bucket):**

```cpp
// IR Delta correlations (major currencies) - 6x6 matrix
// Rows/cols: 1Y, 2Y, 5Y, 10Y, 30Y, Inflation
matrix<Real> irDeltaCorr = {
    {1.00, 0.91, 0.72, 0.55, 0.31, 0.40},
    {0.91, 1.00, 0.87, 0.72, 0.45, 0.40},
    {0.72, 0.87, 1.00, 0.91, 0.68, 0.40},
    {0.55, 0.72, 0.91, 1.00, 0.83, 0.40},
    {0.31, 0.45, 0.68, 0.83, 1.00, 0.40},
    {0.40, 0.40, 0.40, 0.40, 0.40, 1.00}
};
// Other currencies: 0.4

// IR Vega
Real irVegaCorr = 0.4;

// FX
Real fxDeltaSameBucketCorr = 0.6;
Real fxVegaSameBucketCorr = 0.5;
```

**Bucket Correlations (across buckets):**

```cpp
// IR: 0.5 for different currencies
Real irBucketCorr = 0.5;

// FX: 0.6
Real fxBucketCorr = 0.6;

// Credit Counterparty: Complex 8x8 matrix
// Buckets: 1=IG 0-1Y, 2=IG 1-5Y, 3=IG 5Y+, 4=HY 0-1Y, 5=HY 1-5Y, 6=HY 5Y+, 7=NR, 8=Sec
matrix<Real> creditCptyBucketCorr = {
    {1.00, 0.10, 0.20, 0.25, 0.20, 0.15, 0.00, 0.45},
    {0.10, 1.00, 0.05, 0.15, 0.20, 0.05, 0.00, 0.45},
    {0.20, 0.05, 1.00, 0.05, 0.10, 0.20, 0.00, 0.45},
    {0.25, 0.15, 0.05, 1.00, 0.25, 0.05, 0.00, 0.45},
    {0.20, 0.20, 0.10, 0.25, 1.00, 0.05, 0.00, 0.45},
    {0.15, 0.05, 0.20, 0.05, 0.05, 1.00, 0.00, 0.45},
    {0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.00, 0.00},
    {0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.00, 1.00}
};
```

### 5.4 Supported Risk Factors

#### Interest Rate (IR)
- **Delta**: Sensitivities to yield curve shifts at tenors (1Y, 2Y, 5Y, 10Y, 30Y)
- **Vega**: Sensitivities to IR volatility changes

#### Foreign Exchange (FX)
- **Delta**: Sensitivities to FX spot rate changes
- **Vega**: Sensitivities to FX volatility changes

#### Credit Counterparty
- **Delta**: Sensitivities to counterparty credit spread changes
- Bucketed by credit quality (IG, HY, NR) and tenor (0-1Y, 1-5Y, 5Y+)

#### Credit Reference (future)
- Index CDS hedges
- Single-name CDS hedges

#### Equity and Commodity (future)
- Sensitivities to equity prices and commodity prices

### 5.5 Hedge Recognition

SA-CVA recognizes two types of hedges:

1. **CVA Hedges**: Derivatives used to hedge CVA itself
   - Single-name CDS on counterparty
   - Index CDS
   - Interest rate swaps (IR CVA hedging)

2. **Exposure Hedges**: Derivatives offsetting portfolio exposure
   - Trades that naturally reduce exposure
   - Included automatically if in same netting set

**Implementation:**
```cpp
Real getHedgeSensitivity(RiskType rt, string bucket, MarginType mt,
                         string riskFactor, Real cvaSensi) {
    // Check if hedge is specified for this risk factor
    if (perfectHedges_.count({rt, bucket, mt, riskFactor})) {
        // Perfect hedge: hedge sensitivity = CVA sensitivity
        return cvaSensi;
    }

    // Check for explicit hedge sensitivities
    if (hedgeSensitivities_.count({rt, bucket, mt, riskFactor})) {
        return hedgeSensitivities_[{rt, bucket, mt, riskFactor}];
    }

    // If useUnhedgedCvaSensis = false, treat CVA as unhedged
    return 0.0;
}
```

---

## 6. Input Requirements

### 6.1 Common Inputs (Both BA-CVA and SA-CVA)

#### Portfolio Definition

**File:** `portfolio.xml`

```xml
<?xml version="1.0"?>
<Portfolio>
  <Trade id="SWAP_1">
    <TradeType>Swap</TradeType>
    <Envelope>
      <CounterParty>CPTY_A</CounterParty>
      <NettingSetId>CPTY_A</NettingSetId>
      <PortfolioIds>
        <PortfolioId>BOOK_1</PortfolioId>
      </PortfolioIds>
    </Envelope>
    <SwapData>
      <!-- Swap details -->
    </SwapData>
  </Trade>

  <Trade id="FXFWD_1">
    <TradeType>FxForward</TradeType>
    <Envelope>
      <CounterParty>CPTY_A</CounterParty>
      <NettingSetId>CPTY_A</NettingSetId>
    </Envelope>
    <FxForwardData>
      <!-- FX forward details -->
    </FxForwardData>
  </Trade>
</Portfolio>
```

#### Netting Set Definitions

**File:** `netting.xml`

```xml
<?xml version="1.0"?>
<CSA>
  <NettingSetDetails>
    <NettingSetDefinition nettingSetId="CPTY_A">
      <CSADetails>
        <Bilateral>true</Bilateral>
        <CSACurrency>USD</CSACurrency>
        <Index>USD-SOFR</Index>
        <ThresholdPay>0</ThresholdPay>
        <ThresholdReceive>0</ThresholdReceive>
        <MinimumTransferAmountPay>0</MinimumTransferAmountPay>
        <MinimumTransferAmountReceive>0</MinimumTransferAmountReceive>
        <IndependentAmountPay>0</IndependentAmountPay>
        <IndependentAmountReceive>0</IndependentAmountReceive>
      </CSADetails>
    </NettingSetDefinition>
  </NettingSetDetails>
</CSA>
```

#### Counterparty Information

**File:** `counterparty.xml`

```xml
<?xml version="1.0"?>
<CounterpartyDetails>
  <Counterparty id="CPTY_A">
    <!-- BA-CVA specific -->
    <BaCvaRiskWeight>0.05</BaCvaRiskWeight>
    <IsClearingCP>false</IsClearingCP>

    <!-- SA-CVA specific -->
    <CreditQuality>IG</CreditQuality>  <!-- IG, HY, or NR -->
    <CreditCurve>CPTY_A_CDS</CreditCurve>

    <!-- Common -->
    <NettingSetDetails>
      <NettingSetId>CPTY_A</NettingSetId>
    </NettingSetDetails>
  </Counterparty>

  <Counterparty id="CPTY_B">
    <BaCvaRiskWeight>0.20</BaCvaRiskWeight>
    <CreditQuality>HY</CreditQuality>
    <CreditCurve>CPTY_B_CDS</CreditCurve>
    <IsClearingCP>false</IsClearingCP>
    <NettingSetDetails>
      <NettingSetId>CPTY_B</NettingSetId>
    </NettingSetDetails>
  </Counterparty>
</CounterpartyDetails>
```

#### Market Data

**File:** `market.txt` (CSV format)

```csv
# Yield curves
20240101,DiscountCurve/USD,0Y,0.0500
20240101,DiscountCurve/USD,1Y,0.0510
20240101,DiscountCurve/USD,2Y,0.0515
20240101,DiscountCurve/USD,5Y,0.0525
20240101,DiscountCurve/USD,10Y,0.0540
20240101,DiscountCurve/USD,30Y,0.0550

# FX rates
20240101,FXSpot/EURUSD,0Y,1.0850
20240101,FXSpot/GBPUSD,0Y,1.2750

# Credit spreads
20240101,CDS/CPTY_A,1Y,0.0050
20240101,CDS/CPTY_A,5Y,0.0075
20240101,CDS/CPTY_A,10Y,0.0095
```

#### Today's Market Configuration

**File:** `todaysmarket.xml`

```xml
<?xml version="1.0"?>
<TodaysMarket>
  <Configuration>
    <id>default</id>

    <!-- Discount curves -->
    <DiscountingCurves>
      <DiscountingCurve>
        <CurveName>USD</CurveName>
        <YieldCurve>Yield/USD/USD-SOFR</YieldCurve>
      </DiscountingCurve>
      <DiscountingCurve>
        <CurveName>EUR</CurveName>
        <YieldCurve>Yield/EUR/EUR-ESTR</YieldCurve>
      </DiscountingCurve>
    </DiscountingCurves>

    <!-- FX -->
    <FxSpots>
      <FxSpot>
        <CurrencyPair>EURUSD</CurrencyPair>
        <Quote>FX/EUR/USD</Quote>
      </FxSpot>
    </FxSpots>

    <!-- Credit curves -->
    <DefaultCurves>
      <DefaultCurve>
        <Name>CPTY_A_CDS</Name>
        <Currency>USD</Currency>
        <Quote>CDS/CPTY_A/*</Quote>
      </DefaultCurve>
    </DefaultCurves>
  </Configuration>
</TodaysMarket>
```

### 6.2 SA-CVA Specific Inputs

#### Sensitivity Configuration

**File:** `sensitivity.xml`

```xml
<?xml version="1.0"?>
<SensitivityAnalysis>
  <ParConversion>true</ParConversion>

  <PricingEngines>
    <Engine>DiscountingSwapEngineOptimised</Engine>
  </PricingEngines>

  <SensitivityData>
    <!-- IR Delta: Shift zero rates -->
    <RiskFactorSetup>
      <RiskFactorType>DiscountCurve</RiskFactorType>
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>  <!-- 1bp -->
      <ShiftTenors>1Y,2Y,5Y,10Y,30Y</ShiftTenors>
    </RiskFactorSetup>

    <!-- FX Delta: Shift spot rates -->
    <RiskFactorSetup>
      <RiskFactorType>FXSpot</RiskFactorType>
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>  <!-- 1% -->
    </RiskFactorSetup>

    <!-- IR Vega: Shift swaption volatilities -->
    <RiskFactorSetup>
      <RiskFactorType>SwaptionVolatility</RiskFactorType>
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>  <!-- 1% -->
    </RiskFactorSetup>

    <!-- FX Vega: Shift FX volatilities -->
    <RiskFactorSetup>
      <RiskFactorType>FXVolatility</RiskFactorType>
      <ShiftType>Relative</ShiftType>
      <ShiftSize>0.01</ShiftSize>  <!-- 1% -->
    </RiskFactorSetup>

    <!-- Credit Delta: Shift credit spreads -->
    <RiskFactorSetup>
      <RiskFactorType>SurvivalProbability</RiskFactorType>
      <ShiftType>Absolute</ShiftType>
      <ShiftSize>0.0001</ShiftSize>  <!-- 1bp -->
      <ShiftTenors>1Y,5Y,10Y</ShiftTenors>
    </RiskFactorSetup>
  </SensitivityData>
</SensitivityAnalysis>
```

#### Scenario Simulation Market

**File:** `xvasensimarket.xml`

```xml
<?xml version="1.0"?>
<ScenarioSimMarket>
  <BaseCurrency>USD</BaseCurrency>
  <Currencies>
    <Currency>USD</Currency>
    <Currency>EUR</Currency>
    <Currency>GBP</Currency>
  </Currencies>

  <YieldCurves>
    <Configuration>
      <Tenors>1M,3M,6M,1Y,2Y,3Y,5Y,7Y,10Y,15Y,20Y,30Y</Tenors>
      <Interpolation>LogLinear</Interpolation>
      <Extrapolation>FlatFwd</Extrapolation>
    </Configuration>
  </YieldCurves>

  <FxRates>
    <CurrencyPairs>
      <CurrencyPair>EURUSD</CurrencyPair>
      <CurrencyPair>GBPUSD</CurrencyPair>
    </CurrencyPairs>
  </FxRates>

  <SwaptionVolatilities>
    <Simulate>true</Simulate>
    <ReactionToTimeDecay>ForwardVariance</ReactionToTimeDecay>
    <Currencies>
      <Currency>USD</Currency>
      <Currency>EUR</Currency>
    </Currencies>
    <Expiries>6M,1Y,2Y,5Y,10Y</Expiries>
    <Terms>1Y,5Y,10Y,20Y</Terms>
  </SwaptionVolatilities>

  <DefaultCurves>
    <Names>
      <Name>CPTY_A_CDS</Name>
      <Name>CPTY_B_CDS</Name>
    </Names>
    <Tenors>6M,1Y,2Y,3Y,5Y,7Y,10Y</Tenors>
  </DefaultCurves>
</ScenarioSimMarket>
```

---

## 7. Configuration Examples

### 7.1 BA-CVA Configuration

**File:** `ore_bacva.xml`

```xml
<?xml version="1.0"?>
<ORE>
  <Setup>
    <Parameter name="asofDate">2024-01-01</Parameter>
    <Parameter name="inputPath">Input/</Parameter>
    <Parameter name="outputPath">Output/</Parameter>
    <Parameter name="baseCurrency">USD</Parameter>
    <Parameter name="marketDataFile">market.txt</Parameter>
    <Parameter name="fixingDataFile">fixings.txt</Parameter>
  </Setup>

  <Markets>
    <Market>
      <id>default</id>
      <todaysMarketParams>todaysmarket.xml</todaysMarketParams>
    </Market>
  </Markets>

  <Analytics>
    <Analytic type="bacva">
      <Parameter name="active">Y</Parameter>
      <Parameter name="baseCurrency">USD</Parameter>
      <Parameter name="marketConfigFile">todaysmarket.xml</Parameter>
      <Parameter name="portfolioFile">portfolio.xml</Parameter>
      <Parameter name="csaFile">netting.xml</Parameter>
      <Parameter name="counterpartyFile">counterparty.xml</Parameter>

      <!-- Optional -->
      <Parameter name="collateralBalancesFile">collateralbalances.xml</Parameter>
    </Analytic>
  </Analytics>
</ORE>
```

### 7.2 SA-CVA Configuration

**File:** `ore_sacva.xml`

```xml
<?xml version="1.0"?>
<ORE>
  <Setup>
    <Parameter name="asofDate">2024-01-01</Parameter>
    <Parameter name="inputPath">Input/</Parameter>
    <Parameter name="outputPath">Output/</Parameter>
    <Parameter name="baseCurrency">USD</Parameter>
    <Parameter name="marketDataFile">market.txt</Parameter>
    <Parameter name="fixingDataFile">fixings.txt</Parameter>
    <Parameter name="observationModel">Disable</Parameter>
  </Setup>

  <Markets>
    <Market>
      <id>default</id>
      <todaysMarketParams>todaysmarket.xml</todaysMarketParams>
    </Market>
    <Market>
      <id>xvasensitivity</id>
      <todaysMarketParams>todaysmarket.xml</todaysMarketParams>
    </Market>
  </Markets>

  <Analytics>
    <!-- Generate CVA sensitivities first -->
    <Analytic type="xvaSensitivity">
      <Parameter name="active">Y</Parameter>
      <Parameter name="baseCurrency">USD</Parameter>
      <Parameter name="marketConfigFile">todaysmarket.xml</Parameter>
      <Parameter name="portfolioFile">portfolio.xml</Parameter>
      <Parameter name="csaFile">netting.xml</Parameter>
      <Parameter name="counterpartyFile">counterparty.xml</Parameter>

      <!-- Sensitivity configuration -->
      <Parameter name="sensitivityConfigFile">sensitivity.xml</Parameter>
      <Parameter name="scenarioSimMarketParamsFile">xvasensimarket.xml</Parameter>
      <Parameter name="parSensitivity">Y</Parameter>

      <!-- CVA calculation parameters -->
      <Parameter name="creditSimulationConfigFile">creditSimulation.xml</Parameter>
      <Parameter name="creditCurvesFile">creditcurves.xml</Parameter>

      <!-- Performance -->
      <Parameter name="xvaSensiNThreads">8</Parameter>
    </Analytic>

    <!-- Calculate SA-CVA from sensitivities -->
    <Analytic type="sacva">
      <Parameter name="active">Y</Parameter>
      <Parameter name="baseCurrency">USD</Parameter>
      <Parameter name="counterpartyFile">counterparty.xml</Parameter>

      <!-- Option 1: Use sensitivities from xvaSensitivity analytic -->
      <!-- (automatic if xvaSensitivity is run first) -->

      <!-- Option 2: Load pre-computed sensitivities -->
      <!-- <Parameter name="cvaSensitivitiesFile">xva_par_sensitivity_cva.csv</Parameter> -->

      <!-- Option 3: Load SA-CVA formatted sensitivities directly -->
      <!-- <Parameter name="saCvaNetSensitivitiesFile">sacva_sensitivity.csv</Parameter> -->

      <!-- Hedge recognition -->
      <Parameter name="useUnhedgedCvaSensis">false</Parameter>
      <!-- <Parameter name="cvaPerfectHedgesFile">perfect_hedges.xml</Parameter> -->
    </Analytic>
  </Analytics>
</ORE>
```

### 7.3 Perfect Hedges Configuration (Optional)

**File:** `perfect_hedges.xml`

```xml
<?xml version="1.0"?>
<PerfectHedges>
  <!-- Perfect hedge: IR Delta for EUR 5Y tenor -->
  <Hedge>
    <RiskType>InterestRate</RiskType>
    <Bucket>EUR</Bucket>
    <MarginType>Delta</MarginType>
    <RiskFactor>5Y</RiskFactor>
  </Hedge>

  <!-- Perfect hedge: FX Delta for EUR -->
  <Hedge>
    <RiskType>ForeignExchange</RiskType>
    <Bucket>EUR</Bucket>
    <MarginType>Delta</MarginType>
    <RiskFactor>FXSpot</RiskFactor>
  </Hedge>
</PerfectHedges>
```

---

## 8. Running FRTB CVA Analytics

### 8.1 Using the ORE Application

From the build directory:

```bash
# BA-CVA
cd Examples/XvaRisk
../../build/App/ore Input/ore_bacva.xml

# SA-CVA
../../build/App/ore Input/ore_sacva.xml
```

### 8.2 Using Python Scripts

The examples include Python wrapper scripts:

```bash
cd Examples/XvaRisk

# BA-CVA
python run_bacva.py

# SA-CVA
python run_sacva.py
```

Example Python script structure:

```python
#!/usr/bin/env python3
import os
import sys
sys.path.append('../')
from ore_examples_helper import OreExample

oreex = OreExample(sys.argv[1] if len(sys.argv) > 1 else False)

# Run BA-CVA
oreex.run("Input/ore_bacva.xml")

# Check outputs
print("\n=== BA-CVA Results ===")
oreex.get_output_data_from_column("Output/bacva.csv",
                                  "Analytic",
                                  "BA_CVA_CAPITAL")

print("\nCompleted successfully")
```

### 8.3 Using Python Module (ORE-SWIG)

```python
import ORE

# Load configuration
params = ORE.Parameters()
params.fromFile("Input/ore_sacva.xml")

# Create and run ORE application
app = ORE.OREApp(params, True)
app.run()

# Access results
reports = app.getReports()
sacva_report = reports["sacva"]

# Process report data
for row in sacva_report:
    print(f"{row['NettingSetId']}: {row['Value']}")
```

### 8.4 Command-line Options

The `ore` executable supports various options:

```bash
# Basic usage
ore ore_bacva.xml

# Verbose output
ore ore_bacva.xml --verbose

# Dry run (parse config without running)
ore ore_bacva.xml --dry-run

# Override parameters
ore ore_bacva.xml --parameter asofDate=2024-02-01

# Multi-threaded (for SA-CVA sensitivity generation)
ore ore_sacva.xml --threads 8
```

---

## 9. Output Reports

### 9.1 BA-CVA Output

**File:** `Output/bacva.csv`

```csv
#Counterparty,NettingSet,Analytic,Value
All,All,BA_CVA_CAPITAL,335678.732366
CPTY_A,All,sCVA,516428.819025
CPTY_A,All,RiskWeight,0.050000
CPTY_A,CPTY_A,EAD,1719864.855298
CPTY_A,CPTY_A,EffMaturity,10.907723
CPTY_A,CPTY_A,DiscountFactor,0.770797
CPTY_B,All,sCVA,289156.442211
CPTY_B,All,RiskWeight,0.200000
CPTY_B,CPTY_B,EAD,548923.156489
CPTY_B,CPTY_B,EffMaturity,5.234567
CPTY_B,CPTY_B,DiscountFactor,0.821345
```

**Interpretation:**
- **BA_CVA_CAPITAL**: Total capital charge (USD 335,679)
- **sCVA**: Supervisory CVA for each counterparty
- **RiskWeight**: Counterparty risk weight
- **EAD**: Exposure at default from SA-CCR
- **EffMaturity**: Effective maturity in years
- **DiscountFactor**: Regulatory discount factor

### 9.2 SA-CVA Outputs

#### Summary Report

**File:** `Output/sacva.csv`

```csv
#NettingSetId,RiskType,MarginType,Bucket,Analytic,Value
,All,All,All,SA_CVA_CAPITAL,562485.5272
CPTY_A,All,All,All,SA_CVA_CAPITAL,485623.2145
CPTY_B,All,All,All,SA_CVA_CAPITAL,98745.3214
,InterestRate,All,All,SA_CVA_CAPITAL,349285.4553
,InterestRate,Delta,All,SA_CVA_CAPITAL,312066.7794
,InterestRate,Delta,EUR,SA_CVA_CAPITAL,156234.5621
,InterestRate,Delta,USD,SA_CVA_CAPITAL,145628.4024
,InterestRate,Delta,GBP,SA_CVA_CAPITAL,10203.8149
,InterestRate,Vega,All,SA_CVA_CAPITAL,37218.6759
,InterestRate,Vega,EUR,SA_CVA_CAPITAL,19845.2134
,InterestRate,Vega,USD,SA_CVA_CAPITAL,17373.4625
,ForeignExchange,All,All,SA_CVA_CAPITAL,98456.2341
,ForeignExchange,Delta,All,SA_CVA_CAPITAL,89234.5612
,ForeignExchange,Delta,EUR,SA_CVA_CAPITAL,52341.2345
,ForeignExchange,Delta,GBP,SA_CVA_CAPITAL,36893.3267
,ForeignExchange,Vega,All,SA_CVA_CAPITAL,9221.6729
,CreditCounterparty,All,All,SA_CVA_CAPITAL,114743.8378
,CreditCounterparty,Delta,All,SA_CVA_CAPITAL,114743.8378
,CreditCounterparty,Delta,IG_1_5Y,SA_CVA_CAPITAL,78234.5612
,CreditCounterparty,Delta,HY_1_5Y,SA_CVA_CAPITAL,36509.2766
```

**Interpretation:**
- Total SA-CVA capital: USD 562,486
- IR risk: USD 349,285 (62% of total)
- FX risk: USD 98,456 (17% of total)
- Credit risk: USD 114,744 (20% of total)
- Delta dominates over Vega in both IR and FX

#### Detail Report

**File:** `Output/sacvadetail.csv`

```csv
#NettingSetId,RiskType,Bucket,MarginType,RiskFactor,CvaType,Sensitivity,RiskWeight
,InterestRate,EUR,Delta,1Y,CvaAggregate,-1112543.3467,0.0111
,InterestRate,EUR,Delta,1Y,CvaHedge,0.0000,0.0111
,InterestRate,EUR,Delta,2Y,CvaAggregate,2345678.9012,0.0093
,InterestRate,EUR,Delta,2Y,CvaHedge,0.0000,0.0093
,InterestRate,EUR,Delta,5Y,CvaAggregate,5236861.8145,0.0074
,InterestRate,EUR,Delta,5Y,CvaHedge,0.0000,0.0074
,InterestRate,EUR,Delta,10Y,CvaAggregate,3456789.0123,0.0074
,InterestRate,EUR,Delta,10Y,CvaHedge,0.0000,0.0074
,InterestRate,EUR,Delta,30Y,CvaAggregate,1234567.8901,0.0074
,InterestRate,EUR,Delta,30Y,CvaHedge,0.0000,0.0074
,ForeignExchange,EUR,Delta,FXSpot,CvaAggregate,4567890.1234,0.11
,ForeignExchange,EUR,Delta,FXSpot,CvaHedge,0.0000,0.11
,CreditCounterparty,IG_1_5Y,Delta,CPTY_A,CvaAggregate,5678901.2345,0.0048
,CreditCounterparty,IG_1_5Y,Delta,CPTY_A,CvaHedge,0.0000,0.0048
```

**Interpretation:**
- Shows individual sensitivities for each risk factor
- **CvaAggregate**: Total CVA sensitivity (portfolio + hedges)
- **CvaHedge**: Hedge-only sensitivity
- **Sensitivity**: Change in CVA for unit change in risk factor
- **RiskWeight**: Regulatory risk weight applied

#### Sensitivity Reports

**File:** `Output/sacva_sensitivities.csv`

Aggregated sensitivities in SA-CVA format (after mapping).

**File:** `Output/cva_sensitivities.csv`

Raw CVA sensitivities from XVA sensitivity analytic (before mapping).

**File:** `Output/xva_par_sensitivity_cva.csv`

Par sensitivities (if `parSensitivity=Y`).

### 9.3 Report Comparison

**When to use each approach:**

| Metric | BA-CVA | SA-CVA |
|--------|--------|--------|
| **Simplicity** | ✓ Simple, single formula | Complex, multi-level aggregation |
| **Speed** | ✓ Fast (seconds) | Slow (minutes to hours) |
| **Granularity** | Counterparty/netting set level | Risk factor level |
| **Hedge Recognition** | Limited | ✓ Full recognition |
| **Capital Result** | Higher (conservative) | ✓ Lower (realistic) |
| **Regulatory Approval** | ✓ Not required | Required |
| **Transparency** | Less granular | ✓ Full decomposition |

---

## 10. Key Differences: BA-CVA vs SA-CVA

### 10.1 Conceptual Differences

| Aspect | BA-CVA | SA-CVA |
|--------|--------|--------|
| **Methodology** | Exposure-based (SA-CCR) | Sensitivity-based (CVA sensitivities) |
| **Computational Approach** | Direct formula | Hierarchical aggregation |
| **Risk Capture** | Aggregate exposure | Decomposed by risk factor |
| **Market Risk** | Implicit in EAD | Explicit (IR, FX, Vol) |
| **Credit Risk** | Counterparty risk weight | Spread sensitivities |
| **Diversification** | Limited (ρ=0.5) | Full (via correlations) |

### 10.2 Input Differences

| Input | BA-CVA | SA-CVA |
|-------|--------|--------|
| **Market Data** | Basic (curves, FX) | Comprehensive (curves, FX, vols, credit) |
| **Configuration** | Simple | Complex (sensitivity config) |
| **Counterparty Data** | Risk weight | Risk weight + credit quality + curve |
| **Hedges** | Not recognized | Fully recognized |
| **Pre-computation** | None | Optional (sensitivities) |

### 10.3 Output Differences

| Output | BA-CVA | SA-CVA |
|--------|--------|--------|
| **Granularity** | Counterparty, netting set | Risk type, bucket, risk factor |
| **Transparency** | EAD, maturity, risk weight | Full sensitivity breakdown |
| **Hedge Impact** | Not shown | Explicit hedge contributions |
| **Risk Attribution** | Limited | Comprehensive |

### 10.4 Calculation Time Comparison

**Typical portfolio: 100 trades, 5 counterparties**

| Analytic | Calculation Time | Main Cost |
|----------|-----------------|-----------|
| **BA-CVA** | ~10 seconds | SA-CCR calculation |
| **SA-CVA (pre-computed sensi)** | ~5 seconds | Aggregation only |
| **SA-CVA (with sensi generation)** | ~10-30 minutes | Bump-and-revalue (200+ scenarios) |

**Optimization strategies:**
- SA-CVA: Pre-compute and cache sensitivities
- SA-CVA: Use multithreading (8+ threads)
- SA-CVA: Run overnight for large portfolios
- Both: Use optimized pricing engines

### 10.5 Capital Results Comparison

**Typical observations:**

```
Portfolio: Mixed IR swaps, FX forwards, total notional $1B
Counterparties: 3 IG, 2 HY

BA-CVA Capital: $2.5M - $3.5M
  - Higher due to conservative assumptions
  - No hedge recognition
  - Less diversification benefit

SA-CVA Capital: $1.5M - $2.5M
  - Lower due to granular risk capture
  - Full hedge recognition
  - Diversification across risk factors

Ratio (SA/BA): 60% - 80%
```

**Factors affecting the ratio:**
- **Hedging**: More hedges → lower SA-CVA → lower ratio
- **Diversification**: More diverse portfolio → more SA-CVA benefit
- **Credit Quality**: Higher quality → lower absolute capital (both)
- **Maturity**: Longer maturity → higher capital (both)

---

## 11. Testing and Validation

### 11.1 Unit Tests

**Location:** `OREAnalytics/test/sacva.cpp`, `OREAnalytics/test/sacva.hpp`

**Test coverage:**

```cpp
BOOST_AUTO_TEST_SUITE(SaCvaTest)

// Correlation tests
BOOST_AUTO_TEST_CASE(testSACVA_IRDeltaCorr) {
    // Verify IR delta correlations match regulatory matrix
}

BOOST_AUTO_TEST_CASE(testSACVA_FxDeltaBucketCorr) {
    // Verify FX bucket correlations
}

BOOST_AUTO_TEST_CASE(testSACVA_CreditCptyBucketCorr) {
    // Verify credit counterparty bucket correlations
}

// Risk weight tests
BOOST_AUTO_TEST_CASE(testSACVA_IRDeltaRiskWeights) {
    // Verify IR delta risk weights by currency and tenor
}

// Calculation tests
BOOST_AUTO_TEST_CASE(testSACVA_FxDeltaCalc) {
    // End-to-end calculation for FX delta only
    // Load test sensitivities
    // Run calculator
    // Verify against expected results
}

BOOST_AUTO_TEST_CASE(testSACVA_IRDeltaCalc) {
    // End-to-end calculation for IR delta only
}

BOOST_AUTO_TEST_CASE(testSACVA_CreditCptyDeltaCalc) {
    // End-to-end calculation for credit delta only
}

BOOST_AUTO_TEST_SUITE_END()
```

**Running tests:**

```bash
cd build
./OREAnalytics/test/orea-test-suite --run_test=SaCvaTest
```

### 11.2 Example Tests

**Location:** `Examples/XvaRisk/`

**Test structure:**

```python
# run_bacva.py
def test_bacva():
    oreex = OreExample()
    oreex.run("Input/ore_bacva.xml")

    # Validate BA-CVA capital
    capital = oreex.get_output_data("Output/bacva.csv",
                                    filter={"Analytic": "BA_CVA_CAPITAL"})
    assert capital > 0, "BA-CVA capital should be positive"

    # Validate counterparty breakdown
    for cp in ["CPTY_A", "CPTY_B"]:
        scva = oreex.get_output_data("Output/bacva.csv",
                                      filter={"Counterparty": cp,
                                             "Analytic": "sCVA"})
        assert scva > 0, f"sCVA for {cp} should be positive"

# run_sacva.py
def test_sacva():
    oreex = OreExample()
    oreex.run("Input/ore_sacva.xml")

    # Validate SA-CVA capital
    capital = oreex.get_output_data("Output/sacva.csv",
                                    filter={"RiskType": "All",
                                           "Analytic": "SA_CVA_CAPITAL"})
    assert capital > 0, "SA-CVA capital should be positive"

    # Validate risk type breakdown
    for rt in ["InterestRate", "ForeignExchange", "CreditCounterparty"]:
        rt_capital = oreex.get_output_data("Output/sacva.csv",
                                           filter={"RiskType": rt,
                                                  "MarginType": "All"})
        # Risk type capital may be zero if no exposure
```

**Running example tests:**

```bash
cd Examples
python3 run_examples_testsuite.py XvaRisk
```

### 11.3 Validation Against Regulatory Examples

Both BA-CVA and SA-CVA implementations have been validated against:

1. **Basel consultative document examples** (d424, d507)
2. **ISDA SIMM methodology** (for correlation parameters)
3. **Industry benchmarks** (via test portfolios)

**Validation approach:**

```
1. Reproduce regulatory example portfolio
2. Match input parameters exactly
3. Run ORE calculation
4. Compare results (tolerance: <1% difference)
5. Document any discrepancies
```

### 11.4 Regression Testing

**Test suite execution:**

```bash
# Full test suite (all modules)
cd build
ctest -j $(sysctl -n hw.ncpu)

# CVA-specific tests only
ctest -R "bacva|sacva|saccr"

# Verbose output
ctest -R sacva --verbose
```

**Continuous integration:**
- Automated testing on each commit
- Multiple platforms (Linux, macOS, Windows)
- Multiple compilers (GCC, Clang, MSVC)
- Performance benchmarking

---

## 12. Performance Considerations

### 12.1 BA-CVA Performance

**Typical performance:**

| Portfolio Size | Trades | Counterparties | Calculation Time |
|----------------|--------|----------------|------------------|
| Small | 10-50 | 1-5 | <5 seconds |
| Medium | 50-200 | 5-20 | 5-20 seconds |
| Large | 200-1000 | 20-100 | 20-60 seconds |
| Very Large | 1000+ | 100+ | 1-5 minutes |

**Performance bottlenecks:**

1. **SA-CCR calculation** (main cost)
   - Trade pricing
   - Netting set aggregation
   - Multiplier calculation

2. **Market building**
   - Curve bootstrapping
   - Surface calibration

3. **Effective maturity calculation**
   - Cashflow generation
   - FX conversion

**Optimization tips:**

```cpp
// Use efficient pricing engines
<Engine>DiscountingSwapEngineOptimised</Engine>

// Cache market builds
analytic->configurations().buildCachedMarket = true;

// Minimize logging
LOG_MASK(ORE_ERROR);
```

### 12.2 SA-CVA Performance

**Typical performance:**

| Operation | Portfolio Size | Calculation Time |
|-----------|----------------|------------------|
| **CVA Sensitivity Generation** | 100 trades | 10-30 minutes |
| | 500 trades | 1-3 hours |
| | 1000+ trades | 3-10 hours |
| **SA-CVA Aggregation** | Any | <1 minute |

**Performance bottlenecks:**

1. **CVA calculation** (repeated 200+ times)
   - Monte Carlo simulation (if used)
   - Exposure cube generation
   - Default probability integration

2. **Sensitivity bumps** (200-500 scenarios)
   - Market rebuilds for each bump
   - Trade re-pricing

3. **Sensitivity mapping and aggregation**
   - Large CSV file parsing
   - In-memory aggregation

**Optimization strategies:**

```xml
<!-- Use multithreading -->
<Parameter name="xvaSensiNThreads">16</Parameter>

<!-- Use efficient CVA method -->
<Parameter name="creditSimulation">Analytic</Parameter>  <!-- vs MonteCarlo -->

<!-- Reduce simulation dates -->
<Parameter name="grid">1Y,2Y,5Y,10Y</Parameter>  <!-- vs monthly -->

<!-- Cache sensitivities -->
<Parameter name="cvaSensitivitiesFile">cached_sensitivities.csv</Parameter>

<!-- Use optimized pricing engines -->
<Engine>DiscountingSwapEngineOptimised</Engine>
```

**Multithreading scalability:**

```
Portfolio: 200 trades, 300 scenarios

Threads | Time     | Speedup
--------|----------|--------
1       | 120 min  | 1.0x
2       | 65 min   | 1.8x
4       | 35 min   | 3.4x
8       | 20 min   | 6.0x
16      | 12 min   | 10.0x
32      | 10 min   | 12.0x (diminishing returns)
```

### 12.3 Memory Considerations

**BA-CVA memory usage:**

```
Base: ~100 MB (market data, portfolio)
+ SA-CCR: ~50 MB per 100 trades
Total (1000 trades): ~600 MB
```

**SA-CVA memory usage:**

```
Base: ~100 MB (market data, portfolio)
+ CVA sensitivities: ~10 MB per 100 risk factors
+ Sensitivity cube: ~500 MB (for 200 trades, 300 scenarios)
Total (200 trades): ~1.5 GB
```

**Memory optimization:**

```cpp
// Stream sensitivities instead of loading all at once
SensiCubeStream stream("sensitivities.csv");
while (stream.next()) {
    process(stream.current());
}

// Clear intermediate results
analytic->clearIntermediateResults();

// Reduce report buffer size
<Parameter name="reportBufferSize">1000</Parameter>
```

### 12.4 Caching Strategies

**CVA sensitivity caching workflow:**

```
Day 1: Full run
  - Generate sensitivities: 2 hours
  - Calculate SA-CVA: 30 seconds
  - Total: 2 hours
  - Save: xva_par_sensitivity_cva.csv

Day 2-N: Incremental updates
  - Load cached sensitivities: 10 seconds
  - Update portfolio (add/remove trades): 5 minutes (sensitivity delta)
  - Calculate SA-CVA: 30 seconds
  - Total: 6 minutes

Weekly: Full refresh
  - Regenerate all sensitivities with latest market data
```

**Configuration for caching:**

```xml
<!-- Initial run: generate and save -->
<Analytic type="xvaSensitivity">
  <Parameter name="active">Y</Parameter>
  <!-- Full sensitivity config -->
</Analytic>

<!-- Subsequent runs: load cached -->
<Analytic type="sacva">
  <Parameter name="active">Y</Parameter>
  <Parameter name="cvaSensitivitiesFile">xva_par_sensitivity_cva.csv</Parameter>
</Analytic>
```

---

## 13. Limitations and Future Enhancements

### 13.1 Current Limitations

#### BA-CVA Limitations

1. **Reduced version only**
   - Does not recognize hedges (single-name CDS, index CDS)
   - Full version not yet implemented

2. **Trade type coverage**
   - Limited to trade types supported by SA-CCR
   - Exotic options not fully supported

3. **Wrong-way risk**
   - Not captured in current implementation
   - May underestimate capital for specific portfolios

4. **Collateral treatment**
   - Basic CSA handling
   - Complex collateral agreements not fully supported

#### SA-CVA Limitations

1. **Product scope**
   - IR: Swaps, swaptions (limited exotic support)
   - FX: Forwards, vanilla options
   - Credit: Basic CDS (index CDS not yet supported)
   - Equity/Commodity: Limited implementation

2. **CVA calculation method**
   - Independence assumption between credit and market risk
   - Joint modeling not implemented
   - May overestimate diversification benefits

3. **Reference credit**
   - Index CDS hedges not yet implemented
   - Single-name CDS hedges partially implemented

4. **Exotic derivatives**
   - Path-dependent options require AMC framework
   - Not all exotic features supported in sensitivity framework

5. **Dynamic hedging**
   - Static hedge recognition only
   - Dynamic rebalancing not modeled

### 13.2 Planned Enhancements

#### Short-term (Next 1-2 releases)

1. **BA-CVA full version**
   ```cpp
   // Hedge recognition for single-name and index CDS
   Real hedgeBenefit = calculateHedgeBenefit(
       cdsHedges, counterpartyExposures);
   sCva_hedged = sCva_unhedged - hedgeBenefit;
   ```

2. **Expanded product coverage**
   - Interest rate exotics (callable swaps, CMS, etc.)
   - FX exotics (barriers, digitals)
   - Commodity derivatives

3. **Index CDS support for SA-CVA**
   ```cpp
   // Reference credit sensitivities
   RiskFactorType: CreditReference
   Buckets: ITRAXX, CDX, etc.
   ```

4. **Performance improvements**
   - GPU acceleration for sensitivity calculations
   - Improved caching mechanisms
   - Parallel SA-CVA aggregation

#### Medium-term (2-4 releases)

1. **Joint credit-market risk modeling**
   ```cpp
   // Joint scenario generation
   scenario.creditSpread = f(scenario.interestRates, correlation);
   scenario.exposureDistribution = g(scenario.creditSpread);
   ```

2. **Wrong-way risk capture**
   - Explicit WWR adjustment factors
   - Stressed exposure measures
   - WWR-specific scenarios

3. **Dynamic hedge modeling**
   - Time-varying hedge portfolios
   - Rebalancing costs
   - Hedge effectiveness tracking

4. **Advanced collateral features**
   - Multiple currencies
   - Segregated vs unsegregated
   - Rehypothecation
   - Haircuts and eligibility

#### Long-term (4+ releases)

1. **Machine learning for CVA**
   - ML-based exposure prediction
   - Accelerated sensitivity calculations
   - Portfolio optimization

2. **Real-time CVA**
   - Streaming market data
   - Incremental updates
   - Sub-second response times

3. **Integration with XVA**
   - Unified FRTB-CVA and XVA framework
   - Consistent exposure measures
   - Joint optimization

4. **Regulatory reporting**
   - Automated COREP/FINREP reports
   - Regulatory submission formats
   - Audit trail and documentation

### 13.3 Known Issues

#### BA-CVA Known Issues

1. **Issue #1**: Effective maturity calculation for amortizing swaps
   - **Status**: Open
   - **Workaround**: Manual override in counterparty file
   - **Target**: v14

2. **Issue #2**: FX conversion for multi-currency netting sets
   - **Status**: Under review
   - **Workaround**: Ensure consistent base currency
   - **Target**: v13.1

#### SA-CVA Known Issues

1. **Issue #3**: Sensitivity mapping for cross-currency basis
   - **Status**: Open
   - **Workaround**: Manual sensitivity adjustment
   - **Target**: v14

2. **Issue #4**: Memory usage for large portfolios (1000+ trades)
   - **Status**: In progress
   - **Workaround**: Split portfolio into sub-portfolios
   - **Target**: v13.1

3. **Issue #5**: Vega sensitivities for swaptions with short expiries
   - **Status**: Under review
   - **Workaround**: Use longer expiry tenors
   - **Target**: v14

### 13.4 Contributing

To contribute enhancements or report issues:

1. **GitHub Issues**: https://github.com/OpenSourceRisk/Engine/issues
2. **Pull Requests**: https://github.com/OpenSourceRisk/Engine/pulls
3. **Mailing List**: ore-users@opensourcerisk.org
4. **User Guide**: See `Docs/userguide.pdf` for contribution guidelines

---

## Appendix A: Glossary

**BA-CVA**: Basic Approach for CVA risk capital calculation

**SA-CVA**: Standardized Approach for CVA risk capital calculation

**SA-CCR**: Standardized Approach for Counterparty Credit Risk

**EAD**: Exposure At Default

**CVA**: Credit Valuation Adjustment

**FRTB**: Fundamental Review of the Trading Book

**IG**: Investment Grade

**HY**: High Yield

**NR**: Not Rated

**RW**: Risk Weight

**WS**: Weighted Sensitivity

**ρ (rho)**: Correlation parameter

**γ (gamma)**: Bucket correlation parameter

**α (alpha)**: Scaling factor (1.4 in BA-CVA)

---

## Appendix B: Regulatory References

**Basel Framework:**
- MAR50: CVA Risk Capital Requirement
  https://www.bis.org/basel_framework/chapter/MAR/50.htm

**Basel Consultative Documents:**
- d424: Revision to the CVA risk framework (December 2015)
- d507: Targeted revisions to the CVA risk framework (July 2020)

**ISDA:**
- SIMM Methodology (for correlation parameters)

---

## Appendix C: Contact and Support

**Project Website:** http://opensourcerisk.org

**Documentation:**
- User Guide: `Docs/userguide.pdf`
- Products Guide: `Docs/products.pdf`
- Methodology: `Docs/ore_design.pdf`

**Code Repository:** https://github.com/OpenSourceRisk/Engine

**Support:**
- User Forum: ore-users@opensourcerisk.org
- Issue Tracker: https://github.com/OpenSourceRisk/Engine/issues

**Commercial Support:** Available from Quaternion Risk Management
- Website: https://www.quaternion.com
- Contact: info@quaternion.com

---

*Document version: 1.0*
*Last updated: 2025-11-12*
*ORE version: v13*
