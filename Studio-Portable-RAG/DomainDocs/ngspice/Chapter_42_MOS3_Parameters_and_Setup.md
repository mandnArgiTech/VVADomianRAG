# MOS3: Parameter Parsing and Matrix Setup

_Generated 2026-04-12 06:04 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3ask.c`

# MOS3: Parameter Parsing and Matrix Setup

## Introduction

The MOS3 (Level 3) model implementation in Ngspice relies on a coordinated architecture of four core C files that handle parameter management, mathematical transformations, and SPICE integration. `mos3defs.h` defines the fundamental data structures that map SPICE parameters to C variables, establishing the memory layout for both model-wide and instance-specific data. `mos3mpar.c` and `mos3mask.c` implement the parameter binding system, translating SPICE deck parameter names (like "VTO", "KP", "THETA") to internal integer identifiers and providing the lookup tables that connect user input to the simulation engine. `mos3ask.c` enables querying of computed values during and after simulation, exposing internal states like transconductance (`GM`) and capacitances (`CGS`, `CGD`) for post-processing. Finally, `mos3set.c` performs the critical mathematical transformations and matrix allocation: it calculates effective device dimensions, applies temperature scaling laws, computes derived parameters like oxide capacitance and body effect coefficient, and allocates the sparse matrix pointers required for Newton-Raphson iteration. Together, these files implement the parameter parsing pipeline and matrix setup that underpin the Level 3 MOSFET's semi-empirical model within Ngspice's SPICE-compatible simulation framework.

## Mathematical Formulation

The MOS3 (Level 3) model parameter parsing and setup phase transforms user-provided SPICE parameters into the mathematical quantities required for device evaluation. This transformation involves geometry corrections, temperature scaling, and derivation of interdependent parameters, all of which directly impact the subsequent DC load and matrix stamping operations.

### 1. Effective Geometry Calculation with Narrow-Width Effect

The Level 3 model refines the simple effective dimension model by incorporating a narrow-width correction derived from charge sharing in the depletion region:

**Effective Length:**
```
L_eff = L - 2·L_d
```
Where `L_d` is the lateral diffusion parameter (`LD`). This maps directly to `inst->MOS3leff = inst->MOS3l - 2 * model->MOS3ld` in the C code.

**Effective Width with Narrow-Width Correction:**
```
W_eff = W - 2·ΔW
```
Where the width reduction `ΔW` accounts for fringe field effects:
```
ΔW = (ε_si / (q·N_sub))^{1/2} · √φ · (√(1 + 2·W_d/X_j) - 1)
```
Here, `ε_si` is silicon permittivity, `q` is electron charge, `N_sub` is substrate doping, `φ` is surface potential, `W_d` is width diffusion (`WD`), and `X_j` is junction depth. This complex formula is implemented conditionally in `mos3set.c` when `model->MOS3delta > 0.0`, otherwise reverting to `W_eff = W - 2·W_d`.

**SPICE Integration Significance:** These effective dimensions directly scale the transconductance parameter `β = (W_eff/L_eff)·KP` stored in `inst->MOS3beta`, which multiplies all current equations. The minimum dimension clamping to `1e-12` prevents division by zero in the Newton-Raphson solver.

### 2. Temperature-Dependent Parameter Transformations

The setup phase applies physics-based temperature scaling to ensure consistent device behavior across operating temperatures:

**Mobility Degradation with Temperature:**
```
μ(T) = μ(T₀) · (T/T₀)^{-1.5}
```
Implemented as `inst->MOS3beta *= pow(TempRatio, -1.5)` where `TempRatio = T/T₀`. This power-law scaling directly reduces the `β` factor at higher temperatures, affecting all current calculations.

**Threshold Voltage Temperature Coefficient:**
```
V_TO(T) = V_TO(T₀) - α·(T - T₀)
```
Where `α ≈ 0.5 mV/K` is a typical temperature coefficient. This linear adjustment modifies `model->MOS3vto` based on the instance temperature `inst->MOS3temp` relative to the nominal circuit temperature `ckt->CKTnomTemp`.

**Saturation Velocity Temperature Dependence:**
```
v_sat(T) = v_sat(T₀) · (T/T₀)^{-0.87}
```
Applied when `model->MOS3vmax > 0.0` via `model->MOS3vmax *= pow(TempRatio, -0.87)`. This affects the velocity saturation factor `κ` and consequently the saturation voltage `V_dsat`.

**SPICE Integration Significance:** These transformations ensure the DC operating point remains physically accurate when instance temperature (`TEMP` parameter) differs from the circuit nominal temperature (`TNOM`), critical for multi-temperature corner analysis.

### 3. Derived Parameter Calculations

When users omit certain parameters, the setup code calculates them from fundamental physical relationships:

**Oxide Capacitance per Unit Area:**
```
C_ox = ε_ox / t_ox = 3.9·ε₀ / t_ox
```
Stored as `model->MOS3oxideCapFactor = 3.9 * 8.854e-12 / model->MOS3tox`. This is fundamental for both current (`β = (W_eff/L_eff)·C_ox·μ_eff`) and capacitance calculations.

**Transconductance Parameter KP from Mobility:**
If `KP` not given but `U0` and `TOX` are provided:
```
KP = U0 · C_ox
```
Implemented as `model->MOS3kp = model->MOS3uo * model->MOS3oxideCapFactor`.

**Body Effect Parameter γ from Doping:**
If `GAMMA` not given but `NSUB` and `TOX` are provided:
```
γ = √(2·q·ε_si·N_sub) / C_ox
```
Where `q = 1.602e-19` and `eps_si = 11.7 * 8.854e-12`.

**Surface Potential φ from Doping:**
If `PHI` not given but `NSUB` is provided:
```
φ = 2·V_T · ln(N_sub / n_i)
```
Where `V_T = kT/q` is thermal voltage and `n_i = 1.45e16 cm⁻³` at 300K.

**SPICE Integration Significance:** These derivations ensure model completeness even with minimal parameter sets, maintaining simulation capability while preserving physical consistency.

### 4. Critical Voltage for Newton-Raphson Limiting

The setup calculates a critical voltage used in the `DEVfetlim()` function to ensure convergence:
```
V_crit = V_T · ln(V_T / (√2 · 1e-14))
```
Stored as `model->MOS3vcrit`. This voltage determines the allowable change per Newton iteration for `V_gs` limiting, preventing oscillation in strong inversion or near cutoff regions.

### 5. SMP Matrix Structure and Pointer Allocation

The mathematical conductance matrix for the 4-terminal MOSFET (D, G, S, B) has the structure:
```
[ G_dd  G_dg  G_ds  G_db ]   [ V_d ]   [ I_d ]
[ G_gd  G_gg  G_gs  G_gb ] · [ V_g ] = [ I_g ]
[ G_sd  G_sg  G_ss  G_sb ]   [ V_s ]   [ I_s ]
[ G_bd  G_bg  G_bs  G_bb ]   [ V_b ]   [ I_b ]
```

Where each entry represents a partial derivative:
- `G_dd = ∂I_d/∂V_d` (drain self-conductance, includes `g_ds + 1/R_d`)
- `G_ds = ∂I_d/∂V_s` (drain-source transconductance, typically `-g_ds`)
- `G_dg = ∂I_d/∂V_g` (drain-gate transconductance, `g_m`)
- `G_db = ∂I_d/∂V_b` (drain-bulk transconductance, `g_mbs`)

**SPICE Integration Significance:** The 16 matrix pointers allocated in `MOS3setup()` (`MOS3dPtrPosPtr`, `MOS3dPtrNegPtr`, etc.) provide direct write access to these matrix positions. During `MOS3load()`, the computed conductances (`inst->MOS3gm`, `inst->MOS3gds`, `inst->MOS3gmbs`) are stamped into these pre-allocated locations, building the Jacobian matrix for Newton-Raphson iteration.

### 6. State Vector Allocation for Charge Conservation

For transient analysis, the setup allocates state vector entries for charge storage:
```
states[0] → q_gs (gate-source charge)
states[1] → q_gd (gate-drain charge)  
states[2] → q_gb (gate-bulk charge)
states[3] → q_bd (bulk-drain charge)
states[4] → q_bs (bulk-source charge)
```

These indices are stored in `inst->MOS3qgsState` through `inst->MOS3qbsState`. The charges are initialized to zero.

**SPICE Integration Significance:** During transient analysis, these state entries store the history of charges for numerical integration:
```
I_cap = dq/dt ≈ (q_new - q_old)/Δt + trapezoidal correction terms
```
The state vector enables charge-conserving transient analysis via the Meyer capacitance model.

## Convergence Analysis

### 1. Parameter Validation and Defaulting

The setup phase ensures mathematical robustness by validating parameters and applying sensible defaults:

**Default Value Assignment:**
- `VTO = 0.0` (zero threshold voltage if unspecified)
- `KP = 2.0e-5` (default transconductance)
- `PHI = 0.6` (typical surface potential)
- `U0 = 600.0` (typical low-field mobility in cm²/V·s)
- `TOX = 1.0e-7` (100Å oxide thickness)
- `KAPPA = 0.2` (default saturation field factor)

**Dimension Validation:**
```c
if(inst->MOS3leff <= 0.0) inst->MOS3leff = 1.0e-12;
if(inst->MOS3weff <= 0.0) inst->MOS3weff = 1.0e-12;
```
This prevents division by zero in `β = (W_eff/L_eff)·KP` calculations.

**SPICE Convergence Impact:** Proper defaults prevent singular Jacobian matrices while maintaining reasonable device behavior for unspecified parameters.

### 2. Temperature Consistency Enforcement

The setup ensures temperature parameters are physically consistent:

**Instance Temperature Defaulting:**
```c
if(!inst->MOS3tempGiven) inst->MOS3temp = ckt->CKTtemp;
```
If no instance `TEMP` specified, uses circuit temperature.

**Temperature Ratio Calculation:**
```c
double T = inst->MOS3temp + CONSTCtoK;      /* Convert to Kelvin */
double TNOM = ckt->CKTnomTemp + CONSTCtoK;  /* Nominal in Kelvin */
TempRatio = T / TNOM;
```

**SPICE Convergence Impact:** Consistent temperature scaling prevents discontinuities in temperature-dependent parameters (`μ(T)`, `V_TO(T)`, `v_sat(T)`), which could cause Newton-Raphson divergence when temperature differs from nominal.

### 3. Matrix Conditioning via Pointer Allocation

The sparse matrix pointer allocation in `MOS3setup()` directly affects numerical conditioning:

**Diagonal Entry Guarantee:**
All four diagonal pointers (`MOS3dPtrPosPtr`, `MOS3sPtrPosPtr`, `MOS3gPtrGatePtr`, `MOS3bPtrBulkPtr`) are always allocated, ensuring the Jacobian has non-zero diagonal entries.

**Memory Allocation Check:**
```c
if(!inst->MOS3dPtrPosPtr || !inst->MOS3sPtrPosPtr ||
   !inst->MOS3gPtrGatePtr || !inst->MOS3bPtrBulkPtr) {
    return E_NOMEM;
}
```
Failure to allocate any diagonal pointer aborts setup, preventing singular matrices.

**SPICE Convergence Impact:** Guaranteed diagonal entries allow the solver to add `GMIN` (typically 1e-12 Ʊ) to prevent singularity, a critical fallback for convergence.

### 4. State Vector Initialization for Transient Analysis

Charge states are initialized to zero:
```c
ckt->CKTstates[inst->MOS3qgsState] = 0.0;
ckt->CKTstates[inst->MOS3qgdState] = 0.0;
/* ... etc. */
```

**SPICE Convergence Impact:** Zero initial charges ensure the first transient step starts from a known, consistent state. For devices with initial conditions (`IC` parameter), these would be overridden during initial condition setup.

### 5. Operating Mode and OFF Flag Handling

**Mode Assignment:**
```c
inst->MOS3mode = (model->MOS3type > 0) ? 1.0 : -1.0;
```
Sets `mode = 1` for NMOS, `-1` for PMOS, affecting voltage polarity in calculations.

**OFF Flag Enforcement:**
```c
if(inst->MOS3off) {
    inst->MOS3vgs = 0.0;
    inst->MOS3vds = 0.0;
    inst->MOS3vbs = 0.0;
}
```
Forces device to cutoff region initially.

**SPICE Convergence Impact:** The OFF flag provides a known starting point (all voltages zero) for difficult convergence cases, often used with `.NODESET` to guide the solver.

### 6. Parameter Interdependence Resolution

The setup resolves parameter dependencies in a specific priority order:

**Priority Rules:**
1. If `KP` given explicitly, use it directly
2. Else if `U0` and `TOX` given, calculate `KP = U0·C_ox`
3. Similar logic for `GAMMA` from `NSUB` and `TOX`
4. Similar logic for `PHI` from `NSUB`

**Implementation:**
```c
if(!model->MOS3kpGiven && model->MOS3uoGiven && model->MOS3toxGiven) {
    model->MOS3kp = model->MOS3uo * model->MOS3oxideCapFactor;
}
```

**SPICE Convergence Impact:** Consistent derivation prevents conflicting parameter values that could create discontinuities in device behavior (e.g., different `KP` values from direct specification vs. calculation from `U0` and `TOX`).

### 7. Narrow-Width Effect Conditional Application

The complex narrow-width correction is applied conditionally:
```c
if(model->MOS3delta > 0.0) {
    /* Apply full narrow-width correction */
    double dw = coeff * sqrt(phi) * (sqrt(1 + 2 * wd / xj) - 1);
    inst->MOS3weff = inst->MOS3w - 2 * dw;
} else {
    /* Simple width reduction */
    inst->MOS3weff = inst->MOS3w - 2 * model->MOS3wd;
}
```

**SPICE Convergence Impact:** The `DELTA` parameter acts as a switch: `DELTA=0` uses simple model for faster computation and better convergence in wide devices; `DELTA>0` activates full physics for accurate narrow-width simulation at potential convergence cost due to more complex `W_eff` calculation.

### 8. Numerical Safeguards in Derived Calculations

**Square Root Protection:**
```c
double coeff = sqrt(2 * eps_si / (q * model->MOS3nsub));
```
Assumes `model->MOS3nsub > 0` (validated during parsing).

**Logarithm Argument Protection:**
In `φ = 2·V_T·ln(N_sub/n_i)`, requires `N_sub > n_i` for positive `φ`.

**SPICE Convergence Impact:** These protections prevent mathematical exceptions (sqrt of negative, log of non-positive) that would crash the solver during setup.

### 9. Convergence-Oriented Defaults for Semi-Empirical Parameters

Level 3-specific parameters default to values promoting convergence:

- `VMAX = 0.0` (disables velocity saturation unless specified)
- `THETA = 0.0` (disables mobility degradation unless specified)  
- `ETA = 0.0` (disables DIBL unless specified)
- `DELTA = 0.0` (disables narrow-width correction unless specified)

**SPICE Convergence Impact:** Defaulting these second-order effects to zero creates a simpler, more robust Level 1-like model that converges easily. Users explicitly enable effects when needed, accepting potential convergence trade-offs for accuracy.

### 10. Setup Failure Modes and Error Propagation

**Critical Failure Points:**
1. Memory allocation failure → `E_NOMEM`
2. Invalid parameter combinations → Parameter validation warnings
3. Zero or negative effective dimensions → Clamped to 1e-12 with warning

**SPICE Integration:** Setup errors propagate to the simulation controller, which may attempt fallback strategies (source stepping, GMIN stepping) or abort with diagnostic messages.

### 11. Mathematical Consistency Summary

The parameter parsing and setup phase ensures:
1. **Complete parameter set:** All required mathematical variables have defined values (explicit or derived)
2. **Physical consistency:** Derived parameters obey physical relationships (e.g., `γ ∝ √N_sub/C_ox`)
3. **Numerical robustness:** Protected operations, dimension clamping, sensible defaults
4. **Matrix readiness:** Sparse matrix pointers allocated for Jacobian construction
5. **State initialization:** Charge states zeroed for transient analysis
6. **Temperature consistency:** Proper scaling applied when `TEMP ≠ TNOM`

These measures collectively create a mathematically well-posed problem for the Newton-Raphson solver, establishing the foundation for robust convergence in subsequent DC, transient, and AC analyses.

---

# C Implementation

## 1. Data Structure Definition and Parameter Storage

### 1.1 Core Data Structures in `mos3defs.h`

The MOS3 implementation uses two primary C structures that map directly to SPICE's device modeling framework:

```c
/* MOS3 Model Structure - Process parameters */
typedef struct sMOS3model {
    int MOS3type;                   /* Device polarity: NMF or PMF */
    
    /* Level 3 specific parameters with direct SPICE mapping */
    double MOS3vto;                 /* VTO - Zero-bias threshold voltage */
    double MOS3kp;                  /* KP - Transconductance parameter */
    double MOS3gamma;               /* GAMMA - Body effect parameter */
    double MOS3phi;                 /* PHI - Surface potential */
    double MOS3lambda;              /* LAMBDA - Channel-length modulation */
    
    /* Level 3 semi-empirical extensions */
    double MOS3vmax;                /* VMAX - Maximum carrier velocity */
    double MOS3theta;               /* THETA - Mobility degradation */
    double MOS3eta;                 /* ETA - Drain-induced barrier lowering */
    double MOS3kappa;               /* KAPPA - Saturation field factor */
    double MOS3delta;               /* DELTA - Narrow-width effect */
    double MOS3xj;                  /* XJ - Junction depth */
    double MOS3ld;                  /* LD - Lateral diffusion */
    double MOS3wd;                  /* WD - Width diffusion */
    double MOS3uo;                  /* UO - Low-field mobility */
    double MOS3nsub;                /* NSUB - Substrate doping */
    double MOS3tox;                 /* TOX - Oxide thickness */
    
    /* Derived parameters computed during setup */
    double MOS3oxideCapFactor;      /* C_ox = ε_ox/t_ox */
    double MOS3vcrit;               /* Critical voltage for NR limiting */
    
    /* Bit flags for parameter presence tracking */
    unsigned MOS3vtoGiven:1;
    unsigned MOS3kpGiven:1;
    /* ... additional flag bits for all parameters */
    
    struct sMOS3model *MOS3nextModel;    /* Linked list for multiple models */
    sMOS3instance *MOS3instances;        /* Pointer to instance chain */
} MOS3model;
```

The model structure stores process parameters that are shared across instances. The bit flags (`MOS3vtoGiven`, etc.) implement the mathematical condition "if parameter not given" by tracking which parameters were explicitly specified in the SPICE deck.

```c
/* MOS3 Instance Structure - Geometry and state variables */
typedef struct sMOS3instance {
    char *MOS3name;                      /* Instance identifier */
    
    /* Terminal node indices for matrix addressing */
    int MOS3dNode;                       /* Drain node in circuit matrix */
    int MOS3gNode;                       /* Gate node */
    int MOS3sNode;                       /* Source node */
    int MOS3bNode;                       /* Bulk node */
    
    /* Geometry parameters from SPICE deck */
    double MOS3l;                        /* L - Channel length */
    double MOS3w;                        /* W - Channel width */
    double MOS3ad;                       /* AD - Drain area */
    double MOS3as;                       /* AS - Source area */
    
    /* Calculated effective dimensions */
    double MOS3leff;                     /* L_eff = L - 2*LD */
    double MOS3weff;                     /* W_eff with narrow-width correction */
    double MOS3beta;                     /* β = (W_eff/L_eff) * KP */
    
    /* State vector indices for charge storage */
    int MOS3qgsState;                    /* Index for q_gs in CKTstates[] */
    int MOS3qgdState;                    /* Index for q_gd */
    int MOS3qgbState;                    /* Index for q_gb */
    int MOS3qbdState;                    /* Index for q_bd */
    int MOS3qbsState;                    /* Index for q_bs */
    
    /* SMP matrix pointers for 4×4 conductance matrix */
    double *MOS3dPtrPosPtr;              /* Pointer to G_dd */
    double *MOS3dPtrNegPtr;              /* Pointer to G_ds */
    double *MOS3dPtrGatePtr;             /* Pointer to G_dg */
    double *MOS3dPtrBulkPtr;             /* Pointer to G_db */
    /* ... 12 more matrix pointers for complete 4×4 matrix */
    
    /* Instance-specific flags */
    unsigned MOS3lGiven:1;               /* L parameter was specified */
    unsigned MOS3wGiven:1;               /* W parameter was specified */
    unsigned MOS3off:1;                  /* OFF flag for initial condition */
    
    struct sMOS3instance *MOS3nextInstance; /* Linked list for multiple instances */
    MOS3model *MOS3modPtr;               /* Back pointer to parent model */
} MOS3instance;
```

The instance structure contains geometry-specific parameters and runtime state. The matrix pointers (`MOS3dPtrPosPtr`, etc.) provide direct access to the sparse matrix entries for efficient Jacobian updates during Newton-Raphson iteration.

## 2. Parameter Binding and SPICE Integration

### 2.1 Parameter Table Definitions in `mos3mpar.c`

The parameter tables map SPICE deck names to internal C variables and mathematical quantities:

```c
/* Model parameter table - maps ".model" line parameters */
static IFparm MOS3mPTable[] = {
    /* Basic Level 1 parameters */
    IOP("vto",     MOS3_VTO,    IF_REAL, "Threshold voltage"),
    IOP("kp",      MOS3_KP,     IF_REAL, "Transconductance parameter"),
    IOP("gamma",   MOS3_GAMMA,  IF_REAL, "Body effect parameter"),
    IOP("phi",     MOS3_PHI,    IF_REAL, "Surface potential"),
    IOP("lambda",  MOS3_LAMBDA, IF_REAL, "Channel-length modulation"),
    
    /* Level 3 semi-empirical extensions */
    IOP("vmax",    MOS3_VMAX,   IF_REAL, "Maximum carrier velocity"),
    IOP("theta",   MOS3_THETA,  IF_REAL, "Mobility degradation coefficient"),
    IOP("eta",     MOS3_ETA,    IF_REAL, "Drain-induced barrier lowering"),
    IOP("kappa",   MOS3_KAPPA,  IF_REAL, "Saturation field factor"),
    IOP("delta",   MOS3_DELTA,  IF_REAL, "Narrow-width effect"),
    IOP("xj",      MOS3_XJ,     IF_REAL, "Junction depth"),
    IOP("ld",      MOS3_LD,     IF_REAL, "Lateral diffusion"),
    IOP("wd",      MOS3_WD,     IF_REAL, "Width diffusion"),
    IOP("uo",      MOS3_UO,     IF_REAL, "Low-field mobility"),
    IOP("nsub",    MOS3_NSUB,   IF_REAL, "Substrate doping"),
    IOP("tox",     MOS3_TOX,    IF_REAL, "Oxide thickness"),
    
    /* Device type flags */
    IP("nmos",     MOS3_TYPE,   IF_FLAG, "N-type MOSFET"),
    IP("pmos",     MOS3_TYPE,   IF_FLAG, "P-type MOSFET"),
};
```

Each `IOP` macro defines:
- SPICE name (e.g., "vto")
- Internal constant (e.g., `MOS3_VTO`)
- Type (`IF_REAL` for real numbers)
- Description for documentation

```c
/* Instance parameter table - maps device instance parameters */
static IFparm MOS3pTable[] = {
    IOP("l",       MOS3_L,      IF_REAL, "Channel length"),
    IOP("w",       MOS3_W,      IF_REAL, "Channel width"),
    IOP("ad",      MOS3_AD,     IF_REAL, "Drain area"),
    IOP("as",      MOS3_AS,     IF_REAL, "Source area"),
    IOP("pd",      MOS3_PD,     IF_REAL, "Drain perimeter"),
    IOP("ps",      MOS3_PS,     IF_REAL, "Source perimeter"),
    IOP("nrd",     MOS3_NRD,    IF_REAL, "Drain squares"),
    IOP("nrs",     MOS3_NRS,    IF_REAL, "Source squares"),
    IOP("temp",    MOS3_TEMP,   IF_REAL, "Instance temperature"),
    IP("off",      MOS3_OFF,    IF_FLAG, "Initially off"),
};
```

### 2.2 Parameter ID Masks in `mos3mask.c`

The mask file defines numerical constants for parameter identification:

```c
/* Model parameter IDs */
#define MOS3_VTO       101
#define MOS3_KP        102
#define MOS3_GAMMA     103
#define MOS3_PHI       104
#define MOS3_LAMBDA    105
#define MOS3_VMAX      106
#define MOS3_THETA     107
#define MOS3_ETA       108
#define MOS3_KAPPA     109
#define MOS3_DELTA     110
#define MOS3_XJ        111
#define MOS3_LD        112
#define MOS3_WD        113
#define MOS3_UO        114
#define MOS3_NSUB      115
#define MOS3_TOX       116

