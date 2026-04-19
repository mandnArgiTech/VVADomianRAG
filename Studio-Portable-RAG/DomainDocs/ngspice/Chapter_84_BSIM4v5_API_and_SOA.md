# BSIM4v5: API Binding, Memory Lifecycle, and SOA

_Generated 2026-04-12 14:51 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/bsim4v5init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5dest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5del.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5mdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5soachk.c`

# Chapter: BSIM4v5: API Binding, Memory Lifecycle, and SOA

## Technical Introduction

The BSIM4v5 model in Ngspice integrates with the simulation kernel through a comprehensive API binding architecture, implements rigorous memory lifecycle management, and enforces Safe Operating Area (SOA) constraints for reliability simulation. The `bsim4init.c` and `b4.c` files define the `SPICEdev BSIM4info` structure that registers the device with Ngspice's function table, providing the essential interface for all simulation modes including parameter tables, load functions, and analysis routines. Memory management is distributed across `b4dest.c` (device-wide destruction), `b4del.c` (instance deletion), and `b4mdel.c` (model deletion), implementing a cascading deallocation strategy for the complex hierarchical data structures that prevents memory leaks. SOA checking in `b4soachk.c` monitors five critical reliability limits during simulation: gate oxide breakdown voltage, drain-source punch-through, electromigration current limits, thermal runaway power dissipation, and hot carrier injection degradation. These components collectively ensure that BSIM4v5 operates as a robust, production-grade device model within the Ngspice ecosystem, with proper SPICE integration, dynamic memory management, and reliability enforcement.

## Mathematical Formulation

### Safe Operating Area (SOA) Reliability Limits

The BSIM4v5 SOA checking implements five mathematical conditions that must be satisfied during SPICE simulation to ensure device reliability:

#### 1. Gate Oxide Breakdown Voltage Limit
```
Vox_acc = |Vgs - Vfb| ≤ Vox_acc_max
```
Where:
- `Vox_acc_max = VOXACC` (gate oxide acceleration voltage, typically 5-7 MV/cm × tox)
- `Vfb` = flat-band voltage
- Violation indicates gate oxide reliability risk

#### 2. Drain-Source Punch-Through Voltage Limit
```
Vds ≤ Vds_max = VDSMAX(T) × [1 + α_pt × (T - T_nom)]
```
Where:
- `VDSMAX` = maximum drain-source voltage at nominal temperature
- `α_pt` = punch-through temperature coefficient (positive for NMOS)
- Temperature scaling accounts for junction breakdown voltage reduction

#### 3. Electromigration Current Density Limit
```
Ids ≤ Ids_max = J_max × Weff × Xj
```
Where:
- `J_max` = maximum allowable current density (typically 1-10 MA/cm²)
- `Weff` = effective channel width
- `Xj` = junction depth
- Based on Black's equation for electromigration lifetime

#### 4. Thermal Power Dissipation Limit
```
P_diss = Ids × Vds ≤ P_max = (T_j_max - T_amb)/R_θja
```
Where:
- `T_j_max` = maximum junction temperature (typically 125-150°C)
- `T_amb` = ambient temperature
- `R_θja` = junction-to-ambient thermal resistance
- Ensures thermal runaway prevention

#### 5. Hot Carrier Injection (HCI) Degradation Limit
```
Vds × Ids / (Weff × Leff) ≤ HCI_limit × exp(-E_a/(k×T))
```
Where:
- `E_a` = activation energy for HCI (typically 0.1-0.2 eV)
- `HCI_limit` = technology-dependent HCI reliability constraint
- Models time-dependent dielectric breakdown acceleration

### Threshold Voltage with Layout-Dependent Effects

The BSIM4v5 threshold voltage incorporates layout-dependent effects critical for accurate SPICE simulation:

#### Base Threshold Voltage with Advanced Body Effect
```
Vth0_eff = VTH0 + K1 × (√(PHI + Vsb) - √PHI) 
                   - K2 × Vsb
                   + K1B × (√(PHI + Vsb) - √PHI)
