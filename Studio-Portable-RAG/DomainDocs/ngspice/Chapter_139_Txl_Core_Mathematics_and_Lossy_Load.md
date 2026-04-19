# Lossy Transmission Line: Convolution Math and DC Load

_Generated 2026-04-12 21:23 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txldefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlfbr.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlload.c`

# Chapter: Lossy Transmission Line: Convolution Math and DC Load

## Technical Introduction

The Ngspice lossy transmission line model implements a sophisticated, frequency-aware simulation component critical for high-speed digital, RF, and microwave circuit analysis. The four core files—`txldefs.h`, `txlparam.c`, `txlfbr.c`, and `txlload.c`—form the computational backbone of this model. `txldefs.h` defines the fundamental data structures (`sTXLinstance`, `sTXLmodel`) that encapsulate the line's electrical parameters, convolution history buffers, and sparse matrix pointers required for Modified Nodal Analysis (MNA) integration. `txlparam.c` processes user inputs, performing essential calculations such as deriving per-unit-length parameters from lumped values, applying temperature scaling, and computing the frequency-dependent characteristic impedance \(Z_0(\omega)\) and propagation constant \(\gamma(\omega)\). `txlfbr.c` (Frequency-Basis Response) is the algorithmic heart, responsible for generating the impulse or step response via methods like Vector Fitting or direct Inverse Fast Fourier Transform (IFFT), translating the continuous frequency-domain telegrapher's equations into a discrete-time model suitable for convolution. Finally, `txlload.c` executes the core simulation loop: it stamps the conductance matrix for DC analysis, performs the real-time convolution sums for transient analysis using the pre-computed impulse responses, and updates the history buffers. Together, these files bridge the gap between the mathematical ideal of a distributed, lossy transmission line and a numerically stable, efficient implementation within the SPICE simulation kernel, handling everything from DC operating point calculation to full transient analysis with frequency-dependent losses.

## Mathematical Formulation

The lossy transmission line model in Ngspice implements a frequency-dependent convolution-based approach for transient analysis, coupled with a simplified resistive model for DC operating point calculation. The formulation bridges the telegrapher's equations with SPICE's Modified Nodal Analysis (MNA) framework.

### 1. Telegrapher's Equations for Lossy Lines

The fundamental partial differential equations governing voltage and current propagation along a lossy transmission line are:

\[
\frac{\partial v(x,t)}{\partial x} = -R'i(x,t) - L'\frac{\partial i(x,t)}{\partial t}
\]
\[
\frac{\partial i(x,t)}{\partial x} = -G'v(x,t) - C'\frac{\partial v(x,t)}{\partial t}
\]

where:
- \( R' \) = resistance per unit length (Ω/m)
- \( L' \) = inductance per unit length (H/m)
- \( G' \) = conductance per unit length (S/m)
- \( C' \) = capacitance per unit length (F/m)
- \( x \) = position along the line
- \( t \) = time

### 2. Frequency-Domain Solution and Characteristic Impedance

Transforming to the frequency domain (\( s = j\omega \)) yields:

\[
\frac{d^2V(x,s)}{dx^2} = \gamma^2(s)V(x,s)
\]
\[
\frac{d^2I(x,s)}{dx^2} = \gamma^2(s)I(x,s)
\]

where the propagation constant \( \gamma(s) \) is:

\[
\gamma(s) = \sqrt{(R' + sL')(G' + sC')} = \alpha(s) + j\beta(s)
\]

The characteristic impedance, which varies with frequency for lossy lines, is:

\[
Z_0(s) = \sqrt{\frac{R' + sL'}{G' + sC'}}
\]

### 3. Convolution-Based Time-Domain Implementation

For transient analysis, Ngspice employs a convolution approach. The frequency-domain ABCD matrix for a line of length \( \ell \) is:

\[
\begin{bmatrix}
V_1(s) \\
I_1(s)
\end{bmatrix}
=
\begin{bmatrix}
\cosh(\gamma\ell) & Z_0(s)\sinh(\gamma\ell) \\
\frac{\sinh(\gamma\ell)}{Z_0(s)} & \cosh(\gamma\ell)
\end{bmatrix}
\begin{bmatrix}
V_2(s) \\
I_2(s)
\end{bmatrix}
\]

The time-domain relationship requires inverse Laplace transforms:

\[
v_1(t) = z_{11}(t) * v_2(t) + z_{12}(t) * i_2(t)
\]
\[
i_1(t) = z_{21}(t) * v_2(t) + z_{22}(t) * i_2(t)
\]

where \( * \) denotes convolution and \( z_{ij}(t) \) are the impulse responses corresponding to the frequency-domain ABCD parameters.

### 4. Discrete Convolution for SPICE Simulation

For numerical implementation, the continuous convolution is discretized using a finite impulse response (FIR) approach:

\[
v_1[n] = \sum_{k=0}^{M-1} h_{11}[k] v_2[n-k] + \sum_{k=0}^{M-1} h_{12}[k] i_2[n-k]
\]
\[
i_1[n] = \sum_{k=0}^{M-1} h_{21}[k] v_2[n-k] + \sum_{k=0}^{M-1} h_{22}[k] i_2[n-k]
\]

where:
- \( n \) = discrete time index
- \( M \) = number of taps in the impulse response
- \( h_{ij}[k] \) = discretized impulse response coefficients

The impulse responses are pre-computed via inverse FFT of the frequency-domain ABCD parameters sampled at logarithmically spaced frequencies.

### 5. DC Load Model (Special Case)

For DC analysis (\( s = 0 \)), the transmission line simplifies to a resistive network:

\[
Z_0(0) = \sqrt{\frac{R'}{G'}} \quad \text{(real)}
\]
\[
\gamma(0) = \sqrt{R'G'} \quad \text{(real)}
\]

The DC resistance matrix for a line of length \( \ell \) is:

\[
\begin{bmatrix}
V_1 \\
V_2
\end{bmatrix}
=
\begin{bmatrix}
R_{11} & R_{12} \\
R_{21} & R_{22}
\end{bmatrix}
\begin{bmatrix}
I_1 \\
I_2
\end{bmatrix}
\]

where:
\[
R_{11} = R_{22} = Z_0(0) \coth(\gamma(0)\ell)
\]
\[
R_{12} = R_{21} = -Z_0(0) \operatorname{csch}(\gamma(0)\ell)
\]

### 6. MNA Matrix Stamping for DC Analysis

For SPICE's Modified Nodal Analysis, the DC model stamps a conductance matrix. For the two-port transmission line with nodes 1, 2 (port 1) and 3, 4 (port 2):

\[
\begin{bmatrix}
G_{11} & -G_{11} & G_{13} & -G_{13} \\
-G_{11} & G_{11} & -G_{13} & G_{13} \\
G_{31} & -G_{31} & G_{33} & -G_{33} \\
-G_{31} & G_{31} & -G_{33} & G_{33}
\end{bmatrix}
\begin{bmatrix}
V_1 \\
V_2 \\
V_3 \\
V_4
\end{bmatrix}
=
\begin{bmatrix}
I_1 \\
-I_1 \\
I_2 \\
-I_2
\end{bmatrix}
\]

where:
\[
G_{11} = \frac{1}{R_{11}}, \quad G_{13} = -\frac{1}{R_{12}}, \quad G_{33} = \frac{1}{R_{22}}
\]

### 7. Parameter Extraction and Scaling

The per-unit-length parameters are derived from user inputs:

\[
R' = \frac{R}{\ell}, \quad L' = \frac{L}{\ell}, \quad C' = \frac{C}{\ell}, \quad G' = \frac{G}{\ell}
\]

where \( R, L, C, G \) are the total resistance, inductance, capacitance, and conductance of the line.

Temperature scaling follows:

\[
R'(T) = R'(T_0)[1 + TC1(T - T_0) + TC2(T - T_0)^2]
\]

### 8. Numerical Considerations for Convolution

The convolution length \( M \) is determined by:

\[
M = \frac{t_{\text{max}}}{\Delta t_{\text{min}}} + 1
\]

where \( t_{\text{max}} \) is the maximum time delay of significant impulse response energy and \( \Delta t_{\text{min}} \) is the minimum time step.

To prevent aliasing, the frequency sampling for FFT must satisfy:

\[
f_{\text{max}} \geq \frac{1}{2\Delta t_{\text{min}}}
\]
\[
\Delta f \leq \frac{1}{t_{\text{max}}}
\]

## Convergence Analysis

### 1. Newton-Raphson Iteration for DC Analysis

The DC operating point is found via Newton-Raphson iteration:

\[
J^{(k)} \Delta x^{(k)} = -F(x^{(k)})
\]

where:
- \( J^{(k)} = \frac{\partial F}{\partial x}\big|_{x^{(k)}} \) is the Jacobian matrix (MNA conductance matrix)
- \( \Delta x^{(k)} = x^{(k+1)} - x^{(k)} \) is the update vector
- \( F(x^{(k)}) \) is the circuit equation residual

For the transmission line DC model, the Jacobian entries are constant (linear elements), guaranteeing convergence in one iteration from any initial guess.

### 2. Transient Analysis Convergence

For transient analysis with convolution, the system is linear time-invariant (LTI) in the small-signal approximation. The convergence criterion is based on the local truncation error (LTE) of the convolution sum.

The LTE for the convolution at time step \( n \) is estimated as:

\[
\text{LTE}_v = \left| \sum_{k=0}^{M-1} h_{11}[k] \left( v_2[n-k] - \tilde{v}_2[n-k] \right) \right|
\]
\[
\text{LTE}_i = \left| \sum_{k=0}^{M-1} h_{21}[k] \left( v_2[n-k] - \tilde{v}_2[n-k] \right) \right|
\]

where \( \tilde{v}_2 \) is the predicted voltage from the previous time step.

### 3. Time Step Control Algorithm

The adaptive time step control uses the LTE estimate:

\[
\Delta t_{\text{new}} = \Delta t_{\text{current}} \cdot \min\left( \text{FACMAX}, \max\left( \text{FACMIN}, \text{FAC} \cdot \left( \frac{\epsilon}{\text{LTE}} \right)^{\frac{1}{p+1}} \right) \right)
\]

where:
- \( \epsilon \) = user-specified error tolerance (TRTOL)
- \( p \) = order of the integration method (1 for backward Euler)
- FACMAX, FACMIN = bounds on step size change (typically 2.0 and 0.5)
- FAC = safety factor (typically 0.8)

### 4. Convolution Truncation Error

The impulse response is truncated after \( M \) samples, introducing truncation error:

\[
E_{\text{trunc}} = \sum_{k=M}^{\infty} |h[k]|
\]

For stable systems with exponential decay, this error is bounded by:

\[
E_{\text{trunc}} \leq \frac{A e^{-\alpha M\Delta t}}{1 - e^{-\alpha\Delta t}}
\]

where \( A \) is the initial amplitude and \( \alpha \) is the decay rate of the impulse response.

### 5. Frequency Sampling Error in FFT

The discretization of the frequency response introduces aliasing and truncation errors. The total error in the impulse response is:

\[
E_{\text{total}} = E_{\text{aliasing}} + E_{\text{truncation}}
\]

where:
\[
E_{\text{aliasing}} = \sum_{n=-\infty}^{-1} |h(n\Delta t)|
\]
\[
E_{\text{truncation}} = \left| \frac{1}{N} \sum_{k=0}^{N-1} H(k\Delta f) e^{j2\pi k n/N} - h(n\Delta t) \right|
\]

### 6. Convergence Criteria for Newton Iteration

The DC and transient Newton iterations terminate when:

\[
\| \Delta x^{(k)} \|_\infty < \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \| x^{(k)} \|_\infty
\]

where:
- \( \epsilon_{\text{abs}} = \text{ABSTOL} \) (absolute tolerance, typically 1e-12)
- \( \epsilon_{\text{rel}} = \text{RELTOL} \) (relative tolerance, typically 1e-3)
- \( \| \cdot \|_\infty \) = maximum norm

For the transmission line convolution model, the residual function \( F(x) \) includes the convolution sums, making the system memory-dependent but linear in the current variables.

### 7. Stability Analysis

The convolution-based model stability requires:

1. **Bounded Input Bounded Output (BIBO) stability**:
   \[
   \sum_{k=0}^{\infty} |h[k]| < \infty
   \]

2. **Numerical stability of convolution sum**:
   The recursive convolution implementation must avoid accumulation of round-off error.

3. **Time step stability**:
   The effective numerical integration of the convolution must satisfy:
   \[
   \Delta t < \frac{2}{|\lambda_{\text{max}}|}
   \]
   where \( \lambda_{\text{max}} \) is the largest eigenvalue of the discretized system.

### 8. Special Cases and Degeneracies

1. **Lossless limit** (\( R' = 0, G' = 0 \)):
   The convolution reduces to pure delay:
   \[
   h(t) = \delta(t - \tau_d)
   \]
   where \( \tau_d = \ell\sqrt{L'C'} \)

2. **DC limit** (\( \omega \to 0 \)):
   As derived in the DC load model section

3. **Very lossy limit** (\( R' \gg \omega L', G' \gg \omega C' \)):
   The line behaves as a distributed RC network with diffusion-like response

### 9. Error Propagation in Monte Carlo Analysis

When used with Monte Carlo parameter variations, the convergence must account for statistical variations:

\[
P\left( \left| \hat{x} - x_{\text{true}} \right| < \epsilon \right) \geq 1 - \alpha
\]

where \( \hat{x} \) is the Monte Carlo estimate and \( \alpha \) is the confidence level. The required number of Monte Carlo runs for error \( \epsilon \) is:

\[
N \geq \left( \frac{z_{\alpha/2} \sigma}{\epsilon} \right)^2
\]

where \( \sigma \) is the standard deviation of the output and \( z_{\alpha/2} \) is the standard normal quantile.

### 10. Implementation-Specific Convergence Enhancements

The Ngspice implementation includes:

1. **Predictor-corrector for convolution**: Reduces LTE by predicting future values
2. **Adaptive convolution window**: Adjusts \( M \) based on impulse response decay
3. **Caching of convolution sums**: Avoids recomputation for repeated time steps
4. **Regularization for near-DC frequencies**: Prevents ill-conditioning when \( \omega \to 0 \)

This mathematical formulation provides the foundation for Ngspice's lossy transmission line model, balancing accuracy in frequency-dependent behavior with computational efficiency through judicious use of convolution and specialized DC handling.

## C Implementation

### 1. Core Data Structures (`txldefs.h`)

The implementation is anchored by two primary structures that map directly to the mathematical model's parameters and state variables.

```c
typedef struct sTXLmodel {
    int TXLmodType;                 /* Model type identifier */
    double TXLr;                    /* Resistance per unit length */
    double TXLl;                    /* Inductance per unit length */
    double TXLg;                    /* Conductance per unit length */
    double TXLc;                    /* Capacitance per unit length */
    double TXLlength;               /* Total line length */
    double TXLtemp;                 /* Temperature */
    double TXLtc1;                  /* First temperature coefficient */
    double TXLtc2;                  /* Second temperature coefficient */
    double TXLrs;                   /* Surface roughness factor (skin effect) */
    double TXLtand;                 /* Dielectric loss tangent */
    
    /* Frequency-domain data */
    int TXLnFreq;                   /* Number of frequency points */
    double *TXLfreq;                /* Frequency array */
    double *TXLz0Real;              /* Real part of Z0(ω) */
    double *TXLz0Imag;              /* Imaginary part of Z0(ω) */
    double *TXLgammaReal;           /* Real part of γ(ω) */
    double *TXLgammaImag;           /* Imaginary part of γ(ω) */
    
    /* Rational approximation for recursive convolution */
    int TXLnPoles;                  /* Number of poles in approximation */
    double *TXLpoles;               /* Pole locations a_k */
    double *TXLresidues;            /* Residues c_k */
    double TXLdirect;               /* Direct term d */
    
    struct sTXLmodel *TXLnextModel; /* Next model in linked list */
    GENmodel *GENmod;               /* Generic model structure */
} TXLmodel;

