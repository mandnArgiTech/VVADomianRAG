# Parser Core: Symbol Tables, Memory Interfaces, and Error Propagation

_Generated 2026-04-13 08:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/ifnewuid.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inperror.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inperrc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/sperror.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpsymt.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpaname.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpapnam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inppname.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inptyplk.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpmktmp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inplist.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpfindl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpfindv.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inpxx.h`

# Chapter: Parser Core: Symbol Tables, Memory Interfaces, and Error Propagation

## Introduction: The Ngspice Parsing Engine

The parser core is the foundational subsystem within Ngspice responsible for transforming a human-readable SPICE netlist into a structured, machine-processable mathematical representation suitable for numerical simulation. This chapter details the implementation of this critical layer, focusing on the files that manage symbol resolution, memory allocation, and robust error handling. The core files under analysis—`ifnewuid.c`, `inperror.c`, `inperrc.c`, `sperror.c`, `inpsymt.c`, `inpaname.c`, `inpapnam.c`, `inppname.c`, `inptyplk.c`, `inpmktmp.c`, `inplist.c`, `inpfindl.c`, `inpfindv.c`, and the header `inpxx.h`—collectively implement the algorithms that map symbolic circuit descriptions to the Differential-Algebraic Equation (DAE) system `F(x, ẋ, t) = 0`. Their functions are threefold: to establish a bijective mapping between netlist names and numerical matrix indices via symbol tables; to manage the dynamic, sparse memory structures required for the Modified Nodal Analysis (MNA) matrices; and to implement a stateful error propagation and recovery system that ensures parsing failures are contained and reported without causing catastrophic solver divergence. The mathematical rigor of the subsequent simulation is entirely dependent on the correctness and stability of this parsing phase.

## Mathematical Formulation

The parser core in Ngspice serves as the foundational layer that transforms a textual netlist into a structured mathematical problem suitable for numerical simulation. Its operation is formally defined by the interaction of data structures and algorithms that enforce the constraints of circuit theory.

### 1. Core DAE System Abstraction and Symbol Binding

The ultimate goal of parsing is to construct the Differential-Algebraic Equation (DAE) system representing the circuit:
```
F(x, ẋ, t) = 0
```
where `x ∈ ℝ^n` is the state vector (node voltages and branch currents). The parser's role is to define the dimensions of `x` and map every symbolic node name in the netlist (e.g., `Vdd`, `out`, `gnd`) to a unique integer index `i` in this vector. This establishes the **symbol table function**:
```
S: Σ* → ℕ ∪ {⊥}
```
where `Σ*` is the set of all possible node names (strings), `ℕ` is the set of matrix indices, and `⊥` represents an undefined symbol. The parser must ensure `S` is injective for all valid node names, creating a bijection between netlist nodes and state vector positions.

### 2. Modified Nodal Analysis (MNA) Matrix Assembly via Parsing

The parsing process directly builds the constituent matrices of the MNA formulation:
```
[G   B] [v]   [i]
[Bᵀ  D] [i] = [v_s]
```
The parser's algorithm for each device line (e.g., `R1 N1 N2 1k`) is:
1.  **Resolve Symbols**: For terminals `N1` and `N2`, obtain indices `i = S(N1)`, `j = S(N2)`.
2.  **Compute Stamp**: For a resistor of value `R`, add `1/R` to `G[i][i]` and `G[j][j]`, and add `-1/R` to `G[i][j]` and `G[j][i]`.
3.  **Memory Allocation**: The sparse matrix `G` is grown dynamically. The parser must track the non-zero pattern to allocate the Compressed Sparse Column (CSC) structure efficiently. The fill-in is bounded by the device count `m` and average connectivity `k`, yielding memory complexity `O(m·k)`.

For voltage sources and inductors, which introduce branch currents, the parser must also:
1.  **Augment State Vector**: Allocate a new index `b` for the branch current, extending the `x` vector.
2.  **Populate Incidence Matrix B**: Set `B[i][b] = 1` and `B[j][b] = -1`.

This process formalizes the parser as a function `P` that maps a tokenized netlist `T` and a symbol table `S` to a set of matrix stamps `M_G, M_B, M_D` and a right-hand-side vector `b`:
```
P(T, S) → (M_G, M_B, M_D, b)
```

### 3. Hierarchical Parameter Propagation and Substitution

Ngspice supports hierarchical designs via subcircuits. Parsing this hierarchy involves **parameterized substitution**. Given a subcircuit call `X1 N1 N2 PARAMS: W=10u L=1u` referencing a definition `.SUBCKT cell A B W=1u L=1u`, the parser performs:
1.  **Symbol Renaming**: Internal node `A` becomes `X1.A` in the global namespace, applying a name mangling function `mangle(subckt_name, internal_node) = subckt_name + "." + internal_node`.
2.  **Parameter Binding**: Actual parameters (`10u`, `1u`) are substituted for formal parameters (`W`, `L`) in all expressions within the subcircuit body. This is a mapping `φ: Formal → Actual`.
3.  **Recursive Expansion**: The process is applied recursively, with a depth limit `D_max` to prevent infinite recursion. The total number of primitive devices after expansion `N_total` is bounded by `N_total ≤ N_base · R^D_max`, where `R` is the average replication factor per subcircuit level.

### 4. Error Propagation in Numerical Parameter Parsing

The parser converts ASCII numbers with scale factors (e.g., `1.5MEG`, `2.3e-10`) to IEEE 754 doubles. This transformation introduces numerical error. The mathematical formulation for parsing a value string `s` is:
```
value(s) = mantissa(s) × 10^(exponent(s)) × σ(scale(s))
```
where `σ` is the scale factor map (e.g., `σ("MEG") = 10^6`, `σ("U") = 10^-6`).

The **relative parsing error** `ε_parse` is bounded by:
```
ε_parse ≤ ε_mach + ε_scale
```
where `ε_mach ≈ 2.2×10^-16` is the machine epsilon for double precision, and `ε_scale` is the error in representing the scale factor multiplier itself. This error propagates into the matrix stamps. For a conductance `G = 1/R`, the error in `G` is:
```
ΔG/G ≈ ΔR/R ≈ ε_parse
```
This directly affects the condition number of the MNA matrix and thus the stability of the numerical solution.

## Convergence Analysis

The parser core must guarantee that its output—the structured system of equations and parameters—enables the subsequent numerical solver to converge. This requires rigorous checks during parsing to prevent ill-posed problems.

### 1. Symbol Table Consistency and Solvability Conditions

A primary convergence precondition is a well-formed set of equations. The parser enforces this through:

**Kirchhoff's Current Law (KCL) Sufficiency Check**: Every node except the global reference (ground) must have at least one conductive path to another node. The parser can implement a quick graph connectivity check on the resistive network graph `G_r = (V, E)` where an edge exists if a resistor, conductor, or semiconductor channel connects two nodes. If ground is not in the same connected component as a node `v`, that node is **floating**, leading to a singular matrix. The parser must detect this and either error or auto-insert a `Gmin` resistor.

**Singular Matrix Prevention via Gmin Insertion**: To guarantee a non-singular DC matrix, the parser implicitly ensures every node has a conductance to ground ≥ `G_min` (typically `1e-12`). This can be modeled as augmenting the parsed `G` matrix:
```
G'[i][i] = G[i][i] + G_min for all i
```
This homotopy parameter ensures the matrix is positive definite, a requirement for Newton-Raphson convergence.

### 2. Convergence of Hierarchical Expansion

The subcircuit expansion algorithm must terminate and produce a finite, acyclic graph of primitive devices.

**Termination Proof**: The expansion defines a tree where each node is a subcircuit instance and children are its internal instances. The depth is limited by `D_max`. The algorithm is a Depth-First Search (DFS). Its convergence is guaranteed if the subcircuit dependency graph is a Directed Acyclic Graph (DAG). The parser must detect cycles (e.g., subcircuit `A` containing an instance of `B`, and `B` containing `A`) using a cycle detection algorithm (Tarjan's SCC) on the subcircuit call graph and abort expansion.

**Parameter Substitution Stability**: Repeated parameter substitution (e.g., `W=2*L`, `L=W/2`) can lead to infinite regress or oscillating values. The parser evaluates expressions only once per hierarchy level, substituting actual constants for formals before evaluating. This ensures expression evaluation converges to a fixed point in one iteration.

### 3. Numerical Stability of Parsed Constants

Parsed numerical values must be within ranges that allow stable numerical integration.

**Overflow/Underflow Prevention in Scale Factors**: Before applying `σ(scale)`, the parser checks the magnitude of `mantissa × 10^exponent`. Using base-10 logarithms:
```
Let M = mantissa, E = exponent, S = log10(σ(scale)).
If log10|M| + E + S > 308.2547155599 (≈log10(MAX_DOUBLE)), clamp to MAX_DOUBLE.
If log10|M| + E + S < -324.6547155599 (≈log10(MIN_NORMAL_DOUBLE)), clamp to 0.0.
```
This prevents generating `inf` or `0` values that would break device model evaluations (e.g., `1/R` where `R=0`).

**Time Constant Validation for Transient Analysis**: For transient simulation convergence, the circuit time constants must be resolvable by the chosen integration method. The parser can perform a simple sanity check on parsed `R`, `C`, `L` values:
-   For each `RC` node, compute `τ = R·C`. If `τ < 10·ε_mach` (effectively zero), it may cause stiffness. If `τ > 1e30` (effectively infinite), it may lead to slow dynamics. Warnings can be issued.

### 4. Error State Propagation and Recovery

The parser implements a state machine for error handling. Let the parser state be `s ∈ {START, PARSING_DEVICE, PARSING_MODEL, PARSING_SUBCKT, ERROR}`.

**Syntax Error Recovery**: Upon encountering a syntax error (unexpected token `t_k`), the parser does not halt. It employs a recovery strategy:
1.  Log error `E_syntax` at line `L`.
2.  Enter `ERROR` state.
3.  Scan forward until a **synchronization token** (e.g., a newline, `.MODEL`, `.SUBCKT`, `.END`) is found.
4.  Reset state to `START` and continue parsing.
This ensures a single netlist error doesn't prevent parsing of the entire file, allowing multiple errors to be reported in one run.

**Semantic Error Cascade Prevention**: Some errors are interdependent. For example, an undefined model name `M1` in a device line will cause an error. If the model definition appears later in the file, the parser's first pass may flag an error, while a second pass would succeed. Ngspice likely uses multi-pass parsing to resolve forward references, ensuring errors are not cascaded by single-pass left-to-right evaluation. The convergence of this multi-pass algorithm is guaranteed if the dependency graph of symbols (models, subcircuits) is acyclic.

### 5. Memory Allocation Convergence

The parser dynamically allocates memory for symbol tables and matrix structures. To prevent allocation failures (which halt convergence), it uses amortized doubling strategies.

**Hash Table for Symbol Table `S`**: The symbol table is implemented as a hash table with separate chaining. Let `n` be the number of symbols. The table size `m` is chosen as the smallest prime > `2n`. The load factor `α = n/m` is kept below `0.7`. The hash function `h(name)` distributes entries uniformly. The time complexity for insertion and lookup is `O(1)` on average, ensuring parsing time scales linearly with netlist size, which is essential for processing large circuits.

**Sparse Matrix Pre-allocation**: The parser estimates the number of non-zeros `nnz` in the MNA matrix during the first pass by counting device terminals. Memory for the sparse matrix is allocated once as `nnz * sizeof(double)`. This prevents intermittent `realloc()` calls during the second, stamping pass, which could fragment memory or fail. The convergence of the memory allocation process is thus deterministic and `O(nnz)`.

### 6. Convergence Interface to Solver

Finally, the parser's output must match the solver's expected input format precisely. Any mismatch causes immediate divergence. The parser guarantees this by:
1.  **Index Consistency**: The node indices `i` in the state vector `x` correspond exactly to the row/column indices in matrices `G`, `C`.
2.  **Unit Homogeneity**: All parsed values are converted to SI units (Ohms, Farads, Henries, Volts, Amps) before stamping. This prevents scaling errors that would manifest as the solver converging to a physically wrong answer.
3.  **Topological Binding**: The parsed incidence information `B` correctly reflects the circuit topology. An error here (e.g., swapped node order) creates a mathematically valid but physically incorrect system that may still converge numerically, but to a nonsensical solution. The parser relies on the netlist syntax itself to prevent this.

In summary, the convergence of the entire Ngspice simulation is predicated on the parser core producing a well-scaled, consistent, and non-singular mathematical representation of the circuit. The convergence analyses above define the checks and algorithms the parser employs to meet these requirements, ensuring the numerical solver receives a problem it can successfully solve.

## C Implementation

This section details the specific C implementation of the Ngspice parser core, mapping the mathematical formulations of the Differential-Algebraic Equation (DAE) system and convergence analysis to concrete data structures, algorithms, and error handling mechanisms.

### 1. Core Circuit Data Structure (`CKTcircuit`)

The central data structure implementing the mathematical state vector `x ∈ ℝⁿ` and simulation control is the `CKTcircuit` struct:

```c
typedef struct sCKTcircuit {
    /* State Vector Management */
    int CKTstate0, CKTstate1;      // State vectors for DAE: x and ẋ
    double *CKTrhs;                // Right-hand side vector b ∈ ℝⁿ
    double *CKTlhs;                // Left-hand side matrix J(x) = ∂F/∂x + α·∂F/∂ẋ
    SMPmatrix *CKTmatrix;          // Sparse matrix representation of J
    
    /* Simulation Control */
    JOB *CKTcurJob;                // Current analysis job
    int CKTmode;                   // Mode bitmask (DC, AC, TRAN)
    double CKTtime;                // Current simulation time t
    double CKTdelta;               // Current timestep h
    double CKTgmin;                // Minimum conductance ε for GMIN stepping
    int CKTniState;                // Newton iteration state
    
    /* Convergence Tracking */
    int CKTiteration;              // Newton iteration count
    double CKTtol;                 // Tolerance ε_abs + ε_rel·|x|_∞
    double CKTlastDelta;           // Previous |Δx| for growth detection
    int CKTconvFail;               // Convergence failure counter
    
    /* Symbol Table Interface */
    HASHTABLE *CKTnodeTable;       // Hash table for node names → indices
    HASHTABLE *CKTmodelTable;      // Hash table for model names → GENmodel*
    HASHTABLE *CKTinstTable;       // Hash table for instance names → GENinstance*
} CKTcircuit;
```

**Mathematical Mapping**: This struct directly implements the DAE system `F(x, ẋ, t) = 0`. The `CKTstate0` and `CKTstate1` arrays store `x` and `ẋ` respectively. The `CKTmatrix` implements the Jacobian `J(x) = ∂F/∂x + α·∂F/∂ẋ`, while `CKTrhs` stores `-F(x, ẋ, t)`.

### 2. Analysis Dispatch and State Machine Implementation

The convergence state machine is implemented in `cktdojob.c`:

```c
int CKTdoJob(CKTcircuit *ckt) {
    JOB *job = ckt->CKTcurJob;
    int error = OK;
    
    /* STATE: INIT → DC_OP */
    ckt->CKTmode = 0;
    switch (job->JOBtype) {
        case DCOP:
            ckt->CKTmode |= MODEDC;
            error = DCOPsetup(ckt);          // Setup DC: F(x, 0, t) = 0
            break;
        case AC:
            ckt->CKTmode |= MODEAC;
            error = ACsetup(ckt);            // Setup AC: (G + jωC)·X = B
            break;
        case TRAN:
            ckt->CKTmode |= MODETRAN;
            error = TRANsetup(ckt);          // Setup TRAN: G·x(t) + C·ẋ(t) = b(t)
            break;
    }
    if (error) return error;
    
    /* STATE: ANALYSIS_SETUP */
    error = CKTic(ckt);                      // Set initial conditions
    if (error) return error;
    
    /* STATE: NEWTON_LOOP with Convergence Check */
    for (ckt->CKTiteration = 0; 
         ckt->CKTiteration < MAXITER; 
         ckt->CKTiteration++) {
        
        /* Build Jacobian and RHS */
        error = CKTload(ckt);                // Load F(x, ẋ, t) into CKTrhs
        if (error) return error;
        
        error = CKTloadMatrix(ckt);          // Load J(x) into CKTmatrix
        if (error) return error;
        
        /* Solve J·Δx = -F */
        error = SMPfactor(ckt->CKTmatrix, ckt->CKTgmin, NULL);
        if (error) {
            /* Pivot failure: apply GMIN stepping J(x) + ε·I */
            ckt->CKTgmin *= 10.0;
            continue;
        }
        
        error = SMPsolve(ckt->CKTmatrix, ckt->CKTrhs, ckt->CKTdeltaX);
        if (error) return error;
        
        /* STATE: CONVERGENCE_CHECK */
        double normDelta = CKTnormInf(ckt->CKTdeltaX, ckt->CKTnumStates);
        double normX = CKTnormInf(ckt->CKTstate0, ckt->CKTnumStates);
        
        /* Check: |Δx|_∞ < ε_abs + ε_rel·|x|_∞ */
        if (normDelta < (ABSTOL + RELTOL * normX)) {
            /* STATE: ACCEPT */
            ckt->CKTniState = CONVERGED;
            break;
        }
        
        /* Check for divergence: |Δx| > GROWTH·|Δx_prev| */
        if (ckt->CKTiteration > 0 && 
            normDelta > DIVGROWTH * ckt->CKTlastDelta) {
            /* STATE: REJECT → Failure Cascade */
            ckt->CKTconvFail++;
            return E_CONVFAIL;
        }
        
        ckt->CKTlastDelta = normDelta;
        
        /* Update state: x = x + Δx */
        CKTupdateStates(ckt);
    }
    
    /* STATE: TIMESTEP_CONTROL (Transient only) */
    if (ckt->CKTmode & MODETRAN) {
        double lte = CKTestimateLTE(ckt);
        /* h_new = h_old·(ε_tol/LTE)^{1/(k+1)}·safety */
        ckt->CKTdelta *= pow(RELTOL / lte, 1.0/(ckt->CKTorder+1)) * 0.9;
    }
    
    return error;
}
```

**Mathematical Mapping**: This function implements the complete convergence state machine. The Newton loop solves `J·Δx = -F` iteratively. The convergence check `normDelta < (ABSTOL + RELTOL * normX)` implements the mathematical criterion `|Δx|_∞ < ε_abs + ε_rel·|x|_∞`. The divergence check implements the cascading failure detection condition.

### 3. Symbol Table Implementation for Node and Model Resolution

The symbol tables map SPICE netlist names to mathematical indices:

```c
/* Hash table structure for O(1) name lookup */
typedef struct hashtable {
    int size;
    int count;
    HashEntry **entries;
} HASHTABLE;

