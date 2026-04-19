# MOS9: Parameter Parsing and Matrix Setup

_Generated 2026-04-12 08:36 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9ask.c`

# Chapter 6: MOS6: Transient Control and Convergence Checking

## 6.1 Introduction: Transient Analysis Framework for MOS6

The MOS6 (Level 6) model implements the Sakurai-Newton empirical alpha-power law formulation optimized for digital circuit simulation, where transient analysis and convergence robustness are paramount. This chapter examines the core C files responsible for time-step control, convergence checking, and initial condition handling within Ngspice's transient analysis framework:

- **`mos6trun.c`**: Implements Local Truncation Error (LTE) calculation for adaptive time-step control using charge conservation principles
- **`mos6conv.c`**: Performs Newton-Raphson convergence testing by comparing voltage and current changes against SPICE tolerances
- **`mos6ic.c`**: Handles initial condition specification and prioritization for transient analysis startup
- **`mos6set.c`**: Allocates the 6×6 sparse matrix structure for the MOS6 device topology
- **`mos6temp.c`**: Manages temperature-dependent parameter scaling for consistent device behavior

These files work in concert to ensure numerical stability during transient simulation of digital circuits, where the MOS6 model's piecewise-linear approximation and lack of subthreshold conduction demand specialized convergence handling.

## 6.2 Mathematical Formulation

### 6.2.1 Threshold Voltage with DIBL and Temperature Effects

The MOS6 threshold voltage incorporates drain-induced barrier lowering (DIBL) and temperature dependence:

```
V_th = VTO + γ·[√(2φ + V_sb) - √(2φ)] + η·V_ds + K_T·(T - T_nom)
```

Where:
- `VTO`: Zero-bias threshold voltage at reference temperature
- `γ`: Body effect coefficient
- `φ`: Surface potential (typically 0.7V)
- `η`: DIBL coefficient (model parameter `MOS6eta`)
- `K_T`: Temperature coefficient of threshold voltage

### 6.2.2 Sakurai-Newton Alpha-Power Law Current Equations

The MOS6 model uses separate formulations for linear and saturation regions with empirical power coefficients:

**Linear Region (|V_ds| ≤ |V_dsat|):**
```
I_ds_lin = β_lin · (V_gsteff)^NC · V_ds · (1 + λ·V_ds)
```
Where `β_lin = (W_eff/L_eff)·μ_eff·C_ox` and `NC` is the linear region power coefficient (model parameter `MOS6nc`).

**Saturation Region (|V_ds| > |V_dsat|):**
```
I_ds_sat = β_sat · (V_gsteff)^NV · (1 + λ·V_ds)
```
Where `NV` is the saturation region power coefficient (model parameter `MOS6nv`) and typically `NV > NC`.

### 6.2.3 Saturation Voltage and Smoothing Function

The drain saturation voltage is derived from continuity conditions:

```
V_dsat = (KV/KC)^(1/(NV-NC)) · (V_gsteff)^((NC-1)/(NV-NC))
```

Where `KV = β_sat` and `KC = β_lin·V_dsat`. For C¹ continuity between regions, a smoothing function is applied:

```
V_dseff = V_dsat · [1 - S(1 - V_ds/V_dsat)]
```

With the smoothing function `S(x) = 0.5·[x + √(x² + δ²)]` where `δ = 0.1` ensures derivative continuity.

### 6.2.4 Effective Gate-Source Voltage

The effective gate drive voltage uses the `DEVfetlim()` limiting function for Newton-Raphson convergence:

```
V_gsteff = DEVfetlim(V_gs - V_th, vgs_old, VTH_MAX, VTH_MIN, &check)
```

Where `VTH_MAX = V_gd + 0.5` and `VTH_MIN = -3.0` for typical digital voltage ranges.

### 6.2.5 Charge Conservation Model

The MOS6 uses the Meyer capacitance model with charge partitioning:

```
Q_gs = (2/3)·C_ox·W_eff·L_eff·V_gsteff·[1 - (V_dseff/(2·V_gsteff + V_dseff))²]
Q_gd = (2/3)·C_ox·W_eff·L_eff·V_gsteff·[1 - (V_gsteff/(2·V_dseff + V_gsteff))²]
Q_gb = C_gb0·V_gb + 0.5·C_gb1·V_gb²
```

Junction capacitances use the standard SPICE diode model:
```
C_bd = C_j0·A_d / (1 - V_bd/PB)^MJ + C_jsw0·P_d / (1 - V_bd/PB)^MJSW
C_bs = C_j0·A_s / (1 - V_bs/PB)^MJ + C_jsw0·P_s / (1 - V_bs/PB)^MJSW
```

### 6.2.6 Local Truncation Error (LTE) Formulation

For adaptive time-step control, the LTE is computed from charge derivatives:

```
ε_charge = |h·(q̈(t) + O(h²))|
TOL = CKTchgtol·max(|q(t)|, |q(t-h)|) + CKTabstol
```

Where `h` is the current time-step, `q̈(t)` is the second derivative of charge estimated from history arrays, and the simulation requires `ε_charge ≤ TOL`.

### 6.2.7 Convergence Criteria

Newton-Raphson iteration continues until all convergence tests pass:

**Voltage Convergence:**
```
|ΔV| ≤ CKTreltol·max(|V_new|, |V_old|) + CKTvoltTol
```

**Current Convergence:**
```
|ΔI| ≤ CKTreltol·max(|I_new|, |I_old|) + CKTabstol
```

**Charge Convergence:**
```
|ΔQ| ≤ CKTreltol·max(|Q_new|, |Q_old|) + CKTchgtol
```

With typical SPICE defaults: `CKTreltol = 0.001`, `CKTabstol = 1e-12`, `CKTvoltTol = 1e-6`, `CKTchgtol = 1e-14`.

## 6.3 C Implementation

### 6.3.1 Core Data Structures

**Model Structure (`mos6defs.h`):**
```c
typedef struct sMOS6model {
    int MOS6type;                  /* N_TYPE or P_TYPE */
    double MOS6vto;                /* Threshold voltage VTO */
    double MOS6alpha;              /* Alpha-power law coefficient */
    double MOS6beta;               /* Beta factor (KP·W/L) */
    double MOS6lambda;             /* Channel length modulation */
    double MOS6kv;                 /* Saturation coefficient KV */
    double MOS6nv;                 /* Saturation power NV */
    double MOS6kc;                 /* Linear coefficient KC */
    double MOS6nc;                 /* Linear power NC */
    double MOS6gamma;              /* Body effect coefficient */
    double MOS6phi;                /* Surface potential */
    double MOS6eta;                /* DIBL coefficient */
    
    /* Temperature scaling parameters */
    double MOS6vtoTemp;
    double MOS6betaTemp;
    double MOS6phiTemp;
    
    /* Matrix pointers */
    int MOS6drainDrainPtr;
    int MOS6drainGatePtr;
    int MOS6drainSourcePtr;
    int MOS6drainBulkPtr;
    /* ... 6×6 matrix total */
    
    struct sMOS6model *MOS6nextModel; /* Linked list */
    MOS6instance *MOS6instances;      /* Instance list */
} MOS6model;
```

**Instance Structure (`mos6defs.h`):**
```c
typedef struct sMOS6instance {
    int MOS6dNode;          /* Drain node */
    int MOS6gNode;          /* Gate node */
    int MOS6sNode;          /* Source node */
    int MOS6bNode;          /* Bulk node */
    int MOS6dNodePrime;     /* Internal drain node */
    int MOS6sNodePrime;     /* Internal source node */
    
    /* Operating point variables */
    double MOS6vgs;
    double MOS6vds;
    double MOS6vbs;
    double MOS6vbd;
    double MOS6vbs;
    double MOS6ids;
    
    /* Small-signal parameters */
    double MOS6gm;          /* Transconductance */
    double MOS6gds;         /* Output conductance */
    double MOS6gmbs;        /* Body transconductance */
    
    /* Charge states */
    int MOS6qgs;            /* Gate-source charge state index */
    int MOS6qgd;            /* Gate-drain charge state index */
    int MOS6qgb;            /* Gate-bulk charge state index */
    int MOS6qbd;            /* Bulk-drain charge state index */
    int MOS6qbs;            /* Bulk-source charge state index */
    
    /* History arrays for LTE */
    double MOS6ids_old[3];  /* Current history for derivative estimation */
    double MOS6qgs_old[3];  /* Charge history for LTE */
    double MOS6qgd_old[3];
    
    /* Convergence flags */
    unsigned MOS6off : 1;   /* Device off flag */
    unsigned MOS6icVBSGiven : 1;
    unsigned MOS6icVDSGiven : 1;
    unsigned MOS6icVGSGiven : 1;
    
    struct sMOS6instance *MOS6nextInstance;
} MOS6instance;
```

### 6.3.2 Matrix Setup (`mos6set.c`)

The `MOS6setup()` function allocates the 6×6 sparse matrix structure:

```c
int MOS6setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    
    /* Allocate 6×6 matrix pointers for nodes: 0:D, 1:D', 2:G, 3:S', 4:S, 5:B */
    for (here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
        /* External nodes */
        here->MOS6drainDrainPtr = SMPmakeElt(matrix, here->MOS6dNode, here->MOS6dNode);
        here->MOS6gateGatePtr = SMPmakeElt(matrix, here->MOS6gNode, here->MOS6gNode);
        here->MOS6sourceSourcePtr = SMPmakeElt(matrix, here->MOS6sNode, here->MOS6sNode);
        here->MOS6bulkBulkPtr = SMPmakeElt(matrix, here->MOS6bNode, here->MOS6bNode);
        
        /* Internal nodes for parasitic resistances */
        here->MOS6drainPrimeDrainPrimePtr = SMPmakeElt(matrix, 
            here->MOS6dNodePrime, here->MOS6dNodePrime);
        here->MOS6sourcePrimeSourcePrimePtr = SMPmakeElt(matrix, 
            here->MOS6sNodePrime, here->MOS6sNodePrime);
        
        /* Cross terms */
        here->MOS6drainDrainPrimePtr = SMPmakeElt(matrix, 
            here->MOS6dNode, here->MOS6dNodePrime);
        here->MOS6drainPrimeDrainPtr = SMPmakeElt(matrix, 
            here->MOS6dNodePrime, here->MOS6dNode);
        /* ... allocate all 36 possible entries */
        
        /* Allocate state vector indices for charges */
        if (states != NULL) {
            here->MOS6qgs = *states; (*states)++;
            here->MOS6qgd = *states; (*states)++;
            here->MOS6qgb = *states; (*states)++;
            here->MOS6qbd = *states; (*states)++;
            here->MOS6qbs = *states; (*states)++;
        }
    }
    
    return OK;
}
```

### 6.3.3 Local Truncation Error Calculation (`mos6trun.c`)

The `MOS6trunc()` function computes LTE for time-step control:

```c
int MOS6trunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    double chargeTol, currentTol;
    double del1, del2, del3;
    double qddot;
    
    for (here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
        /* Calculate second derivative of charge using history */
        del1 = here->MOS6qgs_old[0] - here->MOS6qgs_old[1];
        del2 = here->MOS6qgs_old[1] - here->MOS6qgs_old[2];
        del3 = del1 - del2;
        qddot = del3 / (ckt->CKTdeltaOld[0] * ckt->CKTdeltaOld[1]);
        
        /* Gate-source charge LTE */
        chargeTol = ckt->CKTchgtol * MAX(fabs(here->MOS6qgs_old[0]), 
                                        fabs(here->MOS6qgs_old[1])) + ckt->CKTabstol;
        
        double lte_qgs = fabs(ckt->CKTdelta * ckt->CKTdelta * qddot / 12.0);
        
        if (lte_qgs > chargeTol) {
            /* Reduce time-step */
            double newDelta = ckt->CKTdelta * sqrt(chargeTol / (lte_qgs + 1e-30));
            *timeStep = MIN(*timeStep, newDelta);
        }
        
        /* Similar calculations for other charges (qgd, qgb, qbd, qbs) */
        
        /* Current LTE check */
        del1 = here->MOS6ids_old[0] - here->MOS6ids_old[1];
        del2 = here->MOS6ids_old[1] - here->MOS6ids_old[2];
        del3 = del1 - del2;
        double iddot = del3 / (ckt->CKTdeltaOld[0] * ckt->CKTdeltaOld[1]);
        
        currentTol = ckt->CKTreltol * MAX(fabs(here->MOS6ids_old[0]), 
                                         fabs(here->MOS6ids_old[1])) + ckt->CKTabstol;
        
        double lte_ids = fabs(ckt->CKTdelta * ckt->CKTdelta * iddot / 12.0);
        
        if (lte_ids > currentTol) {
            double newDelta = ckt->CKTdelta * sqrt(currentTol / (lte_ids + 1e-30));
            *timeStep = MIN(*timeStep, newDelta);
        }
    }
    
    return OK;
}
```

### 6.3.4 Convergence Testing (`mos6conv.c`)

The `MOS6convTest()` function performs Newton-Raphson convergence checks:

```c
int MOS6convTest(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    double vgs, vds, vbs;
    double delVgs, delVds, delVbs;
    double delIds, delQgs, delQgd;
    double reltol = ckt->CKTreltol;
    double abstol = ckt->CKTabstol;
    double voltTol = ckt->CKTvoltTol;
    double chgTol = ckt->CKTchgtol;
    
    for (here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
        /* Get current and previous voltages */
        vgs = *(ckt->CKTrhsOld + here->MOS6gNode) - *(ckt->CKTrhsOld + here->MOS6sNodePrime);
        vds = *(ckt->CKTrhsOld + here->MOS6dNodePrime) - *(ckt->CKTrhsOld + here->MOS6sNodePrime);
        vbs = *(ckt->CKTrhsOld + here->MOS6bNode) - *(ckt->CKTrhsOld + here->MOS6sNodePrime);
        
        double vgs_old = here->MOS6vgs_old;
        double vds_old = here->MOS6vds_old;
        double vbs_old = here->MOS6vbs_old;
        
        /* Calculate changes */
        delVgs = fabs(vgs - vgs_old);
        delVds = fabs(vds - vds_old);
        delVbs = fabs(vbs - vbs_old);
        
        /* Voltage convergence test */
        double vgsCrit = reltol * MAX(fabs(vgs), fabs(vgs_old)) + voltTol;
        double vdsCrit = reltol * MAX(fabs(vds), fabs(vds_old)) + voltTol;
        double vbsCrit = reltol * MAX(fabs(vbs), fabs(vbs_old)) + voltTol;
        
        if (delVgs > vgsCrit || delVds > vdsCrit || delVbs > vbsCrit) {
            ckt->CKTnoncon = 1;  /* Mark as non-convergent */
            return E_NOT_CONVERGED;
        }
        
        /* Current convergence test */
        double ids = here->MOS6ids;
        double ids_old = here->MOS6ids_old;
        delIds = fabs(ids - ids_old);
        double idsCrit = reltol * MAX(fabs(ids), fabs(ids_old)) + abstol;
        
        if (delIds > idsCrit) {
            ckt->CKTnoncon = 1;
            return E_NOT_CONVERGED;
        }
        
        /* Charge convergence test */
        double *states = ckt->CKTstates;
        int qgs_index = here->MOS6qgs;
        int qgd_index = here->MOS6qgd;
        
        if (qgs_index >= 0 && qgd_index >= 0) {
            double qgs = states[qgs_index];
            double qgd = states[qgd_index];
            double qgs_old = here->MOS6qgs_old[0];
            double qgd_old = here->MOS6qgd_old[0];
            
            delQgs = fabs(qgs - qgs_old);
            delQgd = fabs(qgd - qgd_old);
            
            double qgsCrit = reltol * MAX(fabs(qgs), fabs(qgs_old)) + chgTol;
            double qgdCrit = reltol * MAX(fabs(qgd), fabs(qgd_old)) + chgTol;
            
            if (delQgs > qgsCrit || delQgd > qgdCrit) {
                ckt->CKTnoncon = 1;
                return E_NOT_CONVERGED;
            }
        }
    }
    
    return OK;
}
```

### 6.3.5 Initial Condition Handling (`mos6ic.c`)

The `MOS6ic()` function processes initial conditions with priority handling:

```c
int MOS6ic(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS6model *model = (MOS6model*)inModel;
    MOS6instance *here;
    
    for (here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
        /* Priority 1: IC parameter on instance */
        if (here->MOS6icVGSGiven || here->MOS6icVDSGiven || here->MOS6icVBSGiven) {
            if (here->MOS6icVGSGiven) {
                double vgs = here->MOS6icVGS;
                *(ckt->CKTrhs + here->MOS6gNode) = vgs;
                *(ckt->CKTrhs + here->MOS6sNodePrime) = 0.0;
            }
            if (here->MOS6icVDSGiven) {
                double vds = here->MOS6icVDS;
                *(ckt->CKTrhs + here->MOS6dNodePrime) = vds;
                *(ckt->CKTrhs + here->MOS6sNodePrime) = 0.0;
            }
            if (here->MOS6icVBSGiven) {
                double vbs = here->MOS6icVBS;
                *(ckt->CKTrhs + here->MOS6bNode) = vbs;
                *(ckt->CKTrhs + here->MOS6sNodePrime) = 0.0;
            }
            continue;
        }
        
        /* Priority 2: NODESET values */
        double vg = ckt->CKTnodeset[here->MOS6gNode];
        double vd = ckt->CKTnodeset[here->MOS6dNode];
        double vs = ckt->CKTnodeset[here->MOS6sNode];
        double vb = ckt->CKTnodeset[here->MOS6bNode];
        
        if (vg != 0.0 || vd != 0.0 || vs != 0.0 || vb != 0.0) {
            *(ckt->CKTrhs + here->MOS6gNode) = vg;
            *(ckt->CKTrhs + here->MOS6dNode) = vd;
            *(ckt->CKTrhs + here->MOS6sNode) = vs;
            *(ckt->CKTrhs + here->MOS6bNode) = vb;
            continue;
        }
        
        /* Priority 3: Default initialization */
        if (model->MOS6type == N_TYPE) {
            *(ckt->CKTrhs + here->MOS6gNode) = 0.0;
            *(ckt->CKTrhs + here->MOS6dNode) = 5.0;  /* Typical VDD */
            *(ckt->CKTrhs + here->MOS6sNode) = 0.0;
            *(ckt->CKTrhs + here->MOS6bNode) = 0.0;
        } else { /* P_TYPE */
            *(ckt->CKTrhs + here->MOS6gNode) = 5.0;
            *(ckt->CKTrhs + here->MOS6dNode) = 0.0;
            *(ckt->CKTrhs + here->MOS6sNode) = 5.0;
            *(ckt->CKTrhs + here->MOS6bNode) = 5.0;
        }
        
        /* Initialize internal nodes */
        *(ckt->CKTrhs + here->MOS6dNodePrime) = *(ckt->CKTrhs + here->MOS6dNode);
        *(ckt->CKTrhs + here->MOS6sNodePrime) = *(ckt->CKTrhs + here->MOS6sNode);
        
        /* Initialize history arrays */
        here->MOS6vgs_old = *(ckt->CKTrhs + here->MOS6gNode) - 
                           *(ckt->CKTrhs + here->MOS6sNodePrime);
        here->MOS6vds_old = *(ckt->CKTrhs + here->MOS6dNodePrime) - 
                           *(ckt->CKTrhs + here->MOS6sNodePrime);
        here->MOS6vbs_old = *(ckt->CKTrhs + here->MOS6bNode) - 
                           *(ckt->CKTrhs + here->MOS6sNodePrime);
        
        /* Initialize charge states */
        if (here->MOS6qgs >= 0) {
            ckt->CKTstates[here->MOS6qgs] = 0.0;
            here->MOS6qgs_old[0] = here->MOS6qgs_old[1] = here->MOS6qgs_old[2] = 0.0;
        }
        if (here->MOS6qgd >= 0) {
            ckt->CKTstates[here->MOS6qgd] = 0.0;
            here->MOS6qgd_old[0] = here->MOS6qgd_old[1] = here->MOS6qgd_old[2] = 0.0;
        }
    }
    
    return OK;
}
```

### 6.3.6 Temperature Scaling (`mos6temp.c`)

The `MOS6temperature()` function handles temperature-dependent parameter updates:

```c
int MOS6temperature(MOS6model *model, CKTcircuit *ckt)
{
    double temp = ckt->CKTtemp;
    double tnom = model->MOS6tnom;
    double tempRatio = temp / tnom;
    double vt = temp * CONSTKoverQ;
    double vtnom = tnom * CONSTKoverQ;
    
    /* Threshold voltage temperature scaling */
    double kt = model->MOS6kt1;
    if (model->MOS6tcvGiven) {
        kt = model->MOS6tcv;
    }
    model->MOS6vtoTemp = model->MOS6vto - kt * (temp - tnom);
    
    /* Beta temperature scaling */
    double betaExp = model->MOS6ute;
    if (!model->MOS6uteGiven) {
        betaExp = 1.5;  /* Default exponent */
    }
    model->MOS6betaTemp = model->MOS6beta * pow(tempRatio, betaExp);
    
    /* Phi temperature scaling */
    double eg = 1.16 - 7.02e-4 * temp * temp / (temp + 1108.0);
    double egnom = 1.16 - 7.02e-4 * tnom * tnom / (tnom + 1108.0);
    model->MOS6phiTemp = model->MOS6phi * temp / tnom - 
                        2.0 * vt * log(temp / tnom) - 
                        eg + temp / tnom * egnom;
    
    /* Bandgap narrowing effect */
    if (model->MOS6tlev == 2) {
        double vtn = CONSTKoverQ * tnom;
        double vtd = CONSTKoverQ * temp;
        double phin = 2.0 * vtn * log(model->MOS6nsub / 1.45e16);
        double phid = 2.0 * vtd * log(model->MOS6nsub / 1.45e16);
        model->MOS6phiTemp = model->MOS6phiTemp + phid - phin;
    }
    
    /* Update all instances */
    MOS6instance *here;
    for (here = model->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
        here->MOS6temp = temp;
        here->MOS6vt = vt;
        
        /* Recalculate effective dimensions at new temperature */
        double tlevc = model->MOS6tlevc;
        double tlev = model->MOS6tlev;
        
        here->MOS6leff = here->MOS6l - 2.0 * model->MOS6latDiff;
        if (tlev == 1) {
            here->MOS6leff = here->MOS6leff - tlevc * (temp - tnom);
        }
        here->MOS6leff = MAX(here->MOS6leff, 1e-12);
        
        here->MOS6weff = here->MOS6w - 2.0 * model->MOS6widthDiff;
        here->MOS6weff = MAX(here->MOS6weff, 1e-12);
        
        /* Update beta for this instance */
        here->MOS6beta = model->MOS6betaTemp * here->MOS6weff / here->MOS6leff;
    }
    
    return OK;
}
```

### 6.3.7 Voltage Limiting Algorithm

The `DEVfetlim()` function ensures Newton-Raphson convergence by limiting voltage changes:

```c
double DEVfetlim(double vnew, double vold, double vto, double vmax, int *check)
{
    double vtsthi, vtstlo, vtox;
    double delv, vtemp;
    
    vtsthi = fabs(2.0 * (vold - vto)) + 2.0;
    vtstlo = vtsthi / 2.0 + vmax;
    
    delv = vnew - vold;
    
    if (vold >= vto) {
        if (vold >= vmax) {
            vtemp = vmax;
            vtox = vto + 3.0;
            if (vnew >= vtox) {
                if (delv > 0.0) {
                    *check = 1;
                    vnew = vold + vtsthi * (1.0 - exp(-delv/vtsthi));
                } else {
                    vnew = vold + delv / (1.0 - delv/vtstlo);
                }
            } else {
                if (delv > 0.0) {
                    vnew = MIN(vnew, vtox);
                } else if (vnew <= vto) {
                    vnew = MAX(vnew, vto - 0.5);
                }
            }
        } else {
            vtox = vto + 3.0;
            if (vnew >= vtox) {
                if (delv > 0.0) {
                    *check = 1;
                    vnew = vold + vtsthi * (1.0 - exp(-delv/vtsthi));
                } else {
                    vnew = vold + delv / (1.0 - delv/vtstlo);
                }
            } else if (vnew <= vto) {
                vnew = MAX(vnew, vto - 0.5);
            }
        }
    } else {
        vtemp = vto - 0.5;
        if (vnew <= vtemp) {
            if (delv < 0.0) {
                *check = 1;
                vnew = vold - vtsthi * (1.0 - exp(delv/vtsthi));
            } else {
                vnew = vold + delv / (1.0 + delv/vtstlo);
            }
        } else if (vnew >= vto) {
            vnew = MIN(vnew, vto + 0.5);
        }
    }
    
    return vnew;
}
```

### 6.3.8 Source-Drain Swap Logic

For PMOS devices or negative Vds, the source and drain are swapped:

```c
void MOS6swapSourceDrain(MOS6instance *here, CKTcircuit *ckt)
{
    if ((here->MOS6mode < 0 && here->MOS6vds > 0) || 
        (here->MOS6mode > 0 && here->MOS6vds < 0)) {
        
        /* Swap node indices */
        int tmpNode = here->MOS6dNode;
        here->MOS6dNode = here->MOS6sNode;
        here->MOS6sNode = tmpNode;
        
        tmpNode = here->MOS6dNodePrime;
        here->MOS6dNodePrime = here->MOS6sNodePrime;
        here->MOS6sNodePrime = tmpNode;
        
        /* Swap voltages with sign change */
        double tmpVolt = here->MOS6vgs;
        here->MOS6vgs = here->MOS6vgd;
        here->MOS6vgd = tmpVolt;
        
        here->MOS6vds = -here->MOS6vds;
        here->MOS6vbs = here->MOS6vbd;
        
        /* Swap conductances */
        tmpVolt = here->MOS6gm;
        here->MOS6gm = here->MOS6gmbs;
        here->MOS6gmbs = tmpVolt;
        
        /* Update matrix pointers */
        int tmpPtr = here->MOS6drainDrainPtr;
        here->MOS6drainDrainPtr = here->MOS6sourceSourcePtr;
        here->MOS6sourceSourcePtr = tmpPtr;
        
        /* ... swap all matrix pointers */
        
        here->MOS6mode = -here->MOS6mode;
    }
}
```

## 6.4 Convergence Analysis

### 6.4.1 Newton-Raphson Convergence Strategy

The MOS6 model employs several strategies to ensure Newton-Raphson convergence:

1. **Voltage Limiting**: The `DEVfetlim()` function prevents excessive voltage changes between iterations, particularly near threshold where derivatives are discontinuous.

2. **Alpha-Power Law Smoothing**: The smoothing function `S(x)` ensures C¹ continuity between linear and saturation regions, providing continuous first derivatives for Newton-Raphson.

3. **Charge Conservation**: By tracking charges in the state vector and ensuring charge continuity, the model avoids charge-based discontinuities that can cause convergence failure.

4. **Temperature Consistency**: All temperature-dependent parameters are updated simultaneously at the start of each temperature point, preventing inconsistent device behavior.

5. **Fallback Strategies**: If convergence fails, Ngspice employs:
   - GMIN stepping (gradually increasing minimum conductance)
   - Source stepping (gradually applying sources)
   - Damping (reducing Newton step size)

### 6.4.2 Time-Step Control Algorithm

The LTE-based time-step control follows this algorithm:

```
1. Initialize time-step h = h_min
2. While t < t_stop:
   3. Perform Newton-Raphson iteration at time t
   4. If converged:
       5. Calculate LTE for all MOS6 devices
       6. Find maximum LTE ratio = max(ε_device / TOL_device)
       7. If max_ratio > 1.0:
           8. h_new = h * sqrt(1.0 / max_ratio)
           9. If h_new < h_min: h_new = h_min
          10. Reject step, set h = h_new, goto 3
       11. Else:
          12. Accept step, update history arrays
          13. Predict next time-step: h_next = h * min(2.0, (7.0/max_ratio)^(1/3))
          14. h = min(h_next, h_max, t_stop - t)
          15. t = t + h
   16. Else: (not converged)
       17. Reduce time-step: h = h * 0.5
       18. If h < h_min: abort with convergence error
       19. Goto 3
