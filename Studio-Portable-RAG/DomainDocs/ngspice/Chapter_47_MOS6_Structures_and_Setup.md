# MOS6: Data Structures, API, and Parameter Setup

_Generated 2026-04-12 07:10 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6defs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6mask.c`

# MOS6: Data Structures, API, and Parameter Setup

## Technical Introduction

This chapter details the C implementation of the MOS6 (Level 6) Sakurai-Newton empirical MOSFET model in Ngspice. The implementation spans multiple files that handle different aspects of the device model:

- **`mos6defs.h`** - Defines the core data structures `sMOS6model` and `sMOS6instance` that store all mathematical parameters, operating point variables, and SPICE matrix pointers.

- **`mos6mpar.c`** and **`mos6mask.c`** - Implement parameter binding tables and mask definitions that map SPICE netlist parameters to internal C variables.

- **`mos6set.c`** - Contains the `MOS6setup()` function that performs mathematical transformations, allocates SMP matrix pointers, and initializes the device for circuit simulation.

- **`mos6temp.c`** - Implements temperature-dependent parameter scaling through the `MOS6temp()` function, adjusting physical parameters based on operating temperature.

These files collectively implement the Sakurai-Newton alpha-power law model optimized for digital circuit simulation, with complete SPICE integration including 6×6 matrix allocation, parameter validation, and temperature compensation.

## Mathematical Formulation

The MOS6 Level 6 model implements the Sakurai-Newton empirical alpha-power law formulation, specifically designed for digital circuit simulation in SPICE. The mathematics directly maps to SPICE's DC operating point calculation, Newton-Raphson iteration requirements, and matrix stamping algorithms.

### 1. Threshold Voltage with Body Effect

The threshold voltage calculation incorporates the body effect for substrate bias:

```
V_th = VTO + γ × [√(φ - V_bs) - √φ]   for V_bs ≤ 0
     = VTO + γ × [√φ/(1 + V_bs/(2φ))] for V_bs > 0 (approximation)
```

**SPICE Implementation Mapping:**
- `VTO` → `model->MOS6vt0` (zero-bias threshold voltage)
- `γ` → `model->MOS6gamma` (body effect parameter)
- `φ` → `model->MOS6phi` (surface potential, default 0.6V)
- `V_bs` → `inst->MOS6vbs` (source-bulk voltage from circuit solution)

In C code (`mos6load.c`):
```c
if (vbs <= 0) {
    inst->MOS6vth = model->MOS6vt0 + model->MOS6gamma * 
                   (sqrt(model->MOS6phi - vbs) - sqrt(model->MOS6phi));
} else {
    inst->MOS6vth = model->MOS6vt0 + model->MOS6gamma * 
                   (-vbs) / (2 * sqrt(model->MOS6phi + vbs));
}
```

### 2. Sakurai-Newton Alpha-Power Law Current Equations

#### Gate Overdrive Voltage:
```
V_gst = V_gs - V_th
```

#### Saturation Voltage:
```
V_dsat = KV × (V_gst)^NV
```
where:
- `KV` = Saturation voltage coefficient (typically ~1.0)
- `NV` = Saturation voltage exponent (0.5 for long-channel, 1.0-2.0 for short-channel)

#### Drain Current by Region:

**Region 1: Cutoff (V_gst ≤ 0)**
```
I_d = 0
g_m = 0
g_ds = 0
g_mbs = 0
```

**Region 2: Linear/Triode (0 < V_gst and 0 < V_ds ≤ V_dsat)**
```
I_d = β_eff × (V_gst)^NC × V_ds × (1 + λ × V_ds)
g_m = β_eff × NC × (V_gst)^(NC-1) × V_ds × (1 + λ × V_ds)
g_ds = β_eff × (V_gst)^NC × (1 + 2 × λ × V_ds)
g_mbs = (γ/(2√(φ - V_bs))) × g_m
```

**Region 3: Saturation (0 < V_gst and V_ds > V_dsat)**
```
I_d = KC × (V_gst)^NC × (1 + λ × V_ds)
g_m = KC × NC × (V_gst)^(NC-1) × (1 + λ × V_ds)
g_ds = KC × (V_gst)^NC × λ
g_mbs = (γ/(2√(φ - V_bs))) × g_m
```

**SPICE Implementation Mapping:**
- `β_eff` → `inst->MOS6betaEff` = `(W_eff/L_eff) × KP`
- `KP` → `model->MOS6kp` = `μ₀ × ε₀ₓ/t₀ₓ` = `μ₀ × 3.9×8.854e-12/TOX`
- `NC` → `model->MOS6nc` (current exponent in linear region)
- `KC` → `model->MOS6kc` (saturation current coefficient)
- `λ` → `model->MOS6lambda` (channel-length modulation)

### 3. Effective Dimensions Calculation

```
L_eff = L - 2 × LD
W_eff = W - 2 × WD

