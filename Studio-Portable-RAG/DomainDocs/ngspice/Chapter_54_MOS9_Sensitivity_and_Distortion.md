# MOS9: Sensitivity and Distortion Analysis

_Generated 2026-04-12 09:10 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9sld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9sset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9dist.c`

# MOS9: Sensitivity and Distortion Analysis

## Chapter Introduction

The files `mos9sld.c`, `mos9sset.c`, and `mos9dist.c` implement the advanced analysis capabilities of the Philips MOS9 model within Ngspice's simulation framework. These modules extend the core DC/AC analysis to provide critical insights for circuit design optimization and nonlinear performance characterization.

**`mos9sld.c`** (Sensitivity Load) implements the adjoint method for computing parameter sensitivities, calculating how circuit performance metrics (node voltages, branch currents) change with respect to variations in device model parameters (VTO, KP, γ, η, etc.) and geometric parameters (L, W, AD, AS). It stamps derivative matrices into the circuit's sensitivity system, enabling efficient computation of ∂V/∂p for multiple parameters simultaneously.

**`mos9sset.c`** (Sensitivity Setup) allocates the extended data structures and matrix pointers required for sensitivity analysis. It establishes the mapping between SPICE parameters and their corresponding derivative storage locations, initializes sensitivity arrays, and configures the adjoint system infrastructure.

**`mos9dist.c`** (Distortion Analysis) computes harmonic distortion coefficients using Taylor series expansion of the MOS9 device equations. It calculates second and third-order derivatives (g_m2, g_m3, g_ds2, etc.) to predict harmonic distortion (HD2, HD3) and intermodulation distortion (IMD3) for RF and analog circuit design.

Together, these files transform the MOS9 model from a simple IV characteristic calculator into a comprehensive design analysis tool, providing the mathematical derivatives and nonlinear coefficients needed for yield analysis, circuit optimization, and distortion prediction in analog/RF applications.

---

## Mathematical Formulation

The sensitivity and distortion analysis of the MOS9 model in SPICE extends the small-signal linearization to compute derivatives with respect to model parameters and to quantify harmonic generation from device nonlinearities. These analyses are critical for circuit optimization and RF design.

### 1. Sensitivity Analysis Mathematics

Sensitivity analysis computes how circuit performance metrics (voltages, currents) change with respect to variations in device model parameters. In SPICE, this is implemented using the adjoint method for computational efficiency.

#### 1.1 Adjoint Method Formulation

For a circuit described by the nodal equation `F(V, p) = 0`, where `V` is the node voltage vector and `p` is a model parameter, the sensitivity of an output function `Φ(V, p)` is:

```
∂Φ/∂p = λᵀ·(∂F/∂p) + ∂Φ/∂p
```

Where the adjoint vector `λ` satisfies:
```
[∂F/∂V]ᵀ·λ = ∂Φ/∂V
```

For the MOS9 model, the device equation contributions to the circuit Jacobian `∂F/∂V` are the conductance matrix entries `G_ij` calculated during DC analysis.

#### 1.2 Parameter Derivatives for MOS9

The sensitivity analysis requires analytical derivatives of the drain current and charges with respect to each model parameter:

**Threshold Voltage Sensitivity:**
```
∂I_ds/∂VTO = -g_m·(1 + η·V_ds)  (linear region)
∂I_ds/∂VTO = -g_m·(1 + η·V_dsat)  (saturation region)
```

**Transconductance Parameter Sensitivity:**
```
∂I_ds/∂KP = I_ds/KP
```

**Body Effect Parameter Sensitivity:**
```
∂I_ds/∂γ = g_m·(√(φ - V_bs) - √φ)/(2√(φ - V_bs))·(1 + η·V_ds)
```

**Drain-Induced Barrier Lowering Sensitivity:**
```
∂I_ds/∂η = g_m·V_ds  (linear)
∂I_ds/∂η = g_m·V_dsat  (saturation)
```

**Mobility Degradation Sensitivity:**
```
∂I_ds/∂θ = -g_m·(V_gs - V_th)/(1 + θ·(V_gs - V_th))·I_ds
```

#### 1.3 Charge Parameter Sensitivities

For transient sensitivity analysis, charge derivatives are also required:

**Gate-Source Charge Sensitivity:**
```
∂Q_gs/∂C_ox = (2/3)·W_eff·L_eff·[1 - ((V_gd - V_th)/(V_gs - V_th + V_gd - V_th))²]
∂Q_gs/∂VTO = -∂Q_gs/∂V_gs·(1 + ∂V_th/∂VTO)
```

**Junction Capacitance Sensitivities:**
```
∂Q_bd/∂CJ = AD·∫(1 - V_bd/PB)^{-MJ} dV_bd
∂Q_bd/∂MJ = -AD·CJ·∫(1 - V_bd/PB)^{-MJ}·ln(1 - V_bd/PB) dV_bd
∂Q_bd/∂PB = AD·CJ·MJ·∫(1 - V_bd/PB)^{-MJ-1}·(V_bd/PB²) dV_bd
```

#### 1.4 Normalized Sensitivity Coefficients

SPICE typically reports normalized sensitivities:
```
S_p^Φ = (p/Φ)·(∂Φ/∂p)
```

For the drain current with respect to VTO:
```
S_VTO^{I_ds} = (VTO/I_ds)·(∂I_ds/∂VTO) ≈ -VTO/(V_gs - V_th)
```

### 2. Distortion Analysis Mathematics

Harmonic distortion analysis quantifies the nonlinear behavior of the MOS9 device when driven by sinusoidal signals. This is implemented using Taylor series expansion or Volterra series analysis.

#### 2.1 Taylor Series Expansion of Drain Current

The drain current can be expanded around the DC operating point:
```
I_ds(V_gs + v_gs, V_ds + v_ds, V_bs + v_bs) = I_DC + 
    g_m·v_gs + g_ds·v_ds + g_mb·v_bs +
    (1/2)·g_m2·v_gs² + (1/2)·g_ds2·v_ds² + (1/2)·g_mb2·v_bs² +
    g_md·v_gs·v_ds + g_mb_d·v_gs·v_bs + g_ds_b·v_ds·v_bs +
    (1/6)·g_m3·v_gs³ + (1/6)·g_ds3·v_ds³ + (1/6)·g_mb3·v_bs³ + ...
