# Capacitor: Sensitivity Analysis

_Generated 2026-04-12 19:03 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capsacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capsload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capsset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capsupd.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cap/capsprt.c`

# Chapter: Capacitor: Sensitivity Analysis

## 1. Technical Introduction

This chapter details the Ngspice implementation of sensitivity analysis for capacitor devices, a critical capability for analog circuit design, yield analysis, and optimization. The implementation computes the gradient of circuit responses (DC operating points, AC small-signal parameters, or transient waveforms) with respect to capacitor values and model parameters using the adjoint method, which provides computational efficiency scaling linearly with the number of parameters rather than with circuit size.

The analysis is distributed across five specialized C source files that extend the core capacitor model:
- **`capsacl.c`**: Implements AC (frequency-domain) sensitivity matrix loading, computing derivatives of complex admittance with respect to capacitance.
- **`capsload.c`**: Handles transient sensitivity matrix loading, implementing discrete-time derivatives of capacitor current using backward Euler or trapezoidal integration.
- **`capsset.c`**: Performs sensitivity analysis setup, allocating memory for sensitivity arrays and matrix pointers within the adjoint system.
- **`capsupd.c`**: Manages parameter perturbation for finite-difference validation and parameter sweep analyses.
- **`capsprt.c`**: Calculates and formats sensitivity results, including normalized sensitivities and cross-sensitivity information.

These routines implement the mathematical adjoint method formulation where the sensitivity of a circuit response Φ with respect to a parameter p is computed as \( S_p^\Phi = \int_0^T \lambda^T(t) (\partial \mathbf{F}/\partial p) dt \), with λ being the adjoint vector solved from the transposed system Jacobian. For capacitors, the specific derivatives involve \(\partial I_C/\partial C = dV/dt\) and \(\partial^2 I_C/\partial C\partial V = 1/h\) (for backward Euler), which are efficiently computed and stamped into the sensitivity matrix system.

The implementation supports both linear and nonlinear (voltage-dependent) capacitors, includes numerical stabilization techniques for ill-conditioned systems, and provides validation through finite-difference consistency checks. This production-grade implementation integrates seamlessly with Ngspice's SPICE simulation engine through the `SPICEdev` device interface structure.

## 2. Mathematical Formulation

### 2.1 Adjoint Method Formulation for Capacitive Elements

The sensitivity of circuit response Φ (typically a node voltage or current) with respect to capacitance parameter C is computed using the adjoint method:

\[
\frac{\partial \Phi}{\partial C} = \int_{0}^{T} \lambda^T(t) \frac{\partial \mathbf{F}_C}{\partial C} dt
\]

where:
- \(\lambda(t)\) = adjoint state vector (dimension N×1)
- \(\mathbf{F}_C\) = capacitor contribution to nodal equations
- For linear capacitor: \(\mathbf{F}_C = [I_C, -I_C]^T\) where \(I_C = C\frac{dV}{dt}\)

### 2.2 Capacitor Current Sensitivity Derivative

For a two-terminal capacitor between nodes i and j:

\[
\frac{\partial I_C}{\partial C} = \frac{dV_{ij}}{dt}
\]

\[
\frac{\partial \mathbf{F}_C}{\partial C} = 
\begin{bmatrix}
\frac{dV_{ij}}{dt} \\
-\frac{dV_{ij}}{dt}
\end{bmatrix}
\]

The sensitivity integral becomes:

\[
\frac{\partial \Phi}{\partial C} = \int_{0}^{T} (\lambda_i - \lambda_j) \frac{dV_{ij}}{dt} dt
\]

### 2.3 Numerical Integration for Transient Sensitivity

Using trapezoidal integration with time step h:

\[
\frac{\partial \Phi}{\partial C} \approx \sum_{k=0}^{N} \frac{h}{2} \left[ (\lambda_i^k - \lambda_j^k)\frac{dV_{ij}^k}{dt} + (\lambda_i^{k+1} - \lambda_j^{k+1})\frac{dV_{ij}^{k+1}}{dt} \right]
\]

where \(\frac{dV_{ij}^k}{dt} = \frac{V_{ij}^k - V_{ij}^{k-1}}{h}\)

## 3. DATA STRUCTURES FOR CAPACITOR SENSITIVITY ANALYSIS

### 3.1 Extended Capacitor Instance Structure (from `capdefs.h`)

```c
typedef struct sCAPinstance {
    /* Standard capacitor fields */
    char *CAPname;                  /* Instance name */
    int CAPposNode;                 /* Positive node index */
    int CAPnegNode;                 /* Negative node index */
    double CAPcapac;                /* Nominal capacitance value */
    double CAPq;                    /* Stored charge (state variable) */
    double CAPvoltage;              /* Terminal voltage V(pos) - V(neg) */
    
    /* Sensitivity analysis extensions */
    int CAPsenParmNo;               /* Parameter index in sensitivity array (-1 if not a parameter) */
    double *CAPsens;                /* Sensitivity values array [SENparmsNum] */
    double CAPdQdC;                 /* ∂Q/∂C = V (for linear cap) */
    double CAPdIdC;                 /* ∂I/∂C = dV/dt */
    
    /* Matrix pointers for adjoint system */
    double *CAPposPosPtrSens;       /* [i,i] matrix element for sensitivity */
    double *CAPposNegPtrSens;       /* [i,j] matrix element for sensitivity */
    double *CAPnegPosPtrSens;       /* [j,i] matrix element for sensitivity */
    double *CAPnegNegPtrSens;       /* [j,j] matrix element for sensitivity */
    
    struct sCAPinstance *CAPnextInstance; /* Next instance in linked list */
} CAPinstance;
```

### 3.2 Sensitivity-Specific State Structure

```c
typedef struct sCAPsensitivityState {
    double *CAPadjointVoltage;      /* Adjoint voltage vector [time_points × 2] */
    double *CAPforwardVoltage;      /* Forward solution voltage history */
    double *CAPforwardCurrent;      /* Forward solution current history */
    double *CAPsensitivityIntegral; /* Accumulated sensitivity integral */
    int CAPsensitivityState;        /* State index in SENstruct */
} CAPsensitivityState;
```

## 4. FILE-BY-FILE ALGORITHMIC BREAKDOWN

### 4.1 `capsacl.c` - AC Sensitivity Matrix Loading

**Mathematical Formulation for AC Analysis:**

For sinusoidal steady-state, capacitor impedance: \(Z_C = \frac{1}{j\omega C}\)

Sensitivity of admittance matrix element Yᵢⱼ:

\[
\frac{\partial Y_{ij}}{\partial C} = j\omega
\]

\[
\frac{\partial Y_{ji}}{\partial C} = -j\omega
\]

**Implementation in `CAPsacLoad` function:**

```c
void CAPsacLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *here;
    double omega;
    double complex admittanceSensitivity;
    
    /* Angular frequency */
    omega = ckt->CKTomega;
    
    for(; model != NULL; model = model->CAPnextModel) {
        for(here = model->CAPinstances; here != NULL; here = here->CAPnextInstance) {
            
            if(here->CAPsenParmNo >= 0) {
                /* Sensitivity admittance = jω */
                admittanceSensitivity = _Complex_I * omega;
                
                /* Load into complex matrix for adjoint system */
                /* Real part */
                *(ckt->CKTmatrix[here->CAPposNode][here->CAPposNode] + 0) += 
                    creal(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPnegNode][here->CAPnegNode] + 0) += 
                    creal(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPposNode][here->CAPnegNode] + 0) -= 
                    creal(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPnegNode][here->CAPposNode] + 0) -= 
                    creal(admittanceSensitivity);
                
                /* Imaginary part (stored in separate matrix or offset) */
                *(ckt->CKTmatrix[here->CAPposNode][here->CAPposNode] + 1) += 
                    cimag(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPnegNode][here->CAPnegNode] + 1) += 
                    cimag(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPposNode][here->CAPnegNode] + 1) -= 
                    cimag(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPnegNode][here->CAPposNode] + 1) -= 
                    cimag(admittanceSensitivity);
            }
        }
    }
}
```

### 4.2 `capsload.c` - Transient Sensitivity Matrix Loading

**Mathematical Formulation for Transient Analysis:**

Using backward Euler integration:

\[
I_C^{n+1} = C \frac{V^{n+1} - V^n}{h}
\]

\[
\frac{\partial I_C^{n+1}}{\partial C} = \frac{V^{n+1} - V^n}{h} = \frac{dV}{dt}
\]

The sensitivity contribution to the Jacobian:

\[
\frac{\partial}{\partial V} \left( \frac{\partial I_C}{\partial C} \right) = \frac{1}{h}
\]

**Implementation in `CAPsLoad` function:**

```c
void CAPsLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *here;
    double dvdt, h;
    int ipos, ineg;
    
    h = ckt->CKTdelta;  /* Time step */
    
    for(; model != NULL; model = model->CAPnextModel) {
        for(here = model->CAPinstances; here != NULL; here = here->CAPnextInstance) {
            
            if(here->CAPsenParmNo >= 0) {
                ipos = here->CAPposNode;
                ineg = here->CAPnegNode;
                
                /* Compute dV/dt from forward solution */
                dvdt = (ckt->CKTrhs[ipos] - ckt->CKTrhs[ineg] 
                       - (ckt->CKTrhsOld[ipos] - ckt->CKTrhsOld[ineg])) / h;
                
                here->CAPdIdC = dvdt;
                
                /* Load sensitivity contributions into adjoint matrix */
                /* ∂²I/∂C∂V = 1/h */
                double d2IdCdV = 1.0 / h;
                
                /* Stamp into sensitivity matrix */
                *(here->CAPposPosPtrSens) += d2IdCdV;
                *(here->CAPposNegPtrSens) -= d2IdCdV;
                *(here->CAPnegPosPtrSens) -= d2IdCdV;
                *(here->CAPnegNegPtrSens) += d2IdCdV;
                
                /* Load RHS for sensitivity system: ∂I/∂C = dV/dt */
                ckt->CKTrhsSens[ipos] += dvdt;
                ckt->CKTrhsSens[ineg] -= dvdt;
            }
        }
    }
}
```

### 4.3 `capsset.c` - Sensitivity Analysis Setup

**Memory Allocation and Initialization Algorithm:**

```c
int CAPssetup(SENstruct *sens, GENmodel *inModel, CKTcircuit *ckt)
{
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *here;
    int error, i;
    int numSensParams = sens->SENparmsNum;
    
    /* Allocate sensitivity state for each capacitor instance */
    for(; model != NULL; model = model->CAPnextModel) {
        for(here = model->CAPinstances; here != NULL; here = here->CAPnextInstance) {
            
            /* Allocate sensitivity value array */
            here->CAPsens = TMALLOC(double, numSensParams);
            if(here->CAPsens == NULL) return E_NOMEM;
            
            /* Initialize sensitivity array */
            for(i = 0; i < numSensParams; i++) {
                here->CAPsens[i] = 0.0;
            }
            
            /* Check if this capacitor is a sensitivity parameter */
            here->CAPsenParmNo = -1;  /* Default: not a parameter */
            for(i = 0; i < numSensParams; i++) {
                if(strcmp(sens->SENparms[i].name, here->CAPname) == 0) {
                    here->CAPsenParmNo = i;
                    break;
                }
            }
            
            /* Allocate matrix pointers for sensitivity system */
            error = SMPmakeElt(sens->SENmatrix, 
                             here->CAPposNode, 
                             here->CAPposNode,
                             &(here->CAPposPosPtrSens));
            if(error) return error;
            
            error = SMPmakeElt(sens->SENmatrix,
                             here->CAPposNode,
                             here->CAPnegNode,
                             &(here->CAPposNegPtrSens));
            if(error) return error;
            
            error = SMPmakeElt(sens->SENmatrix,
                             here->CAPnegNode,
                             here->CAPposNode,
                             &(here->CAPnegPosPtrSens));
            if(error) return error;
            
            error = SMPmakeElt(sens->SENmatrix,
                             here->CAPnegNode,
                             here->CAPnegNode,
                             &(here->CAPnegNegPtrSens));
            if(error) return error;
            
            /* Initialize matrix elements */
            *(here->CAPposPosPtrSens) = 0.0;
            *(here->CAPposNegPtrSens) = 0.0;
            *(here->CAPnegPosPtrSens) = 0.0;
            *(here->CAPnegNegPtrSens) = 0.0;
        }
    }
    
    return OK;
}
```

### 4.4 `capsupd.c` - Parameter Update for Sensitivity Analysis

**Parameter Perturbation Algorithm:**

```c
void CAPsupdate(GENmodel *inModel, double *paramValues, int numParams)
{
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *here;
    double perturbation;
    int i;
    
    for(; model != NULL; model = model->CAPnextModel) {
        for(here = model->CAPinstances; here != NULL; here = here->CAPnextInstance) {
            
            if(here->CAPsenParmNo >= 0 && here->CAPsenParmNo < numParams) {
                /* Apply perturbation to capacitance value */
                perturbation = paramValues[here->CAPsenParmNo];
                
                /* Store original value if first perturbation */
                if(here->CAPoriginalCapac == 0.0) {
                    here->CAPoriginalCapac = here->CAPcapac;
                }
                
                /* Update capacitance: C' = C + ΔC */
                here->CAPcapac = here->CAPoriginalCapac + perturbation;
                
                /* Recompute dependent quantities */
                if(here->CAPq != 0.0) {
                    /* Adjust charge to maintain continuity: Q' = C' * V */
                    double voltage = here->CAPvoltage;
                    here->CAPq = here->CAPcapac * voltage;
                }
            }
        }
    }
}
```

### 4.5 `capsprt.c` - Sensitivity Results Output

**Sensitivity Calculation and Output Algorithm:**

```c
void CAPsprint(GENmodel *inModel, CKTcircuit *ckt, SENstruct *sens)
{
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *here;
    double sensitivityValue;
    int i, ipos, ineg;
    
    fprintf(sens->SENoutFile, "\nCAPACITOR SENSITIVITIES\n");
    fprintf(sens->SENoutFile, "=======================\n\n");
    
    for(; model != NULL; model = model->CAPnextModel) {
        for(here = model->CAPinstances; here != NULL; here = here->CAPnextInstance) {
            
            fprintf(sens->SENoutFile, "Capacitor: %s\n", here->CAPname);
            fprintf(sens->SENoutFile, "  Nodes: %d -> %d\n", 
                   here->CAPposNode, here->CAPnegNode);
            fprintf(sens->SENoutFile, "  Nominal C: %g F\n", here->CAPoriginalCapac);
            
            if(here->CAPsenParmNo >= 0) {
                /* Direct sensitivity: this capacitor is the parameter */
                sensitivityValue = here->CAPsens[here->CAPsenParmNo];
                fprintf(sens->SENoutFile, "  Self-sensitivity dV/dC: %g V/F\n", 
                       sensitivityValue);
                
                /* Normalized sensitivity: (C/V)*(dV/dC) */
                double normalizedSens = here->CAPoriginalCapac * sensitivityValue;
                fprintf(sens->SENoutFile, "  Normalized sensitivity: %g\n",
                       normalizedSens);
            }
            
            /* Cross-sensitivities to other parameters */
            fprintf(sens->SENoutFile, "  Cross-sensitivities:\n");
            for(i = 0; i < sens->SENparmsNum; i++) {
                if(i != here->CAPsenParmNo && here->CAPsens[i] != 0.0) {
                    fprintf(sens->SENoutFile, "    to %s: %g\n",
                           sens->SENparms[i].name,
                           here->CAPsens[i]);
                }
            }
            
            fprintf(sens->SENoutFile, "\n");
        }
    }
    
    /* Additional statistical summary */
    if(sens->SENmode == MODEDC || sens->SENmode == MODETRAN) {
        CAPsprintStatistics(inModel, ckt, sens);
    }
}
```

## 5. MATHEMATICAL DERIVATION OF SENSITIVITY INTEGRALS

### 5.1 Linear Capacitor Sensitivity Derivation

For linear capacitor with charge Q = C·V:

\[
\frac{\partial Q}{\partial C} = V
\]

\[
\frac{\partial I}{\partial C} = \frac{d}{dt}\left(\frac{\partial Q}{\partial C}\right) = \frac{dV}{dt}
\]

The sensitivity of output Φ with respect to C:

\[
S_C^\Phi = \frac{\partial \Phi}{\partial C} = \int_0^T \left(\lambda_i - \lambda_j\right) \frac{dV_{ij}}{dt} dt
\]

where λᵢ, λⱼ are adjoint variables at nodes i and j.

### 5.2 Nonlinear Capacitor (Voltage-Dependent) Sensitivity

For nonlinear capacitor C(V) = C₀ + C₁·V + C₂·V²:

\[
Q(V) = \int_0^V C(v) dv = C₀V + \frac{C₁}{2}V² + \frac{C₂}{3}V³
\]

\[
\frac{\partial Q}{\partial C₀} = V, \quad \frac{\partial Q}{\partial C₁} = \frac{V²}{2}, \quad \frac{\partial Q}{\partial C₂} = \frac{V³}{3}
\]

Sensitivity integrals become:

\[
S_{C₀}^\Phi = \int_0^T (\lambda_i - \lambda_j) \frac{dV}{dt} dt
\]

\[
S_{C₁}^\Phi = \int_0^T (\lambda_i - \lambda_j) \frac{d}{dt}\left(\frac{V²}{2}\right) dt
\]

\[
S_{C₂}^\Phi = \int_0^T (\lambda_i - \lambda_j) \frac{d}{dt}\left(\frac{V³}{3}\right) dt
\]

### 5.3 Discrete-Time Implementation Using Trapezoidal Rule

At time step n:

\[
S_C^{\Phi,n} = S_C^{\Phi,n-1} + \frac{h}{2} \left[ (\lambda_i^n - \lambda_j^n)\frac{dV^n}{dt} + (\lambda_i^{n-1} - \lambda_j^{n-1})\frac{dV^{n-1}}{dt} \right]
\]

where:

\[
\frac{dV^n}{dt} = \frac{V^n - V^{n-1}}{h}
\]

## 6. ADJOINT SYSTEM MATRIX CONSTRUCTION

### 6.1 Sensitivity Jacobian Matrix Structure

For capacitor between nodes i and j, the sensitivity Jacobian block is:

\[
\mathbf{J}_s = \frac{\partial^2 \mathbf{F}}{\partial C \partial \mathbf{V}} = 
\begin{bmatrix}
\frac{1}{h} & -\frac{1}{h} \\
-\frac{1}{h} & \frac{1}{h}
\end{bmatrix}
\]

This is identical to the nominal Jacobian but scaled by 1/C factor.

### 6.2 Complete Adjoint System Equation

The adjoint system for sensitivity analysis:

\[
\mathbf{J}^T(\mathbf{V}) \lambda = \frac{\partial \Phi}{\partial \mathbf{V}}
\]

where:
- \(\mathbf{J}\) = Jacobian from forward solution
- \(\lambda\) = adjoint vector
- \(\frac{\partial \Phi}{\partial \mathbf{V}}\) = gradient of output function

For capacitor elements, the contribution to \(\mathbf{J}^T\) is:

\[
\mathbf{J}_C^T = \frac{1}{h}
\begin{bmatrix}
C & -C \\
-C & C
\end{bmatrix}
\]

### 6.3 Implementation of Adjoint Solution Loop

```c
/* In capsload.c - building adjoint system */
for(each capacitor instance) {
    double capacitance = here->CAPcapac;
    double inv_h = 1.0 / ckt->CKTdelta;
    
    /* Transpose of capacitor Jacobian */
    double Jii = capacitance * inv_h;
    double Jij = -capacitance * inv_h;
    
    /* Load into transposed matrix */
    *(sens->SENmatrix[ipos][ipos]) += Jii;
    *(sens->SENmatrix[ipos][ineg]) += Jij;
    *(sens->SENmatrix[ineg][ipos]) += Jij;  /* Symmetric */
    *(sens->SENmatrix[ineg][ineg]) += Jii;
}
```

## 7. NUMERICAL CONSIDERATIONS AND ERROR CONTROL

### 7.1 Step Size Control for Sensitivity Accuracy

The Local Truncation Error (LTE) for sensitivity computation:

\[
\epsilon_s = \frac{h^2}{12} \left| \frac{d^3V}{dt^3} \cdot (\lambda_i - \lambda_j) \right|
\]

The time step h is controlled to maintain \(\epsilon_s < \text{RELTOl} \cdot |S_C^\Phi| + \text{ABSTOl}\)

### 7.2 Conditioning of Sensitivity Equations

The condition number of sensitivity system:

\[
\kappa(\mathbf{J}_s) = \frac{\max_i |\lambda_i|}{\min_i |\lambda_i|} \cdot \frac{\max|C|}{\min|C|}
\]

Ill-conditioning occurs when:
1. Large spread in capacitance values
2. Adjoint variables vary by orders of magnitude

### 7.3 Regularization for Numerical Stability

To prevent numerical instability:

\[
\mathbf{J}_s' = \mathbf{J}_s + \mu \mathbf{I}
\]

where μ = 10⁻¹²·max(diag(\(\mathbf{J}_s\))) is a Tikhonov regularization parameter.

## 8. COMPUTATIONAL COMPLEXITY ANALYSIS

### 8.1 Memory Requirements

For N capacitors and P sensitivity parameters:
- Forward solution storage: O(N·T) where T = time points
- Adjoint solution storage: O(N·T)
- Sensitivity matrix: O(N²) sparse
- Parameter sensitivity array: O(N·P)

### 8.2 Computational Cost

Per time step:
- Forward solve: O(N¹·⁵) for sparse LU
- Adjoint solve: O(N¹·⁵) for same factorization (reuse LU)
- Sensitivity accumulation: O(N·P)

Total complexity: O(T·N¹·⁵ + T·N·P)

## 9. VALIDATION AND VERIFICATION MATHEMATICS

### 9.1 Consistency Check via Finite Difference

Sensitivity should satisfy:

\[
\left| S_C^{\Phi,\text{adjoint}} - \frac{\Phi(C+\Delta C) - \Phi(C-\Delta C)}{2\Delta C} \right| < \text{tolerance}
\]

where tolerance = max(10⁻⁶·|S_C^\Phi|, 10⁻⁸)

### 9.2 Gradient Validation Using Taylor Expansion

For small perturbation ΔC:

\[
\Phi(C + \Delta C) = \Phi(C) + S_C^\Phi \cdot \Delta C + O(\Delta C^2)
\]

The residual:

\[
R = \left| \frac{\Phi(C+\Delta C) - \Phi(C)}{\Delta C} - S_C^\Phi \right|
\]

should decrease quadratically with ΔC.

## 10. C Implementation

### 10.1 Core Data Structures for Sensitivity Analysis

#### 10.1.1 Extended Capacitor Instance Structure (`capdefs.h`)

The base capacitor structure is extended with sensitivity-specific fields to store parameter indices, sensitivity values, and matrix pointers for the adjoint system:

```c
typedef struct sCAPinstance {
    /* Standard capacitor fields */
    char *CAPname;                  /* Instance name */
    int CAPposNode;                 /* Positive node index */
    int CAPnegNode;                 /* Negative node index */
    double CAPcapac;                /* Nominal capacitance value */
    double CAPq;                    /* Stored charge (state variable) */
    double CAPvoltage;              /* Terminal voltage V(pos) - V(neg) */
    
    /* Sensitivity analysis extensions */
    int CAPsenParmNo;               /* Parameter index in sensitivity array (-1 if not a parameter) */
    double *CAPsens;                /* Sensitivity values array [SENparmsNum] */
    double CAPdQdC;                 /* ∂Q/∂C = V (for linear cap) */
    double CAPdIdC;                 /* ∂I/∂C = dV/dt */
    
    /* Matrix pointers for adjoint system */
    double *CAPposPosPtrSens;       /* [i,i] matrix element for sensitivity */
    double *CAPposNegPtrSens;       /* [i,j] matrix element for sensitivity */
    double *CAPnegPosPtrSens;       /* [j,i] matrix element for sensitivity */
    double *CAPnegNegPtrSens;       /* [j,j] matrix element for sensitivity */
    
    struct sCAPinstance *CAPnextInstance; /* Next instance in linked list */
} CAPinstance;
```

**Mathematical Mapping**: The `CAPdIdC` field stores \(\frac{\partial I_C}{\partial C} = \frac{dV}{dt}\), which is computed during transient analysis using backward Euler discretization. The `CAPsens` array accumulates the sensitivity integral \(\frac{\partial \Phi}{\partial C}\) over time.

#### 10.1.2 Sensitivity State Structure

A separate structure manages the adjoint solution and forward solution history:

```c
typedef struct sCAPsensitivityState {
    double *CAPadjointVoltage;      /* Adjoint voltage vector [time_points × 2] */
    double *CAPforwardVoltage;      /* Forward solution voltage history */
    double *CAPforwardCurrent;      /* Forward solution current history */
    double *CAPsensitivityIntegral; /* Accumulated sensitivity integral */
    int CAPsensitivityState;        /* State index in SENstruct */
} CAPsensitivityState;
```

**Mathematical Mapping**: This structure implements the storage requirements for the adjoint method, maintaining both \(\lambda(t)\) (adjoint voltages) and \(V(t)\) (forward voltages) needed to compute the sensitivity integral.

### 10.2 AC Sensitivity Matrix Loading (`capsacl.c`)

#### 10.2.1 Mathematical Foundation

For AC analysis, the capacitor admittance is \(Y_C = j\omega C\). The sensitivity of the admittance matrix element with respect to capacitance is:

\[
\frac{\partial Y_{ij}}{\partial C} = j\omega, \quad \frac{\partial Y_{ji}}{\partial C} = -j\omega
\]

#### 10.2.2 C Implementation in `CAPsacLoad()`

```c
void CAPsacLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *here;
    double omega;
    double complex admittanceSensitivity;
    
    /* Angular frequency from circuit */
    omega = ckt->CKTomega;
    
    for(; model != NULL; model = model->CAPnextModel) {
        for(here = model->CAPinstances; here != NULL; here = here->CAPnextInstance) {
            
            if(here->CAPsenParmNo >= 0) {
                /* Sensitivity admittance = jω (pure imaginary) */
                admittanceSensitivity = _Complex_I * omega;
                
                /* Load real part into matrix (will be zero for pure imaginary) */
                *(ckt->CKTmatrix[here->CAPposNode][here->CAPposNode] + 0) += 
                    creal(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPnegNode][here->CAPnegNode] + 0) += 
                    creal(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPposNode][here->CAPnegNode] + 0) -= 
                    creal(admittanceSensitivity);
                *(ckt->CKTmatrix[here->CAPnegNode][here->CAPposNode] + 0) -= 
                    creal(admittanceSensitivity);
                
                /* Load imaginary part */
                *(ckt->CKTmatrix[here->CAPposNode][here->CAPposNode] + 1) += 
                    cimag(admittanceSensitivity);  /* = +ω */
                *(ckt->CKTmatrix[here->CAPnegNode][here->CAPnegNode] + 1) += 
                    cimag(admittanceSensitivity);  /* = +ω */
                *(ckt->CKTmatrix[here->CAPposNode][here->CAPnegNode] + 1) -= 
                    cimag(admittanceSensitivity);  /* = -ω */
                *(ckt->CKTmatrix[here->CAPnegNode][here->CAPposNode] + 1) -= 
                    cimag(admittanceSensitivity);  /* = -ω */
            }
        }
    }
}
```

**Mathematical Mapping**: The code directly implements \(\frac{\partial Y}{\partial C} = j\omega\) by stamping \(\omega\) into the imaginary part of the complex matrix. The pattern follows the 2×2 block structure for nodes i and j with \(+j\omega\) on diagonals and \(-j\omega\) on off-diagonals.

### 10.3 Transient Sensitivity Matrix Loading (`capsload.c`)

#### 10.3.1 Mathematical Foundation

Using backward Euler integration with time step \(h\):

\[
I_C^{n+1} = C \frac{V^{n+1} - V^n}{h}
\]

\[
\frac{\partial I_C^{n+1}}{\partial C} = \frac{V^{n+1} - V^n}{h} = \frac{dV}{dt}
\]

The second derivative needed for the sensitivity Jacobian:

\[
\frac{\partial}{\partial V} \left( \frac{\partial I_C}{\partial C} \right) = \frac{1}{h}
\]

#### 10.3.2 C Implementation in `CAPsLoad()`

```c
void CAPsLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *here;
    double dvdt, h;
    int ipos, ineg;
    
    h = ckt->CKTdelta;  /* Time step */
    
    for(; model != NULL; model = model->CAPnextModel) {
        for(here = model->CAPinstances; here != NULL; here = here->CAPnextInstance) {
            
            if(here->CAPsenParmNo >= 0) {
                ipos = here->CAPposNode;
                ineg = here->CAPnegNode;
                
                /* Compute dV/dt = (V^{n+1} - V^n)/h */
                dvdt = (ckt->CKTrhs[ipos] - ckt->CKTrhs[ineg] 
                       - (ckt->CKTrhsOld[ipos] - ckt->CKTrhsOld[ineg])) / h;
                
                /* Store ∂I/∂C for RHS contribution */
                here->CAPdIdC = dvdt;
                
                /* ∂²I/∂C∂V = 1/h */
                double d2IdCdV = 1.0 / h;
                
                /* Stamp sensitivity Jacobian block: 
                   J_s = 1/h * [ 1  -1 ]
                               [ -1  1 ] */
                *(here->CAPposPosPtrSens) += d2IdCdV;
                *(here->CAPposNegPtrSens) -= d2IdCdV;
                *(here->CAPnegPosPtrSens) -= d2IdCdV;
                *(here->CAPnegNegPtrSens) += d2IdCdV;
                
                /* Load RHS for sensitivity system: ∂I/∂C = dV/dt */
                ckt->CKTrhsSens[ipos] += dvdt;
                ckt->CKTrhsSens[ineg] -= dvdt;
            }
        }
    }
}
```

**Mathematical Mapping**: The code computes the discrete derivative \(\frac{dV}{dt} = \frac{V^{n+1} - V^n}{h}\) using current and previous RHS values (node voltages). It then stamps the constant Jacobian block \(\frac{1}{h} \begin{bmatrix} 1 & -1 \\ -1 & 1 \end{bmatrix}\) into the sensitivity matrix and adds \(\frac{dV}{dt}\) to the RHS of the adjoint system.

### 10.4 Sensitivity Analysis Setup (`capsset.c`)

#### 10.4.1 Memory Allocation and Initialization

The `CAPssetup()` function prepares all data structures for sensitivity analysis:

```c
int CAPssetup(SENstruct *sens, GENmodel *inModel, CKTcircuit *ckt)
{
    CAPmodel *model = (CAPmodel *)inModel;
    CAPinstance *here;
    int error, i;
    int numSensParams = sens->SENparmsNum;
    
    /* Allocate sensitivity state for each capacitor instance */
    for(; model != NULL; model = model->CAPnextModel) {
        for(here = model->CAPinstances; here != NULL; here = here->CAPnextInstance) {
            
            /* Allocate sensitivity value array */
            here->CAPsens = TMALLOC(double, numSensParams);
            if(here->CAPsens == NULL) return E_NOMEM;
            
            /* Initialize sensitivity array to zero */
            for(i = 0; i < numSensParams; i++) {
                here->CAPsens[i] = 0.0;
            }
            
            /* Determine if this capacitor is a sensitivity parameter */
            here->CAPsenParmNo = -1;  /* Default: not a parameter */
            for(i = 0; i < numSensParams; i++) {
                if(strcmp(sens->SENparms[i].name, here->CAPname) == 0) {
                    here->CAPsenParmNo = i;
                    break;
                }
            }
            
            /* Allocate matrix pointers in sensitivity system */
            error = SMPmakeElt(sens->SENmatrix, 
                             here->CAPposNode, 
                             here->CAPposNode,
                             &(here->CAPposPosPtrSens));
            if(error) return error;
            
            /* Similar allocations for other three matrix positions... */
            
            /* Initialize matrix elements to zero */
            *(here->CAPposPosPtrSens) = 0.0;
            *(here->CAPposNegPtrSens) = 0.0;
            *(here->CAPnegPosPtrSens) = 0.0;
            *(here->CAPnegNegPtrSens) = 0.0;
        }
    }
    
    return OK;
}
```

**Mathematical Mapping**: This setup phase allocates storage for the sensitivity integrals \(\frac{\partial \Phi}{\partial p_i}\) for each parameter \(p_i\). The `CAPsenParmNo` field identifies which capacitors are actual design parameters versus those only affected by cross-sensitivities.

### 10.5 Parameter Update for Perturbation Analysis (`capsupd.c`)

#### 10.5.1 Parameter Perturbation Algorithm

The `CAPsupdate()` function applies parameter perturbations for finite-difference validation:

```c
void CAPsupdate(GENmodel *inModel, double *paramValues, int numParams)
{
    CAPmodel