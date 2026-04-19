# VBIC BJT: AC, Capacitance, Noise, and Transient Control

_Generated 2026-04-13 01:30 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicnoise.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbictrunc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicconv.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicgetic.c`

# Chapter: VBIC BJT: AC, Capacitance, Noise, and Transient Control

## Technical Introduction

This chapter details the C implementation of the VBIC (Vertical Bipolar Inter-Company) BJT model's AC analysis, capacitance modeling, noise generation, and transient control mechanisms within the Ngspice circuit simulator. The implementation follows Ngspice's standardized device architecture, mapping complex semiconductor physics to efficient numerical algorithms for circuit simulation. The VBIC model extends traditional Gummel-Poon formulations with quasi-saturation, self-heating, and advanced capacitance models, requiring sophisticated C implementations that balance physical accuracy with computational efficiency.

The files `vbicacld.c`, `vbicpzld.c`, `vbicnoise.c`, `vbictrunc.c`, `vbicconv.c`, and `vbicgetic.c` form the computational core for the model's dynamic and small-signal behavior. `vbicacld.c` implements the small-signal AC analysis by stamping the complex admittance matrix derived from linearizing the DC operating point. `vbicpzld.c` handles pole-zero analysis for stability assessment. `vbicnoise.c` computes spectral noise densities including shot, thermal, and flicker noise components. `vbictrunc.c` controls transient simulation accuracy through Local Truncation Error (LTE) calculation and adaptive time-stepping. `vbicconv.c` performs convergence testing for the Newton-Raphson iterations, and `vbicgetic.c` manages initial condition processing. Together, these files implement the mathematical formulations that enable accurate simulation of the VBIC BJT's frequency response, noise characteristics, and transient behavior within SPICE's Modified Nodal Analysis framework.

## 1. Mathematical Formulation

### 1.1 Small-Signal AC Admittance Matrix for VBIC BJT

The VBIC BJT model implements a complex admittance matrix for AC analysis that extends the DC conductance matrix with capacitive and frequency-dependent terms. The formulation follows SPICE's Modified Nodal Analysis (MNA) framework where each matrix element represents the linearized device behavior around the DC operating point.

#### 1.1.1 Complex Admittance Matrix Structure

For the 4-terminal VBIC model (collector, base, emitter, substrate), the AC admittance matrix takes the form:

\[
\mathbf{Y}_{ac}(\omega) = \mathbf{G} + j\omega\mathbf{C}
\]

where \(\mathbf{G}\) is the DC conductance matrix from the operating point and \(\mathbf{C}\) is the capacitance matrix. In SPICE implementation, this becomes:

\[
\begin{bmatrix}
Y_{cc} & Y_{cb} & Y_{ce} & Y_{cs} \\
Y_{bc} & Y_{bb} & Y_{be} & Y_{bs} \\
Y_{ec} & Y_{eb} & Y_{ee} & Y_{es} \\
Y_{sc} & Y_{sb} & Y_{se} & Y_{ss}
\end{bmatrix}
=
\begin{bmatrix}
g_{cc} & g_{cb} & g_{ce} & g_{cs} \\
g_{bc} & g_{bb} & g_{be} & g_{bs} \\
g_{ec} & g_{eb} & g_{ee} & g_{es} \\
g_{sc} & g_{sb} & g_{se} & g_{ss}
\end{bmatrix}
+ j\omega
\begin{bmatrix}
c_{cc} & c_{cb} & c_{ce} & c_{cs} \\
c_{bc} & c_{bb} & c_{be} & c_{bs} \\
c_{ec} & c_{eb} & c_{ee} & c_{es} \\
c_{sc} & c_{sb} & c_{se} & c_{ss}
\end{bmatrix}
\]

#### 1.1.2 Capacitance Matrix Elements from VBIC Physics

The capacitance matrix elements are derived from the VBIC charge storage equations:

**Base-emitter capacitance contributions:**
\[
c_{bb}^{be} = \frac{\partial Q_{be}}{\partial V_{be}}, \quad c_{be}^{be} = -\frac{\partial Q_{be}}{\partial V_{be}}, \quad c_{ee}^{be} = \frac{\partial Q_{be}}{\partial V_{be}}
\]

**Base-collector capacitance contributions:**
\[
c_{bb}^{bc} = \frac{\partial Q_{bc}}{\partial V_{bc}}, \quad c_{bc}^{bc} = -\frac{\partial Q_{bc}}{\partial V_{bc}}, \quad c_{cc}^{bc} = \frac{\partial Q_{bc}}{\partial V_{bc}}
\]

**Substrate-collector capacitance contributions:**
\[
c_{ss}^{sc} = \frac{\partial Q_{sc}}{\partial V_{sc}}, \quad c_{sc}^{sc} = -\frac{\partial Q_{sc}}{\partial V_{sc}}, \quad c_{cc}^{sc} = \frac{\partial Q_{sc}}{\partial V_{sc}}
\]

**Diffusion capacitance from transport currents:**
\[
c_{bb}^{diff} = \tau_F \frac{\partial I_{tf}}{\partial V_{be}} + \tau_R \frac{\partial I_{tr}}{\partial V_{bc}}
\]

#### 1.1.3 Complete Matrix Element Formulation

The individual admittance elements for SPICE stamping are:

\[
Y_{cc} = g_{ce} + g_{cb} + j\omega(C_{bc} + C_{sc})
\]
\[
Y_{cb} = -g_{cb} - j\omega C_{bc}
\]
\[
Y_{ce} = -g_{ce}
\]
\[
Y_{cs} = -j\omega C_{sc}
\]
\[
Y_{bb} = g_{be} + g_{cb} + g_{bs} + j\omega(C_{be} + C_{bc} + C_{bs})
\]
\[
Y_{be} = -g_{be} - j\omega C_{be}
\]
\[
Y_{bs} = -g_{bs} - j\omega C_{bs}
\]
\[
Y_{ee} = g_{ce} + g_{be} + j\omega C_{be}
\]
\[
Y_{ss} = g_{bs} + j\omega(C_{sc} + C_{bs})
\]

where the conductances \(g_{ij} = \partial I_i/\partial V_j\) are computed from the DC operating point.

### 1.2 Capacitance Models with VBIC Extensions

#### 1.2.1 Depletion Capacitance Formulation

The VBIC model uses the standard SPICE junction capacitance model with continuous derivatives:

**For \(V_d < F_C \cdot V_J\):**
\[
C_j(V_d) = C_{J0} \left(1 - \frac{V_d}{V_J}\right)^{-M}
\]
\[
\frac{\partial C_j}{\partial V_d} = C_{J0} \cdot M \cdot \frac{1}{V_J} \left(1 - \frac{V_d}{V_J}\right)^{-(M+1)}
\]

**For \(V_d \geq F_C \cdot V_J\):**
\[
C_j(V_d) = C_{J0} \cdot \frac{1 - F_C \cdot (1 + M) + M \cdot \frac{V_d}{V_J}}{(1 - F_C)^{1 + M}}
\]
\[
\frac{\partial C_j}{\partial V_d} = C_{J0} \cdot \frac{M}{V_J} \cdot \frac{1}{(1 - F_C)^{1 + M}}
\]

#### 1.2.2 Diffusion Capacitance with High-Injection Effects

The VBIC diffusion capacitance includes base width modulation:

\[
C_{diff} = \tau_F \cdot \frac{\partial I_{tf}}{\partial V_{be}} + \tau_R \cdot \frac{\partial I_{tr}}{\partial V_{bc}}
\]

where the derivatives account for the base charge factor \(Q_b\):

\[
\frac{\partial I_{tf}}{\partial V_{be}} = \frac{I_S}{Q_b} \cdot \frac{1}{N_F V_T} e^{\frac{V_{be}}{N_F V_T}} - \frac{I_{tf}}{Q_b} \cdot \frac{\partial Q_b}{\partial V_{be}}
\]

#### 1.2.3 Overlap and Parasitic Capacitances

The VBIC model includes fixed overlap capacitances:

\[
C_{beo} = C_{JE0} \cdot (1 - X_{CJE}) + C_{JEP} \cdot P_E
\]
\[
C_{bco} = C_{JC0} \cdot (1 - X_{CJC}) + C_{JCP} \cdot P_C
\]

where \(P_E\) and \(P_C\) are emitter and collector perimeters.

### 1.3 Noise Analysis Mathematics

#### 1.3.1 Shot Noise Spectral Density

The shot noise in VBIC follows the standard bipolar transistor formulation:

**Collector current shot noise:**
\[
S_{I_c}(f) = 2qI_C \quad \text{[A²/Hz]}
\]

**Base current shot noise:**
\[
S_{I_b}(f) = 2qI_B \quad \text{[A²/Hz]}
\]

**Correlation between collector and base noise:**
\[
S_{I_c I_b}(f) = 2qI_C \cdot \frac{\partial I_C}{\partial I_B}
\]

#### 1.3.2 Thermal Noise from Parasitic Resistances

**Base resistance thermal noise:**
\[
S_{V_{rb}}(f) = 4kTR_b \quad \text{[V²/Hz]}
\]

**Emitter resistance thermal noise:**
\[
S_{V_{re}}(f) = 4kTR_e \quad \text{[V²/Hz]}
\]

**Collector resistance thermal noise:**
\[
S_{V_{rc}}(f) = 4kTR_c \quad \text{[V²/Hz]}
\]

#### 1.3.3 Flicker (1/f) Noise Model

The VBIC flicker noise model includes both current-dependent and bias-independent components:

\[
S_{I_b}^{1/f}(f) = \frac{K_F \cdot I_B^{A_F}}{f} + \frac{K_{F2}}{f}
\]

where \(K_F\) and \(A_F\) are fitting parameters extracted from measurements.

#### 1.3.4 Avalanche Multiplication Noise

When operating near breakdown, avalanche multiplication adds excess noise:

\[
S_{I_c}^{avl}(f) = 2qI_C \cdot M^2 \cdot F(M)
\]

where \(M\) is the multiplication factor and \(F(M)\) is the excess noise factor:

\[
F(M) = M \left[1 - (1 - k_{eff}) \left(\frac{M - 1}{M}\right)^2\right]
\]

### 1.4 Transient Analysis Formulation

#### 1.4.1 Charge Conservation Formulation

The VBIC model uses the charge-controlled formulation for transient analysis:

\[
I_i(t) = \frac{dQ_i}{dt} + I_{dc,i}
\]

where \(Q_i\) represents the total charge associated with terminal \(i\).

#### 1.4.2 Backward Euler Integration

For numerical integration, SPICE uses the backward Euler method:

\[
\frac{dQ}{dt} \approx \frac{Q(t) - Q(t - \Delta t)}{\Delta t}
\]

The companion model for capacitance becomes:

\[
I_c(t) = \frac{C}{\Delta t} V(t) - \frac{C}{\Delta t} V(t - \Delta t)
\]

#### 1.4.3 Trapezoidal Integration

For better accuracy, the trapezoidal rule is often used:

\[
\frac{dQ}{dt} \approx \frac{2}{\Delta t} [Q(t) - Q(t - \Delta t)] - \frac{dQ}{dt}(t - \Delta t)
\]

The companion model is:

\[
I_c(t) = \frac{2C}{\Delta t} V(t) - \left[\frac{2C}{\Delta t} V(t - \Delta t) + I_c(t - \Delta t)\right]
\]

#### 1.4.4 VBIC-Specific Transient Considerations

**Quasi-saturation transient response:**
\[
\tau_{qs} = \frac{R_{bc} \cdot C_{bc}}{1 + g_m R_{bc}}
\]

**Self-heating thermal time constant:**
\[
\tau_{th} = R_{th} \cdot C_{th}
\]

**The complete transient response includes:**
\[
I_c(t) = I_{c,dc} + \frac{d}{dt}(Q_{be} + Q_{bc} + Q_{sc}) + \frac{\partial I_c}{\partial T_j} \cdot \frac{dT_j}{dt}
\]

## 2. Convergence Analysis

### 2.1 AC Analysis Convergence

#### 2.1.1 Frequency-Domain Newton-Raphson

For AC analysis, SPICE solves the complex linear system:

\[
[\mathbf{G} + j\omega\mathbf{C}]\mathbf{V}(\omega) = \mathbf{I}(\omega)
\]

The convergence is guaranteed for linear systems, but the VBIC model requires careful handling of:

1. **Frequency-dependent parameters**: \(C_j(\omega)\) and \(g_m(\omega)\) from high-frequency effects
2. **Noise correlation matrices**: Ensuring positive definiteness
3. **Thermal impedance**: \(Z_{th}(\omega) = R_{th}/(1 + j\omega R_{th}C_{th})\)

#### 2.1.2 Numerical Conditioning of Complex Matrices

The condition number of the complex admittance matrix affects AC solution accuracy:

\[
\kappa(\mathbf{Y}_{ac}) = \frac{\sigma_{max}(\mathbf{Y}_{ac})}{\sigma_{min}(\mathbf{Y}_{ac})}
\]

where \(\sigma\) denotes singular values. VBIC implementations monitor:

\[
\text{Warning if } \kappa > 10^6 \quad \text{Error if } \kappa > 10^{10}
\]

#### 2.1.3 Frequency Sweep Stability

For .AC analysis, SPICE performs frequency sweeps where solution from frequency \(f_k\) initializes \(f_{k+1}\). Convergence checks include:

\[
\frac{|\mathbf{V}(f_{k+1}) - \mathbf{V}(f_k)|}{|\mathbf{V}(f_k)|} < \epsilon_{freq}
\]

with typical \(\epsilon_{freq} = 10^{-4}\).

### 2.2 Transient Analysis Convergence

#### 2.2.1 Local Truncation Error (LTE) Control

The VBIC model implements rigorous LTE control for charge-based integration:

**Charge-based LTE estimate:**
\[
\text{LTE}_Q = \frac{\Delta t^2}{12} \left|\frac{d^3Q}{dt^3}\right|
\]

**Numerical approximation using backward differences:**
\[
\frac{d^3Q}{dt^3} \approx \frac{Q(t) - 3Q(t-\Delta t) + 3Q(t-2\Delta t) - Q(t-3\Delta t)}{\Delta t^3}
\]

**Normalization against SPICE tolerances:**
\[
\epsilon_{norm} = \frac{\text{LTE}_Q}{\text{reltol} \cdot |Q| + \text{chgtol}}
\]

where \(\text{chgtol} = 10^{-14}\) typically.

#### 2.2.2 Time-Step Control Algorithm

SPICE's adaptive time-stepping for VBIC:

\[
\Delta t_{new} = 
\begin{cases}
0.9 \cdot \Delta t_{old} \cdot \sqrt{\frac{\epsilon_{target}}{\epsilon_{norm}}} & \epsilon_{norm} > 1 \\
\min(1.1 \cdot \Delta t_{old}, \Delta t_{max}) & \epsilon_{norm} < 0.1 \\
\Delta t_{old} & \text{otherwise}
\end{cases}
\]

with constraints:
\[
\Delta t_{min} \leq \Delta t_{new} \leq \Delta t_{max}
\]
\[
\Delta t_{min} = 10^{-12} \text{s}, \quad \Delta t_{max} = 0.1 \cdot \text{TRAN} \text{ stop time}
\]

#### 2.2.3 Convergence Testing in Transient Analysis

Each Newton iteration at time point \(t_n\) checks:

**Voltage convergence:**
\[
|V_i^{(k+1)} - V_i^{(k)}| \leq \text{reltol} \cdot \max(|V_i^{(k+1)}|, |V_i^{(k)}|) + \text{vntol}
\]

**Charge convergence:**
\[
|Q_i^{(k+1)} - Q_i^{(k)}| \leq \text{reltol} \cdot \max(|Q_i^{(k+1)}|, |Q_i^{(k)}|) + \text{chgtol}
\]

**Temperature convergence (with self-heating):**
\[
|T_j^{(k+1)} - T_j^{(k)}| \leq 10^{-4} \cdot T_j^{(k)} + 0.1 \text{K}
\]

#### 2.2.4 Predictor-Corrector Methods

VBIC uses predictor-corrector for better initial guess:

**Prediction (polynomial extrapolation):**
\[
V^{pred}(t_n) = 2V(t_{n-1}) - V(t_{n-2}) + \Delta t[2\dot{V}(t_{n-1}) - \dot{V}(t_{n-2})]
\]

**Correction (Newton iteration):**
\[
\mathbf{J} \cdot \Delta \mathbf{V} = -\mathbf{F}(\mathbf{V}^{pred})
\]

where \(\mathbf{J}\) is the Jacobian and \(\mathbf{F}\) is the residual function.

### 2.3 Noise Analysis Convergence

#### 2.3.1 Spectral Density Integration

Noise analysis requires integration over frequency bands:

\[
\overline{v_n^2} = \int_{f_{min}}^{f_{max}} S_v(f) df
\]

Numerical integration uses adaptive quadrature with error control:

\[
\text{Error} \leq \epsilon_{abs} + \epsilon_{rel} \cdot |\overline{v_n^2}|
\]

#### 2.3.2 Correlation Matrix Positive-Definiteness

The noise correlation matrix must remain positive-definite:

\[
\mathbf{S} = 
\begin{bmatrix}
S_{I_cI_c} & S_{I_cI_b} \\
S_{I_bI_c} & S_{I_bI_b}
\end{bmatrix}
\]

Check: \(\det(\mathbf{S}) > 0\) and \(\text{trace}(\mathbf{S}) > 0\)

If numerical issues arise, SPICE applies regularization:

\[
\mathbf{S}_{reg} = \mathbf{S} + \lambda \mathbf{I}, \quad \lambda = 10^{-12} \cdot \|\mathbf{S}\|_F
\]

### 2.4 Matrix Conditioning and Numerical Stability

#### 2.4.1 Ill-Conditioning Detection

The VBIC Jacobian can become ill-conditioned when:

1. **Very small capacitances**: \(C_{je} < 10^{-18} \text{F}\)
2. **Very large resistances**: \(R_{th} > 10^9 \Omega\)
3. **Near-cutoff operation**: \(I_C < 10^{-18} \text{A}\)

Detection algorithm:
\[
\text{cond\_est} = \frac{\max_i |J_{ii}|}{\min_i |J_{ii}|}
\]
\[
\text{Warning if cond\_est} > 10^8, \quad \text{Error if cond\_est} > 10^{12}
\]

#### 2.4.2 Pivoting Strategies for VBIC

SPICE uses threshold pivoting during LU decomposition:

\[
\text{Pivot if } |J_{kk}| \geq u \cdot \max_{i \geq k} |J_{ik}|
\]

where \(u = 0.1\) for stability vs. \(u = 0.01\) for accuracy.

#### 2.4.3 Regularization Techniques

For singular matrices, SPICE applies Tikhonov regularization:

\[
\mathbf{J}_{reg} = \mathbf{J} + \mu \mathbf{D}
\]

where \(\mathbf{D}\) is diagonal with \(D_{ii} = \max(|J_{ii}|, 10^{-12})\) and \(\mu = 10^{-8}\).

### 2.5 Convergence Acceleration Techniques

#### 2.5.1 Damping for Newton-Raphson

Adaptive damping based on previous iteration performance:

\[
\lambda = \min\left(1.0, \frac{2 \cdot \text{norm}(\Delta \mathbf{V}_{prev})}{\text{norm}(\Delta \mathbf{V}_{current})}\right)
\]
\[
\mathbf{V}_{new} = \mathbf{V}_{old} + \lambda \Delta \mathbf{V}
\]

#### 2.5.2 Continuation Methods for Difficult Cases

For hard convergence, SPICE uses parameter continuation:

\[
\mathbf{F}(\mathbf{V}, \alpha) = \mathbf{0}, \quad \alpha: 0 \rightarrow 1
\]

where \(\alpha\) gradually introduces:
1. Nonlinearities (exponential terms)
2. Thermal coupling
3. High-injection effects

#### 2.5.3 Dynamic Tolerance Adjustment

Tolerances adapt based on solution scale:

\[
\text{reltol}_{eff} = \text{reltol} \cdot \left[1 + 0.5 \log_{10}\left(\max\left(\frac{|I_C|}{1\text{A}}, \frac{|V_{CE}|}{1\text{V}}\right)\right)\right]
\]

### 2.6 Memory and Performance Considerations

#### 2.6.1 State Vector Management

VBIC requires storage for:
- Terminal voltages (4)
- Junction charges (3)
- Diffusion charges (2)
- Thermal state (1 if enabled)
- History terms (3 for LTE)

Total: 13 state variables per instance

#### 2.6.2 Matrix Sparsity Pattern

The VBIC Jacobian has predictable sparsity:
- 4×4 block for electrical nodes
- Additional row/column for thermal node
- 37 non-zero entries out of 25 (5×5) or 16 (4×4)

#### 2.6.3 Computational Complexity

Per Newton iteration:
- 50-100 floating-point operations for current evaluation
- 100-200 operations for derivative calculation
- O(n³) for matrix solve, but n ≤ 5

### 2.7 Error Recovery and Fallback Strategies

#### 2.7.1 Time-Step Reduction Hierarchy

If convergence fails:
1. Reduce time step by factor of 2
2. Switch to backward Euler (more stable)
3. Reduce Newton damping factor
4. Use previous successful solution as initial guess

#### 2.7.2 Model Simplification for Recovery

In extreme cases, SPICE can temporarily:
1. Disable self-heating
2. Use simplified capacitance models
3. Ignore quasi-saturation effects
4. Use linearized models

#### 2.7.3 Convergence Statistics Monitoring

SPICE tracks:
- Average Newton iterations per time point
- Number of time-step reductions
- Maximum LTE observed
- Condition number history

These statistics guide adaptive algorithm selection and parameter tuning.

The convergence analysis demonstrates that VBIC implementation in SPICE requires sophisticated numerical techniques to handle the complex interactions between electrical and thermal domains, multiple nonlinear effects, and the wide dynamic range of bipolar transistor operation. The algorithms balance computational efficiency with robust convergence across all operating conditions.

## 3. C Implementation

### 3.1 Core Data Structures for AC and Transient Analysis

```c
/* VBIC instance structure extensions for AC/transient (vbicdefs.h) */
typedef struct sVBICinstance {
    /* DC operating point values */
    double VBICvbe;      /* Base-emitter voltage */
    double VBICvbc;      /* Base-collector voltage */
    double VBICvcs;      /* Collector-substrate voltage */
    double VBICic;       /* Collector current */
    double VBICib;       /* Base current */
    double VBICisub;     /* Substrate current */
    
    /* Small-signal parameters */
    double VBICgm;       /* Transconductance ∂Ic/∂Vbe */
    double VBICgo;       /* Output conductance ∂Ic/∂Vce */
    double VBICgpi;      /* Input conductance ∂Ib/∂Vbe */
    double VBICgmu;      /* Feedback conductance ∂Ib/∂Vbc */
    
    /* Capacitance values */
    double VBICcbe;      /* Base-emitter capacitance */
    double VBICcbc;      /* Base-collector capacitance */
    double VBICccs;      /* Collector-substrate capacitance */
    double VBICcjs;      /* Substrate capacitance */
    
    /* Charge states */
    double VBICqbe;      /* Base-emitter charge */
    double VBICqbc;      /* Base-collector charge */
    double VBICqcs;      /* Collector-substrate charge */
    double VBICqjs;      /* Substrate junction charge */
    
    /* History for integration */
    double VBICqbe_hist[3];  /* Charge history for LTE */
    double VBICqbc_hist[3];
    double VBICqcs_hist[3];
    
    /* Matrix pointers for 4-terminal device */
    double *VBICccPtr;   /* Collector-collector */
    double *VBICcbPtr;   /* Collector-base */
    double *VBICcePtr;   /* Collector-emitter */
    double *VBICcsPtr;   /* Collector-substrate */
    double *VBICbcPtr;   /* Base-collector */
    double *VBICbbPtr;   /* Base-base */
    double *VBICbePtr;   /* Base-emitter */
    double *VBICbsPtr;   /* Base-substrate */
    double *VBICecPtr;   /* Emitter-collector */
    double *VBICebPtr;   /* Emitter-base */
    double *VBICeePtr;   /* Emitter-emitter */
    double *VBICesPtr;   /* Emitter-substrate */
    double *VBICscPtr;   /* Substrate-collector */
    double *VBICsbPtr;   /* Substrate-base */
    double *VBICsePtr;   /* Substrate-emitter */
    double *VBICssPtr;   /* Substrate-substrate */
    
    /* Thermal node pointers (if enabled) */
    double *VBICtcPtr;   /* Thermal-collector */
    double *VBICtbPtr;   /* Thermal-base */
    double *VBICtePtr;   /* Thermal-emitter */
    double *VBICtsPtr;   /* Thermal-substrate */
    double *VBICttPtr;   /* Thermal-thermal */
    
    /* State vector indices */
    int VBICqbeState;    /* State index for Qbe */
    int VBICqbcState;    /* State index for Qbc */
    int VBICqcsState;    /* State index for Qcs */
    int VBICqjsState;    /* State index for Qjs */
    
    /* Flags */
    unsigned VBICoff:1;          /* Device off */
    unsigned VBICtempNodeGiven:1; /* Thermal node enabled */
    unsigned VBICicGiven:1;      /* Initial conditions given */
} VBICinstance;
```

### 3.2 AC Load Implementation (vbicacld.c)

```c
int VBICacLoad(GENmodel *inModel, CKTcircuit *ckt) {
    VBICmodel *model = (VBICmodel *)inModel;
    VBICinstance *here;
    double omega;
    double gbe, gbc, gce, gcs;
    double cbe, cbc, ccs, cjs;
    double complex ycc, ycb, yce, ycs;
    double complex ybc, ybb, ybe, ybs;
    double complex yec, yeb, yee, yes;
    double complex ysc, ysb, yse, yss;
    
    /* Check analysis mode */
    if (!(ckt->CKTmode & MODEAC)) {
        return OK;  /* Not AC analysis */
    }
    
    omega = ckt->CKTomega;
    
    for (; model != NULL; model = model->VBICnextModel) {
        for (here = model->VBICinstances; here != NULL; 
             here = here->VBICnextInstance) {
            
            /* Extract small-signal parameters from DC op point */
            gbe = here->VBICgpi;      /* ∂Ib/∂Vbe */
            gbc = here->VBICgmu;      /* ∂Ib/∂Vbc */
            gce = here->VBICgm;       /* ∂Ic/∂Vbe */
            gcs = here->VBICgo;       /* ∂Ic/∂Vce */
            
            /* Extract capacitances */
            cbe = here->VBICcbe;
            cbc = here->VBICcbc;
            ccs = here->VBICccs;
            cjs = here->VBICcjs;
            
            /* Calculate complex admittances */
            /* Collector row */
            ycc = gcs + gbc + I * omega * (cbc + ccs);
            ycb = -gbc - I * omega * cbc;
            yce = -gcs;
            ycs = -I * omega * ccs;
            
            /* Base row */
            ybc = -gbc - I * omega * cbc;
            ybb = gbe + gbc + I * omega * (cbe + cbc);
            ybe = -gbe - I * omega * cbe;
            ybs = 0.0;
            
            /* Emitter row */
            yec = -gcs;
            yeb = -gbe - I * omega * cbe;
            yee = gce + gbe + I * omega * cbe;
            yes = 0.0;
            
            /* Substrate row */
            ysc = -I * omega * ccs;
            ysb = 0.0;
            yse = 0.0;
            yss = I * omega * cjs;  /* Substrate capacitance only */
            
            /* Stamp into complex matrix */
            /* Collector equation */
            ckt->CKTmatrix[here->VBICcolNode][here->VBICcolNode]->real += creal(ycc);
            ckt->CKTmatrix[here->VBICcolNode][here->VBICcolNode]->imag += cimag(ycc);
            
            ckt->CKTmatrix[here->VBICcolNode][here->VBICbaseNode]->real += creal(ycb);
            ckt->CKTmatrix[here->VBICcolNode][here->VBICbaseNode]->imag += cimag(ycb);
            
            ckt->CKTmatrix[here->VBICcolNode][here->VBICemitNode]->real += creal(yce);
            ckt->CKTmatrix[here->VBICcolNode][here->VBICemitNode]->imag += cimag(yce);
            
            ckt->CKTmatrix[here->VBICcolNode][here->VBICsubsNode]->real += creal(ycs);
            ckt->CKTmatrix[here->VBICcolNode][here->VBICsubsNode]->imag += cimag(ycs);
            
            /* Base equation */
            ckt->CKTmatrix[here->VBICbaseNode][here->VBICcolNode]->real += creal(ybc);
            ckt->CKTmatrix[here->VBICbaseNode][here->VBICbaseNode]->imag += cimag(ybc);
            
            ckt->CKTmatrix[here->VBICbaseNode][here->VBICbaseNode]->real += creal(ybb);
            ckt->CKTmatrix[here->VBICbaseNode][here->VBICbaseNode]->imag += cimag(ybb);
            
            ckt->CKTmatrix[here->VBICbaseNode][here->VBICemitNode]->real += creal(ybe);
            ckt->CKTmatrix[here->VBICbaseNode][here->VBICemitNode]->imag += cimag(ybe);
            
            /* Emitter equation */
            ckt->CKTmatrix[here->VBICemitNode][here->VBICcolNode]->real += creal(yec);
            ckt->CKTmatrix[here->VBICemitNode][here->VBICcolNode]->imag += cimag(yec);
            
            ckt->CKTmatrix[here->VBICemitNode][here->VBICbaseNode]->real += creal(yeb);
            ckt->CKTmatrix[here->VBICemitNode][here->VBICbaseNode]->imag += cimag(yeb);
            
            ckt->CKTmatrix[here->VBICemitNode][here->VBICemitNode]->real += creal(yee);
            ckt->CKTmatrix[here->VBICemitNode][here->VBICemitNode]->imag += cimag(yee);
            
            /* Substrate equation */
            ckt->CKTmatrix[here->VBICsubsNode][here->VBICcolNode]->real += creal(ysc);
            ckt->CKTmatrix[here->VBICsubsNode][here->VBICcolNode]->imag += cimag(ysc);
            
            ckt->CKTmatrix[here->VBICsubsNode][here->VBICsubsNode]->real += creal(yss);
            ckt->CKTmatrix[here->VBICsubsNode][here->VBICsubsNode]->imag += cimag(yss);
            
            /* Thermal network if enabled */
            if (here->VBICtempNodeGiven) {
                double gth = 1.0 / model->VBICrth;
                double cth = model->VBICcth;
                double complex ytt = gth + I * omega * cth;
                
                /* Thermal node self-admittance */
                ckt->CKTmatrix[here->VBICtempNode][here->VBICtempNode]->real += creal(ytt);
                ckt->CKTmatrix[here->VBICtempNode][here->VBICtempNode]->imag += cimag(ytt);
                
                /* Thermal coupling terms (∂I/∂T and ∂T/∂V) */
                double dIc_dT = here->VBICdIdT;  /* From DC analysis */
                double dIb_dT = here->VBICdIbT;
                double dP_dVc = here->VBICdPdVc; /* Power derivatives */
                double dP_dVb = here->VBICdPdVb;
                double dP_dVe = here->VBICdPdVe;
                
                /* Stamp thermal coupling */
                ckt->CKTmatrix[here->VBICcolNode][here->VBICtempNode]->real += dIc_dT;
                ckt->CKTmatrix[here->VBICbaseNode][here->VBICtempNode]->real += dIb_dT;
                
                ckt->CKTmatrix[here->VBICtempNode][here->VBICcolNode]->real += -dP_dVc;
                ckt->CKTmatrix[here->VBICtempNode][here->VBICbaseNode]->real += -dP_dVb;
                ckt->CKTmatrix[here->VBICtempNode][here->VBICemitNode]->real += -dP_dVe;
            }
        }
    }
    
    return OK;
}
```

### 3.3 Capacitance and Charge Implementation (vbiccap.c)

```c
/* Calculate junction capacitances with bias dependence */
void VBIC_calc_caps(VBICinstance *here, VBICmodel *model,
                    double vbe, double vbc, double vcs) {
    double fc = 0.5;  /* Forward bias factor */
    double cjbe, cjbc, cjcs;
    
    /* Base-emitter depletion capacitance */
    if (vbe < fc * model->VBICvje) {
        /* Reverse and moderate forward bias */
        cjbe = model->VBICcje0 * 
               pow(1.0 - vbe/model->VBICvje, -model->VBICmje);
    } else {
        /* Strong forward bias - linear extrapolation */
        double arg = 1.0 - fc;
        double f1 = pow(arg, -model->VBICmje);
        double f2 = model->VBICmje * fc / (model->VBICvje * arg);
        cjbe = model->VBICcje0 * (f1 + f2 * (vbe - fc * model->VBICvje));
    }
    
    /* Base-collector depletion capacitance */
    if (vbc < fc * model->VBICvjc) {
        cjbc = model->VBICcjc0 * 
               pow(1.0 - vbc/model->VBICvjc, -model->VBICmjc);
    } else {
        double arg = 1.0 - fc;
        double f1 = pow(arg, -model->VBICmjc);
        double f2 = model->VBICmjc * fc / (model->VBICvjc * arg);
        cjbc = model->VBICcjc0 * (f1 + f2 * (vbc - fc * model->VBICvjc));
    }
    
    /* Collector-substrate depletion capacitance */
    if (vcs < fc *