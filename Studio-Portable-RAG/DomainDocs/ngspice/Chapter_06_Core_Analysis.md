# Core Analysis Routines: Setup, OP, and Transient

_Generated 2026-04-11 13:34 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktop.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/dctran.c`

# Chapter: Core Analysis Routines: Setup, OP, and Transient

## Introduction

The Ngspice simulation engine is built upon three foundational C modules that implement the core numerical algorithms for circuit analysis: `cktsetup.c`, `cktop.c`, and `dctran.c`. These files collectively transform a netlist description into a solvable mathematical system, implement nonlinear solution techniques, and perform time-domain integration with adaptive step control. `cktsetup.c` constructs the Modified Nodal Analysis (MNA) matrix formulation, mapping circuit topology into sparse matrix data structures. `cktop.c` implements the Newton-Raphson algorithm for solving the nonlinear DC operating point equations, handling convergence acceleration through damping and homotopy methods. `dctran.c` provides transient analysis capabilities using numerical integration methods (Trapezoidal, Backward Euler, and Gear) with predictor-corrector algorithms and local truncation error-based adaptive time stepping. Together, these modules implement the mathematical foundation of SPICE simulation: solving the differential-algebraic equation system **G·x + C·dx/dt + f_NL(x) = b(t)** through sparse linear algebra, nonlinear iteration, and numerical integration.

## Mathematical Formulation

### 1. Modified Nodal Analysis (MNA) Framework

The core mathematical model for SPICE circuit simulation is the Differential-Algebraic Equation (DAE) system derived from Modified Nodal Analysis:

```
G·x + C·dx/dt + f_NL(x) = b(t)
```

Where:
- **G** ∈ ℝⁿˣⁿ: Sparse conductance matrix containing linear element contributions
- **C** ∈ ℝⁿˣⁿ: Sparse capacitance/inductance matrix for energy storage elements
- **x** ∈ ℝⁿ: State vector containing node voltages and branch currents: [V₁, V₂, ..., Vₙ, I_V₁, I_V₂, ...]ᵀ
- **f_NL(x)**: Nonlinear current contributions from devices like diodes and transistors
- **b(t)** ∈ ℝⁿ: Time-dependent source vector
- **n**: Total number of equations = number of circuit nodes + number of voltage sources

This formulation directly maps to the CKTcircuit data structure in `cktsetup.c`:
- `CKTmatrix` stores the combined **G + ∂f_NL/∂x** matrix (Jacobian)
- `CKTrhs` stores the right-hand side vector **b(t)**
- `CKTlhs` stores the solution vector **x**
- `CKTnumStates` tracks the dimension **n**

### 2. Matrix Stamping Algorithms

Each circuit element contributes to the MNA system through specific matrix stamps:

#### 2.1 Linear Resistive Elements
For a resistor of value R connected between nodes i and j:
```
G[i][i] += 1/R
G[j][j] += 1/R  
G[i][j] -= 1/R
G[j][i] -= 1/R
```
This corresponds to the `MATstamp()` calls in the `DEVload()` function.

#### 2.2 Independent Voltage Sources
For a voltage source V between nodes i and j with branch current I_V:
```
Row for KVL:    G[n][i] = +1,  G[n][j] = -1,  b[n] = V
Row for KCL i:  G[i][n] = +1
Row for KCL j:  G[j][n] = -1
```
Where n is the additional equation index for the branch current.

#### 2.3 Nonlinear Device Stamping
The `DEVload()` function implements the mathematical operation:
```
i = f_NL(v)          // Nonlinear current function
g = ∂f_NL/∂v         // Small-signal conductance
```
These contribute to both the Jacobian matrix (through g) and the right-hand side vector (through i).

### 3. DC Operating Point: Nonlinear System Solution

#### 3.1 Problem Formulation
The DC operating point solves the steady-state equation:
```
F(x) = G·x + f_NL(x) - b_DC = 0
```
This is a nonlinear algebraic system where **b_DC** contains DC source values.

#### 3.2 Newton-Raphson Iteration
The algorithm in `cktop.c` implements:
```
x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ - J⁻¹(x⁽ᵏ⁾)·F(x⁽ᵏ⁾)
```
Where the Jacobian **J(x)** = **G** + **∂f_NL/∂x**.

The iteration loop follows:
1. **Matrix Assembly**: Construct **J(x⁽ᵏ⁾)** = **G** + **∂f_NL/∂x**|ₓ₍ₖ₎
2. **RHS Assembly**: Compute **F(x⁽ᵏ⁾)** = **G·x⁽ᵏ⁾** + **f_NL(x⁽ᵏ⁾)** - **b_DC**
3. **Linear Solve**: **SMPsolve(J, -F, Δx)**
4. **Solution Update**: **x⁽ᵏ⁺¹⁾** = **x⁽ᵏ⁾** + **λ·Δx** (with damping factor λ)
5. **Convergence Check**: ‖**F(x⁽ᵏ⁺¹⁾)**‖ < ε

#### 3.3 Convergence Criteria
The normalized error for each state variable i is:
```
error_i = |Δx_i| / (reltol·|x_i| + abstol)
```
Convergence is achieved when max(error_i) < 1.0, where:
- `reltol` = `TSKreltol` (relative tolerance, typically 1e-3)
- `abstol` = `TSKabstol` (absolute tolerance, typically 1e-12)
- `voltTol` = `TSKvoltTol` (voltage-specific tolerance)

### 4. Transient Analysis: Time Discretization

#### 4.1 Discretized DAE System
The continuous-time system **G·x + C·dx/dt + f_NL(x) = b(t)** is discretized using numerical integration.

#### 4.2 Backward Euler Method
```
dx/dt ≈ (xₙ - xₙ₋₁)/h
```
Substituting into the DAE:
```
[G + C/h]·xₙ + f_NL(xₙ) = b(tₙ) + (C/h)·xₙ₋₁
```
This results in a nonlinear system at each time step solved via Newton-Raphson.

#### 4.3 Trapezoidal Rule (Default)
```
dx/dt ≈ (2/h)·(xₙ - xₙ₋₁) - dx/dtₙ₋₁
```
The discretized system becomes:
```
[G + (2C/h)]·xₙ + f_NL(xₙ) = b(tₙ) + C·[(2/h)·xₙ₋₁ + dx/dtₙ₋₁]
```
Where **dx/dtₙ₋₁** is known from the previous accepted step.

#### 4.4 Gear Method (Variable Order)
For order k, the multi-step formula is:
```
xₙ = Σ(αᵢ·xₙ₋ᵢ) + h·β₀·dx/dtₙ
```
Coefficients for orders 1-3:
- Order 1 (Backward Euler): α₁ = 1, β₀ = 1
- Order 2: α₁ = 4/3, α₂ = -1/3, β₀ = 2/3  
- Order 3: α₁ = 18/11, α₂ = -9/11, α₃ = 2/11, β₀ = 6/11

The `gear_predictor()` function in `dctran.c` implements this using the `CKThistory` array.

## Convergence Analysis

### 1. Newton-Raphson Convergence Properties

#### 1.1 Local Quadratic Convergence
Given a sufficiently accurate initial guess x⁽⁰⁾ near the solution x*, Newton's method exhibits quadratic convergence:
```
‖x⁽ᵏ⁺¹⁾ - x*‖ ≤ K·‖x⁽ᵏ⁾ - x*‖²
```
This requires that **J(x)** is Lipschitz continuous and nonsingular at x*.

#### 1.2 Convergence Failure Modes
The algorithm in `cktop.c` handles several failure cases:

1. **Singular Jacobian**: Detected during `SMPfactor()` LU decomposition
2. **Oscillation**: Managed by damping factor λ ∈ (0,1]
3. **Divergence**: Limited by `TSKmaxIter` (typically 100-200 iterations)

#### 1.3 Damping Strategy
The damping factor λ is computed as:
```
λ = min(1.0, 10.0 / max_norm_delta)
```
Where `max_norm_delta` is the maximum normalized change across all variables. This prevents overshoot in highly nonlinear regions.

### 2. Transient Analysis Convergence

#### 2.1 Local Truncation Error (LTE)
For the trapezoidal rule, the LTE is bounded by:
```
LTE ≤ (h³/12)·‖x‴(ξ)‖ for some ξ ∈ [tₙ₋₁, tₙ]
```
In practice, Ngspice estimates LTE using predictor-corrector difference:
```
LTE_estimate = ‖xₙ - x̂ₙ‖
```
Where x̂ₙ is the predicted value from the predictor step.

#### 2.2 LTE-Based Time Step Control
The adaptive time step algorithm follows:
```
if LTE > τ:          // Error too large
    h_new = h·max(0.5, 0.9·√(τ/LTE))
    Reject step and retry
    
