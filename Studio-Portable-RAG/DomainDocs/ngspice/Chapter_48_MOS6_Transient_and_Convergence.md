# MOS6: Transient Control and Convergence Checking

_Generated 2026-04-12 07:26 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6trun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6conv.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos6/mos6ic.c`

# MOS6: Transient Control and Convergence Checking

## Technical Introduction

Within the Ngspice EDA codebase, the MOS6 (Level 6) Sakurai-Newton empirical MOSFET model's transient analysis and convergence checking are implemented across three specialized C files that extend the core DC model. These files provide the mathematical and computational infrastructure for time-domain simulation stability and accuracy, which are critical for digital circuit verification where switching speed and signal integrity are paramount.

**`mos6trun.c`** implements the local truncation error (LTE) control function `MOS6trunc()`, which calculates charge-based error estimates for adaptive time step control. This file manages the state vector containing gate and junction charges (`MOS6qgs`, `MOS6qgd`, `MOS6qgb`, `MOS6qbd`, `MOS6qbs`) and computes the error bound `ε_charge = |dq_total/Δt|` to determine when the time step must be reduced to maintain simulation accuracy within specified tolerances (`CKTtrtol`, `CKTchgtol`).

**`mos6conv.c`** contains the convergence testing function `MOS6convTest()`, which implements SPICE's mixed absolute-relative tolerance checking for Newton-Raphson iteration stability. This file evaluates voltage changes (`ΔVgs`, `ΔVds`, `ΔVbs`) and current changes (`ΔIds`) against convergence criteria, returning `OK` only when all variables satisfy `|Δx| ≤ reltol·max(|x_new|, |x_old|) + abstol`. It serves as the primary gatekeeper for iteration termination in both DC and transient analyses.

**`mos6ic.c`** implements the initial condition handling function `MOS6ic()`, which applies user-specified initial voltages (`.IC` cards) and processes the `OFF` flag to ensure physically reasonable starting points for Newton-Raphson iterations. This file follows a strict priority hierarchy: explicit IC specifications override the `OFF` flag, which in turn overrides zero-bias assumptions, providing multiple pathways to achieve convergence in difficult circuits.

Together, these three files transform the basic MOS6 DC model into a robust transient simulation engine capable of handling the rapid switching transitions characteristic of digital circuits while maintaining numerical stability through comprehensive convergence checking and adaptive time step control.

---

## Mathematical Formulation

The MOS6 Level 6 model implements the Sakurai-Newton empirical alpha-power law formulation with specific mathematical constructs for transient analysis and convergence control in SPICE simulation. These formulations directly support SPICE's time-domain analysis, Newton-Raphson iteration stability, and adaptive time step control.

### 1. Threshold Voltage with DIBL and Temperature Effects

The threshold voltage calculation incorporates drain-induced barrier lowering (DIBL) and temperature dependencies:

```
V_th = VTO + γ·[√(2φ + V_sb) - √(2φ)] + η·V_ds
```

**Temperature Scaling:**
```
VTO(T) = VTO(T_nom) - KT1·(T - T_nom) - KT1L/L_eff·(T - T_nom) - KT2·(T² - T_nom²)
```

**SPICE Implementation Mapping:**
- `VTO` → `model->MOS6vto` (zero-bias threshold voltage)
- `γ` → `model->MOS6gamma` (body effect parameter)
- `φ` → `model->MOS6phi` (surface potential, default 0.6V)
- `η` → Derived from geometry: `η ∝ 1/L_eff`
- `KT1`, `KT1L`, `KT2` → `model->MOS6kt1`, `model->MOS6kt1l`, `model->MOS6kt2` (temperature coefficients)

### 2. Sakurai-Newton Alpha-Power Law with Smoothing

The drain current equations use alpha-power law formulation with smoothing for C¹ continuity:

**Linear Region (V_ds ≤ V_dsat):**
```
I_ds_lin = β_lin · (V_gsteff)^NC · V_ds · (1 + λ·V_ds)
where β_lin = (W_eff/L_eff) · KC
```

**Saturation Voltage:**
```
V_dsat = (KV/KC)^(1/(NV-NC)) · (V_gsteff)^((NC-1)/(NV-NC))
```

**Saturation Region (V_ds > V_dsat):**
```
I_ds_sat = β_sat · (V_gsteff)^NV · (1 + λ·V_ds)
where β_sat = (W_eff/L_eff) · KV
```

**Alpha-Power Law Smoothing Function:**
To ensure C¹ continuity at V_ds = V_dsat:
```
if V_ds < V_dsat:
    I_ds = I_ds_sat · [1 - (1 - (V_ds/V_dsat)^α)^(1/α)]
