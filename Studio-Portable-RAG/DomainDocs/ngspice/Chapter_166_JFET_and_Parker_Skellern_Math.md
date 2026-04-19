# JFET: Classic Equations and the Parker-Skellern Macro-Model

_Generated 2026-04-13 02:09 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfetload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet/jfettemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2defs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2load.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/jfet2temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/psmodel.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/jfet2/psmodel.c`

# Chapter: JFET: Classic Equations and the Parker-Skellern Macro-Model

## Technical Introduction

This chapter documents the implementation of the Junction Field-Effect Transistor (JFET) model within the Ngspice circuit simulator, focusing on two complementary representations: the classic Shockley square-law model and the enhanced Parker-Skellern macro-model. The implementation spans ten core source files that define the complete device behavior:

- **`jfetdefs.h` & `jfet2defs.h`**: Contain the fundamental C structure definitions (`sJFETmodel`, `sJFETinstance`) that store model parameters, instance-specific data, and simulation state variables for both the standard and enhanced models.

- **`jfetpar.c` & `jfet2par.c`**: Implement the parameter parsing and binding logic that maps SPICE netlist parameters (e.g., `VTO`, `BETA`, `LAMBDA`) to the internal C structure fields, including validation and default value assignment.

- **`jfetload.c` & `jfet2load.c`**: House the core computational engine. These files implement the `JFETload()` function, which evaluates the device's current-voltage characteristics, computes small-signal parameters (`gm`, `gds`), and stamps contributions into the circuit's Modified Nodal Analysis (MNA) matrix and right-hand-side vector during DC and transient analysis.

- **`jfettemp.c` & `jfet2temp.c`**: Manage temperature-dependent effects. They implement the `JFETtemp()` function, which scales critical model parameters (threshold voltage `VTO`, transconductance `BETA`, saturation current `IS`) based on the operating temperature and predefined temperature coefficients (`XTB`, `XTI`, `TCV`).

- **`psmodel.h` & `psmodel.c`**: Define the Parker-Skellern macro-model extension. This is not a separate device but a set of additional parameters and modified equations that augment the standard JFET model. The `psmodel.c` file provides the specific routines that calculate the modified saturation current using an empirical exponent `M` and adjusted channel-length modulation, offering improved accuracy for modern JFET devices.

Collectively, these files implement the full SPICE `DEVICE` interface for the JFET, translating the device's physics—governed by the classic gradual channel approximation and extended by empirical macro-model corrections—into the numerical framework required for nonlinear Newton-Raphson iteration, sparse matrix solution, and robust convergence within Ngspice.

## 1. Mathematical Formulation

The JFET model in Ngspice implements the classical Shockley square-law equations for the intrinsic FET, extended by the Parker-Skellern macro-model to account for practical device parasitics and high-frequency effects. The mathematical formulation is structured within the Modified Nodal Analysis (MNA) framework, where the device contributes stamp entries to the circuit Jacobian matrix based on its terminal voltages.

### 1.1 Intrinsic DC Model (Classic Shockley Equations)

The core DC model defines the drain current \(I_D\) as a function of gate-source (\(V_{GS}\)) and drain-source (\(V_{DS}\)) voltages, with distinct regions of operation.

**Cutoff Region** (\(V_{GS} \leq V_{TO}\)):
\[
I_D = 0
\]
where \(V_{TO}\) is the threshold voltage (pinch-off voltage).

**Linear (Triode) Region** (\(V_{GS} > V_{TO}\) and \(0 \leq V_{DS} \leq V_{GS} - V_{TO}\)):
\[
I_D = \beta \left[ 2 (V_{GS} - V_{TO}) V_{DS} - V_{DS}^2 \right] (1 + \lambda V_{DS})
\]
Here, \(\beta = \frac{\text{BETA}}{(1 + \text{THETA} \cdot (V_{GS} - V_{TO}))}\) is the transconductance parameter, incorporating mobility degradation via the THETA parameter. \(\lambda\) is the channel-length modulation parameter.

**Saturation Region** (\(V_{GS} > V_{TO}\) and \(V_{DS} > V_{GS} - V_{TO}\)):
\[
I_D = \beta (V_{GS} - V_{TO})^2 (1 + \lambda V_{DS})
\]

The gate currents are modeled as ideal diode equations for the gate-source and gate-drain junctions:
\[
I_{GS} = I_S \left[ \exp\left(\frac{V_{GS}}{N V_T}\right) - 1 \right] + \frac{V_{GS}}{R_{GS}}
\]
\[
I_{GD} = I_S \left[ \exp\left(\frac{V_{GD}}{N V_T}\right) - 1 \right] + \frac{V_{GD}}{R_{GD}}
\]
where \(I_S\) is the saturation current, \(N\) is the emission coefficient, \(V_T = kT/q\) is the thermal voltage, and \(R_{GS}\), \(R_{GD}\) are parasitic resistances.

### 1.2 Parker-Skellern Macro-Model Extensions

The Parker-Skellern model extends the intrinsic FET with a comprehensive network of parasitics essential for accurate RF and analog simulation.

**Parasitic Resistances:**
- Drain resistance: \(R_D\)
- Source resistance: \(R_S\)
- Gate metallization resistance: \(R_G\)

These are stamped as constant conductances in the MNA matrix: \(G_D = 1/R_D\), \(G_S = 1/R_S\), \(G_G = 1/R_G\).

**Parasitic Capacitances (Voltage-Dependent):**
- Gate-source depletion capacitance:
\[
C_{GS}(V_{GS}) = \begin{cases}
\frac{C_{GS0}}{\left(1 - \frac{V_{GS}}{V_{BI}}\right)^{M_{GS}}}, & V_{GS} \leq FC \cdot V_{BI} \\
\frac{C_{GS0}}{(1-FC)^{M_{GS}}} \left[ 1 - FC(1+M_{GS}) + M_{GS}\frac{V_{GS}}{V_{BI}} \right], & V_{GS} > FC \cdot V_{BI}
\end{cases}
\]
- Gate-drain depletion capacitance \(C_{GD}(V_{GD})\) follows an identical form.
- Drain-source capacitance \(C_{DS}\) is modeled as a constant or voltage-dependent junction capacitance.

Here, \(C_{GS0}\), \(C_{GD0}\) are zero-bias capacitances, \(V_{BI}\) is the built-in potential, \(M_{GS}\), \(M_{GD}\) are grading coefficients, and \(FC\) is the forward-bias coefficient (typically 0.5).

**Charge Conservation Formulation:**
For transient analysis, the nonlinear capacitances are modeled via charge conservation. The stored charge is the integral of capacitance:
\[
Q_{GS}(V_{GS}) = \int_0^{V_{GS}} C_{GS}(v)\,dv
\]
A similar definition holds for \(Q_{GD}(V_{GD})\). The derivatives of these charges provide the capacitive currents and the Jacobian entries during Newton-Raphson iteration.

### 1.3 Small-Signal AC Model

For AC analysis, the device is linearized around the DC operating point. The small-signal model contributes a complex admittance stamp to the MNA matrix \( \mathbf{Y} = \mathbf{G} + j\omega\mathbf{C} \).

**Transconductance and Output Conductance:**
The key small-signal parameters derived from the DC model are:
\[
g_m = \frac{\partial I_D}{\partial V_{GS}} \quad \text{(transconductance)}
\]
\[
g_{ds} = \frac{\partial I_D}{\partial V_{DS}} \quad \text{(output conductance)}
\]
\[
g_{gs} = \frac{\partial I_{GS}}{\partial V_{GS}} \quad \text{(gate-source conductance)}
\]
\[
g_{gd} = \frac{\partial I_{GD}}{\partial V_{GD}} \quad \text{(gate-drain conductance)}
\]

**AC Matrix Stamp:**
For a 3-terminal JFET (Drain, Gate, Source), the linearized conductance matrix stamp at the operating point is:
\[
\begin{bmatrix}
g_{ds} & 0 & -g_{ds} \\
-g_m & g_{gs}+g_{gd} & g_m-g_{gs} \\
g_m-g_{ds} & -g_{gs} & g_{ds}+g_{gs}-g_m
\end{bmatrix}
\]
To this, the capacitive susceptance \(j\omega\mathbf{C}\) is added, where \(\mathbf{C}\) is the matrix of capacitances \(C_{GS}\), \(C_{GD}\), \(C_{DS}\).

### 1.4 Noise Model

The intrinsic noise sources are modeled with spectral densities for inclusion in AC noise analysis.

**Thermal Noise:** The channel thermal noise is modeled as a current source between drain and source:
\[
\overline{i_{nd}^2} = 4kT \cdot \frac{2}{3} g_{m0} \cdot \Delta f
\]
where \(g_{m0}\) is the zero-bias transconductance.

**Flicker (1/f) Noise:** Modeled as a voltage source in series with the gate:
\[
\overline{v_{ng}^2} = \frac{KF \cdot I_D^{AF}}{f \cdot C_{GS0}^2} \cdot \Delta f
\]
where \(KF\) is the flicker noise coefficient, \(AF\) is the flicker noise exponent (typically ~1).

**Shot Noise:** From the gate junction diodes:
\[
\overline{i_{ngs}^2} = 2q I_{GS} \cdot \Delta f, \quad \overline{i_{ngd}^2} = 2q I_{GD} \cdot \Delta f
\]

These noise sources are correlated and are stamped into the noise correlation matrix using the adjoint method.

## 2. Convergence Analysis

Convergence in SPICE for the JFET model relies on the Newton-Raphson algorithm applied to the nonlinear MNA equations. The Parker-Skellern macro-model, with its multiple diodes and voltage-dependent capacitances, introduces specific challenges.

### 2.1 Newton-Raphson Formulation

The circuit equations are written as \(\mathbf{F}(\mathbf{x}) = 0\), where \(\mathbf{x}\) is the vector of node voltages and branch currents. For the JFET, the contributions to \(\mathbf{F}\) are the current balance equations at its terminals:
\[
F_D: I_D(V_{GS}, V_{DS}) + I_{GD}(V_{GD}) + \frac{dQ_{GD}}{dt} - I_{node\_D} = 0
\]
\[
F_G: I_{GS}(V_{GS}) + I_{GD}(V_{GD}) + \frac{dQ_{GS}}{dt} + \frac{dQ_{GD}}{dt} - I_{node\_G} = 0
\]
\[
F_S: -I_D(V_{GS}, V_{DS}) - I_{GS}(V_{GS}) - \frac{dQ_{GS}}{dt} - I_{node\_S} = 0
\]

The Newton-Raphson update is:
\[
\mathbf{J}^{(k)} \Delta \mathbf{x}^{(k)} = -\mathbf{F}(\mathbf{x}^{(k)})
\]
where the Jacobian \(\mathbf{J} = \partial \mathbf{F}/\partial \mathbf{x}\) contains the device derivatives: conductances (\(g_m, g_{ds}, g_{gs}, g_{gd}\)) and capacitive derivatives (\( \partial Q/\partial V \)).

### 2.2 Jacobian Stamping for the JFET

The Jacobian contribution from the JFET is a 3x3 matrix plus derivatives with respect to any internal nodes (e.g., intrinsic drain, source). For the intrinsic nodes:
\[
\mathbf{J}_{FET} = \begin{bmatrix}
\frac{\partial F_D}{\partial V_D} & \frac{\partial F_D}{\partial V_G} & \frac{\partial F_D}{\partial V_S} \\
\frac{\partial F_G}{\partial V_D} & \frac{\partial F_G}{\partial V_G} & \frac{\partial F_G}{\partial V_S} \\
\frac{\partial F_S}{\partial V_D} & \frac{\partial F_S}{\partial V_G} & \frac{\partial F_S}{\partial V_S}
\end{bmatrix}
\]
where, for DC analysis:
\[
\frac{\partial F_D}{\partial V_G} = -g_m + g_{gd}, \quad \frac{\partial F_D}{\partial V_D} = g_{ds} + g_{gd}, \quad \frac{\partial F_D}{\partial V_S} = -g_{ds}
\]
\[
\frac{\partial F_G}{\partial V_G} = g_{gs} + g_{gd}, \quad \frac{\partial F_G}{\partial V_D} = -g_{gd}, \quad \frac{\partial F_G}{\partial V_S} = -g_{gs}
\]
\[
\frac{\partial F_S}{\partial V_G} = g_m - g_{gs}, \quad \frac{\partial F_S}{\partial V_D} = -g_{ds}, \quad \frac{\partial F_S}{\partial V_S} = g_{ds} + g_{gs}
\]

For transient analysis, the capacitive terms add contributions scaled by the integration method coefficient (e.g., \( \frac{\partial Q}{\partial V} \cdot \frac{1}{h} \) for Backward Euler).

### 2.3 Convergence Criteria and Challenges

The iteration is deemed converged when both **absolute** and **relative** error criteria are satisfied for all variables.

**Voltage Convergence:** For each node voltage \(V_i\),
\[
| \Delta V_i^{(k)} | \leq \text{VNTOL} + \text{RELTOL} \cdot \max(|V_i^{(k)}|, |V_i^{(k-1)}|)
\]
Typical values: \(\text{VNTOL} = 1\,\mu\text{V}\), \(\text{RELTOL} = 0.001\).

**Current Convergence:** For each branch current from the JFET (e.g., \(I_D\)),
\[
| F_i^{(k)} | \leq \text{ABSTOL} + \text{RELTOL} \cdot \max(|I^{(k)}|, |I^{(k-1)}|)
\]
Typical value: \(\text{ABSTOL} = 1\,\text{pA}\).

**JFET-Specific Challenges:**
1.  **Sharp Pinch-Off:** The discontinuity in derivative at \(V_{GS} = V_{TO}\) can cause convergence oscillation. Ngspice employs **limiting functions** (e.g., `pnjlim` for junction voltages, `fetlim` for \(V_{GS}-V_{TO}\)) to smooth the transition and guide the Newton iteration.
2.  **Exponential Diodes:** The gate diodes \(I_{GS}\), \(I_{GD}\) have exponential I-V characteristics. Convergence is ensured by using the diode's exact derivative in the Jacobian and proper initial guess.
3.  **Parasitic Resistances:** The series resistances \(R_D\), \(R_S\) help condition the Jacobian by preventing the intrinsic drain-source voltage from becoming indeterminate.
4.  **Charge Conservation:** The nonlinear capacitance model uses the **Charge-Free** formulation, where the Jacobian stamps \(\partial I/\partial V = \partial^2 Q/\partial V^2 \cdot (dV/dt) + \partial Q/\partial V \cdot (1/h)\). This ensures charge conservation and improves transient convergence.

### 2.4 Local Truncation Error (LTE) Control for Transient Analysis

The Parker-Sellern model's capacitances necessitate tight control of the integration time-step. The LTE for a capacitive branch is estimated using the second derivative of charge:
\[
\text{LTE}_Q = \frac{h^2}{12} \left| \frac{d^2 Q}{dt^2} \right|
\]
For the gate-source capacitance, this becomes:
\[
\frac{d^2 Q_{GS}}{dt^2} = \frac{d}{dt}\left( C_{GS}(V_{GS}) \frac{dV_{GS}}{dt} \right) = \frac{dC_{GS}}{dV_{GS}} \left( \frac{dV_{GS}}{dt} \right)^2 + C_{GS}(V_{GS}) \frac{d^2 V_{GS}}{dt^2}
\]
The time-step \(h\) is adjusted to keep \(\text{LTE}_Q \leq \text{CHGTOL} + \text{RELTOL} \cdot |Q_{GS}|\). Typical \(\text{CHGTOL} = 10^{-14}\).

### 2.5 Algorithmic Convergence Aids

To handle difficult biasing (e.g., startup with all voltages at 0), Ngspice employs:
- **Gmin Stepping:** A small conductance (\(G_{min} \approx 10^{-12}\, \text{S}\)) is added across all PN junctions and gradually reduced.
- **Source Stepping:** Independent voltage sources are ramped from 0 to their final value.
- **Pseudo-Transient:** A fictitious capacitance is added to critical nodes to damp oscillations.

For the JFET, these methods are particularly useful when the gate junction is strongly forward-biased, causing large initial current mismatches.

The mathematical formulation of the JFET model, combining classic square-law equations with the comprehensive Parker-Skellern parasitic network, provides a robust framework for DC, AC, and transient simulation. Its convergence properties are managed within Ngspice's unified Newton-Raphson framework, utilizing device-specific limiting and the charge-conserving capacitance model to ensure numerical stability and accuracy across a wide range of operating conditions.

## 3. C Implementation

### 3.1 Data Structures

The JFET implementation in Ngspice follows the standard SPICE device architecture with model and instance structures.

**Model Structure (`sJFETmodel`):**
```c
typedef struct sJFETmodel {
    int JFETmodType;              /* Device type: NJF or PJF */
    double JFETthreshold;         /* VTO: Threshold voltage */
    double JFETbeta;              /* BETA: Transconductance parameter */
    double JFETlambda;            /* LAMBDA: Channel-length modulation */
    double JFETdrainResist;       /* RD: Drain resistance */
    double JFETsourceResist;      /* RS: Source resistance */
    double JFETgateSourceCap;     /* CGS: Gate-source capacitance */
    double JFETgateDrainCap;      /* CGD: Gate-drain capacitance */
    double JFETgatePotential;     /* PB: Gate junction potential */
    double JFETgateSatCurrent;    /* IS: Gate saturation current */
    double JFETdepletionCapCoeff; /* M: Grading coefficient */
    double JFETfNcoef;            /* FC: Forward bias coefficient */
    double JFETfNexp;             /* FNE: Flicker noise exponent */
    double JFETtNominal;          /* TNOM: Nominal temperature */
    
    /* Parker-Skellern parameters */
    double JFETpsM;               /* PS_M: Parker-Skellern exponent */
    double JFETpsLambda;          /* PS_LAMBDA: PS channel-length modulation */
    
    struct sJFETmodel *JFETnextModel;  /* Pointer to next model */
    JFETinstance *JFETinstances;       /* Pointer to instances */
} JFETmodel;
```

**Instance Structure (`sJFETinstance`):**
```c
typedef struct sJFETinstance {
    char *JFETname;               /* Instance name */
    
    /* Terminal connections */
    int JFETdrainNode;            /* Drain node number */
    int JFETgateNode;             /* Gate node number */
    int JFETsourceNode;           /* Source node number */
    int JFETdrainPrimeNode;       /* Internal drain node */
    int JFETsourcePrimeNode;      /* Internal source node */
    
    /* Model parameters */
    double JFETl;                 /* L: Channel length */
    double JFETw;                 /* W: Channel width */
    double JFETarea;              /* AREA: Area multiplier */
    double JFETicVDS;             /* IC: Initial VDS condition */
    double JFETicVGS;             /* IC: Initial VGS condition */
    double JFETtemp;              /* TEMP: Instance temperature */
    double JFETdTemp;             /* DTEMP: Temperature difference */
    
    /* State variables */
    double JFETvgs;               /* Vgs: Gate-source voltage */
    double JFETvds;               /* Vds: Drain-source voltage */
    double JFETcd;                /* Id: Drain current */
    double JFETcgs;               /* Igs: Gate-source current */
    double JFETcgd;               /* Igd: Gate-drain current */
    
    /* Small-signal parameters */
    double JFETgm;                /* gm: Transconductance */
    double JFETgds;               /* gds: Drain conductance */
    double JFETggs;               /* ggs: Gate-source conductance */
    double JFETggd;               /* ggd: Gate-drain conductance */
    
    /* Charge storage */
    double JFETqgs;               /* Qgs: Gate-source charge */
    double JFETqgd;               /* Qgd: Gate-drain charge */
    double JFETcgsb;              /* Cgs: Gate-source capacitance */
    double JFETcgdb;              /* Cgd: Gate-drain capacitance */
    
    /* Matrix pointers */
    double *JFETdrainPtr;         /* Pointer to drain node in RHS */
    double *JFETgatePtr;          /* Pointer to gate node in RHS */
    double *JFETsourcePtr;        /* Pointer to source node in RHS */
    double *JFETdrainPrimePtr;    /* Pointer to internal drain node */
    double *JFETsourcePrimePtr;   /* Pointer to internal source node */
    
    /* Sparse matrix elements */
    double *JFETdrainDrainPtr;    /* G[drain][drain] */
    double *JFETdrainGatePtr;     /* G[drain][gate] */
    double *JFETdrainSourcePtr;   /* G[drain][source] */
    double *JFETdrainDrainPrimePtr; /* G[drain][drainPrime] */
    double *JFETdrainSourcePrimePtr; /* G[drain][sourcePrime] */
    
    struct sJFETinstance *JFETnextInstance; /* Next instance */
    JFETmodel *JFETmodPtr;        /* Pointer to model */
} JFETinstance;
```

### 3.2 SPICEdev API Binding

The JFET device is registered with Ngspice through the standard `SPICEdev` structure:

```c
SPICEdev JFETinfo = {
    .DEVpublic = {
        .name = "JFET",
        .description = "Junction Field-Effect Transistor",
        .terms = 3,  /* Drain, Gate, Source */
        .numNames = 2,
        .termNames = (char *[]){"drain", "gate", "source"},
        .numInstanceParms = 12,
        .instanceParms = (IFparm[]){
            IOP("l", JFET_L, IF_REAL, "Length"),
            IOP("w", JFET_W, IF_REAL, "Width"),
            IOP("area", JFET_AREA, IF_REAL, "Area multiplier"),
            IOP("ic", JFET_IC, IF_REAL, "Initial condition vector"),
            IOP("temp", JFET_TEMP, IF_REAL, "Instance temperature"),
            IOP("dtemp", JFET_DTEMP, IF_REAL, "Temperature difference"),
            IP("off", JFET_OFF, IF_FLAG, "Device initially off"),
            IP("m", JFET_M, IF_REAL, "Parallel multiplier"),
            IP("n", JFET_N, IF_INTEGER, "Number of devices in parallel"),
            IP("sens_area", JFET_SENS_AREA, IF_FLAG, "Flag to request sensitivity wrt area"),
            IP("icvds", JFET_IC_VDS, IF_REAL, "Initial VDS"),
            IP("icvgs", JFET_IC_VGS, IF_REAL, "Initial VGS"),
        },
        .numModelParms = 20,
        .modelParms = (IFparm[]){
            IOP("vto", JFET_VTO, IF_REAL, "Threshold voltage"),
            IOP("beta", JFET_BETA, IF_REAL, "Transconductance parameter"),
            IOP("lambda", JFET_LAMBDA, IF_REAL, "Channel-length modulation"),
            IOP("rd", JFET_RD, IF_REAL, "Drain resistance"),
            IOP("rs", JFET_RS, IF_REAL, "Source resistance"),
            IOP("cgs", JFET_CGS, IF_REAL, "Zero-bias G-S capacitance"),
            IOP("cgd", JFET_CGD, IF_REAL, "Zero-bias G-D capacitance"),
            IOP("pb", JFET_PB, IF_REAL, "Gate junction potential"),
            IOP("is", JFET_IS, IF_REAL, "Gate saturation current"),
            IOP("m", JFET_M, IF_REAL, "Grading coefficient"),
            IOP("fc", JFET_FC, IF_REAL, "Forward bias coefficient"),
            IOP("kf", JFET_KF, IF_REAL, "Flicker noise coefficient"),
            IOP("af", JFET_AF, IF_REAL, "Flicker noise exponent"),
            IOP("fne", JFET_FNE, IF_REAL, "Flicker noise frequency exponent"),
            IOP("tnom", JFET_TNOM, IF_REAL, "Nominal temperature"),
            
            /* Parker-Skellern parameters */
            IOP("psm", JFET_PS_M, IF_REAL, "Parker-Skellern exponent"),
            IOP("pslambda", JFET_PS_LAMBDA, IF_REAL, "PS channel-length modulation"),
            
            /* Device type */
            IP("njf", JFET_NJF, IF_FLAG, "N-channel JFET"),
            IP("pjf", JFET_PJF, IF_FLAG, "P-channel JFET"),
        },
    },
    
    /* Function pointers */
    .DEVparam = JFETparam,
    .DEVmodParam = JFETmParam,
    .DEVload = JFETload,
    .DEVsetup = JFETsetup,
    .DEVunsetup = JFETunsetup,
    .DEVpzSetup = JFETpzSetup,
    .DEVtemperature = JFETtemp,
    .DEVtrunc = JFETtrunc,
    .DEVfindBranch = JFETfindBranch,
    .DEVacLoad = JFETacLoad,
    .DEVaccept = JFETaccept,
    .DEVdestroy = JFETdestroy,
    .DEVmodDelete = JFETmDelete,
    .DEVdelete = JFETdelete,
    .DEVsetic = JFETgetic,
    .DEVask = JFETask,
    .DEVmodAsk = JFETmAsk,
    .DEVpzLoad = JFETpzLoad,
    .DEVconvTest = JFETconvTest,
    .DEVsenSetup = JFETsSetup,
    .DEVsenLoad = JFETsLoad,
    .DEVsenUpdate = JFETsUpdate,
    .DEVsenAcLoad = JFETsAcLoad,
    .DEVsenPrint = JFETsPrint,
    .DEVsenDisto = JFETsDisto,
    .DEVsenTraSetup = JFETsTsetup,
    .DEVsenTraLoad = JFETsTload,
};
```

### 3.3 Core Algorithm Implementation

**DC/Transient Load Function (`JFETload`):**
```c
int JFETload(GENmodel *inModel, CKTcircuit *ckt)
{
    JFETmodel *model = (JFETmodel*)inModel;
    JFETinstance *here;
    
    for (; model != NULL; model = model->JFETnextModel) {
        for (here = model->JFETinstances; here != NULL; here = here->JFETnextInstance) {
            
            /* Get voltages */
            double vgs = *(ckt->CKTrhsOld + here->JFETgateNode) 
                       - *(ckt->CKTrhsOld + here->JFETsourcePrimeNode);
            double vds = *(ckt->CKTrhsOld + here->JFETdrainPrimeNode) 
                       - *(ckt->CKTrhsOld + here->JFETsourcePrimeNode);
            
            /* Apply voltage limiting */
            vgs = DEVfetlim(vgs, here->JFETvgs, model->JFETthreshold);
            vds = DEVfetlim(vds, here->JFETvds, 0.0);
            
            /* Store state */
            here->JFETvgs = vgs;
            here->JFETvds = vds;
            
            /* Calculate effective voltage */
            double vto = model->JFETthreshold;
            double veff = vgs - vto;
            
            /* Region detection with smoothing */
            double vds_sat;
            if (veff <= 0.0) {
                /* Cutoff region */
                here->JFETcd = 0.0;
                here->JFETgm = 0.0;
                here->JFETgds = 0.0;
            } else {
                /* Smooth saturation voltage calculation */
                double delta = 1e-6;
                vds_sat = 0.5 * (vds + veff + sqrt((vds - veff)*(vds - veff) + delta*delta)
                                 - sqrt(veff*veff + delta*delta));
                
                /* Calculate drain current */
                double beta = model->JFETbeta;
                double lambda = model->JFETlambda;
                
                if (vds <= vds_sat) {
                    /* Linear region - classic square law */
                    here->JFETcd = beta * (2.0 * veff * vds - vds * vds) 
                                 * (1.0 + lambda * vds);
                    here->JFETgm = 2.0 * beta * vds * (1.0 + lambda * vds);
                    here->JFETgds = beta * (2.0 * veff - 2.0 * vds) * (1.0 + lambda * vds)
                                  + lambda * beta * (2.0 * veff * vds - vds * vds);
                } else {
                    /* Saturation region - Parker-Skellern model */
                    double ps_m = model->JFETpsM;
                    double ps_lambda = model->JFETpsLambda;
                    
                    if (ps_m > 0.0) {
                        /* Use Parker-Skellern exponent */
                        here->JFETcd = beta * pow(veff, ps_m) 
                                     * (1.0 + ps_lambda * vds);
                        here->JFETgm = beta * ps_m * pow(veff, ps_m - 1.0) 
                                     * (1.0 + ps_lambda * vds);
                        here->JFETgds = ps_lambda * beta * pow(veff, ps_m);
                    } else {
                        /* Classic square law fallback */
                        here->JFETcd = beta * veff * veff * (1.0 + lambda * vds);
                        here->JFETgm = 2.0 * beta * veff * (1.0 + lambda * vds);
                        here->JFETgds = lambda * beta * veff * veff;
                    }
                }
            }
            
            /* Add series resistances */
            double rd = model->JFETdrainResist;
            double rs = model->JFETsourceResist;
            
            if (rd > 0.0) {
                here->JFETgds = 1.0 / (1.0 / here->JFETgds + rd);
            }
            if (rs > 0.0) {
                here->JFETgm = here->JFETgm / (1.0 + here->JFETgm * rs);
                here->JFETgds = here->JFETgds / (1.0 + here->JFETgds * rs);
            }
            
            /* Matrix stamping */
            double *rhs = ckt->CKTrhs;
            double *matrix = ckt->CKTmatrix->SMPmatrix;
            
            /* Stamp internal nodes (drainPrime, sourcePrime) */
            *(here->JFETdrainPrimeDrainPrimePtr) += here->JFETgds;
            *(here->JFETsourcePrimeSourcePrimePtr) += here->JFETgds + here->JFETgm;
            *(here->JFETdrainPrimeSourcePrimePtr) -= here->JFETgds;
            *(here->JFETsourcePrimeDrainPrimePtr) -= here->JFETgds + here->JFETgm;
            
            /* Stamp gate node */
            *(here->JFETsourcePrimeGatePtr) += here->JFETgm;
            *(here->JFETgateSourcePrimePtr) -= here->JFETgm;
            
            /* Right-hand side stamp */
            rhs[here->JFETdrainPrimeNode] -= here->JFETcd;
            rhs[here->JFETsourcePrimeNode] += here->JFETcd;
            
            /* Add series resistance stamps if present */
            if (rd > 0.0) {
                *(here->JFETdrainDrainPtr) += 1.0 / rd;
                *(here->JFETdrainPrimeDrainPrimePtr) += 1.0 / rd;
                *(here->JFETdrainDrainPrimePtr) -= 1.0 / rd;
                *(here->JFETdrainPrimeDrainPtr) -= 1.0 / rd;
            }
            
            if (rs > 0.0) {
                *(here->JFETsourceSourcePtr) += 1.0 / rs;
                *(here->JFETsourcePrimeSourcePrimePtr) += 1.0 / rs;
                *(here->JFETsourceSourcePrimePtr) -= 1.0 / rs;
                *(here->JFETsourcePrimeSourcePtr) -= 1.0 / rs;
            }
        }
    }
    
    return OK;
}
```

**AC Load Function (`JFETacLoad`):**
```c
int JFETacLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    JFETmodel *model = (JFETmodel*)inModel;
    JFETinstance *here;
    double omega = ckt->CKTomega;
    
    for (; model != NULL; model = model->JFETnextModel) {
        for (here = model->JFETinstances; here != NULL; here = here->JFETnextInstance) {
            
            /* Calculate junction capacitances */
            double vgs = here->JFETvgs;
            double vgd = vgs - here->JFETvds;
            
            double cgs, cgd;
            double pb = model->JFETgatePotential;
            double fc = model->JFETfNcoef;
            double m = model->JFETdepletionCapCoeff;
            
            /* Gate-source capacitance */
            if (vgs < fc * pb) {
                /* Reverse bias */
                cgs = model->JFETgateSourceCap / pow(1.0 - vgs/pb, m);
            } else {
                /* Forward bias - linear extrapolation */
                double f1 = pow(1.0 - fc, -m);
                double f2 = (1.0 - fc*(1.0 + m) + m*vgs/pb);
                cgs = model->JFETgateSourceCap * f1 * f2;
            }
            
            /* Gate-drain capacitance */
            if (vgd < fc * pb) {
                cgd = model->JFETgateDrainCap / pow(1.0 - vgd/pb, m);
            } else {
                double f1 = pow(1.0 - fc, -m);
                double f2 = (1.0 - fc*(1.0 + m) + m*vgd/pb);
                cgd = model->JFETgateDrainCap * f1 * f2;
            }
            
            /* Store for noise calculation */
            here->JFETcgsb = cgs;
            here->JFETcgdb = cgd;
            
            /* Complex admittance matrix stamp */
            double g_complex = here->JFETgds;
            double b_complex = omega * (cgs + cgd);
            
            /* Stamp Y-matrix for AC analysis */
            double *matrix = ckt->CKTmatrix->SMPmatrix;
            
            /* Real part (conductance) */
            *(here->JFETdrainPrimeDrainPrimePtr) += g_complex;
            *(here->JFETsourcePrimeSourcePrimePtr) += g_complex + here->JFETgm;
            *(here->JFETdrainPrimeSourcePrimePtr) -= g_complex;
            *(here->JFETsourcePrimeDrainPrimePtr) -= g_complex + here->JFETgm;
            
            /* Imaginary part (capacitance) */
            int offset = ckt->CKTmatrix->SMPsize;
            *(here->JFETdrainPrimeDrainPrimePtr + offset) += b_complex;
            *(here->JFETsourcePrimeSourcePrimePtr + offset) += b_complex;
            *(here->JFETdrainPrimeSourcePrimePtr + offset) -= b_complex;
            *(here->JFETsourcePrimeDrain