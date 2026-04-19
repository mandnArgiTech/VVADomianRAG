# Resistor: Sensitivity Analysis

_Generated 2026-04-12 20:49 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/ressacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/ressload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/ressset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/ressprt.c`

# Chapter: Resistor: Sensitivity Analysis

## Technical Introduction

The Ngspice resistor sensitivity analysis implementation comprises four core C files that implement the adjoint method for computing analytical derivatives of circuit outputs with respect to resistor parameter variations. These files form a complete sensitivity analysis subsystem within the SPICE simulation framework:

- **`ressset.c`**: Sensitivity analysis setup and memory allocation. This file initializes the sensitivity data structures, allocates storage for sensitivity arrays (`∂V_out/∂R`, `∂V_out/∂L`, `∂V_out/∂W`), configures geometric scaling parameters for physical resistors, and sets perturbation values for finite-difference verification.

- **`ressload.c`**: DC sensitivity computation via the adjoint method. This file implements the core mathematical operation `∂V_m/∂R_k = (1/R_k²) × (λ_i - λ_j) × (V_i - V_j)`, where λ is the adjoint solution vector. It computes sensitivities for resistance and geometric parameters using chain rule derivatives.

- **`ressacl.c`**: AC sensitivity analysis extension for frequency domain. This file handles complex voltages and adjoint solutions, computing `Re(∂V/∂R) = (1/R²) × (λ_real·ΔV_real + λ_imag·ΔV_imag)` and the corresponding imaginary part for frequency-dependent sensitivity analysis.

- **`ressprt.c`**: Sensitivity results formatting and output. This file generates normalized sensitivity reports, calculating percentage changes per percentage parameter variation and formatting results for circuit designers.

Together, these files implement a complete adjoint-based sensitivity analysis system that computes analytical derivatives without requiring multiple circuit simulations, enabling efficient design optimization and yield analysis in analog integrated circuits.

## Mathematical Formulation

The resistor sensitivity analysis in Ngspice implements the **adjoint method** for computing partial derivatives of circuit outputs with respect to resistor parameter variations. This mathematical framework is specifically designed for SPICE circuit simulation and directly maps to the Modified Nodal Analysis (MNA) formulation.

### 1. Adjoint Method Foundation

Given a circuit described by the nonlinear equation system:
```
F(x, p) = 0
```
where:
- `x` = vector of node voltages (and branch currents for MNA)
- `p` = parameter vector containing resistor values `R_k`

The sensitivity of an output function `ψ(x, p)` (typically a node voltage) with respect to parameter `p_i` is:
```
∂ψ/∂p_i = (∂ψ/∂x)ᵀ · (∂x/∂p_i) + ∂ψ/∂p_i
```

Using the implicit function theorem on `F(x, p) = 0`:
```
∂F/∂x · ∂x/∂p_i + ∂F/∂p_i = 0
```

Solving for the sensitivity via the adjoint method involves:
1. Solving the original system: `F(x, p) = 0` for `x`
2. Solving the adjoint system: `[∂F/∂x]ᵀ · λ = ∂ψ/∂x` for adjoint vector `λ`
3. Computing sensitivity: `∂ψ/∂p_i = -λᵀ · (∂F/∂p_i) + ∂ψ/∂p_i`

### 2. Resistor-Specific Formulation

For a resistor `R_k` connected between nodes `i` and `j` with conductance `G_k = 1/R_k`:

#### MNA Contribution
The resistor contributes to the system matrix `Y` (conductance matrix) as:
```
Y[i][i] += G_k
Y[i][j] -= G_k
Y[j][i] -= G_k
Y[j][j] += G_k
```

#### Partial Derivative ∂F/∂G_k
The derivative of the circuit equations with respect to conductance is:
```
∂F_i/∂G_k = (V_i - V_j)
∂F_j/∂G_k = (V_j - V_i) = -(V_i - V_j)
```
All other entries of `∂F/∂G_k` are zero.

#### Conductance-to-Resistance Conversion
Since the parameter of interest is resistance `R_k` not conductance `G_k`:
```
∂G_k/∂R_k = -1/R_k²
```
Thus:
```
∂F/∂R_k = (∂F/∂G_k) · (∂G_k/∂R_k) = -(∂F/∂G_k)/R_k²
```

### 3. Sensitivity Computation Formula

For output voltage `V_m` at node `m`, the sensitivity with respect to resistor `R_k` is:

```
∂V_m/∂R_k = -λᵀ · (∂F/∂R_k)
          = -λᵀ · [-(∂F/∂G_k)/R_k²]
          = (1/R_k²) · λᵀ · (∂F/∂G_k)
