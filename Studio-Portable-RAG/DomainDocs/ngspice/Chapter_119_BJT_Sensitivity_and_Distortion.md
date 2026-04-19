# BJT: Sensitivity and Harmonic Distortion Analysis

_Generated 2026-04-12 18:09 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtdisto.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtdset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtdset.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtsload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtsset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtsacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtsupd.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtsprt.c`

# **Chapter: BJT: Sensitivity and Harmonic Distortion Analysis**

## **Introduction**

This chapter details the implementation of advanced circuit analysis features for the Bipolar Junction Transistor (BJT) within the Ngspice simulator, specifically focusing on parameter sensitivity and harmonic distortion. These analyses are critical for design optimization, yield prediction, and linearity assessment in analog and RF circuits. The implementation is distributed across several specialized C source files that extend the core Gummel-Poon model:

*   **`bjtsload.c`**: Implements the sensitivity load function (`BJTsLoad`). This function computes the contributions of the BJT to the circuit's sensitivity matrix using the adjoint method. It calculates derivatives of the device's conductance matrix and current sources with respect to model parameters (e.g., `IS`, `BF`, `VAF`) and stamps them into the sensitivity system of equations.
*   **`bjtdisto.c`**: Contains the distortion analysis function (`BJTdisto`). It performs a Volterra-series-based analysis by evaluating higher-order derivatives (second and third) of the BJT's current-voltage characteristics. These nonlinear coefficients are used to predict harmonic distortion (HD2, HD3) and intermodulation distortion (IMD3) for small-signal excitations.
*   **`bjtsupd.c`**: Handles the sensitivity update function (`BJTsUpdate`). This routine updates the sensitivity-related quantities in the device's instance structure after a successful Newton-Raphson iteration, ensuring consistency between the operating point and the computed parameter derivatives.
*   **`bjtsprt.c`**: Manages the sensitivity print function (`BJTsPrint`). It formats and outputs the results of sensitivity analysis (normalized and absolute sensitivities) to the simulation output file or console in a human-readable format.
*   **`bjtsacl.c`**: Implements the sensitivity AC load function (`BJTsAcLoad`). This extends sensitivity analysis to the frequency domain, computing the complex derivatives of the device's `Y`-parameters with respect to model parameters for `.AC` and `.SENS` analyses.
*   **`bjtdset.h` & `bjtdset.c`**: Define and implement the data structures and setup routines for distortion analysis. `bjtdset.h` declares the `DISTO` structure and associated macros for storing nonlinear coefficients, while `bjtdset.c` contains setup functions that allocate and initialize these structures within the circuit's state.
*   **`bjtsset.c`**: Provides the sensitivity setup function (`BJTsSetup`). This function initializes the data structures and state vector indices required for sensitivity analysis, allocating memory for storing sensitivity vectors and adjoint variables for each parameter of interest.

Together, these files form a sophisticated analytical layer on top of the BJT's DC and AC models. They enable Ngspice to answer critical design questions: "How much will the gain change if the transistor's beta varies by 10%?" or "What is the third-harmonic distortion of this amplifier at 1 kHz?" The following sections present the rigorous mathematical formulation underpinning these analyses, followed by a detailed exposition of the corresponding C implementation that brings this mathematics to life within the simulator.

## **Mathematical Formulation**

The sensitivity and harmonic distortion analysis for the BJT Gummel-Poon model in Ngspice extends the DC and small-signal formulations to compute parameter sensitivities via the adjoint method and predict nonlinear distortion through Volterra series analysis. These mathematical frameworks integrate directly with SPICE's sensitivity and distortion analysis modes, providing critical insights for circuit optimization and linearity assessment.

### **1. Sensitivity Analysis via Adjoint Method**

#### **1.1 Sensitivity Definition and Circuit Equation**

The sensitivity of a circuit response `R` (voltage or current) to a parameter `p` is defined as:
```
S_p^R = ∂R/∂p
```

For the Modified Nodal Analysis (MNA) system `G·x = b`, where `G` is the conductance matrix, `x` is the node voltage vector, and `b` is the source vector, the sensitivity is computed using the adjoint method:

**Forward System:**
```
G·x = b
```

**Adjoint System:**
```
Gᵀ·λ = ∂R/∂x
```

**Sensitivity Computation:**
```
∂R/∂p = λᵀ·(∂b/∂p - ∂G/∂p·x)
```

#### **1.2 BJT-Specific Sensitivity Contributions**

For the BJT, the sensitivity contributions come from the device's conductance matrix and current source entries:

**Parameter Sensitivities of Conductance Matrix Elements:**
```
∂g_m/∂IS = (1/(NF·V_T))·exp(V_BE/(NF·V_T))/q_B - I_C·(∂q_B/∂IS)/(q_B²)
∂g_π/∂IS = (1/(NF·V_T))·exp(V_BE/(NF·V_T)) + (ISE/(NE·V_T))·(∂/∂IS)[exp(V_BE/(NE·V_T))]
∂g_μ/∂IS = (1/(NR·V_T))·exp(V_BC/(NR·V_T)) + (ISC/(NC·V_T))·(∂/∂IS)[exp(V_BC/(NC·V_T))]
```

**Base Charge Factor Sensitivity:**
```
∂q_B/∂IS = (∂q₁/∂IS)·(1 + (q₁ + 2·q₂)/√(q₁² + 4·q₂)) / 2
```
where:
```
∂q₁/∂IS = 0 (q₁ independent of IS)
∂q₂/∂IS = (1/IKF)·[exp(V_BE/(NF·V_T)) - 1] + (1/IKR)·[exp(V_BC/(NR·V_T)) - 1]
```

#### **1.3 Early Voltage Sensitivities**

The Early voltage parameters `V_AF` and `V_AR` affect the output conductance:

```
∂g_o/∂V_AF = -I_C/(V_AF²·q_B) + (I_C/(V_AF·q_B²))·(∂q_B/∂V_AF)
∂q_B/∂V_AF = (q_B/q₁²)·(V_BC/V_AF²)·(1 + q₁/√(q₁² + 4·q₂)) / 2
```

#### **1.4 Resistance Parameter Sensitivities**

For series resistances `R_B`, `R_C`, `R_E`:

```
∂G_BB/∂R_B = -1/R_B²  (diagonal element)
∂G_BB'/∂R_B = 1/R_B²  (coupling element)
∂G_B'B'/∂R_B = -1/R_B² (internal node)
```

where `B'` is the internal base node after `R_B`.

