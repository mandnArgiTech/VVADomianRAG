# MOS3: Transient Control and Convergence Checking

_Generated 2026-04-12 06:29 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3trun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3conv.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3ic.c`

# MOS3: Transient Control and Convergence Checking

## Technical Introduction

This chapter details the implementation of transient analysis control and convergence checking for the MOS3 (Level 3) model in Ngspice. Three core C files implement these critical simulation stability mechanisms:

- **`mos3trun.c`** - Implements Local Truncation Error (LTE) estimation and adaptive time step control for transient analysis, ensuring numerical accuracy while maintaining simulation efficiency through polynomial extrapolation and charge-based error metrics.

- **`mos3conv.c`** - Performs comprehensive convergence testing for Newton-Raphson iterations, implementing SPICE's mixed absolute-relative tolerance checking for voltages, currents, and charges across all device terminals and operating regions.

- **`mos3ic.c`** - Handles initial condition specification and priority-based startup logic, managing user `.IC` directives, `OFF` flags, and zero-bias fallback strategies to ensure robust convergence from physically reasonable starting points.

These files form the numerical stability backbone of the MOS3 model implementation, ensuring reliable DC operating point solution, accurate transient response, and robust convergence across all bias conditions, temperatures, and time scales required for production circuit simulation.

## Mathematical Formulation

The MOS3 Level 3 model's transient analysis and convergence checking in Ngspice implement mathematical formulations for time-domain simulation stability and Newton-Raphson iteration control. These formulations directly map to SPICE's transient analysis requirements through charge conservation principles, local truncation error estimation, and mixed tolerance convergence criteria.

### 1. Charge Conservation and Capacitive Current Formulation

The transient analysis implements charge-conserving integration through the Meyer capacitance model, ensuring Kirchhoff's Current Law (KCL) is satisfied at all time points:

**Terminal Current Relationships:**
```
I_g + I_d + I_s + I_b = 0
```

**Capacitive Current Components:**
```
I_g = d(Q_gs + Q_gd + Q_gb)/dt
I_d = I_ds - dQ_gd/dt + I_bd
I_s = -I_ds - dQ_gs/dt + I_bs
I_b = -dQ_gb/dt - I_bd - I_bs
```

**Meyer Capacitance Charge Definitions:**
```
Q_gs = C_gs(V_gs, V_gd, V_gb) × V_gs
Q_gd = C_gd(V_gs, V_gd, V_gb) × V_gd
Q_gb = C_gb(V_gs, V_gd, V_gb) × V_gb
```

**SPICE Integration:** These charge variables are stored in the state vector at indices `MOS3states[3-6]` and integrated using the trapezoidal rule to compute capacitive currents for transient analysis.

### 2. Trapezoidal Integration Rule for Charge Derivatives

The numerical integration of charge derivatives uses the trapezoidal rule for stability and accuracy:

**Discrete Time Integration:**
```
I_cap(t) = dQ/dt ≈ (Q_n - Q_{n-1})/Δt + 0.5·(dQ/dt_{n-1} + dQ/dt_n)
```

Where:
- `Q_n = Q(t)` = charge at current time point
- `Q_{n-1} = Q(t-Δt)` = charge at previous time point
- `Δt` = time step from SPICE's adaptive time step control
- `dQ/dt_n = C_n·dV/dt_n` = capacitive current derivative at current time
- `dQ/dt_{n-1} = C_{n-1}·dV/dt_{n-1}` = capacitive current derivative at previous time

**SPICE Implementation:** This formulation is implemented in the transient analysis loop, with charges stored in `inst->MOS3qgs`, `inst->MOS3qgd`, `inst->MOS3qgb`, `inst->MOS3qbd`, `inst->MOS3qbs` and their derivatives computed from capacitance-voltage relationships.

### 3. Local Truncation Error (LTE) Estimation

The LTE calculation uses polynomial extrapolation to estimate integration error for adaptive time step control:

**Charge Prediction Polynomial:**
```
Q_pred = 2.5·Q_n - 2.0·Q_{n-1} + 0.5·Q_{n-2}
```

Where:
- `Q_n` = charge at time `t_n`
- `Q_{n-1}` = charge at time `t_{n-1} = t_n - Δt`
- `Q_{n-2}` = charge at time `t_{n-2} = t_n - 2Δt`

**LTE Calculation (Milne's Method):**
```
LTE = |Q_pred - Q_sim| / (|Q| + 1)
```

**Normalized Error for Time Step Control:**
```
Error_ratio = LTE / (reltol·|Q| + abstol)
```

Where:
- `reltol = CKTreltol` = relative tolerance (default 0.001)
- `abstol = CKTchgtol` = absolute charge tolerance (default 1e-14)

**SPICE Integration:** The LTE calculation in `MOS3trunc()` uses this formulation to compute `deltaCharge` and adjust `timeStep` based on the error relative to `chargeTol = chgtol + reltol * qref`.

### 4. Adaptive Time Step Control Algorithm

The time step adjustment follows a square-root relationship to error:

**Time Step Reduction Factor:**
```
factor = sqrt(chargeTol / deltaCharge)
newStep = timeStep * factor * safety_factor
```

Where `safety_factor = 0.8` prevents overly aggressive time step increases.

**Time Step Limiting Rules:**
1. Maximum increase: `Δt_{new} ≤ 2·Δt_{old}`
2. Minimum decrease: `Δt_{new} ≥ 0.1·Δt_{old}`
3. Absolute minimum: `Δt_{min} = 1e-18` seconds

**SPICE Implementation:** The `MOS3trunc()` function computes `newStep` and updates `*timeStep` when `deltaCharge > chargeTol`, ensuring local error remains within specified tolerances.

### 5. Newton-Raphson Convergence Criteria

The convergence testing implements SPICE's mixed absolute-relative tolerance checking for voltages, currents, and charges:

**Voltage Convergence Test:**
For each terminal voltage `V` (V_gs, V_ds, V_bs):
```
|V_new - V_old| ≤ reltol·max(|V_new|, |V_old|) + vntol
```

Where:
- `reltol = CKTreltol = 0.001` (default)
- `vntol = CKTvoltTol = 1e-6` (default voltage absolute tolerance)

**Current Convergence Test:**
For each terminal current `I` (I_d, I_bs, I_bd):
```
|I_new - I_old| ≤ reltol·max(|I_new|, |I_old|) + abstol
```

Where `abstol = CKTabstol = 1e-12` (default current absolute tolerance).

**Charge Convergence Test (Transient Analysis):**
For each stored charge `Q` (Q_gs, Q_gd, Q_gb, Q_bd, Q_bs):
```
|Q_new - Q_old| ≤ reltol·max(|Q_new|, |Q_old|) + chgtol
```

Where `chgtol = CKTchgtol = 1e-14` (default charge absolute tolerance).

**SPICE Implementation:** The `MOS3convTest()` function computes `delVgs`, `delVds`, `delVbs`, `delCd`, `delCbs`, `delCbd`, `delQgs`, `delQgd` and compares against the combined tolerances, setting `ckt->CKTnoncon++` when any test fails.

### 6. Newton-Raphson Voltage Limiting (DEVfetlim Algorithm)

The `DEVfetlim()` function prevents excessive voltage changes between Newton iterations:

**Mathematical Formulation:**
Given previous voltage `v_old` and new NR prediction `v_new`:
```
Δv = v_new - v_old
v_crit = { V_dsat for V_ds, V_on for V_gs, 0 for V_bs }
```

**Limiting Rules:**
1. If `v_old > v_crit` and `v_new > v_old`: Allow increase but limit to `v_temp = v_old + 2·(v_crit - v_old)`
2. If `v_old > v_crit` and `v_new < v_crit`: Clamp to `v_crit`
3. If `v_old < -v_crit` and `v_new < v_old`: Allow decrease but limit to `v_temp = v_old - 2·(v_crit + v_old)`
4. If `v_old < -v_crit` and `v_new > -v_crit`: Clamp to `-v_crit`
5. If `-v_crit ≤ v_old ≤ v_crit`: Clamp `v_new` to `[ -v_crit, v_crit ]`

**SPICE Application:** Applied in `MOS3load()` to `V_gs`, `V_ds`, and `V_bs` using `inst->MOS3vdsat` and `inst->MOS3von` as critical voltages before current calculation.

### 7. Initial Condition Handling Priority

The initial condition algorithm follows a strict priority order for convergence:

**Priority Order:**
1. User `.IC` specification (VDS, VGS, VBS) → `inst->MOS3icVDS`, `inst->MOS3icVGS`, `inst->MOS3icVBS`
2. `OFF` flag → forces `V_gs = 0`, `I_ds = 0` (cutoff region)
3. Zero-bias assumption → all voltages = 0
4. Previous solution (for continuation analyses)

**Mathematical Implementation:**
```
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