If (L_eff ≤ 0): L_eff = 1e-12  (prevents division by zero)
If (W_eff ≤ 0): W_eff = 1e-12
```

**SPICE Implementation Mapping:**
- `L` → `inst->MOS6l` (drawn channel length from netlist)
- `W` → `inst->MOS6w` (drawn channel width from netlist)
- `LD` → `model->MOS6ld` (lateral diffusion length)
- `WD` → `model->MOS6wd` (lateral diffusion width)

Computed in `MOS6setup()` and stored as `inst->MOS6lEff` and `inst->MOS6wEff`.

### 4. Parasitic Resistance Calculations

```
R_d_eff = RD + RSH × NRD
R_s_eff = RS + RSH × NRS

g_rd = 1/R_d_eff
g_rs = 1/R_s_eff
```

**SPICE Implementation Mapping:**
- `RD` → `model->MOS6rd` (drain ohmic resistance)
- `RS` → `model->MOS6rs` (source ohmic resistance)
- `RSH` → `model->MOS6rsh` (sheet resistance)
- `NRD` → `inst->MOS6nrd` (number of squares in drain)
- `NRS` → `inst->MOS6nrs` (number of squares in source)

### 5. Capacitance Calculations

#### Junction Capacitances:
```
C_bd = CBD × AD + CJSW × PD
C_bs = CBS × AS + CJSW × PS

C_bd(V_bd) = C_bd0/(1 - V_bd/PB)^MJ    for V_bd < FC × PB
           = C_bd0 × (1 - FC)^(-MJ) × [1 - FC × (1+MJ) + MJ × V_bd/PB] for V_bd ≥ FC × PB
```

#### Overlap Capacitances:
```
C_gso = CGSO × W_eff
C_gdo = CGDO × W_eff
C_gbo = CGBO × L_eff
```

**SPICE Implementation Mapping:**
- `CBD`, `CBS` → `model->MOS6cbd`, `model->MOS6cbs` (zero-bias capacitances)
- `CJSW` → `model->MOS6cjsw` (sidewall capacitance per perimeter)
- `CGSO`, `CGDO`, `CGBO` → `model->MOS6cgso`, `model->MOS6cgdo`, `model->MOS6cgb`
- `AD`, `AS`, `PD`, `PS` → `inst->MOS6ad`, `inst->MOS6as`, `inst->MOS6pd`, `inst->MOS6ps`

### 6. Temperature-Dependent Parameter Scaling

#### Threshold Voltage Temperature Scaling:
```
V_TO(T) = V_TO(T_nom) × [1 + VTO_TC × (T - T_nom)]
```

#### Mobility Temperature Degradation:
```
μ(T) = μ(T_nom) × (T/T_nom)^{-1.5}
```

#### Junction Potential Temperature Scaling:
```
PB(T) = PB(T_nom) × (T/T_nom) - 3 × V_T × ln(T/T_nom) - E_g(T) × (T/T_nom) + E_g(T_nom)
```

**SPICE Implementation Mapping:**
Implemented in `MOS6temp()` function using:
- `T_nom` → `model->MOS6tnom` (nominal temperature)
- `VTO_TC` → `model->MOS6vt0tc` (threshold voltage temperature coefficient)
- `E_g(T)` → Bandgap energy computed as `1.16 - 7.02e-4 × T²/(T + 1108.0)`

### 7. Matrix Stamping Pattern for 6-Node Representation

The MOS6 model uses a 6×6 conductance matrix for nodes: D, G, S, B, DP (drain prime), SP (source prime):

```
Indices: 0:D, 1:G, 2:S, 3:B, 4:DP, 5:SP
```

**Intrinsic MOSFET Stamp (nodes 4,5,1,3 only):**
```
G[4][4] = +g_ds          (drainPrime-drainPrime)
G[4][5] = -g_ds - g_m - g_mbs  (drainPrime-sourcePrime)
G[4][1] = +g_m           (drainPrime-gate)
G[4][3] = +g_mbs         (drainPrime-bulk)

