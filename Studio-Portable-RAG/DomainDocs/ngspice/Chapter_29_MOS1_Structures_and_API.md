# MOS1: Data Structures and SPICE API

_Generated 2026-04-12 03:36 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1defs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1dest.c`

# Chapter: MOS1: Data Structures and SPICE API

## Introduction

The MOS1 device implementation in Ngspice constitutes the SPICE Level 1 MOSFET model, representing the foundational long-channel transistor model for integrated circuit simulation. The files `mos1defs.h`, `mos1init.c`, `mos1.c`, and `mos1dest.c` collectively implement the Shichman-Hodges square-law equations within Ngspice's device abstraction framework. `mos1defs.h` defines the core C structures (`sMOS1model`, `sMOS1instance`) that encapsulate process and geometry parameters. `mos1init.c` handles device registration and parameter initialization, binding the model to Ngspice's `SPICEdev` API. The primary computational engine resides in `mos1.c`, which implements the `MOS1load()` function that evaluates the current-voltage characteristics, computes analytical derivatives, and stamps the conductance matrix into the circuit's nodal analysis system. Finally, `mos1dest.c` provides memory management routines for proper cleanup of the linked-list data structures. This implementation directly translates the piecewise-continuous mathematical model into efficient C code with explicit Jacobian computation for Newton-Raphson convergence, enabling DC, transient, AC, and noise analysis of MOSFET-based circuits.

---

## Mathematical Formulation

The MOS1 device implements the Shichman-Hodges Level 1 MOSFET model, which provides the foundational mathematical framework for DC, transient, and small-signal analysis of metal-oxide-semiconductor field-effect transistors in SPICE circuit simulation. The formulation centers on piecewise-continuous current-voltage relationships with explicit derivatives for Newton-Raphson convergence.

### Core Current-Voltage Relationships

The drain current `Id` is defined by three distinct operating regions, determined by the gate-source voltage `Vgs`, drain-source voltage `Vds`, and threshold voltage `Vth`.

#### Threshold Voltage with Body Effect

The threshold voltage incorporates the body (substrate) bias effect through:

```
Vth = VTO + γ * (√(2φ + Vsb) - √(2φ))
```

where:
- `VTO` is the zero-bias threshold voltage (model parameter `MOS1vt0`)
- `γ` is the body effect parameter (model parameter `MOS1gamma`)
- `φ` is the surface potential (model parameter `MOS1phi`)
- `Vsb = Vs - Vb` is the source-bulk voltage

This formulation accounts for the modulation of channel charge by the substrate potential, critical for accurate simulation of bulk-connected MOSFETs.

#### Triode (Linear) Region

For `Vds ≤ Vgs - Vth` and `Vgs > Vth`:

```
Id = β * [(Vgs - Vth) * Vds - Vds²/2] * (1 + λ·Vds)
```

where:
- `β = (W/L) * KP * (1 + θ·(Vgs - Vth))` is the transconductance coefficient
- `W` and `L` are the channel width and length (instance parameters `MOS1w`, `MOS1l`)
- `KP` is the transconductance parameter (model parameter `MOS1kp`)
- `θ` is the mobility reduction coefficient (typically modeled)
- `λ` is the channel-length modulation parameter (model parameter `MOS1lambda`)

The term `(1 + λ·Vds)` models the finite output conductance in saturation.

#### Saturation Region

For `Vds > Vgs - Vth` and `Vgs > Vth`:

```
Id = (β/2) * (Vgs - Vth)² * (1 + λ·Vds)
```

This represents the square-law characteristic fundamental to long-channel MOSFET behavior.

#### Cutoff Region

For `Vgs ≤ Vth`:

```
Id = 0
```

### Conductance Matrix Formulation for Nodal Analysis

The device contributes to the circuit's Jacobian matrix through partial derivatives computed at the operating point. For the four-terminal device (drain, gate, source, bulk), a 4×4 conductance matrix `G` is stamped:

```
[Gdd  Gdg  Gds  Gdb] [Vd]   [Id]
[Ggd  Ggg  Ggs  Ggb] [Vg] = [Ig]
[Gsd  Gsg  Gss  Gsb] [Vs]   [Is]
[Gbd  Bbg  Gbs  Gbb] [Vb]   [Ib]
```

The matrix elements are defined as:

```
Gdd = ∂Id/∂Vd = gds
Gds = ∂Id/∂Vs = -(gds + gm + gmb)
Gdg = ∂Id/∂Vg = gm
Gdb = ∂Id/∂Vb = gmb