else:
    I_ds = I_ds_sat
where α = MOS6alpha (typically α = 2)
```

**SPICE Implementation Mapping:**
- `KV`, `NV` → `model->MOS6kv`, `model->MOS6nv` (saturation region parameters)
- `KC`, `NC` → `model->MOS6kc`, `model->MOS6nc` (linear region parameters)
- `α` → `model->MOS6alpha` (smoothing factor)
- `λ` → `model->MOS6lambda` (channel-length modulation)

### 3. Charge Conservation and Capacitance Models

The transient analysis implements charge-conserving integration using the Meyer capacitance model:

**Gate Charge Partitioning:**
```
Q_gs = C_gso·W_eff + C_ox·W_eff·L_eff·f_gs(V_gs, V_ds, V_bs)
Q_gd = C_gdo·W_eff + C_ox·W_eff·L_eff·f_gd(V_gs, V_ds, V_bs)
Q_gb = C_gbos·L_eff + C_ox·W_eff·L_eff·f_gb(V_gs, V_bs)
```

**Junction Capacitances:**
```
C_bd = CBD·A_d + CJSW·P_d
C_bs = CBS·A_s + CJSW·P_s

C_bd(V_bd) = C_bd0/(1 - V_bd/PB)^MJ    for V_bd < FC·PB
           = C_bd0·(1 - FC)^(-MJ)·[1 - FC·(1+MJ) + MJ·V_bd/PB] for V_bd ≥ FC·PB
```

**SPICE Implementation Mapping:**
- `C_gso`, `C_gdo`, `C_gbos` → `model->MOS6cgso`, `model->MOS6cgdo`, `model->MOS6cgbos` (overlap capacitances)
- `CBD`, `CBS` → `model->MOS6cbd`, `model->MOS6cbs` (zero-bias junction capacitances)
- `CJSW` → `model->MOS6cjsw` (sidewall capacitance per perimeter)
- Charges stored in state vector indices: `inst->MOS6qgs`, `inst->MOS6qgd`, `inst->MOS6qgb`, `inst->MOS6qbd`, `inst->MOS6qbs`

### 4. Local Truncation Error (LTE) Calculation

The LTE estimation uses charge-based error calculation for adaptive time step control:

**Charge Change Calculation:**
```
ΔQ = h·(Q̈ + O(h²))
where h = Δt (time step)
```

**Numerical Implementation:**
```
dq_gs = Δt·(q_gs_new - q_gs_old)/(Δt + Δt_old)
dq_gd = Δt·(q_gd_new - q_gd_old)/(Δt + Δt_old)
dq_gb = Δt·(q_gb_new - q_gb_old)/(Δt + Δt_old)
dq_bd = Δt·(q_bd_new - q_bd_old)/(Δt + Δt_old)
dq_bs = Δt·(q_bs_new - q_bs_old)/(Δt + Δt_old)
```

**Total Capacitive Current Error:**
```
ε_charge = (dq_gs + dq_gd + dq_gb + dq_bd + dq_bs)/Δt
```

**Tolerance Calculation:**
```
TOL = trtol·max(|I_ds|, Q_total/Δt) + chgtol·Q_total
where:
    trtol = CKTtrtol (transient relative tolerance)
    chgtol = CKTchgtol (charge absolute tolerance)
    Q_total = |q_gs| + |q_gd| + |q_gb| + |q_bd| + |q_bs|