G[5][4] = -g_ds          (sourcePrime-drainPrime)
G[5][5] = +g_ds + g_m + g_mbs  (sourcePrime-sourcePrime)
G[5][1] = -g_m           (sourcePrime-gate)
G[5][3] = -g_mbs         (sourcePrime-bulk)
```

**Parasitic Resistance Stamp:**
For RD between nodes 0 and 4:
```
G[0][0] += g_rd
G[0][4] -= g_rd
G[4][0] -= g_rd
G[4][4] += g_rd
```

For RS between nodes 2 and 5:
```
G[2][2] += g_rs
G[2][5] -= g_rs
G[5][2] -= g_rs
G[5][5] += g_rs
```

### 8. Newton-Raphson Voltage Limiting (DEVfetlim)

The `DEVfetlim()` function prevents excessive voltage changes between Newton iterations:

**Mathematical Implementation:**
```c
double DEVfetlim(double vnew, double vold, double vth) {
    double vt, vtox;
    
    if (vold > vth) {
        vt = vth + 3.5;  /* Thermal voltage * 3.5 */
        if (vnew > vold) {
            vnew = MIN(vnew, vold + 2.0);
        } else {
            if (vnew > 3.0 * vt) {
                vnew = MAX(vnew, vold - 2.0);
            } else {
                vnew = MAX(vnew, -0.5);
            }
        }
    } else {
        vt = 0.5 * (vth + 3.5);
        if (vnew < vold) {
            vnew = MAX(vnew, vold - 2.0);
        } else {
            if (vold < -0.5) {
                vnew = MIN(vnew, vold + 2.0);
            } else {
                vnew = MIN(vnew, 0.5 * vt);
            }
        }
    }
    return vnew;
}
```

**SPICE Application:** Applied to `V_gs`, `V_ds`, and `V_bs` before current calculation to ensure Newton-Raphson convergence.

### 9. Source-Drain Swap Mechanics

When `V_ds < 0`, the device operates in reverse mode with terminal swapping:

**Voltage Transformations:**
```
V_ds' = -V_ds
V_gs' = V_gs - V_ds  (becomes V_gd)
V_bs' = V_bs + V_ds  (becomes V_bd)
```

**Matrix Stamp Adjustment:** Drain and source matrix entries are swapped, and current direction is reversed.

### 10. Parameter Defaults and Validation

**Critical Default Values (from `mos6set.c`):**
```c
if (!model->MOS6vt0Given)    model->MOS6vt0 = 0.0;
if (!model->MOS6kvGiven)     model->MOS6kv = 1.0;
if (!model->MOS6nvGiven)     model->MOS6nv = 1.0;
if (!model->MOS6kcGiven)     model->MOS6kc = 2e-5;
if (!model->MOS6ncGiven)     model->MOS6nc = 1.0;
if (!model->MOS6lambdaGiven) model->MOS6lambda = 0.0;
if (!model->MOS6betaGiven)   model->MOS6beta = 2e-5;
if (!model->MOS6gammaGiven)  model->MOS6gamma = 0.0;
if (!model->MOS6phiGiven)    model->MOS6phi = 0.6;
```

**Parameter Validation:**
```c
if (inst->MOS6lEff <= 0.0) {
    inst->MOS6lEff = 1e-12;  /* Prevent division by zero */
}
if (inst->MOS6wEff <= 0.0) {
    inst->MOS6wEff = 1e-12;
}
```

### 11. SPICE Integration Summary

The MOS6 mathematical formulation directly supports SPICE's analysis requirements:

1. **DC Operating Point**: Current equations provide `I_ds` for Kirchhoff's Current Law satisfaction
2. **Newton-Raphson Iteration**: Derivatives `g_m`, `g_ds`, `g_mbs` form the Jacobian matrix for linearization
3. **Matrix Stamping**: Conductance values are stamped into SPICE's sparse matrix system
4. **Convergence Control**: `DEVfetlim()` prevents oscillation and divergence
5. **Temperature Analysis**: `MOS6temp()` scales parameters for .TEMP and .DC temperature sweeps
6. **Bidirectional Operation**: Source-drain swap enables symmetric behavior for PMOS and reverse bias
7. **Digital Optimization**: Alpha-power law with empirical exponents `NV`, `NC` provides accurate fitting for short-channel digital circuits

## Convergence Analysis

### 1. Newton-Raphson Convergence Criteria

The MOS6 model implements SPICE's standard convergence checking for the Newton-Raphson iterative solver:

**Voltage Convergence Test:**
For each terminal voltage `V` (V_gs, V_ds, V_bs):
```
|V_new - V_old| ≤ reltol × max(|V_new|, |V_old|) + vntol
```

**Current Convergence Test:**
For drain current `I_ds`:
```
|I_ds_new - I_ds_old| ≤ reltol × max(|I_ds_new|, |I_ds_old|) + abstol
```

**SPICE Implementation Parameters:**
- `reltol = CKTreltol = 0.001` (default relative tolerance)
- `vntol = CKTvoltTol = 1e-6` (default voltage absolute tolerance)
- `abstol = CKTabstol = 1e-12` (default current absolute tolerance)

### 2. DEVfetlim Voltage Limiting Algorithm

The `DEVfetlim()` function ensures convergence by preventing excessive voltage changes between Newton iterations:

**Mathematical Regions:**
1. **ON Region** (`vold > vth`):
   - Allow increase but limit to `vold + 2.0`
   - For decrease: if `vnew > 3.0 × vt`, limit to `vold - 2.0`; otherwise limit to `-0.5`

2. **OFF Region** (`vold ≤ vth`):
   - Allow decrease but limit to `vold - 2.0`
   - For increase: if `vold < -0.5`, limit to `vold + 2.0`; otherwise limit to `0.5 × vt`

Where `vt = vth + 3.5` approximates thermal voltage scaling.

**Convergence Impact:**
- Prevents overshoot when crossing the threshold voltage `vth`
- Maintains derivative continuity for Newton-Raphson convergence
- Different limiting for ON→OFF vs OFF→ON transitions

### 3. Region Boundary Handling

The MOS6 model has explicit region boundaries that affect convergence:

**Cutoff/Linear Boundary (V_gst = 0):**
- Discontinuous transition: `I_ds = 0` for `V_gst ≤ 0`, `I_ds > 0` for `V_gst > 0`
- No subthreshold modeling simplifies convergence for digital circuits
- `DEVfetlim()` ensures smooth voltage transitions across this boundary

**Linear/Saturation Boundary (V_ds = V_dsat):**
- Continuous current: `I_ds_linear(V_dsat) = I_ds_sat(V_dsat)` by design
- Discontinuous first derivative: `g_ds` jumps at boundary due to different region equations
- Newton-Raphson can handle this discontinuity with proper voltage limiting

### 4. Source-Drain Swap Convergence Symmetry

The automatic source-drain swapping ensures consistent convergence:

**Swap Conditions:**
- `V_ds < 0` triggers reverse mode operation
- Internal voltage transformation: `V_ds' = -V_ds`, `V_gs' = V_gs - V_ds`, `V_bs' = V_bs + V_ds`
- Matrix stamping adjusted to reflect terminal swapping