```

Where the nonlinear coefficients are:

**Second-Order Coefficients:**
```
g_m2 = ∂²I_ds/∂V_gs²
g_ds2 = ∂²I_ds/∂V_ds²
g_mb2 = ∂²I_ds/∂V_bs²
g_md = ∂²I_ds/∂V_gs∂V_ds
g_mb_d = ∂²I_ds/∂V_gs∂V_bs
g_ds_b = ∂²I_ds/∂V_ds∂V_bs
```

**Third-Order Coefficients:**
```
g_m3 = ∂³I_ds/∂V_gs³
g_ds3 = ∂³I_ds/∂V_ds³
g_mb3 = ∂³I_ds/∂V_bs³
```

#### 2.2 MOS9-Specific Nonlinear Coefficients

For the Philips MOS9 model in saturation region:

**Second-Order Transconductance:**
```
g_m2 = ∂/∂V_gs[β·(V_gs - V_th)·(1 + λ·V_ds)/(1 + θ·(V_gs - V_th))]
     = β·(1 + λ·V_ds)·[1/(1 + θ·(V_gs - V_th)) - θ·(V_gs - V_th)/(1 + θ·(V_gs - V_th))²]
```

**Third-Order Transconductance:**
```
g_m3 = ∂g_m2/∂V_gs
     = -2β·θ·(1 + λ·V_ds)/[1 + θ·(V_gs - V_th)]³
