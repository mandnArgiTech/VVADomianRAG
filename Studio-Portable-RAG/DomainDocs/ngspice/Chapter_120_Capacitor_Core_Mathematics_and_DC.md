# Capacitor: Device Physics, Temperature, and Transient Load

_Generated 2026-04-12 18:21 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/captemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capload.c`

# **Chapter: Capacitor: Device Physics, Temperature, and Transient Load**

## **Introduction**

This chapter details the implementation of the capacitor device model within the Ngspice circuit simulator, focusing on the integration of device physics, temperature effects, and transient load behavior. The implementation is distributed across several core C source files, each with a distinct role in mapping the mathematical models to SPICE's simulation framework:

*   **`capdefs.h`**: Contains the fundamental data structures `sCAPmodel` and `sCAPinstance`. These structures define the memory layout for all capacitor parameters, runtime state variables, and sparse matrix pointers, serving as the bridge between the SPICE netlist and the numerical simulation engine.
*   **`capparam.c`**: Defines the parameter table `CAPpTable` that maps SPICE netlist keywords (e.g., `c`, `ic`, `poly1`) to internal symbolic constants and storage locations within the instance structure. This file handles the parsing and validation of user-provided parameters.
*   **`captemp.c`**: Implements the `CAPtemp()` function, which applies temperature scaling to the nominal capacitance and other temperature-sensitive parameters using the formula `C(T) = C(T₀) × [1 + TC₁·(T - T₀) + TC₂·(T - T₀)²]`. This ensures model accuracy across operating temperatures.
*   **`capload.c`**: Contains the critical `CAPload()` function, the core of the transient analysis implementation. This function evaluates the voltage-dependent capacitance `C(V)`, computes the corresponding charge `Q(V)` and its derivative `G(V) = dQ/dV`, constructs a linearized companion model based on the selected numerical integration method (Backward Euler, Trapezoidal, Gear), and stamps the resulting conductance and current contributions into the SPICE Modified Nodal Analysis (MNA) matrix.

Together, these files form a cohesive pipeline: definitions establish the data model, parameters are ingested and validated, environmental effects (temperature) are applied, and finally, the device's dynamic `I-V` relationship is integrated into the circuit matrix at each Newton-Raphson iteration. The following sections provide the complete mathematical formulation governing these operations and the corresponding C implementation that brings the mathematics to life within Ngspice.

## **Mathematical Formulation**

The capacitor device model in Ngspice implements both linear and nonlinear capacitance with comprehensive support for temperature effects, numerical integration, and convergence within the SPICE Modified Nodal Analysis (MNA) framework. The mathematical foundation extends from basic charge-voltage relationships to complex voltage-dependent and temperature-scaled models required for accurate circuit simulation.

### **1. Fundamental Charge-Voltage Relationships**

#### **1.1 Basic Capacitor Equation**

The fundamental relationship governing a capacitor in SPICE is:
```
i(t) = dQ/dt = d[C(V)·V]/dt
```
where:
- `i(t)` = instantaneous current through the capacitor (A)
- `Q` = stored charge (C)
- `C(V)` = voltage-dependent capacitance (F)
- `V` = voltage across capacitor terminals (V)

For linear capacitors, this simplifies to:
```
i(t) = C·dV/dt
```

#### **1.2 Charge Integration Formulation**

The stored charge is computed as:
```
Q(V) = ∫ C(V) dV
```

For linear capacitors:
```
Q(V) = C·V
```

For nonlinear capacitors, the integral must be evaluated based on the specific capacitance model.

### **2. Voltage-Dependent Capacitance Models**

#### **2.1 Polynomial Voltage Dependence**

The capacitor supports polynomial expansion for voltage-dependent capacitance:
```
C(V) = C₀ × [1 + VC₁·V + VC₂·V² + VC₃·V³]
```
where:
- `C₀` = nominal capacitance (parameter `c` in SPICE)
- `VC₁` = linear voltage coefficient (parameter `poly1`)
- `VC₂` = quadratic voltage coefficient (parameter `poly2`)
- `VC₃` = cubic voltage coefficient (parameter `poly3`)

The corresponding charge function is:
```
Q(V) = ∫ C(V) dV = C₀ × [V + (VC₁/2)·V² + (VC₂/3)·V³ + (VC₃/4)·V⁴]
```

#### **2.2 Junction Diode Capacitance Model**

For semiconductor junction capacitors (reverse-biased diode model), the capacitance follows:
```
C_j(V) = 
{
    C_j0 / (1 - V/V_j)^M          for V ≤ FC·V_j (reverse bias)
    C_j0 × [1 - FC×(1+M) + M×V/V_j] / (1-FC)^(1+M) for V > FC·V_j (forward bias)
}
```
where:
- `C_j0` = zero-bias capacitance = `CAPcj × area + CAPcjsw × perimeter`
- `V_j` = junction potential (`CAPpb`)
- `M` = grading coefficient (`CAPm`)
- `FC` = forward bias coefficient (`CAPfc`)

This model is critical for simulating pn-junction depletion capacitances in semiconductor devices.

### **3. Temperature Scaling Mathematics**

#### **3.1 Temperature-Dependent Capacitance**

Capacitance varies with temperature according to:
```
C(T) = C(T₀) × [1 + TC₁·(T - T₀) + TC₂·(T - T₀)²]
```
where:
- `T₀` = nominal temperature (default 300.15 K in SPICE)
- `TC₁` = first-order temperature coefficient (`CAPtc1`)
- `TC₂` = second-order temperature coefficient (`CAPtc2`)

#### **3.2 Junction Parameter Temperature Scaling**

For junction capacitors, key parameters scale with temperature:
```
V_j(T) = V_j(T₀) × (T/T₀) - (2kT/q) × ln(T/T₀)
```
where `k` is Boltzmann's constant and `q` is electron charge.

The saturation current scales as:
```
I_s(T) = I_s(T₀) × exp[(E_G/q) × (1/T₀ - 1/T) × (T/T₀)^XTI]
```
where `E_G` is the bandgap energy and `XTI` is the saturation current temperature exponent.

### **4. Numerical Integration for Transient Analysis**

#### **4.1 Discretization of Differential Equation**

The capacitor differential equation is discretized using numerical integration methods. For time step `h` and integration coefficient `α`:
```
Qₙ - Qₙ₋₁ = h·[α·iₙ + (1-α)·iₙ₋₁]
```

The integration coefficient `α` depends on the method:
- **Backward Euler**: α = 1.0
- **Trapezoidal**: α = 0.5
- **Gear-2**: α = 2/3

#### **4.2 Companion Model Formulation**

The discretized equation is linearized to create a companion model suitable for Newton-Raphson iteration:
```
iₙ = G_eq·Vₙ + I_eq
```
where:
```
G_eq = α·h⁻¹·G(Vₙ)
I_eq = α·h⁻¹·[Q(Vₙ) - Vₙ·G(Vₙ)] + (1-α)·iₙ₋₁ - α·h⁻¹·Qₙ₋₁
```
and `G(V) = dQ/dV` is the voltage-dependent conductance.

#### **4.3 Matrix Stamp for MNA**

The companion model stamps into the SPICE MNA matrix as:
```
[Y]·[V] = [I]
```
with contributions:
```
Y_pp += G_eq
Y_nn += G_eq
Y_pn -= G_eq
Y_np -= G_eq
I_p  -= I_eq
I_n  += I_eq
```
where `p` and `n` are positive and negative node indices.

### **5. AC Analysis Formulation**

#### **5.1 Small-Signal Admittance**

For AC analysis at angular frequency `ω = 2πf`, the capacitor admittance is:
```
Y(ω) = jωC(V_dc)
```
where `C(V_dc)` is the capacitance evaluated at the DC operating point voltage.

For voltage-dependent capacitors, the linearized admittance includes both capacitive and conductive components:
```
Y(ω) = G(V_dc) + jωC(V_dc)
```
where `G(V_dc) = dC/dV · dV/dt` evaluated at the DC point.

#### **5.2 Complex Matrix Stamping**

In AC analysis, the matrix becomes complex:
```
[Y(ω)] = [G] + jω[C]
```
The capacitor contributes purely imaginary terms for ideal capacitors, but may contribute real terms for nonlinear capacitors with equivalent series resistance or dielectric loss models.

### **6. Distortion Analysis Mathematics**

#### **6.1 Taylor Series Expansion**

For harmonic distortion analysis, the charge function is expanded as a Taylor series around the DC operating point `V₀`:
```
Q(V) = Q(V₀) + Q'(V₀)·ΔV + (1/2!)·Q''(V₀)·ΔV² + (1/3!)·Q'''(V₀)·ΔV³ + ...
```
where `ΔV = V - V₀`.

#### **6.2 Nonlinearity Coefficients**

For the polynomial capacitance model, the derivatives are:
```
Q'(V)  = C₀·[1 + VC₁·V + VC₂·V² + VC₃·V³]
Q''(V) = C₀·[VC₁ + 2·VC₂·V + 3·VC₃·V²]
Q'''(V) = C₀·[2·VC₂ + 6·VC₃·V]
```

#### **6.3 Harmonic Generation**

For a sinusoidal input `V = V₀ + A·sin(ωt)`, the nonlinearities generate harmonics at multiples of `ω`. The amplitude of the nth harmonic is proportional to the nth derivative of the charge function.

### **7. Sensitivity Analysis Formulation**

#### **7.1 Adjoint Method for Parameter Sensitivity**

The sensitivity of circuit response `R` to capacitor parameter `p` is computed using the adjoint method:
```
∂R/∂p = -λᵀ·(∂Y/∂p)·V
```
where:
- `λ` = adjoint vector (solution of `Yᵀ·λ = ∂R/∂V`)
- `Y` = admittance matrix
- `V` = nodal voltage vector

#### **7.2 Parameter Derivatives**

For capacitance parameter `C`:
```
∂Y/∂C = jω·M
```
where `M` is the topology matrix:
```
M = [ 1  -1 ]
    [ -1  1 ]
```

For voltage coefficient parameters:
```
∂Y/∂VC₁ = jω·C₀·V·M
∂Y/∂VC₂ = jω·C₀·V²·M
∂Y/∂VC₃ = jω·C₀·V³·M
```

### **8. Initial Condition Processing**

#### **8.1 Charge Initialization**

When initial voltage `V_ic` is specified, the initial charge is computed as:
```
Q_ic = ∫ C(V) dV from 0 to V_ic
```

For linear capacitors:
```
Q_ic = C·V_ic
```

For polynomial capacitors:
```
Q_ic = C₀·[V_ic + (VC₁/2)·V_ic² + (VC₂/3)·V_ic³ + (VC₃/4)·V_ic⁴]
```

#### **8.2 State Vector Initialization**

The initial charge is stored in the state vector at indices `CKTstate0` and `CKTstate1` for use in subsequent time steps and LTE calculations.

## **Convergence Analysis**

The capacitor model in Ngspice employs rigorous convergence controls to ensure numerical stability across all analysis types (DC, AC, transient). The convergence mechanisms handle both linear and nonlinear capacitance models within SPICE's Newton-Raphson framework.

### **1. Newton-Raphson Convergence Criteria**

#### **1.1 Voltage Convergence Test**

The primary convergence criterion checks voltage changes between iterations:
```
|V_new - V_old| < ε_v = RELTOL × max(|V_new|, |V_old|) + VNTOL
```
where:
- `RELTOL` = relative tolerance (default 1e-3 in SPICE)
- `VNTOL` = absolute voltage tolerance (default 1e-6 V)

This ensures the solution has stabilized to within acceptable bounds.

#### **1.2 Charge Convergence Test**

For charge-storage elements, charge convergence is also monitored:
```
|Q_new - Q_old| < ε_q = RELTOL × max(|Q_new|, |Q_old|) + CHGTOL
```
where `CHGTOL` = absolute charge tolerance (default 1e-14 C).

#### **1.3 Current Convergence Test**

Current convergence provides additional verification:
```
|i_new - i_old| < ε_i = RELTOL × max(|i_new|, |i_old|) + ABSTOL
```
where `ABSTOL` = absolute current tolerance (default 1e-12 A).

### **2. Local Truncation Error (LTE) Control**

#### **2.1 LTE Formulation for Charge-Based Elements**

The Local Truncation Error estimates the error introduced by the numerical integration method. For charge-based elements:
```
LTE = |Q_actual - Q_predicted|
```
where `Q_predicted` is extrapolated from previous time steps using the integration method's polynomial.

#### **2.2 Prediction Formulas by Integration Method**

**Backward Euler (1st order):**
```
Q_predicted = Q_{n-1}
```

**Trapezoidal/Gear-2 (2nd order):**
```
Q_predicted = 2·Q_{n-1} - Q_{n-2}
```

**Gear-3 (3rd order):**
```
Q_predicted = 3·Q_{n-1} - 3·Q_{n-2} + Q_{n-3}
```

#### **2.3 Normalized LTE and Time-Step Control**

The normalized LTE is computed as:
```
LTE_norm = LTE / CHGTOL_max
```
where `CHGTOL_max = max(RELTOL × max(|Q|), CHGTOL)`.

If `LTE_norm > 1`, the time step is reduced according to:
```
h_new = h_old × (1/LTE_norm)^{1/(k+1)}
```
where `k` is the integration method order.

### **3. Integration Method Stability Analysis**

#### **3.1 Stability Regions**

Different integration methods have different stability properties:

**Backward Euler:**
- Unconditionally stable (A-stable)
- Stability region: entire left half-plane
- Introduces numerical damping (dissipative)

**Trapezoidal:**
- Unconditionally stable (A-stable)
- Stability region: entire left half-plane
- Preserves energy for linear systems (non-dissipative)

**Gear Methods:**
- Gear-2: A-stable
- Gear-3: conditionally stable
- Higher-order Gear methods have shrinking stability regions

#### **3.2 Stiff Decay Property**

Backward Euler exhibits "stiff decay" - it rapidly damps high-frequency components, making it suitable for stiff systems but potentially overdamping fast transients.

#### **3.3 Method Switching Logic**

Ngspice may switch between integration methods based on:
- LTE estimates
- Circuit activity (rapid vs. slow transients)
- Previous convergence history
- User-specified preferences

### **4. Nonlinear Convergence Handling**

#### **4.1 Voltage-Dependent Capacitance Convergence**

For nonlinear capacitors `C(V)`, convergence requires:
```
|C(V_new) - C(V_old)| < ε_c = RELTOL × max(|C(V_new)|, |C(V_old)|)
```

The Newton-Raphson iteration for nonlinear capacitance uses the Jacobian:
```
J = ∂i/∂V = α·h⁻¹·[C(V) + V·(dC/dV)]
```

#### **4.2 Damping for Newton-Raphson**

When convergence is slow, damping is applied:
```
V_{k+1} = V_k + λ·ΔV
```
where `λ` is a damping factor (0 < λ ≤ 1) that reduces when:
- Oscillations are detected in `V_k` sequence
- `|ΔV|` increases between iterations
- Maximum iterations are approached without convergence

#### **4.3 Convergence Acceleration Techniques**

**Predictor-Corrector Methods:**
- Use polynomial extrapolation to predict initial guess
- Apply Newton-Raphson correction
- Particularly effective for smooth transients

**History Weighting:**
- Weight previous solutions based on time-step changes
- More weight given to recent solutions during rapid changes
- Reduced weight during steady-state periods

### **5. AC Analysis Convergence**

#### **5.1 Complex Variable Convergence**

For AC analysis, both real and imaginary parts must converge:
```
|Re(V_new) - Re(V_old)| < ε_v
|Im(V_new) - Im(V_old)| < ε_v
```

#### **5.2 Frequency Sweep Continuation**

During frequency sweeps, the solution at frequency `f_k` is used as initial guess for `f_{k+1}`:
```
V_initial(f_{k+1}) = V_solution(f_k) × (f_{k+1}/f_k)^{phase_estimate}
```

### **6. Distortion Analysis Convergence**

#### **6.1 Harmonic Balance Convergence**

For distortion analysis using harmonic balance, convergence is checked per harmonic:
```
|V^{(m)}_{new} - V^{(m)}_{old}| < ε_hb
```
for `m = 1, 2, 3, ...` (harmonic number).

#### **6.2 Intermodulation Convergence**

For multi-tone analysis, convergence must be achieved for all mixing products:
```
|V^{(mω₁ ± nω₂)}_{new} - V^{(mω₁ ± nω₂)}_{old}| < ε_imd
```
where `m, n` are integers.

### **7. Sensitivity Analysis Convergence**

#### **7.1 Adjoint System Convergence**

The adjoint system `Yᵀ·λ = b` must converge with the same criteria as the forward system:
```
|λ_new - λ_old| < ε_adj = RELTOL × max(|λ_new|, |λ_old|)
```

#### **7.2 Gradient Convergence**

Sensitivity gradients must stabilize:
```
|∇R_new - ∇R_old| < ε_grad = RELTOL × max(|∇R_new|, |∇R_old|)
```

### **8. Temperature Analysis Convergence**

#### **8.1 Self-Consistent Temperature Solution**

When temperature is solved self-consistently with electrical behavior:
```
|T_{new} - T_{old}| < ε_T = 0.1 K (typical)
|I(T_{new}) - I(T_{old})| < ε_I = RELTOL × max(|I|)
```

#### **8.2 Temperature Ramp Convergence**

During temperature sweeps, the solution at `T_k` initializes `T_{k+1}`:
```
V_initial(T_{k+1}) = V_solution(T_k) + (dV/dT)·ΔT
```

### **9. Implementation-Specific Convergence Controls**

#### **9.1 State Vector Management**

The capacitor maintains convergence history in state vectors:
```
CKTstate0[inst->CAPstate] = Q_{n-2}
CKTstate1[inst->CAPstate] = Q_{n-1}
CKTstate[inst->CAPstate] = Q_n
```

Convergence is tracked through these state variables with proper weighting based on time-step changes.

#### **9.2 Matrix Condition Monitoring**

The condition number of the Jacobian matrix is monitored:
```
κ(J) = ||J||·||J⁻¹||
```
If `κ(J) > 10^8`, the system is ill-conditioned and requires:
- Regularization (adding small diagonal terms)
- Method switching (to more stable integration)
- Time-step reduction

#### **9.3 Convergence Failure Recovery**

When convergence fails, Ngspice employs:
1. **Time-step reduction** (by factor of 2-8)
2. **Integration method switching** (to lower order)
3. **Damping factor reduction** (more conservative steps)
4. **Reinitialization** from previous converged point

### **10. Default Tolerance Values**

Ngspice uses these default tolerances for capacitor convergence:

| Parameter | Symbol | Default Value | Purpose |
|-----------|--------|---------------|---------|
| Relative Tolerance | `RELTOL` | 1e-3 | Relative error tolerance |
| Absolute Voltage Tolerance | `VNTOL` | 1e-6 V | Minimum voltage change |
| Absolute Charge Tolerance | `CHGTOL` | 1e-14 C | Minimum charge change |
| Absolute Current Tolerance | `ABSTOL` | 1e-12 A | Minimum current change |
| Truncation Error Tolerance | `TRTOL` | 7.0 | LTE safety factor |
| Minimum Time Step | `TSTEPMIN` | 1e-15 s | Minimum allowed time step |

These mathematical formulations and convergence controls ensure that the capacitor model in Ngspice provides accurate, stable simulations across all operating conditions while maintaining computational efficiency within the SPICE simulation framework.

## **C Implementation**

The Ngspice capacitor device model is implemented across a suite of C source files that map the mathematical formulations for linear/nonlinear capacitance, temperature scaling, and transient integration directly to SPICE's simulation kernel. This section details the specific C structures, functions, and algorithms that realize the device physics within the circuit simulator.

### **1. Core Data Structures and Memory Layout**

The capacitor's state is encapsulated in two primary structures defined in `capdefs.h`, which serve as the bridge between the SPICE netlist parameters and the runtime simulation variables.

#### **1.1 Instance Structure (`sCAPinstance`)**
This structure holds all data unique to a single capacitor instance in the circuit. Its design reflects a direct mapping of the device's electrical and numerical state.

```c
typedef struct sCAPinstance {
    /* Topology and connectivity - Mapped to circuit nodes */
    int CAPposNode;                         /* Positive terminal node index */
    int CAPnegNode;                         /* Negative terminal node index */
    int CAPbranch;                          /* Branch equation index (for current) */
    
    /* Core capacitance parameters - Direct from SPICE netlist */
    double CAPcapac;                        /* Nominal capacitance (F) - Parameter 'c' */
    double CAPinitCond;                     /* Initial voltage condition (V) - Parameter 'ic' */
    
    /* Runtime state variables - Calculated during simulation */
    double CAPc;                            /* Instantaneous capacitance C(V) */
    double CAPq;                            /* Instantaneous charge Q(V) */
    double CAPcapCur;                       /* Capacitor current i(t) */
    double CAPvoltage;                      /* Terminal voltage V(t) */
    double CAPconduct;                      /* Equivalent conductance G_eq */
    double CAPqprime;                       /* Charge at previous time point Q_{n-1} */
    
    /* Parameter flags - Bitfields for memory efficiency */
    unsigned CAPtempGiven    :1;            /* Temperature specification flag */
    unsigned CAPicGiven      :1;            /* Initial condition flag */
    unsigned CAPpolyGiven    :1;            /* Polynomial coefficients present */
    
    /* Voltage-dependent capacitance coefficients */
    double CAPpoly1;                        /* VC₁ coefficient */
    double CAPpoly2;                        /* VC₂ coefficient */
    double CAPpoly3;                        /* VC₃ coefficient */
    
    /* Sparse Matrix Pointers (SMP) - Critical for matrix stamping */
    double *CAPposPosPtr;                   /* G++ matrix element */
    double *CAPnegNegPtr;                   /* G-- matrix element */
    double *CAPposNegPtr;                   /* G+- matrix element */
    double *CAPnegPosPtr;                   /* G-+ matrix element */
    
    /* State management for numerical integration */
    int CAPstate;                           /* State vector index for charge storage */
    struct sCAPinstance *CAPnextInstance;   /* Linked list pointer */
} CAPinstance;
```

**Mathematical Mapping:** The `CAPc` and `CAPq` members directly store the computed values of `C(V)` and `Q(V)` from the voltage-dependent capacitance equations. The `CAPconduct` member holds the equivalent conductance `G_eq` for the companion model used in Newton-Raphson iteration.

#### **1.2 Model Structure (`sCAPmodel`)**
This structure contains parameters shared across multiple capacitor instances of the same model type, particularly for semiconductor junction capacitors.

```c
typedef struct sCAPmodel {
    /* Semiconductor junction capacitance parameters */
    double CAPcj;                           /* Zero-bias junction capacitance (F/m²) */
    double CAPcjsw;                         /* Zero-bias sidewall capacitance (F/m) */
    
    /* Temperature coefficients */
    double CAPtc1;                          /* First-order temp coefficient TC₁ (1/°C) */
    double CAPtc2;                          /* Second-order temp coefficient TC₂ (1/°C²) */
    double CAPtnom;                         /* Nominal temperature T₀ (K) */
    
    /* Parameter presence flags */
    unsigned CAPtc1Given    :1;
    unsigned CAPtc2Given    :1;
    unsigned CAPtnomGiven   :1;
    
    /* Instance chain and model linking */
    CAPinstance *CAPinstances;              /* Linked list of all instances */
    struct sCAPmodel *CAPnextModel;         /* Next model in circuit */
} CAPmodel;
```

### **2. SPICE Device API Binding**

The capacitor device registers with the Ngspice kernel through the `SPICEdev` structure in `capinit.c`. This structure defines the complete interface between the device model and the simulator.

```c
SPICEdev CAPinfo = {
    .DEVpublic = {
        .name = "capacitor",
        .description = "Linear and nonlinear capacitor",
        .terms = 2,  /* Two-terminal device */
        .numNames = 2,
        .termNames = {"p", "n"},
    },
    /* Critical function pointers mapping math to simulation phases */
    .DEVparam = CAPparam,        /* Parameter parsing: maps netlist to C structs */
    .DEVload = CAPload,          /* Transient load: implements i = dQ/dt */
    .DEVsetup = CAPsetup,        /* Matrix setup: allocates SMP pointers */
    .DEVtemperature = CAPtemp,   /* Temperature scaling: applies C(T) formula */
    .DEVtrunc = CAPtrunc,        /* LTE calculation: estimates truncation error */
    .DEVacLoad = CAPacLoad,      /* AC analysis: computes Y(ω) = jωC */
    .DEVconvTest = CAPconvTest,  /* Convergence testing: checks |ΔV|, |ΔQ| */
    .DEVdestroy = CAPdestroy,    /* Memory cleanup: frees all allocated memory */
    .DEVinstSize = sizeof(CAPinstance),
    .DEVmodSize = sizeof(CAPmodel)
};
```

**Simulation Integration:** Each function pointer corresponds to a specific phase of SPICE simulation. For example, `DEVload` is called during the Newton-Raphson iteration to stamp the capacitor's contribution into the circuit matrix.

### **3. Parameter Parsing and Validation**

The `CAPpTable` in `capparam.c` defines how SPICE netlist parameters map to the C structure members and their mathematical meaning.

```c
static IFparm CAPpTable[] = {
    /* Basic parameters with direct mathematical meaning */
    IOP("c",       CAP_CAP,      IF_REAL,    "Capacitance C₀"),
    IOP("ic",      CAP_IC,       IF_REAL,    "Initial voltage V(0)"),
    IOP("tc1",     CAP_TC1,      IF_REAL,    "First order temp coeff TC₁"),
    IOP("tc2",     CAP_TC2,      IF_REAL,    "Second order temp coeff TC₂"),
    
    /* Polynomial coefficients for C(V) = C₀[1 + VC₁·V + VC₂·V² + VC₃·V³] */
    IOP("poly1",   CAP_POLY1,    IF_REAL,    "Linear voltage coefficient VC₁"),
    IOP("poly2",   CAP_POLY2,    IF_REAL,    "Quadratic voltage coefficient VC₂"),
    IOP("poly3",   CAP_POLY3,    IF_REAL,    "Cubic voltage coefficient VC₃"),
    
    /* Output variables computed during simulation */
    OP("q",        CAP_CHARGE,   IF_REAL,    "Current charge Q(V)"),
    OP("i",        CAP_CURRENT,  IF_REAL,    "Current i(t) = dQ/dt"),
    OP("v",        CAP_VOLTAGE,  IF_REAL,    "Voltage V(t)"),
};
```

**Mathematical Correspondence:** Each `IOP` macro links a SPICE parameter name (e.g., "c") to a symbolic constant (`CAP_CAP`) that indexes into the parameter table. During netlist parsing, the value is stored in `inst->CAPcapac`, directly representing the mathematical parameter `C₀`.

### **4. Temperature Scaling Implementation**

The `CAPtemp()` function in `captemp.c` implements the temperature scaling mathematics:

```c
void CAPtemp(CAPinstance *inst, CAPmodel *model, CKTcircuit *ckt)
{
    double T, Tnom, dT, factor;
    
    /* Determine operating temperature: instance-specific or circuit default */
    T = inst->CAPtempGiven ? inst->CAPtemp : ckt->CKTtemp;
    Tnom = model->CAPtnomGiven ? model->CAPtnom : ckt->CKTnomTemp;
    
    /* Calculate temperature difference ΔT = T - T₀ */
    dT = T - Tnom;
    
    /* Apply temperature scaling formula: C(T) = C(T₀) × [1 + TC₁·ΔT + TC₂·ΔT²] */
    if (model->CAPtc1Given || model->CAPtc2Given) {
        factor = 1.0;  /* Start with unity factor */
        
        /* Add first-order term: TC₁·ΔT */
        if (model->CAPtc1Given)
            factor += model->CAPtc1 * dT;
        
        /* Add second-order term: TC₂·ΔT² */
        if (model->CAPtc2Given)
            factor += model->CAPtc2 * dT * dT;
        
        /* Scale the nominal capacitance */
        inst->CAPcapac *= factor;
    }
}
```

**Algorithm Details:** The function implements the exact mathematical formula `C(T) = C(T₀) × [1 + TC₁·(T - T₀) + TC₂·(T - T₀)²]`. The conditional checks (`CAPtc1Given`, `CAPtc2Given`) ensure terms are only added when the corresponding parameters are specified in the netlist, maintaining backward compatibility.

### **5. Transient Load and Matrix Stamping**

The core of the capacitor implementation is the `CAPload()` function in `capload.c`, which maps the differential equation `i(t) = dQ/dt` to a linearized companion model for Newton-Raphson iteration.

#### **5.1 Voltage-Dependent Capacitance Calculation**

```c
/* Compute instantaneous capacitance C(V) and its derivative G(V) = dQ/dV */
if (inst->CAPpolyGiven) {
    /* Evaluate polynomial: C(V) = C₀[1 + VC₁·V + VC₂·V² + VC₃·V³] */
    inst->CAPc = inst->CAPcapac * 
        (1.0 + inst->CAPpoly1*v + inst->CAPpoly2*v*v + inst->CAPpoly3*v*v*v);
    
    /* Compute conductance: G(V) = C₀[1 + VC₁·V + VC₂·V² + VC₃·V³] + V·C₀[VC₁ + 2VC₂·V + 3VC₃·V²] */
    g = inst->CAPc + v * inst->CAPcapac * 
        (inst->CAPpoly1 + 2*inst->CAPpoly2*v + 3*inst->CAPpoly3*v*v);
} else {
    /* Linear case: C(V) = C₀, G(V) = C₀ */
    inst->CAPc = inst->CAPcapac;
    g = inst->CAPc;
}
```

**Mathematical Accuracy:** This code directly computes the analytical derivative `G(V) = dQ/dV = C(V) + V·dC/dV`, which is required for the Newton-Raphson Jacobian. For the polynomial model, `dC/dV = C₀[VC₁ + 2VC₂·V + 3VC₃·V²]`.

#### **5.2 Charge Computation**

```c
/* Compute charge Q(V) = ∫ C(V) dV */
if (inst->CAPpolyGiven) {
    /* Q(V) = C₀[V + (VC₁/2)·V² + (VC₂/3)·V³ + (VC₃/4)·V⁴] */
    q = inst->CAPcapac * 
        (v + 0.5*inst->CAPpoly1*v*v + 
         1.0/3.0*inst->CAPpoly2*v*v*v + 
         0.25*inst->CAPpoly3*v*v*v*v);
} else {
    /* Linear case: Q(V) = C₀·V */
    q = inst->CAPc * v;
}
```

**Integration Mapping:** The polynomial coefficients are hardcoded (0.5, 1.0/3.0, 0.25) corresponding to the analytical integral `∫(1 + VC₁·V + VC₂·V² + VC₃·V³) dV = V + (VC₁/2)V² + (VC₂/3)V³ + (VC₃/4)V⁴`.

#### **5.3 Numerical Integration Method Selection**

```c
switch (ckt->CKTintegrateMethod) {
    case TRAPEZOIDAL:  /* α = 0.5 */
        h = ckt->CKTdelta;
        g = 2.0 * inst->CAPc / h;          /* G_eq = 2C/h */
        ieq = (2.0 * q / h) + inst->CAPcapCur; /* I_eq = 2Q/h + i_{n-1} */
        break;
        
    case GEAR:  /* Gear-2: α = 2/3 */
        h = ckt->CKTdelta;
        g = 1.5 * inst->CAPc / h;          /* G_eq = 1.5C/h */
        ieq = (1.5 * q / h) + 0.5 * inst->CAPcapCur; /* I_eq = 1.5Q/h + 0.5i_{n-1} */
        break;
        
    default: /* Backward Euler: α = 1 */
        h = ckt->CKTdelta;
        g = inst->CAPc / h;                /* G_eq = C/h */
        ieq = q / h;                       /* I_eq = Q/h */
        break;
}
```

**Companion Model Parameters:** This implements the discretized companion model `iₙ = G_eq·Vₙ + I_eq` where:
- `G_eq = α·C/h` (equivalent conductance)
- `I_eq = α·Q/h + (1-α)·i_{n-1} - α·Q_{n-1}/h` (equivalent current source)

#### **5.4 Sparse Matrix Stamping**

```c
/* Stamp conductance matrix G */
*(inst->CAPposPosPtr) += g;   /* G_{pp} += G_eq */
*(inst->CAPnegNegPtr) += g;   /* G_{nn} += G_eq */
*(inst->CAPposNegPtr) -= g;   /* G_{pn} -= G_eq */
*(inst->CAPnegPosPtr) -= g;   /* G_{np} -= G_eq */

/* Stamp right-hand side vector */
ckt->CKTrhs[inst->CAPposNode] -= ieq;  /* b_p -= I_eq */
ckt->CKTrhs[inst->CAPnegNode] += ieq;  /* b_n += I_eq */
```

**Matrix Pattern:** The capacitor stamps a symmetric 2×2 conductance matrix with pattern `[[G_eq, -G_eq], [-G_eq, G_eq]]`, representing the mathematical relationship `i = G_eq·(V₊ - V₋) + I_eq`.

### **6. AC Analysis Implementation**

The `CAPacLoad()` function in `capacld.c` implements the small-signal admittance `Y(ω) = jωC` for frequency domain analysis.

```c
int CAPacLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    CAPmodel *model = (CAPmodel*)inModel;
    CAPinstance *inst;
    double v, c, omega;
    
    omega = ckt->CKTomega;  /* Angular frequency ω = 2πf */
    
    for (inst = model->CAPinstances; inst != NULL; inst = inst->CAPnextInstance) {
        /* Get DC operating point