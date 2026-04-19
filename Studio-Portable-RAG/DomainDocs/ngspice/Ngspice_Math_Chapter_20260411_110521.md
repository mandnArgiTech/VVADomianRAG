# Ngspice algorithm reference

_Generated 2026-04-11 11:05 UTC — `crewai/ngspice_book_factory.py`_

**Source file:** `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/ni/niniter.c`

# Chapter 4: Newton-Raphson Iteration in Circuit Simulation

## 4.1 Introduction to Nonlinear Circuit Solution

Circuit simulation fundamentally requires solving systems of nonlinear algebraic equations derived from Kirchhoff's Current Law (KCL). For a circuit with `n` nodes (excluding ground), we express KCL at each node as:

```
F₁(v₁, v₂, ..., vₙ) = 0
F₂(v₁, v₂, ..., vₙ) = 0
⋮
Fₙ(v₁, v₂, ..., vₙ) = 0
```

where `v = [v₁, v₂, ..., vₙ]ᵀ` is the vector of node voltages and `F: ℝⁿ → ℝⁿ` represents the net current flowing into each node. Each `Fᵢ` is typically a sum of device currents that are nonlinear functions of terminal voltages (diodes, transistors, etc.).

The Newton-Raphson method provides an iterative numerical technique to find the solution `v*` such that `F(v*) = 0`. This chapter details the mathematical formulation, convergence criteria, and implementation within ngspice's `niniter.c` module.

## 4.2 Mathematical Formulation

### 4.2.1 Taylor Series Expansion

Given an initial guess `v⁽⁰⁾`, we expand `F(v)` in a first-order Taylor series around the current iterate `v⁽ᵏ⁾`:

```
F(v⁽ᵏ⁾ + Δv⁽ᵏ⁾) ≈ F(v⁽ᵏ⁾) + J(v⁽ᵏ⁾)·Δv⁽ᵏ⁾
```

where `J(v) = ∂F/∂v` is the Jacobian matrix of partial derivatives. Setting `F(v⁽ᵏ⁾ + Δv⁽ᵏ⁾) = 0` yields the linear system:

```
J(v⁽ᵏ⁾)·Δv⁽ᵏ⁾ = -F(v⁽ᵏ⁾)          (4.1)
```

### 4.2.2 Iterative Update Rule

Solving Equation 4.1 for the correction vector `Δv⁽ᵏ⁾` gives the Newton-Raphson update:

```
v⁽ᵏ⁺¹⁾ = v⁽ᵏ⁾ + Δv⁽ᵏ⁾           (4.2)
```

where:
- `k = 0, 1, 2, ...` is the iteration index
- `J(v⁽ᵏ⁾) ∈ ℝⁿˣⁿ` is the Jacobian evaluated at `v⁽ᵏ⁾`
- `Δv⁽ᵏ⁾ ∈ ℝⁿ` is the solution to the linear system
- `F(v⁽ᵏ⁾) ∈ ℝⁿ` is the residual vector (KCL violations)

### 4.2.3 Jacobian Matrix Structure

In circuit terms, the Jacobian represents the *conductance matrix*:

```
J[i][j] = ∂Fᵢ/∂vⱼ = ∂(∑ I_into_node_i)/∂vⱼ
```

For linear resistors, `∂I/∂V = 1/R`. For nonlinear devices, these derivatives depend on the operating point. The Jacobian is typically sparse in large circuits, as each node connects only to its neighbors.

## 4.3 Convergence Analysis

### 4.3.1 Convergence Criteria

The iteration terminates successfully when all of the following conditions are satisfied:

**Absolute Residual Tolerance:**
```
‖F(v⁽ᵏ⁾)‖∞ < ε_abs           (4.3)
```
where `‖·‖∞` is the maximum norm (∞-norm), and `ε_abs` is typically on the order of `1e-12` to `1e-9` A.

**Relative Voltage Change Tolerance:**
```
‖Δv⁽ᵏ⁾‖∞ < ε_rel·max(‖v⁽ᵏ⁾‖∞, V_scale)   (4.4)
```
where `ε_rel ≈ 1e-3` to `1e-6`, and `V_scale` prevents false convergence near zero volts.

