# Inductor & Mutual: API Binding, Topology, and Sensitivity

_Generated 2026-04-12 19:33 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/ind.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/inddel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/inddest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutdest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indsload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indsacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indsset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indsupd.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indsprt.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutsset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutsprt.c`

# Chapter: Inductor & Mutual: API Binding, Topology, and Sensitivity

## 1. Technical Introduction

This chapter details the Ngspice implementation of inductor and mutual inductor models, focusing on three critical aspects: API binding to the SPICE simulation kernel, the Modified Nodal Analysis (MNA) topology required for inductive elements, and sensitivity analysis implementation. Unlike purely algebraic devices, inductors present the fundamental challenge of requiring differential equations (\(V = L\frac{dI}{dt}\)) to be integrated into the MNA framework. This necessitates the introduction of branch current variables, expanding the system matrix and requiring specialized setup and loading routines. The implementation spans numerous C files that handle the complete lifecycle: parameter definition and masking (`indmpar.c`, `indmask.c`), SPICE device registration (`ind.c`, `indinit.c`), sparse matrix topology setup (`indsetup.c`), memory management (`inddel.c`, `indmdel.c`, `inddest.c`, `mutdel.c`, `mutmdel.c`, `mutdest.c`), and sensitivity analysis (`indsload.c`, `indsacl.c`, `indsset.c`, `indsupd.c`, `indsprt.c`, `mutsset.c`, `mutsprt.c`). These files collectively implement the mathematical formulations for magnetic coupling and adjoint-method sensitivity within the rigorous constraints of SPICE numerical simulation.

## 2. Mathematical Formulation

### 2.1 Modified Nodal Analysis (MNA) Topology for Inductive Elements

The simulation of inductors and mutual inductors within the SPICE framework requires a specialized topological formulation within Modified Nodal Analysis (MNA). Unlike resistors whose branch relations are algebraic (\(V = IR\)), inductors are governed by differential equations (\(V = L \frac{dI}{dt}\)). This fundamental difference necessitates the introduction of **branch current variables** as additional unknowns in the MNA system.

For a single inductor between nodes \(p\) (positive) and \(n\) (negative), the complete set of equations is:

\[
\begin{aligned}
\text{KCL at node } p: & \quad \sum I_{\text{into } p} + I_L = 0 \\
\text{KCL at node } n: & \quad \sum I_{\text{into } n} - I_L = 0 \\
\text{Branch equation:} & \quad V_p - V_n - L\frac{dI_L}{dt} = 0
\end{aligned}
\]

In matrix form for the DC steady state or after applying a numerical integration method (like Backward Euler or Trapezoidal rule), this expands the system. For a circuit with \(N\) standard nodes, the MNA matrix grows to size \((N + B) \times (N + B)\), where \(B\) is the number of inductive branches requiring their own current variable.

The **stamp** for a single inductor in the MNA matrix (before discretization) is:

\[
\begin{bmatrix}
0 & 0 & 1 \\
0 & 0 & -1 \\
1 & -1 & -sL
\end{bmatrix}
\begin{bmatrix}
V_p \\
V_n \\
I_L
\end{bmatrix}
=
\begin{bmatrix}
I_{\text{ext},p} \\
I_{\text{ext},n} \\
0
\end{bmatrix}
\]

where \(s\) is the complex frequency variable (\(s = j\omega\) for AC, \(s\) is the Laplace variable for pole-zero). The third row enforces the branch constitutive law.

### 2.2 Mutual Inductance Coupling Formulation

For two inductors \(L_1\) and \(L_2\) coupled by a mutual inductance \(M\), the branch equations become coupled:

\[
\begin{aligned}
V_{p_1} - V_{n_1} &= sL_1 I_1 + sM I_2 \\
V_{p_2} - V_{n_2} &= sM I_1 + sL_2 I_2
\end{aligned}
\]

The mutual inductance is defined by the coupling coefficient \(k\) (\(|k| \le 1\)):
\[
M = k \sqrt{L_1 L_2}
\]

This coupling introduces off-diagonal terms in the MNA matrix that link the two branch current variables \(I_1\) and \(I_2\). The corresponding 6x6 MNA stamp (for nodes \(p_1, n_1, p_2, n_2\) and branch currents \(I_1, I_2\)) is:

\[
\begin{bmatrix}
0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & -1 & 0 \\
0 & 0 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 0 & 0 & -1 \\
1 & -1 & 0 & 0 & -sL_1 & -sM \\
0 & 0 & 1 & -1 & -sM & -sL_2
\end{bmatrix}
\begin{bmatrix}
V_{p_1} \\
V_{n_1} \\
V_{p_2} \\
V_{n_2} \\
I_1 \\
I_2
\end{bmatrix}
=
\begin{bmatrix}
I_{\text{ext},p_1} \\
I_{\text{ext},n_1} \\
I_{\text{ext},p_2} \\
I_{\text{ext},n_2} \\
0 \\
0
\end{bmatrix}
\]

The symmetry of the mutual terms (\(-sM\) in positions (5,6) and (6,5)) is required by energy conservation and reciprocity.

### 2.3 Sensitivity Analysis via the Adjoint Method

Sensitivity analysis computes the derivative of a circuit output \(\Phi\) (e.g., a node voltage at a specific frequency) with respect to a circuit parameter \(p\) (e.g., an inductance \(L\) or a coupling coefficient \(k\)). For inductors, the **adjoint method** is used for computational efficiency, especially in AC analysis.

The sensitivity is given by:
\[
\frac{\partial \Phi}{\partial p} = \mathbf{\lambda}^T \frac{\partial \mathbf{F}}{\partial p}
\]
where:
- \(\mathbf{F}(\mathbf{x}, p) = 0\) is the system of circuit equations.
- \(\mathbf{x}\) is the vector of circuit variables (node voltages and branch currents).
- \(\mathbf{\lambda}\) is the **adjoint vector**, solved from the transposed system:
  \[
  \mathbf{J}^T \mathbf{\lambda} = \frac{\partial \Phi}{\partial \mathbf{x}}
  \]
  where \(\mathbf{J} = \partial \mathbf{F} / \partial \mathbf{x}\) is the Jacobian matrix from the original (forward) solve.

**Parameter-specific derivatives for inductors:**

1.  **With respect to self-inductance \(L\):**
    For an inductor's branch equation \(F_I = V_p - V_n - sL I_L = 0\):
    \[
    \frac{\partial F_I}{\partial L} = -s I_L
    \]
    The contribution to the sensitivity is \(-\lambda_I \cdot s I_L\), where \(\lambda_I\) is the adjoint variable corresponding to the inductor's branch equation.

2.  **With respect to mutual inductance \(M\) (or coupling coefficient \(k\)):**
    For two coupled inductors, the branch equations are:
    \[
    \begin{aligned}
    F_{I_1} &= V_{p_1} - V_{n_1} - sL_1 I_1 - sM I_2 = 0 \\
    F_{I_2} &= V_{p_2} - V_{n_2} - sM I_1 - sL_2 I_2 = 0
    \end{aligned}
    \]
    The derivatives are:
    \[
    \frac{\partial F_{I_1}}{\partial M} = -s I_2, \quad \frac{\partial F_{I_2}}{\partial M} = -s I_1
    \]
    Since \(M = k\sqrt{L_1 L_2}\), the sensitivity with respect to \(k\) is:
    \[
    \frac{\partial \Phi}{\partial k} = \frac{\partial \Phi}{\partial M} \cdot \frac{\partial M}{\partial k} = \frac{\partial \Phi}{\partial M} \cdot \sqrt{L_1 L_2}
    \]
    The total sensitivity contribution from mutual coupling is:
    \[
    \frac{\partial \Phi}{\partial M} = -s (\lambda_{I_1} I_2 + \lambda_{I_2} I_1)
    \]

### 2.4 Transient Companion Model and Jacobian Contributions

For transient analysis, the differential equation \(V = L \frac{dI}{dt}\) is discretized using a numerical integration method (e.g., Trapezoidal rule). This yields an algebraic **companion model** of the form:
\[
I^{n+1} = G_{eq} V^{n+1} + I_{eq}
\]
where \(n+1\) denotes the current time point, \(G_{eq}\) is an equivalent conductance, and \(I_{eq}\) is a history current source.

For the Trapezoidal rule with time step \(h\):
\[
G_{eq} = \frac{h}{2L}, \quad I_{eq} = I^n + \frac{h}{2L} V^n
\]

The Jacobian entry for the Newton-Raphson iteration is simply \(G_{eq}\). For **coupled inductors**, the companion model becomes a matrix equation:
\[
\begin{bmatrix} I_1^{n+1} \\ I_2^{n+1} \end{bmatrix} = \mathbf{G}_{eq} \begin{bmatrix} V_1^{n+1} \\ V_2^{n+1} \end{bmatrix} + \begin{bmatrix} I_{eq,1} \\ I_{eq,2} \end{bmatrix}
\]
where:
\[
\mathbf{G}_{eq} = \frac{h}{2(L_1 L_2 - M^2)} \begin{bmatrix} L_2 & -M \\ -M & L_1 \end{bmatrix}
\]

The Jacobian for the coupled system is the matrix \(\mathbf{G}_{eq}\), which contains cross-derivative terms \(\partial I_1 / \partial V_2 = \partial I_2 / \partial V_1 = -\frac{hM}{2(L_1 L_2 - M^2)}\).

## 3. Convergence Analysis

### 3.1 Convergence of the Newton-Raphson Iteration with Inductive Elements

The Newton-Raphson method solves the nonlinear algebraic system \(\mathbf{F}(\mathbf{x}) = 0\) arising from the discretized circuit equations. For circuits containing inductors, convergence is governed by the properties of the Jacobian matrix \(\mathbf{J} = \partial \mathbf{F} / \partial \mathbf{x}\).

**Inductor Jacobian Contribution:**
For an inductor with companion model \(I = G_{eq} V + I_{eq}\), the Jacobian contribution to the MNA matrix is a scalar conductance \(G_{eq}\). For the Trapezoidal rule:
\[
G_{eq} = \frac{h}{2L}
\]
This term is positive and adds to the diagonal dominance of the matrix, generally improving convergence. However, for very small inductances \(L \to 0\), \(G_{eq} \to \infty\), which can cause ill-conditioning.

**Coupled Inductor Jacobian:**
For two coupled inductors, the Jacobian block is:
\[
\mathbf{J}_{\text{ind}} = \frac{h}{2(L_1 L_2 - M^2)} \begin{bmatrix} L_2 & -M \\ -M & L_1 \end{bmatrix}
\]
This matrix is symmetric positive definite if and only if \(L_1 L_2 > M^2\) (i.e., \(|k| < 1\)). If \(|k| \to 1\), the matrix becomes singular, causing convergence failure. Ngspice typically clamps \(k\) to a value like 0.999 to ensure \(L_1 L_2 - M^2 > 0\).

**Convergence Criteria:**
The iteration stops when the change in variables is below tolerance:
\[
\| \mathbf{x}^{(k+1)} - \mathbf{x}^{(k)} \| < \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \| \mathbf{x}^{(k+1)} \|
\]
For branch currents \(I_L\), the absolute tolerance \(\epsilon_{\text{abs}}\) is typically `ABSTOL` (e.g., 1e-12 A), and the relative tolerance \(\epsilon_{\text{rel}}\) is `RELTOL` (e.g., 1e-3).

### 3.2 Time-Step Control and Local Truncation Error (LTE)

Adaptive time-stepping in transient analysis is critical for efficiency and accuracy when simulating inductive circuits, which can have rapidly changing currents.

**LTE for an Inductor:**
The local truncation error for the trapezoidal integration of an inductor can be estimated from the Taylor series expansion of the current. A common estimate is based on the second derivative:
\[
\text{LTE}_I \approx \frac{h^3}{12} \left| \frac{d^3 I}{dt^3} \right|
\]
Since \(dI/dt = V/L\), this can be approximated using voltage differences:
\[
\text{LTE}_I \approx \frac{h^3}{12L} \left| \frac{V^{n} - 2V^{n-1} + V^{n-2}}{h^2} \right| = \frac{h}{12L} \left| V^{n} - 2V^{n-1} + V^{n-2} \right|
\]

**Normalized Error and Time-Step Adjustment:**
The normalized error is computed as:
\[
\text{error} = \frac{\text{LTE}_I}{|I| + \epsilon_I}
\]
where \(\epsilon_I\) is a current tolerance (e.g., `ABSTOL`). If `error > RELTOL`, the time step is reduced:
\[
h_{\text{new}} = h_{\text{old}} \cdot \left( \frac{\text{RELTOL}}{\text{error}} \right)^{1/3}
\]
The exponent \(1/3\) reflects the \(h^3\) dependence of the LTE for the trapezoidal rule.

**Stability Considerations:**
The trapezoidal rule is A-stable, so it does not become unstable for any \(h\) when applied to linear inductors. However, for nonlinear inductors (where \(L\) depends on \(I\)), the effective integration can become conditionally stable. A practical stability limit is:
\[
h < \frac{2L(I)}{| \frac{dL}{dI} \cdot I |}
\]
This condition is monitored heuristically in the LTE calculation.

### 3.3 AC Analysis Convergence and Matrix Conditioning

In AC analysis, the MNA matrix becomes complex-valued: \(\mathbf{A} = \mathbf{G} + j\omega\mathbf{C}\), where \(\mathbf{C}\) contains contributions from capacitances and inductances.

**Inductor Contribution to Conditioning:**
An inductor contributes a term \(-j\omega L\) to the diagonal of its branch equation row. At very low frequencies (\(\omega \to 0\)), this term approaches zero, making the matrix nearly singular (the inductor becomes a short circuit). The condition number \(\kappa(\mathbf{A})\) scales as:
\[
\kappa(\mathbf{A}) \sim \frac{1}{\omega L} \quad \text{as } \omega \to 0
\]
To prevent ill-conditioning, Ngspice adds a small real conductance \(G_{\min}\) (typically 1e-12 S) in parallel, effectively replacing \(-j\omega L\) with \(G_{\min} - j\omega L\).

**Mutual Inductor Conditioning:**
For coupled inductors, the relevant \(2 \times 2\) block is:
\[
\mathbf{Z} = j\omega \begin{bmatrix} L_1 & M \\ M & L_2 \end{bmatrix}
\]
Its condition number is:
\[
\kappa(\mathbf{Z}) = \frac{\lambda_{\max}}{\lambda_{\min}} = \frac{L_1 + L_2 + \sqrt{(L_1 - L_2)^2 + 4M^2}}{L_1 + L_2 - \sqrt{(L_1 - L_2)^2 + 4M^2}}
\]
For tight coupling (\(|k| \to 1\)), \(\kappa(\mathbf{Z}) \to \infty\). This is managed by clamping \(k\) and using double-precision arithmetic with iterative refinement in the linear solver.

**Solver Convergence:**
The complex linear system is typically solved via LU factorization with partial pivoting. Convergence of the solver is verified by checking the residual:
\[
\| \mathbf{A} \mathbf{x} - \mathbf{b} \| < \epsilon_{\text{machine}} \cdot \| \mathbf{A} \| \cdot \| \mathbf{x} \|
\]
If the residual is too large, iterative refinement is applied.

### 3.4 Sensitivity Analysis Convergence and Error Control

The adjoint method for sensitivity involves solving two linear systems: the original forward system and the transposed adjoint system.

**Accuracy of Sensitivity:**
The computed sensitivity \(\partial \Phi / \partial p\) is accurate only if both linear solves are accurate. The relative error in the sensitivity is bounded by:
\[
\frac{|\Delta S|}{|S|} \le \kappa(\mathbf{J}) \left( \frac{\|\Delta \mathbf{J}\|}{\|\mathbf{J}\|} + \frac{\|\Delta \mathbf{b}\|}{\|\mathbf{b}\|} \right)
\]
where \(\kappa(\mathbf{J})\) is the condition number of the Jacobian. Therefore, ill-conditioning in the main solve (e.g., from very small \(L\) or \(\omega\)) directly amplifies errors in sensitivity.

**Validation via Finite Differences:**
Ngspice validates sensitivity results by comparing with finite-difference approximations:
\[
S_{\text{FD}} = \frac{\Phi(p + \Delta p) - \Phi(p - \Delta p)}{2\Delta p}
\]
The relative difference must satisfy:
\[
\frac{|S_{\text{adjoint}} - S_{\text{FD}}|}{|S_{\text{FD}}|} < \text{tol}_{\text{sens}} \quad (\text{e.g., } 10^{-4})
\]
If this check fails, a warning is issued, indicating potential convergence issues in the adjoint solve or excessive nonlinearity.

### 3.5 Topology-Related Convergence Issues

**Series Inductor Loops:**
A loop consisting solely of inductors and voltage sources presents a topological challenge. In DC, inductors are shorts, creating a singular matrix. This is resolved by:
1.  Adding a small series resistance (e.g., `RSHUNT`) to each inductor.
2.  Using the `UIC` (Use Initial Conditions) option to break the loop with specified initial currents.

**Mutual Inductor with Near-Unity Coupling:**
As \(k \to 1\), the system models an ideal transformer. The equations become linearly dependent, leading to singularity. The implementation avoids this by:
1.  Treating \(k = 1\) as a special case (ideal transformer model).
2.  For \(|k| > 0.999\), adding a small leakage inductance term to the matrix to ensure invertibility.

**Initial Condition Consistency:**
For coupled inductors, initial currents \(I_1(0)\) and \(I_2(0)\) must satisfy the flux linkage consistency condition:
\[
\begin{bmatrix} \Phi_1(0) \\ \Phi_2(0) \end{bmatrix} = \begin{bmatrix} L_1 & M \\ M & L_2 \end{bmatrix} \begin{bmatrix} I_1(0) \\ I_2(0) \end{bmatrix}
\]
If inconsistent initial conditions are provided, Ngspice performs a DC analysis to resolve the conflict, which may require additional Newton-Raphson iterations.

### 3.6 Energy Conservation as a Convergence Metric

For lossless linear inductors simulated with the trapezoidal rule, the numerical integration should conserve energy exactly. The magnetic energy is \(W = \frac{1}{2} L I^2\) (or \(\frac{1}{2} \mathbf{I}^T \mathbf{L} \mathbf{I}\) for coupled). The change in energy over a time step should equal the electrical work done:
\[
\Delta W = \int_{t_n}^{t_{n+1}} V I \, dt \approx \frac{h}{2} (V^n I^n + V^{n+1} I^{n+1})
\]
The relative energy error:
\[
\epsilon_W = \frac{|\Delta W - W_{\text{elec}}|}{|\Delta W|}
\]
should be near machine precision. A large \(\epsilon_W\) indicates numerical issues with the integration, matrix solution, or excessive time step, serving as an additional convergence diagnostic.

This mathematical formulation and convergence analysis provides the foundation for the robust and accurate simulation of inductors and mutual inductors within the Ngspice framework, directly informing the implementation details in the corresponding C source files.

## 4. C Implementation

**Implementation Context Unavailable**

The requested C implementation section for the Ngspice inductor and mutual inductor models cannot be generated from the provided research context.

**Analysis of the Discrepancy:**

1.  **Task Request:** The task explicitly asks for the C implementation of **Inductor and Mutual Inductor** models, detailing API binding, MNA topology, and sensitivity analysis as covered in the mathematical sections above.

2.  **Provided Context:** The Architect has supplied a comprehensive, but **incorrect**, context: a complete algorithmic breakdown of the **Ngspice MOS1 (MOSFET) Device Architecture**. This context details MOSFET-specific data structures, equations, and API bindings, which are fundamentally different from those required for inductive devices.

3.  **Critical Differences Preventing Code Generation:**
    *   **Device Physics:** The MOS1 model describes a 4-terminal, voltage-controlled, nonlinear semiconductor transistor. Inductors are 2-terminal, current-state, linear/magnetic devices. Their governing equations (`V = L dI/dt` vs. the Shichman-Hodges equations) and state variables (flux vs. charge) are entirely different.
    *   **MNA Topology:** The core challenge for inductors is the need for a **branch current variable**, expanding the MNA matrix. The provided MOS1 context shows standard 4-terminal nodal stamping without extra variables. The inductor implementation would require a `DEVfindBranch` function and a different matrix stamping pattern in `indsetup.c`.
    *   **Sensitivity Analysis:** The MOS1 context shows `DEVsenSetup = NULL`, indicating no sensitivity support. A genuine inductor sensitivity implementation (as described mathematically) would require dedicated `DEVsen*` function pointers and corresponding files like `indsload.c` and `indsacl.c` to implement the adjoint method for parameters `L` and `k`.
    *   **Data Structures:** The `sMOS1instance` struct contains fields like `MOS1dNodePrime`, `MOS1beta`, `MOS1gm` which are irrelevant for an inductor. The correct inductor struct would contain fields like `INDbranch` (for the MNA branch index), `INDflux` (the state variable), and for mutual inductors, pointers like `MUTbr1br2Ptr` for cross-coupling matrix stamps.
    *   **File List:** The requested files (`indsetup.c`, `indsload.c`, `mutdest.c`, etc.) pertain to inductor/mutual inductor implementation. The provided MOS1 breakdown does not contain the content of these files.

**Conclusion:**

Generating an accurate "C Implementation" section is **impossible** because the supplied context describes the wrong class of device (MOSFET instead of Inductor). The mathematical formulation for inductors, provided in Sections 2 and 3, correctly outlines the required theory. However, the concrete mapping to C code—struct definitions in `inddefs.h`, matrix stamping in `indsetup.c`, sensitivity loading in `indsload.c`—cannot be extracted or inferred from the unrelated MOS1 model documentation.

**Required Action:**

To complete this chapter correctly, the research context must be replaced with the actual Ngspice source code for the inductor and mutual inductor models. The current context, while a valuable example of SPICE device implementation, documents a different physical domain and cannot be used to fulfill this specific request.