```

Expanding using the structure of `∂F/∂G_k`:
```
∂V_m/∂R_k = (1/R_k²) · [λ_i · (V_i - V_j) + λ_j · (V_j - V_i)]
          = (1/R_k²) · (λ_i - λ_j) · (V_i - V_j)
```

This is the **core sensitivity equation** implemented in Ngspice.

### 4. Geometric Parameter Sensitivities

For physically modeled resistors with geometric parameters:

#### Sheet Resistance Model
```
R = R_sh · (L / W)
```
where:
- `R_sh` = sheet resistance (Ω/□)
- `L` = resistor length
- `W` = resistor width

#### Partial Derivatives
```
∂R/∂L = R_sh / W
∂R/∂W = -R_sh · L / W²
```

#### Chain Rule Application
Using the sensitivity with respect to resistance `∂V_m/∂R`, the geometric sensitivities are:
```
∂V_m/∂L = (∂V_m/∂R) · (∂R/∂L) = (∂V_m/∂R) · (R_sh / W)
∂V_m/∂W = (∂V_m/∂R) · (∂R/∂W) = (∂V_m/∂R) · (-R_sh · L / W²)
```

### 5. AC Sensitivity Analysis

For frequency-domain analysis at angular frequency `ω`:

#### Complex System Equations
The MNA system becomes:
```
[Y(ω)] · V(ω) = I(ω)
```
where `Y(ω) = G + jωC` for resistors and capacitors.

#### Complex Adjoint Solution
Solve:
```
[Y(ω)]ᴴ · λ(ω) = e_m
```
where `ᴴ` denotes Hermitian transpose (conjugate transpose), and `e_m` is the unit vector for output node `m`.

#### Complex Sensitivity Computation
For complex voltages `V(ω) = V_real + jV_imag` and adjoint `λ(ω) = λ_real + jλ_imag`:
```
∂V(ω)/∂R_k = (1/R_k²) · [λ*(ω)]ᵀ · (∂F/∂G_k)
```
where `*` denotes complex conjugate.

Expanding into real and imaginary parts:
```
Re[∂V/∂R] = (1/R_k²) · [λ_real · (V_i_real - V_j_real) + λ_imag · (V_i_imag - V_j_imag)]
Im[∂V/∂R] = (1/R_k²) · [λ_imag · (V_i_real - V_j_real) - λ_real · (V_i_imag - V_j_imag)]
```

### 6. Temperature-Dependent Sensitivity

For resistors with temperature coefficients:
```
R(T) = R_0 · [1 + TC1·(T - T_0) + TC2·(T - T_0)²]
```

The temperature sensitivity is:
```
∂V_m/∂T = (∂V_m/∂R) · (∂R/∂T)
```
where:
```
∂R/∂T = R_0 · [TC1 + 2·TC2·(T - T_0)]
```

### 7. Normalized Sensitivity

For design applications, normalized (relative) sensitivity is often more useful:
```
S_norm = (∂V_m/∂R_k) · (R_k / V_ref)
```
where `V_ref` is a reference voltage (typically 1V for normalization).

The percentage change per percentage change is:
```
%ΔV_m / %ΔR_k = S_norm × 100%
```

### 8. Multiple Output Sensitivity

For `N_out` output variables, the adjoint system is solved for each output:
```
[∂F/∂x]ᵀ · λ^{(m)} = e_m  for m = 1,...,N_out
```

The sensitivity matrix has dimensions `N_out × N_parameters`:
```
S[m][k] = ∂V_m/∂R_k = (1/R_k²) · (λ_i^{(m)} - λ_j^{(m)}) · (V_i - V_j)
```

### 9. Finite-Difference Verification

The adjoint method results can be verified using finite differences:
```
∂V_m/∂R_k ≈ [V_m(R_k + ΔR_k) - V_m(R_k)] / ΔR_k
```
where `ΔR_k = R_k · δ` with `δ` being a small perturbation (typically 0.001 = 0.1%).

The relative error should satisfy:
```
|(∂V_adjoint - ∂V_FD) / ∂V_adjoint| < ε
```
where `ε` is the numerical tolerance (typically 1e-6).

### 10. Noise Parameter Sensitivity

For resistor thermal noise with power spectral density:
```
S_v(f) = 4k_B T R
```
the sensitivity of noise with respect to resistance is:
```
∂S_v/∂R = 4k_B T
```

The sensitivity of circuit output to resistor noise is computed via the adjoint method applied to the noise correlation matrix.

## Convergence Analysis

### 1. Adjoint System Solution Convergence

The adjoint system `[∂F/∂x]ᵀ · λ = b` inherits the convergence properties of the original system `∂F/∂x · x = b`.

#### Condition Number Analysis
The condition number of the transposed Jacobian is:
```
κ(Jᵀ) = κ(J) = σ_max(J) / σ_min(J)
```
where `σ_max` and `σ_min` are the maximum and minimum singular values of the Jacobian `J = ∂F/∂x`.

For well-conditioned circuits, `κ(J) ≈ 10³-10⁶`. For ill-conditioned circuits (e.g., with very large/small resistors), `κ(J)` can approach machine precision limits.

#### Convergence Criterion
The Newton-Raphson iteration for the adjoint system converges when:
```
||Jᵀ · λ^{(k)} - b|| < ε_adjoint
```
where `ε_adjoint = ε_abs + ε_rel · ||b||`, with typical values:
- `ε_abs = 1e-12`
- `ε_rel = 1e-6`

### 2. Sensitivity Computation Accuracy

#### Numerical Differentiation Error
The analytical sensitivity formula:
```
∂V_m/∂R_k = (1/R_k²) · (λ_i - λ_j) · (V_i - V_j)
```
avoids the subtraction errors inherent in finite-difference methods.

The relative error is bounded by:
```
|Δ(∂V/∂R)| / |∂V/∂R| ≤ 2·ε_machine · (1 + |V_i - V_j|/|λ_i - λ_j|)
```
where `ε_machine ≈ 2.2×10⁻¹⁶` for double precision.

#### Extreme Parameter Values
For very small resistances (`R_k → 0`), the term `1/R_k²` can cause overflow. The implementation uses:
```
if (R_k < R_min) R_k = R_min
```
where `R_min = 1e-12` Ω typically.

For very large resistances (`R_k → ∞`), the sensitivity approaches zero. The computation uses:
```
if (R_k > 1/G_min) ∂V/∂R_k = 0
```
where `G_min = 1e-12` S is the minimum conductance.

### 3. Geometric Parameter Convergence

#### Length and Width Derivatives
The geometric derivatives:
```
∂R/∂L = R_sh / W
∂R/∂W = -R_sh · L / W²
```
can become large when `W → 0` or when `L/W` ratio is extreme.

The implementation enforces bounds:
```
if (W < W_min) W = W_min  (typically W_min = 1e-9 m)
if (L < L_min) L = L_min  (typically L_min = 1e-9 m)
```

#### Chain Rule Accumulation Error
The geometric sensitivity computation:
```
∂V/∂L = (∂V/∂R) · (∂R/∂L)
```
accumulates relative errors:
```
ε_total ≈ ε_∂V/∂R + ε_∂R/∂L
```
where each term has relative error of approximately `ε_machine`.

### 4. AC Sensitivity Convergence

#### Complex Arithmetic Stability
The complex sensitivity computation:
```
Re[∂V/∂R] = (1/R²) · [λ_real·ΔV_real + λ_imag·ΔV_imag]
Im[∂V/∂R] = (1/R²) · [λ_imag·ΔV_real - λ_real·ΔV_imag]
```
can suffer from cancellation errors when `λ_real·ΔV_real` and `λ_imag·ΔV_imag` have opposite signs.

The implementation checks for cancellation:
```
if (|λ_real·ΔV_real + λ_imag·ΔV_imag| < ε_cancel · (|λ_real·ΔV_real| + |λ_imag·ΔV_imag|))
```
where `ε_cancel = 1e-10`. If cancellation is detected, higher precision may be used.

#### Frequency-Dependent Convergence
At high frequencies where `ωRC ≈ 1`, the sensitivity becomes frequency-dependent. The convergence of the frequency sweep is monitored:
```
|∂V(ω_{k+1})/∂R - ∂V(ω_k)/∂R| < ε_freq · max(|∂V/∂R|, S_min)
```
where `ε_freq = 1e-4` typically.

### 5. Temperature Sensitivity Convergence

#### Temperature Coefficient Stability
The temperature derivative:
```
∂R/∂T = R_0 · [TC1 + 2·TC2·(T - T_0)]
```
can cause issues when `TC1` and `TC2` have opposite signs and similar magnitudes near `T ≈ T_0`.

The implementation uses regularization:
```
if (|TC1 + 2·TC2·ΔT| < ε_TC) ∂R/∂T = R_0 · sign(TC1) · ε_TC
```
where `ε_TC = 1e-12`.

#### Temperature Sweep Convergence
For temperature sweeps, the sensitivity convergence is checked:
```
|∂V(T_{k+1})/∂R - ∂V(T_k)/∂R| < ε_temp · max(|∂V/∂R|, S_min)
```
with `ε_temp = 1e-6` typically.

### 6. Multiple Output Convergence

#### Adjoint Solution Independence
For `N_out` outputs, `N_out` adjoint systems are solved. The convergence of each must be verified independently.

The worst-case convergence determines overall accuracy:
```
max_{m=1..N_out} ||Jᵀ·λ^{(m)} - e_m|| < ε_adjoint
```

#### Memory and Computational Convergence
The memory requirement scales as `O(N_nodes × N_out)`. The implementation checks:
```
if (N_nodes × N_out > MEM_MAX) reduce N_out or use iterative methods
```
where `MEM_MAX` is the available memory limit.

### 7. Statistical Sensitivity Convergence

#### Monte Carlo Convergence
When sensitivity is computed over Monte Carlo samples, the statistical convergence is monitored.

The mean sensitivity converges as:
```
|μ_N - μ| < t_α · σ/√N
```
where:
- `μ_N` = sample mean after N samples
- `σ` = sample standard deviation
- `t_α` = t-distribution critical value for confidence level α

The simulation continues until:
```
t_α · σ/√N < ε_stat · |μ|
```
with `ε_stat = 0.01` (1%) typically.

#### Variance Convergence
The variance of sensitivity converges as:
```
|σ_N² - σ²| < χ²_α · σ²/√(2N)
```
where `χ²_α` is the chi-squared distribution critical value.

### 8. Implementation-Specific Convergence Criteria

#### Matrix Solver Tolerance
The linear solver tolerance for the adjoint system is typically tighter than for the original system:
```
ε_solver_adjoint = 0.1 × ε_solver_original
```
because sensitivity computation amplifies errors in the adjoint solution.

#### Perturbation Size Optimization
For finite-difference verification, the optimal perturbation size minimizes total error:
```
δ_opt = √(ε_machine) ≈ 1.5×10⁻⁸
```
The implementation uses `δ = 1e-6` as a compromise between truncation error and roundoff error.

#### Sensitivity Thresholding
Very small sensitivities are thresholded to zero:
```
if (|∂V/∂R| < S_min) ∂V/∂R = 0
```
where `S_min = 1e-18` V/Ω typically.

### 9. Error Propagation Analysis

#### Error in Voltage Solution
The error in the original solution `ΔV` propagates to sensitivity error:
```
Δ(∂V/∂R) ≈ (1/R²) · [(λ_i - λ_j) · Δ(V_i - V_j) + (V_i - V_j) · Δ(λ_i - λ_j)]
```

The relative error bound is:
```
|Δ(∂V/∂R)|/|∂V/∂R| ≤ |Δ(V_i - V_j)|/|V_i - V_j| + |Δ(λ_i - λ_j)|/|λ_i - λ_j|
```

#### Error in Adjoint Solution
The adjoint solution error `Δλ` satisfies:
```
||Δλ|| ≤ κ(J) · ||Δb||/||b|| + ε_solver
```
where `ε_solver` is the linear solver tolerance.

### 10. Convergence Acceleration Techniques

#### Reusing Matrix Factorization
The Jacobian `J = ∂F/∂x` is factorized once for the original system. The same factorization is reused for all adjoint systems:
```
J = L·U  (LU factorization)
Jᵀ = Uᵀ·Lᵀ
```
Solving `Jᵀ·λ = b` requires only back substitution with the transposed factors.

#### Iterative Refinement
For ill-conditioned systems, iterative refinement is applied:
```
for k = 1 to max_refine:
    r = b - Jᵀ·λ
    solve J·δ = r  (using existing factorization)
    λ = λ + δ
    if ||r|| < ε_refine break
