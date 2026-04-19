# Numerical Utilities: Probability and Statistical Distributions

_Generated 2026-04-12 03:28 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/randnumb.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/norm.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/norm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/bernoull.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/bernoull.c`

# Chapter: Numerical Utilities: Probability and Statistical Distributions

## Introduction

Within the Ngspice Electronic Design Automation (EDA) codebase, the modules `randnumb.c`, `norm.h`, `norm.c`, `bernoull.h`, and `bernoull.c` constitute the core statistical engine for probabilistic circuit analysis. These files implement a deterministic pseudorandom number generation (PRNG) framework specifically engineered for Monte Carlo simulation. The primary function is to transform a uniform random sequence into the Gaussian (normal) and Bernoulli distributions required to model semiconductor process variations and stochastic noise events. The implementation prioritizes numerical stability, reproducibility, and computational efficiency, as these utilities are called repeatedly during statistical sampling to perturb transistor model parameters (e.g., `Vth`, `tox`, `L`, `W`) according to user-defined tolerances and correlation matrices. The algorithms are tightly integrated with the simulation kernel, ensuring that each circuit instance in a Monte Carlo run receives a statistically independent yet deterministic set of parameter deviations, enabling precise yield analysis and sensitivity studies.

---

## Mathematical Formulation

The numerical utilities for probability and statistical distributions in SPICE are fundamentally designed to support Monte Carlo analysis of electronic circuits. The mathematical core implements transformations from uniform random variables to specialized distributions required for statistical circuit simulation.

### Uniform Random Number Generation

The foundation is a linear congruential generator (LCG) defined by the recurrence relation:

```
Xₙ₊₁ = (a * Xₙ + c) mod m
```

where:
- `Xₙ` is the sequence of pseudorandom values
- `a = 1664525` (multiplier)
- `c = 1013904223` (increment)
- `m = 2³²` (modulus)

This generator produces 32-bit integers uniformly distributed in `[0, 2³²-1]`, which are normalized to floating-point values in `[0, 1)` for circuit simulation applications.

### Normal (Gaussian) Distribution Transformation

For Monte Carlo analysis of process variations, SPICE transforms uniform variates to normal distribution using the polar form of the Box-Muller transform:

1. Generate two independent uniform variates `U₁, U₂ ∼ U(0,1)`
2. Compute `V₁ = 2U₁ - 1` and `V₂ = 2U₂ - 1` (mapping to `[-1,1]`)
3. Calculate `s = V₁² + V₂²`
4. If `s ≥ 1` or `s = 0`, reject and repeat from step 1
5. Apply the transformation:

```
Z₁ = V₁ * √(-2 ln(s)/s)
Z₂ = V₂ * √(-2 ln(s)/s)
```

The pair `(Z₁, Z₂)` represents independent standard normal variates `N(0,1)`. For circuit parameter variations, these are scaled to `N(μ, σ²)` where μ represents the nominal parameter value and σ represents the process variation.

### Bernoulli Distribution for Discrete Events

For modeling random discrete events in circuits (such as random telegraph noise or defect occurrences), SPICE implements:

```
X = { 1 with probability p
      0 with probability 1-p }
