# MOS9: Transient Control and Charge Conservation

_Generated 2026-04-12 08:57 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9trun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9conv.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9ic.c`

# MOS9: Transient Control and Charge Conservation

## Chapter Introduction

In Ngspice's transient analysis framework, the MOS9 model implements rigorous time-domain simulation through three critical C files: `mos9trun.c`, `mos9conv.c`, and `mos9ic.c`. These modules collectively manage adaptive time-stepping, Newton-Raphson convergence verification, and initial condition establishment for the Philips MOS9 MOSFET model. The `mos9trun.c` file calculates Local Truncation Error (LTE) using third-order charge derivatives to control time-step adaptation, ensuring numerical accuracy while minimizing computational cost. `mos9conv.c` implements the convergence testing logic that validates voltage, charge, and current changes against SPICE's relative and absolute tolerances (`CKTreltol`, `CKTabstol`, `CKTchgtol`), employing the `DEVfetlim()` and `DEVlimvds()` functions to prevent Newton-Raphson divergence during rapid voltage transitions. Finally, `mos9ic.c` handles initial condition processing, prioritizing user-specified `.IC` values over DC operating points and initializing the seven-element state vector for charge conservation. Together, these files enforce the fundamental charge conservation principle `Q_G + Q_D + Q_S + Q_B = 0` through the Meyer charge partitioning model while maintaining numerical stability across all operating regions—cutoff, linear, and saturation—with continuous derivatives for robust transient simulation.

## Mathematical Formulation

The transient analysis of the MOS9 model in SPICE requires solving the time-dependent device equations while maintaining charge conservation and numerical stability. This involves the discretization of differential equations for charges and the implementation of local truncation error (LTE) control for adaptive time-stepping.

### 1. Charge Conservation Formulation

The fundamental principle of charge conservation in MOSFET modeling requires that the sum of terminal charges equals zero at all times:

```
Q_G + Q_D + Q_S + Q_B = 0
```

For the MOS9 model, this is implemented through the Meyer charge partitioning model with time derivatives computed using numerical integration.

#### 1.1 Terminal Charge Definitions

**Gate Charge Partitioning (Meyer Model):**
```
Q_GS = (2/3)·C_ox·W_eff·L_eff·[1 - ((V_GD - V_th)/(V_GS - V_th + V_GD - V_th))²]
Q_GD = (2/3)·C_ox·W_eff·L_eff·[1 - ((V_GS - V_th)/(V_GS - V_th + V_GD - V_th))²]
Q_GB = C_ox·W_eff·L_eff·(V_th - V_GB)/√(2φ - V_GB)  for V_GB < V_th
```

**Bulk Junction Charges:**
```
Q_BD = AD·CJ·∫(1 - V_BD/PB)^{-MJ} dV_BD + PD·CJSW·∫(1 - V_BD/PB)^{-MJSW} dV_BD
Q_BS = AS·CJ·∫(1 - V_BS/PB)^{-MJ} dV_BS + PS·CJSW·∫(1 - V_BS/PB)^{-MJSW} dV_BS
```

#### 1.2 Time Derivative Discretization

Using the trapezoidal integration method (default in SPICE), the current-charge relationship is:

```
I(t) = dQ/dt ≈ (Q(t) - Q(t-h))/h + O(h²)
```

For the backward Euler method (used for stiff circuits):
```
I(t) ≈ (Q(t) - Q(t-h))/h
```

The discretized form for the gate-source current becomes:
```
I_GS(t) = (Q_GS(t) - Q_GS(t-h))/h + (h/2)·d²Q_GS/dt²
```

### 2. Local Truncation Error (LTE) Control

The LTE calculation determines the maximum allowable time step while maintaining specified error tolerances. For charge-based LTE in MOS9:

#### 2.1 Charge LTE Formulation

The local truncation error for charge integration is bounded by:
```
ε_Q = |(h²/12)·Q⃛(ξ)| ≤ TOL_Q
```
where `ξ ∈ [t-h, t]` and `TOL_Q = CKTchgtol + CKTreltol·|Q|`

For the MOS9 implementation, this is approximated using third-order differences:
```
Q⃛(t) ≈ [Q(t) - 3Q(t-h) + 3Q(t-2h) - Q(t-3h)]/h³
```

Thus the LTE estimate becomes:
```
ε_Q ≈ |(h²/12)·[Q(t) - 3Q(t-h) + 3Q(t-2h) - Q(t-3h)]/h³|
     = |[Q(t) - 3Q(t-h) + 3Q(t-2h) - Q(t-3h)]/(12h)|
