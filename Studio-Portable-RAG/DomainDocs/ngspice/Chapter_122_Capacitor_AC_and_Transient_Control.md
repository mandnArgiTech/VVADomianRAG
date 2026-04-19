# Capacitor: AC Analysis and Transient Time-Stepping

_Generated 2026-04-12 18:49 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/cappzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/captrunc.c`

# **Chapter: Capacitor: AC Analysis and Transient Time-Stepping**

## **Introduction**

This chapter details the implementation of AC analysis and adaptive transient time-stepping for the capacitor device within the Ngspice circuit simulator. The functionality is distributed across three core C source files that handle distinct aspects of frequency-domain response and numerical integration:

*   **`capacld.c`**: Implements the `CAPacLoad()` function, which computes the small-signal complex admittance `Y(ω) = jωC` for AC analysis. It stamps the purely imaginary matrix contributions into Ngspice's separate real and imaginary sparse matrix system, enabling frequency-domain simulation.
*   **`cappzld.c`**: Contains the `CAPpzLoad()` function, which generalizes the AC analysis to the full complex Laplace domain for pole-zero analysis. It computes the admittance `Y(s) = sC = (σ + jω)C` and stamps both real (σC) and imaginary (ωC) components into a unified complex matrix.
*   **`captrunc.c`**: Implements the `CAPtrunc()` function, the cornerstone of adaptive time-step control. It estimates the Local Truncation Error (LTE) for the trapezoidal integration method using finite-difference approximations of voltage derivatives. This error estimate is used to dynamically adjust the simulation time step (`Δt`), balancing computational efficiency with numerical accuracy during transient analysis.

Together, these files form the computational bridge between the mathematical formulations of capacitor behavior in the frequency and time domains and their efficient, stable integration into SPICE's simulation kernel. The following sections present the complete mathematical formulation governing these analyses, followed by a detailed exposition of the corresponding C implementation.

## **Mathematical Formulation**

The capacitor model in Ngspice implements a comprehensive mathematical framework for AC analysis and transient time-stepping that integrates directly with SPICE's Modified Nodal Analysis (MNA) and numerical integration algorithms. The formulation encompasses frequency-domain admittance, time-domain discretization, and adaptive time-step control based on Local Truncation Error (LTE) estimation.

### **1. AC Analysis: Frequency Domain Admittance**

#### **1.1 Small-Signal Complex Admittance**

For AC analysis at angular frequency ω = 2πf, the capacitor contributes purely imaginary admittance to the circuit's complex Y-matrix:

```
Y(jω) = jωC
```

where C is the small-signal capacitance evaluated at the DC operating point. For linear capacitors, C is constant; for voltage-dependent capacitors, C = dQ/dV evaluated at the DC bias voltage V_DC.

#### **1.2 Complex Matrix Stamp Pattern**

The capacitor stamps into the complex admittance matrix with the symmetric pattern:

```
[  Y   -Y ]
[ -Y    Y ]  where Y = jωC
```

This corresponds to the sparse matrix entries:
- `Y_pp = +jωC` (positive node self-admittance)
- `Y_nn = +jωC` (negative node self-admittance)
- `Y_pn = -jωC` (cross admittance)
- `Y_np = -jωC` (cross admittance)

#### **1.3 Small-Signal Capacitance for Nonlinear Models**

For voltage-dependent capacitors with polynomial model `C(V) = C₀ + C₁·V + C₂·V²`, the small-signal capacitance at DC operating point V_DC is:

```
C_small-signal = dQ/dV = C₀ + 2C₁·V_DC + 3C₂·V_DC²
```

This derivative represents the linearized capacitance around the operating point for AC analysis.

#### **1.4 Pole-Zero Analysis in Laplace Domain**

For pole-zero analysis using complex frequency s = σ + jω, the capacitor's admittance becomes:

```
Y(s) = sC = (σ + jω)C
```

This requires stamping complex numbers into the matrix with both real (σC) and imaginary (ωC) components.

### **2. Transient Analysis: Time-Domain Discretization**

#### **2.1 Capacitor Differential Equation**

The fundamental time-domain equation governing capacitor behavior is:

```
i(t) = dQ/dt = d[C(V)·V]/dt
```

For linear capacitors, this simplifies to `i(t) = C·dV/dt`.

#### **2.2 Trapezoidal Integration Method**

Ngspice primarily uses trapezoidal integration for charge conservation. Discretizing the charge equation yields:

```
Q_{n+1} = Q_n + (Δt/2)·(i_n + i_{n+1})
```

where:
- `Q_n`, `i_n` are charge and current at time t_n
- `Q_{n+1}`, `i_{n+1}` are charge and current at time t_{n+1}
- `Δt = t_{n+1} - t_n` is the time step

#### **2.3 Companion Model Formulation**

The discretized equation is linearized to create a companion model suitable for Newton-Raphson iteration:

```
i_{n+1} = G_eq·V_{n+1} + I_eq
```

where the equivalent conductance and current source are:

```
G_eq = 2C/Δt
I_eq = -[(2C/Δt)·V_n + i_n]
```

This companion model allows the capacitor to be represented as a linear conductance `G_eq` in parallel with a current source `I_eq` during each Newton-Raphson iteration.

#### **2.4 Matrix Stamp for Transient Analysis**

The companion model stamps into the MNA matrix as:

```
[  G_eq  -G_eq ] [ V_p ]   [ -I_eq ]
[ -G_eq   G_eq ] [ V_n ] = [  I_eq ]
```

This corresponds to updating the sparse matrix entries:
- `G_pp += G_eq`, `G_nn += G_eq`
- `G_pn -= G_eq`, `G_np -= G_eq`
- `RHS_p -= I_eq`, `RHS_n += I_eq`

### **3. Voltage-Dependent Capacitance Models**

#### **3.1 Polynomial Model**

The capacitor supports polynomial voltage dependence:

```
C(V) = C₀ + C₁·V + C₂·V²
```

where:
- `C₀` = voltage-independent capacitance (parameter `c0`)
- `C₁` = linear voltage coefficient (parameter `c1`) in F/V
- `C₂` = quadratic voltage coefficient (parameter `c2`) in F/V²

#### **3.2 Charge Calculation for Nonlinear Capacitance**

The stored charge is the integral of capacitance:

```
Q(V) = ∫ C(V) dV = C₀·V + (C₁/2)·V² + (C₂/3)·V³
```

This analytical integral ensures exact charge conservation for the polynomial model.

#### **3.3 Piecewise Linear Regions**

For improved numerical stability with strong nonlinearities, piecewise linear regions can be defined using voltage breakpoints `VC1` and `VC2`:

```
C(V) = C₀                            for V < VC1
C(V) = C₀ + C₁·V + C₂·V²            for VC1 ≤ V ≤ VC2  
C(V) = C₀ + C₁·VC2 + C₂·VC2²        for V > VC2 (saturation)
```

### **4. Local Truncation Error (LTE) Estimation**

#### **4.1 LTE Formula for Trapezoidal Integration**

The Local Truncation Error estimates the error introduced by the numerical integration method. For trapezoidal integration of charge q(t) = C·v(t):

```
LTE = |(Δt³/12)·q‴(τ)| = |(Δt³/12)·C·v‴(τ)|
```

where τ is some point in the interval [t_n, t_{n+1}] and v‴ is the third derivative of voltage.

#### **4.2 Derivative Estimation via Finite Differences**

Since the exact third derivative is unavailable, it is estimated using finite differences from stored voltage history:

```
v̇ ≈ (v_n - v_{n-1})/Δt                    (first derivative)
v̈ ≈ (v_n - 2v_{n-1} + v_{n-2})/Δt²        (second derivative)
v‴ ≈ (v_n - 3v_{n-1} + 3v_{n-2} - v_{n-3})/Δt³ (third derivative)
```

These estimates use the state vector history stored in `CKTstates[]`.

#### **4.3 Normalized LTE for Time-Step Control**

The LTE is normalized against the current charge magnitude for time-step adjustment:

```
LTE_norm = LTE / (|q| + ε)
```

where ε = `CKTvoltTol` (typically 1e-6 V) prevents division by zero.

### **5. Time-Step Adaptation Algorithm**

#### **5.1 Time-Step Reduction Criteria**

When the normalized LTE exceeds the truncation error tolerance `trtol` (default 7.0):

```
if LTE_norm > trtol:
    Δt_new = 0.9·Δt_old·√(trtol / LTE_norm)
