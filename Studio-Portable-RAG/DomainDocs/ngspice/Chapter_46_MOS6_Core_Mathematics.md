# MOSFET Level 6: Sakurai-Newton Digital Model and DC Load

_Generated 2026-04-12 06:55 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/include/ngspice/devdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6load.c`

# MOSFET Level 6: Sakurai-Newton Digital Model and DC Load

## Technical Introduction

This chapter details the implementation of the MOS6 (Level 6) Sakurai-Newton empirical MOSFET model in Ngspice. The MOS6 model is specifically designed for digital circuit simulation, implementing an alpha-power law formulation that accurately captures short-channel effects without the complexity of subthreshold modeling. Four core files implement the model:

- **`devdefs.h`** - Provides the generic SPICE device framework structures that MOS6 inherits from, defining the interface between device models and the SPICE simulator core.

- **`mos6par.c`** - Implements parameter parsing and binding, mapping SPICE netlist parameters to the `MOS6model` and `MOS6instance` structures with proper default values and validation.

- **`mos6temp.c`** - Handles temperature-dependent parameter scaling through the `MOS6temp()` function, adjusting threshold voltage, mobility, junction potentials, and saturation currents based on operating temperature using semiconductor physics equations.

- **`mos6load.c`** - Implements the main DC load function `MOS6load()` that computes the Sakurai-Newton drain current equations, calculates partial derivatives for the Jacobian matrix, and stamps the conductance matrix and current vector into SPICE's circuit matrices for Newton-Raphson iteration.

These files collectively implement a computationally efficient model optimized for digital switching circuits, featuring source-drain symmetry, Newton-Raphson convergence limiting via `DEVfetlim()`, and empirical fitting parameters `(KV, NV, KC, NC)` for velocity saturation effects characteristic of short-channel devices.

## Mathematical Formulation

The MOS6 Level 6 model implements the Sakurai-Newton empirical equations using an alpha-power law formulation optimized for digital circuit simulation. The mathematics directly maps to SPICE's DC operating point calculation and Newton-Raphson iteration requirements.

### 1. Threshold Voltage with Body Effect

The threshold voltage calculation includes the body effect for substrate bias:

```
V_th = VTO + γ × [√(φ + V_sb) - √φ]
```

**SPICE Implementation Mapping:**
- `VTO` → `model->MOS6vto` (zero-bias threshold voltage)
- `γ` → `model->MOS6gamma` (body effect parameter)
- `φ` → `model->MOS6phi` (surface potential, default 0.6V)
- `V_sb` → `vbs` (source-bulk voltage computed from circuit nodes)

In C code (`mos6load.c`):
```c
vth = model->MOS6vto + gamma * (sqrt(phi + vbs) - sqrt(phi));
```

### 2. Effective Channel Dimensions

The effective dimensions account for lateral diffusion:

```
L_eff = L - 2 × LD
W_eff = W - 2 × WD
```

**SPICE Implementation Mapping:**
- `L` → `inst->MOS6l` (drawn channel length)
- `W` → `inst->MOS6w` (drawn channel width)
- `LD` → `model->MOS6ld` (lateral diffusion length)
- `WD` → `model->MOS6wd` (lateral diffusion width)

These are computed during setup and stored as `inst->MOS6effL` and `inst->MOS6effW`.

### 3. Transconductance Parameter β

The transconductance parameter combines geometry and process parameters:

```
β = (W_eff / L_eff) × KP
```

Where `KP = μ₀ × ε₀ₓ / t₀ₓ = μ₀ × 3.9 × 8.854e-12 / TOX`

**SPICE Implementation Mapping:**
- `μ₀` → `model->MOS6u0` (low-field mobility)
- `TOX` → `model->MOS6tox` (oxide thickness)
- `KP` → Computed from `u0` and `tox`, or directly specified as `model->MOS6kp`

In C code (`mos6temp.c`):
```c
inst->MOS6beta = (inst->MOS6effW / inst->MOS6effL) * u0 * 3.9 * 8.854e-12 / model->MOS6tox;
```

### 4. Sakurai-Newton Alpha-Power Law Current Equations

#### Gate Overdrive Voltage:
```
V_gst = V_gs - V_th
```

#### Saturation Voltage:
```
V_dsat = (KV / KC) × (V_gst)^(NV - NC)
```

#### Linear Region (V_ds ≤ V_dsat):
```
I_ds = β × KC × (V_gst)^NC × V_ds
```

#### Saturation Region (V_ds > V_dsat):
```
I_ds = β × KV × (V_gst)^NV × [1 + λ × V_ds]
```

**SPICE Implementation Mapping:**
- `KV` → `model->MOS6kv` (saturation region factor)
- `NV` → `model->MOS6nv` (saturation region exponent)
- `KC` → `model->MOS6kc` (linear region factor)
- `NC` → `model->MOS6nc` (linear region exponent)
- `λ` → `model->MOS6lambda` (channel-length modulation)

In C code (`mos6load.c`):
```c
if (vds <= vdsat) {
    /* Linear region */
    ids = beta * kc * pow(vgst, nc) * vds;
} else {
    /* Saturation region */
    ids = beta * kv * pow(vgst, nv) * (1 + lambda * vds);
}
```

### 5. Partial Derivatives for Newton-Raphson Jacobian

#### Transconductance (gm):
```
gm = ∂I_ds/∂V_gs = 
    Linear: β × KC × NC × (V_gst)^(NC-1) × V_ds
    Saturation: β × KV × NV × (V_gst)^(NV-1) × [1 + λ × V_ds]
