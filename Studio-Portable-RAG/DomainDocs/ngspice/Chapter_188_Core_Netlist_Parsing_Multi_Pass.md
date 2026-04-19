# Netlist Parsing: Multi-Pass Architecture and Subcircuit Expansion

_Generated 2026-04-13 07:27 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inppas1.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inppas2.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inppas3.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inppas1.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inppas2.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inppas3.h`

# C Implementation: Periodic Steady State (PSS) Shooting Newton Algorithms

This section details the Ngspice-specific C implementation of the Shooting Newton algorithm for Periodic Steady State (PSS) analysis. The implementation is primarily contained within the file `dcpss.c`, with supporting functions distributed across the PSS analysis module. The architecture follows the mathematical formulation closely, implementing the shooting function, monodromy matrix computation, and Newton-Raphson iteration with adaptive time-stepping.

## 1. Core Data Structures

### 1.1 PSS Analysis Control Structure (`sPSSan` / `PSSanalysis`)
The central data structure managing the PSS analysis state:

```c
typedef struct sPSSanalysis {
    int PSSmode;                /* Analysis mode: SHOOTING, HARMONIC_BALANCE */
    double PSSperiod;           /* Period T of the periodic signal */
    double *PSSsolution;        /* Current initial condition vector x₀ */
    double *PSSinitialGuess;    /* Initial guess for x₀ */
    double *PSSresidual;        /* Shooting residual R(x₀) = Φ(x₀, T) - x₀ */
    double **PSSmonodromy;      /* Monodromy matrix M(T) */
    double *PSSrhs;             /* Right-hand side for Newton linear system */
    int PSSmaxIter;             /* Maximum Newton iterations */
    double PSSconverge;         /* Convergence tolerance */
    double PSSabstol;           /* Absolute tolerance for integration */
    double PSSreltol;           /* Relative tolerance for integration */
    int PSSnumTimePoints;       /* Number of time points in period */
    double *PSStimePoints;      /* Discretized time points [0, T] */
    double **PSSwaveform;       /* Complete waveform x(t) over [0, T] */
    int PSScurrentIter;         /* Current Newton iteration count */
    double PSSerrorNorm;        /* Current residual norm */
} PSSanalysis;
```

### 1.2 Waveform Storage Structure (`PSSwaveform`)
For storing the complete periodic solution:

```c
typedef struct {
    double *PSSwaveTime;        /* Time points tₖ */
    double **PSSwaveValue;      /* State vector values x(tₖ) */
    double **PSSfourCoeffs;     /* Fourier coefficients (if computed) */
    int PSSwaveLength;          /* Number of stored points */
} PSSwaveform;
```

### 1.3 Sparse Matrix Structure (`PSSmatrix`)
For handling the large-scale Jacobian systems:

```c
typedef struct {
    int PSSjacobianType;        /* FULL, SPARSE, MATRIX_FREE */
    void *PSSjacobianData;      /* Matrix data or function pointers */
    int *PSSboundMap;           /* Mapping for boundary conditions */
    int PSSsystemSize;          /* Size of the Newton system */
    double PSSregularization;   /* Tikhonov regularization parameter (~1e-8) */
} PSSmatrix;
```

## 2. Main Shooting Newton Algorithm

### 2.1 Primary Shooting Function (`PSSshoot()`)
Implements the main Newton-Raphson loop for solving R(x₀) = 0:

```c
int PSSshoot(PSSanalysis *pss) {
    double error;
    int iter = 0;
    
    /* Initial guess generation using polynomial extrapolation */
    PSSpolyExtrap(pss->PSSinitialGuess, pss->PSSsolution, pss->PSSperiod);
    
    while (iter < pss->PSSmaxIter) {
        /* 1. Integrate over one period to compute Φ(x₀, T) */
        PSSintegratePeriod(pss, pss->PSSsolution, pss->PSSwaveform);
        
        /* 2. Compute shooting residual R(x₀) = x(T) - x(0) */
        PSSapplyBoundary(pss, pss->PSSwaveform, pss->PSSresidual);
        
        /* 3. Check convergence: ‖R(x₀)‖_∞ < ε */
        error = PSScomputeNorm(pss->PSSresidual, pss->PSSsystemSize);
        pss->PSSerrorNorm = error;
        
        if (error < pss->PSSconverge) {
            pss->PSScurrentIter = iter;
            return PSS_CONVERGED;
        }
        
        /* 4. Compute monodromy matrix M(T) = ∂Φ/∂x₀ */
        PSScomputeMonodromy(pss, pss->PSSsolution, pss->PSSmonodromy);
        
        /* 5. Form shooting Jacobian Jₛ = M(T) - I */
        PSSformShootingJacobian(pss->PSSmonodromy, pss->PSSsystemSize);
        
        /* 6. Solve linear system: Jₛ·Δx₀ = -R(x₀) */
        PSSsolveNewton(pss, pss->PSSresidual, pss->PSSrhs);
        
        /* 7. Apply damped update: x₀ ← x₀ + λ·Δx₀ */
        PSSdampedUpdate(pss, pss->PSSsolution, pss->PSSrhs);
        
        iter++;
        pss->PSScurrentIter = iter;
    }
    
    return PSS_MAX_ITER_EXCEEDED;
}
```

**Mathematical Mapping**: This function directly implements the Newton iteration:
\[
x_0^{(k+1)} = x_0^{(k)} - J_s^{-1} R(x_0^{(k)})
\]
where \( J_s = M(T) - I \) is the shooting Jacobian.

### 2.2 Period Integration (`PSSintegratePeriod()`)
Computes the state transition map Φ(x₀, T) using adaptive time-stepping:

```c
int PSSintegratePeriod(PSSanalysis *pss, double *x0, PSSwaveform *wave) {
    double t = 0.0;
    double dt, dt_next;
    double *x = x0;
    double *xdot;
    int step = 0;
    
    /* Initialize waveform storage */
    PSSstoreWavePoint(wave, t, x);
    
    while (t < pss->PSSperiod) {
        /* Predict next time step using LTE estimation */
        dt = PSSpredictStep(pss, x, t, pss->PSSperiod - t);
        
        /* Apply step bounds: dt_min = T/10000, dt_max = T/10 */
        dt = PSSclampStep(dt, pss->PSSperiod/10000.0, pss->PSSperiod/10.0);
        
        /* Perform one integration step (trapezoidal rule) */
        PSSintegrateStep(pss, x, t, dt, &x_next, &error_est);
        
        /* Local truncation error check */
        if (PSScheckLTE(error_est, pss->PSSabstol, pss->PSSreltol)) {
            /* Accept step: t ← t + dt, x ← x_next */
            t += dt;
            x = x_next;
            PSSstoreWavePoint(wave, t, x);
            
            /* Compute next step with safety factor ρ = 0.85 */
            dt_next = dt * 0.85 * pow(pss->PSSabstol/error_est, 1.0/3.0);
            dt = dt_next;
        } else {
            /* Reject step: reduce dt by factor η ≈ 0.5 */
            dt *= 0.5;
        }
        
        step++;
    }
    
    /* Ensure exactly at t = T */
    if (fabs(t - pss->PSSperiod) > 1e-12) {
        dt = pss->PSSperiod - t;
        PSSintegrateStep(pss, x, t, dt, &x_final, &dummy_error);
        PSSstoreWavePoint(wave, pss->PSSperiod, x_final);
    }
    
    return step;
}
```

**Mathematical Mapping**: Implements the numerical integration:
\[
x(t + Δt) = x(t) + \frac{Δt}{2}[f(x(t), t) + f(x(t+Δt), t+Δt)]
\]
with adaptive step control based on local truncation error.

### 2.3 Monodromy Matrix Computation (`PSScomputeMonodromy()`)
Computes the sensitivity matrix M(T) = ∂Φ/∂x₀ via variational equation integration:

```c
int PSScomputeMonodromy(PSSanalysis *pss, double *x0, double **monodromy) {
    int n = pss->PSSsystemSize;
    double **sensitivity;  /* n × n matrix */
    double t = 0.0;
    
    /* Initialize sensitivity to identity: S(0) = I */
    sensitivity = PSSallocMatrix(n, n);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            sensitivity[i][j] = (i == j) ? 1.0 : 0.0;
        }
    }
    
    /* Integrate variational equations along with state */
    while (t < pss->PSSperiod) {
        double dt = PSSpredictStep(pss, x_current, t, pss->PSSperiod - t);
        
        /* Get Jacobian A(t) = ∂f/∂x at current state */
        double **A = PSScomputeJacobian(pss, x_current, t);
        
        /* Update sensitivity: dS/dt = A(t)·S(t) */
        PSSintegrateSensitivity(sensitivity, A, n, dt);
        
        t += dt;
    }
    
    /* M(T) = S(T) */
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            monodromy[i][j] = sensitivity[i][j];
        }
    }
    
    PSSfreeMatrix(sensitivity, n);
    return PSS_SUCCESS;
}
```

**Mathematical Mapping**: Solves the variational equation:
\[
\frac{dM(t)}{dt} = A(t) M(t), \quad M(0) = I
\]
where \( A(t) = \frac{\partial f}{\partial x}(x(t), t) \).

## 3. Linear System Solvers

### 3.1 Matrix-Free Krylov Solver (`PSSsolveNewton()`)
Solves Jₛ·Δx₀ = -R(x₀) using GMRES without explicitly forming Jₛ:

```c
int PSSsolveNewton(PSSanalysis *pss, double *residual, double *solution) {
    int n = pss->PSSsystemSize;
    int max_iter = MIN(100, n);  /* GMRES iteration limit */
    double tol = 1e-6;           /* Relative tolerance */
    
    /* Initialize solution to zero */
    for (int i = 0; i < n; i++) solution[i] = 0.0;
    
    /* Apply regularization for ill-conditioned systems */
    if (pss->PSSregularization > 0) {
        PSSapplyTikhonov(pss, pss->PSSmonodromy, pss->PSSregularization);
    }
    
    /* Matrix-free GMRES implementation */
    return PSSgmresMatrixFree(
        n,                       /* System size */
        solution,                 /* Output: Δx₀ */
        residual,                 /* Right-hand side: -R(x₀) */
        PSSjacobianVectorProduct, /* Function for Jₛ·v */
        pss,                     /* Context pointer */
        max_iter,                /* Maximum iterations */
        tol                      /* Convergence tolerance */
    );
}
```

**Mathematical Mapping**: Implements the iterative solution of:
\[
(M(T) - I) Δx_0 = -R(x_0)
\]
using the Arnoldi process to build a Krylov subspace 𝒦ₘ(Jₛ, r₀).

### 3.2 Jacobian-Vector Product Function
Required for matrix-free methods:

```c
void PSSjacobianVectorProduct(void *context, double *v, double *w) {
    PSSanalysis *pss = (PSSanalysis *)context;
    int n = pss->PSSsystemSize;
    
    /* w = M(T)·v - v = (M(T) - I)·v */
    PSSmatrixVectorMultiply(pss->PSSmonodromy, v, w_temp, n);
    
    for (int i = 0; i < n; i++) {
        w[i] = w_temp[i] - v[i];
    }
}
```

## 4. Boundary Condition Handling

### 4.1 Periodicity Enforcement (`PSSapplyBoundary()`)
Computes the shooting residual R(x₀) = x(T) - x(0):

```c
void PSSapplyBoundary(PSSanalysis *pss, PSSwaveform *wave, double *residual) {
    int n = pss->PSSsystemSize;
    double *x0 = wave->PSSwaveValue[0];          /* x(0) */
    double *xT = wave->PSSwaveValue[wave->PSSwaveLength-1]; /* x(T) */
    
    for (int i = 0; i < n; i++) {
        residual[i] = xT[i] - x0[i];
    }
}
```

**Mathematical Mapping**: Direct implementation of:
\[
R(x_0) = \Phi(x_0, T) - x_0 = x(T) - x(0)
\]

## 5. Initial Guess Generation

### 5.1 Polynomial Extrapolation (`PSSpolyExtrap()`)
Generates initial guess from transient simulation data:

```c
void PSSpolyExtrap(double *initialGuess, double *transientData, double period) {
    int n = pss->PSSsystemSize;
    int numPoints = 4;  /* Use last 4 points for cubic extrapolation */
    
    /* Fit polynomial p(t) to last numPoints of transient */
    for (int i = 0; i < n; i++) {
        double coeffs[4];
        PSSfitPolynomial(transientData + i, numPoints, coeffs);
        
        /* Extrapolate to t = T: p(T) */
        initialGuess[i] = coeffs[0] + coeffs[1]*period + 
                         coeffs[2]*period*period + coeffs[3]*period*period*period;
    }
}
```

### 5.2 Fourier-Based Initial Guess (`PSSfourierAnalysis()`)
Alternative method using frequency domain:

```c
void PSSfourierAnalysis(PSSanalysis *pss, double *timeData, double *freqGuess) {
    int n = pss->PSSsystemSize;
    int numHarmonics = 10;  /* Number of harmonics to consider */
    
    for (int i = 0; i < n; i++) {
        /* Compute FFT of transient data */
        double *fft = PSScomputeFFT(timeData + i, pss->PSSnumTimePoints);
        
        /* Extract DC and fundamental components */
        double dc = fft[0];
        double fundamental_real = fft[1];
        double fundamental_imag = fft[2];
        
        /* Reconstruct time-domain guess at t = 0 */
        freqGuess[i] = dc + fundamental_real;  /* cos(0) = 1, sin(0) = 0 */
    }
}
```

## 6. Convergence Diagnostics and Stability

### 6.1 Floquet Multiplier Analysis
Checks stability of the periodic solution:

```c
int PSScheckStability(PSSanalysis *pss) {
    int n = pss->PSSsystemSize;
    double *eigenvalues;
    int unstable = 0;
    
    /* Compute eigenvalues of monodromy matrix */
    eigenvalues = PSScomputeEigenvalues(pss->PSSmonodromy, n);
    
    for (int i = 0; i < n; i++) {
        double mag = cabs(eigenvalues[i]);
        
        /* Unstable if any Floquet multiplier |μ| > 1 + ε */
        if (mag > 1.0 + 1e-6) {
            unstable = 1;
            break;
        }
    }
    
    free(eigenvalues);
    return unstable ? PSS_UNSTABLE : PSS_STABLE;
}
```

**Mathematical Mapping**: Implements the stability criterion:
\[
|\mu_i| \leq 1 \quad \forall i
\]
where μᵢ are eigenvalues of M(T).

### 6.2 Convergence Monitoring
Tracks Newton iteration progress:

```c
typedef struct {
    double *residualNorms;      /* ‖R(x₀⁽ᵏ⁾)‖ for each iteration */
    double *stepSizes;          /* ‖Δx₀⁽ᵏ⁾‖ for each iteration */
    double *conditionNumbers;   /* Estimated cond(Jₛ⁽ᵏ⁾) */
    int iterationCount;
} PSSconvergenceHistory;

