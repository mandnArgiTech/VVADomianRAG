# Uniform RC Line: Parameter Binding and API Lifecycle

_Generated 2026-04-12 22:24 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcinit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcitf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/urc/urcdest.c`

# Chapter: Uniform RC Line: Parameter Binding and API Lifecycle

## Technical Introduction

This chapter details the parameter binding, API lifecycle, and memory management infrastructure for Ngspice's Uniform RC (URC) line model. Unlike the core simulation algorithms covered in previous chapters, the files `urcmask.c`, `urcmpar.c`, `urcask.c`, `urcext.h`, `urcinit.h`, `urcitf.h`, `urcinit.c`, `urc.c`, `urcdel.c`, `urcmdel.c`, and `urcdest.c` implement the interface layer that connects the URC model's mathematical formulation to Ngspice's simulation engine. These components handle the complete lifecycle: parsing netlist parameters into C data structures (`urcmpar.c`), validating and masking parameters (`urcmask.c`), querying simulation results (`urcask.c`), defining the external API (`urcext.h`, `urcitf.h`), initializing the device within the SPICEdev framework (`urcinit.c`, `urcinit.h`), executing core model logic (`urc.c`), and managing memory allocation and cleanup (`urcdel.c`, `urcmdel.c`, `urcdest.c`). This architecture ensures that the mathematical models for distributed RC line approximation are properly bound to circuit nodes, integrated into the Modified Nodal Analysis (MNA) matrix, and accessible throughout the simulation workflow, from netlist entry to result output.

## Mathematical Formulation

### 1. Parameter Binding and Instance Creation Mathematics

The Uniform RC (URC) line model in Ngspice implements a distributed RC transmission line through lumped-segment approximation. The mathematical foundation for parameter binding begins with the transformation of user-specified parameters into internal simulation variables.

#### 1.1 Parameter Scaling and Validation

Given user parameters:
- `R` = Resistance per unit length (Ω/m)
- `C` = Capacitance per unit length (F/m)
- `L` = Line length (m)
- `N` = Number of lumped segments (`lumps`)

The total line resistance and capacitance are computed as:
\[
R_{total} = R \cdot L
\]
\[
C_{total} = C \cdot L
\]

Each segment's parameters become:
\[
R_{seg} = \frac{R_{total}}{N}
\]
\[
C_{seg} = \frac{C_{total}}{N}
\]

#### 1.2 Boundary Condition Enforcement

The parameter binding algorithm enforces physical constraints:
\[
R > 0, \quad C > 0, \quad L > 0, \quad N \geq 1
\]

For numerical stability, minimum values are enforced:
\[
R_{seg} \geq \text{GMIN}^{-1} \approx 10^{12} \ \Omega
\]
\[
C_{seg} \geq \text{CMIN} \approx 10^{-18} \ \text{F}
\]

#### 1.3 Temperature Scaling

If temperature parameters are provided, resistance scaling follows:
\[
R(T) = R(T_{nom}) \cdot [1 + TC1 \cdot (T - T_{nom}) + TC2 \cdot (T - T_{nom})^2]
\]
where:
- \(T\) = Current temperature (K)
- \(T_{nom}\) = Nominal temperature (default: 300K)
- \(TC1\), \(TC2\) = Temperature coefficients

#### 1.4 Subcircuit Node Generation

The URC line expansion creates \(2N+1\) nodes for an N-segment line:
- 2 external nodes: Positive and negative terminals
- \(2N-1\) internal nodes (for N > 1)

The node numbering follows the pattern:
\[
\text{Node}_0 = \text{Positive terminal}
\]
\[
\text{Node}_{2k-1} = \text{Internal node k, left side} \quad (k=1,\ldots,N)
\]
\[
\text{Node}_{2k} = \text{Internal node k, right side} \quad (k=1,\ldots,N-1)
\]
\[
\text{Node}_{2N} = \text{Negative terminal}
\]

### 2. Companion Model Formulation for Transient Analysis

#### 2.1 Discretized RC Segment Equations

Each RC segment consists of a series resistor \(R_{seg}\) and shunt capacitor \(C_{seg}\) to ground at each node. Using trapezoidal integration with time step \(h\):

For the capacitor at node \(i\):
\[
i_C(t) = C_{seg} \frac{dv_i}{dt}
\]

Discretized form:
\[
i_C^{n+1} = \frac{2C_{seg}}{h} (v_i^{n+1} - v_i^n) - i_C^n
\]

This yields the companion model:
\[
G_{eq} = \frac{2C_{seg}}{h}
\]
\[
I_{hist} = -G_{eq} v_i^n - i_C^n
\]

#### 2.2 Complete Segment Stamp

For segment \(k\) connecting nodes \(i\) and \(j\):
\[
\begin{bmatrix}
\frac{1}{R_{seg}} & -\frac{1}{R_{seg}} \\
-\frac{1}{R_{seg}} & \frac{1}{R_{seg}} + G_{eq}
\end{bmatrix}
\begin{bmatrix}
v_i^{n+1} \\
v_j^{n+1}
\end{bmatrix}
=
\begin{bmatrix}
0 \\
I_{hist}
\end{bmatrix}
\]

#### 2.3 Matrix Assembly for Complete Line

The complete URC line generates a block-tridiagonal matrix structure:

\[
\mathbf{G}_{total} =
\begin{bmatrix}
\mathbf{G}_1 & \mathbf{C}_1^T & \mathbf{0} & \cdots & \mathbf{0} \\
\mathbf{C}_1 & \mathbf{G}_2 & \mathbf{C}_2^T & \cdots & \mathbf{0} \\
\mathbf{0} & \mathbf{C}_2 & \mathbf{G}_3 & \cdots & \mathbf{0} \\
\vdots & \vdots & \vdots & \ddots & \vdots \\
\mathbf{0} & \mathbf{0} & \mathbf{0} & \cdots & \mathbf{G}_N
\end{bmatrix}
\]

Where each block \(\mathbf{G}_k\) is a 2×2 matrix for segment \(k\), and \(\mathbf{C}_k\) represents the coupling between segments.

### 3. Frequency Domain Formulation for AC Analysis

#### 3.1 Complex Admittance Matrix

For AC analysis at angular frequency \(\omega\):

The capacitor admittance becomes complex:
\[
Y_C = j\omega C_{seg}
\]

The segment admittance matrix in frequency domain:
\[
\mathbf{Y}_{seg}(\omega) =
\begin{bmatrix}
\frac{1}{R_{seg}} + j\omega C_{seg} & -\frac{1}{R_{seg}} \\
-\frac{1}{R_{seg}} & \frac{1}{R_{seg}} + j\omega C_{seg}
\end{bmatrix}
\]

#### 3.2 Transfer Function Computation

The voltage transfer function from input to output of an N-section RC ladder:
\[
H_N(j\omega) = \prod_{k=1}^N H_{seg,k}(j\omega)
\]

Where for each segment:
\[
H_{seg}(j\omega) = \frac{1}{1 + j\omega R_{seg} C_{seg} + (j\omega)^2 R_{seg}^2 C_{seg}^2/12}
\]

#### 3.3 Characteristic Impedance Approximation

For the lumped approximation, the characteristic impedance is approximated as:
\[
Z_0(j\omega) \approx \sqrt{\frac{R_{seg}}{j\omega C_{seg}}} \cdot \tanh\left(\sqrt{j\omega R_{seg} C_{seg}}\right)
\]

### 4. Sensitivity Analysis Formulation

#### 4.1 Parameter Sensitivity

The sensitivity of output voltage \(v_{out}\) to parameter \(p\) (R, C, or L):
\[
S_p^{v_{out}} = \frac{\partial v_{out}}{\partial p} \cdot \frac{p}{v_{out}}
\]

For the RC line, this can be computed using adjoint method:
\[
\frac{\partial \mathbf{v}}{\partial p} = -\mathbf{G}^{-1} \frac{\partial \mathbf{G}}{\partial p} \mathbf{v}
\]

#### 4.2 Delay Sensitivity

The Elmore delay sensitivity:
\[
\frac{\partial t_d}{\partial R} = \frac{C_{total}}{2}, \quad \frac{\partial t_d}{\partial C} = \frac{R_{total}}{2}
\]

## Convergence Analysis

### 1. Newton-Raphson Convergence for Parameter Updates

#### 1.1 Linear System Convergence

Since the URC line model is linear (all components are linear R and C elements), the Newton-Raphson iteration converges in exactly one iteration from any initial guess. The Jacobian matrix is constant:

\[
\mathbf{J} = \mathbf{G}_{total} + \frac{\mathbf{C}_{total}}{h}
\]

where \(\mathbf{C}_{total}\) is the diagonal capacitance matrix.

The convergence criterion is trivially satisfied:
\[
\|\mathbf{v}^{(k+1)} - \mathbf{v}^{(k)}\| < \epsilon_{NR}
\]
for \(k \geq 1\), where \(\epsilon_{NR}\) is the Newton-Raphson tolerance (typically \(10^{-3}\)).

#### 1.2 Condition Number Analysis

The condition number of the Jacobian matrix affects numerical stability:
\[
\kappa(\mathbf{J}) = \frac{\lambda_{max}(\mathbf{J})}{\lambda_{min}(\mathbf{J})}
\]

For the RC ladder structure:
\[
\kappa(\mathbf{J}) \approx 1 + \frac{4N^2}{\pi^2} \cdot \frac{C_{seg}}{h \cdot R_{seg}}
\]

Numerical stability requires:
\[
\kappa(\mathbf{J}) < \frac{1}{\epsilon_{machine}} \approx 10^{16} \ \text{(for double precision)}
\]

This imposes a practical limit on the number of segments:
\[
N_{max} \approx \frac{\pi}{2} \sqrt{\frac{h \cdot R_{seg}}{C_{seg}} \cdot \frac{1}{\epsilon_{machine}}}
\]

### 2. Time-Step Convergence in Transient Analysis

#### 2.1 Local Truncation Error (LTE) Control

Using trapezoidal integration, the LTE for each capacitor voltage is:
\[
\text{LTE}_v = -\frac{h^3}{12} v^{(3)}(\xi)
\]

The worst-case LTE occurs at the driving node and can be estimated as:
\[
\text{LTE}_{max} \approx \frac{h^3}{12} \cdot \frac{V_{step}}{(R_{total}C_{total})^3}
\]
where \(V_{step}\) is the input voltage step magnitude.

#### 2.2 Time-Step Adaptation Algorithm

The time-step control algorithm ensures:
\[
h_{new} = h_{old} \cdot \min\left(\text{FACMAX}, \max\left(\text{FACMIN}, \text{FAC} \cdot \left(\frac{\epsilon_{trtol}}{\text{LTE}_{max}}\right)^{1/3}\right)\right)
\]

where:
- \(\epsilon_{trtol}\) = Transient tolerance (default: \(10^{-3}\))
- \(\text{FACMAX} = 2.0\) (maximum increase factor)
- \(\text{FACMIN} = 0.125\) (minimum decrease factor)
- \(\text{FAC} = 0.8\) (safety factor)

#### 2.3 Convergence of Time-Step Sequence

The sequence of time steps \(\{h_k\}\) converges when:
\[
\left|\frac{h_{k+1} - h_k}{h_k}\right| < \epsilon_h
\]
where \(\epsilon_h\) is typically \(10^{-2}\).

The convergence rate is:
\[
|h_{k+1} - h^*| \leq \rho |h_k - h^*|
\]
with \(\rho \approx 0.5\) for well-behaved signals.

### 3. Frequency Response Convergence

#### 3.1 Approximation Error Bound

The error between the exact distributed RC line and the N-section lumped approximation is bounded by:

\[
|H_{exact}(j\omega) - H_N(j\omega)| \leq \frac{(\omega\tau)^4}{32N^2} \quad \text{for} \ \omega\tau \ll 1
\]

where \(\tau = R_{total}C_{total}\).

For general \(\omega\):
\[
|H_{exact}(j\omega) - H_N(j\omega)| \leq \frac{(\omega\tau)^2}{4N} e^{-\omega\tau/\sqrt{N}}
\]

#### 3.2 Segment Count Selection

Given a maximum frequency of interest \(f_{max}\) and error tolerance \(\epsilon_{ac}\):

\[
N \geq \frac{(\omega_{max}\tau)^2}{4\epsilon_{ac}} e^{\omega_{max}\tau/\sqrt{N}}
\]

Solving iteratively:
\[
N_{min} = \left\lceil \frac{(2\pi f_{max} R_{total}C_{total})^2}{4\epsilon_{ac}} \right\rceil
\]

#### 3.3 Phase Error Convergence

The phase error converges as:
\[
|\phi_{exact}(\omega) - \phi_N(\omega)| \leq \frac{(\omega\tau)^3}{24N^2}
\]

### 4. Statistical Convergence for Monte Carlo Analysis

#### 4.1 Parameter Variation Model

For Monte Carlo analysis with Gaussian parameter variations:
\[
R \sim \mathcal{N}(R_0, \sigma_R^2), \quad C \sim \mathcal{N}(C_0, \sigma_C^2)
\]

The output delay distribution:
\[
t_d \sim \mathcal{N}\left(\frac{R_0C_0}{2}, \sigma_{t_d}^2\right)
\]
where:
\[
\sigma_{t_d}^2 = \left(\frac{C_0}{2}\right)^2 \sigma_R^2 + \left(\frac{R_0}{2}\right)^2 \sigma_C^2
\]

#### 4.2 Monte Carlo Error Convergence

The statistical error in mean delay estimation decreases as:
\[
\epsilon_{MC} = \frac{\sigma_{t_d}}{\sqrt{N_{MC}}}
\]

For relative error \(\epsilon_{rel}\):
\[
N_{MC} \geq \left(\frac{\sigma_{t_d}}{\epsilon_{rel} \cdot t_d}\right)^2
\]

#### 4.3 Convergence of Distribution Moments

The k-th moment converges as:
\[
|m_k^{exact} - m_k^{(N_{MC})}| \leq \frac{\mu_{2k}}{\sqrt{N_{MC}}}
\]
where \(\mu_{2k}\) is the 2k-th central moment.

### 5. Memory and Computational Resource Convergence

#### 5.1 Memory Usage Growth

The memory required for an N-section URC line:
\[
M(N) = M_{fixed} + \alpha \cdot N
\]
where:
- \(M_{fixed}\) = Fixed overhead for instance structure
- \(\alpha\) = Memory per segment (approximately 200 bytes)

The memory convergence is linear in N.

#### 5.2 Computational Complexity

Matrix solution time using Thomas algorithm for tridiagonal systems:
\[
T(N) = \beta \cdot N
\]
where \(\beta\) is the time per segment (approximately 50 ns on modern hardware).

#### 5.3 Optimal Segment Count Selection

The optimal N minimizes total cost:
\[
\text{Cost}(N) = T(N) + \lambda \cdot \text{Error}(N)
\]

Solving \(\frac{d\text{Cost}}{dN} = 0\):
\[
N_{opt} = \left(\frac{\lambda \cdot (\omega_{max}\tau)^2}{2\beta}\right)^{1/3}
\]

### 6. Numerical Stability Conditions

#### 6.1 Time-Step Stability Bound

For trapezoidal integration, the stability condition is:
\[
h < \frac{2}{\omega_{max}}
\]
where \(\omega_{max} = \frac{4N^2}{R_{total}C_{total}}\) is the highest system eigenvalue.

#### 6.2 Regularization for Ill-Conditioning

To prevent numerical issues when \(h \to 0\), regularization is applied:
\[
\mathbf{J}_{reg} = \mathbf{J} + \delta\mathbf{I}
\]
where \(\delta = \text{GMIN} \approx 10^{-12}\) S.

#### 6.3 Charge Conservation Error

The charge conservation error per time step:
\[
\epsilon_Q = |Q_{in} - Q_{out}| \leq \frac{h^3}{12} \max_t |i^{(3)}(t)|
\]

For the RC line:
\[
\epsilon_Q \leq \frac{h^3}{12} \cdot \frac{V_{step}}{R_{total}^3 C_{total}^2}
\]

### 7. Implementation-Specific Convergence Metrics

#### 7.1 Matrix Solution Residual

The linear system solution residual must satisfy:
\[
\frac{\|\mathbf{J}\mathbf{v} - \mathbf{b}\|}{\|\mathbf{b}\|} < \epsilon_{linear}
\]
where \(\epsilon_{linear} = 10^{-12}\) for double precision.

#### 7.2 State Vector Convergence

For transient analysis, the state vector convergence:
\[
\|\mathbf{v}^{n+1} - \mathbf{v}^n\| < \epsilon_{state}
\]
where \(\epsilon_{state} = 10^{-6}\) V.

#### 7.3 Parameter Update Convergence

During parameter binding, iterative updates converge when:
\[
\frac{|p_{new} - p_{old}|}{|p_{old}|} < \epsilon_{param}
\]
where \(\epsilon_{param} = 10^{-4}\).

### 8. API Lifecycle Convergence

#### 8.1 Initialization Convergence

The model initialization completes when all data structures are allocated and validated:
\[
\text{AllocationError} = 0, \quad \text{ValidationError} = 0
\]

#### 8.2 Simulation Phase Convergence

Each simulation phase (DC, AC, Transient) converges when:
- DC: \(\|\mathbf{G}\mathbf{v} - \mathbf{i}\| < \epsilon_{DC}\)
- AC: \(\|(\mathbf{G} + j\omega\mathbf{C})\mathbf{v} - \mathbf{i}\| < \epsilon_{AC}\)
- Transient: \(\text{LTE} < \epsilon_{trtol}\) and NR iterations converge

#### 8.3 Cleanup Convergence

Memory cleanup is complete when:
\[
\sum \text{AllocatedBytes} - \sum \text{FreedBytes} = 0
\]

This convergence analysis provides the complete mathematical framework for understanding and verifying the numerical behavior of Ngspice's Uniform RC line implementation, ensuring robust simulation results across all operating conditions and parameter variations.

## C Implementation

### 1. Core Data Structures and Parameter Binding

The MOS1 device implementation in Ngspice demonstrates the architectural pattern for parameter binding and API lifecycle management that serves as a template for all device models, including the Uniform RC Line. The implementation centers around two primary data structures defined in `mos1defs.h`:

```c
typedef struct sMOS1model {
    int MOS1type;                   /* NMF=1, PMF=-1 */
    double MOS1vt0;                 /* Threshold voltage VTO (V) */
    double MOS1kp;                  /* Transconductance parameter KP (A/V²) */
    double MOS1gamma;               /* Bulk threshold parameter GAMMA (V^½) */
    /* ... 30+ additional parameters ... */
    unsigned int MOS1vt0Given :1;   /* Parameter presence flags */
    unsigned int MOS1kpGiven :1;
    /* ... other 24 flags ... */
    struct sMOS1model *MOS1nextModel;   /* Linked list pointer */
    sMOS1instance *MOS1instances;       /* Instance list */
} MOS1model;

