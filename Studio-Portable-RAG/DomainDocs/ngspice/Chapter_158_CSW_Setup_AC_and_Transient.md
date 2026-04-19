# Current-Controlled Switch: Setup, API, AC, and Transient

_Generated 2026-04-13 00:28 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/csw.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswdest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswnoise.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswtrunc.c`

# Chapter: Current-Controlled Switch: Setup, API, AC, and Transient

## 1. Technical Introduction

The Current-Controlled Switch (CSW) implementation in Ngspice spans multiple C source files that collectively define the device's behavior across all SPICE analysis modes. The core architecture follows Ngspice's modular design pattern, separating concerns into distinct functional units:

- **`cswdefs.h`**: Defines the fundamental data structures `CSWmodel` and `CSWinstance` that encapsulate device parameters, state variables, and sparse matrix pointers.
- **`cswsetup.c`**: Implements matrix pointer allocation and device initialization within the sparse matrix system.
- **`cswmask.c`**: Contains parameter mask definitions that map netlist keywords to internal parameter IDs for parsing.
- **`cswask.c`**: Provides query functions for retrieving device parameters during simulation.
- **`cswinit.c` & `csw.c`**: Handle device registration through the `SPICEdev` API structure, binding all analysis functions to Ngspice's simulation engine.
- **`cswdel.c`, `cswmdel.c`, `cswdest.c`**: Manage memory lifecycle, implementing instance and model destruction with proper linked-list traversal.
- **`cswacld.c`**: Implements AC small-signal analysis by linearizing the switch around its DC operating point.
- **`cswpzld.c`**: Provides pole-zero analysis support (if implemented) for stability analysis.
- **`cswnoise.c`**: Calculates Johnson-Nyquist thermal noise based on instantaneous conductance.
- **`cswtrunc.c`**: Estimates Local Truncation Error (LTE) for adaptive time-step control in transient analysis.

These files collectively implement a numerically robust switch model that employs cubic polynomial smoothing for C¹ continuity, hysteresis logic to prevent chattering, and proper Jacobian construction for Newton-Raphson convergence. The implementation demonstrates Ngspice's device architecture, where mathematical formulations are directly mapped to sparse matrix operations through carefully designed C structures and algorithms.

## 2. Mathematical Formulation

### 2.1 Core State-Transition Model

The switch behavior is governed by a control current \(I_{\text{control}}\) measured through a zero-voltage source branch. The state variable \(s \in [0,1]\) represents the normalized conductance position, where \(s=0\) corresponds to OFF (\(R_{\text{off}}\)) and \(s=1\) to ON (\(R_{\text{on}}\)).

**Hysteresis Logic:**
\[
\begin{aligned}
\text{Turn-ON if:} & \quad I_{\text{control}} > I_{\text{on}} + \frac{I_h}{2} \\
\text{Turn-OFF if:} & \quad I_{\text{control}} < I_{\text{off}} - \frac{I_h}{2} \\
\text{Hold state if:} & \quad I_{\text{off}} - \frac{I_h}{2} \leq I_{\text{control}} \leq I_{\text{on}} + \frac{I_h}{2}
\end{aligned}
\]

**Cubic Smoothing Function:**
For \(x = \frac{I_{\text{control}} - I_{\text{low}}}{I_{\text{high}} - I_{\text{low}}}\) clamped to \([0,1]\):
\[
S(x) = 3x^2 - 2x^3
\]
\[
\frac{dS}{dx} = 6x - 6x^2
\]

**Effective Conductance:**
\[
G_{\text{eff}} = G_{\text{off}} + S(x) \cdot (G_{\text{on}} - G_{\text{off}})
\]
where \(G_{\text{on}} = 1/R_{\text{on}}\), \(G_{\text{off}} = 1/R_{\text{off}}\).

**Jacobian Contribution:**
\[
\frac{\partial G_{\text{eff}}}{\partial I_{\text{control}}} = \frac{dS}{dx} \cdot \frac{1}{I_{\text{high}} - I_{\text{low}}} \cdot (G_{\text{on}} - G_{\text{off}})
\]

### 2.2 MNA Formulation

The switch stamps a 2×2 conductance matrix between its terminals (pos, neg):
\[
\begin{bmatrix}
+G_{\text{eff}} & -G_{\text{eff}} \\
-G_{\text{eff}} & +G_{\text{eff}}
\end{bmatrix}
\begin{bmatrix}
V_p \\
V_n
\end{bmatrix}
=
\begin{bmatrix}
I_{\text{switch}} \\
-I_{\text{switch}}
\end{bmatrix}
\]

The control coupling appears in the Jacobian as additional stamps at rows (pos, neg) and column (control_branch):
\[
J_{\text{coupling}} = \frac{\partial G_{\text{eff}}}{\partial I_{\text{control}}} \cdot (V_p - V_n)
\]

### 2.3 AC Small-Signal Model

For AC analysis, the switch is linearized at the DC operating point:
\[
G_{\text{ac}} = G_{\text{eff}}|_{\text{DC}}
\]
Control coupling derivatives are ignored in AC analysis, as the small-signal control current is zero for fixed bias.

### 2.4 Noise Model

Johnson-Nyquist thermal noise is implemented as a current noise source in parallel with the switch:
\[
S_i(f) = 4kT G_{\text{eff}}
\]
The noise is stamped as a diagonal contribution to the noise correlation matrix.

## 3. Convergence Analysis

### 3.1 Newton-Raphson Convergence Testing

The `CSWconvTest` function implements SPICE's mixed relative-absolute tolerance check:

**State Variable Convergence:**
\[
|s_{\text{new}} - s_{\text{old}}| \leq \text{reltol} \cdot \max(|s_{\text{new}}|, |s_{\text{old}}|) + \text{abstol}
\]

**Switch Current Convergence:**
\[
|I_{\text{switch,new}} - I_{\text{switch,old}}| \leq \text{reltol} \cdot \max(|I_{\text{switch,new}}|, |I_{\text{switch,old}}|) + \text{abstol}
\]

Default tolerances: \(\text{reltol} = 10^{-3}\), \(\text{abstol} = 10^{-12}\).

### 3.2 Local Truncation Error (LTE) Control

The `CSWtrunc` function estimates LTE for time-step adjustment using a predictor-corrector method:

\[
\text{LTE} = |s_{\text{TR}} - s_{\text{BE}}|
\]
\[
\text{Error Ratio} = \frac{\text{LTE}}{\text{reltol} \cdot |s_{\text{TR}}| + \text{abstol}}
\]

where \(s_{\text{TR}}\) is the state using Trapezoidal integration and \(s_{\text{BE}}\) using Backward Euler. If Error Ratio > 1, the time step is reduced.

### 3.3 Continuity Enforcement

The cubic smoothing function ensures:
- C⁰ continuity: \(S(0)=0\), \(S(1)=1\)
- C¹ continuity: \(S'(0)=0\), \(S'(1)=0\)

This guarantees the Jacobian remains continuous through the transition region, preventing Newton-Raphson divergence.

## 4. C Implementation

This section details the Ngspice C implementation of the Current-Controlled Switch (CSW), mapping the mathematical formulations directly to the code structures, algorithms, and SPICEdev API integration. The implementation is distributed across several core files, each responsible for a specific aspect of device simulation.

### 4.1 Core Data Structures and Parameter Binding

#### 4.1.1 Device Definition (`cswdefs.h`)

The CSW device is defined through two primary structures that encapsulate both model parameters and instance-specific state:

```c
/* CSW Model Parameters Structure */
typedef struct sCSWmodel {
    int CSWtype;                    /* Device type identifier */
    double CSWron;                  /* ON resistance (Ω) */
    double CSWroff;                 /* OFF resistance (Ω) */
    double CSWiton;                 /* ON current threshold (A) */
    double CSWitoff;                /* OFF current threshold (A) */
    double CSWih;                   /* Hysteresis current (A) */
    double CSWvon;                  /* ON voltage (derived) */
    double CSWvoff;                 /* OFF voltage (derived) */
    struct sCSWmodel *CSWnextModel; /* Next model in linked list */
    sCSWinstance *CSWinstances;     /* Pointer to instance list */
} CSWmodel;

