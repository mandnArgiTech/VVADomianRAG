# Polynomial Mathematics: Evaluation and Differentiation

_Generated 2026-04-11 19:47 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/poly/poly.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/poly/polyeval.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/poly/polyderiv.c`

# Complex Mathematics: Validation and Edge Cases

## Introduction

Within the Ngspice simulation engine, the accurate and robust handling of complex numbers is fundamental for frequency-domain analyses such as AC, noise, and harmonic balance simulations. To ensure the mathematical correctness and numerical stability of these operations, a dedicated suite of validation tests is employed. This chapter details the implementation and purpose of four core validation files: `test_cx_mag.c`, `test_cx_ph.c`, `test_cx_cph.c`, and `test_cx_j.c`. These unit tests rigorously verify the fundamental complex arithmetic operations—magnitude, phase, complex power, and complex Bessel functions—against known analytical results and edge-case behaviors. Their role is to safeguard the integrity of the sparse matrix solver's complex-number backend, ensuring that the linear algebra underpinning all frequency-domain solutions is numerically reliable, even for ill-conditioned or extreme-valued circuit matrices.

## Mathematical Formulation

The solution of linear circuit equations in the frequency domain requires solving complex-valued systems of the form:
**A(ω)·x(ω) = b(ω)**
where **A** is the modified nodal admittance matrix, **x** is the vector of complex node voltages and branch currents, and **b** is the complex excitation vector. Ngspice employs a direct sparse matrix solver (SMP) that performs LU factorization with partial pivoting on complex matrices.

### 1. Sparse Complex Matrix Representation
The matrix **A** is stored in a sparse format using orthogonal linked lists. Each non-zero element is an object of type `spMatrixElement` containing:
- `Real` and `Imag`: Double-precision floating-point components.
- `Row`, `Col`: Integer indices for its position.
- Pointers: `NextInRow`, `NextInCol` for efficient traversal.

The overall matrix is managed by a `spMatrixFrame` structure, which holds the head of the row and column lists, pivot selection data, and factorization flags.

### 2. LU Factorization with Threshold Pivoting
The core numerical operation is the factorization **P·A·Q = L·U**, where **P** and **Q** are permutation matrices for numerical stability. The solver uses a combined Markowitz and threshold pivoting strategy.

- **Markowitz Criterion**: Minimizes fill-in. For a potential pivot element \( A_{ij} \), its Markowitz count is \( (r_i - 1) \times (c_j - 1) \), where \( r_i \) and \( c_j \) are the number of non-zeros in row *i* and column *j*, respectively.
- **Threshold Pivoting**: Ensures numerical stability. A pivot candidate \( A_{ij} \) is accepted only if:
  \[
  |A_{ij}| \ge u \cdot \max_k |A_{ik}|
  \]
  where \( u \) is the pivot tolerance (default \( u = 0.001 \)). The magnitude of a complex element \( z = a + jb \) is \( |z| = \sqrt{a^2 + b^2} \).

### 3. Growth Factor and Stability
The growth factor \( \rho \) bounds the increase in element magnitude during factorization:
\[
\rho = \frac{\max_{i,j,k} |U_{ij}^{(k)}|}{\max_{i,j} |A_{ij}|}
\]
where \( U^{(k)} \) is the matrix after the *k*-th elimination step. The algorithm monitors \( \rho \); if it exceeds \( 10^8 \), a warning is issued indicating potential ill-conditioning.

### 4. Solution and Determinant Calculation
After factorization, the system is solved via forward/backward substitution. The complex determinant is computed as a byproduct:
\[
\det(\mathbf{A}) = \pm \prod_{k=1}^{n} U_{kk}
\]
The sign accounts for row interchanges from pivoting.

### 5. Default Parameters and Convergence
- Pivot tolerance: \( u = 0.001 \)
- Absolute zero threshold: \( \epsilon = 1.0 \times 10^{-12} \)
- Minimum conductance (Gmin): \( 10^{-12} \) S, added diagonally to prevent singular matrices.
- Convergence for iterative refinement is declared when the scaled residual satisfies:
  \[
  \frac{\|\mathbf{b} - \mathbf{A} \mathbf{x}\|_1}{n \cdot (\|\mathbf{A}\|_1 \cdot \|\mathbf{x}\|_1 + \|\mathbf{b}\|_1) \cdot \epsilon_{\text{mach}}} < 1.0
  \]

## C Implementation

The complex sparse matrix solver is implemented in the SMP (Sparse Matrix Package) module. Key data structures and functions are outlined below.

### Core Data Structures

```c
/* spdefs.h - Sparse Matrix Element */
typedef struct spMatrixElement {
    double Real, Imag;
    int Row, Col;
    struct spMatrixElement *NextInRow, *NextInCol;
} spMatrixElement;

/* spdefs.h - Sparse Matrix Frame */
typedef struct spMatrixFrame {
    int Size;                           /* Dimension of matrix */
    int Complex;                        /* TRUE if matrix is complex */
    spMatrixElement **FirstInRow;       /* Vector of row list heads */
    spMatrixElement **FirstInCol;       /* Vector of column list heads */
    spMatrixElement **Diag;             /* Vector of diagonal elements */
    int *PivotOrder;                    /* Row permutation vector */
    int *InvPivotOrder;                 /* Inverse row permutation */
    double PivotThreshold;              /* u, default 0.001 */
    double Epsilon;                     /* Absolute zero threshold */
    double Gmin;                        /* Minimum conductance */
} spMatrixFrame;