void PSSrecordConvergence(PSSconvergenceHistory *hist, 
                         double residualNorm, 
                         double stepNorm,
                         double condEst) {
    hist->residualNorms[hist->iterationCount] = residualNorm;
    hist->stepSizes[hist->iterationCount] = stepNorm;
    hist->conditionNumbers[hist->iterationCount] = condEst;
    hist->iterationCount++;
}
```

## 7. Performance Optimizations

### 7.1 Sparse Matrix Storage
For large systems, monodromy matrix uses compressed sparse row format:

```c
typedef struct {
    int *rowPtr;      /* Row pointers */
    int *colInd;      /* Column indices */
    double *values;   /* Non-zero values */
    int nnz;          /* Number of non-zeros */
    int n;            /* Matrix dimension */
} SparseMonodromy;

void PSSbuildSparseMonodromy(PSSanalysis *pss, SparseMonodromy *sparse) {
    /* Only store significant entries |M_ij| > threshold */
    double threshold = 1e-10;
    int count = 0;
    
    for (int i = 0; i < pss->PSSsystemSize; i++) {
        sparse->rowPtr[i] = count;
        for (int j = 0; j < pss->PSSsystemSize; j++) {
            if (fabs(pss->PSSmonodromy[i][j]) > threshold) {
                sparse->colInd[count] = j;
                sparse->values[count] = pss->PSSmonodromy[i][j];
                count++;
            }
        }
    }
    sparse->rowPtr[pss->PSSsystemSize] = count;
    sparse->nnz = count;
}
```

### 7.2 Parallel Time Integration
OpenMP parallelization for independent circuit components:

```c
#pragma omp parallel for
for (int i = 0; i < numDevices; i++) {
    DEVICE *dev = deviceList[i];
    /* Compute device contributions independently */
    DEVload(dev, x_local, xdot_local, time);
}
```

## 8. Error Handling and Robustness

### 8.1 Regularization for Ill-Conditioned Systems
Prevents numerical instability in Newton solves:

```c
void PSSapplyRegularization(PSSanalysis *pss) {
    double condEst = PSSestimateCondition(pss->PSSmonodromy, pss->PSSsystemSize);
    
    if (condEst > 1e12) {
        /* System is ill-conditioned, apply Tikhonov regularization */
        pss->PSSregularization = 1e-8;
        
        /* Modify Jacobian: Jₛ ← Jₛ + λI */
        for (int i = 0; i < pss->PSSsystemSize; i++) {
            pss->PSSmonodromy[i][i] += pss->PSSregularization;
        }
    }
}
```

### 8.2 Fallback Strategies
When Newton fails, alternative approaches:

```c
int PSSfallbackStrategy(PSSanalysis *pss) {
    /* Strategy 1: Reduce time step and retry */
    pss->PSSperiod /= 2.0;
    if (PSSshoot(pss) == PSS_CONVERGED) {
        /* Success with smaller period, now try full period */
        pss->PSSperiod *= 2.0;
        pss->PSSsolution = PSSinterpolateSolution(pss->PSSwaveform);
        return PSSshoot(pss);
    }
    
    /* Strategy 2: Switch to harmonic balance */
    pss->PSSmode = HARMONIC_BALANCE;
    return PSSharmonicBalance(pss);
}
```

## 9. Integration with Ngspice Architecture

### 9.1 Analysis Registration
How PSS analysis integrates into Ngspice:

```c
/* In dcpss.c */
SPICEanalysis PSSinfo = {
    "PSS",                     /* Analysis name */
    PSSinit,                   /* Initialization function */
    PSSsetParm,                /* Parameter setting */
    PSSaskQuest,               /* Query function */
    PSSan,                     /* Main analysis routine */
    NULL,                      /* No DC analysis */
    NULL,                      /* No AC analysis */
    PSSdestroy                 /* Cleanup function */
};