else if LTE < τ/10:  // Error very small  
    h_new = h·min(2.0, √(τ/LTE))
    
else:                // Error acceptable
    h_new = h
```
Where:
- τ = `TSKtrtol` (user-specified truncation error tolerance)
- Bounds: `TSKminStep` ≤ h_new ≤ `TSKmaxStep`

#### 2.3 Stability Analysis

##### 2.3.1 Trapezoidal Rule (A-stable)
The trapezoidal rule is A-stable, meaning it remains stable for all h > 0 when applied to linear stable systems. However, it can produce artificial oscillations for stiff systems with large time steps.

##### 2.3.2 Backward Euler (L-stable)
Backward Euler is L-stable (A-stable and dampens high frequencies), making it more robust for stiff problems but less accurate.

##### 2.3.3 Gear Methods (Stiffly Stable)
Gear methods of order k are stable for:
```
h·λ ∈ R_k
```
Where R_k is the stability region and λ represents the system eigenvalues. Higher-order Gear methods have smaller stability regions but better accuracy.

#### 2.4 Convergence of Nonlinear Iteration at Each Time Step
At each time tₙ, the nonlinear system:
```
F(xₙ, (xₙ - xₙ₋₁)/h, tₙ) = 0
```
is solved via Newton-Raphson. The convergence criteria are identical to DC analysis but with the additional time-dependent terms.

### 3. Sparse Linear Solver Convergence

#### 3.1 LU Factorization Stability
The `SMPfactor()` function implements LU factorization with partial pivoting:
```
P·A = L·U
```
The growth factor ρ = max|uᵢⱼ|/max|aᵢⱼ| is bounded by:
```
ρ ≤ 2ⁿ⁻¹
```
but in practice is much smaller for circuit matrices due to diagonal dominance.

#### 3.2 Ill-Conditioning Detection
Circuit matrices can become ill-conditioned due to:
1. **Large element value ratios** (e.g., 1Ω vs 1GΩ)
2. **Floating nodes** (zero diagonal entries)
3. **Singularities during Newton iteration**

The solver detects this through:
- **Small pivots** during LU decomposition
- **Large residual** ‖A·x - b‖ after solution

### 4. Global Convergence Techniques

#### 4.1 Source Stepping
For difficult DC convergence, the homotopy method solves:
```
F(x, α) = G·x + f_NL(x) - α·b = 0
```
Starting from α = 0 (zero sources) and gradually increasing to α = 1.

#### 4.2 Gmin Stepping
A small conductance Gmin (typically 1e-12) is added from every node to ground to improve matrix conditioning, then gradually reduced.

#### 4.3 Pseudotransient Analysis
The transient analysis equations are solved with artificially large capacitors to "slow down" the circuit dynamics, making convergence easier.

### 5. Mathematical Convergence Criteria Summary

#### 5.1 DC Convergence
```
max_i( |Δx_i| / (reltol·|x_i| + abstol) ) < 1.0
```
AND
```
max_i( |F_i(x)| / (reltol·|x_i| + abstol) ) < 1.0
```

#### 5.2 Transient Step Acceptance
```
max_i( LTE_i / (reltol·|x_i| + abstol) ) < τ
```
AND
```
Newton iteration converged at time tₙ
```

#### 5.3 Time Step Adjustment
```
h_new = h_current · min(2.0, max(0.5, √(τ/LTE_estimated)))
```
With bounds: `TSKminStep` ≤ h_new ≤ `TSKmaxStep`

These mathematical formulations and convergence analyses are directly implemented in the Ngspice C code through the data structures and algorithms described in `cktsetup.c`, `cktop.c`, and `dctran.c`.

## C Implementation

### 1. Circuit Setup Implementation (`cktsetup.c`)

#### 1.1 Core Data Structures

The mathematical formulation **G·x + C·dx/dt = b** maps directly to the `CKTcircuit` structure:

```c
typedef struct sCKT {
    int CKTmaxEqns;           // Dimension n of the MNA system
    int CKTnumStates;         // Number of state variables (≤ CKTmaxEqns)
    double *CKTrhs;           // Right-hand side vector b(t)
    double *CKTlhs;           // Solution vector x (node voltages + branch currents)
    double **CKTmatrix;       // Pointer to Jacobian matrix J = G + ∂f_NL/∂x
    double *CKTdiag;          // Diagonal elements for sparse optimization
    int *CKTcolPtr;           // Column pointers for CSC sparse format
    int *CKTrowIdx;           // Row indices for CSC sparse format
    SMPmatrix *CKTmatrixImpl; // Sparse matrix solver implementation
    double *CKTrhsOld;        // Previous solution x⁽ᵏ⁾ for Newton iteration
    double *CKTpred;          // Predicted solution x̂ for LTE calculation
    double CKThistory[8][MAX_EQNS]; // History for Gear multi-step methods
} CKTcircuit;
```

#### 1.2 Matrix Stamping Implementation

The matrix stamp algorithm implements the mathematical conductance contributions:

```c
// Mathematical: G[i][i] += 1/R, G[j][j] += 1/R, G[i][j] -= 1/R, G[j][i] -= 1/R
void MATstamp(double **matrix, int row, int col, double value) {
    if (row >= 0 && col >= 0) {
        matrix[row][col] += value;
    }
}

