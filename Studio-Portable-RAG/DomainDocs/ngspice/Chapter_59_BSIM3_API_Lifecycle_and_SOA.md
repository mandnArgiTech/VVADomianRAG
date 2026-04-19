# BSIM3: API Binding, Memory Lifecycle, and Safe Operating Area

_Generated 2026-04-12 10:18 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/bsim3init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3dest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3del.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3mdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3soachk.c`

# **BSIM3: API Binding, Memory Lifecycle, and Safe Operating Area**

## **Introduction**

This chapter details the system-level integration of the BSIM3 deep-submicron MOSFET model within the Ngspice simulation framework, focusing on the software architecture that enables robust, production-ready circuit simulation. The implementation spans six critical C source files that handle device registration, dynamic memory management, and physical reliability enforcement.

*   **`bsim3init.c` (Device Registration & API Binding)**: This file defines the `BSIM3info` structure of type `SPICEdev`, which serves as the formal contract between the BSIM3 device model and the Ngspice kernel. It populates a table of function pointers (e.g., `DEVload`, `DEVsetup`, `DEVsoaCheck`) that the simulator calls to perform specific operations. The `BSIM3init()` function registers this structure, making the "bsim3" device available in the SPICE netlist.

*   **`b3.c` (Core Device Functions)**: This file contains the primary computational routines for the BSIM3 model. Functions like `BSIM3load()` evaluate the core DC and transient equations (drain current, charges, conductances), while `BSIM3acLoad()` constructs the small-signal admittance matrix for AC analysis. It operates directly on the `B3model` and `B3instance` data structures defined in `bsim3def.h`.

*   **`b3dest.c`, `b3del.c`, `b3mdel.c` (Memory Lifecycle Management)**: These files implement a robust memory management system based on linked lists. `b3dest.c` provides the master `BSIM3destroy()` function for tearing down an entire device hierarchy. `b3del.c` and `b3mdel.c` implement targeted deletion of individual instances and models, respectively, ensuring proper cleanup of allocated strings and structures while maintaining list integrity. This prevents memory leaks during long simulation sessions or iterative netlist modifications.

*   **`b3soachk.c` (Safe Operating Area Verification)**: This file implements the `BSIM3soaCheck()` function, a critical reliability feature. It audits every device instance at checkpoints during simulation (e.g., after a solved DC point) against six physical limits: gate oxide breakdown, junction avalanche breakdown, hot-carrier injection, punch-through, maximum drain current, and maximum power dissipation. It issues warnings to the user when biases approach or exceed these physically destructive boundaries, translating device physics into actionable simulation feedback.

Together, these modules exemplify the industrial-strength design of Ngspice's device modeling interface. They ensure the BSIM3 model is not just a collection of mathematical equations but a well-behaved software component that integrates cleanly with the solver kernel, manages its resources responsibly, and safeguards against the simulation of physically impossible or destructive operating conditions.

---

## **Mathematical Formulation**

This section details the mathematical models and constraints implemented in Ngspice's BSIM3 device for API binding, memory management, and Safe Operating Area (SOA) analysis. All formulations are explicitly tied to SPICE's simulation framework, where they govern device registration, parameter validation, and physical reliability limits.

### **1. Device Registration and Parameter Binding Mathematics**

The BSIM3 device integrates with the Ngspice kernel through a formal API defined by the `SPICEdev` structure. This binding involves mathematical mappings between SPICE netlist parameters, internal C variables, and simulation algorithms.

#### **1.1 Parameter Table Mapping**

The device uses parameter tables (`BSIM3mPTable` for models, `BSIM3pTable` for instances) that define a bijective mapping between SPICE input names and internal C structure fields. For each parameter `P`, the mapping is:

```
SPICE_name(P) ↔ model->B3P or inst->B3P
```

Where the transformation includes:
- **Unit conversion**: SPICE parameters in MKS units (meters, seconds, amps) are converted to internal simulation units (µm, ps, mA) via scaling factors `U_scale`.
- **Default value application**: If parameter is unspecified, apply `P_default = f(P_type, P_min, P_max)`.
- **Bound checking**: Ensure `P_min ≤ P ≤ P_max` where bounds are defined by physical limits (e.g., `tox > 0`, `L > 0`).

#### **1.2 Instance-Model Hierarchy Mathematics**

The BSIM3 implementation uses a linked list structure with mathematical relationships:

```
Model List: M1 → M2 → ... → Mn
Instance List per Model: I1 → I2 → ... → Im
```

Each instance inherits parameters from its parent model with geometry scaling:
```
inst->B3vth = model->B3vth0 + ΔV_th(inst->B3l, inst->B3w)
inst->B3u0 = model->B3u0 * f_u(inst->B3l, inst->B3w)
```

The inheritance follows the SPICE rule: instance parameters override model defaults, with validation:
```
if (inst->B3lGiven) use inst->B3l else use model->B3l
if (inst->B3wGiven) use inst->B3w else use model->B3w
```

#### **1.3 State Vector Allocation Mathematics**

During `BSIM3setup()`, the device requests state vector entries for charge storage. The allocation follows:

```
num_states = 5 (for Qgs, Qgd, Qgb, Qbd, Qbs) + 2 (for historical derivatives)
state_index = *states; (*states) += num_states
```

The state vector `CKTstate` stores charge history for numerical integration:
```
Q_n     = CKTstate[state_index]
Q_{n-1} = CKTstate[state_index + size]
Q_{n-2} = CKTstate[state_index + 2*size]
```

Where `size = ckt->CKTnumStates` is the total number of state variables in the circuit.

### **2. Safe Operating Area (SOA) Mathematical Constraints**

The BSIM3 SOA checks enforce physical limits to prevent device damage during simulation. Each constraint is derived from semiconductor physics and device geometry.

#### **2.1 Gate Oxide Breakdown Limit**

The electric field across the gate oxide must remain below the critical field for SiO₂:

```
E_ox = |V_ox| / t_ox ≤ E_crit ≈ 6×10⁸ V/m
```

Where:
- `V_ox = V_gs` or `V_gd` (gate-to-channel voltage)
- `t_ox = model->B3tox` (oxide thickness)
- `E_crit` is the dielectric breakdown field (~6 MV/cm for SiO₂)

The maximum allowable gate voltage is:
```
V_gs,max = V_gd,max = E_crit * t_ox
```

In the SOA check:
```
if (|V_gs| > E_crit * model->B3tox) → WARNING: Oxide breakdown risk
```

#### **2.2 Junction Breakdown Voltage Limit**

The reverse-bias pn-junction voltage must remain below the avalanche breakdown voltage:

```
|V_BD| ≤ BV_max
|V_BS| ≤ BV_max
```

Where `BV_max` is the junction breakdown voltage parameter. For silicon pn-junctions, the breakdown voltage can be approximated by:

```
BV_max ≈ (ε_si * E_crit²) / (2 * q * N_a)  (for abrupt junctions)
```

Where:
- `ε_si = 11.7 * ε_0` (silicon permittivity)
- `E_crit ≈ 3×10⁵ V/cm` (critical field for avalanche)
- `q` = electron charge
- `N_a` = substrate doping concentration

#### **2.3 Hot Carrier Injection (HCI) Limit**

Hot carrier injection occurs when the lateral electric field in the channel exceeds the critical value for carrier heating. The lateral field is estimated as:

```
E_max ≈ (V_DS - V_DS,sat) / L_eff
```

Where:
- `V_DS,sat = (V_GS - V_th) / (1 + κ)` (saturation voltage)
- `L_eff = inst->B3leff` (effective channel length)
- `κ = model->B3kappa` (saturation field factor)

The saturation field (where velocity saturates) is:
```
E_sat = v_sat / μ_eff
```

Where:
- `v_sat = model->B3vsat` (saturation velocity, ~1×10⁵ m/s for electrons)
- `μ_eff = inst->B3u0temp` (temperature-adjusted mobility)

The HCI safety criterion is:
```
E_max ≤ α * E_sat
```
Typically `α ≈ 10` for conservative design.

#### **2.4 Punch-Through Voltage Limit**

Punch-through occurs when the drain depletion region extends to the source at high `V_DS`. The punch-through voltage is approximated by:

```
V_DS,pt = (q * N_a * X_j²) / (2 * ε_si) * (1 / L_eff²) * V_th
```

Where:
- `X_j = model->B3xj` (junction depth)
- `N_a` = substrate doping (derived from `model->B3nsub`)
- `V_th = inst->B3vth` (threshold voltage)

A simplified form used in the code is:
```
V_DS,pt = 0.5 * X_j² * V_th / L_eff²
```

The safety check is:
```
if (V_DS > V_DS,pt) → WARNING: Punch-through risk
```

#### **2.5 Maximum Current Limit**

The drain current must remain below the thermal destruction limit:

```
|I_DS| ≤ I_max
```

Where `I_max` is determined by the maximum allowable temperature rise:
```
I_max = √(P_max / R_DS(on))
```

Or from electromigration limits in interconnects:
```
I_max = J_max * A_metal
```

Where:
- `J_max` = maximum current density (~1 MA/cm² for Al, ~10 MA/cm² for Cu)
- `A_metal` = cross-sectional area of drain/source contacts

#### **2.6 Power Dissipation Limit**

The instantaneous power dissipation must remain below the maximum rating:

```
P = |I_DS * V_DS| ≤ P_max
```

Where `P_max` is determined by thermal resistance and maximum junction temperature:
```
P_max = (T_j,max - T_a) / R_θJA
```

With:
- `T_j,max` = maximum junction temperature (typically 150°C for silicon)
- `T_a` = ambient temperature
- `R_θJA` = junction-to-ambient thermal resistance

### **3. Memory Lifecycle Mathematical Model**

The BSIM3 memory management follows a reference-counted linked list model with specific allocation patterns.

#### **3.1 Memory Allocation Pattern**

For `n` models and `m_i` instances per model, the total memory allocation is:

```
Total memory = n * sizeof(B3model) + Σ_{i=1}^{n} m_i * sizeof(B3instance)
```

Where typical sizes are:
- `sizeof(B3model) ≈ 300 parameters * 8 bytes ≈ 2400 bytes`
- `sizeof(B3instance) ≈ 150 parameters * 8 bytes + pointers ≈ 1500 bytes`

The SMP matrix pointers allocation follows:
```
num_pointers = 36 (for 6×6 matrix with D, D', G, S, S', B nodes)
memory_per_pointer = 8 bytes (on 64-bit system)
```

#### **3.2 Linked List Traversal Complexity**

Operations on the model-instance hierarchy have time complexity:

- **Search for instance**: `O(n * m)` worst case
- **Deletion of model**: `O(m)` to free all instances
- **SOA check on all devices**: `O(Σ m_i)`

The traversal algorithm for SOA checking is:
```
for each model in model_list:
    for each instance in model->instance_list:
        apply_soa_checks(instance)
