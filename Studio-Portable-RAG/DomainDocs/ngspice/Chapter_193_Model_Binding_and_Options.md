# Directive Parsing: Model Binding, Options, and Initial Conditions

_Generated 2026-04-13 16:48 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpdomod.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpdoopt.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpmkmod.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inplkmod.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpkmods.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpdpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpcfix.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2dot.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/include/ngspice/cpextern.h`

# Chapter: Directive Parsing: Model Binding, Options, and Initial Conditions

## Introduction: The Ngspice Dot-Card Parsing Subsystem

The Ngspice dot-card parsing subsystem constitutes the critical interface between human-readable SPICE netlists and the mathematical core of the circuit simulator. This chapter examines the C implementation files that transform textual directives into executable mathematical operations: `inp2dot.c` serves as the finite-state dispatcher routing commands to specialized handlers; `inpdomod.c` and `inpmkmod.c` implement the hash-based model creation and binding system; `inplkmod.c` provides model lookup functionality; `inpdoopt.c` processes solver options that directly modify Newton-Raphson convergence parameters; `inpkmods.c` and `inpdpar.c` handle parameter keyword parsing and device-specific parameter binding; `inpcfix.c` manages complex number handling for AC analysis; and `cpextern.h` declares the critical data structures that bridge the parsing subsystem with the numerical solver. Collectively, these files implement a two-stage mapping: first converting ASCII strings to C data structures through hash tables and offset arithmetic, then binding these structures to the nonlinear device equations that populate the Modified Nodal Analysis (MNA) matrix. The mathematical fidelity of this translation directly determines simulator accuracy, as each parsed parameter becomes a coefficient in the system of equations `F(x) = 0` solved by Newton-Raphson iteration.

## Mathematical Formulation: Model Name to Physical Structure Mapping

The Ngspice dot-card parsing system implements a **two-stage hierarchical mapping** from arbitrary string model names to physical C-struct mathematical models used in SPICE circuit simulation. This mapping directly translates user-defined model names into the internal data structures that govern the device equations solved during circuit analysis.

### Hash Map Data Structure Definition

Let `M` be the universe of all possible model names, where each model name `m ∈ M` is a character string. The system maintains:

1. **Primary Hash Table `H: M → PTR_MODEL`**
   - Hash function: `h(m) = (∑_{i=1}^{n} c_i × 31^{n-i}) mod N` where `c_i` is ASCII value of i-th character
   - Bucket size: `N = 256` (HASHSIZE in implementation)
   - Collision resolution: Separate chaining with linked lists

2. **Model Parameter Structure `MODEL`**
   ```
   MODEL = {
       char *MName;           // Model name string
       int MType;             // Model type enum (NMOS, PMOS, NPN, etc.)
       void *MData;           // Pointer to device-specific structure
       MODEL *MNext;          // Next model in hash chain
       double params[NPARAMS]; // Parameter array
       int flags;             // Status flags
   }
   ```

3. **Device-Specific Structure Mapping to SPICE Equations**
   For a MOSFET model "mymos", the binding creates:
   ```
   SPICEmodel = {
       GENmodel;              // Generic model header
       MOSmodel;              // MOSFET-specific parameters:
       double VTO;            // Threshold voltage (appears in Ids equations)
       double KP;             // Transconductance (K' in Ids = KP/2·(W/L)·(Vgs-VTO)²)
       double LAMBDA;         // Channel-length modulation (Ids = Ids0·(1+λVds))
       double GAMMA;          // Bulk threshold parameter (VTO = VTO0 + γ(√|2φF+Vsb|-√|2φF|))
       ...
   }
   ```

The complete mathematical mapping for SPICE simulation is:
`parse(".model mymos nmos VTO=0.7 KP=100u") → H("mymos") → MODEL → SPICEmodel → Device equations inserted into Newton-Raphson formulation`

### Physical Memory Layout and Parameter Binding

The actual binding occurs through pointer arithmetic:
```
address(MODEL.MData) = address(SPICEmodel) 
                     = malloc(sizeof(SPICEmodel))