```

The factor 0.9 provides conservative reduction, and the square root accounts for the LTE's cubic dependence on Δt.

#### **5.2 Time-Step Increase Criteria**

When the LTE is well below tolerance, the time step can be increased:

```
if LTE_norm < 0.1·trtol:
    Δt_new = 1.1·Δt_old (capped at 2× increase)
```

#### **5.3 Minimum Time-Step Enforcement**

The time step is bounded below by `CKTminTimeStep` (typically 1e-15 s) to prevent underflow and infinite loops.

### **6. Temperature Scaling Effects**

#### **6.1 Temperature-Dependent Capacitance**

Capacitance varies with temperature according to:

```
C(T) = C(T_nom)·[1 + TC₁·(T - T_nom) + TC₂·(T - T_nom)²]
```

where:
- `T_nom` = nominal temperature (300.15 K default)
- `TC₁` = first-order temperature coefficient (`tc1` parameter)
- `TC₂` = second-order temperature coefficient (`tc2` parameter)

#### **6.2 AC Analysis with Temperature Effects**

For AC analysis, the temperature-scaled capacitance directly affects the admittance:

```
Y(jω, T) = jω·C(T) = jω·C(T_nom)·[1 + TC₁·ΔT + TC₂·ΔT²]
```

### **7. Geometric Capacitance Models**

#### **7.1 Junction Capacitance Model**

For semiconductor junction capacitors:

```
C_junction = C_J·W·L + C_JSW·2·(W + L)
```

where:
- `C_J` = bottom junction capacitance per area (F/m²)
- `C_JSW` = sidewall junction capacitance per perimeter (F/m)
- `W`, `L` = width and length of the junction

#### **7.2 Parallel Plate Capacitance Model**

For oxide capacitors:

```
C_oxide = (ε₀·ε_r·W·L) / t_ox
```

where:
- `ε₀` = vacuum permittivity (8.854e-12 F/m)
- `ε_r` = relative dielectric constant
- `t_ox` = oxide thickness

### **8. Initial Condition Processing**

#### **8.1 Initial Voltage Specification**

When the `ic` parameter specifies initial voltage V_ic:

```
V(0) = V_ic
Q(0) = ∫ C(V) dV evaluated at V_ic
```

For linear capacitors: `Q(0) = C·V_ic`
For polynomial capacitors: `Q(0) = C₀·V_ic + (C₁/2)·V_ic² + (C₂/3)·V_ic³`

#### **8.2 State Vector Initialization**

The initial conditions populate the state vector and history arrays:

```
CKTstate0[CAPstate] = Q(0)        (initial charge)
CKTstate1[CAPstate] = Q(0)        (backup for LTE)
CAPv_hist[0] = CAPv_hist[1] = V_ic (voltage history)
CAPq_hist[0] = CAPq_hist[1] = Q(0) (charge history)
```

### **9. Safe Operating Area (SOA) Constraints**

#### **9.1 Voltage Rating Check**

```
|V| ≤ V_max
```

where `V_max` is the maximum voltage rating parameter.

#### **9.2 Electric Field Check for Oxide Capacitors**

```
E_field = |V| / t_ox ≤ E_max ≈ 1 GV/m (for SiO₂)
```

#### **9.3 Energy Storage Check**

```
E_stored = 0.5·C·V² ≤ E_max (typically 1 J threshold)
```

## **Convergence Analysis**

The capacitor model's integration into SPICE's Newton-Raphson solver requires rigorous convergence analysis to ensure numerical stability across AC analysis, transient simulation with adaptive time-stepping, and handling of nonlinear voltage-dependent capacitance.

### **1. Newton-Raphson Convergence for AC Analysis**

#### **1.1 Complex Variable Convergence**

For AC analysis with complex voltages `V = V_re + jV_im`, convergence must be achieved for both real and imaginary parts independently:

```
|V_re^{new} - V_re^{old}| ≤ ε_V = RELTOL·max(|V_re^{new}|, |V_re^{old}|) + VNTOL
|V_im^{new} - V_im^{old}| ≤ ε_V = RELTOL·max(|V_im^{new}|, |V_im^{old}|) + VNTOL
```

#### **1.2 Frequency Continuity and Predictor Initialization**

During frequency sweeps, the solution at frequency `f_k` provides an initial guess for `f_{k+1}`:

```
V_initial(f_{k+1}) = V_solution(f_k) × (f_{k+1}/f_k)^{jφ}
```

where the phase shift φ is estimated from the circuit's dominant time constant `τ = RC` as `φ = -arctan(2πfτ)`.

#### **1.3 Small-Signal Linearization Validity**

The AC analysis assumes small-signal conditions:

```
|ΔV_AC| ≪ V_T (thermal voltage ≈ 26 mV at 300K)
```

If AC signal amplitudes violate this assumption, harmonic distortion occurs, requiring transient analysis instead of linear AC analysis.

### **2. Transient Analysis Convergence**

#### **2.1 Voltage Convergence Test**

The primary convergence criterion for Newton-Raphson iteration:

```
|V^{new} - V^{old}| ≤ ε_V = RELTOL·max(|V^{new}|, |V^{old}|) + VNTOL
```

where:
- `RELTOL` = relative tolerance (default 1e-3)
- `VNTOL` = absolute voltage tolerance (default 1e-6 V)

#### **2.2 Charge Convergence Test**

For charge conservation, an additional convergence test is applied:

```
|Q^{new} - Q^{old}| ≤ ε_Q = RELTOL·max(|Q^{new}|, |Q^{old}|) + 1e-12
```

The absolute tolerance 1e-12 C corresponds to approximately 6.24 million electrons, ensuring physical charge conservation.

#### **2.3 Convergence Acceleration for Nonlinear Capacitance**

For voltage-dependent capacitance `C(V)`, the Newton-Raphson Jacobian includes the derivative term:

```
J = ∂i/∂V = G_eq + (2/Δt)·V·(dC/dV)
```

where `dC/dV = C₁ + 2C₂·V` for polynomial model. When `|dC/dV|` is large (strong nonlinearity), damping may be required:

```
V_{k+1} = V_k + λ·ΔV, where 0 < λ ≤ 1
```

The damping factor λ is reduced when:
- Oscillations are detected in the `V_k` sequence
- `|ΔV|` increases between iterations
- Maximum iteration count is approached without convergence

### **3. Local Truncation Error Control and Time-Step Stability**

#### **3.1 LTE-Based Time-Step Selection**

The adaptive time-step algorithm uses the normalized LTE:

```
LTE_norm = LTE / (|q| + VNTOL)
```

Time-step adjustment follows the rule:
```
if LTE_norm > TRTOL:    Δt_new = 0.9·Δt_old·√(TRTOL / LTE_norm)
if LTE_norm < 0.1·TRTOL: Δt_new = min(1.1·Δt_old, 2·Δt_old)
```

where `TRTOL` is the truncation error tolerance (default 7.0).

#### **3.2 Stability Regions for Integration Methods**

Different integration methods have distinct stability properties:

**Trapezoidal Rule:**
- Unconditionally stable (A-stable)
- Stability region: entire left half of complex plane
- No amplitude error: `|H(jω)| = 1` for all ω
- Phase error: `∠H(jω) ≈ -ωΔt/2` (half the delay of Backward Euler)

**Backward Euler:**
- Unconditionally stable (A-stable)
- Stability region: entire left half-plane
- Amplitude error: `|H(jω)| ≈ 1/(1 + ωΔt)` (numerical damping)
- Phase error: `∠H(jω) ≈ -ωΔt` (full step delay)

#### **3.3 Stiff System Handling**

For circuits with widely separated time constants (stiff systems), the choice of Δt affects stability:
- Large Δt may overdamp fast transients (Backward Euler) or cause ringing (Trapezoidal)
- Ngspice may switch to Backward Euler when Trapezoidal exhibits stability issues
- The LTE estimator automatically reduces Δt for fast transients

### **4. Convergence for Voltage-Dependent Capacitance**

#### **4.1 Convergence Radius for Polynomial Models**

The polynomial capacitance model `C(V) = C₀ + C₁·V + C₂·V²` has a finite convergence radius determined by the higher-order terms. Newton-Raphson converges if the voltage step satisfies:

```
|ΔV| < R_conv ≈ min(1/|C₁/C₀|, 1/√|C₂/C₀|)
```

For strong nonlinearities (large `C₁` or `C₂`), the initial guess must be within this radius.

#### **4.2 Predictor-Corrector Methods for Smooth Waveforms**

For smoothly varying signals, predictor-corrector methods improve convergence:

1. **Predictor:** Extrapolate from previous solutions using polynomial fitting:
   ```
   V_pred = 2V_n - V_{n-1}  (linear extrapolation)
   V_pred = 3V_n - 3V_{n-1} + V_{n-2}  (quadratic extrapolation)
   ```

2. **Corrector:** Apply Newton-Raphson starting from `V_pred`

3. **Error Estimation:** Compare predictor and corrector solutions to estimate local error

#### **4.3 History Weighting for Rapid Changes**

During rapid voltage changes, previous solutions are weighted based on time-step ratios:

```
V_initial = w₀·V_n + w₁·V_{n-1} + w₂·V_{n-2}
```

where weights are computed as:
```
w₀ = 1 + α·(Δt_n/Δt_{n-1})
w₁ = -α·(Δt_n/Δt_{n-1})
w₂ = α·(Δt_n/Δt_{n-1}) - 1
```
with α typically 0.5-0.8.

### **5. AC Analysis Convergence Enhancements**

#### **5.1 Frequency-Domain Predictor**

For closely spaced frequency points in sweeps, the solution is predicted as:

```
V(f_{k+1})_pred = V(f_k) × exp(j·(φ(f_k) + Δφ))
```

where `Δφ = (dφ/df)·Δf` is estimated from previous frequency points.

#### **5.2 Adaptive Frequency Stepping**

In regions of rapid phase/gain change, the frequency step is reduced:

```
if |∠V(f_k) - ∠V(f_{k-1})| > 0.1 rad: Δf_new = 0.5·Δf_old
if |∠V(f_k) - ∠V(f_{k-1})| < 0.01 rad: Δf_new = 2·Δf_old
```

#### **5.3 Complex Matrix Conditioning**

The capacitor's purely imaginary admittance `Y = jωC` contributes only to the imaginary part of the matrix. For circuits with many capacitors, this can lead to ill-conditioning when ω → 0. Ngspice adds a small real conductance `G_min` (typically 1e-12 S) to maintain numerical stability.

### **6. Time Integration Stability Analysis**

#### **6.1 Amplitude and Phase Error Analysis**

Each integration method introduces numerical errors:

**Trapezoidal Rule:**
- Amplitude error: `|H(jω)| = 1` (no amplitude distortion)
- Phase error: `∠H(jω) = -arctan(ωΔt/2) ≈ -ωΔt/2` for ωΔt ≪ 1
- Phase error leads to time delay of `Δt/2`

**Backward Euler:**
- Amplitude error: `|H(jω)| = 1/√(1 + ω²Δt²) ≈ 1 - (ω²Δt²)/2`
- Phase error: `∠H(jω) = -arctan(ωΔt) ≈ -ωΔt`
- Amplitude damping and full-step delay

#### **6.2 Numerical Dispersion**

For high-frequency components, different integration methods exhibit numerical dispersion:

- Trapezoidal: All frequencies experience same phase delay `Δt/2`
- Backward Euler: High frequencies are excessively damped
- This affects simulation of sharp edges and high-frequency content

#### **6.3 Aliasing Prevention**

The time step must satisfy the Nyquist criterion for the highest frequency of interest:

```
Δt ≤ 1/(2·f_max)
```

where `f_max` is the highest significant frequency in the signal. The LTE estimator indirectly enforces this by reducing Δt when high-frequency content is detected via large third derivatives.

### **7. Convergence Diagnostics and Recovery**

#### **7.1 Convergence Failure Detection**

When convergence fails, Ngspice employs multiple diagnostics:

1. **Oscillation Detection:** Check if `V_k` alternates around the solution
2. **Divergence Detection:** Check if `|ΔV|` increases over iterations
3. **Stagnation Detection:** Check if `|ΔV|` is below tolerance but residual is not

#### **7.2 Recovery Strategies**

When convergence fails:

1. **Time-Step Reduction:** Reduce Δt by factors of 2, 4, or 8
2. **Integration Method Switch:** Switch from Trapezoidal to Backward Euler
3. **Damping Increase:** Reduce λ to 0.5, 0.25, or 0.1
4. **Reinitialization:** Restart from last converged point with smaller Δt
5. **Fallback to DC Analysis:** If transient fails repeatedly, attempt DC solution first

#### **7.3 Convergence History Tracking**

The capacitor maintains convergence history in state vectors:

```
CKTstate0[CAPstate] = V_n     (current voltage)
CKTstate1[CAPstate] = Q_n     (current charge)
CKTstates[CAPstate] = dV/dt   (voltage derivative)
CKTstates[CAPstate+1] = d²V/dt² (second derivative)
```

This history enables polynomial extrapolation for initial guesses and LTE estimation.

### **8. Default Tolerance Values and Their Effects**

Ngspice uses conservative default tolerances for capacitor convergence:

| Parameter | Symbol | Default Value | Effect on Convergence |
|-----------|--------|---------------|----------------------|
| Relative Tolerance | `RELTOL` | 1e-3 | Controls relative error in V, Q, I |
| Absolute Voltage Tolerance | `VNTOL` | 1e-6 V | Minimum detectable voltage change |
| Absolute Charge Tolerance | - | 1e-12 C | Minimum charge change (≈6.24M electrons) |
| Truncation Error Tolerance | `TRTOL` | 7.0 | LTE safety factor for Δt control |
| Minimum Time Step | `TSTEPMIN` | 1e-15 s | Prevents underflow in Δt calculation |
| Maximum Time Step | `TSTEPMAX` | 0.1·TSTOP | Prevents missing fast transients |

### **9. Multi-Rate Integration Considerations**

For circuits with both fast and slow dynamics, the capacitor's LTE estimation enables multi-rate integration:

1. **Fast Capacitors** (small C, rapid V changes): Small Δt from LTE control
2. **Slow Capacitors** (large C, slow V changes): Larger Δt possible
3. **Global Δt** = min(all device Δt requests)

This automatic Δt selection ensures accuracy for fast dynamics while maintaining efficiency for slow ones.

### **10. Numerical Conservation Laws**

The capacitor implementation enforces key numerical conservation laws:

1. **Charge Conservation:** `Q_{n+1} - Q_n = (Δt/2)·(i_n + i_{n+1})` exactly for trapezoidal rule
2. **Energy Conservation:** For linear C, trapezoidal rule conserves energy in discrete sense
3. **Symplecticity:** Trapezoidal rule is symplectic for linear systems, preserving phase space volume

These conservation properties ensure physically meaningful simulation results even with finite Δt.

This comprehensive convergence analysis ensures the capacitor model provides accurate, stable simulations across all analysis types while maintaining robust integration with SPICE's numerical algorithms. The implementation balances computational efficiency with numerical reliability, automatically adapting to circuit conditions through LTE-based time-step control and convergence acceleration techniques.

----------

# **Chapter: Capacitor: AC Analysis and Transient Time-Stepping**

## **C Implementation**

The Ngspice capacitor model's AC analysis and transient time-stepping capabilities are implemented through a coordinated set of C source files that map the mathematical formulations for frequency-domain response, numerical integration, and adaptive time-step control directly to SPICE's simulation kernel. This section details the specific C structures, functions, and algorithms that realize these analyses, explicitly connecting the mathematical models to their computational implementations.

### **1. Core Data Structures for Time-Stepping and AC Analysis**

The capacitor's state management for both transient and AC analysis is defined in `capdefs.h` through structures that store history vectors, matrix pointers, and frequency-domain parameters.

#### **1.1 Instance Structure with History Vectors (`sCAPinstance`)**
```c
typedef struct sCAPinstance {
    /* Topological nodes for matrix indexing */
    int CAPposNode;                 /* Positive terminal node index */
    int CAPnegNode;                 /* Negative terminal node index */
    
    /* User parameters with mathematical meaning */
    double CAPcapac;                /* Nominal capacitance C₀ (F) */
    double CAPic;                   /* Initial voltage V(0) (V) */
    double CAPc0, CAPc1, CAPc2;     /* Polynomial coefficients for C(v) = c0 + c1·v + c2·v² */
    double CAPvc1, CAPvc2;          /* Voltage breakpoints for piecewise model */
    
    /* Internal computed values - critical for time-stepping */
    int CAPstate;                   /* State vector index for charge storage */
    double CAPq;                    /* Current charge Q(t) = ∫C(v)dv (C) */
    double CAPcap;                  /* Actual capacitance after scaling (F) */
    double CAPgeq;                  /* Equivalent conductance G_eq = 2C/h (S) */
    double CAPceq;                  /* Equivalent current source I_eq (A) */
    
    /* Sparse matrix pointers - allocated during setup for matrix stamping */
    double *CAPposPosPtr;           /* Pointer to G[p,p] matrix element */
    double *CAPnegNegPtr;           /* Pointer to G[n,n] matrix element */
    double *CAPposNegPtr;           /* Pointer to G[p,n] matrix element */
    double *CAPnegPosPtr;           /* Pointer to G[n,p] matrix element */
    
    /* History vectors for numerical integration - store past values for LTE calculation */
    double CAPq_hist[2];            /* Charge at t-1, t-2: Q_{n-1}, Q_{n-2} */
    double CAPv_hist[2];            /* Voltage at t-1, t-2: V_{n-1}, V_{n-2} */
    
    /* Parameter presence flags (bitfields for memory efficiency) */
    int CAPcapacGiven;              /* C value provided flag */
    int CAPicGiven;                 /* Initial condition flag */
    int CAPc0Given, CAPc1Given, CAPc2Given; /* Polynomial coefficient flags */
    int CAPvc1Given, CAPvc2Given;   /* Voltage breakpoint flags */
} CAPinstance;
```

**Mathematical Mapping:** The `CAPq_hist[2]` and `CAPv_hist[2]` arrays store the history terms `Q_{n-1}`, `Q_{n-2}`, `V_{n-1}`, `V_{n-2}` required for the trapezoidal integration formula `Q_{n+1} = Q_n + (h/2)·(I_n + I_{n+1})` and for Local Truncation Error (LTE) calculation using finite differences. The `CAPstate` index provides access to the state vector where `Q(t)` is stored for charge conservation.

#### **1.2 Model Structure for AC Parameters (`sCAPmodel`)**
```c
typedef struct sCAPmodel {
    /* Geometry and process parameters for AC analysis */
    double CAPcj;                   /* Bottom junction capacitance (F/m²) */
    double CAPcjsw;                 /* Sidewall junction capacitance (F/m) */
    double CAPoxideThickness;       /* Oxide thickness t_ox (m) */
    double CAPrelativePermittivity; /* Dielectric constant ε_r */
    
    /* Safe Operating Area parameters */
    double CAPmaxVoltage;           /* Maximum voltage rating V_max (V) */
    
    /* Temperature coefficients for frequency-dependent effects */
    double CAPtc1, CAPtc2;          /* Temperature coefficients TC₁, TC₂ */
    
    /* Linked list management */
    struct sCAPmodel *CAPnextModel; /* Next model in circuit */
    CAPinstance *CAPinstances;      /* Chain of all instances */
} CAPmodel;
```

### **2. Transient Analysis Implementation with Trapezoidal Integration**

The `CAPload()` function in `capload.c` implements the core transient analysis algorithm, mapping the differential equation `i(t) = dQ/dt` to a linearized companion model using trapezoidal integration.

#### **2.1 Voltage-Dependent Capacitance Calculation**
```c
/* Calculate instantaneous capacitance C(v) */
if(inst->CAPc0Given) {
    /* Nonlinear polynomial model: C(v) = c0 + c1·v + c2·v² */
    cap = inst->CAPc0;
    if(inst->CAPc1Given) 
        cap += inst->CAPc1 * vc;          /* c1·v term */
    if(inst->CAPc2Given) 
        cap += inst->CAPc2 * vc * vc;     /* c2·v² term */
    
    /* Piecewise linear regions with breakpoints */
    if(inst->CAPvc1Given && vc < inst->CAPvc1) {
        cap = inst->CAPc0;  /* Constant below first breakpoint */
    } else if(inst->CAPvc2Given && vc > inst->CAPvc2) {
        /* Saturated value at second breakpoint */
        cap = inst->CAPc0 + inst->CAPc1*inst->CAPvc2 + 
              inst->CAPc2*inst->CAPvc2*inst->CAPvc2;
    }
} else {
    /* Linear capacitance: C(v) = constant */
    cap = inst->CAPcap;
}
```

**Mathematical Implementation:** This code directly computes the polynomial `C(v) = c0 + c1·v + c2·v²`. The piecewise logic implements the mathematical model:
```
C(v) = { c0                     for v < vc1
         c0 + c1·v + c2·v²     for vc1 ≤ v ≤ vc2
         C(vc2)                for v > vc2 }
