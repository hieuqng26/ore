# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## About ORE

ORE (Open Source Risk Engine) is a C++ quantitative finance library for pricing, risk analytics, and XVA calculations. Built on QuantLib, ORE extends it with simulation models, financial instruments, and risk analytics capabilities. The project is sponsored by Acadia Inc. and released under the Modified BSD License.

## Build System

ORE uses CMake 3.15+ as its build system. The project is organized as a monorepo with multiple components.

### Quick Build Commands

```bash
# Basic build
mkdir -p build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
ninja

# Run all tests
ctest -j $(sysctl -n hw.ncpu)

# Run specific test suite
./QuantLib/test-suite/quantlib-test-suite
./QuantExt/test/quantext-test-suite
./OREData/test/ored-test-suite
./OREAnalytics/test/orea-test-suite
```

### Build Options

Key CMake options (defined in root [CMakeLists.txt](CMakeLists.txt:7-18)):
- `ORE_BUILD_TESTS=ON/OFF` - Build test suites (default: ON)
- `ORE_BUILD_EXAMPLES=ON/OFF` - Build examples (default: ON)
- `ORE_BUILD_APP=ON/OFF` - Build ORE application (default: ON)
- `ORE_BUILD_SWIG=ON/OFF` - Build Python bindings (default: ON)
- `ORE_BUILD_DOC=ON/OFF` - Build documentation (default: ON)
- `CMAKE_BUILD_TYPE` - Debug, Release, or RelWithDebInfo

### Architecture-Specific Builds

For Apple Silicon (M1/M2/M3):
```bash
cmake .. -G Ninja -DCMAKE_OSX_ARCHITECTURES=arm64 \
  -DBoost_INCLUDE_DIR=/usr/local/include \
  -DBoost_LIBRARY_DIR=/usr/local/lib
```

## Project Structure

The repository is organized into distinct layers:

```
ORE/
├── QuantLib/          # Core quantitative finance library (submodule)
├── QuantExt/          # QuantLib extensions (qle/)
├── OREData/           # Data layer - XML/CSV parsing, trade builders (ored/)
├── OREAnalytics/      # Analytics layer - pricing, risk, XVA (orea/)
├── App/               # Command-line application (ore executable)
├── ORE-SWIG/          # Python bindings via SWIG
├── Examples/          # Organized by topic (see Examples/Readme.md)
├── Docs/              # User guide, methodology, product documentation
└── Tools/             # Python utilities and Docker files
```

### Key Architectural Layers

1. **QuantLib** - Foundation library providing:
   - Yield curve bootstrapping
   - Option pricing models (Black-Scholes, Heston, etc.)
   - Interest rate models (Hull-White, LGM)
   - Numerical methods (Monte Carlo, finite differences)

2. **QuantExt** - Extensions to QuantLib:
   - Cross-asset models (CAM)
   - Additional pricing engines
   - Extended term structures

3. **OREData** - Data abstraction layer:
   - XML trade parsing (portfolio.xml)
   - Market data loading (CSV, binary)
   - Trade builders (convert XML to QuantLib instruments)
   - Configuration management (conventions, curve configs)

4. **OREAnalytics** - Risk analytics:
   - NPV, cashflow, and sensitivity calculations
   - Exposure simulation (Monte Carlo)
   - XVA calculations (CVA, DVA, FVA, KVA, MVA)
   - SIMM, SA-CCR, BA-CVA, SA-CVA analytics
   - AMC (American Monte Carlo) framework with AAD support

## Core Design Patterns

### Factory Pattern for Analytics

ORE uses factories extensively. Analytics are registered via `AnalyticFactory` and instantiated based on XML configuration:

```cpp
// Analytics are created from ore.xml <Analytic type="..."> tags
auto analytic = AnalyticFactory::instance().build(type, inputs, manager);
```

Common analytic types:
- `npv` - Basic valuation
- `cashflow` - Cashflow schedules
- `sensitivity` - Greeks/sensitivities
- `stress` - Stress testing
- `xva` - CVA/DVA/FVA calculations
- `xvaExplain` - XVA attribution by risk factor
- `simm` - SIMM initial margin
- `saccr` - SA-CCR exposure

### XML-Driven Configuration

ORE separates configuration (XML) from computation (C++):