```

The parameter array indexing follows SPICE's device equation requirements:
```
params[i] = *(base_address + offset_i)
```
where `offset_i` is determined by the device model's parameter table. For example, in MOSFETs:
- `VTO` offset maps to threshold voltage in the drain current equation
- `KP` offset maps to transconductance in `Ids = (KP/2)·(W/L)·(Vgs-VTO)²·(1+λVds)`
- `LAMBDA` offset maps to channel-length modulation factor

The C implementation uses a three-tier lookup system:
```c
/* Tier 1: Hash table declaration */
#define HASHSIZE 256
static MODEL *modeltab[HASHSIZE];

/* Hash function implementation */
unsigned hash(char *s) {
    unsigned hashval = 0;
    for (; *s; s++)
        hashval = *s + 31 * hashval;
    return hashval % HASHSIZE;
}

/* Parameter binding mathematics */
void setparam(MODEL *mp, char *param, double value) {
    int idx = find_param_index(param);
    if (idx >= 0) {
        double *param_ptr = (double *)((char *)mp->MData + param_table[idx].offset);
        *param_ptr = value;  // Directly modifies device equation coefficients
    }
}
```

### Dot-Card Dispatcher Finite-State Parser

The command parser implements function table lookup for SPICE directives:
```c
struct dotcmd {
    char *name;           // ".model", ".options", ".ic", ".nodeset"
    int (*func)(void);    // Handler function pointer
    int minargs;          // Minimum arguments
    int maxargs;          // Maximum arguments
};

static struct dotcmd dotcmds[] = {
    {".model",  domodel,  2, MAXARGS},
    {".options",dooption, 1, MAXARGS},
    {".ic",     doic,     2, MAXARGS},      // Initial conditions
    {".nodeset",donodeset,2, MAXARGS},      // Node voltage hints
    {NULL, NULL, 0, 0}
};
```

## Convergence Analysis: Option Overrides and Solver Limits

The parsed `.options` directives modify global convergence parameters that directly affect the Newton-Raphson iteration used to solve the nonlinear circuit equations in SPICE.

### Newton-Raphson Iteration Formulation for Circuit Equations

Given the system of nonlinear circuit equations `F(x) = 0`, where `x ∈ ℝⁿ` is the node voltage vector (and branch currents for MNA formulation):

1. **Iteration update**: `x_{k+1} = x_k - J(x_k)^{-1}F(x_k)`
   where `J(x)` is the Jacobian matrix `∂F/∂x` containing conductances and transconductances

2. **SPICE Convergence criteria**:
   ```
   |x_{k+1} - x_k| < ε_a + ε_r × max(|x_k|, |x_{k+1}|)
   ```
   where:
   - `ε_a = VNTOL` (absolute voltage tolerance, typically 1μV)
   - `ε_r = RELTOL` (relative tolerance, default 0.001)

### Global Parameter Override Mechanism and Solver Impact

Parsed options modify solver limits through global variables that directly alter the Newton-Raphson iteration:

#### RELTOL (Relative Tolerance)
```
RELTOL = parsed_value;  // Default: 0.001 (0.1%)
```
Mathematical effect on SPICE convergence test:
```
converged = |ΔV| < VNTOL + RELTOL × max(|V_old|, |V_new|)
```
This provides scale-invariant convergence for circuits with voltages ranging from μV to kV.

#### GMIN (Minimum Conductance) - Matrix Regularization
```
CKTgmin = parsed_value;  // Default: 1e-12
```
Jacobian modification: Adds `GMIN` to diagonal entries of the Modified Nodal Analysis (MNA) matrix:
```
J[i,i] = J[i,i] + GMIN
```
This ensures matrix non-singularity: `det(J + GMIN·I) ≠ 0` even for disconnected nodes. The modified Newton iteration becomes:
```
Solve: (J(x_k) + GMIN·I)·Δx = -F(x_k)
```
In SPICE, this corresponds to adding a small resistor (1/GMIN) between every node and ground.

#### ITL1 (DC Iteration Limit)
```
CKTmaxIter = parsed_value;  // Default: 100
```
Termination condition in SPICE's Newton loop:
```
if (iteration > ITL1) then 
    convergence_failed = TRUE
    trigger_alternative_method (source stepping, pseudo-transient)