```

**SPICE Implementation Mapping:**
- Implemented in `MOS6trunc()` function in `mos6trun.c`
- Uses state vectors `CKTstate0` (current) and `CKTstate1` (previous)
- Adjusts `*timeStep` when `ε_charge > TOL`

### 5. Newton-Raphson Convergence Criteria

The convergence testing implements SPICE's mixed absolute-relative tolerance checking:

**Voltage Convergence Test:**
For each terminal voltage V (V_gs, V_ds, V_bs):
```
|V_new - V_old| ≤ reltol·max(|V_new|, |V_old|) + abstol
```

**Current Convergence Test:**
For drain current I_ds:
```
|I_ds_new - I_ds_old| ≤ reltol·max(|I_ds_new|, |I_ds_old|) + abstol
```

**SPICE Implementation Parameters:**
- `reltol = CKTreltol = 0.001` (default relative tolerance)
- `abstol = CKTabstol = 1e-12` (default current absolute tolerance)
- `vntol = CKTvoltTol = 1e-6` (default voltage absolute tolerance)

### 6. Voltage Limiting Algorithm (DEVfetlim)

The `DEVfetlim()` function prevents excessive voltage changes between Newton iterations:

**Mathematical Implementation:**
```
if v_old ≥ v_to:
    vtsthi = |2·(v_old - v_to)| + 2.0
    vtstlo = vtsthi/2.0 + v_to
    
    if v_new > vtsthi: return vtsthi
    if v_new < vtstlo: return vtstlo
else:
    if v_new > v_to + 0.5: return v_to + 0.5
    if v_new < v_old - 0.5: return v_old - 0.5

return v_new
```

**SPICE Application:**
Applied to V_gs, V_ds, and V_bs in `MOS6load()`:
```c
vgs = DEVfetlim(vgs, inst->MOS6vgs_old, model->MOS6vto);
vds = DEVlimvds(vds, inst->MOS6vds_old);
vbs = DEVfetlim(vbs, inst->MOS6vbs_old, 0.0);
```

### 7. Temperature-Dependent Parameter Scaling

**Temperature Scaling Equations:**
```
KV(T) = KV(T_nom)·(T/T_nom)^(-UTE)
KC(T) = KC(T_nom)·(T/T_nom)^(-UTE)
μ(T) = μ(T_nom)·(T/T_nom)^(-1.5)
PB(T) = (T/T_nom)·PB(T_nom) - 3·(k/q)·T·ln(T/T_nom) + E_g(T) - (T/T_nom)·E_g(T_nom)
```

**Bandgap Energy Temperature Dependence:**
```
E_g(T) = 1.16 - 7.02×10⁻⁴·T²/(T + 1108.0)
```

**SPICE Implementation Mapping:**
- `UTE` → `model->MOS6ute` (mobility temperature exponent)
- Implemented in `MOS6temperature()` function in `mos6temp.c`
- Uses `CONSTCtoK = 273.15` for Celsius to Kelvin conversion
- `KoverQ = 8.617333262145×10⁻⁵` (Boltzmann constant / electron charge)

### 8. Source-Drain Swap Mechanics

When V_ds < 0, the device operates in reverse mode with terminal swapping:

**Voltage Transformations:**
```
V_ds' = -V_ds
V_gs' = V_gs - V_ds  (becomes V_gd)
V_bs' = V_bs + V_ds  (becomes V_bd)
```

**Matrix Stamp Adjustment:**
- Drain and source matrix entries are swapped
- Current direction is reversed
- Geometry parameters (AD/AS, PD/PS, NRD/NRS) are exchanged

**SPICE Implementation:**
```c
if(vds < 0) {
    /* Swap D and S nodes */
    int tempNode = inst->MOS6dNode;
    inst->MOS6dNode = inst->MOS6sNode;
    inst->MOS6sNode = tempNode;
    
    /* Swap internal nodes */
    tempNode = inst->MOS6dNodePrime;
    inst->MOS6dNodePrime = inst->MOS6sNodePrime;
    inst->MOS6sNodePrime = tempNode;
    
    /* Invert Vds after swap */
    vds = -vds;
}
```

### 9. Initial Condition Handling Priority

The initialization follows strict priority order:

**Priority Hierarchy:**
1. User `.IC` specification (VDS, VGS, VBS) → `inst->MOS6icVDS`, `inst->MOS6icVGS`, `inst->MOS6icVBS`
2. `OFF` flag → forces `V_gs = V_to - 0.1`, `I_ds = 0` (cutoff region)
3. Zero-bias assumption → all voltages = 0

**SPICE Implementation:**
```c
if(inst->MOS6icVGSGiven) {
    vgs = inst->MOS6icVGS;
    /* Force initial Vgs by adding voltage source */
    *(ckt->CKTrhs + inst->MOS6gNode) -= vgs;
    *(ckt->CKTrhs + inst->MOS6sNodePrime) += vgs;
}

