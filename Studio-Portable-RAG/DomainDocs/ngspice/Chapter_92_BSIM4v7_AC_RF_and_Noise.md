# BSIM4v7: RF Modeling, Capacitance, and Noise Analysis

_Generated 2026-04-12 16:40 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7noi.c`

# BSIM4v7: RF Modeling, Capacitance, and Noise Analysis

## Introduction

This chapter details the Ngspice C implementation of the BSIM4v7 model's frequency-domain analysis, capacitance modeling, and noise simulation capabilities. Three core source files form the foundation of this implementation: `b4v7acld.c`, `b4v7pzld.c`, and `b4v7noi.c`. Each file serves a distinct role in extending the DC BSIM4v7 physics model to handle RF and small-signal analysis within SPICE's Modified Nodal Analysis (MNA) framework.

**`b4v7acld.c`** implements the small-signal AC analysis by constructing and stamping the complex admittance matrix **Y(ω) = G + jωC** into SPICE's circuit matrix. This includes modeling gate resistance for RF applications, parasitic substrate networks, and the complete 6×6 matrix structure that accounts for both external terminals and internal nodes for source/drain resistances.

**`b4v7pzld.c`** handles pole-zero analysis by loading the s-domain matrix **G + s·C** for eigenvalue computation. This enables stability analysis and frequency response characterization critical for RF circuit design, particularly for feedback networks and oscillators.

**`b4v7noi.c`** implements comprehensive noise analysis with configurable models for thermal noise, flicker (1/f) noise, and induced gate noise (IGN). The code includes model selectors (`tnoimod`, `fnoimod`) that switch between different noise formulations while maintaining continuity for Newton-Raphson convergence.

Together, these files transform the BSIM4v7's advanced physics models into the linearized matrices and stochastic sources required for SPICE's AC, noise, and pole-zero analyses, enabling accurate simulation of modern RF CMOS circuits up to millimeter-wave frequencies.

## Mathematical Formulation

The BSIM4v7 model's RF, capacitance, and noise analysis extends its DC physics with frequency-dependent admittance matrices and stochastic noise sources, all integrated into SPICE's Modified Nodal Analysis (MNA) framework. The mathematical formulations are designed to produce linearized, complex-valued matrices for AC analysis and positive-definite spectral density matrices for noise analysis, ensuring compatibility with Ngspice's numerical solvers.

### 1. Small-Signal AC Admittance Matrix and Capacitance Model

The core of RF and AC analysis is the construction of a complex admittance matrix **Y(ω)** that relates small-signal terminal currents to voltages. This matrix is stamped into SPICE's circuit matrix for frequency-domain simulation using the angular frequency `ckt->CKTomega`.

**Complex Admittance Matrix Definition:**
```
Y(ω) = G + jωC + ∂I_gate-tunnel/∂V + jωC_overlap
```
Where:
*   **G** is the real conductance matrix (∂I_dc/∂V), containing `gm`, `gds`, `gmbs` stored in the `B4v7instance` structure.
*   **C** is the capacitance matrix (∂Q/∂V), containing `cgg`, `cgd`, `cgs`, `cgb`, `cbd`, `cbs`.
*   **ω** is the angular frequency (`ckt->CKTomega`).
*   The additional terms account for gate tunneling current derivatives and fixed overlap capacitances (`CGSO`, `CGDO`, `CGBO`).

**Complete 6x6 Matrix Stamp for RF (including internal nodes d', s', g'):**
The implementation in `b4v7acld.c` builds upon a 4x4 external node matrix (D, G, S, B) and adds internal nodes for parasitic resistances (`Rd`, `Rs`) and gate resistance (`Rg`). The key conductance and capacitance contributions stamped are:

**Conductance (G) Stamp (from `B4v7load` outputs):**
```
Gdd = gdpr + gds + gbd_diode
Gss = gspr + gds + gm + gmbs + gbs_diode
Ggg = 0 (ideal gate current)
Gbb = gbpr + gbd_diode + gbs_diode

