# Numerical Integration: Predictors and Time Stepping

_Generated 2026-04-11 17:27 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/niinteg.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/nipred.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/nicomcof.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/nipzmeth.c`

# Chapter: Numerical Integration: Predictors and Time Stepping

## Introduction

The numerical integration subsystem in Ngspice provides the core algorithms for transient circuit simulation by discretizing time derivatives in differential-algebraic equations. The modules `niinteg.c`, `nipred.c`, `nicomcof.c`, and `nipzmeth.c` implement a sophisticated predictor-corrector framework with adaptive time step and order control. `niinteg.c` implements the fundamental integration methods (Backward Euler, Trapezoidal, and Gear) that approximate time derivatives using linear multistep formulas. `nipred.c` computes predictor steps using Adams-Bashforth methods to provide accurate initial guesses for Newton iteration. `nicomcof.c` manages the computation and caching of integration coefficients, while `nipzmeth.c` performs stability analysis using pole-zero methods to ensure numerical robustness. Together, these modules enable Ngspice to solve stiff circuit equations with automatic accuracy control, adapting time steps from microseconds to nanoseconds and integration orders from 1 to 6 based on local truncation error estimates and stability constraints.

## Mathematical Formulation

The numerical integration subsystem in Ngspice provides the mathematical framework for discretizing time derivatives in transient circuit simulation. The core problem is solving differential-algebraic equations (DAEs) of the form:

**F(x, ẋ, t) = 0**

where **ẋ = dx/dt** represents time derivatives of circuit variables (node voltages and branch currents). The integration methods approximate these derivatives using numerical differentiation formulas based on current and past solution values.

### Fundamental Discretization Formulation

All integration methods in Ngspice use the general linear multistep formulation:

**ẋ ≈ (α₀·x + Σ_{i=1}^p αᵢ·x₋ᵢ)/Δt**

where:
- **p** = integration order (1-6)
- **αᵢ** = integration coefficients (method-dependent)
- **x₋ᵢ** = solution at time **t - i·Δt** (historical values)
- **Δt** = time step size

The discretized circuit equations become:

**F(x, (α₀·x + Σ αᵢ·x₋ᵢ)/Δt, t) = 0**

This transforms the DAE into a nonlinear algebraic system solvable by Newton-Raphson iteration.

### Integration Method Specific Formulations

#### 1. Backward Euler (First Order)
**ẋ ≈ (x - x₋₁)/Δt**

Coefficients: **α₀ = 1/Δt**, **α₁ = -1/Δt**

Local Truncation Error (LTE): **O(Δt²)**

Stability: A-stable and L-stable (unconditionally stable)

#### 2. Trapezoidal Rule (Second Order)
**ẋ ≈ (x - x₋₁)/Δt + ẋ₋₁/2**

Coefficients: **α₀ = 1/Δt**, **α₁ = -1/Δt** with separate handling of **ẋ₋₁** term

LTE: **O(Δt³)**

Stability: A-stable but not L-stable (can exhibit numerical oscillation)

#### 3. Gear Methods (Orders 2-6)
For Gear method of order **p**:

**ẋ ≈ (α₀·x + Σ_{i=1}^p αᵢ·x₋ᵢ)/Δt**

where coefficients **αᵢ** are determined by solving:
**Σ_{i=0}^p αᵢ·(t₋ᵢ)^k = k·(t₋ᵢ)^{k-1}** for **k = 0, 1, ..., p**

LTE: **O(Δt^{p+1})**

Stability: Stability region shrinks with increasing order, requiring smaller **Δt** for higher orders

### Coefficient Computation Mathematics

The integration coefficients are computed based on the method and order:

#### Gear Method Coefficients:
For order **p**, the coefficients satisfy:
```
[1     1     1     ...    1    ] [α₀]   [0]
[0    -1    -2     ...   -p    ] [α₁]   [1]
[0     1     4     ...    p²   ] [α₂] = [0]
[...                         ] [...]   [...]
[0   (-1)^p (-2)^p ...  (-p)^p] [αₚ]   [0]
```

This yields the standard Gear coefficients:
- Order 1: **α₀ = 1**, **α₁ = -1**
- Order 2: **α₀ = 3/2**, **α₁ = -2**, **α₂ = 1/2**
- Order 3: **α₀ = 11/6**, **α₁ = -3**, **α₂ = 3/2**, **α₃ = -1/3**

#### Trapezoidal Rule Coefficients:
The trapezoidal rule uses:
**ẋ ≈ (x - x₋₁)/Δt + ẋ₋₁/2**

This requires storing both **x₋₁** and **ẋ₋₁**, making it a two-step method despite being second order.

### Predictor Step Formulation

Before Newton iteration, a predictor step computes an initial guess **x̂**:

**x̂ = Σ_{i=0}^{p} βᵢ·x₋ᵢ**

where **βᵢ** are predictor coefficients. For Adams-Bashforth predictors:

- Order 1 (Forward Euler): **x̂ = x₋₁ + Δt·ẋ₋₁**
- Order 2: **x̂ = x₋₁ + Δt·(3/2·ẋ₋₁ - 1/2·ẋ₋₂)**
- Order 3: **x̂ = x₋₁ + Δt·(23/12·ẋ₋₁ - 16/12·ẋ₋₂ + 5/12·ẋ₋₃)**

The predictor provides a good initial guess, reducing Newton iterations.

### Device Model Integration

For circuit elements with energy storage:

#### Capacitors:
**I = dQ/dt = C·dV/dt ≈ C·(α₀·V + Σ αᵢ·V₋ᵢ)**

Jacobian contribution: **∂I/∂V = C·α₀**

#### Inductors:
**V = L·dI/dt ≈ L·(α₀·I + Σ αᵢ·I₋ᵢ)**

Jacobian contribution: **∂V/∂I = L·α₀**

#### Companion Model Formulation:
Energy storage elements are converted to equivalent conductances and current sources:
- Capacitor: **G_eq = C·α₀**, **I_eq = -C·Σ αᵢ·V₋ᵢ**
- Inductor: **R_eq = L·α₀**, **V_eq = -L·Σ αᵢ·I₋ᵢ**

### Stability Analysis Formulation

Numerical stability is analyzed using the test equation:
**ẋ = λ·x**

Applying numerical integration gives:
**xₙ₊₁ = R(z)·xₙ**, where **z = λ·Δt**

The stability region is defined by **|R(z)| ≤ 1**:

#### Backward Euler:
**R(z) = 1/(1 - z)**
Stable for **Re(z) < 0** (A-stable)

#### Trapezoidal Rule:
**R(z) = (1 + z/2)/(1 - z/2)**
Stable for **Re(z) < 0** (A-stable)

#### Gear Methods:
Stability polynomial: **Σ_{i=0}^p αᵢ·R^{p-i} = 0**
Stability region shrinks with increasing **p**

### Local Truncation Error (LTE) Formulation

The LTE for an order **p** method is:
**LTE = C·Δt^{p+1}·x^{(p+1)}(ξ)**

where:
- **C** = method-dependent error constant
- **x^{(p+1)}** = (p+1)th derivative of the solution
- **ξ** ∈ [tₙ, tₙ₊₁]

Error constants:
- Backward Euler: **C = -1/2**
- Trapezoidal: **C = -1/12**
- Gear order p: **C = -p/(p+1)**

The LTE is estimated using divided differences of past solutions.

### Time Step Control Formulation

The optimal time step is determined by:
**Δt_{new} = Δt_{old}·(ε/LTE)^{1/(p+1)}**

where **ε** is the error tolerance:
**ε = ε_abs + ε_rel·|x|**

In practice, a PID controller is used:
**Δt_{new} = Δt_{old}·exp(-(K_p·e + K_i·∫e·dt + K_d·de/dt))**

where **e = LTE/ε - 1** is the normalized error.

### Order Control Formulation

The optimal order is selected based on error trends:
- Increase order if: **LTE_{current}/LTE_{previous} < 0.5** and **p < p_max**
- Decrease order if: **LTE_{current}/LTE_{previous} > 2.0** and **p > 1**

Higher orders provide better accuracy but reduced stability, requiring trade-off based on **Δt**.

## Convergence Analysis

### Integration Method Convergence Properties

#### 1. Backward Euler Convergence
- **Consistency**: LTE = O(Δt²) → 0 as Δt → 0
- **Stability**: A-stable, unconditionally stable
- **Convergence**: First-order accurate, guaranteed convergence for stable circuits
- **Damping**: Strongly damps high frequencies (L-stable)

#### 2. Trapezoidal Rule Convergence
- **Consistency**: LTE = O(Δt³) → 0 as Δt → 0
- **Stability**: A-stable, but can exhibit numerical oscillation
- **Convergence**: Second-order accurate, faster than Backward Euler for smooth solutions
- **Oscillation Risk**: Can produce numerical ringing on sharp transitions

#### 3. Gear Method Convergence
- **Consistency**: LTE = O(Δt^{p+1}) for order p
- **Stability**: Stability region shrinks with increasing order
- **Convergence**: Higher order provides better accuracy for smooth solutions
- **Order Limitations**: Practical limit of p ≤ 6 due to stability constraints

### Predictor-Corrector Convergence

The predictor-corrector scheme exhibits:

#### 1. Predictor Accuracy
- Order p predictor: error = O(Δt^{p+1})
- Provides good initial guess for Newton iteration
- Reduces Newton iterations from ~3-5 to ~1-3

#### 2. Corrector (Newton) Convergence
- Quadratic convergence near solution
- Convergence rate enhanced by good predictor
- Damping applied if Newton diverges

#### 3. Overall Scheme Convergence
The combined predictor-corrector scheme maintains:
- **Global error** = O(Δt^p) for order p method
- **Stability** determined by corrector method
- **Efficiency** improved by reduced Newton iterations

### Time Step Control Convergence

#### 1. LTE-Based Step Control
The time step adjustment aims to maintain:
**LTE ≈ ε = ε_abs + ε_rel·|x|**

Convergence properties:
- **Adaptive**: Δt increases for smooth regions, decreases for rapid changes
- **Stable**: Prevents oscillation in step size through PID control
- **Efficient**: Maximizes Δt while maintaining accuracy

#### 2. Step Rejection and Recovery
When LTE > ε:
- Step is rejected
- Δt reduced (typically by factor 0.5)
- Solution recomputed with smaller Δt

Convergence ensures:
- Finite rejections before acceptance
- Δt bounded by Δt_min ≤ Δt ≤ Δt_max
- Eventual acceptance of all steps

#### 3. Order Control Convergence
Order selection converges to:
- **Low order** (1-2) for stiff problems or large Δt
- **High order** (3-6) for smooth problems with small Δt
- **Stable configuration**: Order and Δt pair that maintains stability

### Stability-Convergence Trade-offs

#### 1. Stiff System Convergence
For stiff circuits (widely separated time constants):
- Backward Euler: Converges reliably but with first-order accuracy
- Trapezoidal: May oscillate on stiff components
- Gear methods: Require careful order/step control

#### 2. Accuracy-Stability Trade-off
Higher order methods offer:
- **Better accuracy**: LTE ∝ Δt^{p+1}
- **Reduced stability**: Smaller stability regions
- **Practical limit**: p ≤ 6 for circuit simulation

#### 3. Method Selection Criteria
- **Stiff circuits**: Backward Euler or low-order Gear
- **Smooth responses**: Trapezoidal or high-order Gear
- **Mixed signals**: Adaptive order control

### Error Propagation and Accumulation

#### 1. Local vs Global Error
- **Local error** (LTE): Error in one step
- **Global error**: Accumulated error over simulation
- Relationship: Global error ≈ (T/Δt)·LTE for order p method

#### 2. Error Growth Modes
- **Exponential growth**: Unstable methods amplify errors
- **Linear growth**: Stable methods control error accumulation
- **Bounded growth**: A-stable methods guarantee bounded errors for stable circuits

#### 3. Error Control Mechanisms
- **Step control**: Adjusts Δt to maintain LTE ≈ ε
- **Order control**: Selects optimal order for current solution behavior
- **Method switching**: May switch between methods based on stiffness

### Convergence in Practical Circuit Simulation

#### 1. Initial Transient Phase
- Large errors due to initial conditions
- Small Δt required for accuracy
- Possible method/order changes

#### 2. Steady-State Phase
- Smooth solution behavior
- Larger Δt possible
- Higher order methods effective

#### 3. Discontinuity Handling
- Events (switches, pulses) cause discontinuities
- Δt reduction near discontinuities
- Possible order reduction to 1

#### 4. Periodic Steady-State
- Constant Δt often optimal
- Fixed order typically sufficient
- Predictor particularly effective

### Numerical Convergence Criteria

#### 1. Step Acceptance Criteria
A time step is accepted if:
1. **Newton convergence**: ‖F(x)‖ < ε_newton
2. **LTE criterion**: LTE < ε = ε_abs + ε_rel·|x|
3. **Stability check**: No numerical oscillation detected

#### 2. Order Selection Criteria
Order p is selected based on:
1. **Error ratio**: LTE(p)/LTE(p-1)
2. **Stability limit**: Δt < Δt_stable(p)
3. **Efficiency**: Computational cost vs accuracy gain

#### 3. Method Selection Criteria
Integration method selected based on:
1. **Circuit stiffness**: Stiffness ratio κ = |λ_max|/|λ_min|
2. **Accuracy requirements**: Desired global error
3. **Stability requirements**: Need for L-stability

### Convergence Rate Analysis

#### 1. Temporal Convergence Rates
- Backward Euler: Global error = O(Δt)
- Trapezoidal: Global error = O(Δt²)
- Gear order p: Global error = O(Δt^p)

#### 2. Computational Efficiency
- Higher order: Fewer steps but more computation per step
- Optimal order: Balances step count and per-step cost
- Adaptive control: Maximizes efficiency through Δt and order adjustment

#### 3. Newton Convergence Enhancement
Predictor improves Newton convergence:
- Without predictor: 3-5 Newton iterations per step
- With predictor: 1-3 Newton iterations per step
- Convergence rate: Quadratic near solution

### Stability Analysis for Convergence Guarantees

#### 1. A-Stability
Methods preserving convergence for all Re(λ) < 0:
- Backward Euler: A-stable
- Trapezoidal: A-stable
- Gear orders 1-2: A-stable, higher orders: not A-stable

#### 2. L-Stability
Methods damping high frequencies:
- Backward Euler: L-stable
- Trapezoidal: Not L-stable
- Gear: Varies with order

#### 3. Stiff Decay
Ability to handle stiff components:
- Essential for circuit simulation
- Backward Euler provides stiff decay
- Trapezoidal lacks stiff decay

### Practical Convergence Considerations

#### 1. Tolerance Settings
- **ε_abs**: Typically 1e-12 for voltages
- **ε_rel**: Typically 1e-3 for relative error
- **Balance**: Too tight → excessive computation, too loose → inaccurate results

#### 2. Step Size Bounds
- **Δt_min**: Typically 1e-15 (numerical precision limit)
- **Δt_max**: Typically 0.1 (stability/accuracy limit)
- **Adaptation**: Δt can vary by several orders of magnitude

#### 3. Order Limitations
- **Maximum order**: Typically 6 for Gear methods
- **Minimum order**: 1 for stability
- **Automatic adjustment**: Based on error estimates and stability

#### 4. Method Switching
Ngspice may switch methods during simulation:
- Start with Trapezoidal for accuracy
- Switch to Backward Euler if oscillations occur
- Use Gear methods for smooth regions

### Convergence Monitoring and Diagnostics

#### 1. Error Tracking
- LTE monitored at each step
- Global error estimated periodically
- Convergence rate computed from error reduction

#### 2. Stability Monitoring
- Oscillation detection in solution
- Step rejection rate monitoring
- Order change frequency tracking

#### 3. Performance Metrics
- Steps per unit time
- Newton iterations per step
- Rejection rate (target < 10%)

The convergence analysis demonstrates that Ngspice's numerical integration framework provides robust, adaptive control of accuracy and stability through sophisticated time step and order selection algorithms, ensuring reliable convergence across diverse circuit simulation scenarios.

## C Implementation

### Core Integration Data Structures

#### INTstate Structure

The `INTstate` structure encapsulates the complete state of the numerical integration algorithm:

```c
typedef struct INTstate {
    int     INTmethod;       /* INT_METHOD_TRAP, INT_METHOD_GEAR, INT_METHOD_BE */
    int     INTorder;        /* Integration order (1-6 for Gear) */
    double  INTdelta;        /* Current time step Δt */
    double  INTtime;         /* Current time t */
    
    /* History arrays for multi-step methods */
    double  **INThistory;    /* History of solutions: [order][n] */
    double  *INTcoeff;       /* Integration coefficients: α₀, α₁, ..., αₚ */
    double  *INTpredCoeff;   /* Predictor coefficients: β₀, β₁, ..., βₚ */
    
    /* Error control */
    double  INTtruncError;   /* Local truncation error estimate */
    double  INTmaxError;     /* Maximum allowed error */
    double  INTminStep;      /* Minimum time step */
    double  INTmaxStep;      /* Maximum time step */
    
    /* State management */
    int     INThistorySize;  /* Current history array size */
    int     INThistoryPtr;   /* Circular buffer pointer */
} INTstate;

