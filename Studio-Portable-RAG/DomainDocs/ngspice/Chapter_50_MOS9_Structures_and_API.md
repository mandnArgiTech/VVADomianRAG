# MOS9: Data Structures and SPICE API

_Generated 2026-04-12 07:59 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9defs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9dest.c`

# MOS9: Data Structures and SPICE API

## Technical Introduction

Within the Ngspice EDA codebase, the MOS9 (Level 9) Philips MOSFET model is implemented through a sophisticated C architecture that bridges advanced semiconductor physics with SPICE circuit simulation requirements. The implementation spans multiple specialized files that handle different aspects of device modeling and SPICE integration.

**`mos9defs.h`** defines the core data structures that encapsulate the MOS9 model's mathematical parameters and instance-specific operating point variables. This file contains the `sMOS9model` structure, which stores all physical parameters (VTO, KP, GAMMA, PHI, etc.) and the `sMOS9instance` structure, which manages operating point variables (voltages, currents, conductances) and SPICE matrix pointers. These structures directly map to the mathematical formulation, with each field corresponding to a specific parameter in the Philips model equations.

**`mos9init.c`** implements the SPICE device initialization and parameter binding system. This file contains the `MOS9info` structure that defines the MOS9 device interface to Ngspice, including function pointers for all analysis types (DC, AC, transient, noise, distortion, sensitivity). It also implements the `MOS9init()` function that sets up parameter tables and establishes the connection between SPICE netlist parameters and the internal C data structures.

**`mos9.c`** (typically named `mos9load.c` in Ngspice) is the computational core that implements the MOS9 mathematical model and performs matrix stamping for Newton-Raphson iteration. This file contains the `MOS9load()` function that evaluates the Philips model equations, computes partial derivatives for the Jacobian matrix, and stamps conductances and currents into the SPICE circuit matrix. It translates the mathematical smoothing functions and region transitions into efficient C code with numerical stability protections.

**`mos9dest.c`** handles memory management and cleanup operations for the MOS9 model. This file implements the `MOS9destroy()` and `MOS9delete()` functions that properly deallocate memory for model and instance structures, ensuring no memory leaks during circuit simulation. It manages the linked list structures that chain multiple MOS9 instances and models together.

Together, these four files form a complete SPICE device implementation that transforms the Philips MOS9 mathematical model into a production-ready circuit simulation component, balancing physical accuracy with numerical robustness and computational efficiency. The architecture follows Ngspice's standardized device interface pattern while implementing the specific mathematical innovations of the Philips model.

---

## Mathematical Formulation

The MOS9 (Level 9) model in Ngspice implements the Philips (NXP) MOSFET formulation with comprehensive physical effects and smooth mathematical transitions for robust SPICE simulation. The model's mathematical structure is designed to provide physical accuracy while ensuring numerical stability through continuous derivatives across all operating regions.

### 1. Threshold Voltage with Advanced Physical Effects

The MOS9 threshold voltage calculation incorporates multiple physical effects with smooth blending:

**Core Threshold Equation:**
```
V_th = VTO + γ·[√(φ - V_bs) - √φ] + η·V_ds + ΔV_w
```

**Component Breakdown:**
- **VTO**: Zero-bias threshold voltage (`model->MOS9vto`)
- **Body Effect**: `γ·[√(φ - V_bs) - √φ]` where `γ = model->MOS9gamma`, `φ = model->MOS9phi`
- **DIBL (Drain-Induced Barrier Lowering)**: `η·V_ds` where `η = model->MOS9eta`
- **Narrow Width Effect**: `ΔV_w = δ·(π·ε_si/(4·C_ox·W_eff))·(φ - V_bs)` where `δ = model->MOS9delta`

**SPICE Implementation Smoothing:**
```c
/* Continuous square root for body effect */
if (φ - V_bs < 0) {
    sqrt_term = sqrt(φ) * (1.0 - 0.5*(V_bs/φ) - 0.125*pow(V_bs/φ, 2));
} else {
    sqrt_term = sqrt(φ - V_bs);
}
```

### 2. Mobility Degradation with Multiple Field Dependencies

The effective mobility model captures vertical and lateral field effects:

**Mobility Degradation Equation:**
```
μ_eff = μ₀ / [1 + θ·(V_gs - V_th) + μ₁·V_ds/L_eff + μ₂/(V_gs - V_th + μ₀_param)]
```

**Parameter Mapping:**
- `μ₀` = `model->MOS9u0` (low-field mobility)
- `θ` = `model->MOS9theta` (vertical field mobility reduction)
- `μ₁` = `model->MOS9mu1` (lateral field coefficient)
- `μ₂` = `model->MOS9mu2` (saturation velocity coefficient)
- `μ₀_param` = `model->MOS9mu0` (mobility reference parameter)

**SPICE Numerical Protection:**
```c
Vgst = V_gs - V_th;
if (fabs(Vgst) < 1e-10) {
    Vgst = (Vgst >= 0) ? 1e-10 : -1e-10;
}
mobility_denom = 1.0 + model->MOS9theta * Vgst + 
                 model->MOS9mu1 * V_ds / L_eff + 
                 model->MOS9mu2 / (Vgst + model->MOS9mu0);
