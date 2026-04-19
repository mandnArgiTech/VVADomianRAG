# MOSFET Level 2: Core Mathematics and DC Load

_Generated 2026-04-12 04:29 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/include/ngspice/devdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2load.c`

# MOSFET Level 2: Core Mathematics and DC Load

## Technical Introduction

The Level 2 MOSFET model in Ngspice implements the Grove-Frohman analytical model, which extends the basic Shichman-Hodges equations with comprehensive geometry-dependent effects essential for accurate simulation of modern semiconductor devices. This implementation is distributed across several core C source files that work in concert:

*   **`devdefs.h` (and derived MOS2 headers)**: Defines the fundamental data structures `sMOS2model` and `sMOS2instance`. These structures map SPICE model and instance parameters (e.g., `MOS2vt0`, `MOS2gamma`, `MOS2l`, `MOS2w`) directly to C variables, and store computed operating point data (voltages, currents, small-signal parameters, charges) required by the Newton-Raphson solver.

*   **`mos2par.c`**: Handles parameter processing and the calculation of geometry-dependent corrections. It implements the mathematical transformations for short-channel and narrow-width effects on threshold voltage, computes effective channel dimensions considering lateral diffusion (`LD`, `WD`), and pre-calculates derived parameters like the oxide capacitance factor (`ε_ox/TOX`).

*   **`mos2temp.c`**: Implements temperature scaling of model parameters. It adjusts threshold voltage, mobility, surface potential, and junction characteristics based on thermodynamic principles, using the bandgap voltage temperature dependence to ensure accurate simulation across operating temperatures.

*   **`mos2load.c`**: Contains the core DC load function `MOS2load()`. This is the computational heart of the model, evaluating the piecewise Grove-Frohman drain current equations (subthreshold, linear/triode, velocity saturation), computing the associated small-signal conductances (`gm`, `gds`, `gmb`), and stamping the 4x4 conductance matrix and current vector into the circuit's linear system for the Newton-Raphson iteration. It also integrates the `DEVfetlim()` function for robust convergence control.

Together, these files translate the complex, geometry-aware Level 2 MOSFET physics into the numerical procedures required for SPICE-based circuit simulation, balancing physical accuracy with computational efficiency and solver stability.

## Mathematical Formulation

### 1. Threshold Voltage with Geometry Effects

The Level 2 MOSFET model extends the basic Shichman-Hodges formulation with comprehensive geometry-dependent corrections. The threshold voltage calculation incorporates short-channel and narrow-width effects critical for modern device simulation:

\[
V_{th} = VTO + \gamma \cdot \left[ \sqrt{2\phi + V_{sb}} - \sqrt{2\phi} \right] + \Delta V_{th}^{\text{short}} + \Delta V_{th}^{\text{narrow}}
\]

where:
- \( VTO \) = `MOS2vt0` (zero-bias threshold voltage)
- \( \gamma \) = `MOS2gamma` (body effect parameter)
- \( \phi \) = `MOS2phi` (surface potential)
- \( V_{sb} \) = bulk-source voltage

#### Short-Channel Effect Correction
For devices with channel length \( L \) comparable to junction depth \( X_j \):

\[
\Delta V_{th}^{\text{short}} = -\delta \cdot \frac{\varepsilon_{si}}{\varepsilon_{ox}} \cdot \frac{X_j}{L} \cdot \left[ \sqrt{2\phi + V_{sb}} - \sqrt{2\phi} \right]
\]

where:
- \( \delta \) = `MOS2delta` (short-channel effect parameter)
- \( \varepsilon_{si} = 11.7 \cdot \varepsilon_0 \) (silicon permittivity)
- \( \varepsilon_{ox} = 3.9 \cdot \varepsilon_0 \) (oxide permittivity)
- \( X_j \) = `MOS2xj` (metallurgical junction depth)

#### Narrow-Width Effect Correction
For devices with channel width \( W \) comparable to oxide thickness \( TOX \):

\[
\Delta V_{th}^{\text{narrow}} = \frac{\gamma \cdot TOX}{W} \cdot \left[ \sqrt{2\phi + V_{sb}} - \sqrt{2\phi} \right] \cdot \left( 1 + \sqrt{\frac{\pi \cdot \varepsilon_{si} \cdot \phi}{4 \cdot \varepsilon_{ox} \cdot TOX}} \right)
\]

where \( TOX \) = `MOS2tox` (oxide thickness).

### 2. Effective Mobility with Field-Dependent Degradation

The Level 2 model accounts for mobility degradation due to vertical and lateral electric fields:

\[
\mu_{\text{eff}} = \frac{U_0}{1 + \theta \cdot (V_{gs} - V_{th}) + \eta \cdot V_{ds}}
\]

where:
- \( U_0 \) = `MOS2u0` (low-field mobility)
- \( \theta \) = `MOS2theta` (mobility degradation coefficient)
- \( \eta \) = `MOS2eta` (static feedback coefficient)

### 3. Piecewise Drain Current Equations

#### Region 1: Subthreshold Conduction (\( V_{gs} \leq V_{th} + n \cdot V_t \))
For weak inversion operation:

\[
I_d = I_0 \cdot \exp\left( \frac{V_{gs} - V_{th}}{n \cdot V_t} \right) \cdot \left[ 1 - \exp\left( -\frac{V_{ds}}{V_t} \right) \right]
\]

where:
- \( n = 1 + \frac{C_{\text{dep}}}{C_{ox}} + \frac{q \cdot NFS}{C_{ox}} \) (subthreshold slope factor)
- \( C_{\text{dep}} = \sqrt{\frac{q \cdot \varepsilon_{si} \cdot NSUB}{4\phi}} \) (depletion capacitance)
- \( C_{ox} = \frac{\varepsilon_{ox}}{TOX} \) (oxide capacitance per unit area)
- \( V_t = \frac{kT}{q} \) (thermal voltage)
- \( I_0 = \frac{W}{L} \cdot \mu_{\text{eff}} \cdot C_{ox} \cdot (n \cdot V_t)^2 \)
- \( NSUB \) = `MOS2nsub` (substrate doping)
- \( NFS \) = `MOS2nfs` (fast surface state density)

#### Region 2: Linear/Triode Operation (\( V_{gs} > V_{th} + n \cdot V_t \) AND \( V_{ds} \leq V_{dsat} \))
For strong inversion with small drain bias:

\[
I_d = \beta \cdot \left[ (V_{gs} - V_{th}) \cdot V_{ds} - \frac{(1 + F_B) \cdot V_{ds}^2}{2} \right] \cdot (1 + \lambda \cdot V_{ds})
\]

where:
- \( \beta = \frac{W}{L} \cdot \mu_{\text{eff}} \cdot C_{ox} \) (transconductance coefficient)
- \( \lambda \) = `MOS2lambda` (channel-length modulation parameter)
- \( F_B = \frac{\gamma \cdot F_S}{2 \cdot \sqrt{2\phi + V_{sb}}} + F_N \) (geometry factor)

The geometry factors account for charge sharing:

\[
F_S = 1 - \frac{X_j}{L} \cdot \left[ \sqrt{1 + \left( \frac{2W_P}{X_j} \right)^2} - 1 \right]
\]
\[
W_P = \sqrt{\frac{2 \cdot \varepsilon_{si} \cdot (2\phi + V_{sb})}{q \cdot NSUB}}
\]
\[
F_N = \frac{\delta \cdot \pi \cdot \varepsilon_{si}}{4 \cdot C_{ox} \cdot W}
\]

#### Region 3: Velocity Saturation (\( V_{gs} > V_{th} + n \cdot V_t \) AND \( V_{ds} > V_{dsat} \))
For high-field operation where carrier velocity saturates:

**Saturation Voltage Calculation:**
\[
V_{dsat} = \frac{V_{gs} - V_{th}}{1 + F_B} + \frac{VMAX \cdot L}{\mu_{\text{eff}}} - \sqrt{ \left( \frac{V_{gs} - V_{th}}{1 + F_B} \right)^2 + \left( \frac{VMAX \cdot L}{\mu_{\text{eff}}} \right)^2 }
\]

where \( VMAX \) = `MOS2vmax` (maximum carrier velocity).

**Drain Current in Saturation:**
\[
I_d = \beta \cdot \left[ (V_{gs} - V_{th}) \cdot V_{dsat} - \frac{(1 + F_B) \cdot V_{dsat}^2}{2} \right] \cdot (1 + \lambda \cdot V_{ds}) \cdot \frac{V_{ds}}{V_{dsat} \cdot (1 + F_B)}
\]

### 4. Channel-Length Modulation

For devices with non-zero \( \lambda \), the output conductance includes channel-length modulation:

\[
g_{ds} = \lambda \cdot I_d \cdot \frac{L_{\text{eff}}}{\Delta L \cdot (L_{\text{eff}} - \Delta L)}
\]

where:
\[
\Delta L = \sqrt{ \frac{\kappa \cdot \varepsilon_{si}}{2 \cdot q \cdot NSUB} \cdot (V_{ds} - V_{dsat}) }
\]
and \( \kappa \) = `MOS2kappa` (saturation field parameter).

### 5. Meyer Capacitance Charge Model

The gate charge partitioning uses the Meyer model with continuous derivatives:

**Total Gate Charge:**
\[
Q_g = C_{ox} \cdot W \cdot L \cdot \left[ V_{gb} - V_{FB} - \phi - \frac{V_{gs} + V_{gd} - 2V_{bs}}{2} \right] + \frac{2}{3} \cdot C_{ox} \cdot W \cdot L \cdot \frac{(V_{gs} - V_{th})^3 - (V_{gd} - V_{th})^3}{(V_{gs} - V_{th})^2 - (V_{gd} - V_{th})^2}
\]

where \( V_{FB} \) is the flat-band voltage.

**Drain and Source Charges:**
\[
Q_d = -C_{ox} \cdot W \cdot L \cdot \left[ V_{gb} - V_{FB} - \phi - V_{bs} + \frac{1}{2} \cdot (V_{gs} - V_{th}) + \frac{1}{6} \cdot \frac{(V_{gs} - V_{th})^2}{V_{gs} - V_{th} + V_{gd} - V_{th}} \right]
\]
\[
Q_s = -C_{ox} \cdot W \cdot L \cdot \left[ V_{gb} - V_{FB} - \phi - V_{bs} + \frac{1}{2} \cdot (V_{gd} - V_{th}) + \frac{1}{6} \cdot \frac{(V_{gd} - V_{th})^2}{V_{gs} - V_{th} + V_{gd} - V_{th}} \right]
\]

### 6. Small-Signal Conductance Matrix

For the Newton-Raphson iteration in SPICE, the 4×4 conductance matrix is:

\[
\begin{bmatrix}
G_{dd} & G_{dg} & G_{ds} & G_{db} \\
G_{gd} & G_{gg} & G_{gs} & G_{gb} \\
G_{sd} & G_{sg} & G_{ss} & G_{sb} \\
G_{bd} & G_{bg} & G_{bs} & G_{bb}
\end{bmatrix}
\begin{bmatrix}
V_d \\
V_g \\
V_s \\
V_b
\end{bmatrix}
=
\begin{bmatrix}
I_d \\
I_g \\
I_s \\
I_b
\end{bmatrix}
\]

with elements derived from current derivatives:

\[
\begin{aligned}
G_{dd} &= +\frac{\partial I_d}{\partial V_d} = +g_{ds} \\
G_{dg} &= +\frac{\partial I_d}{\partial V_g} = +g_m \\
G_{ds} &= +\frac{\partial I_d}{\partial V_s} = -(g_{ds} + g_m + g_{mb}) \\
G_{db} &= +\frac{\partial I_d}{\partial V_b} = +g_{mb} \\
G_{gd} &= G_{gg} = G_{gs} = G_{gb} = 0 \quad \text{(ideal gate insulation)} \\
G_{sd} &= +\frac{\partial I_s}{\partial V_d} = -g_{ds} \\
G_{sg} &= +\frac{\partial I_s}{\partial V_g} = -g_m \\
G_{ss} &= +\frac{\partial I_s}{\partial V_s} = +(g_{ds} + g_m + g_{mb}) \\
G_{sb} &= +\frac{\partial I_s}{\partial V_b} = -g_{mb} \\
G_{bd} &= G_{bg} = G_{bs} = G_{bb} = 0
\end{aligned}
\]

where:
- \( g_m = \frac{\partial I_d}{\partial V_{gs}} \) (transconductance)
- \( g_{ds} = \frac{\partial I_d}{\partial V_{ds}} \) (output conductance)
- \( g_{mb} = \frac{\partial I_d}{\partial V_{bs}} \) (bulk transconductance)

### 7. Temperature Scaling Equations

For accurate simulation across temperature ranges:

**Bandgap Voltage Temperature Dependence:**
\[
E_g(T) = 1.16 - 7.02 \times 10^{-4} \cdot \frac{T^2}{T + 1108.0}
\]

**Threshold Voltage Scaling:**
\[
VTO(T) = VTO(T_{\text{nom}}) \cdot \frac{T}{T_{\text{nom}}} - 2V_t \ln\left( \frac{T}{T_{\text{nom}}} \right) - [E_g(T) - E_g(T_{\text{nom}})]
\]

**Mobility Scaling (\( \propto T^{-1.5} \)):**
\[
\mu_0(T) = \mu_0(T_{\text{nom}}) \cdot \left( \frac{T}{T_{\text{nom}}} \right)^{-1.5}
\]

**Surface Potential Scaling:**
\[
\phi(T) = \phi(T_{\text{nom}}) \cdot \frac{T}{T_{\text{nom}}} - 3V_t \ln\left( \frac{T}{T_{\text{nom}}} \right) - [E_g(T) - E_g(T_{\text{nom}})]
\]

**Junction Parameters:**
\[
PB(T) = PB(T_{\text{nom}}) \cdot \frac{T}{T_{\text{nom}}} - 2V_t \ln\left( \frac{T}{T_{\text{nom}}} \right) - [E_g(T) - E_g(T_{\text{nom}})]
\]
\[
JS(T) = JS(T_{\text{nom}}) \cdot \exp\left( \frac{E_g}{N} \cdot \left[ \frac{1}{T_{\text{nom}}} - \frac{1}{T} \right] \right) \cdot \left( \frac{T}{T_{\text{nom}}} \right)^3
\]

## Convergence Analysis

### 1. Newton-Raphson Limiting for MOSFET Voltages

The SPICE simulation employs the `DEVfetlim` function to ensure Newton-Raphson convergence by limiting voltage updates:

\[
v_{\text{lim}} = 
\begin{cases}
v_{\text{th}} + \frac{|v_{\text{old}} - v_{\text{th}}|}{2} & \text{if } v_{\text{new}} > v_{\text{th}} + \frac{|v_{\text{old}} - v_{\text{th}}|}{2} \text{ and } v_{\text{old}} \geq v_{\text{th}} \\
v_{\text{th}} - \frac{|v_{\text{old}} - v_{\text{th}}|}{2} & \text{if } v_{\text{new}} < v_{\text{th}} - \frac{|v_{\text{old}} - v_{\text{th}}|}{2} \text{ and } v_{\text{old}} < v_{\text{th}} \\
v_{\text{new}} & \text{otherwise}
\end{cases}
\]

The smoothed return value ensures continuous derivatives:

\[
v_{\text{return}} = v_{\text{lim}} + \frac{\Delta v}{2} \cdot \left( 1 + \frac{\Delta v}{\sqrt{\Delta v^2 + \epsilon}} \right)
\]

where \( \Delta v = v_{\text{new}} - v_{\text{lim}} \) and \( \epsilon = 10^{-12} \) for numerical stability.

### 2. Convergence Criteria for Level 2 MOSFET

The MOS2 convergence test checks both voltage and charge changes against SPICE tolerances:

**Voltage Convergence:**
\[
\frac{|V_{gs}^{(k)} - V_{gs}^{(k-1)}|}{|V_{gs}^{(k)}| + \epsilon_{\text{abs}}} < \epsilon_{\text{rel}}
\]
\[
\frac{|V_{ds}^{(k)} - V_{ds}^{(k-1)}|}{|V_{ds}^{(k)}| + \epsilon_{\text{abs}}} < \epsilon_{\text{rel}}
\]
\[
\frac{|V_{bs}^{(k)} - V_{bs}^{(k-1)}|}{|V_{bs}^{(k)}| + \epsilon_{\text{abs}}} < \epsilon_{\text{rel}}
\]

**Charge Convergence (for transient analysis):**
\[
\frac{|C_{gs}^{(k)} - C_{gs}^{(k-1)}|}{|C_{gs}^{(k)}| + \epsilon_{\text{abs}}} < \epsilon_{\text{rel}}
\]
\[
\frac{|C_{gd}^{(k)} - C_{gd}^{(k-1)}|}{|C_{gd}^{(k)}| + \epsilon_{\text{abs}}} < \epsilon_{\text{rel}}
\]
\[
\frac{|C_{gb}^{(k)} - C_{gb}^{(k-1)}|}{|C_{gb}^{(k)}| + \epsilon_{\text{abs}}} < \epsilon_{\text{rel}}
\]

where:
- \( \epsilon_{\text{rel}} \) = `CKTreltol` (relative tolerance, typically \( 10^{-3} \))
- \( \epsilon_{\text{abs}} = 10^{-12} \) (absolute guard)

### 3. Region Transition Continuity

The Level 2 model ensures \( C^1 \) continuity at region boundaries:

**Subthreshold to Strong Inversion:**
At \( V_{gs} = V_{th} + nV_t \), both current and derivative match:
\[
I_d^{\text{sub}}(V_{th} + nV_t) = I_d^{\text{lin}}(V_{th} + nV_t, V_{ds})
\]
\[
\frac{\partial I_d^{\text{sub}}}{\partial V_{gs}} \bigg|_{V_{th} + nV_t} = \frac{\partial I_d^{\text{lin}}}{\partial V_{gs}} \bigg|_{V_{th} + nV_t}
\]

**Linear to Saturation Transition:**
At \( V_{ds} = V_{dsat} \):
\[
I_d^{\text{lin}}(V_{gs}, V_{dsat}) = I_d^{\text{sat}}(V_{gs}, V_{dsat})
\]
\[
\frac{\partial I_d^{\text{lin}}}{\partial V_{ds}} \bigg|_{V_{dsat}} = \frac{\partial I_d^{\text{sat}}}{\partial V_{ds}} \bigg|_{V_{dsat}}
\]

### 4. Numerical Stability Considerations

#### Square Root Regularization
For the body effect term \( \sqrt{2\phi + V_{sb}} \), numerical protection is applied:

\[
\sqrt{\text{term}} = 
\begin{cases}
\sqrt{\epsilon} & \text{if } 2\phi + V_{sb} < \epsilon \\
\sqrt{2\phi + V_{sb}} & \text{otherwise}
\end{cases}
\]

with \( \epsilon = 10^{-12} \) to prevent negative arguments.

#### Small Denominator Protection
In capacitance calculations, denominators are protected:

\[
\text{denom} = V_{gst} + V_{gdt} + \epsilon
\]

where \( V_{gst} = V_{gs} - V_{th} \), \( V_{gdt} = V_{gd} - V_{th} \), and \( \epsilon = 10^{-12} \).

#### Effective Dimension Clamping
Effective channel length and width are clamped to prevent numerical issues:

\[
L_{\text{eff}} = \max(L - 2 \cdot LD, \epsilon_{\text{min}})
\]
\[
W_{\text{eff}} = \max(W - 2 \cdot WD, \epsilon_{\text{min}})
\]

with \( \epsilon_{\text{min}} = 10^{-12} \) m.

### 5. PMOS Polarity and Source-Drain Swapping

For PMOS devices, all voltages are inverted:

\[
\begin{aligned}
V_{gs}^{\text{PMOS}} &= -V_{gs}^{\text{NMOS}} \\
V_{ds}^{\text{PMOS}} &= -V_{ds}^{\text{NMOS}} \\
V_{bs}^{\text{PMOS}} &= -V_{bs}^{\text{NMOS}}
\end{aligned}
\]

When \( V_{ds} < 0 \), source and drain are swapped internally:
- Drain becomes source and source becomes drain
- \( V_{gs} \) becomes \( V_{gd} \)
- \( V_{bs} \) becomes \( V_{bd} \)
- Areas and perimeters are exchanged

This ensures the device equations always operate with \( V_{ds} \geq 0 \), simplifying the implementation.

### 6. Matrix Conditioning Analysis

The conductance matrix condition number affects convergence:

\[
\kappa(G) = \frac{\sigma_{\max}(G)}{\sigma_{\min}(G)}
\]

For the MOS2 4×4 matrix, the condition number scales with:

\[
\kappa(G) \propto \frac{\max(g_m, g_{ds}, g_{mb})}{\min(g_m, g_{ds}, g_{mb})}
\]

Poor conditioning occurs when:
- \( g_m \gg g_{ds} \) (strong saturation)
- \( g_{mb} \approx 0 \) (small body effect)
- Any conductance approaches zero (cutoff region)

### 7. Time Step Control for Transient Analysis

The local truncation error (LTE) for charge-based integration:

\[
\text{LTE}_q = \left| \frac{h^3}{12} \cdot q'''(\tau) \right| \approx \left| \frac{h}{2} \cdot (q_{\text{new}} - q_{\text{pred}}) \right|
\]

where \( h \) is the time step, \( q_{\text{new}} \) is the computed charge, and \( q_{\text{pred}} \) is the predicted charge from previous steps.

The time step is adapted as:

\[
h_{\text{new}} = 0.9 \cdot h_{\text{current}} \cdot \sqrt{ \frac{\tau_q}{\max(\epsilon_{q_{gs}}, \epsilon_{q_{gd}}, \epsilon_{q_{gb}}, \epsilon_{q_{bd}}, \epsilon_{q_{bs}})} }
\]

where \( \tau_q \) is the charge tolerance and \( \epsilon_q = \text{LTE}_q / (|q| + \epsilon_{\text{abs}}) \).

### 8. Convergence Acceleration Techniques

#### Damping for Newton Failures
After convergence failure, voltage updates are damped:

\[
\Delta V^{(k+1)} = \alpha \cdot \Delta V^{(k)}
\]

with \( \alpha \) reduced from 1.0 to 0.5, then 0.25 for persistent failures.

#### Source Stepping for Difficult Bias Points
For challenging DC operating points, independent sources are scaled:

\[
V_{\text{source}}^{(i)} = \frac{i}{N} \cdot V_{\text{source}}^{\text{final}}
\]

where \( N \) is the number of steps (typically 10-100).

### 9. Error Propagation in Derived Parameters

The total error in threshold voltage calculation accumulates through:

\[
\epsilon_{V_{th}} = \epsilon_{VTO} + \left| \frac{\partial V_{th}}{\partial \gamma} \right| \cdot \epsilon_{\gamma} + \left| \frac{\partial V_{th}}{\partial \phi} \right| \cdot \epsilon_{\phi} + \left| \frac{\partial V_{th}}{\partial \delta} \right| \cdot \epsilon_{\delta}
\]

where each partial derivative is evaluated at the operating point.

For the drain current, error propagation follows:

\[
\epsilon_{I_d} = \left| \frac{\partial I_d}{\partial \beta} \right| \cdot \epsilon_{\beta} + \left| \frac{\partial I_d}{\partial V_{th}} \right| \cdot \epsilon_{V_{th}} + \left| \frac{\partial I_d}{\partial V_{gs}} \right| \cdot \epsilon_{V_{gs}} + \left| \frac{\partial I_d}{\partial V_{ds}} \right| \cdot \epsilon_{V_{ds}}
\]

These error bounds inform the convergence tolerances required for accurate simulation.

## C Implementation

The mathematical formulations for the Level 2 MOSFET model are realized in Ngspice through dedicated C source files that extend the core MOS2 data structures and integrate with the SPICE simulation framework. The implementation directly maps the derivative equations to computational routines and matrix stamping operations.

### 1. Core Data Structures and Parameter Processing

#### MOS2 Data Structure Definitions

The Level 2 MOSFET implementation in Ngspice uses two primary data structures that map directly to the mathematical formulation:

```c
/* sMOS2model - Level 2 MOSFET model parameters (from devdefs.h) */
typedef struct sMOS2model {
    /* Process parameters mapping to mathematical variables */
    int MOS2type;                    /* NMF (1) or PMF (-1) - polarity factor */
    double MOS2vt0;                  /* VTO: Zero-bias threshold voltage */
    double MOS2kp;                   /* KP: Transconductance parameter */
    double MOS2gamma;                /* γ: Bulk threshold parameter */
    double MOS2phi;                  /* φ: Surface potential */
    double MOS2lambda;               /* λ: Channel-length modulation */
    double MOS2delta;                /* δ: Short-channel effect parameter */
    double MOS2eta;                  /* η: Static feedback parameter */
    double MOS2theta;                /* θ: Mobility modulation parameter */
    double MOS2kappa;                /* κ: Saturation field parameter */
    double MOS2vmax;                 /* VMAX: Maximum carrier velocity */
    double MOS2xj;                   /* Xj: Metallurgical junction depth */
    double MOS2ld;                   /* LD: Lateral diffusion */
    double MOS2wd;                   /* WD: Width diffusion */
    double MOS2nsub;                 /* NSUB: Substrate doping */
    double MOS2nss;                  /* NSS: Surface state density */
    double MOS2nfs;                  /* NFS: Fast surface state density */
    double MOS2tox;                  /* TOX: Oxide thickness */
    
    /* Derived parameters computed during setup */
    double MOS2coeff;                /* KP * (ε_ox / TOX) */
    double MOS2vbi;                  /* Built-in potential */
    double MOS2oxideCapFactor;       /* ε_ox / TOX */
    
    /* Linked list for multiple models */
    struct sMOS2model *MOS2nextModel;
    sMOS2instance *MOS2instances;
} MOS2model;

