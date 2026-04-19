# MOS1: Sensitivity and Distortion Analysis

_Generated 2026-04-12 04:18 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1sld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1sset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1dist.c`

# MOS1: Sensitivity and Distortion Analysis

## Technical Introduction

The MOS1 device model in Ngspice implements two critical advanced analysis capabilities through three dedicated C source files: sensitivity analysis and distortion analysis. These analyses provide essential insights for analog circuit design, enabling engineers to understand how circuit performance varies with manufacturing tolerances and to quantify nonlinear behavior that affects signal integrity.

*   **`mos1sld.c`**: Implements the **sensitivity load function** (`MOS1sLoad()`), which computes the sensitivity of circuit outputs (voltages, currents) to variations in MOS1 device parameters. It employs the adjoint method for computational efficiency, calculating derivatives of the drain current and small-signal parameters with respect to key model (VTO, KP, GAMMA, PHI) and instance (L, W) parameters. The results are stamped into a dedicated sensitivity matrix used by Ngspice's `.SENS` analysis.

*   **`mos1sset.c`**: Contains the **sensitivity setup function** (`MOS1sSetup()`), responsible for initializing the data structures required for sensitivity analysis. This includes allocating memory for sensitivity matrix pointers, assigning unique indices to each tunable parameter (both model and instance), and storing nominal parameter values for normalization. It ensures the analysis framework is correctly prepared before the simulation begins.

*   **`mos1dist.c`**: Implements the **distortion analysis function** (`MOS1disto()`), which characterizes the nonlinearity of the MOS1 transistor by computing harmonic and intermodulation distortion. It evaluates a Taylor series expansion of the drain current around the DC operating point, calculating second and third-order derivatives (e.g., `gm2`, `gm3`). These derivatives are used to predict harmonic distortion (HD2, HD3) and intermodulation distortion (IMD2, IMD3) for a given input signal amplitude, supporting Ngspice's `.DISTO` analysis.

Together, these files extend the core DC and transient simulation capabilities of the MOS1 model, providing the numerical machinery to answer critical design questions about parametric yield and linearity performance directly within the SPICE simulation environment.

## Mathematical Formulation

### 1. Sensitivity Analysis Formulation

#### Adjoint Method for Parameter Sensitivity
In SPICE circuit simulation, sensitivity analysis computes how circuit outputs change with respect to variations in device parameters. For the MOS1 model, the adjoint method is employed to efficiently compute these sensitivities. The fundamental equation for a linearized circuit is:

\[
\frac{\partial F}{\partial p} = \lambda^T \cdot \left( \frac{\partial G}{\partial p} \right) \cdot x
\]

where:
- \( F \) = objective function (output voltage or current)
- \( G \) = circuit conductance matrix \( G + j\omega C \) for AC analysis
- \( x \) = solution vector (node voltages)
- \( \lambda \) = adjoint vector from \( G^T \lambda = \frac{\partial F}{\partial x} \)
- \( p \) = device parameter (VTO, KP, L, W, etc.)

#### MOS1 Parameter Derivatives
The sensitivity computation requires derivatives of the MOSFET current and capacitance equations with respect to each parameter:

**Threshold Voltage Derivatives:**
\[
\frac{\partial V_{th}}{\partial VTO} = 1
\]
\[
\frac{\partial V_{th}}{\partial \gamma} = \sqrt{2\phi + V_{sb}} - \sqrt{2\phi}
\]
\[
\frac{\partial V_{th}}{\partial \phi} = \gamma \cdot \left( \frac{1}{\sqrt{2\phi + V_{sb}}} - \frac{1}{\sqrt{2\phi}} \right)
\]

**Drain Current Derivatives (Triode Region):**
\[
\frac{\partial I_d}{\partial VTO} = -\beta \cdot V_{ds}
\]
\[
\frac{\partial I_d}{\partial KP} = \frac{W}{L} \left[ (V_{gs} - V_{th})V_{ds} - \frac{V_{ds}^2}{2} \right]
\]
\[
\frac{\partial I_d}{\partial L} = -\frac{W}{L^2} \cdot KP \cdot \left[ (V_{gs} - V_{th})V_{ds} - \frac{V_{ds}^2}{2} \right]
\]
\[
\frac{\partial I_d}{\partial W} = \frac{1}{L} \cdot KP \cdot \left[ (V_{gs} - V_{th})V_{ds} - \frac{V_{ds}^2}{2} \right]
\]

**Drain Current Derivatives (Saturation Region):**
\[
\frac{\partial I_d}{\partial VTO} = -\beta \cdot (V_{gs} - V_{th})
\]
\[
\frac{\partial I_d}{\partial KP} = \frac{W}{2L} (V_{gs} - V_{th})^2
\]
\[
\frac{\partial I_d}{\partial L} = -\frac{W}{2L^2} \cdot KP \cdot (V_{gs} - V_{th})^2
\]
\[
\frac{\partial I_d}{\partial W} = \frac{1}{2L} \cdot KP \cdot (V_{gs} - V_{th})^2
\]

#### Small-Signal Parameter Sensitivities
For AC sensitivity analysis, derivatives of small-signal parameters are required:

**Transconductance Sensitivities:**
\[
\frac{\partial g_m}{\partial VTO} = 
\begin{cases}
0 & \text{(triode)} \\
-\beta & \text{(saturation)}
\end{cases}
\]
\[
\frac{\partial g_m}{\partial KP} = 
\begin{cases}
\frac{W}{L} V_{ds} & \text{(triode)} \\
\frac{W}{L} (V_{gs} - V_{th}) & \text{(saturation)}
\end{cases}
\]

**Output Conductance Sensitivities:**
\[
\frac{\partial g_{ds}}{\partial VTO} = 
\begin{cases}
0 & \text{(triode)} \\
0 & \text{(saturation)}
\end{cases}
\]
\[
\frac{\partial g_{ds}}{\partial \lambda} = \beta \cdot 
\begin{cases}
(V_{gs} - V_{th})V_{ds} - \frac{V_{ds}^2}{2} & \text{(triode)} \\
\frac{1}{2}(V_{gs} - V_{th})^2 & \text{(saturation)}
\end{cases}
\]

#### Chain Rule Application for Matrix Derivatives
The derivative of the system matrix with respect to parameter \( p \) is computed using the chain rule:

\[
\frac{\partial G}{\partial p} = \sum_i \left( \frac{\partial G}{\partial y_i} \right) \cdot \left( \frac{\partial y_i}{\partial p} \right)
\]

where \( y_i = \{g_m, g_{ds}, g_{mb}, C_{gs}, C_{gd}, C_{gb}, \ldots\} \) are the small-signal parameters.

### 2. Distortion Analysis Formulation

#### Taylor Series Expansion of Drain Current
The MOS1 drain current is expanded as a Taylor series around the DC operating point to analyze harmonic distortion:

\[
I_d(V_{gs} + \Delta v_{gs}, V_{ds} + \Delta v_{ds}, V_{bs} + \Delta v_{bs}) = I_{d0} + g_m \Delta v_{gs} + g_{mb} \Delta v_{bs} + g_{ds} \Delta v_{ds} + \frac{1}{2} g_{m2} \Delta v_{gs}^2 + \frac{1}{2} g_{mb2} \Delta v_{bs}^2 + \frac{1}{2} g_{ds2} \Delta v_{ds}^2 + g_{mgb} \Delta v_{gs} \Delta v_{bs} + g_{mgd} \Delta v_{gs} \Delta v_{ds} + g_{bgd} \Delta v_{bs} \Delta v_{ds} + \frac{1}{6} g_{m3} \Delta v_{gs}^3 + \cdots
\]

where:
- \( g_m = \frac{\partial I_d}{\partial V_{gs}} \) (first-order transconductance)
- \( g_{m2} = \frac{\partial^2 I_d}{\partial V_{gs}^2} \) (second-order transconductance)
- \( g_{m3} = \frac{\partial^3 I_d}{\partial V_{gs}^3} \) (third-order transconductance)
- \( g_{mgb} = \frac{\partial^2 I_d}{\partial V_{gs} \partial V_{bs}} \) (cross-term)

#### Second-Order Derivatives for MOS1 Model

**Triode Region Derivatives:**
\[
g_{m2} = \frac{\partial^2 I_d}{\partial V_{gs}^2} = 0
\]
\[
g_{ds2} = \frac{\partial^2 I_d}{\partial V_{ds}^2} = -\beta
\]
\[
g_{mgd} = \frac{\partial^2 I_d}{\partial V_{gs} \partial V_{ds}} = \beta
\]

**Saturation Region Derivatives:**
\[
g_{m2} = \frac{\partial^2 I_d}{\partial V_{gs}^2} = \beta
\]
\[
g_{ds2} = \frac{\partial^2 I_d}{\partial V_{ds}^2} = 0
\]
\[
g_{mgd} = \frac{\partial^2 I_d}{\partial V_{gs} \partial V_{ds}} = 0
\]

**Body Effect Derivatives:**
\[
g_{mb2} = \frac{\partial^2 I_d}{\partial V_{bs}^2} = -\frac{\gamma \beta}{4(2\phi + V_{sb})^{3/2}} \cdot 
\begin{cases}
V_{ds} & \text{(triode)} \\
(V_{gs} - V_{th}) & \text{(saturation)}
\end{cases}
\]
\[
g_{mgb} = \frac{\partial^2 I_d}{\partial V_{gs} \partial V_{bs}} = -\frac{\gamma \beta}{2\sqrt{2\phi + V_{sb}}} \cdot 
\begin{cases}
V_{ds} & \text{(triode)} \\
(V_{gs} - V_{th}) & \text{(saturation)}
\end{cases}
\]

#### Harmonic Distortion Coefficients
For a sinusoidal input \( v_{in}(t) = V_{in} \cos(\omega t) \), the harmonic distortion components are:

**Second Harmonic Distortion (HD2):**
\[
HD2 = \frac{1}{2} \cdot \frac{A_2}{A_1} \cdot V_{in}
\]
where \( A_1 = g_m \) and \( A_2 = \frac{1}{2} g_{m2} \).

**Third Harmonic Distortion (HD3):**
\[
HD3 = \frac{1}{4} \cdot \frac{A_3}{A_1} \cdot V_{in}^2
\]
where \( A_3 = \frac{1}{6} g_{m3} \).

#### Intermodulation Distortion (IMD)
For two-tone input \( v_{in}(t) = V_1 \cos(\omega_1 t) + V_2 \cos(\omega_2 t) \):

**Second-order IMD (IMD2):**
\[
IMD2 = \frac{A_2}{A_1} \cdot V_1 V_2 \quad \text{at frequencies } |\omega_1 \pm \omega_2|
\]

**Third-order IMD (IMD3):**
\[
IMD3 = \frac{3}{4} \cdot \frac{A_3}{A_1} \cdot V_1^2 V_2 \quad \text{at frequencies } |2\omega_1 \pm \omega_2|
\]
\[
IMD3 = \frac{3}{4} \cdot \frac{A_3}{A_1} \cdot V_1 V_2^2 \quad \text{at frequencies } |\omega_1 \pm 2\omega_2|
\]

#### Volterra Series Representation
For weakly nonlinear systems, the output current can be expressed using Volterra series:

\[
I_d(\omega) = H_1(\omega) \cdot V_{gs}(\omega) + \iint H_2(\omega_1, \omega_2) \cdot V_{gs}(\omega_1) V_{gs}(\omega_2) \, d\omega_1 d\omega_2 + \iiint H_3(\omega_1, \omega_2, \omega_3) \cdot V_{gs}(\omega_1) V_{gs}(\omega_2) V_{gs}(\omega_3) \, d\omega_1 d\omega_2 d\omega_3 + \cdots
\]

where:
- \( H_1(\omega) = g_m \) (linear transfer function)
- \( H_2(\omega_1, \omega_2) = \frac{1}{2} g_{m2} \) (second-order kernel)
- \( H_3(\omega_1, \omega_2, \omega_3) = \frac{1}{6} g_{m3} \) (third-order kernel)

#### Capacitance Nonlinearity
The gate capacitance nonlinearity also contributes to distortion. The Meyer capacitance model derivatives:

\[
\frac{\partial C_{gs}}{\partial V_{gs}} = 
\begin{cases}
0 & \text{(cutoff)} \\
\frac{2}{3} C_{ox} & \text{(saturation)} \\
\frac{1}{2} C_{ox} & \text{(triode)}
\end{cases}
\]

\[
\frac{\partial^2 C_{gs}}{\partial V_{gs}^2} = 0 \quad \text{(piecewise linear model)}
\]

## Convergence Analysis

### 1. Sensitivity Analysis Convergence

#### Adjoint System Solution Convergence
The adjoint system \( G^T \lambda = \frac{\partial F}{\partial x} \) must be solved for each output of interest. Convergence criteria:

\[
\| G^T \lambda^{(k)} - b \| < \epsilon_{\text{adjoint}}
\]
where \( b = \frac{\partial F}{\partial x} \) and \( \epsilon_{\text{adjoint}} = 10^{-6} \cdot \|b\| \).

The convergence rate follows:
\[
\| \lambda^{(k+1)} - \lambda^* \| \leq \kappa(G) \cdot \| \lambda^{(k)} - \lambda^* \|
\]
where \( \kappa(G) \) is the condition number of the conductance matrix.

#### Parameter Derivative Accuracy
The accuracy of sensitivity calculations depends on the finite-difference approximation when analytical derivatives are unavailable:

\[
\frac{\partial I_d}{\partial p} \approx \frac{I_d(p + \Delta p) - I_d(p - \Delta p)}{2\Delta p} + O(\Delta p^2)
\]

The optimal perturbation size balances truncation error and round-off error:
\[
\Delta p_{\text{opt}} = \sqrt{\epsilon_{\text{machine}} \cdot |p|}
\]
where \( \epsilon_{\text{machine}} \approx 2.2 \times 10^{-16} \) for double precision.

#### Chain Rule Accumulation Error
The total error in sensitivity computation accumulates through the chain rule:

\[
\epsilon_{\text{total}} = \sum_i \left| \frac{\partial G}{\partial y_i} \right| \cdot \epsilon_{y_i} + \sum_i \left| \frac{\partial y_i}{\partial p} \right| \cdot \epsilon_{G_i}
\]

where \( \epsilon_{y_i} \) is the error in small-signal parameter computation and \( \epsilon_{G_i} \) is the error in matrix element computation.

### 2. Distortion Analysis Convergence

#### Taylor Series Truncation Error
The Taylor series expansion truncation error for N-th order approximation:

\[
R_N = \frac{1}{(N+1)!} \cdot \left. \frac{\partial^{N+1} I_d}{\partial V^{N+1}} \right|_{\xi} \cdot (\Delta V)^{N+1}
\]
where \( \xi \) is between the operating point and the signal excursion.

For MOS1 Level 1 model, the third derivative \( g_{m3} = 0 \) in saturation, so the Taylor series terminates at second order, making the representation exact for quadratic characteristics.

#### Harmonic Balance Convergence
For distortion analysis using harmonic balance methods, the convergence criterion is:

\[
\| F(V^{(k)}) \| < \epsilon_{\text{HB}}
\]
where \( F(V) \) represents the circuit equations in frequency domain and \( \epsilon_{\text{HB}} = 10^{-4} \cdot \|F(V^{(0)})\| \).

The convergence rate for Newton-Raphson in harmonic balance:
\[
\| V^{(k+1)} - V^* \| \leq C \cdot \| V^{(k)} - V^* \|^2
\]
where \( C \) depends on the Lipschitz constant of the Jacobian.

#### Intermodulation Product Convergence
The convergence of intermodulation products requires sufficient harmonic truncation. The error due to truncating at harmonic M is:

\[
\epsilon_{\text{trunc}} = \sum_{|m|+|n|>M} |H_2(m\omega_1, n\omega_2)| \cdot V_1^{|m|} V_2^{|n|}
\]

For MOS1 with quadratic nonlinearity, only second-order products exist, so M=2 is sufficient.

#### Numerical Integration Error in Distortion
When computing distortion metrics via time-domain simulation, the local truncation error for trapezoidal integration affects results:

\[
\epsilon_{\text{LTE}} = \frac{h^3}{12} \cdot \left. \frac{d^3 I_d}{dt^3} \right|_{\tau}
\]

The time step must satisfy:
\[
h < \frac{1}{10 \cdot f_{\text{max}}}
\]
where \( f_{\text{max}} \) is the highest significant frequency component, including harmonics.

### 3. Combined Sensitivity-Distortion Convergence

#### Perturbation Analysis Stability
When computing distortion sensitivities \( \frac{\partial HD2}{\partial p} \), the finite-difference approach uses:

\[
\frac{\partial HD2}{\partial p} \approx \frac{HD2(p + \Delta p) - HD2(p - \Delta p)}{2\Delta p}
\]

The convergence requires:
1. \( \Delta p \) small enough for accurate derivative approximation
2. \( \Delta p \) large enough to avoid numerical noise
3. HD2(p) computation converged for each perturbation

#### Condition Number Effects
The condition number of the sensitivity matrix affects both sensitivity and distortion computations:

\[
\kappa(S) = \frac{\sigma_{\text{max}}(S)}{\sigma_{\text{min}}(S)}
\]

where \( S_{ij} = \frac{\partial F_i}{\partial p_j} \). Large \( \kappa(S) \) indicates ill-conditioning, requiring regularization:

\[
S_{\text{reg}} = S + \lambda I
\]
with \( \lambda = 10^{-8} \cdot \text{trace}(S) \).

#### Iterative Refinement for Sensitivity
For ill-conditioned systems, iterative refinement improves sensitivity accuracy:

1. Solve \( G \Delta x = -\frac{\partial G}{\partial p} x \)
2. Compute residual \( r = \frac{\partial G}{\partial p} x + G \Delta x \)
3. Solve \( G \delta x = r \)
4. Update \( \Delta x \leftarrow \Delta x + \delta x \)
5. Repeat until \( \|r\| < \epsilon_{\text{refine}} \)

#### Convergence Monitoring
The convergence of sensitivity-distortion analysis is monitored using:

1. **Parameter convergence:**
   \[
   \max_i \left| \frac{\partial F}{\partial p_i}^{(k)} - \frac{\partial F}{\partial p_i}^{(k-1)} \right| < \epsilon_{\text{param}}
   \]

2. **Distortion convergence:**
   \[
   \left| HD2^{(k)} - HD2^{(k-1)} \right| < \epsilon_{\text{dist}}
   \]

3. **Cross-sensitivity convergence:**
   \[
   \max_{i,j} \left| \frac{\partial^2 F}{\partial p_i \partial p_j}^{(k)} - \frac{\partial^2 F}{\partial p_i \partial p_j}^{(k-1)} \right| < \epsilon_{\text{cross}}
   \]

Typical tolerances: \( \epsilon_{\text{param}} = 10^{-6} \), \( \epsilon_{\text{dist}} = 10^{-4} \), \( \epsilon_{\text{cross}} = 10^{-8} \).

### 4. Numerical Stability Considerations

#### Small-Signal Parameter Computation
The computation of small-signal parameters near region boundaries requires regularization:

\[
g_m = \frac{\beta V_{ds}}{1 + \exp(-(V_{gs} - V_{th})/\eta)} \quad \text{(triode regularization)}
\]
\[
g_m = \frac{\beta (V_{gs} - V_{th})}{1 + \exp(-(V_{ds} - (V_{gs} - V_{th}))/\eta)} \quad \text{(saturation regularization)}
\]

with \( \eta = 10^{-3} \) V to ensure smooth transitions.

#### Derivative Computation Near Zero
For parameters near zero, derivatives are computed using:

\[
\frac{\partial I_d}{\partial p} = \frac{I_d(p + \delta) - I_d(p)}{\delta} \quad \text{when } |p| < \epsilon
\]

with \( \delta = \max(\epsilon, |p| \cdot 10^{-3}) \) and \( \epsilon = 10^{-12} \).

#### Harmonic Balance Matrix Conditioning
The harmonic balance Jacobian matrix condition number grows with harmonic order:

\[
\kappa(J_{\text{HB}}) \propto N^2
\]

where N is the number of harmonics. Preconditioning using:

\[
P = \text{diag}(G + j\omega_k C)^{-1}
\]

improves convergence for high harmonic orders.

#### Memory and Computational Complexity
The computational requirements scale as:
- Sensitivity analysis: \( O(N \cdot M) \) where N = number of nodes, M = number of parameters
- Distortion analysis: \( O(N \cdot H^2) \) where H = number of harmonics
- Combined analysis: \( O(N \cdot M \cdot H^2) \)

Memory requirements for sensitivity matrices: \( O(N \cdot M) \) for dense storage, \( O(N + M) \) for adjoint method.

## C Implementation

The mathematical formulations for sensitivity and distortion analysis are realized in Ngspice through dedicated C source files that extend the core MOS1 data structures and integrate with the SPICE simulation framework. The implementation directly maps the derivative equations to computational routines and matrix stamping operations.

### 1. Sensitivity Analysis Implementation (`mos1sld.c`)

#### Core Data Structures for Sensitivity Analysis

The sensitivity analysis implementation extends the standard MOS1 data structures with additional fields for parameter tracking and derivative storage:

```c
/* In mos1defs.h - Extended MOS1instance struct for sensitivity */
typedef struct sMOS1instance {
    /* ... Standard DC parameters ... */
    double MOS1vgs;        /* Gate-source voltage */
    double MOS1vds;        /* Drain-source voltage */
    double MOS1vth;        /* Threshold voltage */
    double MOS1beta;       /* Transconductance coefficient */
    double MOS1l;          /* Channel length */
    double MOS1w;          /* Channel width */
    int MOS1mode;          /* Operating mode: 0=cutoff, 1=triode, 2=saturation */
    
    /* Small-signal parameters (pointers to state vector) */
    double *MOS1gm;        /* Transconductance (∂Id/∂Vgs) */
    double *MOS1gds;       /* Output conductance (∂Id/∂Vds) */
    double *MOS1gmb;       /* Body transconductance (∂Id/∂Vbs) */
    
    /* Sensitivity-specific fields */
    double **MOS1senParmPtr; /* Matrix pointers for sensitivity parameters */
    int MOS1lSenParam;     /* Sensitivity parameter index for L */
    int MOS1wSenParam;     /* Sensitivity parameter index for W */
    int MOS1adSenParam;    /* Sensitivity parameter index for AD */
    /* ... other instance parameter sensitivity indices */
    
    /* Derivative storage for chain rule */
    double MOS1dId_dVTO;   /* ∂Id/∂VTO */
    double MOS1dId_dKP;    /* ∂Id/∂KP */
    double MOS1dId_dL;     /* ∂Id/∂L */
    double MOS1dId_dW;     /* ∂Id/∂W */
    double MOS1dId_dGAMMA; /* ∂Id/∂GAMMA */
    double MOS1dId_dPHI;   /* ∂Id/∂PHI */
} MOS1instance;