typedef struct sTXLinstance {
    int TXLposNode;                 /* Positive node of port 1 */
    int TXLnegNode;                 /* Negative node of port 1 */
    int TXLposPrimeNode;            /* Positive node of port 2 */
    int TXLnegPrimeNode;            /* Negative node of port 2 */
    int TXLbranchEq1;               /* Branch equation index for I1 */
    int TXLbranchEq2;               /* Branch equation index for I2 */
    
    /* Convolution history buffers */
    double *TXLhistoryV1;           /* History of V1(t) for convolution */
    double *TXLhistoryV2;           /* History of V2(t) for convolution */
    double *TXLhistoryI1;           /* History of I1(t) for convolution */
    double *TXLhistoryI2;           /* History of I2(t) for convolution */
    int TXLhistIndex;               /* Current index in circular buffer */
    int TXLhistSize;                /* Size of history buffer */
    
    /* Recursive convolution state variables */
    double *TXLstateV1;             /* State variables for V1 recursion */
    double *TXLstateV2;             /* State variables for V2 recursion */
    double *TXLstateI1;             /* State variables for I1 recursion */
    double *TXLstateI2;             /* State variables for I2 recursion */
    
    /* Pre-computed impulse/step response */
    double *TXLimpulseResp;         /* Impulse response h[n] */
    double *TXLstepResp;            /* Step response s[n] */
    int TXLrespLength;              /* Length of response arrays */
    
    /* DC load parameters */
    double TXLdcResist;             /* DC resistance R*length */
    double TXLdcConduct;            /* DC conductance G*length */
    
    /* Matrix pointers for MNA stamping */
    double *TXLposPosPtr;           /* G_{11} in MNA matrix */
    double *TXLposNegPtr;           /* G_{12} in MNA matrix */
    double *TXLnegPosPtr;           /* G_{21} in MNA matrix */
    double *TXLnegNegPtr;           /* G_{22} in MNA matrix */
    double *TXLposPosPrimePtr;      /* G_{13} in MNA matrix */
    double *TXLposNegPrimePtr;      /* G_{14} in MNA matrix */
    /* ... additional matrix pointers for full 4x4 stamp ... */
    
    struct sTXLinstance *TXLnextInstance; /* Next instance in linked list */
    TXLmodel *TXLmodPtr;            /* Pointer to associated model */
    GENinstance GENinst;            /* Generic instance structure */
} TXLinstance;
```

### 2. Parameter Processing (`txlparam.c`)

This file implements the mathematical parameter extraction and frequency-domain calculations.

```c
int TXLparam(TXLinstance *inst, TXLmodel *model, double freq[], int nfreq)
{
    double omega, R, L, G, C, Z0real, Z0imag, gammareal, gammaimag;
    double length = inst->TXLlength;
    int i;
    
    /* Apply temperature scaling to R and G */
    double deltaT = model->TXLtemp - TNOM;
    R = model->TXLr * (1.0 + model->TXLtc1 * deltaT + model->TXLtc2 * deltaT * deltaT);
    G = model->TXLg * (1.0 + model->TXLtc1 * deltaT + model->TXLtc2 * deltaT * deltaT);
    L = model->TXLl;
    C = model->TXLc;
    
    /* Store DC parameters for DC load analysis */
    inst->TXLdcResist = R * length;
    inst->TXLdcConduct = G * length;
    
    /* Calculate frequency-dependent parameters */
    for (i = 0; i < nfreq; i++) {
        omega = 2.0 * M_PI * freq[i];
        
        /* Apply skin effect model if enabled */
        if (model->TXLrs > 0.0) {
            double skinDepth = sqrt(2.0 / (omega * MU0 * model->TXLrs));
            R = model->TXLr * (1.0 + model->TXLrs / skinDepth);
            L = model->TXLl + model->TXLrs / (2.0 * omega * skinDepth);
        }
        
        /* Apply dielectric loss model if enabled */
        if (model->TXLtand > 0.0) {
            G = model->TXLg + omega * C * model->TXLtand;
        }
        
        /* Calculate Z0(ω) = sqrt((R + jωL)/(G + jωC)) */
        /* Real part calculation */
        double numMag = sqrt(R*R + omega*omega*L*L);
        double denMag = sqrt(G*G + omega*omega*C*C);
        double phaseNum = atan2(omega*L, R);
        double phaseDen = atan2(omega*C, G);
        
        Z0real = sqrt(numMag/denMag) * cos((phaseNum - phaseDen)/2.0);
        Z0imag = sqrt(numMag/denMag) * sin((phaseNum - phaseDen)/2.0);
        
        /* Calculate γ(ω) = sqrt((R + jωL)(G + jωC)) */
        double prodMag = numMag * denMag;
        double prodPhase = phaseNum + phaseDen;
        
        gammareal = sqrt(prodMag) * cos(prodPhase/2.0);
        gammaimag = sqrt(prodMag) * sin(prodPhase/2.0);
        
        /* Store in frequency tables */
        model->TXLz0Real[i] = Z0real;
        model->TXLz0Imag[i] = Z0imag;
        model->TXLgammaReal[i] = gammareal;
        model->TXLgammaImag[i] = gammaimag;
    }
    
    return OK;
}
```

### 3. Frequency-Basis Response Generation (`txlfbr.c`)

This file computes the impulse/step response from frequency-domain data, implementing the convolution math core.

```c
int TXLfbr(TXLinstance *inst, TXLmodel *model)
{
    double *freq = model->TXLfreq;
    double *Z0real = model->TXLz0Real;
    double *Z0imag = model->TXLz0Imag;
    double *gammaReal = model->TXLgammaReal;
    double *gammaImag = model->TXLgammaImag;
    int nFreq = model->TXLnFreq;
    double length = inst->TXLlength;
    
    /* Allocate frequency response arrays */
    double *Y11real = (double *)malloc(nFreq * sizeof(double));
    double *Y11imag = (double *)malloc(nFreq * sizeof(double));
    double *Y12real = (double *)malloc(nFreq * sizeof(double));
    double *Y12imag = (double *)malloc(nFreq * sizeof(double));
    
    /* Calculate Y-parameters Y11(ω) and Y12(ω) */
    for (int i = 0; i < nFreq; i++) {
        double omega = 2.0 * M_PI * freq[i];
        double Z0mag = sqrt(Z0real[i]*Z0real[i] + Z0imag[i]*Z0imag[i]);
        double Z0phase = atan2(Z0imag[i], Z0real[i]);
        double gammaLreal = gammaReal[i] * length;
        double gammaLimag = gammaImag[i] * length;
        
        /* Compute cosh(γℓ) and sinh(γℓ) */
        double coshReal = cosh(gammaLreal) * cos(gammaLimag);
        double coshImag = sinh(gammaLreal) * sin(gammaLimag);
        double sinhReal = sinh(gammaLreal) * cos(gammaLimag);
        double sinhImag = cosh(gammaLreal) * sin(gammaLimag);
        
        /* Y11 = cosh(γℓ) / (Z0 * sinh(γℓ)) */
        /* Complex division: (a+jb)/(c+jd) = [(ac+bd)+j(bc-ad)]/(c²+d²) */
        double denom = sinhReal*sinhReal + sinhImag*sinhImag;
        Y11real[i] = (coshReal*sinhReal + coshImag*sinhImag) / denom;
        Y11imag[i] = (coshImag*sinhReal - coshReal*sinhImag) / denom;
        
        /* Divide by Z0 */
        double tempReal = Y11real[i];
        double tempImag = Y11imag[i];
        Y11real[i] = (tempReal*Z0real[i] + tempImag*Z0imag[i]) / (Z0mag*Z0mag);
        Y11imag[i] = (tempImag*Z0real[i] - tempReal*Z0imag[i]) / (Z0mag*Z0mag);
        
        /* Y12 = -1 / (Z0 * sinh(γℓ)) */
        Y12real[i] = -sinhReal / denom;
        Y12imag[i] = sinhImag / denom;
        
        /* Divide by Z0 */
        tempReal = Y12real[i];
        tempImag = Y12imag[i];
        Y12real[i] = (tempReal*Z0real[i] + tempImag*Z0imag[i]) / (Z0mag*Z0mag);
        Y12imag[i] = (tempImag*Z0real[i] - tempReal*Z0imag[i]) / (Z0mag*Z0mag);
    }
    
    /* Perform Inverse FFT to get impulse response */
    int nTime = 2 * (nFreq - 1);  /* Time samples for IFFT */
    inst->TXLrespLength = nTime;
    inst->TXLimpulseResp = (double *)malloc(nTime * sizeof(double));
    
    /* Hermitian symmetry for real-valued time signal */
    double *freqData = (double *)malloc(2 * nFreq * sizeof(double));
    for (int i = 0; i < nFreq; i++) {
        freqData[2*i] = Y11real[i];   /* Real part */
        freqData[2*i+1] = Y11imag[i]; /* Imaginary part */
    }
    
    /* Apply IFFT using Ngspice's FFT routines */
    ifft(freqData, nFreq);
    
    /* Extract impulse response and apply window function */
    for (int i = 0; i < nTime; i++) {
        double window = 0.5 * (1.0 - cos(2.0 * M_PI * i / (nTime - 1))); /* Hann window */
        inst->TXLimpulseResp[i] = freqData[i] * window;
    }
    
    /* Compute step response by cumulative sum of impulse response */
    inst->TXLstepResp = (double *)malloc(nTime * sizeof(double));
    inst->TXLstepResp[0] = inst->TXLimpulseResp[0];
    for (int i = 1; i < nTime; i++) {
        inst->TXLstepResp[i] = inst->TXLstepResp[i-1] + inst->TXLimpulseResp[i];
    }
    
    free(Y11real); free(Y11imag); free(Y12real); free(Y12imag); free(freqData);
    return OK;
}
```

### 4. Matrix Loading and Convolution Execution (`txlload.c`)

This file implements the core simulation functions: DC load stamping and transient convolution loading.

```c
int TXLload(TXLinstance *inst, CKTcircuit *ckt)
{
    double *rhs = ckt->CKTrhs;
    double *rhsOld = ckt->CKTrhsOld;
    double delta = ckt->CKTdelta;
    int isDC = (ckt->CKTmode & MODEDC) ? 1 : 0;
    
    if (isDC) {
        /* DC Load Analysis - use simplified resistive model */
        return TXLdcLoad(inst, ckt);
    } else {
        /* Transient Analysis - use convolution */
        return TXLtransientLoad(inst, ckt);
    }
}