if(inst->MOS6off) {
    /* Set Vgs < Vth to ensure cutoff */
    vgs = model->MOS6vto - 0.1;
    *(ckt->CKTrhs + inst->MOS6gNode) -= vgs;
    *(ckt->CKTrhs + inst->MOS6sNodePrime) += vgs;
}
```

### 10. Matrix Stamping for 6-Node Representation

The MOS6 model uses a 6×6 conductance matrix for nodes: D, G, S, B, D' (drain prime), S' (source prime):

**Node Index Mapping:**
```
0: D (external drain)
1: G (gate)
2: S (external source)
3: B (bulk)
4: D' (internal drain after RD)
5: S' (internal source after RS)
```

**Intrinsic MOSFET Stamp (nodes 4,5,1,3 only):**
```
G[4][4] = +g_ds          (drainPrime-drainPrime)
G[4][5] = -g_ds - g_m - g_mb  (drainPrime-sourcePrime)
G[4][1] = +g_m           (drainPrime-gate)
G[4][3] = +g_mb          (drainPrime-bulk)

G[5][4] = -g_ds          (sourcePrime-drainPrime)
G[5][5] = +g_ds + g_m + g_mb  (sourcePrime-sourcePrime)
G[5][1] = -g_m           (sourcePrime-gate)
G[5][3] = -g_mb          (sourcePrime-bulk)
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

**SPICE Implementation:**
Each matrix entry has a corresponding pointer in `sMOS6instance` structure, allocated via `SMPmakeElt()` in `MOS6setup()`.

## Convergence Analysis

### 1. Local Truncation Error (LTE) Control Algorithm

The LTE control mechanism ensures transient analysis accuracy while maintaining simulation efficiency:

**Error Estimation Methodology:**
The LTE calculation uses charge-based error estimation with weighted time step averaging:
```
dq = Δt·(q_new - q_old)/(Δt + Δt_old)
ε_charge = |dq_gs + dq_gd + dq_gb + dq_bd + dq_bs|/Δt
```

**Time Step Adjustment Logic:**
```
if (ε_charge > TOL) {
    reduction = 0.9·TOL/(ε_charge + 1e-12)
    Δt_new = MIN(Δt_current, Δt_current·reduction)
    Δt_new = MAX(Δt_new, Δt_min)
}
```

**SPICE Parameters:**
- `CKTtrtol = 7.0` (default transient relative tolerance)
- `CKTchgtol = 1e-14` (default charge absolute tolerance)
- `CKTminDelta = 1e-18` (minimum time step)
- `TOL = trtol·max(|I_ds|, Q_total/Δt) + chgtol·Q_total`

**Convergence Impact:** Proper LTE control prevents error accumulation while avoiding unnecessarily small time steps, balancing accuracy and simulation speed.

### 2. Newton-Raphson Iteration Convergence Testing

The convergence testing implements comprehensive multi-variable checking:

**Voltage Convergence Criteria:**
For each of the three terminal voltage pairs (V_gs, V_ds, V_bs):
```
|ΔV| ≤ reltol·max(|V_new|, |V_old|) + vntol
```
Where `vntol = 1e-6 V` (default voltage absolute tolerance).

**Current Convergence Criteria:**
For drain current I_ds:
```
|ΔI_ds| ≤ reltol·max(|I_ds_new|, |I_ds_old|) + abstol
```
Where `abstol = 1e-12 A` (default current absolute tolerance).