```

### Sparse Matrix Solver Impact in SPICE

The modified Newton iteration with option overrides becomes:

```
Solve: (J(x_k) + GMIN·I)·Δx = -F(x_k)
```

Where the sparse matrix `J` has structure dictated by circuit topology (non-zero pattern from device connections). The SPICE convergence loop:

```
for k = 1 to ITL1:
    build_J(F, x_k, GMIN)    // Assemble Jacobian with GMIN added to diagonals
    factor(J)                // LU factorization of sparse matrix
    solve(J, Δx)            // Solve linear system via sparse LU back substitution
    x_{k+1} = x_k + Δx
    if ||Δx|| < ε(RELTOL, VNTOL):  // Using parsed tolerance values
        converged = TRUE
        break
```

### Options Processing Implementation

The options parser directly modifies global solver state variables that control SPICE convergence:

```c
/* Global convergence parameters in SPICE */
extern double CKTcurTask->TSKreltol;    // RELTOL
extern double CKTcurTask->TSKabstol;    // ABSTOL (current tolerance)
extern double CKTcurTask->TSKchgtol;    // CHGTOL (charge tolerance)
extern double CKTcurTask->TSKgmin;      // GMIN
extern int    CKTcurTask->TSKitl1;      // ITL1 (DC iteration limit)
extern int    CKTcurTask->TSKitl2;      // ITL2 (Gmin stepping iterations)
extern int    CKTcurTask->TSKitl4;      // ITL4 (transient iteration limit)

/* Option processing function */
int dooption(CKTcircuit *ckt, wordlist *wl) {
    char *optname = wl->word;
    char *optvalue = wl->next->word;
    double val = atof(optvalue);
    
    if (strcasecmp(optname, "RELTOL") == 0) {
        if (val > 0.0 && val < 1.0) {
            CKTcurTask->TSKreltol = val;
            ckt->CKTreltol = val;  // Mirror for backward compatibility
        }
    }
    else if (strcasecmp(optname, "GMIN") == 0) {
        if (val > 0.0) {
            CKTcurTask->TSKgmin = val;
            ckt->CKTgmin = val;
            /* Update all device instances in SPICE */
            update_all_devices_gmin(ckt, val);
        }
    }
    else if (strcasecmp(optname, "ITL1") == 0) {
        int ival = atoi(optvalue);
        if (ival > 0) {
            CKTcurTask->TSKitl1 = ival;
        }
    }
    /* ... process other SPICE options ... */
    
    return OK;
}
```

### Mathematical Propagation of Option Overrides

When GMIN is set to `g`:
- Every MNA matrix diagonal entry `J[i,i]` becomes `J[i,i] + g`
- For MOSFETs, additional conductance `g` is added between drain-source terminals
- The modified Newton iteration: `(J + g·I)·Δx = -F(x)` ensures numerical stability

Critical memory mappings in SPICE:
1. `CKTcurTask->TSKreltol` → `ckt->CKTsolver->reltol` → used in `convergence_test()`
2. `CKTcurTask->TSKgmin` → `ckt->CKTgmin` → added to diagonal in `load_matrix()`
3. `CKTcurTask->TSKitl1` → checked in `NewtonIterate()` loop counter

### Convergence Guarantees in SPICE Context

The algorithm provides convergence through these mathematically grounded mechanisms:

1. **Regularization**: GMIN ensures `J + εI` is positive definite, guaranteeing solvability
2. **Adaptive tolerance**: RELTOL provides scale-invariant convergence for mixed-signal circuits
3. **Iteration limits**: ITL1 prevents infinite loops in pathological circuits
4. **Fallback mechanisms**: Source stepping, pseudo-transient when DC Newton fails

The mathematical guarantee for SPICE: For sufficiently small RELTOL, sufficient GMIN > 0, and assuming continuous differentiable device models (MOSFET, BJT, diode equations), the Newton-Raphson iteration converges quadratically in the neighborhood of the solution, with convergence radius determined by the device model Lipschitz constants.

## C Implementation: Dot-Card Parsing and Mathematical Binding

### Dot-Card Dispatcher Finite-State Parser (inp2dot.c)

The dispatcher implements a **finite-state command parser** that maps SPICE directive strings to mathematical handler functions through a static function table:

```c
/* Command dispatch table structure - maps strings to mathematical operations */
struct dotcmd {
    char *name;           // ".model", ".options", ".ic", ".nodeset"
    int (*func)(void);    // Handler function pointer implementing mathematical operations
    int minargs;          // Minimum arguments required
    int maxargs;          // Maximum arguments allowed (typically 50)
};