#### **1.5 Capacitance Parameter Sensitivities**

For junction capacitance parameters:

**Zero-Bias Capacitance `C_JE`:**
```
∂C_JE/∂C_JE0 = (1 - V_BE/V_JE)^(-M_JE)  for V_BE < FC·V_JE
∂C_JE/∂C_JE0 = (1 - FC)^(-M_JE-1)·[1 - FC·(1+M_JE) + M_JE·V_BE/V_JE] for V_BE ≥ FC·V_JE
```

**Built-in Potential `V_JE`:**
```
∂C_JE/∂V_JE = C_JE0·M_JE·V_BE/(V_JE²)·(1 - V_BE/V_JE)^(-M_JE-1) for V_BE < FC·V_JE
```

### **2. Harmonic Distortion Analysis via Volterra Series**

#### **2.1 Nonlinear Current-Voltage Expansion**

The BJT collector current `I_C` as a function of base-emitter and base-collector voltages is expanded in a multivariate Taylor series around the DC operating point `(V_BE0, V_BC0)`:

```
I_C(V_BE, V_BC) = I_C0 + g_m·ΔV_BE + g_μ·ΔV_BC
                + (1/2)·[g_m2·ΔV_BE² + 2·g_mμ·ΔV_BEΔV_BC + g_μ2·ΔV_BC²]
                + (1/6)·[g_m3·ΔV_BE³ + 3·g_m2μ·ΔV_BE²ΔV_BC
                        + 3·g_mμ2·ΔV_BEΔV_BC² + g_μ3·ΔV_BC³] + ...
```

where:
- `ΔV_BE = V_BE - V_BE0`, `ΔV_BC = V_BC - V_BC0`
- `g_m = ∂I_C/∂V_BE` (transconductance)
- `g_μ = ∂I_C/∂V_BC` (feedback conductance)
- `g_m2 = ∂²I_C/∂V_BE²`, `g_mμ = ∂²I_C/∂V_BE∂V_BC`, `g_μ2 = ∂²I_C/∂V_BC²`
- `g_m3 = ∂³I_C/∂V_BE³`, `g_m2μ = ∂³I_C/∂V_BE²∂V_BC`, etc.

