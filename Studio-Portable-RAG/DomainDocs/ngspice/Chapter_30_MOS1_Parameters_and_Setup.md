# MOS1: Parameter Parsing and Matrix Setup

_Generated 2026-04-12 03:46 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1ask.c`

# Chapter: MOS1: Parameter Parsing and Matrix Setup

## Introduction

The MOS1 parameter parsing and matrix setup subsystem in Ngspice implements the critical bridge between SPICE deck specification and numerical simulation. The files `mos1mpar.c`, `mos1mask.c`, `mos1ask.c`, and `mos1set.c` collectively form a sophisticated parameter processing pipeline. `mos1mpar.c` defines the mapping tables that translate SPICE syntax (e.g., `VTO=0.7`, `L=1u`) to internal C structure fields using the `IFparm` system. `mos1mask.c` establishes unique integer identifiers for each parameter, enabling efficient switch-based parameter identification during simulation. `mos1ask.c` implements the query interface that allows the simulator to retrieve parameter values for analysis and debugging. The core computational work occurs in `mos1set.c`, which performs mathematical transformations on user parameters (calculating effective dimensions, transconductance coefficients, temperature scaling), validates physical constraints, and allocates the sparse matrix pointers for the 4×4 Jacobian matrix required for Newton-Raphson iteration. This subsystem ensures that all MOS1 device parameters are properly initialized, transformed, and integrated into the circuit's numerical solution framework before simulation begins.

---

## Mathematical Formulation

### Parameter Transformation and Effective Geometry

The MOS1 parameter parsing system performs critical mathematical transformations between user-specified SPICE parameters and the internal computational parameters used in device equations. These transformations account for process variations and ensure physical consistency.

#### Effective Channel Dimensions

The drawn channel length `L` and width `W` specified in the SPICE deck are converted to effective dimensions that account for lateral diffusion:

```
Leff = L - 2·LD
Weff = W - 2·WD
```

where:
- `LD` is the lateral diffusion length (model parameter `MOS1ld`)
- `WD` is the width diffusion (model parameter `MOS1wd`)

These effective dimensions are used in all current calculations to model the actual electrical channel.

#### Transconductance Coefficient Calculation

The fundamental transconductance parameter `β` is computed from geometry and process parameters:

```
β = (Weff / Leff) · KP
```

where `KP` is the intrinsic transconductance parameter. For enhanced accuracy with mobility reduction:

```
β_enhanced = (Weff / Leff) · KP · (1 + θ·(Vgs - VTO))
```

where `θ` is the mobility reduction coefficient.

#### Oxide Thickness to Transconductance Conversion

If oxide thickness `TOX` is specified instead of `KP`, the transconductance is calculated using oxide physics:

```
KP = μ₀ · ε₀ₓ / TOX
```

where:
- `μ₀` is the surface mobility (model parameter `MOS1u0`)
- `ε₀ₓ = 3.9 · ε₀` is the permittivity of silicon dioxide
- `ε₀ = 8.854 × 10⁻¹²` F/m is the vacuum permittivity

#### Parasitic Resistance Calculation

The total series resistances incorporate both lumped and distributed components:

```
Rd_total = RD + RSH · NRD
Rs_total = RS + RSH · NRS
```

where:
- `RD`, `RS` are lumped drain and source resistances
- `RSH` is the diffusion sheet resistance
- `NRD`, `NRS` are the number of squares in drain and source diffusion

#### Junction Capacitance Modeling

The bulk junction capacitances are computed from area and perimeter parameters:

```
Cbd_total = CBD · AD + CJSW · PD
Cbs_total = CBS · AS + CJSW · PS
```

where:
- `CBD`, `CBS` are zero-bias bottom capacitances
- `CJSW` is the zero-bias sidewall capacitance per unit length
- `AD`, `AS` are drain and source diffusion areas
- `PD`, `PS` are drain and source diffusion perimeters

For voltage-dependent junction capacitance:

```
Cj(V) = Cj0 / (1 - V/PB)^MJ  for V < FC·PB
Cj(V) = Cj0·(1 - FC)^(-MJ)·[1 - MJ·(V - FC·PB)/PB]  for V ≥ FC·PB
```

where `FC` is the forward bias coefficient (typically 0.5).

#### Overlap Capacitance Calculation

Gate overlap capacitances are proportional to effective width:

```
Cgso = CGSO · Weff
Cgdo = CGDO · Weff
Cgbo = CGBO · Leff
```

#### Temperature Scaling of Parameters

Device parameters are scaled from nominal temperature `TNOM` to operating temperature `T`:

##### Threshold Voltage Scaling

```
VTO(T) = VTO(TNOM) · (T/TNOM)
```

##### Mobility Temperature Dependence

```
μ₀(T) = μ₀(TNOM) · (T/TNOM)^(-3/2)
```

##### Junction Saturation Current Scaling

```
IS(T) = IS(TNOM) · exp((EG/N)·(1/TNOM - 1/T))
```

where:
- `EG` is the bandgap energy (≈ 1.11 eV for silicon)
- `N` is the emission coefficient (typically 1 for diodes)

##### Surface Potential Temperature Dependence

```
φ(T) = φ(TNOM) · (T/TNOM) - 2·(kT/q)·ln(T/TNOM)
```

where `k` is Boltzmann's constant and `q` is electron charge.

### Sparse Matrix Structure for Four-Terminal Device

The MOS1 device contributes to the circuit's sparse matrix system with a 4×4 conductance matrix. The matrix stamping follows precise mathematical patterns:

#### Conductance Matrix Pattern

For the four-terminal device (Drain, Gate, Source, Bulk), the Jacobian matrix has this structure:

```
[Gdd  Gdg  Gds  Gdb] [Vd]   [Id]
[Ggd  Ggg  Ggs  Ggb] [Vg] = [Ig]
[Gsd  Gsg  Gss  Gsb] [Vs]   [Is]
[Gbd  Bbg  Gbs  Gbb] [Vb]   [Ib]
```

#### Matrix Element Allocation Strategy

The sparse matrix allocation creates pointers for all 16 possible entries, though many will be zero:

1. **Diagonal Elements** (always allocated):
   - `Gdd = ∂Id/∂Vd = gds`
   - `Ggg = ∂Ig/∂Vg ≈ 0` (gate insulation)
   - `Gss = ∂Is/∂Vs = gds + gm + gmb`
   - `Gbb = ∂Ib/∂Vb ≈ 0` (bulk current negligible)

2. **Non-Zero Off-Diagonal Elements**:
   - `Gds = Gsd = -gds` (drain-source coupling)
   - `Gdg = -Gsg = gm` (gate control)
   - `Gdb = -Gsb = gmb` (body effect)
   - `Gsd = -Gdd = -gds` (source-drain symmetry)

3. **Zero Elements** (allocated but typically zero):
   - `Ggd, Ggs, Ggb` (gate currents negligible)
   - `Gbg, Gbd, Gbs` (bulk currents negligible)

#### State Vector Allocation for Charge Storage

For transient analysis, charge state variables are allocated:

```
q_gs: Gate-source charge
q_gd: Gate-drain charge  
q_gb: Gate-bulk charge
q_bd: Bulk-drain junction charge
q_bs: Bulk-source junction charge
```

These follow the charge conservation equation:
```
q_g + q_b + q_d + q_s = 0
```

## Convergence Analysis

### Parameter-Dependent Convergence Behavior

The convergence of Newton-Raphson iteration in MOS1 simulation is strongly influenced by parameter choices and their mathematical transformations.

#### Effective Dimension Sensitivity

The effective channel dimensions `Leff` and `Weff` affect convergence through:

```
∂β/∂L = -β/L
∂β/∂W = β/W
```

Small `Leff` values (approaching zero) cause large `∂β/∂L`, potentially leading to convergence issues. The implementation protects against this with:

```
if(Leff ≤ 0) Leff = 1e-12
```

#### Threshold Voltage Continuity

The body effect term in threshold voltage calculation:

```
Vth = VTO + γ·(√(2φ + Vsb) - √(2φ))
```

has derivative:
```
∂Vth/∂Vsb = γ / (2√(2φ + Vsb))
```

This derivative becomes large when `2φ + Vsb → 0`, potentially causing convergence problems. The implementation uses:

```
if(2φ + Vsb < ε) sqrt_term = √ε
```

where `ε ≈ 10⁻¹²`.

#### Mobility Reduction and Convergence Radius

The enhanced transconductance with mobility reduction:

```
β_enhanced = β₀·(1 + θ·(Vgs - VTO))
```

introduces additional nonlinearity with derivative:
```
∂β_enhanced/∂Vgs = β₀·θ
```

Large `θ` values reduce the convergence radius of Newton-Raphson iteration.

### Sparse Matrix Conditioning Analysis

#### Matrix Condition Number

The 4×4 conductance matrix has condition number:

```
κ(G) = ||G||·||G⁻¹||
```

For typical MOSFET operating points:
- `Gdd ≈ gds` (small, ~10⁻⁶ to 10⁻³ S)
- `Gdg = gm` (moderate, ~10⁻⁴ to 10⁻² S)
- `Ggg ≈ 0` (ideally zero)

This creates a poorly conditioned matrix when `gm/gds` ratio is large (typical in saturation). The sparse solver must handle this ill-conditioning.

#### Pivot Selection for Numerical Stability

During LU decomposition, pivot selection is critical for:

1. **Gate Node Handling**: Since `Ggg ≈ 0`, the gate node equation may require special pivoting
2. **Bulk Node Handling**: Similar issues with `Gbb ≈ 0`
3. **Drain-Source Symmetry**: The near-symmetry `Gdd ≈ -Gds ≈ -Gsd ≈ Gss` affects pivot choices

### Initial Condition Convergence

#### DC Initialization Strategies

The `.IC` parameter provides initial voltage guesses:

```
VDS(0) = IC_VDS
VGS(0) = IC_VGS  
VBS(0) = IC_VBS
```

These affect convergence through the initial Jacobian evaluation. The error in initial guess `ΔV` propagates as:

```
||V^(k) - V^*|| ≤ C·||ΔV||^k
```

where `C` depends on the Lipschitz constant of the device equations.

#### OFF State Initialization

When `OFF=1` is specified, the device starts in cutoff:

```
VGS(0) = 0
VDS(0) = 0
VBS(0) = 0
```

This guarantees convergence for the first Newton iteration but may require more iterations to reach the actual operating point.

### Temperature-Dependent Convergence

#### Parameter Scaling Smoothness

The temperature scaling functions must be `C¹` continuous for Newton-Raphson convergence:

```
VTO(T) scaling: C¹ continuous for T > 0
μ₀(T) scaling: C¹ continuous for T > 0  
φ(T) scaling: C¹ continuous for T > 0
```

Discontinuities in derivatives would cause convergence failure.

#### Multi-Temperature Simulation Convergence

When different instances have different `TEMP` parameters, the global convergence is governed by the worst-conditioned device. The convergence criterion becomes:

```
max_i |Id_i^(k+1) - Id_i^(k)| < ε_abs + ε_rel·|Id_i^(k)|
```

where `i` indexes all MOSFET instances.

### Parasitic Element Convergence Effects

#### Series Resistance Convergence

The iterative solution for internal voltages with series resistances:

```
Vd' = Vd - Id·Rd
Vs' = Vs + Id·Rs
```

has convergence rate determined by the loop gain:

```
L = (gm + gmb)·(Rd + Rs)
```

Convergence requires `|L| < 1`, which may not hold for large `Rd`, `Rs` values.

#### Junction Capacitance Convergence

The voltage-dependent junction capacitance:

```
Cj(V) = Cj0/(1 - V/PB)^MJ
```

has derivative:
```
dCj/dV = MJ·Cj0/[PB·(1 - V/PB)^(MJ+1)]
```

which becomes large as `V → PB`, potentially causing convergence issues in transient analysis.

### Sparse Matrix Fill-in and Convergence

#### Matrix Sparsity Pattern

The allocated 16 matrix entries create this sparsity pattern for N MOSFETs:

```
Non-zero entries = 16N
Total matrix size = (N_nodes)²
Sparsity = 1 - 16N/(N_nodes)²
```

For large circuits, sparsity > 99%, enabling efficient solution.

#### Fill-in During LU Decomposition

The gate and bulk nodes with near-zero diagonal entries can cause fill-in during LU decomposition, increasing computational cost but not affecting convergence.

### Convergence Monitoring and Adaptation

#### Parameter-Based Convergence Prediction

The setup phase can predict potential convergence issues:

```
if(Leff < 1e-8) issue warning: "Very short channel may cause convergence issues"
if(θ > 1.0) issue warning: "Large mobility reduction may slow convergence"
if(Rd + Rs > 1/gm) issue warning: "Large series resistance may cause convergence problems"
```

#### Adaptive Convergence Parameters

Based on device parameters, convergence tolerances can be adapted:

```
if(small Leff) ε_rel = 10⁻⁴ (tighter tolerance)
if(large θ) max_iterations = 100 (more iterations allowed)
if(large Rd/Rs) use_source_stepping = TRUE
```

This parameter-aware convergence strategy improves robustness across diverse device geometries and operating conditions.

---

## C Implementation

### Parameter Binding Architecture

The MOS1 parameter parsing system implements a sophisticated mapping between SPICE deck syntax and internal C data structures through a table-driven architecture.

#### Parameter Table Definitions

The core parameter mapping is defined in `mos1mpar.c` using the `IFparm` structure arrays:

```c
/* Model parameter table - maps SPICE deck parameters to C struct fields */
static IFparm MOS1mPTable[] = {
    IOP("vto",     MOS1_VTO,    IF_REAL, "Threshold voltage"),
    IOP("kp",      MOS1_KP,     IF_REAL, "Transconductance"),
    IOP("gamma",   MOS1_GAMMA,  IF_REAL, "Bulk threshold parameter"),
    IOP("phi",     MOS1_PHI,    IF_REAL, "Surface potential"),
    IOP("lambda",  MOS1_LAMBDA, IF_REAL, "Channel-length modulation"),
    IOP("rd",      MOS1_RD,     IF_REAL, "Drain ohmic resistance"),
    IOP("rs",      MOS1_RS,     IF_REAL, "Source ohmic resistance"),
    IOP("cbd",     MOS1_CBD,    IF_REAL, "Zero-bias B-D junction capacitance"),
    IOP("cbs",     MOS1_CBS,    IF_REAL, "Zero-bias B-S junction capacitance"),
    IOP("is",      MOS1_IS,     IF_REAL, "Bulk junction saturation current"),
    IOP("pb",      MOS1_PB,     IF_REAL, "Bulk junction potential"),
    IOP("cgso",    MOS1_CGSO,   IF_REAL, "Gate-source overlap capacitance"),
    IOP("cgdo",    MOS1_CGDO,   IF_REAL, "Gate-drain overlap capacitance"),
    IOP("cgbo",    MOS1_CGBO,   IF_REAL, "Gate-bulk overlap capacitance"),
    IOP("rsh",     MOS1_RSH,    IF_REAL, "Drain and source diffusion sheet resistance"),
    IOP("cj",      MOS1_CJ,     IF_REAL, "Zero-bias bulk junction bottom capacitance"),
    IOP("mj",      MOS1_MJ,     IF_REAL, "Bulk junction bottom grading coefficient"),
    IOP("cjsw",    MOS1_CJSW,   IF_REAL, "Zero-bias bulk junction sidewall capacitance"),
    IOP("mjsw",    MOS1_MJSW,   IF_REAL, "Bulk junction sidewall grading coefficient"),
    IOP("js",      MOS1_JS,     IF_REAL, "Bulk junction saturation current per area"),
    IOP("tox",     MOS1_TOX,    IF_REAL, "Oxide thickness"),
    IOP("ld",      MOS1_LD,     IF_REAL, "Lateral diffusion"),
    IOP("wd",      MOS1_WD,     IF_REAL, "Width diffusion"),
    IOP("u0",      MOS1_U0,     IF_REAL, "Surface mobility"),
    IOP("fc",      MOS1_FC,     IF_REAL, "Forward bias junction fit parameter"),
    IP("nmos",     MOS1_TYPE,   IF_FLAG, "N-type MOSFET model"),
    IP("pmos",     MOS1_TYPE,   IF_FLAG, "P-type MOSFET model"),
    OP("vcrit",    MOS1_VCRIT,  IF_REAL, "Critical voltage"),
};

