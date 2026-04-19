# LTRA: API Binding, Memory, and Interface

_Generated 2026-04-13 03:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltra.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltrainit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltraask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltraext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltrainit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltraitf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltrampar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltramask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ltra/ltramisc.c`

# Chapter: VBIC BJT: Matrix Topology, API, and Safe Operating Area

## 1. Technical Introduction

The Vertical Bipolar Inter-Company (VBIC) model represents the most advanced bipolar junction transistor (BJT) formulation in production SPICE simulators, extending the original Gummel-Poon model with critical effects for modern semiconductor design. Within Ngspice, the VBIC implementation provides a comprehensive physical model supporting quasi-saturation, self-heating, avalanche breakdown, substrate network effects, and rigorous safe operating area (SOA) checking—features essential for analog/RF design and reliability verification. This chapter examines the Ngspice VBIC implementation through its mathematical foundation, convergence behavior, and C implementation architecture. The core files—`vbicdefs.h`, `vbicload.c`, `vbicsetup.c`, `vbicsoachk.c`, `vbictemp.c`, and `vbictrunc.c`—implement the complete device lifecycle: from SPICEdev API registration and parameter parsing to DC/AC/transient matrix stamping, temperature scaling, local truncation error (LTE) calculation for adaptive time-stepping, and real-time SOA violation detection. The VBIC model's complexity demands careful numerical treatment: its current and charge equations exhibit strong nonlinearity, its thermal network creates a feedback loop between electrical and thermal domains, and its quasi-saturation resistance introduces additional state variables. The implementation demonstrates advanced SPICE techniques including sparse matrix pointer allocation for the extended equivalent circuit (intrinsic BJT, substrate diode, thermal network), companion model formulation for nonlinear elements, and direct mapping of device physics to Modified Nodal Analysis (MNA) stamps.

## 2. Mathematical Formulation

### 2.1 Intrinsic DC Transport Currents

The VBIC model extends the Gummel-Poon integral charge control relation with separate forward and reverse operation. The normalized base charge \( Q_b \) accounts for high-level injection and Early effects:

\[
Q_b = \frac{1}{2} \left[ 1 + \sqrt{1 + 4 \left( \frac{I_{bf}}{I_{kf}} + \frac{I_{br}}{I_{kr}} \right)} \right] + \frac{V_{bc}}{V_{af}} + \frac{V_{be}}{V_{ar}}
\]

where \( I_{kf} \) and \( I_{kr} \) are forward/reverse knee currents, and \( V_{af} \), \( V_{ar} \) are forward/reverse Early voltages. The forward and reverse diffusion currents are:

\[
I_{bf} = I_{sf} \left[ \exp\left(\frac{V_{be}}{N_f V_T}\right) - 1 \right]
\]
\[
I_{br} = I_{sr} \left[ \exp\left(\frac{V_{bc}}{N_r V_T}\right) - 1 \right]
\]

The collector currents include non-ideality factors and base pushout:

\[
I_{cf} = I_{sf} \left[ \exp\left(\frac{V_{be}}{N_f V_T}\right) - 1 \right] - I_{sr} \left[ \exp\left(\frac{V_{bc}}{N_r V_T}\right) - 1 \right]
\]
\[
I_{cr} = I_{sr} \left[ \exp\left(\frac{V_{bc}}{N_r V_T}\right) - 1 \right] - I_{sf} \left[ \exp\left(\frac{V_{be}}{N_f V_T}\right) - 1 \right]
\]

### 2.2 Quasi-Saturation and Extrinsic Resistance

VBIC models the collector epilayer resistance with voltage-dependent behavior:

\[
R_{bc} = R_{CO} \cdot \left[ 1 + \left( \frac{I_c}{I_{k}} \right)^\gamma \right]^\gamma
\]

where \( R_{CO} \) is the zero-bias collector resistance, \( I_k \) is the critical current for conductivity modulation, and \( \gamma \) is the knee shape factor (typically 0.5-1.0). The effective internal base-collector voltage becomes:

\[
V_{bc,eff} = V_{bc} - I_c \cdot R_{bc}
\]

This formulation captures the conductivity modulation of the lightly-doped collector region at high currents, where the injected carrier density reduces the effective resistance.

### 2.3 Avalanche Multiplication Current

The avalanche current models carrier multiplication in the base-collector depletion region:

\[
I_{avl} = (I_{cf} - I_{cr}) \cdot (M - 1)
\]

with multiplication factor:

\[
M = \frac{1}{1 - \left( \frac{V_{bc}}{V_{afm}} \right)^{n_{avl}}}
\]

where \( V_{afm} \) is the avalanche breakdown voltage and \( n_{avl} \) is the avalanche exponent (typically 2-4). This current adds to the total collector current and can trigger regenerative breakdown.

### 2.4 Substrate Network and Parasitics

The substrate PNP transistor is modeled with simplified transport:

\[
I_{sub} = I_{ss} \left[ \exp\left(\frac{V_{sc}}{N_s V_T}\right) - 1 \right]
\]

where \( V_{sc} \) is the substrate-collector voltage, \( I_{ss} \) is the substrate saturation current, and \( N_s \) is the substrate ideality factor. Parasitic resistances \( R_b \), \( R_c \), \( R_e \) (base, collector, emitter) and junction capacitances complete the equivalent circuit.

### 2.5 Self-Heating Thermal Network

The thermal network solves the power-temperature feedback:

\[
P_{diss} = V_{ce} \cdot I_c + V_{be} \cdot I_b
\]
\[
T_j = T_{amb} + R_{th} \cdot P_{diss} + \tau_{th} \cdot \frac{dP_{diss}}{dt}
\]

where \( R_{th} \) is thermal resistance, \( \tau_{th} \) is thermal time constant, and \( T_j \) is junction temperature. Temperature scaling follows:

\[
I_s(T) = I_s(T_{nom}) \cdot \left( \frac{T}{T_{nom}} \right)^{X_{TI}} \cdot \exp\left[ \frac{E_g}{q \cdot V_T} \cdot \left( \frac{T}{T_{nom}} - 1 \right) \right]
\]

### 2.6 Depletion and Diffusion Charges

Junction depletion charges use the standard SPICE formulation:

\[
Q_{be} = 
\begin{cases}
C_{je0} \cdot V_{be} \cdot \left(1 - \frac{V_{be}}{V_{je}}\right)^{-M_{je}} & V_{be} \leq F_C \cdot V_{je} \\
C_{je0} \cdot \left[ \frac{1 - F_C \cdot (1 + M_{je}) + M_{je} \cdot \frac{V_{be}}{V_{je}}}{(1 - F_C)^{1+M_{je}}} \right] & V_{be} > F_C \cdot V_{je}
\end{cases}
\]

Diffusion charges for forward/reverse operation:

\[
Q_{df} = \tau_f \cdot I_{bf}, \quad Q_{dr} = \tau_r \cdot I_{br}
\]

where \( \tau_f \) and \( \tau_r \) are forward/reverse transit times.

### 2.7 Modified Nodal Analysis Formulation

The complete VBIC equivalent circuit generates a 7×7 MNA stamp (nodes: base, collector, emitter, substrate, internal base, internal collector, thermal):

\[
\begin{bmatrix}
G_{bb} & 0 & 0 & 0 & -G_{bb} & 0 & 0 \\
0 & G_{cc} & 0 & G_{cs} & 0 & -G_{cc} & 0 \\
0 & 0 & G_{ee} & 0 & 0 & 0 & 0 \\
0 & G_{sc} & 0 & G_{ss} & 0 & 0 & 0 \\
-G_{bb} & 0 & 0 & 0 & G_{bb}+g_{\pi}+g_{\mu} & -g_{\mu} & 0 \\
0 & -G_{cc} & 0 & 0 & -g_{\mu} & G_{cc}+g_o+g_{\mu} & g_{th} \\
0 & 0 & 0 & 0 & 0 & g_{th} & G_{th}
\end{bmatrix}
\begin{bmatrix}
V_b \\ V_c \\ V_e \\ V_s \\ V_{bi} \\ V_{ci} \\ T_j
\end{bmatrix}
=
\begin{bmatrix}
0 \\ 0 \\ 0 \\ 0 \\ I_{bf}-I_{br} \\ I_{cf}-I_{cr}+I_{avl} \\ P_{diss}
\end{bmatrix}
\]

where conductances are: \( g_{\pi} = \partial I_{bf}/\partial V_{be} \), \( g_{\mu} = \partial I_{br}/\partial V_{bc} \), \( g_o = \partial I_{cf}/\partial V_{ce} \), \( g_{th} = \partial P_{diss}/\partial T_j \), and \( G_{th} = 1/R_{th} + C_{th}\cdot d/dt \).

## 3. Convergence Analysis

### 3.1 Newton-Raphson Challenges

The VBIC model presents multiple convergence challenges:

1. **Exponential Nonlinearity**: The diode-like \( I_{bf} \), \( I_{br} \) currents have derivatives growing exponentially with voltage, causing large Jacobian entries that can ill-condition the matrix.

2. **Quasi-Saturation Discontinuity**: The piecewise \( R_{bc}(I_c) \) model has discontinuous derivative at the knee current \( I_k \), requiring smoothing:

\[
R_{bc,sm} = R_{CO} \cdot \left[ 1 + \left( \frac{I_c}{I_k} + \delta \right)^\gamma \right]^\gamma
\]

where \( \delta \approx 10^{-6} \) prevents zero-derivative regions.

3. **Thermal-Electrical Feedback**: The coupled system \( f(V, T_j) = 0 \), \( g(V, T_j) = 0 \) can exhibit bi-stability or oscillation if \( \partial P_{diss}/\partial T_j \cdot \partial I_c/\partial V_{be} \) product exceeds stability margin.

### 3.2 Local Truncation Error (LTE) Control

For adaptive time-stepping, VBIC calculates LTE on state variables:

\[
\text{LTE}_Q = \left| \frac{\Delta t^2}{12} \cdot \frac{d^3Q}{dt^3} \right| \leq \text{reltol} \cdot |Q| + \text{abstol}
\]

The third derivative is estimated via backward differences of stored charge values. The thermal state uses:

\[
\text{LTE}_T = \left| \frac{\Delta t^2}{2} \cdot \frac{d^2T_j}{dt^2} \right| \leq \text{reltol} \cdot |T_j - T_{amb}| + \text{abstol}
\]

### 3.3 Safe Operating Area (SOA) Verification

Real-time SOA checking monitors multiple limits:

1. **Junction Temperature**: \( T_j \leq T_{j,max} \) (typically 150-175°C)
2. **Power Dissipation**: \( P_{diss} \leq P_{max}(T_a) \)
3. **Secondary Breakdown**: \( V_{ce} \cdot I_c \leq \text{SB}_{limit}(T_j) \)
4. **Current Crowding**: \( I_c \leq I_{c,max} \cdot (1 + \alpha \cdot (T_j - T_{nom})) \)
5. **Voltage Limits**: \( V_{ce} \leq BV_{ceo} \), \( V_{be} \leq BV_{ebo} \)

Violations trigger simulation warnings or termination, with detailed reporting of exceeding parameters.

### 3.4 Numerical Stabilization Techniques

The implementation employs:

1. **Voltage Limiting**: Using `DEVlimiter()` for \( V_{be} \), \( V_{bc} \) to prevent \( \exp(v/V_T) \) overflow.
2. **GMIN Stepping**: Adding \( 10^{-12} \) S conductance across all junctions to guarantee matrix invertibility.
3. **Damped Newton**: Reducing step size when \( |\Delta V| > 10 \cdot V_T \) or iteration count exceeds 15.
4. **Charge Conservation**: Ensuring \( \sum Q_{nodes} = 0 \) via KCL verification at each iteration.

### 3.5 Convergence Criteria

The Newton loop terminates when all of the following hold:

\[
|V^{k+1} - V^k| \leq \text{VNTOL} + \text{RELTOL} \cdot \max(|V^{k+1}|, |V^k|)
\]
\[
|I^{k+1} - I^k| \leq \text{ABSTOL} + \text{RELTOL} \cdot \max(|I^{k+1}|, |I^k|)
\]
\[
|Q^{k+1} - Q^k| \leq \text{CHGTOL} + \text{RELTOL} \cdot \max(|Q^{k+1}|, |Q^k|)
\]

with typical values: VNTOL = 1 μV, ABSTOL = 1 pA, CHGTOL = 10 fC, RELTOL = 0.001.

## 4. C Implementation

### 4.1 Core Data Structures

**`vbicdefs.h`** defines the hierarchical model/instance structure:

```c
typedef struct sVBICmodel {
    int VBICmodType;                    /* Model type index */
    struct sVBICmodel *VBICnextModel;   /* Linked list pointer */
    VBICinstance *VBICinstances;        /* Instance chain */
    
    /* Model parameters */
    double VBICtype;                    /* NPN/PNP type */
    double VBICtnom;                    /* Nominal temperature */
    double VBICis;                      /* Transport saturation current */
    double VBICnf;                      /* Forward ideality factor */
    double VBICnr;                      /* Reverse ideality factor */
    double VBICikf;                     /* Forward knee current */
    double VBICikr;                     /* Reverse knee current */
    double VBIVaf;                      /* Forward Early voltage */
    double VBICvar;                     /* Reverse Early voltage */
    double VBICrc;                      /* Epilayer resistance */
    double VBICik;                      /* Quasi-saturation knee current */
    double VBICgamm;                    /* Quasi-saturation exponent */
    double VBICavc1;                    /* Avalanche coefficient 1 */
    double VBICavc2;                    /* Avalanche coefficient 2 */
    double VBICiss;                     /* Substrate saturation current */
    double VBICns;                      /* Substrate ideality factor */
    double VBICrth;                     /* Thermal resistance */
    double VBICcth;                     /* Thermal capacitance */
    
    /* Flags and state */
    unsigned VBICisGiven : 1;           /* Parameter given flags */
    unsigned VBICrcGiven : 1;
    unsigned VBICrthGiven : 1;
    
    /* Matrix pointers */
    double *VBICbasePtr;                /* Base node pointer */
    double *VBICcolPtr;                 /* Collector node pointer */
    double *VBICemitPtr;                /* Emitter node pointer */
    double *VBICsubsPtr;                /* Substrate node pointer */
    double *VBICbasePrimePtr;           /* Internal base pointer */
    double *VBICcolPrimePtr;            /* Internal collector pointer */
    double *VBICtempPtr;                /* Thermal node pointer */
} VBICmodel;