1. Main configuration file (e.g., `ore.xml`) specifies:
   - Asset date, input/output paths
   - Market data files
   - Portfolio file
   - Analytics to run

2. Supporting configuration files:
   - `curveconfig.xml` - Yield curve specifications
   - `todaysmarket.xml` - Market object configuration
   - `pricingengine.xml` - Pricing engine selection
   - `conventions.xml` - Day count, calendars, etc.
   - `simulation.xml` - Simulation parameters

3. Data files:
   - `portfolio.xml` - Trade definitions
   - `marketdata.csv` - Market quotes
   - `fixings.csv` - Historical fixings

### Trade Building Flow

```
XML Trade Definition (portfolio.xml)
    ↓
Trade::fromXML() - Parse XML into C++ trade object
    ↓
Trade::build(engineFactory) - Build QuantLib instrument
    ↓
EngineFactory - Select appropriate pricing engine
    ↓
QuantLib::Instrument - Final priceable instrument
```

## Running ORE

### Command-line Application

The `ore` executable (built in [App/](App/)) runs analytics based on XML configuration:

```bash
# From build directory
./App/ore /path/to/ore.xml

# From example directory
cd Examples/MinimalSetup
../../build/App/ore Input/ore.xml
```

### Python Integration

ORE provides Python bindings via SWIG (ORE-SWIG module):

```python
import ORE

# Load configuration
params = ORE.Parameters()
params.fromFile("Input/ore.xml")

# Run analytics
app = ORE.OREApp(params, True)
app.run()
```

Example notebooks: [Examples/ORE-Python/](Examples/ORE-Python/)

## Testing

ORE has comprehensive test suites using Boost.Test framework.

### Running Tests

```bash
# All tests via CTest
cd build
ctest -j $(sysctl -n hw.ncpu)

# Individual test suites
./QuantLib/test-suite/quantlib-test-suite
./QuantExt/test/quantext-test-suite
./OREData/test/ored-test-suite
./OREAnalytics/test/orea-test-suite

# Run specific test case
./OREData/test/ored-test-suite --run_test=SwapTest

# Verbose output
./OREData/test/ored-test-suite --log_level=all
```

### Example Tests

Examples have their own test suite:
```bash
cd Examples
python3 run_examples_testsuite.py
```

## Development Workflow

### Adding a New Trade Type

1. Define trade XML schema in `OREData/ored/portfolio/`
2. Create trade builder class inheriting from `Trade`
3. Implement `fromXML()` and `build()` methods
4. Register in trade factory
5. Add pricing engine configuration
6. Create unit tests in `OREData/test/`
7. Add example in `Examples/Products/`

### Adding a New Analytic

1. Create analytic implementation in `OREAnalytics/orea/app/analytics/`
2. Inherit from `Analytic::Impl`
3. Implement `runAnalytic()` method
4. Register in `AnalyticFactory`
5. Add configuration parsing
6. Create example demonstrating usage

### Market Data Flow

```
CSV/Binary Files → Loader (CSVLoader/BinaryLoader)
    ↓
MarketDataLoader - Organize quotes by date/type
    ↓
TodaysMarket - Build curves, surfaces, FX spots
    ↓
EngineFactory - Provide market to pricing engines
    ↓
Trade::instrument()->NPV() - Calculate values
```

### XVA Calculation Architecture

XVA analytics use a multi-step process:

1. **Market Building**: Construct yield curves, vol surfaces, credit curves
2. **Portfolio Building**: Parse trades and attach pricing engines
3. **Exposure Simulation**: Monte Carlo simulation of future portfolio values
4. **Counterparty Default Modeling**: Build default probabilities
5. **XVA Calculation**: CVA = LGD × Σ EE(t) × PD(t) × DF(t)

See [Docs/markdown/ORE Execution Flow.md](Docs/markdown/ORE Execution Flow.md) for detailed XVA Explain flow.

## Important Implementation Details

### Thread Safety

ORE uses QuantLib's singleton pattern extensively. When running in multithreaded contexts:
- Each thread should have its own evaluation date via `Settings::instance().evaluationDate()`
- Market objects are generally NOT thread-safe
- Use proper cleanup with `CleanUpThreadLocalSingletons` and `CleanUpThreadGlobalSingletons`