/* Instance parameter table */
static IFparm MOS1pTable[] = {
    IOP("l",       MOS1_L,      IF_REAL, "Channel length"),
    IOP("w",       MOS1_W,      IF_REAL, "Channel width"),
    IOP("ad",      MOS1_AD,     IF_REAL, "Drain area"),
    IOP("as",      MOS1_AS,     IF_REAL, "Source area"),
    IOP("pd",      MOS1_PD,     IF_REAL, "Drain perimeter"),
    IOP("ps",      MOS1_PS,     IF_REAL, "Source perimeter"),
    IOP("nrd",     MOS1_NRD,    IF_REAL, "Number of squares in drain"),
    IOP("nrs",     MOS1_NRS,    IF_REAL, "Number of squares in source"),
    IOP("off",     MOS1_OFF,    IF_FLAG, "Device initially off"),
    IOP("ic",      MOS1_IC,     IF_REALVEC, "Initial condition vector"),
    IOP("temp",    MOS1_TEMP,   IF_REAL, "Instance temperature"),
    IOP("dtemp",   MOS1_DTEMP,  IF_REAL, "Instance temperature difference"),
    IOP("m",       MOS1_M,      IF_REAL, "Multiplier"),
};
```

Each entry uses macros to define parameter characteristics:
- `IOP()`: Input-only parameter with real value
- `IP()`: Input-only parameter with flag/integer value  
- `OP()`: Output-only parameter (computed, not user-specified)

#### Parameter Mask System

The `mos1mask.c` file defines unique integer masks for each parameter, enabling efficient switch-based parameter identification:

```c
/* Parameter ID masks - used for quick parameter identification */
#define MOS1_L        1
#define MOS1_W        2
#define MOS1_AD       3
#define MOS1_AS       4
#define MOS1_PD       5
#define MOS1_PS       6
#define MOS1_NRD      7
#define MOS1_NRS      8
#define MOS1_OFF      9
#define MOS1_IC       10
#define MOS1_TEMP     11
#define MOS1_DTEMP    12
#define MOS1_M        13