**Failure Detection:** Any violation indicates non-convergence, requiring another Newton iteration or fallback strategy.

**SPICE Implementation:** The `MOS6convTest()` function computes `delVgs`, `delVds`, `delVbs`, and `delIds`, comparing against combined tolerances.

### 3. Voltage Limiting for Newton-Raphson Stability

The `DEVfetlim()` algorithm prevents oscillation and divergence:

**Critical Voltage Determination:**
- For V_gs: `v_crit = V_to` (threshold voltage)
- For V_ds: `v_crit = 0` (no specific limiting, uses `DEVlimvds`)
- For V_bs: `v_crit = 0` (no limiting for bulk-source)

**Limiting Algorithm Logic:**
1. **Above threshold region** (`v_old ≥ v_to`):
   - Upper limit: `vtsthi = |2·(v_old - v_to)| + 2.0`
   - Lower limit: `vtstlo = vtsthi/2.0 + v_to`
   - Clamp `v_new` to `[vtstlo, vtsthi]`

2. **Below threshold region** (`v_old < v_to`):
   - Upper limit: `v_to + 0.5`
   - Lower limit: `v_old - 0.5`
   - Clamp `v_new` to `[v_old - 0.5, v_to + 0.5]`

**Convergence Benefit:** Prevents the Newton-Raphson solver from oscillating between strong inversion and cutoff regions, which have dramatically different derivatives.

### 4. Alpha-Power Law Smoothing for Derivative Continuity

The α-parameter smoothing ensures C¹ continuity at region boundaries:

**Smoothing Function:**
```
if V_ds < V_dsat:
    I_ds = I_ds_sat · [1 - (1 - (V_ds/V_dsat)^α)^(1/α)]
```

**Derivative Continuity:**
At `V_ds = V_dsat`:
```
I_ds_linear(V_dsat) = I_ds_sat(V_dsat)
∂I_ds/∂V_ds|_linear = ∂I_ds/∂V_ds|_sat
```

**SPICE Implementation:** `α = model->MOS6alpha` (default 2.0) controls smoothing strength.

**Convergence Impact:** Ensures continuous first derivatives across linear/saturation boundary, essential for Newton-Raphson convergence.

### 5. Source-Drain Swap Convergence Symmetry

The automatic source-drain swapping ensures consistent convergence:

**Swap Trigger Conditions:**
1. `V_ds < 0` for any device
2. PMOS devices (`model->MOS6type < 0`) with inherent polarity inversion

**Mathematical Transformation:**
```
/* Voltage inversion for PMOS */
vgs = -vgs;
vds = -vds;
vbs = -vbs;

/* Current inversion */
I_ds = -I_ds;
g_m = -g_m;
g_ds = -g_ds;
g_mb = -g_mb;
```

**Convergence Benefit:** Maintains identical convergence properties for forward and inverse modes, and for NMOS/PMOS devices, reducing special-case handling in the solver.

### 6. Temperature Consistency Enforcement

Temperature-dependent parameters must be consistent for convergence:

**Temperature Scaling Application:**
```c
if(inst->MOS6temp != ckt->CKTtemp) {
    MOS6temperature(model, inst, ckt);
}
```

**Mathematical Consistency:**
All temperature scaling uses the same reference:
```
ratio = T/T_nom
where T = inst->MOS6temp + CONSTCtoK
      T_nom = model->MOS6tnom + CONSTCtoK
```

**Convergence Requirement:** All temperature-dependent parameters updated simultaneously to prevent inconsistencies between `vth`, `β_eff`, and other parameters.

### 7. Initial Condition Priority and OFF Flag Handling

The initialization sequence ensures a physically reasonable starting point:

**Priority Hierarchy:**
1. **Explicit IC vectors**: User-specified `.IC VDS=... VGS=... VBS=...`
2. **OFF flag**: Forces device to cutoff (`V_gs = V_to - 0.1`, `I_ds = 0`)
3. **Zero-bias default**: All terminal voltages = 0

**SPICE Implementation:**
```c
if(inst->MOS6icVGSGiven) {
    /* User IC takes highest priority */
    vgs = inst->MOS6icVGS;
} else if(inst->MOS6off) {
    /* OFF flag forces cutoff */
    vgs = model->MOS6vto - 0.1;
} else {
    /* Default zero-bias start */
    vgs = 0;
}
```