```

#### Shallow Trench Isolation (STI) Stress Effect
```
ΔVth_STI = (K_STI/TOXE) × (1/SA + 1/SB) × (1/Leff^STI_L)
```
Where:
- `SA`, `SB` = distances to STI edges
- `K_STI` = STI stress coefficient
- `STI_L` = length scaling exponent

#### Well Proximity Effect (WPE)
```
ΔVth_WPE = K_WPE × exp(-LOD/λ_WPE)
```
Where:
- `LOD` = length of diffusion
- `λ_WPE` = characteristic scattering length (~0.1 μm)
- `K_WPE` = WPE coefficient

#### Complete Threshold Voltage for Matrix Stamping
```
Vth = Vth0_eff + ΔVth_SCE + ΔVth_DIBL + ΔVth_NWE 
      + ΔVth_STI + ΔVth_WPE
```
This composite `Vth` directly influences the `gm`, `gds`, and `gmb` derivatives stamped into the Jacobian matrix during Newton-Raphson iterations.

### Mobility Degradation with Stress Effects

#### Universal Mobility Model
```
μ_eff = μ0 / [1 + (UA + UC × Vbs) × (E_eff/E0)^EU 
               + UB × (E_eff/E0)^(2×EU)]
```
Where:
- `E_eff = (Vgs + Vth)/(6 × TOXE)` = effective vertical field
- `E0` = reference field (1 V/cm)

#### STI Stress Mobility Enhancement
```
Δμ_STI = STI_MU1 × (1/SA + 1/SB) + STI_MU2 × (1/SA² + 1/SB²)
```

### Drain Current Formulation for SOA Checking

#### Effective Gate Drive Voltage
```
Vgsteff = 2 × n × Vt × ln[1 + exp((Vgs - Vth)/(2 × n × Vt))]
```
Where:
- `n = 1 + NFACTOR × (CIT + CDSC + CDSCD × Vds)/Cox`
- Ensures C¹ continuity for Newton-Raphson convergence

#### Saturation Voltage with Velocity Saturation
```
Vdsat = (Vgsteff × Esat × Leff)/(Vgsteff + Esat × Leff)
```
Where:
- `Esat = 2 × Vsat / μ_eff`

#### Drain Current for Power Calculation
```
Id = μ_eff × Cox × (Weff/Leff) × Vgsteff × Vdsat
     × [1 + LAMBDA × (Vds - Vdsat)]
     × [1 + (Vds/Vdsat)^M]^(-1/M)
```
This current is used in SOA checks for electromigration (`Ids`) and thermal limits (`Ids × Vds`).

### Capacitance Model for Dynamic SOA

#### Gate Tunneling Current (for Gate Oxide Reliability)
```
Igc = A × TOX^(-B) × exp(-C × TOX/|Vox|) × |Vox|^D
```
Where:
- `Vox = Vgs - Vfb` = oxide voltage
- Parameters `A, B, C, D` model Fowler-Nordheim or direct tunneling

#### Induced Gate Noise (for RF Reliability)
```
S_ig = 4 × k × T × δ × (ω² × Cgs²)/(5 × gd0) × Δf
```
Correlation with channel noise:
```
ρ = j × κ × (ω × Cgg/gd0)
```
Where:
- `κ = √(δ/(5 × γ))`
- `δ = n × (1 + β × Vds/Vdsat)`

### Temperature Scaling for Reliability Analysis

#### Mobility Temperature Dependence
```
μ(T) = μ(T_nom) × (T/T_nom)^(-UTE)
```

#### Threshold Voltage Temperature Shift
```
Vth(T) = Vth(T_nom) + (KT1 + KT1L/Leff) × (T/T_nom - 1)
        + KT2 × Vbs × (T/T_nom - 1)
```

#### Junction Breakdown Voltage Temperature Dependence
```
BV(T) = BV(T_nom) × [1 + α_BV × (T - T_nom)]
```
Where `α_BV` is positive for avalanche breakdown temperature coefficient.

### Geometry Scaling and Parameter Binning

#### Effective Dimensions for Current Density
```
Leff = L_drawn - 2 × DL + LLC/(L_drawn + LWL) + LWC/(L_drawn + LWW)
Weff = W_drawn × NF - 2 × DW + WLC/(W_drawn + WWL) + WWC/(W_drawn + WWW)
```

#### Binned Parameter Calculation for SOA Limits
```
P_eff = P + PL/Leff + PW/Weff + PLW/(Leff × Weff)
        + PNL × ln(Leff/L_nom) + PNW × ln(Weff/W_nom)
