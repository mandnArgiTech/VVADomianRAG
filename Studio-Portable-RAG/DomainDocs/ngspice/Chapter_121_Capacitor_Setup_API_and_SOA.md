# Capacitor: Matrix Setup, API Binding, and Safe Operating Area

_Generated 2026-04-12 18:35 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capgetic.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/cap.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capdest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capsoachk.c`

# **Chapter: Capacitor: Matrix Setup, API Binding, and Safe Operating Area**

## **Introduction**

This chapter details the Ngspice implementation of the capacitor device model, focusing on its integration into the simulator's core infrastructure. The implementation spans eleven C source files that collectively manage the device's lifecycle within the SPICE simulation framework:

*   **`capsetup.c`**: Implements the `CAPsetup()` function, which performs the critical initialization of matrix connectivity. It allocates sparse matrix pointers (`SMPmakeElt`) for the capacitor's 2×2 conductance stamp pattern `[[G, -G], [-G, G]]` and assigns indices in the simulator's state vector for storing the capacitor's voltage and charge history, essential for numerical integration and charge conservation.
*   **`capmask.c` & `capmpar.c`**: Define the device's parameter system. `capmpar.c` contains the `CAPmPTable` array, which maps SPICE netlist keywords (e.g., `c`, `tc1`, `ic`) to internal parameter indices and descriptions. `capmask.c` provides the corresponding symbolic constants (`CAP_C`, `CAP_TC1`, etc.) used throughout the code to identify and access these parameters.
*   **`capask.c` & `capgetic.c`**: Handle user interaction and initial conditions. `capask.c` implements the `CAPask()` function, allowing the simulation kernel to query the value of instance parameters (like instantaneous voltage or charge) during and after analysis. `capgetic.c` contains `CAPgetic()`, which processes the `IC` parameter to set initial voltages and compute corresponding initial charges for the state vector.
*   **`capinit.c`**: Defines the `SPICEdev CAPinfo` structure, the central API binding that registers the capacitor device with Ngspice. This structure contains function pointers (e.g., `DEVload`, `DEVsetup`, `DEVsoaCheck`) that the simulator calls during different phases of analysis, creating the bridge between the capacitor's mathematical model and the simulation kernel.
*   **`cap.c`**: Likely contains core model and instance constructor functions (e.g., `CAPnewModel`, `CAPnewInstance`), responsible for allocating and initializing the `sCAPmodel` and `sCAPinstance` structures with default values.
*   **`capdel.c`, `capmdel.c`, `capdest.c`**: Manage the memory lifecycle. `capdel.c` (`CAPdelete`) deletes a single instance, `capmdel.c` (`CAPmDelete`) deletes a model and all its instances, and `capdest.c` (`CAPdestroy`) provides the top-level cleanup function called when a circuit is destroyed, ensuring no memory leaks.
*   **`capsoachk.c`**: Implements the `CAPsoaCheck()` function, a critical reliability feature. It validates the capacitor's instantaneous operating point against user-defined Safe Operating Area (SOA) limits, such as maximum voltage rating (`BV`) and power dissipation, logging warnings if violations occur.

Together, these files orchestrate the capacitor's existence within a simulation: from parsing its netlist description and binding to the SPICE API, to setting up its matrix contributions and state management, performing temperature scaling and nonlinear calculations during analysis, checking for physical limits, and finally ensuring proper cleanup. The following sections present the complete mathematical formulation governing these operations and the corresponding C implementation that brings the mathematics to life within Ngspice.

## **Mathematical Formulation**

The capacitor model in Ngspice integrates into the SPICE simulation framework through a rigorous mathematical formulation that governs its matrix contributions, parameter scaling, and physical operating limits. This formulation directly maps to the sparse matrix solver, device API, and reliability checking algorithms.

### **1. Matrix Setup and Sparse Matrix Allocation**

The capacitor's integration into SPICE's Modified Nodal Analysis (MNA) requires defining its contribution to the circuit's conductance matrix `G` and state vector.

#### **1.1 Two-Terminal Conductance Matrix Pattern**

For a linear capacitor connected between nodes `p` (positive) and `n` (negative), the small-signal conductance contribution follows a fixed symmetric pattern:

```
G_cap = [  G  -G ]
        [ -G   G ]
