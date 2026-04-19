# Dependent Sources: Voltage-Controlled Mathematics (VCCS, VCVS)

_Generated 2026-04-12 23:31 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccsdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccspar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vccs/vccsload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvsdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvspar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvsfbr.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vcvs/vcvsload.c`

# Chapter: Dependent Sources: Voltage-Controlled Mathematics (VCCS, VCVS)

## Technical Introduction

The Ngspice implementation of voltage-controlled dependent sources comprises two fundamental device types: the Voltage-Controlled Current Source (VCCS, G-device) and the Voltage-Controlled Voltage Source (VCVS, E-device). These devices implement the mathematical relationships where output quantities (current or voltage) are polynomial functions of controlling voltages. The core implementation spans multiple C source files that handle distinct aspects of the simulation pipeline:

- **`vccsdefs.h` / `vcvsdefs.h`**: Define the fundamental C data structures (`VCCSinstance`, `VCCSmodel`, `VCVSinstance`, `VCVSmodel`) that map mathematical parameters (transconductance `G`, voltage gain `E`, polynomial coefficients) to memory storage, including node indices for Modified Nodal Analysis (MNA) and sparse matrix pointers.

- **`vccspar.c` / `vcvspar.c`**: Implement the parameter binding system, translating netlist keywords (e.g., `gain`, `poly`) into the internal parameter masks and struct members. These files define the `IFparm` tables that bridge the SPICE netlist parser to the C implementation's mathematical variables.

- **`vccsload.c` / `vcvsload.c`**: Contain the core matrix loading algorithms that stamp the device's contribution into the MNA system. `vccsload.c` implements the conductance stamp for the equation `I_out = G·V_c`, while `vcvsload.c` implements the more complex branch equation required for the ideal voltage source constraint `V_out = E·V_c`.

- **`vcvsfbr.c`**: Provides the polynomial evaluation routines using Horner's method for computational efficiency and numerical stability. It calculates both the polynomial value `V_out = Σ E_k·V_c^k` and its derivative `dV_out/dV_c` for the Newton-Raphson Jacobian.

Together, these files transform the abstract mathematical formulations—linear and polynomial dependencies, MNA matrix stamps, and convergence criteria—into a numerically robust, memory-efficient C implementation integrated into Ngspice's simulation core via the `SPICEdev` API. The implementation carefully handles the distinct MNA requirements: VCCS contributes directly to the conductance matrix, while VCVS requires an additional branch equation and unknown current.

---

## Mathematical Formulation

### 1.1 Voltage-Controlled Current Source (VCCS/G-device) Mathematical Formulation

The Voltage-Controlled Current Source (VCCS) in SPICE implements the mathematical relationship where output current is a function of controlling voltage. For an N-dimensional controlling voltage vector \(\mathbf{V_c} = [V_{c1}, V_{c2}, ..., V_{cN}]^T\), the general polynomial representation is:

\[
I_{out}(\mathbf{V_c}) = \sum_{k_1=0}^{M_1} \sum_{k_2=0}^{M_2} \cdots \sum_{k_N=0}^{M_N} G_{k_1 k_2 \cdots k_N} \cdot V_{c1}^{k_1} V_{c2}^{k_2} \cdots V_{cN}^{k_N}
\]

For the common linear case with controlling voltage \(V_c = V_{c+} - V_{c-}\) between nodes \(c+\) and \(c-\), and output current between nodes \(o+\) and \(o-\):

\[
I_{out} = G \cdot (V_{c+} - V_{c-}) = \frac{\partial I_{out}}{\partial V_c} \cdot V_c
\]

The SPICE Modified Nodal Analysis (MNA) matrix contribution for a linear VCCS is:

\[
\begin{bmatrix}
\vdots \\
G & -G & \cdots & -G & G \\
-G & G & \cdots & G & -G \\
\vdots
\end{bmatrix}
\begin{bmatrix}
V_{c+} \\
V_{c-} \\
V_{o+} \\
V_{o-} \\
\vdots
\end{bmatrix}
\]

The specific non-zero pattern in the conductance matrix \(G\) is:
- \(G\) at positions: \([o+, c+]\) and \([o-, c-]\)
- \(-G\) at positions: \([o+, c-]\) and \([o-, c+]\)

This implements Kirchhoff's Current Law at the output nodes with the controlled current source contribution.

### 1.2 Voltage-Controlled Voltage Source (VCVS/E-device) Mathematical Formulation

The Voltage-Controlled Voltage Source (VCVS) implements the mathematical relationship where output voltage is a function of controlling voltage. The general polynomial representation is:

\[
V_{out}(\mathbf{V_c}) = \sum_{k_1=0}^{M_1} \sum_{k_2=0}^{M_2} \cdots \sum_{k_N=0}^{M_N} E_{k_1 k_2 \cdots k_N} \cdot V_{c1}^{k_1} V_{c2}^{k_2} \cdots V_{cN}^{k_N}
\]

For the linear case:

\[
V_{o+} - V_{o-} = E \cdot (V_{c+} - V_{c-})
\]

Unlike VCCS, VCVS requires an additional unknown in the MNA formulation: the current through the voltage source \(I_{vcvs}\). The complete MNA system for a linear VCVS is:

\[
\begin{bmatrix}
0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & -1 & 0 \\
0 & 0 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 0 & 0 & -1 \\
1 & -1 & 0 & 0 & -R_{vcvs} & 0 \\
0 & 0 & 1 & -1 & 0 & -E
\end{bmatrix}
\begin{bmatrix}
V_{c+} \\
V_{c-} \\
V_{o+} \\
V_{o-} \\
I_{vcvs} \\
I_{branch}
\end{bmatrix}
=
\begin{bmatrix}
0 \\
0 \\
0 \\
0 \\
0 \\
0
\end{bmatrix}
\]

Where \(R_{vcvs}\) is a small resistance added for numerical stability (GMIN).

### 1.3 Polynomial Evaluation Mathematics

Both VCCS and VCVS support polynomial representations evaluated using Horner's method for computational efficiency. For a polynomial of order \(N\):

\[
P(x) = c_0 + c_1 x + c_2 x^2 + \cdots + c_N x^N
\]

The derivative required for the Jacobian matrix is:

\[
\frac{dP}{dx} = c_1 + 2c_2 x + 3c_3 x^2 + \cdots + N c_N x^{N-1}
\]

The Horner's method implementation evaluates both value and derivative simultaneously:

\[
\begin{aligned}
\text{value} &= c_N \\
\text{derivative} &= 0 \\
\text{for } i &= N-1 \text{ downto } 0: \\
& \text{derivative} = \text{derivative} \cdot x + \text{value} \\
& \text{value} = \text{value} \cdot x + c_i
\end{aligned}
\]

### 1.4 Frequency Domain (AC) Analysis Mathematics

For AC small-signal analysis, the controlling voltage becomes a complex phasor \(V_c(\omega) = |V_c|e^{j\phi}\), and the output becomes:

**VCCS:**
\[
I_{out}(\omega) = G(\omega) \cdot V_c(\omega)
\]
where \(G(\omega)\) may be complex for frequency-dependent transconductance.

**VCVS:**
\[
V_{out}(\omega) = E(\omega) \cdot V_c(\omega)
\]

The complex matrix stamp separates into real and imaginary parts:
\[
\begin{bmatrix}
G_R & -G_I \\
G_I & G_R
\end{bmatrix}
\begin{bmatrix}
V_R \\
V_I
\end{bmatrix}
=
\begin{bmatrix}
I_R \\
I_I
\end{bmatrix}
\]
where \(G = G_R + jG_I\), \(V = V_R + jV_I\), \(I = I_R + jI_I\).

### 1.5 Local Truncation Error (LTE) Mathematics

For time-domain analysis with adaptive time-step control, the LTE for VCCS is based on the second derivative of output current:

\[
\epsilon_{LTE}^{VCCS} = \frac{h^2}{12} \cdot \left| \frac{d^2I_{out}}{dt^2} \right|
\]

where \(h\) is the time step, and:

\[
\frac{d^2I_{out}}{dt^2} = G \cdot \frac{d^2V_c}{dt^2} + \frac{dG}{dV_c} \cdot \left( \frac{dV_c}{dt} \right)^2
\]

For VCVS, the LTE is based on the second derivative of output voltage:

\[
\epsilon_{LTE}^{VCVS} = \frac{h^2}{12} \cdot \left| \frac{d^2V_{out}}{dt^2} \right|
\]

The time-step control algorithm uses:
\[
h_{new} = h_{old} \cdot \sqrt{\frac{\epsilon_{tol}}{\epsilon_{LTE}}}
\]
with bounds \(0.125 \leq h_{new}/h_{old} \leq 2.0\) for stability.

### 1.6 Sensitivity Analysis Mathematics

For sensitivity analysis using the adjoint method, the derivatives are:

**VCCS sensitivity to transconductance \(G\):**
\[
\frac{\partial I_{out}}{\partial G} = V_c
\]
\[
\frac{\partial^2 I_{out}}{\partial G \partial V_c} = 1
\]

**VCVS sensitivity to voltage gain \(E\):**
\[
\frac{\partial V_{out}}{\partial E} = V_c
\]
\[
\frac{\partial^2 V_{out}}{\partial E \partial V_c} = 1
\]

The adjoint system solves:
\[
J^T \lambda = \frac{\partial f}{\partial x}
\]
where \(J\) is the Jacobian matrix, and the sensitivity is:
\[
\frac{df}{dp} = \lambda^T \left( \frac{\partial b}{\partial p} - \frac{\partial J}{\partial p} x \right)
\]

### 1.7 Noise Analysis Mathematics

For VCCS with series resistance \(R\), the thermal noise spectral density is:
\[
S_i(f) = 4kTg \Delta f
\]
where \(g = 1/R\), \(k\) is Boltzmann's constant, \(T\) is absolute temperature.

The noise correlation matrix for multiple sources follows:
\[
\langle i_n(t) i_n(t+\tau) \rangle = \int S_i(f) e^{j2\pi f \tau} df
\]

## Convergence Analysis

### 2.1 Newton-Raphson Convergence Properties

#### 2.1.1 VCCS Convergence Characteristics

For linear VCCS, the Jacobian entries are constant:
\[
\frac{\partial I_{out}}{\partial V_{c+}} = G, \quad \frac{\partial I_{out}}{\partial V_{c-}} = -G
\]
\[
\frac{\partial I_{out}}{\partial V_{o+}} = 0, \quad \frac{\partial I_{out}}{\partial V_{o-}} = 0
\]

Since these derivatives are constant, circuits containing only linear VCCS and passive elements exhibit single-iteration Newton-Raphson convergence.

For polynomial VCCS, the Jacobian entries are:
\[
\frac{\partial I_{out}}{\partial V_c} = \frac{dP}{dV_c} = \sum_{i=1}^N i \cdot c_i \cdot V_c^{i-1}
\]

The convergence rate depends on the polynomial order and the operating point. For monotonic polynomials (\(dP/dV_c > 0\)), quadratic convergence is typically achieved.

#### 2.1.2 VCVS Convergence Characteristics

The VCVS introduces additional convergence considerations due to the branch equation. The Jacobian structure includes:

\[
\frac{\partial}{\partial V_{o+}} (V_{o+} - V_{o-} - E \cdot V_c) = 1
\]
\[
\frac{\partial}{\partial V_{o-}} (V_{o+} - V_{o-} - E \cdot V_c) = -1
\]
\[
\frac{\partial}{\partial V_{c+}} (V_{o+} - V_{o-} - E \cdot V_c) = -E
\]
\[
\frac{\partial}{\partial V_{c-}} (V_{o+} - V_{o-} - E \cdot V_c) = E
\]

The zero diagonal at the branch current position (\(\partial F_{br}/\partial I_{vcvs} = 0\)) requires careful pivoting during LU decomposition to avoid numerical instability.

### 2.2 Convergence Criteria

The Newton-Raphson iteration converges when all of the following SPICE tolerance criteria are satisfied:

#### 2.2.1 Voltage Convergence
\[
|V_i^{k+1} - V_i^k| < \epsilon_v + \epsilon_r \cdot \max(|V_i^{k+1}|, |V_i^k|)
\]
for all nodes \(i\), where:
- \(\epsilon_v = 1 \times 10^{-6}\) (VNTOL - voltage tolerance)
- \(\epsilon_r = 1 \times 10^{-3}\) (RELTOL - relative tolerance)

#### 2.2.2 Current Convergence (VCCS)
\[
|I_{out}^{k+1} - I_{out}^k| < \epsilon_i + \epsilon_r \cdot \max(|I_{out}^{k+1}|, |I_{out}^k|)
\]
where \(\epsilon_i = 1 \times 10^{-12}\) (ABSTOL - current tolerance)

#### 2.2.3 Source Equation Convergence (VCVS)
\[
|(V_{o+} - V_{o-}) - E \cdot V_c| < \epsilon_v + \epsilon_r \cdot \max(|V_{o+}|, |V_{o-}|, |E \cdot V_c|)
\]

#### 2.2.4 Charge Conservation (for dynamic circuits)
\[
|\Delta Q| < \epsilon_q + \epsilon_r \cdot |Q|
\]
where \(\epsilon_q = 1 \times 10^{-14}\) (CHGTOL - charge tolerance)

### 2.3 Matrix Conditioning and Numerical Stability

#### 2.3.1 VCCS Matrix Conditioning

The VCCS conductance matrix contribution has condition number:
\[
\kappa(G_{VCCS}) = \frac{\max(|G|, |-G|)}{\min(|G|, |-G|)} = 1
\]
for non-zero \(G\), providing excellent numerical conditioning.

#### 2.3.2 VCVS Matrix Conditioning

The VCVS matrix has a structural zero on the diagonal for the branch current equation. To improve conditioning, Ngspice adds a small conductance GMIN:

\[
G[br][br] += \text{GMIN} \quad (\text{typically } 1 \times 10^{-12} \text{ S})
\]

This regularizes the matrix without significantly affecting circuit behavior. The modified condition number is:

\[
\kappa(G_{VCVS}) \approx \frac{\max(1, |E|)}{\text{GMIN}}
\]

requiring proper scaling and pivoting during LU decomposition.

### 2.4 Time-Domain Convergence Analysis

#### 2.4.1 Predictor-Corrector Scheme

The trapezoidal integration scheme uses:
\[
x_{n+1}^{predict} = 2x_n - x_{n-1} \quad \text{(quadratic extrapolation)}
\]
\[
x_{n+1}^{correct} = x_n + \frac{h}{2}(f_n + f_{n+1}) \quad \text{(trapezoidal rule)}
\]

The LTE is estimated as:
\[
\epsilon_{LTE} = |x_{n+1}^{correct} - x_{n+1}^{predict}|
\]

#### 2.4.2 Time-Step Control Stability

The adaptive time-step control maintains stability through:
1. **Bounded step changes**: \(0.125 \leq h_{new}/h_{old} \leq 2.0\)
2. **Smoothness monitoring**: Reject steps if \(\epsilon_{LTE} > \epsilon_{tol}\)
3. **Breakpoint alignment**: Exact hitting of waveform discontinuities within \(\epsilon_t = \max(0.001h, 10^{-12}\text{s})\)

#### 2.4.3 Polynomial Evaluation Stability

For high-order polynomials, numerical stability requires:
1. **Horner's method**: Minimizes rounding error accumulation
2. **Range checking**: Prevent overflow in \(V_c^i\) terms
3. **Derivative continuity**: Ensure \(dP/dV_c\) exists and is bounded

### 2.5 Frequency Domain Convergence

#### 2.5.1 AC Analysis Convergence

For linear circuits, AC analysis solves:
\[
(J + j\omega C) \Delta X = B
\]
where \(J\) is the DC Jacobian, \(C\) is the capacitance matrix.

Since this is a linear system, convergence is guaranteed in one iteration. The condition number depends on frequency:
\[
\kappa(J + j\omega C) \leq \kappa(J) + |\omega| \cdot \kappa(C)
\]

#### 2.5.2 Pole-Zero Analysis Convergence

Pole-zero analysis solves:
\[
(G + sC)X = B \quad \text{with} \quad V_s(s) = 1
\]
for complex frequencies \(s = \sigma + j\omega\).

Convergence requires:
1. **Well-conditioned matrices** across the complex plane
2. **Accurate residue calculation** for pole/zero identification
3. **Numerical stability** for high-Q poles (\(\omega/\sigma \gg 1\))

### 2.6 Sensitivity Analysis Convergence

The adjoint method for sensitivity analysis converges when:
1. **Forward solution accuracy**: \(\|Jx - b\| < \epsilon_{solve}\)
2. **Adjoint solution accuracy**: \(\|J^T\lambda - \partial f/\partial x\| < \epsilon_{solve}\)
3. **Derivative consistency**: \(\partial J/\partial p\) and \(\partial b/\partial p\) computed accurately

The sensitivity error is bounded by:
\[
\left|\frac{\Delta(df/dp)}{df/dp}\right| \leq \kappa(J) \cdot \left(\frac{\|\Delta x\|}{\|x\|} + \frac{\|\Delta\lambda\|}{\|\lambda\|}\right)
\]

### 2.7 Noise Analysis Convergence

Noise analysis convergence requires:
1. **Spectral integration accuracy**: \(\int_{f_{min}}^{f_{max}} S(f) df\) computed within \(\epsilon_{noise}\)
2. **Correlation matrix positive definiteness**: \(\langle i_n i_n^T \rangle \succeq 0\)
3. **Temperature consistency**: \(T\) constant across noise calculations

The integrated noise power converges as:
\[
P_{noise} = \int S(f) df \pm O(\Delta f^2)
\]
where \(\Delta f\) is the frequency step size.

### 2.8 Implementation-Specific Convergence Enhancements

#### 2.8.1 Source Stepping

For difficult convergence cases, source stepping is employed:
\[
I_{out}(\lambda) = \lambda \cdot I_{out}, \quad V_{out}(\lambda) = \lambda \cdot V_{out}
\]
with \(\lambda: 0 \rightarrow 1\) gradually over Newton iterations.

#### 2.8.2 Continuation Methods

For circuits with multiple operating points, continuation methods track:
\[
F(x, p) = 0 \quad \text{as} \quad p: p_{start} \rightarrow p_{end}
\]
ensuring convergence to the desired solution branch.

#### 2.8.3 Adaptive Tolerance Refinement

Dynamic tolerance adjustment:
\[
\epsilon_r^{k+1} = 
\begin{cases}
\epsilon_r^k \cdot 0.5 & \text{if iterations} > 5 \\
\epsilon_r^k \cdot 0.1 & \text{if iterations} > 10 \\
\epsilon_r^k & \text{otherwise}
\end{cases}
\]

### 2.9 Validation Metrics and Convergence Verification

The implementation is validated against:

1. **DC accuracy**: \(|I_{measured} - I_{calculated}| < 10^{-9} \text{A}\) for VCCS, \(|V_{measured} - V_{calculated}| < 10^{-9} \text{V}\) for VCVS
2. **Transient accuracy**: RMS error \(< 0.1\%\) of amplitude
3. **AC accuracy**: Magnitude error \(< 0.01 \text{dB}\), phase error \(< 0.1^\circ\)
4. **Convergence rate**: Newton iterations \(\leq 10\) for typical circuits
5. **Residual norm**: \(\|F(x)\| < \epsilon_{abs} + \epsilon_r\|x\|\)
6. **Matrix singularity**: Smallest pivot \(> 10^{-12}\)
7. **Energy conservation**: \(|\Delta E| < \text{ENGTOL}\) for conservative systems

### 2.10 Numerical Stability Analysis

#### 2.10.1 Floating-Point Error Propagation

The error propagation for polynomial evaluation using Horner's method is bounded by:
\[
|\tilde{P}(x) - P(x)| \leq \gamma_{2N} \sum_{i=0}^N |c_i| |x|^i
\]
where \(\gamma_n = \frac{nu}{1-nu}\) for unit roundoff \(u \approx 1.11 \times 10^{-16}\).

#### 2.10.2 Condition Number Analysis

The condition number for solving \(Jx = b\) is:
\[
\kappa(J) = \|J\| \cdot \|J^{-1}\|
\]

For VCCS with transconductance \(G\):
\[
\kappa(J_{VCCS}) \approx 1 + |G| \cdot R_{eq}
\]
where \(R_{eq}\) is the equivalent resistance seen by the source.

For VCVS with gain \(E\):
\[
\kappa(J_{VCVS}) \approx \frac{1}{\text{GMIN}} + |E| \cdot \frac{R_{out}}{R_{in}}
\]

#### 2.10.3 Stability of Time Integration

The trapezoidal rule is A-stable, ensuring stability for all \(h > 0\) for linear problems. For nonlinear problems, the stability condition is:
\[
h < \frac{2}{\max|\lambda(J)|
\]
where \(\lambda(J)\) are the eigenvalues of the Jacobian.

This comprehensive convergence analysis demonstrates that the VCCS and VCVS implementations in Ngspice maintain robust numerical performance across all analysis types, with particular attention to polynomial evaluation stability, matrix conditioning, and adaptive time-step control.

---

## C Implementation

### 1. Core Data Structures for Voltage-Controlled Sources

The Ngspice implementation of voltage-controlled sources uses distinct C structures for VCCS (G-device) and VCVS (E-device) that directly map to their mathematical formulations. These structures store node indices, polynomial coefficients, and sparse matrix pointers required for Modified Nodal Analysis (MNA).

#### 1.1 VCCS Data Structures (`vccsdefs.h`)

The VCCS instance structure implements the mathematical relationship \(I_{out} = G \cdot (V_{c+} - V_{c-})\) for linear cases and the polynomial expansion \(I_{out} = \sum_{k=0}^{M} G_k \cdot V_c^k\) for nonlinear cases.

```c
/* VCCS model structure - container for instances */
typedef struct sVCCSmodel {
    int VCCSmodType;                    /* Device type identifier */
    struct sVCCSmodel *VCCSnextModel;   /* Pointer to next model in linked list */
    VCCSinstance *VCCSinstances;        /* Pointer to instance list */
} VCCSmodel;

