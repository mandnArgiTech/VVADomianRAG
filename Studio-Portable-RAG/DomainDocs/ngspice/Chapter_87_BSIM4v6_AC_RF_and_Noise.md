# BSIM4v6: RF Modeling, Capacitance, and Noise Analysis

_Generated 2026-04-12 15:30 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6noi.c`

# BSIM4v6: RF Modeling, Capacitance, and Noise Analysis

## Technical Introduction

This chapter details the implementation of frequency-domain analysis, capacitance modeling, and noise simulation for the BSIM4v6 MOSFET model within the Ngspice EDA framework. The core functionality is distributed across three critical C source files: `b4v6acld.c`, `b4v6pzld.c`, and `b4v6noi.c`. Each file addresses a distinct aspect of RF and noise simulation essential for modern nanometer CMOS circuit design.

The `b4v6acld.c` file implements the small-signal AC matrix stamping algorithm, constructing the complex admittance matrix **Y(ω) = G + jωC** that SPICE stamps into the circuit matrix during frequency-domain analysis. This includes linearization of BSIM4v6 equations around the DC operating point, incorporation of gate resistance for RF modeling, and substrate network parasitics. The `b4v6pzld.c` file extends this capability to pole-zero analysis in the s-domain, using the complex frequency variable **s = σ + jω** directly for transfer function analysis. Finally, `b4v6noi.c` implements comprehensive noise analysis with configurable model selectors (`tnoimod` and `fnoimod`), supporting multiple thermal and flicker noise formulations including induced gate noise (IGN) correlation critical for RF applications. Together, these files enable Ngspice to perform complete RF characterization of BSIM4v6 devices, from small-signal AC response through noise figure analysis.

## Mathematical Formulation

### 1. Small-Signal AC Matrix Stamping for SPICE Frequency-Domain Analysis

The BSIM4v6 model implements frequency-domain analysis through linearization of device equations around the DC operating point, forming a complex admittance matrix that SPICE stamps into the circuit matrix for AC analysis.

#### 1.1 Complex Admittance Matrix Construction

The complete AC admittance matrix for BSIM4v6 in SPICE simulation is:

\[
Y_{ac}(\omega) = G + j\omega C + \frac{\partial I_{gate-leakage}}{\partial V} + j\omega C_{overlap}
\]

Where:
- \(G\) = conductance matrix from DC Jacobian linearization (real part)
- \(C\) = capacitance matrix from BSIM4v6 charge model (imaginary part coefficient)
- \(I_{gate-leakage}\) = gate tunneling currents (Igc, Igb, Igd, Igs)
- \(\omega = 2\pi \cdot \text{CKTomega}\) = SPICE angular frequency variable

#### 1.2 4×4 Terminal Admittance Matrix

For SPICE's Modified Nodal Analysis, the BSIM4v6 stamps a 4×4 complex matrix:

\[
\begin{bmatrix}
Y_{dd} & Y_{dg} & Y_{ds} & Y_{db} \\
Y_{gd} & Y_{gg} & Y_{gs} & Y_{gb} \\
Y_{sd} & Y_{sg} & Y_{ss} & Y_{sb} \\
Y_{bd} & Y_{bg} & Y_{bs} & Y_{bb}
\end{bmatrix}
=
\begin{bmatrix}
g_{ds} + j\omega(C_{dd} + C_{gd}) & -g_m + j\omega C_{gd} & -(g_{ds} + g_m + g_{mb}) + j\omega C_{ds} & g_{mb} + j\omega C_{db} \\
j\omega C_{gd} & j\omega(C_{gg} + C_{gd} + C_{gb}) & j\omega C_{gs} & j\omega C_{gb} \\
-g_{ds} + j\omega C_{sd} & -g_m + j\omega C_{sg} & g_{ds} + g_m + g_{mb} + j\omega(C_{ss} + C_{gs}) & -g_{mb} + j\omega C_{sb} \\
j\omega C_{bd} & j\omega C_{bg} & j\omega C_{bs} & j\omega(C_{bb} + C_{bd} + C_{bs})
\end{bmatrix}
\]

**SPICE Implementation Notes:**
- \(g_m = \text{B4v6gm}\) = transconductance from DC operating point
- \(g_{ds} = \text{B4v6gds}\) = output conductance
- \(g_{mb} = \text{B4v6gmb}\) = bulk transconductance
- \(C_{gg}, C_{gs}, C_{gd}, C_{gb}\) are computed from BSIM4v6 charge model
- \(\omega\) is obtained from `ckt->CKTomega` in SPICE

#### 1.3 Gate Resistance Modeling for RF Analysis

For RF simulations, BSIM4v6 includes distributed gate resistance:

\[
R_g^{eff} = R_{g,cont} + \frac{R_{g,sheet}}{N_{finger}} \cdot \frac{W}{L_{gate}}
\]

This resistance is stamped as a series element in the gate branch, modifying \(Y_{gg}\):

\[
Y_{gg}^{RF} = \frac{1}{R_g^{eff} + \frac{1}{j\omega C_{gg}}}
\]

#### 1.4 Substrate Network Parasitics

BSIM4v6 includes substrate resistances and capacitances for RF modeling:

\[
Y_{bs} = \frac{1}{R_{bs}} + j\omega C_{bs} \cdot \left(1 + \alpha_{sub} \cdot \frac{V_{bs}}{V_{bi}}\right)
\]
\[
Y_{bd} = \frac{1}{R_{bd}} + j\omega C_{bd} \cdot \left(1 + \alpha_{sub} \cdot \frac{V_{bd}}{V_{bi}}\right)
\]

Where \(R_{bs}, R_{bd}, C_{bs}, C_{bd}\) are instance parameters stamped into the matrix.

#### 1.5 Pole-Zero Analysis Formulation

For SPICE pole-zero analysis, the s-domain formulation uses:

\[
Y_{pz}(s) = G + s \cdot C + \frac{\partial^2 I}{\partial V^2} \cdot \Delta V
\]

Where \(s = \sigma + j\omega\) is the complex frequency variable from SPICE's pole-zero analysis.

### 2. Noise Analysis Formulation for SPICE .NOISE Analysis

BSIM4v6 implements comprehensive noise models for SPICE's noise analysis capability, with configurable model selectors.

#### 2.1 Thermal Noise Spectral Density

**Core Thermal Noise Equation:**
\[
S_{id,th}(f) = 4k_B T \cdot g_{ds0} \cdot \gamma_{th} \cdot \frac{1}{1 + \left(\frac{f}{f_c}\right)^2}
\]

Where:
- \(k_B = \text{CONSTboltz}\) = Boltzmann constant in SPICE
- \(T = \text{B4v6temp}\) = device temperature
- \(g_{ds0} = \text{B4v6gds0}\) = output conductance at Vds = 0
- \(f_c\) = corner frequency for velocity saturation effects

**BSIM4v6-Specific Thermal Noise Coefficient:**
\[
\gamma_{th} = \frac{2}{3} \cdot \frac{1 + \eta + \eta^2}{1 + \eta} \cdot \frac{1}{1 + \left(\frac{V_{ds}}{E_{sat}L_{eff}}\right)^2}
\]
\[
\eta = \frac{V_{gs} - V_{th}}{V_{dsat}}
\]

**Velocity Saturation Correction (v6 Enhancement):**
\[
\gamma_{th}^{v6} = \gamma_{th}^{v5} \cdot \frac{1}{1 + \left(\frac{V_{ds}}{E_{sat}L_{eff}}\right)^2}
\]

#### 2.2 Induced Gate Noise (IGN) for RF Analysis

For RF noise analysis with `tnoimod ≥ 2`:

\[
S_{ig,ind}(f) = 4k_B T \cdot \delta_{ig} \cdot \frac{\omega^2 C_{gs}^2}{5g_{ds0}} \cdot \frac{1}{1 + \left(\frac{f}{f_{ig}}\right)^2}
\]

**Correlation Between Drain and Gate Noise:**
\[
S_{igd,corr}(f) = j \cdot c \cdot \sqrt{S_{id,th}(f) \cdot S_{ig,ind}(f)}
\]
\[
c = 0.395j \quad \text{(BSIM4v6 default correlation coefficient)}
\]

This correlation is stamped as a complex source in SPICE's noise correlation matrix.

#### 2.3 Flicker (1/f) Noise Models

BSIM4v6 provides multiple flicker noise models selectable via `fnoimod` parameter:

**Model 1 (fnoimod = 1) - SPICE2-based:**
\[
S_{id,fl}(f) = \frac{KF \cdot I_d^{AF}}{C_{ox} L_{eff}^2 f^{EF}}
\]

**Model 2 (fnoimod = 2) - BSIM4v6 Advanced:**
\[
S_{id,fl}^{v6}(f) = \frac{q^2 k_B T \lambda N_t}{WLC_{ox}^2 f} \cdot 
\left[ \frac{1}{N} + \alpha_{sc} \left(\frac{\mu_{eff}}{\mu_0}\right)^2 \right] \cdot
I_d^2 \cdot F_{v6}(V_{gs}, V_{ds})
\]

Where:
\[
F_{v6}(V_{gs}, V_{ds}) = \frac{1}{V_{ds}} \int_0^{V_{ds}} \frac{1}{N(x)^2} dx
\]

**Model 3 (fnoimod = 3) - Unified Flicker Noise:**
\[
S_{id,fl}^{v6}(f) = \frac{1}{f^{EF}} \cdot 
\left[ NOIA \cdot \frac{k_B T}{q} \cdot \frac{I_d}{g_m} + 
NOIB \cdot I_d^2 + 
NOIC \cdot \frac{I_d^3}{g_m} \right] \cdot
G_{v6}(L_{eff}, W_{eff})
\]

**Temperature Dependence for All Models:**
\[
S_{id,fl}(T) = S_{id,fl}(T_0) \cdot \left(\frac{T}{T_0}\right)^{NT}
\]

#### 2.4 Geometry Scaling for Noise in v6

BSIM4v6 introduces refined geometry scaling for noise:

\[
S_{fl}^{v6} = S_{fl}^{v5} \cdot \left(\frac{L_{eff,ref}}{L_{eff}}\right)^{LNF} \cdot \left(\frac{W_{eff,ref}}{W_{eff}}\right)^{WNF}
\]

#### 2.5 Total Noise Spectral Density

The complete noise PSD stamped into SPICE's noise matrix is:

\[
S_{id,total}(f) = S_{id,th}(f) + \frac{S_{id,fl}(f)}{1 + \left(\frac{f}{f_c}\right)^2}
\]

For RF analysis with induced gate noise, SPICE stamps a 2×2 noise correlation matrix:

\[
\mathbf{S}(f) = \begin{bmatrix}
S_{id,total}(f) & S_{igd,corr}(f) \\
S_{igd,corr}^*(f) & S_{ig,ind}(f)
\end{bmatrix}
\]

### 3. Capacitance Model Formulation

#### 3.1 BSIM4v6 Charge-Based Capacitance Model

The capacitances for AC analysis are derived from charge conservation:

\[
Q_g = Q_{gs} + Q_{gd} + Q_{gb}
\]
\[
Q_b = Q_{bs} + Q_{bd}
\]

**Capacitance Definitions for Matrix Stamping:**
\[
C_{gg} = \frac{\partial Q_g}{\partial V_g}, \quad C_{gd} = \frac{\partial Q_g}{\partial V_d}, \quad C_{gs} = \frac{\partial Q_g}{\partial V_s}, \quad C_{gb} = \frac{\partial Q_g}{\partial V_b}
\]
\[
C_{dd} = \frac{\partial Q_d}{\partial V_d}, \quad C_{ss} = \frac{\partial Q_s}{\partial V_s}, \quad C_{bb} = \frac{\partial Q_b}{\partial V_b}
\]

#### 3.2 Overlap and Fringing Capacitances

BSIM4v6 includes gate overlap capacitances:

\[
C_{gso} = C_{GSO} \cdot W_{eff}
\]
\[
C_{gdo} = C_{GDO} \cdot W_{eff}
\]
\[
C_{gbo} = C_{GBO} \cdot L_{eff}
\]

These are added to the intrinsic capacitances for complete AC response.

## Convergence Analysis

### 4.1 Frequency-Domain Convergence Criteria

For AC analysis convergence, BSIM4v6 implements:

#### 4.1.1 Matrix Condition Number Checking

The complex admittance matrix condition number is monitored:

\[
\kappa(Y_{ac}) = \|Y_{ac}\| \cdot \|Y_{ac}^{-1}\|
\]

If \(\kappa(Y_{ac}) > 10^{12}\), SPICE issues a warning and adds GMIN to diagonal elements.

#### 4.1.2 Frequency Step Adaptation

For AC sweep analysis, frequency step is adapted based on response curvature:

\[
\Delta f_{n+1} = \Delta f_n \cdot \min\left(2.0, \frac{\epsilon_{target}}{\max(\epsilon_{Re}, \epsilon_{Im})}\right)
\]

Where:
\[
\epsilon_{Re} = \left|\frac{\Re\{Y(f_{n+1})\} - \Re\{Y(f_n)\}}{\Re\{Y(f_n)\}}\right|
\]
\[
\epsilon_{Im} = \left|\frac{\Im\{Y(f_{n+1})\} - \Im\{Y(f_n)\}}{\Im\{Y(f_n)\}}\right|
\]

### 4.2 Noise Analysis Convergence

#### 4.2.1 Noise Matrix Positive-Definiteness Check

For the 2×2 noise correlation matrix:

\[
\mathbf{S}(f) = \begin{bmatrix}
S_{11} & S_{12} \\
S_{21} & S_{22}
\end{bmatrix}
\]

The matrix must satisfy:
1. \(S_{11} > 0\) and \(S_{22} > 0\) (positive PSDs)
2. \(S_{11}S_{22} - |S_{12}|^2 \geq 0\) (Schur complement condition)

If these conditions fail, BSIM4v6 adjusts the correlation coefficient:
\[
c_{adjusted} = c \cdot \sqrt{\frac{S_{11}S_{22}}{|S_{12}|^2}}
\]

#### 4.2.2 Frequency-Dependent Noise Convergence

Noise spectral density must be smooth across frequency:

\[
\left|\frac{dS_{id}(f)}{df} \cdot \frac{f}{S_{id}(f)}\right| < \epsilon_{noise}
\]

Default: \(\epsilon_{noise} = 0.1\) (10% maximum relative slope)

### 4.3 Pole-Zero Analysis Convergence

#### 4.3.1 Root Refinement Algorithm

For pole-zero location refinement using Newton-Raphson:

\[
s_{k+1} = s_k - \frac{\det(Y(s_k))}{\frac{d}{ds}\det(Y(s))|_{s=s_k}}
\]

Convergence criterion:
\[
|s_{k+1} - s_k| < \epsilon_{pz} \cdot \max(|s_k|, 1.0)
\]

Default: \(\epsilon_{pz} = 10^{-6}\)

#### 4.3.2 Root Sensitivity Check

Poles and zeros must have low sensitivity to matrix perturbations:

\[
\text{Sensitivity} = \left\|\frac{\partial s}{\partial Y} \cdot \Delta Y\right\| < \epsilon_{sens}
\]

Where \(\Delta Y\) represents numerical round-off level.

### 4.4 RF-Specific Convergence Enhancements

#### 4.4.1 Gate Resistance Stability Criterion

For RF stability, the gate resistance must satisfy:

\[
R_g < \frac{1}{\omega C_{gg}} \cdot \frac{1}{Q_{min}}
\]

Where \(Q_{min} = 0.1\) ensures numerical stability in AC analysis.

#### 4.4.2 Substrate Network Convergence

Substrate admittances must maintain:

\[
\Re\{Y_{bs}\} > \text{GMIN} \quad \text{and} \quad \Re\{Y_{bd}\} > \text{GMIN}
\]

GMIN = \(10^{-12}\) S (SPICE minimum conductance)

### 4.5 Noise Model Selector-Based Convergence

Different noise models have specific convergence requirements:

#### 4.5.1 Thermal Noise Models (`tnoimod`)

- **tnoimod = 1 (SPICE2)**: Requires \(g_m > \text{GMIN}\) for noise calculation
- **tnoimod = 2 (BSIM3)**: Additional check: \(V_{ds} < 10 \cdot V_{dsat}\)
- **tnoimod = 3 (BSIM4)**: Requires \(f < 0.1 \cdot f_T\) for IGN validity
- **tnoimod = 4 (BSIM4v6)**: Velocity saturation check: \(V_{ds} < 5 \cdot E_{sat}L_{eff}\)

#### 4.5.2 Flicker Noise Models (`fnoimod`)

- **fnoimod = 1**: Requires \(I_d > 10^{-12}\) A for meaningful noise
- **fnoimod = 2**: Checks trap density: \(N_t < 10^{20} \text{cm}^{-3}\)
- **fnoimod = 3**: Validates \(NOIA, NOIB, NOIC > 0\)
- **fnoimod = 4 (v6)**: Additional geometry scaling convergence check

### 4.6 Numerical Integration for Transient Noise

For transient noise analysis, BSIM4v6 implements:

#### 4.6.1 Noise Source Integration

\[
i_n(t) = \sqrt{2S_{id}(f_c)} \cdot \xi(t) + \int_0^t h(\tau) \cdot \xi(t-\tau) d\tau
\]

Where \(\xi(t)\) is white Gaussian noise and \(h(\tau)\) is the noise shaping filter.

#### 4.6.2 Convergence Criterion for Transient Noise

\[
\frac{\langle i_n^2(t) \rangle_{simulated} - S_{id}(f_c) \cdot \Delta f}{S_{id}(f_c) \cdot \Delta f} < \epsilon_{noise,int}
\]

Default: \(\epsilon_{noise,int} = 0.01\) (1% error tolerance)

### 4.7 AC Analysis Step Size Control

For .AC analysis, BSIM4v6 implements adaptive frequency stepping:

\[
\Delta f_{new} = \Delta f_{old} \cdot \min\left(1.5, \frac{\epsilon_{target}}{\max(\Delta |Y|/\Delta f)}\right)
\]

Where \(\Delta |Y|/\Delta f\) is the admittance change per frequency step.

### 4.8 Correlation Matrix Regularization

When the noise correlation matrix becomes ill-conditioned:

\[
\mathbf{S}_{regularized} = \mathbf{S} + \lambda \mathbf{I}
\]

Where \(\lambda = 10^{-6} \cdot \text{trace}(\mathbf{S})\) ensures positive definiteness while minimizing perturbation.

This comprehensive convergence analysis ensures robust and accurate RF, capacitance, and noise simulations in SPICE across all BSIM4v6 operating regions and analysis types.

## C Implementation

### 1. Core Data Structures for RF and Noise Analysis

The BSIM4v6 RF modeling and noise analysis implementation in Ngspice is built upon two primary C structures defined in `bsim4v6def.h`. These structures store all parameters, state variables, and matrix pointers required for frequency-domain analysis.

#### 1.1 BSIM4v6 Model Structure (`sBSIM4v6model`)

The model structure contains process-specific parameters shared across all instances, with specific fields for RF and noise modeling:

```c
typedef struct sBSIM4v6model {
    /* Device type identification */
    int B4v6type;                    /* NCH or PCH device type */
    
    /* Core DC parameters (used for linearization) */
    double B4v6vth0;                 /* Threshold voltage at reference temperature */
    double B4v6k1;                   /* First-order body effect coefficient */
    double B4v6k2;                   /* Second-order body effect coefficient */
    double B4v6u0;                   /* Low-field mobility */
    double B4v6vsat;                 /* Saturation velocity */
    
    /* RF-specific parameters */
    double B4v6rg;                   /* Gate resistance for RF modeling */
    double B4v6rds;                  /* Drain-source resistance */
    double B4v6rbs;                  /* Bulk-source resistance */
    double B4v6rbd;                  /* Bulk-drain resistance */
    
    /* Noise model selectors and parameters */
    int B4v6tnoimod;                 /* Thermal noise model selector (0-4) */
    int B4v6fnoimod;                 /* Flicker noise model selector (0-4) */
    double B4v6noia;                 /* Unified flicker noise parameter A */
    double B4v6noib;                 /* Unified flicker noise parameter B */
    double B4v6noic;                 /* Unified flicker noise parameter C */
    double B4v6em;                   /* Saturation field for noise calculation */
    double B4v6af;                   /* Flicker noise current exponent */
    double B4v6ef;                   /* Flicker noise frequency exponent */
    double B4v6kf;                   /* SPICE2 flicker noise coefficient */
    
    /* Linked list management */
    struct sBSIM4v6model *B4v6nextModel;
    sBSIM4v6instance *B4v6instances;
} BSIM4v6model;
```

**Mathematical Mapping**: The `B4v6tnoimod` and `B4v6fnoimod` integers directly control which mathematical noise formulations are used in simulation. For example, `tnoimod = 3` selects the BSIM4 holistic noise model including induced gate noise (IGN), while `fnoimod = 3` selects the unified flicker noise model.

#### 1.2 BSIM4v6 Instance Structure (`sBSIM4v6instance`)

The instance structure stores layout-specific parameters and dynamic simulation state for each MOSFET:

```c
typedef struct sBSIM4v6instance {
    /* Node indices for SPICE Modified Nodal Analysis */
    int B4v6dNode;                   /* External drain node index */
    int B4v6gNode;                   /* External gate node index */
    int B4v6sNode;                   /* External source node index */
    int B4v6bNode;                   /* External bulk node index */
    
    /* Operating point voltages and current */
    double B4v6vds;                  /* Drain-source voltage */
    double B4v6vgs;                  /* Gate-source voltage */
    double B4v6vbs;                  /* Bulk-source voltage */
    double B4v6ids;                  /* Drain current */
    
    /* Small-signal parameters (calculated from DC operating point) */
    double B4v6gm;                   /* Transconductance: ∂Id/∂Vgs */
    double B4v6gds;                  /* Output conductance: ∂Id/∂Vds */
    double B4v6gmb;                  /* Bulk transconductance: ∂Id/∂Vbs */
    double B4v6gds0;                 /* Output conductance at Vds=0 for noise */
    
    /* BSIM4v6 capacitance matrix elements */
    double B4v6cgg;                  /* Total gate capacitance */
    double B4v6cgs;                  /* Gate-source capacitance */
    double B4v6cgd;                  /* Gate-drain capacitance */
    double B4v6cgb;                  /* Gate-bulk capacitance */
    double B4v6cdd;                  /* Drain capacitance */
    double B4v6css;                  /* Source capacitance */
    double B4v6cbb;                  /* Bulk capacitance */
    double B4v6cds;                  /* Drain-source capacitance */
    double B4v6cdb;                  /* Drain-bulk capacitance */
    double B4v6cbs;                  /* Bulk-source capacitance */
    
    /* Noise-specific parameters */
    double B4v6gammaNoise;           /* Thermal noise coefficient γ */
    double B4v6fc;                   /* Corner frequency for noise roll-off */
    double B4v6noiseDens;            /* Cached noise spectral density */
    
    /* Sparse matrix pointers for 4×4 admittance matrix stamping */
    double *B4v6drainDrainPtr;       /* Ydd element pointer */
    double *B4v6drainGatePtr;        /* Ydg element pointer */
    double *B4v6drainSourcePtr;      /* Yds element pointer */
    double *B4v6drainBulkPtr;        /* Ydb element pointer */
    double *B4v6gateDrainPtr;        /* Ygd element pointer */
    double *B4v6gateGatePtr;         /* Ygg element pointer */
    double *B4v6gateSourcePtr;       /* Ygs element pointer */
    double *B4v6gateBulkPtr;         /* Ygb element pointer */
    double *B4v6sourceDrainPtr;      /* Ysd element pointer */
    double *B4v6sourceGatePtr;       /* Ysg element pointer */
    double *B4v6sourceSourcePtr;     /* Yss element pointer */
    double *B4v6sourceBulkPtr;       /* Ysb element pointer */
    double *B4v6bulkDrainPtr;        /* Ybd element pointer */
    double *B4v6bulkGatePtr;         /* Ybg element pointer */
    double *B4v6bulkSourcePtr;       /* Ybs element pointer */
    double *B4v6bulkBulkPtr;         /* Ybb element pointer */
    
    /* Linked list pointers */
    struct sBSIM4v6instance *B4v6nextInstance;
    BSIM4v6model *B4v6modPtr;
} BSIM4v6instance;
```

**SPICE Integration**: The matrix pointers (e.g., `B4v6drainDrainPtr`) directly reference positions in Ngspice's sparse matrix system. These pointers are initialized during device setup and used to stamp the complex admittance matrix `Y = G + jωC` during AC analysis.

### 2. AC Matrix Stamping Implementation (`b4v6acld.c`)

#### 2.1 Core AC Load Function

The `B4v6acLoad()` function in `b4v6acld.c` implements the small-signal admittance matrix stamping for frequency-domain analysis:

```c
int B4v6acLoad(GENmodel *inModel, CKTcircuit *ckt) {
    BSIM4v6model *model = (BSIM4v6model*)inModel;
    BSIM4v6instance *here;
    
    /* Loop through all models and instances */
    for(; model != NULL; model = model->B4v6nextModel) {
        for(here = model->B4v6instances; here != NULL; here = here->B4v6nextInstance) {
            
            /* Extract angular frequency from SPICE circuit */
            double omega = ckt->CKTomega;  /* Already 2πf in Ngspice */
            double s_imag = omega;         /* jω term for capacitive stamping */
            
            /* Retrieve pre-computed small-signal parameters */
            double gm = here->B4v6gm;      /* ∂Id/∂Vgs from DC operating point */
            double gds = here->B4v6gds;    /* ∂Id/∂Vds */
            double gmb = here->B4v6gmb;    /* ∂Id/∂Vbs */
            
            /* Retrieve BSIM4v6 capacitance matrix elements */
            double cgg = here->B4v6cgg;
            double cgs = here->B4v6cgs;
            double cgd = here->B4v6cgd;
            double cgb = here->B4v6cgb;
            double cdd = here->B4v6cdd;
            double css = here->B4v6css;
            double cbb = here->B4v6cbb;
            
            /* ----- Real Part Stamping (Conductance Matrix G) ----- */
            
            /* Drain row conductances */
            *(here->B4v6drainDrainPtr) += gds;                     /* Gdd = gds */
            *(here->B4v6drainGatePtr) -= gm;                       /* Gdg = -gm */
            *(here->B4v6drainSourcePtr) -= (gds + gm + gmb);       /* Gds = -(gds + gm + gmb) */
            *(here->B4v6drainBulkPtr) += gmb;                      /* Gdb = gmb */
            
            /* Source row conductances (by symmetry) */
            *(here->B4v6sourceDrainPtr) -= gds;                    /* Gsd = -gds */
            *(here->B4v6sourceGatePtr) -= gm;                      /* Gsg = -gm */
            *(here->B4v6sourceSourcePtr) += (gds + gm + gmb);      /* Gss = gds + gm + gmb */
            *(here->B4v6sourceBulkPtr) -= gmb;                     /* Gsb = -gmb */
            
            /* ----- Imaginary Part Stamping (Capacitance Matrix C) ----- */
            
            /* Drain row capacitances */
            *(here->B4v6drainDrainPtr) += s_imag * (cdd + cgd);    /* jω(Cdd + Cgd) */
            *(here->B4v6drainGatePtr) += s_imag * cgd;             /* jωCgd */
            *(here->B4v6drainSourcePtr) += s_imag * here->B4v6cds; /* jωCds */
            *(here->B4v6drainBulkPtr) += s_imag * here->B4v6cdb;   /* jωCdb */
            
            /* Gate row capacitances */
            *(here->B4v6gateGatePtr) += s_imag * (cgg + cgd + cgb); /* jω(Cgg + Cgd + Cgb) */
            *(here->B4v6gateDrainPtr) += s_imag * cgd;              /* jωCgd */
            *(here->B4v6gateSourcePtr) += s_imag * cgs;             /* jωCgs */
            *(here->B4v6gateBulkPtr) += s_imag * cgb;              /* jωCgb */
            
            /* Source row capacitances */
            *(here->B4v6sourceSourcePtr) += s_imag * (css + cgs);   /* jω(Css + Cgs) */
            *(here->B4v6sourceGatePtr) += s_imag * cgs;             /* jωCgs */
            *(here->B4v6sourceDrainPtr) += s_imag * here->B4v6cds;  /* jωCds */
            *(here->B4v6sourceBulkPtr) += s_imag * here->B4v6cbs;   /* jωCbs */
            
            /* Bulk row capacitances */
            *(here->B4v6bulkBulkPtr) += s_imag * (cbb + cbd + cbs); /* jω(Cbb + Cbd + Cbs) */
            *(here->B4v6bulkDrainPtr) += s_imag * here->B4v6cdb;    /* jωCbd */
            *(here->B4v6bulkSourcePtr) += s_imag * here->B4v6cbs;   /* jωCbs */
            *(here->B4v6bulkGatePtr) += s_imag * cgb;              /* jωCgb */
            
            /* ----- RF-Specific Stamping (Gate Resistance) ----- */
            if(here->B4v6rg > 0.0) {
                /* Stamp gate resistance as series admittance */
                double Yg = 1.0 / here->B4v6rg;
                *(here->B4v6gateGatePtr) += Yg;  /* Real admittance to ground */
            }
            
            /* ----- Substrate Network Parasitics ----- */
            if(here->B4v6rbs > 0.0) {
                /* Bulk-source resistance and capacitance */
                double Ybs = 1.0 / here->B4v6rbs;
                *(here->B4v6bulkSourcePtr) += Ybs + s_imag * here->B4v6cbs;
                *(here->B4v6sourceBulkPtr) += Ybs + s_imag * here->B4v6cbs;
            }
            
            if(here->B4v6rbd > 0.0) {
                /* Bulk-drain resistance and capacitance */
                double Ybd = 1.0 / here->B4v6rbd;
                *(here->B4v6bulkDrainPtr) += Ybd + s_imag * here->B4v6cdb;
                *(here->B4v6drainBulkPtr) += Ybd + s_imag * here->B4v6cdb;
            }
        }
    }
    return OK;  /* Ngspice success code */
}
```

**Mathematical Mapping**: This function directly implements the complex admittance matrix:
\[
\begin{bmatrix}
Y_{dd} & Y_{dg} & Y_{ds} & Y_{db} \\
Y_{gd} & Y_{gg} & Y_{gs} & Y_{gb} \\
Y_{sd} & Y_{sg} & Y_{ss} & Y_{sb} \\
Y_{bd} & Y_{bg} & Y_{bs} & Y_{bb}
\end{bmatrix}
=
\begin{bmatrix}
g_{ds} + j\omega(C_{dd} + C_{gd}) & -g_m + j\omega C_{gd} & -(g_{ds} + g_m + g_{mb}) + j\omega C_{ds} & g_{mb} + j\omega C_{db} \\
j\omega C_{gd} & j\omega(C_{gg} + C_{gd} + C_{gb}) & j\omega C_{gs} & j\omega C_{gb} \\
-g_{ds} + j\omega C_{sd} & -g_m + j\omega C_{sg} & g_{ds} + g_m + g_{mb} + j\omega(C_{ss} + C_{gs}) & -g_{mb} + j\omega C_{sb} \\
j\omega C_{bd} & j\omega C_{bg} & j\omega C_{bs} & j\omega(C_{bb} + C_{bd} + C_{bs})
\end{bmatrix}
\]

**SPICE Integration**: The function uses `ckt->CKTomega` which contains the angular frequency `2πf` for the current AC analysis point. The matrix pointers add contributions directly to Ngspice's sparse matrix system.

### 3. Pole-Zero Analysis Implementation (`b4v6pzld.c`)

#### 3.1 Pole-Zero Load Function

The `B4v6pzLoad()` function handles s-domain analysis for pole-zero computation:

```c
int B4v6pzLoad(GENmodel *inModel, CKTcircuit *ckt, SPcomplex *s) {
    BSIM4v6model *model = (BSIM4v6model*)inModel;
    BSIM4v6instance *here;
    
    for(; model != NULL; model = model->B4v6nextModel) {
        for(here = model->B4v6instances; here != NULL; here = here->B4v6nextInstance) {
            
            /* Extract complex frequency s = σ + jω */
            double s_real = s->real;  /* σ (real part) */
            double s_imag = s->imag;  /* ω (imaginary part) */
            
            /* Retrieve small-signal parameters */
            double gm = here->B4v6gm;
            double gds = here->B4v6gds;
            double gmb = here->B4v6gmb;
            
            /* Retrieve capacitances */
            double c