```

### 6.4.3 Matrix Conditioning

The 6×6 matrix structure provides numerical stability:

```
[ Y_dd   Y_dd'  0      0      0      0     ] [ V_d   ]   [ I_d   ]
[ Y_d'd  Y_d'd' Y_d'g  Y_d's' 0      0     ] [ V_d'  ]   [ 0     ]
[ 0      Y_gd'  Y_gg   Y_gs'  0      Y_gb  ] [ V_g   ] = [ I_g   ]
[ 0      Y_s'd' Y_s'g  Y_s's' Y_s's  0     ] [ V_s'  ]   [ 0     ]
[ 0      0      0      Y_ss'  Y_ss   0     ] [ V_s   ]   [ I_s   ]
[ 0      0      Y_bg   0      0      Y_bb  ] [ V_b   ]   [ I_b   ]
```

Where:
- Diagonal elements include conductances and GMIN (1e-12 Ʊ) for non-singularity
- The internal nodes D' and S' decouple parasitic resistances from external nodes
- Symmetric structure (Y_ij = Y_ji) for reciprocal devices

### 6.4.4 Error Metrics and Tolerances

The MOS6 model uses SPICE's standard error metrics:

1. **Absolute Tolerance (abstol)**: 1e-12 A for currents, 1e-14 C for charges
2. **Relative Tolerance (reltol)**: 0.001 (0.1%) for all relative comparisons
3. **Voltage Tolerance (voltTol)**: 1e-6 V for voltage convergence
4. **Charge Tolerance (chgtol)**: 1e-14 C for charge conservation
5. **Truncation Tolerance (trtol)**: 7.0 for LTE over-estimation factor

The combined convergence criterion for any quantity x is:
```
|Δx| ≤ reltol·max(|x_new|, |x_old|) + abstol_x
```

### 6.4.5 Numerical Protection Mechanisms

To prevent numerical errors:

1. **Division Protection**:
   ```c
   double safe_divide(double a, double b) {
       return (fabs(b) > 1e-100) ? a/b : (