**SPICE Convergence Impact:** Proper initial conditions reduce Newton iterations by 50-70% and prevent convergence on non-physical operating points.

### 8. Source-Drain Swap Logic for Symmetric Convergence

For PMOS devices and inverse mode operation, internal transformation ensures consistent convergence:

**Mathematical Transformation:**
```
V_gs_pmos = -V_gs_nmos
V_ds_pmos = -V_ds_nmos
V_bs_pmos = -V_bs_nmos
I_ds_pmos = -I_ds_nmos
```

**Swap Conditions:**
1. PMOS devices (`MOS3type < 0`): Always invert polarities
2. NMOS in inverse mode (`V_ds < 0`): Swap source and drain internally

**Implementation Logic:**
```c
if(vds < 0.0) {
    /* Swap internal nodes */
    int tempNode = inst->MOS3dNodePrime;
    inst->MOS3dNodePrime = inst->MOS3sNodePrime;
    inst->MOS3sNodePrime = tempNode;
    
    /* Swap voltages with sign change */
    vds = -vds;
    vgs = -vgs;
    vbs = -vbs;
    
    /* Invert mode for PMOS */
    inst->MOS3mode = -inst->MOS3mode;
}
```

**Convergence Benefit:** Maintains identical numerical properties for all operating conditions, ensuring symmetric convergence behavior.

