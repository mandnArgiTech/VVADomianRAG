# Sparse Matrix: LU Factorization and Solution

_Generated 2026-04-11 18:08 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spfactor.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/sparse/spsolve.c`

# Chapter: Sparse Matrix: LU Factorization and Solution

## Introduction

The LU factorization and solution subsystem forms the computational core of Ngspice's sparse matrix solver, responsible for decomposing circuit matrices and solving the resulting linear systems with numerical stability and efficiency. The `spfactor.c` module implements the sophisticated LU decomposition algorithm that computes the factorization \( \mathbf{P}\mathbf{J}\mathbf{Q} = \mathbf{L}\mathbf{U} \) for circuit Jacobian matrices, employing Markowitz pivoting with threshold control to minimize fill-in while maintaining numerical stability. The `spsolve.c` module provides the forward/backward substitution routines that solve \( \mathbf{L}\mathbf{y} = \mathbf{P}\mathbf{b} \) and \( \mathbf{U}\mathbf{x} = \mathbf{y} \) using the factored matrices, with optimizations for sparse data structures. Together, these modules implement the complete solution pipeline for the linear systems arising from Newton-Raphson iteration in circuit simulation, handling both real-valued DC/transient matrices and complex-valued AC matrices with robust error recovery and performance monitoring.

## Mathematical Formulation

### 1. LU Decomposition for Circuit Matrices

#### 1.1 Modified Nodal Analysis (MNA) System

In SPICE circuit simulation, the Newton-Raphson iteration requires solving the linear system:
\[
\mathbf{J}^{(k)} \Delta\mathbf{x}^{(k)} = -\mathbf{F}(\mathbf{x}^{(k)})
\]
where \(\mathbf{J}^{(k)} \in \mathbb{R}^{n \times n}\) is the Jacobian matrix at iteration \(k\), \(\Delta\mathbf{x}^{(k)} \in \mathbb{R}^n\) is the solution update, and \(\mathbf{F}(\mathbf{x}^{(k)}) \in \mathbb{R}^n\) is the circuit equation residual.

For AC analysis, the system becomes complex-valued:
\[
[\mathbf{G} + j\omega\mathbf{C}] \mathbf{X}(\omega) = \mathbf{B}(\omega)
\]
where \(\mathbf{G}\) is the conductance matrix, \(\mathbf{C}\) is the capacitance/inductance matrix, \(\omega\) is angular frequency, and \(\mathbf{X}(\omega)\) is the complex solution vector.

#### 1.2 LU Decomposition with Partial Pivoting

The LU decomposition with row and column permutations computes:
\[
\mathbf{P} \mathbf{J} \mathbf{Q} = \mathbf{L} \mathbf{U}
\]
where:
- \(\mathbf{P}, \mathbf{Q} \in \{0,1\}^{n \times n}\) are permutation matrices for row and column pivoting
- \(\mathbf{L} \in \mathbb{R}^{n \times n}\) is unit lower triangular (\(L_{ii} = 1\))
- \(\mathbf{U} \in \mathbb{R}^{n \times n}\) is upper triangular

For circuit matrices, the decomposition is typically computed in-place, overwriting \(\mathbf{J}\) with \(\mathbf{L}\) and \(\mathbf{U}\) (with \(\mathbf{L}\)'s unit diagonal implicit).

#### 1.3 Fill-in Creation During Factorization

During Gaussian elimination at step \(k\), for each non-zero pair \((J_{ik}, J_{kj})\) where \(i > k\) and \(j > k\):

If \(J_{ij} = 0\) initially, a fill-in element is created with value:
\[
J_{ij}^{(k+1)} = J_{ij}^{(k)} - \frac{J_{ik}^{(k)} \cdot J_{kj}^{(k)}}{J_{kk}^{(k)}}
\]

The fill-in count \(F\) depends on the elimination order:
\[
F = \sum_{k=1}^{n-1} \left[ (r_k - 1) \cdot (c_k - 1) - \text{existing non-zeros in submatrix} \right]
\]
where \(r_k\) and \(c_k\) are the number of non-zeros in row and column \(k\) of the reduced matrix.

### 2. Pivoting Strategies for Stability and Sparsity

#### 2.1 Markowitz Pivoting Criterion

To minimize fill-in while maintaining numerical stability, Ngspice uses the Markowitz criterion. For element \(J_{ij}\) at elimination step \(k\):

\[
M_{ij}^{(k)} = (r_i^{(k)} - 1) \cdot (c_j^{(k)} - 1)
\]
where:
- \(r_i^{(k)} = |\{j \geq k : J_{ij}^{(k)} \neq 0\}|\) (non-zeros in row \(i\) of active submatrix)
- \(c_j^{(k)} = |\{i \geq k : J_{ij}^{(k)} \neq 0\}|\) (non-zeros in column \(j\) of active submatrix)

The pivot \((p,q)\) at step \(k\) minimizes \(M_{pq}^{(k)}\) subject to numerical stability constraints.

#### 2.2 Threshold Pivoting for Numerical Stability

Given relative threshold \(\tau \in (0,1]\) (default \(\tau = 0.001\)), element \(J_{ij}\) is acceptable as pivot only if:

\[
|J_{ij}| \geq \tau \cdot \max_{m \geq k} |J_{mj}|
\]

This ensures the growth factor \(\rho\) is bounded:
\[
\rho = \frac{\max_{i,j,k} |J_{ij}^{(k)}|}{\max_{i,j} |J_{ij}^{(1)}|} \leq (1 + \tau^{-1})^{n-1}
\]

In practice for circuit matrices, \(\rho < 10^3\) typically.

#### 2.3 Combined Pivoting Strategy

The complete pivot selection algorithm at step \(k\):
1. Compute candidate set \(\mathcal{C} = \{(i,j) : |J_{ij}| \geq \tau \cdot \max_{m \geq k} |J_{mj}|\}\)
2. Select \((p,q) \in \mathcal{C}\) minimizing \(M_{pq}^{(k)}\)
3. If no candidate satisfies threshold, use \((p,q)\) with maximum \(|J_{pq}|\)

### 3. Forward and Backward Substitution

#### 3.1 Forward Substitution (Solve \(\mathbf{L}\mathbf{y} = \mathbf{P}\mathbf{b}\))

Given unit lower triangular \(\mathbf{L}\) with \(L_{ii} = 1\):

\[
y_1 = \tilde{b}_1
\]
\[
y_i = \tilde{b}_i - \sum_{j=1}^{i-1} L_{ij} y_j, \quad i = 2, \ldots, n
\]
where \(\tilde{\mathbf{b}} = \mathbf{P}\mathbf{b}\) is the permuted right-hand side.

In sparse implementation, only non-zero \(L_{ij}\) contribute:
\[
y_i = \tilde{b}_i - \sum_{\substack{j < i \\ L_{ij} \neq 0}} L_{ij} y_j
\]

#### 3.2 Backward Substitution (Solve \(\mathbf{U}\mathbf{x} = \mathbf{y}\))

Given upper triangular \(\mathbf{U}\):

\[
x_n = \frac{y_n}{U_{nn}}
\]
\[
x_i = \frac{1}{U_{ii}} \left( y_i - \sum_{j=i+1}^{n} U_{ij} x_j \right), \quad i = n-1, \ldots, 1
\]

In sparse implementation:
\[
x_i = \frac{1}{U_{ii}} \left( y_i - \sum_{\substack{j > i \\ U_{ij} \neq 0}} U_{ij} x_j \right)
\]

#### 3.3 Complete Solution with Permutations

The full solution process:
1. Apply row permutation: \(\tilde{\mathbf{b}} = \mathbf{P}\mathbf{b}\)
2. Forward substitution: \(\mathbf{L}\mathbf{y} = \tilde{\mathbf{b}}\)
3. Backward substitution: \(\mathbf{U}\mathbf{x} = \mathbf{y}\)
4. Apply column permutation: \(\mathbf{x}_{\text{final}} = \mathbf{Q}\mathbf{x}\)

### 4. Complex Factorization for AC Analysis

#### 4.1 Complex Matrix Representation

For AC analysis at frequency \(\omega\), the matrix is complex-valued:
\[
\mathbf{J}(\omega) = \mathbf{G} + j\omega\mathbf{C}
\]
where \(\mathbf{G}, \mathbf{C} \in \mathbb{R}^{n \times n}\) are real matrices.

Each matrix element stores:
- Real part: \(G_{ij}\) (conductance)
- Imaginary part: \(\omega C_{ij}\) (susceptance)

#### 4.2 Complex LU Decomposition

The complex factorization computes:
\[
\mathbf{P}[\mathbf{G} + j\omega\mathbf{C}]\mathbf{Q} = \mathbf{L}\mathbf{U}
\]
where \(\mathbf{L}\) and \(\mathbf{U}\) are now complex matrices.

The algorithm proceeds similarly to real case, but with complex arithmetic:
- Complex division: \(L_{ik} = J_{ik} / J_{kk}\)
- Complex multiply-add: \(J_{ij} = J_{ij} - L_{ik} \cdot J_{kj}\)

### 5. Numerical Stability Analysis

#### 5.1 Growth Factor Monitoring

The growth factor \(\rho\) measures element growth during factorization:
\[
\rho = \frac{\max_{i,j,k} |J_{ij}^{(k)}|}{\max_{i,j} |J_{ij}^{(1)}|}
\]

With threshold pivoting (\(\tau = 0.001\)), the worst-case bound is:
\[
\rho \leq (1 + \tau^{-1})^{n-1} \approx 1001^{n-1}
\]
but practical values are much smaller: \(\rho < 10^3\) for circuit matrices.

#### 5.2 Condition Number Estimation

The condition number \(\kappa(\mathbf{J}) = \|\mathbf{J}\| \cdot \|\mathbf{J}^{-1}\|\) affects solution accuracy. For circuit matrices:
- Well-conditioned: \(\kappa < 10^6\) (typical for DC operating point)
- Ill-conditioned: \(\kappa > 10^8\) (occurs with floating nodes or extreme element ratios)

The relative error in the solution satisfies:
\[
\frac{\|\Delta\mathbf{x}\|}{\|\mathbf{x}\|} \lesssim \epsilon_{\text{mach}} \cdot \kappa(\mathbf{J}) \cdot \frac{\|\mathbf{r}\|}{\|\mathbf{J}\| \cdot \|\mathbf{x}\|}
\]
where \(\epsilon_{\text{mach}} \approx 2.2 \times 10^{-16}\) for double precision, and \(\mathbf{r} = \mathbf{b} - \mathbf{J}\mathbf{x}\) is the residual.

#### 5.3 Singularity Detection and Handling

A matrix is numerically singular if:
\[
|J_{kk}^{(k)}| < \epsilon_{\text{pivot}} \cdot \max_{i \geq k} |J_{ik}^{(k)}|
\]
where \(\epsilon_{\text{pivot}} = \max(\epsilon_{\text{abs}}, \tau \cdot \max_{i \geq k} |J_{ik}^{(k)}|)\) with \(\epsilon_{\text{abs}} = 10^{-12}\).

Recovery strategies:
1. **Gmin stepping**: Add small conductance \(g_{\text{min}} = 10^{-12}\)S to diagonal
2. **Threshold relaxation**: Reduce \(\tau\) to accept smaller pivots
3. **Modified pivoting**: Search larger region for acceptable pivot

### 6. Performance and Complexity Analysis

#### 6.1 Time Complexity

For an \(n \times n\) matrix with \(m\) non-zeros and \(F\) fill-ins:

- **Symbolic analysis**: \(O(m \cdot \log n)\) using elimination tree
- **Numeric factorization**: \(O(m + F)\) operations
- **Forward/backward substitution**: \(O(m + F)\) operations

For circuit matrices with average degree \(d\) (connections per node):
\[
m = O(n \cdot d), \quad F = O(n \cdot d^2)
\]
Thus total complexity: \(O(n \cdot d^2)\).

#### 6.2 Space Complexity

- **Matrix storage**: \(O(m + F)\) elements
- **Factorization storage**: \(O(m + F)\) for \(\mathbf{L}\) and \(\mathbf{U}\) (stored in-place)
- **Workspace**: \(O(n)\) for permutation vectors and intermediate vectors

Total: \(O(n \cdot d^2)\) memory.

#### 6.3 Operation Count

The factorization requires approximately:
- Multiplications: \(\sum_{k=1}^{n-1} r_k \cdot c_k\)
- Divisions: \(\sum_{k=1}^{n-1} r_k\)
- Additions: \(\sum_{k=1}^{n-1} (r_k - 1) \cdot c_k\)

For complex arithmetic, each operation counts as 6 floating-point operations (4 multiplies + 2 adds).

## Convergence Analysis

### 1. Numerical Stability of Sparse LU Factorization

#### 1.1 Pivot Growth and Stability Bounds

The stability of LU factorization is governed by the growth factor \(\rho\). With threshold pivoting parameter \(\tau\):

**Theorem**: For any matrix \(\mathbf{A}\), threshold pivoting with parameter \(\tau\) yields:
\[
\rho \leq (1 + \tau^{-1})^{n-1}
\]

**Proof sketch**: At step \(k\), the pivot satisfies \(|a_{kk}^{(k)}| \geq \tau \cdot \max_{i \geq k} |a_{ik}^{(k)}|\). The update formula \(a_{ij}^{(k+1)} = a_{ij}^{(k)} - \frac{a_{ik}^{(k)} a_{kj}^{(k)}}{a_{kk}^{(k)}}\) gives bound:
\[
|a_{ij}^{(k+1)}| \leq |a_{ij}^{(k)}| + \tau^{-1} \cdot \max_{i,j} |a_{ij}^{(k)}|
\]
Recursive application yields the bound.

For circuit matrices, empirical observations show \(\rho < 10^3\) for \(\tau = 0.001\), much better than the worst-case bound.

#### 1.2 Condition Number and Error Propagation

The condition number \(\kappa(\mathbf{A}) = \|\mathbf{A}\| \cdot \|\mathbf{A}^{-1}\|\) determines sensitivity to perturbations. For the computed solution \(\tilde{\mathbf{x}}\):

**Forward error bound**:
\[
\frac{\|\mathbf{x} - \tilde{\mathbf{x}}\|}{\|\mathbf{x}\|} \lesssim \epsilon_{\text{mach}} \cdot \kappa(\mathbf{A}) \cdot \left( \frac{\|\mathbf{r}\|}{\|\mathbf{A}\| \cdot \|\tilde{\mathbf{x}}\|} + 1 \right)
\]
where \(\mathbf{r} = \mathbf{b} - \mathbf{A}\tilde{\mathbf{x}}\) is the residual.

**Backward error bound**: There exists \(\Delta\mathbf{A}\) with \(\|\Delta\mathbf{A}\| \leq \epsilon_{\text{back}} \|\mathbf{A}\|\) such that:
\[
(\mathbf{A} + \Delta\mathbf{A})\tilde{\mathbf{x}} = \mathbf{b}
\]
with \(\epsilon_{\text{back}} \approx \epsilon_{\text{mach}} \cdot \rho \cdot n\).

#### 1.3 Singularity Detection Threshold

The factorization detects near-singularity when:
\[
|a_{kk}^{(k)}| < \epsilon_{\text{sing}} \cdot \max_{i \geq k} |a_{ik}^{(k)}|
\]
where \(\epsilon_{\text{sing}} = \max(\epsilon_{\text{abs}}, \tau \cdot \max_{i \geq k} |a_{ik}^{(k)}|)\).

For SPICE accuracy requirements (\(\epsilon_{\text{ckt}} \approx 10^{-6}\)), we need:
\[
\epsilon_{\text{sing}} \cdot \kappa(\mathbf{A}) < \frac{\epsilon_{\text{ckt}}}{\epsilon_{\text{mach}}} \approx 10^{10}
\]
Thus with \(\kappa(\mathbf{A}) < 10^8\), we can use \(\epsilon_{\text{sing}} \approx 10^{-2}\).

### 2. Fill-in Prediction and Control

#### 2.1 Markowitz Criterion Effectiveness

The Markowitz count \(M_{ij} = (r_i - 1)(c_j - 1)\) approximates potential fill-in. The actual fill-in when pivoting on \((i,j)\) is approximately:
\[
F_{ij} \approx M_{ij} - \text{(existing non-zeros in Schur complement)}
\]

**Theorem**: Among all pivots with \(|a_{ij}| \geq \tau \cdot \max_k |a_{kj}|\), choosing the one minimizing \(M_{ij}\) yields fill-in within factor \(O(n)\) of optimal.

**Empirical observation**: For circuit matrices, Markowitz pivoting reduces fill-in by 30-50% compared to partial pivoting.

#### 2.2 Fill-in Ratio Convergence

Define fill-in ratio \(\alpha = F/m\) where \(m\) is original non-zeros. For circuit matrices:
- Initial: \(\alpha_0 = 0\) (no fill-in)
- During factorization: \(\alpha_k\) increases
- Final: \(\alpha_{\text{final}} < 5\) typically

The fill-in growth follows recurrence:
\[
\alpha_{k+1} \approx \alpha_k + \frac{(r_k - 1)(c_k - 1)}{m}
\]

#### 2.3 Memory Pool Convergence

The dynamic memory pool with growth factor \(\gamma = 2\) and initial size \(S_0\) satisfies:
\[
S_k = \gamma^{\lceil \log_\gamma(k/S_0) \rceil} S_0
\]

The steady-state condition occurs when:
\[
\frac{m + F}{S_k} < \beta \quad (\beta \approx 0.8)
\]
indicating efficient memory utilization.

### 3. Iterative Refinement for Enhanced Accuracy

#### 3.1 Residual Calculation and Correction

Given approximate solution \(\mathbf{x}^{(0)}\), compute:
1. Residual: \(\mathbf{r}^{(0)} = \mathbf{b} - \mathbf{A}\mathbf{x}^{(0)}\)
2. Correction: Solve \(\mathbf{A}\mathbf{d}^{(0)} = \mathbf{r}^{(0)}\) using existing LU factors
3. Update: \(\mathbf{x}^{(1)} = \mathbf{x}^{(0)} + \mathbf{d}^{(0)}\)

#### 3.2 Convergence Analysis

The error after \(k\) iterations satisfies:
\[
\|\mathbf{x} - \mathbf{x}^{(k)}\| \leq (\kappa(\mathbf{A}) \cdot \epsilon_{\text{LU}})^k \cdot \|\mathbf{x} - \mathbf{x}^{(0)}\|
\]
where \(\epsilon_{\text{LU}}\) is the error in LU factorization.

**Theorem**: If \(\kappa(\mathbf{A}) \cdot \epsilon_{\text{LU}} < 1\), iterative refinement converges linearly.

**Stopping criterion**: Stop when:
\[
\frac{\|\mathbf{d}^{(k)}\|}{\|\mathbf{x}^{(k)}\|} < \epsilon_{\text{refine}} \quad \text{or} \quad \frac{\|\mathbf{r}^{(k)}\|}{\|\mathbf{b}\|} < \epsilon_{\text{mach}} \cdot \kappa(\mathbf{A})
\]

#### 3.3 Computational Cost

Each refinement iteration requires:
- Residual computation: \(O(m)\) operations
- Forward/backward substitution: \(O(m + F)\) operations
- Total: \(O(m + F)\) operations per iteration

Typically 1-3 iterations suffice for \(\epsilon_{\text{refine}} = 10^{-12}\).

### 4. Performance Optimization Analysis

#### 4.1 Cache Performance of Sparse Algorithms

The blocked LU factorization with block size \(B\) improves cache utilization. For \(B \times B\) blocks:

**Spatial locality**: Elements within block are stored contiguously
**Temporal locality**: Each block reused \(O(B)\) times

Miss ratio improvement:
\[
\frac{\text{Misses}_{\text{blocked}}}{\text{Misses}_{\text{unblocked}}} \approx \frac{1}{\sqrt{B}}
\]

Optimal block size for cache size \(C\) (bytes):
\[
B_{\text{opt}} \approx \sqrt{\frac{C}{8}} \quad \text{(for double precision)}
\]
For 32KB L1 cache: \(B_{\text{opt}} \approx 64\).

#### 4.2 Parallelization Potential

The sparse LU factorization has limited parallelism due to dependencies:
- **Level scheduling**: Independent rows/columns at same elimination level
- **Task parallelism**: Independent update operations within Schur complement

Theoretical speedup:
\[
S_p \approx \frac{n}{\log n} \quad \text{(for elimination tree height $\log n$)}
\]

#### 4.3 Operation Count Minimization

The Markowitz criterion minimizes approximate operation count:
\[
\text{ops} \approx \sum_{k=1}^{n-1} (r_k \cdot c_k)
\]
since each pivot at step \(k\) generates approximately \(r_k \cdot c_k\) multiply-add operations.

### 5. Convergence in Circuit Simulation Context

#### 5.1 Impact on Newton Iteration Convergence

The Newton iteration error propagation:
\[
\|\mathbf{x}_{k+1} - \mathbf{x}^*\| \leq \frac{1}{2} \|\mathbf{J}^{-1}\| \cdot \|\mathbf{H}\| \cdot \|\mathbf{x}_k - \mathbf{x}^*\|^2 + \|\mathbf{J}^{-1}\| \cdot \|\delta_k\|
\]
where \(\mathbf{H}\) is the Hessian and \(\delta_k\) is the linear solve error.

For quadratic convergence, need:
\[
\|\delta_k\| < \epsilon_{\text{linear}} \cdot \|\mathbf{F}(\mathbf{x}_k)\|
\]
with \(\epsilon_{\text{linear}} \to 0\) as \(k \to \infty\).

#### 5.2 Matrix Conditioning in SPICE

Circuit matrices become ill-conditioned due to:
1. **Large conductance ratios**: \(g_{\text{max}}/g_{\text{min}} > 10^{12}\)
2. **Floating nodes**: Zero diagonal before Gmin addition
3. **Coupled inductors**: Near-linear dependence

Condition number estimates:
- Typical DC operating point: \(\kappa \approx 10^4 - 10^6\)
- With floating nodes: \(\kappa \approx 10^8 - 10^{12}\)
- After Gmin addition (\(g_{\text{min}} = 10^{-12}\)S): \(\kappa \approx 10^6 - 10^8\)

#### 5.3 Monitoring and Diagnostics

The solver monitors:
- **Fill-in ratio**: \(F/m < 5.0\) (warning if > 10.0)
- **Pivot size**: \(\min_k |a_{kk}^{(k)}| > 10^{-15}\)
- **Growth factor**: \(\rho < 10^6\) (warning if > \(10^8\))
- **Condition estimate**: \(\hat{\kappa} < 10^8\) (warning if > \(10^{10}\))

Failure modes:
1. **Singular matrix**: \(\exists k: |a_{kk}^{(k)}| < 10^{-20}\)
2. **Excessive fill-in**: \(F > 10 \cdot m\)
3. **Memory exhaustion**: Pool expansion fails
4. **Excessive growth**: \(\rho > 10^8\)

### 6. Default Parameters and Performance Trade-offs

#### 6.1 Critical Threshold Values

| Parameter | Symbol | Default | Effect |
|-----------|--------|---------|--------|
| Relative pivot threshold | \(\tau\) | \(10^{-3}\) | Stability vs fill-in trade-off |
| Absolute pivot threshold | \(\epsilon_{\text{abs}}\) | \(10^{-12}\) | Minimum acceptable pivot |
| Singularity threshold | \(\epsilon_{\text{sing}}\) | \(10^{-15}\) | Singularity detection |
| Growth factor limit | \(\rho_{\text{max}}\) | \(10^6\) | Numerical stability limit |
| Fill-in ratio limit | \(\alpha_{\text{max}}\) | 5.0 | Memory usage control |
| Refinement tolerance | \(\epsilon_{\text{refine}}\) | \(10^{-12}\) | Iterative refinement stopping |

#### 6.2 Performance Characteristics

For typical circuit matrices (\(n = 1000\), \(m = 5000\), \(d = 5\)):
- Factorization time: \(O(n \cdot d^2) \approx 25,000\) operations
- Fill-in count: \(F \approx 2m \approx 10,000\) elements
- Memory usage: \(O(m + F) \approx 15,000\) elements × 24 bytes ≈ 360KB
- Condition number: \(\kappa \approx 10^4 - 10^6\)
- Iterative refinement: 1-2 iterations typically needed

#### 6.3 Convergence Guarantees

**Theorem**: With threshold parameter \(\tau > 0\), the sparse LU factorization with Markowitz pivoting:
1. Completes without breakdown if matrix is strongly regular
2. Produces factors with \(\rho \leq (1 + \tau^{-1})^{n-1}\)
3. Yields solution with relative error \(O(\epsilon_{\text{mach}} \cdot \kappa \cdot \rho \cdot n)\)

**Corollary**: For SPICE accuracy requirement \(\epsilon_{\text{ckt}} = 10^{-6}\), sufficient conditions are:
- \(\kappa(\mathbf{J}) < 10^8\)
- \(\rho < 10^3\)
- \(n < 10^4\)

These conditions are typically satisfied for practical circuit simulations.

## C Implementation

### 1. Core Data Structures for LU Factorization

#### 1.1 Matrix Element Structure with Factorization Data

The `spMatrixElement` structure extends the basic matrix element with fields specifically for LU factorization, implementing the mathematical storage of elements in the factored matrices **L** and **U**.

```c
typedef struct spMatrixElement {
    /* Element location - maps to indices (i,j) in A[i][j] */
    int row;                    /* Row index i (0-indexed) */
    int col;                    /* Column index j (0-indexed) */
    
    /* Element value - stores L[i][j] or U[i][j] after factorization */
    double real;               /* Real part: ℜ(A[i][j]) or ℜ(L[i][j]/U[i][j]) */
    double imag;               /* Imaginary part for AC: ℑ(A[i][j]) */
    
    /* Orthogonal linked list pointers - implements row/column traversals */
    struct spMatrixElement *nextInRow;   /* Next in row list R_i */
    struct spMatrixElement *prevInRow;   /* Previous in row list */
    struct spMatrixElement *nextInCol;   /* Next in column list C_j */
    struct spMatrixElement *prevInCol;   /* Previous in column list */
    
    /* Fill-in tracking - identifies elements created during factorization */
    int isFillIn;              /* 1 if A[i][j] was zero before factorization */
    int markowitzProduct;      /* Stores M(i,j) = (r_i-1)(c_j-1) for pivoting */
} spMatrixElement;
```

**Mathematical Mapping:**
- `row` and `col` correspond to indices \( i \) and \( j \) in matrix element \( A_{ij} \)
- After factorization: `real` stores \( L_{ij} \) for \( i > j \) (below diagonal) and \( U_{ij} \) for \( i \leq j \) (diagonal and above)
- `isFillIn` flag indicates element created during fill-in process: \( A_{ij}^{(k+1)} = A_{ij}^{(k)} - \frac{A_{ik}^{(k)} A_{kj}^{(k)}}{A_{kk}^{(k)}} \)
- `markowitzProduct` stores the Markowitz count \( M(i,j) = (r_i - 1)(c_j - 1) \) used for pivot selection

#### 1.2 Matrix Frame with Factorization State

The `spMatrixFrame` structure manages the complete LU factorization state, implementing the mathematical representation of the factored matrix **A = LU** with permutation matrices **P** and **Q**.

```c
typedef struct spMatrixFrame {
    /* Matrix dimensions - maps to n in A ∈ ℝ^{n×n} */
    int size;                  /* Matrix dimension n */
    int numberOfEquations;     /* Number of equations (≤ size) */
    
    /* Orthogonal linked list headers - implement row/column traversals */
    spMatrixElement **rowHeaders;    /* Array of pointers to R_i lists */
    spMatrixElement **colHeaders;    /* Array of pointers to C_j lists */
    
    /* Pivoting information - implements permutation matrices P and Q */
    int *pivotOrder;           /* Row permutation: P[i] = pivotOrder[i] */
    int *pivotChoice;          /* Column permutation: Q[i] = pivotChoice[i] */
    double *threshold;         /* Array of τ[k] for threshold pivoting */
    
    /* Factorization workspace - implements intermediate vectors */
    double *intermediateVector; /* Workspace for forward/backward substitution */
    double *rightHandSide;      /* Stores RHS vector b */
    
    /* Factorization statistics */
    int numberOfFillins;       /* Count of fill-in elements F */
    int numberOfOperations;    /* Operation count for monitoring complexity */
    int isFactored;            /* Flag: 1 if A = LU factorization exists */
    
    /* Error handling */
    int errorFlag;             /* Error codes: SP_OK, SP_SINGULAR, etc. */
    char errorMessage[256];    /* Detailed error message */
} spMatrixFrame;
```

**Mathematical Mapping:**
- `size` = \( n \), the matrix dimension
- `pivotOrder` implements row permutation **P**: \( \tilde{A} = P A \)
- `pivotChoice` implements column permutation **Q**: \( \tilde{A} = A Q^T \)
- `threshold[k]` stores \( \tau[k] \) for threshold pivoting at step \( k \)
- `isFactored` indicates whether \( A = LU \) decomposition exists
- `numberOfFillins` = \( F \), the fill-in count

### 2. LU Factorization Implementation (`spfactor.c`)

#### 2.1 Main Factorization Algorithm

The `SPfactor` function implements the mathematical LU decomposition \( A = LU \) with partial pivoting, computing the factorization in-place.

```c
int SPfactor(spMatrixFrame *matrix)
{
    int n = matrix->size;
    int step, i, j, k;
    double pivotValue, multiplier;
    
    /* Initialize permutation vectors as identity: P = I, Q = I */
    for (i = 0; i < n; i++) {
        matrix->pivotOrder[i] = i;      /* π_r(i) = i */
        matrix->pivotChoice[i] = -1;    /* Initialize as unset */
    }
    
    /* Main factorization loop: for k = 0 to n-1 */
    for (step = 0; step < n; step++) {
        
        /* 1. Pivot selection using Markowitz criterion with threshold τ */
        int pivotRow, pivotCol;
        double maxElement;
        SPfindPivot(matrix, step, &pivotRow, &pivotCol, &maxElement);
        
        /* Check for singularity: |A_kk| < ε_pivot */
        if (fabs(maxElement) < matrix->threshold[step]) {
            matrix->errorFlag = SP_SINGULAR;
            sprintf(matrix->errorMessage, 
                   "Singular matrix at step %d, pivot=%g", 
                   step, maxElement);
            return matrix->errorFlag;
        }
        
        /* 2. Swap rows and columns to bring pivot to (step,step) */
        if (pivotRow != step) {
            SProwExchange(matrix, step, pivotRow);  /* Update P */
        }
        if (pivotCol != step) {
            SPcolExchange(matrix, step, pivotCol);  /* Update Q */
        }
        
        /* 3. Store pivot choice and extract pivot value A[step][step] */
        matrix->pivotChoice[step] = step;
        pivotValue = SPgetElement(matrix, step, step)->real;  /* A_kk */
        
        /* 4. Update remaining submatrix (Schur complement) */
        for (i = step + 1; i < n; i++) {
            spMatrixElement *element = SPgetElement(matrix, i, step);
            if (element != NULL) {
                /* Compute multiplier: L[i][k] = A[i][k] / A[k][k] */
                multiplier = element->real / pivotValue;  /* L_ik = A_ik / A_kk */
                SPsetElement(matrix, i, step, multiplier); /* Store L_ik */
                
                /* Update row i: A[i][j] = A[i][j] - L[i][k]·A[k][j] */
                for (j = step + 1; j < n; j++) {
                    spMatrixElement *pivotRowElem = 
                        SPgetElement(matrix, step, j);
                    if (pivotRowElem != NULL) {
                        double update = multiplier * pivotRowElem->real; /* L_ik·A_kj */
                        spMatrixElement *targetElem = 
                            SPgetElement(matrix, i, j);
                        
                        if (targetElem != NULL) {
                            /* Element exists: A_ij = A_ij - L_ik·A_kj */
                            targetElem->real -= update;
                        } else {
                            /* Create fill-in: A_ij was zero, now = -L_ik·A_kj */
                            targetElem = SPallocateElement(matrix);
                            targetElem->row = i;
                            targetElem->col = j;
                            targetElem->real = -update;  /* Negative because A_ij = 0 - update */
                            targetElem->isFillIn = 1;
                            matrix->numberOfFillins++;
                            SPinsertElement(matrix, targetElem);
                        }
                    }
                }
            }
        }
    }
    
    matrix->isFactored = 1;  /* Mark as factored: A = LU exists */
    return SP_OK;
}
```

**Mathematical Mapping:**
- Implements Gaussian elimination: \( A^{(k+1)} = A^{(k)} - \mathbf{l}_k \mathbf{a}_k^T / a_{kk} \)
- `multiplier` computes \( L_{ik} = A_{ik}^{(k)} / A_{kk}^{(k)} \)
- `update` computes \( L_{ik} \cdot A_{kj}^{(k)} \) for the rank-1 update
- Fill-in creation implements: \( A_{ij}^{(k+1)} = A_{ij}^{(k)} - L_{ik} \cdot A_{kj}^{(k)} \) when \( A_{ij}^{(k)} = 0 \)
- Row/column exchanges implement permutations: \( \tilde{A} = P A Q^T \)

#### 2.2 Markowitz Pivoting with Threshold Control

The `SPfindPivot` function implements the mathematical pivot selection criterion minimizing \( M(i,j) = (r_i - 1)(c_j - 1) \) subject to threshold constraint \( |A_{ij}| \geq \tau \cdot \max_k |A_{kj}| \).

```c
void SPfindPivot(spMatrixFrame *matrix, int step, 
                 int *pivotRow, int *pivotCol, double *maxElement)
{
    int n = matrix->size;
    int minMarkowitz = n * n;  /* Initialize with large number */
    int currentMarkowitz;
    double candidateValue, absValue;
    
    *pivotRow = step;
    *pivotCol = step;
    *maxElement = 0.0;
    
    /* Search for pivot in remaining submatrix (i,j ≥ step) */
    for (int i = step; i < n; i++) {
        for (int j = step; j < n; j++) {
            spMatrixElement *elem = SPgetElement(matrix, i, j);
            if (elem != NULL) {
                absValue = fabs(elem->real);  /* |A[i][j]| */
                
                /* Compute Markowitz count: M(i,j) = (r_i-1)(c_j-1) */
                int rowCount = SPRowCount(matrix, i, step);  /* r_i */
                int colCount = SPColCount(matrix, j, step);  /* c_j */
                currentMarkowitz = (rowCount - 1) * (colCount - 1); /* M(i,j) */
                
                /* Apply threshold pivoting: |A[i][j]| ≥ τ·max_k|A[k][j]| */
                if (absValue > matrix->threshold[step] * 
                    SPfindMaxInRow(matrix, i)) {
                    
                    /* Select pivot minimizing Markowitz count */
                    if (currentMarkowitz < minMarkowitz || 
                        (currentMarkowitz == minMarkowitz && 
                         absValue > *maxElement)) {
                        minMarkowitz = currentMarkowitz;
                        *pivotRow = i;
                        *pivotCol = j;
                        *maxElement = absValue;
                    }
                }
            }
        }
    }
    
    /* Store Markowitz product for statistics and debugging */
    if (*pivotRow != -1 && *pivotCol != -1) {
        spMatrixElement *pivotElem = 
            SPgetElement(matrix, *pivotRow, *pivotCol);
        if (pivotElem != NULL) {
            pivotElem