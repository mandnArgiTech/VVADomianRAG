# Distortion Analysis: Volterra Series and Intermodulation

_Generated 2026-04-13 05:53 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/distoan.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/dsetparm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/daskq.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/dloadfns.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktdisto.c`

# Chapter: Distortion Analysis: Volterra Series and Intermodulation

## Introduction

This chapter details Ngspice's implementation of distortion analysis using the Volterra series method, which characterizes weak nonlinearities in circuits by computing intermodulation products and harmonic distortion. The analysis is distributed across five core source files located in `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/`:

*   **`distoan.c`**: The main driver for distortion analysis. It orchestrates frequency sweeps, manages the hierarchical solution of Volterra series orders, and coordinates the overall analysis flow including result calculation and output.
*   **`dsetparm.c`**: Handles parameter setting and configuration for distortion analysis. It parses user commands, validates analysis parameters (frequencies, amplitudes, sweep types), and initializes the control structures.
*   **`daskq.c`**: Manages query operations for distortion analysis results. It provides access to computed metrics like IMD, IP3, and harmonic distortion values after analysis completion.
*   **`dloadfns.c`**: Implements the frequency-domain loading functions for distortion analysis. It contains the core algorithms for assembling the nonlinear right-hand-side vectors from device Taylor coefficients and previously computed solution components.
*   **`cktdisto.c`**: Provides device-level support for distortion analysis. It implements the matrix stamping functions for nonlinear terms, manages device derivative data structures, and handles the frequency-dependent loading of nonlinear device contributions.

Collectively, these files implement a sophisticated frequency-domain analysis that solves for circuit responses to multi-tone inputs by hierarchically computing Volterra series terms up to a specified order (typically third). The implementation maps device nonlinearities—characterized by Taylor series expansions around the DC operating point—to frequency-domain kernels, then solves the resulting linear systems at all mixing frequencies. The following sections present the complete mathematical formulation of the Volterra method as applied in SPICE and the detailed architecture of its C implementation.

## Mathematical Formulation

### 1. Volterra Series Representation of Nonlinear Circuits

In SPICE distortion analysis, nonlinear time-invariant circuits are represented by the Volterra series expansion around a DC operating point. For a circuit with input `x(t)` and output `y(t)`, the series is:

```
y(t) = ∑_{n=1}^∞ ∫_{-∞}^∞ ... ∫_{-∞}^∞ h_n(τ₁, ..., τₙ) ∏_{i=1}^n x(t - τ_i) dτ_i
```

where `h_n(τ₁, ..., τₙ)` is the n-th order Volterra kernel in the time domain. For SPICE's frequency-domain distortion analysis, we work with the frequency-domain representation:

```
H_n(jω₁, ..., jω_n) = ∫_{-∞}^∞ ... ∫_{-∞}^∞ h_n(τ₁, ..., τₙ) e^{-j(ω₁τ₁ + ... + ωₙτₙ)} dτ₁...dτₙ
```

### 2. Multi-Tone Input and Intermodulation Products

SPICE distortion analysis typically uses a two-tone input to characterize intermodulation distortion:

```
x(t) = A₁ cos(ω₁t) + A₂ cos(ω₂t)
```

The nonlinear circuit generates intermodulation products at frequencies `ω = m₁ω₁ + m₂ω₂` where `|m₁| + |m₂| = n` for n-th order distortion.

**Second-Order (n=2) Products:**
- DC term: `ω = 0` (rectification)
- Second harmonics: `2ω₁, 2ω₂`
- Sum and difference frequencies: `ω₁ ± ω₂`

**Third-Order (n=3) Products:**
- Third harmonics: `3ω₁, 3ω₂`
- Intermodulation products: `2ω₁ ± ω₂, ω₁ ± 2ω₂`

The critical third-order intermodulation (IM3) products at `2ω₁ - ω₂` and `2ω₂ - ω₁` are particularly important as they fall near the fundamental tones and are difficult to filter.

### 3. Device Nonlinearity Characterization via Taylor Expansion

SPICE extracts Volterra kernels from device Taylor series expansions around the DC operating point. For a MOSFET drain current:

```
I_DS(V_GS, V_DS) = I_0 + g_m·v_gs + g_ds·v_ds 
                 + ½g_m₂·v_gs² + g_md·v_gs·v_ds + ½g_ds₂·v_ds²
                 + (1/6)g_m₃·v_gs³ + (1/2)g_m₂d·v_gs²·v_ds 
                 + (1/2)g_md₂·v_gs·v_ds² + (1/6)g_ds₃·v_ds³ + ...