#### **2.2 Gummel-Poon-Specific Nonlinear Coefficients**

From the Gummel-Poon transport equation `I_C = (I_S/q_B)·[exp(V_BE/(NF·V_T)) - exp(V_BC/(NR·V_T))]`:

**First-Order Coefficients:**
```
g_m = (I_S/(NF·V_T))·exp(V_BE/(NF·V_T))/q_B - (I_C/q_B)·(∂q_B/∂V_BE)
g_μ = -(I_S/(NR·V_T))·exp(V_BC/(NR·V_T))/q_B - (I_C/q_B)·(∂q_B/∂V_BC)
```

**Second-Order Coefficients:**
```
g_m2 = g_m/(NF·V_T) - (2/q_B)·g_m·(∂q_B/∂V_BE) - (I_C/q_B)·(∂²q_B/∂V_BE²)
g_mμ = -(I_C/q_B)·(∂²q_B/∂V_BE∂V_BC) - (1/q_B)·[g_m·(∂q_B/∂V_BC) + g_μ·(∂q_B/∂V_BE)]
g_μ2 = -g_μ/(NR·V_T) - (2/q_B)·g_μ·(∂q_B/∂V_BC) - (I_C/q_B)·(∂²q_B/∂V_BC²)
```

**Third-Order Coefficients:**
```
g_m3 = g_m2/(NF·V_T) - (3/q_B)·g_m2·(∂q_B/∂V_BE) - (3/q_B)·g_m·(∂²q_B/∂V_BE²)
      - (I_C/q_B)·(∂³q_B/∂V_BE³)
```

#### **2.3 Base Charge Factor Derivatives**

The normalized base charge `q_B` derivatives are critical for distortion prediction:

```
q_B = (q₁/2)·[1 + √(1 + 4·q₂)]
q₁ = 1/(1 - V_BC/V_AF - V_BE/V_AR)
q₂ = (I_S/I_KF)·[exp(V_BE/(NF·V_T)) - 1] + (I_S/I_KR)·[exp(V_BC/(NR·V_T)) - 1]
```

**First Derivatives:**
```
∂q_B/∂V_BE = (q_B/q₁²)·(1/V_AR)·[1 + q₁/√(q₁² + 4·q₂)]/2
           + (I_S/(I_KF·V_T·NF))·exp(V_BE/(NF·V_T))/√(q₁² + 4·q₂)
```

**Second Derivatives:**
```
∂²q_B/∂V_BE² = (∂q_B/∂V_BE)·(2/q₁)·(∂q₁/∂V_BE) - (q_B/q₁³)·(∂q₁/∂V_BE)²
             + (q_B/q₁²)·(∂²q₁/∂V_BE²) + (I_S/(I_KF·V_T²·NF²))·exp(V_BE/(NF·V_T))/√(q₁² + 4·q₂)
             - (I_S²/(I_KF²·V_T²·NF²))·exp(2V_BE/(NF·V_T))/(q₁² + 4·q₂)^{3/2}
```

#### **2.4 Harmonic Generation Formulation**

For a single-tone input `v_in(t) = A·cos(ωt)`, the nonlinearities generate harmonics:

**Second Harmonic Distortion (HD2):**
```
HD2 = (1/4)·(g_m2/g_m)·A
```

**Third Harmonic Distortion (HD3):**
```
HD3 = (1/24)·(g_m3/g_m)·A²
```

**Intermodulation Distortion (IMD3):**
For two-tone input `v_in(t) = A·[cos(ω₁t) + cos(ω₂t)]`:
```
IMD3 = (3/4)·(g_m3/g_m)·A²
```

#### **2.5 Capacitive Nonlinearities**

The junction capacitances also contribute to distortion:

**Base-Emitter Capacitance Nonlinearity:**
```
C_JE(V) = C_JE0·(1 - V/V_JE)^(-M_JE)
```

Expanding around `V_0`:
```
C_JE(V) = C_0 + C_1·ΔV + C_2·ΔV² + C_3·ΔV³ + ...
```
where:
```
C_0 = C_JE0·(1 - V_0/V_JE)^(-M_JE)
C_1 = C_0·M_JE/(V_JE - V_0)
C_2 = C_1·(M_JE + 1)/(2·(V_JE - V_0))
C_3 = C_2·(M_JE + 2)/(3·(V_JE - V_0))
```