**Convergence Impact:** The OFF flag provides a guaranteed convergence path for difficult circuits by starting from the well-behaved cutoff region.

### 8. Matrix Conditioning for Numerical Stability

To prevent singular matrices during Newton-Raphson:

**Minimum Conductance Addition:**
```
G_min = GMIN = 1e-12 Ʊ (default)
```
Added to all diagonal entries: `G[i,i] += GMIN`

**Parasitic Resistance Lower Bounds:**
```
R_d, R_s ≥ RMIN = 1e-6 Ω
```
Prevents infinite conductance in matrix.

**Capacitance Floor:**
```
C_gs, C_gd, C_gb ≥ CMIN = 1e-18 F
```
Ensures finite time constant `τ = RC` for transient analysis.

### 9. Fallback Strategies for Difficult Convergence

When standard Newton-Raphson fails:

**GMIN Stepping:**
Increase `GMIN` from `1e-12` to `1e-3` over 5 steps, then reduce back after convergence.

**Source Stepping:**
```
V_source(k) = (k/N)·V_source_full for k = 0..N
```
Where `N = 10` steps gradually increase source voltages.

**Damping:**
Apply damping factor `α = 0.5` to Newton update:
```
V_new = V_old + α·ΔV
```

### 10. Convergence Monitoring and Diagnostics

SPICE tracks convergence metrics:
- `ckt->CKTnoncon`: Non-convergence counter
- `ckt->CKTmode`: Analysis mode (DC_OP, TRAN, etc.)
- `ckt->CKTtime`: Current simulation time
- Iteration count per Newton step

**Device-Specific Storage:**
- `inst->MOS6vgs_old`, `inst->MOS6vds_old`, `inst->MOS6vbs_old`: Previous iteration voltages
- `inst->MOS6ids_old`: Previous drain current for LTE calculation

### 11. Numerical Stability Considerations

**Effective Dimension Clamping:**
```c
if(inst->MOS6leff <= 0.0) {
    inst->MOS6leff = 1e-12;  /* Prevent division by zero */
}
if(inst->MOS6weff <= 0.0) {
    inst->MOS6weff = 1e-12;
}
```

**Power Function Protection:**
```c
if(vgst > 0) {
    ids = beta * kv * pow(vgst, nv) * (1.0 + lambda * vds);
} else {
    ids = 0.0;  /* Avoid pow() with negative base */
}
```

**Time Step Bounding:**
```
Δt_min ≤ Δt ≤ Δt_max
where Δt_min = 1e-18 s, Δt_max = 0.1·T_stop
```

### 12. Algorithmic Convergence Summary

The MOS6 model ensures SPICE convergence through:

1. **Voltage Limiting**: `DEVfetlim()` prevents excessive changes between iterations
2. **Alpha-Power Law Smoothing**: C¹ continuity at region boundaries
3. **Charge Conservation**: Meyer capacitance model with state vector management
4. **LTE Control**: Adaptive time stepping based on charge error
5. **Temperature Consistency**: All parameters scaled simultaneously
6. **Source-Drain Symmetry**: Identical convergence for forward/reverse operation
7. **Matrix Conditioning**: Minimum conductances prevent singularities
8. **Initial Condition Support**: User ICs and OFF flag provide convergence paths
9. **Fallback Strategies**: GMIN stepping, source stepping, damping
10. **Numerical Stability**: Dimension clamping, power function protection

These mechanisms make the MOS6 model robust for digital circuit simulation while maintaining the accuracy of the Sakurai-Newton alpha-power law formulation with proper transient control and convergence checking.

## C Implementation

### Core Data Structures (mos6defs.h)

The transient and convergence control extensions to the MOS6 data structures:

```c
typedef struct sMOS6instance {
    /* ... existing DC model fields ... */
    
    /* Transient analysis state variables */
    int MOS6qgs;        /* State index for gate-source charge */
    int MOS6qgd;        /* State index for gate-drain charge */
    int MOS6qgb;        /* State index for gate-bulk charge */
    int MOS6qbd;        /* State index for bulk-drain charge */
    int MOS6qbs;        /* State index for bulk-source charge */
    
    /* Previous iteration storage for convergence checking */
    double MOS6vgs_old;     /* Previous gate-source voltage */
    double MOS6vds_old;     /* Previous drain-source voltage */
    double MOS6vbs_old;     /* Previous bulk-source voltage */
    double MOS6ids_old;     /* Previous drain current */
    
    /* Initial condition specifications */
    double MOS6icVDS;       /* Initial Vds from .IC card */
    double MOS6icVGS;       /* Initial Vgs from .IC card */
    double MOS6icVBS;       /* Initial Vbs from .IC card */
    unsigned MOS6icVDSGiven : 1;  /* VDS initial condition given */
    unsigned MOS6icVGSGiven : 1;  /* VGS initial condition given */
    unsigned MOS6icVBSGiven : 1;  /* VBS initial condition given */
    unsigned MOS6off : 1;         /* OFF flag for initial cutoff */
    
    /* Convergence state flags */
    unsigned MOS6convIter : 4;    /* Iteration counter for this device */
    unsigned MOS6convLast : 1;    /* Last iteration converged */
    
    /* Sparse matrix pointers for transient stamps */
    double *MOS6qgs_qgsPtr;    /* ∂qgs/∂vgs */
    double *MOS6qgs_qgdPtr;    /* ∂qgs/∂vgd */
    double *MOS6qgs_qgbPtr;    /* ∂qgs/∂vgb */
    double *MOS6qgd_qgsPtr;    /* ∂qgd/∂vgs */
    double *MOS6qgd_qgdPtr;    /* ∂qgd/∂vgd */
    double *MOS6qgd_qgbPtr;    /* ∂qgd/∂vgb */
    double *MOS6qgb_qgsPtr;    /* ∂qgb/∂vgs */
    double *MOS6qgb_qgdPtr;    /* ∂qgb/∂vgd */
    double *MOS6qgb_qgbPtr;    /* ∂qgb/∂vgb */
    
    /* Additional pointers for junction capacitances */
    double *MOS6qbd_qbdPtr;    /* ∂qbd/∂vbd */
    double *MOS6qbs_qbsPtr;    /* ∂qbs/∂vbs */
    
} MOS6instance;
```

### Local Truncation Error Control (mos6trun.c)

The `MOS6trunc()` function implements LTE-based time step control:

```c
int MOS6trunc(MOS6instance *inst, CKTcircuit *ckt, double *timeStep)
{
    double qgs0, qgd0, qgb0, qbd0, qbs0;  /* Current charges */
    double qgs1, qgd1, qgb1, qbd1, qbs1;  /* Previous charges */
    double dqgs, dqgd, dqgb, dqbd, dqbs;  /* Charge changes */
    double dq_total, error, tol;
    double delta, deltaOld;
    
    /* Get current and previous time steps */
    delta = ckt->CKTdelta;
    deltaOld = ckt->CKTdeltaOld[0];
    
    if(deltaOld <= 0.0) {
        /* First step, no error estimate available */
        return(OK);
    }
    
    /* Retrieve charges from state vectors */
    qgs0 = *(ckt->CKTstate0 + inst->MOS6qgs);
    qgd0 = *(ckt->CKTstate0 + inst->MOS6qgd);
    qgb0 = *(ckt->CKTstate0 + inst->MOS6qgb);
    qbd0 = *(ckt->CKTstate0 + inst->MOS6qbd);
    qbs0 = *(ckt->CKTstate0 + inst->MOS6qbs);
    
    qgs1 = *(ckt->CKTstate1 + inst->MOS6qgs);
    qgd1 = *(ckt->CKTstate1 + inst->MOS6qgd);
    qgb1 = *(ckt->CKTstate1 + inst->MOS6qgb);
    qbd1 = *(ckt->CKTstate1 + inst->MOS6qbd);
    qbs1 = *(ckt->CKTstate1 + inst->MOS6qbs);
    
    /* Calculate weighted charge changes */
    dqgs = delta * (qgs0 - qgs1) / (delta + deltaOld);
    dqgd = delta * (qgd0 - qgd1) / (delta + deltaOld);
    dqgb = delta * (qgb0 - qgb1) / (delta + deltaOld);
    dqbd = delta * (qbd0 - qbd1) / (delta + deltaOld);
    dqbs = delta * (qbs0 - qbs1) / (delta + deltaOld);
    
    /* Total capacitive current error */
    dq_total = dqgs + dqgd + dqgb + dqbd + dqbs;
    error = fabs(dq_total) / delta;
    
    /* Calculate tolerance */
    double ids = inst->MOS6ids;
    double q_total = fabs(qgs0) + fabs(qgd0) + fabs(qgb0) + 
                     fabs(qbd0) + fabs(qbs0);
    
    tol = ckt->CKTtrtol * MAX(fabs(ids), q_total/delta) + 
          ckt->CKTchgtol * q_total;
    
    /* Check if error exceeds tolerance */
    if(error > tol) {
        /* Reduce time step */
        double reduction = 0.9 * tol / (error + 1e-30);
        double newDelta = delta * reduction;
        
        /* Apply bounds */
        newDelta = MAX(newDelta, ckt->CKTminDelta);
        newDelta = MIN(newDelta, delta);
        
        if(newDelta < delta) {
            *timeStep = newDelta;
            return(E_LOCALTRUNC);
        }
    }
    
    return(OK);
}
```

