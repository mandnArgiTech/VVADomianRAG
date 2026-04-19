# Resistor: Geometry, Matrix Setup, API, and SOA

_Generated 2026-04-12 20:34 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/ressetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/res.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resdest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/ressoachk.c`

# Chapter: Resistor: Geometry, Matrix Setup, API, and SOA

## Technical Introduction

This chapter documents the Ngspice implementation of the resistor device model, focusing on its geometric parameterization, matrix integration, SPICEdev API binding, and Safe Operating Area (SOA) enforcement. The resistor model in Ngspice extends beyond simple Ohm's Law to incorporate physical layout effects, temperature dependencies, and reliability constraints essential for modern integrated circuit simulation.

The core implementation spans ten critical C files that define the resistor's behavior within the SPICE simulation engine:

- **`ressetup.c`**: Allocates matrix elements for Modified Nodal Analysis (MNA) formulation, handling both external nodes and internal distributed nodes for long resistors.
- **`resmask.c`**: Defines parameter masks and validation logic for instance parameters.
- **`resmpar.c`**: Implements model parameter processing and default value assignment.
- **`resask.c`**: Provides query interface for retrieving simulation results and device states.
- **`resinit.c`**: Registers the resistor model with the SPICE kernel via the `SPICEdev` structure.
- **`res.c`**: Main device implementation containing core algorithms.
- **`resdel.c`**: Instance deletion and memory cleanup.
- **`resmdel.c`**: Model deletion and resource management.
- **`resdest.c`**: Device destruction during circuit teardown.
- **`ressoachk.c`**: Implements SOA boundary checking with configurable violation handling.

These files collectively implement a geometry-aware resistor model that calculates resistance from physical dimensions (length, width, sheet resistance) with correction factors for narrow-width and short-channel effects. The model supports temperature scaling through first and second-order coefficients, integrates with Ngspice's matrix solver via the standardized SPICEdev API, and enforces SOA constraints to prevent unrealistic operating conditions during simulation.

## Mathematical Formulation

The resistor model in Ngspice implements the Modified Nodal Analysis (MNA) formulation for circuit simulation. The core mathematical representation follows Ohm's law extended to include geometric scaling, temperature dependence, and safe operating area constraints.

### 1. Geometric Resistance Model

The fundamental resistance is computed from geometric parameters:

```
R_geo = RSH * (L / W) * (1 + TC1*(T - TNOM) + TC2*(T - TNOM)²)
```

Where:
- `RSH` = Sheet resistance (Ω/□)
- `L` = Length (meters)
- `W` = Width (meters)
- `TC1`, `TC2` = First and second order temperature coefficients
- `T` = Operating temperature (Kelvin)
- `TNOM` = Nominal temperature (Kelvin)

For multi-finger layouts with `NF` fingers:

```
R_total = R_geo / NF
```

### 2. Matrix Stamping Formulation

The resistor contributes to the MNA matrix `G` and right-hand side vector `I` according to:

For a linear resistor between nodes `n1` and `n2`:

```
G[n1][n1] += G_eq
G[n1][n2] -= G_eq
G[n2][n1] -= G_eq
G[n2][n2] += G_eq
```

Where `G_eq = 1/R_total` is the equivalent conductance.

For transient analysis with voltage-dependent resistance `R(V)`, the Jacobian requires derivative terms:

```
∂I/∂V1 = ∂/∂V1[V1/R(V1-V2) - V2/R(V1-V2)]
∂I/∂V2 = ∂/∂V2[V1/R(V1-V2) - V2/R(V1-V2)]
```

These partial derivatives are computed analytically from the resistance function and stamped into the matrix during Newton-Raphson iterations.

### 3. Temperature Scaling Mathematics

The temperature-dependent resistance follows:

```
R(T) = R(TNOM) * [1 + TC1*(T - TNOM) + TC2*(T - TNOM)²]
```

The derivatives for sensitivity analysis:

```
∂R/∂T = R(TNOM) * [TC1 + 2*TC2*(T - TNOM)]
∂²R/∂T² = 2 * R(TNOM) * TC2
```

### 4. Safe Operating Area (SOA) Constraints

The resistor SOA is defined by multiple constraints:

**Power Dissipation Limit:**
```
P_max = V * I ≤ P_MAX_SPEC
```

**Voltage Limit:**
```
|V| ≤ V_MAX
```

**Current Density Limit:**
```
J = I / (W * t) ≤ J_MAX
```
Where `t` is the conductor thickness.

**Thermal Runaway Condition:**
```
∂P/∂T > ∂Q_diss/∂T
```
Where `Q_diss` is the heat dissipation capability.

The SOA boundary is the intersection of these constraints, forming a convex polyhedron in the (V, I, T) space.

### 5. Noise Analysis Formulation

**Thermal Noise (Johnson-Nyquist):**
```
S_v(f) = 4 * k_B * T * R
```
Where `k_B` is Boltzmann's constant.

**Flicker Noise (1/f):**
```
S_v(f) = K_F / (W * L * f^AF)
```
Where `K_F` is the flicker noise coefficient and `AF` is the frequency exponent.

The total noise power spectral density:
```
S_total(f) = 4k_BTR + K_F/(W*L*f^AF)
```

### 6. Sensitivity Analysis

Using the adjoint method for parameter sensitivity:

```
∂V_out/∂p = λᵀ * [∂G/∂p * V - ∂I/∂p]
```

For resistor parameters `p ∈ {RSH, L, W, TC1, TC2}`:

```
∂G/∂RSH = -G² * (L/W) * (1 + TC1*(T-TNOM) + TC2*(T-TNOM)²)
∂G/∂L = -G² * (RSH/W) * (1 + TC1*(T-TNOM) + TC2*(T-TNOM)²)
∂G/∂W = G² * (RSH*L/W²) * (1 + TC1*(T-TNOM) + TC2*(T-TNOM)²)
```

## Convergence Analysis

### 1. Newton-Raphson Convergence Criteria

The resistor model convergence is tested using:

```
|ΔV| < ε_V = ε_abs + ε_rel * max(|V|, V_min)
|ΔI| < ε_I = ε_abs + ε_rel * max(|I|, I_min)
```

Where:
- `ε_abs` = Absolute tolerance (typically 1e-12)
- `ε_rel` = Relative tolerance (typically 1e-6)
- `V_min`, `I_min` = Minimum values to avoid division by zero

### 2. Local Truncation Error (LTE) Control

For transient analysis, the LTE is estimated using:

```
LTE = |(h²/2) * d²I/dt²| + |(h³/6) * d³I/dt³|
```

Where `h` is the time step. The derivatives are computed from:

```
d²I/dt² = d/dt[ (1/R) * dV/dt ] = (1/R) * d²V/dt² - (1/R²) * dR/dV * (dV/dt)²
```

The time step is adapted to maintain:
```
LTE < ε_LTE * max(|I|, I_min)
```

### 3. Numerical Conditioning Analysis

The resistor matrix stamp can cause ill-conditioning when:

**Extreme Resistance Values:**
```
cond(G) ≈ max(R, 1/R) / min(R, 1/R)
```

Regularization is applied for very large or small resistances:

```
G_eff = 1/(R + δ) where δ = ε_machine * max(1, |R|)
```

**Geometric Parameter Sensitivity:**
The condition number with respect to geometric parameters:

```
κ = ||∂G/∂θ|| * ||θ|| / ||G||
```

Where `θ = [L, W, RSH]`. Ill-conditioning occurs when `κ > 1/ε_machine`.

### 4. SOA Convergence Challenges

The SOA constraints introduce discontinuities that affect convergence:

**Power Limit Boundary:**
```
g(V,I) = V*I - P_max = 0
```

The gradient at the boundary:
```
∇g = [I, V]
```

Newton-Raphson may oscillate near this boundary. Damping is applied:

```
Δx_new = α * Δx where α = min(1, 0.5/||∇g||)
```

**Thermal Coupling:**
The temperature-resistance feedback loop:

```
R(T) → I(V,R) → P(I,V) → ΔT(P) → R(T+ΔT)
```

This can create numerical instability. The convergence criterion includes thermal stability:

```
|ΔT| < ε_T = ε_abs + ε_rel * T
```

### 5. Monte Carlo Statistical Convergence

For statistical analysis with `N` samples, the mean and variance converge as:

```
|μ_N - μ| < t_α * σ/√N
|σ_N² - σ²| < χ²_α * σ²/√(2N)
```

Where `t_α` and `χ²_α` are statistical critical values. The simulation continues until:

```
max(|Δμ|/μ, |Δσ|/σ) < ε_stat
```

### 6. Harmonic Balance Convergence

For frequency domain analysis, the convergence of harmonic components:

```
|X_k^{(n+1)} - X_k^{(n)}| < ε_HB * max(|X_k|, X_min)
```

Where `X_k` is the k-th harmonic component. The resistor nonlinearity generates harmonics through:

```
I(V) = V/R(V) = V * [G_0 + G_1*V + G_2*V² + ...]
```

The convergence rate depends on the nonlinearity coefficients `G_n`.

### 7. Implementation-Specific Convergence Enhancements

**Voltage Limiting:**
```
V_new = V_old + min(max(ΔV, -V_limit), V_limit)
```
Where `V_limit = 0.5 * (|V_old| + V_t)` and `V_t` is thermal voltage.

**Pseudo-Transient Continuation:**
For DC operating point finding, a continuation parameter `λ` is introduced:

```
G(V, λ) = λ * G_nonlinear(V) + (1-λ) * G_linear
```
`λ` is gradually increased from 0 to 1.

**Adaptive Damping:**
The damping factor `α` is adjusted based on convergence history:

```
α_{n+1} = 
  0.5 * α_n if oscillations detected
  min(1.1 * α_n, 1) if monotonic convergence
  0.7 * α_n if divergence detected