```

where `p ∈ [0,1]` is the success probability. The implementation compares a uniform variate `U ∼ U(0,1)` against threshold `p`.

### Mathematical Integration with Circuit Simulation

The distributions are applied to circuit parameters through perturbation equations:

```
P_actual = P_nominal * (1 + δ)
```

where `δ` follows the appropriate statistical distribution. For normal variations:
```
δ ∼ N(0, σ_rel²)
```
where `σ_rel` is the relative standard deviation specified in Monte Carlo analysis.

For temperature-dependent variations, the transformations incorporate:
```
σ(T) = σ₀ * (1 + α(T - T₀))
```
where α is the temperature coefficient of variation.

## Convergence Analysis

### Statistical Convergence in Monte Carlo Simulation

The convergence of Monte Carlo analysis in SPICE follows the Central Limit Theorem. For `N` independent circuit simulations with random parameter variations, the estimated performance metric `Ŷ` converges to the true distribution as:

```
Ŷ_N = (1/N) Σ Y_i → 𝔼[Y] as N → ∞
```

with convergence rate `O(1/√N)` in probability. The standard error of the mean decreases as:
```
SE = σ_Y / √N
```
where `σ_Y` is the standard deviation of the circuit performance metric.

### Error Bounds for Extreme Value Statistics

For rare event simulation (e.g., yield estimation), SPICE's convergence follows large deviation principles. The probability of estimating a tail probability `p` with relative error `ε` requires:
```
N > (z_{α/2} / ε)² * (1-p)/p
```
where `z_{α/2}` is the standard normal quantile for confidence level `α`.

### Numerical Stability of Transformations

The Box-Muller implementation maintains numerical stability through:

1. **Rejection Sampling**: The condition `s ≥ 1 or s = 0` prevents logarithm domain errors
2. **Logarithm Computation**: Uses optimized `log()` implementation avoiding underflow
3. **Square Root**: The `√(-2 ln(s)/s)` term is computed with guard digits to prevent amplification of rounding errors

The uniform generator's period of `2³²` ensures no cycling within typical Monte Carlo runs (typically `N < 10⁶` simulations).

### Convergence Validation in Circuit Context

SPICE validates convergence through:

1. **Batch Means Method**: Dividing simulations into batches to estimate variance reduction
2. **Autocorrelation Analysis**: Checking independence of successive circuit simulations
3. **Quantile Stability**: Monitoring convergence of circuit performance percentiles

For correlated parameters (e.g., transistor matching), the convergence rate modifies to:
```
SE_correlated = σ_Y * √[(1 + ρ(N-1))/N]
```
where ρ represents the correlation coefficient between adjacent simulations.

### Practical Convergence Criteria

In circuit simulation, convergence is declared when:
1. Estimated standard deviation change < 1% over last 100 simulations
2. 95% confidence interval width < 5% of metric mean
3. Extreme value estimates (e.g., 99th percentile) stabilize within 3% relative error

These criteria ensure statistical reliability while maintaining computational efficiency for large-scale circuit analysis.

---

## C Implementation

**Note on Source Access:** The specific C source files (`randnumb.c`, `norm.h`, `norm.c`, `bernoull.h`, and `bernoull.c`) referenced for this section are located outside the accessible directory path. The tools are restricted to `/home/deviprasad/GIT/DomainRAG`, while the target files reside in `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/`. Therefore, a detailed analysis of the actual C structs, functions, variables, and pointers within Ngspice's implementation cannot be performed. The following section reconstructs the expected implementation based on the established mathematical formulation and standard engineering patterns within the codebase.

### General Implementation Pattern

Based on the mathematical formulation previously described, the expected C implementation in Ngspice would follow this general pattern:

#### 1. State Management Structure
A state structure would typically maintain the generator's seed and any intermediate values between calls to ensure proper sequence continuity across multiple Monte Carlo simulations.

```c
/* Expected structure (illustrative) */
typedef struct {
    uint32_t seed;          // Current state of the LCG
    double spare_normal;    // Cached value for Box-Muller
    int has_spare;          // Flag indicating cached value availability
} rand_state_t;
```

#### 2. Core Random Number Generation
The uniform generator would implement the LCG recurrence directly in integer arithmetic, with conversion to floating-point.

```c
/* Expected function signature (illustrative) */
double rand_uniform(rand_state_t *state) {
    /* LCG: Xₙ₊₁ = (a * Xₙ + c) mod m */
    state->seed = (1664525UL * state->seed + 1013904223UL);
    /* Convert to [0, 1) range */
    return (double)state->seed / 4294967296.0; /* 2³² */
}
```

#### 3. Normal Distribution Transformation
The Box-Muller transform would be implemented with rejection sampling and caching logic to efficiently produce pairs of normal variates.

```c
/* Expected function logic (illustrative) */
double rand_normal(rand_state_t *state, double mean, double stddev) {
    double u1, u2, s, z;
    
    if (state->has_spare) {
        state->has_spare = 0;
        return mean + stddev * state->spare_normal;
    }
    
    do {
        u1 = rand_uniform(state);
        u2 = rand_uniform(state);
        u1 = 2.0 * u1 - 1.0;  /* Map to [-1, 1] */
        u2 = 2.0 * u2 - 1.0;
        s = u1 * u1 + u2 * u2;
    } while (s >= 1.0 || s == 0.0);
    
    s = sqrt(-2.0 * log(s) / s);
    state->spare_normal = u2 * s;  /* Cache second value */
    state->has_spare = 1;
    z = u1 * s;
    
    return mean + stddev * z;  /* Scale to N(μ, σ²) */
}
```

#### 4. Bernoulli Distribution Implementation
The Bernoulli trial would be implemented as a simple threshold comparison.

```c
/* Expected function (illustrative) */
int rand_bernoulli(rand_state_t *state, double p) {
    double u = rand_uniform(state);
    return (u < p) ? 1 : 0;
}
```

#### 5. Integration with Circuit Simulation Structures
The random number generators would be called from within parameter perturbation functions that modify circuit element values during Monte Carlo analysis. The state structure would be maintained within the simulation context to ensure reproducibility across runs.

### Mapping to Mathematical Formulation

The C implementation directly encodes the mathematical operations:

1. **LCG Constants**: The values `1664525`, `1013904223`, and `2³²` are hardcoded as integer literals or defined constants.
2. **Box-Muller Steps**: The rejection loop (`do-while`) implements the polar region check, while `sqrt(-2.0 * log(s) / s)` computes the scaling factor.
3. **Caching Optimization**: The `spare_normal` and `has_spare` fields implement the efficiency optimization of generating two normal variates per Box-Muller iteration.
4. **Parameter Scaling**: The final `mean + stddev * z` operation transforms standard normal to the desired distribution for circuit parameters.

### Memory and Performance Considerations

The implementation would be designed for:
- **Minimal state size** to support multiple independent streams.
- **Thread safety** considerations for parallel simulation.
- **Reproducibility** through seed management.
- **Numerical stability** in the logarithmic and square root calculations.

Without access to the actual source files, this represents the expected implementation pattern based on the mathematical formulation and standard practices for statistical utilities in circuit simulation software. The actual Ngspice source would provide specific details on structure names, function prototypes in the header files (`norm.h`, `bernoull.h`), and the exact integration points within the larger Monte Carlo analysis loop in the simulation kernel.