typedef struct hashentry {
    char *key;                     // Node/model/instance name
    void *value;                   // CKTnode*/GENmodel*/GENinstance*
    struct hashentry *next;        // Separate chaining for collisions
} HashEntry;

/* Node table maps "Vdd", "gnd", "net5" → matrix indices */
int CKTnodeHash(const char *name, int size) {
    unsigned long hash = 5381;
    int c;
    while ((c = *name++)) {
        hash = ((hash << 5) + hash) + c;  // hash * 33 + c
    }
    return hash % size;
}

CKTnode *CKTfindNode(CKTcircuit *ckt, const char *name) {
    int index = CKTnodeHash(name, ckt->CKTnodeTable->size);
    HashEntry *entry = ckt->CKTnodeTable->entries[index];
    
    while (entry) {
        if (strcmp(entry->key, name) == 0) {
            return (CKTnode*)entry->value;
        }
        entry = entry->next;
    }
    
    /* Not found: create new node */
    CKTnode *node = (CKTnode*)malloc(sizeof(CKTnode));
    node->number = ckt->CKTnumNodes++;
    node->name = strdup(name);
    
    /* Insert into hash table */
    HashEntry *newEntry = (HashEntry*)malloc(sizeof(HashEntry));
    newEntry->key = strdup(name);
    newEntry->value = node;
    newEntry->next = ckt->CKTnodeTable->entries[index];
    ckt->CKTnodeTable->entries[index] = newEntry;
    
    return node;
}
```

**Mathematical Mapping**: The hash table provides O(1) lookup for node names, enabling efficient construction of the MNA matrix `[G B; Bᵀ D]`. Each node name maps to a specific row/column in the matrix, implementing the mapping from circuit topology to mathematical representation.

### 4. Memory Interface for Sparse Matrix Operations

The sparse matrix interface implements the mathematical matrix operations:

```c
/* Sparse Matrix Interface (smpmatrix.c) */
typedef struct smpmatrix {
    int size;                      // Matrix dimension n
    int *colptr;                   // CSC: column pointers
    int *rowind;                   // CSC: row indices
    double *values;                // CSC: non-zero values
    double *rhs;                   // Right-hand side for solves
    double *solution;              // Solution vector
    int factored;                  // LU factorization flag
    double *luValues;              // LU factors
    int *perm;                     // Row permutation
    int *invperm;                  // Inverse permutation
} SMPmatrix;

