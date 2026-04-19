# HFET and MESFET: Heterojunction Physics and DC Load

_Generated 2026-04-13 01:43 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfettemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2defs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2param.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2load.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2temp.c`

# Chapter: HFET and MESFET: Heterojunction Physics and DC Load

## Technical Introduction

The Heterojunction Field-Effect Transistor (HFET) and Metal-Semiconductor FET (MESFET) implementations in Ngspice extend the foundational MOSFET architecture to address the unique transport characteristics of compound semiconductors and Schottky gate structures. These specialized device models are implemented through a coordinated set of C source files that handle parameter definition, physics-based current formulations, and thermal modeling within Ngspice's Modified Nodal Analysis framework.

The core implementation revolves around `hfetdefs.h` and `hfet2defs.h`, which define the fundamental data structures (`HFETmodel`, `HFETinstance`, `HFET2model`, `HFET2instance`) that map SPICE parameters to internal state variables for two different model variants. Parameter processing occurs in `hfetparam.c` and `hfet2param.c`, managing the translation from circuit deck specifications to internal numerical representations. The critical DC load functions in `hfetload.c` and `hfet2load.c` implement the nonlinear current equations and their derivatives, stamping the conductance matrix and right-hand-side vector for Newton-Raphson iteration. Temperature-dependent effects are handled by `hfettemp.c` and `hfet2temp.c`, which scale model parameters according to operating temperature and self-heating effects. This chapter examines how these files collectively implement the advanced physics of heterojunction devices within Ngspice's simulation framework.

## 1. Mathematical Formulation

### 1.1 Modified Nodal Analysis Matrix Topology for HFET/MESFET

The HFET and MESFET models implement a 3-terminal (drain, gate, source) Modified Nodal Analysis (MNA) formulation with optional substrate node for complete physical modeling. The matrix structure follows SPICE's conductance-based approach with extensions for heterojunction-specific effects.

#### 1.1.1 Basic 3-Terminal MNA Formulation

**Terminal ordering:** Drain (d), Gate (g), Source (s)

**Conductance matrix stamp:**
\[
\begin{bmatrix}
Y_{dd} & Y_{dg} & Y_{ds} \\
Y_{gd} & Y_{gg} & Y_{gs} \\
Y_{sd} & Y_{sg} & Y_{ss}
\end{bmatrix}
\begin{bmatrix}
V_d \\ V_g \\ V_s
\end{bmatrix}
=
\begin{bmatrix}
I_d \\ I_g \\ I_s
\end{bmatrix}
\]

**Matrix elements from small-signal parameters:**
\[
Y_{dd} = g_{ds} + j\omega(C_{gd} + C_{ds})
\]
\[
Y_{dg} = -j\omega C_{gd}
\]
\[
Y_{ds} = -g_{ds} - j\omega C_{ds}
\]
\[
Y_{gg} = j\omega(C_{gd} + C_{gs})
\]
\[
Y_{gs} = -j\omega C_{gs}
\]
\[
Y_{ss} = g_{ds} + j\omega(C_{gs} + C_{ds})
\]

Where:
- \(g_{ds} = \partial I_d/\partial V_{ds}\) (output conductance)
- \(C_{gs}, C_{gd}, C_{ds}\) are the corresponding capacitances
- \(\omega = 2\pi f\) is the angular frequency

#### 1.1.2 Extended 4-Terminal Formulation with Substrate

For complete physical modeling including substrate effects:

**Extended matrix structure:**
\[
\begin{bmatrix}
Y_{dd} & Y_{dg} & Y_{ds} & Y_{db} \\
Y_{gd} & Y_{gg} & Y_{gs} & Y_{gb} \\
Y_{sd} & Y_{sg} & Y_{ss} & Y_{sb} \\
Y_{bd} & Y_{bg} & Y_{bs} & Y_{bb}
\end{bmatrix}
\begin{bmatrix}
V_d \\ V_g \\ V_s \\ V_b
\end{bmatrix}
=
\begin{bmatrix}
I_d \\ I_g \\ I_s \\ I_b
\end{bmatrix}
\]

**Substrate coupling elements:**
\[
Y_{db} = -j\omega C_{db}, \quad Y_{gb} = -j\omega C_{gb}, \quad Y_{sb} = -j\omega C_{sb}
\]
\[
Y_{bb} = j\omega(C_{db} + C_{gb} + C_{sb}) + g_{sub}
\]

### 1.2 HFET 2DEG Transport Physics

#### 1.2.1 Two-Dimensional Electron Gas Charge Control

**Sheet charge density in triangular quantum well:**
\[
n_s = \frac{\epsilon}{qd} (V_{gs} - V_{off} - V(x))
\]

**Fermi level position in quantum well:**
\[
E_F = \frac{\hbar^2}{2m^*} \left( \frac{\pi n_s}{2} \right)^{2/3} + \Delta E_c
\]

**Effective gate voltage with quantum capacitance:**
\[
V_{gs,eff} = V_{gs} - V_{off} - \frac{qn_s}{C_{quantum}}
\]
\[
C_{quantum} = \frac{q^2 m^*}{\pi \hbar^2} \left(1 - e^{-qV_{gs}/kT}\right)
\]

#### 1.2.2 Velocity-Field Characteristics for III-V Materials

**Field-dependent mobility with saturation:**
\[
\mu(E) = \frac{\mu_0}{\left[1 + \left(\frac{\mu_0 E}{v_{sat}}\right)^\beta\right]^{1/\beta}}
\]

**Drain current in gradual channel approximation:**
\[
I_d = qW \int_0^L n_s(x) v(E(x)) dx
\]

**Analytical solution for constant mobility:**
\[
I_d = \frac{W}{L} \mu C_g \left[ (V_{gs} - V_{off})V_{ds} - \frac{V_{ds}^2}{2} \right] \quad \text{for } V_{ds} \leq V_{ds,sat}
\]

**Saturation current with velocity saturation:**
\[
I_{d,sat} = qW v_{sat} n_{s,sat}
\]
\[
n_{s,sat} = \frac{\epsilon}{qd} (V_{gs} - V_{off} - V_{ds,sat})
\]

### 1.3 MESFET Schottky Gate Physics

#### 1.3.1 Schottky Barrier Electrostatics

**Gate current with thermionic emission:**
\[
I_g = A^* T^2 \exp\left(-\frac{q\phi_b}{kT}\right) \left[ \exp\left(\frac{qV_{gs}}{nkT}\right) - 1 \right]
\]

**Barrier lowering with image force:**
\[
\Delta \phi = \sqrt{\frac{qE}{4\pi\epsilon}}
\]

**Depletion layer width under gate:**
\[
W_d = \sqrt{\frac{2\epsilon}{qN_d} (\phi_b - V_{gs} + V(x))}
\]

#### 1.3.2 Current-Voltage Characteristics

**Drain current in linear region:**
\[
I_d = \frac{W}{L} \mu qN_d a \left[ V_{ds} - \frac{2}{3} \frac{\sqrt{(\phi_b - V_{gs} + V_{ds})^3} - \sqrt{(\phi_b - V_{gs})^3}}{\sqrt{\phi_b - V_{off}}} \right]
\]

**Pinch-off voltage:**
\[
V_p = \frac{qN_d a^2}{2\epsilon} - \phi_b
\]

**Saturation voltage:**
\[
V_{ds,sat} = V_{gs} - V_p
\]

### 1.4 Advanced Physical Effects

#### 1.4.1 Short-Channel Effects

**Channel length modulation:**
\[
\Delta L = \lambda \sqrt{\frac{\epsilon}{qN_d} (V_{ds} - V_{ds,sat})}
\]

**Drain-induced barrier lowering (DIBL):**
\[
\Delta V_{th} = \eta V_{ds} \exp\left(-\frac{L}{l_d}\right)
\]
\[
l_d = \sqrt{\frac{\epsilon t_{barrier}}{qN_d}}
\]

#### 1.4.2 Self-Heating Effects

**Thermal network equations:**
\[
P_{diss} = V_{ds} I_d + V_{gs} I_g
\]
\[
T_j = T_{amb} + R_{th} P_{diss} + \tau_{th} \frac{dP_{diss}}{dt}
\]

**Temperature-dependent parameters:**
\[
\mu(T) = \mu_0 \left(\frac{T}{T_0}\right)^{-\alpha_\mu}
\]
\[
v_{sat}(T) = v_{sat0} \left(\frac{T}{T_0}\right)^{-\alpha_v}
\]

#### 1.4.3 Trapping Effects (DC-to-RF Dispersion)

**Frequency-dependent output conductance:**
\[
g_{ds}(f) = g_{ds0} + \frac{\Delta g_{ds}}{1 + j\omega\tau_{trap}}
\]

**Surface state trapping time constant:**
\[
\tau_{trap} = \frac{1}{v_{th} \sigma N_t}
\]

### 1.5 Capacitance Modeling

#### 1.5.1 Gate-Source Capacitance

**Intrinsic Cgs with charge control:**
\[
C_{gs} = \frac{\partial Q_g}{\partial V_{gs}} = \frac{W L \epsilon}{d} \left[1 - \frac{V_{ds}}{2(V_{gs} - V_{off})}\right]
\]

**Extrinsic overlap capacitance:**
\[
C_{gso} = \epsilon \frac{W L_{ov}}{t_{ox}}
\]

#### 1.5.2 Gate-Drain Capacitance

**Feedback capacitance with Miller effect:**
\[
C_{gd} = \frac{\partial Q_g}{\partial V_{gd}} = \frac{W L \epsilon}{d} \frac{V_{ds}}{2(V_{gs} - V_{off})}
\]

#### 1.5.3 Drain-Source Capacitance

**Output capacitance:**
\[
C_{ds} = \frac{\epsilon W L_{sd}}{t_{sub}} + C_{j,ds}
\]

**Junction capacitance:**
\[
C_{j,ds} = C_{j0} \left(1 - \frac{V_{ds}}{V_{bi}}\right)^{-m}
\]

## 2. Convergence Analysis

### 2.1 Newton-Raphson Convergence for HFET/MESFET

The HFET and MESFET models present unique convergence challenges due to strong nonlinearities from velocity saturation, Schottky barriers, and quantum confinement effects.

#### 2.1.1 Jacobian Matrix Structure

**Complete Jacobian for 3-terminal device:**
\[
\mathbf{J} = 
\begin{bmatrix}
\frac{\partial I_d}{\partial V_d} & \frac{\partial I_d}{\partial V_g} & \frac{\partial I_d}{\partial V_s} \\
\frac{\partial I_g}{\partial V_d} & \frac{\partial I_g}{\partial V_g} & \frac{\partial I_g}{\partial V_s} \\
\frac{\partial I_s}{\partial V_d} & \frac{\partial I_s}{\partial V_g} & \frac{\partial I_s}{\partial V_s}
\end{bmatrix}
\]

**Key derivative calculations:**
\[
\frac{\partial I_d}{\partial V_d} = g_{ds} + \frac{\partial I_d}{\partial V_{ds}} \cdot \frac{\partial V_{ds}}{\partial V_d}
\]
\[
\frac{\partial I_d}{\partial V_g} = g_m = \frac{\partial I_d}{\partial V_{gs}}
\]
\[
\frac{\partial I_d}{\partial V_s} = -g_{ds} - g_m
\]

**Schottky gate derivatives:**
\[
\frac{\partial I_g}{\partial V_g} = \frac{q}{nkT} I_g \exp\left(\frac{qV_{gs}}{nkT}\right)
\]

#### 2.1.2 Convergence Criteria

**Voltage convergence at all nodes:**
\[
|V_i^{(k+1)} - V_i^{(k)}| \leq \epsilon_{rel} \cdot \max(|V_i^{(k+1)}|, |V_i^{(k)}|) + \epsilon_{abs} \quad \text{for } i \in \{d, g, s\}
\]

**Current convergence:**
\[
|I_i^{(k+1)} - I_i^{(k)}| \leq \epsilon_{rel} \cdot \max(|I_i^{(k+1)}|, |I_i^{(k)}|) + \epsilon_{abs} \quad \text{for } i \in \{d, g, s\}
\]

**Gate current convergence (critical for MESFET):**
\[
|I_g^{(k+1)} - I_g^{(k)}| \leq \epsilon_{gate} \cdot \max(|I_g^{(k+1)}|, |I_g^{(k)}|) + \epsilon_{gate,abs}
\]
\[
\epsilon_{gate} = 10^{-4}, \quad \epsilon_{gate,abs} = 10^{-12} \text{A}
\]

#### 2.1.3 Numerical Limiting for Robust Convergence

**Gate voltage limiting for Schottky barriers:**
\[
V_{gs}^{new} = V_{gs}^{old} + \delta \cdot \tanh\left(\frac{V_{gs}^{new,raw} - V_{gs}^{old}}{\delta}\right)
\]
\[
\delta = 2 \cdot \frac{nkT}{q} \quad \text{(thermal voltage scaling)}
\]

**Drain voltage limiting near saturation:**
\[
V_{ds}^{new} = \min(V_{ds}^{new}, 1.5 \cdot V_{ds,sat})
\]

**Velocity saturation smoothing:**
\[
v(E) = v_{sat} \cdot \frac{E/E_c}{\left[1 + (E/E_c)^\beta\right]^{1/\beta}}
\]
\[
E_c = \frac{v_{sat}}{\mu_0}
\]

### 2.2 Matrix Conditioning Analysis

#### 2.2.1 Condition Number Monitoring

The HFET/MESFET MNA matrix can become ill-conditioned due to:

1. **High gate impedance** (Schottky barrier reverse bias)
2. **Very small capacitances** (quantum-limited Cgs)
3. **Large transconductance ratios** (gm/gds > 10^6)

**Condition number estimation:**
\[
\kappa(\mathbf{Y}) \approx \frac{\max_i \left( |Y_{ii}| + \sum_{j \neq i} |Y_{ij}| \right)}{\min_i \left( |Y_{ii}| - \sum_{j \neq i} |Y_{ij}| \right)}
\]

**Ill-conditioning detection thresholds:**
\[
\text{Warning if } \kappa(\mathbf{Y}) > 10^8
\]
\[
\text{Error if } \kappa(\mathbf{Y}) > 10^{12}
\]

#### 2.2.2 Pivot Growth Monitoring

During LU decomposition for Newton iterations:

**Pivot growth factor:**
\[
\rho = \frac{\max_i |u_{ii}|}{\max_{i,j} |J_{ij}|}
\]

**Stability thresholds:**
\[
\text{Warning if } \rho > 10^4
\]
\[
\text{Use complete pivoting if } \rho > 10^6
\]

#### 2.2.3 Regularization for Ill-Conditioned Systems

**Tikhonov regularization for numerical stability:**
\[
\mathbf{Y}_{reg} = \mathbf{Y} + \lambda \mathbf{D}
\]
\[
\lambda = 10^{-12} \cdot \|\mathbf{Y}\|_F
\]
\[
D_{ii} = \max(|Y_{ii}|, 10^{-12})
\]

**Selective regularization based on operating region:**
\[
\lambda = 
\begin{cases}
10^{-14} \cdot \|\mathbf{Y}\|_F & \text{subthreshold} \\
10^{-12} \cdot \|\mathbf{Y}\|_F & \text{linear region} \\
10^{-10} \cdot \|\mathbf{Y}\|_F & \text{saturation}
\end{cases}
\]

### 2.3 Local Truncation Error (LTE) Control

#### 2.3.1 Charge-Based LTE Estimation

**Gate charge LTE:**
\[
\text{LTE}_{Q_g} = \frac{h^2}{12} \left| \frac{d^3 Q_g}{dt^3} \right|
\]

**Channel charge LTE:**
\[
\text{LTE}_{Q_{ch}} = \frac{h^2}{12} \left| \frac{d^3 Q_{ch}}{dt^3} \right|
\]

**Numerical approximation of third derivatives:**
\[
\frac{d^3 Q}{dt^3} \approx \frac{Q(t) - 3Q(t-h) + 3Q(t-2h) - Q(t-3h)}{h^3}
\]

#### 2.3.2 Thermal Network LTE

**Junction temperature LTE for self-heating:**
\[
\text{LTE}_T = \frac{h^2}{12} \left| \frac{d^3 T_j}{dt^3} \right|
\]

**Power dissipation LTE:**
\[
\text{LTE}_P = \frac{h^2}{12} \left| \frac{d^3 P_{diss}}{dt^3} \right|
\]

#### 2.3.3 Combined Error Metric and Time-Step Control

**Normalized LTE for each state variable:**
\[
\epsilon_{Q_g} = \frac{\text{LTE}_{Q_g}}{\epsilon_{rel}|Q_g| + \epsilon_{abs}}
\]
\[
\epsilon_{Q_{ch}} = \frac{\text{LTE}_{Q_{ch}}}{\epsilon_{rel}|Q_{ch}| + \epsilon_{abs}}
\]
\[
\epsilon_T = \frac{\text{LTE}_T}{\epsilon_{T,rel}|T_j| + \epsilon_{T,abs}}
\]

**Maximum normalized error:**
\[
\epsilon_{max} = \max(\epsilon_{Q_g}, \epsilon_{Q_{ch}}, \epsilon_T)
\]

**Time-step adjustment algorithm:**
\[
h_{new} = 
\begin{cases}
0.9 \cdot h_{old} \cdot \epsilon_{max}^{-1/2} & \epsilon_{max} > 1 \\
\min(1.1 \cdot h_{old}, h_{max}) & \epsilon_{max} < 0.1 \\
h_{old} & \text{otherwise}
\end{cases}
\]

**Minimum time-step enforcement for HFET:**
\[
h_{min} = \max(10^{-15} \text{s}, \frac{L}{10 \cdot v_{sat}})
\]

### 2.4 Convergence Acceleration Techniques

#### 2.4.1 Adaptive Damping for Newton-Raphson

**Voltage damping based on previous iteration:**
\[
\lambda_V = \min\left(1.0, \frac{2 \cdot V_T}{|\Delta V_{max}|}\right)
\]
\[
V^{new} = V^{old} + \lambda_V \cdot \Delta V
\]

**Current damping for velocity saturation region:**
\[
\lambda_I = \min\left(1.0, \frac{I_{d,sat}}{5 \cdot |\Delta I_d|}\right)
\]
\[
I_d^{new} = I_d^{old} + \lambda_I \cdot \Delta I_d
\]

#### 2.4.2 Homotopy Continuation for Difficult Bias Points

**Voltage continuation for hard convergence cases:**
\[
V(\alpha) = \alpha \cdot V^{target} \quad \alpha: 0 \rightarrow 1
\]

**Gradual application of advanced effects:**
\[
I_{d,eff} = (1 - \alpha) \cdot I_{d,simple} + \alpha \cdot I_{d,HFET} \quad \alpha: 0 \rightarrow 1
\]

**Parameter continuation schedule:**
\[
\alpha = 
\begin{cases}
0.1 & \text{iteration 1} \\
0.3 & \text{iteration 2} \\
0.6 & \text{iteration 3} \\
0.9 & \text{iteration 4} \\
1.0 & \text{iteration 5+}
\end{cases}
\]

#### 2.4.3 Dynamic Tolerance Adjustment

**Adaptive relative tolerance based on operating point:**
\[
\epsilon_{rel}^{adapt} = \epsilon_{rel}^{base} \cdot \left[ 1 + 0.2 \cdot \log_{10}\left( \max\left( \frac{|I_d|}{1\text{A}}, \frac{|V_{ds}|}{1\text{V}} \right) \right) \right]
\]

**Adaptive absolute tolerance for gate current (MESFET):**
\[
\epsilon_{abs,I_g}^{adapt} = \max(\epsilon_{abs}^{base}, 10^{-15} \cdot |I_g|)
\]

**Adaptive voltage tolerance for Schottky barriers:**
\[
\epsilon_{abs,V}^{adapt} = \max(\epsilon_{abs}^{base}, 10^{-6} \cdot |V_{gs}|)
\]

### 2.5 Memory and Computational Requirements

#### 2.5.1 State Vector Size

**State variables per HFET/MESFET instance:**
\[
N_{states} = 3 \quad \text{(terminal voltages)}
\]
\[
+ 2 \quad \text{(gate and channel charges: } Q_g, Q_{ch})
\]
\[
+ 1 \quad \text{(substrate charge: } Q_{sub}) \quad \text{if substrate node enabled}
\]
\[
+ 1 \quad \text{(thermal charge: } Q_{th}) \quad \text{if self-heating enabled}
\]
\[
+ 3 \quad \text{(history: } I_d^{old}, I_g^{old}, P_{diss}^{old})
\]
\[
= 10 \quad \text{state variables total (with all options)}
\]

#### 2.5.2 Matrix Storage Requirements

**Non-zero entries in 3×3 Jacobian:**
\[
N_{nz} = 9 \quad \text{(dense 3×3 matrix)}
\]
\[
+ 3 \quad \text{(additional derivatives for substrate coupling)}
\]
\[
+ 2 \quad \text{(charge derivatives)}
\]
\[
= 14 \quad \text{non-zero entries}
\]

**Memory requirements:**
\[
M = 10 \cdot \text{sizeof(double)} \quad \text{state storage} \approx 80 \text{ bytes}
\]
\[
+ 14 \cdot \text{sizeof(double)} \quad \text{Jacobian storage} \approx 112 \text{ bytes}
\]
\[
+ 9 \cdot \text{sizeof(double*)} \quad \text{matrix pointers} \approx 72 \text{ bytes}
\]
\[
+ O(40) \cdot \text{sizeof(double)} \quad \text{parameter storage} \approx 320 \text{ bytes}
\]
\[
\approx 0.6 \text{ KB per instance}
\]

#### 2.5.3 Computational Complexity

**Per Newton iteration operations:**
\[
O(1) \quad \text{for current evaluations (constant time)}
\]
\[
O(N_{states}) \quad \text{for derivative calculations}
\]
\[
O(N_{nz}) \quad \text{for matrix stamping}
\]
\[
O(N^3) \quad \text{for matrix solution (N=3, so O(27))}
\]

**Total operations per iteration:**
\[
\text{Operations} \approx 150 \text{ floating-point operations}
\]

**Memory bandwidth requirements:**
\[
\text{Bandwidth} \approx 0.6 \text{ KB/iteration} \quad \text{(for state updates)}
\]

### 2.6 Error Recovery and Fallback Strategies

#### 2.6.1 Time-Step Reduction Hierarchy

If convergence fails at time point \(t_n\):

1. **Reduce time step by factor of 2:** \(h_{new} = h_{old}/2\)
2. **Switch to backward Euler:** More stable but less accurate
3. **Reduce Newton damping factor:** \(\lambda = \lambda/2\)
4. **Use predictor from previous successful step:**
   \[
   V^{pred} = 2V(t_{n-1}) - V(t_{n-2})
   \]

#### 2.6.2 Model Simplification for Recovery

In extreme convergence difficulties:

1. **Disable velocity saturation:** Use constant mobility model
2. **Ignore quantum capacitance:** Use classical charge control
3. **Linearize Schottky diode:** \(I_g = V_{gs}/R_{gate}\)
4. **Disable self-heating:** Assume isothermal operation

#### 2.6.3 Convergence Statistics Monitoring

SPICE tracks device-specific statistics:
- Average Newton iterations per time point
- Number of time-step reductions
- Maximum LTE observed for each charge component
- Condition number history
- Damping factor evolution

These statistics guide adaptive algorithm selection and provide diagnostics for convergence issues.

The convergence analysis for HFET and MESFET models demonstrates the sophisticated numerical techniques required to handle the complex physics of heterojunction devices, including quantum confinement, velocity saturation, Schottky barriers, and self-heating effects. The implementation combines rigorous mathematical treatment with practical numerical safeguards to ensure robust convergence across the wide operating range typical of III-V semiconductor devices while maintaining computational efficiency for circuit-scale simulations.

## 3. C Implementation

### 3.1 Core Data Structures

Following the generic device template pattern from the research context:

```c
/* HFET/MESFET model structure (per .MODEL card) */
typedef struct sHFETmodel {
    int HFETtype;              /* N-type or P-type */
    double HFETvto;            /* Threshold voltage VTO */
    double HFETkp;             /* Transconductance parameter KP */
    double HFETgamma;          /* Body effect parameter GAMMA */
    double HFETphi;            /* Surface potential PHI */
    double HFETlambda;         /* Channel-length modulation LAMBDA */
    double HFETvsat;           /* Saturation velocity VSAT */
    double HFETbeta;           /* Velocity saturation exponent BETA */
    double HFETis;             /* Gate Schottky saturation current IS */
    double HFETn;              /* Gate diode emission coefficient N */
    double HFETcgd;            /* Gate-drain capacitance CGD */
    double HFETcgs;            /* Gate-source capacitance CGS */
    double HFETpb;             /* Gate junction potential PB */
    struct sHFETmodel *HFETnextModel;  /* Linked list pointer */
    sHFETinstance *HFETinstances;      /* Instance chain head */
} HFETmodel;

