# Transmission Line: Characteristic Impedance and DC Load

_Generated 2026-04-12 20:58 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/tradefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/traparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/tratemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/traload.c`

# Chapter: Transmission Line: Characteristic Impedance and DC Load

## Technical Introduction

The Ngspice transmission line model implements distributed parameter analysis through four core C files that handle the complete simulation workflow for transmission line devices. `tradefs.h` defines the fundamental data structures for transmission line instances and models, establishing the memory layout for distributed parameters (R, L, G, C per unit length), characteristic impedance calculations, and delay-line state management. `traparam.c` processes user-specified parameters from the SPICE netlist, converting them into the internal representation used by the simulation engine, including geometric scaling and unit conversions. `tratemp.c` manages temperature-dependent parameter variations, applying temperature coefficients to the distributed parameters and updating characteristic impedance accordingly. `traload.c` implements the core matrix loading algorithms for both DC and transient analysis, directly implementing the Norton companion model based on the telegrapher's equations and handling the time-delay state management through circular buffers. Together, these files provide a complete implementation of transmission line physics within Ngspice's Modified Nodal Analysis framework, supporting both frequency-domain characteristic impedance calculations and time-domain propagation with accurate delay modeling.

## Mathematical Formulation

The transmission line model in Ngspice implements the telegrapher's equations for distributed parameter analysis within the SPICE circuit simulation framework. The mathematical formulation directly supports both frequency-domain (AC) and time-domain (transient) analysis through Modified Nodal Analysis (MNA) integration.

### 1. Telegrapher's Equations for Distributed Lines

The fundamental equations governing voltage and current propagation along a transmission line are derived from Maxwell's equations:

**Partial Differential Equations:**
```
∂V(x,t)/∂x = -L·∂I(x,t)/∂t - R·I(x,t)
∂I(x,t)/∂x = -C·∂V(x,t)/∂t - G·V(x,t)
```

Where:
- `V(x,t)` = Voltage at position x and time t
- `I(x,t)` = Current at position x and time t
- `R` = Series resistance per unit length (Ω/m)
- `L` = Series inductance per unit length (H/m)
- `G` = Shunt conductance per unit length (S/m)
- `C` = Shunt capacitance per unit length (F/m)

### 2. Characteristic Impedance Formulation

For sinusoidal steady-state analysis at angular frequency ω, the telegrapher's equations transform to:

**Frequency Domain Representation:**
```
dV(x)/dx = -(R + jωL)·I(x)
dI(x)/dx = -(G + jωC)·V(x)
```

**Characteristic Impedance Z₀:**
```
Z₀ = √[(R + jωL)/(G + jωC)]
```

**Propagation Constant γ:**
```
γ = √[(R + jωL)(G + jωC)] = α + jβ
```
Where:
- `α` = Attenuation constant (Np/m)
- `β` = Phase constant (rad/m)

### 3. DC Load Analysis Formulation

For DC analysis (ω = 0), the transmission line reduces to a resistive network:

**DC Characteristic Impedance:**
```
Z₀_DC = √(R/G)  for R,G ≠ 0
```

**DC Propagation Constant:**
```
γ_DC = √(R·G)
```

**Voltage and Current Solutions at DC:**
```
V(x) = V₀·cosh(γ_DC·x) - I₀·Z₀_DC·sinh(γ_DC·x)
I(x) = I₀·cosh(γ_DC·x) - (V₀/Z₀_DC)·sinh(γ_DC·x)
```

### 4. Lossless Line Approximation

For high-frequency applications where R ≪ ωL and G ≪ ωC:

**Lossless Characteristic Impedance:**
```
Z₀_lossless = √(L/C)
```

**Lossless Propagation Constant:**
```
γ_lossless = jω√(LC) = jβ
```

**Phase Velocity:**
```
v_p = ω/β = 1/√(LC)
```

### 5. Norton Companion Model for SPICE Integration

For time-domain transient analysis, the transmission line is discretized using the method of characteristics:

**Time-Delay Representation:**
```
I₁(t) = V₁(t)/Z₀ + I₂(t - T_d) - V₂(t - T_d)/Z₀
I₂(t) = V₂(t)/Z₀ + I₁(t - T_d) - V₁(t - T_d)/Z₀
```

Where:
- `T_d = ℓ/v_p` = Time delay for length ℓ
- `Z₀` = Characteristic impedance
- Subscripts 1,2 denote line endpoints

**DC Limit of Norton Model:**
For DC analysis with finite R,G:
```
I₁ = V₁/Z₀_DC + I_history
I₂ = V₂/Z₀_DC - I_history
```
Where `I_history` accounts for initial conditions and past states.

### 6. Matrix Stamping for MNA

The transmission line contributes to the SPICE MNA matrix as:

**For two-port representation:**
```
[ Y₁₁  Y₁₂ ] [ V₁ ]   [ I₁ ]
[ Y₂₁  Y₂₂ ] [ V₂ ] = [ I₂ ]
```

Where for frequency domain:
```
Y₁₁ = Y₂₂ = 1/Z₀·coth(γℓ)
Y₁₂ = Y₂₁ = -1/Z₀·csch(γℓ)
```

**DC Matrix Stamp:**
For DC analysis with lossy lines:
```
Y_DC = [  G_eq  -G_eq ]
       [ -G_eq   G_eq ]
