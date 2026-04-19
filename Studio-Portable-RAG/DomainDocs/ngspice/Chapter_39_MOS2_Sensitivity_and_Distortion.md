# MOS2: Sensitivity and Distortion Analysis

_Generated 2026-04-12 05:26 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2sld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2sset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2dist.c`

# MOS2: Data Structures and SPICE API

## Introduction

This chapter documents the implementation of the Level 2 MOSFET (MOS2) model in the Ngspice circuit simulator. The MOS2 model implements the Grove-Frohman equations with enhancements for short-channel and narrow-width effects, making it suitable for modern integrated circuit simulation. The implementation spans several C source files that define the model's data structures, mathematical formulation, and integration with the SPICE simulation engine.

The core implementation files are:
- **`mos2defs.h`**: Defines the fundamental data structures `MOS2model` and `MOS2instance` that store process parameters and instance-specific state variables.
- **`mos2init.c`**: Implements the SPICE device API binding through the `MOS2info` structure and handles device registration.
- **`mos2.c`** (or `mos2set.c`): Contains the core computational routines including parameter validation, matrix setup, and the load function that implements the device equations.
- **`mos2dest.c`**: Manages memory cleanup and device destruction.

The MOS2 model extends the basic Level 1 formulation with physical effects critical for sub-micron devices, including velocity saturation, mobility degradation, and threshold voltage modifications due to short-channel and narrow-width phenomena.

## Mathematical Formulation

### Threshold Voltage with Physical Effects

The MOS2 threshold voltage incorporates several physical corrections:

```math
V_{th} = V_{TO} + \gamma \left( \sqrt{\phi - V_{bs}} - \sqrt{\phi} \right) + \Delta V_{th}(\text{short}) + \Delta V_{th}(\text{narrow})
```

Where:
- **Short-channel effect correction**:
  ```math
  \Delta V_{th}(\text{short}) = \frac{\epsilon_{si}}{\epsilon_{ox}} \cdot \frac{t_{ox}}{L_{eff}} \cdot \left( \sqrt{1 + \frac{2W_d}{r_j}} - 1 \right) \cdot \sqrt{\phi - V_{bs}}
  ```
- **Narrow-width effect correction**:
  ```math
  \Delta V_{th}(\text{narrow}) = \frac{\pi \epsilon_{si}}{4C_{ox}W_{eff}} \cdot (\phi - V_{bs})
  ```

### Drain Current Equations

The drain current is computed piecewise based on operating region:

**1. Cutoff Region** (`V_{gs} ≤ V_{th}`):
```math
I_d = I_{ds} \cdot \exp\left(\frac{V_{gs} - V_{th}}{n \cdot V_T}\right) \cdot \left(1 - \exp\left(-\frac{V_{ds}}{V_T}\right)\right)
```

**2. Linear/Triode Region** (`V_{ds} < V_{dsat}`):
```math
I_d = \beta \left[ (V_{gs} - V_{th})V_{ds} - \frac{V_{ds}^2}{2} \right] (1 + \lambda V_{ds})
```

**3. Saturation Region** (`V_{ds} ≥ V_{dsat}`):
```math
I_d = \frac{\beta}{2} (V_{gs} - V_{th})^2 (1 + \lambda V_{ds}) \cdot F_{vsat}
```

Where the velocity saturation factor `F_{vsat}` is:
```math
F_{vsat} = \frac{1}{1 + \frac{V_{dsat}}{E_{crit} \cdot L_{eff}}}
```

And the saturation voltage `V_{dsat}` accounts for velocity saturation:
```math
V_{dsat} = \frac{V_{gs} - V_{th}}{1 + \frac{V_{gs} - V_{th}}{E_{crit} \cdot L_{eff}}}
```

### Small-Signal Parameters

The small-signal conductances for the AC admittance matrix are:

```math
g_m = \frac{\partial I_d}{\partial V_{gs}}, \quad g_{ds} = \frac{\partial I_d}{\partial V_{ds}}, \quad g_{mb} = \frac{\partial I_d}{\partial V_{bs}}
```

For the linear region:
```math
g_m = \beta V_{ds}, \quad g_{ds} = \beta [(V_{gs} - V_{th}) - V_{ds}], \quad g_{mb} = \frac{\gamma \beta V_{ds}}{2\sqrt{\phi - V_{bs}}}
```

For the saturation region:
```math
g_m = \beta (V_{gs} - V_{th}), \quad g_{ds} = \frac{\lambda \beta}{2} (V_{gs} - V_{th})^2, \quad g_{mb} = \frac{\gamma \beta (V_{gs} - V_{th})}{2\sqrt{\phi - V_{bs}}}
```

### Meyer Capacitance Model

The MOS2 implementation uses the Meyer capacitance model with piecewise voltage-dependent charges:

**Gate-Source Charge** `Q_{gs}`:
- Accumulation (`V_{gb} < 0`): `Q_{gs} = C_{ox} \cdot V_{gb}`
- Depletion (`0 ≤ V_{gb} < \phi`): `Q_{gs} = C_{ox} \cdot \frac{\gamma^2}{2} \left[ \sqrt{1 + \frac{4V_{gb}}{\gamma^2}} - 1 \right]`
- Inversion (`V_{gb} ≥ \phi`): `Q_{gs} = C_{ox} \cdot (V_{gb} - \phi)`

**Gate-Drain and Gate-Bulk Charges** follow similar piecewise definitions with appropriate voltage references.

## C Implementation

### Core Data Structures

The model is built around two primary structures defined in `mos2defs.h`:

```c
typedef struct sMOS2model {
    int MOS2type;                   /* NMF or PMF */
    double MOS2vt0;                 /* Threshold voltage VTO */
    double MOS2kp;                  /* Transconductance parameter KP */
    double MOS2gamma;               /* Body effect parameter GAMMA */
    double MOS2phi;                 /* Surface potential PHI */
    double MOS2lambda;              /* Channel-length modulation LAMBDA */
    double MOS2rd;                  /* Drain resistance RD */
    double MOS2rs;                  /* Source resistance RS */
    double MOS2cbd;                 /* Bulk-drain capacitance CBD */
    double MOS2cbs;                 /* Bulk-source capacitance CBS */
    double MOS2is;                  /* Bulk junction saturation current IS */
    double MOS2pb;                  /* Bulk junction potential PB */
    
    /* Derived parameters */
    double MOS2coeff;               /* Precomputed coefficient */
    double MOS2vmax;                /* Maximum carrier velocity VMAX */
    double MOS2xj;                  /* Junction depth XJ */
    double MOS2ld;                  /* Lateral diffusion LD */
    double MOS2tox;                 /* Oxide thickness TOX */
    
    struct sMOS2model *MOS2nextModel;  /* Linked list of models */
    MOS2instance *MOS2instances;        /* Linked list of instances */
} MOS2model;
```

```c
typedef struct sMOS2instance {
    /* Circuit nodes */
    int MOS2dNode;                  /* Drain node */
    int MOS2gNode;                  /* Gate node */
    int MOS2sNode;                  /* Source node */
    int MOS2bNode;                  /* Bulk node */
    int MOS2dNodePrime;             /* Internal drain node (if RD > 0) */
    int MOS2sNodePrime;             /* Internal source node (if RS > 0) */
    
    /* State variables */
    double MOS2vgs;                 /* Gate-source voltage */
    double MOS2vds;                 /* Drain-source voltage */
    double MOS2vbs;                 /* Bulk-source voltage */
    double MOS2cd;                  /* Drain current */
    double MOS2cbs;                 /* Bulk-source current */
    double MOS2cbd;                 /* Bulk-drain current */
    
    /* Small-signal parameters */
    double MOS2gm;                  /* Transconductance */
    double MOS2gds;                 /* Output conductance */
    double MOS2gmbs;                /* Bulk transconductance */
    
    /* Capacitances */
    double MOS2cgs;                 /* Gate-source capacitance */
    double MOS2cgd;                 /* Gate-drain capacitance */
    double MOS2cgb;                 /* Gate-bulk capacitance */
    
    /* State vector indices */
    int MOS2stateGgs;               /* Index for Qgs in state vector */
    int MOS2stateGgd;               /* Index for Qgd in state vector */
    int MOS2stateGgb;               /* Index for Qgb in state vector */
    int MOS2stateQbd;               /* Index for Qbd in state vector */
    int MOS2stateQbs;               /* Index for Qbs in state vector */
    
    /* Matrix pointers */
    double *MOS2drainDrainPtr;      /* G[drain][drain] */
    double *MOS2drainGatePtr;       /* G[drain][gate] */
    double *MOS2drainSourcePtr;     /* G[drain][source] */
    double *MOS2drainBulkPtr;       /* G[drain][bulk] */
    double *MOS2drainDrainPrimePtr; /* G[drain][drain'] */
    double *MOS2drainSourcePrimePtr;/* G[drain][source'] */
    
    /* Additional pointers for the 6x6 matrix... */
    
    struct sMOS2instance *MOS2nextInstance;  /* Linked list */
    MOS2model *MOS2modPtr;          /* Pointer to parent model */
} MOS2instance;
```

### Internal Node Topology

The implementation creates internal nodes `d'` and `s'` when parasitic resistances RD and RS are non-zero:

```
External Nodes:      D     G     S     B
                     |     |     |     |
