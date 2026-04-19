# CIDER Numerical Models: Poisson and Continuity Equation MNA Load

_Generated 2026-04-13 03:04 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtdump.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2load.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2dump.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numddump.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2load.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2dump.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummdump.c`

# **VBIC BJT: Matrix Topology, API, and Safe Operating Area**

## **1. Technical Introduction**

This chapter details the implementation of the Vertical Bipolar Inter-Company (VBIC) bipolar junction transistor model within the Ngspice circuit simulator. The VBIC model represents a significant advancement over traditional SPICE Gummel-Poon models, incorporating quasi-saturation effects, self-heating, avalanche multiplication, substrate current, and comprehensive safe operating area (SOA) checking. The implementation spans several critical C source files that collectively define the model's data structures, mathematical formulation, matrix integration, and operational safety mechanisms.

The core implementation files include:
- **`vbicdefs.h`**: Defines the fundamental data structures `sVBICmodel` and `sVBICinstance` that encapsulate model parameters, instance-specific variables, and internal state.
- **`vbicsetup.c`**: Implements the `VBICsetup()` function responsible for parameter validation, memory allocation, and establishing sparse matrix pointer (SMP) connections for the Modified Nodal Analysis (MNA) matrix.
- **`vbicload.c`**: Contains the `VBICload()` function that stamps the device's conductance matrix and current vector contributions into the global MNA system during Newton-Raphson iterations.
- **`vbicsoachk.c`**: Implements `VBICsoachk()` for comprehensive safe operating area verification, checking voltage, current, and power limits against user-defined constraints.
- **`vbictemp.c`**: Handles `VBICtemp()` for temperature-dependent parameter scaling and self-heating calculations.
- **`vbictrunc.c`**: Provides `VBICtrunc()` for local truncation error (LTE) estimation and adaptive time-step control.

The VBIC model integrates with Ngspice through the standardized `SPICEdev` API, binding device-specific functions to the simulator's numerical engine. This chapter examines the mathematical foundations of the VBIC equations, their numerical implementation, convergence characteristics, and the precise C code mappings that enable robust circuit simulation.

## **2. Mathematical Formulation**

### **2.1 Intrinsic DC Model**

The VBIC DC model extends the Gummel-Poon formulation with additional physical effects. The forward and reverse transport currents are given by:

\[
I_{cf} = \frac{I_{sf}}{Q_b} \left[ \exp\left(\frac{V_{be,eff}}{N_f V_T}\right) - \exp\left(\frac{V_{bc,eff}}{N_f V_T}\right) \right]
\]

\[
I_{cr} = \frac{I_{sr}}{Q_b} \left[ \exp\left(\frac{V_{be,eff}}{N_r V_T}\right) - \exp\left(\frac{V_{bc,eff}}{N_r V_T}\right) \right]
\]

where \(Q_b\) is the normalized base charge:

\[
Q_b = \frac{1}{2} \left[ 1 + \frac{V_{be,eff}}{V_{ar}} + \frac{V_{bc,eff}}{V_{af}} \right] + \sqrt{ \frac{1}{4} \left[ 1 + \frac{V_{be,eff}}{V_{ar}} + \frac{V_{bc,eff}}{V_{af}} \right]^2 + \frac{I_{sf}}{I_{kf}} \exp\left(\frac{V_{be,eff}}{N_f V_T}\right) + \frac{I_{sr}}{I_{kr}} \exp\left(\frac{V_{bc,eff}}{N_r V_T}\right) }
\]

The base-emitter and base-collector currents include ideal and non-ideal components:

\[
I_{bf} = I_{sef} \left[ \exp\left(\frac{V_{be,eff}}{N_e V_T}\right) - 1 \right] + \frac{I_{sf}}{\beta_f Q_b} \left[ \exp\left(\frac{V_{be,eff}}{N_f V_T}\right) - 1 \right]
\]

\[
I_{br} = I_{ser} \left[ \exp\left(\frac{V_{bc,eff}}{N_c V_T}\right) - 1 \right] + \frac{I_{sr}}{\beta_r Q_b} \left[ \exp\left(\frac{V_{bc,eff}}{N_r V_T}\right) - 1 \right]
\]

### **2.2 Quasi-Saturation and Series Resistances**

VBIC models quasi-saturation through voltage-dependent collector resistance:

\[
R_{bc} = R_{CO} \cdot \left[ 1 + \left( \frac{I_c}{I_{k}} \right)^\gamma \right]^\gamma
\]

The effective internal voltages account for series resistances:

\[
V_{be,eff} = V_{be} - I_b \cdot R_{bx} - I_{bf} \cdot R_{e} - I_{c} \cdot R_{cx}
\]

\[
V_{bc,eff} = V_{bc} - I_b \cdot R_{bx} - I_{br} \cdot R_{c} - I_{c} \cdot R_{cx}
\]

### **2.3 Avalanche and Substrate Currents**

Avalanche multiplication current:

\[
I_{avl} = I_{c} \cdot \left[ \exp\left( -A_{vc} \cdot (V_{cb} - V_{cb0}) \right) - 1 \right] \quad \text{for } V_{cb} > V_{cb0}
\]

Substrate current modeled as a parasitic PNP:

\[
I_{sub} = I_{ss} \left[ \exp\left(\frac{V_{sc}}{N_s V_T}\right) - 1 \right]
\]

### **2.4 Charge Storage and Capacitances**

Depletion charges for BE and BC junctions:

\[
Q_{be} = C_{je0} \cdot V_{je} \cdot \left( 1 - \left(1 - \frac{V_{be}}{V_{je}}\right)^{1 - M_{je}} \right) / (1 - M_{je})
\]

\[
Q_{bc} = C_{jc0} \cdot V_{jc} \cdot \left( 1 - \left(1 - \frac{V_{bc}}{V_{jc}}\right)^{1 - M_{jc}} \right) / (1 - M_{jc})
\]

Diffusion charges:

\[
Q_{diff} = \tau_f \cdot I_{cf} + \tau_r \cdot I_{cr}
\]

### **2.5 Self-Heating Thermal Network**

Power dissipation:

\[
P_{diss} = V_{ce} \cdot I_c + V_{be} \cdot I_b
\]

Junction temperature with thermal impedance:

\[
T_j = T_{amb} + R_{th} \cdot P_{diss} + \tau_{th} \cdot \frac{dP_{diss}}{dt}
\]

Temperature scaling of saturation currents:

\[
I_s(T) = I_s(T_{nom}) \cdot \left( \frac{T}{T_{nom}} \right)^{X_{TI}} \cdot \exp\left[ \frac{E_g}{q \cdot V_T} \cdot \left( \frac{T}{T_{nom}} - 1 \right) \right]
\]

## **3. Convergence Analysis**

### **3.1 Newton-Raphson Formulation**

The VBIC model implements the standard Newton-Raphson iteration for solving the nonlinear device equations. The residual vector \(F(V)\) for the four-terminal device (B, E, C, S) is:

\[
F(V) = \begin{bmatrix}
I_b(V_{be}, V_{bc}, V_{cs}) \\
I_e(V_{be}, V_{bc}, V_{cs}) \\
I_c(V_{be}, V_{bc}, V_{cs}) \\
I_s(V_{be}, V_{bc}, V_{cs})
\end{bmatrix} + \frac{dQ(V)}{dt} - I_{ext} = 0
\]

The Jacobian matrix \(J = \partial F/\partial V\) includes both conductive and capacitive components:

\[
J = \begin{bmatrix}
g_{bb} & g_{be} & g_{bc} & g_{bs} \\
g_{eb} & g_{ee} & g_{ec} & g_{es} \\
g_{cb} & g_{ce} & g_{cc} & g_{cs} \\
g_{sb} & g_{se} & g_{sc} & g_{ss}
\end{bmatrix} + \frac{\partial}{\partial V}\left(\frac{dQ}{dt}\right)
\]

where \(g_{ij} = \partial I_i/\partial V_j\) are the small-signal conductances.

### **3.2 Matrix Stamping Pattern**

The VBIC device stamps a 4×4 block into the MNA matrix corresponding to nodes B, E, C, and S (substrate). For the conductive part:

\[
\begin{bmatrix}
+g_{bb} & -g_{be} & -g_{bc} & -g_{bs} \\
-g_{eb} & +g_{ee} & -g_{ec} & -g_{es} \\
-g_{cb} & -g_{ce} & +g_{cc} & -g_{cs} \\
-g_{sb} & -g_{se} & -g_{sc} & +g_{ss}
\end{bmatrix}
\begin{bmatrix}
V_b \\
V_e \\
V_c \\
V_s
\end{bmatrix}
=
\begin{bmatrix}
-I_b^0 \\
-I_e^0 \\
-I_c^0 \\
-I_s^0
\end{bmatrix}
\]

The capacitive contributions use companion models for the integration method (trapezoidal or Gear):

\[
C_{eq} = \frac{2C}{\Delta t} \quad \text{(trapezoidal)}
\]
\[
I_{eq} = C_{eq} \cdot V^{old} + I_{cap}^{old}
\]

### **3.3 Convergence Challenges and Solutions**

**Exponential Nonlinearities**: The BJT exponential \(I-V\) relationships create sharp discontinuities near cutoff. VBIC employs limiting functions similar to `pnjlim()` to bound junction voltage changes between iterations:

\[
\Delta V_{be}^{limited} = \text{limit}(\Delta V_{be}, -5V_T, V_{be}^{max})
\]

**Quasi-Saturation Discontinuity**: The \(R_{bc}(I_c)\) function has a discontinuous derivative at \(I_c = I_k\). Implementation uses a smoothing function:

\[
R_{bc}^{smooth} = R_{CO} \cdot \left[ 1 + \left( \frac{I_c}{I_{k} + \delta} \right)^{\gamma + \delta} \right]^{\gamma}
\]

where \(\delta \approx 10^{-6}\) provides continuous derivatives.

**Thermal Feedback Instability**: The self-heating loop \(P_{diss} \rightarrow T_j \rightarrow I_s(T_j) \rightarrow P_{diss}\) can cause oscillation. The implementation uses under-relaxation:

\[
T_j^{new} = T_j^{old} + \alpha (T_j^{calc} - T_j^{old}), \quad \alpha = 0.3
\]

**Charge Conservation**: The nonlinear depletion capacitances must satisfy:

\[
\frac{\partial Q}{\partial t} = C(V) \frac{\partial V}{\partial t}
\]

VBIC uses the chord method for charge conservation, ensuring \(Q(V)\) is single-valued.

### **3.4 Local Truncation Error (LTE) Control**

The `VBICtrunc()` function estimates LTE for state variables \(V_{be}\), \(V_{bc}\), \(V_{cs}\), and \(Q_{be}\), \(Q_{bc}\), \(Q_{diff}\). For a state variable \(s\):

\[
LTE_s = \frac{|s_{TR} - s_{BE}|}{reltol \cdot |s_{TR}| + abstol}
\]

where \(s_{TR}\) is the trapezoidal rule prediction and \(s_{BE}\) is the backward Euler prediction. The overall device LTE:

\[
LTE_{VBIC} = \max(LTE_{V_{be}}, LTE_{V_{bc}}, LTE_{V_{cs}}, LTE_{Q_{be}}, LTE_{Q_{bc}}, LTE_{Q_{diff}})
\]

Time step is reduced if \(LTE_{VBIC} > 1\) and increased if \(LTE_{VBIC} < 0.1\).

### **3.5 Convergence Criteria**

Newton-Raphson convergence is checked using:

\[
|V^{k+1} - V^k| < \epsilon_{abs} + \epsilon_{rel} \cdot |V^{k+1}|
\]

with \(\epsilon_{abs} = 10^{-6}\) V (VNTOL) and \(\epsilon_{rel} = 10^{-3}\) (RELTOL). Current residuals must satisfy:

\[
|F_i(V)| < 10^{-12} \text{ A} + 10^{-3} \cdot |I_i^{branch}|
\]

## **4. C Implementation**

### **4.1 Core Data Structures**

**From `vbicdefs.h`**:

```c
typedef struct sVBICmodel {
    int VBICmodType;              /* Device type */
    struct sVBICmodel *VBICnextModel; /* Linked list */
    VBICinstance *VBICinstances;  /* Instance list */
    
    /* Model parameters */
    double VBICtype;              /* NPN/PNP */
    double VBICnf;                /* Forward emission coefficient */
    double VBICnr;                /* Reverse emission coefficient */
    double VBICis;                /* Transport saturation current */
    double VBICikf;               /* Forward knee current */
    double VBICikr;               /* Reverse knee current */
    double VBICvaf;               /* Forward Early voltage */
    double VBICvar;               /* Reverse Early voltage */
    double VBICbf;                /* Ideal forward beta */
    double VBICbr;                /* Ideal reverse beta */
    double VBICise;               /* BE leakage saturation current */
    double VBICne;                /* BE leakage emission coefficient */
    double VBICisc;               /* BC leakage saturation current */
    double VBICnc;                /* BC leakage emission coefficient */
    double VBICrb;                /* Zero-bias base resistance */
    double VBICrbi;               /* Intrinsic base resistance */
    double VBICre;                /* Emitter resistance */
    double VBICrc;                /* Collector resistance */
    double VBICcje;               /* Zero-bias BE depletion capacitance */
    double VBICvje;               /* BE built-in potential */
    double VBICmje;               /* BE grading coefficient */
    double VBICcjc;               /* Zero-bias BC depletion capacitance */
    double VBICvjc;               /* BC built-in potential */
    double VBICmjc;               /* BC grading coefficient */
    double VBICxti;               /* Saturation current temp exponent */
    double VBICeg;                /* Energy gap */
    double VBICtnom;              /* Nominal temperature */
    double VBICavc;               /* Avalanche coefficient */
    double VBICvcbo;              /* Avalanche breakdown voltage */
    double VBICrth;               /* Thermal resistance */
    double VBICcth;               /* Thermal capacitance */
    
    /* Flags and state */
    unsigned VBICtnomGiven : 1;
    unsigned VBICrthGiven  : 1;
    unsigned VBICcthGiven  : 1;
} VBICmodel;

