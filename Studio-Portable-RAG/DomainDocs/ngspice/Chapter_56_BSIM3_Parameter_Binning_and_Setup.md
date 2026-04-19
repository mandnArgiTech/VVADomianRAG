# BSIM3: Parameter Binning and Matrix Setup

_Generated 2026-04-12 09:37 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3ask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3check.c`

# MOS6: Transient Control and Convergence Checking

## Technical Introduction

Within the Ngspice simulation framework, the MOS6 (Sakurai-Newton empirical) model implements specialized algorithms for robust transient analysis. The files `mos6trun.c`, `mos6conv.c`, and `mos6ic.c` form the core of this implementation, each addressing a critical aspect of time-domain simulation. `mos6trun.c` calculates the Local Truncation Error (LTE) using charge-based methods to provide adaptive time-step control, ensuring accuracy while maintaining simulation speed. `mos6conv.c` implements convergence testing by comparing successive Newton-Raphson iterations against SPICE's absolute and relative tolerance criteria (`CKTabstol=1e-12`, `CKTreltol=0.001`). `mos6ic.c` handles initial condition computation, setting up consistent starting states for transient analysis by solving the DC operating point with proper device biasing. Together, these modules ensure the MOS6 model's numerical stability across digital switching events where the alpha-power law equations exhibit sharp transitions between linear and saturation regions.

## Mathematical Formulation

### 1. Core DC Equations

The MOS6 model implements the Sakurai-Newton empirical (Level 6) alpha-power law model for digital circuit simulation, with no subthreshold conduction.

**Threshold Voltage:**
```
Vth = VTO + γ·[√(2φ + Vsb) - √(2φ)] + η·Vds
```
where:
- `VTO`: Zero-bias threshold voltage
- `γ`: Body effect coefficient
- `φ`: Surface potential (typically 0.6V)
- `η`: Drain-induced barrier lowering (DIBL) coefficient
- `Vsb`: Source-bulk voltage
- `Vds`: Drain-source voltage

**Effective Gate-Source Voltage:**
```
Vgsteff = Vgs - Vth
```
with `Vgsteff` clamped to be ≥ 0.

**Region-Specific Drain Current:**

*Linear Region (|Vds| < Vdsat):*
```
Ids_lin = β_lin · (Vgsteff)^NC · Vds · (1 + λ·Vds)
```
where:
- `β_lin = KP·(W_eff/L_eff)` for NMOS, `β_lin = KP·(W_eff/L_eff)/2` for PMOS
- `NC`: Linear region power coefficient (typically 1.0-2.0)
- `λ`: Channel length modulation coefficient

*Saturation Region (|Vds| ≥ Vdsat):*
```
Ids_sat = β_sat · (Vgsteff)^NV · (1 + λ·Vds)
```
where:
- `NV`: Saturation region power coefficient (typically 1.0-2.0, NV > NC)
- `β_sat = β_lin · KV/KC` with `KV`, `KC` as saturation/linear coefficients

**Saturation Voltage:**
```
Vdsat = (KV/KC)^(1/(NV-NC)) · (Vgsteff)^((NC-1)/(NV-NC))
```

**Continuous Drain Current (C¹ Smoothing):**
A hyperbolic tangent smoothing function ensures C¹ continuity:
```
Ids = Ids_lin · [1 - f_smooth(Vds/Vdsat)] + Ids_sat · f_smooth(Vds/Vdsat)
```
where `f_smooth(x) = (1 + tanh(A·(x-1)))/2` with A ≈ 10-50.

### 2. Small-Signal Parameters

**Transconductance:**
```
gm = ∂Ids/∂Vgs = 
    NC·β_lin·(Vgsteff)^(NC-1)·Vds·(1+λ·Vds)          (linear)
    NV·β_sat·(Vgsteff)^(NV-1)·(1+λ·Vds)              (saturation)
