# Numerical Iteration: System Initialization and Teardown

_Generated 2026-04-11 17:03 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/niinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/nireinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/nidest.c`

# Chapter: Numerical Iteration: System Initialization and Teardown

## Introduction

The Newton Iteration (NI) subsystem in Ngspice provides the core numerical engine for solving nonlinear circuit equations through the Newton-Raphson method. The files `niinit.c`, `nireinit.c`, and `nidest.c` implement the complete lifecycle management of this iterative solver, handling memory allocation, state preservation, and resource cleanup. These modules create and manage the `NIstate` structure, which encapsulates the entire Newton iteration workspace including the Jacobian matrix, solution vectors, convergence parameters, and circuit bindings. The initialization establishes the mathematical framework for solving **F(x) = 0**, where **x** represents node voltages and branch currents, while the teardown ensures proper memory deallocation following Ngspice's ownership model. The re-initialization function enables state reuse across multiple analysis points without recomputing matrix sparsity patterns, providing significant performance benefits in transient and AC analyses.

## Mathematical Formulation

The Newton Iteration (NI) framework in Ngspice provides the numerical backbone for solving the nonlinear algebraic-differential equations arising from circuit simulation. The mathematical formulation is directly implemented in the NI data structures and algorithms.

### Nonlinear Circuit Equations

The fundamental problem is to find the vector of unknowns **x** (node voltages and branch currents) that satisfies the system of nonlinear equations:

**F(x) = 0**

where for each circuit node *i*, the equation takes the form:

**Fᵢ(x) = Σ I_branch(x) + Σ C·(dV/dt) + Σ I_source**

In the NIstate structure, this maps directly to:
- **x** ↔ `NIsolution[]` array (size *n*)
- **F(x)** ↔ `NIRHS[]` array (size *n*)
- *n* = `NInumNodes` = number of circuit nodes + voltage sources + special equations

### Jacobian Matrix Formulation

The Newton-Raphson method linearizes the system at each iteration *k*:

**J(xᵏ)·δxᵏ = -F(xᵏ)**

where **J(xᵏ)** = ∇F(xᵏ) = ∂Fᵢ/∂xⱼ is the Jacobian matrix.

In implementation:
- **J** ↔ `NIjacobian` (SMPmatrix structure)
- Matrix elements **J[i][j]** = `NIjacobian→values[]` with sparsity pattern defined by `colind[]` and `rowptr[]`
- The matrix dimension is *n*×*n* where *n* = `NIjacobian→size`

### Iteration Update Equation

The Newton iteration update is implemented as:

**xᵏ⁺¹ = xᵏ + α·δxᵏ**

where:
- **δxᵏ** = solution of **J(xᵏ)·δxᵏ = -F(xᵏ)**
- **α** ∈ (0,1] is a damping factor for convergence control
- **xᵏ** ↔ `NIoldSolution[]` (previous iteration)
- **xᵏ⁺¹** ↔ `NIsolution[]` (updated solution)
- **δxᵏ** magnitude is controlled by `NIstepMax` parameter

### Matrix Equation Construction

The Jacobian is built from device contributions following the direct binding to circuit topology:

```
for each device in circuit {
    device→load(device, ckt, J, ckt→CKTrhs);
}
```

This computes the device stamps where for a device connecting nodes *i* and *j*:
- **∂Iᵢ/∂Vᵢ**, **∂Iᵢ/∂Vⱼ**, **∂Iⱼ/∂Vᵢ**, **∂Iⱼ/∂Vⱼ** are added to appropriate Jacobian positions
- The corresponding **Iᵢ(x)**, **Iⱼ(x)** are added to the RHS vector

### Boundary Condition Enforcement

For grounded nodes (voltage fixed at 0V), the system enforces:
- **J[row][row] = 1.0** (diagonal element set to unity)
- **F[row] = 0.0** (RHS set to zero)
where `row = node→number` from the `nodeMap[]` array.

### Time Integration Coupling

For transient analysis, the equations incorporate time derivatives via numerical integration:

**F(x, dx/dt, t) = 0**

The NI framework supports this through:
- `NIorder`: Integration method order (1 for Backward Euler, 2 for Trapezoidal, etc.)
- Companion models convert capacitors and inductors to conductive equivalents:
  - Capacitor: **I = C·(Vᵏ⁺¹ - Vᵏ)/Δt** becomes **I = G_eq·Vᵏ⁺¹ + I_eq**
  - Inductor: **V = L·(Iᵏ⁺¹ - Iᵏ)/Δt** becomes **V = R_eq·Iᵏ⁺¹ + V_eq**

## Convergence Analysis

### Convergence Criteria

The NI framework implements multiple convergence tests, all tracked within the NIstate structure:

#### 1. Absolute Convergence Criterion

**‖F(xᵏ)‖∞ < ε_abs**

where:
- ‖·‖∞ is the maximum norm (infinity norm)
- ε_abs = `NIabstol` (typically 1e-12)
- **F(xᵏ)** = `NIresiduals[]` array
- The maximum residual is tracked in `NImaxResidual`

Implementation:
```c
max_residual = 0.0;
for (i = 0; i < NInumNodes; i++) {
    residual = fabs(NIresiduals[i]);
    if (residual > max_residual) max_residual = residual;
}
if (max_residual < NIabstol) NIconverged = 1;
```

#### 2. Relative Convergence Criterion

**‖δxᵏ‖ / max(‖xᵏ‖, 1.0) < ε_rel**

where:
- ‖δxᵏ‖ = norm of the solution update
- ‖xᵏ‖ = norm of the current solution
- ε_rel = `NIreltol` (typically 1e-3)
- `NIdelta` stores the current step size ‖δxᵏ‖

Implementation avoids division by zero using the max(‖xᵏ‖, 1.0) term.

#### 3. Voltage-Specific Convergence

**|Vᵢᵏ⁺¹ - Vᵢᵏ| < ε_volt** for all voltage nodes *i*

where ε_volt = `NIvoltTol` (typically 1e-6). This provides tighter control on voltage variables which are often the primary unknowns.

### Iteration Control Parameters

The convergence behavior is governed by parameters in NIstate:

- `NImaxIter` = 100 (maximum Newton iterations before failure)
- `NIiter` tracks current iteration count *k*
- `NIstepMax` = 10.0 (maximum allowed step size ‖δxᵏ‖∞)
- `NIconverged` boolean flag indicates convergence status

### Step Limiting and Damping

To prevent divergence and improve convergence, the algorithm implements:

#### Step Limiting:
If **‖δxᵏ‖ > δ_max** where δ_max = `NIstepMax`:
**δxᵏ ← δxᵏ × (δ_max / ‖δxᵏ‖)**

This ensures the update doesn't exceed the maximum step size.

#### Damping (Adaptive):
**xᵏ⁺¹ = xᵏ + α·δxᵏ** with **α ∈ (0,1]**

The damping factor α is reduced when:
- Convergence is slow (many iterations)
- Residuals oscillate
- Previous step was also damped

### Convergence Failure Modes

#### 1. Iteration Limit Exceeded
When `NIiter >= NImaxIter` without convergence:
- If `NIerror < NIstepMax`: Reduce step size and retry (`NIdelta *= 0.5`)
- Otherwise: Report fatal convergence failure

#### 2. Numerical Singularity
When the Jacobian **J(xᵏ)** is nearly singular:
- Matrix factorization fails in `SMPfactor()`
- `NIjacobian→isFactored` remains 0
- Algorithm may attempt regularization or step reduction

#### 3. Oscillatory Behavior
Detected when sign(**δxᵏ**) alternates for several iterations:
- Solution oscillates between values
- Damping factor α is aggressively reduced
- May trigger matrix rebuild if sparsity pattern is suspect

### Convergence Rate Analysis

The Newton-Raphson method exhibits quadratic convergence near the solution:

**‖xᵏ⁺¹ - x*‖ ≤ C·‖xᵏ - x*‖²**

where x* is the true solution. In practice, circuit simulation achieves:
- Linear convergence initially (far from solution)
- Quadratic convergence near solution
- Convergence rate monitored via `NIerror` reduction per iteration

### Matrix Reuse and Convergence

The sparsity pattern reuse strategy impacts convergence:
- Jacobian structure preserved across iterations (`NIjacobian` sparsity pattern constant)
- Only numerical values recomputed each iteration
- LU factorization reused while `NIjacobian→isFactored = 1`
- Structure rebuild triggered when convergence degrades, indicating possible topology change

### Initial Guess Strategy

The initial guess **x₀** significantly affects convergence:
- For DC analysis: `NIsolution[i] = ckt→CKTrhs[i]` (circuit RHS values)
- For transient analysis: `NIsolution[i] = ckt→CKTrhsOld[i]` (previous time step solution)
- Voltage sources initialized to their source values
- Nonlinear devices may use special initialization (PN junctions, etc.)

### Error Norm Computation

The convergence error is computed as a weighted norm:

**error = max( ‖F(xᵏ)‖∞/ε_abs, ‖δxᵏ‖/(ε_rel·max(‖xᵏ‖,1)) )**

Stored in `NIerror` for tracking and step control.

### Practical Convergence Considerations

1. **Mixed Signals**: Circuits with both large (power supply) and small (signal) voltages require careful relative tolerance application
2. **Discontinuities**: Ideal diodes, switches cause derivative discontinuities; convergence may require smaller steps
3. **Floating Nodes**: Unconnected nodes lead to singular Jacobian; detected during matrix factorization
4. **Time Step Control**: In transient analysis, convergence failure triggers time step reduction (`Δt → Δt/2`)

The convergence analysis in Ngspice thus provides a robust framework for handling the wide variety of convergence scenarios encountered in practical circuit simulation.

## C Implementation

### Core Data Structures

#### NIstate Structure

The `NIstate` structure encapsulates the complete Newton iteration state:

```c
typedef struct NIstate {
    /* Control Parameters */
    int             NItype;          /* Type of Newton iteration */
    int             NImaxIter;       /* Maximum Newton iterations */
    double          NIabstol;        /* Absolute tolerance ‖F(x)‖∞ < ε_abs */
    double          NIreltol;        /* Relative tolerance ‖δx‖/‖x‖ < ε_rel */
    double          NIvoltTol;       /* Voltage-specific tolerance */
    double          NIstepMax;       /* Maximum step size ‖δx‖∞ < δ_max */
    
    /* Sparse Matrix System */
    SMPmatrix      *NIjacobian;      /* Jacobian matrix J = ∂F/∂x */
    double         *NIsolution;      /* Solution vector x */
    double         *NIRHS;           /* Right-hand side vector F(x) */
    double         *NIoldSolution;   /* Previous solution xₖ⁻¹ */
    
    /* Iteration Control */
    int             NIiter;          /* Current iteration count k */
    int             NIorder;         /* Integration method order */
    double          NIdelta;         /* Current step δx */
    double          NIerror;         /* Current error estimate */
    
    /* Circuit State Binding */
    CKTnode       **NInodes;         /* Circuit node pointers */
    int             NInumNodes;      /* Number of circuit nodes n */
    GENmodel      **NImodels;        /* Device model pointers */
    int             NInumModels;     /* Number of device models */
    
    /* Convergence Tracking */
    int             NIconverged;     /* Convergence flag */
    double         *NIresiduals;     /* Residual vector r = F(x) */
    double          NImaxResidual;   /* Maximum residual norm ‖r‖∞ */
    
    /* Memory Management */
    void           *NIuserData;      /* User-defined data */
    void           *NIdeviceData;    /* Device-specific data */
} NIstate;
```

#### SMPmatrix Structure

The sparse matrix package structure implements the Jacobian storage:

```c
typedef struct SMPmatrix {
    int             size;            /* Matrix dimension n×n */
    int             nz;              /* Number of non-zero entries */
    double         *values;          /* Non-zero values array J[i][j] */
    int            *colind;          /* Column indices (CSC format) */
    int            *rowptr;          /* Row pointers (CSC format) */
    int            *diagptr;         /* Diagonal element pointers */
    
    /* Factorization data */
    double         *LUvalues;        /* LU factorization values */
    int            *LUcolind;        /* LU column indices */
    int            *LUrowptr;        /* LU row pointers */
    int             isFactored;      /* Factorization flag */
    
    /* Circuit binding */
    CKTnode       **nodeMap;         /* Node to matrix row mapping */
    int            *eqnMap;          /* Equation numbering */
} SMPmatrix;
```

### Initialization Implementation (`niinit.c`)

#### Structure Allocation

The initialization function creates the Newton iteration workspace:

```c
NIstate* NIinit(CKTcircuit *ckt)
{
    NIstate *ni;
    
    /* Allocate NIstate structure */
    ni = (NIstate *) MALLOC(sizeof(NIstate));
    if (!ni) return NULL;
    
    /* Initialize all pointers to NULL */
    ni->NIjacobian = NULL;
    ni->NIsolution = NULL;
    ni->NIRHS = NULL;
    ni->NIoldSolution = NULL;
    ni->NIresiduals = NULL;
    ni->NInodes = NULL;
    ni->NImodels = NULL;
    
    /* Set default mathematical parameters */
    ni->NItype = 0;              /* Standard Newton-Raphson */
    ni->NImaxIter = 100;         /* Maximum iterations k_max */
    ni->NIabstol = 1e-12;        /* ε_abs for ‖F(x)‖∞ */
    ni->NIreltol = 1e-3;         /* ε_rel for ‖δx‖/‖x‖ */
    ni->NIvoltTol = 1e-6;        /* Voltage tolerance */
    ni->NIstepMax = 10.0;        /* δ_max for step limiting */
    
    /* Initialize iteration counters */
    ni->NIiter = 0;              /* k = 0 */
    ni->NIconverged = 0;         /* converged = false */
    ni->NIerror = 0.0;
    ni->NImaxResidual = 0.0;
    
    /* Determine system size n */
    int n = ckt->CKTmaxEqnNum;   /* Circuit equations count */
    ni->NInumNodes = n;
    
    /* Allocate sparse Jacobian matrix J */
    int estimated_nz = 10 * n;   /* α·n with α=10 */
    ni->NIjacobian = SMPnewMatrix(n, estimated_nz);
    
    /* Allocate solution vectors */
    ni->NIsolution = TMALLOC(double, n);      /* x vector */
    ni->NIRHS = TMALLOC(double, n);           /* F(x) vector */
    ni->NIoldSolution = TMALLOC(double, n);   /* xₖ⁻¹ vector */
    ni->NIresiduals = TMALLOC(double, n);     /* r vector */
    
    /* Bind to circuit structures */
    ni->NInodes = ckt->CKTnodes;              /* Node pointers */
    ni->NImodels = ckt->CKTmodels;            /* Model pointers */
    ni->NInumModels = ckt->CKTnumModels;
    
    /* Initialize solution to circuit RHS */
    for (int i = 0; i < n; i++) {
        ni->NIsolution[i] = ckt->CKTrhs[i];      /* x₀ = CKTrhs */
        ni->NIoldSolution[i] = ckt->CKTrhsOld[i]; /* x₋₁ = CKTrhsOld */
        ni->NIresiduals[i] = 0.0;                /* r = 0 */
    }
    
    return ni;
}
```

#### Mathematical Mapping in Initialization

The C code directly implements the mathematical initialization:

1. **System dimension**: `n = ckt->CKTmaxEqnNum` maps to the number of equations
2. **Initial guess**: `NIsolution[i] = ckt->CKTrhs[i]` sets **x₀**
3. **Previous state**: `NIoldSolution[i] = ckt->CKTrhsOld[i]` stores **x₋₁**
4. **Tolerances**: Direct assignment of ε_abs, ε_rel, δ_max
5. **Matrix allocation**: `SMPnewMatrix(n, estimated_nz)` creates **J** with O(α·n) storage

### Re-initialization Implementation (`nireinit.c`)

#### State Preservation Logic

The re-initialization function resets iteration state while preserving circuit binding:

```c
void NIreinit(NIstate *ni, CKTcircuit *ckt)
{
    /* Preserve circuit binding - these are external pointers */
    ni->NInodes = ckt->CKTnodes;
    ni->NImodels = ckt->CKTmodels;
    ni->NInumNodes = ckt->CKTmaxEqnNum;
    
    /* Reset iteration counters */
    ni->NIiter = 0;              /* k = 0 */
    ni->NIconverged = 0;         /* converged = false */
    ni->NIerror = 0.0;
    ni->NImaxResidual = 0.0;
    
    /* Preserve matrix structure but clear values */
    if (ni->NIjacobian) {
        SMPclear(ni->NIjacobian);      /* Set J[i][j] = 0 */
        ni->NIjacobian->isFactored = 0; /* Invalidate LU factorization */
    }
    
    /* Reset solution vectors to current circuit state */
    int n = ni->NInumNodes;
    for (int i = 0; i < n; i++) {
        ni->NIsolution[i] = ckt->CKTrhs[i];      /* x₀ = current RHS */
        ni->NIoldSolution[i] = ckt->CKTrhsOld[i]; /* x₋₁ = previous RHS */
        ni->NIresiduals[i] = 0.0;                /* r = 0 */
    }
    
    /* Re-initialize convergence parameters */
    ni->NIdelta = ni->NIstepMax;        /* Reset step size to δ_max */
}
```

#### Mathematical State Transfer

The re-initialization implements the mathematical reset:

1. **Jacobian clearing**: `SMPclear()` sets **J = 0** while preserving sparsity pattern
2. **Factorization invalidation**: `isFactored = 0` forces recomputation of **J⁻¹**
3. **Solution reset**: `NIsolution[i] = CKTrhs[i]` reinitializes **x₀** from circuit
4. **Iteration reset**: `NIiter = 0` restarts iteration counter **k**

### Destruction Implementation (`nidest.c`)

#### Memory Deallocation Algorithm

The destruction function releases all allocated memory:

```c
void NIdestroy(NIstate **niPtr)
{
    NIstate *ni = *niPtr;
    if (!ni) return;
    
    /* Free sparse matrix J */
    if (ni->NIjacobian) {
        SMPdestroy(&(ni->NIjacobian));  /* Full matrix destruction */
    }
    
    /* Free solution vector x */
    if (ni->NIsolution) {
        FREE(ni->NIsolution);
    }
    
    /* Free RHS vector F(x) */
    if (ni->NIRHS) {
        FREE(ni->NIRHS);
    }
    
    /* Free previous solution vector xₖ⁻¹ */
    if (ni->NIoldSolution) {
        FREE(ni->NIoldSolution);
    }
    
    /* Free residual vector r */
    if (ni->NIresiduals) {
        FREE(ni->NIresiduals);
    }
    
    /* Note: Circuit pointers (NInodes, NImodels) are not owned */
    /* They point to circuit-owned memory, so we don't free them */
    
    /* Free the state structure itself */
    FREE(ni);
    *niPtr = NULL;  /* Prevent dangling pointer */
}
```

#### Memory Ownership Model

The implementation follows strict ownership rules:

1. **Owned memory** (freed in `NIdestroy`):
   - `NIjacobian` and its internal arrays
   - `NIsolution[]`, `NIRHS[]`, `NIoldSolution[]`, `NIresiduals[]`
   - The `NIstate` structure itself

2. **Borrowed memory** (not freed):
   - `NInodes[]` points to `ckt->CKTnodes[]`
   - `NImodels[]` points to `ckt->CKTmodels[]`
   - These are owned by the circuit structure

### Matrix Building Implementation

#### Jacobian Construction

The matrix building function assembles the Jacobian from device contributions:

```c
int NIbuildMatrix(NIstate *ni, CKTcircuit *ckt)
{
    SMPmatrix *J = ni->NIjacobian;
    int n = ni->NInumNodes;
    
    /* Clear existing matrix values J[i][j] = 0 */
    SMPclear(J);
    
    /* Build Jacobian from device contributions */
    for (int modelIndex = 0; modelIndex < ni->NInumModels; modelIndex++) {
        GENmodel *model = ni->NImodels[modelIndex];
        GENinstance *inst;
        
        for (inst = model->GENinstances; inst != NULL; 
             inst = inst->GENnextInstance) {
            /* Each device loads its ∂I/∂V contributions */
            inst->load(inst, ckt, J, ckt->CKTrhs);
        }
    }
    
    /* Apply boundary conditions for grounded nodes */
    for (int i = 0; i < n; i++) {
        CKTnode *node = ni->NInodes[i];
        if (node->type == SP_VOLTAGE && node->number == 0) {
            /* Ground node: V = 0 constraint */
            int row = i;
            SMPsetElement(J, row, row, 1.0);  /* J[row][row] = 1 */
            ckt->CKTrhs[row] = 0.0;          /* F[row] = 0 */
        }
    }
    
    /* Factor matrix for solving J·δx = -F */
    int error = SMPfactor(J);
    if (error == 0) {
        J->isFactored = 1;  /* LU factorization valid */
    } else {
        J->isFactored = 0;  /* Factorization failed */
        return error;
    }
    
    return OK;
}
```

#### Mathematical Device Loading

Each device's `load()` function computes its contributions to:
- **Jacobian elements**: `∂I_device/∂V_nodes`
- **RHS contributions**: `I_device(x)`

For a resistor between nodes i and j:
```c
/* Conductance G = 1/R */
SMPaddElement(J, i, i,  G);  /* ∂Iᵢ/∂Vᵢ = +G */
SMPaddElement(J, i, j, -G);  /* ∂Iᵢ/∂Vⱼ = -G */
SMPaddElement(J, j, i, -G);  /* ∂Iⱼ/∂Vᵢ = -G */
SMPaddElement(J, j, j,  G);  /* ∂Iⱼ/∂Vⱼ = +G */

