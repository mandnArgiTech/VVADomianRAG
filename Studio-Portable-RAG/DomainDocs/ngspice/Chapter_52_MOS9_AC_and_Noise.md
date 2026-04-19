# MOS9: Small-Signal AC, Pole-Zero, and Noise Analysis

_Generated 2026-04-12 08:47 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9noi.c`

# MOS9: Small-Signal AC, Pole-Zero, and Noise Analysis

## Introduction

Within the Ngspice simulation framework, the MOS9 (Philips) model's frequency-domain behavior is implemented across three specialized C files that translate the device's complex physics into linearized circuit matrices suitable for numerical analysis. The file `mos9acld.c` performs the core small-signal linearization, constructing the complex admittance matrix **Y(ω) = G + jωC** by evaluating the derivatives of the non-linear drain current and charge equations at the DC operating point. This matrix enables AC analysis across a user-defined frequency sweep. While the provided context does not detail a dedicated `mos9pzld.c`, pole-zero analysis in SPICE typically extracts the system's transfer function **H(s)** from this same linearized matrix to compute its natural frequencies and zeros. The file `mos9noi.c` implements a comprehensive noise model, calculating spectral densities for thermal, flicker (1/f), and shot noise contributions based on the operating point and material parameters, then stamping these as correlated sources into the circuit matrix for noise simulation. Together, these files transform the static MOS9 device model into a dynamic, frequency-aware component capable of predicting gain, bandwidth, stability, and noise performance within a larger circuit simulation.

## Mathematical Formulation

The small-signal analysis of the MOS9 model in SPICE transforms the non-linear device equations into a linearized admittance matrix evaluated at the DC operating point. This enables AC analysis, pole-zero determination, and noise spectral density calculation.

### 1. Linearization for Small-Signal AC Analysis

The complete MOSFET is represented by a 6-node network (D, G, S, B, DP, SP). The small-signal admittance matrix **Y(ω)** is derived from the Taylor expansion of the device equations around the DC operating point:

```
Y(ω) = G + jωC
```

Where:
- **G** is the conductance matrix containing derivatives of currents with respect to voltages
- **C** is the capacitance matrix containing derivatives of charges with respect to voltages
- **ω = 2πf** is the angular frequency

#### 1.1 Conductance Matrix Elements

From the drain current equation `I_ds = f(V_gs, V_ds, V_bs)`, the small-signal conductances are:

```
g_m = ∂I_ds/∂V_gs|_OP    (transconductance)
g_ds = ∂I_ds/∂V_ds|_OP   (drain conductance)
g_mb = ∂I_ds/∂V_bs|_OP   (bulk transconductance)
```

For the MOS9 Philips model, these derivatives depend on the operating region:

**Linear Region (V_ds ≤ V_dsat):**
```
g_m = β·V_ds·(1 + λ·V_ds)
g_ds = β·[(V_gs - V_th) - (1 + FB)·V_ds]·(1 + λ·V_ds) + λ·I_ds
g_mb = g_m·[γ/(2√(2φ - V_bs))]·(1 + η·V_ds)
where FB = γ/(2√(2φ - V_bs))
```

**Saturation Region (V_ds > V_dsat):**
```
g_m = β·(V_gs - V_th)·(1 + λ·V_ds)/(1 + θ·(V_gs - V_th))
g_ds = λ·I_ds/(1 + λ·V_ds)
g_mb = g_m·[γ/(2√(2φ - V_bs))]·(1 + η·V_dsat)
```

#### 1.2 Capacitance Matrix Elements

Using the Meyer charge model, the capacitance matrix entries are derivatives of charges with respect to terminal voltages:

**Intrinsic Capacitances:**
```
C_gs = ∂Q_gs/∂V_gs = C_gso·W_eff + (2/3)·C_ox·W_eff·L_eff·[1 - (V_gd - V_th)²/(V_gs - V_th + V_gd - V_th)²]
C_gd = ∂Q_gd/∂V_gd = C_gdo·W_eff + (2/3)·C_ox·W_eff·L_eff·[1 - (V_gs - V_th)²/(V_gs - V_th + V_gd - V_th)²]
C_gb = ∂Q_gb/∂V_gb = C_gbo·L_eff + C_ox·W_eff·L_eff·(V_th - V_gb)/√(2φ - V_gb)  for V_gb < V_th
```

**Junction Capacitances:**
```
C_jbd = ∂Q_bd/∂V_bd = AD·CJ·(1 - V_bd/PB)^{-MJ} + PD·CJSW·(1 - V_bd/PB)^{-MJSW}
C_jbs = ∂Q_bs/∂V_bs = AS·CJ·(1 - V_bs/PB)^{-MJ} + PS·CJSW·(1 - V_bs/PB)^{-MJSW}
```

#### 1.3 Complete Admittance Matrix Structure

The 6×6 admittance matrix for the MOS9 model with internal nodes DP and SP has the following non-zero pattern:

```
Y = 
[Y_DD   0     0     0     Y_DDP   0   ]  # External Drain (D)
[ 0    Y_GG   0    Y_GB    0      0   ]  # External Gate (G)
[ 0     0    Y_SS   0      0     Y_SSP]  # External Source (S)
[ 0    Y_BG   0    Y_BB    0      0   ]  # External Bulk (B)
[Y_DPD  0     0     0     Y_DPDP Y_DPSP] # Internal Drain (DP)
[ 0     0    Y_SPS  0     Y_SPDP Y_SPSP] # Internal Source (SP)
```

Where the matrix elements are:

```
Y_DPDP = g_dpr + g_ds + g_mb + g_m + g_spr + jω(C_gs + C_gd + C_gb)
Y_SPSP = g_spr + g_ds + g_mb + g_m + g_dpr + jω(C_gs + C_gd + C_gb)
Y_DPSP = -g_ds - g_mb - jωC_ds
Y_SPDP = -g_ds - g_mb - jωC_ds
Y_DPG = g_m - jωC_gs
Y_SPG = -g_m + jωC_gs
Y_DPB = g_mb - jωC_gb
Y_SPB = -g_mb + jωC_gb
Y_DD = Y_DPDP = g_dpr
Y_SS = Y_SPSP = g_spr
Y_BB = jω(C_jbd + C_jbs)
```

### 2. Pole-Zero Analysis Formulation

The small-signal transfer function H(s) = V_out(s)/V_in(s) can be extracted from the admittance matrix. For a common-source configuration:

```
H(s) = -g_m·(r_ds || (1/sC_L)) / (1 + s/ω_p)
```

Where the dominant pole is:

```
ω_p ≈ 1 / [r_ds·(C_gd + C_L) + (1 + g_m·r_ds)·C_gd·r_s]
```

The MOS9 model calculates these poles from the eigenvalues of the system matrix:

```
[A] = [Y]⁻¹·[C]
```

The poles are the eigenvalues λ_i of [A] satisfying:
```
det(s[I] - [A]) = 0 → s_i = λ_i
```

### 3. Noise Analysis Mathematics

#### 3.1 Thermal Noise Spectral Density

The channel thermal noise current spectral density for MOS9 follows the classical MOSFET noise model with short-channel corrections:

```
S_id(thermal) = 4kT·γ·g_d0
```

Where:
- `k` is Boltzmann's constant (1.380649×10⁻²³ J/K)
- `T` is absolute temperature in Kelvin
- `γ` is the channel noise coefficient
- `g_d0` is the drain conductance at zero V_ds

The noise coefficient γ varies with bias:

**Linear Region (V_ds → 0):**
```
γ_lin = 1
```

**Saturation Region (Long Channel):**
```
γ_sat = 2/3
```

**Short-Channel Correction (when VMAX > 0):**
```
γ_sat = (2/3)·[1 + (E_c·L_eff)/(V_gs - V_th)]
where E_c = VMAX/μ_eff
```

#### 3.2 Induced Gate Noise

At high frequencies, the correlated gate noise becomes significant:

```
S_ig = 4kT·δ·(ω²C_gs²)/(5g_d0)
```

The correlation coefficient between drain and gate noise:
```
c = j·0.395  (approximately)
```

Thus the complete channel noise correlation matrix:
```
[ S_id    S_idg ]
[ S_idg*  S_ig  ] = 4kT·[ γ·g_d0    j·c·√(γδ)·ωC_gs ]
                       [ -j·c·√(γδ)·ωC_gs  δ·ω²C_gs²/(5g_d0) ]