typedef struct sVBICinstance {
    struct sVBICinstance *VBICnextInstance; /* Instance chain */
    VBICmodel *VBICmodPtr;              /* Parent model */
    
    /* Instance parameters */
    char *VBICname;                     /* Instance name */
    int VBICbaseNode;                   /* External node indices */
    int VBICcolNode;
    int VBICemitNode;
    int VBICsubsNode;
    double VBICarea;                    /* Area scaling factor */
    double VBICm;                       /* Parallel multiplier */
    
    /* State variables */
    double VBICvbe;                     /* Internal BE voltage */
    double VBICvbc;                     /* Internal BC voltage */
    double VBICvce;                     /* Collector-emitter voltage */
    double VBICic;                      /* Collector current */
    double VBICib;                      /* Base current */
    double VBICqbe;                     /* BE junction charge */
    double VBICqbc;                     /* BC junction charge */
    double VBICqsub;                    /* Substrate charge */
    double VBICpdis;                    /* Dissipated power */
    double VBICtj;                      /* Junction temperature */
    
    /* Derivatives */
    double VBICgpi;                     /* Base-emitter conductance */
    double VBICgmu;                     /* Base-collector conductance */
    double VBICgo;                      /* Output conductance */
    double VBICgm;                      /* Transconductance */
    double VBICgx;                      /* Quasi-saturation conductance */
    double VBICgt;                      /* Thermal conductance */
    
    /* History for LTE */
    double VBICqbeH1, VBICqbeH2;       /* Two-step charge history */
    double VBICqbcH1, VBICqbcH2;
    double VBICtjH1, VBICtjH2;         /* Thermal history */
    
    /* Matrix indices */
    int VBICbasePrimeNode;              /* Internal node numbers */
    int VBICcolPrimeNode;
    int VBICtempNode;
    
    /* Flags */
    unsigned VBICoff : 1;               /* Device off flag */
    unsigned VBICtempGiven : 1;         /* Temperature specified */
    unsigned VBICsoaViolation : 1;      /* SOA violation detected */
} VBICinstance;
```

### 4.2 SPICEdev API Binding

**`vbicinit.c`** registers the device with Ngspice:

```c
SPICEdev VBICinfo = {
    .DEVpublic = {
        .name = "VBIC",
        .description = "Vertical Bipolar Inter-Company Model",
        .terms = 4,                     /* B, C, E, S terminals */
        .numNames = 4,
        .termNames = {"b", "c", "e", "s"},
        .numInstanceParms = 3,          /* area, m, temp */
        .instanceParms = VBICpTable,
        .numModelParms = 28,
        .modelParms = VBICmTable,
        .flags = DEV_DEFAULT,
    },
    .DEVparam = VBICparam,
    .DEVmodParam = VBICmParam,
    .DEVload = VBICload,
    .DEVsetup = VBICsetup,
    .DEVunsetup = NULL,
    .DEVpzSetup = VBICsetup,
    .DEVtemperature = VBICtemp,
    .DEVtrunc = VBICtrunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = VBICacLoad,
    .DEVaccept = NULL,
    .DEVdestroy = VBICdestroy,
    .DEVmodDelete = VBICmDelete,
    .DEVdelete = VBICdelete,
    .DEVsetic = VBICgetic,
    .DEVask = VBICask,
    .DEVmodAsk = VBICmAsk,
    .DEVpzLoad = VBICpzLoad,
    .DEVconvTest = VBICconvTest,
    .DEVsenSetup = VBICsSetup,
    .DEVsenLoad = VBICsLoad,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVdisto = NULL,
    .DEVnoise = VBICnoise,
    .DEVsoaCheck = VBICsoaCheck,
    .DEVinstSize = sizeof(VBICinstance),
    .DEVmodSize = sizeof(VBICmodel)
};