```

This mathematical formulation provides the complete SPICE-based analysis framework for the resistor model, covering geometric scaling, matrix integration, API binding, and SOA enforcement within the Ngspice simulation engine.

## C Implementation

### **Core Data Structures and SPICEdev API Binding**

The Ngspice resistor model is implemented through a hierarchical structure of C data types and a standardized `SPICEdev` API binding, which provides the interface between the device model and the SPICE simulation kernel.

#### **Instance and Model Structures (`resdefs.h`)**

The fundamental data containers for a resistor are defined in `resdefs.h`. The `sRESinstance` structure holds the state and parameters for a single resistor instance in the circuit netlist, while the `sRESmodel` structure holds the global model parameters shared by multiple instances.

```c
/* resdefs.h - Resistor Instance Structure */
typedef struct sRESinstance {
    struct sRESmodel *RESmodPtr;    /* Pointer to model */
    struct sRESinstance *RESnextInstance; /* Linked list pointer */
    
    /* Node connections */
    int RESposNode;     /* Positive node */
    int RESnegNode;     /* Negative node */
    int RESposPrimeNode; /* Internal node for geometry effects */
    int RESnegPrimeNode; /* Internal node for distributed effects */
    
    /* Resistance parameters */
    double RESresist;    /* Nominal resistance at Tnom */
    double RESwidth;     /* Physical width (geometry) */
    double RESlength;    /* Physical length (geometry) */
    double RESsheetRes;  /* Sheet resistance (Ω/□) */
    double RESnarrow;    /* Narrow width correction */
    double RESshort;     /* Short channel correction */
    
    /* Temperature coefficients */
    double REStc1;       /* First-order temperature coefficient */
    double REStc2;       /* Second-order temperature coefficient */
    double REStemp;      /* Current temperature */
    double REStnom;      /* Nominal temperature */
    
    /* Matrix pointers */
    double *RESposPosPtr;    /* G[pos][pos] */
    double *RESposNegPtr;    /* G[pos][neg] */
    double *RESnegPosPtr;    /* G[neg][pos] */
    double *RESnegNegPtr;    /* G[neg][neg] */
    double *RESposPrimePosPrimePtr; /* Internal node stamps */
    
    /* State variables */
    double REScurrent;   /* Current through resistor */
    double RESvoltage;   /* Voltage across resistor */
    double RESpower;     /* Instantaneous power dissipation */
    double RESconduct;   /* Conductance (1/R) */
    
    /* SOA monitoring */
    double RESmaxPower;  /* Maximum power rating */
    double RESmaxVoltage; /* Maximum voltage rating */
    double RESmaxCurrent; /* Maximum current rating */
    int RESsoaViolation; /* SOA violation flag */
    
    /* Flags */
    unsigned RESwidthGiven :1;   /* Width specified */
    unsigned RESlengthGiven :1;  /* Length specified */
    unsigned RESsheetResGiven :1; /* Sheet resistance specified */
    unsigned RESnarrowGiven :1;  /* Narrow width correction given */
    unsigned RESshortGiven :1;   /* Short channel correction given */
} RESinstance;

