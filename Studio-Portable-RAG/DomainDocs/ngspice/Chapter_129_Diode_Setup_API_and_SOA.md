# Diode: Matrix Setup, API Binding, and Safe Operating Area

_Generated 2026-04-12 19:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diosetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diomask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diompar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/dioask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diogetic.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/dioinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/dio.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diodel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diomdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diodest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diosoachk.c`

# Chapter: Diode: Matrix Setup, API Binding, and Safe Operating Area

## 1. Technical Introduction

This chapter documents the Ngspice implementation of the semiconductor diode model, focusing on the core architectural components that enable circuit simulation. The implementation is distributed across eleven specialized C source files, each with a distinct role in the SPICE simulation workflow:

- **`diosetup.c`**: Allocates sparse matrix pointers for the Modified Nodal Analysis (MNA) system, establishing the diode's connectivity within the circuit matrix. This file implements the mathematical mapping from diode terminals to matrix indices, creating the infrastructure for Newton-Raphson iteration.

- **`diomask.c`**: Defines parameter masks and metadata for the diode model, enabling the SPICE parser to recognize and validate diode parameters during netlist processing. This file bridges the textual netlist representation and the internal C data structures.

- **`diompar.c`**: Implements model parameter processing, handling the diode's physical and electrical characteristics that are shared across multiple instances (saturation current, emission coefficient, breakdown voltage, etc.).

- **`dioask.c`**: Provides query functionality for accessing simulation results, allowing users to retrieve computed values (voltage, current, power, capacitance) after analysis completes.

- **`diogetic.c`**: Handles device-specific equation evaluation and internal state computation, implementing the core Shockley physics and its derivatives for different operating regions.

- **`dioinit.c`**: Registers the diode device with the Ngspice kernel through the `SPICEdev` API structure, binding the diode's mathematical functions to the simulation engine's analysis routines.

- **`dio.c`**: Contains the primary load function (`DIOload()`) that stamps the diode's conductance matrix and right-hand-side vector during Newton-Raphson iteration, implementing the linearized companion model.

- **`diodel.c`**, **`diomdel.c`**, **`diodest.c`**: Manage memory lifecycle for instance and model structures, ensuring proper allocation and cleanup during simulation setup and teardown.

- **`diosoachk.c`**: Implements Safe Operating Area (SOA) verification, checking real-time simulation results against device limits (maximum voltage, current, power) to prevent unrealistic operating conditions.

Together, these files implement a complete production-grade diode model that balances mathematical accuracy from semiconductor physics with the numerical robustness required for circuit simulation. The implementation follows Ngspice's modular architecture while providing efficient matrix operations, convergence control, and physical limit checking.

## 2. Mathematical Formulation

### 2.1 Modified Nodal Analysis (MNA) Matrix Formulation for Diodes

The diode implementation in SPICE integrates into the Modified Nodal Analysis (MNA) framework through a systematic matrix stamping procedure. For a two-terminal diode between nodes `n+` (anode) and `n-` (cathode), the DC companion model contributes to the circuit Jacobian matrix `J` and right-hand side vector `F(x)`.

The diode current-voltage relationship follows the Shockley equation with series resistance:
\[
I_D = I_S \left[ \exp\left(\frac{V_J}{n V_T}\right) - 1 \right]
\]
where \( V_J = V_D - I_D R_S \) is the intrinsic junction voltage.

The linearized Norton equivalent for Newton-Raphson iteration is:
\[
I_D^{(k+1)} = g_d^{(k)} V_D^{(k+1)} + I_{eq}^{(k)}
\]
with:
\[
g_d^{(k)} = \frac{\partial I_D}{\partial V_D} = \frac{g_J}{1 + g_J R_S}, \quad g_J = \frac{I_S}{n V_T} \exp\left(\frac{V_J^{(k)}}{n V_T}\right)
\]
\[
I_{eq}^{(k)} = I_D^{(k)} - g_d^{(k)} V_D^{(k)}
\]

The MNA matrix stamp for a diode is:
\[
\begin{bmatrix}
G_{++} + g_d & G_{+-} - g_d \\
G_{-+} - g_d & G_{--} + g_d
\end{bmatrix}
\begin{bmatrix}
V_+ \\
V_-
\end{bmatrix}
=
\begin{bmatrix}
I_{+} - I_{eq} \\
I_{-} + I_{eq}
\end{bmatrix}
\]

For diodes with significant series resistance (\(R_S > 0\)), SPICE introduces an internal node `n_j` between the junction and series resistance, creating a 3×3 stamp:
\[
\begin{bmatrix}
\frac{1}{R_S} & -\frac{1}{R_S} & 0 \\
-\frac{1}{R_S} & \frac{1}{R_S} + g_J & -g_J \\
0 & -g_J & g_J
\end{bmatrix}
\begin{bmatrix}
V_+ \\
V_j \\
V_-
\end{bmatrix}
=
\begin{bmatrix}
I_{+} \\
-I_{eq} \\
I_{-} + I_{eq}
\end{bmatrix}
\]

### 2.2 Capacitance Matrix Stamping for Transient Analysis

The diode charge model includes depletion and diffusion components:
\[
Q_D = Q_j(V_J) + \tau_T I_D
\]
where:
\[
Q_j(V) = \int_{0}^{V} C_j(v) dv, \quad C_j(V) = \frac{C_{j0}}{\left(1 - \frac{V}{\phi}\right)^m}
\]

For transient analysis using trapezoidal integration with time step \(h\), the companion model becomes:
\[
I_{cap}^{(k+1)} = \frac{Q_D^{(k+1)} - Q_D^{(k)}}{h} = g_c V_D^{(k+1)} + I_{c,eq}^{(k)}
\]
with:
\[
g_c = \frac{C_j(V_J^{(k)})}{h}, \quad I_{c,eq}^{(k)} = -\frac{Q_D^{(k)}}{h} - g_c V_D^{(k)}
\]

The complete transient stamp combines conductive and capacitive terms:
\[
\begin{bmatrix}
G_{++} + g_d + g_c & G_{+-} - g_d - g_c \\
G_{-+} - g_d - g_c & G_{--} + g_d + g_c
\end{bmatrix}
\begin{bmatrix}
V_+^{(k+1)} \\
V_-^{(k+1)}
\end{bmatrix}
=
\begin{bmatrix}
I_{+} - I_{eq} - I_{c,eq} \\
I_{-} + I_{eq} + I_{c,eq}
\end{bmatrix}
\]

### 2.3 Small-Signal AC Analysis Formulation

For AC analysis at frequency \(\omega\), the diode linearizes around the DC operating point. The small-signal admittance is:
\[
y_d(\omega) = g_d + j\omega C_d
\]
where \(C_d = C_j(V_J) + \tau_T g_d\) is the total small-signal capacitance.

The AC matrix stamp uses complex arithmetic:
\[
\begin{bmatrix}
Y_{++} + y_d & Y_{+-} - y_d \\
Y_{-+} - y_d & Y_{--} + y_d
\end{bmatrix}
\begin{bmatrix}
\tilde{V}_+ \\
\tilde{V}_-
\end{bmatrix}
=
\begin{bmatrix}
\tilde{I}_{+} \\
\tilde{I}_{-}
\end{bmatrix}
\]

### 2.4 Breakdown Region Mathematical Treatment

For reverse bias beyond breakdown voltage \(BV\), the multiplication factor introduces additional current:
\[
I_{br} = I_S \left[ \exp\left(\frac{-V_D}{n V_T}\right) - 1 \right] \times M(V_D)
\]
\[
M(V_D) = \frac{1}{1 - \left(\frac{V_D}{BV}\right)^m} \quad \text{for } V_D < 0
\]

The breakdown conductance for the Jacobian is:
\[
g_{br} = \frac{\partial I_{br}}{\partial V_D} = \frac{I_S}{n V_T} \exp\left(\frac{-V_D}{n V_T}\right) M(V_D) + I_{br} \frac{m V_D^{m-1}}{BV^m - V_D^m}
\]

Numerical regularization prevents singularity at \(V_D = -BV\):
\[
M_{\text{reg}}(V_D) = \frac{1}{\max\left(1 - \left(\frac{V_D}{BV}\right)^m, \epsilon\right)}, \quad \epsilon \approx 10^{-6}
\]

### 2.5 Temperature-Dependent Parameter Scaling

Key parameters scale with temperature \(T\) relative to nominal \(T_{\text{nom}}\):
\[
I_S(T) = I_S(T_{\text{nom}}) \left(\frac{T}{T_{\text{nom}}}\right)^{X_{TI}} \exp\left[ \frac{E_g(T_{\text{nom}})}{k T_{\text{nom}}} - \frac{E_g(T)}{k T} \right]
\]
\[
\phi(T) = \phi(T_{\text{nom}}) \frac{T}{T_{\text{nom}}} - \frac{3k T}{q} \ln\left(\frac{T}{T_{\text{nom}}}\right) - \frac{E_g(T_{\text{nom}}) T}{T_{\text{nom}}} + E_g(T)
\]
\[
V_T(T) = \frac{kT}{q}, \quad E_g(T) = 1.16 - \frac{7.02 \times 10^{-4} T^2}{T + 1108}
\]

The temperature derivatives required for sensitivity analysis are:
\[
\frac{\partial I_S}{\partial T} = I_S \left[ \frac{X_{TI}}{T} + \frac{E_g(T)}{k T^2} - \frac{1}{T} \frac{dE_g}{dT} \right]
\]
\[
\frac{dE_g}{dT} = -1.404 \times 10^{-3} T \frac{T + 2216}{(T + 1108)^2}
\]

### 2.6 Noise Analysis Formulation

The diode contributes two noise sources to the circuit:
1. **Shot noise**: \(S_I(f) = 2q I_D\)
2. **Flicker noise**: \(S_I(f) = \frac{K_F I_D^{A_F}}{f}\)

The noise current correlation matrix for the two-terminal diode is:
\[
C_n = 
\begin{bmatrix}
S_I & -S_I \\
-S_I & S_I
\end{bmatrix}
\]

In the frequency domain, the noise contribution to the system is:
\[
\langle \tilde{V}_n \tilde{V}_n^* \rangle = Z C_n Z^H
\]
where \(Z\) is the impedance matrix from the diode terminals to all circuit nodes.

### 2.7 Safe Operating Area (SOA) Mathematical Boundaries

The diode SOA is defined by four constraints:

1. **Maximum forward current**:
   \[
   I_D \leq I_{\text{max}}
   \]

2. **Maximum reverse voltage**:
   \[
   |V_D| \leq V_{\text{max}}
   \]

3. **Maximum power dissipation**:
   \[
   P_D = I_D V_D \leq P_{\text{max}} \quad \text{(forward bias)}
   \]
   \[
   P_D = |I_D V_D| \leq P_{\text{rev,max}} \quad \text{(reverse bias)}
   \]

4. **Second breakdown limit**:
   \[
   \text{If } |V_D| > V_{\text{SB}} \text{ and } |I_D| > I_{\text{SB}}, \text{ device in second breakdown}
   \]

These constraints form a convex region in the \(I_D\)-\(V_D\) plane that must be checked at each simulation step.

## 3. Convergence Analysis

### 3.1 Newton-Raphson Convergence for Exponential Nonlinearity

The diode's exponential I-V characteristic presents the most severe convergence challenge in SPICE. The Newton-Raphson update equation is:
\[
V_D^{(k+1)} = V_D^{(k)} - \frac{I_D(V_D^{(k)}) - I_{\text{target}}}{g_d(V_D^{(k)})}
\]

The convergence rate depends critically on the initial guess \(V_D^{(0)}\). For forward bias solutions, if \(V_D^{(0)} \ll V_D^{\text{actual}}\), then \(g_d \approx 0\), causing:
\[
|\Delta V_D| = \left| \frac{I_D}{g_d} \right| \approx \frac{I_S \exp(V_D/(nV_T))}{(I_S/(nV_T)) \exp(V_D/(nV_T))} = nV_T
\]
This gives a maximum sensible step of approximately \(2nV_T \approx 50-100\text{mV}\).

SPICE implements voltage limiting via the `DEVpnjlim()` function:
\[
V_D^{\text{limited}} = V_D^{(k)} + \delta (V_D^{(k+1)} - V_D^{(k)})
\]
where:
\[
\delta = \min\left(1, \frac{V_{\text{max}}}{|V_D^{(k+1)} - V_D^{(k)}|}\right), \quad V_{\text{max}} = 2nV_T
\]

The convergence test for diodes uses both voltage and current criteria:
\[
|V_D^{(k+1)} - V_D^{(k)}| < \epsilon_V = \text{RELTOL} \cdot \max(|V_D^{(k+1)}|, \text{VNTOL}) + \text{ABSTOL}
\]
\[
|I_D^{(k+1)} - I_D^{(k)}| < \epsilon_I = \text{RELTOL} \cdot \max(|I_D^{(k+1)}|, \text{ABSTOL})
\]

### 3.2 Numerical Conditioning and Regularization

The diode conductance spans extreme ranges:
- Reverse bias (\(V_D = -5V\)): \(g_d \approx I_S/(nV_T) \sim 10^{-12}\ \text{S}\)
- Forward bias (\(V_D = 0.7V\)): \(g_d \approx (I_S/(nV_T)) e^{27} \sim 1\ \text{S}\)

This \(10^{12}\) range can cause ill-conditioning in the MNA matrix. The condition number contribution from a diode is:
\[
\kappa_{\text{diode}} \approx \frac{\max(g_d, G_{\text{min}})}{\min(g_d, G_{\text{min}})}
\]
where \(G_{\text{min}} = 10^{-12}\ \text{S}\) is SPICE's minimum conductance.

SPICE employs three regularization techniques:
1. **Parallel conductance**: \(g_d' = g_d + G_{\text{min}}\)
2. **Pivot selection**: LU decomposition with partial pivoting
3. **Breakdown regularization**: \(M(V_D) = 1/\max(1 - (V_D/BV)^m, 10^{-6})\)

### 3.3 Series Resistance Convergence Analysis

When \(R_S\) is large, the equation \(V_J = V_D - I_D R_S\) creates a stiff system. The effective conductance seen from terminals is:
\[
g_d^{\text{eff}} = \frac{g_J}{1 + g_J R_S}
\]

Two regimes exist:
1. **Low injection** (\(g_J R_S \ll 1\)): \(g_d^{\text{eff}} \approx g_J\), diode-controlled
2. **High injection** (\(g_J R_S \gg 1\)): \(g_d^{\text{eff}} \approx 1/R_S\), resistance-controlled

The convergence damping factor for large \(g_J R_S\) is:
\[
\beta = \min\left(1, \frac{10}{g_J R_S}\right)
\]
\[
V_D^{(k+1)} = V_D^{(k)} + \beta \Delta V_D
\]

### 3.4 Charge Conservation and LTE Control

For transient analysis, the local truncation error (LTE) for diode charge is:
\[
\epsilon_Q = \frac{h^2}{12} \left| \frac{d^2 Q_D}{dt^2} \right|
\]

Expanding the second derivative:
\[
\frac{d^2 Q_D}{dt^2} = C_j \frac{d^2 V_D}{dt^2} + \frac{dC_j}{dV_D} \left(\frac{dV_D}{dt}\right)^2 + \tau_T \frac{d^2 I_D}{dt^2}
\]

The time step control algorithm uses:
\[
h_{\text{new}} = 0.9 h_{\text{old}} \sqrt{\frac{\epsilon_{\text{tol}}}{\epsilon_Q}}
\]
where \(\epsilon_{\text{tol}} = \text{RELTOL} \cdot |Q_D| + \text{CHGTOL}\).

The charge-based formulation ensures conservation:
\[
I_{cap} = \frac{Q_D^{(k+1)} - Q_D^{(k)}}{h}
\]
This avoids errors from capacitance discontinuities at \(V_D = FC \cdot \phi\).

### 3.5 Breakdown Region Convergence

Near the breakdown voltage, the multiplication factor derivative becomes large:
\[
\frac{\partial M}{\partial V_D} = \frac{m V_D^{m-1}}{BV^m} \frac{M^2(V_D)}{}
\]

At \(V_D = -0.99 BV\), for \(m = 3\):
\[
\frac{\partial M}{\partial V_D} \approx \frac{3(0.99BV)^2}{BV^3} \frac{100^2}{} \approx \frac{300}{BV}
\]

SPICE implements derivative limiting:
\[
g_{br}^{\text{limited}} = \text{sign}(g_{br}) \cdot \min(|g_{br}|, g_{\text{max}})
\]
where \(g_{\text{max}} = 10^3 / R_S\) prevents excessive Jacobian entries.

### 3.6 Temperature Sweep Convergence

During temperature analysis, parameters change exponentially with \(T\). The continuation method uses:
\[
P(T + \Delta T) = P(T) \exp\left[\frac{\partial \ln P}{\partial T} \Delta T\right]
\]

The temperature derivative of diode current is:
\[
\frac{\partial I_D}{\partial T} = I_D \left[ \frac{X_{TI}}{T} + \frac{V_D - E_g/q}{n k T^2} + \frac{1}{I_D} \frac{\partial I_D}{\partial V_D} \frac{\partial V_D}{\partial T} \right]
\]

The adaptive temperature step control is:
\[
\Delta T_{\text{new}} = \Delta T_{\text{old}} \cdot \min\left(2.0, \frac{N_{\text{ideal}}}{N_{\text{actual}}}\right)
\]
where \(N_{\text{ideal}} = 3\) and \(N_{\text{actual}}\) is the Newton iteration count.

### 3.7 Statistical Analysis Convergence

For Monte Carlo analysis with parameter variations \(\Delta p\), the worst-case convergence occurs when multiple parameters vary. The initial guess adjustment is:
\[
V_D^{(0)} = V_D^{\text{nominal}} + \sum_i \frac{\partial V_D}{\partial p_i} \Delta p_i
\]

The convergence acceleration uses:
\[
\Delta V_D^{(k+1)} = \omega \Delta V_D^{(k)} + (1-\omega) \Delta V_D^{\text{NR}}
\]
with \(\omega = 0.7\) for statistical runs.

### 3.8 DC Sweep Convergence

For voltage/current sweeps, the predictor-corrector method improves convergence:
\[
V_D^{\text{predict}}(V_{\text{sweep}} + \Delta V) = V_D(V_{\text{sweep}}) + \frac{\partial V_D}{\partial V_{\text{sweep}}} \Delta V
\]

The step size control is:
\[
\Delta V_{\text{next}} = \Delta V_{\text{current}} \times 
\begin{cases}
2.0 & \text{if } N_{\text{iter}} \leq 2 \\
1.0 & \text{if } 3 \leq N_{\text{iter}} \leq 5 \\
0.5 & \text{if } N_{\text{iter}} \geq 6
\end{cases}
\]

### 3.9 Validation of Converged Solution

After convergence, SPICE validates the diode solution by checking:

1. **KCL satisfaction**:
   \[
   \left| \sum I_{\text{into node}} \right| < \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \cdot \max|I_{\text{branch}}|
   \]

2. **Operating region consistency**:
   - Forward bias: \(V_J > -5nV_T\)
   - Reverse bias: \(V_J < 0\)
   - Breakdown: \(V_D < -0.9 BV\)

3. **Energy conservation** (transient):
   \[
   \left| \int_{t_1}^{t_2} V_D I_D dt - \Delta E_{\text{storage}} \right| < \epsilon_E
   \]
   where \(\Delta E_{\text{storage}} = \int_{Q_1}^{Q_2} V_D dQ_D\)

### 3.10 Convergence Failure Recovery

When convergence fails, SPICE employs recovery strategies:

1. **Step reduction**: \(h_{\text{new}} = 0.5 h_{\text{old}}\)
2. **Gmin stepping**: Increase \(G_{\text{min}}\) from \(10^{-12}\) to \(10^{-3}\) S, then ramp down
3. **Source stepping**: Ramp independent sources from 0% to 100%
4. **Pseudotransient**: Add fictitious capacitance \(C_{\text{pt}} = 10^{-12}\) F across diode

The convergence history is tracked:
\[
\text{If } |\Delta V_D^{(k)}| > |\Delta V_D^{(k-1)}| \text{ for 3 iterations, trigger recovery}
\]

This comprehensive convergence analysis ensures robust simulation of diode circuits across all operating regions, temperatures, and analysis types while maintaining numerical stability and physical accuracy.

## 4. C Implementation

This section details the Ngspice C implementation for the diode model, focusing on matrix setup, API binding, and Safe Operating Area (SOA) checking. The implementation follows the unified SPICE device architecture pattern, mapping the mathematical formulations from Section 3 directly to structured C code.

### 4.1 Core Data Structures and API Binding

#### 4.1.1 Diode Instance and Model Structures

Based on the SPICEdev binding template, the diode implementation uses two primary structures:

```c
/* Hypothetical diode instance structure (patterned after MOS1instance) */
typedef struct sDIOinstance {
    /* Node connections */
    int DIOposNode;          /* Anode node index */
    int DIOnegNode;          /* Cathode node index */
    
    /* Model parameters */
    double DIOarea;          /* Area scaling factor */
    double DIOpj;            /* Perimeter junction */
    double DIOtemp;          /* Instance temperature */
    
    /* State variables */
    double DIOvoltage;       /* V_d = V_anode - V_cathode */
    double DIOcurrent;       /* I_d */
    double DIOconduct;       /* g_d = ∂I_d/∂V_d */
    double DIOcap;           /* Junction capacitance */
    double DIOcharge;        /* Stored charge */
    
    /* Matrix pointers (SMP allocation) */
    double *DIOposPosPtr;    /* G_aa */
    double *DIOposNegPtr;    /* G_ac */
    double *DIOnegPosPtr;    /* G_ca */
    double *DIOnegNegPtr;    /* G_cc */
    
    /* Breakdown and SOA fields */
    double DIObv;            /* Breakdown voltage */
    double DIOibv;           /* Breakdown current */
    double DIOpower;         /* Instantaneous power */
    double DIOmaxPower;      /* Maximum power rating */
    
    struct sDIOinstance *DIOnextInstance;
} DIOinstance;

