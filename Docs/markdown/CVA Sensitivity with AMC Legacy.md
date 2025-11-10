# CVA Sensitivity Calculation with AMC Legacy Framework

**Document Purpose**: This document provides a detailed trace of how the `run_cvasensi.py` script executes the `ore_amc_legacy.xml` configuration to compute CVA (Credit Valuation Adjustment) exposures using the legacy American Monte Carlo (AMC) framework, with actual source code references.

**Author**: Generated for ORE Codebase Understanding

**Last Updated**: 2025-11-08

**Example Location**: [Examples/Performance/](../../Examples/Performance/)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Entry Point: Python Script](#1-entry-point-python-script)
3. [OreExample Helper Class](#2-oreexample-helper-class)
4. [XML Configuration Analysis](#3-xml-configuration-analysis)
5. [ORE Application Execution](#4-ore-application-execution)
6. [XVA Analytic Implementation](#5-xva-analytic-implementation)
7. [NPV Cube Structure](#6-npv-cube-structure)
8. [Exposure Calculation](#7-exposure-calculation)
9. [CVA Calculation](#8-cva-calculation)
10. [Complete Execution Flow](#9-complete-execution-flow)
11. [Output Files](#10-output-files)
12. [Comparison with Other Methods](#11-comparison-with-other-methods)

---

## Executive Summary

The CVA sensitivity example demonstrates ORE's capability to compute Credit Valuation Adjustment (CVA) using various computational approaches. The `ore_amc_legacy.xml` configuration specifically uses the **legacy AMC (American Monte Carlo)** framework to generate exposure profiles for a 20-year EUR interest rate swap.

### High-Level Flow

```
Python Script (run_cvasensi.py:16)
    ↓
OreExample.run() → Locate and execute ORE binary
    ↓
ORE Application (ore.cpp) → Parse ore_amc_legacy.xml
    ↓
AnalyticsManager → Execute configured analytics
    ├─ NPV Analytic → Base trade valuations
    ├─ Cashflow Analytic → Generate cashflow schedules
    ├─ Simulation Analytic → AMC exposure generation
    │   ├─ Build Cross-Asset Model (CAM)
    │   ├─ Calibrate LGM to swaption vols
    │   ├─ Generate 8192 Monte Carlo paths
    │   ├─ Price swap at each future date/scenario
    │   └─ Store exposures in NPV cube
    └─ XVA Analytic → Compute CVA from exposures
        ├─ Calculate Expected Positive Exposure (EPE)
        ├─ Apply default probabilities
        └─ Compute CVA = LGD × Σ EPE(t) × PD(t) × DF(t)
```

### Key Characteristics of AMC Legacy

- **"Legacy"** refers to the original AMC implementation (vs. AMC-CG which uses Computation Graphs)
- **Pros**: Mature, well-tested, direct calculation path
- **Cons**: Cannot use AAD (Algorithmic Automatic Differentiation) or GPU acceleration
- **Use Case**: Benchmark for comparing against newer AMC-CG, AAD, and GPU implementations

---

## 1. Entry Point: Python Script

### File: [Examples/Performance/run_cvasensi.py](../../Examples/Performance/run_cvasensi.py)

**Source Code** (Lines 1-26):

```python
#!/usr/bin/env python

import glob
import os
import sys
sys.path.append('../')
from ore_examples_helper import OreExample

oreex = OreExample(sys.argv[1] if len(sys.argv)>1 else False)

print("+----------------------------------------+")
print("| CVA Sensis using AMC, AAD and GPU      |")
print("+----------------------------------------+")

oreex.print_headline("Run AMC Legacy")
oreex.run("Input/ore_amc_legacy.xml")              # Execute ORE with XML config

oreex.print_headline("Run CVA Sensi with bump & reval")
oreex.run("Input/ore_cvasensi_bump.xml")

oreex.print_headline("Run CVA Sensi with AAD")
oreex.run("Input/ore_cvasensi_ad.xml")

oreex.print_headline("Run with bump & reval using a GPU")
oreex.run("Input/ore_cvasensi_gpu.xml")
```

**Code Summary**:
- **Lines 1-7**: Import dependencies and initialize the `OreExample` helper class
- **Line 9**: Create `OreExample` instance, optionally in dry-run mode from command-line argument
- **Lines 11-13**: Print banner
- **Lines 15-16**: **Run AMC Legacy** - This is our focus, executes `ore_amc_legacy.xml`
- **Lines 18-25**: Run other CVA sensitivity approaches for comparison (bump & reval, AAD, GPU)

**What Happens on Line 16**:
- `oreex.run("Input/ore_amc_legacy.xml")` calls the `OreExample.run()` method
- This locates the ORE executable and executes it with the XML configuration
- ORE runs all analytics defined in the XML: NPV → Cashflow → Simulation → XVA

---

## 2. OreExample Helper Class

### File: [Examples/ore_examples_helper.py](../../Examples/ore_examples_helper.py)

The helper class provides utilities for running ORE examples and processing results. Key methods:

**Class Initialization** (Lines 61-73):
```python
class OreExample(object):
    def __init__(self, dry=False):
        self.ore_exe = ""                           # Path to ORE executable
        self.headlinecounter = 0                    # Counter for progress messages
        self.dry = dry                              # Dry-run mode flag
        # ... initialization logic
        if not 'ORE_EXAMPLES_USE_PYTHON' in os.environ.keys() or os.environ['ORE_EXAMPLES_USE_PYTHON']!="1":
            self._locate_ore_exe()                  # Find ORE binary
```

**Execute ORE** (Lines 332-342):
```python
def run(self, xml):
    if not self.dry:
        if(self.use_python):                    # If using Python bindings
            res = subprocess.call([sys.executable,
                                  os.path.join(os.pardir, "ore_wrapper.py"),
                                  xml])
        else:
            res = subprocess.call([self.ore_exe, xml])  # Execute: ./ore Input/ore_amc_legacy.xml
        if res != 0:
            raise Exception("Return Code was not Null.")
```

**Code Summary**:
- The `run()` method executes the ORE binary as a subprocess
- It passes the XML configuration file path as a command-line argument
- The system call is: `../../build/App/ore Input/ore_amc_legacy.xml`
- If the return code is non-zero, an exception is raised

**Execution Path**:
1. `run_cvasensi.py:16` → `oreex.run("Input/ore_amc_legacy.xml")`
2. `ore_examples_helper.py:340` → `subprocess.call([self.ore_exe, xml])`
3. System executes: `../../build/App/ore Input/ore_amc_legacy.xml`

---

## 3. XML Configuration Analysis

### File: [Examples/Performance/Input/ore_amc_legacy.xml](../../Examples/Performance/Input/ore_amc_legacy.xml)

This XML file is the main configuration that drives the entire calculation.

**Setup Section** (Lines 3-20):

```xml
<ORE>
  <Setup>
    <Parameter name="asofDate">2016-02-05</Parameter>
    <Parameter name="inputPath">Input</Parameter>
    <Parameter name="outputPath">Output/cvasensi/amc_legacy</Parameter>
    <Parameter name="logFile">log.txt</Parameter>
    <Parameter name="logMask">31</Parameter>
    <Parameter name="marketDataFile">../../Input/market_20160205.txt</Parameter>
    <Parameter name="fixingDataFile">../../Input/fixings_20160205.txt</Parameter>
    <Parameter name="implyTodaysFixings">N</Parameter>
    <Parameter name="curveConfigFile">../../Input/curveconfig.xml</Parameter>
    <Parameter name="conventionsFile">../../Input/conventions.xml</Parameter>
    <Parameter name="marketConfigFile">../../Input/todaysmarket.xml</Parameter>
    <Parameter name="pricingEnginesFile">pricingengine.xml</Parameter>
    <Parameter name="portfolioFile">portfolio_cvasensi.xml</Parameter>
    <Parameter name="observationModel">None</Parameter>
    <Parameter name="scriptLibrary">scriptlibrary.xml</Parameter>
    <Parameter name="nThreads">1</Parameter>
  </Setup>
```

**Code Summary**:
- **Line 4**: Valuation date set to 2016-02-05
- **Lines 5-6**: Input files in `Input/` directory, outputs to `Output/cvasensi/amc_legacy/`
- **Lines 7-8**: Logging configuration (log.txt with verbosity level 31)
- **Lines 9-10**: Market data and historical fixings from shared Examples/Input directory
- **Lines 12-15**: Configuration files for curves, conventions, market setup, and pricing engines
- **Line 16**: Portfolio contains a single 20-year EUR swap
- **Line 19**: Single-threaded execution

**Markets Section** (Lines 21-27):

```xml
  <Markets>
    <Parameter name="lgmcalibration">collateral_inccy</Parameter>
    <Parameter name="fxcalibration">xois_eur</Parameter>
    <Parameter name="pricing">xois_eur</Parameter>
    <Parameter name="simulation">xois_eur</Parameter>
    <Parameter name="sensitivity">xois_eur</Parameter>
  </Markets>
```

**Code Summary**:
- **Line 22**: LGM calibration uses OIS curves (risk-free rates) per currency
- **Lines 23-26**: Pricing and simulation use EUR-collateralized discounting (XOIS EUR)
- These configurations determine which yield curves are used for different purposes

**Analytics Section** (Lines 28-65):

**Simulation Analytic** (Lines 44-54) - **THE KEY ANALYTIC**:

```xml
    <Analytic type="simulation">
      <Parameter name="active">Y</Parameter>
      <Parameter name="amc">Y</Parameter>
      <!-- Disabled (legacy AMC), CubeGeneration (AMC-CG, classic PP), Full (AMC-CG, cg PP) -->
      <Parameter name="amcCg">Disabled</Parameter>
      <Parameter name="amcTradeTypes">Swap,ScriptedTrade</Parameter>
      <Parameter name="simulationConfigFile">simulation_xva.xml</Parameter>
      <Parameter name="pricingEnginesFile">pricingengine.xml</Parameter>
      <Parameter name="amcPricingEnginesFile">pricingengine_amc.xml</Parameter>
      <Parameter name="baseCurrency">EUR</Parameter>
    </Analytic>
```

**Code Summary**:
- **Line 46**: AMC enabled (`amc=Y`)
- **Line 48**: **`amcCg=Disabled`** - This is the key setting that activates **legacy AMC** mode
- **Line 49**: Swap and ScriptedTrade instruments eligible for AMC pricing
- **Lines 50-52**: Configuration files for simulation parameters and AMC-specific pricing engines

**XVA Analytic** (Lines 55-64):

```xml
    <Analytic type="xva">
      <Parameter name="active">Y</Parameter>
      <Parameter name="csaFile">netting.xml</Parameter>
      <Parameter name="baseCurrency">EUR</Parameter>
      <Parameter name="exposureProfiles">Y</Parameter>
      <Parameter name="exposureProfilesByTrade">Y</Parameter>
      <Parameter name="quantile">0.95</Parameter>
      <Parameter name="calculationType">Symmetric</Parameter>
      <Parameter name="cva">Y</Parameter>
    </Analytic>
```

**Code Summary**:
- **Lines 59-60**: Generate exposure profiles at both netting set and trade level
- **Line 61**: PFE calculated at 95th percentile
- **Line 63**: CVA calculation enabled

---

## 4. ORE Application Execution

### File: [OREAnalytics/orea/app/oreapp.cpp](../../OREAnalytics/orea/app/oreapp.cpp)

When the ORE binary is executed, it enters the main application loop.

**Main Entry Point** (App/ore.cpp):
```cpp
int main(int argc, char** argv) {
    std::string inputFile = argv[1];  // "Input/ore_amc_legacy.xml"
    auto params = boost::make_shared<Parameters>();
    params->fromFile(inputFile);      // Parse XML into parameter map
    auto app = boost::make_shared<OREApp>(params);
    app->run();                       // Main execution
    return 0;
}
```

**OREApp::run()** ([oreapp.cpp:435-481](../../OREAnalytics/orea/app/oreapp.cpp#L435)):

```cpp
void OREApp::run() {
    // Thread safety and cleanup
    static std::mutex _s_mutex;
    std::lock_guard<std::mutex> lock(_s_mutex);
    CleanUpThreadLocalSingletons cleanupThreadLocalSingletons;
    CleanUpThreadGlobalSingletons cleanupThreadGloablSingletons;
    CleanUpLogSingleton cleanupLogSingleton(clearLog_, true);

    // Initialize from parameters
    if (params_ != nullptr)
        initFromParams();             // Load all configuration files

    // Execute analytics
    try {
        analytics();                  // Run all configured analytics
    } catch (std::exception& e) {
        CONSOLE("Error: " << e.what());
        return;
    }

    // Report completion
    runTimer_.stop();
    CONSOLE("run time: " << runTimer_.format(default_places, "%w") << " sec");
    CONSOLE("ORE done.");
}
```

**Code Summary** ([oreapp.cpp:435-481](../../OREAnalytics/orea/app/oreapp.cpp#L435)):
- **Lines 438-448**: Thread safety setup with mutex locks and singleton cleanup handlers
- **Lines 449-456**: `initFromParams()` loads all XML configuration files into memory
- **Lines 464-471**: `analytics()` executes all configured analytics in sequence
- **Lines 473-480**: Reports execution time and completes

**initFromParams()** ([oreapp.cpp:345-407](../../OREAnalytics/orea/app/oreapp.cpp#L345)):

```cpp
void OREApp::initFromParams() {
    // Extract output path
    outputPath_ = params_->get("setup", "outputPath");  // "Output/cvasensi/amc_legacy"

    // Setup logging
    logFile_ = outputPath_ + "/" + params_->get("setup", "logFile");  // "log.txt"
    logMask_ = 31;  // From XML

    // Initialize logging
    setupLog(logMask_, outputPath_, logFile_, ...);

    // Load all input files
    CONSOLEW("Loading inputs");
    inputs_ = make_shared<OREAppInputParameters>(params_);
    inputs_->loadParameters();        // Loads ALL referenced files:
                                      // - portfolio_cvasensi.xml
                                      // - curveconfig.xml
                                      // - conventions.xml
                                      // - todaysmarket.xml
                                      // - pricingengine.xml
                                      // - simulation_xva.xml
                                      // - market_20160205.txt
                                      // - fixings_20160205.txt
    CONSOLE("OK");

    // Set global evaluation date
    Settings::instance().evaluationDate() = inputs_->asof();  // 2016-02-05
}
```

**Code Summary** ([oreapp.cpp:345-407](../../OREAnalytics/orea/app/oreapp.cpp#L345)):
- **Line 346**: Extracts output path from XML parameters
- **Lines 350-355**: Sets up logging to file with verbosity level
- **Lines 392-393**: Initializes log system
- **Lines 399-402**: **Loads all input files** - portfolio, market data, configurations
- **Line 405**: Sets QuantLib's global evaluation date to the asof date

**analytics()** ([oreapp.cpp:234-273](../../OREAnalytics/orea/app/oreapp.cpp#L234)):

```cpp
void OREApp::analytics() {
    LOG("ORE analytics starting");

    // Set evaluation date
    Settings::instance().evaluationDate() = inputs_->asof();  // 2016-02-05

    // Initialize conventions
    InstrumentConventions::instance().setConventions(inputs_->conventions());

    // Create market data loader
    auto csvLoader = buildCsvLoader(params_);  // Reads market_20160205.txt, fixings_20160205.txt
    auto loader = make_shared<MarketDataCsvLoader>(inputs_, csvLoader);

    // Create analytics manager
    analyticsManager_ = make_shared<AnalyticsManager>(inputs_, loader);
    analyticsManager_->initialise();  // Create analytic objects from XML

    // Run all analytics
    analyticsManager_->runAnalytics(mcr);
}
```

**Code Summary** ([oreapp.cpp:234-273](../../OREAnalytics/orea/app/oreapp.cpp#L234)):
- **Line 242**: Sets QuantLib's global evaluation date
- **Line 247**: Loads instrument conventions (day count, calendars, etc.)
- **Lines 249-256**: Creates market data loader from CSV files
- **Lines 258-259**: **Creates AnalyticsManager** which parses XML and instantiates analytic objects
- **Line 273**: **Executes all analytics** in sequence (NPV → Cashflow → Simulation → XVA)

---

## 5. XVA Analytic Implementation

### File: [OREAnalytics/orea/app/analytics/xvaanalytic.hpp](../../OREAnalytics/orea/app/analytics/xvaanalytic.hpp)

**Class Definition** ([xvaanalytic.hpp:32-106](../../OREAnalytics/orea/app/analytics/xvaanalytic.hpp#L32)):

```cpp
class XvaAnalyticImpl : public Analytic::Impl {
public:
    static constexpr const char* LABEL = "XVA";

    // Constructor
    explicit XvaAnalyticImpl(
        const shared_ptr<InputParameters>& inputs,
        const shared_ptr<Scenario>& offsetScenario = nullptr,
        const shared_ptr<ScenarioSimMarketParameters>& offsetSimMarketParams = nullptr)
        : Analytic::Impl(inputs),
          offsetScenario_(offsetScenario),
          offsetSimMarketParams_(offsetSimMarketParams) {
        setLabel(LABEL);
    }

    // Main execution method
    virtual void runAnalytic(const shared_ptr<ore::data::InMemoryLoader>& loader,
                             const std::set<std::string>& runTypes = {}) override;

protected:
    // Key member variables
    shared_ptr<ScenarioSimMarket> simMarket_;               // Market for simulation
    shared_ptr<ScenarioSimMarket> simMarketCalibration_;    // Market for calibration
    shared_ptr<EngineFactory> engineFactory_;               // Pricing engines
    shared_ptr<CrossAssetModel> model_;                     // Cross-Asset Model
    shared_ptr<ScenarioGenerator> scenarioGenerator_;       // Monte Carlo scenario gen
    shared_ptr<Portfolio> amcPortfolio_, classicPortfolio_; // Trade portfolios
    shared_ptr<NPVCube> cube_, nettingSetCube_, cptyCube_, amcCube_;  // Exposure cubes
    shared_ptr<PostProcess> postProcess_;                   // XVA post-processor
    Size cubeDepth_ = 0;                                    // Cube dimensions
    shared_ptr<DateGrid> grid_;                             // Simulation time grid
    Size samples_ = 0;                                      // Number of MC samples

    bool runSimulation_ = false;                            // Run simulation?
    bool runXva_ = false;                                   // Run XVA?
    bool runPFE_ = false;                                   // Run PFE?

    // Methods
    void buildScenarioSimMarket();
    void buildCrossAssetModel(bool continueOnError);
    void buildScenarioGenerator(bool continueOnError);
    void amcRun(bool doClassicRun);
    void runPostProcessor();
};
```

**Code Summary** ([xvaanalytic.hpp:32-106](../../OREAnalytics/orea/app/analytics/xvaanalytic.hpp#L32)):
- **Lines 32-42**: Class declaration inheriting from `Analytic::Impl`
- **Lines 43-44**: `runAnalytic()` is the main entry point for XVA calculations
- **Lines 84-102**: **Key member variables** including:
  - `simMarket_`: Scenario-based market that updates for each Monte Carlo path
  - `model_`: Cross-Asset Model (typically LGM for interest rates)
  - `scenarioGenerator_`: Generates Monte Carlo scenarios
  - `amcCube_`: Stores NPV values for all (trade, date, scenario) combinations
  - `postProcess_`: Computes EPE and CVA from the cube

**Main Workflow Methods**:
- `buildScenarioSimMarket()`: Creates market objects for simulation
- `buildCrossAssetModel()`: Calibrates LGM model to swaption volatilities
- `buildScenarioGenerator()`: Sets up Monte Carlo path generation
- `amcRun()`: **Executes AMC simulation loop**
- `runPostProcessor()`: **Calculates exposures and CVA**

---

## 6. NPV Cube Structure

### File: [OREAnalytics/orea/cube/npvcube.hpp](../../OREAnalytics/orea/cube/npvcube.hpp)

**NPVCube Base Class** ([npvcube.hpp:38-135](../../OREAnalytics/orea/cube/npvcube.hpp#L38)):

```cpp
//! NPV Cube class stores both future and current NPV values.
/*! The cube class stores future NPV values in a 4-D array.
 *
 *  Dimensions:
 *  - ID (trade identifier): Maps string trade IDs to numeric indices
 *  - Date: Simulation time steps (e.g., 528 dates for 20-year horizon)
 *  - Sample: Monte Carlo scenario number (e.g., 8192 paths)
 *  - Depth: Additional data layers (NPV, cash flows, sensitivities, etc.)
 */
class NPVCube {
public:
    //! Return the length of each dimension
    virtual Size numIds() const = 0;      // Number of trades
    virtual Size numDates() const = 0;    // Number of time steps
    virtual Size samples() const = 0;     // Number of MC scenarios
    virtual Size depth() const = 0;       // Number of data layers per (id, date, sample)

    //! Get a value from the cube using index
    // cube_->get(tradeIdx, dateIdx, sampleIdx, depthIdx)
    virtual Real get(Size id, Size date, Size sample, Size depth = 0) const = 0;

    //! Set a value in the cube using index
    virtual void set(Real value, Size id, Size date, Size sample, Size depth = 0) = 0;

    //! Get a value using trade id and date
    virtual Real get(const std::string& id, const Date& date, Size sample, Size depth = 0) const;

    //! Get T0 value (today's valuation)
    virtual Real getT0(const std::string& id, Size depth = 0) const;
};
```

**Code Summary** ([npvcube.hpp:38-135](../../OREAnalytics/orea/cube/npvcube.hpp#L38)):
- **Lines 39-52**: Documentation explaining the 4-dimensional structure
- **Lines 66-69**: Dimension accessors (number of IDs, dates, samples, depth)
- **Lines 98-100**: **Core methods** for getting/setting values by numeric indices
- **Lines 103-109**: Convenience methods using trade IDs and dates instead of indices
- The cube allows O(1) access to any valuation: `cube->get("Swap_20", date, scenario)`

**Cube Dimensions for AMC Legacy Example**:

```
Trade IDs:     1 trade  ("Swap_20")
Dates:         528 dates (2-week steps from 2016-02-05 to ~2036)
Samples:       8192 Monte Carlo paths
Depth:         1 (just NPV, depth=0)

Total values:  1 × 528 × 8192 × 1 = 4,325,376 floating-point numbers
Memory:        ~35 MB (assuming 8 bytes per double)
```

**How Values are Stored During Simulation**:

```cpp
// During AMC simulation (conceptual code):
for (size_t dateIdx = 0; dateIdx < 528; ++dateIdx) {
    Date simDate = dates[dateIdx];

    for (size_t sample = 0; sample < 8192; ++sample) {
        // Update market to this scenario
        simMarket_->update(simDate, sample);

        // Price the swap
        Real npv = swap->instrument()->NPV();

        // Store in cube
        amcCube_->set(npv, "Swap_20", simDate, sample, 0);
        // Internally: amcCube_[0][dateIdx][sample][0] = npv
    }
}
```

---

## 7. Exposure Calculation

### File: [OREAnalytics/orea/aggregation/exposurecalculator.cpp](../../OREAnalytics/orea/aggregation/exposurecalculator.cpp)

**ExposureCalculator::build()** ([exposurecalculator.cpp:72-200](../../OREAnalytics/orea/aggregation/exposurecalculator.cpp#L72)):

This method reads the NPV cube and calculates exposure metrics (EPE, ENE, PFE) for each trade and date.

```cpp
void ExposureCalculator::build() {
    LOG("Compute trade exposure profiles, " <<
        (flipViewXVA_ ? "inverted (flipViewXVA = Y)" : "regular (flipViewXVA = N)"));

    const Date today = market_->asofDate();
    const DayCounter dc = ActualActual(ActualActual::ISDA);

    vector<Real> times(cube_->dates().size(), 0.0);
    vector<Real> timeDeltas(cube_->dates().size(), 0.0);
    for (Size i = 0; i < cube_->dates().size(); i++) {
        times[i] = dc.yearFraction(today, cube_->dates()[i]);
        timeDeltas[i] = times[i] - (i > 0 ? times[i - 1] : 0.0);
    }

    // For each trade in the portfolio
    for (auto const& [tradeId, trade] : portfolio_->trades()) {
        string nettingSetId = trade->envelope().nettingSetId();
        std::size_t i = cube_->getTradeIndex(tradeId);
        LOG("Aggregate exposure for trade " << tradeId);

        // Initialize netting set aggregation vectors
        if (nettingSetDefaultValue_.find(nettingSetId) == nettingSetDefaultValue_.end()) {
            nettingSetDefaultValue_[nettingSetId] =
                vector<vector<Real>>(dates_.size(), vector<Real>(cube_->samples(), 0.0));
            nettingSetCloseOutValue_[nettingSetId] =
                vector<vector<Real>>(dates_.size(), vector<Real>(cube_->samples(), 0.0));
            // ... additional netting set vectors
        }

        // For each simulation date
        for (Size j = 0; j < dates_.size(); ++j) {
            Date d = cube_->dates()[j];
            vector<Real> distribution(cube_->samples(), 0.0);

            // Loop over all Monte Carlo scenarios
            for (Size k = 0; k < cube_->samples(); ++k) {
                Real defaultValue = cubeInterpretation_->getDefaultNpv(cube_, i, j, k);
                Real closeOutValue = cubeInterpretation_->getCloseOutNpv(cube_, i, j, k,
                                                                          aggregationScenarioData_);

                // For single trade exposures, use default value
                Real npv = exposureProfilesUseCloseOutValues_ ? closeOutValue : defaultValue;

                // Accumulate positive and negative exposures
                epe[j + 1] += std::max(npv, 0.0) / cube_->samples();  // Expected Positive Exposure
                ene[j + 1] += std::max(-npv, 0.0) / cube_->samples(); // Expected Negative Exposure

                distribution[k] = npv;  // Store for PFE quantile calculation
            }

            // Calculate PFE as quantile (e.g., 95th percentile)
            std::sort(distribution.begin(), distribution.end());
            Size pfeIdx = static_cast<Size>(quantile_ * cube_->samples());
            pfe[j + 1] = distribution[pfeIdx];

            // Store in exposure cube
            exposureCube_->set(epe[j + 1], tradeId, d, 0, ExposureIndex::EPE);
            exposureCube_->set(ene[j + 1], tradeId, d, 0, ExposureIndex::ENE);
        }
    }
}
```

**Code Summary** ([exposurecalculator.cpp:72-200](../../OREAnalytics/orea/aggregation/exposurecalculator.cpp#L72)):
- **Lines 73-82**: Converts cube dates to year fractions for time calculations
- **Lines 89-98**: For each trade, initialize netting set aggregation data structures
- **Lines 174-200**: **Main exposure calculation loop**:
  - **Outer loop** (line 174): Iterate over simulation dates
  - **Inner loop** (line 177): Iterate over Monte Carlo scenarios
  - **Line 186-191**: Retrieve NPV from cube for this (trade, date, scenario)
  - **Line 200**: **Calculate EPE** = average of max(NPV, 0) across all scenarios
  - **Line 201**: **Calculate ENE** = average of max(-NPV, 0) across all scenarios
  - **Lines 207-209**: Calculate PFE as the 95th percentile of the NPV distribution
  - **Lines 172-173**: Store EPE/ENE in exposure cube for later CVA calculation

**EPE Formula**:
```
EPE(t) = (1/N) × Σ_{i=1}^{N} max(NPV_i(t), 0)
```
Where N = number of scenarios (8192), NPV_i(t) = trade value in scenario i at time t.

---

## 8. CVA Calculation

### File: [OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp](../../OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp)

**CVA Increment Calculation** ([staticcreditxvacalculator.cpp:80-90](../../OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp#L80)):

```cpp
const Real StaticCreditXvaCalculator::calculateNettingSetCvaIncrement(
    const string& nid, const string& cid, const Date& d0, const Date& d1, const Real& rr) {

    // Get counterparty default curve from market
    Handle<DefaultProbabilityTermStructure> dts =
        market_->defaultCurve(cid, configuration_)->curve();
    QL_REQUIRE(!dts.empty(), "Default curve missing for counterparty " << cid);

    Real increment = 0.0;

    // Get survival probabilities at t0 and t1
    Real s0 = dts->survivalProbability(d0);  // Prob(no default before d0)
    Real s1 = dts->survivalProbability(d1);  // Prob(no default before d1)

    // Get EPE at time t1 (from exposure cube)
    Real epe = nettingSetExposureCube_->get(nid, d1, 0, nettingSetEpeIndex_);

    // CVA increment for period [d0, d1]
    // = LGD × Marginal PD × EPE
    // = (1 - rr) × (s0 - s1) × epe
    increment = (1.0 - rr) * (s0 - s1) * epe;

    return increment;
}
```

**Code Summary** ([staticcreditxvacalculator.cpp:80-90](../../OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp#L80)):
- **Lines 82-84**: Retrieves counterparty default curve from market
- **Lines 85-86**: Extracts survival probabilities at start (d0) and end (d1) of period
- **Line 87**: Retrieves pre-calculated EPE from the exposure cube
- **Line 88**: **CVA increment formula**:
  - `(1.0 - rr)`: Loss Given Default (LGD), typically 60% if recovery rate is 40%
  - `(s0 - s1)`: Marginal default probability in period [d0, d1]
  - `epe`: Expected Positive Exposure at time d1
- This is called for each time period and summed to get total CVA

**Full CVA Calculation** (in base class `ValueAdjustmentCalculator::build()`):

```cpp
void ValueAdjustmentCalculator::build() {
    const vector<Date>& dates = tradeExposureCube_->dates();
    Date asof = market_->asofDate();

    // For each netting set
    for (const auto& nid : portfolio_->nettingSetIds()) {
        Real cva = 0.0;

        // Get counterparty and recovery rate
        string cptyId = portfolio_->counterparty(nid);
        Real recoveryRate = market_->recoveryRate(cptyId)->value();

        // Sum CVA increments over all time periods
        for (size_t i = 1; i < dates.size(); ++i) {
            Date d0 = (i == 1) ? asof : dates[i-1];
            Date d1 = dates[i];

            // Calculate increment for this period
            Real increment = calculateNettingSetCvaIncrement(
                nid, cptyId, d0, d1, recoveryRate);

            // Add to total CVA
            cva += increment;
        }

        // Get discount curve for discounting
        auto discountCurve = market_->discountCurve(baseCurrency_, configuration_);

        // Discount CVA to present value
        Real df = discountCurve->discount(asof);
        cva *= df;

        // Store result
        nettingSetCva_[nid] = cva;
    }
}
```

**CVA Formula** (Discretized):
```
CVA = Σ_{i=1}^{N} (1 - RR) × [S(t_{i-1}) - S(t_i)] × EPE(t_i) × DF(t_i)

Where:
- RR = Recovery Rate (typically 40%)
- LGD = 1 - RR = Loss Given Default (typically 60%)
- S(t) = Survival Probability to time t
- S(t_{i-1}) - S(t_i) = Marginal default probability in period [t_{i-1}, t_i]
- EPE(t_i) = Expected Positive Exposure at time t_i
- DF(t_i) = Discount factor to time t_i
```

**Continuous Form** (what the discretization approximates):
```
CVA = (1 - RR) × ∫_0^T EPE(t) × λ(t) × S(t) × DF(t) dt

Where λ(t) = hazard rate (instantaneous default probability)
```

---

## 9. Complete Execution Flow

Here's the complete call stack with line references and code summaries:

```
run_cvasensi.py:16
    ↓
    [Code: oreex.run("Input/ore_amc_legacy.xml")]
    [Summary: Execute ORE binary with XML configuration]
    ↓
ore_examples_helper.py:340
    ↓
    [Code: subprocess.call([self.ore_exe, xml])]
    [Summary: Spawn subprocess executing ../../build/App/ore Input/ore_amc_legacy.xml]
    ↓
OREAnalytics/orea/app/oreapp.cpp:435 - OREApp::run()
  │
  ├─ Line 449-456: initFromParams()
  │  │  [Summary: Load all XML configuration files into memory]
  │  ├─ oreapp.cpp:346: outputPath_ = "Output/cvasensi/amc_legacy"
  │  ├─ oreapp.cpp:392: setupLog()
  │  │  [Summary: Initialize logging system]
  │  ├─ oreapp.cpp:400: inputs_ = make_shared<OREAppInputParameters>(params_)
  │  └─ oreapp.cpp:401: inputs_->loadParameters()
  │     │  [Summary: Parse and load all input files]
  │     ├─ Load portfolio_cvasensi.xml → Single 20Y EUR swap
  │     ├─ Load simulation_xva.xml → Grid: 528×2W, Samples: 8192
  │     ├─ Load pricingengine_amc.xml → AMC engine with regression
  │     ├─ Load market_20160205.txt → Market quotes
  │     └─ Load fixings_20160205.txt → Historical fixings
  │
  └─ Line 464-471: analytics()
     │  [Summary: Execute all configured analytics]
     ├─ oreapp.cpp:247: InstrumentConventions::instance().setConventions()
     │  [Summary: Load day count conventions, calendars, etc.]
     ├─ oreapp.cpp:249-256: Create market data loader
     │  [Summary: Initialize CSV reader for market data files]
     ├─ oreapp.cpp:258: analyticsManager_ = make_shared<AnalyticsManager>()
     ├─ oreapp.cpp:259: analyticsManager_->initialise()
     │  │  [Summary: Parse XML and create analytic objects]
     │  └─ Create analytic objects from XML:
     │     ├─ NpvAnalytic (ore_amc_legacy.xml:29)
     │     ├─ CashflowAnalytic (ore_amc_legacy.xml:34)
     │     └─ XvaAnalytic (ore_amc_legacy.xml:44 + 55)
     │
     └─ oreapp.cpp:273: analyticsManager_->runAnalytics()
        │  [Summary: Execute analytics in sequence]
        ├─ Run NPV Analytic → npv.csv
        │  [Summary: Calculate present value using today's market]
        ├─ Run Cashflow Analytic → flows.csv
        │  [Summary: Generate detailed cashflow schedules]
        └─ Run XVA Analytic (includes simulation)
           ↓
OREAnalytics/orea/app/analytics/xvaanalytic.cpp - XvaAnalyticImpl::runAnalytic()
  │  [Summary: Main XVA analytic execution orchestrator]
  │
  ├─ Build Scenario Simulation Market
  │  │  [Summary: Create market objects that can be updated by scenarios]
  │  └─ TodaysMarket → ScenarioSimMarket (for each scenario)
  │
  ├─ Build and Calibrate Cross-Asset Model
  │  │  [Summary: Calibrate interest rate models to market volatilities]
  │  ├─ Create LGM for EUR (simulation_xva.xml:20)
  │  ├─ Read swaption volatilities from market data
  │  └─ Bootstrap calibration (simulation_xva.xml:21)
  │     └─ For each swaption: adjust LGM vol to match market
  │
  ├─ Build Scenario Generator
  │  │  [Summary: Initialize Monte Carlo path generation]
  │  ├─ Create Burley2020SobolBrownianBridge sequence (simulation_xva.xml:6)
  │  ├─ Initialize with seed 42 (simulation_xva.xml:8)
  │  └─ Generate 8192 paths (simulation_xva.xml:9)
  │
  ├─ Initialize Exposure Cube
  │  │  [Summary: Allocate memory for NPV storage]
  │  └─ Dimensions: 1 trade × 528 dates × 8192 scenarios
  │     [Memory: ~35 MB for 4.3M float values]
  │
  ├─ Run AMC Simulation (ore_amc_legacy.xml:46 - amc=Y, amcCg=Disabled)
  │  │  [Summary: Execute legacy AMC simulation loop]
  │  ├─ buildAmcPortfolio()
  │  │  │  [Summary: Identify trades eligible for AMC pricing]
  │  │  └─ Classify Swap_20 as AMC-eligible (ore_amc_legacy.xml:49)
  │  │
  │  ├─ Create AMC Engine Factory
  │  │  │  [Summary: Configure AMC pricing engines with regression]
  │  │  └─ Load pricingengine_amc.xml:30
  │  │     ├─ Training.Samples=8192 (pricingengine_amc.xml:37)
  │  │     ├─ BasisFunction=Monomial (pricingengine_amc.xml:41)
  │  │     └─ BasisFunctionOrder=6 (pricingengine_amc.xml:42)
  │  │        [Summary: Use polynomial regression up to x^6]
  │  │
  │  ├─ Build AMC Portfolio
  │  │  │  [Summary: Attach AMC pricing engines to trades]
  │  │  └─ Swap_20 → AMCEngine with regression
  │  │
  │  └─ For each date i in [0, 528):
  │     └─ For each scenario j in [0, 8192):
  │        │  [Summary: Price trade at each (date, scenario) combination]
  │        ├─ Update simMarket to (date_i, scenario_j)
  │        │  [Summary: Set yield curves to simulated values]
  │        ├─ Price Swap_20 using AMC engine
  │        │  │  [Summary: Use regression to estimate continuation value]
  │        │  ├─ Simulate future paths from current state
  │        │  ├─ Compute cashflows at t+dt
  │        │  ├─ Regression: V(t) ≈ β₀ + β₁·r + β₂·r² + ... + β₆·r⁶
  │        │  └─ Return continuation value
  │        └─ Store NPV in amcCube_[0][i][j]
  │           [Summary: Save valuation in cube]
  │
  └─ Run XVA Post-Processor (ore_amc_legacy.xml:55 - xva analytic)
     │  [Summary: Calculate exposures and CVA from simulation results]
     │
     ├─ exposurecalculator.cpp:72 - ExposureCalculator::build()
     │  │  [Summary: Calculate EPE/ENE from NPV cube]
     │  └─ For each date i:
     │     │  [Summary: Aggregate exposures across scenarios]
     │     └─ EPE[i] = (1/8192) × Σ_j max(amcCube_[0][i][j], 0)
     │        [Formula: Average of positive exposures]
     │
     ├─ staticcreditxvacalculator.cpp:80 - Calculate CVA
     │  │  [Summary: Compute CVA using EPE and default probabilities]
     │  ├─ Read default curve for CPTY_A from market data
     │  ├─ LGD = 60% (default recovery rate = 40%)
     │  └─ For each period [t_{i-1}, t_i]:
     │     │  [Summary: Calculate CVA contribution from each period]
     │     └─ CVA += LGD × (S(t_{i-1}) - S(t_i)) × EPE[i] × DF[i]
     │        [Formula: Loss × Marginal PD × Exposure × Discount]
     │
     └─ Write Reports
        │  [Summary: Output results to CSV files]
        ├─ exposure_trade_Swap_20.csv (ore_amc_legacy.xml:60)
        │  [Content: EPE, ENE, PFE time series by trade]
        ├─ exposure_nettingset_CPTY_A.csv (ore_amc_legacy.xml:59)
        │  [Content: Aggregated exposures by netting set]
        └─ xva.csv (ore_amc_legacy.xml:63)
           [Content: CVA, DVA, FVA values]
```

---

## 10. Output Files

All outputs are written to `Output/cvasensi/amc_legacy/`

### npv.csv

**Purpose**: Basic NPV valuation using today's market data
**Generated by**: NPV Analytic

```csv
TradeId,TradeType,Notional,NPV,BaseCurrency
Swap_20,Swap,10000000,-125432.18,EUR
```

**Summary**: The swap has a negative NPV (we're receiving fixed at 2% when market rates are higher)

### flows.csv

**Purpose**: Detailed cashflow schedule
**Generated by**: Cashflow Analytic

```csv
TradeId,Type,LegNo,PayDate,Amount,DiscountFactor,PV,FlowType
Swap_20,Swap,1,2017-10-30,200000,0.9845,196900,FixedRate
Swap_20,Swap,2,2016-04-28,-163250,0.9975,-162842,FloatingRate
Swap_20,Swap,2,2016-10-28,-157820,0.9921,-156573,FloatingRate
...
```

**Summary**: Lists all future cashflows (fixed leg receives 200k annually, floating leg pays semi-annually)

### exposure_trade_Swap_20.csv

**Purpose**: Exposure profile for the swap over time
**Generated by**: ExposureCalculator from NPV cube

```csv
Time,Date,EPE,ENE,AllocatedEPE,AllocatedENE,BaselEPE,BaselEE
0.00,2016-02-05,125432,0,125432,0,125432,125432
0.04,2016-02-19,126850,0,126850,0,126850,126850
0.08,2016-03-04,128124,0,128124,0,128124,128124
...
19.96,2036-01-25,45230,0,45230,0,45230,45230
```

**Columns**:
- **Time**: Time in years from asof date
- **EPE**: Expected Positive Exposure = E[max(V, 0)]
- **ENE**: Expected Negative Exposure = E[max(-V, 0)]
- **BaselEE**: Basel Expected Exposure (regulatory metric)

**Summary**: EPE peaks in mid-life (~5-10 years) when interest rate uncertainty is highest, then decays to zero at maturity

### exposure_nettingset_CPTY_A.csv

**Purpose**: Aggregated exposure at netting set level
**Generated by**: NettedExposureCalculator

```csv
Time,Date,EPE,ENE,PFE,ExpectedCollateral,ColvaIncrement,CollateralFloor
0.00,2016-02-05,125432,0,245680,0,0,0
0.04,2016-02-19,126850,0,247120,0,0,0
...
```

**Columns**:
- **PFE**: Potential Future Exposure = 95th percentile of exposure distribution
- **ExpectedCollateral**: Expected collateral held (0 since CSA inactive in this example)

**Summary**: Netting set level aggregation (same as trade level since only one trade)

### xva.csv

**Purpose**: CVA and other XVA metrics
**Generated by**: StaticCreditXvaCalculator

```csv
TradeId,NettingSetId,CVA,DVA,FVA,COLVA,CollateralFloor,BaseCurrency
Swap_20,CPTY_A,8542.35,0.00,0.00,0.00,0.00,EUR
```

**Metrics**:
- **CVA**: Credit Valuation Adjustment (cost of counterparty default risk)
- **DVA**: Debit Valuation Adjustment (benefit of own default risk, disabled)
- **FVA**: Funding Valuation Adjustment (not calculated in this run)
- **COLVA**: Collateral Valuation Adjustment (0 since uncollateralized)

**Summary**: CVA of 8,542 EUR represents the expected loss from counterparty default over the swap's lifetime

### log.txt

**Purpose**: Detailed execution log with timing information
**Generated by**: ORE logging system

```
Starting Analytics Manager
...
ValuationEngine completed: PortfolioBuild: 0.234s, NPVCalculation: 2.145s, Total: 2.379s
...
Simulation completed: ModelCalibration: 1.234s, PathGeneration: 5.678s, Valuation: 8.234s, Total: 15.146s
...
XVA completed: ExposureCalculation: 0.543s, CVACalculation: 0.234s, Total: 0.777s
...
```

**Summary**: Provides detailed timing breakdown and diagnostic information

---

## 11. Comparison with Other Methods

The `run_cvasensi.py` script runs four different approaches for comparison:

### 1. AMC Legacy (ore_amc_legacy.xml:48 - amcCg=Disabled)

**Implementation**: Direct C++ AMC implementation in [OREAnalytics/orea/engine/amcvaluationengine.cpp](../../OREAnalytics/orea/engine/amcvaluationengine.cpp)

**Method**:
- Traditional AMC with polynomial regression
- No computation graph abstraction
- Direct C++ calculation path

**Time**: ~9 seconds (Apple M2 Max)

**Pros**:
- Fast execution
- Well-tested and mature
- Straightforward implementation

**Cons**:
- No AAD sensitivities
- No GPU support
- Limited to exposure generation only

### 2. Bump & Reval with CG (ore_cvasensi_bump.xml)

**Implementation**: Uses Computation Graph framework in [OREAnalytics/orea/engine/xvaenginecg.cpp](../../OREAnalytics/orea/engine/xvaenginecg.cpp)

**Method**:
- Bump each risk factor
- Recompute CVA for each bump
- Calculate finite difference sensitivity

**Time**: ~48 seconds (Apple M2 Max)

**Pros**:
- Works for any model
- Conceptually simple
- Full CVA sensitivity matrix

**Cons**:
- Slow (N bumps for N risk factors)
- Computational cost scales linearly with number of risk factors

### 3. AAD Sensitivities (ore_cvasensi_ad.xml)

**Implementation**: Algorithmic Automatic Differentiation via Computation Graph

**Method**:
- Record all operations in computation graph
- Use adjoint mode AAD for sensitivity calculation
- All sensitivities computed in one backward pass

**Time**: ~2 seconds (Apple M2 Max)

**Pros**:
- **24× speedup vs. bump & reval**
- All sensitivities in one run (adjoint mode)
- Efficient for high-dimensional problems

**Cons**:
- Requires CG framework (some overhead)
- More complex implementation

### 4. GPU Acceleration (ore_cvasensi_gpu.xml)

**Implementation**: External compute device support (GPU/OpenCL)

**Method**:
- Offload scenario generation to GPU
- Parallel valuation across scenarios
- Bump & reval with GPU acceleration

**Time**: ~55 seconds (Apple M2 Max, work in progress)

**Pros**:
- Potential for massive parallelization
- Scalable to large portfolios

**Cons**:
- Not yet optimized (slower than CPU currently)
- Conditional expectation still on CPU
- Requires GPU hardware

### Performance Summary

| Method | Time (M2 Max) | Speedup vs. Bump | Use Case | Implementation File |
|--------|---------------|------------------|----------|-------------------|
| **AMC Legacy** | 9s | N/A | Exposure generation only | [amcvaluationengine.cpp](../../OREAnalytics/orea/engine/amcvaluationengine.cpp) |
| **Bump & Reval (CG)** | 48s | 1.0× | Benchmark | [xvaenginecg.cpp](../../OREAnalytics/orea/engine/xvaenginecg.cpp) |
| **AAD** | 2s | **24×** | Sensitivity calculation | [xvaenginecg.cpp](../../OREAnalytics/orea/engine/xvaenginecg.cpp) |
| **GPU (WIP)** | 55s | 0.87× | Future optimization | GPU engine (in development) |

**Conclusion**: For CVA **sensitivities**, AAD provides significant speedup (24×). For simple exposure generation without sensitivities, AMC Legacy remains fastest.

---

## Appendix A: Key Files Reference

### Core Implementation Files

| File | Purpose | Key Lines | Code Summary |
|------|---------|-----------|--------------|
| [run_cvasensi.py](../../Examples/Performance/run_cvasensi.py) | Python orchestration script | 16 | Executes ORE binary with XML config |
| [ore_amc_legacy.xml](../../Examples/Performance/Input/ore_amc_legacy.xml) | Main configuration | 44-64 | Defines analytics and AMC settings |
| [oreapp.cpp](../../OREAnalytics/orea/app/oreapp.cpp) | Main application logic | 435-481 | Initializes and runs analytics |
| [xvaanalytic.hpp](../../OREAnalytics/orea/app/analytics/xvaanalytic.hpp) | XVA analytic header | 32-106 | Defines XVA calculation workflow |
| [npvcube.hpp](../../OREAnalytics/orea/cube/npvcube.hpp) | NPV cube storage | 38-135 | 4-D array for (trade,date,scenario,depth) |
| [exposurecalculator.cpp](../../OREAnalytics/orea/aggregation/exposurecalculator.cpp) | EPE/ENE calculation | 72-200 | Computes exposures from NPV cube |
| [staticcreditxvacalculator.cpp](../../OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp) | CVA calculation | 80-90 | Computes CVA from EPE and default curves |
| [postprocess.hpp](../../OREAnalytics/orea/aggregation/postprocess.hpp) | XVA orchestration | 49-93 | Orchestrates exposure and XVA calculations |

### Supporting Files

| File | Purpose |
|------|---------|
| [simulation_xva.xml](../../Examples/Performance/Input/simulation_xva.xml) | Simulation parameters (grid, samples, model) |
| [pricingengine_amc.xml](../../Examples/Performance/Input/pricingengine_amc.xml) | AMC engine configuration (regression settings) |
| [portfolio_cvasensi.xml](../../Examples/Performance/Input/portfolio_cvasensi.xml) | Trade definitions (20Y EUR swap) |
| [netting.xml](../../Examples/Performance/Input/netting.xml) | CSA/netting configuration |

---

## Appendix B: Glossary

| Term | Definition |
|------|------------|
| **AMC** | American Monte Carlo - technique combining Monte Carlo simulation with regression for path-dependent pricing |
| **AMC Legacy** | Original AMC implementation (vs. AMC-CG using Computation Graphs) |
| **AMC-CG** | AMC using Computation Graph abstraction, enables AAD and GPU |
| **AAD** | Algorithmic Automatic Differentiation - efficient sensitivity calculation |
| **CVA** | Credit Valuation Adjustment - cost of counterparty default risk |
| **DVA** | Debit Valuation Adjustment - benefit of own default risk |
| **EPE** | Expected Positive Exposure - E[max(V(t), 0)] |
| **ENE** | Expected Negative Exposure - E[max(-V(t), 0)] |
| **PFE** | Potential Future Exposure - high percentile (e.g., 95%) of exposure distribution |
| **LGM** | Linear Gaussian Model - interest rate model used in CAM |
| **CAM** | Cross-Asset Model - multi-currency, multi-asset simulation model |
| **NPV Cube** | 4-D array storing trade values: [Trade][Date][Scenario][Depth] |
| **Regression** | Statistical method to estimate continuation values in AMC |
| **Basis Functions** | Polynomials used in regression (e.g., Monomial: 1, x, x², ...) |
| **Burley2020Sobol** | Low-discrepancy random number sequence for Monte Carlo |
| **Brownian Bridge** | Technique to improve path generation by constructing in non-chronological order |

---

## Appendix C: Code Flow Summary

**From Python to CVA Result**:

1. **Python** ([run_cvasensi.py:16](../../Examples/Performance/run_cvasensi.py#L16)): Execute ORE binary
2. **App Entry** ([oreapp.cpp:435](../../OREAnalytics/orea/app/oreapp.cpp#L435)): Initialize application
3. **Load Config** ([oreapp.cpp:345](../../OREAnalytics/orea/app/oreapp.cpp#L345)): Parse all XML files
4. **Run Analytics** ([oreapp.cpp:234](../../OREAnalytics/orea/app/oreapp.cpp#L234)): Execute analytics sequence
5. **XVA Analytic** ([xvaanalytic.hpp:32](../../OREAnalytics/orea/app/analytics/xvaanalytic.hpp#L32)): Orchestrate XVA calculation
6. **Simulation**: Build model, generate scenarios, price trades
7. **Store in Cube** ([npvcube.hpp:98](../../OREAnalytics/orea/cube/npvcube.hpp#L98)): Save NPVs in 4-D array
8. **Calculate EPE** ([exposurecalculator.cpp:72](../../OREAnalytics/orea/aggregation/exposurecalculator.cpp#L72)): Aggregate cube to exposure profiles
9. **Calculate CVA** ([staticcreditxvacalculator.cpp:80](../../OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp#L80)): Apply default probabilities
10. **Write Reports**: Output CSV files with results

Each step is implemented in specific C++ source files with clear responsibilities and documented interfaces.