int TXLdcLoad(TXLinstance *inst, CKTcircuit *ckt)
{
    double Rdc = inst->TXLdcResist;
    double Gdc = inst->TXLdcConduct;
    double length = inst->TXLlength;
    
    /* Calculate DC resistance matrix elements */
    double Z0dc = sqrt(Rdc / Gdc);  /* Z0 at DC */
    double gammadc = sqrt(Rdc * Gdc);  /* γ at DC */
    double gammadcL = gammadc * length;
    
    double R11, R12;
    if (gammadcL > 1e-6) {
        /* Use hyperbolic functions for significant loss */
        R11 = Z0dc * (cosh(gammadcL) / sinh(gammadcL));  /* Z0 * coth(γℓ) */
        R12 = -Z0dc / sinh(gammadcL);                    /* -Z0 * csch(γℓ) */
    } else {
        /* Small loss approximation */
        R11 = Rdc * length / 3.0 + 1.0 / (Gdc * length);
        R12 = -Rdc * length / 6.0;
    }
    
    /* Convert to conductances for MNA stamp */
    double g11 = 1.0 / R11;
    double g12 = -1.0 / R12;  /* Note: R12 is negative */
    
    /* Stamp 4x4 conductance matrix for two-port */
    /* Port 1 self-conductance */
    *(inst->TXLposPosPtr) += g11;
    *(inst->TXLposNegPtr) += -g11;
    *(inst->TXLnegPosPtr) += -g11;
    *(inst->TXLnegNegPtr) += g11;
    
    /* Coupling between ports */
    *(inst->TXLposPosPrimePtr) += g12;
    *(inst->TXLposNegPrimePtr) += -g12;
    *(inst->TXLnegPosPrimePtr) += -g12;
    *(inst->TXLnegNegPrimePtr) += g12;
    
    /* Symmetric coupling */
    *(inst->TXLposPrimePosPtr) += g12;
    *(inst->TXLposPrimeNegPtr) += -g12;
    *(inst->TXLnegPrimePosPtr) += -g12;
    *(inst->TXLnegPrimeNegPtr) += g12;
    
    /* Port 2 self-conductance (same as port 1) */
    *(inst->TXLposPrimePosPrimePtr) += g11;
    *(inst->TXLposPrimeNegPrimePtr) += -g11;
    *(inst->TXLnegPrimePosPrimePtr) += -g11;
    *(inst->TXLnegPrimeNegPrimePtr) += g11;
    
    return OK;
}

