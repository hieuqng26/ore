# SA-CCR Execution Flow: How run_saccr.py Runs ore_saccr.xml

This document provides a detailed explanation of how the SA-CCR (Standardized Approach for Counterparty Credit Risk) calculation is executed in ORE, from the Python script through to the C++ analytics implementation.

## Table of Contents

1. [Overview](#overview)
2. [Python Script Entry Point](#1-python-script-entry-point)
3. [ORE Application Bootstrap](#2-ore-application-bootstrap)
4. [XML Configuration Parsing](#3-xml-configuration-parsing)
5. [Analytics Manager Initialization](#4-analytics-manager-initialization)
6. [SA-CCR Analytic Execution](#5-sa-ccr-analytic-execution)
7. [SACCR Engine Calculation](#6-saccr-engine-calculation)
8. [Report Generation](#7-report-generation)
9. [Complete Flow Diagram](#8-complete-flow-diagram)
10. [Key Data Structures](#9-key-data-structures)
11. [Key File Reference Table](#10-key-file-reference-table)

---

## Overview

The SA-CCR calculation in ORE follows this high-level flow:

```
run_saccr.py
    ↓
OreExample.run() → executes ore executable
    ↓
ore.cpp main() → creates OREApp
    ↓
OREApp::run() → initializes and runs analytics
    ↓
AnalyticsManager::runAnalytics() → runs all registered analytics
    ↓
SaCcrAnalyticImpl::runAnalytic() → builds market/portfolio and creates SACCR
    ↓
SACCR constructor → performs complete SA-CCR calculation
    ↓
Report generation → writes results to CSV files
```

---

## 1. Python Script Entry Point

**File:** [Examples/CreditRisk/run_saccr.py](../../Examples/CreditRisk/run_saccr.py)

### Code Flow

```python
# Line 9: Create OreExample helper instance
oreex = OreExample(sys.argv[1] if len(sys.argv)>1 else False)

# Line 18: Execute ore application with XML config
oreex.run("Input/ore_saccr.xml")
```

**`OreExample.run()` Method** ([Examples/ore_examples_helper.py:332-342](../../Examples/ore_examples_helper.py#L332-L342)):

```python
def run(self, xml):
    if not self.dry:
        if(self.use_python):
            # Python binding path (ORE-SWIG)
            res = subprocess.call([sys.executable, ore_wrapper.py, xml])
        else:
            # C++ executable path (default)
            res = subprocess.call([self.ore_exe, xml])  # Line 340
        if res != 0:
            raise Exception("Return Code was not Null.")
```

**Key Points:**
- `self.ore_exe` is located during initialization (lines 114-138)
- Typical path: `../../build/App/ore` or `../../../build/App/ore`
- The executable is called with a single argument: the ore.xml path
- Returns non-zero on error

---

## 2. ORE Application Bootstrap

**File:** [App/ore.cpp](../../App/ore.cpp)

### Main Function (lines 61-94)

```cpp
int main(int argc, char** argv) {
    // Line 75-78: Validate arguments
    if (argc != 2) {
        std::cout << "usage: ORE path/to/ore.xml" << endl;
        return -1;
    }

    // Line 80: Initialize all trade builders and analytics factories
    ore::analytics::initBuilders();

    // Line 82: Get XML file path
    string inputFile(argv[1]);

    try {
        // Line 85-86: Parse XML into Parameters object
        auto params = QuantLib::ext::make_shared<Parameters>();
        params->fromFile(inputFile);

        // Line 87: Create OREApp instance
        OREApp ore(params, true);

        // Line 88: Execute analytics
        ore.run();

        return 0;
    } catch (const exception& e) {
        cout << "an error occurred: " << e.what() << endl;
        return -1;
    }
}
```

**Key Steps:**
1. **`initBuilders()`**: Registers all trade builders and analytics factories in global registries
2. **`Parameters::fromFile()`**: Parses ore.xml into a generic key-value structure
3. **`OREApp` construction**: Creates application instance with parameters
4. **`ore.run()`**: Executes the complete analytics workflow

---

## 3. XML Configuration Parsing

### 3.1 ore_saccr.xml Structure

**File:** [Examples/CreditRisk/Input/ore_saccr.xml](../../Examples/CreditRisk/Input/ore_saccr.xml)

```xml
<ORE>
  <Setup>
    <Parameter name="asofDate">2016-02-05</Parameter>
    <Parameter name="inputPath">Input/SA-CCR</Parameter>
    <Parameter name="outputPath">Output/SA-CCR</Parameter>
    <Parameter name="marketDataFile">../../../Input/market_20160205_flat.txt</Parameter>
    <Parameter name="portfolioFile">portfolio.xml</Parameter>
    <Parameter name="counterpartyFile">counterparty.xml</Parameter>
    <!-- ... more setup parameters ... -->
  </Setup>

  <Markets>
    <Parameter name="pricing">xois_eur</Parameter>
    <Parameter name="simulation">xois_eur</Parameter>
  </Markets>

  <Analytics>
    <Analytic type="npv">
      <Parameter name="active">Y</Parameter>
      <Parameter name="baseCurrency">EUR</Parameter>
    </Analytic>

    <Analytic type="saccr">
      <Parameter name="active">Y</Parameter>
      <Parameter name="csaFile">netting.xml</Parameter>
      <Parameter name="collateralBalancesFile">collateralbalances.xml</Parameter>
    </Analytic>
  </Analytics>
</ORE>
```

### 3.2 Parameters Parsing

**File:** [OREAnalytics/orea/app/parameters.cpp:65-124](../../OREAnalytics/orea/app/parameters.cpp#L65-L124)

```cpp
void Parameters::fromFile(const string& fileName) {
    LOG("load ORE configuration from " << fileName);
    clear();

    // Line 68-70: Parse XML document
    XMLDocument doc(fileName);
    fromXML(doc.getFirstNode("ORE"));

    LOG("load ORE configuration from " << fileName << " done.");
}

void Parameters::fromXML(XMLNode* node) {
    // Lines 78-86: Parse Setup section
    XMLNode* setupNode = XMLUtils::getChildNode(node, "Setup");
    map<string, string> setupMap;
    for (XMLNode* child = XMLUtils::getChildNode(setupNode, "Parameter");
         child; child = XMLUtils::getNextSibling(child)) {
        string name = XMLUtils::getAttribute(child, "name");
        setupMap[name] = XMLUtils::getNodeValue(child);
    }
    data_["setup"] = setupMap;

    // Lines 99-108: Parse Markets section
    XMLNode* marketsNode = XMLUtils::getChildNode(node, "Markets");
    map<string, string> marketsMap;
    // ... similar parsing logic ...
    data_["markets"] = marketsMap;

    // Lines 110-123: Parse Analytics section
    XMLNode* analyticsNode = XMLUtils::getChildNode(node, "Analytics");
    for (XMLNode* child = XMLUtils::getChildNode(analyticsNode, "Analytic");
         child; child = XMLUtils::getNextSibling(child)) {
        string type = XMLUtils::getAttribute(child, "type");
        map<string, string> analyticMap;
        // Parse parameters for this analytic
        for (XMLNode* paramNode = XMLUtils::getChildNode(child, "Parameter");
             paramNode; paramNode = XMLUtils::getNextSibling(paramNode)) {
            string name = XMLUtils::getAttribute(paramNode, "name");
            analyticMap[name] = XMLUtils::getNodeValue(paramNode);
        }
        data_[type] = analyticMap;
    }
}
```

**Result:** Parameters stored as `data_[groupName][paramName] = value`

### 3.3 InputParameters Construction

**File:** [OREAnalytics/orea/app/oreapp.cpp:344-407](../../OREAnalytics/orea/app/oreapp.cpp#L344-L407)

```cpp
void OREApp::initFromParams() {
    // Line 401: Create and populate InputParameters from Parameters
    inputs_ = QuantLib::ext::make_shared<OREAppInputParameters>(params_);
    inputs_->loadParameters();

    // Line 403: Create output parameters
    outputs_ = QuantLib::ext::make_shared<OutputParameters>(params_);
}
```

**File:** [OREAnalytics/orea/app/oreapp.cpp:630-1450](../../OREAnalytics/orea/app/oreapp.cpp#L630-L1450)

```cpp
void OREAppInputParameters::loadParameters() {
    // Lines 640-670: Load setup parameters
    setAsOfDate(params_->get("setup", "asofDate"));
    setBaseCurrency(params_->get("setup", "baseCurrency"));
    filesystem::path inputPath = params_->get("setup", "inputPath");
    std::string outputPath = params_->get("setup", "outputPath");
    setResultsPath(outputPath);

    // Lines 774-817: Load configuration files
    string conventionsFile = inputPath / params_->get("setup", "conventionsFile");
    setConventionsFromFile(conventionsFile);

    string pricingEnginesFile = inputPath / params_->get("setup", "pricingEnginesFile");
    setPricingEngineFromFile(pricingEnginesFile);

    string marketConfigFile = inputPath / params_->get("setup", "marketConfigFile");
    setTodaysMarketParamsFromFile(marketConfigFile);

    // Line 819: Load portfolio
    string portfolioFile = inputPath / params_->get("setup", "portfolioFile");
    setPortfolioFromFile(portfolioFile, inputPath);

    // Lines 830-850: Load counterparty and netting set data
    string counterpartyFile = params_->get("setup", "counterpartyFile", false);
    if (!counterpartyFile.empty()) {
        setCounterpartyManagerFromFile(inputPath / counterpartyFile);
    }

    // Lines 868-878: Parse NPV analytic
    string tmp = params_->get("npv", "active", false);
    if (!tmp.empty() && parseBool(tmp)) {
        insertAnalytic("NPV");
    }

    // SA-CCR analytic parsing (approximate location - not shown in excerpts)
    tmp = params_->get("saccr", "active", false);
    if (!tmp.empty() && parseBool(tmp)) {
        insertAnalytic("SA_CCR");

        string csaFile = params_->get("saccr", "csaFile", false);
        if (!csaFile.empty()) {
            setNettingSetManagerFromFile(inputPath / csaFile);
        }

        string collBalFile = params_->get("saccr", "collateralBalancesFile", false);
        if (!collBalFile.empty()) {
            setCollateralBalancesFromFile(inputPath / collBalFile);
        }
    }
}
```

**Result:** `inputs_` now contains all parsed configuration including:
- As-of date, base currency, paths
- Market data configurations
- Portfolio, netting sets, counterparty data
- Set of active analytics: `{"NPV", "SA_CCR"}`

---

## 4. Analytics Manager Initialization

**File:** [OREAnalytics/orea/app/oreapp.cpp](../../OREAnalytics/orea/app/oreapp.cpp)

### OREApp::run() Method

```cpp
void OREApp::run() {
    // Initialize from parameters
    initFromParams();

    // Create analytics manager
    analyticsManager_ = QuantLib::ext::make_shared<AnalyticsManager>(
        inputs_,
        marketDataLoader_
    );

    // Initialize analytics (builds analytics from factory)
    analyticsManager_->initialise();

    // Run all analytics
    analyticsManager_->runAnalytics();

    // Write outputs
    // ...
}
```

### AnalyticsManager::initialise()

**File:** [OREAnalytics/orea/app/analyticsmanager.cpp:36-40](../../OREAnalytics/orea/app/analyticsmanager.cpp#L36-L40)

```cpp
void AnalyticsManager::initialise() {
    // Line 37-38: For each requested analytic type, build from factory
    for (const auto& a : inputs_->analytics()) {
        auto ap = AnalyticFactory::instance().build(a, inputs_, shared_from_this(), true);
    }
    initialised_ = true;
}
```

**How Analytics are Built:**
1. `inputs_->analytics()` returns `{"NPV", "SA_CCR"}`
2. For `"SA_CCR"`:
   - `AnalyticFactory::instance().build("SA_CCR", ...)` is called
   - Factory looks up registered builder for "SA_CCR"
   - Creates `SaCcrAnalytic` instance
   - `SaCcrAnalytic` constructor creates `SaCcrAnalyticImpl`
   - Analytic is automatically registered with AnalyticsManager

**File:** [OREAnalytics/orea/app/analytics/saccranalytic.hpp:41-45](../../OREAnalytics/orea/app/analytics/saccranalytic.hpp#L41-L45)

```cpp
class SaCcrAnalytic : public Analytic {
public:
    SaCcrAnalytic(const QuantLib::ext::shared_ptr<InputParameters>& inputs,
                  const QuantLib::ext::weak_ptr<AnalyticsManager>& analyticsManager)
        : Analytic(std::make_unique<SaCcrAnalyticImpl>(inputs),
                   {"SA_CCR"}, inputs, analyticsManager) {}

    const QuantLib::ext::shared_ptr<SACCR> saccr() const { return saccr_; }
    void setSaccr(QuantLib::ext::shared_ptr<SACCR> saccr) { saccr_ = saccr; }

private:
    QuantLib::ext::shared_ptr<SACCR> saccr_;
};
```

### AnalyticsManager::runAnalytics()

**File:** [OREAnalytics/orea/app/analyticsmanager.cpp:94-186](../../OREAnalytics/orea/app/analyticsmanager.cpp#L94-L186)

```cpp
void AnalyticsManager::runAnalytics(
    const QuantLib::ext::shared_ptr<MarketCalibrationReportBase>& marketCalibrationReport) {

    QL_REQUIRE(initialised_, "AnalyticsManager has not been initialised");

    // Lines 100-139: Load market data if required
    if (std::any_of(analytics_.begin(), analytics_.end(),
                    [](const auto& a) { return a.second->requiresMarketData(); })) {

        // Collect all market dates needed
        std::set<Date> marketDates;
        for (const auto& a : analytics_) {
            auto mdates = a.second->marketDates();
            marketDates.insert(mdates.begin(), mdates.end());
        }

        // Load market data
        marketDataLoader_->populateLoader(tmps, marketDates);

        // Generate market data reports
        // ... (lines 121-138)
    }

    // Lines 142-156: Run each analytic
    for (auto a : analytics_) {
        LOG("run analytic with label '" << a.first << "'");
        a.second->startTimer("Run " + a.second->label() + "Analytic");
        try {
            // Line 146: Main analytic execution
            a.second->runAnalytic(marketDataLoader_->loader(), inputs_->analytics());
        } catch (const exception& e) {
            failedAnalytics_.push_back(a.first);
            StructuredAnalyticsErrorMessage(a.first, "Failed Analytic", e.what());
        }
        a.second->stopTimer("Run " + a.second->label() + "Analytic");
        LOG("run analytic with label '" << a.first << "' finished.");
    }

    // Lines 158-186: Write statistics and timing reports
    // ...
}
```

---

## 5. SA-CCR Analytic Execution

**File:** [OREAnalytics/orea/app/analytics/saccranalytic.cpp:41-114](../../OREAnalytics/orea/app/analytics/saccranalytic.cpp#L41-L114)

### SaCcrAnalyticImpl::runAnalytic()

```cpp
void SaCcrAnalyticImpl::runAnalytic(
    const QuantLib::ext::shared_ptr<InMemoryLoader>& loader,
    const std::set<std::string>& runTypes) {

    LOG("SaCcrAnalytic::runAnalytic called");

    // Line 46-47: Get typed analytic pointer
    auto saccrAnalytic = static_cast<SaCcrAnalytic*>(analytic());
    QL_REQUIRE(saccrAnalytic, "Analytic must be of type SaCcrAnalytic");

    // Line 49: Initialize reports map
    std::map<SACCR::ReportType, QuantLib::ext::shared_ptr<Report>> saccrReports;

    // Line 51: Create collateral balances holder
    auto calculatedCollateralBalances = QuantLib::ext::make_shared<CollateralBalances>();

    // Line 53-54: Build market and portfolio
    analytic()->buildMarket(loader);
    analytic()->buildPortfolio();

    // Line 56: Enrich index fixings for portfolio
    analytic()->enrichIndexFixings(analytic()->portfolio());

    // Line 58: Get market configuration
    auto marketConfig = inputs_->marketConfig("pricing");

    // Lines 61-79: Write intermediate reports if requested
    if (analytic()->getWriteIntermediateReports()) {
        if (inputs_->outputAdditionalResults()) {
            LOG("Write additional results for SA-CCR");
            path addResultsReportPath = inputs_->resultsPath() / "additional_results.csv";
            CSVFileReport addResultsWithoutReport(addResultsReportPath.string(), ...);
            ReportWriter(inputs_->reportNaString())
                .writeAdditionalResultsReport(addResultsWithoutReport,
                                             analytic()->portfolio(),
                                             analytic()->market(),
                                             marketConfig,
                                             inputs_->baseCurrency());
        }

        LOG("Write cashflow report for SA-CCR");
        boost::filesystem::path cfReportPath = inputs_->resultsPath() / "cashflow.csv";
        CSVFileReport cfReport(cfReportPath.string(), ...);
        ReportWriter(inputs_->reportNaString())
            .writeCashflow(cfReport, inputs_->baseCurrency(),
                          analytic()->portfolio(),
                          analytic()->market(),
                          marketConfig);
    }

    // Lines 82-92: Load configuration data (or use defaults)
    auto& collateralBalances = inputs_->collateralBalances()
        ? inputs_->collateralBalances()
        : QuantLib::ext::make_shared<CollateralBalances>();

    auto& nettingSetManager = inputs_->nettingSetManager()
        ? inputs_->nettingSetManager()
        : QuantLib::ext::make_shared<NettingSetManager>();

    auto& counterpartyManager = inputs_->counterpartyManager()
        ? inputs_->counterpartyManager()
        : QuantLib::ext::make_shared<CounterpartyManager>();

    // Lines 94-98: Create in-memory reports
    QuantLib::ext::shared_ptr<InMemoryReport> saCcrReport =
        QuantLib::ext::make_shared<InMemoryReport>();
    QuantLib::ext::shared_ptr<InMemoryReport> saCcrDetailReport =
        QuantLib::ext::make_shared<InMemoryReport>();

    saccrReports[SACCR::ReportType::Summary] = saCcrReport;
    saccrReports[SACCR::ReportType::Detail] = saCcrDetailReport;

    // Lines 101-104: Create SACCR engine (this performs the calculation!)
    auto saccr = QuantLib::ext::make_shared<SACCR>(
        analytic()->portfolio(),           // Portfolio of trades
        nettingSetManager,                  // Netting set definitions
        counterpartyManager,                // Counterparty information
        analytic()->market(),              // Market data
        inputs_->baseCurrency(),           // Base currency
        collateralBalances,                // User-provided collateral
        calculatedCollateralBalances,      // Computed collateral
        inputs_->simmNameMapper(),         // SIMM name mapper
        inputs_->simmBucketMapper(),       // SIMM bucket mapper
        inputs_->refDataManager(),         // Reference data
        saccrReports                       // Output reports
    );

    // Line 105: Store SACCR instance in analytic
    saccrAnalytic->setSaccr(saccr);

    // Lines 108-110: Save collateral balances to XML
    path p = inputs_->resultsPath() / "collateralbalances.xml";
    LOG("Saving collateral balances to file: " << p.string());
    collateralBalances->toFile(p.string());

    // Lines 112-113: Register reports with analytic
    analytic()->addReport(label(), "saccr", saCcrReport);
    analytic()->addReport(label(), "saccr_detail", saCcrDetailReport);
}
```

**Key Points:**
1. **Market & Portfolio Building**: Uses market data loader and portfolio builder
2. **Configuration Managers**: Loads netting sets, counterparty data, collateral balances
3. **SACCR Constructor**: **This is where the entire calculation happens!**
4. **Reports Registration**: Makes results available to OREApp for writing to disk

---

## 6. SACCR Engine Calculation

**File:** [OREAnalytics/orea/engine/saccr.cpp:434-454](../../OREAnalytics/orea/engine/saccr.cpp#L434-L454)

### SACCR Constructor

```cpp
SACCR::SACCR(
    const QuantLib::ext::shared_ptr<Portfolio>& portfolio,
    const QuantLib::ext::shared_ptr<NettingSetManager>& nettingSetManager,
    const QuantLib::ext::shared_ptr<CounterpartyManager>& counterpartyManager,
    const QuantLib::ext::shared_ptr<Market>& market,
    const std::string& baseCurrency,
    const QuantLib::ext::shared_ptr<CollateralBalances>& collateralBalances,
    const QuantLib::ext::shared_ptr<CollateralBalances>& calculatedCollateralBalances,
    const QuantLib::ext::shared_ptr<SimmNameMapper>& nameMapper,
    const QuantLib::ext::shared_ptr<SimmBucketMapper>& bucketMapper,
    const QuantLib::ext::shared_ptr<ReferenceDataManager>& refDataManager,
    const std::map<ReportType, QuantLib::ext::shared_ptr<Report>>& outReports)
    : reports_(outReports), portfolio_(portfolio),
      nettingSetManager_(nettingSetManager),
      counterpartyManager_(counterpartyManager), market_(market),
      baseCurrency_(baseCurrency),
      collateralBalances_(collateralBalances),
      calculatedCollateralBalances_(calculatedCollateralBalances),
      nameMapper_(nameMapper), bucketMapper_(bucketMapper),
      refDataManager_(refDataManager) {

    // Line 444: Initialize data structures
    clear();

    // Line 445: Validate configurations
    validate();

    // Line 446: Extract trade details
    tradeDetails();

    // Line 447: Aggregate results
    aggregate();

    // Line 448: Combine collateral balances
    combineCollateralBalances();
}
```

**The constructor orchestrates the complete SA-CCR calculation in 5 steps:**

### Step 1: clear() - Initialize Data Structures

**File:** [OREAnalytics/orea/engine/saccr.cpp:418-432](../../OREAnalytics/orea/engine/saccr.cpp#L418-L432)

```cpp
void SACCR::clear() {
    nettingSetDetails_.clear();
    npvTotalCurrent_.clear();
    RC_.clear();
    AddOn_.clear();
    EAD_.clear();
    RW_.clear();
    CC_.clear();
    tradeData_.clear();
}
```

Clears all internal maps for:
- `RC_`: Replacement Cost per netting set
- `AddOn_`: Add-on (PFE) per netting set
- `EAD_`: Exposure at Default per netting set
- `RW_`: Risk Weight per netting set
- `CC_`: Capital Charge per netting set

### Step 2: validate() - Validate Configurations

**File:** [OREAnalytics/orea/engine/saccr.cpp:1068-1380](../../OREAnalytics/orea/engine/saccr.cpp#L1068-L1380)

```cpp
void SACCR::validate() {
    // Lines 1076-1097: Validate configuration files exist
    if (!nettingSetManager_ || nettingSetManager_->empty()) {
        LOG("NettingSetManager is empty - using defaults");
    }

    if (!collateralBalances_ || collateralBalances_->empty()) {
        LOG("CollateralBalances is empty - using defaults");
    }

    if (!counterpartyManager_ || counterpartyManager_->empty()) {
        LOG("CounterpartyManager is empty - using defaults");
    }

    // Lines 1105-1129: Validate netting set definitions for all trades
    for (const auto& trade : portfolio_->trades()) {
        string nettingSetId = trade->envelope().nettingSetId();

        // Create default netting set if missing
        if (!nettingSetManager_->has(nettingSetId)) {
            WLOG("No netting set definition for " << nettingSetId
                 << " - creating default");

            NettingSetDefinition def;
            def.setNettingSetId(nettingSetId);
            def.setActiveCsaFlag(true);

            CSADetails csa;
            csa.setMpor("2W");  // Default: 2 weeks
            csa.setThreshold(0);
            csa.setMinimumTransferAmount(0);
            def.setCsaDetails(csa);

            nettingSetManager_->add(def);
        }
    }

    // Lines 1131-1380: Validate collateral balance configurations
    // Checks consistency between CSA definitions and collateral specifications
    // ...
}
```

### Step 3: tradeDetails() - Extract Trade Information

**File:** [OREAnalytics/orea/engine/saccr.cpp:1392-1593](../../OREAnalytics/orea/engine/saccr.cpp#L1392-L1593)

```cpp
void SACCR::tradeDetails() {
    LOG("SACCR: Extract trade details");

    // Lines 1395-1423: Load NPVs from optional report
    std::map<std::string, Real> tradeNPVs;
    if (reports_.find(ReportType::TradeNPV) != reports_.end()) {
        // Extract NPVs from pre-computed report
        // ...
    }

    // Lines 1440-1593: Process each trade
    for (const auto& trade : portfolio_->trades()) {
        TradeData td;

        // Basic information
        td.id = trade->id();
        td.type = trade->tradeType();
        td.cpty = trade->envelope().counterparty();
        td.nettingSetDetails = trade->envelope().nettingSetId();

        // Lines 1460-1475: Extract NPV
        if (tradeNPVs.find(td.id) != tradeNPVs.end()) {
            td.NPV = tradeNPVs[td.id];
        } else {
            Real npvBase = trade->instrument()->NPV();
            string npvCurrency = trade->npvCurrency();

            // Convert to base currency if needed
            if (npvCurrency != baseCurrency_) {
                Real fxRate = getFxRate(npvCurrency, baseCurrency_);
                td.NPV = npvBase * fxRate;
            } else {
                td.NPV = npvBase;
            }
        }

        // Lines 1480-1510: Determine asset class
        td.assetClass = getAssetClass(td.type);

        // Lines 1512-1540: Calculate maturity parameters
        // M: Time to maturity (years)
        // S: Start date (first exercise for options)
        // E: End date (underlying maturity)
        // T: Latest exercise date
        td.M = calculateMaturity(trade);
        td.S = calculateStartDate(trade);
        td.E = calculateEndDate(trade);
        td.T = calculateExerciseDate(trade);

        // Lines 1542-1560: Calculate current notional
        td.currentNotional = getCurrentNotional(trade, td.assetClass);

        // Lines 1562-1570: Calculate supervisory duration
        td.supervisoryDuration = getSupervisoryDuration(td.M);

        // Lines 1572-1580: Calculate delta adjustment
        td.delta = getDelta(trade, td.assetClass);

        // Lines 1582-1585: Calculate effective notional (d)
        td.d = td.delta * td.supervisoryDuration * td.currentNotional;

        // Lines 1587-1590: Assign hedging set and subset
        td.hedgingSet = getHedgingSet(trade, td.assetClass);
        td.hedgingSubset = getHedgingSubset(trade, td.assetClass);

        // Store trade data
        tradeData_.push_back(td);
    }
}
```

**Key Calculations:**

#### getCurrentNotional() - [saccr.cpp:905-1066](../../OREAnalytics/orea/engine/saccr.cpp#L905-L1066)

```cpp
Real SACCR::getCurrentNotional(const QuantLib::ext::shared_ptr<Trade>& trade,
                               SACCR::AssetClass assetClass,
                               const string& baseCcy,
                               const DayCounter& dc,
                               Real& currentPrice1,
                               Real& currentPrice2,
                               const string& hedgingSet,
                               const string& hedgingSubset) {

    const Date& today = Settings::instance().evaluationDate();
    Real currentNotional = Null<Real>();

    // FX Derivatives (FxForward, FxOption, FxBarrierOption)
    if (trade->tradeType() == "FxForward" || trade->tradeType() == "FxOption" ||
        trade->tradeType() == "FxBarrierOption") {
        // Extract bought/sold currencies and amounts
        string boughtCcy, soldCcy;
        Real boughtAmount, soldAmount;
        // ... extract from trade ...

        // Convert to base currency (ignoring home currency leg)
        Real boughtFx = getFxRate(boughtCcy);
        Real soldFx = getFxRate(soldCcy);
        Real boughtNotional = (boughtCcy == baseCcy) ? 0.0 : boughtAmount * boughtFx;
        Real soldNotional = (soldCcy == baseCcy) ? 0.0 : soldAmount * soldFx;

        // Current notional = max of the two legs
        currentNotional = std::max(boughtNotional, soldNotional);
    }

    // FX Touch Options
    else if (trade->tradeType() == "FxTouchOption") {
        auto fxOpt = dynamic_pointer_cast<FxTouchOption>(trade);
        Real fx = getFxRate(fxOpt->payoffCurrency());
        currentNotional = fx * fxOpt->payoffAmount();
    }

    // Equity Options
    else if (trade->tradeType() == "EquityOption") {
        auto equityOption = dynamic_pointer_cast<EquityOption>(trade);
        Real quantity = equityOption->quantity();
        Real fx = getFxRate(equityOption->notionalCurrency());

        // Current equity price from market
        currentPrice1 = market_->equityCurve(equityOption->equityName())
            ->fixing(market_->equityCurve(equityOption->equityName())
                         ->fixingCalendar().adjust(today)) * fx;

        currentNotional = quantity * currentPrice1;
    }

    // Total Return Swaps (Equity)
    else if (trade->tradeType() == "TotalReturnSwap") {
        auto trs = dynamic_pointer_cast<TRS>(trade);
        const string& equityName = /* extract from underlying */;
        Real fx = getFxRate(market_->equityCurve(equityName)->currency().code());

        currentPrice1 = market_->equityCurve(equityName)
            ->fixing(market_->equityCurve(equityName)->fixingCalendar().adjust(today)) * fx;

        const auto& underlyingTrade = trs->underlying().front();
        if (underlyingTrade->tradeType() == "EquityPosition") {
            auto equityPosition = dynamic_pointer_cast<EquityPosition>(underlyingTrade);
            currentNotional = currentPrice1 * equityPosition->data().quantity();
        }
        // Similar for EquityOptionPosition
    }

    // Commodity Forwards
    else if (trade->tradeType() == "CommodityForward") {
        auto commFwd = dynamic_pointer_cast<CommodityForward>(trade);
        currentNotional = commFwd->currentNotional() * getFxRate(trade->notionalCurrency());
        currentPrice1 = currentNotional / commFwd->quantity();
    }

    // Commodity Swaps (including basis swaps)
    else if (trade->tradeType() == "CommoditySwap") {
        auto commoditySwap = dynamic_pointer_cast<CommoditySwap>(trade);
        // Handle basis swaps vs single commodity swaps
        // Aggregate leg notionals considering payer/receiver
        for (Size i = 0; i < commoditySwap->legCurrencies().size(); i++) {
            if (commoditySwap->legData().at(i).legType() == LegType::CommodityFloating) {
                Real multiplier = commoditySwap->legData()[i].isPayer() ? -1 : 1;
                Real legCurrentNotional = getLegAverageNotional(commoditySwap, i, dc, ...) * multiplier;
                // Aggregate or take max
                if (currentNotional == Null<Real>())
                    currentNotional = legCurrentNotional;
                else
                    currentNotional += legCurrentNotional;
            }
        }
    }

    // Interest Rate Swaps and other leg-based trades
    else if (trade->legCurrencies().size() > 0) {
        for (Size i = 0; i < trade->legCurrencies().size(); i++) {
            // For FX swaps, skip base currency leg
            if (assetClass == AssetClass::FX && trade->legCurrencies().at(i) == baseCcy)
                continue;

            Real legCurrentNotional = getLegAverageNotional(trade, i, dc, ...);

            if (currentNotional == Null<Real>())
                currentNotional = legCurrentNotional;
            else
                currentNotional = std::max(currentNotional, legCurrentNotional);
        }
    }

    return currentNotional;
}
```

**Key Points:**
- For **FX derivatives**: Uses max of bought/sold legs converted to base currency (ignoring home currency leg)
- For **Equity derivatives**: Current stock price × quantity
- For **Commodity derivatives**: Current commodity price × quantity
- For **Interest Rate swaps**: Average notional across cashflows (via `getLegAverageNotional`)
- For **cross-currency swaps**: Takes max notional across legs (excluding base currency leg)

#### getDelta() - [saccr.cpp:638-788](../../OREAnalytics/orea/engine/saccr.cpp#L638-L788)

**Purpose:** The delta adjustment captures the direction and magnitude of a trade's exposure to its primary risk factor. For linear products (swaps, forwards), delta is ±1 indicating long/short direction. For options, delta is calculated using the supervisory option pricing formula to account for non-linear exposure.

**First Risk Factor:** To ensure consistent aggregation within a hedging set, all trades must use the same convention for determining the sign of their exposure. The "first risk factor" is a canonical identifier (e.g., first currency in alphabetical order for FX, the floating index for IR) that all trades in the hedging set reference to determine their delta sign.

```cpp
Real SACCR::getDelta(const QuantLib::ext::shared_ptr<Trade>& trade,
                     TradeData& tradeData,
                     Date today) {

    Real delta = 1;
    Real multiplier = 1;

    // Get first risk factor for consistency within hedging set
    // Examples:
    // - FX: First currency in alphabetical order (e.g., "EUR" for EURUSD)
    // - IR: The floating index for basis swaps, empty for single-curve swaps
    // - Equity/Commodity: The underlying name or hedging subset
    string firstRiskfactor = getFirstRiskFactor(tradeData.hedgingSet,
                                                 tradeData.hedgingSubset,
                                                 tradeData.assetClass,
                                                 trade);

    // === Swaps (IR and FX) ===
    if (trade->tradeType() == "Swap") {
        auto swap = dynamic_pointer_cast<Swap>(trade);

        if (tradeData.assetClass == AssetClass::FX) {
            // FX Swap: +1 if receiving first currency, -1 if paying
            for (auto leg : swap->legData()) {
                if (leg.currency() == firstRiskfactor) {
                    multiplier = leg.isPayer() ? -1 : 1;
                    break;
                }
            }
        }
        else if (tradeData.assetClass == AssetClass::IR) {
            // IR Swap: +1 if receiving float, -1 if paying float
            for (const auto& leg : swap->legData()) {
                if (leg.legType() == LegType::Floating) {
                    multiplier = leg.isPayer() ? -1 : 1;
                    break;
                }
            }
        }
    }

    // === Total Return Swaps ===
    else if (trade->tradeType() == "TotalReturnSwap") {
        auto trs = dynamic_pointer_cast<TRS>(trade);
        delta = trs->returnData().payer() ? -1 : 1;

        // If underlying is an option, apply option delta
        const auto& underlyingTrade = trs->underlying().front();
        if (underlyingTrade->tradeType() == "EquityOptionPosition") {
            bool flipTrade = false;
            tradeData.strike = getOptionStrike(underlyingTrade, flipTrade);
            tradeData.price = getOptionPrice(underlyingTrade);

            const auto& [callPut, boughtSold] = getOptionType(underlyingTrade, flipTrade);
            multiplier *= callPut * boughtSold;

            Real sigma = getSupervisoryOptionVolatility(tradeData);
            delta *= phi(tradeData.price, tradeData.strike, tradeData.T, sigma, callPut);
        }
    }

    // === Swaptions ===
    else if (trade->tradeType() == "Swaption") {
        if (tradeData.assetClass == AssetClass::IR) {
            tradeData.strike = getOptionStrike(trade);

            // Get ATM forward from additional results
            const auto& ar = trade->instrument()->additionalResults();
            tradeData.price = boost::any_cast<Real>(ar.at("atmForward"));

            Real sigma = 0.5;  // Supervisory volatility for IR = 50%

            const auto& [callPut, boughtSold] = getOptionType(trade, false);
            multiplier = callPut * boughtSold;

            // Apply option delta formula: phi(P, K, T, sigma)
            delta = phi(tradeData.price, tradeData.strike, tradeData.T, sigma, callPut);
        }
    }

    // === FX Forwards ===
    else if (trade->tradeType() == "FxForward") {
        auto fxFwd = dynamic_pointer_cast<FxForward>(trade);
        string boughtCcy = fxFwd->boughtCurrency();
        // +1 if bought currency = first risk factor, -1 otherwise
        multiplier = (firstRiskfactor == boughtCcy) ? 1 : -1;
    }

    // === FX Options and Equity Options ===
    else if (trade->tradeType() == "FxOption" || trade->tradeType() == "FxBarrierOption" ||
             trade->tradeType() == "FxTouchOption" || trade->tradeType() == "EquityOption") {

        bool flipTrade = false;
        Real sigma;

        if (trade->tradeType() == "EquityOption") {
            // Equity: sigma from supervisory volatility (75% for index, 120% for single name)
            sigma = getSupervisoryOptionVolatility(tradeData);
            tradeData.strike = getOptionStrike(trade, flipTrade);
            tradeData.price = getOptionPrice(trade);
        }
        else {
            // FX: sigma = 15% supervisory volatility
            sigma = 0.15;

            // Ensure consistent currency pair ordering within hedging set
            string origBoughtCcy, origSoldCcy;
            getFxCurrencies(trade, origBoughtCcy, origSoldCcy);

            flipTrade = (firstRiskfactor != origBoughtCcy);

            string boughtCcy = flipTrade ? origSoldCcy : origBoughtCcy;
            string soldCcy = flipTrade ? origBoughtCcy : origSoldCcy;

            // Calculate forward FX rate
            Real disc1near = market_->discountCurve(boughtCcy)->discount(today);
            Real disc1far = market_->discountCurve(boughtCcy)->discount(trade->maturity());
            Real disc2near = market_->discountCurve(soldCcy)->discount(today);
            Real disc2far = market_->discountCurve(soldCcy)->discount(trade->maturity());
            Real fxfwd = disc1near / disc1far * disc2far / disc2near *
                         market_->fxRate(boughtCcy + soldCcy)->value();
            tradeData.price = fxfwd;

            tradeData.strike = getOptionStrike(trade, flipTrade);
        }

        const auto& [callPut, boughtSold] = getOptionType(trade, flipTrade);
        multiplier = callPut * boughtSold;

        // Apply option delta: phi(P, K, T, sigma)
        delta = phi(tradeData.price, tradeData.strike, tradeData.T, sigma, callPut);
    }

    // === Commodity Swaps ===
    else if (trade->tradeType() == "CommoditySwap") {
        auto swap = dynamic_pointer_cast<CommoditySwap>(trade);

        // Check if basis swap (two floating legs)
        if (swap->legData().at(0).legType() == LegType::CommodityFloating &&
            swap->legData().at(1).legType() == LegType::CommodityFloating) {
            // Basis swap: match by commodity name
            auto com = dynamic_pointer_cast<CommodityFloatingLegData>(
                swap->legData().at(0).concreteLegData());
            auto legData = com->name() == firstRiskfactor ?
                           swap->legData().at(0) : swap->legData().at(1);
            multiplier = legData.isPayer() ? -1 : 1;
        }
        else {
            // Single commodity swap: find floating leg
            auto legData = swap->legData().at(0).legType() == LegType::CommodityFloating ?
                           swap->legData().at(0) : swap->legData().at(1);
            multiplier = legData.isPayer() ? -1 : 1;
        }
    }

    // === Commodity Forwards ===
    else if (trade->tradeType() == "CommodityForward") {
        auto fwd = dynamic_pointer_cast<CommodityForward>(trade);
        Position::Type position = parsePositionType(fwd->position());
        multiplier = (position == Position::Long) ? 1 : -1;
    }

    delta *= multiplier;
    return delta;
}
```

**Key Points:**

1. **Linear Products** (Swaps, Forwards):
   - **IR Swaps**: δ = +1 if receiving floating, -1 if paying floating
   - **FX Swaps/Forwards**: δ = +1 if bought currency matches first risk factor, -1 otherwise
   - **Commodity Swaps/Forwards**: δ = +1 for long/receiver, -1 for short/payer

2. **Options** (Swaptions, FX Options, Equity Options):
   - Uses **phi function**: `phi(P, K, T, σ, callPut)` which implements option delta formula
   - **P** = current price (spot for equity, forward for FX, ATM forward for swaptions)
   - **K** = strike price
   - **T** = time to maturity
   - **σ** = supervisory volatility (0.5 for IR, 0.15 for FX, 0.75/1.2 for Equity)
   - **Multiplier** accounts for call/put and bought/sold direction

3. **Consistency within Hedging Set**:
   - Delta sign must be consistent for all trades in the same hedging set
   - Achieved by using `firstRiskfactor` to determine sign conventions
   - For FX: ensures same currency pair ordering across all FX options in hedging set

#### getSupervisoryDuration() - [saccr.cpp:594-600](../../OREAnalytics/orea/engine/saccr.cpp#L594-L600)

**Purpose:** Supervisory Duration (SD) measures the effective time-weighted exposure of interest rate and credit derivatives. It accounts for the present value sensitivity to parallel shifts in interest rates, similar to modified duration in bond mathematics. The exponential decay formula reflects that exposures further in the future contribute less to current risk due to discounting.

**Rationale for the Formula:** The formula `SD = (exp(-0.05*S) - exp(-0.05*E)) / 0.05` represents the integrated area under an exponentially decaying exposure profile from start date S to end date E. The 5% decay rate (0.05) is a supervisory assumption representing a standardized discount rate. This provides a simple, model-independent measure of interest rate sensitivity across the life of the derivative.

```cpp
Real SACCR::getSupervisoryDuration(const TradeData& tradeData) {
    Real SD = Null<Real>();
    if (tradeData.assetClass == SACCR::AssetClass::IR ||
        tradeData.assetClass == SACCR::AssetClass::Credit) {
        // For IR and Credit: SD = (exp(-0.05*S) - exp(-0.05*E)) / 0.05
        // where S = start date (years from today)
        //       E = end date (years from today)
        // The 0.05 represents a 5% supervisory discount rate
        SD = (std::exp(-0.05 * tradeData.S) - std::exp(-0.05 * tradeData.E)) / 0.05;
    }
    return SD;
}
```

**Note:** Supervisory duration is only calculated for Interest Rate and Credit asset classes. For FX, Equity, and Commodity derivatives, SD is not used (remains Null). The effective notional for these asset classes is calculated differently - they use maturity factors (MF) instead of supervisory duration.

---

#### Maturity Factor (MF) - [saccr.cpp:1496-1516](../../OREAnalytics/orea/engine/saccr.cpp#L1496-L1516)

**Purpose:** The Maturity Factor (MF) adjusts potential future exposure based on two key factors:
1. **Time to maturity**: Longer-dated trades have more uncertainty and thus higher potential exposure
2. **Collateralization**: Margined trades have shorter effective time horizons due to regular mark-to-market and collateral posting

MF serves a similar role to Supervisory Duration for non-IR/Credit asset classes, but with a simpler, time-based formula rather than the present-value-weighted approach used for interest rates.

**Derivation - Two Cases:**

```cpp
// Case 1: Margined/Collateralized Netting Sets (activeCsaFlag = true)
if (ndef->activeCsaFlag()) {
    Real MPORinWeeks = weeks(ndef->csaDetails()->marginPeriodOfRisk());

    // Special case: Large netting sets (> 5000 trades) for non-clearing counterparties
    if (tradeCount[nettingSetDetails] > 5000 && !cp->isClearingCP())
        MPORinWeeks = 4.0;  // 4 weeks = 20 business days

    // MF = 1.5 × sqrt(MPOR in years)
    tradeData.MF = 1.5 * std::sqrt(MPORinWeeks / 52.0);
}

// Case 2: Unmargined/Uncollateralized Netting Sets (activeCsaFlag = false)
else {
    // Floor maturity at 10 business days (2 weeks / 52)
    const Real m = std::max(tradeData.M, 2.0 / 52.0);

    // MF = sqrt(min(M, 1))
    // Caps at 1 year - beyond 1 year, no further scaling
    tradeData.MF = std::sqrt(std::min(m, 1.0));
}
```

**Key Parameters:**

1. **MPOR (Margin Period of Risk)**: The time between the last collateral exchange and closeout of positions after counterparty default
   - **Standard: 10 business days (2 weeks)** for non-centrally cleared derivatives
   - **5 business days (1 week)** for centrally cleared derivatives (clearing counterparties)
   - **20 business days (4 weeks)** for large netting sets (>5000 trades) with non-clearing counterparties
   - Can be doubled for netting sets with outstanding disputes (specified in CSA details)

2. **M (Maturity)**: Time to maturity in years (from tradeDetails phase)

**Formula Rationale:**

- **Margined case** `MF = 1.5 × sqrt(MPOR)`:
  - The **square root** reflects that exposure grows with the square root of time (similar to volatility scaling in option pricing)
  - The **1.5 multiplier** is a regulatory scalar that calibrates the formula to observed market exposure
  - **MPOR-based**: Uses margin period of risk rather than full maturity since collateral posting limits exposure horizon

- **Unmargined case** `MF = sqrt(min(M, 1))`:
  - Also uses **square root of time** for the same volatility-scaling reason
  - **Capped at 1 year**: Beyond 1 year, no additional scaling (conservative assumption that uncertainty doesn't grow unboundedly)
  - **Floored at 10 business days**: Minimum exposure horizon even for very short-dated trades

**Usage in Effective Notional:**

The maturity factor is always multiplied with the delta-adjusted notional:

```cpp
// Line 1547: For all asset classes
tradeData.d = tradeData.SD == Null<Real>()
              ? tradeData.currentNotional              // FX/Equity/Commodity
              : tradeData.SD * tradeData.currentNotional;  // IR/Credit

// Then in aggregate() phase (lines 1218, 1226):
// IR/Credit:     D_i += delta × d × MF = delta × SD × CurrentNotional × MF
// FX/Eq/Comm:    EffNotional += delta × d × MF = delta × CurrentNotional × MF
```

**Example Calculations:**

| Scenario | MPOR/Maturity | MF Calculation | MF Value |
|----------|---------------|----------------|----------|
| Margined, 10 bd MPOR | 2 weeks | 1.5 × sqrt(2/52) | **0.295** |
| Margined, 5 bd MPOR (CCP) | 1 week | 1.5 × sqrt(1/52) | **0.208** |
| Margined, large portfolio | 4 weeks | 1.5 × sqrt(4/52) | **0.416** |
| Unmargined, 6 months | M = 0.5 | sqrt(0.5) | **0.707** |
| Unmargined, 1 year | M = 1.0 | sqrt(1.0) | **1.000** |
| Unmargined, 5 years | M = 5.0 | sqrt(min(5, 1)) = sqrt(1) | **1.000** (capped) |
| Unmargined, 1 day | M = 0.003 | sqrt(max(0.003, 0.038)) | **0.196** (floored) |

**Key Insight:** Margined trades have significantly lower maturity factors (typically 0.2-0.4) compared to unmargined trades (0.7-1.0), reflecting the risk-reducing effect of regular collateralization. This creates a strong regulatory incentive for bilateral margining agreements.

### Step 4: aggregate() - Calculate EAD

**File:** [OREAnalytics/orea/engine/saccr.cpp:1595-1952](../../OREAnalytics/orea/engine/saccr.cpp#L1595-1952)

The aggregate() method performs a hierarchical calculation from trade level → hedging set → asset class → netting set. This multi-phase approach follows the SA-CCR regulatory methodology:

1. **Phase 1**: Aggregate NPV by netting set and initialize data structures
2. **Phase 2**: Determine collateral amounts (IM, VM, IAH, TH, MTA) for each netting set
3. **Phase 3**: Calculate Replacement Cost (RC) per netting set
4. **Phase 4**: Calculate add-ons at the hedging set level using asset-class specific formulas
5. **Phase 5**: Aggregate hedging set add-ons to asset class level
6. **Phase 6**: Calculate final EAD, applying multiplier and alpha factor

#### Phase 1: Initialize and Aggregate NPV (lines 1598-1628)

**Purpose:** Initialize all aggregation maps and sum NPV across all trades, grouping by netting set. This establishes the base exposure before applying collateral and potential future exposure calculations.

```cpp
// Initialize aggregation maps
for (const NettingSetDetails& nettingSetDetails : nettingSets_) {
    NPV_[nettingSetDetails] = 0.0;
    RC_[nettingSetDetails] = 0.0;
    addOn_[nettingSetDetails] = 0.0;
    PFE_[nettingSetDetails] = 0.0;
    multiplier_[nettingSetDetails] = 0.0;
}

// Aggregate NPV and initialize addOn maps
for (Size i = 0; i < tradeData_.size(); i++) {
    const TradeData& td = tradeData_.at(i);
    const NettingSetDetails& nettingSetDetails = td.nettingSetDetails;

    NPV_[nettingSetDetails] += td.NPV;
    totalNPV_ += td.NPV;

    // Initialize maps by asset class and hedging set
    AssetClassKey key(nettingSetDetails, assetClass);
    if (addOnAssetClass_.find(key) == addOnAssetClass_.end())
        addOnAssetClass_[key] = 0.0;

    HedgingSetKey key2(nettingSetDetails, assetClass, hedgingSet);
    if (addOnHedgingSet_.find(key2) == addOnHedgingSet_.end())
        addOnHedgingSet_[key2] = 0.0;
}
```

#### Phase 2: Build Collateral Balances (lines 1630-1727)

**Purpose:** Determine the collateral amounts for each netting set. This phase resolves whether to use SIMM-calculated margins, user-provided overrides, or NPV-based calculations. The collateral values (C = VM + IM + IAH) are critical for calculating both Replacement Cost and the multiplier that scales Potential Future Exposure.

**Collateral Components (C = VM + IM + IAH):**

The total collateral **C** consists of three components:
1. **VM (Variation Margin)**: Collateral that covers current mark-to-market exposure
2. **IM (Initial Margin)**: Collateral that covers potential future exposure during MPOR
3. **IAH (Independent Amount Held)**: Additional collateral specified in CSA, independent of exposure

**Derivation Logic:**

```cpp
for (const NettingSetDetails& nettingSetDetails : nettingSets_) {
    const auto& nsd = nettingSetManager_->get(nettingSetDetails);

    if (nsd->activeCsaFlag()) {
        // Get user-provided and calculated collateral balances
        QuantLib::ext::shared_ptr<CollateralBalance> cb = collateralBalances_->get(nettingSetDetails);
        Real cbFxQuote = getFxRate(cb->currency());

        QuantLib::ext::shared_ptr<CollateralBalance> ccb = calculatedCollateralBalances_->get(nettingSetDetails);

        // ===== INITIAL MARGIN (IM) DERIVATION =====
        if (nsd->csaDetails()->calculateIMAmount()) {
            // Option A: Calculate IM from SIMM (Standard Initial Margin Model)
            // This is the typical case for bilateral margin requirements under UMR
            // SIMM calculation happens in a separate analytic (SIMM or XVA analytics)
            // and results are stored in calculatedCollateralBalances_

            if (cb && cb->initialMargin() != Null<Real>() && !isDefaultIM) {
                // Use user-provided override if explicitly specified
                initialMargin = cbFxQuote * cb->initialMargin();
            } else {
                // Use SIMM-calculated IM from calculatedCollateralBalances_
                // If no SIMM calculation available, defaults to 0
                initialMargin = ccb ? ccbFxQuote * ccb->initialMargin() : 0.0;
            }
        } else {
            // Option B: User must provide IM explicitly in collateralbalances.xml
            // Used when:
            // - IM is determined externally (e.g., grid-based IM from CCP)
            // - Historical/legacy margin agreements
            // - Simplified calculations without SIMM
            QL_REQUIRE(cb && cb->initialMargin() != Null<Real>(),
                       "calculateIMAmount=false requires explicit IM in collateral balances");
            initialMargin = cbFxQuote * cb->initialMargin();
        }
        amountsBase_[nettingSetDetails].im = initialMargin;

        // ===== VARIATION MARGIN (VM) DERIVATION =====
        if (nsd->csaDetails()->calculateVMAmount()) {
            // Option A: Calculate VM from current portfolio NPV
            // This is the standard case - VM tracks mark-to-market exposure
            // VM = Net NPV of the netting set (can be positive or negative)

            if (cb && cb->variationMargin() != Null<Real>() && !isDefaultVM) {
                // Use user-provided override if explicitly specified
                // (e.g., to simulate specific collateral scenarios)
                variationMargin = cbFxQuote * cb->variationMargin();
            } else {
                // Use portfolio NPV as VM
                // This represents perfect daily marking-to-market
                variationMargin = NPV_[nettingSetDetails];
            }
        } else {
            // Option B: User must provide VM explicitly in collateralbalances.xml
            // Used for:
            // - Testing specific collateral scenarios
            // - Historical data analysis with known VM positions
            // - Simplified calculations
            QL_REQUIRE(cb && cb->variationMargin() != Null<Real>(),
                       "calculateVMAmount=false requires explicit VM in collateral balances");
            variationMargin = cbFxQuote * cb->variationMargin();
        }
        amountsBase_[nettingSetDetails].vm = variationMargin;

        // ===== INDEPENDENT AMOUNT HELD (IAH) DERIVATION =====
        // IAH is always taken from CSA details - it's a contractual amount
        // specified in the Credit Support Annex (CSA)
        // IAH is additional collateral posted independent of current exposure
        // Common uses:
        // - One-way initial margin (only one party posts)
        // - Fixed collateral requirements for specific counterparty types
        // - Haircuts on collateral value
        Real csaFxQuote = getFxRate(nsd->csaDetails()->csaCurrency());
        amountsBase_[nettingSetDetails].iah = csaFxQuote * nsd->csaDetails()->independentAmountHeld();

        // ===== THRESHOLD (TH) DERIVATION =====
        // Threshold: Exposure level below which no collateral is required
        // Taken from CSA details (contractual term)
        // Higher threshold = less collateral posted but higher uncollateralized exposure
        amountsBase_[nettingSetDetails].tha = csaFxQuote * nsd->csaDetails()->thresholdRcv();

        // ===== MINIMUM TRANSFER AMOUNT (MTA) DERIVATION =====
        // MTA: Minimum change in exposure required before collateral transfer occurs
        // Taken from CSA details (contractual term)
        // Reduces operational burden but creates small gaps in collateralization
        amountsBase_[nettingSetDetails].mta = csaFxQuote * nsd->csaDetails()->mtaRcv();
    } else {
        // Uncollateralized netting set (no CSA or activeCsaFlag = false)
        // All collateral amounts = 0
        // This results in:
        // - RC = max(V, 0) (no collateral offset)
        // - multiplier ≈ 1.0 (no collateral benefit)
        // - Higher capital requirements
        amountsBase_[nettingSetDetails].im = 0.0;
        amountsBase_[nettingSetDetails].vm = 0.0;
        amountsBase_[nettingSetDetails].iah = 0.0;
        amountsBase_[nettingSetDetails].mta = 0.0;
        amountsBase_[nettingSetDetails].tha = 0.0;
    }
}
```

**Summary of Collateral Derivation:**

| Component | Source | Calculation Method | Typical Value |
|-----------|--------|-------------------|---------------|
| **IM** | SIMM calculation OR user-provided | SIMM analytic (complex risk-based model) OR explicit in collateralbalances.xml | Hundreds to thousands (depends on portfolio size/risk) |
| **VM** | Portfolio NPV OR user-provided | Net mark-to-market of all trades in netting set OR explicit value | Equals NPV (can be + or -) |
| **IAH** | CSA contractual terms | Fixed amount from CSA details | 0 to hundreds (contract-specific) |
| **TH** | CSA contractual terms | Fixed threshold from CSA | 0 (fully collateralized) to millions (corporate counterparties) |
| **MTA** | CSA contractual terms | Minimum transfer threshold from CSA | 0 (no minimum) to tens of thousands |

**Key Calculation:**

```
Total Collateral: C = VM + IM + IAH

Net Independent Collateral Amount: NICA = IM + IAH

Used in RC formula: RC = max(V - C, TH + MTA - NICA, 0)
```

**Configuration Flow:**

```
netting.xml (CSA details)
    ↓
    ├─→ MPOR, ThresholdRcv, MTARcv, IndependentAmountHeld
    ├─→ calculateIMAmount flag (true/false)
    └─→ calculateVMAmount flag (true/false)

collateralbalances.xml (optional overrides)
    ↓
    ├─→ initialMargin (override if provided)
    └─→ variationMargin (override if provided)

SIMM Analytic (if calculateIMAmount = true)
    ↓
    └─→ calculatedCollateralBalances_.im (SIMM result)

Portfolio NPV (if calculateVMAmount = true)
    ↓
    └─→ NPV_[nettingSetDetails] used as VM
```

#### Phase 3: Calculate RC (Replacement Cost) (lines 1752-1775)

**Purpose:** Calculate Replacement Cost for each netting set. RC represents the current exposure if the counterparty were to default today, considering netting benefits and collateral. The formula accounts for thresholds and minimum transfer amounts that may prevent full collateralization.

```cpp
for (map<NettingSetDetails, Real>::iterator it = NPV_.begin(); it != NPV_.end(); it++) {
    const NettingSetDetails nettingSetDetails = it->first;

    const Real independentAmountHeld = amountsBase_[nettingSetDetails].iah;
    const Real initialMargin = amountsBase_[nettingSetDetails].im;
    const Real variationMargin = amountsBase_[nettingSetDetails].vm;
    const Real mta = amountsBase_[nettingSetDetails].mta;
    const Real th = amountsBase_[nettingSetDetails].tha;

    const Real nica = independentAmountHeld + initialMargin;
    const Real C = variationMargin + nica;

    // RC Formula: max(V - C, TH + MTA - NICA, 0)
    RC_[nettingSetDetails] = std::max(NPV_[nettingSetDetails] - C,
                                      std::max(th + mta - nica, 0.0));
}
```

#### Phase 4: Calculate Hedging Set Add-Ons (lines 1777-1864)

**Purpose:** Calculate Potential Future Exposure (PFE) add-ons at the hedging set level. Each asset class has a specific aggregation formula that reflects the correlation structure of risk factors within that asset class:
- **IR**: Uses maturity bucketing with prescribed correlations between buckets
- **FX**: Simple absolute sum (perfect hedging within currency pair)
- **Commodity/Equity**: Correlation-based aggregation across subsets (different commodities/equities have imperfect correlation)

The add-ons are scaled by supervisory factors that represent standardized volatilities for each asset class.

```cpp
for (map<HedgingSetKey, Real>::iterator it = addOnHedgingSet_.begin();
     it != addOnHedgingSet_.end(); it++) {

    Real D1 = 0, D2 = 0, D3 = 0;  // For IR maturity buckets

    // Aggregate effective notionals across trades in hedging set
    for (Size i = 0; i < tradeData_.size(); i++) {
        const TradeData& td = tradeData_.at(i);
        HedgingSetKey key(td.nettingSetDetails, td.assetClass, td.hedgingSet);
        if (it->first != key) continue;

        // Interest Rate: aggregate into maturity buckets
        if (assetClass == AssetClass::IR) {
            if (td.M < 1.0)
                D1 += td.delta * td.d * td.MF;
            else if (td.M <= 5.0)
                D2 += td.delta * td.d * td.MF;
            else
                D3 += td.delta * td.d * td.MF;
        }
        // FX: simple sum
        else if (assetClass == AssetClass::FX) {
            effectiveNotional_[key] += td.delta * td.d * td.MF;
        }
        // Commodity/Equity: aggregate by hedging subset
        else if (assetClass == AssetClass::Commodity || assetClass == AssetClass::Equity) {
            HedgingSubsetKey subsetKey(nettingSetDetails, assetClass, hedgingSet, td.hedgingSubset);
            subsetEffectiveNotional_[subsetKey] += td.delta * td.d * td.MF;
        }
    }

    // Calculate add-ons with asset-class specific formulas
    if (assetClass == AssetClass::IR) {
        // Effective notional with maturity correlation
        effectiveNotional_[it->first] =
            std::sqrt(D1*D1 + D2*D2 + D3*D3 + 1.4*(D1*D2 + D2*D3) + 0.6*D1*D3);

        Real supervisoryFactor = 0.005;  // 0.5% for IR
        addOnHedgingSet_[it->first] = supervisoryFactor * effectiveNotional_[it->first];
    }
    else if (assetClass == AssetClass::FX) {
        Real supervisoryFactor = 0.04;  // 4% for FX
        addOnHedgingSet_[it->first] = supervisoryFactor * fabs(effectiveNotional_[it->first]);
    }
    else if (assetClass == AssetClass::Commodity) {
        // Aggregate across subsets with correlation
        Real addonType = 0;
        Real addonTypeSquared = 0;
        for (auto& s : commoditySubsetKeys) {
            const string& hedgingSubset = QuantLib::ext::get<3>(s);
            const Real supervisoryFactor = hedgingSubset == "Power" ? 0.4 : 0.18;
            const Real tmp = supervisoryFactor * subsetEffectiveNotional_.at(s);
            addonType += tmp;
            addonTypeSquared += tmp * tmp;
        }
        const Real corr = 0.4;
        addOnHedgingSet_[it->first] =
            std::sqrt((corr * addonType)*(corr * addonType) + (1 - corr*corr) * addonTypeSquared);
    }
    else if (assetClass == AssetClass::Equity) {
        // Similar to commodity but with different factors
        Real addonType = 0;
        Real addonTypeSquared = 0;
        for (auto& [subsetKey, isEquityIndex] : equitySubsetKeys) {
            const Real supervisoryFactor = isEquityIndex ? 0.2 : 0.32;
            const Real corr = isEquityIndex ? 0.8 : 0.5;
            const Real tmp = supervisoryFactor * subsetEffectiveNotional_.at(subsetKey);
            addonType += corr * tmp;
            addonTypeSquared += (1 - corr*corr) * tmp * tmp;
        }
        addOnHedgingSet_[it->first] = std::sqrt(addonType*addonType + addonTypeSquared);
    }

    // Basis trades: multiply supervisory factor by 0.5
    if (basisHedgingSets_.find(hedgingSet) != basisHedgingSets_.end())
        addOnHedgingSet_[it->first] *= 0.5;
}
```

#### Phase 5: Aggregate to Asset Class (lines 1866-1879)

**Purpose:** Aggregate hedging set add-ons to the asset class level. This is a simple summation - no correlation adjustments are applied between hedging sets within the same asset class (conservative assumption).

```cpp
// Pure aggregation: sum hedging set add-ons within same asset class
for (auto it = addOnAssetClass_.begin(); it != addOnAssetClass_.end(); it++) {
    for (auto ith = addOnHedgingSet_.begin(); ith != addOnHedgingSet_.end(); ith++) {
        NettingSetDetails nettingSetDetails = QuantLib::ext::get<0>(ith->first);
        AssetClass assetClass = QuantLib::ext::get<1>(ith->first);

        AssetClassKey key(nettingSetDetails, assetClass);
        if (it->first != key) continue;

        it->second += ith->second;
    }
}
```

#### Phase 6: Calculate EAD per Netting Set (lines 1881-1924)

**Purpose:** Calculate the final Exposure at Default (EAD) for each netting set. This phase:
1. Sums add-ons across all asset classes for the netting set
2. Calculates the **multiplier** that reduces PFE when net collateral is high (recognizing reduced exposure when well-collateralized)
3. Applies the **alpha factor (1.4)** as a regulatory scalar to convert expected exposure to exposure at default
4. Retrieves the **risk weight** from counterparty information
5. Calculates the **capital charge** = EAD × RW

The multiplier formula creates a smooth transition: when collateral fully covers NPV (V ≈ C), the multiplier approaches its floor of 5%, reducing the add-on contribution. When uncollateralized (C = 0), the multiplier approaches 1, using the full add-on.

```cpp
for (auto it = addOn_.begin(); it != addOn_.end(); it++) {
    NettingSetDetails nettingSetDetails = it->first;

    // Sum add-ons across asset classes
    for (auto ita = addOnAssetClass_.begin(); ita != addOnAssetClass_.end(); ita++) {
        if (nettingSetDetails != ita->first.first) continue;
        it->second += ita->second;
    }

    const Real independentAmountHeld = amountsBase_[nettingSetDetails].iah;
    const Real initialMargin = amountsBase_[nettingSetDetails].im;
    const Real variationMargin = amountsBase_[nettingSetDetails].vm;

    const Real nica = independentAmountHeld + initialMargin;
    const Real C = variationMargin + nica;

    const Real V = NPV_[nettingSetDetails];
    const Real A = addOn_[nettingSetDetails];

    // Multiplier formula
    multiplier_[nettingSetDetails] =
        std::min(1.0, 0.05 + 0.95 * std::exp((V - C) / (2.0 * 0.95 * A)));

    // PFE = multiplier × AddOn
    PFE_[nettingSetDetails] = multiplier_[nettingSetDetails] * addOn_[nettingSetDetails];

    // EAD = alpha × (RC + PFE)
    const Real alpha = 1.4;
    EAD_[nettingSetDetails] = alpha * (RC_[nettingSetDetails] + PFE_[nettingSetDetails]);

    // Get risk weight from counterparty manager
    string cpStr = *nettingSetToCpty_[nettingSetDetails].begin();
    QuantLib::ext::shared_ptr<CounterpartyInformation> cp = counterpartyManager_->get(cpStr);
    RW_[nettingSetDetails] = cp->saCcrRiskWeight();

    // Capital Charge = EAD × RW
    CC_[nettingSetDetails] = EAD_[nettingSetDetails] * RW_[nettingSetDetails];
    totalCC_ += CC_[nettingSetDetails];
}
```

**SA-CCR Formulas Summary:**

```
# Replacement Cost
RC = max(V - C, TH + MTA - NICA, 0)
where:
  V = Net NPV of netting set
  C = VM + IM + IAH  (Total collateral)
  NICA = IM + IAH    (Net Independent Collateral Amount)
  TH = Threshold
  MTA = Minimum Transfer Amount

# Effective Notional (trade level)
d = δ × SD × CurrentNotional × MF
where:
  δ = delta adjustment (from getDelta)
  SD = supervisory duration (IR/Credit only)
  MF = maturity factor

# Hedging Set Add-On
For IR:  AddOn_HS = SF × sqrt(D1² + D2² + D3² + 1.4(D1·D2 + D2·D3) + 0.6·D1·D3)
         where D1, D2, D3 are maturity bucket aggregations
         SF = 0.5% for IR

For FX:  AddOn_HS = SF × |Σ(δ × d × MF)|
         SF = 4% for FX

For Commodity/Equity: Correlation-based aggregation across subsets

# Multiplier
multiplier = min(1, 0.05 + 0.95 × exp((V - C) / (2 × 0.95 × A)))

# PFE (Potential Future Exposure)
PFE = multiplier × AddOn

# EAD (Exposure at Default)
EAD = α × (RC + PFE)
where α = 1.4

# Capital Charge
CC = EAD × RW
where RW = Risk Weight from counterparty information
```

### Step 5: combineCollateralBalances()

**File:** [OREAnalytics/orea/engine/saccr.cpp:1954-2012](../../OREAnalytics/orea/engine/saccr.cpp#L1954-L2012)

```cpp
void SACCR::combineCollateralBalances() {
    // Merge user-provided and calculated collateral balances
    for (const auto& ns : nettingSetManager_->nettingSets()) {
        string nsId = ns.first;

        // Start with user-provided balances
        CollateralBalance combined;
        if (collateralBalances_->has(nsId)) {
            combined = collateralBalances_->get(nsId);
        }

        // Override with calculated balances where available
        if (calculatedCollateralBalances_->has(nsId)) {
            CollateralBalance calculated = calculatedCollateralBalances_->get(nsId);
            if (calculated.hasIM())
                combined.setIM(calculated.getIM());
            if (calculated.hasVM())
                combined.setVM(calculated.getVM());
        }

        // Store final balance
        collateralBalances_->set(nsId, combined);
    }
}
```

---

## 7. Report Generation

After the SACCR constructor completes, reports are automatically populated.

**File:** [OREAnalytics/orea/engine/saccr.cpp:2103-2290](../../OREAnalytics/orea/engine/saccr.cpp#L2103-L2290)

### writeReports() Method (called automatically by constructor)

```cpp
void SACCR::writeReports() {
    // Lines 2106-2166: Write Detail Report
    if (reports_.find(ReportType::Detail) != reports_.end()) {
        auto report = reports_[ReportType::Detail];

        // Header
        report->addColumn("TradeId", string());
        report->addColumn("TradeType", string());
        report->addColumn("NettingSet", string());
        report->addColumn("AssetClass", string());
        report->addColumn("HedgingSet", string());
        report->addColumn("NPV", double(), 6);
        report->addColumn("SupervisoryDuration", double(), 6);
        report->addColumn("Delta", double(), 6);
        report->addColumn("EffectiveNotional", double(), 6);
        report->addColumn("MaturityFactor", double(), 6);
        // ... more columns ...

        // Data rows
        for (const TradeData& td : tradeData_) {
            report->next();
            report->add(td.id);
            report->add(td.type);
            report->add(td.nettingSetDetails);
            report->add(toString(td.assetClass));
            report->add(td.hedgingSet);
            report->add(td.NPV);
            report->add(td.supervisoryDuration);
            report->add(td.delta);
            report->add(td.d);
            report->add(td.maturityFactor);
            // ... more values ...
        }
    }

    // Lines 2168-2290: Write Summary Report
    if (reports_.find(ReportType::Summary) != reports_.end()) {
        auto report = reports_[ReportType::Summary];

        // Header
        report->addColumn("NettingSet", string());
        report->addColumn("AssetClass", string());
        report->addColumn("HedgingSet", string());
        report->addColumn("NPV", double(), 6);
        report->addColumn("RC", double(), 6);
        report->addColumn("AddOn", double(), 6);
        report->addColumn("Multiplier", double(), 6);
        report->addColumn("PFE", double(), 6);
        report->addColumn("EAD", double(), 6);
        report->addColumn("RW", double(), 6);
        report->addColumn("CC", double(), 6);
        report->addColumn("IM", double(), 6);
        report->addColumn("VM", double(), 6);
        // ... more columns ...

        // Data rows - aggregate by netting set
        for (const auto& ns : nettingSetManager_->nettingSets()) {
            string nsId = ns.first;

            report->next();
            report->add(nsId);
            report->add("Total");
            report->add("");
            report->add(npvTotalCurrent_[nsId]);
            report->add(RC_[nsId]);
            report->add(AddOn_[nsId]);
            report->add(multiplier_[nsId]);
            report->add(PFE_[nsId]);
            report->add(EAD_[nsId]);
            report->add(RW_[nsId]);
            report->add(CC_[nsId]);
            // ...
        }
    }
}
```

### Output to Disk

Back in `SaCcrAnalyticImpl::runAnalytic()` (line 112-113):

```cpp
analytic()->addReport(label(), "saccr", saCcrReport);
analytic()->addReport(label(), "saccr_detail", saCcrDetailReport);
```

These reports are then written to disk by `AnalyticsManager` after all analytics complete.

**Output Files:**
- `Output/SA-CCR/saccr.csv` - Summary report with EAD, RC, AddOn per netting set
- `Output/SA-CCR/saccr_detail.csv` - Trade-level detail report
- `Output/SA-CCR/collateralbalances.xml` - Final collateral balances
- `Output/SA-CCR/cashflow.csv` - Cashflow report (if enabled)
- `Output/SA-CCR/additional_results.csv` - Additional results (if enabled)

---

## 8. Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Python Script: run_saccr.py                                  │
│    - Creates OreExample instance                                │
│    - Calls oreex.run("Input/ore_saccr.xml")                     │
│    - Executes: subprocess.call([ore_exe, "Input/ore_saccr.xml"])│
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. C++ Executable: ore.cpp main()                               │
│    Line 80: initBuilders()  // Register factories               │
│    Line 85-86: params->fromFile(inputFile)  // Parse XML        │
│    Line 87: OREApp ore(params, true)                            │
│    Line 88: ore.run()                                           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Parameters::fromFile() & fromXML()                           │
│    parameters.cpp:65-124                                        │
│    - Parse <Setup> → data_["setup"][paramName]                  │
│    - Parse <Markets> → data_["markets"][paramName]              │
│    - Parse <Analytics> → data_[analyticType][paramName]         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 4. OREApp::initFromParams()                                             │
│    oreapp.cpp:344-407                                                   │
│    Line 401: inputs_->loadParameters()                                  │
│    - OREAppInputParameters::loadParameters()                            │
│      oreapp.cpp:630-1450                                                │
│      * Load setup params (asof, paths, baseCurrency)                    │
│      * Load config files (conventions, curves, market)                  │
│      * Load portfolio, netting sets, counterparty data                  │
│      * Parse analytics: insertAnalytic("NPV"), insertAnalytic("SA_CCR") │
└────────────────────────┬────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. OREApp::run() → Create AnalyticsManager                      │
│    - analyticsManager_ = make_shared<AnalyticsManager>(...)     │
│    - analyticsManager_->initialise()                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. AnalyticsManager::initialise()                               │
│    analyticsmanager.cpp:36-40                                   │
│    For each analytic in inputs_->analytics():                   │
│      - AnalyticFactory::instance().build("SA_CCR", ...)         │
│      - Creates SaCcrAnalytic instance                           │
│      - Constructor creates SaCcrAnalyticImpl                    │
│      - Auto-registers with AnalyticsManager                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. AnalyticsManager::runAnalytics()                             │
│    analyticsmanager.cpp:94-186                                  │
│    - Load market data for all analytics                         │
│    - For each analytic:                                         │  
│        analytic->runAnalytic(loader, analytics)                 │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. SaCcrAnalyticImpl::runAnalytic()                             │
│    saccranalytic.cpp:41-114                                     │
│    Line 53-54: buildMarket(loader), buildPortfolio()            │
│    Line 56: enrichIndexFixings()                                │
│    Line 61-79: Write intermediate reports (cashflow, additional)│
│    Line 82-92: Get configuration managers                       │
│    Line 94-98: Create in-memory report objects                  │
│    Line 101-104: Create SACCR engine ← CALCULATION HAPPENS      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. SACCR Constructor - Main Calculation                         │
│    saccr.cpp:434-454                                            │
│                                                                 │
│    Line 444: clear()  [saccr.cpp:418-432]                       │ 
│      - Initialize RC_, AddOn_, EAD_, RW_, CC_ maps              │
│                                                                 │
│    Line 445: validate()  [saccr.cpp:1068-1380]                  │
│      - Check configuration files exist                          │
│      - Create default netting sets if missing                   │
│      - Validate collateral balance configs                      │
│                                                                 │
│    Line 446: tradeDetails()  [saccr.cpp:1392-1593]              │
│      - For each trade in portfolio:                             │
│        * Extract NPV, asset class, maturity                     │
│        * Calculate current notional [905-1068]                  │
│        * Calculate supervisory duration [594-627]               │
│        * Calculate delta adjustment [638-903]                   │
│        * Calculate effective notional: d = δ × SD × notional    │
│        * Assign hedging set/subset                              │
│                                                                 │
│    Line 447: aggregate()  [saccr.cpp:1595-1952]                 │
│      - Aggregate NPV by netting set                             │
│      - Calculate add-ons by hedging set                         │
│      - Aggregate add-ons by asset class                         │
│      - For each netting set:                                    │
│        * RC = max(V - C, 0)                                     │
│        * Calculate multiplier                                   │
│        * PFE = multiplier × AddOn                               │
│        * EAD = (RC + PFE) - C                                   │
│        * RW = risk weight from counterparty                     │
│        * CC = EAD × RW × 8%                                     │
│                                                                 │
│    Line 448: combineCollateralBalances()  [1954-2012]           │
│      - Merge user-provided and SIMM-calculated collateral       │
│                                                                 │
│    writeReports()  [2103-2290]                                  │ 
│      - Populate Detail report (trade-level)                     │
│      - Populate Summary report (netting set level)              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. Back to SaCcrAnalyticImpl::runAnalytic()                    │
│     Line 105: setSaccr(saccr)  // Store SACCR object            │
│     Line 108-110: Save collateralbalances.xml                   │
│     Line 112-113: Register reports with analytic                │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│ 11. AnalyticsManager writes all reports to disk                 │
│     - saccr.csv (summary)                                       │
│     - saccr_detail.csv (trade details)                          │
│     - collateralbalances.xml                                    │
│     - cashflow.csv (if enabled)                                 │
│     - additional_results.csv (if enabled)                       │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Key Data Structures

### Portfolio Structure (portfolio.xml)

```xml
<Portfolio>
  <Trade id="Swap_EUR">
    <TradeType>Swap</TradeType>
    <Envelope>
      <CounterParty>CPTY_A</CounterParty>
      <NettingSetId>CPTY_A</NettingSetId>
    </Envelope>
    <SwapData>
      <!-- Swap details -->
    </SwapData>
  </Trade>
</Portfolio>
```

### Netting Set Definition (netting.xml)

```xml
<NettingSetDefinitions>
  <NettingSet>
    <NettingSetId>CPTY_A</NettingSetId>
    <ActiveCSAFlag>false</ActiveCSAFlag>
    <CSADetails>
      <Bilateral>Bilateral</Bilateral>
      <CSACurrency>EUR</CSACurrency>
      <ThresholdPay>100000</ThresholdPay>
      <ThresholdReceive>100000</ThresholdReceive>
      <MinimumTransferAmountPay>0</MinimumTransferAmountPay>
      <MinimumTransferAmountReceive>0</MinimumTransferAmountReceive>
      <IndependentAmountHeld>0</IndependentAmountHeld>
      <MarginPeriodOfRisk>0W</MarginPeriodOfRisk>
    </CSADetails>
  </NettingSet>
</NettingSetDefinitions>
```

### SACCR::TradeData Structure

**File:** [OREAnalytics/orea/engine/saccr.hpp:116-165](../../OREAnalytics/orea/engine/saccr.hpp#L116-L165)

```cpp
struct TradeData {
    // Identifiers
    std::string id;
    std::string type;
    std::string cpty;
    std::string nettingSetDetails;

    // Classification
    AssetClass assetClass;
    std::string hedgingSet;
    std::string hedgingSubset;

    // Values
    Real NPV;
    Real currentNotional;
    Real delta;
    Real d;  // Effective notional = delta × SD × currentNotional
    Real supervisoryDuration;
    Real maturityFactor;

    // Maturity parameters
    Real M;  // Time to maturity
    Real S;  // Start date (first exercise)
    Real E;  // End date (underlying maturity)
    Real T;  // Latest exercise date

    // Option parameters
    Real price;
    Real strike;
    Size numNominalFlows;

    // Equity-specific
    Real currentPrice1;
    Real currentPrice2;
    bool isEquityIndex;
};
```

### SACCR Calculation Results

Stored in maps keyed by netting set ID:

```cpp
std::map<std::string, Real> RC_;      // Replacement Cost
std::map<std::string, Real> AddOn_;   // Add-on (aggregated PFE)
std::map<std::string, Real> EAD_;     // Exposure at Default
std::map<std::string, Real> RW_;      // Risk Weight
std::map<std::string, Real> CC_;      // Capital Charge
```

---

## 10. Key File Reference Table

| Component | File | Key Lines |
|-----------|------|-----------|
| Python entry point | [Examples/CreditRisk/run_saccr.py](../../Examples/CreditRisk/run_saccr.py) | 18 |
| Python helper | [Examples/ore_examples_helper.py](../../Examples/ore_examples_helper.py) | 332-342 |
| C++ main | [App/ore.cpp](../../App/ore.cpp) | 61-94 |
| Parameters parsing | [OREAnalytics/orea/app/parameters.cpp](../../OREAnalytics/orea/app/parameters.cpp) | 65-124 |
| InputParameters loading | [OREAnalytics/orea/app/oreapp.cpp](../../OREAnalytics/orea/app/oreapp.cpp) | 630-1450 |
| AnalyticsManager init | [OREAnalytics/orea/app/analyticsmanager.cpp](../../OREAnalytics/orea/app/analyticsmanager.cpp) | 36-40 |
| AnalyticsManager run | [OREAnalytics/orea/app/analyticsmanager.cpp](../../OREAnalytics/orea/app/analyticsmanager.cpp) | 94-186 |
| SaCcrAnalytic header | [OREAnalytics/orea/app/analytics/saccranalytic.hpp](../../OREAnalytics/orea/app/analytics/saccranalytic.hpp) | 30-52 |
| SaCcrAnalytic impl | [OREAnalytics/orea/app/analytics/saccranalytic.cpp](../../OREAnalytics/orea/app/analytics/saccranalytic.cpp) | 41-114 |
| SACCR header | [OREAnalytics/orea/engine/saccr.hpp](../../OREAnalytics/orea/engine/saccr.hpp) | 116-224 |
| SACCR constructor | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 434-454 |
| SACCR::clear() | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 418-432 |
| SACCR::validate() | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 1068-1380 |
| SACCR::tradeDetails() | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 1392-1593 |
| SACCR::aggregate() | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 1595-1952 |
| SACCR::getCurrentNotional() | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 905-1068 |
| SACCR::getDelta() | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 638-903 |
| SACCR::getSupervisoryDuration() | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 594-627 |
| SACCR::writeReports() | [OREAnalytics/orea/engine/saccr.cpp](../../OREAnalytics/orea/engine/saccr.cpp) | 2103-2290 |

---

## Summary

The SA-CCR execution flow demonstrates ORE's layered architecture:

1. **Python Layer**: Simple wrapper for test automation and scripting
2. **Application Layer**: Command-line executable that orchestrates the workflow
3. **Configuration Layer**: XML parsing into strongly-typed C++ objects
4. **Analytics Layer**: Factory-based analytics that can be composed and extended
5. **Engine Layer**: Core financial calculations (SACCR implementation)
6. **Reporting Layer**: In-memory and on-disk report generation

The SACCR calculation itself happens entirely in the SACCR constructor, following the regulatory formula:

```
EAD = (RC + PFE) - Collateral
where:
  RC = Replacement Cost = max(NPV - Collateral, 0)
  PFE = Potential Future Exposure = multiplier × AddOn
  AddOn = Aggregated add-ons across asset classes and hedging sets
```

Each trade contributes to the add-on via its effective notional:
```
d = δ × SD × CurrentNotional
```

where:
- δ (delta) captures directionality and non-linearity
- SD (supervisory duration) captures time-to-maturity effects
- CurrentNotional represents the trade's current exposure size

The results are aggregated hierarchically: trade → hedging set → asset class → netting set, ultimately producing the Exposure at Default (EAD) for capital charge calculation.
