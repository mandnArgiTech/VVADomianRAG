# Periodic Steady State (PSS): Shooting Newton Algorithms

_Generated 2026-04-13 06:24 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/dcpss.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/pssinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/psssetp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/pssaskq.c`

# Chapter: Periodic Steady State (PSS): Shooting Newton Algorithms

## 1. Introduction: Ngspice PSS Analysis Engine

Periodic Steady State (PSS) analysis in Ngspice computes the steady-state response of nonlinear circuits to periodic excitations, a critical capability for analyzing oscillators, mixers, switched-capacitor filters, and power converters. The implementation is architected across four core C source files in the Ngspice codebase (`/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/`):

- **`dcpss.c`**: Primary implementation file containing the shooting Newton algorithm core, including the main Newton-Raphson loop (`PSSshoot`), periodic integration (`PSSintegratePeriod`), and monodromy matrix computation (`PSScomputeMonodromy`).
- **`pssinit.c`**: Initialization routines for PSS analysis, setting up data structures, allocating memory for state vectors, and establishing default parameters.
- **`psssetp.c`**: Parameter configuration interface, handling user-specified options such as period, tolerance settings, maximum iterations, and initial guess strategies.
- **`pssaskq.c`**: Query interface for retrieving analysis results, including steady-state waveforms, Floquet multipliers, and convergence statistics.

These files implement a sophisticated numerical engine that transforms the periodic boundary value problem into a nonlinear root-finding problem via the shooting method, then solves it using Newton-Raphson iteration with adaptive time-stepping and matrix-free Krylov solvers for computational efficiency.

## 2. Mathematical Formulation

### 2.1 Fundamental Periodic Steady-State Problem

In SPICE circuit simulation, the Periodic Steady State (PSS) analysis finds the steady-state response of nonlinear circuits to periodic excitations. The circuit is described by nonlinear Differential-Algebraic Equations (DAEs):

```
F(x(t), ẋ(t), t) = 0, where x(t) ∈ ℝⁿ, F: ℝⁿ × ℝⁿ × ℝ → ℝⁿ
```

with T-periodic excitation: `F(x, ẋ, t) = F(x, ẋ, t + T)` for all t. The **Periodic Steady-State (PSS)** solution satisfies:

```
x(t + T) = x(t) ∀t ∈ [0, ∞)
```

with the **boundary condition**:

```
x(T) - x(0) = 0
```

This boundary condition enforces that after one period T, the circuit state returns to its initial value, defining a closed orbit in state space.

### 2.2 Shooting Method Formulation

The shooting method transforms the boundary value problem into an initial value problem. Define the **state transition map** Φ: ℝⁿ × ℝ → ℝⁿ:

```
x(T) = Φ(x₀, T)
```

where Φ integrates the DAEs from t=0 to t=T with initial condition x(0)=x₀. The **shooting function** R: ℝⁿ → ℝⁿ is:

```
R(x₀) = Φ(x₀, T) - x₀
```

PSS requires finding x₀* such that R(x₀*) = 0. This is a root-finding problem in ℝⁿ.

### 2.3 Newton-Raphson Iteration for Shooting

The shooting function is solved using Newton-Raphson iteration. At iteration k:

```
J_s(x₀ᵏ) Δx₀ᵏ = -R(x₀ᵏ)
x₀ᵏ⁺¹ = x₀ᵏ + Δx₀ᵏ
```

where the **shooting Jacobian** J_s is:

```
J_s(x₀) = ∂R/∂x₀ = ∂Φ/∂x₀ - I = M(T) - I
```

and M(T) is the **monodromy matrix** (state transition matrix). The monodromy matrix M(T) satisfies the **variational equation**:

```
dM/dt = A(t)M(t), M(0) = I
```

where A(t) = [∂F/∂ẋ]⁻¹[∂F/∂x] evaluated along the trajectory x(t).

### 2.4 Time-Domain Discretization with Periodicity

Using N time steps with step size h = T/N:

```
tₖ = k·h, k = 0,...,N
```

Discrete DAEs using trapezoidal rule (common in SPICE):

```
F(xₖ, (xₖ - xₖ₋₁)/h, tₖ) = 0, k = 1,...,N
```

with periodicity constraint:

```
x_N = x₀
```

### 2.5 Large-Scale Newton System

Collect all variables: X = [x₀ᵀ, x₁ᵀ, ..., x_Nᵀ]ᵀ ∈ ℝⁿ⁽ᴺ⁺¹⁾

The complete nonlinear system G(X) = 0 has block structure:

```
G(X) = [F(x₀, (x₁-x₀)/h, t₁),
        F(x₁, (x₂-x₁)/h, t₂),
        ...
        F(x_N₋₁, (x_N-x_N₋₁)/h, t_N),
        x_N - x₀] = 0