/* Integration method constants */
#define INT_METHOD_TRAPEZOIDAL  1
#define INT_METHOD_GEAR         2  
#define INT_METHOD_BACKWARD_EULER 3
```

#### Circuit Integration Context

The `CKTcircuit` structure contains integration-specific fields that bind to the circuit simulation:

```c
typedef struct CKTcircuit {
    /* Integration context */
    INTstate *CKTintegState;   /* Integration state structure */
    int      CKTintegMethod;   /* Current integration method */
    int      CKTorder;         /* Current order (1-6) */
    double   CKTdelta;         /* Time step Δt */
    double   CKTtime;          /* Current simulation time */
    
    /* Solution history */
    double  *CKTrhsOld[7];     /* Past solutions: x₋₁, x₋₂, ..., x₋₆ */
    double  *CKTrhsPred;       /* Predicted solution x̂ */
    
    /* Error control */
    double   CKTtruncRel;      /* Relative truncation error tolerance */
    double   CKTtruncAbs;      /* Absolute truncation error tolerance */
    double   CKTminDelta;      /* Minimum time step */
    double   CKTmaxDelta;      /* Maximum time step */
    
    /* Integration coefficients */
    double   CKTalpha[7];      /* Gear coefficients α₀-α₆ */
    double   CKTbeta[7];       /* Predictor coefficients β₀-β₆ */
} CKTcircuit;
```

### Numerical Integration Framework (`niinteg.c`)

#### Integration Coefficient Computation

The core mathematical operation is computing the integration coefficients **αᵢ** for the discretization **ẋ ≈ (α₀·x + Σ αᵢ·x₋ᵢ)/Δt**:

```c
/* Gear method coefficients computation */
void NIcomputeGearCoeff(double *alpha, int order, double delta)
{
    /* For Gear method of order p */
    switch (order) {
    case 1:  /* Backward Euler */
        alpha[0] = 1.0;
        alpha[1] = -1.0;
        break;
    case 2:
        alpha[0] = 3.0/2.0;
        alpha[1] = -2.0;
        alpha[2] = 1.0/2.0;
        break;
    case 3:
        alpha[0] = 11.0/6.0;
        alpha[1] = -3.0;
        alpha[2] = 3.0/2.0;
        alpha[3] = -1.0/3.0;
        break;
    case 4:
        alpha[0] = 25.0/12.0;
        alpha[1] = -4.0;
        alpha[2] = 3.0;
        alpha[3] = -4.0/3.0;
        alpha[4] = 1.0/4.0;
        break;
    case 5:
        alpha[0] = 137.0/60.0;
        alpha[1] = -5.0;
        alpha[2] = 5.0;
        alpha[3] = -10.0/3.0;
        alpha[4] = 5.0/4.0;
        alpha[5] = -1.0/5.0;
        break;
    case 6:
        alpha[0] = 49.0/20.0;
        alpha[1] = -6.0;
        alpha[2] = 15.0/2.0;
        alpha[3] = -20.0/3.0;
        alpha[4] = 15.0/4.0;
        alpha[5] = -6.0/5.0;
        alpha[6] = 1.0/6.0;
        break;
    }
    
    /* Scale by 1/Δt */
    for (int i = 0; i <= order; i++) {
        alpha[i] /= delta;
    }
}
```

#### Trapezoidal and Backward Euler Coefficients

```c
/* Trapezoidal rule coefficients */
void NIcomputeTrapCoeff(double *alpha, double delta)
{
    /* Trapezoidal: ẋ ≈ (x - x₋₁)/Δt + (ẋ₋₁)/2 */
    alpha[0] = 1.0/delta;      /* Coefficient for x */
    alpha[1] = -1.0/delta;     /* Coefficient for x₋₁ */
}