// Device load function implementing f_NL(x) and ∂f_NL/∂x contributions
int DEVload(DEVdevice *device, CKTcircuit *ckt) {
    // Get device terminals from circuit topology
    int posNode = device->DEVposNode;
    int negNode = device->DEVnegNode;
    
    // Compute nonlinear current: i = f_NL(v)
    double v = ckt->CKTrhsOld[posNode] - ckt->CKTrhsOld[negNode];
    double i = DEVcurrent(device, v);
    
    // Compute small-signal conductance: g = ∂f_NL/∂v
    double g = DEVconductance(device, v);
    
    // Stamp conductance into Jacobian matrix
    MATstamp(ckt->CKTmatrix, posNode, posNode, +g);
    MATstamp(ckt->CKTmatrix, negNode, negNode, +g);
    MATstamp(ckt->CKTmatrix, posNode, negNode, -g);
    MATstamp(ckt->CKTmatrix, negNode, posNode, -g);
    
    // Stamp current into RHS vector: b -= i for KCL
    ckt->CKTrhs[posNode] -= i;
    ckt->CKTrhs[negNode] += i;
    
    return OK;
}
```

#### 1.3 Voltage Source Implementation

The voltage source stamp creates the additional equation for branch current:

```c
int VSRCload(DEVdevice *device, CKTcircuit *ckt) {
    int posNode = device->DEVposNode;
    int negNode = device->DEVnegNode;
    int branchEqn = device->DEVbranchEqn; // Additional equation index
    
    // KVL equation: V_pos - V_neg = V_source
    MATstamp(ckt->CKTmatrix, branchEqn, posNode, +1.0);
    MATstamp(ckt->CKTmatrix, branchEqn, negNode, -1.0);
    ckt->CKTrhs[branchEqn] = device->DEVdcValue; // V_source
    
    // KCL contributions for branch current I_V
    MATstamp(ckt->CKTmatrix, posNode, branchEqn, +1.0);
    MATstamp(ckt->CKTmatrix, negNode, branchEqn, -1.0);
    
    return OK;
}
```

### 2. DC Operating Point Implementation (`cktop.c`)

#### 2.1 Newton-Raphson Main Loop

The mathematical Newton iteration **x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ - J⁻¹(x⁽ᵏ⁾)·F(x⁽ᵏ⁾)** is implemented as:

```c
int DCop(CKTcircuit *ckt) {
    double reltol = ckt->CKTcurTask->TSKreltol;
    double abstol = ckt->CKTcurTask->TSKabstol;
    double vntol = ckt->CKTcurTask->TSKvoltTol;
    int maxIter = ckt->CKTcurTask->TSKmaxIter;
    int iter;
    
    // Initialize solution vector x⁽⁰⁾
    for (int i = 0; i < ckt->CKTmaxEqns; i++) {
        ckt->CKTrhsOld[i] = 0.0; // Initial guess
    }
    
    for (iter = 0; iter < maxIter; iter++) {
        // Step 1: Assemble F(x⁽ᵏ⁾) and J(x⁽ᵏ⁾) = G + ∂f_NL/∂x
        CKTload(ckt); // Calls all DEVload() functions
        
        // Step 2: Solve J·Δx = -F(x)
        // CKTrhs contains -F(x) after CKTload()
        SMPsolve(ckt->CKTmatrix, ckt->CKTrhs, ckt->CKTlhs); // Δx = J⁻¹·(-F)
        
        // Step 3: Apply damping: x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ + λ·Δx
        double lambda = damping_factor(ckt, ckt->CKTlhs);
        for (int i = 0; i < ckt->CKTmaxEqns; i++) {
            ckt->CKTrhsOld[i] += lambda * ckt->CKTlhs[i];
        }
        
        // Step 4: Convergence check: ‖Δx‖/(reltol·‖x‖ + abstol) < 1
        double maxDelta = 0.0;
        for (int i = 0; i < ckt->CKTnumStates; i++) {
            double delta = fabs(ckt->CKTlhs[i]);
            double absx = fabs(ckt->CKTrhsOld[i]);
            double error = delta / (reltol * absx + abstol);
            if (error > maxDelta) maxDelta = error;
        }
        
        if (maxDelta < 1.0) {
            ckt->CKTconv = 1;  // Convergence flag
            break;
        }
    }
    
    if (iter >= maxIter) {
        ckt->CKTconv = 0;  // Failure to converge
        return E_NOTCONV;
    }
    
    return OK;
}
```

#### 2.2 Device Model Implementation

The diode Shockley equation **I_D = I_S·[exp(V_D/(n·V_T)) - 1]** maps to:

```c
double DIOcurrent(double vd, double is, double n, double vt, double gmin) {
    if (vd < -3 * n * vt) {
        // Reverse bias approximation for numerical stability
        return -is + gmin * vd;
    } else {
        // Full exponential model
        double evd = exp(vd / (n * vt));
        return is * (evd - 1.0) + gmin * vd;
    }
}