**Absolute Voltage Change Tolerance:**
```
‖Δv⁽ᵏ⁾‖∞ < ε_volt            (4.5)
```
where `ε_volt` is typically `1 μV` to `10 μV`.

### 4.3.2 Failure Detection

**Divergence Detection:**
```
‖Δv⁽ᵏ⁾‖∞ > D·max(‖v⁽ᵏ⁾‖∞, V_scale)   (4.6)
```
where `D ≈ 10³` to `10⁴`. This catches rapidly growing solutions.

**Oscillation Detection:**
Monitor sign patterns of `Δv` components over recent iterations. Persistent sign flipping indicates limit cycling.

**Maximum Iteration Limit:**
```
k ≥ k_max                     (4.7)
```
where `k_max` is typically 100-200 iterations for DC analysis.

### 4.3.3 Convergence Order

Near a simple root, Newton-Raphson exhibits quadratic convergence:
```
‖v⁽ᵏ⁺¹⁾ - v*‖ ≤ C·‖v⁽ᵏ⁾ - v*‖²
```
provided `J(v*)` is nonsingular and the initial guess is sufficiently close.

## 4.4 Implementation Data Structures

### 4.4.1 Core Newton Iteration Structure

```c
/* Simplified representation of Newton iteration context */
typedef struct {
    int size;              /* Matrix dimension n */
    double **J;           /* Jacobian matrix [size][size] */
    double *F;            /* RHS vector (negative residuals) */
    double *v;            /* Voltage vector (solution) */
    double *delta_v;      /* Correction vector */
    int *pivot;           /* LU factorization pivots */
    int iteration;        /* Current iteration count */
    double abs_tol;       /* Absolute current tolerance */
    double rel_tol;       /* Relative voltage tolerance */
    double volt_tol;      /* Absolute voltage tolerance */
    int max_iterations;   /* Maximum allowed iterations */
    double divergence_factor; /* Divergence detection factor */
} NewtonIteration;
```

### 4.4.2 Pointer Relationships and Memory Layout

```
J → [row0] → [J[0][0] J[0][1] ... J[0][n-1]]
    [row1] → [J[1][0] J[1][1] ... J[1][n-1]]
    ...
    [row_n-1] → [J[n-1][0] ... J[n-1][n-1]]

F → [F[0] F[1] ... F[n-1]]          /* Length n */
v → [v[0] v[1] ... v[n-1]]          /* Length n */
delta_v → [Δv[0] Δv[1] ... Δv[n-1]] /* Length n */
pivot → [pivot[0] pivot[1] ... pivot[n-1]] /* Length n */
```

## 4.5 Algorithm Implementation

### 4.5.1 Main Iteration Loop

```c
/* Core Newton-Raphson iteration function */
int newton_iterate(NewtonIteration *ni) {
    int converged_flag = 0;
    double norm_F, norm_delta_v, norm_v;
    
    for (ni->iteration = 0; ni->iteration < ni->max_iterations; ni->iteration++) {
        
        /* 1. Evaluate device equations at current voltages */
        evaluate_device_equations(ni->v, ni->F, ni->J);
        
        /* 2. Check absolute convergence (Equation 4.3) */
        norm_F = vector_inf_norm(ni->F, ni->size);
        if (norm_F < ni->abs_tol) {
            converged_flag = 1;
            break;
        }
        
        /* 3. Form right-hand side: -F(v) */
        vector_scale(ni->F, -1.0, ni->size);
        
        /* 4. Solve J·Δv = -F using LU decomposition */
        if (lu_factorize_with_pivoting(ni->J, ni->pivot, ni->size) != 0) {
            return MATRIX_SINGULAR;
        }
        lu_solve(ni->J, ni->pivot, ni->F, ni->delta_v, ni->size);
        
        /* 5. Check for divergence (Equation 4.6) */
        norm_delta_v = vector_inf_norm(ni->delta_v, ni->size);
        norm_v = vector_inf_norm(ni->v, ni->size);
        if (norm_delta_v > ni->divergence_factor * MAX(norm_v, 1.0)) {
            return DIVERGED;
        }
        
        /* 6. Update voltages: v ← v + Δv (Equation 4.2) */
        vector_add(ni->v, ni->delta_v, ni->size);
        
        /* 7. Check relative convergence (Equations 4.4, 4.5) */
        if (norm_delta_v < ni->rel_tol * MAX(norm_v, 1.0) &&
            norm_delta_v < ni->volt_tol) {
            converged_flag = 1;
            break;
        }
        
        /* 8. Optional: oscillation detection */
        if (detect_oscillation(ni->delta_v, ni->size)) {
            return OSCILLATION_DETECTED;
        }
    }
    
    if (converged_flag) {
        return CONVERGED;
    } else {
        return MAX_ITERATIONS_EXCEEDED;
    }
}
```

