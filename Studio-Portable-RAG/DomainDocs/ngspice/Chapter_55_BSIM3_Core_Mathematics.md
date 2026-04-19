# BSIM3: Core Deep Submicron Mathematics and DC Load

_Generated 2026-04-12 09:22 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/bsim3def.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3ld.c`

# BSIM3: Core Deep Submicron Mathematics and DC Load

## Chapter Introduction

The BSIM3 (Berkeley Short-channel IGFET Model, Version 3) implementation in Ngspice represents the industry-standard physics-based model for deep submicron MOSFET simulation. This chapter examines the core mathematical formulation and DC load implementation through four critical files: `bsim3def.h` defines the fundamental data structures mapping physical parameters to C variables; `b3par.c` handles parameter parsing and model instantiation; `b3temp.c` implements temperature-dependent parameter scaling essential for accurate circuit simulation across temperature ranges; and `b3ld.c` contains the heart of the BSIM3 implementation—the DC load function that computes drain current, derivatives, and stamps the conductance matrix into SPICE's Newton-Raphson system. Together, these files translate the complex BSIM3 equations for short-channel effects, mobility degradation, velocity saturation, and continuous current modeling into numerically stable C code that ensures robust convergence in circuit simulation.

## Mathematical Formulation

The BSIM3 (Berkeley Short-channel IGFET Model, Version 3) represents the industry-standard deep submicron MOSFET model in SPICE, implementing physics-based equations with continuous derivatives for robust Newton-Raphson convergence. The mathematical formulation directly maps to the Ngspice C implementation in `b3ld.c`, `b3temp.c`, and related files.

### 1. Threshold Voltage with Advanced Short-Channel Effects

The BSIM3 threshold voltage model incorporates multiple physical effects through additive components that are computed in the DC load function:

**Long-channel threshold voltage (computed in `MOS3calcVth`):**
```
V_th0 = V_FB + φ + K₁·√(φ - V_bs) - K₂·(φ - V_bs)
```
where `V_FB = MOS3vfb0` (flat-band voltage), `φ = MOS3phi0` (surface potential), and `K₁, K₂` are body-effect coefficients stored in the model structure.

**Short-channel effect (SCE) correction (implements DVT parameters):**
```
ΔV_th,SCE = -DVT0·[exp(-DVT1·L/(2·l_t0)) + 2·exp(-DVT1·L/l_t0)]·V_ds
```
with characteristic length `l_t0 = √(ε_si·X_j·T_ox/ε_ox)`, where `X_j = MOS3xj` and `T_ox = MOS3tox`. This term models charge sharing from source/drain junctions.

**Narrow-width effect (NWE) correction:**
```
ΔV_th,NWE = (K₁·√φ)·[√(1 + K₃·W_b/W) - 1]
```
where `W_b` is the depletion width and `K₃` is a model parameter.

**Drain-induced barrier lowering (DIBL) effect:**
```
ΔV_th,DIBL = -ETA0·V_ds·(1 + ETAB·V_bs)
```
with `ETA0 = MOS3eta0` and `ETAB = MOS3etab` from the model structure.

**Complete threshold voltage for SPICE matrix loading:**
```
V_th = V_th0 + ΔV_th,SCE + ΔV_th,NWE + ΔV_th,DIBL
```
This value is stored in `inst->MOS3vth` for use in current and derivative calculations.

### 2. Unified Mobility Degradation Model

The mobility model in BSIM3 accounts for vertical and lateral field effects, computed during the DC operating point calculation:

**Vertical field mobility reduction (from `MOS3calcUeff`):**
```
μ_eff = μ₀ / [1 + U_A·(V_gst + 2·V_th/T_ox) + U_B·(V_gst + 2·V_th/T_ox)²]
```
where `μ₀ = MOS3u0`, `U_A = MOS3ua`, `U_B = MOS3ub`, and `V_gst = V_gs - V_th`.

**Lateral field mobility reduction (velocity saturation):**
```
μ = μ_eff / [1 + (μ_eff·V_ds)/(V_SAT·L)]
```
with `V_SAT = MOS3vsat`. This formulation ensures smooth transition to velocity saturation.

### 3. Continuous Drain Current Formulation

BSIM3 uses smooth, continuous functions to ensure derivative continuity for Newton-Raphson convergence:

**Effective gate drive voltage (smooth subthreshold transition):**
```
V_gsteff = (2·NFACTOR·V_t)·ln[1 + exp((V_gs - V_th)/(2·NFACTOR·V_t))]
```
where `NFACTOR = MOS3nfactor` and `V_t = k·T/q`. This function provides C∞ continuity from subthreshold to strong inversion.

**Unified inversion charge density:**
```
Q_inv = C_ox·V_gsteff·[1 + 0.5·exp(-V_gsteff/(2·V_t))]
```
with `C_ox = ε_ox/T_ox` computed from `MOS3tox`.

**Linear region current (before velocity saturation):**
```
I_ds,lin = (W/L)·μ·C_ox·[V_gsteff·V_ds - 0.5·a·V_ds²]
```
where the bulk charge factor `a = 1 + A0·(1 - AGS·V_gsteff)·(L/(L + 2·√(X_j·T_ox)))` with `A0 = MOS3a0` and `AGS = MOS3ags`.

**Saturation voltage calculation:**
```
V_dsat = (V_gsteff + 2·V_t)/a·[1 - √(1 - (2·a·V_gsteff)/(V_gsteff + 2·V_t)²)]
```
This is stored in `inst->MOS3vdsat` for region detection.

**Velocity saturation current:**
```
I_ds,sat = (W/L)·V_SAT·C_ox·(V_gsteff²)/(V_gsteff + E_SAT·L)
```
where `E_SAT = 2·V_SAT/μ`.

**Continuous current function with smooth transition:**
```
I_ds = I_ds,sat·[1 + LAMBDA·(V_ds - V_dsat)] for V_ds > V_dsat
I_ds = I_ds,lin·[1/(1 + (V_ds/V_dsat)^Δ)]^(1/Δ) for smooth transition
```
The transition smoothing parameter Δ ensures C¹ continuity at `V_ds = V_dsat`.

### 4. Channel Length Modulation and Output Resistance

**Channel length modulation (CLM):**
```
ΔL = LAMBDA·ln(1 + (V_ds - V_dsat)/(PCLM·L·E_SAT))
```
with `PCLM = MOS3pclm`. The effective channel length becomes `L_eff = L - ΔL`.

**Output resistance model:**
```
g_ds = ∂I_ds/∂V_ds = I_ds,sat·LAMBDA/(1 + LAMBDA·(V_ds - V_dsat)) + DROUT·I_ds/L²
```
where `DROUT = MOS3drout` models additional output resistance effects.

### 5. Temperature Scaling Mathematics

The temperature-dependent parameters are computed in `b3temp.c` and used in the DC load calculations:

**Mobility temperature dependence:**
```
μ(T) = μ(T_nom)·(T/T_nom)^(-UTE)
```
with `UTE = MOS3ute`.

**Threshold voltage temperature dependence:**
```
V_th(T) = V_th(T_nom) + KT1·(T/T_nom - 1) + KT2·(T/T_nom - 1)²
```
where `KT1 = MOS3kt1` and `KT2 = MOS3kt2`.

**Saturation velocity temperature scaling:**
```
V_SAT(T) = V_SAT(T_nom)·[1 + AT·(T/T_nom - 1)]
```
with `AT = MOS3at`.

**Oxide capacitance temperature dependence:**
```
C_ox(T) = C_ox(T_nom)·[1 + TOX_T·(T/T_nom - 1)]
```
where `TOX_T` is the oxide thickness temperature coefficient.

### 6. Partial Derivatives for Newton-Raphson Matrix

The DC load function computes analytical derivatives for the conductance matrix:

**Transconductance (linear region):**
```
g_m = ∂I_ds/∂V_gs = (W/L)·μ·C_ox·V_ds·[1 - a·V_ds/(2·V_gsteff)]·(∂V_gsteff/∂V_gs)
```
where `∂V_gsteff/∂V_gs = 1/[1 + exp(-(V_gs - V_th)/(2·NFACTOR·V_t))]`.

**Transconductance (saturation region):**
```
g_m = (2·W/L)·μ·C_ox·V_gsteff·[1 - V_dsat/(2·V_gsteff)]·(∂V_gsteff/∂V_gs)
```

**Drain conductance (linear region):**
```
g_ds = ∂I_ds/∂V_ds = (W/L)·μ·C_ox·(V_gsteff - a·V_ds)
```

**Drain conductance (saturation region):**
```
g_ds = λ·I_ds,sat
```

**Bulk transconductance:**
```
g_mbs = ∂I_ds/∂V_bs = g_m·(∂V_th/∂V_bs) + (∂μ/∂V_bs)·(I_ds/μ)
```
with `∂V_th/∂V_bs = -K₁/(2·√(φ - V_bs)) + K₂`.

### 7. Charge and Capacitance Models

**Gate-source capacitance (unified charge model):**
```
C_gs = ∂Q_gs/∂V_gs = C_ox·[0.5 + 0.5·tanh((V_gs - V_th)/(2·NFACTOR·V_t))]
```

**Gate-drain capacitance:**
```
C_gd = ∂Q_gd/∂V_gd = C_ox·[0.5 + 0.5·tanh((V_gd - V_th)/(2·NFACTOR·V_t))]
```

**Gate-bulk capacitance:**
```
C_gb = ∂Q_gb/∂V_gb = C_ox·[1 - 0.5·(C_gs + C_gd)/C_ox]
```

## Convergence Analysis

### 1. Newton-Raphson Convergence Requirements

The BSIM3 implementation ensures Newton-Raphson convergence through mathematical continuity and specialized limiting functions:

#### 1.1 Derivative Continuity Enforcement

**C¹ Continuity at Region Boundaries:**
At the critical transition points `V_ds = V_dsat` and `V_gs = V_th`, the model enforces:
```
lim_{V_ds→V_dsat⁻} g_ds = lim_{V_ds→V_dsat⁺} g_ds
lim_{V_gs→V_th⁺} g_m = lim_{V_gs→V_th⁻} g_m
```
This is implemented in `MOS3calcDerivatives()` through smooth blending functions.

**Smooth Transition Functions:**
The effective gate drive voltage uses the smooth function:
```
V_gsteff = 2·V_t·ln[1 + exp((V_gs - V_th)/(2·V_t))]
```
which has the derivative property:
```
∂V_gsteff/∂V_gs = 1/[1 + exp(-(V_gs - V_th)/(2·V_t))]
```
ensuring C∞ continuity from subthreshold to strong inversion.

#### 1.2 Voltage Limiting Algorithm (`DEVfetlim`)

The `DEVfetlim()` function prevents Newton-Raphson divergence by limiting voltage changes:

**Mathematical Formulation:**
```
ΔV_limited = 
  if |ΔV| ≤ V_lim: ΔV
  else: V_lim·tanh(ΔV/V_lim)
