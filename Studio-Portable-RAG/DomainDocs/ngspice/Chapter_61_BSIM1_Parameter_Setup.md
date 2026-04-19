# BSIM1: Parameter Parsing and Matrix Setup

_Generated 2026-04-12 10:40 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim1/b1ask.c`

# Chapter: BSIM1: Parameter Parsing and Matrix Setup

## Introduction

This chapter details the foundational Ngspice C implementation that transforms BSIM1 MOSFET model specifications from a SPICE netlist into a numerically robust data structure ready for circuit simulation. The core files `b1set.c`, `b1mpar.c`, `b1mask.c`, and `b1ask.c` constitute the parameter parsing and matrix setup subsystem. `b1set.c` contains the `BSIM1setup()` function, which orchestrates geometric parameter processing, allocates the sparse matrix pointers for the 6-node device representation, and initializes the state vector for charge conservation. `b1mpar.c` and `b1mask.c` define the parameter binding tables and unique integer masks that map textual SPICE parameters (e.g., `vfb0`, `phi0`, `l`, `w`) to specific fields within the `sBSIM1model` and `sBSIM1instance` C structures. `b1ask.c` implements the query interface, allowing simulation results and internal parameters to be retrieved post-analysis. Together, these files perform the critical translation from a user's netlist description to the initialized mathematical state required by Ngspice's Newton-Raphson solver, enforcing physical constraints, applying defaults, and establishing the matrix topology for efficient numerical solution.

---

## Mathematical Formulation

The BSIM1 model implementation in Ngspice translates empirical MOSFET physics into a form suitable for SPICE's Modified Nodal Analysis (MNA) framework. The mathematical formulation for parameter processing and matrix setup establishes the foundation for all subsequent circuit simulations.

### 1. Parameter Mapping and Validation Mathematics

#### 1.1 Parameter Table Mapping Function
The SPICE parameter system uses a bijective mapping between textual parameter names and internal integer codes:

```
P: SPICE parameter space → M: Internal model space
P(name, value, type) ↦ M(code, storage_location, validation_rules)
```

For BSIM1, this mapping is defined by the parameter tables in `b1mpar.c`:

```
BSIM1mPTable = {(nameᵢ, codeᵢ, typeᵢ, descriptionᵢ)} for i = 1...Nₘ
BSIM1pTable = {(nameⱼ, codeⱼ, typeⱼ, descriptionⱼ)} for j = 1...Nᵢ
```

Where:
- `Nₘ ≈ 60` model parameters (VFB0, PHI0, K1, K2, ETA0, U0, TOX, etc.)
- `Nᵢ ≈ 12` instance parameters (L, W, AD, AS, PD, PS, NRD, NRS, etc.)
- `type ∈ {IF_REAL, IF_FLAG, IF_REALVEC}` determines parsing and storage rules

#### 1.2 Default Value Assignment Logic
When parameters are not specified in the SPICE netlist, the setup algorithm applies default values using conditional logic:

```
For each parameter p in model/instance:
    if !p.Given then
        p.value = f_default(p.code)
    end if