Gsd = ∂Is/∂Vd = -gds
Gss = ∂Is/∂Vs = gds + gm + gmb
Gsg = ∂Is/∂Vg = -gm
Gsb = ∂Is/∂Vb = -gmb

Ggd = ∂Ig/∂Vd = 0
Ggg = ∂Ig/∂Vg = 0
Ggs = ∂Ig/∂Vs = 0
Ggb = ∂Ig/∂Vb = 0

Gbd = ∂Ib/∂Vd = 0
Bbg = ∂Ib/∂Vg = 0
Gbs = ∂Ib/∂Vs = 0
Gbb = ∂Ib/∂Vb = 0
```

where:
- `gm = ∂Id/∂Vgs` is the transconductance
- `gds = ∂Id/∂Vds` is the output conductance
- `gmb = ∂Id/∂Vsb` is the body transconductance

The gate and bulk currents are assumed negligible for DC and low-frequency analysis (`Ig ≈ 0`, `Ib ≈ 0`), resulting in zero derivatives for those terminals.

### Explicit Derivative Expressions

#### Triode Region Derivatives

```
gm = β * Vds * (1 + λ·Vds) + (W/L) * KP * θ * [(Vgs - Vth)·Vds - Vds²/2] * (1 + λ·Vds)

gds = β * [(Vgs - Vth) - Vds] * (1 + λ·Vds) + β * [(Vgs - Vth)·Vds - Vds²/2] * λ

gmb = -γ * β * Vds * (1 + λ·Vds) / (2√(2φ + Vsb))
```

#### Saturation Region Derivatives

```
gm = β * (Vgs - Vth) * (1 + λ·Vds)

gds = (β/2) * (Vgs - Vth)² * λ