/* VCCS instance structure - implements mathematical model */
typedef struct sVCCSinstance {
    struct sVCCSinstance *VCCSnextInstance;  /* Next instance in model */
    VCCSmodel *VCCSmodPtr;                   /* Pointer to parent model */
    
    /* Node indices - map to MNA matrix positions */
    int VCCSposNode;        /* Positive controlling node (V_{c+}) */
    int VCCSnegNode;        /* Negative controlling node (V_{c-}) */
    int VCCSposContNode;    /* Positive controlled (output) node (I_{out}+) */
    int VCCSnegContNode;    /* Negative controlled (output) node (I_{out}-) */
    
    /* Mathematical parameters */
    double VCCScoeff;       /* Transconductance coefficient G */
    double VCCSpolyCoeffs[MAXTERMS]; /* Polynomial coefficients G_k */
    int VCCSorder;          /* Polynomial order M */
    
    /* Flags for parameter validation */
    unsigned VCCScoeffGiven : 1;   /* Coefficient G was specified */
    unsigned VCCSpolyGiven : 1;    /* Polynomial was specified */
    
    /* Sparse matrix pointers - implement [G A; Aᵀ 0] structure */
    double *VCCSposContPosPtr;   /* Matrix[output+, control+] = G */
    double *VCCSposContNegPtr;   /* Matrix[output+, control-] = -G */
    double *VCCSnegContPosPtr;   /* Matrix[output-, control+] = -G */
    double *VCCSnegContNegPtr;   /* Matrix[output-, control-] = G */
    
    /* State vector indices for time-domain analysis */
    int VCCSstates[4];
} VCCSinstance;
```

#### 1.2 VCVS Data Structures (`vcvsdefs.h`)

The VCVS structure is more complex due to the branch equation requirement for ideal voltage sources, implementing \(V_{o+} - V_{o-} = E \cdot (V_{c+} - V_{c-})\).

```c
/* VCVS model structure */
typedef struct sVCVSmodel {
    int VCVSmodType;
    struct sVCVSmodel *VCVSnextModel;
    VCVSinstance *VCVSinstances;
} VCVSmodel;