```

Critical defaults for BSIM1 include:
- `VFB0 = -1.0` (flatband voltage)
- `PHI0 = 0.7` (surface potential in volts)
- `K1 = 0.5` (body effect coefficient)
- `L = 100e-6`, `W = 100e-6` (default dimensions in meters)
- `AD = AS = 0.0` (zero diffusion area by default)

#### 1.3 Geometric Parameter Processing
The setup phase computes effective device dimensions accounting for process variations:

```
L_eff = L_drawn - 2·LD - ΔL
W_eff = W_drawn - 2·WD - ΔW
```

Where:
- `LD, WD` are lateral diffusion lengths from model parameters
- `ΔL, ΔW` are additional length/width reductions
- Constraint: `L_eff > 0` and `W_eff > 0` (enforced with `max(L_eff, 1e-12)`)

The series resistances are calculated using sheet resistance:
```
R_d = RSH · NRD
R_s = RSH · NRS
```

Where `RSH` is the model's sheet resistance parameter, and `NRD, NRS` are the number of squares for drain and source diffusion.

#### 1.4 Derived Parameter Calculations
Key derived parameters computed during setup:

**Oxide Capacitance:**
```
C_ox = ε₀·ε_ox / t_ox = (8.854e-12 · 3.9) / TOX
```

**Built-in Potential:**
```
V_bi = type · φ₀
```
Where `type = +1` for NMOS, `-1` for PMOS.

**Reference Dimensions:**
```
L_eff_ref = L - 2·LD
W_eff_ref = W - 2·WD
```
These reference values are stored in the model structure for parameter binning interpolation.

### 2. Sparse Matrix Allocation Mathematics

#### 2.1 Node Indexing Scheme
BSIM1 uses a 6-node representation for the 4-terminal MOSFET:

```
Node indices: {0:D, 1:G, 2:S, 3:B, 4:D', 5:S'}
```

Where:
- `D, G, S, B` are external terminal nodes
- `D', S'` are internal nodes after series resistances `R_d, R_s`

#### 2.2 Matrix Sparsity Pattern
The conductance matrix `G` for DC analysis has a predefined sparsity pattern determined by device topology:

```
G = 
⎡ g_dd    g_dg    0      g_db    g_dd'    0    ⎤
⎢ g_gd    g_gg    g_gs   g_gb    g_gd'    g_gs' ⎥
⎢ 0       g_sg    g_ss   g_sb    0       g_ss'  ⎥
⎢ g_bd    g_bg    g_bs   g_bb    g_bd'    g_bs' ⎥
⎢ g_d'd   g_d'g   0      g_d'b   g_d'd'   g_d's'⎥
⎣ 0       g_s'g   g_s's  g_s'b   g_s'd'   g_s's'⎦
```

This pattern reflects the device connectivity:
- Drain (`D`) connects to Gate, Bulk, and internal Drain (`D'`)
- Source (`S`) connects to Gate, Bulk, and internal Source (`S'`)
- Internal nodes `D'` and `S'` connect to each other through channel conductance
- No direct `D-S` connection (current flows through `D'-S'`)

#### 2.3 SMP Pointer Allocation Algorithm
The `SMPmakeElt()` function creates matrix elements only for non-zero positions, following the sparsity pattern:

```
For each (i,j) in sparsity_pattern:
    ptr[i,j] = SMPmakeElt(matrix, node_i, node_j)
    if symmetric and i ≠ j:
        ptr[j,i] = ptr[i,j]  (matrix symmetry)
```

The allocation creates 36 pointers for the 6×6 system, but only ~20 are unique due to symmetry.

#### 2.4 State Vector Allocation Mathematics
BSIM1 tracks 7 state variables per instance for charge conservation:

```
State vector indices: {q_gs, q_gd, q_gb, q_bd, q_bs, v_bd, v_bs}
```

The allocation algorithm:
```
For each instance i:
    For state variable s in [0..6]:
        state_index[i,s] = global_state_counter
        global_state_counter++
        CKTstate0[state_index[i,s]] = 0.0  (initialization)
```

This creates a contiguous block of state entries in the circuit's global state vector, enabling efficient access during transient analysis.

### 3. Parameter Validation and Boundary Mathematics

#### 3.1 Physical Limit Enforcement
The setup code enforces physical constraints:

**Positive Dimensions:**
```
L_eff = max(L - 2·LD, L_min) where L_min = 1e-12
W_eff = max(W - 2·WD, W_min) where W_min = 1e-12
```

**Oxide Thickness:**
```
t_ox = max(TOX, t_ox_min) where t_ox_min ≈ 1e-10
```

#### 3.2 Temperature Parameter Processing
Temperature-dependent parameters are scaled during setup:

```
T_abs = T_user + 273.15  (Celsius to Kelvin)
T_ratio = T_abs / T_nom

μ_0(T) = μ_0 · (T_ratio)^{-BEX}
V_th(T) = V_th0 - TCV · (T_abs - T_nom)
C_ox(T) = C_ox / (1 + TCOX · (T_abs - T_nom))
```

#### 3.3 Model-Instance Hierarchy Mathematics
The linked list structure creates a hierarchy:

```
Model_list: M₁ → M₂ → ... → Mₙ → NULL
For each Mᵢ:
    Instance_list: I₁ → I₂ → ... → Iₘ → NULL
```

Parameter inheritance follows:
```
For parameter p:
    if I.p_given then use I.p_value
    else if M.p_given then use M.p_value
    else use default_value(p)
```

## Convergence Analysis

### 1. Matrix Conditioning for Newton-Raphson Convergence

#### 1.1 Diagonal Dominance Enforcement
The BSIM1 matrix setup ensures diagonal dominance through strategic placement of conductances:

```
G[d',d'] = g_ds + g_m + g_mb + 1/R_d + GMIN
G[s',s'] = g_ds + g_m + g_mb + 1/R_s + GMIN
```

Where `GMIN = 1e-12` is SPICE's minimum conductance added to all diagonal elements to prevent singular matrices.

#### 1.2 Symmetry and Reciprocity
The allocated matrix pattern enforces physical reciprocity:

```
g[i,j] = g[j,i] for all i,j
```

This symmetry improves NR convergence by ensuring the Jacobian matrix is symmetric positive definite for passive devices.

#### 1.3 Condition Number Analysis
The matrix condition number `κ(G)` affects convergence rate:

```
κ(G) = ‖G‖·‖G⁻¹‖
```

BSIM1 improves conditioning by:
1. Scaling conductances to similar magnitudes
2. Adding `GMIN` to diagonals
3. Using proper units (Siemens for conductances)

### 2. Parameter Continuity for NR Convergence

#### 2.1 Smooth Default Transitions
Default value assignment ensures continuous parameter spaces:

```
p_value = if p_given then user_value else default_value
```

No discontinuities occur when parameters transition from unspecified to specified.

#### 2.2 Geometric Continuity
The effective dimension calculations are continuous functions:

```
L_eff(L) = max(L - 2·LD, L_min)
```

This `max()` function is continuous and has a continuous first derivative at `L = 2·LD + L_min`.

#### 2.3 Temperature Scaling Continuity
Temperature scaling functions are smooth:

```
μ(T) = μ₀ · (T/T_nom)^{-α}
```
This power law is continuous and differentiable for `T > 0`.

### 3. State Vector Initialization for Transient Convergence

#### 3.1 Zero Initial State
All charge states initialize to zero:

```
q_gs(0) = q_gd(0) = q_gb(0) = q_bd(0) = q_bs(0) = 0
v_bd(0) = v_bs(0) = 0
```

This provides a consistent starting point for transient analysis.

#### 3.2 State Index Contiguity
Contiguous state allocation:

```
state[i] = base_index + i
```

ensures efficient memory access and improves cache performance during NR iterations.

### 4. Sparsity Pattern Optimization for Solver Convergence

#### 4.1 Optimal Fill-in Reduction
The 6-node topology minimizes fill-in during LU factorization:

```
Non-zero count = 20 (of 36 possible)
Fill-in ratio = 20/36 ≈ 56%
```

This sparse structure reduces computational complexity from O(n³) to approximately O(n¹.⁵).

#### 4.2 Pointer Allocation Efficiency
The SMP pointer allocation:

```
ptr = SMPmakeElt(matrix, row, col)
```

creates elements only where needed, avoiding storage of zero elements that could introduce numerical noise.

### 5. Convergence Criteria for Setup Phase

#### 5.1 Parameter Validation Success
Setup converges successfully when:

1. All required parameters have valid values
2. Physical constraints are satisfied (L_eff > 0, W_eff > 0)
3. Matrix allocation succeeds for all instances
4. State vector allocation within circuit limits

#### 5.2 Error Conditions
Setup fails if:

1. Memory allocation fails for matrix pointers
2. State vector exceeds circuit capacity
3. Physical impossibility (e.g., L_eff ≤ 0 after correction)
4. Parameter value out of valid range

### 6. Numerical Stability Analysis

#### 6.1 Dimension Scaling Stability
The algorithm handles extreme dimensions robustly:

```
For L → 0: L_eff → L_min = 1e-12
For W → 0: W_eff → W_min = 1e-12
```

Prevents division by zero in subsequent `W_eff/L_eff` calculations.

#### 6.2 Resistance Calculation Stability
Series resistance calculation:

```
R = RSH · N
```

Handles `RSH → 0` by resulting in `R → 0`, not division by zero.

#### 6.3 Matrix Element Magnitude Balancing
The setup ensures matrix elements have reasonable magnitudes:

```
Diagonal elements: ~1/R or ~g_m (typically 1e-6 to 1)
Off-diagonal elements: ≤ diagonal elements
```

This balancing improves iterative solver convergence.

### 7. PMOS/NMOS Symmetry for Convergence

#### 7.1 Polarity Handling
The setup treats PMOS and NMOS symmetrically:

```
For PMOS: type = -1, all voltage polarities inverted
For NMOS: type = +1, normal polarities
```

This symmetry ensures similar convergence properties for both device types.

#### 7.2 Matrix Pattern Consistency
Identical sparsity pattern for both polarities:

```
G_PMOS[i,j] = -G_NMOS[i,j] for transconductances
G_PMOS[i,i] = G_NMOS[i,i] for diagonal elements
```

Maintains matrix properties (diagonal dominance, symmetry) for both types.

### 8. Integration with SPICE Convergence Framework

#### 8.1 Return Code Protocol
The setup function follows SPICE convergence protocol:

```
Return OK: Setup successful, ready for simulation
Return E_NOMEM: Memory allocation failed
Return E_BADPARM: Invalid parameter value
Return E_PANIC: Unrecoverable error
```

#### 8.2 State Management Integration
State vector integration with SPICE's transient engine:

```
CKTstate0[index] = initial_value
CKTstate1[index] = previous_time_step_value
```

Proper setup enables SPICE's convergence tests on state variables.

This mathematical formulation and convergence analysis demonstrates how BSIM1's parameter parsing and matrix setup creates a numerically robust foundation for SPICE circuit simulation, ensuring Newton-Raphson convergence through careful matrix conditioning, parameter continuity, and proper initialization.

---

## C Implementation

### 1. Core Data Structures for SPICE Integration

#### 1.1 Model Parameter Structure (`sBSIM1model`)

The `sBSIM1model` structure in `bsim1def.h` serves as the container for all process-level parameters required by the BSIM1 mathematical model. Each field directly corresponds to a parameter in the BSIM1 equations:

```c
/* Mathematical mapping to C structure fields */
BSIM1vfb0 → Vfb0 (Flatband voltage at Vbs=0)
BSIM1phi0 → φ0 (Surface potential)
BSIM1k1 → K1 (Body effect coefficient)
BSIM1k2 → K2 (Depletion charge coefficient)
BSIM1eta0 → η0 (Zero-bias DIBL coefficient)
BSIM1etaB → ηb (Body bias coefficient for DIBL)
BSIM1etaD → ηd (Drain bias coefficient for DIBL)
BSIM1u0 → μ0 (Low-field mobility)
BSIM1u1 → θ1 (First-order mobility degradation)
BSIM1u2 → θ2 (Second-order mobility degradation)
BSIM1u3 → θ3 (Body effect on mobility)
BSIM1u4 → θ4 (Width effect on mobility)
```

The structure implements a linked list architecture where `BSIM1nextModel` points to the next model definition, allowing multiple BSIM1 models with different parameter sets in the same circuit. The `BSIM1instances` pointer maintains the list of device instances using this model.

#### 1.2 Instance State Structure (`sBSIM1instance`)

The `sBSIM1instance` structure manages the runtime state of individual MOSFET devices. It contains three critical categories of data:

**Node Indices for SPICE Matrix Integration:**
```c
BSIM1dNode, BSIM1gNode, BSIM1sNode, BSIM1bNode → External terminal nodes
BSIM1dNodePrime, BSIM1sNodePrime → Internal nodes after series resistances
```