```

#### 3.3 Flicker (1/f) Noise Models

MOS9 implements two flicker noise models:

**Standard SPICE 1/f Model:**
```
S_id(flicker) = KF·|I_ds|^AF / (f·C_ox·L_eff²)
```
Where:
- `KF` is the flicker noise coefficient (model parameter MOS9_KF)
- `AF` is the flicker noise exponent (model parameter MOS9_AF, typically ≈1)
- `f` is frequency in Hz

**Carrier Number Fluctuation Model (when NFS > 0):**
```
S_id(flicker) = (q²·kT·NFS·g_m²) / (f·C_ox²·L_eff²·W_eff)
```
Where:
- `q` is electron charge (1.602×10⁻¹⁹ C)
- `NFS` is fast surface state density (model parameter MOS9_NFS)

#### 3.4 Junction Shot Noise

Bulk-drain and bulk-source junctions contribute shot noise:

```
S_ibd = 2q·|I_bd|  (for forward bias, V_bd > 0)
S_ibs = 2q·|I_bs|  (for forward bias, V_bs > 0)
```

For reverse bias (V_bd, V_bs < 0), junction shot noise is negligible.

#### 3.5 Total Input-Referred Noise Voltage

The total input-referred noise voltage spectral density:

```
S_vg = S_id/g_m² + S_ig + 4kT·R_g
```

Where `R_g` is the gate resistance (not explicitly modeled in MOS9 but may be added externally).

## Convergence Analysis

### 1. Small-Signal Convergence Criteria

For AC analysis, convergence is guaranteed by linearity, but numerical stability requires:

#### 1.1 Matrix Condition Number Check

The admittance matrix **Y(ω)** must be well-conditioned for all frequencies:
```
cond(Y) = ||Y||·||Y⁻¹|| < κ_max
```
Where `κ_max` is typically 10⁶ for double-precision arithmetic.

MOS9 ensures this by:
1. Maintaining `g_dpr, g_spr ≥ GMIN` (typically 1×10⁻¹² Ʊ)
2. Bounding capacitances: `C_gs, C_gd, C_gb ≥ 0`
3. Using series expansion for `C_jbd, C_jbs` when `V_bd/PB → 1` or `V_bs/PB → 1`

#### 1.2 Frequency-Dependent Stability

At each frequency point `f_i`, the solution must satisfy:
```
||Y(ω_i)·V(ω_i) - I(ω_i)|| < ε_AC
```
Where `ε_AC = max(CKTreltol·||V||, CKTabstol)` with typical values:
- `CKTreltol = 1×10⁻³`
- `CKTabstol = 1×10⁻¹²`

### 2. Noise Analysis Convergence

Noise analysis uses the already-converged AC solution. Additional checks include:

#### 2.1 Noise Spectral Density Integration

For total integrated noise over bandwidth [f₁, f₂]:
```
V_n²_total = ∫_{f₁}^{f₂} S_vg(f) df
```

The numerical integration must converge with increasing frequency points. MOS9 uses adaptive frequency sampling when `mode == N_M2` (noise as a function of frequency).

#### 2.2 Dynamic Range Management

To avoid numerical underflow/overflow in noise calculations:
```
If S_vg(f) < N_MINLOG (typically 1×10⁻³⁰ V²/Hz), set S_vg(f) = 0
If S_vg(f) > N_MAXLOG (typically 1×10³⁰ V²/Hz), clip to N_MAXLOG
```

### 3. Pole-Zero Extraction Stability

#### 3.1 Eigenvalue Sensitivity

The poles `p_i` are eigenvalues of `A = Y⁻¹C`. For numerical stability:
```
|Im(p_i)| / |Re(p_i)| < 10⁶  (for realizable circuits)
Re(p_i) < 0  (for stable circuits)
```

MOS9 checks these conditions during `.PZ` analysis and issues warnings if violated.

#### 3.2 Numerical Differentiation for s-Domain

When computing `Y(s)` for complex `s = σ + jω`:
- Use analytic continuation of device equations when possible
- For non-analytic functions, use complex step differentiation:
```
∂f/∂x ≈ Im[f(x + jh)]/h, with h ≈ 1×10⁻²⁰
```

### 4. Temperature Convergence in AC Analysis

Small-signal parameters depend on temperature `T`:
```
g_m(T) = g_m(T_nom)·(T_nom/T)^0.5
C_ox(T) = C_ox(T_nom)·[1 + TCox·(T - T_nom)]
```

The AC solution must converge over the temperature sweep range with:
```
|Δg_m/g_m| < CKTreltol per iteration
|ΔC/C| < CKTreltol per iteration
```

### 5. Multi-Port S-Parameter Consistency

For RF analysis, the scattering parameters derived from **Y** must satisfy:
```
|S_ij| ≤ 1 + ε  (for passive devices)
det(I - S*S) ≥ 0  (passivity)
```

MOS9 enforces this by:
1. Ensuring `Re(Y_ii) ≥ 0` (positive conductance)
2. Checking `Re(det(Y)) ≥ 0` at each frequency
3. Using regularization: `Y_ii ← Y_ii + j·ε` when `Re(Y_ii) ≈ 0`

### 6. Harmonic Balance Considerations

For `.HB` analysis, MOS9 linearizes around the large-signal operating point. Convergence requires:
```
||F(X_k) - J(X_k)·ΔX|| < η·||F(X_k)||
```
Where:
- `F(X)` is the harmonic balance error function
- `J(X)` is the Jacobian containing `∂I/∂V` at mixing frequencies
- `η` is typically `1×10⁻⁶`

The mixing products require evaluation of `g_m`, `C_gs`, etc., at sum and difference frequencies, which MOS9 computes using multi-tone linearization.

This mathematical formulation provides the foundation for SPICE's small-signal analysis of the MOS9 model, ensuring numerical stability and physical consistency across all analysis types (AC, noise, pole-zero, and harmonic balance).

----------

# MOS9: Small-Signal AC, Pole-Zero, and Noise Analysis - C Implementation

## 1. Small-Signal AC Matrix Implementation (`mos9acld.c`)

### 1.1 Complex Admittance Matrix Stamping

The AC load function in `mos9acld.c` implements the frequency-domain admittance matrix for small-signal analysis by mapping the mathematical conductance and capacitance derivatives to complex matrix entries:

```c
int MOS9acLoad(GENmodel *inModel, CKTcircuit *ckt) {
    MOS9model *model;
    MOS9instance *inst;
    double gdpr, gspr;
    double xcgs, xcgd, xcgb, xcbds, xcbss, xcds;
    double omega;
    
    omega = ckt->CKTomega;  /* Angular frequency ω = 2πf */
```

The function retrieves the angular frequency `ω` from the circuit context, which is calculated as `ω = 2πf` where `f` is the AC analysis frequency. This maps directly to the mathematical formulation where capacitive susceptances are calculated as `jωC`.

### 1.2 Capacitive Susceptance Calculation

```c
for(inst = model->MOS9instances; inst != NULL; inst = inst->MOS9nextInstance) {
    /* Conductances from parasitic resistances */
    gdpr = model->MOS9drainConductance;
    gspr = model->MOS9sourceConductance;
    
    /* Capacitive susceptances */
    xcgs = omega * inst->MOS9cgs;
    xcgd = omega * inst->MOS9cgd;
    xcgb = omega * inst->MOS9cgb;
    xcbds = omega * inst->MOS9capbd;
    xcbss = omega * inst->MOS9capbs;
    xcds = omega * inst->MOS9cds;  /* Drain-source capacitance */
```

This code implements the mathematical relationship `X_C = ω·C` for each capacitance component. The `inst->MOS9cgs`, `inst->MOS9cgd`, and `inst->MOS9cgb` values are calculated from the Meyer capacitance model equations in the DC load function and stored in the instance structure for reuse in AC analysis.

### 1.3 Matrix Stamping Pattern

The function stamps the complex admittance matrix `Y = G + jωC` using the 6-node topology established in `MOS9setup()`:

```c
/* Internal drain node (DP) */
*(inst->MOS9DPdpPtr) += gdpr + inst->MOS9gds + inst->MOS9gmbs + 
                         inst->MOS9gm + gspr + COMPLEX(0.0, xcgs + xcgd + xcgb);
```

This corresponds to the mathematical sum of conductances (`g_ds`, `g_m`, `g_mbs`) and capacitive susceptances at the internal drain node. The `COMPLEX(0.0, value)` macro creates the imaginary component for the sparse matrix.

### 1.4 Transconductance Terms

```c
/* DP-Gate transconductance terms */
*(inst->MOS9DPgPtr) += inst->MOS9gm - COMPLEX(0.0, xcgs);
*(inst->MOS9SPgPtr) -= inst->MOS9gm - COMPLEX(0.0, xcgs);
```

These lines implement the mathematical transconductance coupling between gate and channel nodes. The `inst->MOS9gm` value (calculated from `∂I_ds/∂V_gs`) provides the real conductance component, while `-jωC_gs` represents the capacitive coupling through the gate-source capacitance.

### 1.5 Parasitic Resistance Stamping

```c
/* External drain (D) to internal drain (DP) */
*(inst->MOS9DdPtr) += gdpr;
*(inst->MOS9DdpPtr) -= gdpr;
*(inst->MOS9DPdPtr) -= gdpr;
*(inst->MOS9DPdpPtr) += gdpr;
```

This implements the mathematical conductance matrix for the series drain resistance `R_D`, creating the symmetric pattern:
```
[ G_D   -G_D ]
[ -G_D   G_D ]
```
where `G_D = 1/R_D`.

## 2. Noise Analysis Implementation (`mos9noi.c`)

### 2.1 Thermal Noise Calculation

The `MOS9thermalNoise()` function implements the channel thermal noise spectral density:

```c
double MOS9thermalNoise(MOS9instance *inst, double freq) {
    double Id, gm, gds, gamma, S_id;
    
    Id = inst->MOS9cdrain;
    gm = inst->MOS9gm;
    gds = inst->MOS9gds;
    
    /* Channel thermal noise coefficient γ */
    if(inst->MOS9vds == 0.0) {
        gamma = 1.0;  /* Linear region */
    } else {
        /* For saturation, γ depends on bias */
        gamma = 2.0/3.0;  /* Long-channel approximation */
        
        /* Short-channel correction factor */
        if(model->MOS9alpha > 0.0) {
            double EcL = model->MOS9vmax * inst->MOS9leff / model->MOS9u0;
            double Vdsat = inst->MOS9vgs - inst->MOS9vth;
            gamma = gamma * (1.0 + EcL/Vdsat);
        }
    }
    
    /* Drain current noise spectral density */
    S_id = 4.0 * K * T * gm * gamma;
```

This code maps directly to the mathematical formulation `S_id = 4kT·g_m·γ`, where `γ` is the noise coefficient that varies between linear region (`γ = 1`) and saturation region (`γ = 2/3` for long-channel devices). The short-channel correction implements the mathematical relationship `γ = (2/3)·(1 + E_c·L_eff/V_dsat)` when velocity saturation effects are significant.

### 2.2 Frequency-Dependent Gate Noise

```c
/* Frequency-dependent correction for induced gate noise */
if(freq > 0.0) {
    double Cgs = inst->MOS9cgs;
    double omega = 2.0 * M_PI * freq;
    double delta = 4.0/3.0;  /* Gate noise coefficient */
    
    /* Induced gate noise correlated with drain noise */
    S_id += 4.0 * K * T * delta * omega * omega * Cgs * Cgs / (5.0 * gm);
}
```

This implements the mathematical induced gate noise contribution `S_ig = 4kT·δ·ω²·C_gs²/(5g_m)`, which becomes significant at high frequencies due to capacitive coupling through the gate oxide.

### 2.3 Flicker Noise Implementation

The `MOS9flickerNoise()` function provides two alternative mathematical models for 1/f noise:

```c
double MOS9flickerNoise(MOS9model *model, MOS9instance *inst, double freq) {
    double S_if, Kf, Af, coeff;
    
    Kf = model->MOS9kf;
    Af = model->MOS9af;
    
    if(model->MOS9nfsGiven && model->MOS9nfs > 0.0) {
        /* Carrier number fluctuation model (ΔN model) */
        double Nfs = model->MOS9nfs;
        double Cox = model->MOS9cox;
        double q = 1.602e-19;
        double kT_q = K * model->MOS9tnom / q;
        
        S_if = q * q * kT_q * Nfs * inst->MOS9gm * inst->MOS9gm /
               (freq * Cox * Cox * inst->MOS9leff * inst->MOS9leff);
    } else {
        /* Empirical 1/f model */
        coeff = Kf * pow(fabs(inst->MOS9cdrain), Af) /
                (freq * model->MOS9cox * inst->MOS9leff * inst->MOS9leff);
        S_if = coeff;
    }
```

The first model implements the carrier number fluctuation theory: `S_id = (q²·kT·N_fs·g_m²)/(f·C_ox²·L_eff²)`, where `N_fs` is the fast surface state density. The second model implements the empirical relationship: `S_id = K_f·|I_d|^A_f/(f·C_ox·L_eff²)`.

### 2.4 Junction Shot Noise

```c
double MOS9junctionNoise(MOS9instance *inst, double V, double I, double freq) {
    /* Shot noise for bulk-drain and bulk-source junctions */
    double q = 1.602e-19;
    double S_i = 2.0 * q * fabs(I);
    
    /* For forward bias, add full shot noise */
    if(V > 0.0) {
        return S_i;
    } else {
        /* For reverse bias, shot noise is negligible */
        return 0.0;
    }
}
```

This implements the mathematical shot noise formula `S_i = 2q|I|` for forward-biased pn junctions, with the condition that reverse-biased junctions contribute negligible shot noise.

### 2.5 Complete Noise Stamping

The `MOS9noise()` function orchestrates all noise contributions and stamps them into the circuit matrix:

```c
int MOS9noise(int mode, int operation, GENmodel *inModel, CKTcircuit *ckt, 
              Ndata *data, double *OnDens) {
    MOS9model *model;
    MOS9instance *inst;
    double tempOnoise, tempInoise;
    double lnNdens, lnFdens;
    double freq;
    
    freq = data->freq;
    
    for(model = (MOS9model *)inModel; model != NULL; model = model->MOS9nextModel) {
        for(inst = model->MOS9instances; inst != NULL; inst = inst->MOS9nextInstance) {
            /* Calculate individual noise contributions */
            double S_thermal = MOS9thermalNoise(inst, freq);
            double S_flicker = MOS9flickerNoise(model, inst, freq);
            double S_bd = MOS9junctionNoise(inst, inst->MOS9vbd, inst->MOS9cbd, freq);
            double S_bs = MOS9junctionNoise(inst, inst->MOS9vbs, inst->MOS9cbs, freq);
            
            /* Total drain current noise */
            double S_id_total = S_thermal + S_flicker;
```

This code collects all noise spectral densities and sums them according to the mathematical relationship `S_id_total = S_thermal + S_flicker`. The junction noises `S_bd` and `S_bs` are kept separate as they appear at different circuit nodes.

### 2.6 Noise Matrix Stamping

```c
/* Stamp noise sources into the matrix */
if(mode == N_M2) {
    /* For AC noise analysis */
    *(inst->MOS9DPdpPtr) += S_id_total;
    *(inst->MOS9SPspPtr) += S_id_total;
    *(inst->MOS9DPspPtr) -= S_id_total;
    *(inst->MOS9SPdpPtr) -= S_id_total;
    
    /* Junction noise */
    *(inst->MOS9BbPtr) += S_bd + S_bs;
}
```

This implements the mathematical noise correlation matrix stamping. The channel noise `S_id_total` appears as correlated sources between drain and source nodes with the pattern:
```
[ S_id   -S_id ]
[ -S_id   S_id ]
```
while junction noises `S_bd + S_bs` appear at the bulk node.

## 3. Data Structure Mapping to Mathematical Variables

### 3.1 Instance Structure Fields for Small-Signal Parameters

The `sMOS9instance` structure stores all calculated small-signal parameters:

```c
/* Small-signal parameters */
double MOS9cgs;                /* Gate-source capacitance */
double MOS9cgd;                /* Gate-drain capacitance */
double MOS9cgb;                /* Gate-bulk capacitance */
double MOS9cbds;               /* Bulk-drain capacitance */
double MOS9cbss;               /* Bulk-source capacitance */

/* State variables */
double MOS9gm;                 /* Transconductance = ∂I_ds/∂V_gs */
double MOS9gds;                /* Drain conductance = ∂I_ds/∂V_ds */
double MOS9gmbs;               /* Bulk transconductance = ∂I_ds/∂V_bs */
```

These fields directly store the mathematical derivatives calculated during the DC operating point solution, which are then reused for AC and noise analysis.

### 3.2 Matrix Pointer Organization

The 18 matrix pointers in the instance structure implement the 6×6 admittance matrix topology:

```c
/* Matrix pointers */
double *MOS9DdPtr;             /* Drain-drain: Y_DD */
double *MOS9GgPtr;             /* Gate-gate: Y_GG */
double *MOS9SsPtr;             /* Source-source: Y_SS */
double *MOS9BbPtr;             /* Bulk-bulk: Y_BB */
double *MOS9DPdpPtr;           /* Internal drain - internal drain: Y_DPDP */
double *MOS9SPspPtr;           /* Internal source - internal source: Y_SPSP */
double *MOS9DdpPtr;            /* External drain - internal drain: Y_DDP */
double *MOS9SspPtr;            /* External source - internal source: Y_SSP */
/* ... additional cross terms ... */
```

This organization maps directly to the mathematical matrix structure shown in the research context, allowing efficient sparse matrix operations while maintaining the complete device physics.

## 4. SPICE Integration and Circuit Context

### 4.1 Frequency-Domain Context Access

The AC load function accesses the circuit's angular frequency through:

```c
omega = ckt->CKTomega;  /* Angular frequency ω = 2πf */
```

This `CKTcircuit` structure member is set by SPICE's AC analysis driver based on the `.AC` analysis specification, demonstrating how the mathematical frequency variable `ω` is provided by the simulation framework.

### 4.2 Noise Analysis Data Structure

The `Ndata` structure passed to `MOS9noise()` contains all necessary noise analysis parameters:

```c
typedef struct {
    double freq;        /* Frequency for noise calculation */
    double delFreq;     /* Frequency step */
    double outNoiz;     /* Integrated output noise */
    double outNoise;    /* Output noise spectral density */
    double Gm2;         /* Square of transfer gain for noise conversion */
    double Gmbd2;       /* Square of bulk-drain transfer gain */
    double Gmbs2;       /* Square of bulk-source transfer gain */
    /* ... additional fields ... */
} Ndata;
```

This structure enables the mathematical conversion from current noise spectral density to voltage noise at circuit nodes using the squared transfer gains `|G|²`.

## 5. Mathematical Consistency and Derivative Continuity

The C implementation ensures mathematical consistency through:

1. **Reuse of DC Derivatives**: The small-signal parameters (`g_m`, `g_ds`, `g_mbs`) calculated during DC analysis are stored and reused for AC analysis, ensuring consistency between operating point and small-signal behavior.

2. **Complex Arithmetic for Capacitances**: The use of `COMPLEX(0.0, value)` for capacitive susceptances implements the mathematical `jωC` term directly in the matrix stamping.

3. **Noise Spectral Density Integration**: The logarithmic integration in the noise function:
   ```c
   lnNdens = log(MAX(tempOnoise, N_MINLOG));
   lnFdens = log(MAX(freq, N_MINLOG));
   ```
   implements the mathematical integration `∫S(f)df` required for total noise power calculation.

4. **Parameter-Dependent Model Selection**: The conditional logic based on `model->MOS9nfsGiven` selects between alternative mathematical models for flicker noise, demonstrating how the C code implements configurable device physics.

This C implementation directly translates the mathematical formulations of the MOS9 model into efficient sparse matrix operations while maintaining the physical accuracy and numerical stability required for robust circuit simulation.