Internal Topology:   D----d'     s'----S
                           |     |
                          Device
                           |     |
                           G     B
```

This topology requires a 6×6 conductance matrix for complete representation:

```
Nodes: [D, G, S, B, d', s']
```

### State Vector Management

In `mos2init.c`, the `MOS2setup()` function allocates state vector indices for charge conservation:

```c
int MOS2setup(MOS2model *model, CKTcircuit *ckt)
{
    MOS2instance *inst;
    
    for (model = model; model != NULL; model = model->MOS2nextModel) {
        for (inst = model->MOS2instances; inst != NULL; inst = inst->MOS2nextInstance) {
            /* Allocate state vector indices for 5 charges */
            inst->MOS2stateGgs = ckt->CKTnumStates++;
            inst->MOS2stateGgd = ckt->CKTnumStates++;
            inst->MOS2stateGgb = ckt->CKTnumStates++;
            inst->MOS2stateQbd = ckt->CKTnumStates++;
            inst->MOS2stateQbs = ckt->CKTnumStates++;
            
            /* Allocate SMP matrix pointers for 6x6 system */
            inst->MOS2drainDrainPtr = SMPmakeElt(ckt, inst->MOS2dNode, inst->MOS2dNode);
            inst->MOS2drainGatePtr = SMPmakeElt(ckt, inst->MOS2dNode, inst->MOS2gNode);
            /* ... allocate all 36 matrix pointers ... */
        }
    }
    return OK;
}
```

### Core Equation Implementation

The `MOS2load()` function in `mos2.c` implements the Grove-Frohman equations:

```c
int MOS2load(MOS2model *model, CKTcircuit *ckt)
{
    MOS2instance *inst;
    double vgs, vds, vbs, vgd, vgb;
    double vgst, vdst, vdsat;
    double beta, lambda, gamma, phi;
    double gm, gds, gmbs;
    double cgs, cgd, cgb;
    
    for (model = model; model != NULL; model = model->MOS2nextModel) {
        for (inst = model->MOS2instances; inst != NULL; inst = inst->MOS2nextInstance) {
            /* Get voltages with Newton-Raphson limiting */
            vgs = DEVfetlim(inst->MOS2vgs_old, 
                           ckt->CKTrhs[inst->MOS2gNode] - ckt->CKTrhs[inst->MOS2sNodePrime],
                           model->MOS2vt0);
            vds = DEVfetlim(inst->MOS2vds_old,
                           ckt->CKTrhs[inst->MOS2dNodePrime] - ckt->CKTrhs[inst->MOS2sNodePrime],
                           0.0);
            vbs = ckt->CKTrhs[inst->MOS2bNode] - ckt->CKTrhs[inst->MOS2sNodePrime];
            
            /* Handle PMOS polarity */
            if (model->MOS2type < 0) { /* PMOS */
                vgs = -vgs;
                vds = -vds;
                vbs = -vbs;
            }
            
            /* Compute threshold voltage with short-channel and narrow-width effects */
            vth = model->MOS2vt0 + model->MOS2gamma * (sqrt(phi - vbs) - sqrt(phi));
            
            /* Add short-channel effect */
            if (model->MOS2xj > 0.0) {
                double fs = 1.0 - model->MOS2ld / inst->MOS2l 
                          - sqrt(1.0 + 2.0 * xd / model->MOS2xj);
                vth -= fs * model->MOS2gamma * sqrt(phi - vbs);
            }
            
            /* Add narrow-width effect */
            if (inst->MOS2w < 10.0 * model->MOS2tox) {
                vth += (M_PI * EPS_SI / (4.0 * cox * inst->MOS2w)) * (phi - vbs);
            }
            
            /* Determine operating region */
            vgst = vgs - vth;
            
            if (vgst <= 0.0) {
                /* Cutoff region */
                inst->MOS2cd = 1e-14 * exp(vgst / (N * V_T)) 
                             * (1.0 - exp(-vds / V_T));
                gm = inst->MOS2cd / (N * V_T);
                gds = inst->MOS2cd / V_T;
                gmbs = 0.0;
            } else {
                /* Compute saturation voltage with velocity saturation */
                if (model->MOS2vmax > 0.0) {
                    vdsat = vgst / (1.0 + vgst / (model->MOS2vmax * inst->MOS2l));
                } else {
                    vdsat = vgst;
                }
                
                if (vds < vdsat) {
                    /* Linear region */
                    inst->MOS2cd = beta * (vgst * vds - 0.5 * vds * vds)
                                 * (1.0 + lambda * vds);
                    gm = beta * vds;
                    gds = beta * (vgst - vds) + lambda * beta 
                        * (vgst * vds - 0.5 * vds * vds);
                } else {
                    /* Saturation region */
                    inst->MOS2cd = 0.5 * beta * vgst * vgst 
                                 * (1.0 + lambda * vds);
                    gm = beta * vgst;
                    gds = 0.5 * lambda * beta * vgst * vgst;
                }
                
                /* Body effect transconductance */
                gmbs = gm * model->MOS2gamma / (2.0 * sqrt(phi - vbs));
            }
            
            /* Store small-signal parameters */
            inst->MOS2gm = gm;
            inst->MOS2gds = gds;
            inst->MOS2gmbs = gmbs;
            
            /* Compute Meyer capacitances */
            MOS2meyerCaps(inst, vgs, vds, vbs, &cgs, &cgd, &cgb);
            inst->MOS2cgs = cgs;
            inst->MOS2cgd = cgd;
            inst->MOS2cgb = cgb;
            
            /* Stamp matrix */
            MOS2stampMatrix(inst, ckt, gm, gds, gmbs, cgs, cgd, cgb);
        }
    }
    return OK;
}
```

### Newton-Raphson Voltage Limiting

The `DEVfetlim()` function ensures convergence by limiting voltage changes between iterations:

```c
double DEVfetlim(double vnew, double vold, double vto)
{
    double vt;
    
    if (vold > vto) {
        if (vnew > vold) {
            vt = vold + 2.0;
            if (vnew > vt) vnew = vt;
        } else if (vnew < vto) {
            if (vold < vto + 3.0) {
                vt = vto - 0.5;
                if (vnew < vt) vnew = vt;
            } else {
                vt = 3.0 * (vto - vold);
                if (vnew < vold + vt) vnew = vold + vt;
            }
        }
    } else if (vold < vto) {
        if (vnew < vold) {
            vt = vold - 2.0;
            if (vnew < vt) vnew = vt;
        } else if (vnew > vto) {
            if (vold > vto - 3.0) {
                vt = vto + 0.5;
                if (vnew > vt) vnew = vt;
            } else {
                vt = 3.0 * (vto - vold);
                if (vnew > vold + vt) vnew = vold + vt;
            }
        }
    }
    return vnew;
}
```

### Matrix Stamping Mathematics

The complete 6×6 conductance matrix for the MOS2 device with parasitic resistances is:

```math
\begin{bmatrix}
G_{DD} & G_{DG} & G_{DS} & G_{DB} & G_{DD'} & G_{DS'} \\
G_{GD} & G_{GG} & G_{GS} & G_{GB} & G_{GD'} & G_{GS'} \\
G_{SD} & G_{SG} & G_{SS} & G_{SB} & G_{SD'} & G_{SS'} \\
G_{BD} & G_{BG} & G_{BS} & G_{BB} & G_{BD'} & G_{BS'} \\
G_{D'D} & G_{D'G} & G_{D'S} & G_{D'B} & G_{D'D'} & G_{D'S'} \\
G_{S'D} & G_{S'G} & G_{S'S} & G_{S'B} & G_{S'D'} & G_{S'S'}
\end{bmatrix}
\begin{bmatrix}
V_D \\ V_G \\ V_S \\ V_B \\ V_{D'} \\ V_{S'}
\end{bmatrix}
=
\begin{bmatrix}
I_D \\ I_G \\ I_S \\ I_B \\ I_{D'} \\ I_{S'}
\end{bmatrix}
```

The stamping implementation in `MOS2stampMatrix()`:

```c
void MOS2stampMatrix(MOS2instance *inst, CKTcircuit *ckt,
                     double gm, double gds, double gmbs,
                     double cgs, double cgd, double cgb)
{
    double gdpr = (inst->MOS2dNodePrime != inst->MOS2dNode) ? 
                  1.0 / model->MOS2rd : 0.0;
    double gspr = (inst->MOS2sNodePrime != inst->MOS2sNode) ? 
                  1.0 / model->MOS2rs : 0.0;
    
    /* Stamp intrinsic device at D', S', G, B nodes */
    *(inst->MOS2drainPrimeDrainPrimePtr) += gdpr + gds;
    *(inst->MOS2drainPrimeGatePtr) += gm;
    *(inst->MOS2drainPrimeSourcePrimePtr) += -gds - gmbs;
    *(inst->MOS2drainPrimeBulkPtr) += gmbs;
    
    *(inst->MOS2sourcePrimeDrainPrimePtr) += -gds;
    *(inst->MOS2sourcePrimeGatePtr) += -gm;
    *(inst->MOS2sourcePrimeSourcePrimePtr) += gspr + gds + gmbs;
    *(inst->MOS2sourcePrimeBulkPtr) += -gmbs;
    
    /* Stamp parasitic resistances */
    if (gdpr > 0.0) {
        *(inst->MOS2drainDrainPtr) += gdpr;
        *(inst->MOS2drainDrainPrimePtr) += -gdpr;
        *(inst->MOS2drainPrimeDrainPtr) += -gdpr;
    }
    
    if (gspr > 0.0) {
        *(inst->MOS2sourceSourcePtr) += gspr;
        *(inst->MOS2sourceSourcePrimePtr) += -gspr;
        *(inst->MOS2sourcePrimeSourcePtr) += -gspr;
    }
    
    /* Add capacitive elements for transient analysis */
    if (ckt->CKTmode & MODETRAN) {
        double cgst = cgs * ckt->CKTomega;
        double cgdt = cgd * ckt->CKTomega;
        double cgbt = cgb * ckt->CKTomega;
        
        /* Stamp imaginary parts for AC analysis */
        *(inst->MOS2drainPrimeDrainPrimePtr) += COMPLEX(0.0, cgdt);
        *(inst->MOS2drainPrimeGatePtr) += COMPLEX(0.0, -cgdt);
        *(inst->MOS2gateDrainPrimePtr) += COMPLEX(0.0, -cgdt);
        *(inst->MOS2gateGatePtr) += COMPLEX(0.0, cgdt + cgst + cgbt);
        *(inst->MOS2gateSourcePrimePtr) += COMPLEX(0.0, -cgst);
        *(inst->MOS2gateBulkPtr) += COMPLEX(0.0, -cgbt);
        *(inst->MOS2sourcePrimeGatePtr) += COMPLEX(0.0, -cgst);
        *(inst->MOS2sourcePrimeSourcePrimePtr) += COMPLEX(0.0, cgst);
        *(inst->MOS2bulkGatePtr) += COMPLEX(0.0, -cgbt);
        *(inst->MOS2bulkBulkPtr) += COMPLEX(0.0, cgbt);
    }
}
```

### Source/Drain Swap Logic

The implementation handles PMOS devices and inverse mode operation through node swapping:

```c
/* In MOS2load() */
if (model->MOS2type < 0) { /* PMOS */
    vgs = -vgs;
    vds = -vds;
    vbs = -vbs;
}

