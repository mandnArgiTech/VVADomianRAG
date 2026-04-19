# BSIM2: API Binding and Memory Lifecycle

_Generated 2026-04-12 12:20 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/bsim2init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2dest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2del.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2mdel.c`

# BSIM2: API Binding and Memory Lifecycle

## Technical Introduction

The BSIM2 MOSFET model's integration into the Ngspice simulation kernel is orchestrated through a sophisticated API binding and memory management system implemented across five core C files: `bsim2init.c`, `b2.c`, `b2dest.c`, `b2del.c`, and `b2mdel.c`. These files collectively define the device's interface to the SPICE simulator, manage its lifecycle from initialization to destruction, and implement the mathematical formulations as executable code.

`bsim2init.c` establishes the fundamental contract between BSIM2 and Ngspice through the `SPICEdev BSIM2info` structure—a comprehensive function dispatch table that maps 20+ simulator operations to specific BSIM2 implementations. This binding enables the simulator kernel to invoke the correct device functions for DC analysis, transient simulation, AC small-signal analysis, convergence testing, and memory management without requiring internal knowledge of BSIM2's implementation details.

`b2.c` serves as the primary entry point and operation dispatcher, routing requests from the Ngspice kernel to the appropriate BSIM2 functions based on analysis type. This file implements the `BSIM2()` function that acts as a switchboard, translating generic SPICE operation codes into specific BSIM2 function calls, ensuring proper execution flow during complex multi-analysis simulations.

The memory management trilogy—`b2dest.c`, `b2del.c`, and `b2mdel.c`—implements a hierarchical destruction system that maintains pointer integrity while efficiently freeing allocated resources. `b2dest.c` provides complete device teardown for circuit cleanup, `b2del.c` enables selective instance deletion during netlist editing, and `b2mdel.c` handles model-level removal. Together, these files implement cascading free algorithms with O(N) time complexity that traverse the model-instance linked list hierarchy, preventing memory leaks and dangling pointers while supporting dynamic circuit modification.

This API binding system transforms the mathematical BSIM2 equations into a numerically stable, production-ready SPICE device implementation, providing the necessary infrastructure for Newton-Raphson iteration, charge conservation, convergence control, and efficient memory utilization throughout the device's lifecycle.

## Mathematical Formulation

The BSIM2 model's integration into the Ngspice simulation kernel is governed by a mathematical framework that maps physical device equations to numerical matrix operations. This formulation is essential for the device's API binding and memory lifecycle management.

### 1. Device Parameter Space and State Vector Formulation

The BSIM2 model operates in a high-dimensional parameter space defined by:

**Model Parameter Vector** (142 dimensions):
```
P_model = [tox, vfb, φ, k1, k2, η, μ0, θ, vmax, xj, ld, wd, δ, α, β, γ, κ, λ, ...]^T
```

**Instance State Vector** (dynamic dimensions):
```
X_instance(t) = [vds(t), vgs(t), vbs(t), id(t), qgs(t), qgd(t), qgb(t), qbd(t), qbs(t)]^T
```

The simulation solves the differential-algebraic system:
```
F(X(t), dX/dt, P_model, P_instance) = 0
```
where `F` represents Kirchhoff's current laws combined with BSIM2 device equations.

### 2. Sparse Matrix Representation for 4-Terminal Device

The BSIM2 device contributes to the global circuit Jacobian matrix `J` with a 4×4 block structure. For each instance, the conductance matrix stamp follows the pattern:

```
J_BSIM2 = ∂I/∂V = [Gdd  Gdg  Gds  Gdb]
                   [Ggd  Ggg  Ggs  Ggb]
                   [Gsd  Ssg  Gss  Gsb]
                   [Gbd  Bbg  Gbs  Gbb]