```

## **Convergence Analysis**

This section analyzes the numerical properties of the BSIM3 API binding, memory management, and SOA implementation, focusing on their stability and compatibility with SPICE's simulation framework.

### **1. Parameter Binding and Validation Stability**

The BSIM3 parameter system must ensure numerical stability across the entire parameter space while maintaining physical realism.

#### **1.1 Parameter Range Enforcement**

The parameter validation in `BSIM3check()` ensures all parameters remain within physically meaningful bounds:

*   **Positive-Definite Constraints**: Parameters like `tox`, `L`, `W` must be strictly positive: `tox ≥ ε_machine`. This prevents division by zero in equations like `C_ox = ε_ox / tox`.
*   **Bounded Parameters**: Mobility `u0` is clamped to `[u0_min, u0_max]` where typical bounds are `[100, 1000] cm²/V·s` for electrons. This prevents unrealistic velocity saturation calculations.
*   **Threshold Voltage Sign Consistency**: For `model->B3type = N_TYPE`, `vth0` should be positive; for `P_TYPE`, negative. The check `if (vth0 * type > 0)` issues a warning but doesn't fail, allowing intentional depletion-mode devices.

**Convergence Impact**: Invalid parameters (e.g., `tox = 0`) would cause singularities in the oxide capacitance calculation `C_ox = ε_ox / tox`, leading to infinite capacitance values and an ill-conditioned circuit matrix `Y(ω) = G + jωC`. The validation prevents such numerical instabilities.

#### **1.2 Geometry Scaling and Binning Continuity**

The geometry-dependent parameter binning uses interpolation formulas:

```
P_eff = P_nom + P_L/L_eff + P_W/W_eff + P_LW/(L_eff·W_eff)
```

The derivatives with respect to `L_eff` and `W_eff` are:
```
∂P_eff/∂L_eff = -P_L/L_eff² - P_LW/(L_eff²·W_eff)
∂P_eff/∂W_eff = -P_W/W_eff² - P_LW/(L_eff·W_eff²)
```

**Convergence Impact**: These derivatives must be continuous at bin boundaries to ensure smooth transitions in device characteristics. Discontinuities in `∂P/∂L` would cause jumps in `∂I_DS/∂L`, potentially disrupting Newton-Raphson convergence when simulating circuits with varying device sizes.

#### **1.3 Temperature Scaling Smoothness**

Temperature-dependent parameters use smooth scaling functions:

```
P(T) = P(T_nom) * (T/T_nom)^α
```

The derivative with respect to temperature is:
```
∂P/∂T = α * P(T_nom) * T^{α-1} / T_nom^α
```

For parameters like mobility where `α = -UTE` (typically -1.5 to -2.0), this derivative is continuous for `T > 0`.

**Convergence Impact**: During temperature sweeps or self-heating simulation, discontinuous temperature derivatives would cause convergence problems in the coupled thermal-electrical solution.

### **2. Safe Operating Area Check Integration with Newton-Raphson**

The SOA checks interact with the Newton-Raphson solver in non-trivial ways that affect convergence.

#### **2.1 SOA as Inequality Constraints**

Each SOA limit defines an inequality constraint:
```
g_i(x) ≤ 0, i = 1,...,6
```
Where `x = [V_GS, V_DS, V_BS, I_DS]^T` is the device state vector.

The constraints are:
1. `|V_GS| - V_GS,max ≤ 0`
2. `|V_GD| - V_GD,max ≤ 0`
3. `|V_BD| - BV_max ≤ 0`
4. `|V_BS| - BV_max ≤ 0`
5. `(V_DS - V_DS,sat)/L_eff - α·E_sat ≤ 0`
6. `|I_DS·V_DS| - P_max ≤ 0`

#### **2.2 Constraint Enforcement Strategy**

The BSIM3 implementation uses a *warning* rather than *enforcement* strategy for SOA violations. This design choice has convergence implications:

*   **No Active Limiting**: Unlike `DEVfetlim()` which actively limits voltages for convergence, SOA checks only issue warnings. This means the Newton-Raphson solver can push the device into physically unrealistic regions.
*   **Numerical Stability**: If the solver enters a region where `V_GS > V_GS,max`, the gate oxide breakdown model isn't activated, so the device equations remain well-behaved numerically. This prevents convergence failures but may produce non-physical results.
*   **Warning Thresholds**: The SOA warnings use conservative thresholds (e.g., `E_max > 10·E_sat` for HCI) to provide design margin while avoiding false positives during normal operation.

#### **2.3 Jacobian Considerations Near SOA Boundaries**

Near SOA boundaries, the device equations remain smooth, ensuring the Jacobian matrix is well-defined. For example, near oxide breakdown:

*   The gate current model (if implemented) would have an exponential dependence: `I_G ∝ exp(E_ox/E_crit)`
*   The derivative `∂I_G/∂V_GS ∝ (1/E_crit·t_ox)·exp(E_ox/E_crit)` becomes very large but remains finite
*   This could cause ill-conditioning of the circuit matrix but doesn't create singularities

**Convergence Impact**: The absence of hard SOA enforcement means convergence is not directly affected by SOA boundaries. However, if the circuit operates deep in the SOA violation region, the underlying device equations may become stiff, requiring smaller time steps in transient analysis.

### **3. Memory Lifecycle and State Management Convergence**

The dynamic memory allocation and state vector management have subtle effects on numerical consistency.

#### **3.1 State Vector Persistence Across Time Steps**

The charge states stored in `CKTstate` must persist correctly across rejected time steps. The algorithm is:

```
if (LTE > tolerance):
    reject_step()
    restore_state(CKTstate_old)
    reduce_time_step()