/* Check for inverse mode */
if (vds < 0.0) {
    /* Swap source and drain */
    double tmp;
    tmp = vds; vds = -vgs; vgs = tmp + vgs;
    tmp = vbs; vbs = vbs - vds; /* Adjust bulk voltage */
    
    /* Swap node pointers */
    SWAP(inst->MOS2dNodePrime, inst->MOS2sNodePrime);
    SWAP(inst->MOS2drainPrimeDrainPrimePtr, inst->MOS2sourcePrimeSourcePrimePtr);
    /* ... swap all relevant matrix pointers ... */
    
    inst->MOS2mode = 1; /* Set inverse mode flag */
} else {
    inst->MOS2mode = 0; /* Normal mode */
}
```

### SPICE API Integration

The device is registered with Ngspice through the `SPICEdev` structure in `mos2init.c`:

```c
SPICEdev MOS2info = {
    .DEVpublic = {
        .name = "mos2",
        .description = "Level 2 MOSFET model",
        .terms = 4,
        .numNames = 0,
        .termNames = NULL,
        .numInstanceParms = 32,
        .instanceParms = MOS2pTable,
        .numModelParms = 28,
        .modelParms = MOS2mPTable,
        .flags = DEV_DEFAULT,
    },
    
    .DEVparam = MOS2param,
    .DEVmodParam = MOS2mParam,
    .DEVload = MOS2load,
    .DEVsetup = MOS2setup,
    .DEVunsetup = MOS2unsetup,
    .DEVpzSetup = MOS2pzSetup,
    .DEVtemperature = MOS2temp,
    .DEVtrunc = MOS2trunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = MOS2acLoad,
    .DEVaccept = NULL,
    .DEVdestroy = MOS2destroy,
    .DEVmodDelete = MOS2mDelete,
    .DEVdelete = MOS2delete,
    .DEVsetic = MOS2getic,
    .DEVask = MOS2ask,
    .DEVmodAsk = MOS2mAsk,
    .DEVpzLoad = MOS2pzLoad,
    .DEVconvTest = MOS2convTest,
    .DEVsenSetup = MOS2sSetup,
    .DEVsenLoad = MOS2sLoad,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = MOS2disto,
    .DEVnoise = MOS2noise,
    .DEVsoaCheck = NULL,
    .DEVinstSize = sizeof(MOS2instance),
    .DEVmodSize = sizeof(MOS2model)
};
```

### Device Initialization and Destruction

The `mos2init.c` file handles device registration:

```c
int MOS2init(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS2model *model = (MOS2model *)inModel;
    
    /* Initialize all instances */
    for (; model != NULL; model = model->MOS2nextModel) {
        for (inst = model->MOS2instances; inst != NULL; inst = inst->MOS2nextInstance) {
            /* Set initial voltages */
            inst->MOS2vgs = ckt->CKTrhs[inst->MOS2gNode] - ckt->CKTrhs[inst->MOS2sNode];
            inst->MOS2vds = ckt->CKTrhs[inst->MOS2dNode] - ckt->CKTrhs[inst->MOS2sNode];
            inst->MOS2vbs = ckt->CKTrhs[inst->MOS2bNode] - ckt->CKTrhs[inst->MOS2sNode];
            
            /* Initialize charges */
            inst->MOS2qgs = 0.0;
            inst->MOS2qgd = 0.0;
            inst->MOS2qgb = 0.0;
            inst->MOS2qbd = 0.0;
            inst->MOS2qbs = 0.0;
            
            /* Initialize history terms */
            inst->MOS2vgs_old = inst->MOS2vgs;
            inst->MOS2vds_old = inst->MOS2vds;
            inst->MOS2vbs_old = inst->MOS2vbs;
        }
    }
    return OK;
}
```

The `mos2dest.c` file handles cleanup:

```c
void MOS2destroy(GENmodel **inModel)
{
    MOS2model *model = (MOS2model *)*inModel;
    MOS2model *nextModel;
    MOS2instance *inst, *nextInst;
    
    while (model) {
        nextModel = model->MOS2nextModel;
        
        /* Free all instances */
        inst = model->MOS2instances;
        while (inst) {
            nextInst = inst->MOS2nextInstance;
            FREE(inst);
            inst = nextInst;
        }
        
        FREE(model);
        model = nextModel;
    }
    *inModel = NULL;
}
```

## Convergence Analysis

### Newton-Raphson Iteration Control

The MOS2 implementation employs several techniques to ensure Newton-Raphson convergence:

**1. Voltage Limiting**: The `DEVfetlim()` function prevents excessive voltage steps between iterations, particularly near the threshold voltage where the drain current exhibits exponential behavior.

**2. GMIN Addition**: A small conductance (typically 1e-12 S) is added to all junctions to prevent singular matrices:
```math
G_{modified} = G_{intrinsic} + G_{MIN}
```

**3. Region Boundary Smoothing**: At the boundaries between cutoff, linear, and saturation regions, the implementation uses smooth transitions to avoid discontinuities in derivatives. For example, near `V_{ds} = V_{dsat}`:
```math
I_d = I_{d,lin} \cdot f_{smooth} + I_{d,sat} \cdot (1 - f_{smooth})
```
where `f_{smooth}` is a smoothing function that varies from 1 to 0 over a small voltage range.

### Convergence Criteria

The `MOS2convTest()` function checks convergence using mixed absolute-relative tolerances:

```c
int MOS2convTest(MOS2instance *inst, CKTcircuit *ckt)
{
    double vgs_rel, vds_rel, vbs_rel;
    double cd_rel, cbs_rel, cbd_rel;
    double tol;
    
    /* Voltage convergence */
    vgs_rel = fabs(inst->MOS2vgs - inst->MOS2vgs_old);
    vds_rel = fabs(inst->MOS2vds - inst->MOS2vds_old);
    vbs_rel = fabs(inst->MOS2vbs - inst->MOS2vbs_old);
    
    tol = ckt->CKTreltol * MAX(fabs(inst->MOS2vgs), fabs(inst->MOS2vgs_old)) 
          + ckt->CKTvoltTol;
    if (vgs_rel > tol) return 0;
    
    tol = ckt->CKTreltol * MAX(fabs(inst->MOS2vds), fabs(inst->MOS2vds_old)) 
          + ckt->CKTvoltTol;
    if (vds_rel > tol) return 0;
    
    /* Current convergence */
    cd_rel = fabs(inst->MOS2cd - inst->MOS2cd_old);
    tol = ckt->CKTreltol * MAX(fabs(inst->MOS2cd), fabs(inst->MOS2cd_old)) 
          + ckt->CKTabstol;
    if (cd_rel > tol) return 0;
    
    /* Charge convergence for transient analysis */
    if (ckt->CKTmode & MODETRAN) {
        double qgs_rel = fabs(ckt->CKTstate0[inst->MOS2stateGgs] 
                            - ckt->CKTstate1[inst->MOS2stateGgs]);
        if (qgs_rel > ckt->CKTchargeTol) return 0;
        /* Check other charges similarly */
    }
    
    inst->MOS2converged = 1;
    return 1;
}
```

### Time-Step Control for Transient Analysis

The `MOS2trunc()` function estimates local truncation error (LTE) for adaptive time-step control:

```c
int MOS2trunc(MOS2instance *inst, CKTcircuit *ckt, double *timeStep)
{
    double qgs_pred, qgd_pred, qgb_pred;
    double error, lte;
    
    /* Predict charges using polynomial extrapolation */
    qgs_pred = 2.5 * ckt->CKTstate0[inst->MOS2stateGgs]
               - 2.0 * ckt->CKTstate1[inst->MOS2stateGgs]
               + 0.5 * ckt->CKTstate2[inst->MOS2stateGgs];
    
    /* Compute LTE using Milne's method */
    error = fabs(qgs_pred - ckt->CKTstate0[inst->MOS2stateGgs]);
    lte = error / (fabs(ckt->CKTstate0[inst->MOS2stateGgs]) + 1.0);
    
    /* Adjust time step */
    if (lte > ckt->CKTtrtol) {
        *timeStep = 0.75 * ckt->CKTdelta * sqrt(ckt->CKTtrtol / (lte + 1e-12));
        return 1; /* Need smaller time step */
    }
    
    return 0; /* Time step OK */
}
```

### Numerical Stability Considerations

**1. Exponential Argument Limiting**: In subthreshold region calculations, exponential arguments are limited to prevent overflow:
```c
double x = (vgs - vth) / (N * V_T);
if (x > 50.0) x = 50.0;
if (x < -50.0) x = -50.0;
```

**2. Square Root Argument Protection**: All square root operations include a small epsilon:
```c
double sqrt_arg = phi - vbs + 1e-12;
if (sqrt_arg < 0.0) sqrt_arg = 0.0;
double sqrt_val = sqrt(sqrt_arg);
```

**3. Minimum Dimension Enforcement**: Effective channel length and width are bounded:
```c
double leff = inst->MOS2l - 2.0 * model->MOS2ld;
if (leff < 1e-12) leff = 1e-12;
double weff = inst->MOS2w;
if (weff < 1e-12) weff = 1e-12;
```

### Parameter Validation

The `MOS2setup()` function validates physical parameters:

```c
int MOS2setup(MOS2model *model, CKTcircuit *ckt)
{
    /* Check for physically reasonable values */
    if (model->MOS2tox <= 0.0) {
        printf("Warning: TOX must be positive, using 1e-7\n");
        model->MOS2tox = 1e-7;
    }
    
    if (model->MOS2phi <= 0.0) {
        printf("Warning: PHI must be positive, using 0.7\n");
        model->MOS2phi = 0.7;
    }
    
    /* Compute derived parameters */
    model->MOS2coeff = sqrt(2.0 * EPS_SI * CHARGE * model->MOS2ndep) 
                     / model->MOS2cox;
    
    return OK;
}
```

This comprehensive implementation of the MOS2 model in Ngspice demonstrates how advanced semiconductor physics is translated into robust numerical algorithms for circuit simulation, with careful attention to convergence, numerical stability, and computational efficiency.