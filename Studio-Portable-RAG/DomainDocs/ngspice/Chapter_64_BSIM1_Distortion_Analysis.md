# BSIM1: Harmonic Distortion Analysis

_Generated 2026-04-12 11:18 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1dset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1disto.c`

# MOS6: Transient Control and Convergence Checking

## Technical Introduction

The MOS6 (Level 6) model in Ngspice implements the Sakurai-Newton empirical alpha-power law model optimized for digital circuit simulation. This chapter details the transient analysis and convergence checking mechanisms specific to the MOS6 implementation, which are distributed across four core C files:

- **`mos6set.c`**: Allocates the 6×6 sparse matrix structure for the MOS6 device and sets up matrix pointers for the Newton-Raphson iteration. This file defines the node mapping (D, D', G, S', S, B) and establishes the conductance matrix framework.
- **`mos6trun.c`**: Implements the Local Truncation Error (LTE) calculation for adaptive time-step control during transient analysis. It computes the second derivative of charge to bound the integration error.
- **`mos6conv.c`**: Performs convergence testing by comparing successive Newton-Raphson iterations of terminal voltages and branch currents against SPICE's relative and absolute tolerances.
- **`mos6ic.c`**: Calculates initial conditions for the device state variables at the start of transient analysis, ensuring consistent starting points for integration.

These files work in concert to ensure numerical stability and accuracy during time-domain simulation of digital circuits using the power-law MOS6 model, which explicitly excludes subthreshold conduction for computational efficiency.

## Mathematical Formulation

### 1. Core DC Equations

The MOS6 model uses empirical alpha-power law relationships with separate coefficients for linear and saturation regions.

#### 1.1 Threshold Voltage
\[
V_{th} = VTO + \gamma \cdot \left[ \sqrt{2\phi + V_{sb}} - \sqrt{2\phi} \right] + \eta \cdot V_{ds}
\]
where:
- \(VTO\): Zero-bias threshold voltage
- \(\gamma\): Body-effect coefficient
- \(\phi\): Surface potential
- \(\eta\): Drain-induced barrier lowering (DIBL) coefficient
- \(V_{sb}\): Source-bulk voltage
- \(V_{ds}\): Drain-source voltage

#### 1.2 Effective Gate-Source Voltage
\[
V_{gsteff} = \text{DEVfetlim}(V_{gs} - V_{th}, V_{gstold})
\]
The `DEVfetlim` function ensures smooth, continuous derivatives for Newton-Raphson convergence by limiting voltage updates between iterations.

#### 1.3 Linear Region Current (\(V_{ds} < V_{dsat}\))
\[
I_{ds\_lin} = \beta_{lin} \cdot (V_{gsteff})^{NC} \cdot V_{ds} \cdot (1 + \lambda \cdot V_{ds})
\]
where:
- \(\beta_{lin} = KC \cdot \frac{W}{L}\): Linear region transconductance coefficient
- \(NC\): Linear region velocity saturation exponent (typically 1.0-1.5)
- \(\lambda\): Channel-length modulation coefficient

#### 1.4 Saturation Region Current (\(V_{ds} \geq V_{dsat}\))
\[
I_{ds\_sat} = \beta_{sat} \cdot (V_{gsteff})^{NV} \cdot (1 + \lambda \cdot V_{ds})
\]
where:
- \(\beta_{sat} = KV \cdot \frac{W}{L}\): Saturation region transconductance coefficient
- \(NV\): Saturation region velocity saturation exponent (typically 1.5-2.5)

#### 1.5 Saturation Voltage
\[
V_{dsat} = \left( \frac{KV}{KC} \right)^{\frac{1}{NV - NC}} \cdot (V_{gsteff})^{\frac{NC - 1}{NV - NC}}
\]

#### 1.6 Smooth Transition Function
\[
I_{ds} = I_{ds\_lin} \cdot \left[ 1 + \left( \frac{V_{ds}}{V_{dsat}} \right)^{ALPHA} \right]^{-\frac{1}{ALPHA}}
\]
where \(ALPHA\) is the smoothing parameter (typically 2.0-5.0) ensuring C¹ continuity between regions.

#### 1.7 Partial Derivatives for Jacobian Matrix
\[
g_m = \frac{\partial I_{ds}}{\partial V_{gs}} = \begin{cases}
NC \cdot \beta_{lin} \cdot (V_{gsteff})^{NC-1} \cdot V_{ds} \cdot (1 + \lambda V_{ds}) & \text{(linear)} \\
NV \cdot \beta_{sat} \cdot (V_{gsteff})^{NV-1} \cdot (1 + \lambda V_{ds}) & \text{(saturation)}
\end{cases}
\]

\[
g_{ds} = \frac{\partial I_{ds}}{\partial V_{ds}} = \begin{cases}
\beta_{lin} \cdot (V_{gsteff})^{NC} \cdot (1 + 2\lambda V_{ds}) & \text{(linear)} \\
\lambda \cdot \beta_{sat} \cdot (V_{gsteff})^{NV} & \text{(saturation)}
\end{cases}
\]

\[
g_{mb} = \frac{\partial I_{ds}}{\partial V_{bs}} = -g_m \cdot \frac{\partial V_{th}}{\partial V_{bs}} = -g_m \cdot \frac{\gamma}{2\sqrt{2\phi + V_{sb}}}
\]

### 2. Charge Conservation Model

#### 2.1 Meyer Capacitance Model
\[
Q_{gs} = C_{gso} \cdot V_{gs} + \frac{2}{3} C_{ox} \cdot W \cdot L \cdot \left[ 1 - \left( \frac{V_{gd} - V_{th}}{2(V_{gs} - V_{th}) - V_{ds}} \right)^2 \right]
\]

\[
Q_{gd} = C_{gdo} \cdot V_{gd} + \frac{2}{3} C_{ox} \cdot W \cdot L \cdot \left[ 1 - \left( \frac{V_{gs} - V_{th}}{2(V_{gd} - V_{th}) + V_{ds}} \right)^2 \right]
\]

\[
Q_{gb} = C_{gbo} \cdot (V_{gb} - V_{th})
\]

#### 2.2 Junction Capacitances
\[
C_{js}(V) = \begin{cases}
\frac{CJ}{\left(1 - \frac{V}{PB}\right)^{MJ}} & V < FC \cdot PB \\
\frac{CJ}{(1 - FC)^{MJ}} \left[ 1 - MJ \cdot \frac{V - FC \cdot PB}{PB(1 - FC)} \right] & V \geq FC \cdot PB
\end{cases}
\]

### 3. Transient Analysis Mathematics

#### 3.1 Local Truncation Error (LTE) Bound
For backward Euler integration with time step \(h\):
\[
\epsilon_{LTE} = \left| h \cdot \left( \ddot{q}(t) + O(h^2) \right) \right| \leq \text{TOL}
\]
where \(\ddot{q}(t)\) is the second derivative of charge and TOL is the error tolerance.

#### 3.2 Charge Derivatives for LTE
\[
\ddot{q}_{gs} = \frac{d^2 Q_{gs}}{dt^2} \approx \frac{Q_{gs}(t) - 2Q_{gs}(t-h) + Q_{gs}(t-2h)}{h^2}
\]

#### 3.3 Adaptive Time-Step Control
\[
h_{new} = h_{current} \cdot \min\left( \text{CKTtrtol}, \sqrt{\frac{\text{TOL}}{\max(\epsilon_{LTE}, \epsilon_{min})}} \right)
\]
where \(\text{CKTtrtol} = 7\) (default truncation error tolerance factor).

### 4. Convergence Analysis

#### 4.1 Newton-Raphson Update Criteria
\[
\Delta V^{(k)} = -J^{-1}(V^{(k)}) \cdot F(V^{(k)})
\]
where \(J\) is the 6×6 Jacobian matrix and \(F\) is the nodal KCL residual vector.

#### 4.2 Voltage Convergence Test
\[
|V_{gs}^{(k)} - V_{gs}^{(k-1)}| \leq \max(\text{CKTreltol} \cdot |V_{gs}^{(k)}|, \text{CKTvoltTol})
\]
\[
|V_{ds}^{(k)} - V_{ds}^{(k-1)}| \leq \max(\text{CKTreltol} \cdot |V_{ds}^{(k)}|, \text{CKTvoltTol})
\]
with \(\text{CKTreltol} = 0.001\) and \(\text{CKTvoltTol} = 1 \times 10^{-6} \text{V}\).

#### 4.3 Current Convergence Test
\[
|I_{ds}^{(k)} - I_{ds}^{(k-1)}| \leq \max(\text{CKTreltol} \cdot |I_{ds}^{(k)}|, \text{CKTcurTol})
\]
with \(\text{CKTcurTol} = 1 \times 10^{-12} \text{A}\).

#### 4.4 Charge Conservation Test
\[
|Q_{total}^{(k)} - Q_{total}^{(k-1)}| \leq \max(\text{CKTreltol} \cdot |Q_{total}^{(k)}|, \text{CKTchgTol})
\]
where \(Q_{total} = Q_{gs} + Q_{gd} + Q_{gb}\).

#### 4.5 Source-Drain Swap Condition
For PMOS devices or when \(V_{ds} < 0\):
\[
V_{gs}' = V_{gd}, \quad V_{ds}' = -V_{ds}, \quad V_{bs}' = V_{bd}
\]
\[
I_{ds}' = -I_{ds}, \quad g_m' = -g_m, \quad g_{ds}' = g_{ds}
\]

## C Implementation

### 1. Core Data Structures

#### 1.1 Model Parameters Structure (`mos6defs.h`)
```c
typedef struct sMOS6model {
    int MOS6type;                  /* N-type or P-type */
    double MOS6vto;                /* VTO: Zero-bias threshold voltage */
    double MOS6kv;                 /* KV: Saturation region coefficient */
    double MOS6nv;                 /* NV: Saturation region exponent */
    double MOS6kc;                 /* KC: Linear region coefficient */
    double MOS6nc;                 /* NC: Linear region exponent */
    double MOS6alpha;              /* ALPHA: Smoothing parameter */
    double MOS6lambda;             /* LAMBDA: Channel-length modulation */
    double MOS6gamma;              /* GAMMA: Body-effect coefficient */
    double MOS6phi;                /* PHI: Surface potential */
    double MOS6eta;                /* ETA: DIBL coefficient */
    double MOS6cox;                /* COX: Gate oxide capacitance */
    double MOS6cgso;               /* CGSO: Gate-source overlap cap */
    double MOS6cgdo;               /* CGDO: Gate-drain overlap cap */
    double MOS6cgbo;               /* CGBO: Gate-bulk overlap cap */
    double MOS6cj;                 /* CJ: Junction capacitance */
    double MOS6pb;                 /* PB: Junction built-in potential */
    double MOS6mj;                 /* MJ: Junction grading coefficient */
    double MOS6fc;                 /* FC: Forward bias coefficient */
    struct sMOS6model *MOS6nextModel; /* Linked list pointer */
    MOS6instance *MOS6instances;   /* Instance list */
} MOS6model;
```

#### 1.2 Instance Structure (`mos6defs.h`)
```c
typedef struct sMOS6instance {
    int MOS6dNode;                 /* Drain node number */
    int MOS6gNode;                 /* Gate node number */
    int MOS6sNode;                 /* Source node number */
    int MOS6bNode;                 /* Bulk node number */
    int MOS6dNodePrime;            /* Internal drain node */
    int MOS6sNodePrime;            /* Internal source node */
    
    /* Operating point variables */
    double MOS6vgs;                /* Gate-source voltage */
    double MOS6vds;                /* Drain-source voltage */
    double MOS6vbs;                /* Bulk-source voltage */
    double MOS6ids;                /* Drain current */
    double MOS6gm;                 /* Transconductance */
    double MOS6gds;                /* Drain conductance */
    double MOS6gmb;                /* Bulk transconductance */
    
    /* Charge storage */
    double MOS6qgs;                /* Gate-source charge */
    double MOS6qgd;                /* Gate-drain charge */
    double MOS6qgb;                /* Gate-bulk charge */
    double MOS6cgs;                /* Gate-source capacitance */
    double MOS6cgd;                /* Gate-drain capacitance */
    double MOS6cgb;                /* Gate-bulk capacitance */
    
    /* Matrix pointers */
    double *MOS6drainDrainPtr;     /* G_dd */
    double *MOS6drainGatePtr;      /* G_dg */
    double *MOS6drainSourcePtr;    /* G_ds */
    double *MOS6drainBulkPtr;      /* G_db */
    double *MOS6gateDrainPtr;      /* G_gd */
    double *MOS6gateGatePtr;       /* G_gg */
    double *MOS6gateSourcePtr;     /* G_gs */
    double *MOS6gateBulkPtr;       /* G_gb */
    double *MOS6sourceDrainPtr;    /* G_sd */
    double *MOS6sourceGatePtr;     /* G_sg */
    double *MOS6sourceSourcePtr;   /* G_ss */
    double *MOS6sourceBulkPtr;     /* G_sb */
    double *MOS6bulkDrainPtr;      /* G_bd */
    double *MOS6bulkGatePtr;       /* G_bg */
    double *MOS6bulkSourcePtr;     /* G_bs */
    double *MOS6bulkBulkPtr;       /* G_bb */
    
    /* State vector indices */
    int MOS6qgsState;              /* State index for Qgs */
    int MOS6qgdState;              /* State index for Qgd */
    int MOS6qgbState;              /* State index for Qgb */
    
    struct sMOS6instance *MOS6nextInstance; /* Linked list */
} MOS6instance;
```

### 2. Matrix Setup Implementation (`mos6set.c`)

#### 2.1 Node Allocation and Matrix Pointer Setup
```c
int MOS6setup(MOS6model *model, CKTcircuit *ckt)
{
    MOS6instance *here;
    MOS6model *mod;
    
    /* Allocate 6x6 sparse matrix entries */
    for (mod = model; mod != NULL; mod = mod->MOS6nextModel) {
        for (here = mod->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
            /* External nodes: D(0), G(1), S(2), B(3) */
            /* Internal nodes: D'(4), S'(5) */
            
            /* Allocate matrix pointers for 6-terminal device */
            SMPmakeElt(ckt, here->MOS6dNode, here->MOS6dNodePrime, 
                      &here->MOS6drainDrainPtr);
            SMPmakeElt(ckt, here->MOS6dNode, here->MOS6gNode, 
                      &here->MOS6drainGatePtr);
            /* ... allocate all 36 possible entries (exploiting symmetry) */
            
            /* Allocate state vector entries for charges */
            if (ckt->CKTstates[0] != NULL) {
                here->MOS6qgsState = *(ckt->CKTstate0 + 0);
                here->MOS6qgdState = *(ckt->CKTstate0 + 1);
                here->MOS6qgbState = *(ckt->CKTstate0 + 2);
            }
        }
    }
    return OK;
}
```

#### 2.2 Matrix Stamping Pattern
The 6×6 conductance matrix follows this structure:
```
[ D  D' G  S' S  B ]   (rows/columns)
[D   Gdd Gd'd Gdg Gd's Gds Gdb]
[D'  Gd'd Gd'd' Gd'g Gd's' Gd's Gd'b]
[G   Ggd Gg'd Ggg Gg's Ggs Ggb]
[S'  Gs'd Gs'd' Gs'g Gs's' Gs's Gs'b]
[S   Gsd Gs'd Gsg Gs's Gss Gsb]
[B   Gbd Gb'd Gbg Gb's Gbs Gbb]
```

### 3. Transient Analysis Implementation (`mos6trun.c`)

#### 3.1 Local Truncation Error Calculation
```c
int MOS6trunc(MOS6instance *here, CKTcircuit *ckt, double *timeStep)
{
    double h1, h2, h3;
    double qgs1, qgs2, qgs3;
    double LTEgs, LTEgd, LTEgb, LTEtotal;
    
    /* Get previous charge values from state vector */
    qgs1 = *(ckt->CKTstate1 + here->MOS6qgsState); /* t-h */
    qgs2 = *(ckt->CKTstate2 + here->MOS6qgsState); /* t-2h */
    qgs3 = *(ckt->CKTstate3 + here->MOS6qgsState); /* t-3h */
    
    /* Calculate second derivative using backward differences */
    h1 = ckt->CKTdeltaOld[0];
    h2 = ckt->CKTdeltaOld[1];
    
    /* Second derivative approximation */
    double qddot = (here->MOS6qgs - 2*qgs1 + qgs2) / (h1*h1);
    
    /* LTE bound calculation */
    LTEgs = fabs(h1 * (qddot + h1/3.0 * (qgs1 - 2*qgs2 + qgs3)/(h2*h2)));
    
    /* Repeat for Qgd and Qgb */
    LTEgd = ...;
    LTEgb = ...;
    
    /* Combined LTE */
    LTEtotal = sqrt(LTEgs*LTEgs + LTEgd*LTEgd + LTEgb*LTEgb);
    
    /* Time-step suggestion */
    if (LTEtotal > ckt->CKTtrtol * ckt->CKTabstol) {
        *timeStep = *timeStep * sqrt(ckt->CKTabstol / LTEtotal);
    }
    
    return OK;
}
```

#### 3.2 Charge Conservation Check
```c
int MOS6chargeCheck(MOS6instance *here, CKTcircuit *ckt)
{
    double qtotal_new, qtotal_old, qerror;
    
    qtotal_new = here->MOS6qgs + here->MOS6qgd + here->MOS6qgb;
    qtotal_old = *(ckt->CKTstate1 + here->MOS6qgsState) +
                 *(ckt->CKTstate1 + here->MOS6qgdState) +
                 *(ckt->CKTstate1 + here->MOS6qgbState);
    
    qerror = fabs(qtotal_new - qtotal_old);
    
    if (qerror > max(ckt->CKTreltol * fabs(qtotal_new), ckt->CKTchgTol)) {
        ckt->CKTnoncon++;
        return E_NOT_CONVERGED;
    }
    
    return OK;
}
```

### 4. Convergence Testing Implementation (`mos6conv.c`)

#### 4.1 Voltage and Current Convergence Check
```c
int MOS6convTest(MOS6instance *here, CKTcircuit *ckt)
{
    double vgs_old, vds_old, vbs_old;
    double ids_old;
    double delvgs, delvds, delvbs, delids;
    int converged = 1;
    
    /* Get previous iteration values */
    vgs_old = here->MOS6vgs_old;
    vds_old = here->MOS6vds_old;
    vbs_old = here->MOS6vbs_old;
    ids_old = here->MOS6ids_old;
    
    /* Calculate changes */
    delvgs = here->MOS6vgs - vgs_old;
    delvds = here->MOS6vds - vds_old;
    delvbs = here->MOS6vbs - vbs_old;
    delids = here->MOS6ids - ids_old;
    
    /* Voltage convergence test */
    if (fabs(delvgs) > max(ckt->CKTreltol * fabs(here->MOS6vgs), ckt->CKTvoltTol)) {
        converged = 0;
    }
    if (fabs(delvds) > max(ckt->CKTreltol * fabs(here->MOS6vds), ckt->CKTvoltTol)) {
        converged = 0;
    }
    if (fabs(delvbs) > max(ckt->CKTreltol * fabs(here->MOS6vbs), ckt->CKTvoltTol)) {
        converged = 0;
    }
    
    /* Current convergence test */
    if (fabs(delids) > max(ckt->CKTreltol * fabs(here->MOS6ids), ckt->CKTcurTol)) {
        converged = 0;
    }
    
    /* Update old values for next iteration */
    here->MOS6vgs_old = here->MOS6vgs;
    here->MOS6vds_old = here->MOS6vds;
    here->MOS6vbs_old = here->MOS6vbs;
    here->MOS6ids_old = here->MOS6ids;
    
    return converged ? OK : E_NOT_CONVERGED;
}
```

#### 4.2 Newton-Raphson Voltage Limiting
```c
double DEVfetlim(double vnew, double vold, MOS6instance *here)
{
    double vt, vtox, delv, vmax, vmin;
    
    vt = here->MOS6vt;  /* Thermal voltage kT/q */
    vtox = here->MOS6vto;  /* Threshold voltage */
    
    /* Calculate maximum allowable change */
    if (vold > vtox) {
        vmax = vold + 2.0;  /* Empirical limit */
        vmin = vold - 0.5;
    } else {
        vmax = vold + 0.5;
        vmin = vold - 2.0;
    }
    
    /* Apply limiting */
    if (vnew > vmax) {
        vnew = vmax + vt * log(1.0 + (vnew - vmax)/vt);
    } else if (vnew < vmin) {
        vnew = vmin - vt * log(1.0 + (vmin - vnew)/vt);
    }
    
    return vnew;
}
```

### 5. Initial Conditions Implementation (`mos6ic.c`)

#### 5.1 DC Operating Point Calculation
```c
int MOS6ic(MOS6instance *here, CKTcircuit *ckt)
{
    double vgs, vds, vbs;
    double vth, vgsteff, vdsat, ids;
    
    /* Get initial voltages from nodes */
    vgs = ckt->CKTrhsOld[here->MOS6gNode] - ckt->CKTrhsOld[here->MOS6sNode];
    vds = ckt->CKTrhsOld[here->MOS6dNode] - ckt->CKTrhsOld[here->MOS6sNode];
    vbs = ckt->CKTrhsOld[here->MOS6bNode] - ckt->CKTrhsOld[here->MOS6sNode];
    
    /* Calculate threshold voltage */
    vth = here->MOS6vto + 
          here->MOS6gamma * (sqrt(2*here->MOS6phi + vbs) - sqrt(2*here->MOS6phi)) +
          here->MOS6eta * vds;
    
    /* Apply voltage limiting */
    vgsteff = DEVfetlim(vgs - vth, 0.0, here);
    
    /* Calculate saturation voltage */
    if (here->MOS6nv != here->MOS6nc) {
        vdsat = pow(here->MOS6kv/here->MOS6kc, 1.0/(here->MOS6nv - here->MOS6nc)) *
                pow(vgsteff, (here->MOS6nc - 1.0)/(here->MOS6nv - here->MOS6nc));
    } else {
        vdsat = vgsteff;  /* Simplified case */
    }
    
    /* Calculate drain current */
    if (vds < vdsat) {
        /* Linear region */
        ids = here->MOS6kc * pow(vgsteff, here->MOS6nc) * vds * 
              (1.0 + here->MOS6lambda * vds);
    } else {
        /* Saturation region */
        ids = here->MOS6kv * pow(vgsteff, here->MOS6nv) * 
              (1.0 + here->MOS6lambda * vds);
    }
    
    /* Apply smoothing function */
    if (here->MOS6alpha > 0) {
        double ratio = vds / vdsat;
        ids = ids / pow(1.0 + pow(ratio, here->MOS6alpha), 1.0/here->MOS6alpha);
    }
    
    /* Store initial conditions */
    here->MOS6vgs = vgs;
    here->MOS6vds = vds;
    here->MOS6vbs = vbs;
    here->MOS6ids = ids;
    
    /* Initialize old values for convergence testing */
    here->MOS6vgs_old = vgs;
    here->MOS6vds_old = vds;
    here->MOS6vbs_old = vbs;
    here->MOS6ids_old = ids;
    
    return OK;
}
```

### 6. Temperature Scaling Implementation (`mos6temp.c`)

#### 6.1 Parameter Temperature Dependence
```c
int MOS6temperature(MOS6model *model, CKTcircuit *ckt)
{
    MOS6model *mod;
    MOS6instance *here;
    double tnom, temp, ratio, vt;
    
    tnom = ckt->CKTnomTemp;
    temp = ckt->CKTtemp;
    
    /* Thermal voltage scaling */
    vt = 8.617333262e-5 * temp;  /* kT/q */
    
    for (mod = model; mod != NULL; mod = mod->MOS6nextModel) {
        /* Temperature scaling of threshold voltage */
        mod->MOS6vto = mod->MOS6vto * (1.0 + mod->MOS6tc1*(temp - tnom) + 
                                       mod->MOS6tc2*(temp - tnom)*(temp - tnom));
        
        /* Mobility temperature dependence */
        mod->MOS6kv = mod->MOS6kv * pow(temp/tnom, -mod->MOS6uexp);
        mod->MOS6kc = mod->MOS6kc * pow(temp/tnom, -mod->MOS6uexp);
        
        /* Junction capacitance temperature scaling */
        mod->MOS6cj = mod->MOS6cj * (1.0 + mod->MOS6tcc*(temp - tnom));
        mod->MOS6pb = mod->MOS6pb * (1.0 + mod->MOS6tcp*(temp - tnom));
        
        for (here = mod->MOS6instances; here != NULL; here = here->MOS6nextInstance) {
            here->MOS6vt = vt;  /* Store thermal voltage */
        }
    }
    
    return OK;
}
```

### 7. SPICE Device Structure Integration

#### 7.1 SPICEdev Initialization
```c
SPICEdev MOS6info = {
    .DEVpublic = {
        .name = "MOS6",
        .description = "Sakurai-Newton alpha-power law MOSFET",
        .terms = 4,  /* D, G, S, B terminals */
        .numNames = 0,
        .termNames = NULL,
        .modType = MOS6modType,
        .flags = DEV_DEFAULT,
    },
    
    .DEVparam = MOS6param,
    .DEVmodParam = MOS6mParam,
    .DEVload = MOS6load,
    .DEVsetup = MOS6setup,
    .DEVunsetup = MOS6unsetup,
    .DEVpzSetup = MOS6pzSetup,
    .DEVtemperature = MOS6temperature,
    .DEVtrunc = MOS6trunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = MOS6acLoad,
    .DEVaccept = NULL,
    .DEVdestroy = MOS6destroy,
    .DEVmodDelete = MOS6mDelete,
    .DEVdelete = MOS6delete,
    .DEVsetic = MOS6getic,
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
    .DEVnoise = MOS6noise,
    .DEVsoaCheck = NULL,
    .DEVinstSize = sizeof(MOS6instance),
    .DEVmodSize = sizeof(MOS6model)
};
```

### 8. Error Handling and Diagnostics

#### 8.1 Convergence Failure Diagnostics
```c
void MOS6convergenceDiagnostics(MOS6instance *here, CKTcircuit *ckt)
{
    if (ckt->CKTnoncon > ckt->CKTmaxNoncon) {
        fprintf(stderr, "MOS6 Convergence Failure at Device: %s\n", here->MOS6name);
        fprintf(stderr, "  Vgs = %g V, Vds = %g V, Vbs = %g V\n", 
                here->MOS6vgs, here->MOS6vds, here->MOS6vbs);
        fprintf(stderr, "  Ids = %g A, gm = %g S, gds = %g S\n",
                here->MOS6ids, here->MOS6gm, here->MOS6gds);
        fprintf(stderr, "  Region: %s\n", 
                (here->MOS6vds < here->MOS6vdsat) ? "Linear" : "Saturation");
        
        /* Suggest corrective actions */
        if (fabs(here->MOS6vgs - here->MOS6vto) < 0.1) {
            fprintf(stderr, "  Suggestion: Increase GMIN (currently %g)\n", ckt->CKTgmin);
        }
        if (here->MOS6vds > 10.0 * here->MOS6vdsat) {
            fprintf(stderr, "  Suggestion: Reduce VDS or increase LAMBDA\n");
        }
    }
}
```

#### 8.2 Time-Step Control Validation
```c
int MOS6validateTimeStep(MOS6instance *here, CKTcircuit *ckt, double proposedStep)
{
    double vgs_slope, vds_slope;
    double max_slope, min_step;
    
    /* Calculate voltage slopes from previous steps */
    vgs_slope = fabs(here->MOS6vgs - here->MOS6vgs_old) / ckt->CKTdelta;
    vds_slope = fabs(here->MOS6vds - here->MOS6vds_old) / ckt->CKTdelta;
    
    max_slope = MAX(vgs_slope, vds_slope);
    
    /* Minimum step based on voltage change rate */
    min_step = 0.1 * ckt->CKTvoltTol / max_slope;
    
    if (proposedStep < min_step) {
        proposedStep = min_step;
        ckt->CKTstat->STATtimeStepLimits++;
    }
    
    /* Maximum step based on circuit time constants */
    if (proposedStep > 0.1 * ckt->CKTmaxStep) {
        proposedStep = 0.1 * ckt->CKTmaxStep;
    }
    
    return proposedStep;
}
```

This complete implementation demonstrates how the MOS6 model integrates into Ngspice's transient analysis framework, providing robust convergence checking and adaptive time-step control specifically tuned for the alpha-power law characteristics of digital MOSFET models.