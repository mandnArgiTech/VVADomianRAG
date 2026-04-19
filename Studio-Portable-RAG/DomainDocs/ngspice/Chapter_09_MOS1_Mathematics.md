# MOSFET Level 1 Implementation

_Generated 2026-04-11 14:17 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/include/ngspice/devdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1load.c`

# Chapter: MOSFET Level 1 Implementation

This chapter details the implementation of the Shichman-Hodges Level 1 MOSFET model within the Ngspice simulation engine. The Level 1 model provides a foundational, physics-based description of long-channel MOSFET behavior, balancing computational efficiency with essential physical effects such as body bias, channel-length modulation, and temperature dependence. The implementation is distributed across several key C source files: `devdefs.h` defines the core data structures (`MOS1model` and `MOS1instance`); `mos1temp.c` handles all temperature-dependent parameter scaling; and `mos1load.c` contains the primary load routine that computes terminal currents, conductances, and capacitances, stamping them into the circuit's Modified Nodal Analysis (MNA) matrix. The following sections present the complete mathematical formulation derived from the device physics and the corresponding convergence analysis required for robust numerical simulation within the SPICE framework.

## Mathematical Formulation

The Shichman-Hodges (Level 1) model formulates the MOSFET terminal behavior using a piecewise-continuous description of drain current across cutoff, linear, and saturation regions. The formulation includes static DC equations, temperature scaling, and dynamic charge/capacitance models.

### 1. DC Terminal Currents (Shichman-Hodges Equations)

The core model defines the drain-source current \(I_{DS}\) based on the region of operation.

**Threshold Voltage:**
The threshold voltage \(V_{TH}\) is modulated by the source-bulk voltage \(V_{SB}\) via the body effect:
\[
V_{TH} = V_{TO} + \gamma \left( \sqrt{2\phi_F + V_{SB}} - \sqrt{2\phi_F} \right)
\]
where:
- \(V_{TO}\) is the zero-bias threshold voltage.
- \(\gamma\) is the body-effect coefficient.
- \(\phi_F\) is the Fermi potential (typically \(2\phi_F \approx 0.6V\)).
- \(V_{SB} = V_S - V_B\) (must be \(\geq 0\) for NMOS).

**Effective Gate-Source Voltage:**
\[
V_{GST} = V_{GS} - V_{TH}
\]
The device is in cutoff if \(V_{GST} \leq 0\).

**Saturation Voltage:**
\[
V_{DSAT} = V_{GST}
\]

**Drain Current \(I_{DS}\):**
- **Cutoff Region (\(V_{GST} \leq 0\)):**
  \[
  I_{DS} = 0
  \]

- **Linear/Triode Region (\(V_{GST} > 0\) and \(V_{DS} < V_{DSAT}\)):**
  \[
  I_{DS} = \beta \left[ V_{GST} V_{DS} - \frac{V_{DS}^2}{2} \right] (1 + \lambda V_{DS})
  \]
  where \(\beta = \frac{W_{eff}}{L_{eff}} \cdot K_P\) is the transconductance coefficient, and \(\lambda\) is the channel-length modulation parameter.

- **Saturation Region (\(V_{GST} > 0\) and \(V_{DS} \geq V_{DSAT}\)):**
  \[
  I_{DS} = \frac{\beta}{2} V_{GST}^2 (1 + \lambda V_{DS})
  \]

**Gate, Bulk, and Source Currents:**
\[
I_G = 0, \quad I_B = I_{BS} + I_{BD}, \quad I_S = -I_{DS} - I_{BS}
\]
where \(I_{BS}\) and \(I_{BD}\) are the diode junction currents between bulk-source and bulk-drain, modeled by:
\[
I_{BS} = I_{S} \left[ \exp\left(\frac{V_{BS}}{N V_T}\right) - 1 \right], \quad I_{BD} = I_{S} \left[ \exp\left(\frac{V_{BD}}{N V_T}\right) - 1 \right]
\]
with \(I_S\) as the junction saturation current, \(N\) the emission coefficient, and \(V_T = kT/q\) the thermal voltage.

### 2. Temperature Dependence

Key model parameters are scaled from their nominal values (specified at \(T_{NOM}\)) to the actual simulation temperature \(T\). The implementation in `mos1temp.c` performs these adjustments.

**Thermal Voltage:**
\[
V_T(T) = \frac{kT}{q}
\]

**Fermi Potential:**
\[
\phi_F(T) = \frac{kT}{q} \ln\left(\frac{N_{SUB}}{n_i(T)}\right)
\]
where the intrinsic carrier concentration \(n_i(T)\) scales as:
\[
n_i(T) = n_i(T_{NOM}) \left( \frac{T}{T_{NOM}} \right)^{3/2} \exp\left[ -\frac{E_G(T)}{2k} \left( \frac{1}{T} - \frac{1}{T_{NOM}} \right) \right]
\]
and the bandgap energy \(E_G(T)\) has a slight temperature dependence.

**Zero-Bias Threshold Voltage:**
\[
V_{TO}(T) = V_{TO}(T_{NOM}) + \left( \frac{dV_{TO}}{dT} \right) (T - T_{NOM})
\]

**Transconductance Coefficient:**
\[
K_P(T) = K_P(T_{NOM}) \left( \frac{T}{T_{NOM}} \right)^{-3/2}
\]

**Mobility:**
\[
\mu(T) = \mu(T_{NOM}) \left( \frac{T}{T_{NOM}} \right)^{-3/2}
\]

**Junction Parameters:**
The junction saturation current \(I_S\), built-in potential \(V_{BI}\), and zero-bias capacitance \(C_{J0}\) scale as:
\[
I_S(T) = I_S(T_{NOM}) \exp\left[ \frac{E_G(T_{NOM})}{V_T(T_{NOM})} - \frac{E_G(T)}{V_T(T)} \right] \left( \frac{T}{T_{NOM}} \right)^{XTI/N}
\]
\[
V_{BI}(T) = V_{BI}(T_{NOM}) \frac{T}{T_{NOM}} - \frac{2k}{q} T \ln\left( \frac{T}{T_{NOM}} \right) - \left[ E_G(T) - E_G(T_{NOM}) \frac{T}{T_{NOM}} \right]
\]
\[
C_{J0}(T) = C_{J0}(T_{NOM}) \left[ 1 + M_J \left( 4 \times 10^{-4} (T - T_{NOM}) - \frac{V_{BI}(T) - V_{BI}(T_{NOM})}{V_{BI}(T_{NOM})} \right) \right]
\]

### 3. Charge Storage and Capacitance Models

The dynamic model accounts for charge storage via gate and junction capacitances.

**Gate Capacitances (Meyer Model):**
The gate-channel capacitance is partitioned between source and drain. The total gate charge \(Q_G\) is balanced by \(Q_S\) and \(Q_D\).
- **Cutoff:** \(C_{GS} = C_{GD} = 0\), \(C_{GB} = C_{OX}\).
- **Saturation:** \(C_{GS} = \frac{2}{3} C_{OX}\), \(C_{GD} = 0\), \(C_{GB} = 0\).
- **Linear:** \(C_{GS} = C_{GD} = \frac{1}{2} C_{OX}\), \(C_{GB} = 0\).
where \(C_{OX} = C_{ox} \cdot W_{eff} \cdot L_{eff}\) is the total oxide capacitance.

**Junction Depletion Capacitances:**
The nonlinear depletion capacitance for the bulk-source and bulk-drain junctions follows:
\[
C_{j}(V) = \begin{cases}
C_{J0} \left(1 - \frac{V}{V_{BI}}\right)^{-M_J}, & V \leq F_C \cdot V_{BI} \\
C_{J0} \left(1 - F_C\right)^{-(1+M_J)} \left[1 - F_C(1+M_J) + M_J \frac{V}{V_{BI}}\right], & V > F_C \cdot V_{BI}
\end{cases}
\]
where \(F_C\) is the forward-bias coefficient.

### 4. Modified Nodal Analysis (MNA) Formulation

The device contributes to the circuit's DAE system \(G \mathbf{x} + C \dot{\mathbf{x}} = \mathbf{b}\). The contributions are stamped into the system matrix and RHS vector via the load function.

**DC Stamp (Conductance Matrix):**
For the four-terminal device (Drain, Gate, Source, Bulk), the Jacobian contributions from the drain current derivatives are:
\[
\begin{aligned}
g_m &= \frac{\partial I_D}{\partial V_{GS}} = \begin{cases}
\beta V_{DS} (1+\lambda V_{DS}), & \text{linear} \\
\beta V_{GST} (1+\lambda V_{DS}), & \text{saturation}
\end{cases} \\
g_{ds} &= \frac{\partial I_D}{\partial V_{DS}} = \begin{cases}
\beta (V_{GST} - V_{DS})(1+\lambda V_{DS}) + \lambda I_{DS}, & \text{linear} \\
\frac{\beta}{2} V_{GST}^2 \lambda, & \text{saturation}
\end{cases} \\
g_{mbs} &= \frac{\partial I_D}{\partial V_{BS}} = - \frac{\gamma}{2\sqrt{2\phi_F + V_{SB}}}} \cdot \begin{cases}
\beta V_{DS} (1+\lambda V_{DS}), & \text{linear} \\
\beta V_{GST} (1+\lambda V_{DS}), & \text{saturation}
\end{cases}
\end{aligned}
\]

The complete \(4 \times 4\) conductance stamp for the DC operating point is:
\[
\begin{bmatrix}
+g_{ds} & 0 & -g_{ds}-g_m-g_{mbs} & +g_{mbs} \\
0 & 0 & 0 & 0 \\
-g_{ds} & 0 & +g_{ds}+g_m+g_{mbs} & -g_{mbs} \\
0 & 0 & 0 & 0
\end{bmatrix}
\]
This matrix is added to the system's \(G\) matrix at the rows/columns corresponding to the drain, gate, source, and bulk nodes.

**Transient Stamp (Capacitance Matrix):**
For transient analysis, the capacitance contributions are discretized using the Backward Euler or Trapezoidal rule. For a capacitor \(C\), the companion model is a conductance \(g_{eq} = C / h\) in parallel with a current source \(i_{eq} = C \cdot v_{old} / h\), where \(h\) is the time step. The gate and junction capacitances generate stamps of the form:
\[
\begin{bmatrix}
+g_{eq} & -g_{eq} \\
-g_{eq} & +g_{eq}
\end{bmatrix}
\]
for the two nodes they connect, with the appropriate \(i_{eq}\) added to the RHS vector.

## Convergence Analysis

The Level 1 MOSFET model presents specific numerical challenges within the Newton-Raphson loop of SPICE. Its piecewise-defined currents and strong nonlinearities require careful handling to ensure robust convergence.

### 1. Newton-Raphson Convergence Properties

The model's current equations are continuous in value but have discontinuous derivatives at the region boundaries (\(V_{GST}=0\) and \(V_{DS}=V_{DSAT}\)). This can degrade the quadratic convergence of Newton's method.

**Continuity Enforcement:**
The implementation uses smooth interpolation or explicit region detection (via `MOS1saturation` flag) to ensure function continuity. The derivatives \(g_m\), \(g_{ds}\), and \(g_{mbs}\) are computed consistently within the detected region. However, the transition between regions can still cause a sudden change in the Jacobian, potentially leading to iteration overshoot or divergence.

**Damping for Large Voltage Steps:**
When the Newton update \(\Delta \mathbf{x}\) is large (e.g., > 0.5 V), the simulator may apply a damping factor \(\lambda < 1\) to the update:
\[
\mathbf{x}^{(k+1)} = \mathbf{x}^{(k)} + \lambda \Delta \mathbf{x}
\]
This is critical during the initial iterations when voltages are far from the solution, especially if the device is in cutoff.

**Regularization of Singularities:**
- The body-effect term \(\sqrt{2\phi_F + V_{SB}}\) is protected by a lower limit (e.g., `MOS1_MIN_SQRT_ARG`) to avoid division by zero or negative arguments.
- The channel-length modulation term \((1 + \lambda V_{DS})\) is clipped to a minimum positive value to prevent non-physical negative conductance.

### 2. Numerical Stability and Time Step Control in Transient Analysis

**Local Truncation Error (LTE) Control:**
The gate and junction charges are state variables. The LTE for a capacitor is estimated as:
\[
\text{LTE} \approx \frac{h^2}{12} \left| \frac{d^2 q}{dt^2} \right|
\]
For the nonlinear Meyer capacitance, the second derivative is approximated using past charge values. The time step \(h\) is adapted to keep LTE below a user-specified tolerance \(\tau\):
\[
h_{new} = h_{current} \cdot \min\left(2.0, \max\left(0.5, \sqrt{\frac{\tau}{\text{LTE}}} \right) \right)
\]

**Stability of Capacitance Discretization:**
The Backward Euler method is L-stable and damps numerical oscillations, making it robust for stiff circuits with large capacitance variations. The Trapezoidal rule is A-stable but can produce artificial ringing during rapid switching if the time step is too large. The Level 1 implementation typically uses the same integration method as the global transient analysis.

**Junction Capacitance in Strong Forward Bias:**
When \(V_{BS}\) or \(V_{BD}\) approaches \(V_{BI}\), the depletion capacitance model switches to a linear extrapolation to avoid singularity. This linearization must be smooth to prevent discontinuities in the Jacobian that could break Newton convergence.

### 3. Matrix Conditioning and Ill-Posed Operations

**Gate Node Isolation:**
The gate terminal draws no DC current, resulting in a zero diagonal element in the conductance matrix for the gate node. This does not cause singularity if the gate is connected to a voltage source or has a finite resistance to ground (e.g., a large `GMIN`). The simulator's sparse matrix solver must handle this via pivoting.

**High-Gain Regions:**
In saturation, the transconductance \(g_m\) can be very large (especially for large \(W/L\) ratios). This can create a large eigenvalue spread in the system Jacobian, worsening its condition number. The solver's partial pivoting in LU factorization is essential to maintain numerical accuracy.

**Impact of Channel-Length Modulation:**
A small \(\lambda\) parameter makes \(g_{ds}\) very small in saturation, leading to a near-zero conductance between drain and source. This can make the matrix nearly singular if the drain and source are not otherwise connected. The global `GMIN` conductance (typically ~1e-12 S) added across every p-n junction provides a DC path to prevent this.

### 4. Convergence Acceleration and Fallback Techniques

**Source Stepping:**
For circuits where the MOSFET is the primary nonlinear element (e.g., a CMOS inverter at the switching threshold), the DC operating point solution may not converge from a default initial guess (all nodes at 0V). Source stepping (a homotopy method) ramps the power supply voltages from zero to their final values over several Newton iterations, providing a smoother path to the solution.

**Gmin Stepping:**
Similarly, the global `GMIN` conductance can be temporarily increased to provide better matrix conditioning and then gradually reduced to its nominal value.

**Use of Previous Solution:**
In transient analysis, the solution from the previous time point provides an excellent initial guess for Newton's method, as device voltages typically change slowly relative to the time step. This is stored in the `CKTstates` vector.

### 5. Error Propagation and Model Limitations

**Sensitivity to Parameters:**
The model is highly sensitive to \(V_{TO}\) and \(K_P\). Small errors in these parameters (e.g., due to temperature scaling) can cause large shifts in \(I_{DS}\). The convergence tolerances (e.g., `reltol=1e-3`, `abstol=1e-12`) must be tight enough to capture these variations.

**Charge Conservation:**
The Meyer gate capacitance model is not charge-conserving; the sum \(Q_G + Q_S + Q_D\) is not constant, which can lead to numerical drift in very long transient simulations. More advanced models (e.g., Yang-Chatterjee) would be required for exact charge conservation.

**Region Detection Errors:**
Incorrect detection of the saturation/linear boundary due to numerical noise can cause the Jacobian to flip between two very different values, leading to convergence failure. The implementation uses hysteresis or a small margin (e.g., `MOS1_SAT_MARGIN`) around \(V_{DSAT}\) to prevent chattering.

**Temperature Scaling Convergence:**
The temperature adjustment in `mos1temp.c` is performed once per temperature point and is not iterative. However, if the circuit self-heats significantly, the updated temperature would require re-evaluation of parameters, which is not handled in the basic Level 1 model.

## C Implementation

This section details the concrete C implementation of the Shichman-Hodges Level 1 MOSFET model within the Ngspice codebase. The implementation is distributed across several key source files, each mapping directly to the mathematical formulations presented earlier. The core data structures, parameter processing, temperature scaling, and the load routine that stamps the device's contributions into the Modified Nodal Analysis (MNA) system are examined.

### 1. Core Data Structures (`devdefs.h`)

The model and instance data are encapsulated in two primary C structures defined in `devdefs.h`. These structures store all parameters, state variables, and matrix pointers required for simulation.

#### 1.1 Model Structure (`MOS1model`)
The `MOS1model` structure holds the Level 1 parameters that are common to all instances of a given model card. It acts as a template.

```c
typedef struct sMOS1model {
    int MOS1modType;                /* NMOS or PMOS */
    /* Level 1 (Shichman-Hodges) parameters */
    double MOS1vto;                 /* Zero-bias threshold voltage (V_TO) */
    double MOS1kp;                  /* Transconductance parameter (K_P) */
    double MOS1gamma;               /* Bulk threshold parameter (γ) */
    double MOS1phi;                 /* Surface potential (φ_F) */
    double MOS1lambda;              /* Channel-length modulation (λ) */
    double MOS1tox;                 /* Oxide thickness (t_ox) */
    double MOS1cox;                 /* Oxide capacitance per unit area (C_ox) */
    double MOS1u0;                  /* Surface mobility (μ_0) */
    /* ... additional parameters and flags ... */
    struct sMOS1model *MOS1nextModel;
    MOS1instance *MOS1instances;    /* Linked list of instances */
} MOS1model;
```
**Mathematical Mapping:** The fields `MOS1vto`, `MOS1kp`, `MOS1gamma`, `MOS1phi`, and `MOS1lambda` correspond directly to the symbols \(V_{TO}\), \(K_P\), \(\gamma\), \(\phi_F\), and \(\lambda\) in the Shichman-Hodges equations. `MOS1cox` is calculated from `MOS1tox` using the formula \(C_{ox} = \epsilon_{ox} / t_{ox}\).

#### 1.2 Instance Structure (`MOS1instance`)
The `MOS1instance` structure holds data specific to a single transistor in the netlist, including its geometry, temperature-adjusted parameters, instantaneous voltages, conductances, and pointers into the system matrix.

```c
typedef struct sMOS1instance {
    /* Node connections */
    int MOS1dNode;                  /* Drain node index */
    int MOS1gNode;                  /* Gate node index */
    int MOS1sNode;                  /* Source node index */
    int MOS1bNode;                  /* Bulk node index */

    /* Geometric parameters */
    double MOS1l;                   /* Drawn length (L) */
    double MOS1w;                   /* Drawn width (W) */

    /* Temperature-adjusted parameters */
    double MOS1tVto;                /* Temperature-adjusted VTO */
    double MOS1tKp;                 /* Temperature-adjusted KP */
    double MOS1tGamma;              /* Temperature-adjusted GAMMA */
    double MOS1tPhi;                /* Temperature-adjusted PHI */
    double MOS1vt;                  /* Thermal voltage (V_T = kT/q) */

    /* State variables */
    double MOS1vgs;                 /* Instantaneous V_GS */
    double MOS1vds;                 /* Instantaneous V_DS */
    double MOS1vbs;                 /* Instantaneous V_BS */
    double MOS1vbd;                 /* Instantaneous V_BD */

    /* Conductances (Jacobian elements) */
    double MOS1gm;                  /* Transconductance (g_m) */
    double MOS1gds;                 /* Drain conductance (g_ds) */
    double MOS1gmbs;                /* Bulk transconductance (g_mbs) */
    double MOS1gbd;                 /* Bulk-drain diode conductance */
    double MOS1gbs;                 /* Bulk-source diode conductance */

    /* Currents */
    double MOS1cd;                  /* Drain current (I_DS) */
    double MOS1cbd;                 /* Bulk-drain diode current */
    double MOS1cbs;                 /* Bulk-source diode current */

    /* Operation flags */
    double MOS1saturation;          /* Saturation flag (1=sat, 0=linear) */

    /* Matrix pointers (e.g., MOS1dDrainPtr points to G[drain][drain]) */
    double *MOS1dDrainPtr;
    double *MOS1dGatePtr;
    double *MOS1dSourcePtr;
    double *MOS1dBulkPtr;
    /* ... 12 more pointers for the 4x4 conductance matrix ... */

    struct sMOS1instance *MOS1nextInstance;
} MOS1instance;
```
**Mathematical Mapping:** This structure is the in-memory representation of the device's state. The voltages (`MOS1vgs`, etc.) are fetched from the circuit's solution vector. The conductances (`MOS1gm`, etc.) are computed from the mathematical derivatives. The matrix pointers provide direct access to locations in the sparse system matrix `G` where the device's Jacobian contributions must be added.

### 2. Parameter Processing and Defaults (`mos1par.c`)

The `MOS1param()` function in `mos1par.c` processes input parameters and calculates derived quantities. A key calculation is the transconductance parameter `K_P`.

**Mathematical Mapping:** The code implements the relationship \(K_P = \mu_0 C_{ox}\). If the user provides `KP`, it is used directly. If they provide mobility `U0` and oxide thickness `TOX`, `KP` is calculated.

```c
case MOS1_TOX:
    model->MOS1tox = value->rValue;
    if (model->MOS1tox <= 0.0) return E_BADPARM;
    /* Calculate oxide capacitance per unit area: C_ox = ε_ox / t_ox */
    model->MOS1cox = 3.9 * 8.854e-14 / model->MOS1tox;
    /* If KP not given, calculate from U0 and COX: K_P = μ_0 * C_ox */
    if (!model->MOS1kpGiven && model->MOS1u0Given) {
        model->MOS1kp = model->MOS1u0 * model->MOS1cox;
    }
    break;
