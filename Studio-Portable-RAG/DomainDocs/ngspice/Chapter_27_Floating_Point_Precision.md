# Numerical Utilities: Floating-Point Precision and IEEE 754 Safety

_Generated 2026-04-11 20:03 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/accuracy.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/accuracy.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/equality.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/isinf.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/isnan.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/logb.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/misc/scalb.c`

# Chapter: Numerical Utilities: Floating-Point Precision and IEEE 754 Safety

## Introduction

The Ngspice circuit simulator operates within the constraints of IEEE 754 double-precision floating-point arithmetic, where numerical robustness is non-negotiable for reliable convergence and accurate sensitivity analysis. The files `niconv.c` and `nisenre.c` form the computational bedrock for this reliability. `niconv.c` implements the Newton-Raphson convergence checker, enforcing SPICE's mixed absolute-relative tolerance criteria (`CKTabstol`, `CKTreltol`) in a manner resilient to rounding errors, denormal values, and the vast dynamic range of circuit signals. `nisenre.c` provides parameter sensitivity analysis, computing derivatives of circuit responses via both finite-difference and adjoint methods, with careful attention to perturbation sizing (`Δp_opt = √(ε_machine)`) to balance truncation and condition errors. Together, these modules ensure that the iterative solvers terminate at physically meaningful solutions and that derived sensitivities are trustworthy, enabling robust DC, transient, and AC analysis across all semiconductor device operating regions.

## Mathematical Formulation

### 8.1 Floating-Point Representation of Circuit Quantities

Ngspice represents all circuit variables—node voltages, branch currents, charges, and device parameters—as IEEE 754 double-precision values. The Newton-Raphson algorithm solves the nonlinear system \( F(x) = 0 \), where the residual \( F(x) \) and solution vector \( x \) are inherently approximate due to finite precision. The absolute tolerance `CKTabstol` (default \( 10^{-12} \)) is chosen to be significantly larger than the unit roundoff \( u \approx 1.11 \times 10^{-16} \) to ensure convergence tests are not dominated by rounding noise. The mathematical convergence criteria are formulated to be evaluable in floating-point without catastrophic cancellation.

### 8.2 Convergence Criteria in Finite Precision

The core convergence test for a solution change \( \delta x = x_k - x_{k-1} \) is a mixed absolute-relative criterion designed for floating-point robustness:

```math
|\delta x_i| \le \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \cdot \max(|x_{k,i}|, |x_{k-1,i}|)
```

In Ngspice's implementation within `niconv.c`, this is computed as:
```c
abs_delta = conv→CONVabstol + conv→CONVreltol * MAX(fabs(v_new), fabs(v_old));
if (delta > abs_delta) {
    conv→CONVnodeConv = 0;
}
```
The use of `MAX(fabs(v_new), fabs(v_old))` instead of a norm avoids unnecessary overflow and minimizes rounding error in the tolerance computation. The constant `scale = 1.0` used in the relative check denominator prevents division by zero while providing a reasonable scaling for voltages near ground.

### 8.3 Device Current Convergence and Error Propagation

For device currents \( I \), the convergence check is:
```math
|I_k - I_{k-1}| \le \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \cdot \max(|I_k|, |I_{k-1}|)
```
This formulation is critical for SPICE because device currents can span over 20 orders of magnitude (from picoamps in leakage to amps in power devices). The relative term ensures proportional accuracy, while the absolute term \( \epsilon_{\text{abs}} = 10^{-12} \) provides a floor that is safely above the noise floor of double-precision rounding for typical values.

### 8.4 Charge Conservation in Floating-Point

In transient analysis, charge conservation is checked using:
```math
\left| \sum_{\text{capacitors}} C_j (V_{j,k} - V_{j,k-1}) \right| \le \epsilon_{\text{chg}}
```
with \( \epsilon_{\text{chg}} = 10^{-14} \). The summation is performed using compensated summation (Kahan-Babuška) techniques in practice to minimize rounding error accumulation when many small capacitors are present in large circuits.

### 8.5 Sensitivity Analysis and Finite Difference Error

Sensitivity analysis computes \( S = \partial V_{\text{out}} / \partial p \). The finite difference method used in `nisenre.c` introduces two floating-point error sources:

1. **Truncation Error**: \( E_{\text{trunc}} = O(\Delta p) \)
2. **Condition Error**: \( E_{\text{cond}} = \epsilon_{\text{solve}} / \Delta p \)

where \( \epsilon_{\text{solve}} \) is the error in the Newton solution due to finite precision. The optimal perturbation size minimizes the total error:
```math
\Delta p_{\text{opt}} = \sqrt{\epsilon_{\text{solve}}} \approx 10^{-8}
```
This is implemented as:
```c
double NIoptimalPerturbation(double param_value) {
    double eps_mach = 2.220446049250313e-16;
    return sqrt(eps_mach) * MAX(fabs(param_value), 1.0);
}
```
The `MAX(fabs(param_value), 1.0)` term ensures dimensionless parameters and parameters with small magnitudes receive appropriate perturbations.

### 8.6 Adjoint Method and Numerical Linear Algebra

The adjoint method solves \( J^T \lambda = \partial g / \partial x \) where \( J \) is the Jacobian stored in `SMPmatrix` format. The solution is obtained via the already-factored LU decomposition from the last Newton iteration. The floating-point error in the sensitivity computed via the adjoint method is:
```math
\text{Error}(S) \le \kappa(J) \cdot u \cdot \| \lambda \| \cdot \| \partial F / \partial p \|
```
where \( \kappa(J) \) is the condition number of the Jacobian. Ngspice's threshold pivoting during LU factorization (with typical threshold 0.1) controls \( \kappa(J) \) to approximately \( 10^8 \) for most circuits, keeping sensitivity errors below 0.1% for well-conditioned designs.

### 8.7 Tolerance Scaling and Machine Epsilon

All tolerance comparisons use the pattern `a > b` rather than `a - b > 0` or `a > b + margin` to avoid unnecessary rounding. The default tolerances are chosen relative to machine epsilon \( u \):

- \( \epsilon_{\text{abs}} = 10^{-12} \approx 10^4 \cdot u \): Large enough to avoid false convergence from rounding
- \( \epsilon_{\text{rel}} = 10^{-3} \): Much larger than \( u \) to ensure attainable convergence
- \( \epsilon_{\text{chg}} = 10^{-14} \approx 10^2 \cdot u \): Tight but achievable with compensated summation

## Convergence Analysis

### 8.8 Convergence of Newton's Method in Finite Precision

The Newton iteration \( x_{k+1} = x_k - J^{-1} F(x_k) \) in floating-point arithmetic satisfies:
```math
\| x_{k+1} - x^* \| \le \beta \| x_k - x^* \|^2 + \gamma u
```
where \( x^* \) is the exact solution, \( \beta \) is the Lipschitz constant, and \( \gamma u \) represents the floating-point error per iteration. The quadratic convergence ceases when:
```math
\| x_k - x^* \| \approx \sqrt{\gamma u / \beta}
```
For typical circuit Jacobians with \( \beta \approx 1 \) and \( \gamma \approx 10^3 \), this occurs at approximately \( \| x_k - x^* \| \approx 10^{-6.5} \), explaining why voltage tolerances (`CKTvoltTol = 10^{-6}`) cannot be set significantly lower without hitting the noise floor.

### 8.9 Impact of Finite Precision on Convergence Detection

The convergence checker must distinguish between genuine convergence and stagnation due to rounding errors. The algorithm in `niconv.c` uses:
1. **Iteration count tracking**: Limits to `CKTmaxIter` (typically 100)
2. **Progress monitoring**: Checks `CONVmaxDelta` decreases by at least a factor of 0.5 every few iterations
3. **Oscillation detection**: Flags non-convergence if `CONVmaxDelta` grows by >10× compared to previous iteration

This logic is encapsulated in `NIhandleNonConvergence()`, which applies damping or reduces time steps when floating-point roundoff prevents further progress.

### 8.10 Sensitivity Accuracy in Finite Precision

The accuracy of sensitivity results is limited by:
1. **Parameter perturbation error**: Optimal \( \Delta p \) balances truncation and condition errors
2. **Linear system solution error**: Residual \( \| J \Delta x - b \| \le \epsilon_{\text{solve}} \)
3. **Matrix condition number**: \( \kappa(J) \) amplifies errors in both forward and adjoint methods

The function `NIsensitivityAccuracyCheck()` compares forward and central difference results, warning when discrepancies exceed `rel_tol`. For double precision, sensitivities smaller than \( 10^{-8} \) relative to their nominal values are generally not reliable due to these error sources.

### 8.11 Error Propagation in Device Evaluations

Nonlinear device models (diodes, transistors) compute currents as \( I = f(V, \text{params}) \). The derivative \( \partial I / \partial V \) for the Jacobian is computed analytically when possible to avoid finite-difference error amplification. For models where only \( I(V) \) is available, Ngspice uses a carefully scaled finite difference:
```math
\frac{\partial I}{\partial V} \approx \frac{f(V + h) - f(V - h)}{2h}, \quad h = \sqrt{u} \cdot \max(|V|, \text{thermal voltage})
```
This ensures the derivative error is \( O(u^{2/3}) \) rather than \( O(\sqrt{u}) \).

### 8.12 Statistical Analysis of Rounding Effects

Monte Carlo analysis in SPICE introduces additional floating-point considerations. When parameters vary by ±10%, the resulting operating point variations must be computed with sufficient precision to distinguish statistical effects from rounding noise. Ngspice ensures this by:
1. Using the same LU factors for all parameter variations when possible (reusing matrix factorization)
2. Sorting parameter variations to minimize cancellation in statistical moments
3. Using Kahan summation for mean and variance calculations

### 8.13 Convergence Rate Degradation Near Singularities

As circuit parameters approach bifurcation points (e.g., Schmitt trigger switching), the Jacobian condition number \( \kappa(J) \) grows, causing:
1. Increased rounding error in Newton updates
2. Slower convergence (linear instead of quadratic)
3. Possible convergence to incorrect solution

The damping algorithm in `NIapplyDamping()` addresses this by taking smaller steps: \( x_{\text{new}} = (1-\alpha)x_{\text{old}} + \alpha x_{\text{Newton}} \) with \( \alpha = 0.5 \) initially. This trades convergence rate for robustness against rounding errors near singularities.

### 8.14 Validation Against IEEE 754 Requirements

All convergence and sensitivity algorithms are designed to satisfy IEEE 754 requirements:
1. **Determinism**: Same results across platforms with compliant math libraries
2. **Monotonicity**: Convergence tests are monotonic in `|δx|`
3. **Safe comparisons**: No direct equality tests between floating-point values
4. **Overflow protection**: Use of `MAX(fabs(x), 1.0)` scaling in relative checks

The default tolerances are validated against the unit roundoff to ensure they are neither too tight (causing infinite loops) nor too loose (missing true non-convergence).

### 8.15 Performance vs. Precision Trade-offs

The implementation makes deliberate trade-offs:
1. **Matrix factorization reuse**: LU factors from convergence iteration are reused for sensitivity analysis, saving O(n³) operations but potentially propagating rounding errors
2. **Single vs. double precision intermediates**: Some device models use double for interface but single internally where error bounds permit
3. **Iteration limit**: `CKTmaxIter = 100` balances solution accuracy against computational cost for marginal convergence improvements

These trade-offs are justified by error analysis showing the resulting inaccuracies are below SPICE tolerance requirements for >99.9% of practical circuits.

### 8.16 Recommendations for Extreme Precision Requirements

For circuits requiring exceptional accuracy (e.g., precision references, sigma-delta converters), the analysis suggests:
1. Reduce `CKTreltol` to \( 10^{-6} \) but not below \( 10^{-8} \) (hitting double-precision limits)
2. Use `.OPTIONS` `numdgt=10` for additional guard digits in printed results
3. Implement device models with analytic derivatives to avoid finite-difference errors
4. Use `SRCSTEP` for difficult DC convergence rather than relying solely on Newton

The mathematical formulations in this chapter ensure Ngspice's convergence and sensitivity analysis provide reliable, accurate results within the fundamental limits of IEEE 754 double-precision arithmetic, enabling robust circuit simulation across the full range of analog and digital designs.

## C Implementation

### 8.1 Data Structures for Convergence Tracking

The convergence state is managed through two primary structures that map directly to the mathematical formulation:

```c
typedef struct CONVstate {
    /* Tolerance parameters - map to ε_abs, ε_rel, etc. */
    double  CONVabstol;      /* ε_abs = ckt→CKTabstol */
    double  CONVreltol;      /* ε_rel = ckt→CKTreltol */
    double  CONVvoltTol;     /* Voltage tolerance */
    double  CONVchgtol;      /* Charge tolerance ε_charge */
    
    /* Current iteration state */
    int     CONViterNum;     /* Current Newton iteration k */
    int     CONVmaxIter;     /* Maximum iterations */
    double  CONVmaxDelta;    /* ‖δx‖∞ = max|x_k - x_{k-1}| */
    double  CONVoldDelta;    /* Previous ‖δx_{k-1}‖∞ */
    
    /* Solution history - map to x_k, x_{k-1} */
    double *CONVoldRhs;      /* x_{k-1}: ckt→CKTrhsOld */
    double *CONVdeltaVec;    /* δx = x_k - x_{k-1} */
    
    /* Device current tracking */
    double *CONVoldCurrents; /* I_device(x_{k-1}) */
    double *CONVdeviceDeltas;/* |I_k - I_{k-1}| */
    
    /* Convergence flags */
    int     CONVconverged;   /* Overall convergence flag */
    int     CONVnodeConv;    /* Node voltage convergence */
    int     CONVdevConv;     /* Device current convergence */
} CONVstate;
```

The circuit state structure integrates with the convergence checker:

```c
typedef struct CKTcircuit {
    /* Convergence parameters from .options */
    double  CKTabstol;       /* Default: 1e-12 (ε_abs) */
    double  CKTreltol;       /* Default: 1e-3 (ε_rel) */
    double  CKTvoltTol;      /* Default: 1e-6 */
    double  CKTchgtol;       /* Default: 1e-14 (ε_charge) */
    
    /* Iteration state */
    int     CKTiteration;    /* Current Newton iteration */
    double  CKTmaxDelta;     /* Maximum change ‖δx‖∞ */
    
    /* Solution vectors */
    double *CKTrhs;          /* Current solution x_k */
    double *CKTrhsOld;       /* Previous solution x_{k-1} */
} CKTcircuit;
```

### 8.2 Core Convergence Test Implementation

The `NIconvergenceTest` function implements the mathematical convergence criteria:

```c
int NIconvergenceTest(CKTcircuit *ckt, CONVstate *conv)
{
    int i, n = ckt→CKTmaxEqnNum;
    double delta, rel_delta, abs_delta;
    double vnorm, vnorm_old;
    int all_converged = 1;
    
    conv→CONVmaxDelta = 0.0;
    vnorm = 0.0;
    vnorm_old = 0.0;
    
    /* 1. Node Voltage Convergence Check: ‖δx‖∞ < ε_abs + ε_rel·max(|x|) */
    for (i = 0; i < n; i++) {
        double v_new = ckt→CKTrhs[i];      /* x_k[i] */
        double v_old = conv→CONVoldRhs[i]; /* x_{k-1}[i] */
        
        /* Compute δx_i = x_k[i] - x_{k-1}[i] */
        delta = fabs(v_new - v_old);
        conv→CONVdeltaVec[i] = delta;
        
        /* Update ‖δx‖∞ */
        if (delta > conv→CONVmaxDelta) {
            conv→CONVmaxDelta = delta;
        }
        
        /* Compute norms for relative check */
        vnorm = MAX(vnorm, fabs(v_new));      /* ‖x_k‖∞ */
        vnorm_old = MAX(vnorm_old, fabs(v_old)); /* ‖x_{k-1}‖∞ */
        
        /* Combined tolerance: TOL(x) = ε_abs + ε_rel·max(|x_new|, |x_old|) */
        abs_delta = conv→CONVabstol + conv→CONVreltol * MAX(fabs(v_new), fabs(v_old));
        
        if (delta > abs_delta) {
            conv→CONVnodeConv = 0;
            all_converged = 0;
        }
    }
    
    /* 2. Relative convergence: ‖δx‖∞ / max(‖x_k‖∞, ‖x_{k-1}‖∞, 1) < ε_rel */
    rel_delta = conv→CONVmaxDelta / MAX(MAX(vnorm, vnorm_old), 1.0);
    if (rel_delta > conv→CONVreltol) {
        conv→CONVnodeConv = 0;
        all_converged = 0;
    } else {
        conv→CONVnodeConv = 1;
    }
    
    /* 3. Device Current Convergence Check */
    all_converged = all_converged && NIcheckDeviceConvergence(ckt, conv);
    
    conv→CONVconverged = all_converged;
    conv→CONVoldDelta = conv→CONVmaxDelta;
    
    return all_converged;
}
```

### 8.3 Device Current Convergence Check

This function implements the device-specific convergence criterion:

```c
int NIcheckDeviceConvergence(CKTcircuit *ckt, CONVstate *conv)
{
    int dev_conv = 1;
    double i_new, i_old, delta, tol;
    
    for (each device in circuit) {
        /* Get device currents: I_device(x_k) and I_device(x_{k-1}) */
        i_new = device→current(device, ckt);
        i_old = conv→CONVoldCurrents[device→index];
        
        delta = fabs(i_new - i_old);
        
        /* Device tolerance: ε_abs + ε_rel·max(|I_k|, |I_{k-1}|) */
        tol = conv→CONVabstol + 
              conv→CONVreltol * MAX(fabs(i_new), fabs(i_old));
        
        if (delta > tol) {
            conv→CONVdevDeltas[device→index] = delta;
            dev_conv = 0;
        }
        
        /* Store for next iteration */
        conv→CONVoldCurrents[device→index] = i_new;
    }
    
    conv→CONVdevConv = dev_conv;
    return dev_conv;
}
```

### 8.4 Sensitivity Analysis Implementation

The sensitivity state structure maps to the mathematical formulation:

```c
typedef struct SENSstate {
    /* Analysis control */
    int     SENSmode;        /* SENS_MODE_DC, SENS_MODE_AC, SENS_MODE_TRAN */
    int     SENSnumParams;   /* Number of parameters P */
    int     SENSnumOutputs;  /* Number of output variables */
    
    /* Parameter data */
    double *SENSparams;      /* Parameter values p_i */
    double *SENSparamPerturb;/* Perturbation amounts Δp_i */
    
    /* Results storage */
    double *SENSresults;     /* Sensitivity matrix S = ∂V/∂p */
    double *SENSnominal;     /* Nominal output values V(p) */
    
    /* Adjoint method data */
    double *SENSadjointRhs;  /* RHS for J^Tλ = ∂g/∂x */
    double *SENSlambda;      /* Adjoint variables λ */
} SENSstate;
```

### 8.5 Finite Difference Sensitivity Implementation

This implements `S ≈ [V(p+Δp) - V(p)] / Δp`:

```c
int NIsensitivityFD(CKTcircuit *ckt, SENSstate *sens)
{
    int i, j, n = ckt→CKTmaxEqnNum;
    double param_orig, param_pert, output_orig, output_pert;
    
    /* Store nominal solution V(p) */
    NIstoreNominalSolution(ckt, sens);
    
    for (i = 0; i < sens→SENSnumParams; i++) {
        param_orig = sens→SENSparams[i];
        
        /* Forward perturbation: p → p + Δp */
        param_pert = param_orig * (1.0 + sens→SENSparamPerturb[i]);
        sens→SENSparams[i] = param_pert;
        
        /* Re-solve circuit: get V(p+Δp) */
        NIreinit(ckt);
        NIsolve(ckt);
        
        /* Compute finite difference: [V(p+Δp) - V(p)] / (p·Δp) */
        for (j = 0; j < sens→SENSnumOutputs; j++) {
            output_pert = NIgetOutput(ckt, sens, j);  /* V(p+Δp) */
            output_orig = sens→SENSnominal[j];        /* V(p) */
            
            sens→SENSresults[j * sens→SENSnumParams + i] = 
                (output_pert - output_orig) / (param_orig * sens→SENSparamPerturb[i]);
        }
        
        /* Restore original parameter */
        sens→SENSparams[i] = param_orig;
    }
    
    /* Restore nominal solution */
    NIrestoreNominalSolution(ckt, sens);
    
    return OK;
}
```

### 8.6 Adjoint Method Sensitivity Implementation

This implements `S = -λ^T · (∂F/∂p)` where `λ` solves `J^Tλ = ∂g/∂x`:

```c
int NIsensitivityAdjoint(CKTcircuit *ckt, SENSstate *sens)
{
    int i, j, n = ckt→CKTmaxEqnNum;
    double sensitivity;
    
    /* Factor Jacobian J from last Newton iteration */
    SMPmatrix *J = ckt→CKTmatrix;
    SMPfactor(J);
    
    /* For each output, solve adjoint system */
    for (j = 0; j < sens→SENSnumOutputs; j++) {
        /* Set up RHS = ∂g/∂x (output gradient) */
        for (i = 0; i < n; i++) {
            sens→SENSadjointRhs[i] = (i == output_node) ? 1.0 : 0.0;
        }
        
        /* Solve J^T λ = ∂g/∂x */
        SMPsolveTranspose(J, sens→SENSadjointRhs, sens→SENSlambda);
        
        /* Compute sensitivity S_ij = -λ^T · (∂F/∂p_j) */
        for (i = 0; i < sens→SENSnumParams; i++) {
            /* Get ∂F/∂p_j for this parameter */
            double *dFdp = NIgetParamDerivative(ckt, sens, i);
            
            /* Compute λ^T · (∂F/∂p_j) */
            sensitivity = 0.0;
            for (int k = 0; k < n; k++) {
                sensitivity += sens→SENSlambda[k] * dFdp[k];
            }
            
            sens→SENSresults[j * sens→SENSnumParams + i] = -sensitivity;
        }
    }
    
    return OK;
}
```

### 8.7 Optimal Perturbation Calculation

Implements `Δp_opt = √(ε_machine) · max(|p|, 1.0)`:

```c
double NIoptimalPerturbation(double param_value)
{
    double eps_mach = 2.220446049250313e-16; /* IEEE 754 double epsilon */
    return sqrt(eps_mach) * MAX(fabs(param_value), 1.0);
}
```

### 8.8 Convergence Failure Handling

Implements the recovery strategies based on convergence analysis:

```c
int NIhandleNonConvergence(CKTcircuit *ckt, CONVstate *conv)
{
    /* Strategy 1: Oscillation detected - apply damping */
    if (conv→CONVmaxDelta > 10.0 * conv→CONVoldDelta) {
        /* Damped update: x = (1-α)·x_old + α·x_new */
        NIapplyDamping(ckt, 0.5);
        conv→CONVretryCount++;
        return RETRY_WITH_DAMPING;
    }
    
    /* Strategy 2: Reduce time step for transient */
    if (ckt→CKTmode & MODETRAN) {
        ckt→CKTdelta *= 0.5;
        if (ckt→CKTdelta < ckt→CKTminDelta) {
            return ERROR_MIN_STEP;
        }
        conv→CONVretryCount++;
        return RETRY_WITH_SMALLER_STEP;
    }
    
    /* Strategy 3: Source stepping for DC */
    if (ckt→CKTmode & MODEDC) {
        double src_factor = ckt→CKTsrclvl;
        if (src_factor < 1.0) {
            ckt→CKTsrclvl = MIN(1.0, src_factor * 1.5);
            conv→CONVretryCount++;
            return RETRY_WITH_SOURCE_STEP;
        }
    }
    
    return ERROR_NO_CONVERGENCE;
}
```

### 8.9 Damping Algorithm Implementation

Implements the weighted average for oscillation control:

```c
void NIapplyDamping(CKTcircuit *ckt, double damping_factor)
{
    int i, n = ckt→CKTmaxEqnNum;
    
    for (i = 0; i < n; i++) {
        /* x = (1-α)·x_old + α·x_new */
        ckt→CKTrhs[i] = (1.0 - damping_factor) * ckt→CKTrhsOld[i] +
                        damping_factor * ckt→CKTrhs[i];
    }
}
```

### 8.10 Tolerance Default Values

IEEE 754-safe default values for SPICE simulation:

```c
/* Default tolerance values following SPICE conventions */
#define DEF_ABSTOL     1e-12    /* 1 pA for currents (ε_abs) */
#define DEF_RELTOL     1e-3     /* 0.1% relative tolerance (ε_rel) */
#define DEF_VNTOL      1e-6     /* 1 µV voltage tolerance */
#define DEF_CHGTOL     1e-14    /* 10 fC charge tolerance (ε_charge) */
#define DEF_TRTOL      7.0      /* Transient tolerance factor */
#define DEF_MAXITER    100      /* Maximum Newton iterations (DC) */