typedef struct sVBICinstance {
    struct sVBICinstance *VBICnextInstance; /* Linked list */
    VBICmodel *VBICmodPtr;        /* Parent model */
    
    /* Node connections */
    int VBICbaseNode;             /* Base node */
    int VBICemitNode;             /* Emitter node */
    int VBICcollNode;             /* Collector node */
    int VBICsubsNode;             /* Substrate node */
    int VBICtempNode;             /* Thermal node */
    
    /* Instance parameters */
    double VBICarea;              /* Area scaling factor */
    double VBICm;                 /* Parallel multiplier */
    
    /* Internal state variables */
    double VBICvbe;               /* Base-emitter voltage */
    double VBICvbc;               /* Base-collector voltage */
    double VBICvcs;               /* Collector-substrate voltage */
    double VBICib;                /* Base current */
    double VBICic;                /* Collector current */
    double VBICisub;              /* Substrate current */
    double VBICqbe;               /* BE junction charge */
    double VBICqbc;               /* BC junction charge */
    double VBICqdiff;             /* Diffusion charge */
    double VBICpdiss;             /* Power dissipation */
    double VBICtj;                /* Junction temperature */
    
    /* Small-signal parameters */
    double VBICgbb, VBICgbe, VBICgbc, VBICgbs;
    double VBICgeb, VBICgee, VBICgec, VBICges;
    double VBICgcb, VBICgce, VBICgcc, VBICgcs;
    double VBICgsb, VBICgse, VBICgsc, VBICgss;
    
    /* Matrix pointers */
    double *VBICbaseBasePtr;      /* Gbb */
    double *VBICbaseEmitPtr;      /* Gbe */
    double *VBICbaseCollPtr;      /* Gbc */
    double *VBICbaseSubsPtr;      /* Gbs */
    double *VBICemitBasePtr;      /* Geb */
    double *VBICemitEmitPtr;      /* Gee */
    double *VBICemitCollPtr;      /* Gec */
    double *VBICemitSubsPtr;      /* Ges */
    double *VBICcollBasePtr;      /* Gcb */
    double *VBICcollEmitPtr;      /* Gce */
    double *VBICcollCollPtr;      /* Gcc */
    double *VBICcollSubsPtr;      /* Gcs */
    double *VBICsubsBasePtr;      /* Gsb */
    double *VBICsubsEmitPtr;      /* Gse */
    double *VBICsubsCollPtr;      /* Gsc */
    double *VBICsubsSubsPtr;      /* Gss */
    
    /* RHS vector pointers */
    double *VBICbaseRhsPtr;
    double *VBICemitRhsPtr;
    double *VBICcollRhsPtr;
    double *VBICsubsRhsPtr;
    
    /* State vector indices */
    int VBICvbeState;
    int VBICvbcState;
    int VBICvcsState;
    int VBICqbeState;
    int VBICqbcState;
    int VBICqdiffState;
    int VBICtjState;
    
    /* Flags */
    unsigned VBICoff     : 1;     /* Device off */
    unsigned VBICtempGiven : 1;   /* Temperature specified */
    unsigned VBICareaGiven : 1;   /* Area specified */
    unsigned VBICicGiven  : 1;    /* Initial condition */
    unsigned VBICsoaFlag  : 1;    /* SOA violation */
} VBICinstance;
```

### **4.2 SPICEdev API Binding**

**From `vbicinit.c`**:

```c
SPICEdev VBICinfo = {
    .DEVpublic = {
        .name = "VBIC",
        .description = "Vertical Bipolar Inter-Company Model",
        .terms = 4,  /* B, E, C, S */
        .numNames = 4,
        .termNames = (char *[]){"b", "e", "c", "s"},
        .numInstanceParms = 12,
        .instanceParms = (IFparm[]){
            IOP("area",  VBIC_AREA,    IF_REAL, "Area factor"),
            IOP("m",     VBIC_M,       IF_REAL, "Parallel multiplier"),
            IOP("ic",    VBIC_IC,      IF_REAL, "Initial condition"),
            IOP("temp",  VBIC_TEMP,    IF_REAL, "Instance temperature"),
            IOP("off",   VBIC_OFF,     IF_FLAG, "Device initially off"),
            IOPU("soa",  VBIC_SOA,     IF_FLAG, "SOA check enabled"),
        },
        .numModelParms = 45,
        .modelParms = (IFparm[]){
            IOP("type",  VBIC_TYPE,    IF_REAL, "NPN or PNP type"),
            IOP("nf",    VBIC_NF,      IF_REAL, "Forward emission coefficient"),
            IOP("nr",    VBIC_NR,      IF_REAL, "Reverse emission coefficient"),
            IOP("is",    VBIC_IS,      IF_REAL, "Transport saturation current"),
            IOP("ikf",   VBIC_IKF,     IF_REAL, "Forward knee current"),
            IOP("ikr",   VBIC_IKR,     IF_REAL, "Reverse knee current"),
            IOP("vaf",   VBIC_VAF,     IF_REAL, "Forward Early voltage"),
            IOP("var",   VBIC_VAR,     IF_REAL, "Reverse Early voltage"),
            IOP("bf",    VBIC_BF,      IF_REAL, "Ideal forward beta"),
            IOP("br",    VBIC_BR,      IF_REAL, "Ideal reverse beta"),
            /* ... additional parameters ... */
            IOP("rth",   VBIC_RTH,     IF_REAL, "Thermal resistance"),
            IOP("cth",   VBIC_CTH,     IF_REAL, "Thermal capacitance"),
        },
        .flags = DEV_DEFAULT,
    },
    
    /* Device functions */
    .DEVparam = VBICparam,
    .DEVmodParam = VBICmParam,
    .DEVload = VBICload,
    .DEVsetup = VBICsetup,
    .DEVunsetup = VBICunsetup,
    .DEVpzSetup = VBICsetup,
    .DEVtemperature = VBICtemp,
    .DEVtrunc = VBICtrunc,
    .DEVfindBranch = VBICfindBr,
    .DEVacLoad = VBICacLoad,
    .DEVaccept = VBICaccept,
    .DEVdestroy = VBICdestroy,
    .DEVmodDelete = VBICmDelete,
    .DEVdelete = VBICdelete,
    .DEVsetic = VBICgetic,
    .DEVask = VBICask,
    .DEVmAsk = VBICmAsk,
    .DEVpzLoad = VBICpzLoad,
    .DEVconvTest = VBICconvTest,
    .DEVsoaCheck = VBICsoachk,
};
```

### **4.3 Matrix Setup and Pointer Allocation**

**From `vbicsetup.c`**:

```c
int VBICsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    VBICmodel *model = (VBICmodel*)inModel;
    VBICinstance *here;
    
    for (; model; model = model->VBICnextModel) {
        for (here = model->VBICinstances; here; here = here->VBICnextInstance) {
            /* Allocate state vector indices */
            here->VBICvbeState = *states;
            (*states)++;
            here->VBICvbcState = *states;
            (*states)++;
            here->VBICvcsState = *states;
            (*states)++;
            here->VBICqbeState = *states;
            (*states)++;
            here->VBICqbcState = *states;
            (*states)++;
            here->VBICqdiffState = *states;
            (*states)++;
            here->VBICtjState = *states;
            (*states)++;
            
            /* Allocate matrix pointers for 4-terminal device */
            SMPmakeElt(matrix, here->VBICbaseNode, here->VBICbaseNode, 
                      &here->VBICbaseBasePtr);
            SMPmakeElt(matrix, here->VBICbaseNode, here->VBICemitNode,
                      &here->VBICbaseEmitPtr);
            SMPmakeElt(matrix, here->VBICbaseNode, here->VBICcollNode,
                      &here->VBICbaseCollPtr);
            SMPmakeElt(matrix, here->VBICbaseNode, here->VBICsubsNode,
                      &here->VBICbaseSubsPtr);
            
            SMPmakeElt(matrix, here->VBICemitNode, here->VBICbaseNode,
                      &here->VBICemitBasePtr);
            SMPmakeElt(matrix, here->VBICemitNode, here->VBICemitNode,
                      &here->VBICemitEmitPtr);
            SMPmakeElt(matrix, here->VBICemitNode, here->VBICcollNode,
                      &here->VBICemitCollPtr);
            SMPmakeElt(matrix, here->VBICemitNode, here->VBICsubsNode,
                      &here->VBICemitSubsPtr);
            
            SMPmakeElt(matrix, here->VBICcollNode, here->VBICbaseNode,
                      &here->VBICcollBasePtr);
            SMPmakeElt(matrix, here->VBICcollNode, here->VBICemitNode,
                      &here->VBICcollEmitPtr);
            SMPmakeElt(matrix, here->VBICcollNode, here->VBICcollNode,
                      &here->VBICcollCollPtr);
            SMPmakeElt(matrix, here->VBICcollNode, here->VBICsubsNode,
                      &here->VBICcollSubsPtr);
            
            SMPmakeElt(matrix, here->VBICsubsNode, here->VBICbaseNode,
                      &here->VBICsubsBasePtr);
            SMPmakeElt(matrix, here->VBICsubsNode, here->VBICemitNode,
                      &here->VBICsubsEmitPtr);
            SMPmakeElt(matrix, here->VBICsubsNode, here->VBICcollNode,
                      &here->VBICsubsCollPtr);
            SMPmakeElt(matrix, here->VBICsubsNode, here->VBICsubsNode,
                      &here->VBICsubsSubsPtr);
            
            /* Get RHS vector pointers */
            here->VBICbaseRhsPtr = ckt->CKTrhs + here->VBICbaseNode;
            here->VBICemitRhsPtr = ckt->CKTrhs + here->VBICemitNode;
            here->VBICcollRhsPtr = ckt->CKTrhs + here->VBICcollNode;
            here->VBICsubsRhsPtr = ckt->CKTrhs + here->VBICsubsNode;
            
            /* Initialize internal states */
            if (ckt->CKTmode & MODEINITTRAN) {
                if (here->VBICicGiven) {
                    *(ckt->CKTstate0 + here->VBICvbeState) = here->VBICicVBE;
                    *(ckt->CKTstate1 + here->VBICvbeState) = here->VBICicVBE;
                }
            }
        }
    }
    return OK;
}
```

### **4.4 Load Function Implementation**

**From `vbicload.c`** (simplified core):

```c
int VBICload(GENmodel *inModel, CKTcircuit *ckt)
{
    VBICmodel *model = (VBICmodel*)inModel;
    VBICinstance *here;
    double vbe, vbc, vcs;
    double gbe, gbc, gcs;
    double ib, ic, isub;
    double qbe, qbc, qdiff;
    double cbe, cbc, cdiff;
    double geqbe, geqbc, geqdiff;
    double ceqbe, ceqbc, ceqdiff;
    double ieqbe, ieqbc, ieqdiff;
    
    for (; model; model = model->VBICnextModel) {
        for (here = model->VBICinstances; here; here = here->VBICnextInstance) {
            /* Get voltages from state vector */
            vbe = *(ckt->CKTstate0 + here->VBICvbeState);
            vbc = *(ckt->CKTstate0 + here->VBICvbcState);
            vcs = *(ckt->CKTstate0 + here->VBICvcsState);
            
            /* Apply limiting to prevent convergence issues */
            vbe = DEVpnjlim(vbe, here->VBICvbe_old, model->VBICvje, V_T, 
                           &here->VBICgbe, &here->VBICcheck);
            vbc = DEVpnjlim(vbc, here->VBICvbc_old, model->VBICvjc, V_T,
                           &here->VBICgbc, &here->VBICcheck);
            
            /* Calculate DC currents (mapping to Section 2.1 equations) */
            double vt = model->VBICtnom * KoverQ;
            double nf_vt = model->VBICnf * vt;
            double nr_vt = model->VBICnr * vt;
            
            /* Base charge calculation */
            double q1 = 1.0 + vbe/model->VBICvar + vbc/model->VBICvaf;
            double q2 = model->VBICis/model->VBICikf * exp(vbe/nf_vt) +
                       model->VBICis/model->VBICikr * exp(vbc/nr_vt);
            double qb = 0.5 * (q1 + sqrt(q1*q1 + 4*q2));
            
            /* Transport currents */
            double icf = model->VBICis/qb * (exp(vbe/nf_vt) - exp(vbc/nf_vt));
            double icr = model->VBICis/qb * (exp(vbe/nr_vt) - exp(vbc/nr_vt));
            
            /* Base currents */
            double ibf = model->VBICise * (exp(vbe/(model->VBICne*vt)) - 1.0) +
                        model->VBICis/(model->VBICbf*qb) * (exp(vbe/nf_vt) - 1.0);
            double ibr = model->VBICisc * (exp(vbc/(model->VBICnc*vt)) - 1.0) +
                        model->VBICis/(model->VBICbr*qb) * (exp(vbc/nr_vt) - 1.0);
            
            /* Terminal currents */
            ib = ibf + ibr;
            ic = icf - icr - ibr;
            
            /* Quasi-saturation resistance (Section 2.2) */
            double rbc = model->VBICrco;
            if (fabs(ic) > 1e-12) {
                double ik_eff = model->VBICik + 1e-12;
                double gamma = model->VBICgamma;
                rbc *= pow(1.0 + pow(fabs(ic)/ik_eff, gamma), 1.0/gamma);
            }
            
            /* Avalanche current (Section 2.3) */
            double iavl = 0.0;
            if (vbc > model->VBICvcbo) {
                iavl = ic * (exp(-model->VBICavc * (vbc - model->VBICvcbo)) - 1.0);
            }
            
            /* Substrate current */
            double isub = model->VBICiss * (exp(vcs/(model->VBICns*vt)) - 1.0);
            
            /* Calculate conductances (Jacobian elements) */
            gbe = (ibf - model->VBICise)/nf_vt;  /* ∂Ib/∂Vbe */
            gbc = (ibr - model->VBICisc)/nr_vt;  /* ∂Ib/∂Vbc */
            
            double gcf = icf/nf_vt;  /* ∂Icf/∂Vbe */
            double gcr = icr/nr_vt;  /* ∂Icr/∂Vbc */
            
            /* Stamp conductances into matrix (Section 3.2 mapping) */
            *here->VBICbaseBasePtr += gbe + gbc;
            *here->VBICbaseEmitPtr -= gbe;
            *here->VBICbaseCollPtr -= gbc;
            
            *here->VBICemitBasePtr -= gbe;
            *here->VBICemitEmitPtr += gbe;
            
            *here->VBICcollBasePtr -= (gcf - gcr - gbc);
            *here->VBICcollCollPtr += (gcf - gcr - gbc);
            
            /* Charge and capacitance calculations (Section 2.4) */
            if (vbe < model->VBICfc * model->VBICvje) {
                cbe = model->VBICcje / pow(1.0 - vbe/model->VBICvje, model->VBICmje);
                qbe = model->VBICcje * model->VBICvje * 
                     (1.0 - pow(1.0 - vbe/model->VBICvje, 1.0 - model->VBICmje)) /
                     (1.0 - model->VBICmje);
            } else {
                double f1 = pow(1.0 - model->VBICfc, 1.0 - model->VBICmje);
                double f2 = 1.0 - model->VBICfc * (1.0 + model->VBICmje);
                double f3 = 1.0 - model->VBICfc;
                cbe = model->VBICcje / f1 * (f2 + model->VBICmje * vbe/model->VBICvje);
                qbe = model->VBICcje * model->VBICvje * 
                     (f1 + (1.0 - f1) * (vbe - model->VBICfc * model->VBICvje) /
                     (model->VBICvje * (1.0 - model->VBICfc)));
            }
            
            /* Similar for BC junction */
            /* ... */
            
            /* Diffusion charge */
            qdiff = model->VBICtf * icf + model->VBICtr * icr;
            cdiff = model->VBICtf * gcf + model->VBICtr * gcr;
            
            /* Companion model for trapezoidal integration */
            if (ckt->CKTmode & MODETRAN) {
                double delta = ckt->CKTdelta;
                ceqbe = 2.0 * cbe / delta;
                ieqbe = ceqbe * vbe + 2.0 * qbe / delta;
                
                /* Stamp capacitive elements */
                *here->VBICbaseBasePtr += ceqbe;
                *here->VBICbaseEmitPtr -= ceqbe;
                *here->VBICemitBasePtr -= ceqbe;
                *here->VBICemitEmitPtr += ceqbe;
                
                *here->VBICbaseRhsPtr -= ieqbe;
                *here->VBICemitRhsPtr += ieqbe;
            }
            
            /* Stamp RHS currents */
            *here->VBICbaseRhsPtr += ib;
            *here->VBICemitRhsPtr -= ib + ic;
            *here->VBICcollRhsPtr += ic - iavl;
            *here->VBICsubsRhsPtr += isub;
            
            /* Store values for next iteration */
            here->VBICvbe_old = vbe;
            here->VBICvbc_old = vbc;
            here->VBICib = ib;
            here->VBICic = ic;
            here->VBICisub = isub;
            here->VBICqbe = qbe;
            here->VBICqbc = qbc;
            here->VBICqdiff = qdiff;
        }
    }
    return OK;
}
```

### **4.5 Safe Operating Area Checking**

**From `vbicsoachk.c`**:

```c
int VBICsoachk(CKTcircuit *ckt, GENmodel *inModel)
{
    VBICmodel *model = (VBICmodel*)inModel;
    VBICinstance *here;
    int violation = 0;
    
    for (; model; model = model->VBICnextModel) {
        for (here = model->VBICinstances; here; here = here->VBICnextInstance) {
            double vce = here->VBICvce;
            double vbe = here->VBICvbe;
            double ic = fabs(here->VBICic);
            double ib = fabs(here->VBICib);
            double pdiss = here->VBICpdiss;
            
            /* Check voltage limits */
            if (vce > model->VBICbvceo) {
                printf("SOA Violation: Vce = %.3f V exceeds BVceo = %.3f V\n",
                       vce, model->VBICbvceo);
                here->VBICsoaFlag = 1;
                violation = 1;
            }
            
            if (vbe > model->VBICbvbeo) {
                printf("SOA Violation: Vbe = %.3f V exceeds BVbeo = %.3f V\n",
                       vbe, model->VBICbvbeo);
                here->VBICsoaFlag =