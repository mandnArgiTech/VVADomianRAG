# MOS1: Small-Signal AC, Pole-Zero, and Noise Analysis

_Generated 2026-04-12 03:54 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1noi.c`

# Chapter: MOS1: Small-Signal AC, Pole-Zero, and Noise Analysis

## Introduction

The MOS1 small-signal AC, pole-zero, and noise analysis subsystem in Ngspice implements the frequency-domain characterization essential for analog and RF circuit design. The files `mos1acld.c`, `mos1pzld.c`, and `mos1noi.c` collectively provide the computational engine for linearized frequency response, stability analysis, and noise performance evaluation. `mos1acld.c` implements the `MOS1acLoad()` function that stamps the complex admittance matrix `Y(ω) = G + jωC` into the circuit's linear system for AC analysis, where `G` contains the small-signal conductances and `C` the charge storage capacitances. `mos1pzld.c` provides `MOS1pzLoad()` for pole-zero analysis, extending the formulation to complex frequency `s = σ + jω` to compute system poles and zeros critical for stability assessment. `mos1noi.c` implements `MOS1noise()` which computes spectral noise densities for thermal (Johnson-Nyquist) and flicker (1/f) noise sources, enabling signal-to-noise ratio calculations and noise figure analysis. These implementations leverage pre-computed small-signal parameters (`gm`, `gds`, `gmb`) and capacitances from DC operating point analysis, ensuring computational efficiency while maintaining physical accuracy across frequency.

---

## Mathematical Formulation

### Small-Signal AC Analysis

The MOS1 small-signal AC analysis solves the linearized frequency-domain equations around the DC operating point. The formulation uses complex admittance matrices to represent both conductive and capacitive effects.

#### Complex Admittance Matrix Formulation

For AC analysis at angular frequency ω = 2πf, the device contributes to the nodal admittance matrix:

```
Y(ω) = G + jωC
```

where `G` is the conductance matrix from DC small-signal analysis and `C` is the capacitance matrix representing all charge storage effects.

#### Conductance Matrix from DC Operating Point

The 4×4 conductance matrix `G` contains the small-signal conductances evaluated at the DC bias point:

```
G = [gds + gbd        gm          -(gds + gm + gmb)   gmb - gbd]
    [0                0           0                   0        ]  (Gate node)
    [-gds            -gm          gds + gbs           gmb - gbs]
    [-gbd             0           -gbs                gbd + gbs]
```

where:
- `gm = ∂Id/∂Vgs` is the transconductance
- `gds = ∂Id/∂Vds` is the output conductance
- `gmb = ∂Id/∂Vsb` is the body transconductance
- `gbd = ∂Ibd/∂Vbd` is the bulk-drain diode conductance
- `gbs = ∂Ibs/∂Vbs` is the bulk-source diode conductance

#### Capacitance Matrix Formulation

The capacitance matrix `C` represents the complete charge storage network:

```
C = [Cgd + Cbd    -Cgd         0          -Cbd]
    [-Cgd         Cgs + Cgd + Cgb  -Cgs   -Cgb]
    [0           -Cgs          Cgs + Cbs  -Cbs]
    [-Cbd        -Cgb          -Cbs       Cgb + Cbd + Cbs]