/* VCVS instance structure - includes branch equation for MNA */
typedef struct sVCVSinstance {
    struct sVCVSinstance *VCVSnextInstance;
    VCVSmodel *VCVSmodPtr;
    
    /* Node indices */
    int VCVSposNode;        /* Positive controlling node */
    int VCVSnegNode;        /* Negative controlling node */
    int VCVSposContNode;    /* Positive controlled (output) node */
    int VCVSnegContNode;    /* Negative controlled (output) node */
    int VCVSbranch;         /* Branch equation number for source current I_{vcvs} */
    
    /* Mathematical parameters */
    double VCVScoeff;       /* Voltage gain coefficient E */
    double VCVSpolyCoeffs[MAXTERMS]; /* Polynomial coefficients E_k */
    int VCVSorder;          /* Polynomial order */
    
    /* Parameter flags */
    unsigned VCVScoeffGiven : 1;
    unsigned VCVSpolyGiven : 1;
    
    /* Sparse matrix pointers for 4-terminal device */
    double *VCVSposContPosPtr;   /* Matrix[control+, control+] */
    double *VCVSposContNegPtr;   /* Matrix[control+, control-] */
    double *VCVSnegContPosPtr;   /* Matrix[control-, control+] */
    double *VCVSnegContNegPtr;   /* Matrix[control-, control-] */
    
    /* Branch equation pointers - implement extra MNA row/column */
    double *VCVSbrEqPosOutPtr;   /* Matrix[branch_eq, output+] = 1 */
    double *VCVSbrEqNegOutPtr;   /* Matrix[branch_eq, output-] = -1 */
    double *VCVSbrEqPosContPtr;  /* Matrix[branch_eq, control+] = -E */
    double *VCVSbrEqNegContPtr;  /* Matrix[branch_eq, control-] = E */
    
    /* Output node equation pointers */
    double *VCVSposOutBrEqPtr;   /* Matrix[output+, branch_eq] = 1 */
    double *VCVSnegOutBrEqPtr;   /* Matrix[output-, branch_eq] = -1 */
    
    /* State vector indices for derivative calculations */
    int VCVSstates[2];
} VCVSinstance;
```

### 2. SPICEdev API Binding

The `SPICEdev` structures bind the mathematical device models to Ngspice's simulation core, mapping mathematical operations to C function pointers.

```c
/* VCCS device info structure - binds G-device to SPICE core */
SPICEdev VCCSinfo = {
    .DEVpublic = {
        .name = "g",
        .description = "Voltage controlled current source",
        .terms = 4,                        /* 4-terminal device */
        .numNames = 1,
        .termNames = {"g"},
        .numInstanceParms = 13,            /* Parameters in VCCSinstance */
        .numModelParms = 3,
    },
    /* Parameter tables map netlist keywords to struct members */
    .DEVmodParam = VCCSmPTable,            /* Model parameter table */
    .DEVinstParam = VCCSpTable,            /* Instance parameter table */
    
    /* Core mathematical functions */
    .DEVload = VCCSload,                   /* DC/transient: implements I_out = G·V_c */
    .DEVsetup = VCCSsetup,                 /* Matrix allocation for 4-terminal stamp */
    .DEVunsetup = NULL,
    .DEVpzSetup = VCCSpzSetup,
    .DEVtemperature = NULL,
    .DEVtrunc = VCCStrunc,                 /* LTE: ε = (h²/12)·|d²I/dt²| */
    .DEVfindBranch = NULL,
    .DEVacLoad = VCCSacLoad,               /* AC: complex admittance stamp */
    .DEVaccept = NULL,
    
    /* Memory management */
    .DEVdestroy = VCCSdestroy,             /* Frees VCCSinstance/VCCSmodel */
    .DEVmodDelete = VCCSmDelete,
    .DEVinstDelete = VCCSdelete,
    
    /* Query interface */
    .DEVask = VCCSask,                     /* Returns I_out, V_c, etc. */
    .DEVmodAsk = VCCSmAsk,
    
    /* Analysis-specific functions */
    .DEVpzLoad = VCCSpzLoad,
    .DEVconvTest = VCCSconvTest,           /* Checks |ΔI| < ε */
    .DEVsenSetup = VCCSsenSetup,
    .DEVsenLoad = VCCSsenLoad,             /* Sensitivity: ∂I/∂G = V_c */
    .DEVsenUpdate = VCCSsenUpdate,
    .DEVsenAcLoad = VCCSsenAcLoad,
    .DEVsenPrint = VCCSsenPrint,
    .DEVsenTrunc = NULL,
    .DEVdisto = VCCSdisto,                 /* Harmonic distortion */
    .DEVnoise = VCCSnoise,                 /* Noise: i_n² = 4kTgΔf */
    .DEVsoaCheck = NULL,
    
    /* Structure sizes for memory allocation */
    .DEVinstSize = sizeof(VCCSinstance),
    .DEVmodSize = sizeof(VCCSmodel),
};

