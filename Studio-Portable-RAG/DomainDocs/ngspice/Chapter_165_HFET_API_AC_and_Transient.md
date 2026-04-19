# HFET and MESFET: Matrix Setup, AC, and Transient Control

_Generated 2026-04-13 01:59 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfet.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetacl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfetpzl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet1/hfettrunc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2setup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2acl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2pzl.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/hfet2/hfet2trunc.c`

# Chapter 8: VBIC BJT: Matrix Topology, API, and Safe Operating Area

## 1. Technical Introduction

The Vertical Bipolar Inter-Company (VBIC) model represents the state-of-the-art in bipolar junction transistor simulation, extending the Gummel-Poon framework with essential effects for modern high-speed and power applications. Within Ngspice, the VBIC implementation follows the canonical SPICE device architecture, decomposing functionality across specialized C modules that handle matrix topology definition, API binding, and operational safety enforcement. This chapter examines the core files `vbicsetup.c`, `vbicmask.c`, `vbicask.c`, `vbicinit.c`, `vbic.c`, `vbicdel.c`, `vbicmdel.c`, `vbicdest.c`, and `vbicsoachk.c`, which collectively implement the 4/5-terminal MNA formulation, manage the SPICEdev interface, and enforce Safe Operating Area (SOA) constraints through real-time junction temperature and power dissipation monitoring. The implementation demonstrates advanced numerical techniques for handling quasi-saturation, self-heating, avalanche breakdown, and substrate effects while maintaining robust convergence in transient and DC analyses.

## 2. Mathematical Formulation

### 2.1 MNA Matrix Topology and Terminal Mapping

The VBIC model supports both 4-terminal (collector, base, emitter, substrate) and 5-terminal (with thermal node) configurations. The Modified Nodal Analysis formulation extends the standard BJT stamp with additional rows/columns for substrate current and thermal dynamics:

\[
\begin{bmatrix}
G_{cc} & G_{cb} & G_{ce} & G_{cs} & G_{ct} \\
G_{bc} & G_{bb} & G_{be} & G_{bs} & G_{bt} \\
G_{ec} & G_{eb} & G_{ee} & G_{es} & G_{et} \\
G_{sc} & G_{sb} & G_{se} & G_{ss} & G_{st} \\
G_{tc} & G_{tb} & G_{te} & G_{ts} & G_{tt}
\end{bmatrix}
\begin{bmatrix}
V_c \\ V_b \\ V_e \\ V_s \\ V_t
\end{bmatrix}
=
\begin{bmatrix}
I_c \\ I_b \\ I_e \\ I_s \\ I_t
\end{bmatrix}
\]

Where the thermal node voltage \(V_t\) represents junction temperature rise \(\Delta T_j\) when the 5-terminal model is active. The conductance submatrices \(G_{xy}\) contain derivatives of terminal currents with respect to terminal voltages: \(G_{xy} = \partial I_x/\partial V_y\).

### 2.2 Intrinsic DC Current Formulations

The VBIC model extends Gummel-Poon with separate forward and reverse operation:

**Forward Injection Current:**
\[
I_{bf} = \frac{I_{sf}}{Q_b} \left[ \exp\left(\frac{V_{b'e'}}{N_f V_T}\right) - 1 \right] + \frac{I_{lef}}{Q_b} \left[ \exp\left(\frac{V_{b'e'}}{N_{lef} V_T}\right) - 1 \right]
\]

**Reverse Injection Current:**
\[
I_{br} = \frac{I_{sr}}{Q_b} \left[ \exp\left(\frac{V_{b'c'}}{N_r V_T}\right) - 1 \right] + \frac{I_{ler}}{Q_b} \left[ \exp\left(\frac{V_{b'c'}}{N_{ler} V_T}\right) - 1 \right]
\]

**Base Charge Modulation:**
\[
Q_b = \frac{1}{2} \left[ 1 + \sqrt{1 + 4 \left( \frac{I_{bf}}{I_{kf}} + \frac{I_{br}}{I_{kr}} \right)} \right] + \frac{V_{b'e'}}{V_{arf}} + \frac{V_{b'c'}}{V_{arr}}
\]

**Collector Currents:**
\[
I_{cf} = I_{bf} - \frac{I_{sf}}{\beta_f} \left[ \exp\left(\frac{V_{b'e'}}{N_f V_T}\right) - 1 \right]
\]
\[
I_{cr} = I_{br} - \frac{I_{sr}}{\beta_r} \left[ \exp\left(\frac{V_{b'c'}}{N_r V_T}\right) - 1 \right]
\]

### 2.3 Quasi-Saturation and Extrinsic Resistances

The VBIC model includes bias-dependent collector resistance for quasi-saturation modeling:

\[
R_{bc} = R_{co} \left[ 1 + \left( \frac{I_c}{I_{k}} \right)^\gamma \right]^\gamma
\]

\[
V_{bc,eff} = V_{bc} - I_c R_{bc}
\]

The extrinsic base resistance includes current crowding effects:

\[
R_b = R_{bm} + \frac{R_{bx} - R_{bm}}{Q_b}
\]

### 2.4 Avalanche Multiplication and Substrate Current

Avalanche current is modeled using the Miller formula:

\[
I_{avl} = I_c \left[ M(V_{cb}) - 1 \right]
\]

\[
M(V_{cb}) = \frac{1}{1 - \left( \frac{V_{cb}}{V_{af}} \right)^{m_{exp}}}
\]

Substrate current arises from hole injection into the substrate:

\[
I_{sub} = I_{ss} \left[ \exp\left(\frac{V_{sc}}{N_s V_T}\right) - 1 \right]
\]

### 2.5 Charge Storage and Capacitance Models

**Depletion Charges:**
\[
Q_{je} = C_{je0} V_{je} \left( 1 - \frac{V_{b'e'}}{V_{je}} \right)^{1 - m_{je}} \quad \text{for } V_{b'e'} < F_c V_{je}
\]
\[
Q_{je} = C_{je0} V_{je} \left[ \frac{1 - F_c (1 + m_{je}) + m_{je} \frac{V_{b'e'}}{V_{je}}}{(1 - F_c)^{1 + m_{je}}} \right] \quad \text{for } V_{b'e'} \geq F_c V_{je}
\]

**Diffusion Charges:**
\[
Q_{de} = \tau_f I_{bf}
\]
\[
Q_{dc} = \tau_r I_{br}
\]

**Parasitic Capacitances:**
\[
C_{bx} = C_{bxc} + C_{bx} \cdot V_{bc}^{m_{bx}}
\]

### 2.6 Self-Heating and Thermal Network

The thermal network models junction temperature rise:

\[
P_{diss} = V_{ce} I_c + V_{be} I_b
\]

\[
T_j = T_{amb} + R_{th} P_{diss} + \tau_{th} \frac{dP_{diss}}{dt}
\]

Temperature scaling of saturation currents:

\[
I_s(T) = I_s(T_{nom}) \left( \frac{T}{T_{nom}} \right)^{X_{TI}} \exp\left[ \frac{E_g}{q V_T} \left( \frac{T}{T_{nom}} - 1 \right) \right]
\]

### 2.7 Convergence Analysis

**Jacobian Matrix Elements:**
The Newton-Raphson iteration requires computation of all conductance terms:

\[
g_{\pi} = \frac{\partial I_{bf}}{\partial V_{b'e'}} = \frac{I_{sf}}{N_f V_T Q_b} \exp\left(\frac{V_{b'e'}}{N_f V_T}\right) + \frac{I_{lef}}{N_{lef} V_T Q_b} \exp\left(\frac{V_{b'e'}}{N_{lef} V_T}\right)
\]

\[
g_{\mu} = \frac{\partial I_{br}}{\partial V_{b'c'}} = \frac{I_{sr}}{N_r V_T Q_b} \exp\left(\frac{V_{b'c'}}{N_r V_T}\right) + \frac{I_{ler}}{N_{ler} V_T Q_b} \exp\left(\frac{V_{b'c'}}{N_{ler} V_T}\right)
\]

**Base Charge Derivatives:**
\[
\frac{\partial Q_b}{\partial V_{b'e'}} = \frac{1}{V_{arf}} + \frac{2}{Q_b \sqrt{1 + 4\left(\frac{I_{bf}}{I_{kf}} + \frac{I_{br}}{I_{kr}}\right)}} \cdot \frac{1}{I_{kf}} \frac{\partial I_{bf}}{\partial V_{b'e'}}
\]

**Local Truncation Error Control:**
For charge-based LTE calculation:

\[
LTE = \frac{|Q_{TR} - Q_{BE}|}{reltol \cdot |Q_{TR}| + abstol}
\]

Where \(Q_{TR}\) is trapezoidal rule estimate and \(Q_{BE}\) is backward Euler estimate.

**Safe Operating Area Constraints:**
Real-time checking against multiple limits:

\[
P_{max} = \frac{T_{j,max} - T_{amb}}{R_{th}}
\]
\[
I_{c,max} = \frac{P_{max}}{V_{ce,sat}}
\]
\[
V_{ceo} = V_{af} \cdot (1 - \epsilon)^{1/m_{exp}}
\]

## 3. C Implementation

### 3.1 Core Data Structures

```c
/* vbicdefs.h - Primary structure definitions */
typedef struct sVBICmodel {
    int VBICmodType;                  /* Device type index */
    struct sVBICmodel *VBICnextModel; /* Linked list pointer */
    VBICinstance *VBICinstances;      /* Instance chain */
    
    /* Model parameters */
    double VBICtype;                  /* NPN/PNP type */
    double VBICtnom;                  /* Nominal temperature */
    double VBICavc;                   /* Avalanche coefficient */
    double VBICavcExp;                /* Avalanche exponent */
    double VBICikf;                   /* Forward knee current */
    double VBICikr;                   /* Reverse knee current */
    double VBICrc;                    /* Collector resistance */
    double VBICrco;                   /* Zero-bias collector resistance */
    double VBICgamma;                 /* Quasi-saturation exponent */
    double VBICvaf;                   /* Forward Early voltage */
    double VBICvar;                   /* Reverse Early voltage */
    double VBICis;                    /* Transport saturation current */
    double VBICnf;                    /* Forward emission coefficient */
    double VBICnr;                    /* Reverse emission coefficient */
    double VBICbf;                    /* Forward beta */
    double VBICbr;                    /* Reverse beta */
    double VBICvof;                   /* Forward offset voltage */
    double VBICvor;                   /* Reverse offset voltage */
    double VBICtf;                    /* Forward transit time */
    double VBICtr;                    /* Reverse transit time */
    double VBICcje;                   /* Base-emitter zero-bias capacitance */
    double VBICvje;                   /* Base-emitter built-in potential */
    double VBICmje;                   /* Base-emitter grading coefficient */
    double VBICcjc;                   /* Base-collector zero-bias capacitance */
    double VBICvjc;                   /* Base-collector built-in potential */
    double VBICmjc;                   /* Base-collector grading coefficient */
    double VBICrth;                   /* Thermal resistance */
    double VBICcth;                   /* Thermal capacitance */
    
    /* Flags and state indicators */
    unsigned VBICavcGiven : 1;        /* Parameter given flags */
    unsigned VBICikfGiven : 1;
    unsigned VBICrcGiven : 1;
    unsigned VBICrthGiven : 1;
    unsigned VBICtempGiven : 1;
} VBICmodel;

