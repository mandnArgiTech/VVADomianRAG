# LTRA: Lossy Transmission Line Convolution and Accept Logic

_Generated 2026-04-13 02:34 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltradefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltrapar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltratemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltraset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltraload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltraacct.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltratrun.c`

# Chapter: LTRA: Lossy Transmission Line Convolution and Accept Logic

## Technical Introduction

This chapter documents the implementation of the LTRA (Lossy Transmission Line) model within the Ngspice circuit simulator, a sophisticated distributed RLCG line model essential for high-speed digital and RF circuit simulation. The implementation spans seven core C source files that collectively transform the continuous Telegrapher's equations into a discrete-time, numerically stable circuit model compatible with SPICE's Modified Nodal Analysis (MNA) framework.

The file `ltradefs.h` defines the fundamental data structures `sLTRAmodel` and `sLTRAinstance`, which encapsulate the distributed line parameters (R, L, G, C per unit length), convolution history buffers, Padé approximation coefficients, and sparse matrix pointers. The parameter processing logic in `ltrapar.c` maps SPICE netlist parameters to these internal C structures. The computational core resides in `ltraload.c`, which implements the `LTRAload()` function. This function evaluates the Norton companion model derived from the convolution integral formulation of the Telegrapher's equations, computing equivalent conductances and history currents via recursive convolution, then stamping these contributions into the circuit's Jacobian matrix during Newton-Raphson iteration. The critical history management and state update logic is implemented in `ltraacct.c` through the `LTRAaccept()` function, which maintains circular buffers of past voltages for the convolution integrals and updates the recursive convolution states. Time-step control and Local Truncation Error (LTE) estimation are handled by `ltratrun.c`, which implements adaptive time-stepping based on Richardson extrapolation of the convolution integrals. The setup and initialization routines in `ltraset.c` allocate the extensive memory required for history buffers, Padé coefficients, and convolution states, while `ltratemp.c` manages temperature scaling of the distributed line parameters. Together, these files implement a rigorous, computationally efficient solution to lossy transmission line simulation using convolution-based time-domain analysis with Padé approximation for the frequency-domain transfer functions.

## Mathematical Formulation

The LTRA (Lossy Transmission Line) model in Ngspice implements a rigorous solution to the Telegrapher's equations for distributed RLCG lines, employing convolution-based time-domain analysis with Padé approximation for computational efficiency. The mathematical formulation bridges frequency-domain transmission line theory with time-domain circuit simulation through the Modified Nodal Analysis (MNA) framework.

### 1.1 Telegrapher's Equations and Frequency-Domain Solution

The fundamental equations governing voltage and current propagation along a lossy transmission line are:

**Telegrapher's Equations in Frequency Domain:**
\[
\frac{\partial V(x,s)}{\partial x} = -[R(s) + sL(s)]I(x,s)
\]
\[
\frac{\partial I(x,s)}{\partial x} = -[G(s) + sC(s)]V(x,s)
\]

where:
- \(R\) = resistance per unit length (Ω/m)
- \(L\) = inductance per unit length (H/m)
- \(G\) = conductance per unit length (S/m)
- \(C\) = capacitance per unit length (F/m)
- \(s = \sigma + j\omega\) = complex frequency variable

**Propagation Constant:**
\[
\gamma(s) = \sqrt{(R + sL)(G + sC)}
\]

**Characteristic Impedance:**
\[
Z_0(s) = \sqrt{\frac{R + sL}{G + sC}}
\]

**ABCD Matrix Representation:**
For a transmission line of length \(l\), the two-port network is described by:
\[
\begin{bmatrix}
V_1(s) \\
I_1(s)
\end{bmatrix}
=
\begin{bmatrix}
\cosh(\gamma l) & Z_0 \sinh(\gamma l) \\
\frac{\sinh(\gamma l)}{Z_0} & \cosh(\gamma l)
\end{bmatrix}
\begin{bmatrix}
V_2(s) \\
-I_2(s)
\end{bmatrix}
\]

### 1.2 Time-Domain Convolution Formulation

The frequency-domain ABCD matrix is transformed to time-domain convolution integrals for SPICE simulation:

**Port Current Relations:**
\[
i_1(t) = \int_0^t h_1'(\tau)v_1(t-\tau)d\tau + \int_0^t h_2(\tau)v_2(t-\tau)d\tau
\]
\[
i_2(t) = \int_0^t h_2(\tau)v_1(t-\tau)d\tau + \int_0^t h_1'(\tau)v_2(t-\tau)d\tau
\]

where the impulse responses are inverse Laplace transforms of:
\[
H_1'(s) = Y_0(s)\coth(\gamma(s)l)
\]
\[
H_2(s) = -Y_0(s)\operatorname{csch}(\gamma(s)l)
\]
with \(Y_0(s) = 1/Z_0(s)\).

### 1.3 Padé Approximation for Recursive Convolution

Direct computation of convolution integrals is computationally expensive. Ngspice employs Padé approximation to express the transfer functions as rational functions:

**Rational Approximation:**
\[
H(s) \approx \sum_{k=1}^N \frac{r_k}{s - p_k}
\]

where \(p_k\) are poles and \(r_k\) are residues obtained via vector fitting algorithms. This enables efficient recursive convolution:

**Recursive Convolution Algorithm:**
For each exponential term \(r_k e^{p_k t}\), the convolution integral can be computed recursively:
\[
y[n] = e^{p_k \Delta t} y[n-1] + r_k \int_{t_{n-1}}^{t_n} e^{p_k(t_n-\tau)} x(\tau) d\tau
\]

### 1.4 Norton Companion Model for MNA Integration

For integration into SPICE's Newton-Raphson solver, the convolution relations are discretized to form a Norton companion model:

**Discrete-Time Representation:**
\[
i_1[n] = G_{eq} v_1[n] + I_{hist1}[n]
\]
\[
i_2[n] = G_{eq} v_2[n] + I_{hist2}[n]
\]

where:
- \(G_{eq} = \sqrt{C/L} \coth(\sqrt{LC} \cdot l \cdot s)|_{s \to \infty}\) (high-frequency limit)
- \(I_{hist}[n]\) = history current computed via recursive convolution

**MNA Matrix Stamp:**
The companion model contributes to the circuit Jacobian as:
\[
\begin{bmatrix}
G_{eq} & -G_{eq} & 0 & 0 \\
-G_{eq} & G_{eq} & 0 & 0 \\
0 & 0 & G_{eq} & -G_{eq} \\
0 & 0 & -G_{eq} & G_{eq}
\end{bmatrix}
\begin{bmatrix}
v_{1+} \\
v_{1-} \\
v_{2+} \\
v_{2-}
\end{bmatrix}
+
\begin{bmatrix}
-I_{hist1} \\
I_{hist1} \\
-I_{hist2} \\
I_{hist2}
\end{bmatrix}
=
\begin{bmatrix}
0 \\
0 \\
0 \\
0
\end{bmatrix}
\]

### 1.5 Delay Extraction and Breakpoint Generation

The propagation delay \(T_d = l\sqrt{LC}\) is explicitly tracked for accurate transient simulation. Breakpoints are generated at:
\[
t_{break} = t_{history} + k \cdot T_d, \quad k = 1,2,\ldots
\]
to ensure proper sampling of the convolution window.

## Convergence Analysis

The LTRA model presents unique convergence challenges due to its distributed nature, infinite-dimensional state space, and the convolution-based formulation. Convergence analysis focuses on the numerical stability of recursive convolution and the conditioning of the companion model.

### 2.1 Newton-Raphson Formulation with Convolution Terms

The circuit equations including LTRA contributions are:
\[
\mathbf{F}(\mathbf{x}) = \mathbf{G}\mathbf{x} + \mathbf{I}_{hist}(\mathbf{x}) - \mathbf{b} = \mathbf{0}
\]

where \(\mathbf{I}_{hist}\) represents the history-dependent convolution terms. The Newton-Raphson update is:
\[
\left[\mathbf{G} + \frac{\partial \mathbf{I}_{hist}}{\partial \mathbf{x}}\right]^{(k)} \Delta \mathbf{x}^{(k)} = -\mathbf{F}(\mathbf{x}^{(k)})
\]

The Jacobian term \(\partial \mathbf{I}_{hist}/\partial \mathbf{x}\) is approximated using the companion model conductance \(G_{eq}\).

### 2.2 Stability of Recursive Convolution

The recursive convolution algorithm is numerically stable if and only if:
\[
|e^{p_k \Delta t}| < 1 \quad \text{for all poles } p_k
\]

This requires all poles to have negative real parts (\(\Re(p_k) < 0\)), which is guaranteed by the vector fitting algorithm for passive systems.

**Stability Criterion:**
\[
\Delta t < \min_k \frac{1}{|\Re(p_k)|}
\]

### 2.3 Local Truncation Error (LTE) Analysis

The LTE for convolution integrals arises from three sources:

**1. Padé Approximation Error:**
\[
\epsilon_{pade} = O\left((s\Delta t)^{2N+1}\right)
\]
where \(N\) is the Padé approximation order.

**2. Convolution Truncation Error:**
\[
\epsilon_{trunc} = O\left(e^{-\alpha T_{window}}\right)
\]
where \(\alpha = \min |\Re(p_k)|\) and \(T_{window}\) is the convolution window length.

**3. Numerical Integration Error (Trapezoidal Rule):**
\[
\epsilon_{int} = \frac{\Delta t^3}{12} \left|\frac{d^3y}{dt^3}\right|
\]

**Total LTE Estimate:**
\[
LTE = \max\left(\epsilon_{pade}, \epsilon_{trunc}, \epsilon_{int}\right)
\]

### 2.4 Time Step Control Algorithm

The time step is controlled to maintain:
\[
LTE \leq \text{reltol} \cdot \max(|y|, \text{abstol})
\]

**Adaptive Time-Stepping Logic:**
1. Compute LTE using Richardson extrapolation:
   \[
   \epsilon = \frac{|y(t_n, \Delta t) - y(t_n, \Delta t/2)|}{2^p - 1}
   \]
   where \(p = 2\) for trapezoidal integration.

2. If \(\epsilon > \text{tolerance}\), reduce time step:
   \[
   \Delta t_{new} = 0.9 \cdot \Delta t_{old} \cdot \sqrt{\frac{\text{tolerance}}{\epsilon}}
   \]

3. Enbreakpoint constraints:
   \[
   \Delta t \leq \min(T_d/100, 1/(2f_{max}), \tau_{min}/10)
   \]
   where \(\tau_{min} = 1/\max|\Re(p_k)|\).

### 2.5 Convergence Criteria for LTRA

**Voltage Convergence:**
\[
|\Delta v_{port}| \leq \text{VNTOL} + \text{RELTOL} \cdot \max(|v_{port}|, |v_{port}^{old}|)
\]

**Current Convergence:**
\[
|\Delta i_{port}| \leq \text{ABSTOL} + \text{RELTOL} \cdot \max(|i_{port}|, |i_{port}^{old}|)
\]

**History Consistency Check:**
\[
\frac{|v_{history}[n] - v_{interpolated}[n]|}{\max(|v_{history}[n]|, \text{CHGTOL})} \leq \text{RELTOL}
\]

### 2.6 Numerical Challenges and Mitigations

**1. Stiffness from Wide Pole Distribution:**
The Padé approximation generates poles spanning multiple decades. This stiffness is managed by:
- Pole clustering to reduce effective state dimension
- Implicit integration for fast poles (\(\Re(p_k) \ll -1/\Delta t\))
- Explicit integration for slow poles (\(\Re(p_k) \approx -1/\Delta t\))

**2. Delay-Induced Discontinuities:**
Sudden changes at delay boundaries can cause convergence failure. Mitigations include:
- Breakpoint generation at \(t = t_{history} + kT_d\)
- Smoothing functions for delay transitions
- Adaptive order reduction near discontinuities

**3. Memory Effects and History Management:**
The convolution window length \(T_{window}\) must balance accuracy and memory:
\[
T_{window} = \max(5\tau_{max}, 2T_d)
\]
where \(\tau_{max} = 1/\min|\Re(p_k)|\).

**4. Companion Model Conditioning:**
The Norton conductance \(G_{eq}\) can become extremely large or small, causing ill-conditioning. Regularization is applied:
\[
G_{eq}' = \max(\min(G_{eq}, G_{max}), G_{min})
\]
with \(G_{min} = 10^{-12}\) S, \(G_{max} = 10^{12}\) S.

### 2.7 Accept Logic and State Management

The "accept" phase updates history buffers and convolution states:

**State Update Equations:**
\[
x_k[n] = e^{p_k \Delta t} x_k[n-1] + r_k \int_{t_{n-1}}^{t_n} e^{p_k(t_n-\tau)} v(\tau) d\tau
\]

**Circular Buffer Management:**
- History buffer size: \(N_{hist} = \lceil T_{window}/\Delta t_{min} \rceil\)
- Pointer update: \(ptr_{new} = (ptr_{old} + 1) \mod N_{hist}\)
- Oldest data overwritten when buffer full

### 2.8 Convergence Acceleration Techniques

**1. Source Stepping for Initial Conditions:**
\[
v_{source}(t) = \alpha(t) v_{final}, \quad \alpha(0)=0, \alpha(T_{ramp})=1
\]

**2. Dynamic Padé Order Reduction:**
\[
N_{effective} = \max\left(4, \left\lfloor \frac{\log(\omega_{max}/\omega_{min})}{\log(2)} \right\rfloor \right)
\]
based on current signal bandwidth.

**3. Adaptive Convolution Window:**
\[
T_{window}(t) = 
\begin{cases}
5\tau_{min} & \text{if } t < 2T_d \\
\max(5\tau_{min}, 2T_d) & \text{otherwise}
\end{cases}
\]

### 2.9 Error Recovery Strategies

When convergence fails:

1. **Time Step Reduction:** \(\Delta t \leftarrow 0.5 \Delta t\)
2. **History Reinitialization:** Reset convolution states using cubic spline interpolation
3. **Padé Coefficient Recalculation:** If poles migrate near imaginary axis
4. **Companion Model Fallback:** Use simple LC model with loss approximation

### 2.10 Performance-Optimized Convergence

The LTRA implementation employs several optimizations for convergence speed:

1. **Exponential Window Truncation:** Terms with \(e^{p_k t} < 10^{-6}\) are discarded
2. **Pole Clustering:** Nearby poles grouped to reduce state dimension
3. **Lookup Tables:** Precomputed \(e^{p_k \Delta t}\) for common \(\Delta t\) values
4. **Selective State Update:** Only update states with significant contribution

The convergence analysis demonstrates that the LTRA model, while mathematically complex, achieves robust numerical performance through careful management of convolution errors, adaptive time-stepping, and regularization of ill-conditioned matrices. The accept logic ensures proper state management between time steps, while the breakpoint generation guarantees accurate sampling of delay effects. These techniques enable efficient simulation of lossy transmission lines in high-speed digital and RF circuits within the SPICE framework.

## C Implementation

### 1. Core Data Structures and Memory Management

The LTRA model implementation in Ngspice follows a sophisticated architecture that maps directly to the mathematical formulation of lossy transmission lines. The core data structures defined in `ltradefs.h` establish the foundation for the convolution-based time-domain simulation.

#### 1.1 Instance Structure (`sLTRAinstance`)

The `LTRAinstance` structure encapsulates all state information for a single transmission line instance:

```c
typedef struct sLTRAinstance {
    /* Terminal nodes - 2-port device with MNA branch equations */
    int LTRAposNode1;      /* Positive node of port 1 (external) */
    int LTRAnegNode1;      /* Negative node of port 1 (external) */
    int LTRAposNode2;      /* Positive node of port 2 (external) */
    int LTRAnegNode2;      /* Negative node of port 2 (external) */
    int LTRAintNode1;      /* Internal node for branch equation 1 */
    int LTRAintNode2;      /* Internal node for branch equation 2 */
    
    /* Distributed line parameters - map directly to Telegrapher's equations */
    double LTRAr;          /* Resistance per unit length (Ω/m) - R in dV/dx = -(R+sL)I */
    double LTRAl;          /* Inductance per unit length (H/m) - L in dV/dx = -(R+sL)I */
    double LTRAg;          /* Conductance per unit length (S/m) - G in dI/dx = -(G+sC)V */
    double LTRAc;          /* Capacitance per unit length (F/m) - C in dI/dx = -(G+sC)V */
    double LTRAlen;        /* Physical length (m) */
    double LTRAd;          /* Total delay = len * sqrt(l*c) (s) - critical for convolution window */
    
    /* Convolution history buffers - implement i(t) = ∫h(τ)v(t-τ)dτ */
    double *LTRAh1dash;    /* Impulse response h₁'(t) buffer - maps to H₁'(s)=Y₀coth(γl) */
    double *LTRAh2;        /* Impulse response h₂(t) buffer - maps to H₂(s)=-Y₀csch(γl) */
    double *LTRAh3;        /* Impulse response h₃(t) buffer - maps to H₃(s)=Z₀tanh(γl/2) */
    double *LTRAtimeHistory; /* Time points in history buffer - circular buffer for convolution */
    double *LTRAsignalHistory1; /* Voltage history at port 1 - stores v₁(t-τ) for convolution */
    double *LTRAsignalHistory2; /* Voltage history at port 2 - stores v₂(t-τ) for convolution */
    int LTRAhistorySize;   /* Current size of history buffer */
    int LTRAhistoryPointer; /* Circular buffer pointer - implements sliding window */
    
    /* Padé approximation coefficients - implement H(s) ≈ Σ rₖ/(s-pₖ) */
    double *LTRApoles;     /* Poles pₖ for rational approximation */
    double *LTRAresidues;  /* Residues rₖ for rational approximation */
    int LTRApadeOrder;     /* Order of Padé approximation (typically 8-12) */
    
    /* State vectors for recursive convolution - implement y[n]=exp(pₖΔt)y[n-1]+... */
    double *LTRAconvState1; /* Convolution state variables for mode 1 */
    double *LTRAconvState2; /* Convolution state variables for mode 2 */
    
    /* Sparse matrix pointers - map to MNA matrix entries */
    double *LTRAptrPos1Pos1; /* G[1+,1+] */
    double *LTRAptrPos1Neg1; /* G[1+,1-] */
    double *LTRAptrNeg1Pos1; /* G[1-,1+] */
    double *LTRAptrNeg1Neg1; /* G[1-,1-] */
    double *LTRAptrPos2Pos2; /* G[2+,2+] */
    double *LTRAptrPos2Neg2; /* G[2+,2-] */
    double *LTRAptrNeg2Pos2; /* G[2-,2+] */
    double *LTRAptrNeg2Neg2; /* G[2-,2-] */
    double *LTRAbrEq1;     /* Branch equation 1 pointer */
    double *LTRAbrEq2;     /* Branch equation 2 pointer */
    
    /* State vector indices */
    int LTRAstateIndex1;   /* State vector index for port 1 current */
    int LTRAstateIndex2;   /* State vector index for port 2 current */
    
    /* Companion model coefficients - implement i[n]=G_eq v[n]+I_history[n] */
    double LTRAgeff;       /* Effective conductance for companion model */
    double LTRAb1, LTRAb2; /* History source coefficients */
    
    /* Flags and control */
    int LTRAlteFlag;       /* LTE calculation flag */
    double LTRAprevStep;   /* Previous time step for LTE calculation */
} LTRAinstance;
```

#### 1.2 Model Structure (`sLTRAmodel`)

The model structure contains parameters shared among multiple instances:

```c
typedef struct sLTRAmodel {
    int LTRAtype;          /* N-type model identifier */
    double LTRArsh;        /* Sheet resistance */
    double LTRAdefaultL;   /* Default inductance per square */
    double LTRAtnom;       /* Nominal temperature */
    double LTRAtempCoeff1; /* First-order temperature coefficient */
    double LTRAtempCoeff2; /* Second-order temperature coefficient */
    struct sLTRAmodel *LTRAnextModel; /* Linked list pointer */
    LTRAinstance *LTRAinstances; /* Instance list */
} LTRAmodel;
```

### 2. Setup and Initialization (`ltraset.c`)

The setup function `LTRAsetup()` performs critical initialization that maps mathematical concepts to C data structures:

```c
int LTRAsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    LTRAmodel *model = (LTRAmodel *)inModel;
    LTRAinstance *inst;
    
    for (; model != NULL; model = model->LTRAnextModel) {
        for (inst = model->LTRAinstances; inst != NULL; 
             inst = inst->LTRAnextInstance) {
            
            /* Allocate Sparse Matrix Pointers for 2-port + branches */
            /* Maps to 4x4 MNA system: [V₁⁺ V₁⁻ V₂⁺ V₂⁻]^T */
            inst->LTRAptrPos1Pos1 = SMPmakeElt(matrix, inst->LTRAposNode1, 
                                               inst->LTRAposNode1);
            inst->LTRAptrPos1Neg1 = SMPmakeElt(matrix, inst->LTRAposNode1, 
                                               inst->LTRAnegNode1);
            /* ... allocate all 16 matrix entries for 4x4 system ... */
            
            /* Allocate branch equation pointers for current states */
            /* Maps to branch equations: i₁ = f(v₁, v₂, history) */
            inst->LTRAintNode1 = ckt->CKTnumStates++;
            inst->LTRAintNode2 = ckt->CKTnumStates++;
            inst->LTRAbrEq1 = SMPmakeElt(matrix, inst->LTRAintNode1, 
                                         inst->LTRAintNode1);
            inst->LTRAbrEq2 = SMPmakeElt(matrix, inst->LTRAintNode2, 
                                         inst->LTRAintNode2);
            
            /* Allocate history buffers for convolution integrals */
            /* Maps to i(t) = ∫₀ᵗ h(τ)v(t-τ)dτ */
            inst->LTRAtimeHistory = TMALLOC(double, MAX_HISTORY_SIZE);
            inst->LTRAsignalHistory1 = TMALLOC(double, MAX_HISTORY_SIZE);
            inst->LTRAsignalHistory2 = TMALLOC(double, MAX_HISTORY_SIZE);
            
            /* Allocate Padé coefficient arrays for H(s) ≈ Σ rₖ/(s-pₖ) */
            inst->LTRApoles = TMALLOC(double, PADE_ORDER);
            inst->LTRAresidues = TMALLOC(double, PADE_ORDER);
            
            /* Allocate convolution state vectors for recursive algorithm */
            /* Maps to y[n] = exp(pₖΔt)y[n-1] + rₖ∫ exp(pₖ(tₙ-τ))x(τ)dτ */
            inst->LTRAconvState1 = TMALLOC(double, PADE_ORDER);
            inst->LTRAconvState2 = TMALLOC(double, PADE_ORDER);
            
            /* Calculate Padé coefficients - numerical approximation of H(s) */
            LTRACalcPadeCoefficients(inst);
            
            /* Initialize state vector indices for Newton-Raphson */
            inst->LTRAstateIndex1 = *states; (*states)++;
            inst->LTRAstateIndex2 = *states; (*states)++;
            
            /* Initialize companion model coefficients */
            /* Maps to i[n] = G_eq v[n] + I_history[n] */
            double Z0 = sqrt(inst->LTRAl / inst->LTRAc);  /* Characteristic impedance */
            double td = inst->LTRAlen * sqrt(inst->LTRAl * inst->LTRAc); /* Delay */
            inst->LTRAd = td;
            inst->LTRAgeff = 1.0 / Z0;  /* G_eq for companion model */
        }
    }
    return OK;
}
```

### 3. Recursive Convolution Algorithm (`ltraload.c`)

The core computational engine implements the recursive convolution algorithm that solves the convolution integrals efficiently:

```c
void LTRArecursiveConvolution(LTRAinstance *inst, double *history, 
                              double *state, double currentTime)
{
    double result = 0.0;
    double deltaT = currentTime - inst->LTRAlastTime;
    
    /* Implements: y[n] = Σₖ [exp(pₖΔt)yₖ[n-1] + rₖ∫ exp(pₖ(tₙ-τ))x(τ)dτ] */
    for (int k = 0; k < inst->LTRApadeOrder; k++) {
        double pole = inst->LTRApoles[k];      /* pₖ from H(s) ≈ Σ rₖ/(s-pₖ) */
        double residue = inst->LTRAresidues[k]; /* rₖ from H(s) ≈ Σ rₖ/(s-pₖ) */
        
        /* Update state variable: exp(pₖΔt)yₖ[n-1] */
        double expFactor = exp(pole * deltaT);  /* Exponential decay/growth */
        inst->LTRAconvState1[k] = expFactor * inst->LTRAconvState1[k]
                                  + residue * history[inst->LTRAhistoryPointer];
        
        result += inst->LTRAconvState1[k];  /* Sum over all poles */
    }
    
    return result;  /* Returns I_history[n] for companion model */
}
```

### 4. Norton Companion Model Stamping

The load function `LTRAload()` implements the discrete-time companion model and stamps it into the MNA matrix:

```c
int LTRAload(GENmodel *inModel, CKTcircuit *ckt)
{
    LTRAmodel *model = (LTRAmodel *)inModel;
    LTRAinstance *inst;
    
    for (; model != NULL; model = model->LTRAnextModel) {
        for (inst = model->LTRAinstances; inst != NULL; 
             inst = inst->LTRAnextInstance) {
            
            /* Calculate equivalent conductance G_eq = Y₀ * coth(γl)|_{s→∞} */
            /* Maps to high-frequency limit of characteristic admittance */
            double Geff = sqrt(inst->LTRAc / inst->LTRAl) * 
                          coth(sqrt(inst->LTRAl * inst->LTRAc) * inst->LTRAlen);
            
            /* Stamp conductance matrix for companion model */
            /* Maps to i[n] = G_eq v[n] + I_history[n] */
            *(inst->LTRAptrPos1Pos1) += Geff;
            *(inst->LTRAptrNeg1Neg1) += Geff;
            *(inst->LTRAptrPos1Neg1) -= Geff;
            *(inst->LTRAptrNeg1Pos1) -= Geff;
            
            *(inst->LTRAptrPos2Pos2) += Geff;
            *(inst->LTRAptrNeg2Neg2) += Geff;
            *(inst->LTRAptrPos2Neg2) -= Geff;
            *(inst->LTRAptrNeg2Pos2) -= Geff;
            
            /* Calculate history currents via recursive convolution */
            /* Maps to I_history[n] = Σ h[n-m]v[m] */
            double Ihist1 = LTRArecursiveConvolution(inst, 
                inst->LTRAsignalHistory1, inst->LTRAconvState1, ckt->CKTtime);
            double Ihist2 = LTRArecursiveConvolution(inst,
                inst->LTRAsignalHistory2, inst->LTRAconvState2, ckt->CKTtime);
            
            /* Stamp history currents into RHS (right-hand side vector) */
            /* Maps to -I_history[n] in KCL equations */
            ckt->CKTrhs[inst->LTRAposNode1] -= Ihist1;
            ckt->CKTrhs[inst->LTRAnegNode1] += Ihist1;
            ckt->CKTrhs[inst->LTRAposNode2] -= Ihist2;
            ckt->CKTrhs[inst->LTRAnegNode2] += Ihist2;
            
            /* Update companion model coefficients for next iteration */
            inst->LTRAgeff = Geff;      /* G_eq */
            inst->LTRAb1 = Ihist1;      /* I_history₁[n] */
            inst->LTRAb2 = Ihist2;      /* I_history₂[n] */
        }
    }
    return OK;
}
```

### 5. Accept Logic and History Management (`ltraacct.c`)

The accept routine manages the circular history buffer and updates convolution states:

```c
int LTRAaccept(CKTcircuit *ckt, GENinstance *geninst)
{
    LTRAinstance *inst = (LTRAinstance *)geninst;
    
    /* Store current time in circular buffer for convolution window */
    inst->LTRAtimeHistory[inst->LTRAhistoryPointer] = ckt->CKTtime;
    
    /* Calculate and store port voltages for convolution integral */
    /* v₁(t) = V₁⁺(t) - V₁⁻(t) */
    double v1 = *(ckt->CKTrhs + inst->LTRAposNode1) - 
                *(ckt->CKTrhs + inst->LTRAnegNode1);
    double v2 = *(ckt->CKTrhs + inst->LTRAposNode2) - 
                *(ckt->CKTrhs + inst->LTRAnegNode2);
    
    /* Store in history buffers for i(t) = ∫h(τ)v(t-τ)dτ */
    inst->LTRAsignalHistory1[inst->LTRAhistoryPointer] = v1;
    inst->LTRAsignalHistory2[inst->LTRAhistoryPointer] = v2;
    
    /* Store state variables for LTE calculation */
    inst->LTRAprevV1 = v1;
    inst->LTRAprevV2 = v2;
    inst->LTRAprevI1 = *(ckt->CKTrhs + inst->LTRAintNode1);
    inst->LTRAprevI2 = *(ckt->CKTrhs + inst->LTRAintNode2);
    
    /* Update convolution states for recursive algorithm */
    /* yₖ[n] = exp(pₖΔt)yₖ[n-1] + rₖx[n] */
    for (int k = 0; k < inst->LTRApadeOrder; k++) {
        double deltaT = ckt->CKTtime - inst->LTRAlastTime;
        double pole = inst->LTRApoles[k];
        double residue = inst->LTRAresidues[k];
        
        /* Update state with exponential decay: exp(pₖΔt)yₖ[n-1] */
        inst->LTRAconvState1[k] = exp(pole * deltaT) * inst->LTRAconvState1[k]
                                 + residue * v1;  /* + rₖx[n] */
        inst->LTRAconvState2[k] = exp(pole * deltaT) * inst->LTRAconvState2[k]
                                 + residue * v2;
    }
    
    /* Advance circular buffer pointer for sliding window */
    inst->LTRAhistoryPointer = (inst->LTRAhistoryPointer + 1) 
                               % MAX_HISTORY_SIZE;
    if (inst->LTRAhistorySize < MAX_HISTORY_SIZE) {
        inst->LTRAhistorySize++;  /* Grow buffer until full */
    }
    
    inst->LTRAlastTime = ckt->CKTtime;
    return OK;
}
```

### 6. Local Truncation Error Calculation (`ltratrun.c`)

The truncation function implements LTE estimation for adaptive time-step control:

```c
double LTRAcalculateLTE(LTRAinstance *inst, double deltaT, 
                        double voltage, double current)
{
    /* Error from numerical integration of companion model */
    /* Charge: q = C·len·v, Flux: φ = L·len·i */
    double charge = inst->LTRAc * inst->LTRAlen * voltage;
    double flux = inst->LTRAl * inst->LTRAlen * current;
    
    /* Second derivative estimation for trapezoidal rule LTE */
    /* LTE = Δt³|d²q/dt²|/12 for charge conservation */
    double d2q_dt2 = (charge - 2*inst->LTRAprevCharge + inst->LTRAprevPrevCharge)
                     / (deltaT * deltaT);
    double d2φ_dt2 = (flux - 2*inst->LTRAprevFlux + inst->LTRAprevPrevFlux)
                     / (deltaT * deltaT);
    
    /* LTE for trapezoidal integration (p=2): Δt³|f''|/12 */
    double lteCharge = deltaT * deltaT * deltaT * fabs(d2q_dt2) / 12.0;
    double lteFlux = deltaT * deltaT * deltaT * fabs(d2φ_dt2) / 12.0;
    
    /* Convolution truncation error from exponential tail */
    /* Error ≈ exp(-αT_window) where α = min|Re(pₖ)| */
    double convError = 0.0;
    double maxPole = 0.0;
    for (int k = 0; k < inst->LTRApadeOrder; k++) {
        maxPole = MAX(maxPole, fabs(inst->LTRApoles[k]));
    }
    double tailWeight = exp(-maxPole * deltaT);  /* Exponential decay of tail */
    convError = tailWeight * fabs(inst->LTRAsignalHistory1[inst->LTRAhistoryPointer]);
    
    /* Combined LTE - take maximum of all error sources */
    double totalLTE = MAX(lteCharge, lteFlux);
    totalLTE = MAX(totalLTE, convError);
    
    return totalLTE;
}

