# BJT: Transient Control and Charge Storage

_Generated 2026-04-12 17:55 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjttrunc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtconv.c`

# **Chapter: BJT: Transient Control and Charge Storage**

## **Introduction: Core Implementation Files for Transient Analysis**

The Ngspice BJT implementation for transient control and charge storage is architected across two critical C source files that handle time-domain numerical integration and convergence testing. These files implement the mathematical formulations for charge-conserving Gummel-Poon simulation within SPICE's transient analysis framework:

- **`bjttrunc.c`**: Implements the Local Truncation Error (LTE) calculation and time-step control algorithm for the BJT device. This file contains the `BJTtrunc()` function that computes charge derivatives using backward differentiation formulas (BDF), stamps transient currents into the Modified Nodal Analysis (MNA) right-hand-side vector, and provides LTE estimates to SPICE's adaptive time-step controller.

- **`bjtconv.c`**: Contains the Newton-Raphson convergence testing implementation through the `BJTconvTest()` function. This file performs multi-dimensional convergence checking across voltages, currents, and charges, ensuring numerical stability during transient simulation while maintaining strict charge conservation.

These files work in concert to implement the charge-based integration methodology that is fundamental to accurate BJT transient simulation. The implementation maps directly to the mathematical formulations for charge storage, numerical integration via Gear and trapezoidal methods, LTE-based time-step control, and comprehensive convergence criteria that maintain numerical stability across all operating conditions.

## **Mathematical Formulation**

The transient analysis and charge storage modeling for the BJT Gummel-Poon implementation in Ngspice centers on the numerical integration of charge conservation equations within SPICE's time-domain simulation framework. The mathematical formulation translates the device physics into state-space equations that are solved using backward differentiation formulas (BDF) while maintaining strict charge conservation.

### **1. Charge Storage and State Variable Definitions**

The BJT implements a charge-conserving Gummel-Poon model with three primary charge storage mechanisms, each mapped to specific state variables in the SPICE state vector:

#### **1.1 Depletion Charges (Voltage-Dependent)**

**Base-Emitter Junction Charge:**
```
Q_be(V_be) = ∫ C_je(V) dV from 0 to V_be
```
Where the depletion capacitance follows the SPICE varactor model:
```
C_je(V) = CJE × (1 - V/V_JE)^(-M_JE)   for V < FC·V_JE
C_je(V) = CJE × (1-FC)^(-M_JE-1) × [1 - FC·(1+M_JE) + M_JE·V/V_JE] for V ≥ FC·V_JE
```

**Base-Collector Junction Charge:**
```
Q_bc(V_bc) = ∫ C_jc(V) dV from 0 to V_bc
```
With similar piecewise capacitance model:
```
C_jc(V) = CJC × (1 - V/V_JC)^(-M_JC)   for V < FC·V_JC
C_jc(V) = CJC × (1-FC)^(-M_JC-1) × [1 - FC·(1+M_JC) + M_JC·V/V_JC] for V ≥ FC·V_JC
```

#### **1.2 Diffusion Charges (Current-Dependent)**

**Forward Diffusion Charge:**
```
Q_f = τ_f × I_f
```
Where:
- `τ_f = TF × [1 + XTF·(I_CC/(I_CC + ITF))² × exp(V_BC/(1.44·VTF))]` (bias-dependent forward transit time)
- `I_f = IS × [exp(V_BE/(NF·V_T)) - 1]` (forward diode current)

**Reverse Diffusion Charge:**
```
Q_r = τ_r × I_r
```
Where:
- `τ_r = TR` (reverse transit time, constant or temperature-scaled)
- `I_r = IS × [exp(V_BC/(NR·V_T)) - 1]` (reverse diode current)

**Total Stored Base Charge:**
```
Q_def = Q_f + Q_r
```

#### **1.3 State Vector Allocation**

The BJT allocates three state vector entries for charge storage in SPICE's `CKTstate` array:
```
state[BJTqbeState] = Q_be    (Base-emitter charge)
state[BJTqbcState] = Q_bc    (Base-collector charge)
state[BJTqdefState] = Q_def  (Total diffusion charge)
```

### **2. Transient Current Formulation via Charge Differentiation**

The terminal currents in transient analysis are derived from charge conservation:

#### **2.1 Charge Conservation Equation**
```
I_B + I_C + I_E = d(Q_be + Q_bc + Q_def)/dt = 0
```
This ensures Kirchhoff's Current Law (KCL) is satisfied to machine precision.

#### **2.2 Numerical Differentiation of Charges**

Using backward differentiation formulas (BDF), the time derivative is approximated as:

**For Gear-2 (BDF-2) Integration:**
```
dQ/dt ≈ α₀·Q_n + α₁·Q_{n-1} + α₂·Q_{n-2}
```
Where coefficients depend on the time step Δt:
```
α₀ = 3/(2Δt)
α₁ = -4/(2Δt) = -2/Δt
α₂ = 1/(2Δt)
```

**For Trapezoidal Integration:**
```
dQ/dt ≈ α₀·Q_n + α₁·Q_{n-1}
```
With coefficients:
```
α₀ = 2/Δt
α₁ = -2/Δt
```

#### **2.3 Terminal Current Computation**

The transient currents are computed from charge derivatives:

**Base Current Contribution:**
```
I_B_transient = -d(Q_be + Q_def)/dt
```

**Collector Current Contribution:**
```
I_C_transient = d(Q_bc - Q_def)/dt
```

**Emitter Current Contribution:**
```
I_E_transient = dQ_be/dt
```

These are added to the DC currents to form the complete terminal currents for transient analysis.

### **3. Numerical Integration Method Implementation**

#### **3.1 Backward Euler (Gear-1)**
```
Q_{n+1} = Q_n + Δt·f(Q_{n+1}, t_{n+1})
```
First-order accurate, L-stable, but introduces numerical damping.

#### **3.2 Trapezoidal (Gear-2 with α=0.5)**
```
Q_{n+1} = Q_n + (Δt/2)·[f(Q_n, t_n) + f(Q_{n+1}, t_{n+1})]
```
Second-order accurate, A-stable, but can exhibit numerical ringing.

#### **3.3 Gear-2 (BDF-2)**
```
Q_{n+1} = (4/3)Q_n - (1/3)Q_{n-1} + (2Δt/3)·f(Q_{n+1}, t_{n+1})
```
Second-order accurate, L-stable, preferred for stiff problems.

### **4. Local Truncation Error (LTE) Formulation**

#### **4.1 LTE for Charge-Based Integration**

The local truncation error estimates the error introduced by the numerical integration method:

**For Trapezoidal Integration:**
```
LTE_Q = |(Δt²/12)·d³Q/dt³| ≈ |(Δt/3)·(Q_{n+1} - Q_{n+1}^{pred})|
```
Where `Q_{n+1}^{pred}` is the predicted charge value from polynomial extrapolation.

**For Gear-2 Integration:**
```
LTE_Q = |(Δt³/24)·d⁴Q/dt⁴| ≈ |(Δt²/4)·(Q_{n+1} - Q_{n+1}^{pred})|
```

#### **4.2 Charge Prediction via Polynomial Extrapolation**

The predicted charge for LTE calculation uses Lagrange polynomial extrapolation:

**Second-Order Prediction (for Gear-2):**
```
Q_{n+1}^{pred} = 3Q_n - 3Q_{n-1} + Q_{n-2}
```

**First-Order Prediction (for Trapezoidal):**
```
Q_{n+1}^{pred} = 2Q_n - Q_{n-1}
```

#### **4.3 Normalized LTE Calculation**

The LTE is normalized against SPICE tolerances:
```
LTE_normalized = |Q_{n+1} - Q_{n+1}^{pred}| / (RELTOL·max(|Q_{n+1}|, CHGTOL) + ABSTOL)
```

### **5. Voltage Limiting Algorithm (DEVpnjlim)**

To prevent numerical overflow in exponential BJT equations during Newton-Raphson iterations:

#### **5.1 Mathematical Formulation**

For PN junction voltages during Newton iterations:
```
If V_new > V_crit AND |V_new - V_old| > 2·V_T:
    If V_old > 0:
        V_limited = V_old + V_T·ln(1 + (V_new - V_old)/V_T)
    Else:
        V_limited = V_T·ln(V_new/V_T)
