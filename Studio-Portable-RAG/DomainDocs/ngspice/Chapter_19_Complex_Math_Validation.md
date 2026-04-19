# Complex Mathematics: Validation and Edge Cases

_Generated 2026-04-11 18:57 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/cmaths/test_cx_mag.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/cmaths/test_cx_ph.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/cmaths/test_cx_cph.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/cmaths/test_cx_j.c`

# Chapter: Complex Mathematics: Validation and Edge Cases

## Introduction

This chapter details the validation framework and edge-case handling for complex number operations within the Ngspice Sparse Matrix Package (SMP). Robust validation is critical for ensuring the numerical stability and reliability of AC, transient, and sensitivity analyses in circuit simulation. The core validation suite consists of four specialized test files: `test_cx_mag.c`, `test_cx_ph.c`, `test_cx_cph.c`, and `test_cx_j.c`. These files systematically verify the correctness, accuracy, and boundary behavior of fundamental complex arithmetic operations—magnitude, phase, complex power, and the imaginary unit `j`—against known mathematical identities and under extreme numerical conditions (e.g., overflow, underflow, and branch cuts). Their execution is integral to the Ngspice build process, guaranteeing that the underlying mathematical primitives used to construct and solve complex linear systems \( \mathbf{Y}(\omega)\mathbf{V}(\omega) = \mathbf{I}(\omega) \) are functionally correct before they are deployed in production circuit simulation.

## Mathematical Formulation

### Sparse Matrix Representation for Complex Systems

The SMP represents complex-valued matrices arising from AC analysis using an **orthogonal linked list** structure within the `spMatrixFrame`. Each non-zero element is stored in a `spMatrixElement` structure containing `Real` and `Imag` double-precision fields. For a matrix element \( a_{ij} = \alpha + j\beta \), the storage maps directly:
```c
typedef struct spMatrixElement {
    double Real, Imag;
    struct spMatrixElement *NextInRow, *NextInColumn;
    int Row, Col;
} spMatrixElement;
```
This provides \( O(1) \) insertion and \( O(\text{nnz}) \) traversal, optimal for the incremental matrix assembly typical of Modified Nodal Analysis (MNA).

### LU Factorization with Complex Pivoting

The core solution of \( \mathbf{Ax} = \mathbf{b} \) for complex systems uses LU factorization with partial pivoting for stability:
\[
\mathbf{P} \cdot \mathbf{A} \cdot \mathbf{Q} = \mathbf{L} \cdot \mathbf{U}
\]
where \( \mathbf{P} \) and \( \mathbf{Q} \) are permutation matrices determined by a **threshold pivoting** strategy combined with the **Markowitz criterion** to minimize fill-in.

The **Markowitz count** for element \( a_{ij} \) is:
\[
M(i,j) = (r_i - 1) \times (c_j - 1)
\]
where \( r_i \) and \( c_j \) are the number of non-zeros in row \( i \) and column \( j \) respectively. The pivot selection algorithm in `spFindPivot` seeks an element satisfying the dual criteria:
1.  **Threshold Condition**: \( |a_{ij}| \ge u \cdot \max_{k \ge i} |a_{kj}| \), where \( u \) is the pivot tolerance (default \( 10^{-3} \)).
2.  **Minimal Markowitz Count**: Among candidates satisfying (1), choose the one minimizing \( M(i,j) \).

For complex values, the magnitude \( |a_{ij}| = \sqrt{\text{Real}(a_{ij})^2 + \text{Imag}(a_{ij})^2} \) is computed using a scaled algorithm to prevent overflow.

### Determinant Calculation

The determinant of the complex matrix is computed from the LU factors, accounting for row and column permutations:
\[
\det(\mathbf{A}) = \text{sign}(\mathbf{P}, \mathbf{Q}) \times \prod_{k=1}^{n} U_{kk}
\]
where \( U_{kk} \) are the complex diagonal elements of the upper triangular factor \( \mathbf{U} \), and \( \text{sign}(\mathbf{P}, \mathbf{Q}) \) is \( \pm 1 \) depending on the parity of the permutations. The `spDeterminant` function implements this as:
\[
\text{det} = \left( \prod_{k=1}^{n} U_{kk}^{\text{Real}} \right) \times \exp\left(j \sum_{k=1}^{n} \arg(U_{kk}^{\text{Imag}})\right)
\]
with careful handling of near-zero pivots to avoid numerical underflow.

### Complex Forward/Backward Substitution

Solving the factorized system uses complex arithmetic in forward and backward substitution:
1.  **Forward Substitution**: Solve \( \mathbf{L} \cdot \mathbf{y} = \mathbf{P} \cdot \mathbf{b} \) for the complex vector \( \mathbf{y} \).
2.  **Backward Substitution**: Solve \( \mathbf{U} \cdot \mathbf{x} = \mathbf{y} \) for the complex solution vector \( \mathbf{x} \), then apply the column permutation \( \mathbf{Q} \) to obtain the final result.

The core operation in `spSolveComplex` is a complex DAXPY-like update: \( \mathbf{b}_i \leftarrow \mathbf{b}_i - \mathbf{L}_{ij} \times \mathbf{b}_j \), using optimized complex multiplication.

## Convergence Analysis

### Numerical Stability and Growth Factor

The use of threshold pivoting controls the **element growth factor** \( \rho \), defined as:
\[
\rho = \frac{\max_{i,j} |U_{ij}|}{\max_{i,j} |A_{ij}|}
\]
A theoretical bound exists: \( \rho \le (1 + u^{-1})^{n-1} \), but for circuit matrices, which are often diagonally dominant, empirical \( \rho \) is typically \( < 10^3 \). The `spFactor` function monitors growth; if \( \rho > 10^6 \), a warning is issued as it indicates potential numerical instability.

### Condition Number Estimation

The stability of the solution \( \mathbf{x} \) to perturbations in \( \mathbf{A} \) or \( \mathbf{b} \) is governed by the **condition number** \( \kappa(\mathbf{A}) = \|\mathbf{A}\| \cdot \|\mathbf{A}^{-1}\| \). For complex matrices, the 1-norm is estimated via a power iteration on \( |\mathbf{A}| \) (element-wise absolute values). Ill-conditioning (\( \kappa > 10^8 \)) often arises in circuits at near-resonant frequencies or with floating nodes, triggering Gmin stepping (\( g_{\text{min}} = 10^{-12} \, \text{S} \)) to regularize the matrix.

### Singularity and Edge-Case Handling

The solver must detect and handle singular or near-singular matrices:
- **Zero Pivot Detection**: If a pivot's magnitude is below the **absolute zero tolerance** \( \epsilon_{\text{abs}} = 10^{-12} \), the matrix is declared singular.
- **Recovery Mechanisms**: Automatic strategies include:
    1.  **Gmin Stepping**: Adding a small conductance \( g_{\text{min}} \) from every node to ground.
    2.  **Threshold Relaxation**: Temporarily increasing the pivot tolerance \( u \) to find a viable pivot.
    3.  **Modified Pivoting**: For AC analysis, prioritizing pivots with large imaginary parts to maintain phase accuracy.

### Validation of Core Complex Operations

The test files `test_cx_mag.c`, `test_cx_ph.c`, `test_cx_cph.c`, and `test_cx_j.c` enforce correctness at the unit level:
- **Magnitude**: Verifies \( |z| = \sqrt{\text{Re}(z)^2 + \text{Im}(z)^2} \) across the representable range, including subnormal numbers.
- **Phase**: Validates \( \arg(z) = \text{atan2}(\text{Im}(z), \text{Re}(z)) \), ensuring correct branch cut behavior along the negative real axis.
- **Complex Power**: Checks identities like \( (a+jb)^{(c+jd)} = \exp((c+jd) \cdot \ln(a+jb)) \).
- **Imaginary Unit**: Confirms \( j^2 = -1 \), \( 1/j = -j \), and that multiplication by `j` performs an exact \( -\pi/2 \) phase shift.

These tests use both absolute (\( \epsilon_{\text{abs}} \)) and relative (\( \epsilon_{\text{rel}} = 10^{-12} \)) error tolerances, ensuring the arithmetic meets the precision requirements for accurate circuit simulation.

## C Implementation

### Core Data Structures

The entire SMP architecture is built around two primary data structures defined in `spdefs.h`:

```c
/* Complex matrix element with orthogonal linked list pointers */
typedef struct spMatrixElement {
    double Real, Imag;                         /* Complex value */
    struct spMatrixElement *NextInRow;         /* Next element in row */
    struct spMatrixElement *NextInColumn;      /* Next element in column */
    int Row, Col;                              /* Internal coordinates */
} spMatrixElement;

