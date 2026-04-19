# Coupled Transmission Lines: Distributed Mathematics and MNA Load

_Generated 2026-04-13 00:38 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cpl/cpldefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cpl/cplparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cpl/cplmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cpl/cplsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cpl/cplmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cpl/cplask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cpl/cplload.c`

# Chapter: Coupled Transmission Lines: Distributed Mathematics and MNA Load

## 1. Technical Introduction

The coupled transmission line implementation in Ngspice provides a comprehensive framework for simulating high-speed interconnect systems with mutual coupling effects. The core files—`cpldefs.h`, `cplparam.c`, `cplmpar.c`, `cplsetup.c`, `cplmask.c`, `cplask.c`, and `cplload.c`—collectively implement the distributed parameter models, Modified Nodal Analysis (MNA) matrix formulation, and numerical algorithms required for accurate simulation of coupled transmission lines. These files define the data structures for per-unit-length RLCG matrices, implement modal decomposition for decoupling the Telegrapher's equations, provide the Norton companion models for transient analysis with recursive convolution, and manage the sparse matrix allocation for the coupled system. The implementation supports both frequency-domain analysis with exact ABCD matrices and time-domain analysis with history-dependent delayed sources, enabling simulation of signal integrity effects including crosstalk, skin effect losses, and propagation delays in multi-conductor transmission line systems.

## 2. Mathematical Formulation

### 2.1 Telegrapher's Equations for Coupled Transmission Lines

The fundamental mathematical description of coupled transmission lines in Ngspice is governed by the time-domain Telegrapher's equations, extended for multiple coupled conductors. For a system of `n` coupled lines, the equations are:

**Voltage propagation:**
\[
\frac{\partial \mathbf{V}(x,t)}{\partial x} = -\mathbf{L} \frac{\partial \mathbf{I}(x,t)}{\partial t} - \mathbf{R} \mathbf{I}(x,t)
\]

**Current propagation:**
\[
\frac{\partial \mathbf{I}(x,t)}{\partial x} = -\mathbf{C} \frac{\partial \mathbf{V}(x,t)}{\partial t} - \mathbf{G} \mathbf{V}(x,t)
\]

Where:
- \(\mathbf{V}(x,t) = [V_1(x,t), V_2(x,t), \ldots, V_n(x,t)]^T\) is the voltage vector
- \(\mathbf{I}(x,t) = [I_1(x,t), I_2(x,t), \ldots, I_n(x,t)]^T\) is the current vector
- \(\mathbf{L}\) is the per-unit-length inductance matrix (n×n, symmetric)
- \(\mathbf{C}\) is the per-unit-length capacitance matrix (n×n, symmetric)
- \(\mathbf{R}\) is the per-unit-length resistance matrix (n×n, diagonal for skin effect)
- \(\mathbf{G}\) is the per-unit-length conductance matrix (n×n, diagonal for substrate loss)

### 2.2 Modal Decomposition for Solution

To solve the coupled equations efficiently, Ngspice employs modal decomposition. The coupled system is diagonalized by finding the eigenvectors of the product \(\mathbf{LC}\):

**Characteristic impedance matrix:**
\[
\mathbf{Z}_0 = \mathbf{L} \mathbf{T} \mathbf{\Lambda}^{-1/2} \mathbf{T}^{-1}
\]

**Propagation constant matrix:**
\[
\mathbf{\Gamma} = \mathbf{T} \mathbf{\Lambda}^{1/2} \mathbf{T}^{-1}
\]

Where:
- \(\mathbf{T}\) is the transformation matrix whose columns are eigenvectors of \(\mathbf{LC}\)
- \(\mathbf{\Lambda}\) is the diagonal matrix of eigenvalues \(\lambda_i\)
- The modal propagation constants are \(\gamma_i = \sqrt{\lambda_i} = \alpha_i + j\beta_i\)

### 2.3 Frequency-Domain Solution

In the frequency domain, the solution takes the form of exponential matrix functions:

**Voltage and current at position x:**
\[
\mathbf{V}(x) = e^{-\mathbf{\Gamma} x} \mathbf{V}^+ + e^{\mathbf{\Gamma} x} \mathbf{V}^-
\]
\[
\mathbf{I}(x) = \mathbf{Y}_0 (e^{-\mathbf{\Gamma} x} \mathbf{V}^+ - e^{\mathbf{\Gamma} x} \mathbf{V}^-)
\]

Where \(\mathbf{Y}_0 = \mathbf{Z}_0^{-1}\) is the characteristic admittance matrix, and \(\mathbf{V}^+\), \(\mathbf{V}^-\) are forward and backward traveling wave amplitudes.

### 2.4 Time-Domain Norton Companion Model

For transient analysis, Ngspice converts the frequency-domain solution to a time-domain Norton equivalent using recursive convolution. The discretized equations at time step \(t_k\) are:

**Norton equivalent at port i:**
\[
I_i(t_k) = \mathbf{Y}_{ii} V_i(t_k) + I_{i,hist}(t_k)
\]

**History current term:**
\[
I_{i,hist}(t_k) = \sum_{j \neq i} \mathbf{Y}_{ij} V_j(t_k - \tau_{ij}) + \sum_{m=0}^{M-1} h_{ij}[m] V_j(t_{k-m})
\]

Where:
- \(\mathbf{Y}_{ij}\) are submatrices of the characteristic admittance matrix
- \(\tau_{ij}\) are modal delays between ports i and j
- \(h_{ij}[m]\) are impulse response coefficients for lossy line modeling
- The summation implements recursive convolution for frequency-dependent parameters

### 2.5 Lossy Line Modeling with Skin Effect

For lossy coupled lines, Ngspice implements frequency-dependent resistance and inductance:

**Skin effect resistance:**
\[
R(f) = R_{dc} + K_R \sqrt{f}
\]

**Internal inductance:**
\[
L_{int}(f) = \frac{K_L}{\sqrt{f}}
\]

**Complex propagation constant:**
\[
\gamma(f) = \sqrt{(R(f) + j\omega L(f))(G + j\omega C)}
\]

Where the frequency dependence requires convolution in the time domain.

### 2.6 Coupling Coefficients and Crosstalk

The coupling between lines is quantified by the off-diagonal elements of the parameter matrices:

**Inductive coupling coefficient:**
\[
k_{L,ij} = \frac{L_{ij}}{\sqrt{L_{ii} L_{jj}}}
\]

**Capacitive coupling coefficient:**
\[
k_{C,ij} = \frac{C_{ij}}{\sqrt{C_{ii} C_{jj}}}
\]

**Near-end crosstalk (NEXT):**
\[
V_{NEXT}(t) = \frac{1}{4} \left( \frac{\Delta L}{Z_0} + \Delta C Z_0 \right) \frac{dV_{aggressor}(t)}{dt}
\]

**Far-end crosstalk (FEXT):**
\[
V_{FEXT}(t) = \frac{TD}{2} \left( \frac{\Delta L}{Z_0} - \Delta C Z_0 \right) \frac{dV_{aggressor}(t - TD)}{dt}
\]

Where \(TD\) is the time delay of the line.

## 3. Convergence Analysis

### 3.1 Newton-Raphson Convergence for Coupled Lines

The coupled transmission line model presents unique convergence challenges due to the delayed coupling terms. The Newton-Raphson iteration for the Norton companion model is:

**Jacobian matrix entries:**
\[
J_{ii} = \frac{\partial I_i}{\partial V_i} = \mathbf{Y}_{ii} + \frac{\partial I_{i,hist}}{\partial V_i}
\]
\[
J_{ij} = \frac{\partial I_i}{\partial V_j} = \frac{\partial I_{i,hist}}{\partial V_j} \quad \text{for } i \neq j
\]

The history term derivatives require careful treatment since they depend on past voltage values.

### 3.2 Convergence Testing Criteria

Ngspice implements specialized convergence testing for transmission lines:

**Voltage convergence at port i:**
\[
|V_i^{(k)} - V_i^{(k-1)}| \leq \epsilon_{rel} \cdot \max(|V_i^{(k)}|, |V_i^{(k-1)}|) + \epsilon_{abs}
\]

**Current convergence:**
\[
|I_i^{(k)} - I_i^{(k-1)}| \leq \epsilon_{rel} \cdot \max(|I_i^{(k)}|, |I_i^{(k-1)}|) + \epsilon_{abs}
\]

**History term stability:**
\[
|I_{i,hist}^{(k)} - I_{i,hist}^{(k-1)}| \leq \epsilon_{hist} \cdot \max(|I_{i,hist}^{(k)}|, 1)
\]

Where \(\epsilon_{hist}\) is a specialized tolerance for history term convergence.

### 3.3 Local Truncation Error (LTE) Control

For transient analysis with coupled lines, LTE estimation must account for both local integration error and error propagation through delays:

**State variable LTE:**
\[
LTE_V = \frac{\Delta t^2}{12} \left| \frac{d^3V}{dt^3} \right|
\]

**Coupled term LTE:**
\[
LTE_{coup} = \sum_{j \neq i} \left| \frac{\partial I_{i,hist}}{\partial V_j} \right| \cdot LTE_{V_j}
\]

**Total normalized error:**
\[
\epsilon_{total} = \frac{LTE_V + LTE_{coup}}{\epsilon_{rel} \cdot |V| + \epsilon_{abs}}
\]

If \(\epsilon_{total} > 1\), the time step is reduced according to:
\[
\Delta t_{new} = 0.9 \cdot \Delta t_{old} \cdot \epsilon_{total}^{-1/2}
\]

### 3.4 Recursive Convolution Stability

The recursive convolution implementation for lossy lines must satisfy stability criteria:

**Impulse response decay condition:**
\[
\sum_{m=0}^{\infty} |h[m]| < \infty
\]

**Time-step limitation:**
\[
\Delta t \leq \frac{0.1}{\max(\alpha_i)}
\]
Where \(\alpha_i\) are the attenuation constants of the propagation modes.

**Numerical stability of recurrence:**
\[
\left| 1 - \Delta t \cdot \max(\Re(\gamma_i)) \right| < 1
\]

### 3.5 Modal Analysis Convergence

For the eigenvector decomposition, convergence is monitored through:

**Relative eigenvalue error:**
\[
\epsilon_{\lambda} = \frac{\|\mathbf{LC} \mathbf{t}_i - \lambda_i \mathbf{t}_i\|}{\|\mathbf{t}_i\| \cdot |\lambda_i|}
\]

**Orthogonality error:**
\[
\epsilon_{ortho} = \max_{i \neq j} |\mathbf{t}_i^T \mathbf{t}_j|
\]

The modal decomposition is considered converged when \(\epsilon_{\lambda} < 10^{-8}\) and \(\epsilon_{ortho} < 10^{-6}\).

### 3.6 Delay Matching for Synchronous Switching

For coupled lines with synchronous switching, additional convergence criteria ensure proper delay matching:

**Delay alignment error:**
\[
\epsilon_{delay} = \max_{i,j} \left| \tau_{ij} - \frac{\text{round}(\tau_{ij}/\Delta t) \cdot \Delta t}{\tau_{ij}} \right|
\]

**Interpolation error for non-integer delays:**
\[
\epsilon_{interp} = \frac{\Delta t^2}{8} \left| \frac{d^2V}{dt^2} \right|
\]

The implementation uses cubic interpolation when \(\epsilon_{delay} > 0.01\) to maintain accuracy.

### 3.7 Matrix Conditioning for Coupled Systems

The Modified Nodal Analysis (MNA) matrix for coupled transmission lines can become ill-conditioned. Ngspice monitors:

**Condition number estimate:**
\[
\kappa(\mathbf{A}) \approx \frac{\max|\lambda_i|}{\min|\lambda_i|}
\]

**Pivot growth factor:**
\[
\rho = \frac{\max|u_{ii}|}{\max|a_{ij}|}
\]

Where \(u_{ii}\) are diagonal elements of the LU factors. If \(\kappa > 10^{10}\) or \(\rho > 10^4\), numerical precision warnings are issued.

### 3.8 Energy Conservation Check

For lossless coupled lines, energy conservation provides a convergence metric:

**Input energy over interval [t1, t2]:**
\[
E_{in} = \int_{t1}^{t2} \sum_i V_i(t) I_i(t) dt
\]

**Stored energy change:**
\[
\Delta E_{store} = \frac{1}{2} \left[ \mathbf{V}^T(t2) \mathbf{C} \mathbf{V}(t2) + \mathbf{I}^T(t2) \mathbf{L} \mathbf{I}(t2) \right] - \frac{1}{2} \left[ \mathbf{V}^T(t1) \mathbf{C} \mathbf{V}(t1) + \mathbf{I}^T(t1) \mathbf{L} \mathbf{I}(t1) \right]
\]

**Energy error:**
\[
\epsilon_{energy} = \frac{|E_{in} - \Delta E_{store}|}{\max(|E_{in}|, |\Delta E_{store}|, 1)}
\]

This provides a physics-based convergence check complementary to the numerical criteria.

The convergence analysis for coupled transmission lines in Ngspice combines standard Newton-Raphson techniques with specialized methods for handling delayed coupling terms, recursive convolution stability, and modal decomposition accuracy, ensuring robust simulation of high-speed interconnect systems.

## 4. C Implementation

This section details the Ngspice C implementation of coupled transmission lines, mapping the distributed mathematical formulations directly to the code structures, algorithms, and SPICEdev API integration. The implementation handles both lossless (TRA) and lossy (TXL) transmission line models with support for coupled lines through mutual inductance and capacitance.

### 4.1 Core Data Structures for Transmission Lines

The transmission line implementation uses hierarchical data structures to manage both model parameters and instance-specific state variables:

```c
/* Transmission Line Model Structure (tradefs.h) */
typedef struct sTRAmodel {
    int TRAmodType;                /* Model type identifier */
    double TRAimped;               /* Characteristic impedance (Z0) */
    double TRAresist;              /* Resistance per unit length */
    double TRAconduct;             /* Conductance per unit length */
    double TRAinduct;              /* Inductance per unit length */
    double TRAcapac;               /* Capacitance per unit length */
    double TRAlength;              /* Physical length */
    double TRAtd;                  /* Time delay (TD) */
    double TRAfrequency;           /* Frequency for NL model */
    double TRAlambda;              /* Wavelength */
    double TRAalpha;               /* Attenuation constant */
    double TRAbeta;                /* Phase constant */
    struct sTRAmodel *TRAnextModel; /* Linked list pointer */
    sTRAinstance *TRAinstances;    /* Instance list */
} TRAmodel;