```

The non-zero elements are computed from BSIM2 partial derivatives:

```
Gdd = ∂Id/∂Vd = gds + gd + ∂Ibd/∂Vd
Gds = ∂Id/∂Vs = -gds - gm - gmb
Gdg = ∂Id/∂Vg = gm
Gdb = ∂Id/∂Vb = gmb + ∂Ibd/∂Vb
Gsd = ∂Is/∂Vd = -gds
Gss = ∂Is/∂Vs = gds + gs + ∂Ibs/∂Vs
Gsg = ∂Is/∂Vg = -gm
Gsb = ∂Is/∂Vb = -gmb + ∂Ibs/∂Vb
Gbd = ∂Ib/∂Vd = -gd + ∂Ibd/∂Vd
Gbs = ∂Ib/∂Vs = -gs + ∂Ibs/∂Vs
Gbb = ∂Ib/∂Vb = gd + gs + ∂Ibd/∂Vb + ∂Ibs/∂Vb
```

where:
- `gm = ∂Id/∂Vgs` (transconductance)
- `gds = ∂Id/∂Vds` (drain conductance)
- `gmb = ∂Id/∂Vbs` (bulk transconductance)
- `gd, gs` = junction conductances

### 3. Charge Conservation Formulation

The BSIM2 model implements charge conservation through state variable allocation. The charge vector `Q` and its time derivative are:

```
Q = [qgs, qgd, qgb, qbd, qbs]^T
dQ/dt = C · dV/dt
```

where the capacitance matrix `C` is:

```
C = [∂qgs/∂vgs  ∂qgs/∂vgd  ∂qgs/∂vgb  0       0      ]
    [∂qgd/∂vgs  ∂qgd/∂vgd  ∂qgd/∂vgb  0       0      ]
    [∂qgb/∂vgs  ∂qgb/∂vgd  ∂qgb/∂vgb  0       0      ]
    [0          0          0          ∂qbd/∂vbd 0      ]
    [0          0          0          0        ∂qbs/∂vbs]
```

The terminal currents include displacement currents:
```
Id_total = Id_dc + d(qgd)/dt
Is_total = Is_dc - d(qgs)/dt
Ig_total = -d(qgs + qgd + qgb)/dt
Ib_total = Ib_dc - d(qbd + qbs)/dt
```

### 4. Linked List Traversal Mathematics

The memory management uses linked list structures with traversal algorithms:

**Model List**: `M1 → M2 → ... → Mn → NULL`
**Instance List per Model**: `I1 → I2 → ... → Im → NULL`

The total memory allocation for N models with Mᵢ instances each is:
```
Total Memory = Σᵢ=1ᴺ [sizeof(BSIM2model) + Σⱼ=1ᴹⁱ (sizeof(BSIM2instance) + |nameⱼ| + 1)]
```

The destruction algorithm has time complexity:
```
T_destroy = O(Σᵢ=1ᴺ Mᵢ) ≈ O(total instances)
```
with space complexity O(1) for the destruction process itself.

### 5. Function Dispatch Table Mathematics

The SPICEdev structure creates a bijective mapping between operation codes and function pointers:

```
f: OP_CODE → FUNCTION_POINTER
```

For BSIM2, this mapping is:
```
f(OP_SETUP) = BSIM2setup
f(OP_LOAD) = BSIM2load
f(OP_ACLOAD) = BSIM2acLoad
f(OP_TRUNC) = BSIM2trunc
f(OP_CONV) = BSIM2convTest
f(OP_TEMP) = BSIM2temp
f(OP_DESTROY) = BSIM2destroy
f(OP_DELETE) = BSIM2delete
f(OP_MDELETE) = BSIM2mDelete
```

The Ngspice kernel executes device operations via:
```
result = device_table[DEVICE_INDEX].function_table[OPERATION](args)
```

## Convergence Analysis

### 1. Newton-Raphson Iteration Convergence Criteria

The BSIM2 convergence test implements a multi-dimensional tolerance check. For iteration k, the convergence condition is:

**Voltage Convergence**:
```
|Vᵢ⁽ᵏ⁾ - Vᵢ⁽ᵏ⁻¹⁾| ≤ ε_rel·max(|Vᵢ⁽ᵏ⁾|, |Vᵢ⁽ᵏ⁻¹⁾|) + ε_abs
```
for all terminal voltages Vᵢ ∈ {Vgs, Vgd, Vgb, Vbs, Vbd}, where:
- `ε_rel = CKTreltol` (typically 0.001)
- `ε_abs = CKTvoltTol` (typically 1e-6)

**Charge Convergence**:
```
|Qⱼ⁽ᵏ⁾ - Qⱼ⁽ᵏ⁻¹⁾| ≤ ε_rel·max(|Qⱼ⁽ᵏ⁾|, |Qⱼ⁽ᵏ⁻¹⁾|) + ε_chg
```
for all charges Qⱼ ∈ {qgs, qgd, qgb, qbd, qbs}, where:
- `ε_chg = CKTchgTol` (typically 1e-14)

### 2. Local Truncation Error (LTE) Control

For transient analysis with time step h, the LTE for charge-based integration is bounded by:

```
LTE = |h·(q̈(t) + O(h²))| ≤ TOL
```

The BSIM2trunc function estimates the second derivative of charge:
```
q̈(t) ≈ [q(t) - 2q(t-h) + q(t-2h)] / h²
```

The time step is adjusted using:
```
h_new = h_old · √(TOL / LTE)
```
where `TOL = CKTtrtol · (ε_rel·|q| + ε_chg)`.

### 3. Jacobian Matrix Conditioning Analysis

The BSIM2 Jacobian matrix must remain well-conditioned for Newton-Raphson convergence. The condition number κ(J) should satisfy:

```
κ(J) = ‖J‖·‖J⁻¹‖ < κ_max
```

where typical SPICE simulations require κ_max ≈ 10¹². The BSIM2 implementation ensures this through:

1. **Voltage Limiting**: Using `DEVfetlim` to prevent large voltage changes:
   ```
   ΔV_limited = V_thermal · limiter(ΔV / V_thermal)
   ```
   where `V_thermal = kT/q` and the limiter function ensures smooth transitions.

2. **Regularization of Singularities**: Near Vds = 0, the conductance is regularized:
   ```
   gds_regularized = gds + ε_machine
   ```

### 4. Memory Access Pattern and Cache Efficiency

The linked list traversal for convergence checking follows:
```
for each model m in model_list:
    for each instance i in m.instance_list:
        check_convergence(i)
