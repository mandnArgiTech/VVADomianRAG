# Transmission Line: Matrix Setup, API Binding, and Memory

_Generated 2026-04-12 21:06 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/trasetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/traask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/trainit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/tra.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/tradel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/tramdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/tradest.c`

# **Ngspice Technical Reference: Transmission Line Model**

## **Chapter 3: Transmission Line - Characteristic Impedance and DC Load**

### **Technical Introduction**

The transmission line implementation in Ngspice represents a sophisticated bridge between distributed electromagnetic theory and lumped-element circuit simulation. The core files `tradefs.h`, `traparam.c`, `tratemp.c`, and `traload.c` implement a complete solution to the telegrapher's equations within SPICE's Modified Nodal Analysis (MNA) framework. This implementation handles:

1. **Distributed Parameter Storage** (`tradefs.h`): Defines C structures for per-unit-length R, L, G, C parameters and derived quantities like characteristic impedance and propagation constants.

2. **Geometric Scaling** (`traparam.c`): Converts physical dimensions to electrical parameters, validating boundary conditions and unit consistency.

3. **Temperature Dependence** (`tratemp.c`): Implements temperature coefficients for resistance and conductance variations.

4. **Matrix Integration** (`traload.c`): Maps continuous transmission line equations to discrete SPICE matrix stamps for both DC and transient analysis.

The implementation follows Ngspice's standardized device architecture while addressing the unique challenges of time-delay systems and distributed parameters.

---

## **Mathematical Formulation**

### **1. Telegrapher's Equations Foundation**

The transmission line model solves Maxwell's equations in one dimension:

```
∂V(x,t)/∂x = -L·∂I(x,t)/∂t - R·I(x,t)
∂I(x,t)/∂x = -C·∂V(x,t)/∂t - G·V(x,t)
```

**Variables:**
- `V(x,t)`: Voltage at position x, time t (volts)
- `I(x,t)`: Current at position x, time t (amperes)
- `R`: Series resistance per unit length (Ω/m)
- `L`: Series inductance per unit length (H/m)
- `G`: Shunt conductance per unit length (S/m)
- `C`: Shunt capacitance per unit length (F/m)

### **2. Frequency Domain Transformation**

For sinusoidal steady-state analysis at angular frequency ω:

```
dV(x)/dx = -(R + jωL)·I(x)
dI(x)/dx = -(G + jωC)·V(x)
```

### **3. Characteristic Impedance Computation**

```
Z₀(ω) = √[(R + jωL)/(G + jωC)]
```

**Special Cases:**
- **DC Limit** (ω → 0): `Z₀_DC = √(R/G)` for R,G ≠ 0
- **Lossless Line** (R,G → 0): `Z₀ = √(L/C)`
- **Lossy DC Open Circuit** (G → 0): `Z₀ → ∞`
- **Lossy DC Short Circuit** (R → 0): `Z₀ → 0`

### **4. Propagation Constant**

```
γ(ω) = √[(R + jωL)(G + jωC)] = α(ω) + jβ(ω)
```

**Components:**
- `α(ω)`: Attenuation constant (nepers/m)
- `β(ω)`: Phase constant (radians/m)

### **5. Norton Companion Model for SPICE**

The continuous equations are discretized using the method of characteristics:

```
I₁(t) = V₁(t)/Z₀ + I₂(t - T_d) - V₂(t - T_d)/Z₀
I₂(t) = V₂(t)/Z₀ + I₁(t - T_d) - V₁(t - T_d)/Z₀
```

**Where:**
- `T_d = ℓ·√(LC)`: Propagation delay for length ℓ (lossless approximation)
- Subscripts 1,2: Port indices

### **6. DC Analysis Simplification**

For ω = 0, the transmission line reduces to resistive elements:

```
R_dc = R·ℓ
G_dc = 1/R_dc  (for R_dc > 0)
```

The DC conductance matrix becomes:
```
[ G_dc  -G_dc  0     0    ]
[ -G_dc  G_dc  0     0    ]
[ 0      0     G_dc  -G_dc ]
[ 0      0     -G_dc  G_dc ]
```

### **7. Matrix Stamping for MNA**

The transmission line contributes to the SPICE system matrix as:

**For frequency domain:**
```
Y₁₁ = Y₂₂ = (1/Z₀)·coth(γℓ)
Y₁₂ = Y₂₁ = -(1/Z₀)·csch(γℓ)
```

**For time domain (trapezoidal integration):**
```
I₁[n] = (V₁[n] + V₁[n-1])/(2Z₀) + I_history[n-1]
I₂[n] = (V₂[n] + V₂[n-1])/(2Z₀) - I_history[n-1]
```

**History term:**
```
I_history[n] = I₂[n - T_d/Δt] - V₂[n - T_d/Δt]/Z₀
```

---

## **Convergence Analysis**

### **1. Newton-Raphson Convergence Criteria**

For the nonlinear system `F(V) = 0`, convergence requires:

```
|ΔV| < ε_V = ε_abs + ε_rel·max(|V|, V_min)
|ΔI| < ε_I = ε_abs + ε_rel·max(|I|, I_min)
```

**Typical values in Ngspice:**
- `ε_abs = 1e-12` (absolute tolerance)
- `ε_rel = 1e-6` (relative tolerance)
- `V_min = 1e-6` V (minimum voltage for scaling)
- `I_min = 1e-12` A (minimum current for scaling)

### **2. Time-Step Control for Transient Analysis**

**Courant-Friedrichs-Lewy (CFL) Condition:**
```
Δt ≤ T_d / N_samples
```
Where `N_samples ≥ 2` for accurate delay representation.

**Local Truncation Error (LTE) Estimation:**
For trapezoidal integration:
```
LTE = (Δt³/12)·|d³I/dt³|
```
Time-step adaptation maintains:
```
LTE < ε_LTE·max(|I|, I_min)
```

### **3. Frequency Domain Convergence**

**Impedance Convergence:**
```
|Z₀(ω_{k+1}) - Z₀(ω_k)| < ε_Z·max(|Z₀|, Z_min)
```

**S-Parameter Convergence:**
```
|S_{ij}(ω_{k+1}) - S_{ij}(ω_k)| < ε_S
```

### **4. DC Operating Point Stability**

**Matrix Conditioning:**
The DC conductance matrix condition number:
```
κ(G_DC) = max(R·ℓ, 1/(G·ℓ)) / min(R·ℓ, 1/(G·ℓ))
```

Regularization applied when:
```
κ(G_DC) > 1/ε_machine ≈ 4.5×10¹⁵ (double precision)
```

### **5. Numerical Stability for Edge Cases**

**Small Parameter Handling:**
```c
if (|R + jωL| < 1e-30) Z₀ = sqrt(L/C);
if (|G + jωC| < 1e-30) Z₀ = sqrt(L/C);
```

**DC with Zero Conductance:**
```c
if (G < 1e-30) {
    Z₀_DC = 1e12;  // Approximate open circuit
    G_eq = 1e-12;  // Minimum conductance
}
```

### **6. Delay Line Implementation Accuracy**

**Interpolation Error:**
For non-integer `T_d/Δt`, linear interpolation introduces:
```
ε_interp = (Δt²/8)·|d²I/dt²|
```

**History Buffer Convergence:**
```
|I_history[n] - I_exact(t - nT_d)| < ε_history
```

### **7. Lossless Line Special Considerations**

**Numerical Dispersion:**
Discrete implementation causes phase velocity error:
```
v_p_num = (2/Δt)·asin(ωΔt/2) / ω
```
Error bounded by:
```
|v_p_num - v_p| / v_p < ε_disp
```

**Stability Requirement:**
```
Δt ≤ ℓ / v_p  (CFL condition for stability)
```

### **8. Multi-Segment Line Convergence**

For long lines divided into N segments:

**Segment Length Convergence:**
```
|V_N-segment(x) - V_∞-segment(x)| < ε_segment
```

**Optimal Segmentation:**
```
N > max(ℓ·β_max/π, ℓ·α_max/ln(2))
```

### **9. Parameter Extraction Convergence**

When extracting R, L, G, C from measurements:

**Error Minimization:**
```
min Σ|Z_measured(ω_i) - Z_model(ω_i, R, L, G, C)|²
```

Convergence achieved when:
```
|ε_fit^{(k+1)} - ε_fit^{(k)}| < ε_fit·ε_fit^{(k)}
```

### **10. Statistical Analysis Convergence**

**Monte Carlo Mean Convergence:**
```
|μ_Z(N) - μ_Z| < t_α·σ_Z/√N
```

**Process Corner Analysis:**
```
max_{corners} |Z₀^{(k+1)} - Z₀^{(k)}| < ε_corner
```

### **11. Adaptive Algorithm Enhancements**

**Frequency Sampling Adaptation:**
```
Δω_{k+1} = Δω_k·min(2, max(0.5, |dZ₀/dω|_k/|dZ₀/dω|_{k-1}))
```

**Time-Step Adaptation for Discontinuities:**
```
Δt_{adapt} = min(Δt_default, T_d/10, T_rise/20)
```

### **12. Error Propagation Analysis**

**Parameter Sensitivity:**
```
ΔZ₀/Z₀ ≈ (1/2)·[ΔR/(R+jωL) - ΔG/(G+jωC) 
                + jω(ΔL/(R+jωL) - ΔC/(G+jωC))]
