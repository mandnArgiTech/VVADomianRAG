# Device Models: Inductors and VCVS

_Generated 2026-04-11 13:47 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvsload.c`

# Chapter: Device Models: Inductors and VCVS

## Introduction

The Ngspice simulation engine implements fundamental circuit elements through specialized device models that translate physical equations into numerical matrix formulations. This chapter examines the implementation of two critical device types: inductors and voltage-controlled voltage sources (VCVS). The inductor model in `indsetup.c` and `indload.c` implements the differential equation **v_L(t) = L·di_L/dt** through time discretization using numerical integration methods (Backward Euler, Trapezoidal Rule, and Gear multi-step). The VCVS model in `vcvsload.c` implements the ideal voltage transfer relationship **V_out = μ·V_in** through a constrained Modified Nodal Analysis (MNA) formulation. These implementations demonstrate how Ngspice transforms continuous-time device physics into discrete algebraic systems compatible with sparse matrix solvers, while maintaining numerical stability through careful attention to integration method properties, matrix conditioning, and error control.

## Mathematical Formulation

### 1. Inductor Device Model

#### 1.1 Continuous-Time Differential Equation

The fundamental inductor relationship in SPICE simulation is given by:

```
v_L(t) = L · di_L/dt
```

Where:
- `v_L(t)`: Instantaneous voltage across the inductor
- `i_L(t)`: Current flowing through the inductor
- `L`: Inductance value (Henries)
- `di_L/dt`: Time derivative of inductor current

This first-order differential equation requires discretization for numerical solution in transient analysis.

#### 1.2 State Variable Representation

In Ngspice's state-space formulation, the inductor contributes one state variable:

```
x = i_L
dx/dt = (1/L) · v_L
```

The state vector `x` is stored in `CKTcircuit.CKTstates`, with the inductor's specific entry pointed to by `INDinstance.INDstate`.

#### 1.3 Flux Conservation Formulation

An equivalent formulation using magnetic flux `Φ` is also maintained:

```
Φ(t) = L · i_L(t) = ∫ v_L(τ) dτ
v_L(t) = dΦ/dt
```

The flux value `INDinstance.INDflux` is updated each time step to maintain numerical consistency and support initial conditions.

### 2. Time Discretization Methods for Inductors

#### 2.1 General Discretization Framework

All integration methods in Ngspice transform the continuous differential equation into a discrete algebraic companion model of the form:

```
i_L^n = g_eq · v_L^n + i_eq
```

Where:
- `i_L^n`, `v_L^n`: Current and voltage at time step `n`
- `g_eq`: Equivalent conductance of the companion model
- `i_eq`: Equivalent current source representing history terms

#### 2.2 Backward Euler Discretization

**Mathematical Derivation:**
```
di_L/dt ≈ (i_L^n - i_L^{n-1})/h
v_L^n = L · (i_L^n - i_L^{n-1})/h
```

**Rearranged for MNA:**
```
i_L^n = (h/L) · v_L^n + i_L^{n-1}
```

**Companion Model Parameters:**
```
g_eq = h/L
i_eq = i_L^{n-1}
```

**Matrix Stamp (Branch Equation Form):**
```
⎡ 0   0   1 ⎤ ⎡ V_pos ⎤   ⎡ 0 ⎤
⎢ 0   0  -1 ⎥ ⎢ V_neg ⎥ = ⎢ 0 ⎥
⎣ 1  -1  L/h⎦ ⎣ I_L   ⎦   ⎣ (L/h)·i_L^{n-1} ⎦
```

#### 2.3 Trapezoidal Rule Discretization

**Mathematical Derivation:**
```
i_L^n = i_L^{n-1} + (h/(2L))·(v_L^{n-1} + v_L^n)
```

**Rearranged for MNA:**
```
v_L^n - (2L/h)·(i_L^n - i_L^{n-1}) + v_L^{n-1} = 0
```

**Companion Model Parameters:**
```
g_eq = 2L/h
i_eq = g_eq·i_L^{n-1} - v_L^{n-1}
```

**Matrix Stamp:**
```
⎡ 0   0   1 ⎤ ⎡ V_pos ⎤   ⎡ 0 ⎤
⎢ 0   0  -1 ⎥ ⎢ V_neg ⎥ = ⎢ 0 ⎥
⎣ 1  -1  2L/h⎦ ⎣ I_L   ⎦   ⎣ (2L/h)·i_L^{n-1} - v_L^{n-1} ⎦
```

#### 2.4 Gear Multi-step Integration

**General Formula (order p):**
```
i_L^n = Σ_{k=1}^p α_k·i_L^{n-k} + β_0·(h/L)·v_L^n
```

**Coefficients for Orders 1-6:**
- Order 1 (Backward Euler): α₁ = 1.0, β₀ = 1.0
- Order 2: α₁ = 4/3, α₂ = -1/3, β₀ = 2/3
- Order 3: α₁ = 18/11, α₂ = -9/11, α₃ = 2/11, β₀ = 6/11
- Order 4: α₁ = 48/25, α₂ = -36/25, α₃ = 16/25, α₄ = -3/25, β₀ = 12/25
- Order 5: α₁ = 300/137, α₂ = -300/137, α₃ = 200/137, α₄ = -75/137, α₅ = 12/137, β₀ = 60/137
- Order 6: α₁ = 360/147, α₂ = -450/147, α₃ = 400/147, α₄ = -225/147, α₅ = 72/147, α₆ = -10/147, β₀ = 60/147

**Companion Model Parameters:**
```
g_eq = L/(β₀·h)
i_eq = g_eq · Σ_{k=1}^p α_k·i_L^{n-k}
```

### 3. Voltage-Controlled Voltage Source (VCVS) Model

#### 3.1 Ideal VCVS Equations

The VCVS is defined by two fundamental equations:

**Voltage Transfer Relation:**
```
V_out = μ · V_in
```
Where:
- `V_out = V_pos - V_neg`: Output voltage
- `V_in = V_cont+ - V_cont-`: Input (control) voltage
- `μ`: Voltage gain

**Control Port Current Constraint:**
```
I_cont+ = I_cont- = 0
```
No current flows into the ideal control port.

#### 3.2 Modified Nodal Analysis Formulation

The VCVS requires one additional branch current variable `I_branch` for the output port, leading to these MNA equations:

1. **Output Node KCL Equations:**
   ```
   I_pos = +I_branch
   I_neg = -I_branch
   ```

2. **Branch Voltage Constraint:**
   ```
   V_pos - V_neg - μ·(V_cont+ - V_cont-) = 0
   ```

3. **Control Port Equations:**
   ```
   I_cont+ = 0
   I_cont- = 0
   ```

#### 3.3 Complete MNA Matrix Stamp

For nodes (out+, out-, ctrl+, ctrl-) and branch equation `m`:

```
⎡ 0   0   0   0   +1 ⎤ ⎡ V_out+   ⎤   ⎡ 0 ⎤
⎢ 0   0   0   0   -1 ⎥ ⎢ V_out-   ⎥   ⎢ 0 ⎥
⎢ 0   0   0   0    0 ⎥ ⎢ V_ctrl+  ⎥ = ⎢ 0 ⎥
⎢ 0   0   0   0    0 ⎥ ⎢ V_ctrl-  ⎥   ⎢ 0 ⎥
⎣+1  -1  -μ  +μ    0 ⎦ ⎣ I_branch ⎦   ⎣ 0 ⎦
```

**Matrix Element Contributions:**
- Row `out+`, Col `m`: `+1` (from `I_pos = +I_branch`)
- Row `out-`, Col `m`: `-1` (from `I_neg = -I_branch`)
- Row `m`, Col `out+`: `+1` (from `V_pos` term in branch equation)
- Row `m`, Col `out-`: `-1` (from `-V_neg` term in branch equation)
- Row `m`, Col `ctrl+`: `-μ` (from `-μ·V_cont+` term)
- Row `m`, Col `ctrl-`: `+μ` (from `+μ·V_cont-` term)

## Convergence Analysis

### 1. Inductor Numerical Stability

#### 1.1 Stability Regions for Integration Methods

**Backward Euler (L-stable):**
- Stability region: `{z ∈ ℂ : |1/(1 - z)| ≤ 1}`
- Contains entire left half-plane
- Strong numerical damping: suppresses high-frequency oscillations
- Unconditionally stable for all `h > 0`

**Trapezoidal Rule (A-stable):**
- Stability region: `{z ∈ ℂ : Re(z) ≤ 0}`
- Contains entire left half-plane
- No numerical damping: can produce artificial oscillations
- Unconditionally stable but may show numerical ringing

**Gear Methods (Stiffly Stable):**
- Stability region shrinks with increasing order
- Order 1-2: A-stable
- Order 3-6: Stiffly stable (stable for sufficiently small `h·λ` where `Re(λ) < 0`)

#### 1.2 Time Step Limitations

**Trapezoidal Rule Oscillation Condition:**
For an inductor `L` in parallel with resistor `R`:
```
If h > 2L/R, numerical oscillations may occur
```
This arises from the discrete-time pole location:
```
z = (1 + hR/(2L)) / (1 - hR/(2L))
```
When `hR/(2L) > 1`, `z < -1` causing alternating sign solutions.

**Backward Euler Stability:**
```
Always stable for any h > 0
```
Pole location: `z = 1/(1 + hR/L)` which is always `0 < z < 1`.

#### 1.3 Local Truncation Error (LTE)

**Trapezoidal Rule LTE:**
```
LTE ≈ (h³/12) · (d³i_L/dt³)
```
For sinusoidal current `i_L(t) = I·sin(ωt)`:
```
LTE ≈ (h³/12) · ω³I
```

**Backward Euler LTE:**
```
LTE ≈ (h²/2) · (d²i_L/dt²)
```
For sinusoidal current:
```
LTE ≈ (h²/2) · ω²I
```

**Gear Method LTE (order p):**
```
LTE ≈ O(h^{p+1}) · (d^{p+1}i_L/dt^{p+1})
```

#### 1.4 Error Accumulation and DC Drift

**Flux Conservation Property:**
The trapezoidal rule preserves the numerical analog of flux conservation:
```
Φ^n - Φ^{n-1} = (h/2)·(v_L^{n-1} + v_L^n)
```
This prevents DC drift in inductor current over long simulations.

**Backward Euler Drift:**
Backward Euler can exhibit numerical drift as it doesn't conserve flux exactly:
```
Φ^n - Φ^{n-1} = h·v_L^n
```
May require smaller time steps for accurate long-term behavior.

### 2. VCVS Numerical Properties

#### 2.1 Matrix Conditioning Analysis

**Zero Diagonal Elements:**
The VCVS stamp creates zero diagonal entries for control nodes in their respective rows:
```
Row ctrl+: [0, 0, 0, 0, 0]
Row ctrl-: [0, 0, 0, 0, 0]
```
This is acceptable only if:
1. Control nodes have other conductive paths (resistors, etc.)
2. The overall matrix remains nonsingular

**Singularity Conditions:**
The MNA matrix becomes singular if:
1. Control nodes are floating (no DC path to ground)
2. Gain `μ` creates a degenerate dependency between equations

**Condition Number:**
For large gains `|μ| >> 1`, the matrix condition number grows as:
```
κ(A) ≈ O(|μ|)
```
This can lead to numerical precision issues in the linear solver.

#### 2.2 Gain Scaling Effects

**Numerical Precision Requirements:**
For a VCVS with gain `μ`, the required floating-point precision scales as:
```
Required precision bits ≈ log₂(|μ|) + machine_precision
```
Large gains may necessitate extended precision or scaling transformations.

**Dynamic Range Issues:**
When `μ` spans many orders of magnitude:
1. Matrix entries vary widely in magnitude
2. Pivoting in LU decomposition becomes critical
3. Residual errors may be amplified by `μ`

#### 2.3 Feedback Stability with VCVS

**Loop Gain Analysis:**
When VCVS elements form feedback loops, the discrete-time system must satisfy:
```
|μ·H(z)| < 1 for all z on unit circle
```
Where `H(z)` is the discrete-time transfer function of the surrounding circuit.

**Numerical Oscillations:**
Feedback configurations can excite numerical modes, particularly with trapezoidal integration where:
```
If |μ·H(-1)| > 1, alternating sign solutions may grow
```

### 3. Combined Inductor-VCVS Stability

#### 3.1 Inductor in VCVS Feedback Loop

**Characteristic Equation:**
For an inductor `L` with VCVS gain `μ` in negative feedback:
```
Discrete: 1 + μ·G_eq(z) = 0
```
Where `G_eq(z)` is the discrete-time inductor impedance.

**Trapezoidal Integration:**
```
G_eq(z) = (h/2L)·(z+1)/(z-1)
Stability requires: |μ·(h/2L)·(z+1)/(z-1)| < 1
```

**Stability Criterion:**
```
For μ < 0 (negative feedback): Always stable
For μ > 0 (positive feedback): Requires h < 2L/μ
```

#### 3.2 Time Step Selection Criteria

**Accuracy-Driven Step:**
Based on inductor current dynamics:
```
h_acc ≈ 0.01 · min(τ_L) where τ_L = L/R_eq
```
Where `R_eq` is the equivalent resistance seen by the inductor.

**Stability-Driven Step:**
For trapezoidal rule with VCVS feedback:
```
h_stab < 2L/|μ| for positive feedback
```

**Final Time Step:**
```
h = min(h_acc, h_stab, h_user_max)
```

## 4. Convergence in Newton-Raphson Iteration

### 4.1 Inductor Nonlinearity (Saturation Effects)

**Nonlinear Inductor Model:**
If inductance varies with current `L = L(i_L)`, the differential equation becomes:
```
v_L = d(L(i_L)·i_L)/dt = L(i_L)·di_L/dt + i_L·(dL/di_L)·di_L/dt
```

**Jacobian Contribution:**
```
∂i_L^n/∂v_L^n = h/(L + i_L·dL/di_L)  (for backward Euler)
```
This nonlinearity affects Newton convergence rate.

### 4.2 VCVS Linear Convergence

**Exact Linear Model:**
The ideal VCVS is purely linear, contributing constant matrix entries:
```
Convergence in 1 Newton iteration (if circuit is linear)
```

**Numerical Round-off Effects:**
Finite precision can cause residual errors:
```
‖F(x)‖ ≈ ε_machine · |μ| · ‖x‖
```
Where `ε_machine` is machine epsilon.

### 4.3 Combined Convergence Rate

**Newton Iteration Count:**
For circuits containing both inductors and VCVS:
- Linear VCVS parts converge in 1 iteration
- Nonlinear inductor parts converge at quadratic rate (near solution)
- Overall convergence dominated by most nonlinear element

**Damping Requirements:**
When large VCVS gains combine with inductor dynamics, Newton damping may be needed:
```
λ = min(1, 1/(|μ|·h/L))
```
Where `λ` is the Newton step damping factor.

## 5. Initial Condition Handling

### 5.1 Inductor Initial Conditions

**Mathematical Consistency:**
Initial current `i_L(0) = I_0` must satisfy:
```
v_L(0) = L · di_L/dt|_{t=0}
```
Requires consistent initialization of both `i_L` and `di_L/dt`.

**Numerical Implementation:**
In `INDload()` with `MODEINITTRAN` flag:
```
i_L^0 = INDinstance.INDic
Φ^0 = L · i_L^0
```

### 5.2 VCVS Initial Conditions

**DC Operating Point:**
For VCVS in DC analysis:
```
V_out = μ · V_in
```
Must be consistent with overall DC solution.

**Transient Initialization:**
Initial output voltage determined by initial control voltage:
```
V_out(0) = μ · (V_cont+(0) - V_cont-(0))
```

## 6. Error Propagation and Control

### 6.1 Local Error Estimation

**Inductor Current Error:**
For predictor-corrector methods:
```
Error estimate = |i_L^n - i_L^{n,pred}|
```
Used in time step control algorithm.

**Global Error Bound:**
For Lipschitz continuous systems:
```
|i_L(t_n) - i_L^n| ≤ (C/λ)·(e^{λt_n} - 1)·LTE
```
Where `λ` is the Lipschitz constant, `C` is method-dependent constant.

### 6.2 Adaptive Time Step Control

**LTE-Based Adjustment:**
```
h_new = h_old · min(2.0, max(0.5, √(τ/error_estimate)))
```
Where `τ` is user-specified error tolerance.

**Stability-Based Limiting:**
For inductor-VCVS combinations:
```
h_max = min(2L/R_eq, 2L/|μ|) for trapezoidal rule
```

These mathematical formulations and convergence analyses provide the complete theoretical foundation for Ngspice's implementation of inductor and VCVS device models, directly mapping to the algorithms in `indsetup.c`, `indload.c`, and `vcvsload.c`.

## C Implementation

### 1. Inductor Device Implementation (`indsetup.c`, `indload.c`)

#### 1.1 Core Data Structures

The mathematical inductor model **v_L(t) = L·di_L/dt** maps to the `INDinstance` structure:

```c
typedef struct sINDinstance {
    GENinstance GEN;           /* Generic device instance header */
    
    /* Node connections - mapping to MNA matrix indices */
    int INDposNode;            /* Positive node index in x vector */
    int INDnegNode;            /* Negative node index in x vector */
    int INDbrEq;               /* Branch equation index for i_L */
    int INDintNode;            /* Internal node (if used) */
    
    /* Device parameters */
    double INDinduct;          /* L: Inductance value (Henries) */
    double INDic;              /* i_L(0): Initial current condition */
    double INDflux;            /* Φ = L·i_L: Magnetic flux */
    double INDconv;            /* Convergence history flag */
    
    /* State variables */
    double INDcurrent;         /* i_L^n: Current at time step n */
    double INDvolt;            /* v_L^n: Voltage at time step n */
    double *INDstate;          /* Pointer to i_L in CKTstates vector */
    double *INDderivs;         /* Pointer to di_L/dt in derivatives */
    
    /* Sparse matrix pointers - direct access to matrix elements */
    double *INDposPosPtr;      /* G[pos][pos] for companion model */
    double *INDposNegPtr;      /* G[pos][neg] for companion model */
    double *INDnegPosPtr;      /* G[neg][pos] for companion model */
    double *INDnegNegPtr;      /* G[neg][neg] for companion model */
    double *INDposBrPtr;       /* G[pos][branch] for branch eq */
    double *INDnegBrPtr;       /* G[neg][branch] for branch eq */
    double *INDbrPosPtr;       /* G[branch][pos] for branch eq */
    double *INDbrNegPtr;       /* G[branch][neg] for branch eq */
    double *INDbrBrPtr;        /* G[branch][branch] for branch eq */
} INDinstance;
```

#### 1.2 Setup Phase Implementation (`indsetup.c`)

The setup function establishes the mathematical framework in the MNA system:

```c
int INDsetup(SMPmatrix *matrix, GENmodel *inModel, 
             CKTcircuit *ckt, int *states) {
    INDmodel *model = (INDmodel*)inModel;
    INDinstance *here;
    
    for (; model != NULL; model = INDnextModel(model)) {
        for (here = INDinstances(model); here != NULL; 
             here = INDnextInstance(here)) {
            
            /* Allocate branch equation for i_L in MNA system */
            /* Mathematical: Adds equation for v_L = L·di_L/dt */
            here->INDbrEq = ckt->CKTnumStates;
            ckt->CKTnumStates++;  /* Increment system dimension */
            
            /* Allocate state vector entry for i_L */
            /* Mathematical: x_k = i_L where k = *states */
            here->INDstate = ckt->CKTstates + *states;
            *states += 1;  /* Each inductor adds one state variable */
            
            /* Set up sparse matrix pointers for efficient stamping */
            /* These map to specific elements in the MNA matrix G */
            SMPmakeElt(matrix, here->INDposNode, here->INDbrEq, 
                      &here->INDposBrPtr);  /* G[pos][branch] */
            SMPmakeElt(matrix, here->INDnegNode, here->INDbrEq,
                      &here->INDnegBrPtr);  /* G[neg][branch] */
            SMPmakeElt(matrix, here->INDbrEq, here->INDposNode,
                      &here->INDbrPosPtr);  /* G[branch][pos] */
            SMPmakeElt(matrix, here->INDbrEq, here->INDnegNode,
                      &here->INDbrNegPtr);  /* G[branch][neg] */
            SMPmakeElt(matrix, here->INDbrEq, here->INDbrEq,
                      &here->INDbrBrPtr);   /* G[branch][branch] */
            
            /* Initialize flux: Φ(0) = L·i_L(0) */
            here->INDflux = here->INDinduct * here->INDic;
        }
    }
    return OK;
}
```

#### 1.3 Load Routine Implementation (`indload.c`)

The load function implements the time discretization of **v_L = L·di_L/dt**:

```c
int INDload(GENmodel *inModel, CKTcircuit *ckt) {
    INDmodel *model = (INDmodel*)inModel;
    INDinstance *here;
    double h;      /* Time step: h = t_n - t_{n-1} */
    double geq;    /* Equivalent conductance: g_eq */
    double ceq;    /* Equivalent current source: i_eq */
    
    /* Get current time step from circuit */
    h = ckt->CKTdelta;
    
    for (; model != NULL; model = INDnextModel(model)) {
        for (here = INDinstances(model); here != NULL;
             here = INDnextInstance(here)) {
            
            /* Initial transient condition handling */
            if (ckt->CKTmode & MODEINITTRAN) {
                /* Mathematical: i_L^0 = I_0 */
                here->INDcurrent = here->INDic;
                *(here->INDstate) = here->INDcurrent;
            }
            
            /* Select integration method based on discretization scheme */
            switch (ckt->CKTintegrateMethod) {
                case INTEG_TRAPEZOIDAL:
                    /* Trapezoidal rule: g_eq = 2L/h, i_eq = g_eq·i_L^{n-1} - v_L^{n-1} */
                    geq = 2.0 * here->INDinduct / h;
                    ceq = geq * here->INDcurrent + 
                          (2.0 / h) * here->INDflux;
                    break;
                    
                case INTEG_GEAR:
                    /* Gear multi-step: i_L^n = Σα_k·i_L^{n-k} + β_0·(h/L)·v_L^n */
                    {
                        double sum = 0.0;
                        for (int i = 0; i < ckt->CKTorder; i++) {
                            sum += ckt->CKTalpha[i] * here->INDpast[i];
                        }
                        geq = ckt->CKTbeta * here->INDinduct / h;
                        ceq = geq * sum;
                    }
                    break;
                    
                case INTEG_BACKWARD_EULER:
                default:
                    /* Backward Euler: g_eq = L/h, i_eq = (L/h)·i_L^{n-1} */
                    geq = here->INDinduct / h;
                    ceq = geq * here->INDpast[0];
                    break;
            }
            
            /* Stamp matrix elements for branch equation: V_pos - V_neg - g_eq·I_L = i_eq */
            
            /* G[pos][branch] = +1 (from I_pos = +I_branch) */
            *(here->INDposBrPtr) += 1.0;
            
            /* G[neg][branch] = -1 (from I_neg = -I_branch) */
            *(here->INDnegBrPtr) -= 1.0;
            
            /* G[branch][branch] = -g_eq (from -g_eq·I_L term) */
            *(here->INDbrBrPtr) -= geq;
            
            /* Complementary equations: G[branch][pos] = +1, G[branch][neg] = -1 */
            *(here->INDbrPosPtr) += 1.0;
            *(here->INDbrNegPtr) -= 1.0;
            
            /* Right-hand side: b[branch] = i_eq */
            ckt->CKTrhs[here->INDbrEq] += ceq;
            
            /* Store history for next time step */
            here->INDpast[0] = here->INDcurrent;
            here->INDflux = here->INDinduct * here->INDcurrent;
        }
    }
    return OK;
}
```

#### 1.4 Companion Model Implementation

The companion model transforms the differential equation into an algebraic form:

```c
void updateInductorCompanion(INDinstance *here, CKTcircuit *ckt) {
    double h = ckt->CKTdelta;
    double geq, ieq;
    
    /* Compute companion model parameters based on integration method */
    switch (ckt->CKTintegrateMethod) {
        case INTEG_TRAPEZOIDAL:
            /* Mathematical: g_eq = h/(2L), i_eq = i_L^{n-1} + (h/(2L))·v_L^{n-1} */
            geq = h / (2.0 * here->INDinduct);
            ieq = here->INDcurrent + 
                  (h / (2.0 * here->INDinduct)) * here->INDvolt;
            break;
            
        case INTEG_BACKWARD_EULER:
        default:
            /* Mathematical: g_eq = h/L, i_eq = i_L^{n-1} */
            geq = h / here->INDinduct;
            ieq = here->INDcurrent;
            break;
    }
    
    /* Stamp companion conductance matrix */
    /* G[pos][pos] += g_eq, G[neg][neg] += g_eq */
    *(here->INDposPosPtr) += geq;
    *(here->INDnegNegPtr) += geq;
    
    /* G[pos][neg] -= g_eq, G[neg][pos] -= g_eq */
    *(here->INDposNegPtr) -= geq;
    *(here->INDnegPosPtr) -= geq;
    
    /* Stamp right-hand side current sources */
    /* b[pos] -= i_eq, b[neg] += i_eq */
    ckt->CKTrhs[here->INDposNode] -= ieq;
    ckt->CKTrhs[here->INDnegNode] += ieq;
}
```

#### 1.5 State Update Implementation

```c
void updateInductorState(INDinstance *here, CKTcircuit *ckt) {
    /* Compute voltage from solution vector: v_L = V_pos - V_neg */
    double v_L = ckt->CKTrhsOld[here->INDposNode] - 
                 ckt->CKTrhsOld[here->INDnegNode];
    
    /* Update current using discretized integration formula */
    switch (ckt->CKTintegrateMethod) {
        case INTEG_TRAPEZOIDAL:
            /* i_L^n = i_L^{n-1} + (h/(2L))·(v_L^{n-1} + v_L^n) */
            here->INDcurrent = here->INDpast[0] + 
                (ckt->CKTdelta/(2.0*here->INDinduct)) * 
                (here->INDpastVolt + v_L);
            break;
            
        case INTEG_BACKWARD_EULER:
            /* i_L^n = i_L^{n-1} + (h/L)·v_L^n */
            here->INDcurrent = here->INDpast[0] + 
                (ckt->CKTdelta/here->INDinduct) * v_L;
            break;
    }
    
    /* Store history for next iteration */
    here->INDpast[0] = here->INDcurrent;      /* i_L^{n-1} */
    here->INDpastVolt = v_L;                  /* v_L^{n-1} */
    here->INDflux = here->INDinduct * here->INDcurrent;  /* Φ^n = L·i_L^n */
    
    /* Update state vector entry */
    *(here->INDstate) = here->INDcurrent;
}
```

### 2. Voltage-Controlled Voltage Source Implementation (`vcvsload.c`)

#### 2.1 VCVS Data Structure

The ideal VCVS equation **V_out = μ·V_in** maps to:

```c
typedef struct sVCVSinstance {
    GENinstance GEN;           /* Generic device instance header */
    
    /* Node connections */
    int VCVSposNode;          /* Output positive node index */
    int VCVSnegNode;          /* Output negative node index */
    int VCVSposContNode;      /* Control positive node index */
    int VCVSnegContNode;      /* Control negative node index */
    int VCVSbrEq;             /* Branch equation index for I_branch */
    
    /* Device parameter */
    double VCVSgain;          /* μ: Voltage gain */
    
    /* Sparse matrix pointers for all non-zero entries */
    double *VCVSposPosPtr;    /* G[out+][out+] */
    double *VCVSposNegPtr;    /* G[out+][out-] */
    double *VCVSNegPosPtr;    /* G[out-][out+] */
    double *VCVSNegNegPtr;    /* G[out-][out-] */
    double *VCVSposBrPtr;     /* G[out+][branch] */
    double *VCVSNegBrPtr;     /* G[out-][branch] */
    double *VCVSbrPosPtr;     /* G[branch][out+] */
    double *VCVSbrNegPtr;     /* G[branch][out-] */
    double *VCVSbrContPosPtr; /* G[branch][ctrl+] */
    double *VCVSbrContNegPtr; /* G[branch][ctrl-] */
    double *VCVSbrBrPtr;      /* G[branch][branch] */
} VCVSinstance;
```

#### 2.2 VCVS Load Implementation

The load function implements the MNA stamp for **V_pos - V_neg - μ·(V_cont+ - V_cont-) = 0**:

```c
int VCVSload(GENmodel *inModel, CKTcircuit *ckt) {
    VCVSmodel *model = (VCVSmodel*)inModel;
    VCVSinstance *here;
    
    for (; model != NULL; model = VCVSnextModel(model)) {
        for (here = VCVSinstances(model); here != NULL;
             here = VCVSnextInstance(here)) {
            
            double gain = here->VCVSgain;  /* μ */
            
            /* Stamp output node equations: I_pos = +I_branch, I_neg = -I_branch */
            
            /* G[out+][branch] = +1 */
            if (here->VCVSposNode != 0) {  /* Skip if grounded */
                *(here->VCVSposBrPtr) += 1.0;
                *(here->VCVSbrPosPtr) += 1.0;  /* Symmetric entry */
            }
            
            /* G[out-][branch] = -1 */
            if (here->VCVSnegNode != 0) {  /* Skip if grounded */
                *(here->VCVSNegBrPtr) -= 1.0;
                *(here->VCVSbrNegPtr) -= 1.0;  /* Symmetric entry */
            }
            
            /* Stamp branch equation: V_pos - V_neg - μ·V_cont+ + μ·V_cont- = 0 */
            
            /* V_pos term: G[branch][out+] = +1 */
            if (here->VCVSposNode != 0) {
                *(here->VCVSbrPosPtr) += 1.0;
            }
            
            /* V_neg term: G[branch][out-] = -1 */
            if (here->VCVSnegNode != 0) {
                *(here->VCVSbrNegPtr) -= 1.0;
            }
            
            /* -μ·V_cont+ term: G[branch][ctrl+] = -μ */
            if (here->VCVSposContNode != 0) {
                *(here->VCVSbrContPosPtr) -= gain;
            }
            
            /* +μ·V_cont- term: G[branch][ctrl-] = +μ */
            if (here->VCVSnegContNode != 0) {
                *(here->VCVSbrContNegPtr) += gain;
            }
            
            /* Note: No RHS contribution since equation = 0 */
        }
    }
    return OK;
}
```

#### 2.3 Sparse Matrix Pointer Setup

The mathematical matrix stamp requires efficient access to specific elements:

```c
/* Setup function excerpt showing pointer initialization */
void VCVSsetupPointers(VCVSinstance *here, SMPmatrix *matrix) {
    /* Map mathematical matrix positions to C pointers */
    
    /* Output node to branch connections */
    SMPmakeElt(matrix, here->VCVSposNode, here->VCVSbrEq,
              &here->VCVSposBrPtr);  /* G[out+][branch] */
    SMPmakeElt(matrix, here->VCVSnegNode, here->VCVSbrEq,
              &here->VCVSNegBrPtr);  /* G[out-][branch] */
    
    /* Branch equation coefficients */
    SMPmakeElt(matrix, here->VCVSbrEq, here->VCVSposNode,
              &here->VCVSbrPosPtr);  /* G[branch][out+] */
    SMPmakeElt(matrix, here->VCVSbrEq, here->VCVSnegNode,
              &here->VCVSbrNegPtr);  /* G[branch][out-] */
    SMPmakeElt(matrix, here->VCVSbrEq, here->VCVSposContNode,
              &here->VCVSbrContPosPtr);  /* G[branch][ctrl+] */
    SMPmakeElt(matrix, here->VCVSbrEq, here->VCVSnegContNode,
              &here->VCVSbrContNegPtr);  /* G[branch][ctrl-] */
    
    /* Diagonal element (typically zero for ideal VCVS) */
    SMPmakeElt(matrix, here->VCVSbrEq, here