/* Global dispatch table - static initialization */
static struct dotcmd dotcmds[] = {
    {".model",  domodel,  2, MAXARGS},    // Maps to model creation and parameter binding
    {".options",dooption, 1, MAXARGS},    // Maps to convergence parameter modification
    {".ic",     doic,     2, MAXARGS},    // Maps to initial condition vector setup
    {".nodeset",donodeset,2, MAXARGS},    // Maps to Newton-Raphson starting point
    {NULL, NULL, 0, 0}                    // Sentinel
};

/* Main dispatch function - mathematical operation router */
int INP2D(CKTcircuit *ckt, char *line) {
    char *command = getfirst(word);  // Tokenize input line
    for (struct dotcmd *dc = dotcmds; dc->name; dc++) {
        if (strcmp(command, dc->name) == 0) {
            return (*dc->func)(ckt, word);  // Execute mathematical handler
        }
    }
    return E_NOTFOUND;
}
```

**Mathematical Mapping**: The dispatcher implements the function `D: S → F` where `S` is the set of SPICE directive strings and `F` is the set of mathematical handler functions that modify circuit equations or solver parameters.

### Model Parameter Hashing and Mathematical Binding (inpmkmod.c / inplkmod.c)

#### Hash Table Implementation for Model Name Mapping

The system implements the hash function `h(m) = (∑ c_i × 31^{n-i}) mod 256` as:

```c
/* Tier 1: Hash table declaration - implements H: M → PTR_MODEL */
#define HASHSIZE 256  // N in mathematical formulation
static MODEL *modeltab[HASHSIZE];  // Hash table array

/* Hash function implementation - mathematical string to integer mapping */
unsigned hash(char *s) {
    unsigned hashval = 0;
    for (; *s; s++)
        hashval = *s + 31 * hashval;  // ∑ c_i × 31^{n-i}
    return hashval % HASHSIZE;        // mod N
}
```

#### Model Lookup with Hash Chaining

```c
/* Model lookup - implements mathematical mapping H(m) */
MODEL *findmodel(char *name) {
    MODEL *mp;
    /* Traverse collision chain: O(1) average, O(n) worst-case */
    for (mp = modeltab[hash(name)]; mp != NULL; mp = mp->MNext) {
        if (strcmp(name, mp->MName) == 0)
            return mp;  // Found: returns pointer to mathematical model structure
    }
    return NULL;  // Not found
}
```

#### Model Creation and Mathematical Structure Binding

```c
/* Model creation - allocates and binds mathematical structures */
MODEL *makemodel(char *name, int type) {
    unsigned hashval = hash(name);
    MODEL *mp = (MODEL *)malloc(sizeof(MODEL));
    
    /* String to structure binding */
    mp->MName = strdup(name);      // Store model name string
    mp->MType = type;              // Set mathematical model type (NMOS, PMOS, etc.)
    mp->MNext = modeltab[hashval]; // Insert at head of collision chain
    modeltab[hashval] = mp;        // Update hash table
    
    /* Allocate device-specific mathematical structure */
    switch(type) {
        case NMOS:
            mp->MData = (void *)malloc(sizeof(MOSmodel));
            bind_mos_params((MOSmodel *)mp->MData);  // Initialize MOSFET equations
            break;
        case NPN:
            mp->MData = (void *)malloc(sizeof(BJTmodel));
            bind_bjt_params((BJTmodel *)mp->MData);  // Initialize BJT equations
            break;
        /* Other device types: diode, resistor, capacitor, etc. */
    }
    return mp;
}
```

#### Parameter Binding to Mathematical Model Offsets

The parameter binding implements the mathematical mapping `params[i] = *(base_address + offset_i)`:

```c
/* Parameter table for MOSFET - defines offsets into mathematical structure */
param_table[] = {
    {"VTO", offsetof(MOSmodel, VTO), ...},    // Threshold voltage offset
    {"KP", offsetof(MOSmodel, KP), ...},      // Transconductance offset
    {"LAMBDA", offsetof(MOSmodel, LAMBDA), ...}, // Channel-length modulation
    {"GAMMA", offsetof(MOSmodel, GAMMA), ...}, // Bulk threshold parameter
    /* ... other MOSFET parameters ... */
};