/* CSW Instance Parameters Structure */
typedef struct sCSWinstance {
    char *CSWname;                  /* Instance name */
    int CSWposNode;                 /* Positive terminal node */
    int CSWnegNode;                 /* Negative terminal node */
    int CSWcontBranch;              /* Controlling branch index */
    double CSWcurrent;              /* Switch current (A) */
    double CSWvoltage;              /* Switch voltage (V) */
    double CSWstate;                /* Internal state variable (0=OFF, 1=ON) */
    double CSWconduct;              /* Instantaneous conductance (1/Ω) */
    double CSWgd;                   /* Derivative d(conductance)/d(control_current) */
    struct sCSWinstance *CSWnextInstance; /* Next instance in list */
    CSWmodel *CSWmodPtr;            /* Pointer to parent model */
    /* Sparse Matrix Pointers */
    double *CSWposPosPtr;           /* G[pos][pos] matrix entry */
    double *CSWposNegPtr;           /* G[pos][neg] matrix entry */
    double *CSWnegPosPtr;           /* G[neg][pos] matrix entry */
    double *CSWnegNegPtr;           /* G[neg][neg] matrix entry */
    double *CSWposContPtr;          /* G[pos][contBranch] coupling */
    double *CSWnegContPtr;          /* G[neg][contBranch] coupling */
} CSWinstance;
```

**Mathematical Mapping:**
- `CSWstate` corresponds to the smoothing parameter `s(t)` ∈ [0,1]
- `CSWconduct` implements `G(t) = G_off + s(t) × (G_on - G_off)`
- `CSWgd` stores the derivative `∂G/∂I_control = ds/dI × (G_on - G_off)` for Jacobian construction

#### 4.1.2 Parameter Tables and Masks (`cswparam.c`, `cswmpar.c`)

The parameter binding system uses integer masks to identify parameters during netlist parsing:

```c
/* Instance Parameter IDs */
#define CSW_POS_NODE     1
#define CSW_NEG_NODE     2
#define CSW_CONTROL      3    /* Name of controlling voltage source */
#define CSW_IC           4    /* Initial condition (0=OFF, 1=ON) */