### 9. State Vector Management for Transient Analysis

The state vector stores historical values for numerical integration:

**State Allocation Pattern:**
```
states[0] → vgs_old (gate-source voltage at previous time)
states[1] → vds_old (drain-source voltage at previous time)
states[2] → vbs_old (bulk-source voltage at previous time)
states[3] → qgs (gate-source charge)
states[4] → qgd (gate-drain charge)
states[5] → qgb (gate-bulk charge)
states[6] → qbd (bulk-drain charge)
```

**State Update Equations:**
```
vgs_old(t+Δt) = vgs(t)
qgs(t+Δt) = C_gs(V_gs, V_gd, V_gb) × V_gs
```

**SPICE Implementation:** The `MOS3states[7]` array provides pointers to these state variables, with `CKTrhsOld` storing previous time step values for LTE calculation.

### 10. Temperature-Dependent Parameter Scaling

Temperature adjustments ensure consistent device behavior across operating temperatures:

**Threshold Voltage Temperature Dependence:**
```
V_TO(T) = V_TO(T_nom) + TCV·(T - T_nom)
```

**Mobility Temperature Scaling:**
```
μ(T) = μ(T_nom)·(T/T_nom)^{-1.5}
```

**Junction Potential Temperature Scaling:**
```
PB(T) = PB(T_nom)·(T/T_nom) - 3·V_T·ln(T/T_nom) - E_g(T)·(T/T_nom) + E_g(T_nom)
```

**SPICE Integration:** Implemented in `MOS3temp()` and applied when `inst->MOS3temp != ckt->CKTtemp`, ensuring convergence consistency across temperature corners.

## Convergence Analysis

### 1. Local Truncation Error (LTE) Control Algorithm

