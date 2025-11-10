# ORE VaR Calculation Implementation: End-to-End Documentation

**Author:** Auto-generated Documentation
**Date:** 2025-11-09
**ORE Version:** 13+

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Historical Simulation VaR](#2-historical-simulation-var)
3. [Parametric VaR](#3-parametric-var)
4. [Key Differences](#4-key-differences)
5. [Class Architecture](#5-class-architecture)
6. [Code Reference Index](#6-code-reference-index)

---

## 1. Introduction

Value at Risk (VaR) is a statistical measure that quantifies the potential loss in value of a portfolio over a defined period for a given confidence interval. ORE implements two distinct approaches to VaR calculation:

1. **Historical Simulation VaR**: Full revaluation approach using historical market scenarios
2. **Parametric VaR**: Approximation approach using sensitivities and covariance matrix

This document traces the complete end-to-end flow from Python entry points through configuration files to C++ implementation details.

---

## 2. Historical Simulation VaR

### 2.1 Python Entry Point

**Summary:** Simple Python wrapper that invokes the ORE application with the Historical Simulation VaR configuration file.

```python
# File: Examples/MarketRisk/run_histsimvar.py
#!/usr/bin/env python

import sys
sys.path.append('../')
from ore_examples_helper import OreExample

oreex = OreExample(sys.argv[1] if len(sys.argv)>1 else False)

print("+----------------------------------------+")
print("| Hist Sim VaR                           |")
print("+----------------------------------------+")

# legacy example 58

oreex.print_headline("Run ORE for HistSim VaR")
oreex.run("Input/ore_histsimvar.xml")  # Executes the ORE application with configuration
```

**File Reference:** [Examples/MarketRisk/run_histsimvar.py](../../Examples/MarketRisk/run_histsimvar.py)

---

### 2.2 Configuration Files

#### 2.2.1 Main Configuration (ore_histsimvar.xml)

**Summary:** Master configuration defining the as-of date, input paths, and Historical Simulation VaR analytic parameters.

```xml
<!-- File: Examples/MarketRisk/Input/ore_histsimvar.xml -->
<?xml version="1.0"?>
<ORE>
  <Setup>
    <!-- Key Parameters -->
    <Parameter name="asofDate">2019-12-30</Parameter>
    <Parameter name="inputPath">Input/HistSimVar</Parameter>
    <Parameter name="outputPath">Output/HistSimVar</Parameter>
    <Parameter name="baseCurrency">EUR</Parameter>
    <Parameter name="portfolioFile">portfolio.xml</Parameter>
    <!-- Market Data Configuration -->
    <Parameter name="marketDataFile">market.txt</Parameter>
    <Parameter name="fixingDataFile">fixings.txt</Parameter>
    <Parameter name="curveConfigFile">curveconfig.xml</Parameter>
    <Parameter name="conventionsFile">conventions.xml</Parameter>
    <Parameter name="marketConfigFile">todaysmarket.xml</Parameter>
    <Parameter name="pricingEnginesFile">pricingengine.xml</Parameter>
  </Setup>

  <Analytics>
    <Analytic type="historicalSimulationVar">
      <Parameter name="active">Y</Parameter>

      <!-- Historical scenario file containing historical market data -->
      <Parameter name="historicalScenarioFile">scenarios.csv</Parameter>

      <!-- Simulation market configuration -->
      <Parameter name="simulationConfigFile">simulation.xml</Parameter>

      <!-- Historical period: 3 years of data from 2017-01-17 to 2019-12-30 -->
      <Parameter name="historicalPeriod">2017-01-17,2019-12-30</Parameter>

      <!-- Margin Period of Risk: 10 business days -->
      <Parameter name="mporDays">10</Parameter>
      <Parameter name="mporCalendar">USD</Parameter>

      <!-- Generate overlapping 10-day periods (e.g., day 1-10, 2-11, 3-12, etc.) -->
      <Parameter name="mporOverlappingPeriods">true</Parameter>

      <!-- VaR confidence levels: 99%, 95%, 5%, 1% -->
      <Parameter name="quantiles">0.01,0.05,0.95,0.99</Parameter>

      <!-- Also calculate Expected Shortfall (CVaR) -->
      <Parameter name="includeExpectedShortfall">Y</Parameter>

      <!-- Output file for VaR results -->
      <Parameter name="outputFile">var.csv</Parameter>
    </Analytic>
  </Analytics>
</ORE>
```

**File Reference:** [Examples/MarketRisk/Input/ore_histsimvar.xml](../../Examples/MarketRisk/Input/ore_histsimvar.xml:29-43)

#### 2.2.2 Portfolio File

**Summary:** Contains trade definitions in XML format - a cross-currency swap and FX forward for this example.

```xml
<!-- File: Examples/MarketRisk/Input/HistSimVar/portfolio.xml -->
<?xml version='1.0' encoding='UTF-8'?>
<Portfolio>
  <Trade id="XCCY_Swap_EUR_USD">
    <TradeType>Swap</TradeType>
    <Envelope>
      <CounterParty>CPTY_A</CounterParty>
      <PortfolioIds>
        <PortfolioId>PF1</PortfolioId>
      </PortfolioIds>
    </Envelope>
    <SwapData>
      <LegData>
        <LegType>Floating</LegType>
        <Payer>true</Payer>
        <Currency>EUR</Currency>
        <Notionals>
          <Notional>30000000</Notional>
          <Exchanges>
            <NotionalInitialExchange>true</NotionalInitialExchange>
            <NotionalFinalExchange>true</NotionalFinalExchange>
          </Exchanges>
        </Notionals>
        <FloatingLegData>
          <Index>EUR-EURIBOR-6M</Index>
        </FloatingLegData>
        <!-- ... schedule details ... -->
      </LegData>
      <LegData>
        <LegType>Floating</LegType>
        <Payer>false</Payer>
        <Currency>USD</Currency>
        <Notionals>
          <Notional>33900000</Notional>
          <!-- ... -->
        </Notionals>
        <FloatingLegData>
          <Index>USD-LIBOR-3M</Index>
        </FloatingLegData>
      </LegData>
    </SwapData>
  </Trade>

  <Trade id="FXFWD_EURUSD_10Y">
    <TradeType>FxForward</TradeType>
    <Envelope>
      <CounterParty>CPTY_A</CounterParty>
      <PortfolioIds>
        <PortfolioId>PF1</PortfolioId>
      </PortfolioIds>
    </Envelope>
    <FxForwardData>
      <ValueDate>2029-03-01</ValueDate>
      <BoughtCurrency>EUR</BoughtCurrency>
      <BoughtAmount>1000000</BoughtAmount>
      <SoldCurrency>USD</SoldCurrency>
      <SoldAmount>1100000</SoldAmount>
    </FxForwardData>
  </Trade>
</Portfolio>
```

**File Reference:** [Examples/MarketRisk/Input/HistSimVar/portfolio.xml](../../Examples/MarketRisk/Input/HistSimVar/portfolio.xml:1-106)

---

### 2.3 C++ Implementation Flow

#### 2.3.1 Analytics Registration

**Summary:** Registration of the Historical Simulation VaR analytic in the factory during application initialization.

```cpp
// File: OREAnalytics/orea/app/initbuilders.cpp:67
void initBuilders(bool registerOREAnalytics) {
    // ... other registrations ...

    if (registerOREAnalytics) {
        // Register Historical Simulation VaR analytic with type "HISTSIM_VAR"
        // This maps to "historicalSimulationVar" in XML configuration
        ORE_REGISTER_ANALYTIC_BUILDER("HISTSIM_VAR", {}, HistoricalSimulationVarAnalytic, false);

        // Other analytics registered...
        ORE_REGISTER_ANALYTIC_BUILDER("PARAMETRIC_VAR", {}, ParametricVarAnalytic, false);
        // ...
    }
}
```

**File Reference:** [OREAnalytics/orea/app/initbuilders.cpp:67](../../OREAnalytics/orea/app/initbuilders.cpp#L67)

---

#### 2.3.2 Market and Portfolio Building

**Summary:** The analytic implementation sets up market data structures and builds the portfolio with pricing engines.

```cpp
// File: OREAnalytics/orea/app/analytics/varanalytic.cpp:43-61
void VarAnalyticImpl::runAnalytic(const QuantLib::ext::shared_ptr<ore::data::InMemoryLoader>& loader,
                              const std::set<std::string>& runTypes) {

    MEM_LOG;
    LOG("Running parametric VaR");

    // Set the evaluation date to the as-of date from configuration
    Settings::instance().evaluationDate() = inputs_->asof();
    ObservationMode::instance().setMode(inputs_->observationModel());

    LOG("VAR: Build Market");
    CONSOLEW("Risk: Build Market for VaR");
    // Build market objects (curves, vol surfaces, FX rates) from market data
    analytic()->buildMarket(loader);
    CONSOLE("OK");

    CONSOLEW("Risk: Build Portfolio for VaR");
    // Parse portfolio XML and attach appropriate pricing engines to each trade
    analytic()->buildPortfolio();
    CONSOLE("OK");

    // Enrich with any required historical fixings for floating rate instruments
    analytic()->enrichIndexFixings(analytic()->portfolio());

    // Create the VaR report object (polymorphic - could be Historical or Parametric)
    setVarReport(loader);
    QL_REQUIRE(varReport_, "No Var Report created");

    LOG("Call VaR calculation");
    CONSOLEW("Risk: VaR Calculation");
    ext::shared_ptr<MarketRiskReport::Reports> reports = ext::make_shared<MarketRiskReport::Reports>();
    QuantLib::ext::shared_ptr<InMemoryReport> varReport = QuantLib::ext::make_shared<InMemoryReport>(inputs_->reportBufferSize());
    reports->add(varReport);

    addAdditionalReports(reports);

    // Execute the VaR calculation
    varReport_->calculate(reports);
    CONSOLE("OK");

    analytic()->addReport(label_, "var", varReport);

    LOG("VaR completed");
    MEM_LOG;
}
```

**File Reference:** [OREAnalytics/orea/app/analytics/varanalytic.cpp:43-81](../../OREAnalytics/orea/app/analytics/varanalytic.cpp#L43-L81)

---

#### 2.3.3 Historical Scenario Generation

**Summary:** Builds a scenario generator that loads historical market data and creates shifted scenarios based on MPOR (Margin Period of Risk).

```cpp
// File: OREAnalytics/orea/app/analytics/varanalytic.cpp:152-180
void HistoricalSimulationVarAnalyticImpl::setVarReport(
    const QuantLib::ext::shared_ptr<ore::data::InMemoryLoader>& loader) {

    LOG("Build VaR calculator");

    // Parse the historical period and MPOR parameters
    TimePeriod benchmarkVarPeriod(parseListOfValues<Date>(inputs_->benchmarkVarPeriod(), &parseDate),
                                   inputs_->mporDays(),
                                   inputs_->mporCalendar());

    // Extract adjustment factors if available (e.g., for stock splits)
    QuantLib::ext::shared_ptr<ore::data::AdjustmentFactors> adjFactors;
    if (auto adjLoader = QuantLib::ext::dynamic_pointer_cast<AdjustedInMemoryLoader>(loader))
        adjFactors = QuantLib::ext::make_shared<ore::data::AdjustmentFactors>(adjLoader->adjustmentFactors());

    // Default return configuration (defines how to calculate returns: absolute, relative, log)
    auto defaultReturnConfig = QuantLib::ext::make_shared<ReturnConfiguration>();

    // Build the historical scenario generator
    // This loads scenarios from scenarios.csv and generates MPOR-shifted scenarios
    auto scenarios = buildHistoricalScenarioGenerator(
        inputs_->scenarioReader(),                                  // Reads scenarios.csv
        adjFactors,                                                  // Adjustment factors
        benchmarkVarPeriod,                                         // Historical period
        inputs_->mporCalendar(),                                    // Calendar for business days
        inputs_->mporDays(),                                        // 10-day MPOR
        analytic()->configurations().simMarketParams,               // Sim market parameters
        analytic()->configurations().todaysMarketParams,            // Today's market parameters
        defaultReturnConfig,                                        // Return calculation config
        inputs_->mporOverlappingPeriods());                        // true = overlapping periods

    // Optionally write scenarios to output for inspection
    if (inputs_->outputHistoricalScenarios())
        ore::analytics::ReportWriter().writeHistoricalScenarios(
            scenarios->scenarioLoader(),
            QuantLib::ext::make_shared<CSVFileReport>(path(inputs_->resultsPath() / "var_histscenarios.csv").string(), ',',
                                              false, inputs_->csvQuoteChar(), inputs_->reportNaString()));

    // Create a scenario simulation market that will apply scenarios to today's market
    auto simMarket = QuantLib::ext::make_shared<ScenarioSimMarket>(
        analytic()->market(),                                       // Today's market
        analytic()->configurations().simMarketParams,               // Simulation parameters
        Market::defaultConfiguration,
        *analytic()->configurations().curveConfig,                  // Curve configurations
        *analytic()->configurations().todaysMarketParams,           // Market parameters
        true, false, false, false,                                  // flags
        *inputs_->iborFallbackConfig());                           // IBOR fallback config

    // Connect the scenario generator to the simulation market
    simMarket->scenarioGenerator() = scenarios;
    scenarios->baseScenario() = simMarket->baseScenario();         // Set base scenario (today)

    // Create arguments for full revaluation (not sensitivity-based)
    std::unique_ptr<MarketRiskReport::FullRevalArgs> fullRevalArgs = std::make_unique<MarketRiskReport::FullRevalArgs>(
        simMarket,                                                  // Simulation market
        inputs_->pricingEngine(),                                   // Pricing engines
        inputs_->refDataManager(),                                  // Reference data
        *inputs_->iborFallbackConfig());                           // IBOR config

    // Create the Historical Simulation VaR report object
    varReport_ = ext::make_shared<HistoricalSimulationVarReport>(
        inputs_->baseCurrency(),                                    // EUR
        analytic()->portfolio(),                                    // Portfolio with trades
        inputs_->portfolioFilter(),                                 // Portfolio filter (regex)
        inputs_->varQuantiles(),                                    // [0.01, 0.05, 0.95, 0.99]
        benchmarkVarPeriod,                                         // Historical period
        scenarios,                                                  // Scenario generator
        std::move(fullRevalArgs),                                  // Full revaluation arguments
        inputs_->varBreakDown(),                                   // Breakdown by risk class
        inputs_->includeExpectedShortfall(),                       // Calculate ES
        inputs_->tradePnl());                                      // Trade-level P&L

}
```

**File Reference:** [OREAnalytics/orea/app/analytics/varanalytic.cpp:152-189](../../OREAnalytics/orea/app/analytics/varanalytic.cpp#L152-L189)

---

#### 2.3.4 P&L Calculation via Full Revaluation

**Summary:** The HistoricalPnlGenerator reprices the entire portfolio on each historical scenario to calculate actual P&L.

```cpp
// File: OREAnalytics/orea/engine/historicalpnlgenerator.cpp:45-77
HistoricalPnlGenerator::HistoricalPnlGenerator(
    const string& baseCurrency,
    const QuantLib::ext::shared_ptr<Portfolio>& portfolio,
    const QuantLib::ext::shared_ptr<ScenarioSimMarket>& simMarket,
    const QuantLib::ext::shared_ptr<HistoricalScenarioGenerator>& hisScenGen,
    const QuantLib::ext::shared_ptr<NPVCube>& cube,
    const set<std::pair<string, QuantLib::ext::shared_ptr<QuantExt::ModelBuilder>>>& modelBuilders,
    bool dryRun)
    : useSingleThreadedEngine_(true),
      portfolio_(portfolio),
      simMarket_(simMarket),
      hisScenGen_(hisScenGen),
      cube_(cube),
      dryRun_(dryRun),
      npvCalculator_([&baseCurrency]() -> std::vector<QuantLib::ext::shared_ptr<ValuationCalculator>> {
          // NPV calculator computes the net present value in base currency
          return {QuantLib::ext::make_shared<NPVCalculator>(baseCurrency)};
      }) {

    // Validate cube dimensions match the scenario generator and portfolio
    QL_REQUIRE(cube_->asof() == simMarket_->asofDate(),
               "The cube's as of date should equal that of the simulation market");

    std::set<std::string> cubeIds;
    for (const auto& [id, pos] : cube->idsAndIndexes()) {
        cubeIds.insert(id);
    }
    QL_REQUIRE(cubeIds == portfolio_->ids(), "The cube ids should equal the portfolio ids");

    // Cube samples = number of historical scenarios
    QL_REQUIRE(cube_->samples() == hisScenGen_->numScenarios(),
               "The cube sample size should equal the number of historical scenarios");

    // Single date (today), single depth (just NPV)
    QL_REQUIRE(cube_->numDates() == 1, "The cube should have exactly one date");
    QL_REQUIRE(cube_->depth() == 1, "The cube should have a depth of one");

    // Connect scenario generator to simulation market
    simMarket_->scenarioGenerator() = hisScenGen_;

    auto grid = QuantLib::ext::make_shared<DateGrid>();
    // Valuation engine will iterate through scenarios and compute NPVs
    valuationEngine_ = QuantLib::ext::make_shared<ValuationEngine>(
        simMarket_->asofDate(), grid, simMarket_, modelBuilders);
}

// The generateCube() method (not shown) iterates through all scenarios:
// For each scenario s:
//   1. simMarket->update(scenario[s])  - Apply scenario to market
//   2. For each trade t:
//        NPV[t][s] = trade[t]->instrument()->NPV()  - Reprice trade
//   3. Store in cube
//
// P&L is then calculated as: PnL[s] = NPV[scenario[s]] - NPV[base_scenario]
```

**File Reference:** [OREAnalytics/orea/engine/historicalpnlgenerator.cpp:45-77](../../OREAnalytics/orea/engine/historicalpnlgenerator.cpp#L45-L77)

---

#### 2.3.5 VaR Calculation from Empirical Distribution

**Summary:** VaR is computed as a quantile of the empirical P&L distribution using boost::accumulators.

```cpp
// File: OREAnalytics/orea/engine/historicalsimulationvar.cpp:132-146
Real HistoricalSimulationVarCalculator::var(Real confidence, const bool isCall,
    const set<pair<string, Size>>& tradeIds) const {

    // Calculate the quantile based on confidence level
    // For 99% VaR, we want the 1st percentile of losses (or 99th percentile of negative P&Ls)
    // c = cache size for boost tail quantile accumulator
    Size c = static_cast<Size>(std::floor(pnls_.size() * (1.0 - confidence) + 0.5)) + 2;

    // Use boost accumulator for efficient quantile calculation
    typedef accumulator_set<double, stats<boost::accumulators::tag::tail_quantile<boost::accumulators::right>>>
        accumulator;
    accumulator acc(boost::accumulators::tag::tail<boost::accumulators::right>::cache_size = c);

    // Feed all P&L values into the accumulator
    // isCall determines sign: for losses (typical VaR), we use -pnl
    for (const auto& pnl : pnls_) {
        acc(isCall ? pnl : -pnl);
    }

    // Extract the quantile at the specified confidence level
    // Example: For confidence = 0.99, this returns the 99th percentile of the distribution
    return quantile(acc, quantile_probability = confidence);
}
```

**Mathematical Formula:**
```
VaR_p = Quantile(P&L distribution, confidence = p)

For 99% VaR: VaR_0.99 = P&L value such that P(P&L ≤ VaR_0.99) = 0.99
```

**File Reference:** [OREAnalytics/orea/engine/historicalsimulationvar.cpp:132-146](../../OREAnalytics/orea/engine/historicalsimulationvar.cpp#L132-L146)

---

#### 2.3.6 Expected Shortfall Calculation

**Summary:** Expected Shortfall (ES) or Conditional VaR (CVaR) is the average of all losses beyond the VaR threshold.

```cpp
// File: OREAnalytics/orea/engine/historicalsimulationvar.cpp:148-165
QuantLib::Real HistoricalSimulationVarCalculator::expectedShortfall(
    QuantLib::Real confidence, const bool isCall,
    const set<std::pair<std::string, QuantLib::Size>>& tradeIds) const {

    // First calculate the VaR at this confidence level
    const auto var = this->var(confidence, isCall, tradeIds);
    if (std::isnan(var)) {
        return var;
    }

    // Use accumulator to compute the mean of tail losses
    accumulator_set<Real, stats<tag::mean>> accumulator;

    // Include all P&L values that are worse than (or equal to) VaR
    for (const auto pnl : pnls_) {
        const auto adjustedPnl = isCall ? pnl : -pnl;
        if (adjustedPnl <= var) {  // Losses beyond VaR threshold
            accumulator(adjustedPnl);
        }
    }

    // Return the average of these tail losses
    return mean(accumulator);
}
```

**Mathematical Formula:**
```
ES_p = E[P&L | P&L ≤ VaR_p]

Expected Shortfall is the conditional expectation of losses given that
losses exceed the VaR threshold.
```

**File Reference:** [OREAnalytics/orea/engine/historicalsimulationvar.cpp:148-165](../../OREAnalytics/orea/engine/historicalsimulationvar.cpp#L148-L165)

---

#### 2.3.7 Report Generation

**Summary:** Results are written to two CSV files: var.csv with VaR/ES metrics, and historical_PnL.csv with detailed P&L history.

```cpp
// File: OREAnalytics/orea/engine/historicalsimulationvar.cpp:108-116
void HistoricalSimulationVarReport::writeHeader(const ext::shared_ptr<Report>& report) const {
    // Header for var.csv
    report->addColumn("Portfolio", string())
          .addColumn("RiskClass", string())
          .addColumn("RiskType", string());

    // Add columns for each quantile (0.01, 0.05, 0.95, 0.99)
    for (const auto p : p())
        report->addColumn("Quantile_" + std::to_string(p), double(), 6);

    // Add Expected Shortfall columns if enabled
    if (includeExpectedShortfall_) {
        for (const auto p : p())
            report->addColumn("ExpectedShortfall_" + std::to_string(p), double(), 6);
    }
}

// File: OREAnalytics/orea/engine/historicalsimulationvar.cpp:51-63
void HistoricalSimulationVarReport::createAdditionalReports(
    const QuantLib::ext::shared_ptr<MarketRiskReport::Reports>& reports) {

    QuantLib::ext::shared_ptr<Report> report = reports->reports().at(1);

    // Header for historical_PnL.csv - detailed P&L for each scenario
    report->addColumn("Portfolio", string())
        .addColumn("RiskClass", string())
        .addColumn("RiskType", string())
        .addColumn("PLDate1", Date())        // Start date of MPOR period
        .addColumn("PLDate2", Date())        // End date of MPOR period
        .addColumn("PLAmount", double(), 6); // P&L for this period
}
```

**File Reference:**
- [OREAnalytics/orea/engine/historicalsimulationvar.cpp:108-116](../../OREAnalytics/orea/engine/historicalsimulationvar.cpp#L108-L116)
- [OREAnalytics/orea/engine/historicalsimulationvar.cpp:51-63](../../OREAnalytics/orea/engine/historicalsimulationvar.cpp#L51-L63)

---

### 2.4 Historical Simulation VaR: Complete Flow Summary

```
┌──────────────────────────────────────────────────────────────┐
│ 1. ENTRY: run_histsimvar.py → ore executable                 │
│    Input: ore_histsimvar.xml                                 │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. CONFIGURATION PARSING                                     │
│    - asofDate: 2019-12-30                                    │
│    - historicalPeriod: 2017-01-17 to 2019-12-30 (3 years)    │
│    - mporDays: 10                                            │
│    - quantiles: [0.01, 0.05, 0.95, 0.99]                     │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. MARKET & PORTFOLIO BUILDING                               │
│    VarAnalyticImpl::runAnalytic()                            │
│    - buildMarket(): Construct curves from market.txt         │
│    - buildPortfolio(): Parse portfolio.xml, attach engines   │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. SCENARIO GENERATION                                       │
│    buildHistoricalScenarioGenerator()                        │
│    - Load scenarios.csv (767,000+ lines)                     │
│    - Generate MPOR-shifted scenarios:                        │
│      * overlapping=true: [day1-10], [day2-11], [day3-12]...  │
│      * Calculate returns: scenario(t+10) / scenario(t)       │
│      * Apply to base scenario (today's market)               │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. P&L CALCULATION (Full Revaluation)                        │
│    HistoricalPnlGenerator::generateCube()                    │
│    For each scenario s:                                      │
│      - simMarket->update(scenario[s])                        │
│      - For each trade: NPV[s] = trade->NPV()                 │
│      - PnL[s] = NPV[s] - NPV[base]                           │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. VAR COMPUTATION                                           │
│    HistoricalSimulationVarCalculator::var()                  │
│    - Sort P&Ls: [pnl₁, pnl₂, ..., pnlₙ]                      │
│    - VaR_0.99 = quantile(P&Ls, 0.99)                         │
│    - ES_0.99 = mean(P&Ls where P&L ≤ VaR_0.99)               │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 7. OUTPUT                                                    │
│    - var.csv: VaR and ES by quantile                         │
│    - historical_PnL.csv: Detailed P&L for all scenarios      │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. Parametric VaR

### 3.1 Python Entry Point

**Summary:** Simple Python wrapper that invokes the ORE application with the Parametric VaR configuration file.

```python
# File: Examples/MarketRisk/run_parametricvar.py
#!/usr/bin/env python

import sys
sys.path.append('../')
from ore_examples_helper import OreExample

oreex = OreExample(sys.argv[1] if len(sys.argv)>1 else False)

print("+----------------------------------------+")
print("| Parametric VaR                         |")
print("+----------------------------------------+")

# legacy example 15

oreex.print_headline("Run ORE for Parametric VaR")
oreex.run("Input/ore_parametricvar.xml")  # Executes the ORE application with configuration
```

**File Reference:** [Examples/MarketRisk/run_parametricvar.py](../../Examples/MarketRisk/run_parametricvar.py)

---

### 3.2 Configuration Files

#### 3.2.1 Main Configuration (ore_parametricvar.xml)

**Summary:** Master configuration defining Parametric VaR analytic parameters including the calculation method and covariance matrix.

```xml
<!-- File: Examples/MarketRisk/Input/ore_parametricvar.xml -->
<?xml version="1.0"?>
<ORE>
  <Setup>
    <Parameter name="asofDate">2016-02-05</Parameter>
    <Parameter name="inputPath">Input</Parameter>
    <Parameter name="outputPath">Output/ParametricVar</Parameter>
    <Parameter name="portfolioFile">portfolio.xml</Parameter>
    <!-- ... market data configuration ... -->
  </Setup>

  <Analytics>
    <!-- Multiple analytics can run in sequence -->
    <Analytic type="npv">
      <Parameter name="active">Y</Parameter>
      <Parameter name="baseCurrency">EUR</Parameter>
      <Parameter name="outputFileName">npv.csv</Parameter>
    </Analytic>

    <Analytic type="parametricVar">
      <Parameter name="active">Y</Parameter>

      <!-- Input: Pre-calculated sensitivities from a previous sensitivity run -->
      <Parameter name="sensitivityInputFile">../Output/Sensi/sensitivity.csv</Parameter>

      <!-- Covariance matrix of risk factors -->
      <Parameter name="covarianceInputFile">covariance.csv</Parameter>

      <!-- VaR confidence levels -->
      <Parameter name="quantiles">0.01,0.05,0.95,0.99</Parameter>

      <!-- Breakdown by risk class (IR, FX, EQ, etc.) and risk type (Delta, Gamma, Vega) -->
      <Parameter name="breakdown">Y</Parameter>

      <!-- Portfolio filter using regex (only calculate VaR for PF1 or PF2) -->
      <Parameter name="portfolioFilter">PF1|PF2</Parameter>

      <!-- VaR calculation method: Delta, DeltaGammaNormal, MonteCarlo, Cornish-Fisher, Saddlepoint -->
      <Parameter name="method">DeltaGammaNormal</Parameter>

      <!-- Parameters for Monte Carlo method (commented out, not needed for DeltaGammaNormal) -->
      <!-- <Parameter name="mcSamples">100000</Parameter> -->
      <!-- <Parameter name="mcSeed">42</Parameter> -->

      <!-- Output file -->
      <Parameter name="outputFile">var.csv</Parameter>
    </Analytic>
  </Analytics>
</ORE>
```

**File Reference:** [Examples/MarketRisk/Input/ore_parametricvar.xml:42-57](../../Examples/MarketRisk/Input/ore_parametricvar.xml#L42-L57)

#### 3.2.2 Portfolio File

**Summary:** Contains diverse trade types to demonstrate sensitivity-based VaR across different risk classes.

```xml
<!-- File: Examples/MarketRisk/Input/portfolio.xml (excerpt) -->
<?xml version="1.0"?>
<Portfolio>
  <!-- Interest Rate Swap -->
  <Trade id="SWAP_EUR">
    <TradeType>Swap</TradeType>
    <Envelope>
      <PortfolioIds><PortfolioId>PF1</PortfolioId></PortfolioIds>
    </Envelope>
    <SwapData>
      <LegData>
        <LegType>Fixed</LegType>
        <Currency>EUR</Currency>
        <Notionals><Notional>10000000</Notional></Notionals>
        <FixedLegData><Rates><Rate>0.009851</Rate></Rates></FixedLegData>
        <!-- 20-year tenor -->
      </LegData>
      <LegData>
        <LegType>Floating</LegType>
        <Currency>EUR</Currency>
        <FloatingLegData><Index>EUR-EURIBOR-6M</Index></FloatingLegData>
      </LegData>
    </SwapData>
  </Trade>

  <!-- FX Option (non-linear, has gamma) -->
  <Trade id="FX_CALL_OPTION">
    <TradeType>FxOption</TradeType>
    <Envelope>
      <PortfolioIds><PortfolioId>PF2</PortfolioId></PortfolioIds>
    </Envelope>
    <FxOptionData>
      <OptionData>
        <LongShort>Long</LongShort>
        <OptionType>Call</OptionType>
        <Style>European</Style>
        <ExerciseDates><ExerciseDate>2026-03-01</ExerciseDate></ExerciseDates>
      </OptionData>
      <BoughtCurrency>EUR</BoughtCurrency>
      <BoughtAmount>1000000</BoughtAmount>
      <SoldCurrency>USD</SoldCurrency>
      <SoldAmount>1100000</SoldAmount>
    </FxOptionData>
  </Trade>

  <!-- ... Additional trades: Swaptions, Equity options, CDS, etc. ... -->
</Portfolio>
```

**File Reference:** [Examples/MarketRisk/Input/portfolio.xml](../../Examples/MarketRisk/Input/portfolio.xml:1-300)

---

### 3.3 C++ Implementation Flow

#### 3.3.1 Parametric VaR Report Initialization

**Summary:** Sets up the Parametric VaR calculator with sensitivity stream and covariance matrix.

```cpp
// File: OREAnalytics/orea/app/analytics/varanalytic.cpp:91-105
void ParametricVarAnalyticImpl::setVarReport(const QuantLib::ext::shared_ptr<ore::data::InMemoryLoader>& loader) {
    LOG("Build trade to portfolio id mapping");

    // Create parameters object with VaR calculation method
    ParametricVarCalculator::ParametricVarParams varParams(
        inputs_->varMethod(),        // "DeltaGammaNormal"
        inputs_->mcVarSamples(),     // MC samples (if using MonteCarlo method)
        inputs_->mcVarSeed());       // Random seed (if using MonteCarlo method)

    // Get sensitivity stream from pre-calculated sensitivity.csv file
    QuantLib::ext::shared_ptr<SensitivityStream> ss = sensiStream(loader);

    LOG("Build VaR calculator");
    if (inputs_->covarianceData().size() > 0) {
        // Case 1: Covariance matrix provided directly in covariance.csv
        std::unique_ptr<MarketRiskReport::SensiRunArgs> sensiArgs =
            std::make_unique<MarketRiskReport::SensiRunArgs>(
                ss,                              // Sensitivity stream (deltas, gammas)
                nullptr,                         // No shift calculator needed
                0.01,                           // Shift size for sensitivity interpretation
                inputs_->covarianceData());     // Covariance matrix from CSV

        // Create Parametric VaR report
        varReport_ = ext::make_shared<ParametricVarReport>(
            inputs_->baseCurrency(),            // EUR
            analytic()->portfolio(),            // Portfolio with all trades
            inputs_->portfolioFilter(),         // "PF1|PF2" regex filter
            inputs_->varQuantiles(),            // [0.01, 0.05, 0.95, 0.99]
            varParams,                          // Method parameters
            inputs_->getVarSalvagingAlgorithm(), // Algorithm to fix non-PSD covariance
            boost::none,                        // No time period (not historical)
            std::move(sensiArgs),              // Sensitivity arguments
            inputs_->varBreakDown());          // true = breakdown by risk class
    }
    // ... alternative case for generating covariance from historical scenarios ...
}
```

**File Reference:** [OREAnalytics/orea/app/analytics/varanalytic.cpp:91-105](../../OREAnalytics/orea/app/analytics/varanalytic.cpp#L91-L105)

---

#### 3.3.2 Sensitivity Aggregation

**Summary:** The MarketRiskReport base class reads delta and gamma sensitivities from the sensitivity stream and organizes them by risk factor.

**Sensitivity File Format (sensitivity.csv):**
```
TradeId,Factor_1,Factor_2,ShiftSize_1,ShiftSize_2,Currency,Base NPV,Delta[Factor_1],Delta[Factor_2],Gamma[Factor_1][Factor_1],Gamma[Factor_1][Factor_2],Gamma[Factor_2][Factor_2],...
SWAP_EUR,DiscountCurve/EUR/2/2Y,DiscountCurve/EUR/3/5Y,0.01,0.01,EUR,125000.50,2500.0,-1800.0,15.5,8.2,12.3,...
FX_CALL_OPTION,FX/RATE/EUR/USD,FXVolatility/EUR/USD/1/1Y/ATM,0.01,0.01,EUR,45000.25,3200.0,1500.0,95.3,25.1,45.8,...
```

**Code Flow (executed in base class):**
```cpp
// Conceptual aggregation (actual implementation in MarketRiskReport base class)

// Step 1: Read sensitivities from stream
for (auto& sensitivity : sensitivityStream) {
    RiskFactorKey key = sensitivity.key;      // e.g., "DiscountCurve/EUR/2/2Y"

    // Aggregate deltas
    deltas_[key] += sensitivity.delta;

    // Aggregate gammas (cross-sensitivities)
    for (auto& crossKey : sensitivity.crossKeys) {
        gammas_[{key, crossKey}] += sensitivity.gamma;
    }
}

// Result:
// deltas_ = map of risk factor → delta value
// gammas_ = map of (risk factor 1, risk factor 2) → gamma value
```

---

#### 3.3.3 VaR Calculation Methods

**Summary:** Five different methods are available for calculating Parametric VaR, each with different accuracy and computational cost trade-offs.

```cpp
// File: OREAnalytics/orea/engine/parametricvar.cpp:77-133
Real ParametricVarCalculator::var(Real confidence, const bool isCall,
                                   const set<pair<string, Size>>& tradeIds) const {
    Real factor = isCall ? 1.0 : -1.0;

    // Build delta vector and gamma matrix from aggregated sensitivities
    Array delta(deltas_.size(), 0.0);
    Matrix gamma(deltas_.size(), deltas_.size(), 0.0);

    if (includeDeltaMargin_) {
        Size counter = 0;
        for (auto it = deltas_.begin(); it != deltas_.end(); it++)
            delta[counter++] = factor * it->second;  // Δ = [δ₁, δ₂, ..., δₙ]
    }

    if (includeGammaMargin_) {
        Size outerIdx = 0;
        for (auto ito = deltas_.begin(); ito != deltas_.end(); ito++) {
            Size innerIdx = 0;
            // Diagonal gamma (second-order sensitivity to same factor)
            gamma[outerIdx][outerIdx] = factor * gammas_.at(std::make_pair(ito->first, ito->first));

            // Off-diagonal gammas (cross-sensitivities)
            for (auto iti = deltas_.begin(); iti != ito; iti++) {
                auto it = gammas_.find(std::make_pair(iti->first, ito->first));
                if (it != gammas_.end()) {
                    gamma[innerIdx][outerIdx] = factor * it->second;
                    gamma[outerIdx][innerIdx] = factor * it->second;  // Symmetric
                }
                innerIdx++;
            }
            outerIdx++;
        }
    }

    // METHOD 1: DELTA ONLY
    // VaR_p = Φ⁻¹(p) × √(Δᵀ Ω Δ)
    // Linear approximation: P&L ≈ Δᵀ × ΔS
    // Variance = Δᵀ Ω Δ, where Ω is covariance matrix
    if (parametricVarParams_.method == ParametricVarCalculator::ParametricVarParams::Method::Delta)
        return QuantExt::deltaVar(omega_, delta, confidence, *covarianceSalvage_);

    // METHOD 2: DELTA-GAMMA NORMAL
    // P&L ≈ Δᵀ ΔS + ½ ΔSᵀ Γ ΔS
    // Variance = Δᵀ Ω Δ + ½ tr(Γ Ω Γᵀ Ω)
    // VaR_p = Φ⁻¹(p) × √Variance
    // Assumes normal distribution even with gamma term
    else if (parametricVarParams_.method == ParametricVarCalculator::ParametricVarParams::Method::DeltaGammaNormal)
        return QuantExt::deltaGammaVarNormal(omega_, delta, gamma, confidence, *covarianceSalvage_);

    // METHOD 3: MONTE CARLO
    // Generate N scenarios from multivariate normal distribution
    // For each scenario i: ΔS[i] ~ N(0, Ω)
    //   P&L[i] = Δᵀ ΔS[i] + ½ ΔS[i]ᵀ Γ ΔS[i]
    // VaR_p = quantile(P&L distribution, p)
    // Most accurate, captures non-normal distribution from gamma
    else if (parametricVarParams_.method == ParametricVarCalculator::ParametricVarParams::Method::MonteCarlo) {
        QL_REQUIRE(parametricVarParams_.samples != Null<Size>(),
                   "MonteCarlo requires mcSamples parameter");
        QL_REQUIRE(parametricVarParams_.seed != Null<Size>(),
                   "MonteCarlo requires mcSeed parameter");
        return QuantExt::deltaGammaVarMc<PseudoRandom>(
            omega_, delta, gamma, confidence,
            parametricVarParams_.samples,      // e.g., 100,000 scenarios
            parametricVarParams_.seed,         // Random seed for reproducibility
            *covarianceSalvage_);
    }

    // METHOD 4: CORNISH-FISHER
    // Uses moment matching (skewness, kurtosis) to adjust normal quantile
    // VaR_p = μ + σ × [Φ⁻¹(p) + corrections for skewness and kurtosis]
    // Analytical approximation, faster than MC
    else if (parametricVarParams_.method == ParametricVarCalculator::ParametricVarParams::Method::CornishFisher)
        return QuantExt::deltaGammaVarCornishFisher(omega_, delta, gamma, confidence, *covarianceSalvage_);

    // METHOD 5: SADDLEPOINT
    // Most sophisticated analytical approximation using saddlepoint method
    // Falls back to Monte Carlo if saddlepoint calculation fails
    else if (parametricVarParams_.method == ParametricVarCalculator::ParametricVarParams::Method::Saddlepoint) {
        Real res;
        try {
            res = QuantExt::deltaGammaVarSaddlepoint(omega_, delta, gamma, confidence, *covarianceSalvage_);
        } catch (const std::exception& e) {
            ALOG("Saddlepoint VaR computation failed: " << e.what() << ", falling back on Monte-Carlo");
            res = QuantExt::deltaGammaVarMc<PseudoRandom>(
                omega_, delta, gamma, confidence,
                parametricVarParams_.samples,
                parametricVarParams_.seed,
                *covarianceSalvage_);
        }
        return res;
    }
    else
        QL_FAIL("Unknown Parametric VaR method");
}
```

**File Reference:** [OREAnalytics/orea/engine/parametricvar.cpp:77-133](../../OREAnalytics/orea/engine/parametricvar.cpp#L77-L133)

---

#### 3.3.4 Delta VaR Implementation (Linear Approximation)

**Summary:** The simplest method assumes linear portfolio response to market moves.

```cpp
// File: QuantExt/qle/math/deltagammavar.cpp (conceptual)

Real deltaVar(const Matrix& omega,      // Covariance matrix Ω
              const Array& delta,        // Delta vector Δ
              Real confidence,           // Confidence level p (e.g., 0.99)
              const CovarianceSalvage& salvage) {

    // Portfolio variance under linear approximation:
    // Var(P&L) = Var(Δᵀ ΔS) = Δᵀ Ω Δ
    Real variance = DotProduct(delta, omega * delta);

    // Standard deviation
    Real stdDev = std::sqrt(variance);

    // VaR at confidence p is the p-th quantile of normal distribution
    // Φ⁻¹(p) is the inverse normal CDF
    InverseCumulativeNormal invNorm;
    Real quantile = invNorm(confidence);

    // VaR_p = Φ⁻¹(p) × σ
    return quantile * stdDev;
}
```

**Mathematical Formula:**
```
P&L ≈ Δᵀ × ΔS    (linear approximation)

where:
  Δ = [δ₁, δ₂, ..., δₙ]ᵀ     (delta sensitivities)
  ΔS ~ N(0, Ω)                (market shocks)
  Ω = covariance matrix

Var(P&L) = Δᵀ Ω Δ
σ = √Var(P&L)
VaR_p = Φ⁻¹(p) × σ
```

**File Reference:** [QuantExt/qle/math/deltagammavar.cpp](../../QuantExt/qle/math/deltagammavar.cpp)

---

#### 3.3.5 Delta-Gamma Normal VaR (Quadratic Approximation)

**Summary:** Includes second-order (gamma) effects but still assumes normal distribution.

```cpp
// File: QuantExt/qle/math/deltagammavar.cpp:48-70 (simplified)

Real deltaGammaVarNormal(const Matrix& omega,   // Covariance matrix Ω
                         const Array& delta,    // Delta vector Δ
                         const Matrix& gamma,   // Gamma matrix Γ
                         Real confidence,       // Confidence level p
                         const CovarianceSalvage& salvage) {

    // Calculate moments of the P&L distribution
    Real num, mu, variance;
    moments(omega, delta, gamma, num, mu, variance);

    // P&L approximation: Δᵀ ΔS + ½ ΔSᵀ Γ ΔS
    // Expected P&L (mean):
    //   E[P&L] = ½ tr(Γ Ω)
    Real expectedPnl = mu * num;

    // Variance of P&L:
    //   Var(P&L) = Δᵀ Ω Δ + ½ tr(Γ Ω Γᵀ Ω)
    Real dOd = DotProduct(delta, omega * delta);
    Matrix go = gamma * omega;
    Matrix go2 = go * go;
    Real trGo2 = Trace(go2);
    Real pnlVariance = (dOd + 0.5 * trGo2) * num * num;

    // Standard deviation
    Real stdDev = std::sqrt(pnlVariance);

    // Assume normal distribution (even though gamma introduces skewness)
    InverseCumulativeNormal invNorm;
    Real quantile = invNorm(confidence);

    // VaR_p = μ + Φ⁻¹(p) × σ
    return expectedPnl + quantile * stdDev;
}
```

**Mathematical Formula:**
```
P&L ≈ Δᵀ ΔS + ½ ΔSᵀ Γ ΔS    (quadratic approximation)

E[P&L] = ½ tr(Γ Ω)

Var(P&L) = Δᵀ Ω Δ + ½ tr(Γ Ω Γᵀ Ω)

VaR_p = E[P&L] + Φ⁻¹(p) × √Var(P&L)

Note: This assumes normality, which may not hold due to gamma effects
```

**File Reference:** [QuantExt/qle/math/deltagammavar.cpp:48-70](../../QuantExt/qle/math/deltagammavar.cpp#L48-L70)

---

#### 3.3.6 Monte Carlo VaR (Most Accurate)

**Summary:** Simulates the full P&L distribution including non-linear effects from gamma.

```cpp
// File: QuantExt/qle/math/deltagammavar.hpp (template implementation)

template <class RNG>
Real deltaGammaVarMc(const Matrix& omega,      // Covariance matrix
                     const Array& delta,       // Delta vector
                     const Matrix& gamma,      // Gamma matrix
                     Real confidence,          // Confidence level
                     Size samples,             // Number of MC scenarios
                     Size seed,                // Random seed
                     const CovarianceSalvage& salvage) {

    // Cholesky decomposition of covariance matrix: Ω = L Lᵀ
    Matrix L = CholeskyDecomposition(omega);

    // Random number generator
    RNG rng(delta.size(), seed);

    // Accumulator for quantile calculation
    typedef accumulator_set<double, stats<tag::tail_quantile<right>>> accumulator;
    Size c = static_cast<Size>(std::floor(samples * (1.0 - confidence) + 0.5)) + 2;
    accumulator acc(tag::tail<right>::cache_size = c);

    // Monte Carlo simulation
    for (Size i = 0; i < samples; ++i) {
        // Generate standard normal random vector: Z ~ N(0, I)
        std::vector<Real> seq = rng.nextSequence().value;
        Array z(seq.begin(), seq.end());

        // Transform to correlated shocks: ΔS = L × Z ~ N(0, Ω)
        Array u = L * z;

        // Calculate P&L using delta-gamma approximation:
        // P&L = Δᵀ ΔS + ½ ΔSᵀ Γ ΔS
        Real pnl = DotProduct(u, delta)              // Linear term
                 + 0.5 * DotProduct(u, gamma * u);  // Quadratic term

        // Add to accumulator
        acc(pnl);
    }

    // Extract VaR as quantile of simulated P&L distribution
    return quantile(acc, quantile_probability = confidence);
}
```

**Mathematical Formula:**
```
Monte Carlo Algorithm:
For i = 1 to N:
  1. Generate Z[i] ~ N(0, I)          (standard normal)
  2. Compute ΔS[i] = L × Z[i]         (L = Cholesky(Ω))
  3. Calculate P&L[i] = Δᵀ ΔS[i] + ½ ΔS[i]ᵀ Γ ΔS[i]

VaR_p = empirical p-th quantile of {P&L[1], ..., P&L[N]}

Advantage: Captures non-normality from gamma effects
Disadvantage: Computationally expensive (typically N = 100,000+)
```

**File Reference:** [QuantExt/qle/math/deltagammavar.hpp:122-126](../../QuantExt/qle/math/deltagammavar.hpp#L122-L126)

---

#### 3.3.7 Report Generation with Breakdown

**Summary:** Results are written with optional breakdown by risk class and risk type.

```cpp
// File: OREAnalytics/orea/engine/parametricvar.cpp:165-176
void ParametricVarReport::writeHeader(const ext::shared_ptr<Report>& report) const {
    // Header for var.csv
    report->addColumn("Portfolio", string())
          .addColumn("RiskClass", string())     // IR, FX, EQ, CREDIT, INFLATION
          .addColumn("RiskType", string());     // Delta, Gamma, Vega, Curvature

    // Add column for each quantile
    for (const auto p : p())
        report->addColumn("Quantile_" + std::to_string(p), double(), 6);
}

std::vector<Real> ParametricVarReport::calcVarsForQuantiles() const {
    std::vector<Real> varRecords;

    // Calculate VaR for each quantile
    for (const auto p : p())
        varRecords.push_back(varCalculator_->var(p));

    return varRecords;
}
```

**Example Output (var.csv):**
```
Portfolio,RiskClass,RiskType,Quantile_0.01,Quantile_0.05,Quantile_0.95,Quantile_0.99
PF1,All,All,-125000.50,-85000.25,85000.25,125000.50
PF1,IR,Delta,-45000.00,-30000.00,30000.00,45000.00
PF1,IR,Gamma,-15000.00,-10000.00,10000.00,15000.00
PF1,FX,Delta,-55000.00,-37000.00,37000.00,55000.00
PF2,All,All,-95000.30,-65000.15,65000.15,95000.30
PF2,FX,Delta,-40000.00,-27000.00,27000.00,40000.00
PF2,FX,Vega,-25000.00,-17000.00,17000.00,25000.00
```

**File Reference:** [OREAnalytics/orea/engine/parametricvar.cpp:165-176](../../OREAnalytics/orea/engine/parametricvar.cpp#L165-L176)

---

### 3.4 Parametric VaR: Complete Flow Summary

```
┌──────────────────────────────────────────────────────────────┐
│ 1. ENTRY: run_parametricvar.py → ore executable              │
│    Input: ore_parametricvar.xml                              │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. CONFIGURATION PARSING                                     │
│    - asofDate: 2016-02-05                                    │
│    - method: DeltaGammaNormal                                │
│    - sensitivityInputFile: sensitivity.csv (pre-calculated)  │
│    - covarianceInputFile: covariance.csv                     │
│    - quantiles: [0.01, 0.05, 0.95, 0.99]                     │
│    - breakdown: true                                         │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. SENSITIVITY LOADING                                       │
│    MarketRiskReport::readSensitivities()                     │
│    - Read sensitivity.csv                                    │
│    - Aggregate deltas by risk factor: Δ = [δ₁,...,δₙ]        │
│    - Aggregate gammas: Γ = [γᵢⱼ]                             │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. COVARIANCE MATRIX LOADING                                 │
│    - Read covariance.csv (115×115 matrix)                   │
│    - Apply salvaging if not positive-definite:               │
│      * Spectral method (eigenvalue adjustment)               │
│      * Hypersphere method (nearest PSD matrix)               │
│    - Result: Valid covariance matrix Ω                       │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. VAR CALCULATION                                           │
│    ParametricVarCalculator::var()                            │
│    Method: DeltaGammaNormal                                  │
│    - Variance = Δᵀ Ω Δ + ½ tr(Γ Ω Γᵀ Ω)                      │
│    - VaR_0.99 = Φ⁻¹(0.99) × √Variance                        │
│                                                              │
│    Alternative methods:                                      │
│    - Delta: VaR = Φ⁻¹(p) × √(Δᵀ Ω Δ)                         │
│    - MonteCarlo: Simulate N scenarios, take quantile         │
│    - Cornish-Fisher: Moment matching approximation           │
│    - Saddlepoint: Advanced analytical approximation          │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. BREAKDOWN (if enabled)                                    │
│    Calculate VaR for each combination:                       │
│    - Portfolio: PF1, PF2                                     │
│    - Risk Class: IR, FX, EQ, CREDIT, INFLATION               │
│    - Risk Type: Delta, Gamma, Vega, Curvature                │
└──────────────────────────────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│ 7. OUTPUT                                                    │
│    - var.csv: VaR by portfolio/risk class/risk type          │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Key Differences

### 4.1 Comparison Table

| Aspect | Historical Simulation VaR | Parametric VaR |
|--------|---------------------------|----------------|
| **Approach** | Full revaluation | Sensitivity approximation |
| **Input Data** | Historical market scenarios (scenarios.csv) | Sensitivities + covariance matrix |
| **Accuracy** | Exact (actual repricing) | Approximate (Taylor expansion up to 2nd order) |
| **Speed** | Slower (reprices all trades N times) | Faster (matrix operations) |
| **Non-linearity** | Fully captured | Limited to gamma (2nd order) |
| **Distribution** | Empirical from history | Assumed (normal or adjusted) |
| **Memory** | High (stores NPV cube) | Low (stores sensitivity vectors) |
| **Scenarios** | Limited by historical data (~700 for 3 years) | Unlimited (analytical/MC) |
| **Best For** | Portfolios with path-dependent trades | Linear/moderately non-linear portfolios |
| **Key Classes** | `HistoricalSimulationVarCalculator` | `ParametricVarCalculator` |
| **P&L Calculation** | `HistoricalPnlGenerator` (full reval) | Delta-gamma approximation |
| **Configuration Type** | `<Analytic type="historicalSimulationVar">` | `<Analytic type="parametricVar">` |

---

### 4.2 When to Use Each Method

**Historical Simulation VaR:**
- ✅ Complex, non-linear instruments (exotic options, path-dependent)
- ✅ No assumptions about distribution shape
- ✅ When accuracy is paramount
- ✅ Backtesting and model validation
- ❌ Limited historical data available
- ❌ Very large portfolios (performance)

**Parametric VaR:**
- ✅ Large portfolios requiring fast calculation
- ✅ Linear or moderately non-linear instruments
- ✅ When sensitivities are already computed
- ✅ Risk attribution and decomposition needed
- ✅ Regulatory reporting (e.g., FRTB standardized approach)
- ❌ Highly non-linear or exotic instruments
- ❌ Fat-tailed distributions not captured by chosen method

---

## 5. Class Architecture

### 5.1 Inheritance Hierarchy

```
VarAnalyticImpl (base analytic)
├── ParametricVarAnalyticImpl
└── HistoricalSimulationVarAnalyticImpl

VarReport (base report)
├── ParametricVarReport
└── HistoricalSimulationVarReport

VarCalculator (base calculator)
├── ParametricVarCalculator
└── HistoricalSimulationVarCalculator
```

### 5.2 Key Components

#### Analytics Layer
- **File:** [OREAnalytics/orea/app/analytics/varanalytic.hpp](../../OREAnalytics/orea/app/analytics/varanalytic.hpp)
- **File:** [OREAnalytics/orea/app/analytics/varanalytic.cpp](../../OREAnalytics/orea/app/analytics/varanalytic.cpp)
- **Classes:** `VarAnalyticImpl`, `ParametricVarAnalyticImpl`, `HistoricalSimulationVarAnalyticImpl`
- **Role:** Orchestrate the VaR calculation workflow

#### Engine Layer
- **File:** [OREAnalytics/orea/engine/parametricvar.hpp](../../OREAnalytics/orea/engine/parametricvar.hpp)
- **File:** [OREAnalytics/orea/engine/parametricvar.cpp](../../OREAnalytics/orea/engine/parametricvar.cpp)
- **File:** [OREAnalytics/orea/engine/historicalsimulationvar.hpp](../../OREAnalytics/orea/engine/historicalsimulationvar.hpp)
- **File:** [OREAnalytics/orea/engine/historicalsimulationvar.cpp](../../OREAnalytics/orea/engine/historicalsimulationvar.cpp)
- **Classes:** `ParametricVarReport`, `HistoricalSimulationVarReport`, `ParametricVarCalculator`, `HistoricalSimulationVarCalculator`
- **Role:** Implement VaR calculation logic

#### P&L Generation
- **File:** [OREAnalytics/orea/engine/historicalpnlgenerator.hpp](../../OREAnalytics/orea/engine/historicalpnlgenerator.hpp)
- **File:** [OREAnalytics/orea/engine/historicalpnlgenerator.cpp](../../OREAnalytics/orea/engine/historicalpnlgenerator.cpp)
- **Class:** `HistoricalPnlGenerator`
- **Role:** Reprice portfolio on historical scenarios

#### Scenario Generation
- **File:** [OREAnalytics/orea/scenario/historicalscenariogenerator.hpp](../../OREAnalytics/orea/scenario/historicalscenariogenerator.hpp)
- **Class:** `HistoricalScenarioGenerator`
- **Role:** Load and transform historical market scenarios

#### Mathematical Library
- **File:** [QuantExt/qle/math/deltagammavar.hpp](../../QuantExt/qle/math/deltagammavar.hpp)
- **File:** [QuantExt/qle/math/deltagammavar.cpp](../../QuantExt/qle/math/deltagammavar.cpp)
- **Functions:** `deltaVar`, `deltaGammaVarNormal`, `deltaGammaVarMc`, `deltaGammaVarCornishFisher`, `deltaGammaVarSaddlepoint`
- **Role:** Implement parametric VaR formulas

---

## 6. Code Reference Index

### Configuration Files
- [Examples/MarketRisk/Input/ore_histsimvar.xml](../../Examples/MarketRisk/Input/ore_histsimvar.xml)
- [Examples/MarketRisk/Input/ore_parametricvar.xml](../../Examples/MarketRisk/Input/ore_parametricvar.xml)
- [Examples/MarketRisk/Input/HistSimVar/portfolio.xml](../../Examples/MarketRisk/Input/HistSimVar/portfolio.xml)
- [Examples/MarketRisk/Input/portfolio.xml](../../Examples/MarketRisk/Input/portfolio.xml)

### Python Entry Points
- [Examples/MarketRisk/run_histsimvar.py](../../Examples/MarketRisk/run_histsimvar.py)
- [Examples/MarketRisk/run_parametricvar.py](../../Examples/MarketRisk/run_parametricvar.py)

### C++ Implementation - Analytics Layer
- [OREAnalytics/orea/app/analytics/varanalytic.hpp](../../OREAnalytics/orea/app/analytics/varanalytic.hpp)
- [OREAnalytics/orea/app/analytics/varanalytic.cpp:43-81](../../OREAnalytics/orea/app/analytics/varanalytic.cpp#L43-L81) - Main analytic flow
- [OREAnalytics/orea/app/analytics/varanalytic.cpp:91-145](../../OREAnalytics/orea/app/analytics/varanalytic.cpp#L91-L145) - Parametric VaR setup
- [OREAnalytics/orea/app/analytics/varanalytic.cpp:152-189](../../OREAnalytics/orea/app/analytics/varanalytic.cpp#L152-L189) - Historical Sim VaR setup

### C++ Implementation - Engine Layer
- [OREAnalytics/orea/engine/parametricvar.hpp](../../OREAnalytics/orea/engine/parametricvar.hpp)
- [OREAnalytics/orea/engine/parametricvar.cpp:77-133](../../OREAnalytics/orea/engine/parametricvar.cpp#L77-L133) - VaR calculation methods
- [OREAnalytics/orea/engine/historicalsimulationvar.hpp](../../OREAnalytics/orea/engine/historicalsimulationvar.hpp)
- [OREAnalytics/orea/engine/historicalsimulationvar.cpp:132-146](../../OREAnalytics/orea/engine/historicalsimulationvar.cpp#L132-L146) - VaR quantile calculation
- [OREAnalytics/orea/engine/historicalsimulationvar.cpp:148-165](../../OREAnalytics/orea/engine/historicalsimulationvar.cpp#L148-L165) - Expected Shortfall

### C++ Implementation - P&L and Scenarios
- [OREAnalytics/orea/engine/historicalpnlgenerator.hpp](../../OREAnalytics/orea/engine/historicalpnlgenerator.hpp)
- [OREAnalytics/orea/engine/historicalpnlgenerator.cpp:45-77](../../OREAnalytics/orea/engine/historicalpnlgenerator.cpp#L45-L77)
- [OREAnalytics/orea/scenario/historicalscenariogenerator.hpp](../../OREAnalytics/orea/scenario/historicalscenariogenerator.hpp)

### C++ Implementation - Mathematical Library
- [QuantExt/qle/math/deltagammavar.hpp](../../QuantExt/qle/math/deltagammavar.hpp)
- [QuantExt/qle/math/deltagammavar.cpp:48-70](../../QuantExt/qle/math/deltagammavar.cpp#L48-L70) - Moment calculations

### Registration
- [OREAnalytics/orea/app/initbuilders.cpp:67-69](../../OREAnalytics/orea/app/initbuilders.cpp#L67-L69) - Analytics factory registration

---

## Appendix: Mathematical Formulas

### Historical Simulation VaR
```
Given N historical scenarios with P&L values: {pnl₁, pnl₂, ..., pnlₙ}

VaR_p = Quantile(P&L distribution, confidence p)

Expected Shortfall:
ES_p = E[P&L | P&L ≤ VaR_p]
     = (1/(N × (1-p))) × Σ pnlᵢ  for all pnlᵢ ≤ VaR_p
```

### Parametric VaR Methods

**Delta Method:**
```
P&L ≈ Δᵀ × ΔS
Var(P&L) = Δᵀ Ω Δ
VaR_p = Φ⁻¹(p) × √(Δᵀ Ω Δ)
```

**Delta-Gamma Normal:**
```
P&L ≈ Δᵀ ΔS + ½ ΔSᵀ Γ ΔS
E[P&L] = ½ tr(Γ Ω)
Var(P&L) = Δᵀ Ω Δ + ½ tr(Γ Ω Γᵀ Ω)
VaR_p = E[P&L] + Φ⁻¹(p) × √Var(P&L)
```

**Monte Carlo:**
```
For i = 1 to N:
  Z[i] ~ N(0, I)
  ΔS[i] = Cholesky(Ω) × Z[i]
  P&L[i] = Δᵀ ΔS[i] + ½ ΔS[i]ᵀ Γ ΔS[i]

VaR_p = empirical p-th quantile of {P&L[1], ..., P&L[N]}
```
