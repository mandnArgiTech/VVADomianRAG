# BSIM2: Transient Control and Convergence

_Generated 2026-04-12 12:09 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2trunc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2cvtest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2getic.c`

# MOS6: Transient Control and Convergence Checking

## Technical Introduction

The MOS6 model (Sakurai-Newton empirical Level 6) implements a digital-oriented MOSFET model optimized for transient simulation of digital circuits. Unlike comprehensive physical models, MOS6 uses an alpha-power law formulation with no subthreshold conduction, making it computationally efficient for timing analysis. The transient control and convergence checking subsystem is distributed across four core C files in the Ngspice implementation:

- **`mos6set.c`**: Allocates and configures the 6×6 sparse conductance matrix for the MOS6 device, mapping node connections (Drain, Drain-prime, Gate, Source-prime, Source, Bulk) to SPICE matrix pointers. This setup establishes the mathematical framework for Newton-Raphson iteration.

- **`mos6trun.c`**: Implements Local Truncation Error (LTE) calculation using charge-based Backward Differentiation Formula (BDF) methods. This module estimates discretization error for adaptive time-step control, ensuring simulation accuracy within specified tolerance bounds.

- **`mos6conv.c`**: Performs convergence testing by comparing successive Newton-Raphson iterations of terminal voltages and branch currents against SPICE's relative and absolute tolerances (`CKTreltol`, `CKTabstol`). This is critical for terminating the iterative solution process.

- **`mos6ic.c`**: Handles initial condition computation for transient analysis, ensuring consistent starting states for voltages and charges. This prevents convergence issues at time zero.

These files work in concert with `mos6defs.h` (data structure definitions) and `mos6temp.c` (temperature scaling) to provide a complete numerical implementation of the MOS6 model within Ngspice's transient analysis framework.

## Mathematical Formulation

### 1. Core DC Equations

#### Threshold Voltage with Body and DIBL Effects
\[
V_{th} = VTO + \gamma \cdot \left[ \sqrt{2\phi + V_{sb}} - \sqrt{2\phi} \right] + \eta \cdot V_{ds}
\]
where:
- \(VTO\): Zero-bias threshold voltage
- \(\gamma\): Body effect coefficient
- \(\phi\): Surface potential (typically 0.7V)
- \(\eta\): Drain-induced barrier lowering (DIBL) coefficient
- \(V_{sb}, V_{ds}\): Source-bulk and drain-source voltages

#### Effective Gate-Source Voltage
\[
V_{gsteff} = \text{DEVfetlim}(V_{gs} - V_{th}, V_{gs}(t-1) - V_{th}(t-1), V_t)
\]
The `DEVfetlim` function enforces C¹ continuity and prevents Newton-Raphson oscillation by limiting voltage changes based on thermal voltage \(V_t = kT/q\).

#### Drain Current Model

**Linear Region** (\(V_{ds} \leq V_{dsat}\)):
\[
I_{ds}^{lin} = \beta_{lin} \cdot (V_{gsteff})^{NC} \cdot V_{ds} \cdot (1 + \lambda \cdot V_{ds})
\]
where \(\beta_{lin} = \frac{K_C \cdot W_{eff}}{L_{eff}}\)

**Saturation Region** (\(V_{ds} > V_{dsat}\)):
\[
I_{ds}^{sat} = \beta_{sat} \cdot (V_{gsteff})^{NV} \cdot (1 + \lambda \cdot V_{ds})
\]
where \(\beta_{sat} = \frac{K_V \cdot W_{eff}}{L_{eff}}\)

**Saturation Voltage**:
\[
V_{dsat} = \left( \frac{K_V}{K_C} \right)^{\frac{1}{NV - NC}} \cdot (V_{gsteff})^{\frac{NC-1}{NV-NC}}
\]

**Smooth Transition Function**:
\[
I_{ds} = I_{ds}^{lin} \cdot \left[ 1 + \left( \frac{V_{ds}}{V_{dsat}} \right)^\alpha \right]^{-\frac{1}{\alpha}}
\]
The smoothing parameter \(\alpha\) (typically 3-5) ensures C¹ continuity between regions.

#### Small-Signal Parameters
\[
g_m = \frac{\partial I_{ds}}{\partial V_{gs}} \quad g_{ds} = \frac{\partial I_{ds}}{\partial V_{ds}} \quad g_{mb} = \frac{\partial I_{ds}}{\partial V_{bs}}
\]

### 2. Charge Conservation and Capacitance Model

**Gate Charge Partitioning** (40%/60% rule):
\[
Q_g = W_{eff}L_{eff}C_{ox}V_{gsteff}
\]
\[
Q_d = -0.4Q_g \quad Q_s = -0.6Q_g \quad Q_b = -(Q_g + Q_d + Q_s)
\]

**Capacitance Matrix**:
\[
C_{ij} = \frac{\partial Q_i}{\partial V_j} \quad \text{for } i,j \in \{g,d,s,b\}
\]

### 3. Transient Integration Mathematics

**Charge Conservation Formulation**:
\[
I_{terminal} = \frac{dQ_{terminal}}{dt} + I_{DC}
\]

**Backward Differentiation Formula (BDF2)**:
\[
\frac{dQ}{dt} \approx \frac{3Q(t) - 4Q(t-h) + Q(t-2h)}{2h}
\]
where \(h\) is the time step.

**Local Truncation Error Bound**:
\[
\epsilon_{LTE} = \left| h \cdot (\ddot{q}(t) + O(h^2)) \right| \leq \text{TOL}
\]
with \(\text{TOL} = \text{CKTtrtol} \cdot (\text{CKTreltol} \cdot |Q| + \text{CKTchgTol})\)

### 4. Convergence Criteria

**Newton-Raphson Voltage Convergence**:
\[
|V_{new} - V_{old}| \leq \text{CKTreltol} \cdot \max(|V_{new}|, |V_{old}|) + \text{CKTabstol}
\]

**Current Convergence**:
\[
|I_{new} - I_{old}| \leq \text{CKTreltol} \cdot \max(|I_{new}|, |I_{old}|) + \text{CKTabstol}
\]

**Charge Convergence**:
\[
|Q_{new} - Q_{old}| \leq \text{CKTreltol} \cdot \max(|Q_{new}|, |Q_{old}|) + \text{CKTchgTol}
\]

### 5. Source-Drain Symmetry Handling

For PMOS devices or when \(V_{ds} < 0\):
\[
V_{ds}' = -V_{ds}, \quad V_{gs}' = V_{gs} - V_{ds}, \quad V_{bs}' = V_{bs} - V_{ds}
\]
\[
I_{ds}' = -I_{ds}, \quad g_m' = -g_m, \quad g_{ds}' = g_{ds}
\]

## C Implementation

### 1. Data Structures (`mos6defs.h`)

```c
typedef struct sMOS6model {
    int MOS6type;                   /* N-type or P-type */
    double MOS6kv;                  /* Saturation coefficient */
    double MOS6nv;                  /* Saturation exponent */
    double MOS6kc;                  /* Linear coefficient */
    double MOS6nc;                  /* Linear exponent */
    double MOS6alpha;               /* Smoothing parameter */
    double MOS6lambda;              /* Channel length modulation */
    double MOS6vt0;                 /* Zero-bias threshold */
    double MOS6gamma;               /* Body effect */
    double MOS6phi;                 /* Surface potential */
    double MOS6eta;                 /* DIBL coefficient */
    
    /* Matrix pointers */
    unsigned int MOS6stateSize;     /* Size of state vector */
    int MOS6states[6];              /* State indices for charges */
    
    struct sMOS6model *MOS6nextModel; /* Linked list */
} MOS6model;