```

This results in memory access patterns that can be analyzed as:

**Spatial Locality**: High within each instance (parameters stored contiguously)
**Temporal Locality**: Moderate (instances checked every iteration)

The algorithm complexity is:
```
T_convergence = O(N_models × N_instances × N_voltages)
```

### 5. Numerical Stability of Destruction Algorithms

The memory destruction algorithm must avoid dangling pointers. The mathematical invariant maintained is:

```
Before destruction: G = {all allocated BSIM2 objects}
After destruction: G = ∅
```

The algorithm ensures:
```
∀ pointer p ∈ G: free(p) is called exactly once
∀ pointer q referencing p ∈ G: q is set to NULL before p is freed
```

This prevents:
1. Double-free errors: `free(p)` called multiple times
2. Use-after-free: Accessing `p` after `free(p)`
3. Memory leaks: `p` never freed

### 6. API Binding Stability Analysis

The SPICEdev binding creates a contract between Ngspice and BSIM2:

**Preconditions**:
1. `BSIM2info` structure must be fully initialized
2. Function pointers must be valid (non-NULL for required functions)
3. Parameter tables must match structure definitions

**Postconditions**:
1. Device registration succeeds: `get_bsim2_info()` returns valid pointer
2. Function dispatch works: `BSIM2()` routes to correct implementation
3. Memory management symmetric: `BSIM2destroy()` reverses `BSIM2setup()`

The binding correctness can be verified by the invariant:
```
∀ operation op ∈ REQUIRED_OPS: BSIM2info.DEVop != NULL
```

### 7. Convergence Rate Analysis

The Newton-Raphson iteration for BSIM2 exhibits quadratic convergence when near the solution:
```
‖X⁽ᵏ⁺¹⁾ - X*‖ ≤ C·‖X⁽ᵏ⁾ - X*‖²
```

where C depends on the Lipschitz constant of the Jacobian. In practice, BSIM2 achieves:
- 3-5 iterations for DC operating point
- 2-3 iterations per time step in transient analysis
- 1 iteration for small-signal AC analysis (linear)

### 8. Error Propagation in Parameter Binding

Parameter parsing from SPICE deck to internal structures introduces quantization errors:

```
P_internal = P_SPICE + δP
```

where δP represents:
1. Floating-point rounding: `|δP| ≤ ε_machine·|P|`
2. Unit conversion errors: `|δP| ≤ ε_unit·|P|`
3. Default value substitutions

The BSIM2 initialization ensures:
```
|δP|/|P| < ε_rel for all significant parameters
```

This mathematical formulation and convergence analysis provides the foundation for BSIM2's robust integration into Ngspice, ensuring numerical stability, charge conservation, and efficient memory management throughout the device lifecycle.

## C Implementation

### 1. Core Data Structures and Memory Organization

The BSIM2 implementation in Ngspice employs a hierarchical data structure system that separates model parameters from instance-specific state. This design enables efficient memory usage and supports multiple device instances sharing the same model parameters.

#### 1.1 Model Structure (`sBSIM2model`)

The `sBSIM2model` structure, defined in `bsim2def.h`, stores all physical parameters that remain constant across instances of the same model:

```c
typedef struct sBSIM2model {
    int BSIM2type;                    /* N_TYPE or P_TYPE */
    double BSIM2version;              /* Model version */
    double BSIM2tox;                  /* Oxide thickness */
    double BSIM2vfb;                  /* Flat-band voltage */
    double BSIM2phi;                  /* Surface potential */
    /* ... 142 total parameters with bit flags for given status */
    struct sBSIM2model *BSIM2nextModel;   /* Next model in linked list */
    sBSIM2instance *BSIM2instances;       /* Pointer to instance list */
} BSIM2model;
```

Each parameter field corresponds directly to mathematical variables in the BSIM2 equations. For example:
- `BSIM2vfb` maps to VFB (flat-band voltage) in the threshold voltage equation
- `BSIM2phi` maps to φ (surface potential)
- `BSIM2k1` maps to K1 (body effect coefficient)
- `BSIM2eta` maps to η (DIBL coefficient)

The bit flags (e.g., `BSIM2vfbGiven:1`) implement a validation system ensuring only user-specified parameters override defaults, while the linked list pointer `BSIM2nextModel` enables multiple BSIM2 models in a single circuit.

#### 1.2 Instance Structure (`sBSIM2instance`)

The `sBSIM2instance` structure contains instance-specific electrical state and computed values:

```c
typedef struct sBSIM2instance {
    char *BSIM2name;                    /* Instance name */
    int BSIM2dNode, BSIM2gNode, BSIM2sNode, BSIM2bNode; /* Node indices */
    double BSIM2l, BSIM2w;              /* Geometric parameters */
    double BSIM2vds, BSIM2vgs, BSIM2vbs; /* Terminal voltages */
    double BSIM2cd;                     /* Drain current */
    double BSIM2gm, BSIM2gds, BSIM2gmb; /* Small-signal parameters */
    double BSIM2qgs, BSIM2qgd, BSIM2qgb; /* Terminal charges */
    double BSIM2cqgs, BSIM2cqgd, BSIM2cqgb; /* Capacitances */
    int BSIM2states[10];                /* State vector indices */
    struct sBSIM2instance *BSIM2nextInstance; /* Next instance in list */
    BSIM2model *BSIM2modPtr;            /* Pointer to parent model */
} BSIM2instance;
```

The electrical state variables (`BSIM2vds`, `BSIM2vgs`, `BSIM2vbs`) store the terminal voltages computed during Newton-Raphson iteration. The small-signal parameters (`BSIM2gm`, `BSIM2gds`, `BSIM2gmb`) store the partial derivatives computed from the BSIM2 equations:

- `BSIM2gm = ∂Id/∂Vgs` (transconductance)
- `BSIM2gds = ∂Id/∂Vds` (output conductance)
- `BSIM2gmb = ∂Id/∂Vbs` (bulk transconductance)

### 2. SPICE Device API Binding

#### 2.1 Device Registration and Initialization

The `BSIM2info` structure in `bsim2init.c` provides the complete interface between the BSIM2 implementation and the Ngspice kernel:

```c
SPICEdev BSIM2info = {
    .DEVpublic = {
        .name = "bsim2",
        .description = "Berkeley Short-channel IGFET Model Version 2",
        .terms = 4,               /* D, G, S, B terminals */
        .numNames = 2,            /* M (instance), BSIM2 (model) */
        .termNames = {"d", "g", "s", "b"},
        .numInstanceParms = sizeof(BSIM2pTable)/sizeof(IFparm),
        .numModelParms = sizeof(BSIM2mPTable)/sizeof(IFparm),
        .flags = DEV_DEFAULT,
    },
    .DEVmodParam = BSIM2mPTable,   /* Model parameter table */
    .DEVinstParam = BSIM2pTable,   /* Instance parameter table */
    .DEVload = BSIM2load,          /* DC and transient load */
    .DEVsetup = BSIM2setup,        /* Setup and matrix allocation */
    /* ... 20+ function pointers mapping to BSIM2 implementations */
    .DEVinstSize = sizeof(BSIM2instance),
    .DEVmodSize = sizeof(BSIM2model),
};
```

This structure creates a function dispatch table where each analysis operation maps to a specific BSIM2 implementation function. The `DEVinstSize` and `DEVmodSize` fields enable the Ngspice kernel to allocate the correct amount of memory for each structure.

#### 2.2 Main Device Entry Point

The `BSIM2()` function in `b2.c` serves as the primary dispatch routine:

```c
int BSIM2(GENmodel *inModel, CKTcircuit *ckt, int operation) {
    BSIM2model *model = (BSIM2model *)inModel;
    int retval = OK;
    
    switch (operation) {
        case OP_INIT:      retval = BSIM2init(model, ckt); break;
        case OP_LOAD:      retval = BSIM2load(model, ckt); break;
        case OP_TRUNC:     retval = BSIM2trunc(model, ckt, ckt->CKTdelta); break;
        case OP_ACLOAD:    retval = BSIM2acLoad(model, ckt); break;
        case OP_TEMP:      retval = BSIM2temp(model, ckt); break;
        case OP_CONV:      retval = BSIM2convTest(model, ckt); break;
        case OP_SETUP:     retval = BSIM2setup(ckt->CKTmatrix, model, ckt, &ckt->CKTstate0); break;
        case OP_DESTROY:   retval = BSIM2destroy(&inModel); break;
        /* ... additional operations */
    }
    return retval;
}
```

This dispatch mechanism allows the Ngspice kernel to call the appropriate BSIM2 function based on the current analysis type (DC, transient, AC, etc.).

#### 2.3 Device Initialization

The `BSIM2init()` function initializes all model and instance parameters:

```c
int BSIM2init(GENmodel *inModel, CKTcircuit *ckt) {
    BSIM2model *model = (BSIM2model *)inModel;
    BSIM2instance *inst;
    
    for (; model != NULL; model = model->BSIM2nextModel) {
        /* Initialize model defaults */
        if (!model->BSIM2versionGiven) model->BSIM2version = 2.0;
        if (!model->BSIM2tnomGiven) model->BSIM2tnom = ckt->CKTnomTemp;
        
        for (inst = model->BSIM2instances; inst != NULL; inst = inst->BSIM2nextInstance) {
            /* Initialize instance defaults */
            if (!inst->BSIM2tempGiven) inst->BSIM2temp = ckt->CKTtemp;
            
            /* Initialize electrical state to zero */
            inst->BSIM2vds = inst->BSIM2vgs = inst->BSIM2vbs = 0.0;
            inst->BSIM2cd = 0.0;
            inst->BSIM2gm = inst->BSIM2gds = inst->BSIM2gmb = 0.0;
            
            /* Initialize charge states */
            inst->BSIM2qgs = inst->BSIM2qgd = inst->BSIM2qgb = 0.0;
            inst->BSIM2cqgs = inst->BSIM2cqgd = inst->BSIM2cqgb = 0.0;
        }
    }
    return OK;
}
```

This initialization ensures all state variables begin at known values before Newton-Raphson iteration begins.

### 3. Memory Management Implementation

#### 3.1 Complete Device Destruction

The `BSIM2destroy()` function in `b2dest.c` implements a cascading free algorithm:

```c
void BSIM2destroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    BSIM2model *model = (BSIM2model *)mod;
    BSIM2instance *inst, *nextInst;
    
    while (model) {
        BSIM2model *nextModel = model->BSIM2nextModel;
        
        /* Traverse and free all instances of this model */
        inst = model->BSIM2instances;
        while (inst) {
            nextInst = inst->BSIM2nextInstance;
            
            /* Free dynamically allocated instance name */
            if (inst->BSIM2name) FREE(inst->BSIM2name);
            
            /* Free the instance structure */
            FREE(inst);
            inst = nextInst;
        }
        
        /* Free the model structure */
        FREE(model);
        model = nextModel;
    }
    *inModel = NULL;
}
```

This algorithm has time complexity O(N_models × M_instances) and uses O(1) additional memory, efficiently cleaning up all allocated resources.

#### 3.2 Selective Instance Deletion

The `BSIM2delete()` function allows removal of specific instances by name:

```c
int BSIM2delete(GENmodel *inModel, IFuid name, GENinstance **kill) {
    BSIM2model *model = (BSIM2model *)inModel;
    BSIM2instance *prev = NULL, *inst;
    
    for (; model != NULL; model = model->BSIM2nextModel) {
        inst = model->BSIM2instances;
        while (inst) {
            if (strcmp(inst->BSIM2name, name) == 0) {
                /* Found instance - update linked list pointers */
                if (prev) prev->BSIM2nextInstance = inst->BSIM2nextInstance;
                else model->BSIM2instances = inst->BSIM2nextInstance;
                
                /* Free memory */
                FREE(inst->BSIM2name);
                FREE(inst);
                
                if (kill) *kill = NULL;
                return OK;
            }
            prev = inst;
            inst = inst->BSIM2nextInstance;
        }
    }
    return E_NODEV;
}
```

This function implements O(N) search through the instance linked lists, maintaining pointer integrity during removal.

#### 3.3 Model Deletion

The `BSIM2mDelete()` function removes entire models and their instances:

```c
int BSIM2mDelete(GENmodel **inModel, IFuid modname, GENmodel *kill) {
    BSIM2model **model = (BSIM2model **)inModel;
    BSIM2model *prev = NULL, *mod;
    
    for (mod = *model; mod != NULL; mod = mod->BSIM2nextModel) {
        if (mod == (BSIM2model *)kill) {
            /* Update model list pointers */
            if (prev) prev->BSIM2nextModel = mod->BSIM2nextModel;
            else *model = mod->BSIM2nextModel;
            
            /* Delete all instances first */
            BSIM2instance *inst = mod->BSIM2instances;
            while (inst) {
                BSIM2instance *nextInst = inst->BSIM2nextInstance;
                FREE(inst->BSIM2name);
                FREE(inst);
                inst = nextInst;
            }
            
            /* Free the model structure */
            FREE(mod);
            return OK;
        }
        prev = mod;
    }
    return E_NOMOD;
}
```

This ensures proper cleanup order: instances are freed before their parent model.

### 4. State Vector Allocation for Charge Conservation

The BSIM2 implementation uses Ngspice's state vector system to ensure charge conservation during transient analysis. In `BSIM2setup()`:

```c
/* Allocate state indices for charge storage */
inst->BSIM2states[0] = *states; (*states)++;  /* qgs */
inst->BSIM2states[1] = *states; (*states)++;  /* qgd */
inst->BSIM2states[2] = *states; (*states)++;  /* qgb */
inst->BSIM2states[3] = *states; (*states)++;  /* qbd */
inst->BSIM2states[4] = *states; (*states)++;  /* qbs */