The LTE control mechanism ensures transient analysis accuracy while maintaining simulation efficiency:

**Error Estimation Methodology:**
The LTE calculation uses third-order polynomial extrapolation to estimate the error in charge integration:
```
Q_pred = 2.5·Q_n - 2.0·Q_{n-1} + 0.5·Q_{n-2}
LTE = |Q_pred - Q_sim| / (|Q| + 1)
```

**Time Step Adjustment Logic:**
```
if (deltaCharge > chargeTol) {
    factor = sqrt(chargeTol / deltaCharge);
    newStep = timeStep * factor * 0.8;  /* 0.8 safety factor */
    if (newStep < timeStep) {
        timeStep = newStep;
    }
}
```

**SPICE Parameters:**
- `CKTreltol = 0.001` (relative tolerance)
- `CKTchgtol = 1e-14` (absolute charge tolerance)
- `chargeTol = chgtol + reltol * qref` (combined tolerance)

**Convergence Impact:** Proper LTE control prevents error accumulation while avoiding unnecessarily small time steps, balancing accuracy and simulation speed.

### 2. Newton-Raphson Iteration Convergence Testing

The convergence testing implements a comprehensive multi-variable check:

**Voltage Convergence Criteria:**
For each of the three terminal voltage pairs (V_gs, V_ds, V_bs):
```
|ΔV| ≤ reltol·max(|V_new|, |V_old|) + vntol
```
Where `vntol = 1e-6 V` (default voltage absolute tolerance).

**Current Convergence Criteria:**
For drain and junction currents (I_d, I_bs, I_bd):
```
|ΔI| ≤ reltol·max(|I_new|, |I_old|) + abstol
```
Where `abstol = 1e-12 A` (default current absolute tolerance).

**Charge Convergence Criteria (Transient Only):**
For Meyer capacitance charges (Q_gs, Q_gd, Q_gb):
```
|ΔQ| ≤ reltol·max(|Q_new|, |Q_old|) + chgtol
```
Where `chgtol = 1e-14 C` (default charge absolute tolerance).

**Failure Detection:** Any violation sets `ckt->CKTnoncon++`, triggering another Newton iteration or fallback strategy.

### 3. Voltage Limiting for Newton-Raphson Stability

The `DEVfetlim()` algorithm prevents oscillation and divergence:

**Critical Voltage Determination:**
- For V_gs: `v_crit = V_on` (turn-on voltage)
- For V_ds: `v_crit = V_dsat` (saturation voltage)
- For V_bs: `v_crit = 0` (no limiting for bulk-source)

**Limiting Algorithm Logic:**
1. **Above critical region** (`v_old > v_crit`):
   - Allow increase but limit to `v_old + 2·(v_crit - v_old)`
   - Never allow crossing below `v_crit`

2. **Below critical region** (`v_old < -v_crit`):
   - Allow decrease but limit to `v_old - 2·(v_crit + v_old)`
   - Never allow crossing above `-v_crit`

3. **Transition region** (`-v_crit ≤ v_old ≤ v_crit`):
   - Clamp to `[-v_crit, v_crit]`

**Convergence Benefit:** Prevents the Newton-Raphson solver from oscillating between strong inversion and cutoff regions, which have dramatically different derivatives.

### 4. Initial Condition Priority and OFF Flag Handling

The initialization sequence ensures a physically reasonable starting point:

**Priority Hierarchy:**
1. **Explicit IC vectors**: User-specified `.IC VDS=... VGS=... VBS=...`
2. **OFF flag**: Forces device to cutoff (`V_gs = 0`, `I_ds = 0`)
3. **Zero-bias default**: All terminal voltages = 0
4. **Previous solution**: For `.DC` sweeps or `.TRAN` continuation