/* Hypothetical diode model structure */
typedef struct sDIOmodel {
    int DIOtype;             /* Diode type */
    double DIOis;            /* Saturation current (I_s) */
    double DIOn;             /* Emission coefficient (N) */
    double DIOrs;            /* Series resistance (R_s) */
    double DIOcjo;           /* Zero-bias capacitance (C_j0) */
    double DIOphi;           /* Built-in potential (φ) */
    double DIOm;             /* Grading coefficient (m) */
    double DIOfc;            /* Forward bias capacitance coefficient */
    double DIOtt;            /* Transit time (τ_T) */
    double DIObv;            /* Breakdown voltage (BV) */
    double DIOibv;           /* Breakdown current (I_bv) */
    double DIOnbv;           /* Breakdown emission coefficient (N_bv) */
    
    /* Temperature coefficients */
    double DIOxti;           /* I_s temperature exponent */
    double DIOeg;            /* Energy gap */
    double DIOtnom;          /* Nominal temperature */
    
    struct sDIOmodel *DIOnextModel;
    DIOinstance *DIOinstances;
} DIOmodel;
```

These structures implement the mathematical parameters from Section 6.1: `DIOis` maps to \(I_s\), `DIOn` to \(N\), `DIObv` to \(BV\), etc. The matrix pointers (`DIOposPosPtr`, etc.) enable efficient stamping into SPICE's Modified Nodal Analysis (MNA) matrix.

#### 4.1.2 SPICEdev API Binding

The diode device registers with Ngspice through the standard `SPICEdev` structure:

```c
/* diodinit.c - Device initialization */
SPICEdev DIOinfo = {
    .DEVpublic = {
        .name = "d",
        .description = "Semiconductor Diode",
        .terms = 2,
        .termNames = {"+", "-"},
        .numInstanceParms = 20,
        .instanceParms = DIOpTable,
        .numModelParms = 15,
        .modelParms = DIOTmPTable,
        .flags = DEV_DEFAULT,
    },
    
    /* Function pointers implementing mathematical operations */
    .DEVload = DIOload,              /* DC/transient load - implements I_d(V_d) */
    .DEVsetup = DIOsetup,            /* Matrix setup - allocates SMP pointers */
    .DEVunsetup = DIOunsetup,        /* Cleanup */
    .DEVtemperature = DIOtemp,       /* Temperature scaling */
    .DEVtrunc = DIOtrunc,            /* LTE calculation */
    .DEVconvTest = DIOconvTest,      /* Convergence test */
    .DEVdestroy = DIOdestroy,        /* Memory destruction */
    .DEVacLoad = DIOacLoad,          /* AC small-signal load */
    .DEVpzLoad = DIOpzLoad,          /* Pole-zero load */
    .DEVnoise = DIOnoise,            /* Noise analysis */
    .DEVsoaCheck = DIOsoaCheck,      /* SOA verification */
    
    /* Structure sizes for memory allocation */
    .DEVinstSize = sizeof(DIOinstance),
    .DEVmodSize = sizeof(DIOmodel),
};

