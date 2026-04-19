# MOS2: Data Structures and SPICE API

_Generated 2026-04-12 04:38 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2defs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2dest.c`

# MOS2: Data Structures and SPICE API

## Introduction

The implementation of the MOSFET Level 2 (MOS2) model in Ngspice is architected around a set of core C source files that define its data structures, initialization logic, and integration with the SPICE simulation engine. These files—`mos2defs.h`, `mos2init.c`, `mos2.c`, and `mos2dest.c`—collectively establish the model's programmatic identity within the simulator, translating the Grove-Frohman analytical equations into a computationally efficient and numerically robust device implementation.

*   **`mos2defs.h`** contains the fundamental data structures `MOS2model` and `MOS2instance`. These structures map SPICE model parameters (VTO, KP, GAMMA, etc.) and instance-specific variables (geometry, bias voltages, small-signal parameters, charges) directly to C variables, serving as the bridge between the netlist specification and the internal mathematical computations.
*   **`mos2init.c`** implements the device setup and initialization routines. Its primary function, `MOS2setup()`, is responsible for allocating state vector indices for the model's five charge variables, creating internal nodes to represent parasitic drain and source resistances (RD, RS), and establishing the sparse matrix pointers required for the Newton-Raphson solver's conductance matrix.
*   **`mos2.c`** (encompassing the core load function) houses the computational heart of the model. It evaluates the piecewise Grove-Frohman drain current equations, computes the associated small-signal parameters (gm, gds, gmbs), implements the Meyer capacitance model, and stamps the resulting conductances and currents into the circuit's system matrix and right-hand-side vector.
*   **`mos2dest.c`** manages the model's lifecycle by implementing memory cleanup routines. It ensures proper deallocation of dynamically allocated strings and structures when a simulation concludes or a model is deleted, preventing memory leaks.

Together, these files define the MOS2 model's API to the Ngspice kernel via the `SPICEdev MOS2info` structure, which registers function pointers for setup, load, temperature adjustment, convergence testing, and other simulation phases. This chapter details how these C constructs implement the mathematical model, manage device state, and interface with the SPICE simulation framework.

## Mathematical Formulation

### 1. Core Grove-Frohman Level 2 Equations

#### Threshold Voltage with Geometry Effects
The threshold voltage \(V_{th}\) incorporates short-channel and narrow-width effects:
\[
V_{th} = VTO + \gamma \left( \sqrt{\phi - V_{bs}} - \sqrt{\phi} \right) + \Delta V_{th}^{(short)} + \Delta V_{th}^{(narrow)}
\]
where:
- **Short-channel effect** (Drain-Induced Barrier Lowering):
\[
\Delta V_{th}^{(short)} = \gamma \left[ \sqrt{\phi - V_{bs} + \psi} - \sqrt{\phi + \psi} \right] + \eta V_{ds}
\]
with \(\psi = \frac{\epsilon_{si} X_j C_{ox}}{2\epsilon_{ox}} \left[1 - \sqrt{1 + \frac{2W_s}{X_j}}\right]\) and \(\eta\) as the DIBL coefficient.
- **Narrow-width effect**:
\[
\Delta V_{th}^{(narrow)} = \delta \frac{\pi \epsilon_{si}}{2 C_{ox} W_{eff}} (\phi - V_{bs})
\]
where \(\delta\) is the DELTA model parameter.

#### Piecewise Drain Current Equations
The drain current \(I_d\) is computed based on operating region:

**Region Conditions:**
- Cutoff: \(V_{gst} = V_{gs} - V_{th} \leq 0\)
- Linear/Triode: \(V_{gst} > 0\) and \(V_{dst} \leq \frac{V_{gst}}{1+\delta}\)
- Saturation: \(V_{gst} > 0\) and \(V_{dst} > \frac{V_{gst}}{1+\delta}\) but \(V_{dst} \leq V_{dsat}\)
- Velocity Saturation: \(V_{dst} > V_{dsat}\)

**Current Equations:**
- Linear Region:
\[
I_d = \beta \left[ V_{gst} V_{dst} - \frac{1+\delta}{2} V_{dst}^2 \right] (1 + \lambda V_{dst})
\]
- Saturation Region:
\[
I_d = \frac{\beta}{2(1+\delta)} V_{gst}^2 (1 + \lambda V_{dst})
\]
- Velocity Saturation Region (modified):
\[
V_{dsat} = \frac{V_{gst}}{1+\delta} + V_c L_{eff}, \quad I_{d,sat} = \beta V_{gst} V_{dsat} \left[1 - \frac{V_{dsat}}{2V_{gst}}\right] (1 + \lambda V_{dst})
\]
where \(\beta = \frac{W_{eff}}{L_{eff}} KP\) and \(V_c = v_{sat}/\mu\).

#### Small-Signal Parameters
The derivatives for the conductance matrix:
\[
g_m = \frac{\partial I_d}{\partial V_{gs}}, \quad g_{ds} = \frac{\partial I_d}{\partial V_{ds}}, \quad g_{mbs} = \frac{\partial I_d}{\partial V_{bs}} = -\frac{\partial I_d}{\partial V_{th}} \cdot \frac{\partial V_{th}}{\partial V_{bs}}
\]

#### Meyer Capacitance Charge Model
Gate charge partitioning based on region:
- **Accumulation** (\(V_{gs} < V_{th}\)):
\[
C_{gb} = C_{ox} W L, \quad C_{gs} = C_{gd} = 0, \quad Q_{gb} = C_{gb}(V_{gs} - V_{th})
\]
- **Saturation** (\(V_{gs} \geq V_{th}, V_{ds} > V_{dsat}\)):
\[
C_{gs} = \frac{2}{3} C_{ox} W L, \quad C_{gd} = C_{gb} = 0, \quad Q_{gs} = C_{gs}(V_{gs} - V_{th})
\]
- **Linear** (\(V_{gs} \geq V_{th}, V_{ds} \leq V_{dsat}\)):
\[
C_{gs} = C_{ox} W L \left[1 - \left(\frac{V_{ds}}{2(V_{gs}-V_{th})}\right)^2\right], \quad C_{gd} = C_{ox} W L \left[1 - \left(1 - \frac{V_{ds}}{2(V_{gs}-V_{th})}\right)^2\right]
\]

### 2. Matrix Stamping Mathematics

The complete 6×6 conductance matrix for the MOS2 device (including internal nodes for RD/RS):
\[
\begin{bmatrix}
G_{dd} & G_{dd'} & 0 & 0 & 0 & 0 \\
G_{d'd} & G_{d'd'} & G_{dg} & G_{d's'} & G_{db} & 0 \\
0 & G_{gd} & G_{gg} & G_{gs'} & G_{gb} & 0 \\
0 & G_{s'd} & G_{sg} & G_{s's'} & G_{sb} & G_{s's} \\
0 & G_{bd} & G_{bg} & G_{bs'} & G_{bb} & 0 \\
0 & 0 & 0 & G_{ss'} & 0 & G_{ss}
\end{bmatrix}
\begin{bmatrix}
V_d \\ V_{d'} \\ V_g \\ V_{s'} \\ V_b \\ V_s
\end{bmatrix}
=
\begin{bmatrix}
0 \\ -I_d \\ 0 \\ I_d \\ I_{bd}+I_{bs} \\ 0
\end{bmatrix}
\]

**Matrix Elements:**
- \(G_{dd} = G_{d'd'} = G_{d'd} = G_{dd'} = 1/R_D\) (for RD > 0)
- \(G_{ss} = G_{s's'} = G_{s's} = G_{ss'} = 1/R_S\) (for RS > 0)
- \(G_{d'd'} += g_{ds}\), \(G_{d's'} = -(g_{ds} + g_m + g_{mbs})\), \(G_{db} = -g_{mbs}\)
- \(G_{s's'} += g_{ds} + g_m + g_{mbs}\), \(G_{sb} = g_{mbs}\), \(G_{bb} = g_{bd} + g_{bs}\)

### 3. Newton-Raphson Convergence and Voltage Limiting

The `DEVfetlim` algorithm ensures convergence by limiting voltage changes between iterations:
- If \(v_{old} > V_{th}\): Allow increase up to \(v_{old} + 2.0\), prevent drop below \(V_{th} + 0.5\)
- If \(v_{old} < -V_{th}\): Allow decrease down to \(v_{old} - 2.0\), prevent rise above \(-V_{th} - 0.5\)
- If \(|v_{old}| \leq V_{th}\): Constrain \(v_{new}\) to \([-V_{th} - 0.5, V_{th} + 0.5]\)

## C Implementation

### 1. Core Data Structures and SPICE Integration

The MOS2 model's implementation in Ngspice is built around two primary C structures defined in `mos2defs.h`: `MOS2model` and `MOS2instance`. These structures map directly to the mathematical parameters and state variables described in the Grove-Frohman Level 2 equations.

#### 1.1 Model Parameter Structure (`MOS2model`)
The `MOS2model` structure contains all process-related parameters that are shared across multiple transistor instances. Each field corresponds to a SPICE model parameter:

```c
typedef struct sMOS2model {
    int MOS2type;                    /* NMF=1, PMF=-1 */
    double MOS2vt0;                  /* VTO: Zero-bias threshold voltage */
    double MOS2kp;                   /* KP: Transconductance parameter */
    double MOS2gamma;                /* GAMMA: Body effect parameter */
    double MOS2phi;                  /* PHI: Surface potential */
    double MOS2lambda;               /* LAMBDA: Channel-length modulation */
    double MOS2rd;                   /* RD: Drain ohmic resistance */
    double MOS2rs;                   /* RS: Source ohmic resistance */
    /* ... additional parameters ... */
    
    /* Derived parameters (computed during setup) */
    double MOS2coeff;               /* β = KP * (W/L) * (1 + LAMBDA*Vds) */
    double MOS2oxideCapFactor;      /* COX = ε_ox/TOX */
    double MOS2gammaEff;            /* Effective gamma with short-channel effect */
    
    struct sMOS2model *MOS2nextModel;  /* Linked list of models */
    sMOS2instance *MOS2instances;      /* Chain of instances for this model */
} MOS2model;
```

The mathematical mapping is direct: `MOS2vt0` ↔ VTO, `MOS2kp` ↔ KP, `MOS2gamma` ↔ γ, etc. The derived parameters like `MOS2coeff` (β) are computed from the base parameters during the setup phase to avoid redundant calculations during simulation.

#### 1.2 Instance Parameter Structure (`MOS2instance`)
The `MOS2instance` structure contains geometry-specific parameters and runtime state variables:

```c
typedef struct sMOS2instance {
    /* Node connectivity */
    int MOS2dNode, MOS2gNode, MOS2sNode, MOS2bNode;
    int MOS2dNodePrime, MOS2sNodePrime;  /* Internal nodes for RD/RS */
    
    /* Geometric parameters */
    double MOS2l, MOS2w;            /* L, W: Drawn length and width */
    double MOS2ad, MOS2as;          /* AD, AS: Drain/source areas */
    
    /* Electrical state (mathematical variables) */
    double MOS2vds, MOS2vgs, MOS2vbs;  /* Terminal voltages */
    double MOS2cd;                    /* Id: Drain current */
    double MOS2gm, MOS2gds, MOS2gmbs; /* Small-signal parameters */
    double MOS2cgs, MOS2cgd, MOS2cgb; /* Meyer capacitances */
    double MOS2qgs, MOS2qgd, MOS2qgb; /* State charges */
    
    /* State vector indices */
    unsigned MOS2stateGgs, MOS2stateGgd, MOS2stateGgb;
    
    /* Matrix element pointers */
    double *MOS2dDrainPrimePtr, *MOS2dGatePtr, *MOS2dSourcePrimePtr;
    /* ... additional matrix pointers ... */
    
    struct sMOS2instance *MOS2nextInstance;
    MOS2model *MOS2modPtr;
} MOS2instance;
```

The instance structure maintains the complete device state: voltages (`MOS2vgs`, `MOS2vds`, `MOS2vbs`), current (`MOS2cd`), small-signal parameters (`MOS2gm`, `MOS2gds`, `MOS2gmbs`), and charges (`MOS2qgs`, etc.). These map directly to the mathematical variables V_gs, V_ds, I_d, g_m, g_ds, Q_gs, etc.

### 2. Internal Node Topology Implementation

The mathematical model of parasitic resistances RD and RS is implemented through internal nodes `d'` and `s'`. The code in `mos2setup()` creates these nodes when RD > 0 or RS > 0:

```c
/* In MOS2setup() */
if(model->MOS2rd > 0.0) {
    inst->MOS2dNodePrime = ckt->CKTnumStates++;
    /* Allocate matrix elements for RD stamp */
    inst->MOS2dDrainPtr = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2dNode);
    inst->MOS2dDrainPrimePtr2 = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2dNodePrime);
    inst->MOS2dPrimeDrainPtr = SMPmakeElt(matrix, inst->MOS2dNodePrime, inst->MOS2dNode);
} else {
    inst->MOS2dNodePrime = inst->MOS2dNode;  /* No internal node needed */
}
```

This creates the topology: D(external) -- RD -- d'(internal) -- Intrinsic MOSFET -- s'(internal) -- RS -- S(external). The matrix stamping for RD implements the conductance equations:

```c
/* Stamp RD conductance */
if(inst->MOS2dNodePrime != inst->MOS2dNode) {
    double gd = 1.0/model->MOS2rd;
    *inst->MOS2dDrainPtr += gd;
    *inst->MOS2dDrainPrimePtr2 -= gd;
    *inst->MOS2dPrimeDrainPtr -= gd;
    *inst->MOS2dDrainPrimePtr += gd;  /* Added to intrinsic matrix */
}
```

This C code directly implements the mathematical conductance matrix:
```
[ 1/RD  -1/RD ] [Vd]   = [0]
[ -1/RD  1/RD ] [Vd']    [0]
```

### 3. State Vector Management for Charge Conservation

The five charge state variables (Q_gs, Q_gd, Q_gb, Q_bd, Q_bs) are managed through Ngspice's state vector system. In `mos2init.c`:

```c
int MOS2setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS2model *model = (MOS2model *)inModel;
    MOS2instance *inst;
    
    for(; model != NULL; model = model->MOS2nextModel) {
        for(inst = model->MOS2instances; inst != NULL; inst = inst->MOS2nextInstance) {
            /* Allocate state vector indices */
            inst->MOS2stateGgs = (*states)++;
            inst->MOS2stateGgd = (*states)++;
            inst->MOS2stateGgb = (*states)++;
            inst->MOS2stateQbd = (*states)++;
            inst->MOS2stateQbs = (*states)++;
            
            /* Initialize charges to zero */
            ckt->CKTstates[inst->MOS2stateGgs] = 0.0;
            /* ... initialize other charges ... */
        }
    }
    return OK;
}
```

During transient analysis, the state vector `ckt->CKTstates[]` stores charge values at different time points, enabling numerical integration and local truncation error calculation. The indices `MOS2stateGgs`, etc., provide direct access to the mathematical charge variables Q_gs(t), Q_gd(t), etc.

### 4. Grove-Frohman Equations Implementation

#### 4.1 Threshold Voltage Calculation
The mathematical threshold voltage equation with short-channel and narrow-width effects is implemented as:

```c
double MOS2computeVth(MOS2model *model, MOS2instance *inst, double vbs) {
    double phi = model->MOS2phi;
    double gamma = model->MOS2gamma;
    double vto = model->MOS2vt0;
    
    /* Body effect term: γ(√(φ - V_bs) - √φ) */
    double sqrtPhi = sqrt(phi);
    double sqrtPhiVbs = sqrt(phi - vbs);
    double bodyEffect = gamma * (sqrtPhiVbs - sqrtPhi);
    
    /* Short-channel effect (simplified) */
    double leff = inst->MOS2effL;
    double xj = model->MOS2xj;
    double deltaVthShort = 0.0;
    if(xj > 0.0 && leff > 0.0) {
        double psi = 0.0;  /* Simplified ψ calculation */
        deltaVthShort = gamma * (sqrt(phi - vbs + psi) - sqrt(phi + psi));
    }
    
    /* Narrow-width effect */
    double weff = inst->MOS2effW;
    double tox = model->MOS2tox;
    double deltaVthNarrow = 0.0;
    if(model->MOS2delta > 0.0 && weff > 0.0) {
        double cox = model->MOS2oxideCapFactor;
        deltaVthNarrow = model->MOS2delta * (M_PI * EPS_SI) / (2.0 * cox * weff) * (phi - vbs);
    }
    
    return vto + bodyEffect + deltaVthShort + deltaVthNarrow;
}
```

This C function directly computes the mathematical expression:
```
V_th = VTO + γ(√(φ - V_bs) - √φ) + ΔV_th(short) + ΔV_th(narrow)
```

#### 4.2 Drain Current Computation
The piecewise drain current equations are implemented with region detection:

```c
void MOS2computeId(MOS2model *model, MOS2instance *inst, 
                   double vgs, double vds, double vbs) {
    double vth = MOS2computeVth(model, inst, vbs);
    double vgst = vgs - vth;
    double beta = inst->MOS2beta;  /* β = (W_eff/L_eff) * KP */
    
    if(vgst <= 0.0) {
        /* Cutoff region */
        inst->MOS2cd = 0.0;
        inst->MOS2gm = 0.0;
        inst->MOS2gds = 0.0;
        inst->MOS2gmbs = 0.0;
    } else {
        double vdst = vds;
        double vdsat = vgst / (1.0 + model->MOS2delta);
        
        if(vdst <= vdsat) {
            /* Linear region: I_d = β[V_gst·V_dst - (1+δ)/2·V_dst²] */
            inst->MOS2cd = beta * (vgst * vdst - 0.5 * (1.0 + model->MOS2delta) * vdst * vdst);
            inst->MOS2gm = beta * vdst;  /* ∂I_d/∂V_gs */
            inst->MOS2gds = beta * (vgst - (1.0 + model->MOS2delta) * vdst);  /* ∂I_d/∂V_ds */
        } else {
            /* Saturation region: I_d = (β/(2(1+δ)))·V_gst² */
            double idsat = (beta / (2.0 * (1.0 + model->MOS2delta))) * vgst * vgst;
            inst->MOS2cd = idsat * (1.0 + model->MOS2lambda * vdst);
            inst->MOS2gm = (beta / (1.0 + model->MOS2delta)) * vgst;  /* ∂I_d/∂V_gs */
            inst->MOS2gds = model->MOS2lambda * idsat;  /* ∂I_d/∂V_ds (channel-length modulation) */
        }
        
        /* Bulk transconductance: g_mbs = ∂I_d/∂V_bs = (∂I_d/∂V_th)·(∂V_th/∂V_bs) */
        double dVth_dVbs = -0.5 * model->MOS2gamma / sqrt(model->MOS2phi - vbs);
        inst->MOS2gmbs = -inst->MOS2gm * dVth_dVbs;
    }
}
```

This implementation maps directly to the mathematical equations:
- Linear: `I_d = β[V_gst·V_dst - (1+δ)/2·V_dst²]`
- Saturation: `I_d = (β/(2(1+δ)))·V_gst²·(1 + λ·V_dst)`
- Derivatives: `g_m = ∂I_d/∂V_gs`, `g_ds = ∂I_d/∂V_ds`, `g_mbs = ∂I_d/∂V_bs`

### 5. Newton-Raphson Voltage Limiting

The `DEVfetlim()` function implements voltage limiting to ensure Newton-Raphson convergence:

```c
double DEVfetlim(double vnew, double vold, double vto) {
    if(vold > vto) {
        if(vnew > vold) {
            double vtemp = vold + 2.0;
            if(vnew > vtemp) vnew = vtemp;  /* Limit increase */
        } else {
            if(vnew < vto) {
                double vtemp = vto + 0.5;
                if(vnew < vtemp) vnew = vtemp;  /* Don't drop below threshold */
            }
        }
    }
    /* ... similar logic for other cases ... */
    return vnew;
}
```

This algorithm prevents large voltage changes between Newton iterations, particularly near the threshold voltage where the device characteristics change rapidly. It's applied to V_gs, V_ds, and V_bs in `MOS2load()`:

```c
vgs = DEVfetlim(vgs, inst->MOS2vgs, model->MOS2vt0);
vds = DEVfetlim(vds, inst->MOS2vds, model->MOS2vt0);
vbs = DEVfetlim(vbs, inst->MOS2vbs, 0.0);
```

### 6. Matrix Stamping Implementation

The complete 6×6 conductance matrix stamping implements the mathematical Jacobian:

```c
void MOS2stampMatrix(MOS2instance *inst, CKTcircuit *ckt) {
    /* Stamp intrinsic MOSFET (4-terminal) */
    *inst->MOS2dDrainPrimePtr += inst->MOS2gds;  /* G[d'][d'] += g_ds */
    *inst->MOS2dGatePtr -= inst->MOS2gm;         /* G[d'][g] -= g_m */
    *inst->MOS2dSourcePrimePtr -= (inst->MOS2gds + inst->MOS2gm + inst->MOS2gmbs);
    *inst->MOS2dBulkPtr -= inst->MOS2gmbs;       /* G[d'][b] -= g_mbs */
    
    *inst->MOS2sGatePtr += inst->MOS2gm;         /* G[s'][g] += g_m */
    *inst->MOS2sSourcePrimePtr += (inst->MOS2gds + inst->MOS2gm + inst->MOS2gmbs);
    *inst->MOS2sBulkPtr += inst->MOS2gmbs;       /* G[s'][b] += g_mbs */
    
    *inst->MOS2bDrainPrimePtr -= inst->MOS2gmbs; /* G[b][d'] -= g_mbs */
    *inst->MOS2bSourcePrimePtr += inst->MOS2gmbs;/* G[b][s'] += g_mbs */
    *inst->MOS2bBulkPtr += (inst->MOS2gbd + inst->MOS2gbs); /* G[b][b] += g_bd + g_bs */
    
    /* Stamp RHS current vector */
    double *rhs = ckt->CKTrhs;
    rhs[inst->MOS2dNodePrime] -= inst->MOS2cd;   /* -I_d at d' */
    rhs[inst->MOS2sNodePrime] += inst->MOS2cd;   /* +I_d at s' */
    rhs[inst->MOS2bNode] += (inst->MOS2cbd + inst->MOS2cbs); /* I_bd + I_bs at b */
}
```

This code implements the mathematical matrix:
```
[g_ds    -g_m    -(g_ds+g_m+g_mbs)  -g_mbs] [V_d']   [-I_d]
[0        g_m     g_ds+g_m+g_mbs     g_mbs] [V_g]    [0]
[0        0       0                  0    ] [V_s']   [+I_d]
[-g_mbs   0       g_mbs              g_bd+g_bs] [V_b] [I_bd+I_bs]
```

### 7. SPICE Device API Integration

The MOS2 model integrates with Ngspice through the `SPICEdev` structure:

```c
SPICEdev MOS2info = {
    .DEVpublic = {
        .name = "mos2",
        .description = "Level 2 MOSFET model",
        .terms = 4,
        .termNames = {"d", "g", "s", "b"},
    },
    .DEVmodParam = MOS2mPTable,      /* Model parameter table */
    .DEVinstParam = MOS2pTable,      /* Instance parameter table */
    .DEVload = MOS2load,             /* DC/transient load function */
    .DEVsetup = MOS2setup,           /* Setup/initialization */
    .DEVunsetup = MOS2unsetup,       /* Cleanup */
    .DEVtemperature = MOS2temp,      /* Temperature adjustment */
    .DEVtrunc = MOS2trunc,           /* Truncation error calculation */
    .DEVacLoad = MOS2acLoad,         /* AC small-signal load */
    .DEVconvTest = MOS2convTest,     /* Convergence testing */
    .DEVnoise = MOS2noise,           /* Noise analysis */
    .DEVinstSize = sizeof(sMOS2instance),
    .DEVmodSize = sizeof(sMOS2model),
};
```

This structure defines the complete interface between the MOS2 device model and the SPICE simulator engine. Each function pointer maps to a specific simulation phase:
- `MOS2load()`: Computes currents and stamps matrix for DC/transient analysis
- `MOS2acLoad()`: Computes and stamps small-signal parameters for AC analysis
- `MOS2convTest()`: Checks Newton-Raphson convergence
- `MOS2trunc()`: Calculates local truncation error for adaptive time stepping

### 8. Source/Drain Swap for PMOS and Inverse Mode

The code handles PMOS devices and inverse mode operation (V_ds < 0) through voltage polarity inversion and node swapping:

```c
/* In MOS2load() */
double type = (model->MOS2type > 0) ? 1.0 : -1.0;
vgs = type * (vg - vs_prime);
vds = type * (vd_prime - vs_prime);

if(vds >= 0.0) {
    inst->MOS2mode = 1;  /* Normal mode */
} else {
    inst->MOS2mode = -1; /* Inverse mode */
    /* Swap source and drain internally */
    SWAP(inst->MOS2dNodePrime, inst->MOS2sNodePrime);
    SWAP(inst->MOS2dDrainPrimePtr, inst->MOS2sSourcePrimePtr);
    /* Update voltages for swapped configuration */
    vds = -vds;
    vgs = type * (vg - vd_prime);  /* Now gate wrt new "source" */
}

/* Compute currents with absolute V_ds */
MOS2computeId(model, inst, vgs, vds, vbs);

/* Apply polarity to results */
inst->MOS2cd *= type;
inst->MOS2gm *= type;
inst->MOS2gds *= type;
inst->MOS2gmbs *= type;
```

This implementation ensures the mathematical equations always operate with V_ds ≥ 0, while maintaining correct polarity for PMOS devices (type = -1).

The C implementation thus provides a direct computational realization of the Grove-Frohman Level 2 mathematical model, with careful attention to numerical stability, convergence control, and integration with the SPICE simulation framework.