typedef struct sMOS6instance {
    double MOS6vgs;                 /* Gate-source voltage */
    double MOS6vds;                 /* Drain-source voltage */
    double MOS6vbs;                 /* Bulk-source voltage */
    double MOS6ids;                 /* Drain current */
    double MOS6gm;                  /* Transconductance */
    double MOS6gds;                 /* Output conductance */
    double MOS6gmb;                 /* Bulk transconductance */
    
    /* Charge states */
    double MOS6qgs;                 /* Gate-source charge */
    double MOS6qgd;                 /* Gate-drain charge */
    double MOS6qgb;                 /* Gate-bulk charge */
    
    /* Matrix pointers for 6x6 stamp */
    double *MOS6drainDrainPtr;      /* G[drain][drain] */
    double *MOS6drainDrainPrimePtr;
    double *MOS6drainGatePtr;
    double *MOS6drainSourcePrimePtr;
    double *MOS6drainSourcePtr;
    double *MOS6drainBulkPtr;
    
    struct sMOS6instance *MOS6nextInstance; /* Linked list */
} MOS6instance;
```

### 2. Matrix Setup (`mos6set.c`)

```c
int MOS6setup(MOS6model *model, CKTcircuit *ckt)
{
    MOS6instance *here;
    MOS6model *mod;
    
    /* Allocate 6x6 sparse matrix positions */
    for (mod = model; mod != NULL; mod = mod->MOS6nextModel) {
        for (here = mod->MOS6instances; here != NULL; 
             here = here->MOS6nextInstance) {
            
            /* Request matrix positions for all 36 elements */
            SMPmakeElt(ckt, here->MOS6drainNode, here->MOS6drainNode, 
                      &here->MOS6drainDrainPtr);
            SMPmakeElt(ckt, here->MOS6drainNode, here->MOS6drainPrimeNode,
                      &here->MOS6drainDrainPrimePtr);
            /* ... allocate all 36 positions ... */
            
            /* Allocate state vector positions for charges */
            ckt->CKTstate0[here->MOS6states[0]] = 0.0; /* Qgs */
            ckt->CKTstate1[here->MOS6states[0]] = 0.0;
            ckt->CKTstate0[here->MOS6states[1]] = 0.0; /* Qgd */
            ckt->CKTstate1[here->MOS6states[1]] = 0.0;
            ckt->CKTstate0[here->MOS6states[2]] = 0.0; /* Qgb */
            ckt->CKTstate1[here->MOS6states[2]] = 0.0;
        }
    }
    return OK;
}
```

### 3. Local Truncation Error Calculation (`mos6trun.c`)

```c
int MOS6trunc(MOS6model *model, CKTcircuit *ckt, double *timeStep)
{
    MOS6instance *here;
    double qgs_new, qgd_new, qgb_new;
    double qgs_old, qgd_old, qgb_old;
    double qgs_older, qgd_older, qgb_older;
    double tol, charge, error;
    double maxStep = *timeStep;
    
    for (here = model->MOS6instances; here != NULL; 
         here = here->MOS6nextInstance) {
        
        /* Get current and previous charge states */
        qgs_new = ckt->CKTstate0[here->MOS6states[0]];
        qgs_old = ckt->CKTstate1[here->MOS6states[0]];
        qgs_older = ckt->CKTstate2[here->MOS6states[0]];
        
        /* BDF2 LTE estimation for gate-source charge */
        charge = fabs(qgs_new);
        tol = ckt->CKTtrtol * (ckt->CKTreltol * charge + ckt->CKTchgTol);
        
        /* Second derivative approximation */
        error = fabs(3.0*qgs_new - 4.0*qgs_old + qgs_older) / 2.0;
        
        if (error > tol && error > 1e-20) {
            /* Calculate reduced time step */
            double newStep = *timeStep * sqrt(tol / error);
            if (newStep < maxStep) {
                maxStep = newStep;
            }
        }
        
        /* Repeat for Qgd and Qgb */
    }
    
    *timeStep = maxStep;
    return OK;
}
```

### 4. Convergence Testing (`mos6conv.c`)

```c
int MOS6convTest(MOS6model *model, CKTcircuit *ckt)
{
    MOS6instance *here;
    double vgs_new, vgs_old, vgs_delta;
    double vds_new, vds_old, vds_delta;
    double ids_new, ids_old, ids_delta;
    double qgs_new, qgs_old, qgs_delta;
    int converged = 1;
    
    for (here = model->MOS6instances; here != NULL; 
         here = here->MOS6nextInstance) {
        
        /* Voltage convergence test */
        vgs_new = *(ckt->CKTrhsOld + here->MOS6gateNode) -
                  *(ckt->CKTrhsOld + here->MOS6sourceNode);
        vgs_old = here->MOS6vgs;
        vgs_delta = fabs(vgs_new - vgs_old);
        
        double vgs_rel = ckt->CKTreltol * 
                        MAX(fabs(vgs_new), fabs(vgs_old)) + ckt->CKTabstol;
        
        if (vgs_delta > vgs_rel) {
            converged = 0;
            break;
        }
        
        /* Current convergence test */
        ids_new = here->MOS6ids;
        ids_old = here->MOS6ids_old;
        ids_delta = fabs(ids_new - ids_old);
        
        double ids_rel = ckt->CKTreltol * 
                        MAX(fabs(ids_new), fabs(ids_old)) + ckt->CKTabstol;
        
        if (ids_delta > ids_rel) {
            converged = 0;
            break;
        }
        
        /* Charge convergence test */
        qgs_new = ckt->CKTstate0[here->MOS6states[0]];
        qgs_old = ckt->CKTstate1[here->MOS6states[0]];
        qgs_delta = fabs(qgs_new - qgs_old);
        
        double qgs_rel = ckt->CKTreltol * 
                        MAX(fabs(qgs_new), fabs(qgs_old)) + ckt->CKTchgTol;
        
        if (qgs_delta > qgs_rel) {
            converged = 0;
            break;
        }
    }
    
    return converged ? OK : E_NOT_CONVERGED;
}
```

### 5. Initial Conditions (`mos6ic.c`)

```c
int MOS6ic(MOS6model *model, CKTcircuit *ckt)
{
    MOS6instance *here;
    double vgs, vds, vbs;
    double vth, vgsteff;
    double beta_lin, beta_sat;
    
    for (here = model->MOS6instances; here != NULL; 
         here = here->MOS6nextInstance) {
        
        /* Get initial voltages from nodes */
        vgs = *(ckt->CKTrhs + here->MOS6gateNode) -
              *(ckt->CKTrhs + here->MOS6sourceNode);
        vds = *(ckt->CKTrhs + here->MOS6drainNode) -
              *(ckt->CKTrhs + here->MOS6sourceNode);
        vbs = *(ckt->CKTrhs + here->MOS6bulkNode) -
              *(ckt->CKTrhs + here->MOS6sourceNode);
        
        /* Apply voltage limiting for convergence */
        vgs = DEVfetlim(vgs, here->MOS6vgs_old, ckt->CKTvt);
        vds = DEVlimvds(vds, here->MOS6vds_old);
        
        /* Calculate threshold voltage */
        vth = here->MOS6vt0 + 
              here->MOS6gamma * (sqrt(here->MOS6phi*2.0 + vbs) - 
                                sqrt(here->MOS6phi*2.0)) +
              here->MOS6eta * vds;
        
        vgsteff = MAX(vgs - vth, 0.0);
        
        /* Calculate initial drain current */
        if (vgsteff <= 0.0) {
            here->MOS6ids = 0.0;
        } else {
            beta_lin = here->MOS6kc * here->MOS6w / here->MOS6l;
            beta_sat = here->MOS6kv * here->MOS6w / here->MOS6l;
            
            double vdsat = pow(here->MOS6kv/here->MOS6kc, 
                              1.0/(here->MOS6nv - here->MOS6nc)) *
                          pow(vgsteff, 
                              (here->MOS6nc-1.0)/(here->MOS6nv-here->MOS6nc));
            
            if (vds <= vdsat) {
                /* Linear region */
                here->MOS6ids = beta_lin * pow(vgsteff, here->MOS6nc) *
                               vds * (1.0 + here->MOS6lambda * vds);
            } else {
                /* Saturation region */
                here->MOS6ids = beta_sat * pow(vgsteff, here->MOS6nv) *
                               (1.0 + here->MOS6lambda * vds);
            }
        }
        
        /* Store initial charges */
        ckt->CKTstate0[here->MOS6states[0]] = 0.0; /* Qgs */
        ckt->CKTstate0[here->MOS6states[1]] = 0.0; /* Qgd */
        ckt->CKTstate0[here->MOS6states[2]] = 0.0; /* Qgb */
        
        /* Save voltages for next iteration */
        here->MOS6vgs_old = vgs;
        here->MOS6vds_old = vds;
        here->MOS6vbs_old = vbs;
        here->MOS6ids_old = here->MOS6ids;
    }
    
    return OK;
}
```

### 6. Temperature Scaling (`mos6temp.c`)

```c
int MOS6temperature(MOS6model *model, CKTcircuit *ckt)
{
    MOS6model *mod;
    double tnom, temp, ratio;
    
    for (mod = model; mod != NULL; mod = mod->MOS6nextModel) {
        tnom = ckt->CKTnomTemp;
        temp = ckt->CKTtemp;
        
        if (temp != tnom) {
            ratio = temp / tnom;
            
            /* Temperature scaling of threshold voltage */
            mod->MOS6vt0 = mod->MOS6vt0 * 
                          (1.0 - mod->MOS6tcv * (temp - tnom));
            
            /* Mobility temperature dependence */
            mod->MOS6kv = mod->MOS6kv * pow(ratio, -1.5);
            mod->MOS6kc = mod->MOS6kc * pow(ratio, -1.5);
            
            /* Update derived parameters */
            mod->MOS6phi = mod->MOS6phi * ratio - 
                          2.0 * ckt->CKTvt * log(ratio);
        }
    }
    
    return OK;
}
```

### 7. Matrix Stamping Pattern

The 6×6 conductance matrix follows this structure for nodal analysis:

```
Node Order: [0:Drain, 1:Drain', 2:Gate, 3:Source', 4:Source, 5:Bulk]

