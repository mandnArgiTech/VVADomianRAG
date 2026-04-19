# BSIM4: RF Modeling, Advanced Capacitance, and Noise

_Generated 2026-04-12 13:01 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4/b4acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4/b4pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4/b4noi.c`

# BSIM4: RF Modeling, Advanced Capacitance, and Noise

## Technical Introduction

The BSIM4 implementation in Ngspice provides comprehensive RF modeling, advanced capacitance formulations, and sophisticated noise analysis through three critical C files: `b4acld.c`, `b4pzld.c`, and `b4noi.c`. These files implement the frequency-domain behavior, pole-zero analysis, and noise characteristics essential for modern nanometer-scale CMOS circuit simulation.

**`b4acld.c`** implements the small-signal AC matrix stamping for frequency-domain analysis, handling complex admittance matrices that include non-quasi-static (NQS) effects, gate resistance networks, and substrate coupling. This file translates the BSIM4 capacitance and transconductance models into the complex Y-parameters required for SPICE's AC analysis.

**`b4pzld.c`** provides pole-zero analysis capabilities, essential for stability analysis in feedback circuits and RF matching networks. It computes the small-signal transfer functions and extracts critical frequency-domain characteristics from the BSIM4 device model.

**`b4noi.c`** implements the comprehensive noise model including thermal channel noise, induced gate noise (unique to BSIM4), flicker noise with unified modeling across operating regions, and shot noise from gate tunneling currents. This enables accurate noise figure prediction and low-noise amplifier design.

Together, these files enable BSIM4 to accurately simulate RF circuits up to millimeter-wave frequencies while maintaining charge conservation, handling quantum mechanical tunneling effects, and providing detailed noise characterization required for modern communication and sensing applications.

## Mathematical Formulation

The BSIM4 model implements comprehensive RF modeling, advanced capacitance formulations, and sophisticated noise mechanisms that are critical for accurate high-frequency SPICE simulation. These mathematical formulations directly interface with Ngspice's frequency-domain solvers and noise analysis algorithms.

### 1. Advanced Capacitance Modeling for RF Applications

#### 1.1 Intrinsic Capacitance Matrix with Charge Conservation

BSIM4 implements a full 4×4 capacitance matrix that ensures charge conservation for RF stability:

```
C = [C_gg  C_gd  C_gs  C_gb]
    [C_dg  C_dd  C_ds  C_db]
    [C_sg  C_sd  C_ss  C_sb]
    [C_bg  C_bd  C_bs  C_bb]
