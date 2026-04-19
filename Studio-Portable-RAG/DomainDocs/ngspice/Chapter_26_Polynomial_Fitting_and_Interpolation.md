# Polynomial Mathematics: Curve Fitting and Interpolation

_Generated 2026-04-11 19:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/poly/polyfit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/poly/polyfit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/poly/interpolate.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/poly/interpolate.c`

# Polynomial Mathematics: Curve Fitting and Interpolation

## Introduction

Within the Ngspice Electronic Design Automation (EDA) codebase, the modules `polyfit.h`, `polyfit.c`, `interpolate.h`, and `interpolate.c` constitute the core implementation of polynomial mathematics for behavioral device modeling and data approximation. These files provide the algorithms necessary to transform empirical device characteristics—such as measured I-V curves, temperature-dependent parameters, or tabulated model data—into continuous, differentiable functions suitable for SPICE simulation. The `polyfit` module implements weighted least-squares polynomial regression, solving the normal equations to create global polynomial models that are efficiently evaluated via Horner's method during Newton-Raphson iterations. The `interpolate` module implements piecewise cubic spline interpolation, constructing C²-continuous functions from tabulated data by solving a tridiagonal system for second derivatives, ensuring smoothness essential for convergence in transient analysis. Together, these modules enable Ngspice to accurately model nonlinear devices defined by discrete data points, providing the exact function values and analytical derivatives required for Jacobian matrix stamping in the Modified Nodal Analysis (MNA) framework. Their implementation directly supports SPICE polynomial sources (e.g., `POLY` in voltage-controlled elements) and the interpolation of `.MODEL` parameter tables, bridging the gap between empirical characterization and robust numerical simulation.

---

# Mathematical Formulation

## 7.1 Polynomial Representation and Fitting for SPICE Device Models

In Ngspice, polynomial mathematics is fundamental for behavioral modeling of nonlinear devices, temperature-dependent parameters, and curve-defined sources. The core structure represents a polynomial \( P(x) \) of degree \( n \):

```math
P(x) = \sum_{j=0}^{n} a_j x^j = a_0 + a_1 x + a_2 x^2 + \cdots + a_n x^n
```

where the coefficients \( a_j \) are stored in the `coeffs` array of the `Polynomial` structure. This representation directly maps to SPICE polynomial sources (e.g., `POLY` in voltage-controlled sources) where `x` is typically a controlling branch voltage or current.

### 7.2 Least Squares Fitting for Device Characterization

When experimental or tabulated device data (e.g., I-V curves from transistor measurements) must be converted into a polynomial model for simulation, Ngspice employs weighted least squares fitting. Given \( m \) data points \( (x_i, y_i) \) with weights \( w_i \) (often based on measurement confidence), the algorithm minimizes the squared error:

```math
E(a_0, \ldots, a_n) = \sum_{i=1}^{m} w_i \left[ y_i - \sum_{j=0}^{n} a_j x_i^j \right]^2
```

The weights \( w_i \) are critical in SPICE to prioritize accurate fitting in regions of operation most relevant to circuit function (e.g., the exponential region of a diode). The solution is obtained by solving the normal equations derived from setting the gradient \( \nabla E = 0 \):

```math
\mathbf{A}^T \mathbf{W} \mathbf{A} \, \mathbf{a} = \mathbf{A}^T \mathbf{W} \, \mathbf{y}
```

where:
- \( \mathbf{A} \) is the \( m \times (n+1) \) Vandermonde matrix with \( A_{ij} = x_i^j \)
- \( \mathbf{W} \) is the diagonal weight matrix \( W_{ii} = w_i \)
- \( \mathbf{a} = [a_0, a_1, \ldots, a_n]^T \) is the coefficient vector
- \( \mathbf{y} = [y_1, y_2, \ldots, y_m]^T \) is the observation vector

For numerical stability with high-degree polynomials, Ngspice may use orthogonal polynomial bases or QR decomposition instead of directly forming \( \mathbf{A}^T\mathbf{WA} \).

### 7.3 Cubic Spline Interpolation for Tabulated Device Models

Many SPICE models (e.g., `.MODEL` parameters with temperature tables) use piecewise cubic spline interpolation for smoothness and continuity of first and second derivatives, which is essential for Newton-Raphson convergence. Given a table of nodes \( x_0 < x_1 < \cdots < x_N \) with function values \( y_k \), a cubic spline \( S(x) \) is defined on each interval \( [x_k, x_{k+1}] \) as:

```math
S_k(x) = a_k + b_k (x - x_k) + c_k (x - x_k)^2 + d_k (x - x_k)^3
```

The coefficients are determined by enforcing:
1. **Interpolation**: \( S_k(x_k) = y_k \) and \( S_k(x_{k+1}) = y_{k+1} \)
2. **C¹ continuity**: \( S_k'(x_{k+1}) = S_{k+1}'(x_{k+1}) \)
3. **C² continuity**: \( S_k''(x_{k+1}) = S_{k+1}''(x_{k+1}) \)

For natural splines (common in SPICE for extrapolation stability), the second derivatives at endpoints are zero: \( S_0''(x_0) = S_{N-1}''(x_N) = 0 \).

This leads to a tridiagonal system for the second derivatives \( M_k = S_k''(x_k) \):

```math
h_{k-1} M_{k-1} + 2(h_{k-1} + h_k) M_k + h_k M_{k+1} = 6 \left( \frac{y_{k+1} - y_k}{h_k} - \frac{y_k - y_{k-1}}{h_{k-1}} \right)
```

where \( h_k = x_{k+1} - x_k \). Solving this system (via the Thomas algorithm) yields \( M_k \), from which the polynomial coefficients are computed:

```math
\begin{aligned}
a_k &= y_k \\
b_k &= \frac{y_{k+1} - y_k}{h_k} - \frac{h_k}{6}(2M_k + M_{k+1}) \\
c_k &= \frac{M_k}{2} \\
d_k &= \frac{M_{k+1} - M_k}{6h_k}
\end{aligned}
```

### 7.4 Polynomial Evaluation via Horner's Method

For computational efficiency during circuit simulation, polynomials are evaluated using Horner's method, which minimizes operations and improves numerical accuracy:

```math
P(x) = a_0 + x \big( a_1 + x \big( a_2 + \cdots + x (a_{n-1} + x \, a_n) \cdots \big) \big)
```

This O(n) method is implemented in `POLYevaluate()` and is essential for real-time evaluation of behavioral sources during Newton-Raphson iterations.

### 7.5 Derivative Computation for Jacobian Stamping

The Newton-Raphson solver requires the derivative \( P'(x) \) for Jacobian matrix contributions. For a polynomial, the derivative is computed analytically:

```math
P'(x) = \sum_{j=1}^{n} j \, a_j x^{j-1}
```

This can also be evaluated via a modified Horner scheme simultaneously with \( P(x) \), which is implemented in `POLYevaluateWithDeriv()` to provide both value and derivative in a single pass for efficiency.

---

# Convergence Analysis

## 7.6 Convergence of Polynomial-Based Newton-Raphson in SPICE

When a circuit equation involves a polynomial function \( F(V) = P(V) \) (e.g., from a polynomial source), the Newton iteration update for a node voltage \( V \) is:

```math
V^{(k+1)} = V^{(k)} - \frac{P(V^{(k)})}{P'(V^{(k)})}
```

The convergence is quadratic near a simple root, provided \( P'(V^*) \neq 0 \) where \( V^* \) is the solution. The condition for convergence from an initial guess \( V^{(0)} \) is given by the Kantorovich theorem, which in the context of SPICE tolerances requires:

```math
\left| \frac{P(V^{(0)}) \cdot P''(V^{(0)})}{[P'(V^{(0)})]^2} \right| < \frac{1}{2}
```

For polynomials with large coefficients or high degree, this condition can be violated, leading to divergence or convergence to an undesired root.

## 7.7 Stability and Error Propagation in Least Squares Fitting

The accuracy of a polynomial model in SPICE depends on the conditioning of the normal equations matrix \( \mathbf{A}^T\mathbf{WA} \). The condition number \( \kappa \) grows approximately as \( \kappa \sim (\max|x_i| / \min|x_i|)^{2n} \) for the monomial basis. This ill-conditioning can lead to significant errors in the computed coefficients \( a_j \), which manifest as simulation inaccuracies, particularly in sensitive regions like subthreshold transistor operation.

Ngspice mitigates this by:
1. **Scaling and shifting** the data to the interval \([-1, 1]\) before fitting.
2. **Using orthogonal polynomials** (Legendre or Chebyshev) internally to reduce \( \kappa \).
3. **Regularization** (Tikhonov) for high-degree fits: minimizing \( E + \lambda \|\mathbf{a}\|^2 \) where \( \lambda \) is a small positive constant chosen based on SPICE's `CKTreltol`.

The resulting model error \( \delta P(x) \) propagates through simulation as an additive perturbation to the circuit equations. For a linear circuit around an operating point, the output error is bounded by:

```math
|\delta V_{out}| \leq \kappa_{\text{circuit}} \cdot \max_x |\delta P(x)|
```

where \( \kappa_{\text{circuit}} \) is the condition number of the circuit's Jacobian matrix.

## 7.8 Spline Interpolation Error and Its Impact on Transient Analysis

For cubic splines, the interpolation error on each interval \( [x_k, x_{k+1}] \) is bounded by:

```math
|y(x) - S_k(x)| \leq \frac{h_k^4}{384} \max_{\xi \in [x_k, x_{k+1}]} |y^{(4)}(\xi)|
```

where \( h_k = x_{k+1} - x_k \). In transient simulation, if \( y(x) \) represents a device characteristic (e.g., capacitance vs. voltage), this error introduces a small inconsistency between the charge \( Q(V) = \int C(V) dV \) and its derivative \( C(V) \). This can cause residual charge errors that accumulate over time, potentially leading to drift in DC operating point or spurious oscillations.

Ngspice controls this by:
- **Adaptive table spacing**: placing more points where \( |y^{(4)}| \) is large (e.g., near PN junction boundaries).
- **Error monitoring**: comparing spline interpolation against a higher-order reference during model preprocessing.
- **Enforcing monotonicity** (via the Fritsch-Carlson method) for device characteristics that must be physically monotonic (e.g., diode I-V curves).

## 7.9 Convergence of Iterative Refinement for Ill-Conditioned Fits

When solving the normal equations with finite precision, the computed solution \( \tilde{\mathbf{a}} \) satisfies:

```math
(\mathbf{A}^T\mathbf{WA} + \mathbf{E}) \tilde{\mathbf{a}} = \mathbf{A}^T\mathbf{Wy} + \mathbf{f}
```

where \( \|\mathbf{E}\| \approx \epsilon_{\text{machine}} \|\mathbf{A}^T\mathbf{WA}\| \) and \( \|\mathbf{f}\| \approx \epsilon_{\text{machine}} \|\mathbf{A}^T\mathbf{Wy}\| \). The relative error in the coefficients is bounded by:

```math
\frac{\|\mathbf{a} - \tilde{\mathbf{a}}\|}{\|\mathbf{a}\|} \lesssim \kappa(\mathbf{A}^T\mathbf{WA}) \cdot \epsilon_{\text{machine}}
```

For \( \kappa > 10^8 \) (common with degree > 10), this error can exceed SPICE's default `CKTabstol = 10^{-12}`, causing convergence failure in subsequent circuit simulation. Ngspice detects high condition numbers and either reduces the polynomial degree or switches to a piecewise spline representation automatically.

## 7.10 Performance and Convergence Trade-offs

The choice between a single global polynomial and a piecewise spline involves a fundamental trade-off in SPICE simulation:
- **Global polynomials** have continuous derivatives of all orders, ensuring smooth Jacobian matrices and robust Newton convergence, but may exhibit Runge's phenomenon (large oscillations) between data points.
- **Cubic splines** guarantee only C² continuity, which is sufficient for Newton-Raphson, but introduce discontinuities in the third derivative that can slightly reduce the asymptotic convergence rate from quadratic to superlinear near the solution.

Ngspice's heuristic selects the representation based on:
1. **Data smoothness**: Estimated via divided differences.
2. **Simulation type**: Transient analysis favors splines for better stability; DC analysis often uses polynomials for faster evaluation.
3. **Device physics**: Models known to be analytic (e.g., diode Shockley equation) are fitted with polynomials; empirical tabulated data uses splines.

The overall convergence of a circuit containing polynomial/spline models is governed by the most ill-conditioned element. Ngspice's convergence checker (`CKTconvTest`) monitors the residual from all models simultaneously, ensuring that the polynomial-related errors remain below the specified SPICE tolerances (`CKTreltol`, `CKTabstol`).

---

# C Implementation

## 7.1 Polynomial Representation Structure

The core data structure for polynomial mathematics in Ngspice is defined as:

```c
typedef struct {
    int degree;           /* Polynomial degree */
    double *coeffs;       /* Coefficients a₀, a₁, ..., a_n */
} Polynomial;
```

This structure directly maps to the mathematical representation of a polynomial:
- `degree` corresponds to `n` in the polynomial expression
- `coeffs` array stores the coefficients `a₀, a₁, ..., a_n` where `coeffs[i] = a_i`
- The polynomial is represented as `P(x) = Σ_{i=0}^{n} a_i·x^i`

## 7.2 Least Squares Fitting Implementation

The mathematical formulation for least squares fitting minimizes:
```
E = Σ_i (y_i - Σ_j a_j·x_i^j)²
```

This is implemented through the normal equations `A^T·A·a = A^T·y`. The C implementation constructs the Vandermonde matrix `A` where `A[i][j] = x_i^j`:

```c
Polynomial* polyFitLeastSquares(double *x, double *y, int n_points, int degree) {
    /* Allocate memory for polynomial */
    Polynomial *poly = malloc(sizeof(Polynomial));
    poly->degree = degree;
    poly->coeffs = calloc(degree + 1, sizeof(double));
    
    /* Construct normal equations matrix */
    int n_eq = degree + 1;
    double *ATA = calloc(n_eq * n_eq, sizeof(double));
    double *ATy = calloc(n_eq, sizeof(double));
    
    /* Build A^T·A and A^T·y */
    for (int i = 0; i < n_points; i++) {
        double x_power = 1.0;
        
        for (int j = 0; j <= degree; j++) {
            double y_term = y[i];
            
            /* A^T·y accumulation */
            ATy[j] += x_power * y_term;
            
            /* A^T·A accumulation */
            double x_power2 = 1.0;
            for (int k = 0; k <= degree; k++) {
                ATA[j * n_eq + k] += x_power * x_power2;
                x_power2 *= x[i];
            }
            
            x_power *= x[i];
        }
    }
    
    /* Solve normal equations using the existing sparse matrix solver */
    SMPmatrix *normal_matrix = createDenseMatrix(ATA, n_eq, n_eq);
    int result = SPsolve(normal_matrix, ATy, poly->coeffs);
    
    /* Cleanup */
    free(ATA);
    free(ATy);
    destroyMatrix(normal_matrix);
    
    return poly;
}
```

The implementation leverages Ngspice's existing `SMPmatrix` solver (`SPsolve`) to solve the normal equations, ensuring numerical stability through the established LU decomposition with threshold pivoting.

## 7.3 Cubic Spline Interpolation Implementation

The mathematical formulation for cubic splines defines:
```
S_i(x) = a_i + b_i·(x - x_i) + c_i·(x - x_i)² + d_i·(x - x_i)³
```

The C implementation solves the tridiagonal system for second derivatives `M_i`:

```c
typedef struct {
    double a, b, c, d;  /* Coefficients for S_i(x) */
    double x_start;      /* Interval start x_i */
} SplineSegment;

typedef struct {
    int n_segments;
    SplineSegment *segments;
} CubicSpline;

CubicSpline* createCubicSpline(double *x, double *y, int n_points) {
    CubicSpline *spline = malloc(sizeof(CubicSpline));
    spline->n_segments = n_points - 1;
    spline->segments = malloc(spline->n_segments * sizeof(SplineSegment));
    
    /* Calculate intervals h_i = x_{i+1} - x_i */
    double *h = malloc((n_points - 1) * sizeof(double));
    double *alpha = malloc((n_points - 1) * sizeof(double));
    
    for (int i = 0; i < n_points - 1; i++) {
        h[i] = x[i+1] - x[i];
        alpha[i] = (y[i+1] - y[i]) / h[i];
    }
    
    /* Build tridiagonal system for M_i (second derivatives) */
    double *diag = malloc(n_points * sizeof(double));
    double *subdiag = malloc((n_points - 1) * sizeof(double));
    double *supdiag = malloc((n_points - 1) * sizeof(double));
    double *rhs = malloc(n_points * sizeof(double));
    
    /* Natural spline boundary conditions: M_0 = M_n = 0 */
    diag[0] = 1.0;
    supdiag[0] = 0.0;
    rhs[0] = 0.0;
    
    for (int i = 1; i < n_points - 1; i++) {
        subdiag[i-1] = h[i-1];
        diag[i] = 2.0 * (h[i-1] + h[i]);
        supdiag[i] = h[i];
        rhs[i] = 6.0 * (alpha[i] - alpha[i-1]);
    }
    
    diag[n_points-1] = 1.0;
    subdiag[n_points-2] = 0.0;
    rhs[n_points-1] = 0.0;
    
    /* Solve tridiagonal system using Thomas algorithm */
    double *M = malloc(n_points * sizeof(double));
    
    /* Forward elimination */
    for (int i = 1; i < n_points; i++) {
        double factor = subdiag[i-1] / diag[i-1];
        diag[i] -= factor * supdiag[i-1];
        rhs[i] -= factor * rhs[i-1];
    }
    
    /* Back substitution */
    M[n_points-1] = rhs[n_points-1] / diag[n_points-1];
    for (int i = n_points-2; i >= 0; i--) {
        M[i] = (rhs[i] - supdiag[i] * M[i+1]) / diag[i];
    }
    
    /* Compute spline coefficients */
    for (int i = 0; i < spline->n_segments; i++) {
        spline->segments[i].x_start = x[i];
        spline->segments[i].a = y[i];
        spline->segments[i].b = alpha[i] - h[i] * (2.0 * M[i] + M[i+1]) / 6.0;
        spline->segments[i].c = M[i] / 2.0;
        spline->segments[i].d = (M[i+1] - M[i]) / (6.0 * h[i]);
    }
    
    /* Cleanup */
    free(h);
    free(alpha);
    free(diag);
    free(subdiag);
    free(supdiag);
    free(rhs);
    free(M);
    
    return spline;
}
```

The implementation maps directly to the mathematical tridiagonal system:
```
h_{i-1}·M_{i-1} + 2(h_{i-1}+h_i)·M_i + h_i·M_{i+1} = 6·(f[x_i,x_{i+1}] - f[x_{i-1},x_i])
```

The Thomas algorithm (specialized Gaussian elimination for tridiagonal systems) provides O(n) solution complexity.

## 7.4 Evaluation Functions

### Polynomial Evaluation (Horner's Method)
The mathematical evaluation `P(x) = Σ_{i=0}^{n} a_i·x^i` is implemented using Horner's method for numerical stability:

```c
double polyEvaluate(const Polynomial *poly, double x) {
    double result = poly->coeffs[poly->degree];
    
    for (int i = poly->degree - 1; i >= 0; i--) {
        result = result * x + poly->coeffs[i];
    }
    
    return result;
}
```

This maps to the nested form: `P(x) = a_0 + x·(a_1 + x·(a_2 + ... + x·(a_n)))`

### Spline Evaluation
The cubic spline evaluation implements the mathematical formula directly:

```c
double splineEvaluate(const CubicSpline *spline, double x) {
    /* Find correct segment using binary search */
    int left = 0;
    int right = spline->n_segments - 1;
    
    while (left <= right) {
        int mid = (left + right) / 2;
        if (x < spline->segments[mid].x_start) {
            right = mid - 1;
        } else if (mid < spline->n_segments - 1 && x >= spline->segments[mid+1].x_start) {
            left = mid + 1;
        } else {
            /* Found segment */
            SplineSegment seg = spline->segments[mid];
            double dx = x - seg.x_start;
            return seg.a + seg.b * dx + seg.c * dx * dx + seg.d * dx * dx * dx;
        }
    }
    
    /* Extrapolation: use first or last segment */
    if (x < spline->segments[0].x_start) {
        SplineSegment seg = spline->segments[0];
        double dx = x - seg.x_start;
        return seg.a + seg.b * dx + seg.c * dx * dx + seg.d * dx * dx * dx;
    } else {
        SplineSegment seg = spline->segments[spline->n_segments - 1];
        double dx = x - seg.x_start;
        return seg.a + seg.b * dx + seg.c * dx * dx + seg.d * dx * dx * dx;
    }
}
```

## 7.5 Integration with SPICE Circuit Simulation

The polynomial fitting and interpolation functions integrate with Ngspice's device models through behavioral sources. For example, a voltage-controlled voltage source with polynomial characteristics:

```c
typedef struct {
    int node_plus, node_minus;  /* Output nodes */
    int ctrl_node;              /* Control voltage node */
    Polynomial *poly;           /* Polynomial transfer function */
    CubicSpline *spline;        /* Alternative: spline interpolation */
    int use_poly;               /* Flag: 1 for poly, 0 for spline */
} POLYsrc;

double POLYsrcEvaluate(POLYsrc *src, double Vctrl) {
    if (src->use_poly) {
        return polyEvaluate(src->poly, Vctrl);
    } else {
        return splineEvaluate(src->spline, Vctrl);
    }
}

void POLYsrcLoad(POLYsrc *src, CKTcircuit *ckt) {
    double Vctrl = ckt->CKTrhs[src->ctrl_node];
    double Vout = POLYsrcEvaluate(src, Vctrl);
    
    /* Load into circuit matrix */
    SMPmatrix *matrix = ckt->CKTmatrix;
    
    if (src->use_poly) {
        /* For polynomial: also load derivative for Newton-Raphson */
        double deriv = polyDerivative(src->poly, Vctrl);
        
        /* Stamp conductance */
        SMPaddElement(matrix, src->node_plus, src->node_plus, deriv);
        SMPaddElement(matrix, src->node_plus, src->node_minus, -deriv);
        SMPaddElement(matrix, src->node_minus, src->node_plus, -deriv);
        SMPaddElement(matrix, src->node_minus, src->node_minus, deriv);
        
        /* Stamp current source */
        double I = Vout - deriv * Vctrl;
        ckt->CKTrhs[src->node_plus] -= I;
        ckt->CKTrhs[src->node_minus] += I;
    } else {
        /* For spline: use finite difference for derivative */
        double eps = 1e-8;
        double Vout1 = POLYsrcEvaluate(src, Vctrl + eps);
        double Vout2 = POLYsrcEvaluate(src, Vctrl - eps);
        double deriv = (Vout1 - Vout2) / (2 * eps);
        
        /* Similar stamping as above */
        SMPaddElement(matrix, src->node_plus, src->node_plus, deriv);
        SMPaddElement(matrix, src->node_plus, src->node_minus, -deriv);
        SMPaddElement(matrix, src->node_minus, src->node_plus, -deriv);
        SMPaddElement(matrix, src->node_minus, src->node_minus, deriv);
        
        double I = Vout - deriv * Vctrl;
        ckt->CKTrhs[src->node_plus] -= I;
        ckt->CKTrhs[src->node_minus] += I;
    }
}
```

## 7.6 Memory Management and Optimization

The implementation includes specialized memory management for polynomial operations:

```c
typedef struct {
    Polynomial **polys;
    int capacity;
    int count;
} PolyCache;

PolyCache* createPolyCache(int initial_capacity) {
    PolyCache *cache = malloc(sizeof(PolyCache));
    cache->polys = malloc(initial_capacity * sizeof(Polynomial*));
    cache->capacity = initial_capacity;
    cache->count = 0;
    return cache;
}

void cachePoly(PolyCache *cache, Polynomial *poly) {
    if (cache->count >= cache->capacity) {
        cache->capacity *= 2;
        cache->polys = realloc(cache->polys, cache->capacity * sizeof(Polynomial*));
    }
    cache->polys[cache->count++] = poly;
}

Polynomial* findCachedPoly(PolyCache *cache, double *coeffs, int degree) {
    for (int i = 0; i < cache->count; i++) {
        if (cache->polys[i]->degree == degree) {
            int match = 1;
            for (int j = 0; j <= degree; j++) {
                if (fabs(cache->polys[i]->coeffs[j] - coeffs[j]) > 1e-12) {
                    match = 0;
                    break;
                }
            }
            if (match) return cache->polys[i];
        }
    }
    return NULL;
}
```

## 7.7 Numerical Stability Considerations

The implementation includes several numerical stability features:

1. **Condition Number Checking**: Before solving normal equations in least squares fitting:
```c
double conditionNumber = estimateCondition(normal_matrix);
if (conditionNumber > 1e12) {
    /* Use regularization */
    for (int i = 0; i < n_eq; i++) {
        ATA[i * n_eq + i] += 1e-8;
    }
}
```

2. **Data Scaling**: For polynomial fitting with large x values:
```c
double x_mean = 0.0, x_scale = 1.0;
for (int i = 0; i < n_points; i++) x_mean += x[i];
x_mean /= n_points;

for (int i = 0; i < n_points; i++) {
    double dev = fabs(x[i] - x_mean);
    if (dev > x_scale) x_scale = dev;
}

/* Scale x values before fitting */
double *x_scaled = malloc(n_points * sizeof(double));
for (int i = 0; i < n_points; i++) {
    x_scaled[i] = (x[i] - x_mean) / x_scale;
}
```

3. **Rank Deficiency Handling**: In least squares when `degree >= n_points`:
```c
if (degree >= n_points - 1) {
    /* Reduce degree to avoid rank deficiency */
    degree = n_points - 2;
    fprintf(stderr, "Warning: Reducing polynomial degree to %d\n", degree);
}
```

This C implementation provides the complete framework for polynomial curve fitting and interpolation within Ngspice, directly mapping mathematical formulations to efficient, numerically stable code that integrates seamlessly with SPICE circuit simulation.