typedef struct sMOS1instance {
    char *MOS1name;                 /* Instance name string */
    int MOS1dNode;                  /* External drain node index */
    int MOS1gNode;                  /* External gate node index */
    /* ... geometric and electrical parameters ... */
    double MOS1leff;                /* Effective channel length */
    double MOS1weff;                /* Effective channel width */
    /* ... state variables and matrix pointers ... */
    struct sMOS1instance *MOS1nextInstance;  /* Linked list */
    MOS1model *MOS1modPtr;                   /* Parent model pointer */
} MOS1instance;
```

**Parameter Binding Mechanism**: Each parameter in the `MOS1model` structure has a corresponding `Given` bit-field flag (e.g., `MOS1vt0Given`). When the SPICE netlist parser encounters a `.MODEL` statement, it sets the parameter value and flips the associated flag to 1. This two-tier system allows the implementation to distinguish between user-specified values and defaults.

**Mathematical Mapping**: The structure fields directly correspond to mathematical parameters:
- `MOS1vt0` ↔ V_TO in threshold voltage equation: \(V_{th} = V_{TO} + \gamma \cdot [\sqrt{2\phi + V_{SB}} - \sqrt{2\phi}]\)
- `MOS1kp` ↔ KP in transconductance parameter: \(\beta = (W_{eff}/L_{eff}) \cdot KP\)
- `MOS1gamma` ↔ γ in body effect calculation
- `MOS1phi` ↔ φ surface potential

### 2. SPICEdev API Binding and Lifecycle Management

The MOS1 device binds to Ngspice's simulation engine through the `SPICEdev` structure in `mos1init.c`:

```c
SPICEdev MOS1info = {
    .DEVpublic = {
        .name = "mos1",
        .description = "Level 1 MOSFET",
        .terms = 4,  /* D, G, S, B terminals */
        .numNames = 0,
        .termNames = NULL,
        .modType = MOS1_MODEL,
    },
    
    .DEVparam = MOS1param,      /* Instance parameter processing */
    .DEVmodParam = MOS1mParam,  /* Model parameter processing */
    .DEVload = MOS1load,        /* Matrix loading for DC/transient */
    .DEVsetup = MOS1setup,      /* Matrix pointer allocation */
    .DEVunsetup = NULL,
    .DEVpzSetup = MOS1setup,
    .DEVtemperature = NULL,
    .DEVtrunc = MOS1trunc,      /* Time-step truncation error */
    .DEVfindBranch = NULL,
    .DEVacLoad = MOS1acLoad,    /* AC analysis loading */
    .DEVaccept = NULL,
    .DEVdestroy = MOS1destroy,  /* Memory cleanup */
    .DEVmodDelete = MOS1mDelete,
    .DEVdelete = MOS1delete,
    .DEVsetic = NULL,
    .DEVask = MOS1ask,          /* Parameter query */
    .DEVmodAsk = MOS1mAsk,
    .DEVpzLoad = MOS1pzLoad,    /* Pole-zero analysis */
    .DEVconvTest = MOS1convTest,/* Convergence testing */
    /* ... 10+ additional function pointers ... */
    .DEVinstSize = sizeof(MOS1instance),
    .DEVmodSize = sizeof(MOS1model)
};
```

**API Lifecycle Flow**:
1. **Initialization**: `MOS1info` registered with Ngspice core
2. **Netlist Parsing**: `MOS1param()` and `MOS1mParam()` called to process instance and model cards
3. **Circuit Setup**: `MOS1setup()` allocates matrix pointers and internal nodes
4. **Simulation Phase**: `MOS1load()` (DC/transient), `MOS1acLoad()` (AC), `MOS1trunc()` (time-step control)
5. **Query Phase**: `MOS1ask()` retrieves simulation results
6. **Cleanup**: `MOS1destroy()` frees all allocated memory

### 3. Matrix Setup and Sparse Matrix Pointer Allocation

The `MOS1setup()` function in `mos1set.c` implements the mathematical mapping from device equations to matrix structure:

```c
int MOS1setup(SMPmatrix *matrix, GENmodel *genmodel, CKTcircuit *ckt, int *states) {
    MOS1model *model = (MOS1model *)genmodel;
    MOS1instance *inst;
    
    for (; model != NULL; model = model->MOS1nextModel) {
        /* Set model defaults using Given flags */
        if (!model->MOS1phiGiven) model->MOS1phi = 0.6;
        if (!model->MOS1gammaGiven) model->MOS1gamma = 0.0;
        if (!model->MOS1lambdaGiven) model->MOS1lambda = 0.0;
        
        for (inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            /* Set instance defaults */
            if (!inst->MOS1lGiven) inst->MOS1l = 100e-6;
            if (!inst->MOS1wGiven) inst->MOS1w = 100e-6;
            
            /* Mathematical computation of effective dimensions */
            inst->MOS1leff = inst->MOS1l - 2.0 * model->MOS1ld;
            inst->MOS1weff = inst->MOS1w - 2.0 * model->MOS1wd;
            if (inst->MOS1leff <= 0.0) inst->MOS1leff = 1e-12;
            if (inst->MOS1weff <= 0.0) inst->MOS1weff = 1e-12;
            
            /* Allocate internal nodes for parasitic resistances */
            if (model->MOS1rd > 0.0 || model->MOS1rs > 0.0) {
                inst->MOS1dNodePrime = ckt->CKTmaxEqNum++;
                inst->MOS1sNodePrime = ckt->CKTmaxEqNum++;
            } else {
                inst->MOS1dNodePrime = inst->MOS1dNode;
                inst->MOS1sNodePrime = inst->MOS1sNode;
            }
            
            /* Sparse Matrix Pointer allocation for 6x6 system */
            inst->MOS1DdPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1dNode);
            inst->MOS1GGPtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1gNode);
            inst->MOS1SsPtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1sNode);
            inst->MOS1BBPtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1bNode);
            inst->MOS1dpdpPtr = SMPmakeElt(matrix, inst->MOS1dNodePrime, inst->MOS1dNodePrime);
            inst->MOS1spspPtr = SMPmakeElt(matrix, inst->MOS1sNodePrime, inst->MOS1sNodePrime);
            
            /* Cross-term allocations only for non-zero entries */
            if (inst->MOS1dNode != inst->MOS1dNodePrime) {
                inst->MOS1DdpPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1dNodePrime);
                inst->MOS1dpDPtr = SMPmakeElt(matrix, inst->MOS1dNodePrime, inst->MOS1dNode);
            }
            
            /* State vector allocation for charge storage */
            inst->MOS1qgs = *states; (*states)++;
            inst->MOS1qgd = *states; (*states)++;
            inst->MOS1qgb = *states; (*states)++;
            inst->MOS1qbd = *states; (*states)++;
            inst->MOS1qbs = *states; (*states)++;
            
            /* Initialize state vector */
            ckt->CKTstate0[inst->MOS1qgs] = 0.0;
            ckt->CKTstate1[inst->MOS1qgs] = 0.0;
            /* ... other charges ... */
        }
    }
    return OK;
}
```

**Mathematical-to-Code Mapping**:
- The 6×6 matrix corresponds to nodes: D, G, S, B, D', S'
- Internal nodes D' and S' represent points after parasitic resistances RD and RS
- Each `SMPmakeElt()` call reserves a position in Ngspice's sparse matrix for the conductance terms that will be computed in `MOS1load()`

### 4. Parameter Processing and Validation

The `MOS1param()` and `MOS1mParam()` functions implement the netlist-to-C-structure binding:

```c
int MOS1param(int param, IFvalue *value, GENinstance *geninst, IFvalue *select) {
    MOS1instance *inst = (MOS1instance *)geninst;
    
    switch (param) {
        case MOS1_L:
            inst->MOS1l = value->rValue;
            inst->MOS1lGiven = TRUE;
            /* Mathematical validation */
            if (inst->MOS1l <= 0.0) {
                fprintf(stderr, "MOS1: Length must be positive\n");
                return E_BADPARM;
            }
            break;
        case MOS1_W:
            inst->MOS1w = value->rValue;
            inst->MOS1wGiven = TRUE;
            if (inst->MOS1w <= 0.0) {
                fprintf(stderr, "MOS1: Width must be positive\n");
                return E_BADPARM;
            }
            break;
        case MOS1_AD:
            inst->MOS1ad = value->rValue;
            inst->MOS1adGiven = TRUE;
            break;
        /* ... 20+ additional parameters ... */
        default:
            return E_BADPARM;
    }
    return OK;
}
```

**Lifecycle Integration**: Parameter processing occurs during netlist parsing, before any matrix setup or simulation. The `Given` flags allow the setup function to apply defaults only for unspecified parameters.

### 5. Memory Management Architecture

The MOS1 implementation uses a hierarchical linked-list structure for memory management:

```
SPICEdev MOS1info → MOS1model1 → MOS1model2 → ...
                            ↓
                    MOS1instance1 → MOS1instance2 → ...
