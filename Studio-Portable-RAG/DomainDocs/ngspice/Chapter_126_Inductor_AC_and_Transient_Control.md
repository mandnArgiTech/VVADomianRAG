# Inductor & Mutual: AC Analysis and Transient Time-Stepping

_Generated 2026-04-12 19:24 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/mutpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ind/indtrunc.c`

# Chapter: Inductor & Mutual: AC Analysis and Transient Time-Stepping

## 1. Technical Introduction

This chapter details the Ngspice C implementation for AC analysis, pole-zero analysis, and transient time-stepping of independent and mutually coupled inductors. The core challenge in simulating inductive elements within the Modified Nodal Analysis (MNA) framework is their differential constitutive relationship \(V = L \frac{dI}{dt}\). Ngspice addresses this by introducing branch current variables, expanding the system matrix, and employing numerical integration to create discrete-time companion models. The implementation spans several critical source files: `indacld.c` and `mutacld.c` stamp the complex impedance matrices for frequency-domain AC analysis; `indpzld.c` and `mutpzld.c` handle the generalized complex frequency variable \(s = \sigma + j\omega\) for pole-zero analysis; and `indtrunc.c` implements Local Truncation Error (LTE) estimation for adaptive time-step control in transient simulation. These routines work in concert with the core inductor and mutual inductor data structures defined in `inddefs.h` and `mutdefs.h`, which manage device parameters, state variables (flux), and the sparse matrix pointers required for the expanded MNA formulation. This chapter explicitly maps the mathematical formulations for magnetic coupling and numerical integration to the specific C code that implements them within the SPICE simulation kernel.

## 2. Mathematical Formulation

### 2.1 Modified Nodal Analysis (MNA) Framework for Inductive Elements

In SPICE circuit simulation, inductors and mutual inductors require special treatment within Modified Nodal Analysis (MNA) due to their differential voltage-current relationships. The fundamental constitutive equation for an inductor is:

\[
V_L(t) = L \frac{dI_L(t)}{dt}
\]

where \(V_L\) is the voltage across the inductor, \(I_L\) is the current through it, and \(L\) is the inductance. This differential relationship necessitates introducing branch current variables into the MNA formulation.

For a single inductor between nodes \(p\) (positive) and \(n\) (negative), the MNA system expands to include the branch current \(I_L\) as an additional unknown. The complete set of equations is:

\[
\begin{aligned}
\text{KCL at node } p: & \quad I_{\text{ext},p} + I_L = 0 \\
\text{KCL at node } n: & \quad I_{\text{ext},n} - I_L = 0 \\
\text{Branch equation:} & \quad V_p - V_n - L\frac{dI_L}{dt} = 0
\end{aligned}
\]

In matrix form for time-domain analysis:

\[
\begin{bmatrix}
\mathbf{G} & \mathbf{A} \\
\mathbf{A}^T & \mathbf{0}
\end{bmatrix}
\begin{bmatrix}
\mathbf{V} \\
I_L
\end{bmatrix}
+
\begin{bmatrix}
\mathbf{0} & \mathbf{0} \\
\mathbf{0} & L
\end{bmatrix}
\frac{d}{dt}
\begin{bmatrix}
\mathbf{V} \\
I_L
\end{bmatrix}
=
\begin{bmatrix}
\mathbf{I}_{\text{ext}} \\
0
\end{bmatrix}
\]

where \(\mathbf{G}\) is the conductance matrix for resistive elements, \(\mathbf{A} = [1, -1, 0, \dots]^T\) is the incidence vector for the inductor branch, and \(\mathbf{V}\) is the vector of node voltages.

### 2.2 AC Small-Signal Analysis Formulation

For AC analysis at angular frequency \(\omega = 2\pi f\), the inductor impedance is \(Z_L(j\omega) = j\omega L\). The MNA formulation in the frequency domain becomes algebraic:

\[
\begin{bmatrix}
\mathbf{G} & \mathbf{A} \\
\mathbf{A}^T & -j\omega L
\end{bmatrix}
\begin{bmatrix}
\mathbf{V} \\
I_L
\end{bmatrix}
=
\begin{bmatrix}
\mathbf{I}_{\text{ext}} \\
0
\end{bmatrix}
\]

This complex-valued matrix is implemented in Ngspice by storing separate real and imaginary parts. For an independent inductor, the stamped 3×3 block (nodes \(p\), \(n\), and branch \(I_L\)) is:

\[
\begin{bmatrix}
0 & 0 & 1 \\
0 & 0 & -1 \\
1 & -1 & -j\omega L
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

The third row implements the branch equation \(V_p - V_n - j\omega L I_L = 0\), while the first two rows enforce KCL with the branch current \(I_L\).

### 2.3 Mutual Inductance Coupling Formulation

For two inductors \(L_1\) and \(L_2\) with mutual inductance \(M = k\sqrt{L_1 L_2}\) (where \(|k| \leq 1\) is the coupling coefficient), the coupled equations are:

\[
\begin{aligned}
V_1(t) &= L_1 \frac{dI_1}{dt} + M \frac{dI_2}{dt} \\
V_2(t) &= M \frac{dI_1}{dt} + L_2 \frac{dI_2}{dt}
\end{aligned}
\]

In the frequency domain for AC analysis:

\[
\begin{aligned}
V_1(j\omega) &= j\omega L_1 I_1 + j\omega M I_2 \\
V_2(j\omega) &= j\omega M I_1 + j\omega L_2 I_2
\end{aligned}
\]

The expanded MNA matrix for two coupled inductors includes four node voltages (\(p_1, n_1, p_2, n_2\)) and two branch currents (\(I_1, I_2\)):

\[
\begin{bmatrix}
0 & 0 & 0 & 0 & 1 & 0 \\
0 & 0 & 0 & 0 & -1 & 0 \\
0 & 0 & 0 & 0 & 0 & 1 \\
0 & 0 & 0 & 0 & 0 & -1 \\
1 & -1 & 0 & 0 & -j\omega L_1 & -j\omega M \\
0 & 0 & 1 & -1 & -j\omega M & -j\omega L_2
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

The cross-coupling terms \(-j\omega M\) appear in positions (5,6) and (6,5), linking the two branch equations.

### 2.4 Transient Analysis: Numerical Integration Methods

For transient analysis, the differential equations must be discretized using numerical integration. Ngspice primarily uses the Trapezoidal rule and Backward Euler method.

**Trapezoidal Rule Discretization:**
For a single inductor, applying the trapezoidal rule with time step \(h = \Delta t\):

\[
I_L^{n+1} = I_L^n + \frac{h}{2L}\left(V_L^n + V_L^{n+1}\right)
\]

where superscripts denote time steps: \(n\) = current time, \(n+1\) = next time. Rearranging gives the companion (Norton equivalent) model:

\[
I_L^{n+1} = G_{\text{eq}} V_L^{n+1} + I_{\text{eq}}
\]

with:

\[
G_{\text{eq}} = \frac{h}{2L}, \quad I_{\text{eq}} = I_L^n + \frac{h}{2L} V_L^n
\]

**Backward Euler Discretization:**
\[
I_L^{n+1} = I_L^n + \frac{h}{L} V_L^{n+1}
\]
giving:
\[
G_{\text{eq}} = \frac{h}{L}, \quad I_{\text{eq}} = I_L^n
\]

**Coupled Inductors with Trapezoidal Rule:**
For two coupled inductors, the discretized system is:

\[
\begin{bmatrix}
I_1^{n+1} \\
I_2^{n+1}
\end{bmatrix}
=
\begin{bmatrix}
I_1^n \\
I_2^n
\end{bmatrix}
+
\frac{h}{2}
\begin{bmatrix}
L_1 & M \\
M & L_2
\end{bmatrix}^{-1}
\left(
\begin{bmatrix}
V_1^n \\
V_2^n
\end{bmatrix}
+
\begin{bmatrix}
V_1^{n+1} \\
V_2^{n+1}
\end{bmatrix}
\right)
\]

The inverse inductance matrix is:

\[
\begin{bmatrix}
L_1 & M \\
M & L_2
\end{bmatrix}^{-1}
=
\frac{1}{L_1 L_2 - M^2}
\begin{bmatrix}
L_2 & -M \\
-M & L_1
\end{bmatrix}
\]

The companion model becomes:

\[
\begin{bmatrix}
I_1^{n+1} \\
I_2^{n+1}
\end{bmatrix}
=
\mathbf{G}_{\text{eq}}
\begin{bmatrix}
V_1^{n+1} \\
V_2^{n+1}
\end{bmatrix}
+
\begin{bmatrix}
I_{\text{eq},1} \\
I_{\text{eq},2}
\end{bmatrix}
\]

where:

\[
\mathbf{G}_{\text{eq}} = \frac{h}{2(L_1 L_2 - M^2)}
\begin{bmatrix}
L_2 & -M \\
-M & L_1
\end{bmatrix},
\quad
\begin{bmatrix}
I_{\text{eq},1} \\
I_{\text{eq},2}
\end{bmatrix}
=
\begin{bmatrix}
I_1^n \\
I_2^n
\end{bmatrix}
+
\mathbf{G}_{\text{eq}}
\begin{bmatrix}
V_1^n \\
V_2^n
\end{bmatrix}
\]

### 2.5 Pole-Zero Analysis Formulation

For pole-zero analysis, the complex frequency variable \(s = \sigma + j\omega\) replaces \(j\omega\). The inductor impedance becomes \(Z(s) = sL = (\sigma + j\omega)L\). The MNA stamps are identical to AC analysis but with complex matrix entries:

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

For mutual inductors, the cross-coupling term is \(-sM = -(\sigma + j\omega)M\).

### 2.6 Flux as State Variable

The magnetic flux \(\phi = LI\) serves as the fundamental state variable stored in SPICE's state vector. The voltage-flux relationship is:

\[
V(t) = \frac{d\phi}{dt}
\]

For numerical integration, flux is updated using the trapezoidal rule:

\[
\phi^{n+1} = \phi^n + \frac{h}{2}\left(V^n + V^{n+1}\right)
\]

The current is then recovered as \(I = \phi/L\). This flux-based formulation ensures charge conservation and facilitates Local Truncation Error (LTE) estimation.

## 3. Convergence Analysis

### 3.1 Local Truncation Error (LTE) Estimation and Time-Step Control

The LTE for inductors provides the basis for adaptive time-step control in transient analysis. Two complementary LTE estimates are used: flux-based and current-based.

**Flux-Based LTE Estimation:**
For an inductor, the flux \(\phi(t) = LI(t)\) is the integrated quantity. Using polynomial extrapolation (Backward Difference Formula) of order \(p\):

\[
\phi_{\text{pred}}^{n+1} = \sum_{i=0}^{p} a_i \phi^{n-i}
\]

where \(a_i\) are BDF coefficients dependent on the integration order and recent time steps. The LTE in flux is:

\[
\text{LTE}_\phi = |\phi^{n+1} - \phi_{\text{pred}}^{n+1}|
\]

The normalized error used for time-step control is:

\[
\text{error}_\phi = \frac{\text{LTE}_\phi}{|\phi| + \epsilon_\phi}
\]

where \(\epsilon_\phi\) is an absolute flux tolerance, typically \(\epsilon_\phi = \text{ABSTOL} \cdot L\).

**Current-Based LTE Estimation:**
From the Taylor expansion of current:

\[
I(t_{n+1}) = I(t_n) + h\frac{dI}{dt}\Big|_{t_n} + \frac{h^2}{2}\frac{d^2I}{dt^2}\Big|_{t_n} + O(h^3)
\]

For trapezoidal integration, the dominant error term is:

\[
\text{LTE}_I \approx \frac{h^3}{12} \frac{d^3I}{dt^3}
\]

Since \(dI/dt = V/L\), this can be estimated as:

\[
\text{LTE}_I \approx \frac{h^3}{12L} \frac{d^2V}{dt^2} \approx \frac{h^3}{12L} \frac{V^n - 2V^{n-1} + V^{n-2}}{h^2} = \frac{h}{12L} (V^n - 2V^{n-1} + V^{n-2})
\]

**Time-Step Adjustment:**
If the normalized error exceeds the tolerance \(\text{TOL} = \text{RELTOL} \cdot \text{TRTOL} + \text{ABSTOL}\), the time step is reduced:

\[
h_{\text{new}} = h_{\text{old}} \cdot \sqrt{\frac{\text{TOL}}{\text{error}}}
\]

The square root arises because the LTE for trapezoidal rule is \(O(h^3)\), so error \(\propto h^3\), and thus \(h \propto \sqrt[3]{\text{error}} \approx \sqrt{\text{error}}\) for small adjustments.

### 3.2 Newton-Raphson Convergence for Nonlinear Inductors

When magnetic core saturation is modeled (inductance \(L\) becomes current-dependent), the equations become nonlinear. The Newton-Raphson iteration requires the Jacobian entries.

For a nonlinear inductor \(I = f(\phi)\) where \(\phi = \int V dt\), the companion model for trapezoidal rule is:

\[
I^{n+1} = f\left(\phi^n + \frac{h}{2}(V^n + V^{n+1})\right)
\]

The Jacobian contribution to the MNA matrix is:

\[
\frac{\partial I^{n+1}}{\partial V^{n+1}} = \frac{h}{2} f'(\phi^{n+1})
\]

where \(f'(\phi) = dI/d\phi = 1/L(I)\) is the differential inductance.

The convergence criterion for the branch current is:

\[
|I^{(k+1)} - I^{(k)}| < \text{RELTOL} \cdot \max(|I^{(k+1)}|, |I^{(k)}|) + \text{ABSTOL}
\]

where \(k\) is the Newton iteration index, \(\text{RELTOL} \approx 10^{-3}\), and \(\text{ABSTOL} \approx 10^{-12}\) A.

### 3.3 Matrix Conditioning and Numerical Stability

**Ill-Conditioning at Low Frequency:**
In AC analysis, as \(\omega \to 0\), the inductor branch equation becomes \(V_p - V_n \approx 0\), making the matrix nearly singular. The condition number of the inductor block is:

\[
\kappa \approx \frac{\max(\text{diag}(\mathbf{G}))}{\omega L}
\]

Ngspice mitigates this by adding a small conductance \(G_{\min}\) (typically \(10^{-12}\) S) in parallel, effectively replacing \(-j\omega L\) with \(-j\omega L + G_{\min}\) in the matrix.

**Ill-Conditioning from Tight Coupling:**
For mutual inductors with \(|k| \to 1\), the inductance matrix becomes near-singular since \(L_1 L_2 - M^2 = L_1 L_2(1 - k^2) \to 0\). The condition number of the coupled block is:

\[
\kappa \approx \frac{1 + |k|}{1 - |k|}
\]

For \(k = 0.999\), \(\kappa \approx 2000\). Ngspice handles this by:
1. Clamping \(k\) to a maximum such as 0.9999
2. Using double precision arithmetic
3. Employing partial pivoting in LU factorization

**Time-Step Related Conditioning:**
In transient analysis, the companion conductance \(G_{\text{eq}} = h/(2L)\) can become very large for small \(L\) or small \(h\), potentially causing ill-conditioning. The condition number contribution is:

\[
\kappa_{\text{ind}} \approx \frac{G_{\text{eq}}}{G_{\min}} = \frac{h}{2L G_{\min}}
\]

A minimum time step \(h_{\min}\) (e.g., \(10^{-15}\) s) is enforced to prevent excessive \(G_{\text{eq}}\).

### 3.4 Energy Conservation Validation

For lossless linear inductors with trapezoidal integration, the numerical scheme should conserve energy exactly. The magnetic energy is:

\[
W_m = \frac{1}{2} LI^2 = \frac{\phi^2}{2L}
\]

The change in energy from step \(n\) to \(n+1\) should equal the electrical work done:

\[
\Delta W_m = W_m^{n+1} - W_m^n = \int_{t_n}^{t_{n+1}} V(t)I(t) dt \approx \frac{h}{2}(V^n I^n + V^{n+1} I^{n+1})
\]

The relative energy error:

\[
\epsilon_{\text{energy}} = \frac{|\Delta W_m - W_{\text{elec}}|}{|\Delta W_m|}
\]

should be near machine precision (\(\sim 10^{-15}\)) for correct implementation. Large \(\epsilon_{\text{energy}}\) indicates numerical issues with the integration or matrix solution.

### 3.5 Coupled System Stability Analysis

For two coupled inductors, the numerical stability depends on the eigenvalues of the amplification matrix derived from the discretization. Applying trapezoidal rule to the coupled system:

\[
\frac{d}{dt}\begin{bmatrix} I_1 \\ I_2 \end{bmatrix} = 
\begin{bmatrix} L_1 & M \\ M & L_2 \end{bmatrix}^{-1}
\begin{bmatrix} V_1 \\ V_2 \end{bmatrix}
\]

The eigenvalues \(\lambda_{1,2}\) of \(\mathbf{L}^{-1}\) are:

\[
\lambda_{1,2} = \frac{L_1 + L_2 \pm \sqrt{(L_1 - L_2)^2 + 4M^2}}{2(L_1 L_2 - M^2)}
\]

Trapezoidal rule is A-stable, so the numerical solution remains stable for any \(h > 0\) provided the real parts of \(h\lambda_i\) are in the left-half plane (always true for positive definite \(\mathbf{L}\)). However, for very large \(|\lambda_i|\) (near-singular \(\mathbf{L}\)), the solution can exhibit numerical oscillation if \(h\) is too large relative to \(1/|\lambda_i|\).

### 3.6 DC Convergence with Initial Conditions

When an initial current \(I(0) = I_0\) is specified via the `IC` parameter, the DC operating point solution must satisfy this constraint. Ngspice enforces this by adding a large conductance \(G_{\text{ic}}\) (typically \(10^{12}\) S) in parallel with a current source \(I_0\) during the DC phase:

\[
I_{\text{stamp}} = G_{\text{ic}}(V_p - V_n) - I_0
\]

This effectively forces \(V_p - V_n \approx I_0/G_{\text{ic}} \approx 0\) (short circuit) with current \(I_0\). Convergence requires:

\[
|G_{\text{ic}}(V_p - V_n) - I_0| < \text{ABSTOL}
\]

### 3.7 AC Analysis Convergence at Extreme Frequencies

**Low Frequency (\(\omega \to 0\)):**
As mentioned, matrix ill-conditioning occurs. Ngspice switches to DC analysis for \(\omega < \omega_{\min}\) (typically \(2\pi \times 10^{-10}\) rad/s).

**High Frequency (\(\omega \to \infty\)):**
The inductor becomes an open circuit (\(Z \to \infty\)). The branch equation dominates with large diagonal entry \(-j\omega L\). Convergence of the linear solver (typically LU with partial pivoting) is monitored via the residual:

\[
\|\mathbf{Ax} - \mathbf{b}\|_2 < \epsilon_{\text{machine}} \cdot \|\mathbf{A}\|_F \cdot \|\mathbf{x}\|_2
\]

where \(\mathbf{A}\) is the complex MNA matrix and \(\|\cdot\|_F\) is the Frobenius norm. Iterative refinement is applied if the residual exceeds tolerance.

### 3.8 Mutual Inductor Reciprocity Validation

For linear mutual inductors, reciprocity requires \(M_{12} = M_{21}\). In the implementation, this is validated by checking symmetry of the stamped matrix entries. The symmetry error is computed as:

\[
\epsilon_{\text{sym}} = \max(|Z_{12} - Z_{21}|, |Z_{21} - Z_{12}|)
\]

where \(Z_{12}\) and \(Z_{21}\) are the cross-coupling matrix entries. A warning is issued if \(\epsilon_{\text{sym}} > 10^{-10} \cdot \max(|Z_{12}|, |Z_{21}|)\).

### 3.9 Time-Step Control in Coupled Systems

For coupled inductors, the LTE estimation must account for coupling. The flux vector \(\boldsymbol{\phi} = \mathbf{LI}\) is used, where \(\mathbf{L}\) is the inductance matrix. The predicted flux is:

\[
\boldsymbol{\phi}_{\text{pred}}^{n+1} = \sum_{i=0}^{p} a_i \boldsymbol{\phi}^{n-i}
\]

The LTE vector is \(\boldsymbol{\epsilon}_\phi = \boldsymbol{\phi}^{n+1} - \boldsymbol{\phi}_{\text{pred}}^{n+1}\). The normalized error for time-step control is:

\[
\text{error} = \max_i \frac{|[\boldsymbol{\epsilon}_\phi]_i|}{|[\boldsymbol{\phi}]_i| + \epsilon_{\phi,i}}
\]

where \(\epsilon_{\phi,i}\) are absolute tolerances for each flux component.

### 3.10 Damping of Numerical Oscillations

LC circuits can produce high-frequency numerical oscillations with trapezoidal rule, which is non-dissipative. Gear integration methods (order > 1) provide numerical damping. The effective damping ratio for Gear-2 is approximately:

\[
\zeta_{\text{num}} \approx \frac{1}{2}\left(1 - \frac{h}{h_{\text{crit}}}\right)
\]

where \(h_{\text{crit}} = 2/\omega_0\) and \(\omega_0 = 1/\sqrt{LC}\) is the natural frequency. This damping helps convergence in oscillatory circuits but can artificially suppress legitimate high-frequency responses.

This mathematical formulation and convergence analysis directly underpins the Ngspice C implementation, ensuring numerically robust simulation of inductive elements within the SPICE framework while maintaining physical accuracy and computational efficiency.

## 4. C Implementation

This section details the Ngspice C implementation for inductor and mutual inductor models, explicitly mapping the mathematical formulations for AC analysis and transient time-stepping to the specific data structures, functions, and matrix operations found in the source code. The implementation handles the fundamental challenge of inductors in Modified Nodal Analysis (MNA)—their constitutive relation is differential (\(V = L \frac{dI}{dt}\))—by introducing branch current variables and employing numerical integration to create discrete-time companion models.

### 4.1 Core Data Structures for MNA Branch Formulation

The implementation is built upon two primary data structures defined in `inddefs.h` and `mutdefs.h`. These structures manage the device parameters, state variables, and, critically, the sparse matrix pointers required for the expanded MNA system.

#### 4.1.1 Independent Inductor Instance (`INDinstance`)

```c
typedef struct sINDinstance {
    char *INDname;              /* Instance name */
    int INDposNode;             /* Positive terminal node */
    int INDnegNode;             /* Negative terminal node */
    int INDbranch;              /* Branch equation index (MNA) */
    double INDinduct;           /* Nominal inductance L */
    double INDic;               /* Initial current IC= */
    double INDflux;             /* Magnetic flux (state variable) */
    double INDcurrent;          /* Current through inductor */
    double *INDposPosPtr;       /* SMP pointer: G[pos][pos] */
    double *INDposNegPtr;       /* SMP pointer: G[pos][neg] */
    double *INDposBrPtr;        /* SMP pointer: G[pos][branch] */
    double *INDnegPosPtr;       /* SMP pointer: G[neg][pos] */
    double *INDnegNegPtr;       /* SMP pointer: G[neg][neg] */
    double *INDnegBrPtr;        /* SMP pointer: G[neg][branch] */
    double *INDbrPosPtr;        /* SMP pointer: G[branch][pos] */
    double *INDbrNegPtr;        /* SMP pointer: G[branch][neg] */
    double *INDbrBrPtr;         /* SMP pointer: G[branch][branch] */
    int INDstate;               /* State vector index for flux */
    /* ... temperature and link fields ... */
} INDinstance;
```

**Mathematical Mapping:** This structure encapsulates the physics and numerics of a single inductor. The field `INDbranch` holds the index for the extra MNA variable \(I_L\), the branch current. The nine `double*` matrix pointers (`INDposPosPtr`, `INDposBrPtr`, etc.) are pre-allocated during setup to point to specific locations in the sparse MNA matrix, corresponding to the 3x3 block for nodes `pos`, `neg`, and the branch variable `branch`. The `INDstate` index provides access to the flux history \(\phi = L \cdot I\) stored in the global `CKTstates` vector for Local Truncation Error (LTE) calculation.

#### 4.1.2 Mutual Inductor Instance (`MUTinstance`)

```c
typedef struct sMUTinstance {
    char *MUTname;              /* Instance name */
    INDinstance *MUTind1;       /* Pointer to first inductor */
    INDinstance *MUTind2;       /* Pointer to second inductor */
    double MUTcoupling;         /* Coupling coefficient k */
    double MUTfactor;           /* k * sqrt(L1*L2) = M */
    double *MUTbr1br2Ptr;       /* SMP pointer: G[branch1][branch2] */
    double *MUTbr2br1Ptr;       /* SMP pointer: G[branch2][branch1] */
    /* ... temperature and link fields ... */
} MUTinstance;
```

**Mathematical Mapping:** This structure defines the magnetic coupling between two `INDinstance` objects. It stores the coupling coefficient \(k\) and the computed mutual inductance \(M = k \sqrt{L_1 L_2}\) in `MUTfactor`. The key implementation detail is the pair of matrix pointers `MUTbr1br2Ptr` and `MUTbr2br1Ptr`. These are allocated to point to the off-diagonal positions linking the two branch current rows/columns in the MNA matrix, enabling the stamping of the cross-coupling terms \(j\omega M\) (AC) or \(h/(2M)\) (transient).

### 4.2 AC and Pole-Zero Analysis Implementation

Frequency-domain analysis requires stamping complex impedance terms into the MNA matrix. The functions `INDacLoad`, `MUTacLoad`, `INDpzLoad`, and `MUTpzLoad` implement this.

#### 4.2.1 AC Analysis for Independent Inductor (`indacld.c`)

The function `INDacLoad` stamps the complex admittance for an inductor at angular frequency \(\omega\).

```c
int INDacLoad(GENmodel *inModel, CKTcircuit *ckt) {
    /* ... */
    omega = ckt->CKTomega;
    for(/* each instance */) {
        /* Branch equation: V_pos - V_neg - jωL·I_branch = 0 */
        *(here->INDbrPosPtr) += 1.0;             /* ∂/∂V_pos = 1 */
        *(here->INDbrPosPtr + 1) += 0.0;         /* (imag part) */
        *(here->INDbrNegPtr) += -1.0;            /* ∂/∂V_neg = -1 */
        *(here->INDbrNegPtr + 1) += 0.0;
        *(here->INDbrBrPtr) += 0.0;              /* ∂/∂I_branch (real) */
        *(here->INDbrBrPtr + 1) += -omega * here->INDinduct; /* -jωL */

        /* Current injection from branch to nodes */
        *(here->INDposBrPtr) += 1.0;             /* I_branch into pos node */
        *(here->INDnegBrPtr) += -1.0;            /* -I_branch into neg node */
    }
}
```

**Mathematical Mapping:** This code directly builds the 3x3 MNA block for the branch formulation:
\[
\begin{bmatrix}
0 & 0 & 1 \\
0 & 0 & -1 \\
1 & -1 & -j\omega L
\end{bmatrix}
\begin{bmatrix}
V_+ \\ V_- \\ I_L
\end{bmatrix}
=
\begin{bmatrix}
I_{\text{ext},+} \\ I_{\text{ext},-} \\ 0
\end{bmatrix}
\]
The pointers `INDbrPosPtr` and `INDbrNegPtr` stamp the `+1` and `-1` in the third row (branch equation). `INDbrBrPtr` stamps the complex impedance \(-j\omega L\). `INDposBrPtr` and `INDnegBrPtr` stamp the `+1` and `-1` in the first and second rows, enforcing KCL: the branch current \(I_L\) flows out of the positive node and into the negative node.

#### 4.2.2 AC Analysis for Mutual Inductor (`mutacld.c`)

The function `MUTacLoad` stamps the cross-coupling terms between two coupled inductors.

```c
int MUTacLoad(GENmodel *inModel, CKTcircuit *ckt) {
    /* ... */
    for(/* each MUTinstance */) {
        /* Calculate M = k * sqrt(L1 * L2) */
        here->MUTfactor = k * sqrt(L1 * L2);
        M_val = here->MUTfactor;
        imag_part = -omega * M_val; /* -jωM */

        /* Stamp mutual impedance between branch equations */
        if(here->MUTbr1br2Ptr) {
            *(here->MUTbr1br2Ptr) += 0.0;        /* Real part */
            *(here->MUTbr1br2Ptr + 1) += imag_part; /* Imag part: -jωM */
        }
        /* ... same for MUTbr2br1Ptr ... */
    }
}
```

**Mathematical Mapping:** This implements the coupled branch equations:
\[
V_{1+} - V_{1-} = j\omega L_1 I_1 + j\omega M I_2
\]
\[
V_{2+} - V_{2-} = j\omega M I_1 + j\omega L_2 I_2
\]
The code stamps the term \(-j\omega M\) at the matrix positions `[branch1][branch2]` and `[branch2][branch1]`, which are the derivatives \(\partial (\text{eqn1}) / \partial I_2\) and \(\partial (\text{eqn2}) / \partial I_1\). The pointer arithmetic (`+1`) accesses the adjacent memory location storing the imaginary component of the complex matrix.

#### 4.2.3 Pole-Zero Analysis Loading

Pole-zero analysis uses the complex frequency variable \(s = \sigma + j\omega\). The functions `INDpzLoad` and `MUTpzLoad` are identical to their AC counterparts but use `s->real` and `s->imag` instead of `0` and `omega`.

```c
/* In INDpzLoad */
double Z_real = s->real * here->INDinduct; /* σL */
double Z_imag = s->imag * here->INDinduct; /* ωL */
*(here->INDbrBrPtr) += Z_real;
*(here->INDbrBrPtr + 1) += Z_imag;
```
**Mathematical Mapping:** This stamps the general impedance \(Z(s) = sL = (\sigma + j\omega)L\) into the branch equation, generalizing the AC case where \(\sigma = 0\).

### 4.3 Transient Time-Stepping and Companion Model

Transient analysis discretizes the differential equation using numerical integration (Trapezoidal or Backward Euler). The functions `INDload` and `MUTload` construct and stamp the resulting discrete-time companion model.

#### 4.3.1 Independent Inductor Companion Model (`INDload`)

The core of transient analysis is the derivation of a Norton equivalent companion model: \(I^{n+1} = G_{eq} V^{n+1} + I_{eq}\).

```c
int INDload(GENmodel *inModel, CKTcircuit *ckt) {
    h = ckt->CKTdelta; /* Time step Δt */
    for(/* each instance */) {
        if(ckt->CKTintegrateMethod == TRAPEZOIDAL) {
            g_eq = h / (2.0 * here->INDinduct);    /* G_eq = Δt/(2L) */
            i_eq = here->INDcurrent + g_eq * (V_old);
        } else { /* Backward Euler */
            g_eq = h / here->INDinduct;            /* G_eq = Δt/L */
            i_eq = here->INDcurrent;
        }
        /* Stamp Norton equivalent into the conductance matrix */
        *(here->INDposPosPtr) += g_eq;
        *(here->INDposNegPtr) -= g_eq;
        *(here->INDnegPosPtr) -= g_eq;
        *(here->INDnegNegPtr) += g_eq;
        /* Stamp history current into RHS vector */
        ckt->CKTrhs[here->INDposNode] -= i_eq;
        ckt->CKTrhs[here->INDnegNode] += i_eq;
    }
}
```

**Mathematical Mapping:** This code implements the discretized integration formula. For the Trapezoidal rule:
\[
I^{n+1} = I^n + \frac{\Delta t}{2L} (V^n + V^{n+1}) = \underbrace{\frac{\Delta t}{2L}}_{G_{eq}} V^{n+1} + \underbrace{I^n + \frac{\Delta t}{2L} V^n}_{I_{eq}}
\]
The `g_eq` and `i_eq` variables hold these computed values. The stamping pattern adds \(G_{eq}\) to the four positions of the 2x2 nodal conductance matrix (`[pos,pos]`, `[neg,neg]` as `+g_eq`; `[pos,neg]`, `[neg,pos]` as `-g_eq`), representing a resistor of value \(1/G_{eq}\). The history current `i_eq` is subtracted/added to the RHS at the positive/negative nodes, representing a parallel current source. **Crucially, this transient load function uses the standard 2x2 nodal stamp (`INDposPosPtr`, etc.), not the 3x3 branch formulation used in AC analysis.** This is because the companion model transforms the differential inductor into an algebraic resistive companion, eliminating the need for an extra branch variable during the transient Newton-Raphson iteration.

#### 4.3.2 Mutual Inductor Transient Coupling (`MUTload`)

For coupled inductors, the mutual term adds a cross-coupling conductance between the companion models of the two inductors.

```c
int MUTload(GENmodel *inModel, CKTcircuit *ckt) {
    h = ckt->CKTdelta;
    for(/* each MUTinstance */) {
        M = here->MUTfactor;
        if(ckt->CKTintegrateMethod == TRAPEZOIDAL) {
            g_mut = h / (2.0 * M); /* G_mut = Δt/(2M) */
        } else {
            g_mut = h / M;         /* G_mut = Δt/M */
        }
        /* Stamp cross-coupling conductance */
        if(here->MUTbr1br2Ptr && here->MUTbr2br1Ptr) {
            *(here->MUTbr1br2Ptr) += g_mut;
            *(here->MUTbr2br1Ptr) += g_mut;
        }
    }
}
```

**Mathematical Mapping:** The coupled trapezoidal