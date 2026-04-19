# Dependent Sources: Setup, Pole-Zero, and Sensitivity Analysis

_Generated 2026-04-12 23:51 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccsset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvsset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccsset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvsset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccspzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvspzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccspzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvspzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccssacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccssld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccssset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccssprt.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvssacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvssld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvssset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvssprt.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccssacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccssld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccssset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccssprt.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvssacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvssld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvssset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvssprt.c`

# **Chapter: Dependent Sources: Setup, Pole-Zero, and Sensitivity Analysis**

## **Technical Introduction**

This chapter details the Ngspice implementation of dependent source devices—specifically Voltage-Controlled Current Sources (VCCS/G-device) and Voltage-Controlled Voltage Sources (VCVS/E-device)—focusing on their matrix setup, pole-zero analysis, and sensitivity analysis subsystems. The referenced C files (`vccsset.c`, `vcvsset.c`, `vccspzld.c`, `vcvsset.c`, `vccssacl.c`, `vccssld.c`, etc.) collectively implement the complete SPICE simulation pipeline for these devices:

1.  **Setup Files (`*set.c`)**: Allocate sparse matrix pointers within Ngspice's Modified Nodal Analysis (MNA) system, validate device parameters, and initialize internal state vectors. They map the mathematical Jacobian structure to efficient, O(1)-access C pointers.

2.  **Pole-Zero Files (`*pzld.c`)**: Construct the complex-valued matrix system `(G + sC)X(s) = B` required for frequency-domain transfer function and stability analysis. These routines stamp the linearized device conductances and capacitances at the operating point into a separate complex matrix.

3.  **Sensitivity Analysis Files (`*sacl.c`, `*ssld.c`, `*sset.c`, `*sprt.c`)**: Implement the adjoint method for efficient computation of circuit response derivatives with respect to model parameters (e.g., transconductance `gm`, voltage gain `Av`). This involves setting up and solving an auxiliary linear system alongside the primary circuit equations.

The implementation follows Ngspice's canonical architecture: a `SPICEdev` API structure (`VCCSinfo`, `VCVSinfo`) binds device-specific functions for load, setup, and analysis to the simulation kernel. Core data structures (`VCCSmodel`, `VCCSinstance`) separate physical model parameters from instance-specific electrical state, enabling efficient linked-list traversal during matrix assembly. The following sections present the complete mathematical formulation governing these devices in SPICE and the corresponding C implementation that realizes these equations with numerical robustness.

---

## **Mathematical Formulation**

### 1. Modified Nodal Analysis (MNA) Framework for Dependent Sources

The core SPICE simulation engine solves circuit equations using Modified Nodal Analysis (MNA), which extends nodal analysis to include branch currents for voltage sources and dependent sources. For dependent sources, the MNA system takes the form:

\[
\begin{bmatrix}
\mathbf{G} & \mathbf{B} \\
\mathbf{C} & \mathbf{D}
\end{bmatrix}
\begin{bmatrix}
\mathbf{V} \\
\mathbf{I}
\end{bmatrix}
=
\begin{bmatrix}
\mathbf{J} \\
\mathbf{E}
\end{bmatrix}
\]

Where:
- \(\mathbf{G}\) is the conductance matrix (n × n for n nodes)
- \(\mathbf{B}\) and \(\mathbf{C}\) are incidence matrices for branch equations
- \(\mathbf{D}\) contains coefficients for dependent source relationships
- \(\mathbf{V}\) is the node voltage vector
- \(\mathbf{I}\) is the branch current vector
- \(\mathbf{J}\) is the independent current source vector
- \(\mathbf{E}\) is the independent voltage source vector

### 2. Voltage-Controlled Current Source (VCCS) Formulation

For a linear VCCS with controlling nodes \(c+\) and \(c-\), and output nodes \(o+\) and \(o-\):

\[
I_{out} = g_m \cdot (V_{c+} - V_{c-})
\]

The MNA stamp for a VCCS contributes to the conductance matrix as:

\[
\begin{bmatrix}
\vdots \\
G_{o+,c+} & += & g_m \\
G_{o+,c-} & -= & g_m \\
G_{o-,c+} & -= & g_m \\
G_{o-,c-} & += & g_m \\
\vdots
\end{bmatrix}
\]

For polynomial VCCS with coefficients \(g_0, g_1, \ldots, g_n\):

\[
I_{out} = \sum_{k=0}^{n} g_k \cdot (V_c)^k
\]

Where \(V_c = V_{c+} - V_{c-}\). The derivative for Newton-Raphson iteration is:

\[
\frac{\partial I_{out}}{\partial V_c} = \sum_{k=1}^{n} k \cdot g_k \cdot (V_c)^{k-1}
\]

### 3. Voltage-Controlled Voltage Source (VCVS) Formulation

For a linear VCVS with gain \(A_v\):

\[
V_{o+} - V_{o-} = A_v \cdot (V_{c+} - V_{c-})
\]

This requires introducing a branch current \(I_x\) for the output port, leading to the augmented system:

\[
\begin{bmatrix}
\vdots & \vdots & \vdots & \vdots \\
\cdots & 0 & \cdots & 1 \\
\cdots & 0 & \cdots & -1 \\
\cdots & 1 & \cdots & 0 \\
\cdots & -1 & \cdots & 0 \\
\vdots & \vdots & \vdots & \vdots
\end{bmatrix}
\begin{bmatrix}
\vdots \\
V_{o+} \\
V_{o-} \\
I_x \\
\vdots
\end{bmatrix}
=
\begin{bmatrix}
\vdots \\
0 \\
0 \\
A_v \cdot V_c \\
\vdots
\end{bmatrix}
\]

For polynomial VCVS:

\[
V_{out} = \sum_{k=0}^{n} a_k \cdot (V_c)^k
\]

### 4. Pole-Zero Analysis Formulation

Pole-zero analysis solves the generalized eigenvalue problem:

\[
(\mathbf{G} + s\mathbf{C})\mathbf{X}(s) = \mathbf{B}\mathbf{U}(s)
\]

For dependent sources in pole-zero analysis:
1. **VCCS**: Contributes to \(\mathbf{G}\) matrix as \(g_m\) terms
2. **VCVS**: Requires additional rows/columns in the augmented system

The transfer function \(H(s) = \frac{\mathbf{X}(s)}{\mathbf{U}(s)}\) has poles where \(\det(\mathbf{G} + s\mathbf{C}) = 0\) and zeros where the numerator polynomial vanishes.

For a VCCS with controlling impedance \(Z_c(s)\):

\[
H(s) = \frac{g_m \cdot Z_c(s)}{1 + g_m \cdot Z_c(s) \cdot Z_L(s)}
\]

### 5. Sensitivity Analysis Mathematics

Sensitivity analysis computes derivatives of circuit responses with respect to parameters. For dependent source parameter \(p\) (e.g., \(g_m\) or \(A_v\)):

#### 5.1 Direct Method
\[
\frac{\partial \mathbf{X}}{\partial p} = -(\mathbf{G} + s\mathbf{C})^{-1} \frac{\partial (\mathbf{G} + s\mathbf{C})}{\partial p} \mathbf{X}
\]

For VCCS sensitivity to \(g_m\):
\[
\frac{\partial \mathbf{G}}{\partial g_m} = 
\begin{bmatrix}
0 & \cdots & 1 & -1 & \cdots \\
\vdots & \ddots & \vdots & \vdots & \ddots \\
-1 & \cdots & 0 & 0 & \cdots \\
1 & \cdots & 0 & 0 & \cdots
\end{bmatrix}
\]

#### 5.2 Adjoint Method (Efficient for Many Outputs)
Given objective function \(F(\mathbf{X}, p)\):
1. Solve original system: \((\mathbf{G} + s\mathbf{C})\mathbf{X} = \mathbf{B}\mathbf{U}\)
2. Solve adjoint system: \((\mathbf{G} + s\mathbf{C})^T \mathbf{\Lambda} = \frac{\partial F}{\partial \mathbf{X}}^T\)
3. Compute sensitivity: \(\frac{dF}{dp} = \frac{\partial F}{\partial p} - \mathbf{\Lambda}^T \frac{\partial (\mathbf{G} + s\mathbf{C})}{\partial p} \mathbf{X}\)

### 6. Noise Analysis for Dependent Sources

Dependent sources contribute noise based on their controlling and output relationships:

#### 6.1 VCCS Noise
Output noise current PSD:
\[
S_{I_{out}}(f) = |g_m|^2 \cdot S_{V_c}(f) + S_{I_{int}}(f)
\]
Where \(S_{V_c}(f)\) is the PSD of controlling voltage noise and \(S_{I_{int}}(f)\) is intrinsic noise.

#### 6.2 VCVS Noise
Output noise voltage PSD:
\[
S_{V_{out}}(f) = |A_v|^2 \cdot S_{V_c}(f) + S_{V_{int}}(f)
\]

### 7. Temperature Dependence

Dependent source parameters scale with temperature \(T\):
\[
g_m(T) = g_m(T_{nom}) \cdot \left(\frac{T}{T_{nom}}\right)^{TCE}
\]
\[
A_v(T) = A_v(T_{nom}) \cdot \left[1 + TC1 \cdot (T - T_{nom}) + TC2 \cdot (T - T_{nom})^2\right]
\]

Where TCE is the temperature coefficient of expansion, and TC1, TC2 are first and second-order temperature coefficients.

### 8. Polynomial Evaluation using Horner's Method

For efficient evaluation of polynomial dependent sources:
\[
P(x) = a_0 + x(a_1 + x(a_2 + \cdots + x(a_{n-1} + x \cdot a_n)\cdots))
\]

This minimizes computational operations from \(O(n^2)\) to \(O(n)\).

## Convergence Analysis

### 1. Newton-Raphson Convergence for Nonlinear Dependent Sources

For polynomial dependent sources, the Newton-Raphson iteration solves:
\[
\mathbf{F}(\mathbf{x}^{(k)}) + \mathbf{J}(\mathbf{x}^{(k)}) \cdot \Delta\mathbf{x}^{(k)} = 0
\]

Where \(\mathbf{J}\) is the Jacobian containing derivatives of dependent source equations.

#### 1.1 Convergence Criteria
The iteration converges when:
\[
\|\Delta\mathbf{x}^{(k)}\| < \epsilon_{abs} + \epsilon_{rel} \cdot \|\mathbf{x}^{(k)}\|
\]
With SPICE defaults:
- \(\epsilon_{abs} = 10^{-12}\) (ABSTOL)
- \(\epsilon_{rel} = 10^{-3}\) (RELTOL)
- \(\epsilon_{volt} = 10^{-6}\) (VNTOL)

#### 1.2 Jacobian Conditioning for VCVS
VCVS introduces structural zeros in the Jacobian:
\[
\mathbf{J} = \begin{bmatrix}
\mathbf{G} & \mathbf{A} \\
\mathbf{A}^T & \mathbf{0}
\end{bmatrix}
\]

This indefinite matrix requires careful pivoting in LU decomposition to maintain numerical stability.

### 2. Local Truncation Error (LTE) Control

For time-domain analysis, LTE bounds the error per step:

#### 2.1 VCCS LTE
\[
\epsilon_{LTE}^{VCCS} = \frac{h^2}{12} \left|\frac{d^2 I_{out}}{dt^2}\right|
\]
Where \(h\) is the time step and:
\[
\frac{d^2 I_{out}}{dt^2} = g_m \cdot \frac{d^2 V_c}{dt^2} + \frac{\partial g_m}{\partial V_c} \cdot \left(\frac{dV_c}{dt}\right)^2
\]

#### 2.2 VCVS LTE
\[
\epsilon_{LTE}^{VCVS} = \frac{h^2}{12} \left|\frac{d^2 V_{out}}{dt^2}\right|
\]

The time step is adjusted to maintain \(\epsilon_{LTE} < \text{TRTOL} \cdot \max(|V_{out}|, |I_{out}|) + \text{CHGTOL}\).

### 3. Pole-Zero Analysis Convergence

#### 3.1 QZ Algorithm for Generalized Eigenvalue Problem
The pole-zero analysis solves \((\mathbf{G} + s\mathbf{C})\mathbf{x} = 0\) using the QZ algorithm:
1. Transform to Hessenberg-triangular form
2. Apply QZ iterations until convergence
3. Extract eigenvalues \(s_i = -\lambda_i\)

Convergence criterion:
\[
\frac{|s^{(k+1)} - s^{(k)}|}{|s^{(k)}|} < \epsilon_{pz}
\]
Typically \(\epsilon_{pz} = 10^{-10}\).

#### 3.2 Pole-Zero Pairing
For dependent sources with feedback, pole-zero pairs must satisfy:
\[
\sum \text{poles} - \sum \text{zeros} = \text{number of reactive elements} - \text{number of VCVS}
\]

### 4. Sensitivity Analysis Convergence

#### 4.1 Adjoint Method Accuracy
The adjoint method computes sensitivities with error:
\[
\epsilon_{sens} = O(\|\mathbf{G}^{-1}\| \cdot \kappa(\mathbf{G}) \cdot \epsilon_{machine})
\]
Where \(\kappa(\mathbf{G})\) is the condition number of the conductance matrix.

#### 4.2 Regularization for Ill-Conditioned Systems
When \(\kappa(\mathbf{G}) > 10^8\), Tikhonov regularization is applied:
\[
(\mathbf{G}^T\mathbf{G} + \alpha\mathbf{I})\frac{\partial \mathbf{X}}{\partial p} = -\mathbf{G}^T\frac{\partial \mathbf{G}}{\partial p}\mathbf{X}
\]
With \(\alpha = 10^{-6} \cdot \|\mathbf{G}\|_F^2\).

### 5. Numerical Stability Considerations

#### 5.1 Matrix Stamping Stability
Dependent source stamps must maintain diagonal dominance:
\[
|G_{ii}| \geq \sum_{j \neq i} |G_{ij}| + |B_{ij}|
\]

For VCVS, the augmented system requires 2×2 pivot blocks during LU decomposition.

#### 5.2 Polynomial Evaluation Stability
Horner's method minimizes error propagation:
\[
\text{Error} \leq \gamma_n \sum_{k=0}^n |a_k| |x|^k
\]
Where \(\gamma_n = \frac{n\epsilon_{machine}}{1 - n\epsilon_{machine}}\) and \(\epsilon_{machine} \approx 2.2\times10^{-16}\).

### 6. Convergence Acceleration Techniques

#### 6.1 Damped Newton-Raphson
For difficult convergence:
\[
\mathbf{x}^{(k+1)} = \mathbf{x}^{(k)} + \lambda \Delta\mathbf{x}^{(k)}
\]
With \(\lambda \in (0,1]\) chosen to minimize \(\|\mathbf{F}(\mathbf{x}^{(k+1)})\|\).

#### 6.2 Continuation Methods
For strongly nonlinear dependent sources:
1. Solve for parameter \(p = 0\) (linear case)
2. Gradually increase \(p\) to 1 using previous solution as initial guess
3. Use predictor-corrector steps

### 7. Validation Metrics

#### 7.1 DC Operating Point Validation
- Current conservation: \(\sum I_{node} < 10^{-12}\text{A}\)
- Voltage consistency: \(|V_{calculated} - V_{expected}| < 10^{-9}\text{V}\)
- Power balance: \(\sum P_{sources} - \sum P_{dissipated} < 10^{-15}\text{W}\)

#### 7.2 AC Response Validation
- Reciprocity check: \(H_{ij}(f) = H_{ji}(f)\) within \(10^{-6}\)
- Causality validation via Kramers-Kronig relations
- Passivity: \(\Re\{Z(j\omega)\} \geq 0\) for all \(\omega\)

#### 7.3 Transient Response Validation
- Energy conservation: \(\int_0^T (P_{in} - P_{out})dt < 10^{-12}\text{J}\)
- Charge conservation: \(\Delta Q_{total} < 10^{-14}\text{C}\)
- Time-reversal symmetry error \(< 10^{-6}\)

### 8. Performance Optimization

#### 8.1 Sparse Matrix Optimization
Dependent source stamps create sparse patterns:
- VCCS: 4 non-zeros per device
- VCVS: 6 non-zeros per device (with branch current)

Compressed Sparse Row (CSR) format with:
- Fill-in reduction using AMD ordering
- Block elimination for VCVS branch equations

#### 8.2 Cache-Aware Polynomial Evaluation
Polynomial coefficients stored in contiguous memory:
- L1 cache: Frequently used low-order coefficients
- Prefetching for high-order terms

This mathematical formulation and convergence analysis provides the foundation for robust implementation of dependent sources in Ngspice, ensuring numerical stability, accuracy, and efficient computation across all analysis modes.

---

## **C Implementation: Dependent Sources - Setup, Pole-Zero, and Sensitivity Analysis**

### **1. Core Data Structures and SPICEdev API Binding**

#### **Device Structure Architecture**
The MOS1 device implementation in Ngspice follows a hierarchical structure with separate model and instance definitions in `mos1defs.h`:

```c
/* Model structure containing physical parameters */
typedef struct sMOS1model {
    int MOS1type;                    /* N_MOS=1, P_MOS=-1 */
    double MOS1vt0;                  /* VTO: Threshold voltage */
    double MOS1kp;                   /* KP: Transconductance */
    double MOS1gamma;                /* GAMMA: Body effect */
    double MOS1phi;                  /* PHI: Surface potential */
    double MOS1lambda;               /* LAMBDA: Channel-length modulation */
    /* ... 25 total model parameters */
    struct sMOS1model *MOS1nextModel;  /* Linked list pointer */
    sMOS1instance *MOS1instances;      /* Instance chain */
} MOS1model;