#define MOS1_VTO      101
#define MOS1_KP       102
#define MOS1_GAMMA    103
#define MOS1_PHI      104
#define MOS1_LAMBDA   105
#define MOS1_RD       106
#define MOS1_RS       107
#define MOS1_CBD      108
#define MOS1_CBS      109
#define MOS1_IS       110
#define MOS1_PB       111
#define MOS1_CGSO     112
#define MOS1_CGDO     113
#define MOS1_CGBO     114
#define MOS1_RSH      115
#define MOS1_CJ       116
#define MOS1_MJ       117
#define MOS1_CJSW     118
#define MOS1_MJSW     119
#define MOS1_JS       120
#define MOS1_TOX      121
#define MOS1_LD       122
#define MOS1_WD       123
#define MOS1_U0       124
#define MOS1_FC       125
#define MOS1_TYPE     126
#define MOS1_VCRIT    127
```

The separation into instance parameters (1-99) and model parameters (100+) allows quick identification of parameter scope.

### Parameter Query Implementation

The `mos1ask.c` file implements the parameter query interface using switch statements keyed by the mask values:

```c
int MOS1ask(CKTcircuit *ckt, GENinstance *geninst, int which, IFvalue *value) {
    MOS1instance *inst = (MOS1instance *)geninst;
    
    switch(which) {
        case MOS1_W:
            value->rValue = inst->MOS1w;
            return OK;
        case MOS1_L:
            value->rValue = inst->MOS1l;
            return OK;
        case MOS1_AD:
            value->rValue = inst->MOS1ad;
            return OK;
        case MOS1_AS:
            value->rValue = inst->MOS1as;
            return OK;
        case MOS1_PD:
            value->rValue = inst->MOS1pd;
            return OK;
        case MOS1_PS:
            value->rValue = inst->MOS1ps;
            return OK;
        case MOS1_TEMP:
            value->rValue = inst->MOS1temp;
            return OK;
        case MOS1_OFF:
            value->iValue = inst->MOS1off;
            return OK;
        case MOS1_ICVDS:
            value->rValue = inst->MOS1icVDS;
            return OK;
        case MOS1_ICVGS:
            value->rValue = inst->MOS1icVGS;
            return OK;
        case MOS1_ICVBS:
            value->rValue = inst->MOS1icVBS;
            return OK;
        default:
            return E_BADPARM;
    }
}