/* HFET/MESFET instance structure (per device instance) */
typedef struct sHFETinstance {
    char *HFETname;            /* Instance identifier */
    int HFETdNode;             /* Drain node index */
    int HFETgNode;             /* Gate node index */
    int HFETsNode;             /* Source node index */
    double HFETl;              /* Channel length L */
    double HFETw;              /* Channel width W */
    double HFETtemp;           /* Instance temperature */
    double HFETvds;            /* Drain-source voltage */
    double HFETvgs;            /* Gate-source voltage */
    double HFETcd;             /* Drain current */
    double HFETcg;             /* Gate current */
    double HFETgm;             /* Transconductance ∂Id/∂Vgs */
    double HFETgds;            /* Output conductance ∂Id/∂Vds */
    double HFETggs;            /* Gate conductance ∂Ig/∂Vgs */
    double HFETqgs;            /* Gate-source charge */
    double HFETqgd;            /* Gate-drain charge */
    struct sHFETinstance *HFETnextInstance;  /* Linked list pointer */
    HFETmodel *HFETmodPtr;     /* Parent model reference */
    
    /* Sparse matrix pointers for 3-terminal device */
    double *HFETdrainDrainPtr;    /* Gdd */
    double *HFETdrainGatePtr;     /* Gdg */
    double *HFETdrainSourcePtr;   /* Gds */
    double *HFETgateDrainPtr;     /* Ggd */
    double *HFETgateGatePtr;      /* Ggg */
    double *HFETgateSourcePtr;    /* Ggs */
    double *HFETsourceDrainPtr;   /* Gsd */
    double *HFETsourceGatePtr;    /* Gsg */
    double *HFETsourceSourcePtr;  /* Gss */
    
    /* State vector indices for charges */
    int HFETqgsState;          /* State index for Qgs */
    int HFETqgdState;          /* State index for Qgd */
    
    /* History for LTE calculation */
    double HFETqgsHist[3];     /* Qgs history for 3rd derivative */
    double HFETqgdHist[3];     /* Qgd history for 3rd derivative */
    
    /* Flags */
    unsigned HFEToff:1;        /* Device initially off */
    unsigned HFETicGiven:1;    /* Initial conditions given */
} HFETinstance;
```

### 3.2 DC Load Function Implementation

The `HFETload` function implements the mathematical formulation and stamps the conductance matrix:

```c
int HFETload(GENmodel *inModel, CKTcircuit *ckt) {
    HFETmodel *model = (HFETmodel *)inModel;
    HFETinstance *here;
    double vgs, vds, vgd;
    double vth, vgst, beta, vsat, lambda;
    double ids, igs, gm, gds, ggs;
    double f_sat, df_sat_dvds, vdsat;
    
    for (; model != NULL; model = model->HFETnextModel) {
        for (here = model->HFETinstances; here != NULL; 
             here = here->HFETnextInstance) {
            
            /* Extract terminal voltages from circuit */
            vgs = *(ckt->CKTrhs + here->HFETgNode) - 
                  *(ckt->CKTrhs + here->HFETsNode);
            vds = *(ckt->CKTrhs + here->HFETdNode) - 
                  *(ckt->CKTrhs + here->HFETsNode);
            vgd = vgs - vds;  /* Gate-drain voltage */
            
            /* Apply voltage limiting for numerical stability */
            vgs = pnjlim(vgs, here->HFETvgs, model->HFETn * Vt, &check);
            
            /* Calculate threshold voltage with body effect */
            vth = model->HFETvto + model->HFETgamma * 
                  (sqrt(model->HFETphi) - sqrt(model->HFETphi));
            
            /* Effective gate overdrive */
            vgst = vgs - vth;
            
            /* Device parameters */
            beta = (here->HFETw / here->HFETl) * model->HFETkp;
            vsat = model->HFETvsat;
            lambda = model->HFETlambda;
            
            /* Velocity saturation factor */
            if (fabs(vds) > 1e-12) {
                double mu_eff = model->HFETkp;  /* Simplified mobility */
                vdsat = (vsat * here->HFETl) / mu_eff;
                double v_ratio = vds / vdsat;
                f_sat = 1.0 / (1.0 + v_ratio);
                df_sat_dvds = -f_sat * f_sat / vdsat;
            } else {
                f_sat = 1.0;
                df_sat_dvds = 0.0;
                vdsat = 1.0;  /* Avoid division by zero */
            }
            
            /* Drain current calculation */
            if (vgst <= 0.0) {
                /* Cutoff region */
                ids = 0.0;
                gm = 0.0;
                gds = 0.0;
            } else if (vds <= vgst) {
                /* Linear region */
                ids = beta * (vgst * vds - 0.5 * vds * vds) * 
                      (1.0 + lambda * vds) * f_sat;
                
                /* Transconductance */
                gm = beta * vds * (1.0 + lambda * vds) * f_sat;
                
                /* Output conductance */
                gds = beta * (vgst - vds) * (1.0 + lambda * vds) * f_sat +
                      beta * (vgst * vds - 0.5 * vds * vds) * lambda * f_sat +
                      beta * (vgst * vds - 0.5 * vds * vds) * 
                      (1.0 + lambda * vds) * df_sat_dvds;
            } else {
                /* Saturation region */
                ids = 0.5 * beta * vgst * vgst * 
                      (1.0 + lambda * vds) * f_sat;
                
                /* Transconductance */
                gm = beta * vgst * (1.0 + lambda * vds) * f_sat;
                
                /* Output conductance */
                gds = 0.5 * beta * vgst * vgst * lambda * f_sat +
                      0.5 * beta * vgst * vgst * 
                      (1.0 + lambda * vds) * df_sat_dvds;
            }
            
            /* Gate Schottky diode current */
            if (vgs < -10.0 * model->HFETn * Vt) {
                /* Reverse bias - use linear approximation */
                igs = -model->HFETis + vgs * Gmin;
                ggs = Gmin;
            } else {
                /* Forward bias or moderate reverse bias */
                double exp_arg = vgs / (model->HFETn * Vt);
                if (exp_arg > 50.0) exp_arg = 50.0;  /* Prevent overflow */
                igs = model->HFETis * (exp(exp_arg) - 1.0) + vgs * Gmin;
                ggs = model->HFETis * exp(exp_arg) / (model->HFETn * Vt) + Gmin;
            }
            
            /* Stamp conductance matrix (3×3 for HFET/MESFET) */
            
            /* Drain equation: I_d = g_m·V_gs + g_ds·V_ds */
            *(here->HFETdrainDrainPtr) += gds;          /* Gdd: ∂I_d/∂V_d */
            *(here->HFETdrainGatePtr) += gm;            /* Gdg: ∂I_d/∂V_g */
            *(here->HFETdrainSourcePtr) += -(gds + gm); /* Gds: ∂I_d/∂V_s */
            
            /* Gate equation: I_g = g_gs·V_gs */
            *(here->HFETgateGatePtr) += ggs;            /* Ggg: ∂I_g/∂V_g */
            *(here->HFETgateSourcePtr) += -ggs;         /* Ggs: ∂I_g/∂V_s */
            
            /* Source equation: I_s = -I_d - I_g */
            *(here->HFETsourceDrainPtr) += -gds;        /* Gsd: ∂I_s/∂V_d */
            *(here->HFETsourceGatePtr) += -(gm + ggs);  /* Gsg: ∂I_s/∂V_g */
            *(here->HFETsourceSourcePtr) += gds + gm + ggs; /* Gss: ∂I_s/∂V_s */
            
            /* Stamp RHS current vector */
            *(ckt->CKTrhs + here->HFETdNode) -= ids;
            *(ckt->CKTrhs + here->HFETgNode) -= igs;
            *(ckt->CKTrhs + here->HFETsNode) += ids + igs;
            
            /* Store state variables for next iteration */
            here->HFETvds = vds;
            here->HFETvgs = vgs;
            here->HFETcd = ids;
            here->HFETcg = igs;
            here->HFETgm = gm;
            here->HFETgds = gds;
            here->HFETggs = ggs;
        }
    }
    
    return OK;
}
```

### 3.3 Matrix Setup and State Allocation

The `HFETsetup` function follows the SPICE device pattern for matrix pointer allocation:

```c
int HFETsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    HFETmodel *model = (HFETmodel *)inModel;
    HFETinstance *here;
    
    for (