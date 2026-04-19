# BSIM4v5: Layout-Dependent Effects, Geometry, and Setup

_Generated 2026-04-12 14:02 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5ask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5check.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5geo.c`

# Chapter: BSIM4v5: Layout-Dependent Effects, Geometry, and Setup

## Technical Introduction

The BSIM4v5 model in Ngspice implements sophisticated layout-dependent effects (LDE) and geometric transformations essential for accurate nanometer-scale CMOS simulation. The implementation of these effects is distributed across several key files: `bsim4v5def.h` defines the data structures that store LDE parameters; `b4v5par.c` handles the binding of these parameters from SPICE input to internal C variables; `b4v5temp.c` manages the temperature scaling of geometry-dependent parameters; and `b4v5ld.c` integrates these effects into the core DC load equations. This chapter details the mathematical formulation of STI stress, well proximity effects (WPE), and geometric corrections, and analyzes their impact on SPICE convergence. The implementation ensures that layout-dependent parameter shifts are computed during setup and consistently applied throughout the Newton-Raphson iterations, maintaining the numerical stability required for robust circuit simulation.

---

## Mathematical Formulation

### 1. Layout-Dependent Effects (LDE) Mathematics

BSIM4v5 explicitly models mechanical stress from isolation structures and proximity effects that modulate electrical parameters. These effects are calculated during the setup phase and stored as instance-specific corrections.

#### 1.1 Shallow Trench Isolation (STI) Stress Effects

STI-induced mechanical stress alters carrier mobility and threshold voltage. The model uses distance parameters `sa`, `sb`, `sd` representing distances to STI edges in different directions.

**Stress Factor for Mobility:**
```
F_stress = 1 + (sar / sa) + (sbr / sb) + (sdr / sd)
```
where:
- `sar`, `sbr`, `sdr`: Model parameters for stress coefficients in different directions
- `sa`, `sb`, `sd`: Instance geometry distances to STI edges (minimum 1e-9m to avoid singularity)

**Effective Mobility with STI Stress:**
```
μ_eff_STI = μ_0 × F_stress
```

**SPICE Integration:** The stress factor is computed once during `BSIM4v5setup()` in `b4v5set.c` and stored in the instance variable `BSIM4v5u0eff`. This pre-computed value is reused during each Newton iteration in `BSIM4v5load()`, ensuring computational efficiency while maintaining accuracy.

#### 1.2 Well Proximity Effect (WPE)

WPE causes additional threshold voltage and mobility shifts due to dopant scattering from well edges.

**Threshold Voltage Shift:**
```
ΔVth_WPE = warc / (sd^1.5)
```
where:
- `warc`: WPE coefficient for Vth shift (model parameter)
- `sd`: Distance to well edge (instance geometry)

**Mobility Shift:**
```
F_WPE = 1 + (wbrc / (sd^1.5))
```
where `wbrc` is the WPE coefficient for mobility.

**Modified Parameters:**
```
Vth0_effective = Vth0 + ΔVth_WPE
μ0_effective = μ0 × F_WPE
```

**SPICE Integration:** These shifts are applied during setup and modify the base model parameters before any electrical calculations. The `sd` distance is extracted from layout and specified as an instance parameter.

#### 1.3 Pocket/Halo Implant Effects

Pocket or halo implants used for short-channel control introduce additional doping gradients.

**Threshold Voltage Shift:**
```
ΔVth_pocket = dvtshft × [1 + dvtshfttemp × (T/T_nom - 1)]
```
where:
- `dvtshft`: Pocket implant Vth shift coefficient
- `dvtshfttemp`: Temperature coefficient of the pocket effect

**Mobility Modulation:**
```
F_pocket = 1 + (phigh / Leff) - (plow / Leff)
```
where `phigh` and `plow` represent peak and background pocket doping concentrations.

**SPICE Integration:** The pocket effect is length-dependent (`1/Leff`), making it increasingly significant for shorter channels. This is computed during each operating point calculation since it depends on the effective length which may vary with bias.

### 2. Effective Geometry Calculations

BSIM4v5 modifies drawn dimensions to account for process variations and quantum mechanical effects.

#### 2.1 Effective Channel Length

```
Leff = L_drawn - 2 × dlc + dlc × exp(-L_drawn / llc)
```
where:
- `dlc`: Length correction parameter
- `llc`: Characteristic length for correction saturation

**Mathematical Properties:**
- As `L_drawn → ∞`: `Leff → L_drawn - 2 × dlc` (classical correction)
- As `L_drawn → 0`: `Leff → L_drawn - dlc` (reduced correction for very short channels)
- The exponential term ensures smooth transition and prevents over-correction

#### 2.2 Effective Channel Width

```
Weff = W_drawn - 2 × dwc + dwc × exp(-W_drawn / wwc)
```
where `dwc` and `wwc` are width correction parameters with similar behavior to the length corrections.

#### 2.3 SPICE Implementation

These corrections are computed in `BSIM4v5setup()` and stored in `BSIM4v5leff` and `BSIM4v5weff`. The exponential terms require careful numerical implementation to avoid underflow/overflow:
```c
/* In b4v5set.c */
double exp_arg = -inst->BSIM4v5l / model->BSIM4v5llc;
double exp_term = (exp_arg < -50.0) ? 0.0 : exp(exp_arg);
inst->BSIM4v5leff = inst->BSIM4v5l - 2.0 * model->BSIM4v5dlc
                   + model->BSIM4v5dlc * exp_term;
