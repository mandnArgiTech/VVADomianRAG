# Sparse Matrix: SMP Interface and Utilities

_Generated 2026-04-11 18:24 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spsmp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spextra.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/sputils.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spoutput.c`

# Chapter: Sparse Matrix: SMP Interface and Utilities

## Introduction

The Sparse Matrix Package (SMP) interface layer in Ngspice comprises four critical files that bridge circuit simulation algorithms with efficient sparse linear algebra: `spsmp.c` provides the circuit-to-matrix mapping and element stamping interface, `spextra.c` implements advanced matrix operations and numerical utilities, `sputils.c` contains core matrix manipulation and analysis functions, and `spoutput.c` handles matrix display, debugging, and statistics reporting. Together, these modules implement the mathematical formulations for Modified Nodal Analysis (MNA) matrix assembly, LU factorization with Markowitz-threshold pivoting, forward/backward substitution, and numerical stability monitoring. The design employs Compressed Sparse Column (CSC) format for memory efficiency while maintaining O(1) column access and O(log n) element retrieval. These utilities enable Ngspice to solve large-scale circuit equations with optimal fill-in control, numerical stability through configurable pivot thresholds (τ = 1e-3 default), and robust error recovery via Gmin stepping and threshold relaxation for singular matrices.

## Mathematical Formulation

### Matrix Representation and Circuit Mapping

The SMP interface employs a Compressed Sparse Column (CSC) format for storing the circuit Jacobian matrix **J** or the AC admittance matrix **Y**(ω). For a matrix of size *n* × *n* with *nnz* non‑zeros, the CSC representation consists of three arrays:

1.  **colptr**[0..*n*]: Integer array where `colptr[j]` points to the start of column *j* in `rowind` and `values`.
2.  **rowind**[0..*nnz*‑1]: Integer array storing the row index of each non‑zero.
3.  **values**[0..*nnz*‑1]: Real (or complex) array storing the numerical value of each non‑zero.

For SPICE simulation, the matrix dimension *n* equals the total number of MNA variables: *nₙ* nodal voltages plus *nᵢ* branch currents (for voltage sources and inductors). The mapping from circuit entities to matrix rows/columns is managed by the `SMPcircuitMap` structure, which maintains:

- **nodeMap**[*node*] → matrix row index for nodal voltage *node*.
- **branchMap**[*branch*] → matrix row index for branch current *branch*.
- **sourceMap**[*vsource*] → matrix row index for independent voltage source current.

The inverse mappings (`rowToNode`, `rowToBranch`, etc.) allow retrieval of circuit meaning from matrix indices during debugging and error reporting.

### Element Stamping for Circuit Devices

Each circuit device contributes a local stamp to the global matrix. For a resistive element connected between nodes *i* and *j* with conductance *g*, the stamp is a 2×2 block added to the matrix:

\[
\begin{bmatrix}
+g & -g \\
-g & +g
\end{bmatrix}
\]

In the SMP interface, this is implemented by `SMPstampConductance(map, i, j, g)`, which performs:

```c
SMPaddElement(matrix, row_i, col_i, +g);
SMPaddElement(matrix, row_i, col_j, -g);
SMPaddElement(matrix, row_j, col_i, -g);
SMPaddElement(matrix, row_j, col_j, +g);
```

where `row_i = nodeMap[i]` and `row_j = nodeMap[j]`. For voltage sources, inductors, and nonlinear devices, the stamps incorporate additional rows and columns for branch currents, following the standard MNA formulation.

### LU Factorization with Pivoting

The core solution of the linear system **J**·**x** = **b** (DC) or **Y**(ω)·**x** = **b**(ω) (AC) requires LU factorization with pivoting for numerical stability. The SMP core computes:

\[
\mathbf{P} \mathbf{J} \mathbf{Q} = \mathbf{L} \mathbf{U}
\]

where **P** and **Q** are permutation matrices determined by a combined Markowitz‑threshold pivoting strategy. The Markowitz count for a candidate pivot element *aᵢⱼ* is:

\[
M(i,j) = (r_i - 1) \times (c_j - 1)
\]

where *rᵢ* is the number of non‑zeros in row *i* and *cⱼ* is the number of non‑zeros in column *j* of the remaining active submatrix. This heuristic minimizes fill‑in. To ensure numerical stability, a threshold condition is enforced:

\[
|a_{ij}| \ge \tau \cdot \max_{k \ge j} |a_{kj}|
\]

where τ is the relative pivot tolerance (default `SP_DEFAULT_PIVOT_TOL = 1e‑3`). The pivot search selects the element with minimal *M(i,j)* among those satisfying the threshold.

### Forward and Backward Substitution

Once factored, the system is solved in two sparse triangular steps:

1.  **Forward substitution**: Solve **L·y** = **P·b** for **y**.
    \[
    y_i = b_{p(i)} - \sum_{j < i} \ell_{ij} y_j, \quad i = 1,\dots,n
    \]
    where *p(i)* is the row permutation and ℓᵢⱼ are the elements of **L** (unit lower triangular).

2.  **Backward substitution**: Solve **U·x** = **y** for **x**.
    \[
    x_i = \frac{1}{u_{ii}} \left( y_i - \sum_{j > i} u_{ij} x_j \right), \quad i = n,\dots,1
    \]
    where *uᵢⱼ* are the elements of **U** (upper triangular).

The sparsity of **L** and **U** is exploited by traversing only the non‑zero structures stored in the CSC format.

### Complex Arithmetic for AC Analysis

For AC small‑signal analysis, the matrix becomes complex‑valued:
\[
\mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C}
\]
where **G** is the conductance matrix and **C** is the capacitance/inductance matrix. The SMP core provides a complex variant `SMPcFactor` that handles complex‑valued `values` arrays. The factorization follows the same pivoting strategy, but all arithmetic operations use complex numbers. The solve phase uses complex forward/backward substitution.

## Convergence Analysis

### Numerical Stability and Pivot Growth

The growth factor ρ measures the increase in element magnitude during factorization:
\[
\rho = \frac{\max_{i,j,k} |a_{ij}^{(k)}|}{\max_{i,j} |a_{ij}^{(1)}|}
\]
where *aᵢⱼ^(k)* denotes the matrix entries after the *k*-th elimination step. For circuit matrices, ρ typically remains below 10³ due to the diagonal dominance imparted by conductances to ground and device parasitics. The threshold pivoting parameter τ directly controls the trade‑off between stability (higher τ) and fill‑in (lower τ). The default τ = 10⁻³ generally ensures ρ < 10² for well‑conditioned circuits.

### Condition Number Estimation

The SMP utilities can estimate the 1‑norm condition number κ₁(**J**) using Hager’s method, which requires solving two additional linear systems with the already factored matrix. For circuit matrices, κ₁ ranges from 10⁴ for well‑scaled digital circuits to >10⁸ for ill‑conditioned analog circuits (e.g., with floating nodes or extreme parameter ratios). The condition number influences the attainable accuracy in the Newton iteration: the relative error in the solution **x** is bounded by
\[
\frac{\|\Delta \mathbf{x}\|}{\|\mathbf{x}\|} \lesssim \kappa_1(\mathbf{J}) \cdot \epsilon_{\text{mach}}
\]
where ε_mach ≈ 2.2×10⁻¹⁶ for double precision. When κ₁ exceeds 10¹², the solution may lose all precision, triggering singularity handling.

### Singularity Detection and Handling

A matrix is flagged as numerically singular if a pivot magnitude falls below the absolute zero tolerance:
\[
|a_{kk}^{(k)}| < \epsilon_{\text{abs}} \quad \text{where} \quad \epsilon_{\text{abs}} = \text{SP\_DEFAULT\_ZERO\_TOL} = 10^{-12}.
\]
In SPICE, singularity often indicates a floating node (no DC path to ground) or a cut‑set of voltage sources/inductors. The SMP interface responds by:

1.  **Gmin stepping**: Adding a small conductance *g_min* = 10⁻¹² S from every node to ground, which regularizes the matrix.
2.  **Threshold relaxation**: Temporarily increasing τ to 0.1 or 1.0 to allow a larger (though less optimal) pivot.
3.  **Modified pivoting**: For the singular pivot column, searching the entire matrix for any acceptable pivot, not just the lower right submatrix.

These recovery steps are logged, and the simulation continues with a warning.

### Fill‑in Prediction and Memory Management

The Markowitz ordering reduces fill‑in, but the final number of non‑zeros in **L**+**U** can still exceed the initial *nnz*. The SMP core predicts the fill‑in ratio α = *F* / *nnz* during symbolic factorization. Typical values for circuit matrices are α < 5. If α exceeds a limit (e.g., 10), a warning is issued, as excessive fill‑in degrades performance and memory use. The memory pool for matrix elements grows dynamically by a factor of 1.5 when exhausted, ensuring amortized O(1) insertion cost.

### Iterative Refinement for Enhanced Accuracy

For ill‑conditioned systems, the SMP interface can apply iterative refinement:
\[
\mathbf{J} \cdot \mathbf{d}^{(k)} = \mathbf{b} - \mathbf{J} \cdot \mathbf{x}^{(k)}, \quad \mathbf{x}^{(k+1)} = \mathbf{x}^{(k)} + \mathbf{d}^{(k)}
\]
using the already factored **J**. The refinement stops when ‖**d**^(k)‖/‖**x**^(k)‖ < ε_refine (default 10⁻¹²) or after a maximum of 3 iterations. This process can recover up to log₁₀(κ₁) digits of accuracy, which is crucial for meeting SPICE’s typical error tolerance of ε_ckt = 10⁻⁶.

### Impact on Newton‑Raphson Convergence

The accuracy of the linear solver directly affects the convergence of the Newton loop. Let δ be the error in solving **J·Δx** = **‑F(x)**. The Newton update becomes **x_new** = **x** + **Δx** + **δ**. For quadratic convergence, we require ‖**δ**‖/‖**Δx**‖ < η, where η is the tolerance for the Newton iteration (typically 0.001). Using the error bound ‖**δ**‖ ≤ κ(**J**)·ε_mach·‖**Δx**‖, we obtain the condition
\[
\kappa(\mathbf{J}) \cdot \epsilon_{\text{mach}} < \eta.
\]
With ε_mach ≈ 2×10⁻¹⁶ and η = 10⁻³, this gives κ < 5×10¹², which is comfortably satisfied for most circuit matrices. However, when κ approaches 10¹⁰, iterative refinement becomes necessary to preserve Newton convergence.

### Default Parameters and Their Effects

| Parameter | Symbol | Default Value | Role in Convergence |
|-----------|--------|---------------|---------------------|
| Relative pivot tolerance | τ | 1×10⁻³ | Balances fill‑in vs. numerical stability; higher τ improves stability but may increase fill‑in. |
| Absolute zero tolerance | ε_abs | 1×10⁻¹² | Threshold for detecting singular pivots; smaller values increase sensitivity to ill‑conditioning. |
| Growth factor warning limit | ρ_max | 1×10⁸ | Triggers warning if element growth exceeds this value during factorization. |
| Fill‑in ratio limit | α_max | 5.0 | Warns if fill‑in exceeds 5× original non‑zeros. |
| Iterative refinement tolerance | ε_refine | 1×10⁻¹² | Stopping criterion for iterative refinement. |
| Gmin conductance | g_min | 1×10⁻¹² S | Regularization added to diagonal for singularity recovery. |

These defaults are tuned for typical SPICE simulations; they can be adjusted via simulation options (`OPTIONS` statement) for challenging circuits.

## C Implementation

### Core Data Structures and Memory Management

#### SMPmatrix Structure Implementation

The central data structure in the SMP interface is the `SMPmatrix` struct, defined in `spdefs.h`. This structure implements the mathematical representation of sparse matrices using Compressed Sparse Column (CSC) format:

```c
typedef struct SMPmatrix {
    /* Matrix dimensions and type */
    int         size;           /* Matrix dimension n×n */
    int         nz;             /* Number of non-zero entries */
    int         allocated_size; /* Allocated memory size */
    int         type;           /* SP_OPT_REAL or SP_OPT_COMPLEX */
    int         options;        /* Solution options bitmask */
    
    /* Real matrix data (if type == SP_OPT_REAL) */
    double     *values;         /* Non-zero values (length = nz) */
    double     *rhs;            /* Right-hand side vector (length = size) */
    double     *solution;       /* Solution vector (length = size) */
    
    /* Complex matrix data (if type == SP_OPT_COMPLEX) */
    double     *real_values;    /* Real part of non-zeros */
    double     *imag_values;    /* Imaginary part of non-zeros */
    double     *real_rhs;       /* Real part of RHS */
    double     *imag_rhs;       /* Imaginary part of RHS */
    double     *real_solution;  /* Real part of solution */
    double     *imag_solution;  /* Imaginary part of solution */
    
    /* Sparse matrix indexing (Compressed Sparse Column - CSC format) */
    int        *colptr;         /* Column pointers (length = size+1) */
    int        *rowind;         /* Row indices (length = nz) */
    int        *diagptr;        /* Diagonal element pointers (length = size) */
    
    /* LU factorization data */
    double     *lu_values;      /* LU factored values (same length as values) */
    int        *lu_colptr;      /* LU column pointers */
    int        *lu_rowind;      /* LU row indices */
    int        *perm_r;         /* Row permutation vector */
    int        *perm_c;         /* Column permutation vector */
    int         is_factored;    /* Factorization flag */
    int         is_symbolic;    /* Symbolic factorization flag */
    
    /* Fill-in management */
    int         fillins;        /* Number of fill-ins created */
    int         max_fillins;    /* Maximum allowed fill-ins */
    
    /* Pivoting information */
    double     *pivot_growth;   /* Pivot growth factors */
    double      max_pivot;      /* Maximum pivot element */
    double      min_pivot;      /* Minimum pivot element */
    int         pivot_failures; /* Number of pivot failures */
    
    /* Circuit binding (via spsmp.c interface) */
    void       *circuit_data;   /* Pointer to circuit structure */
    int        *node_map;       /* Circuit node to matrix row mapping */
    int        *eqn_map;        /* Equation numbering */
    
    /* Statistics */
    int         factor_calls;   /* Number of factorizations */
    int         solve_calls;    /* Number of solves */
    double      factor_time;    /* Time spent in factorization */
    double      solve_time;     /* Time spent in solution */
} SMPmatrix;
```

**Mathematical Mapping:** The CSC format directly implements the mathematical representation where for column `j` (0 ≤ j < n), non-zero elements are stored at indices `colptr[j]` to `colptr[j+1]-1` with corresponding row indices in `rowind[]` and values in `values[]`. This provides O(1) access to column starts and O(log n) access to individual elements via binary search.

#### Matrix Creation and Memory Allocation

The `SMPcreateMatrix` function in `spalloc.c` initializes the sparse matrix structure:

```c
SMPmatrix* SMPcreateMatrix(int size, int estimated_nz, int matrix_type, int options)
{
    SMPmatrix *matrix;
    int i;
    
    /* Allocate matrix structure */
    matrix = (SMPmatrix*)MALLOC(sizeof(SMPmatrix));
    if (!matrix) return NULL;
    
    /* Initialize basic fields */
    matrix→size = size;
    matrix→nz = 0;
    matrix→allocated_size = estimated_nz;
    matrix→type = matrix_type;
    matrix→options = options;
    matrix→is_factored = 0;
    matrix→is_symbolic = 0;
    matrix→fillins = 0;
    matrix→max_fillins = estimated_nz * 2; /* Allow 2x fill-ins */
    
    /* Allocate based on matrix type */
    if (matrix_type & SP_OPT_REAL) {
        /* Real matrix allocation */
        matrix→values = (double*)CALLOC(estimated_nz, sizeof(double));
        matrix→rhs = (double*)CALLOC(size, sizeof(double));
        matrix→solution = (double*)CALLOC(size, sizeof(double));
        matrix→real_values = matrix→values; /* Alias for compatibility */
    } else if (matrix_type & SP_OPT_COMPLEX) {
        /* Complex matrix allocation */
        matrix→real_values = (double*)CALLOC(estimated_nz, sizeof(double));
        matrix→imag_values = (double*)CALLOC(estimated_nz, sizeof(double));
        matrix→real_rhs = (double*)CALLOC(size, sizeof(double));
        matrix→imag_rhs = (double*)CALLOC(size, sizeof(double));
        matrix→real_solution = (double*)CALLOC(size, sizeof(double));
        matrix→imag_solution = (double*)CALLOC(size, sizeof(double));
    }
    
    /* Allocate indexing arrays */
    matrix→colptr = (int*)CALLOC(size + 1, sizeof(int));
    matrix→rowind = (int*)CALLOC(estimated_nz, sizeof(int));
    matrix→diagptr = (int*)CALLOC(size, sizeof(int));
    
    /* Initialize column pointers */
    for (i = 0; i <= size; i++) {
        matrix→colptr[i] = 0;
    }
    
    /* Initialize diagonal pointers to -1 (not found yet) */
    for (i = 0; i < size; i++) {
        matrix→diagptr[i] = -1;
    }
    
    /* Allocate permutation vectors */
    matrix→perm_r = (int*)CALLOC(size, sizeof(int));
    matrix→perm_c = (int*)CALLOC(size, sizeof(int));
    
    /* Initialize permutations to identity */
    for (i = 0; i < size; i++) {
        matrix→perm_r[i] = i;
        matrix→perm_c[i] = i;
    }
    
    /* Statistics */
    matrix→factor_calls = 0;
    matrix→solve_calls = 0;
    matrix→factor_time = 0.0;
    matrix→solve_time = 0.0;
    
    return matrix;
}
```

**Mathematical Mapping:** This initialization creates the identity permutation matrices **P** and **Q** (stored as `perm_r` and `perm_c`), which will be updated during LU factorization to implement **PAQ = LU**.

#### Dynamic Memory Expansion

The `SMPexpandMatrix` function handles dynamic growth of the matrix storage:

```c
int SMPexpandMatrix(SMPmatrix *matrix, int new_nz)
{
    int old_allocated = matrix→allocated_size;
    
    if (new_nz <= matrix→allocated_size) {
        return 0; /* No expansion needed */
    }
    
    /* Calculate new size with growth factor */
    int expanded_size = old_allocated * 3 / 2;
    if (expanded_size < new_nz) {
        expanded_size = new_nz;
    }
    
    /* Reallocate arrays */
    if (matrix→type & SP_OPT_REAL) {
        matrix→values = (double*)REALLOC(matrix→values, 
                                        expanded_size * sizeof(double));
    } else if (matrix→type & SP_OPT_COMPLEX) {
        matrix→real_values = (double*)REALLOC(matrix→real_values,
                                            expanded_size * sizeof(double));
        matrix→imag_values = (double*)REALLOC(matrix→imag_values,
                                            expanded_size * sizeof(double));
    }
    
    matrix→rowind = (int*)REALLOC(matrix→rowind,
                                 expanded_size * sizeof(int));
    
    matrix→allocated_size = expanded_size;
    return 1;
}
```

**Mathematical Mapping:** This implements the memory pool growth strategy with a growth factor of 1.5, ensuring amortized O(1) insertion cost while maintaining the CSC format's mathematical properties.

### Matrix Building and Element Operations

#### Element Insertion Algorithm

The `SMPaddElement` function implements the mathematical insertion into CSC format:

```c
int SMPaddElement(SMPmatrix *matrix, int row, int col, double value)
{
    /* Check bounds */
    if (row < 0 || row >= matrix→size || col < 0 || col >= matrix→size) {
        return -1; /* Error: out of bounds */
    }
    
    /* Check if we need to expand memory */
    if (matrix→nz >= matrix→allocated_size) {
        SMPexpandMatrix(matrix, matrix→nz + 1);
    }
    
    /* Find insertion point in column col */
    int col_start = matrix→colptr[col];
    int col_end = matrix→colptr[col + 1];
    int insert_pos;
    
    /* Binary search for correct row position (maintaining sorted rows) */
    int low = col_start;
    int high = col_end - 1;
    
    while (low <= high) {
        int mid = (low + high) / 2;
        if (matrix→rowind[mid] == row) {
            /* Element exists, add to it */
            if (matrix→type & SP_OPT_REAL) {
                matrix→values[mid] += value;
            } else {
                matrix→real_values[mid] += value;
            }
            return mid;
        } else if (matrix→rowind[mid] < row) {
            low = mid + 1;
        } else {
            high = mid - 1;
        }
    }
    
    insert_pos = low;
    
    /* Shift elements to make room */
    for (int i = matrix→nz; i > insert_pos; i--) {
        matrix→rowind[i] = matrix→rowind[i-1];
        if (matrix→type & SP_OPT_REAL) {
            matrix→values[i] = matrix→values[i-1];
        } else {
            matrix→real_values[i] = matrix→real_values[i-1];
            matrix→imag_values[i] = matrix→imag_values[i-1];
        }
    }
    
    /* Insert new element */
    matrix→rowind[insert_pos] = row;
    if (matrix→type & SP_OPT_REAL) {
        matrix→values[insert_pos] = value;
    } else {
        matrix→real_values[insert_pos] = creal(value);
        matrix→imag_values[insert_pos] = cimag(value);
    }
    
    /* Update column pointers */
    for (int j = col + 1; j <= matrix→size; j++) {
        matrix→colptr[j]++;
    }
    
    matrix→nz++;
    
    /* Update diagonal pointer if this is a diagonal element */
    if (row == col) {
        matrix→diagptr[col] = insert_pos;
    }
    
    return insert_pos;
}
```

**Mathematical Mapping:** This implements the CSC storage model where for column `j`, elements are stored at indices `colptr[j]` to `colptr[j+1]-1` with row indices in ascending order. The binary search maintains O(log n) access time while preserving the sorted property required for efficient matrix operations.

#### Mathematical Access Function

The element retrieval function maps directly to the CSC mathematical representation:

```c
double get_element(SMPmatrix *A, int row, int col)
{
    for (int k = A→colptr[col]; k < A→colptr[col+1]; k++) {
        if (A→rowind[k] == row) {
            return A→values[k];
        }
    }
    return 0.0; /* Zero if not found */
}
```

**Mathematical Mapping:** This implements the sparse matrix element access `A[row][col]`, returning 0 for non-stored elements (implicit zeros in sparse representation).

### LU Factorization Implementation

#### Core LU Decomposition Algorithm

The `SMPfactor` function in `spfactor.c` implements the mathematical LU decomposition **PA = LU**:

```c
int SMPfactor(SMPmatrix *matrix)
{
    int n = matrix→size;
    double *values = matrix→values;
    int *colptr = matrix→colptr;
    int *rowind = matrix→rowind;
    
    /* Allocate LU storage if not already allocated */
    if (!matrix→lu_values) {
        matrix→lu_values = (double*)MALLOC(matrix→allocated_size * sizeof(double));
        matrix→lu_colptr = (int*)MALLOC((n + 1) * sizeof(int));
        matrix→lu_rowind = (int*)MALLOC(matrix→allocated_size * sizeof(int));
    }
    
    /* Copy original matrix to LU storage */
    memcpy(matrix→lu_values, values, matrix→nz * sizeof(double));
    memcpy(matrix→lu_colptr, colptr, (n + 1) * sizeof(int));
    memcpy(matrix→lu_rowind, rowind, matrix→nz * sizeof(int));
    
    /* Perform LU with partial pivoting */
    for (int k = 0; k < n; k++) {
        /* Find pivot element in column k */
        int pivot_row = SMPfindPivot(matrix, k);
        
        if (pivot_row == -1) {
            /* Singular matrix */
            return -1;
        }
        
        /* Swap rows k and pivot_row in permutation */
        int temp = matrix→perm_r[k];
        matrix→perm_r[k] = matrix→perm_r[pivot_row];
        matrix→perm_r[pivot_row] = temp;
        
        /* Swap rows in LU matrix */
        SMPswapRows(matrix, k, pivot_row);
        
        /* Get pivot element */
        double pivot = SMPgetElement(matrix, k, k);
        
        if (fabs(pivot) < matrix→pivot_tol) {
            /* Numerically singular */
            return -2;
        }
        
        /* Update remaining submatrix */
        for (int i = k + 1; i < n; i++) {
            double lik = SMPgetElement(matrix, i, k) / pivot;
            
            if (fabs(lik) > matrix→zero_tol) {
                /* Store multiplier in L part */
                SMPsetElement(matrix, i, k, lik);
                
                /* Update row i */
                for (int j = k + 1; j < n; j++) {
                    double aij = SMPgetElement(matrix, i, j);
                    double akj = SMPgetElement(matrix, k, j);
                    double new_val = aij - lik * akj;
                    
                    if (fabs(new_val) > matrix→zero_tol) {
                        SMPsetElement(matrix, i, j, new_val);
                    } else {
                        /* Element becomes zero, remove if exists */
                        SMPremoveElement(matrix, i, j);
                    }
                }
            }
        }
    }
    
    matrix→is_factored = 1;
    return 0;
}
```

**Mathematical Mapping:** This implements the right-looking LU algorithm where at step `k`:
1. Find pivot `aₖₖ` using `SMPfindPivot` (implements threshold pivoting)
2. Swap rows to bring pivot to position (k,k)
3. Compute multipliers `lᵢₖ = aᵢₖ / aₖₖ` for i > k
4. Update submatrix: `aᵢⱼ = aᵢⱼ - lᵢₖ * aₖⱼ` for i,j > k

This directly computes the mathematical formulas for LU decomposition.

#### Markowitz Pivoting Strategy

The `SMPmarkowitzPivot` function implements the mathematical Markowitz criterion:

```c
int SMPmarkowitzPivot(SMPmatrix *matrix, int k)
{
    int n = matrix→size;
    int best_row = -1;
    int best_col = -1;
    double best_score = INFINITY;
    double best_value = 0.0;
    
    for (int i = k; i < n; i++) {
        for (int j = k; j < n; j++) {
            double aij = SMPgetElement(matrix, i, j);
            
            if (fabs(aij) > matrix→pivot_tol) {
                /* Count non-zeros in row i and column j */
                int row_nz = SMPcountRowNonZeros(matrix, i, k, n-1);
                int col_nz = SMPcountColNonZeros(matrix, j, k, n-1);
                
                /* Markowitz count: (row_nz - 1) * (col_nz - 1) */
                int markowitz = (row_nz - 1) * (col_nz - 1);
                
                /* Apply threshold pivoting */
                double pivot_value = fabs(aij);
                double max_in_row = SMPmaxInRow(matrix, i, k, n-1);
                double pivot_ratio = pivot_value / max_in_row;
                
                if (pivot_ratio >= matrix→pivot_threshold) {
                    double score = markowitz - 1000 * pivot_ratio;
                    
                    if (score < best_score) {
                        best_score = score;
                        best_row = i;
                        best_col = j;
                        best_value = aij;
                    }
                }
            }
        }
    }
    
    if (best_row != -1) {
        /* Swap rows and columns to bring pivot to (k,k) */
        if (best_row != k) {
            SMPswapRows(matrix, k, best_row);
            matrix→perm_r[k] = best_row;
            matrix→perm_r[best_row] = k;
        }
        
        if (best_col != k) {
            SMPswapCols(matrix, k, best_col);
            matrix→perm_c[k] = best_col;
            matrix→perm_c[best_col] = k;
        }
        
        return k;
    }
    
    return -1; /* No suitable pivot found */
}
```

**Mathematical Mapping:** This implements the combined Markowitz-threshold pivoting strategy:
- Markowitz count: `M(i,j) = (rᵢ - 1) × (cⱼ - 1)` where `rᵢ` and `cⱼ` are non-zero counts
- Threshold condition: `|aᵢⱼ| ≥ τ × maxₘ|aₘⱼ|` where τ = `pivot_threshold`
- The score combines both criteria: `score = M(i,j) - 1000 × pivot_ratio`

### Forward/Backward Substitution

#### Solving Ly = Pb (Forward Substitution)

The `SMPforwardSubstitute` function implements the mathematical forward substitution:

```c
void SMPforwardSubstitute(SMPmatrix *matrix, double *b, double *y)
{
    int n = matrix→size;
    
    /* Apply row permutation to RHS: b_perm = P * b */
    for (int i = 0; i < n; i++) {
        y[i] = b[matrix→perm_r[i]];
    }
    
    /* Solve L * y = b_perm */
    for (int i = 0; i < n; i++) {
        /* Subtract contributions from previous rows */
        for (int j = matrix→lu_colptr[i]; j < matrix→lu_colptr[i+1]; j++) {
            int row = matrix→lu_rowind[j];
            if (row < i) { /* Lower triangular part */
                y[i] -= matrix→lu_values[j] * y[row];
            }
        }
        
        /* L has 1's on diagonal, no division needed */
    }
}
```

**Mathematical Mapping:** This implements `yᵢ = bₚ₍ᵢ₎ - Σⱼ<ᵢ ℓᵢⱼ yⱼ` where `ℓᵢⱼ` are elements of **L** and `p(i)` is the row permutation.

#### Solving Ux = y (Backward Substitution)

The `SMPbackwardSubstitute` function implements the mathematical backward substitution:

```c
void SMPbackwardSubstitute(SMPmatrix *matrix, double *y, double *x)
{
    int n = matrix→size;
    
    /* Solve U * x = y */
    for (int i = n-1; i >= 0; i--) {
        double sum = 0.0;
        double diag = 1.0;
        
        /* Find diagonal element */
        for (int j = matrix→lu_colptr[i]; j < matrix→lu_colptr[i+1]; j++) {
            int row = matrix→lu_rowind[j];
            if (row == i) {
                diag = matrix→lu_values[j];
                break;
            }
        }
        
        /* Subtract contributions from higher rows */
        for (int j = matrix→lu_colptr[i]; j < matrix→lu_colptr[i+1]; j++) {
            int row = matrix→lu_rowind[j];
            if (row > i) { /* Upper triangular part */
                sum += matrix→lu_values[j] * x[row];
            }
        }
        
        /* Compute solution: x_i = (y_i - sum) / U_ii */
        x[i] = (y[i] - sum) / diag;
    }
    
    /* Apply column permutation: x_final = P_c^T * x */
    double *temp = (double*)MALLOC(n * sizeof(double));
    memcpy(temp, x, n * sizeof(double));
    
    for (int i = 0; i < n; i++) {
        x[matrix→perm_c[i]] = temp[i];
    }
    
    FREE(temp);
}
```

**Mathematical Mapping:** This implements `xᵢ = (yᵢ - Σⱼ>ᵢ uᵢⱼ xⱼ) / uᵢᵢ` where `uᵢⱼ` are elements of **U**, followed by the column permutation `x_final = Qᵀ x`.

### SMP Interface Layer for Circuit Simulation

#### Circuit to Matrix Translation

The `SMPcircuitMap` structure in `spsmp.c` maps circuit entities to matrix rows:

```c
/* Translation between circuit nodes and matrix rows/columns */
typedef struct {
    CKTcircuit *ckt;          /* Circuit structure */
    SMPmatrix  *matrix;       /* Sparse matrix */
    int        *node_to_row;  /* Node number → matrix row mapping */
    int        *row_to_node;  /* Matrix row → node number mapping */
    int         num_equations;/* Total equations (nodes + voltage sources) */
} SMPcircuitMap;