```

**Cross-Term Coefficient (gm·gds interaction):**
```
g_md = ∂²I_ds/∂V_gs∂V_ds = β·λ/(1 + θ·(V_gs - V_th))
```

#### 2.3 Harmonic Distortion Metrics

For a sinusoidal gate-source voltage `v_gs = V_a·cos(ωt)`:

**Second Harmonic Distortion (HD2):**
```
HD2 = (1/4)·|g_m2/g_m|·V_a
```

**Third Harmonic Distortion (HD3):**
```
HD3 = (1/24)·|g_m3/g_m|·V_a²
```

**Total Harmonic Distortion:**
```
THD = √(HD2² + HD3² + ...)
```

**Intermodulation Distortion (IMD3):**
For two-tone input `v_gs = V_a·[cos(ω₁t) + cos(ω₂t)]`:
```
IMD3 = (3/4)·|g_m3/g_m|·V_a²  (at 2ω₁ - ω₂ and 2ω₂ - ω₁)
```

#### 2.4 Capacitive Nonlinearities

The Meyer capacitance model also contributes to distortion:

**Gate-Source Capacitance Nonlinearity:**
```
C_gs(V_gs) = C_gso·W_eff + (2/3)·C_ox·W_eff·L_eff·[1 - (V_gd - V_th)²/(V_gs - V_th + V_gd - V_th)²]
```

The nonlinear capacitance coefficients:
```
C_gs1 = ∂C_gs/∂V_gs
C_gs2 = (1/2)·∂²C_gs/∂V_gs²
C_gs3 = (1/6)·∂³C_gs/∂V_gs³
```

**Junction Capacitance Nonlinearity:**
```
C_j(V) = CJ·(1 - V/PB)^{-MJ}
C_j1 = ∂C_j/∂V = (MJ·CJ/PB)·(1 - V/PB)^{-MJ-1}
C_j2 = (1/2)·∂²C_j/∂V² = (MJ·(MJ+1)·CJ/(2·PB²))·(1 - V/PB)^{-MJ-2}
```

### 3. Volterra Series Analysis

For large-signal distortion analysis, SPICE may use Volterra series, which accounts for frequency-dependent nonlinearities:

#### 3.1 Nonlinear Transfer Functions

The nth-order Volterra kernel `H_n(ω₁, ..., ω_n)` relates input spectral components to output:

```
I_ds(ω) = H_1(ω)·V_gs(ω) + 
          ∫H_2(ω₁, ω-ω₁)·V_gs(ω₁)·V_gs(ω-ω₁)dω₁ +
          ∬H_3(ω₁, ω₂, ω-ω₁-ω₂)·V_gs(ω₁)·V_gs(ω₂)·V_gs(ω-ω₁-ω₂)dω₁dω₂ + ...