/* Matrix factorization with pivot thresholding */
int SMPfactor(SMPmatrix *matrix, double gmin, int *singular) {
    int n = matrix->size;
    
    for (int col = 0; col < n; col++) {
        /* Find pivot in column */
        double maxVal = 0.0;
        int pivotRow = -1;
        
        for (int i = matrix->colptr[col]; i < matrix->colptr[col+1]; i++) {
            int row = matrix->rowind[i];
            if (row >= col) {  // Consider only lower triangle for pivot
                double absVal = fabs(matrix->values[i]);
                if (absVal > maxVal) {
                    maxVal = absVal;
                    pivotRow = row;
                }
            }
        }
        
        /* Pivot thresholding: if |pivot| < PIVTOL, add GMIN */
        if (maxVal < PIVTOL) {
            // Add ε·I to diagonal: J(x) + ε·I
            int diagIdx = SMPfindElement(matrix, col, col);
            if (diagIdx >= 0) {
                matrix->values[diagIdx] += gmin;
            } else {
                SMPinsertElement(matrix, col, col, gmin);
            }
            maxVal = gmin;
        }
        
        if (singular && maxVal < 1e-30) {
            *singular = col;
            return E_SINGULAR;
        }
        
        /* Perform LU factorization with partial pivoting */
        SMPeliminateColumn(matrix, col, pivotRow);
    }
    
    matrix->factored = 1;
    return OK;
}

