# BSIM4v5: Transient Control and Charge Conservation

_Generated 2026-04-12 14:38 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5trunc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5cvtest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5getic.c`

# Chapter: BSIM4v5: Transient Control and Charge Conservation

## Technical Introduction

The BSIM4v5 model in Ngspice implements a comprehensive, physics-based MOSFET model for sub-100nm CMOS technologies, requiring sophisticated transient control and charge conservation mechanisms. The `b4v5trunc.c` file calculates Local Truncation Error (LTE) for adaptive time-step control using charge-based formulations. The `b4v5cvtest.c` file performs Newton-Raphson convergence testing, checking voltage, current, and charge changes against SPICE's numerical tolerances (`CKTreltol`, `CKTabstol`, `CKTvoltTol`). The `b4v5getic.c` file handles initial condition computation for `.IC` statements and operating point analysis. These routines work in concert with the core load function in `b4v5ld.c`, which implements the trapezoidal integration rule for charge conservation, ensuring numerical stability during transient simulation of advanced nanometer-scale circuits.

## Mathematical Formulation

### Threshold Voltage with Advanced Physical Effects

The BSIM4v5 threshold voltage incorporates multiple nanometer-scale physical effects critical for accurate SPICE simulation:

**Base Threshold Voltage with Body Effect:**
```
Vth0_eff = VTH0 + (K1 × (√(PHI + Vsb) - √PHI)) 
                   - (K2 × Vsb)
                   + (K1B × (√(PHI + Vsb) - √PHI))
```

**Short-Channel Effects (SCE) for Sub-100nm Devices:**
```
ΔVth_SCE = -DVT0 × [cosh(DVT1 × Leff/L0) - 1] × Vds
```
where `L0 = 1μm` serves as the reference length for scaling. This term models the threshold voltage roll-off due to charge sharing between source and drain.

**Drain-Induced Barrier Lowering (DIBL):**
```
ΔVth_DIBL = -(ETA0 + ETAB × Vsb) × Vds
```
This formulation captures the voltage-dependent barrier lowering that becomes significant in short-channel devices.

**Narrow Width Effects:**
```
ΔVth_NWE = (K3 + K3B × Vsb) × TOXE/Weff × √(PHI + Vsb)
```

**Layout-Dependent Effects (STI Stress and Well Proximity):**
```
ΔVth_STI = (SA/Leff + SB/Weff) × exp(-SD/d)
ΔVth_WPE = WPE × [1 - exp(-L/λ_WPE)] × [1 - exp(-W/λ_WPE)]
```
where `λ_WPE ≈ 0.1μm` represents the characteristic scattering length for well proximity effects.

**Complete Threshold Voltage for SPICE Matrix Stamping:**
```
Vth = Vth0_eff + ΔVth_SCE + ΔVth_DIBL + ΔVth_NWE 
      + ΔVth_STI + ΔVth_WPE
```
This composite `Vth` directly influences the `gm`, `gds`, and `gmb` derivatives stamped into the Jacobian matrix during Newton-Raphson iterations.

### Mobility Degradation Model for Numerical Stability

**Vertical Field Degradation:**
```
μ_vfe = U0 / [1 + UA × (Vgsteff + 2VTH)/TOXE 
               + UB × (Vgsteff + 2VTH)²/TOXE²]
```

**Surface Roughness Scattering:**
```
μ_sr = 1 / [1 + UC × (Vbs + PHI)/TOXE]
```

**Velocity Saturation for High-Field Conditions:**
```
μ_vsat = 1 / [1 + (Eeff/Esat)]
where Eeff = (Vgsteff + 2VTH)/(TOXE × U0)
      Esat = 2 × Vsat / μ_eff