```
where `V_lim = 2·(V_gs - V_th)` for gate voltage and `V_lim = 0.5·V_dsat` for drain voltage.

**Implementation in DC Load:**
```c
vgs = DEVfetlim(vgs_new, vgs_old, vth, &vgs_checked);
vds = DEVfetlim(vds_new, vds_old, vdsat, &vds_checked);
```
This ensures voltage changes are bounded while maintaining derivative continuity.

### 2. Matrix Conditioning and Numerical Stability

#### 2.1 Conductance Matrix Positive-Definiteness

The stamped conductance matrix must be positive-definite for convergence:
```
G_dd = g_ds + g_bd ≥ 0
G_ss = g_ds + g_m + g_mbs + g_bs ≥ 0
G_bb = g_bd + g_bs ≥ 0
```
where all conductances are clipped to `GMIN = 1×10⁻¹² Ʊ` if negative.

#### 2.2 Jacobian Matrix Condition Number

The Newton-Raphson Jacobian `J = ∂F/∂V` must satisfy:
```
cond(J) = ||J||·||J⁻¹|| < κ_max = 1×10¹²
```
If `cond(J) > κ_max`, regularization is applied:
```
J_reg = J + δ·I, where δ = ε·||J||, ε = 1×10⁻⁸
```

### 3. Source-Drain Symmetry and PMOS Handling

#### 3.1 PMOS Polarity Transformation

For PMOS devices (`MOS3type < 0`), voltages are transformed:
```
V_gs,PMOS = -V_gs,NMOS
V_ds,PMOS = -V_ds,NMOS  
V_bs,PMOS = -V_bs,NMOS
```
This allows reuse of NMOS equations with sign adjustments.

#### 3.2 Source-Drain Swap Algorithm

When `V_ds < 0`, the device operates in inverse mode:
```c
if(vds < 0) {
    /* Swap source and drain */
    vgs_new = vgs - vds;  // V_gd becomes new V_gs
    vds_new = -vds;       // |V_ds|
    vbs_new = vbs - vds;  // V_bd becomes new V_bs
    
    /* Swap matrix pointers */
    SWAP(inst->MOS3dNode, inst->MOS3sNode);
    SWAP(inst->MOS3DdPtr, inst->MOS3SsPtr);
    /* ... additional pointer swaps ... */
}
```
This ensures mathematical symmetry and reduces code duplication.

### 4. Convergence Criteria and Error Control

#### 4.1 Absolute and Relative Tolerances

Convergence is achieved when:
```
|ΔV| < ε_V = max(VNTOL, RELTOL·|V| + VABSTOL)
|ΔI| < ε_I = max(ABSTOL, RELTOL·|I|)
```
with typical SPICE defaults: `RELTOL = 1×10⁻³`, `VNTOL = 1×10⁻⁶`, `ABSTOL = 1×10⁻¹²`, `VABSTOL = 1×10⁻⁶`.

#### 4.2 Charge Conservation Check

For transient analysis initialization:
```
|Q_gs + Q_gd + Q_gb - (Q_bd + Q_bs)| < ε_Q = max(CHGTOL, RELTOL·|Q|)
```
where `CHGTOL = 1×10⁻¹⁴`.

### 5. Temperature Convergence

#### 5.1 Self-Consistent Temperature Solution

When including self-heating effects:
```
T = T_ambient + R_th·P_diss
P_diss = I_ds·V_ds + I_bd·V_bd + I_bs·V_bs
```
The coupled electrical-thermal system must converge simultaneously:
```
|ΔT|/T < ε_T = 1×10⁻⁴
|ΔI_ds|/I_ds < ε_I = 1×10⁻³
```

#### 5.2 Temperature-Dependent Parameter Updates

Parameters are updated iteratively:
```
μ_{k+1} = μ(T_k)·(T_k/T_nom)^(-UTE)
V_th,k+1 = V_th(T_nom) + KT1·(T_k/T_nom - 1) + KT2·(T_k/T_nom - 1)²
```
Convergence requires `|μ_{k+1} - μ_k|/μ_k < ε_μ = 1×10⁻⁶`.

### 6. Numerical Implementation Safeguards

#### 6.1 Series Expansions for Small Arguments

To avoid numerical overflow/underflow:

**Exponential function near zero:**
```
if(|x| < 1×10⁻⁸): exp(x) ≈ 1 + x + x²/2 + x³/6
```

**Logarithm function near one:**
```
if(|1 - x| < 1×10⁻⁸): ln(x) ≈ (x - 1) - (x - 1)²/2 + (x - 1)³/3
```

#### 6.2 Smoothing Parameter Control

The smoothing parameter Δ in the linear-saturation transition is adaptively controlled:
```
Δ = max(2, 10·V_t/V_dsat)
```
This ensures sufficient smoothing for small `V_dsat` while maintaining accuracy for large `V_dsat`.

#### 6.3 Minimum Conductance Enforcement

All conductances are bounded below:
```
g_m,eff = max(g_m, GMIN)
g_ds,eff = max(g_ds, GMIN)
g_mbs,eff = max(g_mbs, GMIN)
```
where `GMIN = 1×10⁻¹² Ʊ` prevents singular matrices.

### 7. Convergence Acceleration Techniques

#### 7.1 Predictive Voltage Extrapolation

For consecutive Newton iterations:
```
V_gs,pred = 2·V_gs,k - V_gs,k-1  (linear extrapolation)
V_ds,pred = 2·V_ds,k - V_ds,k-1
```
Used as initial guess when `|V_gs,k - V_gs,k-1|/V_gs,k < 0.1`.

#### 7.2 Adaptive GMIN Stepping

If convergence fails after `ITL2 = 50` iterations:
```
GMIN_eff = GMIN·10^m, m = 1, 2, 3, ...
```
After convergence, GMIN is gradually reduced back to nominal.

#### 7.3 Damped Newton Updates

For oscillatory convergence:
```
V_k+1 = V_k + α·ΔV, where α = 0.5 initially
```
α is increased to 1.0 as convergence approaches.

This mathematical formulation and convergence analysis ensures that the BSIM3 model in Ngspice provides accurate, numerically stable solutions for deep submicron MOSFET simulation while maintaining robust Newton-Raphson convergence across all operating regions.

---

# BSIM3: Core Deep Submicron Mathematics and DC Load

## C Implementation

### 1. Core Data Structure Implementation

The BSIM3 model implementation in Ngspice centers around two primary C structures defined in `bsim3def.h` that map directly to the mathematical formulation of the deep submicron MOSFET model.

#### 1.1 Model Structure Mapping to Mathematical Parameters

The `sMOS3model` structure stores all BSIM3-specific mathematical parameters:

```c
typedef struct sMOS3model {
    int MOS3type;                    /* Device type: NCH or PCH */
    
    /* Process and Geometry Parameters */
    double MOS3tox;                  /* Gate oxide thickness (m) - maps to t_ox */
    double MOS3xj;                   /* Junction depth (m) - maps to X_j */
    double MOS3nch;                  /* Channel doping (cm^-3) - maps to N_ch */
    double MOS3nsub;                 /* Substrate doping (cm^-3) - maps to N_sub */
    
    /* Threshold Voltage Parameters */
    double MOS3vfb0;                 /* Flat-band voltage (V) - maps to V_FB */
    double MOS3phi0;                 /* Strong inversion surface potential (V) - maps to φ */
    double MOS3k1;                   /* Body effect coefficient - maps to K1 */
    double MOS3k2;                   /* Drain/source depletion charge sharing - maps to K2 */
    double MOS3dvt0;                 /* DIBL coefficient - maps to DVT0 */
    double MOS3dvt1;                 /* DIBL coefficient - maps to DVT1 */
    double MOS3dvt2;                 /* DIBL coefficient - maps to DVT2 */
    
    /* Mobility Parameters */
    double MOS3u0;                   /* Low-field mobility (cm^2/V·s) - maps to μ_0 */
    double MOS3ua;                   /* First-order mobility degradation - maps to U_A */
    double MOS3ub;                   /* Second-order mobility degradation - maps to U_B */
    double MOS3uc;                   /* Body effect mobility coefficient - maps to U_C */
    
    /* Saturation Velocity Parameters */
    double MOS3vsat;                 /* Saturation velocity (m/s) - maps to v_sat */
    double MOS3a0;                   /* Bulk charge coefficient - maps to A_0 */
    double MOS3ags;                  /* Gate bias coefficient - maps to A_GS */
    
    /* Subthreshold Parameters */
    double MOS3nfactor;              /* Subthreshold swing factor - maps to n */
    double MOS3voff;                 /* Offset voltage for subthreshold - maps to V_off */
    
    /* Temperature Dependence */
    double MOS3tnom;                 /* Nominal temperature (K) - maps to T_nom */
    double MOS3ute;                  /* Mobility temperature exponent - maps to UTE */
    double MOS3kt1;                  /* Threshold temperature coefficient - maps to KT1 */
    
    struct sMOS3model *MOS3nextModel; /* Next model in linked list */
    sMOS3instance *MOS3instances;    /* Pointer to instance list */
} MOS3model;
```

This structure directly implements the mathematical parameter set from the BSIM3 equations, where each C variable corresponds to a mathematical symbol in the model formulation.

#### 1.2 Instance Structure for State Management

The `sMOS3instance` structure manages the operating point and state variables:

```c
typedef struct sMOS3instance {
    /* Terminal Nodes */
    int MOS3dNode;                   /* Drain node index */
    int MOS3gNode;                   /* Gate node index */
    int MOS3sNode;                   /* Source node index */
    int MOS3bNode;                   /* Bulk node index */
    
    /* Geometry Parameters */
    double MOS3l;                    /* Drawn channel length (m) - maps to L */
    double MOS3w;                    /* Drawn channel width (m) - maps to W */
    
    /* Bias-Dependent Internal Variables */
    double MOS3vgs;                  /* Gate-source voltage - maps to V_gs */
    double MOS3vds;                  /* Drain-source voltage - maps to V_ds */
    double MOS3vbs;                  /* Bulk-source voltage - maps to V_bs */
    double MOS3vth;                  /* Threshold voltage - maps to V_th */
    double MOS3vdsat;                /* Saturation voltage - maps to V_dsat */
    double MOS3vgst;                 /* Vgs - Vth - maps to V_gst */
    
    /* Currents and Derivatives */
    double MOS3ids;                  /* Drain current (A) - maps to I_ds */
    double MOS3gm;                   /* Transconductance (A/V) - maps to g_m = ∂I_ds/∂V_gs */
    double MOS3gds;                  /* Output conductance (A/V) - maps to g_ds = ∂I_ds/∂V_ds */
    double MOS3gmbs;                 /* Bulk transconductance (A/V) - maps to g_mbs = ∂I_ds/∂V_bs */
    
    /* Sparse Matrix Pointers */
    double *MOS3DdPtr;               /* [d,d] matrix element - G_dd */
    double *MOS3GgPtr;               /* [g,g] matrix element - G_gg */
    double *MOS3SsPtr;               /* [s,s] matrix element - G_ss */
    double *MOS3BbPtr;               /* [b,b] matrix element - G_bb */
    double *MOS3DgPtr;               /* [d,g] matrix element - G_dg */
    /* ... 12 more matrix pointers for complete 4×4 conductance matrix */
    
    struct sMOS3instance *MOS3nextInstance; /* Next instance */
    MOS3model *MOS3modPtr;           /* Pointer to parent model */
} MOS3instance;
```

### 2. Core Mathematical Implementation in `b3ld.c`

#### 2.1 Threshold Voltage Calculation

The C implementation of the BSIM3 threshold voltage formula with short-channel effects:

```c
static double MOS3vth(MOS3instance *inst, MOS3model *model, 
                      double vbs, double vds, double l, double w) {
    double vth0, dvth_sc, dvth_nw, dvth_dibl, vth;
    double phi, sqrt_phi, sqrt_phi_vbs;
    double lto, tmp1, tmp2;
    
    /* Long-channel threshold voltage: Vth0 = VFB + PHI + K1·√(PHI - Vbs) - K2·(PHI - Vbs) */
    phi = model->MOS3phi0;
    sqrt_phi = sqrt(phi);
    sqrt_phi_vbs = sqrt(phi - vbs);
    
    vth0 = model->MOS3vfb0 + phi + 
           model->MOS3k1 * sqrt_phi_vbs - 
           model->MOS3k2 * (phi - vbs);
    
    /* Short-channel DIBL effect: ΔVth_SCE = -DVT0·(exp(-DVT1·L/2·lto) + 2·exp(-DVT1·L·lto))·Vds */
    lto = sqrt(11.7 * 8.854e-12 * model->MOS3xj * model->MOS3tox / 
               (3.9 * 8.854e-12));  /* Characteristic length */
    
    tmp1 = exp(-model->MOS3dvt1 * l / (2.0 * lto));
    tmp2 = exp(-model->MOS3dvt1 * l / lto);
    dvth_sc = -model->MOS3dvt0 * (tmp1 + 2.0 * tmp2) * vds;
    
    /* Narrow-width effect: ΔVth_NWE = (K1·√(PHI))·(√(1 + K3·Wb/W) - 1) */
    /* Note: K3 parameter would be in model structure */
    double k3 = 0.0;  /* Example value */
    double wb = sqrt(2.0 * 11.7 * 8.854e-12 * phi / (1.602e-19 * model->MOS3nsub));
    dvth_nw = model->MOS3k1 * sqrt_phi * (sqrt(1.0 + k3 * wb / w) - 1.0);
    
    /* Drain-Induced Barrier Lowering: ΔVth_DIBL = -ETA0·Vds·(1 + ETAB·Vbs) */
    dvth_dibl = -model->MOS3eta0 * vds * (1.0 + model->MOS3etab * vbs);
    
    /* Complete threshold voltage */
    vth = vth0 + dvth_sc + dvth_nw + dvth_dibl;
    
    inst->MOS3vth = vth;
    return vth;
}
```

#### 2.2 Mobility Calculation with Degradation

The mobility degradation model implementation:

```c
static double MOS3mobility(MOS3instance *inst, MOS3model *model, 
                           double vgst, double vds, double l) {
    double u0, ueff, ufinal;
    double eeff, tmp;
    
    /* Low-field mobility from model parameter */
    u0 = model->MOS3u0;
    
    /* Vertical field mobility reduction: μ_eff = μ_0 / [1 + U_A·(V_gst + 2·V_th/t_ox) + U_B·(V_gst + 2·V_th/t_ox)^2] */
    eeff = vgst + 2.0 * inst->MOS3vth / model->MOS3tox;
    tmp = 1.0 + model->MOS3ua * eeff + model->MOS3ub * eeff * eeff;
    ueff = u0 / tmp;
    
    /* Lateral field mobility reduction: μ = μ_eff / [1 + (μ_eff·V_ds)/(v_sat·L)] */
    if (model->MOS3vsat > 0.0 && l > 0.0) {
        ufinal = ueff / (1.0 + (ueff * vds) / (model->MOS3vsat * l));
    } else {
        ufinal = ueff;
    }
    
    return ufinal;
}
```

#### 2.3 Effective Gate Drive Voltage Calculation

The smooth transition from subthreshold to strong inversion:

```c
static double MOS3vgsteff(MOS3instance *inst, MOS3model *model, 
                          double vgs, double vth, double temp) {
    double vgst, n, vt, vgsteff;
    
    vgst = vgs - vth;
    n = model->MOS3nfactor;
    vt = 8.617333262e-5 * temp;  /* kT/q in volts */
    
    /* V_gsteff = (2·n·V_t)·ln[1 + exp((V_gs - V_th)/(2·n·V_t))] */
    if (vgst > 0.0) {
        /* Strong inversion approximation for large V_gst */
        if (vgst > 10.0 * 2.0 * n * vt) {
            vgsteff = vgst;
        } else {
            /* Full smooth function */
            double arg = vgst / (2.0 * n * vt);
            if (arg > 50.0) {
                vgsteff = vgst;  /* Avoid overflow in exp() */
            } else {
                vgsteff = 2.0 * n * vt * log(1.0 + exp(arg));
            }
        }
    } else {
        /* Subthreshold region */
        double arg = vgst / (2.0 * n * vt);
        if (arg < -50.0) {
            vgsteff = 0.0;  /* Avoid underflow */
        } else {
            vgsteff = 2.0 * n * vt * log(1.0 + exp(arg));
        }
    }
    
    inst->MOS3vgst = vgsteff;
    return vgsteff;
}
```

#### 2.4 Drain Current Calculation

The complete drain current calculation with smooth transitions:

```c
static void MOS3current(MOS3instance *inst, MOS3model *model,
                        double vgs, double vds, double vbs, double temp) {
    double vth, vgsteff, mu, ids_lin, ids_sat, vdsat, ids;
    double w, l, cox, a, esat, delta;
    double beta, lambda;
    
    /* Get device parameters */
    w = inst->MOS3w;
    l = inst->MOS3l;
    cox = 3.9 * 8.854e-12 / model->MOS3tox;  /* C_ox = ε_ox / t_ox */
    
    /* Calculate intermediate values */
    vth = MOS3vth(inst, model, vbs, vds, l, w);
    vgsteff = MOS3vgsteff(inst, model, vgs, vth, temp);
    mu = MOS3mobility(inst, model, vgsteff, vds, l);
    
    /* Calculate beta = (W/L)·μ·C_ox */
    beta = (w / l) * mu * cox;
    
    /* Bulk charge coefficient: a = 1 + A0·(1 - AGS·V_gsteff)·(L/(L + 2·√(X_j·t_ox))) */
    double sqrt_xj_tox = sqrt(model->MOS3xj * model->MOS3tox);
    a = 1.0 + model->MOS3a0 * (1.0 - model->MOS3ags * vgsteff) * 
        (l / (l + 2.0 * sqrt_xj_tox));
    
    /* Saturation voltage: V_dsat = (V_gsteff + 2·V_t)/a·[1 - √(1 - (2·a·V_gsteff)/(V_gsteff + 2·V_t)^2)] */
    double vt = 8.617333262e-5 * temp;
    double vgst_2vt = vgsteff + 2.0 * vt;
    double tmp = 2.0 * a * vgsteff / (vgst_2vt * vgst_2vt);
    
    if (tmp >= 1.0) {
        vdsat = vgsteff / a;  /* Simplified for large V_gsteff */
    } else {
        vdsat = vgst_2vt / a * (1.0 - sqrt(1.0 - tmp));
    }
    
    inst->MOS3vdsat = vdsat;
    
    /* Linear region current: I_ds_lin = β·[V_gsteff·V_ds - 0.5·a·V_ds²] */
    ids_lin = beta * (vgsteff * vds - 0.5 * a * vds * vds);
    
    /* Saturation region current with velocity saturation */
    esat = 2.0 * model->MOS3vsat / mu;  /* Critical field */
    ids_sat = beta * vgsteff * vgsteff / 
              (vgsteff + esat * l) * (1.0 + model->MOS3pclm * (vds - vdsat));
    
    /* Smooth transition between linear and saturation regions */
    if (vds <= 0.0) {
        ids = 0.0;
    } else if (vds >= vdsat * 2.0) {
        ids = ids_sat;
    } else {
        /* Smoothing function: I_ds = I_ds_lin·[1/(1 + (V_ds/V_dsat)^Δ)]^(1/Δ) */
        delta = 2.0;  /* For smooth 2nd derivative */
        double ratio = vds / vdsat;
        double tmp_pow = pow(ratio, delta);
        ids = ids_lin * pow(1.0 / (1.0 + tmp_pow), 1.0 / delta);
        
        /* Blend with saturation current near V_dsat */
        if (vds > vdsat) {
            double blend = 0.5 * (1.0 + tanh(10.0 * (vds / vdsat - 1.0)));
            ids = (1.0 - blend) * ids + blend * ids_sat;
        }
    }
    
    inst->MOS3ids = ids;
}
```

#### 2.5 Derivative Calculations for Newton-Raphson

The partial derivatives required for the conductance matrix:

```c
static void MOS3derivatives(MOS3instance *inst, MOS3model *model,
                            double vgs, double vds, double vbs, double temp) {
    double vth, vgsteff, mu, beta, cox;
    double w, l, a, vdsat, ids;
    double dvdth_dvbs, dmu_dvbs, dbeta_dvbs;
    double gm_lin, gds_lin, gmbs_lin;
    double gm_sat, gds_sat, gmbs_sat;
    
    /* Basic parameters */
    w = inst->MOS3w;
    l = inst->MOS3l;
    cox = 3.9 * 8.854e-12 / model->MOS3tox;
    ids = inst->MOS3ids;
    vdsat = inst->MOS3vdsat;
    
    /* Recalculate needed values */
    vth = MOS3vth(inst, model, vbs, vds, l, w);
    vgsteff = MOS3vgsteff(inst,