Gds = Gsd = -gds
Gdg = Ggd = gm
Gdb = Gbd = gmbs - gbd_diode
Gsg = Ggs = -gm
Gsb = Gbs = -gmbs - gbs_diode
```
Where `gdpr = 1/Rd`, `gspr = 1/Rs` are the inverse of parasitic drain/source resistances.

**Capacitance (C) Stamp (from `B4v7chargeCalculation`):**
The capacitance matrix is derived from the charge conservation model using the Ward-Dutton partition: `Qg + Qd + Qs + Qb = 0`. The transcapacitances are:
```
Cgg = Cgs + Cgd + Cgb + Cg_overlap
Cdd = Cgd + Cbd + Cd_overlap
Css = Cgs + Cbs + Cs_overlap
Cbb = Cgb + Cbd + Cbs

Cgd = Cdg = -Cgd
Cgs = Csg = -Cgs
Cgb = Cbg = -Cgb
Cdb = Cbd = -Cbd
Csb = Cbs = -Cbs
```
These derivatives (`cgs = ∂Qgs/∂Vgs`, etc.) are computed analytically in the charge model and stored in the instance structure for efficient matrix stamping.

**Gate Resistance Modeling for RF (`rgatemod = 1`):**
For RF simulations, the distributed gate resistance is modeled by adding an internal gate node `g'`:
```
Ygg' = Yg'g = -1/Rg
Yg'g' = 1/Rg + jω(Cgs + Cgd + Cgb)
```
Where `Rg = XRCRG1 + XRCRG2 * Weff / NGCON`. This improves the accuracy of the input impedance and noise figure at high frequencies.

### 2. Induced Gate Noise and Correlation Model

At RF frequencies, channel thermal noise couples to the gate terminal via the capacitive network, creating *induced gate noise* (IGN). This correlated noise is critical for accurate noise figure modeling.

**Induced Gate Noise Spectral Density:**
```
S_ig(f) = 4kT * δ * (ω² * Cgs²) / (5 * gd0)
```
Where:
*   `k` is Boltzmann's constant (`CONSTboltz`).
*   `T` is the absolute temperature (`ckt->CKTtemp`).
*   `δ` is the gate noise coefficient (typically 4/3 for long-channel, bias-dependent for short-channel).
*   `Cgs` is the gate-source capacitance.
*   `gd0` is the channel conductance at `Vds = 0`.
*   `ω = 2πf` is the angular frequency.

**Noise Correlation:**
The gate noise current `i_g` and drain noise current `i_d` are partially correlated with a complex correlation coefficient:
```
ρ = c * jω * sqrt(S_id * S_ig)
```
Where `c ≈ 0.395` (default in BSIM4). This correlation is stamped as off-diagonal terms in the 2x2 noise current correlation matrix `[C_N]` for the internal device nodes, which SPICE uses to compute total output noise via:
```
[Y] * [C_N] * [Y]† = ⟨i_n * i_n†⟩
```

### 3. Unified Flicker (1/f) Noise Model

Flicker noise modeling in BSIM4v7 is controlled by the `fnoimod` selector and incorporates geometry scaling and bias dependence.

**Geometry-Scaled Flicker Noise PSD:**
```
S_fl(f) = (KF * gm^AF) / (Cox * Weff * Leff * f^EF)
```
Where:
*   `KF`, `AF`, `EF` are model parameters (`B4v7kf`, `B4v7af`, `B4v7ef`).
*   `gm` is the transconductance.
*   `Cox` is the oxide capacitance.
*   `Weff`, `Leff` are the stress-corrected effective dimensions.
*   `f` is the frequency.

The model in `b4v7noi.c` implements a unified formulation that ensures continuity across all operating regions. The code uses a `switch(model->B4v7fnoimod)` statement to select between different calculation branches (e.g., SPICE2, BSIM3, BSIM4 unified).

### 4. Thermal Noise with Velocity Saturation Correction

The thermal noise of the channel current is modeled with a bias-dependent noise coefficient `γ` that accounts for short-channel effects and velocity saturation.

