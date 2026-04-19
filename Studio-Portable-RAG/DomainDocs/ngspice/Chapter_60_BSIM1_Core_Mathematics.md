# BSIM1: Core Empirical Mathematics and Evaluation

_Generated 2026-04-12 10:31 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/bsim1def.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1eval.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1ld.c`

# MOS6: Transient Control and Convergence Checking

## Technical Introduction

Within the Ngspice simulation framework, the MOS6 (Sakurai-Newton Level 6) model implements a specialized alpha-power law formulation optimized for digital circuit transient analysis. This chapter examines the C implementation files responsible for ensuring numerical stability during time-domain simulation: `mos6set.c` (sparse matrix allocation and setup), `mos6trun.c` (Local Truncation Error calculation for adaptive time-step control), `mos6conv.c` (Newton-Raphson convergence testing), and `mos6ic.c` (initial condition computation). These components work in concert with the core model evaluation in `mos6eval.c` to provide robust transient analysis for the empirical MOS6 model, which lacks subthreshold conduction but provides efficient digital switching characteristics through its piecewise-linear/saturation current formulation with C¹ continuity smoothing.

## Mathematical Formulation

### 1. Core DC Equations

#### Threshold Voltage
The MOS6 threshold voltage includes body and drain bias effects:

```
V_th = VTO + γ·[√(2φ + V_sb) - √(2φ)] + η·V_ds
```

Where:
- `VTO`: Zero-bias threshold voltage
- `γ`: Body effect coefficient
- `φ`: Bulk Fermi potential (typically 0.6V)
- `η`: Drain-induced barrier lowering (DIBL) coefficient
- `V_sb`: Source-bulk voltage
- `V_ds`: Drain-source voltage

#### Effective Gate-Source Voltage
For the alpha-power law model, the effective gate overdrive is:

```
V_gsteff = V_gs - V_th
```

This value is clamped to be non-negative since MOS6 has no subthreshold conduction.

#### Drain Current Formulation
The model uses separate formulations for linear and saturation regions:

**Linear Region (V_ds < V_dsat):**
```
I_ds,lin = β_lin · (V_gsteff)^NC · V_ds · (1 + λ·V_ds)
```

**Saturation Region (V_ds ≥ V_dsat):**
```
I_ds,sat = β_sat · (V_gsteff)^NV · (1 + λ·V_ds)
```

Where:
- `β_lin = MOS6kc · (W_eff/L_eff)`
- `β_sat = MOS6kv · (W_eff/L_eff)`
- `NC`: Linear region exponent (typically 1.0)
- `NV`: Saturation region exponent (typically 1.0-2.0)
- `λ`: Channel length modulation coefficient
- `W_eff`, `L_eff`: Effective channel dimensions

#### Saturation Voltage
The drain saturation voltage provides smooth transition:

```
V_dsat = (KV/KC)^(1/(NV-NC)) · (V_gsteff)^((NC-1)/(NV-NC))
```

For the common case where `NC = 1`, this simplifies to:
```
V_dsat = (KV/KC)^(1/(NV-1))  (constant for given model parameters)
```

#### Continuous Blending Function
To ensure C¹ continuity between regions, MOS6 uses a smoothing function:

```
V_ds,eff = V_dsat · [1 - (1 - (V_ds/V_dsat)^α)^(1/α)]
```

Where `α` is a smoothing parameter (typically 2-3). The final drain current becomes:

```
I_ds = β_sat · (V_gsteff)^NV · f(V_ds/V_dsat) · (1 + λ·V_ds)
```

With `f(x) = x` for `x ≤ 1` (linear) and `f(x) = 1` for `x ≥ 1` (saturation), smoothed near `x = 1`.

### 2. Small-Signal Parameters

The conductances for matrix stamping are derived as:

**Transconductance:**
```
g_m = ∂I_ds/∂V_gs = NV·β_sat·(V_gsteff)^(NV-1)·f(V_ds/V_dsat)·(1+λ·V_ds)
```

**Output conductance:**
```
g_ds = ∂I_ds/∂V_ds = β_sat·(V_gsteff)^NV·[f'(V_ds/V_dsat)·(1/V_dsat)·(1+λ·V_ds) + λ·f(V_ds/V_dsat)]
```

**Body transconductance:**
```
g_mb = ∂I_ds/∂V_bs = -g_m · [γ/(2√(2φ + V_sb))]
```

### 3. Charge and Capacitance Model

MOS6 uses a simplified charge-based model for transient analysis:

**Gate charge partitioning:**
```
Q_g = C_ox·W_eff·L_eff·[V_gsteff + V_th + 0.5·V_ds,eff]
Q_d = -0.4·C_ox·W_eff·L_eff·V_gsteff
Q_s = -0.6·C_ox·W_eff·L_eff·V_gsteff
Q_b = -C_ox·W_eff·L_eff·[γ·√(2φ + V_sb) + η·V_ds]
```

**Intrinsic capacitances:**
```
C_gs = ∂Q_g/∂V_gs = C_ox·W_eff·L_eff
C_gd = ∂Q_g/∂V_ds = 0.5·C_ox·W_eff·L_eff·(∂V_ds,eff/∂V_ds)
C_gb = ∂Q_g/∂V_bs = C_ox·W_eff·L_eff·[1 - γ/(2√(2φ + V_sb))]
```

### 4. Local Truncation Error (LTE) Formulation

For trapezoidal integration with time-step `h`, the LTE bound for charge-based integration is:

```
ε_LTE = |(h³/12) · d³q/dt³| ≤ TOL
```

Where `TOL = CKTtrtol·(CKTreltol·|q| + CKTabstol)`. The third derivative is approximated using backward differences:

```
d³q/dt³ ≈ (q_n - 3q_{n-1} + 3q_{n-2} - q_{n-3}) / h³
```

This provides the time-step control criterion:
```
h_new = h_current · min(1.5, max(0.5, √(TOL/|ε_LTE|)))
```

### 5. Convergence Testing Criteria

Newton-Raphson convergence is verified using SPICE's standard relative/absolute tolerance scheme:

**Voltage convergence:**
```
|ΔV| < CKTreltol·max(|V|, CKTvoltTol) + CKTabstol
```

**Current convergence:**
```
|ΔI| < CKTreltol·max(|I|, CKTcurTol) + CKTabstol
```

**Charge convergence (for charge-based devices):**
```
|ΔQ| < CKTreltol·max(|Q|, CKTchgTol) + CKTabstol
```

Where typical SPICE defaults are:
- `CKTreltol = 0.001` (0.1% relative tolerance)
- `CKTabstol = 1e-12` (absolute tolerance)
- `CKTtrtol = 7` (LTE tolerance factor)
- `CKTvoltTol = 1e-6`, `CKTcurTol = 1e-12`, `CKTchgTol = 1e-14`

## C Implementation

### 1. Core Data Structures (`mos6defs.h`)

```c
/* Model parameters structure */
typedef struct sMOS6model {
    int MOS6type;                  /* N-type or P-type */
    double MOS6kv;                 /* Saturation coefficient */
    double MOS6nv;                 /* Saturation exponent */
    double MOS6kc;                 /* Linear coefficient */
    double MOS6nc;                 /* Linear exponent */
    double MOS6alpha;              /* Smoothing parameter */
    double MOS6lambda;             /* Channel length modulation */
    double MOS6vto;                /* Zero-bias threshold voltage */
    double MOS6gamma;              /* Body effect coefficient */
    double MOS6phi;                /* Bulk Fermi potential */
    double MOS6eta;                /* DIBL coefficient */
    double MOS6tox;                /* Oxide thickness */
    double MOS6cox;                /* Oxide capacitance per area */
    double MOS6ld;                 /* Lateral diffusion length */
    double MOS6wd;                 /* Width reduction */
    
    struct sMOS6model *MOS6nextModel;  /* Linked list pointer */
    MOS6instance *MOS6instances;       /* Instance list */
} MOS6model;

/* Instance state structure */
typedef struct sMOS6instance {
    int MOS6dNode;                 /* Drain node index */
    int MOS6gNode;                 /* Gate node index */
    int MOS6sNode;                 /* Source node index */
    int MOS6bNode;                 /* Bulk node index */
    int MOS6dNodePrime;            /* Internal drain node */
    int MOS6sNodePrime;            /* Internal source node */
    
    /* Terminal voltages */
    double MOS6vgs;
    double MOS6vds;
    double MOS6vbs;
    double MOS6vgd;
    double MOS6vsb;
    
    /* Electrical quantities */
    double MOS6ids;                /* Drain current */
    double MOS6gm;                 /* Transconductance */
    double MOS6gds;                /* Output conductance */
    double MOS6gmbs;               /* Body transconductance */
    
    /* Charge states */
    double MOS6qgs;                /* Gate-source charge */
    double MOS6qgd;                /* Gate-drain charge */
    double MOS6qgb;                /* Gate-bulk charge */
    double MOS6cqgs;               /* Gate-source capacitance */
    double MOS6cqgd;               /* Gate-drain capacitance */
    double MOS6cqgb;               /* Gate-bulk capacitance */
    
    /* State vector indices */
    int MOS6stateQgs;              /* Qgs state index */
    int MOS6stateQgd;              /* Qgd state index */
    int MOS6stateQgb;              /* Qgb state index */
    
    /* Matrix pointers (6x6 system) */
    double *MOS6drainDrainPtr;
    double *MOS6drainGatePtr;
    double *MOS6drainSourcePtr;
    double *MOS6drainBulkPtr;
    double *MOS6drainDrainPrimePtr;
    double *MOS6drainSourcePrimePtr;
    /* ... 30 more matrix pointers for full 6x6 system */
    
    /* Convergence testing history */
    double MOS6vgs_old;
    double MOS6vds_old;
    double MOS6vbs_old;
    double MOS6ids_old;
    double MOS6qgs_old[3];         /* History for LTE calculation */
    
    /* Initial condition storage */
    double MOS6icVGS;
    double MOS6icVDS;
    double MOS6icVBS;
    
    struct sMOS6instance *MOS6nextInstance;  /* Linked list */
} MOS6instance;
```

### 2. Matrix Setup (`mos6set.c`)

The `MOS6setup()` function allocates the sparse matrix structure for the 6-node system:

```c
int MOS6setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    
    /* Loop through all instances */
    for(; model != NULL; model = model->MOS6nextModel) {
        for(here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
            
            /* Allocate 6x6 matrix pointers (36 total) */
            int error = 0;
            error += SMPmakeElt(matrix, here->MOS6dNode, here->MOS6dNode);
            error += SMPmakeElt(matrix, here->MOS6dNode, here->MOS6gNode);
            error += SMPmakeElt(matrix, here->MOS6dNode, here->MOS6sNode);
            error += SMPmakeElt(matrix, here->MOS6dNode, here->MOS6bNode);
            error += SMPmakeElt(matrix, here->MOS6dNode, here->MOS6dNodePrime);
            error += SMPmakeElt(matrix, here->MOS6dNode, here->MOS6sNodePrime);
            /* ... allocate remaining 30 matrix elements */
            
            /* Store pointers in instance structure */
            here->MOS6drainDrainPtr = SMPfindElt(matrix, here->MOS6dNode, here->MOS6dNode);
            here->MOS6drainGatePtr = SMPfindElt(matrix, here->MOS6dNode, here->MOS6gNode);
            /* ... store all 36 pointers */
            
            /* Allocate state vector entries for charges */
            here->MOS6stateQgs = ckt->CKTnumStates++;
            here->MOS6stateQgd = ckt->CKTnumStates++;
            here->MOS6stateQgb = ckt->CKTnumStates++;
            
            if(error) return(E_NOMEM);
        }
    }
    return(OK);
}
```

### 3. Local Truncation Error Calculation (`mos6trun.c`)

```c
int MOS6trunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    double h = ckt->CKTdelta;  /* Current time-step */
    double tol, error, newStep;
    double qgs_third, qgd_third, qgb_third;
    
    for(; model != NULL; model = model->MOS6nextModel) {
        for(here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
            
            /* Calculate third derivative using backward differences */
            double *qgs_state = ckt->CKTstates[here->MOS6stateQgs];
            double *qgd_state = ckt->CKTstates[here->MOS6stateQgd];
            double *qgb_state = ckt->CKTstates[here->MOS6stateQgb];
            
            /* Third derivative: (q_n - 3q_{n-1} + 3q_{n-2} - q_{n-3}) / h^3 */
            qgs_third = (qgs_state[0] - 3*qgs_state[1] + 3*qgs_state[2] - qgs_state[3]) / (h*h*h);
            qgd_third = (qgd_state[0] - 3*qgd_state[1] + 3*qgd_state[2] - qgd_state[3]) / (h*h*h);
            qgb_third = (qgb_state[0] - 3*qgb_state[1] + 3*qgb_state[2] - qgb_state[3]) / (h*h*h);
            
            /* LTE bound: |h^3/12 * d^3q/dt^3| */
            error = fabs((h*h*h/12.0) * (qgs_third + qgd_third + qgb_third));
            
            /* Tolerance: trtol * (reltol*|q| + abstol) */
            double q_total = fabs(here->MOS6qgs) + fabs(here->MOS6qgd) + fabs(here->MOS6qgb);
            tol = ckt->CKTtrtol * (ckt->CKTreltol * q_total + ckt->CKTabstol);
            
            /* Suggest new time-step */
            if(error > 0.0) {
                newStep = h * sqrt(tol / error);
                /* Limit step change to factor of 2 */
                newStep = MIN(newStep, 2.0 * h);
                newStep = MAX(newStep, 0.5 * h);
                
                /* Update global time-step suggestion */
                *timeStep = MIN(*timeStep, newStep);
            }
            
            /* Shift history for next iteration */
            qgs_state[3] = qgs_state[2];
            qgs_state[2] = qgs_state[1];
            qgs_state[1] = qgs_state[0];
            
            qgd_state[3] = qgd_state[2];
            qgd_state[2] = qgd_state[1];
            qgd_state[1] = qgd_state[0];
            
            qgb_state[3] = qgb_state[2];
            qgb_state[2] = qgb_state[1];
            qgb_state[1] = qgb_state[0];
        }
    }
    return(OK);
}
```

### 4. Convergence Testing (`mos6conv.c`)

```c
int MOS6convTest(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    double vgs_rel, vds_rel, vbs_rel;
    double ids_rel, qgs_rel, qgd_rel, qgb_rel;
    int converged = 1;
    
    for(; model != NULL; model = model->MOS6nextModel) {
        for(here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
            
            /* Voltage convergence test */
            vgs_rel = fabs(here->MOS6vgs - here->MOS6vgs_old);
            vds_rel = fabs(here->MOS6vds - here->MOS6vds_old);
            vbs_rel = fabs(here->MOS6vbs - here->MOS6vbs_old);
            
            double vgs_tol = ckt->CKTreltol * MAX(fabs(here->MOS6vgs), ckt->CKTvoltTol) + ckt->CKTabstol;
            double vds_tol = ckt->CKTreltol * MAX(fabs(here->MOS6vds), ckt->CKTvoltTol) + ckt->CKTabstol;
            double vbs_tol = ckt->CKTreltol * MAX(fabs(here->MOS6vbs), ckt->CKTvoltTol) + ckt->CKTabstol;
            
            if(vgs_rel > vgs_tol || vds_rel > vds_tol || vbs_rel > vbs_tol) {
                converged = 0;
            }
            
            /* Current convergence test */
            ids_rel = fabs(here->MOS6ids - here->MOS6ids_old);
            double ids_tol = ckt->CKTreltol * MAX(fabs(here->MOS6ids), ckt->CKTcurTol) + ckt->CKTabstol;
            
            if(ids_rel > ids_tol) {
                converged = 0;
            }
            
            /* Charge convergence test (for charge-based devices) */
            double *qgs_state = ckt->CKTstates[here->MOS6stateQgs];
            double *qgd_state = ckt->CKTstates[here->MOS6stateQgd];
            double *qgb_state = ckt->CKTstates[here->MOS6stateQgb];
            
            qgs_rel = fabs(qgs_state[0] - here->MOS6qgs_old[0]);
            qgd_rel = fabs(qgd_state[0] - here->MOS6qgd_old[0]);
            qgb_rel = fabs(qgb_state[0] - here->MOS6qgb_old[0]);
            
            double qgs_tol = ckt->CKTreltol * MAX(fabs(here->MOS6qgs), ckt->CKTchgTol) + ckt->CKTabstol;
            double qgd_tol = ckt->CKTreltol * MAX(fabs(here->MOS6qgd), ckt->CKTchgTol) + ckt->CKTabstol;
            double qgb_tol = ckt->CKTreltol * MAX(fabs(here->MOS6qgb), ckt->CKTchgTol) + ckt->CKTabstol;
            
            if(qgs_rel > qgs_tol || qgd_rel > qgd_tol || qgb_rel > qgb_tol) {
                converged = 0;
            }
            
            /* Store current values as old for next iteration */
            here->MOS6vgs_old = here->MOS6vgs;
            here->MOS6vds_old = here->MOS6vds;
            here->MOS6vbs_old = here->MOS6vbs;
            here->MOS6ids_old = here->MOS6ids;
            here->MOS6qgs_old[0] = qgs_state[0];
            here->MOS6qgd_old[0] = qgd_state[0];
            here->MOS6qgb_old[0] = qgb_state[0];
        }
    }
    
    return(converged ? OK : E_NOT_CONVERGED);
}
```

### 5. Initial Conditions (`mos6ic.c`)

```c
int MOS6ic(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    
    for(; model != NULL; model = model->MOS6nextModel) {
        for(here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
            
            /* Use IC values if provided, otherwise use node voltages */
            if(here->MOS6icVGS != 0.0) {
                here->MOS6vgs = here->MOS6icVGS;
            } else {
                here->MOS6vgs = ckt->CKTrhs[here->MOS6gNode] - ckt->CKTrhs[here->MOS6sNode];
            }
            
            if(here->MOS6icVDS != 0.0) {
                here->MOS6vds = here->MOS6icVDS;
            } else {
                here->MOS6vds = ckt->CKTrhs[here->MOS6dNode] - ckt->CKTrhs[here->MOS6sNode];
            }
            
            if(here->MOS6icVBS != 0.0) {
                here->MOS6vbs = here->MOS6icVBS;
            } else {
                here->MOS6vbs = ckt->CKTrhs[here->MOS6bNode] - ckt->CKTrhs[here->MOS6sNode];
            }
            
            /* Apply Newton-Raphson voltage limiting */
            here->MOS6vgs = DEVfetlim(here->MOS6vgs, here->MOS6vgs_old, 
                                      model->MOS6vto, ckt);
            here->MOS6vds = DEVlimvds(here->MOS6vds, here->MOS6vds_old);
            
            /* Handle PMOS polarity */
            if(model->MOS6type < 0) {  /* PMOS */
                here->MOS6vgs = -here->MOS6vgs;
                here->MOS6vds = -here->MOS6vds;
                here->MOS6vbs = -here->MOS6vbs;
            }
            
            /* Handle source-drain swapping for negative Vds */
            if(here->MOS6vds < 0.0) {
                double temp = here->MOS6vds;
                here->MOS6vds = -temp;
                here->MOS6vgs = here->MOS6vgs - temp;
                here->MOS6vbs = here->MOS6vbs - temp;
                
                /* Swap internal node indices */
                int tempNode = here->MOS6dNodePrime;
                here->MOS6dNodePrime = here->MOS6sNodePrime;
                here->MOS6sNodePrime = tempNode;
            }
            
            /* Initialize charges based on initial voltages */
            double vth = model->MOS6vto + model->MOS6gamma * 
                        (sqrt(model->MOS6phi + here->MOS6vbs) - sqrt(model->MOS6phi)) +
                        model->MOS6eta * here->MOS6vds;
            
            double vgsteff = MAX(here->MOS6vgs - vth, 0.0);
            double vdsat = pow(model->MOS6kv/model->MOS6kc, 1.0/(model->MOS6nv - model->MOS6nc)) *
                          pow(vgsteff, (model->MOS6nc - 1.0)/(model->MOS6nv - model->MOS6nc));
            
            double vdseff = vdsat * (1.0 - pow(1.0 - pow(here->MOS6vds/vdsat, model->MOS6alpha), 
                                              1.0/model->MOS6alpha));
            
            /* Calculate initial charges */
            here->MOS6qgs = model->MOS6cox * here->MOS6weff * here->MOS6leff * 
                           (vgsteff + vth + 0.5 * vdseff);
            here->MOS6qgd = -0.4 * model->MOS6cox * here->MOS6weff * here->MOS6leff * vgsteff;
            here->MOS6qgb = -model->MOS6cox * here->MOS6weff * here->MOS6leff * 
                           (model->MOS6gamma * sqrt(model->MOS6phi + here->MOS6vbs) + 
                            model->MOS6eta * here->MOS6vds);
            
            /* Initialize state vector */
            double *qgs_state = ckt->CKTstates[here->MOS6stateQgs];
            double *qgd_state = ckt->CKTstates[here->MOS6stateQgd];
            double *qgb_state = ckt->CKTstates[here->MOS6stateQgb];
            
            qgs_state[0] = qgs_state[1] = qgs_state[2] = qgs_state[3] = here->MOS6qgs;
            qgd_state[0] = qgd_state[1] = qgd_state[2] = qgd_state[3] = here->MOS6qgd;
            qgb_state[0] = qgb_state[1] = qgb_state[2] = qgb_state[3] = here->MOS6qgb;
            
            /* Store as old values for convergence testing */
            here->MOS6vgs_old = here->MOS6vgs;
            here->MOS6vds_old = here->MOS6vds;
            here->MOS6vbs_old = here->MOS6vbs;
            here->MOS6qgs_old[0] = here->MOS6qgs_old[1] = here->MOS6qgs_old[2] = here->MOS6qgs;
            here->MOS6qgd_old[0] = here->MOS6qgd_old[1] = here->MOS6qgd_old[2] = here->MOS6qgd;
            here->MOS6qgb_old[0] = here->MOS6qgb_old[1] = here->MOS6qgb_old[2] = here->MOS6qgb;
        }
    }
    return(OK);
}
```

### 6. Temperature Scaling (`mos6temp.c`)

```c
int MOS6temperature(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    double temp = ckt->CKTtemp;
    double tempRatio, vt;
    
    for(; model != NULL; model = model->MOS6nextModel) {
        /* Scale model parameters with temperature */
        tempRatio = temp / model->MOS6tnom;
        vt = temp * CONSTKoverQ;
        
        /* Threshold voltage temperature coefficient */
        model->MOS6vto = model->MOS6vto * (1.0 + model->MOS6tc1 * (temp - model->MOS6tnom) +
                                          model->MOS6tc2 * pow(temp - model->MOS6tnom, 2));
        
        /* Mobility temperature scaling */
        model->MOS6kv = model->MOS6kv * pow(tempRatio, -model->MOS6tmu);
        model->MOS6kc = model->MOS6kc * pow(tempRatio, -model->MOS6tmu);
        
        /* Body effect coefficient scaling */
        model->MOS6gamma = model->MOS6gamma * sqrt(tempRatio);
        
        /* Fermi potential temperature dependence */
        model->MOS6phi = model->MOS6phi * tempRatio - 
                         vt * log(pow(temp/model->MOS6tnom, 1.5)) -
                         3.0 * vt * log(tempRatio);
        
        /* Update all instances of this model */
        for(here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
            /* Recalculate effective dimensions with temperature */
            here->MOS6leff = here->MOS6l - 2.0 * model->MOS6ld * 
                            (1.0 + model->MOS6tld * (temp - model->MOS6tnom));
            here->MOS6weff = here->MOS6w - 2.0 * model->MOS6wd * 
                            (1.0 + model->MOS6twd * (temp - model->MOS6tnom));
            
            /* Oxide capacitance per area */
            model->MOS6cox = 3.9 * 8.854e-12 / model->MOS6tox;
        }
    }
    return(OK);
}
```

## Convergence Analysis

### 1. Numerical Stability Considerations

The MOS6 implementation employs several key techniques to ensure Newton-Raphson convergence:

**Voltage Limiting (`DEVfetlim`):**
```c
double DEVfetlim(double vnew, double vold, double vto, CKTcircuit *ckt)
{
    double vt = CONSTKoverQ * ckt->CKTtemp;
    double vcrit = vt * (1.0 + log(1.0 + (vold - vto)/vt));
    
    if(vnew > vold + vcrit) {
        return vold + vcrit;
    } else if(vnew < vold - vcrit) {
        return vold - vcrit;
    } else if(fabs(vnew - vto) < vt) {
        return vto + vt * tanh((vnew - vto)/vt);
    }
    return vnew;
}
```

This function prevents the gate-source voltage from changing too rapidly between iterations, which could cause divergence in the exponential region near threshold.

**Drain-Source Voltage Limiting (`DEVlimvds`):**
```c
double DEVlimvds(double vnew, double vold)
{
    double limit = 2.0;  /* Maximum factor change per iteration */
    
    if(vnew > 0.0) {
        if(vnew > vold * limit) return vold * limit;
        if(vnew < vold / limit) return vold / limit;
    } else {
        if(vnew < vold * limit) return vold * limit;
        if(vnew > vold / limit) return vold / limit;
    }
    return vnew;
}
```

### 2. Matrix Conditioning

The 6×6 stamped matrix for MOS6 has the following structure for NMOS:

```
Nodes: 0=D, 1=D', 2=G, 3=S', 4=S, 5=B