int TXLtransientLoad(TXLinstance *inst, CKTcircuit *ckt)
{
    double delta = ckt->CKTdelta;
    double *rhs = ckt->CKTrhs;
    double *rhsOld = ckt->CKTrhsOld;
    
    /* Get current and previous voltages */
    double v1 = rhs[inst->TXLposNode] - rhs[inst->TXLnegNode];
    double v2 = rhs[inst->TXLposPrimeNode] - rhs[inst->TXLnegPrimeNode];
    double v1_old = rhsOld[inst->TXLposNode] - rhsOld[inst->TXLnegNode];
    double v2_old = rhsOld[inst->TXLposPrimeNode] - rhsOld[inst->TXLnegPrimeNode];
    
    /* Update history buffer index */
    inst->TXLhistIndex = (inst->TXLhistIndex + 1) % inst->TXLhistSize;
    
    /* Store current voltages in history buffer */
    inst->TXLhistoryV1[inst->TXLhistIndex] = v1;
    inst->TXLhistoryV2[inst->TXLhistIndex] = v2;
    
    /* Perform convolution to compute currents */
    double i1 = 0.0, i2 = 0.0;
    double *h = inst->TXLimpulseResp;
    int respLength = inst->TXLrespLength;
    
    /* Convolution sum: i1[n] = Σ h[k] * v2[n-k] */
    for (int k = 0; k < respLength && k <= inst->TXLhistIndex; k++) {
        int histIdx = (inst->TXLhistIndex - k + inst->TXLhistSize) % inst->TXLhistSize;
        i1 += h[k] * inst->TXLhistoryV2[histIdx];
        i2 += h[k] * inst->TXLhistoryV1[histIdx];
    }
    
    /* Add contributions from older history if buffer wrapped */
    if (inst->TXLhistIndex < respLength) {
        for (int k = inst->TXLhistIndex + 1; k < respLength; k++) {
            int histIdx = inst->TXLhistSize - (k - inst->TXLhistIndex);
            i1 += h[k] * inst->TXLhistoryV2[histIdx];
            i2 += h[k] * inst->TXLhistoryV1[histIdx];
        }
    }
    
    /* Store currents in history buffer */
    inst->TXLhistoryI1[inst->TXLhistIndex] = i1;
    inst->TXLhistoryI2[inst->TXLhistIndex] = i2;
    
    /* Stamp dependent current sources into MNA matrix */
    /* I1 depends on V2 history */
    rhs[inst->TXLposNode] -= i1;
    rhs[inst->TXLnegNode] += i1;
    
    /* I2 depends on V1 history */
    rhs[inst->TXLposPrimeNode] -= i2;
    rhs[inst->TXLnegPrimeNode] += i2;
    
    /* Stamp conductance for numerical stability (GMIN) */
    double gmin = ckt->CKTgmin;
    *(inst->TXLposPosPtr) += gmin;
    *(inst->TXLnegNegPtr) += gmin;
    *(inst->TXLposPrimePosPrimePtr) += gmin;
    *(inst->TXLnegPrimeNegPrimePtr) += gmin;
    
    return OK;
}

int TXLconvTest(TXLinstance *inst, CKTcircuit *ckt)
{
    double reltol = ckt->CKTreltol;
    double abstol = ckt->CKTabstol;
    double vntol = ckt->CKTvoltTol;
    
    /* Get current and previous voltages */
    double v1_new = ckt->CKTrhs[inst->TXLposNode] - ckt->CKTrhs[inst->TXLnegNode];
    double v2_new = ckt->CKTrhs[inst->TXLposPrimeNode] - ckt->CKTrhs[inst->TXLnegPrimeNode];
    double