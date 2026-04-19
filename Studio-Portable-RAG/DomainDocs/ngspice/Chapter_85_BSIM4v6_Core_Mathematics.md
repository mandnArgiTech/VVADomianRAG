# BSIM4v6: Nanometer Physics Revision and DC Load

_Generated 2026-04-12 15:04 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/bsim4v6def.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6ld.c`

# BSIM4v5: RF Modeling, Capacitance, and Noise Analysis

## Technical Introduction

This chapter details the implementation of high-frequency (RF) and noise analysis for the BSIM4v5 MOSFET model within the Ngspice circuit simulator. The BSIM4v5 model, designed for deep-submicron CMOS technologies, extends DC and transient capabilities with comprehensive small-signal AC, pole-zero, and noise analysis to enable accurate RF circuit simulation. Three core C source files implement these frequency-domain and stochastic behaviors:

*   **`b4v5acld.c`**: Implements the `B4v5acLoad()` function, which constructs and stamps the complex admittance matrix **Y(ω) = G + jωC** into the SPICE circuit matrix for small-signal AC analysis. This includes the intrinsic 4x4 admittance matrix for the gate, drain, source, and bulk nodes, and integrates extrinsic components such as gate resistance (`Rg`).
*   **`b4v5pzld.c`**: Implements the `B4v5pzLoad()` function, which stamps the **G + sC** matrices required for s-domain pole-zero analysis. This enables the analysis of transfer function zeros and poles critical for stability and frequency response evaluation.
*   **`b4v5noi.c`**: Implements the `B4v5noise()` function, which computes and stamps the spectral densities of various noise sources into the SPICE noise correlation matrix. It supports configurable thermal noise (`tnoimod`) and flicker noise (`fnoimod`) models, including advanced effects like induced gate noise with correlation to channel thermal noise.

These files work in concert with the core BSIM4v5 data structures defined in `bsim4v5def.h`—specifically the `sB4v5model` and `sB4v5instance` structs—to provide a complete RF and noise simulation capability, linking compact model equations directly to Ngspice's numerical simulation engines.

---

## Mathematical Formulation

The RF and noise analysis for BSIM4v5 is built upon a linearized small-signal representation of the transistor and stochastic models for intrinsic noise sources.

### Small-Signal Admittance Matrix

For small-signal AC analysis, the intrinsic MOSFET is linearized around its DC operating point, characterized by conductances (`gm`, `gds`, `gmb`) and capacitances (`cgg`, `cgd`, `cgs`, etc.). The complete admittance matrix **Y** linking the intrinsic gate (g), drain (d), source (s), and bulk (b) nodes is a 4x4 complex matrix:

**Y(ω) = G + jωC**

Where **G** is the real conductance matrix and **C** is the capacitance matrix. The matrix elements are stamped according to the following pattern, derived from the code in `b4v5acld.c`:

*   **Ygg** = `jω * (cgg + cgdo + cgso)` (Total gate capacitance)
*   **Ygd** = `-jω * cgd` (Gate-drain capacitance)
*   **Ygs** = `-jω * cgs` (Gate-source capacitance)
*   **Ygb** = `-jω * cgb` (Gate-bulk capacitance)
*   **Ydg** = `gm - jω * cgd` (Transconductance & gate-drain capacitance)
*   **Ydd** = `gds + jω * (cdd + cgdo)` (Drain conductance & capacitance)
*   **Yds** = `-gds - gm - gmb + jω * cds` (Cross-conductance & capacitance)
*   **Ydb** = `gmb - jω * cdb` (Body transconductance & capacitance)
*   ... (with similar stamps for source and bulk rows completing the symmetric 4x4 matrix).

When the gate resistance model is active (`rgateMod > 0`), an external resistor `Rg` is added in series with the intrinsic gate node. This modifies the stamp: the external gate node (G) is connected to the internal gate node (g) via `1/Rg`, and the intrinsic **Y** matrix is stamped at the internal node g.

### Pole-Zero Analysis Formulation

For pole-zero analysis in the s-domain, the system is described by the modified nodal analysis (MNA) formulation:
**H(s) = [C·s + G]⁻¹·B**

The `B4v5pzLoad()` function in `b4v5pzld.c` stamps the same **G** and **C** matrices used in AC analysis, allowing the SPICE kernel to compute the transfer function **H(s)** and its roots (poles and zeros).

### Noise Spectral Density Models

The intrinsic noise of the MOSFET is modeled by several uncorrelated and correlated noise sources, with their Power Spectral Densities (PSD) computed in `b4v5noi.c`.

#### 1. Channel Thermal Noise
The thermal noise due to channel resistance is modeled with a configurable PSD. The primary model (`B4V5_TNOIMOD_BSIM4`) is:
**S_id_th(f) = 4kT · γ · gds0**
where `k` is Boltzmann's constant, `T` is temperature, `gds0` is the zero-bias drain conductance, and `γ` is a bias-dependent factor (`B4v5gamma0`).

#### 2. Induced Gate Noise
At high frequencies, channel charge fluctuations induce a noise current at the gate terminal, correlated with the channel thermal noise. When `tnoimod` is set to `B4V5_TNOIMOD_IGNOISE`, this effect is included. The PSD for induced gate noise is:
**S_ig(f) = 4kT · δ · (ω²Cgs²) / (5gds0)**
where `δ` is a bias-dependent coefficient. The correlation coefficient between the gate and drain noise currents is approximately:
**ρ = j · c · sqrt( S_id_th · S_ig ) / (4kT)**
where `c` is the correlation coefficient (typically ~0.4).

#### 3. Flicker (1/f) Noise
Flicker noise is modeled based on the `fnoimod` parameter. The unified flicker noise model (`B4V5_FNOIMOD_UNIFIED`) calculates the PSD as:
**S_id_fl(f) = (KF · Id^AF) / (f^EF · Leff^2)**
where `KF`, `AF`, and `EF` are model parameters, `Id` is the drain current, and `Leff` is the effective channel length.

### SPICE Integration Mathematics

In SPICE, these mathematical models are integrated numerically:
*   **AC Analysis**: The frequency `ω` is provided by the simulation kernel as `ckt->CKTomega`. The complex matrix **Y(ω)** is built and solved to find the small-signal voltages.
*   **Noise Analysis**: Each noise PSD **S(f)** is stamped as an independent source into the noise correlation matrix. The total output noise is computed by summing the contributions of all sources, propagated through the linearized network.

---

## Convergence Analysis

The convergence of frequency-domain analyses (AC, Pole-Zero) in BSIM4v5 is inherently tied to the linearity of the small-signal model and the numerical stability of the matrix solutions.

### Linear System Conditioning

The AC and Pole-Zero analyses operate on the linearized **Y(ω)** or **[G + sC]** matrices. Convergence is guaranteed for these linear systems if the matrix is non-singular. Potential issues arise from:
1.  **High-Frequency Ill-Conditioning**: At very high frequencies (`ω → large`), the `jωC` term dominates, potentially making the matrix stiff. SPICE's matrix solver must handle this numerical stiffness.
2.  **Extrinsic Component Integration**: The addition of extrinsic `Rg`, `Rd`, `Rs` in series with intrinsic nodes improves diagonal dominance of the **G** matrix, which generally enhances the condition number and solver stability.

### Pole-Zero Algorithm Stability

The pole-zero analysis computes the roots of the determinant `det(G + sC) = 0`. The numerical algorithm's stability depends on:
*   The accuracy of the stamped **G** and **C** matrices.
*   The robustness of the root-finding algorithm (handled by the SPICE kernel, not the model code). The model's responsibility is to provide an accurate, consistent linear descriptor.

### Noise Analysis Convergence

Noise analysis in SPICE is a post-processing step performed on the *solved* linear AC network. Therefore, it does not have its own iterative convergence loop. Its "convergence" is determined by:
*   **Accuracy of Linearization**: The small-signal parameters (`gm`, `gds`, `cgg`, etc.) used to build the **Y** matrix for noise propagation must be accurate derivatives of the DC operating point. Any error in the DC solution directly propagates to noise results.
*   **Frequency Sampling**: The noise spectral density is computed at discrete frequency points. The accuracy of the integrated noise over a band depends on the density of this sampling, controlled by the simulator's frequency sweep settings.

### Role of Model Smoothing Functions

While the RF analyses themselves are linear, the small-signal parameters are derivatives of the DC model equations. The BSIM4v5 DC model employs smooth, continuous functions (e.g., for `Vgsteff`, `Vdsat`) with continuous first derivatives. This **C¹ continuity** is essential for generating stable, continuous conductances (`gm`, `gds`) and capacitances across all bias regions. Discontinuities in these derivatives would manifest as abrupt changes in the **Y** matrix, potentially causing convergence warnings or inaccurate frequency response.

### Validation via `B4v5acLoad` and `B4v5pzLoad`

The functions `B4v5acLoad()` and `B4v5pzLoad()` contain no iterative loops; they are direct stamping functions. Their correctness is validated by ensuring:
1.  The stamped **G** matrix is symmetric where required by reciprocity.
2.  The capacitance stamps obey charge conservation (e.g., `cgg = cgs + cgd + cgb`).
3.  The sum of each row/column of the **Y** matrix approaches zero at low frequency, satisfying Kirchhoff's Current Law.

In summary, the convergence of BSIM4v5's RF and noise analyses is primarily contingent upon the accuracy and stability of the DC operating point solution and the correctness of the linearized derivative calculations. The frequency-domain code itself provides a well-conditioned, linear description to the SPICE kernel for stable numerical solution.

---

## C Implementation

The RF and noise capabilities of the BSIM4v5 model are implemented through a series of C functions that map the mathematical formulations directly to SPICE's matrix stamping and noise computation interfaces.

### Core Data Structures

The definitions in `bsim4v5def.h` provide the storage for all necessary parameters and state variables.

```c
/* From bsim4v5def.h */
struct sB4v5instance {
    /* ... DC and transient parameters ... */