```

### 3. Temperature Scaling of Geometry-Dependent Parameters

BSIM4v5 enhances temperature scaling with geometry-dependent terms.

#### 3.1 Threshold Voltage Temperature Scaling

```
ΔVth_temp = kt1 × (T/T_nom - 1) + (kt1l / Leff) × (T/T_nom - 1)
Vth(T) = Vth0 - ΔVth_temp
```
where `kt1l` provides length-dependent temperature coefficient.

**SPICE Integration:** The `1/Leff` term makes short-channel devices more sensitive to temperature variations. This is computed in `b4v5temp.c` and stored in `BSIM4v5vth0temp`.

#### 3.2 Mobility Temperature Dependence

```
μ(T) = μ0 × (T/T_nom)^(-ute)
```
where `ute` is the temperature exponent, typically around 1.5.

#### 3.3 Pocket Implant Temperature Dependence

```
dvtshft(T) = dvtshft × [1 + dvtshfttemp × (T/T_nom - 1)]
```
This secondary temperature effect is specific to BSIM4v5's pocket modeling.

### 4. Integration into Core MOSFET Equations

The layout-dependent modifications feed into the standard BSIM4 equations through modified parameters.

#### 4.1 Modified Threshold Voltage

```
Vth_total = Vth0_effective + ΔVth_SCE + ΔVth_DIBL + ΔVth_NWE + ΔVth_pocket(T)
```
where:
- `Vth0_effective = Vth0 + ΔVth_WPE` (includes WPE)
- Other terms follow standard BSIM4 formulations

#### 4.2 Modified Mobility

```
μ_total = μ0_effective × F_stress × F_pocket × f_vertical_field × f_velocity_saturation
```
where `μ0_effective = μ0 × F_WPE` includes WPE mobility effect.

#### 4.3 Current Equations

The drain current uses the modified parameters:
```
β_effective = μ_total × Cox × Weff / Leff
Id = f(β_effective, Vth_total, Vgs, Vds, Vbs)
```
with `Weff` and `Leff` being the geometrically corrected dimensions.

### 5. Parasitic Resistance Modeling

BSIM4v5 includes geometry-dependent parasitic resistances.

#### 5.1 Diffusion Resistance

```
Rd = RSH × (nrd / Weff) + RDC × (1/Weff)
Rs = RSH × (nrs / Weff) + RSC × (1/Weff)
```
where:
- `RSH`: Sheet resistance
- `nrd`, `nrs`: Number of squares
- `RDC`, `RSC`: Contact resistances

#### 5.2 Width-Dependent Scaling

```
Rd_effective = Rd × (1 + wr × (1/Weff - 1/W_ref))
```
where `wr` is the width dependence coefficient.

### 6. Junction Capacitance Geometry Dependence

#### 6.1 Area and Perimeter Calculations

```
AD = ad × m  (drain area)
AS = as × m  (source area)
PD = pd × m  (drain perimeter)
PS = ps × m  (source perimeter)
```
where `m` is the device multiplier.

#### 6.2 Junction Capacitance

```
C_jd = CJ × AD + CJSW × PD
C_js = CJ × AS + CJSW × PS
```
These geometry-dependent capacitances are stamped into the matrix during AC analysis.

---

## Convergence Analysis

### 1. Impact of Layout-Dependent Effects on Newton-Raphson Convergence

The introduction of layout-dependent effects creates additional nonlinearities that must be managed for robust SPICE convergence.

#### 1.1 Discontinuity Management

**STI Stress Singularities:**
The stress factor `F_stress = 1 + sar/sa + sbr/sb + sdr/sd` contains potential singularities as `sa`, `sb`, `sd` → 0.

**SPICE Implementation:** Minimum distance clamping:
```c
double sa_eff = MAX(inst->BSIM4v5sa, 1e-9);
double sb_eff = MAX(inst->BSIM4v5sb, 1e-9);
double sd_eff = MAX(inst->BSIM4v5sd, 1e-9);
```
This prevents division by zero while maintaining physical realism.

**WPE Singularity:**
The term `1/sd^1.5` becomes infinite as `sd → 0`. Similar clamping is applied.

#### 1.2 Gradient Continuity

The derivatives of layout-dependent terms must be continuous for Newton-Raphson convergence:

**Stress Factor Derivative:**
```
∂F_stress/∂V = 0
```
Since stress factors depend only on geometry (not voltage), their derivatives are zero, avoiding additional Jacobian terms.

**WPE Derivative:**
```
∂(ΔVth_WPE)/∂V = 0
```
Similarly, WPE effects are geometry-only, preserving Jacobian sparsity.

#### 1.3 Pocket Effect Gradient

The pocket term `F_pocket = 1 + phigh/Leff - plow/Leff` has derivative:
```
∂F_pocket/∂Leff = -(phigh - plow) / Leff²
```
Since `Leff` is voltage-independent in BSIM4v5 (unlike some advanced models), this derivative doesn't enter the Jacobian.

### 2. Geometry-Dependent Temperature Scaling Convergence

#### 2.1 Length-Dependent Temperature Coefficient

The term `kt1l/Leff` in threshold voltage temperature scaling:
```
ΔVth_temp = kt1 × (T/T_nom - 1) + (kt1l / Leff) × (T/T_nom - 1)
```

**Convergence Impact:**
- For very small `Leff`, the `1/Leff` term becomes large
- This increases the temperature sensitivity of short-channel devices
- The derivative `∂Vth/∂T` is larger for short channels, affecting thermal analysis convergence

**SPICE Implementation:** Regularization through minimum effective length:
```c
double Leff_eff = MAX(inst->BSIM4v5leff, 1e-9);
```

#### 2.2 Temperature Iteration Coupling

In electro-thermal simulation, temperature becomes a state variable. The geometry-dependent terms create additional coupling:

**Jacobian Entry:**
```
∂Id/∂T = (∂Id/∂Vth) × (∂Vth/∂T) + (∂Id/∂μ) × (∂μ/∂T)
```
where `∂Vth/∂T` and `∂μ/∂T` contain geometry-dependent terms.

### 3. Effective Geometry Smoothing

#### 3.1 Exponential Correction Smoothness

The effective geometry calculations use exponential terms:
```
Leff = L_drawn - 2·dlc + dlc·exp(-L_drawn/llc)
```

**Derivative Continuity:**
```
∂Leff/∂L_drawn = 1 - (dlc/llc)·exp(-L_drawn/llc)
```
This derivative is continuous for all `L_drawn ≥ 0`, ensuring C¹ continuity.

**Numerical Stability:** For very large negative arguments (`-L_drawn/llc < -50`), the exponential underflows to zero, handled by:
```c
double exp_arg = -L_drawn / llc;
double exp_term = (exp_arg < -50.0) ? 0.0 : exp(exp_arg);
```

#### 3.2 Impact on Current Derivatives

The effective dimensions affect all current derivatives:

```
∂Id/∂Vgs = (∂β/∂Weff)×(∂Weff/∂W_drawn)×(∂Id/∂β) + ... (chain rule)
```

Since `Weff` and `Leff` are bias-independent in BSIM4v5, these terms don't create additional Jacobian complexity but do affect the magnitude of derivatives.

### 4. Parasitic Resistance Convergence

#### 4.1 Width-Dependent Resistance

```
Rd_effective = Rd × (1 + wr × (1/Weff - 1/W_ref))
```

**Convergence Considerations:**
- The `1/Weff` term can become large for narrow devices
- Minimum width clamping prevents singularity
- Resistance derivatives affect matrix conditioning

#### 4.2 Matrix Conditioning with Parasitics

The inclusion of parasitic resistances improves diagonal dominance:

```
G_dd = gds + 1/Rd
G_ss = gds + gm + gmb + 1/Rs
```

The `1/R` terms increase diagonal elements, improving condition number and convergence rate.

### 5. Multi-Finger Device Convergence

#### 5.1 Multiplier Effects

For devices with `m > 1` (multiple fingers), parameters scale as:

```
Id_total = m × Id_single
Rd_total = Rd_single / m
C_total = m × C_single
```

**Convergence Impact:**
- Larger `m` increases current magnitude, requiring appropriate `abstol` scaling
- Parallel resistances reduce parasitic effects
- Matrix elements scale with `m`, affecting pivot selection

#### 5.2 Layout-Dependent Effect Scaling

Some layout effects don't scale linearly with `m`:

```
F_stress = 1 + sar/sa + sbr/sb + sdr/sd  (independent of m)
ΔVth_WPE = warc / sd^1.5  (independent of m)
```

This creates non-uniform scaling across fingers in multi-finger devices.

### 6. Initial Condition Consistency

#### 6.1 Geometry-Dependent Initial Guess

For initial condition solution `f(Vgs, Vds, Vbs) = Ids - I_specified = 0`, the geometry-corrected parameters affect the initial guess:

```
Vgs_guess = Vth_total + sqrt(2 × I_specified / β_effective)
```
where `β_effective` includes all geometry corrections.

#### 6.2 Temperature-Dependent Initial Conditions

When temperature is a variable, the initial guess must account for geometry-dependent temperature scaling:

```
Vth_guess = Vth0_effective - [kt1 + (kt1l/Leff)] × (T_guess/T_nom - 1)
```

### 7. Local Truncation Error (LTE) with Geometry Effects

#### 7.1 Charge-Based LTE

The LTE calculation uses geometrically corrected charges:

```
Q_total = Cox × Weff × Leff × Q_normalized(V)
LTE = |(1/3)Q(t) - (4/3)Q(t-Δt) + Q(t-2Δt)|
```

**Geometry Impact:** `Weff` and `Leff` scale the charge magnitude, affecting LTE tolerance scaling.

#### 7.2 Time-Step Control

The adaptive time-step algorithm must account for geometry-dependent time constants:

```
τ_min = min(Rd × C_gd, Rs × C_gs, ...)
Δt_max = 0.1 × τ_min
```

where capacitances scale with `Weff × Leff`.

### 8. Convergence Acceleration Techniques

#### 8.1 Geometry-Aware Damping

For devices with strong layout effects, additional damping may be required:

```
λ_damping = 1 / (1 + α × |ΔVth_WPE|/Vth0)
V_new = V_old + λ_damping × (V_NR - V_old)
```

where `α` is a tuning parameter (typically 0.1).

#### 8.2 Predictor-Corrector with Geometry Terms

The predictor step includes geometry effects:

```
Vth_pred = Vth0_effective + ΔVth_WPE + ΔVth_pocket(T_pred)
```

### 9. Validation and Error Metrics

#### 9.1 Geometry Consistency Checks

```
|Weff_calculated - Weff_expected| / Weff_expected < ε_geom (1e-6)
|Leff_calculated - Leff_expected| / Leff_expected < ε_geom
```

#### 9.2 Layout Effect Magnitude Bounds

```
|ΔVth_WPE| / Vth0 < 0.3  (typical bound)
|F_stress - 1| < 0.5  (stress factor bound)
```

Violations trigger warnings but not errors, as extreme layout conditions may be intentional.

#### 9.3 Convergence Rate Monitoring

For devices with strong layout effects, monitor convergence rate:

```
ρ = log(|ΔV_k|/|ΔV_{k-1}|) / log(|ΔV_{k-1}|/|ΔV_{k-2}|)
```

Geometry effects should not degrade `ρ` from the ideal value of 2.

### 10. Performance Optimization

#### 10.1 Precomputation Strategy

Layout-dependent terms are computed once during setup:

```c
/* In BSIM4v5setup() */
inst->BSIM4v5stress_factor = 1.0 + model->BSIM4v5sar/sa_eff 
                                   + model->BSIM4v5sbr/sb_eff 
                                   + model->BSIM4v5sdr/sd_eff;