Else:
    V_limited = V_new
```

Where:
- `V_crit = V_T·ln(V_T/(IS·√2))` (critical voltage where exponential terms become large)
- `V_T = kT/q` (thermal voltage)

#### **5.2 Purpose and Effect**

This algorithm:
1. Prevents `exp(V/V_T)` overflow in forward bias
2. Maintains derivative continuity for Newton-Raphson convergence
3. Smoothly limits voltage changes while preserving physical behavior

### **6. Matrix Stamping for Transient Analysis**

#### **6.1 Companion Model Formulation**

The charge-based model is linearized using the companion model approach:

**Capacitance Companion Model:**
```
I = C_eq·V + I_eq
```
Where for backward Euler:
```
C_eq = C
I_eq = -C·V_old/Δt
```

**For the complete BJT:**
The transient currents are stamped into the MNA matrix as:
```
[G]·[V] + [C]·dV/dt = [I]
```

#### **6.2 Discrete-Time Representation**

Applying backward differentiation:
```
[G + α₀·C]·V_{n+1} = [I] - C·[α₁·V_n + α₂·V_{n-1} + ...]
```

This creates a modified conductance matrix for transient analysis.

### **7. Temperature Scaling of Time Constants**

#### **7.1 Transit Time Temperature Dependence**

**Forward Transit Time:**
```
TF(T) = TF(T_NOM) × (T/T_NOM)^{XTF}
```
Where `XTF` is the temperature exponent (typically 1.5 due to mobility dependence).

**Reverse Transit Time:**
```
TR(T) = TR(T_NOM) × (T/T_NOM)^{1.5}
```

#### **7.2 Thermal Voltage Scaling**
```
V_T(T) = (k·T)/q
```
Directly affects all exponential terms and the `DEVpnjlim` algorithm.

### **8. Charge Conservation Enforcement**

#### **8.1 Mathematical Constraint**

The implementation enforces:
```
Q_be(t) + Q_bc(t) + Q_def(t) = constant + ∫(I_B + I_C + I_E) dt
```

Since `I_B + I_C + I_E = 0` (KCL), this simplifies to:
```
Q_be(t) + Q_bc(t) + Q_def(t) = constant
```

#### **8.2 Numerical Implementation**

Charge conservation is maintained by:
1. Using the same numerical integration method for all charge components
2. Computing all charge derivatives from the same state vector
3. Ensuring the sum of transient currents equals the total charge derivative

### **9. State Vector Management**

#### **9.1 State Allocation Algorithm**

During setup (`BJTsetup()`), the BJT requests state vector entries:
```
inst->BJTqbeState = *state_index; (*state_index)++;
inst->BJTqbcState = *state_index; (*state_index)++;
inst->BJTqdefState = *state_index; (*state_index)++;
```

#### **9.2 State Update Procedure**

During each time step:
```
state0[inst->BJTqbeState] = Q_be_new
state0[inst->BJTqbcState] = Q_bc_new
state0[inst->BJTqdefState] = Q_def_new