**Mathematical Implementation:**
```c
if (inst->MOS3icVDSGiven) {
    /* User IC takes highest priority */
    vds = inst->MOS3icVDS;
    vgs = inst->MOS3icVGS;
    vbs = inst->MOS3icVBS;
} else if (inst->MOS3off) {
    /* OFF flag forces cutoff */
    vgs = 0; vds = 0; vbs = 0;
} else {
    /* Default zero-bias start */
    vgs = vds = vbs = 0;
}
```

**Convergence Impact:** The OFF flag provides a guaranteed convergence path for difficult circuits by starting from the well-behaved cutoff region.

### 5. Region Boundary Smoothing for Derivative Continuity

To ensure Newton-Raphson convergence, the model implements smoothing at critical boundaries:

**Cutoff/Linear Boundary (V_gs = V_th):**
Use linear extrapolation for small negative `V_gst`:
```
I_ds_smooth = β·V_gst²/(2·V_smooth) for V_gst > -V_smooth
```
Where `V_smooth ≈ 0.1 V` ensures continuous first derivative.

**Linear/Saturation Boundary (V_ds = V_dsat):**
Quadratic blending over range `[V_dsat - ΔV, V_dsat + ΔV]`:
```
I_ds_blend = w_lin·I_ds_lin + w_sat·I_ds_sat
```
Where weights vary smoothly with `V_ds` to prevent Jacobian discontinuities.

**SPICE Implementation:** These smoothing functions are applied during `MOS3load()` calculations to ensure `g_m`, `g_ds`, and `g_mb` are continuous across all operating regions.

### 6. Source-Drain Swap Convergence Symmetry

The automatic source-drain swapping ensures consistent convergence for all bias conditions:

**Swap Trigger Conditions:**
1. PMOS devices: Always swap (inherent polarity inversion)
2. NMOS with `V_ds < 0`: Swap for inverse mode operation