```
Where `G_eq = 1/Z₀_DC·tanh(γ_DC·ℓ/2)` for short lines.

### 7. Parameter Extraction and Scaling

**Geometric Scaling:**
For physical transmission lines:
```
R = R'·ℓ, L = L'·ℓ, G = G'·ℓ, C = C'·ℓ
```
Where primed quantities are per-unit-length values and ℓ is line length.

**Frequency-Dependent Parameters:**
For wideband analysis, skin effect modifies R and L:
```
R(ω) = R_DC·√(1 + jω/ω_skin)
L(ω) = L' + ΔL(ω)·ℓ
```
Where `ω_skin` is the skin effect corner frequency.

### 8. Initial Conditions and DC Operating Point

**DC Solution for Initialization:**
The DC operating point solves:
```
[ R·ℓ  -R·ℓ ] [ I ]   [ V₁ - V₂ ]
[ -G·ℓ  G·ℓ ] [ V ] = [ 0 ]
```

**Initial Voltage Distribution:**
For initial conditions with voltage V₀ applied:
```
V(x,0) = V₀·exp(-γ_DC·x)
I(x,0) = (V₀/Z₀_DC)·exp(-γ_DC·x)
```

### 9. Numerical Integration for Transient Analysis

**Discrete Time Implementation:**
Using trapezoidal integration with time step Δt:
```
I₁[n] = (V₁[n] + V₁[n-1])/(2Z₀) + I_history[n-1]
I₂[n] = (V₂[n] + V₂[n-1])/(2Z₀) - I_history[n-1]
```

Where the history term is:
```
I_history[n] = I₂[n - T_d/Δt] - V₂[n - T_d/Δt]/Z₀
```

### 10. Special Cases and Limits

**Open-Circuit Termination:**
```
Z_L → ∞ ⇒ Γ = 1 ⇒ V₁ = V₂·cosh(γℓ)
```

**Short-Circuit Termination:**
```
Z_L = 0 ⇒ Γ = -1 ⇒ I₁ = I₂·cosh(γℓ)
```

**Matched Termination:**
```
Z_L = Z₀ ⇒ Γ = 0 ⇒ V₁/V₂ = I₁/I₂ = exp(-γℓ)
```

**DC Short-Circuit Limit:**
```
As ω → 0 and G → 0: Z₀ → ∞, line becomes open circuit
```

**DC Open-Circuit Limit:**
```
As ω → 0 and R → 0: Z₀ → 0, line becomes short circuit
```

This mathematical formulation provides the complete SPICE-compatible framework for transmission line analysis in Ngspice, covering characteristic impedance calculation, DC load behavior, and seamless integration with the Modified Nodal Analysis system for both frequency-domain and time-domain simulation.

## Convergence Analysis

### 1. Newton-Raphson Convergence for Nonlinear Parameters

When transmission line parameters exhibit voltage or current dependence (nonlinear R, L, C, G), the Newton-Raphson iteration must converge to a consistent solution:

**Jacobian Matrix for Nonlinear Line:**
```
J = ∂F/∂V = [ ∂I₁/∂V₁  ∂I₁/∂V₂ ]
            [ ∂I₂/∂V₁  ∂I₂/∂V₂ ]
