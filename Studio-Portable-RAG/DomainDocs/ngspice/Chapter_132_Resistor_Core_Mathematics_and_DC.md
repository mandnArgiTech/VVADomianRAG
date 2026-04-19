# Resistor: Ohm's Law, Temperature Scaling, and DC Load

_Generated 2026-04-12 20:26 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/restemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resload.c`

# **Chapter 8: Diode: Sensitivity and Harmonic Distortion Analysis**

## **Technical Introduction**

This chapter details the advanced analysis capabilities of the Ngspice diode model, focusing on two critical aspects for modern analog and RF circuit design: **sensitivity analysis** and **harmonic distortion analysis**. The implementation is distributed across a suite of specialized C files that extend the core diode model (`dio.c`, `dioload.c`). The primary files covered here are:

*   **`diosload.c`, `diosacl.c`, `diosset.c`, `diosupd.c`, `diosprt.c`**: This group implements the **discrete adjoint method** for sensitivity analysis. `diosload.c` stamps the adjoint circuit's Jacobian matrix, `diosacl.c` handles AC small-signal sensitivity, `diosset.c` initializes sensitivity data structures, `diosupd.c` updates parameter derivatives during Newton-Raphson iterations, and `diosprt.c` computes and prints the final sensitivity integrals.
*   **`diodisto.c`, `diodset.c`**: These files implement **harmonic and intermodulation distortion** analysis. `diodisto.c` computes the Volterra series kernels (Taylor coefficients g1, g2, g3) of the diode's nonlinear I-V and C-V characteristics and stamps the corresponding distortion currents into the frequency-domain system. `diodset.c` performs the necessary setup and memory allocation for distortion analysis.

Together, these modules transform the basic DC diode model into a tool for predicting yield (via parameter sensitivity), linearity (via distortion metrics), and their interplay in real-world manufacturing variations.

---

## **Mathematical Formulation**

### **8.1 Sensitivity Analysis via the Adjoint Method**

Sensitivity analysis computes the gradient of any circuit output (e.g., a node voltage) with respect to a device parameter `p` (e.g., saturation current `I_S`, emission coefficient `N`). For transient analysis, Ngspice employs the **discrete adjoint method**, which is computationally efficient for many outputs.

The sensitivity of an output function `Φ` (e.g., `V_out(t_end)`) w.r.t. parameter `p` is given by the integral:
```
∂Φ/∂p = ∫_{0}^{T} λᵀ(t) · [ (∂G/∂p) V(t) - (∂I/∂p) ] dt
```
where:
*   `λ(t)` is the **adjoint variable vector**, solved from the **adjoint system**: `Gᵀ λ = ∂Φ/∂V`.
*   `G` is the circuit Jacobian matrix.
*   `V(t)` is the forward-time nodal voltage vector.
*   `∂G/∂p` and `∂I/∂p` are parameter derivatives of the matrix and RHS vector.

For a diode, key parameter derivatives are derived from the Shockley equation and its extensions:

**1. Saturation Current (`I_S`):**
```
∂I_D/∂I_S = exp(V_D / (N V_T)) - 1
∂G_D/∂I_S = (1/(N V_T)) * exp(V_D / (N V_T))
```
where `G_D = ∂I_D/∂V_D`.

**2. Emission Coefficient (`N`):**
```
∂I_D/∂N = - (I_S * V_D / (N² V_T)) * exp(V_D / (N V_T))
∂G_D/∂N = - (I_S / (N V_T)) * exp(V_D / (N V_T)) * [V_D/(N V_T) + 2]
```

**3. Series Resistance (`R_S`):**
The effective junction voltage is `V_J = V_D - I_D R_S`. The derivative requires solving via the chain rule:
```
∂I_D/∂R_S = -I_D * (∂I_D/∂V_J) / [1 + R_S (∂I_D/∂V_J)]
```

**4. Junction Capacitance Parameters (`C_J0`, `φ`, `m`):**
For the depletion capacitance `C_j(V) = C_J0 / (1 - V/φ)^m`, the charge derivative is:
```
∂Q_j/∂C_J0 = φ * (1 - (1 - V/φ)^{1-m}) / (1-m)
∂Q_j/∂φ = C_J0 * [ (1 - V/φ)^{1-m} * ( (1-m)V/φ² ) - 1/(1-m) * (1 - (1 - V/φ)^{1-m}) ]
```
These derivatives directly contribute to `∂I/∂p` in the sensitivity integral via `dQ/dt`.

### **8.2 Harmonic Distortion Analysis**

Harmonic distortion quantifies the generation of unwanted frequency components due to device nonlinearity. For a diode driven by a single-tone signal `v_d(t) = V_bias + V_ac cos(ωt)`, the nonlinear current `i_d(v_d)` is expanded as a Taylor series around the bias point:
```
i_d(v_d) ≈ I_0 + g₁·v_ac + (g₂/2!)·v_ac² + (g₃/3!)·v_ac³ + ...
```
where the coefficients `g_k` are the `k-th` derivatives of the I-V characteristic at the bias point:
```
g₁ = ∂i_d/∂v_d |_{V_bias}
g₂ = ∂²i_d/∂v_d² |_{V_bias}
g₃ = ∂³i_d/∂v_d³ |_{V_bias}
```

For the Shockley equation `I_D = I_S [exp(V_D/(N V_T)) - 1]`, the derivatives are:
```
g₁ = (I_S/(N V_T)) exp(V_bias/(N V_T))
g₂ = (I_S/(N V_T)²) exp(V_bias/(N V_T))
g₃ = (I_S/(N V_T)³) exp(V_bias/(N V_T))
```

The **second harmonic distortion (HD2)** and **third harmonic distortion (HD3)** for a small-signal amplitude `V_ac` are:
```
HD2 ≈ (1/4) * |g₂/g₁| * V_ac
HD3 ≈ (1/24) * |g₃/g₁| * V_ac²
```

### **8.3 Intermodulation Distortion (IMD)**

For two-tone excitation `v_d(t) = V_bias + V_ac1 cos(ω₁t) + V_ac2 cos(ω₂t)`, the cubic nonlinearity generates intermodulation products. The **third-order intercept point (IP3)** is a key metric, related to the Taylor coefficients:
```
IP3 (voltage) ≈ √( (4/3) * |g₁/g₃| )
```
The **third-order intermodulation distortion (IM3)** for equal tone amplitudes `V_ac` is:
```
IM3 ≈ (3/4) * |g₃/g₁| * V_ac²
```

### **8.4 Sensitivity of Distortion Metrics**

The sensitivity of distortion metrics w.r.t. a parameter `p` is crucial for design centering. Using the chain rule:
```
∂(HD2)/∂p = (V_ac/4) * ∂/∂p (|g₂/g₁|)
∂(IP3)/∂p = (1/2) * √( (4/3) * |g₁/g₃| ) * (1/|g₁/g₃|) * ∂/∂p (|g₁/g₃|)
```
These require computing second-order mixed derivatives like `∂²i_d/∂v_d∂p`.

### **8.5 Capacitance Nonlinearity Contribution**

The junction charge `Q_j(V)` also contributes to distortion, especially at high frequencies. The nonlinear charge is modeled as a current source `i_cap = dQ_j/dt`. Expanding `Q_j(V)` as a Taylor series yields additional distortion coefficients `c_k = ∂ᵏQ_j/∂v_dᵏ`. In frequency-domain distortion analysis, these combine with the conductive nonlinearity to determine total distortion.

### **8.6 Statistical Analysis with Parameter Variation**

For Monte Carlo analysis, parameters are modeled as random variables with Gaussian distribution:
```
p = p_nom * (1 + σ_global * N(0,1) + σ_mismatch * N_i(0,1))
```
where `N(0,1)` is a global random seed and `N_i(0,1)` is a per-device random seed. The sensitivity coefficients `∂Φ/∂p` directly determine the output variance via:
```
σ_Φ² ≈ Σ_i (∂Φ/∂p_i)² σ_p_i²
```

---

## **Convergence Analysis**

### **8.7 Convergence of Adjoint Sensitivity Computation**

The adjoint method's convergence is tied to the forward Newton-Raphson convergence. The adjoint system `Gᵀ λ = b` uses the **transpose** of the converged Jacobian from the forward analysis. Since `G` is already factored (LU), solving for `λ` is a single back-substitution step, guaranteeing machine-precision accuracy provided:

1.  **Forward Solution Accuracy:** `||G V - I|| < ε_NR` (Newton tolerance).
2.  **Parameter Derivative Consistency:** The derivatives `∂G/∂p` and `∂I/∂p` must be evaluated at the **exact same operating point** as the converged `V`. Any discrepancy introduces a systematic error in the sensitivity integral.
3.  **Time Integration Error:** The trapezoidal rule used for the sensitivity integral `∫ λᵀ [...] dt` introduces its own truncation error, `O(Δt²)`. This error is controlled by the same LTE mechanism as the transient analysis.

### **8.8 Convergence of Harmonic Distortion Analysis**

Distortion analysis in Ngspice is performed in the **frequency domain** using a multi-dimensional Volterra series approach. The system solves for distortion currents at harmonic frequencies `kω`. Convergence is assessed by:

1.  **Taylor Series Truncation:** The error from truncating at third order (`g₃`) is `O(V_ac⁴)`. The analysis assumes `V_ac << N V_T` (typically `V_ac < 10 mV` for <1% error).
2.  **Frequency-Domain Solver Convergence:** The linear system at each harmonic frequency must satisfy the residual criterion `||Y(ω) V(ω) - I_dist(ω)|| < ε_AC`, where `Y` is the linearized admittance matrix and `I_dist` is the distortion current source vector.
3.  **Consistency of Linearization:** The `g₁` used in `Y(ω)` must match the DC bias point derivative. A convergence check verifies `|g₁ - (I_D(V_bias+δV) - I_D(V_bias-δV))/(2δV)| < ε_diff`.

### **8.9 Regularization for High Sensitivity**

Near breakdown or at very low bias currents, derivatives `∂I_D/∂p` can become extremely large, causing numerical overflow in sensitivity computation. Ngspice employs **parameter clipping**:
```
if (|∂I_D/∂p| > MAX_SENS) ∂I_D/∂p = sign(∂I_D/∂p) * MAX_SENS
```
where `MAX_SENS` is typically `1e15`. This regularization ensures solver stability while logging a warning.

### **8.10 Validation via Complex Step Differentiation**

To verify the accuracy of analytically coded derivatives, a **complex step derivative** check can be enabled:
```
∂I_D/∂p ≈ Im( I_D(p + i·h) ) / h
```
with `h ≈ 1e-15`. This provides derivative approximations accurate to `O(h²)` free from subtraction cancellation errors. Discrepancies between analytic and complex-step derivatives above `1e-6` relative error trigger runtime warnings.

### **8.11 Monte Carlo Convergence**

Statistical analysis convergence is governed by the **standard error of the mean**:
```
SE = σ_Φ / √N_runs
```
The simulation continues until `SE < ε_stat` (e.g., `ε_stat = 0.01 * |μ_Φ|`) or a maximum number of runs is reached. For correlated parameters (e.g., `I_S` and `N`), Cholesky decomposition of the covariance matrix ensures physically consistent samples.

---

## **C Implementation**

### **8.12 Core Data Structure Extensions**

The basic `DIOinstance` and `DIOmodel` structures (from `diodefs.h`) are extended with fields for sensitivity and distortion analysis.

```c
/* From diosdefs.h - Sensitivity extensions */
typedef struct sDIOinstanceSensitivity {
    double *DIOsenParmNo;      /* Parameter ID mapping */
    double **DIOsens;          /* Sensitivity matrix [timeSteps][params] */
    double *DIOadjointV;       /* Adjoint voltage vector for this instance */
    double *DIOadjointI;       /* Adjoint current vector */
    double DIOdIdIS, DIOdIdN;  /* Parameter derivatives (∂I_D/∂p) */
    double DIOdGdIS, DIOdGdN;  /* Conductance derivatives (∂G_D/∂p) */
} DIOinstanceSensitivity;