```
Applied to SOA parameters: `VDSMAX`, `J_max`, `P_max`, `HCI_limit`

## Convergence Analysis

### Newton-Raphson Convergence with SOA Constraints

The BSIM4v5 implementation must maintain numerical convergence while enforcing SOA limits, requiring careful mathematical formulation:

#### Voltage Convergence with SOA Clipping
```
|V_new - V_old| < RELTOL × max(|V_new|, |V_old|) + VNTOL
```
If SOA violation detected:
```
V_limited = V_old + sign(V_new - V_old) × min(|V_new - V_old|, ΔV_max)
```
Where `ΔV_max` prevents abrupt changes that could trigger SOA violations.

#### Current Convergence for Electromigration Checking
```
|I_new - I_old| < RELTOL × max(|I_new|, |I_old|) + ABSTOL
```
SOA-aware limiting:
```
if (I_new > I_max) I_new = I_old + (I_max - I_old) × α
```
Where `α = 0.5` provides smooth limiting.

#### SPICE Tolerance Hierarchy for SOA
- `ABSTOL = 1e-12` (current)
- `VNTOL = 1e-6` (voltage)
- `RELTOL = 0.001` (relative)
- `SOATOL = 0.1` (SOA warning threshold, 10% margin)

### Local Truncation Error with SOA Considerations

#### Charge-Based LTE Formulation
```
LTE = |h × dq/dt - (q_n - q_{n-1})|
```
SOA-modified time step control:
```
if (SOA_violation) h_new = 0.5 × h_old
else if (LTE > TOL) h_new = 0.8 × h_old
else if (LTE < TOL/10) h_new = 1.2 × h_old
```

#### SOA-Aware Integration
When approaching SOA limits, the integration becomes more conservative:
```
α = 1.0 - 0.5 × (SOA_margin/SOA_limit)  /* Backward Euler near limits */
I_cap = (Q_new - Q_old)/(α × Δt)
```

### Matrix Stamping with SOA Diode Elements

#### Extended Matrix for SOA Checking
The BSIM4v5 matrix stamp includes SOA diode elements between gate-drain and gate-source:
```
[Gdd + G_soa_gd    ...    -G_soa_gd     ... ] [Vd]   [Id]
[ ...              Ggg + G_soa_gd + G_soa_gs ... ] [Vg] = [Ig]
[-G_soa_gd         -G_soa_gs          ...     ... ] [Vs]   [Is]
```
Where:
- `G_soa_gd = ∂I_gd_soa/∂Vgd` (gate-drain SOA conductance)
- `G_soa_gs = ∂I_gs_soa/∂Vgs` (gate-source SOA conductance)

#### SOA Diode Characteristics
```
I_soa = I_s × [exp(V/V_t) - 1] × H(V - V_limit)
```
Where `H()` is a smooth Heaviside function for numerical continuity.

### Numerical Stability with SOA Enforcement

#### Gmin Stepping for SOA Convergence
```
Gmin = GMIN_START;
while (Gmin > GMIN_FINAL) {
    if (SOA_check(ckt) == VIOLATION) {
        Gmin = min(Gmin × 2, GMIN_MAX);
        continue;
    }
    solve_matrix(ckt);
    if (converged) Gmin = Gmin / 10;
}
```

#### Source-Drain Swap with SOA Preservation
```
if (vds < 0) {
    swap(&inst->BSIM4v5dNodePrime, &inst->BSIM4v5sNodePrime);
    swap(&inst->BSIM4v5rd, &inst->BSIM4v5rs);
    /* Preserve SOA limits during swap */
    swap(&inst->SOA_Vds_max, &inst->SOA_Vsd_max);
    vds = -vds;
}
```

### SOA Warning and Error Handling Mathematics

#### Margin Calculation
```
margin = (SOA_limit - actual_value) / SOA_limit
if (margin < WARNING_THRESHOLD) issue_warning();
if (margin < ERROR_THRESHOLD) issue_error();
```

#### Statistical SOA Tracking
```
μ_soa = (1 - α) × μ_soa + α × margin
σ_soa² = (1 - α) × σ_soa² + α × (margin - μ_soa)²
```
Where `α = 0.01` provides exponential averaging.

### Memory Lifecycle Mathematical Model

#### Instance Deletion Probability
```
P_delete = 1 - exp(-λ × t_sim)
```
Where:
- `λ = 1/mean_instance_lifetime`
- `t_sim` = simulation time

#### Memory Fragmentation Metric
```
fragmentation = 1 - (largest_free_block / total_free_memory)
```
BSIM4v5's linked list structure minimizes fragmentation.

### API Binding Mathematical Formulation

#### Function Pointer Table Optimization
The `SPICEdev` structure optimization minimizes lookup time:
```
T_lookup = T_base + n_params × T_param + n_funcs × T_func
```
Where BSIM4v5 has:
- `n_params ≈ 300` parameters
- `n_funcs = 28` function pointers
- Optimized hash table provides `O(1)` lookup

#### Parameter Validation Mathematics
```
if (|param_value - nominal| > 3 × σ_process) flag_warning();
if (param_value < min_physical || param_value > max_physical) flag_error();
```

### Convergence Acceleration with SOA

#### Damped Newton for SOA Violations
```
if (SOA_violation) {
    damping_factor = 0.5;
    Δx = damping_factor × J⁻¹ × F(x);
} else {
    damping_factor = 1.0;
}
```

#### Adaptive Tolerance for SOA Regions
```
if (near_SOA_limit) {
    RELTOL_effective = RELTOL / 10;
    ABSTOL_effective = ABSTOL / 100;
}
```

This comprehensive mathematical formulation ensures that BSIM4v5 simulations maintain numerical stability while accurately enforcing reliability constraints, with particular attention to the interaction between convergence algorithms and SOA checking mechanisms.

## C Implementation

### Core Data Structures for API Binding and SOA

The BSIM4v5 implementation uses specialized data structures that integrate with Ngspice's API while supporting SOA monitoring.

#### Model Structure (`sBSIM4model`)

```c
typedef struct sBSIM4model {
    int BSIM4type;                  /* NCH or PCH device type */
    
    /* Process parameters for SOA calculations */
    double BSIM4tox;                /* Gate oxide thickness */
    double BSIM4vth0;               /* Zero-bias threshold voltage */
    double BSIM4xj;                 /* Junction depth */
    double BSIM4nch;                /* Channel doping */
    
    /* SOA limit parameters */
    double BSIM4vgsmax;             /* Maximum gate-source voltage */
    double BSIM4vdsmax;             /* Maximum drain-source voltage */
    double BSIM4vdgmax;             /* Maximum gate-drain voltage */
    double BSIM4idsmax;             /* Maximum drain current */
    double BSIM4pdissmax;           /* Maximum power dissipation */
    double BSIM4vbsmax;             /* Maximum bulk-source voltage */
    
    /* Reliability model parameters */
    double BSIM4tbd;                /* Time-to-breakdown at reference field */
    double BSIM4alpha;              /* Voltage acceleration factor */
    double BSIM4jem;                /* Electromigration current density */
    double BSIM4ea;                 /* Activation energy for EM */
    double BSIM4rthja;              /* Junction-to-ambient thermal resistance */
    
    /* Linked list structure */
    struct sBSIM4model *BSIM4nextModel;
    BSIM4instance *BSIM4instances;
} BSIM4model;
```

#### Instance Structure (`sBSIM4instance`)

```c
typedef struct sBSIM4instance {
    /* Terminal nodes */
    int BSIM4dNode;                 /* Drain node */
    int BSIM4gNode;                 /* Gate node */
    int BSIM4sNode;                 /* Source node */
    int BSIM4bNode;                 /* Bulk node */
    
    /* Geometry parameters */
    double BSIM4l;                  /* Drawn length */
    double BSIM4w;                  /* Drawn width */
    double BSIM4sa;                 /* STI distance parameter A */
    double BSIM4sb;                 /* STI distance parameter B */
    double BSIM4sd;                 /* STI distance parameter D */
    
    /* Operating point variables */
    double BSIM4vgs;                /* Gate-source voltage */
    double BSIM4vds;                /* Drain-source voltage */
    double BSIM4vbs;                /* Bulk-source voltage */
    double BSIM4id;                 /* Drain current */
    double BSIM4pdiss;              /* Power dissipation */
    
    /* SOA violation flags */
    int BSIM4soaVgsViolation;       /* Gate overstress flag */
    int BSIM4soaVdsViolation;       /* Drain overstress flag */
    int BSIM4soaIdsViolation;       /* Current overstress flag */
    int BSIM4soaPdissViolation;     /* Thermal overstress flag */
    int BSIM4soaVbsViolation;       /* Bulk overstress flag */
    
    /* Cumulative stress for reliability */
    double BSIM4stressTime;         /* Cumulative stress time */
    double BSIM4vgsStress;          /* Vgs during stress */
    double BSIM4vdsStress;          /* Vds during stress */
    double BSIM4tempStress;         /* Temperature during stress */
    
    /* Matrix pointers */
    double *BSIM4drainDrainPtr;
    double *BSIM4gateGatePtr;
    double *BSIM4sourceSourcePtr;
    double *BSIM4bulkBulkPtr;
    /* ... additional cross-term pointers ... */
    
    struct sBSIM4instance *BSIM4nextInstance;
    BSIM4model *BSIM4modPtr;
} BSIM4instance;
```

### SPICEdev API Binding Implementation

The `BSIM4info` structure in `bsim4init.c` provides the complete interface between BSIM4v5 and the Ngspice kernel:

```c
SPICEdev BSIM4info = {
    .DEVpublic = {
        .name = "bsim4",
        .description = "BSIM4v5 Nanometer MOSFET Model",
        .terms = 4,
        .numNames = 4,
        .termNames = {"d", "g", "s", "b"},
        .numInstanceParms = 45,
        .instanceParms = BSIM4pTable,
        .numModelParms = 180,
        .modelParms = BSIM4mPTable,
        .flags = DEV_DEFAULT,
    },
    
    /* Core simulation functions */
    .DEVparam = BSIM4param,
    .DEVmodParam = BSIM4mParam,
    .DEVload = BSIM4load,
    .DEVsetup = BSIM4setup,
    .DEVunsetup = BSIM4unsetup,
    .DEVpzSetup = BSIM4setup,
    .DEVtemperature = BSIM4temp,
    .DEVtrunc = BSIM4trunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = BSIM4acLoad,
    .DEVaccept = NULL,
    .DEVdestroy = BSIM4destroy,
    .DEVmodDelete = BSIM4mDelete,
    .DEVdelete = BSIM4delete,
    .DEVsetic = BSIM4getic,
    .DEVask = BSIM4ask,
    .DEVmodAsk = BSIM4mAsk,
    .DEVpzLoad = BSIM4pzLoad,
    .DEVconvTest = BSIM4convTest,
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = NULL,
    .DEVnoise = BSIM4noise,
    
    /* SOA checking function */
    .DEVsoaCheck = BSIM4soaCheck,
    
    /* Memory size information */
    .DEVinstSize = sizeof(BSIM4instance),
    .DEVmodSize = sizeof(BSIM4model)
};
```

### Parameter Table Definitions

The parameter tables in `b4.c` define the complete set of BSIM4v5 parameters:

```c
/* Instance parameter table */
static IFparm BSIM4pTable[] = {
    IOP("l",        BSIM4_L,        IF_REAL, "Length"),
    IOP("w",        BSIM4_W,        IF_REAL, "Width"),
    IOP("sa",       BSIM4_SA,       IF_REAL, "STI distance parameter A"),
    IOP("sb",       BSIM4_SB,       IF_REAL, "STI distance parameter B"),
    IOP("sd",       BSIM4_SD,       IF_REAL, "STI distance parameter D"),
    IOP("nrs",      BSIM4_NRS,      IF_REAL, "Source squares"),
    IOP("nrd",      BSIM4_NRD,      IF_REAL, "Drain squares"),
    IOP("as",       BSIM4_AS,       IF_REAL, "Source area"),
    IOP("ad",       BSIM4_AD,       IF_REAL, "Drain area"),
    IOP("ps",       BSIM4_PS,       IF_REAL, "Source perimeter"),
    IOP("pd",       BSIM4_PD,       IF_REAL, "Drain perimeter"),
    IOPU("temp",    BSIM4_TEMP,     IF_REAL, "Instance temperature"),
    IOP("dtemp",    BSIM4_DTEMP,    IF_REAL, "Temperature difference"),
    IOP("m",        BSIM4_M,        IF_REAL, "Multiplier"),
    IP("off",       BSIM4_OFF,      IF_FLAG, "Device initially off"),
    IOP("icvds",    BSIM4_IC_VDS,   IF_REAL, "Initial VDS"),
    IOP("icvgs",    BSIM4_IC_VGS,   IF_REAL, "Initial VGS"),
    IOP("icvbs",    BSIM4_IC_VBS,   IF_REAL, "Initial VBS"),
    
    /* SOA monitoring parameters */
    IOP("vgsmax",   BSIM4_VGSMAX,   IF_REAL, "Maximum Vgs for SOA"),
    IOP("vdsmax",   BSIM4_VDSMAX,   IF_REAL, "Maximum Vds for SOA"),
    IOP("idsmax",   BSIM4_IDSMAX,   IF_REAL, "Maximum Ids for SOA"),
    IOP("pdissmax", BSIM4_PDISSMAX, IF_REAL, "Maximum power dissipation"),
    
    { NULL }
};