/* Main matrix frame containing all state */
typedef struct spMatrixFrame {
    int Size;                                  /* Matrix dimension */
    int Complex;                               /* TRUE for complex matrix */
    spMatrixElement **FirstInRow;              /* Row linked list headers */
    spMatrixElement **FirstInColumn;           /* Column linked list headers */
    spMatrixElement **Diag;                    /* Pointers to diagonal elements */
    double *RHS;                               /* Real right-hand side (2*Size for complex) */
    double *Intermediate;                      /* Workspace for solves */
    int *IntToExtRowMap;                       /* Internal to external row map */
    int *IntToExtColMap;                       /* Internal to external column map */
    int *ExtToIntRowMap;                       /* External to internal row map */
    double PivotThreshold;                     /* Threshold u (default 1e-3) */
    double AbsThreshold;                       /* Absolute zero tolerance (1e-12) */
    double *MarkowitzRowCount;                 /* Non-zeros per row for Markowitz */
    double *MarkowitzColCount;                 /* Non-zeros per column */
    long Fillins;                              /* Count of fill-in elements created */
    int Partitioned;                           /* Factorization state flag */
    int Factored;                              /* TRUE if factored */
    int Singular;                              /* TRUE if matrix is singular */
    int SingularRow;                           /* Row index of singular pivot */
} spMatrixFrame;
```

### Matrix Allocation (`spalloc.c`)

The `spCreate` function pre-allocates the matrix structure and an element pool to minimize runtime allocation overhead.

```c
spMatrixFrame* spCreate(int size, int complexFlag, int expectedNz) {
    spMatrixFrame *matrix = (spMatrixFrame*)malloc(sizeof(spMatrixFrame));
    /* ... initialization of array pointers ... */
    
    /* Pre-allocate element pool with fill-in allowance */
    int poolSize = expectedNz * 5;  /* Fill-in factor of 5 */
    matrix->ElementPool = (spMatrixElement*)calloc(poolSize, sizeof(spMatrixElement));
    matrix->FreeElement = matrix->ElementPool;
    
    /* Link free elements into a pool */
    for (int i = 0; i < poolSize - 1; i++)
        matrix->ElementPool[i].NextInColumn = &matrix->ElementPool[i+1];
    matrix->ElementPool[poolSize-1].NextInColumn = NULL;
    
    return matrix;
}
```

### Matrix Building (`spbuild.c`)

Element insertion uses `spGetElement` to find or create an element at `(row, col)`, traversing the orthogonal linked lists.

```c
spMatrixElement* spGetElement(spMatrixFrame *matrix, int row, int col) {
    spMatrixElement *prev, *element;
    
    /* Search row list for column */
    prev = NULL;
    element = matrix->FirstInRow[row];
    while (element != NULL && element->Col < col) {
        prev = element;
        element = element->NextInRow;
    }
    
    if (element != NULL && element->Col == col)
        return element; /* Element exists */
        
    /* Create new element from pool */
    spMatrixElement *new = matrix->FreeElement;
    matrix->FreeElement = new->NextInColumn;
    
    new->Row = row; new->Col = col;
    new->Real = new->Imag = 0.0;
    
    /* Insert into row list */
    new->NextInRow = element;
    if (prev == NULL) matrix->FirstInRow[row] = new;
    else prev->NextInRow = new;
    
    /* Insert into column list (similar logic) */
    /* ... */
    
    return new;
}
```

Stamping functions like `spADD_COMPLEX_ELEMENT` map directly to this primitive:
```c
void spADD_COMPLEX_ELEMENT(spMatrixFrame *matrix, int row, int col, 
                           double real, double imag) {
    spMatrixElement *e = spGetElement(matrix, row, col);
    e->Real += real;
    e->Imag += imag;
}
```

### LU Factorization (`spfactor.c`)

The factorization driver `spFactor` implements a right-looking algorithm with in-place storage of L and U factors in the original matrix structure.

```c
int spFactor(spMatrixFrame *matrix) {
    matrix->Fillins = 0;
    matrix->Singular = FALSE;
    
    for (int k = 0; k < matrix->Size; k++) {
        /* 1. Find pivot using Markowitz-threshold search */
        if (!spFindPivot(matrix, k)) {
            matrix->Singular = TRUE;
            matrix->SingularRow = k;
            return -1;
        }
        
        /* 2. Perform row/column permutations (swap pointers) */
        spSwapRows(matrix, k, pivotRow);
        spSwapCols(matrix, k, pivotCol);
        
        /* 3. Extract pivot */
        spMatrixElement *pivot = matrix->Diag[k];
        double pivotMag = sqrt(pivot->Real*pivot->Real + pivot->Imag*pivot->Imag);
        
        /* 4. Compute multipliers and update submatrix */
        for (spMatrixElement *e = pivot->NextInRow; e != NULL; e = e->NextInRow) {
            /* Compute multiplier L_ik = A_ik / pivot */
            double multReal = (e->Real*pivot->Real + e->Imag*pivot->Imag) / (pivotMag*pivotMag);
            double multImag = (e->Imag*pivot->Real - e->Real*pivot->Imag) / (pivotMag*pivotMag);
            
            /* Store multiplier in the matrix (L factor) */
            e->Real = multReal; e->Imag = multImag;
            
            /* Update column: A_jk = A_jk - L_ik * A_ij */
            for (spMatrixElement *colElem = pivot->NextInColumn; colElem != NULL; colElem = colElem->NextInColumn) {
                if (colElem->Row > k) {
                    spMatrixElement *target = spGetElement(matrix, e->Row, colElem->Col);
                    /* Complex update: target -= mult * colElem */
                    target->Real -= multReal*colElem->Real - multImag*colElem->Imag;
                    target->Imag -= multReal*colElem->Imag + multImag*colElem->Real;
                }
            }
        }
    }
    matrix->Factored = TRUE;
    return 0;
}
```

The pivot search function `spFindPivot` directly encodes the mathematical threshold and Markowitz criteria:

```c
static int spFindPivot(spMatrixFrame *matrix, int diag) {
    double maxInCol, candidateMag;
    int bestRow = -1, bestCol = -1;
    long bestMarkowitz = LONG_MAX;
    
    for (int col = diag; col < matrix->Size; col++) {
        /* Find maximum magnitude in column */
        maxInCol = 0.0;
        for (spMatrixElement *e = matrix->FirstInColumn[col]; e != NULL; e = e->NextInColumn) {
            if (e->Row >= diag) {
                candidateMag = sqrt(e->Real*e->Real + e->Imag*e->Imag);
                if (candidateMag > maxInCol) maxInCol = candidateMag;
            }
        }
        
        /* Check candidates in this column against threshold */
        for (spMatrixElement *e = matrix->FirstInColumn[col]; e != NULL; e = e->NextInColumn) {
            if (e->Row >= diag) {
                candidateMag = sqrt(e->Real*e->Real + e->Imag*e->Imag);
                if (candidateMag >= matrix->PivotThreshold * maxInCol) {
                    /* Compute Markowitz count */
                    long markowitz = (matrix->MarkowitzRowCount[e->Row] - 1) *
                                     (matrix->MarkowitzColCount[col] - 1);
                    if (markowitz < bestMarkowitz) {
                        bestMarkowitz = markowitz;
                        bestRow = e->Row;
                        bestCol = col;
                    }
                }
            }
        }
    }
    
    if (bestRow == -1) return FALSE;
    /* ... store pivot ... */
    return TRUE;
}
```

### Solution Routines (`spsolve.c`)

Forward and backward substitution are implemented to exploit the linked list structure of L and U.

```c
/* Forward substitution: Solve L*y = Pb */
void spForwardSubstitute(spMatrixFrame *matrix, double *rhs) {
    for (int i = 0; i < matrix->Size; i++) {
        int extRow = matrix->IntToExtRowMap[i];
        double realRHS = rhs[2*extRow];
        double imagRHS = rhs[2*extRow + 1];
        
        for (spMatrixElement *e = matrix->FirstInRow[i]; e != NULL && e->Col < i; e = e->NextInRow) {
            /* y_i -= L_ij * y_j */
            double multReal = e->Real;  /* L_ij stored during factorization */
            double multImag = e->Imag;
            int j = e->Col;
            int extCol = matrix->IntToExtRowMap[j];
            
            realRHS -= multReal*rhs[2*extCol] - multImag*rhs[2*extCol+1];
            imagRHS -= multReal*rhs[2*extCol+1] + multImag*rhs[2*extCol];
        }
        matrix->Intermediate[2*i] = realRHS;
        matrix->Intermediate[2*i+1] = imagRHS;
    }
}