```

The Jacobian ∂G/∂X has special periodic structure:

```
J = ⎡ B₀  C₁                A₀ ⎤
    ⎢ A₁  B₁  C₂                ⎥
    ⎢     ⋱   ⋱   ⋱            ⎥
    ⎢          A_N₋₁  B_N₋₁  C_N ⎥
    ⎣ I                       -I  B_N ⎦
```

where:
- Aₖ = ∂F/∂xₖ₋₁ at time step k
- Bₖ = ∂F/∂xₖ at time step k  
- Cₖ = (1/h)∂F/∂ẋₖ at time step k
- The last block row enforces x_N = x₀

### 2.6 Matrix-Free Implementation via Krylov Methods

For large circuits with many states n, storing J ∈ ℝⁿ⁽ᴺ⁺¹⁾×ⁿ⁽ᴺ⁺¹⁾ is prohibitive. SPICE uses:
- **GMRES** or **BiCGSTAB** requiring only matrix-vector products J·v
- Matrix-vector product computed via **transient sensitivity**:

```
J·v = [∂G/∂X]·v computed by integrating variational equations
```

This avoids explicit storage of the large periodic Jacobian.

## 3. Convergence Analysis

### 3.1 Residual Error Formulation

The **fundamental residual** for convergence checking in SPICE PSS analysis:

```
R_max = max_{i=1..n} |R_i(x₀)| / w_i
```

where weights w_i = ATOL_i + RTOL_i·|x₀_i|, with typical SPICE values:
- ATOL_i = 1e-6 (absolute tolerance)
- RTOL_i = 1e-3 (relative tolerance)

**Convergence criterion**: R_max < 1.0

### 3.2 Error Propagation and Orbital Stability

The **Floquet multipliers** μ_i (eigenvalues of M(T)) determine stability of the periodic orbit:
- |μ_i| < 1: orbit stable, Newton converges quadratically
- |μ_i| ≈ 1: marginal stability, slow convergence
- |μ_i| > 1: unstable orbit, Newton diverges

**Condition number** of shooting Jacobian:

```
κ(J_s) = σ_max(J_s)/σ_min(J_s)
```

Large κ indicates ill-conditioning; occurs when:
1. Circuit has widely separated time constants (stiff system)
2. Orbit is nearly marginal (μ_i ≈ 1)
3. Period T is resonant with natural frequencies
4. Circuit has floating nodes or perfect voltage sources

### 3.3 Step Rejection Criteria

A Newton step is rejected in SPICE if:
1. **Residual increases**: ||R(x₀ᵏ⁺¹)|| > (1 + η)||R(x₀ᵏ)||, η ≈ 0.1
2. **Step too large**: ||Δx₀ᵏ|| > δ_max·||x₀ᵏ||, δ_max ≈ 0.5
3. **Oscillation detected**: sign(Δx₀ᵏ·Δx₀ᵏ⁻¹) < 0 repeatedly

### 3.4 Time-Step Adaptation Algorithm

Based on **local truncation error** (LTE) during integration:

```
LTEₖ = C·hᵖ⁺¹·x⁽ᵖ⁺¹⁾(ξ), ξ ∈ [tₖ₋₁, tₖ]
```

where p = integration order (1 for Backward Euler, 2 for Trapezoidal Rule).

New time step computed as:

```
h_new = h_old·min(ρ_max, max(ρ_min, ρ·(ε/LTE)^(1/(p+1))))
```

where:
- ε = error tolerance (typically 1e-6 in SPICE)
- ρ = safety factor (0.8-0.9)
- ρ_min = 0.1, ρ_max = 5.0 (limits on step size change)

### 3.5 Initial Guess Generation Strategies

SPICE employs several strategies for initial guess x₀⁽⁰⁾:

1. **DC solution**: x₀⁽⁰⁾ = x_DC (simple but often poor for oscillators)
2. **Transient startup**: Integrate for m periods: x₀⁽⁰⁾ = x(mT)
3. **Frequency domain**: Use harmonic balance for initial guess (for quasi-sinusoidal signals)
4. **Continuation**: Start with small amplitude/frequency, increase gradually

### 3.6 Convergence Monitoring

**Quadratic convergence check**:

```
ρₖ = ||R(x₀ᵏ⁺¹)|| / ||R(x₀ᵏ)||²
```

Newton method exhibits quadratic convergence: ρₖ → constant. If ρₖ grows, convergence is failing.

**Residual reduction rate**:

```
αₖ = log(||R(x₀ᵏ⁺¹)||) / log(||R(x₀ᵏ)||)
```

Linear convergence: αₖ → 1. Quadratic convergence: αₖ → 2.

### 3.7 Numerical Precision Limits

**Finite difference perturbation** for ∂Φ/∂x₀ when analytical derivatives unavailable:

```
[J_s]_{ij} ≈ [Φ(x₀ + δeⱼ, T) - Φ(x₀, T)]_i / δ
```

Optimal δ = √(ε_mach)·||x₀|| ≈ 1e-8 for double precision, balancing truncation and roundoff errors.

**Round-off error accumulation** over N integration steps:

```
Error in M(T) ≈ N·ε_mach·cond(A(t))
```

For N > 1e6, may need extended precision or compensated summation techniques.

### 3.8 Regularization for Ill-Conditioned Systems

When J_s is nearly singular (common in circuits with floating nodes), SPICE uses Tikhonov regularization:

```
Solve (J_s + λI)Δx₀ = -R(x₀)
```

where λ = max(ε_mach·||J_s||, 1e-8). This stabilizes the Newton iteration at the cost of slightly slower convergence.

### 3.9 Damped Newton for Global Convergence

To ensure global convergence, SPICE may use damped Newton:

```
x₀ᵏ⁺¹ = x₀ᵏ + αΔx₀ᵏ, α ∈ (0,1]
```

with α chosen by line search to ensure ||R(x₀ᵏ⁺¹)|| < ||R(x₀ᵏ)||. Common strategies:
- **Armijo rule**: α = 1, 1/2, 1/4, ... until sufficient decrease
- **Quadratic/cubic interpolation** for optimal α

### 3.10 Computational Complexity Analysis

The shooting Newton algorithm in SPICE has the following complexity per iteration:

1. **Transient integration**: O(N·n³) with direct linear solvers, O(N·n²) with iterative solvers
2. **Monodromy computation**: O(n·N·n²) = O(N·n³) worst case (n sensitivity integrations)
3. **Newton solve**: O(n³) for dense, O(n²) for sparse with good preconditioner

**Memory requirements**:
- State trajectory: O(N·n) doubles
- Monodromy matrix: O(n²) doubles  
- Full periodic Jacobian: O(N·n²) but not stored explicitly in matrix-free implementation

### 3.11 Convergence Acceleration Techniques

SPICE employs several acceleration techniques:

1. **Quasi-Newton methods**: Broyden update for J_s⁻¹, avoiding recomputation of M(T)
2. **Waveform relaxation**: Decouple circuit into subsystems, solve separately
3. **Selective sensitivity**: Only compute important columns of M(T) (for dominant states)
4. **Krylov subspace recycling**: Reuse subspace information between Newton iterations

### 3.12 Period Adaptation for Autonomous Oscillators

For oscillators (free-running, no external clock), the period T is unknown. SPICE solves the augmented system:

```
R(x₀, T) = Φ(x₀, T) - x₀ = 0
Phase condition: ψ(x₀) = 0 (e.g., x₀₁ = 0)
```

This adds one more unknown (T) and one more equation (phase condition). The extended Jacobian has size (n+1)×(n+1).

### 3.13 Harmonic Balance vs. Shooting Method Trade-offs

SPICE may switch between methods based on circuit characteristics:

- **Shooting method**: Better for strongly nonlinear circuits, sharp transitions
- **Harmonic balance**: Better for mildly nonlinear circuits, narrowband signals
- **Hybrid methods**: Use harmonic balance for initial guess, then shooting for refinement

The choice depends on spectral content, nonlinearity strength, and computational resources.

### 3.14 Parallelization Strategies

For large circuits, SPICE can parallelize:

1. **Time parallel**: Different time points on different processors (parareal algorithm)
2. **Parameter parallel**: Multiple shooting parameters simultaneously
3. **Matrix parallel**: Parallel linear algebra operations (BLAS/LAPACK)
4. **Device parallel**: Different circuit partitions on different processors

### 3.15 Stopping Criteria

SPICE uses multiple stopping criteria:

1. **Absolute residual**: ||R(x₀)|| < ε_abs (typically 1e-9)
2. **Relative residual**: ||R(x₀)||/||R(x₀⁽⁰⁾)|| < ε_rel (typically 1e-6)
3. **Step size**: ||Δx₀|| < ε_step·||x₀|| (typically 1e-8)
4. **Maximum iterations**: k > k_max (typically 20-50)
5. **Stagnation detection**: No improvement for 3 consecutive iterations

The analysis terminates when any criterion is satisfied, with priority given to convergence over iteration limits.

## 4. C Implementation Architecture

### 4.1 Core Data Structures

```c
/* Main PSS analysis control structure (inferred from research context) */
typedef struct sPSSan {
    int PSSmode;                /* Analysis mode: AUTO, SHOOTING, HARMONIC */
    double PSSperiod;           /* Period T of excitation */
    double *PSSsolution;        /* Steady-state solution vector x₀* */
    double *PSSinitialGuess;    /* Initial guess x₀⁽⁰⁾ */
    double *PSSresidual;        /* Shooting residual R(x₀) */
    double **PSSmonodromy;      /* Monodromy matrix M(T) */
    int PSSmaxIter;             /* Maximum Newton iterations */
    double PSSconverge;         /* Convergence tolerance */
    double PSSabstol;           /* Absolute tolerance ATOL */
    double PSSreltol;           /* Relative tolerance RTOL */
    int PSSnumTimePoints;       /* Number of time points N */
    double *PSStimeGrid;        /* Time grid t₀...t_N */
    double **PSSstateTrajectory;/* Full state trajectory x(t) */
    int CKTnumStates;           /* Number of state variables n */
} PSSanalysis;

