# Sparse Matrix: Data Structures and Memory Allocation

_Generated 2026-04-11 17:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spconfig.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spalloc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spbuild.c`

# Chapter: Sparse Matrix: Data Structures and Memory Allocation

## Introduction

The sparse matrix solver forms the computational backbone of Ngspice's circuit simulation engine, responsible for solving the large, sparse linear systems that arise from Modified Nodal Analysis (MNA). The efficiency and numerical stability of this solver directly determine the simulator's performance and reliability when analyzing circuits ranging from small analog designs to complex digital systems. This chapter examines the four core files that implement Ngspice's sparse matrix infrastructure: `spconfig.h` defines the numerical thresholds and configuration constants that govern solver behavior; `spdefs.h` declares the fundamental data structures that mathematically represent sparse matrices; `spalloc.c` implements the memory management system that dynamically allocates and reuses matrix elements; and `spbuild.c` provides the matrix assembly routines that stamp device contributions into the sparse matrix structure. Together, these files implement an orthogonal linked list representation optimized for circuit matrices, with sophisticated pivoting strategies to minimize fill-in during LU factorization while maintaining numerical stability through threshold-based pivot selection.

## Mathematical Formulation

### 1. Sparse Matrix Representation for Circuit Equations

The core mathematical problem in SPICE circuit simulation is solving the Modified Nodal Analysis (MNA) system:
\[
\mathbf{J} \cdot \Delta\mathbf{x} = -\mathbf{F}(\mathbf{x})
\]
where \(\mathbf{J} \in \mathbb{R}^{n \times n}\) is the Jacobian matrix, \(\Delta\mathbf{x} \in \mathbb{R}^n\) is the solution update vector, and \(\mathbf{F}(\mathbf{x}) \in \mathbb{R}^n\) is the circuit equation residual. For AC analysis, this becomes a complex system:
\[
[\mathbf{G} + j\omega\mathbf{C}] \cdot \mathbf{X}(\omega) = \mathbf{B}(\omega)
\]
where \(\mathbf{G}\) is the conductance matrix, \(\mathbf{C}\) is the capacitance/inductance matrix, and \(\omega\) is angular frequency.

#### 1.1 Sparsity Pattern of Circuit Matrices

Circuit matrices exhibit specific sparsity patterns determined by device connectivity. For a circuit with \(n\) nodes and \(b\) branches:

- **Diagonal dominance**: Each diagonal element \(J_{ii}\) represents the sum of conductances connected to node \(i\) plus contributions from energy storage elements.
- **Off-diagonal structure**: Non-zero element \(J_{ij}\) exists if nodes \(i\) and \(j\) are connected by at least one circuit element.
- **Symmetry**: For passive linear elements, \(J_{ij} = J_{ji}\). Nonlinear elements and controlled sources break this symmetry.

The fill ratio \(\rho\) (fraction of non-zero elements) is typically:
\[
\rho = \frac{\text{nnz}}{n^2} \approx \frac{3n + 2b}{n^2} \ll 1
\]
where nnz is the number of non-zero elements. For large circuits (\(n > 1000\)), \(\rho < 0.1\%\).

#### 1.2 Orthogonal Linked List Mathematical Model

The sparse matrix \(\mathbf{A}\) is represented as two orthogonal sets of linked lists:

**Row-major representation:**
For each row \(i \in \{1, \ldots, n\}\):
\[
R_i = \{(j, a_{ij}) : a_{ij} \neq 0, j \in \{1, \ldots, n\}\}
\]
sorted by column index \(j\).

**Column-major representation:**
For each column \(j \in \{1, \ldots, n\}\):
\[
C_j = \{(i, a_{ij}) : a_{ij} \neq 0, i \in \{1, \ldots, n\}\}
\]
sorted by row index \(i\).

**Element access complexity:**
Finding element \(a_{ij}\) requires traversing either \(R_i\) or \(C_j\):
\[
T_{\text{find}}(i,j) = O(\min(r_i, c_j))
\]
where \(r_i = |R_i|\) and \(c_j = |C_j|\).

#### 1.3 Matrix Stamping Formulation

Device contributions are "stamped" into the matrix. For a resistor between nodes \(p\) and \(q\) with conductance \(g\):

\[
\mathbf{J} \leftarrow \mathbf{J} + g \cdot 
\begin{bmatrix}
1 & -1 \\
-1 & 1
\end{bmatrix}
\]
at positions \((p,p)\), \((p,q)\), \((q,p)\), \((q,q)\).

For a capacitor in transient analysis using Backward Euler integration:
\[
\mathbf{J} \leftarrow \mathbf{J} + \frac{C}{\Delta t} \cdot 
\begin{bmatrix}
1 & -1 \\
-1 & 1
\end{bmatrix}
\]
where \(\Delta t\) is the time step.

For AC analysis at frequency \(\omega\):
\[
\mathbf{J} \leftarrow \mathbf{J} + (g + j\omega C) \cdot 
\begin{bmatrix}
1 & -1 \\
-1 & 1
\end{bmatrix}
\]
storing both real and imaginary parts in the `Real` and `Imag` fields of `spMatrixElement`.

### 2. LU Factorization with Fill-in Prediction

#### 2.1 Gaussian Elimination Fill-in Creation

During LU factorization at step \(k\), for each non-zero pair \((A_{ik}, A_{kj})\) where \(i > k\) and \(j > k\):

If \(A_{ij} = 0\) initially, a fill-in element is created with value:
\[
A_{ij}^{(k+1)} = A_{ij}^{(k)} - \frac{A_{ik}^{(k)} \cdot A_{kj}^{(k)}}{A_{kk}^{(k)}}
\]

The fill-in count \(F\) depends on the elimination order:
\[
F = \sum_{k=1}^{n-1} \left[ (r_k - 1) \cdot (c_k - 1) - \text{existing non-zeros in submatrix} \right]
\]
where \(r_k\) and \(c_k\) are the number of non-zeros in row and column \(k\) of the reduced matrix.

#### 2.2 Markowitz Pivoting Criterion

To minimize fill-in, Ngspice uses the Markowitz criterion. For element \(A_{ij}\) at elimination step \(k\):

\[
M_{ij} = (r_i^{(k)} - 1) \cdot (c_j^{(k)} - 1)
\]
where:
- \(r_i^{(k)}\) = number of non-zeros in row \(i\) of the active submatrix (\(i \geq k\))
- \(c_j^{(k)}\) = number of non-zeros in column \(j\) of the active submatrix (\(j \geq k\))

The pivot is selected to minimize \(M_{ij}\) subject to numerical stability constraints.

#### 2.3 Threshold Pivoting for Numerical Stability

Given relative threshold \(\tau_r\) (default \(10^{-3}\)) and absolute thresholds \(\tau_a[j]\) (default \(10^{-12}\)), element \(A_{ij}\) is acceptable as pivot only if:

\[
|A_{ij}| \geq \max\left( \tau_a[j],\ \tau_r \cdot \max_{m \geq k} |A_{mj}| \right)
\]

This ensures the growth factor \(\rho\) in LU factorization is bounded:
\[
\rho \leq \frac{\max_{i,j,k} |A_{ij}^{(k)}|}{\max_{i,j} |A_{ij}^{(1)}|} \leq (1 + \tau_r^{-1})^{n-1}
\]

#### 2.4 Memory Allocation Model

The element pool uses a growth strategy to balance memory usage and allocation overhead. If the current pool size is \(S\) and needs expansion:

\[
S_{\text{new}} = \max(\lfloor \alpha S \rfloor,\ S + \beta)
\]
where \(\alpha = 1.5\) (growth factor) and \(\beta = 100\) (minimum increment).

The total memory usage for an \(n \times n\) matrix with \(m\) non-zeros is:
\[
M_{\text{total}} = \underbrace{O(n)}_{\text{headers}} + \underbrace{O(m)}_{\text{elements}} + \underbrace{O(n)}_{\text{mappings}} + \underbrace{O(n)}_{\text{workspace}}
\]

### 3. Solution Algorithms

#### 3.1 Forward Substitution (L·y = b)

For unit lower triangular matrix \(\mathbf{L}\) with \(L_{ii} = 1\):

\[
y_i = b_i - \sum_{j=1}^{i-1} L_{ij} y_j,\quad i = 1, \ldots, n
\]

In sparse implementation, only non-zero \(L_{ij}\) contribute:
\[
y_i = b_i - \sum_{\substack{j < i \\ L_{ij} \neq 0}} L_{ij} y_j
\]

#### 3.2 Backward Substitution (U·x = y)

For upper triangular matrix \(\mathbf{U}\):

\[
x_i = \frac{1}{U_{ii}} \left( y_i - \sum_{j=i+1}^{n} U_{ij} x_j \right),\quad i = n, n-1, \ldots, 1
\]

In sparse implementation:
\[
x_i = \frac{1}{U_{ii}} \left( y_i - \sum_{\substack{j > i \\ U_{ij} \neq 0}} U_{ij} x_j \right)
\]

#### 3.3 Matrix-Vector Multiplication

For sparse matrix \(\mathbf{A}\) and vector \(\mathbf{x}\):

\[
y_i = \sum_{\substack{j \\ A_{ij} \neq 0}} A_{ij} x_j,\quad i = 1, \ldots, n
\]

Complexity: \(O(\text{nnz})\) operations.

#### 3.4 Residual Calculation

The residual \(\mathbf{r} = \mathbf{b} - \mathbf{A}\mathbf{x}\) measures solution accuracy:

\[
r_i = b_i - \sum_{\substack{j \\ A_{ij} \neq 0}} A_{ij} x_j
\]

The relative residual norm:
\[
\frac{\|\mathbf{r}\|_\infty}{\|\mathbf{b}\|_\infty} = \frac{\max_i |r_i|}{\max_i |b_i|}
\]
should be \(< \epsilon_{\text{mach}} \cdot \kappa(\mathbf{A})\) for an accurate solution, where \(\kappa(\mathbf{A})\) is the condition number and \(\epsilon_{\text{mach}} \approx 2.2 \times 10^{-16}\) for double precision.

### 4. Reordering and Mapping Mathematics

#### 4.1 Internal-External Mapping

Let \(\pi_r: \{1, \ldots, n\} \to \{1, \ldots, n\}\) be the row permutation and \(\pi_c: \{1, \ldots, n\} \to \{1, \ldots, n\}\) be the column permutation. The permuted matrix is:
\[
P_r \mathbf{A} P_c^T
\]
where \(P_r\) and \(P_c\) are permutation matrices.

The mapping arrays implement:
- `IntToExtRowMap[i]` = \(\pi_r(i)\)
- `ExtToIntRowMap[k]` = \(\pi_r^{-1}(k)\)
- Similarly for columns.

#### 4.2 Fill-in Reducing Reordering

The Markowitz count for the reduced matrix after \(k-1\) eliminations is:
\[
M_{ij}^{(k)} = (r_i^{(k)} - 1)(c_j^{(k)} - 1)
\]
where:
\[
r_i^{(k)} = |\{j \geq k : A_{ij}^{(k)} \neq 0\}|,\quad i \geq k
\]
\[
c_j^{(k)} = |\{i \geq k : A_{ij}^{(k)} \neq 0\}|,\quad j \geq k
\]

The pivot \((p,q)\) at step \(k\) minimizes \(M_{pq}^{(k)}\) among numerically acceptable candidates.

## Convergence Analysis

### 1. Numerical Stability of Sparse Factorization

#### 1.1 Pivot Growth and Stability

The LU factorization stability is governed by the growth factor:
\[
g_k = \frac{\max_{i,j} |A_{ij}^{(k)}|}{\max_{i,j} |A_{ij}^{(1)}|}
\]

With threshold pivoting (\(\tau_r = 10^{-3}\)), the growth is bounded by:
\[
g_n \leq (1 + \tau_r^{-1})^{n-1} \approx (1001)^{n-1} \text{ in worst case}
\]
but in practice for circuit matrices, \(g_n < 10^3\) typically.

#### 1.2 Condition Number Estimation

The condition number \(\kappa(\mathbf{A}) = \|\mathbf{A}\| \cdot \|\mathbf{A}^{-1}\|\) affects solution accuracy. For circuit matrices:
- Well-conditioned: \(\kappa < 10^6\) (typical for DC operating point)
- Ill-conditioned: \(\kappa > 10^8\) (occurs with very large/small conductances)

The sparse solver detects near-singularity when:
\[
|A_{kk}^{(k)}| < \epsilon_{\text{pivot}} \cdot \max_{i \geq k} |A_{ik}^{(k)}|
\]
where \(\epsilon_{\text{pivot}} = \max(\tau_a[k], \tau_r \cdot \max_{i \geq k} |A_{ik}^{(k)}|)\).

#### 1.3 Forward Error Analysis

For the computed solution \(\tilde{\mathbf{x}}\) to \(\mathbf{A}\mathbf{x} = \mathbf{b}\):
\[
\frac{\|\mathbf{x} - \tilde{\mathbf{x}}\|}{\|\mathbf{x}\|} \lesssim \epsilon_{\text{mach}} \cdot \kappa(\mathbf{A}) \cdot \frac{\|\mathbf{r}\|}{\|\mathbf{A}\| \cdot \|\tilde{\mathbf{x}}\|}
\]
where \(\mathbf{r} = \mathbf{b} - \mathbf{A}\tilde{\mathbf{x}}\) is the residual.

For SPICE, we require:
\[
\frac{\|\mathbf{x} - \tilde{\mathbf{x}}\|}{\|\mathbf{x}\|} < \epsilon_{\text{ckt}} \approx 10^{-6}
\]
which implies:
\[
\kappa(\mathbf{A}) \cdot \frac{\|\mathbf{r}\|}{\|\mathbf{A}\| \cdot \|\tilde{\mathbf{x}}\|} < \frac{\epsilon_{\text{ckt}}}{\epsilon_{\text{mach}}} \approx 10^{10}
\]

### 2. Fill-in and Memory Convergence

#### 2.1 Fill-in Prediction Accuracy

The symbolic factorization predicts fill-ins using the elimination graph model. For a symmetric matrix, the fill-in set is:
\[
\mathcal{F} = \{(i,j): \text{ there exists a path } i \to v_1 \to \cdots \to v_k \to j \text{ in the graph}\}
\]
where all intermediate vertices have lower index than \(\min(i,j)\).

The actual fill-in count \(F_{\text{actual}}\) vs predicted \(F_{\text{predicted}}\) satisfies:
\[
F_{\text{predicted}} \leq F_{\text{actual}} \leq F_{\text{predicted}} + O(n)
\]
due to numerical cancellation creating exact zeros.

#### 2.2 Memory Pool Convergence

The dynamic memory pool allocation follows the recurrence:
\[
S_{k+1} = \max(\lfloor \alpha S_k \rfloor, S_k + \beta)
\]
where \(S_k\) is pool size after \(k\) expansions.

The steady-state condition occurs when:
\[
\frac{\text{nnz}_{\text{max}}}{S_k} < \gamma \quad (\gamma \approx 0.8)
\]
where \(\text{nnz}_{\text{max}}\) is the maximum non-zeros encountered.

The total memory overhead (fragmentation + headers) is:
\[
\text{Overhead} = \frac{S_{\text{allocated}} - \text{nnz}_{\text{used}}}{\text{nnz}_{\text{used}}} + \frac{5n + 4}{ \text{nnz}_{\text{used}}}
\]
which converges to \(< 20\%\) for large matrices.

### 3. Iterative Refinement for Accuracy

#### 3.1 Residual Calculation and Correction

Given approximate solution \(\mathbf{x}^{(0)}\), compute residual \(\mathbf{r}^{(0)} = \mathbf{b} - \mathbf{A}\mathbf{x}^{(0)}\), solve \(\mathbf{A}\mathbf{d}^{(0)} = \mathbf{r}^{(0)}\), update \(\mathbf{x}^{(1)} = \mathbf{x}^{(0)} + \mathbf{d}^{(0)}\).

The error after \(k\) iterations satisfies:
\[
\|\mathbf{x} - \mathbf{x}^{(k)}\| \leq (\kappa(\mathbf{A}) \cdot \epsilon_{\text{LU}})^k \cdot \|\mathbf{x} - \mathbf{x}^{(0)}\|
\]
where \(\epsilon_{\text{LU}}\) is the error in LU factorization.

#### 3.2 Convergence Criterion for Iterative Refinement

Stop when:
\[
\frac{\|\mathbf{d}^{(k)}\|}{\|\mathbf{x}^{(k)}\|} < \epsilon_{\text{refine}} \quad \text{or} \quad \frac{\|\mathbf{r}^{(k)}\|}{\|\mathbf{b}\|} < \epsilon_{\text{mach}} \cdot \kappa(\mathbf{A})
\]

In Ngspice, \(\epsilon_{\text{refine}} = 10^{-12}\) typically.

### 4. Performance and Complexity Analysis

#### 4.1 Time Complexity

For an \(n \times n\) matrix with nnz non-zeros and \(F\) fill-ins:

- **Symbolic analysis**: \(O(\text{nnz} \cdot \log n)\) using elimination tree
- **Numeric factorization**: \(O(\text{nnz} + F)\) operations
- **Forward/backward substitution**: \(O(\text{nnz} + F)\) operations

For circuit matrices with average degree \(d\) (connections per node):
\[
\text{nnz} = O(n \cdot d),\quad F = O(n \cdot d^2)
\]
Thus total complexity: \(O(n \cdot d^2)\).

#### 4.2 Space Complexity

- **Matrix storage**: \(O(\text{nnz} + F)\) elements
- **Factorization storage**: \(O(\text{nnz} + F)\) for \(\mathbf{L}\) and \(\mathbf{U}\)
- **Workspace**: \(O(n)\) for intermediate vectors

Total: \(O(n \cdot d^2)\) memory.

#### 4.3 Cache Performance

The blocked LU factorization improves cache utilization. For block size \(B\):
- **Spatial locality**: Elements within a \(B \times B\) block are stored contiguously
- **Temporal locality**: Each block is reused \(O(B)\) times

Miss ratio improvement:
\[
\frac{\text{Misses}_{\text{blocked}}}{\text{Misses}_{\text{unblocked}}} \approx \frac{1}{\sqrt{B}}
\]

### 5. Convergence in Circuit Simulation Context

#### 5.1 Matrix Condition Number in SPICE

Circuit matrices can become ill-conditioned due to:
1. **Large conductance ratios**: \(g_{\text{max}}/g_{\text{min}} > 10^{12}\)
2. **Floating nodes**: Zero diagonal elements before Gmin addition
3. **Coupled inductors**: Near-linear dependence

The solver handles this via:
- **Gmin stepping**: Add \(g_{\text{min}} = 10^{-12}\)S to diagonal
- **Pivoting**: Ensure \(|A_{kk}| > \epsilon_{\text{pivot}}\)
- **Scaling**: Implicit via threshold pivoting

#### 5.2 Convergence of Newton Iteration

The Newton iteration convergence depends on the accuracy of the linear solve. The error propagation is:
\[
\|\mathbf{x}_{k+1} - \mathbf{x}^*\| \leq \frac{1}{2} \|\mathbf{J}^{-1}\| \cdot \|\mathbf{H}\| \cdot \|\mathbf{x}_k - \mathbf{x}^*\|^2 + \|\mathbf{J}^{-1}\| \cdot \|\delta_k\|
\]
where \(\mathbf{H}\) is the Hessian and \(\delta_k\) is the linear solve error.

For quadratic convergence, we need:
\[
\|\delta_k\| < \epsilon_{\text{linear}} \cdot \|\mathbf{F}(\mathbf{x}_k)\|
\]
with \(\epsilon_{\text{linear}} \to 0\) as \(k \to \infty\).

#### 5.3 Monitoring and Diagnostics

The solver tracks:
- **Fill-in ratio**: \(F/\text{nnz} < 5.0\) typically
- **Pivot size**: \(\min_k |A_{kk}^{(k)}| > 10^{-15}\)
- **Growth factor**: \(g_n < 10^6\)
- **Iteration count**: Newton iterations < 100

Failure occurs when:
1. **Singular matrix**: \(\exists k: |A_{kk}^{(k)}| < 10^{-20}\)
2. **Excessive fill-in**: \(F > 10 \cdot \text{nnz}\)
3. **Memory exhaustion**: Pool expansion fails

### 6. Default Parameters and Their Effects

#### 6.1 Critical Threshold Values

| Parameter | Symbol | Default | Effect on Convergence |
|-----------|--------|---------|----------------------|
| Relative pivot threshold | \(\tau_r\) | \(10^{-3}\) | Controls stability vs fill-in trade-off |
| Absolute pivot threshold | \(\tau_a\) | \(10^{-12}\) | Minimum acceptable pivot |
| Minimum pivot | \(\epsilon_{\text{min}}\) | \(10^{-15}\) | Singularity detection threshold |
| Growth factor limit | \(g_{\text{max}}\) | \(10^6\) | Numerical stability limit |
| Fill-in ratio limit | \(\rho_{\text{fill}}\) | 5.0 | Memory usage control |

#### 6.2 Convergence Criteria

The linear solver is considered converged when:
1. **Direct solve**: Residual \(< 10^{-12} \cdot \|\mathbf{b}\|\)
2. **Iterative refinement**: Correction \(< 10^{-12} \cdot \|\mathbf{x}\|\)
3. **Backward error**: \(\|\mathbf{b} - \mathbf{A}\tilde{\mathbf{x}}\| < 10^{-12} \cdot (\|\mathbf{A}\| \cdot \|\tilde{\mathbf{x}}\| + \|\mathbf{b}\|)\)

#### 6.3 Performance Optimization Convergence

The blocked algorithm converges to optimal performance when:
\[
B_{\text{opt}} \approx \sqrt{\frac{C_{\text{cache}}}{8}} \quad (\text{for double precision})
\]
where \(C_{\text{cache}}\) is cache size in bytes. For 32KB L1 cache: \(B_{\text{opt}} \approx 64\).

The memory pool converges to steady-state when:
\[
\frac{\text{Allocations}}{\text{Reuses}} < 0.1
\]
indicating efficient element recycling.

## C Implementation

### 1. Core Data Structures Implementation

#### 1.1 Matrix Element Structure (`spdefs.h`)

The fundamental building block of Ngspice's sparse matrix system is the `spMatrixElement` structure, which implements the mathematical concept of a non-zero matrix entry \( A_{ij} \).

```c
typedef struct spMatrixElement {
    /* Element location and value - maps to mathematical A[i][j] */
    int     Row;                    /* Row index i (1-indexed) */
    int     Col;                    /* Column index j (1-indexed) */
    double  Real;                   /* Real part of A[i][j] */
    double  Imag;                   /* Imaginary part (for AC analysis) */
    
    /* Orthogonal linked list pointers - implements R_i and C_j sets */
    struct spMatrixElement *NextInRow;   /* Next in row list R_i */
    struct spMatrixElement *NextInCol;   /* Next in column list C_j */
    
    /* Factorization data */
    struct spMatrixElement *NextInDiag;  /* For diagonal chaining during pivoting */
    int     Mark;                    /* Garbage collection mark bit */
    
    /* Fill-in tracking - identifies elements created during LU factorization */
    unsigned char IsFillin;          /* 1 if A[i][j] was zero before factorization */
    unsigned char WasFillin;         /* 1 if was fill-in in previous step */
} spMatrixElement;
```

**Mathematical Mapping:**
- `Row` and `Col` correspond to indices \( i \) and \( j \) in \( A_{ij} \)
- `Real` and `Imag` store \( \Re(A_{ij}) \) and \( \Im(A_{ij}) \) for complex matrices in AC analysis
- `NextInRow` implements the sorted row list \( R_i = \{(j, A_{ij}) : A_{ij} \neq 0\} \)
- `NextInCol` implements the sorted column list \( C_j = \{(i, A_{ij}) : A_{ij} \neq 0\} \)
- `IsFillin` tracks whether \( A_{ij} \) was created during the fill-in process \( A_{ij}^{(k+1)} = A_{ij}^{(k)} - \frac{A_{ik}^{(k)} A_{kj}^{(k)}}{A_{kk}^{(k)}} \)

#### 1.2 Matrix Frame Structure (`spdefs.h`)

The `spMatrixFrame` structure is the main container that manages the entire sparse matrix, implementing the mathematical matrix \( \mathbf{A} \in \mathbb{R}^{n \times n} \) (or \( \mathbb{C}^{n \times n} \)).

```c
typedef struct spMatrixFrame {
    /* Matrix dimensions - maps to n in A ∈ ℝ^{n×n} */
    int     Size;                   /* Matrix dimension n */
    int     NumberOfEquations;      /* Actual number of equations (≤ Size) */
    int     ExtSize;                /* Extended size for memory allocation */
    
    /* Element management - implements row/column lists */
    spMatrixElement **FirstInRow;   /* Array of pointers to R_i lists */
    spMatrixElement **FirstInCol;   /* Array of pointers to C_j lists */
    spMatrixElement **Diag;         /* Array of pointers to diagonal A[i][i] */
    spMatrixElement *Elements;      /* Pre-allocated element pool */
    
    /* Memory management */
    spMatrixElement *FreeElement;   /* Free list for element reuse */
    int     AllocatedElements;      /* Total elements allocated in pool */
    int     RemainingElements;      /* Elements available: S_k - nnz */
    int     Fillins;                /* Count of fill-ins F */
    
    /* Pivoting and reordering - implements permutation matrices P_r, P_c */
    int     *IntToExtRowMap;        /* π_r: internal → external row mapping */
    int     *IntToExtColMap;        /* π_c: internal → external column mapping */
    int     *ExtToIntRowMap;        /* π_r^{-1}: external → internal row mapping */
    int     *ExtToIntColMap;        /* π_c^{-1}: external → internal column mapping */
    int     PivotSelectionMethod;   /* SP_NO_PIVOTING, SP_PARTIAL_PIVOTING, etc. */
    
    /* Factorization state */
    int     Factored;               /* 1 if LU factorization exists */
    int     NeedsOrdering;          /* 1 if Markowitz reordering needed */
    int     Singular;               /* 1 if matrix is singular */
    int     SingularRow;            /* Row k where |A_{kk}| < ε_min detected */
    
    /* Workspace for factorization - implements intermediate vectors */
    double  *Intermediate;          /* Workspace vector for solves */
    double  *AbsThreshold;          /* Array of τ_a[j] for threshold pivoting */
    double  RelThreshold;           /* τ_r for relative threshold pivoting */
    
    /* Performance statistics */
    long    AddCount;               /* Counts arithmetic operations */
    long    MultCount;
    long    DivCount;
} spMatrixFrame;
```

**Mathematical Mapping:**
- `Size` = \( n \), the matrix dimension
- `FirstInRow[i]` = head of linked list for \( R_i \)
- `FirstInCol[j]` = head of linked list for \( C_j \)
- `Diag[i]` = pointer to \( A_{ii} \)
- `IntToExtRowMap` and `ExtToIntRowMap` implement the row permutation \( P_r \)
- `IntToExtColMap` and `ExtToIntColMap` implement the column permutation \( P_c \)
- `RelThreshold` = \( τ_r \) (default \( 10^{-3} \))
- `AbsThreshold[j]` = \( τ_a[j] \) (default \( 10^{-12} \))
- `Fillins` = \( F \), the fill-in count

### 2. Memory Allocation System (`spalloc.c`)

#### 2.1 Matrix Creation and Initialization

The `spCreate` function allocates and initializes a sparse matrix frame, implementing the mathematical initialization of matrix \( \mathbf{A} \) with identity permutation mappings.

```c
spMatrixFrame* spCreate(int Size, int ExtSize, int PivotMethod)
{
    spMatrixFrame *Matrix = (spMatrixFrame*)malloc(sizeof(spMatrixFrame));
    if (Matrix == NULL) return NULL;
    
    /* Initialize dimensions */
    Matrix->Size = Size;
    Matrix->ExtSize = ExtSize;
    Matrix->NumberOfEquations = Size;
    Matrix->PivotSelectionMethod = PivotMethod;
    
    /* Allocate header arrays (1-indexed, so size+1) */
    Matrix->FirstInRow = (spMatrixElement**)calloc(Size+1, sizeof(spMatrixElement*));
    Matrix->FirstInCol = (spMatrixElement**)calloc(Size+1, sizeof(spMatrixElement*));
    Matrix->Diag = (spMatrixElement**)calloc(Size+1, sizeof(spMatrixElement*));
    
    /* Allocate mapping arrays - initialize to identity permutation */
    Matrix->IntToExtRowMap = (int*)malloc((Size+1) * sizeof(int));
    Matrix->IntToExtColMap = (int*)malloc((Size+1) * sizeof(int));
    Matrix->ExtToIntRowMap = (int*)malloc((ExtSize+1) * sizeof(int));
    Matrix->ExtToIntColMap = (int*)malloc((ExtSize+1) * sizeof(int));
    
    /* Initialize identity mappings: π_r(i) = i, π_c(j) = j */
    for (int i = 1; i <= Size; i++) {
        Matrix->IntToExtRowMap[i] = i;
        Matrix->IntToExtColMap[i] = i;
        Matrix->ExtToIntRowMap[i] = i;
        Matrix->ExtToIntColMap[i] = i;
    }
    
    /* Allocate element pool with initial size S_0 = SP_DEFAULT_ALLOC_SIZE */
    Matrix->AllocatedElements = SP_DEFAULT_ALLOC_SIZE;
    Matrix->RemainingElements = SP_DEFAULT_ALLOC_SIZE;
    Matrix->Elements = (spMatrixElement*)malloc(SP_DEFAULT_ALLOC_SIZE * sizeof(spMatrixElement));
    
    /* Initialize free list - all elements in pool are initially free */
    Matrix->FreeElement = Matrix->Elements;
    for (int i = 0; i < SP_DEFAULT_ALLOC_SIZE - 1; i++) {
        Matrix->Elements[i].NextInRow = &Matrix->Elements[i+1];
        Matrix->Elements[i].Mark = 0;
    }
    Matrix->Elements[SP_DEFAULT_ALLOC_SIZE-1].NextInRow = NULL;
    
    /* Initialize workspace vectors */
    Matrix->Intermediate = (double*)malloc((Size+1) * sizeof(double));
    Matrix->AbsThreshold = (double*)malloc((Size+1) * sizeof(double));
    
    /* Set default thresholds: τ_r = 1e-3, τ_a[j] = 1e-12 */
    for (int i = 1; i <= Size; i++) {
        Matrix->AbsThreshold[i] = SP_DEFAULT_ABS_THRESHOLD;
    }
    Matrix->RelThreshold = SP_DEFAULT_REL_THRESHOLD;
    
    /* Initialize statistics */
    Matrix->Fillins = 0;
    Matrix->AddCount = 0;
    Matrix->MultCount = 0;
    Matrix->DivCount = 0;
    Matrix->Factored = 0;
    Matrix->NeedsOrdering = 1;
    Matrix->Singular = 0;
    
    return Matrix;
}
```

**Mathematical Mapping:**
- Memory allocation follows \( M_{\text{total}} = O(n)_{\text{headers}} + O(\text{nnz})_{\text{elements}} + O(n)_{\text{mappings}} + O(n)_{\text{workspace}} \)
- Identity permutation initialization: \( \pi_r(i) = i, \pi_c(j) = j \)
- Default thresholds: \( τ_r = 10^{-3}, τ_a[j] = 10^{-12} \)
- Initial pool size: \( S_0 = 1000 \) elements

#### 2.2 Dynamic Pool Expansion

The `spGetFreeElement` function implements the dynamic memory pool growth strategy \( S_{k+1} = \max(\lfloor αS_k \rfloor, S_k + β) \).

```c
spMatrixElement* spGetFreeElement(spMatrixFrame *Matrix)
{
    if (Matrix->FreeElement == NULL) {
        /* Need to expand pool: S_new = max(α·S_old, S_old + β) */
        int NewAlloc = (int)(Matrix->AllocatedElements * SP_GROWTH_FACTOR);
        if (NewAlloc < Matrix->AllocatedElements + 100) {
            NewAlloc = Matrix->AllocatedElements + 100;
        }
        
        /* Reallocate pool with new size */
        spMatrixElement *NewPool = (spMatrixElement*)realloc(
            Matrix->Elements, NewAlloc * sizeof(spMatrixElement));
        
        if (NewPool == NULL) return NULL;
        
        /* Update pointers */
        int OldSize = Matrix->AllocatedElements;
        Matrix->Elements = NewPool;
        Matrix->AllocatedElements = NewAlloc;
        
        /* Add new elements to free list */
        for (int i = OldSize; i < NewAlloc - 1; i++) {
            Matrix->Elements[i].NextInRow = &Matrix->Elements[i+1];
            Matrix->Elements[i].Mark = 0;
        }
        Matrix->Elements[NewAlloc-1].NextInRow = Matrix->FreeElement;
        Matrix->FreeElement = &Matrix->Elements[OldSize];
        
        /* Update remaining elements count */
        Matrix->RemainingElements += (NewAlloc - OldSize);
    }
    
    /* Get element from free list */
    spMatrixElement *Element = Matrix->FreeElement;
    Matrix->FreeElement = Element->NextInRow;
    
    /* Initialize element pointers */
    Element->NextInRow = NULL;
    Element->NextInCol = NULL;
    Element->NextInDiag = NULL;
    
    return Element;
}
```

**Mathematical Mapping:**
- Growth factor \( α = 1.5 \) (`SP_GROWTH_FACTOR`)
- Minimum increment \( β = 100 \)
- Memory expansion follows recurrence: \( S_{k+1} = \max(\lfloor 1.5S_k \rfloor, S_k + 100) \)

#### 2.3 Element Management

The `spGetElement` function finds or creates a matrix element \( A_{ij} \), implementing the mathematical operation of accessing/creating a non-zero entry.

```c
spMatrixElement* spGetElement(spMatrixFrame *Matrix, int Row, int Col)
{
    /* Convert to internal ordering using permutation mappings */
    int intRow = Matrix->ExtToIntRowMap[Row];  /* i' = π_r^{-1}(i) */
    int intCol = Matrix->ExtToIntColMap[Col];  /* j' = π_c^{-1}(j) */
    
    /* Search in row list R_{i'} for column j' */
    spMatrixElement *pPrevInRow = NULL;
    spMatrixElement *pElement = Matrix->FirstInRow[intRow];
    
    while (pElement != NULL && pElement->Col < intCol) {
        pPrevInRow = pElement;
        pElement = pElement->NextInRow;
    }
    
    /* Element exists at (i', j') */
    if (pElement != NULL && pElement->Col == intCol) {
        return pElement;
    }
    
    /* Create new element - this may be a fill-in */
    spMatrixElement *pNewElement = spGetFreeElement(Matrix);
    if (pNewElement == NULL) return NULL;
    
    /* Initialize new element */
    pNewElement->Row = intRow;
    pNewElement->Col = intCol;
    pNewElement->Real = 0.0;
    pNewElement->Imag = 0.0;
    
    /* Determine if this is a fill-in: A[i'][j'] was previously zero */
    pNewElement->IsFillin = (pElement == NULL) ? 0 : 1;
    
    /* Insert into row list R_{i'} maintaining sorted order by j' */
    pNewElement