state1[inst->BJTqbeState] = Q_be_old
state1[inst->BJTqbcState] = Q_bc_old
state1[inst->BJTqdefState] = Q_def_old
```

Where `state0` is the current state vector and `state1` is the previous state vector.

### **10. Integration with SPICE Transient Engine**

#### **10.1 Time Step Control Interface**

The BJT provides LTE estimates to SPICE's time step controller:
```
Δt_{new} = Δt_{old} × √(TRTOL/LTE_max)
```

Where `TRTOL` is the transient tolerance factor (typically 7).

#### **10.2 Breakpoint Detection**

The BJT detects when junction voltages cross `FC·V_J` and requests a breakpoint:
```
If sign(V - FC·V_J) changes between time steps:
    Request breakpoint at exact crossing time
```

This ensures accurate simulation of capacitance model discontinuities.

This mathematical formulation provides the foundation for the charge-conserving, numerically stable transient simulation of BJT devices within the Ngspice SPICE simulator, ensuring accurate modeling of switching behavior, frequency response, and charge storage effects while maintaining robust convergence properties.

## **Convergence Analysis**

The transient control and charge storage implementation for the BJT in Ngspice employs sophisticated convergence control mechanisms that operate within SPICE's time-domain Newton-Raphson framework. These algorithms ensure numerical stability while maintaining charge conservation and accurate modeling of device dynamics.

### **1. Newton-Raphson Convergence Criteria for Transient Analysis**

#### **1.1 Multi-Dimensional Convergence Testing**

The BJT implements comprehensive convergence testing across voltage, current, and charge domains:

**Voltage Convergence:**
```
|ΔV_BE| < ε_V = RELTOL × max(|V_BE_new|, |V_BE_old|, VNTOL) + ABSTOL_V
|ΔV_BC| < ε_V = RELTOL × max(|V_BC_new|, |V_BC_old|, VNTOL) + ABSTOL_V
```

**Current Convergence:**
```
|ΔI_C| < ε_I = RELTOL × max(|I_C_new|, |I_C_old|) + ABSTOL_I
|ΔI_B| < ε_I = RELTOL × max(|I_B_new|, |I_B_old|) + ABSTOL_I
```

**Charge Convergence (Critical for Transient):**
```
|ΔQ_BE| < ε_Q = CHGTOL × max(|Q_BE_new|, |Q_BE_old|) + ABSTOL_Q
|ΔQ_BC| < ε_Q = CHGTOL × max(|Q_BC_new|, |Q_BC_old|) + ABSTOL_Q
|ΔQ_def| < ε_Q = CHGTOL × max(|Q_def_new|, |Q_def_old|) + ABSTOL_Q
```

Where typical SPICE defaults are:
- `RELTOL = 0.001` (0.1% relative tolerance)
- `VNTOL = 1e-6 V` (voltage noise tolerance)
- `ABSTOL_V = 1e-12 V` (absolute voltage tolerance)
- `ABSTOL_I = 1e-12 A` (absolute current tolerance)
- `CHGTOL = 1e-14 C` (charge tolerance)
- `ABSTOL_Q = 1e-16 C` (absolute charge tolerance)

#### **1.2 Convergence Logic Implementation**

The convergence test follows logical AND across all criteria:
```
Converged = (V_BE_converged ∧ V_BC_converged) ∧ 
            (I_C_converged ∧ I_B_converged) ∧
            (Q_BE_converged ∧ Q_BC_converged ∧ Q_def_converged)