double DIOconductance(double vd, double is, double n, double vt, double gmin) {
    if (vd < -3 * n * vt) {
        // Reverse bias conductance
        return gmin;
    } else {
        // ∂I_D/∂V_D = (I_S/(n·V_T))·exp(V_D/(n·V_T))
        double evd = exp(vd / (n * vt));
        return (is / (n * vt)) * evd + gmin;
    }
}
```

#### 2.3 Damping Factor Implementation

The damping factor **λ** for **x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ + λ·Δx** is computed as:

```c
double damping_factor(CKTcircuit *ckt, double *delta) {
    double lambda = 1.0;
    double maxDelta = 0.0;
    double reltol = ckt->CKTcurTask->TSKreltol;
    double abstol = ckt->CKTcurTask->TSKabstol;
    
    // Find maximum normalized change: max_i(|Δx_i|/(reltol·|x_i|+abstol))
    for (int i = 0; i < ckt->CKTnumStates; i++) {
        double normDelta = fabs(delta[i]) / 
                          (reltol * fabs(ckt->CKTrhsOld[i]) + abstol);
        if (normDelta > maxDelta) maxDelta = normDelta;
    }
    
    // Apply damping if change is too large
    if (maxDelta > 10.0) {
        lambda = 10.0 / maxDelta;
        lambda = max(lambda, 0.1); // Minimum damping factor
    }
    
    return lambda;
}
```

### 3. Transient Analysis Implementation (`dctran.c`)

#### 3.1 Time Integration Data Structures

The DAE system **G·x + C·dx/dt + f_NL(x) = b(t)** uses:

```c
typedef struct sTSKtask {
    double TSKstep;           // Current time step h
    double TSKmaxStep;        // Maximum time step h_max
    double TSKminStep;        // Minimum time step h_min
    double TSKtrtol;          // Truncation error tolerance τ
    double TSKchgtol;         // Charge conservation tolerance
    int TSKmethod;            // TRAP (0), GEAR (1), or BE (2)
    double TSKorder;          // Integration order for Gear (1-6)
    double TSKstartTime;      // Simulation start time
    double TSKstopTime;       // Simulation stop time
} TSKtask;