/* Current I = G·(Vᵢ - Vⱼ) */
ckt->CKTrhs[i] -= I;  /* Fᵢ -= I */
ckt->CKTrhs[j] += I;  /* Fⱼ += I */
```

### Convergence Checking Implementation

#### Convergence Test Function

The convergence checking implements the mathematical criteria:

```c
int NIconvergedTest(NIstate *ni)
{
    int n = ni->NInumNodes;
    double max_residual = 0.0;
    double norm_x = 0.0;
    double norm_dx = 0.0;
    
    /* Compute ‖r‖∞ = max|F(x)| */
    for (int i = 0; i < n; i++) {
        double residual = fabs(ni->NIresiduals[i]);
        if (residual > max_residual) {
            max_residual = residual;
        }
    }
    ni->NImaxResidual = max_residual;
    
    /* Compute ‖x‖ and ‖δx‖ */
    for (int i = 0; i < n; i++) {
        double x = ni->NIsolution[i];
        double dx = ni->NIsolution[i] - ni->NIoldSolution[i];
        norm_x += x * x;
        norm_dx += dx * dx;
    }
    norm_x = sqrt(norm_x);
    norm_dx = sqrt(norm_dx);
    
    /* Absolute convergence: ‖F(x)‖∞ < ε_abs */
    if (max_residual < ni->NIabstol) {
        ni->NIconverged = 1;
        return 1;
    }
    
    /* Relative convergence: ‖δx‖/max(‖x‖,1) < ε_rel */
    double denominator = (norm_x > 1.0) ? norm_x : 1.0;
    if (norm_dx / denominator < ni->NIreltol) {
        ni->NIconverged = 1;
        return 1;
    }
    
    /* Voltage-specific check for voltage nodes */
    int voltage_converged = 1;
    for (int i = 0; i < n; i++) {
        CKTnode *node = ni->NInodes[i];
        if (node->type == SP_VOLTAGE) {
            double dx = fabs(ni->NIsolution[i] - ni->NIoldSolution[i]);
            if (dx > ni->NIvoltTol) {
                voltage_converged = 0;
                break;
            }
        }
    }
    
    if (voltage_converged) {
        ni->NIconverged = 1;
        return 1;
    }
    
    return 0;  /* Not converged */
}
```

#### Step Limiting Implementation

The step limiting prevents divergence:

```c
void NIlimitStep(NIstate *ni)
{
    double max_step = 0.0;
    int n = ni->NInumNodes;
    
    /* Find maximum component of δx */
    for (int i = 0; i < n; i++) {
        double dx = fabs(ni->NIsolution[i] - ni->NIoldSolution[i]);
        if (dx > max_step) {
            max_step = dx;
        }
    }
    
    /* Apply step limiting: if ‖δx‖∞ > δ_max, scale down */
    if (max_step > ni->NIstepMax) {
        double scale = ni->NIstepMax / max_step;
        for (int i = 0; i < n; i++) {
            double dx = ni->NIsolution[i] - ni->NIoldSolution[i];
            ni->NIsolution[i] = ni->NIoldSolution[i] + scale * dx;
        }
        ni->NIdelta = ni->NIstepMax;  /* Update step size */
    } else {
        ni->NIdelta = max_step;
    }
}
```

### Error Recovery Implementation

#### Convergence Failure Handling

When Newton iteration fails to converge:

```c
int NIhandleFailure(NIstate *ni)
{
    /* Check if max iterations exceeded */
    if (ni->NIiter >= ni->NImaxIter) {
        /* Newton failed to converge in k_max iterations */
        if (ni->NIerror < ni->NIstepMax) {
            /* Reduce step size and retry */
            ni->NIdelta *= 0.5;  /* δ_max ← δ_max/2 */
            ni->NIstepMax = ni->NIdelta;
            return TRY_AGAIN;
        } else {
            /* Fatal convergence failure */
            return CONVERGENCE_FAILURE;
        }
    }
    
    /* Check for numerical singularity */
    if (ni->NIjacobian && !ni->NIjacobian->isFactored) {
        /* Matrix factorization failed - J is singular */
        return MATRIX_SINGULAR;
    }
    
    return OK;
}
```

### Performance Optimizations

#### Matrix Reuse Strategy

The implementation optimizes by reusing matrix structures:

```c
/* Check if matrix structure needs rebuild */
int NImatrixNeedsRebuild(NIstate *ni, CKTcircuit *ckt)
{
    /* Rebuild if topology changed */
    if (ckt->CKTstateChanged) {
        return 1;
    }
    
    /* Rebuild if convergence is poor */
    if (ni->NIiter > 10 && ni->NIerror > 0.1 * ni->NIstepMax) {
        return 1;
    }
    
    /* Otherwise reuse existing structure */
    return 0;
}
```

#### Memory Pool Management

The allocation functions use Ngspice's memory management:

```c
/* TMALLOC uses thread-local memory pools */
double *vector = TMALLOC(double, n);

/* TREALLOC for resizing */
vector = TREALLOC(double, vector, new_n);

/* FREE returns memory to pool */
FREE(vector);
```

This C implementation directly maps mathematical operations to efficient data structures and algorithms, providing the numerical engine for SPICE circuit simulation while maintaining optimal memory usage and numerical stability.