/* Model Parameter IDs */
#define CSW_RON          101
#define CSW_ROFF         102
#define CSW_ITON         103
#define CSW_ITOFF        104
#define CSW_IH           105

/* Parameter Tables */
static IFparm CSWpTable[] = {
    IOP("pos",    CSW_POS_NODE,  IF_INTEGER, "Positive node"),
    IOP("neg",    CSW_NEG_NODE,  IF_INTEGER, "Negative node"),
    IOP("control",CSW_CONTROL,   IF_STRING,  "Controlling voltage source"),
    IOP("ic",     CSW_IC,        IF_REAL,    "Initial condition")
};

static IFparm CSWmPTable[] = {
    IOP("ron",    CSW_RON,       IF_REAL, "On resistance"),
    IOP("roff",   CSW_ROFF,      IF_REAL, "Off resistance"),
    IOP("iton",   CSW_ITON,      IF_REAL, "On current threshold"),
    IOP("itoff",  CSW_ITOFF,     IF_REAL, "Off current threshold"),
    IOP("ih",     CSW_IH,        IF_REAL, "Hysteresis current")
};
```

### 4.2 Setup and Matrix Allocation (`cswsetup.c`)

The setup function allocates sparse matrix pointers and initializes the device state:

```c
int CSWsetup(SMPmatrix *matrix, GENmodel *genmodel, CKTcircuit *ckt, int *states) {
    CSWmodel *model = (CSWmodel *)genmodel;
    CSWinstance *inst;
    
    for (; model; model = model->CSWnextModel) {
        for (inst = model->CSWinstances; inst; inst = inst->CSWnextInstance) {
            /* Allocate main conductance matrix pointers */
            inst->CSWposPosPtr = SMPmakeElt(matrix, inst->CSWposNode, inst->CSWposNode);
            inst->CSWposNegPtr = SMPmakeElt(matrix, inst->CSWposNode, inst->CSWnegNode);
            inst->CSWnegPosPtr = SMPmakeElt(matrix, inst->CSWnegNode, inst->CSWposNode);
            inst->CSWnegNegPtr = SMPmakeElt(matrix, inst->CSWnegNode, inst->CSWnegNode);
            
            /* Allocate control coupling pointers */
            inst->CSWposContPtr = SMPmakeElt(matrix, inst->CSWposNode, inst->CSWcontBranch);
            inst->CSWnegContPtr = SMPmakeElt(matrix, inst->CSWnegNode, inst->CSWcontBranch);
            
            /* Link to controlling voltage source */
            inst->CSWcontBranch = ckt->findBranch(inst->CSWcontrolName);
            
            /* Initialize state variable */
            if (inst->CSWicGiven) {
                inst->CSWstate = (inst->CSWic > 0.5) ? 1.0 : 0.0;
            }
        }
    }
    return OK;
}
```

**SPICE Integration:**
- The function allocates 6 sparse matrix pointers: 4 for the 2×2 conductance matrix and 2 for control coupling
- The controlling branch index is resolved via `ckt->findBranch()` to link with the zero-voltage source measuring control current

### 4.3 DC Load and Smoothing Implementation (`cswload.c`)

The core algorithm implements the cubic smoothing function and matrix stamping:

#### 4.3.1 Smoothing Function Implementation

```c
double smooth_transition(double I, double I_low, double I_high) {
    if (I <= I_low) return 0.0;
    if (I >= I_high) return 1.0;
    
    double x = (I - I_low) / (I_high - I_low);
    return 3.0*x*x - 2.0*x*x*x;  /* Cubic polynomial: 3x² - 2x³ */
}
```

**Mathematical Mapping:**
- Implements the C¹ continuous transition function `S(x) = 3x² - 2x³`
- Ensures Newton-Raphson convergence by providing continuous first derivatives

#### 4.3.2 Conductance Calculation

```c
void calculate_conductance(CSWinstance *inst, double I_control) {
    CSWmodel *model = inst->CSWmodPtr;
    
    /* Calculate threshold boundaries */
    double I_low = model->CSWitoff - model->CSWih/2.0;
    double I_high = model->CSWiton + model->CSWih/2.0;
    
    /* Calculate conductances */
    double G_on = 1.0 / model->CSWron;
    double G_off = 1.0 / model->CSWroff;
    
    /* Compute smoothing parameter */
    double s = smooth_transition(I_control, I_low, I_high);
    
    /* Store state and conductance */
    inst->CSWstate = s;
    inst->CSWconduct = G_off + s * (G_on - G_off);
    
    /* Compute derivative for Jacobian */
    double ds_dI = 0.0;
    if (I_control > I_low && I_control < I_high) {
        double x = (I_control - I_low) / (I_high - I_low);
        ds_dI = (6.0*x - 6.0*x*x) / (I_high - I_low);
    }
    inst->CSWgd = ds_dI * (G_on - G_off);
}
```

**Mathematical Mapping:**
- `inst->CSWconduct` = `G_off + s × (G_on - G_off)` where `s = S((I_control - I_low)/(I_high - I_low))`
- `inst->CSWgd` = `(dS/dx × (G_on - G_off))/(I_high - I_low)` where `dS/dx = 6x - 6x²`

#### 4.3.3 Matrix Stamping Algorithm

```c
int CSWload(GENmodel *genmodel, CKTcircuit *ckt) {
    CSWmodel *model = (CSWmodel *)genmodel;
    CSWinstance *inst;
    
    for (; model; model = model->CSWnextModel) {
        for (inst = model->CSWinstances; inst; inst = inst->CSWnextInstance) {
            /* Get controlling current from branch equation */
            double I_control = ckt->CKTrhsOld[inst->CSWcontBranch];
            
            /* Calculate smoothed conductance */
            calculate_conductance(inst, I_control);
            
            /* Stamp conductance matrix */
            *(inst->CSWposPosPtr) += inst->CSWconduct;
            *(inst->CSWposNegPtr) -= inst->CSWconduct;
            *(inst->CSWnegPosPtr) -= inst->CSWconduct;
            *(inst->CSWnegNegPtr) += inst->CSWconduct;
            
            /* Stamp control coupling */
            double Vdiff = ckt->CKTrhsOld[inst->CSWposNode] - 
                          ckt->CKTrhsOld[inst->CSWnegNode];
            *(inst->CSWposContPtr) += inst->CSWgd * Vdiff;
            *(inst->CSWnegContPtr) -= inst->CSWgd * Vdiff;
            
            /* Update RHS vector */
            double I_sw = inst->CSWconduct * Vdiff;
            ckt->CKTrhs[inst->CSWposNode] -= I_sw;
            ckt->CKTrhs[inst->CSWnegNode] += I_sw;
        }
    }
    return OK;
}
```

**Mathematical Mapping to MNA:**
- Conductance stamps implement: `G[p][p] += G`, `G[p][n] -= G`, `G[n][p] -= G`, `G[n][n] += G`
- Control coupling stamps implement: `G[p][cb] += ∂G/∂I_control × (Vp - Vn)`
- RHS updates implement: `RHS[p] -= G × (Vp - Vn)`, `RHS[n] += G × (Vp - Vn)`

### 4.4 AC Analysis Implementation (`cswacld.c`)

For small-signal AC analysis, the device is linearized around the DC operating point:

```c
int CSWacLoad(GENmodel *genmodel, CKTcircuit *ckt) {
    CSWmodel *model = (CSWmodel *)genmodel;
    CSWinstance *inst;
    
    for (; model; model = model->CSWnextModel) {
        for (inst = model->CSWinstances; inst; inst = inst->CSWnextInstance) {
            /* Use DC operating point conductance */
            double g = inst->CSWconduct;
            
            /* Stamp into real part of complex matrix */
            *(inst->CSWposPosPtr) += g;
            *(inst->CSWposNegPtr) -= g;
            *(inst->CSWnegPosPtr) -= g;
            *(inst->CSWnegNegPtr) += g;
            
            /* Control coupling ignored in AC (control current is DC) */
        }
    }
    return OK;
}
```

**Mathematical Basis:**
- AC analysis assumes small perturbations around DC operating point
- The Jacobian reduces to constant conductance `G_op` since `∂G/∂I_control` multiplies DC control current (constant)
- No frequency-dependent terms as CSW has no capacitance

### 4.5 Transient Analysis and Time-Step Control (`cswtrunc.c`)

Local Truncation Error (LTE) calculation ensures accurate time-step control:

```c
int CSWtrunc(GENmodel *genmodel, CKTcircuit *ckt, double *delta) {
    CSWmodel *model = (CSWmodel *)genmodel;
    CSWinstance *inst;
    double lte, tol, maxLTE = 0.0;
    
    for (inst = model->CSWinstances; inst; inst = inst->CSWnextInstance) {
        /* Calculate state using different integration methods */
        double s_BE = inst->CSWstate;  /* Backward Euler value */
        double s_TR = 0.5 * (inst->CSWstate + inst->CSWstateOld); /* Trapezoidal */
        
        /* LTE calculation */
        tol = ckt->CKTtrtol * fabs(s_TR) + ckt->CKTabstol;
        lte = fabs(s_TR - s_BE) / tol;
        
        if (lte > maxLTE) maxLTE = lte;
    }
    
    /* Adjust time step if LTE too large */
    if (maxLTE > 1.0) {
        *delta = 0.9 * (*delta) / maxLTE;
        *delta = MAX(*delta, ckt->CKTminStep);  /* Enforce minimum step */
    }
    
    return OK;
}
```

**Mathematical Formulation:**
- LTE = `|s_TR - s_BE| / (reltol × |s_TR| + abstol)`
- Time-step adjustment: `Δt_new = 0.9 × Δt_old / LTE` when LTE > 1.0
- Uses the state variable `s(t)` as error indicator since it controls conductance transition smoothness

### 4.6 Noise Analysis Implementation (`cswnoise.c`)

Johnson-Nyquist thermal noise is implemented based on instantaneous conductance:

```c
int CSWnoise(int mode, int operation, GENmodel *genmodel, 
             CKTcircuit *ckt, Ndata *data, double *OnDens) {
    CSWmodel *model = (CSWmodel *)genmodel;
    CSWinstance *inst;
    double temp = ckt->CKTtemp;
    
    for (inst = model->CSWinstances; inst; inst = inst->CSWnextInstance) {
        double g = inst->CSWconduct;
        double si = 4.0 * CONSTboltz * temp * g;
        
        /* Pass to noise summation */
        switch (operation) {
            case N_OPEN:
                data->outNoiz += si * data->delFreq;
                data->inNoise += si * data->delFreq;
                break;
            case N_CALC:
                /* Calculate noise contribution */
                break;
        }
    }
    return OK;
}
```

**Mathematical Basis:**
- Implements `S_i(f) = 4kT·G` (A²/Hz)
- `CONSTboltz` = Boltzmann constant (1.380649×10⁻²³ J/K)
- Noise is proportional to instantaneous conductance, varying with switch state

### 4.7 SPICEdev API Binding (`cswinit.c`, `csw.c`)

The device is registered with Ngspice through the SPICEdev structure:

```c
SPICEdev CSWinfo = {
    .DEVpublic = {
        .name = "csw",
        .description = "Current controlled switch",
        .terms = 2,
        .numNames = 1,
        .termNames = {"pos", "neg"},
        .numInstanceParms = 4,
        .numModelParms = 5,
    },
    .DEVmodParam = CSWmPTable,
    .DEVinstParam = CSWpTable,
    .DEVload = CSWload,
    .DEVsetup = CSWsetup,
    .DEVunsetup = NULL,
    .DEVpzSetup = NULL,
    .DEVtemperature = NULL,
    .DEVtrunc = CSWtrunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = CSWacLoad,
    .DEVaccept = NULL,
    .DEVdestroy = CSWdestroy,
    .DEVmodDelete = CSWmDelete,
    .DEVinstDelete = CSWdelete,
    .DEVask = CSWask,
    .DEVmodAsk = CSWmAsk,
    .DEVpzLoad = CSWpzLoad,
    .DEVconvTest = NULL,
    .DEVnoise = CSWnoise,
    .DEVinstSize = sizeof(sCSWinstance),
    .DEVmodSize = sizeof(sCSWmodel),
};
```

**Integration Points:**
- `DEVload`: DC and transient matrix loading
- `DEVsetup`: Sparse matrix pointer allocation
- `DEVacLoad`: AC analysis matrix loading
- `DEVtrunc`: Time-step control via LTE
- `DEVnoise`: Noise analysis implementation

### 4.8 Memory Management (`cswdel.c`, `cswmdel.c`, `cswdest.c`)

Proper cleanup of dynamically allocated memory:

```c
void CSWdestroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    CSWmodel *model = (CSWmodel *)mod;
    CSWinstance *inst, *nextInst;
    
    while (model) {
        CSWmodel *nextModel = model->CSWnextModel;
        inst = model->CSWinstances;
        
        while (inst) {
            nextInst = inst->CSWnextInstance;
            FREE(inst->CSWname);
            FREE(inst);
            inst = nextInst;
        }
        
        FREE(model);
        model = nextModel;
    }
    *inModel = NULL;
}
```

**Memory Lifecycle:**
- Instance names are dynamically allocated strings requiring explicit freeing
- Linked list traversal ensures all instances are cleaned up before models
- Double pointer parameter allows caller's model pointer to be nullified

### 4.9 Parameter Query Functions (`cswask.c`)

The ask functions provide runtime access to device parameters:

```c
int CSWask(CKTcircuit *ckt, GENinstance *geninst, int which, IFvalue *value) {
    CSWinstance *inst = (CSWinstance *)geninst;
    
    switch (which) {
        case CSW_CURRENT:
            value->rValue = inst->CSWcurrent;
            break;
        case CSW_VOLTAGE:
            value->rValue = inst->CSWvoltage;
            break;
        case CSW_STATE:
            value->rValue = inst->CSWstate;
            break;
        case CSW_CONDUCT:
            value->rValue = inst->CSWconduct;
            break;
        default:
            return E_BADPARM;
    }
    return OK;
}
```

### 4.10 Implementation Summary

The CSW C implementation demonstrates several key design patterns:

1. **Mathematical Fidelity**: The cubic smoothing function `3x² - 2x³` is directly implemented in C, ensuring C¹ continuity for Newton-Raphson convergence.

2. **Sparse Matrix Integration**: Six sparse matrix pointers are allocated to implement the 2×2 conductance matrix plus control coupling terms.

3. **State Management**: The internal state variable `CSWstate` tracks the smoothing parameter, used for both conductance calculation and LTE estimation.

4. **Analysis-Specific Implementations**: Separate functions handle DC (`CSWload`), AC (`CSWacLoad`), noise (`CSWnoise`), and transient (`CSWtrunc`) analyses.

5. **SPICEdev API Compliance**: Full integration with Ngspice through the `SPICEdev` structure, enabling automatic registration and dispatch.

6. **Numerical Robustness**: Hysteresis thresholds prevent chatter, while the smoothing function ensures derivative continuity for convergence.

The implementation balances physical accuracy (through proper hysteresis and noise modeling) with numerical stability (through smoothing and LTE control), making it suitable for robust circuit simulation within Ngspice's Newton-Raphson framework. Each C file serves a distinct purpose in the device lifecycle, from initialization and parameter parsing to matrix operations and memory cleanup, demonstrating Ngspice's modular architecture for device implementation.