typedef struct sCKT {
    double CKTtime;           // Current simulation time t
    double CKTdelta;          // Current time step h
    double CKTdeltaOld[8];    // Previous time steps for Gear
    double CKTtrtol;          // Local truncation error tolerance
    int CKTmode;              // MODETRAN for transient analysis
    int CKTreject;            // Flag to reject current step
    double CKTpred[MAX_EQNS]; // Predicted solution x̂ for LTE
} CKTcircuit;
```

#### 3.2 Trapezoidal Integration Implementation

The trapezoidal rule **dx/dt ≈ (2/h)·(xₙ - xₙ₋₁) - dx/dtₙ₋₁** is implemented:

```c
void TRAPload(CKTcircuit *ckt, double h) {
    // For each capacitor/inductor with companion model conductance g_c
    double g_c = (2.0 * C) / h; // C is capacitance value
    
    // Stamp [G + (2C/h)] into matrix
    MATstamp(ckt->CKTmatrix, posNode, posNode, +g_c);
    MATstamp(ckt->CKTmatrix, negNode, negNode, +g_c);
    MATstamp(ckt->CKTmatrix, posNode, negNode, -g_c);
    MATstamp(ckt->CKTmatrix, negNode, posNode, -g_c);
    
    // Compute history term: i_history = C·[(2/h)·xₙ₋₁ + dx/dtₙ₋₁]
    double i_history = C * ((2.0/h) * x_old + dxdt_old);
    
    // Stamp into RHS: b(tₙ) + i_history
    ckt->CKTrhs[posNode] += i_history;
    ckt->CKTrhs[negNode] -= i_history;
}
```

#### 3.3 Predictor-Corrector Implementation

```c
void predictor(CKTcircuit *ckt, double t, double h) {
    // Simple predictor: x̂ₙ = xₙ₋₁ + h·dx/dtₙ₋₁ (forward Euler)
    for (int i = 0; i < ckt->CKTmaxEqns; i++) {
        ckt->CKTpred[i] = ckt->CKTrhsOld[i] + h * ckt->CKTdxdtOld[i];
    }
}