**Electrical State Variables (Mathematical Mapping):**
```c
BSIM1vds, BSIM1vgs, BSIM1vbs → Terminal voltages (Vds, Vgs, Vbs)
BSIM1id → Drain current Id
BSIM1gm → ∂Id/∂Vgs (transconductance)
BSIM1gds → ∂Id/∂Vds (output conductance)
BSIM1gmb → ∂Id/∂Vbs (bulk transconductance)
BSIM1cgs, BSIM1cgd, BSIM1cgb → Capacitances
```

**Sparse Matrix Pointers (SMP):**
36 double pointers that reference specific locations in Ngspice's sparse matrix system, enabling direct modification of matrix elements during the load phase.

### 2. Parameter Binding and Parsing System

#### 2.1 Parameter Table Architecture

The parameter binding system in `b1mpar.c` uses static tables to map SPICE deck parameter names to internal C structure fields:

```c
/* Model Parameter Table - Maps .MODEL card parameters */
static IFparm BSIM1mPTable[] = {
    IOP("vfb0",    BSIM1_VFB0,   IF_REAL, "Flatband voltage at Vbs=0"),
    IOP("phi0",    BSIM1_PHI0,   IF_REAL, "Surface potential"),
    /* ... 50+ additional parameters ... */
};

/* Instance Parameter Table - Maps device instance parameters */
static IFparm BSIM1pTable[] = {
    IOP("l",       BSIM1_L,      IF_REAL, "Channel length"),
    IOP("w",       BSIM1_W,      IF_REAL, "Channel width"),
    /* ... additional instance parameters ... */
};
```

The `IOP` macro defines the mapping: parameter name, mask value, data type, and description. This table-driven approach allows Ngspice's parser to dynamically bind SPICE deck parameters to the appropriate C structure fields without hardcoded string comparisons.

#### 2.2 Mask-Based Parameter Identification

The `b1mask.c` file defines unique integer masks for each parameter:

```c
#define BSIM1_VFB0     101
#define BSIM1_PHI0     102
#define BSIM1_K1       103
/* ... 100+ additional masks ... */
```

These masks serve as efficient identifiers during parameter parsing. When Ngspice encounters a parameter in the SPICE deck, it uses the mask value to determine which field in the `sBSIM1model` or `sBSIM1instance` structure to update, avoiding expensive string operations during simulation.

#### 2.3 Given Flag System

Each parameter in the model structure has an associated `Given` flag bit:

```c
unsigned BSIM1vfb0Given :1;
unsigned BSIM1phi0Given :1;
unsigned BSIM1k1Given :1;
/* ... additional 50+ flag bits ... */
```

This system tracks whether a parameter was explicitly specified in the SPICE deck or should use its default value. During `BSIM1setup()`, these flags are checked:

```c
if(!model->BSIM1vfb0Given)   model->BSIM1vfb0 = -1.0;  /* Apply default */
if(!model->BSIM1phi0Given)   model->BSIM1phi0 = 0.7;   /* Apply default */
```

### 3. Geometric Parameter Processing and Validation

#### 3.1 Effective Dimension Calculation

The `BSIM1setup()` function in `b1set.c` implements the geometric transformations from drawn dimensions to effective electrical dimensions:

```c
/* Mathematical implementation in C */
inst->BSIM1leff = inst->BSIM1l - 2.0 * model->BSIM1ld;  /* Leff = L - 2·LD */
inst->BSIM1weff = inst->BSIM1w - 2.0 * model->BSIM1wd;  /* Weff = W - 2·WD */

/* Protection against non-positive dimensions */
if(inst->BSIM1leff <= 0.0) inst->BSIM1leff = 1e-12;
if(inst->BSIM1weff <= 0.0) inst->BSIM1weff = 1e-12;
```

These effective dimensions (`BSIM1leff`, `BSIM1weff`) are used throughout the BSIM1 mathematical model in equations such as:

```
Id = (W_eff/L_eff)·μ_eff·Cox·[(Vgs - Vth)·Vds - (1/2)·Vds²]·(1 + λ·Vds)
```

#### 3.2 Series Resistance Calculation

The implementation calculates parasitic resistances based on layout parameters:

```c
inst->BSIM1rd = model->BSIM1rsh * inst->BSIM1nrd;  /* Rd = RSH · NRD */
inst->BSIM1rs = model->BSIM1rsh * inst->BSIM1nrs;  /* Rs = RSH · NRS */
```

These resistances create the internal nodes D' and S' that appear in the 6×6 matrix formulation, separating the external terminals from the intrinsic MOSFET channel.

### 4. Sparse Matrix Pointer Allocation

#### 4.1 6×6 Matrix Structure Allocation

The `BSIM1setup()` function allocates SMP pointers for all 36 elements of the 6×6 conductance matrix:

```c
/* External diagonal elements (4 nodes) */
inst->BSIM1DdPtr = SMPmakeElt(matrix, inst->BSIM1dNode, inst->BSIM1dNode);
inst->BSIM1GgPtr = SMPmakeElt(matrix, inst->BSIM1gNode, inst->BSIM1gNode);
inst->BSIM1SsPtr = SMPmakeElt(matrix, inst->BSIM1sNode, inst->BSIM1sNode);
inst->BSIM1BbPtr = SMPmakeElt(matrix, inst->BSIM1bNode, inst->BSIM1bNode);

/* Internal diagonal elements (2 nodes) */
inst->BSIM1DPdPtr = SMPmakeElt(matrix, inst->BSIM1dNodePrime, inst->BSIM1dNodePrime);
inst->BSIM1SPsPtr = SMPmakeElt(matrix, inst->BSIM1sNodePrime, inst->BSIM1sNodePrime);

/* Cross-coupling elements (30 pointers) */
inst->BSIM1DgPtr = SMPmakeElt(matrix, inst->BSIM1dNode, inst->BSIM1gNode);
inst->BSIM1DsPtr = SMPmakeElt(matrix, inst->BSIM1dNode, inst->BSIM1sNode);
/* ... additional 28 cross-coupling allocations ... */
```

This allocation pattern corresponds directly to the mathematical matrix structure:

```
[G_dd   G_dg   G_ds   G_db   G_dd'  G_ds']
[G_gd   G_gg   G_gs   G_gb   G_gd'  G_gs']
[G_sd   G_sg   G_ss   G_sb   G_sd'  G_ss']
[G_bd   G_bg   G_bs   G_bb   G_bd'  G_bs']
[G_d'd  G_d'g  G_d's  G_d'b  G_d'd' G_d's']
[G_s'd  G_s'g  G_s's  G_s'b  G_s'd' G_s's']
```

#### 4.2 State Vector Allocation for Charge Conservation

The implementation allocates state vector entries for charge storage, essential for transient analysis:

```c
/* Allocate 7 state entries per instance */
for(int i = 0; i < 7; i++) {
    inst->BSIM1states[i] = *states;
    (*states)++;
}

/* Initialize charge states to zero */
ckt->CKTstate0[inst->BSIM1states[0]] = 0.0;  /* qgs */
ckt->CKTstate0[inst->BSIM1states[1]] = 0.0;  /* qgd */
ckt->CKTstate0[inst->BSIM1states[2]] = 0.0;  /* qgb */
ckt->CKTstate0[inst->BSIM1states[3]] = 0.0;  /* qbd */
ckt->CKTstate0[inst->BSIM1states[4]] = 0.0;  /* qbs */
ckt->CKTstate0[inst->BSIM1states[5]] = 0.0;  /* vbd */
ckt->CKTstate0[inst->BSIM1states[6]] = 0.0;  /* vbs */
```

These state indices enable the BSIM1 model to participate in Ngspice's numerical integration for transient analysis, storing charge values between time steps.

### 5. Derived Parameter Calculations

#### 5.1 Oxide Capacitance Calculation

During setup, the implementation calculates the oxide capacitance per unit area:

```c
Cox = 3.9 * 8.854e-12 / model->BSIM1tox;  /* ε_ox/tox */
```

This derived parameter `Cox` appears in multiple BSIM1 equations, including the drain current calculation:

```
Id = (W_eff/L_eff)·μ_eff·Cox·[(Vgs - Vth)·Vds - (1/2)·Vds²]·(1 + λ·Vds)
```