### **3. Temperature-Dependent Sensitivities**

#### **3.1 Temperature Scaling Sensitivities**

The sensitivity of parameters to temperature changes:

**Saturation Current Temperature Sensitivity:**
```
∂I_S/∂T = I_S·[X_TI/T + (E_G/(q·V_T))·(1/T - 1/T_NOM)/V_T]
```

**Transconductance Temperature Sensitivity:**
```
∂g_m/∂T = g_m·[1/T - (1/V_T)·∂V_T/∂T - (1/q_B)·∂q_B/∂T]
```
where `∂V_T/∂T = k/q` (constant).

#### **3.2 Beta Temperature Sensitivity**

```
∂β_F/∂T = β_F·X_TB/T
```

### **4. Noise Parameter Sensitivities**

#### **4.1 Shot Noise Sensitivity**

**Collector Current Shot Noise Sensitivity:**
```
∂S_IC/∂I_C = 2q
∂S_IC/∂T = 0 (temperature independent)
```

**Base Current Shot Noise Sensitivity:**
```
∂S_IB/∂I_B = 2q + KF·AF·|I_B|^(AF-1)/f^EF
```

#### **4.2 Flicker Noise Parameter Sensitivities**

```
∂S_flicker/∂KF = |I_B|^AF/f^EF
∂S_flicker/∂AF = KF·|I_B|^AF·ln|I_B|/f^EF
∂S_flicker/∂EF = -KF·|I_B|^AF·ln f/f^(EF+1)
```

#### **4.3 Thermal Noise Sensitivities**

```
∂S_R/∂R = 4kT
∂S_R/∂T = 4kR
```

### **5. Sensitivity Matrix Formulation**

#### **5.1 Complete Sensitivity Matrix for BJT**

The BJT contributes to the circuit sensitivity matrix as:

```
[S] = [∂I_C/∂p₁  ∂I_C/∂p₂  ...  ∂I_C/∂p_N]
      [∂I_B/∂p₁  ∂I_B/∂p₂  ...  ∂I_B/∂p_N]
      [∂I_E/∂p₁  ∂I_E/∂p₂  ...  ∂I_E/∂p_N]
```

where `p₁, p₂, ..., p_N` are the BJT parameters: `I_S, β_F, β_R, V_AF, V_AR, I_KF, I_KR, R_B, R_C, R_E, C_JE, C_JC, ...`

#### **5.2 Normalized Sensitivities**

For circuit optimization, normalized sensitivities are often more useful:

```
S_{p}^{R} = (p/R)·(∂R/∂p)
```

For example:
```
S_{I_S}^{I_C} = (I_S/I_C)·(∂I_C/∂I_S) ≈ 1 (for forward-active operation)
S_{β_F}^{I_C} = (β_F/I_C)·(∂I_C/∂β_F) ≈ 0 (I_C relatively independent of β_F)
S_{V_AF}^{g_o} = (V_AF/g_o)·(∂g_o/∂V_AF) ≈ -1
```

### **6. Distortion Analysis with Early Effect**

#### **6.1 Output Conductance Nonlinearity**

The Early effect introduces output conductance nonlinearity:

```
g_o(V_CE) = I_C/(V_AF + V_CE)  (simplified model)
```

Expanding around `V_CE0`:
```
g_o(V_CE) = g_o0 + g_o1·ΔV_CE + g_o2·ΔV_CE² + ...
```
where:
```
g_o0 = I_C0/(V_AF + V_CE0)
g_o1 = -I_C0/(V_AF + V_CE0)²
g_o2 = I_C0/(V_AF + V_CE0)³
```

#### **6.2 Harmonic Distortion due to Early Effect**

The output conductance nonlinearity generates voltage-dependent load currents:

```
I_out = g_o(V_CE)·V_CE ≈ g_o0·V_CE + g_o1·V_CE² + g_o2·V_CE³
```

For a voltage swing `ΔV_CE = A·cos(ωt)`:
```
HD2_Early = (1/4)·(g_o1/g_o0)·A
HD3_Early = (1/24)·(g_o2/g_o0)·A²
```