double compute_LTE(CKTcircuit *ckt, double h, double *x_n, double *x_pred) {
    double lte_max = 0.0;
    double reltol = ckt->CKTcurTask->TSKreltol;
    double abstol = ckt->CKTcurTask->TSKabstol;
    
    // LTE ≈ |(h/3)·(xₙ - x̂ₙ)| for trapezoidal rule
    for (int i = 0; i < ckt->CKTnumStates; i++) {
        double error = fabs(x_n[i] - x_pred[i]);
        double denom = reltol * fabs(x_n[i]) + abstol;
        double lte = error / denom;
        
        if (lte > lte_max) lte_max = lte;
    }
    
    return lte_max;
}
```

#### 3.4 Adaptive Time Step Control

The algorithm **h_new = h·min(2.0, max(0.5, √(τ/LTE)))** is implemented:

```c
double adjust_time_step(CKTcircuit *ckt, double lte) {
    double trtol = ckt->CKTcurTask->TSKtrtol;
    double h = ckt->CKTdelta;
    double h_new;
    
    if (lte > trtol) {
        // Error too large: reduce step
        double factor = sqrt(trtol / lte);
        factor = max(0.5, min(factor, 0.9)); // Conservative reduction
        h_new = h * factor;
        h_new = max(h_new, ckt->CKTcurTask->TSKminStep);
        ckt->CKTreject = 1; // Mark for rejection
    } else if (lte < trtol/10.0) {
        // Error very small: can increase
        double factor = sqrt(trtol / lte);
        factor = min(factor, 2.0); // Limit increase
        h_new = h * factor;
        h_new = min(h_new, ckt->CKTcurTask->TSKmaxStep);
    } else {
        // Error acceptable: keep current step
        h_new = h;
    }
    
    return h_new;
}
```

#### 3.5 Gear Method Implementation

The multi-step formula **xₙ = Σ(αᵢ·xₙ₋ᵢ) + h·β₀·dx/dtₙ** is implemented:

```c
// Gear coefficients for orders 1-3
static double gear_alpha[4][4] = {
    {0, 0, 0, 0},           // Unused
    {0, 1.0, 0, 0},         // Order 1: α₁=1
    {0, 4.0/3.0, -1.0/3.0, 0}, // Order 2: α₁=4/3, α₂=-1/3
    {0, 18.0/11.0, -9.0/11.0, 2.0/11.0} // Order 3: α₁=18/11, α₂=-9/11, α₃=2/11
};