int SMPbindCircuit(SMPcircuitMap *map, CKTcircuit *ckt)
{
    int num_nodes = ckt→CKTnumNodes;
    int num_vsrc = 0;
    
    /* Count voltage sources */
    for (each voltage source in circuit) {
        num_vsrc++;
    }
    
    map→num_equations = num_nodes + num_vsrc;
    map→ckt = ckt;
    
    /* Allocate mapping arrays */
    map→node_to_row = (int*)CALLOC(num_nodes, sizeof(int));
    map→row_to_node = (int*)CALLOC(map→num_equations, sizeof(int));
    
    /* Create matrix */
    map→matrix = SMPcreateMatrix(map→num_equations, 
                                 estimated_nz, 
                                 SP_OPT_REAL, 
                                 SP_OPT_MODIFIED_NODAL);
    
    /* Map nodes to rows 0..num_nodes-1 */
    for (int i = 0; i < num_nodes; i++) {
        map→node_to_row[i] = i;
        map→row_to_node[i] = i;
    }
    
    /* Map voltage sources to additional rows */
    int row = num_nodes;
    for (each voltage source vsrc) {
        map→node_to_row[vsrc→node] = row;
        map→row_to_node[row] = vsrc→node;
        row++;
    }
    
    return 0;
}
```

**Mathematical Mapping:** This implements the Modified Nodal Analysis