int LTRAtrunc(GENinstance *geninst, CKTcircuit *ckt, double *timeStep)
{
    LTRAinstance *inst = (LTRAinstance *)geninst;
    
    /* Get current state for LTE calculation */
    double currentV1 = *(ckt->CKTrhs + inst->LTRAposNode1) - 
                       *(ckt->CKTrhs + inst->LTRAnegNode1);
    double currentI1 = *(ckt->CKTrhs + inst->LTRAintNode1);
    
    /* Calculate LTE using Richardson extrapolation principle */
    double lte = LTRAcalculateLTE(inst, *timeStep, currentV1, currentI1);
    
    /* Normalize by tolerance: ε_LTE ≤ reltol·|x| + abstol */
    double reltol = ckt->CKTtrtol;
    double abstol = ckt->CKTabstol;
    double norm = lte / (reltol * MAX(fabs(currentV1), abstol));
    
    if (norm > 1.0) {
        /* Reduce time step using stability-preserving factor */
        double factor = 0.9 / sqrt(norm);  /* Conservative reduction */
        *timeStep = *timeStep * factor;
        inst->LTRAlteFlag = 1;
        return E_LOCALTRUNCATION;
    }
    
    /* Check for breakpoints in convolution window */
    /* Ensure sampling at least every T_d/100 for accuracy */
    double nextHistoryTime = inst->LTRAtimeHistory[0] + inst->LTRAd;
    if (nextHistoryTime - ckt->CKTtime < *timeStep) {
        *timeStep = nextHistoryTime - ckt->CKTtime;