**Convergence Benefit:**
- Identical convergence properties for forward and reverse bias
- No special-case handling needed in Newton-Raphson solver
- Symmetric Jacobian matrix conditioning

### 5. Parameter Validation for Numerical Stability

**Effective Dimension Clamping:**
```c
if (inst->MOS6lEff <= 0.0) {
    inst->MOS6lEff = 1e-12;  /* Prevent division by zero in β_eff calculation */
}
if (inst->MOS6wEff <= 0.0) {
    inst->MOS6wEff = 1e-12;
}
```

**Parameter Range Checking:**
- `φ > 0` (surface potential must be positive)
- `NV > 0`, `NC > 0` (exponents must be positive for `pow()` function)
- `KV > 0`, `KC > 0` (coefficients must be positive)
- `λ ≥ 0` (channel-length modulation non-negative)

### 6. Temperature Consistency Enforcement

**Temperature Scaling Application:**
```c
if (inst->MOS6temp != ckt->CKTtemp) {
    MOS6temp(model, inst, ckt);  /* Apply temperature scaling */
}
```

**Convergence Requirement:**
- All temperature-dependent parameters updated simultaneously in `MOS6temp()`
- Prevents inconsistency between `vth`, `β_eff`, and other parameters
- Ensures self-consistent operating point at new temperature

