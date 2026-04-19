# BSIM4v7: Final Planar Physics Revision and DC Load

_Generated 2026-04-12 16:15 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/bsim4v7def.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7ld.c`

# BSIM4v7: Final Planar Physics Revision and DC Load

## Technical Introduction

The BSIM4v7 model represents the culmination of planar bulk CMOS modeling within the BSIM4 framework, incorporating refined physical effects for nanometer-scale technologies. Its implementation in Ngspice is architected around four core C source files that establish the model's identity, manage its parameters, handle temperature scaling, and execute the critical DC load operation. The file `bsim4v7def.h` is the architectural blueprint, defining the fundamental data structures (`sBSIM4v7model`, `sBSIM4v7instance`) that encapsulate over 280 physical parameters, instance-specific electrical states, and sparse matrix pointers for a 6x6 Modified Nodal Analysis (MNA) system. The parameter binding logic in `b4v7par.c` maps SPICE netlist parameters to these internal C struct members, enforcing model-card semantics. Temperature-dependent behavior, a critical aspect of modern IC design, is managed by `b4v7temp.c`, which scales key parameters like mobility (`U0`), threshold voltage (`VTH0`), and junction characteristics according to the simulation temperature (`ckt->CKTtemp`). The cornerstone of DC analysis is `b4v7ld.c`, which houses the `BSIM4v7load()` function. This function evaluates the complete core physics model—calculating effective geometry, threshold voltage with advanced short-channel and stress effects, mobility degradation, drain current from subthreshold to strong inversion, and associated conductances—and stamps the resulting Jacobian matrix into SPICE's Newton-Raphson solver. Together, these files form the essential infrastructure that transforms the BSIM4v7 mathematical formalism into a robust, convergent circuit simulation component within the Ngspice kernel.

## Mathematical Formulation

The BSIM4v5 model's frequency-domain and noise analysis is built upon the linearization of its DC and charge equations, constructing complex admittance matrices and noise spectral densities for integration into SPICE's Modified Nodal Analysis (MNA) framework.

### 1. Small-Signal AC Admittance Matrix
The core of the AC analysis is the construction of a 4x4 complex admittance matrix **Y(ω)** that relates the small-signal terminal currents to voltages. This matrix is stamped into SPICE's circuit matrix for frequency-domain simulation (`ckt->CKTomega`).

**Matrix Definition:**
```
Y(ω) = G + jωC
```
Where:
*   **G** is the real conductance matrix (derivatives of DC currents: `gm`, `gds`, `gmb`).
*   **C** is the capacitance matrix (derivatives of terminal charges: `cgg`, `cgd`, `cgs`, etc.).
*   **ω** is the angular frequency (`ckt->CKTomega`).

**Complete 4x4 Matrix Stamp (including extrinsic gate resistance Rg):**
The implementation in `b4v5acld.c` stamps the following matrix for nodes Gate, Drain, Source, Bulk (G, D, S, B):

| Stamp Point          | G Column                              | D Column                  | S Column                  | B Column                  | RHS |
| :------------------- | :------------------------------------ | :------------------------ | :------------------------ | :------------------------ | :--- |
| **G Row (Internal)** | `(1/Rg) + jω*cgg`                     | `jω*cgd`                  | `jω*cgs`                  | `jω*cgb`                  | `Ig` |
| **D Row**            | `-gm + jω*cdg`                        | `gds + gbd + jω*cdd`      | `-gds - gmbs + jω*cds`    | `-gbd + jω*cdb`           | `Id` |
| **S Row**            | `-gm + jω*csg`                        | `-gds + jω*csd`           | `gds + gmbs + gbs + jω*css` | `-gbs + jω*csb`           | `Is` |
| **B Row**            | `jω*cbg`                              | `-gbd + jω*cbd`           | `-gbs + jω*cbs`           | `gbd + gbs + jω*cbb`      | `Ib` |

**Key Derivatives (stored in `B4v5instance`):**
*   `B4v5gm`: Transconductance (∂Id/∂Vgs)
*   `B4v5gds`: Output conductance (∂Id/∂Vds)
*   `B4v5gmb`: Body transconductance (∂Id/∂Vbs)
*   `B4v5cgg`, `B4v5cgd`, `B4v5cgs`, `B4v5cgb`: Gate charge derivatives.
*   `B4v5rg`: Extrinsic gate resistance (model parameter).

### 2. Pole-Zero Analysis Formulation
For pole-zero analysis, the `b4v5pzld.c` file constructs the s-domain transfer function **H(s)** for the linearized system:
```
H(s) = [C·s + G]^{-1} · B
```
Where:
*   **s** is the complex frequency variable (`jω` for AC).
*   **G** and **C** are the same conductance and capacitance matrices as in AC analysis.
*   **B** is the input selection vector.

The code loads the matrix `(G + s*C)` into SPICE's SMP matrix for eigenvalue computation, enabling the analysis of circuit stability and frequency response.

### 3. Noise Analysis Models
Noise analysis in `b4v5noi.c` implements multiple configurable models for thermal, flicker, and induced gate noise. The total noise is represented as a set of correlated noise sources stamped into SPICE's noise correlation matrix.

#### 3.1 Thermal Noise (Channel)
The thermal noise spectral density is modeled as:
```
S_id,th(f) = 4kT · γ · gds0
```
Where:
*   `k` is Boltzmann's constant (`CONSTboltz`).
*   `T` is the absolute temperature (`ckt->CKTtemp`).
*   `gds0` is the output conductance at zero Vds.
*   `γ` is the bias-dependent noise coefficient (`B4v5gamma0`), calculated in the code as:
    ```
    gamma = B4v5gamma0 * (1 - (Vds / (Esat * Leff))^2)  // Simplified representation
    ```
    The model selector `B4v5tnoimod` chooses between SPICE2, BSIM3, and BSIM4-specific formulations for `γ`.

#### 3.2 Induced Gate Noise (RF)
For RF modeling, induced gate noise (IGN) and its correlation with channel thermal noise are included when `B4v5tnoimod` is set appropriately.
```
S_ig,ind(f) = 4kT · δ · (ω²Cgs²) / (5gd0)
```
The correlation coefficient **ρ** between the gate and drain noise currents is complex and frequency-dependent:
```
ρ = c · jω · sqrt(S_id,th · S_ig,ind)  // where c ≈ 0.395
```
These are stamped as two correlated noise sources between gate and source, and drain and source.

#### 3.3 Flicker (1/f) Noise
A unified flicker noise model is implemented, controlled by `B4v5fnoimod`. The power spectral density is:
```
S_id,fl(f) = (KF · Id^AF) / (f^EF · Weff · Leff^EF)
```
Where:
*   `KF`, `AF`, `EF` are model parameters (`B4v5kf`, `B4v5af`, `B4v5ef`).
*   `Id` is the DC drain current.
*   `Weff`, `Leff` are effective channel dimensions.

The code in `B4v5noise` uses a `switch(B4v5fnoimod)` statement to select between different calculation branches (e.g., SPICE2, BSIM4 unified model).

#### 3.4 Total Noise Correlation Matrix
All noise contributions are summed and stamped into a 2x2 noise correlation matrix for the device's internal nodes, which SPICE uses to compute total output noise:
```
[Y] · [C_N] · [Y]† = ⟨i_n · i_n†⟩
```
Where `[C_N]` is the noise correlation matrix built from `S_id,th`, `S_id,fl`, `S_ig,ind`, and `ρ`.

## Convergence Analysis

Convergence in frequency-domain and noise simulations for BSIM4v5 relies on the numerical stability of the linearized matrices and the physical consistency of the noise models.

### 1. Frequency-Domain (AC & Pole-Zero) Convergence
*   **Matrix Conditioning:** The complex admittance matrix `Y(ω) = G + jωC` must be well-conditioned across all simulation frequencies. The inclusion of `Rg` (gate resistance) provides a real diagonal component that improves matrix conditioning at high frequencies, preventing singularities.
*   **Charge Conservation:** The capacitance matrix **C** is derived from charge derivatives (`cgg = ∂Qg/∂Vg`, etc.) using the Ward-Dutton partition. This ensures charge conservation `(Qg + Qd + Qs + Qb = 0)` in the small-signal domain, which is critical for stable AC response.
*   **Pole-Zero Solver Stability:** The pole-zero analysis solves `det(G + sC) = 0`. Convergence depends on SPICE's eigenvalue solver algorithms and the numerical accuracy of the `G` and `C` matrix elements stamped by `B4v5pzLoad`. Ill-conditioned matrices due to extreme geometry or bias can lead to solver failures.

### 2. Noise Analysis Convergence
*   **Spectral Density Positivity:** The noise analysis ensures all computed Power Spectral Densities (PSDs) are non-negative:
    ```
    S_id(f) >= 0 for all f.
    ```
    The code clamps negative values (from numerical error) to zero.
*   **Correlation Matrix Positive-Definiteness:** The 2x2 noise correlation matrix must be positive semi-definite. This imposes a constraint on the correlation coefficient `ρ`:
    ```
    |ρ|² ≤ 1
    ```
    The BSIM4v5 IGN model ensures this physical constraint is met in its derivation.
*   **Geometry Scaling Continuity:** Flicker noise PSD scales as `1/(Weff * Leff^EF)`. As `Weff` or `Leff` approach zero (invalid geometry), the noise term diverges. The model's geometry calculation (`b4v5geo.c`) must provide non-zero, positive effective dimensions to ensure finite, continuous noise values.
*   **Frequency Roll-Off:** At very high frequencies (`f → ∞`), the IGN model scales as `ω²`. In practice, SPICE noise integration over frequency band `[fmin, fmax]` converges only if the simulation bandwidth is finite and the roll-off is handled correctly by the simulator's integration routines.

### 3. RF-Specific Convergence Aids
*   **Extrinsic Parasitics:** The explicit inclusion of `Rg`, `Rbs` (bulk resistance), and `Rbd` in the Y-matrix provides damping, which improves Newton-Raphson convergence in harmonic balance or shooting-method analyses that use the AC matrix.
*   **Model Selector Continuity:** The `tnoimod` and `fnoimod` selectors must switch between noise formulations without introducing discontinuities in the total noise PSD or its derivative. The C code uses `switch` statements with separate, continuous branches for each model to achieve this.
*   **Integration with Transient Analysis:** For `.NOISE` analysis in a transient operating point, convergence requires that the DC operating point (from which `gm`, `gds`, `gmb` are derived) is itself converged. The noise functions `B4v5noise` are called only after a successful DC solution.

----------

# C Implementation

This section details the Ngspice-specific C implementation of the BSIM4v7 DC load and core physics model. The code architecture is centered on two primary data structures defined in `bsim4v7def.h` and a suite of functions that implement the mathematical formulations for DC analysis, matrix stamping, and numerical convergence.

## 1. Core Data Structures and Memory Management

The BSIM4v7 model is built upon two foundational C structures that encapsulate all model parameters, instance variables, and simulation state.

### 1.1 The Model Structure (`sBSIM4v7model`)

This structure, defined in `bsim4v7def.h`, stores all process-dependent parameters that are shared across transistor instances. It acts as a container for the physical model.

**Key Implementation Mappings:**
*   **Threshold Voltage Parameters:** Fields like `BSIM4v7vth0`, `BSIM4v7dvt0`, `BSIM4v7dvt1`, `BSIM4v7k1`, `BSIM4v7k2`, `BSIM4v7kt1` directly correspond to the coefficients in the composite Vth equation (`Vth = Vth0 + ΔVth_SCE + ΔVth_DIBL + ΔVth_NWE + ΔVth_TEMP`).
*   **Mobility Parameters:** `BSIM4v7u0`, `BSIM4v7ua`, `BSIM4v7ub`, `BSIM4v7uc`, `BSIM4v7ute` store the coefficients for the vertical field, Coulomb scattering, and temperature-dependent mobility degradation models.
*   **Velocity Saturation:** `BSIM4v7vsat`, `BSIM4v7a0`, `BSIM4v7ags`, `BSIM4v7b0`, `BSIM4v7b1` implement the lateral field mobility reduction and bulk charge effect.
*   **Layout-Dependent Effects:** `BSIM4v7sa`, `BSIM4v7sb`, `BSIM4v7sd` (STI stress) and `BSIM4v7wpe` (Well Proximity Effect) parameters are stored here for geometry scaling functions.
*   **Model Selectors:** Integer flags `BSIM4v7tnoimod` and `BSIM4v7fnoimod` control the branch logic in the noise analysis functions (`b4v7noi.c`).

### 1.2 The Instance Structure (`sBSIM4v7instance`)

This structure holds all state information unique to a single transistor instance during a simulation.

**Key Implementation Mappings:**
*   **Electrical State:** Terminal voltages (`BSIM4v7vgs`, `BSIM4v7vds`, `BSIM4v7vbs`), currents (`BSIM4v7cd`, `BSIM4v7cbd`), and conductances (`BSIM4v7gm`, `BSIM4v7gds`) are stored as `double` types. These are the primary outputs of the DC model evaluation.
*   **Charge State:** Charges (`BSIM4v7qg`, `BSIM4v7qd`, `BSIM4v7qs`, `BSIM4v7qb`) and their corresponding state vector indices (`BSIM4v7states[7]`) are crucial for the charge-conserving transient analysis. The indices link instance charges to the global SPICE state vector managed by `ckt->CKTstate0/1/2`.
*   **Sparse Matrix Pointers:** A comprehensive set of `SMPmatrix` pointers (e.g., `BSIM4v7drainDrainPtr`, `BSIM4v7gateSourcePtr`) defines a 6x6 conductance matrix. This includes stamps for four external nodes (D, G, S, B) and two internal nodes (d', s') for parasitic source/drain resistance.
*   **Internal Variables:** Intermediate calculation results like `BSIM4v7von` (turn-on voltage), `BSIM4v7vdsat` (saturation voltage), and `BSIM4v7beta` (gain factor) are cached here to avoid recalculation in related functions (AC load, noise).

## 2. Matrix Stamping and the DC Load Function (`b4v7ld.c`)

The `BSIM4v7load()` function in `b4v7ld.c` is the core DC analysis routine. It evaluates the mathematical model, computes conductances, and stamps the Jacobian matrix for the Newton-Raphson solver.

### 2.1 Matrix Pointer Allocation (`b4v7set.c`)

Before simulation, `BSIM4v7setup()` in `b4v7set.c` allocates the sparse matrix pointers. It creates a 6x6 matrix structure:
*   **Rows/Columns 0-3:** External terminals Drain, Gate, Source, Bulk.
*   **Rows/Columns 4-5:** Internal nodes `dNodePrime`, `sNodePrime` for parasitic resistances.
The code uses `SMPmakeElt()` to create matrix elements for all diagonal and off-diagonal combinations, enabling the stamping of conductances and capacitances between any node pair.

### 2.2 The DC Load Algorithm

The load function follows a strict sequence that maps directly to the mathematical model:

```c
int BSIM4v7load(GENmodel *inModel, CKTcircuit *ckt)
{
    BSIM4v7model *model = (BSIM4v7model*)inModel;
    BSIM4v7instance *here;
    
    for(; model; model = model->BSIM4v7nextModel) {
        for(here = model->BSIM4v7instances; here; here = here->BSIM4v7nextInstance) {
            
            // 1. FET LIMITING: Apply DEVfetlim to Vgs, Vds, Vbs
            DEVfetlim(&vgs, &vds, &vbs, vth, vcrit, vdsmax);
            here->BSIM4v7vgs = vgs;
            here->BSIM4v7vds = vds;
            here->BSIM4v7vbs = vbs;
            
            // 2. EFFECTIVE GEOMETRY: Call b4v7geo.c functions
            here->BSIM4v7leff = Ldrawn - 2*model->BSIM4v7dl;
            here->BSIM4v7weff = Wdrawn - 2*model->BSIM4v7dw;
            // Apply STI and WPE corrections
            calculateStressEffects(here, model);
            
            // 3. THRESHOLD VOLTAGE: Compute composite Vth
            vth = model->BSIM4v7vth0;
            vth += calculateSCE(here, model); // ΔVth_SCE
            vth += calculateDIBL(here, model); // ΔVth_DIBL
            vth += calculateNWE(here, model);  // ΔVth_NWE
            vth += calculateTempVth(here, model, ckt->CKTtemp); // ΔVth_TEMP
            here->BSIM4v7von = vth + model->BSIM4v7voff;
            
            // 4. EFFECTIVE MOBILITY: Compute μ_eff
            ueff = model->BSIM4v7u0;
            ueff /= (1.0 + model->BSIM4v7ua * Eeff + model->BSIM4v7ub * Eeff*Eeff);
            ueff /= (1.0 + (ueff * vds) / (model->BSIM4v7vsat * here->BSIM4v7leff));
            ueff *= pow(ckt->CKTtemp/model->BSIM4v7tnom, -model->BSIM4v7ute);
            here->BSIM4v7ueff = ueff;
            
            // 5. DRAIN CURRENT: Compute Ids using smooth function
            vgsteff = calculateVgsteff(vgs, vth, model->BSIM4v7nfactor, ckt->CKTtemp);
            vdsat = calculateVdsat(vgsteff, ueff, model, here);
            
            ids_lin = ueff * model->BSIM4v7cox * (here->BSIM4v7weff/here->BSIM4v7leff) *
                      (vgsteff * vds - 0.5 * vds * vds);
            ids_sat = 0.5 * ueff * model->BSIM4v7cox * (here->BSIM4v7weff/here->BSIM4v7leff) *
                      vgsteff * vgsteff;
            
            // Smooth transition using (1 + (Vds/Vdsat)^M)^(-1/M)
            M = 2.0;
            ids = ids_lin * pow(1.0 + pow(fabs(vds/vdsat), M), -1.0/M);
            here->BSIM4v7cd = ids;
            
            // 6. CONDUCTANCE CALCULATION: Analytic derivatives
            here->BSIM4v7gm = dIds_dVgs;  // ∂Id/∂Vgs
            here->BSIM4v7gds = dIds_dVds; // ∂Id/∂Vds
            here->BSIM4v7gmbs = dIds_dVbs; // ∂Id/∂Vbs
            
            // 7. JUNCTION & TUNNELING CURRENTS
            here->BSIM4v7cbd = calculateJunctionCurrent(vbd, model, here, 'd');
            here->BSIM4v7cbs = calculateJunctionCurrent(vbs, model, here, 's');
            here->BSIM4v7igc = calculateGateTunnelCurrent(vgs, vgd, model, here);
            
            // 8. MATRIX STAMPING: Load Jacobian into SMP matrix
            // Stamp conductances
            *(here->BSIM4v7drainDrainPtr) += here->BSIM4v7gds + gbd + ggd_tunnel;
            *(here->BSIM4v7drainSourcePtr) -= here->BSIM4v7gds;
            *(here->BSIM4v7drainGatePtr) += here->BSIM4v7gm;
            *(here->BSIM4v7drainBulkPtr) += here->BSIM4v7gmbs - gbd;
            
            // Stamp internal resistance (Rd, Rs)
            gdpr = 1.0 / (model->BSIM4v7rdsw / here->BSIM4v7weff);
            gspr = 1.0 / (model->BSIM4v7rdsw / here->BSIM4v7weff);
            *(here->BSIM4v7drainPrimeDrainPrimePtr) += gdpr + here->BSIM4v7gds;
            *(here->BSIM4v7sourcePrimeSourcePrimePtr) += gspr + here->BSIM4v7gds;
            *(here->BSIM4v7drainPrimeSourcePrimePtr) -= here->BSIM4v7gds;
            
            // 9. STORE STATE FOR TRUNCATION ERROR
            ckt->CKTstate0[here->BSIM4v7states[0]] = vgs;
            ckt->CKTstate0[here->BSIM4v7states[1]] = ids;
            // ... store other states
        }
    }
    return OK;
}
```

### 2.3 The `DEVfetlim` Voltage Limiting Algorithm

A critical component for convergence, `DEVfetlim()` is called at the start of the load function. It smoothly limits terminal voltages to prevent numerical overflow and ensure derivative continuity in the Newton-Raphson iteration:
1.  Limits the gate overdrive `Vgst = Vgs - Vth` to a critical value `vcrit`.
2.  Limits `Vds` to a maximum `vdsmax` and ensures `|Vds| ≤ |Vgst|`.
3.  Applies symmetric limiting to prevent hysteresis.
This function is implemented in `b4v7ld.c` and is essential for simulator robustness.

## 3. Supporting Implementation Files

### 3.1 Geometry and Stress Calculation (`b4v7geo.c`)
This file implements the layout-dependent effect models. Functions calculate:
*   Effective length/width (`Leff`, `Weff`) with bias-dependent corrections.
*   STI mechanical stress (`σ_sti`) using exponential distance decay models and its effect on mobility (`Δμ/μ0`) and threshold voltage (`ΔVth_sti`).
*   Well Proximity Effect (WPE) factor as a function of distance to well edges, modifying `Vth0` and `U0`.

### 3.2 Convergence Testing (`b4v7cvtest.c`)
The `BSIM4v7convTest()` function implements the SPICE convergence criteria by comparing successive Newton iterations:
*   **Voltage Convergence:** `|v_new - v_old| < RELTOL*MAX(|v_new|,|v_old|) + VNTOL`
*   **Current Convergence:** `|i_new - i_old| < RELTOL*MAX(|i_new|,|i_old|) + ABSTOL`
*   **Charge Convergence:** Similar check for all stored charge states.
The function accesses old states from `ckt->CKTstate0` and new values from instance fields or `ckt->CKTrhsOld`.

### 3.3 Local Truncation Error Calculation (`b4v7trunc.c`)
The `BSIM4v7trunc()` function computes the Local Truncation Error (LTE) for adaptive time-step control:
1.  For each charge state `q` (gate, drain, source, bulk, junction), it calculates the current `i = dq/dt`.
2.  The error is estimated as `error = |Δt * i| / (ABSTOL + RELTOL * MAX(|q_old|, |q_new|))`.
3.  The maximum error across all devices is returned to the SPICE core, which adjusts the time step using `h_new = h_old * sqrt(TRTOL/error)`.

### 3.4 Safe Operating Area Checking (`b4v7soachk.c`)
The `BSIM4v7soaCheck()` function performs reliability checks at each operating point:
*   **Gate Oxide Overstress:** Checks if `|Vgs|, |Vgd|, |Vgb| > tox * 1e7` (10 MV/cm critical field).
*   **Hot Carrier Injection:** Calculates lateral channel field `E_parallel = (Vds - Vdsat)/Leff` and warns if it exceeds a critical value.
*   **Parasitic Bipolar Turn-on:** Warns if `Vbs` or `Vbd` exceeds ~0.7V.
*   **Self-Heating:** If thermal resistance `Rth0` is modeled, calculates junction temperature `Tj = Pdiss * Rth0 + Tambient` and checks against `Tmax`.

## 4. SPICE Device Integration

The BSIM4v7 model binds to Ngspice through the `SPICEdev` structure defined in `bsim4v7init.c`:

```c
SPICEdev BSIM4v7info = {
    .DEVpublic = {
        .name = "BSIM4v7",
        .description = "Berkeley Short Channel IGFET Model Version 4.7",
        .terms = 4, // D, G, S, B terminals
        .numNames = 4,
        .termNames = (char*[]){"d", "g", "s", "b"},
        .modType = BSIM4v7_MOD_B4V7,
    },
    .DEVparam = BSIM4v7param,
    .DEVmodParam = BSIM4v7mParam,
    .DEVload = BSIM4v7load,           // DC load function
    .DEVacLoad = BSIM4v7acLoad,       // AC load function (b4v7acld.c)
    .DEVaccept = NULL,
    .DEVdestroy = BSIM4v7destroy,
    .DEVmodDelete = BSIM4v7mDelete,
    .DEVdelete = BSIM4v7delete,
    .DEVsetic = BSIM4v7getic,
    .DEVask = BSIM4v7ask,
    .DEVmodAsk = BSIM4v7mAsk,
    .DEVpzLoad = BSIM4v7pzLoad,       // Pole-zero load (b4v7pzld.c)
    .DEVconvTest = BSIM4v7convTest,   // Convergence test
    .DEVfindBranch = NULL,
    .DEVtrunc = BSIM4v7trunc,         // LTE calculation
    .DEVnoise = BSIM4v7noise,         // Noise analysis (b4v7noi.c)
    .DEVsoaCheck = BSIM4v7soaCheck,   // SOA checking
    .DEVinstSize = sizeof(BSIM4v7instance),
    .DEVmodSize = sizeof(BSIM4v7model)
};
```

This structure provides Ngspice with a complete API to the BSIM4v7 model, enabling all analysis types (DC, AC, transient, noise, pole-zero) through standardized function pointers. The `DEVload` member specifically points to the `BSIM4v7load()` function in `b4v7ld.c`, which implements the DC physics model and matrix stamping described in this chapter.