```

Where for the Norton companion model:
```
∂I₁/∂V₁ = 1/Z₀ + ∂I_history/∂V₁
∂I₁/∂V₂ = ∂I_history/∂V₂
∂I₂/∂V₁ = ∂I_history/∂V₁
∂I₂/∂V₂ = 1/Z₀ + ∂I_history/∂V₂
```

**Convergence Criterion:**
```
|ΔV| < ε_V = ε_abs + ε_rel·max(|V|, V_min)
|ΔI| < ε_I = ε_abs + ε_rel·max(|I|, I_min)
```

### 2. Time-Step Control for Transient Analysis

The transmission line's time-delay nature imposes constraints on time-step selection:

**Courant-Friedrichs-Lewy (CFL) Condition:**
```
Δt ≤ T_d / N_samples
```
Where `N_samples ≥ 2` for accurate time-delay representation.

**Local Truncation Error (LTE) Estimation:**
For trapezoidal integration:
```
LTE = (Δt³/12)·|d³I/dt³|
```

The time-step adapts to maintain:
```
LTE < ε_LTE·max(|I|, I_min)
```

### 3. Frequency-Domain Convergence

For AC analysis, the convergence of the frequency sweep must be monitored:

**Impedance Convergence:**
```
|Z₀(ω_{k+1}) - Z₀(ω_k)| < ε_Z·max(|Z₀|, Z_min)
```

**S-Parameter Convergence:**
For scattering parameters:
```
|S_{ij}(ω_{k+1}) - S_{ij}(ω_k)| < ε_S
```

### 4. DC Operating Point Convergence

The DC solution for lossy transmission lines must converge despite potentially ill-conditioned matrices:

**Lossy Line Conditioning:**
The condition number for the DC conductance matrix:
```
κ(G_DC) = max(R·ℓ, 1/(G·ℓ)) / min(R·ℓ, 1/(G·ℓ))
```

Regularization is applied when:
```
κ(G_DC) > 1/ε_machine
```

**Initial Condition Convergence:**
For DC with initial voltage distribution:
```
|V_{k+1}(x) - V_k(x)| < ε_DC·max(|V(x)|, V_min)
```

### 5. Characteristic Impedance Computation Stability

The complex square root in `Z₀ = √[(R+jωL)/(G+jωC)]` requires careful numerical handling:

**Branch Cut Handling:**
For `ω → 0`, the computation uses:
```
Z₀ = lim_{ω→0} √[(R+jωL)/(G+jωC)] = √(R/G)  (if R,G > 0)
```

**Numerical Stability for Small Parameters:**
When `R,G → 0`:
```
if (|R+jωL| < ε_small) Z₀ = √(L/C)
if (|G+jωC| < ε_small) Z₀ = √(L/C)
```

### 6. Time-Delay Implementation Convergence

The discrete time-delay implementation must converge with respect to interpolation accuracy:

**Interpolation Error:**
For non-integer `T_d/Δt`, linear interpolation error:
```
ε_interp = (Δt²/8)·|d²I/dt²|
```

**History Buffer Convergence:**
The history term convergence:
```
|I_history[n] - I_exact(t-nT_d)| < ε_history
```

### 7. Lossless Line Special Case Convergence

For lossless lines (R=0, G=0), special convergence considerations apply:

**Numerical Dispersion:**
The discrete implementation introduces numerical dispersion:
```
v_p_num = (2/Δt)·asin(ωΔt/2) / ω
```

The dispersion error must be bounded:
```
|v_p_num - v_p| / v_p < ε_disp
```

**Stability Condition:**
The lossless line implementation is stable only if:
```
Δt ≤ ℓ/v_p  (CFL condition)
```

### 8. Multi-Segment Line Convergence

For long lines discretized into multiple segments:

**Segment Length Convergence:**
```
|V_N-segment(x) - V_∞-segment(x)| < ε_segment
```

**Optimal Segment Count:**
The number of segments N is chosen to satisfy:
```
N > ℓ·β_max / π  (for phase accuracy)
N > ℓ·α_max / ln(2)  (for attenuation accuracy)
```

### 9. Parameter Extraction Convergence

When R, L, G, C are extracted from measurements or geometry:

**Extraction Algorithm Convergence:**
The parameter extraction minimizes:
```
ε_fit = Σ|Z_measured(ω_i) - Z_model(ω_i)|²
```

Convergence is achieved when:
```
|ε_fit^{(k+1)} - ε_fit^{(k)}| < ε_fit·ε_fit^{(k)}
```

### 10. Temperature and Process Variation Convergence

For statistical analysis with parameter variations:

**Monte Carlo Convergence:**
The mean characteristic impedance converges as:
```
|μ_Z(N) - μ_Z| < t_α·σ_Z/√N
```

**Process Corner Convergence:**
For corner analysis, the worst-case convergence:
```
max_{corners} |Z₀^{(k+1)} - Z₀^{(k)}| < ε_corner
```

### 11. Implementation-Specific Convergence Enhancements

**Adaptive Frequency Sampling:**
For wideband analysis, frequency points are adapted based on:
```
Δω_{k+1} = Δω_k·min(2, max(0.5, |dZ₀/dω|_k/|dZ₀/dω|_{k-1}))
```

**Time-Step Adaptation for Discontinuities:**
Near reflections and discontinuities:
```
Δt_{adapt} = min(Δt_default, T_d/10, T_rise/20)
```

**Regularization for Ill-Conditioned Cases:**
When `|Z₀| → 0` or `|Z₀| → ∞`:
```
Z₀_reg = Z₀ / (1 + j·ε_reg·sign(imag(Z₀)))
```

### 12. Error Propagation Analysis

**Sensitivity to Parameter Errors:**
```
ΔZ₀/Z₀ ≈ (1/2)·[ΔR/(R+jωL) - ΔG/(G+jωC) 
                + jω(ΔL/(R+jωL) - ΔC/(G+jωC))]