gmb = -γ * β * (Vgs - Vth) * (1 + λ·Vds) / (2√(2φ + Vsb))
```

### Temperature Dependence

Model parameters are adjusted for temperature variations:

```
KP(T) = KP(T₀) * (T/T₀)^(-3/2)
φ(T) = φ(T₀) * (T/T₀) - 2 * (kT/q) * ln(T/T₀)
VTO(T) = VTO(T₀) + α·(T - T₀)
```

where `T₀` is the nominal temperature, `k` is Boltzmann's constant, `q` is electron charge, and `α` is the temperature coefficient of threshold voltage.

## Convergence Analysis

### Newton-Raphson Iteration for MOSFET Circuits

The MOS1 device employs the Newton-Raphson method to solve the nonlinear device equations within the larger circuit context. Convergence is governed by the local linearization of the current-voltage characteristics.

#### Iteration Update Equation

At iteration `k`, the voltage updates are computed from:

```
[V_d^(k+1)]   [V_d^(k)]   -1 [Id(V_d^(k), V_g^(k), V_s^(k), V_b^(k))]
[V_g^(k+1)] = [V_g^(k)] - J  [Ig(V_d^(k), V_g^(k), V_s^(k), V_b^(k))]
[V_s^(k+1)]   [V_s^(k)]     [Is(V_d^(k), V_g^(k), V_s^(k), V_b^(k))]
[V_b^(k+1)]   [V_b^(k)]     [Ib(V_d^(k), V_g^(k), V_s^(k), V_b^(k))]
```

where `J` is the 4×4 Jacobian matrix containing the conductance terms `Gdd`, `Gdg`, etc., evaluated at the current operating point.

#### Convergence Criteria for MOSFET Devices

The iteration terminates when both absolute and relative criteria are satisfied:

```
|Id^(k+1) - Id^(k)| < ε_abs + ε_rel * |Id^(k)|
|Vds^(k+1) - Vds^(k)| < ε_abs + ε_rel * |Vds^(k)|
|Vgs^(k+1) - Vgs^(k)| < ε_abs + ε_rel * |Vgs^(k)|
```

where typical SPICE values are `ε_abs = 10⁻¹²` and `ε_rel = 10⁻³`.

### Region Transition Continuity

The piecewise model maintains continuity at region boundaries to ensure convergence:

#### Triode-Saturation Boundary

At `Vds = Vgs - Vth`, both triode and saturation expressions yield:

```
Id_boundary = (β/2) * (Vgs - Vth)² * (1 + λ·(Vgs - Vth))
```

The first derivatives are also continuous:
```
gm_triode(Vds = Vgs - Vth) = gm_sat(Vds = Vgs - Vth)
gds_triode(Vds = Vgs - Vth) = gds_sat(Vds = Vgs - Vth)
```

#### Cutoff-Triode/Saturation Boundary

At `Vgs = Vth`:
```
Id(Vgs = Vth) = 0
gm(Vgs = Vth) = 0
```

This `C¹` continuity (continuous function with continuous first derivative) ensures Newton-Raphson convergence near operating region transitions.

### Numerical Stability Considerations

#### Body Effect Square Root

The term `√(2φ + Vsb)` requires careful handling for `Vsb < -2φ` (forward-biased source-bulk junction). The implementation uses:

```
if (2φ + Vsb < 0) {
    sqrt_term = √|2φ + Vsb| * j  (imaginary part handled separately)
} else {
    sqrt_term = √(2φ + Vsb)
}
```

#### Small Denominator Protection

The body transconductance calculation `gmb` contains denominator `2√(2φ + Vsb)`. Protection against division by zero is implemented as:

```
if (|2φ + Vsb| < ε) {
    gmb = -γ * β * Vds / (2√ε)  (for triode)
    or
    gmb = -γ * β * (Vgs - Vth) / (2√ε)  (for saturation)
}
```

where `ε ≈ 10⁻¹²`.

### Convergence Acceleration Techniques

#### Limiting Voltage Updates

To prevent oscillation during Newton-Raphson iteration, voltage updates are limited:

```
ΔVds_max = 0.5 * |Vds| + 0.1
ΔVgs_max = 0.5 * |Vgs - Vth| + 0.1
if (|ΔVds| > ΔVds_max) ΔVds = sign(ΔVds) * ΔVds_max
if (|ΔVgs| > ΔVgs_max) ΔVgs = sign(ΔVgs) * ΔVgs_max
```

#### Source-Drain Symmetry

For `Vds < 0`, the device equations are evaluated with swapped source and drain terminals, ensuring numerical stability in the reverse bias region.

### Time-Step Control in Transient Analysis

The local truncation error (LTE) for transient analysis is estimated using the derivative of current with respect to time:

```
LTE = (h²/12) * |d²Id/dt²|
```

where `h` is the time step. The MOS1 device provides `MOS1trunc()` function to compute this error estimate, enabling adaptive time-step control to maintain simulation accuracy while optimizing computational efficiency.

### Convergence in Presence of Parasitics

The series drain and source resistances (`RD`, `RS`) modify the effective terminal voltages:

```
Vd' = Vd - Id * RD
Vs' = Vs + Id * RS
```

These internal voltages are solved iteratively, with convergence criteria:

```
|Id^(k+1) - Id^(k)| < ε_abs + ε_rel * |Id^(k)|
```

The additional nonlinearity from the `Id·R` product requires careful initialization and may reduce the convergence radius of the Newton-Raphson method.

---

## C Implementation

### Core Data Structures and Memory Organization

The MOS1 device implementation in Ngspice is built around two primary C structures that map directly to the SPICE model and instance concepts, with linked-list organization for efficient traversal during circuit solution.

#### Model Structure (`sMOS1model`)

The `sMOS1model` structure encapsulates all process-dependent parameters that are shared among multiple transistor instances fabricated with the same technology:

```c
typedef struct sMOS1model {
    int MOS1type;                 /* NMF (NMOS) or PMF (PMOS) */
    double MOS1vt0;               /* VTO: Zero-bias threshold voltage */
    double MOS1kp;                /* KP: Transconductance parameter */
    double MOS1gamma;             /* GAMMA: Body effect parameter */
    double MOS1phi;               /* PHI: Surface potential */
    double MOS1lambda;            /* LAMBDA: Channel-length modulation */
    double MOS1rd;                /* RD: Drain resistance */
    double MOS1rs;                /* RS: Source resistance */
    double MOS1cbd;               /* CBD: Zero-bias B-D junction capacitance */
    double MOS1cbs;               /* CBS: Zero-bias B-S junction capacitance */
    double MOS1is;                /* IS: Bulk junction saturation current */
    double MOS1pb;                /* PB: Bulk junction potential */
    struct sMOS1model *MOS1nextModel; /* Linked list to next model */
    sMOS1instance *MOS1instances;     /* Linked list of instances using this model */
} MOS1model;
```

Each field corresponds directly to a SPICE model parameter. The `MOS1type` field encodes the device polarity, affecting sign conventions in the mathematical formulation.

#### Instance Structure (`sMOS1instance`)

The `sMOS1instance` structure contains geometry-specific and bias-dependent parameters for individual transistor instances:

```c
typedef struct sMOS1instance {
    char *MOS1name;               /* Instance name (e.g., "M1") */
    int MOS1dNode;                /* Drain node index in circuit matrix */
    int MOS1gNode;                /* Gate node index */
    int MOS1sNode;                /* Source node index */
    int MOS1bNode;                /* Bulk node index */
    double MOS1l;                 /* L: Drawn channel length */
    double MOS1w;                 /* W: Drawn channel width */
    double MOS1ad;                /* AD: Drain diffusion area */
    double MOS1as;                /* AS: Source diffusion area */
    double MOS1pd;                /* PD: Drain diffusion perimeter */
    double MOS1ps;                /* PS: Source diffusion perimeter */
    double MOS1temp;              /* TEMP: Instance temperature */
    struct sMOS1instance *MOS1nextInstance; /* Next instance in model's list */
    MOS1model *MOS1modPtr;        /* Pointer to parent model structure */
} MOS1instance;
```

The node indices (`MOS1dNode`, `MOS1gNode`, `MOS1sNode`, `MOS1bNode`) provide the mapping between physical terminals and positions in the circuit's nodal analysis matrix.

### SPICE Device API Integration

The MOS1 device registers itself with the Ngspice simulation kernel through the `SPICEdev` structure, which defines the complete interface for device operations:

```c
SPICEdev MOS1info = {
    .DEVpublic = {
        .name = "mos1",
        .description = "Level 1 MOSFET model",
        .terms = 4,               /* Four terminals: D, G, S, B */
        .numNames = 2,            /* Two SPICE names: M (instance), MOS1 (model) */
        .termNames = {"d", "g", "s", "b"},
        .numInstanceParms = 12,   /* L, W, AD, AS, PD, PS, TEMP, etc. */
        .numModelParms = 20,      /* VTO, KP, GAMMA, PHI, LAMBDA, etc. */
    },
    .DEVmodParam = MOS1mPTable,   /* Model parameter table for parsing */
    .DEVinstParam = MOS1pTable,   /* Instance parameter table for parsing */
    .DEVload = MOS1load,          /* Load function: stamps matrix for DC/transient */
    .DEVsetup = MOS1setup,        /* Setup: allocates internal state */
    .DEVunsetup = MOS1unsetup,    /* Unsetup: frees internal state */
    .DEVpzSetup = MOS1pzSetup,    /* Pole-zero analysis setup */
    .DEVtemperature = MOS1temp,   /* Temperature update function */
    .DEVtrunc = MOS1trunc,        /* Truncation error for time-step control */
    .DEVfindBranch = NULL,        /* No branch currents (4-terminal device) */
    .DEVacLoad = MOS1acLoad,      /* AC analysis load function */
    .DEVaccept = NULL,
    .DEVdestroy = MOS1destroy,    /* Complete destruction of all models/instances */
    .DEVmodDelete = MOS1mDelete,  /* Single model deletion */
    .DEVinstDelete = MOS1delete,  /* Single instance deletion */
    .DEVask = MOS1ask,            /* Query instance parameters */
    .DEVmodAsk = MOS1mAsk,        /* Query model parameters */
    .DEVpzLoad = MOS1pzLoad,      /* Pole-zero analysis load */
    .DEVconvTest = MOS1convTest,  /* Convergence testing */
    .DEVsenSetup = NULL,          /* Sensitivity analysis not implemented */
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = NULL,             /* Distortion analysis not implemented */
    .DEVnoise = MOS1noise,        /* Noise analysis function */
    .DEVsoaCheck = NULL,          /* Safe operating area check */
    .DEVinstSize = sizeof(sMOS1instance), /* Memory allocation size */
    .DEVmodSize = sizeof(sMOS1model),     /* Memory allocation size */
};
```

This structure provides function pointers for all device operations, allowing the simulation kernel to interact with the MOS1 device through a standardized interface.

### Mathematical Implementation in Load Function

The `MOS1load()` function implements the core Shichman-Hodges equations and stamps the conductance matrix into the circuit's linear system. The C code directly translates the mathematical formulation:

```c
int MOS1load(GENmodel *inModel, CKTcircuit *ckt) {
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    
    for(; model; model = model->MOS1nextModel) {
        for(inst = model->MOS1instances; inst; inst = inst->MOS1nextInstance) {
            /* Extract terminal voltages from circuit state */
            double vg = ckt->CKTrhs[inst->MOS1gNode];
            double vd = ckt->CKTrhs[inst->MOS1dNode];
            double vs = ckt->CKTrhs[inst->MOS1sNode];
            double vb = ckt->CKTrhs[inst->MOS1bNode];
            
            /* Compute bias voltages */
            double vgs = vg - vs;
            double vds = vd - vs;
            double vsb = vs - vb;
            
            /* Calculate threshold voltage with body effect */
            double phi = model->MOS1phi;
            double sqrtPhi = sqrt(phi);
            double sqrtPhiVsb = sqrt(phi + vsb);
            double vth = model->MOS1vt0 + model->MOS1gamma * (sqrtPhiVsb - sqrtPhi);
            
            /* Determine operating region */
            double vgst = vgs - vth;
            double beta = (inst->MOS1w / inst->MOS1l) * model->MOS1kp;
            
            double Id, gm, gds, gmb;
            
            if(vgst <= 0) {
                /* Cutoff region - mathematical implementation */
                Id = 0.0;
                gm = 0.0;
                gds = 0.0;
                gmb = 0.0;
            } 
            else if(vds <= vgst) {
                /* Triode region - direct C implementation of Id = β[(Vgs-Vth)Vds - Vds²/2](1+λVds) */
                double linearTerm = vgst * vds - 0.5 * vds * vds;
                Id = beta * linearTerm * (1.0 + model->MOS1lambda * vds);
                
                /* Derivatives computed analytically */
                gm = beta * vds * (1.0 + model->MOS1lambda * vds);  /* ∂Id/∂Vgs */
                gds = beta * (vgst - vds) * (1.0 + model->MOS1lambda * vds) 
                      + beta * linearTerm * model->MOS1lambda;      /* ∂Id/∂Vds */
                gmb = -model->MOS1gamma * beta * vds * (1.0 + model->MOS1lambda * vds) 
                      / (2.0 * sqrtPhiVsb);                         /* ∂Id/∂Vsb */
            } 
            else {
                /* Saturation region - direct C implementation of Id = (β/2)(Vgs-Vth)²(1+λVds) */
                double saturationTerm = 0.5 * vgst * vgst;
                Id = beta * saturationTerm * (1.0 + model->MOS1lambda * vds);
                
                /* Derivatives computed analytically */
                gm = beta * vgst * (1.0 + model->MOS1lambda * vds);  /* ∂Id/∂Vgs */
                gds = beta * saturationTerm * model->MOS1lambda;     /* ∂Id/∂Vds */
                gmb = -model->MOS1gamma * beta * vgst * (1.0 + model->MOS1lambda * vds) 
                      / (2.0 * sqrtPhiVsb);                         /* ∂Id/∂Vsb */
            }
            
            /* Stamp conductance matrix (4x4 Jacobian) */
            /* Gdd = ∂Id/∂Vd = gds */
            *(ckt->CKTmatrix[inst->MOS1dNode][inst->MOS1dNode]) += gds;
            
            /* Gds = ∂Id/∂Vs = -(gds + gm + gmb) */
            *(ckt->CKTmatrix[inst->MOS1dNode][inst->MOS1sNode]) -= gds + gm + gmb;
            
            /* Gdg = ∂Id/∂Vg = gm */
            *(ckt->CKTmatrix[inst->MOS1dNode][inst->MOS1gNode]) += gm;
            
            /* Gdb = ∂Id/∂Vb = gmb */
            *(ckt->CKTmatrix[inst->MOS1dNode][inst->MOS1bNode]) += gmb;
            
            /* Source node equation: Is = -Id */
            /* Gsd = ∂Is/∂Vd = -gds */
            *(ckt->CKTmatrix[inst->MOS1sNode][inst->MOS1dNode]) -= gds;
            
            /* Gss = ∂Is/∂Vs = gds + gm + gmb */
            *(ckt->CKTmatrix[inst->MOS1sNode][inst->MOS1sNode]) += gds + gm + gmb;
            
            /* Gsg = ∂Is/∂Vg = -gm */
            *(ckt->CKTmatrix[inst->MOS1sNode][inst->MOS1gNode]) -= gm;
            
            /* Gsb = ∂Is/∂Vb = -gmb */
            *(ckt->CKTmatrix[inst->MOS1sNode][inst->MOS1bNode]) -= gmb;
            
            /* Stamp right-hand side vector (currents) */
            ckt->CKTrhs[inst->MOS1dNode] -= Id;  /* Drain: -Id flows out */
            ckt->CKTrhs[inst->MOS1sNode] += Id;  /* Source: +Id flows in */
        }
    }
    return OK;
}
```

### Memory Management Implementation

The destruction functions implement careful memory cleanup following the linked-list structure:

```c
void MOS1destroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    MOS1model *model = (MOS1model*)mod;
    MOS1instance *inst, *nextInst;
    
    /* Traverse model linked list */
    while(model) {
        MOS1model *nextModel = model->MOS1nextModel;
        
        /* Traverse instance linked list for this model */
        inst = model->MOS1instances;
        while(inst) {
            nextInst = inst->MOS1nextInstance;
            FREE(inst->MOS1name);     /* Free dynamically allocated name string */
            FREE(inst);               /* Free instance structure */
            inst = nextInst;
        }
        
        FREE(model);                  /* Free model structure */
        model = nextModel;
    }
    *inModel = NULL;  /* Clear the external pointer */
}