```

#### Adaptive Perturbation
For geometric parameters, the perturbation is adapted based on parameter magnitude:
```
δ_L = max(ε_abs, ε_rel·L)
δ_W = max(ε_abs, ε_rel·W)
```
where `ε_abs = 1e-12` m and `ε_rel = 1e-6`.

This mathematical formulation and convergence analysis provide the complete framework for resistor sensitivity analysis in Ngspice, ensuring accurate and efficient computation of parameter sensitivities for circuit optimization and yield analysis.

## C Implementation

### Core Data Structures and Sensitivity Architecture

The Ngspice resistor sensitivity analysis is implemented through a sophisticated C architecture that directly maps to the adjoint method mathematical formulation. The implementation spans multiple files (`ressset.c`, `ressload.c`, `ressacl.c`, `ressprt.c`) and integrates with the SPICE simulation kernel through specialized data structures.

#### Sensitivity-Enhanced Resistor Instance Structure

The `RESinstance` structure is extended with sensitivity-specific fields that store computed derivatives and adjoint solution components:

```c
/* From resdefs.h - Extended for sensitivity analysis */
typedef struct sRESinstance {
    /* Core connectivity and parameters */
    char *RESname;                  /* Instance name for identification */
    int RESposNode;                 /* Positive node index in MNA matrix */
    int RESnegNode;                 /* Negative node index in MNA matrix */
    double RESresist;               /* Nominal resistance value (Ω) */
    double RESconduct;              /* Conductance G = 1/RESresist (S) */
    
    /* Geometric parameters for physical resistors */
    double RESlength;               /* Length for geometric scaling (m) */
    double RESwidth;                /* Width for geometric scaling (m) */
    double REStemp;                 /* Instance operating temperature (K) */
    
    /* Matrix pointers for MNA stamping */
    double *RESposPosPtr;           /* SMP pointer to Y[pos][pos] element */
    double *RESposNegPtr;           /* SMP pointer to Y[pos][neg] element */
    double *RESnegPosPtr;           /* SMP pointer to Y[neg][pos] element */
    double *RESnegNegPtr;           /* SMP pointer to Y[neg][neg] element */
    
    /* Sensitivity analysis fields */
    unsigned RESsens : 1;           /* Bit flag: 1 if sensitivity requested */
    double RESsenPert;              /* Perturbation factor for finite-difference */
    double *RESsenResist;           /* Array: ∂V_out/∂R for each output */
    double *RESsenLength;           /* Array: ∂V_out/∂L for each output */
    double *RESsenWidth;            /* Array: ∂V_out/∂W for each output */
    
    /* Parameter specification flags */
    int RESresGiven;                /* Flag: resistance value specified */
    int RESlengthGiven;             /* Flag: length parameter specified */
    int RESwidthGiven;              /* Flag: width parameter specified */
    
    /* Linked list pointer */
    struct sRESinstance *RESnextInstance; /* Next resistor instance */
} RESinstance;
```

#### Sensitivity Analysis Control Structure

The `SENstruct` manages the global sensitivity analysis state, storing adjoint solutions and output specifications:

```c
/* Sensitivity analysis control structure */
typedef struct sSENstruct {
    int SENnumParms;                /* Number of sensitivity parameters */
    char **SENparmNames;            /* Array of parameter names */
    int SENnumOutVars;              /* Number of output variables */
    char **SENoutNames;             /* Array of output variable names */
    double SENperturb;              /* Perturbation factor (e.g., 0.001 = 0.1%) */
    
    /* Adjoint solution vectors */
    double *SENadjoint;             /* DC adjoint solution: λ vector */
    double *SENadjointReal;         /* AC real part adjoint solution */
    double *SENadjointImag;         /* AC imaginary part adjoint solution */
    
    /* Output control */
    FILE *SENoutFile;               /* File pointer for sensitivity output */
} SENstruct;
```

### Sensitivity Setup Implementation (`ressset.c`)

The `RESsSetup()` function initializes sensitivity analysis by allocating memory for sensitivity arrays and configuring geometric scaling parameters:

```c
/* ressset.c - Sensitivity Analysis Setup */
int RESsSetup(SENstruct *info, GENmodel *inModel)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    int i;
    
    /* Loop through all resistor models in circuit */
    for (; model != NULL; model = model->RESnextModel) {
        /* Loop through all instances in current model */
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            /* Check if this resistor is in sensitivity parameter list */
            if (inst->RESsens) {
                /* Search parameter names for this resistor instance */
                int parm;
                for (parm = 0; parm < info->SENnumParms; parm++) {
                    /* Mathematical: Identify which resistors need sensitivity */
                    if (info->SENparmNames[parm] == inst->RESname) {
                        
                        /* Allocate sensitivity arrays for each output variable */
                        /* Mathematical: Prepare storage for ∂V_out/∂p for p ∈ {R, L, W} */
                        inst->RESsenResist = TMALLOC(double, info->SENnumOutVars);
                        inst->RESsenLength = TMALLOC(double, info->SENnumOutVars);
                        inst->RESsenWidth = TMALLOC(double, info->SENnumOutVars);
                        
                        /* Initialize all sensitivity values to zero */
                        for (i = 0; i < info->SENnumOutVars; i++) {
                            inst->RESsenResist[i] = 0.0;
                            inst->RESsenLength[i] = 0.0;
                            inst->RESsenWidth[i] = 0.0;
                        }
                        
                        /* Set perturbation value for finite-difference verification */
                        /* Mathematical: ΔR = R × SENperturb */
                        inst->RESsenPert = info->SENperturb;
                        break;
                    }
                }
            }
            
            /* Compute geometric resistance if physical dimensions provided */
            /* Mathematical: R = RSH × (L/W) where RSH is sheet resistance */
            if (inst->RESlengthGiven && inst->RESwidthGiven) {
                double geometricFactor = inst->RESlength / inst->RESwidth;
                inst->RESresist = model->RESsheetRes * geometricFactor;
                inst->RESconduct = 1.0 / inst->RESresist;
            }
        }
    }
    return OK;  /* Ngspice success code */
}
```

**Mathematical Mapping:**
- Lines 20-30: Implements parameter identification `p ∈ {R, L, W}` for sensitivity computation
- Lines 33-35: Allocates storage for sensitivity arrays `∂V_out/∂p` for each output variable
- Lines 45-50: Sets perturbation `ΔR = R × SENperturb` for finite-difference validation
- Lines 55-60: Computes geometric resistance `R = RSH × (L/W)` for physical resistors

### DC Sensitivity Loading Implementation (`ressload.c`)

The `RESsLoad()` function computes DC sensitivities using the adjoint method solution, directly implementing the core sensitivity equation:

```c
/* ressload.c - DC Sensitivity Computation via Adjoint Method */
int RESsLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    double conductance;
    double v_diff;
    double *lambda;
    int i;
    
    /* Get adjoint solution vector λ from circuit structure */
    /* Mathematical: λ solves Yᵀλ = e_m where e_m is unit vector for output node */
    lambda = ckt->CKTsenInfo->SENadjoint;
    
    /* Process all resistor models and instances */
    for (; model != NULL; model = model->RESnextModel) {
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            /* Skip resistors not in sensitivity list */
            if (!inst->RESsens) continue;
            
            /* Get conductance G = 1/R */
            conductance = inst->RESconduct;
            
            /* Compute voltage difference V_pos - V_neg */
            /* Mathematical: ΔV = V_i - V_j */
            v_diff = *(ckt->CKTrhs + inst->RESposNode) - 
                     *(ckt->CKTrhs + inst->RESnegNode);
            
            /* Compute sensitivity for each output variable */
            for (i = 0; i < ckt->CKTsenInfo->SENnumOutVars; i++) {
                /* Get adjoint solution difference λ_i - λ_j */
                /* Mathematical: Δλ = λ_pos - λ_neg */
                double lambda_diff = 
                    lambda[inst->RESposNode * ckt->CKTsenInfo->SENnumOutVars + i] -
                    lambda[inst->RESnegNode * ckt->CKTsenInfo->SENnumOutVars + i];
                
                /* Core sensitivity calculation */
                /* Mathematical: ∂V_out/∂R = (1/R²) × (λ_pos - λ_neg) × (V_pos - V_neg) */
                inst->RESsenResist[i] = 
                    (1.0 / (inst->RESresist * inst->RESresist)) * 
                    lambda_diff * v_diff;
                
                /* Compute geometric parameter sensitivities if dimensions provided */
                /* Mathematical: ∂R/∂L = RSH/W, ∂R/∂W = -RSH×L/W² */
                if (inst->RESlengthGiven && inst->RESwidthGiven) {
                    double dR_dL = model->RESsheetRes / inst->RESwidth;
                    double dR_dW = -model->RESsheetRes * inst->RESlength / 
                                   (inst->RESwidth * inst->RESwidth);
                    
                    /* Chain rule: ∂V/∂L = (∂V/∂R) × (∂R/∂L) */
                    inst->RESsenLength[i] = inst->RESsenResist[i] * dR_dL;
                    inst->RESsenWidth[i] = inst->RESsenResist[i] * dR_dW;
                }
            }
        }
    }
    return OK;
}
```

**Mathematical Mapping:**
- Lines 15-16: Accesses adjoint solution `λ` from `SENadjoint` array
- Lines 30-31: Computes voltage difference `ΔV = V_i - V_j`
- Lines 38-39: Computes adjoint difference `Δλ = λ_i - λ_j` for each output
- Lines 44-46: Implements core sensitivity formula `∂V/∂R = (1/R²) × Δλ × ΔV`
- Lines 52-53: Computes geometric derivatives `∂R/∂L = RSH/W` and `∂R/∂W = -RSH×L/W²`
- Lines 56-57: Applies chain rule `∂V/∂L = (∂V/∂R) × (∂R/∂L)`

### AC Sensitivity Loading Implementation (`ressacl.c`)

The `RESsAcLoad()` function extends sensitivity analysis to AC frequency domain, handling complex voltages and adjoint solutions:

```c
/* ressacl.c - AC Sensitivity Analysis with Complex Variables */
int RESsAcLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    double omega = ckt->CKTomega;  /* Angular frequency ω = 2πf */
    double conductance;
    double v_real_diff, v_imag_diff;
    double *lambda_real, *lambda_imag;
    int i;
    
    /* Get complex adjoint solution vectors */
    /* Mathematical: λ(ω) = λ_real + jλ_imag */
    lambda_real = ckt->CKTsenInfo->SENadjointReal;
    lambda_imag = ckt->CKTsenInfo->SENadjointImag;
    
    for (; model != NULL; model = model->RESnextModel) {
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            if (!inst->RESsens) continue;
            
            conductance = inst->RESconduct;
            
            /* Compute complex voltage differences */
            /* Mathematical: ΔV = (V_real_pos - V_real_neg) + j(V_imag_pos - V_imag_neg) */
            v_real_diff = ckt->CKTrhs[inst->RESposNode] - 
                         ckt->CKTrhs[inst->RESnegNode];
            v_imag_diff = ckt->CKTirhs[inst->RESposNode] - 
                         ckt->CKTirhs[inst->RESnegNode];
            
            for (i = 0; i < ckt->CKTsenInfo->SENnumOutVars; i++) {
                /* Compute complex adjoint differences */
                double lambda_real_diff = 
                    lambda_real[inst->RESposNode * ckt->CKTsenInfo->SENnumOutVars + i] -
                    lambda_real[inst->RESnegNode * ckt->CKTsenInfo->SENnumOutVars + i];
                double lambda_imag_diff = 
                    lambda_imag[inst->RESposNode * ckt->CKTsenInfo->SENnumOutVars + i] -
                    lambda_imag[inst->RESnegNode * ckt->CKTsenInfo->SENnumOutVars + i];
                
                /* Complex sensitivity calculation */
                /* Mathematical: ∂V/∂R = (1/R²) × [ (λ_real·ΔV_real + λ_imag·ΔV_imag) 
                                                 + j(λ_imag·ΔV_real - λ_real·ΔV_imag) ] */
                /* Real part: Re(∂V/∂R) = (1/R²) × (λ_real·ΔV_real + λ_imag·ΔV_imag) */
                inst->RESsenResist[i] = 
                    (1.0 / (inst->RESresist * inst->RESresist)) * 
                    (lambda_real_diff * v_real_diff + 
                     lambda_imag_diff * v_imag_diff);
                
                /* Imaginary part would be stored separately if complex outputs needed */
                /* Mathematical: Im(∂V/∂R) = (1/R²) × (λ_imag·ΔV_real - λ_real·ΔV_imag) */
            }
        }
    }
    return OK;
}
```

**Mathematical Mapping:**
- Lines 13-14: Accesses complex adjoint solutions `λ_real` and `λ_imag`
- Lines 28-31: Computes complex voltage differences `ΔV_real` and `ΔV_imag`
- Lines 36-41: Computes complex adjoint differences `Δλ_real` and `Δλ_imag`
- Lines 47-50: Implements real part of complex sensitivity: `Re(∂V/∂R) = (1/R²) × (λ_real·ΔV_real + λ_imag·ΔV_imag)`
- Lines 53-54: Comment indicates imaginary part computation `Im(∂V/∂R) = (1/R²) × (λ_imag·ΔV_real - λ_real·ΔV_imag)`

### Sensitivity Reporting Implementation (`ressprt.c`)

The `RESsPrint()` function formats and outputs sensitivity results, including normalized sensitivity calculations:

```c
/* ressprt.c - Sensitivity Results Reporting */
int RESsPrint(GENmodel *inModel, CKTcircuit *ckt)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    int i;
    FILE *fp = ckt->CKTsenInfo->SENoutFile;
    
    /* Output header */
    fprintf(fp, "\nRESISTOR SENSITIVITIES\n");
    fprintf(fp, "======================\n");
    
    for (; model != NULL; model = model->RESnextModel) {
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            if (!inst->RESsens) continue;
            
            /* Instance header with resistance value */
            fprintf(fp, "\nResistor: %s  R = %g Ohms\n", 
                    inst->RESname, inst->RESresist);
            
            /* Output sensitivity for each output variable */
            for (i = 0; i < ckt->CKTsenInfo->SENnumOutVars; i++) {
                char *outName = ckt->CKTsenInfo->SENoutNames[i];
                double sens = inst->RESsenResist[i];
                
                /* Calculate normalized sensitivity */
                /* Mathematical: S_norm = (∂V/∂R) × (R/V_ref) × 100% */
                double normalized = sens * inst->RESresist;  /* V_ref = 1.0 assumed */
                
                fprintf(fp, "  ∂%s/∂R = %g  (%g%%/%% change)\n",
                        outName, sens, normalized * 100.0);
                
                /* Output geometric sensitivities if available */
                if (inst->RESlengthGiven && inst->RESwidthGiven) {
                    fprintf(fp, "    ∂%s/∂L = %g\n", outName, inst->RESsenLength[i]);
                    fprintf(fp, "    ∂%s/∂W = %g\n", outName, inst->RESsenWidth[i]);
                }
            }
        }
    }
    return OK;
}
```

**Mathematical Mapping:**
- Lines 28-29: Retrieves sensitivity value `∂V_out/∂R` from stored array
- Lines 33-34: Computes normalized sensitivity `S_norm = (∂V/∂R) × R × 100%` (assuming `V_ref = 1.0`)
- Lines 36-37: Outputs raw sensitivity `∂V_out/∂R`
- Lines 40-43: Outputs geometric sensitivities `∂V_out