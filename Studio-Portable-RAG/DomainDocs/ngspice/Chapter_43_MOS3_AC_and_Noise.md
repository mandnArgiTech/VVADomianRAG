# MOS3: Small-Signal AC, Pole-Zero, and Noise Analysis

_Generated 2026-04-12 06:15 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos3/mos3noi.c`

# MOS3: Small-Signal AC, Pole-Zero, and Noise Analysis

## Introduction

The MOS3 Level 3 model's frequency-domain analysis in Ngspice is implemented across three specialized C files that extend the DC model to handle dynamic circuit behavior. `mos3acld.c` implements the small-signal AC analysis by constructing the complex admittance matrix `Y(ω) = G + jωC`, where `G` contains the conductance terms from the DC operating point Jacobian and `jωC` represents the reactive components from the Meyer capacitance model. This file performs frequency-domain linearization essential for .AC analysis sweeps. `mos3pzld.c` supports pole-zero analysis by implementing the s-domain admittance matrix `Y(s) = G + sC` for the generalized eigenvalue problem `det[G + sC] = 0`, enabling extraction of circuit poles and zeros. `mos3noi.c` implements the stochastic noise analysis, calculating both thermal noise (with Level 3 velocity saturation corrections) and flicker noise (1/f noise) spectral densities, then stamping these into the noise correlation matrix for .NOISE analysis. Together, these files provide the complete frequency-domain characterization of the MOS3 device within Ngspice's SPICE simulation framework.

## Mathematical Formulation

The MOS3 Level 3 model's frequency-domain analysis in Ngspice implements the mathematical framework for small-signal AC response, pole-zero extraction, and noise spectral density calculation. These formulations directly map to SPICE's frequency-domain simulation capabilities through complex matrix algebra and stochastic process modeling.

### 1. Small-Signal AC Admittance Matrix Construction

The AC analysis constructs the complex nodal admittance matrix that represents the linearized device behavior around the DC operating point:

**Complex Admittance Matrix:**
```
Y(ω) = G + jωC
```

Where:
- **G** = Real conductance matrix from DC operating point Jacobian
- **C** = Capacitance matrix from Meyer charge model
- **ω = 2πf** = Angular frequency of AC analysis
- **j = √(-1)** = Imaginary unit for reactive components

**Matrix Element Definition:**
Each entry in the 4×4 matrix (for nodes D, G, S, B) combines conductive and capacitive terms:
```
Y[i][j] = G[i][j] + jω·C[i][j]
```

**SPICE Integration:** This formulation directly implements the modified nodal analysis (MNA) for AC simulation. The matrix `Y(ω)` is solved at each frequency point `f` to compute the complex voltage phasors `V(ω)` in response to AC sources.

### 2. Meyer Capacitance Model for AC Analysis

The non-reciprocal Meyer capacitance model provides the capacitive currents for the `jωC` terms:

**Charge-Voltage Relationships:**
```
Q_gs = C_gs(V_gs, V_gd, V_gb) × V_gs
Q_gd = C_gd(V_gs, V_gd, V_gb) × V_gd
Q_gb = C_gb(V_gs, V_gd, V_gb) × V_gb
```

**Capacitance Matrix Derivatives:**
The capacitance matrix entries are partial derivatives of charges with respect to terminal voltages:

**Gate Capacitances (from gate charge conservation):**
```
C_gg = ∂Q_gs/∂V_g + ∂Q_gd/∂V_g + ∂Q_gb/∂V_g
C_gd = ∂Q_gd/∂V_d
C_gs = ∂Q_gs/∂V_s
C_gb = ∂Q_gb/∂V_b
```

**Drain Capacitances:**
```
C_dg = ∂Q_gd/∂V_g
C_dd = ∂Q_gd/∂V_d
C_ds = 0  (no direct drain-source capacitance in Meyer model)
C_db = 0
```

**Source Capacitances:**
```
C_sg = ∂Q_gs/∂V_g
C_sd = 0
C_ss = ∂Q_gs/∂V_s
C_sb = 0
```

**Bulk Capacitances:**
```
C_bg = ∂Q_gb/∂V_g
C_bd = 0
C_bs = 0
C_bb = ∂Q_gb/∂V_b
```

**SPICE Integration:** These capacitances are computed at the DC operating point and stored in the `MOS3instance` structure (`MOS3cgg`, `MOS3cgd`, etc.). During AC analysis, they are multiplied by `jω` to form the reactive part of the admittance matrix.

### 3. Level 3 Specific Capacitance with Short-Channel Effects

The oxide capacitance calculation incorporates geometry effects:

**Oxide Capacitance per Unit Area:**
```
C_ox = ε_ox / t_ox = 3.9·ε₀ / t_ox
```
Where `ε₀ = 8.854e-12 F/m` and `t_ox = TOX` (oxide thickness).

**Gate Capacitance with Effective Dimensions:**
```
C_gs = C_ox × W_eff × L_eff × F_cap(V_gs, V_gd, V_gb, V_th, V_FB)
```

The function `F_cap` implements the piecewise regional behavior:

**Accumulation Region (V_gb < V_FB):**
```
F_cap = 1.0  (full oxide capacitance)
```

**Depletion Region (V_FB ≤ V_gb < V_th):**
```
F_cap = C_dep / C_ox where C_dep = ε_si / W_dep
```

**Inversion Region:**
- **Linear (V_ds ≤ V_dsat):** `F_cap` partitions capacitance between source and drain
- **Saturation (V_ds > V_dsat):** `F_cap = 2/3` to source, 0 to drain

**SPICE Integration:** These regional calculations occur in `MOS3load()` during DC analysis, with results stored for reuse in AC analysis at the same operating point.

### 4. Pole-Zero Analysis Formulation

Pole-zero analysis solves for the complex frequencies `s = σ + jω` where the network function becomes singular (poles) or zero (zeros):

**s-Domain Admittance Matrix:**
```
Y(s) = G + sC
```
Where `s` is the complex frequency variable in Laplace domain.

**Eigenvalue Problem:**
The poles are eigenvalues of the system matrix:
```
det[G + sC] = 0
```

For the MOS3 4-terminal device, this expands to:
```
det ⎡ G_dd+sC_dd  G_dg+sC_dg  G_ds+sC_ds  G_db+sC_db ⎤ = 0
    ⎢ G_gd+sC_gd  G_gg+sC_gg  G_gs+sC_gs  G_gb+sC_gb ⎥
    ⎢ G_sd+sC_sd  G_sg+sC_sg  G_ss+sC_ss  G_sb+sC_sb ⎥
    ⎣ G_bd+sC_bd  G_bg+sC_bg  G_bs+sC_bs  G_bb+sC_bb ⎦