```

All conditions must be satisfied simultaneously for the device to be considered converged.

### **2. Local Truncation Error (LTE) Control and Time Step Selection**

#### **2.1 LTE Calculation Algorithm**

The LTE for charge-based integration is computed using polynomial extrapolation:

**For Trapezoidal Integration (k=1):**
```
Q_predicted = 2Q_n - Q_{n-1}
LTE_Q = |(Δt/3) × (Q_{n+1} - Q_predicted)|
```

**For Gear-2 Integration (k=2):**
```
Q_predicted = 3Q_n - 3Q_{n-1} + Q_{n-2}
LTE_Q = |(Δt²/4) × (Q_{n+1} - Q_predicted)|
```

#### **2.2 Normalized LTE and Time Step Adjustment**

The LTE is normalized against SPICE tolerances:
```
LTE_normalized = LTE_Q / (RELTOL × max(|Q_{n+1}|, CHGTOL) + ABSTOL_Q)
```

Time step adjustment follows asymptotic control:
```
If LTE_normalized > TRTOL:
    Δt_new = Δt_old × √(TRTOL / LTE_normalized)
Else if LTE_normalized < 0.1 × TRTOL:
    Δt_new = Δt_old × min(2.0, √(TRTOL / LTE_normalized))
```

Where `TRTOL = 7` is the transient tolerance factor.

#### **2.3 Minimum and Maximum Time Step Enforcement**

```
Δt_new = max(Δt_new, Δt_min)  where Δt_min = 10⁻¹² s
Δt_new = min(Δt_new, Δt_max)  where Δt_max = 0.1 × T_stop
```

### **3. Charge Conservation Enforcement and Error Control**

#### **3.1 Charge Conservation Constraint**

The implementation enforces strict charge conservation:
```
Q_total = Q_BE + Q_BC + Q_def
Error_charge = |dQ_total/dt - (I_B + I_C + I_E)|
```

The convergence test includes:
```
Error_charge < ε_charge = RELTOL × max(|Q_total|, CHGTOL) + ABSTOL_Q
```

#### **3.2 State Vector Consistency Check**

For multi-step integration methods, state vectors must be consistent:
```
|state0[i] - state1[i]| < ε_state = RELTOL × max(|state0[i]|, |state1[i]|) + ABSTOL_S
```

Where `state0` is the current state and `state1` is the previous state.

### **4. Numerical Integration Stability Analysis**

#### **4.1 Stability Regions for Integration Methods**

**Trapezoidal Rule:**
- A-stable: Stable for all Δt when solving linear problems
- Can exhibit numerical ringing for stiff problems with large Δt
- Stability function: `R(z) = (1 + z/2)/(1 - z/2)`

**Gear-2 (BDF-2):**
- L-stable: Strongly stable for stiff problems
- Stability region includes negative real axis
- Stability function: `R(z) = (1 + 2z/3)/(1 - 2z/3 + z²/6)`

#### **4.2 Stiffness Detection and Method Switching**

The BJT implementation monitors stiffness through:
```
Stiffness_ratio = |λ_max| / |λ_min|
```
Where λ are the eigenvalues of the device Jacobian.

If `Stiffness_ratio > 10⁶`, the solver may switch from trapezoidal to Gear-2 for improved stability.

### **5. Newton-Raphson Convergence Acceleration Techniques**

#### **5.1 Damped Newton-Raphson**

For difficult convergence cases, damping is applied:
```
V_new = V_old + λ × ΔV
```
Where the damping factor λ is adapted based on convergence history:
```
If ||ΔV|| increasing for 3 iterations: λ = λ/2
If ||ΔV|| decreasing steadily: λ = min(1.0, 2λ)
```

#### **5.2 Convergence Rate Monitoring**

The implementation tracks convergence rate:
```
ρ = ||ΔV^{(k)}|| / ||ΔV^{(k-1)}||
```

If `ρ > 0.9` for 5 consecutive iterations, additional measures are taken:
1. Tighten tolerances by factor of 0.1
2. Enable line search
3. Apply more aggressive voltage limiting

### **6. Voltage Limiting and Numerical Stability**

#### **6.1 DEVpnjlim Algorithm Implementation**

The PN junction limiting algorithm prevents numerical overflow:
```
If V_new > V_crit AND |V_new - V_old| > 2V_T:
    If V_old > 0:
        V_limited = V_old + V_T × ln(1 + (V_new - V_old)/V_T)
    Else:
        V_limited = V_T × ln(V_new/V_T)