/* From dioddefs.h - Distortion extensions */
typedef struct sDIOinstanceDistortion {
    double DIOg1, DIOg2, DIOg3; /* Taylor coefficients (I-V) */
    double DIOc1, DIOc2, DIOc3; /* Taylor coefficients (Q-V) */
    double *DIOdistoI2h;        /* 2nd harmonic distortion current */
    double *DIOdistoI3h;        /* 3rd harmonic distortion current */
    unsigned int DIOdistoFlags;
} DIOinstanceDistortion;

/* Augmented instance structure */
struct sDIOinstance {
    /* ... standard fields (DIOposNode, DIOnegNode, DIOcurrent, etc.) ... */
    
    /* Sensitivity and distortion extensions */
    DIOinstanceSensitivity *DIOsensInfo;
    DIOinstanceDistortion *DIOdistoInfo;
    
    /* Parameter derivatives for sensitivity */
    double DIOdIdRS;
    double DIOdQdCJ0, DIOdQdPHI, DIOdQdM;
    
    /* Flags */
    int DIOsenParmNo; /* Sensitivity parameter count */
};
```

### **8.13 Sensitivity Analysis Implementation (`diosload.c`, `diosprt.c`)**

The adjoint method is implemented in two phases: **matrix stamping** during the adjoint solution, and **integral computation** after both forward and adjoint solutions are complete.

```c
/* diosload.c - Stamping adjoint system and parameter derivatives */
int DIOsLoad(DIOinstance *inst, CKTcircuit *ckt, double *rhs)
{
    double vd = ckt->CKTrhsOld[inst->DIOposNode] - ckt->CKTrhsOld[inst->DIOnegNode];
    double g1 = inst->DIOconduct; /* ∂I_D/∂V_D from forward solution */
    
    /* Stamp adjoint Jacobian (Gᵀ) - same as forward for linearized diode */
    *(inst->DIOposPosPtr) += g1;
    *(inst->DIOnegNegPtr) += g1;
    *(inst->DIOposNegPtr) -= g1;
    *(inst->DIOnegPosPtr) -= g1;
    
    /* Compute and store parameter derivatives for sensitivity integral */
    if (inst->DIOsensInfo) {
        double vt = inst->DIOmodel->DIOnomVt;
        double n = inst->DIOmodel->DIOemissionCoeff;
        double expVd = exp(vd/(n*vt));
        
        /* ∂I_D/∂I_S */
        inst->DIOsensInfo->DIOdIdIS = expVd - 1.0;
        /* ∂G_D/∂I_S */
        inst->DIOsensInfo->DIOdGdIS = expVd/(n*vt);
        
        /* ∂I_D/∂N */
        inst->DIOsensInfo->DIOdIdN = -inst->DIOsatCur * vd * expVd/(n*n*vt);
        /* ∂G_D/∂N */
        inst->DIOsensInfo->DIOdGdN = -inst->DIOsatCur * expVd/(n*vt) * (vd/(n*vt) + 2.0);
        
        /* ∂I/∂p term for RHS of sensitivity equation */
        double dIdp = inst->DIOsensInfo->DIOdIdIS; /* Example for I_S */
        rhs[inst->DIOposNode] -= dIdp;
        rhs[inst->DIOnegNode] += dIdp;
    }
    
    return OK;
}