### **7. Cross-Term Sensitivities**

#### **7.1 Parameter Correlation Sensitivities**

Some parameters have correlated effects. For example, `I_S` and `β_F` often track together in process variations:

```
∂²I_C/(∂I_S∂β_F) = (1/(β_F·q_B))·exp(V_BE/(NF·V_T)) - (I_C/(β_F·q_B²))·(∂q_B/∂I_S)
```

#### **7.2 Mismatch Sensitivity Analysis**

For differential pairs, mismatch sensitivities are critical:

```
ΔI_C = (∂I_C/∂I_S)·ΔI_S + (∂I_C/∂β_F)·Δβ_F + (∂I_C/∂V_AF)·ΔV_AF + ...
```

The offset voltage due to parameter mismatches:
```
V_os = ΔI_C/g_m
```

### **8. Frequency-Dependent Sensitivities**

#### **8.1 AC Sensitivity Formulation**

At frequency `ω`, the sensitivities become complex:

```
S_p^{Y(ω)} = ∂Y(ω)/∂p = ∂G/∂p + jω·∂C/∂p
```

where `Y(ω) = G + jωC` is the complex admittance.

#### **8.2 Capacitance Parameter Sensitivities at High Frequency**

```
∂|Y(ω)|/∂C_JE = ω/√(G² + ω²C²)·(∂C/∂C_JE)
∂∠Y(ω)/∂C_JE = -ω·G/(G² + ω²C²)·(∂C/∂C_JE)
```

### **9. Sensitivity to Operating Point**

#### **9.1 Bias-Dependent Sensitivities**

The sensitivities vary with the DC operating point:

```
∂g_m/∂V_BE = g_m/(NF·V_T) - (1/q_B)·g_m·(∂q_B/∂V_BE) - (I_C/q_B)·(∂²q_B/∂V_BE²)
```

#### **9.2 Region-Specific Sensitivities**

**Forward-Active Region (V_BE > 0, V_BC < 0):**
- `S_{I_S}^{I_C} ≈ 1`
- `S_{β_F}^{I_C} ≈ 0`
- `S_{V_AF}^{I_C} ≈ -V_BC/V_AF²`

**Saturation Region (V_BE > 0, V_BC > 0):**
- `S_{I_S}^{I_C} ≈ 1/q_B` (reduced sensitivity)
- `S_{β_F}^{I_C}` becomes significant
- `S_{V_AF}^{I_C}` and `S_{V_AR}^{I_C}` both contribute

### **10. Practical Sensitivity Computation**

#### **10.1 Finite Difference Approximation**

For parameters without analytic derivatives, finite differences are used:

```
∂R/∂p ≈ [R(p + Δp) - R(p - Δp)]/(2Δp)
```

#### **10.2 Normalization for Comparison**

Sensitivities are normalized for meaningful comparison:

```
Normalized Sensitivity = (p/R)·(∂R/∂p) × 100%  (percent change per percent change)
```

This comprehensive mathematical formulation provides the foundation for sensitivity analysis and harmonic distortion prediction in BJT circuits within Ngspice, enabling circuit designers to optimize performance, understand manufacturing tolerances, and predict linearity limitations.

## **Convergence Analysis**

The sensitivity and harmonic distortion analysis for the BJT in Ngspice requires specialized convergence control mechanisms that operate within SPICE's adjoint method framework for sensitivity computation and Volterra series analysis for distortion prediction. These algorithms ensure numerical stability while computing parameter derivatives and nonlinear coefficients.

### **1. Adjoint Method Convergence for Sensitivity Analysis**

#### **1.1 Adjoint System Solution Convergence**

The adjoint system `Gᵀ·λ = ∂R/∂x` must be solved with the same convergence criteria as the forward system:

**Adjoint Variable Convergence:**
```
|λ_new - λ_old| < ε_λ = RELTOL·max(|λ_new|, |λ_old|) + ABSTOL_λ
```

**Gradient Convergence:**
```
|∇R_new - ∇R_old| < ε_∇ = RELTOL·max(|∇R_new|, |∇R_old|) + ABSTOL_∇
```

Where `∇R = ∂R/∂p` is the sensitivity gradient being computed.

#### **1.2 Sensitivity Error Estimation**

The sensitivity computation error is bounded by:

```
Error_S ≤ ||λ||·(||ΔG||·||x|| + ||Δb||) + ||Δλ||·(||G||·||x|| + ||b||)
```

where `ΔG`, `Δb`, `Δλ` are errors in the matrix, source vector, and adjoint solution respectively.

#### **1.3 Convergence Acceleration for Adjoint Solution**

Since the adjoint system uses the transposed conductance matrix `Gᵀ`, convergence can be accelerated using:

**Reusing LU Factorization:**
```
Factorize G = L·U for forward system
Solve G·x = b using L·U
Solve Gᵀ·λ = ∂R/∂x using Uᵀ·Lᵀ (same factorization)
```

**Iterative Refinement:**
```
For k = 1 to max_iter:
    r = ∂R/∂x - Gᵀ·λ_k
    Solve G·Δλ = r  (using existing factorization)
    λ_{k+1} = λ_k + Δλ
    If ||r|| < ε: break
```

### **2. Nonlinear Coefficient Computation Convergence**

#### **2.1 Taylor Series Coefficient Convergence**

The Taylor series coefficients must converge as higher-order terms are included:

**Coefficient Convergence Test:**
```
|g_{n+1}·ΔV^{n+1}| < ε_coeff·|g_n·ΔV^n|
```

where typical `ε_coeff = 10⁻⁶` ensures the series has converged.

#### **2.2 Derivative Computation via Finite Differences**

When analytic derivatives are unavailable, finite differences are used with error control:

**Optimal Step Size Selection:**
```
Δp_opt = √(ε_machine)·|p|  for central differences
```
where `ε_machine ≈ 10⁻¹⁶` for double precision.

**Error Estimation for Finite Differences:**
```
Error_fd ≈ (Δp²/6)·|∂³R/∂p³|·|p|
```

The step size is adjusted to balance truncation error and round-off error.

#### **2.3 Higher-Order Derivative Regularization**

To prevent numerical instability in higher-order derivatives:

**Regularized Third Derivative:**
```
g_3_regularized = (g_3_raw + α·g_1)/(1 + α)
```
where `α = 10⁻⁶` adds slight regularization while preserving accuracy.

### **3. Harmonic Balance Convergence for Distortion Analysis**

#### **3.1 Multi-Tone Harmonic Balance Formulation**

For distortion analysis with `M` tones, the harmonic balance system becomes:

```
Y(ω)·X(ω) + Γ·F(X) = B(ω)
```

where:
- `X(ω)` is the frequency-domain solution vector
- `F(X)` is the nonlinear function in frequency domain
- `Γ` is the DFT matrix
- `B(ω)` is the source vector

#### **3.2 Convergence Criteria for Harmonic Balance**

**Frequency-Domain Convergence:**
```
||Y(ω)·X_k(ω) + Γ·F(X_k) - B(ω)|| < ε_HB
```

**Inter-Frequency Coupling Convergence:**
```
|X_{k+1}(mω) - X_k(mω)| < ε_freq·max(|X(mω)|) for m = 1, 2, 3, ...
```

#### **3.3 Damping for Harmonic Balance Newton**

To improve convergence in harmonic balance:

**Frequency-Selective Damping:**
```
ΔX_{k+1}(mω) = λ_m·ΔX_k(mω) + (1 - λ_m)·ΔX_{k-1}(mω)
```
where `λ_m = 1/(1 + m·α)` with `α = 0.1` provides more damping at higher harmonics.

### **4. Volterra Series Convergence Analysis**

#### **4.1 Convergence Radius Estimation**

The Volterra series converges if:
```
||H_n||·||x||^n → 0 as n → ∞
```

For the BJT, the convergence radius is approximately:
```
R_conv ≈ min(NF·V_T, NR·V_T)
```
beyond which the exponential nonlinearities dominate.

#### **4.2 Truncation Error Estimation**

The error after truncating at order `N` is bounded by:

```
Error_N ≤ ∑_{k=N+1}^∞ ||H_k||·||x||^k
```

For the BJT exponential nonlinearity:
```
||H_k|| ≈ 1/(k!·(NF·V_T)^k)
Error_N ≤ exp(||x||/(NF·V_T)) - ∑_{k=0}^N ||x||^k/(k!·(NF·V_T)^k)
```

#### **4.3 Practical Convergence Test**