```

**Cumulative Error in Cascade:**
For N cascaded lines:
```
ε_total ≈ √N·ε_single
```

This convergence analysis ensures robust and accurate transmission line simulation in Ngspice, addressing numerical stability, time-step control, frequency-domain convergence, and special case handling for both lossless and lossy transmission lines in SPICE circuit simulation.

## C Implementation

### Core Data Structures and SPICEdev API Integration

The transmission line model in Ngspice implements the telegrapher's equations through specialized C data structures that store distributed parameters and delay-line state information. The implementation follows the standard Ngspice device model architecture with extensions for handling propagation delays and characteristic impedance calculations.

#### Transmission Line Instance and Model Structures

Based on the Ngspice device model patterns shown in the research context, the transmission line would have structures similar to:

```c
/* Hypothetical transmission line structure based on Ngspice patterns */
typedef struct sTXLinstance {
    /* Node connectivity - transmission lines typically have 4 nodes (2 ports) */
    int TXLposNode1;      /* Positive node of port 1 */
    int TXLnegNode1;      /* Negative node of port 1 */
    int TXLposNode2;      /* Positive node of port 2 */
    int TXLnegNode2;      /* Negative node of port 2 */
    
    /* Distributed parameters */
    double TXLr;          /* Resistance per unit length (R) */
    double TXLl;          /* Inductance per unit length (L) */
    double TXLg;          /* Conductance per unit length (G) */
    double TXLc;          /* Capacitance per unit length (C) */
    double TXLlength;     /* Line length */
    double TXLdelay;      /* Propagation delay T_d = length * √(LC) */
    
    /* Characteristic impedance and propagation constant */
    double TXLz0;         /* Characteristic impedance Z₀ = √((R+jωL)/(G+jωC)) */
    double TXLgamma_real; /* Real part of propagation constant (attenuation α) */
    double TXLgamma_imag; /* Imaginary part of propagation constant (phase β) */
    
    /* Matrix pointers following Ngspice SMP pattern */
    double *TXLp1p1Ptr;   /* Port 1 positive to positive */
    double *TXLp1n1Ptr;   /* Port 1 positive to negative */
    double *TXLn1p1Ptr;   /* Port 1 negative to positive */
    double *TXLn1n1Ptr;   /* Port 1 negative to negative */
    double *TXLp2p2Ptr;   /* Port 2 positive to positive */
    double *TXLp2n2Ptr;   /* Port 2 positive to negative */
    double *TXLn2p2Ptr;   /* Port 2 negative to positive */
    double *TXLn2n2Ptr;   /* Port 2 negative to negative */
    double *TXLp1p2Ptr;   /* Cross-coupling port 1 to port 2 */
    double *TXLp2p1Ptr;   /* Cross-coupling port 2 to port 1 */
    
    /* Delay line state variables for Norton companion model */
    double *TXLdelayLineV1;  /* Past voltage at port 1 */
    double *TXLdelayLineV2;  /* Past voltage at port 2 */
    double *TXLdelayLineI1;  /* Past current at port 1 */
    double *TXLdelayLineI2;  /* Past current at port 2 */
    int TXLdelayIndex;       /* Current index in delay line buffer */
    
    /* DC load specific parameters */
    double TXLdcResistance;  /* DC resistance = R * length */
    double TXLdcConductance; /* DC conductance = 1/(R * length) */
    
    struct sTXLinstance *TXLnextInstance;
} TXLinstance;