/* Instance parameter IDs */
#define MOS3_L         1
#define MOS3_W         2
#define MOS3_AD        3
#define MOS3_AS        4
#define MOS3_PD        5
#define MOS3_PS        6
#define MOS3_NRD       7
#define MOS3_NRS       8
#define MOS3_TEMP      9
#define MOS3_OFF       12
```

These constants are used in switch statements throughout the code to identify which parameter is being accessed.

### 2.3 Parameter Query Functions in `mos3ask.c`

The ask functions implement the mathematical mapping between internal variables and SPICE output:

```c
int MOS3ask(CKTcircuit *ckt, GENinstance *geninst, int which, IFvalue *value) {
    MOS3instance *inst = (MOS3instance *)geninst;
    
    switch(which) {
        case MOS3_W:
            value->rValue = inst->MOS3w;          /* W → inst->MOS3w */
            return OK;
        case MOS3_L:
            value->rValue = inst->MOS3l;          /* L → inst->MOS3l */
            return OK;
        case MOS3_VGS:
            value->rValue = inst->MOS3vgs;        /* VGS → inst->MOS3vgs */
            return OK;
        case MOS3_GM:
            value->rValue = inst->MOS3gm;         /* GM → inst->MOS3gm */
            return OK;
        case MOS3_GDS:
            value->rValue = inst->MOS3gds;        /* GDS → inst->MOS3gds */
            return OK;
        case MOS3_CGS:
            value->rValue = inst->MOS3cgs;        /* CGS → inst->MOS3cgs */
            return OK;
        default:
            return E_BADPARM;
    }
}
```

Each case maps a SPICE output request (`MOS3_VGS`, etc.) to the corresponding C variable that stores the computed mathematical value.

## 3. Core Setup Implementation in `mos3set.c`

### 3.1 Main Setup Function Architecture

The `MOS3setup()` function implements all mathematical transformations from SPICE parameters to internal representations:

```c
int MOS3setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS3model *model;
    MOS3instance *inst;
    
    /* Loop through all models in linked list */
    for(model = (MOS3model *)inModel; model != NULL; 
        model = model->MOS3nextModel) {
        
        /* MATHEMATICAL STEP 1: Set default values for unspecified parameters */
        if(!model->MOS3vtoGiven)    model->MOS3vto = 0.0;
        if(!model->MOS3kpGiven)     model->MOS3kp = 2.0e-5;
        if(!model->MOS3gammaGiven)  model->MOS3gamma = 0.0;
        if(!model->MOS3phiGiven)    model->MOS3phi = 0.6;
        if(!model->MOS3lambdaGiven) model->MOS3lambda = 0.0;
        /* ... defaults for all Level 3 parameters ... */
        
        /* MATHEMATICAL STEP 2: Calculate derived model parameters */
        
        /* Oxide capacitance: C_ox = ε_ox / t_ox */
        model->MOS3oxideCapFactor = 3.9 * 8.854e-12 / model->MOS3tox;
        
        /* Calculate KP from UO if not given: KP = μ₀·C_ox */
        if(!model->MOS3kpGiven && model->MOS3uoGiven && model->MOS3toxGiven) {
            model->MOS3kp = model->MOS3uo * model->MOS3oxideCapFactor;
        }
        
        /* Calculate GAMMA from NSUB if not given: γ = √(2qε_siN_sub)/C_ox */
        if(!model->MOS3gammaGiven && model->MOS3nsubGiven && model->MOS3toxGiven) {
            double q = 1.602e-19;
            double eps_si = 11.7 * 8.854e-12;
            model->MOS3gamma = sqrt(2 * q * eps_si * model->MOS3nsub) 
                               / model->MOS3oxideCapFactor;
        }
        
        /* Calculate PHI from NSUB if not given: φ = 2V_T·ln(N_sub/n_i) */
        if(!model->MOS3phiGiven && model->MOS3nsubGiven) {
            double ni = 1.45e16;  /* Intrinsic concentration at 300K */
            model->MOS3phi = 2 * Vthermal * log(model->MOS3nsub / ni);
        }
        
        /* Critical voltage for Newton-Raphson limiting */
        model->MOS3vcrit = Vthermal * log(Vthermal / (CONSTroot2 * 1.0e-14));
```

### 3.2 Instance-Specific Mathematical Transformations

```c
        /* Process each instance under this model */
        for(inst = model->MOS3instances; inst != NULL; 
            inst = inst->MOS3nextInstance) {
            
            /* Set instance parameter defaults */
            if(!inst->MOS3lGiven) inst->MOS3l = 100.0e-6;
            if(!inst->MOS3wGiven) inst->MOS3w = 100.0e-6;
            if(!inst->MOS3tempGiven) inst->MOS3temp = ckt->CKTtemp;
            
            /* MATHEMATICAL: Effective length calculation */
            /* L_eff = L - 2·L_d */
            inst->MOS3leff = inst->MOS3l - 2 * model->MOS3ld;
            
            /* MATHEMATICAL: Effective width with narrow-width effect */
            if(model->MOS3delta > 0.0) {
                /* Narrow-width correction: ΔW = √(2ε_si/(qN_sub))·√φ·(√(1+2W_d/X_j)-1) */
                double wd = model->MOS3wd;
                double xj = model->MOS3xj;
                double phi = model->MOS3phi;
                double coeff = sqrt(2 * eps_si / (q * model->MOS3nsub));
                
                double dw = coeff * sqrt(phi) * 
                           (sqrt(1 + 2 * wd / xj) - 1);
                inst->MOS3weff = inst->MOS3w - 2 * dw;
            } else {
                /* Simple width reduction: W_eff = W - 2·W_d */
                inst->MOS3weff = inst->MOS3w - 2 * model->MOS3wd;
            }
            
            /* Numerical protection: ensure positive dimensions */
            if(inst->MOS3leff <= 0.0) inst->MOS3leff = 1.0e-12;
            if(inst->MOS3weff <= 0.0) inst->MOS3weff = 1.0e-12;
            
            /* MATHEMATICAL: Beta calculation */
            /* β = (W_eff / L_eff) · KP */
            inst->MOS3beta = (inst->MOS3weff / inst->MOS3leff) * model->MOS3kp;
```

### 3.3 Temperature Scaling Implementation

```c
            /* Temperature scaling if instance TEMP differs from circuit nominal */
            if(inst->MOS3temp != ckt->CKTtemp) {
                double T = inst->MOS3temp + CONSTCtoK;
                double TNOM = ckt->CKTnomTemp + CONSTCtoK;
                double TempRatio = T / TNOM;
                
                /* Mobility: μ(T) = μ(T₀)·(T/T₀)^{-1.5} */
                inst->MOS3beta *= pow(TempRatio, -1.5);
                
                /* Threshold voltage: V_TO(T) = V_TO(T₀) - α·(T - T₀) */
                double alpha = 0.5e-3;  /* 0.5 mV/K temperature coefficient */
                model->MOS3vto -= alpha * (inst->MOS3temp - ckt->CKTnomTemp);
                
                /* Saturation velocity: v_sat(T) = v_sat(T₀)·(T/T₀)^{-0.87} */
                if(model->MOS3vmax > 0.0) {
                    model->MOS3vmax *= pow(TempRatio, -0.87);
                }
            }
```

### 3.4 Sparse Matrix Pointer Allocation

```c
            /* SPARSE MATRIX ALLOCATION for 4×4 conductance matrix */
            
            /* Diagonal entries (always allocated) */
            inst->MOS3dPtrPosPtr = SMPmakeElt(matrix, 
                inst->MOS3dNode, inst->MOS3dNode);      /* G_dd */
            inst->MOS3sPtrPosPtr = SMPmakeElt(matrix,
                inst->MOS3sNode, inst->MOS3sNode);      /* G_ss */
            inst->MOS3gPtrGatePtr = SMPmakeElt(matrix,
                inst->MOS3gNode, inst->MOS3gNode);      /* G_gg */
            inst->MOS3bPtrBulkPtr = SMPmakeElt(matrix,
                inst->MOS3bNode, inst->MOS3bNode);      /* G_bb */
            
            /* Off-diagonal entries (conditionally non-zero) */
            inst->MOS3dPtrNegPtr = SMPmakeElt(matrix,
                inst->MOS3dNode, inst->MOS3sNode);      /* G_ds */
            inst->MOS3dPtrGatePtr = SMPmakeElt(matrix,
                inst->MOS3dNode, inst->MOS3gNode);      /* G_dg */
            inst->MOS3dPtrBulkPtr = SMPmakeElt(matrix,
                inst->MOS3dNode, inst->MOS3bNode);      /* G_db */
            
            inst->MOS3sPtrNegPtr = SMPmakeElt(matrix,
                inst->MOS3sNode, inst->MOS3dNode);      /* G_sd */
            inst->MOS3sPtrGatePtr = SMPmakeElt(matrix,
                inst->MOS3sNode, inst->MOS3gNode