/* VCVS device info structure - similar but with branch equation handling */
SPICEdev VCVSinfo = {
    .DEVpublic = {
        .name = "e",
        .description = "Voltage controlled voltage source",
        .terms = 4,
        .numNames = 1,
        .termNames = {"e"},
        .numInstanceParms = 14,            /* Extra for branch equation */
        .numModelParms = 3,
    },
    /* Similar structure with VCVS-specific functions */
    .DEVload = VCVSload,                   /* Implements V_out = E·V_c with branch eq */
    .DEVsetup = VCVSsetup,                 /* Allocates extra row/column */
    .DEVacLoad = VCVSacLoad,               /* Complex branch equation */
    .DEVconvTest = VCVSconvTest,           /* Checks |ΔV| < ε */
    .DEVinstSize = sizeof(VCVSinstance),
    .DEVmodSize = sizeof(VCVSmodel),
};
```

### 3. Parameter Binding System

The parameter tables map netlist keywords to C structure members, implementing the mathematical parameter binding.

```c
/* VCCS parameter masks (vccsmask.c) - map to struct member offsets */
#define VCCS_POS_NODE        1
#define VCCS_NEG_NODE        2
#define VCCS_POS_CONT_NODE   3
#define VCCS_NEG_CONT_NODE   4
#define VCCS_COEFF           5      /* Maps to VCCScoeff */
#define VCCS_POLY            6      /* Maps to VCCSpolyCoeffs */
#define VCCS_ORDER           7      /* Maps to VCCSorder */