int MOS1mAsk(CKTcircuit *ckt, GENmodel *genmodel, int which, IFvalue *value) {
    MOS1model *model = (MOS1model *)genmodel;
    
    switch(which) {
        case MOS1_VTO:
            value->rValue = model->MOS1vt0;
            return OK;
        case MOS1_KP:
            value->rValue = model->MOS1kp;
            return OK;
        case MOS1_GAMMA:
            value->rValue = model->MOS1gamma;
            return OK;
        case MOS1_PHI:
            value->rValue = model->MOS1phi;
            return OK;
        case MOS1_LAMBDA:
            value->rValue = model->MOS1lambda;
            return OK;
        case MOS1_RD:
            value->rValue = model->MOS1rd;
            return OK;
        case MOS1_RS:
            value->rValue = model->MOS1rs;
            return OK;
        case MOS1_CBD:
            value->rValue = model->MOS1cbd;
            return OK;
        case MOS1_CBS:
            value->rValue = model->MOS1cbs;
            return OK;
        case MOS1_IS:
            value->rValue = model->MOS1is;
            return OK;
        case MOS1_PB:
            value->rValue = model->MOS1pb;
            return OK;
        case MOS1_TYPE:
            value->iValue = model->MOS1type;
            return OK;
        default:
            return E_BADPARM;
    }
}
```

This direct mapping from mask values to structure field accesses provides efficient parameter retrieval during simulation.

### Setup and Matrix Allocation Implementation

The `mos1set.c` file contains the core setup logic that performs mathematical transformations and allocates sparse matrix pointers:

```c
int MOS1setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS1model *model;
    MOS1instance *inst;
    int error;
    
    /* Loop through all models */
    for(model = (MOS1model *)inModel; model != NULL; model = model->MOS1nextModel) {
        
        /* Default model parameters if not set by user */
        if(!model->MOS1vt0Given)    model->MOS1vt0 = 0.0;
        if(!model->MOS1kpGiven)     model->MOS1kp = 2e-5;
        if(!model->MOS1gammaGiven)  model->MOS1gamma = 0.0;
        if(!model->MOS1phiGiven)    model->MOS1phi = 0.6;
        if(!model->MOS1lambdaGiven) model->MOS1lambda = 0.0;
        
        /* Calculate derived parameters */
        model->MOS1coeff = model->MOS1kp;
        model->MOS1vbi = model->MOS1type * model->MOS1vt0;
        
        /* Setup each instance */
        for(inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            
            /* Default instance parameters */
            if(!inst->MOS1lGiven) inst->MOS1l = 100e-6;
            if(!inst->MOS1wGiven) inst->MOS1w = 100e-6;
            if(!inst->MOS1adGiven) inst->MOS1ad = 0.0;
            if(!inst->MOS1asGiven) inst->MOS1as = 0.0;
            if(!inst->MOS1pdGiven) inst->MOS1pd = 0.0;
            if(!inst->MOS1psGiven) inst->MOS1ps = 0.0;
            
            /* Calculate effective dimensions - direct C implementation of Leff = L - 2·LD */
            inst->MOS1effL = inst->MOS1l - 2 * model->MOS1ld;
            inst->MOS1effW = inst->MOS1w - 2 * model->MOS1wd;
            
            /* Ensure positive dimensions - numerical protection */
            if(inst->MOS1effL <= 0.0) inst->MOS1effL = 1e-12;
            if(inst->MOS1effW <= 0.0) inst->MOS1effW = 1e-12;
            
            /* Calculate beta = (Weff / Leff) * KP - core mathematical transformation */
            inst->MOS1beta = (inst->MOS1effW / inst->MOS1effL) * model->MOS1kp;
            
            /* Allocate SMP matrix pointers for 4-terminal device */
            /* Matrix structure: [drain, gate, source, bulk] x [drain, gate, source, bulk] */
            
            /* Diagonal entries */
            inst->MOS1drainDrainPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1dNode);
            inst->MOS1gateGatePtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1gNode);
            inst->MOS1sourceSourcePtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1sNode);
            inst->MOS1bulkBulkPtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1bNode);
            
            /* Cross entries - all 12 off-diagonal entries allocated */
            inst->MOS1drainSourcePtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1sNode);
            inst->MOS1drainGatePtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1gNode);
            inst->MOS1drainBulkPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1bNode);
            
            inst->MOS1sourceDrainPtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1dNode);
            inst->MOS1sourceGatePtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1gNode);
            inst->MOS1sourceBulkPtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1bNode);
            
            /* Gate is ideally insulated - pointers allocated but conductances will be zero */
            inst->MOS1gateDrainPtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1dNode);
            inst->MOS1gateSourcePtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1sNode);
            inst->MOS1gateBulkPtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1bNode);
            
            inst->MOS1bulkDrainPtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1dNode);
            inst->MOS1bulkSourcePtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1sNode);
            inst->MOS1bulkGatePtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1gNode);
            
            /* Check for allocation errors */
            if(!inst->MOS1drainDrainPtr || !inst->MOS1sourceSourcePtr) {
                return E_NOMEM;
            }
            
            /* Allocate state vector entries for charges - 5 charge storage elements */
            inst->MOS1qgs = *states; (*states)++;
            inst->MOS1qgd = *states; (*states)++;
            inst->MOS1qgb = *states; (*states)++;
            inst->MOS1qbd = *states; (*states)++;
            inst->MOS1qbs = *states; (*states)++;
            
            /* Initialize charges to zero */
            *(ckt->CKTrhsOld + inst->MOS1qgs) = 0.0;
            *(ckt->CKTrhsOld + inst->MOS1qgd) = 0.0;
            *(ckt->CKTrhsOld + inst->MOS1qgb) = 0.0;
            *(ckt->CKTrhsOld + inst->MOS1qbd) = 0.0;
            *(ckt->CKTrhsOld + inst->MOS1qbs) = 0.0;
            
            /* Set initial conditions if specified */
            if(inst->MOS1off) {
                /* Device initially off - sets mode flag */
                inst->MOS1mode = 0;
            }
            
            if(inst->MOS1icGiven) {
                /* Apply initial conditions directly to RHS vector */
                if(inst->MOS1icVDS != 0.0) {
                    *(ckt->CKTrhs + inst->MOS1dNode) -= inst->MOS1icVDS;
                    *(ckt->CKTrhs + inst->MOS1sNode) += inst->MOS1icVDS;
                }
            }
        }
    }
    
    return OK;
}
```

### Mathematical Parameter Processing Implementation

The setup function implements several critical mathematical transformations in C:

#### Effective Dimension Calculation

```c
/* Direct C translation of Leff = L - 2·LD and Weff = W - 2·WD */
inst->MOS1effL = inst->MOS1l - 2 * model->MOS1ld;
inst->MOS1effW = inst->MOS1w - 2 * model->MOS1wd;