/* Initialize charges in circuit state vector */
ckt->CKTrhsOld[inst->BSIM2states[0]] = 0.0;  /* qgs */
ckt->CKTrhsOld[inst->BSIM2states[1]] = 0.0;  /* qgd */
ckt->CKTrhsOld[inst->BSIM2states[2]] = 0.0;  /* qgb */
ckt->CKTrhsOld[inst->BSIM2states[3]] = 0.0;  /* qbd */
ckt->CKTrhsOld[inst->BSIM2states[4]] = 0.0;  /* qbs */
```

This allocation maps directly to the charge conservation mathematics:
- `qgs` corresponds to Q_gs in the gate-source charge equation
- `qgd` corresponds to Q_gd in the gate-drain charge equation  
- `qgb` corresponds to Q_gb in the gate-bulk charge equation
- `qbd` and `qbs` store junction charges for bulk-drain and bulk-source diodes

### 5. Convergence Testing Implementation

The `BSIM2convTest()` function implements the Newton-Raphson convergence criteria:

```c
int BSIM2convTest(GENmodel *inModel, CKTcircuit *ckt) {
    BSIM2model *model = (BSIM2model *)inModel;
    BSIM2instance *inst;
    
    for (; model != NULL; model = model->BSIM2nextModel) {
        for (inst = model->BSIM2instances; inst != NULL; inst = inst->BSIM2nextInstance) {
            /* Calculate terminal voltage differences */
            double vgs = ckt->CKTrhs[inst->BSIM2gNode] - ckt->CKTrhs[inst->BSIM2sNode];
            double vgd = ckt->CKTrhs[inst->BSIM2gNode] - ckt->CKTrhs[inst->BSIM2dNode];
            /* ... vgb, vbs, vbd similarly */
            
            /* Compute changes from previous iteration */
            double delvgs = vgs - inst->BSIM2vgs_old;
            double delvgd = vgd - inst->BSIM2vgd_old;
            /* ... other deltas */
            
            /* Voltage convergence test */
            if (fabs(delvgs) > ckt->CKTreltol * fabs(vgs) + ckt->CKTvoltTol ||
                fabs(delvgd) > ckt->CKTreltol * fabs(vgd) + ckt->CKTvoltTol) {
                ckt->CKTnoncon = 1;
                return OK;
            }
            
            /* Charge convergence test using capacitances */
            double delqgs = inst->BSIM2cqgs * delvgs;
            double delqgd = inst->BSIM2cqgd * delvgd;
            /* ... other charge deltas */
            
            if (fabs(delqgs) > ckt->CKTreltol * fabs(inst->BSIM2qgs) + ckt->CKTchgTol ||
                fabs(delqgd) > ckt->CKTreltol * fabs(inst->BSIM2qgd) + ckt->CKTchgTol) {
                ckt->CKTnoncon = 1;
                return OK;
            }
        }
    }
    return OK;
}
```

This implementation directly maps to the convergence mathematics:
- Voltage convergence uses relative tolerance `CKTreltol` (typically 0.001) plus absolute voltage tolerance
- Charge convergence uses the same relative tolerance plus charge tolerance `CKTchgTol` (typically 1e-14)
- The capacitance values (`BSIM2cqgs`, `BSIM2cqgd`, etc.) convert voltage changes to charge changes

### 6. Matrix Stamping Implementation

The BSIM2 load function (`BSIM2load()` in `b2ld.c`) stamps the conductance matrix according to the mathematical pattern:

```c
/* Stamp drain equation: Id = gm*Vg + gds*Vd - (gds+gm+gmb)*Vs + gmb*Vb */
SMPaddElt(ckt->CKTmatrix, inst->BSIM2drainDrainPtr, inst->BSIM2drainDrainPtr, gds);
SMPaddElt(ckt->CKTmatrix, inst->BSIM2drainDrainPtr, inst->BSIM2gateDrainPtr, gm);
SMPaddElt(ckt->CKTmatrix, inst->BSIM2drainDrainPtr, inst->BSIM2sourceDrainPtr, -(gds + gm + gmb));
SMPaddElt(ckt->CKTmatrix, inst->BSIM2drainDrainPtr, inst->BSIM2bulkDrainPtr, gmb);