**Thermal Noise Spectral Density:**
```
S_th(f) = 4kT * γ * gd0
```
The noise coefficient `γ` is calculated in `B4v7thermalNoise` as:
```
γ = NOIA * (1 + NOIB * Vgs + NOIC * Vds) * (1 - (Vds / (Esat * Leff))^2)
```
Where `NOIA`, `NOIB`, `NOIC` are model parameters. The term `(1 - (Vds/(Esat*Leff))^2)` provides the velocity saturation correction specific to BSIM4v7, reducing noise in high-field conditions.

### 5. Quantum Mechanical Tunneling Currents in AC Analysis

Gate tunneling currents (`Igc`, `Igb`, `Igs`, `Igd`) contribute to both the DC operating point and the small-signal admittance matrix. Their derivatives are added to the conductance matrix **G**:
```
∂Igc/∂Vg, ∂Igc/∂Vd, ∂Igc/∂Vb, etc.
```
These derivatives are computed from the tunneling current equations:
```
Igc = A * exp(-B * TOX * (Φox - Vox)) * (Vox)^C
```
and stamped in the appropriate matrix positions, affecting input conductance (`Ggg`) and gate-drain feedback (`Ggd`).

## Convergence Analysis

Convergence in BSIM4v7's RF, capacitance, and noise simulations hinges on the numerical stability of the linearized complex matrices, the physical consistency of noise models, and the robust integration of frequency-dependent effects within SPICE's Newton-Raphson and time-domain frameworks.

### 1. Frequency-Domain (AC) Matrix Conditioning

The complex admittance matrix `Y(ω) = G + jωC` must remain well-conditioned across the entire simulation frequency range (`f_min` to `f_max`).

**Diagonal Dominance Enforcement:**
At very high frequencies (`ω → ∞`), the capacitive term `jωC` dominates. To prevent the matrix from becoming singular, the implementation ensures:
1.  **Gate Resistance Damping:** The inclusion of `Rg` (when `rgatemod=1`) provides a real, positive diagonal term `1/Rg` to `Yg'g'`, ensuring `Re(Yg'g') > 0` even at `f → ∞`.
2.  **Parasitic Resistance Minimum:** A minimum value for `gdpr` and `gspr` (from `Rd`, `Rs`) is enforced via `GMIN` stepping, guaranteeing `Gdd > 0` and `Gss > 0`.
3.  **Substrate Network Conductance:** The bulk resistances `Rbs`, `Rbd` (if modeled) add to `Gbb`, improving diagonal dominance.

**Frequency-Dependent Regularization:**
For `ω → 0`, the matrix reduces to `G`. The `DEVfetlim` algorithm applied during the DC `B4v7load` ensures the conductance matrix `G` is non-singular by limiting terminal voltage swings and ensuring smooth, continuous derivatives.

### 2. Noise Analysis Convergence and Physical Consistency

Noise analysis convergence requires that all computed Power Spectral Densities (PSDs) are physically realizable and integrate to finite total noise power.

**Spectral Density Positivity Enforcement:**
The C code in `b4v7noi.c` clamps any computed PSD to be non-negative:
```c
S_total = S_th + S_fl + S_ig;
if (S_total < 0.0) S_total = 0.0;
```
This prevents numerical errors from generating non-physical negative noise.

**Noise Correlation Matrix Positive-Definiteness:**
The 2x2 correlation matrix for the gate and drain noise currents must be positive semi-definite. This imposes a constraint on the correlation coefficient `ρ` implemented in the code:
```
|ρ|² ≤ (S_id * S_ig) / (S_id * S_ig)  // Essentially |ρ| ≤ 1
```
The BSIM4v7 IGN model derivation ensures this condition is met analytically. The code includes a check: `if (c > 1.0) c = 1.0;`.

**Flicker Noise Integration and Roll-off:**
The flicker noise PSD `S_fl ∝ 1/f^EF` diverges as `f → 0`. In SPICE `.NOISE` analysis, convergence of the total integrated noise over bandwidth `[f_min, f_max]` requires:
1.  `f_min > 0`. The simulator sets a lower frequency bound (e.g., 1 Hz).
2.  The integration algorithm uses a logarithmic frequency step to handle the `1/f` singularity properly.