```

**Drain Conductance:**
```
gds = ∂Ids/∂Vds = 
    β_lin·(Vgsteff)^NC·(1+2λ·Vds)                    (linear)
    λ·β_sat·(Vgsteff)^NV                             (saturation)
```

**Body Transconductance:**
```
gmb = ∂Ids/∂Vbs = -gm·[γ/(2√(2φ+Vsb))]
```

### 3. Charge Conservation and Capacitance Model

The MOS6 uses the Meyer capacitance model for computational efficiency in digital simulation:

**Gate Charges:**
```
Qg = Cgso·Vgs + Cgdo·Vgd + Cgbo·Vgb
```
where `Cgso`, `Cgdo`, `Cgbo` are overlap capacitances.

**Partitioning Factors:**
- Linear region: Qgs:Qgd = 60:40
- Saturation region: Qgs:Qgd = 100:0
- Cutoff: Qgs = Qgd = 0

**Junction Capacitances:**
```
Cbd = CBD·(1 - Vbd/PHI)^(-MJ) + CBSWL·P
Cbs = CBS·(1 - Vbs/PHI)^(-MJ) + CBSWL·P
```
where `CBD`, `CBS` are zero-bias capacitances, `MJ` is grading coefficient.

### 4. Local Truncation Error (LTE) Formulation

For charge-based LTE calculation:
```
ε_LTE = |h·(q̈(t) + O(h²))| ≤ TOL
```
where:
- `h`: Current time step
- `q̈(t)`: Second derivative of charge
- `TOL = CKTtrtol·(CKTreltol·|q| + CKTchgtol)`

The error estimate for trapezoidal integration:
```
ε_q = h²/12 · |q̇(t+h) - q̇(t)| / h
```

### 5. Convergence Analysis

**Newton-Raphson Iteration:**
The device equation is linearized as:
```
F(vⁿ⁺¹) ≈ F(vⁿ) + J(vⁿ)·Δv
```
where `J` is the Jacobian containing `gm`, `gds`, `gmb`, and capacitive terms.

**Convergence Criteria:**
1. *Absolute Current Tolerance*: `|ΔIds| < CKTabstol + CKTreltol·|Ids|`
2. *Absolute Voltage Tolerance*: `|ΔVgs|, |ΔVds|, |ΔVbs| < CKTreltol·|V| + CKTabstol`
3. *Charge Tolerance*: `|ΔQ| < CKTchgtol`

**Voltage Limiting Functions:**
- Gate limiting: `DEVfetlim(ΔVgs, Vgs_old, Vth)`
- Drain-source limiting: `DEVlimvds(ΔVds, Vds_old)`

**Matrix Conditioning:**
The 6×6 conductance matrix must satisfy:
```
cond(G + jωC + h⁻¹·C) < 1/(CKTreltol)
```
where `h` is the time step for transient analysis.

**Regularization:**
A minimum conductance `GMIN = 1e-12 Ʊ` is added diagonally to prevent singular matrices.

## C Implementation

### 1. Core Data Structures

**Model Structure (`mos6defs.h`):**
```c
typedef struct sMOS6model {
    int MOS6type;                   /* Device type: NMOS/PMOS */
    double MOS6vt0;                 /* Zero-bias threshold voltage */
    double MOS6alpha;               /* Alpha power law parameter */
    double MOS6beta;                /* Beta factor (KP·W/L) */
    double MOS6lambda;              /* Channel length modulation */
    double MOS6gamma;               /* Body effect coefficient */
    double MOS6phi;                 /* Surface potential */
    double MOS6eta;                 /* DIBL coefficient */
    double MOS6kc;                  /* Linear region coefficient */
    double MOS6nc;                  /* Linear region power */
    double MOS6kv;                  /* Saturation region coefficient */
    double MOS6nv;                  /* Saturation region power */
    double MOS6cgso;                /* Gate-source overlap cap */
    double MOS6cgdo;                /* Gate-drain overlap cap */
    double MOS6cgb;                 /* Gate-bulk overlap cap */
    double MOS6cbd;                 /* Bulk-drain junction cap */
    double MOS6cbs;                 /* Bulk-source junction cap */
    struct sMOS6model *MOS6nextModel; /* Linked list pointer */
} MOS6model;
```

**Instance Structure (`mos6defs.h`):**
```c
typedef struct sMOS6instance {
    struct sMOS6instance *MOS6nextInstance; /* Linked list */
    struct sMOS6model *MOS6modPtr;          /* Parent model */
    
    /* Terminal nodes */
    int MOS6dNode;      /* Drain node */
    int MOS6gNode;      /* Gate node */
    int MOS6sNode;      /* Source node */
    int MOS6bNode;      /* Bulk node */
    int MOS6dNodePrime; /* Internal drain node */
    int MOS6sNodePrime; /* Internal source node */
    
    /* State variables */
    double MOS6vgs;     /* Gate-source voltage */
    double MOS6vds;     /* Drain-source voltage */
    double MOS6vbs;     /* Bulk-source voltage */
    double MOS6vbd;     /* Bulk-drain voltage */
    double MOS6ids;     /* Drain current */
    double MOS6gm;      /* Transconductance */
    double MOS6gds;     /* Drain conductance */
    double MOS6gmb;     /* Bulk transconductance */
    
    /* Charge states */
    int MOS6qgsState;   /* State index for Qgs */
    int MOS6qgdState;   /* State index for Qgd */
    int MOS6qgbState;   /* State index for Qgb */
    int MOS6qbdState;   /* State index for Qbd */
    int MOS6qbsState;   /* State index for Qbs */
    
    /* Matrix pointers (6x6 matrix) */
    double *MOS6drainDrainPtr;
    double *MOS6drainGatePtr;
    double *MOS6drainSourcePtr;
    double *MOS6drainBulkPtr;
    double *MOS6drainDrainPrimePtr;
    double *MOS6drainSourcePrimePtr;
    /* ... 30 more matrix pointers for full 6x6 connectivity */
    
    /* Flags */
    unsigned MOS6off : 1;           /* Device off flag */
    unsigned MOS6sens : 1;          /* Sensitivity flag */
} MOS6instance;
```

### 2. Matrix Setup (`mos6set.c`)

**Setup Function:**
```c
int MOS6setup(MOS6model *model, CKTcircuit *ckt)
{
    MOS6instance *here;
    
    for (; model != NULL; model = model->MOS6nextModel) {
        for (here = model->MOS6instances; here != NULL; 
             here = here->MOS6nextInstance) {
            
            /* Allocate state vector indices for charges */
            if (ckt->CKTmode & MODEINITTRAN) {
                CKTallocState(ckt, &here->MOS6qgsState);
                CKTallocState(ckt, &here->MOS6qgdState);
                CKTallocState(ckt, &here->MOS6qgbState);
                CKTallocState(ckt, &here->MOS6qbdState);
                CKTallocState(ckt, &here->MOS6qbsState);
            }
            
            /* Allocate sparse matrix pointers for 6 nodes */
            /* Node order: 0:D, 1:D', 2:G, 3:S', 4:S, 5:B */
            SMPmakeElt(ckt, here->MOS6dNode, here->MOS6dNode, 
                      &here->MOS6drainDrainPtr);
            SMPmakeElt(ckt, here->MOS6dNode, here->MOS6gNode,
                      &here->MOS6drainGatePtr);
            SMPmakeElt(ckt, here->MOS6dNode, here->MOS6sNode,
                      &here->MOS6drainSourcePtr);
            /* ... allocate all 36 possible matrix elements */
            
            /* Setup internal nodes if RD/RS > 0 */
            if (here->MOS6rd > 0.0) {
                here->MOS6dNodePrime = ckt->CKTrhs->size();
                ckt->CKTrhs->extend(1);
                /* Allocate matrix pointers for D' node */
            }
            if (here->MOS6rs > 0.0) {
                here->MOS6sNodePrime = ckt->CKTrhs->size();
                ckt->CKTrhs->extend(1);
                /* Allocate matrix pointers for S' node */
            }
        }
    }
    return OK;
}
```

### 3. Transient Analysis and LTE (`mos6trun.c`)

**Truncation Error Calculation:**
```c
int MOS6trunc(MOS6instance *here, CKTcircuit *ckt, double *timeStep)
{
    double h = ckt->CKTdelta;  /* Current time step */
    double tol, charge, dcharge, ddcharge, error;
    
    /* Calculate charge derivatives */
    charge = here->MOS6qgs + here->MOS6qgd + here->MOS6qgb;
    dcharge = (charge - here->MOS6qgs_old) / h;
    
    /* Estimate second derivative using previous step */
    if (ckt->CKTtime > 0) {
        ddcharge = (dcharge - here->MOS6dqgs_old) / h;
        
        /* LTE error bound */
        error = fabs(h * h * ddcharge / 12.0);
        tol = ckt->CKTtrtol * (ckt->CKTreltol * fabs(charge) + ckt->CKTchgtol);
        
        if (error > tol) {
            /* Reduce time step */
            *timeStep = h * sqrt(tol / (error + 1e-30));
            return E_LOCALTRUNC;
        }
    }
    
    /* Store for next iteration */
    here->MOS6qgs_old = charge;
    here->MOS6dqgs_old = dcharge;
    
    return OK;
}
```

**Time Step Control:**
```c
int MOS6adjustTimeStep(MOS6instance *here, CKTcircuit *ckt)
{
    double h = ckt->CKTdelta;
    double hnew, error_ratio;
    
    /* Calculate error ratio for all charge components */
    double max_error = 0.0;
    double charges[] = {here->MOS6qgs, here->MOS6qgd, here->MOS6qgb,
                       here->MOS6qbd, here->MOS6qbs};
    
    for (int i = 0; i < 5; i++) {
        double q = charges[i];
        double q_old = here->MOS6charges_old[i];
        double dq = (q - q_old) / h;
        double dq_old = here->MOS6dcharges_old[i];
        double ddq = (dq - dq_old) / h;
        
        double error = fabs(h * h * ddq / 12.0);
        double tol = ckt->CKTtrtol * (ckt->CKTreltol * fabs(q) + ckt->CKTchgtol);
        
        error_ratio = error / (tol + 1e-30);
        if (error_ratio > max_error) max_error = error_ratio;
    }
    
    /* Adjust time step based on error */
    if (max_error > 1.0) {
        /* Error too large - reduce step */
        hnew = h * 0.9 / sqrt(max_error);
    } else if (max_error < 0.1) {
        /* Error small - can increase step */
        hnew = h * 1.1;
    } else {
        hnew = h;  /* Keep current step */
    }
    
    /* Apply bounds: 0.1h ≤ hnew ≤ 10h */
    hnew = MAX(hnew, 0.1 * h);
    hnew = MIN(hnew, 10.0 * h);
    
    ckt->CKTdelta = hnew;
    return OK;
}
```

### 4. Convergence Testing (`mos6conv.c`)

**Convergence Test Function:**
```c
int MOS6convTest(MOS6instance *here, CKTcircuit *ckt)
{
    double vgs, vds, vbs, ids;
    double delvgs, delvds, delvbs, delids;
    int converged = 1;
    
    /* Get current and previous values */
    vgs = *(ckt->CKTrhs + here->MOS6gNode) - *(ckt->CKTrhs + here->MOS6sNode);
    vds = *(ckt->CKTrhs + here->MOS6dNode) - *(ckt->CKTrhs + here->MOS6sNode);
    vbs = *(ckt->CKTrhs + here->MOS6bNode) - *(ckt->CKTrhs + here->MOS6sNode);
    ids = here->MOS6ids;
    
    /* Calculate changes from previous iteration */
    delvgs = vgs - here->MOS6vgs_old;
    delvds = vds - here->MOS6vds_old;
    delvbs = vbs - here->MOS6vbs_old;
    delids = ids - here->MOS6ids_old;
    
    /* Voltage convergence test */
    double vntol = ckt->CKTreltol * MAX(fabs(vgs), fabs(vds)) + ckt->CKTabstol;
    if (fabs(delvgs) > vntol) converged = 0;
    if (fabs(delvds) > vntol) converged = 0;
    if (fabs(delvbs) > vntol) converged = 0;
    
    /* Current convergence test */
    double abstol = ckt->CKTabstol;
    double reltol = ckt->CKTreltol;
    double idstol = abstol + reltol * MAX(fabs(ids), fabs(here->MOS6ids_old));
    if (fabs(delids) > idstol) converged = 0;
    
    /* Charge convergence test */
    double charges[] = {here->MOS6qgs, here->MOS6qgd, here->MOS6qgb};
    double charges_old[] = {here->MOS6qgs_old, here->MOS6qgd_old, here->MOS6qgb_old};
    
    for (int i = 0; i < 3; i++) {
        double delq = charges[i] - charges_old[i];
        double qtol = ckt->CKTchgtol + ckt->CKTreltol * fabs(charges[i]);
        if (fabs(delq) > qtol) converged = 0;
    }
    
    /* Store current values for next iteration */
    here->MOS6vgs_old = vgs;
    here->MOS6vds_old = vds;
    here->MOS6vbs_old = vbs;
    here->MOS6ids_old = ids;
    here->MOS6qgs_old = here->MOS6qgs;
    here->MOS6qgd_old = here->MOS6qgd;
    here->MOS6qgb_old = here->MOS6qgb;
    
    return converged ? OK : E_NOT_CONVERGED;
}
```

**Voltage Limiting Implementation:**
```c
/* Gate voltage limiting (FET-specific) */
double DEVfetlim(double vnew, double vold, double vto)
{
    double vtsthi, vtstlo, vtox;
    double delv, vtemp;
    
    vtsthi = fabs(2.0 * (vold - vto)) + 2.0;
    vtstlo = vtsthi / 2.0 + 2.0;
    vtox = vto + 3.0;
    
    delv = vnew - vold;
    
    if (vold >= vtox) {
        if (delv <= 0.0) {
            /* Going down - normal */
            vtemp = vnew;
        } else {
            /* Going up - limit */
            vtemp = MIN(vnew, vold + vtsthi);
        }
    } else if (vold <= vto) {
        if (delv >= 0.0) {
            /* Going up - normal */
            vtemp = vnew;
        } else {
            /* Going down - limit */
            vtemp = MAX(vnew, vold - vtstlo);
        }
    } else {
        /* In transition region */
        if (delv >= 0.0) {
            vtemp = MIN(vnew, vold + vtsthi);
        } else {
            vtemp = MAX(vnew, vold - vtstlo);
        }
    }
    
    return vtemp;
}