**Mathematical Transformation:**
```
/* Voltage inversion */
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

### 7. State Vector Management for Numerical Stability

The state vector system ensures charge conservation and numerical stability:

**State Allocation Pattern:**
```
inst->MOS3states[0] = &(inst->MOS3vgs);    /* V_gs at previous time */
inst->MOS3states[1] = &(inst->MOS3vds);    /* V_ds at previous time */
inst->MOS3states[2] = &(inst->MOS3vbs);    /* V_bs at previous time */
inst->MOS3states[3] = &(inst->MOS3qgs);    /* Q_gs charge */
inst->MOS3states[4] = &(inst->MOS3qgd);    /* Q_gd charge */
inst->MOS3states[5] = &(inst->MOS3qgb);    /* Q_gb charge */
inst->MOS3states[6] = &(inst->MOS3qbd);    /* Q_bd charge */
```

**State Update Protocol:**
1. Store current values to `CKTrhsOld` before time step
2. Compute new values using trapezoidal integration
3. Calculate LTE using `Q_pred` polynomial extrapolation
4. Update states if LTE within tolerance

**Convergence Impact:** Proper state management prevents charge non-conservation, which can cause artificial damping or instability in transient analysis.

### 8. Temperature Consistency Enforcement

Temperature-dependent parameters must be consistent for convergence:

**Temperature Scaling Application:**
```c
if(inst->MOS3temp != ckt->CKTtemp) {
    double T = inst->MOS3temp + CONSTCtoK;
    double TNOM = model->MOS3tnom + CONSTCtoK;
    double ratio = T / TNOM;
    
    /* Apply scaling laws */
    inst->MOS3vto_t = model->MOS3vto * (1.0 + model->MOS3tcv * (T - TNOM));
    inst->MOS3u0_t = model->MOS3u0 * pow(ratio, -1.5);
    /* ... other parameters ... */
}
```

**Convergence Requirement:** All temperature scaling must use the same temperature `T` and reference `T_nom` to prevent inconsistencies between parameter values.

### 9. Matrix Conditioning for Numerical Stability

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

### 10. Fallback Strategies for Difficult Convergence

When standard Newton-Raphson fails:

**Source Stepping:**
```
V_source(k) = (k/N)·V_source_full for k = 0..N
```
Where `N = 10` steps gradually increase source voltages.

**GMIN Stepping:**
Increase `GMIN` from `1e-12` to `1e-3` over 5 steps, then reduce back after convergence.

**Damping:**
Apply damping factor `α = 0.5` to Newton update:
```
V_new = V_old + α·ΔV
```

### 11. Convergence Monitoring and Diagnostics

SPICE tracks convergence metrics:
- `ckt->CKTnoncon`: Non-convergence counter
- `ckt->CKTmode`: Analysis mode (DC_OP, TRAN, etc.)
- `ckt->CKTtime`: Current simulation time
- Iteration count per Newton step

**Debug Output:** With `.OPTIONS METHOD=DEBUG`, prints voltage/current changes per iteration for divergence diagnosis.

### 12. Algorithmic Convergence Summary

The MOS3 model ensures SPICE convergence through:
1. **Continuous derivatives** across all operating regions
2. **Voltage limiting** via `DEVfetlim()` at critical boundaries
3. **Mixed tolerance checking** for voltages, currents, and charges
4. **Adaptive time stepping** based on LTE estimation
5. **Charge conservation** through state vector management
6. **Temperature consistency** in parameter scaling
7. **Matrix conditioning** with GMIN and minimum resistances
8. **Fallback strategies** (source stepping, GMIN stepping)
9. **Symmetric handling** of all operating modes
10. **Proper initialization** with priority-based IC handling

These mechanisms collectively ensure the Level 3 model converges robustly across all bias conditions, temperatures, and time scales while maintaining physical accuracy for circuit simulation.

## C Implementation

### 1. Data Structures for Transient and Convergence Control (`mos3defs.h`)

The `MOS3instance` structure is extended with fields for transient analysis and convergence checking:

```c
typedef struct sMOS3instance {
    /* ... existing DC model parameters ... */
    
    /* Transient analysis states */
    double MOS3vgs_old;           /* Previous V_gs for LTE calculation */
    double MOS3vds_old;           /* Previous V_ds for LTE calculation */
    double MOS3vbs_old;           /* Previous V_bs for LTE calculation */
    double MOS3qgs;               /* Gate-source charge */
    double MOS3qgd;               /* Gate-drain charge */
    double MOS3qgb;               /* Gate-bulk charge */
    double MOS3qbd;               /* Bulk-drain charge */
    double MOS3qbs;               /* Bulk-source charge */
    
    /* State vector pointers */
    double *MOS3states[7];        /* State variables for integration */
    
    /* Initial condition handling */
    double MOS3icVDS;             /* Initial V_DS from .IC */
    double MOS3icVGS;             /* Initial V_GS from .IC */
    double MOS3icVBS;             /* Initial V_BS from .IC */
    unsigned MOS3icVDSGiven :1;   /* IC VDS specified flag */
    unsigned MOS3icVGSGiven :1;   /* IC VGS specified flag */
    unsigned MOS3icVBSGiven :1;   /* IC VBS specified flag */
    unsigned MOS3off      :1;     /* OFF flag for startup */
    
    /* Convergence testing deltas */
    double MOS3delVgs;            /* ΔV_gs between iterations */
    double MOS3delVds;            /* ΔV_ds between iterations */
    double MOS3delVbs;            /* ΔV_bs between iterations */
    double MOS3delCd;             /* ΔI_d between iterations */
    double MOS3delCbs;            /* ΔI_bs between iterations */
    double MOS3delCbd;            /* ΔI_bd between iterations */
    double MOS3delQgs;            /* ΔQ_gs between iterations */
    double MOS3delQgd;            /* ΔQ_gd between iterations */
    
    /* LTE calculation variables */
    double MOS3qgs_pred;          /* Predicted Q_gs for LTE */
    double MOS3qgd_pred;          /* Predicted Q_gd for LTE */
    double MOS3qgb_pred;          /* Predicted Q_gb for LTE */
    double MOS3deltaCharge;       /* LTE charge error */
    
} MOS3instance;
```

### 2. Local Truncation Error Control (`mos3trun.c`)

The `MOS3trunc()` function implements LTE estimation and time step control:

```c
int MOS3trunc(MOS3instance *here, MOS3model *model, 
              CKTcircuit *ckt, double *timeStep)
{
    double chargeTol, deltaCharge, factor, newStep;
    
    /* Retrieve previous charge values from state vector */
    double qgs_old = *(here->MOS3states[3]);
    double qgd_old = *(here->MOS3states[4]);
    double qgb_old = *(here->MOS3states[5]);
    
    /* Get charges from two previous time points for polynomial extrapolation */
    double *rhsOld = ckt->CKTrhsOld;
    int qgs_index = ckt->CKTstate0 + here->MOS3qgsState;
    int qgd_index = ckt->CKTstate0 + here->MOS3qgdState;
    int qgb_index = ckt->CKTstate0 + here->MOS3qgbState;
    
    double qgs_n2 = rhsOld[qgs_index];    /* Q_gs at t-2Δt */
    double qgd_n2 = rhsOld[qgd_index];    /* Q_gd at t-2Δt */
    double qgb_n2 = rhsOld[qgb_index];    /* Q_gb at t-2Δt */
    
    /* Polynomial extrapolation for charge prediction (Milne's method) */
    here->MOS3qgs_pred = 2.5 * here->MOS3qgs - 2.0 * qgs_old + 0.5 * qgs_n2;
    here->MOS3qgd_pred = 2.5 * here->MOS3qgd - 2.0 * qgd_old + 0.5 * qgd_n2;
    here->MOS3qgb_pred = 2.5 * here->MOS3qgb - 2.0 * qgb_old + 0.5 * qgb_n2;
    
    /* Calculate LTE for each charge component */
    double lte_qgs = fabs(here->MOS3qgs_pred - here->MOS3qgs) / 
                     (fabs(here->MOS3qgs) + 1.0);
    double lte_qgd = fabs(here->MOS3qgd_pred - here->MOS3qgd) / 
                     (fabs(here->MOS3qgd) + 1.0);
    double lte_qgb = fabs(here->MOS3qgb_pred - here->MOS3qgb) / 
                     (fabs(here->MOS3qgb) + 1.0);
    
    /* Take maximum LTE across all charge components */
    here->MOS3deltaCharge = MAX(lte_qgs, MAX(lte_qgd, lte_qgb));
    
    /* Calculate combined tolerance */
    double qref = MAX(fabs(here->MOS3qgs), 
                     MAX(fabs(here->MOS3qgd), fabs(here->MOS3qgb)));
    chargeTol = ckt->CKTchgtol + ckt->CKTreltol * qref;
    
    /* Adjust time step if LTE exceeds tolerance */
    if(here->MOS3deltaCharge > chargeTol) {
        factor = sqrt(chargeTol / here->MOS3deltaCharge);
        newStep = *timeStep * factor * 0.8;  /* 0.8 safety factor */
        
        /* Apply time step limits */
        if(newStep < *timeStep) {
            /* Only reduce time step, never increase from LTE */
            if(newStep < 0.1 * *timeStep) {
                newStep = 0.1 * *timeStep;    /* Minimum reduction */
            }
            if(newStep < 1e-18) {
                newStep = 1e-18;              /* Absolute minimum */
            }
            *timeStep = newStep;
            
            /* Signal that time step was reduced */
            return E_TIMESTEP;
        }
    }
    
    /* Store current charges for next LTE calculation */
    *(here->MOS3states[3]) = here->MOS3qgs;
    *(here->MOS3states[4]) = here->MOS3qgd;
    *(here->MOS3states[5]) = here->MOS3qgb;
    
    return OK;
}
```

### 3. Convergence Testing (`mos3conv.c`)

The `MOS3convTest()` function implements comprehensive convergence checking:

```c
int MOS3convTest(MOS3instance *here, MOS3model *model, 
                 CKTcircuit *ckt)
{
    double reltol = ckt->CKTreltol;
    double vntol = ckt->CKTvoltTol;
    double abstol = ckt->CKTabstol;
    double chgtol = ckt->CKTchgtol;
    
    /* Retrieve previous iteration values */
    double vgs_old = here->MOS3vgs_old;
    double vds_old = here->MOS3vds_old;
    double vbs_old = here->MOS3vbs_old;
    double cd_old = here->MOS3cd_old;
    double cbs_old = here->MOS3cbs_old;
    double cbd_old = here->MOS3cbd_old;
    double qgs_old = here->MOS3qgs_old;
    double qgd_old = here->MOS3qgd_old;
    
    /* Calculate deltas */
    here->MOS3delVgs = here->MOS3vgs - vgs_old;
    here->MOS3delVds = here->MOS3vds - vds_old;
    here->MOS3delVbs = here->MOS3vbs - vbs_old;
    here->MOS3delCd = here->MOS3cd - cd_old;
    here->MOS3delCbs = here->MOS3cbs - cbs_old;
    here->MOS3delCbd = here->MOS3cbd - cbd_old;
    here->MOS3delQgs = here->MOS3qgs - qgs_old;
    here->MOS3delQgd = here->MOS3qgd - qgd_old;
    
    /* Voltage convergence tests */
    double vgs_tol = reltol * MAX(fabs(here->MOS3vgs), fabs(vgs_old)) + vntol;
    double vds_tol = reltol * MAX(fabs(here->MOS3vds), fabs(vds_old)) + vntol;
    double vbs_tol = reltol * MAX(fabs(here->MOS3vbs), fabs(vbs_old)) + vntol;
    
    int voltage_converged = 
        (fabs(here->MOS3delVgs) <= vgs_tol) &&
        (fabs(here->MOS3delVds) <= vds_tol) &&
        (fabs(here->MOS3delVbs) <= vbs_tol);
    
    /* Current convergence tests */
    double cd_tol = reltol * MAX(fabs(here->MOS3cd), fabs(cd_old)) + abstol;
    double cbs_tol = reltol * MAX(fabs(here->MOS3cbs), fabs(cbs_old)) + abstol;
    double cbd_tol = reltol * MAX(fabs(here->MOS3cbd), fabs(cbd_old)) + abstol;
    
    int current_converged = 
        (fabs(here->MOS3delCd) <= cd_tol) &&
        (fabs(here->MOS3delCbs) <= cbs_tol) &&
        (fabs(here->MOS3delCbd) <= cbd_tol);
    
    /* Charge convergence tests (transient analysis only) */
    int charge_converged = 1;
    if(ckt->CKTmode & MODETRAN) {
        double qgs_tol = reltol * MAX(fabs(here->MOS3qgs), fabs(qgs_old)) + chgtol;
        double qgd_tol = reltol * MAX(fabs(here->MOS3qgd), fabs(qgd_old)) + chgtol;
        
        charge_converged = 
            (fabs(here->MOS3delQgs) <= qgs_tol) &&
            (fabs(here->MOS3delQgd) <= qgd_tol);
    }
    
    /* Check overall convergence */
    if(!(voltage_converged && current_converged && charge_converged)) {
        ckt->CKTnoncon++;
        
        /* Store current values for next iteration comparison */
        here->MOS3vgs_old = here->MOS3vgs;
        here->MOS3vds_old = here->MOS3vds;
        here->MOS3vbs_old = here->MOS3vbs;
        here->MOS3cd_old = here->MOS3cd;
        here->MOS3cbs_old = here->MOS3cbs;
        here->MOS3cbd_old = here->MOS3cbd;
        here->MOS3qgs_old = here->MOS3qgs;
        here->MOS3qgd_old = here->MOS3qgd;
        
        return E_NOT_CONVERGED;
    }
    
    return OK;
}
```

### 4. Initial Condition Handling (`mos3ic.c`)

The `MOS3ic()` function implements priority-based startup logic:

```c
int MOS3ic(MOS3instance *here, MOS3model *model, CKTcircuit *ckt)
{
    double vgs,