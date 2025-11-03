# ORE Execution Flow: XVA Explain Analysis

**Document Purpose**: This document provides a detailed trace of how ORE processes `Input/ore_explain.xml` from the Python wrapper through C++ analytics, including all major steps: XML parsing, configuration setup, trade creation, market building, pricing engines, and XVA calculations.

**Author**: Generated for ORE Codebase Understanding
**Last Updated**: 2025-10-30
**ORE Version**: Based on latest master branch

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Entry Point: Python Wrapper](#1-entry-point-python-wrapper)
3. [XML Configuration Parsing](#2-xml-configuration-parsing)
4. [OREApp Initialization](#3-oreapp-initialization)
5. [Parameter Loading and File Reading](#4-parameter-loading-and-file-reading)
6. [Market Data Loading](#5-market-data-loading)
7. [Analytics Manager Setup](#6-analytics-manager-setup)
8. [XVA Explain Analytic Execution](#7-xva-explain-analytic-execution)
9. [Portfolio Building](#8-portfolio-building)
10. [Market Construction](#9-market-construction)
11. [Pricing Engines Setup](#10-pricing-engines-setup)
12. [XVA Calculations](#11-xva-calculations)
13. [Report Generation](#12-report-generation)
14. [Complete Call Stack](#13-complete-call-stack)

---

## Executive Summary

The ORE XVA Explain workflow follows this high-level flow:

```
Python (ore_wrapper.py)
    ↓ SWIG bindings
C++ Parameters::fromFile() - Parse XML
    ↓
OREApp::run() - Main orchestration
    ↓
initFromParams() - Load all configuration files
    ↓
analytics() - Execute analytics
    ↓
AnalyticsManager::runAnalytics() - Run each analytic
    ↓
XvaExplainAnalyticImpl::runAnalytic() - XVA Explain specific logic
    ├─ Build Market (curves, surfaces)
    ├─ Build Portfolio (trades → instruments)
    ├─ Compute Base XVA (CVA/DVA/FVA)
    ├─ Generate Stress Scenarios (par rate shifts)
    ├─ Compute Stressed XVA (full revaluation)
    └─ Generate Explain Reports (attribution by risk factor)
```

**Key Insight**: ORE uses an **XML-driven, factory-pattern architecture** where configuration (XML) is separated from computation (C++). The XVA Explain analytic attributes XVA changes to market risk factors using **full revaluation** rather than sensitivities.

---

## 1. Entry Point: Python Wrapper

### File: `Examples/ore_wrapper.py`

The Python script provides a minimal interface to the C++ library via SWIG bindings.

```python
# Lines 1-23
import ORE  # SWIG-generated Python bindings

if __name__ == "__main__":
    # Line 13: Get path to ore.xml from command line
    parser.add_argument('path_to_ore_xml', default=".\Input\ore.xml")
    args = parser.parse_args()

    # Line 16-17: Create Parameters object and load XML
    params = ORE.Parameters()
    params.fromFile(args.path_to_ore_xml)  # Calls C++ Parameters::fromFile()

    # Line 19: Create OREApp with parameters
    ore = ORE.OREApp(params, True)  # True = enable console output

    # Line 21: Execute the analytics pipeline
    ore.run()  # Calls C++ OREApp::run()
```

**SWIG Binding**: The `ORE` module is generated from C++ headers in `ORE-SWIG/` directory using SWIG, exposing C++ classes to Python.

---

## 2. XML Configuration Parsing

### File: `OREAnalytics/orea/app/parameters.cpp`

When `params.fromFile("Input/ore_explain.xml")` is called:

#### XML Structure (`Input/ore_explain.xml`):

```xml
<!-- Lines 1-103 -->
<ORE>
  <Setup>
    <Parameter name="asofDate">2024-06-10</Parameter>
    <Parameter name="inputPath">Input</Parameter>
    <Parameter name="outputPath">Output/explain</Parameter>
    <Parameter name="marketDataFile">marketdata.csv</Parameter>
    <Parameter name="portfolioFile">portfolio_explain.xml</Parameter>
    <!-- ... more parameters ... -->
  </Setup>

  <Markets>
    <Parameter name="pricing">default</Parameter>
    <!-- ... market configurations ... -->
  </Markets>

  <Analytics>
    <Analytic type="npv">...</Analytic>
    <Analytic type="xvaExplain">
      <Parameter name="active">Y</Parameter>
      <Parameter name="marketConfigFile">xvaexplainmarket.xml</Parameter>
      <Parameter name="sensitivityConfigFile">sensitivity_explain.xml</Parameter>
      <Parameter name="mporDays">1</Parameter>
      <!-- ... more XVA explain parameters ... -->
    </Analytic>
  </Analytics>
</ORE>
```

#### Parsing Logic:

**File: `OREAnalytics/orea/app/parameters.hpp` (Lines 40-59)**
```cpp
class Parameters : public XMLSerializable {
public:
    // Line 45: Load from XML file
    void fromFile(const string& filename);

    // Line 46: Parse XML structure
    virtual void fromXML(XMLNode* node) override;

    // Line 51: Access parameter by group and name
    string get(const string& groupName, const string& paramName, bool fail = true) const;

private:
    // Line 58: Nested map structure: group → (parameter → value)
    map<string, map<string, string>> data_;
};
```

**Result**: XML is parsed into `data_["setup"]["asofDate"] = "2024-06-10"`, etc.

---

## 3. OREApp Initialization

### File: `OREAnalytics/orea/app/oreapp.cpp`

#### `OREApp::run()` - Main Entry Point

**Lines 435-481**:
```cpp
void OREApp::run() {
    // Line 438-439: Thread safety
    static std::mutex _s_mutex;
    std::lock_guard<std::mutex> lock(_s_mutex);

    // Line 442-446: Clean up singleton state
    CleanUpThreadLocalSingletons cleanupThreadLocalSingletons;
    CleanUpThreadGlobalSingletons cleanupThreadGloablSingletons;
    CleanUpLogSingleton cleanupLogSingleton(clearLog_, true);

    // Line 449-456: Initialize from parameters or inputs
    if (inputs_ != nullptr)
        initFromInputs();  // API-driven initialization
    else if (params_ != nullptr)
        initFromParams();  // File-driven initialization (our case)
    else {
        ALOG("both inputs are empty");
        return;
    }

    // Line 462: Start execution timer
    runTimer_.start();

    // Line 464-471: Execute analytics with error handling
    try {
        structuredLogger_->clear();
        analytics();  // Main analytics execution
    } catch (std::exception& e) {
        StructuredAnalyticsWarningMessage("OREApp::run()", "Error", e.what()).log();
        CONSOLE("Error: " << e.what());
        return;
    }

    // Line 473-480: Stop timer and report
    runTimer_.stop();
    errorMessages_ = structuredLogger_->messages();
    CONSOLE("run time: " << runTimer_.format(default_places, "%w") << " sec");
    CONSOLE("ORE done.");
}
```

---

## 4. Parameter Loading and File Reading

### `initFromParams()` - Load All Configuration

**File: `OREAnalytics/orea/app/oreapp.cpp` (Lines 345-407)**

```cpp
void OREApp::initFromParams() {
    // Line 346-349: Extract output path
    outputPath_ = params_->get("setup", "outputPath");

    // Line 350-355: Setup log file and log level
    logFile_ = outputPath_ + "/" + params_->get("setup", "logFile");
    logMask_ = 15;  // Default log mask
    if (params_->has("setup", "logMask")) {
        logMask_ = static_cast<Size>(parseInteger(params_->get("setup", "logMask")));
    }

    // Line 392-393: Initialize logging
    setupLog(logMask_, outputPath_, logFile_, logRootPath_, progressLogFile_,
             progressLogRotationSize_, progressLogToConsole_,
             structuredLogFile_, structuredLogRotationSize_);

    // Line 399-402: Create InputParameters and load all referenced files
    CONSOLEW("Loading inputs");
    inputs_ = make_shared<OREAppInputParameters>(params_);
    inputs_->loadParameters();  // ← Loads ALL XML/CSV files referenced in ore_explain.xml
    outputs_ = make_shared<OutputParameters>(params_);
    CONSOLE("OK");

    // Line 405: Set global evaluation date
    Settings::instance().evaluationDate() = inputs_->asof();
}
```

#### Files Loaded by `inputs_->loadParameters()`:

From the XML parameters, these files are read:

1. **Market Data**: `marketdata.csv` - Market quotes (rates, spreads, volatilities)
2. **Fixings**: `fixings.csv` - Historical index fixings
3. **Portfolio**: `portfolio_explain.xml` - Trade definitions
4. **Curve Config**: `curveconfig.xml` - Yield curve specifications
5. **Conventions**: `conventions.xml` - Market conventions (day count, calendars)
6. **Today's Market**: `todaysmarket.xml` - Market configuration
7. **Pricing Engines**: `pricingengine.xml` - Engine selection per product type
8. **XVA Explain Market**: `xvaexplainmarket.xml` - Market config for XVA explain
9. **Sensitivity Config**: `sensitivity_explain.xml` - Risk factors to stress

---

## 5. Market Data Loading

### `OREApp::analytics()` - Build CSV Loader

**File: `OREAnalytics/orea/app/oreapp.cpp` (Lines 234-256)**

```cpp
void OREApp::analytics() {
    LOG("ORE analytics starting");

    // Line 242: Set evaluation date globally
    Settings::instance().evaluationDate() = inputs_->asof();

    // Line 244: Set global pricing parameters
    GlobalPseudoCurrencyMarketParameters::instance().set(
        inputs_->pricingEngine()->globalParameters());

    // Line 247: Initialize conventions
    InstrumentConventions::instance().setConventions(inputs_->conventions());

    // Line 249-256: Create market data loader
    shared_ptr<MarketDataLoader> loader;
    if (!inputs_->marketDataLoaderInput().empty()) {
        // Binary loader for pre-serialized data
        loader = make_shared<MarketDataBinaryLoader>(inputs_,
                                                      inputs_->marketDataLoaderInput());
    } else {
        // CSV loader (our case)
        auto csvLoader = buildCsvLoader(params_);  // Reads marketdata.csv, fixings.csv
        loader = make_shared<MarketDataCsvLoader>(inputs_, csvLoader);
    }
```

#### `buildCsvLoader()` - Parse CSV Files

**File: `OREAnalytics/orea/app/oreapp.cpp` (Lines 188-232)**

```cpp
shared_ptr<CSVLoader> OREApp::buildCsvLoader(const shared_ptr<Parameters>& params) {
    // Line 189-192: Initialize variables
    bool implyTodaysFixings = false;
    vector<string> marketFiles = {};
    vector<string> fixingFiles = {};
    vector<string> dividendFiles = {};

    // Line 194: Get input path
    filesystem::path inputPath = params_->get("setup", "inputPath");

    // Line 196-198: Check if we should imply today's fixings
    std::string tmp = params_->get("setup", "implyTodaysFixings", false);
    if (tmp != "")
        implyTodaysFixings = ore::data::parseBool(tmp);

    // Line 200-205: Get market data files
    tmp = params->get("setup", "marketDataFile", false);
    if (tmp != "")
        marketFiles = getFileNames(tmp, inputPath);  // Supports wildcards

    // Line 207-212: Get fixing data files
    tmp = params->get("setup", "fixingDataFile", false);
    if (tmp != "")
        fixingFiles = getFileNames(tmp, inputPath);

    // Line 221-227: Get fixing cutoff date
    tmp = params->get("setup", "fixingCutoff", false);
    Date cutoff = Date();
    if (tmp != "")
        cutoff = parseDate(tmp);

    // Line 229-231: Create and return CSV loader
    auto loader = make_shared<CSVLoader>(marketFiles, fixingFiles,
                                         dividendFiles, implyTodaysFixings, cutoff);
    return loader;
}
```

**CSV Format Example** (`marketdata.csv`):
```
Date,Quote,Value
2024-06-10,DEPOSIT/EUR/1M,0.0320
2024-06-10,SWAP/EUR/10Y,0.0250
2024-06-10,FX/FXSPOT/EUR/USD,1.0850
```

---

## 6. Analytics Manager Setup

### Create Analytics Manager

**File: `OREAnalytics/orea/app/oreapp.cpp` (Lines 257-273)**

```cpp
    // Line 258-259: Create analytics manager
    analyticsManager_ = make_shared<AnalyticsManager>(inputs_, loader);
    analyticsManager_->initialise();

    // Line 260-263: Log analytics information
    LOG("Available analytics: " << to_string(analyticsManager_->validAnalytics()));
    CONSOLEW("Requested analytics");
    CONSOLE(to_string(inputs_->analytics()));
    LOG("Requested analytics: " << to_string(inputs_->analytics()));

    // Line 265-270: Setup market calibration report (optional)
    shared_ptr<MarketCalibrationReportBase> mcr;
    if (inputs_->outputTodaysMarketCalibration()) {
        auto marketCalibrationReport =
            make_shared<ore::data::InMemoryReport>(inputs_->reportBufferSize());
        mcr = make_shared<MarketCalibrationReport>(string(), marketCalibrationReport);
    }

    // Line 273: Run all requested analytics
    analyticsManager_->runAnalytics(mcr);
```

### AnalyticsManager::initialise()

**File: `OREAnalytics/orea/app/analyticsmanager.cpp`**

The `initialise()` method reads the `<Analytics>` section and creates analytic objects using the factory pattern:

```cpp
void AnalyticsManager::initialise() {
    // Parse each <Analytic> tag from XML
    for (auto& analyticConfig : inputs_->analytics()) {
        string type = analyticConfig.type;  // e.g., "npv", "xvaExplain"

        // Use factory to create analytic instance
        auto analytic = AnalyticFactory::instance().build(type, inputs_,
                                                          shared_from_this());

        // Add to analytics_ vector
        addAnalytic(type, analytic);
        validAnalytics_.insert(type);
    }
    initialised_ = true;
}
```

**For our example**, this creates:
1. **NpvAnalytic** - Basic NPV calculation
2. **CashflowAnalytic** - Cashflow schedule generation
3. **XvaExplainAnalytic** - XVA attribution (focus of this document)

---

## 7. XVA Explain Analytic Execution

### XvaExplainAnalyticImpl Constructor

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 172-180)**

```cpp
XvaExplainAnalyticImpl::XvaExplainAnalyticImpl(
    const shared_ptr<InputParameters>& inputs) : Analytic::Impl(inputs) {

    // Line 174: Set analytic label
    setLabel(LABEL);  // LABEL = "XVA_EXPLAIN"

    // Line 175-177: Calculate MPOR date (t0 + mporDays)
    mporDate_ = inputs_->mporDate() != Date()
                    ? inputs_->mporDate()  // Explicit MPOR date
                    : inputs_->mporCalendar().advance(inputs_->asof(),
                                                       int(inputs_->mporDays()),
                                                       QuantExt::Days);  // Default: t0 + 1 day

    // Line 178-179: Log dates
    LOG("ASOF date " << io::iso_date(inputs_->asof()));
    LOG("MPOR date " << io::iso_date(mporDate_));
}
```

**MPOR (Margin Period of Risk)**: Time horizon for XVA explain (typically 1 day). XVA Explain measures market moves from t0 to t0 + MPOR.

### Setup Configurations

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 182-186)**

```cpp
void XvaExplainAnalyticImpl::setUpConfigurations() {
    // Line 183-185: Load market and sensitivity configurations
    analytic()->configurations().todaysMarketParams = inputs_->todaysMarketParams();
    analytic()->configurations().simMarketParams = inputs_->xvaExplainSimMarketParams();
    analytic()->configurations().sensiScenarioData = inputs_->xvaExplainSensitivityScenarioData();
}
```

These configurations define:
- **todaysMarketParams**: Which curves/surfaces to build
- **simMarketParams**: Simulation market parameters (tenors, strikes)
- **sensiScenarioData**: Which risk factors to stress and by how much

---

## 8. Portfolio Building

### `runAnalytic()` - Main Execution

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 188-240)**

```cpp
void XvaExplainAnalyticImpl::runAnalytic(
    const shared_ptr<ore::data::InMemoryLoader>& loader,
    const std::set<std::string>& runTypes) {

    // Line 193-194: Validate inputs
    LOG("Running XVA Explain analytic.");
    QL_REQUIRE(inputs_->portfolio(), "XvaExplainAnalytic::run: No portfolio loaded.");

    // Line 196-197: Set evaluation date and market config
    Settings::instance().evaluationDate() = inputs_->asof();
    std::string marketConfig = inputs_->marketConfig("pricing");

    // Line 199-201: Build market (curves, volatilities, etc.)
    CONSOLEW("XVA_EXPLAIN: Build T0 and Sim Market");
    analytic()->buildMarket(loader);
    CONSOLE("OK");
```

#### Portfolio Building Details

**File: `OREAnalytics/orea/app/analytic.cpp`** (called by `buildMarket()` internally)

```cpp
void Analytic::buildPortfolio(const bool emitStructuredError) {
    LOG("Building portfolio for analytic " << label());

    // Get portfolio from inputs (already loaded from portfolio_explain.xml)
    portfolio_ = inputs_->portfolio();

    // Build pricing engines
    auto engineData = configurations_.engineData;
    auto engineFactory = make_shared<EngineFactory>(
        engineData, market_,
        map<MarketContext, string>{{MarketContext::pricing, marketConfig}},
        inputs_->refDataManager(), inputs_->iborFallbackConfig());

    // Build each trade in the portfolio
    portfolio_->build(engineFactory);

    LOG("Portfolio built with " << portfolio_->size() << " trades");
}
```

### Trade Building Process

**File: `OREData/ored/portfolio/portfolio.cpp`**

```cpp
void Portfolio::build(const shared_ptr<EngineFactory>& engineFactory,
                      const string& context, const bool emitStructuredError) {

    LOG("Building portfolio of size " << size());

    // Iterate through all trades
    for (auto& [tradeId, trade] : trades_) {
        try {
            // Build QuantLib instrument from trade XML
            trade->build(engineFactory);

            // Get the QuantLib instrument
            auto instrument = trade->instrument()->qlInstrument();

            // Set pricing engine
            instrument->setPricingEngine(engineFactory->builder(trade->tradeType()));

        } catch (std::exception& e) {
            LOG("Error building trade " << tradeId << ": " << e.what());
            if (!ignoreTradeBuildFail_)
                throw;
        }
    }
}
```

### Example: Building the 20Y Swap

**Input XML** (`portfolio_explain.xml`, Lines 3-50):
```xml
<Trade id="Swap_20y">
  <TradeType>Swap</TradeType>
  <Envelope>
    <CounterParty>CPTY_A</CounterParty>
    <NettingSetId>CPTY_A</NettingSetId>
  </Envelope>
  <SwapData>
    <LegData>
      <LegType>Fixed</LegType>
      <Payer>false</Payer>  <!-- Receive fixed -->
      <Currency>EUR</Currency>
      <Notionals><Notional>10000000</Notional></Notionals>
      <FixedLegData><Rates><Rate>0.02</Rate></Rates></FixedLegData>
      <!-- Schedule: 20240610 to 20440610, annual payments -->
    </LegData>
    <LegData>
      <LegType>Floating</LegType>
      <Payer>true</Payer>  <!-- Pay floating -->
      <FloatingLegData><Index>EUR-EURIBOR-6M</Index></FloatingLegData>
      <!-- Schedule: semi-annual payments -->
    </LegData>
  </SwapData>
</Trade>
```

**C++ Trade Building** (in `OREData/ored/portfolio/swap.cpp`):
```cpp
void Swap::build(const shared_ptr<EngineFactory>& engineFactory) {
    // Parse XML into C++ objects
    Currency ccy = parseCurrency(legs_[0]->currency());

    // Build fixed leg
    Leg fixedLeg = makeFixedLeg(fixedLegData_);

    // Build floating leg
    auto iborIndex = parseIborIndex(floatingLegData_->index());  // EUR-EURIBOR-6M
    Leg floatingLeg = makeIborLeg(floatingLegData_, iborIndex);

    // Create QuantLib::Swap
    instrument_ = make_shared<QuantLib::Swap>(
        std::vector<Leg>{fixedLeg, floatingLeg},
        std::vector<bool>{false, true});  // false = receive, true = pay

    // Set pricing engine
    auto engine = engineFactory->engine(ccy);  // DiscountingSwapEngine
    instrument_->setPricingEngine(engine);
}
```

---

## 9. Market Construction

### Build Today's Market

**File: `OREAnalytics/orea/app/analytic.cpp`**

```cpp
void Analytic::buildMarket(const shared_ptr<InMemoryLoader>& loader,
                           const bool marketRequired) {

    LOG("Building today's market for analytic " << label());

    // Line: Create TodaysMarket object
    market_ = make_shared<TodaysMarket>(
        configurations_.asofDate,              // 2024-06-10
        configurations_.todaysMarketParams,    // Which curves to build
        loader_,                               // Market data loader
        configurations_.curveConfig,           // Curve configurations
        continueOnError_,                      // Continue if curve build fails
        true,                                  // Load fixings
        lazyMarketBuilding_,                   // Lazy vs eager building
        inputs_->refDataManager()              // Reference data
    );

    LOG("Today's market built");
}
```

### TodaysMarket Construction

**File: `OREData/ored/marketdata/todaysmarket.cpp`**

TodaysMarket builds all required market objects:

1. **Discount Curves** (e.g., EUR discount curve)
2. **Index Curves** (e.g., EURIBOR-6M forecast curve)
3. **FX Spots** (e.g., EUR/USD)
4. **Volatility Surfaces** (swaption vol, cap/floor vol, FX vol)
5. **Credit Curves** (survival probabilities for counterparty)
6. **Inflation Curves** (if needed)

#### Example: Building EUR Discount Curve

```cpp
// In TodaysMarket constructor
void TodaysMarket::buildDiscountCurve(const string& curveName) {
    // Get curve configuration
    auto curveConfig = curveConfigs_->get(CurveSpec::CurveType::Yield, curveName);

    // Get market quotes for this curve
    vector<shared_ptr<RateHelper>> helpers;
    for (auto& segment : curveConfig->segments()) {
        // Create helpers (DepositHelper, SwapHelper, etc.)
        if (segment->type() == "Deposit") {
            Real rate = loader_->get(segment->quote(), asof_);
            helpers.push_back(make_shared<DepositRateHelper>(
                rate, segment->tenor(), ...));
        } else if (segment->type() == "Swap") {
            Real rate = loader_->get(segment->quote(), asof_);
            helpers.push_back(make_shared<SwapRateHelper>(
                rate, segment->tenor(), ...));
        }
    }

    // Bootstrap curve
    auto curve = make_shared<PiecewiseYieldCurve<Discount, LogLinear>>(
        asof_, helpers, dayCounter_);
    curve->enableExtrapolation();

    // Store in market
    yieldCurves_[make_tuple(Market::defaultConfiguration,
                            YieldCurveType::Discount,
                            curveName)] = curve;
}
```

**Bootstrapping**: QuantLib iteratively solves for zero rates that exactly reprice the input instruments (deposits, swaps, etc.) at their quoted market rates.

---

## 10. Pricing Engines Setup

### EngineFactory - Creating Pricing Engines

**File: `OREData/ored/portfolio/enginefactory.cpp`**

The EngineFactory creates appropriate pricing engines based on:
1. Product type (Swap, Swaption, FxOption, etc.)
2. Engine configuration from `pricingengine.xml`
3. Market data availability

#### Example: Swap Pricing Engine

From `pricingengine.xml`:
```xml
<PricingEngine>
  <Product type="Swap">
    <Model>DiscountedCashflows</Model>
    <ModelParameters/>
    <Engine>DiscountingSwapEngine</Engine>
    <EngineParameters/>
  </Product>
</PricingEngine>
```

**C++ Engine Building**:
```cpp
shared_ptr<PricingEngine> EngineFactory::engineBuilder(const string& tradeType) {
    if (tradeType == "Swap") {
        // Get discount curve from market
        auto discountCurve = market_->discountCurve(currency_);

        // Create discounting swap engine
        return make_shared<DiscountingSwapEngine>(
            discountCurve,
            boost::none,  // Spread
            Date(),       // Settlement date
            Date()        // NPV date
        );
    }
    // ... other trade types
}
```

### How Pricing Works

When `trade->instrument()->NPV()` is called:

```cpp
// In QuantLib::Swap
Real Swap::NPV() const {
    calculate();  // Triggers calculation if needed
    return npv_;
}

void Swap::calculate() const {
    // Call pricing engine
    engine_->calculate();  // DiscountingSwapEngine::calculate()
    npv_ = engine_->results_.value;
}

// In DiscountingSwapEngine
void DiscountingSwapEngine::calculate() const {
    Real npv = 0.0;

    // Price each leg
    for (size_t i = 0; i < arguments_.legs.size(); ++i) {
        Real legNPV = CashFlows::npv(
            arguments_.legs[i],       // Cashflow leg
            discountCurve_,          // Discount curve
            includeSettlementDateFlows_,
            settlementDate_,
            npvDate_
        );

        // Add or subtract based on payer/receiver
        npv += (arguments_.payer[i] ? -legNPV : legNPV);
    }

    results_.value = npv;
}

// CashFlows::npv() sums discounted cashflows:
// NPV = Σ CF_i × DF(t_i)
```

---

## 11. XVA Calculations

### Create Stress Test Data

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 203-240)**

```cpp
    // Line 203: Create stress scenarios
    auto scenarioData = createStressTestData(loader);

    // Line 205: Store in analytic
    analytic()->stressTests()[label()]["xvaExplain_parStressTest"] = scenarioData;
```

### `createStressTestData()` - Generate Par Rate Scenarios

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 244-399)**

This is the **core of XVA Explain logic**:

```cpp
shared_ptr<StressTestScenarioData>
XvaExplainAnalyticImpl::createStressTestData(
    const shared_ptr<ore::data::InMemoryLoader>& loader) const {

    // STEP 1: Compute t0 par rates (today)
    // Lines 247-256
    CONSOLEW("XVA_EXPLAIN: Compute t0 par rates");
    auto todayParAnalytic =
        AnalyticFactory::instance().build("PAR_SCENARIO", inputs_,
                                          analytic()->analyticsManager(), false).second;
    todayParAnalytic->configurations().asofDate = inputs_->asof();
    todayParAnalytic->configurations().todaysMarketParams =
        analytic()->configurations().todaysMarketParams;
    todayParAnalytic->configurations().simMarketParams =
        analytic()->configurations().simMarketParams;
    todayParAnalytic->configurations().sensiScenarioData =
        analytic()->configurations().sensiScenarioData;
    todayParAnalytic->runAnalytic(loader);
    auto todaysRates =
        dynamic_cast<ParScenarioAnalyticImpl*>(todayParAnalytic->impl().get())->parRates();
    CONSOLE("OK");
```

**What are Par Rates?**: Instead of zero rates, par rates are market-observable rates (e.g., swap par rate = rate that makes swap NPV=0). XVA Explain uses par rates because they're more stable and interpretable.

```cpp
    // STEP 2: Compute t1 par rates (MPOR date, e.g., t0 + 1 day)
    // Lines 258-269
    CONSOLEW("XVA_EXPLAIN: Compute t1 par rates");
    auto mporParAnalytic =
        AnalyticFactory::instance().build("PAR_SCENARIO", inputs_,
                                          analytic()->analyticsManager(), false).second;
    Settings::instance().evaluationDate() = mporDate_;  // Move to t1
    mporParAnalytic->configurations().asofDate = mporDate_;
    mporParAnalytic->configurations().todaysMarketParams =
        analytic()->configurations().todaysMarketParams;
    mporParAnalytic->configurations().simMarketParams =
        analytic()->configurations().simMarketParams;
    mporParAnalytic->configurations().sensiScenarioData =
        analytic()->configurations().sensiScenarioData;
    mporParAnalytic->runAnalytic(loader);
    auto mporRates =
        dynamic_cast<ParScenarioAnalyticImpl*>(mporParAnalytic->impl().get())->parRates();
    CONSOLE("OK");
```

```cpp
    // STEP 3: Calculate par rate shifts (Δpar = par_t1 - par_t0)
    // Lines 271-297
    CONSOLEW("XVA_EXPLAIN: Generate Stresstests");

    // Create scenario to store all shifts (full revaluation)
    StressTestScenarioData::StressTestData fullRevalScenario;
    fullRevalScenario.label = "t1";
    fullRevalScenario.irCurveParShifts = true;
    fullRevalScenario.irCapFloorParShifts = true;
    fullRevalScenario.creditCurveParShifts = true;

    auto scenarioData = make_shared<StressTestScenarioData>();
    scenarioData->useSpreadedTermStructures() = true;

    // STEP 4: For each risk factor, create individual stress scenario
    // Lines 300-398
    for (const auto& [key, mporValue] : mporRates) {
        auto t0Value = todaysRates.find(key);
        QL_REQUIRE(t0Value != todaysRates.end(),
                   "XVAExplain: Mismatch between t0 and mpor riskfactors");

        // Line 304: Calculate shift
        double shift = mporValue - t0Value->second;

        // Line 306: Only create scenario if shift exceeds threshold
        if (std::abs(shift) > inputs_->xvaExplainShiftThreshold()) {
            StressTestScenarioData::StressTestData scenario;
            scenario.label = to_string(key);  // e.g., "DiscountCurve/EUR/10Y"
            scenario.irCurveParShifts = true;
            scenario.irCapFloorParShifts = true;
            scenario.creditCurveParShifts = true;

            bool inScope = false;

            // Lines 313-391: Switch on risk factor type
            switch (key.keytype) {
            case RiskFactorKey::KeyType::DiscountCurve: {
                // Line 315-318: Add discount curve shift
                curveShiftData(scenario.discountCurveShifts, key, shift,
                               sensitivityData->discountCurveShiftData()[key.name]->shiftTenors);
                curveShiftData(fullRevalScenario.discountCurveShifts, key, shift,
                               sensitivityData->discountCurveShiftData()[key.name]->shiftTenors);
                inScope = true;
                break;
            }
            case RiskFactorKey::KeyType::IndexCurve: {
                // Line 330-335: Add index curve shift
                curveShiftData(fullRevalScenario.indexCurveShifts, key, shift,
                               sensitivityData->indexCurveShiftData()[key.name]->shiftTenors);
                curveShiftData(scenario.indexCurveShifts, key, shift,
                               sensitivityData->indexCurveShiftData()[key.name]->shiftTenors);
                inScope = true;
                break;
            }
            case RiskFactorKey::KeyType::FXSpot: {
                // Line 358-361: Add FX spot shift
                fullRevalScenario.fxShifts[key.name] = spotShiftData(key, shift);
                scenario.fxShifts[key.name] = spotShiftData(key, shift);
                inScope = true;
                break;
            }
            case RiskFactorKey::KeyType::SwaptionVolatility: {
                // Line 376-379: Add swaption vol shift
                swaptionVolShiftData(fullRevalScenario.swaptionVolShifts, key, shift, simParameters);
                swaptionVolShiftData(scenario.swaptionVolShifts, key, shift, simParameters);
                inScope = true;
                break;
            }
            // ... other risk factor types
            }

            // Line 392-394: Add scenario if in scope
            if (inScope) {
                scenarioData->setData(scenario);
            }
        }
    }

    // Line 397: Add full revaluation scenario (all shifts combined)
    scenarioData->setData(fullRevalScenario);
    return scenarioData;
}
```

**Result**: We now have stress scenarios:
- **"t1"**: Full market move from t0 to t1 (all risk factors)
- **"DiscountCurve/EUR/10Y"**: Only EUR 10Y discount rate shifted
- **"IndexCurve/EUR-EURIBOR-6M/5Y"**: Only EURIBOR-6M 5Y forward rate shifted
- ... one scenario per risk factor

### Convert to Zero Domain

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 207-215)**

```cpp
    // Line 207-208: Convert par shifts to zero shifts
    CONSOLEW("XVA_EXPLAIN: Convert Stresstest to zero domain");
    CONSOLE("");

    // Line 209-212: Create ParStressTestConverter
    ParStressTestConverter converter(
        analytic()->configurations().asofDate,
        analytic()->configurations().todaysMarketParams,
        analytic()->configurations().simMarketParams,
        analytic()->configurations().sensiScenarioData,
        analytic()->configurations().curveConfig,
        analytic()->market(),
        inputs_->iborFallbackConfig());

    // Line 213: Convert scenarios
    auto zeroScenarioData = converter.convertStressScenarioData(scenarioData);

    // Line 214: Store zero scenarios
    analytic()->stressTests()[label()]["xvaExplain_zeroStressTest"] = zeroScenarioData;
    CONSOLE("OK");
```

**Why Convert?**: Internal calculations use zero rates, but XVA Explain reports par rates for interpretability. The converter ensures consistent pricing.

### Run XVA Stress Analytic

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 217-229)**

```cpp
    // Line 217-218: Create XVA_STRESS analytic
    auto stressAnalytic =
        AnalyticFactory::instance().build("XVA_STRESS", inputs_,
                                          analytic()->analyticsManager(), false).second;

    // Line 219-220: Set stress scenarios
    auto stImpl = static_cast<XvaStressAnalyticImpl*>(stressAnalytic->impl().get());
    stImpl->setStressScenarios(zeroScenarioData);

    // Line 222-224: Configure analytic
    stressAnalytic->configurations().asofDate = inputs_->asof();
    stressAnalytic->configurations().todaysMarketParams =
        analytic()->configurations().todaysMarketParams;
    stressAnalytic->configurations().simMarketParams =
        analytic()->configurations().simMarketParams;

    // Line 225: Run XVA calculation for each scenario
    stressAnalytic->runAnalytic(loader);
```

### XVA Stress Calculation

The `XVA_STRESS` analytic does the following **for each scenario**:

1. **Rebuild Market** with stressed risk factors
2. **Reprice Portfolio** using stressed market
3. **Calculate Exposures**:
   - EPE (Expected Positive Exposure) = E[max(V, 0)]
   - ENE (Expected Negative Exposure) = E[max(-V, 0)]
4. **Compute CVA**:
   ```
   CVA = LGD × ∑ EE(t_i) × PD(t_i-1, t_i) × DF(t_i)
   ```
   Where:
   - LGD = Loss Given Default (typically 60%)
   - EE = Expected Exposure
   - PD = Marginal Probability of Default
   - DF = Discount Factor

5. **Store Results** with scenario label

---

## 12. Report Generation

### Parse XVA Results

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 226-239)**

```cpp
    // Line 226-227: Get XVA report from stress analytic
    CONSOLEW("XVA_EXPLAIN: Write Reports");
    auto xvaReport = stressAnalytic->getReport("XVA_STRESS", "xva");

    // Line 228: Add detailed report
    analytic()->addReport(label(), "xvaExplain_details", xvaReport);

    // Line 229: Parse results
    XvaExplainResults xvaData(xvaReport);
```

### XvaExplainResults Constructor

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 135-166)**

```cpp
XvaExplainResults::XvaExplainResults(const shared_ptr<InMemoryReport>& xvaReport) {
    // Line 136-139: Get column positions
    size_t tradeIdColumn = xvaReport->columnPosition("TradeId");
    size_t nettingSetIdColumn = xvaReport->columnPosition("NettingSetId");
    size_t scenarioIdColumn = xvaReport->columnPosition("Scenario");
    size_t cvaColumn = xvaReport->columnPosition("CVA");

    // Line 140-165: Parse each row
    for (size_t i = 0; i < xvaReport->rows(); ++i) {
        const string& scenario = boost::get<string>(xvaReport->data(scenarioIdColumn, i));
        const string& tradeId = boost::get<string>(xvaReport->data(tradeIdColumn, i));
        const string& nettingset = boost::get<string>(xvaReport->data(nettingSetIdColumn, i));
        const double cva = boost::get<double>(xvaReport->data(cvaColumn, i));

        const auto key = XvaReportKey{tradeId, nettingset};

        // Line 151-164: Categorize by scenario
        if (scenario != "BASE" && scenario != "t1") {
            // Individual risk factor scenario
            try {
                auto rfKey = parseRiskFactorKey(scenario);  // e.g., "DiscountCurve/EUR/10Y"
                fullRevalScenarioCva_[rfKey][key] = cva;
                keyTypes_.insert(rfKey.keytype);
            } catch (const std::exception&) {
                StructuredAnalyticsErrorMessage("XvaExplain", "Unexpected RiskFactor",
                    scenario + " is not a valid riskfactor, skip it");
            }
        } else if (scenario == "BASE") {
            // Base (unstressed) CVA
            baseCvaData_[key] = cva;
        } else {
            // Full revaluation (all shifts)
            fullRevalCva_[key] = cva;
        }
    }
}
```

### Generate Explain Reports

**File: `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` (Lines 231-239)**

```cpp
    // Line 231-232: Create explain report
    auto xvaExplainReport = make_shared<InMemoryReport>(inputs_->reportBufferSize());
    ReportWriter(inputs_->reportNaString()).writeXvaExplainReport(*xvaExplainReport, xvaData);
    analytic()->addReport(label(), "xvaExplain", xvaExplainReport);

    // Line 235-237: Create summary report
    auto xvaExplainSummaryReport = make_shared<InMemoryReport>(inputs_->reportBufferSize());
    ReportWriter(inputs_->reportNaString()).writeXvaExplainSummary(*xvaExplainSummaryReport, xvaData);
    analytic()->addReport(label(), "xvaExplain_summary", xvaExplainSummaryReport);
    CONSOLE("OK");
```

### Write Reports to Files

**File: `OREAnalytics/orea/app/oreapp.cpp` (Lines 275-334)**

```cpp
    // Line 275-276: Log and get reports
    CONSOLEW("Writing reports...");
    Analytic::analytic_reports reports = analyticsManager_->reports();

    // Line 279-281: Write to files
    analyticsManager_->toFile(reports, inputs_->resultsPath().string(),
                              outputs_->fileNameMap(),
                              inputs_->csvSeparator(),
                              inputs_->csvCommentCharacter(),
                              inputs_->csvQuoteChar(),
                              inputs_->reportNaString());
    CONSOLE("OK");
```

### Output Files

In `Output/explain/` directory:

1. **npv.csv**: Basic NPV report
   ```csv
   TradeId,TradeType,Notional,NPV,Currency
   Swap_20y,Swap,10000000,-125000.00,EUR
   ```

2. **flows.csv**: Cashflow schedule
   ```csv
   TradeId,Type,LegNo,PayDate,Amount,DiscountFactor,PV
   Swap_20y,Fixed,1,2025-06-10,200000,0.9850,197000
   Swap_20y,Floating,2,2024-12-10,-160000,0.9925,-158800
   ...
   ```

3. **xvaExplain.csv**: Detailed XVA attribution
   ```csv
   TradeId,NettingSet,RiskFactor,BaseCVA,StressedCVA,Contribution
   Swap_20y,CPTY_A,DiscountCurve/EUR/10Y,12500.00,12450.00,-50.00
   Swap_20y,CPTY_A,DiscountCurve/EUR/20Y,12500.00,12480.00,-20.00
   Swap_20y,CPTY_A,IndexCurve/EUR-EURIBOR-6M/5Y,12500.00,12520.00,20.00
   ...
   ```

4. **xvaExplain_summary.csv**: Aggregated attribution
   ```csv
   RiskFactorType,TotalContribution
   DiscountCurve,-120.00
   IndexCurve,35.00
   SwaptionVol,5.00
   FXSpot,0.00
   ```

---

## 13. Complete Call Stack

Here's the complete execution flow with line numbers:

```
ore_wrapper.py:21
    ore.run()
    ↓
OREApp::run() [oreapp.cpp:435]
  ├─ initFromParams() [oreapp.cpp:345]
  │  ├─ params_->get("setup", "outputPath") [parameters.cpp]
  │  ├─ setupLog() [oreapp.cpp:392]
  │  ├─ inputs_ = make_shared<OREAppInputParameters>(params_) [oreapp.cpp:400]
  │  └─ inputs_->loadParameters() [inputparameters.cpp]
  │     ├─ Load portfolio_explain.xml → Portfolio object
  │     ├─ Load curveconfig.xml → CurveConfigurations
  │     ├─ Load conventions.xml → Conventions
  │     ├─ Load todaysmarket.xml → TodaysMarketParameters
  │     ├─ Load pricingengine.xml → EngineData
  │     ├─ Load xvaexplainmarket.xml → TodaysMarketParameters
  │     └─ Load sensitivity_explain.xml → SensitivityScenarioData
  │
  └─ analytics() [oreapp.cpp:234]
     ├─ Settings::instance().evaluationDate() = inputs_->asof() [oreapp.cpp:242]
     ├─ InstrumentConventions::instance().setConventions() [oreapp.cpp:247]
     ├─ buildCsvLoader(params_) [oreapp.cpp:254]
     │  └─ CSVLoader(marketFiles, fixingFiles, ...) [oreapp.cpp:229]
     │     ├─ Read marketdata.csv
     │     ├─ Read fixings.csv
     │     └─ Parse into quotes map
     │
     ├─ analyticsManager_ = make_shared<AnalyticsManager>() [oreapp.cpp:258]
     ├─ analyticsManager_->initialise() [analyticsmanager.cpp]
     │  └─ For each <Analytic> in XML:
     │     ├─ AnalyticFactory::build("npv", ...) → NpvAnalytic
     │     ├─ AnalyticFactory::build("cashflow", ...) → CashflowAnalytic
     │     └─ AnalyticFactory::build("xvaExplain", ...) → XvaExplainAnalytic
     │        └─ XvaExplainAnalyticImpl() [xvaexplainanalytic.cpp:172]
     │           ├─ setLabel("XVA_EXPLAIN") [xvaexplainanalytic.cpp:174]
     │           └─ Calculate mporDate_ [xvaexplainanalytic.cpp:175-177]
     │
     └─ analyticsManager_->runAnalytics() [analyticsmanager.cpp]
        └─ For each analytic:
           └─ XvaExplainAnalytic::runAnalytic() [xvaexplainanalytic.cpp:188]
              ├─ analytic()->buildMarket(loader) [analytic.cpp]
              │  └─ TodaysMarket::TodaysMarket() [todaysmarket.cpp]
              │     ├─ buildDiscountCurve("EUR") [todaysmarket.cpp]
              │     │  ├─ Get quotes from loader
              │     │  ├─ Create RateHelpers (Deposit, Swap, ...)
              │     │  └─ Bootstrap PiecewiseYieldCurve
              │     ├─ buildIndexCurve("EUR-EURIBOR-6M") [todaysmarket.cpp]
              │     ├─ buildFXSpots() [todaysmarket.cpp]
              │     ├─ buildSwaptionVols() [todaysmarket.cpp]
              │     └─ buildDefaultCurves("CPTY_A") [todaysmarket.cpp]
              │
              ├─ analytic()->buildPortfolio() [analytic.cpp]
              │  └─ portfolio_->build(engineFactory) [portfolio.cpp]
              │     └─ For each trade:
              │        ├─ Swap::build() [swap.cpp]
              │        │  ├─ Parse XML → C++ objects
              │        │  ├─ makeFixedLeg() → QuantLib::Leg
              │        │  ├─ makeIborLeg() → QuantLib::Leg
              │        │  ├─ Create QuantLib::Swap instrument
              │        │  └─ Set DiscountingSwapEngine
              │        └─ trade->instrument()->NPV() (test pricing)
              │
              ├─ createStressTestData(loader) [xvaexplainanalytic.cpp:244]
              │  ├─ Compute t0 par rates [xvaexplainanalytic.cpp:247-256]
              │  │  └─ ParScenarioAnalytic::runAnalytic()
              │  │     └─ For each risk factor: compute par rate
              │  │
              │  ├─ Compute t1 par rates [xvaexplainanalytic.cpp:258-267]
              │  │  ├─ Settings::instance().evaluationDate() = mporDate_
              │  │  └─ ParScenarioAnalytic::runAnalytic()
              │  │
              │  └─ Generate stress scenarios [xvaexplainanalytic.cpp:300-398]
              │     └─ For each risk factor:
              │        ├─ shift = par_t1 - par_t0 [xvaexplainanalytic.cpp:304]
              │        ├─ if |shift| > threshold:
              │        │  ├─ Create scenario with label = to_string(key)
              │        │  └─ Add to scenarioData
              │        └─ Create "t1" scenario with all shifts
              │
              ├─ ParStressTestConverter::convertStressScenarioData() [xvaexplainanalytic.cpp:213]
              │  └─ Convert par shifts to zero shifts
              │
              ├─ XvaStressAnalytic::runAnalytic() [xvaexplainanalytic.cpp:225]
              │  └─ For each scenario:
              │     ├─ Build stressed market
              │     │  └─ Apply shifts to curves/surfaces
              │     ├─ Reprice portfolio
              │     │  └─ For each trade:
              │     │     ├─ trade->instrument()->NPV()
              │     │     └─ DiscountingSwapEngine::calculate()
              │     │        └─ CashFlows::npv(leg, discountCurve)
              │     ├─ Calculate exposures (EPE/ENE)
              │     └─ Compute CVA
              │        └─ CVA = LGD × ∑ EE(t) × PD(t) × DF(t)
              │
              ├─ XvaExplainResults(xvaReport) [xvaexplainanalytic.cpp:229]
              │  └─ Parse CVA results by scenario [xvaexplainanalytic.cpp:135-166]
              │     ├─ baseCvaData_["BASE"]
              │     ├─ fullRevalCva_["t1"]
              │     └─ fullRevalScenarioCva_[riskFactor]
              │
              ├─ ReportWriter::writeXvaExplainReport() [xvaexplainanalytic.cpp:232]
              │  └─ Generate detailed attribution report
              │
              └─ ReportWriter::writeXvaExplainSummary() [xvaexplainanalytic.cpp:236]
                 └─ Generate summary report
```

---

## Appendix A: Key Files Reference

| File | Purpose | Key Lines |
|------|---------|-----------|
| `Examples/ore_wrapper.py` | Python entry point | 16-21 |
| `OREAnalytics/orea/app/parameters.cpp` | XML parsing | - |
| `OREAnalytics/orea/app/oreapp.cpp` | Main orchestration | 435-481 |
| `OREAnalytics/orea/app/oreapp.cpp` | Parameter loading | 345-407 |
| `OREAnalytics/orea/app/oreapp.cpp` | Analytics execution | 234-334 |
| `OREAnalytics/orea/app/analyticsmanager.cpp` | Analytics coordination | - |
| `OREAnalytics/orea/app/analytics/xvaexplainanalytic.cpp` | XVA Explain logic | 172-399 |
| `OREData/ored/portfolio/portfolio.cpp` | Portfolio building | - |
| `OREData/ored/portfolio/swap.cpp` | Swap trade building | - |
| `OREData/ored/marketdata/todaysmarket.cpp` | Market construction | - |
| `OREData/ored/portfolio/enginefactory.cpp` | Pricing engines | - |

---

## Appendix B: Configuration Files

| File | Purpose |
|------|---------|
| `Input/ore_explain.xml` | Main configuration (asof, paths, analytics) |
| `Input/portfolio_explain.xml` | Trade definitions |
| `Input/marketdata.csv` | Market quotes |
| `Input/fixings.csv` | Historical fixings |
| `Input/curveconfig.xml` | Curve specifications |
| `Input/conventions.xml` | Market conventions |
| `Input/todaysmarket.xml` | Today's market config |
| `Input/pricingengine.xml` | Pricing engine selection |
| `Input/xvaexplainmarket.xml` | XVA explain market config |
| `Input/sensitivity_explain.xml` | Risk factors to stress |

---

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **XVA** | X-Value Adjustments (CVA, DVA, FVA, etc.) |
| **CVA** | Credit Valuation Adjustment - cost of counterparty default risk |
| **DVA** | Debit Valuation Adjustment - benefit of own default risk |
| **FVA** | Funding Valuation Adjustment - cost of funding uncollateralized exposure |
| **MPOR** | Margin Period of Risk - time horizon for XVA explain (typically 1 day) |
| **Par Rate** | Market-observable rate that makes an instrument NPV=0 |
| **Zero Rate** | Risk-free rate used for discounting |
| **EPE** | Expected Positive Exposure - E[max(V, 0)] |
| **ENE** | Expected Negative Exposure - E[max(-V, 0)] |
| **LGD** | Loss Given Default - fraction lost if counterparty defaults |
| **PD** | Probability of Default |
| **Bootstrap** | Iterative process to construct yield curve from market quotes |
| **SWIG** | Simplified Wrapper and Interface Generator - C++ to Python bindings |