/* Waveform storage for periodic solution */
typedef struct {
    double *PSSwaveTime;        /* Time points over one period */
    double **PSSwaveValue;      /* State values at each time point */
    double **PSSfourCoeffs;     /* Fourier coefficients (if computed) */
    int PSSnumHarmonics;        /* Number of harmonics stored */
} PSSwaveform;

/* Matrix structure for periodic Jacobian (sparse representation) */
typedef struct {
    int PSSjacobianSize;        /* Size of block Jacobian */
    int *PSSjacobianRowPtr;     /* Row pointers (CSR format) */
    int *PSSjacobianColIdx;     /* Column indices */
    double *PSSjacobianValues;  /* Non-zero values */
    int *PSSboundMap;           /* Mapping for boundary condition */
} PSSmatrix;
```

### 4.2 Main Shooting Newton Algorithm (`dcpss.c`)

```c
/* Primary shooting Newton implementation */
int PSSshoot(PSSanalysis *pss, CKTcircuit *ckt) {
    int iter = 0, converged = 0;
    double norm, norm_old, alpha;
    double *delta_x0 = NULL;
    
    /* Allocate memory for Newton step */
    delta_x0 = (double*)malloc(pss->CKTnumStates * sizeof(double));
    if (!delta_x0) return E_NOMEM;
    
    /* Compute initial residual */
    pss->PSSresidual = computeShootingResidual(pss, ckt);
    norm_old = vectorNorm(pss->PSSresidual, pss->CKTnumStates);
    
    while (iter < pss->PSSmaxIter && !converged) {
        /* Compute shooting Jacobian J_s = M(T) - I */
        computeShootingJacobian(pss, ckt);
        
        /* Solve Newton system: J_s * delta_x0 = -R(x₀) */
        if (solveNewtonSystem(pss, delta_x0) != 0) {
            free(delta_x0);
            return E_SINGULAR;
        }
        
        /* Apply damping with line search */
        alpha = 1.0;
        while (alpha > 1e-4) {
            /* Update initial condition: x₀_new = x₀ + alpha * delta_x0 */
            updateInitialCondition(pss, delta_x0, alpha);
            
            /* Compute new residual */
            pss->PSSresidual = computeShootingResidual(pss, ckt);
            norm = vectorNorm(pss->PSSresidual, pss->CKTnumStates);
            
            /* Check for sufficient decrease (Armijo condition) */
            if (norm < (1.0 - 1e-4 * alpha) * norm_old) {
                break;  /* Accept step */
            }
            
            /* Reduce step size */
            alpha *= 0.5;
        }
        
        /* Check convergence criteria */
        if (norm < pss->PSSconverge) {
            converged = 1;
        } else if (fabs(norm - norm_old) < 1e-12 * norm_old) {
            /* Stagnation detected */
            free(delta_x0);
            return E_NOCONVERGE;
        }
        
        norm_old = norm;
        iter++;
    }
    
    free(delta_x0);
    
    if (!converged) {
        return E_NOCONVERGE;
    }
    
    /* Store final solution */
    memcpy(pss->PSSsolution, pss->PSSinitialGuess, 
           pss->CKTnumStates * sizeof(double));
    
    return 0; /* Success */
}
```

### 4.3 Periodic Integration with Adaptive Time-Stepping

```c
/* Integrate over one period with adaptive time-stepping */
int PSSintegratePeriod(PSSanalysis *pss, CKTcircuit *ckt, 
                       double *x0, double **trajectory) {
    double t = 0.0, h = pss->PSSperiod / pss->PSSnumTimePoints;
    double h_min = pss->PSSperiod / 10000.0;
    double h_max = pss->PSSperiod / 10.0;
    double error, scale;
    int step = 0;
    
    /* Initialize state */
    memcpy(trajectory[0], x0, pss->CKTnumStates * sizeof(double));
    
    while (t < pss->PSSperiod && step < pss->PSSnumTimePoints) {
        double *x_current = trajectory[step];
        double *x_next = trajectory[step + 1];
        
        /* Attempt integration step */
        error = integrateStep(pss, ckt, x_current, x_next, h, &scale);
        
        if (error < 1.0) {
            /* Step accepted */
            t += h;
            step++;
            
            /* Adjust time step based on local truncation error */
            h *= MIN(h_max, MAX(h_min, 0.9 * pow(1.0 / error, 1.0/3.0)));
        } else {
            /* Step rejected, reduce time step */
            h *= 0.5;
            if (h < h_min) {
                return E_TIMESTEP; /* Time step too small */
            }
        }
    }
    
    /* Ensure periodicity: x(T) should equal x(0) */
    if (step > 0) {
        double diff = vectorDistance(trajectory[step], x0, pss->CKTnumStates);
        if (diff > pss->PSSabstol) {
            /* Apply boundary condition correction */
            enforcePeriodicity(trajectory[step], x0, pss->CKTnumStates);
        }
    }
    
    return 0;
}
```

### 4.4 Monodromy Matrix Computation via Sensitivity Analysis

```c
/* Compute monodromy matrix M(T) = ∂Φ/∂x₀ */
int PSScomputeMonodromy(PSSanalysis *pss, CKTcircuit *ckt) {
    int i, j;
    double *perturbed, *sensitivity;
    double delta = 1e-8; /* Optimal perturbation for finite differences */
    
    /* Allocate memory for sensitivity vectors */
    perturbed = (double*)malloc(pss->CKTnumStates * sizeof(double));
    sensitivity = (double*)malloc(pss->CKTnumStates * sizeof(double));
    
    if (!perturbed || !sensitivity) {
        free(perturbed);
        free(sensitivity);
        return E_NOMEM;
    }
    
    /* For each state variable, compute column of M(T) */
    for (i = 0; i < pss->CKTnumStates; i++) {
        /* Create perturbed initial condition: x₀ + δ·e_i */
        memcpy(perturbed, pss->PSSinitialGuess, 
               pss->CKTnumStates * sizeof(double));
        perturbed[i] += delta;
        
        /* Integrate perturbed system over one period */
        double **perturbed_traj = allocateTrajectory(pss);
        PSSintegratePeriod(pss, ckt, perturbed, perturbed_traj);
        
        /* Compute sensitivity: (Φ(x₀+δe_i) - Φ(x₀))/δ */
        for (j = 0; j < pss->CKTnumStates; j++) {
            sensitivity[j] = (perturbed_traj[pss->PSSnumTimePoints][j] - 
                            pss->PSSstateTrajectory[pss->PSSnumTimePoints][j]) / delta;
        }
        
        /* Store as column i of monodromy matrix */
        for (j = 0; j < pss->CKTnumStates; j++) {
            pss->PSSmonodromy[j][i] = sensitivity[j];
        }
        
        freeTrajectory(perturbed_traj, pss);
    }
    
    free(perturbed);
    free(sensitivity);
    return 0;
}
```

### 4.5 Matrix-Free Newton System Solver

```c
/* Solve Newton system using matrix-free GMRES */
int PSSsolveNewton(PSSanalysis *pss, double *b, double *x) {
    int n = pss->CKTnumStates;
    int max_iter = MIN(100, n); /* GMRES iteration limit */
    double tol = 1e-6;
    double *r, *v, *w;
    double **H;
    int i, j, k;
    
    /* Allocate Krylov subspace vectors */
    r = (double*)malloc(n * sizeof(double));
    v = (double*)malloc(n * sizeof(double));
    w = (double*)malloc(n * sizeof(double));
    H = (double**)malloc((max_iter + 1) * sizeof(double*));
    for (i = 0; i <= max_iter; i++) {
        H[i] = (double*)malloc((max_iter + 1) * sizeof(double));
    }
    
    /* Initial guess: x = 0 */
    memset(x, 0, n * sizeof(double));
    
    /* Compute initial residual: r = b - J_s * x = b (since x=0) */
    memcpy(r, b, n * sizeof(double));
    
    /* Normalize first basis vector */
    double beta = vectorNorm(r, n);
    if (beta < tol) {
        /* Already converged */
        free(r); free(v); free(w);
        for (i = 0; i <= max_iter; i++) free(H[i]);
        free(H);
        return 0;
    }
    
    /* GMRES iteration */
    for (j = 0; j < max_iter; j++) {
        /* Matrix-vector product: w = J_s * v */
        applyShootingJacobian(pss, v, w);
        
        /* Modified Gram-Schmidt orthogonalization */
        for (i = 0; i <= j; i++) {
            H[i][j] = dotProduct(w, v, n);
            axpy(w, -H[i][j], v, n);
        }
        
        H[j+1][j] = vectorNorm(w, n);
        
        /* Check for breakdown */
        if (H[j+1][j] < 1e-14) {
            break;
        }
        
        /* Normalize next basis vector */
        scaleVector(v, 1.0 / H[j+1][j], n);
    }
    
    /* Solve least squares problem and update solution */
    /* ... (standard GMRES implementation continues) ... */
    
    /* Cleanup */
    free(r); free(v); free(w);
    for (i = 0; i <= max_iter; i++) free(H[i]);
    free(H);
    
    return 0;
}
```

### 4.6 Boundary Condition Enforcement

```c
/* Apply periodic boundary condition to trajectory */
int PSSapplyBoundary(PSSanalysis *pss, double **trajectory) {
    int i;
    double diff;
    
    /* Compute difference: x_N - x_0 */
    for (i = 0; i < pss->CKTnumStates; i++) {
        diff = trajectory[pss->PSSnumTimePoints][i] - trajectory[0][i];
        
        /* Apply correction to enforce x_N = x_0 */
        if (fabs(diff) > pss->PSSabstol) {
            /* Distribute correction across trajectory */
            for (int k = 0; k <= pss->PSSnumTimePoints; k++) {
                double weight = (double)k / pss->PSSnumTimePoints;
                trajectory[k][i] -= weight * diff;
            }
        }
    }
    
    return 0;
}
```

### 4.7 Initial Guess Generation (`pssinit.c`)

```c
/* Generate initial guess for shooting method */
int PSSgenerateInitialGuess(PSSanalysis *pss, CKTcircuit *ckt, int strategy) {
    switch (strategy) {
        case PSS_GUESS_DC:
            /* Use DC solution as initial guess */
            memcpy(pss->PSSinitialGuess, ckt->CKTrhsOld, 
                   pss->CKTnumStates * sizeof(double));
            break;
            
        case PSS_GUESS_TRANSIENT:
            /* Run transient simulation for a few periods */
            runTransientStartup(pss, ckt, 3); /* 3 periods */
            extractFinalState(pss, ckt, pss->PSSinitialGuess);
            break;
            
        case PSS_GUESS_FREQUENCY:
            /* Use frequency domain method (harmonic balance) */
            computeHarmonicBalanceGuess(pss, ckt, pss->PSSinitialGuess);
            break;
            
        case PSS_GUESS_CONTINUATION:
            /* Continuation from known solution */
            if (pss->PSSsolution) {
                memcpy(pss->PSSinitialGuess, pss->PSSsolution, 
                       pss->CKTnumStates * sizeof(double));
            } else {
                /* Fall back to DC solution */
                memcpy(pss->PSSinitialGuess, ckt->CKTrhsOld, 
                       pss->CKTnumStates * sizeof(double));
            }
            break;
            
        default:
            return E_BADPARM;
    }
    
    return 0;
}
```

### 4.8 Parameter Configuration (`psssetp.c`)

```c
/* Set PSS analysis parameters */
int PSSsetParam(PSSanalysis *pss, int param, IFvalue *value) {
    switch (param) {
        case PSS_PERIOD:
            if (value->rValue <= 0.0) return E_BADPARM;
            pss->PSSperiod = value->rValue;
            break;
            
        case PSS_MAXITER:
            if (value->iValue < 1) return E_BADPARM;
            pss->PSSmaxIter = value->iValue;
            break;
            
        case PSS_CONVTOL:
            if (value->rValue <= 0.0) return E_BADPARM;
            pss->PSSconverge = value->rValue;
            break;
            
        case PSS_ABSTOL:
            pss->PSSabstol = value->rValue;
            break;
            
        case PSS_RELTOL:
            pss->PSSreltol = value->rValue;
            break;
            
        case PSS_NUMPOINTS:
            if (value->iValue < 10) return E_BADPARM;
            pss->PSSnumTimePoints = value->iValue;
            break;
            
        case PSS_GUESSMODE:
            pss->PSSmode = value->iValue;
            break;
            
        default:
            return E_BADPARM;
    }
    
    return 0;
}
```

### 4.9 Result Query Interface (`pssaskq.c`)

```c
/* Query PSS analysis results */
int PSSaskQuest(PSSanalysis *pss, int which, IFvalue *value) {
    switch (which) {
        case PSS_SOLUTION:
            /* Return steady-state initial condition */
            value->v.numValue = pss->CKTnumStates;
            value->v.vec.rVec = pss->PSSsolution;
            break;
            
        case PSS_WAVEFORM:
            /* Return full periodic waveform */
            value->v.numValue = pss->PSSnumTimePoints + 1;
            value->v.vec.rVec = pss->PSStimeGrid;
            value->v.vec.iVec = NULL; /* Time grid is real */
            break;
            
        case PSS_FLOQUET:
            /* Return Floquet multipliers (eigenvalues of M(T)) */
            computeFloquetMultipliers(pss, value->v.vec.rVec, value->v.vec.iVec);
            value->v.numValue = pss->CKTnumStates;
            break;
            
        case PSS_RESIDUAL:
            /* Return shooting residual norm */
            value->rValue = vectorNorm(pss->PSSresidual, pss->CKTnumStates);
            break;
            
        case PSS_ITERATIONS:
            /* Return number of Newton iterations */
            value->iValue = pss->PSSmaxIter; /* Actual count would be stored */
            break;
            
        default:
            return E_BADPARM;
    }
    
    return 0;
}
```

### 4.10 Polynomial Extrapolation for Step Prediction

```c
/* Polynomial extrapolation for better initial steps */
int PSSpolyExtrap(PSSanalysis *pss, double *x_pred, int order) {
    int i, j;
    double t, coeff;
    
    if (order < 1 || order > 4) return E_BADPARM;
    
    /* Use previous Newton steps to predict next initial guess */
    for (i = 0; i < pss->CKTnumStates; i++) {
        x_pred[i] = 0.0;
        
        /* Lagrange polynomial extrapolation */
        for (j = 0; j < order; j++) {
            coeff = lagrangeCoefficient(j, order, pss->PSStimeGrid);
            x_pred[i] += coeff * pss->PSSstateTrajectory[j][i];
        }
    }
    
    return 0;
}
```

### 4.11 Fourier Analysis for Frequency Domain Representation

```c
/* Compute Fourier coefficients of periodic solution */
int PSSfourierAnalysis(PSSanalysis *pss, PSSwaveform *wave, int numHarmonics) {
    int i, k, n;
    double *a, *b;
    double t, dt, omega;
    
    if (numHarmonics < 1) return E_BADPARM;
    
    wave->PSSnumHarmonics = numHarmonics;
    dt = pss->PSSperiod / pss->PSSnumTimePoints;
    omega = 2.0 * M_PI / pss->PSSperiod;
    
    /* Allocate coefficient arrays */
    a = (double*)malloc((numHarmonics + 1) * sizeof(double));
    b = (double*)malloc((numHarmonics + 1) * sizeof(double));
    
    /* For each state variable */
    for (n = 0; n < pss->CKTnumStates; n++) {
        /* Compute DC component (a₀) */
        a[0] = 0.0;
        for (i = 0; i <= pss->PSSnumTimePoints; i++) {
            a[0] += wave->PSSwaveValue[i][n];
        }
        a[0] /= (pss->PSSnumTimePoints + 1);
        
        /* Compute harmonic coefficients */
        for (k = 1; k <= numHarmonics; k++) {
            a[k] = 0.0;
            b[k] = 0.0;
            
            for (i = 0; i <= pss->PSSnumTimePoints; i++) {
                t = i * dt;
                a[k] += wave->PSSwaveValue[i][n] * cos(k * omega * t);
                b[k] += wave->PSSwaveValue[i][n] * sin(k * omega * t);
            }
            
            a[k] *= 2.0 / (pss->PSSnumTimePoints + 1);
            b[k] *= 2.0 / (pss->PSSnumTimePoints + 1);
        }
        
        /* Store coefficients */
        memcpy(wave->PSSfourCoeffs[n], a, (numHarmonics + 1) * sizeof(double));
        memcpy(wave->PSSfourCoeffs[n] + numHarmonics + 1, b + 1, 
               numHarmonics * sizeof(double));
    }
    
    free(a);
    free(b);
    return 0;
}
```

## 5. Numerical Stability and Performance Optimizations

### 5.1 Regularization for Ill-Conditioned Systems

```c
/* Apply Tikhonov regularization to ill-conditioned Jacobian */
int regularizeJacobian(PSSanalysis *pss, double lambda) {
    int i;
    double norm_J = matrixNorm(pss->PSSmonodromy, pss->CKTnumStates);
    
    /* Default regularization parameter if not specified */
    if (lambda <= 0.0) {
        lambda = MAX(1e-8, 1e-12 * norm_J);