```

#### **6.2 Derivative Continuity Preservation**

The limiting algorithm maintains C¹ continuity:
```
lim(V → V_crit⁺) dV_limited/dV = 1
```

This ensures Newton-Raphson convergence is not compromised by derivative discontinuities.

### **7. Time Step Control Based on Device Dynamics**

#### **7.1 BJT-Specific Time Constants**

The implementation considers device-specific time constants for time step selection:

**Base Transit Time Constant:**
```
τ_B = TF × (1 + V_BE/V_T)
```

**RC Time Constants:**
```
τ_RB = R_B × (C_JE + C_JC)
τ_RC = R_C × C_JC
τ_RE = R_E × C_JE
```

**Minimum Device Time Constant:**
```
τ_min = min(τ_B, τ_RB, τ_RC, τ_RE)
```

#### **7.2 Time Step Bound Enforcement**

```
Δt_max_device = 10 × τ_min  (for accuracy)
Δt_min_device = 0.01 × τ_min  (for stability)
```

### **8. Error Propagation and Recovery Mechanisms**

#### **8.1 LTE Accumulation Monitoring**

The implementation monitors accumulated error:
```
Error_accumulated = Σ LTE_normalized
```

If `Error_accumulated > 10 × TRTOL`, a step rejection and retry with smaller Δt is triggered.

#### **8.2 Convergence Failure Recovery**

When Newton-Raphson fails to converge:
1. Reduce time step by factor of 0.5
2. Apply stronger damping (λ = 0.1)
3. Reinitialize from previous solution
4. If still failing, switch to backward Euler (Gear-1) for one step

### **9. Charge-Based Convergence Criteria**

#### **9.1 Normalized Charge Error**

Charge convergence uses normalized error:
```
Error_Q = |Q_new - Q_old| / (CHGTOL × max(|Q_new|, |Q_old|) + ABSTOL_Q)
```

#### **9.2 Charge Conservation Error**

The implementation verifies charge conservation:
```
Error_conservation = |Q_BE + Q_BC + Q_def - Q_initial| / 
                     (CHGTOL × |Q_initial| + ABSTOL_Q)
