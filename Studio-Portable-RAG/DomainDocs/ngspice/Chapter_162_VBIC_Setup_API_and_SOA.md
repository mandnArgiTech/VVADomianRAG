# VBIC BJT: Matrix Topology, API, and Safe Operating Area

_Generated 2026-04-13 01:13 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbic.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicdest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vbic/vbicsoachk.c`

# Chapter: VBIC BJT: Matrix Topology, API, and Safe Operating Area

## Technical Introduction

The VBIC (Vertical Bipolar Inter-Company) model represents the state-of-the-art in bipolar junction transistor simulation, extending the Gummel-Poon framework with critical effects for modern power and RF devices: quasi-saturation, self-heating, avalanche multiplication, and substrate parasitics. Within Ngspice, this advanced physics is implemented through a coordinated suite of C files that manage the complete device lifecycle—from parameter parsing and matrix topology definition to numerical integration and safe operating area protection.

The implementation architecture centers on `vbicsetup.c`, which establishes the 4×4 (or 5×5 with thermal node) Modified Nodal Analysis matrix topology by allocating sparse matrix pointers for all terminal combinations. This file works in concert with `vbicmask.c` to define parameter masks for simulation control and `vbicask.c` to provide query access to internal device states. The initialization system in `vbicinit.c` registers the device with Ngspice's SPICEdev API, while `vbic.c` serves as the main entry point containing the `VBICinfo` structure that binds all device functions. Memory lifecycle management is handled by `vbicdel.c` (instance deletion), `vbicmdel.c` (model deletion), and `vbicdest.c` (destruction cleanup). Crucially, `vbicsoachk.c` implements real-time safe operating area checking, protecting against electrical overstress during simulation. Together, these files implement a production-grade VBIC model that balances numerical robustness with computational efficiency, handling the complex interactions between electrical, thermal, and reliability domains within SPICE's Newton-Raphson framework.

## 1. Mathematical Formulation

### 1.1 Modified Nodal Analysis Matrix Topology for VBIC BJT

The VBIC BJT model implements a sophisticated 4-terminal (or 5-terminal with thermal node) Modified Nodal Analysis (MNA) formulation that accounts for the intrinsic transistor, substrate transistor, and optional thermal network.

#### 1.1.1 Basic 4-Terminal MNA Formulation

For the standard VBIC model without self-heating, the MNA matrix has the following structure:

**Terminal ordering:** Collector (c), Base (b), Emitter (e), Substrate (s)

**Conductance matrix stamp:**
\[
\begin{bmatrix}
Y_{cc} & Y_{cb} & Y_{ce} & Y_{cs} \\
Y_{bc} & Y_{bb} & Y_{be} & Y_{bs} \\
Y_{ec} & Y_{eb} & Y_{ee} & Y_{es} \\
Y_{sc} & Y_{sb} & Y_{se} & Y_{ss}
\end{bmatrix}
\begin{bmatrix}
V_c \\ V_b \\ V_e \\ V_s
\end{bmatrix}
=
\begin{bmatrix}
I_c \\ I_b \\ I_e \\ I_s
\end{bmatrix}
\]

**Matrix elements from small-signal parameters:**
\[
Y_{cc} = g_{ce} + g_{cb} + j\omega(C_{bc} + C_{cs})
\]
\[
Y_{cb} = -g_{cb} - j\omega C_{bc}
\]
\[
Y_{ce} = -g_{ce}
\]
\[
Y_{cs} = -j\omega C_{cs}
\]
\[
Y_{bb} = g_{be} + g_{cb} + g_{bs} + j\omega(C_{be} + C_{bc} + C_{bs})
\]
\[
Y_{be} = -g_{be} - j\omega C_{be}
\]
\[
Y_{bs} = -g_{bs} - j\omega C_{bs}
\]
\[
Y_{ee} = g_{ce} + g_{be} + j\omega C_{be}
\]
\[
Y_{ss} = g_{bs} + j\omega(C_{cs} + C_{bs})
\]

Where:
- \(g_{be} = \partial I_b/\partial V_{be}\) (base-emitter conductance)
- \(g_{cb} = \partial I_c/\partial V_{bc}\) (base-collector conductance)
- \(g_{ce} = \partial I_c/\partial V_{ce}\) (collector-emitter conductance)
- \(g_{bs} = \partial I_s/\partial V_{bs}\) (substrate conductance)
- \(C_{be}, C_{bc}, C_{cs}, C_{bs}\) are the corresponding capacitances

#### 1.1.2 Extended 5-Terminal Formulation with Thermal Network

When self-heating is enabled, the thermal node (t) is added, creating a 5×5 MNA system:

**Extended matrix structure:**
\[
\begin{bmatrix}
Y_{cc} & Y_{cb} & Y_{ce} & Y_{cs} & Y_{ct} \\
Y_{bc} & Y_{bb} & Y_{be} & Y_{bs} & Y_{bt} \\
Y_{ec} & Y_{eb} & Y_{ee} & Y_{es} & Y_{et} \\
Y_{sc} & Y_{sb} & Y_{se} & Y_{ss} & Y_{st} \\
Y_{tc} & Y_{tb} & Y_{te} & Y_{ts} & Y_{tt}
\end{bmatrix}
\begin{bmatrix}
V_c \\ V_b \\ V_e \\ V_s \\ V_t
\end{bmatrix}
=
\begin{bmatrix}
I_c \\ I_b \\ I_e \\ I_s \\ I_t
\end{bmatrix}
\]

**Thermal node equations:**
\[
Y_{tt} = \frac{1}{R_{th}} + j\omega C_{th}
\]
\[
Y_{tc} = -\frac{\partial P_{diss}}{\partial V_c}, \quad Y_{tb} = -\frac{\partial P_{diss}}{\partial V_b}, \quad Y_{te} = -\frac{\partial P_{diss}}{\partial V_e}, \quad Y_{ts} = -\frac{\partial P_{diss}}{\partial V_s}
\]
\[
Y_{ct} = \frac{\partial I_c}{\partial T_j}, \quad Y_{bt} = \frac{\partial I_b}{\partial T_j}, \quad Y_{et} = \frac{\partial I_e}{\partial T_j}, \quad Y_{st} = \frac{\partial I_s}{\partial T_j}
\]

**Power dissipation derivatives:**
\[
\frac{\partial P_{diss}}{\partial V_c} = I_c + V_{ce}\frac{\partial I_c}{\partial V_c} + V_{be}\frac{\partial I_b}{\partial V_c}
\]
\[
\frac{\partial P_{diss}}{\partial V_b} = V_{ce}\frac{\partial I_c}{\partial V_b} + I_b + V_{be}\frac{\partial I_b}{\partial V_b}
\]
\[
\frac{\partial P_{diss}}{\partial V_e} = -I_c + V_{ce}\frac{\partial I_c}{\partial V_e} - I_b + V_{be}\frac{\partial I_b}{\partial V_e}
\]

#### 1.1.3 Series Resistance Inclusion

The VBIC model includes extrinsic resistances that modify the internal node voltages:

**Internal base-emitter voltage:**
\[
V_{b'e'} = V_b - V_e - I_b \cdot R_{bx} - (I_b + I_c) \cdot R_e
\]

**Internal base-collector voltage:**
\[
V_{b'c'} = V_b - V_c - I_b \cdot R_{bx} - I_c \cdot R_{cx}
\]

**Internal collector-emitter voltage:**
\[
V_{c'e'} = V_c - V_e - I_c \cdot (R_{cx} + R_e) - I_b \cdot R_e
\]

These internal voltages are used in all current and capacitance calculations, requiring additional Jacobian terms for the resistance derivatives.

### 1.2 Advanced Current Formulations

#### 1.2.1 Modified Gummel-Poon with VBIC Extensions

**Forward transport current with high-injection correction:**
\[
I_{tf} = \frac{I_S \left[ \exp\left(\frac{V_{b'e'}}{N_F V_T}\right) - \exp\left(\frac{V_{b'c'}}{N_R V_T}\right) \right]}{Q_b}
\]
\[
Q_b = \frac{1}{2} \left[ 1 + \frac{V_{b'c'}}{V_{AF}} + \sqrt{\left(1 + \frac{V_{b'c'}}{V_{AF}}\right)^2 + 4\frac{I_{tf}}{I_{KF}}} \right]
\]

**Reverse transport current:**
\[
I_{tr} = \frac{I_S \left[ \exp\left(\frac{V_{b'c'}}{N_R V_T}\right) - 1 \right]}{Q_b}
\]

**Non-ideal base currents:**
\[
I_{be} = I_{SE} \left[ \exp\left(\frac{V_{b'e'}}{N_E V_T}\right) - 1 \right]
\]
\[
I_{bc} = I_{SC} \left[ \exp\left(\frac{V_{b'c'}}{N_C V_T}\right) - 1 \right]
\]

#### 1.2.2 Quasi-Saturation Model

**Collector current in quasi-saturation:**
\[
I_{C,qs} = I_{QS0} \cdot \tanh\left(\frac{V_k}{V_T}\right) \cdot \left(1 + \lambda V_{ce}\right)
\]
\[
I_{QS0} = I_{QS} \cdot \left[ \exp\left(\frac{V_{bc}}{N_{QS} V_T}\right) - 1 \right]
\]
\[
V_k = V_{K0} \cdot \left[ 1 + \theta \left(T_j - T_{nom}\right) \right]
\]

#### 1.2.3 Avalanche Multiplication (Kirk Effect)

**Avalanche multiplication factor:**
\[
M = \frac{1}{1 - \left(\frac{V_{bc}}{BV}\right)^n} \quad \text{for } V_{bc} < BV
\]
\[
M \to \infty \quad \text{for } V_{bc} \geq BV
\]

**Avalanche current:**
\[
I_{avl} = (M - 1) \cdot I_{cc}
\]
\[
I_{cc} = I_{tf} - I_{tr}
\]

#### 1.2.4 Substrate Transistor Current

**Substrate diode current:**
\[
I_{sub} = I_{S,sub} \left[ \exp\left(\frac{V_{bs}}{N_{S} V_T}\right) - 1 \right] + I_{SC,sub} \left[ \exp\left(\frac{V_{bs}}{N_{C,sub} V_T}\right) - 1 \right]
\]

### 1.3 Charge Storage Formulation

#### 1.3.1 Depletion Charges with Bias Dependence

**Base-emitter depletion charge:**
\[
Q_{je} = 
\begin{cases}
C_{JE0} \cdot V_{JE} \cdot \frac{1 - \left(1 - \frac{V_{be}}{V_{JE}}\right)^{1-M_{JE}}}{1 - M_{JE}} & V_{be} < F_C \cdot V_{JE} \\
C_{JE0} \cdot \left[ \frac{1 - F_C^{1-M_{JE}}}{1 - M_{JE}} + \frac{V_{be} - F_C \cdot V_{JE}}{V_{JE}(1 - F_C)^{-M_{JE}}} \right] & V_{be} \geq F_C \cdot V_{JE}
\end{cases}
\]

**Base-collector depletion charge:**
\[
Q_{jc} = 
\begin{cases}
C_{JC0} \cdot V_{JC} \cdot \frac{1 - \left(1 - \frac{V_{bc}}{V_{JC}}\right)^{1-M_{JC}}}{1 - M_{JC}} & V_{bc} < F_C \cdot V_{JC} \\
C_{JC0} \cdot \left[ \frac{1 - F_C^{1-M_{JC}}}{1 - M_{JC}} + \frac{V_{bc} - F_C \cdot V_{JC}}{V_{JC}(1 - F_C)^{-M_{JC}}} \right] & V_{bc} \geq F_C \cdot V_{JC}
\end{cases}
\]

#### 1.3.2 Diffusion Charges

**Forward diffusion charge:**
\[
Q_{df} = \tau_F \cdot I_{tf}
\]

**Reverse diffusion charge:**
\[
Q_{dr} = \tau_R \cdot I_{tr}
\]

**Total charge for each junction:**
\[
Q_{be} = Q_{je} + Q_{df}
\]
\[
Q_{bc} = Q_{jc} + Q_{dr}
\]

### 1.4 Temperature Scaling Mathematics

#### 1.4.1 Temperature-Dependent Parameters

**Saturation current scaling:**
\[
I_S(T) = I_S(T_{nom}) \cdot \left(\frac{T}{T_{nom}}\right)^{X_{TI}} \cdot \exp\left[\frac{E_G}{q V_T} \cdot \left(\frac{T}{T_{nom}} - 1\right)\right]
\]

**Resistance scaling:**
\[
R(T) = R(T_{nom}) \cdot \left(\frac{T}{T_{nom}}\right)^{X_R}
\]

**Capacitance scaling:**
\[
C(T) = C(T_{nom}) \cdot \left(\frac{T}{T_{nom}}\right)^{X_C}
\]

**Built-in potential scaling:**
\[
V_J(T) = V_J(T_{nom}) \cdot \frac{T}{T_{nom}} - V_T \cdot 3 \cdot \ln\left(\frac{T}{T_{nom}}\right) + E_G \cdot \left(1 - \frac{T}{T_{nom}}\right)
\]

#### 1.4.2 Thermal Voltage Dependence

**Thermal voltage:**
\[
V_T(T) = \frac{kT}{q}
\]

**All exponential terms scale as:**
\[
\exp\left(\frac{V}{N V_T(T)}\right)
\]

## 2. Convergence Analysis

### 2.1 Newton-Raphson Convergence for VBIC Matrix System

The VBIC model's 4×4 (or 5×5) MNA matrix presents unique convergence challenges due to strong nonlinearities from multiple exponential junctions and thermal coupling.

#### 2.1.1 Jacobian Matrix Structure

The complete Jacobian for the VBIC model with self-heating includes derivatives of all terminal currents with respect to all node voltages and temperature:

**Jacobian matrix for 5-terminal system:**
\[
\mathbf{J} = 
\begin{bmatrix}
\frac{\partial I_c}{\partial V_c} & \frac{\partial I_c}{\partial V_b} & \frac{\partial I_c}{\partial V_e} & \frac{\partial I_c}{\partial V_s} & \frac{\partial I_c}{\partial V_t} \\
\frac{\partial I_b}{\partial V_c} & \frac{\partial I_b}{\partial V_b} & \frac{\partial I_b}{\partial V_e} & \frac{\partial I_b}{\partial V_s} & \frac{\partial I_b}{\partial V_t} \\
\frac{\partial I_e}{\partial V_c} & \frac{\partial I_e}{\partial V_b} & \frac{\partial I_e}{\partial V_e} & \frac{\partial I_e}{\partial V_s} & \frac{\partial I_e}{\partial V_t} \\
\frac{\partial I_s}{\partial V_c} & \frac{\partial I_s}{\partial V_b} & \frac{\partial I_s}{\partial V_e} & \frac{\partial I_s}{\partial V_s} & \frac{\partial I_s}{\partial V_t} \\
\frac{\partial I_t}{\partial V_c} & \frac{\partial I_t}{\partial V_b} & \frac{\partial I_t}{\partial V_e} & \frac{\partial I_t}{\partial V_s} & \frac{\partial I_t}{\partial V_t}
\end{bmatrix}
\]

**Key derivative calculations:**
\[
\frac{\partial I_c}{\partial V_c} = g_{ce} + g_{cb} + \frac{\partial I_{avl}}{\partial V_c} + \frac{\partial I_{qs}}{\partial V_c}
\]
\[
\frac{\partial I_c}{\partial V_b} = -g_{cb} + \frac{\partial I_{avl}}{\partial V_b} + \frac{\partial I_{qs}}{\partial V_b}
\]
\[
\frac{\partial I_c}{\partial V_e} = -g_{ce}
\]
\[
\frac{\partial I_c}{\partial V_t} = \frac{\partial I_c}{\partial T_j} \cdot \frac{\partial T_j}{\partial V_t} = \frac{\partial I_c}{\partial T_j} \quad (\text{since } V_t = \Delta T)
\]

**Thermal coupling derivatives:**
\[
\frac{\partial I_t}{\partial V_c} = -\frac{\partial P_{diss}}{\partial V_c} = - \left[ I_c + V_{ce} \frac{\partial I_c}{\partial V_c} + V_{be} \frac{\partial I_b}{\partial V_c} \right]
\]
\[
\frac{\partial I_t}{\partial V_b} = -\frac{\partial P_{diss}}{\partial V_b} = - \left[ V_{ce} \frac{\partial I_c}{\partial V_b} + I_b + V_{be} \frac{\partial I_b}{\partial V_b} \right]
\]
\[
\frac{\partial I_t}{\partial V_t} = \frac{1}{R_{th}} + j\omega C_{th}
\]

#### 2.1.2 Convergence Criteria

Ngspice implements comprehensive convergence testing for VBIC:

**Voltage convergence at all nodes:**
\[
|V_i^{(k+1)} - V_i^{(k)}| \leq \epsilon_{rel} \cdot \max(|V_i^{(k+1)}|, |V_i^{(k)}|) + \epsilon_{abs} \quad \text{for } i \in \{c, b, e, s, t\}
\]

**Current convergence:**
\[
|I_i^{(k+1)} - I_i^{(k)}| \leq \epsilon_{rel} \cdot \max(|I_i^{(k+1)}|, |I_i^{(k)}|) + \epsilon_{abs} \quad \text{for } i \in \{c, b, e, s\}
\]

**Temperature convergence (when self-heating enabled):**
\[
|T_j^{(k+1)} - T_j^{(k)}| \leq \epsilon_{T,rel} \cdot T_j^{(k)} + \epsilon_{T,abs}
\]
\[
\epsilon_{T,rel} = 10^{-4}, \quad \epsilon_{T,abs} = 0.1 \, \text{K}
\]

**Power convergence:**
\[
|P_{diss}^{(k+1)} - P_{diss}^{(k)}| \leq \epsilon_{P,rel} \cdot P_{diss}^{(k)} + \epsilon_{P,abs}
\]
\[
\epsilon_{P,rel} = 10^{-4}, \quad \epsilon_{P,abs} = 10^{-9} \, \text{W}
\]

#### 2.1.3 Numerical Limiting for Robust Convergence

**PN junction limiting for internal voltages:**
\[
V_{be}^{new} = \text{pnjlim}(V_{be}^{new}, V_{be}^{old}, N_F V_T, V_{crit}, \&limited)
\]
\[
V_{bc}^{new} = \text{pnjlim}(V_{bc}^{new}, V_{bc}^{old}, N_R V_T, V_{crit}, \&limited)
\]

**Critical voltage calculation:**
\[
V_{crit} = N \cdot V_T \cdot \ln\left(\frac{N \cdot V_T}{\sqrt{2} \cdot I_S}\right)
\]

**Quasi-saturation current limiting:**
\[
\Delta I_{C,qs} = \min\left(\Delta I_{C,qs}, \frac{I_{QS0}}{10}\right)
\]

**Avalanche current limiting:**
\[
I_{avl}^{new} = I_{avl}^{old} + \min\left(\Delta I_{avl}, \frac{I_{cc}}{5}\right)
\]

### 2.2 Matrix Conditioning Analysis

#### 2.2.1 Condition Number Monitoring

The VBIC MNA matrix can become ill-conditioned due to large conductance ratios:

**Condition number estimation via Gershgorin circles:**
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

During LU decomposition, pivot growth indicates numerical stability issues:

**Pivot growth factor:**
\[
\rho = \frac{\max_i |u_{ii}|}{\max_{i,j} |Y_{ij}|}
\]

**Stability thresholds:**
\[
\text{Warning if } \rho > 10^4
\]
\[
\text{Use complete pivoting if } \rho > 10^6
\]

#### 2.2.3 Regularization for Ill-Conditioned Systems

**Tikhonov regularization:**
\[
\mathbf{Y}_{reg} = \mathbf{Y} + \lambda \mathbf{I}
\]
\[
\lambda = 10^{-12} \cdot \|\mathbf{Y}\|_F
\]

**Selective regularization based on condition number:**
\[
\lambda = 
\begin{cases}
0 & \kappa(\mathbf{Y}) < 10^6 \\
10^{-10} \cdot \|\mathbf{Y}\|_F & 10^6 \leq \kappa(\mathbf{Y}) < 10^8 \\
10^{-8} \cdot \|\mathbf{Y}\|_F & \kappa(\mathbf{Y}) \geq 10^8
\end{cases}
\]

### 2.3 Local Truncation Error (LTE) Control

#### 2.3.1 Charge-Based LTE Estimation

**Base-emitter charge LTE:**
\[
\text{LTE}_{Q_{be}} = \frac{h^2}{12} \left| \frac{d^3 Q_{be}}{dt^3} \right|
\]

**Base-collector charge LTE:**
\[
\text{LTE}_{Q_{bc}} = \frac{h^2}{12} \left| \frac{d^3 Q_{bc}}{dt^3} \right|
\]

**Numerical approximation of third derivative:**
\[
\frac{d^3 Q}{dt^3} \approx \frac{Q(t) - 3Q(t-h) + 3Q(t-2h) - Q(t-3h)}{h^3}
\]

#### 2.3.2 Thermal Network LTE

**Temperature LTE for self-heating:**
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
\epsilon_{Q_{be}} = \frac{\text{LTE}_{Q_{be}}}{\epsilon_{rel}|Q_{be}| + \epsilon_{abs}}
\]
\[
\epsilon_{Q_{bc}} = \frac{\text{LTE}_{Q_{bc}}}{\epsilon_{rel}|Q_{bc}| + \epsilon_{abs}}
\]
\[
\epsilon_T = \frac{\text{LTE}_T}{\epsilon_{T,rel}|T_j| + \epsilon_{T,abs}}
\]

**Maximum normalized error:**
\[
\epsilon_{max} = \max(\epsilon_{Q_{be}}, \epsilon_{Q_{bc}}, \epsilon_T)
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

**Minimum time-step enforcement:**
\[
h_{new} = \max(h_{new}, h_{min})
\]
\[
h_{min} = 10^{-12} \, \text{s} \quad \text{(typical)}
\]

### 2.4 Safe Operating Area (SOA) Analysis

#### 2.4.1 Voltage Limit Checks

**Base-emitter voltage limit:**
\[
\text{Check: } |V_{be}| \leq V_{BE,max}
\]
\[
V_{BE,max} = \min(1.2 \, \text{V}, 0.7 \cdot BV_{EBO}) \quad \text{(typical)}
\]

**Base-collector voltage limit:**
\[
\text{Check: } |V_{bc}| \leq V_{BC,max}
\]
\[
V_{BC,max} = 0.8 \cdot BV_{CBO} \quad \text{(typical)}
\]

**Collector-emitter voltage limit:**
\[
\text{Check: } |V_{ce}| \leq V_{CE,max}
\]
\[
V_{CE,max} = 0.8 \cdot BV_{CEO} \quad \text{(typical)}
\]

**Collector-substrate voltage limit:**
\[
\text{Check: } |V_{cs}| \leq V_{CS,max}
\]
\[
V_{CS,max} = 0.8 \cdot BV_{CSU} \quad \text{(typical)}
\]

#### 2.4.2 Current Limit Checks

**Collector current limit:**
\[
\text{Check: } |I_c| \leq I_{C,max}
\]
\[
I_{C,max} = \min(I_{C,abs}, I_{C,soa})
\]

**Base current limit:**
\[
\text{Check: } |I_b| \leq I_{B,max}
\]
\[
I_{B,max} = \frac{I_{C,max}}{\beta_{min}}
\]

**SOA current derating with voltage:**
\[
I_{C,soa}(V_{ce}) = I_{C,max} \cdot \frac{V_{CE,max} - V_{ce}}{V_{CE,max} - V_{CE,sat}} \quad \text{for } V_{ce} > V_{CE,sat}
\]

#### 2.4.3 Power Dissipation Limits

**Maximum power dissipation:**
\[
\text{Check: } P_{diss} \leq P_{D,max}
\]

**Temperature-dependent derating:**
\[
P_{D,max}(T_j) = P_{D,max}(T_{j,max}) \cdot \frac{T_{j,max} - T_j}{T_{j,max} - T_{amb}} \quad \text{for } T_j > T_{amb}
\]

**Second breakdown limit:**
\[
\text{Check: } V_{ce} \cdot I_c \leq P_{SB}(V_{ce})
\]
\[
P_{SB}(V_{ce}) = P_{SB0} \cdot \left(1 - \frac{V_{ce}}{V_{CE,max}}\right) \quad \text{(linear approximation)}
\]

#### 2.4.4 Thermal Limits

**Maximum junction temperature:**
\[
\text{Check: } T_j \leq T_{j,max}
\]
\[
T_{j,max} = 150^\circ \text{C} \quad \text{(typical for silicon)}
\]

**Thermal runaway condition:**
\[
\text{Check: } \frac{\partial P_{diss}}{\partial T_j} \cdot R_{th} < 1
\]
\[
\frac{\partial P_{diss}}{\partial T_j} = V_{ce} \frac{\partial I_c}{\partial T_j} + V_{be} \frac{\partial I_b}{\partial T_j}
\]

#### 2.4.5 SOA Violation Response Strategies

**Warning thresholds:**
\[
\text{Warning if: } \frac{X}{X_{max}} > 0.8 \quad \text{for } X \in \{V_{be}, V_{bc}, V_{ce}, I_c, P_{diss}, T_j\}
\]

**Error thresholds:**
\[
\text{Error if: } \frac{X}{X_{max}} > 1.0 \quad \text{for } X \in \{V_{be}, V_{bc}, V_{ce}, I_c, P_{diss}, T_j\}
\]

**Automatic limiting for simulation stability:**
\[
I_c^{limited} = \min(I_c, 1.1 \cdot I_{C,max})
\]
\[
T_j^{limited} = \min(T_j, 1.1 \cdot T_{j,max})
\]

### 2.5 Convergence Acceleration Techniques

#### 2.5.1 Adaptive Damping

**Voltage damping factor:**
\[
\lambda_V = \min\left(1.0, \frac{2 \cdot V_T}{|\Delta V_{max}|}\right)
\]
\[
V^{new} = V^{old} + \lambda_V \cdot \Delta V
\]

**Current damping for quasi-saturation:**
\[
\lambda_I = \min\left(1.0, \frac{I_{QS0}}{5 \cdot |\Delta I_c|}\right)
\]
\[
I_c^{new} = I_c^{old} + \lambda_I \cdot \Delta I_c
\]

#### 2.5.2 Homotopy Continuation

**Voltage continuation for hard convergence cases:**
\[
V(\alpha) = \alpha \cdot V^{target} \quad \alpha: 0 \rightarrow 1
\]

**Gradual application of advanced effects:**
\[
I_{C,eff} = (1 - \alpha) \cdot I_{C,simple} + \alpha \cdot I_{C,VBIC} \quad \alpha: 0 \rightarrow 1
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

#### 2.5.3 Dynamic Tolerance Adjustment

**Adaptive relative tolerance:**
\[
\epsilon_{rel}^{adapt} = \epsilon_{rel}^{base} \cdot \left[ 1 + 0.2 \cdot \log_{10}\left( \max\left( \frac{|I_c|}{1\text{A}}, \frac{|V_{ce}|}{1\text{V}} \right) \right) \right]
\]

**Adaptive absolute tolerance for currents:**
\[
\epsilon_{abs,I}^{adapt} = \max(\epsilon_{abs}^{base}, 10^{-12} \cdot |I_c|)
\]

**Adaptive absolute tolerance for voltages:**
\[
\epsilon_{abs,V}^{adapt} = \max(\epsilon_{abs}^{base}, 10^{-9} \cdot |V_{ce}|)
\]

### 2.6 Memory and Computational Requirements

#### 2.6.1 State Vector Size

**State variables per VBIC instance:**
\[
N_{states} = 4 \quad \text{(terminal voltages)}
\]
\[
+ 2 \quad \text{(junction charges: } Q_{be}, Q_{bc})
\]
\[
+ 1 \quad \text{(substrate charge: } Q_{sub})
\]
\[
+ 2 \quad \text{(diffusion charges: } Q_{df}, Q_{dr})
\]
\[
+ 1 \quad \text{(thermal charge: } Q_{th}) \quad \text{if self-heating enabled}
\]
\[
+ 3 \quad \text{(history: } I_c^{old}, I_b^{old}, P_{diss}^{old})
\]
\[
= 13 \quad \text{state variables total (with self-heating)}
\]

#### 2.6.2 Matrix Storage Requirements

**Non-zero entries in 5×5 Jacobian:**
\[
N_{nz} = 25 \quad \text{(dense 5×5 matrix)}
\]
\[
+ 8 \quad \text{(additional derivatives for series resistances)}
\]
\[
+ 4 \quad \text{(charge derivatives)}
\]
\[
= 37 \quad \text{non-zero entries}
\]

**Memory requirements:**
\[
M = 13 \cdot \text{sizeof(double)} \quad \text{state storage} \approx 104 \text{ bytes}
\]
\[
+ 37 \cdot \text{sizeof(double)} \quad \text{Jacobian storage} \approx 296 \text{ bytes}
\]
\[
+ 16 \cdot \text{sizeof(double*)} \quad \text{matrix pointers} \approx 128 \text{ bytes}
\]
\[
+ O(60) \cdot \text{sizeof(double)} \quad \text{parameter storage} \approx 480 \text{ bytes}
\]
\[
\approx 1 \text{ KB per instance}
\]

#### 2.6.3 Computational Complexity

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
O(N^3) \quad \text{for matrix solution (N=5, so O(125))}
\]

**Total operations per iteration:**
\[
\text{Operations} \approx 200 \text{ floating-point operations}
\]

**Memory bandwidth requirements:**
\[
\text{Bandwidth} \approx 1 \text{ KB/iteration} \quad \text{(for state updates)}
\]

The convergence analysis for the VBIC BJT model demonstrates the sophisticated numerical techniques required to handle the complex interactions between electrical and thermal domains, multiple nonlinear effects, and the extended matrix topology. The implementation combines rigorous mathematical treatment with practical numerical safeguards to ensure robust convergence across the entire operating range while maintaining computational efficiency for circuit-scale simulations.

## 3. C Implementation

### 3.1 Core Data Structures and API Binding

The VBIC implementation in Ngspice centers around the `SPICEdev` API structure defined in `vbic.c`, which binds all device functions into the simulator's framework:

```c
/* File: vbic.c - Main device registration */
SPICEdev VBICinfo = {
    .DEVpublic = {
        .name = "VBIC",
        .description = "Vertical Bipolar Inter-Company BJT Model",
        .terms = 4,  /* Collector, Base, Emitter, Substrate */
        .numNames = 4,
        .termNames = (char *[]) {"c", "b", "e", "s"},
        .numInstanceParms = 2,  /* area, m */
        .instanceParms = (IFparm[]) {
            IOP("area", 1.0),
            IOP("m",    1.0)
        },
        .numModelParms = 42,  /* All VBIC model parameters */
        .modelParms = vbic_parms  /* Defined in vbicparam.c */
    },
    
    /* Function pointer assignments */
    .DEVparam = VBICparam,      /* Parameter processing - vbicparam.c */
    .DEVmodParam = VBICmParam,  /* Model parameter processing - vbicmpar.c */
    .DEVload = VBICload,        /* DC load - vbicload.c */
    .DEVsetup = VBICsetup,      /* Matrix setup - vbicsetup.c */
    .DEVunsetup = VBICunsetup,  /* Cleanup */
    .DEVpzSetup = VBICpzSetup,  /* Pole-zero setup */
    .DEVtemperature = VBICtemp, /* Temperature scaling - vbictemp.c */
    .DEVtrunc = VBICtrunc,      /* Truncation error - vbictrunc.c */
    .DEVfindBranch = NULL,
    .DEVacLoad = VBICacLoad,    /* AC analysis - vbicacld.c */
    .DEVaccept = NULL,
    .DEVdestroy = VBICdestroy,  /* Memory cleanup - vbicdest.c */
    .DEVmodDelete = VBICmDelete,/* Model deletion - vbicmdel.c */
    .DEVdelete = VBICdelete,    /* Instance deletion - vbicdel.c */
    .DEVsetic = VBICgetic,
    .DEVask = VBICask,          /* Query device state - vb