/* Extended MOS1model struct for sensitivity */
typedef struct sMOS1model {
    /* ... Standard model parameters ... */
    double MOS1vt0;        /* Zero-bias threshold voltage */
    double MOS1kp;         /* Transconductance parameter */
    double MOS1gamma;      /* Body effect parameter */
    double MOS1phi;        /* Surface potential */
    
    /* Sensitivity-specific fields */
    int MOS1vt0SenParam;   /* Sensitivity parameter index for VTO */
    int MOS1kpSenParam;    /* Sensitivity parameter index for KP */
    int MOS1gammaSenParam; /* Sensitivity parameter index for GAMMA */
    int MOS1phiSenParam;   /* Sensitivity parameter index for PHI */
    /* ... other model parameter sensitivity indices */
} MOS1model;
```

#### Sensitivity Load Function Implementation

The `MOS1sLoad()` function implements the adjoint method for sensitivity computation, mapping directly to the mathematical formulation:

```c
int MOS1sLoad(GENmodel *inModel, CKTcircuit *ckt) {
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    
    /* Loop through all models and instances */
    for(; model != NULL; model = model->MOS1nextModel) {
        for(inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            
            /* Extract operating point voltages */
            double Vgs = ckt->CKTrhs[inst->MOS1gNode] - ckt->CKTrhs[inst->MOS1sNode];
            double Vds = ckt->CKTrhs[inst->MOS1dNode] - ckt->CKTrhs[inst->MOS1sNode];
            double Vbs = ckt->CKTrhs[inst->MOS1bNode] - ckt->CKTrhs[inst->MOS1sNode];
            
            /* Extract device parameters */
            double Vth = inst->MOS1vth;
            double beta = inst->MOS1beta;
            double L = inst->MOS1l;
            double W = inst->MOS1w;
            double gamma = model->MOS1gamma;
            double phi = model->MOS1phi;
            
            /* Map mathematical derivatives to C code */
            
            /* 1. ∂Id/∂VTO = -gm·(∂Vth/∂VTO) where ∂Vth/∂VTO = 1 */
            double dId_dVTO = -(*inst->MOS1gm);  /* Direct mapping: -gm */
            inst->MOS1dId_dVTO = dId_dVTO;
            
            /* 2. ∂Id/∂KP calculation based on operating region */
            double dId_dKP = 0.0;
            if(inst->MOS1mode == 1) { /* Triode region */
                /* Mathematical: (W/L)·[(Vgs-Vth)Vds - Vds²/2] */
                dId_dKP = (W/L) * ((Vgs - Vth) * Vds - 0.5 * Vds * Vds);
            } else if(inst->MOS1mode == 2) { /* Saturation region */
                /* Mathematical: (W/2L)·(Vgs-Vth)² */
                dId_dKP = (W/(2.0 * L)) * (Vgs - Vth) * (Vgs - Vth);
            }
            inst->MOS1dId_dKP = dId_dKP;
            
            /* 3. ∂Id/∂L using chain rule: -(W/L²)·KP·[(Vgs-Vth)Vds - Vds²/2] */
            double dId_dL = -dId_dKP * (W/(L * L));
            inst->MOS1dId_dL = dId_dL;
            
            /* 4. ∂Id/∂W using chain rule: (1/L)·KP·[(Vgs-Vth)Vds - Vds²/2] */
            double dId_dW = dId_dKP * (1.0/(L * W));
            inst->MOS1dId_dW = dId_dW;
            
            /* 5. ∂Id/∂GAMMA = ∂Id/∂Vth · ∂Vth/∂GAMMA */
            /* ∂Vth/∂GAMMA = √(2φ + Vsb) - √(2φ) */
            double sqrt_term = 0.0;
            if((2.0 * phi + Vbs) < 1e-12) {
                sqrt_term = sqrt(1e-12) - sqrt(2.0 * phi);
            } else {
                sqrt_term = sqrt(2.0 * phi + Vbs) - sqrt(2.0 * phi);
            }
            double dId_dGAMMA = -(*inst->MOS1gm) * sqrt_term;
            inst->MOS1dId_dGAMMA = dId_dGAMMA;
            
            /* 6. ∂Id/∂PHI = ∂Id/∂Vth · ∂Vth/∂PHI */
            /* ∂Vth/∂PHI = γ·[1/√(2φ + Vsb) - 1/√(2φ)] */
            double dVth_dPHI = 0.0;
            if((2.0 * phi + Vbs) < 1e-12) {
                dVth_dPHI = gamma * (1.0/sqrt(1e-12) - 1.0/sqrt(2.0 * phi));
            } else {
                dVth_dPHI = gamma * (1.0/sqrt(2.0 * phi + Vbs) - 1.0/sqrt(2.0 * phi));
            }
            double dId_dPHI = -(*inst->MOS1gm) * dVth_dPHI;
            inst->MOS1dId_dPHI = dId_dPHI;
            
            /* Stamp sensitivity matrix using adjoint method */
            /* Mathematical: ∂F/∂p = λᵀ·(∂G/∂p)·x */
            
            /* For sensitivity w.r.t. VTO */
            if(model->MOS1vt0SenParam >= 0) {
                /* Stamp ∂Id/∂VTO into sensitivity matrix */
                ckt->CKTsenInfo->SEN_Sap[inst->MOS1dNode][model->MOS1vt0SenParam] += dId_dVTO;
                ckt->CKTsenInfo->SEN_Sap[inst->MOS1sNode][model->MOS1vt0SenParam] -= dId_dVTO;
            }
            
            /* For sensitivity w.r.t. L */
            if(inst->MOS1lSenParam >= 0) {
                ckt->CKTsenInfo->SEN_Sap[inst->MOS1dNode][inst->MOS1lSenParam] += dId_dL;
                ckt->CKTsenInfo->SEN_Sap[inst->MOS1sNode][inst->MOS1lSenParam] -= dId_dL;
            }
            
            /* For sensitivity w.r.t. W */
            if(inst->MOS1wSenParam >= 0) {
                ckt->CKTsenInfo->SEN_Sap[inst->MOS1dNode][inst->MOS1wSenParam] += dId_dW;
                ckt->CKTsenInfo->SEN_Sap[inst->MOS1sNode][inst->MOS1wSenParam] -= dId_dW;
            }
            
            /* Repeat for other parameters: KP, GAMMA, PHI, etc. */
            
            /* Chain rule implementation for matrix derivatives */
            /* Mathematical: ∂G/∂p = Σ_i (∂G/∂y_i)·(∂y_i/∂p) */
            
            /* Example: ∂g_m/∂VTO */
            double dgm_dVTO = 0.0;
            if(inst->MOS1mode == 2) { /* Saturation only */
                dgm_dVTO = -beta;  /* ∂g_m/∂VTO = -β */
            }
            
            /* Stamp ∂g_m/∂VTO into appropriate matrix positions */
            if(dgm_dVTO != 0.0 && model->MOS1vt0SenParam >= 0) {
                /* Affect drain-gate and source-gate conductances */
                *inst->MOS1drainGatePtr += dgm_dVTO;
                *inst->MOS1sourceGatePtr -= dgm_dVTO;
            }
        }
    }
    return OK;
}
```

### Sensitivity Setup Function (`mos1sset.c`)

The setup function initializes sensitivity data structures and parameter indices:

```c
int MOS1sSetup(GENmodel *inModel, CKTcircuit *ckt) {
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    
    /* Allocate sensitivity structures if not already done */
    if(ckt->CKTsenInfo == NULL) {
        ckt->CKTsenInfo = SENinit();
    }
    
    /* Calculate total number of sensitivity parameters */
    int numModelParams = 10;  /* VTO, KP, GAMMA, PHI, LAMBDA, RD, RS, CBD, CBS, IS */
    int numInstanceParams = 8; /* L, W, AD, AS, PD, PS, NRD, NRS */
    int numParams = numModelParams + numInstanceParams;
    
    /* Allocate memory for sensitivity matrix pointers */
    ckt->CKTsenInfo->SENsize += numParams * sizeof(double*);
    
    /* Initialize parameter indices */
    for(; model != NULL; model = model->MOS1nextModel) {
        /* Model parameter sensitivity indices */
        model->MOS1vt0SenParam = ckt->CKTsenInfo->SENparms++;
        model->MOS1kpSenParam = ckt->CKTsenInfo->SENparms++;
        model->MOS1gammaSenParam = ckt->CKTsenInfo->SENparms++;
        model->MOS1phiSenParam = ckt->CKTsenInfo->SENparms++;
        /* ... other model parameters */
        
        for(inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            /* Instance parameter sensitivity indices */
            inst->MOS1lSenParam = ckt->CKTsenInfo->SENparms++;
            inst->MOS1wSenParam = ckt->CKTsenInfo->SENparms++;
            inst->MOS1adSenParam = ckt->CKTsenInfo->SENparms++;
            inst->MOS1asSenParam = ckt->CKTsenInfo->SENparms++;
            /* ... other instance parameters */
            
            /* Store nominal values for normalization */
            inst->MOS1lNominal = inst->MOS1l;
            inst->MOS1wNominal = inst->MOS1w;
            inst->MOS1adNominal = inst->MOS1ad;
            inst->MOS1asNominal = inst->MOS1as;
            
            /* Allocate and initialize sensitivity matrix pointers */
            inst->MOS1senParmPtr = (double**)MALLOC(numParams * sizeof(double*));
            for(int i = 0; i < numParams; i++) {
                /* Create sparse matrix elements for sensitivity parameters */
                inst->MOS1senParmPtr[i] = SMPmakeElt(ckt->CKTsenInfo->SENmatrix, 
                                                    inst->MOS1dNode, i);
                /* Additional pointers for other nodes if needed */
            }
        }
    }
    
    /* Set up adjoint system if needed */
    if(ckt->CKTsenInfo->SENadjoint) {
        /* Allocate adjoint vector */
        ckt->CKTsenInfo->SENadjVec = (double*)MALLOC(ckt->CKTmaxEqNum * sizeof(double));
    }
    
    return OK;
}
```

### 2. Distortion Analysis Implementation (`mos1dist.c`)

#### Distortion Data Structures

```c
/* In mos1defs.h - Extended for distortion analysis */
typedef struct sMOS1instance {
    /* ... Existing fields ... */
    
    /* Distortion-specific fields */
    double MOS1gm2;        /* Second-order transconduct