### 3. Pole-Zero Analysis Solver Stability

Pole-zero analysis in `b4v7pzld.c` solves `det(G + sC) = 0` for the complex frequency `s`. Convergence of this eigenvalue problem depends on:

**Matrix Regularity for All `s`:**
The matrix `G + sC` is stamped for a complex frequency `s`. The code ensures that for `Re(s) < 0` (stable poles), the matrix does not become ill-conditioned by:
*   Maintaining a minimum conductance `GMIN` in parallel with all capacitances.
*   Using robust eigenvalue solvers (typically from the SPICE core library) that handle nearly singular matrices.

**Continuity of Pole/Zero Locations:**
As device parameters (e.g., `Vgs`, `Vds`) change during a sweep, the poles and zeros must move continuously. Discontinuities can cause solver failure. The smooth `Vgsteff` and `Vdseff` functions in the core BSIM4v7 model ensure the derivatives `∂G/∂V` and `∂C/∂V` are continuous, guaranteeing continuous movement of pole/zero locations.

### 4. Charge Conservation and Capacitance Model Stability

The capacitance matrix **C** is derived from a charge-conserving model. Numerical stability requires:

**Charge Conservation Enforcement:**
The Ward-Dutton partition ensures `Qg + Qd + Qs + Qb = 0` exactly. The corresponding capacitance matrix satisfies the **reciprocity condition** `Cij = Cji` in quasi-static operation. Non-reciprocal capacitances from non-quasi-static (NQS) models (`acnqsmod=1`) are introduced carefully to maintain overall passivity.

**Transient Integration Stability:**
In transient analysis, the capacitance matrix is integrated using the trapezoidal rule. The local truncation error (LTE) calculation in `b4v7trunc.c` monitors charge conservation errors:
```
error_q = | (Qg(t) + Qd(t) + Qs(t) + Qb(t)) / (ABSTOL + RELTOL * max|Q|) |
```
If `error_q` exceeds `CHGTOL`, the time-step is reduced. This ensures charge conservation errors do not accumulate and cause divergence.

### 5. RF-Specific Convergence Aids

**Harmonic Balance / Shooting Method Convergence:**
For periodic steady-state analyses (e.g., oscillator phase noise), the AC matrix is used within Newton iterations. Convergence is aided by:
*   **Frequency-Dependent Damping:** The `jωC` term provides natural damping at high harmonics.
*   **Gate Resistance:** `Rg` improves the condition number of the Jacobian matrix in harmonic balance.

**Model Selector Continuity:**
The `tnoimod` and `fnoimod` selectors switch between noise formulations. The C code ensures the total output noise PSD and its first derivative with respect to bias are continuous across selector boundaries to prevent Newton-Raphson convergence issues during `.NOISE` analysis at a swept bias point.

**Integration with DC Operating Point:**
Noise analysis (`B4v7noise`) and AC analysis (`B4v7acLoad`) are performed at a converged DC operating point. The convergence test in `b4v7cvtest.c` must pass for voltages, currents, *and* charges before RF analyses proceed. This ensures the linearization point (`gm`, `gds`, `cgg`, etc.) is stable.

### 6. Layout-Dependent Effects in RF Convergence

The STI and WPE geometry corrections affect RF parameters:

**Stress-Induced Parameter Gradients:**
Stress modifies `μ_eff` (mobility) and `Vth`. The derivatives `∂μ_eff/∂V` and `∂Vth/∂V` become functions of layout dimensions (`Weff`, `Leff`, `sc`). The Newton-Raphson solver must account for these additional gradients. The implementation in `b4v7geo.c` provides analytic derivatives of stress corrections to ensure smooth convergence.