static double gear_beta[4] = {0, 1.0, 2.0/3.0, 6.0/11.0};

void gear_predictor(CKTcircuit *ckt, int order) {
    // Predict xₙ using history: x̂ₙ = Σ(αᵢ·xₙ₋ᵢ)
    for (int i = 0; i < ckt->CKTmaxEqns; i++) {
        ckt->CKTpred[i] = 0.0;
        for (int j = 1; j <= order; j++) {
            ckt->CKTpred[i] += gear_alpha[order][j] * ckt->CKThistory[j-1][i];
        }
    }
}

void gear_corrector(CKTcircuit *ckt, int order, double h) {
    // For each energy storage element
    double beta0 = gear_beta[order];
    double g_eq = C / (beta0 * h); // Equivalent conductance
    
    // Stamp into matrix: C/(β₀·h) contributes to diagonal
    MATstamp(ckt->CKTmatrix, posNode, posNode, +g_eq);
    MATstamp(ckt->CKTmatrix, negNode, negNode, +g_eq);
    MATstamp(ckt->CKTmatrix, posNode, negNode, -g_eq);
    MATstamp(ckt->CKTmatrix, negNode, posNode, -g_eq);
    
    // History term: i_hist = C/(β₀·h) * Σ(αᵢ·xₙ₋ᵢ)
    double x_pred = gear_alpha[order][1] * x_n1 + 
                    gear_alpha[order][2] * x_n2 + 
                    gear_alpha[order][3] * x_n3;
    double i_hist = g_eq * x_pred;
    
    ckt->CKTrhs[posNode] += i_hist;
    ckt->CKTrhs[negNode] -= i_hist;
}
```

#### 3.6 Transient Analysis Main Loop

```c
int TRANanalyze(CKTcircuit *ckt) {
    double t_start = ckt->CKTcurTask->TSKstartTime;
    double t_stop = ckt->CKTcurTask->TSKstopTime;
    double t = t_start;
    
    // Initial DC operating point: solve F(x₀, 0, 0) = 0
    DCop(ckt);
    
    // Initialize time step
    ckt->CKTdelta = ckt->CKTcurTask->TSKstep;
    
    while (t < t_stop) {
        int converged = 0;
        int retry_count = 0;
        
        do {
            // Predictor step for LTE calculation
            predictor(ckt, t, ckt->CKTdelta);
            
            // Set up discretized system at time t + h
            ckt->CKTtime = t + ckt->CKTdelta;
            
            // Load matrix with integration method coefficients
            switch (ckt->CKTcurTask->TSKmethod) {
                case TRAP:
                    TRAPload(ckt, ckt->CKTdelta);
                    break;
                case GEAR:
                    gear_corrector(ckt, ckt->CKTcurTask->TSKorder, ckt->CKTdelta);
                    break;
                case BE:
                    BEload(ckt, ckt->CKTdelta);
                    break;
            }
            
            // Nonlinear solve at time t + h
            converged = NewtonIteration(ckt);
            
            if (!converged) {
                // Reduce time step and retry
                ckt->CKTdelta *= 0.5;
                retry_count++;
                
                if (retry_count > MAX_RETRY) {
                    return E_NOTCONV;
                }
            }
        } while (!converged);
        
        // Calculate Local Truncation Error
        double lte = compute_LTE(ckt, ckt->CKTdelta, 
                                ckt->CKTrhsOld, ckt->CKTpred);
        
        if (lte > ckt->CKTcurTask->TSKtrtol) {
            // Reject step: error too large
            ckt->CKTdelta = adjust_time_step(ckt, lte);
            continue;
        }
        
        // Accept step
        t += ckt->CKTdelta;
        save_solution(ckt, t);
        
        // Update history for multi-step methods
        update_history(ckt);
        
        // Adjust time step for next iteration
        ckt->CKTdelta = adjust_time_step(ckt, lte);
        
        // Handle final step
        if (t + ckt->CKTdelta > t_stop) {
            ckt->CKTdelta = t_stop - t;
        }
    }
    
    return OK;
}
```

### 4. Sparse Matrix Solver Implementation

#### 4.1 Compressed Sparse Column (CSC) Format

```c
typedef struct {
    double *values;      // Non-zero values (size = nnz)
    int *rowIndices;     // Row indices (size = nnz)
    int *colPointers;    // Column pointers (size = nCols+1)
    int nRows;           // Number of rows
    int nCols;           // Number of columns
    int nnz;             // Number of non-zeros
    int *perm;           // Row permutation from pivoting
    int *invperm;        // Inverse permutation
} SMPmatrix;
```

#### 4.2 LU Factorization with Partial Pivoting

```c
int SMPfactor(SMPmatrix *matrix) {
    int n = matrix->nRows;
    double *values = matrix->values;
    int *colPtr = matrix->colPointers;
    int *rowIdx = matrix->rowIndices;
    
    // Initialize permutation vectors
    for (int i = 0; i < n; i++) {
        matrix->perm[i] = i;
        matrix->invperm[i] = i;
    }
    
    for (int k = 0; k < n-1; k++) {
        // Find pivot in column k (partial pivoting)
        int pivotRow = k;
        double maxVal = fabs(values[colPtr[k] + k]);
        
        for (int i = k+1; i < n; i++) {
            double val = fabs(values[colPtr[i] + k]);
            if (val > maxVal) {
                maxVal = val;
                pivotRow = i;
            }
        }
        
        // Swap rows if necessary
        if (pivotRow != k) {
            swapRows(matrix, k, pivotRow);
            // Update permutation vectors
            int tmp = matrix->perm[k];
            matrix->perm[k] = matrix->perm[pivotRow];
            matrix->perm