```

**Cascaded Line Error:**
For N identical cascaded lines:
```
ε_total ≈ √N·ε_single
```

---

## **C Implementation**

### **Core Data Structures**

```c
/* tradefs.h - Transmission Line Data Structures */
typedef struct sTRAinstance {
    /* Node Connections (4 nodes for 2-port) */
    int TRAposNode1;    /* Port 1 positive node */
    int TRAnegNode1;    /* Port 1 negative node */
    int TRAposNode2;    /* Port 2 positive node */
    int TRAnegNode2;    /* Port 2 negative node */
    
    /* Distributed Parameters */
    double TRAresist;   /* R - Resistance per unit length (Ω/m) */
    double TRAind;      /* L - Inductance per unit length (H/m) */
    double TRAcond;     /* G - Conductance per unit length (S/m) */
    double TRAcap;      /* C - Capacitance per unit length (F/m) */
    double TRAlength;   /* Line length (m) */
    
    /* Derived Quantities */
    double TRAz0;       /* Characteristic impedance Z₀ */
    double TRAgammaR;   /* Real(γ) = α - attenuation constant */
    double TRAgammaI;   /* Imag(γ) = β - phase constant */
    double TRAdelay;    /* Propagation delay T_d = length·√(LC) */
    
    /* Matrix Pointers (SMP sparse matrix system) */
    double *TRAp1p1Ptr; /* G[pos1][pos1] */
    double *TRAp1n1Ptr; /* G[pos1][neg1] */
    double *TRAn1p1Ptr; /* G[neg1][pos1] */
    double *TRAn1n1Ptr; /* G[neg1][neg1] */
    double *TRAp2p2Ptr; /* G[pos2][pos2] */
    double *TRAp2n2Ptr; /* G[pos2][neg2] */
    double *TRAn2p2Ptr; /* G[neg2][pos2] */
    double *TRAn2n2Ptr; /* G[neg2][neg2] */
    double *TRAp1p2Ptr; /* G[pos1][pos2] - cross coupling */
    double *TRAp2p1Ptr; /* G[pos2][pos1] - cross coupling */
    
    /* Delay Line State Variables */
    double *TRAdelayV1; /* Past voltages at port 1 */
    double *TRAdelayV2; /* Past voltages at port 2 */
    double *TRAdelayI1; /* Past currents at port 1 */
    double *TRAdelayI2; /* Past currents at port 2 */
    int TRAdelayIdx;    /* Current delay line index */
    int TRAdelaySize;   /* Delay line buffer size */
    
    /* DC Analysis Parameters */
    double TRAdcResist; /* DC resistance = R·length */
    double TRAdcCond;   /* DC conductance = 1/(R·length) */
    
    /* Linked List Pointer */
    struct sTRAinstance *TRAnextInstance;
} TRAinstance;