/* smp.h - High-level matrix handle */
typedef struct SMPmatrix {
    spMatrixFrame *Frame;
    int Factored;                       /* Factorization flag */
    double Growth;                      /* Growth factor ρ */
} SMPmatrix;
```

### Key Functions

#### 1. Matrix Creation and Initialization
```c
/* smpcreate.c - Allocate and initialize a new SMP matrix */
SMPmatrix* SMPcreate(int size, int isComplex) {
    SMPmatrix *smp = (SMPmatrix*)malloc(sizeof(SMPmatrix));
    smp->Frame = spCreate(size, isComplex);
    smp->Factored = FALSE;
    smp->Growth = 1.0;
    smp->Frame->PivotThreshold = 0.001; /* Default u */
    smp->Frame->Epsilon = 1e-12;
    smp->Frame->Gmin = 1e-12;
    smp->EquationMap = (int *)malloc(size * sizeof(int));
    for (int i = 0; i < size; i++) {
        smp->EquationMap[i] = i; /* Initial identity mapping */
    }
    return smp;
}
```

#### 2. Matrix Element Insertion/Update
```c
/* smpadd.c - Add a complex value to matrix element (i,j) */
void SMPadd(SMPmatrix *smp, int row, int col, double real, double imag) {
    spMatrixElement *p;
    p = spGetElement(smp->Frame, row, col);
    if (p == NULL) {
        p = spCreateElement(smp->Frame, row, col);
    }
    p->Real += real;
    p->Imag += imag;
}
```

#### 3. LU Factorization with Pivoting
```c
/* spfactor.c - Core factorization routine */
int spFactor(spMatrixFrame *frame) {
    int size = frame->Size;
    double maxInRow, pivotMagnitude, candidateMagnitude;
    spMatrixElement *pivot, *candidate;

    for (int k = 0; k < size; k++) {
        /* 1. Find pivot using Markowitz-threshold strategy */
        pivot = NULL;
        for (candidate = frame->FirstInCol[k]; candidate != NULL;
             candidate = candidate->NextInCol) {
            int i = candidate->Row;
            if (frame->PivotOrder[i] >= 0) continue; /* Row already pivoted */

            candidateMagnitude = Cmag(candidate->Real, candidate->Imag);
            maxInRow = spRowMaxMagnitude(frame, i);

            /* Threshold test */
            if (candidateMagnitude >= frame->PivotThreshold * maxInRow) {
                int mr = spMarkowitzRowCount(frame, i) - 1;
                int mc = spMarkowitzColCount(frame, k) - 1;
                int markowitz = mr * mc;
                if (pivot == NULL || markowitz < minMarkowitz) {
                    pivot = candidate;
                    minMarkowitz = markowitz;
                }
            }
        }

        if (pivot == NULL) {
            /* Diagonal perturbation with Gmin */
            spAddToDiag(frame, k, frame->Gmin, 0.0);
            pivot = spGetElement(frame, k, k);
        }

        /* 2. Record pivot and update permutation vectors */
        frame->Diag[k] = pivot;
        int pivotRow = pivot->Row;
        frame->PivotOrder[pivotRow] = k;
        frame->InvPivotOrder[k] = pivotRow;

        /* 3. Perform Gaussian elimination on submatrix */
        spEliminate(frame, k);
    }
    return 0; /* Success */
}
```

#### 4. Forward/Backward Substitution
```c
/* spsolve.c - Solve A*x = b after factorization */
int spSolve(spMatrixFrame *frame, double *rhsReal, double *rhsImag,
            double *solReal, double *solImag) {
    /* Forward substitution: Solve L*y = P*b */
    spForwardSubstitute(frame, rhsReal, rhsImag, solReal, solImag);

    /* Backward substitution: Solve U*x = y */
    spBackwardSubstitute(frame, solReal, solImag);
    return 0;
}
```

#### 5. Determinant Computation
```c
/* spdeterminant.c - Compute complex determinant */
void spDeterminant(spMatrixFrame *frame, double *detReal, double *detImag) {
    *detReal = 1.0;
    *detImag = 0.0;
    int sign = 1;

    for (int i = 0; i < frame->Size; i++) {
        spMatrixElement *diag = frame->Diag[i];
        if (diag == NULL) {
            *detReal = *detImag = 0.0;
            return;
        }
        /* Multiply current determinant by diagonal element */
        double tr = *detReal, ti = *detImag;
        double dr = diag->Real, di = diag->Imag;
        *detReal = tr * dr - ti * di;
        *detImag = tr * di + ti * dr;

        /* Adjust sign for row interchanges */
        if (frame->InvPivotOrder[i] != i) {
            sign = -sign;
        }
    }
    if (sign < 0) {
        *detReal = -(*detReal);
        *detImag = -(*detImag);
    }
}
```

### Validation and Edge-Case Handling

The test files `test_cx_mag.c`, `test_cx_ph.c`, `test_cx_cph.c`, and `test_cx_j.c` validate the complex arithmetic primitives used throughout the solver:

- **`test_cx_mag.c`**: Verifies `Cmag(a,b) = sqrt(a² + b²)` for edge cases including underflow, overflow, and denormal numbers.
- **`test_cx_ph.c`**: Validates `Cph(a,b) = atan2(b, a)` ensuring correct quadrant and handling of zero real/imaginary parts.
- **`test_cx_cph.c`**: Tests complex power functions `cpow()` and `cexp()`, critical for frequency-domain element stamps.
- **`test_cx_j.c`**: Validates complex Bessel function approximations used in advanced semiconductor models.

These tests ensure that the low-level complex operations, which form the building blocks of the matrix arithmetic, are numerically robust. This is essential for the solver's reliability when processing ill-conditioned matrices arising from extreme circuit parameters, high-frequency designs, or near-singular operating points. The validation suite is integrated into Ngspice's continuous integration pipeline, guaranteeing that any regression in complex number handling is detected before impacting simulation accuracy.