μ_eff = model->MOS9u0 / MAX(mobility_denom, 1e-3);
```

### 3. Drain Current with Smooth Region Transitions

The drain current formulation uses hyperbolic smoothing functions for C¹ continuity:

**Transconductance Parameter:**
```
β = (W_eff/L_eff) · KP · (μ_eff/μ₀)
where KP = μ₀ · C_ox = model->MOS9kp
```

**Critical Field and Saturation Voltage:**
```
E_c = 2 · V_MAX / μ_eff
V_dsat = (V_gs - V_th) / (1 + (V_gs - V_th)/(E_c·L_eff))
```

**Triode Region Current (V_ds ≤ V_dsat):**
```
I_ds_tri = β · [(V_gs - V_th - 0.5·α·V_ds) · V_ds]
where α = 1 + γ/(2√(φ - V_bs))
```

**Saturation Region Current (V_ds > V_dsat):**
```
I_ds_sat = β · (V_gs - V_th)² · (1 + κ·V_ds) / [2·(1 + (V_gs - V_th)/(E_c·L_eff))]
where κ = model->MOS9kappa
```

**Hyperbolic Smoothing Function:**
```c
/* Smooth transition parameter */
δ = 0.01 * V_dsat;

/* Effective V_ds with smoothing */
if (V_ds < V_dsat) {
    V_ds_eff = V_dsat - 0.5 * (sqrt(pow(V_ds - V_dsat, 2) + δ*δ) + V_ds - V_dsat);
} else {
    V_ds_eff = V_ds;
}

/* Blend function using tanh for smooth transition */
λ = 0.5 * (1.0 + tanh(10.0 * (V_ds - V_dsat) / V_dsat));

