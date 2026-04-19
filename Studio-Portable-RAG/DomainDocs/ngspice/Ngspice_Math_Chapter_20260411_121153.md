# Ngspice algorithm reference

_Generated 2026-04-11 12:11 UTC — `crewai/ngspice_book_factory.py`_

**Source file:** `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/niniter.c`

# Chapter 5: Non-Linear Iteration Controller (`niniter.c`)

## Introduction

The `niniter.c` file implements the core Newton-Raphson iteration controller for NGSPICE's non-linear circuit equation solver. This module serves as the computational engine that drives the solution of the system of non-linear algebraic equations derived from Kirchhoff's Current and Voltage Laws (KCL/KVL). At its essence, it solves the fundamental circuit equation `F(x) = 0`, where `F: ℝⁿ → ℝⁿ` represents the non-linear circuit equations and `x ∈ ℝⁿ` is the vector of unknown node voltages and branch currents.

The implementation combines rigorous numerical mathematics with practical engineering considerations, providing a robust solver capable of handling circuits ranging from simple resistive networks to complex mixed-signal designs with highly non-linear semiconductor devices. The controller manages the complete iteration lifecycle: from initial guess generation through Newton updates, convergence checking, and recovery strategies when standard methods fail.

What distinguishes NGSPICE's implementation is its comprehensive approach to numerical stability. Beyond the basic Newton-Raphson algorithm, the module incorporates device limiting functions to prevent exponential overflow in semiconductor junctions, continuation methods (source stepping and gmin stepping) for difficult convergence scenarios, and sophisticated tolerance-based convergence criteria that balance computational efficiency with solution accuracy. The architecture cleanly separates mathematical formulation from implementation details while maintaining direct correspondence between the mathematical equations and their C code realization.

## Mathematical Formulation

The core non-linear solver in NGSPICE implements the Newton-Raphson method to solve the system of non-linear algebraic equations derived from Kirchhoff's Current and Voltage Laws (KCL/KVL). For a circuit with `n` unknowns (node voltages and branch currents), the mathematical problem is formulated as:

```
F(x) = 0
```

where `F: ℝⁿ → ℝⁿ` represents the non-linear circuit equations and `x ∈ ℝⁿ` is the vector of unknown node voltages and branch currents.

### Newton-Raphson Algorithm

The iterative solution proceeds according to the Newton-Raphson update equation:

```
x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ - J(x⁽ᵏ⁾)⁻¹F(x⁽ᵏ⁾)
```

where:
- `x⁽ᵏ⁾`: Solution vector at iteration `k`
- `J(x) = ∂F/∂x`: Jacobian matrix (circuit conductance matrix)
- `F(x)`: Right-hand side vector (current injections)

In practical implementation, this is computed by solving the linear system:

```
J(x⁽ᵏ⁾)·Δx⁽ᵏ⁾ = -F(x⁽ᵏ⁾)
```

followed by the update:

```
x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ + Δx⁽ᵏ⁾
```

### Jacobian Matrix Composition

The Jacobian matrix `J` contains the partial derivatives of device currents with respect to node voltages. For common semiconductor devices:

**Diode Model:**
```
I_d = I_s·[exp(V_d/(n·V_t)) - 1]
∂I_d/∂V_d = (I_s/(n·V_t))·exp(V_d/(n·V_t)) = g_d
```

**MOSFET (Level 1, Linear Region):**
```
I_ds = β·[(V_gs - V_t)·V_ds - V_ds²/2]·(1 + λ·V_ds)
∂I_ds/∂V_gs = β·V_ds
∂I_ds/∂V_ds = β·[(V_gs - V_t) - V_ds]·(1 + λ·V_ds) + β·λ·[(V_gs - V_t)·V_ds - V_ds²/2]
```

### Transient Analysis Formulation

For transient analysis, the equations include time derivatives:

```
F(x, dx/dt) = C·dx/dt + G·x + f(x) = 0
```

Using Backward Euler discretization with time step `h`:

```
C·(xⁿ⁺¹ - xⁿ)/h + G·xⁿ⁺¹ + f(xⁿ⁺¹) = 0
```

The corresponding Jacobian for the Newton iteration becomes:

```
J = C/h + G + ∂f/∂x
```

where `C` is the capacitance matrix, `G` is the conductance matrix, and `∂f/∂x` represents the derivatives of non-linear device currents.

### Device Limiting Functions

To prevent numerical overflow during iteration, NGSPICE employs limiting functions:

**PN Junction Limiting (`pnjlim`):**
```c
double pnjlim(double vnew, double vold, double vt, double vcrit, 
              double *vpred) {
    double delv = vnew - vold;
    
    if (vold >= vcrit && delv > 0) {
        // Forward bias limiting
        double arg = 1 + delv/vt;
        if (arg > 0) {
            vnew = vold + vt * log(arg);
        } else {
            vnew = vcrit;
        }
    } else if (vold <= -vcrit && delv < 0) {
        // Reverse bias limiting
        double arg = 1 - delv/vt;
        if (arg > 0) {
            vnew = vold - vt * log(arg);
        } else {
            vnew = -vcrit;
        }
    }
    
    *vpred = vnew;
    return vnew;
}
```

**FET Limiting (`fetlim`):**
```c
double fetlim(double vds, double vgs, double vto, 
              double *vds_pred, double *vgs_pred) {
    double vgst = vgs - vto;
    double vdsth = MAX(0, vgst);  // Threshold voltage
    
    // Limit Vds to prevent negative conductance
    if (vds > 0) {
        *vds_pred = vdsth * (1 - exp(-vds/vdsth));
    } else {
        *vds_pred = -vdsth * (1 - exp(vds/vdsth));
    }
    
    // Limit Vgs
    if (vgst > 0) {
        *vgs_pred = vto + 2 * vt * log(1 + exp(vgst/(2*vt)));
    } else {
        *vgs_pred = vto - 2 * vt * log(1 + exp(-vgst/(2*vt)));
    }
    
    return *vds_pred;
}
```

## Convergence Analysis

### Convergence Criteria

NGSPICE employs a mixed relative-absolute convergence criterion based on the infinity norm (maximum absolute value). The solution is considered converged when:

```
||x⁽ᵏ⁺¹⁾ - x⁽ᵏ⁾||∞ ≤ εᵣ·max(|x⁽ᵏ⁺¹⁾|, |x⁽ᵏ⁾|) + εₐ
```

where:
- `εᵣ = reltol`: Relative tolerance (typically 0.001)
- `εₐ = abstol`: Absolute tolerance (typically 1e-12)
- `||·||∞`: Infinity norm (maximum absolute value of vector elements)

### Implementation of Convergence Check

The convergence check is implemented as:

```c
int checkConvergence(CKTcircuit *ckt) {
    double max_change = 0.0;
    double max_voltage = 0.0;
    
    for (int i = 0; i < ckt->CKTmaxEqns; i++) {
        double change = fabs(ckt->CKTlhs[i] - ckt->CKToldLhs[i]);
        double voltage = MAX(fabs(ckt->CKTlhs[i]), fabs(ckt->CKToldLhs[i]));
        
        // Check voltage convergence
        if (i < ckt->CKTnumVoltages) {
            if (change > ckt->CKTcurTask->TSKvntol * voltage + ckt->CKTcurTask->TSKabstol) {
                return 0;  // Not converged
            }
        }
        
        // Track maximum changes for overall convergence
        if (change > max_change) {
            max_change = change;
        }
        if (voltage > max_voltage) {
            max_voltage = voltage;
        }
    }
    
    // Final convergence check using relative tolerance
    if (max_change > ckt->CKTcurTask->TSKreltol * max_voltage + ckt->CKTcurTask->TSKabstol) {
        return 0;
    }
    
    // Additional check on RHS (current) convergence
    for (int i = 0; i < ckt->CKTmaxEqns; i++) {
        double rhs_change = fabs(ckt->CKTrhs[i] - ckt->CKToldRhs[i]);
        if (rhs_change > ckt->CKTcurTask->TSKabstol * 10) {
            return 0;
        }
    }
    
    return 1;  // Converged
}
```

### Theoretical Convergence Properties

The Newton-Raphson method exhibits quadratic convergence near the solution:

```
||x⁽ᵏ⁺¹⁾ - x*|| ≤ C·||x⁽ᵏ⁾ - x*||²
```

where `C` depends on the Lipschitz constant of the Jacobian inverse. The convergence radius `ρ` satisfies:

```
ρ = min(1/(2L·M), ε)
```

where:
- `L`: Lipschitz constant of `J⁻¹`
- `M`: Bound on second derivative of `F`
- `ε`: Machine precision

### Convergence Enhancement Techniques

When standard Newton-Raphson fails to converge, NGSPICE employs continuation methods:

**Source Stepping:**
```c
void applySourceStepping(CKTcircuit *ckt) {
    static double lambda = 1.0;  // Continuation parameter
    
    if (ckt->CKTniIter > ckt->CKTmaxIter/2 && !converged) {
        // Reduce continuation parameter
        lambda = MAX(0.1, lambda * 0.5);
        
        // Scale independent sources
        for (GENmodel *model = ckt->CKTmodels[SRC]; model != NULL; 
             model = model->GENnextModel) {
            for (GENinstance *inst = model->GENinstances; inst != NULL;
                 inst = inst->GENnextInstance) {
                if (inst->SRCdcValue != 0) {
                    inst->SRCdcValue *= lambda;
                }
            }
        }
    }
}
```

**Gmin Stepping:**
```c
void applyGminStepping(CKTcircuit *ckt) {
    double gmin_orig = ckt->CKTgminOrig;
    double gmin_current = ckt->CKTgmin;
    
    if (!converged && ckt->CKTniIter > ckt->CKTmaxIter/3) {
        // Increase gmin to improve convergence
        gmin_current *= 10.0;
        ckt->CKTgmin = MIN(gmin_current, 1e-3);
        
        // Add gmin conductances to Jacobian diagonal
        for (int i = 0; i < ckt->CKTnumVoltages; i++) {
            int diag_pos = getDiagonalPosition(i);
            Matrix[diag_pos] += ckt->CKTgmin;
        }
    } else if (converged && ckt->CKTgmin > gmin_orig) {
        // Reduce gmin back to original value
        ckt->CKTgmin = MAX(gmin_orig, ckt->CKTgmin / 100.0);
    }
}
```

### Iteration Control and Statistics

The iteration loop includes comprehensive monitoring:

```c
for (iter = 0; iter < CKTmaxIter; iter++) {
    // Save old solution for convergence check
    memcpy(oldSolution, newSolution, CKTmaxEqns * sizeof(double));
    memcpy(oldRhs, rhs, CKTmaxEqns * sizeof(double));
    
    // Load circuit equations: F(x) and J(x)
    CKTterTask(CKTcircuit*);
    
    // Apply device limiting if needed
    if (limiting_needed) {
        applyDeviceLimiting(CKTcircuit*);
    }
    
    // Solve linear system: J·Δx = -F
    spSolve(Matrix, newSolution, rhs, RowMap, ColMap);
    
    // Update solution: x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ + Δx
    for (int i = 0; i < CKTmaxEqns; i++) {
        newSolution[i] = oldSolution[i] + newSolution[i];
    }
    
    // Check convergence
    converged = checkConvergence(CKTcircuit*);
    if (converged) {
        break;
    }
    
    // Apply source stepping if not converging
    if (iter > CKTmaxIter/2 && !converged) {
        applySourceStepping(CKTcircuit*);
    }
}
```

Statistics are tracked for analysis and debugging:
```c
// Update statistics after iteration
ckt->CKTstat->STATiter++;
ckt->CKTstat->STATtranIter += (ckt->CKTmode == MODETRAN);
ckt->CKTstat->STATdcIter += (ckt->CKTmode == MODEDC);
```

### Failure Recovery

When convergence fails, NGSPICE attempts recovery strategies:

```c
if (!converged && iter == CKTmaxIter) {
    // Newton-Raphson failed to converge
    if (ckt->CKTgmin < GMIN_MAX) {
        // Try gmin stepping
        ckt->CKTgmin *= 10.0;
        ckt->CKTniIter = 0;  // Reset iteration
        return NI_GMIN_STEP;
    } else if (lambda > LAMBDA_MIN) {
        // Try source stepping
        return NI_SRC_STEP;
    } else {
        // Final failure
        return NI_NOCONV;
    }
}
```

The convergence analysis demonstrates that NGSPICE implements a robust iterative solver that combines theoretical Newton-Raphson convergence with practical numerical stabilization techniques, making it suitable for a wide range of circuit simulation scenarios from well-behaved linear circuits to highly non-linear, difficult-to-converge designs.

## C Implementation

### Data Structures for Circuit Representation

The Newton-Raphson solver in NGSPICE operates on a comprehensive circuit data structure that maps directly to the mathematical formulation:

#### Primary Circuit Structure
```c
typedef struct CKTcircuit {
    int CKTmaxEqns;           // Dimension n of solution vector x
    double *CKTrhs;           // RHS vector F(x) (current injections)
    double *CKTlhs;           // LHS vector x (solution: voltages/currents)
    double *CKToldRhs;        // Previous F(x) for convergence check
    double *CKToldLhs;        // Previous x for convergence check
    double CKTcurTask->TSKreltol; // Relative tolerance εᵣ
    double CKTcurTask->TSKabstol; // Absolute tolerance εₐ
    double CKTcurTask->TSKvntol;  // Voltage-specific tolerance
    double CKTgmin;           // Minimum conductance for gmin stepping
    int CKTniIter;           // Current Newton iteration count
    int CKTmaxIter;          // Maximum allowed iterations
    int CKTmode;             // Operating mode (DC, AC, TRAN)
    int CKTstat->STATiter;   // Statistics: total iterations
    GENmodel **CKTmodels;    // Array of device models
    CKTnode **CKTnodes;      // Array of circuit nodes
} CKTcircuit;
```

#### Node Structure for Voltage Storage
```c
typedef struct CKTnode {
    int number;              // Node number (matrix index)
    char *name;              // Node name
    double v;                // Node voltage (current solution)
    double n_volt;           // New voltage (for limiting)
    double old_volt;         // Previous voltage
    int type;                // Node type (INTERNAL, EXTERNAL)
} CKTnode;
```

### Core Iteration Loop Variables

The main iteration loop uses these variables to implement the Newton-Raphson algorithm:

```c
// Primary iteration control variables
int iter;                    // Current iteration counter k
int converged;               // Convergence flag (0/1)
int limiting_needed;         // Flag for voltage/current limiting
double delmax;               // Maximum change in solution ||Δx||∞

// Tolerance parameters from circuit structure
double reltol = CKTcurTask->TSKreltol;  // εᵣ
double abstol = CKTcurTask->TSKabstol;  // εₐ
double vntol = CKTcurTask->TSKvntol;    // Voltage tolerance

// Solution vector aliases for clarity
double *newSolution = CKTlhs;      // x⁽ᵏ⁺¹⁾
double *oldSolution = CKToldLhs;   // x⁽ᵏ⁾
double *rhs = CKTrhs;              // F(x⁽ᵏ⁾)
double *oldRhs = CKToldRhs;        // F(x⁽ᵏ⁻¹⁾)

// Sparse matrix solver interface
int *RowMap;                 // Row permutation P from LU factorization
int *ColMap;                 // Column permutation
double *Matrix;              // Jacobian matrix J(x⁽ᵏ⁾) in compressed format
```

### Newton-Raphson Algorithm Implementation

The main iteration loop implements the mathematical update equation `x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ - J(x⁽ᵏ⁾)⁻¹F(x⁽ᵏ⁾)`:

```c
for (iter = 0; iter < CKTmaxIter; iter++) {
    // 1. Save old solution for convergence check: x⁽ᵏ⁾ → x⁽ᵏ⁻¹⁾
    memcpy(oldSolution, newSolution, CKTmaxEqns * sizeof(double));
    memcpy(oldRhs, rhs, CKTmaxEqns * sizeof(double));
    
    // 2. Load circuit equations: Compute F(x⁽ᵏ⁾) and J(x⁽ᵏ⁾)
    // This calls device model functions to load conductances and currents
    CKTterTask(CKTcircuit*);
    
    // 3. Apply device limiting functions to prevent numerical overflow
    if (limiting_needed) {
        applyDeviceLimiting(CKTcircuit*);
    }
    
    // 4. Solve linear system: J(x⁽ᵏ⁾)·Δx = -F(x⁽ᵏ⁾)
    // The RHS vector 'rhs' contains -F(x⁽ᵏ⁾) after CKTterTask
    spSolve(Matrix, newSolution, rhs, RowMap, ColMap);
    
    // 5. Update solution: x⁽ᵏ⁺¹⁾ = x⁽ᵏ⁾ + Δx
    // Note: newSolution initially contains Δx from spSolve
    for (int i = 0; i < CKTmaxEqns; i++) {
        newSolution[i] = oldSolution[i] + newSolution[i];
    }
    
    // 6. Check convergence: ||x⁽ᵏ⁺¹⁾ - x⁽ᵏ⁾||∞ ≤ εᵣ·max(|x⁽ᵏ⁺¹⁾|, |x⁽ᵏ⁾|) + εₐ
    converged = checkConvergence(CKTcircuit*);
    if (converged) {
        break;
    }
    
    // 7. Apply source stepping if not converging (continuation method)
    if (iter > CKTmaxIter/2 && !converged) {
        applySourceStepping(CKTcircuit*);
    }
}
```