In implementation, convergence is tested by:
```
If |H_{N+1}·x^{N+1}| < ε_volterra·|H_N·x^N|: series converged
```
where `ε_volterra = 10⁻⁴` typically.

### **5. Parameter Space Exploration Convergence**

#### **5.1 Multi-Parameter Sensitivity Convergence**

When computing sensitivities for multiple parameters simultaneously:

**Jacobian Matrix Condition Number Monitoring:**
```
κ(J) = ||J||·||J⁻¹|| where J_ij = ∂R_i/∂p_j
```

If `κ(J) > 10⁸`, the sensitivity computation becomes ill-conditioned and requires regularization.

#### **5.2 Regularized Sensitivity Computation**

For ill-conditioned systems, Tikhonov regularization is applied:

```
(Jᵀ·J + αI)·Δp = Jᵀ·ΔR
```

where `α = 10⁻⁶·max(diag(Jᵀ·J))` provides stabilization.

### **6. Distortion Metric Convergence**

#### **6.1 Harmonic Distortion Ratio Convergence**

The harmonic distortion ratios must converge as analysis order increases:

**HD2 Convergence:**
```
|HD2^{(N)} - HD2^{(N-1)}| < ε_HD·HD2^{(N)}
```

**HD3 Convergence:**
```
|HD3^{(N)} - HD3^{(N-1)}| < ε_HD·HD3^{(N)}
```

where `ε_HD = 0.01` (1% relative error).

#### **6.2 Intermodulation Distortion Convergence**

For two-tone analysis, IMD convergence requires:

**IMD3 Convergence Test:**
```
|IMD3(ω₁ ± ω₂) - IMD3_previous| < ε_IMD·max(|IMD3|)
```

**Spectral Regrowth Convergence:**
```
|X(2ω₁ - ω₂) - X_previous(2ω₁ - ω₂)| < ε_spec·max(|X(ω₁)|, |X(ω₂)|)
```

### **7. Temperature-Dependent Convergence**

#### **7.1 Temperature Derivative Convergence**

Sensitivities to temperature require special handling:

**Temperature Step Size Control:**
```
ΔT_opt = √(ε_machine)·T  (for finite differences)
```

**Convergence Test for ∂/∂T:**
```
|∂R/∂T_{new} - ∂R/∂T_{old}| < ε_temp·max(|∂R/∂T|, |R/T|)
```

#### **7.2 Self-Heating Convergence**

When self-heating effects are included:

**Thermal-Electrical Coupling Convergence:**
```
|T_{k+1} - T_k| < ε_T = 0.1 K
|I_C(T_{k+1}) - I_C(T_k)| < ε_I·max(|I_C|)
```

### **8. Statistical Sensitivity Convergence**

#### **8.1 Monte Carlo Convergence**

For statistical sensitivity analysis via Monte Carlo:

**Mean Convergence:**
```
|μ_N - μ_{N-1}| < ε_stat/√N
```
where `ε_stat = 0.01·σ` (1% of standard deviation).

**Variance Convergence:**
```
|σ_N² - σ_{N-1}²| < ε_stat²
```

#### **8.2 Correlation Convergence**

Parameter correlation coefficients must converge:

```
|ρ_{ij}^{(N)} - ρ_{ij}^{(N-1)}| < ε_ρ·(1 - |ρ_{ij}|)
```
where `ε_ρ = 0.01`.

### **9. Frequency-Domain Convergence**

#### **9.1 Sensitivity Frequency Response Convergence**

The sensitivity frequency response `S_p^{Y(ω)}` must converge across frequency:

**Magnitude Convergence:**
```
|S(ω)_{new} - S(ω)_{old}| < ε_S·max(|S(ω)|, 1)
```

**Phase Convergence:**
```
∠S(ω)_{new} - ∠S(ω)_{old} (mod 2π) < ε_phase = 0.01 rad
```

#### **9.2 Distortion Frequency Response Convergence**

Harmonic distortion varies with frequency:

**HD2(f) Convergence:**
```
|HD2(f)_{new} - HD2(f)_{old}| < ε_HDf·HD2(f)
```

**IMD3(f₁, f₂) Convergence:**
```
|IMD3(f₁, f₂)_{new} - IMD3(f₁, f₂)_{old}| < ε_IMDf·IMD3(f₁, f₂)
```