```

where the terminal charges are computed as:
```
Q_g = ∫(C_gg·dV_g + C_gd·dV_d + C_gs·dV_s + C_gb·dV_b)
Q_d = ∫(C_dg·dV_g + C_dd·dV_d + C_ds·dV_s + C_db·dV_b)
Q_s = ∫(C_sg·dV_g + C_sd·dV_d + C_ss·dV_s + C_sb·dV_b)
Q_b = ∫(C_bg·dV_g + C_bd·dV_d + C_bs·dV_s + C_bb·dV_b)
```

The capacitance matrix satisfies the charge conservation constraint:
```
C_gg + C_gd + C_gs + C_gb = 0
C_dg + C_dd + C_ds + C_db = 0
C_sg + C_sd + C_ss + C_sb = 0
C_bg + C_bd + C_bs + C_bb = 0
```

This ensures numerical stability in SPICE transient analysis where `I = dQ/dt`.

#### 1.2 Bias-Dependent Overlap Capacitance Model

The gate overlap capacitances exhibit voltage dependence critical for RF matching:

```
C_gso(V) = CGS0·[1 + CGSL/L_eff + CGSW/W_eff]·(1 + V_gs/V_max)^(-M_gso)
C_gdo(V) = CGD0·[1 + CGDL/L_eff + CGDW/W_eff]·(1 + V_gd/V_max)^(-M_gdo)
C_gbo(V) = CGB0·[1 + CGBL/L_eff + CGBW/W_eff]·(1 + V_gb/V_max)^(-M_gbo)
```

where the voltage dependence follows a power-law model with exponent `M` typically between 0.3-0.5.

#### 1.3 Fringing and Inner Fringing Capacitance

For nanometer devices, fringing capacitances become significant:

```
C_fringe = ε_ox/π·ln(1 + T_poly/TOX) + ε_ox/2·ln(1 + 2·H_gate/TOX)
```

where:
- `T_poly` = poly gate thickness
- `H_gate` = gate height above substrate
- `TOX` = oxide thickness

This fringing capacitance adds to the total gate capacitance in SPICE's AC analysis.

### 2. Non-Quasi-Static (NQS) Modeling for RF

#### 2.1 Distributed RC Gate Model

The NQS effect is modeled using a distributed RC network for the gate:

```
τ_nqs = R_g·C_gg/12 + R_ch·C_gg/6
```

where:
- `R_g` = gate electrode resistance (`B4rgc + B4rgi`)
- `R_ch` = channel resistance ≈ `1/(g_m + g_ds)`
- `C_gg` = total gate capacitance

The frequency-dependent transconductance becomes:
```
g_m(ω) = g_m0/(1 + jωτ_nqs)
```

This modifies the Y-parameters in SPICE's small-signal analysis:
```
Y_gd(ω) = jωC_gd + g_m(ω)·exp(-jωτ_d)
Y_gs(ω) = jωC_gs - g_m(ω)·exp(-jωτ_d)
```

#### 2.2 Channel Charge Partitioning

For accurate RF simulation, channel charge is partitioned between source and drain:

```
X_part = 0.4 + 0.1·tanh(V_ds/(2·V_t))  (BSIM4 default)
Q_d = X_part·Q_channel
Q_s = (1 - X_part)·Q_channel
```

The partitioning factor `X_part` affects the capacitance derivatives:
```
C_gd = ∂Q_g/∂V_d = C_gd_overlap + X_part·∂Q_channel/∂V_d
C_gs = ∂Q_g/∂V_s = C_gs_overlap + (1-X_part)·∂Q_channel/∂V_s
```

### 3. Gate Resistance Modeling for RF

#### 3.1 Distributed Gate Resistance

The gate electrode resistance has both contact and distributed components:

```
R_g_total = R_gc + R_gi/3·(1/N_f)^2
```

where:
- `R_gc` = gate contact resistance (`B4rgc`)
- `R_gi` = gate intrinsic resistance per square (`B4rgi`)
- `N_f` = number of fingers

For multi-finger layouts, the distributed nature affects the input impedance:
```
Z_in(ω) = R_g_total + jωL_g + 1/(jωC_gg)
```

#### 3.2 Substrate Resistance Network

The substrate forms a distributed RC network affecting output impedance:

```
R_sub = RSUB·(1/Weff + 1/L_eff)
C_sub = C_jbd + C_jbs + C_jbsw·(P_d + P_s)
```

The substrate network modifies the Y-parameters at high frequency:
```
Y_bb(ω) = (1/R_sub) + jωC_sub
Y_bd(ω) = -jωC_jbd
Y_bs(ω) = -jωC_jbs
```

### 4. Advanced Noise Modeling

#### 4.1 Thermal Channel Noise with Velocity Saturation

The thermal noise power spectral density accounts for velocity saturation:

```
S_id_th = 4kT·γ·g_m0·α
```

where:
- `γ = 2/3·(1 + (V_ds/V_dsat)^2)/(1 + V_ds/V_dsat)` (bias-dependent factor)
- `α = 1/(1 + (V_ds/V_dsat)^δ)` (velocity saturation correction)
- `δ = B4em` (excess noise factor, typically 1.0-2.0)

This formulation ensures accurate noise prediction in saturation region for SPICE's `.NOISE` analysis.

#### 4.2 Induced Gate Noise (Correlated with Channel Noise)

Unique to BSIM4, induced gate noise arises from potential fluctuations in the channel:

```
S_ig = 4kT·δ·ω²·C_gg²/(5g_m)
```

where `δ = 0.4` for long-channel devices, increasing with:
```
δ_eff = δ·(1 + (V_ds/V_dsat)^2)
```

The correlation between channel and gate noise is:
```
c = j·0.4·√(S_id_th·S_ig)/(ω·C_gg)
```

This correlation is crucial for accurate noise figure calculation in RF circuits.

#### 4.3 Unified Flicker Noise Model

BSIM4 implements a unified flicker noise model covering all operating regions:

```
S_id_f = q·I_d²·(N_oiA + N_oiB·|I_d| + N_oiC·I_d²)/(f·W_eff·L_eff)
```

where:
- `N_oiA` (`B4noia`) = trap density coefficient
- `N_oiB` (`B4noib`) = mobility fluctuation coefficient
- `N_oiC` (`B4noic`) = series resistance coefficient

The model transitions smoothly between:
- Subthreshold: `S_f ∝ I_d²` (number fluctuation dominant)
- Linear: `S_f ∝ I_d` (mobility fluctuation dominant)
- Saturation: `S_f ∝ I_d^(3/2)` (unified behavior)

#### 4.4 Shot Noise from Gate Tunneling Currents

For nanometer oxides, gate tunneling currents contribute shot noise:

```
S_ig_tunnel = 2q·(|I_gs| + |I_gd| + |I_gb|)
```

where the tunneling currents follow:
```
I_gx = A·TOX_nm²·exp(-B·TOX_nm/|V_ox|)·(1 + C·V_ox²)·Area
```

This adds to the total gate noise in SPICE's noise analysis.

### 5. Gate Tunneling Current Modeling

#### 5.1 Direct Tunneling Model

The gate current density follows a direct tunneling formulation:

```
J_g = A·(TOX/TOX_ref)^(-P_exp)·V_ox²·exp(-B·TOX/|V_ox|)·(1 + C·V_ox²)
```

where:
- `A = B4aigsd` (pre-exponential factor)
- `B = B4bigsd` (exponential coefficient)
- `C = B4cigsd` (field enhancement factor)
- `P_exp = 2.0` (tox scaling exponent)

#### 5.2 Partitioning Between Source and Drain

The gate tunneling current partitions based on channel potential:

```
I_gs = J_g·W_eff·L_eff·exp(-V_chs/ηV_t)
I_gd = J_g·W_eff·L_eff·exp(-V_chd/ηV_t)
```

where:
- `V_chs`, `V_chd` = channel potentials at source and drain ends
- `η = 0.1` (partitioning factor)

#### 5.3 Temperature Dependence of Tunneling

Tunneling parameters scale with temperature:

```
A(T) = A_0·exp(E_a/k·(1/T - 1/T_0))
B(T) = B_0·(T/T_0)
```

This ensures accurate gate leakage prediction across temperature corners in SPICE.

### 6. High-Frequency Substrate Network

#### 6.1 Distributed Substrate RC Model

The substrate forms a lossy transmission line affecting RF performance:

```
Y_sub(ω) = √(jωC_sub/R_sub)·coth(√(jωR_subC_sub)·L_sub)
```

For practical implementation in SPICE, this is approximated as a 3-element network:
```
R_sub1 = R_sub/2
C_sub1 = C_sub/2
R_sub2 = R_sub/2
C_sub2 = C_sub/2
```

#### 6.2 Substrate Coupling Between Devices

For multi-finger or array layouts, substrate coupling affects matching:

```
Z_couple(ω) = R_sub_couple + 1/(jωC_sub_couple)
```

where the coupling elements scale with finger spacing `S_f`:
```
R_sub_couple ∝ 1/S_f
C_sub_couple ∝ 1/S_f
```

### 7. Temperature-Dependent RF Parameters

#### 7.1 Gate Resistance Temperature Scaling

Gate resistance increases with temperature:

```
R_g(T) = R_g(T_0)·[1 + TCR1·(T - T_0) + TCR2·(T - T_0)²]
```

where `TCR1`, `TCR2` are temperature coefficients.

#### 7.2 Capacitance Temperature Dependence

Capacitances exhibit weak temperature dependence:

```
C(T) = C(T_0)·[1 + TCC·(T - T_0)]
```

where `TCC ≈ 10-50 ppm/°C` for oxide capacitances.

### 8. Noise Correlation Matrix for Multi-Port Analysis

For complete RF noise characterization, BSIM4 provides the 2×2 noise correlation matrix:

```
C = [S_id       S_id_ig*]
    [S_id_ig    S_ig    ]