#### 5.2 Built-in Potential Calculation

The setup function computes the built-in potential for junction calculations:

```c
Vbi = model->BSIM1type * model->BSIM1phi0;
```

The `BSIM1type` field (+1 for NMOS, -1 for PMOS) handles polarity inversion, ensuring the mathematical model correctly processes both device types.

### 6. Integration with Ngspice's Simulation Framework

#### 6.1 Circuit Integration Points

The `BSIM1setup()` function returns the `OK` status code to Ngspice, indicating successful initialization. The function signature follows Ngspice's device API:

```c
int BSIM1setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
```

Parameters:
- `matrix`: Ngspice's sparse matrix system
- `inModel`: Generic model pointer (cast to BSIM1model)
- `ckt`: Circuit context containing simulation state
- `states`: Pointer to state counter for charge storage allocation

#### 6.2 Default Value Processing

The implementation provides robust default handling for unspecified parameters:

```c
/* Model parameter defaults */
if(!model->BSIM1vfb0Given)   model->BSIM1vfb0 = -1.0;
if(!model->BSIM1phi0Given)   model->BSIM1phi0 = 0.7;
if(!model->BSIM1k1Given)     model->BSIM1k1 = 0.5;

/* Instance parameter defaults */
if(!inst->BSIM1lGiven)   inst->BSIM1l = 100e-6;
if(!inst->BSIM1wGiven)   inst->BSIM1w = 100e-6;
if(!inst->BSIM1adGiven)  inst->BSIM1ad = 0.0;
```

These defaults ensure the model remains numerically stable even with incomplete parameter specifications.

### 7. Mathematical Consistency Enforcement

#### 7.1 Dimension Validation

The C implementation enforces physical constraints on geometric parameters:

```c
if(inst->BSIM1leff <= 0.0) inst->BSIM1leff = 1e-12;
if(inst->BSIM1weff <= 0.0) inst->BSIM1weff = 1e-12;
```

This prevents division by zero in equations like `Id ∝ W_eff/L_eff` and maintains numerical stability during Newton-Raphson iterations.

#### 7.2 Matrix Symmetry Preparation

By allocating all 36 matrix pointers (including symmetric pairs), the implementation prepares for the stamping of a symmetric conductance matrix. During the load phase, conductances will be stamped into both `G_ij` and `G_ji` positions to maintain matrix symmetry, as required by Ngspice's modified nodal analysis formulation.

### 8. Temperature Scaling Initialization

Although detailed temperature scaling occurs in `b1temp.c`, the setup function initializes temperature-related parameters:

```c
/* Store instance temperature for later scaling */
inst->BSIM1temp = model->BSIM1temp;  /* Default to model temperature */
if(inst->BSIM1dtempGiven) {
    inst->BSIM1temp += inst->BSIM1dtemp;  /* Apply instance delta */
}
```

This initialization ensures that when `BSIM1temp()` is called during simulation, it has the correct baseline temperature for scaling calculations like:

```
μ_eff(T) = μ0 · (T/TNOM)^(-bex)
Vth(T) = Vfb0 + φ0 - tcv·(T - TNOM)
```

### 9. Linked List Traversal Architecture

The implementation uses linked list traversal to process all models and instances:

```c
for(; model; model = model->BSIM1nextModel) {
    /* Process model-level parameters */
    for(inst = model->BSIM1instances; inst; inst = inst->BSIM1nextInstance) {
        /* Process each instance */
    }
}
```

This architecture allows multiple BSIM1 models with different parameter sets and multiple device instances per model, all processed within a single setup call.

### 10. Error Handling and Robustness

The implementation includes several robustness features:

1. **Null pointer checks**: The function assumes valid input pointers from Ngspice
2. **Dimension sanitization**: Prevents non-positive effective dimensions
3. **Default value fallbacks**: Provides reasonable defaults for unspecified parameters
4. **State allocation tracking**: Properly increments the state counter for each instance

This C implementation establishes the complete infrastructure for BSIM1 simulation in Ngspice, transforming SPICE deck parameters into initialized data structures ready for the load phase where the actual mathematical evaluation and matrix stamping occur.