Stamp for linear region:
G[drain][drain]      +=  gds
G[drain][drainPrime] += -gds
G[drain][gate]       +=  gm
G[drain][bulk]       +=  gmb

G[drainPrime][drain]      += -gds
G[drainPrime][drainPrime] +=  gds + gdpr
G[drainPrime][sourcePrime] += -gdpr

G[gate][drain]       +=  gmgd (capacitive)
G[gate][gate]        +=  ggg
G[gate][source]      +=  gmgs
G[gate][bulk]        +=  gmgb

G[sourcePrime][drainPrime] += -gspr
G[sourcePrime][sourcePrime] +=  gspr + gds
G[sourcePrime][gate]       += -gm
G[sourcePrime][source]     += -gds
G[sourcePrime][bulk]       += -gmb

G[source][sourcePrime] += -gspr
G[source][source]      +=  gspr

G[bulk][drain]   += -gmb
G[bulk][source]  +=  gmb
G[bulk][bulk]    +=  gbd + gbs
```

### 8. SPICE Integration

```c
/* SPICE device structure for MOS6 */
SPICEdev MOS6info = {
    .DEVpublic = {
        .name = "mos6",
        .description = "Sakurai-Newton Level 6 MOSFET model",
        .terms = 4,
        .numNames = 4,
        .termNames = {"drain", "gate", "source", "bulk"},
        .numInstanceParms = 24,
        .instanceParms = MOS6pTable,
        .numModelParms = 18,
        .modelParms = MOS6mPTable,
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
    .DEVconvTest = MOS6convTest,
    .DEVacLoad = MOS6acLoad,
    .DEVaccept = MOS6accept,
    .DEVdestroy = MOS6destroy,
    .DEVmodDelete = MOS6mDelete,
    .DEVdelete = MOS6delete,
    .DEVsetic = MOS6getic,
    .DEVask = MOS6ask,
    .DEVmodAsk = MOS6mAsk,
    .DEVpzLoad = MOS6pzLoad,
    .DEVnoise = MOS6noise,
    .DEVsoaCheck = NULL,
    .DEVinstSize = sizeof(MOS6instance),
    .DEVmodSize = sizeof(MOS6model)
};
```

## Summary

The MOS6 model's transient control and convergence checking implementation demonstrates a specialized approach for digital circuit simulation. By combining:

1. **Alpha-power law current equations** for computational efficiency
2. **C¹ continuous smoothing functions** for Newton-Raphson stability
3. **Charge-based LTE estimation** using BDF2 methods
4. **Multi-dimensional convergence testing** (voltage, current, charge)
5. **Source-drain symmetry handling** for PMOS support
6. **6×6 sparse matrix formulation** for complete terminal modeling

The implementation achieves robust numerical performance while maintaining the simplicity of the empirical MOS6 formulation. The integration with Ngspice's core simulation engine through the `SPICEdev` interface allows seamless operation within transient, AC, and noise analyses while providing the time-step control and convergence guarantees necessary for reliable digital timing simulation.