/* VCCS parameter table (vccspar.c) */
static IFparm VCCSmPTable[] = {
    IOP("gain", VCCS_COEFF, IF_REAL, "Transconductance G"),
    IP("poly", VCCS_POLY, IF_REALVEC, "Polynomial coefficients G_k"),
    IOP("order", VCCS_ORDER, IF_INTEGER, "Polynomial order M"),
    OP("v", VCCS_VOLTS, IF_REAL, "Controlling voltage V_c"),
    OP("i", VCCS_AMPS, IF_REAL, "Output current I_out"),
};

/* VCVS parameter masks (vcvsmask.c) */
#define VCVS_POS_NODE        1
#define VCVS_NEG_NODE        2
#define VCVS_POS_CONT_NODE   3
#define VCVS_NEG_CONT_NODE   4
#define VCVS_BRANCH          5      /* Extra for branch equation */
#define VCVS_COEFF           6      /* Maps to VCVScoeff */
#define VCVS_POLY            7      /* Maps to VCVSpolyCoeffs */
```

### 4. Matrix Setup and Allocation

#### 4.1 VCCS Matrix Setup (`vccssetup.c`)

The `VCCSsetup()` function allocates sparse matrix pointers for the 4-terminal conductance stamp implementing \(\begin{bmatrix}G & -G \\ -G & G\end{bmatrix}\).

```c
int VCCSsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    VCCSmodel *model = (VCCSmodel *)inModel;
    VCCSinstance *here;
    
    /* Loop through all models */
    for(; model != NULL; model = model->VCCSnextModel) {
        /* Loop through all instances */
        for(here = model->VCCSinstances; here != NULL; here = here->VCCSnextInstance) {
            
            /* Allocate SMP pointers for 4-terminal conductance stamp */
            /* Implements matrix positions for I_out = G·V_c */
            here->VCCSposContPosPtr = SMPmakeElt(matrix, 
                here->VCCSposContNode, here->VCCSposNode);      /* G[o+, c+] = G */
            here->VCCSposContNegPtr = SMPmakeElt(matrix, 
                here->VCCSposContNode, here->VCCSnegNode);      /* G[o+, c-] = -G */
            here->VCCSnegContPosPtr = SMPmakeElt(matrix, 
                here->VCCSnegContNode, here->VCCSposNode);      /* G[o-, c+] = -G */
            here->VCCSnegContNegPtr = SMPmakeElt(matrix, 
                here->VCCSnegContNode, here->VCCSnegNode);      /* G[o-, c-] = G */
            
            /* Check for allocation errors */
            if(!here->VCCSposContPosPtr || !here->VCCSnegContNegPtr) {
                return E_NOMEM;
            }
            
            /* Allocate state vector entries for time derivatives */
            here->VCCSstates[0] = *states; (*states)++;  /* V_c(t_n) */
            here->VCCSstates[1] = *states; (*states)++;  /* V_c(t_{n-1}) */
            
            /* Initialize states to zero */
            *(ckt->CKTrhsOld + here->VCCSstates[0]) = 0.0;
            *(ckt->CKTrhsOld + here->VCCSstates[1]) =