# Lossy Transmission Line: Matrix Setup, API Binding, and Memory

_Generated 2026-04-12 21:32 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlinit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlitf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txldel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txlmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/txl/txldest.c`

# Chapter: Lossy Transmission Line: Matrix Setup, API Binding, and Memory

## Technical Introduction

The files `txlsetup.c`, `txlmask.c`, `txlmpar.c`, `txlask.c`, `txlinit.h`, `txlext.h`, `txlitf.h`, `txlinit.c`, `txl.c`, `txldel.c`, `txlmdel.c`, and `txldest.c` collectively implement the Ngspice lossy transmission line model's infrastructure layer—the bridge between the mathematical convolution model and the SPICE simulation engine. This layer handles the critical tasks of matrix allocation, parameter management, API registration, and memory lifecycle. `txlsetup.c` allocates the sparse matrix pointers within SPICE's Modified Nodal Analysis (MNA) system, mapping the transmission line's 4 nodes and 2 branch currents to specific positions in the global matrix. `txlmask.c` and `txlmpar.c` manage model-level parameter masking and parsing, enforcing constraints and default values for per-unit-length R, L, G, C parameters. `txlask.c` provides the query interface for retrieving instance parameters during simulation. The header files (`txlinit.h`, `txlext.h`, `txlitf.h`) define the internal and external APIs and data structures. `txlinit.c` is the cornerstone, registering the device with Ngspice via the `SPICEdev` structure, binding the mathematical functions (`TXLload`, `TXLsetup`, `TXLtrunc`) to the simulation kernel. `txl.c` contains the core device logic, while `txldel.c`, `txlmdel.c`, and `txldest.c` manage the precise deallocation of instance and model memory, ensuring no leaks in long-running or Monte Carlo analyses. Together, these files transform the abstract convolution mathematics into a robust, memory-efficient, and kernel-integrated simulation component.

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

### 1. Matrix Setup and Allocation (`txlsetup.c`)

The `TXLsetup` function performs the critical task of allocating positions within SPICE's sparse matrix (SMP) for the transmission line's contributions. A lossy transmission line, being a 4-terminal device with 2 branch currents (I1, I2), requires 18 matrix entries in the full MNA formulation.

```c
int TXLsetup(TXLmodel *model, CKTcircuit *ckt)
{
    TXLinstance *inst;
    int error;
    
    /* Loop through all instances of this model */
    for (; model != NULL; model = model->TXLnextModel) {
        for (inst = model->TXLinstances; inst != NULL; inst = inst->TXLnextInstance) {
            
            /* Allocate matrix positions for the 4-node, 2-branch system */
            /* Port 1 self terms: G11 */
            error = SMPmakeElt(ckt, inst->TXLposNode1, inst->TXLposNode1, 
                               &(inst->TXLp1p1Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLposNode1, inst->TXLnegNode1, 
                               &(inst->TXLp1n1Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLnegNode1, inst->TXLposNode1, 
                               &(inst->TXLn1p1Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLnegNode1, inst->TXLnegNode1, 
                               &(inst->TXLn1n1Ptr));
            if (error) return error;
            
            /* Port 2 self terms: G22 */
            error = SMPmakeElt(ckt, inst->TXLposNode2, inst->TXLposNode2, 
                               &(inst->TXLp2p2Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLposNode2, inst->TXLnegNode2, 
                               &(inst->TXLp2n2Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLnegNode2, inst->TXLposNode2, 
                               &(inst->TXLn2p2Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLnegNode2, inst->TXLnegNode2, 
                               &(inst->TXLn2n2Ptr));
            if (error) return error;
            
            /* Cross-coupling terms: G12 and G21 */
            error = SMPmakeElt(ckt, inst->TXLposNode1, inst->TXLposNode2, 
                               &(inst->TXLp1p2Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLposNode1, inst->TXLnegNode2, 
                               &(inst->TXLp1n2Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLnegNode1, inst->TXLposNode2, 
                               &(inst->TXLn1p2Ptr));
            if (error) return error;
            error = SMPmakeElt(ckt, inst->TXLnegNode1, inst->TXLnegNode2, 
                               &(inst->TXLn1n2Ptr));
            if (error) return error;
            
            /* Branch equation stamps: I1 = f(V), I2 = f(V) */
            if (inst->TXLbranchEq1 >= 0) {
                error = SMPmakeElt(ckt, inst->TXLbranchEq1, inst->TXLposNode1, 
                                   &(inst->TXLb1p1Ptr));
                if (error) return error;
                error = SMPmakeElt(ckt, inst->TXLbranchEq1, inst->TXLnegNode1, 
                                   &(inst->TXLb1n1Ptr));
                if (error) return error;
            }
            if (inst->TXLbranchEq2 >= 0) {
                error = SMPmakeElt(ckt, inst->TXLbranchEq2, inst->TXLposNode2, 
                                   &(inst->TXLb2p2Ptr));
                if (error) return error;
                error = SMPmakeElt(ckt, inst->TXLbranchEq2, inst->TXLnegNode2, 
                                   &(inst->TXLb2n2Ptr));
                if (error) return error;
            }
            
            /* Initialize history buffers for convolution */
            inst->TXLhistSize = (int)(model->TXLmaxDelay / ckt->CKTminTimeStep) + 1;
            inst->TXLhistV1 = (double *)calloc(inst->TXLhistSize, sizeof(double));
            inst->TXLhistV2 = (double *)calloc(inst->TXLhistSize, sizeof(double));
            inst->TXLhistI1 = (double *)calloc(inst->TXLhistSize, sizeof(double));
            inst->TXLhistI2 = (double *)calloc(inst->TXLhistSize, sizeof(double));
            inst->TXLhistIndex = 0;
            
            /* Allocate state variables for recursive convolution */
            if (model->TXLnPoles > 0) {
                inst->TXLstateV1Real = (double *)calloc(model->TXLnPoles, sizeof(double));
                inst->TXLstateV1Imag = (double *)calloc(model->TXLnPoles, sizeof(double));
                inst->TXLstateV2Real = (double *)calloc(model->TXLnPoles, sizeof(double));
                inst->TXLstateV2Imag = (double *)calloc(model->TXLnPoles, sizeof(double));
            }
        }
    }
    return OK;
}
```

### 2. Parameter Masking and Validation (`txlmask.c`)

The `TXLmask` function validates and applies bit masks to model parameters, ensuring physically realistic values. It directly implements bounds from the mathematical formulation, such as positive definiteness for R', L', C'.

```c
void TXLmask(TXLmodel *model, int which, IFvalue *value)
{
    double newval;
    
    switch (which) {
        case TXL_R_PER_UNIT:
            /* Resistance per unit length must be non-negative */
            newval = value->rValue;
            if (newval < 0.0) {
                fprintf(stderr, "Warning: TXL R per unit length negative, clamping to 0\n");
                newval = 0.0;
            }
            model->TXLrPerUnit = newval;
            break;
            
        case TXL_L_PER_UNIT:
            /* Inductance per unit length must be positive */
            newval = value->rValue;
            if (newval <= 0.0) {
                fprintf(stderr, "Error: TXL L per unit length must be > 0\n");
                model->TXLlPerUnit = 1e-12; /* Default small value */
            } else {
                model->TXLlPerUnit = newval;
            }
            break;
            
        case TXL_G_PER_UNIT:
            /* Conductance per unit length must be non-negative */
            newval = value->rValue;
            if (newval < 0.0) {
                fprintf(stderr, "Warning: TXL G per unit length negative, clamping to 0\n");
                newval = 0.0;
            }
            model->TXLgPerUnit = newval;
            break;
            
        case TXL_C_PER_UNIT:
            /* Capacitance per unit length must be positive */
            newval = value->rValue;
            if (newval <= 0.0) {
                fprintf(stderr, "Error: TXL C per unit length must be > 0\n");
                model->TXLcPerUnit = 1e-15; /* Default small value */
            } else {
                model->TXLcPerUnit = newval;
            }
            break;
            
        case TXL_TEMP_COEFF1:
            /* Temperature coefficient 1 */
            model->TXLtempCoeff1 = value->rValue;
            break;
            
        case TXL_TEMP_COEFF2:
            /* Temperature coefficient 2 */
            model->TXLtempCoeff2 = value->rValue;
            break;
            
        default:
            fprintf(stderr, "TXLmask: Unknown parameter %d\n", which);
    }
}
```

### 3. Model Parameter Processing (`txlmpar.c`)

The `TXLmParam` function processes model-level parameters, computing derived quantities essential for simulation. This includes calculating the maximum delay \( \tau_{max} = \ell \sqrt{L'C'} \) for history buffer sizing.

```c
int TXLmParam(int param, IFvalue *value, TXLmodel *model)
{
    switch (param) {
        case TXL_R_PER_UNIT:
            model->TXLrPerUnit = value->rValue;
            break;
            
        case TXL_L_PER_UNIT:
            model->TXLlPerUnit = value->rValue;
            /* Recompute maximum delay for history buffer sizing */
            if (model->TXLcPerUnit > 0.0) {
                model->TXLmaxDelay = model->TXLlength * 
                                     sqrt(model->TXLlPerUnit * model->TXLcPerUnit);
            }
            break;
            
        case TXL_G_PER_UNIT:
            model->TXLgPerUnit = value->rValue;
            break;
            
        case TXL_C_PER_UNIT:
            model->TXLcPerUnit = value->rValue;
            /* Recompute maximum delay */
            if (model->TXLlPerUnit > 0.0) {
                model->TXLmaxDelay = model->TXLlength * 
                                     sqrt(model->TXLlPerUnit * model->TXLcPerUnit);
            }
            break;
            
        case TXL_LENGTH:
            model->TXLlength = value->rValue;
            /* Recompute maximum delay */
            if (model->TXLlPerUnit > 0.0 && model->TXLcPerUnit > 0.0) {
                model->TXLmaxDelay = model->TXLlength * 
                                     sqrt(model->TXLlPerUnit * model->TXLcPerUnit);
            }
            break;
            
        case TXL_N_POLES:
            /* Number of poles for rational approximation */
            model->TXLnPoles = value->iValue;
            if (model->TXLnPoles > 0) {
                /* Allocate pole and residue arrays */
                if (model->TXLpoleReal) free(model->TXLpoleReal);
                if (model->TXLpoleImag) free(model->TXLpoleImag);
                if (model->TXLresidueReal) free(model->TXLresidueReal);
                if (model->TXLresidueImag) free(model->TXLresidueImag);
                
                model->TXLpoleReal = (double *)malloc(model->TXLnPoles * sizeof(double));
                model->TXLpoleImag = (double *)malloc(model->TXLnPoles * sizeof(double));
                model->TXLresidueReal = (double *)malloc(model->TXLnPoles * sizeof(double));
                model->TXLresidueImag = (double *)malloc(model->TXLnPoles * sizeof(double));
            }
            break;
            
        default:
            return E_BADPARM;
    }
    return OK;
}
```

### 4. Instance Parameter Query (`txlask.c`)

The `TXLask` function provides the interface for querying instance parameters during simulation, mapping internal C variables to user-accessible parameters.

```c
int TXLask(CKTcircuit *ckt, TXLinstance *inst, int which, IFvalue *value)
{
    switch (which) {
        case TXL_LENGTH:
            value->rValue = inst->TXLlength;
            break;
            
        case TXL_WIDTH:
            value->rValue = inst->TXLwidth;
            break;
            
        case TXL_TEMP:
            value->rValue = inst->TXLtemp;
            break;
            
        case TXL_V1:
            /* Current voltage at port 1 */
            value->rValue = *(ckt->CKTrhs[inst->TXLposNode1]) - 
                            *(ckt->CKTrhs[inst->TXLnegNode1]);
            break;
            
        case TXL_V2:
            /* Current voltage at port 2 */
            value->rValue = *(ckt->CKTrhs[inst->TXLposNode2]) - 
                            *(ckt->CKTrhs[inst->TXLnegNode2]);
            break;
            
        case TXL_I1:
            /* Current at port 1 from convolution */
            value->rValue = TXLcalculateCurrent(inst,
                *(ckt->CKTrhs[inst->TXLposNode1]) - *(ckt->CKTrhs[inst->TXLnegNode1]),
                *(ckt->CKTrhs[inst->TXLposNode2]) - *(ckt->CKTrhs[inst->TXLnegNode2]),
                1);
            break;
            
        case TXL_I2:
            /* Current at port 2 from convolution */
            value->rValue = TXLcalculateCurrent(inst,
                *(ckt->CKTrhs[inst->TXLposNode1]) - *(ckt->CKTrhs[inst->TXLnegNode1]),
                *(ckt->CKTrhs[inst->TXLposNode2]) - *(ckt->CKTrhs[inst->TXLnegNode2]),
                2);
            break;
            
        case TXL_Z0_REAL:
            /* Real part of characteristic impedance at current frequency */
            if (ckt->CKTomega > 0.0) {
                value->rValue = TXLinterpolateZ0Real(inst, ckt->CKTomega);
            } else {
                value->rValue = sqrt(inst->TXLmodPtr->TXLrPerUnit / 
                                     inst->TXLmodPtr->TXLgPerUnit);
            }
            break;
            
        case TXL_Z0_IMAG:
            /* Imaginary part of Z0 */
            if (ckt->CKTomega > 0.0) {
                value->rValue = TXLinterpolateZ0Imag(inst, ckt->CKTomega);
            } else {
                value->rValue = 0.0;
            }
            break;
            
        default:
            return E_BADPARM;
    }
    return OK;
}
```

### 5. SPICEdev API Registration (`txlinit.c`)

The core of Ngspice integration is the `SPICEdev` structure defined in `txlinit.c`. This structure maps all device functions to the Ngspice kernel, enabling the transmission line to participate in DC, AC, transient, and noise analyses.

```c
/* SPICEdev structure for TXL device */
SPICEdev TXLinfo = {
    .DEVpublic = {
        .name = "TXL",
        .description = "Lossy Transmission Line",
        .terms = 4,  /* 4-terminal device */
        .numNames = 0,
        .termNames = NULL,
        .numInstanceParms = 8,
        .instanceParms = TXLpTable,
        .numModelParms = 6,
        .modelParms = TXLmPTable,
        .flags = DEV_DEFAULT,
    },
    
    /* Function pointers binding math to simulation */
    .DEVparam = TXLparam,           /* Instance parameter processing */
    .DEVmodParam = TXLmParam,       /* Model parameter processing */
    .DEVload = TXLload,             /* Matrix loading (DC & transient) */
    .DEVsetup = TXLsetup,           /* Matrix allocation */
    .DEVunsetup = NULL,
    .DEVpzSetup = TXLsetup,         /* Pole-zero setup */
    .DEVtemperature = TXLtemp,      /* Temperature update */
    .DEVtrunc = TXLtrunc,           /* Local truncation error */
    .DEVfindBranch = NULL,
    .DEVacLoad = TXLacLoad,         /* AC analysis loading */
    .DEVaccept = TXLaccept,         /* Accept time step */
    .DEVdestroy = TXLdestroy,       /* Instance destruction */
    .DEVmodDelete = TXLmDelete,     /* Model deletion */
    .DEVdelete = TXLdelete,         /* Instance deletion */
    .DEVsetic = NULL,
    .DEVask = TXLask,               /* Parameter query */
    .DEVmodAsk = NULL,
    .DEVpzLoad = TXLpzLoad,         /* Pole-zero loading */
    .DEVconvTest = TXLconvTest,     /* Convergence test */
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = NULL,
    .DEVnoise = NULL,
    .DEVsoaCheck = NULL,
    .DEVinstSize = sizeof(TXLinstance),
    .DEVmodSize = sizeof(TXLmodel)
};

/* Device initialization function called by Ngspice */
int TXLinit(GENmodel *inModel, CKTcircuit *ckt)
{
    TXLmodel *model = (TXLmodel *)inModel;
    TXLinstance *inst;
    
    /* Initialize all instances in the model */
    for (; model != NULL; model = model->TXLnextModel) {
        for (inst = model->TXLinstances; inst != NULL; inst = inst->TXLnextInstance) {
            
            /* Initialize history buffers to zero */
            if (inst->TXLhistV1) {
                memset(inst->TXLhistV1, 0, inst->TXLhistSize * sizeof(double));
                memset(inst->TXLhistV2, 0, inst->TXLhistSize * sizeof(double));
                memset(inst->TXLhistI1, 0, inst->TXLhistSize * sizeof(double));
                memset(inst->TXLhistI2, 0, inst->TXLhistSize * sizeof(double));
            }
            
            /* Initialize state variables for recursive convolution */
            if (inst->TXLstateV1Real && model->TXLnPoles > 0) {
                memset(inst->TXLstateV1Real, 0, model->TXLnPoles * sizeof(double));
                memset(inst->TXLstateV1Imag, 0, model->TXLnPoles * sizeof(double));
                memset(inst->TXLstateV2Real, 0, model->TXLnPoles * sizeof(double));
                memset(inst->TXLstateV2Imag, 0, model->TXLnPoles * sizeof(double));
            }
            
            /* Initialize matrix pointers to NULL for safety */
            inst->TXLp1p1Ptr = inst->TXLp1n1Ptr = inst->TXLn1p1Ptr = inst->TXLn1n1Ptr = NULL;
            inst->TXLp2p2Ptr = inst->TXLp2n2Ptr = inst->TXLn2p2Ptr = inst->TXLn2n2Ptr = NULL;
            inst->TXLp1p2Ptr = inst->TXLp1n2Ptr = inst->TXLn1p2Ptr = inst->TXLn1n2Ptr = NULL;
            inst->TXLb1p1Ptr = inst->TXLb1n1Ptr = inst->TXLb2p2Ptr = inst->TXLb2n2Ptr = NULL;
        }
    }
    return OK;
}
```

### 6. Core Device Logic (`txl.c`)

The `txl.c` file contains the central device logic, including the `TXLload` function that stamps the conductance matrix based on the convolution mathematics.

```c
int TXLload(TXLinstance *inst, CKTcircuit *ckt)
{
    double v1, v2, i1, i2;
    double g11, g12, g21, g22;
    
    /* Get current port voltages from MNA solution vector */
    v1 = *(ckt->CKTrhs[inst->TXLposNode1]) - *(ckt->CKTrhs[inst->TXLnegNode1]);
    v2 = *(ckt->CKTrhs[inst->TXLposNode2]) - *(ckt->CKTrhs[inst->TXLnegNode2]);
    
    if (ckt->CKTmode & MODEDC) {
        /* DC analysis: use simple resistive model */
        /* G_dc = 1 / (R' * length) from mathematical formulation */
        g11 = g22 = inst->TXLdcConduct;
        g12 = g21 = -inst->TXLdcConduct;
        
        /* Stamp the 4x4 conductance matrix */
        STAMP_M