/* Final blended current */
I_ds = (1.0 - λ) * I_ds_tri(V_ds_eff) + λ * I_ds_sat;
```

### 4. Channel Length Modulation with Logarithmic Form

**CLM Equation:**
```
ΔL = λ₁ · ln(1 + V_ds - V_dsat) + λ₂ · (V_ds - V_dsat)
where λ₁ = model->MOS9lambda1, λ₂ = model->MOS9lambda2
```

**SPICE Implementation with Protection:**
```c
V_diff = V_ds - V_dsat;
if (V_diff > 0) {
    /* Logarithmic term with protection */
    if (V_diff < 1e-6) {
        log_term = V_diff - 0.5 * V_diff * V_diff;  /* Series expansion */
    } else {
        log_term = log(1.0 + V_diff);
    }
    deltaL = model->MOS9lambda1 * log_term + model->MOS9lambda2 * V_diff;
    I_ds *= (1.0 + deltaL / L_eff);
}
```

### 5. Subthreshold Conduction with Exponential Smoothing

**Subthreshold Slope Factor:**
```
n = 1 + γ/(2√(φ - V_bs)) + n₀ + n_b·V_bs + n_d·V_ds
where n₀ = model->MOS9n0, n_b = model->MOS9nb, n_d = model->MOS9nd
```

**Thermal Voltage:**
```
V_t = k·T/q = 8.617333262145e-5 * (temp + 273.15)
```

**Effective Gate-Source Voltage (Smooth Transition):**
```
V_gsteff = 2·n·V_t · ln(1 + exp((V_gs - V_th)/(2·n·V_t)))
```

**Subthreshold Current:**
```
I_ds_sub = β · (n·V_t)² · exp((V_gs - V_th)/(n·V_t)) · (1 - exp(-V_ds/V_t))
```

**Blending with Above-Threshold Current:**
```c
blend_factor = 1.0 - exp(-V_gsteff/(n * V_t));
I_ds_total = I_ds_sub + blend_factor * I_ds_above;
```

### 6. Capacitance Models with Continuous Derivatives

**Meyer Capacitance Model with Smooth Region Transitions:**

**Accumulation Region (V_gs < V_fb):**
```
Q_g = C_ox · (V_gs - V_fb)
where V_fb = model->MOS9vfb
```

**Saturation Region (V_ds > V_gs - V_th):**
```
Q_g = (2/3) · C_ox · (V_gs - V_th)
Q_s = (2/3) · Q_g
Q_d = (1/3) · Q_g
```

**Linear Region (V_ds ≤ V_gs - V_th):**
```
Q_g = C_ox · [(V_gs - V_th) - (1/2)V_ds]
Q_s = Q_d = (1/2) · Q_g
```

**Smoothing Implementation:**
```c
/* Smooth transition between regions */
V_gt = V_gs - V_th;
if (V_gt < 0) {
    /* Accumulation */
    Q_g = model->MOS9cox * W_eff * L_eff * (V_gs - model->MOS9vfb);
} else {
    /* Smooth transition parameter */
    ε = 0.1 * V_gt;
    
    /* Determine if in saturation */
    sat_factor = 0.5 * (1.0 + tanh((V_ds - V_gt)/ε));
    
    /* Linear region charge */
    Q_g_lin = model->MOS9cox * W_eff * L_eff * (V_gt - 0.5 * V_ds);
    
    /* Saturation region charge */
    Q_g_sat = (2.0/3.0) * model->MOS9cox * W_eff * L_eff * V_gt;
    
    /* Blended charge */
    Q_g = (1.0 - sat_factor) * Q_g_lin + sat_factor * Q_g_sat;
}
```

### 7. Junction Capacitance with Voltage Smoothing

**Bottom Junction Capacitance:**
```
C_j0 = C_J · A_diff + C_JSW · P_diff
```

**Reverse Bias (V_j < FC·PB):**
```
C_j = C_j0 · (1 - V_j/PB)^(-MJ)
```

**Forward Bias (V_j ≥ FC·PB):**
```
C_j = C_j0 · (1 - FC)^(-MJ) · [1 - MJ·(V_j - FC·PB)/(PB·(1 - FC))]
```

**Smoothing Around V_j = 0:**
```c
/* Continuous derivative at V_j = 0 */
if (fabs(V_j) < 0.1) {
    /* Use smooth approximation */
    C_j = C_j0 / sqrt(1.0 + pow(V_j/PB, 2));
} else if (V_j < model->MOS9fc * model->MOS9pb) {
    /* Standard reverse bias formula */
    C_j = C_j0 * pow(1.0 - V_j/model->MOS9pb, -model->MOS9mj);
} else {
    /* Forward bias linear approximation */
    C_j = C_j0 * pow(1.0 - model->MOS9fc, -model->MOS9mj) *
          (1.0 - model->MOS9mj * (V_j - model->MOS9fc * model->MOS9pb) /
          (model->MOS9pb * (1.0 - model->MOS9fc)));
}
```

### 8. Temperature Scaling Equations

**Threshold Voltage Temperature Dependence:**
```
VTO(T) = VTO(T_nom) + (KT1 + KT1L/L_eff + KT2·V_bs) · (T/T_nom - 1)
```

**Mobility Temperature Degradation:**
```
μ₀(T) = μ₀(T_nom) · (T/T_nom)^UTE
```

**Bandgap Energy Temperature Dependence:**
```
E_g(T) = 1.16 - 7.02×10⁻⁴ · T²/(T + 1108)
```

**Junction Potential Scaling:**
```
PB(T) = PB(T_nom) · T/T_nom - 2·(k·T/q)·ln(T/T_nom) - E_g(T_nom)·T/T_nom + E_g(T)
```

**SPICE Implementation:**
```c
/* Temperature ratio */
tratio = (inst->MOS9temp + CONSTCtoK) / (model->MOS9tnom + CONSTCtoK);

