# MOS2: Parameter Parsing and Matrix Setup

_Generated 2026-04-12 04:49 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2ask.c`

# MOS2: Parameter Parsing and Matrix Setup

## Introduction

The Ngspice MOS2 (Level 2 MOSFET) implementation relies on a sophisticated parameter processing and matrix initialization system that bridges SPICE netlist specifications to executable simulation mathematics. This chapter details the mathematical transformations and convergence mechanisms implemented across four core files: `mos2defs.h` defines the data structures mapping SPICE parameters to C variables; `mos2init.c` implements the SPICE device API binding and state vector allocation; `mos2.c` (typically `mos2set.c`) performs parameter validation, geometry effect calculations, and matrix pointer allocation; and `mos2dest.c` handles memory cleanup. Together, these files transform user-provided model cards and instance parameters into a numerically stable formulation ready for Newton-Raphson iteration within the SPICE simulation framework.

## Mathematical Formulation

The mathematical formulation for MOS2 parameter processing and matrix setup directly implements the Grove-Frohman Level 2 model with geometry-dependent effects, ensuring the equations are properly conditioned for SPICE's numerical solvers.

### 1. Parameter Processing and Geometry-Dependent Transformations

**Effective Dimension Calculation:**
The drawn dimensions (L, W) from the SPICE netlist are transformed into effective electrical dimensions accounting for lateral diffusion:
```
L_eff = L - 2·LD
W_eff = W - 2·WD
```
where LD and WD are model parameters for drain and source lateral diffusion. Numerical protection enforces:
```
L_eff = max(L_eff, 1e-12)
W_eff = max(W_eff, 1e-12)
```
This prevents division by zero in subsequent conductance calculations.

**Transconductance Coefficient (β):**
The SPICE parameter KP is combined with geometry to form the transconductance coefficient:
```
β = KP · (W_eff / L_eff)
```
In the C implementation, this becomes `inst->MOS2beta = model->MOS2kp * inst->MOS2wEff / inst->MOS2lEff`.

**Oxide Capacitance Calculation:**
The oxide capacitance per unit area is derived from physical constants and the TOX parameter:
```
C_ox = ε_ox / TOX = (3.9 · 8.854e-12) / TOX
```
This is computed during setup as `model->MOS2oxideCapFactor` for use in capacitance and charge calculations.

### 2. Threshold Voltage with Short-Channel and Narrow-Width Effects

The MOS2 model extends the basic Shichman-Hodges formulation with geometry-dependent corrections critical for accurate deep-submicron simulation.

**Base Threshold Voltage with Body Effect:**
```
V_th_base = VTO + γ · [√(φ - V_bs) - √φ]
```
where γ is the body-effect coefficient (GAMMA) and φ is the surface potential (PHI).

**Short-Channel Effect Correction (ΔV_th_short):**
```
ΔV_th_short = γ · [√(φ - V_bs + ψ) - √(φ + ψ)]
```
with
```
ψ = (ε_si · X_j · C_ox) / (2 · ε_ox) · [1 - √(1 + (2 · W_s / X_j))]
```
and
```
W_s = √[(2 · ε_si / (q · N_sub)) · (φ - V_bs)]
```
where X_j is the junction depth, N_sub is the substrate doping, and ε_si is the silicon permittivity.

**Narrow-Width Effect Correction (ΔV_th_narrow):**
```
ΔV_th_narrow = δ · (π · ε_si) / (2 · C_ox · W_eff) · (φ - V_bs)
```
where δ is the narrow-width coefficient (DELTA).

**Complete Threshold Voltage:**
```
V_th = V_th_base + ΔV_th_short + ΔV_th_narrow
```
This formulation ensures the threshold voltage accurately models modern MOSFET geometries where these effects are significant.

### 3. Conductance Matrix Formulation for Newton-Raphson

The DC and transient analysis in SPICE requires constructing a conductance matrix (Jacobian) for the Newton-Raphson solver. For the 4-terminal MOS2 device (including internal nodes for RD/RS), this becomes a 6×6 matrix.

**Intrinsic MOSFET Stamp (4-terminal):**
The small-signal conductances computed from the drain current derivatives form the core matrix:
```
G[d'][d'] = g_ds
G[d'][g]  = -g_m
G[d'][s'] = -(g_ds + g_m + g_mbs)
G[d'][b]  = -g_mbs

G[s'][d'] = -g_ds
G[s'][g]  = g_m
G[s'][s'] = g_ds + g_m + g_mbs
G[s'][b]  = g_mbs

G[b][d']  = -g_mbs
G[b][s']  = g_mbs
G[b][b]   = g_bd + g_bs + g_mbs
```
where:
- `g_m = ∂I_d/∂V_gs` (transconductance)
- `g_ds = ∂I_d/∂V_ds` (output conductance)
- `g_mbs = ∂I_d/∂V_bs` (body transconductance)
- `g_bd = ∂I_bd/∂V_bd` (bulk-drain conductance)
- `g_bs = ∂I_bs/∂V_bs` (bulk-source conductance)

**Parasitic Resistance Stamping:**
When RD > 0 or RS > 0, internal nodes d' and s' are created, and the conductance matrix expands to 6×6:
```
G[D][D] = 1/RD
G[D][d'] = -1/RD
G[d'][D] = -1/RD
G[d'][d'] += 1/RD  (added to intrinsic value)

G[S][S] = 1/RS
G[S][s'] = -1/RS
G[s'][S] = -1/RS
G[s'][s'] += 1/RS  (added to intrinsic value)
```

**Right-Hand Side (RHS) Current Vector:**
The Newton-Raphson formulation also requires a current vector:
```
I[d'] = -I_d
I[s'] = I_d
I[b] = I_bd + I_bs
```
where I_d is the drain current and I_bd, I_bs are the junction diode currents.

### 4. State Vector Allocation for Charge Conservation

The charge-conservative formulation requires five state variables for numerical integration:
```
q_gs(t) = ∫ i_gs(τ) dτ  (gate-source charge)
q_gd(t) = ∫ i_gd(τ) dτ  (gate-drain charge)
q_gb(t) = ∫ i_gb(τ) dτ  (gate-bulk charge)
q_bd(t) = ∫ i_bd(τ) dτ  (bulk-drain charge)
q_bs(t) = ∫ i_bs(τ) dτ  (bulk-source charge)
```
These are allocated in the global state vector with indices `MOS2stateGgs`, `MOS2stateGgd`, etc., enabling the trapezoidal integration method:
```
q[n+1] = q[n] + (h/2) · (i[n] + i[n+1])
```
where h is the time step.

### 5. Temperature Scaling Equations

SPICE simulations often require temperature sweeps, necessitating parameter scaling:

**Threshold Voltage Temperature Dependence:**
```
VTO(T) = VTO(T_nom) - α_VTO · (T - T_nom)
```
where α_VTO is the temperature coefficient of threshold voltage.

**Mobility Temperature Scaling:**
```
μ(T) = μ_0 · (T/T_nom)^{-1.5}
```
This accounts for phonon scattering effects.

**Junction Potential Temperature Dependence:**
```
PB(T) = PB(T_nom) · (T/T_nom) - 2·V_t·ln(T/T_nom) + E_g·(1 - T_nom/T)
```
where V_t = kT/q is the thermal voltage and E_g is the temperature-dependent silicon bandgap:
```
E_g(T) = 1.16 - 7.02e-4 · T²/(T + 1108)
```

**Saturation Current Temperature Scaling:**
```
IS(T) = IS(T_nom) · exp[(E_g/(N·V_t)) · (T - T_nom)/(T·T_nom)] · (T/T_nom)^{XTI/N}
```
where XTI is the saturation current temperature exponent (typically 3.0).

## C Implementation

### 1. Parameter Binding and Setup Logic

The MOS2 model's parameter parsing and matrix setup are orchestrated by the `MOS2setup()` function, typically found in a file like `mos2set.c`. This function bridges the mathematical model parameters defined in SPICE netlists to the internal C data structures and prepares the device for simulation by allocating matrix entries and state vector slots.

#### 1.1 Parameter Tables and Mapping
The mathematical parameters (VTO, KP, GAMMA, etc.) from a `.MODEL` statement are mapped to internal C structure fields via parameter tables defined in files like `mos2mpar.c` and `mos2mask.c`.

```c
/* Example parameter mapping indices (mos2mpar.c) */
#define MOS2_VTO   101
#define MOS2_KP    102
#define MOS2_GAMMA 103
#define MOS2_PHI   104
#define MOS2_LAMBDA 105
#define MOS2_RD    106
#define MOS2_RS    107
/* ... additional parameters ... */
```

These indices are used in a `IFparm` structure array (`MOS2mPTable` for model parameters, `MOS2pTable` for instance parameters) that defines the mapping between SPICE parameter names, their internal indices, data types, and description strings. This table-driven approach allows the simulator's parser to directly assign netlist values to the correct fields in the `MOS2model` and `MOS2instance` structs.

#### 1.2 Core Setup Algorithm (`MOS2setup`)
The `MOS2setup()` function performs the critical one-time initialization for the device. Its primary responsibilities, mapped directly from the mathematical formulation, are:

1.  **Temperature Scaling of Model Parameters:** Applies the temperature-dependent formulas to adjust parameters like `VTO`, `KP`, and `IS` from their nominal (`TNOM`) values to the current simulation temperature.
2.  **Calculation of Effective Dimensions:** Computes `L_eff` and `W_eff` by subtracting lateral diffusion (`LD`, `WD`) from the drawn dimensions, enforcing a numerical minimum (e.g., 1e-12 meters).
3.  **Pre-calculation of Derived Parameters:** Computes frequently used values like `beta` (β = `KP * W_eff / L_eff`) and oxide capacitance factor (`Cox = ε_ox / TOX`) to avoid redundant calculations during the load phase.
4.  **Sparse Matrix Pointer Allocation:** Allocates entries in the circuit's Jacobian matrix for the device's conductance and capacitance contributions.
5.  **State Vector Allocation:** Reserves slots in the simulator's state vector array for the device's internal state variables (charges).

```c
int MOS2setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS2model *model = (MOS2model *)inModel;
    MOS2instance *inst;
    double T, TNOM, Vt, Vtnom;

    for(; model; model = model->MOS2nextModel) {
        /* TEMPERATURE SCALING: Maps math T_scaling formulas to code */
        T = ckt->CKTtemp + CONSTCtoK;
        TNOM = model->MOS2tnom + CONSTCtoK;
        Vt = KoverQ * T;
        Vtnom = KoverQ * TNOM;

        if(T != TNOM) {
            /* φ(T) = φ(T_nom) * (T/T_nom) - 2V_t * ln(T/T_nom) + E_g(T) * (1 - T_nom/T) */
            model->MOS2phi = model->MOS2phi * T/TNOM - 2*Vt*log(T/TNOM) + EG*(1 - TNOM/T);
            /* VTO(T) adjustment due to φ change */
            model->MOS2vt0 = model->MOS2vt0 - model->MOS2gamma*(sqrt(model->MOS2phi) - sqrt(PHI_T));
            /* KP(T) = KP(T_nom) * (T/T_nom)^(-1.5) */
            model->MOS2kp = model->MOS2kp * pow(T/TNOM, -1.5);
            /* IS(T) = IS(T_nom) * exp( (E_g/(N*V_t)) * (T-T_nom)/(T*T_nom) ) */
            model->MOS2is = model->MOS2is * exp(EG/(N*Vt)*(T-TNOM)/(T*TNOM));
        }

        for(inst = model->MOS2instances; inst; inst = inst->MOS2nextInstance) {
            /* GEOMETRY PROCESSING: L_eff = L - 2*LD, W_eff = W - 2*WD */
            inst->MOS2lEff = inst->MOS2l - 2*model->MOS2ld;
            inst->MOS2wEff = inst->MOS2w - 2*model->MOS2wd;
            /* Numerical guard: enforce minimum dimensions */
            if(inst->MOS2lEff < 1e-12) inst->MOS2lEff = 1e-12;
            if(inst->MOS2wEff < 1e-12) inst->MOS2wEff = 1e-12;

            /* DERIVED PARAMETER: β = (W_eff/L_eff) * KP */
            inst->MOS2beta = model->MOS2kp * inst->MOS2wEff / inst->MOS2lEff;

            /* MATRIX ALLOCATION: Allocate 16 pointers for the 4x4 conductance matrix */
            inst->MOS2drainDrainPtr = SMPmakeElt(matrix, inst->MOS2dNodePrime, inst->MOS2dNodePrime);
            inst->MOS2drainGatePtr = SMPmakeElt(matrix, inst->MOS2dNodePrime, inst->MOS2gNode);
            inst->MOS2drainSourcePtr = SMPmakeElt(matrix, inst->MOS2dNodePrime, inst->MOS2sNodePrime);
            inst->MOS2drainBulkPtr = SMPmakeElt(matrix, inst->MOS2dNodePrime, inst->MOS2bNode);
            /* ... allocate all 16 matrix element pointers ... */

            /* STATE VECTOR ALLOCATION: Reserve indices for 5 charges (q_gs, q_gd, q_gb, q_bd, q_bs) */
            inst->MOS2states[0] = (*states)++;  /* q_gs */
            inst->MOS2states[1] = (*states)++;  /* q_gd */
            inst->MOS2states[2] = (*states)++;  /* q_gb */
            inst->MOS2states[3] = (*states)++;  /* q_bd */
            inst->MOS2states[4] = (*states)++;  /* q_bs */

            /* Initialize state vector entries to zero */
            ckt->CKTstate0[inst->MOS2states[0]] = 0.0;
            /* ... initialize other states ... */
        }
    }
    return OK;
}
```

### 2. Sparse Matrix Allocation Pattern

The SPICE simulator uses a sparse matrix system to solve the nodal equations efficiently. Each device must stamp its contributions into this global matrix. The MOS2 model, being a 4-terminal device (D, G, S, B), requires a 4x4 conductance/capacitance block.

#### 2.1 Matrix Pointer Structure
The `MOS2instance` struct contains 16 double pointers (e.g., `MOS2drainDrainPtr`, `MOS2drainGatePtr`) that point to specific locations in the sparse matrix. These pointers are obtained via `SMPmakeElt()` during setup. The mathematical conductance matrix `G` and its mapping to C pointers is:

```
G = [ Gdd  Gdg  Gds  Gdb ]    where: Gdd = *MOS2drainDrainPtr
    [ Ggd  Ggg  Ggs  Ggb ]           Gdg = *MOS2drainGatePtr
    [ Gsd  Ssg  Gss  Gsb ]           ...
    [ Gbd  Bbg  Gbs  Gbb ]
```

#### 2.2 Allocation for Internal Nodes (RD, RS)
A key aspect of the setup is handling parasitic resistances `RD` and `RS`. The mathematical model introduces internal nodes `d'` and `s'`. The code creates these nodes and allocates additional matrix pointers for the conductance stamps between external and internal nodes.

```c
/* In MOS2setup(), if RD > 0 */
if(model->MOS2rd > 0.0) {
    inst->MOS2dNodePrime = ckt->CKTnumStates++; // Create internal node
    /* Allocate pointers for the 2x2 RD conductance block */
    inst->MOS2dDrainPtr = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2dNode);       // G[D][D]
    inst->MOS2dDrainPrimePtr2 = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2dNodePrime); // G[D][d']
    inst->MOS2dPrimeDrainPtr = SMPmakeElt(matrix, inst->MOS2dNodePrime, inst->MOS2dNode); // G[d'][D]
    // G[d'][d'] is part of the intrinsic 4x4 block (MOS2drainDrainPtr)
} else {
    inst->MOS2dNodePrime = inst->MOS2dNode; // No internal node needed
}
```
This creates the topology: `D -- RD -- d' -- (Intrinsic MOSFET) -- s' -- RS -- S`. The matrix stamp for `RD` implemented later in the load function will be:
```
[ 1/RD  -1/RD ] [V_D]   = [I_D]
[ -1/RD  1/RD ] [V_d']    [I_d']
```
This is a direct C implementation of the mathematical conductance relationship.

### 3. State Vector Management

For transient analysis, the simulator must track the time evolution of state variables. For the MOS2 model, these are the five charges: `q_gs`, `q_gd`, `q_gb`, `q_bd`, `q_bs`.

#### 3.1 State Allocation
During `MOS2setup()`, indices into the global state vector array `ckt->CKTstate0[]` are allocated and stored in `inst->MOS2states[]`. The simulator manages multiple time points (e.g., current `CKTstate0`, previous `CKTstate1`). The offset for previous states is `ckt->CKTnumStates`.

```c
/* Allocate and initialize states */
inst->MOS2states[0] = (*states)++; // Index for q_gs at time t
ckt->CKTstate0[inst->MOS2states[0]] = 0.0; // Initialize current charge
ckt->CKTstate1[inst->MOS2states[0]] = 0.0; // Initialize charge at t-Δt
```
This scheme allows the transient analysis algorithms (like trapezoidal integration) to access `q(t)` and `q(t-Δt)` as `ckt->CKTstate0[index]` and `ckt->CKTstate1[index]`.

#### 3.2 State Update Logic
During the load phase (`MOS2load()`), after computing the new charges based on voltages, the state vector is updated. The integration for Local Truncation Error (LTE) control uses these stored values.

```c
/* Simplified state update logic */
double q_gs_new = calculateGateSourceCharge(inst, vgs, vds, vbs);
double q_gs_old = ckt->CKTstate0[inst->MOS2states[0]];
/* Store for next iteration */
ckt->CKTstate1[inst->MOS2states[0]] = q_gs_old;
/* Update current state */
ckt->CKTstate0[inst->MOS2states[0]] = q_gs_new;
```

### 4. SPICE Device API Integration (`MOS2info`)

The MOS2 model is integrated into Ngspice through the `SPICEdev` structure, which acts as a function table defining the device's interface to the simulator core. This structure is defined in the initialization file (e.g., `mos2init.c`).

```c
SPICEdev MOS2info = {
    .DEVpublic = {
        .name = "mos2",
        .description = "Level 2 MOSFET model (Grove-Frohman)",
        .terms = 4,
        .termNames = {"d", "g", "s", "b"},
        .numInstanceParms = 15, // L, W, AD, AS, PD, PS, NRD, NRS, M, TEMP, DTEMP, OFF, IC_VDS, IC_VGS, IC_VBS
        .numModelParms = 30, // VTO, KP, GAMMA, PHI, LAMBDA, RD, RS, CBD, CBS, IS, PB, CGSO, CGDO, CGBO, RSH, CJ, MJ, CJSW, MJSW, JS, TOX, LD, WD, U0, FC, TNOM, NSUB, NFS, VMAX, XJ
        .flags = DEV_DEFAULT,
    },
    .DEVmodParam = MOS2mPTable,  // Pointer to model parameter table
    .DEVinstParam = MOS2pTable,  // Pointer to instance parameter table
    .DEVload = MOS2load,         // DC/Transient load function
    .DEVsetup = MOS2setup,       // Setup function described above
    .DEVunsetup = MOS2unsetup,   // Cleanup function
    .DEVtemperature = MOS2temp,  // Temperature update function
    .DEVtrunc = MOS2trunc,       // Local Truncation Error calculation
    .DEVacLoad = MOS2acLoad,     // AC small-signal load
    .DEVconvTest = MOS2convTest, // Convergence test
    .DEVnoise = MOS2noise,       // Noise analysis
    .DEVinstSize = sizeof(MOS2instance),
    .DEVmodSize = sizeof(MOS2model),
};
```

This `MOS2info` structure is registered with the simulator. When the parser encounters a `M` (MOSFET) device with `LEVEL=2`, it uses this table to:
1.  Parse instance and model parameters using `MOS2pTable` and `MOS2mPTable`.
2.  Call `MOS2setup()` during circuit setup.
3.  Call `MOS2load()` repeatedly during Newton-Raphson iterations for DC/transient analysis.
4.  Call `MOS2acLoad()` for AC analysis.
5.  Call `MOS2temp()` for temperature scaling.
6.  Call `MOS2trunc()` for adaptive time-step control in transient analysis.

### 5. Memory Management and Cleanup

Complementary to the setup is the destruction logic, typically in a file like `mos2dest.c`. This ensures proper cleanup of allocated memory when the circuit is destroyed or the device is removed.

```c
void MOS2destroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    MOS2model *model = (MOS2model*)mod;
    MOS2instance *inst;

    while(model) {
        MOS2model *nextModel = model->MOS2nextModel;
        inst = model->MOS2instances;
        while(inst) {
            MOS2instance *nextInst = inst->MOS2nextInstance;
            /* Free instance name string */
            if(inst->MOS2name) FREE(inst->MOS2name);
            /* Free any other allocated memory (e.g., sensitivity data) */
            FREE(inst);
            inst = nextInst;
        }
        FREE(model);
        model = nextModel;
    }
    *inModel = NULL;
}
```

The `MOS2unsetup()` function would handle the release of matrix pointers and state vector indices, working in tandem with the simulator's matrix management system.

This C implementation provides the foundational infrastructure that allows the mathematical Grove-Frohman Level 2 equations to be integrated into the SPICE simulation flow, handling parameter management, memory allocation, and interface registration.