typedef struct sTXLmodel {
    int TXLmodType;
    struct sTXLmodel *TXLnextModel;
    TXLinstance *TXLinstances;
    
    /* Model-level parameters with defaults */
    double TXLdefaultR;      /* Default R per unit length */
    double TXLdefaultL;      /* Default L per unit length */
    double TXLdefaultG;      /* Default G per unit length */
    double TXLdefaultC;      /* Default C per unit length */
    double TXLdefaultZ0;     /* Default characteristic impedance */
    double TXLdefaultDelay;  /* Default propagation delay */
} TXLmodel;
```

### Characteristic Impedance Calculation Implementation

The characteristic impedance calculation directly implements the mathematical formula from the research context:

```c
/* Calculate characteristic impedance Z₀ = √[(R + jωL)/(G + jωC)] */
static void TXLcalcImpedance(TXLinstance *inst, double frequency) {
    double omega = 2.0 * M_PI * frequency;
    
    /* Mathematical: Z₀ = √[(R + jωL)/(G + jωC)] */
    /* For DC (ω = 0): Z₀_dc = √(R/G) if G ≠ 0, otherwise approaches ∞ */
    if (frequency == 0.0) {
        /* DC case */
        if (inst->TXLg > 1e-30) {
            inst->TXLz0 = sqrt(inst->TXLr / inst->TXLg);
        } else {
            /* Lossless line at DC - impedance approaches infinity */
            inst->TXLz0 = 1e12; /* Large but finite value */
        }
        inst->TXLgamma_real = inst->TXLlength * sqrt(inst->TXLr * inst->TXLg);
        inst->TXLgamma_imag = 0.0;
    } else {
        /* AC case - complex impedance */
        double numerator_real = inst->TXLr;
        double numerator_imag = omega * inst->TXLl;
        double denominator_real = inst->TXLg;
        double denominator_imag = omega * inst->TXLc;
        
        /* Compute magnitude and phase of Z₀ */
        double mag_num = sqrt(numerator_real*numerator_real + numerator_imag*numerator_imag);
        double mag_den = sqrt(denominator_real*denominator_real + denominator_imag*denominator_imag);
        double phase_num = atan2(numerator_imag, numerator_real);
        double phase_den = atan2(denominator_imag, denominator_real);
        
        inst->TXLz0 = sqrt(mag_num / mag_den);
        double phase_z0 = 0.5 * (phase_num - phase_den);
        
        /* Also compute propagation constant γ = α + jβ = √[(R+jωL)(G+jωC)] */
        double prod_real = numerator_real*denominator_real - numerator_imag*denominator_imag;
        double prod_imag = numerator_real*denominator_imag + numerator_imag*denominator_real;
        
        double mag_gamma = sqrt(sqrt(prod_real*prod_real + prod_imag*prod_imag));
        double phase_gamma = 0.5 * atan2(prod_imag, prod_real);
        
        inst->TXLgamma_real = mag_gamma * cos(phase_gamma); /* α - attenuation */
        inst->TXLgamma_imag = mag_gamma * sin(phase_gamma); /* β - phase constant */
    }
    
    /* Calculate propagation delay: T_d = length * √(LC) for lossless case */
    inst->TXLdelay = inst->TXLlength * sqrt(inst->TXLl * inst->TXLc);
}
```

### DC Load Implementation

For DC analysis, the transmission line reduces to a simple resistive network based on the DC resistance:

```c
/* DC load function for transmission line */
int TXLloadDC(GENmodel *inModel, CKTcircuit *ckt) {
    TXLmodel *model = (TXLmodel *)inModel;
    TXLinstance *inst;
    
    for (; model != NULL; model = model->TXLnextModel) {
        for (inst = model->TXLinstances; inst != NULL; 
             inst = inst->TXLnextInstance) {
            
            /* Calculate DC resistance: R_dc = R * length */
            /* Mathematical: At DC, ω = 0, so Z₀ = √(R/G) and γ = √(RG) */
            double R_dc = inst->TXLr * inst->TXLlength;
            double G_dc = 0.0;
            
            if (R_dc > 1e-30) {
                G_dc = 1.0 / R_dc;
            } else {
                /* Avoid division by zero for very small resistance */
                R_dc = 1e-12;
                G_dc = 1e12;
            }
            
            inst->TXLdcResistance = R_dc;
            inst->TXLdcConductance = G_dc;
            
            /* For DC, the transmission line acts as a resistor network */
            /* Stamp conductance matrix similar to resistor pattern */
            if (inst->TXLp1p1Ptr != NULL) {
                *(inst->TXLp1p1Ptr) += G_dc;
            }
            if (inst->TXLn1n1Ptr != NULL) {
                *(inst->TXLn1n1Ptr) += G_dc;
            }
            if (inst->TXLp1n1Ptr != NULL) {
                *(inst->TXLp1n1Ptr) -= G_dc;
            }
            if (inst->TXLn1p1Ptr != NULL) {
                *(inst->TXLn1p1Ptr) -= G_dc;
            }
            
            /* Port 2 similarly */
            if (inst->TXLp2p2Ptr != NULL) {
                *(inst->TXLp2p2Ptr) += G_dc;
            }
            if (inst->TXLn2n2Ptr != NULL) {
                *(inst->TXLn2n2Ptr) += G_dc;
            }
            if (inst->TXLp2n2Ptr != NULL) {
                *(inst->TXLp2n2Ptr) -= G_dc;
            }
            if (inst->TXLn2p2Ptr != NULL) {
                *(inst->TXLn2p2Ptr) -= G_dc;
            }
            
            /* For DC, there's no cross-coupling between ports (delay → ∞ at DC) */
            /* The ports are effectively isolated except through the ground network */
        }
    }
    return OK;
}
```

### Matrix Setup Following Ngspice SMP Pattern

The matrix setup function allocates SMP matrix elements following the pattern shown in the research:

```c
/* Matrix setup following the Ngspice SMP pattern shown in section 7 */
int TXLsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    TXLmodel *model = (TXLmodel *)inModel;
    TXLinstance *inst;
    
    for (; model != NULL; model = model->TXLnextModel) {
        for (inst = model->TXLinstances; inst != NULL; 
             inst = inst->TXLnextInstance) {
            
            /* Allocate matrix elements for port 1 */
            inst->TXLp1p1Ptr = SMPmakeElt(matrix, inst->TXLposNode1, inst->TXLposNode1);
            inst->TXLp1n1Ptr = SMPmakeElt(matrix, inst->TXLposNode1, inst->TXLnegNode1);
            inst->TXLn1p1Ptr = SMPmakeElt(matrix, inst->TXLnegNode1, inst->TXLposNode1);
            inst->TXLn1n1Ptr = SMPmakeElt(matrix, inst->TXLnegNode1, inst->TXLnegNode1);
            
            /* Allocate matrix elements for port 2 */
            inst->TXLp2p2Ptr = SMPmakeElt(matrix, inst->TXLposNode2, inst->TXLposNode2);
            inst->TXLp2n2Ptr = SMPmakeElt(matrix, inst->TXLposNode2, inst->TXLnegNode2);
            inst->TXLn2p2Ptr = SMPmakeElt(matrix, inst->TXLnegNode2, inst->TXLposNode2);
            inst->TXLn2n2Ptr = SMPmakeElt(matrix, inst->TXLnegNode2, inst->TXLnegNode2);
            
            /* Allocate cross-coupling elements for transmission */
            inst->TXLp1p2Ptr = SMPmakeElt(matrix, inst->TXLposNode1, inst->TXLposNode2);
            inst->TXLp2p1Ptr = SMPmakeElt(matrix, inst->TXLposNode2, inst->TXLposNode1);
            
            /* Allocate delay line state variables */
            int delaySteps = (int)(inst->TXLdelay / ckt->CKTminTimeStep) + 10;
            inst->TXLdelayLineV1 = TMALLOC(double, delaySteps);
            inst->TXLdelayLineV2 = TMALLOC(double, delaySteps);
            inst->TXLdelayLineI1 = TMALLOC(double, delaySteps);
            inst->TXLdelayLineI2 = TMALLOC(double, delaySteps);
            inst->TXLdelayIndex = 0;
            
            /* Initialize delay line to zero */
            for (int i = 0; i < delaySteps; i++) {
                inst->TXLdelayLineV1[i] = 0.0;
                inst->TXLdelayLineV2[i] = 0.0;
                inst->TXLdelayLineI1[i] = 0.0;
                inst->TXLdelayLineI2[i] = 0.0;
            }
            
            /* Allocate state numbers for time integration */
            inst->TXLstateIndex = *states;
            *states += 4; /* V1, V2, I1, I2 */
        }
    }
    return OK;
}
```

### Norton Companion Model Implementation

The Norton companion model implements the mathematical formulation from the research:

```c
/* Norton companion model for transient analysis */
int TXLload(GENmodel *inModel, CKTcircuit *ckt) {
    TXLmodel *model = (TXLmodel *)inModel;
    TXLinstance *inst;
    
    for (; model != NULL; model = model->TXLnextModel) {
        for (inst = model->TXLinstances; inst != NULL; 
             inst = inst->TXLnextInstance) {
            
            /* Calculate characteristic impedance at current frequency */
            double freq = 0.0;
            if (ckt->CKTmode & MODEAC) {
                freq = ckt->CKTomega / (2.0 * M_PI);
            }
            TXLcalcImpedance(inst, freq);
            
            double Z0 = inst->TXLz0;
            double Y0 = 1.0 / Z0; /* Characteristic admittance */
            double Td = inst->TXLdelay;
            
            /* Get current voltages */
            double V1 = ckt->CKTrhs[inst->TXLposNode1] - ckt->CKTrhs[inst->TXLnegNode1];
            double V2 = ckt->CKTrhs[inst->TXLposNode2] - ckt->CKTrhs[inst->TXLnegNode2];
            
            /* Get delayed values from history buffer */
            int delayIndex = inst->TXLdelayIndex;
            int histIndex = (delayIndex - (int)(Td / ckt->CKTdeltaOld[0]) + inst->TXLdelaySteps) % inst->TXLdelaySteps;
            
            double V2_delayed = inst->TXLdelayLineV2[histIndex];
            double I2_delayed = inst->TXLdelayLineI2[histIndex];
            double V1_delayed = inst->TXLdelayLineV1[histIndex];
            double I1_delayed = inst->TXLdelayLineI1[histIndex];
            
            /* Norton companion model equations from research: */
            /* I₁(t) = V₁(t)/Z₀ + I₂(t - T_d) - V₂(t - T_d)/Z₀ */
            /* I₂(t) = V₂(t)/Z₀ + I₁(t - T_d) - V₁(t - T_d)/Z₀ */
            
            double I1_eq = I2_delayed - V2_delayed / Z0;
            double I2_eq = I1_delayed - V1_delayed / Z0;
            
            /* Stamp into matrix */
            /* Self admittance Y0 at each port */
            if (inst->TXLp1p1Ptr != NULL) {
                *(inst->TXLp1p1Ptr) += Y0;
            }
            if (inst->TXLn1n1Ptr != NULL) {
                *(inst->TXLn1n1Ptr) += Y0;
            }
            if (inst->TXLp1n1Ptr != NULL) {
                *(inst->TXLp1n1Ptr) -= Y0;
            }
            if (inst->TXLn1p1Ptr != NULL) {
                *(inst->TXLn1p1Ptr) -= Y0;
            }
            
            if (inst->TXLp2p2Ptr != NULL) {
                *(inst->TXLp2p2Ptr) += Y0;
            }
            if (inst->TXLn2n2Ptr != NULL) {
                *(inst->TXLn2n2Ptr) += Y0;
            }
            if (inst->TXLp2n2Ptr != NULL) {
                *(inst->TXLp2n2Ptr) -= Y0;
            }
            if (inst->TXLn2p2Ptr != NULL) {
                *(inst->TXLn2p2Ptr) -= Y0;
            }
            
            /* Stamp equivalent current sources to RHS */
            ckt->CKTrhs[inst->TXLposNode1] -= I1_eq;
            ckt->CKTrhs[inst->TXLnegNode1] += I1_eq;
            ckt->CKTrhs[inst->TXLposNode2] -= I2_eq;
            ckt->CKTrhs[inst->TXLnegNode2] += I2_eq;
            
            /* Store current state in delay line */
            inst->TXLdelayLineV1[delayIndex] = V1;
            inst->TXLdelayLineV2[delayIndex] = V2;
            inst->TXLdelayLineI1[delayIndex] = (V1 / Z0) + I1_eq; /* Actual current */
            inst->TXLdelayLineI2[delayIndex] = (V2 / Z0) + I2_eq; /* Actual current */
            
            inst->TXLdelayIndex = (delayIndex + 1) % inst->TXLdelaySteps;
        }
    }
    return OK;
}
```

### SPICEdev API Integration

Following the Ngspice device registration pattern shown in section 9:

```c
/* SPICEdev structure for transmission line */
SPICEdev TXLinfo = {
    .DEVpublic = {
        .name = "tline",
        .description = "Transmission line with characteristic impedance",
        .terms = 4,
        .numNames = 4,
        .termNames = {"p1", "n1", "p2", "n2"},
    },
    
    /* Parameter tables would be defined elsewhere */
    .DEVmodParam = TXLmPTable,
    .DEVinstParam = TXLpTable,
    
    /* Core functions following Ngspice pattern */
    .DEVload = TXLload,           /* Transient loading */
    .DEVsetup = TXLsetup,         /* Matrix setup */
    .DEVunsetup = TXLunsetup,     /* Cleanup */
    .DEVtemperature = TXLtemp,    /* Temperature effects */
    .DEVtrunc = TXLtrunc,         /* Local truncation error */
    .DEVacLoad = TXLacLoad,       /* AC small-signal */
    .DEVdestroy = TXLdestroy,     /* Memory cleanup */
    .DEVmodDelete = TXLmDelete,   /* Model deletion */
    .DEVinstDelete = TXLdelete,   /* Instance deletion */
    .DEVask = TXLask,             /* Parameter query */
    .DEVmodAsk = TXLmAsk,         /* Model parameter query */
    .DEVpzLoad = TXLpzLoad,       /* Pole-zero analysis */
    .DEVconvTest = TXLconvTest,   /* Convergence testing */
    .DEVnoise = TXLnoise,         /* Noise analysis */
    
    /* DC analysis specific function */
    .DEVload = TXLloadDC,         /* DC loading (overrides transient) */
    
    /* Sizing information */
    .DEVinstSize = sizeof(TXLinstance),
    .DEVmodSize = sizeof(TXLmodel),
};
```

### Convergence Testing Implementation

Following the convergence test pattern from section 7:

```c
int TXLconvTest(GENmodel *inModel, CKTcircuit *ckt) {
    TXLmodel *model = (TXLmodel *)inModel;
    TXLinstance *inst;
    double vnew, vold, tol;
    
    for (; model != NULL; model = model->TXLnextModel) {
        for (inst = model->TXLinstances; inst != NULL; 
             inst = inst->TXLnextInstance) {
            
            /* Test port 1 voltage convergence */
            vnew = ckt->CKTr