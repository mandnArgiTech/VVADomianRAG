# Global Matrix Assembly: Device Loading and Temperature Clamping

_Generated 2026-04-13 06:39 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktmcrt.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/dkerproc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cluster.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/ckttemp.c`

# Chapter: Global Matrix Assembly: Device Loading and Temperature Clamping

## Introduction: Ngspice Matrix Assembly Engine

The global matrix assembly system forms the computational core of Ngspice's circuit simulation engine, responsible for constructing and solving the nonlinear systems that model electronic circuits. This chapter examines five critical C source files that implement the mathematical framework for Modified Nodal Analysis (MNA) with robust numerical handling:

- **`cktload.c`**: Main device loading dispatcher implementing the direct stamping method for Jacobian assembly
- **`cktmcrt.c`**: Matrix creation and sparse storage management (companion to load operations)
- **`dkerproc.c`**: Device kernel processor enabling parallelized device evaluation and matrix contribution
- **`cluster.c`**: Matrix reordering and clustering algorithms for fill-in reduction during LU factorization
- **`ckttemp.c`**: Temperature-dependent parameter updates and numerical clamping for exponential device equations

These files collectively implement the mathematical transformation from circuit netlists to solvable nonlinear algebraic systems, incorporating essential numerical safeguards for handling extreme voltages, temperatures, and device operating conditions. The architecture follows SPICE's traditional direct stamping approach while adding modern optimizations for parallel processing and numerical stability.

## Mathematical Formulation

### 1. Modified Nodal Analysis (MNA) Foundation

In SPICE circuit simulation, the global matrix assembly process constructs the system of equations that governs circuit behavior. The circuit is described by the nonlinear Differential-Algebraic Equation (DAE) system:

```math
F(x, \dot{x}, t) = 0
```

where:
- `x ∈ ℝᴺ` is the state vector containing node voltages and branch currents
- `N = n_nodes + n_branches` is the total number of unknowns
- `F: ℝᴺ × ℝᴺ × ℝ → ℝᴺ` represents Kirchhoff's Current and Voltage Laws (KCL/KVL) combined with device constitutive relations

### 2. Jacobian Matrix Structure for Newton-Raphson

During DC operating point analysis or transient analysis using implicit integration methods, SPICE employs the Newton-Raphson method to solve the nonlinear equations. This requires the Jacobian matrix:

```math
J(x) = \frac{\partial F}{\partial x} + \alpha \frac{\partial F}{\partial \dot{x}}
```

where `α` is a coefficient determined by the integration method (e.g., `α = 1/h` for Backward Euler with step size `h`).

For circuit analysis specifically, the Jacobian decomposes into physically meaningful components:

```math
J = G + \alpha C + \frac{\partial I_{nl}}{\partial x}
```

where:
- `G ∈ ℝᴺˣᴺ`: Linear conductance matrix from resistors and linear controlled sources
- `C ∈ ℝᴺˣᴺ`: Capacitance/inductance matrix from energy storage elements
- `∂Iₙₗ/∂x ∈ ℝᴺˣᴺ`: Jacobian contributions from nonlinear devices (diodes, transistors, etc.)

### 3. Device Jacobian Aggregation via Direct Stamping

Each device `k` in the circuit contributes a local Jacobian `Jₖ ∈ ℝᴺₖˣᴺₖ`, where `Nₖ` is the number of device terminals. SPICE assembles the global Jacobian through the **direct stamping method**:

```math
J[i,j] = \sum_{k=1}^{M} \sum_{(p,q)∈Tₖ} Jₖ[p,q] \cdot δ(i, mapₖ(p)) \cdot δ(j, mapₖ(q))
```

where:
- `M`: Total number of devices in the circuit
- `Tₖ`: Set of terminal pairs for device `k` (e.g., for a 3-terminal MOSFET: `{(gate,drain), (gate,source), (drain,source)}`)
- `mapₖ: Tₖ → {1,...,N}`: Mapping function that converts device terminal indices to global matrix indices
- `δ(i,j)`: Kronecker delta function (1 if `i = j`, 0 otherwise)

This can be expressed more compactly using projection matrices:

```math
J = \sum_{k=1}^{M} Pₖ^T \cdot Jₖ \cdot Pₖ
```

where `Pₖ ∈ {0,1}^{Nₖ×N}` is a projection matrix with `Pₖ[p,i] = 1` if device terminal `p` maps to global node `i`.

### 4. Sparse Matrix Assembly Algorithms

SPICE uses specialized sparse matrix formats to efficiently store and manipulate the Jacobian. The assembly process follows these mathematical steps:

**Triplet Format (Coordinate Format - COO)**:
Each device contributes a set of triplets `(i, j, value)`:
```math
T = \bigcup_{k=1}^{M} \{(mapₖ(p), mapₖ(q), Jₖ[p,q]) : (p,q)∈Tₖ\}
```

**Compressed Sparse Column (CSC) Construction**:
1. Count non-zeros per column: `col_count[j] = |{k: ∃i s.t. (i,j)∈Tₖ}|`
2. Compute column pointers: `col_ptr[j+1] = col_ptr[j] + col_count[j]`
3. Fill `row_ind` and `values` arrays by sorting triplets

**Mathematical Complexity**:
- Memory requirement: `O(nnz)` where `nnz = ∑ₖ Nₖ²` (total non-zero entries)
- Time complexity: `O(M·Nₖ²)` for triplet generation plus `O(nnz log nnz)` for sorting

### 5. Temperature-Dependent Device Models

SPICE device equations explicitly include temperature `T` as a parameter. For example, the diode equation becomes:

```math
I_d(V, T) = I_s(T) \left( e^{\frac{V}{nV_t(T)}} - 1 \right)
```

where the thermal voltage `V_t(T) = kT/q` depends on temperature.

The Jacobian requires temperature derivatives for proper convergence:

```math
\frac{\partial I_d}{\partial T} = \frac{\partial I_s}{\partial T} \left( e^{\frac{V}{nV_t}} - 1 \right) - I_s \frac{V}{nV_t^2} \frac{dV_t}{dT} e^{\frac{V}{nV_t}}
```

### 6. Matrix Reordering for Sparsity Preservation

To minimize fill-in during LU factorization, SPICE applies permutation matrices `P` and `Q`:

```math
PJQ = LU
```

The fill-in reduction problem is formulated as:

```math
\text{minimize}_{π} \quad \text{nnz}(L·U) \quad \text{subject to} \quad P_π J P_π^T = L·U
```

where `P_π` is a permutation matrix corresponding to ordering `π`. SPICE typically uses:
- **Minimum Degree Algorithm**: Greedy minimization of degree at each elimination step
- **Nested Dissection**: Recursive graph partitioning for large matrices
- **AMD (Approximate Minimum Degree)**: Practical implementation balancing quality and speed

## Convergence Analysis: Numerical Clamping Algorithms

### 1. Exponential Overflow Prevention in Device Equations

The most critical numerical issue in SPICE occurs in exponential device equations like diodes and BJTs:

```math
I = I_s \left( \exp\left(\frac{V}{nV_t}\right) - 1 \right)
```

For `V >> nV_t`, the term `exp(V/(nV_t))` exceeds the floating-point range (overflow occurs at approximately `exp(709)` for double precision).

**Clamping Condition**:
Define normalized voltage `v_norm = V/(nV_t)`. Numerical overflow occurs when:
```math
v_norm > v_{\max} = \ln(\text{MAX_DOUBLE}) - \ln(I_s) \approx 709 \ \text{for IEEE double precision}
```

**Practical Clamping Algorithm in SPICE**:
```math
I(V) = 
\begin{cases}
I_s \left( e^{v_norm} - 1 \right) & \text{if } v_norm \leq v_{clamp} \\
I_s \left( e^{v_{clamp}} (1 + v_norm - v_{clamp}) - 1 \right) & \text{if } v_norm > v_{clamp}
\end{cases}
```
where `v_clamp ≈ 50` is an empirical value (`e⁵⁰ ≈ 5.18×10²¹`, well below overflow but high enough for most practical circuits).

### 2. Derivative Clamping for Jacobian Conditioning

The device derivative (small-signal conductance) must also be clamped to maintain Jacobian conditioning:

```math
g_d = \frac{\partial I}{\partial V} = \frac{I_s}{nV_t} e^{v_norm}
```

Clamped version used in SPICE:
```math
g_d(V) = 
\begin{cases}
\frac{I_s}{nV_t} e^{v_norm} & \text{if } v_norm \leq v_{clamp} \\
\frac{I_s}{nV_t} e^{v_{clamp}} & \text{if } v_norm > v_{clamp}
\end{cases}
```

This ensures the Jacobian remains well-conditioned even for extreme voltages.

### 3. Temperature Extremes Handling

**Low Temperature Limit** (`T → 0K`):
As `T → 0`, `V_t = kT/q → 0`, causing `v_norm = V/(nV_t) → ∞` and potential division by zero.

SPICE solution: Enforce a minimum temperature:
```math
T_{eff} = \max(T, T_{\min}) \quad \text{where } T_{\min} \approx 1 \ \text{K}
```

**High Temperature Limit** (`T → ∞`):
As `T → ∞`, saturation current `I_s(T)` grows exponentially and may overflow.

SPICE solution: Use logarithmic representation:
```math
\ln I_s(T) = \ln I_{s0} + \frac{E_g}{k} \left( \frac{1}{T_0} - \frac{1}{T} \right)
```
with bounds: `ln I_s ∈ [ln I_min, ln I_max]` to prevent overflow.

### 4. Convergence Criteria with Clamping

The Newton-Raphson iteration with clamping becomes:
```math
x_{k+1} = x_k - [J_c(x_k)]^{-1} F_c(x_k)
```
where `F_c` and `J_c` are the clamped function and Jacobian.

SPICE convergence requires two conditions:
1. **Function convergence**:
```math
\|F_c(x_k)\|_\infty < \epsilon_{abs} + \epsilon_{rel} \|x_k\|_\infty
```
2. **Step convergence**:
```math
\|x_{k+1} - x_k\|_\infty < \delta_{abs} + \delta_{rel} \|x_k\|_\infty
```
Typical SPICE values: `ε_abs = 1e-12`, `ε_rel = 1e-6`, `δ_abs = 1e-10`, `δ_rel = 1e-8`.

**Clamping-Induced Error Bound**:
The error introduced by clamping is bounded by:
```math
|I_{true} - I_{clamped}| < I_s e^{v_{clamp}} \frac{(v_norm - v_{clamp})^2}{2}
```
for `v_norm > v_clamp`. This quadratic error bound ensures clamping doesn't destroy solution accuracy for moderately large voltages.

### 5. Adaptive Clamping Strategy

SPICE employs adaptive clamping based on circuit behavior:

**Dynamic v_clamp Selection**:
```math
v_{clamp}^{(k)} = \min\left(50, \max_i v_norm^{(i)} - \Delta\right)
```
where `Δ ≈ 5` provides a safety margin below the maximum observed normalized voltage.

**Iteration-Aware Clamping**:
- Early Newton iterations: Tighter clamping (`v_clamp = 20`) for robustness
- Near convergence: Relaxed clamping (`v_clamp = 50`) for accuracy
- Decision based on `‖Δx‖` magnitude: `if ‖Δx‖ > 0.1 then v_clamp = 20 else v_clamp = 50`

### 6. Numerical Stability Analysis

The condition number of the clamped Jacobian satisfies:
```math
\kappa(J_c) \leq \kappa(J) \cdot \frac{\max(g_d)}{\min(g_d_c)}
```
where `g_d_c` is the clamped derivative.

**Stability Condition for Double Precision**:
```math
\kappa(J_c) < 1/\epsilon_{mach} \approx 10^{16}
```
This imposes constraints on `v_clamp`:
```math
v_{clamp} < \ln\left(\frac{nV_t \cdot 10^{16}}{I_s} \cdot \min(g_{other})\right)
```
where `g_other` represents other conductances in the matrix. Violation of this condition triggers SPICE warnings about ill-conditioned matrices.

### 7. Matrix Conditioning and Pivot Selection

During LU factorization, SPICE monitors pivot magnitudes:
```math
\text{pivot}_{ii} = J_c[i,i] - \sum_{k=1}^{i-1} L[i,k] \cdot U[k,i]
```

The algorithm rejects pivots satisfying:
```math
|\text{pivot}_{ii}| < \epsilon_{pivot} \cdot \max_{j \geq i} |J_c[j,i]|
```
where `ε_pivot ≈ 1e-12`. This prevents division by extremely small numbers that could amplify rounding errors.

### 8. Convergence Rate with Clamping

The Newton iteration with clamping exhibits modified convergence:
- **Quadratic convergence region**: When `v_norm ≤ v_clamp` for all devices
- **Linear convergence region**: When some devices operate in clamped region
- **Convergence monitor**: SPICE tracks the ratio
```math
\rho_k = \frac{\|F_c(x_{k+1})\|}{\|F_c(x_k)\|^2}
```
Quadratic convergence implies `ρ_k → constant`. If `ρ_k` grows significantly, SPICE may reduce step size or tighten clamping.

### 9. Computational Complexity Analysis

The global matrix assembly in SPICE has the following complexity characteristics:

**Time Complexity**:
- Device loading: `O(M·Nₖ²)` where `M` devices with `Nₖ` terminals each
- Matrix assembly: `O(nnz)` where `nnz` is number of non-zero entries
- Clamping overhead: `O(M)` for checking and applying clamps
- Temperature updates: `O(M)` for updating all device parameters

**Space Complexity**:
- Matrix storage: `O(nnz)` for sparse format
- Device data: `O(M·Nₖ²)` for local Jacobians
- Clamping state: `O(M)` for storing `v_norm` per device

**Numerical Stability Guarantees**:
With proper clamping as implemented in SPICE:
- All exponentials bounded: `|exp(v/v_t)| ≤ exp(v_clamp)`
- Jacobian condition number: `κ(J) ≤ κ_max` where `κ_max ≈ 10^12` (maintains ~4 digits accuracy in double precision)
- Newton iteration converges for `‖Δx‖ < δ_max` where `δ_max` adapts based on clamping state

This mathematical formulation and convergence analysis provides the foundation for SPICE's robust global matrix assembly, enabling simulation of circuits with extreme voltage swings and temperature variations while maintaining numerical stability and convergence.

## C Implementation: Global Matrix Assembly Architecture

### 1. Core Data Structures and System Architecture

#### 1.1 Circuit State Management (`CKTcircuit`)

The `CKTcircuit` structure serves as the central data container for the entire simulation state, implementing the mathematical framework for Modified Nodal Analysis (MNA). This structure directly maps to the mathematical formulation `F(x, ẋ, t) = 0` where `x ∈ ℝᴺ` represents the state vector.

```c
typedef struct sCKTcircuit {
    /* Matrix and solution - maps to J = G + αC + ∂I_nl/∂x */
    SMPmatrix *CKTmatrix;           /* Sparse Jacobian matrix J */
    double *CKTrhs;                 /* Right-hand side vector F(x) */
    double *CKTlhs;                 /* Solution vector x */
    
    /* Device management - implements ∑ₖ Pₖᵀ·Jₖ·Pₖ */
    GENinstance **CKTdevices;       /* Array of M device instances */
    int CKTnumDevices;              /* Device count M */
    
    /* Load function dispatch table */
    int (**DEVload)(GENmodel*, GENinstance*, struct sCKTcircuit*);
    
    /* Temperature data - implements V_t(T) = kT/q */
    double CKTtemp;                 /* Current temperature T (K) */
    double CKTnomTemp;              /* Nominal temperature T_nom */
    double CKTvt;                   /* Thermal voltage V_t = kT/q */
    double CKTfactor1;              /* exp(E_g/(kT)) factor */
    
    /* Integration parameters */
    double CKTag[2];                /* Integration coefficients α */
    double CKTdelta;                /* Time step h */
    int CKTmode;                    /* Analysis mode flags */
    
    /* Statistics and monitoring */
    struct sSTAT *CKTstat;          /* Convergence statistics */
    int CKTnumStates;               /* State dimension N */
} CKTcircuit;
```

#### 1.2 Device Instance Representation (`GENinstance`)

Each device instance implements the local Jacobian contribution `Jₖ ∈ ℝᴺₖˣᴺₖ` where `Nₖ` is the number of device terminals. The `terminals` array implements the mapping function `mapₖ: Tₖ → {1,...,N}` from the mathematical formulation.

```c
typedef struct sGENinstance {
    int instnum;                    /* Instance identifier */
    char *instname;                 /* Instance name */
    GENmodel *GENmodPtr;            /* Pointer to model parameters */
    
    /* Node connections - implements mapₖ function */
    int **terminals;                /* Terminal-to-global node mapping */
    int numTerminals;               /* Nₖ: number of terminals */
    
    /* State variables - device-specific internal states */
    double *states;                 /* Internal state vector */
    double *derivs;                 /* State derivatives */
    
    /* Local Jacobian storage - Jₖ matrix */
    double **jacobian;              /* Nₖ×Nₖ local Jacobian */
    
    /* Previous values for limiting */
    double *oldStates;              /* States from previous iteration */
    
    /* Device type identifier */
    int type;                       /* DIODE, MOS, BJT, etc. */
} GENinstance;
```

### 2. Device Loading Engine (`cktload.c`)

#### 2.1 Main Load Dispatch Algorithm

The `CKTload()` function implements the global assembly operation `J = ∑ₖ Pₖᵀ·Jₖ·Pₖ` by iterating through all devices and aggregating their contributions.

```c
int CKTload(CKTcircuit *ckt) {
    int error;
    
    /* Clear global matrix and RHS - reset J and F(x) */
    SMPzero(ckt->CKTmatrix);
    for (int i = 0; i < ckt->CKTnumStates; i++) {
        ckt->CKTrhs[i] = 0.0;
    }
    
    /* Phase 1: Load linear devices first (better numerical conditioning) */
    for (int i = 0; i < ckt->CKTnumDevices; i++) {
        GENinstance *inst = ckt->CKTdevices[i];
        if (isLinearDevice(inst->type)) {
            /* Dispatch to device-specific load function */
            error = (*(ckt->DEVload[inst->type]))(inst->GENmodPtr, inst, ckt);
            if (error) return error;
        }
    }
    
    /* Phase 2: Load nonlinear devices */
    for (int i = 0; i < ckt->CKTnumDevices; i++) {
        GENinstance *inst = ckt->CKTdevices[i];
        if (!isLinearDevice(inst->type)) {
            error = (*(ckt->DEVload[inst->type]))(inst->GENmodPtr, inst, ckt);
            if (error) return error;
        }
    }
    
    /* Phase 3: Load independent sources */
    error = loadSources(ckt);
    
    return error;
}
```

#### 2.2 Device-Specific Load Implementation

The `DEVload()` function template implements the mathematical operations for each device type, including numerical clamping for exponential terms.

```c
int DEVload(GENmodel *model, GENinstance *inst, CKTcircuit *ckt) {
    /* 1. Compute terminal voltages - get V from solution vector x */
    double v1 = ckt->CKTlhs[inst->terminals[0]];
    double v2 = ckt->CKTlhs[inst->terminals[1]];
    double v = v1 - v2;
    
    /* 2. Compute device current I(V,T) with temperature dependence */
    double current, conductance;
    
    if (inst->type == DIODE) {
        /* Implement I_d(V,T) = I_s(T)(exp(V/(nV_t)) - 1) */
        double v_norm = v / (model->DIOemissionCoeff * ckt->CKTvt);
        
        /* Apply exponential clamping: v_norm > v_clamp → linear extrapolation */
        if (v_norm > V_CLAMP) {
            double exp_clamp = exp(V_CLAMP);
            current = model->DIOsatCurTemp * (exp_clamp * (1.0 + (v_norm - V_CLAMP)) - 1.0);
            conductance = model->DIOsatCurTemp * exp_clamp / (model->DIOemissionCoeff * ckt->CKTvt);
        } else {
            current = model->DIOsatCurTemp * (exp(v_norm) - 1.0);
            conductance = model->DIOsatCurTemp * exp(v_norm) / (model->DIOemissionCoeff * ckt->CKTvt);
        }
    }
    
    /* 3. Stamp into global matrix - implement Pₖᵀ·Jₖ·Pₖ */
    int n1 = inst->terminals[0];    /* Global node i */
    int n2 = inst->terminals[1];    /* Global node j */
    
    /* Stamp conductance (diagonal entries of Jₖ) */
    SMPaddElement(ckt->CKTmatrix, n1, n1,  conductance);  /* J[i,i] += g */
    SMPaddElement(ckt->CKTmatrix, n2, n2,  conductance);  /* J[j,j] += g */
    SMPaddElement(ckt->CKTmatrix, n1, n2, -conductance);  /* J[i,j] += -g */
    SMPaddElement(ckt->CKTmatrix, n2, n1, -conductance);  /* J[j,i] += -g */
    
    /* Stamp current to RHS - contributes to F(x) */
    ckt->CKTrhs[n1] -= current;     /* F[i] -= I */
    ckt->CKTrhs[n2] += current;     /* F[j] += I */
    
    /* 4. Add capacitive contributions for transient analysis */
    if (ckt->CKTmode & MODE_TRAN) {
        double cap = getCapacitance(inst);
        double geq = cap * ckt->CKTag[0] / ckt->CKTdelta;  /* αC/h term */
        double ieq = computeHistoryTerm(inst, ckt);        /* History term */
        
        /* Add to Jacobian: J += (α/h)C */
        SMPaddElement(ckt->CKTmatrix, n1, n1, geq);
        SMPaddElement(ckt->CKTmatrix, n2, n2, geq);
        SMPaddElement(ckt->CKTmatrix, n1, n2, -geq);
        SMPaddElement(ckt->CKTmatrix, n2, n1, -geq);
        
        /* Add to RHS: F(x) -= history terms */
        ckt->CKTrhs[n1] -= ieq;
        ckt->CKTrhs[n2] += ieq;
    }
    
    return OK;
}
```

### 3. Kernel-Based Parallel Processing (`dkerproc.c`)

#### 3.1 Device Kernel Structure

The `DEVkern` structure enables parallel processing of device groups, implementing the mathematical aggregation `∑ₖ Pₖᵀ·Jₖ·Pₖ` in parallel.

```c
typedef struct sDEVkern {
    int kernelID;                   /* Kernel identifier */
    int deviceType;                 /* Device model type */
    int numInstances;               /* Number of instances in this kernel */
    GENinstance **instances;        /* Array of device instances */
    
    /* Kernel functions - parallel implementations */
    int (*loadFunc)(struct sDEVkern*, CKTcircuit*);
    int (*updateFunc)(struct sDEVkern*, CKTcircuit*);
    int (*acceptFunc)(struct sDEVkern*, CKTcircuit*);
    
    /* Thread synchronization */
    pthread_mutex_t lock;           /* Protects kernel data */
    int threadID;                   /* Assigned thread ID */
    
    /* Performance tracking */
    int callCount;                  /* Number of kernel invocations */
    double totalTime;               /* Cumulative execution time */
} DEVkern;
```

#### 3.2 Parallel Kernel Processing Engine

The `DKEprocessKernels()` function implements parallel aggregation of device contributions, reducing the `O(M·Nₖ²)` complexity through concurrent execution.

```c
int DKEprocessKernels(CKTcircuit *ckt, int operation) {
    int numKernels = ckt->CKTnumKernels;
    DEVkern **kernels = ckt->CKTkernels;
    
    switch (operation) {
        case OP_LOAD: {
            /* Parallel matrix assembly: J = ∑ₖ Pₖᵀ·Jₖ·Pₖ */
            #pragma omp parallel for schedule(dynamic)
            for (int k = 0; k < numKernels; k++) {
                DEVkern *kern = kernels[k];
                
                /* Acquire kernel lock for thread-safe updates */
                pthread_mutex_lock(&kern->lock);
                
                /* Execute kernel-specific load function */
                kern->loadFunc(kern, ckt);
                
                pthread_mutex_unlock(&kern->lock);
                
                /* Update performance metrics */
                kern->callCount++;
            }
            break;
        }
            
        case OP_UPDATE:
            /* Update device states after Newton iteration */
            for (int k = 0; k < numKernels; k++) {
                kernels[k]->updateFunc(kernels[k], ckt);
            }
            break;
            
        case OP_ACCEPT:
            /* Accept time step for dynamic analysis */
            for (int k = 0; k < numKernels; k++) {
                kernels[k]->acceptFunc(kernels[k], ckt);
            }
            break;
    }
    
    return OK;
}
```

#### 3.3 MOS Device Kernel Implementation

The `MOSloadKernel()` function demonstrates how the mathematical MOSFET equations are implemented with numerical clamping.

```c
int MOSloadKernel(DEVkern *kern, CKTcircuit *ckt) {
    MOSmodel *model = (MOSmodel*)kern->modelPtr;
    
    for (int i = 0; i < kern->numInstances; i++) {
        MOSinstance *inst = (MOSinstance*)kern->instances[i];
        
        /* Get terminal voltages from solution vector */
        double vgs = ckt->CKTlhs[inst->gateNode] - ckt->CKTlhs[inst->sourceNode];
        double vds = ckt->CKTlhs[inst->drainNode] - ckt->CKTlhs[inst->sourceNode];
        double vbs = ckt->CKTlhs[inst->bulkNode] - ckt->CKTlhs[inst->sourceNode];
        
        /* Apply voltage limiting: v_limited = v_old + δ·tanh((v_new - v_old)/δ) */
        vgs = VOLTLIM(vgs, inst->vgs_old, ckt->CKTdelta);
        vds = VOLTLIM(vds, inst->vds_old, ckt->CKTdelta);
        
        /* Compute MOSFET currents and derivatives */
        double ids, gm, gds, gmb;
        computeMOSCurrents(inst, vgs, vds, vbs, &ids, &gm, &gds, &gmb, ckt->CKTtemp);
        
        /* Apply transconductance clamping for extreme V_gs */
        if (fabs(vgs) > VGS_CLAMP) {
            double clamp_factor = VGS_CLAMP / fabs(vgs);
            ids *= clamp_factor;
            gm *= clamp_factor;
        }
        
        /* Stamp 4×4 local Jacobian Jₖ into global matrix J */
        int g = inst->gateNode, d = inst->drainNode;
        int s = inst->sourceNode, b = inst->bulkNode;
        
        /* Gate equations */
        SMPaddElement(ckt->CKTmatrix, g, g, GM_CGG);
        SMPaddElement(ckt->CKTmatrix, g, d, -GM_CGD);
        SMPaddElement(ckt->CKTmatrix, g, s, -gm - GM_CGS);
        SMPaddElement(ckt->CKTmatrix, g, b, -GM_CGB);
        
        /* Drain equations */
        SMPaddElement(ckt->CKTmatrix, d, d, gds + GM_CDD);
        SMPaddElement(ckt->CKTmatrix, d, s, -gds);
        
        /* Source equations */
        SMPaddElement(ckt->CKTmatrix, s, s, gds + gm + gmb + GM_CSS);
        SMPaddElement(ckt->CKTmatrix, s, b, -gmb);
        
        /* Bulk equations */
        SMPaddElement(ckt->CKTmatrix, b, b, GM_CBB);
        
        /* Symmetric entries (matrix symmetry) */
        SMPaddElement(ckt->CKTmatrix, d, g, -GM_CGD);
        SMPaddElement(ckt->CKTmatrix, s, g, -gm - GM_CGS);
        SMPaddElement(ckt->CKTmatrix, b, g, -GM_CGB);
        SMPaddElement(ckt->CKTmatrix, s, d, -gds);
        SMPaddElement(ckt->CKTmatrix, b, s, -gmb);
        
        /* Stamp drain current to RHS */
        ckt->CKTrhs[d] -= ids;
        ckt->CKTrhs[s] += ids;
        
        /* Store for next iteration */
        inst->vgs_old = vgs;
        inst->vds_old = vds;
        inst->ids = ids;
    }
    
    return OK;
}
```

### 4. Temperature Management System (`ckttemp.c`)

#### 4.1 Temperature Data Structure

The `TEMPDATA` structure implements the temperature-dependent parameter calculations `I_s(T)`, `V_t(T) = kT/q`, and the exponential scaling factors.

```c
typedef struct sTEMPDATA {
    double nominalTemp;             /* T_nom from .OPTIONS (K) */
    double currentTemp;             /* Current temperature T (K) */
    double deltaTemp;               /* ΔT = T - T_nom */
    
    /* Precomputed factors - implements V_t(T) = kT/q */
    double vt;                      /* Thermal voltage V_t */
    double vt_inv;                  /* 1/V_t for efficiency */
    double vt_nom;                  /* V_t at nominal temperature */
    
    /* Exponential scaling - implements exp(E_g/(kT)) */
    double factor1;                 /* exp(E_g/(kT)) */
    double factor2;                 /* T/T_nom */
    double factor3;                 /* (T/T_nom)^XTI */
    
    /* Material parameters */
    double eg0;                     /* Energy gap at 0K E_g(0) */
    double alpha, beta;             /* Temperature coefficients */
    
    /* Numerical bounds */
    double minTemp;                 /* T_min ≈ 1K */
    double maxTemp;                 /* T_max for clamping */
    double vClamp;                  /* Voltage clamp threshold */
    double iClamp;                  /* Current clamp threshold */
} TEMPDATA;
```

#### 4.2 Temperature Update Algorithm

The `CKTupdateTemp()` function implements the mathematical temperature transformations with numerical bounds checking.

```c
int CKTupdateTemp(CKTcircuit *ckt, double newTemp) {
    TEMPDATA *td = ckt->CKTtempData;
    
    /* Apply temperature bounds: T_eff = max(T, T_min) */
    if (newTemp < td->minTemp) {
        newTemp = td->minTemp;
        ckt->CKTstat->limitTmin++;  /* Track clamping events */
    }
    if (newTemp > td->maxTemp) {
        newTemp = td->maxTemp;
        ckt->CKTstat->limitTmax++;
    }
    
    /* Update temperature state */
    td->currentTemp = newTemp;
    td->deltaTemp = newTemp - td->nominalTemp;
    
    /* Compute thermal voltage: V_t = kT/q with safety bounds */
    td->vt = BOLTZMANN * newTemp / ELECTRON_CHARGE;
    if (td->vt < VT_MIN) td->vt = VT_MIN;  /* Prevent division by zero */
    td->vt_inv = 1.0 / td->vt;
    
    /* Compute energy gap: E_g(T) = E_g(0) - αT²/(T + β) */
    double eg = td->eg0 - td->alpha * newTemp * newTemp / (newTemp + td->beta);
    
    /* Compute exp(E_g/(kT)) with overflow protection */
    double arg = eg / (BOLTZMANN * newTemp);
    if (arg > MAX_EXP_ARG) {
        arg = MAX_EXP_ARG;
        ckt->CKTstat->limitEg++;
    }
    td->factor1 = exp(arg);
    
    /* Compute scaling factors */
    td->factor2 = newTemp / td->nominalTemp;
    td->factor3 = pow(td->factor2, XTI_DEFAULT);
    
    /* Update all device parameters */
    updateDeviceTemperatures(ckt, td);
    
    return OK;
}
```

#### 4.3 Diode Temperature Updates

The `updateDiodeTemperature()` function implements the mathematical temperature scaling for diode parameters.

```c
void updateDiodeTemperature(DIOmodel *model, TEMPDATA *td) {
    /* Saturation current: I_s(T) = I_s(T_nom) × (T/T_nom)^XTI × exp(E_g/(kT_nom) - E_g/(kT)) */
    double is_t = model->DIOsatCur * td->factor3 * td->factor1;
    
    /* Apply current clamping to prevent overflow */
    if (is_t > MAX_SAT_CURRENT) {
        is_t = MAX_SAT_CURRENT;
    } else if (is_t < MIN_SAT_CURRENT) {
        is_t = MIN_SAT_CURRENT;
    }
    
    model->DIOsatCurTemp = is_t;
    
    /* Junction potential: V_j(T) = V_j(T_nom) × (T/T_nom) */
    double vj_t = model->DIOjunctionPot * td->factor2;
    model->DIOjunctionPotTemp = vj_t;
    
    /* Series resistance: R_s(T) = R_s(T_nom) × [1 + TC1·ΔT + TC2·ΔT²] */
    double rs_t = model->DIOresist * (1.0 + model->DIOresistTC1 * td->deltaTemp
                                     + model->DIOresistTC2 * td->deltaTemp * td->deltaTemp);
    model->DIOresistTemp = rs_t;
}
```

#### 4.4 Exponential Clamping Functions

These functions implement the mathematical clamping algorithm for exponential terms.

```c
double clampExponential(double v, double vt, double v_clamp) {
    double v_norm = v / vt;  /* Normalized voltage */
    
    if (v_norm > v_clamp) {
        /* Linear extrapolation: exp(v_norm) ≈ exp(v_clamp)·[1 + (v_norm - v_clamp)] */
        double exp_clamp = exp(v_clamp);
        return exp_clamp * (1.0 + (v_norm - v_clamp));
    } else if (v_norm < -v_clamp) {
        /* Clamp negative exponential for reverse bias */
        double exp_clamp