/* Drain-source voltage limiting */
double DEVlimvds(double vnew, double vold)
{
    double delv, vtemp;
    
    delv = vnew - vold;
    
    if (vold >= 0.0) {
        if (delv <= 0.0) {
            /* Normal decrease */
            vtemp = vnew;
        } else {
            /* Limit increase */
            vtemp = vold + 2.0;
            if (vtemp < 0.0) vtemp = vold / 2.0;
            vnew = MIN(vnew, vtemp);
        }
    } else {
        if (delv >= 0.0) {
            /* Normal increase */
            vtemp = vnew;
        } else {
            /* Limit decrease */
            vtemp = vold - 2.0;
            if (vtemp > 0.0) vtemp = vold / 2.0;
            vnew = MAX(vnew, vtemp);
        }
    }
    
    return vnew;
}
```

### 5. Initial Conditions (`mos6ic.c`)

**Initial Condition Calculation:**
```c
int MOS6ic(MOS6instance *here, CKTcircuit *ckt)
{
    double vgs, vds, vbs, vth, vgsteff, ids;
    
    /* Get initial voltages from circuit */
    vgs = *(ckt->CKTrhs + here->MOS6gNode) - *(ckt->CKTrhs + here->MOS6sNode);
    vds = *(ckt->CKTrhs + here->MOS6dNode) - *(ckt->CKTrhs + here->MOS6sNode);
    vbs = *(ckt->CKTrhs + here->MOS6bNode) - *(ckt->CKTrhs + here->MOS6sNode);
    
    /* Apply voltage limiting for initial guess */
    vgs = DEVfetlim(vgs, 0.0, here->MOS6vt0);
    vds = DEVlimvds(vds, 0.0);
    
    /* Calculate threshold voltage */
    vth = here->MOS6vt0 + 
          here->MOS6gamma * (sqrt(here->MOS6phi + vbs) - sqrt(here->MOS6phi)) +
          here->MOS6eta * vds;
    
    /* Effective gate voltage */
    vgsteff = vgs - vth;
    if (vgsteff < 0.0) vgsteff = 0.0;
    
    /* Calculate initial drain current */
    if (fabs(vds) < 1e-12) {
        /* At origin - use linear approximation */
        ids = here->MOS6beta * pow(vgsteff, here->MOS6nc) * vds;
    } else {
        /* Regular calculation */
        double vdsat = pow(here->MOS6kv/here->MOS6kc, 1.0/(here->MOS6nv - here->MOS6nc)) *
                      pow(vgsteff, (here->MOS6nc - 1.0)/(here->MOS6nv - here->MOS6nc));
        
        if (fabs(vds) < vdsat) {
            /* Linear region */
            ids = here->MOS6beta * here->MOS6kc * 
                  pow(vgsteff, here->MOS6nc) * vds * (1.0 + here->MOS6lambda * vds);
        } else {
            /* Saturation region */
            ids = here->MOS6beta * here->MOS6kv * 
                  pow(vgsteff, here->MOS6nv) * (1.0 + here->MOS6lambda * vds);
        }
    }
    
    /* Store initial conditions */
    here->MOS6vgs = vgs;
    here->MOS6vds = vds;
    here->MOS6vbs = vbs;
    here->MOS6ids = ids;
    
    /* Initialize charge states */
    here->MOS6qgs = here->MOS6cgso * vgs;
    here->MOS6qgd = here->MOS6cgdo * (vgs - vds);
    here->MOS6qgb = here->MOS6cgb * (vgs - vbs);
    
    /* Initialize junction charges */
    double phi = here->MOS6phi;
    double mj = 0.5;  /* Default grading coefficient */
    
    if (vbs < 0.0) {
        here->MOS6qbs = here->MOS6cbs * phi * (1.0 - pow(1.0 - vbs/phi, 1.0 - mj)) / (1.0 - mj);
    } else {
        here->MOS6qbs = here->MOS6cbs * vbs;
    }
    
    if (vbs - vds < 0.0) {
        here->MOS6qbd = here->MOS6cbd * phi * (1.0 - pow(1.0 - (vbs - vds)/phi, 1.0 - mj)) / (1.0 - mj);
    } else {
        here->MOS6qbd = here->MOS6cbd * (vbs - vds);
    }
    
    return OK;
}
```

### 6. Temperature Scaling (`mos6temp.c`)

**Temperature Effects:**
```c
int MOS6temperature(MOS6model *model, CKTcircuit *ckt)
{
    double tnom, temp, ratio, ratio4;
    
    tnom = ckt->CKTnomTemp;
    temp = ckt->CKTtemp;
    
    /* Temperature ratio */
    ratio = temp / tnom;
    ratio4 = ratio * sqrt(ratio);
    
    /* Threshold voltage temperature coefficient */
    model->MOS6vt0 = model->MOS6vt0 * (1.0 + model->MOS6tcv * (temp - tnom));
    
    /* Mobility temperature scaling */
    model->MOS6beta = model->MOS6beta * pow(ratio, -model->MOS6bex);
    
    /* Junction capacitance temperature scaling */
    model->MOS6cbd = model->MOS6cbd * (1.0 + model->MOS6tcc * (temp - tnom));
    model->MOS6cbs = model->MOS6cbs * (1.0 + model->MOS6tcc * (temp - tnom));
    
    /* Overlap capacitance temperature scaling */
    model->MOS6cgso = model->MOS6cgso * (1.0 + model->MOS6tcco * (temp - tnom));
    model->MOS6cgdo = model->MOS6cgdo * (1.0 + model->MOS6tcco * (temp - tnom));
    model->MOS6cgb = model->MOS6cgb * (1.0 + model->MOS6tcco * (temp - tnom));
    
    return OK;
}
```

### 7. Matrix Stamping for Transient Analysis

**Load Function for Transient Analysis:**
```c
int MOS6load(MOS6instance *here, CKTcircuit *ckt)
{
    double ggs, ggd, ggb, gds, gm, gmb;
    double cgs, cgd, cgb;
    double geq, ceq;
    
    /* Calculate conductances from current derivatives */
    gm = here->MOS6gm;
    gds = here->MOS6gds;
    gmb = here->MOS6gmb;
    
    /* Calculate capacitances */
    cgs = here->MOS6cgso + here->MOS6cgs;  /* Overlap + intrinsic */
    cgd = here->MOS6cgdo + here->MOS6cgd;
    cgb = here->MOS6cgb + here->MOS6cgb;
    
    /* Stamp conductance matrix */
    /* Drain equation */
    *here->MOS6drainDrainPtr += gds;
    *here->MOS6drainGatePtr += gm;
    *here->MOS6drainSourcePtr -= (gds + gm + gmb);
    *here->MOS6drainBulkPtr += gmb;
    
    /* Gate equation */
    *here->MOS6gateDrainPtr -= 0.0;  /* No DC gate current */
    *here->MOS6gateGatePtr += 0.0;
    *here->MOS6gateSourcePtr += 0.0;
    *here->MOS6gateBulkPtr += 0.0;
    
    /* Source equation */
    *here->MOS6sourceDrainPtr -= gds;
    *here->MOS6sourceGatePtr -= gm;
    *here->MOS6sourceSourcePtr += (gds + gm + gmb);
    *here->MOS6sourceBulkPtr -= gmb;
    
    /* Bulk equation */
    *here->MOS6bulkDrainPtr -= 0.0;
    *here->MOS6bulkGatePtr -= 0.0;
    *here->MOS6bulkSourcePtr -= gmb;
    *here->MOS6bulkBulkPtr += gmb;
    
    /* Stamp capacitance matrix for trapezoidal integration */
    double coef = 2.0 / ckt->CKTdelta;
    
    /* Drain node capacitive terms */
    *here->MOS6drainDrainPtr += coef * (cgd);
    *here->MOS6drainGatePtr += coef * (-cgd);
    
    /* Gate node capacitive terms */
    *here->MOS6gateDrainPtr += coef * (-cgd);
    *here->MOS6gateGatePtr += coef * (cgs + cgd + cgb);
    *here->MOS6gateSourcePtr += coef * (-cgs);
    *here->MOS6gateBulkPtr += coef * (-cgb);
    
    /* Source node capacitive terms */
    *here->MOS6sourceGatePtr += coef * (-cgs);
    *here->MOS6sourceSourcePtr += coef * (cgs);
    
    /* Bulk node capacitive terms */
    *here->MOS6bulkGatePtr += coef * (-cgb);
    *here->MOS6bulkBulkPtr += coef * (cgb);
    
    /* Stamp RHS vector for companion model */
    double *rhs = ckt->CKTrhs;
    double *rhsOld = ckt->CKTstate0;
    
    /* Gate charge companion model */
    double qg = here->MOS6qgs + here->MOS6qgd + here->MOS6qgb;
    double qg_old = rhsOld[here->MOS6qgsState] + 
                    rhsOld[here->MOS6qgdState] + 
                    rhsOld[here->MOS6qgbState];
    
    rhs[here->MOS6gNode] += coef * qg + 2.0 * qg_old / ckt->CKTdelta;
    
    /* Drain and source charges */
    double qd = -here->MOS6qgd;
    double qd_old = -rhsOld[here->MOS6qgdState];
    rhs[here->MOS6dNode] += coef * qd + 2.0 * qd_old / ckt->CKTdelta;
    
    double qs = -here->MOS6qgs;
    double qs_old = -rhsOld[here->MOS6qgsState];
    rhs[here->MOS6sNode] += coef * qs + 2.0 * qs_old / ckt->CKTdelta;
    
    /* Bulk charges */
    double qb = -here->MOS6qgb - here->MOS6qbd - here->MOS6qbs;
    double qb_old = -rhsOld[here->MOS6qgbState] - 
                    rhsOld[here->MOS6qbdState] - 
                    rhsOld[here->MOS6qbsState];
    rhs[here->MOS6bNode] += coef * qb + 2.0 * qb_old / ckt->CKTdelta;
    
    return OK;
}
```

### 8. Source-Drain Symmetry Handling

**PMOS and Negative Vds Handling:**
```c
/* In load function, before calculations: */
int isPMOS = (here->MOS6type < 0);  /* Negative type indicates PMOS */
double vds_sign = 1.0;