### Convergence Check Implementation

The `checkConvergence` function implements the mixed relative-absolute convergence criterion:

```c
int checkConvergence(CKTcircuit *ckt) {
    double max_change = 0.0;      // ||x⁽ᵏ⁺¹⁾ - x⁽ᵏ⁾||∞
    double max_voltage = 0.0;     // max(|x⁽ᵏ⁺¹⁾|, |x⁽ᵏ⁾|)
    
    for (int i = 0; i < ckt->CKTmaxEqns; i++) {
        // Compute change and magnitude for each variable
        double change = fabs(ckt->CKTlhs[i] - ckt->CKToldLhs[i]);
        double voltage = MAX(fabs(ckt->CKTlhs[i]), fabs(ckt->CKToldLhs[i]));
        
        // Special check for voltage variables with tighter tolerance
        if (i < ckt->CKTnumVoltages) {
            if (change > ckt->CKTcurTask->TSKvntol * voltage + ckt->CKTcurTask->TSKabstol) {
                return 0;  // Voltage not converged
            }
        }
        
        // Track maximum values for overall convergence check
        if (change > max_change) {
            max_change = change;
        }
        if (voltage > max_voltage) {
            max_voltage = voltage;
        }
    }
    
    // Main convergence criterion: ||Δx||∞ ≤ εᵣ·max(|x|) + εₐ
    if (max_change > ckt->CKTcurTask->TSKreltol * max_voltage + ckt->CKTcurTask->TSKabstol) {
        return 0;
    }
    
    // Additional check on RHS (current) convergence
    // Ensures F(x) is also stable, not just x
    for (int i = 0; i < ckt->CKTmaxEqns; i++) {
        double rhs_change = fabs(ckt->CKTrhs[i] - ckt->CKToldRhs[i]);
        if (rhs_change > ckt->CKTcurTask->TSKabstol * 10) {
            return 0;
        }
    }
    
    return 1;  // All convergence criteria satisfied
}
```

### Device Limiting Functions

These functions implement the mathematical limiting operations to prevent numerical overflow during Newton iterations:

#### PN Junction Limiting
```c
double pnjlim(double vnew, double vold, double vt, double vcrit, 
              double *vpred) {
    double delv = vnew - vold;  // ΔV
    
    if (vold >= vcrit && delv > 0) {
        // Forward bias limiting: prevent exponential overflow
        double arg = 1 + delv/vt;
        if (arg > 0) {
            vnew = vold + vt * log(arg);  // Logarithmic limiting
        } else {
            vnew = vcrit;  // Clamp to critical voltage
        }
    } else if (vold <= -vcrit && delv < 0) {
        // Reverse bias limiting
        double arg = 1 - delv/vt;
        if (arg > 0) {
            vnew = vold - vt * log(arg);
        } else {
            vnew = -vcrit;
        }
    }
    
    *vpred = vnew;  // Return limited voltage prediction
    return vnew;
}
```

#### FET Limiting
```c
double fetlim(double vds, double vgs, double vto, 
              double *vds_pred, double *vgs_pred) {
    double vgst = vgs - vto;
    double vdsth = MAX(0, vgst);  // Threshold voltage
    
    // Limit Vds to prevent negative conductance in saturation
    if (vds > 0) {
        *vds_pred = vdsth * (1 - exp(-vds/vdsth));  // Exponential limiting
    } else {
        *vds_pred = -vdsth * (1 - exp(vds/vdsth));
    }
    
    // Limit Vgs using smooth logarithmic function
    if (vgst > 0) {
        *vgs_pred = vto + 2 * vt * log(1 + exp(vgst/(2*vt)));
    } else {
        *vgs_pred = vto - 2 * vt * log(1 + exp(-vgst/(2*vt)));
    }
    
    return *vds_pred;
}
```

### Continuation Methods for Difficult Convergence

#### Source Stepping Algorithm
```c
void applySourceStepping(CKTcircuit *ckt) {
    static double lambda = 1.0;  // Continuation parameter λ ∈ [0,1]
    
    if (ckt->CKTniIter > ckt->CKTmaxIter/2 && !converged) {
        // Reduce continuation parameter: λ ← max(0.1, 0.5λ)
        lambda = MAX(0.1, lambda * 0.5);
        
        // Scale independent sources: I_source ← λ·I_source
        for (GENmodel *model = ckt->CKTmodels[SRC]; model != NULL; 
             model = model->GENnextModel) {
            for (GENinstance *inst = model->GENinstances; inst != NULL;
                 inst = inst->GENnextInstance) {
                if (inst->SRCdcValue != 0) {
                    inst->SRCdcValue *= lambda;
                }
            }
        }
    }
}
```