/* Threshold voltage scaling */
vto_temp = model->MOS9vto + 
           (model->MOS9kt1 + model->MOS9kt1l/inst->MOS9l + 
            model->MOS9kt2 * vbs) * (tratio - 1.0);

/* Mobility scaling */
if (model->MOS9ute != 0.0) {
    u0_temp = model->MOS9u0 * pow(tratio, model->MOS9ute);
} else {
    u0_temp = model->MOS9u0;
}
```

### 9. Matrix Stamping for Newton-Raphson

**7-Node Matrix Structure:**
Nodes: [D, G, S, B, D', S', internal]

**Conductance Definitions:**
```
g_m = ∂I_ds/∂V_gs
g_ds = ∂I_ds/∂V_ds
g_mbs = ∂I_ds/∂V_bs
g_bd = ∂I_bd/∂V_bd
g_bs = ∂I_bs/∂V_bs
```

**Matrix Stamp Pattern:**
```
[ G_dd+G_dpdp   0         0         0        -G_dpdp       0       ] [V_d]   [I_d]
[ 0             0         0         0         0            0       ] [V_g]   [0]
[ 0             0         G_ss+G_ssp 0        0           -G_ssp   ] [V_s] = [I_s]
[ 0             0         0         G_bb      0            0       ] [V_b]   [I_b]
[-G_dpdp        0         0         0        G_dpdp+g_dsp -g_dsp   ] [V_d']  [0]
[ 0             0        -G_ssp     0        -g_dsp       G_ssp+g_dsp] [V_s']  [0]
```

**SPICE Implementation:**
```c
/* Stamp intrinsic MOSFET conductances */
*(inst->MOS9drainDrainPrimePtr) += g_ds;
*(inst->MOS9drainPrimeDrainPtr) += g_ds;
*(inst->MOS9drainPrimeDrainPrimePtr) += g_ds + g_m + g_mbs;
*(inst->MOS9drainPrimeGatePtr) += g_m;
*(inst->MOS9drainPrimeBulkPtr) += g_mbs;
*(inst->MOS9drainPrimeSourcePrimePtr) += -g_ds - g_m - g_mbs;

/* Stamp parasitic resistances */
g_rd = 1.0 / MAX(model->MOS9rd, 1e-12);
*(inst->MOS9drainDrainPtr) += g_rd;
*(inst->MOS9drainDrainPrimePtr) += -g_rd;
*(inst->MOS9drainPrimeDrainPtr) += -g_rd;
*(inst->MOS9drainPrimeDrainPrimePtr) += g_rd;
```

---

## C Implementation

The MOS9 (Philips) model implementation in Ngspice translates the sophisticated mathematical formulations into efficient C code with careful attention to numerical stability and SPICE integration. The implementation spans multiple files that handle different aspects of the device simulation.

### 1. Core Data Structures (`mos9defs.h`)

#### Model Structure (`sMOS9model`)

The `sMOS9model` structure encapsulates all mathematical parameters of the Philips MOS9 model:

```c
typedef struct sMOS9model {
    int MOS9type;                     /* Device type: NMF (>0) or PMF (<0) */
    double MOS9vto;                   /* VTO: Zero-bias threshold voltage (V) */
    double MOS9kp;                    /* KP: Transconductance parameter (A/V²) */
    double MOS9gamma;                 /* GAMMA: Body effect parameter (√V) */
    double MOS9phi;                   /* PHI: Surface potential (V) */
    double MOS9lambda;                /* LAMBDA: Channel-length modulation (1/V) */
    double MOS9rd;                    /* RD: Drain ohmic resistance (Ω) */
    double MOS9rs;                    /* RS: Source ohmic resistance (Ω) */
    double MOS9cbd;                   /* CBD: Zero-bias B-D junction capacitance (F) */
    double MOS9cbs;                   /* CBS: Zero-bias B-S junction capacitance (F) */
    double MOS9is;                    /* IS: Junction saturation current (A) */
    double MOS9pb;                    /* PB: Junction potential (V) */
    double MOS9cgso;                  /* CGSO: Gate-source overlap capacitance per width (F/m) */
    double MOS9cgdo;                  /* CGDO: Gate-drain overlap capacitance per width (F/m) */
    double MOS9cgbo;                  /* CGBO: Gate-bulk overlap capacitance per length (F/m) */
    double MOS9rsh;                   /* RSH: Diffusion sheet resistance (Ω/□) */
    double MOS9cj;                    /* CJ: Bottom junction capacitance per area (F/m²) */
    double MOS9mj;                    /* MJ: Bottom junction grading coefficient */
    double MOS9cjsw;                  /* CJSW: Sidewall junction capacitance per perimeter (F/m) */
    double MOS9mjsw;                  /* MJSW: Sidewall junction grading coefficient */
    double MOS9js;                    /* JS: Junction saturation current per area (A/m²) */
    double MOS9tox;                   /* TOX: Oxide thickness (m) */
    double MOS9ld;                    /* LD: Lateral diffusion (m) */
    double MOS9wd;                    /* WD: Width diffusion (m) */
    double MOS9u0;                    /* U0: Low-field mobility (cm²/V·s) */
    double MOS9fc;                    /* FC: Coefficient for forward-bias depletion capacitance */
    double MOS9delta;                 /* DELTA: Width effect on threshold voltage */
    double MOS9eta;                   /* ETA: Static feedback coefficient (DIBL) */
    double MOS9theta;                 /* THETA: Mobility modulation coefficient (1/V) */
    double MOS9vmax;                  /* VMAX: Maximum carrier velocity (m/s) */
    double MOS9kappa;                 /* KAPPA: Saturation field factor */
    double MOS9tnom;                  /* TNOM: Nominal temperature (°C) */
    double MOS9beta;                  /* BETA: Mobility degradation exponent */
    double MOS9alpha;                 /* ALPHA: Velocity saturation exponent */
    double MOS9lambda1;               /* LAMBDA1: First-order CLM coefficient */
    double MOS9lambda2;               /* LAMBDA2: Second-order CLM coefficient */
    double MOS9vfb;                   /* VFB: Flat-band voltage (V) */
    double MOS9acde;                  /* ACDE: Exponential non-quasi-static coefficient */
    double MOS9moin;                  /* MOIN: Gate bias dependent surface potential */
    struct sMOS9model *MOS9nextModel; /* Linked list pointer to next model */
    sMOS9instance *MOS9instances;     /* Pointer to chain of instances */
} MOS9model;
```

**Mathematical Mapping:** Each field corresponds directly to a parameter in the MOS9 mathematical formulation. The structure organizes parameters by physical effect: threshold voltage (VTO, GAMMA, PHI), mobility (U0, THETA), velocity saturation (VMAX, KAPPA), etc. Temperature-dependent parameters (TNOM) are stored for scaling calculations.

#### Instance Structure (`sMOS9instance`)

The `sMOS9instance` structure manages instance-specific data and operating point variables:

```c
typedef struct sMOS9instance {
    /* Terminal Nodes (SPICE node indices) */
    int MOS9dNode;                    /* Drain external node index */
    int MOS9gNode;                    /* Gate external node index */
    int MOS9sNode;                    /* Source external node index */
    int MOS9bNode;                    /* Bulk external node index */
    
    /* Internal Parasitic Nodes */
    int MOS9dNodePrime;               /* Drain internal node (after RD) */
    int MOS9sNodePrime;               /* Source internal node (after RS) */
    
    /* Geometry Parameters (instance-specific) */
    double MOS9l;                     /* L: Drawn channel length (m) */
    double MOS9w;                     /* W: Drawn channel width (m) */
    double MOS9ad;                    /* AD: Drain diffusion area (m²) */
    double MOS9as;                    /* AS: Source diffusion area (m²) */
    double MOS9pd;                    /* PD: Drain diffusion perimeter (m) */
    double MOS9ps;                    /* PS: Source diffusion perimeter (m) */
    double MOS9nrd;                   /* NRD: Number of squares in drain diffusion */
    double MOS9nrs;                   /* NRS: Number of squares in source diffusion */
    
    /* State Vector Allocation */
    unsigned MOS9states;              /* Base index into CKTstate array */
    /* Individual state indices allocated during setup: */
    /* MOS9qgs - Gate-source charge state index */
    /* MOS9qgd - Gate-drain charge state index */
    /* MOS9qgb - Gate-bulk charge state index */
    /* MOS9qbd - Bulk-drain charge state index */
    /* MOS9qbs - Bulk-source charge state index */
    
    /* Operating Point Variables (calculated each iteration) */
    double MOS9vds;                   /* Vds: Drain-source voltage (V) */
    double MOS9vgs;                   /* Vgs: Gate-source voltage (V) */
    double MOS9vbs;                   /* Vbs: Bulk-source voltage (V) */
    double MOS9vbd;                   /* Vbd: Bulk-drain voltage (V) */
    double MOS9vdsat;                 /* Vdsat: Saturation voltage (V) */
    double MOS9von;                   /* Von: Turn-on voltage (V) */
    int MOS9mode;                     /* 1=NMOS (normal), -1=PMOS or swapped */
    
    /* Small-Signal Parameters (for AC analysis) */
    double MOS9gm;                    /* gm: Transconductance (A/V) */
    double MOS9gds;                   /* gds: Drain conductance (A/V) */
    double MOS9gmbs;                  /* gmbs: Bulk transconductance (A/V) */
    double MOS9gbd;                   /* gbd: Bulk-drain conductance (A/V) */
    double MOS9gbs;                   /* gbs: Bulk-source conductance (A/V) */
    double MOS9cgs;                   /* Cgs: Gate-source capacitance (F) */
    double MOS9cgd;                   /* Cgd: Gate-drain capacitance (F) */
    double MOS9cgb;                   /* Cgb: Gate-bulk capacitance (F) */
    double MOS9capbd;                 /* Capbd: Bulk-drain junction capacitance (F) */
    double MOS9capbs;                 /* Capbs: Bulk-source junction capacitance (F) */
    
    /* Sparse Matrix Pointers (7×7 matrix for D,G,S,B,D',S' nodes) */
    double *MOS9drainDrainPtr;        /* G[drain][drain] = ∂Id/∂Vd */
    double *MOS9drainGatePtr;         /* G[drain][gate] = ∂Id/∂Vg */
    double *MOS9drainSourcePtr;       /* G[drain][source] = ∂Id/∂Vs */
    double *MOS9drainBulkPtr;         /* G[drain][bulk] = ∂Id/∂Vb */
    double *MOS9drainDrainPrimePtr;   /* G[drain][drainPrime] */
    double *MOS9drainSourcePrimePtr;  /* G[drain][sourcePrime] */
    /* Additional 36 pointers for complete 7×7 matrix */
    
    struct sMOS9instance *MOS9nextInstance; /* Next instance in linked list */
    MOS9model *MOS9modPtr;            /* Pointer to parent model */
} MOS9instance;
```

**Mathematical Mapping:** Operating point variables (`MOS9vds`, `MOS9vgs`, `MOS9vbs`) store the solution from Newton-Raphson iterations. Small-signal parameters (`MOS9gm`, `MOS9gds`, `MOS9gmbs`) are the derivatives needed for the Jacobian matrix. Matrix pointers provide direct access to sparse matrix locations for efficient stamping.

### 2. SPICE Device Initialization (`mos9init.c`)

#### Device Information Structure

The `MOS9info` structure defines the MOS9 device interface to Ngspice:

```c
SPICEdev MOS9info = {
    .DEVpublic = {
        .name = "MOS9",
        .description = "Level 9 Philips MOSFET model",
        .terms = 4,
        .numNames = 0,
        .termNames = NULL,
        .instance = MOS9pInstance,
        .model = MOS9mParam,
        .flags = DEV_DEFAULT,
        
        /* Function pointers for all analysis types */
        .DEVload = MOS9load,
        .DEVsetup = MOS9setup,
        .DEVunsetup = MOS9unsetup,
        .DEVpzLoad = MOS9pzLoad,
        .DEVacLoad = MOS9acLoad,
        .DEVaccept = MOS9accept,
        .DEVdestroy = MOS9destroy,
        .DEVmodDelete = MOS9mDelete,
        .DEVdelete = MOS9delete,
        .DEVsetic = MOS9getic,
        .DEVask = MOS9ask,
        .DEVmodAsk = MOS9mAsk,
        .DEVpzSetup = MOS9pzSetup,
        .DEVtrunc = MOS9trunc,
        .DEVconvTest = MOS9convTest,
        .DEVsenSetup = MOS9sSetup,
        .DEVsenLoad = MOS9sLoad,
        .DEVsenUpdate = MOS9sUpdate,
        .DEVsenAcLoad = MOS9sAcLoad,
        .DEVsenPrint = MOS9sPrint,
        .DEVdisto = MOS9disto,
        .DEVnoise = MOS9noise,
        .DEVsoaCheck = MOS9soaCheck,
    },
    .DEVparamCount = MOS9_PARAMS,
    .DEVmodParamCount = MOS9_MODPARMS,
    .DEVinstSize = sizeof(MOS9instance),
    .DEVmodSize = sizeof(MOS9model),
};
```

**SPICE Integration:** This structure maps each SPICE analysis type to the corresponding MOS9 implementation function. The `DEVload` pointer points to `MOS9load()` for DC/transient analysis, `DEVacLoad` points to `MOS9acLoad()` for AC analysis, etc.

#### Parameter Tables

Parameter tables define the mapping between SPICE netlist parameters and C structure fields:

```c
static IFparm MOS9pTable[] = {
    IOP("l", MOS9_L, IF_REAL, "Length"),
    IOP("w", MOS9_W, IF_REAL, "Width"),
    IOP("ad", MOS9_AD, IF_REAL, "Drain area"),
    IOP("as", MOS9_AS, IF_REAL, "Source area"),
    IOP("pd", MOS9_PD, IF_REAL, "Drain perimeter"),
    IOP("ps", MOS9_PS, IF_REAL, "Source perimeter"),
    IOP("nrd", MOS9_NRD, IF_REAL, "Drain squares"),
    IOP("nrs", MOS9_NRS, IF_REAL, "Source squares"),
    IOP("off", MOS9_OFF, IF_FLAG, "Device initially off"),
    IOP("ic", MOS9_IC, IF_REALVEC, "Initial condition vector"),
    IP("temp", MOS9_TEMP, IF_REAL, "Instance temperature"),
};

static IFparm MOS9mPTable[] = {
    IOP("vto", MOS9_VTO, IF_REAL, "Threshold voltage"),
    IOP("kp", MOS9_KP, IF_REAL, "Transconductance parameter"),
    IOP("gamma", MOS9_GAMMA, IF_REAL, "Body effect parameter"),
    IOP("phi", MOS9_PHI, IF_REAL, "Surface potential"),
    IOP("lambda", MOS9_LAMBDA, IF_REAL, "Channel-length modulation"),
    IOP("rd", MOS9_RD, IF_REAL, "Drain resistance"),
    IOP("rs", MOS9_RS, IF_REAL, "Source resistance"),
    IOP("cbd", MOS9_CBD, IF_REAL, "B-D junction capacitance"),
    IOP("cbs", MOS9_CBS, IF_REAL, "B-S junction capacitance"),
    IOP("is", MOS9_IS, IF_REAL, "Junction saturation current"),
    IOP("pb", MOS9_PB, IF_REAL, "Junction potential"),
    /* ... additional model parameters */
};
```

**Parameter Binding:** These tables define the parameter names recognized in SPICE netlists, their data types (`IF_REAL`, `IF_FLAG`, `IF_REALVEC`), and the corresponding symbolic constants that map to structure field offsets.

### 3. Core Device Equations Implementation (`mos9.c` / `mos9load.c`)

#### Main Load Function

The `MOS9load()` function implements the Philips model equations and stamps the matrix:

```c
int MOS9load(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS9model *model;
    MOS9instance *inst;
    double vgs, vds, vbs, vbd;
    double vgs_old, vds_old, vbs_old;
    double von, vdsat, vcrit;
    
    /* Loop through all models and instances */
    for(model = (MOS9model *)inModel; model != NULL; 
        model = model->MOS9nextModel) {
        
        for(inst = model->MOS9instances; inst != NULL; 
            inst = inst->MOS9nextInstance) {
            
            /* Get terminal voltages from circuit solution */
            vgs = *(ckt->CKTrhs + inst->MOS9gNode) - 
                  *(ckt->CKTrhs + inst->MOS9sNodePrime);
            vds = *(ckt->CKTrhs + inst->MOS9dNodePrime) - 
                  *(ckt->CKTrhs + inst->MOS9sNodePrime);
            vbs = *(ckt->CKTrhs + inst->MOS9bNode) - 
                  *(ckt->CKTrhs + inst->MOS9sNodePrime);
            vbd = vbs - vds;
            
            /* Store old values for convergence checking */
            vgs_old = inst->MOS9vgs;
            vds_old = inst->MOS9vds;
            vbs_old = inst->MOS9vbs;
            
            /* Apply Newton-Raphson voltage limiting */
            von = inst->MOS9von;
            vdsat = inst->MOS9vdsat;
            vcrit = sqrt(4.0 * (vgs_old - von) * (vgs_old - von) + 1.0) - 1.0;
            
            DEVfetlim(&vgs, vgs_old, von, vcrit);
            DEVfetlim(&vds, vds_old, vdsat, 0.5 * vdsat);
            DEVfetlim(&vbs, vbs_old, 0.0, 0.5);
            
            /* Store limited voltages */
            inst->MOS9vgs = vgs;
            inst->MOS9vds = vds;
            inst->MOS9vbs = vbs;
            inst->MOS9vbd = vbd;
            
            /* Calculate threshold voltage with body effect and DIBL */
            double phi = model->MOS9phi;
            double gamma = model->MOS9gamma;
            double eta = model->MOS9eta;
            double delta = model->MOS9delta;
            double vto = inst->MOS9vt;  /* Temperature-scaled VTO */
            
            double sqrtPhi = sqrt(phi);
            double sqrtPhiVbs = sqrt(phi - vbs);
            
            /* Body effect term */
            double vthBody = gamma * (sqrtPhiVbs - sqrtPhi);
            
            /* Narrow width effect */
            double cox = model->MOS9cox;
            double weff = inst->MOS9w - 2.0 * model->MOS9wd;
            double narrowEffect = 0.0;
            if(delta != 0.0 && cox > 0.0 && weff > 0.0) {
                double epsSi = 11.7 * 8.854e-12;
                narrowEffect = delta * (M_PI * epsSi / (4.0 * cox * weff)) * (phi - vbs);
            }
            
            /* Complete threshold voltage */
            double vth = vto + vthBody + eta * vds + narrowEffect;
            inst->MOS9vth = vth;
            
            /* Calculate effective mobility */
            double u0 = inst->MOS9u0temp;  /* Temperature-scaled mobility */
            double theta = model->MOS9theta;
            double mu1 = model->MOS9mu1;
            double mu2 = model->MOS9mu2;
            double mu0 = model->MOS9mu0;
            
            double Vgst = vgs - vth;
            if(fabs(Vgst) < 1e-10) {
                Vgst = (Vgst >= 0) ? 1e-10 : -1e-10;
            }
            
            double mobility_denom = 1.0 + theta * Vgst + 
                                   mu1 * vds / inst->MOS9leff + 
                                   mu2 / (Vgst + mu0);
            double ueff = u0 / MAX(mobility_denom, 1e-3);
            inst->MOS9ueff = ueff;
            
            /* Calculate transconductance parameter beta */
            double beta = (inst->MOS9weff / inst->MOS9leff) * 
                         model->MOS9kp * (ueff / u0);
            inst->MOS9beta = beta;
            
            /* Calculate saturation voltage */
            double Ec = 2.0 * model->MOS9vmax / ueff;
            vdsat = Vgst / (1.0 + Vgst / (Ec * inst->MOS9leff));
            inst->MOS9vdsat = vdsat;
            
            /* Calculate drain current with smooth region transitions */
            double Ids;
            if(Vgst <= 0.0) {
                /* Subthreshold/cutoff region */
                double n = 1.0 + gamma/(2.0 * sqrtPhiVbs) + 
                          model->MOS9n0 + model->MOS9nb * vbs + 
                          model->MOS9nd * vds;
                double Vt = 8.617333262145e-5 * (inst->MOS9temp + 273.15);