case MOS1_U0:
    model->MOS1u0 = value->rValue;
    model->MOS1u0Given = TRUE;
    /* If TOX is given, calculate KP */
    if (model->MOS1toxGiven) {
        model->MOS1kp = model->MOS1u0 * model->MOS1cox;
    }
    break;
```

### 3. Temperature Dependence Implementation (`mos1temp.c`)

The `MOS1temp()` function scales all model parameters from their nominal temperature (`TNOM`) to the actual simulation or instance temperature. This function is called before any analysis at a new temperature.

#### 3.1 Thermal Voltage and Ratios
The foundation for temperature scaling is the thermal voltage \(V_T = kT/q\) and the temperature ratio.

```c
void MOS1temp(MOS1instance *here, MOS1model *model, CKTcircuit *ckt) {
    double tnom = model->MOS1tnom;
    double temp = here->MOS1temp;
    double tempk = temp + CONSTCtoK;
    double tnomk = tnom + CONSTCtoK;
    double ratio = tempk / tnomk;      /* T/T_NOM */
    double ratio1 = ratio - 1.0;       /* T/T_NOM - 1 */
    double vt = tempk * CONSTKoverQ;   /* V_T = kT/q */
    here->MOS1vt = vt;                 /* Store for use in load routine */
    /* ... further scaling ... */
}
```

#### 3.2 Threshold Voltage Scaling
Implements \(V_{TO}(T) = V_{TO}(T_{NOM}) + K_{T1} \times (T/T_{NOM} - 1) + K_{T2} \times (T/T_{NOM} - 1)^2\).

```c
double kt1_total = model->MOS1kt1 + model->MOS1kt1l / here->MOS1l;
here->MOS1tVto = model->MOS1vto + kt1_total * ratio1 + model->MOS1kt2 * ratio1 * ratio1;
```

#### 3.3 Mobility and K_P Scaling
Implements \(\mu(T) = \mu(T_{NOM}) \times (T/T_{NOM})^{-UTE}\) and consequently \(K_P(T) = K_P(T_{NOM}) \times (T/T_{NOM})^{-UTE}\).

```c
here->MOS1tU0 = model->MOS1u0 * pow(ratio, -model->MOS1ute);
if (model->MOS1kpGiven) {
    here->MOS1tKp = model->MOS1kp * pow(ratio, -model->MOS1ute);
} else {
    /* K_P = μ(T) * C_ox */
    here->MOS1tKp = here->MOS1tU0 * model->MOS1cox;
}
```

#### 3.4 Surface and Junction Potential Scaling
Implements the complex temperature dependence for \(\phi_F(T)\) and \(V_{BI}(T)\), which includes bandgap energy \(E_G(T)\) terms.

```c
double egfet = 1.16 - (7.02e-4 * tempk * tempk) / (tempk + 1108.0); /* E_G(T) */
/* Surface potential φ_F(T) */
here->MOS1tPhi = model->MOS1phi * ratio - 3.0 * vt * log(ratio) - egfet + egfet * ratio;
/* Junction built-in potential V_BI(T) */
here->MOS1tPb = model->MOS1pb * ratio - 3.0 * vt * log(ratio) - egfet + egfet * ratio;
```

### 4. Load Routine Implementation (`mos1load.c`)

The `MOS1load()` function is the core of the implementation. It is called during each Newton-Raphson iteration to compute the device's currents and conductances based on the current circuit solution, and to stamp these contributions into the MNA matrix and RHS vector.

#### 4.1 Voltage Retrieval and Threshold Calculation
The function first retrieves the terminal voltages from the circuit's previous solution vector (`CKTrhsOld`).

```c
here->MOS1vgs = ckt->CKTrhsOld[here->MOS1gNode] - ckt->CKTrhsOld[here->MOS1sNode];
here->MOS1vds = ckt->CKTrhsOld[here->MOS1dNode] - ckt->CKTrhsOld[here->MOS1sNode];
here->MOS1vbs = ckt->CKTrhsOld[here->MOS1bNode] - ckt->CKTrhsOld[here->MOS1sNode];
here->MOS1vbd = here->MOS1vbs - here->MOS1vds;
```
It then calculates the threshold voltage \(V_{TH}\) using the temperature-adjusted parameters, implementing the body effect formula.

```c
double calculateVth(MOS1instance *here) {
    double vto = here->MOS1tVto;
    double gamma = here->MOS1tGamma;
    double phi = here->MOS1tPhi;
    double vbs = here->MOS1vbs;
    double sarg;
    if (vbs <= 0.0) {
        sarg = sqrt(phi - vbs); /* sqrt(2φ_F - V_BS) */
    } else {
        /* Forward bias approximation */
        sarg = sqrt(phi) - vbs / (2.0 * sqrt(phi));
    }
    double vth = vto + gamma * (sarg - sqrt(phi)); /* V_TH = V_TO + γ*(sarg - √(2φ_F)) */
    return vth;
}
```

#### 4.2 Drain Current and Conductance Calculation
The function `calculateIds()` implements the piecewise Shichman-Hodges equations and computes the partial derivatives for the Jacobian.

```c
void calculateIds(MOS1instance *here, CKTcircuit *ckt) {
    double vgs = here->MOS1vgs;
    double vds = here->MOS1vds;
    double vth = calculateVth(here);
    double beta = here->MOS1tKp * (here->MOS1w / here->MOS1l); /* β = K_P * (W/L) */
    double vdsat = vgs - vth; /* V_DSAT = V_GS - V_TH */
    if (vdsat < 0.0) vdsat = 0.0;

    double ids, gm, gds, gmbs;
    if (vgs <= vth) {
        /* Cutoff */
        ids = 0.0; gm = 0.0; gds = 0.0; gmbs = 0.0;
        here->MOS1saturation = 0;
    } else if (vds < vdsat) {
        /* Linear region */
        double lambda = here->MOS1lambda;
        double arg = 1.0 + lambda * vds;
        /* I_DS = β * [(V_GS-V_TH)*V_DS - V_DS²/2] * (1+λ*V_DS) */
        ids = beta * ((vgs - vth) * vds - 0.5 * vds * vds) * arg;
        /* g_m = ∂I_DS/∂V_GS = β * V_DS * (1+λ*V_DS) */
        gm = beta * vds * arg;
        /* g_ds = ∂I_DS/∂V_DS = β*[(V_GS-V_TH)-V_DS]*(1+λ*V_DS) + β*λ*[...] */
        gds = beta * ((vgs - vth) - vds) * arg + beta * lambda * ((vgs - vth) * vds - 0.5 * vds * vds);
        /* g_mbs = -g_m * ∂V_TH/∂V_BS */
        double dvdth_dvbs = -here->MOS1tGamma / (2.0 * sqrt(here->MOS1tPhi - vbs));
        gmbs = -gm * dvdth_dvbs;
        here->MOS1saturation = 0;
    } else {
        /* Saturation region */
        double lambda = here->MOS1lambda;
        double arg = 1.0 + lambda * vds;
        /* I_DS = (β/2) * (V_GS-V_TH)² * (1+λ*V_DS) */
        ids = 0.5 * beta * (vgs - vth) * (vgs - vth) * arg;
        /* g_m = β * (V_GS-V_TH) * (1+λ*V_DS) */
        gm = beta * (vgs - vth) * arg;
        /* g_ds = (β/2) * λ * (V_GS-V_TH)² */
        gds = 0.5 * beta * lambda * (vgs - vth) * (vgs - vth);
        double dvdth_dvbs = -here->MOS1tGamma / (2.0 * sqrt(here->MOS1tPhi - vbs));
        gmbs = -gm * dvdth_dvbs;
        here->MOS1saturation = 1;
    }
    here->MOS1cd = ids; here->MOS1gm = gm; here->MOS1gds = gds; here->MOS1gmbs = gmbs;
}
```

#### 4.3 Junction Diode Calculations
The bulk-source and bulk-drain diodes are modeled using the standard diode equation with exponential limiting.

```c
void calculateJunctionCurrents(MOS1instance *here) {
    double vt = here->MOS1vt;
    double is = here->MOS1tIs;
    double vbs = here->MOS1vbs;
    /* I_BS = I_S * [exp(V_BS/(N*V_T)) - 1], N=1 for Level 1 */
    double vbsn = vbs / vt;
    double expbs;
    if (vbsn > MOS1_MAX_EXP) { expbs = exp(MOS1_MAX_EXP); } /* Numerical safeguard */
    else if (vbsn < -MOS1_MAX_EXP) { expbs = exp(-MOS1_MAX_EXP); }
    else { expbs = exp(vbsn); }
    here->MOS1cbs = is * (expbs - 1.0);
    here->MOS1gbs = (is / vt) * expbs; /* ∂I_BS/∂V_BS */
    /* ... Repeat for bulk-drain diode (V_BD) ... */
}
```

#### 4.4 MNA Matrix Stamping
This is the critical step that inserts the device's linearized contributions into the global system of equations. The code directly stamps the 4x4 conductance matrix derived from the partial derivatives.

```c
/* Extract conductances computed earlier */
double gm = here->MOS1gm;
double gds = here->MOS1gds;
double gmbs = here->MOS1gmbs;
double gbd = here->MOS1gbd;
double gbs = here->MOS1gbs;