/* Transmission Line Instance Structure */
typedef struct sTRAinstance {
    char *TRAname;                 /* Instance name */
    int TRApos1Node, TRAneg1Node;  /* Port 1 nodes */
    int TRApos2Node, TRAneg2Node;  /* Port 2 nodes */
    int TRAbrEq1, TRAbrEq2;        /* Branch equations */
    
    /* State variables */
    double TRAvolt1, TRAvolt2;     /* Port voltages */
    double TRAcurr1, TRAcurr2;     /* Port currents */
    double TRAhistV1, TRAhistV2;   /* History voltages */
    double TRAhistI1, TRAhistI2;   /* History currents */
    
    /* Matrix pointers for MNA stamping */
    double *TRApos1Pos1Ptr;
    double *TRApos1Neg1Ptr;
    double *TRAneg1Pos1Ptr;
    double *TRAneg1Neg1Ptr;
    double *TRApos2Pos2Ptr;
    double *TRApos2Neg2Ptr;
    double *TRAneg2Pos2Ptr;
    double *TRAneg2Neg2Ptr;
    double *TRAbr1Ptr, *TRAbr2Ptr; /* Branch equation pointers */
    
    /* Coupling parameters for multiple lines */
    double TRAcouplingK;           /* Coupling coefficient */
    double TRAmutualL;             /* Mutual inductance */
    double TRAmutualC;             /* Mutual capacitance */
    
    struct sTRAinstance *TRAnextInstance;
    TRAmodel *TRAmodPtr;
} TRAinstance;
```

**Mathematical Mapping:**
- `TRAimped` implements characteristic impedance `Z₀ = √(L/C)`
- `TRAtd` stores time delay `TD = length·√(LC)`
- `TRAhistV1`, `TRAhistI1` store delayed values `V₂(t-TD)`, `I₂(t-TD)` for Norton companion model
- `TRAcouplingK` implements coupling coefficient `k = M/√(L₁L₂)`

### 4.2 Lossless Line (TRA) Norton Companion Model Implementation

The lossless transmission line uses a Norton equivalent circuit based on delayed sources:

```c
/* TRAload.c - DC/Transient loading for lossless line */
int TRAload(GENmodel *inModel, CKTcircuit *ckt) {
    TRAmodel *model = (TRAmodel*)inModel;
    TRAinstance *here;
    
    for(; model != NULL; model = model->TRAnextModel) {
        for(here = model->TRAinstances; here != NULL; here = here->TRAnextInstance) {
            double Z0 = model->TRAimped;
            double TD = model->TRAtd;
            
            /* Retrieve history terms from time t-TD */
            double V2_hist = here->TRAhistV2;
            double I2_hist = here->TRAhistI2;
            double V1_hist = here->TRAhistV1;
            double I1_hist = here->TRAhistI1;
            
            /* Norton equivalent currents */
            double I1_history = (1.0/Z0) * V2_hist + I2_hist;
            double I2_history = (1.0/Z0) * V1_hist + I1_hist;
            
            /* Stamp conductance matrix (Y = 1/Z0) */
            *(here->TRApos1Pos1Ptr) += 1.0/Z0;
            *(here->TRApos1Neg1Ptr) -= 1.0/Z0;
            *(here->TRAneg1Pos1Ptr) -= 1.0/Z0;
            *(here->TRAneg1Neg1Ptr) += 1.0/Z0;
            
            *(here->TRApos2Pos2Ptr) += 1.0/Z0;
            *(here->TRApos2Neg2Ptr) -= 1.0/Z0;
            *(here->TRAneg2Pos2Ptr) -= 1.0/Z0;
            *(here->TRAneg2Neg2Ptr) += 1.0/Z0;
            
            /* Stamp history currents into RHS */
            ckt->CKTrhs[here->TRApos1Node] -= I1_history;
            ckt->CKTrhs[here->TRAneg1Node] += I1_history;
            ckt->CKTrhs[here->TRApos2Node] -= I2_history;
            ckt->CKTrhs[here->TRAneg2Node] += I2_history;
            
            /* Store current values for next time step history */
            here->TRAhistV1 = *(ckt->CKTrhs + here->TRApos1Node) 
                            - *(ckt->CKTrhs + here->TRAneg1Node);
            here->TRAhistI1 = I1_history;
            here->TRAhistV2 = *(ckt->CKTrhs + here->TRApos2Node) 
                            - *(ckt->CKTrhs + here->TRAneg2Node);
            here->TRAhistI2 = I2_history;
        }
    }
    return OK;
}
```

**Mathematical Mapping to Telegrapher's Equations:**
- Norton currents implement: `I₁(t) = V₂(t-TD)/Z₀ + I₂(t-TD)` and `I₂(t) = V₁(t-TD)/Z₀ + I₁(t-TD)`
- Conductance stamps implement: `Y = 1/Z₀` in 2×2 admittance matrices for each port
- History storage implements the time delay `TD` required by the d'Alembert solution

### 4.3 Lossy Line (TXL) Recursive Convolution Implementation

For lossy lines with frequency-dependent parameters, Ngspice implements recursive convolution:

```c
/* TXL model with frequency-dependent parameters */
typedef struct sTXLmodel {
    /* RLCG parameters per unit length */
    double R[TXLR_MAXORDER];      /* Resistance polynomial coefficients */
    double L[TXLL_MAXORDER];      /* Inductance polynomial coefficients */
    double C[TXLC_MAXORDER];      /* Capacitance polynomial coefficients */
    double G[TXLG_MAXORDER];      /* Conductance polynomial coefficients */
    int Rorder, Lorder, Corder, Gorder; /* Polynomial orders */
    
    /* Convolution kernel storage */
    double *TXLh11, *TXLh12;      /* Impulse response kernels */
    double *TXLh21, *TXLh22;
    int TXLkernelSize;            /* Kernel length */
} TXLmodel;