### 7. Matrix Conditioning

**Minimum Conductance Addition:**
```
G_min = GMIN = 1e-12 Ʊ (default SPICE parameter)
```
Added to all diagonal entries by SPICE's circuit solver to prevent singular matrices.

**SPICE Implementation:** Applied at circuit level, not in MOS6 device code, but critically affects MOS6 convergence.

### 8. Initial Condition Handling

**Priority Order:**
1. User `.IC` specification (VDS, VGS, VBS) → `inst->MOS6icVDS`, `inst->MOS6icVGS`, `inst->MOS6icVBS`
2. `OFF` flag → forces `V_gs = 0`, `I_ds = 0` (cutoff region)
3. Zero-bias assumption → all voltages = 0

**Implementation in `MOS6load()`:**
```c
/* Check for initial conditions */
if (inst->MOS6icVDSGiven) {
    vds = inst->MOS6icVDS;
    vgs = inst->MOS6icVGS;
    vbs = inst->MOS6icVBS;
} else if (inst->MOS6off) {
    vgs = 0; vds = 0; vbs = 0;
}
```

**Convergence Impact:**
- Proper initial conditions reduce Newton iterations by 40-60%
- `OFF` flag provides guaranteed convergence path for difficult circuits
- Prevents convergence on non-physical operating points

### 9. Alpha-Power Law Numerical Stability

**Power Function Considerations:**
```c
ids = beta * kv * pow(vgst, nv) * (1.0 + lambda * vds);
```

**Numerical Precautions:**
- Check for `vgst ≤ 0` before calling `pow()` to avoid domain errors
- Use `pow(vgst, nc-1)` instead of `pow(vgst, nc)/vgst` for `nc-1` exponent to avoid division by zero
- Handle `nv == nc` special case for `vdsat` calculation to avoid unnecessary `pow()` calls

### 10. Convergence Monitoring

**SPICE Convergence Flags:**
- `ckt->CKTnoncon`: Non-convergence counter (incremented when any device fails convergence)
- `ckt->CKTmode`: Analysis mode (DC_OP, TRAN, AC, etc.)
- `ckt->CKTiter`: Newton-Raphson iteration count

**Device-Specific Storage for Limiting:**
- `inst->MOS6vgs_old`, `inst->MOS6vds_old`, `inst->MOS6vbs_old`: Previous iteration voltages
- Used by `DEVfetlim()` for voltage limiting between iterations

### 11. Fallback Strategies

When standard Newton-Raphson fails, SPICE employs:

**GMIN Stepping:**
Increase `GMIN` from `1e-12` to `1e-3` over 5-10 steps to improve matrix conditioning.

**Source Stepping:**
Gradually ramp source voltages: `V_source(k) = (k/N) × V_source_full` for `k = 0..N`

**Damping:**
Apply damping factor to Newton update: `V_new = V_old + α × ΔV` with `α = 0.5`

### 12. Digital Circuit Optimization

**Convergence Advantages for Digital Circuits:**
1. **No Subthreshold**: Eliminates exponential region with extremely large derivatives
2. **Explicit Regions**: Clear cutoff/linear/saturation boundaries
3. **Alpha-Power Law**: Smooth, well-behaved power functions in each region
4. **Limited Voltage Range**: Digital circuits typically use `V_gs ∈ [0, VDD]`, `V_ds ∈ [0, VDD]`