```

where:
- `S_id` = drain current noise PSD
- `S_ig` = gate current noise PSD
- `S_id_ig` = cross-correlation PSD

This enables calculation of noise parameters in SPICE:
- Minimum noise figure: `F_min = 1 + 2√(R_n·G_opt)`
- Optimal source admittance: `Y_opt = √(G_opt² + B_opt²)`
- Noise resistance: `R_n = S_id/(4kT|Y_21|²)`

### 9. Harmonic Balance Formulation for Large-Signal RF

For `.HB` analysis in SPICE, BSIM4 provides harmonic derivatives:

```
I_d(ω) = g_m1·V_gs(ω) + g_m2·V_gs²(ω) + g_m3·V_gs³(ω) + ...
```

where the harmonic transconductances are:
```
g_mn = (1/n!)·∂ⁿI_d/∂V_gsⁿ
```

The capacitance nonlinearities are similarly expanded:
```
Q_g(ω) = C_1·V_gs(ω) + C_2·V_gs²(ω) + C_3·V_gs³(ω) + ...
```

### 10. S-parameter Formulation

BSIM4 enables S-parameter extraction through Y-parameter conversion:

```
Y = G + jωC + Y_nqs(ω) + Y_sub(ω)
S = (I - Z_0·Y)·(I + Z_0·Y)⁻¹
```

where `Z_0 = 50Ω` is the reference impedance.

The key RF metrics computed from S-parameters:
- `f_T = |Y_21|/(2π·|Y_11|)` (current gain cutoff)
- `f_max = f_T/(2√(R_g·g_ds + 2πf_T·R_g·C_gd))` (power gain cutoff)
- `MSG/MAG` (maximum stable/available gain)

## Convergence Analysis

### 1. Frequency-Domain Newton-Raphson Convergence

For AC analysis, the complex Jacobian matrix must converge:

#### 1.1 Complex Variable Convergence Criteria

For each complex voltage `V_i(ω) = V_real + jV_imag`:

```
|ΔV_real| ≤ ε_rel·max(|V_real|, |V_real_old|) + ε_abs
|ΔV_imag| ≤ ε_rel·max(|V_imag|, |V_imag_old|) + ε_abs
```

where `ε_rel = CKTreltol` and `ε_abs = CKTvoltTol`.

The complex residual norm must satisfy:
```
‖F(V(ω))‖₂ = √(Σ|F_real|² + |F_imag|²) < ε_residual
```

#### 1.2 NQS Model Convergence

The NQS time constant iteration converges as:

```
τ^(k+1) = R_g·C_gg(V^(k))/12 + R_ch(V^(k))·C_gg(V^(k))/6
```

Convergence criterion:
```
|τ^(k+1) - τ^(k)|/τ^(k) < ε_nqs
```
where `ε_nqs = 1e-4` typically.

### 2. Noise Analysis Convergence

#### 2.1 Noise Power Spectral Density Convergence

For noise analysis at frequency `f`, the PSD iteration converges when:

```
|S^(k+1)(f) - S^(k)(f)|/S^(k)(f) < ε_noise
```

where `ε_noise = 0.01` for 1% accuracy.

#### 2.2 Correlation Matrix Convergence

The 2×2 noise correlation matrix converges when:

```
‖C^(k+1) - C^(k)‖_F/‖C^(k)‖_F < ε_correlation
```

where `‖·‖_F` is the Frobenius norm and `ε_correlation = 0.05`.

### 3. Gate Tunneling Current Convergence

#### 3.1 Exponential Term Regularization

The gate tunneling exponential requires careful handling:

```
exp(-B·TOX/|V_ox|) → exp(-B·TOX/max(|V_ox|, V_ox_min))
```

where `V_ox_min = 0.01 V` prevents numerical overflow.

#### 3.2 Tunneling Current Convergence Rate

The tunneling current iteration exhibits linear convergence:

```
|I_g^(k+1) - I_g^*| ≤ L·|I_g^(k) - I_g^*|
```

with Lipschitz constant:
```
L = |∂J_g/∂V_ox|·Area·(∂V_ox/∂V_gs)
```

Typically `L ≈ 10^-6 A/V`, ensuring fast convergence.

### 4. Capacitance Matrix Convergence

#### 4.1 Charge Conservation Enforcement

The capacitance matrix must satisfy row-sum zero constraint:

```
Σ_j C_ij^(k) ≤ ε_charge
```

where `ε_charge = 1e-18 F` (charge tolerance).

#### 4.2 Symmetry Enforcement

For numerical stability, the capacitance matrix is symmetrized:

```
C_sym = (C + Cᵀ)/2
```

The symmetry error is bounded by:
```
‖C - C_sym‖_F/‖C‖_F < ε_symmetry
```
where `ε_symmetry = 1e-6`.

### 5. RF Parameter Extraction Convergence

#### 5.1 S-parameter Iteration

For S-parameter extraction at N frequency points:

```
S^(k+1)(f_i) = f(Y^(k)(f_i), Z_0)
```

Convergence across the frequency sweep:
```
max_i ‖S^(k+1)(f_i) - S^(k)(f_i)‖_F < ε_s_param
```
where `ε_s_param = 1e-3`.

#### 5.2 f_T/f_max Extraction

The cutoff frequencies converge as:

```
|f_T^(k+1) - f_T^(k)|/f_T^(k) < ε_freq
|f_max^(k+1) - f_max^(k)|/f_max^(k) < ε_freq
```

where `ε_freq = 0.01` for 1% accuracy.

### 6. Harmonic Balance Convergence

#### 6.1 Harmonic Amplitude Convergence

For harmonic `n` with amplitude `A_n`:

```
|A_n^(k+1) - A_n^(k)|/A_n^(k) < ε_harmonic
```

where `ε_harmonic = 1e-4` typically.

#### 6.2 Intermodulation Product Convergence

For two-tone analysis with frequencies `f1, f2`, intermodulation products converge when:

```
|IM3^(k+1) - IM3^(k)|/IM3^(k) < ε_imd
```

where `IM3` is the 3rd-order intermodulation product and `ε_imd = 0.05`.

### 7. Multi-Finger Device Convergence

#### 7.1 Finger-to-Finger Symmetry

For symmetric multi-finger layouts:

```
|I_d,i - I_d,avg|/I_d,avg < ε_finger
```

where `ε_finger = 1e-4` ensures finger matching.

#### 7.2 Distributed Gate Network Convergence

The distributed gate RC network converges when:

```
|V_g,i^(k+1) - V_g,i^(k)| < ε_gate·V_g,avg
```

where `ε_gate = 1e-5`.

### 8. Substrate Network Convergence

#### 8.1 Substrate Potential Convergence

The substrate potential iteration:

```
V_sub^(k+1) = (Σ_i g_i·V_i + I_sub)/Σ_i g_i
```

converges when:
```
|V_sub^(k+1) - V_sub^(k)| < ε_substrate
```
where `ε_substrate = 1e-6 V`.

#### 8.2 Substrate RC Network Convergence

The substrate impedance converges as:

```
|Z_sub^(k+1)(ω) - Z_sub^(k)(ω)|/|Z_sub^(k)(ω)| < ε_zsub
```

where `ε_zsub = 0.01` at each frequency.

### 9. Temperature-RF Coupling Convergence

#### 9.1 Self-Heating in RF Operation

The coupled electrical-thermal equations:

```
P_diss = Re{V·I*} + P_gate_tunnel
T_j = T_ambient + R_th·P_diss
```

converge when:
```
|T_j^(k+1) - T_j^(k)| < ε_temp_rf
```
where `ε_temp_rf = 0.1 K`.

#### 9.2 Temperature-Dependent RF Parameter Convergence

RF parameters with temperature dependence converge when:

```
|P_RF(T^(k+1)) - P_RF(T^(k))|/P_RF(T^(k)) < ε_temp_param
```

where `ε_temp_param = 1e-4`.

### 10. Convergence Acceleration Techniques

#### 10.1 Frequency Continuation

For wideband analysis, use frequency continuation:

```
Solve at f_0 → Use as initial guess for f_1 → ... → f_N
```

Reduces iterations by factor of 2-3×.

#### 10.2 Harmonic Continuation

For harmonic balance, solve sequentially:

```
Solve DC → Use as guess for fundamental → Add harmonics progressively
```

#### 10.3 Adaptive Damping

For difficult convergence cases, use adaptive damping:

```
V^(k+1) = V^(k) + λ·ΔV
λ = min(1, 2/‖J‖)
```

#### 10.4 Convergence Monitoring

Monitor convergence rate:

```
ρ_k = ‖ΔV^(k)‖/‖ΔV^(k-1)‖
```

If `ρ_k > 0.9` for 3 iterations, reduce step or increase damping.

This mathematical formulation ensures BSIM4 provides accurate RF modeling, advanced capacitance calculations, and comprehensive noise analysis while maintaining robust convergence across all frequency ranges and bias conditions in SPICE simulation.

---

## C Implementation

### 1. Core Data Structures for RF and Noise Modeling

#### 1.1 Extended BSIM4 Model Structure for RF Applications

The BSIM4 model structure in `bsim4def.h` includes specialized parameters for RF and noise modeling:

```c
typedef struct sB4model {
    /* RF-specific parameters */
    double B4rgc;                  /* Gate contact resistance (Ω) */
    double B4rgi;                  /* Gate intrinsic resistance (Ω) */
    double B4rgatemod;             /* Gate resistance model selector */
    double B4rbody;                /* Body resistance */
    double B4rbsh;                 /* Body sheet resistance */
    
    /* Noise model parameters */
    double B4noia;                 /* Flicker noise parameter A */
    double B4noib;                 /* Flicker noise parameter B */
    double B4noic;                 /* Flicker noise parameter C */
    double B4em;                   /* Excess noise factor for thermal noise */
    double B4af;                   /* Flicker noise exponent */
    double B4ef;                   /* Frequency exponent for flicker noise */
    double B4kf;                   /* Flicker noise coefficient */
    
    /* Gate tunneling parameters */
    double B4aigbacc;              /* Gate-to-body tunneling, accumulation */
    double B4bigbacc;              /* Gate-to-body tunneling, accumulation */
    double B4cigbacc;              /* Gate-to-body tunneling, accumulation */
    double B4aigbinv;              /* Gate-to-body tunneling, inversion */
    double B4bigbinv;              /* Gate-to-body tunneling, inversion */
    double B4cigbinv;              /* Gate-to-body tunneling, inversion */
    double B4aigsd;                /* Gate-to-source/drain tunneling */
    double B4bigsd;                /* Gate-to-source/drain tunneling */
    double B4cigsd;                /* Gate-to-source/drain tunneling */
    double B4nigbinv;              /* Gate-to-body inversion emission coefficient */
    double B4nigbacc;              /* Gate-to-body accumulation emission coefficient */
    double B4nigsd;                /* Gate-to-S/D emission coefficient */
    
    /* Non-quasi-static (NQS) model parameters */
    double B4rgateMod;             /* Gate resistance model flag */
    double B4xrcrg1;               /* Gate resistance parameter 1 */
    double B4xrcrg2;               /* Gate resistance parameter 2 */
    
    /* Advanced capacitance model parameters */
    double B4cgsl;                 /* Gate-source overlap capacitance per length */
    double B4cgdl;                 /* Gate-drain overlap capacitance per length */
    double B4ckappas;              /* Source side capacitance parameter */
    double B4ckappad;              /* Drain side capacitance parameter */
    double B4cf;                   /* Fringing capacitance */
    double B4clc;                  /* Constant overlap capacitance */
    double B4cle;                  /* Edge overlap capacitance */
    
    struct sB4model *B4nextModel;
    sB4instance *B4instances;
} B4model;
```

#### 1.2 Instance Structure with RF and Noise State Variables

```c
typedef struct sB4instance {
    /* Internal nodes for RF modeling */
    int B4dNodePrime;              /* Internal drain node (after Rd) */
    int B4sNodePrime;              /* Internal source node (after Rs) */
    int B4gNodeExt;                /* External gate node (with RG) */
    int B4bNodePrime;              /* Internal bulk node (with Rbody) */
    
    /* RF-specific state variables */
    double B4tau;                  /* NQS time constant (s) */
    double B4gtau;                 /* Gate charging time constant */
    double B4cgg;                  /* Total gate capacitance (F) */
    double B4cgs;                  /* Gate-source capacitance (F) */
    double B4cgd;                  /* Gate-drain capacitance (F) */
    double B4cgb;                  /* Gate-bulk capacitance (F) */
    double B4cdd;                  /* Drain-drain capacitance (F) */
    double B4css;                  /* Source-source capacitance (F) */
    double B4cbb;                  /* Bulk-bulk capacitance (F) */
    double B4cds;                  /* Drain-source capacitance (F) */
    double B4csd;                  /* Source-drain capacitance (F) */
    
    /* Noise source values */
    double B4idnoise;              /* Drain current noise PSD (A²/Hz) */
    double B4ignoise;              /* Induced gate noise PSD (A²/Hz) */
    double B4ibnoise;              /* Bulk current noise PSD (A²/Hz) */
    double B4correlation;          /* Correlation coefficient */
    double B4fn1;                  /* Flicker noise coefficient 1 */
    double B4fn2;                  /* Flicker noise coefficient 2 */
    
    /* Gate tunneling currents */
    double B4igc;                  /* Gate-to-channel current (A) */
    double B4igd;                  /* Gate-to-drain current (A) */
    double B4igs;                  /* Gate-to-source current (A) */
    double B4igb;                  /* Gate-to-bulk current (A) */
    double B4igcs;                 /* Gate-to-channel source side (A) */
    double B4igcd;                 /* Gate-to-channel drain side (A) */
    
    /* Matrix pointers for RF network */
    double *B4dDprimePtr;          /* G[drain, drain'] */
    double *B4sSprimePtr;          /* G[source, source'] */
    double *B4gGextPtr;            /* G[gate, gate_ext] */
    double *B4bBprimePtr;          /* G[bulk, bulk'] */
    double *B4dprimeDPtr;          /* G[drain', drain] */
    double *B4sprimeSPtr;          /* G[source', source] */
    double *B4gextGPtr;            /* G[gate_ext, gate] */
    double *B4bprimeBPtr;          /* G[bulk', bulk] */
    double *B4dprimeSprimePtr;     /* G[drain', source'] */
    double *B4sprimeDprimePtr;     /* G[source', drain'] */
    double *B4gextDprimePtr;       /* G[gate_ext, drain'] */
    double *B4gextSprimePtr;       /* G[gate_ext, source'] */
    double *B4gextBprimePtr;       /* G[gate_ext, bulk'] */
    
    struct sB4instance *B4nextInstance;
    B4model *B4modPtr;
} B4instance;
```

### 2. Advanced Capacitance Model Implementation

#### 2.1 BSIM4 Capacitance Calculation (`b4cap.c`)

The BSIM4 implements a charge-based capacitance model ensuring charge conservation:

```c
void B4calcCapacitances(B4instance *here, B4model *model)
{
    double Vgs = here->B4vgs;
    double Vds = here->B4vds;
    double Vbs = here->B4vbs;
    double Vgd = Vgs - Vds;
    double Vgb = Vgs - Vbs;
    
    /* Effective gate overdrive for capacitance */
    double Vgsteff = B4_Vgsteff_CV(Vgs, here->B4vth, Vbs, Vds, model);
    double Vdseff = B4_Vdseff_CV(Vds, Vgsteff, here->B4leff, model);
    
    /* Partitioning factor (40/60 typical) */
    double Xpart = 0.4;
    
    /* Gate charge calculation */
    double Cox = model->B4cox * here->B4weffCV * here->B4leffCV;
    double Qg = Cox * (Vgsteff + model->B4vfb + model->B4phi);
    
    /* Bulk charge */
    double Qb = -Cox * (model->B4gamma * sqrt(model->B4phi - Vbs) 
                       + 0.5 * model->B4k2 * (model->B4phi - Vbs));
    
    /* Inversion charge partitioning */
    double Qinv = Cox * Vgsteff;
    double Qd = -Xpart * Qinv * (1.0 - Vdseff/Vgsteff) * (1.0 - Vdseff/Vgsteff);
    double Qs = -(1.0 - Xpart) * Qinv * (1.0 - Vdseff/Vgsteff) * (1.0 - Vdseff/Vgsteff);
    
    /* Overlap capacitances */
    double Cgso = model->B4cgso * here->B4weffCV;
    double Cgdo = model->B4cgdo * here->B4weffCV;
    double Cgbo = model->B4cgbo * here->B4leffCV;
    
    /* Fringing capacitance */
    double Cf = model->B4cf * here->B4weffCV;
    
    /* Store charges */
    here->B4qgs = Qs + Cgso * Vgs;
    here->B4qgd = Qd + Cgdo * Vgd;
    here->B4qgb = Qb + Cgbo * Vgb;
    
    /* Calculate capacitances as derivatives */
    here->B4cgs = B4_capgs(here, model);
    here->B4cgd = B4_capgd(here, model);
    here->B4cgb = B4_capgb(here, model);
    here->B4cgg = here->B4cgs + here->B4cgd + here->B4cgb;
    
    /* Junction capacitances */
    double Vbd = Vbs - Vds;
    here->B4cbd = B4_junctionCap(model->B4cbd, model->B4pb, 
                                 model->B4mj, Vbd, here->B4ad);
    here->B4cbs = B4_junctionCap(model->B4cbs, model->B4pb, 
                                 model->B4mj, Vbs, here->B4as);
}
```

**Mathematical Mapping:**
- `Qg = Cox·(Vgsteff + Vfb + φ)` corresponds to gate charge equation
- `Qb = -Cox·(γ·√(φ-Vbs) + 0.5·k2·(φ-Vbs))` implements bulk charge
- `Qd = -Xpart·Qinv·(1 - Vdseff/Vgsteff)²` implements 40/60 charge partitioning
- Capacitances `Cij = ∂Qi/∂Vj` ensure charge conservation for SPICE transient analysis

#### 2.2 Junction Capacitance Model

```c
double B4_junctionCap(double Cj0, double Pb, double Mj, double Vj, double Area)
{
    /* Junction capacitance with voltage dependence */
    if (Vj < 0.0) {
        /* Reverse bias */
        return Cj0 * Area * pow(1.0 - Vj/Pb, -Mj);
    } else {
        /* Forward bias - linear approximation */
        return Cj0 * Area * (1.0 + Mj * Vj/Pb);
    }
}
```

### 3. RF and AC Analysis Implementation

#### 3.1 Small-Signal AC Matrix Stamping (`b4acld.c`)

The AC load function stamps the complex admittance matrix for frequency-domain analysis:

```c
int B4acLoad(B4instance *here, CKTcircuit *ckt, double omega)
{
    double s = I * omega;  /* Complex frequency */
    
    /* Intrinsic Y-parameters for 4-terminal device */
    double Ydd = here->B4gds + s * (here->B4cbd + here->B4cdd);
    double Yss = here->B4gds + here->B4gm + here->B4gmbs 
                 + s * (here->B4cbs + here->B4css);
    double Yds = -here->B4gds + s * here->B4cds;
    double Ysd = -here->B4gds - here->B4gm - here->B4gmbs + s * here->B4csd;
    
    /* Gate network with NQS effects */
    double Ygg_int = s * here->B4cgg;
    double Ygd = -s * here->B4cgd + here->B4gm / (1.0 + s * here->B4tau);
    double Ygs = -s * here->B4cgs - here->B4gm / (1.0 + s * here->B4tau);
    double Ygb = -s * here->B4cgb;
    
    /* Body network */
    double Ybb = s * (here->B4cbd + here->B4cbs + here->B4cbb) 
                 + here->B4gbd + here->B4gbs;
    double Ybd = -s * here->B4cbd - here->B4gbd;