/* Forward/backward substitution */
int SMPsolve(SMPmatrix *matrix, double *rhs, double *solution) {
    if (!matrix->factored) return E_NOTFACTORED;
    
    /* Forward substitution: L·y = P·b */
    for (int i = 0; i < matrix->size; i++) {
        solution[i] = rhs[matrix->perm[i]];
        for (int j = matrix->colptr[i]; j < matrix->colptr[i+1]; j++) {
            int row = matrix->rowind[j];
            if (row < i) {
                solution[i] -= matrix->luValues[j] * solution[row];
            }
        }
    }
    
    /* Backward substitution: U·x = y */
    for (int i = matrix->size-1; i >= 0; i--) {
        for (int j = matrix->colptr[i]; j < matrix->colptr[i+1]; j++) {
            int row = matrix->rowind[j];
            if (row > i) {
                solution[i] -= matrix->luValues[j] * solution[row];
            }
        }
        solution[i] /= SMPgetDiagonal(matrix, i);
    }
    
    return OK;
}
```

**Mathematical Mapping**: The `SMPfactor` function implements the LU factorization of the Jacobian matrix `J(x)` with pivot thresholding that adds `ε·I` (GMIN) when pivots are too small. This directly implements the homotopy continuation method `J(x) + ε·I = b`. The `SMPsolve` function solves the linear system `J·Δx = -F` using forward/backward substitution.

### 5. Error Propagation and Recovery System

The error handling system maps mathematical failure modes to recovery actions:

```c
/* Error codes mapping to mathematical failures */
#define OK            0
#define E_NOMEM       1    // Memory allocation failure
#define E_SINGULAR    2    // Singular matrix: det(J) ≈ 0
#define E_CONVFAIL    3    // Newton non-convergence
#define E_TIMESTEP    4    // Timestep too small
#define E_OVERFLOW    5    // Numerical overflow
#define E_BADMATRIX   6    // Matrix structure error