```

#### 3.2 Frequency-Dependent Nonlinear Coefficients

For the MOS9 with velocity saturation:

```
H_1(ω) = g_m/(1 + jωτ)
H_2(ω₁, ω₂) = g_m2/[(1 + jω₁τ)(1 + jω₂τ)(1 + j(ω₁+ω₂)τ)]
H_3(ω₁, ω₂, ω₃) = g_m3/[(1 + jω₁τ)(1 + jω₂τ)(1 + jω₃τ)(1 + j(ω₁+ω₂+ω₃)τ)]
```

Where `τ = C_gs/g_m` is the input time constant.

## Convergence Analysis

### 1. Sensitivity Analysis Convergence

Sensitivity analysis in SPICE uses the already-converged DC solution, but additional numerical considerations apply:

#### 1.1 Adjoint System Solution

The adjoint equation `[J]ᵀ·λ = b` must be solved, where `[J]` is the converged circuit Jacobian. Convergence requires:

```
||[J]ᵀ·λ - b|| < ε_sens = max(CKTreltol·||b||, CKTabstol)
```

Typical tolerances: `CKTreltol = 1×10⁻³`, `CKTabstol = 1×10⁻¹²`.

#### 1.2 Parameter Derivative Continuity

The analytical derivatives `∂F/∂p` must be continuous for convergence. For MOS9, this requires:

**Smoothing at Region Boundaries:**
At the linear-saturation boundary `V_ds = V_dsat`, the derivative smoothing ensures:
```
lim_{V_ds→V_dsat⁻} ∂I_ds/∂p = lim_{V_ds→V_dsat⁺} ∂I_ds/∂p
```

The smoothing function uses:
```
f(V_ds, V_dsat) = 0.5·[1 + tanh(A·(V_ds - V_dsat))]
∂f/∂V_ds = (A/2)·sech²(A·(V_ds - V_dsat))
```
with `A ≈ 10-50 V⁻¹` for smooth transition.

#### 1.3 Numerical Differentiation Fallback

When analytical derivatives are unavailable or problematic, SPICE uses numerical differentiation:
```
∂F/∂p ≈ [F(p + Δp) - F(p - Δp)]/(2Δp)
```

The perturbation `Δp` is chosen as:
```
Δp = max(√ε·|p|, δ_min)
```
where `ε ≈ 1×10⁻⁸` (machine epsilon for double precision) and `δ_min ≈ 1×10⁻¹²`.

### 2. Distortion Analysis Convergence

Harmonic balance and distortion analysis require convergence of the nonlinear system at multiple frequencies.

#### 2.1 Harmonic Balance Convergence

For `.DISTO` analysis with input amplitude `V_in`, the harmonic balance error at frequency `kω₀` is:
```
E_k = |F_k(V) - Y_k·V_k - I_nl,k(V)| < ε_dist
```

Where:
- `F_k` is the k-th harmonic of device equations
- `Y_k` is the linear admittance matrix at frequency `kω₀`
- `I_nl,k` is the k-th harmonic of nonlinear currents

The convergence criterion:
```
max_k(||E_k||/||I_nl,k||) < η_dist
```
with `η_dist = 1×10⁻⁶` typically.

#### 2.2 Newton-Raphson for Harmonic Balance

The extended Jacobian for harmonic balance includes frequency-dependent terms:
```
[J_HB] = ∂F/∂V = [Y] + [∂I_nl/∂V]
```

Where `[∂I_nl/∂V]` is block-diagonal with blocks `[∂I_nl,k/∂V_k]` at each harmonic.

Convergence requires:
```
cond([J_HB]) < κ_max ≈ 1×10⁸
```

#### 2.3 Intermodulation Product Convergence

For two-tone analysis at frequencies `ω₁` and `ω₂`, the intermodulation products at `2ω₁ - ω₂` and `2ω₂ - ω₁` must also converge:

```
|I_IMD3|/|I_fund| < ε_IMD = 1×10⁻⁹  (for -180 dBc resolution)
```

### 3. Numerical Stability Considerations

#### 3.1 Derivative Regularization

To prevent singularities in sensitivity calculations:

**Near-Zero Current Regularization:**
When `|I_ds| < I_min ≈ 1×10⁻¹⁸` A:
```
∂I_ds/∂p ≈ sign(∂I_ds/∂p)·I_min/|p|
```

**Near-Threshold Regularization:**
When `|V_gs - V_th| < V_min ≈ 1×10⁻⁶` V:
```
g_m ≈ β·V_min
g_m2 ≈ β
g_m3 ≈ 0
```

#### 3.2 Frequency Scaling for Distortion

High-frequency distortion analysis requires careful frequency scaling:

**Maximum Frequency for Convergence:**
```
f_max = min(0.1·f_T, 0.01·f_τ)
```
where:
- `f_T = g_m/(2πC_gs)` (transit frequency)
- `f_τ = 1/(2πτ_thermal)` (thermal time constant frequency)

**Adaptive Harmonic Truncation:**
The number of harmonics `N_h` is adaptively determined:
```
N_h = min(N_max, ceil(2·f_max/f_in))
```
with `N_max = 10` typically for MOS9.

#### 3.3 Memory Effect Convergence

For accurate distortion prediction with memory effects (due to traps, thermal effects):

**Thermal Time Constant Integration:**
```
τ_thermal = R_th·C_th
P_diss(t) = I_ds(t)·V_ds(t)
ΔT(t) = ∫_0^t P_diss(t')·exp(-(t-t')/τ_thermal) dt'/C_th
```

The harmonic balance must converge for both electrical and thermal variables:
```
|ΔT_k|/T_0 < ε_thermal = 1×10⁻⁴
```

### 4. Convergence Acceleration Techniques

#### 4.1 Continuation Methods for Large-Signal Distortion

For large input amplitudes `V_in`, continuation (homotopy) methods are used:

**Amplitude Continuation:**
```
V_in(λ) = λ·V_in_target, λ: 0 → 1
```

At each λ step, the solution from previous λ is used as initial guess.

**Frequency Continuation:**
For multi-tone analysis, tones are added sequentially:
1. Solve for ω₁ alone
2. Use as initial guess for ω₁ + ω₂
3. Solve for full spectrum including IMD products

#### 4.2 Preconditioning for Sensitivity Equations

The adjoint system `[J]ᵀ·λ = b` is preconditioned using:

**Diagonal Preconditioner:**
```
P = diag(1/√(J_ii² + ε))
```
where `ε = 1×10⁻¹²` prevents division by zero.

**Approximate Inverse Preconditioner:**
For MOS9-dominated circuits:
```
P ≈ [Y]⁻¹ where [Y] = diag(g_m, g_ds, g_mb, ...)
```

#### 4.3 Step Size Control in Parameter Space

For parameter sweeps in sensitivity analysis:

**Adaptive Parameter Step:**
```
Δp_{k+1} = Δp_k·min(2, √(ε_target/ε_k))
```
where `ε_k` is the error at step k.

**Backtracking on Divergence:**
If Newton iteration diverges:
```
Δp ← Δp/2
```
and retry with smaller step.

### 5. Error Estimation and Validation

#### 5.1 Sensitivity Error Bounds

The error in sensitivity calculation is bounded by:

**Truncation Error from Numerical Differentiation:**
```
|∂F/∂p - ∂F/∂p_numeric| ≤ (Δp²/6)·|∂³F/∂p³|
```

**Condition Number Effects:**
```
|ΔS|/|S| ≤ cond([J])·(||Δb||/||b|| + ||ΔJ||/||J||)
```

#### 5.2 Distortion Error Metrics

**Relative Error in HD3:**
```
ε_HD3 = |HD3_analytic - HD3_numeric|/HD3_analytic < 0.01  (1% error)
```

**Intermodulation Error:**
```
ε_IMD3 = |IMD3(ω₁,ω₂) - IMD3(ω₂,ω₁)|/IMD3_avg < 0.001  (0.1% symmetry error)
```

#### 5.3 Convergence Monitoring

SPICE monitors convergence through:

**Residual History:**
```
r_k = ||F(V_k)||
Converged if: r_k < ε_abs AND r_k/r_{k-1} < 0.1
```

**Parameter Change History:**
```
Δp_k = ||p_k - p_{k-1}||
Converged if: Δp_k < ε_p AND Δp_k/Δp_{k-1} < 0.5
```

This mathematical formulation ensures that MOS9 sensitivity and distortion analysis in SPICE provides accurate, numerically stable results for circuit optimization and nonlinear performance prediction, with rigorous convergence guarantees even for challenging operating conditions.

---

## C Implementation

### 1. Sensitivity Analysis Implementation (`mos9sld.c`)

#### 1.1 Extended Data Structures for Sensitivity

The sensitivity analysis requires extended data structures to store parameter derivatives:

```c
/* In mos9defs.h - Extended instance structure for sensitivity */
typedef struct sMOS9instance {
    /* ... existing fields ... */
    
    /* Sensitivity analysis fields */
    double *MOS9sens;               /* Sensitivity values array */
    double *MOS9dphidp;             /* ∂φ/∂p derivatives */
    double *MOS9dvthdp;             /* ∂Vth/∂p derivatives */
    double *MOS9dgmdp;              /* ∂gm/∂p derivatives */
    double *MOS9dgdsdp;             /* ∂gds/∂p derivatives */
    double *MOS9dgmbsdp;            /* ∂gmbs/∂p derivatives */
    
    /* Parameter derivative flags */
    unsigned int MOS9sensGiven:1;
    unsigned int MOS9sensFlag:1;
    
    /* Sensitivity matrix pointers */
    double **MOS9sensDdPtr;         /* ∂Gdd/∂p */
    double **MOS9sensDgPtr;         /* ∂Gdg/∂p */
    double **MOS9sensDsPtr;         /* ∂Gds/∂p */
    double **MOS9sensDbPtr;         /* ∂Gdb/∂p */
    /* ... 12 more sensitivity matrix pointers ... */
} MOS9instance;