```

**Effective Mobility for Current Calculation:**
```
μ_eff = μ_vfe × μ_sr × μ_vsat
```
The mobility derivatives `∂μ_eff/∂Vgs`, `∂μ_eff/∂Vds`, `∂μ_eff/∂Vbs` contribute to the conductance matrix elements during AC analysis.

### Drain Current Formulation with Smooth Blending

**Effective Gate Drive Voltage with Continuous Transition:**
```
Vgsteff = 2 × n × Vt × ln[1 + exp((Vgs - Vth)/(2 × n × Vt))]
where n = 1 + NFACTOR × (CIT + CDSC + CDSCD × Vds)/Cox
```
This formulation ensures C¹ continuity for Newton-Raphson convergence.

**Linear Region Current:**
```
Id_lin = μ_eff × Cox × (Weff/Leff) × Vgsteff × Vds 
         × [1 - 0.5 × A0 × Vds/(Vgsteff + 2Vt)]
```

**Saturation Voltage Definition:**
```
Vdsat = (Vgsteff × Esat × Leff)/(Vgsteff + Esat × Leff)
```

**Saturation Region Current:**
```
Id_sat = μ_eff × Cox × (Weff/Leff) × Vgsteff × Vdsat
         × [1 + LAMBDA × (Vds - Vdsat)]
```

**Smooth Transition Function for Numerical Continuity:**
```
Id = Id_sat × [1 + (Vds/Vdsat)^M]^(-1/M)
where M = 3 (smoothing parameter)
```
This blending function ensures C¹ continuity at the `Vds = Vdsat` boundary, preventing Newton-Raphson oscillations.

### Capacitance and Charge Model for Charge Conservation

**Gate-Channel Charge Partitioning:**
```
Qgc = Cox × Weff × Leff × [Vgs - VFB - φ_s - 0.5×(Vds + Δ)]
where Δ = (A0 × Vds²)/(12×(Vgs - Vth - 0.5×A0×Vds))
```

**Terminal Charge Derivatives for Capacitance Matrix:**
```
Cgs = ∂Qg/∂Vs - ∂Qg/∂Vg
Cgd = ∂Qg/∂Vd - ∂Qg/∂Vg  
Cgb = ∂Qg/∂Vb - ∂Qg/∂Vg
```
These derivatives form the capacitance matrix `C` in the complex admittance formulation `Y(ω) = G + jωC`.

**Overlap Capacitances for Parasitic Effects:**
```
Cgso = CGSO × Weff
Cgdo = CGDO × Weff  
Cgbo = CGBO × Leff
```

### Temperature Scaling for Circuit Reliability

**Mobility Temperature Dependence:**
```
μ(T) = μ(Tnom) × (T/Tnom)^(-UTE)
where UTE ≈ 1.5 for electrons
```

**Threshold Voltage Temperature Dependence:**
```
Vth(T) = Vth(Tnom) + (KT1 + KT1L/Leff) × (T/Tnom - 1)
        + KT2 × Vbs × (T/Tnom - 1)
```

**Saturation Velocity Temperature Dependence:**
```
Vsat(T) = Vsat(Tnom) × (T/Tnom)^(-AT)
```
These temperature dependencies are computed in `b4v5temp.c` and affect all conductance and capacitance matrix entries.

## Convergence Analysis

### Local Truncation Error (LTE) for Adaptive Time-Step Control

**Charge-Based LTE Formulation:**
For backward Euler integration in SPICE transient analysis:
```
LTE = |h × dq/dt - (q_n - q_{n-1})|
where h = CKTdelta (time step), q = terminal charge
```

**More Accurate Estimation Using Taylor Expansion:**
```
LTE ≈ (h²/12) × |d³q/dt³|
```
Implemented in `b4v5trunc.c` as:
```
q_pred = 2q_n - q_{n-1}  (linear prediction)
q_actual = q_{n+1}       (from device equations)
LTE = |q_actual - q_pred|
```

**SPICE Integration with Tolerance Checking:**
```
TOL = CKTtrtol × (RELTOL × |q| + ABSTOL)
where CKTtrtol = 7 (default truncation error tolerance)
      RELTOL = 0.001 (relative tolerance)
      ABSTOL = 1e-12 (absolute tolerance)