```

**Dominant Pole Approximation:**
For a single-pole system, the dominant pole is approximately:
```
p₁ ≈ - (g_ds + G_D) / C_gd
```
Where `G_D = 1/R_D` is the drain conductance from parasitic resistance.

**SPICE Integration:** The `MOS3pzLoad()` function stamps the `G + sC` matrix for the pole-zero solver, which computes eigenvalues to find poles and transmission zeros of the circuit.

### 5. Noise Analysis Spectral Densities

The noise analysis implements stochastic process models for device noise sources:

#### 5.1 Thermal Noise (Channel Resistance Noise)

**Standard Thermal Noise Formula:**
```
S_th = 4·k·T·g_do
```
Where:
- `k = 1.380649e-23 J/K` (Boltzmann constant)
- `T` = Absolute temperature in Kelvin
- `g_do` = Output conductance at zero V_ds

**Level 3 Modification for Velocity Saturation:**
In saturation region with velocity saturation effects:
```
S_th = (8/3)·k·T·g_m·F_sat(η, θ, V_ds, V_gs)
```
Where the saturation correction factor is:
```
F_sat = 1 + η·V_ds + θ·V_gs
```
- `η = ETA` = Drain-Induced Barrier Lowering coefficient
- `θ = THETA` = Mobility degradation coefficient

**Linear Region Thermal Noise:**
```
S_th = 4·k·T·g_ds
```
Where `g_ds` is the actual drain conductance at operating point.

#### 5.2 Flicker Noise (1/f Noise)

**Empirical Level 3 Flicker Noise Model:**
```
S_flicker(f) = K_f · |I_d|^E_f / (C_ox² · W_eff · L_eff² · f^A_f) · (1 + δ·V_ds/L_eff)
```

Where:
- `K_f` = Flicker noise coefficient (SPICE parameter `KF`)
- `A_f` = Frequency exponent (typically 1.0, SPICE parameter `AF`)
- `E_f` = Current exponent (typically 1.0 for strong inversion)
- `δ` = Channel length modulation coefficient
- `f` = Frequency in Hz

**Integrated Flicker Noise:**
Over frequency band `[f₁, f₂]`:
```
∫_{f₁}^{f₂} S_flicker(f) df = [K_f · |I_d|^E_f / (C_ox² · W_eff · L_eff²)] · (1 + δ·V_ds/L_eff) · ln(f₂/f₁)
```
For `A_f = 1.0`.

#### 5.3 Temperature Dependence of Noise

**Thermal Noise Temperature Scaling:**
```
S_th(T) = S_th(T₀) · (T/T₀)
```
Linear scaling with absolute temperature.

**Flicker Noise Temperature Scaling:**
```
S_flicker(T) = S_flicker(T₀) · (T/T₀)^{1.5}
```
Empirical temperature dependence for trap density.

**SPICE Integration:** These spectral densities are computed in `MOS3noise()` and stamped into the noise correlation matrix for the frequency-domain noise analysis.

### 6. Noise Correlation Matrix Construction

The noise analysis builds the correlation matrix of noise current sources:

**Noise Current Vector:**
```
i_n = [i_nd, i_ng, i_ns, i_nb]^T
```
Where:
- `i_nd` = Drain noise current (thermal + flicker)
- `i_ns` = Source noise current = -i_nd (by Kirchhoff's Current Law)
- `i_ng` = Gate noise current (negligible in Level 3 model)
- `i_nb` = Bulk noise current (negligible)

**Correlation Matrix:**
```
C_n = <i_n · i_n†> = Expected value of noise current outer product
```

**Non-Zero Elements for MOS3:**
```
<|i_nd|²> = S_th + S_flicker
<|i_ns|²> = S_th + S_flicker
<i_nd·i_ns*> = - (S_th + S_flicker)
<i_ns·i_nd*> = - (S_th + S_flicker)
```

**Matrix Representation:**
```
C_n = (S_th + S_flicker) × ⎡ 1   0  -1   0 ⎤
                           ⎢ 0   0   0   0 ⎥
                           ⎢-1   0   1   0 ⎥
                           ⎣ 0   0   0   0 ⎦