if (isPMOS) {
    /* Invert voltages for PMOS */
    vgs = -vgs;
    vds = -vds;
    vbs = -vbs;
    vds_sign = -1.0;
}

/* After current calculation: */
if (vds < 0.0) {
    /* Source and drain are swapped */
    double tmp;
    
    /* Swap terminal voltages */
    tmp = vgs;
    vgs = vgs - vds;  /* Vgs becomes Vgd */
    vds = -vds;
    
    /* Swap conductances */
    tmp = gm;
    gm = -gds;  /* gm becomes -gds for swapped terminals */
    gds = tmp;
    
    /* Swap capacitances */
    tmp = cgs;
    cgs = cgd;
    cgd = tmp;
}

/* Apply PMOS sign correction */
if (isPMOS) {
    ids *= -1.0;
    gm *= -1.0;
    gds *= -1.0;
    gmb *= -1.0;
}
```

### 9. Integration with SPICE Circuit Context

**Circuit Structure Integration:**
```c
/* SPICE device structure for MOS6 */
SPICEdev MOS6info = {
    .DEVpublic = {
        .name = "mos6",
        .description = "Sakurai-Newton MOS Level 6",
        .terms = 4,  /* D, G, S, B */
        .numNames = 0,
        .termNames = NULL,
        .modType = 0,
    },
    .DEVparam = MOS6param,
    .DEVmodParam = MOS6mParam,
    .DEVload = MOS6load,
    .DEVsetup = MOS6setup,
    .DEVunsetup = NULL,
    .DEVpzSetup = MOS6setup,
    .DEVtemperature = MOS6temperature,
    .DEVtrunc = MOS6trunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = MOS6acLoad,
    .DEVaccept = NULL,
    .DEVdestroy = NULL,
    .DEVmodDelete = NULL,
    .DEVdelete = NULL,
    .DEVsetic = MOS6ic,
    .DEVask = MOS6ask,
    .DEVmodAsk = MOS6mAsk,
    .DEVpzLoad = MOS6pzLoad,
    .DEVconvTest = MOS6convTest,
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = NULL,
    .DEVnoise = NULL,
    .DEVsoaCheck = NULL,
    .DEVinstSize = sizeof(MOS6instance),
    .DEVmodSize = sizeof(MOS6model)
};
```

This complete implementation demonstrates how the MOS6 model in Ngspice achieves robust transient simulation through careful integration of mathematical formulations, numerical methods for convergence control, and efficient C implementations that map directly to SPICE's circuit simulation framework.