```

The capacitances are computed from both intrinsic and extrinsic components:

##### Intrinsic Capacitances (Bias-Dependent)

**Gate-Channel Capacitances:**
```
Cgs = ∂Qg/∂Vgs = Cox·Weff·Leff·fgs(Vgs, Vds, Vbs)
Cgd = ∂Qg/∂Vgd = Cox·Weff·Leff·fgd(Vgs, Vds, Vbs)
Cgb = ∂Qg/∂Vgb = Cox·Weff·Leff·fgb(Vgs, Vds, Vbs)
```

where `Cox = ε₀ₓ/tox` is the oxide capacitance per unit area, and the functions `fgs`, `fgd`, `fgb` represent the charge partitioning between terminals based on operating region.

##### Extrinsic Capacitances (Bias-Dependent Junctions)

**Bulk Junction Capacitances:**
```
Cbd = CBD·AD·f(Vbd) + CJSW·PD·f(Vbd)
Cbs = CBS·AS·f(Vbs) + CJSW·PS·f(Vbs)
```

where `f(V) = (1 - V/PB)^(-MJ)` for reverse bias and follows the linear approximation for forward bias.

##### Overlap Capacitances (Bias-Independent)

```
Cgso = CGSO·Weff
Cgdo = CGDO·Weff
Cgbo = CGBO·Leff
```

These are added to the corresponding intrinsic capacitances.

#### Complete AC System Equation

The AC analysis solves the complex linear system:

```
[G + jωC]·[V(ω)] = [I(ω)]
```

where `V(ω)` is the complex node voltage vector and `I(ω)` is the complex current source vector. The solution provides magnitude and phase response across frequency.

### Pole-Zero Analysis

Pole-zero analysis extends the AC formulation to the complex frequency domain `s = σ + jω` to find system poles and zeros.

#### Complex Frequency Domain Formulation

The system matrix for pole-zero analysis is:

```
M(s) = G + sC
```

where `s` is the complex frequency variable. This represents the Laplace transform of the linearized time-domain equations.

#### Pole Calculation

The poles of the system are the values of `s` for which:

```
det[M(s)] = 0
```

For the MOS1 device, the characteristic equation is a polynomial in `s`:

```
a₄s⁴ + a₃s³ + a₂s² + a₁s + a₀ = 0
```

The coefficients `aᵢ` are functions of the conductances and capacitances. The four poles typically represent:
1. **Input pole**: Dominated by `Cgs` and source resistance
2. **Output pole**: Dominated by `Cgd` and load capacitance
3. **Bulk poles**: From bulk junction capacitances `Cbd`, `Cbs`
4. **Gate-bulk pole**: From `Cgb`

#### Zero Calculation

The zeros of transfer functions (e.g., `Vout/Vin`) are found by solving:

```
N(s) = 0
```

where `N(s)` is the numerator polynomial of the transfer function. For common-source configuration, the right-half-plane zero occurs at:

```
s_z = gm / Cgd
```

This zero limits bandwidth and affects stability.

#### Pole-Zero Patterns by Operating Region

**Cutoff Region:**
- All capacitances are approximately constant (depletion capacitances)
- Poles determined by `Cgb`, `Cbd`, `Cbs`
- No zeros from transconductance

**Triode Region:**
- `Cgs ≈ Cgd ≈ Cox·Weff·Leff/2`
- Poles shift with `Vds`
- Real poles dominate

**Saturation Region:**
- `Cgs ≈ (2/3)Cox·Weff·Leff`
- `Cgd ≈ Cgdo` (overlap capacitance dominates)
- Complex conjugate poles possible with inductive loads
- Right-half-plane zero at `s = gm/Cgd`

### Noise Analysis

The MOS1 noise analysis implements physically-based noise models for both thermal and flicker noise sources.

#### Thermal Noise Models

##### Channel Thermal Noise

The channel thermal noise spectral density depends on operating region:

**Triode Region (Vds ≤ Vgs - Vth):**
```
S_Id(f) = 4kT·gds
```
where `gds = ∂Id/∂Vds` is the output conductance.

**Saturation Region (Vds > Vgs - Vth):**
```
S_Id(f) = γ·(8/3)kT·gm
```
where `γ = 2/3` for long-channel devices (model parameter), and `gm = ∂Id/∂Vgs` is the transconductance.

The factor `γ` accounts for non-uniform channel charge distribution and hot-carrier effects.

##### Parasitic Resistance Thermal Noise

**Drain Resistance Noise:**
```
S_Vrd(f) = 4kT·Rd
```
or equivalently as current noise:
```
S_Ird(f) = 4kT/Rd = 4kT·gd
```
where `gd = 1/Rd`.

**Source Resistance Noise:**
```
S_Vrs(f) = 4kT·Rs
```
or:
```
S_Irs(f) = 4kT/Rs = 4kT·gs
```
where `gs = 1/Rs`.

#### Flicker (1/f) Noise Model

The SPICE 2G.6 flicker noise model implements:

```
S_Id(f) = KF · gm² / (Cox · Weff · Leff · f^AF)
```

where:
- `KF`: Flicker noise coefficient (model parameter `MOS1kf`)
- `AF`: Flicker noise exponent (model parameter `MOS1af`, typically ≈1)
- `Cox = ε₀ₓ/tox`: Oxide capacitance per unit area
- `Weff`, `Leff`: Effective channel dimensions
- `f`: Frequency in Hz

This model assumes the noise originates from carrier trapping at the Si-SiO₂ interface, with spectral density inversely proportional to frequency.

#### Gate-Induced Noise

For RF applications, gate noise correlation is important but not implemented in basic MOS1 model. The complete RF noise model would include:

```
S_Ig(f) = δ·(4kT)·ω²Cgs²/(5gm)
```
with correlation coefficient:
```
c = j·0.395 (approximately)
```

#### Total Noise Spectral Density

The total drain current noise spectral density is the sum of uncorrelated components:

```
S_Id,total(f) = S_Id,thermal(f) + S_Id,flicker(f) + S_Ird(f)·|Hrd(f)|² + S_Irs(f)·|Hrs(f)|²
```

where `Hrd(f)` and `Hrs(f)` are transfer functions from resistance noise sources to drain current.

#### Input-Referred Noise

For amplifier design, input-referred noise voltage spectral density is:

```
S_Vn,in(f) = S_Id,total(f) / gm²
```

This allows comparison with source impedance noise.

#### Noise Integration

For noise analysis over a frequency band `[f₁, f₂]`:

```
Total noise power = ∫_{f₁}^{f₂} S(f) df
```

For flicker noise with `AF = 1`:
```
∫_{f₁}^{f₂} K/f df = K·ln(f₂/f₁)
```

## Convergence Analysis

### Frequency-Domain Convergence

#### AC Analysis Numerical Stability

The complex matrix equation `[G + jωC]·V = I` must be solved accurately across a wide frequency range. The condition number:

```
κ(ω) = ||G + jωC||·||(G + jωC)⁻¹||
```

varies with frequency. At low frequencies (`ω → 0`), `κ ≈ ||G||·||G⁻¹||`. At high frequencies (`ω → ∞`), `κ ≈ ω·||C||·||C⁻¹||`.

Ill-conditioning occurs when:
1. **Low frequency with poor DC convergence**: If `G` is ill-conditioned
2. **High frequency with small capacitances**: When `ωC` dominates but `C` has near-zero eigenvalues

#### Pole-Zero Extraction Convergence

The pole-zero analysis solves `det[G + sC] = 0`. For numerical root finding:

##### Newton-Raphson for Complex Roots

For finding root `sₖ`:
```
sₖ⁽ⁿ⁺¹⁾ = sₖ⁽ⁿ⁾ - det[M(sₖ⁽ⁿ⁾)] / (d/ds det[M(s)])|_(s=sₖ⁽ⁿ⁾)
```

Convergence requires:
```
|det[M(sₖ⁽ⁿ⁾)]| < ε_abs + ε_rel·|det[M(sₖ⁽⁰⁾)]|
```

The derivative computation uses:
```
d/ds det[M(s)] = det[M(s)]·tr[M⁻¹(s)·C]
```

##### Initial Guess Strategy

Poles are initially estimated from RC time constants:
```
s_initial ≈ -1/(R_eq·C_eq)
```
where `R_eq` and `C_eq` are equivalent resistances and capacitances from each node.

#### Frequency Sweep Convergence

For AC analysis with frequency sweep `f_min` to `f_max`, the step size `Δf` affects accuracy and convergence:

##### Adaptive Frequency Stepping

Based on phase change between points:
```
Δf_next = min(Δf_max, Δf_current·(Δφ_max/Δφ_current))
```
where `Δφ_max` is the maximum allowed phase change per step (typically 5-10 degrees).

##### Resonance Handling

Near resonant frequencies where `Im[Y(ω)] ≈ 0`, finer frequency steps are needed to capture peak responses accurately.

### Noise Analysis Convergence

#### Noise Spectral Integration

The total noise over bandwidth `[f₁, f₂]` is computed by numerical integration:

```
P_noise = Σ_{i=1}^{N-1} [S(f_i) + S(f_{i+1})]/2 · Δf_i
```

Convergence requires the integration error estimate:

```
Error = |P_noise(fine) - P_noise(coarse)| < ε_abs + ε_rel·P_noise
```

#### Flicker Noise Integration Challenges

The 1/f noise integral diverges as `f → 0`. In practice, a lower frequency limit `f_min` is set:

```
∫_{f_min}^{f₂} K/f df = K·ln(f₂/f_min)
```

The choice of `f_min` affects results. Typical values: `f_min = 0.1 Hz` to `1 Hz`.

#### Thermal Noise Convergence

Thermal noise spectral density is frequency-independent (white noise), so integration is straightforward:

```
P_thermal = S_thermal·(f₂ - f₁)
```

Numerical issues arise only if `f₂ - f₁` is extremely large (overflow) or small (underflow).

### Small-Signal Parameter Consistency

#### Operating Point Sensitivity

The small-signal parameters `gm`, `gds`, `gmb` are computed from DC operating point derivatives. Their accuracy depends on DC convergence:

```
δgm/gm ≈ (∂²Id/∂Vgs²)/(∂Id/∂Vgs)·δVgs
```

Tighter DC convergence (`δVgs` smaller) improves AC accuracy.

#### Capacitance Consistency

The capacitances `Cgs`, `Cgd`, `Cgb` must satisfy charge conservation:

```
Cgs + Cgd + Cgb = Cox·Weff·Leff + Cgso·Weff + Cgdo·Weff + Cgbo·Leff
```

Numerical errors in capacitance computation can violate this constraint, affecting AC response accuracy.

### Numerical Precision in Complex Arithmetic

#### Complex Matrix Solution

Solving `[G + jωC]·V = I` requires complex arithmetic. The real and imaginary parts are stored separately in SPICE:

```
[G  -ωC] [V_real]   [I_real]
[ωC  G ] [V_imag] = [I_imag]
```

This 2N×2N real system must be solved accurately. The condition number increases by factor up to `√2` compared to the N×N complex system.

#### Pole-Zero Numerical Accuracy

Pole-zero locations are sensitive to numerical precision. Relative error in pole location:

```
|δs/s| ≈ κ(M)·(|δG|/|G| + |δC|/|C|)
```

For closely spaced poles (nearly degenerate), extraction becomes ill-conditioned.

### Frequency Scaling for Numerical Stability

#### Normalized Frequency

To improve numerical conditioning, frequencies are often normalized:

```
ω_norm = ω/ω_ref
```
where `ω_ref` is a reference frequency (e.g., unity gain frequency).

The normalized system is:
```
[G + jω_norm·(ω_ref·C)]·V = I
```

This prevents extremely large or small matrix entries at frequency extremes.

#### Capacitance Scaling

For very small capacitances (e.g., `Cgd` in saturation), numerical underflow can occur. The implementation uses:

```
if(C < C_min) C = C_min
```
where `C_min ≈ 1e-18 F` prevents division by zero.

### Noise Correlation and Convergence

#### Uncorrelated Noise Source Assumption

The implementation assumes noise sources are uncorrelated. For advanced noise analysis (e.g., induced gate noise), correlations would be needed:

```
S_total = Σ_i Σ_j H_i·H_j*·C_ij
```
where `C_ij` is the noise correlation matrix.

#### Convergence in Presence of Multiple Noise Sources

When multiple noise sources contribute, the total noise converges as:

```
|P_total⁽ⁿ⁺¹⁾ - P_total⁽ⁿ⁾| < ε_abs + ε_rel·P_total⁽ⁿ⁾
```

where `n` indexes included noise sources. The dominant source (usually channel thermal noise) converges first, with flicker noise requiring more careful integration.

### Frequency-Dependent Parameter Convergence

#### Small-Signal Parameter Frequency Dependence

At high frequencies, small-signal parameters become frequency-dependent:

```
gm(ω) = gm(0)/(1 + jωτ)
```
where `τ` is the transit time.

The MOS1 model assumes frequency-independent parameters, which is valid for:
```
f << f_T = gm/(2πCgs)
```
where `f_T` is the transition frequency.

#### Convergence Beyond Model Limits

When simulation frequency approaches `f_T`, the model assumptions break down. Convergence monitoring should detect this:

```
if(f > 0.1·f_T) issue warning: "Frequency approaching model limits"
```

This ensures users are aware of potential inaccuracies in high-frequency simulations.

---

## C Implementation

### Small-Signal AC Analysis Implementation

The AC analysis implementation in `mos1acld.c` directly computes and stamps the complex admittance matrix `Y(ω) = G + jωC` into the circuit's linear system.

#### Core AC Load Function

The `MOS1acLoad()` function implements the frequency-domain matrix stamping:

```c
int MOS1acLoad(GENmodel *inModel, CKTcircuit *ckt) {
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    double gdpr, gspr;
    double xgs, xgd, xgb, xbd, xbs;
    double cgs, cgd, cgb, cbd, cbs;
    double omega;  /* Angular frequency = 2*pi*f */

    omega = ckt->CKTomega;  /* 2 * M_PI * frequency */

    for(; model != NULL; model = model->MOS1nextModel) {
        for(inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            
            /* Extract small-signal parameters from operating point */
            double gm = inst->MOS1gm;      /* Transconductance */
            double gds = inst->MOS1gds;    /* Drain-source conductance */
            double gmb = inst->MOS1gmb;    /* Bulk transconductance */
            double gbd = inst->MOS1gbd;    /* Bulk-drain conductance */
            double gbs = inst->MOS1gbs;    /* Bulk-source conductance */
            
            /* Extract capacitances */
            cgs = inst->MOS1cgs;
            cgd = inst->MOS1cgd;
            cgb = inst->MOS1cgb;
            cbd = inst->MOS1cbd;
            cbs = inst->MOS1cbs;
            
            /* Calculate admittances: Y = G + jωC */
            xgs = omega * cgs;
            xgd = omega * cgd;
            xgb = omega * cgb;
            xbd = omega * cbd;
            xbs = omega * cbs;
```

The code extracts pre-computed small-signal parameters (`gm`, `gds`, `gmb`, `gbd`, `gbs`) and capacitances (`cgs`, `cgd`, `cgb`, `cbd`, `cbs`) from the instance structure, which were calculated during DC analysis. The angular frequency `ω` is obtained from the circuit context.

#### Conductance Matrix Stamping

The real part of the admittance matrix (conductance `G`) is stamped directly into the main matrix:

```c
            /* Stamp Y-matrix for AC analysis (complex matrix) */
            /* Real part (conductance) */
            *(inst->MOS1drainDrainPtr) += gds + gbd;
            *(inst->MOS1drainSourcePtr) -= gds + gm + gmb;
            *(inst->MOS1drainGatePtr) += gm;
            *(inst->MOS1drainBulkPtr) += gmb - gbd;
            
            *(inst->MOS1sourceDrainPtr) -= gds;
            *(inst->MOS1sourceSourcePtr) += gds + gbs;
            *(inst->MOS1sourceGatePtr) -= gm;
            *(inst->MOS1sourceBulkPtr) += gmb - gbs;
            
            *(inst->MOS1bulkDrainPtr) -= gbd;
            *(inst->MOS1bulkSourcePtr) -= gbs;
            *(inst->MOS1bulkBulkPtr) += gbd + gbs;
```

This implements the mathematical conductance matrix:
```
G = [gds+gbd      gm          -(gds+gm+gmb)   gmb-gbd]
    [-gds        -gm          gds+gbs         gmb-gbs]
    [-gbd         0           -gbs            gbd+gbs]
```

Note that the gate node conductances are zero (ideal insulation) and thus not stamped.

#### Capacitive Susceptance Stamping

The imaginary part (capacitive susceptance `jωC`) is stamped into a separate imaginary matrix:

```c
            /* Imaginary part (capacitive susceptance) */
            /* Stamp jωC terms into the imaginary matrix */
            /* The matrix is split into real and imaginary parts in Ngspice */
            /* We access the imaginary matrix via ckt->CKTmatrixImag */
            
            SMPmatrix *Imag = ckt->CKTmatrixImag;
            
            /* Drain node equations */
            *(SMPmakeElt(Imag, inst->MOS1dNode, inst->MOS1dNode)) += xgd + xbd;
            *(SMPmakeElt(Imag, inst->MOS1dNode, inst->MOS1gNode)) -= xgd;
            *(SMPmakeElt(Imag, inst->MOS1dNode, inst->MOS1sNode)) -= 0.0;  /* No direct D-S cap */
            *(SMPmakeElt(Imag, inst->MOS1dNode, inst->MOS1bNode)) -= xbd;
            
            /* Gate node equations */
            *(SMPmakeElt(Imag, inst->MOS1gNode, inst->MOS1gNode)) += xgs + xgd + xgb;
            *(SMPmakeElt(Imag, inst->MOS1gNode, inst->MOS1dNode)) -= xgd;
            *(SMPmakeElt(Imag, inst->MOS1gNode, inst->MOS1sNode)) -= xgs;
            *(SMPmakeElt(Imag, inst->MOS1gNode, inst->MOS1bNode)) -= xgb;
            
            /* Source node equations */
            *(SMPmakeElt(Imag, inst->MOS1sNode, inst->MOS1sNode)) += xgs + xbs;
            *(SMPmakeElt(Imag, inst->MOS1sNode, inst->MOS1gNode)) -= xgs;
            *(SMPmakeElt(Imag, inst->MOS1sNode, inst->MOS1dNode)) -= 0.0;  /* No direct S-D cap */
            *(SMPmakeElt(Imag, inst->MOS1sNode, inst->MOS1bNode)) -= xbs;
            
            /* Bulk node equations */
            *(SMPmakeElt(Imag, inst->MOS1bNode, inst->MOS1bNode)) += xgb + xbd + xbs;
            *(SMPmakeElt(Imag, inst->MOS1bNode, inst->MOS1gNode)) -= xgb;
            *(SMPmakeElt(Imag, inst->MOS1bNode, inst->MOS1dNode)) -= xbd;
            *(SMPmakeElt(Imag, inst->MOS1bNode, inst->MOS1sNode)) -= xbs;
```

This implements the capacitive susceptance matrix `jωC` where `x = ωC` represents the capacitive susceptance terms. The `SMPmakeElt()` function ensures the matrix entries exist in the sparse matrix structure.

### Pole-Zero Analysis Implementation

The pole-zero analysis in `mos1pzld.c` extends the AC formulation to complex frequency `s = σ + jω`.

#### Complex Frequency Matrix Stamping

```c
int MOS1pzLoad(GENmodel *inModel, CKTcircuit *ckt, SPcomplex *s) {
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    double gdpr, gspr;
    
    for(; model != NULL; model = model->MOS1nextModel) {
        for(inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            
            /* Extract small-signal parameters */
            double gm = inst->MOS1gm;
            double gds = inst->MOS1gds;
            double gmb = inst->MOS1gmb;
            double gbd = inst->MOS1gbd;
            double gbs = inst->MOS1gbs;
            
            /* Extract capacitances */
            double cgs = inst->MOS1cgs;
            double cgd = inst->MOS1cgd;
            double cgb = inst->MOS1cgb;
            double cbd = inst->MOS1cbd;
            double cbs = inst->MOS1cbs;
            
            /* Complex frequency s = σ + jω */
            SPcomplex sc;
            sc.real = s->real;
            sc.imag = s->imag;
            
            /* Calculate complex admittances: Y = G + sC */
            SPcomplex ygs, ygd, ygb, ybd, ybs;
            
            ygs.real = 0.0;
            ygs.imag = sc.real * cgs;  /* sCgs = (σ + jω)Cgs */
            
            ygd.real = 0.0;
            ygd.imag = sc.real * cgd;
            
            ygb.real = 0.0;
            ygb.imag = sc.real * cgb;
            
            ybd.real = gbd;
            ybd.imag = sc.real * cbd;
            
            ybs.real = gbs;
            ybs.imag = sc.real * cbs;
```

The function receives the complex frequency `s` as an `SPcomplex` structure containing `real` (σ) and `imag` (ω) parts. It computes complex admittances `y = G + sC` for each capacitive element.

#### Complex Matrix Stamping

```c
            /* Stamp the matrix with complex values */
            /* Real part */
            *(inst->MOS1drainDrainPtr) += gds + ybd.real;
            *(inst->MOS1drainSourcePtr) -= gds + gm + gmb;
            *(inst->MOS1drainGatePtr) += gm;
            *(inst->MOS1drainBulkPtr) += gmb - ybd.real;
            
            /* Imaginary part (stored in separate matrix) */
            SMPmatrix *MatImag = ckt->CKTmatrixImag;
            
            *(SMPmakeElt(MatImag, inst->MOS1dNode, inst->MOS1dNode)) += ygd.imag + ybd.imag;
            *(SMPmakeElt(MatImag, inst->MOS1dNode, inst->MOS1gNode)) -= ygd.imag;
            *(SMPmakeElt(MatImag, inst->MOS1dNode, inst->MOS1bNode)) -= ybd.imag;
            
            /* Gate capacitances */
            *(SMPmakeElt(MatImag, inst->MOS1gNode, inst->MOS1gNode)) += ygs.imag + ygd.imag + ygb.imag;
            *(SMPmakeElt(MatImag, inst->MOS1gNode, inst->MOS1dNode)) -= ygd.imag;
            *(SMPmakeElt(MatImag, inst->MOS1gNode, inst->MOS1sNode)) -= ygs.imag;
            *(SMPmakeElt(MatImag, inst->MOS1gNode, inst->MOS1bNode)) -= ygb.imag;
            
            /* Source capacitances */
            *(SMPmakeElt(MatImag, inst->MOS1sNode, inst->MOS1sNode)) += ygs.imag + ybs.imag;
            *(SMPmakeElt(MatImag, inst->MOS1sNode, inst->MOS1gNode)) -= ygs.imag;
            *(SMPmakeElt(MatImag, inst->MOS1sNode, inst->MOS1bNode)) -= ybs.imag;
            
            /* Bulk capacitances */
            *(SMPmakeElt(MatImag, inst->MOS1bNode, inst->MOS1bNode)) += ygb.imag + ybd.imag + ybs.imag;
            *(SMPmakeElt(MatImag, inst->MOS1bNode, inst->MOS1gNode)) -= ygb.imag;
            *(SMPmakeElt(MatImag, inst->MOS1bNode, inst->MOS1dNode)) -= ybd.imag;
            *(SMPmakeElt(MatImag, inst->MOS1bNode, inst->MOS1sNode)) -= ybs.imag;
```

This stamps the complex matrix `M(s) = G + sC`, with the real part going to the main matrix and the imaginary part to `CKTmatrixImag`. Note that `sc.real * capacitance` computes `sC = (σ + jω)C`, but the implementation appears to use only the real part of `s` for the capacitive terms, which may be a simplification or error in the provided code.

### Noise Analysis Implementation

The noise analysis in `mos1noi.c` implements comprehensive noise models for the MOS1 device.

#### Noise Source Definitions

```c
    /* Define noise source indices */
    #define MOS1RDNOIZ   0   /* Thermal noise of drain resistance */
    #define MOS1RSNOIZ   1   /* Thermal noise of source resistance */
    #define MOS1IDNOIZ   2   /* Channel thermal noise */
    #define MOS1FLNOIZ   3   /* Flicker (1/f) noise */
    #define MOS1TOTNOIZ  4   /* Total output noise */
```

Five noise sources are defined with unique indices for identification and reporting.

#### Noise Initialization Phase

```c
    if(operation == N_OPEN) {
        /* Initialize noise source names */
        data->namelist = (char**)malloc((MOS1NSRCS+1)*sizeof(char*));
        data->namelist[MOS1RDNOIZ] = "rd";
        data->namelist[MOS1RSNOIZ] = "rs";
        data->namelist[MOS1IDNOIZ] = "id";
        data->namelist[MOS1FLNOIZ] = "fn";
        data->namelist[MOS1TOTNOIZ] = "total";
        data->namelist[MOS1NSRCS] = NULL;
        return OK;
    }
```

The `N_OPEN` operation allocates and names the noise sources for reporting purposes.

#### Noise Calculation Phase

```c
    if(operation == N_CALC) {
        for(; model != NULL; model = model->MOS1nextModel) {
            for(inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
                
                double freq = ckt->CKTomega / (2 * M_PI);
```

The `N_CALC` operation computes noise spectral densities at the current frequency.

##### Drain Resistance Thermal Noise

```c
                /* 1. Thermal noise from drain resistance Rd */
                double gdpr = 1.0 / inst->MOS1drainResist;
                noizDens[MOS1RDNOIZ] = 4.0 * CONSTboltz * inst->MOS1temp * gdpr;
```

Implements `S_Ird(f) = 4kT/Rd = 4kT·gd` where `gd = 1/Rd`. `CONSTboltz` is Boltzmann's constant.

##### Source Resistance Thermal Noise

```c
                /* 2. Thermal noise from source resistance Rs */
                double gspr = 1.0 / inst->MOS1sourceResist;
                noizDens[MOS1RSNOIZ] = 4.0 * CONSTboltz * inst->MOS1temp * gspr;
```

Implements `S_Irs(f) = 4kT/Rs = 4kT·gs` where `gs = 1/Rs`.

##### Channel Thermal Noise

```c
                /* 3. Channel thermal noise (Johnson-Nyquist) */
                double gm = inst->MOS1gm;
                double gds = inst->MOS1gds;
                double T = inst->MOS1temp;
                
                /* Channel noise spectral density */
                /* For MOSFET in saturation: Sid = (8/3) * kT * gm */
                /* For triode region: Sid = 4kT * gds */
                double gamma = 2.0/3.0;  /* Long-channel factor */
                if(inst->MOS1mode == 2) {  /* Saturation */
                    noizDens[MOS1IDNOIZ] = 8.0/3.0 * CONSTboltz * T * gm;
                } else {  /* Triode or cutoff */
                    noizDens[MOS1IDNOIZ] = 4.0 * CONSTboltz * T * gds;
                }
```

Implements the channel thermal noise model:
- Saturation: `S_Id(f) = (8/3)kT·gm` (with γ = 2/3)
- Triode/Cutoff: `S_Id(f) = 4kT·gds`

The `MOS1mode` field indicates operating region (2 = saturation).

##### Flicker (1/f) Noise

```c
                /* 4. Flicker (1/f) noise */
                /* SPICE 2G.6 flicker noise model */
                double Kf = model->MOS1kf;      /* Flicker noise coefficient */
                double Af = model->MOS1af;      /* Flicker noise exponent (usually ~1) */
                double Cox = model->MOS1cox;    /* Oxide capacitance per area */
                double Weff = inst->MOS1effW;
                double Leff = inst->MOS1effL;
                
                /* Flicker noise spectral density: S_id(f) = Kf * gm² / (Cox * Weff * Leff * f^Af) */
                if(freq > 0 && Cox > 0 && Weff > 0 && Leff > 0) {
                    noizDens[MOS1FLNOIZ] = Kf * gm * gm / 
                                           (Cox * Weff * Leff * pow(freq, Af));
                } else {
                    noizDens[MOS1FLNOIZ] = 0.0;
                }
```

Implements the SPICE 2G.6 flicker noise model: `S_Id(f) = KF·gm²/(Cox·Weff·Leff·f^AF)`. The `pow(freq, Af)` computes `f^AF`.

##### Total Noise Computation

```c
                /* Convert to log density for output */
                for(i = 0; i < MOS1NSRCS; i++) {
                    lnNdens[i] = log(MAX(noizDens[i], 1e-38));
                }
                
                /* Calculate total output noise */
                /* Noise contributions are uncorrelated, so add power spectral densities */
                tempOnoise = noizDens[MOS1RDNOIZ] + noizDens[MOS1RSNOIZ] + 
                             noizDens[MOS1IDNOIZ] + noizDens[MOS1FLNOIZ];
                
                /* Store in data structure */
                data->outNoiz = tempOnoise;
                data->inNoise = tempOnoise / (gm * gm);  /* Referred to input */
                
                /* Store individual noise densities */
                data->outNoiseDens[MOS1TOTNOIZ] = tempOnoise;
                for(i = 0; i < MOS1