/* Parameter assignment - modifies mathematical model coefficients */
void setparam(MODEL *mp, char *param, double value) {
    int idx = find_param_index(param);  // Lookup parameter in table
    if (idx >= 0) {
        /* Calculate address: base + offset */
        double *param_ptr = (double *)((char *)mp->MData + param_table[idx].offset);
        *param_ptr = value;  // Direct modification of equation coefficient
    }
}
```

**Mathematical Significance**: Each parameter assignment directly modifies coefficients in device equations. For example, setting `VTO` changes the threshold voltage in the MOSFET drain current equation: `Ids ∝ (Vgs - VTO)²`.

### Simulator Options Processing - Mathematical Parameter Override (inpdoopt.c)

The options parser implements the global parameter override mechanism that modifies Newton-Raphson convergence:

```c
/* Global convergence parameters - mathematical solver state */
extern double CKTcurTask->TSKreltol;    // ε_r in convergence test
extern double CKTcurTask->TSKabstol;    // Absolute current tolerance
extern double CKTcurTask->TSKchgtol;    // Charge tolerance
extern double CKTcurTask->TSKgmin;      // g in J + gI regularization
extern int    CKTcurTask->TSKitl1;      // k_max in Newton iteration loop
extern int    CKTcurTask->TSKitl2;      // Gmin stepping iterations
extern int    CKTcurTask->TSKitl4;      // Transient iteration limit