**Convergence Challenges:**
1. **Discontinuous at V_gst = 0**: `DEVfetlim()` essential for crossing this boundary
2. **Discontinuous derivative at V_ds = V_dsat**: Newton-Raphson can handle with proper limiting
3. **Parameter sensitivity**: Empirical parameters `KV`, `NV`, `KC`, `NC` require careful fitting to measured data

### 13. Algorithmic Convergence Summary

The MOS6 model ensures SPICE convergence through:

1. **Voltage Limiting**: `DEVfetlim()` prevents excessive changes between iterations
2. **Explicit Region Handling**: Clear mathematical definitions for cutoff/linear/saturation
3. **Parameter Validation**: Range checking and clamping prevent numerical errors
4. **Temperature Consistency**: All parameters scaled simultaneously in `MOS6temp()`
5. **Source-Drain Symmetry**: Identical convergence for forward/reverse operation
6. **Digital Optimization**: Simplified model (no subthreshold) reduces convergence issues
7. **SPICE Integration**: Standard convergence checking and fallback strategies
8. **Matrix Conditioning**: Minimum conductance `GMIN` prevents singular matrices
9. **Initial Condition Support**: User ICs and OFF flag provide convergence paths
10. **Numerical Stability**: Careful handling of `pow()` functions and division operations

These mechanisms make the MOS6 model robust for digital circuit simulation while maintaining the accuracy of the Sakurai-Newton alpha-power law formulation for short-channel devices.

## C Implementation

### 1. Core Data Structures (`mos6defs.h`)

The MOS6 implementation uses two primary data structures that directly map mathematical parameters to C variables:

#### `sMOS6model` Structure - Mathematical Parameter Storage

```c
typedef struct sMOS6model {
    int MOS6type;                   /* NMF or PMF - device polarity */
    
    /* Sakurai-Newton alpha-power law parameters */
    double MOS6vt0;                 /* VTO: Zero-bias threshold voltage VTO */
    double MOS6kv;                  /* KV: Saturation voltage coefficient in Vdsat = KV·(Vgst)^NV */
    double MOS6nv;                  /* NV: Saturation voltage exponent */
    double MOS6kc;                  /* KC: Saturation current coefficient in Id = KC·(Vgst)^NC·(1+λVds) */
    double MOS6nc;                  /* NC: Saturation current exponent */
    double MOS6lambda;              /* λ: Channel-length modulation parameter */
    double MOS6beta;                /* β: Transconductance coefficient (alternative to KP) */
    double MOS6gamma;               /* γ: Body effect parameter in Vth = VTO + γ[√(φ-Vbs)-√φ] */
    double MOS6phi;                 /* φ: Surface potential (default 0.6V) */
    
    /* Derived mathematical parameters */
    double MOS6kp;                  /* KP = μ₀·Cox = μ₀·3.9×8.854e-12/TOX */
    double MOS6coxf;                /* Cox = ε₀εᵣ/TOX = 3.9×8.854e-12/TOX */
    
    /* Parameter presence flags */
    unsigned MOS6vt0Given:1;        /* Flag indicating VTO was specified */
    unsigned MOS6kvGiven:1;         /* Flag for KV parameter */
    unsigned MOS6nvGiven:1;         /* Flag for NV parameter */
    /* ... additional given flags for all parameters ... */
    
    /* Linked list structure */
    struct sMOS6model *MOS6nextModel;
    sMOS6instance *MOS6instances;
} MOS6model;
```

**Mathematical Mapping:**
- `MOS6vt0` ↔ VTO (threshold voltage at Vbs=0)
- `MOS6kv`, `MOS6nv` ↔ KV, NV in saturation voltage equation: Vdsat = KV·(Vgst)^NV
- `MOS6kc`, `MOS6nc` ↔ KC, NC in drain current equations
- `MOS6gamma`, `MOS6phi` ↔ γ, φ in body effect calculation
- `MOS6kp` = μ₀·Cox where Cox = 3.9×8.854e-12/TOX

#### `sMOS6instance` Structure - Operating Point and Matrix Pointers

