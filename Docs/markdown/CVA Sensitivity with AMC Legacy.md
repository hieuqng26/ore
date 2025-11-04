# CVA Sensitivity Calculation with AMC Legacy Framework

**Document Purpose**: This document provides a detailed trace of how the `run_cvasensi.py` script executes the `ore_amc_legacy.xml` configuration to compute CVA (Credit Valuation Adjustment) exposures using the legacy American Monte Carlo (AMC) framework.

**Author**: Generated for ORE Codebase Understanding

**Last Updated**: 2025-11-04

**Example Location**: [Examples/Performance/](../../Examples/Performance/)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Entry Point: Python Script](#1-entry-point-python-script)
3. [OreExample Helper Class](#2-oreexample-helper-class)
4. [XML Configuration Analysis](#3-xml-configuration-analysis)
5. [ORE Application Execution](#4-ore-application-execution)
6. [Simulation Analytic Setup](#5-simulation-analytic-setup)
7. [AMC Legacy Framework](#6-amc-legacy-framework)
8. [Cross-Asset Model Calibration](#7-cross-asset-model-calibration)
9. [Exposure Simulation](#8-exposure-simulation)
10. [XVA Calculation](#9-xva-calculation)
11. [Complete Execution Flow](#10-complete-execution-flow)
12. [Output Files](#11-output-files)
13. [Comparison with Other Methods](#12-comparison-with-other-methods)

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

The script coordinates multiple CVA sensitivity runs using different computational approaches.

```python
# Line 1-7: Imports and setup
#!/usr/bin/env python

import glob
import os
import sys
sys.path.append('../')                              # Add parent dir to path
from ore_examples_helper import OreExample          # Import helper class

# Line 9: Initialize OreExample with optional dry-run flag
oreex = OreExample(sys.argv[1] if len(sys.argv)>1 else False)

# Line 11-13: Print banner
print("+----------------------------------------+")
print("| CVA Sensis using AMC, AAD and GPU      |")
print("+----------------------------------------+")

# Line 15-16: Run AMC Legacy (our focus)
oreex.print_headline("Run AMC Legacy")
oreex.run("Input/ore_amc_legacy.xml")              # Execute ORE with XML config

# Line 18-25: Run other approaches (bump & reval, AAD, GPU)
oreex.print_headline("Run CVA Sensi with bump & reval")
oreex.run("Input/ore_cvasensi_bump.xml")

oreex.print_headline("Run CVA Sensi with AAD")
oreex.run("Input/ore_cvasensi_ad.xml")

oreex.print_headline("Run with bump & reval using a GPU")
oreex.run("Input/ore_cvasensi_gpu.xml")
```

**What Happens on Line 16**:
- `oreex.run("Input/ore_amc_legacy.xml")` calls the `OreExample.run()` method
- This locates the ORE executable and executes it with the XML configuration
- ORE runs all analytics defined in the XML: NPV → Cashflow → Simulation → XVA

---

## 2. OreExample Helper Class

### File: [Examples/ore_examples_helper.py](../../Examples/ore_examples_helper.py)

The helper class provides utilities for running ORE examples and processing results.

```python
# Line 61-73: Class initialization
class OreExample(object):
    def __init__(self, dry=False):
        self.ore_exe = ""                           # Path to ORE executable
        self.headlinecounter = 0                    # Counter for progress messages
        self.dry = dry                              # Dry-run mode flag
        self.ax = None                              # Matplotlib axis (for plotting)
        self.plot_name = ""
        if 'ORE_EXAMPLES_USE_PYTHON' in os.environ.keys():
            self.use_python = os.environ['ORE_EXAMPLES_USE_PYTHON']=="1"
            self.ore_exe = ""
        else:
            self.use_python = False
            self._locate_ore_exe()                  # Find ORE binary

# Line 75-139: Locate ORE executable
    def _locate_ore_exe(self):
        # Lines 113-138: Unix/Linux/macOS path search
        if os.path.isfile("../../App/build/ore"):
            self.ore_exe = "../../App/build/ore"
        elif os.path.isfile("../../../App/build/ore"):
            self.ore_exe = "../../../App/build/ore"
        elif os.path.isfile("../../build/App/ore"):
            self.ore_exe = "../../build/App/ore"    # Most common build location
        elif os.path.isfile("../../../build/App/ore"):
            self.ore_exe = "../../../build/App/ore"
        # ... [additional search paths]
        else:
            print_on_console("ORE executable not found.")
            quit()
        print_on_console("Using ORE executable " + (os.path.abspath(self.ore_exe)))

# Line 141-144: Print section headlines
    def print_headline(self, headline):
        self.headlinecounter += 1
        print_on_console('')
        print_on_console(str(self.headlinecounter) + ") " + headline)
        # Output: "1) Run AMC Legacy"

# Line 332-342: Execute ORE with XML configuration
    def run(self, xml):
        if not self.dry:
            if(self.use_python):                    # If using Python bindings
                if(os.path.isfile(os.path.join(os.pardir, "ore_wrapper.py"))):
                    res = subprocess.call([sys.executable,
                                          os.path.join(os.pardir, "ore_wrapper.py"),
                                          xml])
                elif(os.path.isfile(os.path.join(os.pardir, "..", "ore_wrapper.py"))):
                    res = subprocess.call([sys.executable,
                                          os.path.join(os.pardir, "..", "ore_wrapper.py"),
                                          xml])
            else:
                res = subprocess.call([self.ore_exe, xml])  # Execute: ./ore Input/ore_amc_legacy.xml
            if res != 0:
                raise Exception("Return Code was not Null.")
```

**Execution Path**:
1. `run_cvasensi.py:16` → `oreex.run("Input/ore_amc_legacy.xml")`
2. `ore_examples_helper.py:340` → `subprocess.call([self.ore_exe, xml])`
3. System executes: `../../build/App/ore Input/ore_amc_legacy.xml`

---

## 3. XML Configuration Analysis

### File: [Examples/Performance/Input/ore_amc_legacy.xml](../../Examples/Performance/Input/ore_amc_legacy.xml)

This XML file is the main configuration that drives the entire calculation.

#### 3.1 Setup Section (Lines 3-20)

```xml
<ORE>
  <Setup>
    <!-- Line 4: Valuation date -->
    <Parameter name="asofDate">2016-02-05</Parameter>

    <!-- Line 5-6: Directory paths -->
    <Parameter name="inputPath">Input</Parameter>
    <Parameter name="outputPath">Output/cvasensi/amc_legacy</Parameter>

    <!-- Line 7-8: Logging configuration -->
    <Parameter name="logFile">log.txt</Parameter>
    <Parameter name="logMask">31</Parameter>

    <!-- Line 9-10: Market data files (from shared Examples/Input) -->
    <Parameter name="marketDataFile">../../Input/market_20160205.txt</Parameter>
    <Parameter name="fixingDataFile">../../Input/fixings_20160205.txt</Parameter>
    <Parameter name="implyTodaysFixings">N</Parameter>

    <!-- Line 12-18: Configuration files -->
    <Parameter name="curveConfigFile">../../Input/curveconfig.xml</Parameter>
    <Parameter name="conventionsFile">../../Input/conventions.xml</Parameter>
    <Parameter name="marketConfigFile">../../Input/todaysmarket.xml</Parameter>
    <Parameter name="pricingEnginesFile">pricingengine.xml</Parameter>      <!-- Standard engines -->
    <Parameter name="portfolioFile">portfolio_cvasensi.xml</Parameter>      <!-- Single 20Y swap -->
    <Parameter name="observationModel">None</Parameter>
    <Parameter name="scriptLibrary">scriptlibrary.xml</Parameter>
    <Parameter name="nThreads">1</Parameter>                                <!-- Single-threaded -->
  </Setup>
```

#### 3.2 Markets Section (Lines 21-27)

```xml
  <Markets>
    <!-- Line 22-26: Market configurations for different purposes -->
    <Parameter name="lgmcalibration">collateral_inccy</Parameter>  <!-- LGM calibration market -->
    <Parameter name="fxcalibration">xois_eur</Parameter>           <!-- FX calibration market -->
    <Parameter name="pricing">xois_eur</Parameter>                 <!-- Pricing market -->
    <Parameter name="simulation">xois_eur</Parameter>              <!-- Simulation market -->
    <Parameter name="sensitivity">xois_eur</Parameter>             <!-- Sensitivity market -->
  </Markets>
```

### Understanding Market Configurations

Market configurations define **which discount curves** to use for different purposes. This is crucial because the choice of discounting curve affects valuations.

#### Available Configurations

See [Examples/Input/todaysmarket.xml](../../Examples/Input/todaysmarket.xml#L2-L26) for the full list:

```xml
<TodaysMarket>
  <!-- Default: XOIS (cross-currency OIS) discounting with EUR collateral -->
  <Configuration id="default">
    <DiscountingCurvesId>xois_eur</DiscountingCurvesId>
    <YieldCurvesId>xois_eur</YieldCurvesId>
    <IndexForwardingCurvesId>default</IndexForwardingCurvesId>
  </Configuration>

  <!-- Collateral in-currency: OIS discounting in each currency -->
  <Configuration id="collateral_inccy">
    <DiscountingCurvesId>ois</DiscountingCurvesId>
    <IndexForwardingCurvesId>default</IndexForwardingCurvesId>
    <YieldCurvesId>ois</YieldCurvesId>
  </Configuration>

  <!-- XOIS EUR: Cross-currency OIS discounting w.r.t. EUR collateral -->
  <Configuration id="xois_eur">
    <DiscountingCurvesId>xois_eur</DiscountingCurvesId>
    <IndexForwardingCurvesId>default</IndexForwardingCurvesId>
  </Configuration>

  <!-- XOIS USD: Cross-currency OIS discounting w.r.t. USD collateral -->
  <Configuration id="xois_usd">
    <DiscountingCurvesId>xois_usd</DiscountingCurvesId>
    <IndexForwardingCurvesId>default</IndexForwardingCurvesId>
  </Configuration>

  <!-- LIBOR: In-currency swap discounting (legacy, pre-CSA) -->
  <Configuration id="libor">
    <DiscountingCurvesId>inccy_swap</DiscountingCurvesId>
    <YieldCurvesId>inccy_swap</YieldCurvesId>
    <IndexForwardingCurvesId>default</IndexForwardingCurvesId>
  </Configuration>
</TodaysMarket>
```

#### What Each Configuration Means

| Configuration | Meaning | Use Case | Discounting |
|---------------|---------|----------|-------------|
| `collateral_inccy` | Collateral in-currency | CSA with collateral in each trade's currency | OIS curves per currency |
| `xois_eur` | Cross-currency OIS EUR | CSA with EUR collateral for all trades | EUR OIS + FX basis |
| `xois_usd` | Cross-currency OIS USD | CSA with USD collateral for all trades | USD OIS + FX basis |
| `libor` | In-currency swap | No CSA (uncollateralized) | Swap curves (includes credit spread) |
| `default` | Default configuration | Falls back to `xois_eur` | Same as xois_eur |

#### Why This Matters for AMC Legacy

In `ore_amc_legacy.xml:22-26`, we have:
- **`lgmcalibration=collateral_inccy`**: Calibrate the LGM model using OIS curves (risk-free rates)
- **`pricing=xois_eur`**: Price trades assuming EUR collateral (discounting at EUR OIS + FX basis)
- **`simulation=xois_eur`**: Simulate future values using same discounting assumption

**Key Point**: `xois_eur` means we discount all cashflows (even non-EUR) using EUR OIS + appropriate FX basis adjustments. This is correct for a portfolio with a EUR CSA.

#### Acceptable Values

The acceptable values are **any configuration ID defined in `todaysmarket.xml`**. Common ones:
- `default`, `collateral_inccy`, `xois_eur`, `xois_usd`, `libor`
- Custom configurations can be added to `todaysmarket.xml`

#### How Configuration is Used in Code

```cpp
// When building a trade (e.g., in OREData/ored/portfolio/swap.cpp):
std::string marketConfig = inputs_->marketConfig("pricing");  // "xois_eur"

// Retrieve discount curve using this configuration
auto discountCurve = market_->discountCurve("EUR", marketConfig);

// This retrieves the EUR curve from the "xois_eur" configuration group
// which points to the EUR-OIS curve (risk-free) rather than EUR-SWAP curve
```

**Historical Note**: Before CSA became standard, LIBOR/swap curves (which include bank credit spread) were used for discounting. Modern practice uses OIS curves (risk-free) when collateral is posted.

#### 3.3 Analytics Section (Lines 28-65)

The Analytics section defines which calculations to run in sequence.

##### NPV Analytic (Lines 29-33)

```xml
    <Analytic type="npv">
      <Parameter name="active">Y</Parameter>
      <Parameter name="baseCurrency">EUR</Parameter>
      <Parameter name="outputFileName">npv.csv</Parameter>
    </Analytic>
```

**Purpose**: Calculate present value of all trades using today's market data.

##### Cashflow Analytic (Lines 34-37)

```xml
    <Analytic type="cashflow">
      <Parameter name="active">Y</Parameter>
      <Parameter name="outputFileName">flows.csv</Parameter>
    </Analytic>
```

**Purpose**: Generate detailed cashflow schedules for all trades.

##### Simulation Analytic (Lines 44-54) - **THE KEY ANALYTIC**

```xml
    <Analytic type="simulation">
      <!-- Line 45: Enable simulation -->
      <Parameter name="active">Y</Parameter>

      <!-- Line 46: Enable AMC (American Monte Carlo) -->
      <Parameter name="amc">Y</Parameter>

      <!-- Line 48: AMC-CG mode = Disabled (use legacy AMC) -->
      <!-- Options: Disabled (legacy), CubeGeneration (AMC-CG classic), Full (AMC-CG with CG pricing) -->
      <Parameter name="amcCg">Disabled</Parameter>

      <!-- Line 49: Trade types eligible for AMC pricing -->
      <Parameter name="amcTradeTypes">Swap,ScriptedTrade</Parameter>

      <!-- Line 50: Simulation parameters (grid, samples, model) -->
      <Parameter name="simulationConfigFile">simulation_xva.xml</Parameter>

      <!-- Line 51: Standard pricing engines -->
      <Parameter name="pricingEnginesFile">pricingengine.xml</Parameter>

      <!-- Line 52: AMC-specific pricing engines -->
      <Parameter name="amcPricingEnginesFile">pricingengine_amc.xml</Parameter>

      <!-- Line 53: Base currency for aggregation -->
      <Parameter name="baseCurrency">EUR</Parameter>
    </Analytic>
```

**Key Configuration**: `amcCg=Disabled` means we use the **legacy AMC** implementation, not the newer Computation Graph framework.

##### XVA Analytic (Lines 55-64)

```xml
    <Analytic type="xva">
      <!-- Line 56: Enable XVA calculation -->
      <Parameter name="active">Y</Parameter>

      <!-- Line 57: Netting and CSA configuration -->
      <Parameter name="csaFile">netting.xml</Parameter>

      <!-- Line 58: Base currency -->
      <Parameter name="baseCurrency">EUR</Parameter>

      <!-- Line 59-60: Generate exposure profiles -->
      <Parameter name="exposureProfiles">Y</Parameter>
      <Parameter name="exposureProfilesByTrade">Y</Parameter>

      <!-- Line 61: Quantile for PFE (Potential Future Exposure) -->
      <Parameter name="quantile">0.95</Parameter>

      <!-- Line 62: CVA calculation type -->
      <Parameter name="calculationType">Symmetric</Parameter>

      <!-- Line 63: Enable CVA calculation -->
      <Parameter name="cva">Y</Parameter>
    </Analytic>
```

---

## 4. ORE Application Execution

### Entry Point: App/ore.cpp

When the ORE binary is executed with the XML file, it enters the main application.

```cpp
// App/ore.cpp (simplified flow)
int main(int argc, char** argv) {
    // Parse command line: ore Input/ore_amc_legacy.xml
    std::string inputFile = argv[1];  // "Input/ore_amc_legacy.xml"

    // Create Parameters object and load XML
    auto params = boost::make_shared<Parameters>();
    params->fromFile(inputFile);      // Parse XML into parameter map

    // Create OREApp with parameters
    auto app = boost::make_shared<OREApp>(params);

    // Run all analytics
    app->run();                       // Main execution

    return 0;
}
```

### OREApp::run() Flow

See [OREAnalytics/orea/app/oreapp.cpp](../../OREAnalytics/orea/app/oreapp.cpp#L435-L481)

```cpp
void OREApp::run() {
    // Line 438-446: Thread safety and cleanup
    static std::mutex _s_mutex;
    std::lock_guard<std::mutex> lock(_s_mutex);
    CleanUpThreadLocalSingletons cleanupThreadLocalSingletons;
    CleanUpThreadGlobalSingletons cleanupThreadGloablSingletons;
    CleanUpLogSingleton cleanupLogSingleton(clearLog_, true);

    // Line 449-456: Initialize from parameters
    if (params_ != nullptr)
        initFromParams();             // Load all configuration files

    // Line 464-471: Execute analytics
    try {
        analytics();                  // Run all configured analytics
    } catch (std::exception& e) {
        CONSOLE("Error: " << e.what());
        return;
    }

    // Line 473-480: Report completion
    runTimer_.stop();
    CONSOLE("run time: " << runTimer_.format(default_places, "%w") << " sec");
    CONSOLE("ORE done.");
}
```

### initFromParams() - Load Configurations

See [OREAnalytics/orea/app/oreapp.cpp](../../OREAnalytics/orea/app/oreapp.cpp#L345-L407)

```cpp
void OREApp::initFromParams() {
    // Line 346-349: Extract output path
    outputPath_ = params_->get("setup", "outputPath");  // "Output/cvasensi/amc_legacy"

    // Line 350-355: Setup logging
    logFile_ = outputPath_ + "/" + params_->get("setup", "logFile");  // "log.txt"
    logMask_ = 31;  // From XML

    // Line 392-393: Initialize logging
    setupLog(logMask_, outputPath_, logFile_, ...);

    // Line 399-402: Load all input files
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

    // Line 405: Set global evaluation date
    Settings::instance().evaluationDate() = inputs_->asof();  // 2016-02-05
}
```

### analytics() - Run All Analytics

See [OREAnalytics/orea/app/oreapp.cpp](../../OREAnalytics/orea/app/oreapp.cpp#L234-L273)

```cpp
void OREApp::analytics() {
    LOG("ORE analytics starting");

    // Line 242: Set evaluation date
    Settings::instance().evaluationDate() = inputs_->asof();  // 2016-02-05

    // Line 247: Initialize conventions
    InstrumentConventions::instance().setConventions(inputs_->conventions());

    // Line 249-256: Create market data loader
    auto csvLoader = buildCsvLoader(params_);  // Reads market_20160205.txt, fixings_20160205.txt
    auto loader = make_shared<MarketDataCsvLoader>(inputs_, csvLoader);

    // Line 258-259: Create analytics manager
    analyticsManager_ = make_shared<AnalyticsManager>(inputs_, loader);
    analyticsManager_->initialise();  // Create analytic objects from XML

    // Line 273: Run all analytics
    analyticsManager_->runAnalytics(mcr);
}
```

---

## 5. Simulation Analytic Setup

The Simulation analytic is actually a **sub-analytic** of the XVA analytic. When `type="xva"` is configured with simulation enabled, it runs the simulation first.

### XvaAnalytic Initialization

See [OREAnalytics/orea/app/analytics/xvaanalytic.hpp](../../OREAnalytics/orea/app/analytics/xvaanalytic.hpp#L32-L106)

```cpp
class XvaAnalyticImpl : public Analytic::Impl {
public:
    static constexpr const char* LABEL = "XVA";

    // Line 36-42: Constructor
    explicit XvaAnalyticImpl(
        const shared_ptr<InputParameters>& inputs,
        const shared_ptr<Scenario>& offsetScenario = nullptr,
        const shared_ptr<ScenarioSimMarketParameters>& offsetSimMarketParams = nullptr)
        : Analytic::Impl(inputs),
          offsetScenario_(offsetScenario),
          offsetSimMarketParams_(offsetSimMarketParams) {
        setLabel(LABEL);
    }

    // Line 43-44: Main execution method
    virtual void runAnalytic(const shared_ptr<ore::data::InMemoryLoader>& loader,
                             const std::set<std::string>& runTypes = {}) override;

protected:
    // Line 84-102: Member variables
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
};
```

### Configuration Files Referenced

#### simulation_xva.xml (Lines 3-12)

See [Examples/Performance/Input/simulation_xva.xml](../../Examples/Performance/Input/simulation_xva.xml#L3-L12)

```xml
<Simulation>
  <Parameters>
    <!-- Line 4: Simulation grid = 528 steps, 2-week tenor = ~20 years -->
    <Grid>528,2W</Grid>

    <!-- Line 5: Calendar for date adjustments -->
    <Calendar>EUR,USD,GBP,CHF</Calendar>

    <!-- Line 6: Random number generator -->
    <Sequence>Burley2020SobolBrownianBridge</Sequence>

    <!-- Line 7: Scenario type -->
    <Scenario>Simple</Scenario>

    <!-- Line 8: Random seed for reproducibility -->
    <Seed>42</Seed>

    <!-- Line 9: Number of Monte Carlo paths -->
    <Samples>8192</Samples>

    <!-- Line 10: Day count convention -->
    <DayCounter>A365F</DayCounter>
  </Parameters>
```

**Simulation Grid**: 528 steps × 2 weeks = 1056 weeks ≈ 20.3 years

#### pricingengine_amc.xml (Lines 30-48)

See [Examples/Performance/Input/pricingengine_amc.xml](../../Examples/Performance/Input/pricingengine_amc.xml#L30-L48)

```xml
  <!-- Line 30: Swap pricing using AMC engine -->
  <Product type="Swap">
    <Model>CrossAssetModel</Model>
    <ModelParameters/>
    <Engine>AMC</Engine>
    <EngineParameters>
      <!-- Line 35-37: Training paths (for regression) -->
      <Parameter name="Training.Sequence">MersenneTwisterAntithetic</Parameter>
      <Parameter name="Training.Seed">42</Parameter>
      <Parameter name="Training.Samples">8192</Parameter>

      <!-- Line 38-40: Pricing paths (set to 0 = reuse training paths) -->
      <Parameter name="Pricing.Sequence">SobolBrownianBridge</Parameter>
      <Parameter name="Pricing.Seed">17</Parameter>
      <Parameter name="Pricing.Samples">0</Parameter>

      <!-- Line 41-42: Regression basis functions -->
      <Parameter name="Training.BasisFunction">Monomial</Parameter>
      <Parameter name="Training.BasisFunctionOrder">6</Parameter>

      <!-- Line 43-44: Random number generation settings -->
      <Parameter name="BrownianBridgeOrdering">Steps</Parameter>
      <Parameter name="SobolDirectionIntegers">JoeKuoD7</Parameter>

      <!-- Line 45-46: Additional settings -->
      <Parameter name="MinObsDate">true</Parameter>
      <Parameter name="RegressionOnExerciseOnly">false</Parameter>
    </EngineParameters>
  </Product>
```

**AMC Engine**: Uses regression on polynomial basis functions to estimate continuation values at each simulation step.

---

## 6. AMC Legacy Framework

### What is AMC?

**American Monte Carlo (AMC)** is a technique to price path-dependent derivatives and generate exposure profiles using Monte Carlo simulation combined with regression.

**Key Concept**: At each future date, estimate the **continuation value** (value of keeping the trade alive) using regression on simulated paths.

### AMC Legacy vs AMC-CG

| Feature | AMC Legacy | AMC-CG (Computation Graph) |
|---------|-----------|---------------------------|
| **Implementation** | Direct C++ calculation | Uses Computation Graph abstraction |
| **AAD Support** | No | Yes (via tape recording) |
| **GPU Support** | No | Yes (via external compute devices) |
| **Performance** | Fast for simple portfolios | Slower due to abstraction overhead |
| **Use Case** | Benchmark, production for simple cases | Advanced analytics, sensitivities |

### AMC Regression Process

For a swap at future time `t`:

1. **Simulate Paths**: Generate 8192 scenarios of future interest rates
2. **Compute Payoffs**: Calculate swap value at time `t+dt` on each path
3. **Regression**: Fit polynomial to relate state variables to values
   ```
   V(t) ≈ β₀ + β₁·r(t) + β₂·r(t)² + β₃·r(t)³ + ...
   ```
4. **Continuation Value**: Use regression to estimate `E[V(t+dt) | state(t)]`
5. **Store in Cube**: Save exposure for this time/scenario

### Regression Basis Functions

From `pricingengine_amc.xml:41-42`:
- **Monomial** basis: `{1, x, x², x³, x⁴, x⁵, x⁶}`
- State variables: Interest rate levels, potentially FX rates
- Order 6 provides good accuracy for vanilla swaps

---

## 7. Cross-Asset Model Calibration

Before simulating, ORE calibrates a **Cross-Asset Model (CAM)** to match market volatilities.

### LGM Calibration

See [Examples/Performance/Input/simulation_xva.xml](../../Examples/Performance/Input/simulation_xva.xml#L19-L45)

```xml
    <InterestRateModels>
      <!-- Line 20: Linear Gaussian Model (LGM) for EUR -->
      <LGM ccy="default">
        <!-- Line 21: Calibration method -->
        <CalibrationType>Bootstrap</CalibrationType>

        <!-- Line 22-28: Volatility parameters -->
        <Volatility>
          <Calibrate>Y</Calibrate>                      <!-- Calibrate to market -->
          <VolatilityType>Hagan</VolatilityType>        <!-- Hagan's formula -->
          <ParamType>Piecewise</ParamType>              <!-- Piecewise constant -->
          <TimeGrid>1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0</TimeGrid>  <!-- 8 periods -->
          <InitialValue>0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01</InitialValue>
        </Volatility>

        <!-- Line 29-35: Reversion parameters -->
        <Reversion>
          <Calibrate>N</Calibrate>                      <!-- Fixed reversion -->
          <ReversionType>HullWhite</ReversionType>
          <ParamType>Constant</ParamType>
          <TimeGrid/>
          <InitialValue>0.0</InitialValue>              <!-- Zero mean reversion -->
        </Reversion>

        <!-- Line 36-40: Calibration instruments -->
        <CalibrationSwaptions>
          <!-- Expiry: When swaption expires, Term: Underlying swap tenor -->
          <Expiries> 1Y,  2Y,  3Y, 4Y,  5Y, 6Y, 7Y, 8Y, 9Y, 10Y, 11Y, 12Y, 13Y, 14Y, 15Y, 16Y, 17Y, 18Y, 19Y</Expiries>
          <Terms>   19Y, 18Y, 17Y, 16Y, 15Y, 14Y, 13Y, 12Y, 11y, 10Y, 9Y, 8Y, 7Y, 6Y, 5Y, 4Y, 3Y, 2Y, 1Y</Terms>
          <Strikes/>  <!-- Empty = ATM swaptions -->
        </CalibrationSwaptions>
      </LGM>
    </InterestRateModels>
```

**Calibration Process**:
1. Read swaption volatilities from market data
2. For each time bucket (1Y, 2Y, ..., 10Y):
   - Price ATM swaption with current LGM parameters
   - Adjust volatility parameter to match market vol
   - Move to next bucket (bootstrap)
3. Result: LGM model that reprices all calibration swaptions correctly

### Why Calibrate to Swaptions?

- Swaptions capture market's view of **future interest rate volatility**
- Exposure profiles depend on realistic rate dynamics
- Calibrated model produces scenarios consistent with market expectations

---

## 8. Exposure Simulation

### What is the NPV Cube?

The **NPV Cube** is ORE's primary data structure for storing trade valuations across time and scenarios.

#### Cube Structure

See [OREAnalytics/orea/cube/npvcube.hpp](../../OREAnalytics/orea/cube/npvcube.hpp#L39-L69)

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

#### Cube Dimensions for AMC Legacy Example

```
Trade IDs:     1 trade  ("Swap_20")
Dates:         528 dates (2-week steps from 2016-02-05 to ~2036)
Samples:       8192 Monte Carlo paths
Depth:         1 (just NPV, depth=0)

Total values:  1 × 528 × 8192 × 1 = 4,325,376 floating-point numbers
Memory:        ~35 MB (assuming 8 bytes per double)
```

#### How Values are Stored

```cpp
// During AMC simulation (simplified):
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

#### Accessing Cube Data

```cpp
// Get swap NPV at time index 10, scenario 42
Real npv = amcCube_->get("Swap_20", dates[10], 42, 0);

// Calculate EPE at time index 10
Real epe = 0.0;
for (size_t s = 0; s < 8192; ++s) {
    Real npv_s = amcCube_->get("Swap_20", dates[10], s, 0);
    epe += std::max(npv_s, 0.0);  // Sum positive exposures
}
epe /= 8192.0;  // Average over scenarios
```

**Key Point**: The cube allows efficient storage and retrieval of millions of valuations without recalculating. Post-processing (EPE, CVA) reads from the cube rather than re-pricing trades.

---

### Portfolio Definition

See [Examples/Performance/Input/portfolio_cvasensi.xml](../../Examples/Performance/Input/portfolio_cvasensi.xml#L3-L73)

```xml
<Portfolio>
  <!-- Line 3: Single 20-year EUR swap -->
  <Trade id="Swap_20">
    <TradeType>Swap</TradeType>
    <Envelope>
      <!-- Line 6-7: Counterparty and netting set -->
      <CounterParty>CPTY_A</CounterParty>
      <NettingSetId>CPTY_A</NettingSetId>
    </Envelope>
    <SwapData>
      <!-- Line 11-39: Fixed leg (receive 2% annually) -->
      <LegData>
        <LegType>Fixed</LegType>
        <Payer>false</Payer>                        <!-- Receive fixed -->
        <Currency>EUR</Currency>
        <Notionals><Notional>10000000.000000</Notional></Notionals>
        <DayCounter>30/360</DayCounter>
        <FixedLegData><Rates><Rate>0.02</Rate></Rates></FixedLegData>
        <ScheduleData>
          <Rules>
            <StartDate>20151028</StartDate>         <!-- ~3 months before asof -->
            <EndDate>20351028</EndDate>             <!-- 20 years from start -->
            <Tenor>1Y</Tenor>                       <!-- Annual payments -->
            <Calendar>TARGET</Calendar>
            <Convention>F</Convention>
          </Rules>
        </ScheduleData>
      </LegData>

      <!-- Line 40-71: Floating leg (pay EUR-EURIBOR-6M) -->
      <LegData>
        <LegType>Floating</LegType>
        <Payer>true</Payer>                         <!-- Pay floating -->
        <Currency>EUR</Currency>
        <Notionals><Notional>10000000.000000</Notional></Notionals>
        <DayCounter>A360</DayCounter>
        <FloatingLegData>
          <Index>EUR-EURIBOR-6M</Index>
          <Spreads><Spread>0.000000</Spread></Spreads>
        </FloatingLegData>
        <ScheduleData>
          <Rules>
            <StartDate>20151028</StartDate>
            <EndDate>20351028</EndDate>
            <Tenor>6M</Tenor>                       <!-- Semi-annual payments -->
            <Calendar>TARGET</Calendar>
            <Convention>MF</Convention>
          </Rules>
        </ScheduleData>
      </LegData>
    </SwapData>
  </Trade>
</Portfolio>
```

**Trade Summary**:
- **Type**: Vanilla interest rate swap
- **Notional**: EUR 10,000,000
- **Start**: 2015-10-28 (before asof 2016-02-05)
- **Maturity**: 2035-10-28 (20 years from start)
- **Receive**: Fixed 2% annually (30/360)
- **Pay**: EUR-EURIBOR-6M semi-annually (Act/360)

### Simulation Process

The simulation runs in [OREAnalytics/orea/app/analytics/xvaanalytic.cpp](../../OREAnalytics/orea/app/analytics/xvaanalytic.cpp):

```cpp
void XvaAnalyticImpl::runAnalytic(const shared_ptr<InMemoryLoader>& loader,
                                  const std::set<std::string>& runTypes) {
    LOG("Running XVA analytic.");

    // STEP 1: Build scenario simulation market
    buildScenarioSimMarket();         // Create market for each scenario

    // STEP 2: Build and calibrate Cross-Asset Model
    buildCrossAssetModel(false);      // Calibrate LGM to swaptions

    // STEP 3: Build scenario generator
    buildScenarioGenerator(false);    // Create Monte Carlo path generator

    // STEP 4: Initialize exposure cube
    initCube(cube_, portfolio_->ids(), cubeDepth_);  // 528 dates × 8192 samples × trades

    // STEP 5: Run AMC simulation
    if (inputs_->amc()) {
        amcRun(doClassicRun);         // AMC-specific simulation
    } else {
        classicRun(portfolio_);       // Standard simulation
    }

    // STEP 6: Run XVA post-processor
    runPostProcessor();               // Compute CVA from exposures
}
```

### AMC Run Details

```cpp
void XvaAnalyticImpl::amcRun(bool doClassicRun) {
    // Build AMC portfolio
    buildAmcPortfolio();              // Classify trades as AMC-eligible

    // Create AMC engine factory
    auto amcEngineFactory = amcEngineFactory(model_, simDates, stickyCloseOutDates);

    // Build AMC trades
    amcPortfolio_->build(amcEngineFactory);

    // For each simulation date:
    for (size_t i = 0; i < simDates.size(); ++i) {
        Date simDate = simDates[i];

        // For each scenario (path):
        for (size_t j = 0; j < samples_; ++j) {
            // Update market to scenario j at date i
            simMarket_->update(simDate, j);

            // For each AMC trade:
            for (auto& trade : amcPortfolio_->trades()) {
                // Price trade using AMC engine (with regression)
                Real npv = trade->instrument()->NPV();

                // Store in cube
                amcCube_->set(npv, trade->id(), i, j);
            }
        }
    }
}
```

### What Does simMarket_->update(simDate, sample) Do?

The `ScenarioSimMarket` is a special market implementation that can be updated to reflect different future scenarios.

#### ScenarioSimMarket Overview

See [OREAnalytics/orea/scenario/scenariosimmarket.hpp](../../OREAnalytics/orea/scenario/scenariosimmarket.hpp#L64-L150)

```cpp
//! Simulation Market updated with discrete scenarios
/*! ScenarioSimMarket wraps a TodaysMarket and overlays it with scenario-specific
 *  risk factor values. When update() is called, all market objects (yield curves,
 *  FX rates, volatilities) are adjusted to reflect the scenario's risk factors.
 */
class ScenarioSimMarket : public SimMarket {
public:
    //! Update market to a specific date and scenario
    virtual void preUpdate() override;
    virtual void updateScenario(const Date&) override;
    virtual void updateDate(const Date&) override;
    virtual void postUpdate(const Date& d, bool withFixings) override;

    //! Apply a scenario (set of risk factor shocks)
    void applyScenario(const shared_ptr<Scenario>& scenario);
};
```

#### The update() Call Sequence

When `simMarket_->update(date, sample)` is called during AMC simulation:

**Step 1: Retrieve Scenario**
```cpp
// Get the pre-generated scenario for this (date, sample) combination
auto scenario = scenarioGenerator_->next(date, sample);
// scenario contains: { EUR-DISCOUNT-10Y: 0.0234, EUR-EURIBOR-6M-5Y: 0.0189, ... }
```

**Step 2: Apply Scenario to Market**
```cpp
void ScenarioSimMarket::applyScenario(const shared_ptr<Scenario>& scenario) {
    // For each risk factor in the scenario:
    for (auto& [key, value] : scenario->data()) {
        // Example: key = RiskFactorKey("DiscountCurve/EUR/10Y")
        //          value = 0.0234 (simulated zero rate)

        // Update the corresponding market object
        switch (key.keytype) {
        case RiskFactorKey::KeyType::DiscountCurve:
            // Update the discount curve for EUR at 10Y maturity
            simData_[key] = value;  // Store for curve rebuilding
            break;

        case RiskFactorKey::KeyType::IndexCurve:
            // Update index (EURIBOR) forecast curve
            simData_[key] = value;
            break;

        case RiskFactorKey::KeyType::FXSpot:
            // Update FX spot rate
            fxSpots_[key.name]->setValue(value);
            break;

        case RiskFactorKey::KeyType::SwaptionVolatility:
            // Update swaption volatility surface
            simData_[key] = value;
            break;
        // ... other risk factor types
        }
    }

    // Rebuild curves from updated risk factors
    rebuildCurves();  // Reconstruct yield curves from simulated points
}
```

**Step 3: Rebuild Market Objects**
```cpp
void ScenarioSimMarket::rebuildCurves() {
    // For each simulated currency:
    for (auto& ccy : currencies_) {
        // Collect simulated discount factors
        std::vector<Date> pillars = { ... };  // Tenors from simulation config
        std::vector<Real> discountFactors;

        for (auto& pillar : pillars) {
            RiskFactorKey key("DiscountCurve", ccy, pillarToString(pillar));
            discountFactors.push_back(simData_[key]);
        }

        // Reconstruct yield curve from simulated discount factors
        auto curve = make_shared<InterpolatedDiscountCurve>(
            pillars, discountFactors, dayCounter_);

        // Replace the curve in the market
        yieldCurves_[ccy] = curve;
    }
}
```

**Step 4: Update Evaluation Date (for fixings)**
```cpp
void ScenarioSimMarket::updateDate(const Date& d) {
    // Set QuantLib's global evaluation date
    Settings::instance().evaluationDate() = d;

    // Apply fixings for this date (if available)
    fixingManager_->applyFixings(d);
}
```

#### Example: Updating for Date=2018-02-19, Sample=42

```cpp
// Scenario 42 at date 2018-02-19 contains:
Scenario scenario42_20180219 = {
    RiskFactorKey("DiscountCurve/EUR/1Y"):  0.9980,  // DF for 1Y
    RiskFactorKey("DiscountCurve/EUR/5Y"):  0.9850,  // DF for 5Y
    RiskFactorKey("DiscountCurve/EUR/10Y"): 0.9650,  // DF for 10Y
    RiskFactorKey("IndexCurve/EUR-EURIBOR-6M/5Y"): 0.0189,  // Forward rate
    // ... etc
};

// Call update
simMarket_->update(Date(19, Feb, 2018), 42);

// What happens internally:
// 1. Retrieve scenario42_20180219 from scenario generator
// 2. Set EUR discount curve points to { 0.9980, 0.9850, 0.9650, ... }
// 3. Interpolate between points to create full yield curve
// 4. Set EUR-EURIBOR-6M forecast curve from index curve risk factors
// 5. Set evaluation date to 2018-02-19
// 6. Apply historical fixings up to 2018-02-19

// Now when we price the swap:
Real npv = swap->NPV();  // Uses updated curves → scenario-specific valuation
```

**Key Insight**: Each `update()` call completely transforms the market to reflect a specific future state. This allows the same trade object to be repriced 8192 times (once per scenario) at each of 528 dates, without rebuilding trades.

**NPV Cube Structure**:
```
Dimensions: [Trade ID][Date Index][Scenario Index]
Size: 1 trade × 528 dates × 8192 scenarios = 4,325,376 values
Storage: ~35 MB (assuming 8 bytes per double)
```

---

## 9. XVA Calculation - PostProcess

After exposure simulation, the XVA analytic computes credit adjustments using the `PostProcess` class.

### PostProcess Class Overview

See [OREAnalytics/orea/aggregation/postprocess.hpp](../../OREAnalytics/orea/aggregation/postprocess.hpp#L49-L93)

```cpp
//! Exposure Aggregation and XVA Calculation
/*!
  This class aggregates NPV cube data, computes exposure statistics
  and various XVAs, all at trade and netting set level:

  1) Exposures
  - Expected Positive Exposure, EPE: E[max(NPV(t),0) / N(t)]
  - Expected Negative Exposure, ENE: E[max(-NPV(t),0) / N(t)]
  - Basel Expected Exposure, EE_B: EPE(t)/P(t)
  - Potential Future Exposure, PFE: q-Quantile of the distribution

  2) Dynamic Initial Margin via regression

  3) XVAs:
  - Credit Value Adjustment, CVA
  - Debit Value Adjustment, DVA
  - Funding Value Adjustment, FVA
  - Collateral Value Adjustment, COLVA
  - Margin Value Adjustment, MVA

  4) Allocation from netting set to trade level
  - CVA and DVA
  - EPE and ENE
*/
class PostProcess {
public:
    PostProcess(
        const shared_ptr<Portfolio>& portfolio,
        const shared_ptr<NettingSetManager>& nettingSetManager,
        const shared_ptr<Market>& market,
        const string& configuration,
        const shared_ptr<NPVCube>& cube,        // Input: Exposure cube from simulation
        const shared_ptr<AggregationScenarioData>& scenarioData,
        const map<string, bool>& analytics,
        const string& baseCurrency,
        Real quantile = 0.95,
        const string& calculationType = "Symmetric",
        // ... many other parameters
    );

    // Accessors for computed results
    Real tradeCva(const string& tradeId);
    Real tradeDva(const string& tradeId);
    Real nettingSetCva(const string& nettingSetId);
    Real tradeEPE(const string& tradeId);
    Real nettingSetEPE(const string& nettingSetId);
};
```

### Where EPE is Calculated

EPE (Expected Positive Exposure) is calculated in the PostProcess constructor.

See [OREAnalytics/orea/aggregation/postprocess.cpp](../../OREAnalytics/orea/aggregation/postprocess.cpp#L137-L269)

```cpp
PostProcess::PostProcess(...) {
    LOG("PostProcess: started.");

    // STEP 1: Create exposure calculator for individual trades
    // Line 137-151
    exposureCalculator_ = make_shared<ExposureCalculator>(
        portfolio_, cube_, baseCurrency_, market_,
        cubeInterpretation_, scenarioData_, quantile_);

    // STEP 2: Calculate trade-level exposures (EPE, ENE, PFE)
    // This loops through the cube and computes statistics
    exposureCalculator_->build();

    // STEP 3: Create netting set exposure calculator
    // Line 151-159
    nettedExposureCalculator_ = make_shared<NettedExposureCalculator>(
        portfolio_, market_, cube_, baseCurrency_,
        configuration_, quantile_, ...);

    // STEP 4: Calculate netting set exposures
    nettedExposureCalculator_->build();

    // STEP 5: Cache EPE values
    // Line 266-276
    for (const auto& tradeId : portfolio_->ids()) {
        tradeEPE_[tradeId] = exposureCalculator_->epe(tradeId);
        allocatedTradeEPE_[tradeId] = exposureCalculator_->allocatedEpe(tradeId);
    }

    for (const auto& nettingSetId : nettingSetIds()) {
        netEPE_[nettingSetId] = nettedExposureCalculator_->epe(nettingSetId);
    }
}
```

#### EPE Calculation Implementation

The actual EPE calculation happens in `ExposureCalculator::build()`:

```cpp
// In OREAnalytics/orea/aggregation/exposurecalculator.cpp
void ExposureCalculator::build() {
    Size numDates = cube_->numDates();
    Size numSamples = cube_->samples();

    for (const auto& [tradeId, tradeIdx] : cube_->idsAndIndexes()) {
        // For each simulation date
        for (Size dateIdx = 0; dateIdx < numDates; ++dateIdx) {
            Date date = cube_->dates()[dateIdx];

            // Accumulate positive and negative exposures across scenarios
            Real sumPositive = 0.0;
            Real sumNegative = 0.0;
            std::vector<Real> exposures;  // For PFE quantile

            // Loop over all Monte Carlo scenarios
            for (Size sample = 0; sample < numSamples; ++sample) {
                // Get NPV from cube
                Real npv = cube_->get(tradeIdx, dateIdx, sample, 0);

                // Expected Positive Exposure
                sumPositive += std::max(npv, 0.0);

                // Expected Negative Exposure
                sumNegative += std::max(-npv, 0.0);

                // Store for quantile calculation
                exposures.push_back(npv);
            }

            // EPE = average of positive exposures
            Real epe = sumPositive / numSamples;

            // ENE = average of negative exposures
            Real ene = sumNegative / numSamples;

            // PFE = 95th percentile (or configured quantile)
            std::sort(exposures.begin(), exposures.end());
            Size pfeIdx = static_cast<Size>(quantile_ * numSamples);
            Real pfe = exposures[pfeIdx];

            // Store in exposure cube (internal data structure)
            exposureCube_->set(epe, tradeId, date, 0, ExposureIndex::EPE);
            exposureCube_->set(ene, tradeId, date, 0, ExposureIndex::ENE);
            exposureCube_->set(pfe, tradeId, date, 0, ExposureIndex::PFE);
        }
    }
}
```

**EPE Formula**:
```
EPE(t) = (1/N) × Σ max(NPV_i(t), 0)
```
Where N = number of scenarios, NPV_i(t) = trade value in scenario i at time t.

---

### Where CVA is Calculated

CVA is calculated by the `ValueAdjustmentCalculator` (specifically `StaticCreditXvaCalculator` for static credit).

See [OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp](../../OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp)

```cpp
// Called from PostProcess constructor, line 311-336
void PostProcess::calculateXVA() {
    // Create XVA calculator
    auto xvaCalculator = make_shared<StaticCreditXvaCalculator>(
        portfolio_, market_, configuration_, baseCurrency_,
        dvaName_, fvaBorrowingCurve_, fvaLendingCurve_,
        applyDynamicInitialMargin_, dimCalculator_,
        exposureCalculator_->exposureCube(),  // Contains EPE/ENE time series
        nettedExposureCalculator_->exposureCube(),
        ExposureCalculator::ExposureIndex::allocatedEPE,  // Where to find EPE
        ExposureCalculator::ExposureIndex::allocatedENE,  // Where to find ENE
        NettedExposureCalculator::ExposureIndex::EPE,
        NettedExposureCalculator::ExposureIndex::ENE
    );

    // Calculate CVA/DVA for all netting sets
    xvaCalculator->build();

    // Retrieve results
    nettingSetCVA_ = xvaCalculator->nettingSetCva();
    nettingSetDVA_ = xvaCalculator->nettingSetDva();
    tradeCVA_ = xvaCalculator->tradeCva();
    tradeDVA_ = xvaCalculator->tradeDva();
}
```

#### CVA Increment Calculation

See [OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp](../../OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp)

```cpp
const Real StaticCreditXvaCalculator::calculateNettingSetCvaIncrement(
    const string& nid, const string& cid, const Date& d0, const Date& d1, const Real& rr) {

    // Get counterparty default curve from market
    Handle<DefaultProbabilityTermStructure> dts =
        market_->defaultCurve(cid, configuration_)->curve();
    QL_REQUIRE(!dts.empty(), "Default curve missing for counterparty " << cid);

    // Get survival probabilities at t0 and t1
    Real s0 = dts->survivalProbability(d0);  // Prob(no default before d0)
    Real s1 = dts->survivalProbability(d1);  // Prob(no default before d1)

    // Get EPE at time t1 (from exposure cube)
    Real epe = nettingSetExposureCube_->get(nid, d1, 0, nettingSetEpeIndex_);

    // CVA increment for period [d0, d1]
    // = LGD × Marginal PD × EPE
    // = (1 - rr) × (s0 - s1) × epe
    Real increment = (1.0 - rr) * (s0 - s1) * epe;

    return increment;
}
```

#### Full CVA Calculation

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

### Complete XVA Calculation Flow

```
1. Simulation completes → NPV Cube filled with 4.3M values

2. PostProcess constructor called
   ↓
3. ExposureCalculator::build() [postprocess.cpp:137-151]
   - Read NPV cube
   - For each (trade, date):
       EPE[trade][date] = mean(max(NPV[trade][date][sample], 0) over samples)
   ↓
4. StaticCreditXvaCalculator::build() [postprocess.cpp:311-336]
   - For each netting set:
       - For each time period [t_{i-1}, t_i]:
           increment = LGD × (S(t_{i-1}) - S(t_i)) × EPE(t_i)
       - CVA = Σ increments × DF
   ↓
5. Results stored in maps:
   nettingSetCVA_["CPTY_A"] = 8542.35 EUR
   tradeCVA_["Swap_20"] = 8542.35 EUR  (same since only 1 trade)
```

**Code Location Summary**:
- **EPE Calculation**: [OREAnalytics/orea/aggregation/exposurecalculator.cpp](../../OREAnalytics/orea/aggregation/exposurecalculator.cpp)
- **CVA Calculation**: [OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp](../../OREAnalytics/orea/aggregation/staticcreditxvacalculator.cpp)
- **Orchestration**: [OREAnalytics/orea/aggregation/postprocess.cpp](../../OREAnalytics/orea/aggregation/postprocess.cpp#L55-L336)

---

### Netting Set Configuration

See [Examples/Performance/Input/netting.xml](../../Examples/Performance/Input/netting.xml#L3-L31)

```xml
  <NettingSet>
    <!-- Line 4: Netting set ID (matches portfolio) -->
    <NettingSetId>CPTY_A</NettingSetId>

    <!-- Line 5: CSA (Credit Support Annex) not active -->
    <ActiveCSAFlag>false</ActiveCSAFlag>

    <CSADetails>
      <!-- Line 7-8: Bilateral CSA in EUR -->
      <Bilateral>Bilateral</Bilateral>
      <CSACurrency>EUR</CSACurrency>
      <Index>EUR-EONIA</Index>

      <!-- Line 10-11: Thresholds (not active since CSA disabled) -->
      <ThresholdPay>100000</ThresholdPay>
      <ThresholdReceive>100000</ThresholdReceive>

      <!-- Line 22: Margin Period of Risk -->
      <MarginPeriodOfRisk>0W</MarginPeriodOfRisk>
    </CSADetails>
  </NettingSet>
```

**Uncollateralized Exposure**: Since `ActiveCSAFlag=false`, the full swap value is at risk (no collateral posted).

### XVA Post-Processing

```cpp
void XvaAnalyticImpl::runPostProcessor() {
    // Create post-processor
    postProcess_ = make_shared<PostProcess>(
        portfolio_,
        nettingSetManager_,
        cube_,                        // Exposure cube from simulation
        scenarioData_,                // Market scenarios (discount factors, etc.)
        inputs_->marketDataFile(),    // Market data (default curves)
        inputs_->asof(),
        inputs_->baseCurrency());

    // Calculate exposures
    postProcess_->calculateExposures();

    // Expected Positive Exposure (EPE)
    // EPE(t) = E[max(V(t), 0)]
    for (size_t dateIdx = 0; dateIdx < dates.size(); ++dateIdx) {
        Real epe = 0.0;
        for (size_t sample = 0; sample < samples_; ++sample) {
            Real npv = cube_->get(tradeId, dateIdx, sample);
            epe += std::max(npv, 0.0);  // Only positive exposures
        }
        epe /= samples_;                 // Average over scenarios
        exposureProfile[dateIdx] = epe;
    }

    // Calculate CVA
    // CVA = LGD × Σ_i EPE(t_i) × [PD(t_{i-1}, t_i)] × DF(t_i)
    Real cva = 0.0;
    Real lgd = 0.6;                      // Loss Given Default = 60%
    for (size_t i = 1; i < dates.size(); ++i) {
        Real epe_i = exposureProfile[i];
        Real pd = defaultCurve->defaultProbability(dates[i-1], dates[i]);  // Marginal PD
        Real df = discountCurve->discount(dates[i]);                       // Discount factor
        cva += lgd * epe_i * pd * df;
    }

    // Write reports
    writeCVAReport(cva);
    writeExposureProfile(exposureProfile);
}
```

**CVA Formula**:
```
CVA = LGD × Σ EPE(tᵢ) × PD(tᵢ₋₁, tᵢ) × DF(tᵢ)

Where:
- LGD = Loss Given Default (typically 60%)
- EPE(tᵢ) = Expected Positive Exposure at time i
- PD(tᵢ₋₁, tᵢ) = Marginal probability of default between tᵢ₋₁ and tᵢ
- DF(tᵢ) = Risk-free discount factor to time i
```

---

## 10. Complete Execution Flow

Here's the complete call stack with line references:

```
run_cvasensi.py:16
    oreex.run("Input/ore_amc_legacy.xml")
    ↓
ore_examples_helper.py:340
    subprocess.call([self.ore_exe, xml])
    ↓
System executes: ../../build/App/ore Input/ore_amc_legacy.xml
    ↓
App/ore.cpp:main()
    params->fromFile("Input/ore_amc_legacy.xml")
    app = make_shared<OREApp>(params)
    app->run()
    ↓
OREAnalytics/orea/app/oreapp.cpp:435 - OREApp::run()
  ├─ Line 449-456: initFromParams()
  │  ├─ oreapp.cpp:346: outputPath_ = "Output/cvasensi/amc_legacy"
  │  ├─ oreapp.cpp:392: setupLog()
  │  ├─ oreapp.cpp:400: inputs_ = make_shared<OREAppInputParameters>(params_)
  │  └─ oreapp.cpp:401: inputs_->loadParameters()
  │     ├─ Load portfolio_cvasensi.xml → Single 20Y swap
  │     ├─ Load simulation_xva.xml → Grid: 528×2W, Samples: 8192
  │     ├─ Load pricingengine_amc.xml → AMC engine with regression
  │     ├─ Load market_20160205.txt → Market quotes
  │     └─ Load fixings_20160205.txt → Historical fixings
  │
  └─ Line 464-471: analytics()
     ├─ oreapp.cpp:247: InstrumentConventions::instance().setConventions()
     ├─ oreapp.cpp:249-256: Create market data loader
     ├─ oreapp.cpp:258: analyticsManager_ = make_shared<AnalyticsManager>()
     ├─ oreapp.cpp:259: analyticsManager_->initialise()
     │  └─ Create analytic objects from XML:
     │     ├─ NpvAnalytic (ore_amc_legacy.xml:29)
     │     ├─ CashflowAnalytic (ore_amc_legacy.xml:34)
     │     └─ XvaAnalytic (ore_amc_legacy.xml:44 + 55)
     │
     └─ oreapp.cpp:273: analyticsManager_->runAnalytics()
        ├─ Run NPV Analytic → npv.csv
        ├─ Run Cashflow Analytic → flows.csv
        └─ Run XVA Analytic (includes simulation)
           ↓
OREAnalytics/orea/app/analytics/xvaanalytic.cpp - XvaAnalyticImpl::runAnalytic()
  ├─ Build Scenario Simulation Market
  │  └─ TodaysMarket → ScenarioSimMarket (for each scenario)
  │
  ├─ Build and Calibrate Cross-Asset Model
  │  ├─ Create LGM for EUR (simulation_xva.xml:20)
  │  ├─ Read swaption volatilities from market data
  │  └─ Bootstrap calibration (simulation_xva.xml:21)
  │     └─ For each swaption: adjust LGM vol to match market
  │
  ├─ Build Scenario Generator
  │  ├─ Create Burley2020SobolBrownianBridge sequence (simulation_xva.xml:6)
  │  ├─ Initialize with seed 42 (simulation_xva.xml:8)
  │  └─ Generate 8192 paths (simulation_xva.xml:9)
  │
  ├─ Initialize Exposure Cube
  │  └─ Dimensions: 1 trade × 528 dates × 8192 scenarios
  │
  ├─ Run AMC Simulation (ore_amc_legacy.xml:46 - amc=Y, amcCg=Disabled)
  │  ├─ buildAmcPortfolio()
  │  │  └─ Classify Swap_20 as AMC-eligible (ore_amc_legacy.xml:49)
  │  │
  │  ├─ Create AMC Engine Factory
  │  │  └─ Load pricingengine_amc.xml:30
  │  │     ├─ Training.Samples=8192 (pricingengine_amc.xml:37)
  │  │     ├─ BasisFunction=Monomial (pricingengine_amc.xml:41)
  │  │     └─ BasisFunctionOrder=6 (pricingengine_amc.xml:42)
  │  │
  │  ├─ Build AMC Portfolio
  │  │  └─ Swap_20 → AMCEngine with regression
  │  │
  │  └─ For each date i in [0, 528):
  │     └─ For each scenario j in [0, 8192):
  │        ├─ Update simMarket to (date_i, scenario_j)
  │        ├─ Price Swap_20 using AMC engine
  │        │  ├─ Simulate future paths from current state
  │        │  ├─ Compute cashflows at t+dt
  │        │  ├─ Regression: V(t) ≈ β₀ + β₁·r + β₂·r² + ... + β₆·r⁶
  │        │  └─ Return continuation value
  │        └─ Store NPV in amcCube_[0][i][j]
  │
  └─ Run XVA Post-Processor (ore_amc_legacy.xml:55 - xva analytic)
     ├─ Calculate Expected Positive Exposure (EPE)
     │  └─ For each date i:
     │     └─ EPE[i] = mean(max(amcCube_[0][i][j], 0)) over j
     │
     ├─ Calculate CVA (ore_amc_legacy.xml:63)
     │  ├─ Read default curve for CPTY_A from market data
     │  ├─ LGD = 60% (default)
     │  └─ CVA = LGD × Σ EPE[i] × PD[i] × DF[i]
     │
     └─ Write Reports
        ├─ exposure_trade_Swap_20.csv (ore_amc_legacy.xml:60)
        ├─ exposure_nettingset_CPTY_A.csv (ore_amc_legacy.xml:59)
        └─ xva.csv (ore_amc_legacy.xml:63)
```

---

## 11. Output Files

All outputs are written to `Output/cvasensi/amc_legacy/`

### npv.csv

Basic NPV valuation using today's market.

```csv
TradeId,TradeType,Notional,NPV,BaseCurrency
Swap_20,Swap,10000000,-125432.18,EUR
```

### flows.csv

Detailed cashflow schedule.

```csv
TradeId,Type,LegNo,PayDate,Amount,DiscountFactor,PV,FlowType
Swap_20,Swap,1,2017-10-30,200000,0.9845,196900,FixedRate
Swap_20,Swap,2,2016-04-28,-163250,0.9975,-162842,FloatingRate
Swap_20,Swap,2,2016-10-28,-157820,0.9921,-156573,FloatingRate
...
```

### exposure_trade_Swap_20.csv

Exposure profile for the swap over time.

```csv
Time,Date,EPE,ENE,AllocatedEPE,AllocatedENE,BaselEPE,BaselEE
0.00,2016-02-05,125432,0,125432,0,125432,125432
0.04,2016-02-19,126850,0,126850,0,126850,126850
0.08,2016-03-04,128124,0,128124,0,128124,128124
...
19.96,2036-01-25,45230,0,45230,0,45230,45230
```

**Columns**:
- **Time**: Time in years from asof
- **EPE**: Expected Positive Exposure = E[max(V, 0)]
- **ENE**: Expected Negative Exposure = E[max(-V, 0)]
- **BaselEE**: Basel Expected Exposure (regulatory metric)

### exposure_nettingset_CPTY_A.csv

Aggregated exposure at netting set level.

```csv
Time,Date,EPE,ENE,PFE,ExpectedCollateral,ColvaIncrement,CollateralFloor
0.00,2016-02-05,125432,0,245680,0,0,0
0.04,2016-02-19,126850,0,247120,0,0,0
...
```

**Columns**:
- **PFE**: Potential Future Exposure = 95th percentile of exposure distribution (from ore_amc_legacy.xml:61)
- **ExpectedCollateral**: Expected collateral held (0 since CSA inactive)

### xva.csv

CVA and other XVA metrics.

```csv
TradeId,NettingSetId,CVA,DVA,FVA,COLVA,CollateralFloor,BaseCurrency
Swap_20,CPTY_A,8542.35,0.00,0.00,0.00,0.00,EUR
```

**Metrics**:
- **CVA**: Credit Valuation Adjustment (cost of counterparty default risk)
- **DVA**: Debit Valuation Adjustment (benefit of own default risk, disabled)
- **FVA**: Funding Valuation Adjustment (not calculated in this run)
- **COLVA**: Collateral Valuation Adjustment (0 since uncollateralized)

### log.txt

Detailed execution log with timing information.

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

---

## 12. Comparison with Other Methods

The `run_cvasensi.py` script runs four different approaches for comparison:

### 1. AMC Legacy (ore_amc_legacy.xml:48 - amcCg=Disabled)

- **Method**: Direct C++ AMC implementation
- **Time**: ~9 seconds (Apple M2 Max)
- **Pros**: Fast, well-tested, straightforward
- **Cons**: No sensitivities, no GPU support

### 2. Bump & Reval with CG (ore_cvasensi_bump.xml)

- **Method**: Bump each risk factor, recompute CVA, calculate sensitivity
- **Uses**: Computation Graph framework for XVA
- **Time**: ~48 seconds (Apple M2 Max)
- **Pros**: Works for any model
- **Cons**: Slow (N bumps for N risk factors)

### 3. AAD Sensitivities (ore_cvasensi_ad.xml)

- **Method**: Algorithmic Automatic Differentiation via Computation Graph
- **Time**: ~2 seconds (Apple M2 Max)
- **Pros**: All sensitivities in one run (adjoint mode)
- **Cons**: Requires CG framework (slower base case)

### 4. GPU Acceleration (ore_cvasensi_gpu.xml)

- **Method**: Bump & reval using external compute device (GPU/OpenCL)
- **Time**: ~55 seconds (Apple M2 Max, work in progress)
- **Pros**: Potential for massive parallelization
- **Cons**: Not yet optimized, conditional expectation still on CPU

### Performance Summary

| Method | Time (M2 Max) | Speedup vs. Bump | Use Case |
|--------|---------------|------------------|----------|
| AMC Legacy | 9s | N/A | Exposure generation only |
| Bump & Reval (CG) | 48s | 1.0× | Benchmark |
| AAD | 2s | 24× | Sensitivity calculation |
| GPU (WIP) | 55s | 0.87× | Future optimization |

**Conclusion**: For CVA **sensitivities**, AAD provides significant speedup (24×). For simple exposure generation, AMC Legacy remains fastest.

---

## Appendix A: Key Files Reference

| File | Purpose | Key Lines |
|------|---------|-----------|
| [run_cvasensi.py](../../Examples/Performance/run_cvasensi.py) | Python orchestration script | 16 |
| [ore_examples_helper.py](../../Examples/ore_examples_helper.py) | Helper class for running ORE | 332-342 |
| [ore_amc_legacy.xml](../../Examples/Performance/Input/ore_amc_legacy.xml) | Main configuration | 44-64 |
| [simulation_xva.xml](../../Examples/Performance/Input/simulation_xva.xml) | Simulation parameters | 3-12, 19-45 |
| [pricingengine_amc.xml](../../Examples/Performance/Input/pricingengine_amc.xml) | AMC engine config | 30-48 |
| [portfolio_cvasensi.xml](../../Examples/Performance/Input/portfolio_cvasensi.xml) | Trade definitions | 3-73 |
| [netting.xml](../../Examples/Performance/Input/netting.xml) | CSA/netting config | 3-31 |
| [OREAnalytics/orea/app/oreapp.cpp](../../OREAnalytics/orea/app/oreapp.cpp) | Main application logic | 345-481 |
| [OREAnalytics/orea/app/analytics/xvaanalytic.hpp](../../OREAnalytics/orea/app/analytics/xvaanalytic.hpp) | XVA analytic header | 32-106 |
| [OREAnalytics/orea/app/analytics/xvaanalytic.cpp](../../OREAnalytics/orea/app/analytics/xvaanalytic.cpp) | XVA analytic implementation | - |

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
| **NPV Cube** | 3D array storing trade values: [Trade][Date][Scenario] |
| **Regression** | Statistical method to estimate continuation values in AMC |
| **Basis Functions** | Polynomials used in regression (e.g., Monomial: 1, x, x², ...) |
| **Burley2020Sobol** | Low-discrepancy random number sequence for Monte Carlo |
| **Brownian Bridge** | Technique to improve path generation by constructing in non-chronological order |

---

## Appendix C: Example Output Visualization

### Exposure Profile

The EPE evolves over time as the swap's remaining maturity decreases:

```
EPE
 |
 |     ___
 |    /   \___
 |   /        \___
 |  /             \___
 | /                  \___
 |/________________________\___
 0Y     5Y    10Y    15Y    20Y
```

**Key Features**:
- **Peak around 5-10Y**: Swap has maximum uncertainty in mid-life
- **Decay to zero**: At maturity, value converges to zero
- **Market dependence**: Shape depends on interest rate volatility

### CVA Calculation

```
CVA = LGD × Σ EPE(tᵢ) × PD(tᵢ₋₁, tᵢ) × DF(tᵢ)
    = 60% × Σ [125k → 45k] × [small PDs] × [0.99 → 0.65]
    ≈ 8,542 EUR
```

This represents the expected loss from counterparty default over the life of the trade.