### **10. Implementation-Specific Convergence Controls**

#### **10.1 Memory Management for Sensitivity Vectors**

Sensitivity vectors require careful memory management:

**Vector Allocation Convergence:**
```
If ||Δp|| < ε_alloc·||p||: freeze sensitivity vector allocation
```

**Update Frequency Control:**
```
If ||Δx||/||x|| < 10⁻³: update sensitivities every 3 iterations
If ||Δx||/||x|| > 10⁻¹: update sensitivities every iteration
```

#### **10.2 Convergence Diagnostics**

For debugging convergence issues:

**Sensitivity Convergence History:**
```
History[k] = ||∂R/∂p^{(k)} - ∂R/∂p^{(k-1)}||/||∂R/∂p^{(k)}||
```

If `History[k] > History[k-1]` for 3 iterations, convergence problems are flagged.

**Distortion Convergence Monitoring:**
```
If |HD3^{(k)}/HD2^{(k)} - HD3^{(k-1)}/HD2^{(k-1)}| > 0.1:
    Log distortion convergence warning
```

This comprehensive convergence analysis framework ensures that the BJT sensitivity and harmonic distortion analysis provides accurate, stable results while maintaining computational efficiency within the Ngspice simulation environment. The implementation handles the numerical challenges of derivative computation, nonlinear coefficient extraction, and multi-parameter sensitivity analysis with robust convergence controls.

## **C Implementation**

The mathematical formulations for sensitivity and distortion analysis are realized in Ngspice through a coordinated set of C functions and data structures. These implementations map the adjoint method and Volterra series mathematics directly to efficient numerical code that integrates with SPICE's simulation kernel.

### **1. Core Data Structures for Sensitivity and Distortion**

**1.1 Sensitivity State Structure (`bjtdset.h`)**
```c
typedef struct sBJTsensitivity {
    int senParmNo;              /* Parameter number for sensitivity */
    double *senVal;             /* Sensitivity values array */
    double *senVal2;            /* Second-order sensitivities */
    int senState;               /* State index for sensitivity */
    struct sBJTsensitivity *next; /* Linked list for multiple parameters */
} BJTsensitivity;
```

**1.2 Distortion Analysis Structure (`bjtdset.h`)**
```c
typedef struct sBJTdistortion {
    double D1gp;    /* ∂I_C/∂V_BE (gm) */
    double D1gm;    /* ∂I_C/∂V_BC (gμ) */
    double D2gpp;   /* ∂²I_C/∂V_BE² */
    double D2gpm;   /* ∂²I_C/∂V_BE∂V_BC */
    double D2gmm;   /* ∂²I_C/∂V_BC² */
    double D3gppp;  /* ∂³I_C/∂V_BE³ */
    double D3gppm;  /* ∂³I_C/∂V_BE²∂V_BC */
    double D3gpmm;  /* ∂³I_C/∂V_BE∂V_BC² */
    double D3gmmm;  /* ∂³I_C/∂V_BC³ */
    double *hd2;    /* Second harmonic distortion */
    double *hd3;    /* Third harmonic distortion */
    double *imd3;   /* Third-order intermodulation */
} BJTdistortion;
```

**1.3 Extended Instance Structure (`bjtdefs.h`)**
```c
typedef struct sBJTinstance {
    /* ... standard BJT instance fields ... */
    
    /* Sensitivity analysis fields */
    BJTsensitivity *BJTsens;    /* Linked list of sensitivity states */
    double *BJTsenG;            /* Sensitivity conductance matrix */
    double *BJTsenC;            /* Sensitivity capacitance matrix */
    
    /* Distortion analysis fields */
    BJTdistortion *BJTdisto;    /* Distortion coefficients */
    int BJTdistoState;          /* State index for distortion */
    
    /* Adjoint method fields */
    double *BJTadjoint;         /* Adjoint variables λ */
    double *BJTdGdp;            /* ∂G/∂p matrix elements */
    double *BJTdCdp;            /* ∂C/∂p matrix elements */
} BJTinstance;
```

### **2. Sensitivity Analysis Implementation**

**2.1 Sensitivity Setup (`bjtsset.c`)**
```c
int BJTsSetup(SENstruct *info, GENmodel *inModel)
{
    BJ