```

#### Drain Conductance (gds):
```
gds = ∂I_ds/∂V_ds = 
    Linear: β × KC × (V_gst)^NC
    Saturation: β × KV × (V_gst)^NV × λ
```

#### Bulk Transconductance (gmb):
```
gmb = ∂I_ds/∂V_bs = gm × [γ / (2 × √(φ + V_sb))]
```

**SPICE Implementation Mapping:**
These derivatives are computed in `MOS6load()` and stamped into the conductance matrix for Newton-Raphson iteration:
- `gm` → `inst->MOS6gm` (stamped as `G_dg` and `G_sg` matrix entries)
- `gds` → `inst->MOS6gds` (stamped as `G_dd` and `G_ss` matrix entries)
- `gmb` → `inst->MOS6gmb` (stamped as `G_db` and `G_sb` matrix entries)

### 6. Temperature-Dependent Parameter Scaling

#### Threshold Voltage Temperature Scaling:
```
V_TO(T) = V_TO(T_nom) - TC1·(T - T_nom) - TC2·(T - T_nom)²
```

#### Mobility Temperature Degradation:
```
μ(T) = μ(T_nom)·(T/T_nom)^{-1.5}
```

#### Junction Potential Temperature Scaling:
```
PB(T) = PB(T_nom)·(T/T_nom) - 3·V_T·ln(T/T_nom) - E_g(T)·(T/T_nom) + E_g(T_nom)
```

**SPICE Implementation Mapping:**
Implemented in `MOS6temp()` function:
- `T_nom` → `model->MOS6tnom` (nominal temperature)
- `TC1`, `TC2` → `model->MOS6tc1`, `model->MOS6tc2` (temperature coefficients)
- `E_g(T)` → Bandgap energy computed as `1.16 - 7.02e-4 * temp² / (temp + 1108.0)`

### 7. Matrix Stamping Pattern for 4-Terminal Device

The conductance matrix follows SPICE's 4×4 formulation:

```
[ G_dd   G_dg   G_ds   G_db ] [ V_d ]   [ I_d ]
[ G_gd   G_gg   G_gs   G_gb ] [ V_g ] = [ I_g ]
[ G_sd   G_sg   G_ss   G_sb ] [ V_s ]   [ I_s ]
[ G_bd   G_bg   G_bs   G_bb ] [ V_b ]   [ I_b ]
```

**Non-zero entries for normal mode (V_ds ≥ 0):**
- `G_dd = +gds`, `G_ds = -gds - gm - gmb`, `G_dg = +gm`, `G_db = +gmb`
- `G_sd = -gds`, `G_ss = +gds + gm + gmb`, `G_sg = -gm`, `G_sb = -gmb`
- Gate terms (`G_g*`) are zero (ideal gate insulation)
- Bulk terms complete the symmetry

**SPICE Implementation Mapping:**
Each matrix entry has a corresponding pointer in `sMOS6instance`:
- `G_dd` → `inst->MOS6drainDrainPtr`
- `G_dg` → `inst->MOS6drainGatePtr`
- `G_ds` → `inst->MOS6drainSourcePtr`
- etc.

### 8. Source-Drain Swap Mechanics

When `V_ds < 0`, the device operates in reverse mode with swapped terminals:

**Voltage Transformations:**
```
V_ds' = -V_ds
V_gs' = V_gs - V_ds  (becomes V_gd)
V_bs' = V_bs + V_ds  (becomes V_bd)
```

**Matrix Stamping Adjustment:**
- Drain and source matrix entries are swapped
- Current direction is reversed

**SPICE Implementation Mapping:**
In `MOS6load()`:
```c
if (vds >= 0) {
    mode = 1;  /* Normal mode */
} else {
    mode = -1; /* Reverse mode */
    /* Swap voltages */
    double tmp = vds;
    vds = -vds;
    vgs = vgs - tmp;
    vbs = vbs + tmp;
}
```

### 9. Newton-Raphson Voltage Limiting (DEVfetlim)

The `DEVfetlim()` function prevents excessive voltage changes between Newton iterations:

**Mathematical Formulation:**
- For `vold ≥ vto` (ON region):
  - If `delv ≤ 0`: `vnew = vold - 2·V_T·ln(1 + (vold - vnew)/(2·V_T))`
  - If `delv > 0`: `vnew = vold + V_T·ln(1 + delv/V_T)`
- For `vold < vto` (OFF region):
  - If `delv ≥ 0`: `vnew = vold + 2·V_T·ln(1 + (vnew - vold)/(2·V_T))`
  - If `delv < 0`: `vnew = vold - V_T·ln(1 - delv/V_T)`

Where `V_T = kT/q ≈ 0.026V` at 300K.

**SPICE Implementation Mapping:**
Applied to `V_gs`, `V_ds`, and `V_bs` before current calculation:
```c
vgs = DEVfetlim(vgs, inst->MOS6vgs_old, model->MOS6vto);
vds = DEVfetlim(vds, inst->MOS6vds_old, 0.0);
vbs = DEVfetlim(vbs, inst->MOS6vbs_old, 0.0);
```

### 10. Cutoff Region Handling

The MOS6 model has no subthreshold conduction:
- For `V_gst ≤ 0`: `I_ds = 0`, `gm = 0`, `gds = 0`, `gmb = 0`
- This discontinuity is acceptable for digital circuits where devices operate in strong inversion or cutoff

**SPICE Implementation Mapping:**
```c
if (vgst <= 0) {
    ids = 0;
    gm = 0;
    gds = 0;
    gmb = 0;
}
```

### 11. Parameter Defaults and Validation

**Critical Default Values (from `mos6par.c`):**
```c
if (!model->MOS6vtoGiven) model->MOS6vto = 0.0;
if (!model->MOS6kpGiven)  model->MOS6kp = 2e-5;
if (!model->MOS6gammaGiven) model->MOS6gamma = 0.0;
if (!model->MOS6phiGiven) model->MOS6phi = 0.6;
if (!model->MOS6lambdaGiven) model->MOS6lambda = 0.0;
if (!model->MOS6kvGiven) model->MOS6kv = 1.0;
if (!model->MOS6nvGiven) model->MOS6nv = 2.0;
if (!model->MOS6kcGiven) model->MOS6kc = 1.0;
if (!model->MOS6ncGiven) model->MOS6nc = 1.0;
```

**Parameter Validation:**
```c
if (model->MOS6phi <= 0.0) {
    model->MOS6phi = 0.6;  /* Must be positive */
}
if (inst->MOS6effL <= 0.0) {
    inst->MOS6effL = 1e-12;  /* Prevent division by zero */
}
if (inst->MOS6effW <= 0.0) {
    inst->MOS6effW = 1e-12;
}
```

### 12. SPICE Integration Summary

The MOS6 mathematical formulation directly supports SPICE's analysis requirements:

1. **DC Operating Point**: Current equations provide `I_ds` for KCL satisfaction
2. **Newton-Raphson Iteration**: Derivatives `gm`, `gds`, `gmb` form the Jacobian matrix
3. **Convergence Control**: `DEVfetlim()` prevents oscillation and divergence
4. **Temperature Analysis**: `MOS6temp()` scales parameters for temperature sweeps
5. **Bidirectional Operation**: Source-drain swap enables symmetric behavior
6. **Digital Optimization**: No subthreshold modeling reduces computation for switching circuits

The alpha-power law with separate `(KV, NV)` and `(KC, NC)` parameters provides empirical fitting to measured short-channel device characteristics while maintaining computational efficiency for digital circuit simulation.

## Convergence Analysis

### 1. Newton-Raphson Convergence Criteria

The MOS6 model implements SPICE's standard convergence checking for the Newton-Raphson iterative solver:

**Voltage Convergence Test:**
For each terminal voltage `V` (V_gs, V_ds, V_bs):
```
|V_new - V_old| ≤ reltol·max(|V_new|, |V_old|) + vntol
```

**Current Convergence Test:**
For drain current `I_ds`:
```
|I_ds_new - I_ds_old| ≤ reltol·max(|I_ds_new|, |I_ds_old|) + abstol
```

**SPICE Implementation Parameters:**
- `reltol = CKTreltol = 0.001` (default relative tolerance)
- `vntol = CKTvoltTol = 1e-6` (default voltage absolute tolerance)
- `abstol = CKTabstol = 1e-12` (default current absolute tolerance)

### 2. DEVfetlim Voltage Limiting Algorithm

The `DEVfetlim()` function ensures convergence by preventing excessive voltage changes:

**Mathematical Implementation:**
```c
double DEVfetlim(double vnew, double vold, double vto) {
    double vt = 0.026;  /* Thermal voltage at 300K */
    double delv = vnew - vold;
    
    if (vold >= vto) {
        if (delv <= 0) {
            /* Transition from ON to OFF */
            if (vnew >= vto + 0.5) {
                return vnew;
            } else {
                return vold - 2 * vt * log(1 + (vold - vnew) / (2 * vt));
            }
        } else {
            /* Increasing in ON region */
            return vold + vt * log(1 + delv / vt);
        }
    } else {
        if (delv >= 0) {
            /* Transition from OFF to ON */
            if (vnew <= vto - 0.5) {
                return vnew;
            } else {
                return vold + 2 * vt * log(1 + (vnew - vold) / (2 * vt));
            }
        } else {
            /* Decreasing in OFF region */
            return vold - vt * log(1 - delv / vt);
        }
    }
}
```

**Convergence Impact:**
- Logarithmic limiting prevents overshoot when crossing the threshold voltage `vto`
- Maintains derivative continuity for Newton-Raphson convergence
- Different limiting for ON→OFF vs OFF→ON transitions

### 3. Region Boundary Handling

The MOS6 model has explicit region boundaries that affect convergence:

**Cutoff/Linear Boundary (V_gst = 0):**
- Discontinuous transition: `I_ds = 0` for `V_gst ≤ 0`, `I_ds > 0` for `V_gst > 0`
- No subthreshold modeling simplifies convergence for digital circuits
- `DEVfetlim()` ensures smooth voltage transitions across this boundary

**Linear/Saturation Boundary (V_ds = V_dsat):**
- Continuous current: `I_ds_linear(V_dsat) = I_ds_sat(V_dsat)`
- Discontinuous first derivative: `gds` jumps at boundary
- Newton-Raphson can handle this with proper limiting

### 4. Source-Drain Swap Convergence Symmetry

The automatic source-drain swapping ensures consistent convergence:

**Swap Conditions:**
- `V_ds < 0` triggers reverse mode operation
- Internal voltage transformation maintains mathematical consistency
- Matrix stamping adjusted to reflect terminal swapping

**Convergence Benefit:**
- Identical convergence properties for forward and reverse bias
- No special-case handling needed in Newton-Raphson solver
- Symmetric Jacobian matrix conditioning

### 5. Parameter Validation for Numerical Stability

**Effective Dimension Clamping:**
```c
if (inst->MOS6effL <= 0.0) {
    inst->MOS6effL = 1e-12;  /* Prevent division by zero */
}
if (inst->MOS6effW <= 0.0) {
    inst->MOS6effW = 1e-12;
}
```

**Parameter Range Checking:**
- `phi > 0` (surface potential must be positive)
- `nv > 0`, `nc > 0` (exponents must be positive)
- `kv > 0`, `kc > 0` (factors must be positive)

### 6. Temperature Consistency Enforcement

**Temperature Scaling Application:**
```c
if (inst->MOS6temp != ckt->CKTtemp) {
    MOS6temp(model, inst, ckt);  /* Apply temperature scaling */
}
```

**Convergence Requirement:**
- All temperature-dependent parameters updated simultaneously
- Prevents inconsistency between `vth`, `beta`, and other parameters
- Ensures self-consistent operating point at new temperature

### 7. Matrix Conditioning

**Minimum Conductance Addition:**
```
G_min = GMIN = 1e-12 Ʊ (default)
```
Added to diagonal entries to prevent singular matrices.

**SPICE Implementation:**
Applied by circuit solver, not in device code, but affects MOS6 convergence.

### 8. Initial Condition Handling

**Priority Order:**
1. User `.IC` specification (VDS, VGS, VBS)
2. `OFF` flag (forces cutoff region)
3. Zero-bias assumption (all voltages = 0)

**Implementation in `MOS6load()`:**
```c
/* Check for initial conditions */
if (inst->MOS6icGiven) {
    vds = inst->MOS6icVDS;
    vgs = inst->MOS6icVGS;
    vbs = inst->MOS6icVBS;
} else if (inst->MOS6off) {
    vgs = 0; vds = 0; vbs = 0;
}
```

**Convergence Impact:**
- Proper initial conditions reduce Newton iterations
- `OFF` flag provides guaranteed convergence path

### 9. Alpha-Power Law Numerical Stability

**Power Function Considerations:**
```c
ids = beta * kv * pow(vgst, nv) * (1 + lambda * vds);
```

**Numerical Precautions:**
- Check for `vgst ≤ 0` before calling `pow()`
- Use `pow(vgst, nc-1)` instead of `pow(vgst, nc)/vgst` for `nc-1` exponent
- Handle `nv == nc` special case for `vdsat` calculation

### 10. Convergence Monitoring

**SPICE Convergence Flags:**
- `ckt->CKTnoncon`: Non-convergence counter
- `ckt->CKTmode`: Analysis mode (DC_OP, TRAN, etc.)
- `ckt->CKTiter`: Newton-Raphson iteration count

**Device-Specific Storage:**
- `inst->MOS6vgs_old`, `inst->MOS6vds_old`, `inst->MOS6vbs_old`: Previous iteration voltages
- Used by `DEVfetlim()` for voltage limiting

### 11. Fallback Strategies

**GMIN Stepping:**
If Newton-Raphson fails, SPICE increases `GMIN` from `1e-12` to `1e-3` over several steps to improve matrix conditioning.

**Source Stepping:**
Gradually ramp source voltages: `V_source(k) = (k/N)·V_source_full`

**Damping:**
Apply damping factor to Newton update: `V_new = V_old + α·ΔV` with `α = 0.5`

### 12. Digital Circuit Optimization

**Convergence Advantages for Digital Circuits:**
1. **No Subthreshold**: Eliminates exponential region with large derivatives
2. **Explicit Regions**: Clear cutoff/linear/saturation boundaries
3. **Alpha-Power Law**: Smooth, well-behaved functions in each region
4. **Limited Voltage Range**: Digital circuits typically use `V_gs ∈ [0, VDD]`, `V_ds ∈ [0, VDD]`

**Convergence Challenges:**
1. **Discontinuous at V_gst = 0**: `DEVfetlim()` essential for crossing this boundary
2. **Discontinuous derivative at V_ds = V_dsat**: Newton-Raphson can handle with proper limiting
3. **Parameter sensitivity**: Empirical parameters `KV`, `NV`, `KC`, `NC` require careful fitting

### 13. Algorithmic Convergence Summary

The MOS6 model ensures SPICE convergence through:

1. **Voltage Limiting**: `DEVfetlim()` prevents excessive changes between iterations
2. **Explicit Region Handling**: Clear mathematical definitions for cutoff/linear/saturation
3. **Parameter Validation**: Range checking and clamping prevent numerical errors
4. **Temperature Consistency**: All parameters scaled simultaneously
5. **Source-Drain Symmetry**: Identical convergence for forward/reverse operation
6. **Digital Optimization**: Simplified model reduces convergence issues
7. **SPICE Integration**: Standard convergence checking and fallback strategies

These mechanisms make the MOS6 model robust for digital circuit simulation while maintaining the accuracy of the Sakurai-Newton alpha-power law formulation for short-channel devices.

## C Implementation

### 1. Core Data Structures (`mos6defs.h`)

The MOS6 implementation centers around two primary data structures that map directly to the mathematical model parameters:

#### `sMOS6model` Structure - Mathematical Parameter Mapping

```c
typedef struct sMOS6model {
    int MOS6type;                   /* NMF or PMF - device polarity */
    
    /* Sakurai-Newton alpha-power law parameters */
    double MOS6vto;                 /* VTO: Threshold voltage at Vbs=0 */
    double MOS6kv;                  /* KV: Saturation region factor in I_ds = β × KV × (V_gst)^NV */
    double MOS6nv;                  /* NV: Saturation region exponent */
    double MOS6kc;                  /* KC: Linear region factor in I_ds = β × KC × (V_gst)^NC × V_ds */
    double MOS6nc;                  /* NC: Linear region exponent */
    
    /* Physical parameters */
    double MOS6gamma;               /* γ: Body effect parameter in V_th = VTO + γ[√(φ+V_sb)-√φ] */
    double MOS6phi;                 /* φ: Surface potential (default 0.6V) */
    double MOS6lambda;              /* λ: Channel-length modulation in saturation region */
    
    /* Geometry and process parameters */
    double MOS6ld;                  /* LD: Lateral diffusion for L_eff = L - 2×LD */
    double MOS6wd;                  /* WD: Width diffusion for W_eff = W - 2×WD */
    double MOS6u0;                  /* μ₀: Low-field mobility for β calculation */
    double MOS6tox;                 /* TOX: Oxide thickness for KP = μ₀ × 3.9×8.854e-12/TOX */
    
    /* Temperature parameters */
    double MOS6tnom;                /* T_nom: Nominal temperature for scaling */
    double MOS6tc1;                 /* TC1: Linear temperature coefficient for VTO */
    double MOS6tc2;                 /* TC2: Quadratic temperature coefficient for VTO */
    
    /* Parameter presence flags */
    int MOS6vtoGiven;               /* Flag indicating VTO was specified by user */
    int MOS6kvGiven;                /* Flag for KV parameter */
    /* ... additional given flags for each parameter ... */
    
    /* Linked list structure */
    struct sMOS6model *MOS6nextModel;
    sMOS6instance *MOS6instances;
} MOS6model;
```

#### `sMOS6instance` Structure - Operating Point Storage

```c
typedef struct sMOS6instance {
    /* Instance identification */
    char *MOS6name;                 /* Instance name from SPICE netlist */
    
    /* SPICE circuit node indices */
    int MOS6dNode;                  /* Drain node index in circuit matrix */
    int MOS6gNode;                  /* Gate node index */
    int MOS6sNode;                  /* Source node index */
    int MOS6bNode;                  /* Bulk node index */
    
    /* Geometry parameters from netlist */
    double MOS6l;                   /* L: Drawn channel length */
    double MOS6w;                   /* W: Drawn channel width */
    
    /* Calculated effective dimensions */
    double MOS6effL;                /* L_eff = L - 2×LD (computed in setup) */
    double MOS6effW;                /* W_eff = W - 2×WD (computed in setup) */
    
    /* Transconductance parameter */
    double MOS6beta;                /* β = (W_eff/L_eff) × KP (temperature-adjusted) */
    
    /* Operating point variables */
    double MOS6vth;                 /* V_th: Threshold voltage including body effect */
    double MOS6mode;                /* Operation mode: 1=normal, -1=reverse (source-drain swapped) */
    
    /* Small-signal parameters (Jacobian entries) */
    double MOS6gm;                  /* g_m = ∂I_ds/∂V_gs (computed in MOS6load) */
    double MOS6gds;                 /* g_ds = ∂I_ds/∂V_ds */
    double MOS6gmb;                 /* g_mb = ∂I_ds/∂V_bs */
    
    /* Terminal currents */
    double MOS6cd;                  /* I_ds: Drain current */
    
    /* Previous iteration voltages for DEVfetlim */
    double MOS6vgs_old;             /* V_gs from previous Newton iteration */
    double MOS6vds_old;             /* V_ds from previous iteration */
    double MOS6vbs_old;             /* V_b from previous iteration */
    
    /* Sparse matrix pointers for 4×4 conductance matrix */
    double *MOS6drainDrainPtr;      /* G_dd = +g_ds */
    double *MOS6drainGatePtr;       /* G_dg = +g_m */
    double *MOS6drainSourcePtr;     /* G_ds = -g_ds - g_m - g_mb */
    double *MOS6drainBulkPtr;       /* G_db = +g_mb */
    /* ... 12 more matrix pointers for complete 4×4 matrix ... */
    
    /* Linked list pointer */
    struct sMOS6instance *MOS6nextInstance;
    MOS6model *MOS6modPtr;          /* Pointer to parent model structure */
} MOS6instance;
```

### 2. Parameter Parsing Implementation (`mos6par.c`)

The parameter parsing functions map SPICE netlist parameters to the C data structures:

```c
/* Parameter table for instance parameters */
IFparm MOS6pTable[] = {
    IOP("l",       MOS6_L,        IF_REAL, "Length"),
    IOP("w",       MOS6_W,        IF_REAL, "Width"),
    IOP("ad",      MOS6_AD,       IF_REAL, "Drain area"),
    IOP("as",      MOS6_AS,       IF_REAL, "Source area"),
    IOP("pd",      MOS6_PD,       IF_REAL, "Drain perimeter"),
    IOP("ps",      MOS6_PS,       IF_REAL, "Source perimeter"),
    IOP("nrd",     MOS6_NRD,      IF_REAL, "Drain squares"),
    IOP("nrs",     MOS6_NRS,      IF_REAL, "Source squares"),
    IOP("off",     MOS6_OFF,      IF_FLAG, "Device initially off"),
    IOP("ic",      MOS6_IC,       IF_REALVEC, "Initial conditions"),
    IOP("temp",    MOS6_TEMP,     IF_REAL, "Instance temperature"),
    IP("vds",      MOS6_IC_VDS,   IF_REAL, "Initial VDS"),
    IP("vgs",      MOS6_IC_VGS,   IF_REAL, "Initial VGS"),
    IP("vbs",      MOS6_IC_VBS,   IF_REAL, "Initial VBS"),
};

