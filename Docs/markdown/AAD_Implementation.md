# Algorithmic Automatic Differentiation (AAD) in ORE

## Table of Contents

1. [Overview](#overview)
2. [Architecture and Design Philosophy](#architecture-and-design-philosophy)
3. [Core Components](#core-components)
4. [AAD Integration Flow](#aad-integration-flow)
5. [Implementation in AMC Framework](#implementation-in-amc-framework)
6. [XVA Sensitivities with AAD](#xva-sensitivities-with-aad)
7. [Configuration Guide](#configuration-guide)
8. [Performance Characteristics](#performance-characteristics)
9. [Examples and Usage](#examples-and-usage)
10. [Technical Deep Dive](#technical-deep-dive)
11. [References](#references)

---

## Overview

ORE implements **Algorithmic Automatic Differentiation (AAD)** using a custom computation graph infrastructure to efficiently compute sensitivities for complex derivatives pricing and XVA calculations. Unlike traditional bump-and-revalue approaches, AAD can compute derivatives with respect to all inputs in a time proportional to computing the function itself, providing speedups of **20-30× for typical use cases**.

### Key Features

- **Custom Implementation**: No external AAD libraries; fully integrated with ORE architecture
- **Computation Graph Based**: Explicit graph construction from Abstract Syntax Trees (ASTs)
- **Backward Mode (Adjoint)**: Efficient for functions with many inputs and few outputs
- **Configurable Activation**: AAD can be enabled/disabled via XML configuration
- **Memory Optimized**: Red blocks support value reconstruction to reduce memory footprint
- **Multiple Value Types**: Template-based design supports double, RandomVariable, and external compute devices

### Where AAD is Used

1. **Scripted Trade Pricing**: NPV sensitivities for complex structured products
2. **XVA Analytics**: CVA, DVA, FVA sensitivities to market risk factors
3. **AMC Framework**: American Monte Carlo with AAD-based XVA sensitivities
4. **Dynamic SIMM**: Time-dependent delta sensitivities for initial margin
5. **Exposure Simulation**: Conditional portfolio sensitivities

---

## Architecture and Design Philosophy

### Why Custom Implementation?

ORE chose to implement AAD from scratch rather than using external libraries (CppAD, Sacura, dco/c++) for several strategic reasons:

#### 1. **Selective Activation**
AAD is computationally expensive when not needed. By using explicit computation graphs, ORE can:
- Enable AAD only for scripted trades and XVA calculations
- Keep standard QuantLib pricing unchanged
- Avoid intrusive type changes throughout the codebase

#### 2. **Performance Control**
```
Operator Overloading Approach:  ~10× overhead (Griewank 2000)
ORE Computation Graph Approach: ~4× overhead maximum
```

By avoiding operator overloading on core types, ORE maintains:
- Fast standard pricing paths
- Explicit graph construction from ASTs
- Optimized memory management

#### 3. **Configuration Flexibility**
```xml
<!-- AAD can be toggled per trade or analytic -->
<Parameter name="UseAD">true</Parameter>      <!-- Enable AAD -->
<Parameter name="UseAD">false</Parameter>     <!-- Disable for speed -->
```

#### 4. **Memory Management**
The computation graph approach enables:
- **Red Blocks**: Mark sections of the graph where values can be deleted and reconstructed
- **Explicit Cleanup**: Control over when intermediate values are freed
- **Streaming**: Process large graphs in chunks

### Design Principles

#### Separation of Concerns

```
ComputationGraph      →  DAG structure, node relationships
   ↓
forwardEvaluation()   →  Compute all node values
   ↓
backwardDerivatives() →  Compute adjoints via chain rule
   ↓
grad operations       →  Gradient implementations per operation
```

#### Template-Based Design

```cpp
template <class T>
void backwardDerivatives(
    const ComputationGraph& g,
    std::vector<T>& values,        // Any value type: double, RandomVariable, etc.
    std::vector<T>& derivatives,
    const std::vector<std::function<...>>& grad
);
```

This allows AAD to work with:
- `double` for single-path pricing
- `RandomVariable` for Monte Carlo paths
- External types for GPU computation

---

## Core Components

### 1. ComputationGraph

**Location**: [QuantExt/qle/ad/computationgraph.hpp](../../../QuantExt/qle/ad/computationgraph.hpp)

The `ComputationGraph` class represents a Directed Acyclic Graph (DAG) where:
- **Nodes** represent values (constants, variables, or operation results)
- **Edges** represent dependencies (inputs to operations)

#### Key Methods

```cpp
class ComputationGraph {
public:
    // Node Creation
    std::size_t insert(const std::string& label = "");
    std::size_t insert(const std::vector<std::size_t>& predecessors,
                      const std::size_t opId,
                      const std::string& label = "");

    // Constants and Variables
    std::size_t constant(const double c);
    std::size_t variable(const std::string& name);

    // Binary Operations
    std::size_t add(const std::size_t a, const std::size_t b);
    std::size_t subtract(const std::size_t a, const std::size_t b);
    std::size_t multiply(const std::size_t a, const std::size_t b);
    std::size_t divide(const std::size_t a, const std::size_t b);

    // Unary Operations
    std::size_t negative(const std::size_t a);
    std::size_t exp(const std::size_t a);
    std::size_t log(const std::size_t a);
    std::size_t sqrt(const std::size_t a);

    // Mathematical Functions
    std::size_t pow(const std::size_t a, const std::size_t b);
    std::size_t abs(const std::size_t a);
    std::size_t max(const std::size_t a, const std::size_t b);
    std::size_t min(const std::size_t a, const std::size_t b);

    // Probability Functions
    std::size_t normalCdf(const std::size_t a);
    std::size_t normalPdf(const std::size_t a);

    // Conditional Expectation (for AMC)
    std::size_t conditionalExpectation(
        const std::size_t regressor,
        const std::vector<std::size_t>& values
    );

    // Memory Optimization
    void startRedBlock();
    void endRedBlock();
    std::size_t redBlockId(const std::size_t node) const;

    // Graph Inspection
    std::size_t size() const;
    const std::vector<std::size_t>& predecessors(const std::size_t node) const;
    std::size_t opId(const std::size_t node) const;
    const std::string& variableName(const std::size_t node) const;
};
```

#### Example: Building a Simple Graph

```cpp
ComputationGraph g;

// Create input variables
std::size_t x = g.variable("x");
std::size_t y = g.variable("y");

// f = x^2 + y^2
std::size_t x_squared = g.multiply(x, x);      // x * x
std::size_t y_squared = g.multiply(y, y);      // y * y
std::size_t f = g.add(x_squared, y_squared);   // x^2 + y^2

// Graph now contains 5 nodes: x, y, x^2, y^2, f
std::cout << "Graph size: " << g.size() << std::endl;  // 5
```

### 2. Forward Evaluation

**Location**: [QuantExt/qle/ad/forwardevaluation.hpp](../../../QuantExt/qle/ad/forwardevaluation.hpp)

Forward evaluation computes all node values in topological order.

```cpp
template <class T>
void forwardEvaluation(
    const ComputationGraph& g,
    std::vector<T>& values,                     // Output: values[i] = value of node i
    const std::vector<std::function<T(const std::vector<const T*>&)>>& ops,
                                                // Operation implementations
    std::function<void(T&)> deleter = {},       // Optional cleanup function
    const std::vector<bool>& keepNodes = {},    // Nodes to keep in memory
    std::vector<std::pair<std::size_t, std::function<void(void)>>>* opNodeCache = nullptr
);
```

#### Example: Evaluating the Graph

```cpp
std::vector<double> values(g.size());
std::vector<std::function<double(const std::vector<const double*>&)>> ops;

// Define operations (add, multiply, etc.)
setupOperations(ops);

// Set input values
values[x] = 3.0;
values[y] = 4.0;

// Execute forward pass
forwardEvaluation(g, values, ops);

// Result: values[f] = 3^2 + 4^2 = 25
std::cout << "f(3,4) = " << values[f] << std::endl;  // 25
```

### 3. Backward Derivatives (AAD)

**Location**: [QuantExt/qle/ad/backwardderivatives.hpp](../../../QuantExt/qle/ad/backwardderivatives.hpp)

Backward mode AAD computes derivatives efficiently using the **chain rule in reverse**.

#### The Adjoint Method

For a computation graph computing `y = f(x₁, x₂, ..., xₙ)`:

```
Forward Pass:   x₁, x₂, ..., xₙ  →  intermediate values  →  y
Backward Pass:  dy/dx₁, dy/dx₂, ..., dy/dxₙ  ←  adjoints  ←  dy/dy = 1
```

**Key Insight**: To compute `dy/dxᵢ` for all inputs, traverse the graph **once** in reverse:

```cpp
template <class T>
void backwardDerivatives(
    const ComputationGraph& g,
    std::vector<T>& values,                     // From forward pass
    std::vector<T>& derivatives,                // Input: ∂L/∂outputs, Output: ∂L/∂inputs
    const std::vector<std::function<std::vector<T>(const std::vector<const T*>&,
                                                     const T*, Size)>>& grad
);
```

#### Algorithm

```cpp
// Initialize output adjoint
derivatives[output_node] = 1.0;

// Loop in REVERSE topological order
for (node = g.size() - 1; node > 0; --node) {
    if (derivatives[node] == 0) continue;  // No contribution

    // Get predecessors and operation
    auto preds = g.predecessors(node);
    auto opId = g.opId(node);

    // Compute gradients w.r.t. inputs
    std::vector<T> grads = grad[opId](values[preds], &values[node], node);

    // Accumulate adjoints (chain rule)
    for (size_t i = 0; i < preds.size(); ++i) {
        derivatives[preds[i]] += derivatives[node] * grads[i];
    }
}
```

#### Example: Computing Derivatives

```cpp
std::vector<double> derivatives(g.size(), 0.0);

// Set output adjoint: df/df = 1
derivatives[f] = 1.0;

// Define gradient operations
std::vector<std::function<...>> gradOps;
setupGradientOperations(gradOps);

// Execute backward pass
backwardDerivatives(g, values, derivatives, gradOps);

// Results:
// df/dx = 2x = 2*3 = 6
// df/dy = 2y = 2*4 = 8
std::cout << "df/dx = " << derivatives[x] << std::endl;  // 6
std::cout << "df/dy = " << derivatives[y] << std::endl;  // 8
```

### 4. Gradient Operations

Each operation in the computation graph needs a corresponding gradient function.

#### Example: Multiplication Gradient

For `c = a * b`, the gradients are:
```
∂c/∂a = b
∂c/∂b = a
```

Implementation:
```cpp
template <class T>
std::vector<T> grad_multiply(
    const std::vector<const T*>& args,  // [a, b]
    const T* result,                    // c = a * b
    Size node
) {
    return {
        *args[1],  // ∂c/∂a = b
        *args[0]   // ∂c/∂b = a
    };
}
```

#### Example: Division Gradient

For `c = a / b`:
```
∂c/∂a = 1/b
∂c/∂b = -a/b²
```

Implementation:
```cpp
template <class T>
std::vector<T> grad_divide(
    const std::vector<const T*>& args,
    const T* result,
    Size node
) {
    const T& a = *args[0];
    const T& b = *args[1];
    return {
        1.0 / b,           // ∂c/∂a
        -a / (b * b)       // ∂c/∂b
    };
}
```

#### Supported Operations (50+)

| Category | Operations |
|----------|-----------|
| **Arithmetic** | add, subtract, multiply, divide, negative |
| **Powers** | pow, sqrt, exp, log |
| **Trigonometric** | sin, cos, tan |
| **Comparison** | max, min, abs |
| **Probability** | normalCdf, normalPdf |
| **Logic** | indicatorEq, indicatorGt, indicatorGeq |
| **Conditional** | conditionalExpectation (for AMC) |

### 5. Model Integration: ModelCG

**Location**: [OREData/ored/scripting/models/modelcg.hpp](../../../OREData/ored/scripting/models/modelcg.hpp)

`ModelCG` is the base class for models that support computation graph-based AAD.

#### Architecture

```cpp
class ModelCG : public QuantLib::LazyObject {
public:
    // Computation Graph Access
    boost::shared_ptr<ComputationGraph> computationGraph() { return g_; }

    // Model Parameters with CG Nodes
    class ModelParameter {
    public:
        enum Type {
            fix,              // Historical fixing
            dsc,              // T0 discount factor
            fwd,              // T0 forward price
            lgm_H,            // LGM H function
            lgm_zeta,         // LGM zeta (integrated variance)
            fxbs_sigma,       // FX Black-Scholes volatility
            eqbs_sigma,       // Equity Black-Scholes volatility
            logFxSpot,        // log(FX spot)
            logEqSpot,        // log(Equity spot)
            sqrtCorr,         // sqrt(correlation matrix)
            // ... and more
        };

        Type type;
        std::size_t index;        // Index into model state
        std::size_t node;         // CG node representing this parameter
        double eval() const;      // Current value
    };

    // Random Variates (Brownian increments)
    virtual const std::vector<std::vector<std::size_t>>& randomVariates() const = 0;

    // All Model Parameters
    virtual std::vector<std::pair<std::size_t, double>> modelParameters() const = 0;

    // Graph Version (for caching)
    virtual std::size_t cgVersion() const = 0;

protected:
    boost::shared_ptr<ComputationGraph> g_;
};
```

#### Concrete Model: GaussianCamCG

**Location**: [OREData/ored/scripting/models/gaussiancamcg.hpp](../../../OREData/ored/scripting/models/gaussiancamcg.hpp)

GaussianCamCG implements a multi-asset Cross-Asset Model (CAM) with:
- **Interest Rates**: Linear Gaussian Model (LGM)
- **FX**: Log-normal processes
- **Equities**: Log-normal processes
- **Correlations**: Full correlation matrix

```cpp
class GaussianCamCG : public ModelCG {
public:
    // Constructor
    GaussianCamCG(
        const std::vector<std::string>& currencies,
        const std::vector<Handle<YieldTermStructure>>& curves,
        const std::vector<Handle<Quote>>& fxSpots,
        const std::vector<std::pair<std::string, Handle<YieldTermStructure>>>& irIndices,
        const std::vector<std::pair<std::string, Handle<Quote>>>& infIndices,
        const std::vector<std::string>& equities,
        const std::vector<Handle<Quote>>& eqSpots,
        const std::vector<Handle<YieldTermStructure>>& eqForecastCurves,
        const Handle<CorrelationTermStructure>& correlations,
        const Date& referenceDate,
        const Size timeStepsPerYear = 1,
        const IborFallbackConfig& iborFallbackConfig = IborFallbackConfig::defaultConfig(),
        const std::vector<Size>& conditionalExpectationModelStates = {}
    );

    // Model Evolution
    RandomVariable evolve(const std::size_t timeStep,
                         const RandomVariable& state) const;

    // Asset-Specific State Extractors
    RandomVariable getIrState(const std::size_t ccy,
                             const std::size_t timeStep,
                             const RandomVariable& state) const;
    RandomVariable getFxState(const std::size_t ccy,
                             const std::size_t timeStep,
                             const RandomVariable& state) const;

    // NPV Functions
    RandomVariable npv(const RandomVariable& amount,
                      const Date& obsdate,
                      const boost::optional<long>& discount,
                      const Date& fwddate,
                      const boost::optional<long>& fwdPaydate) const;
};
```

---

## AAD Integration Flow

### Three-Stage Process

```
┌─────────────────────────────────────────────────────────┐
│ Stage 1: Forward Evaluation                             │
├─────────────────────────────────────────────────────────┤
│ 1. Build computation graph from AST or model            │
│ 2. Add nodes for all operations                         │
│ 3. Execute forwardEvaluation()                          │
│ 4. Store all intermediate values                        │
│                                                         │
│ Output: values[i] for all nodes i                       │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 2: Backward Derivatives (AAD)                     │
├─────────────────────────────────────────────────────────┤
│ 1. Initialize: derivatives[output] = 1.0                │
│ 2. Execute backwardDerivatives() in reverse order       │
│ 3. Apply chain rule: ∂y/∂xᵢ += ∂y/∂f · ∂f/∂xᵢ           │
│ 4. Accumulate adjoints for all model parameters         │
│                                                         │
│ Output: derivatives[p] = ∂output/∂parameter_p           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ Stage 3: Risk Factor Conversion                         │
├─────────────────────────────────────────────────────────┤
│ 1. Convert model parameter sensitivities                │
│ 2. Apply Jacobian transformations:                      │
│    - Zero rates → Par rates                             │
│    - Model parameters → Market quotes                   │
│ 3. Populate sensitivity cube/report                     │
│                                                         │
│ Output: Sensitivities to market risk factors            │
└─────────────────────────────────────────────────────────┘
```

### Detailed Flow for Scripted Trade

#### 1. Graph Construction from Script AST

When a scripted trade is parsed, the script is converted to an Abstract Syntax Tree (AST), which is then transformed into a computation graph.

**Example Script:**
```
REQUIRE Underlying > 100;
Option = PAY(max(Underlying - Strike, 0), Maturity, PayCurrency);
```

**Graph Construction:**
```cpp
// In scriptedinstrumentpricingenginecg.cpp

// 1. Parse script → AST
auto ast = parseScript(script);

// 2. Convert AST → ComputationGraph
auto g = boost::make_shared<ComputationGraph>();

// For "Underlying > 100":
std::size_t underlying_node = g->variable("Underlying");
std::size_t strike_100 = g->constant(100.0);
std::size_t condition = g->indicatorGt(underlying_node, strike_100);

// For "max(Underlying - Strike, 0)":
std::size_t strike_node = g->variable("Strike");
std::size_t diff = g->subtract(underlying_node, strike_node);
std::size_t zero = g->constant(0.0);
std::size_t payoff = g->max(diff, zero);

// For "PAY(...)":
std::size_t discount = g->variable("DiscountFactor_Maturity");
std::size_t npv = g->multiply(payoff, discount);
```

#### 2. Model State Integration

The computation graph integrates model state from `ModelCG`:

```cpp
// Model provides random variates (Brownian increments)
auto randomVariates = model->randomVariates();

// Model provides parameter nodes
auto modelParams = model->modelParameters();

// Link script variables to model nodes
g->variable("Underlying") = model->getUnderlyingNode(obsDate);
g->variable("DiscountFactor_Maturity") = model->getDiscountNode(maturity);
```

#### 3. Forward Evaluation

```cpp
// Allocate value storage
std::vector<RandomVariable> values(g->size());

// Set model parameter values from market data
for (auto& [node, value] : modelParams) {
    values[node] = RandomVariable(nSamples, value);
}

// Execute forward pass
forwardEvaluation(g, values, ops);

// Extract NPV
RandomVariable npv = values[outputNode];
Real meanNPV = mean(npv);
```

#### 4. Backward Pass for Sensitivities

When sensitivities are requested:

```cpp
if (useAD) {
    // Allocate derivative storage
    std::vector<RandomVariable> derivatives(g->size(),
                                            RandomVariable(nSamples, 0.0));

    // Initialize output adjoint
    derivatives[outputNode] = RandomVariable(nSamples, 1.0);

    // Execute backward pass
    backwardDerivatives(g, values, derivatives, gradOps);

    // Extract sensitivities to model parameters
    for (auto& [node, value] : modelParams) {
        Real sensitivity = mean(derivatives[node]);
        sensitivities[paramName] = sensitivity;
    }
}
```

#### 5. Cache for Bump & Revalue

The key optimization: cache AAD derivatives and reuse them for bumped scenarios.

```cpp
// First call: compute AAD derivatives
if (!cachedDerivatives_) {
    backwardDerivatives(g, values, derivatives, gradOps);
    cachedDerivatives_ = derivatives;
}

// Subsequent calls with bumped market data:
// Just multiply cached derivatives by market shift
for (auto& [param, cachedDeriv] : cachedDerivatives_) {
    Real shift = bumpedValue - baseValue;
    Real bumpedNPV = baseNPV + cachedDeriv * shift;
}
```

This avoids recomputing the entire graph for each bump, providing **10-20× speedup**.

---

## Implementation in AMC Framework

### AMC Overview

**American Monte Carlo (AMC)** values derivatives with early exercise features using:
1. **Forward Simulation**: Generate future scenarios via Monte Carlo
2. **Backward Induction**: At each exercise date, compare:
   - **Intrinsic Value**: Immediate payoff
   - **Continuation Value**: Expected future value (estimated via regression)
3. **Optimal Exercise**: Exercise if intrinsic > continuation

### AMC-CG: AMC with Computation Graph

ORE extends AMC to support AAD by building a computation graph for the entire AMC algorithm.

#### Key Insight: Conditional Expectation as a Graph Node

The regression for continuation value becomes a **graph operation**:

```cpp
// Continuation value = E[future_value | regression_variables]
std::size_t continuation = g->conditionalExpectation(
    regressorNode,         // State variables for regression (S, t, ...)
    futureValueNodes       // Future values to regress
);
```

This enables AAD to compute:
```
∂NPV/∂model_param = ∂NPV/∂continuation · ∂continuation/∂model_param
```

### AMC-CG Architecture

**Base Engine**: [OREData/ored/scripting/engines/amccgbaseengine.hpp](../../../OREData/ored/scripting/engines/amccgbaseengine.hpp)

```cpp
class AmcCgBaseEngine {
public:
    // Build computation graph for AMC
    void buildComputationGraph(
        const boost::shared_ptr<ModelCG>& model,
        const std::vector<Date>& exerciseDates,
        const ScriptedTrade& trade
    );

    // Training: Build regression coefficients
    void trainRegressionModels(
        const Size trainingSamples,
        const Size regressionOrder,
        const std::string& basisFunction  // Monomial, Hermite, Laguerre
    );

    // Pricing: Evaluate with trained models
    void calculatePricing(
        const boost::shared_ptr<ComputationGraph>& g,
        std::vector<RandomVariable>& values
    );

    // Sensitivities: Execute AAD
    void calculateSensitivities(
        const boost::shared_ptr<ComputationGraph>& g,
        const std::vector<RandomVariable>& values,
        std::vector<RandomVariable>& derivatives
    );
};
```

### AMC-CG Execution Flow

```
┌──────────────────────────────────────────────────────────────┐
│ Phase 1: Training (on subset of paths)                       │
├──────────────────────────────────────────────────────────────┤
│ 1. Simulate forward (t=0 → T)                                │
│ 2. Backward induction (T → 0):                               │
│    For each exercise date t:                                 │
│      a. Compute intrinsic value at t                         │
│      b. Regress future NPV on state variables                │
│      c. Store regression coefficients                        │
│ 3. Build computation graph for optimal exercise              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ Phase 2: Pricing (on all paths)                              │
├──────────────────────────────────────────────────────────────┤
│ 1. Simulate forward (t=0 → T)                                │
│ 2. Use trained regression models in CG                       │
│ 3. Execute forwardEvaluation() with conditionalExpectation   │
│ 4. Extract NPV = mean(values[outputNode])                    │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ Phase 3: Sensitivities (AAD on computation graph)            │
├──────────────────────────────────────────────────────────────┤
│ 1. Initialize derivatives[outputNode] = 1.0                  │
│ 2. Execute backwardDerivatives()                             │
│ 3. Include gradient of conditionalExpectation:               │
│    ∂E[V|X]/∂model_param via expected stochastic AD           │
│ 4. Extract sensitivities = mean(derivatives[paramNodes])     │
└──────────────────────────────────────────────────────────────┘
```

### Expected Stochastic AD

For conditional expectation nodes, ORE implements **expected stochastic automatic differentiation** (Fries 2017):

```
Given: V_future = E[V | X]  (regression result)

Traditional AD would give: ∂V_future/∂param = E[∂V/∂param | X]

But we want: ∂V_future/∂param considering changes in E[·|·] operator

Solution (Fries 2017):
∂V_future/∂param = ∂E[V | X]/∂param
                 = E[∂V/∂param | X] + Cov(V, ∂X/∂param | X) / Var(X | X)
```

This is implemented in the gradient function for `conditionalExpectation` nodes.

### AMC-CG Product Engines

ORE provides specialized AMC-CG engines for common products:

#### 1. **AmcCgSwapEngine**
[OREData/ored/scripting/engines/amccgswapengine.hpp](../../../OREData/ored/scripting/engines/amccgswapengine.hpp)

For callable swaps:
```cpp
class AmcCgSwapEngine : public AmcCgBaseEngine {
    // Bermudan swaption with AMC-CG
    // Regression on:
    // - Current swap rate
    // - Discount factors
    // - Volatility state (LGM state)
};
```

#### 2. **AmcCgFxOptionEngine**
[OREData/ored/scripting/engines/amccgfxoptionengine.hpp](../../../OREData/ored/scripting/engines/amccgfxoptionengine.hpp)

For FX options with early exercise:
```cpp
class AmcCgFxOptionEngine : public AmcCgBaseEngine {
    // Regression on:
    // - FX spot
    // - Domestic/foreign interest rates
};
```

---

## XVA Sensitivities with AAD

### XVA Overview

**XVA** (X-Value Adjustment) encompasses various valuation adjustments:
- **CVA**: Credit Valuation Adjustment (counterparty default risk)
- **DVA**: Debt Valuation Adjustment (own default risk)
- **FVA**: Funding Valuation Adjustment (funding costs)
- **KVA**: Capital Valuation Adjustment (regulatory capital)
- **MVA**: Margin Valuation Adjustment (initial margin costs)

XVA calculations require:
1. **Exposure Simulation**: Monte Carlo simulation of future portfolio values
2. **Aggregation**: Netting set aggregation and collateral
3. **XVA Metrics**: Expected Exposure (EE), Potential Future Exposure (PFE), CVA
4. **Sensitivities**: Derivatives w.r.t. market risk factors

### Traditional XVA Sensitivity Calculation

**Bump & Revalue Approach:**
```
For each risk factor r:
    1. Bump r by Δr
    2. Rebuild market (yield curves, vol surfaces, etc.)
    3. Re-simulate exposures (thousands of scenarios × hundreds of dates)
    4. Recompute CVA_bumped
    5. Sensitivity = (CVA_bumped - CVA_base) / Δr
```

**Problem**: For n risk factors, this requires:
- n+1 full exposure simulations
- Each simulation: 10,000 scenarios × 100 dates × portfolio repricing
- **Total time**: Minutes to hours for large portfolios

### XVA with AAD: 24× Speedup

**AAD Approach:**
```
1. Build computation graph for ENTIRE XVA calculation
2. Forward evaluation: Compute base XVA
3. Backward derivatives: Compute ∂XVA/∂all_params in ONE pass
4. Transform to risk factor sensitivities via Jacobian
```

**Key Advantage**: Compute derivatives w.r.t. ALL parameters in time ~4× base calculation (not n× base calculation).

### XVA-CG Engine Architecture

**Location**: [OREAnalytics/orea/engine/xvaenginecg.hpp](../../../OREAnalytics/orea/engine/xvaenginecg.hpp)

```cpp
class XvaEngineCG {
public:
    XvaEngineCG(
        const boost::shared_ptr<Market>& market,
        const boost::shared_ptr<Portfolio>& portfolio,
        const boost::shared_ptr<NPVCube>& exposureCube,
        const boost::shared_ptr<NettingSetManager>& nettingSetManager,
        const std::string& configuration
    );

    // Build computation graph for XVA
    void buildComputationGraph();

    // Compute XVA (base case)
    void calculate();

    // Compute sensitivities via AAD
    void calculateSensitivities(
        const boost::shared_ptr<SensitivityScenarioData>& scenarioData
    );

    // Results
    Real cva() const;
    Real dva() const;
    Real fva() const;
    std::map<std::string, Real> sensitivities() const;
};
```

### XVA-CG Computation Graph Structure

The XVA computation graph includes nodes for:

```
Input Nodes:
├─ Model Parameters (from GaussianCamCG)
│  ├─ lgm_H[ccy][t]           : LGM H function
│  ├─ lgm_zeta[ccy][t]        : LGM integrated variance
│  ├─ dsc[ccy][t]             : Discount factors
│  ├─ fxbs_sigma[ccypair][t]  : FX volatilities
│  └─ logFxSpot[ccypair]      : FX spots
│
Simulation Nodes:
├─ randomVariates[scenario][t][factor] : Brownian increments
├─ modelState[scenario][t][ccy]        : Evolved state variables
│
Trade Pricing Nodes (for each trade i, scenario s, date t):
├─ tradeNPV[i][s][t]          : Trade NPV
├─ trades are priced using ModelCG and scripting engines
│
Netting Set Aggregation:
├─ nettingSetNPV[ns][s][t] = Σ tradeNPV[i][s][t] for trades in ns
├─ collateral[ns][s][t]
├─ exposure[ns][s][t] = max(nettingSetNPV - collateral, 0)
│
XVA Calculation:
├─ EE[ns][t] = E[exposure[ns][·][t]]          : Expected Exposure
├─ defaultProb[ns][t]                          : Default probability
├─ cva[ns] = LGD × Σ EE[ns][t] × PD × DF[t]  : CVA per netting set
└─ totalCVA = Σ cva[ns]                       : Total CVA
```

### Detailed XVA-CG Flow

#### Step 1: Build Computation Graph

```cpp
// Initialize computation graph
auto g = boost::make_shared<ComputationGraph>();

// Create model with CG
auto modelCG = boost::make_shared<GaussianCamCG>(
    currencies, curves, fxSpots, correlations, referenceDate
);

// For each date in simulation grid:
for (size_t t = 0; t < numDates; ++t) {
    Date simDate = simulationDates[t];

    // Evolve model state
    std::vector<std::size_t> stateNodes = modelCG->evolve(t, prevStateNodes);

    // For each trade in portfolio:
    for (auto& trade : portfolio->trades()) {
        // Build pricing graph for this trade
        std::size_t npvNode = trade->buildCG(modelCG, g, simDate);

        // Store in cube structure
        tradeNPVNodes[trade->id()][t] = npvNode;
    }

    // Aggregate by netting set
    for (auto& ns : nettingSets) {
        std::vector<std::size_t> tradeNodes;
        for (auto& tradeId : ns->trades()) {
            tradeNodes.push_back(tradeNPVNodes[tradeId][t]);
        }

        // Sum trade NPVs
        std::size_t nsNPV = g->sum(tradeNodes);

        // Collateral
        std::size_t collateral = buildCollateralNode(g, ns, t);

        // Exposure = max(nsNPV - collateral, 0)
        std::size_t netExposure = g->subtract(nsNPV, collateral);
        std::size_t zero = g->constant(0.0);
        std::size_t exposure = g->max(netExposure, zero);

        exposureNodes[ns->id()][t] = exposure;
    }
}

// Compute CVA from exposures
for (auto& ns : nettingSets) {
    std::size_t cvaNode = computeCVA(g, exposureNodes[ns->id()],
                                      defaultProbNodes[ns->id()],
                                      discountNodes,
                                      lgd);
    cvaNodes[ns->id()] = cvaNode;
}

// Total CVA
std::size_t totalCVA = g->sum(cvaNodes);
```

#### Step 2: Forward Evaluation

```cpp
// Allocate value storage (RandomVariable for all MC paths)
std::vector<RandomVariable> values(g->size());

// Set model parameters from market
auto modelParams = modelCG->modelParameters();
for (auto& [node, value] : modelParams) {
    values[node] = RandomVariable(nScenarios, value);
}

// Generate random variates
for (size_t s = 0; s < nScenarios; ++s) {
    for (size_t t = 0; t < numDates; ++t) {
        for (size_t f = 0; f < numFactors; ++f) {
            values[randomVariateNodes[s][t][f]] =
                RandomVariable(1, normalRandom());
        }
    }
}

// Execute forward pass
forwardEvaluation(g, values, ops);

// Extract base CVA
Real baseCVA = mean(values[totalCVA]);
```

#### Step 3: Backward Derivatives (AAD)

```cpp
// Allocate derivative storage
std::vector<RandomVariable> derivatives(g->size(),
                                         RandomVariable(nScenarios, 0.0));

// Initialize: ∂CVA/∂CVA = 1
derivatives[totalCVA] = RandomVariable(nScenarios, 1.0);

// Execute AAD
backwardDerivatives(g, values, derivatives, gradOps);

// Extract sensitivities to model parameters
std::map<std::string, Real> modelSensitivities;
for (auto& [node, baseValue] : modelParams) {
    Real sensitivity = mean(derivatives[node]);
    modelSensitivities[paramName] = sensitivity;
}
```

#### Step 4: Transform to Risk Factor Sensitivities

Model parameters (e.g., `lgm_zeta`, `dsc`) must be converted to market risk factors (e.g., par swap rates, FX spots).

**Jacobian Transformation:**
```
∂CVA/∂market_quote = Σ (∂CVA/∂model_param) × (∂model_param/∂zero_rate) × (∂zero_rate/∂market_quote)
                     └─ From AAD ─────┘   └── From model ──┘   └─── Par conversion ───┘
```

**Example: IR Sensitivity**

```cpp
// 1. AAD gives: ∂CVA/∂dsc[t]
Real dCVA_dDsc_t = derivatives[dscNode[t]];

// 2. Model gives: ∂dsc[t]/∂zero_rate[T]
// dsc(t) = exp(-r(0,t) · t)
// ∂dsc(t)/∂r(0,T) = -t · dsc(t)  if T >= t, else 0
Real dDsc_dZeroRate_T = -t * values[dscNode[t]];

// 3. Par conversion: ∂zero_rate[T]/∂par_rate[tenor]
// Uses swap Jacobian (computed via curve sensitivity)
Real dZeroRate_dParRate = swapJacobian(T, tenor);

// 4. Chain rule:
Real dCVA_dParRate = dCVA_dDsc_t * dDsc_dZeroRate_T * dZeroRate_dParRate;

sensitivities["IR/EUR/" + tenor] = dCVA_dParRate;
```

**Example: FX Sensitivity**

```cpp
// 1. AAD gives: ∂CVA/∂logFxSpot
Real dCVA_dLogFX = derivatives[logFxSpotNode];

// 2. Transform: ∂logFX/∂FX = 1/FX
Real fx = exp(values[logFxSpotNode]);
Real dCVA_dFX = dCVA_dLogFX / fx;

sensitivities["FX/EURUSD"] = dCVA_dFX;
```

### XVA Sensitivity Configuration

**File**: `xvasensiconfig.xml`

```xml
<SensitivityAnalysis>
  <!-- Market risk factors to compute sensitivities for -->
  <RiskFactors>
    <!-- Interest Rate Sensitivities -->
    <RiskFactor type="DiscountCurve">
      <Currency>EUR</Currency>
      <Currency>USD</Currency>
      <Tenors>1Y,2Y,5Y,10Y,20Y,30Y</Tenors>
    </RiskFactor>

    <!-- FX Sensitivities -->
    <RiskFactor type="FXSpot">
      <CurrencyPair>EURUSD</CurrencyPair>
      <CurrencyPair>GBPUSD</CurrencyPair>
    </RiskFactor>

    <!-- Volatility Sensitivities -->
    <RiskFactor type="SwaptionVolatility">
      <Currency>EUR</Currency>
      <Expiries>1Y,5Y,10Y</Expiries>
      <Terms>5Y,10Y,20Y</Terms>
    </RiskFactor>

    <!-- Credit Spreads -->
    <RiskFactor type="SurvivalProbability">
      <Name>CPTY_A</Name>
      <Tenors>1Y,3Y,5Y,10Y</Tenors>
    </RiskFactor>
  </RiskFactors>

  <!-- AAD Configuration -->
  <AADConfiguration>
    <UseAAD>true</UseAAD>
    <CacheDerivatives>true</CacheDerivatives>
  </AADConfiguration>
</SensitivityAnalysis>
```

---

## Configuration Guide

### Enabling AAD for Scripted Trades

#### Pricing Engine Configuration

**File**: `pricingengine.xml`

```xml
<PricingEngines>
  <Product type="ScriptedTrade">
    <Model>Generic</Model>

    <ModelParameters>
      <!-- Model Selection -->
      <Parameter name="Model">BlackScholes</Parameter>
      <!-- Options: BlackScholes, LocalVolDupire, LocalVolAndreasenHuge,
                     GaussianCam (multi-asset), GaussianCam1F, LGM -->

      <!-- Calibration Settings -->
      <Parameter name="Calibration">ATM</Parameter>
      <Parameter name="CalibrationStrikes">ATM,ATM-100,ATM+100</Parameter>
    </ModelParameters>

    <Engine>Generic</Engine>

    <EngineParameters>
      <!-- Monte Carlo Engine -->
      <Parameter name="Engine">MC</Parameter>

      <!-- AAD Configuration -->
      <Parameter name="UseCG">true</Parameter>           <!-- Required for AAD -->
      <Parameter name="UseAD">true</Parameter>           <!-- Enable AAD -->
      <Parameter name="UseCachedSensis">true</Parameter> <!-- Cache derivatives -->

      <!-- MC Simulation -->
      <Parameter name="Samples">10000</Parameter>
      <Parameter name="Seed">42</Parameter>
      <Parameter name="SobolOrdering">Unit</Parameter>
      <Parameter name="SobolDirectionIntegers">JoeKuoD7</Parameter>

      <!-- Brownian Bridge (for path-dependent products) -->
      <Parameter name="BrownianBridge">true</Parameter>

      <!-- AMC Settings (for early exercise) -->
      <Parameter name="RegressionOrder">6</Parameter>
      <Parameter name="BasisFunction">Monomial</Parameter>
      <!-- Options: Monomial, Hermite, Laguerre -->

      <!-- Training/Pricing Split -->
      <Parameter name="TrainingPaths">8192</Parameter>

      <!-- Performance Options -->
      <Parameter name="Interactive">false</Parameter>

      <!-- External Compute (GPU - experimental) -->
      <Parameter name="UseExternalComputeFramework">false</Parameter>
      <Parameter name="ExternalComputeDevice">GPUOCL</Parameter>
    </EngineParameters>
  </Product>
</PricingEngines>
```

### Enabling AAD for XVA

#### Simulation Configuration

**File**: `ore.xml`

```xml
<Simulation>
  <!-- Standard Simulation Parameters -->
  <Parameters>
    <Discretization>Exact</Discretization>
    <Grid>40,3M</Grid>  <!-- 40 points, 3 months spacing -->
    <Samples>10000</Samples>
    <Seed>42</Seed>
  </Parameters>

  <!-- Cross Asset Model -->
  <CrossAssetModel>
    <Discretization>Exact</Discretization>
    <Currencies>
      <Currency>EUR</Currency>
      <Currency>USD</Currency>
    </Currencies>
    <FXPairs>
      <Pair>EURUSD</Pair>
    </FXPairs>
    <BootstrapTolerance>0.0001</BootstrapTolerance>
  </CrossAssetModel>

  <!-- AMC with Computation Graph -->
  <AmcConfiguration>
    <!-- Enable AMC-CG -->
    <Parameter name="amc">true</Parameter>
    <Parameter name="amcCg">Full</Parameter>
    <!-- Options:
         - Disabled: Use legacy AMC (no CG, no AAD)
         - CubeGeneration: Use CG for exposure cube only
         - Full: Use CG for exposure AND sensitivities -->

    <!-- Trade Types for AMC -->
    <Parameter name="amcTradeTypes">Swap,ScriptedTrade</Parameter>

    <!-- Regression Configuration -->
    <Parameter name="RegressionOrder">4</Parameter>
    <Parameter name="TrainingSamples">8192</Parameter>
    <Parameter name="RegressionVarianceCutoff">0.0001</Parameter>

    <!-- Serialization (save/load trained models) -->
    <Parameter name="amcCgSerializePath">./amc_cache/</Parameter>
    <Parameter name="amcCgSerializeGrid">true</Parameter>
  </AmcConfiguration>
</Simulation>
```

#### XVA Sensitivity Configuration

**File**: `ore.xml` (XVA Analytic Section)

```xml
<Analytics>
  <Analytic type="xva">
    <Parameter name="baseCurrency">EUR</Parameter>
    <Parameter name="exposureProfiles">true</Parameter>

    <!-- XVA-CG with AAD Sensitivities -->
    <Parameter name="xvaCgSensitivityConfigFile">Input/xvasensiconfig.xml</Parameter>

    <!-- Netting and Collateral -->
    <Parameter name="nettingSetId">CPTY_A</Parameter>
    <Parameter name="csaFile">Input/netting.xml</Parameter>

    <!-- XVA Types -->
    <Parameter name="cva">true</Parameter>
    <Parameter name="dva">true</Parameter>
    <Parameter name="fva">true</Parameter>
    <Parameter name="mva">true</Parameter>

    <!-- Credit Parameters -->
    <Parameter name="dvaName">BANK</Parameter>
    <Parameter name="fvaBorrowingCurve">BANK_SR</Parameter>
    <Parameter name="fvaLendingCurve">BANK_SR</Parameter>
  </Analytic>
</Analytics>
```

### Performance Tuning

#### Memory Optimization

**Red Blocks**:
- Automatically inserted by ORE in long computation graphs
- Intermediate values deleted and reconstructed as needed
- Reduces memory by ~50-70% for large graphs

**Manual Control** (advanced):
```cpp
// In custom code
g->startRedBlock();
// ... add many nodes ...
g->endRedBlock();
// Values in this block can be deleted in backward pass
```

#### Parallelization

```xml
<Parameter name="nThreads">8</Parameter>  <!-- For scenario generation -->
```

Note: AAD itself is inherently sequential (backward pass), but:
- Scenario generation can be parallelized
- Multiple trade evaluations can be parallelized
- Multiple sensitivity calculations can be parallelized

#### Training vs Pricing Samples

For AMC-CG:
```xml
<Parameter name="TrainingPaths">8192</Parameter>  <!-- Smaller for regression -->
<Parameter name="Samples">100000</Parameter>       <!-- Larger for final pricing -->
```

Recommendation:
- Training: 5,000 - 10,000 paths (sufficient for regression)
- Pricing: 50,000 - 500,000 paths (for accuracy)
- AAD: Works on pricing samples (full graph)

---

## Performance Characteristics

### Speedup Analysis

#### Scripted Trade Sensitivities

| Method | Relative Time | Sensitivities Computed |
|--------|--------------|------------------------|
| **Finite Difference** | 1 + n | n (one per risk factor) |
| **AAD (cached)** | 1.2 + 0.1n | n (all at once) |

For n=100 risk factors:
- Finite Difference: 101× base calculation time
- AAD: 1.2 + 10 = 11.2× base time
- **Speedup: 9×**

#### XVA Sensitivities (Real-World Example)

From Example 56 benchmarks:

| Configuration | Time (s) | Description |
|--------------|----------|-------------|
| **AMC Legacy** | 9 | Exposure only, no sensitivities |
| **AMC-CG (exposure only)** | 10 | CG overhead minimal |
| **Bump & Revalue (100 factors)** | 980 | 100× scenario regeneration |
| **AAD** | 42 | 1× forward + 1× backward |
| | | **Speedup: 23×** |

#### Breakdown of AAD Time

```
Total AAD Time = Forward + Backward + Transform
                   40%      50%        10%
```

- **Forward Evaluation**: ~40% (same as base calculation)
- **Backward Derivatives**: ~50% (gradient computations)
- **Risk Factor Transform**: ~10% (Jacobian application)

Total overhead vs. base: **~2-4×** (depending on graph complexity)

### Memory Usage

#### Without Red Blocks

```
Memory = sizeof(ValueType) × (numNodes + numNodes)
       = sizeof(ValueType) × 2 × numNodes

For RandomVariable with 10,000 samples:
sizeof(RandomVariable) = 10,000 × 8 bytes = 80 KB
numNodes (large XVA graph) = 10,000,000
Memory = 80 KB × 2 × 10M = 1.6 TB  (impossible!)
```

#### With Red Blocks

```
Memory = sizeof(ValueType) × (numNodes + numKeptNodes)

If 90% of nodes are in red blocks:
numKeptNodes = 0.1 × numNodes = 1,000,000
Memory = 80 KB × (10M + 1M) = 880 GB  (large but feasible)
```

For typical use cases:
- **Scripted Trade**: 10,000 - 100,000 nodes → 1-10 GB
- **XVA (small portfolio)**: 1,000,000 nodes → 100 GB
- **XVA (large portfolio)**: 10,000,000 nodes → 1 TB (requires red blocks)

### Scaling Properties

#### Number of Risk Factors (n)

**Bump & Revalue**: O(n) full repricing operations
**AAD**: O(1) backward pass (independent of n)

```
              n=10   n=100   n=1000
Bump & Revalue  10×    100×    1000×
AAD            1.5×    1.5×     1.5×
```

#### Number of Scenarios (m)

**Both methods**: O(m) scenarios to simulate

AAD doesn't improve scenario generation, but computes sensitivities per scenario efficiently.

#### Graph Size (N nodes)

**Forward**: O(N)
**Backward**: O(N)

Linear scaling with graph size.

---

## Examples and Usage

### Example 1: Basic Scripted Trade with AAD

**Location**: [Examples/Legacy/Example_61](../../../Examples/Legacy/Example_61/)

#### Trade: European Call Option

**portfolio.xml**:
```xml
<Trade id="CALL_EUR">
  <TradeType>ScriptedTrade</TradeType>
  <Envelope>
    <CounterParty>BANK</CounterParty>
    <NettingSetId>BANK_EUR</NettingSetId>
  </Envelope>
  <ScriptedTradeData>
    <Script>
      <Code><![CDATA[
        NUMBER Payoff;
        Payoff = max(Underlying(Expiry) - Strike, 0);
        Option = PAY(Payoff, Expiry, Settlement, PayCcy);
      ]]></Code>
    </Script>
    <Data>
      <Event>
        <Name>Expiry</Name>
        <Value>2026-01-15</Value>
      </Event>
      <Event>
        <Name>Settlement</Name>
        <Value>2026-01-17</Value>
      </Event>
      <Number>
        <Name>Strike</Name>
        <Value>100</Value>
      </Number>
      <Currency>
        <Name>PayCcy</Name>
        <Value>EUR</Value>
      </Currency>
      <Index>
        <Name>Underlying</Name>
        <Value>EQ-SPX</Value>
      </Index>
    </Data>
  </ScriptedTradeData>
</Trade>
```

#### Pricing Engine (AAD Enabled)

**pricingengine_ad.xml**:
```xml
<Product type="ScriptedTrade">
  <Model>Generic</Model>
  <ModelParameters>
    <Parameter name="Model">BlackScholes</Parameter>
  </ModelParameters>
  <Engine>Generic</Engine>
  <EngineParameters>
    <Parameter name="Engine">MC</Parameter>
    <Parameter name="Samples">10000</Parameter>
    <Parameter name="UseCG">true</Parameter>
    <Parameter name="UseAD">true</Parameter>
    <Parameter name="UseCachedSensis">true</Parameter>
  </EngineParameters>
</Product>
```

#### Run Sensitivity Analysis

```bash
cd Examples/Legacy/Example_61
../../../build/App/ore Input/ore_sensi_ad.xml
```

#### Results

**Output/sensi.csv**:
```
TradeId,RiskFactor,RiskFactorType,ShiftSize,Delta,Gamma
CALL_EUR,EQ-SPX,EquitySpot,0.01,52.3,0.042
CALL_EUR,EUR-EONIA,DiscountCurve/1Y,0.0001,-1.2,0.001
CALL_EUR,EUR-EONIA,DiscountCurve/2Y,0.0001,-0.5,0.000
CALL_EUR,EQ-SPX,EquityVolatility/ATM/1Y,0.01,15.7,0.003
```

**Performance**:
- Base NPV calculation: 0.8s
- AAD sensitivities (20 risk factors): 1.5s total (0.035s per factor)
- Bump & revalue (20 risk factors): 16s total (0.8s per factor)
- **Speedup: 10.7×**

### Example 2: XVA with AAD Sensitivities

**Location**: [Examples/Legacy/Example_56](../../../Examples/Legacy/Example_56/)

#### Portfolio

10 interest rate swaps with counterparty CPTY_A:
- 5 EUR payer swaps
- 5 USD receiver swaps
- Maturities: 5Y to 30Y
- Notionals: €10M - €50M

#### Configuration (AAD)

**ore_ad.xml**:
```xml
<Simulation>
  <Parameters>
    <Grid>40,3M</Grid>
    <Samples>10000</Samples>
  </Parameters>
  <CrossAssetModel>
    <Currencies>EUR,USD</Currencies>
  </CrossAssetModel>
  <AmcConfiguration>
    <Parameter name="amc">true</Parameter>
    <Parameter name="amcCg">Full</Parameter>
    <Parameter name="amcTradeTypes">Swap</Parameter>
    <Parameter name="RegressionOrder">4</Parameter>
  </AmcConfiguration>
</Simulation>

<Analytics>
  <Analytic type="xva">
    <Parameter name="cva">true</Parameter>
    <Parameter name="xvaCgSensitivityConfigFile">Input/xvasensiconfig.xml</Parameter>
  </Analytic>
</Analytics>
```

**xvasensiconfig.xml**:
```xml
<SensitivityAnalysis>
  <RiskFactors>
    <RiskFactor type="DiscountCurve">
      <Currency>EUR</Currency>
      <Currency>USD</Currency>
      <Tenors>1Y,2Y,5Y,10Y,20Y,30Y</Tenors>
    </RiskFactor>
    <RiskFactor type="FXSpot">
      <CurrencyPair>EURUSD</CurrencyPair>
    </RiskFactor>
    <RiskFactor type="SurvivalProbability">
      <Name>CPTY_A</Name>
      <Tenors>1Y,3Y,5Y,10Y</Tenors>
    </RiskFactor>
  </RiskFactors>
</SensitivityAnalysis>
```

#### Run XVA with AAD

```bash
cd Examples/Legacy/Example_56
../../../build/App/ore Input/ore_ad.xml
```

#### Results

**Output/xva.csv**:
```
NettingSet,CVA,DVA,FVA,CollateralFloor
CPTY_A,285000,0,-12000,0
```

**Output/xva_sensitivity.csv**:
```
NettingSet,RiskFactor,Sensitivity
CPTY_A,DiscountCurve/EUR/5Y,1250.5
CPTY_A,DiscountCurve/EUR/10Y,2340.2
CPTY_A,DiscountCurve/USD/5Y,-980.3
CPTY_A,FXSpot/EURUSD,15000.7
CPTY_A,SurvivalProbability/CPTY_A/5Y,8500.2
```

**Performance**:
```
Simulation (exposure generation):  45s
CVA calculation:                    2s
AAD sensitivities (17 factors):     8s
─────────────────────────────────────
Total AAD:                         55s

Bump & Revalue (17 factors):      820s

Speedup: 14.9×
```

### Example 3: Bermudan Swaption with AMC-CG

**Location**: [Examples/AmericanMonteCarlo](../../../Examples/AmericanMonteCarlo/)

#### Trade: 10Y Bermudan Payer Swaption

**portfolio.xml**:
```xml
<Trade id="BERM_SWAPTION">
  <TradeType>ScriptedTrade</TradeType>
  <ScriptedTradeData>
    <Script>
      <Code><![CDATA[
        NUMBER exercised, i, contValue, intrValue;
        FOR i IN (SIZE(ExerciseDates), 1, -1) DO
          IF exercised == 0 THEN
            intrValue = NPV(FloatingLeg(ExerciseDates[i]), PayCcy) -
                       NPV(FixedLeg(ExerciseDates[i]), PayCcy);
            contValue = LOGPAY(intrValue, ExerciseDates[i], PayCcy);
            IF intrValue > contValue THEN
              exercised = 1;
              Option = PAY(intrValue, ExerciseDates[i], PayCcy);
            END;
          END;
        END;
      ]]></Code>
    </Script>
  </ScriptedTradeData>
</Trade>
```

#### Pricing with AMC-CG and AAD

**pricingengine.xml**:
```xml
<Product type="ScriptedTrade">
  <Model>Generic</Model>
  <ModelParameters>
    <Parameter name="Model">LGM</Parameter>
    <Parameter name="Currency">EUR</Parameter>
  </ModelParameters>
  <Engine>Generic</Engine>
  <EngineParameters>
    <Parameter name="Engine">MC</Parameter>
    <Parameter name="Samples">50000</Parameter>
    <Parameter name="TrainingPaths">8192</Parameter>
    <Parameter name="RegressionOrder">6</Parameter>
    <Parameter name="BasisFunction">Hermite</Parameter>
    <Parameter name="UseCG">true</Parameter>
    <Parameter name="UseAD">true</Parameter>
  </EngineParameters>
</Product>
```

#### Results

```
NPV: €450,000
Delta (EUR 10Y):  €2,500 / bp
Vega (EUR 10Yx10Y): €12,000 / bp vol

Computation time:
- Training (8,192 paths):     5s
- Pricing (50,000 paths):    15s
- AAD sensitivities (25):     8s
Total: 28s

Bump & revalue: 350s (25 factors)
Speedup: 12.5×
```

---

## Technical Deep Dive

### Gradient Implementations

#### Binary Operations

**Addition**: `c = a + b`
```cpp
// Forward: c = a + b
// Backward: ∂L/∂a += ∂L/∂c · 1
//          ∂L/∂b += ∂L/∂c · 1

template <class T>
std::vector<T> grad_add(
    const std::vector<const T*>& args,  // [a, b]
    const T* result,                    // c
    Size node
) {
    return {T(1.0), T(1.0)};  // [∂c/∂a, ∂c/∂b]
}
```

**Multiplication**: `c = a × b`
```cpp
// Forward: c = a × b
// Backward: ∂L/∂a += ∂L/∂c · b
//          ∂L/∂b += ∂L/∂c · a

template <class T>
std::vector<T> grad_multiply(
    const std::vector<const T*>& args,
    const T* result,
    Size node
) {
    return {*args[1], *args[0]};  // [b, a]
}
```

**Division**: `c = a / b`
```cpp
// Forward: c = a / b
// Backward: ∂L/∂a += ∂L/∂c · (1/b)
//          ∂L/∂b += ∂L/∂c · (-a/b²)

template <class T>
std::vector<T> grad_divide(
    const std::vector<const T*>& args,
    const T* result,
    Size node
) {
    const T& a = *args[0];
    const T& b = *args[1];
    return {
        T(1.0) / b,       // ∂c/∂a
        -a / (b * b)      // ∂c/∂b
    };
}
```

#### Unary Operations

**Exponential**: `y = exp(x)`
```cpp
// Forward: y = exp(x)
// Backward: ∂L/∂x += ∂L/∂y · exp(x) = ∂L/∂y · y

template <class T>
std::vector<T> grad_exp(
    const std::vector<const T*>& args,
    const T* result,
    Size node
) {
    return {*result};  // exp(x) = y
}
```

**Natural Log**: `y = log(x)`
```cpp
// Forward: y = log(x)
// Backward: ∂L/∂x += ∂L/∂y · (1/x)

template <class T>
std::vector<T> grad_log(
    const std::vector<const T*>& args,
    const T* result,
    Size node
) {
    return {T(1.0) / *args[0]};
}
```

**Power**: `y = x^n`
```cpp
// Forward: y = x^n
// Backward: ∂L/∂x += ∂L/∂y · n·x^(n-1)

template <class T>
std::vector<T> grad_pow(
    const std::vector<const T*>& args,  // [x, n]
    const T* result,                    // y = x^n
    Size node
) {
    const T& x = *args[0];
    const T& n = *args[1];
    return {
        n * pow(x, n - T(1.0)),         // ∂y/∂x
        (*result) * log(x)              // ∂y/∂n = x^n · log(x)
    };
}
```

#### Max/Min Operations

**Maximum**: `y = max(a, b)`
```cpp
// Forward: y = max(a, b)
// Backward: ∂L/∂a += ∂L/∂y · 1[a >= b]
//          ∂L/∂b += ∂L/∂y · 1[b > a]

template <class T>
std::vector<T> grad_max(
    const std::vector<const T*>& args,
    const T* result,
    Size node
) {
    const T& a = *args[0];
    const T& b = *args[1];

    // Smoothed indicator (avoids discontinuity)
    T epsilon = 1e-10;
    T indicator_a = (a >= b - epsilon) ? T(1.0) : T(0.0);
    T indicator_b = (b > a - epsilon) ? T(1.0) : T(0.0);

    // Normalize if both are active (at equality)
    T sum = indicator_a + indicator_b;
    if (sum > T(1.5)) {  // Both active
        indicator_a /= sum;
        indicator_b /= sum;
    }

    return {indicator_a, indicator_b};
}
```

#### Probability Functions

**Normal CDF**: `y = Φ(x)`
```cpp
// Forward: y = Φ(x) = ∫_{-∞}^x (1/√(2π)) exp(-t²/2) dt
// Backward: ∂L/∂x += ∂L/∂y · φ(x)
//          where φ(x) = (1/√(2π)) exp(-x²/2)

template <class T>
std::vector<T> grad_normalCdf(
    const std::vector<const T*>& args,
    const T* result,
    Size node
) {
    const T& x = *args[0];
    T phi = exp(-x * x / T(2.0)) / sqrt(T(2.0 * M_PI));
    return {phi};
}
```

### Conditional Expectation Gradient

The most complex gradient: regression for AMC.

**Forward**: `E[V | X]` computed via regression
```cpp
// 1. Training phase (done once):
//    Given samples {X_i, V_i}, fit regression:
//    V ≈ β₀ + β₁·f₁(X) + β₂·f₂(X) + ... + βₖ·fₖ(X)
//
//    where f_j are basis functions (monomials, Hermite, etc.)
//
// 2. Prediction:
//    E[V | X] = β₀ + β₁·f₁(X) + ... + βₖ·fₖ(X)
```

**Backward** (Expected Stochastic AD):
```cpp
// ∂L/∂V_i += ∂L/∂E[V|X] · (∂E[V|X]/∂V_i)
// ∂L/∂X_i += ∂L/∂E[V|X] · (∂E[V|X]/∂X_i)

template <class T>
std::vector<T> grad_conditionalExpectation(
    const std::vector<const T*>& args,     // [X, V₁, V₂, ..., Vₙ]
    const T* result,                       // E[V|X]
    Size node
) {
    const T& X = *args[0];
    size_t n_values = args.size() - 1;

    std::vector<T> grads;

    // 1. Gradient w.r.t. regressor X
    //    ∂E[V|X]/∂X = Σ βⱼ · (∂fⱼ(X)/∂X)
    T dEdX = T(0.0);
    for (size_t j = 0; j < regressionCoeffs_.size(); ++j) {
        dEdX += regressionCoeffs_[j] * basisFunctionDerivative(j, X);
    }
    grads.push_back(dEdX);

    // 2. Gradient w.r.t. values V_i
    //    From Fries (2017):
    //    ∂E[V|X]/∂V_i = w_i where w are regression weights
    //    w = (F^T F)^{-1} F^T  (F = basis function matrix)
    for (size_t i = 0; i < n_values; ++i) {
        grads.push_back(T(regressionWeights_[i]));
    }

    return grads;
}
```

### Red Blocks Implementation

Red blocks optimize memory by allowing value reconstruction.

#### Marking Red Blocks

```cpp
ComputationGraph g;

// Normal nodes (always kept)
size_t x = g.variable("x");
size_t y = g.variable("y");

g.startRedBlock();  // Mark start of deletable region

// These nodes can be deleted and reconstructed
size_t a = g.multiply(x, y);
size_t b = g.exp(a);
size_t c = g.log(b);

g.endRedBlock();  // Mark end

// Result nodes (always kept)
size_t z = g.add(c, x);
```

#### Backward Pass with Reconstruction

```cpp
template <class T>
void backwardDerivatives(
    const ComputationGraph& g,
    std::vector<T>& values,
    std::vector<T>& derivatives,
    const std::vector<std::function<...>>& grad,
    std::function<void(T&)> deleter,
    const std::vector<bool>& keepNodes
) {
    // Standard backward loop
    for (size_t node = g.size() - 1; node > 0; --node) {
        if (derivatives[node] == T(0.0)) continue;

        // Check if values need reconstruction
        size_t redBlockId = g.redBlockId(node);
        if (redBlockId != 0 && !keepNodes[node]) {
            // Values were deleted - reconstruct forward
            reconstructRedBlock(g, values, ops, redBlockId);
        }

        // Compute gradients
        auto preds = g.predecessors(node);
        auto grads = grad[g.opId(node)](/* ... */);

        // Accumulate
        for (size_t i = 0; i < preds.size(); ++i) {
            derivatives[preds[i]] += derivatives[node] * grads[i];
        }

        // Delete value if in red block
        if (redBlockId != 0 && !keepNodes[node]) {
            deleter(values[node]);
        }
    }
}
```

### RandomVariable Type

For Monte Carlo paths, ORE uses `RandomVariable` type:

```cpp
class RandomVariable {
public:
    RandomVariable(Size size = 0, Real value = 0.0);

    Size size() const;  // Number of paths
    Real operator[](Size i) const;
    Real& operator[](Size i);

    // Statistics
    Real mean() const;
    Real variance() const;

    // Operations (vectorized)
    RandomVariable operator+(const RandomVariable& other) const;
    RandomVariable operator*(const RandomVariable& other) const;
    RandomVariable exp() const;
    // ... etc

private:
    std::vector<Real> data_;
};
```

All AAD operations work on `RandomVariable` via templates:
```cpp
// Same gradient function works for double and RandomVariable
auto grad = grad_multiply<RandomVariable>(args, result, node);
```

---

## References

### Primary Documentation

1. **ORE Design Document**
   Location: `Docs/Design/ore_design.tex`
   Sections on computation graph and AAD implementation

2. **AAD Technical Note**
   Location: `Docs/Design/aad.tex`
   Detailed mathematical exposition of AAD in ORE

3. **User Guide**
   Location: `Docs/UserGuide/userguide.tex`
   Sections on scripted trade pricing engines and XVA configuration

4. **Release Notes**
   Location: `News.txt`
   v12+: AAD introduction
   v13+: AMC-CG, dynamic SIMM, AAD improvements

### Academic References

1. **Griewank, Andreas (2000)**
   "Evaluating Derivatives: Principles and Techniques of Algorithmic Differentiation"
   SIAM, Philadelphia
   *Classic reference on AAD theory*

2. **Fries, Christian P. (2017)**
   "Computational aspects of sensitivities in Monte-Carlo pricing"
   *Expected stochastic AD for conditional expectations*

3. **Giles, Michael B. & Glasserman, Paul (2006)**
   "Smoking adjoints: fast Monte Carlo Greeks"
   *Adjoint methods for Monte Carlo derivatives*

4. **Leclerc, Matthieu, Liang, Qian, & Schneider, Irwin (2009)**
   "Fast Monte Carlo Bermudan Greeks"
   *AAD for American options*

### Code References

#### Core AAD Infrastructure
- [QuantExt/qle/ad/computationgraph.hpp](../../../QuantExt/qle/ad/computationgraph.hpp)
- [QuantExt/qle/ad/backwardderivatives.hpp](../../../QuantExt/qle/ad/backwardderivatives.hpp)
- [QuantExt/qle/ad/forwardevaluation.hpp](../../../QuantExt/qle/ad/forwardevaluation.hpp)

#### Model Integration
- [OREData/ored/scripting/models/modelcg.hpp](../../../OREData/ored/scripting/models/modelcg.hpp)
- [OREData/ored/scripting/models/gaussiancamcg.hpp](../../../OREData/ored/scripting/models/gaussiancamcg.hpp)

#### Pricing Engines
- [OREData/ored/scripting/engines/scriptedinstrumentpricingenginecg.cpp](../../../OREData/ored/scripting/engines/scriptedinstrumentpricingenginecg.cpp)
- [OREData/ored/scripting/engines/amccgbaseengine.hpp](../../../OREData/ored/scripting/engines/amccgbaseengine.hpp)

#### XVA Integration
- [OREAnalytics/orea/engine/xvaenginecg.hpp](../../../OREAnalytics/orea/engine/xvaenginecg.hpp)
- [OREAnalytics/orea/engine/xvaenginecg.cpp](../../../OREAnalytics/orea/engine/xvaenginecg.cpp)

#### Examples
- [Examples/Legacy/Example_56](../../../Examples/Legacy/Example_56/) - XVA with AAD
- [Examples/Legacy/Example_61](../../../Examples/Legacy/Example_61/) - Scripted trades with AAD
- [Examples/AmericanMonteCarlo](../../../Examples/AmericanMonteCarlo/) - Bermudan options with AMC-CG

### Online Resources

- **ORE Website**: http://opensourcerisk.org
- **GitHub Repository**: https://github.com/OpenSourceRisk/Engine
- **QuantLib**: http://quantlib.org

---

## Appendix: Quick Reference

### Key Configuration Parameters

| Parameter | Values | Description |
|-----------|--------|-------------|
| `UseCG` | true/false | Enable computation graph (required for AAD) |
| `UseAD` | true/false | Enable AAD sensitivities |
| `UseCachedSensis` | true/false | Cache AAD derivatives for bumps |
| `amcCg` | Disabled, CubeGeneration, Full | AMC-CG mode |
| `RegressionOrder` | 2-10 | Polynomial degree for AMC regression |
| `TrainingPaths` | 1000-10000 | Paths for AMC training |
| `BasisFunction` | Monomial, Hermite, Laguerre | AMC basis functions |

### Typical Use Cases

| Use Case | Configuration | Speedup |
|----------|--------------|---------|
| Scripted Trade NPV | `UseAD=false` | N/A (base) |
| Scripted Trade Sensitivities | `UseAD=true, UseCachedSensis=true` | **10-20×** |
| XVA Exposure Only | `amcCg=CubeGeneration` | ~1× (minimal overhead) |
| XVA with Sensitivities | `amcCg=Full, xvaCgSensitivityConfigFile=...` | **20-30×** |
| Bermudan Option | `UseAD=true, RegressionOrder=6` | **10-15×** |

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| "Computation graph disabled" | `UseCG=false` | Set `UseCG=true` |
| "AAD not available" | Engine doesn't support CG | Use scripted trade or AMC-CG engine |
| Out of memory | Large graph, no red blocks | Automatic in ORE; check `nThreads` |
| Slow AAD | Too many paths | Use `TrainingPaths` for AMC; reduce `Samples` |
| Wrong sensitivities | Missing Jacobian | Check `xvasensiconfig.xml` has all factors |

---

**Document Version**: 1.0
**Last Updated**: 2025-01-11
**ORE Version**: v13+