/* Backward substitution: Solve U*x = y */
void spBackwardSubstitute(spMatrixFrame *matrix, double *solution) {
    for (int i = matrix->Size-1; i >= 0; i--) {
        double realAccum = matrix->Intermediate[2*i];
        double imagAccum = matrix->Intermediate[2*i+1];
        
        for (spMatrixElement *e = matrix->Diag[i]->NextInRow; e != NULL; e = e->NextInRow) {
            /* U_ij stored in element */
            double uReal = e->Real;
            double uImag = e->Imag;
            int j = e->Col;
            int extCol = matrix->IntToExtColMap[j];
            
            realAccum -= uReal*solution[2*extCol] - uImag*solution[2*extCol+1];
            imagAccum -= uReal*solution[2*extCol+1] + uImag*solution[2*extCol];
        }
        
        /* Divide by diagonal U_ii */
        spMatrixElement *diag = matrix->Diag[i];
        double div = diag->Real*diag->Real + diag->Imag*diag->Imag;
        solution[2*i] = (realAccum*diag->Real + imagAccum*diag->Imag) / div;
        solution[2*i+1] = (imagAccum*diag->Real - realAccum*diag->Imag) / div;
    }
}
```

The main solver `spSolveComplex` orchestrates these steps:
```c
int spSolveComplex(spMatrixFrame *matrix, double *rhs, double *solution) {
    if (!matrix->Factored) {
        if (spFactor(matrix) != 0) return -1; /* Singular */
    }
    
    /* Apply row permutation to RHS */
    for (int i = 0; i < matrix->Size; i++) {
        int extRow = matrix->IntToExtRowMap[i];
        matrix->Intermediate[2*i] = rhs[2*extRow];
        matrix->Intermediate[2*i+1] = rhs[2*extRow+1];
    }
    
    spForwardSubstitute(matrix, rhs);
    spBackwardSubstitute(matrix, solution);
    
    /* Apply column permutation to solution */
    double *temp = (double*)malloc(2*matrix->Size*sizeof(double));
    memcpy(temp, solution, 2*matrix->Size*sizeof(double));
    for (int i = 0; i < matrix->Size; i++) {
        int extCol = matrix->IntToExtColMap[i];
        solution[2*extCol] = temp[2*i];
        solution[2*extCol+1] = temp[2*i+1];
    }
    free(temp);
    
    return 0;
}
```

### SMP Interface Layer (`spsmp.c`)

The `SMPmatrix` structure provides a circuit-simulation-friendly abstraction over the raw `spMatrixFrame`.

```c
typedef struct {
    spMatrixFrame *frame;
    int size;
    int *EquationMap;          /* Circuit node/branch -> matrix row map */
    int *InvEquationMap;       /* Matrix row -> circuit node/branch map */
    int numNodes;
    int numVoltageSources;
} SMPmatrix;