```c
typedef struct sMOS6instance {
    /* Instance identification */
    char *MOS6name;                 /* Instance name from SPICE netlist */
    
    /* SPICE circuit node indices */
    int MOS6dNode;                  /* Drain node (external) */
    int MOS6gNode;                  /* Gate node */
    int MOS6sNode;                  /* Source node (external) */
    int MOS6bNode;                  /* Bulk node */
    int MOS6dNodePrime;             /* Internal drain node (after RD) */
    int MOS6sNodePrime;             /* Internal source node (after RS) */
    
    /* Geometric parameters from netlist */
    double MOS6l;                   /* L: Drawn channel length */
    double MOS6w;                   /* W: Drawn channel width */
    double MOS6ad;                  /* AD: Drain area */
    double MOS6as;                  /* AS: Source area */
    double MOS6pd;                  /* PD: Drain perimeter */
    double MOS6ps;                  /* PS: Source perimeter */
    double MOS6nrd;                 /* NRD: Number of squares in drain */
    double MOS6nrs;                 /* NRS: Number of squares in source */
    
    /* Calculated effective dimensions */
    double MOS6lEff;                /* Leff = L - 2·LD (computed in setup) */
    double MOS6wEff;                /* Weff = W - 2·WD (computed in setup) */
    
    /* Transconductance parameter */
    double MOS6betaEff;             /* β_eff = (Weff/Leff)·KP (temperature-adjusted) */
    
    /* Operating point variables (computed in MOS6load) */
    double MOS6vds;                 /* Vds: Drain-source voltage */
    double MOS6vgs;                 /* Vgs: Gate-source voltage */
    double MOS6vbs;                 /* Vbs: Bulk-source voltage */
    double MOS6vth;                 /* Vth: Threshold voltage with body effect */
    double MOS6vgst;                /* Vgst = Vgs - Vth (overdrive voltage) */
    double MOS6vdsat;               /* Vdsat: Saturation voltage */
    double MOS6cd;                  /* Id: Drain current */
    double MOS6gm;                  /* gm = ∂Id/∂Vgs (transconductance) */
    double MOS6gds;                 /* gds = ∂Id/∂Vds (drain conductance) */
    double MOS6gmbs;                /* gmbs = ∂Id/∂Vbs (body transconductance) */
    
    /* 6×6 Sparse Matrix Pointers for nodes [D, G, S, B, DP, SP] */
    double *MOS6drainDrainPtr;          /* G[0][0] - external drain self-conductance */
    double *MOS6gateGatePtr;            /* G[1][1] - gate self-conductance */
    double *MOS6sourceSourcePtr;        /* G[2][2] - external source self-conductance */
    double *MOS6bulkBulkPtr;            /* G[3][3] - bulk self-conductance */
    double *MOS6drainPrimeDrainPrimePtr;/* G[4][4] - internal drain self-conductance */
    double *MOS6sourcePrimeSourcePrimePtr; /* G[5][5] - internal source self-conductance */
    
    /* Off-diagonal matrix pointers */
    double *MOS6drainDrainPrimePtr;     /* G[0][4] - RD connection */
    double *MOS6drainPrimeDrainPtr;     /* G[4][0] - RD connection (symmetric) */
    double *MOS6sourceSourcePrimePtr;   /* G[2][5] - RS connection */
    double *MOS6sourcePrimeSourcePtr;   /* G[5][2] - RS connection (symmetric) */
    double *MOS6drainPrimeGatePtr;      /* G[4][1] - gm contribution */
    double *MOS6drainPrimeSourcePrimePtr; /* G[4][5] - gds + gm + gmbs contribution */
    double *MOS6drainPrimeBulkPtr;      /* G[4][3] - gmbs contribution */
    /* ... additional matrix pointers ... */
    
    /* Device operation mode */
    int MOS6mode;                    /* 1: normal (Vds≥0), -1: inverted (Vds<0) */
    
    struct sMOS6instance *MOS6nextInstance;
    MOS6model *MOS6modPtr;
} MOS6instance;
```

