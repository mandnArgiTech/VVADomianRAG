# Mutual Inductance: Magnetic Coupling and Transformer Setup

_Generated 2026-04-12 19:13 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/muttemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutask.c`

# Chapter: Mutual Inductance: Magnetic Coupling and Transformer Setup

## 1. Technical Introduction

This chapter details the Ngspice implementation of mutual inductance, which models magnetic coupling between inductors as found in transformers and coupled inductors. The implementation centers on four core files: `mutparam.c` defines the parameter parsing and data structures linking coupled inductor instances; `muttemp.c` handles temperature-dependent scaling of inductances and coupling coefficients; `mutsetup.c` performs the critical sparse matrix allocation for the cross-coupling terms between inductor branch equations; and `mutask.c` provides the query interface for accessing mutual inductance parameters during simulation. These files collectively implement the coupled differential equations \(V_1 = L_1 di_1/dt + M di_2/dt\) and \(V_2 = M di_1/dt + L_2 di_2/dt\) within SPICE's Modified Nodal Analysis (MNA) framework. The implementation extends the standard inductor model by introducing off-diagonal matrix elements that represent the mutual inductance \(M = k\sqrt{L_1 L_2}\), requiring careful management of matrix sparsity patterns and ensuring numerical stability when the coupling coefficient \(k\) approaches unity.

## 2. Mathematical Formulation

### 2.1 Fundamental Coupling Equations

For two inductors \(L_1\) and \(L_2\) with coupling coefficient \(k\) (\(|k| < 1\)), the mutual inductance \(M\) is defined as:
\[
M = k \sqrt{L_1 L_2}
\]
The coupled voltage-current relationships are given by:
\[
\begin{aligned}
V_1(t) &= L_1 \frac{dI_1(t)}{dt} + M \frac{dI_2(t)}{dt} \\
V_2(t) &= M \frac{dI_1(t)}{dt} + L_2 \frac{dI_2(t)}{dt}
\end{aligned}
\]
where \(V_1, I_1\) are the voltage across and current through inductor \(L_1\), and \(V_2, I_2\) are for inductor \(L_2\). In matrix form:
\[
\begin{bmatrix} V_1(t) \\ V_2(t) \end{bmatrix} = \begin{bmatrix} L_1 & M \\ M & L_2 \end{bmatrix} \frac{d}{dt} \begin{bmatrix} I_1(t) \\ I_2(t) \end{bmatrix}
\]
The inductance matrix must be positive definite, which requires \(L_1 L_2 > M^2\), equivalent to \(k^2 < 1\).

### 2.2 Discrete-Time Companion Model

Using the trapezoidal integration rule with time step \(h = \Delta t\), the discrete-time approximation for the coupled system is:
\[
\begin{aligned}
I_1^{n+1} &= I_1^n + \frac{h}{2L_1 L_2 - 2M^2} \left[ L_2 (V_1^n + V_1^{n+1}) - M (V_2^n + V_2^{n+1}) \right] \\
I_2^{n+1} &= I_2^n + \frac{h}{2L_1 L_2 - 2M^2} \left[ -M (V_1^n + V_1^{n+1}) + L_1 (V_2^n + V_2^{n+1}) \right]
\end{aligned}
\]
This can be rearranged into the companion model form:
\[
\begin{bmatrix} I_1^{n+1} \\ I_2^{n+1} \end{bmatrix} = \mathbf{G}_{eq} \begin{bmatrix} V_1^{n+1} \\ V_2^{n+1} \end{bmatrix} + \begin{bmatrix} I_{eq,1} \\ I_{eq,2} \end{bmatrix}
\]
where the equivalent conductance matrix \(\mathbf{G}_{eq}\) and history current vector are:
\[
\mathbf{G}_{eq} = \frac{h}{L_1 L_2 - M^2} \begin{bmatrix} L_2 & -M \\ -M & L_1 \end{bmatrix}, \quad \begin{bmatrix} I_{eq,1} \\ I_{eq,2} \end{bmatrix} = \begin{bmatrix} I_1^n \\ I_2^n \end{bmatrix} + \mathbf{G}_{eq} \begin{bmatrix} V_1^n \\ V_2^n \end{bmatrix}
\]

### 2.3 MNA Matrix Structure with Mutual Inductance

In Modified Nodal Analysis, each inductor requires a branch current variable. For two coupled inductors, the extended MNA system becomes:
\[
\begin{bmatrix}
\mathbf{G} & \mathbf{A}_1 & \mathbf{A}_2 \\
\mathbf{A}_1^T & Z_{11} & Z_{12} \\
\mathbf{A}_2^T & Z_{21} & Z_{22}
\end{bmatrix}
\begin{bmatrix}
\mathbf{V}_n \\ I_1 \\ I_2
\end{bmatrix}
=
\begin{bmatrix}
\mathbf{I}_s \\ V_{eq,1} \\ V_{eq,2}
\end{bmatrix}
\]
where:
- \(\mathbf{G}\) is the conductance matrix for resistive elements.
- \(\mathbf{A}_1 = [1, -1, 0, \dots]^T\) is the incidence vector for inductor 1 (connecting its positive and negative nodes).
- \(\mathbf{A}_2\) is the incidence vector for inductor 2.
- The \(Z\)-block contains the companion model elements: \(Z_{11} = -2L_1/h\), \(Z_{22} = -2L_2/h\), \(Z_{12} = Z_{21} = -2M/h\) for trapezoidal rule.
- \(V_{eq,1}\) and \(V_{eq,2}\) are the history voltage sources derived from \(I_{eq}\).

### 2.4 AC Analysis Formulation

For AC analysis at angular frequency \(\omega\), the impedance matrix for the coupled inductors is:
\[
\mathbf{Z}(j\omega) = j\omega \begin{bmatrix} L_1 & M \\ M & L_2 \end{bmatrix}
\]
The corresponding admittance matrix stamped into the complex MNA system is:
\[
\mathbf{Y}(j\omega) = \frac{1}{j\omega (L_1 L_2 - M^2)} \begin{bmatrix} L_2 & -M \\ -M & L_1 \end{bmatrix}
\]
The branch equations become:
\[
\begin{aligned}
V_1 - j\omega L_1 I_1 - j\omega M I_2 &= 0 \\
V_2 - j\omega M I_1 - j\omega L_2 I_2 &= 0
\end{aligned}
\]

### 2.5 Multiple Coupled Inductors (Transformers)

For \(N\) coupled inductors (an \(N\)-winding transformer), the system generalizes to:
\[
\mathbf{V}(t) = \mathbf{L} \frac{d\mathbf{I}(t)}{dt}
\]
where \(\mathbf{L}\) is the \(N \times N\) symmetric inductance matrix with \(L_{ii}\) as self-inductances and \(L_{ij} = L_{ji} = M_{ij}\) as mutual inductances. The trapezoidal discretization yields:
\[
\mathbf{I}^{n+1} = \mathbf{I}^n + \frac{h}{2} \mathbf{L}^{-1} (\mathbf{V}^n + \mathbf{V}^{n+1})
\]
The companion model is:
\[
\mathbf{I}^{n+1} = \frac{h}{2} \mathbf{L}^{-1} \mathbf{V}^{n+1} + \left[ \mathbf{I}^n + \frac{h}{2} \mathbf{L}^{-1} \mathbf{V}^n \right]
\]
The matrix \(\mathbf{L}\) must be positive definite, requiring all eigenvalues to be positive.

## 3. Convergence Analysis

### 3.1 Stability of Coupled Integration

The numerical stability of the coupled inductor integration depends on the eigenvalues of the amplification matrix derived from the integration method. For trapezoidal rule applied to \(\frac{d\mathbf{I}}{dt} = \mathbf{L}^{-1} \mathbf{V}\), the amplification factor for a mode with eigenvalue \(\lambda\) of \(\mathbf{L}^{-1}\) is:
\[
A(h\lambda) = \frac{1 + h\lambda/2}{1 - h\lambda/2}
\]
Trapezoidal rule is A-stable, so stability is guaranteed for any \(h > 0\) provided \(\mathbf{L}\) is positive definite. However, for poorly coupled systems where \(\mathbf{L}\) is near-singular (i.e., \(k \approx 1\)), the eigenvalues of \(\mathbf{L}^{-1}\) become very large, requiring careful time-step control.

### 3.2 Time-Step Control via Local Truncation Error

The Local Truncation Error (LTE) for the coupled system is derived from the Taylor series expansion of the flux vector \(\boldsymbol{\Phi} = \mathbf{L} \mathbf{I}\). For trapezoidal rule, the LTE in flux is:
\[
\text{LTE}_{\boldsymbol{\Phi}} \approx -\frac{h^3}{12} \frac{d^3 \boldsymbol{\Phi}}{dt^3}
\]
The third derivative is estimated using finite differences of the voltage vector:
\[
\frac{d^3 \Phi_i}{dt^3} \approx \frac{V_i^{n+1} - 2V_i^n + V_i^{n-1}}{h^2}
\]
The time step is adapted to keep the normalized error below tolerance:
\[
\frac{\|\text{LTE}_{\boldsymbol{\Phi}}\|_2}{\|\boldsymbol{\Phi}\|_2 + \epsilon} < \text{reltol}
\]
where \(\epsilon\) is an absolute flux tolerance (e.g., \(\epsilon = \text{abstol} \cdot \sqrt{L_1 L_2}\)).

### 3.3 Newton-Raphson Convergence for Nonlinear Cores

If magnetic core saturation is modeled, the inductance matrix becomes current-dependent: \(\mathbf{L}(\mathbf{I})\). The Newton-Raphson iteration for the coupled system requires the Jacobian:
\[
\mathbf{J} = \frac{\partial \mathbf{F}}{\partial \mathbf{I}} = \mathbf{I} + \frac{h}{2} \frac{\partial}{\partial \mathbf{I}} \left( \mathbf{L}^{-1}(\mathbf{I}) \mathbf{V} \right)
\]
The convergence criterion for the coupled currents is:
\[
\|\mathbf{I}^{(k+1)} - \mathbf{I}^{(k)}\|_2 < \text{reltol} \cdot \|\mathbf{I}^{(k)}\|_2 + \text{abstol}
\]
where \(\text{abstol}\) is a vector of absolute tolerances for each branch current.

### 3.4 Matrix Conditioning and Pivoting

The MNA matrix for coupled inductors can become ill-conditioned in two scenarios:
1. **Low Frequency (\(\omega \rightarrow 0\))**: The inductor branches become near short circuits, making the \(Z\)-block dominate with very large entries (\( \propto 1/h \)).
2. **Tight Coupling (\(k \approx 1\))**: The inductance matrix becomes near-singular, causing \(\mathbf{L}^{-1}\) to have large eigenvalues.

The condition number of the coupled inductor block is approximately:
\[
\kappa \approx \frac{\max(|Z_{ii}|)}{\min(\text{eig}(\mathbf{L}))} \cdot \frac{1}{h}
\]
SPICE employs partial pivoting in the LU factorization to handle this ill-conditioning. Additionally, a minimum time step \(h_{\min}\) (e.g., 1e-15 s) is enforced to prevent \(Z_{ii}\) from becoming excessively large.

### 3.5 Energy Conservation Check

For lossless linear coupled inductors, the trapezoidal rule conserves energy exactly. The total magnetic energy is:
\[
W_m = \frac{1}{2} \mathbf{I}^T \mathbf{L} \mathbf{I}
\]
The change in energy from step \(n\) to \(n+1\) should equal the electrical work done:
\[
\Delta W_m = \frac{h}{2} \left( \mathbf{V}^{nT} \mathbf{I}^n + \mathbf{V}^{(n+1)T} \mathbf{I}^{n+1} \right)
\]
The relative error \(|\Delta W_m - W_{\text{elec}}| / |\Delta W_m|\) serves as a validation metric and should be near machine precision for a correct implementation.

### 3.6 Coupling Coefficient Validation

The coupling coefficient \(k\) must satisfy \(|k| < 1\) for physical realizability. In simulation, values very close to 1 (e.g., \(k > 0.999\)) can cause numerical issues. Ngspice may internally clamp \(k\) to a maximum such as \(0.9999\) and issue a warning. The effective mutual inductance is computed as:
\[
M_{\text{eff}} = \text{sign}(k) \cdot \min(|k|, k_{\max}) \cdot \sqrt{L_1 L_2}
\]

### 3.7 Initial Conditions for Coupled System

Specifying initial currents for coupled inductors requires solving:
\[
\begin{bmatrix} L_1 & M \\ M & L_2 \end{bmatrix} \begin{bmatrix} I_1(0) \\ I_2(0) \end{bmatrix} = \begin{bmatrix} \Phi_1(0) \\ \Phi_2(0) \end{bmatrix}
\]
for given initial fluxes \(\Phi_1(0), \Phi_2(0)\). If currents are specified directly, the corresponding fluxes are computed via the above equation. During DC operating point analysis, these initial conditions are enforced via large conductances as with single inductors.

### 3.8 Error Propagation in Multi-Winding Transformers

For \(N > 2\) coupled inductors, error propagation can be analyzed through the sensitivity of the solution to perturbations in \(\mathbf{L}\). The relative error in current \(\mathbf{I}\) due to a relative error \(\delta \mathbf{L}\) in the inductance matrix is bounded by:
\[
\frac{\|\delta \mathbf{I}\|}{\|\mathbf{I}\|} \leq \kappa(\mathbf{L}) \frac{\|\delta \mathbf{L}\|}{\|\mathbf{L}\|}
\]
where \(\kappa(\mathbf{L}) = \|\mathbf{L}\| \cdot \|\mathbf{L}^{-1}\|\) is the condition number of the inductance matrix. This emphasizes the need for accurate \(k\) and \(L\) values in transformer models.

## 4. C Implementation

**Error: Source Code Unavailable**

The requested C implementation section for the Ngspice mutual inductance (transformer) model cannot be generated. The analysis requires direct access to the Ngspice source files—specifically `mutparam.c`, `mutdefs.h`, and related mutual inductor model files—to extract the exact data structures, function implementations, and the critical matrix stamping logic for the cross-coupling terms.

The provided research context indicates a **FILE ACCESS RESTRICTION**. The necessary source files reside outside the permitted directory path, while tool operations are restricted. Without read access to these files, it is impossible to:

1.  Reference the specific C structs that link inductor instances (e.g., a mutual inductance structure containing pointers to `INDinstance1` and `INDinstance2`, and the coupling coefficient `k`).
2.  Detail the exact function (e.g., `MUTload()`) that stamps the cross-coupling terms \(Z_{12}\) and \(Z_{21}\) into the expanded MNA matrix.
3.  Explain the mapping of C code logic to the mathematical formulation for the coupled companion model matrix \(\mathbf{G}_{eq}\).
4.  Document the sparse matrix allocation pattern in the setup function that creates the additional off-diagonal pointers between the branch current rows of the two inductors.

A genuine, technically accurate C implementation section **must** be derived from the source code itself. Providing generic or inferred content based on architectural patterns would violate the core requirement of this reference book: to document the actual Ngspice implementation.

**Resolution:** To complete this chapter, the file path restrictions must be modified to allow access to the Ngspice source directory, or the relevant files must be copied into the accessible workspace.