int VBICinit(GENmodel *inModel, CKTcircuit *ckt) {
    return SPICEdevInit(&VBICinfo, inModel, ckt);
}
```

### 4.3 Matrix Setup and Pointer Allocation

**`vbicsetup.c`** allocates sparse matrix pointers for the 7-node equivalent circuit:

```c
int VBICsetup(SMPmatrix *matrix, GENmodel *inModel, 
              CKTcircuit *ckt, int *states) {
    VBICmodel *model = (VBICmodel*)inModel;
    VBICinstance *here;
    
    for (; model; model = model->VBICnextModel) {
        for (here = model->VBICinstances; here; here = here->VBICnextInstance) {
            /* Allocate internal nodes */
            here->VBICbasePrimeNode = *states;
            (*states)++;
            here->VBICcolPrimeNode = *states;
            (*states)++;
            here->VBICtempNode = *states;
            (*states)++;
            
            /* Request matrix pointers for all 7 nodes */
            SMPmakeElt(matrix, here->VBICbaseNode, here->VBICbasePrimeNode);
            SMPmakeElt(matrix, here->VBICbaseNode, here->VBICbaseNode);
            SMPmakeElt(matrix, here->VBICbasePrimeNode, here->VBICbaseNode);
            SMPmakeElt(matrix, here->VBICbasePrimeNode, here->VBICbasePrimeNode);
            SMPmakeElt(matrix, here->VBICbasePrimeNode, here->VBICcolPrimeNode);
            
            SMPmakeElt(matrix, here->VBICcolNode, here->VBICcolPrimeNode);
            SMPmakeElt(matrix, here->VBICcolNode, here->VBICcolNode);
            SMPmakeElt(matrix, here->VBICcolPrimeNode, here->VBICcolNode);
            SMPmakeElt(matrix, here->VBICcolPrimeNode, here->VBICcolPrimeNode);
            SMPmakeElt(matrix, here->VBICcolPrimeNode, here->VBICbasePrimeNode);
            SMPmakeElt(matrix, here->VBICcolPrimeNode, here->VBICtempNode);
            
            SMPmakeElt(matrix, here->VBICemitNode, here->VBICemitNode);
            
            SMPmakeElt(matrix, here->VBICsubsNode, here->VBICcolNode);
            SMPmakeElt(matrix, here->VBICsubsNode, here->VBICsubsNode);
            SMPmakeElt(matrix, here->VBICcolNode, here->VBICsubsNode);
            
            SMPmakeElt(matrix, here->VBICtempNode, here->VBICcolPrimeNode);
            SMPmakeElt(matrix, here->VBICtempNode, here->VBICtempNode);
            
            /* Store pointers for fast access in load function */
            model->VBICbasePtr = SMPfindElt(matrix, here->VBICbaseNode, here->VBICbaseNode, 1);
            model->VBICcolPtr = SMPfindElt(matrix, here->VBICcolNode, here->VBICcolNode, 1);
            /* ... all other pointers */
        }
    }
    return OK;
}
```

### 4.4 DC Load Implementation

**`vbicload.c`** implements the core Newton-Raphson load function:

```c
int VBICload(GENmodel *inModel, CKTcircuit *ckt) {
    VBICmodel *model = (VBICmodel*)inModel;
    VBICinstance *here;
    double vbe, vbc, vce, vt, is_t, ibf, ibr, icf, icr;
    double gpi, gmu, go, gm, gx, gt, qb, dqb_dvbe, dqb_dvbc;
    double rbc, drbc_dic, mavl, dmavl_dvbc, iavl, diavl_dvbc;
    double pdis, dpdis_dvbe, dpdis_dvbc, dpdis_dtj;
    
    for (; model; model = model->VBICnextModel) {
        for (here = model->VBICinstances; here; here = here->VBICnextInstance) {
            /* Get voltages with limiting */
            vbe = DEVlimiter(ckt->CKTrhs[here->VBICbasePrimeNode] - 
                            ckt->CKTrhs[here->VBICemitNode], 
                            here->VBICvbe, model->VBICvt, ckt);
            vbc = DEVlimiter(ckt->CKTrhs[here->VBICbasePrimeNode] - 
                            ckt->CKTrhs[here->VBICcolPrimeNode], 
                            here->VBICvbc, model->VBICvt, ckt);
            vce = ckt->CKTrhs[here->VBICcolPrimeNode] - 
                  ckt->CKTrhs[here->VBICemitNode];
            
            vt = model->VBICvt * here->VBICtj / model->VBICtnom;
            
            /* Temperature-adjusted saturation current */
            is_t = model->VBICis * pow(here->VBICtj/model->VBICtnom, model->VBICxti) *
                   exp(model->VBICeg/(model->VBICvt*model->VBICtnom) * 
                       (here->VBICtj/model->VBICtnom - 1));
            
            /* Base charge calculation (Eq. 2.1) */
            ibf = is_t * (exp(vbe/(model->VBICnf*vt)) - 1);
            ibr = is_t * (exp(vbc/(model->VBICnr*vt)) - 1);
            qb = 0.5 * (1 + sqrt(1 + 4*(ibf/model->VBICikf + ibr/model->VBICikr))) +
                 vbc/model->VBICvaf + vbe/model->VBICvar;
            
            dqb_dvbe = (1/(model->VBICnf*vt)*ibf/model->VBICikf) / 
                       sqrt(1 + 4*(ibf/model->VBICikf + ibr/model->VBICikr)) + 
                       1/model->VBICvar;
            dqb_dvbc = (1/(model->VBICnr*vt)*ibr/model->VBICikr) / 
                       sqrt(1 + 4*(ibf/model->VBICikf + ibr/model->VBICikr)) + 
                       1/model->VBICvaf;
            
            /* Collector currents (Eq. 2.3-2.4) */
            icf = ibf - ibr;
            icr = ibr - ibf;
            
            /* Quasi-saturation resistance (Eq. 2.2) */
            double ic_abs = fabs(icf);
            if (ic_abs < 1e-12) ic_abs = 1e-12;
            double ratio = ic_abs / model->VBICik;
            rbc = model->VBICrc * pow(1 + pow(ratio, model->VBICgamm), model->VBICgamm);
            drbc_dic = model->VBICrc * model->VBICgamm * 
                       pow(1 + pow(ratio, model->VBICgamm), model->VBICgamm-1) *
                       model->VBICgamm * pow(ratio, model->VBICgamm-1) / model->VBICik;
            
            /* Effective internal voltage */
            double vbc_eff = vbc - icf * rbc;
            
            /* Recalculate currents with effective voltage */
            ibr = is_t * (exp(vbc_eff/(model->VBICnr*vt)) - 1);
            icf = ibf - ibr;
            
            /* Avalanche multiplication (Eq. 2.3) */
            double vbc_abs = fabs(vbc_eff);
            if (vbc_abs < model->VBICavc1) {
                mavl = 1.0;
                dmavl_dvbc = 0.0;
            } else {
                mavl = 1.0 / (1.0 - pow(vbc_abs/model->VBICavc1, model->VBICavc2));
                dmavl_dvbc = mavl*mavl * model->VBICavc2 * 
                            pow(vbc_abs/model->VBICavc1, model->VBICavc2-1) / model->VBICavc1;
            }
            iavl = (icf - icr) * (mavl - 1);
            diavl_dvbc = (icf - icr) * dmavl_dvbc + 
                        (dibf_dvbe - dibr_dvbc_eff*(1 - icf*drbc_dic)) * (mavl - 1);
            
            /* Substrate current */
            double isub = model->VBICiss * (exp(vbc/(model->VBICns*vt)) - 1);
            double gsub = model->VBICiss/(model->VBICns*vt) * exp(vbc/(model->VBICns*vt));
            
            /* Power dissipation and thermal derivatives */
            pdis = vce * icf + vbe * ibf;
            dpdis_dvbe = vce * dibf_dvbe + icf * dvce_dvbe + ibf + vbe * dibf_dvbe;
            dpdis_dvbc = vce * dicf_dvbc + icf * dvce_dvbc + vbe * dibf_dvbc;
            dpdis_dtj = vce * dicf_dtj + icf * dvce_dtj + vbe * dibf_dtj;
            
            /* Conductance calculations */
            gpi = dibf_dvbe / qb - ibf * dqb_dvbe / (qb*qb);  /* ∂Ibf/∂Vbe */
            gmu = dibr_dvbc_eff / qb - ibr * dqb_dvbc / (qb*qb); /* ∂Ibr/∂Vbc */
            gm = gpi - gmu;                                   /* Transconductance */
            go = dicf_dvce + diavl_dvbc * dvbc_dvce;          /* Output conductance */
            gx = 1.0 / (rbc + icf * drbc_dic);               /* Quasi-saturation conductance */
            gt = dpdis_dtj;                                   /* Thermal conductance */
            
            /* Store for next iteration */
            here->VBICvbe = vbe;
            here->VBICvbc = vbc;
            here->VBICic = icf + iavl;
            here->VBICib = ibf/qb + ibr/qb;
            here->VBICgpi = gpi;
            here->VBICgmu = gmu;
            here->VBICgo = go;
            here->VBICgm = gm;
            here->VBICgx = gx;
            here->VBICgt = gt;
            here->VBICpdis = pdis;
            
            /* Stamp the 7×7 MNA matrix (Eq. 2.7) */
            /* Base node (external) */
            SMPaddElt(matrix, here->VBICbaseNode, here->VBICbaseNode, model->VBICrb);
            SMPaddElt(matrix, here->VBICbaseNode, here->VBICbasePrimeNode, -model->VBICrb);
            
            /* Internal base node */
            SMPaddElt(matrix, here->VBICbasePrimeNode, here->VBICbaseNode, -model->VBICrb);
            SMPaddElt(matrix, here->VBICbasePrimeNode, here->VBICbasePrimeNode, 
                     model->VBICrb + gpi + gmu);
            SMPaddElt(matrix, here->VBICbasePrimeNode, here->VBICcolPrimeNode, -gmu);
            
            /* RHS currents */
            double ib_total = ibf/qb + ibr/qb;
            SMPaddRhs(ckt, here->VBICbasePrimeNode, -ib_total);
            
            /* Internal collector node */
            SMPaddElt(matrix, here->VBICcolPrimeNode, here->VBICcolNode, -model->VBICrc);
            SMPaddElt(matrix, here->VBICcolPrimeNode, here->VBICcolPrimeNode, 
                     model->VBICrc + go + gmu + gx);
            SMPaddElt(matrix, here->VBICcolPrimeNode, here->VBICbasePrimeNode, -gmu);
            SMPaddElt(matrix, here->VBICcolPrimeNode, here->VBICtempNode, gt);
            
            double ic_total = icf + iavl + isub;
            SMPaddRhs(ckt, here->VBICcolPrimeNode, -ic_total);
            
            /* Thermal node */
            SMPaddElt(matrix, here->VBICtempNode, here->VBICcolPrimeNode, gt);
            SMPaddElt(matrix, here->VBICtempNode, here->VBICtempNode, 
                     1.0/model->VBICrth + model->VBICcth/ckt->CKTdelta);
            SMPaddRhs(ckt, here->VBICtempNode, -pdis);
            
            /* Substrate node */
            SMPaddElt(matrix, here->VBICsubsNode, here->VBICcolNode, gsub);
            SMPaddElt(matrix, here->VBICsubsNode, here->VBICsubsNode, gsub);
            SMPaddRhs(ckt, here->VBICsubsNode, -isub);
        }
    }
    return OK;
}
```

### 4.5 Safe Operating Area Checking

**`vbicsoachk.c`** implements real-time SOA monitoring:

```c
int VBICsoaCheck(CKTcircuit *ckt, GENmodel *inModel) {
    VBICmodel *model = (VBICmodel*)inModel;
    VBICinstance *here;
    int violation = 0;
    
    for (; model; model = model->VBICnextModel) {
        for (here = model->VBICinstances; here; here = here->VBICnextInstance) {
            /* Junction temperature check */
            if (here->VBICtj > model->VBICtmax) {
                printf("WARNING: VBIC %s Tj=%.1fC > Tmax=%.1fC at t=%.2es\n",
                       here->VBICname, here->VBICtj-273.15, 
                       model->VBICtmax-273.15, ckt->CKTtime);
                here->VBICsoaViolation = 1;
                violation = 1;
            }
            
            /* Power dissipation check */
            double pmax = model->VBICpmax * (1 - (here->VBICtj-298)/model->VBICrthja);
            if (here->VBICpdis > pmax) {
                printf("WARNING: VBIC %s Pdiss=%.3fW > Pmax=%.3fW at t=%.2es\n",
                       here->VBICname, here->VBICpdis, pmax, ckt->CKTtime);
                here->VBICsoaViolation = 1;
                violation = 1;
            }
            
            /* Secondary breakdown check */
            double sblimit = model->VBICsblim * exp(-(here->VBICtj-298)/model->VBICsbtc);
            if (here->VBICvce * here->VBICic > sblimit) {
                printf("WARNING: VBIC %s Vce*Ic=%.3f > SBlimit=%.3f at t=%.2es\n",
                       here->VBICname, here->VBICvce*here->VBICic, 
                       sblimit, ckt->CKTtime);
                here->VBICsoaViolation = 1;
                violation = 1;
            }
            
            /* Current limit with temperature derating */
            double icmax = model->VBICicmax * (1 - model->VBICictc*(here->VBICtj-298));
            if (fabs(here->VBICic) > icmax) {
                printf("WARNING: VBIC %s |Ic|=%.3fA > Icmax=%.3fA at t=%.2es\n",
                       here->VBICname, fabs(here->VBICic), icmax, ckt->CKTtime);
                here->VBICsoaViolation = 1;
                violation = 1;
            }
            
            /* Voltage limits */
            if (fabs(here->VBICvce) > model->VBICbvceo) {
                printf("WARNING: VBIC %s |Vce|=%.1fV > BVceo=%.1fV at t=%.2es\n",
                       here->VBICname, fabs(here->VBICvce), model->VBICbvceo, ckt->CKTtime);