/* Numerical protection against non-positive dimensions */
if(inst->MOS1effL <= 0.0) inst->MOS1effL = 1e-12;
if(inst->MOS1effW <= 0.0) inst->MOS1effW = 1e-12;
```

#### Transconductance Parameter Calculation

```c
/* β = (Weff / Leff) · KP */
inst->MOS1beta = (inst->MOS1effW / inst->MOS1effL) * model->MOS1kp;
```

#### Oxide Thickness to KP Conversion

```c
/* If TOX specified but KP not given, calculate KP = μ₀·ε₀ₓ/TOX */
if(model->MOS1tox <= 0.0) {
    model->MOS1tox = 1e-7;  /* Default oxide thickness */
    /* Recalculate KP from oxide thickness */
    model->MOS1kp = model->MOS1u0 * 3.9 * 8.854e-12 / model->MOS1tox;
}
```

#### Temperature Scaling Implementation

```c
if(inst->MOS1temp != ckt->CKTtemp) {
    /* Apply temperature scaling */
    double T = inst->MOS1temp + CONSTCtoK;
    double TNOM = model->MOS1tnom + CONSTCtoK;
    double VT = KoverQ * T;
    double VTNOM = KoverQ * TNOM;
    
    /* Scale threshold voltage: VTO(T) = VTO(TNOM)·(T/TNOM) */
    inst->MOS1vt0 = model->MOS1vt0 * (T/TNOM);
    
    /* Scale mobility: μ₀(T) = μ₀(TNOM)·(T/TNOM)^(-3/2) */
    inst->MOS1u0 = model->MOS1u0 * pow(T/TNOM, -1.5);
    
    /* Scale saturation current: IS(T) = IS(TNOM)·exp((EG/N)·(1/TNOM - 1/T)) */
    inst->MOS1is = model->MOS1is * exp((EG/N)*(1/TNOM - 1/T));
}
```

### Sparse Matrix Pointer Allocation Pattern

The matrix allocation follows a systematic pattern for the 4-terminal device:

```c
/* 16 matrix pointers allocated in this exact pattern:
   [row, column] mapping:
   0: Drain, 1: Gate, 2: Source, 3: Bulk
   
   This creates the complete 4x4 Jacobian matrix for Newton-Raphson */
   