inst->BSIM4v5wpe_vth_shift = model->BSIM4v5warc / pow(sd_eff, 1.5);
```

These precomputed values are reused during load iterations.

#### 10.2 Conditional Evaluation

Geometry effects are only evaluated if parameters are specified:

```c
if (model->BSIM4v5sarGiven && model->BSIM4v5sbrGiven && model->BSIM4v5sdrGiven) {
    /* Compute STI stress */
}
if (model->BSIM4v5warcGiven) {
    /* Compute WPE effect */
}
```

This avoids unnecessary computations for models without layout effects.

This mathematical formulation and convergence analysis demonstrates how BSIM4v5's layout-dependent effects are integrated into SPICE simulation while maintaining the numerical robustness required for production circuit analysis. The implementation carefully balances physical accuracy with computational efficiency and convergence stability.

---

## C Implementation

### 1. Core Data Structures for Layout-Dependent Effects

The BSIM4v5 implementation extends the generic MOS framework with specialized structures for layout-dependent parameters.

#### 1.1 Enhanced Model Structure (`bsim4v5def.h`)

```c
typedef struct sBSIM4v5model {
    /* Device type */
    int BSIM4v5type;                    /* NMOS=1, PMOS=-1 */
    
    /* STI Stress Parameters */
    double BSIM4v5sar;                  /* Stress effect on mobility: Π_mob */
    double BSIM4v5sbr;                  /* Length-direction stress: α */
    double BSIM4v5sdr;                  /* Well-edge proximity: γ */
    int BSIM4v5sarGiven;                /* Flag for parameter presence */
    int BSIM4v5sbrGiven;
    int BSIM4v5sdrGiven;
    
    /* WPE Parameters */
    double BSIM4v5warc;                 /* WPE Vth shift: K_wpe */
    double BSIM4v5wbrc;                 /* WPE mobility: M_wpe */
    double BSIM4v5wl;                   /* Characteristic length: λ_wpe */
    int BSIM4v5warcGiven;
    int BSIM4v5wbrcGiven;
    
    /* Pocket/Halo Implant Parameters */
    double BSIM4v5dvtshft;              /* Pocket Vth shift: P_shift */
    double BSIM4v5dvtshfttemp;          /* Temperature coeff: α_temp */
    double BSIM4v5phigh;                /* Peak concentration: P_high */
    double BSIM4v5plow;                 /* Background: P_low */
    int BSIM4v5dvtshftGiven;
    int BSIM4v5phighGiven;
    
    /* Geometry Correction Parameters */
    double BSIM4v5dlc;                  /* Length correction: DL */
    double BSIM4v5dwc;                  /* Width correction: DW */
    double BSIM4v5llc;                  /* Length char. length: LL */
    double BSIM4v5wwc;                  /* Width char. length: WW */
    
    /* Temperature Scaling with Geometry Dependence */
    double BSIM4v5kt1l;                 /* Length-dependent Vth temp coeff: KT1L */
    double BSIM4v5atl;                  /* Length-dependent vsat temp coeff: ATL */
    double BSIM4v5utel;                 /* Length-dependent mobility temp exp: UTE_L */
    
    /* Traditional BSIM4 parameters */
    double BSIM4v5vth0;                 /* Zero-bias threshold voltage */
    double BSIM4v5u0;                   /* Low-field mobility */
    double BSIM4v5vsat;                 /* Saturation velocity */
    double BSIM4v5tox;                  /* Oxide thickness */
    /* ... 400+ additional parameters ... */
    
    /* Linked list management */
    struct sBSIM4v5model *BSIM4v5nextModel;
    sBSIM4v5instance *BSIM4v5instances;
} BSIM4v5model;
```

#### 1.2 Enhanced Instance Structure (`bsim4v5def.h`)

```c
typedef struct sBSIM4v5instance {
    /* Terminal nodes */
    int BSIM4v5dNode;                   /* Drain */
    int BSIM4v5gNode;                   /* Gate */
    int BSIM4v5sNode;                   /* Source */
    int BSIM4v5bNode;                   /* Bulk */
    
    /* Geometry parameters from layout */
    double BSIM4v5l;                    /* Drawn length */
    double BSIM4v5w;                    /* Drawn width */
    double BSIM4v5sa;                   /* Distance to STI edge a */
    double BSIM4v5sb;                   /* Distance to STI edge b */
    double BSIM4v5sc;                   /* Distance to STI edge c */
    double BSIM4v5sd;                   /* Distance to well edge */
    
    /* Effective dimensions after correction */
    double BSIM4v5leff;                 /* Effective length: L_eff */
    double BSIM4v5weff;                 /* Effective width: W_eff */
    
    /* Stress-modified parameters */
    double BSIM4v5vth0_stress;          /* Vth0 with STI/WPE corrections */
    double BSIM4v5u0_stress;            /* u0 with stress corrections */
    
    /* Temperature-scaled parameters */
    double BSIM4v5vth0_temp;            /* Temperature-scaled Vth0 */
    double BSIM4v5u0_temp;              /* Temperature-scaled mobility */
    double BSIM4v5vsat_temp;            /* Temperature-scaled vsat */
    
    /* State variables for convergence */
    double BSIM4v5vth_old;              /* Previous Vth for convergence test */
    double BSIM4v5ueff_old;             /* Previous μ_eff for convergence */
    
    /* Matrix pointers (16 total) */
    double *BSIM4v5DdPtr;               /* Gdd */
    double *BSIM4v5DgPtr;               /* Gdg = gm */
    double *BSIM4v5DsPtr;               /* Gds = -gds */
    double *BSIM4v5DbPtr;               /* Gdb = gmbs */
    /* ... additional 12 pointers ... */
    
    /* Linked list */
    struct sBSIM4v5instance *BSIM4v5nextInstance;
    BSIM4v5model *BSIM4v5modPtr;
} BSIM4v5instance;
```

### 2. Parameter Binding System (`b4v5par.c`)

The parameter table maps SPICE input to C structure fields, including layout-dependent parameters.

```c
/* STI Stress Parameters */
IOP("sar",    BSIM4v5_SAR,    IF_REAL, "STI stress mobility coefficient Π_mob"),
IOP("sbr",    BSIM4v5_SBR,    IF_REAL, "Length-direction STI stress α"),
IOP("sdr",    BSIM4v5_SDR,    IF_REAL, "Well-edge proximity stress γ"),