```

#### **2.2 Trapezoidal Integration Companion Model**
```c
/* Trapezoidal integration parameters */
double h = ckt->CKTdelta;  /* Current time step Δt */

/* Equivalent conductance: G_eq = 2C/h */
double geq = 2.0 * cap / h;

/* Equivalent current source: I_eq = -[(2C/h)·v_old + i_old] */
double v_old = inst->CAPv_hist[0];  /* V_{n-1} */
double i_old = (2.0 * cap / h) * v_old - inst->CAPceq;  /* i_{n-1} */
double ceq = -(geq * v_old + i_old);  /* I_eq */

/* Store for next iteration */
inst->CAPgeq = geq;
inst->CAPceq = ceq;
inst->CAPq = cap * vc;  /* Q_n = C·V_n */
```

**Companion Model Derivation:** This implements the trapezoidal discretization of `i(t) = dQ/dt`:
```
i_{n+1} = (2C/h)·v_{n+1} - [(2C/h)·v_n + i_n]
```
which is linearized as `i_{n+1} = G_eq·v_{n+1} + I_eq` with `G_eq = 2C/h` and `I_eq = -[(2C/h)·v_n + i_n]`.

#### **2.3 Sparse Matrix Stamping for Transient Analysis**
```c
/* Stamp conductance matrix: [G_eq  -G_eq; -G_eq  G_eq] */
*(inst->CAPposPosPtr) += geq;   /* G[p,p] += G_eq */
*(inst->CAPnegNegPtr) += geq;   /* G[n,n] += G_eq */
*(inst->CAPposNegPtr) -= geq;   /* G[p,n] -= G_eq */
*(inst->CAPnegPosPtr) -= geq;   /* G[n,p] -= G_eq */