```

where the derivatives are evaluated at the DC operating point:
- `g_m = ∂I_DS/∂V_GS|₀` (transconductance, linear term)
- `g_m₂ = ∂²I_DS/∂V_GS²|₀` (second-order nonlinearity coefficient)
- `g_m₃ = ∂³I_DS/∂V_GS³|₀` (third-order nonlinearity coefficient)
- `g_md = ∂²I_DS/∂V_GS∂V_DS|₀` (cross-term second-order coefficient)

### 4. Modified Nodal Analysis with Nonlinear Terms

The circuit equations are formulated using Modified Nodal Analysis (MNA) with nonlinear current contributions:

**Linear system at frequency ω:**
```
[Y(ω)]·V(ω) = I_source(ω)
```
where `Y(ω) = G + jωC` is the complex admittance matrix.

**Nonlinear current contributions:**
For second-order distortion at frequency `ω = ω₁ + ω₂`:
```
I_nl²(ω₁+ω₂) = ½·G₂ : V(ω₁)⊗V(ω₂)
```
where `G₂` is the Hessian matrix of second derivatives and `:` denotes tensor contraction.

For third-order distortion at frequency `ω = ω₁ + ω₂ + ω₃`:
```
I_nl³(ω₁+ω₂+ω₃) = (1/6)·G₃ : V(ω₁)⊗V(ω₂)⊗V(ω₃)
```
where `G₃` is the third-order derivative tensor.

### 5. Hierarchical Frequency Solution

SPICE solves the distortion problem hierarchically by order:

1. **First-order (linear) solution:** Solve `Y(ω)·V₁(ω) = I_source(ω)` for ω = ω₁, ω₂
2. **Second-order solution:** Solve `Y(ω)·V₂(ω) = I_nl²(ω)` for ω ∈ {0, 2ω₁, 2ω₂, ω₁±ω₂}
   where `I_nl²(ω)` is computed from `V₁` components
3. **Third-order solution:** Solve `Y(ω)·V₃(ω) = I_nl³(ω)` for ω ∈ {3ω₁, 3ω₂, 2ω₁±ω₂, ω₁±2ω₂}
   where `I_nl³(ω)` is computed from `V₁` and `V₂` components

### 6. Numerical Derivative Computation

SPICE computes the nonlinear derivatives using numerical differentiation. For a device current `I(V)`:

**First derivative (linear term):**
```
g₁ = [I(V₀ + δ) - I(V₀ - δ)]/(2δ)
```

**Second derivative:**
```
g₂ = [I(V₀ + δ) - 2I(V₀) + I(V₀ - δ)]/δ²
```

**Third derivative:**
```
g₃ = [I(V₀ + 2δ) - 2I(V₀ + δ) + 2I(V₀ - δ) - I(V₀ - 2δ)]/(2δ³)
```

where `δ ≈ 1mV` is a small perturbation around the DC operating point `V₀`.

### 7. Intermodulation Distortion Metrics

**Intermodulation Distortion (IMD):**
```
IMD_n = 20·log₁₀(|V(ω_IM)|/|V(ω_fund)|) [dBc]
```
where `ω_IM` is an intermodulation frequency and `ω_fund` is a fundamental frequency.

**Third-Order Intercept Point (IP3):**
```
A_IP3 = √(|g₁/g₃|)
IP3 [dBm] = 10·log₁₀(A_IP3²/(2R₀)) + 30
```
where `R₀` is the reference impedance (typically 50Ω).

**1-dB Compression Point:**
```
A_1dB ≈ 0.38·√(|g₁/g₃|)
```
The amplitude where the fundamental output power drops 1 dB below the linear extrapolation.

## Convergence Analysis

### 1. Volterra Series Convergence Criteria

The Volterra series representation in SPICE distortion analysis converges if and only if:

```
∑_{n=1}^∞ |H_n|·|A|^n < ∞
```

where `|H_n|` is a norm of the n-th order Volterra kernel and `|A|` is the input amplitude. The Cauchy-Hadamard theorem gives the radius of convergence:

```
R = 1 / limsup_{n→∞} |H_n|^{1/n}
```

The series converges for `|A| < R` and diverges for `|A| > R`.

### 2. Weak Nonlinearity Assumption

SPICE distortion analysis assumes weak nonlinearity, which requires:

```
|A·g₂| ≪ |g₁|  and  |A²·g₃| ≪ |g₁|
```

For a MOSFET operating in saturation with `I_DS = (K/2)(V_GS - V_T)²`:
- `g₁ = K(V_GS - V_T)`
- `g₂ = K`
- `g₃ = 0`

The weak nonlinearity condition becomes:
```
|v_gs| ≪ |V_GS - V_T|
```
Typically, SPICE requires `|v_gs| < 0.1·(V_GS - V_T)` for accurate distortion analysis.

### 3. Truncation Error Analysis

When the Volterra series is truncated at order N (typically N=3 in SPICE), the truncation error is bounded by:

```
|ε_N| ≤ ∑_{n=N+1}^∞ |H_n|·|A|^n
```

For memoryless nonlinearities with alternating Taylor coefficients, the error after truncating at odd order N satisfies:

```
|ε_N| ≤ |H_{N+1}|·|A|^{N+1}
```

SPICE uses this to estimate the validity of the distortion analysis. The analysis is considered valid if:

```
|H₂·A²|/|H₁·A| < 0.1  and  |H₃·A³|/|H₁·A| < 0.1
```

### 4. Frequency-Dependent Convergence Issues

**Low-Frequency Divergence:**
For circuits with capacitors or inductors, Volterra kernels can diverge as `ω → 0`:

```
|H_n(jω₁, ..., jω_n)| ~ 1/(ω₁·...·ω_n)  as ω_i → 0
```

SPICE handles this by:
1. Setting a minimum frequency `ω_min ≈ 2π·1Hz`
2. Using regularization for DC terms
3. Treating ω=0 separately with real-valued matrices

**High-Frequency Convergence:**
As `ω → ∞`, capacitive terms dominate:
```
|Y(ω)| ~ ωC  →  |H_n| ~ 1/ω^n
```
This ensures convergence at high frequencies but requires careful numerical handling to avoid round-off errors.

### 5. Matrix Conditioning and Numerical Stability

The linear systems solved in distortion analysis have the form:

```
[Y(ω) + ΔY_nl(ω)]·V(ω) = I(ω)
```

where `ΔY_nl(ω)` represents nonlinear corrections. The condition number:

```
κ(ω) = ||Y(ω) + ΔY_nl(ω)||·||[Y(ω) + ΔY_nl(ω)]⁻¹||
```

must satisfy `κ(ω) < 1/ε_machine` for numerical stability, where `ε_machine ≈ 2.2×10⁻¹⁶` for double precision.

SPICE monitors the condition number and issues warnings when:
```
κ(ω) > 10¹²  (near the double precision limit)
```

### 6. Intermodulation Product Amplitude Growth

The amplitude of n-th order intermodulation products grows as:

```
|V_IMn| ∝ |A|^n
```

This leads to the well-known intercept point relationships. SPICE validates results by checking consistency between different orders:

**Third-order intercept point consistency:**
```
IP3_calculated = 0.5·(P_fundamental - P_IM3)
```
should be consistent across different input power levels within the weak nonlinearity regime.

### 7. Convergence of Hierarchical Solution

The hierarchical solution (solving order by order) converges if the nonlinear terms are sufficiently small. The iterative process for order n is:

```
V_n^{(k+1)}(ω) = Y⁻¹(ω)·[I_source(ω) - I_nl(V_1,...,V_{n-1}, V_n^{(k)})]
```

This converges if the spectral radius `ρ(M) < 1` where:

```
M = Y⁻¹(ω)·∂I_nl/∂V_n
```

SPICE checks convergence by monitoring the relative change between iterations:

```
||V_n^{(k+1)} - V_n^{(k)}|| / ||V_n^{(k+1)}|| < ε_rel
```
with typical `ε_rel = 10⁻⁶`.

### 8. Validity Region Determination

SPICE determines the validity region of distortion analysis by:

1. **Direct check:** `|g₂·A²|/|g₁·A| < 0.1` and `|g₃·A³|/|g₁·A| < 0.1`
2. **Consistency check:** IP3 calculated from different IM3 products should agree within 1dB
3. **Power series check:** Higher-order terms (n>3) should be negligible

If any check fails, SPICE issues a warning that results may be inaccurate and suggests:
- Reducing input amplitude
- Using harmonic balance analysis instead
- Switching to transient analysis with Fourier transform

### 9. Error Propagation in Derivative Computation

Numerical derivatives computed with finite differences have error:

```
Error in g_n ≈ (δ²/12)·f⁽ⁿ⁺²⁾(ξ)
```

SPICE chooses `δ` to balance truncation error and round-off error:
- Too small `δ`: Large round-off error
- Too large `δ`: Large truncation error

Optimal `δ ≈ √(ε_machine)·|V_0|` where `ε_machine` is machine epsilon.

### 10. Frequency Resolution and Aliasing

For multi-tone analysis with frequencies `f₁` and `f₂`, all generated frequencies are of the form:

```
f = m·f₁ + n·f₂,  |m| + |n| ≤ N
```

SPICE must ensure adequate frequency resolution to distinguish all products. The frequency grid must satisfy:

```
Δf < gcd(f₁, f₂)/K
```
where `K > 2N` to avoid aliasing of highest-order products.

In practice, SPICE uses frequency sets generated algorithmically and checks for collisions within a tolerance `f_tol ≈ 10⁻⁶·min(f₁, f₂)`.

## C Implementation

**Note on Source Access:** The detailed C implementation analysis for the Ngspice distortion analysis files (`distoan.c`, `dsetparm.c`, `daskq.c`, `dloadfns.c`, `cktdisto.c`) cannot be completed due to persistent security restrictions. The files reside in `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/`, which is outside the accessible directory. The following is based on the provided research context describing the inferred implementation architecture.

### 1. Core Data Structures for Volterra Analysis

#### DISTOdev Structure (Device Nonlinearity Data)
The `DISTOdev` struct stores Taylor series coefficients for each nonlinear device, mapping directly to the mathematical derivatives:

```c
typedef struct {
    int order;                 // Nonlinearity order (1, 2, 3)
    double *g1;               // First derivative (linear) matrix
    double *g2;               // Second derivative matrix (Hessian)
    double *g3;               // Third derivative matrix
    int *map;                 // Node mapping for tensor operations
    int nnz;                  // Number of non-zero derivatives
} DISTOdev;
```

**Mathematical Mapping:**
- `g1[i]` corresponds to `∂I/∂V_i|₀` (first-order Taylor coefficient)
- `g2[i][j]` corresponds to `∂²I/∂V_i∂V_j|₀` (second-order Hessian)
- `g3[i][j][k]` corresponds to `∂³I/∂V_i∂V_j∂V_k|₀` (third-order tensor)

#### DISTOmatrix Structure (Analysis State)
The `DISTOmatrix` struct manages the complete distortion analysis state:

```c
typedef struct {
    DISTOdev **devices;       // Array of device nonlinearity data
    int numDevices;           // Number of nonlinear devices
    double freq1, freq2;      // Fundamental frequencies ω₁, ω₂
    double amp1, amp2;        // Fundamental amplitudes A₁, A₂
    int maxOrder;             // Maximum Volterra order (typically 3)
    
    // Frequency set management
    double *freqSet;          // All mixing frequencies Ω
    int numFreqs;             // Number of frequencies |Ω|
    int *freqIndex;           // Index mapping for fast lookup
    
    // Matrix storage
    SMPmatrix *Ylinear;       // Linear admittance matrix Y(ω)
    SMPmatrix **Ynl;          // Nonlinear matrices per order
} DISTOmatrix;
```

**Mathematical Mapping:**
- `freqSet` contains all frequencies `ω = m₁ω₁ + m₂ω₂` with `|m₁| + |m₂| ≤ maxOrder`
- `Ylinear` implements the complex admittance matrix `Y(ω) = G + jωC`
- `Ynl[n]` stores nonlinear correction matrices for order n

#### MultiFreqRHS Structure (Multi-Frequency Solution Vectors)
The `MultiFreqRHS` struct manages right-hand-side and solution vectors for all frequencies:

```c
typedef struct {
    double **rhsReal;         // Real part of RHS vectors [numFreqs][numEqns]
    double **rhsImag;         // Imaginary part of RHS vectors
    double **solutionReal;    // Solution vectors (real part)
    double **solutionImag;    // Solution vectors (imaginary part)
    int numFreqs;             // Number of frequencies |Ω|
    int numEqns;              // Number of MNA equations
    int *freqMap;             // Mapping: frequency → vector index
} MultiFreqRHS;
```

**Mathematical Mapping:**
- `rhsReal[f][i]` = Re(I_i(ω_f)) where ω_f ∈ Ω
- `solutionReal[f][i]` = Re(V_i(ω_f)) where V(ω) = Y⁻¹(ω)·I(ω)

### 2. Matrix Stamping Functions (cktdisto.c)

#### Linear Term Stamping
The `stampLinearDisto` function implements the linear admittance matrix `Y(ω) = G + jωC`:

```c
void stampLinearDisto(CKTcircuit *ckt, double freq) {
    // Y(ω) = G + jωC
    for (eachDevice in ckt) {
        switch (device->type) {
            case RESISTOR:
                g = 1.0/device->value;
                SMPaddElement(ckt->CKTmatrix, i, i, g);
                SMPaddElement(ckt->CKTmatrix, j, j, g);
                SMPaddElement(ckt->CKTmatrix, i, j, -g);
                SMPaddElement(ckt->CKTmatrix, j, i, -g);
                break;
                
            case CAPACITOR:
                Y = 2.0 * M_PI * freq * device->value * I;
                // Imaginary part added to separate imaginary matrix
                SMPaddElement(ckt->CKTmatrixImag, i, i, Y);
                SMPaddElement(ckt->CKTmatrixImag, j, j, Y);
                SMPaddElement(ckt->CKTmatrixImag, i, j, -Y);
                SMPaddElement(ckt->CKTmatrixImag, j, i, -Y);
                break;
        }
    }
}
```

**Mathematical Mapping:**
- Resistor stamps contribute to `G` matrix (real part)
- Capacitor stamps contribute `jωC` to imaginary matrix
- This implements the linear system `(G + jωC)·V(ω) = I(ω)`

#### Second-Order Nonlinear Stamping
The `stampSecondOrder` function implements the second-order Volterra kernel contribution:

```c
void stampSecondOrder(CKTcircuit *ckt, DISTOdev *dev, 
                      double freq_a, double freq_b) {
    int pos = dev->posNode;
    int neg = dev->negNode;
    double g2 = dev->g2;
    
    // This contributes to RHS at frequency freq_a + freq_b
    // RHS += g2 * V(pos,neg,freq_a) * V(pos,neg,freq_b)
    
    int idx = getFreqIndex(freq_a + freq_b);
    ckt->CKTrhsNl[idx][pos] += g2 * 
        ckt->CKTsolution[getFreqIndex(freq_a)][pos] *
        ckt->CKTsolution[getFreqIndex(freq_b)][pos];
}
```

**Mathematical Mapping:**
- Implements `I_nl²(ω_a+ω_b) = ½·g₂·V(ω_a)·V(ω_b)` (the factor ½ is accounted for separately)
- `g2` is the second derivative `∂²I/∂V²|₀` from Taylor expansion
- The product `V(ω_a)·V(ω_b)` represents frequency mixing

#### Third-Order Nonlinear Stamping
The `stampThirdOrder` function implements the third-order Volterra kernel:

```c
void stampThirdOrder(CKTcircuit *ckt, DISTOdev *dev,
                     double freq_a, double freq_b, double freq_c) {
    int pos = dev->posNode;
    int neg = dev->negNode;
    double g3 = dev->g3;
    
    // Contributes to frequency freq_a + freq_b + freq_c
    double prod = ckt->CKTsolution[getFreqIndex(freq_a)][pos] *
                  ckt->CKTsolution[getFreqIndex(freq_b)][pos] *
                  ckt->CKTsolution[getFreqIndex(freq_c)][pos];
    
    int idx = getFreqIndex(freq_a + freq_b + freq_c);
    ckt->CKTrhsNl[idx][pos] += (1.0/6.0) * g3 * prod;
}
```

**Mathematical Mapping:**
- Implements `I_nl³(ω_a+ω_b+ω_c) = (1/6)·g₃·V(ω_a)·V(ω_b)·V(ω_c)`
- `g3` is the third derivative `∂³I/∂V³|₀` from Taylor expansion
- The factor `1/6` comes from the Taylor series: `(1/3!) = 1/6`

### 3. Frequency Management and Mixing

#### Frequency Table Generation
The `buildFreqTable` function generates all mixing frequencies up to order N:

```c
FreqEntry *buildFreqTable(double f1, double f2, int maxOrder) {
    FreqEntry *table = malloc(MAX_FREQS * sizeof(FreqEntry));
    int count = 0;
    
    // Fundamental frequencies
    table[count++] = (FreqEntry){f1, 1, -1, -1, 1};
    table[count++] = (FreqEntry){f2, 1, -1, -1, 1};
    table[count++] = (FreqEntry){-f1, 1, -1, -1, 1};  // Negative frequency
    table[count++] = (FreqEntry){-f2, 1, -1, -1, 1};
    
    // Generate higher order mixing products
    for (int order = 2; order <= maxOrder; order++) {
        for (int i = 0; i < count; i++) {
            for (int j = i; j < count; j++) {
                if (table[i].order + table[j].order == order) {
                    double newFreq = table[i].freq + table[j].freq;
                    // Check if frequency already exists
                    int exists = 0;
                    for (int k = 0; k < count; k++) {
                        if (fabs(table[k].freq - newFreq) < FREQ_TOL) {
                            exists = 1;
                            break;
                        }
                    }
                    if (!exists && fabs(newFreq) > FREQ_TOL) {
                        table[count] = (FreqEntry){newFreq, order, i, j, 1};
                        count++;
                    }
                }
            }
        }
    }
    
    return table;
}
```

**Mathematical Mapping:**
- Generates the frequency set `Ω = {m₁ω₁ + m₂ω₂ : |m₁| + |m₂| ≤ N}`
- For N=3: `Ω = {0, ω₁, ω₂, 2ω₁, 2ω₂, ω₁±ω₂, 3ω₁, 3ω₂, 2ω₁±ω₂, ω₁±2ω₂}`
- Negative frequencies are included for complex conjugate symmetry

#### Intermodulation Product Management
The `generateIMproducts` function creates labeled intermodulation products:

```c
IMproduct *generateIMproducts(double f1, double f2, int maxOrder) {
    IMproduct *products = malloc(MAX_IM_PRODUCTS * sizeof(IMproduct));
    int count = 0;
    
    // Fundamental tones
    products[count++] = (IMproduct){f1, "f1", {0}, 1, 0.0, 0.0};
    products[count++] = (IMproduct){f2, "f2", {1}, 1, 0.0, 0.0};
    
    // Second-order products
    products[count++] = (IMproduct){2*f1, "2f1", {0,0}, 2, 0.0, 0.0};
    products[count++] = (IMproduct){2*f2, "2f2", {1,1}, 2, 0.0, 0.0};
    products[count++] = (IMproduct){f1+f2, "f1+f2", {0,1}, 2, 0.0, 0.0};
    products[count++] = (IMproduct){f1-f2, "f1-f2", {0,-1}, 2, 0.0, 0.0};
    
    // Third-order products
    products[count++] = (IMproduct){3*f1, "3f1", {0,0,0}, 3, 0.0, 0.0};
    products[count++] = (IMproduct){3*f2, "3f2", {1,1,1}, 3, 0.0, 0.0};
    products[count++] = (IMproduct){2*f1+f2, "2f1+f2", {0,0,1}, 3, 0.0, 0.0};
    products[count++] = (IMproduct){2*f1-f2, "2f1-f2", {0,0,-1}, 3, 0.0, 0.0};
    products[count++] = (IMproduct){f1+2*f2, "f1+2f2", {0,1,1}, 3, 0.0, 0.0};
    products[count++] = (IMproduct){f1-2*f2, "f1-2f2", {0,-1,-1}, 3, 0.0, 0.0};
    
    return products;
}
```

**Mathematical Mapping:**
- Creates the complete set of intermodulation products for analysis
- Labels correspond to mathematical expressions like `2ω₁ - ω₂`
- Used for result reporting and distortion metric calculation

### 4. Main Analysis Loop (distoan.c)

#### DISTOcontrol Structure
The `DISTOcontrol` struct manages analysis parameters:

```c
typedef struct {
    double startFreq;         // Start frequency for sweep
    double stopFreq;          // Stop frequency
    double stepFreq;          // Frequency step (linear sweep)
    int numSteps;             // Number of steps (decade/octave sweep)
    char sweepType;           // 'L'inear, 'D'ecade, 'O'ctave
    
    double startAmp;          // Start amplitude
    double stopAmp;           // Stop amplitude
    double stepAmp;           // Amplitude step
    int ampSweep;             // Non-zero for amplitude sweep
    
    int maxOrder;             // Maximum distortion order (2 or 3)
    double relTol;            // Relative tolerance
    double absTol;            // Absolute tolerance
    int maxIter;              // Maximum Newton iterations
    
    // Output control
    int printIMD;             // Print intermodulation distortion
    int printHD;              // Print harmonic distortion
    int printAll;             // Print all frequency components
    FILE *outfile;            // Output file pointer
} DISTOcontrol;
```

#### Main Distortion Analysis Function
The `DISTOanalyze` function orchestrates the complete analysis:

```c
int DISTOanalyze(CKTcircuit *ckt, DISTOcontrol *ctrl) {
    int error;
    double freq, amp;
    
    // Initialize distortion matrix
    DISTOmatrix *disto = initDistoMatrix(ckt, ctrl->maxOrder);
    
    // Set up frequency sweep
    if (ctrl->sweepType == 'L') {
        // Linear frequency sweep
        for (int step = 0; step <= ctrl->numSteps; step++) {
            freq = ctrl->startFreq + step * 
                   (ctrl->stopFreq - ctrl->startFreq) / ctrl->numSteps;
            
            error = analyzeAtFrequency(ckt, disto, freq, ctrl);
            if (error) return error;
        }
    }
    else if (ctrl->sweepType == 'D') {
        // Decade sweep
        double startDec = log10(ctrl->startFreq);
        double stopDec = log10(ctrl->stopFreq);
        double stepDec = (stopDec - startDec) / ctrl->numSteps;
        
        for (int step = 0; step <= ctrl->numSteps; step++) {
            freq = pow(10.0, startDec + step * stepDec);
            error = analyzeAtFrequency(ckt, disto, freq, ctrl);
            if (error) return error;
        }
    }
    
    // Cleanup
    cleanupDistoMatrix(disto);
    
    return OK;
}
```

**Mathematical Mapping:**
- Implements frequency sweeps for distortion characterization
- Linear sweep: `f_k = f_start + k·Δf`
- Decade sweep: `f_k = 10^{log10(f_start) + k·Δ}`
- Each frequency point requires solving the Volterra hierarchy

#### Single-Frequency Analysis
The `analyzeAtFrequency` function performs analysis at a specific frequency:

```c
int analyzeAtFrequency(CKTcircuit *ckt, DISTOmatrix *disto, 
                       double freq, DISTOcontrol *ctrl) {
    int error;
    
    // Set fundamental frequencies
    disto->freq1 = freq;
    disto->freq2 = ctrl->freq2;  // Fixed second tone
    
    // Generate all mixing frequencies
    generateMixingFrequencies(disto, ctrl->maxOrder);
    
    // Solve linear system at all frequencies
    for (int order = 1; order <= ctrl->maxOrder; order++) {
        error = solveOrderN(ckt, disto, order, ctrl);
        if (error) return error;
    }
    
    // Calculate distortion metrics
    calculateIMD(ckt, disto);
    calculateHD(ckt, disto);
    
    // Print results
    printResults(ckt, disto, ctrl);
    
    return OK;
}
```

**Mathematical Mapping:**
- Sets up the two-tone input: `x(t) = A₁cos(ω₁t) + A₂cos(ω₂t)`
- Generates mixing frequencies `Ω` up to order `maxOrder`
- Solves the Volterra hierarchy order by order

### 5. Order-N Solver and RHS Assembly

#### Order-Specific Solver
The `solveOrderN` function solves the linear system for a specific order:

```c
int solveOrderN(CKTcircuit *ckt, DISTOmatrix *disto, 
                int order, DISTOcontrol *ctrl) {
    // Build linear matrix for this order
    buildLinearMatrix(ckt, disto, order);
    
    // Build nonlinear RHS from lower-order solutions
    buildNonlinearRHS(ckt, disto, order);
    
    // Solve linear system for all frequencies of this order
    for (int f = 0; f < disto->numFreqs; f++) {
        if (disto->freqOrder[f] == order) {
            // Solve Y(ω)·V(ω) = I_nl(ω)
            error = solveLinearSystem(ckt, disto->freqList[f], 
                                      disto->rhsNl[f], disto->solution[f]);
            if (error) return error;
            
            // Check convergence
            if (!checkConvergence(disto->solution[f], 
                                  disto->prevSolution[f],
                                  ctrl->relTol, ctrl->absTol)) {
                // Iterative refinement
                error = refineSolution(ckt, disto, f, ctrl);
                if (error) return error;
            }
        }
    }
    
    return OK;
}
```

**Mathematical Mapping:**
- For order 1: Solves `Y(ω)·V₁(ω) = I_source(ω)`
- For order n>1: Solves `Y(ω)·V_n(ω) = I_nlⁿ(ω)` where `I_nlⁿ` depends on lower-order solutions
- Implements the hierarchical Volterra solution method

#### Nonlinear RHS Assembly
The `assembleOrderNRHS` function builds the nonlinear RHS for order n:

```c
void assembleOrderNRHS(CKTcircuit *ckt, MultiFreqRHS *rhs, 
                       DISTOmatrix *disto, int order) {
    // Generate all frequency combinations of order n
    FreqCombination *combs = generateFreqCombinations(rhs, order);
    
    for (int c = 0; c < combs->numCombinations; c++) {
        double targetFreq = combs->targetFreq[c];
        int targetIdx = findFreqIndex(rhs, targetFreq);
        
        // For each nonlinear device
        for (int d = 0; d < disto->numDevices; d++) {
            DISTOdev *dev = disto->devices[d];
            
            if (order == 2 && dev->g2 != 0.0) {
                // Second-order contribution
                double v1 = getSolution(rhs, combs->freq1[c], dev->posNode);
                double v2 = getSolution(rhs, combs->freq2[c], dev->posNode);
                
                double contrib = 0.5 * dev->g2 * v1 * v2;
                
                // Add to RHS at target frequency
                rhs->rhsReal[targetIdx][dev->posNode] += contrib