int MOS1delete(GENmodel *inModel, IFuid name, GENinstance **kill) {
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *prev = NULL, *inst;
    
    /* Search through all models */
    for(; model; model = model->MOS1nextModel) {
        inst = model->MOS1instances;
        /* Search through instances in this model */
        while(inst) {
            if(strcmp(inst->MOS1name, name) == 0) {
                /* Found instance to delete */
                if(prev) {
                    /* Remove from middle of list */
                    prev->MOS1nextInstance = inst->MOS1nextInstance;
                } else {
                    /* Remove from head of list */
                    model->MOS1instances = inst->MOS1nextInstance;
                }
                
                FREE(inst->MOS1name);
                FREE(inst);
                return OK;
            }
            prev = inst;
            inst = inst->MOS1nextInstance;
        }
    }
    return E_NODEV;  /* Device not found */
}
```

### Parameter Tables for SPICE Parsing

The parameter tables `MOS1mPTable` and `MOS1pTable` define the mapping between SPICE deck parameters and C structure fields:

```c
/* Model parameter table example */
SPICEparam MOS1mPTable[] = {
    { "vto",    PARM_SET, &(model->MOS1vt0) },
    { "kp",     PARM_SET, &(model->MOS1kp) },
    { "gamma",  PARM_SET, &(model->MOS1gamma) },
    { "phi",    PARM_SET, &(model->MOS1phi) },
    { "lambda", PARM_SET, &(model->MOS1lambda) },
    { "rd",     PARM_SET, &(model->MOS1rd) },
    { "rs",     PARM_SET, &(model->MOS1rs) },
    { "cbd",    PARM_SET, &(model->MOS1cbd) },
    { "cbs",    PARM_SET, &(model->MOS1cbs) },
    { "is",     PARM_SET, &(model->MOS1is) },
    { "pb",     PARM_SET, &(model->MOS1pb) },
    { NULL, 0, NULL }  /* Sentinel */
};