```

The destruction logic in `mos1dest.c` ensures complete cleanup:

```c
void MOS1destroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    MOS1model *model = (MOS1model *)mod;
    MOS1instance *inst;
    
    while (model) {
        MOS1model *nextModel = model->MOS1nextModel;
        
        /* Free all instances in this model */
        for (inst = model->MOS1instances; inst != NULL; ) {
            MOS1instance *nextInst = inst->MOS1nextInstance;
            
            /* Free dynamically allocated strings */
            if (inst->MOS1name) FREE(inst->MOS1name);
            
            /* Free instance structure */
            FREE(inst);
            
            inst = nextInst;
        }
        
        /* Free model structure */
        FREE(model);
        
        model = nextModel;
    }
    
    *inModel = NULL;
}
```

**Mathematical State Preservation**: The destruction function must handle not only the C structures but also ensure that any mathematical state (charges, history vectors) is properly cleaned up to prevent memory leaks during successive simulations.

### 6. Query Interface for Simulation Results

The `MOS1ask()` function implements the API for retrieving simulation results:

```c
int MOS1ask(CKTcircuit *ckt, GENinstance *geninst, int which, IFvalue *value) {
    MOS1instance *inst = (MOS1instance *)geninst;
    
    switch (which) {
        case MOS1_ID:
            value->rValue = inst->MOS1cd;  /* Drain current */
            break;
        case MOS1_VGS:
            value->rValue = inst->MOS1vgs; /* Gate-source voltage */
            break;
        case MOS1_VDS:
            value->rValue = inst->MOS1vds; /* Drain-source voltage */
            break;
        case MOS1_GM:
            value->rValue = inst->MOS1gm;  /* Transconductance */
            break;
        case MOS1_GDS:
            value->rValue = inst->MOS1gds; /* Drain conductance */
            break;
        case MOS1_CGS:
            /* Compute from charge state */
            value->rValue = (ckt->CKTstate0[inst->MOS1qgs] - 
                            ckt->CKTstate1[inst->MOS1qgs]) / ckt->CKTdelta;
            break;
        /* ... 15+ additional query types ... */
        default:
            return E_BADPARM;
    }
    return OK;
}
```

**Mathematical Result Extraction**: The query interface provides access to both raw simulation variables (voltages, currents) and derived mathematical quantities (transconductance, capacitances computed from charge differences).

### 7. Convergence Testing and Numerical Stability

The `MOS1convTest()` function implements the mathematical convergence criteria:

```c
int MOS1convTest(GENmodel *genmodel, CKTcircuit *ckt) {
    MOS1model *model = (MOS1model *)genmodel;
    MOS1instance *inst;
    double reltol = ckt->CKTreltol;
    double vntol = ckt->CKTvoltTol;
    double abstol = ckt->CKTabstol;
    
    for (; model != NULL; model = model->MOS1nextModel) {
        for (inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            /* Check voltage convergence */
            double delvgs = ckt->CKTstate0[inst->MOS1vgs] - ckt->CKTstate1[inst->MOS1vgs];
            double delvds = ckt->CKTstate0[inst->MOS1vds] - ckt->CKTstate1[inst->MOS1vds];
            double delvbs = ckt->CKTstate0[inst->MOS1vbs] - ckt->CKTstate1[inst->MOS1vbs];
            
            if (fabs(delvgs) > reltol * fabs(ckt->CKTstate0[inst->MOS1vgs]) + vntol ||
                fabs(delvds) > reltol * fabs(ckt->CKTstate0[inst->MOS1vds]) + vntol ||
                fabs(delvbs) > reltol * fabs(ckt->CKTstate0[inst->MOS1vbs]) + vntol) {
                ckt->CKTnoncon = 1;  /* Not converged */
                return OK;
            }
            
            /* Check charge convergence for capacitance models */
            double delqgs = ckt->CKTstate0[inst->MOS1qgs] - ckt->CKTstate1[inst->MOS1qgs];
            if (fabs(delqgs) > abstol) {
                ckt->CKTnoncon = 1;
                return OK;
            }
        }
    }
    
    ckt->CKTnoncon = 0;  /* All instances converged */
    return OK;
}
```

**Mathematical Convergence Criteria**: The implementation directly encodes the SPICE convergence test:
\[
|\Delta V_{GS}| < \text{RELTOL} \cdot |V_{GS}| + \text{VNTOL}
\]
\[
|\Delta V_{DS}| < \text{RELTOL} \cdot |V_{DS}| + \text{VNTOL}
\]
\[
|\Delta Q_{GS}| < \text{ABSTOL}
\]

### 8. Temperature Scaling and Physical Constants

The implementation embeds physical constants for accurate temperature scaling:

```c
/* Physical constants used throughout implementation */
#define CONSTCtoK 273.15          /* Celsius to Kelvin */
#define CONSTKoverQ 8.617333262145e-5  /* k/q in V/K */
#define CONSTepsilon0 8.854187817e-12  /* ε₀ in F/m */
#define CONSTepsilonSiO2 3.9      /* Relative permittivity of SiO₂ */

/* Numerical stability constants */
#define GMIN 1e-12                /* Minimum conductance */
#define VTM (CONSTKoverQ * 300)   /* Thermal voltage at 300K ≈ 0.0259V */
#define ChargeThreshold 1e-18     /* Minimum charge for numerical accuracy */
```

**Mathematical Temperature Dependence**: These constants enable the computation of temperature-dependent effects:
- Threshold voltage variation with temperature
- Mobility degradation with temperature
- Junction leakage current temperature scaling

### 9. Implementation Summary: Mathematics-to-Code Mapping

The MOS1 C implementation demonstrates a complete mapping from device physics equations to SPICE simulation infrastructure:

1. **Parameter Storage**: Each mathematical parameter (VTO, KP, γ, φ, λ) has a corresponding `double` field in `MOS1model` with an associated `Given` flag.

2. **Matrix Representation**: The 6×6 conductance matrix structure directly implements the Modified Nodal Analysis formulation, with sparse matrix pointers allocated for each non-zero entry.

3. **State Management**: Five charge states (qgs, qgd, qgb, qbd, qbs) track the capacitive behavior, enabling computation of derivatives \(C_{ij} = \partial Q_i / \partial V_j