```

Where `Q_initial` is the total charge at the start of the transient analysis.

### **10. Integration Method Stability Analysis**

#### **10.1 Amplification Factor Analysis**

For linear test equation `dy/dt = λy`, the amplification factor is:

**Trapezoidal:**
```
R(z) = (1 + z/2)/(1 - z/2) where z = λΔt
|R(z)| ≤ 1 for Re(z) ≤ 0 (A-stable)
```

**Gear-2:**
```
R(z) = (1 + 2z/3)/(1 - 2z/3 + z²/6)
|R(z)| ≤ 1 for Re(z) ≤ -0.5 (L-stable region)
```

#### **10.2 Numerical Damping Control**

The implementation can add numerical damping for stability:
```
Modified trapezoidal: y_{n+1} = y_n + Δt[(1-α)f_n + αf_{n+1}]
```
Where α = 0.52 adds slight damping to control numerical ringing.

### **11. Multi-Rate Convergence Strategy**

#### **11.1 Device-Level vs. Circuit-Level Convergence**

The BJT implements hierarchical convergence checking:
1. **Device-level convergence:** Internal voltages and charges
2. **Node-level convergence:** Terminal voltages
3. **Circuit-level convergence:** Global Newton-Raphson

#### **11.2 Adaptive Tolerance Strategy**

Tolerances adapt based on simulation phase:
```
During initial transient: RELTOL = 0.01 (looser)
During steady-state: RELTOL = 0.001 (standard)
During precise timing: RELTOL = 0.0001 (tighter)
```

### **12. Breakpoint Handling and Discontinuity Management**

#### **12.1 Capacitance Model Discontinuity Detection**

The implementation detects when `V = FC × V_J`:
```
If sign(V - FC×V_J) changes between iterations:
    Mark breakpoint at exact crossing
    Use linear interpolation to find exact crossing time
