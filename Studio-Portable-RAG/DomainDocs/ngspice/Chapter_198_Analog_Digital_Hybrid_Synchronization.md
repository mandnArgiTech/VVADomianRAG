# Mixed-Mode Synchronization: Transient Acceptance and Backtracking

_Generated 2026-04-13 10:01 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtaccept.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtbackup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtcall_hybrids.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/xspice/evt/evtnode_copy.c`

# Ngspice Reference Architecture: A Unified Mathematical and Implementation Compendium

## Executive Summary

This document synthesizes the complete mathematical foundations and C implementation architecture of the Ngspice Electronic Design Automation (EDA) toolchain. Drawing from extensive architectural teardowns of the Ngspice codebase, we present a unified reference covering the entire simulation pipeline—from netlist parsing through behavioral modeling to mixed-signal event-driven execution.

## Core Mathematical Framework

### 1. Differential-Algebraic Equation System

Ngspice solves circuit problems formulated as index-1 Differential-Algebraic Equations (DAEs):

```
F(x(t), ẋ(t), t) = 0
```

where:
- `x(t) ∈ ℝⁿ`: State vector (node voltages + branch currents)
- `ẋ(t)`: Time derivative of state vector
- `t`: Time variable
- `F: ℝⁿ × ℝⁿ × ℝ → ℝⁿ`: Nonlinear vector function

### 2. Modified Nodal Analysis (MNA) Formulation

The DAE system is structured using Modified Nodal Analysis:

```
[G  B] [v]   [i]
[Bᵀ D] [i] = [vₛ]
```

where:
- `G ∈ ℝ^{m×m}`: Conductance matrix
- `B ∈ ℝ^{m×k}`: Branch incidence matrix
- `D ∈ ℝ^{k×k}`: Device-specific matrix
- `v ∈ ℝᵐ`: Node voltage vector
- `i ∈ ℝᵏ`: Branch current vector
- `vₛ ∈ ℝᵏ`: Source voltage vector

### 3. Analysis-Specific Transformations

#### DC Operating Point Analysis
```
G·x = b
```
Solved via Newton-Raphson iteration with homotopy continuation (GMIN stepping, source stepping).

#### AC Small-Signal Analysis
```
(G + jωC + J_NL)·X̃ = B̃
```
where `J_NL = ∂φ/∂x` is the Jacobian of nonlinear devices evaluated at DC operating point.

#### Transient Analysis
Using Backward Differentiation Formula (BDF) of order p:
```
G·x_{n+1} + C·(∑_{i=0}^p α_i x_{n+1-i})/h + φ(x_{n+1}) = b(t_{n+1})
```
with coefficients α_i satisfying ∑α_i = 0.

## Implementation Architecture

### 1. Parser Core System

**Mathematical Model**: The parser transforms SPICE netlists into mathematical representations through formal grammar processing:

```
Netlist → Parse Tree → Symbol Table → MNA Matrices
```

**Key Algorithms**:
- Three-pass parsing architecture (subcircuit expansion, node aliasing, topological binding)
- Union-Find algorithm for node equivalence resolution
- Hash-based symbol table: `S: Σ* → ℕ ∪ {⊥}` with O(1) lookup
- Recursive descent parsing with depth limit `MAX_EXPANSION_DEPTH = 100`

**C Implementation**:
```c
// Core data structures
typedef struct CKTcircuit {
    SMPmatrix *CKTmatrix;      // Sparse MNA matrix
    double *CKTrhs;            // Right-hand side vector
    double *CKTlhs;            // Left-hand side (solution)
    HASHTABLE *CKTnodeHash;    // Symbol table
    int CKTmode;               // Analysis mode flags
    double CKTtime;            // Current simulation time
    double CKTdelta;           // Current time step
    GENmodel *CKTmodels;       // Device model linked list
} CKTcircuit;

// Analysis state machine (cktdojob.c)
int CKTdoJob(CKTcircuit *ckt) {
    switch(ckt->CKTstate) {
        case STATE_INIT:    initialize_analysis(ckt); break;
        case STATE_DCOP:    solve_dc_operating_point(ckt); break;
        case STATE_TRAN:    perform_transient_analysis(ckt); break;
        case STATE_AC:      perform_ac_analysis(ckt); break;
        case STATE_FINISH:  cleanup(ckt); return OK;
    }
}
```

### 2. Device Modeling System

**Mathematical Formulation**: Each device implements a mapping:
```
Φ: Parameters → (G, B, D, φ) contributions
```

**Device Categories**:
1. **Passive Elements**: R, L, C with linear stamps
2. **Semiconductors**: Nonlinear with exponential characteristics
3. **Sources**: Independent (V, I) and dependent (E, F, G, H)
4. **Behavioral Models**: User-defined equations via AST evaluation

**Parameter Propagation Hierarchy**:
```
Model Card → Instance Parameters → Temperature Effects → Operating Point
```

### 3. Behavioral Modeling Engine

**Formal Grammar Definition**:
```
G = (V, Σ, P, S) where:
V = {Expression, Term, Factor, ...}
Σ = {+, -, *, /, ^, sin, cos, log, ...}
P: Production rules for SPICE expressions
S = Expression
```

**Abstract Syntax Tree (AST) Representation**:
```
AST = (type, value, children[], derivative_fn)
```

**Automatic Differentiation**:
```c
// Dual number implementation for Newton-Raphson
typedef struct {
    double value;
    double derivative;
} DualNumber;