### 4.5.2 Device Equation Stamping

Each nonlinear device contributes to both the residual vector `F` and the Jacobian matrix `J`. The stamping process follows:

```c
/* Generic device stamping template */
void stamp_device(Device *dev, double *F, double **J, double *v) {
    double I, g;
    
    /* Evaluate device current and conductance at current voltages */
    device_current_and_conductance(dev, v, &I, &g);
    
    /* Get device node indices */
    int node_plus = dev->node_plus;
    int node_minus = dev->node_minus;
    
    /* Stamp into residual vector F (KCL) */
    if (node_plus >= 0) {
        F[node_plus] += I;      /* Current leaving + terminal */
    }
    if (node_minus >= 0) {
        F[node_minus] -= I;     /* Current entering - terminal */
    }
    
    /* Stamp into Jacobian matrix J */
    if (node_plus >= 0 && node_plus < n) {
        if (node_plus >= 0) J[node_plus][node_plus] += g;
        if (node_minus >= 0) J[node_plus][node_minus] -= g;
    }
    if (node_minus >= 0 && node_minus < n) {
        if (node_minus >= 0) J[node_minus][node_minus] += g;
        if (node_plus >= 0) J[node_minus][node_plus] -= g;
    }
}
```

#### Example: Diode Stamping
For a diode with equation `I = Iₛ·[exp(V/Vₜ) - 1]`:
- Conductance: `g = ∂I/∂V = (Iₛ/Vₜ)·exp(V/Vₜ)`
- Current: `I = Iₛ·[exp(V/Vₜ) - 1]`
- Stamps identical to template with these `I` and `g` values

#### Example: MOSFET Stamping (Level 1)
For a MOSFET in saturation (`V_ds > V_gs - V_th`):
```
I_ds = (β/2)·(V_gs - V_th)²·(1 + λ·V_ds)
g_m = ∂I_ds/∂V_gs = β·(V_gs - V_th)·(1 + λ·V_ds)
g_ds = ∂I_ds/∂V_ds = (β/2)·(V_gs - V_th)²·λ
```
These conductances populate the appropriate positions in `J` based on drain, gate, source, and bulk connections.

## 4.6 Convergence Enhancement Techniques

### 4.6.1 Damped Newton (Line Search)

For difficult convergence cases, a damping factor `λ ∈ (0, 1]` is introduced:

```
v⁽ᵏ⁺¹⁾ = v⁽ᵏ⁾ + λ·Δv⁽ᵏ⁾           (4.8)
```

The optimal `λ` minimizes `‖F(v⁽ᵏ⁾ + λ·Δv⁽ᵏ⁾)‖`. A simple backtracking algorithm:

```c
double backtrack_line_search(double *v_old, double *delta_v, 
                             double *F_old, double **J, int n) {
    double lambda = 1.0;
    double *v_new = malloc(n * sizeof(double));
    double *F_new = malloc(n * sizeof(double));
    double norm_old, norm_new;
    
    norm_old = vector_inf_norm(F_old, n);
    
    while (lambda > 1e-4) {  /* Minimum step size */
        /* Trial update */
        for (int i = 0; i < n; i++) {
            v_new[i] = v_old[i] + lambda * delta_v[i];
        }
        
        /* Evaluate residuals at trial point */
        evaluate_device_equations(v_new, F_new, NULL);
        
        norm_new = vector_inf_norm(F_new, n);
        
        /* Check if trial improves solution */
        if (norm_new < norm_old) {
            break;
        }
        
        /* Reduce step size */
        lambda *= 0.5;
    }
    
    free(v_new);
    free(F_new);
    return lambda;
}
```

