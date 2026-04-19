# Numerical Iteration: AC, DC, and Transient Control

_Generated 2026-04-11 17:15 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/niiter.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/niaciter.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/niditer.c`

# Chapter: Numerical Iteration: AC, DC, and Transient Control

## Introduction

The Newton Iteration subsystem in Ngspice implements the core numerical algorithms for three fundamental circuit analysis types through specialized modules: `niiter.c` for DC/steady-state analysis, `niditer.c` for transient/time-domain analysis, and `niaciter.c` for AC/frequency-domain analysis. These files implement the mathematical formulations specific to each analysis domain while sharing a common infrastructure through the `NIstate` and `CKTcircuit` data structures. The DC iteration solves nonlinear algebraic systems **F(x) = 0** using standard Newton-Raphson methods, transient analysis solves differential-algebraic equations **F(x, ẋ, t) = 0** through numerical integration, and AC analysis solves linear complex systems **[G + jωC]·X(ω) = B(ω)** through direct matrix methods. Each module adapts the core Newton framework to its specific mathematical requirements while maintaining consistent convergence control, error handling, and performance optimization across all analysis types.

## Mathematical Formulation

The Newton Iteration framework in Ngspice implements distinct mathematical formulations for each analysis type: DC (steady-state), transient (time-domain), and AC (frequency-domain). Each formulation derives from the fundamental circuit equations but applies different numerical treatments based on the analysis requirements.

### DC Analysis Formulation

DC analysis solves the nonlinear algebraic system representing the circuit at steady state (all time derivatives zero):

**F_DC(x) = 0**

where for each node *i*:
**F_DCᵢ(x) = Σ I_branch(x) + Σ I_source(x)**

The Newton-Raphson iteration solves:
**J_DC(xᵏ)·δxᵏ = -F_DC(xᵏ)**
**xᵏ⁺¹ = xᵏ + δxᵏ**

where **J_DC = ∂F_DC/∂x** is the DC Jacobian matrix. In implementation:
- **x** ↔ `ckt→CKTrhs[]` (node voltages and branch currents)
- **F_DC(x)** ↔ `ni→NIresiduals[]`
- **J_DC** ↔ `ni→NIjacobian→values[]` (real sparse matrix)

### Transient Analysis Formulation

Transient analysis solves differential-algebraic equations (DAEs) representing circuit dynamics:

**F_TRAN(x, ẋ, t) = 0**

where **ẋ = dx/dt**. Ngspice discretizes time derivatives using numerical integration methods:

#### Backward Euler (first order):
**ẋ ≈ (xₖ - xₖ₋₁)/Δt**

#### Trapezoidal (second order):
**ẋ ≈ 2(xₖ - xₖ₋₁)/Δt - ẋₖ₋₁**

#### Gear method (order p):
**ẋ ≈ (α₀·xₖ + Σ_{i=1}^p αᵢ·xₖ₋ᵢ)/Δt**

The discretized system becomes:
**F_TRAN(xₖ, (α₀·xₖ + Σ αᵢ·xₖ₋ᵢ)/Δt, tₖ) = 0**

The Newton iteration for transient analysis solves:
**[∂F/∂x + (α₀/Δt)·∂F/∂ẋ]·δxₖ = -F_TRAN(xₖ, ẋₖ, tₖ)**

Key implementation mappings:
- **xₖ** ↔ `ckt→CKTrhs[]` (current solution)
- **xₖ₋₁, xₖ₋₂, ...** ↔ `ckt→CKTrhsOld[]`, `ni→NIrhsOld[]`, etc. (history)
- **Δt** ↔ `ckt→CKTdelta`
- Integration coefficients **αᵢ** computed based on `ckt→CKTintegMethod` and `ckt→CKTorder`

### AC Analysis Formulation

AC analysis linearizes the circuit around a DC operating point and solves in the frequency domain. The system becomes linear complex-valued:

**[G + jωC]·X(ω) = B(ω)**

where:
- **G** = conductance matrix (∂I/∂V at DC bias)
- **C** = capacitance/inductance matrix (∂Q/∂V, ∂Φ/∂I)
- **ω** = angular frequency = 2πf
- **X(ω)** = complex node voltages
- **B(ω)** = complex source vector

For each frequency point ω, the system is solved directly (no Newton iteration needed for linear AC):
**X(ω) = [G + jωC]⁻¹·B(ω)**

Implementation storage uses separate real and imaginary parts:
- **Re{X}** ↔ `ckt→CKTrhs[]`
- **Im{X}** ↔ `ckt→CKTirhs[]`
- **G** ↔ `ni→NIjacobian→values[]` (real part matrix)
- **ωC** ↔ `ni→NIjacobian→imagValues[]` (imaginary part matrix)
- **ω** ↔ `ni→NIomega`

### Unified Formulation with Analysis-Specific Terms

All analysis types share the core Newton framework but with different residual functions:

**F(x) = F_static(x) + F_dynamic(x, ẋ) + F_source(x, t)**

where:
- **F_static**: Device I-V characteristics (all analyses)
- **F_dynamic**: C·dV/dt + L·dI/dt terms (transient only, zero for DC/AC)
- **F_source**: Time/frequency-dependent sources (analysis-dependent)

The Jacobian generalizes to:
**J = ∂F_static/∂x + ∂F_dynamic/∂x + (α₀/Δt)·∂F_dynamic/∂ẋ**

### Device Model Linearization

For each device, the load function computes:
- **DC**: I_device(V) and ∂I/∂V
- **Transient**: I_device(V) + C·dV/dt and ∂I/∂V + (α₀/Δt)·C
- **AC**: (G_device + jωC_device)·V and source contributions

Capacitor example:
- **DC**: I = 0, ∂I/∂V = 0
- **Transient**: I = C·(Vₖ - Vₖ₋₁)/Δt, ∂I/∂V = C/Δt
- **AC**: I = jωC·V, ∂I/∂V = jωC

## Convergence Analysis

### DC Convergence Criteria

DC Newton iteration convergence is determined by multiple simultaneous criteria:

#### 1. Absolute Residual Convergence
**‖F_DC(xᵏ)‖∞ < ε_abs**
where ε_abs = `ni→NIabstol` (default 1e-12). Implementation:
```c
max_residual = 0.0;
for (i = 0; i < ni→NInumNodes; i++) {
    residual = fabs(ni→NIresiduals[i]);
    if (residual > max_residual) max_residual = residual;
}
if (max_residual < ni→NIabstol) converged = 1;
```

#### 2. Relative Step Convergence
**‖δxᵏ‖ / max(‖xᵏ‖, 1.0) < ε_rel**
where ε_rel = `ni→NIreltol` (default 1e-3). This prevents false convergence when x is near zero.

#### 3. Voltage-Specific Convergence
**|Vᵢᵏ⁺¹ - Vᵢᵏ| < ε_volt** for all voltage nodes i
where ε_volt = `ni→NIvoltTol` (default 1e-6). Provides tighter control on primary circuit variables.

#### 4. Charge Conservation (Capacitors)
**|Q(xₖ₊₁) - Q(xₖ)| / max(|Q(xₖ)|, 1.0) < ε_charge**
Ensures charge conservation in nonlinear capacitors.

### Transient Convergence Analysis

Transient analysis adds time integration-specific convergence considerations:

#### 1. Newton Convergence within Time Step
Each time step requires Newton convergence with the same criteria as DC, but applied to the discretized system **F_TRAN(x, ẋ, t) = 0**.

#### 2. Local Truncation Error (LTE) Control
The time step Δt is controlled by LTE estimation:
**LTE ≈ C·(Δt)^{p+1}·x^{(p+1)}**
where p = integration method order.

Time step acceptance criterion:
**LTE < ε_rel·max(|x|, |ẋ·Δt|) + ε_abs**

Implementation logic:
```c
error_estimate = NIcomputeLTE(ni, ckt);
if (error_estimate < ckt→CKTrtol) {
    ckt→CKTdelta = MIN(ckt→CKTdelta * 1.5, ckt→CKTmaxStep);
    return TIME_STEP_ACCEPTED;
} else {
    ckt→CKTdelta = MAX(ckt→CKTdelta * 0.5, ckt→CKTminStep);
    return TIME_STEP_REJECTED;
}
```

#### 3. Time Step Rejection Conditions
A time step is rejected if:
1. Newton fails to converge within `ni→NImaxIter` iterations
2. LTE exceeds tolerance `ckt→CKTrtol`
3. Step size Δt < `ckt→CKTminStep` (numerical precision limit)
4. Oscillation detected in solution

#### 4. Convergence Rate in Transient Analysis
The Newton convergence rate in transient analysis is typically faster than DC because:
- The solution from previous time step provides excellent initial guess
- Smaller Δt reduces nonlinearity in dynamic terms
- The Jacobian **∂F/∂x + (α₀/Δt)·∂F/∂ẋ** is better conditioned due to the (α₀/Δt) term

### AC Convergence Considerations

AC analysis involves no Newton iteration (linear system) but has its own convergence-related issues:

#### 1. Matrix Conditioning at High Frequency
The AC matrix **G + jωC** becomes increasingly ill-conditioned as ω → ∞:
**cond(G + jωC) ≈ ω·‖C‖/‖G‖** for large ω

This can cause numerical accuracy issues at very high frequencies.

#### 2. Frequency-Dependent Convergence of Iterative Solvers
While Ngspice typically uses direct LU decomposition, iterative solvers would show convergence rates dependent on:
- Frequency ω
- Matrix conditioning
- Preconditioner effectiveness

#### 3. Inter-Frequency Extrapolation
For frequency sweeps, solution at frequency fᵢ provides initial guess for fᵢ₊₁:
**X₀(fᵢ₊₁) = X(fᵢ)** for closely spaced frequencies

### Cross-Analysis Convergence Interactions

#### 1. DC Operating Point for AC/Transient
AC and transient analyses require a converged DC operating point as starting condition. DC convergence failures propagate to other analyses.

#### 2. Transient Initialization from DC
Transient analysis initializes using DC solution:
**x(t=0) = x_DC**
This ensures consistent starting conditions.

#### 3. AC Linearization around DC Point
AC analysis linearizes around DC operating point:
**G = ∂I/∂V|_DC**, **C = ∂Q/∂V|_DC**
DC convergence accuracy directly affects AC results.

### Advanced Convergence Techniques

#### 1. Damped Newton (Step Limiting)
When convergence is difficult, apply damping:
**xₖ₊₁ = xₖ + α·δxₖ**, where α ∈ (0,1]

Implementation:
```c
if (step_norm > ni→NIstepMax) {
    scale_factor = ni→NIstepMax / step_norm;
    for (i = 0; i < ni→NInumNodes; i++) {
        ni→NIdelta[i] *= scale_factor;
    }
    ni→NIstepMax *= 0.5;  /* Reduce for next iteration */
}
```

#### 2. Source Stepping
For strongly nonlinear circuits, gradually increase sources:
Solve **F(x, λ·sources) = 0** for λ: 0 → 1

#### 3. Gmin Stepping
Add small conductance to diagonal to improve conditioning:
**J ← J + ε·I** where ε = `ckt→CKTgmin` (typically 1e-12)

#### 4. Continuation Methods
For parameter sweeps, use solution from previous parameter value as initial guess.

### Convergence Failure Analysis

#### 1. Non-Convergence Detection
Failure occurs when:
- Iterations ≥ `ni→NImaxIter` (default 100) without convergence
- Step size ‖δx‖ < machine epsilon
- Residual norm increases significantly

#### 2. Failure Recovery Strategies
Hierarchical recovery attempts:
1. Reduce Newton step: `ni→NIstepMax *= 0.5`
2. Switch to damped Newton: `ni→NItype = NI_TYPE_DAMPED`
3. Apply source stepping: `ckt→CKTsrcStepFactor *= 0.5`
4. For transient: reduce time step `ckt→CKTdelta *= 0.25`

#### 3. Oscillation Detection
Detect when sign(δx) alternates for several iterations:
**sign(δxᵏ) = -sign(δxᵏ⁻¹)** for multiple consecutive k

Response: aggressively reduce damping factor α.

### Convergence Rate Analysis by Analysis Type

#### 1. DC Analysis Convergence Rate
- Initial iterations: linear convergence (far from solution)
- Near solution: quadratic convergence ‖xₖ₊₁ - x*‖ ≤ C·‖xₖ - x*‖²
- Typical iterations: 3-10 for well-behaved circuits

#### 2. Transient Analysis Convergence Rate
- Faster than DC due to good initial guess from previous time step
- Typically 1-3 Newton iterations per accepted time step
- Convergence deteriorates if Δt too large (increased nonlinearity)

#### 3. AC Analysis "Convergence"
- Direct solve: O(1) "iterations" (LU decomposition + solve)
- Computational cost: O(nnz^1.5) for factorization, O(nnz) per frequency point

### Numerical Stability Considerations

#### 1. Time Integration Stability
- Backward Euler: L-stable, unconditionally stable
- Trapezoidal: A-stable, but can exhibit numerical oscillation
- Gear methods: stiffly stable, good for stiff systems

#### 2. Matrix Conditioning
DC/transient Jacobian conditioning affected by:
- Large ratio of device parameters (e.g., R_max/R_min)
- Floating nodes (singular matrix)
- Ill-conditioned device models

AC matrix conditioning degrades as ω → ∞:
**cond(G + jωC) ∝ ω**

#### 3. Machine Precision Effects
Double precision (ε ≈ 2.2e-16) limits:
- Minimum resolvable voltage: ~1e-8 V for 10V scale
- Maximum condition number: ~1e8 before precision loss
- Minimum time step: ~1e-15 s (practical limit)

### Practical Convergence Heuristics

#### 1. Adaptive Tolerance Scaling
For circuits with widely varying signal levels:
**ε_effective = ε_abs + ε_rel·|signal_level|**

#### 2. Device-Specific Convergence Aids
- Diodes/BJTs: use exponential linearization
- MOSFETs: smooth transition between regions
- Switches: continuous model approximations

#### 3. Analysis-Specific Parameter Tuning
- DC: may need tighter tolerances for accurate AC linearization
- Transient: balance between Newton iterations and time step control
- AC: frequency-dependent preconditioning for iterative solves

The convergence analysis demonstrates that Ngspice implements a sophisticated, multi-level convergence control system that adapts to the specific requirements of each analysis type while maintaining numerical robustness across a wide range of circuit topologies and operating conditions.

## C Implementation

### Core Data Structures for Multi-Analysis Support

#### NIstate Structure with Analysis-Specific Fields

The `NIstate` structure extends to support all analysis types through type-specific fields:

```c
typedef struct NIstate {
    /* Analysis Type Control */
    int    NItype;          /* NI_TYPE_DC, NI_TYPE_TRAN, NI_TYPE_AC */
    int    NImaxIter;       /* Maximum iterations: ckt→CKTmaxIter */
    double NIabstol;        /* Absolute tolerance: ckt→CKTabstol */
    double NIreltol;        /* Relative tolerance: ckt→CKTreltol */
    double NIvoltTol;       /* Voltage tolerance: ckt→CKTvoltTol */
    double NIstepMax;       /* Maximum step: ckt→CKTstepMax */
    
    /* Sparse Matrix System */
    SMPmatrix *NIjacobian;  /* Jacobian matrix J = ∂F/∂x */
    double    *NIsolution;  /* Solution vector x */
    double    *NIRHS;       /* Right-hand side F(x) */
    double    *NIoldSolution; /* Previous solution xₖ⁻¹ */
    double    *NIresiduals;  /* Residuals r = F(x) */
    
    /* Iteration State */
    int     NIiter;         /* Current iteration: ckt→CKTiteration */
    int     NIconverged;    /* Convergence flag */
    double  NIdelta;        /* Current step δx */
    double  NIerror;        /* Current error ‖r‖ */
    double  NImaxResidual;  /* Maximum residual ‖r‖∞ */
    
    /* Circuit Binding */
    CKTnode **NInodes;      /* ckt→CKTnodes */
    int      NInumNodes;    /* ckt→CKTmaxEqnNum */
    
    /* AC-specific Fields (only in NIaciter) */
    double  NIomega;        /* Angular frequency ω = 2πf */
    int     NIfreqIndex;    /* Frequency point index */
    double  *NIrhsOld;      /* Previous RHS for AC */
    double  *NIrhsOld2;     /* Two-step old RHS for AC */
} NIstate;
```

#### Circuit State with Analysis-Specific Storage

```c
typedef struct CKTcircuit {
    /* Node System */
    CKTnode  **CKTnodes;     /* Array of circuit nodes */
    int       CKTnumNodes;   /* Total node count */
    int       CKTmaxEqnNum;  /* Maximum equation number */
    
    /* Solution Vectors */
    double   *CKTrhs;        /* Current RHS: F(x) */
    double   *CKTrhsOld;     /* Previous RHS: F(x₋₁) */
    double   *CKTirhs;       /* Imaginary part (AC only) */
    double   *CKTirhsOld;    /* Previous imaginary (AC only) */
    
    /* Integration State */
    double    CKTtime;       /* Current simulation time t */
    double    CKTdelta;      /* Current time step Δt */
    double    CKTextConvergence; /* External convergence criterion */
    
    /* Device Models */
    GENmodel **CKTmodels;    /* Device model array */
    int       CKTnumModels;  /* Model count */
} CKTcircuit;
```

### DC/Generic Iteration Implementation (`niiter.c`)

#### Core Newton-Raphson Loop

The DC iteration implements the standard Newton algorithm for solving **F(x) = 0**:

```c
int NIiterate(NIstate *ni, CKTcircuit *ckt)
{
    int converged = 0;
    int iteration = 0;
    double old_error, new_error;
    
    /* Initial residual computation: r₀ = F(x₀) */
    NIcomputeResidual(ni, ckt);
    old_error = NIcomputeNorm(ni->NIresiduals, ni->NInumNodes);
    
    while (!converged && iteration < ni->NImaxIter) {
        /* 1. Build Jacobian: Jₖ = ∂F/∂x at xₖ */
        NIbuildJacobian(ni, ckt);
        
        /* 2. Solve linear system: Jₖ·δxₖ = -F(xₖ) */
        NIsolveLinearSystem(ni);
        
        /* 3. Compute step δxₖ = -Jₖ⁻¹·F(xₖ) */
        NIcomputeStep(ni);
        
        /* 4. Apply step limiting (damping) if ‖δxₖ‖ > δ_max */
        if (NIcomputeNorm(ni->NIdelta, ni->NInumNodes) > ni->NIstepMax) {
            NIlimitStep(ni);
        }
        
        /* 5. Update solution: xₖ₊₁ = xₖ + δxₖ */
        NIupdateSolution(ni, ckt);
        
        /* 6. Compute new residual: rₖ₊₁ = F(xₖ₊₁) */
        NIcomputeResidual(ni, ckt);
        new_error = NIcomputeNorm(ni->NIresiduals, ni->NInumNodes);
        
        /* 7. Convergence checks */
        converged = NICheckConvergence(ni, old_error, new_error);
        
        /* 8. Store for next iteration */
        old_error = new_error;
        iteration++;
        ni->NIiter = iteration;
    }
    
    ni->NIconverged = converged;
    return converged ? CONVERGED : NOT_CONVERGED;
}
```

#### Convergence Checking Implementation

The convergence test implements the multi-criteria mathematical checks:

```c
int NICheckConvergence(NIstate *ni, double old_error, double new_error)
{
    int converged = 0;
    
    /* Condition 1: Absolute residual norm ‖F(xₖ)‖∞ < ε_abs */
    if (new_error < ni->NIabstol) {
        converged = 1;
    }
    
    /* Condition 2: Relative error reduction */
    double rel_error = fabs(new_error - old_error) / MAX(old_error, 1.0);
    if (rel_error < ni->NIreltol) {
        converged = 1;
    }
    
    /* Condition 3: No progress (stagnation) */
    if (fabs(new_error - old_error) < 1e-15 * MAX(old_error, new_error)) {
        converged = 1;  /* Accept stagnation as convergence */
    }
    
    /* Condition 4: External convergence criterion */
    if (ckt->CKTextConvergence > 0 && 
        new_error < ckt->CKTextConvergence) {
        converged = 1;
    }
    
    return converged;
}
```

#### Step Limiting Algorithm

```c
void NIlimitStep(NIstate *ni)
{
    double step_norm = NIcomputeNorm(ni->NIdelta, ni->NInumNodes);
    double scale_factor;
    
    if (step_norm > ni->NIstepMax) {
        scale_factor = ni->NIstepMax / step_norm;
        
        /* Apply damping: δx ← α·δx where α < 1 */
        for (int i = 0; i < ni->NInumNodes; i++) {
            ni->NIdelta[i] *= scale_factor;
        }
        
        /* Reduce step for next iteration */
        ni->NIstepMax *= 0.5;
    }
}
```

### Transient/Dynamic Iteration Implementation (`niditer.c`)

#### Integration Method Integration

Transient analysis incorporates numerical integration for solving **F(x, ẋ, t) = 0**:

```c
int NIdynamicIterate(NIstate *ni, CKTcircuit *ckt)
{
    /* Store previous time point solution */
    NIcopySolution(ni->NIoldSolution, ckt->CKTrhsOld, ni->NInumNodes);
    
    /* Integration method coefficients for ẋ ≈ (α₀·x + Σ αᵢ·x₋ᵢ)/Δt */
    double *coeff;
    switch (ckt->CKTintegMethod) {
        case TRAPEZOIDAL:
            coeff = NItrapCoeff(ckt->CKTdelta);  /* α₀ = 2/Δt, α₁ = -2/Δt */
            break;
        case GEAR:
            coeff = NIgearCoeff(ckt->CKTorder, ckt->CKTdelta);
            break;
        case BACKWARD_EULER:
            coeff = NIBECoeff(ckt->CKTdelta);    /* α₀ = 1/Δt, α₁ = -1/Δt */
            break;
    }
    
    /* Modified Newton for dynamic systems with J = ∂F/∂x + (α₀/Δt)·∂F/∂ẋ */
    return NImodifiedNewton(ni, ckt, coeff);
}
```

#### Modified Newton Algorithm for Transient Analysis

```c
int NImodifiedNewton(NIstate *ni, CKTcircuit *ckt, double *coeff)
{
    /* α₀ is the first coefficient for current solution */
    double alpha0 = coeff[0];
    double inv_dt = 1.0 / ckt->CKTdelta;
    
    /* Build modified Jacobian: J_mod = ∂F/∂x + (α₀/Δt)·∂F/∂ẋ */
    NIbuildDynamicJacobian(ni, ckt, alpha0 * inv_dt);
    
    /* Build RHS with history terms: F_mod = F(x, (α₀·x + Σ αᵢ·x₋ᵢ)/Δt, t) */
    NIbuildDynamicRHS(ni, ckt, coeff);
    
    /* Solve J_mod·δx = -F_mod */
    return NIsolveAndUpdate(ni, ckt);
}
```

#### Time Step Control Logic

```c
int NIadjustTimeStep(NIstate *ni, CKTcircuit *ckt, int converged)
{
    double error_estimate;
    
    if (converged) {
        /* Compute local truncation error (LTE) ≈ C·(Δt)^{p+1}·x^{(p+1)} */
        error_estimate = NIcomputeLTE(ni, ckt);
        
        if (error_estimate < ckt->CKTrtol) {
            /* Accept time step, possibly increase Δt */
            ckt->CKTdelta = MIN(ckt->CKTdelta * 1.5, ckt->CKTmaxStep);
            return TIME_STEP_ACCEPTED;
        } else {
            /* Reject, reduce Δt and retry */
            ckt->CKTdelta = MAX(ckt->CKTdelta * 0.5, ckt->CKTminStep);
            return TIME_STEP_REJECTED;
        }
    } else {
        /* Newton failed to converge, reduce Δt */
        ckt->CKTdelta = MAX(ckt->CKTdelta * 0.25, ckt->CKTminStep);
        return TIME_STEP_REJECTED;
    }
}
```

#### Time Step Rejection Conditions

```c
int NIShouldRejectTimeStep(NIstate *ni, CKTcircuit *ckt)
{
    /* Condition 1: Newton failed to converge */
    if (!ni->NIconverged) {
        return REJECT_NEWTON_FAILURE;
    }
    
    /* Condition 2: Local truncation error too large */
    double lte = NIcomputeLTE(ni, ckt);
    if (lte > ckt->CKTrtol) {
        return REJECT_LTE_EXCEEDED;
    }
    
    /* Condition 3: Step size too small */
    if (ckt->CKTdelta < ckt->CKTminStep) {
        return REJECT_MIN_STEP;
    }
    
    /* Condition 4: Oscillation detection */
    if (NIdetectOscillation(ni, ckt)) {
        return REJECT_OSCILLATION;
    }
    
    return ACCEPT_TIME_STEP;
}
```

### AC Iteration Implementation (`niaciter.c`)

#### Complex Number Handling for Frequency Domain

AC analysis solves the linear complex system **[G + jωC]·X(ω) = B(ω)**:

```c
int NIacIterate(NIstate *ni, CKTcircuit *ckt, double frequency)
{
    /* Set angular frequency ω = 2πf */
    ni->NIomega = 2.0 * M_PI * frequency;
    
    /* AC uses complex matrices: A = G + jωC */
    NIbuildACMatrix(ni, ckt);
    
    /* Solve complex linear system (no Newton iteration needed) */
    return NIsolveComplexSystem(ni, ckt);
}
```

#### Complex Matrix Structure and Storage

```c
/* Real and imaginary parts stored separately */
typedef struct SMPcomplexMatrix {
    SMPmatrix *realPart;    /* G matrix */
    SMPmatrix *imagPart;    /* ωC matrix */
    int isFactored;         /* LU factorization flag */
} SMPcomplexMatrix;