else:
    accept_step()
    CKTstate_old = CKTstate_current
```

**Convergence Impact**: If state restoration is incorrect (e.g., due to memory corruption), the device will have inconsistent charge history, causing LTE calculation errors and potentially unstable time-step control.

#### **3.2 Linked List Integrity During Simulation**

The model-instance linked lists must remain intact during simulation. Deletion operations (if supported during simulation) require careful synchronization:

```
delete_instance(inst):
    lock_memory()
    prev->next = inst->next
    free(inst->name)
    free(inst)
    unlock_memory()
```

**Convergence Impact**: Memory corruption or dangling pointers would cause undefined behavior in device evaluation, leading to random convergence failures. The BSIM3 implementation typically prohibits structural changes during simulation to avoid this issue.

#### **3.3 SMP Matrix Pointer Consistency**

The SMP matrix pointers allocated in `BSIM3setup()` must remain valid throughout simulation. The pointers reference locations in the global circuit matrix:

```
inst->B3drainDrainPtr = &(ckt->CKTmatrix[inst->B3dNode, inst->B3dNode])
```

**Convergence Impact**: If matrix reallocation occurs (due to added devices or modified topology), these pointers become invalid. Ngspice typically prohibits matrix structure changes after setup to maintain pointer validity, ensuring convergence stability.

### **4. API Binding and Error Handling Robustness**

The device API must handle error conditions gracefully without disrupting convergence.

#### **4.1 Error Propagation Model**

When the BSIM3 device encounters an error (e.g., SOA violation), it returns an error code to the SPICE kernel:

```
if (soa_violation):
    return E_SOA