```

where `G` is the equivalent conductance derived from the numerical integration method. This pattern is hardcoded in the matrix pointer allocation during setup.

#### **1.2 State Vector Allocation for Charge Conservation**

The capacitor requires state variables to store charge history for numerical integration and Local Truncation Error (LTE) calculation. The state vector allocation follows:

```
STATE = [ ..., V_cap, Q_cap, ... ]
```

where:
- `V_cap` = capacitor voltage (state index `CAPstate`)
- `Q_cap` = stored charge (state index `CAPqstate`)

The number of state entries per capacitor instance is fixed at 2, regardless of capacitance value or nonlinearity.

#### **1.3 Parameter Scaling and Multiplier Application**

Before matrix setup, raw parameters from the SPICE netlist are scaled according to device multipliers and scale factors:

```
C_effective = C_nominal × M × SCALE
```

where:
- `C_nominal` = capacitance value from `c` or `cap` parameter
- `M` = parallel multiplier (`m` parameter)
- `SCALE` = global scale factor (`scale` parameter)

This scaling occurs in `CAPsetup()` before any matrix allocation.

### **2. Temperature Scaling Mathematics**

The capacitance temperature dependence follows a quadratic polynomial relative to the nominal temperature `T_nom` (typically 300.15K):

#### **2.1 Temperature Coefficient Formula**

```
C(T) = C(T_nom) × [1 + TC₁ × (T - T_nom) + TC₂ × (T - T_nom)²]
```

where:
- `TC₁` = first-order temperature coefficient (`tc1` parameter) in 1/°C
- `TC₂` = second-order temperature coefficient (`tc2` parameter) in 1/°C²
- `T` = operating temperature in Kelvin
- `T_nom` = nominal temperature (300.15K default)

#### **2.2 Instance vs. Circuit Temperature**

The implementation supports three temperature specifications:
1. **Instance temperature**: `temp` parameter overrides circuit temperature
2. **Delta temperature**: `dtemp` adds to circuit temperature
3. **Circuit temperature**: Defaults to `CKTtemp` (typically 300.15K)

The temperature difference calculation is:
```
ΔT = (temp ? T_instance : CKTtemp + dtemp) - 300.15
```

#### **2.3 Temperature Scaling Implementation**

The scaling factor is computed as:
```
factor = 1.0
if (TC₁ given) factor += TC₁ × ΔT
if (TC₂ given) factor += TC₂ × ΔT²
C_scaled = C_nominal × factor
```

This ensures backward compatibility when temperature coefficients are not specified.

### **3. Voltage-Dependent Capacitance Models**

#### **3.1 Polynomial Model (Direct Coefficients)**

```
C(V) = C₀ + C₁·V + C₂·V²
```

where:
- `C₀` = voltage-independent capacitance (`c0` parameter)
- `C₁` = linear voltage coefficient (`c1` parameter) in F/V
- `C₂` = quadratic voltage coefficient (`c2` parameter) in F/V²

The corresponding charge function is:
```
Q(V) = ∫ C(V) dV = C₀·V + (C₁/2)·V² + (C₂/3)·V³
```

#### **3.2 Polynomial Model (Relative Coefficients)**

```
C(V) = C_nominal × (1 + VC₁·V + VC₂·V²)
```

where:
- `VC₁` = linear relative coefficient (`vc1` parameter) in 1/V
- `VC₂` = quadratic relative coefficient (`vc2` parameter) in 1/V²

The charge function for this model is:
```
Q(V) = C_nominal × [V + (VC₁/2)·V² + (VC₂/3)·V³]
```

#### **3.3 Small-Signal Conductance Derivative**

For Newton-Raphson iteration, the derivative `dQ/dV` is required:
```
dQ/dV = C(V) + V × dC/dV
```

For the direct polynomial model:
```
dC/dV = C₁ + 2·C₂·V
dQ/dV = C₀ + 2·C₁·V + 3·C₂·V²
```

For the relative polynomial model:
```
dC/dV = C_nominal × (VC₁ + 2·VC₂·V)
dQ/dV = C_nominal × (1 + 2·VC₁·V + 3·VC₂·V²)
```

### **4. Companion Model for Transient Analysis**

#### **4.1 Discretized Charge Equation**

The capacitor differential equation `i(t) = dQ/dt` is discretized using numerical integration:

```
Q^{n+1} = Q^n + Δt × [α·i^{n+1} + (1-α)·i^n]
```

where `α` is the integration coefficient:
- Backward Euler: `α = 1`
- Trapezoidal: `α = 0.5`
- Gear-2: `α = 2/3`

#### **4.2 Linearized Companion Model**

The discretized equation is linearized to form a companion model suitable for the MNA matrix:

```
i^{n+1} = G_eq × V^{n+1} + I_eq
```

where the equivalent conductance and current source are:

**Trapezoidal Rule:**
```
G_eq = 2C/Δt
I_eq = -G_eq × V^n - i^n
```

**Backward Euler:**
```
G_eq = C/Δt
I_eq = -G_eq × V^n
```

**Gear-2:**
```
G_eq = 1.5C/Δt
I_eq = -G_eq × V^n - (C/Δt) × (2V^n - 0.5 × Q^{n-1}/C)
```

#### **4.3 Matrix Stamp for Companion Model**

The companion model stamps into the MNA matrix as:

```
[  G_eq  -G_eq ] [ V_p ]   [ -I_eq ]
[ -G_eq   G_eq ] [ V_n ] = [  I_eq ]
```

This corresponds to the sparse matrix entries:
- `G_pp += G_eq`
- `G_nn += G_eq`
- `G_pn -= G_eq`
- `G_np -= G_eq`
- `RHS_p -= I_eq`
- `RHS_n += I_eq`

### **5. AC Analysis Formulation**

#### **5.1 Small-Signal Admittance**

For AC analysis at angular frequency `ω = 2πf`, the capacitor contributes purely imaginary admittance:

```
Y(ω) = jωC
```

where `C` is the small-signal capacitance evaluated at the DC operating point.

#### **5.2 Small-Signal Capacitance for Nonlinear Models**

For voltage-dependent capacitors, the small-signal capacitance is the derivative `dQ/dV` at the DC bias point:

**Direct polynomial model:**
```
C_small-signal = dQ/dV = C₀ + 2C₁·V_dc + 3C₂·V_dc²
```

**Relative polynomial model:**
```
C_small-signal = C_nominal × (1 + 2VC₁·V_dc + 3VC₂·V_dc²)
```

#### **5.3 Complex Matrix Stamp**

The AC matrix stamp uses complex numbers:

```
Y_matrix = [  jωC  -jωC ]
           [ -jωC   jωC ]