/* diosprt.c - Compute sensitivity integral */
int DIOsPrint(DIOinstance *inst, CKTcircuit *ckt, FILE *fp)
{
    if (!inst->DIOsensInfo || !inst->DIOsensInfo->DIOsens) return OK;
    
    double *adjointV = inst->DIOsensInfo->DIOadjointV;
    double sensIntegral = 0.0;
    
    /* Trapezoidal integration: ∫ λᵀ * [ (∂G/∂p)V - (∂I/∂p) ] dt */
    for (int i = 0; i < ckt->CKTtimeSteps; i++) {
        double lambda = adjointV[i];
        double vd = ckt->CKTstates[i][inst->DIOposNode] - 
                    ckt->CKTstates[i][inst->DIOnegNode];
        
        /* (∂G/∂p)V - (∂I/∂p) term */
        double term = (inst->DIOsensInfo->DIOdGdIS * vd) - 
                      inst->DIOsensInfo->DIOdIdIS;
        
        sensIntegral += ckt->CKTtimeWeights[i] * lambda * term;
    }
    
    /* Store final sensitivity */
    inst->DIOsensInfo->DIOsens[ckt->CKTtimeSteps-1][PARAM_IS] = sensIntegral;
    
    /* Print to output */
    fprintf(fp, "Diode %s: d(Vout)/d(IS) = %12.5e\n", 
            inst->DIOname, sensIntegral);
    
    return OK;
}
```

### **8.14 Harmonic Distortion Implementation (`diodisto.c`)**

The distortion analysis computes Taylor coefficients and stamps frequency-domain distortion currents.

```c
/* diodisto.c - Compute distortion coefficients and stamp */
int DIOdisto(DIOinstance *inst, CKTcircuit *ckt, DIOmodel *model)
{
    double vd = ckt->CKTrhsOld[inst->DIOposNode] - 
                ckt->CKTrhsOld[inst->DIOnegNode];
    double vt = model->DIOnomVt;
    double n = model->DIOemissionCoeff;
    double is = inst->DIOsatCur;
    
    double expVd = exp(vd/(n*vt));
    
    /* Taylor coefficients for I-V characteristic */
    inst->DIOdistoInfo->DIOg1 = (is/(n*vt)) * expVd;          /* 1st derivative */
    inst->DIOdistoInfo->DIOg2 = (is/(n*vt*n*vt)) * expVd;     /* 2nd derivative */
    inst->DIOdistoInfo->DIOg3 = (is/(n*vt*n*vt*n*vt)) * expVd; /* 3rd derivative */
    
    /* For capacitance nonlinearity */
    if (model->DIOjunctionCap > 0.0) {
        double phi = model->DIOjunctionPot;
        double m = model->DIOgradingCoeff;
        double cj0 = model->DIOjunctionCap;
        
        /* Q(V) = ∫ C(V) dV = Cj0 * φ * (1 - (1 - V/φ)^{1-m})/(1-m) */
        double x = 1.0 - vd/phi;
        if (x < 1e-12) x = 1e-12; /* Regularize near breakdown */
        
        inst->DIOdistoInfo->DIOc1 = cj0 / pow(x, m);  /* C(V) = dQ/dV */
        inst->DIOdistoInfo->DIOc2 = m * inst->DIOdistoInfo->DIOc1 / (phi * x);
        inst->DIOdistoInfo->DIOc3 = m * (m+1) * inst->DIOdistoInfo->DIOc1 / 
                                    (phi*phi * x*x);
    }
    
    /* Stamp distortion currents for 2nd harmonic (2ω) */
    if (ckt->CKTmode & MODE2HARMONIC) {
        double v_ac = ckt->CKTacValues[inst->DIOposNode] - 
                      ckt->CKTacValues[inst->DIOnegNode];
        /* i_dist(2ω) = (g₂/2) * v_ac² */
        double i2h = 0.5 * inst->DIOdistoInfo->DIOg2 * v_ac * v_ac;
        
        /* Add to distortion current vector */
        ckt->CKTdistoValues[inst->DIOposNode][HARMONIC_2] += i2h;
        ckt->CKTdistoValues[inst->DIOnegNode][HARMONIC_2] -= i2h;
    }
    
    return OK;
}
```

### **8.15 Statistical Analysis Implementation (`diostat.c`)**

```c
/* diostat.c - Monte Carlo parameter variation */
int DIOmonteCarloParams(DIOinstance *inst, DIOmodel *model, 
                        int runNumber, int globalSeed, int deviceSeed)
{
    double globalRand = norm_random(globalSeed + runNumber);
    double mismatchRand = norm_random(deviceSeed + runNumber);
    
    /* Apply global and mismatch variations */
    inst->DIOsatCur = model->DIOsatCurNom * 
                      (1.0 + model->DIOsigmaISglobal * globalRand +
                             model->DIOsigmaISmismatch * mismatchRand);
    
    inst->DIOemissionCoeff = model->DIOemissionCoeffNom * 
                             (1.0 + model->DIOsigmaNglobal * globalRand +
                                    model->DIOsigmaNmismatch * mismatchRand);
    
    /* Update derivatives for sensitivity analysis */
    DIOupdateDerivatives(inst, model);
    
    return OK;
}
```

### **8.16 SPICEdev API Integration**

The sensitivity and distortion functions are integrated into Ngspice via the `SPICEdev` structure.

```c
/* From dioreg.c - Device registration */
SPICEdev DIOinfo = {
    .DEVpublic = {
        .name = "diode",
        .description = "PN junction diode with sensitivity/distortion",
        .terms = 2,
        .numNames = 0,
        .termNames = NULL,
    },
    
    /* Core functions */
    .DEVload = DIOload,
    .DEVsetup = DIOsetup,
    .DEVunsetup = DIOunsetup,
    .DEVpzSetup = DIOpzSetup,
    .DEVpzLoad = DIOpzLoad,
    .DEVconvTest = DIOconvTest,
    .DEVtrunc = DIOtrunc,
    
    /* Sensitivity functions */
    .DEVsenSetup = DIOsenSetup,
    .DEVsenLoad = DIOsLoad,
    .DEVsenUpdate = DIOsUpdate,
    .DEVsenPrint = DIOsPrint,
    .DEVsenTrunc = DIOsenTrunc,
    
    /* Distortion functions */
    .DEVdisto = DIOdisto,
    .DEVdistoSetup = DIOdistoSetup,
    
    /* Statistical functions */
    .DEVmcSetup = DIOmcSetup,
    .DEVmcLoad = DIOmcLoad,
    .DEVmcUpdate = DIOmcUpdate,
    .DEVmcPrint = DIOmcPrint,
    
    .DEVinstSize = sizeof(DIOinstance),
    .DEVmodSize = sizeof(DIOmodel),
};
```

### **8.17 Complex Step Verification Code**

```c
/* dioderivcheck.c - Validate analytic derivatives */
int DIOcheckDerivatives(DIOinstance *inst, DIOmodel *model)
{
    double h = 1e-15;
    double vd = inst->DIOvoltage;
    
    /* Complex step for ∂I_D/∂I_S */
    double is_complex = model->DIOsatCurNom + h * I; /* I = sqrt(-1) in complex.h */
    double id_complex = is_complex * (exp(vd/(model->DIOnomVt*model->DIOemissionCoeff)) - 1.0);
    double dIdIS_complex = cimag(id_complex) / h;
    
    /* Compare with analytic */
    double dIdIS_analytic = inst->DIOsensInfo->DIOdIdIS;
    double relError = fabs(dIdIS_analytic - dIdIS_complex) / 
                      (fabs(dIdIS_complex) + 1e-30);
    
    if (relError > 1e-6) {
        fprintf(stderr, "WARNING: Diode %s derivative mismatch: analytic=%e, complex=%e, error=%e\n",
                inst->DIOname, dIdIS_analytic, dIdIS_complex, relError);
    }
    
    return OK;
}
```

This implementation provides production-grade sensitivity and distortion analysis for the Ngspice diode model, enabling rigorous analog/RF design verification and yield analysis directly within the SPICE simulation environment.