/* Sensitivity model structure */
typedef struct sMOS9sensModel {
    int MOS9senParmNum;             /* Number of sensitivity parameters */
    char **MOS9senParmNames;        /* Parameter names */
    int *MOS9senParmTypes;          /* Parameter types */
    double *MOS9senParmValues;      /* Parameter values */
    struct sMOS9sensModel *MOS9nextSensModel;
} MOS9sensModel;
```

#### 1.2 Sensitivity Load Function Implementation

The `MOS9sLoad()` function in `mos9sld.c` computes and stamps parameter derivatives:

```c
int MOS9sLoad(GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS9model *model;
    MOS9instance *inst;
    SENstruct *info;
    double sVth, sPhi, sGamma, sEta, sDelta;
    double sGm, sGds, sGmbs;
    double sCgs, sCgd, sCgb;
    int iparm, i;
    
    info = ckt->CKTsenInfo;
    
    for(model = (MOS9model *)inModel; model != NULL; model = model->MOS9nextModel) {
        for(inst = model->MOS9instances; inst != NULL; inst = inst->MOS9nextInstance) {
            
            /* Compute operating point if not already done */
            if(!inst->MOS9senFlag) {
                MOS9computeOP(inst, model, ckt);
                inst->MOS9senFlag = 1;
            }
            
            /* Allocate sensitivity arrays if needed */
            if(inst->MOS9sens == NULL) {
                int numParams = info->SENparms;
                inst->MOS9sens = TMALLOC(double, numParams);
                inst->MOS9dphidp = TMALLOC(double, numParams);
                inst->MOS9dvthdp = TMALLOC(double, numParams);
                inst->MOS9dgmdp = TMALLOC(double, numParams);
                inst->MOS9dgdsdp = TMALLOC(double, numParams);
                inst->MOS9dgmbsdp = TMALLOC(double, numParams);
                
                /* Initialize to zero */
                for(iparm = 0; iparm < numParams; iparm++) {
                    inst->MOS9sens[iparm] = 0.0;
                    inst->MOS9dphidp[iparm] = 0.0;
                    inst->MOS9dvthdp[iparm] = 0.0;
                    inst->MOS9dgmdp[iparm] = 0.0;
                    inst->MOS9dgdsdp[iparm] = 0.0;
                    inst->MOS9dgmbsdp[iparm] = 0.0;
                }
            }
            
            /* Compute parameter derivatives for each sensitivity parameter */
            for(iparm = 0; iparm < info->SENparms; iparm++) {
                int parmType = info->SENparmType[iparm];
                int parmIndex = info->SENparmIndex[iparm];
                
                switch(parmType) {
                    case SEN_MODEL:
                        /* Model parameter sensitivity */
                        switch(parmIndex) {
                            case MOS9_VTO:
                                /* ∂Vth/∂VTO = 1 */
                                sVth = 1.0;
                                sPhi = 0.0;
                                sGamma = 0.0;
                                sEta = 0.0;
                                sDelta = 0.0;
                                break;
                                
                            case MOS9_GAMMA:
                                /* ∂Vth/∂γ = √(φ + Vbs) - √φ */
                                sVth = sqrt(model->MOS9phi - inst->MOS9vbs) - sqrt(model->MOS9phi);
                                sPhi = 0.0;
                                sGamma = 1.0;
                                sEta = 0.0;
                                sDelta = 0.0;
                                break;
                                
                            case MOS9_PHI:
                                /* ∂Vth/∂φ = γ·[1/(2√(φ+Vbs)) - 1/(2√φ)] - δ·(Weff/Leff) */
                                sVth = model->MOS9gamma * 
                                      (1.0/(2.0*sqrt(model->MOS9phi - inst->MOS9vbs)) - 
                                       1.0/(2.0*sqrt(model->MOS9phi))) -
                                      model->MOS9delta * (inst->MOS9weff/inst->MOS9leff);
                                sPhi = 1.0;
                                sGamma = 0.0;
                                sEta = 0.0;
                                sDelta = 0.0;
                                break;
                                
                            case MOS9_ETA:
                                /* ∂Vth/∂η = Vds */
                                sVth = inst->MOS9vds;
                                sPhi = 0.0;
                                sGamma = 0.0;
                                sEta = 1.0;
                                sDelta = 0.0;
                                break;
                                
                            case MOS9_DELTA:
                                /* ∂Vth/∂δ = -(φ + Vbs)·(Weff/Leff) */
                                sVth = -(model->MOS9phi - inst->MOS9vbs) * 
                                       (inst->MOS9weff/inst->MOS9leff);
                                sPhi = 0.0;
                                sGamma = 0.0;
                                sEta = 0.0;
                                sDelta = 1.0;
                                break;
                                
                            case MOS9_KP:
                                /* ∂Id/∂KP = Id/KP */
                                sGm = inst->MOS9gm * (inst->MOS9cdrain/(model->MOS9kp * inst->MOS9cdrain));
                                sGds = inst->MOS9gds * (inst->MOS9cdrain/(model->MOS9kp * inst->MOS9cdrain));
                                sGmbs = inst->MOS9gmbs * (inst->MOS9cdrain/(model->MOS9kp * inst->MOS9cdrain));
                                break;
                                
                            case MOS9_THETA:
                                /* ∂Id/∂θ = -gm·(Vgs-Vth)·Id/[1 + θ·(Vgs-Vth)] */
                                {
                                    double Vgst = inst->MOS9vgs - inst->MOS9vth;
                                    double denom = 1.0 + model->MOS9theta * Vgst;
                                    double factor = -inst->MOS9gm * Vgst * inst->MOS9cdrain / denom;
                                    sGm = factor * inst->MOS9gm / inst->MOS9cdrain;
                                    sGds = factor * inst->MOS9gds / inst->MOS9cdrain;
                                    sGmbs = factor * inst->MOS9gmbs / inst->MOS9cdrain;
                                }
                                break;
                                
                            default:
                                sVth = 0.0;
                                sPhi = 0.0;
                                sGamma = 0.0;
                                sEta = 0.0;
                                sDelta = 0.0;
                                sGm = 0.0;
                                sGds = 0.0;
                                sGmbs = 0.0;
                                break;
                        }
                        break;
                        
                    case SEN_INSTANCE:
                        /* Instance parameter sensitivity */
                        switch(parmIndex) {
                            case MOS9_L:
                                /* ∂Id/∂L = -Id/Leff */
                                sGm = -inst->MOS9gm / inst->MOS9leff;
                                sGds = -inst->MOS9gds / inst->MOS9leff;
                                sGmbs = -inst->MOS9gmbs / inst->MOS9leff;
                                break;
                                
                            case MOS9_W:
                                /* ∂Id/∂W = Id/Weff */
                                sGm = inst->MOS9gm / inst->MOS9weff;
                                sGds = inst->MOS9gds / inst->MOS9weff;
                                sGmbs = inst->MOS9gmbs / inst->MOS9weff;
                                break;
                                
                            case MOS9_AD:
                                /* ∂Id/∂AD = 0, but ∂Cbd/∂AD = CJ·(1 - Vbd/PB)^{-MJ} */
                                sCgs = 0.0;
                                sCgd = 0.0;
                                sCgb = 0.0;
                                break;
                                
                            case MOS9_AS:
                                /* ∂Id/∂AS = 0, but ∂Cbs/∂AS = CJ·(1 - Vbs/PB)^{-MJ} */
                                sCgs = 0.0;
                                sCgd = 0.0;
                                sCgb = 0.0;
                                break;
                                
                            default:
                                sGm = 0.0;
                                sGds = 0.0;
                                sGmbs = 0.0;
                                sCgs = 0.0;
                                sCgd = 0.0;
                                sCgb = 0.0;
                                break;
                        }
                        break;
                }
                
                /* Store computed derivatives */
                inst->MOS9dvthdp[iparm] = sVth;
                inst->MOS9dphidp[iparm] = sPhi;
                inst->MOS9dgmdp[iparm] = sGm;
                inst->MOS9dgdsdp[iparm] = sGds;
                inst->MOS9dgmbsdp[iparm] = sGmbs;
                
                /* Stamp sensitivity matrix */
                MOS9stampSensitivity(inst, ckt, iparm, sGm, sGds, sGmbs, sCgs, sCgd, sCgb);
            }
        }
    }
    
    return OK;
}
```

#### 1.3 Sensitivity Matrix Stamping

```c
static void MOS9stampSensitivity(MOS9instance *inst, CKTcircuit *ckt, 
                                 int iparm, double sGm, double sGds, double sGmbs,
                                 double sCgs, double sCgd, double sCgb) {
    SENstruct *info = ckt->CKTsenInfo;
    double *rhs = ckt->CKTrhs;
    double *irhs = ckt->CKTirhs;
    double *senRhs = info->SENrhs;
    double *senIRhs = info->SENirhs;
    
    /* Stamp ∂G/∂p into sensitivity matrix */
    
    /* Drain-drain conductance derivative: ∂Gdd/∂p = ∂gds/∂p + ∂gmb/∂p */
    double sGdd = sGds + sGmbs;
    if(inst->MOS9sensDdPtr[iparm]) {
        *(inst->MOS9sensDdPtr[iparm]) += sGdd;
    }
    
    /* Drain-source conductance derivative: ∂Gds/∂p = -∂gds/∂p - ∂gm/∂p - ∂gmb/∂p */
    double sGds_deriv = -sGds - sGm - sGmbs;
    if(inst->MOS9sensDsPtr[iparm]) {
        *(inst->MOS9sensDsPtr[iparm]) += sGds_deriv;
    }
    
    /* Drain-gate conductance derivative: ∂Gdg/∂p = ∂gm/∂p */
    if(inst->MOS9sensDgPtr[iparm]) {
        *(inst->MOS9sensDgPtr[iparm]) += sGm;
    }
    
    /* Drain-bulk conductance derivative: ∂Gdb/∂p = -∂gmb/∂p */
    double sGdb = -sGmbs;
    if(inst->MOS9sensDbPtr[iparm]) {
        *(inst->MOS9sensDbPtr[iparm]) += sGdb;
    }
    
    /* Source-drain conductance derivative: ∂Gsd/∂p = -∂gds/∂p - ∂gm/∂p - ∂gmb/∂p */
    if(inst->MOS9sensSdPtr[iparm]) {
        *(inst->MOS9sensSdPtr[iparm]) += sGds_deriv;
    }
    
    /* Source-gate conductance derivative: ∂Gsg/∂p = -∂gm/∂p */
    if(inst->MOS9sensSgPtr[iparm]) {
        *(inst->MOS9sensSgPtr[iparm]) += -sGm;
    }
    
    /* Source-source conductance derivative: ∂Gss/∂p = ∂gds/∂p + ∂gm/∂p + ∂gmb/∂p */
    double sGss = sGds + sGm + sGmbs;
    if(inst->MOS9sensSsPtr[iparm]) {
        *(inst->MOS9sensSsPtr[iparm]) += sGss;
    }
    
    /* Source-bulk conductance derivative: ∂Gsb/∂p = ∂gmb/∂p */
    if(inst->MOS9sensSbPtr[iparm]) {
        *(inst->MOS9sensSbPtr[iparm]) += sGmbs;
    }
    
    /* Bulk-drain conductance derivative: ∂Gbd/∂p = 0 (simplified) */
    if(inst->MOS9sensBdPtr[iparm]) {
        *(inst->MOS9sensBdPtr[iparm]) += 0.0;
    }
    
    /* Bulk-source conductance derivative: ∂Gbs/∂p = 0 (simplified) */
    if(inst->MOS9sensBsPtr[iparm]) {
        *(inst->MOS9sensBsPtr[iparm]) += 0.0;
    }
    
    /* Bulk-bulk conductance derivative: ∂Gbb/∂p = 0 (simplified) */
    if(inst->MOS9sensBbPtr[iparm]) {
        *(inst->MOS9sensBbPtr[iparm]) += 0.0;
    }
    
    /* Stamp RHS sensitivity vector */
    int dNode = inst->MOS9dNode;
    int sNode = inst->MOS9sNode;
    int gNode = inst->MOS9gNode;
    int bNode = inst->MOS9bNode;
    
    /* Current derivatives */
    double sId = sGm * (rhs[gNode] - rhs[sNode]) + 
                 sGds * (rhs[dNode] - rhs[sNode]) + 
                 sGmbs * (rhs[bNode] - rhs[sNode]);
    
    double sIs = -sId;  /* By KCL */
    
    /* Add to sensitivity R