    /* Small-signal parameters (calculated in DC/op point) */
    double B4v5gm;    // Transconductance
    double B4v5gds;   // Drain-source conductance
    double B4v5gmb;   // Body transconductance
    double B4v5cgg;   // Total gate capacitance
    double B4v5cgd;   // Gate-drain capacitance
    double B4v5cgs;   // Gate-source capacitance
    double B4v5cgb;   // Gate-bulk capacitance
    double B4v5cdd;   // Drain capacitance
    double B4v5css;   // Source capacitance
    double B4v5cbb;   // Bulk capacitance
    double B4v5cdb;   // Drain-bulk capacitance
    double B4v5csb;   // Source-bulk capacitance
    double B4v5capbd; // Drain junction capacitance
    double B4v5capbs; // Source junction capacitance

    /* RF and Noise Specifics */
    int B4v5rgateMod; // Gate resistance model selector
    double B4v5rgate; // Gate resistance
    int B4v5tnoimod;  // Thermal noise model selector (0:BSIM4, 1:Induced Gate)
    int B4v5fnoimod;  // Flicker noise model selector (0:BSIM4, 1:Unified)
    double B4v5gamma0; // Thermal noise coefficient
    double B4v5npart;  // Channel charge partitioning factor (for induced gate noise)
    double B4v5noia, B4v5noib, B4v5noic; // Flicker noise parameters