/* Stamp drain node equation: I_D + I_BD + g_dd*V_D + g_dg*V_G + g_ds*V_S + g_db*V_B = 0 */
*(here->MOS1dDrainPtr) += gds + gbd;       /* g_dd = g_ds + g_bd */
*(here->MOS1dGatePtr) += -gm;              /* g_dg = -g_m */
*(here->MOS1dSourcePtr) += -gds;           /* g_ds = -g_ds */
*(here->MOS1dBulkPtr) += -gbd + gmbs;      /* g_db = -g_bd + g_mbs */

/* Stamp source node equation */
*(here->MOS1sDrainPtr) += -gds;            /* g_sd = -g_ds */
*(here->MOS1sGatePtr) += gm;               /* g_sg = g_m */
*(here->MOS1sSourcePtr) += gds + gbs;      /* g_ss = g_ds + g_bs */
*(here->MOS1sBulkPtr) += -gbs - gmbs;      /* g_sb = -g_bs - g_mbs */

/* Stamp bulk node equation */
*(here->MOS1bDrainPtr) += -gbd;            /* g_bd = -g_bd */
*(here->MOS1bSourcePtr) += -gbs;           /* g_bs = -g_bs */
*(here->MOS1bBulkPtr) += gbd + gbs;        /* g_bb = g_bd + g_bs */

/* Stamp RHS vector with current contributions */
ckt->CKTrhs[here->MOS1dNode] -= here->MOS1cd + here->MOS1cbd; /* -I_D - I_BD */
ckt->CKTrhs[here->MOS1sNode] -= -here->MOS1cd + here->MOS1cbs; /* -(-I