```

The real part is zero for ideal capacitors; any series resistance would contribute to the real part.

### **6. Local Truncation Error (LTE) Estimation**

#### **6.1 LTE Formula for Trapezoidal Integration**

For the trapezoidal rule, the LTE is estimated from the third derivative of charge:

```
LTE = |(Δt²/12) × d³q/dt³|
```

#### **6.2 LTE Formula for Gear Integration**

For Gear-2 (second order):

```
LTE = |(Δt³/24) × d³q/dt³|
```

#### **6.3 Derivative Calculations**

The charge derivatives are computed from capacitance derivatives:

```
q = Q(V)
dq/dt = C(V) × dV/dt
d²q/dt² = dC/dV × (dV/dt)² + C(V) × d²V/dt²
d³q/dt³ = d²C/dV² × (dV/dt)³ + 3 × dC/dV × dV/dt × d²V/dt² + C(V) × d³V/dt³
```

For linear capacitance (`C` constant):
```
d²C/dV² = 0
dC/dV = 0
d³q/dt³ = C × d³V/dt³
```

#### **6.4 Time-Step Control**

The LTE is compared against a tolerance:
```
tol = RELTOL × V_TOL + ABSTOL
```

If `LTE > tol`, the time step is reduced:
```
Δt_new = 0.9 × Δt_old × √(tol / LTE)
```

### **7. Safe Operating Area (SOA) Constraints**

#### **7.1 Voltage Rating Check**

The primary SOA check verifies the absolute voltage against the maximum rating:

```
|V_cap| ≤ V_max
```

where `V_max` is the breakdown voltage parameter (if specified).

#### **7.2 Power Dissipation Check**

For capacitors with series resistance, power dissipation is checked:

```
P_diss = I² × R_series ≤ P_max
```

where:
- `I` = capacitor current
- `R_series` = equivalent series resistance (ESR)
- `P_max` = maximum power rating

#### **7.3 SOA Violation Handling**

When SOA violations are detected:
1. Warning messages are logged with device name and violation details
2. The `CKTsoaFlag` is set to `TRUE`
3. Simulation may continue or pause based on user settings

### **8. Noise Modeling**

#### **8.1 Thermal Noise from Series Resistance**

If the capacitor model includes series resistance `R_s`, it generates thermal noise:

```
S_I(f) = 4kT / R_s
```

where:
- `k` = Boltzmann's constant (1.380649×10⁻²³ J/K)
- `T` = temperature in Kelvin
- `R_s` = series resistance in ohms

#### **8.2 Noise-Free Capacitor**

Without series resistance, the capacitor is considered noiseless in the model:
```
S_I(f) = 0
```

### **9. Convergence Testing Criteria**

#### **9.1 Voltage Convergence Test**

The Newton-Raphson iteration checks voltage changes:

```
|V_new - V_old| ≤ ε_V = RELTOL × max(|V_new|, |V_old|) + VNTOL
```

where:
- `RELTOL` = relative tolerance (default 1e-3)
- `VNTOL` = absolute voltage tolerance (default 1e-6 V)

#### **9.2 Charge Convergence Test**

For charge conservation, charge changes are also checked:

```
|Q_new - Q_old| ≤ ε_Q = RELTOL × max(|Q_new|, |Q_old|) + 1e-12
```

#### **9.3 Convergence Failure Handling**

If either test fails:
1. `CKTnoncon` counter is incremented
2. Newton-Raphson continues with adjusted damping
3. Time step may be reduced if convergence fails repeatedly

### **10. Initial Condition Processing**

#### **10.1 Initial Voltage Specification**

When `ic` parameter is given:
```
V(0) = V_ic
Q(0) = ∫ C(V) dV evaluated at V_ic
```

#### **10.2 State Vector Initialization**

The initial conditions populate the state vector:
```
CKTrhsOld[CAPstate] = V_ic
CKTrhsOld[CAPqstate] = Q(0)
```

#### **10.3 DC Initialization**

During DC analysis, the capacitor is treated as an open circuit (G = 0) if no initial condition is specified.

## **Convergence Analysis**

The capacitor model's integration into SPICE's Newton-Raphson solver requires careful convergence analysis to ensure numerical stability across all operating conditions, from DC initialization through transient simulation with adaptive time stepping.

### **1. Newton-Raphson Convergence for Nonlinear Capacitance**

#### **1.1 Jacobian Matrix Contribution**

For voltage-dependent capacitance `C(V)`, the capacitor contributes to the circuit Jacobian matrix `J = ∂I/∂V`:

```
J_cap = [  G_nl  -G_nl ]
        [ -G_nl   G_nl ]