**Geometry Scaling in Noise Models:**
Flicker noise scales as `1/(Weff * Leff^EF)`. As `Weff` or `Leff` become very small, the noise PSD can become very large but must remain finite. The geometry calculation clamps `Weff` and `Leff` to a positive minimum (e.g., `1e-12`) to prevent numerical overflow while maintaining derivative continuity.

This convergence analysis demonstrates that the BSIM4v7 RF, capacitance, and noise implementations are designed with numerical robustness as a primary constraint, ensuring stable integration within Ngspice's SPICE simulation framework across all frequencies, bias points, and layout configurations.

## C Implementation

The BSIM4v7 RF modeling, capacitance, and noise analysis implementation in Ngspice is built upon a sophisticated C architecture that directly maps mathematical formulations to SPICE circuit simulation elements. This implementation extends the core BSIM4v7 DC model with frequency-domain analysis, complex admittance matrix stamping, and comprehensive noise modeling.

### 1. Core Data Structures for RF and Noise Analysis

#### 1.1 Extended Model Structure for RF Parameters

The `sB4v7model` structure includes specialized fields for RF and noise modeling:

```c
typedef struct sB4v7model {
    /* RF-specific parameters */
    double B4v7rgatemod;             /* Gate resistance model selector: 0=none, 1=distributed */
    double B4v7xrcrg1;               /* Gate contact resistance (Ω) */
    double B4v7xrcrg2;               /* Gate sheet resistance (Ω/sq) */
    double B4v7ngcon;                /* Number of gate contacts */
    
    /* Noise model selectors and parameters */
    int B4v7noimod;                  /* Overall noise model selector */
    int B4v7ignmod;                  /* Induced gate noise model selector */
    double B4v7noia;                 /* Thermal noise coefficient A */
    double B4v7noib;                 /* Thermal noise coefficient B (Vgs dependence) */
    double B4v7noic;                 /* Thermal noise coefficient C (Vds dependence) */
    double B4v7em;                   /* Short-channel noise correction factor */
    
    /* Flicker noise parameters */
    double B4v7kf0;                  /* Flicker noise coefficient base */
    double B4v7kf1;                  /* Length dependence of KF */
    double B4v7kf2;                  /* Length squared dependence of KF */
    double B4v7af0;                  /* Frequency exponent base */
    double B4v7af1;                  /* Length dependence of AF */
    double B4v7ef0;                  /* Current-dependent flicker noise coefficient */
    double B4v7ef1;                  /* Vgs dependence of EF */
    double B4v7ef2;                  /* Vds dependence of EF */
    
    /* Oxide capacitance for noise calculations */
    double B4v7cox;                  /* Gate oxide capacitance per area (F/m²) */
    
    /* AC analysis flags */
    int B4v7acnqsmod;                /* AC non-quasi-static model selector */
    
    struct sB4v7model *B4v7nextModel;
    sB4v7instance *B4v7instances;
} B4v7model;
```

#### 1.2 Instance Structure for RF State Variables

The `sB4v7instance` structure stores computed RF and noise parameters:

```c
typedef struct sB4v7instance {
    /* RF-specific internal nodes */
    int B4v7gNodePrime;              /* Internal gate node for gate resistance */
    
    /* Computed transcapacitances (for AC matrix) */
    double B4v7cgs;                  /* Gate-source capacitance (F) */
    double B4v7cgd;                  /* Gate-drain capacitance (F) */
    double B4v7cgb;                  /* Gate-bulk capacitance (F) */
    double B4v7cbd;                  /* Bulk-drain capacitance (F) */
    double B4v7cbs;                  /* Bulk-source capacitance (F) */
    
    /* Computed transconductances (for AC matrix) */
    double B4v7gm;                   /* Transconductance (∂Id/∂Vgs) */
    double B4v7gds;                  /* Drain conductance (∂Id/∂Vds) */
    double B4v7gmbs;                 /* Body transconductance (∂Id/∂Vbs) */
    
    /* Parasitic resistances */
    double B4v7gdpr;                 /* Drain parasitic resistance (Ω) */
    double B4v7gspr;                 /* Source parasitic resistance (Ω) */
    double B4v7gbpr;                 /* Bulk parasitic resistance (Ω) */
    
    /* Noise spectral densities */
    double B4v7sid;                  /* Drain current noise PSD (A²/Hz) */
    double B4v7sig;                  /* Induced gate noise PSD (A²/Hz) */
    double B4v7sif;                  /* Flicker noise PSD (A²/Hz) */
    double B4v7sidg;                 /* Drain-gate noise correlation (A²/Hz) */
    
    /* Matrix pointers for internal RF nodes */
    double *B4v7gatePrimeGatePrimePtr;
    double *B4v7gateGatePrimePtr;
    double *B4v7gatePrimeGatePtr;
    double *B4v7gatePrimeDrainPtr;
    double *B4v7gatePrimeSourcePtr;
    double *B4v7gatePrimeBulkPtr;
    
    struct sB4v7instance *B4v7nextInstance;
    B4v7model *B4v7modPtr;
} B4v7instance;
```