#### Gmin Stepping Implementation
```c
void applyGminStepping(CKTcircuit *ckt) {
    double gmin_orig = ckt->CKTgminOrig;
    double gmin_current = ckt->CKTgmin;
    
    if (!converged && ckt->CKTniIter > ckt->CKTmaxIter/3) {
        // Increase gmin to improve convergence: gmin ← min(10·gmin, 1e-3)
        gmin_current *= 10.0;
        ckt->CKTgmin = MIN(gmin_current, 1e-3);
        
        // Add gmin conductances to Jacobian diagonal: Jᵢᵢ ← Jᵢᵢ + gmin
        for (int i = 0; i < ckt->CKTnumVoltages; i++) {
            int diag_pos = getDiagonalPosition(i);
            Matrix[diag_pos] += ckt->CKTgmin;
        }
    } else if (converged && ckt->CKTgmin > gmin_orig) {
        // Reduce gmin back to original: gmin ← max(gmin_orig, gmin/100)
        ckt->CKTgmin = MAX(gmin_orig, ckt->CKTgmin / 100.0);
    }
}
```

### Sparse Matrix Solver Interface

The linear system `J·Δx = -F` is solved using sparse LU factorization:

```c
int spSolve(double *A, double *x, double *b, int *RowMap, int *ColMap) {
    // Perform LU factorization with partial pivoting: PA = LU
    int error = spFactor(A, RowMap, ColMap);
    if (error) {
        return error;  // Singular matrix detected
    }
    
    // Forward substitution: Solve Ly = Pb
    spForwardSub(A, x, b, RowMap);
    
    // Backward substitution: Solve Ux = y
    spBackwardSub(A, x, ColMap);
    
    return 0;  // Success
}
```

### Statistics Tracking and Error Recovery

#### Iteration Statistics
```c
// Update statistics after each iteration
ckt->CKTstat->STATiter++;  // Total Newton iterations
ckt->CKTstat->STATtranIter += (ckt->CKTmode == MODETRAN);  // Transient iterations
ckt->CKTstat->STATdcIter += (ckt->CKTmode == MODEDC);      // DC iterations

// Store convergence history for debugging
if (ckt->CKTconvHistSize < MAX_CONV_HIST) {
    ckt->CKTconvHistory[ckt->CKTconvHistSize].iteration = iter;
    ckt->CKTconvHistory[ckt->CKTconvHistSize].max_change = delmax;
    ckt->CKTconvHistory[ckt->CKTconvHistSize].converged = converged;
    ckt->CKTconvHistSize++;
}
```

#### Error Handling and Recovery
```c
if (!converged && iter == CKTmaxIter) {
    // Newton-Raphson failed to converge within max iterations
    
    if (ckt->CKTgmin < GMIN_MAX) {
        // Try gmin stepping: increase minimum conductance
        ckt->CKTgmin *= 10.0;
        ckt->CKTniIter = 0;  // Reset iteration counter
        return NI_GMIN_STEP;  // Signal to retry with new gmin
    } else if (lambda > LAMBDA_MIN) {
        // Try source stepping: reduce source magnitudes
        return NI_SRC_STEP;  // Signal to retry with scaled sources
    } else {
        // All recovery methods exhausted
        return NI_NOCONV;  // Report non-convergence
    }
}
```

### Mapping C Implementation to Mathematical Formulation

The C code directly implements the mathematical equations:

1. **Solution Vector**: `CKTlhs` array represents `x ∈ ℝⁿ`
2. **Circuit Equations**: `CKTrhs` array represents `F(x)`
3. **Jacobian Matrix**: `Matrix` array represents `J(x) = ∂F/∂x`
4. **Newton Update**: `spSolve` computes `Δx = -J⁻¹F`, followed by `x ← x + Δx`
5. **Convergence Check**: Implements `||Δx||∞ ≤ εᵣ·max(|x|) + εₐ`
6. **Continuation Methods**: Source stepping modifies `F(x)`, gmin stepping modifies `J(x)`

The implementation maintains mathematical rigor while addressing practical numerical issues through device limiting, continuation methods, and comprehensive error recovery.