/* Error recovery with cascading fallbacks */
int CKTrecover(CKTcircuit *ckt, int error) {
    switch (error) {
        case E_SINGULAR:
            /* Homotopy continuation: increase GMIN */
            ckt->CKTgmin *= 10.0;
            if (ckt->CKTgmin > 1.0) {
                return E_CONVFAIL;  // Give up if GMIN too large
            }
            return RETRY;
            
        case E_CONVFAIL:
            if (ckt->CKTmode & MODEDC) {
                /* Source stepping: J(x)·x = λ·b */
                return DCtrouble(ckt);  // Reduce λ and retry
            } else if (ckt->CKTmode & MODETRAN) {
                /* Timestep reduction: h_new = 0.5·h_old */
                ckt->CKTdelta *= 0.5;
                if (ckt->CKTdelta < MINTIMESTEP) {
                    return E_TIMESTEP;
                }
                return RETRY;
            }
            break;
            
        case E_OVERFLOW:
            /* Clamp exponential arguments */
            for (int i = 0; i < ckt->CKTnumStates; i++) {
                if (ckt->CKTstate0[i] > EXP_CLAMP) {
                    ckt->CKTstate0[i] = EXP_CLAMP;
                } else if (ckt->CKTstate0[i] < -EXP_CLAMP) {
                    ckt->CKTstate0[i] = -EXP_CLAMP;
                }
            }
            return RETRY;
    }
    
    return error;  // Unrecoverable error
}