```
If `LTE > TOL`, the time step is reduced; if `LTE < TOL/10`, the time step is increased.

### Newton-Raphson Convergence Criteria

**Voltage Convergence Test:**
```
|V_new - V_old| < RELTOL × max(|V_new|, |V_old|) + VNTOL
where VNTOL = 1e-6 (1μV voltage tolerance)
```
Applied to `Vgs`, `Vds`, and `Vbs` separately in `b4v5cvtest.c`.

**Current Convergence Test:**
```
|I_new - I_old| < RELTOL × max(|I_new|, |I_old|) + ABSTOL
where ABSTOL = 1e-12 (1pA current tolerance)
```

**Charge Convergence Test for Charge-Conservative Models:**
```
|Q_new - Q_old| < RELTOL × max(|Q_new|, |Q_old|) + CHGTOL
where CHGTOL = 1e-14 (charge tolerance)
```
Applied to gate, drain, source, and bulk charges stored in the state vector.

**SPICE Convergence Variables:**
- `CKTnoncon`: Counter for non-convergence events
- `CKTreltol = 0.001`: Relative tolerance (default)
- `CKTabstol = 1e-12`: Absolute current tolerance
- `CKTvoltTol = 1e-6`: Voltage tolerance
- `CKTchargeTol = 1e-14`: Charge tolerance

### Numerical Integration for Charge Conservation

**Trapezoidal Rule Implementation:**
For each terminal charge `Q` (gate, bulk) in `b4v5ld.c`:
```
I_cap(t_n) = (2/Δt)[Q(t_n) - Q(t_{n-1})] - I_cap(t_{n-1})
where Δt = CKTdelta
```
This ensures charge conservation to machine precision.

**State Vector Management for Charge Storage:**
```
CKTstate0[inst->BSIM4v5states[3]] = qgs (current time step)
CKTstate1[inst->BSIM4v5states[3]] = qgs (previous time step)
CKTstate2[inst->BSIM4v5states[3]] = qgs (two steps back)
```
Three-state storage enables Gear's method (BDF2) for LTE calculation.

### Voltage Limiting for Newton-Raphson Stability

**FET Voltage Limiting (`DEVfetlim`):**
```
vgs_limited = DEVfetlim(vgs_old, vgs_new, model->BSIM4v5type × Vth)
```
This function ensures C¹ continuity and prevents Newton-Raphson oscillations by smoothly limiting voltage changes between iterations.

**VDS Limiting for Numerical Robustness:**
```
vds_limited = limvds(vds_old, vds_new)
```
Prevents negative conductance regions that can cause convergence failure.

### Source-Drain Swap Logic for PMOS/NMOS Symmetry

**Automatic Terminal Swapping:**
```
if (vds < 0) {
    swap(&inst->BSIM4v5dNodePrime, &inst->BSIM4v5sNodePrime);
    swap(&inst->BSIM4v5rd, &inst->BSIM4v5rs);
    vds = -vds;
    mode = -1;  /* Inverted mode flag */
}
```
This ensures numerical robustness for PMOS devices or when `Vds` becomes negative during Newton iterations.

### Matrix Stamping for Convergence Acceleration

**Complete 6×6 Matrix Stamp with Internal Nodes:**
```
[Gdd  0    0    0    -Gdd   0    ] [Vd]   [Id]
[0    Ggg  0    0    0      0    ] [Vg]   [Ig]
[0    0    Gss  0    0      -Gss ] [Vs] = [Is]
[0    0    0    Gbb  0      0    ] [Vb]   [Ib]
[-Gdd 0    0    0    Gdd+Gd -Gd  ] [Vd']  [0]
[0    0    -Gss 0    -Gs    Gss+Gs] [Vs']  [0]
```
Where:
- `Gd = 1/RD`, `Gs = 1/RS` (parasitic resistances)
- `Vd'`, `Vs'` are internal node voltages
- Last two rows enforce KVL: `Vd - Vd' = Id × RD`, `Vs' - Vs = Is × RS`

This extended matrix formulation improves convergence by explicitly modeling parasitic voltage drops.

### Noise Analysis Convergence Considerations

**Thermal Noise Models with Convergence-Friendly Formulations:**
```
Model 0 (SPICE2): S_id = 4kT × (2/3) × gm
Model 1 (BSIM3): S_id = 4kT × (gm + gds + gmbs) × γ
Model 2 (BSIM4): S_id = 4kT × (Id / Vdseff) × [1 + (Vdseff / (Esat × Leff))^2]
```
Each model provides different trade-offs between physical accuracy and numerical stability during noise analysis.

**Flicker Noise with Smooth Transitions:**
```
Model 2 (BSIM4 default): S_id = (NOIA × Id + NOIB × Id^2 + NOIC × Id^3) / (f^EF × Cox × Leff^2)
```
The polynomial formulation ensures smooth derivatives for Newton-Raphson convergence during .NOISE analysis.

### Time-Step Control Algorithm

**Adaptive Time-Step Selection:**
```
if (LTE > TOL) {
    h_new = 0.5 × h_old;  /* Reduce time step */
} else if (LTE < TOL/10) {
    h_new = 1.2 × h_old;  /* Increase time step */
} else {
    h_new = h_old;        /* Keep current step */
}

/* Limit step changes to factor of 8 */
h_new = MAX(h_old/8, MIN(h_old×8, h_new));
```
This algorithm, implemented in `b4v5trunc.c`, balances simulation speed against accuracy requirements.

### Initial Condition Handling

**DC Operating Point Calculation:**
```
if (inst->BSIM4v5icVGSgiven) {
    vgs = inst->BSIM4v5icVGS;
} else {
    vgs = Vth;  /* Start at threshold for convergence */
}
```
Proper initial conditions in `b4v5getic.c` prevent convergence failures at `t=0`.

## C Implementation

### Core Data Structures for Transient Analysis

The BSIM4v5 implementation uses specialized data structures defined in `bsim4v5def.h` to manage transient state and charge conservation.

#### Model Structure (`sBSIM4v5model`)

```c
typedef struct sBSIM4v5model {
    int BSIM4v5type;                  /* NCH or PCH (1 = NMOS, -1 = PMOS) */
    
    /* Transient-relevant parameters */
    double BSIM4v5toxe;               /* Electrical oxide thickness [m] */
    double BSIM4v5u0;                 /* Low-field mobility [cm²/V·s] */
    double BSIM4v5vth0;               /* Zero-bias threshold voltage [V] */
    double BSIM4v5nfactor;            /* Subthreshold swing coefficient */
    double BSIM4v5vsat;               /* Saturation velocity [m/s] */
    
    /* Layout-dependent effects */
    double BSIM4v5sa;                 /* STI stress length parameter */
    double BSIM4v5sb;                 /* STI stress width parameter */
    double BSIM4v5sd;                 /* STI stress distance parameter */
    double BSIM4v5wpe;                /* Well proximity effect coefficient */
    
    /* Linked list pointers */
    struct sBSIM4v5model *BSIM4v5nextModel;
    sBSIM4v5instance *BSIM4v5instances;
} BSIM4v5model;
```

#### Instance Structure (`sBSIM4v5instance`)

```c
typedef struct sBSIM4v5instance {
    /* Terminal nodes */
    int BSIM4v5dNode;                 /* Drain external node */
    int BSIM4v5gNode;                 /* Gate external node */
    int BSIM4v5sNode;                 /* Source external node */
    int BSIM4v5bNode;                 /* Bulk external node */
    int BSIM4v5dNodePrime;            /* Internal drain node */
    int BSIM4v5sNodePrime;            /* Internal source node */
    
    /* Geometry parameters */
    double BSIM4v5l;                  /* Drawn channel length [m] */
    double BSIM4v5w;                  /* Drawn channel width [m] */
    double BSIM4v5leff;               /* Effective channel length */
    double BSIM4v5weff;               /* Effective channel width */
    
    /* Bias voltages */
    double BSIM4v5vgs;                /* Gate-source voltage */
    double BSIM4v5vds;                /* Drain-source voltage */
    double BSIM4v5vbs;                /* Bulk-source voltage */
    
    /* Terminal charges (STATE VARIABLES) */
    double BSIM4v5qgs;                /* Gate-source charge [C] */
    double BSIM4v5qgd;                /* Gate-drain charge [C] */
    double BSIM4v5qgb;                /* Gate-bulk charge [C] */
    
    /* STATE VECTOR ALLOCATION - Critical for charge conservation */
    int BSIM4v5states[7];             /* State indices in CKTstate array:
                                         0: vgs
                                         1: vds
                                         2: vbs
                                         3: qgs  (charge state 1)
                                         4: qgd  (charge state 2)
                                         5: qgb  (charge state 3)
                                         6: temperature */
    
    /* Small-signal parameters */
    double BSIM4v5gm;                 /* Transconductance ∂Id/∂Vgs [S] */
    double BSIM4v5gds;                /* Output conductance ∂Id/∂Vds [S] */
    double BSIM4v5gmbs;               /* Bulk transconductance ∂Id/∂Vbs [S] */
    double BSIM4v5cgs;                /* Gate-source capacitance [F] */
    double BSIM4v5cgd;                /* Gate-drain capacitance [F] */
    double BSIM4v5cgb;                /* Gate-bulk capacitance [F] */
    
    /* Current components */
    double BSIM4v5id;                 /* Drain current [A] */
    double BSIM4v5ig;                 /* Gate current [A] */
    
    /* SPARSE MATRIX POINTERS for transient stamping */
    double *BSIM4v5drainDrainPtr;     /* Gdd = ∂Id/∂Vd */
    double *BSIM4v5gateGatePtr;       /* Ggg = ∂Ig/∂Vg */
    double *BSIM4v5sourceSourcePtr;   /* Gss = ∂Is/∂Vs */
    double *BSIM4v5bulkBulkPtr;       /* Gbb = ∂Ib/∂Vb */
    /* ... 12 more cross-term pointers ... */
    
    /* Additional pointers for internal nodes */
    double *BSIM4v5drainPrimeDrainPrimePtr;
    double *BSIM4v5sourcePrimeSourcePrimePtr;
    
    struct sBSIM4v5instance *BSIM4v5nextInstance;
    BSIM4v5model *BSIM4v5modPtr;
} BSIM4v5instance;
```

### State Vector Management (`b4v5set.c`)

The setup function allocates state vector entries for charge conservation:

```c
int BSIM4v5setup(SMPmatrix *matrix, GENmodel *genmodel, CKTcircuit *ckt, int *states)
{
    BSIM4v5model *model = (BSIM4v5model *)genmodel;
    BSIM4v5instance *inst;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (inst = model->BSIM4v5instances; inst != NULL; 
             inst = inst->BSIM4v5nextInstance) {
            
            /* Allocate state vector entries for charge conservation */
            inst->BSIM4v5states[0] = *states; (*states)++;  /* vgs state */
            inst->BSIM4v5states[1] = *states; (*states)++;  /* vds state */
            inst->BSIM4v5states[2] = *states; (*states)++;  /* vbs state */
            inst->BSIM4v5states[3] = *states; (*states)++;  /* qgs state */
            inst->BSIM4v5states[4] = *states; (*states)++;  /* qgd state */
            inst->BSIM4v5states[5] = *states; (*states)++;  /* qgb state */
            inst->BSIM4v5states[6] = *states; (*states)++;  /* temperature state */
            
            /* Initialize charge states to zero */
            if (ckt->CKTstate0) {
                *(ckt->CKTstate0 + inst->BSIM4v5states[3]) = 0.0;  /* qgs */
                *(ckt->CKTstate0 + inst->BSIM4v5states[4]) = 0.0;  /* qgd */
                *(ckt->CKTstate0 + inst->BSIM4v5states[5]) = 0.0;  /* qgb */
            }
            
            /* Allocate matrix pointers for 6×6 stamp (with internal nodes) */
            int d = inst->BSIM4v5dNode;
            int g = inst->BSIM4v5gNode;
            int s = inst->BSIM4v5sNode;
            int b = inst->BSIM4v5bNode;
            int dp = inst->BSIM4v5dNodePrime;
            int sp = inst->BSIM4v5sNodePrime;
            
            inst->BSIM4v5drainDrainPtr = SMPmakeElt(matrix, d, d);
            inst->BSIM4v5gateGatePtr = SMPmakeElt(matrix, g, g);
            inst->BSIM4v5sourceSourcePtr = SMPmakeElt(matrix, s, s);
            inst->BSIM4v5bulkBulkPtr = SMPmakeElt(matrix, b, b);
            inst->BSIM4v5drainPrimeDrainPrimePtr = SMPmakeElt(matrix, dp, dp);
            inst->BSIM4v5sourcePrimeSourcePrimePtr = SMPmakeElt(matrix, sp, sp);
            
            /* Allocate cross-term pointers... */
        }
    }
    return OK;
}
```

### Local Truncation Error Calculation (`b4v5trunc.c`)

The LTE function implements charge-based error estimation for adaptive time-step control:

```c
int BSIM4v5trunc(GENmodel *genmodel, CKTcircuit *ckt, double *delta)
{
    BSIM4v5model *model = (BSIM4v5model *)genmodel;
    BSIM4v5instance *inst;
    double charge_new, charge_old, charge_pred, lte;
    double tol = ckt->CKTtrtol * (ckt->CKTreltol + ckt->CKTabstol);
    double h = *delta;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (inst = model->BSIM4v5instances; inst != NULL;
             inst = inst->BSIM4v5nextInstance) {
            
            /* Get charge states from state vector */
            double qgs_new = *(ckt->CKTstate0 + inst->BSIM4v5states[3]);
            double qgd_new = *(ckt->CKTstate0 + inst->BSIM4v5states[4]);
            double qgb_new = *(ckt->CKTstate0 + inst->BSIM4v5states[5]);
            
            double qgs_old = *(ckt->CKTstate1 + inst->BSIM4v5states[3]);
            double qgd_old = *(ckt->CKTstate1 + inst->BSIM4v5states[4]);
            double qgb_old = *(ckt->CKTstate1 + inst->BSIM4v5states[5]);
            
            /* Total gate charge */
            charge_new = qgs_new + qgd_new + qgb_new;
            charge_old = qgs_old + qgd_old + qgb_old;
            
            /* Linear prediction: q_pred = 2q_n - q_{n-1} */
            charge_pred = 2.0 * charge_new - charge_old;
            
            /* Actual charge from device evaluation */
            double charge_actual = inst->BSIM4v5qgs + inst->BSIM4v5qgd + inst->BSIM4v5qgb;
            
            /* LTE calculation: |q_actual - q_pred| */
            lte = fabs(charge_actual - charge_pred);
            
            /* Normalize by charge magnitude */
            double charge_norm = MAX(fabs(charge_new), fabs(charge_old));
            double normalized_lte = lte / (ckt->CKTreltol * charge_norm + ckt->CKTabstol);
            
            /* Adjust time step based on LTE */
            if (normalized_lte > tol) {
                /* Reduce time step - LTE too large */
                double factor = sqrt(tol / normalized_lte);  /* 2nd order method */
                *delta = MAX(h * factor, h * 0.125);  /* Limit reduction to 1/8 */
            } else if (normalized_lte < tol / 10.0) {
                /* Increase time step - LTE too small */
                double factor = sqrt(tol / normalized_lte);
                *delta = MIN(h * factor, h * 8.0);  /* Limit increase to 8x */
            }
        }
    }
    return OK;
}
```

### Convergence Testing (`b4v5cvtest.c`)

The convergence test implements multiple criteria for Newton-Raphson iteration control:

```c
int BSIM4v5convTest(GENmodel *genmodel, CKTcircuit *ckt)
{
    BSIM4v5model *model = (BSIM4v5model *)genmodel;
    BSIM4v5instance *inst;
    double vgs_new, vds_new, vbs_new;
    double vgs_old, vds_old, vbs_old;
    double delv, deli, delq;
    double reltol = ckt->CKTreltol;
    double abstol = ckt->CKTabstol;
    double vntol = ckt->CKTvoltTol;
    double chgtol = ckt->CKTchargeTol;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (inst = model->BSIM4v5instances; inst != NULL;
             inst = inst->BSIM4v5nextInstance) {
            
            /* Get new voltages from solution vector */
            vgs_new = ckt->CKTrhs[inst->BSIM4v5gNode] - 
                      ckt->CKTrhs[inst->BSIM4v5sNode];
            vds_new = ckt->CKTrhs[inst->BSIM4v5dNode] - 
                      ckt->CKTrhs[inst->BSIM4v5sNode];
            vbs_new = ckt->CKTrhs[inst->BSIM4v5bNode] - 
                      ckt->CKTrhs[inst->BSIM4v5sNode];
            
            /* Get old voltages from instance storage */
            vgs_old = inst->BSIM4v5vgs;
            vds_old = inst->BSIM4v5vds;
            vbs_old = inst->BSIM4v5vbs;
            
            /* VOLTAGE CONVERGENCE TESTS */
            
            /* Vgs convergence: |ΔVgs| < reltol*max(|Vgs|) + vntol */
            delv = fabs(vgs_new - vgs_old);
            double vgs_norm = MAX(fabs(vgs_new), fabs(vgs_old));
            if (delv > reltol * vgs_norm + vntol) {
                ckt->CKTnoncon++;
                return NOT_CONVERGED;
            }
            
            /* Vds convergence */
            delv = fabs(vds_new - vds_old);
            double vds_norm = MAX(fabs(vds_new), fabs(vds_old));
            if (delv > reltol * vds_norm + vntol) {
                ckt->CKTnoncon++;
                return NOT_CONVERGED;
            }
            
            /* Vbs convergence */
            delv = fabs(vbs_new - vbs_old);
            double vbs_norm = MAX(fabs(vbs_new), fabs(vbs_old));
            if (delv > reltol * vbs_norm + vntol) {
                ckt->CKTnoncon++;
                return NOT_CONVERGED;
            }
            
            /* CHARGE CONVERGENCE TESTS */
            
            /* Get charge states from state vector */
            double qgs_new = *(ckt->CKTstate0 + inst->BSIM4v5states[3]);
            double qgd_new = *(ckt->CKTstate0 + inst->BSIM4v5states[4]);
            double qgb_new = *(ckt->CKTstate0 + inst->BSIM4v5states[5]);
            
            double qgs_old = *(ckt->CKTstate1 + inst->BSIM4v5states[3]);
            double qgd_old = *(ckt->CKTstate1 + inst->BSIM4v5states[4]);
            double qgb_old = *(ckt->CKTstate1 + inst->BSIM4v5states[5]);
            
            /* Qgs convergence */
            delq = fabs(qgs_new - qgs_old);
            double qgs_norm = MAX(fabs(qgs_new), fabs(qgs_old));
            if (delq > reltol * qgs_norm + chgtol) {
                ckt->CKTnoncon++;
                return NOT_CONVERGED;
            }
            
            /* Qgd convergence */
            delq = fabs(qgd_new - qgd_old);
            double qgd_norm = MAX(fabs(qgd_new), fabs(qgd_old));
            if (delq > reltol * qgd_norm + chgtol) {
                ckt->CKTnoncon++;
                return NOT_CONVERGED;
            }
            
            /* Qgb convergence */
            delq = fabs(qgb_new - qgb_old);
            double qgb_norm = MAX(fabs(qgb_new), fabs(qgb_old));
            if (delq > reltol * qgb_norm + chgtol) {
                ckt->CKTnoncon++;
                return NOT_CONVERGED;
            }
            
            /* CURRENT CONVERGENCE TEST */
            
            /* Get currents */
            double id_new = inst->BSIM4v5id;
            double id_old = *(ckt->CKTstate1 + inst->BSIM4v5states[6]); /* stored in state */
            
            deli = fabs(id_new - id_old);
            double id_norm = MAX(fabs(id_new), fabs(id_old));
            if (deli > reltol * id_norm + abstol) {
                ckt->CKTnoncon++;
                return NOT_CONVERGED;
            }
            
            /* Update stored values for next iteration */
            inst->BSIM4v5vgs = vgs_new;
            inst->BSIM4v5vds = vds_new;
            inst->BSIM4v5vbs = vbs_new;
            
            /* Store current in state vector for next convergence test */
            *(ckt->CKTstate0 + inst->BSIM4v5states[6]) = id_new;
        }
    }
    
    /* All convergence tests passed */
    return OK;
}
```

### Numerical Integration for Charge Conservation (`b4v5ld.c`)

The load function implements numerical integration for capacitive currents:

```c
int BSIM4v5load(GENmodel *genmodel, CKTcircuit *ckt)
{
    BSIM4v5model *model = (BSIM4v5model *)genmodel;
    BSIM4v5instance *inst;
    double delta = ckt->CKTdelta;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (inst = model->BSIM4v5instances; inst != NULL;
             inst = inst->BSIM4v5nextInstance) {
            
            /* Get charge states from state vector */
            double qgs = *(ckt->CKTstate0 + inst->BSIM4v5states[3]);
            double qgd = *(ckt->CKTstate0 + inst->BSIM4v5states[4]);
            double qgb = *(ckt->CKTstate0 + inst->BSIM4v5states[5]);
            
            double qgs_old = *(ckt->CKTstate1 + inst->BSIM4v5states[3]);
            double qgd_old = *(ckt->CKTstate1 + inst->BSIM4v5states[4]);
            double qgb_old = *(ckt->CKTstate1 + inst->BSIM4v5states[5]);
            
            /* NUMERICAL INTEGRATION FOR CAPACITIVE CURRENTS */
            
            if (delta > 0.0) {
                /* Trapezoidal rule: i_cap(t_n) = (2/Δt)[Q(t_n) - Q(t_{n-1})] - i_cap(t_{n-1}) */
                double igs = (2.0/delta) * (qgs - qgs_old) - inst->BSIM4v5igs_old;
                double igd = (2.0/delta) * (qgd - qgd_old) - inst->BSIM4v5igd_old;
                double igb = (2.0/delta) * (qgb - qgb_old) - inst->BSIM4v5igb_old;
                
                /* Store for next iteration */
                inst->BSIM4v5igs_old = igs;
                inst->BSIM4v5igd_old = igd;
                inst->BSIM4v5igb_old = igb;
                
                /* Total gate current */
                inst->BSIM4v5ig = igs + igd + igb;
                
                /* Stamp capacitive terms into matrix */
                double cap_factor = 2.0 / delta;
                *(inst->BSIM4v5gateGatePtr) += cap_factor * (inst->BSIM4v5cgs + 
                                                             inst->BSIM4v5cgd + 
                                                             inst->BSIM4v5cgb);
                *(inst->BSIM4v5gateDrainPtr) -= cap_factor * inst->BSIM4v5cgd;
                *(inst->BSIM4v5gateSourcePtr) -= cap_factor * inst->BSIM4v5cgs;
                *(inst->BSIM4v5gateBulkPtr) -= cap_factor * inst->BSIM4v5cgb;
                
                /* Add capacitive currents to RHS */
                ckt->CKTrhs[inst->BSIM4v5gNode] -= inst->BSIM4v5ig;
                ckt->CKTrhs[inst->BSIM4v5dNode] += igd;
                ckt->CKTrhs[inst->BSIM4v5sNode] += igs;
                ckt->CKTrhs[inst->BSIM4v5bNode] += igb;
            }
            
            /* Compute and stamp conductances from drain current */
            double gm, gds, gmbs;
            computeConductances(inst, &gm, &gds, &gmbs);
            
            /* Stamp conductance matrix */
            *(inst->BSIM4v5drainDrainPtr) += gds;
            *(inst->BSIM4v5sourceSourcePtr) += gds + gm + gmbs;
            *(inst->BSIM4v5bulkBulkPtr) += gmbs;
            *(inst->BSIM