/* Option processing function - modifies mathematical solver parameters */
int dooption(CKTcircuit *ckt, wordlist *wl) {
    char *optname = wl->word;
    char *optvalue = wl->next->word;
    double val = atof(optvalue);
    
    /* Case-insensitive option matching and validation */
    if (strcasecmp(optname, "RELTOL") == 0) {
        /* Modify convergence criterion: |Δx| < ε_a + ε_r × max(|x_k|, |x_{k+1}|) */
        if (val > 0.0 && val < 1.0) {
            CKTcurTask->TSKreltol = val;  // Set ε_r
            ckt->CKTreltol = val;         // Backward compatibility
        }
    }
    else if (strcasecmp(optname, "GMIN") == 0) {
        /* Modify matrix regularization: J → J + gI */
        if (val > 0.0) {
            CKTcurTask->TSKgmin = val;    // Set g
            ckt->CKTgmin = val;           // Update circuit context
            update_all_devices_gmin(ckt, val);  // Propagate to device equations
        }
    }
    else if (strcasecmp(optname, "ITL1") == 0) {
        /* Modify iteration limit: k_max in Newton loop */
        int ival = atoi(optvalue);
        if (ival > 0) {
            CKTcurTask->TSKitl1 = ival;  // Set maximum iterations
        }
    }
    /* Process other mathematical parameters: ABSTOL, VNTOL, PIVREL, etc. */
    
    return OK;
}
```

#### Critical Memory Mappings for Mathematical Propagation

The C implementation maintains these critical mappings between parsed values and mathematical operations:

1. **Convergence Tolerance Propagation**:
   ```
   CKTcurTask->TSKreltol → ckt->CKTsolver->reltol → used in convergence_test()
   ```
   Mathematical effect: Changes the convergence test to `|ΔV| < VNTOL + RELTOL × max(|V_old|, |V_new|)`

2. **Matrix Regularization Propagation**:
   ```
   CKTcurTask->TSKgmin → ckt->CKTgmin → added to diagonal in load_matrix()
   ```
   Mathematical effect: Modifies Jacobian to `J[i,i] = J[i,i] + GMIN` ensuring `det(J + GMIN·I) ≠ 0`

3. **Iteration Limit Propagation**:
   ```
   CKTcurTask->TSKitl1 → checked in NewtonIterate() loop counter
   ```
   Mathematical effect: Implements termination condition `if (iteration > ITL1) then convergence_failed = TRUE`

### Initial Conditions and Node Setting Implementation

```c
/* Initial conditions handler - sets x_0 in Newton iteration */
int doic(CKTcircuit *ckt, wordlist *wl) {
    char *node = wl->word;
    char *value_str = wl->next->word;
    double value = atof(value_str);
    
    /* Find node index in MNA matrix */
    int node_index = find_node_index(ckt, node);
    if (node_index >= 0) {
        /* Set initial voltage in solution vector */
        ckt->CKTrhsOld[node_index] = value;
        ckt->CKTrhs[node_index] = value;
        /* Mark node for initial condition treatment */
        set_ic_flag(ckt, node_index);
    }
    return OK;
}

/* Nodeset handler - provides starting point x_0 for Newton */
int donodeset(CKTcircuit *ckt, wordlist *wl) {
    char *node = wl->word;
    char *value_str = wl->next->word;
    double value = atof(value_str);
    
    int node_index = find_node_index(ckt, node);
    if (node_index >= 0) {
        /* Set initial guess for Newton-Raphson */
        ckt->CKTrhs[node_index] = value;
        /* Nodeset provides hint but doesn't force like .IC */
        set_nodeset_flag(ckt, node_index);
    }
    return OK;
}
```

**Mathematical Significance**: 
- `.IC` commands set `x_0` in the Newton iteration and may be enforced as constraints
- `.NODESET` commands provide initial guesses `x_0` to improve convergence but don't constrain the solution

### C to Mathematics Correspondence Table

| C Implementation | Mathematical Operation | Effect on Newton-Raphson |
|-----------------|------------------------|---------------------------|
| `hash(name)` | `h(m) = (∑ c_i × 31^{n-i}) mod 256` | Maps model names to equation structures |
| `setparam(mp, "VTO", 0.7)` | `VTO = 0.7` in `Ids = f(Vgs, VTO, KP, ...)` | Modifies MOSFET drain current equation |
| `CKTcurTask->TSKreltol = val` | Sets `ε_r` in `|Δx| < ε_a + ε_r·max(|x|)` | Changes convergence criterion |
| `CKTcurTask->TSKgmin = val` | Adds `gI` to Jacobian: `J → J + gI` | Regularizes matrix for numerical stability |
| `CKTcurTask->TSKitl1 = ival` | Sets `k_max` in `for k=1 to k_max` | Limits Newton iteration attempts |
| `doic()` | Sets `x_0` in `x_{k+1} = x_k - J^{-1}F(x_k)` | Provides initial condition vector |
| `donodeset()` | Provides `x_0` guess | Improves convergence starting point |

This C implementation directly implements the mathematical formulations described in the previous sections, with each function and data structure corresponding to a specific mathematical operation in the SPICE circuit simulation algorithm. The parsing subsystem thus serves as the essential translator between human-authored netlists and the numerical machinery that solves the circuit equations, with mathematical correctness enforced at every stage of the translation pipeline.