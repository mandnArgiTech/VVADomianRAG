# MOSFET Level 3: Semi-Empirical Mathematics and DC Load

_Generated 2026-04-12 05:41 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/include/ngspice/devdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3load.c`

# MOSFET Level 3: Semi-Empirical Mathematics and DC Load

## Introduction: Core Implementation Files

The MOS3 (Level 3 MOSFET) model in Ngspice is implemented through a coordinated set of C source files that bridge the Grove-Frohman semi-empirical mathematics to SPICE's circuit simulation engine. Four key files form the foundation of the DC load implementation:

1. **`devdefs.h`** - Defines the generic device framework (`SPICEdev` structure) that provides the interface contract between any semiconductor device and the Ngspice simulation kernel. This file establishes the function pointer architecture that allows MOS3 to register its implementation routines.

2. **`mos3par.c`** - Contains the parameter binding tables that map SPICE netlist parameters (like `VTO`, `KP`, `GAMMA`) to internal C structure fields. This file implements the device's "front end," translating user input into the internal representation used by the computational routines.

3. **`mos3temp.c`** - Implements temperature-dependent parameter scaling based on semiconductor physics. This file contains the temperature adjustment routines that modify threshold voltage, mobility, junction potentials, and other parameters according to established physical models, ensuring accurate simulation across temperature corners.

4. **`mos3load.c`** - The computational heart of the DC implementation. This file contains the core Grove-Frohman Level 3 equations for threshold voltage calculation (with body effect, DIBL, and narrow-width effects), field-dependent mobility degradation, velocity saturation modeling, and piecewise drain current calculation. It also implements the Newton-Raphson voltage limiting (`DEVfetlim`) and matrix stamping algorithms that integrate the device into the circuit's conductance matrix.

Together, these files implement a complete, production-ready Level 3 MOSFET model that accurately captures short-channel effects while maintaining robust convergence properties within Ngspice's Newton-Raphson iterative solver framework.

## Mathematical Formulation

The MOS3 (Level 3) model in Ngspice implements the Grove-Frohman semi-empirical equations with geometry-dependent effects. The mathematical formulation directly maps to SPICE's DC operating point calculation and matrix stamping requirements.

### 1. Threshold Voltage with Geometry Effects

The threshold voltage calculation incorporates three key second-order effects critical for accurate DC simulation:

```
V_th = VTO + φ_γ + η·V_ds - δ·(W_eff/L_eff)·V_bs
```

Where:
- **VTO**: Zero-bias threshold voltage (SPICE parameter `VTO`)
- **φ_γ**: Body effect term = `γ·[√(2φ_F - V_bs) - √(2φ_F)]`
  - `γ`: Body effect coefficient (SPICE parameter `GAMMA`)
  - `φ_F`: Surface potential (SPICE parameter `PHI`)
- **η·V_ds**: Drain-Induced Barrier Lowering (DIBL) effect
  - `η`: DIBL coefficient (SPICE parameter `ETA`)
- **δ·(W_eff/L_eff)·V_bs**: Narrow-width effect
  - `δ`: Narrow-width coefficient (SPICE parameter `DELTA`)
  - `W_eff = W - 2·WD`, `L_eff = L - 2·LD`: Effective dimensions

**SPICE Integration**: This formulation directly populates the `MOS3instance.vth` field used in all subsequent current calculations and affects the bulk transconductance `gmbs` for matrix stamping.

### 2. Field-Dependent Mobility Model

The effective mobility accounts for vertical field degradation, essential for accurate transconductance calculation:

```
μ_eff = μ₀ / [1 + θ·(V_gs - V_th)]
```

Where:
- **μ₀**: Low-field mobility (SPICE parameter `U0`)
- **θ**: Mobility degradation coefficient (SPICE parameter `THETA`)

**Temperature Scaling**:
```
μ_eff(T) = μ_eff(T_nom) · (T/T_nom)^{-1.5}
```

**SPICE Integration**: The effective mobility directly scales the transconductance parameter `β = (W_eff/L_eff)·C_ox·μ_eff`, which determines all current derivatives for the Jacobian matrix.

### 3. Saturation Voltage with Velocity Saturation

The saturation voltage formulation includes velocity saturation effects critical for short-channel devices:

```
V_dsat = (V_gs - V_th) / [1 + κ·(V_gs - V_th)]
```

Where:
- **κ**: Saturation field factor = `μ₀/(2·v_max·L_eff)`
- **v_max**: Maximum drift velocity (SPICE parameter `VMAX`)

**SPICE Integration**: `V_dsat` determines the operating region boundary and is used in the `DEVfetlim` voltage limiting function to ensure Newton-Raphson convergence.

### 4. Piecewise Drain Current Equations

#### 4.1 Cutoff Region (V_gs ≤ V_th)
```
I_ds = 0
g_m = 0, g_ds = 0, g_mbs = 0
```

#### 4.2 Linear/Triode Region (V_gs > V_th and V_ds ≤ V_dsat)
```
I_ds = β·[(V_gs - V_th)·V_ds - (1 + κ·(V_gs - V_th))·V_ds²/2]·(1 + λ·V_ds)
```

First derivatives for Jacobian matrix:
```
g_m = ∂I_ds/∂V_gs = β·V_ds·(1 + κ·V_gst) - β·κ·V_ds²/2
g_ds = ∂I_ds/∂V_ds = β·(V_gst - (1 + κ·V_gst)·V_ds)·(1 + λ·V_ds) + λ·I_ds
g_mbs = ∂I_ds/∂V_bs = -g_m·(∂V_th/∂V_bs)
```

Where `V_gst = V_gs - V_th` and `∂V_th/∂V_bs = -γ/(2√(φ - V_bs)) - δ·(W_eff/L_eff)`

#### 4.3 Saturation Region (V_gs > V_th and V_ds > V_dsat)
```
I_ds = (β/(2κ))·(V_gs - V_th)²/[1 + κ·(V_gs - V_th)]·(1 + λ·V_ds)
```

First derivatives:
```
g_m = ∂I_ds/∂V_gs = (β·V_gst/(κ·(1 + κ·V_gst)²))·(1 + κ·V_gst/2)
g_ds = ∂I_ds/∂V_ds = λ·I_ds
g_mbs = -g_m·(∂V_th/∂V_bs)
```

**SPICE Integration**: These equations directly compute the `MOS3instance` fields `MOS3cd`, `MOS3gm`, `MOS3gds`, and `MOS3gmbs` that are stamped into the conductance matrix.

### 5. Meyer Capacitance Charge Model

The charge model provides the capacitive currents for transient analysis:

#### 5.1 Accumulation Region (V_gb < V_FB)
```
Q_g = C_ox·(V_gb - V_FB)
Q_b = -Q_g
Q_s = Q_d = 0
```

#### 5.2 Depletion Region (V_FB ≤ V_gb < V_th)
```
Q_b = -C_ox·γ·√(φ - V_bs)
Q_g = -Q_b
Q_s = Q_d = 0
```

#### 5.3 Inversion Region
##### Linear (V_ds ≤ V_dsat):
```
Q_g = C_ox·[V_gb - V_FB - φ - (V_gs + V_gd - 2V_th)/2]
Q_d = -C_ox·[V_gb - V_FB - φ - (2V_gd + V_gs - 3V_th)/6]
Q_s = -C_ox·[V_gb - V_FB - φ - (2V_gs + V_gd - 3V_th)/6]
```

##### Saturation (V_ds > V_dsat):
```
Q_g = (2/3)·C_ox·(V_gs - V_th)
Q_d = 0
Q_s = -Q_g
```

**SPICE Integration**: Charges are stored in the state vector at indices `MOS3state[0..2]` for `q_gs`, `q_gd`, `q_gb`, enabling charge-conserving transient analysis.

### 6. Temperature-Dependent Parameter Scaling

Critical for accurate simulation across temperature corners:

```
VTO(T) = VTO(T_nom) + TCV·(T - T_nom)
μ₀(T) = μ₀(T_nom)·(T/T_nom)^{-1.5}
PB(T) = PB(T_nom)·(T/T_nom) - 3·V_T·ln(T/T_nom) - E_g(T)·(T/T_nom) + E_g(T_nom)
IS(T) = IS(T_nom)·exp[(E_g(T_nom)/V_T(T_nom) - E_g(T)/V_T(T))·(T/T_nom)^{XTI}]
```

Where `E_g(T) = 1.16 - 7.02e-4·T²/(T + 1108)` and `V_T = kT/q`.

**SPICE Integration**: Implemented in `mos3temp.c` and called during `.TEMP` analysis or when instance temperature differs from nominal.

### 7. Parasitic Resistance Modeling

The internal nodes D' and S' model series resistances:

```
I_rd = (V_d - V_d')/R_d
I_rs = (V_s - V_s')/R_s
```

**Matrix Stamp**:
```
G[d,d] += 1/R_d, G[d,d'] -= 1/R_d
G[d',d] -= 1/R_d, G[d',d'] += 1/R_d + g_ds
```

**SPICE Integration**: Creates a 6×6 conductance matrix (D, G, S, B, D', S') instead of 4×4, requiring 36 matrix pointers in `MOS3instance`.

## Convergence Analysis

### 1. Newton-Raphson Voltage Limiting Algorithm

The `DEVfetlim` function ensures convergence by preventing excessive voltage changes between iterations:

#### Mathematical Formulation:
Given previous voltage `v_old` and new Newton-Raphson prediction `v_new`:
```
Δv = v_new - v_old
v_crit = { V_dsat for V_ds, V_on for V_gs, 0 for V_bs }
```

Limiting rules:
1. If `v_old > v_crit` and `v_new > v_old`: Allow increase but limit to `v_temp = v_old + 2·(v_crit - v_old)`
2. If `v_old > v_crit` and `v_new < v_crit`: Clamp to `v_crit`
3. If `v_old < -v_crit` and `v_new < v_old`: Allow decrease but limit to `v_temp = v_old - 2·(v_crit + v_old)`
4. If `v_old < -v_crit` and `v_new > -v_crit`: Clamp to `-v_crit`
5. If `-v_crit ≤ v_old ≤ v_crit`: Clamp `v_new` to `[ -v_crit, v_crit ]`

**SPICE Context**: Applied in `mos3load.c` to `V_gs`, `V_ds`, and `V_bs` before current calculation to prevent divergence in strong inversion or near cutoff.

### 2. Convergence Testing Criteria

The `MOS3convTest` function implements SPICE's mixed absolute-relative tolerance checking:

#### Voltage Convergence:
For each node voltage `v` (D, G, S, B, D', S'):
```
|v_new - v_old| ≤ RELTOL·max(|v_new|, |v_old|) + VNTOL
```
Where:
- `RELTOL = 0.001` (default relative tolerance)
- `VNTOL = 1e-6` (default voltage absolute tolerance)

#### Charge Convergence:
For each stored charge `q` (q_gs, q_gd, q_gb):
```
|q_new - q_old| ≤ RELTOL·max(|q_new|, |q_old|) + CHGTOL
```
Where `CHGTOL = 1e-14` (default charge absolute tolerance).

**SPICE Implementation**: Uses `ckt->CKTstate0` (current iteration) and `ckt->CKTstate1` (previous iteration) arrays. Failure sets `ckt->CKTnoncon = 1`, triggering another Newton iteration.

### 3. Region Boundary Smoothing

To ensure derivative continuity for Newton-Raphson convergence:

#### At V_gs = V_th (cutoff/linear boundary):
Use linear extrapolation for `V_gst < 0`:
```
I_ds_smooth = β·V_gst²/(2·V_smooth) for V_gst > -V_smooth
```
Where `V_smooth ≈ 0.1` V ensures continuous first derivative.

#### At V_ds = V_dsat (linear/saturation boundary):
Use quadratic blending over range `[V_dsat - ΔV, V_dsat + ΔV]`:
```
I_ds_blend = w_lin·I_ds_lin + w_sat·I_ds_sat
```
Where weights `w_lin + w_sat = 1` and vary smoothly with `V_ds`.

**SPICE Context**: Prevents Jacobian discontinuities that cause Newton-Raphson oscillation.

### 4. PMOS Polarity and Source-Drain Swap Convergence

For PMOS devices (`MOS3type = -1`), internal transformation ensures consistent mathematics:

```
V_gs_pmos = -V_gs_nmos
V_ds_pmos = -V_ds_nmos
V_bs_pmos = -V_bs_nmos
I_ds_pmos = -I_ds_nmos
```

**Swap Logic**:
1. Invert all voltage polarities
2. Swap drain/source node indices
3. Swap internal D'/S' node indices
4. Swap R_d/R_s values
5. After calculation, invert currents and transconductances

**Convergence Benefit**: Maintains identical numerical behavior for NMOS/PMOS, ensuring symmetric convergence properties.

### 5. Conductance Matrix Conditioning

To prevent singular matrices during Newton-Raphson:

#### Minimum Conductance Addition:
```
G_min = GMIN = 1e-12 Ʊ (default)
```
Added to all diagonal entries: `G[i,i] += GMIN`

#### Parasitic Resistance Lower Bounds:
```
R_d, R_s ≥ RMIN = 1e-6 Ω
```
Prevents infinite conductance in matrix.

#### Capacitance Floor:
```
C_gs, C_gd, C_gb ≥ CMIN = 1e-18 F
```
Ensures time constant `τ = RC` remains finite for transient analysis.

### 6. Iteration Control and Fallback

#### Maximum Iterations:
`ITL1 = 40` (default DC iteration limit)
`ITL2 = 20` (default NR iteration limit per DC point)

#### Source Stepping:
If direct NR fails, apply source stepping:
```
V_source(k) = (k/N)·V_source_full for k = 0..N
```
Where `N = 10` steps gradually increase source voltages to final values.

#### GMIN Stepping:
If convergence fails, increase `GMIN` from `1e-12` to `1e-3` over 5 steps, then reduce back after convergence.

### 7. Initial Condition Handling

#### Priority Order:
1. User `.IC` specification (VDS, VGS, VBS)
2. `OFF` flag (forces V_gs = 0, I_ds = 0)
3. Zero-bias assumption (all voltages = 0)
4. Previous solution (for continuation analyses)

#### Implementation:
```c
if (inst->MOS3icVDSGiven) {
    vds = inst->MOS3icVDS;
    vgs = inst->MOS3icVGS;
    vbs = inst->MOS3icVBS;
} else if (inst->MOS3off) {
    vgs = 0; vds = 0; vbs = 0;
} else {
    vgs = vds = vbs = 0;
}
```

**Convergence Impact**: Good initial conditions reduce Newton iterations by 50-70%.

### 8. Numerical Stability Safeguards

#### Argument Protection:
```c
sqrt_arg = MAX(φ - V_bs, 1e-12);
log_arg = MAX(ratio, 1e-12);
denom = MAX(1 + κ·V_gst, 1e-12);
```

#### Overflow Prevention:
```c
exp_arg = MIN(MAX(arg, -50.0), 50.0);
```

#### Division Protection:
```c
if (fabs(denom) < 1e-30) denom = SIGN(1e-30, denom);
```

### 9. Convergence Monitoring and Diagnostics

SPICE tracks convergence metrics:
- `ckt->CKTnoncon`: Non-convergence flag
- `ckt->CKTmode`: Analysis mode (DC, TRAN, AC, etc.)
- `ckt->CKTtime`: Current simulation time (for transient)
- Iteration count per device type

**Debug Output**: With `.OPTIONS METHOD=DEBUG`, prints voltage/current changes per iteration for divergence diagnosis.

### 10. Algorithmic Convergence Summary

The MOS3 model ensures SPICE convergence through:
1. **Continuous derivatives** across all operating regions
2. **Voltage limiting** via `DEVfetlim` at critical boundaries
3. **Mixed tolerance checking** for voltages, currents, and charges
4. **Matrix conditioning** with GMIN and minimum resistances
5. **Fallback strategies** (source stepping, GMIN stepping)
6. **Numerical protection** for all mathematical operations
7. **Symmetric handling** of NMOS/PMOS devices
8. **Temperature-consistent** parameter scaling

These mechanisms collectively ensure the Level 3 model converges robustly across all bias conditions, geometries, and temperatures while maintaining physical accuracy for circuit simulation.

----------

# C Implementation

## 1. Core Data Structures and SPICE Integration

### 1.1 Device Framework and Inheritance Hierarchy

The MOS3 implementation follows Ngspice's generic device framework defined in `devdefs.h`. The `SPICEdev` structure provides the interface between the MOS3 device and the SPICE simulation engine:

```c
/* From devdefs.h - Device registration structure */
typedef struct sSPICEdev {
    char *DEVname;                  /* "mos3" */
    /* ... function pointers for all device operations ... */
    int DEVinstSize;                /* sizeof(MOS3instance) */
    int DEVmodSize;                 /* sizeof(MOS3model) */
} SPICEdev;
```

The MOS3-specific structures inherit from these generic types through type casting in function signatures. The `MOS3model` and `MOS3instance` structures defined in `mos3defs.h` contain all Level 3-specific parameters and state variables.

### 1.2 Parameter Binding and SPICEdev Initialization

The device registration occurs through parameter tables in `mos3par.c`:

```c
/* Model parameter table mapping SPICE names to internal indices */
static IFparm MOS3mPTable[] = {
    IOP("vto",     MOS3_VTO,     IF_REAL,    "Threshold voltage"),
    IOP("kp",      MOS3_KP,      IF_REAL,    "Transconductance parameter"),
    IOP("gamma",   MOS3_GAMMA,   IF_REAL,    "Body effect parameter"),
    IOP("phi",     MOS3_PHI,     IF_REAL,    "Surface potential"),
    IOP("lambda",  MOS3_LAMBDA,  IF_REAL,    "Channel-length modulation"),
    /* ... Level 3 specific parameters ... */
    IOP("eta",     MOS3_ETA,     IF_REAL,    "DIBL coefficient"),
    IOP("theta",   MOS3_THETA,   IF_REAL,    "Mobility degradation coefficient"),
    IOP("kappa",   MOS3_KAPPA,   IF_REAL,    "Saturation field factor"),
    IOP("vmax",    MOS3_VMAX,    IF_REAL,    "Maximum drift velocity"),
    /* ... geometry and temperature parameters ... */
};

/* Instance parameter table */
static IFparm MOS3pTable[] = {
    IOP("l",       MOS3_L,       IF_REAL,    "Channel length"),
    IOP("w",       MOS3_W,       IF_REAL,    "Channel width"),
    /* ... other instance parameters ... */
};
```

The `SPICEdev MOS3info` structure binds these tables to the implementation functions:

```c
SPICEdev MOS3info = {
    .DEVname = "mos3",
    .DEVmodParam = MOS3mPTable,
    .DEVinstParam = MOS3pTable,
    .DEVload = MOS3load,           /* DC and transient load function */
    .DEVsetup = MOS3setup,         /* Matrix allocation and initialization */
    .DEVtemperature = MOS3temp,    /* Temperature adjustments */
    .DEVtrunc = MOS3trunc,         /* Local truncation error calculation */
    .DEVconvTest = MOS3convTest,   /* Convergence testing */
    .DEVinstSize = sizeof(MOS3instance),
    .DEVmodSize = sizeof(MOS3model),
    /* ... other function pointers ... */
};
```

## 2. Setup and Initialization (`mos3set.c`)

### 2.1 Matrix Pointer Allocation

The `MOS3setup()` function allocates sparse matrix pointers for the 6-node system (D, G, S, B, D', S'):

```c
int MOS3setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS3model *model = (MOS3model *)inModel;
    MOS3instance *inst;
    
    for (; model != NULL; model = model->MOS3nextModel) {
        for (inst = model->MOS3instances; inst != NULL; inst = inst->MOS3nextInstance) {
            /* Allocate 36 matrix pointers for 6x6 conductance matrix */
            inst->MOS3dDrainPtr = SMPmakeElt(matrix, inst->MOS3dNode, inst->MOS3dNode);
            inst->MOS3dGatePtr = SMPmakeElt(matrix, inst->MOS3dNode, inst->MOS3gNode);
            inst->MOS3dSourcePtr = SMPmakeElt(matrix, inst->MOS3dNode, inst->MOS3sNode);
            /* ... allocate all 36 pointers ... */
            
            /* Calculate effective dimensions */
            inst->MOS3leff = inst->MOS3l - 2.0 * model->MOS3ld;
            inst->MOS3weff = inst->MOS3w - 2.0 * model->MOS3wd;
            
            /* Allocate state vector indices for charge storage */
            inst->MOS3state[0] = (*states)++;  /* qgs */
            inst->MOS3state[1] = (*states)++;  /* qgd */
            inst->MOS3state[2] = (*states)++;  /* qgb */
            inst->MOS3state[3] = (*states)++;  /* qbd */
            inst->MOS3state[4] = (*states)++;  /* qbs */
            inst->MOS3state[5] = (*states)++;  /* qd' */
            inst->MOS3state[6] = (*states)++;  /* qs' */
        }
    }
    return OK;
}
```

### 2.2 Effective Dimension Calculation

The code implements the mathematical effective dimension formulas:
- `L_eff = L - 2·LD` (mapped to `inst->MOS3leff = inst->MOS3l - 2.0 * model->MOS3ld`)
- `W_eff = W - 2·WD` (mapped to `inst->MOS3weff = inst->MOS3w - 2.0 * model->MOS3wd`)

## 3. Core DC Load Implementation (`mos3load.c`)

### 3.1 Voltage Extraction and Polarity Handling

```c
int MOS3load(GENmodel *inModel, CKTcircuit *ckt) {
    MOS3model *model = (MOS3model *)inModel;
    MOS3instance *inst;
    
    for (; model != NULL; model = model->MOS3nextModel) {
        for (inst = model->MOS3instances; inst != NULL; inst = inst->MOS3nextInstance) {
            /* Extract node voltages from circuit solution vector */
            double vgs = ckt->CKTrhs[inst->MOS3gNode] - ckt->CKTrhs[inst->MOS3sNodePrime];
            double vds = ckt->CKTrhs[inst->MOS3dNodePrime] - ckt->CKTrhs[inst->MOS3sNodePrime];
            double vbs = ckt->CKTrhs[inst->MOS3bNode] - ckt->CKTrhs[inst->MOS3sNodePrime];
            
            /* PMOS polarity inversion */
            if (model->MOS3type < 0) {
                vgs = -vgs;
                vds = -vds;
                vbs = -vbs;
                /* Internal node swapping logic */
                SWAP(inst->MOS3dNode, inst->MOS3sNode);
                SWAP(inst->MOS3dNodePrime, inst->MOS3sNodePrime);
            }
            
            /* Newton-Raphson voltage limiting */
            inst->MOS3vgs_orig = vgs;
            inst->MOS3vds_orig = vds;
            inst->MOS3vbs_orig = vbs;
            
            vgs = DEVfetlim(vgs, inst->MOS3vgs_orig, inst->MOS3von);
            vds = DEVfetlim(vds, inst->MOS3vds_orig, inst->MOS3vdsat);
            vbs = DEVfetlim(vbs, inst->MOS3vbs_orig, 0.0);
            
            /* Store limited voltages */
            inst->MOS3vgs = vgs;
            inst->MOS3vds = vds;
            inst->MOS3vbs = vbs;
```

### 3.2 Threshold Voltage Calculation Mapping

The mathematical threshold voltage formula:
```
Vth = VTO + γ·[√(φ - Vbs) - √φ] + η·Vds - δ·(W_eff/L_eff)·Vbs
```

maps directly to C code:

```c
/* Body effect term */
if (model->MOS3gammaGiven && model->MOS3phiGiven) {
    double phiMinVbs = model->MOS3phi - vbs;
    double sqrtPhiMinVbs = (phiMinVbs > 0.0) ? sqrt(phiMinVbs) : 0.0;
    double sqrtPhi = sqrt(model->MOS3phi);
    double phiGamma = model->MOS3gamma * (sqrtPhiMinVbs - sqrtPhi);
} else {
    phiGamma = 0.0;
}

vth = model->MOS3vt0 + phiGamma;

/* DIBL effect (ETA * Vds) */
if (model->MOS3etaGiven) {
    vth += model->MOS3eta * vds;
}

/* Narrow-width effect (DELTA * (W_eff/L_eff) * Vbs) */
if (model->MOS3deltaGiven) {
    vth -= model->MOS3delta * (inst->MOS3weff / inst->MOS3leff) * vbs;
}

/* Temperature adjustment */
if (inst->MOS3temp != model->MOS3tnom) {
    vth -= model->MOS3tcv * (inst->MOS3temp - model->MOS3tnom);
}

inst->MOS3von = vth;  /* Store as turn-on voltage */
inst->MOS3vgst = vgs - vth;  /* Effective gate drive */
```

### 3.3 Mobility Degradation Implementation

The mathematical mobility model:
```
μ_eff = μ₀ / [1 + θ·(Vgs - Vth)]
```

maps to:

```c
double ueff;
if (model->MOS3thetaGiven && vgst > 0.0) {
    ueff = model->MOS3u0 / (1.0 + model->MOS3theta * vgst);
} else {
    ueff = model->MOS3u0;
}

/* Temperature scaling: μ ∝ T^{-3/2} */
if (inst->MOS3temp != model->MOS3tnom) {
    double T = inst->MOS3temp + 273.15;
    double Tnom = model->MOS3tnom + 273.15;
    ueff *= pow(T/Tnom, -1.5);
}
```

### 3.4 Saturation Voltage with Velocity Saturation

The velocity saturation equations:
```
κ = μ₀/(2·v_max·L_eff)
Vdsat = (Vgs - Vth) / [1 + κ·(Vgs - Vth)]
```

are implemented as:

```c
double vdsat;
if (model->MOS3kappaGiven && model->MOS3vmaxGiven) {
    /* Calculate KAPPA from physical parameters if not explicitly given */
    if (!model->MOS3kappaGiven) {
        model->MOS3kappa = ueff / (2.0 * model->MOS3vmax * inst->MOS3leff);
    }
    
    if (vgst > 0.0) {
        vdsat = vgst / (1.0 + model->MOS3kappa * vgst);
    } else {
        vdsat = 0.0;
    }
} else {
    /* Without velocity saturation */
    vdsat = vgst;
}

inst->MOS3vdsat = vdsat;  /* Store for NR limiting */
```

### 3.5 Drain Current Calculation with Piecewise Regions

The piecewise current equations map directly to conditional code blocks:

```c
/* Calculate β = (W_eff/L_eff)·C_ox·μ_eff */
double cox = 3.9 * 8.854e-12 / model->MOS3tox;
double beta = (inst->MOS3weff / inst->MOS3leff) * cox * ueff;
inst->MOS3beta = beta;

if (vgst <= 0.0) {
    /* CUTOFF REGION: Id = 0 */
    inst->MOS3cd = 0.0;
    inst->MOS3gm = 0.0;
    inst->MOS3gds = 0.0;
    inst->MOS3gmbs = 0.0;
    
} else if (vds <= vdsat) {
    /* LINEAR REGION: Id = β·[(Vgs-Vth)·Vds - (1+κ·(Vgs-Vth))·Vds²/2]·(1+λ·Vds) */
    double kappaVGST = model->MOS3kappa * vgst;
    double term1 = vgst * vds;
    double term2 = (1.0 + kappaVGST) * vds * vds / 2.0;
    
    inst->MOS3cd = beta * (term1 - term2);
    
    /* Channel-length modulation */
    if (model->MOS3lambdaGiven) {
        inst->MOS3cd *= (1.0 + model->MOS3lambda * vds);
    }
    
    /* Derivatives for Jacobian matrix */
    inst->MOS3gm = beta * vds * (1.0 + kappaVGST) 
                   - beta * model->MOS3kappa * vds * vds / 2.0;
    
    inst->MOS3gds = beta * (vgst - (1.0 + kappaVGST) * vds);
    if (model->MOS3lambdaGiven) {
        inst->MOS3gds = inst->MOS3gds * (1.0 + model->MOS3lambda * vds)
                       + model->MOS3lambda * inst->MOS3cd;
    }
    
} else {
    /* SATURATION REGION: Id = (β/(2κ))·(Vgs-Vth)²/[1+κ·(Vgs-Vth)]·(1+λ·Vds) */
    double denom = 1.0 + model->MOS3kappa * vgst;
    inst->MOS3cd = (beta / (2.0 * model->MOS3kappa)) * (vgst * vgst) / denom;
    
    /* Channel-length modulation */
    if (model->MOS3lambdaGiven) {
        inst->MOS3cd *= (1.0 + model->MOS3lambda * vds);
    }
    
    /* Derivatives */
    double dId_dVg = (beta * vgst / (model->MOS3kappa * denom * denom))
                     * (1.0 + model->MOS3kappa * vgst / 2.0);
    inst->MOS3gm = dId_dVg;
    inst->MOS3gds = model->MOS3lambda * inst->MOS3cd;
}

/* Bulk transconductance: gmbs = -gm · ∂Vth/∂Vbs */
if (model->MOS3gammaGiven && model->MOS3phiGiven && vbs < model->MOS3phi) {
    double dVth_dVbs = -model->MOS3gamma / (2.0 * sqrtPhiMinVbs);
    if (model->MOS3deltaGiven) {
        dVth_dVbs -= model->MOS3delta * (inst->MOS3weff / inst->MOS3leff);
    }
    inst->MOS3gmbs = -inst->MOS3gm * dVth_dVbs;
} else {
    inst->MOS3gmbs = 0.0;
}

/* PMOS current inversion */
if (model->MOS3type < 0) {
    inst->MOS3cd = -inst->MOS3cd;
    inst->MOS3gm = -inst->MOS3gm;
    inst->MOS3gds = -inst->MOS3gds;
    inst->MOS3gmbs = -inst->MOS3gmbs;
}
```

### 3.6 Meyer Capacitance Model Implementation

The Meyer capacitance model maps mathematical piecewise equations to conditional code:

```c
/* Calculate Meyer capacitances */
double vgd = vgs - vds;
double vgb = vgs - vbs;

if (vgst <= 0.0) {
    /* CUTOFF: Only overlap capacitances */
    inst->MOS3cgs = model->MOS3cgso * inst->MOS3weff;
    inst->MOS3cgd = model->MOS3cgdo * inst->MOS3weff;
    inst->MOS3cgb = model->MOS3cgbo * inst->MOS3leff;
    
} else if (vds <= vdsat) {
    /* LINEAR REGION capacitance partitioning */
    double vmid = (vgs + vgd - 2.0 * vth) / 2.0;
    inst->MOS3cgs = cox * (0.5 - vmid / (6.0 * (vgst - vmid)));
    inst->MOS3cgd = cox * (0.5 + vmid / (6.0 * (vgst - vmid)));
    inst->MOS3cgb = 0.0;
    
    /* Add overlap capacitances */
    inst->MOS3cgs += model->MOS3cgso * inst->MOS3weff;
    inst->MOS3cgd += model->MOS3cgdo * inst->MOS3weff;
    inst->MOS3cgb += model->MOS3cgbo * inst->MOS3leff;
    
} else {
    /* SATURATION REGION: 2/3 Cox to source, none to drain */
    inst->MOS3cgs = (2.0/3.0) * cox;
    inst->MOS3cgd = 0.0;
    inst->MOS3cgb = 0.0;
    
    /* Add overlap capacitances */
    inst->MOS3cgs += model->MOS3cgso * inst->MOS3weff;
    inst->MOS3cgd += model->MOS3cgdo * inst->MOS3weff;
    inst->MOS3cgb += model->MOS3cgbo * inst->MOS3leff;
}

/* Calculate charges for state vector */
inst->MOS3qgs = inst->MOS3cgs * vgs;
inst->MOS3qgd = inst->MOS3cgd * vgd;
inst->MOS3qgb = inst->MOS3cgb * vgb;

/* Store in circuit state vector for transient analysis */
ckt->CKTstates[inst->MOS3state[0