### 4.6.2 Continuation Methods

For strongly nonlinear problems or poor initial guesses:
1. Solve a simplified problem (e.g., all diodes replaced with resistors)
2. Gradually reintroduce nonlinearities via a homotopy parameter `α ∈ [0, 1]`:
   ```
   H(v, α) = α·F(v) + (1-α)·F₀(v) = 0
   ```
   where `F₀` represents the simplified system.

### 4.6.3 Adaptive Tolerance

Dynamic tolerance adjustment based on iteration progress:
```
if (‖Δv⁽ᵏ⁾‖/‖Δv⁽ᵏ⁻¹⁾‖ > 0.9) {
    /* Slow convergence, tighten tolerance gradually */
    effective_tol = MAX(0.1 * current_tol, min_tol);
}
```

## 4.7 Matrix Solver Integration

### 4.7.1 Sparse Matrix Representation

Large circuits use sparse matrix formats. ngspice typically employs Modified Nodal Analysis (MNA) with sparse storage:

```c
typedef struct {
    int n;                  /* Matrix dimension */
    int nnz;                /* Number of nonzeros */
    double *values;         /* Nonzero values */
    int *col_indices;       /* Column indices */
    int *row_pointers;      /* Row pointer (CSR format) */
} SparseMatrix;
```

### 4.7.2 LU Decomposition with Partial Pivoting

The core linear solver implements:
```c
int lu_factorize_with_pivoting(double **A, int *pivot, int n) {
    for (int i = 0; i < n; i++) {
        pivot[i] = i;
    }
    
    for (int k = 0; k < n-1; k++) {
        /* Find pivot row */
        int p = k;
        double max_val = fabs(A[k][k]);
        for (int i = k+1; i < n; i++) {
            if (fabs(A[i][k]) > max_val) {
                max_val = fabs(A[i][k]);
                p = i;
            }
        }
        
        if (max_val < 1e-15) {
            return -1;  /* Singular matrix */
        }
        
        /* Swap rows if necessary */
        if (p != k) {
            swap_rows(A, k, p, n);
            int temp = pivot[k];
            pivot[k] = pivot[p];
            pivot[p] = temp;
        }
        
        /* Gaussian elimination */
        for (int i = k+1; i < n; i++) {
            A[i][k] /= A[k][k];
            for (int j = k+1; j < n; j++) {
                A[i][j] -= A[i][k] * A[k][j];
            }
        }
    }
    
    return 0;
}
```

### 4.7.3 Forward/Backward Substitution

```c
void lu_solve(double **LU, int *pivot, double *b, double *x, int n) {
    double *y = malloc(n * sizeof(double));
    
    /* Forward substitution: L·y = P·b */
    for (int i = 0; i < n; i++) {
        y[i] = b[pivot[i]];
        for (int j = 0; j < i; j++) {
            y[i] -= LU[i][j] * y[j];
        }
    }
    
    /* Backward substitution: U·x = y */
    for (int i = n-1; i >= 0; i--) {
        x[i] = y[i];
        for (int j = i+1; j < n; j++) {
            x[i] -= LU[i][j] * x[j];
        }
        x[i] /= LU[i][i];
    }
    
    free(y);
}
```

## 4.8 Physical Interpretation

### 4.8.1 Circuit Equivalents

At each iteration, the nonlinear circuit is replaced by a *linearized equivalent circuit*:
- Nonlinear devices → Linearized models (current source + conductance)
- `J(v⁽ᵏ⁾)` → Conductance matrix of linearized circuit
- `-F(v⁽ᵏ⁾)` → Equivalent current sources representing KCL violations

### 4.8.2 Variable Significance

- **`J[i][j