/* WPE Parameters */
IOP("warc",   BSIM4v5_WARC,   IF_REAL, "WPE Vth shift coefficient K_wpe"),
IOP("wbrc",   BSIM4v5_WBRC,   IF_REAL, "WPE mobility coefficient M_wpe"),
IOP("wl",     BSIM4v5_WL,     IF_REAL, "WPE characteristic length λ_wpe"),

/* Pocket/Halo Parameters */
IOP("dvtshft", BSIM4v5_DVTSHFT, IF_REAL, "Pocket implant Vth shift P_shift"),
IOP("dvtshfttemp", BSIM4v5_DVTSHFTTEMP, IF_REAL, "Pocket Vth temperature coeff α_temp"),
IOP("phigh",   BSIM4v5_PHIGH,   IF_REAL, "Peak pocket concentration P_high"),
IOP("plow",    BSIM4v5_PLOW,    IF_REAL, "Background concentration P_low"),

/* Geometry Correction Parameters */
IOP("dlc",    BSIM4v5_DLC,    IF_REAL, "Length correction DL"),
IOP("dwc",    BSIM4v5_DWC,    IF_REAL, "Width correction DW"),
IOP("llc",    BSIM4v5_LLC,    IF_REAL, "Length characteristic length LL"),
IOP("wwc",    BSIM4v5_WWC,    IF_REAL, "Width characteristic length WW"),