/* Parameter binding tables */
static IFparm DIOpTable[] = {
    IOP("is",    DIO_IS,    IF_REAL, "Saturation current"),
    IOP("n",     DIO_N,     IF_REAL, "Emission coefficient"),
    IOP("rs",    DIO_RS,    IF_REAL, "Series resistance"),
    IOP("cjo",   DIO_CJO,   IF_REAL, "Zero-bias junction capacitance"),
    IOP("vj",    DIO_VJ,    IF_REAL, "Junction potential"),
    IOP("m",     DIO_M,     IF_REAL, "Grading coefficient"),
    IOP("bv",    DIO_BV,    IF_REAL, "Reverse breakdown voltage"),
    IOP("ibv",   DIO_IBV,   IF_REAL, "Current at breakdown voltage"),
    IOP("tt",    DIO_TT,    IF_REAL, "Transit time"),
    IOP("area",  DIO_AREA,  IF_REAL, "Area factor"),
    IP("off",    DIO_OFF,   IF_FLAG, "Device initially off"),
    OP("v",      DIO_VOLT,  IF_REAL, "Diode voltage"),
    OP("i",      DIO_CUR,   IF_REAL, "Diode current"),
    OP("p",      DIO_POWER, IF_REAL, "Instantaneous power"),
};

void DIOinit(SPICEdev **device) {
    *device = &DIOinfo;
}
```

This API binding maps directly to the mathematical framework: `DEVload` implements the Shockley equation, `DEVtemperature` handles temperature scaling, and `DEVsoaCheck` enforces the SOA boundaries from Section 10.

### 4.2 Matrix Setup Implementation

#### 4.2.1 Sparse Matrix Pointer Allocation

The `DIOsetup()` function in `diosetup.c` allocates SMP matrix pointers following the pattern shown in Section 7.4:

```c
int DIOsetup(DIOmodel *model, CKTcircuit *ckt)
{
    DIOinstance *inst;
    
    for (inst = model->DIOinstances; inst != NULL; inst = inst->DIOnextInstance) {
        /* Allocate matrix pointers for 2-terminal device */
        inst->DIOposPosPtr = SMPmakeElt(ckt->CKTmatrix, 
                                        inst->DIOposNode, 
                                        inst->DIOposNode);
        inst->DIOposNegPtr = SMPmakeElt(ckt->CKTmatrix, 
                                        inst->DIOposNode, 
                                        inst->DIOnegNode);
        inst->DIOnegPosPtr = SMPmakeElt(ckt->CKTmatrix, 
                                        inst->DIOnegNode, 
                                        inst->DIOposNode);
        inst->DIOnegNegPtr = SMPmakeElt(ckt->CKTmatrix, 
                                        inst->DIOnegNode, 
                                        inst->DIOnegNode);
        
        /* Allocate internal node for series resistance if R_s > 0 */
        if (model->DIOrs > 0.0) {
            inst->DIOintNode = ckt->CKTmaxEqn++;
            inst->DIOposIntPtr = SMPmakeElt(ckt->CKTmatrix, 
                                            inst->DIOposNode, 
                                            inst->DIOintNode);
            inst->DIOintPosPtr = SMPmakeElt(ckt->CKTmatrix, 
                                            inst->DIOintNode, 
                                            inst->DIOposNode);
            inst->DIOintIntPtr = SMPmakeElt(ckt->CKTmatrix, 
                                            inst->DIOintNode, 
                                            inst->DIOintNode);
            inst->DIOintNegPtr = SMPmakeElt(ckt->CKTmatrix, 
                                            inst->DIOintNode, 
                                            inst->DIOnegNode);
            inst->DIOnegIntPtr = SMPmakeElt(ckt->CKTmatrix, 
                                            inst->DIOnegNode, 
                                            inst->DIOintNode);
        }
    }
    return OK;
}
```

This implements the MNA formulation from Section 5.2, creating the necessary matrix entries for the diode's conductance and any internal nodes for series resistance.

#### 4.2.2 Matrix Stamping for Newton-Raphson

The `DIOload()` function in `dioload.c` stamps the diode's conductance matrix and right-hand side vector:

```c
int DIOload(DIOmodel *model, CKTcircuit *ckt)
{
    DIOinstance *inst;
    double vd, id, gd, vt, exp_arg;
    double vj, ij, gj;  /* Junction variables */
    
    vt = CONSTKoverQ * ckt->CKTtemp;
    
    for (inst = model->DIOinstances; inst != NULL; inst = inst->DIOnextInstance) {
        /* Get voltage across diode */
        vd = *(ckt->CKTrhs + inst->DIOposNode) - 
             *(ckt->CKTrhs + inst->DIOnegNode);
        
        /* Apply PN junction limiting (Section 7.2) */
        vd = DEVpnjlim(vd, inst->DIOvoltage, vt, ckt->CKTvoltTol, &icheck);
        
        if (model->DIOrs > 0.0) {
            /* Solve for junction voltage with series resistance */
            vj = vd - inst->DIOcurrent * model->DIOrs;
            vj = DEVpnjlim(vj, inst->DIOvoltage, vt, ckt->CKTvoltTol, &icheck);
            
            /* Compute junction current and conductance */
            if (vj < -3.0 * vt * model->DIOn) {
                /* Reverse bias - breakdown region */
                if (vj < -model->DIObv) {
                    /* Breakdown current (Section 6.1) */
                    exp_arg = -(vj + model->DIObv) / (model->DIOnbv * vt);
                    ij = -model->DIOibv * exp(exp_arg);
                    gj = model->DIOibv * exp(exp_arg) / (model->DIOnbv * vt);
                } else {
                    /* Normal reverse bias */
                    ij = -model->DIOis;
                    gj = model->DIOis / (model->DIOn * vt);
                }
            } else {
                /* Forward bias - Shockley equation (Section 6.1) */
                exp_arg = vj / (model->DIOn * vt);
                ij = model->DIOis * (exp(exp_arg) - 1.0);
                gj = model->DIOis * exp(exp_arg) / (model->DIOn * vt);
            }
            
            /* Add GMIN for numerical stability */
            gj += ckt->CKTgmin;
            
            /* Total conductance with series resistance (Section 1.2) */
            gd = gj / (1.0 + gj * model->DIOrs);
            id = ij;
            
            /* Stamp 3x3 matrix for series resistance case */
            *(inst->DIOposIntPtr) += 1.0;
            *(inst->DIOintPosPtr) += 1.0;
            *(inst->DIOintIntPtr) += -1.0 - model->DIOrs * gj;
            *(inst->DIOintNegPtr) += gj;
            *(inst->DIOnegIntPtr) += -gj;
            
            /* RHS stamp */
            ckt->CKTrhs[inst->DIOintNode] += ij - gj * vj;
        } else {
            /* No series resistance - direct 2-terminal stamp */
            if (vd < -3.0 * vt * model->DIOn) {
                /* Reverse bias */
                if (vd < -model->DIObv) {
                    exp_arg = -(vd + model->DIObv) / (model->DIOnbv * vt);
                    id = -model->DIOibv * exp(exp_arg);
                    gd = model->DIOibv * exp(exp_arg) / (model->DIOnbv * vt);
                } else {
                    id = -model->DIOis;
                    gd = model->DIOis / (model->DIOn * vt);
                }
            } else {
                /* Forward bias */
                exp_arg = vd / (model->DIOn * vt);
                id = model->DIOis * (exp(exp_arg) - 1.0);
                gd = model->DIOis * exp(exp_arg) / (model->DIOn * vt);
            }
            
            gd += ckt->CKTgmin;
            
            /* Stamp 2x2 conductance matrix (Section 1.6) */
            *(inst->DIOposPosPtr) += gd;
            *(inst->DIOposNegPtr) += -gd;
            *(inst->DIOnegPosPtr) += -gd;
            *(inst->DIOnegNegPtr) += gd;
            
            /* RHS stamp */
            ckt->CKTrhs[inst->DIOposNode] -= id;
            ckt->CKTrhs[inst->DIOnegNode] += id;
        }
        
        /* Store state variables */
        inst->DIOvoltage = vd;
        inst->DIOcurrent = id;
        inst->DIOconduct = gd;
        
        /* Calculate instantaneous power for SOA check */
        inst->DIOpower = vd * id;
    }
    
    return OK;
}
```

This code directly implements the mathematical models from Section 6.1:
- Lines 31-45: Shockley equation \(I_d = I_s[\exp(V_d/(N V_T)) - 1]\)
- Lines 24-29: Breakdown model \(I_{br} = -I_{bv}\exp(-(V_d + BV)/(N_{bv} V_T))\)
- Lines 50-51: Conductance \(g_d = \partial