SMPmatrix* SMPcreate(int numNodes, int numVSources) {
    SMPmatrix *smp = (SMPmatrix*)malloc(sizeof(SMPmatrix));
    smp->numNodes = numNodes;
    smp->numVoltageSources = numVSources;
    smp->size = numNodes + numVSources;  /* Modified Nodal Analysis size */
    
    /* Allocate equation maps */
    smp->EquationMap = (int*)malloc((numNodes + numVSources) * sizeof(int));
    smp->InvEquationMap = (int*)malloc((numNodes + numVSources) * sizeof(int));
    
    /* Initialize: nodes first, then voltage source branches */
    for (int i = 0; i < numNodes; i++) {
        smp->EquationMap[i] = i;
        smp->InvEquationMap[i] = i;
    }
    for (int i = 0; i < numVSources; i++) {
        smp->EquationMap[numNodes + i] = numNodes + i;
        smp->InvEquationMap[numNodes + i] = numNodes + i;
    }
    
    /* Create underlying sparse matrix with expected ~5 non-zeros per row */
    smp->frame = spCreate(smp->size, TRUE, smp->size * 5);
    return smp;
}

void SMPaddElement(SMPmatrix *smp, int node1, int node2, double real, double imag) {
    int row = smp->EquationMap[node1];
    int col = smp->EquationMap[node2];
    spADD_COMPLEX_ELEMENT(smp->frame, row, col, real, imag);
}
```

### Utility Functions (`sputils.c`)

The determinant calculation implements the mathematical formula described earlier:

```c
void spDeterminant(spMatrixFrame *matrix, double *real, double *imag) {
    double logReal = 0.0;
    double logImag = 0.0;
    int sign = 1;
    
    for (int i = 0; i < matrix->Size; i++) {
        spMatrixElement *diag = matrix->Diag[i];
        if (diag == NULL) { /* Zero pivot */
            *real = *imag = 0.0;
            return;
        }
        
        /* Accumulate log of diagonal: log(U_ii) */
        double mag = sqrt(diag->Real*diag->Real + diag->Imag*diag->Imag);
        double arg = atan2(diag->Imag, diag->Real);
        
        logReal += log(mag);
        logImag += arg;
        
        /* Track permutation parity from row/column swaps */
        if (matrix->IntToExtRowMap[i] != i) sign = -sign;
        if (matrix->IntToExtColMap[i] != i) sign = -sign;
    }
    
    /* exponentiate: det = sign * exp(logReal + j*logImag) */
    double expReal = exp(logReal);
    *real = sign * expReal * cos(logImag);
    *imag = sign * expReal * sin(logImag);
}
```

Scaling functions implement diagonal scaling \( \mathbf{A}' = \mathbf{D}_1 \mathbf{A} \mathbf{D}_2 \) to improve condition number:

```c
void spScale(spMatrixFrame *matrix, double *rowScale, double *colScale) {
    for (int i = 0; i < matrix->Size; i++) {
        for (spMatrixElement *e = matrix->FirstInRow[i]; e != NULL; e = e->NextInRow) {
            /* A'_ij = D1_i * A_ij * D2_j */
            double real = e->Real * rowScale[i] * colScale[e->Col];
            double imag = e->Imag * rowScale[i] * colScale[e->Col];
            e->Real = real;
            e->Imag = imag;
        }
    }
}
```

### Validation Test Files

The four test files provide unit-level validation:

**`test_cx_mag.c`** - Validates magnitude computation across all quadrants and edge cases:
```c
void test_magnitude() {
    complex z;
    double expected, obtained, error;
    
    /* Test 1: Basic values */
    z.real = 3.0; z.imag = 4.0;
    expected = 5.0;
    obtained = Cabs(z);
    error = fabs(obtained - expected) / expected;
    assert(error < 1e-12);
    
    /* Test 2: Underflow */
    z.real = 1e-150; z.imag = 1e-150;
    obtained = Cabs(z);
    assert(obtained >= 0.0 && obtained < 1e-149);
    
    /* Test 3: Overflow protection */
    z.real = 1e150; z.imag = 1e150;
    obtained = Cabs(z);
    assert(!isinf(obtained) && obtained < 1.5e150);
}
```

**`test_cx_ph.c`** - Validates phase angle computation, including branch cut continuity:
```c
void test_phase() {
    complex z;
    
    /* Test branch cut along negative real axis */
    z.real = -1.0; z.imag = +1e-15;  /* Just above cut */
    double phase_above = Carg(z);
    z.imag = -1e-15;                 /* Just below cut */
    double phase_below = Carg(z);
    /* Should be ~π and ~-π respectively */
    assert(fabs(phase_above - M_PI) < 1e-12);
    assert(fabs(phase_below + M_PI) < 1e-12);
}
```

**`test_cx_cph.c`** - Validates complex power function using identities:
```c
void test_complex_power() {
    complex a, b, result;
    
    /* Test: a^(b+c) = a^b * a^c */
    a.real = 2.0; a.imag = 1.0;
    b.real = 1.0; b.imag = 0.5;
    complex c; c.real = 0.5; c.imag = 0.25;
    
    complex b_plus_c = Cadd(b, c);
    complex pow1 = Cpow(a, b_plus_c);
    
    complex pow2 = Cpow(a, b);
    complex pow3 = Cpow(a, c);
    complex pow_product = Cmul(pow2, pow3);
    
    double diff = Cabs(Csub(pow1, pow_product));
    assert(diff < 1e-10);
}
```

**`test_cx_j.c`** - Validates fundamental imaginary unit properties:
```c
void test_imaginary_unit() {
    complex j = {0.0, 1.0};
    complex one = {1.0, 0.0};
    complex neg_one = {-1.0, 0.0};
    complex result;
    
    /* j^2 = -1 */
    result = Cmul(j, j);
    assert(fabs(result.real - neg_one.real) < 1e-15);
    assert(fabs(result.imag - neg_one.imag) < 1e-15);
    
    /* 1/j = -j */
    result = Cdiv(one, j);
    complex neg_j = {0.0, -1.0};
    assert(fabs(result.real - neg_j.real) < 1e-15);
    assert(fabs(result.imag - neg_j.imag) < 1e-15);
}
```

These validation tests, combined with the robust numerical algorithms in the SMP, ensure that Ngspice's complex mathematics layer provides the accuracy and reliability required for professional-grade circuit simulation across all analysis types.