/* Safe mathematical operations with error bounds */
double safe_exp(double x) {
    if (x > 80.0) return exp(80.0);      // Prevent overflow
    if (x < -80.0) return exp(-80.0);    // Prevent underflow
    return exp(x);
}

double safe_divide(double a, double b) {
    if (fabs(b) < 1e-30) {
        if (a >= 0) return 1e30;         // HUGE_VAL
        else return -1e30;
    }
    return a / b;
}
```

**Mathematical Mapping**: The error recovery system implements the failure cascade mechanism mathematically described. When `det(J) ≈ 0` (E_SINGULAR), it increases `ε` in `J(x) + ε·I`. When Newton fails to converge (E_CONVFAIL), it reduces `λ` in source stepping `J(x)·x = λ·b` or reduces the timestep `h` in transient analysis.

### 6. Analysis Plugin Architecture

The analysis interface maps mathematical domains to C implementations:

```c
/* Analysis function table (analysis.c) */
IFanalysis DCanalysis = {
    DCOP,
    "dc",
    DCcreate,     // Allocate DC analysis struct
    DCdestroy,    // Free memory
    DCparam,      // Set parameters (e.g., sweep ranges)
    DCsetParm,    // Apply parameters to circuit
    DCaskQuest,   // Query analysis results
    DCload,       // Load DC equations: G·x = b
    DCtemp,       // Temperature adjustments
    DCaccept,     // Accept solution
    DCdestroy     // Cleanup
};