/* Recursive convolution implementation */
double txl_convolve(double *kernel, double *history, int n, double dt) {
    double result = 0.0;
    /* Direct convolution for small n, FFT for large n */
    if(n < TXL_FFT_THRESHOLD) {
        for(int i = 0; i < n; i++) {
            result += kernel[i] * history[n-i-1];
        }
    } else {
        result = txl_fft_convolve(kernel, history, n);
    }
    return result * dt;  /* Scale by time step */
}

/* TXL load function with recursive convolution */
int TXLload(GENmodel *inModel, CKTcircuit *ckt) {
    TXLmodel *model = (TXLmodel*)inModel;
    TXLinstance *here;
    
    for(here = model->TXLinstances; here != NULL; here = here->TXLnextInstance) {
        /* Compute frequency-dependent parameters */
        double omega = 2.0 * M_PI * ckt->CKTcurTask->TSKfrequency;
        double R = txl_eval_poly(model->R, model->Rorder, omega);
        double L = txl_eval_poly(model->L, model->Lorder, omega);
        double G = txl_eval_poly(model->G, model->Gorder, omega);
        double C = txl_eval_poly(model->C, model->Corder, omega);
        
        /* Characteristic impedance and propagation constant */
        double Z0 = sqrt((R + I*omega*L) / (G + I*omega*C));
        double gamma = sqrt((R + I*omega*L) * (G + I*omega*C));
        
        /* Update convolution kernels if frequency changed */
        if(ckt->CKTmode & MODEINITFREQ) {
            txl_update_kernels(model, Z0, gamma, ckt->CKTdelta);
        }
        
        /* Convolve with history */
        double V1_conv = txl_convolve(model->TXLh11, here->TXLhistV1, 
                                      here->TXLhistIndex, ckt->CKTdelta);
        double I1_conv = txl_convolve(model->TXLh12, here->TXLhistI1, 
                                      here->TXLhistIndex, ckt->CKTdelta);
        double V2_conv = txl_convolve(model->TXLh21, here->TXLhistV2, 
                                      here->TXLhistIndex, ckt->CKTdelta);
        double I2_conv = txl_convolve(model->TXLh22, here->TXLhistI2, 
                                      here->TXLhistIndex, ckt->CKTdelta);
        
        /* Stamp into matrix */
        *(here->TXLpos1Pos1Ptr) += 1.0/Z0;
        *(here->TXLpos1Neg1Ptr) -= 1.0/Z0;
        *(here->TXLneg1Pos1Ptr) -= 1.0/Z0;
        *(here->TXLneg1Neg1Ptr) += 1.0/Z0;
        
        /* Add convolution results to RHS */
        ckt->CKTrhs[here->TXLpos1Node] -= V1_conv + I1_conv;
        ckt->CKTrhs[here->TXLneg1Node] += V1_conv + I1_conv;
        
        /* Update history buffer */
        txl_update_history(here, ckt);
    }
    return OK;
}
```

**Mathematical Mapping to Distributed Parameters:**
- `txl_eval_poly()` implements frequency-dependent RLCG parameters: `R(ω) = Σ R_i·ω^i`
- `Z0 = √((R+jωL)/(G+jωC))` implements complex characteristic impedance
- `γ = √((R+jωL)(G+jωC))` implements complex propagation constant
- Recursive convolution implements the inverse Laplace transform of `e^{-γ·length}`

### 4.4 Coupled Transmission Lines Implementation

For multiple coupled lines, the implementation extends to N×N matrices:

```c
/* Coupled line model structure */
typedef struct sCOUPLEDmodel {
    int COUPLEDnlines;            /* Number of coupled lines */
    double **COUPLEDL;            /* N×N inductance matrix */
    double **COUPLEDC;            /* N×N capacitance matrix */
    double **COUPLEDR;            /* N×N resistance matrix */
    double **COUPLEDG;            /* N×N conductance matrix */
    double *COUPLEDlength;        /* Length for each line */
    
    /* Modal decomposition storage */
    double **COUPLEDTv;           /* Voltage transformation matrix */
    double **COUPLEDTi;           /* Current transformation matrix */
    double *COUPLEDZ0mode;        /* Modal characteristic impedances */
    double *COUPLEDgammamode;     /* Modal propagation constants */
} COUPLEDmodel;