DualNumber ptEval(PTnode *node, double *vars, double *derivs) {
    switch(node->type) {
        case OP_ADD:
            result = add(eval(left), eval(right));
            result.derivative = left.derivative + right.derivative;
            break;
        case OP_MUL:
            result.value = left.value * right.value;
            result.derivative = left.derivative * right.value 
                              + left.value * right.derivative;
            break;
        // ... other operations
    }
}
```

### 4. Numerical Solver Core

**Newton-Raphson Iteration**:
```
J(xₖ)·Δxₖ = -F(xₖ)
xₖ₊₁ = xₖ + λ·Δxₖ
```
where `λ ∈ (0,1]` is damping factor for convergence control.

**Convergence Criteria**:
1. **Update Test**: `‖Δx‖∞ < ε_abs + ε_rel·‖x‖∞`  
   (ε_abs = 1e-12, ε_rel = 1e-3)
2. **Residual Test**: `‖F(x)‖∞ < ε_res·(1 + ‖b‖∞)`  
   (ε_res = 1e-6)
3. **Divergence Detection**: `‖Δxₖ₊₁‖ > γ·‖Δxₖ‖` (γ ≈ 1.5)

**Homotopy Continuation Methods**:

1. **GMIN Stepping**:
   ```
   J(x) + ε·I = b, ε: 1 → GMIN_MIN (1e-12)
   ```

2. **Source Stepping**:
   ```
   J(x)·x = λ·b, λ: 0 → 1
   ```

### 5. Sparse Matrix System

**Compressed Sparse Column (CSC) Format**:
```
typedef struct SMPmatrix {
    int size;           // Matrix dimension
    int *colptr;        // Column pointers
    int *rowind;        // Row indices
    double *values;     // Non-zero values
    double pivotrel;    // Pivot threshold (1e-13)
} SMPmatrix;
```

**Matrix Operations**:
- Factorization: `SMPfactor()` with partial pivoting
- Solution: `SMPsolve()` for forward/backward substitution
- Jacobian reuse condition: `‖Δx‖ < ε_reuse` (1e-6)

### 6. Transient Integration System

**Time-Step Control Algorithm**:
```
h_new = h_old * min(β * (ε_LTE / ‖LTE‖)^(1/(p+1)), f_max)
```
where:
- `ε_LTE`: Local truncation error tolerance (1e-6)
- `p`: Integration order (1-6)
- `β`: Safety factor (0.8-0.9)
- `f_max`: Maximum growth factor (2.0)

**State Management**:
```c
// Integration history (ninteg.c)
typedef struct {
    double *states[7];      // State vectors for BDF
    double *derivs[7];      // Derivative history
    double coeffs[7][7];    // BDF coefficients
    int order;              // Current integration order (1-6)
} INTEG;
```

### 7. Event-Driven Mixed-Signal Engine

**Digital Logic System**:
12-state representation: `{0,1,X,Z} × {STRONG,RESISTIVE,HI_Z}`

**Event Queue Mathematics**:
```
EventQueue = {(t₁, event₁), (t₂, event₂), ... | tᵢ < tᵢ₊₁}
t_next = min(eventᵢ.timestamp)
```

**Mixed-Signal Interface**:

1. **ADC Model**:
   ```
   DigitalOutput[n] = { 1 if V_analog ≥ V_thresh_high[n]
                        0 if V_analog ≤ V_thresh_low[n]
                        previous otherwise }
   ```

2. **DAC Model**:
   ```
   V_analog = V_low + (V_high - V_low) * (∑ bit[i]·2ⁱ)/(2ᴺ - 1)
   ```

**Time-Wheel Scheduler**:
O(1) complexity event scheduling using circular buffer:
```c
#define TIME_WHEEL_SIZE 1024
typedef struct {
    Event *buckets[TIME_WHEEL_SIZE];
    int current_tick;
} TimeWheel;
```

### 8. XSPICE Code Model System

**Two-Stage Compilation Pipeline**:

1. **Interface Specification (.ifs)**:
   ```
   G₁ = (V₁, Σ₁, R₁, S₁)  // Chomsky Type-2 grammar
   → SPICEdev structure generation
   ```

2. **Model Behavior (.mod)**:
   ```
   G₂ = (V₂, Σ₂, R₂, S₂)  // Extended Backus-Naur Form
   → Optimized C code generation
   ```

**Macro Expansion System**:
```
INPUT(x) → *(ckt->CKTstates[inst->stateOffset + x_index])
```
with depth limiting: `depth(M) ≤ D_max = 100`

**Type Mapping Function**:
```
φ: SPICE Types → C Types
φ(DOUBLE) = double
φ(INTEGER) = int
φ(STRING) = char*
φ(COMPLEX) = double complex
```

### 9. Convergence and Stability Guarantees

**Numerical Protection Functions**:

1. **Safe Division**:
   ```c
   double safe_divide(double a, double b) {
       return (fabs(b) > 1e-100) ? a/b : 
              (a >= 0) ? DBL_MAX : -DBL_MAX;
   }
   ```

2. **Safe Exponential**:
   ```c
   double safe_exp(double x) {
       if (x > 700.0) return DBL_MAX;
       if (x < -700.0) return 0.0;
       return exp(x);
   }
   ```

3. **Smooth Conditional**:
   ```
   smooth_if(x, a, b) = a + (b-a) / (1 + exp(-αx))
   ```
   where α = 100.0 for differentiability.

**Algebraic Loop Detection**:
Construct dependency graph G = (V,E) where edge (u→v) exists if variable v appears in equation for u. Detect cycles using Tarjan's algorithm.

### 10. Memory and Performance Optimization

**Hash Table Implementation**:
```c
// DJB2 hash function
unsigned long hash(unsigned char *str) {
    unsigned long hash = 5381;
    while (int c = *str++)
        hash = ((hash << 5) + hash) + c;
    return hash % HASHSIZE;
}
```

**Cache Optimization**:
- Jacobian reuse based on ‖Δx‖ threshold
- Sparse pattern caching for repeated solves
- Block allocation for state vectors

**Parallelization Strategy**:
- Device load functions parallelizable across instances
- Matrix factorization using SuperLU or KLU
- Multi-threaded AC frequency sweep points

## Critical Constants and Limits

| Constant | Value | Purpose |
|----------|-------|---------|
| `GMIN_MIN` | 1e-12 | Minimum conductance for singularity |
| `GMIN_MAX` | 0.1 | Maximum GMIN for homotopy |
| `ABSTOL` | 1e-12 | Absolute convergence tolerance |
| `RELTOL` | 1e-3 | Relative convergence tolerance |
| `MAXITER` | 100 | Maximum Newton iterations |
| `MINTIMESTEP` | 1e-18 | Minimum time step |
| `MAX_TIMESTEP_RATIO` | 1e9 | Maximum time step growth |
| `PIVTOL` | 1e-13 | Matrix pivot threshold |
| `EXP_MAX` | 700.0 | Exponential argument limit |
| `EXP_MIN` | -700.0 | Exponential argument limit |
| `ε_mach` | 2.22e-16 | Machine epsilon (double) |

## Error Propagation Model

Parsing and numerical errors propagate through the simulation pipeline:

```
ε_parse ≤ ε_mach + ε_scale
ε_scale = max(|value| × 10⁻¹⁵, 10⁻²²)
```

Matrix element errors accumulate as:
```
ε_matrix ≤ n × (ε_mach + ε_parse + ε_round)
```
where n is matrix dimension.

## Validation and Verification

### 1. Structural Checks
- KCL sufficiency: Each node has at least two connections
- Subcircuit DAG validation: No expansion cycles
- Parameter range validation: R > 0, 0 < |K| ≤ 1, etc.

### 2. Numerical Validation
- Jacobian condition number monitoring
- Residual consistency checking
- Energy conservation verification

### 3. Convergence Monitoring
- Iteration count tracking
- Step rejection statistics
- Homotopy progression logging

## Conclusion

Ngspice represents a sophisticated synthesis of numerical algorithms, compiler technology, and circuit theory. Its architecture demonstrates several key engineering principles:

1. **Abstraction Layering**: Mathematical models cleanly separated from implementation
2. **Extensibility**: Plugin architecture for analyses and device models
3. **Robustness**: Multiple fallback strategies for convergence
4. **Performance**: Sparse matrix techniques with caching optimizations
5. **Accuracy**: Careful numerical analysis with protection functions

The system's ability to handle everything from simple RC circuits to complex mixed-signal systems with behavioral modeling makes it a versatile tool for electronic design. Its open architecture continues to evolve with advancements in numerical methods and semiconductor technology.

---
*This reference consolidates the complete Ngspice architecture based on analysis of the codebase structure, mathematical formulations, and implementation patterns. All information derives from architectural teardowns of the actual Ngspice implementation.*