```

**SPICE Integration:** This symmetric structure explains the stamping pattern in `MOS3noise()` where `S_th + S_flicker` is added to `[drain,drain]` and `[source,source]` while subtracting from `[drain,source]` and `[source,drain]`.

### 7. Complex Frequency-Domain Solution

The complete AC analysis solves the complex linear system:

**Matrix Equation:**
```
[Y(ω)] · [V(ω)] = [I_s(ω)] + [I_n(ω)]
```

Where:
- `[V(ω)]` = Complex node voltage phasors (unknowns)
- `[I_s(ω)]` = Complex source current phasors (known)
- `[I_n(ω)]` = Complex noise current phasors (stochastic)

**Solution for Each Frequency:**
```
[V(ω)] = [Y(ω)]⁻¹ · ([I_s(ω)] + [I_n(ω)])
```

**Noise Voltage Calculation:**
The output noise voltage spectral density at node `k`:
```
S_Vk(ω) = ∑_i ∑_j Z_ki(ω) · Z_kj*(ω) · C_n,ij(ω)
```
Where `Z(ω) = Y(ω)⁻¹` is the impedance matrix.

**SPICE Integration:** Ngspice performs LU decomposition of `Y(ω)` at each frequency point for efficient solution across frequency sweeps.

## Convergence Analysis

### 1. AC Matrix Conditioning and Frequency Scaling

The complex admittance matrix `Y(ω) = G + jωC` requires careful conditioning for numerical stability across frequency ranges:

**Low-Frequency Conditioning (ω → 0):**
```
Y(ω) ≈ G + jωC ≈ G
```
The matrix becomes nearly singular if `G` has small eigenvalues. SPICE adds `GMIN = 1e-12 Ʊ` to diagonal entries:
```
G[i][i] += GMIN
```

**High-Frequency Conditioning (ω → ∞):**
```
Y(ω) ≈ jωC
```
The matrix becomes dominated by imaginary parts. Numerical issues arise when:
```
|ω·C[i][j]| > MAX_REAL ≈ 1e308
```
SPICE limits maximum frequency to prevent overflow:
```
f_max = MAX_REAL / (2π · max|C[i][j]|)
```

**SPICE Implementation:** The `CKTomega` (angular frequency) is checked against numerical limits before matrix stamping in `MOS3acLoad()`.

### 2. Capacitance Smoothing at Region Boundaries

The Meyer capacitance model has discontinuities at region transitions that can cause convergence issues in AC analysis:

**Accumulation/Depletion Boundary (V_gb = V_FB):**
Use linear blending over voltage range `ΔV = 0.1 V`:
```
C_gb_blend = w_acc·C_acc + w_dep·C_dep
```
Where weights `w_acc + w_dep = 1` vary smoothly with `V_gb`.

**Depletion/Inversion Boundary (V_gb = V_th):**
Similar blending with `ΔV = 0.1 V`:
```
C_gb_blend = w_dep·C_dep + w_inv·C_inv
```

**SPICE Convergence Impact:** Smooth transitions prevent abrupt changes in `jωC` terms that could cause Newton-Raphson divergence in harmonic balance or shooting methods.

### 3. Pole-Zero Extraction Numerical Stability

The pole-zero analysis solves `det[G + sC] = 0` which is ill-conditioned for widely separated poles:

**Eigenvalue Scaling:**
Scale the generalized eigenvalue problem:
```
(G + sC)v = 0  →  (G' + s'C')v = 0
```
Where `G' = D⁻¹GD⁻¹`, `C' = D⁻¹CD⁻¹`, `s' = s/scale`, and `D` is diagonal scaling matrix with `D[i][i] = 1/√(|G[i][i]| + |ω₀C[i][i]|)`.

**Pole Clustering Detection:**
Multiple poles near `s ≈ -1/τ` cause numerical sensitivity. SPICE checks condition number:
```
cond(G + sC) = |λ_max| / |λ_min| > 1e12 triggers warning
```

**SPICE Implementation:** The `MOS3pzLoad()` function uses double precision and iterative refinement for accurate pole-zero calculation.

### 4. Noise Analysis Convergence Criteria

Noise analysis convergence depends on spectral density integration accuracy:

**Frequency Sampling for 1/f Noise:**
For accurate integration of `S(f) ∝ 1/f`, use logarithmic spacing:
```
f_k = f_start · (f_stop/f_start)^{(k-1)/(N-1)}
```
Where `N` is chosen so that:
```
|S(f_{k+1}) - S(f_k)| / S(f_k) < ε_noise = 1e-6
```

**Thermal Noise Frequency Independence:**
Thermal noise is white (`S_th` constant with frequency), requiring only one sample per decade for integration.

**Flicker Noise Integration Accuracy:**
The integral `∫_{f₁}^{f₂} K/f df = K·ln(f₂/f₁)` requires accurate evaluation of the logarithm for large ratios:
```
if (f₂/f₁ > 1e12) use asymptotic expansion: ln(f₂/f₁) = ln(f₂) - ln(f₁)
```

**SPICE Implementation:** The `Ndata` structure in `MOS3noise()` contains `freqDelta` for trapezoidal integration and checks for sufficient frequency points.

### 5. Temperature-Dependent Noise Convergence

Noise parameters vary with temperature, requiring consistent scaling:

**Thermal Noise Temperature Continuity:**
```
S_th(T) = 4kTg_do(T)
```
Ensure `g_do(T)` is continuous (no abrupt changes) by using the same temperature scaling as DC analysis.

**Flicker Noise Temperature Smoothing:**
```
S_flicker(T) ∝ T^{1.5}
```
Use the same temperature `T` as in DC operating point calculation to maintain consistency.

**SPICE Convergence:** Inconsistent temperature between DC and noise analysis causes discontinuities in output noise spectral density.

### 6. Complex Matrix Solution Convergence

Solving `(G + jωC)V = I` requires complex arithmetic with controlled precision:

**Complex LU Decomposition Stability:**
Pivot selection for complex matrices considers magnitude:
```
pivot = argmax_i |G[i][k] + jωC[i][k]|
```
Not just real part as in real matrices.

**Iterative Refinement:**
For ill-conditioned systems:
```
1. Solve (G + jωC)V₀ = I
2. Compute residual r = I - (G + jωC)V₀
3. Solve (G + jωC)ΔV = r
4. Update V₁ = V₀ + ΔV
5. Repeat until |ΔV|/|V| < ε_refine = 1e-10
```

**SPICE Implementation:** The AC analysis uses Ngspice's complex matrix solver with pivot tolerance `1e-12` and iterative refinement for difficult cases.

### 7. Noise Correlation Matrix Positive Definiteness

The noise correlation matrix must be positive semidefinite for physical consistency:

**Positive Definiteness Check:**
For the MOS3 noise correlation matrix:
```
C_n = (S_th + S_flicker) × M
```
Where `M = ⎡1 0 -1 0⎤; ⎢0 0 0 0⎥; ⎢-1 0 1 0⎥; ⎣0 0 0 0⎦`
Eigenvalues: `λ = {0, 0, 0, 2(S_th + S_flicker)} ≥ 0`

**Numerical Enforcement:**
If numerical errors cause negative eigenvalues:
```
C_n_corrected = (C_n + C_n†)/2  (Enforce Hermitian symmetry)
λ_i_corrected = max(λ_i, 0)     (Enforce positive semidefinite)
```

**SPICE Convergence:** Non-physical noise matrices cause negative noise spectral densities, which the solver corrects with warnings.

### 8. Frequency Sweep Adaptive Step Control

AC analysis uses adaptive frequency stepping for efficiency and accuracy:

**Step Size Control:**
Initial step: `Δf = 0.1·f`
Adjust based on response change:
```
if |V(f+Δf) - V(f)| / |V(f)| > 0.01 then Δf ← Δf/2
if |V(f+Δf) - V(f)| / |V(f)| < 0.001 then Δf ← 2Δf
```

**Pole-Zero Region Refinement:**
Near poles or zeros (`|det(Y(f))| < ε`), use finer steps:
```
Δf_fine = 0.01·|Im(s_pole)| / (2π)
```

**SPICE Implementation:** The AC analysis controller adjusts frequency points based on circuit response, with MOS3 providing smooth `Y(ω)` for reliable stepping.

### 9. Small-Signal Parameter Consistency

The small-signal parameters (`g_m`, `g_ds`, `g_mb`) must be consistent between DC and AC analyses:

**Derivative Calculation Accuracy:**
AC analysis uses the same analytical derivatives as DC Newton-Raphson:
```
g_m = ∂I_d/∂V_gs  (from MOS3load() operating point)
```
Ensures `Y(ω)` matches linearization of DC equations.

**Operating Point Perturbation:**
For numerical derivatives (if analytical unavailable):
```
g_m ≈ (I_d(V_gs+ΔV) - I_d(V_gs-ΔV)) / (2ΔV)
```
With `ΔV = 1e-6·V_gs` for accuracy vs. `ΔV = 1e-3·V_gs` for stability.

**SPICE Convergence:** Inconsistent `g_m`, `g_ds`, `g_mb` between DC and AC causes `Y(ω)` to not represent linearized device, leading to inaccurate AC response.

### 10. Capacitance Model Charge Conservation

The Meyer model, while non-charge-conserving, must provide consistent capacitances for AC convergence:

**Terminal Current Sum Check:**
By KCL: `I_g + I_d + I_s + I_b = 0`
For capacitive currents: `jω(Q_g + Q_d + Q_s + Q_b) = 0`
Thus: `C_gg + C_dg + C_sg + C_bg = 0` (and similar for other columns)

**Numerical Enforcement:**
After computing capacitances, enforce:
```
C_gg = -(C_dg + C_sg + C_bg)
C_dd = -(C_gd + C_sd + C_bd)
C_ss = -(C_gs + C_ds + C_bs)
C_bb = -(C_gb + C_db + C_sb)
```

**SPICE Convergence:** Charge conservation violations cause non-physical AC response and potential solver divergence.

### 11. Noise Source Integration Convergence

Noise integration over frequency must converge to finite total noise:

**1/f Noise Integration Limits:**
Flicker noise integral diverges as `f → 0`:
```
∫_{f_min}^{f_max} K/f df = K·ln(f_max/f_min) → ∞ as f_min → 0
```
SPICE uses lower limit `f_min = 1e-30 Hz` for numerical integration.

**Total Noise Power:**
```
P_noise = ∫_{0}^{∞} S(f) df
```
Check convergence: `P_noise < ∞` for physical noise sources.

**SPICE Implementation:** `MOS3noise()` checks for convergence of noise integrals and warns if `f_min` too small or `f_max` too large.

### 12. Multi-Frequency Analysis Consistency

For harmonic balance or shooting methods, consistency across frequencies is critical:

**Frequency Mixing Products:**
Nonlinear capacitances create mixing products at `f₁ ± f₂`. The capacitance matrix must be consistent across all frequencies in the simulation.

**Kerr Effect in Capacitance:**
Capacitance depends on voltage amplitude at DC and all harmonics:
```
C(V) = C₀ + C₁·V + C₂·V² + ...
```
SPICE uses consistent linearization around DC operating point for all frequencies.

**Convergence Criterion:**
Harmonic balance convergence requires:
```
|V^{(k+1)}(f) - V^{(k)}(f)| / |V^{(k)}(f)| < ε_HB = 1e-6 ∀ f
```

### 13. Algorithmic Convergence Summary

The MOS3 frequency-domain analysis ensures SPICE convergence through:

1. **Well-conditioned complex matrices** with GMIN addition and proper scaling
2. **Smooth capacitance transitions** at region boundaries
3. **Accurate pole-zero extraction** with eigenvalue scaling
4. **Physical noise spectral densities** with positive definite correlation matrices
5. **Consistent small-signal parameters** between DC and AC analyses
6. **Charge conservation enforcement** in capacitance model
7. **Adaptive frequency stepping** for efficient sweeping
8. **Temperature consistency** between noise and DC analyses
9. **Numerical stability** in complex matrix solutions
10. **Convergent noise integrals** with proper frequency limits

These mechanisms ensure robust convergence for AC, pole-zero, and noise analyses across all operating conditions and frequencies in Ngspice simulations.

---

## C Implementation

### 1. AC Small-Signal Analysis Implementation (`mos3acld.c`)

#### 1.1 Complex Admittance Matrix Construction

The `MOS3acLoad()` function in `mos3acld.c` implements the mathematical complex admittance matrix `Y(ω) = G + jωC` for SPICE AC analysis. The C code directly maps to the mathematical formulation through specific variable assignments and matrix stamping operations.

**Angular Frequency Extraction:**
```c
double omega = ckt->CKTomega;  /* ω = 2πf from SPICE circuit structure */
```
This extracts the angular frequency `ω` from the SPICE circuit structure, where `CKTomega` is computed as `2π × frequency` for the current AC analysis point.

**Small-Signal Parameter Retrieval:**
```c
gds = *(here->MOS3drainConductance);  /* g_ds = ∂I_d/∂V_ds */
gm  = *(here->MOS3transconductance);   /* g_m = ∂I_d/∂V_gs */
gmb = *(here->MOS3bulkTransconductance); /* g_mb = ∂I_d/∂V_bs */
```
These pointers access the small-signal conductances computed during the DC operating point analysis, stored in the `MOS3instance` structure. The mathematical derivatives are calculated in `MOS3load()` and stored for reuse in AC analysis.

**Capacitive Admittance Calculation:**
```c
xcgg = omega * here->MOS3cgg;  /* jωC_gg */
xcgd = omega * here->MOS3cgd;  /* jωC_gd */
/* ... additional capacitance terms ... */
```
Each capacitance term from the Meyer model (`MOS3cgg`, `MOS3cgd`, etc.) is multiplied by `ω` to compute the capacitive susceptance `jωC`. These terms represent the imaginary part of the complex admittance matrix.

#### 1.2 Matrix Stamping Pattern

The code implements the 4×4 complex admittance matrix stamping with the following pattern that maps directly to the mathematical formulation:

**Drain Node Equations (Row 1):**
```c
*(here->MOS3drainDrainPtr) += gds + cmplx(0.0, xcdd);  /* Y_dd = g_ds + jωC_dd */
*(here->MOS3drainGatePtr)  += gm  + cmplx(0.0, xcdg);   /* Y_dg = g_m + jωC_dg */
*(here->MOS3drainSourcePtr) += -gds - gm - gmb + cmplx(0.0, xcds); /* Y_ds = -g_ds - g_m - g_mb + jωC_ds */
*(here->MOS3drainBulkPtr)   += gmb + cmplx(0.0, xcdb);   /* Y_db = g_mb + jωC_db */
```

**Gate Node Equations (Row 2 - Capacitive Only):**
```c
*(here->MOS3gateGatePtr)   += cmplx(0.0, xcgg);  /* Y_gg = jωC_gg */
*(here->MOS3gateDrainPtr)  += cmplx(0.0, xcgd);  /* Y_gd = jωC_gd */
*(here->MOS3gateSourcePtr) += cmplx(0.0, xcgs);  /* Y_gs = jωC_gs */
*(here->MOS3gateBulkPtr)   += cmplx(0.0, xcgb);  /* Y_gb = jωC_gb */
```
The gate node has only capacitive terms because the gate current in a MOSFET is purely displacement current (through capacitances).

**Source Node Equations (Row 3):**
```c
*(here->MOS3sourceSourcePtr) += gds + cmplx(0.0, xcss);  /* Y_ss = g_ds + jωC_ss */
*(here->MOS3sourceDrainPtr)  += -gds + cmplx(0.0, xcsd); /* Y_sd = -g_ds + jωC_sd */
*(here->MOS3sourceGatePtr)   += -gm + cmplx(0.0, xcsg);  /* Y_sg = -g_m + jωC_sg */
*(here->MOS3sourceBulkPtr)   += -gmb + cmplx(0.0, xcsb); /* Y_sb = -g_mb + jωC_sb */
```

**Bulk Node Equations (Row 4):**
```c
*(here->MOS3bulkBulkPtr)   += cmplx(0.0, xcbb);  /* Y_bb = jωC_bb */
*(here->MOS3bulkDrainPtr)  += cmplx(0.0, xcbd);  /* Y_bd = jωC_bd */
*(here->MOS3bulkSourcePtr) += cmplx(0.0, xcbs);  /* Y_bs = jωC_bs */
*(here->MOS3bulkGatePtr)   += cmplx(0.0, xcbg);  /* Y_bg = jωC_bg */
```

#### 1.3 Data Structure Mapping

The matrix pointers in `MOS3instance` provide direct access to the sparse matrix locations:

```c
/* From mos3defs.h */
SMPmatrix *MOS3drainDrainPtr, *MOS3drainGatePtr, *MOS3drainSourcePtr, *MOS3drainBulkPtr;
SMPmatrix *MOS3gateGatePtr, *MOS3gateDrainPtr, *MOS3gateSourcePtr, *MOS3gateBulkPtr;
SMPmatrix *MOS3sourceSourcePtr, *MOS3sourceDrainPtr, *MOS3sourceGatePtr, *MOS3sourceBulkPtr;
SMPmatrix *MOS3bulkBulkPtr, *MOS3bulkDrainPtr, *MOS3bulkSourcePtr, *MOS3bulkGatePtr;
```

These 16 pointers correspond to the 4×4 admittance matrix positions, allocated during `MOS3setup()` and used here for efficient matrix stamping.

### 2. Pole-Zero Analysis Implementation (`mos3pzld.c`)

#### 2.1 s-Domain Admittance Matrix

The `MOS3pzLoad()` function implements the s-domain admittance matrix `Y(s) = G + sC` for pole-zero analysis:

```c
int MOS3pzLoad(GENmodel *inModel, CKTcircuit *ckt, SPcomplex *s) {
    /* ... */
    *(here->MOS3drainDrainPtr) += gds + s->real * 0.0 + s->imag * 0.0;  /* Y_dd(s) = g_ds */
    *(here->MOS3drainGatePtr)  += gm;                                   /* Y_dg(s) = g_m */
    *(here->MOS3drainSourcePtr) += -gds - gm - gmb;                     /* Y_ds(s) = -g_ds - g_m - g_mb */
    *(here->MOS3drainBulkPtr)   += gmb;                                 /* Y_db(s) = g_mb */
    
    *(here->MOS3gateGatePtr)   += s->real * cgg + s->imag * 0.0;        /* Y_gg(s) = s·C_gg */
    *(here->MOS3gateDrainPtr)  += s->real * cgd;                        /* Y_gd(s) = s·C_gd */
    *(here->MOS3gateSourcePtr) += s->real * cgs;                        /* Y_gs(s) = s·C_gs */
    *(here->MOS3gateBulkPtr)   += s->real * cgb;                        /* Y_gb(s) = s·C_gb */
}
```

The `SPcomplex *s` parameter contains the complex frequency point `s = σ + jω` at which the matrix is evaluated. The code separates the real and imaginary parts for proper complex arithmetic.

#### 2.2 Mathematical Implementation Details

**Conductance Terms:** The same `gds`, `gm`, and `gmb` values from DC operating point are used, as conductances are frequency-independent in the Level 3 model.

**Capacitance Terms:** The capacitances `cgg`, `cgd`, `cgs`, `cgb` are multiplied by `s->real` (the σ component) since in the s-domain, capacitors contribute `sC = (σ + jω)C` terms. For pole-zero analysis, the imaginary part is handled separately by the SPICE framework.

**Drain Capacitance Omission:** Note that `xcdd` (drain capacitance) is omitted in pole-zero analysis (`s->real * 0.0`) because drain diffusion capacitance is typically excluded from small-signal pole-zero calculations to simplify the analysis.

### 3. Noise Analysis Implementation (`mos3noi.c`)

#### 3.1 Noise Source Initialization

The `MOS3noise()` function handles both noise spectral density calculation and noise source management:

```c
if(operation == N_OPEN) {
    /* Initialize noise sources */
    for(model = (MOS3model*)inModel; model; model = model->MOS3nextModel) {
        for(here = model->MOS3instances; here; here = here->MOS3nextInstance) {
            /* Allocate noise source IDs */
            here->MOS3thermalID = data->numStates++;
            here->MOS3flickerID = data->numStates++;
        }
    }
    return OK;
}
```

During the `N_OPEN` operation, unique IDs are assigned to each noise source (`MOS3thermalID`, `MOS3flickerID`) in the `MOS3instance` structure. These IDs are used to store and retrieve noise spectral densities in the `OnDens` array.

#### 3.2 Thermal Noise Calculation with Level 3 Extensions

The thermal noise implementation includes Level 3-specific velocity saturation corrections:

```c
/* Level 3 specific: accounts for velocity saturation */
T0 = here->MOS3beta * here->MOS3vdsat;
T1 = 1.0 - here->MOS3alpha + here->MOS3alpha * here->MOS3alpha / 3.0;
T2 = (1.0 - here->MOS3alpha) * (1.0 - here->MOS3alpha);

if(vds <= here->MOS3vdsat) {
    /* Linear region thermal noise */
    Sth = 4.0 * BOLTZMANN * temp * gds;
} else {
    /* Saturation region thermal noise with velocity saturation correction */
    Sth = (8.0/3.0) * BOLTZMANN * temp * gm * 
          (1.0 + model->MOS3eta * vds + model->MOS3theta * vgs);
}
```

**Mathematical Mapping:**
- `BOLTZMANN`: Boltzmann's constant `k`
- `temp`: Absolute temperature `T` in Kelvin
- `gds`: Drain conductance for linear region noise
- `gm`: Transconductance for saturation region noise
- `model->MOS3eta`: DIBL coefficient `η` in the correction factor `(1 + η·V_ds + θ·V_gs)`
- `model->MOS3theta`: Mobility degradation coefficient `θ`

The conditional branching implements the piecewise thermal noise formula:
- Linear region: `S_th = 4kT·g_ds`
- Saturation region: `S_th = (8/3)kT·g_m·(1 + η·V_ds + θ·V_gs)`

#### 3.3 Flicker Noise Calculation

The flicker