/* sMOS2instance - Level 2 MOSFET instance parameters */
typedef struct sMOS2instance {
    /* Terminal node indices for matrix stamping */
    int MOS2dNode;                   /* Drain node index */
    int MOS2gNode;                   /* Gate node index */
    int MOS2sNode;                   /* Source node index */
    int MOS2bNode;                   /* Bulk node index */
    
    /* Geometry parameters from SPICE deck */
    double MOS2l;                    /* L: Drawn channel length */
    double MOS2w;                    /* W: Drawn channel width */
    double MOS2ad;                   /* AD: Drain area */
    double MOS2as;                   /* AS: Source area */
    
    /* Bias-dependent operating point (computed each iteration) */
    double MOS2vgs;                  /* Vgs: Gate-source voltage */
    double MOS2vds;                  /* Vds: Drain-source voltage */
    double MOS2vbs;                  /* Vbs: Bulk-source voltage */
    double MOS2vdsat;                /* Vdsat: Saturation voltage */
    int MOS2mode;                    /* Operating mode: 0=cutoff, 1=linear, 2=saturation */
    
    /* Small-signal parameters (∂Id/∂V) */
    double MOS2gm;                   /* gm = ∂Id/∂Vgs */
    double MOS2gds;                  /* gds = ∂Id/∂Vds */
    double MOS2gmb;                  /* gmb = ∂Id/∂Vbs */
    
    /* Charge storage for transient analysis */
    double MOS2cgs;                  /* Cgs: Gate-source capacitance */
    double MOS2cgd;                  /* Cgd: Gate-drain capacitance */
    double MOS2cgb;                  /* Cgb: Gate-bulk capacitance */
    
    /* State variables for numerical integration */
    double MOS2qgs;                  /* Qgs: Gate-source charge */
    double MOS2qgd;                  /* Qgd: Gate-drain charge */
    double MOS2qgb;                  /* Qgb: Gate-bulk charge */
    
    /* Convergence control */
    int MOS2limited;                 /* Flag: NR limiting applied */
    
    /* Linked list for multiple instances */
    struct sMOS2instance *MOS2nextInstance;
    MOS2model *MOS2modPtr;           /* Pointer to parent model */
} MOS2instance;
```

#### Parameter Processing and Geometry Effects

The `MOS2setup()` function in `mos2set.c` processes parameters and computes geometry-dependent corrections:

```c
int MOS2setup(MOS2model *model, MOS2instance *inst, CKTcircuit *ckt) {
    /* Physical constants */
    double eps_ox = 3.9 * 8.854e-12;    /* ε_ox: Oxide permittivity */
    double eps_si = 11.7 * 8.854e-12;   /* ε_si: Silicon permittivity */
    
    /* Compute effective dimensions with lateral diffusion */
    inst->MOS2effL = inst->MOS2l - 2.0 * model->MOS2ld;
    inst->MOS2effW = inst->MOS2w - 2.0 * model->MOS2wd;
    
    /* Clamp to minimum dimensions for numerical stability */
    if (inst->MOS2effL < 1e-12) inst->MOS2effL = 1e-12;
    if (inst->MOS2effW < 1e-12) inst->MOS2effW = 1e-12;
    
    /* Compute oxide capacitance factor: C_ox = ε_ox / TOX */
    model->MOS2oxideCapFactor = eps_ox / model->MOS2tox;
    
    /* Compute derived coefficient: β_factor = KP * (ε_ox / TOX) */
    model->MOS2coeff = model->MOS2kp * model->MOS2oxideCapFactor;
    
    /* Compute depletion width factor for geometry effects */
    double phi = model->MOS2phi;
    double q = 1.602e-19;               /* Electron charge */
    double Nsub = model->MOS2nsub;
    
    /* Depletion width: W_P = √[2ε_si(2φ + V_sb)/(q·NSUB)] */
    /* Precompute constant part for efficiency */
    inst->MOS2wp_const = sqrt(2.0 * eps_si * 2.0 * phi / (q * Nsub));
    
    /* Compute narrow-width effect factor: F_N = (δ·π·ε_si)/(4·C_ox·W) */
    if (model->MOS2delta != 0.0) {
        inst->MOS2fn = (model->MOS2delta * M_PI * eps_si) 
                      / (4.0 * model->MOS2oxideCapFactor * inst->MOS2effW);
    } else {
        inst->MOS2fn = 0.0;
    }
    
    /* Set up matrix pointers for efficient stamping */
    inst->MOS2drainDrainPtr = SMPmakeElt(ckt->CKTmatrix, 
                                        inst->MOS2dNode, inst->MOS2dNode);
    inst->MOS2drainGatePtr = SMPmakeElt(ckt->CKTmatrix, 
                                       inst->MOS2dNode, inst->MOS2gNode);
    /* ... create all 16 matrix pointers for 4×4 conductance matrix */
    
    return OK;
}
```

### 2. Temperature Adjustment Implementation

The `MOS2temp()` function in `mos2temp.c` implements temperature scaling of model parameters:

```c
void MOS2temp(MOS2model *model, MOS2instance *inst, double temp) {
    /* Convert to Kelvin */
    double T = temp + CONSTCtoK;
    double TNOM = model->MOS2tnom + CONSTCtoK;
    double ratio = T / TNOM;
    
    /* Thermal voltage: V_t = kT/q */
    double Vt = KoverQ * T;
    double Vtnom = KoverQ * TNOM;
    
    /* Bandgap voltage temperature dependence: 
       E_g(T) = 1.16 - 7.02e-4 * T²/(T + 1108) */
    double Eg = 1.16 - 7.02e-4 * T * T / (T + 1108.0);
    double Egnom = 1.16 - 7.02e-4 * TNOM * TNOM / (TNOM + 1108.0);
    
    /* Threshold voltage scaling: 
       VTO(T) = VTO(T_nom)·(T/T_nom) - 2V_t·ln(T/T_nom) - [E_g(T) - E_g(T_nom)] */
    inst->MOS2vt0 = model->MOS2vt0 * ratio
                   - 2.0 * Vt * log(T / TNOM)
                   - (Eg - Egnom);
    
    /* Mobility scaling: μ_0 ∝ T^{-1.5} */
    inst->MOS2u0 = model->MOS2u0 * pow(ratio, -1.5);
    
    /* Surface potential scaling:
       φ(T) = φ(T_nom)·(T/T_nom) - 3V_t·ln(T/T_nom) - [E_g(T) - E_g(T_nom)] */
    inst->MOS2phi = model->MOS2phi * ratio
                   - 3.0 * Vt * log(ratio)
                   - (Eg - Egnom);
    
    /* Junction potential scaling */
    inst->MOS2pb = model->MOS2pb * ratio
                  - 2.0 * Vt * log(ratio)
                  - (Eg - Egnom);
    
    /* Junction saturation current scaling:
       J_S(T) = J_S(T_nom)·exp[(E_g/N)·(1/T_nom - 1/T)]·(T/T_nom)³ */
    inst->MOS2js = model->MOS2js * exp((Eg/N) * (1.0/TNOM - 1.0/T))
                   * pow(ratio, 3.0);
    
    /* Recompute derived parameters with updated values */
    inst->MOS2coeff = inst->MOS2u0 * model->MOS2oxideCapFactor;
}
```

### 3. Core Load Function Implementation

The `MOS2load()` function in `mos2load.c` implements the Grove-Frohman Level 2 equations:

#### Threshold Voltage Calculation with Geometry Effects

```c
double MOS2computeVth(MOS2model *model, MOS2instance *inst, 
                      double Vgs, double Vds, double Vbs) {
    double phi = inst->MOS2phi;
    double gamma = model->MOS2gamma;
    double delta = model->MOS2delta;
    double Xj = model->MOS2xj;
    double TOX = model->MOS2tox;
    double Leff = inst->MOS2effL;
    double Weff = inst->MOS2effW;
    
    /* Base threshold: V_th0 = VTO + γ·[√(2φ + V_sb) - √(2φ)] */
    double sqrt_phi = sqrt(2.0 * phi);
    double sqrt_term;
    
    /* Numerical protection for square root */
    if ((2.0 * phi + Vbs) < 1e-12) {
        sqrt_term = sqrt(1e-12);
    } else {
        sqrt_term = sqrt(2.0 * phi + Vbs);