### Memory Management

- ORE uses `shared_ptr` extensively for memory management
- Large reports can be optionally cached to disk to reduce memory footprint
- The exposure cube can be serialized/deserialized for AMC calculations

### AAD (Algorithmic Automatic Differentiation)

Recent versions support AAD for efficient XVA sensitivities:
- AMC framework supports AAD-based XVA sensitivities
- Used for dynamic SIMM calculations
- Requires specific model configurations

## Common Operations

### Building Curves

Curves are bootstrapped from market instruments (deposits, FRAs, futures, swaps):

```cpp
// Configured via curveconfig.xml
// Built by TodaysMarket from market data
auto discountCurve = market->discountCurve("EUR");
auto indexCurve = market->iborIndex("EUR-EURIBOR-6M")->forwardingTermStructure();
```

### Pricing a Trade

```cpp
// Build trade from XML
auto trade = Trade::fromXML(tradeNode);

// Build QuantLib instrument with market and engines
auto engineFactory = make_shared<EngineFactory>(engineData, market, ...);
trade->build(engineFactory);

// Get NPV
Real npv = trade->instrument()->NPV();
```

### Sensitivity Calculations

Sensitivity analytics compute Greeks via bump-and-revalue:
1. Compute base NPV
2. For each risk factor:
   - Shift the risk factor
   - Rebuild market
   - Recompute NPV
   - Calculate sensitivity = (NPV_shifted - NPV_base) / shift

## Dependencies

Required:
- CMake 3.15+
- C++17 compiler (Clang/GCC/MSVC)
- Boost 1.58+ (date_time, serialization, filesystem, timer, unit_test_framework)

Optional:
- SWIG 4.0+ (for Python bindings)
- Python 3.7+ (for Python integration)
- Eigen3 3.3+ (for optimized linear algebra)
- zlib (for compression support)
- Ninja (for faster builds - recommended)

Install on macOS:
```bash
brew install cmake boost ninja swig python3
```

See [INSTALL_MACOS.md](INSTALL_MACOS.md) for detailed installation instructions.

## Code Organization Conventions

- **Headers**: `.hpp` extension
- **Implementation**: `.cpp` extension
- **Namespaces**: `ore::data`, `ore::analytics`, `QuantExt`
- **Include guards**: Use `#pragma once` or traditional guards
- **Naming**: CamelCase for classes, camelCase for methods/variables

## Documentation

- **User Guide**: `Docs/userguide.pdf` - Running ORE, examples, parametrization
- **Products Guide**: `Docs/products.pdf` - Trade type descriptions and XML schemas
- **Methodology**: `Docs/ore_design.pdf` - Technical methodology documentation
- **API Reference**: Generated via Doxygen from source comments
- **Release Notes**: See [News.txt](News.txt) for version-by-version changes

## Recent Notable Features (v13)

- SA-CCR, BA-CVA, SA-CVA analytics
- AMC exposure framework with AAD-based XVA sensitivities
- Dynamic SIMM model validation (IR/FX CRIF analytic)
- Serialization of AMC path data and regression models
- Callable swaps with mid-coupon exercise
- Optimized memory footprint for exposure calculations
- ORE-SWIG integrated into main repository
- Examples reorganized by topic (see [Examples/Readme.md](Examples/Readme.md))

## Troubleshooting

### Build Issues

- **Boost not found**: Set `Boost_INCLUDE_DIR` and `Boost_LIBRARY_DIR` explicitly
- **Slow builds**: Use Ninja (`cmake -G Ninja`) for 30-50% faster builds
- **macOS linker warnings**: Flat namespace warnings are harmless, can be ignored
- **Out of memory**: Reduce parallel jobs (`ninja -j 4` instead of auto-detection)

### Runtime Issues

- **Curve building failures**: Check market data completeness in CSV files
- **Missing fixings**: Ensure fixings.csv contains all required historical data
- **Date mismatches**: Verify asof date matches market data dates
- **Engine not found**: Check pricingengine.xml has configuration for trade type

## Additional Resources

- Project Website: http://opensourcerisk.org
- QuantLib: http://quantlib.org
- User Guide: Comprehensive documentation in `Docs/`
- Examples: See [Examples/](Examples/) organized by topic