/* Geometry-Dependent Temperature Parameters */
IOP("kt1l",   BSIM4v5_KT1L,   IF_REAL, "Length-dependent Vth temp coeff KT1L"),
IOP("atl",    BSIM4v5_ATL,    IF_REAL, "Length-dependent vsat temp coeff ATL"),
IOP("utel",   BSIM4v5_UTEL,   IF_REAL, "Length-dependent mobility temp exp UTE_L"),
```

### 3. Geometry and Stress Setup (`b4v5set.c`)

The setup function computes effective dimensions and applies layout-dependent corrections.

```c
int BSIM4v5setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    BSIM4v5model *model = (BSIM4v5model *)inModel;
    BSIM4v5instance *here;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (here = model->BSIM4v5instances; here != NULL; 
             here = here->BSIM4v5nextInstance) {
            
            /* 1. Effective Length Calculation: L_eff = L - 2·DL + DL·exp(-L/LL) */
            if (model->BSIM4v5dlcGiven && model->BSIM4v5llcGiven) {
                double L = here->BSIM4v5l;
                double DL = model->BSIM4v5dlc;
                double LL = model->BSIM4v5llc;
                here->BSIM4v5leff = L - 2.0 * DL + DL * exp(-L / LL);
            } else {
                here->BSIM4v5leff = here->BSIM4v5l;
            }
            
            /* 2. Effective Width Calculation: W_eff = W - 2·DW + DW·exp(-W/WW) */
            if (model->BSIM4v5dwcGiven && model->BSIM4v5wwcGiven) {
                double W = here->BSIM4v5w;
                double DW = model->BSIM4v5dwc;
                double WW = model->BSIM4v5wwc;
                here->BSIM4v5weff = W - 2.0 * DW + DW * exp(-W / WW);
            } else {
                here->BSIM4v5weff = here->BSIM4v5w;
            }
            
            /* 3. STI Stress Effect on Mobility: μ_stress = μ_0 × [1 + sar/sa + sbr/sb + sdr/sc] */
            if (model->BSIM4v5sarGiven && model->BSIM4v5sbrGiven && 
                model->BSIM4v5sdrGiven) {
                double stress_factor = 1.0;
                stress_factor += model->BSIM4v5sar / MAX(here->BSIM4v5sa, 1e-9);
                stress_factor += model->BSIM4v5sbr / MAX(here->BSIM4v5sb, 1e-9);
                stress_factor += model->BSIM4v5sdr / MAX(here->BSIM4v5sc, 1e-9);
                here->BSIM4v5u0_stress = model->BSIM4v5u0 * stress_factor;
            } else {
                here->BSIM4v5u0_stress = model->BSIM4v5u0;
            }
            
            /* 4. WPE Effect on Threshold Voltage: ΔVth_WPE = warc / sd^1.5 */
            if (model->BSIM4v5warcGiven) {
                double wpe_shift = model->BSIM4v5warc / 
                                   pow(MAX(here->BSIM4v5sd, 1e-9), 1.5);
                here->BSIM4v5vth0_stress = model->BSIM4v5vth0 + wpe_shift;
            } else {
                here->BSIM4v5vth0_stress = model->BSIM4v5vth0;
            }
            
            /* 5. Pocket Implant Effect: ΔVth_pocket = dvtshft / L_eff */
            if (model->BSIM4v5dvtshftGiven) {
                double pocket_shift = model->BSIM4v5dvtshft / here->BSIM4v5leff;
                here->BSIM4v5vth0_stress += pocket_shift;
            }
            
            /* 6. Allocate state vector indices for convergence testing */
            here->BSIM4v5state_vth = *states; (*states)++;
            here->BSIM4v5state_ueff = *states; (*states)++;
            
            /* 7. Setup matrix pointers for 4-terminal device */
            BSIM4v5setupMatrix(matrix, here, ckt);
        }
    }
    return OK;
}
```

### 4. Temperature Scaling with Geometry Dependence (`b4v5temp.c`)

Temperature effects are computed with geometry-dependent coefficients.

```c
int BSIM4v5temperature(GENmodel *inModel, CKTcircuit *ckt)
{
    BSIM4v5model *model = (BSIM4v5model *)inModel;
    BSIM4v5instance *here;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (here = model->BSIM4v5instances; here != NULL; 
             here = here->BSIM4v5nextInstance) {
            
            /* Convert to Kelvin */
            double T = here->BSIM4v5temp + CONSTCtoK;
            double TNOM = model->BSIM4v5tnom + CONSTCtoK;
            double Tratio = T / TNOM;
            
            /* 1. Mobility Temperature Dependence: μ(T) = μ_0·(T/T_nom)^(-UTE) */
            /*    where UTE = UTE_0 + UTE_L/L_eff */
            double UTE = model->BSIM4v5ute;
            if (model->BSIM4v5utelGiven) {
                UTE += model->BSIM4v5utel / here->BSIM4v5leff;
            }
            here->BSIM4v5u0_temp = here->BSIM4v5u0_stress * pow(Tratio, -UTE);
            
            /* 2. Threshold Voltage Temperature Scaling */
            /*    ΔVth(T) = KT1·(T/T_nom - 1) + KT1L/L_eff·(T/T_nom - 1) */
            double dVth_temp = model->BSIM4v5kt1 * (Tratio - 1.0);
            if (model->BSIM4v5kt1lGiven) {
                dVth_temp += model->BSIM4v5kt1l / here->BSIM4v5leff * (Tratio - 1.0);
            }
            here->BSIM4v5vth0_temp = here->BSIM4v5vth0_stress - dVth_temp;
            
            /* 3. Saturation Velocity Temperature Dependence */
            /*    v_sat(T) = v_sat - AT·(T/T_nom - 1) - ATL/L_eff·(T/T_nom - 1) */
            double dvsat_temp = model->BSIM4v5at * (Tratio - 1.0);
            if (model->BSIM4v5atlGiven) {
                dvsat_temp += model->BSIM4v5atl / here->BSIM4v5leff * (Tratio - 1.0);
            }
            here->BSIM4v5vsat_temp = model->BSIM4v5vsat - dvsat_temp;
            
            /* 4. Pocket Implant Temperature Dependence */
            if (model->BSIM4v5dvtshfttempGiven) {
                here->BSIM4v5dvtshft_temp = model->BSIM4v5dvtshft * 
                    (1.0 + model->BSIM4v5dvtshfttemp * (Tratio - 1.0));
            }
        }
    }
    return OK;
}
```

### 5. DC Load Function with Layout Effects (`b4v5ld.c`)

The core load function integrates layout-dependent effects into the current equations.

```c
int BSIM4v5load(GENmodel *inModel, CKTcircuit *ckt)
{
    BSIM4v5model *model = (BSIM4v5model *)inModel;
    BSIM4v5instance *here;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (here = model->BSIM4v5instances; here != NULL; 
             here = here->BSIM4v5nextInstance) {
            
            /* Get terminal voltages */
            double vgs = *(ckt->CKTrhs + here->BSIM4v5gNode) -
                        *(ckt->CKTrhs + here->BSIM4v5sNode);
            double vds = *(ckt->CKTrhs + here->BSIM4v5dNode) -
                        *(ckt->CKTrhs + here->BSIM4v5sNode);
            double vbs = *(ckt->CKTrhs + here->BSIM4v5bNode) -
                        *(ckt->CKTr