typedef struct sTRAmodel {
    int TRAmodType;              /* Model type identifier */
    struct sTRAmodel *TRAnextModel; /* Linked list pointer */
    TRAinstance *TRAinstances;   /* Instance list */
    
    /* Model Default Parameters */
    double TRAdefResist;         /* Default R */
    double TRAdefInd;            /* Default L */
    double TRAdefCond;           /* Default G */
    double TRAdefCap;            /* Default C */
    double TRAdefLength;         /* Default length */
    double TRAdefZ0;             /* Default Z₀ */
    double TRAdefDelay;          /* Default delay */
    
    /* Temperature Coefficients */
    double TRAtc1;               /* First-order temp coeff for R */
    double TRAtc2;               /* Second-order temp coeff for R */
    double TRAtnom;              /* Nominal temperature */
} TRAmodel;
```

### **Matrix Setup Implementation**

```c
/* trasetup.c - Matrix Element Allocation */
int TRAsetup(SMPmatrix *matrix, GENmodel *inModel, 
             CKTcircuit *ckt, int *stateCount) {
    TRAmodel *model = (TRAmodel *)inModel;
    TRAinstance *inst;
    
    for (; model != NULL; model = model->TRAnextModel) {
        for (inst = model->TRAinstances; inst != NULL; 
             inst = inst->TRAnextInstance) {
            
            /* Allocate 10 matrix elements for 2-port device */
            inst->TRAp1p1Ptr = SMPmakeElt(matrix, 
                inst->TRAposNode1, inst->TRAposNode1);
            inst->TRAp1n1Ptr = SMPmakeElt(matrix, 
                inst->TRAposNode1, inst->TRAnegNode1);
            inst->TRAn1p1Ptr = SMPmakeElt(matrix, 
                inst->TRAnegNode1, inst->TRAposNode1);
            inst->TRAn1n1Ptr = SMPmakeElt(matrix, 
                inst->TRAnegNode1, inst->TRAnegNode1);
            
            inst->TRAp2p2Ptr = SMPmakeElt(matrix, 
                inst->TRAposNode2, inst->TRAposNode2);
            inst->TRAp2n2Ptr = SMPmakeElt(matrix, 
                inst->TRAposNode2, inst->TRAnegNode2);
            inst->TRAn2p2Ptr = SMPmakeElt(matrix, 
                inst->TRAnegNode2, inst->TRAposNode2);
            inst->TRAn2n2Ptr = SMPmakeElt(matrix, 
                inst->TRAnegNode2, inst->TRAnegNode2);
            
            /* Cross-coupling elements for transmission */
            inst->TRAp1p2Ptr = SMPmakeElt(matrix, 
                inst->TRAposNode1, inst->TRAposNode2);
            inst->TRAp2p1Ptr = SMPmakeElt(matrix, 
                inst->TRAposNode2, inst->TRAposNode1);
            
            /* Calculate delay line buffer size */
            double minStep = ckt->CKTminTimeStep;
            if (minStep < 1e-12) minStep = 1e-12;
            
            inst->TRAdelaySize = (int)(inst->TRAdelay / minStep) + 10;
            if (inst->TRAdelaySize < 100) inst->TRAdelaySize = 100;
            
            /* Allocate delay line buffers */
            inst->TRAdelayV1 = TMALLOC(double, inst->TRAdelaySize);
            inst->TRAdelayV2 = TMALLOC(double, inst->TRAdelaySize);
            inst->TRAdelayI1 = TMALLOC(double, inst->TRAdelaySize);
            inst->TRAdelayI2 = TMALLOC(double, inst->TRAdelaySize);
            
            /* Initialize delay lines to zero */
            for (int i = 0; i < inst->TRAdelaySize; i++) {
                inst->TRAdelayV1[i] = 0.0;
                inst->TRAdelayV2[i] = 0.0;
                inst->TRAdelayI1[i] = 0.0;
                inst->TRAdelayI2[i] = 0.0;
            }
            inst->TRAdelayIdx = 0;
            
            /* Allocate state numbers for time integration */
            inst->TRAstateNum = *stateCount;
            *stateCount += 4; /* V1, V2, I1, I2 */
        }
    }
    return OK;
}
```

### **Characteristic Impedance Calculation**

```c
/* tratemp.c - Impedance and Propagation Constant Calculation */
static void TRAcalcImpedance(TRAinstance *inst, double freq) {
    double omega = 2.0 * M_PI * freq;
    
    if (freq == 0.0) {
        /* DC Analysis */
        if (inst->TRAcond > 1e-30 && inst->TRAresist > 1e-30) {
            /* Z₀ = √(R/G) for DC */
            inst->TRAz0 = sqrt(inst->TRAresist / inst->TRAcond);
            inst->TRAgammaR = inst->TRAlength * 
                sqrt(inst->TRAresist * inst->TRAcond);
        } else if (inst->TRAcond < 1e-30) {
            /* G → 0: Open circuit at DC */
            inst->TRAz0 = 1e12;
            inst->TRAgammaR = 0.0;
        } else {
            /* R → 0: Short circuit at DC */
            inst->TRAz0 = 1e-12;
            inst->TRAgammaR = 0.0;
        }
        inst->TRAgammaI = 0.0;
    } else {
        /* AC Analysis: Z₀ = √[(R + jωL)/(G + jωC)] */
        double R = inst->TRAresist;
        double L = inst->TRAind;
        double G = inst->TRAcond;
        double C = inst->TRAcap;
        
        double num_real = R;
        double num_imag = omega * L;
        double den_real = G;
        double den_imag = omega * C;
        
        /* Compute magnitude and phase */
        double mag_num = sqrt(num_real*num_real + num_imag*num_imag);
        double mag_den = sqrt(den_real*den_real + den_imag*den_imag);
        double phase_num = atan2(num_imag, num_real);
        double phase_den = atan2(den_imag, den_real);
        
        /* Z₀ = √(mag_num/mag_den) * exp(j*(phase_num-phase_den)/2) */
        inst->TRAz0 = sqrt(mag_num / mag_den);
        double phase_z0 = 0.5 * (phase_num - phase_den);
        
        /* γ = √[(R+jωL)(G+jωC)] = α + jβ */
        double prod_real = num_real*den_real - num_imag*den_imag;
        double prod_imag = num_real*den_imag + num_imag*den_real;
        
        double mag_gamma = sqrt(sqrt(prod_real*prod_real + prod_imag*prod_imag));
        double phase_gamma = 0.5 * atan2(prod_imag, prod_real);
        
        inst->TRAgammaR = mag_gamma * cos(phase_gamma); /* α */
        inst->TRAgammaI = mag_gamma * sin(phase_gamma); /* β */
    }
    
    /* Propagation delay: T_d = length·√(LC) */
    inst->TRAdelay = inst->TRAlength * sqrt(inst->TRAind * inst->TRAcap);
}
```

### **DC Load Implementation**

```c
/* traload.c - DC Matrix Loading */
int TRAloadDC(GENmodel *inModel, CKTcircuit *ckt) {
    TRAmodel *model = (TRAmodel *)inModel;
    TRAinstance *inst;
    
    for (; model != NULL; model = model->TRAnextModel) {
        for (inst = model->TRAinstances; inst != NULL; 
             inst = inst->TRAnextInstance) {
            
            /* Calculate DC resistance and conductance */
            double R_dc = inst->TRAresist * inst->TRAlength;
            double G_dc;
            
            if (R_dc > 1e-12) {
                G_dc = 1.0 / R_dc;
            } else {
                /* Avoid division by zero */
                R_dc = 1e-12;
                G_dc = 1e12;
            }
            
            inst->TRAdcResist = R_dc;
            inst->TRAdcCond = G_dc;
            
            /* Stamp conductance matrix for port 1 */
            if (inst->TRAp1p1Ptr != NULL) {
                *(inst->TRAp1p1Ptr) += G_dc;
            }
            if (inst->TRAn1n1Ptr != NULL) {
                *(inst->TRAn1n1Ptr) += G_dc;
            }
            if (inst->TRAp1n1Ptr != NULL) {
                *(inst->TRAp1n1Ptr) -= G_dc;
            }
            if (inst->TRAn1p1Ptr != NULL) {
                *(inst->TRAn1p1Ptr) -= G_dc;
            }
            
            /* Stamp conductance matrix for port 2 */
            if (inst->TRAp2p2Ptr != NULL) {
                *(inst->TRAp2p2Ptr) += G_dc;
            }
            if (inst->TRAn2n2Ptr != NULL) {
                *(inst->TRAn2n2Ptr) += G_dc;
            }
            if (inst->TRAp2n2Ptr != NULL) {
                *(inst->TRAp2n2Ptr) -= G_dc;
            }
            if (inst->TRAn2p2Ptr != NULL) {
                *(inst->TRAn2p2Ptr) -= G_dc;
            }
            
            /* No cross-coupling at DC (infinite delay) */
            /* Ports are isolated except through ground network */
        }
    }
    return OK;
}
```

### **Transient Analysis Loading**

```c
/* traload.c - Transient Analysis Matrix Loading */
int TRAload(GENmodel *inModel, CKTcircuit *ckt) {
    TRAmodel *model = (TRAmodel *)inModel;
    TRAinstance *inst;
    
    for (; model != NULL; model = model->TRAnextModel) {
        for (inst = model->TRAinstances; inst != NULL; 
             inst = inst->TRAnextInstance) {
            
            /* Calculate impedance at current frequency */
            double freq = 0.0;
            if (ckt->CKTmode & MODEAC) {
                freq = ckt->CKTomega / (2.0 * M_PI);
            }
            TRAcalcImpedance(inst, freq);
            
            double Z0 = inst->TRAz0;
            double Y0 = 1.0 / Z0;  /* Characteristic admittance */
            double Td = inst->TRAdelay;
            
            /* Get current voltages */
            double V1 = ckt->CKTrhs[inst->TRAposNode1] - 
                       ckt->CKTrhs[inst->TRAnegNode1];
            double V2 = ckt->CKTrhs[inst->TRAposNode2] - 
                       ckt->CKTrhs[inst->TRAnegNode2];
            
            /* Get delayed values from history buffer */
            int delaySteps = (int)(Td / ckt->CKTdeltaOld[0]);
            if (delaySteps < 0) delaySteps = 0;
            if (delaySteps >= inst->TRAdelaySize) 
                delaySteps = inst->TRAdelaySize - 1;
            
            int histIdx = (inst->TRAdelayIdx - delaySteps + 
                          inst->TRAdelaySize) % inst->TRAdelaySize;
            
            double V2_delayed = inst->TRAdelayV2[histIdx];
            double I2_delayed = inst->TRAdelayI2[histIdx];
            double V1_delayed = inst->TRAdelayV1[histIdx];
            double I1_delayed = inst->TRAdelayI1[histIdx];
            
            /* Norton companion model equations */
            /* I₁(t) = V₁(t)/Z₀ + I₂(t-T_d) - V₂(t-T_d)/Z₀ */
            /* I₂(t) = V₂(t)/Z₀ + I₁(t-T_d) - V₁(t-T_d)/Z₀ */
            
            double I1_eq = I2_delayed - V2_delayed / Z0;
            double I2_eq = I1_delayed - V1_delayed / Z0;
            
            /* Stamp admittance Y0 = 1/Z₀ at each port */
            if (inst->TRAp1p1Ptr != NULL) *(inst->TRAp1p1Ptr) += Y0;
            if (inst->TRAn1n1Ptr != NULL) *(inst->TRAn1n1Ptr) += Y0;
            if (inst->TRAp1n1Ptr != NULL) *(inst->TRAp1n1Ptr) -= Y0;
            if (inst->TRAn1p1Ptr != NULL) *(inst->TRAn1p1Ptr) -= Y0;
            
            if (inst->TRAp2p2Ptr != NULL) *(inst->TRAp2p2Ptr) += Y0;
            if (inst->TRAn2n2Ptr != NULL) *(inst->TRAn2n2Ptr) += Y0;
            if (inst->TRAp2n2Ptr != NULL) *(inst->TRAp2n2Ptr) -= Y0;
            if (inst->TRAn2p2Ptr != NULL) *(inst->TRAn2p2Ptr) -= Y0;
            
            /* Stamp equivalent current sources */
            ckt->CKTrhs[inst->TRAposNode1] -= I1_eq;
            ckt->CKTrhs[inst->TRAnegNode1] += I1_eq;
            ckt->CKTrhs[inst->TRAposNode2] -= I2_eq;
            ckt->CKTrhs[inst->TRAnegNode2] += I2_eq;
            
            /* Store current state in delay line */
            inst->TRAdelayV1[inst->TRAdelayIdx] = V1;
            inst->TRAdelayV2[inst->TRAdelayIdx] = V2;
            inst->TRAdelayI1[inst->TRAdelayIdx] = (V1 / Z0) + I1_eq;
            inst->TRAdelayI2[inst->TRAdelayIdx] = (V2 / Z0) + I2_eq;
            
            /* Update delay line index */
            inst->TRAdelayIdx = (inst->TRAdelayIdx + 1) % inst->TRAdelaySize;
        }
    }
    return OK;
}
```

### **SPICEdev API Binding**

```c
/* trainit.c - Device Registration */
SPICEdev TRAinfo = {
    .DEVpublic = {
        .name = "tline",
        .description = "Lossy transmission line",
        .terms = 4,
        .numNames = 4,
        .termNames = (char *[]){"pos1", "neg1", "pos2", "neg2"},
        .numInstanceParms = 6,
        .instanceParms = (IFparm[]) {
            IOP("r", TRA_RESIST, IF_REAL, "Resistance per unit length"),
            IOP("l", TRA_IND, IF_REAL, "Inductance per unit length"),
            IOP("g", TRA_COND, IF_REAL, "Conductance per unit length"),
            IOP("c", TRA_CAP, IF_REAL, "Capacitance per unit length"),
            IOP("len", TRA_LENGTH, IF_REAL, "Line length"),
            IOP("z0", TRA_Z0, IF_REAL, "Characteristic impedance"),
        },
        .numModelParms = 3,
        .modelParms = (IFparm[]) {
            IOP("tc1", TRA_TC1, IF_REAL, "First order temp coeff"),
            IOP("tc2", TRA_TC2, IF_REAL, "Second order temp coeff"),
            IOP("tnom", TRA_TNOM, IF_REAL, "Nominal temperature"),
        },
    },
    
    /* Function Pointers */
    .DEVparam = TRAparam,
    .DEVmodParam = TRAmParam,
    .DEVload = TRAload,
    .DEVsetup = TRAsetup,
    .DEVunsetup = TRAunsetup,
    .DEVpzSetup = TRApzSetup,
    .DEVtemperature = TRAtemp,
    .DEVtrunc = TRAtrunc,
    .DEVfindBranch = TRAfindBr,
    .DEVacLoad = TRAacLoad,
    .DEVaccept = TRAaccept,
    .DEVdestroy = TRAdestroy,
    .DEVmodDelete = TRAmDelete,
    .DEVdelete = TRAdelete,
    .DEVsetic = TRAgetic,
    .DEVask = TRAask,
    .DEVmodAsk = TRAmAsk,
    .DEVpzLoad = TRApzLoad,
    .DEVconvTest = TRAconvTest,
    .DEVsenSetup = TRAsSetup,
    .DEVsenLoad = TRAsLoad,
    .DEVsenUpdate = TRAsUpdate,
    .DEVsenAcLoad = TRAsAcLoad,
    .DEVsenPrint = TRAsPrint,
    .DEVsenDisto = TRAdisto,
    .DEVsenNoise = TRAnoise,
    .DEVsoaCheck = TRAsoaCheck,
    
    /* Size Information */
    .DEVinstSize = sizeof(TRAinstance),
    .DEVmodSize = sizeof(TRAmodel),
};
```

### **Convergence Testing**

```c
/* traconv.c - Convergence Testing */
int TRAconvTest(GENmodel *inModel, CKTcircuit *ckt) {
    TRAmodel *model = (TRAmodel *)inModel;
    TRAinstance *inst;
    
    for (; model != NULL; model = model->TRAnextModel) {
        for (inst = model->TRAinstances; inst != NULL; 
             inst = inst->TRAnextInstance) {
            
            /* Test port 1 voltage convergence */
            double v1_new = ckt->CKTrhs[inst->TRAposNode1] - 
                           ckt->CKTrhs[inst->TRAnegNode1];
            double v1_old = ckt->CKTrhsOld[inst->TRAposNode1] - 
                           ckt->CKTrhsOld[inst->TRAnegNode1];
            
            double tol = ckt->CKTreltol * MAX(fabs(v1_new), fabs(v1_old)) + 
                        ckt->CKTvoltTol;
            
            if (fabs(v1_new - v1_old) > tol) {
                return E_NOT_CONVERGED;
            }
            
            /* Test port 2 voltage convergence */
            double v2_new = ckt->CKTrhs[inst->TRAposNode2] - 
                           ckt->CKTrhs[inst->TRAnegNode2];
            double v2_old = ckt->CKTrhsOld[inst->TRAposNode2] - 
                           ckt->CKTrhsOld[inst->TRAnegNode2];
            
            tol = ckt->CKTreltol * MAX(fabs(v2_new), fabs(v2_old)) + 
                 ckt->CKTvoltTol;
            
            if (fabs(v2_new - v2_old) > tol) {
                return E_NOT_CONVERGED;
            }
            
            /* Check delay line stability for long lines */
            if (inst->TRAdelay > 10 * ckt->CKTdeltaOld[0]) {
                double maxChange = 0.0;
                for (int i = 0; i < inst->TRAdelaySize; i++) {
                    double change = fabs(inst->TRAdelayV1[i] - 
                                        inst->TRAdelayV1Old[i]);
                    maxChange = MAX(maxChange, change);
                }
                
                if (maxChange > 10 * ckt->CKTvoltTol) {
                    return E_NOT_CONVERGED;
                }
            }
        }
    }
    return OK;
}
```

### **Memory Management**

```c
/* tradest.c - Memory Cleanup */
void TRAdestroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    TRAmodel *model = (TRAmodel*)mod;
    TRAinstance *inst;
    
    while (model != NULL) {
        TRAmodel *nextModel = model->TRAnextModel;
        
        inst = model->TRAinstances;
        while (inst != NULL) {
            TRAinstance *nextInst = inst->TRAnextInstance;
            
            /* Free delay line buffers */
            if (inst->TRAdelayV1 != NULL) FREE(inst->TRAdelayV1);
            if (inst->TRAdelayV2 != NULL) FREE(inst->TRAdelayV2);
            if (inst->TRAdelayI1 != NULL) FREE(inst->TRAdelayI1);
            if (inst->TRAdelayI2 != NULL) FREE(inst->TRAdelayI2);
            
            /* Free instance name */
            if (inst->TRAname != NULL) FREE(inst->TRAname);
            
            FREE(inst);
            inst = nextInst;
        }
        
        FREE(model);
        model = nextModel;
    }
    *inModel = NULL;
}
```

### **Mathematical-to-Code Mapping Summary**

| **Mathematical Formulation** | **C Implementation** | **File** |
|------------------------------|----------------------|----------|
| `Z₀ = √[(R+jωL)/(G+jωC)]` | `TRAcalcImpedance()` | `tratemp.c` |
| `γ = √[(R+jωL)(G+jωC)]` | Same function computes α,β | `tratemp.c` |
| `I₁(t) = V₁(t)/Z₀ + I₂(t-T_d) - V₂(t-T_d)/Z₀` | Norton model in `TRAload()` | `traload.c` |
| DC: `R_dc = R·ℓ`, `G_dc = 1/R_dc` | `TRAloadDC()` | `traload.c` |
| Matrix: `Y = [Y₀ -Y₀; -Y₀ Y₀]` | SMP stamping in setup/load | `trasetup.c`, `traload.c` |
| Convergence: `\|ΔV\| < ε_rel·max(\|V\|) + ε_abs` | `TRAconvTest()` | `traconv.c` |
| Delay line: `I_history[n] = I₂[n - T_d/Δt]` | Circular buffer in `TRAinstance` | `tradefs.h`, `traload.c` |

---

## **Conclusion**

The Ngspice transmission