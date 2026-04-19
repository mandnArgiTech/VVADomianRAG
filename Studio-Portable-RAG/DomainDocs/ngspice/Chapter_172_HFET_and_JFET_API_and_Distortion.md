# HFET and JFET: Memory Lifecycle, Interfaces, and Distortion

_Generated 2026-04-13 03:40 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfet.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetgetic.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetinit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetitf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2ask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2getic.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2ext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2init.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2itf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfet.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetic.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetdist.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetdset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetinit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetitf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2ask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2ic.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2parm.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2ext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2init.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2itf.h`

# Chapter: HFET and JFET: Memory Lifecycle, Interfaces, and Distortion

## Technical Introduction

The Ngspice HFET (Heterojunction FET) and JFET device implementations constitute a sophisticated software architecture that translates semiconductor physics into SPICE-compatible circuit simulation. The 40+ source files referenced—including `hfet.c`, `jfet.c`, their initialization (`*init.c`), parameter mapping (`*mpar.c`, `*mask.c`), interface (`*itf.h`, `*ext.h`), and analysis modules (`*dist.c`, `*pzld.c`, `*ic.c`)—collectively implement a complete device modeling ecosystem. This architecture follows Ngspice's canonical pattern: a `SPICEdev` structure (`HFET1info`, `JFETinfo`) registers each device with the simulator kernel, binding mathematical models to numerical solvers through a well-defined API. The `*defs.h` files establish the memory footprint for model and instance structures, segregating process parameters (e.g., `HFETvt0`, `JFETbeta`) from runtime state (e.g., `HFETvgs`, `JFETids`). The `*setup.c`/`*load.c` functions map the device's nonlinear current-voltage relationships and their derivatives into the Modified Nodal Analysis (MNA) matrix via sparse matrix pointers (`SMPmakeElt`). Specialized modules handle temperature scaling (`*temp.c`), noise (`*noise.c`), distortion (`*dist.c`), and pole-zero analysis (`*pzld.c`), while the `*ask.c` and `*getic.c` files manage user interaction and initial conditions. The Parker-Skellern macro-model extensions (`jfet2*` files) augment the classic Shockley equations with high-injection, recombination, and DIBL effects. This entire codebase enforces charge conservation, manages dynamic memory allocation, and ensures numerical stability through limiting functions and adaptive time-stepping, enabling robust simulation of heterojunction and junction field-effect transistors within the broader SPICE framework.

## 1. Mathematical Formulation

The HFET (Heterojunction FET) and JFET models in Ngspice implement physics-based semiconductor equations coupled with empirical extensions for high-frequency and distortion analysis. The mathematical formulation integrates DC transport, AC small-signal response, charge dynamics, and nonlinear distortion effects within the SPICE Modified Nodal Analysis (MNA) framework.

### 1.1 Core DC Transport Equations

#### 1.1.1 HFET1 Basic Model (Shichman-Hodges Extension)

The fundamental drain current equations implement a continuous three-region model:

**Threshold Voltage Calculation:**
\[
V_{th} = V_{TO} \cdot \text{type}
\]
Where \( \text{type} = +1 \) for N-type, \( -1 \) for P-type devices.

**Effective Gate-Source Voltage:**
\[
V_{gst} = V_{gs} - V_{th}
\]

**Region Determination and Current Equations:**

1. **Subthreshold Region** (\( V_{gst} \leq 0 \)):
\[
I_d = \beta \cdot \exp\left(\frac{V_{gst}}{n \cdot V_t}\right) \cdot V_{ds} \cdot (1 + \lambda V_{ds})
\]
\[
g_m = \frac{I_d}{n \cdot V_t}, \quad g_{ds} = \beta \cdot \exp\left(\frac{V_{gst}}{n \cdot V_t}\right) \cdot (1 + 2\lambda V_{ds})
\]

2. **Linear/Triode Region** (\( 0 < V_{ds} \leq V_{gst} \)):
\[
I_d = \beta \cdot V_{gst} \cdot V_{ds} \cdot (1 + \lambda V_{ds})
\]
\[
g_m = \beta \cdot V_{ds} \cdot (1 + \lambda V_{ds}), \quad g_{ds} = \beta \cdot V_{gst} \cdot (1 + 2\lambda V_{ds})
\]

3. **Saturation Region** (\( V_{ds} > V_{gst} \)):
\[
I_d = \frac{\beta}{2} \cdot V_{gst}^2 \cdot (1 + \lambda V_{ds})
\]
\[
g_m = \beta \cdot V_{gst} \cdot (1 + \lambda V_{ds}), \quad g_{ds} = \frac{\beta}{2} \cdot V_{gst}^2 \cdot \lambda
\]

Where:
- \( \beta = \text{BETA} \cdot W/L \) (effective transconductance parameter)
- \( V_t = kT/q \) (thermal voltage)
- \( \lambda = \text{LAMBDA} \) (channel-length modulation)
- \( n = \text{N} \) (subthreshold slope factor)

#### 1.1.2 Parker-Skellern JFET2 Extended Model

The JFET2 model extends the basic equations with velocity saturation and DIBL effects:

**Effective Gate Voltage with DIBL:**
\[
V_{gst,eff} = V_{gs} - V_{TO} - \gamma \cdot V_{ds}
\]

**Velocity Saturation Factor:**
\[
F_{vsat} = \frac{1}{1 + V_{ds}/V_K}
\]

**Modified Current Equations:**

1. **Linear Region with Velocity Saturation:**
\[
I_d = \beta \cdot V_{gst,eff} \cdot V_{ds} \cdot F_{vsat} \cdot (1 + \lambda V_{ds})
\]

2. **Saturation Region:**
\[
V_{dsat} = \frac{V_{gst,eff}}{\alpha}
\]
\[
I_{dsat} = \frac{\beta}{2} \cdot \frac{V_{gst,eff}^2}{1 + V_{gst,eff}/V_K}
\]
\[
I_d = I_{dsat} \cdot (1 + \lambda V_{ds})
\]

Where:
- \( \alpha = \text{ALPHA} \) (saturation parameter)
- \( \gamma = \text{GAMMA} \) (DIBL coefficient)
- \( V_K = \text{VK} \) (knee voltage for velocity saturation)

#### 1.1.3 Gate Diode Equations (Schottky/PN Junction)

**Forward Bias Current:**
\[
I_{gs} = I_S \cdot \left[\exp\left(\frac{V_{gs}}{n \cdot V_t}\right) - 1\right] + \text{GMIN} \cdot V_{gs}
\]
\[
I_{gd} = I_S \cdot \left[\exp\left(\frac{V_{gd}}{n \cdot V_t}\right) - 1\right] + \text{GMIN} \cdot V_{gd}
\]

**JFET2 Recombination Current Extension:**
\[
I_{gs,rec} = I_{SR} \cdot \left[\exp\left(\frac{V_{gs}}{n_r \cdot V_t}\right) - 1\right]
\]
\[
I_{gd,rec} = I_{SR} \cdot \left[\exp\left(\frac{V_{gd}}{n_r \cdot V_t}\right) - 1\right]
\]

**Diode Conductances:**
\[
g_{gs} = \frac{I_S}{n \cdot V_t} \cdot \exp\left(\frac{V_{gs}}{n \cdot V_t}\right) + \frac{I_{SR}}{n_r \cdot V_t} \cdot \exp\left(\frac{V_{gs}}{n_r \cdot V_t}\right) + \text{GMIN}
\]
\[
g_{gd} = \frac{I_S}{n \cdot V_t} \cdot \exp\left(\frac{V_{gd}}{n \cdot V_t}\right) + \frac{I_{SR}}{n_r \cdot V_t} \cdot \exp\left(\frac{V_{gd}}{n_r \cdot V_t}\right) + \text{GMIN}
\]

### 1.2 Capacitance Models

#### 1.2.1 Voltage-Dependent Depletion Capacitances

**Reverse Bias** (\( V \leq \text{FC} \cdot \text{PB} \)):
\[
C_{gs}(V_{gs}) = \frac{C_{GS0}}{(1 - V_{gs}/\text{PB})^M}
\]
\[
C_{gd}(V_{gd}) = \frac{C_{GD0}}{(1 - V_{gd}/\text{PB})^M}
\]

**Forward Bias** (\( V > \text{FC} \cdot \text{PB} \)):
\[
C(V) = \frac{C_0}{(1 - \text{FC})^{1+M}} \cdot \left[1 - \text{FC} \cdot (1 + M) + M \cdot \frac{V}{\text{PB}}\right]
\]

#### 1.2.2 Charge Conservation Formulation

The Meyer capacitance model ensures charge conservation through state variables:

**Gate Charge:**
\[
Q_g = Q_{gs} + Q_{gd}
\]

**Charge-State Relationships:**
\[
Q_{gs} = \int C_{gs}(V_{gs}) \, dV_{gs}, \quad Q_{gd} = \int C_{gd}(V_{gd}) \, dV_{gd}
\]

**SPICE State Vector Storage:**
\[
\text{State}[q_{gs}] = Q_{gs}, \quad \text{State}[q_{gd}] = Q_{gd}, \quad \text{State}[q_{gb}] = Q_{gb}
\]

### 1.3 AC Small-Signal Analysis

#### 1.3.1 Linearized Device Equations

**Small-Signal Admittance Matrix:**
\[
\mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C}
\]

Where the conductance matrix \(\mathbf{G}\) for a 3-terminal device is:

\[
\mathbf{G} = \begin{bmatrix}
g_{ds} & 0 & -g_{ds} - g_m \\
0 & g_{gs} + g_{gd} & -g_{gs} \\
-g_{ds} & -g_{gs} - g_m & g_{ds} + g_{gs} + g_m
\end{bmatrix}
\]

And the capacitance matrix \(\mathbf{C}\) is:

\[
\mathbf{C} = \begin{bmatrix}
0 & 0 & 0 \\
0 & C_{gs} + C_{gd} & -C_{gs} \\
0 & -C_{gs} & C_{gs}
\end{bmatrix}
\]

#### 1.3.2 Complex Matrix Stamping for AC Analysis

The complete complex admittance for SPICE MNA:

\[
Y_{ij}(\omega) = G_{ij} + j\omega C_{ij}
\]

**Matrix Partitioning for Complex Arithmetic:**
\[
\begin{bmatrix}
\mathbf{G} & -\omega\mathbf{C} \\
\omega\mathbf{C} & \mathbf{G}
\end{bmatrix}
\begin{bmatrix}
\mathbf{V}_{re} \\
\mathbf{V}_{im}
\end{bmatrix}
=
\begin{bmatrix}
\mathbf{I}_{re} \\
\mathbf{I}_{im}
\end{bmatrix}
\]

### 1.4 Noise Modeling

#### 1.4.1 Channel Thermal Noise

**Long-Channel Approximation:**
\[
S_{id,thermal} = 4kT \gamma g_{d0}
\]
Where \(\gamma = 2/3\) for long channels, modified for short channels:

**Short-Channel Correction:**
\[
\gamma = \frac{2}{3} \cdot \frac{1 + V_{ds}/V_{dsat}}{1 + 2V_{ds}/V_{dsat}}
\]

#### 1.4.2 Gate-Induced Noise (Correlated)

\[
S_{ig,induced} = 4kT \delta \frac{\omega^2 C_{gg}^2}{g_{d0}}
\]
Where \(\delta = 4/3\) for long channels.

**Correlation Coefficient:**
\[
c = j0.395 \quad (j = \sqrt{-1})
\]

#### 1.4.3 Gate Shot Noise (Schottky Barrier)

\[
S_{ig,shot} = 2q(|I_{gs}| + |I_{gd}|)
\]

#### 1.4.4 Flicker (1/f) Noise

\[
S_{id,flicker}(f) = \frac{K_F \cdot I_d^{A_F}}{f}
\]

#### 1.4.5 Parasitic Resistance Thermal Noise

\[
S_{rd} = \frac{4kT}{R_D}, \quad S_{rs} = \frac{4kT}{R_S}
\]

### 1.5 Harmonic Distortion Analysis

#### 1.5.1 Taylor Series Expansion

The drain current expanded around the DC operating point:

\[
I_d(V_{gs} + v_{gs}, V_{ds} + v_{ds}) = I_{d0} + g_m v_{gs} + g_{ds} v_{ds} + \frac{1}{2}g_{m2} v_{gs}^2 + \frac{1}{2}g_{ds2} v_{ds}^2 + g_{md} v_{gs} v_{ds} + \frac{1}{6}g_{m3} v_{gs}^3 + \cdots
\]

#### 1.5.2 Second-Order Derivatives

**Subthreshold Region:**
\[
g_{m2} = \frac{\beta}{n^2 V_t^2} \exp\left(\frac{V_{gst}}{n V_t}\right) V_{ds} (1 + \lambda V_{ds})
\]
\[
g_{ds2} = \frac{\beta}{n V_t} \exp\left(\frac{V_{gst}}{n V_t}\right) (1 + 2\lambda V_{ds})
\]

**Linear Region:**
\[
g_{m2} = 0, \quad g_{ds2} = \beta (1 + 2\lambda V_{ds})
\]

**Saturation Region:**
\[
g_{m2} = \beta (1 + \lambda V_{ds}), \quad g_{ds2} = 0
\]

#### 1.5.3 Third-Order Derivatives

**Subthreshold Region:**
\[
g_{m3} = \frac{\beta}{n^3 V_t^3} \exp\left(\frac{V_{gst}}{n V_t}\right) V_{ds} (1 + \lambda V_{ds})
\]
\[
g_{ds3} = \frac{\beta}{n^2 V_t^2} \exp\left(\frac{V_{gst}}{n V_t}\right) (1 + 2\lambda V_{ds})
\]

**Linear Region:**
\[
g_{m3} = 0, \quad g_{ds3} = 2\beta\lambda
\]

#### 1.5.4 Capacitance Nonlinearities

**Second-Order Capacitance Derivative (Reverse Bias):**
\[
C_{gs2} = C_{GS0} \cdot \frac{M(M+1)}{PB^2} \cdot \frac{1}{(1 - V_{gs}/PB)^{M+2}}
\]

**Third-Order Capacitance Derivative:**
\[
C_{gs3} = C_{GS0} \cdot \frac{M(M+1)(M+2)}{PB^3} \cdot \frac{1}{(1 - V_{gs}/PB)^{M+3}}
\]

#### 1.5.5 Distortion Coefficients

**Second Harmonic Distortion:**
\[
HD2 \approx \frac{1}{2} \cdot \frac{g_{m2}}{g_m} \cdot V_{sig}
\]

**Third Harmonic Distortion:**
\[
HD3 \approx \frac{1}{6} \cdot \frac{g_{m3}}{g_m} \cdot V_{sig}^2
\]

**Intermodulation Distortion:**
\[
IM3 \approx \frac{3}{4} \cdot \frac{g_{m3}}{g_m} \cdot V_{sig}^2
\]

### 1.6 Temperature Dependence

#### 1.6.1 Threshold Voltage Temperature Scaling

\[
V_{TO}(T) = V_{TO}(T_{nom}) \cdot [1 + T_{CV1}(T - T_{nom}) + T_{CV2}(T - T_{nom})^2]
\]

#### 1.6.2 Mobility Temperature Dependence

\[
\beta(T) = \beta(T_{nom}) \cdot \left(\frac{T}{T_{nom}}\right)^{-T_{CB1}}
\]

#### 1.6.3 Saturation Current Temperature Scaling

\[
I_S(T) = I_S(T_{nom}) \cdot \exp\left[-\frac{E_G}{k}\left(\frac{1}{T} - \frac{1}{T_{nom}}\right)\right] \cdot \left(\frac{T}{T_{nom}}\right)^{X_{TI}}
\]

#### 1.6.4 Junction Potential Temperature Dependence

\[
PB(T) = PB(T_{nom}) \cdot \frac{T}{T_{nom}} - 3V_t \ln\left(\frac{T}{T_{nom}}\right) - E_G(T) \cdot \left(1 - \frac{T}{T_{nom}}\right)
\]

#### 1.6.5 Series Resistance Temperature Scaling

\[
R_D(T) = R_D(T_{nom}) \cdot [1 + T_{CRD1}(T - T_{nom}) + T_{CRD2}(T - T_{nom})^2]
\]

### 1.7 Self-Heating Model

**Thermal Network Equations:**
\[
P_{diss} = V_{ds} \cdot I_d
\]
\[
T_j = T_a + R_{th} \cdot P_{diss} + \tau_{th} \cdot \frac{dP_{diss}}{dt}
\]

**Recursive Temperature Update:**
\[
T_{j}^{(k+1)} = T_a + R_{th} \cdot V_{ds}^{(k)} \cdot I_d^{(k)}(T_j^{(k)})
\]

### 1.8 SPICE MNA Integration

#### 1.8.1 Companion Model for Transient Analysis

**Charge Conservation Formulation:**
\[
I_{cap}(t) = \frac{dQ}{dt} = \frac{Q(t) - Q(t-\Delta t)}{\Delta t} + \text{history terms}
\]

**Backward Euler Discretization:**
\[
I_{cap}^{n+1} = \frac{C}{\Delta t} (V^{n+1} - V^n) + I_{history}
\]

#### 1.8.2 Jacobian Matrix for Newton-Raphson

The complete Jacobian for the 3-terminal device:

\[
\mathbf{J} = \begin{bmatrix}
\frac{\partial I_d}{\partial V_d} & \frac{\partial I_d}{\partial V_g} & \frac{\partial I_d}{\partial V_s} \\
\frac{\partial I_g}{\partial V_d} & \frac{\partial I_g}{\partial V_g} & \frac{\partial I_g}{\partial V_s} \\
\frac{\partial I_s}{\partial V_d} & \frac{\partial I_s}{\partial V_g} & \frac{\partial I_s}{\partial V_s}
\end{bmatrix}
=
\begin{bmatrix}
g_{ds} & g_m & -g_{ds} - g_m \\
-g_{gd} & g_{gs} + g_{gd} & -g_{gs} \\
-g_{ds} + g_{gd} & -g_{gs} - g_m & g_{ds} + g_{gs} + g_m
\end{bmatrix}
\]

#### 1.8.3 Parasitic Resistance Inclusion

When \( R_D > 0 \) or \( R_S > 0 \), internal nodes are created:

\[
\begin{bmatrix}
\frac{1}{R_D} & -\frac{1}{R_D} & 0 & 0 \\
-\frac{1}{R_D} & \frac{1}{R_D} + g_{ds} & g_m & -g_{ds} - g_m \\
0 & -g_{gd} & g_{gs} + g_{gd} & -g_{gs} \\
0 & -g_{ds} + g_{gd} & -g_{gs} - g_m & \frac{1}{R_S} + g_{ds} + g_{gs} + g_m
\end{bmatrix}
\]

### 1.9 Pole-Zero Analysis Formulation

#### 1.9.1 Small-Signal Equivalent Circuit

**Intrinsic Y-Parameters:**
\[
y_{11} = j\omega(C_{gs} + C_{gd})
\]
\[
y_{12} = -j\omega C_{gd}
\]
\[
y_{21} = g_m - j\omega C_{gd}
\]
\[
y_{22} = g_{ds} + j\omega(C_{gd} + C_{ds})
\]

#### 1.9.2 Complete Admittance Matrix with Parasitics

\[
\mathbf{Y}_{total}(s) = \mathbf{Y}_{intrinsic}(s) + 
\begin{bmatrix}
\frac{1}{R_D} & 0 & 0 \\
0 & 0 & 0 \\
0 & 0 & \frac{1}{R_S}
\end{bmatrix}
+ s
\begin{bmatrix}
C_{d,par} & 0 & 0 \\
0 & C_{g,par} & 0 \\
0 & 0 & C_{s,par}
\end{bmatrix}
\]

### 1.10 Sensitivity Analysis Formulation

#### 1.10.1 Adjoint Method for Parameter Sensitivity

**Direct Sensitivities:**
\[
\frac{\partial I_d}{\partial P} = \frac{\partial I_d}{\partial V_{gs}} \cdot \frac{\partial V_{gs}}{\partial P} + \frac{\partial I_d}{\partial V_{ds}} \cdot \frac{\partial V_{ds}}{\partial P} + \frac{\partial I_d}{\partial P}_{direct}
\]

**Specific Parameter Sensitivities:**

1. **Threshold Voltage:**
\[
\frac{\partial I_d}{\partial V_{TO}} = -g_m
\]

2. **Transconductance Parameter:**
\[
\frac{\partial I_d}{\partial \beta} = \frac{I_d}{\beta}
\]

3. **Channel Length:**
\[
\frac{\partial I_d}{\partial L} = -\frac{I_d}{L} \quad \text{(constant field scaling)}
\]

4. **Channel Width:**
\[
\frac{\partial I_d}{\partial W} = \frac{I_d}{W}
\]

#### 1.10.2 Matrix Sensitivity Derivatives

**Conductance Matrix Sensitivity:**
\[
\frac{\partial \mathbf{G}}{\partial P} = 
\begin{bmatrix}
\frac{\partial g_{ds}}{\partial P} & 0 & -\frac{\partial g_{ds}}{\partial P} - \frac{\partial g_m}{\partial P} \\
0 & \frac{\partial g_{gs}}{\partial P} + \frac{\partial g_{gd}}{\partial P} & -\frac{\partial g_{gs}}{\partial P} \\
-\frac{\partial g_{ds}}{\partial P} & -\frac{\partial g_{gs}}{\partial P} - \frac{\partial g_m}{\partial P} & \frac{\partial g_{ds}}{\partial P} + \frac{\partial g_{gs}}{\partial P} + \frac{\partial g_m}{\partial P}
\end{bmatrix}
\]

This comprehensive mathematical formulation provides the foundation for the HFET and JFET implementations in Ngspice, integrating semiconductor physics with numerical methods for circuit simulation while maintaining compatibility with the SPICE MNA framework.

## 2. Convergence Analysis

The convergence analysis for HFET and JFET models in Ngspice addresses the numerical stability and solution accuracy of the nonlinear semiconductor equations within the SPICE simulation framework. The analysis encompasses Newton-Raphson iteration, local truncation error control, charge conservation, and specialized techniques for handling device-specific numerical challenges.

### 2.1 Newton-Raphson Iteration Framework

#### 2.1.1 Nonlinear System Formulation

The device equations form a nonlinear system:

\[
\mathbf{F}(\mathbf{V}) = \mathbf{I}_{device}(\mathbf{V}) - \mathbf{Y} \cdot \mathbf{V} = 0
\]

Where for a 3-terminal device:
\[
\mathbf{V} = [V_d, V_g, V_s]^T, \quad \mathbf{I}_{device} = [I_d, I_g, I_s]^T
\]

#### 2.1.2 Jacobian Matrix Construction

The Newton-Raphson iteration at step \(k+1\):

\[
\mathbf{J}^{(k)} \Delta \mathbf{V}^{(k)} = -\mathbf{F}(\mathbf{V}^{(k)})
\]
\[
\mathbf{V}^{(k+1)} = \mathbf{V}^{(k)} + \lambda^{(k)} \Delta \mathbf{V}^{(k)}
\]

The device Jacobian contributions are:

\[
\mathbf{J}_{device} = \frac{\partial \mathbf{I}_{device}}{\partial \mathbf{V}} = 
\begin{bmatrix}
g_{ds} & g_m & -g_{ds} - g_m \\
-g_{gd} & g_{gs} + g_{gd} & -g_{gs} \\
-g_{ds} + g_{gd} & -g_{gs} - g_m & g_{ds} + g_{gs} + g_m
\end{bmatrix}
\]

#### 2.1.3 Convergence Criteria

**Voltage Convergence:**
\[
|\Delta V_i^{(k)}| < \epsilon_V = \text{VNTOL} + \text{RELTOL} \cdot \max(|V_i^{(k)}|, |V_i^{(k-1)}|)
\]
Where \(\text{VNTOL} = 10^{-6} \, \text{V}\), \(\text{RELTOL} = 10^{-3}\).

**Current Convergence:**
\[
|\Delta I_d^{(k)}| < \epsilon_I = \text{ABSTOL} + \text{RELTOL} \cdot \max(|I_d^{(k)}|, |I_d^{(k-1)}|)
\]
Where \(\text{ABSTOL} = 10^{-12} \, \text{A}\).

**Charge Convergence (Transient):**
\[
|\Delta Q^{(k)}| < \epsilon_Q = \text{CHGTOL} + \text{RELTOL} \cdot \max(|Q^{(k)}|, |Q^{(k-1)}|)
\]
Where \(\text{CHGTOL} = 10^{-14} \, \text{C}\).

### 2.2 Numerical Challenges and Solutions

#### 2.2.1 Exponential Nonlinearity in Subthreshold Region

The subthreshold current equation:
\[
I_d = \beta \cdot \exp\left(\frac{V_{gst}}{nV_t}\right) \cdot V_{ds} \cdot (1 + \lambda V_{ds})
\]

**Problem:** The exponential term can cause numerical overflow and convergence issues.

**Solution:** Implementation of voltage limiting function `DEVfetlim()`:

```c
vgs_limited = DEVfetlim(vgs, vgs_old, vth);
```

The limiting function ensures:
\[
|V_{gs}^{(k+1)} - V_{gs}^{(k)}| < 2 \cdot n \cdot V_t
\]
to prevent excessive argument to exponential function.

#### 2.2.2 Gate Diode Exponential Nonlinearity

The Schottky/PN diode equation:
\[
I = I_S \cdot [\exp(V/(nV_t)) - 1]
\]

**Problem:** Can cause convergence failure for large forward bias.

**Solution:** PN junction limiting function `pnjlim()`:
- Limits voltage step to prevent \( \exp(V/(nV_t)) \) overflow
- Maintains continuous first derivative
- Typical limit: \( \Delta V < 10 \cdot n \cdot V_t \)

#### 2.2.3 Discontinuous Derivatives at Region Boundaries

The piecewise-defined current equations have discontinuous derivatives at:
1. \( V_{gst} = 0 \) (subthreshold to linear transition)
2. \( V_{ds} = V_{gst} \) (linear to saturation transition)

**Problem:** Discontinuous Jacobian causes Newton-Raphson oscillation.

**Solution:** Smoothing functions and continuous derivative formulations:

**Subthreshold-Linear Transition Smoothing:**
\[
V_{gst,eff} = \frac{1}{2} \left[ V_{gst} + \sqrt{V_{gst}^2 + \delta^2} \right]
\]
Where \( \delta \approx 10^{-6} \, \text{V} \).

**Linear-Saturation Transition:**
\[
V_{ds,eff} = V_{ds} - \frac{1}{2} \left[ V_{ds} - V_{gst} + \sqrt{(V_{ds} - V_{gst})^2 + \delta^2} \right]
\]

### 2.3 Local Truncation Error (LTE) Analysis

#### 2.3.1 Charge-Based LTE Estimation

For trapezoidal integration, the LTE is estimated using Richardson extrapolation:

**Charge Conservation Formulation:**
\[
\text{LTE}_Q = \frac{\Delta t^3}{12} \cdot \left| \frac{d^3Q}{dt^3} \right|
\]

**Numerical Estimation:**
\[
\frac{d^3Q}{dt^3} \approx \frac{Q(t) - 3Q(t-\Delta t) + 3Q(t-2\Delta t) - Q(t-3\Delta t)}{\Delta t^3}
\]

**Normalized Error:**
\[
e_Q = \frac{\text{LTE}_Q}{\text{RELTOL} \cdot |Q| + \text{CHGTOL}}
\]

#### 2.3.2 Current-Based LTE Estimation

**For rapidly changing currents:**
\[
\text{LTE}_I = \frac{\Delta t^3}{12} \cdot \left| \frac{d^3I_d}{dt^3} \right|
\]

**Time Step Control:**
\[
\Delta t_{new} = \Delta t_{old} \cdot \min\left(0.9 \cdot \max(e_Q, e_I)^{-1/3}, 2.0\right)
\]

#### 2.3.3 Breakpoint Generation

Time points are forced at:
1. **Rapid voltage changes:** \( |dV/dt| > \text{VNTOL}/\Delta t \)
2. **Region transitions:** When \( V_{gst} \) crosses zero or \( V_{ds} \approx V_{gst} \)
3. **Capacitance discontinuities:** When \( V_{gs} \) or \( V_{gd} \) crosses \( \text{FC} \cdot \text{PB} \)

### 2.4 Convergence Acceleration Techniques

#### 2.4.1 Damping (Lambda) Algorithm

The damping factor \( \lambda^{(k)} \) is dynamically adjusted:

**Initial value:** \( \lambda^{(0)} = 1.0 \)

**Reduction criteria:**
1. If \( \|\mathbf{F}(\mathbf{V}^{(k+1)})\| > \|\mathbf{F}(\mathbf{V}^{(k)})\| \): \( \lambda \leftarrow 0.5\lambda \)
2. If oscillation detected: \( \lambda \leftarrow 0.25\lambda \)
3. If \( \lambda < 0.1 \): activate fallback strategies

**Increase criteria:**
- After 3 consecutive successful iterations: \( \lambda \leftarrow \min(2\lambda, 1.0) \)

#### 2.4.2 GMIN Stepping

**Algorithm:**
1. Start with \( \text{GMIN} = 10^{-12} \, \text{S} \)
2. If no convergence after \( N_{max} \) iterations: \( \text{GMIN} \leftarrow 10 \cdot \text{GMIN} \)
3. Maximum \( \text{GMIN} = 10^{-6} \, \text{S} \)
4. After convergence, gradually reduce GMIN back to nominal

**Effect:** Adds small conductance across all junctions to improve matrix conditioning.

#### 2.4.3 Source Stepping

For difficult DC operating points:

**Algorithm:**
1. Scale all independent sources by factor \( \alpha \) (initially 0.1)
2. Solve circuit
3. Gradually increase \( \alpha \) toward 1.0
4. Use previous solution as initial guess for next step

**Mathematical formulation:**
\[
\mathbf{F}(\mathbf{V}, \alpha) = \mathbf{I}_{device}(\mathbf{V}) - \alpha \cdot \mathbf{I}_{source} = 0
\]

### 2.5 Charge Conservation Verification

#### 2.5.1 Terminal Current Consistency

Check: \( I_d + I_s + I_g = 0 \) (within tolerance)

**Tolerance:** \( \epsilon_{KCL} = 10^{-12} \, \text{A} \)

#### 2.5.2 Capacitance Charge Conservation

For Meyer capacitance model:
\[
Q_g = Q_{gs} + Q_{gd} + Q_{gb}
\]

**Verification:**
\[
\left| \frac{dQ_g}{dt} - (I_{gs} + I_{gd} + I_{gb}) \right| < \text{CHGTOL}
\]

#### 2.5.3 State Vector Consistency

Check that stored charges in state vector match computed charges:
\[
| \text{State}[q_{gs}] - Q_{gs}(V_{gs}) | < \epsilon_Q
\]

### 2.6 AC Analysis Convergence

#### 2.6.1 Frequency Domain Convergence Criteria

**Admittance Matrix Convergence:**
\[
\| \mathbf{Y}^{(k)}(\omega) - \mathbf{Y}^{(k-1)}(\omega) \|_F < \epsilon_Y \cdot \| \mathbf{Y}^{(k)}(\omega) \|_F
\]
Where \( \epsilon_Y = 10^{-4} \).

**Phase Convergence:**
\[
|\angle Y_{ij}^{(k)}(\omega) - \angle Y_{ij}^{(k-1)}(\omega)| < 0.1^\circ
\]

#### 2.6.2 Perturbation Method Stability

The AC derivatives are computed using finite difference:
\[
\frac{\partial I_i}{\partial V_j} \approx \frac{I_i(V_j + \delta) - I_i(V_j - \delta)}{2\delta}
\]

**Optimal perturbation size:**
\[
\delta = \max(10^{-8}, 10^{-5} \cdot |V_j|)
\]

**Convergence check:**
\[
\left| \frac{\partial I}{\partial V}^{(k)} - \frac{\partial I}{\partial V}^{(k-1)} \right| < \text{RELTOL} \cdot \left| \frac{\partial I}{\partial V}^{(k)} \right|
\]

### 2.7 Distortion Analysis Convergence

#### 2.7.1 Volterra Series Convergence

For harmonic distortion analysis, check convergence of Taylor coefficients:

**Second-order coefficient:**
\[
|g_{m2}^{(k)} - g_{m2}^{(k-1)}| < \epsilon_{HD2} \cdot |g_{m2}^{(k)}|
\]
Where \( \epsilon_{HD2} = 10^{-3} \).

**Third-order coefficient:**
\[
|g_{m3}^{(k)} - g_{m3}^{(k-1)}| < \epsilon_{HD3} \cdot |g_{m3}^{(k)}|
\]
Where \( \epsilon_{HD3} = 10^{-3} \).

#### 2.7.2 Intermodulation Product Convergence

For two-tone analysis at frequencies \( f_1 \) and \( f_2 \):

**IM3 product at \( 2f_1 - f_2 \):**
\[
\left| \frac{P_{IM3}^{(k)} - P_{IM3}^{(k-1)}}{P_{IM3}^{(k)}} \right| < 10^{-2}
\]

### 2.8 Temperature Iteration Convergence

#### 2.8.1 Self-Heating Iteration

For devices with thermal network:

**Temperature convergence:**
\[
|T_j^{(k+1)} - T_j^{(k)}| < \epsilon_T = 0.1 \, \text{K}
\]

**Power convergence:**
\[
|P_{diss}^{(k+1)} - P_{diss}^{(k)}| < \epsilon_P = 10^{-6} \cdot P_{diss}^{(k)}
\]

#### 2.8.2 Recursive Parameter Update

After temperature update, device parameters are recomputed:

**Convergence check for recursive updates:**
\[
\max\left( \frac{|\beta^{(k+1)} - \beta^{(k)}|}{|\beta^{(k)}|}, \frac{|V_{TO}^{(k+1)} - V_{TO}^{(k)}|}{|V_{TO}^{(k)}|} \right) < 10^{-4}
\]

### 2.9 Memory and State Management Convergence

#### 2.9.1 State Vector Consistency

Check that all state variables are properly updated:

**Charge state consistency:**
\[
| \text{State}_{new}[q] - \text{State}_{old}[q] - \Delta Q | < \epsilon_Q
\]

**History buffer consistency (for multi-step methods):**
- Check that Gear method coefficients properly weight past states
- Verify charge conservation across time steps

#### 2.9.2 Matrix Pointer Validity

During Newton-Raphson iteration:
- Verify SMP matrix pointers are valid
- Check for null pointers before dereferencing
- Ensure matrix elements are properly