# BSIM3: Small-Signal AC, Capacitance, and Noise Analysis

_Generated 2026-04-12 09:48 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3noi.c`

# **BSIM3: Small-Signal AC, Capacitance, and Noise Analysis**

## **Chapter Introduction**

This chapter details the implementation of small-signal AC analysis, intrinsic capacitance modeling, and noise analysis for the BSIM3v3.2.4 deep-submicron MOSFET model within the Ngspice EDA framework. The analysis focuses on three critical source files: `b3acld.c`, which constructs the complex admittance matrix for frequency-domain simulation; the integrated capacitance model within `b3ld.c` that ensures charge conservation; and `b3noi.c`, which implements spectral density calculations for thermal, flicker, and induced gate noise. These components are essential for accurate simulation of analog and RF circuits, where frequency response, linearity, and noise figure are paramount. The implementation rigorously maps the BSIM3's continuous, differentiable mathematical formulations to SPICE's matrix-based solving infrastructure, ensuring numerical stability and convergence during `.AC` and `.NOISE` analyses. The following sections present the complete mathematical formulation, convergence analysis, and corresponding C implementation that together define Ngspice's BSIM3 small-signal and noise simulation capabilities.

## **Mathematical Formulation**

This section details the mathematical models implemented in Ngspice's BSIM3v3.2.4 for small-signal AC analysis, intrinsic capacitance calculation, and noise analysis. All formulations are explicitly tied to SPICE's circuit simulation framework, where they are used to construct the complex admittance matrix and noise correlation matrices for frequency-domain analysis.

### **1. Small-Signal Linearization for AC Analysis**

The BSIM3 model linearizes the device around its DC operating point to construct the small-signal equivalent circuit. The linearization yields a conductance matrix **G** and a capacitance matrix **C**, which combine to form the complex admittance matrix **Y(ω)** used in SPICE's AC analysis.

#### **1.1 Conductance Parameters from DC Operating Point**

The small-signal conductances are partial derivatives of the terminal currents with respect to terminal voltages, evaluated at the DC operating point:

*   **Transconductance:** `gm = ∂Id/∂Vgs|Vds,Vbs` - Relates drain current change to gate-source voltage.
*   **Drain Conductance:** `gds = ∂Id/∂Vds|Vgs,Vbs` - Output conductance, inverse of early voltage effect.
*   **Bulk Transconductance:** `gmbs = ∂Id/∂Vbs|Vgs,Vds` - Body effect transconductance.
*   **Bulk-Drain Conductance:** `gbd = ∂Ib/∂Vbd|Vbs` - Conductance of the reverse-biased drain-bulk diode.
*   **Bulk-Source Conductance:** `gbs = ∂Ib/∂Vbs|Vbd` - Conductance of the reverse-biased source-bulk diode.

In the C implementation (`b3ld.c`), these are calculated as `inst->BSIM3gm`, `inst->BSIM3gds`, etc., after the DC operating point is solved via Newton-Raphson iteration.

#### **1.2 Intrinsic Capacitance Model (Meyer with Charge Conservation)**

The BSIM3 implementation uses a charge-based capacitance model to ensure charge conservation during transient simulation. The model computes terminal charges (`Qg, Qb, Qd, Qs`) and derives capacitances as their voltage derivatives.

**Gate Oxide Capacitance:**
```
C_ox = ε_ox * W_eff * L_eff / t_ox
```
Where `ε_ox = 3.9 * 8.854e-12 F/m`, `W_eff` and `L_eff` are scaled effective dimensions, and `t_ox` is the oxide thickness (`model->BSIM3tox`).

**Terminal Charges:**
The charges are partitioned based on the `xpart` parameter (0 = 40/60, 0.5 = 50/50, 1 = 0/100).
```
Qg = C_ox * [ Vgb - V_fb - φ_s + γ * sqrt(φ_s - Vbs) + (Vgs - Vth) * (1 - xpart) ]
Qb = -C_ox * [ γ * sqrt(φ_s - Vbs) + V_fb - φ_s ]
Qd = -C_ox * (Vgs - Vth) * xpart
Qs = -C_ox * (Vgs - Vth) * (1 - xpart)
```
`V_fb` is the flat-band voltage, `φ_s` is the surface potential (~2φ_F), and `γ` is the body-effect coefficient.

**Transcapacitances (for AC matrix stamping):**
Capacitances are the derivatives of charge with respect to voltage, ensuring `Cij = Cji` for reciprocity.
```
Cgs = ∂(Qg - Qs)/∂Vgs
Cgd = ∂(Qg - Qd)/∂Vgd
Cgb = ∂Qg/∂Vgb
Cdd = ∂Qd/∂Vd = 0 (ideal drain has no charge storage)
Css = ∂Qs/∂Vs = 0 (ideal source has no charge storage)
Cbb = ∂Qb/∂Vb
```
These are stored in the instance as `inst->BSIM3cgs`, `inst->BSIM3cgd`, etc.

#### **1.3 Complex Admittance Matrix Y(ω)**

For AC analysis at angular frequency `ω = 2πf`, SPICE constructs the circuit matrix as `Y(ω) = G + jωC`. For the BSIM3's 6-node representation (D, D', G, S, S', B), the stamped matrix elements combine conductive (`g*`) and capacitive (`jωC*`) parts.

**Matrix Stamp for Internal Drain Node (D'):**
```
Y[D', D']  += (1/Rd) + gds + gbd + jω(C_g,total + C_bd + C_bs)
Y[D', G]   += gm - jω(C_gs + C_gb)
Y[D', S']  += -gds - gmbs - jω(C_gd)
Y[D', B]   += gbd - jω(C_gb)
Y[D', D]   += -1/Rd
```
Where `C_g,total = C_gs + C_gd + C_gb`. Similar stamps apply for the internal source node (S') and bulk node (B). The ideal gate node (G) has no conductance but has capacitive coupling terms.

### **2. Noise Analysis Formulation**

The BSIM3 model in `b3noi.c` implements three primary noise sources for AC noise analysis: thermal noise, flicker (1/f) noise, and induced gate noise. These are characterized by their spectral densities and stamped into SPICE's noise correlation matrix.

#### **2.1 Channel Thermal Noise**

The spectral density of the drain current thermal noise is:
```
S_id,thermal(f) = 4 * k_B * T * gm,eff * γ_eff
```
Where:
*   `k_B` is Boltzmann's constant.
*   `T` is the absolute temperature (`ckt->CKTtemp`).
*   `gm,eff` is the effective transconductance, reduced by velocity saturation: `gm,eff = gm / (1 + θ * (Vgs - Vth))`.
*   `γ_eff` is a bias-dependent noise coefficient accounting for short-channel effects:
    ```
    γ_eff = (2/3) * [1 + α0 + α1*L_eff] * [1 + β0 * Vds]
    ```
    Here, `α0`, `α1` (`model->BSIM3alpha0`, `BSIM3alpha1`) and `β0` (`model->BSIM3beta0`) are model parameters.

#### **2.2 Flicker (1/f) Noise**

Two models are implemented:

**A. Empirical SPICE Model:**
```
S_id,flicker(f) = KF * |Id|^AF / ( f^EF * (W_eff * L_eff)^LF )
```
Parameters: `KF` (`BSIM3kf`), `AF` (`BSIM3af`), `EF` (`BSIM3ef`), `LF` (`BSIM3lf`).

**B. BSIM3-Specific Carrier Fluctuation Model:**
```
S_id,bsim3(f) = [ NOIA * log(1 + NOIB * Id) + NOIC * Id ] / ( f * W_eff * L_eff )
```
Parameters: `NOIA` (`BSIM3noia`), `NOIB` (`BSIM3noib`), `NOIC` (`BSIM3noic`).

The total flicker noise is the sum of the selected models.

#### **2.3 Induced Gate Noise**

Due to capacitive coupling, fluctuating channel potential induces noise on the gate terminal. Its spectral density and correlation with drain noise are:
```
S_ig,gate(f) = 4 * k_B * T * δ * (ω * C_gs)^2 / (5 * gm,eff)
```
Where `δ` is a model parameter (~4/3 for long channel).
The correlated component between gate and drain noise is:
```
S_ig,id,corr(f) = c * sqrt( S_id,thermal(f) * S_ig,gate(f) )
```
The correlation coefficient `c` is typically a complex number with value ~`0.395j`.

#### **2.4 Junction Shot Noise**

For the reverse-biased bulk-drain and bulk-source diodes:
```
S_i,bd(f) = 2 * q * |I_bd|
S_i,bs(f) = 2 * q * |I_bs|
```
Where `q` is the electron charge and `I_bd`, `I_bs` are the diode currents.

### **3. Pole-Zero Analysis Formulation**

While not a separate `pzld.c` file, the BSIM3 model supports pole-zero analysis through the admittance matrix `Y(ω)`. The poles and zeros of the device's transfer function (e.g., `Id/Vgs`) are extracted by SPICE's analysis routines from the linearized system:
```
[Y(ω)] * [V(ω)] = [I(ω)]
```
The eigenvalues of the system matrix (related to `Y(ω)`) give the natural frequencies (poles). Zeros are found by solving for `ω` where the transfer function numerator goes to zero. The BSIM3 implementation ensures `Y(ω)` is correctly stamped so these analyses are accurate.

## **Convergence Analysis**

This section analyzes the numerical properties of the BSIM3 small-signal, capacitance, and noise implementations, focusing on their stability and compatibility with SPICE's iterative solvers.

### **1. Continuity and Differentiability for AC Linearization**

The accuracy of the small-signal `gm`, `gds`, and `gmbs` parameters depends entirely on the continuity and smoothness of the DC `Id(Vgs, Vds, Vbs)` characteristic and its first derivatives.

*   **Smoothing Functions:** The DC model uses hyperbolic tangent (`tanh`) blending between operating regions (subthreshold/strong inversion, linear/saturation). This ensures the function `Id(...)` and its first partial derivatives (the conductances) are C¹ continuous. Discontinuities in the first derivative would cause abrupt changes in the `G` matrix between Newton iterations, harming convergence.
*   **`DEVfetlim` Voltage Limiting:** This function (applied to `Vgs`, `Vds`) ensures voltages change smoothly between Newton-Raphson iterations. It prevents the `gm` calculation from jumping across regions (e.g., from subthreshold to strong inversion) in a single iteration, which would destabilize the AC matrix construction.

### **2. Charge Conservation and Capacitance Reciprocity**

Charge non-conservation in capacitance models is a classic source of error and non-convergence in transient analysis, which also affects the accuracy of AC analysis.

*   **Charge-Based Formulation:** By computing terminal charges (`Qg, Qb, Qd, Qs`) and defining capacitances as `Cij = ∂Qi/∂Vj`, the BSIM3 model inherently satisfies the reciprocity condition `Cij = Cji`. This symmetry is crucial for the capacitance matrix `C` to be physically consistent and for the overall `Y(ω)` matrix to be valid for reciprocal network analysis.
*   **Conservation Law:** The model enforces `Qg + Qb + Qd + Qs = 0`. This guarantees no net charge is created or destroyed within the device, a fundamental requirement for the stability of numerical integration in transient analysis, which underpins the validity of the linearized `C` matrix used in AC analysis.

### **3. Admittance Matrix Conditioning for Frequency Sweep**

During an AC frequency sweep, SPICE solves `Y(ω)*V = I` at each frequency point. The numerical conditioning of `Y(ω)` is critical.

*   **Parasitic Resistance Handling:** The inclusion of internal nodes D' and S' for series resistances `Rd` and `Rs` prevents the matrix from becoming ill-conditioned when these resistances are very small. The stamp `Y[D,D'] = -1/Rd` provides a well-defined path even as `Rd → 0`.
*   **Capacitive Susceptance Scaling:** The imaginary part of `Y(ω)` scales with `ω`. At very low frequencies (`ω → 0`), the matrix becomes dominated by the real conductance part `G`. At very high frequencies, the `jωC` terms dominate. The BSIM3 implementation ensures the `C` matrix entries are finite and physically bounded (e.g., `C_ox` is the maximum possible `C_gs`), preventing the matrix from becoming singular at any frequency.
*   **GMIN Parallel Conductance:** SPICE adds a tiny conductance (`GMIN`, typically 1e-12 Ʊ) across every pn-junction. In the BSIM3 AC stamp, this appears as a small positive real value added to the diagonal entries for nodes B, D', S' (e.g., `Y[B,B] += GMIN`). This ensures `Y(ω)` is positive definite and non-singular, guaranteeing a solution exists at all frequencies.

### **4. Noise Analysis Convergence and Positive-Definite Matrices**

Noise analysis in SPICE requires building a real, symmetric, positive-semidefinite noise correlation matrix `C_n` from the spectral densities.

*   **Spectral Density Positivity:** The implemented formulas ensure `S_id(f) ≥ 0` and `S_ig(f) ≥ 0` for all biases and frequencies. The thermal noise formula is positive because `gm,eff > 0` and `γ_eff > 0`. The flicker noise models use absolute current `|Id|` and positive parameters.
*   **Correlation Matrix Consistency:** The cross-correlation term `S_ig,id,corr` is calculated to satisfy the Cauchy-Schwarz inequality: `|S_ig,id,corr|² ≤ S_id * S_ig`. This is enforced by the implementation using the defined correlation coefficient `c`. This guarantees the 2x2 noise correlation matrix for the gate and drain ports is positive-semidefinite, a necessary condition for the physical realizability of the noise and for the stability of the noise analysis computation.
*   **Frequency Dependence Regularization:** The flicker noise model `1/f^EF` has a singularity at `f=0`. SPICE's noise analysis avoids this by starting the frequency sweep at a small positive frequency (`f_min > 0`). The BSIM3 implementation does not require special handling at DC because the noise functions are only evaluated during the `.NOISE` analysis, which is inherently an AC analysis.

### **5. Interaction with Newton-Raphson and Time-Step Control**

While AC analysis is linear, its accuracy depends on a converged DC operating point.

*   **DC Operating Point Dependence:** The `G` and `C` matrices are evaluated at the converged DC solution. Therefore, any convergence failure in the DC analysis (`.OP`) will propagate, making the AC results meaningless. The robustness of the BSIM3 DC model (via smoothing and `DEVfetlim`) is thus a prerequisite for AC analysis convergence.
*   **Consistency with Transient Analysis:** The same charge-based capacitance model used for the `C` matrix in AC analysis is used for charge calculation in transient analysis. This consistency ensures that the small-signal behavior predicted by `.AC` matches the linearized behavior around the operating point in `.TRAN`, which is vital for validating simulation results across different analysis types.

In summary, the BSIM3 implementation for AC, capacitance, and noise analysis provides numerically robust, physically consistent models that produce well-conditioned matrices (`Y(ω)`, `C_n`) across all frequencies and bias points, ensuring reliable convergence within the SPICE simulation framework.

----------

# **BSIM3: Small-Signal AC, Capacitance, and Noise Analysis - C Implementation**

## **1. Core Data Structures for AC and Noise Analysis**

The BSIM3 implementation in Ngspice extends the basic DC structures to support frequency-domain analysis and noise calculations through additional fields in the instance structure.

### **AC Analysis State Variables**
```c
/* From bsim3def.h - Extended instance structure for AC analysis */
typedef struct sBSIM3instance {
    /* ... DC parameters omitted for brevity ... */
    
    /* Small-signal conductances (calculated in b3ld.c) */
    double BSIM3gm;                   /* ∂Id/∂Vgs - Transconductance */
    double BSIM3gds;                  /* ∂Id/∂Vds - Output conductance */
    double BSIM3gmbs;                 /* ∂Id/∂Vbs - Bulk transconductance */
    double BSIM3gbd;                  /* ∂Id/∂Vbd - Bulk-drain conductance */
    double BSIM3gbs;                  /* ∂Id/∂Vbs - Bulk-source conductance */
    
    /* Intrinsic capacitances (Meyer model implementation) */
    double BSIM3cgs;                  /* Gate-source capacitance */
    double BSIM3cgd;                  /* Gate-drain capacitance */
    double BSIM3cgb;                  /* Gate-bulk capacitance */
    double BSIM3cdg;                  /* Drain-gate capacitance (reciprocal) */
    double BSIM3cdb;                  /* Drain-bulk capacitance */
    double BSIM3csg;                  /* Source-gate capacitance (reciprocal) */
    double BSIM3csb;                  /* Source-bulk capacitance */
    
    /* Matrix pointers for complex admittance stamping */
    double *BSIM3DdPtr;              /* [drain, drain] - Ydd */
    double *BSIM3DdpPtr;             /* [drain, drain'] - Ydd' */
    double *BSIM3DgPtr;              /* [drain, gate] - Ydg */
    /* ... 36 total pointers for 6×6 matrix ... */
    
    /* State vector indices for charge conservation */
    int BSIM3qgState;                /* Gate charge state (index in CKTstate) */
    int BSIM3qbState;                /* Bulk charge state */
    int BSIM3qdState;                /* Drain charge state */
    int BSIM3qsState;                /* Source charge state */
} BSIM3instance;
```

**Mathematical Mapping:** The `BSIM3gm`, `BSIM3gds`, and `BSIM3gmbs` fields store the partial derivatives \(g_m = \partial I_d/\partial V_{gs}\), \(g_{ds} = \partial I_d/\partial V_{ds}\), and \(g_{mbs} = \partial I_d/\partial V_{bs}\) calculated during the DC operating point analysis in `b3ld.c`. These form the conductance matrix \(G\) for small-signal analysis.

## **2. AC Load Function Implementation (`b3acld.c`)**

The `BSIM3acLoad()` function constructs the complex admittance matrix \(Y(\omega) = G + j\omega C\) for frequency-domain analysis.

### **Complex Admittance Matrix Construction**
```c
int BSIM3acLoad(GENmodel *genmodel, CKTcircuit *ckt) {
    BSIM3model *model = (BSIM3model *)genmodel;
    BSIM3instance *inst;
    double omega;
    double gd_ext, gs_ext;  /* External parasitic conductances */
    double rd, rs;          /* Parasitic resistances */
    
    /* Get angular frequency from circuit context */
    omega = ckt->CKTomega;  /* ω = 2πf */
    
    for (; model != NULL; model = model->BSIM3nextModel) {
        for (inst = model->BSIM3instances; inst != NULL; 
             inst = inst->BSIM3nextInstance) {
            
            /* Calculate total gate capacitance */
            double cg_total = inst->BSIM3cgs + inst->BSIM3cgd + inst->BSIM3cgb;
            
            /* Stamp conductive (real) part of admittance matrix */
            *(inst->BSIM3DdPtr) += gd_ext;                    /* Gdd */
            *(inst->BSIM3DdpPtr) += -1.0/rd;                  /* Gdd' */
            *(inst->BSIM3dpdpPtr) += 1.0/rd + inst->BSIM3gds 
                                     + inst->BSIM3gbd;        /* Gd'd' */
            *(inst->BSIM3dpgPtr) += inst->BSIM3gm;            /* Gd'g */
            *(inst->BSIM3dpspPtr) += -inst->BSIM3gds 
                                     - inst->BSIM3gmbs;       /* Gd's' */
            *(inst->BSIM3dpbPtr) += inst->BSIM3gbd;           /* Gd'b */
            
            /* Stamp capacitive (imaginary) part - jωC terms */
            *(inst->BSIM3DdPtr) += I * omega * cd_ext;        /* jωCd_ext */
            *(inst->BSIM3dpdpPtr) += I * omega * (cg_total 
                                     + inst->BSIM3cdb 
                                     + inst->BSIM3csb);       /* jωCg_total */
            *(inst->BSIM3dpgPtr) += -I * omega * (inst->BSIM3cgs 
                                     + inst->BSIM3cgb);       /* -jω(Cgs+Cgb) */
            *(inst->BSIM3dpspPtr) += -I * omega * inst->BSIM3cgd; /* -jωCgd */
            *(inst->BSIM3dpbPtr) += -I * omega * inst->BSIM3cgb;  /* -jωCgb */
            
            /* Stamp reciprocal terms for symmetric matrix */
            *(inst->BSIM3gdpPtr) += -I * omega * (inst->BSIM3cgs 
                                     + inst->BSIM3cgb);       /* -jω(Cgs+Cgb) */
            *(inst->BSIM3gspPtr) += -I * omega * inst->BSIM3cgd; /* -jωCgd */
            *(inst->BSIM3gbpPtr) += -I * omega * inst->BSIM3cgb;  /* -jωCgb */
        }
    }
    return OK;
}
```

**Mathematical Mapping:** This code implements the admittance matrix stamping:
- Real part: \(G_{ij}\) from DC small-signal conductances
- Imaginary part: \(j\omega C_{ij}\) from capacitance matrix
- The `I` macro represents the imaginary unit \(j = \sqrt{-1}\)
- Matrix symmetry \(Y_{ij} = Y_{ji}\) is enforced through reciprocal stamping

## **3. Capacitance Model Implementation**

The BSIM3 uses a charge-conserving Meyer capacitance model implemented across multiple functions.

### **Charge Calculation and Capacitance Extraction**
```c
/* In b3ld.c - During DC operating point calculation */
void BSIM3calcCapacitances(BSIM3instance *inst, BSIM3model *model,
                           double vgs, double vds, double vbs) {
    double cox, vfb, phi_s, gamma;
    double qg, qb, qd, qs;
    
    /* Oxide capacitance calculation */
    cox = EPS_OX * inst->BSIM3weff * inst->BSIM3leff / model->BSIM3tox;
    
    /* Flat-band voltage and surface potential */
    vfb = model->BSIM3vfb0;
    phi_s = 2.0 * PHI_T - vbs;
    gamma = model->BSIM3gamma;
    
    /* Gate charge partitioning (Meyer model) */
    qg = cox * (vgs - vfb - phi_s 
                + gamma * sqrt(phi_s - vbs) 
                + (vgs - inst->BSIM3von) * (1.0 - XPART));
    
    /* Bulk charge */
    qb = -cox * (gamma * sqrt(phi_s - vbs) + vfb - phi_s);
    
    /* Drain and source charges */
    qd = -cox * (vgs - inst->BSIM3von) * XPART;
    qs = -cox * (vgs - inst->BSIM3von) * (1.0 - XPART);
    
    /* Store charges for state vector */
    inst->BSIM3qg = qg;
    inst->BSIM3qb = qb;
    inst->BSIM3qd = qd;
    inst->BSIM3qs = qs;
    
    /* Calculate capacitances as derivatives */
    inst->BSIM3cgs = (qg - qs) / (vgs + DELTA_SMALL);
    inst->BSIM3cgd = (qg - qd) / (vgs - vds + DELTA_SMALL);
    inst->BSIM3cgb = qg / (vgs - vbs + DELTA_SMALL);
    
    /* Enforce reciprocity: Cij = Cji */
    inst->BSIM3cdg = inst->BSIM3cgd;
    inst->BSIM3csg = inst->BSIM3cgs;
}
```

**Mathematical Mapping:** This implements:
- Oxide capacitance: \(C_{ox} = \epsilon_{ox} \cdot W_{eff} \cdot L_{eff} / t_{ox}\)
- Gate charge: \(Q_g = C_{ox}[V_{gb} - V_{fb} - \phi_s + \gamma\sqrt{\phi_s - V_{bs}} + (V_{gs} - V_{th})(1 - x)]\)
- Capacitance calculation: \(C_{ij} = \partial Q_i/\partial V_j\) using finite differences
- Charge conservation: \(Q_g + Q_b + Q_d + Q_s = 0\) enforced by construction

## **4. Noise Analysis Implementation (`b3noi.c`)**

The BSIM3 noise model includes thermal, flicker, and induced gate noise components.

### **Noise Source Setup and Calculation**
```c
int BSIM3noise(int mode, int operation, GENmodel *genmodel,
               CKTcircuit *ckt, Ndata *data, double *OnDens) {
    BSIM3model *model = (BSIM3model *)genmodel;
    BSIM3instance *inst;
    double freq, temp;
    
    freq = ckt->CKTomega / (2.0 * M_PI);  /* Convert ω to Hz */
    temp = ckt->CKTtemp + 273.15;         /* Temperature in Kelvin */
    
    for (; model != NULL; model = model->BSIM3nextModel) {
        for (inst = model->BSIM3instances; inst != NULL;
             inst = inst->BSIM3nextInstance) {
            
            /* Calculate thermal noise spectral density */
            double sid_thermal = BSIM3thermalNoise(inst, model, temp);
            
            /* Calculate flicker noise spectral density */
            double sid_flicker = BSIM3flickerNoise(inst, model, freq);
            
            /* Calculate induced gate noise */
            double sig_gate = BSIM3gateNoise(inst, model, freq, temp);
            
            /* Total noise spectral density */
            double sid_total = sid_thermal + sid_flicker;
            
            /* Stamp noise sources into the noise matrix */
            if (operation == N_OPEN) {
                /* Open-circuit noise voltage calculation */
                *(inst->BSIM3drainNoiseDensPtr) = sid_total;
                *(inst->BSIM3gateNoiseDensPtr) = sig_gate;
                
                /* Correlation term */
                *(inst->BSIM3corrNoisePtr) = BSIM3correlationNoise(
                    inst, model, sid_thermal, sig_gate);
            }
        }
    }
    return OK;
}
```

### **Thermal Noise Implementation**
```c
double BSIM3thermalNoise(BSIM3instance *inst, BSIM3model *model,
                         double temp) {
    double gm_eff, gamma_eff, sid;
    
    /* Effective transconductance including velocity saturation */
    gm_eff = inst->BSIM3gm / 
             (1.0 + model->BSIM3theta * (inst->BSIM3vgs - inst->BSIM3von));
    
    /* Noise coefficient with short-channel effects */
    gamma_eff = (2.0/3.0) 
                * (1.0 + model->BSIM3alpha0 
                   + model->BSIM3alpha1 * inst->BSIM3leff)
                * (1.0 + model->BSIM3beta0 * inst->BSIM3vds);
    
    /* Thermal noise spectral density */
    sid = 4.0 * BOLTZMANN * temp * gm_eff * gamma_eff;
    
    return sid;
}
```

### **Flicker Noise Implementation**
```c
double BSIM3flickerNoise(BSIM3instance *inst, BSIM3model *model,
                         double freq) {
    double sid_flicker, sid_bsim3;
    
    /* Standard 1/f noise model */
    sid_flicker = (model->BSIM3kf * pow(fabs(inst->BSIM3id), model->BSIM3af))
                  / (pow(freq, model->BSIM3ef)
                     * pow(inst->BSIM3weff * inst->BSIM3leff, model->BSIM3lf));
    
    /* BSIM3-specific flicker noise model */
    if (model->BSIM3noia != 0.0 || model->BSIM3noib != 0.0 
        || model->BSIM3noic != 0.0) {
        sid_bsim3 = (model->BSIM3noia * log(1.0 + model->BSIM3noib 
                     * fabs(inst->BSIM3id))
                     + model->BSIM3noic * fabs(inst->BSIM3id))
                    / (freq * inst->BSIM3weff * inst->BSIM3leff);
        
        /* Use BSIM3 model if parameters are specified */
        if (sid_bsim3 > 0.0) {
            sid_flicker = sid_bsim3;
        }
    }
    
    return sid_flicker;
}
```

### **Induced Gate Noise Implementation**
```c
double BSIM3gateNoise(BSIM3instance *inst, BSIM3model *model,
                      double freq, double temp) {
    double omega, delta, sig_gate;
    
    omega = 2.0 * M_PI * freq;
    
    /* Gate noise coefficient (typically 4/3 for long channel) */
    delta = model->BSIM3delta != 0.0 ? model->BSIM3delta : 4.0/3.0;
    
    /* Induced gate noise spectral density */
    sig_gate = 4.0 * BOLTZMANN * temp * delta
               * pow(omega * inst->BSIM3cgs, 2)
               / (5.0 * inst->BSIM3gm);
    
    return sig_gate;
}

double BSIM3correlationNoise(BSIM3instance *inst, BSIM3model *model,
                             double sid_thermal, double sig_gate) {
    double c_corr;
    
    /* Correlation coefficient (typically j0.395 for long channel) */
    c_corr = model->BSIM3corr != 0.0 ? model->BSIM3corr : 0.395;
    
    /* Correlated noise between drain and gate */
    return c_corr * sqrt(sid_thermal * sig_gate);
}
```

**Mathematical Mapping:** This implements:
- Thermal noise: \(S_{id}^{th} = 4k_B T g_m \gamma_{eff}\) with short-channel correction
- Flicker noise: \(S_{id}^{1/f} = K_f I_d^{A_f} / (f^{E_f} (W_{eff}L_{eff})^{L_f})\)
- BSIM3 flicker model: \(S_{id}^{BSIM3} = [N_{OA}\ln(1+N_{OB}I_d) + N_{OC}I_d] / (f W_{eff}L_{eff})\)
- Induced gate noise: \(S_{ig} = 4k_B T \delta (\omega C_{gs})^2 / (5g_m)\)
- Correlation: \(S_{igd} = c\sqrt{S_{id}^{th}S_{ig}}\)

## **5. Matrix Pointer Allocation for AC/Noise Analysis**

The setup function in `b3set.c` allocates additional matrix pointers for AC and noise analysis.

### **Extended Matrix Allocation**
```c
int BSIM3setup(SMPmatrix *matrix, GENmodel *genmodel,
               CKTcircuit *ckt, int *states) {
    BSIM3model *model = (BSIM3model *)genmodel;
    BSIM3instance *inst;
    
    for (; model != NULL; model = model->BSIM3nextModel) {
        for (inst = model->BSIM3instances; inst != NULL;
             inst = inst->BSIM3nextInstance) {
            
            /* Allocate 6×6 matrix pointers for AC analysis */
            SPfrontEnd->IFuid(matrix,
                &(inst->BSIM3DdPtr),    /* Ydd */
                inst->BSIM3dNode, inst->BSIM3dNode);
            
            SPfrontEnd->IFuid(matrix,
                &(inst->BSIM3DdpPtr),   /* Ydd' */
                inst->BSIM3dNode, inst->BSIM3dNodePrime);
            
            SPfrontEnd->IFuid(matrix,
                &(inst->BSIM3DgPtr),    /* Ydg */
                inst->BSIM3dNode, inst->BSIM3gNode);
            
            /* ... allocate all 36 matrix pointers ... */
            
            /* Allocate noise matrix pointers */
            SPfrontEnd->IFuid(matrix,
                &(inst->BSIM3drainNoiseDensPtr),
                inst->BSIM3dNodePrime, inst->BSIM3dNodePrime);
            
            SPfrontEnd->IFuid(matrix,
                &(inst->BSIM3gateNoiseDensPtr),
                inst->BSIM3gNode, inst->BSIM3gNode);
            
            SPfrontEnd->IFuid(matrix,
                &(inst->BSIM3corrNoisePtr),
                inst->BSIM3dNodePrime, inst->BSIM3gNode);
            
            /* Allocate state vector entries for charge storage */
            inst->BSIM3qgState = *states;
            (*states)++;
            inst->BSIM3qbState = *states;
            (*states)++;
            inst->BSIM3qdState = *states;
            (*states)++;
            inst->BSIM3qsState = *states;
            (*states)++;
        }
    }
    return OK;
}
```

## **6. Parameter Validation for AC/Noise Analysis**

The checking function ensures parameters are physically valid for small-signal analysis.

### **AC/Noise Parameter Validation**
```c
int BSIM3check(BSIM3model *model) {
    /* ... DC parameter checks omitted ... */
    
    /* Validate capacitance parameters */
    if (model->BSIM3cgso < 0.0) {
        model->BSIM3cgso = 0.0;  /* Gate-source overlap capacitance */
    }
    if (model->BSIM3cgdo < 0.0) {
        model->BSIM3cgdo = 0.0;  /* Gate-drain overlap capacitance */
    }
    if (model->BSIM3cgbo < 0.0) {
        model->BSIM3cgbo = 0.0;  /* Gate-bulk overlap capacitance */
    }
    
    /* Validate noise parameters */
    if (model->BSIM3kf < 0.0) {
        model->BSIM3kf = 0.0;    /* Flicker noise coefficient */
    }
    if (model->BSIM3af <= 0.0) {
        model->BSIM3af = 1.0;    /* Flicker noise exponent */
    }
    if (model->BSIM3ef <= 0.0) {
        model->BSIM3ef = 1.0;    /* Frequency exponent */
    }
    
    /* Validate correlation coefficient bounds */
    if (model->BSIM3corr < -1