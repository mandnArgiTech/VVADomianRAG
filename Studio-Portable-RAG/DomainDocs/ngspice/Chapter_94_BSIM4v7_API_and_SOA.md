# BSIM4v7: API Binding, Memory Lifecycle, and SOA

_Generated 2026-04-12 17:04 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/bsim4v7init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7dest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7del.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7mdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7soachk.c`

# BSIM4v7: Final Planar Physics Revision and DC Load

This chapter details the implementation of the BSIM4v7 (Berkeley Short-channel IGFET Model, version 7) in the Ngspice circuit simulator. BSIM4v7 represents the final major revision of the planar bulk CMOS model, incorporating comprehensive short-channel, narrow-width, quantum mechanical, and layout-dependent effects essential for accurate simulation of sub-100nm technologies. The core of its DC and transient simulation capability resides in the interplay between four critical files: `bsim4v7def.h` defines the fundamental data structures; `b4v7par.c` handles model parameter parsing and binding; `b4v7temp.c` manages temperature-dependent parameter updates; and `b4v7ld.c` implements the DC load function, which stamps the device's nonlinear conductances and charges into the circuit's system of equations. The following sections provide the mathematical foundation and the corresponding C implementation that maps these physics to Ngspice's Modified Nodal Analysis (MNA) framework.

## Mathematical Formulation

The BSIM4v7 DC model computes terminal currents and charges as functions of terminal voltages, geometry, temperature, and a vast set of physical parameters. The formulation ensures continuity and derivability for robust Newton-Raphson convergence.

### 1. Threshold Voltage with Advanced Effects
The effective threshold voltage \( V_{th} \) is a composite of the long-channel value modified by several physical effects:
```math
V_{th} = V_{th0} + \Delta V_{th,SCE} + \Delta V_{th,DIBL} + \Delta V_{th,NWE} + \Delta V_{th,STRESS} + \Delta V_{th,TEMP}
```
*   \( V_{th0} \): Zero-bias long-channel threshold voltage (`BSIM4v7vth0`).
*   \( \Delta V_{th,SCE} \): Short-Channel Effect correction, a function of \( L_{eff} \), \( V_{ds} \), and parameters `BSIM4v7dvt0`, `BSIM4v7dvt1`, `BSIM4v7dvt2`.
*   \( \Delta V_{th,DIBL} \): Drain-Induced Barrier Lowering, modeled as \( \eta \cdot V_{ds} \), where \( \eta \) depends on `BSIM4v7eta0` and `BSIM4v7etab`.
*   \( \Delta V_{th,NWE} \): Narrow-Width Effect, a function of \( W_{eff} \) and parameters `BSIM4v7k1`, `BSIM4v7k2`.
*   \( \Delta V_{th,STRESS} \): Stress-induced shift from STI and WPE, calculated in `b4v7geo.c`.
*   \( \Delta V_{th,TEMP} \): Temperature dependence via `BSIM4v7kt1`.

### 2. Effective Mobility and Velocity Saturation
Carrier mobility degrades with vertical field and velocity saturates at high lateral fields.
```math
\mu_{eff} = \frac{\mu_0}{1 + (E_{eff}/E_0)^\nu}
```
where \( \mu_0 \) is `BSIM4v7u0`, \( E_{eff} \) is the effective vertical field, and \( E_0 \), \( \nu \) are model parameters (`BSIM4v7ua`, `BSIM4v7ub`, `BSIM4v7uc`). The saturation velocity \( v_{sat} \) (`BSIM4v7vsat`) is used to define the critical field \( E_{crit} = v_{sat} / \mu_{eff} \).

### 3. Drain Current (I-V Core)
A single, continuous expression ensures smooth transitions between cutoff, linear, and saturation regions.
```math
V_{gsteff} = DEVfetlim(V_{gs} - V_{th}, V_{gs,prev} - V_{th,prev}, vtm)
```
```math
V_{dseff} = V_{dsat} - 0.5 \left[ V_{dsat} - V_{ds} - \delta + \sqrt{(V_{dsat} - V_{ds} - \delta)^2 + 4 \delta V_{dsat}} \right]
```
```math
I_{ds} = \frac{W_{eff}}{L_{eff}} \mu_{eff} C_{ox} \frac{V_{gsteff} \cdot V_{dseff} \left(1 - \frac{V_{dseff}}{2 V_{b}} \right)}{1 + \frac{V_{dseff}}{E_{crit} L_{eff}}}
```
The saturation voltage \( V_{dsat} \) is calculated as \( V_{dsat} = E_{crit} L_{eff} \cdot V_{gsteff} / (E_{crit} L_{eff} + V_{gsteff}) \). The function `DEVfetlim` is critical for Newton-Raphson convergence, limiting the voltage change between iterations.

### 4. Gate Tunneling Currents
Gate leakage is modeled for accumulation, inversion, and source/drain overlap regions.
```math
I_{gc} = A \cdot T_{ox} \cdot \exp\left(-B \cdot T_{ox} / (V_{ox} + C)\right)
```
```math
I_{gs} = I_{gd} = W_{eff} \cdot D \cdot V_{gs/d} \cdot \exp\left(-E / (V_{gs/d} + F)\right)
```
Parameters `AIGC`, `BIGC`, `CIGC`, `AIGS`, `BIGS`, etc., control these currents. They are enabled via the `IGCMOD` and `IGBMOD` flags.

### 5. Charge and Capacitance Model (Q-V)
The intrinsic charge model computes inversion charge \( Q_{inv} \) and depletion charge \( Q_{dep} \). Partitioning to source and drain terminals is controlled by the `XPART` parameter (0=40/60, 1=50/50, 0.5= Ward-Dutton).
```math
Q_G = -(Q_{inv} + Q_{dep})
```
```math
Q_D = XPART \cdot Q_{inv}
```
```math
Q_S = (1 - XPART) \cdot Q_{inv}
```
```math
Q_B = Q_{dep}
```
Charge conservation is enforced: \( Q_G + Q_D + Q_S + Q_B = 0 \). The derivatives of these charges with respect to terminal voltages yield the transcapacitances (e.g., \( C_{gs} = \partial Q_G / \partial V_s \)).

### 6. 6x6 Conductance Matrix for MNA
For DC and transient analysis, the device stamps a 6x6 Jacobian matrix into the circuit's system \( J \Delta x = -F \). The matrix includes contributions from conductances (\( g_m, g_{ds}, g_{mb} \)), gate tunneling conductances, and capacitance derivatives.
The matrix structure for nodes G, D, S, B, GP, SP (where GP/SP are internal nodes for gate/source resistance if `RGMOD=1`) is:
```
[ Gg  Gd  Gs  Gb  Ggp Gsp ]   [ΔVg]   [Ig]
[ Dg  Dd  Ds  Db  Dgp Dsp ]   [ΔVd]   [Id]
[ Sg  Sd  Ss  Sb  Sgp Ssp ] * [ΔVs] = -[Is]
[ Bg  Bd  Bs  Bb  Bgp Bsp ]   [ΔVb]   [Ib]
[GPg GPd GPs GPb GPgp GPsp]   [ΔVgp]  [ 0]
[SPg SPd SPs SPb SPgp SPsp]   [ΔVsp]  [ 0]
```
Where, for example:
*   \( Gg = \partial I_G / \partial V_g \) includes gate tunneling conductance and capacitive displacement current.
*   \( Dd = g_{ds} + g_{bd} + g_{gd\_tunnel} \).
*   Off-diagonal terms ensure symmetry and charge conservation (e.g., \( Gd = \partial I_G / \partial V_d \)).

## Convergence Analysis

Robust numerical convergence in SPICE is paramount. BSIM4v7 employs several algorithms to ensure stability in DC operating point and transient analyses.

### 1. Newton-Raphson Convergence Test (`b4v7cvtest.c`)
The function `BSIM4v7convTest` checks if the Newton iteration has converged by comparing changes in state variables against SPICE tolerances.
*   **Voltage Convergence**: For each branch voltage (e.g., \( V_{gs} \), \( V_{ds} \), \( V_{bs} \)):
    ```math
    |\Delta V_{new}| \leq \text{RELTOL} \cdot \max(|V_{old}|, \text{VNTOL}) + \text{ABSTOL}_V
    ```
    where `RELTOL=1e-3`, `VNTOL=1e-6` by default.
*   **Charge Convergence**: For each stored charge state (\( Q_{gs}, Q_{gd}, Q_{gb} \)):
    ```math
    |\Delta Q| \leq \text{RELTOL} \cdot \max(|Q_{old}|, \text{CHGTOL}) + \text{ABSTOL}_Q
    ```
    where `CHGTOL=1e-14`.
*   **Current Convergence**: Checks the absolute change in terminal currents against `ABSTOL=1e-12`.
The function returns `OK` only if *all* checked states have converged.

### 2. Local Truncation Error Control (`b4v7trunc.c`)
For transient analysis, `BSIM4v7trunc` calculates the Local Truncation Error (LTE) associated with the device's state to guide time-step selection.
*   The LTE for a state variable \( x \) (charge or current) using the trapezoidal integration rule is estimated as:
    ```math
    \text{LTE}_x \approx \frac{\Delta t_n}{2} \cdot | \dot{x}_n - \dot{x}_{n-1} |
    ```
    where \( \Delta t_n \) is the current time step, and \( \dot{x} \) is the derivative (current for charge, di/dt for current).
*   This predicted error is normalized:
    ```math
    \text{error} = \frac{\text{LTE}_x}{\max(|x_n|, \text{CHGTOL}) + \text{ABSTOL}_x}
    ```
*   The function returns the maximum normalized error across all device states. The SPICE integrator compares this to `TRTOL` (default 7) to accept/reject the time step and choose a new \( \Delta t \).

### 3. Voltage Limiting via `DEVfetlim`
The internal function `DEVfetlim` is applied to all internal branch voltages (\( V_{gsteff}, V_{dseff} \)) before computing currents. It limits the voltage change between Newton iterations to prevent divergence, especially near the kink between operation regions. It implements a smooth, derivative-friendly limiting function that clamps the new voltage guess to be within a few thermal voltages (\( vtm = kT/q \)) of the previous iteration's value. This is the first line of defense against Newton iteration divergence.

### 4. Source-Drain Symmetry and Swap
To maintain physical symmetry and improve convergence when \( V_{ds} < 0 \), the model internally swaps source and drain terminals, recalculating all voltages and derivatives accordingly. The stamped matrix and RHS vector are then unswapped before returning to the solver. This ensures the model equations are always evaluated in the \( V_{ds} \geq 0 \) domain.

## C Implementation

The mathematical models are realized in Ngspice through a structured C implementation centered on key data structures and functions defined across several files.

### 1. Core Data Structures (`bsim4v7def.h`)
The model and instance parameters are encapsulated in two primary structures:
*   `sBSIM4v7model`: Contains all process-related parameters (over 450), flags (e.g., `BSIM4v7igcMod`), and pointers to the model's matrix location.
*   `sBSIM4v7instance`: Contains terminal voltages, currents, conductances, charges, state derivatives, and pointers to its specific entries in the circuit's matrix (`BSIM4v7DdPtr`, `BSIM4v7GbPtr`, etc.). It also holds the `BSIM4v7states[]` array for storing charge and current history for LTE calculation.

### 2. DC Load Function (`b4v7ld.c`)
The function `BSIM4v7load` is the workhorse for DC and transient analysis.
1.  **Parameter Retrieval**: Accesses model parameters and instance voltages from the structures.
2.  **Geometry & Temperature Scaling**: Calls helper functions (which ultimately use `b4v7temp.c`) to compute effective \( L_{eff}, W_{eff} \) and temperature-adjusted parameters.
3.  **State Calculation**: Computes \( V_{th} \), \( \mu_{eff} \), \( V_{gsteff} \) (using `DEVfetlim`), \( V_{dsat} \), \( V_{dseff} \).
4.  **Current & Derivative Calculation**: Evaluates the \( I_{ds} \) equation and its analytic derivatives (\( g_m, g_{ds}, g_{mb} \)). Calculates gate tunneling currents if enabled.
5.  **Charge Calculation**: Computes \( Q_G, Q_D, Q_S, Q_B \) and their voltage derivatives (capacitances).
6.  **Matrix Stamping**: Stamps the 6x6 conductance/capacitance matrix into the sparse matrix `ckt->CKTmatrix` using the stored pointers.
    *   For DC: Stamps only the conductance components (`G`).
    *   For Transient: Stamps the combined \( G + \frac{dQ}{dV} \cdot \frac{\partial}{\partial t} \) matrix. Using the trapezoidal rule, the capacitor stamp is \( G_{eq} = \frac{2C}{\Delta t} \) and a companion current source.
7.  **RHS Vector Stamping**: Stamps the right-hand side vector `ckt->CKTrhs[]` with the negative of the sum of currents entering each node (Kirchhoff's Current Law).

### 3. Parameter Setup and Binding (`b4v7set.c`, `b4v7par.c`)
*   `BSIM4v7setup`: Allocates space in the sparse matrix for the device's 6x6 stamp using `SMPmakeElt` calls. It determines the matrix positions based on the circuit node numbers and stores the pointers in the instance structure for efficient access during loading.
*   `BSIM4v7param`: Called during netlist parsing. It reads parameter values from the SPICE input deck, validates them against min/max bounds defined in the `IFparm` table, and stores them in the model structure.

### 4. Temperature Update (`b4v7temp.c`)
The function `BSIM4v7temp` recalculates all temperature-dependent parameters (e.g., mobility, threshold voltage, junction potentials) and geometry-dependent parameters (e.g., `BSIM4v7leff`, `BSIM4v7weff`). It is called whenever the circuit temperature changes or at the start of a new simulation.

### 5. Integration with Ngspice Solver
The device is registered with Ngspice via the `SPICEdev` structure defined in `bsim4v7init.c`:
```c
SPICEdev BSIM4v7info = {
    .DEVpublic = {
        .name = "BSIM4v7",
        .description = "BSIM4v7 MOSFET model",
    },
    .DEVparam = BSIM4v7param,
    .DEVmodParam = BSIM4v7mParam,
    .DEVload = BSIM4v7load,
    .DEVsetup = BSIM4v7setup,
    .DEVunsetup = NULL,
    .DEVpzSetup = BSIM4v7setup,
    .DEVtemperature = BSIM4v7temp,
    .DEVtrunc = BSIM4v7trunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = BSIM4v7acLoad,
    .DEVaccept = NULL,
    .DEVdestroy = BSIM4v7destroy,
    .DEVmodDelete = BSIM4v7mDelete,
    .DEVdelete = BSIM4v7delete,
    .DEVsetic = BSIM4v7getic,
    .DEVask = BSIM4v7ask,
    .DEVmodAsk = BSIM4v7mAsk,
    .DEVpzLoad = BSIM4v7pzLoad,
    .DEVconvTest = BSIM4v7convTest,
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = NULL,
    .DEVnoise = BSIM4v7noise,
    .DEVsoaCheck = BSIM4v7soaCheck,
    .DEVinstSize = sizeof(sBSIM4v7instance),
    .DEVmodSize = sizeof(sBSIM4v7model)
};
```
This structure provides the solver with function pointers for all necessary operations, creating a clean interface between the device model and the core simulation engine. The `BSIM4v7load` function, implementing the mathematical formulation above, is called repeatedly by the Newton-Raphson solver until convergence is achieved, as verified by `BSIM4v7convTest`.