/* DC analysis load function implements F(x, 0, t) = 0 */
int DCload(CKTcircuit *ckt, GENERIC *anal) {
    DCanalysis *dc = (DCanalysis*)anal;
    
    /* Zero out matrix and RHS */
    SMPzeroMatrix(ckt->CKTmatrix);
    for (int i = 0; i < ckt->CKTnumStates; i++) {
        ckt->CKTrhs[i] = 0.0;
    }
    
    /* Load resistive contributions to G matrix */
    for (GENmodel *model = ckt->CKTmodels; model; model = model->next) {
        for (GENinstance *inst = model->instances; inst; inst = inst->next) {
            if (model->modType == RESISTOR) {
                double g = 1.0 / inst->resistance;
                int pos = inst->posNode->number;
                int neg = inst->negNode->number;
                
                /* Add to G matrix: G[pos][pos] += g, G[neg][neg] += g */
                /* G[pos][neg] -= g, G[neg][pos] -= g */
                SMPaddToElement(ckt->CKTmatrix, pos, pos, g);
                SMPaddToElement(ckt->CKTmatrix, neg, neg, g);
                SMPaddToElement(ckt->CKTmatrix, pos, neg, -g);
                SMPaddToElement(ckt->CKTmatrix, neg, pos, -g);
            }
        }
    }
    
    /* Load DC sources to RHS vector b */
    for (GENmodel *model = ckt->CKTmodels; model; model = model->next) {
        for (GENinstance *inst = model->instances; inst; inst = inst->next) {
            if (model->modType == VSOURCE) {
                int pos = inst->posNode->number;
                int neg = inst->negNode->number;
                ckt->CKTrhs[pos] -= inst->dcValue;
                ckt->CKTrhs[neg] += inst->dcValue;
            }
        }
    }
    
    return OK;
}
```

**Mathematical Mapping**: Each analysis type implements a specific form of the DAE. `DCload` builds the DC equation `G·x = b`. `ACload` builds the complex equation `(G + jωC)·X = B`. `TRANload` builds the discretized equation `G·x(t) + C·ẋ(t) = b(t)` using numerical integration coefficients.

### 7. Device Model Integration Interface

Device models implement the constitutive relations `F_device(x, ẋ, t)`:

```c
/* Generic device model interface */
typedef struct sGENmodel {
    int modType;                   // RESISTOR, CAPACITOR, MOSFET, etc.
    struct sGENmodel *next;        // Linked list of all models
    GENinstance *instances;        // Linked list of instances
    double **staticProps;          // Model parameters (e.g., VTO for MOSFET)
    double **instanceProps;        // Instance parameters (e.g., W, L)
    int (*load)(GENmodel*, CKTcircuit*);  // Load function
    int (*setup)(GENmodel*, CKTcircuit*); // Setup function
    int (*temp)(GENmodel*, CKTcircuit*);  // Temperature update
} GENmodel;