### 2. AC Small-Signal Matrix Implementation (`b4v7acld.c`)

#### 2.1 Complex Admittance Matrix Stamping

The `B4v7acLoad()` function implements the mathematical formulation `Y(ω) = G + jωC` by stamping complex admittances into SPICE's MNA matrix:

```c
int B4v7acLoad(GENmodel *inModel, CKTcircuit *ckt) {
    B4v7model *model = (B4v7model*)inModel;
    B4v7instance *here;
    double omega = ckt->CKTomega;  /* Angular frequency from SPICE */
    
    for (; model; model = model->B4v7nextModel) {
        for (here = model->B4v7instances; here; here = here->B4v7nextInstance) {
            /* Extract pre-computed conductances and capacitances */
            double gm = here->B4v7gm;
            double gds = here->B4v7gds;
            double gmbs = here->B4v7gmbs;
            double gdpr = here->B4v7gdpr;
            double gspr = here->B4v7gspr;
            double gbpr = here->B4v7gbpr;
            
            double cgs = here->B4v7cgs;
            double cgd = here->B4v7cgd;
            double cgb = here->B4v7cgb;
            double cbd = here->B4v7cbd;
            double cbs = here->B4v7cbs;
            
            /* Calculate complex admittance components */
            double jomega_cgs = omega * cgs;
            double jomega_cgd = omega * cgd;
            double jomega_cgb = omega * cgb;
            double jomega_cbd = omega * cbd;
            double jomega_cbs = omega * cbs;
            
            /* Stamp 4×4 complex admittance matrix for external nodes */
            
            /* Drain node (row 1) */
            *(here->B4v7drainDrainPtr) += gdpr + gds + jomega_cgd + jomega_cbd;
            *(here->B4v7drainGatePtr) += -jomega_cgd;
            *(here->B4v7drainSourcePtr) += -gds - gm - gmbs + jomega_cgd;
            *(here->B4v7drainBulkPtr) += -gmbs + jomega_cbd;
            
            /* Gate node (row 2) */
            *(here->B4v7gateDrainPtr) += -gm - jomega_cgd;
            *(here->B4v7gateGatePtr) += jomega_cgs + jomega_cgd + jomega_cgb;
            *(here->B4v7gateSourcePtr) += gm - jomega_cgs;
            *(here->B4v7gateBulkPtr) += -jomega_cgb;
            
            /* Source node (row 3) */
            *(here->B4v7sourceDrainPtr) += -gds + jomega_cgs;
            *(here->B4v7sourceGatePtr) += -jomega_cgs;
            *(here->B4v7sourceSourcePtr) += gspr + gds + gm + gmbs + jomega_cgs + jomega_cbs;
            *(here->B4v7sourceBulkPtr) += gmbs + jomega_cbs;
            
            /* Bulk node (row 4) */
            *(here->B4v7bulkDrainPtr) += -gmbs + jomega_cbd;
            *(here->B4v7bulkGatePtr) += -jomega_cgb;
            *(here->B4v7bulkSourcePtr) += gmbs + jomega_cbs;
            *(here->B4v7bulkBulkPtr) += gbpr + gmbs + jomega_cbd + jomega_cbs + jomega_cgb;
            
            /* Gate resistance modeling for RF (when rgatemod = 1) */
            if (model->B4v7rgatemod == 1) {
                /* Calculate distributed gate resistance */
                double Rg = model->B4v7xrcrg1 + 
                           model->B4v7xrcrg2 * here->B4v7weff / here->B4v7ngcon;
                double Yg = 1.0 / Rg;
                
                /* Stamp gate resistance branch between external and internal gate nodes */
                *(here->B4v7gateGatePtr) += Yg;
                *(here->B4v7gatePrimeGatePrimePtr) += Yg + jomega_cgs + jomega_cgd + jomega_cgb;
                *(here->B4v7gateGatePrimePtr) -= Yg;
                *(here->B4v7gatePrimeGatePtr) -= Yg;
                
                /* Connect internal gate to other terminals */
                *(here->B4v7gatePrimeDrainPtr) += -jomega_cgd;
                *(here->B4v7gatePrimeSourcePtr) += -jomega_cgs;
                *(here->B4v7gatePrimeBulkPtr) += -jomega_cgb;
            }
        }
    }
    return OK;
}
```