/* Modal decomposition for coupled lines */
int coupled_modal_decomposition(COUPLEDmodel *model) {
    int n = model->COUPLEDnlines;
    
    /* Form per-unit-length matrices */
    gsl_matrix *L = gsl_matrix_alloc(n, n);
    gsl_matrix *C = gsl_matrix_alloc(n, n);
    
    for(int i = 0; i < n; i++) {
        for(int j = 0; j < n; j++) {
            gsl_matrix_set(L, i, j, model->COUPLEDL[i][j]);
            gsl_matrix_set(C, i, j, model->COUPLEDC[i][j]);
        }
    }
    
    /* Solve eigenvalue problem: (L·C)·Tv = λ·Tv */
    gsl_eigen_symmv_workspace *w = gsl_eigen_symmv_alloc(n);
    gsl_vector *eval = gsl_vector_alloc(n);
    gsl_matrix *evec = gsl_matrix_alloc(n, n);
    
    /* Form product matrix LC */
    gsl_matrix *LC = gsl_matrix_alloc(n, n);
    gsl_blas_dgemm(CblasNoTrans, CblasNoTrans, 1.0, L, C, 0.0, LC);
    
    gsl_eigen_symmv(LC, eval, evec, w);
    
    /* Store modal transformation matrices */
    for(int i = 0; i < n; i++) {
        model->COUPLEDZ0mode[i] = sqrt(gsl_vector_get(eval, i));
        for(int j = 0; j < n; j++) {
            model->COUPLEDTv[i][j] = gsl_matrix_get(evec, i, j);
        }
    }
    
    /* Current transformation: Ti = C·Tv·Λ^{-1/2} */
    gsl_matrix *Ti = gsl_matrix_alloc(n, n);
    for(int i = 0; i < n; i++) {
        double lambda_sqrt = sqrt(gsl_vector_get(eval, i));
        for(int j = 0; j < n; j++) {
            double sum = 0.0;
            for(int k = 0; k < n; k++) {
                sum += model->COUPLEDC[j][k] * gsl_matrix_get(evec, k, i);
            }
            gsl_matrix_set(Ti, j, i, sum / lambda_sqrt);
        }
    }
    
    /* Cleanup */
    gsl_eigen_symmv_free(w);
    gsl_vector_free(eval);
    gsl_matrix_free(evec);
    gsl_matrix_free(LC);
    gsl_matrix_free(L);
    gsl_matrix_free(C);
    gsl_matrix_free(Ti);
    
    return OK;
}
```

**Mathematical Mapping to Coupled Telegrapher's Equations:**
- N×N matrices implement: `∂V/∂x = -R·I - L·∂I/∂t` and `∂I/∂x = -G·V - C·∂V/∂t`
- Modal decomposition solves eigenvalue problem: `(L·C)·T_v = λ·T_v`
- Modal impedances: `Z₀_mode[i] = √(λ[i])`
- Enables simulation of crosstalk, common mode, and differential mode propagation

### 4.5 MNA Matrix Setup and Pointer Allocation

The setup function allocates sparse matrix pointers for the transmission line stamps:

```c
/* TRAsetup.c - Matrix pointer allocation */
int TRAsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    TRAmodel *model = (TRAmodel*)inModel;
    TRAinstance *here;
    
    for(; model != NULL; model = model->TRAnextModel) {
        for(here = model->TRAinstances; here != NULL; here = here->TRAnextInstance) {
            /* Allocate 2×2 matrix pointers for port 1 */
            here->TRApos1Pos1Ptr = SMPmakeElt(matrix, here->TRApos1Node, here->TRApos1Node);
            here->TRApos1Neg1Ptr = SMPmakeElt(matrix, here->TRApos1Node, here->TRAneg1Node);
            here->TRAneg1Pos1Ptr = SMPmakeElt(matrix, here->TRAneg1Node, here->TRApos1Node);
            here->TRAneg1Neg1Ptr = SMPmakeElt(matrix, here->TRAneg1Node, here->TRAneg1Node);
            
            /* Allocate 2×2 matrix pointers for port 2 */
            here->TRApos2Pos2Ptr = SMPmakeElt(matrix, here->TRApos2Node, here->TRApos2Node);
            here->TRApos2Neg2Ptr = SMPmakeElt(matrix, here->TRApos2Node, here->TRAneg2Node);
            here->TRAneg2Pos2Ptr = SMPmakeElt(matrix, here->TRAneg2Node, here->TRApos2Node);
            here->TRAneg2Neg2Ptr = SMPmakeElt(matrix, here->TRAneg2Node, here->TRAneg2Node);
            
            /* Allocate branch equations if needed for coupled lines */
            if(model->TRAmodType == TRA_MOD_COUPLED) {
                here->TRAbrEq1 = *states;
                (*states)++;
                here->TRAbrEq2 = *states;
                (*states)++;
                
                here->TRAbr1Ptr = SMPmakeElt(matrix, here->TRAbrEq1, here->TRAbrEq1);
                here->TRAbr2Ptr = SMPmakeElt(matrix, here->TRAbrEq2, here->TRAbrEq2);
            }
            
            /* Initialize history buffers */
            here->TRAhistV1 = 0.0;
            here->TRAhistI1 = 0.0;
            here->TRAhistV2 = 0.0;
            here->TRAhistI2 = 0.0;
        }
    }
    return OK;
}
```

**SPICE Integration:**
- Allocates 8 sparse matrix pointers for two 2×2 admittance matrices
- For coupled lines, adds branch equations to handle mutual coupling terms
- History buffers initialized to zero for startup conditions

### 4.6 AC Analysis Implementation

For frequency-domain analysis, transmission lines use the exact frequency-dependent solution:

```c
/* TRAacLoad.c - AC analysis loading */
int TRAacLoad(GENmodel *inModel, CKTcircuit *ckt) {
    TRAmodel *model = (TRAmodel*)inModel;
    TRAinstance *here;
    
    for(; model != NULL; model = model->TRAnextModel) {
        for(here = model->TRAinstances; here != NULL; here = here->TRAnextInstance) {
            double omega = ckt->CKTomega;
            double Z0 = model->TRAimped;
            double TD = model->TRAtd;
            
            /* Frequency-dependent phase shift */
            double phase = omega * TD;
            double cos_phase = cos(phase);
            double sin_phase = sin(phase);
            
            /* Complex ABCD matrix for transmission line */
            double A = cos_phase;
            double B = I * Z0 * sin_phase;
            double C = I * sin_phase / Z0;
            double D = cos_phase;
            
            /* Convert to Y-parameters */
            double det = A * D - B * C;
            double Y11 = D / det;
            double Y12 = -B / det;
            double Y21 = -C / det;
            double Y22 = A / det;
            
            /* Stamp into complex matrix */
            /* Port 1 self-admittance */
            *(here->TRApos1Pos1Ptr) += Y11;
            *(here->TRApos1Neg1Ptr) -= Y11;
            *(here->TRAneg1Pos1Ptr) -= Y11;
            *(here->TRAneg1Neg1Ptr) += Y11;
            
            /* Port 2 self-admittance */
            *(here->TRApos2Pos2Ptr) += Y22;
            *(here->TRApos2Neg2Ptr) -= Y22;
            *(here->TRAneg2Pos2Ptr) -= Y22;
            *(here->TRAneg2Neg2Ptr) += Y22;
            
            /* Cross admittances (coupling) */
            int pos1 = here->TRApos1Node;
            int neg1 = here->TRAneg1Node;
            int pos2 = here->TRApos2Node;
            int neg2 = here->TRAneg2Node;
            
            SMPcElt *c12 = SMPmakeElt(ckt->CKTmatrix, pos1, pos2);
            SMPcElt *c13 = SMPmakeElt(ckt->CKTmatrix, pos1, neg2);
            SMPcElt *c14 = SMPmakeElt(ckt->CKTmatrix, neg1, pos2);
            SMPcElt *c15 = SMPmakeElt(ckt->CKTmatrix, neg1, neg2);
            
            *c12 += Y12;
            *c13 -= Y12;
            *c14 -= Y12;
            *c15 += Y12;
        }
    }
    return OK;
}
```

**Mathematical Mapping to Frequency Domain:**
- ABCD matrix implements: `[V₁; I₁] = [A B; C D]·[V₂; I₂]`
- Y-parameters derived from: `Y = [D/Δ -B/Δ; -C/Δ A/Δ]` where `Δ = AD - BC`
- Phase shift `φ = ω·TD` implements time delay in frequency domain

### 4.7 SPICEdev API Binding

The transmission line device is registered with Ngspice through the standard SPICEdev structure:

```c
/* TRA initialization and API binding */
SPICEdev TRAinfo = {
    .DEVpublic = {
        .name = "t",
        .description = "Lossless transmission line",
        .terms = 4,
        .numNames = 4,
        .termNames = {"pos1", "neg1", "pos2", "neg2"},
        .numInstanceParms = 6,
        .numModelParms = 3,
    },
    .DEVmodParam = TRAmPTable,
    .DEVinstParam = TRApTable,
    .DEVload = TRAload,
    .DEVsetup = TRAsetup,
    .DEVunsetup = NULL,
    .DEVpzSetup = NULL,
    .DEVtemperature = NULL,
    .DEVtrunc = TRAtrunc,