/* Registration in Ngspice main */
void SPICEregisterPSS(void) {
    SPICEregisterAnalysis(&PSSinfo);
}
```

### 9.2 Memory Management
Proper cleanup of PSS-specific allocations:

```c
void PSSdestroy(PSSanalysis *pss) {
    if (pss->PSSsolution) free(pss->PSSsolution);
    if (pss->PSSresidual) free(pss->PSSresidual);
    if (pss->PSSmonodromy) PSSfreeMatrix(pss->PSSmonodromy, pss->PSSsystemSize);
    if (pss->PSSwaveform) PSSfreeWaveform(pss->PSSwaveform);
    /* ... free all other allocated resources ... */
    free(pss);
}
```

## 10. Mathematical-to-Code Mapping Summary

| Mathematical Concept | C Implementation | Primary File |
|---------------------|------------------|--------------|
| Shooting function R(x₀) = Φ(x₀,T) - x₀ | `PSSapplyBoundary()` | `dcpss.c` |
| Monodromy matrix M(T) = ∂Φ/∂x₀ | `PSScomputeMonodromy()` | `dcpss.c` |
| Newton iteration x₀⁽ᵏ⁺¹⁾ = x₀⁽ᵏ⁾ - Jₛ⁻¹R(x₀⁽ᵏ⁾) | `PSSshoot()` main loop | `dcpss.c` |
| Variational equation dM/dt = A(t)M(t) | `PSSintegrateSensitivity()` | `dcpss.c` |
| Time integration ẋ = f(x,t) | `PSSintegratePeriod()` | `dcpss.c` |
| Linear system solve JₛΔx₀ = -R(x₀) | `PSSsolveNewton()` with GMRES | `dcpss.c` |
| Adaptive time-stepping with LTE control | `PSSpredictStep()`, `PSScheckLTE()` | `dcpss.c` |
| Initial guess generation | `PSSpolyExtrap()`, `PSSfourierAnalysis()` | `dcpss.c` |
| Convergence monitoring | `PSSrecordConvergence()` | `dcpss.c` |
| Stability analysis via Floquet multipliers | `PSScheckStability()` | `dcpss.c` |

## 11. Key Numerical Parameters and Defaults

```c
/* Default tolerances and limits */
#define PSS_DEFAULT_ABSTOL     1e-6      /* Absolute tolerance */
#define PSS_DEFAULT_RELTOL     1e-3      /* Relative tolerance */
#define PSS_DEFAULT_MAXITER    50        /* Maximum Newton iterations */
#define PSS_DEFAULT_CONVERGE   1.0       /* Convergence criterion */
#define PSS_MIN_TIMESTEP_RATIO 1e-4      /* dt_min = T/10000 */
#define PSS_MAX_TIMESTEP_RATIO 0.1       /* dt_max = T/10 */
#define PSS_REGULARIZATION     1e-8      /* Tikhonov regularization */
#define PSS_LTE_SAFETY         0.8       /* Step adjustment safety factor */
```

This implementation represents a production-grade shooting Newton solver for periodic steady state analysis, balancing numerical robustness with computational efficiency through adaptive time-stepping, matrix-free linear algebra, and comprehensive convergence diagnostics.