/* Instance structure containing electrical state */
typedef struct sMOS1instance {
    char *MOS1name;                  /* Instance identifier */
    int MOS1dNode, MOS1gNode, MOS1sNode, MOS1bNode; /* MNA indices */
    double MOS1l, MOS1w;             /* Geometric parameters */
    double MOS1effL, MOS1effW;       /* Effective dimensions */
    double MOS1beta;                 /* β = (W_eff/L_eff)·KP */
    double MOS1vgs, MOS1vds, MOS1vbs; /* Terminal voltages */
    double MOS1cdrain;               /* Drain current */
    double MOS1gm, MOS1gds, MOS1gmb; /* Small-signal parameters */
    /* 16 matrix pointers for 4×4 Jacobian */
    double *MOS1drainDrainPtr;       /* ∂Id/∂Vd */
    double *MOS1drainGatePtr;        /* ∂Id/∂Vg */
    /* ... all 16 partial derivatives */
    int MOS1qgs, MOS1qgd, MOS1qgb;   /* Charge state indices */
    struct sMOS1instance *MOS1nextInstance;
    MOS1model *MOS1modPtr;
} MOS1instance;
```

**Mathematical Mapping**: The `MOS1instance` structure directly implements the state variables from the MOS1 equations: terminal voltages (`MOS1vgs`, `MOS1vds`, `MOS1vbs`), drain current (`MOS1cdrain`), and small-signal parameters (`MOS1gm`, `MOS1gds`, `MOS1gmb`) that correspond to the partial derivatives in the Jacobian matrix.

#### **SPICEdev API Registration**
The device binds to Ngspice's simulation core through the `SPICEdev` structure in `mos1init.c`:

```c
SPICEdev MOS1info = {
    .DEVpublic = {
        .name = "mos1",
        .description = "Level 1 MOS FET",
        .terms = 4,
        .numNames = 2,
        .termNames = {"d", "g", "s", "b"},
        .numInstanceParms = 13,
        .numModelParms = 25,
        .flags = DEV_DEFAULT,
    },
    
    .DEVmodParam = MOS1mPTable,
    .DEVinstParam = MOS1pTable,
    .DEVload = MOS1load,          /* DC/transient load */
    .DEVsetup = MOS1setup,        /* Matrix allocation */
    .DEVpzSetup = MOS1pzSetup,    /* Pole-zero setup */
    .DEVtemperature = MOS1temp,   /* Temperature scaling */
    .DEVtrunc = MOS1trunc,        /* LTE calculation */
    .DEVacLoad = MOS1acLoad,      /* AC analysis */
    .DEVdestroy = MOS1destroy,    /* Memory cleanup */
    .DEVpzLoad = MOS1pzLoad,      /* Pole-zero load */
    .DEVconvTest = MOS1convTest,  /* Convergence test */
    .DEVdisto = MOS1disto,        /* Distortion analysis */
    .DEVnoise = MOS1noise,        /* Noise analysis */
    .DEVinstSize = sizeof(sMOS1instance),
    .DEVmodSize = sizeof(sMOS1model),
};
```

**Mathematical Significance**: Each function pointer maps to a specific mathematical operation in SPICE simulation:
- `MOS1load`: Implements the nonlinear device equations and stamps the Jacobian
- `MOS1acLoad`: Adds frequency-dependent capacitive terms
- `MOS1pzLoad`: Constructs the complex matrix for pole-zero analysis
- `MOS1convTest`: Implements the convergence criteria for Newton-Raphson

### **2. Matrix Setup and Sparse Allocation**

#### **Sparse Matrix Pointer Allocation (`mos1set.c`)**
The setup function allocates all 16 matrix pointers for the 4-terminal device:

```c
int MOS1setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    
    for(; model; model = model->MOS1nextModel) {
        /* Default model parameters */
        if(!model->MOS1vt0Given) model->MOS1vt0 = 0.0;
        if(!model->MOS1kpGiven) model->MOS1kp = 2.0e-5;
        /* ... parameter validation */
        
        for(inst = model->MOS1instances; inst; inst = inst->MOS1nextInstance) {
            /* Calculate effective dimensions */
            inst->MOS1effL = inst->MOS1l - 2.0 * model->MOS1ld;
            inst->MOS1effW = inst->MOS1w - 2.0 * model->MOS1wd;
            if(inst->MOS1effL <= 0.0) inst->MOS1effL = 1e-12;
            if(inst->MOS1effW <= 0.0) inst->MOS1effW = 1e-12;
            
            /* Calculate β parameter: β = (W_eff/L_eff)·KP */
            inst->MOS1beta = (inst->MOS1effW / inst->MOS1effL) * model->MOS1kp;
            
            /* Allocate 16 SMP pointers for 4×4 Jacobian */
            inst->MOS1drainDrainPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1dNode);
            inst->MOS1drainGatePtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1gNode);
            inst->MOS1drainSourcePtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1sNode);
            inst->MOS1drainBulkPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1bNode);
            /* ... allocate all 16 pointers */
            
            /* Allocate state vector entries for charges */
            inst->MOS1qgs = *states; (*states)++;
            inst->MOS1qgd = *states; (*states)++;
            inst->MOS1qgb = *states; (*states)++;
            inst->MOS1qbd = *states; (*states)++;
            inst->MOS1qbs = *states; (*states)++;
            
            /* Initialize charge states */
            *(ckt->CKTrhsOld + inst->MOS1qgs) = 0.0;
            /* ... initialize all charges */
        }
    }
    return OK;
}
```

**Mathematical Mapping**: The 16 matrix pointers correspond to the 4×4 Jacobian matrix for the MOS1 device:
```
J = [ ∂Id/∂Vd  ∂Id/∂Vg  ∂Id/∂Vs  ∂Id/∂Vb
      ∂Ig/∂Vd  ∂Ig/∂Vg  ∂Ig/∂Vs  ∂Ig/∂Vb
      ∂Is/∂Vd  ∂Is/∂Vg  ∂Is/∂Vs  ∂Is/∂Vb
      ∂Ib/∂Vd  ∂Ib/∂Vg  ∂Ib/∂Vs  ∂Ib/∂Vb ]