typedef struct sGENinstance {
    int type;                      // Instance type
    struct sGENinstance *next;     // Next instance
    CKTnode *pos, *neg;           // Terminal nodes
    CKTnode *internalNodes[4];    // Internal nodes (for MOSFETs, etc.)
    double *state;                // State variables
    double *derivs;               // Derivatives ∂I/∂V, ∂Q/∂V
    GENmodel *model;              // Pointer to parent model
    double area;                  Geometry scaling factor
} GENinstance;

/* MOSFET load function example */
int MOSload(GENmodel *model, CKTcircuit *ckt) {
    for (GENinstance *inst = model->instances; inst; inst = inst->next) {
        double vgs, vds, vbs;  // Terminal voltages
        double ids, gm, gds, gmb;  // Current and conductances
        
        /* Compute terminal voltages from state vector */
        vgs = ckt->CKTstate0[inst->gateNode->number] - 
              ckt->CKTstate0[inst->sourceNode->number];
        vds = ckt->CKTstate0[inst->drainNode->number] - 
              ckt->CKTstate0[inst->sourceNode->number];
        vbs = ckt->CKTstate0[inst->bulkNode->number] - 
              ckt->CKTstate0[inst->sourceNode->number];
        
        /* MOSFET equations (simplified Level 1) */
        if (vgs < model->VTO) {  // Cutoff
            ids = 0.0;
            gm = 0.0;
            gds = 0.0;
        } else if (vds < vgs - model->VTO) {  // Linear
            ids = model->KP * inst->W/inst->L * 
                  ((vgs - model->VTO)*vds - 0.5*vds*vds);
            gm = model->KP * inst->W/inst->L * vds;
            gds = model->KP * inst->W/inst->L * (vgs - model->VTO - vds);
        } else {  // Saturation
            ids = 0.5 * model->KP * inst->W/inst->L * 
                  (vgs - model->VTO)*(vgs - model->VTO);
            gm = model->KP * inst->W/inst.L * (vgs - model->VTO);
            gds = 0.0;
        }
        
        /* Load current into R