**Mathematical Mapping:**
- `MOS6lEff`, `MOS6wEff` ↔ Leff = L - 2·LD, Weff = W - 2·WD
- `MOS6betaEff` ↔ β_eff = (Weff/Leff)·KP
- `MOS6vth` ↔ Vth = VTO + γ[√(φ-Vbs)-√φ]
- `MOS6vgst` ↔ Vgst = Vgs - Vth
- `MOS6vdsat` ↔ Vdsat = KV·(Vgst)^NV
- Matrix pointers map to 6×6 conductance matrix for Newton-Raphson iteration

### 2. Parameter Binding and Tables (`mos6mpar.c`, `mos6mask.c`)

#### Parameter Table Definition

```c
static IFparm MOS6mPTable[] = {
    IOP("vto",     MOS6_VTO,    IF_REAL, "Threshold voltage"),
    IOP("kv",      MOS6_KV,     IF_REAL, "Saturation voltage coefficient"),
    IOP("nv",      MOS6_NV,     IF_REAL, "Saturation voltage exponent"),
    IOP("kc",      MOS6_KC,     IF_REAL, "Saturation current coefficient"),
    IOP("nc",      MOS6_NC,     IF_REAL, "Saturation current exponent"),
    IOP("lambda",  MOS6_LAMBDA, IF_REAL, "Channel-length modulation"),
    IOP("beta",    MOS6_BETA,   IF_REAL, "Transconductance coefficient"),
    IOP("gamma",   MOS6_GAMMA,  IF_REAL, "Body effect parameter"),
    IOP("phi",     MOS6_PHI,    IF_REAL, "Surface potential"),
    /* ... 25 additional model parameters ... */
};

static IFparm MOS6pTable[] = {
    IOP("l",       MOS6_L,      IF_REAL, "Channel length"),
    IOP("w",       MOS6_W,      IF_REAL, "Channel width"),
    IOP("ad",      MOS6_AD,     IF_REAL, "Drain area"),
    IOP("as",      MOS6_AS,     IF_REAL, "Source area"),
    IOP("pd",      MOS6_PD,     IF_REAL, "Drain perimeter"),
    IOP("ps",      MOS6_PS,     IF_REAL, "Source perimeter"),
    IOP("nrd",     MOS6_NRD,    IF_REAL, "Number of squares in drain"),
    IOP("nrs",     MOS6_NRS,    IF_REAL, "Number of squares in source"),
    /* ... additional instance parameters ... */
};
```

**Mathematical Mapping:**
- Each `IOP` macro maps a SPICE netlist parameter name to an integer constant
- `MOS6_VTO` (101) ↔ `model->MOS6vt0` in C structure
- `MOS6_KV` (102) ↔ `model->MOS6kv` in C structure
- `MOS6_L` (1) ↔ `inst->MOS6l` in instance structure

#### Parameter Mask Definitions

```c
#define MOS6_L        1
#define MOS6_W        2
#define MOS6_AD       3
#define MOS6_AS       4
/* ... instance parameter masks ... */

#define MOS6_VTO      101
#define MOS6_KV       102
#define MOS6_NV       103
#define MOS6_KC       104
#define MOS6_NC       105
#define MOS6_LAMBDA   106
#define MOS6_BETA     107
#define MOS6_GAMMA    108
#define MOS6_PHI      109
/* ... model parameter masks ... */
```

**Implementation Purpose:**
- Masks provide integer identifiers for parameter lookup
- Used in `MOS6setup()` to check which parameters were specified
- Enable default value assignment for unspecified parameters

### 3. Setup and Matrix Allocation (`mos6set.c`)

The `MOS6setup()` function performs mathematical transformations and allocates SPICE matrix resources:

```c
int MOS6setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS6model *model = (MOS6model *)inModel;
    MOS6instance *inst;
    int nodeArray[6];  /* D, G, S, B, DP, SP */
    
    for (; model; model = model->MOS6nextModel) {
        /* --- MATHEMATICAL DEFAULT VALUES --- */
        /* Set defaults for unspecified parameters */
        if (!model->MOS6vt0Given)    model->MOS6vt0 = 0.0;
        if (!model->MOS6kvGiven)     model->MOS6kv = 1.0;
        if (!model->MOS6nvGiven)     model->MOS6nv = 1.0;
        if (!model->MOS6kcGiven)     model->MOS6kc = 2e-5;
        if (!model->MOS6ncGiven)     model->MOS6