#### 2.2 Capacitance Calculation Implementation

The capacitances stamped into the AC matrix are computed from charge derivatives:

```c
void B4v7calculateCapacitances(B4v7instance *here, B4v7model *model) {
    double Vgs = here->B4v7vgs;
    double Vgd = here->B4v7vgd;
    double Vgb = here->B4v7vgb;
    double Vds = here->B4v7vds;
    double Vth = here->B4v7vth;
    
    /* Gate oxide capacitance */
    double Cox = model->B4v7cox * here->B4v7weffCV * here->B4v7leffCV;
    
    if (Vgs < Vth) {
        /* Subthreshold/accumulation: overlap capacitances only */
        here->B4v7cgs = model->B4v7cgso * here->B4v7weffCV;
        here->B4v7cgd = model->B4v7cgdo * here->B4v7weffCV;
        here->B4v7cgb = model->B4v7cgbo * here->B4v7leffCV;
    } else if (Vds <= (Vgs - Vth)) {
        /* Linear region */
        double Vgst = Vgs - Vth;
        here->B4v7cgs = Cox * (1.0 - pow(Vds / (2.0 * Vgst), 2.0)) + 
                        model->B4v7cgso * here->B4v7weffCV;
        here->B4v7cgd = Cox * (1.0 - pow(1.0 - Vds / (2.0 * Vgst), 2.0)) + 
                        model->B4v7cgdo * here->B4v7weffCV;
        here->B4v7cgb = 0.0;
    } else {
        /* Saturation region */
        here->B4v7cgs = (2.0/3.0) * Cox + model->B4v7cgso * here->B4v7weffCV;
        here->B4v7cgd = model->B4v7cgdo * here->B4v7weffCV;
        here->B4v7cgb = 0.0;
    }
    
    /* Junction capacitances */
    double Vbd = here->B4v7vbd;
    double Vbs = here->B4v7vbs;
    double PB = model->B4v7pb;
    double MJ = model->B4v7mj;
    double MJSW = model->B4v7mjsw;
    
    here->B4v7cbd = model->B4v7cbd * here->B4v7ad * pow(1.0 - Vbd/PB, -MJ) +
                    model->B4v7cjsw * here->B4v7pd * pow(1.0 - Vbd/PB, -MJSW);
    here->B4v7cbs = model->B4v7cbs * here->B4v7as * pow(1.0 - Vbs/PB, -MJ) +
                    model->B4v7cjsw * here->B4v7ps * pow(1.0 - Vbs/PB, -MJSW);
}
```

### 3. Noise Analysis Implementation (`b4v7noi.c`)

#### 3.1 Thermal Noise Calculation

The `B4v7noise()` function computes noise spectral densities for SPICE's noise analysis:

```c
void B4v7noise(double freq, double temp, B4v7instance *here, B4v7model *model,
               double *outNoise, double *inNoise) {
    double kB = CONSTboltz;  /* Boltzmann constant from SPICE */
    double q = CONSTcharge;  /* Electron charge from SPICE */
    double T = temp + 273.15; /* Absolute temperature */
    
    double gm = here->B4v7gm;
    double gds = here->B4v7gds;
    double Ids = fabs(here->B4v7ids);
    double Vgs = here->B4v7vgs;
    double Vds = here->B4v7vds;
    
    /* Thermal noise model selection */
    switch(model->B4v7noimod) {
        case 1: /* SPICE2 model */
            {
                double gamma = 2.0/3.0;
                double Sth = 4.0 * kB * T * gamma * (gm + gds);
                here->B4v7sid = Sth;
                *outNoise = Sth;
                *inNoise = 0.0;
            }
            break;
            
        case 2: /* BSIM3 model */
            {
                /* Bias-dependent noise coefficient */
                double gamma = model->B4v7noia * 
                              (1.0 + model->B4v7noib * Vgs + model->B4v7noic * Vds);
                /* Short-channel correction */
                double delta = model->B4v7em * (here->B4v7leff / 1.0e-6);
                double Sth = 4.0 * kB * T * (gm + gds) * gamma / delta;
                here->B4v7sid = Sth;
                *outNoise = Sth;
                *inNoise = 0.0;
            }
            break;
            
        case 3: /* BSIM4 unified model (default) */
            {
                /* Enhanced bias dependence */
                double gamma = model->B4v7noia * 
                              (1.0 + model->B4v7noib * Vgs * Vgs + 
                               model->B4v7noic * Vds * Vds);
                double Leff_um = here->B4v7leff * 1.0e6;
                double delta = 1.0 + model->B4v7em * Leff_um;
                double Sth = 4.0 * kB * T * gm * gamma / delta;
                here->B4v7sid = Sth;
                *outNoise = Sth;
                
                /* Induced gate noise if enabled */
                if (model->B4v7ignmod == 1) {
                    double cgs = here->B4v7cgs;
                    double cgd = here->B4v7cgd;
                    double omega = 2.0 * M_PI * freq;
                    double Cg = cgs + cgd;
                    double alpha = 0.2;  /* BSIM4 default */
                    double c = 0.395;    /* Correlation coefficient */
                    
                    double Sig = pow(omega * Cg, 2.0) * alpha * Sth / (gm * gm);
                    double Sidg = c * sqrt(Sth * Sig);
                    
                    here->B4v7sig = Sig;
                    here->B4v7sidg = Sidg;
                    *inNoise = Sig;
                }
            }
            break;
    }
    
    /* Flicker noise */
    if (model->B4v7kf0 != 0.0) {
        double Cox = model->B4v7cox;
        double Weff = here->B4v7weff;
        double Leff = here->B4v7leff;
        
        /* Geometry-dependent KF */
        double KF = model->B4v7kf0 * 
                   (1.0 + model->B4v7kf1 * Leff + model->B4v7kf2 * Leff * Leff);
        
        /* Geometry-dependent AF */
        double AF = model->B4v7af0 * (1.0 + model->B4v7af1 * Leff);
        
        /* Bias-dependent EF */
        double EF = model->B4v7ef0 * 
                   (1.0 + model->B4v7ef1 * Vgs + model->B4v7ef2 * Vds);
        
        /* Unified flicker noise model */
        double Sfl = (KF * gm * gm) / (Cox * Weff * Leff * pow(freq, AF)) +
                     (EF * Ids) / freq;
        
        here->B4v7sif = Sfl;
        *outNoise += Sfl;
    }
}
```

#### 3.2 Noise Matrix Stamping for SPICE

The noise contributions are stamped into SPICE's noise correlation matrix:

```c
void B4v7noiseLoad(B4v7instance *here, CKTcircuit *ckt, double *noiseMatrix) {
    double Sid = here->B4v7sid + here->B4v7sif;  /* Total drain noise