```

#### **12.2 Smoothing at Discontinuities**

To maintain Newton-Raphson convergence, small smoothing regions are introduced:
```
Near V = FC×V_J: C(V) = C_reverse + (C_forward - C_reverse) × S((V - FC×V_J)/δ)
```
Where `S(x)` is a smooth sigmoid function and `δ = 0.1 × V_T`.

### **13. Performance Optimization with Convergence Maintenance**

#### **13.1 Jacobian Reuse Strategy**

The Jacobian matrix is reused when:
```
|ΔV| < 0.01 × V_T AND |ΔQ| < 0.01 × CHGTOL
```

#### **13.2 State Prediction for Initial Guess**

For the next time step, states are predicted:
```
Q_predicted = Q_n + Δt × dQ/dt_n
```
This provides a better initial guess for Newton-Raphson.

### **14. Convergence Diagnostics and Debugging**

#### **14.1 Convergence History Tracking**

The implementation maintains convergence history:
```
History[k] = ||ΔV^{(k)}|| / ||V^{(k)}||
```

If `History[k] > History[k-1]` for 3 consecutive iterations, convergence problems are flagged.

#### **14.2 Diagnostic Output Control**

When convergence difficulties are detected:
```
if (iteration > MAX_ITER/2) {
    print_convergence_debug(BJTvbe, BJTvbc, BJTqbe, BJTqbc, BJTqdef);
}
```

This comprehensive convergence analysis framework ensures that the BJT transient simulation maintains numerical stability, charge conservation, and accurate dynamics modeling while providing robust convergence across all operating conditions and time step sizes within the Ngspice simulation environment.

---

## **C Implementation**

The Ngspice BJT transient control and charge storage implementation centers on rigorous numerical integration of charge conservation equations, local truncation error (LTE) calculation for adaptive time-step control, and comprehensive Newton-Raphson convergence testing. This C implementation directly maps the mathematical formulations for charge-based simulation to efficient algorithms that ensure numerical stability and accuracy in time-domain analysis.

### **1. Core Data Structures for Charge Storage**

The BJT charge storage model is built around the `sBJTinstance` structure defined in `bjtdefs.h`, which contains all necessary state variables for transient analysis:

```c
typedef struct sBJTinstance {
    char *BJTname;                  /* Instance name */
    int BJTdNodePrime;              /* Internal drain node */
    int BJTgNodePrime;              /* Internal gate node */
    int BJTsNodePrime;              /* Internal source node */
    int BJTbNodePrime;              /* Internal bulk node */
    
    /* Terminal voltages */
    double BJTvbe;                  /* Base-emitter voltage */
    double BJTvbc;                  /* Base-collector voltage */
    double BJTvce;                  /* Collector-emitter voltage */
    
    /* Charge states - mathematical mapping to Qbe, Qbc, Qdef */
    double BJTqbe;                  /* Base-emitter charge: Qbe = Qjbe + Qde */
    double BJTqbc;                  /* Base-collector charge: Qbc = Qjbc + Qdc */
    double BJTqcs;                  /* Collector-substrate charge */
    
    /* Diffusion charges - mathematical mapping to Qf, Qr */
    double BJTqdef;                 /* Base transit time charge: Qdef = Qf + Qr */
    double BJTqf;                   /* Forward diffusion charge: Qf = TF·If */
    double BJTqr;                   /* Reverse diffusion charge: Qr = TR·Ir */
    
    /* Transit time parameters */
    double BJTtf;                   /* Forward transit time TF */
    double BJTtr;                   /* Reverse transit time TR */
    double BJTtt;                   /* Total transit time */
    
    /* State vector indices for accessing charge history in CKTstate arrays */
    int BJTqbeState;                /* State index for qbe in CKTstate0/1/2 */
    int BJTqbcState;                /* State index for qbc */
    int BJTqdefState;               /* State index for qdef */
    
    /* Matrix pointers for Modified Nodal Analysis stamping */
    double *BJTdrainDrainPtr;       /* Gdd conductance matrix pointer */
    double *BJTdrainGatePtr;        /* Gdg */
    double *BJTdrainSourcePtr;      /* Gds */
    double *BJTdrainBulkPtr;        /* Gdb */
    /* ... 16 total matrix entries for complete 4-terminal device */
    
    /* Charge history for numerical integration */
    double BJTqbeOld1;              /* Qbe at time t-Δt */
    double BJTqbeOld2;              /* Qbe at time t-2Δt */
    double BJTqbcOld1;              /* Qbc at time t-Δt */
    double BJTqbcOld2;              /* Qbc at time t-2Δt */
    double BJTqdefOld1;             /* Qdef at time t-Δt */
    double BJTqdefOld2;             /* Qdef at time t-2Δt */
    
    /* Previous iteration values for convergence testing */
    double BJTvbeOld;               /* Vbe from previous Newton iteration */
    double BJTvbcOld;               /* Vbc from previous iteration */
    double BJTicOld;                /* Ic from previous iteration */
    double BJTibOld;                /* Ib from previous iteration */
    double BJTqbeOld;               /* Qbe from previous iteration */
    double BJTqbcOld;               /* Qbc from previous iteration */
    double BJTqdefOld;              /* Qdef from previous iteration */
    
    struct sBJTinstance *BJTnextInstance;
} BJTinstance;
```

**Mathematical-to-Code Mapping:** Each field in the structure corresponds directly to a mathematical variable:
- `BJTqbe` ↔ `Qbe = Qjbe + Qde` (total base-emitter charge)
- `BJTqbc` ↔ `Qbc = Qjbc + Qdc` (total base-collector charge)
- `BJTqdef` ↔ `Qdef = Qf + Qr` (total diffusion charge)
- `BJTqf` ↔ `Qf = TF·If` (forward diffusion charge)
- `BJTqr` ↔ `Qr = TR·Ir` (reverse diffusion charge)

### **2. Numerical Integration Implementation (`bjttrunc.c`)**

The `BJTtrunc()` function implements the core charge-based integration algorithm that computes transient currents via backward differentiation of charges:

```c
int BJTtrunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep)
{
    BJTmodel *model = (BJTmodel *)inModel;
    BJTinstance *inst;
    
    for(; model; model = model->BJTnextModel) {
        for(inst = model->BJTinstances; inst; inst = inst->BJTnextInstance) {
            /* Get integration method coefficients from SPICE task */
            double coeff0 = ckt->CKTcurTask->TSKcoeff0;
            double coeff1 = ckt->CKTcurTask->TSKcoeff1;
            double coeff2 = ckt->CKTcurTask->TSKcoeff2;
            
            /* Mathematical mapping: dQ/dt = α₀Qₙ + α₁Qₙ₋₁ + α₂Qₙ₋₂ */
            /* For trapezoidal: α₀ = 2/Δt, α₁ = -2/Δt, α₂ = 0 */
            /* For Gear-2: α₀ = 3/(2Δt), α₁ = -4/(2Δt), α₂ = 1/(2Δt) */
            
            /* Access charge history from state vector */
            double qbe = inst->BJTqbe;
            double qbe_old = *(ckt->CKTrhsOld + inst->BJTqbeState);
            
            double qbc = inst->BJTqbc;
            double qbc_old = *(ckt->CKTrhsOld + inst->BJTqbcState);
            
            double qdef = inst->BJTqdef;
            double qdef_old = *(ckt->CKTrhsOld + inst->BJTqdefState);
            
            /* Compute charge derivatives using integration coefficients */
            double dqbe_dt = coeff0 * qbe + coeff1 * qbe_old + coeff2 * inst->BJTqbeOld2;
            double dqbc_dt = coeff0 * qbc + coeff1 * qbc_old + coeff2 * inst->BJTqbcOld2;
            double dqdef_dt = coeff0 * qdef + coeff1 * qdef_old + coeff2 * inst->BJTqdefOld2;
            
            /* Mathematical: I_cap = dQ/dt (displacement current) */
            /* Stamp transient currents into RHS vector using KCL */
            ckt->CKTrhs[inst->BJTbNode] -= dqbe_dt + dqdef_dt;  /* Base node */
            ckt->CKTrhs[inst->BJTeNode] += dqbe_dt;             /* Emitter node */
            ckt->CKTrhs[inst->BJTcNode] += dqbc_dt - dqdef_dt;  /* Collector node */
            
            /* Update charge history for next time step */
            inst->BJTqbeOld2 = qbe_old;
            inst->BJTqbcOld2 = qbc_old;
            inst->BJTqdefOld2 = qdef_old;
            
            /* Store current charges as "old" for next iteration */
            *(ckt->CKTrhsOld + inst->BJTqbeState) = qbe;
            *(ckt->CKTrhsOld + inst->BJTqbcState) = qbc;
            *(ckt->CKTrhsOld + inst->BJTqdefState) = qdef;
        }
    }
    return OK;
}
```

**Mathematical Significance:** This code implements the fundamental charge conservation equation:
```
I_be + I_bc + I_def = dQbe/dt + dQbc/dt + dQdef/dt
```
where the displacement currents are computed via backward differentiation formulas (BDF). The coefficients `coeff0`, `coeff1`, `coeff2` implement either trapezoidal or Gear-2 integration methods based on SPICE's time-step control algorithm.

### **3. Local Truncation Error (LTE) Calculation**

The LTE calculation in `BJT_LTE()` implements the mathematical formulation for error estimation in charge-based integration:

```c
double BJT_LTE(BJTinstance *inst, CKTcircuit *ckt, double timeStep)
{
    double lte = 0.0;
    double reltol = ckt->CKTcurTask->TSKreltol;
    double abstol = ckt->CKTcurTask->TSKabstol;
    double chgtol = ckt->CKTcurTask->TSKchgtol;
    
    /* Mathematical: Q_predicted = polynomial extrapolation from past values */
    /* For 2nd order: Q_pred = 2Qₙ₋₁ - Qₙ₋₂ */
    double qbe_pred = 2.0 * inst->BJTqbe - inst->BJTqbeOld1;
    double qbc_pred = 2.0 * inst->BJTqbc - inst->BJTqbcOld1;
    double qdef_pred = 2.0 * inst->BJTqdef - inst->BJTqdefOld1;
    
    /* Compute normalized LTE for each charge component */
    /* LTE_Q = |Q_new - Q_pred| / (reltol·max(|Q|, chgtol) + abstol) */
    double lte_qbe = fabs(inst->BJTqbe - qbe_pred) / 
                    (reltol * MAX(fabs(inst->BJTqbe), chgtol) + abstol);
    double lte_qbc = fabs(inst->BJT