else:
    return OK
```

The kernel then decides whether to continue, issue a warning, or abort. This layered error handling prevents device-level errors from crashing the entire simulation.

#### **4.2 Parameter Query Consistency**

The `BSIM3ask()` function provides parameter values to the kernel and user. The mathematical consistency requirement is:

```
value_returned = f(parameters_current, state_current)
```

Where `f` must be the same function used internally for simulation. Inconsistency would cause confusion but doesn't affect convergence directly.

#### **4.3 Temperature Update Continuity**

The `BSIM3temp()` function updates temperature-dependent parameters. The update must be smooth in temperature:

```
ΔP/ΔT ≈ ∂P/∂T (continuous)
```

Discontinuous temperature updates between iterations would disrupt convergence in coupled thermal-electrical simulations.

### **5. Integration with SPICE's Adaptive Algorithms**

The BSIM3 implementation must work correctly with SPICE's adaptive time-step and Newton-Raphson algorithms.

#### **5.1 Time-Step Control Compatibility**

The LTE calculation in `BSIM3trunc()` provides error estimates for adaptive time-step control. The error estimate must be:

*   **Monotonic with step size**: `LTE ∝ h^p` where `p` is the integration order
*   **Continuous in state variables**: Small changes in charge → small changes in LTE
*   **Bounded**: `LTE < ∞` for finite charges and time steps

These properties ensure the time-step controller converges to an appropriate step size.

#### **5.2 Convergence Test Integration**

The `BSIM3convTest()` function must implement the same convergence criteria as other devices. The normalized error measures:

```
error_V = |ΔV| / (reltol·max(|V|, vntol) + abstol)
error_I = |ΔI| / (reltol·max(|I|, abstol) + abstol)
```

Must use the same `reltol`, `abstol`, `vntol` as the SPICE kernel for consistent convergence detection across all devices.

#### **5.3 SOA Check Timing in Simulation Flow**

SOA checks are typically performed:
*   At DC operating point
*   At each accepted time point in transient analysis
*   Not at every Newton iteration (to avoid overhead)

This timing ensures SOA violations are detected without significantly impacting simulation speed.

### **6. Numerical Safeguards and Robustness**

Several numerical safeguards ensure robust convergence across all operating conditions.

#### **6.1 Floating-Point Exception Prevention**

The code guards against divisions by zero and overflow:

```
if (tox < 1e-18) tox = 1e-18;  /* Prevent division by zero */
if (vgs > 1e3) vgs = 1e3;      /* Prevent overflow in exp() */
```

#### **6.2 Smoothing at SOA Boundaries**

While SOA boundaries aren't actively enforced, the device equations themselves use smoothing functions near physical limits:

```
E_ox_eff = E_ox / (1 + (E_ox/E_crit)^10)^{0.1}  /* Soft limiting */
```

This ensures derivatives remain bounded even beyond SOA limits.

#### **6.3 Memory Allocation Failure Handling**

Graceful handling of allocation failures:

```
inst = (B3instance *)MALLOC(sizeof(B3instance));
if (!inst) return E_NOMEM;  /* Propagate error without crash */
```

In summary, the BSIM3 API binding, memory lifecycle, and SOA implementation provide a robust framework that maintains numerical stability while enforcing physical constraints. The design choices prioritize convergence reliability over strict SOA enforcement, with comprehensive error checking and graceful degradation when limits are approached. This ensures SPICE simulations remain stable even when devices operate near their physical limits, while providing useful warnings to circuit designers about potential reliability issues.

---

# **BSIM3: API Binding, Memory Lifecycle, and Safe Operating Area - C Implementation**

## **1. Device Registration and API Binding (`bsim3init.c`)**

The BSIM3 device is integrated into the Ngspice kernel through a standardized `SPICEdev` structure that defines the device's interface and function pointers.

### **SPICEdev Structure Initialization**
```c
/* bsim3init.c - Device registration */
SPICEdev BSIM3info = {
    .DEVpublic = {
        .name = "bsim3",
        .description = "Berkeley Short-Channel IGFET Model Version 3",
        .terms = 4,                     /* Drain, Gate, Source, Bulk terminals */
        .numNames = 2,                  /* M (instance), BSIM3 (model) */
        .termNames = {"d", "g", "s", "b"},
        .numInstanceParms = 150,        /* Instance parameters (L, W, etc.) */
        .numModelParms = 300,           /* Model parameters (VTH0, U0, etc.) */
        .flags = DEV_DEFAULT,
    },
    .DEVmodParam = BSIM3mPTable,        /* Model parameter table */
    .DEVinstParam = BSIM3pTable,        /* Instance parameter table */
    .DEVload = BSIM3load,               /* DC and transient load function */
    .DEVsetup = BSIM3setup,             /* Matrix allocation and setup */
    .DEVunsetup = BSIM3unsetup,         /* Cleanup function */
    .DEVpzSetup = BSIM3pzSetup,         /* Pole-zero analysis setup */
    .DEVtemperature = BSIM3temp,        /* Temperature scaling */
    .DEVtrunc = BSIM3trunc,             /* Local truncation error calculation */
    .DEVfindBranch = NULL,              /* No branch currents */
    .DEVacLoad = BSIM3acLoad,           /* AC analysis load */
    .DEVaccept = NULL,
    .DEVdestroy = BSIM3destroy,         /* Complete device destruction */
    .DEVmodDelete = BSIM3mDelete,       /* Model deletion */
    .DEVinstDelete = BSIM3delete,       /* Instance deletion */
    .DEVask = BSIM3ask,                 /* Parameter query */
    .DEVmodAsk = BSIM3mAsk,             /* Model parameter query */
    .DEVpzLoad = BSIM3pzLoad,           /* Pole-zero load */
    .DEVconvTest = BSIM3convTest,       /* Convergence testing */
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = NULL,
    .DEVnoise = BSIM3noise,             /* Noise analysis */
    .DEVsoaCheck = BSIM3soaCheck,       /* Safe Operating Area check */
    .DEVinstSize = sizeof(B3instance),  /* Instance structure size */
    .DEVmodSize = sizeof(B3model),      /* Model structure size */
};