/* In NIbuildACMatrix: */
int NIbuildACMatrix(NIstate *ni, CKTcircuit *ckt)
{
    SMPmatrix *G = ni->NIjacobian;      /* Real part: conductance */
    SMPmatrix *wC = ni->NIjacobian_imag; /* Imag part: ω×capacitance */
    
    /* Build G from device conductances at DC bias */
    NIbuildConductanceMatrix(ni, ckt, G);
    
    /* Build ωC from device capacitances */
    NIbuildCapacitanceMatrix(ni, ckt, wC, ni->NIomega);
    
    /* Combine into complex matrix structure */
    return SMPassembleComplex(G, wC);
}
```

#### Frequency Sweep Algorithm

```c
int NIacSweep(NIstate *ni, CKTcircuit *ckt, double *frequencies, int numFreq)
{
    for (int i = 0; i < numFreq; i++) {
        ni->NIfreqIndex = i;
        
        /* Build matrix at current frequency: A(ω) = G + jωC */
        NIbuildACMatrixAtFreq(ni, ckt, frequencies[i]);
        
        /* Factor matrix (LU decomposition) - reuse if structure unchanged */
        if (i == 0 || matrixStructureChanged) {
            SMPfactorComplex(ni->NIjacobian);
        }
        
        /* Solve for each source vector */
        for (int src = 0; src < numSources; src++) {
            NIsetACSource(ni, ckt, src);
            NIsolveComplexSystem(ni, ckt);
            NIstoreACSolutions(ni, ckt, i, src);
        }
    }
    
    return OK;
}
```

#### Complex System Solver

```c
int NIsolveComplexSystem(NIstate *ni, CKTcircuit *ckt)
{
    /* Solve [G + jωC]·X = B where X = Re{X} + jIm{X} */
    
    /* Forward substitution for complex LU */
    SMPforwardSubComplex(ni->NIjacobian, ckt->CKTrhs, ckt->CKTirhs);
    
    /* Backward substitution for complex LU */
    SMPbackwardSubComplex(ni->NIjacobian, ckt->CKTrhs, ckt->CKTirhs);
    
    /* Solution now in ckt->CKTrhs (real) and ckt->CKTirhs (imag) */
    return OK;
}
```

### Non-Convergence Handling Implementation

#### Hierarchical Recovery Strategies

```c
int NIhandleNonConvergence(NIstate *ni, CKTcircuit *ckt)
{
    /* Strategy 1: Reduce step and retry */
    if (ni->NIstepMax > ckt->CKTminStep) {
        ni->NIstepMax *= 0.5;
        return RETRY_WITH_SMALLER_STEP;
    }
    
    /* Strategy 2: Switch to damped Newton */
    if (ni->NItype == NI_TYPE_STANDARD) {
        ni->NItype = NI_TYPE_DAMPED;
        return RETRY_WITH_DAMPING;
    }
    
    /* Strategy 3: Use source stepping */
    if (ckt->CKTsrcStepFactor > 0) {
        ckt->CKTsrcStepFactor *= 0.5;
        return RETRY_WITH_SOURCE_STEPPING;
    }
    
    /* Final failure */
    return CONVERGENCE_FAILURE;
}
```

### Matrix Reuse Strategies for Performance

#### Jacobian Reuse Checking

```c
/* Check if Jacobian structure unchanged */
int NIcanReuseJacobian(NIstate *ni, CKTcircuit *ckt)
{
    /* DC/Transient: Reuse if no topology change */
    if (!ckt->CKTtopologyChanged && 
        ni->NIjacobian->isFactored) {
        return 1;
    }
    
    /* AC: Reuse factorization across frequencies */
    if (ni->NItype == NI_TYPE_AC &&
        !ckt->CKTtopologyChanged) {
        return 1;
    }
    
    return 0;
}
```

#### Analysis-Specific Matrix Building

```c
int NIbuildJacobian(NIstate *ni, CKTcircuit *ckt)
{
    switch (ni->NItype) {
        case NI_TYPE_DC:
            /* Build J = ∂F/∂x for DC */
            return NIbuildDCJacobian(ni, ckt);
            
        case NI_TYPE_TRAN:
            /* Build J = ∂F/∂x + (α₀/Δt)·∂F/∂ẋ for transient */
            return NIbuildTransientJacobian(ni, ckt);
            
        case NI_TYPE_AC:
            /* Build A = G + jωC for AC */
            return NIbuildACMatrix(ni, ckt);
            
        default:
            return E_BADPARM;
    }
}
```

### Device Model Interface for Multi-Analysis

#### Device Load Function Dispatch

```c
/* Device load function prototype */
int DEVload(GENinstance *inst, CKTcircuit *ckt, SMPmatrix *matrix, double *rhs)
{
    switch (ckt->CKTmode) {
        case MODE_DC:
            /* DC: compute I(V) and ∂I/∂V */
            return DEVdcLoad(inst, ckt, matrix, rhs);
            
        case MODE_TRAN:
            /* Transient: compute I(V) + C·dV/dt and derivatives */
            return DEVtranLoad(inst, ckt, matrix, rhs);
            
        case MODE_AC:
            /* AC: compute (G + jωC)·V and source contributions */
            return DEVacLoad(inst, ckt, matrix, rhs);
    }
}
```

#### Capacitor Implementation Example

```c
int CAPload(GENinstance *inst, CKTcircuit *ckt, SMPmatrix *matrix, double *rhs)
{
    CAPinstance *cap = (CAPinstance *)inst;
    double conductance;
    
    switch (ckt->CKTmode) {
        case MODE_DC:
            /* DC: capacitor is open circuit */
            /* I = 0, ∂I/∂V = 0 */
            return OK;
            
        case MODE_TRAN:
            /* Transient: companion model I = G_eq·V + I_eq */
            conductance = cap->CAPcapacitance / ckt->CKTdelta;
            SMPaddElement(matrix, cap->posNode, cap->posNode, conductance);
            SMPaddElement(matrix, cap->negNode, cap->negNode, conductance);
            SMPaddElement(matrix, cap->posNode, cap->negNode, -conductance);
            SMPaddElement(matrix, cap->negNode, cap->posNode, -conductance);
            
            /* I_eq = -G_eq·V_old */
            double Ieq = conductance * (cap->voltage - cap->voltageOld);
            rhs[cap->posNode] -= Ieq;
            rhs[cap->negNode] += Ieq;
            break;
            
        case MODE_AC:
            /* AC: I = jωC·V */
            double wC = ckt->CKTomega * cap->CAPcapacitance;
            /* Add to imaginary matrix part */
            SMPaddElement(matrix->imagPart, cap->posNode, cap->posNode, wC);
            SMPaddElement(matrix->imagPart, cap->negNode, cap->negNode, wC);
            SMPaddElement(matrix->imagPart, cap->posNode, cap->negNode, -wC);
            SMPaddElement(matrix->imagPart, cap->negNode, cap->posNode, -wC);
            break;
    }
    
    return OK;
}
```

### Analysis Control and Dispatch

#### Main Analysis Dispatcher

```c
int NIperformAnalysis(NIstate *ni, CKTcircuit *ckt, int analysisType)
{
    ni->NItype = analysisType;
    
    switch (analysisType) {
        case ANALYSIS_DC:
            /* DC operating point */
            return NIdcAnalysis(ni, ckt);
            
        case ANALYSIS_TRAN:
            /* Transient time-domain */
            return NItranAnalysis(ni, ckt);
            
        case ANALYSIS_AC:
            /* AC frequency-domain */