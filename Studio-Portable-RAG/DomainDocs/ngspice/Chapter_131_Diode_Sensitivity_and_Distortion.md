# Diode: Sensitivity and Harmonic Distortion Analysis

_Generated 2026-04-12 20:16 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diodisto.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diodset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diosload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diosacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diosset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diosupd.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diosprt.c`

# Chapter: Diode: Sensitivity and Harmonic Distortion Analysis

## 1. Technical Introduction

This chapter details the Ngspice C implementation for advanced diode analysis, specifically focusing on sensitivity analysis and harmonic distortion prediction. The files `diodisto.c`, `diodset.c`, `diosload.c`, `diosacl.c`, `diosset.c`, `diosupd.c`, and `diosprt.c` collectively implement the mathematical frameworks for adjoint sensitivity computation and Volterra series-based distortion analysis within the SPICE simulation environment.

- **`diodisto.c`** implements harmonic distortion analysis using Volterra series expansion, computing second and third derivatives of the diode's I-V characteristic to predict harmonic and intermodulation distortion products.

- **`diodset.c`** handles distortion analysis setup, allocating memory for distortion matrices and initializing the Volterra kernel computation framework.

- **`diosload.c`** implements the core adjoint sensitivity method, loading the transposed Jacobian matrix and computing parameter derivatives for sensitivity integral evaluation.

- **`diosacl.c`** provides AC sensitivity analysis, computing frequency-dependent sensitivity coefficients for small-signal analysis.

- **`diosset.c`** performs sensitivity analysis setup, allocating extended data structures for storing parameter derivatives, adjoint variables, and sensitivity matrices.

- **`diosupd.c`** manages parameter updates during sensitivity analysis, handling parameter perturbations and recomputation of derivative information.

- **`diosprt.c`** computes and outputs sensitivity results, implementing trapezoidal integration of the sensitivity integral and formatting results for user consumption.

These files work together to translate the mathematical formulations of adjoint sensitivity analysis and Volterra series distortion prediction into numerically robust C implementations, fully integrated with Ngspice's Newton-Raphson solver, matrix manipulation routines, and convergence control systems.

## 2. Mathematical Formulation

### 2.1 Sensitivity Analysis via Adjoint Method

The sensitivity of circuit responses to diode parameters is computed using the discrete adjoint method, which efficiently calculates derivatives of objective functions with respect to multiple parameters. For a diode with parameters \( \mathbf{p} = [I_S, N, R_S, C_{j0}, \phi, m, BV, \tau_T] \), the sensitivity of an output function \( \Phi(\mathbf{x}, \mathbf{p}) \) is:

\[
\frac{\partial \Phi}{\partial p_i} = \int_0^T \lambda^T(t) \left[ \frac{\partial \mathbf{F}}{\partial p_i} - \frac{\partial \mathbf{J}}{\partial p_i} \mathbf{x}(t) \right] dt
\]

where:
- \( \mathbf{F}(\mathbf{x}, \mathbf{p}) = 0 \) represents the circuit equations
- \( \mathbf{J} = \partial \mathbf{F}/\partial \mathbf{x} \) is the Jacobian matrix
- \( \lambda(t) \) is the adjoint vector satisfying \( \mathbf{J}^T \lambda = \partial \Phi/\partial \mathbf{x} \)

For the diode's Shockley equation \( I_D = I_S[\exp(V_J/(N V_T)) - 1] \), the parameter derivatives are:

\[
\frac{\partial I_D}{\partial I_S} = \frac{I_D + I_S}{I_S}, \quad \frac{\partial I_D}{\partial N} = -\frac{I_D V_J}{N^2 V_T}
\]

\[
\frac{\partial I_D}{\partial R_S} = -g_d I_D, \quad \text{where } g_d = \frac{\partial I_D}{\partial V_D}
\]

The capacitance parameter derivatives for the depletion charge \( Q_j(V) = \frac{C_{j0} \phi}{1-m} \left[1 - (1 - V/\phi)^{1-m}\right] \) are:

\[
\frac{\partial Q_j}{\partial C_{j0}} = \frac{Q_j}{C_{j0}}, \quad \frac{\partial Q_j}{\partial \phi} = \frac{C_{j0}}{1-m} \left[1 - (1 - V/\phi)^{1-m} \left(1 + \frac{(1-m)V}{\phi}\right)\right]
\]

\[
\frac{\partial Q_j}{\partial m} = \frac{C_{j0} \phi}{(1-m)^2} \left[1 - (1 - V/\phi)^{1-m} \left(1 - (1-m)\ln(1 - V/\phi)\right)\right]
\]

### 2.2 Harmonic Distortion via Volterra Series

The diode's nonlinear I-V characteristic generates harmonic distortion when driven by sinusoidal signals. The Volterra series representation up to third order is:

\[
i_d(t) = \sum_{n=1}^3 \int_{-\infty}^\infty \cdots \int_{-\infty}^\infty h_n(\tau_1, \ldots, \tau_n) \prod_{j=1}^n v_d(t-\tau_j) d\tau_j
\]

where \( h_n \) are the Volterra kernels. For memoryless nonlinearities, this reduces to a Taylor series expansion around the DC operating point \( V_{D0} \):

\[
I_D(V_{D0} + v_d) = I_{D0} + g_d v_d + \frac{1}{2} g_{d2} v_d^2 + \frac{1}{6} g_{d3} v_d^3 + O(v_d^4)
\]

The derivatives for the Shockley equation are:

\[
g_d = \frac{I_S}{N V_T} \exp\left(\frac{V_{J0}}{N V_T}\right) = \frac{I_{D0} + I_S}{N V_T}
\]

\[
g_{d2} = \frac{g_d}{N V_T} = \frac{I_{D0} + I_S}{(N V_T)^2}
\]

\[
g_{d3} = \frac{g_{d2}}{N V_T} = \frac{I_{D0} + I_S}{(N V_T)^3}
\]

For the breakdown region with multiplication factor \( M(V_D) = 1/[1 - (V_D/BV)^m] \), the derivatives become:

\[
g_d^{\text{br}} = \frac{I_S}{N_{bv} V_T} \exp\left(\frac{-V_D - BV}{N_{bv} V_T}\right) M(V_D) + I_{br} \frac{m V_D^{m-1}}{BV^m - V_D^m}
\]

\[
g_{d2}^{\text{br}} = \frac{g_d^{\text{br}}}{N_{bv} V_T} + I_{br} \frac{m(m-1)V_D^{m-2}}{BV^m - V_D^m} + I_{br} \left(\frac{m V_D^{m-1}}{BV^m - V_D^m}\right)^2
\]

### 2.3 Intermodulation Distortion Analysis

For two-tone excitation \( v_d(t) = A_1 \cos(\omega_1 t) + A_2 \cos(\omega_2 t) \), the third-order intermodulation products at frequencies \( 2\omega_1 - \omega_2 \) and \( 2\omega_2 - \omega_1 \) have amplitudes:

\[
\text{IM3} = \frac{3}{4} \frac{g_{d3}}{g_d} A_1^2 A_2
\]

The third-order intercept point (IP3) is:

\[
\text{IP3} = \sqrt{\frac{4}{3} \left|\frac{g_d}{g_{d3}}\right|}
\]

For the diode's exponential characteristic, this becomes:

\[
\text{IP3}_{\text{diode}} = \sqrt{\frac{4}{3}} N V_T \approx 1.15 N V_T
\]

At room temperature with \( N = 1 \), \( \text{IP3} \approx 29.7 \text{mV} \).

### 2.4 Sensitivity of Distortion to Parameter Variations

The sensitivity of harmonic distortion to diode parameters is crucial for yield analysis. The derivative of HD2 with respect to saturation current is:

\[
\frac{\partial \text{HD2}}{\partial I_S} = \frac{1}{4} \frac{A^2}{N V_T (I_{D0} + I_S)} \left(1 - \frac{I_{D0}}{I_{D0} + I_S}\right)
\]

where \( A \) is the signal amplitude. For HD3:

\[
\frac{\partial \text{HD3}}{\partial I_S} = \frac{1}{24} \frac{A^3}{(N V_T)^2 (I_{D0} + I_S)^2} \left(2I_{D0} + I_S\right)
\]

The sensitivity to emission coefficient \( N \) is:

\[
\frac{\partial \text{HD2}}{\partial N} = -\frac{\text{HD2}}{N}, \quad \frac{\partial \text{HD3}}{\partial N} = -\frac{2\text{HD3}}{N}
\]

### 2.5 Capacitance Nonlinearity Contribution

The voltage-dependent junction capacitance contributes additional distortion. The charge nonlinearity up to third order is:

\[
Q_j(V) = Q_{j0} + C_{j0} v + \frac{1}{2} C_{j1} v^2 + \frac{1}{6} C_{j2} v^3
\]

where for \( V < FC \cdot \phi \):

\[
C_{j1} = \frac{m C_{j0}}{\phi (1 - V_0/\phi)}, \quad C_{j2} = \frac{m(m+1) C_{j0}}{\phi^2 (1 - V_0/\phi)^2}
\]

The displacement current distortion is frequency-dependent:

\[
I_{\text{cap}}(\omega) = j\omega Q(V) = j\omega \left[ C_{j0} v + \frac{1}{2} C_{j1} v^2 + \frac{1}{6} C_{j2} v^3 \right]
\]

The total distortion current is the sum of conductive and capacitive contributions:

\[
I_{\text{total}} = (g_d + j\omega C_{j0}) v + \frac{1}{2} (g_{d2} + j\omega C_{j1}) v^2 + \frac{1}{6} (g_{d3} + j\omega C_{j2}) v^3
\]

### 2.6 Statistical Distortion Analysis

For Monte Carlo analysis with parameter variations \( \delta p_i \sim N(0, \sigma_i^2) \), the statistical variation of HD2 is:

\[
\sigma_{\text{HD2}}^2 = \sum_i \left( \frac{\partial \text{HD2}}{\partial p_i} \right)^2 \sigma_i^2 + \sum_{i \neq j} \frac{\partial \text{HD2}}{\partial p_i} \frac{\partial \text{HD2}}{\partial p_j} \rho_{ij} \sigma_i \sigma_j
\]

where \( \rho_{ij} \) are correlation coefficients between parameters. The correlation matrix for diode parameters typically shows strong correlation between \( I_S \) and \( C_{j0} \) (both area-dependent), and between \( N \) and \( \phi \) (both material-dependent).

## 3. Convergence Analysis

### 3.1 Newton-Raphson Convergence for Sensitivity Analysis

The adjoint sensitivity method requires solving both the original system \( \mathbf{Jx} = \mathbf{b} \) and the adjoint system \( \mathbf{J}^T \lambda = \mathbf{c} \). The convergence of the adjoint solution depends on the condition number of \( \mathbf{J} \):

\[
\kappa(\mathbf{J}) = \frac{\sigma_{\max}(\mathbf{J})}{\sigma_{\min}(\mathbf{J})}
\]

For diodes in forward bias, \( \kappa(\mathbf{J}) \) can exceed \( 10^{12} \) due to the exponential I-V characteristic. The convergence criterion for the adjoint system is:

\[
\| \mathbf{J}^T \lambda^{(k)} - \mathbf{c} \| < \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \| \mathbf{c} \|
\]

with \( \epsilon_{\text{abs}} = 10^{-12} \) and \( \epsilon_{\text{rel}} = 10^{-6} \) for sensitivity analysis (tighter than normal DC analysis).

The parameter derivative calculation requires accurate computation of \( \partial \mathbf{J}/\partial p_i \), which for the diode involves second derivatives of the I-V characteristic:

\[
\frac{\partial^2 I_D}{\partial V_D \partial I_S} = \frac{g_d}{I_S}, \quad \frac{\partial^2 I_D}{\partial V_D \partial N} = -\frac{g_d V_J}{N^2 V_T} \left(1 + \frac{V_J}{N V_T}\right)
\]

These mixed partial derivatives must be computed with relative error less than \( 10^{-8} \) to maintain overall sensitivity accuracy.

### 3.2 Harmonic Balance Convergence

For harmonic distortion analysis using harmonic balance, the system solves for Fourier coefficients \( \mathbf{X}_k \) satisfying:

\[
\mathbf{F}_k(\mathbf{X}_0, \mathbf{X}_1, \ldots, \mathbf{X}_K) = 0, \quad k = 0, \ldots, K
\]

where \( K \) is the highest harmonic considered. The convergence test for harmonic balance includes both magnitude and phase criteria:

\[
|X_k^{(n+1)} - X_k^{(n)}| < \epsilon_{\text{abs}} + \epsilon_{\text{rel}} |X_k^{(n+1)}|, \quad \text{for all } k
\]

\[
|\angle X_k^{(n+1)} - \angle X_k^{(n)}| < \epsilon_{\text{phase}}, \quad \text{typically } 10^{-3} \text{ radians}
\]

For diode distortion analysis, the convergence rate depends on the excitation amplitude \( A \) relative to \( N V_T \). The contraction factor for Newton-Raphson in harmonic balance is:

\[
\rho = \max_k \left| 1 - \frac{\partial \mathbf{F}_k/\partial X_k}{J_{kk}} \right|
\]

where \( J_{kk} \) are the diagonal blocks of the harmonic Jacobian. For small signals (\( A \ll N V_T \)), \( \rho \approx 0.1 \), providing fast convergence. For large signals (\( A > N V_T \)), \( \rho \) can approach 1, requiring damping.

### 3.3 Intermodulation Convergence

For two-tone analysis, the convergence of intermodulation products requires special handling due to the closely spaced frequencies \( \omega_1 \) and \( \omega_2 \). The frequency grid must satisfy:

\[
\Delta \omega = \gcd(\omega_1, \omega_2, |\omega_1 - \omega_2|, 2\omega_1 - \omega_2, 2\omega_2 - \omega_1)
\]

The time window for discrete Fourier transform must be:

\[
T = \frac{2\pi}{\Delta \omega} \times N_{\text{cycles}}, \quad \text{with } N_{\text{cycles}} \geq 10
\]

to properly resolve all intermodulation products. The convergence criterion for IM3 components is tighter than for fundamentals:

\[
\epsilon_{\text{IM3}} = 0.1 \times \epsilon_{\text{fundamental}}
\]

### 3.4 Numerical Differentiation for Derivative Computation

The second and third derivatives required for distortion analysis are computed using complex step differentiation for accuracy:

\[
g_{d2} = \frac{\text{Im}[I_D(V_D + jh)]}{h^2} + O(h^2)
\]

\[
g_{d3} = \frac{\text{Re}[I_D(V_D + jh) - I_D(V_D)]}{h^3} + O(h^2)
\]

with \( h = 10^{-8} \). This avoids the subtractive cancellation errors of finite differences. The error in derivative computation propagates to distortion estimates as:

\[
\frac{\Delta \text{HD2}}{\text{HD2}} \approx 2 \frac{\Delta g_{d2}}{g_{d2}}, \quad \frac{\Delta \text{HD3}}{\text{HD3}} \approx 3 \frac{\Delta g_{d3}}{g_{d3}}
\]

Requiring \( \Delta g_{d2}/g_{d2} < 10^{-4} \) for 0.1% accuracy in HD2.

### 3.5 Regularization for Ill-Conditioned Sensitivity Systems

Near breakdown or at very low currents, the sensitivity equations become ill-conditioned. Tikhonov regularization is applied:

\[
(\mathbf{J}^T \mathbf{J} + \mu \mathbf{I}) \frac{\partial \mathbf{x}}{\partial p_i} = \mathbf{J}^T \frac{\partial \mathbf{F}}{\partial p_i}
\]

with \( \mu = 10^{-8} \max(\text{diag}(\mathbf{J}^T \mathbf{J})) \). The regularization error is:

\[
\epsilon_{\text{reg}} = \mu \left\| \frac{\partial \mathbf{x}}{\partial p_i} \right\|
\]

which is monitored to ensure \( \epsilon_{\text{reg}} < 0.01 \epsilon_{\text{sensitivity}} \).

### 3.6 Convergence of Statistical Moments

For statistical distortion analysis, the convergence of moments is monitored. The standard error of the mean for HD2 after \( N \) samples is:

\[
\sigma_{\overline{\text{HD2}}} = \frac{\sigma_{\text{HD2}}}{\sqrt{N}}
\]

The simulation continues until:

\[
\sigma_{\overline{\text{HD2}}} < \epsilon_{\text{rel}} |\overline{\text{HD2}}| + \epsilon_{\text{abs}}
\]

with \( \epsilon_{\text{rel}} = 0.01 \) and \( \epsilon_{\text{abs}} = 0.1 \text{dB} \). The convergence of the full distribution is tested using the Kolmogorov-Smirnov statistic:

\[
D_N = \sup_x |F_N(x) - F(x)|
\]

where \( F_N \) is the empirical CDF and \( F \) is the estimated theoretical CDF. The simulation stops when \( D_N < 0.05 \).

### 3.7 Frequency-Dependent Convergence

For distortion analysis across frequency, the convergence criteria are frequency-weighted. Lower frequencies require tighter convergence due to larger capacitive effects:

\[
\epsilon(\omega) = \epsilon_{\text{DC}} \times \max\left(1, \frac{\omega_{\text{ref}}}{\omega}\right)
\]

with \( \omega_{\text{ref}} = 2\pi \times 1\text{kHz} \). This ensures accurate modeling of low-frequency distortion where \( 1/f \) noise and diffusion capacitance dominate.

### 3.8 Validation of Sensitivity Results

Sensitivity results are validated using finite differences:

\[
S_{\text{FD}} = \frac{\Phi(p_i + \Delta p_i) - \Phi(p_i - \Delta p_i)}{2\Delta p_i}
\]

The relative error must satisfy:

\[
\frac{|S_{\text{adjoint}} - S_{\text{FD}}|}{|S_{\text{FD}}|} < 10^{-4}
\]

for \( \Delta p_i = 0.01 p_i \). Additionally, the adjoint method's consistency is checked via the gradient identity:

\[
\lambda^T \mathbf{J} \mathbf{x} = \frac{\partial \Phi}{\partial \mathbf{x}} \mathbf{x}
\]

which should hold to within \( 10^{-10} \).

### 3.9 Distortion Convergence with Temperature

Temperature variations affect distortion through \( V_T(T) = kT/q \) and parameter temperature coefficients. The convergence test includes temperature derivatives:

\[
\left| \frac{\partial \text{HD2}}{\partial T} \Delta T \right| < \epsilon_{\text{HD2}}
\]

For a temperature sweep with step \( \Delta T \), this ensures smooth variation of distortion with temperature. The temperature derivative is:

\[
\frac{\partial \text{HD2}}{\partial T} = \text{HD2} \times \left( -\frac{1}{T} + \frac{1}{I_{D0} + I_S} \frac{\partial I_{D0}}{\partial T} \right)
\]

### 3.10 Multi-Diode Circuit Convergence

For circuits with multiple diodes, the convergence of cross-sensitivities \( \partial \Phi/\partial p_i^{(j)} \) where \( p_i^{(j)} \) is parameter \( i \) of diode \( j \), requires block matrix methods. The convergence criterion for the full sensitivity matrix \( \mathbf{S} \) is:

\[
\| \mathbf{S}^{(n+1)} - \mathbf{S}^{(n)} \|_F < \epsilon \| \mathbf{S}^{(n)} \|_F
\]

where \( \| \cdot \|_F \) is the Frobenius norm and \( \epsilon = 10^{-6} \). The harmonic distortion in multi-diode circuits involves intermodulation between diodes, requiring coupled harmonic balance with convergence tested for all diode currents simultaneously.

## 4. C Implementation

### 4.1 Core Data Structures for Sensitivity Analysis

The diode sensitivity implementation extends the basic diode structures with additional fields for storing parameter derivatives and adjoint system information:

```c
/* Extended diode instance structure for sensitivity analysis */
typedef struct sDIOinstance {
    /* Basic diode parameters (from previous implementation) */
    int DIOposNode, DIOnegNode;
    double DIOis, DIOn, DIOrs, DIOcjo, DIOphi, DIOm, DIObv, DIOibv;
    double DIOvoltage, DIOcurrent, DIOconduct;
    
    /* Sensitivity analysis fields */
    int DIOsenParmNo;               /* Number of sensitivity parameters */
    double *DIOsens;                /* Sensitivity values ∂Vout/∂p */
    double **DIOdIdP;               /* ∂I_D/∂p matrix [num_params × num_steps] */
    double **DIOdVdP;               /* ∂V_D/∂p matrix */
    
    /* Adjoint system storage */
    double *DIOadjointCurrent;      /* λ_I(t) - adjoint current */
    double *DIOadjointVoltage;      /* λ_V(t) - adjoint voltage */
    
    /* Matrix pointers for adjoint system */
    double *DIOadjPosPosPtr;        /* Adjoint system G_aa */
    double *DIOadjPosNegPtr;        /* Adjoint system G_ac */
    double *DIOadjNegPosPtr;        /* Adjoint system G_ca */
    double *DIOadjNegNegPtr;        /* Adjoint system G_cc */
    
    /* Harmonic distortion fields */
    double DIOgm2;                  /* ∂²I_D/∂V_D² - second derivative */
    double DIOgm3;                  /* ∂³I_D/∂V_D³ - third derivative */
    double DIOhd2;                  /* Second harmonic distortion */
    double DIOhd3;                  /* Third harmonic distortion */
    double DIOimd2;                 /* Second-order intermodulation */
    double DIOimd3;                 /* Third-order intermodulation */
    
    struct sDIOinstance *DIOnextInstance;
} DIOinstance;