/* Parameter table for model parameters */
IFparm MOS6mPTable[] = {
    OP("vto",      MOS6_VTO,      IF_REAL, "Threshold voltage"),
    OP("kv",       MOS6_KV,       IF_REAL, "Saturation factor"),
    OP("nv",       MOS6_NV,       IF_REAL, "Saturation exponent"),
    OP("kc",       MOS6_KC,       IF_REAL, "Linear factor"),
    OP("nc",       MOS6_NC,       IF_REAL, "Linear exponent"),
    OP("gamma",    MOS6_GAMMA,    IF_REAL, "Body effect parameter"),
    OP("phi",      MOS6_PHI,      IF_REAL, "Surface potential"),
    OP("lambda",   MOS6_LAMBDA,   IF_REAL, "Channel length modulation"),
    OP("rd",       MOS6_RD,       IF_REAL, "Drain resistance"),
    OP("rs",       MOS6_RS,       IF_REAL, "Source resistance"),
    OP("cbd",      MOS6_CBD,      IF_REAL, "B-D junction capacitance"),
    OP("cbs",      MOS6_CBS,      IF_REAL, "B-S junction capacitance"),
    OP("is",       MOS6_IS,       IF_REAL, "Junction saturation current"),
    OP("pb",       MOS6_PB,       IF_REAL, "Junction potential"),
    OP("cgso",     MOS6_CGSO,     IF_REAL, "Gate-source overlap capacitance"),
    OP("cgdo",     MOS6_CGDO,     IF_REAL, "Gate-drain overlap capacitance"),
    OP("cgb",      MOS6_CGBO,     IF_REAL, "Gate-bulk overlap capacitance"),
    OP("rsh",      MOS6_RSH,      IF_REAL, "Sheet resistance"),
    OP("cj",       MOS6_CJ,       IF_REAL, "Bottom junction capacitance"),
    OP("mj",       MOS6_MJ,       IF_REAL, "Bottom grading coefficient"),
    OP("cjsw",     MOS6_CJSW,     IF_REAL, "Sidewall capacitance"),
    OP("mjsw",     MOS6_MJSW,     IF_REAL, "Sidewall grading coefficient"),
    OP("js",       MOS6_JS,       IF_REAL, "Junction saturation current density"),
    OP("tox",      MOS6_TOX,      IF_REAL, "Oxide thickness"),
    OP("ld",       MOS6_LD,       IF_REAL, "Lateral diffusion"),
    OP("wd",       MOS6_WD,       IF_REAL, "Width diffusion"),
    OP("u0",       MOS6_U0,       IF_REAL, "Low-field mobility"),
    OP("fc",       MOS6_FC,       IF_REAL, "Forward bias junction fit parameter"),
    OP("tnom",     MOS6_TNOM,     IF_REAL, "Nominal temperature"),
    OP("kf",       MOS6_KF,       IF_REAL, "Flicker noise coefficient"),
    OP("af",       MOS6_AF,       IF_REAL, "Flicker noise exponent"),
    OP("type",     MOS6_TYPE,     IF_STRING, "N-channel or P-channel MOS"),
};
```

### 3. Temperature Scaling Implementation (`mos6temp.c`)

The `MOS6temp()` function implements the temperature-dependent parameter scaling:

```c
void MOS6temp(MOS6model *model, MOS6instance *inst, CKTcircuit *ckt) {
    /* Convert to Kelvin */
    double tnom = model->MOS6tnom + CONSTCtoK;
    double temp = inst->MOS6temp + CONSTCtoK + ckt->CKTdeltaTemp;
    double ratio = temp / tnom;
    
    /* Thermal voltages */
    double vt = KoverQ * temp;           /* kT/q at instance temperature */
    double vtnom = KoverQ * tnom;        /* kT/q at nominal temperature */
    
    /* Bandgap energy temperature dependence */
    double eg = 1.16 - 7.02e-4 * temp * temp / (temp + 1108.0);
    double egnom = 1.16 - 7.02e-4 * tnom * tnom / (tnom + 1108.0);
    
    /* --- Threshold Voltage Temperature Scaling --- */
    /* V_TO(T) = V_TO(T_nom) - TC1·(T - T_nom) - TC2·(T - T_nom)² */
    double vt0 = model->MOS6vto - model->MOS6tc1 * (temp - tnom) 
                 - model->MOS6tc2 * (temp - tnom) * (temp - tnom);
    
    /* --- Mobility Temperature Degradation --- */
    /* μ(T) = μ(T_nom)·(T/T_nom)^{-1.5} */
    double u0 = model->MOS6u0 * pow(ratio, -1.5);
    
    /* --- Junction Potential Temperature Scaling --- */
    /* PB(T) = PB(T_nom)·(T/T_nom) - 3·V_T·ln(T/T_nom) - E_g(T)·(T/T_nom) + E_g(T_nom) */
    double pb = model->MOS6pb * ratio - 3 * vt * log(ratio) 
                - eg * ratio + egnom;
    
    /* --- Surface Potential Temperature Scaling --- */
    /* φ(T) = φ(T_nom)·(T/T_nom) - 2·V_T·ln(T/T_nom) */
    double phi = model->MOS6phi * ratio - 2 * vt * log(ratio);
    
    /* --- Saturation Current Temperature Scaling --- */
    /* IS(T) = IS(T_nom)·exp((E_g/V_T)·(1 - T/T_nom)) */
    double is = model->MOS6is * exp((egnom / vtnom) * (1.0 - ratio));
    
    /* --- Update Instance Parameters --- */
    inst->MOS6vth = vt0;  /* Store temperature-adjusted threshold */
    
    /* Recalculate β with temperature-adjusted mobility */
    /* β = (W_eff/L_eff) × μ₀ × ε₀ₓ / t₀ₓ */
    inst->MOS6beta = (inst->MOS6effW / inst->MOS6effL) * 
                     u0 * 3.9 * 8.