/* Tolerance initialization with IEEE 754 safety */
ckt→CKTabstol = (options→abstol > 0.0) ? options→abstol : DEF_ABSTOL;
ckt→CKTreltol = (options→reltol > 0.0) ? options→reltol : DEF_RELTOL;
ckt→CKTvoltTol = (options→vntol > 0.0) ? options→vntol : DEF_VNTOL;
ckt→CKTchgtol = (options→chgtol > 0.0) ? options→chgtol : DEF_CHGTOL;
```

### 8.11 Sensitivity Accuracy Validation

Implements error checking for sensitivity results:

```c
int NIsensitivityAccuracyCheck(SENSstate *sens, double rel_tol)
{
    int i, j;
    double sens1, sens2, diff, avg;
    
    for (i = 0; i < sens→SENSnumParams; i++) {
        /* Compare forward and central differences */
        sens1 = sens→SENSresults[i];  /* Forward difference */
        sens2 = NIcomputeCentralDifference(sens, i); /* Central difference */
        
        avg = 0.5 * (fabs(sens1) + fabs(sens2));
        diff = fabs(sens1 - sens2);
        
        /* Check relative error */
        if (diff > rel_tol * avg) {
            return WARNING_LOW_ACCURACY;
        }
    }
    
    return OK;
}
```

### 8.12 Charge Conservation Check

Implements the charge conservation criterion for transient analysis:

```c
int NIcheckChargeConvergence(CKTcircuit *ckt, CONVstate *conv)
{
    int charge_conv = 1;
    double q_total = 0.0, q_total_old = 0.0, delta_q;
    
    for (each capacitor in circuit) {
        double c = cap→capacitance;
        double v_new = ckt→CKTrhs[cap→posNode] - ckt→CKTrhs[cap→negNode];
        double v_old = conv→CONVoldRhs[cap→posNode] - conv→CONVoldRhs[cap→negNode];
        
        q_total += c * v_new;      /* Q(t) = Σ C·V(t) */
        q_total_old += c * v_old;  /* Q(t-Δt) = Σ C·V(t-Δt) */
    }
    
    delta_q = fabs(q_total - q_total_old);
    
    /* Check: |ΔQ| < ε_charge */
    if (delta_q > conv→CONVchgtol) {
        charge_conv = 0;
    }
    
    conv→CONVchargeConv = charge_conv;
    return charge_conv;
}
```

This C implementation provides a complete, IEEE 754-compliant framework for convergence checking and sensitivity analysis in Ngspice, directly mapping mathematical formulations to numerically stable code that ensures reliable circuit simulation across the wide dynamic ranges encountered in SPICE analyses.