/* Stamp source equation: Is = -gds*Vd - gm*Vg + (gds+gs)*Vs - gmb*Vb */
SMPaddElt(ckt->CKTmatrix, inst->BSIM2sourceSourcePtr, inst->BSIM2drainSourcePtr, -gds);
SMPaddElt(ckt->CKTmatrix, inst->BSIM2sourceSourcePtr, inst->BSIM2gateSourcePtr, -gm);
SMPaddElt(ckt->CKTmatrix, inst->BSIM2sourceSourcePtr, inst->BSIM2sourceSourcePtr, gds + gs);
SMPaddElt(ckt->CKTmatrix, inst->BSIM2sourceSourcePtr, inst->BSIM2bulkSourcePtr, -gmb);

/* Stamp right-hand side with current values */
ckt->CKTrhs[inst->BSIM2dNode] -= inst->BSIM2cd;
ckt->CKTrhs[inst->BSIM2sNode] += inst->BSIM2cd;
```

This C code directly implements the 4×4 conductance matrix mathematics, where each `SMPaddElt()` call adds a conductance value to the sparse matrix at the appropriate row/column intersection.

### 7. Mathematical-to-Code Mapping

The BSIM2 C implementation maintains a direct correspondence with the mathematical formulations:

1. **Threshold Voltage Calculation**:
   - Mathematics: `Vth = VFB + φ + K1·√(φ - Vbs) - K2·(φ - Vbs) - η·Vds + (Δ·ε_si·(φ - Vbs))/(Cox·W_eff)`
   - C Code: Computed in `BSIM2eval()` using `model->BSIM2vfb`, `model->BSIM2phi`, `model->BSIM2k1`, etc.

2. **Mobility Calculation**:
   - Mathematics: `μ_eff = μ0 / [1 + θ·(Vgs - Vth) + θ_b·Vbs]`
   - C Code: `ueff = model->BSIM2mu0 / (1.0 + model->BSIM2theta * vgst + thetab * vbs)`

3. **Drain Current Computation**:
   - Mathematics: Linear and saturation region equations with smoothing
   - C Code: `BSIM2load()` computes region, applies smoothing functions (`exp()`, `tanh()`), and stores result in `inst->BSIM2cd`

4. **Partial Derivatives**:
   - Mathematics: `gm = ∂Id/∂Vgs`, `gds = ∂Id/∂Vds`, `gmb = ∂Id/∂Vbs`
   - C Code: Computed analytically in `BSIM2eval()` and stored in instance structure for matrix stamping

### 8. Linked List Traversal Patterns

The BSIM2 implementation uses consistent linked list traversal patterns:

```c
/* Model list traversal */
for (model = (BSIM2model *)inModel; model != NULL; model = model->BSIM2nextModel) {
    /* Instance list traversal within each model */
    for (inst = model->BSIM2instances; inst != NULL; inst = inst->BSIM2nextInstance) {
        /* Process each instance */
    }
}
```

This pattern appears in every BSIM2 function (`BSIM2load`, `BSIM2convTest`, `BSIM2temp`, etc.), ensuring all instances of all models are processed during each analysis step.

### 9. Error Handling and Return Codes

The implementation uses Ngspice's standard error codes:
- `OK` (0): Successful completion
- `E_NODEV`: Device/instance not found (in deletion functions)
- `E_NOMOD`: Model not found
- `E_BADPARM`: Invalid operation code (in dispatch function)

Each function returns an integer status code, allowing the Ngspice kernel to detect and handle errors appropriately.

### 10. Integration with Ngspice Analysis Framework

The complete BSIM2 implementation integrates with Ngspice through:

1. **Device Registration**: `BSIM2bind()` makes the device available to the simulator
2. **Function Dispatch**: `BSIM2()` routes operations to appropriate implementations
3. **State Management**: State vector indices track charge conservation
4. **Matrix Integration**: Sparse matrix pointers enable efficient Newton-Raphson solving
5. **Convergence Control**: `BSIM2convTest()` provides iteration termination criteria

This architecture ensures the BSIM2 model participates fully in all Ngspice analyses (DC, transient, AC, noise, etc.) while maintaining numerical stability and charge conservation.