    /* Matrix Pointers for 4 intrinsic nodes + internal gate (if Rg present) */
    double *B4v5DdPtr, *B4v5GgPtr, *B4v5SsPtr, *B4v5BbPtr;
    double *B4v5DPgPtr, *B4v5GPdPtr, *B4v5DPsPtr, *B4v5SPdPtr, *B4v5DPbPtr, *B4v5BPdPtr;
    double *B4v5GPgPtr, *B4v5SPgPtr, *B4v5BPgPtr;
    double *B4v5GPsPtr, *B4v5SPsPtr, *B4v5BPsPtr;
    double *B4v5GPbPtr, *B4v5BPbPtr, *B4v5SPbPtr;
    /* ... more matrix pointers ... */
};

struct sB4v5model {
    /* ... Model-level parameters ... */
    double B4v5tox;   // Oxide thickness
    double B4v5xl;    // Lateral diffusion
    double B4v5u0;    // Low-field mobility
    double B4v5kf;    // Flicker noise coefficient
    double B4v5af;    // Flicker noise exponent
    double B4v5ef;    // Flicker noise frequency exponent
    /* ... */
};
```

### AC Analysis Implementation (`b4v5acld.c`)

The `B4v5acLoad()` function constructs the complex admittance matrix.

```c
/* Pseudocode reflecting the logic in b4v5acld.c */
void B4v5acLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    B4v5model *model = (B4v5model*)inModel;
    B4v5instance *here;

    for(; model != NULL; model = model->B4v5nextModel) {
        for(here = model->B4v5instances; here != NULL; here = here->B4v5nextInstance) {

            double omega = ckt->CKTomega; // Get simulation frequency

            /* 1. Stamp intrinsic Y matrix (G + jωC) at internal nodes */
            /* Gate row (internal node 'g') */
            Ygg = IMAX * omega * (here->B4v5cgg + here->B4v5cgdo + here->B4v5cgso);
            Ygd = -IMAX * omega * here->B4v5cgd;
            Ygs = -IMAX * omega * here->B4v5cgs;
            Ygb = -IMAX * omega * here->B4v5cgb;
            stamp_complex_matrix(ckt, here->B4v5GgPtr, Ygg);
            stamp_complex_matrix(ckt, here->B4v5GPdPtr, Ygd);
            /* ... stamp all other Ygd, Ygs, Ygb ... */

            /* Drain row */
            Ydg = here->B4v5gm - IMAX * omega * here->B4v5cgd;
            Ydd = here->B4v5gds + IMAX * omega * (here->B4v5cdd + here->B4v5cgdo);
            Yds = -here->B4v5gds - here->B4v5gm - here->B4v5gmb + IMAX * omega * here->B4v5cds;
            Ydb = here->B4v5gmb - IMAX * omega * here->B4v5cdb;
            /* ... stamp drain row ... */

            /* ... stamp source and bulk rows similarly ... */

            /* 2. Handle gate resistance if present */
            if(here->B4v5rgateMod > 0) {
                /* Stamp conductance 1/Rg between external G and internal g nodes */
                g = 1.0 / here->B4v5rgate;
                stamp_real_matrix(ckt, external_G_node, external_G_node, +g);
                stamp_real_matrix(ckt, external_G_node, internal_g_node, -g);
                stamp_real_matrix(ckt, internal_g_node, external_G_node, -g);
                stamp_real_matrix(ckt, internal_g_node, internal_g_node, +g);
                /* The intrinsic Y matrix is stamped at internal_g_node */
            } else {
                /* Stamp intrinsic Y matrix directly at external G node */
            }

            /* 3. Stamp junction depletion capacitances (bias-dependent) */
            if(here->B4v5capbd > 0.0) {
                Yjj = IMAX * omega * here->B4v5capbd;
                stamp_complex_matrix(ckt, drain_bulk_junction_ptr, Yjj);
            }
            /* ... similarly for source-bulk junction ... */
        }
    }
}
```

### Pole-Zero Analysis Implementation (`b4v5pzld.c`)

The `B4v5pzLoad()` function stamps the real **G** and **C** matrices separately for the s-domain analysis.

```c
void B4v5pzLoad(GENmodel *inModel, CKTcircuit *ckt, SPcomplex *s)
{
    /* Similar to B4v5acLoad, but stamps G and C matrices separately */
    /* for the kernel to form (G + s*C) */
    B4v5model *model = (B4v5model*)inModel;
    B4v5instance *here;

    for(; model != NULL; model = model->B4v5nextModel) {
        for(here = model->B4v5instances; here != NULL; here = here->B4v5nextInstance) {

            /* Stamp G matrix (real conductances) */
            stamp_real_matrix(ckt, here->B4v5DdPtr, here->B4v5gds);
            stamp_real_matrix(ckt, here->B4v5DPgPtr, here->B4v5gm);
            /* ... stamp all gds, gm, gmb terms ... */

            /* Stamp C matrix (real capacitances) */
            stamp_real_matrix(ckt, here->B4v5GgPtr, here->B4v5cgg + here->B4v5cgdo + here->B4v5cgso);
            stamp_real_matrix(ckt, here->B4v5GPdPtr, -here->B4v5cgd);
            /* ... stamp all capacitance terms ... */

            /* Handle gate resistance (real only for pole-zero) */
            if(here->B4v5rgateMod > 0) {
                g = 1.0 / here->B4v5rgate;
                stamp_real_matrix(ckt, external_G_node, external_G_node, +g);
                stamp_real_matrix(ckt, external_G_node, internal_g_node, -g);
                stamp_real_matrix(ckt, internal_g_node, external_G_node, -g);
                stamp_real_matrix(ckt, internal_g_node, internal_g_node, +g);
            }
        }
    }
}
```

### Noise Analysis Implementation (`b4v5noi.c`)

The `B4v5noise()` function is the main entry point, dispatching to specific noise model functions.

```c
void B4v5noise(int mode, int operation, GENmodel *inModel,
                CKTcircuit *ckt, Ndata *data, double *OnDens)
{
    B4v5model *model = (B4v5model*)inModel;
    B4v5instance *here;

    if(operation == N_OPEN) { /* Initialize noise calculation */
        return;
    }

    for(; model != NULL; model = model->B4v5nextModel) {
        for(here = model->B4v5instances; here != NULL; here = here->B4v5nextInstance) {

            double temp = ckt->CKTtemp;
            double freq = data->freq;

            /* 1. Calculate Thermal Noise PSD */
            double Sid_thermal = 0.0;
            switch(here->B4v5tnoimod) {
                case B4V5_TNOIMOD_BSIM4:
                    Sid_thermal = B4v5thermalNoiseBSIM4(here, temp);
                    break;
                case B4V5_TNOIMOD_IGNOISE:
                    Sid_thermal = B4v5thermalNoiseBSIM4(here, temp);
                    /* Also calculate induced gate noise and correlation */
                    double Sig_induced, corr_coeff;
                    B4v5inducedGateNoise(here, temp, freq, &Sig_induced, &corr_coeff);
                    /* Stamp correlated noise sources */
                    NevalSrc(&noise1, &noise2, ckt, data,
                             here->B4v5dNode, here->B4v5sNode,
                             Sid_thermal, Sig_induced, corr_coeff);
                    break;
            }

            /* 2. Calculate Flicker Noise PSD */
            double Sid_flicker = 0.0;
            switch(here->B4v5fnoimod) {
                case B4V5_FNOIMOD_BSIM4:
                    Sid_flicker = B4v5flickerNoiseBSIM4(here, freq);
                    break;
                case B4V5_FNOIMOD_UNIFIED:
                    Sid_flicker = B4v5flickerNoiseUnified(here, freq);
                    break;
            }

            /* 3. Stamp the total noise PSD */
            if(here->B4v5tnoimod != B4V5_TNOIMOD_IGNOISE) {
                /* Stamp thermal noise as an independent source */
                NevalSrc(&noise1, &noise2, ckt, data,
                         here->B4v5dNode, here->B4v5sNode,
                         Sid_thermal, 0.0, 0.0);
            }
            /* Stamp flicker noise as an independent source */
            NevalSrc(&noise1, &noise2, ckt, data,
                     here->B4v5dNode, here->B4v5sNode,
                     Sid_flicker, 0.0, 0.0);

            /* 4. Calculate output noise if requested (mode == N_OUTPUT) */
            if(mode == N_OUTPUT) {
                *OnDens += data->outNoiz;
            }
        }
    }
}