### Convergence Testing (mos6conv.c)

The `MOS6convTest()` function implements SPICE convergence criteria:

```c
int MOS6convTest(MOS6instance *inst, CKTcircuit *ckt)
{
    double vgs, vds, vbs, ids;
    double delVgs, delVds, delVbs, delIds;
    double reltol, abstol, vntol;
    double vgs_old, vds_old, vbs_old, ids_old;
    
    /* Get current operating point */
    vgs = inst->MOS6vgs;
    vds = inst->MOS6vds;
    vbs = inst->MOS6vbs;
    ids = inst->MOS6ids;
    
    /* Get previous iteration values */
    vgs_old = inst->MOS6vgs_old;
    vds_old = inst->MOS6vds_old;
    vbs_old = inst->MOS6vbs_old;
    ids_old = inst->MOS6ids_old;
    
    /* Calculate changes */
    delVgs = vgs - vgs_old;
    delVds = vds - vds_old;
    delVbs = vbs - vbs_old;
    delIds = ids - ids_old;
    
    /* Get SPICE tolerances */
    reltol = ckt->CKTreltol;
    abstol = ckt->CKTabstol;
    vntol = ckt->CKTvoltTol;
    
    /* Voltage convergence tests */
    double vgs_test = fabs(delVgs) - 
                     reltol * MAX(fabs(vgs), fabs(vgs_old)) - vntol;
    double vds_test = fabs(delVds) - 
                     reltol * MAX(fabs(vds), fabs(vds_old)) - vntol;
    double vbs_test = fabs(delVbs) - 
                     reltol * MAX(fabs(vbs), fabs(vbs_old)) - vntol;
    
    /* Current convergence test */
    double ids_test = fabs(delIds) - 
                     reltol * MAX(fabs(ids), fabs(ids_old)) - abstol;
    
    /* Check all convergence criteria */
    if(vgs_test > 0.0 || vds_test > 0.0 || 
       vbs_test > 0.0 || ids_test > 0.0) {
        
        /* Update iteration counter */
        inst->MOS6convIter++;
        
        /* Check for excessive iterations */
        if(inst->MOS6convIter > 8) {
            ckt->CKTnoncon++;
            inst->MOS6convIter = 0;
            return(E_NOT_CONVERGED);
        }
        
        /* Not converged, continue iterating */
        inst->MOS6convLast = 0;
        return(E_NOT_CONVERGED);
    }
    
    /* All tests passed - converged */
    inst->MOS6convIter = 0;
    inst->MOS6convLast = 1;
    
    /* Store current values as old for next iteration */
    inst->MOS6vgs_old = vgs;
    inst->MOS6vds