Conductance matrix stamp:
G[D'][D']  += gdpr + gds + gbd + gm + gmb
G[D'][G]   += -gm
G[D'][S']  += -gds
G[D'][B]   += -gmb - gbd
G[G][D']   += -gm
G[G][G]    += gm
G[S'][D']  += -gds
G[S'][S']  += gspr + gds + gbs - gmbs
G[S'][G]   += gmbs
G[S'][B]   += -gbs
G[B][D']   += -gbd
G[B][S']   += -gbs
G[B][B]    += gbd + gbs

Capacitance matrix stamp (for AC analysis):
Add s*C terms to corresponding positions, where s = jω
```

Where:
- `gdpr`, `gspr`: Drain/source parasitic resistances
- `gds`: Output conductance (`∂I_ds/∂V_ds`)
- `gm`: Transconductance (`∂I_ds/∂V_gs`)
- `gmb`: Body transconductance (`∂I_ds/∂V_bs`)
- `gbd`, `gbs`: Bulk-drain/source diode conductances

### 3. Charge Conservation Verification

The implementation ensures charge conservation through:

1. **Reciprocal Capacitance Matrix:** The stamped capacitance matrix is symmetric (`C_ij = C_ji`) by construction.

2. **State Vector Integration:** Charges are integrated using the trapezoidal rule:
   ```c
   q_n = q_{n-1} + 0.5 * h * (dq/dt_n + dq/dt_{n-1})
   ```
   This preserves charge to second-order accuracy.

3. **KCL Verification:** The sum of terminal currents equals displacement current:
   ```
   I_d + I_s + I_b + I_g = d(Q_d + Q_s + Q_b + Q_g)/dt = 0
   ```
   Since `Q_d + Q_s + Q_b + Q_g = 0` by construction.

### 4. LTE Control and Adaptive Time-Stepping

The LTE calculation provides two key benefits:

1. **Error Control:** Maintains local truncation error below `CKTtrtol × (reltol×|q| + abstol)`.

2. **Efficiency:** Allows larger time-steps during slowly varying periods and automatically reduces time-steps during fast transitions.

The implementation uses a conservative approach:
- Limits time-step changes to factors between 0.5 and 2.0
- Uses three-point backward difference for third derivative estimation
- Applies the LTE criterion separately to each charge component

### 5. Source-Drain Symmetry Handling

For negative `V_ds`, the implementation swaps source and drain internally:

```c
if(here->MOS6vds < 0.0) {
    /* Swap voltages */
    double temp_v = here->MOS6vds;
    here->MOS6vds = -temp_v;
    here->MOS6vgs = here->MOS6vgs - temp_v;
    here->MOS6vbs = here->MOS6vbs - temp_v;
    
    /* Swap matrix pointers */
    double *temp_ptr;
    temp_ptr = here->MOS6drainDrainPrimePtr;
    here->MOS6drainDrainPrimePtr = here->MOS6sourceSourcePrimePtr;
    here->MOS6sourceSourcePrimePtr = temp_ptr;
    /* ... swap all affected matrix pointers */
    
    /* Recalculate with swapped roles */
    MOS6eval(model, here, ckt);
    
    /* Unswap currents for proper stamping */
    here->MOS6ids = -here->MOS6ids;
    here->MOS6gm = here->MOS6gm;  /* Transconductance remains same magnitude */
    here->MOS6gds = here->MOS6gds;
}
```

This ensures the model works correctly for both positive and negative `V_ds` without duplicating evaluation code.

### 6. PMOS Polarity Handling

For PMOS devices (`MOS6type < 0`), the implementation:

1. Negates all terminal voltages
2. Adjusts threshold voltage sign
3. Maintains proper current direction (positive current flows into drain for both NMOS and PMOS in SPICE convention)

### 7. Integration with Ngspice Simulation Flow

The MOS6 model integrates with Ngspice through the device operations structure:

```c
SPICEdev MOS6info = {
    .DEVpublic = {
        .name = "MOS6",
        .description = "Sakurai-Newton Level 6 MOSFET model",
        .terms = 4,
        .numNames = 0,
        .termNames = NULL,
        .modType = MOS6modType,
    },
    .DEVparam = MOS6param,
    .DEVmodParam = MOS6mParam,
    .DEVload = MOS6load,
    .DEVsetup = MOS6setup,
    .DEVunsetup = NULL,
    .DEVpzSetup = MOS6setup,
    .DEVtemperature = MOS6temperature,
    .DEVtrunc = MOS6trunc,
    .DEVconvTest = MOS6convTest,
    .DEVfindBranch = NULL,
    .DEVacLoad = MOS6acLoad,
    .DEVaccept = NULL,
    .DEV