/* Stamp right-hand side vector */
*(ckt->CKTrhs + inst->CAPposNode) -= ceq;  /* RHS[p] -= I_eq */
*(ckt->CKTrhs + inst->CAPnegNode) += ceq;  /* RHS[n] += I_eq */

/* Update history vectors for next time step */
inst->CAPv_hist[1] = inst->CAPv_hist[0];  /* V_{n-2} = V_{n-1} */
inst->CAPv_hist[0] = vc;                  /* V_{n-1} = V_n */
inst->CAPq_hist[1] = inst->CAPq_hist[0];  /* Q_{n-2} = Q_{n-1} */
inst->CAPq_hist[0] = inst->CAPq;          /* Q_{n-1} = Q_n */
```

**Matrix Pattern Implementation:** The 2×2 conductance matrix pattern `[[G_eq, -G_eq], [-G_eq, G_eq]]` represents the mathematical relationship `i = G_eq·(V_p - V_n) + I_eq`. The history vectors implement the shift register needed for the next iteration's `v_old` and for LTE calculation.

### **3. AC Analysis Implementation for Frequency Domain**

The `CAPacLoad()` function in `capacld.c` implements small-signal AC analysis by computing the complex admittance `Y(ω) = jωC` and stamping it into Ngspice's complex matrix system.

#### **3.1 Complex Admittance Calculation**
```c
int CAPacLoad(GENmodel *inModel, CKTcircuit *ckt) {
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *inst;
    double omega = ckt->CKTomega;  /* Angular frequency ω = 2πf */
    
    for(; model; model = model->CAPnextModel) {
        for(inst = model->CAPinstances; inst; inst = inst->CAPnextInstance) {
            /* Small-signal admittance: Y = jωC */
            double cap = inst->CAPcap;
            double conductance = 0.0;           /* Real part = 0 for ideal capacitor */
            double susceptance = omega * cap;   /* Imaginary part = ωC */
            
            /* Stamp real part (conductance) - zero for ideal capacitor */
            *(inst->CAPposPosPtr) += 0.0;
            *(inst->CAPnegNegPtr) += 0.0;
            *(inst->CAPposNegPtr) -= 0.0;
            *(inst->CAPnegPosPtr) -= 0.0;
            
            /* Stamp imaginary part (susceptance) into separate imaginary matrix */
            /* Ngspice stores complex matrices as real and imaginary parts separately */
            double *posPosImag = SMPmakeElt(ckt->CKTmatrix, 
                                          inst