```

where `G_nl = α/Δt × dQ/dV` is the nonlinear equivalent conductance, with `dQ/dV = C(V) + V × dC/dV`.

#### **1.2 Convergence Radius for Polynomial Models**

The polynomial capacitance model `C(V) = C₀ + C₁·V + C₂·V²` has a finite convergence radius determined by the higher-order terms. The Newton-Raphson iteration converges if:

```
|V_{k+1} - V_k| < R_conv ≈ min(1/|C₁|, 1/√|C₂|)
```

for significant coefficients `C₁` or `C₂`.

#### **1.3 Damping for Stiff Nonlinearities**

When the capacitance varies rapidly with voltage (large `dC/dV`), damping is applied:

```
V_{k+1} = V_k + λ × ΔV
```

where `0 < λ ≤ 1` is a damping factor reduced when:
- Oscillations are detected in the `V_k` sequence
- `|ΔV|` increases between iterations
- Maximum iterations are approached without convergence

### **2. Time Integration Stability Analysis**

#### **2.1 Stability Regions for Integration Methods**

Different numerical integration methods have distinct stability properties:

**Backward Euler (α = 1):**
- Unconditionally stable (A-stable)
- Stability region: entire left half of complex plane
- Introduces numerical damping: `|H(jω)| < 1` for all ω

**Trapezoidal Rule (α = 0.5):**
- Unconditionally stable (A-stable)
- Stability region: entire left half-plane
- Preserves energy for linear systems: `|H(jω)| = 1`

**Gear-2 (α = 2/3):**
- A-stable
- Stability region includes entire left half-plane
- Moderate numerical damping

#### **2.2 Stiff System Handling**

For circuits with widely separated time constants (stiff systems), the integration method choice affects stability:

- Backward Euler handles stiffness well but may overdamp fast transients
- Trapezoidal rule can exhibit ringing for stiff problems
- Ngspice may switch methods based on LTE estimates and circuit activity

#### **2.3 Amplitude and Phase Errors**

Each integration method introduces numerical errors:

**Backward Euler:**
- Amplitude error: `|H(jω)| ≈ 1/(1 + ωΔt)` (damping)
- Phase error: `∠H(jω) ≈ -ωΔt` (phase lag)

**Trapezoidal Rule:**
- Amplitude error: `|H(jω)| = 1` (no amplitude error)
- Phase error: `∠H(jω) ≈ -ωΔt/2` (half the phase lag of Backward Euler)

### **3. Local Truncation Error Control**

#### **3.1 LTE-Based Time-Step Selection**

The adaptive time-step algorithm uses the normalized LTE:

```
LTE_norm = LTE / (RELTOL × max(|Q|, |Q_pred|) + CHGTOL)
```

Time-step adjustment follows:
```
if LTE_norm > 1:    Δt_new = 0.9 × Δt_old × √(1/LTE_norm)
if LTE_norm < 0.1:  Δt_new = 1.1 × Δt_old (limited to 2× increase)
```

#### **3.2 Derivative Estimation Accuracy**

The LTE calculation uses finite differences to estimate derivatives:

```
dV/dt ≈ (V_n - V_{n-1})/Δt
d²V/dt² ≈ (dV/dt - dV/dt_{old})/Δt
```

For nonlinear capacitance, additional derivatives are needed:
```
dC/dV = C₁ + 2C₂·V  (for polynomial model)
d²C/dV² = 2C₂
```

#### **3.3 Error Accumulation Prevention**

To prevent error accumulation in long simulations:
1. Charge conservation is enforced at each time step
2. State variables (`Q`, `V`) are stored with full precision
3. The `CKTrhsOld` array maintains history for LTE calculation
4. Time-step reductions trigger re-initialization of derivative estimates

### **4. AC Analysis Convergence**

#### **4.1 Frequency Domain Convergence**

For AC analysis, convergence is measured in the complex domain:

```
|V_new(ω) - V_old(ω)| ≤ ε_AC = RELTOL × |V(ω)| + VNTOL
```

Both real and imaginary parts must converge independently.

#### **4.2 Frequency Sweep Continuity**

During frequency sweeps, the solution at frequency `f_k` initializes the Newton-Raphson iteration at `f_{k+1}`:

```
V_initial(f_{k+1}) = V_solution(f_k) × (f_{k+1}/f_k)^{jφ}
```

where `φ` estimates the phase shift based on circuit topology.

#### **4.3 Small-Signal Linearization Accuracy**

The AC analysis linearization around the DC operating point assumes:

```
|ΔV| ≪ V_T (thermal voltage) for accurate dC/dV calculation
```

If the AC signal amplitude is too large, harmonic distortion occurs, requiring transient analysis instead.

### **5. Convergence Acceleration Techniques**

#### **5.1 Predictor-Corrector Methods**

For smooth waveforms, predictor-corrector methods improve convergence:

1. **Predictor**: Extrapolate from previous solutions: `V_pred = 2V_n - V_{n-1}`
2. **Corrector**: Apply Newton-Raphson starting from `V_pred`
3. **Error estimation**: Compare predictor and corrector solutions

#### **5.2 History Weighting**

Previous solutions are weighted based on time-step changes:

```
V_initial = w₁×V_n + w₂×V_{n-1} + w₃×V_{n-2}
```

where weights `w_i` depend on `Δt_n/Δt_{n-1}` ratios.

#### **5.3 Matrix Reuse Optimization**

Since the capacitor's Jacobian changes slowly for small voltage steps, matrix factorization can be reused:
- If `|ΔV|/|V| < 0.01`, reuse previous Jacobian
- If `0.01 ≤ |ΔV|/|V| < 0.1`, update Jacobian every 2-3 iterations
- If `|ΔV|/|V| ≥ 0.1`, update Jacobian every iteration

### **6. Temperature Analysis Convergence**

#### **6.1 Self-Consistent Temperature Solution**

When temperature is solved self-consistently with electrical behavior:

```
|T_{new} - T_{old}| ≤ ε_T = 0.1 K (typical)
|I(T_{new}) - I(T_{old})| ≤ ε_I = RELTOL × |I|
```

#### **6.2 Temperature Ramp Convergence**

During temperature sweeps, the solution at `T_k` initializes `T_{k+1}`:

```
V_initial(T_{k+1}) = V_solution(T_k) + (dV/dT) × ΔT
```

where `dV/dT` is estimated from previous temperature points.

### **7. Safe Operating Area Convergence**

#### **7.1 SOA Boundary Smoothing**

Hard SOA limits can cause convergence problems. The implementation uses smoothed boundaries:

```
V_effective = V_max × tanh(V/V_max)
```

This provides a differentiable transition near the limit.

#### **7.2 SOA-Aware Time-Step Control**

When approaching SOA limits, the time step is reduced:

```
if |V| > 0.8 × V_max: Δt_new = Δt_old × (1 - |V|/V_max)
```

This provides finer resolution near operating limits.

### **8. Implementation-Specific Convergence Controls**

#### **8.1 Default Tolerance Values**

Ngspice uses conservative default tolerances for capacitors:

| Parameter | Symbol | Default Value | Purpose |
|-----------|--------|---------------|---------|
| Relative Tolerance | `RELTOL` | 1e-3 | General relative error |
| Absolute Voltage Tolerance | `VNTOL` | 1e-6 V | Voltage convergence |
| Absolute Charge Tolerance | `CHGTOL` | 1e-14 C | Charge conservation |
| Absolute Current Tolerance | `ABSTOL` | 1e-12 A | Current convergence |
| LTE Safety Factor | `TRTOL` | 7.0 | Time-step control |
| Minimum Time Step | `TSTEPMIN` | 1e-15 s | Prevents underflow |

#### **8.2 Convergence Diagnostics**

The capacitor model provides convergence diagnostics through:
- `CKTnoncon` counter for convergence failures
- State variable history for oscillation detection
- LTE monitoring for time-step adequacy
- SOA violation flags for reliability checking

#### **8.3 Recovery from Convergence Failure**

When convergence fails, Ngspice employs:
1. **Time-step reduction** by factors of 2, 4, or 8
2. **Integration method switching** to more stable methods
3. **Damping factor reduction** for conservative steps
4. **Reinitialization** from last converged point
5. **Fallback to DC analysis** if transient fails repeatedly

This comprehensive convergence analysis ensures the capacitor model provides accurate, stable simulations while maintaining robust integration with SPICE's numerical algorithms. The implementation balances computational efficiency with numerical reliability across all analysis types and operating conditions.

## **C Implementation**

The Ngspice capacitor device model is implemented through a coordinated suite of C source files that manage matrix allocation, API registration, parameter handling, and Safe Operating Area (SOA) validation. This section details the specific C structures, functions, and algorithms that realize the capacitor's integration into SPICE's simulation kernel, explicitly mapping the mathematical formulations to their computational implementations.

### **1. Core Data Structures for Matrix Connectivity**

The capacitor's electrical connectivity and state are defined in `capdefs.h` through two primary structures that interface directly with SPICE's Modified Nodal Analysis (MNA) matrix system.

#### **1.1 Instance Structure (`sCAPinstance`)**
This structure encapsulates all data for a single capacitor instance, with members specifically designed for matrix stamping and state management.

```c
typedef struct sCAPinstance {
    /* SPICE Node Indices - Direct mapping to MNA matrix rows/columns */
    int CAPposNode;                 /* Positive terminal node index */
    int CAPnegNode;                 /* Negative terminal node index */
    int CAPposPrimeNode;            /* Internal positive node (if series resistance modeled) */
    int CAPnegPrimeNode;            /* Internal negative node (if series resistance modeled) */
    
    /* Parameter Storage - Direct from SPICE netlist with mathematical meaning */
    double CAPcapac;                /* Nominal capacitance C₀ (Farads) */
    double CAPc;                    /* Alternative capacitance parameter */
    double CAPtc1;                  /* First-order temperature coefficient TC₁ (1/°C) */
    double CAPtc2;                  /* Second-order temperature coefficient TC₂ (1/°C²) */
    double CAPm;                    /* Multiplier for parallel devices */
    double CAPscale;                /* Scale factor for layout scaling */
    double CAPtemp;                 /* Instance-specific temperature (K) */
    double CAPic;                   /* Initial condition voltage V(0) */
    
    /* Voltage-Dependent Capacitance Coefficients */
    double CAPc0;                   /* Constant coefficient for C(V) = C₀ + C₁·V + C₂·V² */
    double CAPc1;                   /* Linear coefficient C₁ */
    double CAPc2;                   /* Quadratic coefficient C₂ */
    double CAPvc1;                  /* Alternative linear voltage coefficient */
    double CAPvc2;                  /* Alternative quadratic voltage coefficient */
    
    /* State Vector Indices - Critical for charge conservation and LTE calculation */
    int CAPstate;                   /* Index in state vector for voltage V(t) */
    int CAPqstate;                  /* Index in state vector for charge Q(t) */
    
    /* Sparse Matrix Pointers (SMP) - Direct pointers into Ngspice's sparse matrix */
    double *CAPposPosPtr;           /* Pointer to G[pos][pos] matrix element */
    double *CAPposNegPtr;           /* Pointer to G[pos][neg] matrix element */
    double *CAPnegPosPtr;           /* Pointer to G[neg][pos] matrix element */
    double *CAPnegNegPtr;           /* Pointer to G[neg][neg] matrix element */
    
    /* Runtime State Variables - Computed during simulation */
    double CAPvoltage;              /* Instantaneous terminal voltage V(t) */
    double CAPcharge;               /* Stored charge Q(t) = ∫C(V)dV */
    double CAPconduct;              /* Equivalent conductance G_eq for companion model */
    double CAPcap;                  /* Actual capacitance after scaling C_actual */
    
    /* Parameter Presence Flags - Bitfields for memory efficiency */
    unsigned CAPcapacGiven  :1;     /* Capacitance parameter specified */
    unsigned CAPtc1Given    :1;     /* Temperature coefficient TC₁ specified */
    unsigned CAPicGiven     :1;     /* Initial condition specified */
    unsigned CAPc0Given     :1;     /* Voltage-dependent C₀ specified */
    /* ... additional flags ... */
    
    /* Linked List Pointers for Instance Management */
    struct sCAPinstance *CAPnextInstance;
    struct sCAPmodel *CAPmodPtr;
    IFuid CAPname;
} CAPinstance;
```

**Mathematical Mapping:** The `CAPstate` and `CAPqstate` indices provide direct access to the state vector where `V(t)` and `Q(t)` are stored, enabling the numerical integration formulas `Q_{n+1} = Q_n + Δt·I_{n+1}` (Backward Euler) or `Q_{n+1} = Q_n + (Δt/2)·(I_n + I_{n+1})` (Trapezoidal). The matrix pointers (`CAPposPosPtr`, etc.) reference the exact locations in the sparse conductance matrix where the capacitor stamps its `G_eq` values.

#### **1.2 Model Structure (`sCAPmodel`)**
This minimal structure manages collections of capacitor instances, primarily serving as a container for the linked list of instances.

```c
typedef struct sCAPmodel {
    int CAPmodType;                 /* Device type identifier */
    struct sCAPmodel *CAPnextModel; /* Next capacitor model in circuit */
    CAPinstance *CAPinstances;      /* Linked list of all instances */
    IFuid CAPmodName;               /* Model name string */
} CAPmodel;
```

### **2. SPICE Device API Binding and Registration**

The capacitor device registers with the Ngspice simulation kernel through the `SPICEdev` structure defined in `capinit.c`. This structure defines the complete interface between the capacitor model and all SPICE analysis modes.

```c
SPICEdev CAPinfo = {
    .DEVpublic = {
        .name = "Capacitor",
        .description = "Linear and nonlinear capacitor",
        .terms = 2,                  /* Two-terminal device */
        .numNames = 2,
        .termNames = {"+", "-"},     /* Netlist terminal names */
        .numInstanceParms = 14,      /* Parameters in CAPmPTable */
        .numModelParms = 0,          /* Capacitor has no model parameters */
    },
    
    /* Critical Function Pointers - Each maps to a specific simulation phase */
    .DEVparam = CAPparam,            /* Parameter parsing: netlist → C structs */
    .DEVmodParam = CAPmParam,        /* Model parameter parsing (unused for capacitor) */
    .DEVload = CAPload,              /* Transient analysis: stamps i = dQ/dt */
    .DEVsetup = CAPsetup,            /* Matrix setup: allocates SMP pointers & state indices */
    .DEVpzSetup = CAPpzSetup,        /* Pole-zero analysis setup */
    .DEVtemperature = CAPtemp,       /* Temperature scaling: applies C(T) formula */
    .DEVtrunc = CAPtrunc,            /* LTE calculation: estimates d³q/dt³ for time-step control */
    .DEVacLoad = CAPacLoad,          /* AC analysis: computes Y(ω) = jωC */
    .DEVconvTest = CAPconvTest,      /* Convergence testing: checks |ΔV|, |ΔQ| against tolerances */
    .DEVdestroy = CAPdestroy,        /* Memory cleanup: frees all allocated structures */
    .DEVmodDelete = CAPmDelete,      /* Model deletion */
    .DEVinstDelete = CAPdelete,      /* Instance deletion */
    .DEVask = CAPask,                /* Parameter querying */
    .DEVpzLoad = CAPpzLoad,          /* Pole-zero analysis loading */
    .DEVnoise = CAPnoise,            /* Noise analysis: thermal noise from series resistance */
    .DEVsoaCheck = CAPsoaCheck,      /* Safe Operating Area checking */
    
    /* Structure Sizes for Memory Allocation */
    .DEVinstSize = sizeof(CAPinstance),
    .DEVmodSize = sizeof(CAPmodel)
};
```

**API Integration:** Each function pointer corresponds to a specific phase of SPICE simulation. When Ngspice enters transient analysis, it calls `CAPload()` for each capacitor instance to stamp the companion model `i = G_eq·V + I_eq` into the circuit matrix. During setup, `CAPsetup()` allocates the sparse matrix pointers that `CAPload()` will later use.

### **3. Parameter System and Mask Definitions**

The capacitor's parameter system in `capmpar.c` and `capmask.c` defines the mapping between SPICE netlist syntax, internal parameter indices, and C structure members.

#### **3.1 Parameter Table (`capmpar.c`)**
```c
static IFparm CAPmPTable[] = {
    /* Basic Capacitance Parameters */
    IOP("c",      CAP_C,      IF_REAL, "Capacitance"),
    IOP("cap",    CAP_CAP,    IF_REAL, "Capacitance"),
    
    /* Temperature Coefficients */
    IOP("tc1",    CAP_TC1,    IF_REAL, "First order temperature coeff. TC₁"),
    IOP("tc2",    CAP_TC2,    IF_REAL, "Second order temperature coeff. TC₂"),
    
    /* Scaling Parameters */
    IOP("m",      CAP_M,      IF_REAL, "Multiplier for parallel devices"),
    IOP("scale",  CAP_SCALE,  IF_REAL, "Scale factor for layout scaling"),
    
    /* Temperature Parameters */
    IOP("temp",   CAP_TEMP,   IF_REAL, "Instance temperature T"),
    IOP("dtemp",  CAP_DTEMP,  IF_REAL, "Delta temperature from circuit"),
    
    /* Initial Conditions */
    IOP("ic",     CAP_IC,     IF_REAL, "Initial voltage V(0)"),
    
    /* Voltage-Dependent Capacitance Parameters */
    IOP("c0",     CAP_C0,     IF_REAL, "Constant coefficient C₀ for C(V)=C₀+C₁·V+C₂·V²"),
    IOP("c1",     CAP_C1,     IF_REAL, "Linear coefficient C₁"),
    IOP("c2",     CAP_C2,     IF_REAL, "Quadratic coefficient C₂"),
    IOP("vc1",    CAP_VC1,    IF_REAL, "Linear voltage coefficient"),
    IOP("vc2",    CAP_VC2,    IF_REAL, "Quadratic voltage coefficient"),
};
```

#### **3.2 Parameter Masks (`capmask.c`)**
```c
#define CAP_C       1   /* Maps to inst->CAPcapac or inst->CAPc */
#define CAP_TC1     3   /* Maps to inst->CAPtc1 */
#define CAP_IC      9   /* Maps to inst->CAPic */
#define CAP_C0      10  /* Maps to inst->CAPc0 */
#define CAP_C1      11  /* Maps to inst->CAPc1 */
#define CAP_C2      12  /* Maps to inst->CAPc2 */
/* ... additional masks ... */
```

**Parameter Processing:** When Ngspice parses a netlist statement like `C1 1 0 1nF ic=5V tc1=0.001`, it uses the `CAPmPTable` to identify parameters, then stores values in the corresponding `CAPinstance` members using the mask indices. The bitfield flags (`CAPicGiven`, `CAPtc1Given`) track which parameters were explicitly specified.

### **4. Matrix Setup and SMP Allocation**

The `CAPsetup()` function in `capsetup.c` performs critical initialization: allocating sparse matrix pointers, assigning state vector indices, and applying scaling factors.

```c
int CAPsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    CAPmodel *model = (CAPmodel*)inModel;
    CAPinstance *here;
    
    for( ; model !=