/* Resistor Model Structure */
typedef struct sRESmodel {
    int RESmodType;              /* Model type identifier */
    struct sRESmodel *RESnextModel; /* Linked list pointer */
    RESinstance *RESinstances;   /* List of instances */
    
    /* Model parameters */
    double RESsheetRes;          /* Default sheet resistance */
    double RESdefWidth;          /* Default width */
    double RESdefLength;         /* Default length */
    double REStc1;               /* Default TC1 */
    double REStc2;               /* Default TC2 */
    double REStnom;              /* Default nominal temperature */
    
    /* Geometry correction parameters */
    double RESdw;                /* Width offset */
    double RESdl;                /* Length offset */
    double RESrsh;               /* Sheet resistance */
    double RESnarrow;            /* Narrow width parameter */
    double RESshort;             /* Short channel parameter */
    
    /* SOA defaults */
    double RESmaxPower;          /* Default max power */
    double RESmaxVoltage;        /* Default max voltage */
    double RESmaxCurrent;        /* Default max current */
} RESmodel;
```

#### **SPICEdev API Structure (`resinit.c`)**

The resistor model registers itself with the SPICE kernel through the `SPICEdev` structure, which defines function pointers for all device operations. This follows the standard Ngspice device API pattern.

```c
/* resinit.c - SPICEdev Structure for Resistor */
SPICEdev RESinfo = {
    .DEVpublic = {
        .name = "resistor",
        .description = "Linear/Nonlinear resistor with geometry effects",
        .terms = 2,  /* Two-terminal device */
        .numNames = 2,
        .termNames = (char *[]){"p", "n"},
        .numInstanceParms = 15,
        .instanceParms = (IFparm[]) {
            IOP("r", RES_RESIST, IF_REAL, "Resistance"),
            IOP("w", RES_WIDTH, IF_REAL, "Width"),
            IOP("l", RES_LENGTH, IF_REAL, "Length"),
            IOP("tc1", RES_TC1, IF_REAL, "First order temp coeff"),
            IOP("tc2", RES_TC2, IF_REAL, "Second order temp coeff"),
            IOP("temp", RES_TEMP, IF_REAL, "Operating temperature"),
            IOP("m", RES_M, IF_REAL, "Multiplier"),
            IOP("p", RES_POWER, IF_REAL, "Power"),
            IOP("maxpower", RES_MAXPOWER, IF_REAL, "Maximum power"),
            IOP("maxvoltage", RES_MAXVOLTAGE, IF_REAL, "Maximum voltage"),
            IOP("maxcurrent", RES_MAXCURRENT, IF_REAL, "Maximum current"),
            IOP("narrow", RES_NARROW, IF_REAL, "Narrow width correction"),
            IOP("short", RES_SHORT, IF_REAL, "Short channel correction"),
            IOP("rsh", RES_SHEETRES, IF_REAL, "Sheet resistance"),
            IOP("scale", RES_SCALE, IF_REAL, "Scale factor"),
        },
        .numModelParms = 10,
        .modelParms = (IFparm[]) {
            IOP("rsh", RES_MOD_SHEETRES, IF_REAL, "Sheet resistance"),
            IOP("defw", RES_MOD_DEFWIDTH, IF_REAL, "Default width"),
            IOP("defl", RES_MOD_DEFLENGTH, IF_REAL, "Default length"),
            IOP("tc1", RES_MOD_TC1, IF_REAL, "First order temp coeff"),
            IOP("tc2", RES_MOD_TC2, IF_REAL, "Second order temp coeff"),
            IOP("tnom", RES_MOD_TNOM, IF_REAL, "Nominal temperature"),
            IOP("dw", RES_MOD_DW, IF_REAL, "Width offset"),
            IOP("dl", RES_MOD_DL, IF_REAL, "Length offset"),
            IOP("narrow", RES_MOD_NARROW, IF_REAL, "Narrow width parameter"),
            IOP("short", RES_MOD_SHORT, IF_REAL, "Short channel parameter"),
        },
    },
    
    /* Function pointers */
    .DEVparam = RESparam,
    .DEVmodParam = RESmParam,
    .DEVload = RESload,
    .DEVsetup = RESsetup,
    .DEVunsetup = RESunsetup,
    .DEVpzSetup = RESpzSetup,
    .DEVtemperature = REStemp,
    .DEVtrunc = REStrunc,
    .DEVfindBranch = RESfindBr,
    .DEVacLoad = RESacLoad,
    .DEVaccept = RESaccept,
    .DEVdestroy = RESdestroy,
    .DEVmodDelete = RESmDelete,
    .DEVdelete = RESdelete,
    .DEVsetic = RESgetic,
    .DEVask = RESask,
    .DEVmodAsk = RESmAsk,
    .DEVpzLoad = RESpzLoad,
    .DEVconvTest = RESconvTest,
    .DEVsenSetup = RESsSetup,
    .DEVsenLoad = RESsLoad,
    .DEVsenUpdate = RESsUpdate,
    .DEVsenAcLoad = RESsAcLoad,
    .DEVsenPrint = RESsPrint,
    .DEVsenDisto = RESdisto,
    .DEVsenNoise = RESnoise,
    .DEVsoaCheck = RESsoaCheck,
    
    /* Size information */
    .DEVinstSize = sizeof(RESinstance),
    .DEVmodSize = sizeof(RESmodel),
};
```

### **Geometry-Based Resistance Calculation (`resparam.c`)**

The resistance calculation incorporates geometry effects through sheet resistance and correction factors. The C implementation maps directly to the mathematical formulation for geometry-corrected resistance.

```c
/* resparam.c - Geometry-Aware Resistance Calculation */
int RESparam(int param, IFvalue *value, GENinstance *genInst, IFvalue *select)
{
    RESinstance *inst = (RESinstance *)genInst;
    
    switch (param) {
        case RES_RESIST:
            /* Direct resistance specification */
            inst->RESresist = value->rValue;
            inst->RESconduct = 1.0 / inst->RESresist;
            break;
            
        case RES_WIDTH:
            inst->RESwidth = value->rValue;
            inst->RESwidthGiven = 1;
            break;
            
        case RES_LENGTH:
            inst->RESlength = value->rValue;
            inst->RESlengthGiven = 1;
            break;
            
        case RES_SHEETRES:
            inst->RESsheetRes = value->rValue;
            inst->RESsheetResGiven = 1;
            break;
            
        case RES_NARROW:
            inst->RESnarrow = value->rValue;
            inst->RESnarrowGiven = 1;
            break;
            
        case RES_SHORT:
            inst->RESshort = value->rValue;
            inst->RESshortGiven = 1;
            break;
    }
    
    /* Calculate geometry-based resistance if dimensions given */
    if (inst->RESwidthGiven && inst->RESlengthGiven && 
        (inst->RESsheetResGiven || inst->RESmodPtr->RESsheetRes > 0)) {
        
        double sheetRes = inst->RESsheetResGiven ? 
                         inst->RESsheetRes : inst->RESmodPtr->RESsheetRes;
        double width = inst->RESwidth;
        double length = inst->RESlength;
        
        /* Apply narrow width correction: R = Rsh * (L/W) * (1 + narrow/W) */
        if (inst->RESnarrowGiven && width > 0) {
            width = width - 2 * inst->RESnarrow;
            if (width <= 0) width = 1e-12; /* Prevent division by zero */
        }
        
        /* Apply short channel correction: R = Rsh * (L/W) * (1 + short/L) */
        if (inst->RESshortGiven && length > 0) {
            length = length - 2 * inst->RESshort;
            if (length <= 0) length = 1e-12;
        }
        
        /* Calculate final resistance: R = Rsh * (L/W) */
        if (width > 0 && length > 0) {
            inst->RESresist = sheetRes * (length / width);
            inst->RESconduct = 1.0 / inst->RESresist;
        }
    }
    
    return OK;
}
```

### **Matrix Setup and Node Allocation (`ressetup.c`)**

The matrix setup function allocates matrix elements for the resistor's contributions to the Modified Nodal Analysis (MNA) system. This includes handling internal nodes for distributed resistance effects.

```c
/* ressetup.c - Matrix Element Allocation */
int RESsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    
    /* Loop through all resistor models */
    for (; model != NULL; model = model->RESnextModel) {
        
        /* Loop through all instances in this model */
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            /* Allocate matrix elements for external nodes */
            inst->RESposPosPtr = SMPmakeElt(matrix, inst->RESposNode, 
                                           inst->RESposNode);
            inst->RESposNegPtr = SMPmakeElt(matrix, inst->RESposNode, 
                                           inst->RESnegNode);
            inst->RESnegPosPtr = SMPmakeElt(matrix, inst->RESnegNode, 
                                           inst->RESposNode);
            inst->RESnegNegPtr = SMPmakeElt(matrix, inst->RESnegNode, 
                                           inst->RESnegNode);
            
            /* Allocate internal nodes for distributed effects if needed */
            if (inst->RESlength > 100e-6) { /* Long resistor needs distribution */
                inst->RESposPrimeNode = *states;
                (*states)++;
                inst->RESnegPrimeNode = *states;
                (*states)++;
                
                /* Allocate matrix elements for internal nodes */
                inst->RESposPrimePosPrimePtr = SMPmakeElt(matrix, 
                    inst->RESposPrimeNode, inst->RESposPrimeNode);
                /* ... additional internal node allocations ... */
            }
            
            /* Initialize SOA violation flag */
            inst->RESsoaViolation = 0;
        }
    }
    
    return OK;
}
```

### **DC Load Function - Matrix Stamping (`resload.c`)**

The load function implements the core mathematical operation of stamping the resistor's conductance into the MNA matrix. This directly implements Ohm's Law in matrix form.

```c
/* resload.c - DC Matrix Loading */
int RESload(GENmodel *inModel, CKTcircuit *ckt)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    double g; /* Conductance */
    
    for (; model != NULL; model = model->RESnextModel) {
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            /* Apply temperature scaling to resistance */
            double R = inst->RESresist;
            if (inst->REStc1 != 0.0 || inst->REStc2 != 0.0) {
                double deltaT = inst->REStemp - inst->REStnom;
                R = inst->RESresist * (1.0 + inst->REStc1 * deltaT + 
                                      inst->REStc2 * deltaT * deltaT);
            }
            
            /* Calculate conductance */
            g = 1.0 / R;
            inst->RESconduct = g;
            
            /* Get node voltages */
            double v_pos = ckt->CKTrhs[inst->RESposNode];
            double v_neg = ckt->CKTrhs[inst->RESnegNode];
            inst->RESvoltage = v_pos - v_neg;
            
            /* Calculate current: I = G * V */
            inst->REScurrent = g * inst->RESvoltage;
            
            /* Stamp conductance matrix: [G -G; -G G] */
            *(inst->RESposPosPtr) += g;
            *(inst->RESposNegPtr) -= g;
            *(inst->RESnegPosPtr) -= g;
            *(inst->RESnegNegPtr) += g;
            
            /* Stamp RHS vector for internal nodes if distributed */
            if (inst->RESposPrimeNode >= 0) {
                /* Distributed resistor model: split into segments */
                double g_segment = g / 2.0; /* Two segments for simplicity */
                /* Stamp internal node matrix elements... */
            }
            
            /* Calculate power dissipation: P = V * I */
            inst->RESpower = inst->RESvoltage * inst->REScurrent;
            
            /* Check SOA violations */
            if (inst->RESpower > inst->RESmaxPower) {
                inst->RESsoaViolation = 1;
                ckt->CKTsoaViolation = 1;
            }
            if (fabs(inst->RESvoltage) > inst->RESmaxVoltage) {
                inst->RESsoaViolation = 1;
                ckt->CKTsoaViolation = 1;
            }
            if (fabs(inst->REScurrent) > inst->RESmaxCurrent) {
                inst->RESsoaViolation = 1;
                ckt->CKTsoaViolation = 1;
            }
        }
    }
    
    return OK;
}
```

### **Temperature Scaling Implementation (`restemp.c`)**

The temperature scaling function implements the mathematical model for temperature-dependent resistance, updating instance parameters based on circuit temperature.

```c
/* restemp.c - Temperature Scaling */
int REStemp(GENmodel *inModel, CKTcircuit *ckt)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    
    for (; model != NULL; model = model->RESnextModel) {
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            /* Use circuit temperature if instance temperature not specified */
            if (!inst->REStempGiven) {
                inst->REStemp = ckt->CKTtemp;
            }
            
            /* Apply temperature scaling to geometry-corrected resistance */
            if (inst->REStc1 != 0.0 || inst->REStc2 != 0.0) {
                double deltaT = inst->REStemp - inst->REStnom;
                double scaleFactor = 1.0 + inst->REStc1 * deltaT + 
                                   inst->REStc2 * deltaT * deltaT;
                
                /* Store temperature-scaled conductance for load function */
                inst->RESconduct = 1.0 / (inst->RESresist * scaleFactor);
            } else {
                inst->RESconduct = 1.0 / inst->RESresist;
            }
            
            /* Update SOA limits with temperature derating */
            if (inst->REStemp > inst->REStnom) {
                /* Derate power rating: typically 1% per °C above Tnom */
                double derateFactor = 1.0 - 0.01 * (inst->REStemp - inst->REStnom);
                if (derateFactor < 0.5) derateFactor = 0.5; /* Limit derating */
                inst->RESmaxPower *= derateFactor;
            }
        }
    }
    
    return OK;
}
```

### **Safe Operating Area Checking (`ressoachk.c`)**

The SOA checking function implements the boundary checks for power, voltage, and current limits, providing warnings or errors when violations occur.

```c
/* ressoachk.c - Safe Operating Area Verification */
int RESsoaCheck(GENmodel *inModel, CKTcircuit *ckt)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    int violationCount = 0;
    
    for (; model != NULL; model = model->RESnextModel) {
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            if (inst->RESsoaViolation) {
                violationCount++;
                
                /* Log SOA violation details */
                if (ckt->CKTsoaDebug) {
                    printf("RESISTOR SOA VIOLATION at instance %s:\n", 
                           inst->GENname);
                    printf("  Voltage: %.6e V (Limit: %.6e V)\n", 
                           fabs(inst->RESvoltage), inst->RESmaxVoltage);
                    printf("  Current: %.6e A (Limit: %.6e A)\n", 
                           fabs(inst->REScurrent), inst->RESmaxCurrent);
                    printf("  Power: %.6e W (Limit: %.6e W)\n", 
                           inst->RESpower, inst->RESmaxPower);
                    printf("  Temperature: %.2f C\n", inst->REStemp - 273.15);
                }
                
                /* Apply action based on SOA mode */
                switch (ckt->CKTsoaMode) {
                    case SOA_WARN:
                        /* Just warn and continue */
                        printf("WARNING: Resistor %s exceeds SOA limits\n",
                               inst->GENname);
                        break;
                        
                    case SOA_ERROR:
                        /* Flag error but continue iteration */
                        ckt->CKTerror = E_SOA;
                        break;
                        
                    case SOA_CLAMP:
                        /* Clamp to limits by adjusting matrix */
                        if (inst->RESpower > inst->RESmaxPower) {
                            /* Reduce conductance to limit power */
                            double g_clamp = inst->RESmaxPower / 
                                           (inst->RESvoltage * inst->RESvoltage);
                            if (g_clamp < inst->RESconduct) {
                                /* Update matrix with clamped conductance */
                                double delta_g = g_clamp - inst->RESconduct;
                                *(inst->RESposPosPtr) += delta_g;
                                *(inst->RESposNegPtr) -= delta_g;
                                *(inst->RESnegPosPtr) -= delta_g;
                                *(inst->RESnegNegPtr) += delta_g;
                                inst->RESconduct = g_clamp;
                            }
                        }
                        break;
                }
            }
            
            /* Reset violation flag for next iteration */
            inst->RESsoaViolation = 0;
        }
    }
    
    if (violationCount > 0 && ckt->CKTsoaMode == SOA_ERROR) {
        return E_SOA;
    }
    
    return OK;
}
```

### **Convergence Testing (`resconv.c`)**

The convergence test function implements the mathematical criteria for determining when the Newton-Raphson iteration has converged for resistor instances.

```c
/* resconv.c - Convergence Testing */
int RESconvTest(GENmodel *inModel, CKTcircuit *ckt)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    double tol, diff, max;
    int converged = 1;
    
    for (; model != NULL; model = model->RESnextModel) {
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            /* Test voltage convergence: |ΔV| < ε_abs + ε_rel * max(|V|, V_min) */
            double v_old = inst->RESvoltage;
            double v_new = ckt->CKTrhs[inst->RESposNode] - 
                          ckt->CKTrhs[inst->RESnegNode];
            diff = fabs(v_new - v_old);
            max = MAX(fabs(v_new), fabs(v_old));
            max = MAX(max, ckt->CKTvoltTol);
            tol = ckt->CKTreltol * max + ckt->CKTvoltTol;
            
            if (diff > tol) {
                converged = 0;
                if (ckt->CKTconvDebug) {
                    printf("RES conv fail V: diff=%.2e, tol=%.2e\n", diff, tol);
                }
            }
            
            /* Test current convergence: |ΔI| < ε_abs + ε_rel * max(|I|, I_min) */
            double i_old = inst->REScurrent;
            double i_new = inst->RESconduct * v_new;
            diff = fabs(i_new - i_old);
            max = MAX(fabs(i_new), fabs(i_old));
            max = MAX(max, ckt->CKTcurTol);
            tol = ckt->CKTreltol * max + ckt->CKTcurTol;
            
            if (diff > tol) {
                converged = 0;
                if (ckt->CKTconvDebug) {
                    printf("RES conv fail I: diff=%.2e, tol=%.2e\n", diff, tol);
                }
            }
            
            /* Update instance state for next iteration */
            inst->RESvoltage = v_new;
            inst->REScurrent = i_new;
        }
    }
    
    return converged ? OK : E_NOT_CONVERGED;
}
```

### **Local Truncation Error Estimation (`restrunc.c`)**

The truncation function estimates the local truncation error for adaptive time step control in transient analysis.

```c
/* restrunc.c - Local Truncation Error Estimation */
int REStrunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep)
{
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *inst;
    double maxError = 0.0;
    
    for (; model != NULL; model = model->RESnextModel) {
        for (inst = model->RESinstances; inst != NULL; 
             inst = inst->RESnextInstance) {
            
            /* For resistors, LTE is based on current change */
            double i1 = inst->REScurrent;          /* Current at t */
            double i2 = ckt->CKTstate0[inst->GENstate]; /* Current at t-Δt */
            double di_dt = (i1 - i2) / ckt->CKTdeltaOld[0];
            
            /* Estimate second derivative using three points */
            double i3 = ckt->CKTstate1[inst->GENstate]; /* Current at t-2Δt */
            double d2i_dt2 = (i1 - 2*i2 + i3) / 
                           (ckt->CKTdeltaOld[0] * ckt->CKTdeltaOld[1]);
            
            /* LTE formula for trapezoidal integration: LTE ≈ (Δt²/12) * d²i/dt² */
            double lte = fabs(ckt->CKTdelta * ckt->CKTdelta * d2i_dt2 / 12.0);
            
            /* Scale by tolerance */
            double tol = ckt->CKTcurTol + ckt->CKTreltol * MAX(fabs(i1), ckt->CKTcurTol);
            double error = lte / tol;
            
            if (error > maxError) {
                maxError = error;
            }
            
            /* Store current state for next iteration */
            ckt->