```

#### 2.2 Current LTE Formulation

For the drain current, the LTE is calculated from the derivative continuity:
```
ε_I = |(h²/6)·I⃛(ξ)| ≤ TOL_I
```
where `TOL_I = CKTabstol + CKTreltol·|I_DS|`

The third derivative is estimated from history:
```
I⃛(t) ≈ [I_DS(t) - 3I_DS(t-h) + 3I_DS(t-2h) - I_DS(t-3h)]/h³
```

### 3. Numerical Integration Methods

#### 3.1 Trapezoidal Rule Implementation

The charge update using trapezoidal integration:
```
Q(t) = Q(t-h) + (h/2)·[I(t) + I(t-h)]
```

This requires solving the implicit equation:
```
I(t) = f(V(t), Q(t)) = [2/h·(Q(t) - Q(t-h))] - I(t-h)
```

#### 3.2 Gear Integration (Order 2)

For stiff problems, Gear's method provides better stability:
```
Q(t) = (4/3)·Q(t-h) - (1/3)·Q(t-2h) + (2h/3)·I(t)
```

### 4. Voltage Limiting for Convergence

To ensure Newton-Raphson convergence during transient analysis, the MOS9 model employs voltage limiting functions:

#### 4.1 Gate-Source Voltage Limiting

The `DEVfetlim()` function implements smooth limiting:
```
V_GS_limited = V_GS_old + δ·ln(1 + (V_GS_new - V_GS_old)/(δ·(1 + 2·(V_GS_new - V_GS_old)/δ)))
```
where `δ = 2·n·V_T` (thermal voltage) for smooth transition.

#### 4.2 Drain-Source Voltage Limiting

For `V_DS` limiting to prevent numerical overflow:
```
V_DS_limited = V_DS_old + sign(ΔV)·δ·ln(1 + |ΔV|/δ)
where ΔV = V_DS_new - V_DS_old, δ = 0.5·(V_DS_old + V_DS_sat)
```

### 5. State Vector Management

The MOS9 model maintains a state vector with 7 charge components for accurate transient analysis:

```
State Vector Indices:
0: Q_GS - Gate-source charge
1: Q_GD - Gate-drain charge  
2: Q_GB - Gate-bulk charge
3: Q_BD - Bulk-drain junction charge
4: Q_BS - Bulk-source junction charge
5: Q_BD_jct - Bulk-drain junction charge (separate for nonlinear C)
6: Q_BS_jct - Bulk-source junction charge (separate for nonlinear C)
```

## Convergence Analysis

### 1. Transient Convergence Criteria

For Newton-Raphson iteration at each time point, convergence requires:

#### 1.1 Voltage Convergence

```
|V_k - V_{k-1}| < ε_V = max(CKTvoltTol, CKTreltol·|V| + CKTabstol)
```
where:
- `CKTvoltTol = 1×10⁻⁶` (voltage tolerance)
- `CKTreltol = 1×10⁻³` (relative tolerance)
- `CKTabstol = 1×10⁻¹²` (absolute tolerance)

#### 1.2 Charge Convergence

```
|Q_k - Q_{k-1}| < ε_Q = max(CKTchgtol, CKTreltol·|Q|)
```
where `CKTchgtol = 1×10⁻¹⁴` (charge tolerance)

#### 1.3 Current Convergence

```
|I_k - I_{k-1}| < ε_I = max(CKTabstol, CKTreltol·|I|)
```

### 2. Time Step Control Algorithm

The adaptive time-stepping in MOS9 follows the SPICE LTE control algorithm:

#### 2.1 LTE Calculation per Device

For each charge component `i`:
```
LTE_Q_i = |[Q_i(t) - 3Q_i(t-h) + 3Q_i(t-2h) - Q_i(t-3h)]/(12h)|
```

The normalized error is:
```
Err_Q_i = LTE_Q_i / (CKTchgtol + CKTreltol·|Q_i|)
```

#### 2.2 Time Step Prediction

The maximum allowable time step based on LTE:
```
h_new = h_current · min(1.5, 0.9/√(max(Err_Q_i)))
```

With safety factors:
- Upper bound: `h_new ≤ 2·h_current`
- Lower bound: `h_new ≥ h_min = 1×10⁻¹⁸` seconds

#### 2.3 Truncation Error Ratio Check

For each time step acceptance:
```
max(Err_Q_i) ≤ 1.0
```

If violated, the time step is reduced by:
```
h_reduced = h_current · 0.5/√(max(Err_Q_i))
```

### 3. Charge Conservation Enforcement

#### 3.1 Terminal Current Consistency

The sum of terminal currents must satisfy:
```
|I_G + I_D + I_S + I_B| < ε_sum = 10·max(ε_I)
```

If violated, charge redistribution is applied:
```
ΔQ = h·(I_G + I_D + I_S + I_B)
Q_corrected = Q - ΔQ/4  (distributed equally to all terminals)
```

#### 3.2 State Vector Consistency Check

After each Newton iteration, the state vector is checked:
```
|Q_GS + Q_GD + Q_GB - (Q_BD + Q_BS)| < ε_charge
```

If the imbalance exceeds `ε_charge = 1×10⁻¹⁰`, a correction is applied to maintain:
```
Q_GB_corrected = Q_GB - (Q_GS + Q_GD + Q_GB - Q_BD - Q_BS)
```

### 4. Numerical Stability Conditions

#### 4.1 Capacitance Positivity Enforcement

All capacitances must remain positive for stability:
```
C_GS = max(0, ∂Q_GS/∂V_GS)
C_GD = max(0, ∂Q_GD/∂V_GD)  
C_GB = max(0, ∂Q_GB/∂V_GB)
```

If negative capacitances are detected, they are clipped to `GMIN = 1×10⁻¹²` F.

#### 4.2 Time Step Limiting for Rapid Changes

During rapid voltage transitions, additional limits apply:

**Gate Voltage Slew Rate Limit:**
```
h ≤ 0.1·τ_GS where τ_GS = C_GS/g_m
```

**Drain Voltage Slew Rate Limit:**
```
h ≤ 0.1·τ_DS where τ_DS = C_DS/g_ds
```

#### 4.3 Newton Iteration Limit Protection

To prevent infinite loops:
- Maximum iterations: `MAX_ITER = 100`
- If not converged after 50 iterations, apply damping:
  ```
  V_new = 0.5·(V_old + V_new)
  ```
- If still not converged after 100 iterations, reduce time step by factor of 10

### 5. Temperature-Dependent Transient Behavior

#### 5.1 Thermal Time Constant Effects

The MOS9 model accounts for thermal time constants through:
```
τ_thermal = R_th·C_th
```
where `R_th` is thermal resistance and `C_th` is thermal capacitance.

The temperature update equation:
```
T(t) = T(t-h) + (h/τ_thermal)·[T_ambient - T(t-h)] + (h/C_th)·P_diss(t)
```

#### 5.2 Self-Heating Integration

For devices with self-heating (`RTH`, `CTH` parameters):
```
P_diss(t) = I_DS(t)·V_DS(t) + I_BD(t)·V_BD(t) + I_BS(t)·V_BS(t)
ΔT(t) = T(t) - T_ambient = ∫[P_diss(t')·exp(-(t-t')/τ_thermal)]dt'
```

This is integrated using the same numerical method as charge integration.

### 6. Convergence Acceleration Techniques

#### 6.1 Predictive Voltage Extrapolation

For smooth waveforms, voltage prediction reduces iterations:
```
V_predicted(t+h) = 2·V(t) - V(t-h)  (linear extrapolation)
V_predicted(t+h) = 3·V(t) - 3·V(t-h) + V(t-2h)  (quadratic extrapolation)
```

#### 6.2 Adaptive GMIN Stepping

If convergence fails, GMIN is temporarily increased:
```
GMIN_effective = GMIN·10^k, k = 1,2,3,... until convergence
```

After convergence, GMIN is gradually reduced back to nominal value.

#### 6.3 Source Stepping for Hard Convergence

For difficult initial conditions, source stepping is employed:
```
V_source = λ·V_source_nominal, λ: 0 → 1
```

The homotopy parameter λ increases gradually from 0 to 1 over several Newton iterations.

This mathematical formulation ensures that the MOS9 model maintains charge conservation, numerical stability, and accurate transient response while adhering to SPICE's rigorous convergence requirements for robust circuit simulation.

----------

# MOS9: Transient Control and Charge Conservation

## C Implementation

### 1. Core Data Structures for Transient Analysis

#### 1.1 Instance Structure Extensions for Charge Conservation

The `sMOS9instance` structure in `mos9defs.h` contains critical fields for transient analysis and charge conservation:

```c
typedef struct sMOS9instance {
    /* ... existing fields from previous chapters ... */
    
    /* Charge state variables for transient analysis */
    double MOS9qgs;                /* Gate-source charge */
    double MOS9qgd;                /* Gate-drain charge */
    double MOS9qgb;                /* Gate-bulk charge */
    double MOS9qbd;                /* Bulk-drain charge */
    double MOS9qbs;                /* Bulk-source charge */
    
    /* Previous time-step values for LTE calculation */
    double MOS9qgs_old;            /* Previous gate-source charge */
    double MOS9qgd_old;            /* Previous gate-drain charge */
    double MOS9qgb_old;            /* Previous gate-bulk charge */
    double MOS9qbd_old;            /* Previous bulk-drain charge */
    double MOS9qbs_old;            /* Previous bulk-source charge */
    
    /* Charge derivatives for capacitance calculation */
    double MOS9cqgs;               /* d(qgs)/dt */
    double MOS9cqgd;               /* d(qgd)/dt */
    double MOS9cqgb;               /* d(qgb)/dt */
    double MOS9cqbd;               /* d(qbd)/dt */
    double MOS9cqbs;               /* d(qbs)/dt */
    
    /* State vector indices for charge conservation */
    int MOS9states[7];             /* Indices for: qgs, qgd, qgb, qbd, qbs, qbd_jct, qbs_jct */
    
    /* Transient analysis flags */
    int MOS9mode;                  /* Operating mode: cutoff, linear, saturation */
    double MOS9vdsat;              /* Saturation voltage */
    double MOS9von;                /* Turn-on voltage */
    
    /* Convergence history for time-step control */
    double MOS9vgs_hist[3];        /* Vgs history for derivative estimation */
    double MOS9vds_hist[3];        /* Vds history for derivative estimation */
    double MOS9vbs_hist[3];        /* Vbs history for derivative estimation */
    int MOS9hist_ptr;              /* History array pointer */
    
    /* ... matrix pointers and other fields ... */
} MOS9instance;
```

#### 1.2 Model Structure Extensions for Transient Parameters

The `sMOS9model` structure includes parameters controlling transient behavior:

```c
typedef struct sMOS9model {
    /* ... existing model parameters ... */
    
    /* Transient analysis parameters */
    double MOS9trtol;              /* Local truncation error tolerance */
    double MOS9chgtol;             /* Charge tolerance */
    double MOS9abstol;             /* Absolute current tolerance */
    double MOS9reltol;             /* Relative voltage tolerance */
    
    /* Numerical integration method flags */
    int MOS9method;                /* Integration method: trapezoidal, gear, etc. */
    double MOS9maxstep;            /* Maximum time step */
    double MOS9minstep;            /* Minimum time step */
    
    /* Convergence control parameters */
    int MOS9itl1;                  /* DC iteration limit */
    int MOS9itl2;                  /* DC iteration limit (Gmin stepping) */
    int MOS9itl3;                  /* Transient iteration limit */
    int MOS9itl4;                  /* Transient iteration limit (source stepping) */
    
    /* Charge conservation enforcement */
    int MOS9charge;                /* Charge conservation flag */
    int MOS9ic;                    /* Initial condition flag */
    
    /* ... other model fields ... */
} MOS9model;
```

### 2. Transient Load Function Implementation (`mos9tr.c`)

#### 2.1 Main Transient Load Function

The `MOS9trunc()` function in `mos9tr.c` implements the Local Truncation Error (LTE) calculation:

```c
int MOS9trunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep) {
    MOS9model *model;
    MOS9instance *inst;
    double del1, del2, del3;
    double tol, charge_tol;
    double q_error, max_error;
    int error_flag = 0;
    
    /* Get circuit tolerances */
    tol = ckt->CKTtrtol;           /* Default = 7.0 */
    charge_tol = ckt->CKTchgtol;   /* Charge tolerance */
    
    for(model = (MOS9model *)inModel; model != NULL; model = model->MOS9nextModel) {
        for(inst = model->MOS9instances; inst != NULL; inst = inst->MOS9nextInstance) {
            
            /* Calculate charge changes using backward differentiation */
            del1 = inst->MOS9qgs - inst->MOS9qgs_old;
            del2 = inst->MOS9qgd - inst->MOS9qgd_old;
            del3 = inst->MOS9qgb - inst->MOS9qgb_old;
            
            /* Estimate second derivative using three-point formula */
            double h = ckt->CKTdeltaOld[0];  /* Previous time step */
            double h2 = ckt->CKTdeltaOld[1]; /* Two steps back */
            
            /* Second derivative estimation for LTE bound */
            double qgs_ddot = (inst->MOS9qgs - 2*inst->MOS9qgs_old + 
                              *(ckt->CKTrhsOld + inst->MOS9states[0] - 2)) / (h*h);
            double qgd_ddot = (inst->MOS9qgd - 2*inst->MOS9qgd_old + 
                              *(ckt->CKTrhsOld + inst->MOS9states[1] - 2)) / (h*h);
            double qgb_ddot = (inst->MOS9qgb - 2*inst->MOS9qgb_old + 
                              *(ckt->CKTrhsOld + inst->MOS9states[2] - 2)) / (h*h);
            
            /* LTE error bound: ε ≤ |h²·q̈/12| for trapezoidal rule */
            double lte_qgs = fabs(h*h * qgs_ddot / 12.0);
            double lte_qgd = fabs(h*h * qgd_ddot / 12.0);
            double lte_qgb = fabs(h*h * qgb_ddot / 12.0);
            
            /* Normalized error calculation */
            double norm_qgs = MAX(fabs(inst->MOS9qgs), charge_tol);
            double norm_qgd = MAX(fabs(inst->MOS9qgd), charge_tol);
            double norm_qgb = MAX(fabs(inst->MOS9qgb), charge_tol);
            
            double error_qgs = lte_qgs / norm_qgs;
            double error_qgd = lte_qgd / norm_qgd;
            double error_qgb = lte_qgb / norm_qgb;
            
            /* Find maximum error */
            max_error = MAX(error_qgs, MAX(error_qgd, error_qgb));
            
            /* Adjust time step based on LTE */
            if(max_error > tol) {
                /* Error too large - reduce time step */
                double factor = pow(tol / max_error, 1.0/3.0);  /* Cubic root for 2nd order method */
                factor = MAX(0.5, MIN(factor, 0.9));  /* Limit reduction factor */
                *timeStep = *timeStep * factor;
                error_flag = 1;
            } else if(max_error < tol/10.0) {
                /* Error too small - increase time step */
                double factor = pow(tol / (2.0 * max_error), 1.0/3.0);
                factor = MIN(2.0, MAX(factor, 1.1));  /* Limit increase factor */
                *timeStep = *timeStep * factor;
            }
            
            /* Store current charges for next LTE calculation */
            inst->MOS9qgs_old = inst->MOS9qgs;
            inst->MOS9qgd_old = inst->MOS9qgd;
            inst->MOS9qgb_old = inst->MOS9qgb;
            inst->MOS9qbd_old = inst->MOS9qbd;
            inst->MOS9qbs_old = inst->MOS9qbs;
        }
    }
    
    return error_flag;
}
```

#### 2.2 Charge Calculation and Conservation

The `MOS9load()` function in `mos9ld.c` includes charge calculation for transient analysis:

```c
int MOS9load(GENmodel *inModel, CKTcircuit *ckt) {
    MOS9model *model;
    MOS9instance *inst;
    
    for(model = (MOS9model *)inModel; model != NULL; model = model->MOS9nextModel) {
        for(inst = model->MOS9instances; inst != NULL; inst = inst->MOS9nextInstance) {
            
            /* Calculate terminal voltages with limiting */
            double vgs = DEVfetlim(inst->MOS9vgs, inst->MOS9vgs_old, 
                                   model->MOS9vt, model->MOS9vt);
            double vds = DEVlimvds(inst->MOS9vds, inst->MOS9vds_old);
            double vbs = inst->MOS9vbs;
            
            /* Calculate charges using Meyer model */
            if(vgs > inst->MOS9von) {
                /* Inversion region */
                double vgd = vgs - vds;
                double vgt = vgs - inst->MOS9von;
                double vgdt = vgd - inst->MOS9von;
                
                /* Gate charges */
                inst->MOS9qgs = model->MOS9cgso * inst->MOS9weff +
                               (2.0/3.0) * model->MOS9cox * inst->MOS9weff * inst->MOS9leff *
                               (1.0 - pow(vgdt/(vgt + vgdt), 2));
                
                inst->MOS9qgd = model->MOS9cgdo * inst->MOS9weff +
                               (2.0/3.0) * model->MOS9cox * inst->MOS9weff * inst->MOS9leff *
                               (1.0 - pow(vgt/(vgt + vgdt), 2));
                
                inst->MOS9qgb = model->MOS9cgbo * inst->MOS9leff;
            } else {
                /* Accumulation/depletion region */
                inst->MOS9qgs = model->MOS9cgso * inst->MOS9weff;
                inst->MOS9qgd = model->MOS9cgdo * inst->MOS9weff;
                
                if(vgs < inst->MOS9von) {
                    inst->MOS9qgb = model->MOS9cgbo * inst->MOS9leff +
                                   model->MOS9cox * inst->MOS9weff * inst->MOS9leff *
                                   (inst->MOS9von - vgs) / sqrt(2 * model->MOS9phi - vbs);
                } else {
                    inst->MOS9qgb = model->MOS9cgbo * inst->MOS9leff;
                }
            }
            
            /* Junction charges */
            double vbd = vbs - vds;
            inst->MOS9qbd = MOS9juncCapCharge(model, inst, vbd, inst->MOS9ad, inst->MOS9pd);
            inst->MOS9qbs = MOS9juncCapCharge(model, inst, vbs, inst->MOS9as, inst->MOS9ps);
            
            /* Calculate capacitive currents using numerical differentiation */
            if(ckt->CKTmode & MODEINITTRAN) {
                /* Initial transient - use backward Euler */
                double delta = ckt->CKTdelta;
                inst->MOS9cqgs = (inst->MOS9qgs - inst->MOS9qgs_old) / delta;
                inst->MOS9cqgd = (inst->MOS9qgd - inst->MOS9qgd_old) / delta;
                inst->MOS9cqgb = (inst->MOS9qgb - inst->MOS9qgb_old) / delta;
                inst->MOS9cqbd = (inst->MOS9qbd - inst->MOS9qbd_old) / delta;
                inst->MOS9cqbs = (inst->MOS9qbs - inst->MOS9qbs_old) / delta;
            } else {
                /* Steady state - use trapezoidal integration */
                double delta = ckt->CKTdelta;
                inst->MOS9cqgs = 0.5 * (inst->MOS9qgs - inst->MOS9qgs_old) / delta;
                inst->MOS9cqgd = 0.5 * (inst->MOS9qgd - inst->MOS9qgd_old) / delta;
                inst->MOS9cqgb = 0.5 * (inst->MOS9qgb - inst->MOS9qgb_old) / delta;
                inst->MOS9cqbd = 0.5 * (inst->MOS9qbd - inst->MOS9qbd_old) / delta;
                inst->MOS9cqbs = 0.5 * (inst->MOS9qbs - inst->MOS9qbs_old) / delta;
            }
            
            /* Stamp capacitive currents into matrix */
            *(inst->MOS9DPgPtr) += inst->MOS9cqgs;
            *(inst->MOS9SPgPtr) -= inst->MOS9cqgs;
            *(inst->MOS9DPgPtr) += inst->MOS9cqgd;
            *(inst->MOS9SPgPtr) -= inst->MOS9cqgd;
            *(inst->MOS9DPbPtr) += inst->MOS9cqgb;
            *(inst->MOS9SPbPtr) -= inst->MOS9cqgb;
            
            /* Stamp junction capacitive currents */
            *(inst->MOS9BbPtr) += inst->MOS9cqbd + inst->MOS9cqbs;
            *(inst->MOS9DPbPtr) -= inst->MOS9cqbd;
            *(inst->MOS9SPbPtr) -= inst->MOS9cqbs;
        }
    }
    
    return OK;
}
```

### 3. Convergence Testing Implementation (`mos9conv.c`)

#### 3.1 Convergence Test Function

The `MOS9convTest()` function checks Newton-Raphson convergence:

```c
int MOS9convTest(GENmodel *inModel, CKTcircuit *ckt) {
    MOS9model *model;
    MOS9instance *inst;
    double delvgs, delvds, delvbs;
    double delqgs, delqgd, delqgb, delqbd, delqbs;
    double reltol, abstol, chgtol;
    int converged = 1;
    
    /* Get circuit tolerances */
    reltol = ckt->CKTreltol;      /* Default = 0.001 */
    abstol = ckt->CKTabstol;      /* Default = 1e-12 */
    chgtol = ckt->CKTchgtol;      /* Charge tolerance */
    
    for(model = (MOS9model *)inModel; model != NULL; model = model->MOS9nextModel) {
        for(inst = model->MOS9instances; inst != NULL; inst = inst->MOS9nextInstance) {
            
            /* Calculate voltage changes */
            delvgs = ckt->CKTstate0[inst->MOS9states[0]] - ckt->CKTstate1[inst->MOS9states[0]];
            delvds = ckt->CKTstate0[inst->MOS9states[1]] - ckt->CKTstate1[inst->MOS9states[1]];
            delvbs = ckt->CKTstate0[inst->MOS9states[2]] - ckt->CKTstate1[inst->MOS9states[2]];
            
            /* Calculate charge changes */
            delqgs = inst->MOS9qgs - *(ckt->CKTrhsOld + inst->MOS9states[0]);
            delqgd = inst->MOS9qgd - *(ckt->CKTrhsOld + inst->MOS9states[1]);
            delqgb = inst->MOS9qgb - *(ckt->CKTrhsOld + inst->MOS9states[2]);
            delqbd = inst->MOS9qbd - *(ckt->CKTrhsOld + inst->MOS9states[3]);
            delqbs = inst->MOS9qbs - *(ckt->CKTrhsOld + inst->MOS9states[4]);
            
            /* Normalize voltage changes */
            double vgs_norm = MAX(fabs(ckt->CKTstate0[inst->MOS9states[0]]), abstol);
            double vds_norm = MAX(fabs(ckt->CKTstate0[inst->MOS9states[1]]), abstol);
            double vbs_norm = MAX(fabs(ckt->CKTstate0[inst->MOS9states[2]]), abstol);
            
            double vgs_error = fabs(delvgs) / (reltol * vgs_norm + abstol);
            double vds_error = fabs(delvds) / (reltol * vds_norm + abstol);
            double vbs_error = fabs(delvbs) / (reltol * vbs_norm + abstol);
            
            /* Normalize charge changes */
            double qgs_norm = MAX(fabs(inst->MOS9qgs), chgtol);
            double qgd_norm = MAX(fabs(inst->MOS9qgd), chgtol);
            double qgb_norm = MAX(fabs(inst->MOS9qgb), chgtol);
            double qbd_norm = MAX(fabs(inst->MOS9qbd), chgtol);
            double qbs_norm = MAX(fabs(inst->MOS9qbs), chgtol);
            
            double qgs_error = fabs(delqgs) / (reltol * qgs_norm + chgtol);
            double qgd_error = fabs(delqgd) / (reltol * qgd_norm + chgtol);
            double qgb_error = fabs(delqgb) / (reltol * qgb_norm + chgtol);
            double qbd_error = fabs(delqbd) / (reltol * qbd_norm + chgtol);
            double qbs_error = fabs(delqbs) / (reltol * qbs_norm + chgtol);
            
            /* Check convergence criteria */
            if(vgs_error > 1.0 || vds_error > 1.0 || vbs_error > 1.0 ||
               qgs_error > 1.0 || qgd_error > 1.0 || qgb_error > 1.0 ||
               qbd_error > 1.0 || qbs_error > 1.0) {
                converged = 0;
                break;
            }
            
            /* Check current convergence */
            double cdrain_norm = MAX(fabs(inst->MOS9cdrain), abstol);
            double cdrain_error = fabs(inst->MOS9cdrain - inst->MOS9cdrain_old) / 
                                  (reltol * cdrain_norm + abstol);
            
            if(cdrain_error > 1.0) {
                converged = 0;
                break;
            }
        }
        
        if(!converged) break;
    }
    
    return converged ? OK : E_NOT_CONVERGED;
}
```

#### 3.2 Voltage Limiting Functions

The `DEVfetlim()` and `DEVlimvds()` functions prevent Newton-Raphson divergence:

```c
double DEVfetlim(double vnew, double vold, double vto, double vcrit) {
    double delv, vtemp;
    
    if(vold > vcrit) {
        if(vnew > vcrit) {
            /* Use linear continuation */
            if(vnew > vold + vto) {
                vnew = vold + vto;
            } else if(vnew < vold - vto) {
                vnew = vold - vto;
            }
        } else {
            /* Transition region - use quadratic limiting */
            delv = vnew - vold;
            if(delv <= 0) {
                return vnew;  /* Going downward - no limiting needed */
            } else {
                /* Going upward into cutoff - limit the change */
                vtemp = vcrit + vto;
                if(vold < vtemp) {
                    vtemp = (vtemp + vold) / 2.0;
                }
                if(vnew > vtemp) {
                    vnew = vtemp;
                }
            }
        }
    } else {
        /* Below critical voltage - use different limiting */
        if(vnew < vcrit) {
            /* Stay in subthreshold region */
            if(vnew > vold + vto/2) {
                vnew = vold + vto/2;
            } else if(vnew < vold - vto/2) {
                vnew = vold - vto/2;
            }
        } else {
            /* Transition to above-threshold */
            vtemp = (vcrit + vold) / 2.0;
            if(vnew < vtemp) {
                vnew = vtemp;
            }
        }
    }
    
    return vnew;
}

double DEVlimvds(double vnew, double vold) {
    double delv, vtemp;
    
    /* Limit Vds changes to prevent sign reversal issues */
    delv = vnew - vold;
    
    if(vold >= 0) {
        if(delv <= 0) {
            /* Vds decreasing */
            if(vnew < 0) {
                vnew = 0;  /* Prevent sign change */
            }
        } else {
            /* Vds increasing */
            if(vnew > 2 * vold) {
                vnew = 2 * vold;  /* Limit increase */
            }
        }
    } else {
        if(delv >= 0) {
            /* Negative Vds becoming less negative */
            if(vnew > 0) {
                vnew = 0;  /* Prevent sign change */
            }
        } else {
            /* Negative Vds becoming more negative */
            if(vnew < 2 * vold) {
                vnew = 2 * vold;  /* Limit decrease */
            }
        }
    }
    
    return vnew;
}
```

### 4. Initial Condition Implementation (`mos9ic.c`)

#### 4.1 Initial Condition Function

The `MOS9ic()` function sets initial conditions for transient analysis:

```c
int MOS9ic(GENmodel *inModel, CKTcircuit *ckt) {
    MOS9model *model;
    MOS9instance *inst;