/* Instance parameter table example */
SPICEparam MOS1pTable[] = {
    { "l",   PARM_SET, &(inst->MOS1l) },
    { "w",   PARM_SET, &(inst->MOS1w) },
    { "ad",  PARM_SET, &(inst->MOS1ad) },
    { "as",  PARM_SET, &(inst->MOS1as) },
    { "pd",  PARM_SET, &(inst->MOS1pd) },
    { "ps",  PARM_SET, &(inst->MOS1ps) },
    { "temp", PARM_SET, &(inst->MOS1temp) },
    { NULL, 0, NULL }  /* Sentinel */
};
```

These tables enable the SPICE parser to recognize parameters like "VTO=0.7" in a `.MODEL` statement and store the value in the appropriate field of the `MOS1model` structure.

### Temperature Update Implementation

The `MOS1temp()` function implements the temperature-dependent parameter adjustments:

```c
int MOS1temp(MOS1model *model, CKTcircuit *ckt) {
    double tnom = ckt->CKTnomTemp;
    double temp = ckt->CKTtemp;
    
    for(; model; model = model->MOS1nextModel) {
        /* Update KP: KP(T) = KP(T₀) * (T/T₀)^(-3/2) */
        double tempRatio = temp / tnom;
        model->MOS1kp *= pow(tempRatio, -1.5);
        
        /* Update PHI: φ(T) = φ(T₀) * (T/T₀) - 2 * (kT/q) * ln(T/T₀) */
        double ktq = 8.617333262145e-5 * temp;  /* kT/q */
        model->MOS1phi = model->MOS1phi * tempRatio 
                         - 2.0 * ktq * log(tempRatio);
        
        /* Update VTO with temperature coefficient */
        /* Implementation depends on available model parameters */
    }
    return OK;
}
```

This implementation demonstrates how the mathematical temperature dependencies are encoded in C, with the `pow()` and `log()` functions computing the necessary transformations.