void BSIM3init(SPICEdev **device, int *count) {
    *device = &BSIM3info;
    *count = 1;
}
```

**Mathematical Mapping:** The `SPICEdev` structure maps mathematical operations to C functions:
- `DEVload` → Implements the BSIM3 current equations: `I_DS = f(V_GS, V_DS, V_BS)`
- `DEVacLoad` → Implements small-signal admittance matrix: `Y(ω) = G + jωC`
- `DEVtrunc` → Calculates Local Truncation Error: `LTE ≈ h³/12 * d³Q/dt³`
- `DEVsoaCheck` → Enforces physical limits: `|V_GS| < E_crit * t_ox`, `|I_DS| < I_max`, etc.

### **Parameter Table Binding**
The parameter tables `BSIM3mPTable` and `BSIM3pTable` (defined elsewhere) map SPICE input parameters to C structure fields:
```c
/* Example parameter table entry */
IFparm BSIM3pTable[] = {
    IOP("l", B3_L, IF_REAL, "Length"),
    IOP("w", B3_W, IF_REAL, "Width"),
    IOP("ad", B3_AD, IF_REAL, "Drain area"),
    IOP("as", B3_AS, IF_REAL, "Source area"),
    /* ... 150 parameters total */
};
```
Each parameter maps to a bitmask (e.g., `B3_L`) that identifies which instance field needs updating.

## **2. Core Data Structures (`bsim3def.h`)**

The BSIM3 implementation uses two primary structures to separate model parameters from instance state.

### **B3model Structure - Process Parameters**
```c
typedef struct sB3model {
    int B3type;                         /* N_TYPE or P_TYPE */
    double B3vth0;                      /* Threshold voltage VTH0 */
    double B3u0;                        /* Low-field mobility U0 */
    double B3kappa;                     /* Saturation field factor KAPPA */
    double B3eta0;                      /* DIBL coefficient ETA0 */
    double B3uc;                        /* Velocity saturation coefficient UC */
    double B3voff;                      /* Offset voltage VOFF */
    double B3delta;                     /* Width effect on threshold voltage DELTA */
    double B3lambda;                    /* Channel-length modulation LAMBDA */
    double B3xj;                        /* Junction depth XJ */
    double B3tox;                       /* Oxide thickness TOX */
    double B3ld;                        /* Lateral diffusion LD */
    double B3wd;                        /* Width diffusion WD */
    
    /* Capacitance parameters */
    double B3cgso;                      /* Gate-source overlap capacitance per width CGSO */
    double B3cgdo;                      /* Gate-drain overlap capacitance per width CGDO */
    double B3cgb;                       /* Gate-bulk overlap capacitance per length CGBO */
    double B3cj;                        /* Bottom junction capacitance per area CJ */
    double B3mj;                        /* Bottom junction grading coefficient MJ */
    double B3cjsw;                      /* Sidewall junction capacitance per perimeter CJSW */
    double B3mjsw;                      /* Sidewall junction grading coefficient MJSW */
    double B3pb;                        /* Junction built-in potential PB */
    
    /* SOA limits */
    double B3bv_max;                    /* Maximum breakdown voltage */
    double B3i_max;                     /* Maximum drain current */
    double B3p_max;                     /* Maximum power dissipation */
    
    /* Linked list pointers */
    struct sB3model *B3nextModel;       /* Next model in list */
    B3instance *B3instances;            /* First instance of this model */
} B3model;
```

**Mathematical Mapping:** The `B3model` structure stores the physical parameters used in BSIM3 equations:
- `B3vth0`, `B3u0`, `B3kappa` → Used in `V_th` and `I_DS` calculations
- `B3tox`, `B3cgso`, `B3cgdo` → Used in capacitance calculations
- `B3bv_max`, `B3i_max`, `B3p_max` → SOA limit parameters

### **B3instance Structure - Device State**
```c
typedef struct sB3instance {
    /* Node indices */
    int B3dNode;                        /* Drain node index */
    int B3gNode;                        /* Gate node index */
    int B3sNode;                        /* Source node index */
    int B3bNode;                        /* Bulk node index */
    int B3dNodePrime;                   /* Internal drain node (after RD) */
    int B3sNodePrime;                   /* Internal source node (after RS) */
    
    /* Geometry */
    double B3l;                         /* Drawn channel length L */
    double B3w;                         /* Drawn channel width W */
    double B3leff;                      /* Effective channel length LEFF */
    double B3weff;                      /* Effective channel width WEFF */
    
    /* Bias conditions */
    double B3vgs;                       /* Gate-source voltage */
    double B3vds;                       /* Drain-source voltage */
    double B3vbs;                       /* Bulk-source voltage */
    double B3vth;                       /* Threshold voltage (calculated) */
    
    /* Current and conductances */
    double B3ids;                       /* Drain current I_DS */
    double B3gm;                        /* Transconductance gm = ∂I_DS/∂V_GS */
    double B3gds;                       /* Output conductance gds = ∂I_DS/∂V_DS */
    double B3gmbs;                      /* Body transconductance gmbs = ∂I_DS/∂V_BS */
    
    /* Charges and capacitances */
    double B3qgs;                       /* Gate-source charge Q_GS */
    double B3qgd;                       /* Gate-drain charge Q_GD */
    double B3qgb;                       /* Gate-bulk charge Q_GB */
    double B3cgs;                       /* Gate-source capacitance C_GS = ∂Q_GS/∂V_GS */
    double B3cgd;                       /* Gate-drain capacitance C_GD = ∂Q_GD/∂V_GD */
    double B3cgb;                       /* Gate-bulk capacitance C_GB = ∂Q_GB/∂V_GB */
    
    /* Matrix pointers for 6×6 stamp (D, D', G, S, S', B) */
    double *B3drainDrainPtr;            /* G_DD */
    double *B3drainGatePtr;             /* G_DG */
    double *B3drainSourcePtr;           /* G_DS */
    double *B3drainBulkPtr;             /* G_DB */
    /* ... 36 total pointers for full matrix */
    
    /* State vector indices */
    int B3stateQgs;                     /* Index for Q_GS in CKTstate */
    int B3stateQgd;                     /* Index for Q_GD in CKTstate */
    int B3stateQgb;                     /* Index for Q_GB in CKTstate */
    
    /* Linked list */
    struct sB3instance *B3nextInstance; /* Next instance in list */
    B3model *B3modPtr;                  /* Parent model */
} B3instance;
```

**Mathematical Mapping:** The `B3instance` structure stores the device state:
- `B3ids` → The drain current `I_DS` from BSIM3 equations
- `B3gm`, `B3gds`, `B3gmbs` → Small-signal conductances for matrix stamping
- `B3qgs`, `B3qgd`, `B3qgb` → Charges for charge conservation
- Matrix pointers → Locations in SPICE's `G` matrix for stamping conductances

## **3. Memory Lifecycle Management**

### **3.1 Complete Device Destruction (`b3dest.c`)**
```c
void BSIM3destroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    B3model *model = (B3model *)mod;
    B3instance *inst, *nextInst;

    /* Traverse model linked list */
    while (model) {
        B3model *nextModel = model->B3nextModel;

        /* Traverse instance linked list for this model */
        inst = model->B3instances;
        while (inst) {
            nextInst = inst->B3nextInstance;
            FREE(inst->B3name);   /* Free instance name string */
            FREE(inst);           /* Free instance structure */
            inst = nextInst;
        }

        FREE(model);              /* Free model structure */
        model = nextModel;
    }
    *inModel = NULL;  /* Clear the caller's pointer */
}
```

**Memory Management Logic:** This function implements a nested linked list traversal:
1. Outer loop: Iterates through model list (`model->B3nextModel`)
2. Inner loop: Iterates through instance list (`inst->B3nextInstance`)
3. Frees all dynamically allocated memory in reverse order of allocation

### **3.2 Instance Deletion (`b3del.c`)**
```c
int BSIM3delete(GENmodel *inModel, IFuid name, GENinstance **kill) {
    B3model *model = (B3model *)inModel;
    B3instance *prev = NULL, *inst;

    for (; model; model = model->B3nextModel) {
        inst = model->B3instances;
        while (inst) {
            if (strcmp(inst->B3name, name) == 0) {
                /* Found instance to delete */
                if (prev)
                    prev->B3nextInstance = inst->B3nextInstance;
                else
                    model->B3instances = inst->B3nextInstance;

                FREE(inst->B3name);
                FREE(inst);
                return OK;
            }
            prev = inst;
            inst = inst->B3nextInstance;
        }
    }
    return E_NODEV;  /* Device not found */
}
```

**Algorithm:** Linear search through instance linked lists with pointer adjustment:
- Maintains `prev` pointer to update `nextInstance` links
- Returns `E_NODEV` if instance not found (SPICE error code)

### **3.3 Model Deletion (`b3mdel.c`)**
```c
int BSIM3mDelete(GENmodel **inModel, IFuid modname, GENmodel *kill) {
    B3model **model = (B3model **)inModel;
    B3model *prev = NULL, *mod;

    for (mod = *model; mod; mod = mod->B3nextModel) {
        if