```
Each `SMPmakeElt` call creates a sparse matrix entry at the intersection of the row and column node indices.

### **3. Pole-Zero Analysis Implementation**

#### **Pole-Zero Setup (`MOS1pzSetup`)**
The pole-zero setup prepares the device for complex frequency analysis by allocating additional matrix pointers for the complex system:

```c
int MOS1pzSetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    /* Similar to MOS1setup but for complex matrices */
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    
    for(; model; model = model->MOS1nextModel) {
        for(inst = model->MOS1instances; inst; inst = inst->MOS1nextInstance) {
            /* Allocate complex matrix pointers */
            inst->MOS1drainDrainPtrPZ = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1dNode);
            /* ... allocate all 16 pointers for complex system */
            
            /* Store operating point for linearization */
            inst->MOS1vgs0 = ckt->CKTrhs[inst->MOS1gNode] - ckt->CKTrhs[inst->MOS1sNode];
            inst->MOS1vds0 = ckt->CKTrhs[inst->MOS1dNode] - ckt->CKTrhs[inst->MOS1sNode];
            inst->MOS1vbs0 = ckt->CKTrhs[inst->MOS1bNode] - ckt->CKTrhs[inst->MOS1sNode];
            
            /* Linearize at operating point */
            MOS1linearize(inst, model, ckt);
        }
    }
    return OK;
}
```

#### **Pole-Zero Load (`MOS1pzLoad`)**
Implements the complex matrix stamp for the system `(G + sC)X(s) = B`:

```c
int MOS1pzLoad(MOS1instance *inst, CKTcircuit *ckt, SPcomplex *s) {
    double omega = s->real;  /* Frequency component */
    
    /* Stamp conductance matrix (real part) */
    *(inst->MOS1drainDrainPtrPZ) += inst->MOS1gds;
    *(inst->MOS1drainSourcePtrPZ) -= inst->MOS1gds + inst->MOS1gm + inst->MOS1gmb;
    *(inst->MOS1drainGatePtrPZ) += inst->MOS1gm;
    *(inst->MOS1drainBulkPtrPZ) += inst->MOS1gmb;
    /* ... stamp all 16 real conductances */
    
    /* Stamp capacitive matrix (imaginary part) */
    double Cgs = inst->MOS1cgs;
    double Cgd = inst->MOS1cgd;
    double Cgb = inst->MOS1cgb;
    double Cbd = inst->MOS1cbd;
    double Cbs = inst->MOS1cbs;
    
    /* Complex frequency multiplication: s·C = (σ + jω)·C */
    double s_real_times_C = s->real * Cgs;
    double s_imag_times_C = s->imag * Cgs;
    
    /* Stamp into complex matrix system */
    SMPaddToElement(matrix, inst->MOS1gateGatePtrPZ, s_real_times_C, s_imag_times_C);
    SMPaddToElement(matrix, inst->MOS1gateSourcePtrPZ, -s_real_times_C, -s_imag_times_C);
    /* ... stamp all capacitive terms */
    
    return OK;
}
```

**Mathematical Mapping**: The pole-zero implementation directly solves the Laplace-domain system:
\[
(G + sC)X(s) = B
\]
where:
- `G` is the real conductance matrix (DC Jacobian linearized at operating point)
- `C` is the capacitance matrix
- `s = σ + jω` is the complex frequency variable
- `X(s)` is the complex node voltage vector
- `B` is the source vector (typically unit input for transfer function calculation)

### **4. Sensitivity Analysis Implementation**

#### **Adjoint Method Implementation (`mos1sld.c`)**
The sensitivity analysis uses the adjoint method to compute derivatives of circuit responses with respect to parameters:

```c
void MOS1sLoad(MOS1instance *inst, CKTcircuit *ckt, int *row, int *col, double *values) {
    /* Compute sensitivity derivatives using chain rule */
    
    /* ∂Id/∂VTO = -gm (from threshold voltage equation) */
    double dId_dVTO = -inst->MOS1gm;
    
    /* ∂Id/∂KP = Id/KP (proportional relationship) */
    double dId_dKP = inst->MOS1cdrain / inst->MOS1modPtr->MOS1kp;
    
    /* ∂Id/∂LAMBDA = Id·Vds/(1 + λ·Vds) */
    double dId_dLAMBDA = inst->MOS1cdrain * inst->MOS1vds / 
                        (1.0 + inst->MOS1modPtr->MOS1lambda * inst->MOS1vds);
    
    /* ∂Id/∂γ requires body effect calculation */
    double sqrt_phi = sqrt(inst->MOS1modPtr->MOS1phi);
    double sqrt_phi_vbs = sqrt(2.0 * inst->MOS1modPtr->MOS1phi + inst->MOS1vbs);
    double dVth_dgamma = sqrt_phi_vbs - sqrt_phi;
    double dId_dGAMMA = -inst->MOS1gm * dVth_dgamma;
    
    /* Stamp sensitivity contributions into adjoint system */
    values[*row] += dId_dVTO;
    col[(*row)++] = inst->MOS1modPtr->MOS1vt0Sens;
    
    values[*row] += dId_dKP;
    col[(*row)++] = inst->MOS1modPtr->MOS1kpSens;
    
    values[*row] += dId_dLAMBDA;
    col[(*row)++] = inst->MOS1modPtr->MOS1lambdaSens;
    
    values[*row] += dId_dGAMMA;
    col[(*row)++] = inst->MOS1modPtr->MOS1gammaSens;
}
```

**Mathematical Foundation**: The adjoint method solves two systems:
1. **Original system**: `J·x = b` (standard circuit equations)
2. **Adjoint system**: `Jᵀ·λ = c` where `c` is the output vector

The sensitivity is then: `∂R/∂p = λᵀ·(∂J/∂p·x - ∂b/∂p)`

The code implements the term `∂J/∂p·x` through the partial derivatives `dId_dVTO`, `dId_dKP`, etc.

### **5. Convergence Testing and Numerical Stability**

#### **Convergence Test Implementation (`mos1conv.c`)**
Implements the SPICE convergence criteria for Newton-Raphson iteration:

```c
int MOS1convTest(MOS1instance *inst, CKTcircuit *ckt) {
    /* Compute terminal voltages from MNA solution */
    double vgs = ckt->CKTrhs[inst->MOS1gNode] - ckt->CKTrhs[inst->MOS1sNode];
    double vds = ckt->CKTrhs[inst->MOS1dNode] - ckt->CKTrhs[inst->MOS1sNode];
    double vbs = ckt->CKTrhs[inst->MOS1bNode] - ckt->CKTrhs[inst->MOS1sNode];
    
    /* Compute changes from previous iteration */
    double delvgs = vgs - inst->MOS1vgs_old;
    double delvds = vds - inst->MOS1vds_old;
    double delvbs = vbs - inst->MOS1vbs_old;
    double delid = inst->MOS1cdrain - inst->MOS1cdrain_old;
    
    /* SPICE tolerance parameters */
    double reltol = ckt->CKTreltol;      /* Typically 1e-3 */
    double abstol = ckt->CKTvoltTol;     /* Typically 1e-6 */
    double vntol = ckt->CKTvoltTol;      /* Voltage noise tolerance */
    
    /* Voltage convergence: |Δx| ≤ reltol·max(|x|,|x_old|) + abstol */
    if(fabs(delvgs) > reltol * MAX(fabs(vgs), fabs(inst->MOS1vgs_old)) + vntol)
        return OK; /* Not converged */
    
    if(fabs(delvds) > reltol * MAX(fabs(vds), fabs(inst->MOS1vds_old)) + vntol)
        return OK;
    
    if(fabs(delvbs) > reltol * MAX(fabs(vbs), fabs(inst->MOS1vbs_old)) + vntol)
        return OK;
    
    /* Current convergence */
    double deltol = reltol * MAX(fabs(inst->MOS1cdrain), fabs(inst->MOS1cdrain_old)) + abstol;
    if(fabs(delid) > deltol)
        return OK;
    
    /* All checks passed - device converged */
    return CONVERGED;
}
```

**Mathematical Significance**: This implements the mixed relative-absolute convergence criterion:
\[
|\Delta x_i| \leq \epsilon_r \cdot \max(|x_i|, |x_i^{\text{old}}|) + \epsilon_a
\]
where:
- \(\epsilon_r = \text{RELTOL} = 10^{-3}\)
- \(\epsilon_a = \text{VNTOL} = 10^{-6}\) for voltages, \(\text{ABSTOL} = 10^{-12}\) for currents

#### **Local Truncation Error Control (`mos1trun.c`)**
Implements LTE calculation for adaptive time-step control:

```c
double MOS1trunc(MOS1instance *inst, CKTcircuit *ckt, double *timestep) {
    /* Get charge states from state vector */
    double qgs_old = *(ckt->CKTrhsOld + inst->MOS1qgs);
    double qgs_new = inst->MOS1qgs;
    
    /* Compute derivatives using backward differences */
    double dqdt = (qgs_new - qgs_old) / ckt->CKTdeltaOld[0];
    double d2qdt2 = (dqdt - inst->MOS1dqdt_old) / ckt->CKTdeltaOld[0];
    
    /* LTE = h²/12 · |d³q/dt³| ≈ h²/12 · |d²q/dt² - d²q/dt²_old|/h */
    double lte = fabs(ckt->CKTdeltaOld[0] * ckt->CKTdeltaOld[0] * d2qdt2 / 12.0);
    
    /* Compare against tolerance */
    if(lte > ckt->CKTtrtol) {
        /* Reduce time step by factor of 2 */
        *timestep = 0.5 * ckt->CKTdeltaOld[0];
        return E_LOCALTRUNC;
    }
    
    /* Store for next iteration */
    inst->MOS1dqdt_old = dqdt;
    
    return OK;
}
```

**Mathematical Basis**: The LTE formula for the trapezoidal integration method:
\[
\text{LTE} = \frac{h^3}{12} \left| \frac{d^3q}{dt^3}(\xi) \right| \approx \frac{h^2}{12} \left| \frac{d^2q}{dt^2} \right|
\]
where \(h\) is the time step and \(q\) is the charge.

### **6. Noise Analysis Implementation**

#### **Thermal and Flicker Noise (`mos1noi.c`)**
Implements the noise source models for circuit noise analysis:

```c
void MOS1noise(MOS1instance *inst, CKTcircuit *ckt, double freq, double *lnoise, double *inoise) {
    /* Thermal noise: i_d² = (8kT/3)gm Δf */
    double thermal_noise = (8.0 * CONSTboltz * ckt->CKTtemp / 3.0) * inst->MOS1gm;
    
    /* Flicker noise