/* Model parameter table (partial) */
static IFparm BSIM4mPTable[] = {
    IOP("nmos",     BSIM4_TYPE,     IF_FLAG, "N-type MOSFET"),
    IOP("pmos",     BSIM4_TYPE,     IF_FLAG, "P-type MOSFET"),
    IOP("version",  BSIM4_VERSION,  IF_REAL, "Model version"),
    
    /* Core parameters */
    IOP("vth0",     BSIM4_VTH0,     IF_REAL, "Zero-bias threshold voltage"),
    IOP("tox",      BSIM4_TOX,      IF_REAL, "Gate oxide thickness"),
    IOP("xj",       BSIM4_XJ,       IF_REAL, "Junction depth"),
    IOP("nch",      BSIM4_NCH,      IF_REAL, "Channel doping"),
    
    /* Mobility parameters */
    IOP("u0",       BSIM4_U0,       IF_REAL, "Low-field mobility"),
    IOP("ua",       BSIM4_UA,       IF_REAL, "First-order mobility degradation"),
    IOP("ub",       BSIM4_UB,       IF_REAL, "Second-order mobility degradation"),
    
    /* SOA model parameters */
    IOP("tbd",      BSIM4_TBD,      IF_REAL, "Time-to-breakdown"),
    IOP("alpha",    BSIM4_ALPHA,    IF_REAL, "Voltage acceleration factor"),
    IOP("jem",      BSIM4_JEM,      IF_REAL, "Electromigration current density"),
    IOP("ea",       BSIM4_EA,       IF_REAL, "Activation energy"),
    IOP("rthja",    BSIM4_RTHJA,    IF_REAL, "Thermal resistance"),
    
    { NULL }
};
```

### Memory Lifecycle Management

#### Device Destruction (`b4dest.c`)

```c
void BSIM4destroy(GENmodel **inModel)
{
    BSIM4model **model = (BSIM4model **)inModel;
    BSIM4instance *here, *next;
    BSIM4model *mod, *nextmod;
    
    /* Traverse model list */
    for (mod = *model; mod != NULL; mod = nextmod) {
        nextmod = mod->BSIM4nextModel;
        
        /* Free all instances in this model */
        for (here = mod->BSIM4instances; here != NULL; here = next) {
            next = here->BSIM4nextInstance;
            
            /* Free dynamically allocated strings */
            if (here->BSIM4name) {
                FREE(here->BSIM4name);
            }
            
            /* Free instance structure */
            FREE(here);
        }
        
        /* Free model structure */
        FREE(mod);
    }
    
    *model = NULL;
}
```

#### Instance Deletion (`b4del.c`)

```c
int BSIM4delete(GENmodel *genmodel, IFuid name, GENinstance **inst)
{
    BSIM4model *model = (BSIM4model *)genmodel;
    BSIM4instance **fast = (BSIM4instance **)inst;
    BSIM4instance *prev = NULL;
    BSIM4instance *here;
    
    /* Search for instance in model's instance list */
    for (here = model->BSIM4instances; here != NULL; here = here->BSIM4nextInstance) {
        if (here->BSIM4name == name || 
            (here->BSIM4name && strcmp(here->BSIM4name, name) == 0)) {
            
            /* Found it - remove from linked list */
            if (prev == NULL) {
                model->BSIM4instances = here->BSIM4nextInstance;
            } else {
                prev->BSIM4nextInstance = here->BSIM4nextInstance;
            }
            
            /* Free instance resources */
            if (here->BSIM4name) {
                FREE(here->BSIM4name);
            }
            FREE(here);
            
            *fast = NULL;
            return OK;
        }
        prev = here;
    }
    
    return E_NODEV;  /* Instance not found */
}
```

#### Model Deletion (`b4mdel.c`)

```c
int BSIM4mDelete(GENmodel **genmodel, IFuid modname, GENmodel *killmodel)
{
    BSIM4model **model = (BSIM4model **)genmodel;
    BSIM4model *mod = *model;
    BSIM4model *prev = NULL;
    
    /* Search for model in linked list */
    while (mod != NULL) {
        if (mod->BSIM4modName == modname || mod == killmodel) {
            
            /* Found it - remove from linked list */
            if (prev == NULL) {
                *model = mod->BSIM4nextModel;
            } else {
                prev->BSIM4nextModel = mod->BSIM4nextModel;
            }
            
            /* First delete all instances in this model */
            BSIM4instance *inst = mod->BSIM4instances;
            while (inst != NULL) {
                BSIM4instance *next = inst->BSIM4nextInstance;
                if (inst->BSIM4name) {
                    FREE(inst->BSIM4name);
                }
                FREE(inst);
                inst = next;
            }
            
            /* Free model structure */
            FREE(mod);
            return OK;
        }
        prev = mod;
        mod = mod->BSIM4nextModel;
    }
    
    return E_NOMOD;  /* Model not found */
}
```

### Safe Operating Area (SOA) Checking Implementation (`b4soachk.c`)

```c
int BSIM4soaCheck(CKTcircuit *ckt, GENmodel *genmodel)
{
    BSIM4model *model = (BSIM4model *)genmodel;
    BSIM4instance *inst;
    int warningCount = 0;
    double vgs, vds, vbs, id, pdiss, temp;
    double vgsmax, vdsmax, idsmax, pdissmax, vbsmax;
    double vgd, vgdmax;
    
    for (; model != NULL; model = model->BSIM4nextModel) {
        for (inst = model->BSIM4instances; inst != NULL; 
             inst = inst->BSIM4nextInstance) {
            
            /* Get operating point */
            vgs = inst->BSIM4vgs;
            vds = inst->BSIM4vds;
            vbs = inst->BSIM4vbs;
            id = inst->BSIM4id;
            pdiss = fabs(vds * id);
            temp = ckt->CKTtemp + inst->BSIM4dtemp;
            
            /* Get SOA limits (instance-specific or model default) */
            vgsmax = (inst->BSIM4vgsmax > 0) ? inst->BSIM4vgsmax : model->BSIM4vgsmax;
            vdsmax = (inst->BSIM4vdsmax > 0) ? inst->BSIM4vdsmax : model->BSIM4vdsmax;
            idsmax = (inst->BSIM4idsmax > 0) ? inst->BSIM4idsmax : model->BSIM4idsmax;
            pdissmax = (inst->BSIM4pdissmax > 0) ? inst->BSIM4pdissmax : model->BSIM4pdissmax;
            vbsmax = (inst->BSIM4vbsmax > 0) ? inst->BSIM4vbsmax : model->BSIM4vbsmax;
            vgdmax = model->BSIM4vdgmax;
            vgd = vgs - vds;
            
            /* Check 1: Gate oxide overstress */
            if (fabs(vgs) > vgsmax) {
                inst->BSIM4soaVgsViolation++;
                if (warningCount < MAX_SOA_WARNINGS) {
                    soaPrint(ckt, "WARNING: Gate oxide overstress", 
                             inst->BSIM4name, "Vgs", vgs, vgsmax);
                }
                warningCount++;
            }
            
            /* Check 2: Drain junction breakdown */
            if (fabs(vds) > vdsmax) {
                inst->BSIM4soaVdsViolation++;
                if (warningCount < MAX_SOA_WARNINGS) {
                    soaPrint(ckt, "WARNING: Drain junction breakdown", 
                             inst->BSIM4name, "Vds", vds, vdsmax);
                }
                warningCount++;
            }
            
            /* Check 3: Gate-drain overstress */
            if (fabs(vgd) > vgdmax) {
                if (warningCount < MAX_SOA_WARNINGS) {
                    soaPrint(ckt, "WARNING: Gate-drain overstress", 
                             inst->BSIM4name, "Vgd", vgd, vgdmax);
                }
                warningCount++;
            }
            
            /* Check 4: Electromigration current limit */
            if (fabs(id) > idsmax) {
                inst->BSIM4soaIdsViolation++;
                if (warningCount < MAX_SOA_WARNINGS) {
                    soaPrint(ckt, "WARNING: Electromigration current limit", 
                             inst->BSIM4name, "Ids", id, idsmax);
                }
                warningCount++;
            }
            
            /* Check 5: Thermal overstress */
            if (pdiss > pdissmax) {
                inst->BSIM4soaPdissViolation++;
                if (warningCount < MAX_SOA_WARNINGS) {
                    soaPrint(ckt, "WARNING: Thermal overstress", 
                             inst->BSIM4name, "Pdiss", pdiss, pdissmax);
                }
                warningCount++;
            }
            
            /* Check 6: Bulk junction overstress */
            if (fabs(vbs) > vbsmax) {
                inst->BSIM4soaVbsViolation++;
                if (warningCount < MAX_SOA_WARNINGS) {
                    soaPrint(ckt, "WARNING: Bulk junction overstress", 
                             inst->BSIM4name, "Vbs", vbs, vbsmax);
                }
                warningCount++;
            }
            
            /* Update cumulative stress for reliability prediction */
            if (fabs(vgs) > 0.7 * vgsmax || fabs(vds) > 0.7 * vdsmax) {
                inst->BSIM4stressTime += ckt->CKTdelta;
                inst->BSIM4vgsStress = MAX(inst->BSIM4vgsStress, fabs(vgs));
                inst->BSIM4vdsStress = MAX(inst->BSIM4vdsStress, fabs(vds));
                inst->BSIM4tempStress = MAX(inst->BSIM4tempStress, temp);
            }
            
            /* Calculate time-to-failure based on cumulative stress */
            if (inst->BSIM4stressTime > 0) {
                double eox = fabs(vgs) / model->BSIM4tox;
                double ttf = model->BSIM4tbd * exp(-model->BSIM4alpha * eox);
                double af = inst->BSIM4stressTime / ttf;  /* Acceleration factor */
                
                if (af > 0.8 && warningCount < MAX_SOA_WARNINGS) {
                    soaPrint(ckt, "WARNING: Approaching oxide breakdown", 
                             inst->BSIM4name, "TTF", ttf, inst->BSIM4stressTime);
                    warningCount++;
                }
            }
        }
    }
    
    if (warningCount > 0) {
        ckt->CKTsoaViolations += warningCount;
        return E_SOA;  /* SOA violation detected */
    }
    
    return OK;
}
```

### Mathematical-to-Code Mapping for SOA Calculations

The C implementation directly maps to the mathematical SOA formulations:

#### Gate Oxide Breakdown Calculation:
```c
/* Mathematical: Vox_acc = VGS_MAX - α·Tox·ln(t_stress/τ_BD) */
/* C Implementation: */
double eox = fabs(vgs) / model->BSIM4tox;
double ttf = model->BSIM4tbd * exp(-model->BSIM4alpha * eox);
double af = inst->BSIM4stressTime / ttf;
```

#### Electromigration Current Limit:
```c
/* Mathematical: Ids_max = J_EM·A_metal·exp(-E_a/(k·T)) */
/* C Implementation: */
double idsmax_em = model->BSIM4jem * inst->BSIM4w * 1e-6 * 
                   exp(-model->BSIM4ea / (CONSTboltz * temp));
if (fabs(id) > idsmax_em