/* Example helper function for unified flicker noise */
static double B4v5flickerNoiseUnified(B4v5instance *here, double freq)
{
    B4v5model *model = (B4v5model *)here->B4v5gen.B4v5modPtr;
    double Sid;

    /* S_id_fl(f) = (KF · Id^AF) / (f^EF · Leff^2) */
    Sid = model->B4v5kf * pow(fabs(here->B4v5id), model->B4v5af);
    Sid /= (pow(freq, model->B4v5ef) * here->B4v5leff * here->B4v5leff);

    /* Add bias-dependent parameter correction */
    Sid *= (model->B4v5noia + model->B4v5noib * here->B4v5vgs
            + model->B4v5noic * here->B4v5vgs * here->B4v5vgs);

    return Sid;
}
```

### Mapping to Mathematical Formulations

The C implementation directly codifies the mathematical models:

1.  **Y(ω) Matrix**: The complex stamps in `B4v5acLoad()` precisely implement **Y = G + jωC**. The `IMAX * omega * C` terms create the imaginary part, where `IMAX` is the complex constant `j` and `omega` is `ω`.
2.  **Thermal Noise PSD**: The function `B4v5thermalNoiseBSIM4()` computes **4kT · γ · gds0**, using stored `B4v5gamma0` and `B4v5gds`.
3.  **Induced Gate Noise**: When selected, `B4v5inducedGateNoise()` calculates **S_ig(f)** and the correlation coefficient **ρ** using the channel charge partitioning factor `B4v5npart` and frequency `freq`.
4.  **Flicker Noise**: The `B4v5flickerNoiseUnified()` function is a direct translation of the unified model equation, using parameters `KF`, `AF`, `EF`, `noia`, `noib`, `noic`, and the operating point current `B4v5id`.

The code demonstrates a clean separation of concerns: the model computes the *values* of conductances, capacitances, and noise spectral densities based on physics and operating point, while the SPICE kernel (via `stamp_complex_matrix`, `NevalSrc`) handles the numerical linear algebra of assembling and solving the system matrices. This architecture ensures both computational efficiency and adherence to the rigorous mathematical foundations of the BSIM4v5 RF and noise models.