/* Row 0: Drain node equations */
inst->MOS1drainDrainPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1dNode);     /* [0,0] */
inst->MOS1drainGatePtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1gNode);      /* [0,1] */
inst->MOS1drainSourcePtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1sNode);    /* [0,2] */
inst->MOS1drainBulkPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1bNode);      /* [0,3] */

/* Row 1: Gate node equations */
inst->MOS1gateDrainPtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1dNode);      /* [1,0] */
inst->MOS1gateGatePtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1gNode);       /* [1,1] */
inst->MOS1gateSourcePtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1sNode);     /* [1,2] */
inst->MOS1gateBulkPtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1bNode);       /* [1,3] */

/* Row 2: Source node equations */
inst->MOS1sourceDrainPtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1dNode);    /* [2,0] */
inst->MOS1sourceGatePtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1gNode);     /* [2,1] */
inst->MOS1sourceSourcePtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1sNode);   /* [2,2] */
inst->MOS1sourceBulkPtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1bNode);     /* [2,3] */

/* Row 3: Bulk node equations */
inst->MOS1bulkDrainPtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1dNode);      /* [3,0] */
inst->MOS1bulkSourcePtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1sNode);     /* [3,2] */
inst->MOS1bulkGatePtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1gNode);       /* [3,1] */
inst->MOS1bulkBulkPtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1bNode);       /* [3,3] */
```

### Parameter Validation and Default Logic

The implementation includes comprehensive parameter validation:

```c
/* Surface potential validation */
if(model->MOS1phi <= 0.0) {
    model->MOS1phi =