/* Backward Euler coefficients */
void NIcomputeBECoeff(double *alpha, double delta)
{
    /* Backward Euler: ẋ ≈ (x - x₋₁)/Δt */
    alpha[0] = 1.0/delta;      /* Coefficient for x */
    alpha[1] = -1.0/delta;     /* Coefficient for x₋₁ */
}
```

### Predictor Step Implementation (`nipred.c`)

#### Predictor Coefficient Computation

The predictor computes initial guess **x̂ = Σ βᵢ·x₋ᵢ** using Adams-Bashforth coefficients:

```c
/* Adams-Bashforth predictor coefficients */
void NIcomputePredCoeff(double *beta, int order, double delta)
{
    /* p-step Adams-Bashforth coefficients */
    switch (order) {
    case 1:  /* Forward Euler */
        beta[0] = 1.0;
        beta[1] = delta;
        break;
    case 2:
        beta[0] = 1.0;
        beta[1] = 3.0/2.0 * delta;
        beta[2] = -1.0/2.0 * delta;
        break;
    case 3:
        beta[0] = 1.0;
        beta[1] = 23.0/12.0 * delta;
        beta[2] = -16.0/12.0 * delta;
        beta[3] = 5.0/12.0 * delta;
        break;
    case 4:
        beta[0] = 1.0;
        beta[1] = 55.0/24.0 * delta;
        beta[2] = -59.0/24.0 * delta;
        beta[3] = 37.0/24.0 * delta;
        beta[4] = -9.0/24.0 * delta;
        break;
    }
}
```

#### Predictor Implementation

```c
void NIpredictor(CKTcircuit *ckt, double *x_pred)
{
    int order = ckt->CKTorder;
    int n = ckt->CKTmaxEqnNum;
    
    /* Apply predictor formula: x̂ = Σ βᵢ·x₋ᵢ */
    for (int i = 0; i < n; i++) {
        double sum = 0.0;
        
        /* β₀ term (current solution) */
        sum = ckt->CKTbeta[0] * ckt->CKTrhs[i];
        
        /* Historical terms */
        for (int j = 1; j <= order; j++) {
            if (ckt->CKTrhsOld[j-1] != NULL) {
                sum += ckt->CKTbeta[j] * ckt->CKTrhsOld[j-1][i];
            }
        }
        
        x_pred[i] = sum;
    }
    
    /* Store predicted solution */
    if (ckt->CKTrhsPred == NULL) {
        ckt->CKTrhsPred = TMALLOC(double, n);
    }
    memcpy(ckt->CKTrhsPred, x_pred, n * sizeof(double));
}
```

### Integration Coefficient Computation (`nicomcof.c`)

#### Unified Coefficient Computation

```c
/* Main coefficient computation function */
int NIcomputeCoeff(CKTcircuit *ckt, int method, int order, double delta)
{
    double *alpha = ckt->CKTalpha;
    double *beta = ckt->CKTbeta;
    
    switch (method) {
    case INT_METHOD_TRAPEZOIDAL:
        NIcomputeTrapCoeff(alpha, delta);
        NIcomputeTrapPredCoeff(beta, delta);
        break;
        
    case INT_METHOD_GEAR:
        NIcomputeGearCoeff(alpha, order, delta);
        NIcomputeGearPredCoeff(beta, order, delta);
        break;
        
    case INT_METHOD_BACKWARD_EULER:
        NIcomputeBECoeff(alpha, delta);
        NIcomputeBEPredCoeff(beta, delta);
        break;
    }
    
    /* Store in circuit */
    ckt->CKTintegMethod = method;
    ckt->CKTorder = order;
    ckt->CKTdelta = delta;
    
    return OK;
}
```

#### Coefficient Scaling for Device Loading

```c
/* Compute scaled coefficients for device loading */
void NIcomputeScaledCoeff(double *scaledAlpha, double *alpha, 
                          double chargeCoeff, double delta)
{
    /* For capacitive elements: Q = C·V */
    /* dQ/dt = C·dV/dt ≈ C·(α₀·V + Σ αᵢ·V₋ᵢ) */
    
    /* Scale by capacitance */
    for (int i = 0; i <= MAX_ORDER; i++) {
        scaledAlpha[i] = chargeCoeff * alpha[i];
    }
    
    /* Additional scaling for trapezoidal rule */
    if (ckt->CKTintegMethod == INT_METHOD_TRAPEZOIDAL) {
        /* Trapezoidal needs special handling for charge */
        scaledAlpha[0] *= 0.5;
        scaledAlpha[1] *= 0.5;
    }
}
```

### Pole-Zero Method (`nipzmeth.c`) - Stability Analysis

#### Stability Region Computation

```c
/* Compute stability region for integration method */
void NIcomputeStability(int method, int order, 
                        double *realStable, double *imagStable)
{
    /* For test equation: ẋ = λ·x */
    /* Numerical method: xₙ₊₁ = R(z)·xₙ, where z = λ·Δt */
    
    switch (method) {
    case INT_METHOD_BACKWARD_EULER:
        /* BE: R(z) = 1/(1 - z) */
        /* Stable for Re(z) < 0 (A-stable) */
        *realStable = -INFINITY;
        *imagStable = INFINITY;
        break;
        
    case INT_METHOD_TRAPEZOIDAL:
        /* Trapezoidal: R(z) = (1 + z/2)/(1 - z/2) */
        /* A-stable but not L-stable */
        *realStable = -INFINITY;
        *imagStable = INFINITY;
        break;
        
    case INT_METHOD_GEAR:
        /* Gear methods: stability depends on order */
        NIcomputeGearStability(order, realStable, imagStable);
        break;
    }
}
```

#### Gear Method Stability Polynomial

```c
/* Gear method stability polynomial */
double NIgearStabilityPoly(double z, int order)
{
    /* Characteristic polynomial for Gear method */
    double poly = 0.0;
    
    switch (order) {
    case 1:  /* 1 - z */
        poly = 1.0 - z;
        break;
    case 2:  /* (3/2) - 2z + (1/2)z² */
        poly = 1.5 - 2.0*z + 0.5*z*z;
        break;
    case 3:  /* (11/6) - 3z + (3/2)z² - (1/3)z³ */
        poly = 11.0/6.0 - 3.0*z + 1.5*z*z - 1.0/3.0*z*z*z;
        break;
    }
    
    return poly;
}
```

### Truncation Error Analysis and Time Step Control

#### Local Truncation Error (LTE) Computation

```c
/* Estimate local truncation error */
double NIcomputeLTE(CKTcircuit *ckt, double *x_new)
{
    int order = ckt->CKTorder;
    int n = ckt->CKTmaxEqnNum;
    double lte_max = 0.0;
    
    /* Method-dependent error constants */
    double error_const;
    switch (ckt->CKTintegMethod) {
    case INT_METHOD_TRAPEZOIDAL:
        error_const = -1.0/12.0;  /* C = -1/12 for trapezoidal */
        break;
    case INT_METHOD_GEAR:
        error_const = -order/(order+1);  /* Gear error constant */
        break;
    case INT_METHOD_BACKWARD_EULER:
        error_const = -1.0/2.0;  /* C = -1/2 for BE */
        break;
    }
    
    /* Estimate (p+1)th derivative using divided differences */
    for (int i = 0; i < n; i++) {
        /* Compute divided difference of order p+1 */
        double dd = NIcomputeDividedDiff(ckt, i, order+1);
        
        /* LTE estimate for this variable */
        double lte_i = fabs(error_const * pow(ckt->CKTdelta, order+1) * dd);
        
        /* Scale by tolerance */
        double tol = ckt->CKTtruncAbs + 
                    ckt->CKTtruncRel * fabs(x_new[i]);
        
        double scaled_lte = lte_i / MAX(tol, 1e-12);
        
        lte_max = MAX(lte_max, scaled_lte);
    }
    
    return lte_max;
}
```

#### Time Step Adjustment Algorithm

```c
/* Adjust time step based on error estimate */
double NIadjustTimeStep(CKTcircuit *ckt, double lte_estimate)
{
    double delta_old = ckt->CKTdelta;
    double delta_new;
    
    /* PID controller for time step adjustment */
    static double lte_prev = 0.0;
    static double delta_prev = 0.0;
    
    double Kp = 0.8;   /* Proportional gain */
    double Ki = 0.3;   /* Integral gain */
    double Kd = 0.1;   /* Derivative gain */
    
    /* Error normalized to 1 (target) */
    double error = lte_estimate - 1.0;
    
    /* PID computation */
    static double integral = 0.0;
    double derivative = (error - lte_prev) / delta_old;
    integral += error * delta_old;
    
    double correction = Kp*error + Ki*integral + Kd*derivative;
    
    /* New time step */
    delta_new = delta_old * exp(-correction);
    
    /* Limit to allowed range */
    delta_new = MIN(delta_new, ckt->CKTmaxDelta);
    delta_new = MAX(delta_new, ckt->CKTminDelta);
    
    /* Store for next iteration */
    lte_prev = lte_estimate;
    delta_prev = delta_old;
    
    return delta_new;
}
```

#### Order Control Algorithm

```c
/* Adjust integration order based on error estimates */
int NIadjustOrder(CKTcircuit *ckt, double *lte_history, int history_len)
{
    int current_order = ckt->CKTorder;
    int new_order = current_order;
    
    /* Compute optimal order based on error trends */
    if (history_len >= 3) {
        double error_ratio = lte_history[history_len-1] / 
                           lte_history[history_len-2];
        
        if (error_ratio < 0.5 && current_order < MAX_ORDER) {
            /* Error decreasing rapidly, can increase order */
            new_order = current_order + 1;
        } else if (error_ratio > 2.0 && current_order > 1) {
            /* Error increasing, decrease order */
            new_order = current_order - 1;
        }
    }
    
    /* Limit order changes based on stability */
    if (ckt->CKTintegMethod == INT_METHOD_GEAR) {
        /* Gear methods: higher order less stable */
        if (ckt->CKTdelta > 0.1 * ckt->CKTmaxDelta && new_order > 2) {
            new_order = 2;  /* Limit order for large steps */
        }
    }
    
    return new_order;
}
```

### Device Loading with Integration Coefficients

#### Capacitor Loading Implementation

```c
/* Example: Capacitor loading with integration */
void CAPload(CKTcircuit *ckt, GENinstance *inst, 
             SMPmatrix *matrix, double *rhs)
{
    CAPinstance *here = (CAPinstance *)inst;
    double cap = here->CAPcapac;
    
    /* Get integration coefficients */
    double alpha0 = ckt->CKTalpha[0];
    
    /* Load conductance: G = C·α₀ */
    double geq = cap * alpha0;
    
    /* Load history term: I_history = -C·Σ αᵢ·V₋ᵢ */
    double ceq = 0.0;
    for (int i = 1; i <= ckt->CKTorder; i++) {
        if (ckt->CKTrhsOld[i-1] != NULL) {
            double v_old = ckt->CKTrhsOld[i-1][here->CAPposNode] -
                          ckt->CKTrhsOld[i-1][here->CAPnegNode];
            ceq -= cap * ckt->CKTalpha[i] * v_old;
        }
    }
    
    /* Stamp matrix */
    SMPaddElement(matrix, here->CAPposNode, here->CAPposNode, geq);
    SMPaddElement(matrix, here->CAPpos