typedef struct sVBICinstance {
    struct sVBICinstance *VBICnextInstance; /* Instance chain */
    VBICmodel *VBICmodPtr;                  /* Parent model */
    
    /* Terminal connections */
    int VBICcolNode;      /* Collector node */
    int VBICbaseNode;     /* Base node */
    int VBICemitNode;     /* Emitter node */
    int VBICsubsNode;     /* Substrate node */
    int VBICtempNode;     /* Thermal node (optional) */
    
    /* Instance parameters */
    double VBICarea;      /* Area scaling factor */
    double VBICm;         /* Parallel multiplier */
    double VBICicVbe;     /* Initial Vbe condition */
    double VBICicVce;     /* Initial Vce condition */
    double VBICtemp;      /* Instance temperature */
    double VBICdtemp;     /* Temperature difference from circuit */
    
    /* State variables */
    double VBICvbe;       /* Internal base-emitter voltage */
    double VBICvbc;       /* Internal base-collector voltage */
    double VBICvce;       /* Collector-emitter voltage */
    double VBICvcs;       /* Collector-substrate voltage */
    
    /* Currents */
    double VBICib;        /* Base current */
    double VBICic;        /* Collector current */
    double VBICie;        /* Emitter current */
    double VBICisub;      /* Substrate current */
    double VBICiavl;      /* Avalanche current */
    double VBICpdiss;     /* Power dissipation */
    
    /* Charges */
    double VBICqbe;       /* Base-emitter charge */
    double VBICqbc;       /* Base-collector charge */
    double VBICqcs;       /* Collector-substrate charge */
    
    /* Conductances (Jacobian elements) */
    double VBICgm;        /* Transconductance */
    double VBICgo;        /* Output conductance */
    double VBICgpi;       /* Base-emitter conductance */
    double VBICgmu;       /* Base-collector conductance */
    double VBICgx;        /* Substrate conductance */
    
    /* Matrix pointers for MNA stamp */
    double *VBICcolColPtr;    /* Gcc */
    double *VBICcolBasePtr;   /* Gcb */
    double *VBICcolEmitPtr;   /* Gce */
    double *VBICcolSubsPtr;   /* Gcs */
    double *VBICcolTempPtr;   /* Gct */
    double *VBICbaseColPtr;   /* Gbc */
    double *VBICbaseBasePtr;  /* Gbb */
    double *VBICbaseEmitPtr;  /* Gbe */
    double *VBICbaseSubsPtr;  /* Gbs */
    double *VBICbaseTempPtr;  /* Gbt */
    /* ... additional matrix pointers for all terminals */
    
    /* RHS vector pointers */
    double *VBICcolRhsPtr;    /* I_c */
    double *VBICbaseRhsPtr;   /* I_b */
    double *VBICemitRhsPtr;   /* I_e */
    double *VBICsubsRhsPtr;   /* I_s */
    double *VBICtempRhsPtr;   /* I_t */
    
    /* Previous state for LTE calculation */
    double VBICqbe_old;
    double VBICqbc_old;
    double VBICqcs_old;
    double VBICvbe_old;
    double VBICvbc_old;
    
    /* Flags */
    unsigned VBICoff : 1;         /* Device off flag */
    unsigned VBICtempNodeGiven : 1; /* Thermal node present */
    unsigned VBICicVbeGiven : 1;  /* Initial condition given */
    unsigned VBICareaGiven : 1;
    unsigned VBICmGiven : 1;
} VBICinstance;
```

### 3.2 SPICEdev API Binding

```c
/* vbic.c - Device registration and function table */
SPICEdev VBICinfo = {
    .DEVpublic = {
        .name = "vbic",
        .description = "Vertical Bipolar Inter-Company Model",
        .terms = 4,  /* Base number of terminals */
        .numNames = 1,
        .termNames = (const char *[]){"c b e s"},
        .numInstanceParms = 12,
        .instanceParms = (IFparm[]){
            IOP("area",  VBIC_AREA,    IF_REAL, "Area factor"),
            IOP("m",     VBIC_M,       IF_REAL, "Parallel multiplier"),
            IOP("icvbe", VBIC_IC_VBE,  IF_REAL, "Initial Vbe"),
            IOP("icvce", VBIC_IC_VCE,  IF_REAL, "Initial Vce"),
            IOP("temp",  VBIC_TEMP,    IF_REAL, "Instance temperature"),
            IOP("dtemp", VBIC_DTEMP,   IF_REAL, "Temperature difference"),
            IOP("off",   VBIC_OFF,     IF_FLAG, "Device initially off"),
            IP("c",      VBIC_COL_NODE,IF_INTEGER, "Collector node"),
            IP("b",      VBIC_BASE_NODE,IF_INTEGER,"Base node"),
            IP("e",      VBIC_EMIT_NODE,IF_INTEGER,"Emitter node"),
            IP("s",      VBIC_SUBS_NODE,IF_INTEGER,"Substrate node"),
            IP("t",      VBIC_TEMP_NODE,IF_INTEGER,"Thermal node"),
        },
        .numModelParms = 32,
        .modelParms = (IFparm[]){
            IOP("type",   VBIC_TYPE,   IF_REAL, "NPN=1, PNP=-1"),
            IOP("tnom",   VBIC_TNOM,   IF_REAL, "Nominal temperature"),
            IOP("is",     VBIC_IS,     IF_REAL, "Transport saturation current"),
            IOP("nf",     VBIC_NF,     IF_REAL, "Forward emission coefficient"),
            IOP("nr",     VBIC_NR,     IF_REAL, "Reverse emission coefficient"),
            IOP("bf",     VBIC_BF,     IF_REAL, "Forward beta"),
            IOP("br",     VBIC_BR,     IF_REAL, "Reverse beta"),
            IOP("ikf",    VBIC_IKF,    IF_REAL, "Forward knee current"),
            IOP("ikr",    VBIC_IKR,    IF_REAL, "Reverse knee current"),
            IOP("vaf",    VBIC_VAF,    IF_REAL, "Forward Early voltage"),
            IOP("var",    VBIC_VAR,    IF_REAL, "Reverse Early voltage"),
            IOP("rc",     VBIC_RC,     IF_REAL, "Collector resistance"),
            IOP("rco",    VBIC_RCO,    IF_REAL, "Zero-bias collector resistance"),
            IOP("gamma",  VBIC_GAMMA,  IF_REAL, "Quasi-saturation exponent"),
            IOP("avc",    VBIC_AVC,    IF_REAL, "Avalanche coefficient"),
            IOP("avcexp", VBIC_AVC_EXP,IF_REAL, "Avalanche exponent"),
            IOP("tf",     VBIC_TF,     IF_REAL, "Forward transit time"),
            IOP("tr",     VBIC_TR,     IF_REAL, "Reverse transit time"),
            IOP("cje",    VBIC_CJE,    IF_REAL, "Base-emitter zero-bias capacitance"),
            IOP("vje",    VBIC_VJE,    IF_REAL, "Base-emitter built-in potential"),
            IOP("mje",    VBIC_MJE,    IF_REAL, "Base-emitter grading coefficient"),
            IOP("cjc",    VBIC_CJC,    IF_REAL, "Base-collector zero-bias capacitance"),
            IOP("vjc",    VBIC_VJC,    IF_REAL, "Base-collector built-in potential"),
            IOP("mjc",    VBIC_MJC,    IF_REAL, "Base-collector grading coefficient"),
            IOP("rth",    VBIC_RTH,    IF_REAL, "Thermal resistance"),
            IOP("cth",    VBIC_CTH,    IF_REAL, "Thermal capacitance"),
            IOP("vof",    VBIC_VOF,    IF_REAL, "Forward offset voltage"),
            IOP("vor",    VBIC_VOR,    IF_REAL, "Reverse offset voltage"),
            IOP("xti",    VBIC_XTI,    IF_REAL, "Saturation current temp exponent"),
            IOP("eg",     VBIC_EG,     IF_REAL, "Energy gap"),
            IOP("fc",     VBIC_FC,     IF_REAL, "Forward bias depletion coefficient"),
            IOP("xtb",    VBIC_XTB,    IF_REAL, "Forward beta temp coefficient"),
        },
    },
    
    /* Function pointers */
    .DEVparam = VBICparam,
    .DEVmodParam = VBICmParam,
    .DEVload = VBICload,
    .DEVsetup = VBICsetup,
    .DEVunsetup = VBICunsetup,
    .DEVpzSetup = VBICpzSetup,
    .DEVtemperature = VBICtemp,
    .DEVtrunc = VBICtrunc,
    .DEVfindBranch = VBICfindBranch,
    .DEVacLoad = VBICacLoad,
    .DEVaccept = VBICaccept,
    .DEVdestroy = VBICdestroy,
    .DEVmodDelete = VBICmDelete,
    .DEVdelete = VBICdelete,
    .DEVsetic = VBICgetic,
    .DEVask = VBICask,
    .DEVmodAsk = VBICmAsk,
    .DEVpzLoad = VBICpzLoad,
    .DEVconvTest = VBICconvTest,
    .DEVsenSetup = VBICsenSetup,
    .DEVsenLoad = VBICsenLoad,
    .DEVsenUpdate = VBICsenUpdate,
    .DEVsenAcLoad = VBICsenAcLoad,
    .DEVsenPrint = VBICsenPrint,
    .DEVsenDisto = VBICsenDisto,
    .DEVsenNoise = VBICsenNoise,
    .DEVsoaCheck = VBICsoaCheck,
};
```

### 3.3 Matrix Setup and Pointer Allocation

```c
/* vbicsetup.c - Matrix topology initialization */
int VBICsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    VBICmodel *model = (VBICmodel *)inModel;
    VBICinstance *here;
    int error;
    
    /* Loop through all models */
    for ( ; model != NULL; model = model->VBICnextModel) {
        /* Loop through all instances of this model */
        for (here = model->VBICinstances; here != NULL; here = here->VBICnextInstance) {
            
            /* Allocate matrix pointers for 4-terminal configuration */
            error = NIallocSparse(matrix, &here->VBICcolColPtr,
                                  here->VBICcolNode, here->VBICcolNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICcolBasePtr,
                                  here->VBICcolNode, here->VBICbaseNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICcolEmitPtr,
                                  here->VBICcolNode, here->VBICemitNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICcolSubsPtr,
                                  here->VBICcolNode, here->VBICsubsNode, ckt);
            if (error) return(error);
            
            /* Allocate base node pointers */
            error = NIallocSparse(matrix, &here->VBICbaseColPtr,
                                  here->VBICbaseNode, here->VBICcolNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICbaseBasePtr,
                                  here->VBICbaseNode, here->VBICbaseNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICbaseEmitPtr,
                                  here->VBICbaseNode, here->VBICemitNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICbaseSubsPtr,
                                  here->VBICbaseNode, here->VBICsubsNode, ckt);
            if (error) return(error);
            
            /* Allocate emitter node pointers */
            error = NIallocSparse(matrix, &here->VBICemitColPtr,
                                  here->VBICemitNode, here->VBICcolNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICemitBasePtr,
                                  here->VBICemitNode, here->VBICbaseNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICemitEmitPtr,
                                  here->VBICemitNode, here->VBICemitNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICemitSubsPtr,
                                  here->VBICemitNode, here->VBICsubsNode, ckt);
            if (error) return(error);
            
            /* Allocate substrate node pointers */
            error = NIallocSparse(matrix, &here->VBICsubsColPtr,
                                  here->VBICsubsNode, here->VBICcolNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICsubsBasePtr,
                                  here->VBICsubsNode, here->VBICbaseNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICsubsEmitPtr,
                                  here->VBICsubsNode, here->VBICemitNode, ckt);
            if (error) return(error);
            
            error = NIallocSparse(matrix, &here->VBICsubsSubsPtr,
                                  here->VBICsubsNode, here->VBICsubsNode, ckt);
            if (error) return(error);
            
            /* Allocate thermal node pointers if 5-terminal model */
            if (here->VBICtempNodeGiven && here->VBICtempNode > 0) {
                error = NIallocSparse(matrix, &here->VBICtempTempPtr,
                                      here->VBICtempNode, here->VBICtempNode, ckt);
                if (error) return(error);
                
                /* Cross-coupling terms for thermal node */
                error = NIallocSparse(matrix, &here->VBICcolTempPtr,
                                      here->VBICcolNode, here->VBICtempNode, ckt);
                if (error) return(error);
                
                error = NIallocSparse(matrix, &here->VBICbaseTempPtr,
                                      here->VBICbaseNode, here->VBICtempNode, ckt);
                if (error) return(error);
                
                error = NIallocSparse(matrix, &here->VBICemitTempPtr,
                                      here->VBICemitNode, here->VBICtempNode, ckt);
                if (error) return(error);
                
                error = NIallocSparse(matrix, &here->VBICsubsTempPtr,
                                      here->VBICsubsNode, here->VBICtempNode, ckt);
                if (error) return(error);
                
                error = NIallocSparse(matrix, &here->VBICtempColPtr,
                                      here->VBICtempNode, here->VBICcolNode, ckt);
                if (error) return(error);
                
                error = NIallocSparse(matrix, &here->VBICtempBasePtr,
                                      here->VBICtempNode, here->VBICbaseNode, ckt);
                if (error) return(error);
                
                error = NIallocSparse(matrix, &here->VBICtempEmitPtr,
                                      here->VBICtempNode, here->VBICemitNode, ckt);
                if (error) return(error);
                
                error = NIallocSparse(matrix, &here->VBICtempSubsPtr,
                                      here->VBICtempNode, here->VBICsubsNode, ckt);
                if (error) return(error);
            }
            
            /* Allocate RHS vector pointers */
            error = NIallocRHS(matrix, &here->VBICcolRhsPtr,
                               here->VBICcolNode, ckt);
            if (error) return(error);
            
            error = NIallocRHS(matrix, &here->VBICbaseRhsPtr,
                               here->VBICbaseNode, ckt);
            if (error) return(error);
            
            error = NIallocRHS(matrix, &here->VBICemitRhsPtr,
                               here->VBICemitNode, ckt);
            if (error) return(error);
            
            error = NIallocRHS(matrix, &here->VBICsubsRhsPtr,
                               here->VBICsubsNode, ckt);
            if (error) return(error);
            
            if (here->VBICtempNodeGiven && here->VBICtempNode > 0) {
                error = NIallocRHS(matrix, &here->VBICtempRhsPtr,
                                   here->VBICtempNode, ckt);
                if (error) return(error);
            }
            
            /* Request state vector slots for charges */
            if (states) {
                here->VBICstate = *states;
                *states += 6;  /* qbe, qbc, qcs, vbe, vbc, pdiss */
            }
        }
    }
    
    return(OK);
}
```

### 3.4 DC and Transient Load Implementation

```c
/* vbicload.c - Matrix stamping for DC and transient analysis */
int VBICload(GENmodel *inModel, CKTcircuit *ckt)
{
    VBICmodel *model = (VBICmodel *)inModel;
    VBICinstance *here;
    double vbe, vbc, vce, vcs;
    double gpi, gmu, go, gm, gx;
    double ib, ic, ie, isub, iavl;
    double qbe, qbc, qcs;
    double cbe, cbc, ccs;
    double vt, vteff;
    double arg, sarg;
    double rb, rc, rbc;
    double tdiff, temp;
    double area, m;
    int selfheat;
    
    vt = CONSTKoverQ * ckt->CKTtemp;
    
    /* Loop through all models */
    for ( ; model != NULL; model = model->VBICnextModel) {
        /* Loop through all instances */
        for (here = model->VBICinstances; here != NULL; here = here->VBICnextInstance) {
            
            area = here->VBICarea;
            m = here->VBICm;
            selfheat = (here->VBICtempNodeGiven && here->VBICtempNode > 0);
            
            /* Get terminal voltages */
            vce = *(ckt->CKTrhsOld + here->VBICcolNode) -
                  *(ckt->CKTrhsOld + here->VBICemitNode);
            vbe = *(ckt->CKTrhsOld + here->VBICbaseNode) -
                  *(ckt->CKTrhsOld + here->VBICemitNode);
            vbc = *(ckt->CKTrhsOld + here->VBICbaseNode) -
                  *(ckt->CKTrhsOld + here->VBICcolNode);
            vcs = *(ckt->CKTrhsOld + here->VBICcolNode) -
                  *(ckt->CKTrhsOld + here->VBICsubsNode);
            
            /* Apply limiting to prevent convergence issues */
            vbe = DEVpnjlim(vbe, here->VBICvbe_old, vt, 
                           model->VBICvof, &here->VBICcheck);
            vbc = DEVpnjlim(vbc, here->VBICvbc_old, vt,
                           model->VBICvor, &here->VBICcheck);
            
            /* Temperature calculation */
            if (selfheat) {
                tdiff = *(ckt->CKTrhsOld + here->VBICtempNode);
                temp = ckt->CKTtemp + tdiff;
                vteff = CONSTKoverQ * temp;
            } else {
                temp = ckt->CKTtemp + here->VBICdtemp;
                vteff = vt;
            }
            
            /* Calculate intrinsic currents (simplified for illustration) */
            /* Forward current */
            arg = vbe / (model->VBICnf * vteff);
            if (arg > 80.0) arg = 80.0;
            ibf = model->VBICis * area * m * (exp(arg) - 1.0);
            
            /* Reverse current */
            arg = vbc / (model->VBICnr * vteff);
            if (arg > 80.0) arg = 80.0;
            ibr = model->VBICis * area * m * (exp(arg) - 1.0);
            
            /* Base charge calculation */
            qb = 0.5 * (1.0 + sqrt(1.0 + 4.0 * (ibf/model->VBICikf + ibr/model->VBICikr)));
            
            /* Normalize currents by base charge */
            ibf /= qb;
            ibr /= qb;
            
            /* Collector currents */
            icf = ibf - model->VBICis * area * m * (exp(vbe/(model->VBICnf*vteff)) - 1.0) / model->VBICbf;
            icr = ibr - model->VBICis * area * m * (exp(vbc/(model->VBICnr*vteff)) - 1.0) / model->VBICbr;
            
            /* Quasi-saturation resistance */
            rbc = model->VBICrco * pow(1.0 + pow(fabs(icf)/model->VBICikf, model->VBICgamma), model->VBICgamma);
            
            /* Avalanche multiplication */
            if (vbc < 0.0) {
                sarg = -vbc / model->VBICvaf;
                if (sarg < 1.0) {
                    mavl = 1.0 / (1.0 - pow(sarg, model->VBICavcExp));
                    iavl = icf * (mavl - 1.0);
                } else {
                    iavl = 1e6; /* Clamp at high field */
                }
            } else {
                iavl = 0.0;
            }
            
            /* Substrate current */
            arg = vcs / (model->VBICns * vteff);
            if (arg > 80.0) arg = 80.0;
            isub = model->VBICiss * area * m * (exp(arg) - 1.0);
            
            /* Total terminal currents */
            ib = ibf + ibr;
            ic = icf - icr - iavl - isub;
            ie = -ibf - icf;
            
            /* Conductance calculations */
            gpi = model->VBICis * area * m * exp(vbe/(model->VBICnf*vteff)) / 
                  (model->VBICnf * vteff * qb);
            gmu = model->VBICis * area * m * exp(vbc/(model->VBICnr*vteff)) / 
                  (model->VBICnr * vteff * qb);
            gm = gpi / model->VBICbf;
            go = gmu / model->VBICbr;
            gx = model->VBICiss * area * m * exp(vcs/(model->VBICns*vteff)) /
                 (model->VBICns * vteff);
            
            /* Charge and capacitance calculations */
            /* Depletion charges */
            if (vbe < model->VBICfc * model->VBICvje) {
                cbe = model->VBICcje * area * m * 
                      pow(1.0 - vbe/model->VBICvje, -model->VBICmje);
                qbe = model->VBICcje * area * m * model->VBICvje * 
                      (1.0 - pow(1.0 - vbe/model->VBICvje, 1.0 - model->VBICmje)) /
                      (1.0 - model->VBICmje);
            } else {
                cbe = model->VBICcje * area * m * 
                      pow(1.0 - model->VBICfc, -model->VBICmje) *
                      (1.0 + model->VBICmje * (vbe - model->VBICfc * model->VBICvje) /
                       (