/* Extended model structure with sensitivity parameters */
typedef struct sDIOmodel {
    /* Basic model parameters */
    double DIOtnom;                 /* Nominal temperature */
    double DIOxti;                  /* IS temperature exponent */
    double DIOeg;                   /* Energy gap */
    
    /* Sensitivity parameter variations */
    double DIOsigmaIS;              /* Standard deviation for IS */
    double DIOsigmaN;               /* Standard deviation for N */
    double DIOsigmaBV;              /* Standard deviation for BV */
    double DIOsigmaCJO;             /* Standard deviation for CJO */
    
    /* Correlation matrix for Monte Carlo */
    double **DIOcorrMatrix;         /* Parameter correlation matrix */
    double **DIOcholFactor;         /* Cholesky factor for correlated sampling */
    
    struct sDIOmodel *DIOnextModel;
    DIOinstance *DIOinstances;
} DIOmodel;
```

### 4.2 Sensitivity Analysis Implementation

#### 4.2.1 Adjoint Method Implementation

The sensitivity analysis uses the adjoint method, implemented in `diosload.c`:

```c
/* diosload.c - Diode sensitivity loading using adjoint method */
int DIOsLoad(DIOmodel *model, CKTcircuit *ckt) {
    DIOinstance *inst;
    double vd, id, gd, vt;
    double dIdIS, dIdN, dIdBV, dIdCJO;
    
    vt = CONSTKoverQ * ckt->CKTtemp;
    
    for (inst = model->DIOinstances; inst != NULL; inst = inst->DIOnextInstance) {
        /* Get operating point */
        vd = *(ckt->CKTrhs + inst->DIOposNode) - *(ckt->CKTrhs + inst->DIOnegNode);
        id = inst->DIOcurrent;
        gd = inst->DIOconduct;
        
        /* Compute parameter derivatives ∂I_D/∂p */
        if (vd < -3.0 * vt * inst->DIOn) {
            /* Reverse bias region */
            if (vd < -inst->DIObv) {
                /* Breakdown region derivatives */
                double exp_arg = -(vd + inst->DIObv) / (inst->DIOnbv * vt);
                dIdIS = 0.0;  /* IS doesn't affect breakdown current */
                dIdN = 0.0;   /* N doesn't affect breakdown current */
                dIdBV = inst->DIOibv * exp_arg * exp(exp_arg) / (inst->DIOnbv * vt);
                dIdCJO = 0.0; /* CJO doesn't affect DC current */
            } else {
                /* Normal reverse bias */
                dIdIS = -1.0;  /* I_D = -I_S in reverse */
                dIdN = 0.0;
                dIdBV = 0.0;
                dIdCJO = 0.0;
            }
        } else {
            /* Forward bias - Shockley equation derivatives */
            double exp_arg = vd / (inst->DIOn * vt);
            double exp_val = exp(exp_arg);
            
            dIdIS = exp_val - 1.0;                    /* ∂I_D/∂I_S */
            dIdN = -inst->DIOis * vd * exp_val / (inst->DIOn * inst->DIOn * vt); /* ∂I_D/∂N */
            dIdBV = 0.0;                              /* BV doesn't affect forward current */
            dIdCJO = 0.0;                             /* CJO doesn't affect DC current */
        }
        
        /* Store derivatives for sensitivity integral */
        inst->DIOdIdP[0][ckt->CKTstep] = dIdIS;   /* Index 0 = IS */
        inst->DIOdIdP[1][ckt->CKTstep] = dIdN;    /* Index 1 = N */
        inst->DIOdIdP[2][ckt->CKTstep] = dIdBV;   /* Index 2 = BV */
        inst->DIOdIdP[3][ckt->CKTstep] = dIdCJO;  /* Index 3 = CJO */
        
        /* Load transposed Jacobian for adjoint system: Gᵀ */
        *(inst->DIOadjPosPosPtr) += gd;
        *(inst->DIOadjPosNegPtr) += -gd;
        *(inst->DIOadjNegPosPtr) += -gd;
        *(inst->DIOadjNegNegPtr) += gd;
        
        /* For capacitance sensitivity, add capacitive terms */
        if (ckt->CKTmode & MODETRAN) {
            double cj = diode_capacitance(inst, vd);
            double gcap = cj / ckt->CKTdelta;
            *(inst->DIOadjPosPosPtr) += gcap;
            *(inst->DIOadjPosNegPtr) += -gcap;
            *(inst->DIOadjNegPosPtr) += -gcap;
            *(inst->DIOadjNegNegPtr) += gcap;
        }
    }
    
    return OK;
}
```

This implements the adjoint method formulation:
- Lines 31-53: Compute parameter derivatives ∂I_D/∂p
- Lines 56-59: Store derivatives for the sensitivity integral
- Lines 62-71: Load transposed Jacobian Gᵀ for the adjoint system λᵀ·G = ∂f/∂V_out

#### 4.2.2 Sensitivity Integral Computation

The sensitivity integral is computed in `diosprt.c` using trapezoidal integration:

```c
/* diosprt.c - Sensitivity integral computation and output */
void DIOsPrint(DIOmodel *model, CKTcircuit *ckt) {
    DIOinstance *inst;
    double integral, delta_t;
    int i, step;
    
    for (inst = model->DIOinstances; inst != NULL; inst = inst->DIOnextInstance) {
        for (i = 0; i < inst->DIOsenParmNo; i++) {
            integral = 0.0;
            
            /* Compute sensitivity integral: ∂Φ/∂p = ∫₀ᵀ λᵀ·(∂F/∂p) dt */
            for (step = 0; step < ckt->CKTnumSteps; step++) {
                delta_t = ckt->CKTdelta[step];
                
                /* Get adjoint variables at this time step */
                double lambda_I = inst->DIOadjointCurrent[step];
                double lambda_V = inst->DIOadjointVoltage[step];
                
                /* Get parameter derivative at this time step */
                double dFdp = inst->DIOdIdP[i][step];
                
                /* Trapezoidal integration */
                if (step == 0) {
                    integral += 0.5 * delta_t * (lambda_I * dFdp);
                } else if (step == ckt->CKTnumSteps - 1) {
                    integral += 0.5 * delta_t * (lambda_I * dFdp);
                } else {
                    integral += delta_t * (lambda_I * dFdp);
                }
            }
            
            /* Store computed sensitivity */
            inst->DIOsens[i] = integral;
            
            /* Normalize by parameter value for relative sensitivity */
            double rel_sens = integral / diode_parameter_value(inst, i);
            printf("Diode %s: ∂Vout/∂p%d = %.3e (rel: %.3e)\n",
                   inst->DIOname, i, integral, rel_sens);
        }
    }
}
```

This implements the discrete adjoint sensitivity integral:
- Line 17: ∂Φ/∂p = ∫₀ᵀ λᵀ·(∂F/∂p) dt
- Lines 24-35: Trapezoidal integration with second-order accuracy
- Line 41: Relative sensitivity normalization S_rel = (∂Vout/∂p) / p

### 4.3 Harmonic Distortion Implementation

#### 4.3.1 Higher-Order Derivative Computation

The harmonic distortion analysis in `diodisto.c` computes second and third derivatives of the diode I-V characteristic:

```c
/* diodisto.c - Diode harmonic distortion analysis */
void DIOdisto(int mode, DIOmodel *model, CKTcircuit *ckt, DKTdisto *disto) {
    DIOinstance *inst;
    double vd, id, gd, vt, n;
    double gm2, gm3;  /* Second and third derivatives */
    
    vt = CONSTKoverQ * ckt->CKTtemp;
    
    for (inst = model->DIOinstances; inst != NULL; inst = inst->DIOnextInstance) {
        vd = inst->DIOvoltage;
        id = inst->DIOcurrent;
        gd = inst->DIOconduct;
        n = inst->DIOn;
        
        /* Compute higher-order derivatives */
        if (vd < -3.0 * vt * n) {
            /* Reverse bias - derivatives are small */
            gm2 = 0.0;
            gm3 = 0.0;
        } else {
            /* Forward bias - exponential derivatives */
            double exp_arg = vd / (n * vt);
            double exp_val = exp(exp_arg);
            
            /* First derivative already computed: gd = (I_S/(n·V_T))·exp(V_D/(n·V_T)) */
            gd = inst->DIOis * exp_val / (n * vt);
            
            /* Second derivative: ∂²I_D/∂V_D² = gd/(n·V_T) */
            gm2 = gd / (n * vt);
            
            /* Third derivative: ∂³I_D/∂V_D³ = gm2/(n·V_T) */
            gm3 = gm2 / (n * vt);
        }
        
        /* Store for distortion computation */
        inst->DIOgm2 = gm2;
        inst->DIOgm3 = gm3;
        
        /* Compute harmonic distortion products */
        if (mode == D_COMPUTE) {
            double A = disto->DKTinputAmp;  /* Input amplitude */
            
            /* Second harmonic distortion: HD2 = (1/4)·(g2/g1)·A */
            inst->DIOhd2 = 0.25 * (gm2 / gd) * A;
            
            /* Third harmonic distortion: HD3 = (1/24)·(g3/g1)·A² */
            inst->DIOhd3 = (1.0/24.0) * (gm3 / gd) * A * A;
            
            /* Second-order intermodulation: IMD2 = (1/2)·(g2/g1)·A */
            inst->DIOimd2 = 0.5 * (gm2 / gd) * A;
            
            /* Third-order intermodulation: IMD3 = (3/8)·(g3/g1)·A² */
            inst->DIOimd3 = 0.375 * (gm3 / gd) * A * A;
            
            /* Convert to dB */
            disto->DKThd2 = 20.0 * log10(fabs(inst->DIOhd2));
            disto->DKThd3 = 20.0 * log10(fabs(inst->DIOhd3));
            disto->DKTimd2 = 20.0 * log10(fabs(inst->DIOimd2));
            disto->DKTimd3 = 20.0 * log10(fabs(inst->DIOimd3));
        }
    }
}
```

This implements the Volterra series formulation:
- Lines 28-33: Compute derivatives: g₁ = ∂I/∂V, g₂ = ∂²I/∂V², g₃ = ∂³I/∂V³
- Lines 40-43: Second harmonic: HD2 = (1/4)·(g₂/g₁)·A
- Lines 44-47: Third harmonic: HD3 = (1/24)·(g₃/g₁)·A²
- Lines 49-52: Intermodulation products

#### 4.3.2 Volterra Kernel Computation

For multi-tone analysis, the diode distortion uses Volterra kernels:

```c
/* Volterra kernel computation for diode */
void DIOvolterraKernels(DIOinstance *inst, double f1, double f2, double f3,
                        double *H2, double *H3) {
    double g1 = inst->DIOconduct;
    double g2 = inst->DIOgm2;
    double g3 = inst->DIOgm3;
    
    /* Second-order Volterra kernel */
    *H2 = 0.5 * g2 / (g1 * g1);
    
    /* Third-order Volterra kernel */
    *H3 = (1.0/6.0) * g3 / (g1 * g1 * g1);
    
    /* Frequency-dependent terms for reactive components */
    if (inst->DIOtt > 0.0) {  /* Has transit time */
        double w1 = 2.0 * M_PI * f1;
        double w2 = 2.0 * M_PI * f2;
        double w3 = 2.0 * M_PI * f3;
        
        /* Diffusion capacitance affects high-frequency distortion */
        double tau = inst->DIOtt;
        *H2 *= 1.0 / (1.0 + w1 * tau * 1j);
        *H3 *= 1.0 / ((1.0 + w1 * tau * 1j) * (1.0 + w2 * tau * 1j));
    }
}
```

### 4.4 Statistical Sensitivity Analysis

#### 4.4.1 Monte Carlo Sensitivity Computation

For statistical analysis, the sensitivity computation incorporates parameter variations:

```c
/* diostat.c - Statistical sensitivity analysis */
void DIOstatSensitivity(DIO