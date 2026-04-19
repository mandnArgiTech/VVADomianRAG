# CIDER Numerical Models: Memory Lifecycle, API, and Pole-Zero

_Generated 2026-04-13 04:11 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjt.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtinit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtitf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2del.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2ask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbjt2ext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2init.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbjt2itf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numd.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numddel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdinit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numditf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/numd2init.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2del.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2ask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/numd2ext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/numd2init.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/numd2itf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/numm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/numosinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/numosext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/numosinit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/numositf.h`

# Chapter: CIDER Numerical Models: Memory Lifecycle, API, and Pole-Zero

## Technical Introduction

The CIDER (Circuit Internal Device Evaluation Routine) numerical models in Ngspice represent a sophisticated framework for implementing advanced semiconductor device simulations that go beyond traditional compact models. The files referenced in this chapter—`nbjt.c`, `nbjtinit.c`, `nbjtdel.c`, `nbjtmpar.c`, `nbjtask.c`, `nbjtpzld.c`, `nbjtext.h`, `nbjtinit.h`, `nbjtitf.h`, `nbt2.c`, `nbt2init.c`, `nbt2del.c`, `nbt2mpar.c`, `nbt2ask.c`, `nbt2pzld.c`, `nbjt2ext.h`, `nbt2init.h`, `nbjt2itf.h`, `numd.c`, `numdinit.c`, `numddel.c`, `numdmpar.c`, `numdask.c`, `numdpzld.c`, `numdext.h`, `numdinit.h`, `numditf.h`, `nud2.c`, `numd2init.c`, `nud2del.c`, `nud2mpar.c`, `nud2ask.c`, `nud2pzld.c`, `numd2ext.h`, `numd2init.h`, `numd2itf.h`, `numm.c`, `numosinit.c`, `nummdel.c`, `nummmpar.c`, `nummask.c`, `nummpzld.c`, `numosext.h`, `numosinit.h`, and `numositf.h`—collectively implement the Numerical BJT (NBJT), Numerical Diode (NUMD), and Numerical MOSFET (NUMM) device families.

These files implement a complete device lifecycle management system within Ngspice's SPICEdev architecture. The `init` files (`nbjtinit.c`, `numdinit.c`, etc.) register devices with the simulator kernel through `SPICEdev` structures, defining the API contract between the numerical models and the simulation engine. The `mpar` files implement parameter binding tables that map SPICE deck parameters to internal C structures, while the `ask` files provide query interfaces for runtime parameter inspection. Memory management is handled through `del` files (`nbjtdel.c`, `numddel.c`, etc.) that implement proper cleanup of dynamically allocated structures, preventing memory leaks during long simulation runs.

The pole-zero analysis capabilities in `pzld` files (`nbjtpzld.c`, `numdpzld.c`, etc.) implement complex frequency domain analysis for stability determination, while the header files (`ext.h`, `init.h`, `itf.h`) define the public interfaces, internal structures, and function prototypes that enable modular compilation and linking. The core simulation algorithms reside in the main `.c` files (`nbjt.c`, `numd.c`, etc.), implementing the numerical solutions to semiconductor device equations using finite-difference or finite-element discretization of the drift-diffusion equations.

This chapter details the complete mathematical foundation and C implementation of these numerical models, focusing on their integration into Ngspice's simulation framework through the SPICEdev API, their memory lifecycle management, and their pole-zero analysis capabilities for stability assessment in feedback circuits.

## 1. Mathematical Formulation

### 1.1 Random Number Generation for Statistical Device Variations

The Ngspice MOS1 model incorporates statistical variations through three fundamental random number distributions implemented in C for Monte Carlo analysis:

**Uniform Distribution (Multiplicative Linear Congruential Generator):**
```
X_{n+1} = (a × X_n + c) mod m
```
where for Ngspice POSIX compatibility:
- `a = 1103515245` (multiplier from POSIX rand())
- `c = 12345` (increment)
- `m = 2^31` (32-bit modulus)

**Normal Distribution via Box-Muller Transform:**
Given two independent uniform variates u₁, u₂ ∈ (0,1):
```
z₀ = √(-2·ln(u₁)) × cos(2π·u₂)
z₁ = √(-2·ln(u₁)) × sin(2π·u₂)
```
This generates two independent standard normal variates N(0,1) used for Gaussian parameter variations.

**Bernoulli Distribution for Discrete Variations:**
```
X = { 1 if drand48() < p
     { 0 otherwise
```
where `p` is the probability of success, used for defect modeling.

### 1.2 Level 1 MOSFET (Shichman-Hodges) Core Equations

**Threshold Voltage with Body Effect:**
```
V_th = VTO + γ·[√(2φ + V_sb) - √(2φ)]
```
where:
- `VTO` = zero-bias threshold voltage (model parameter)
- `γ` = body-effect coefficient (GAMMA)
- `φ` = surface potential (PHI, typically 0.6V)
- `V_sb` = source-bulk voltage (state variable)

**Effective Dimensions for Process Variations:**
```
L_eff = L - 2·LD
W_eff = W - 2·WD
```
where `LD`, `WD` are lateral diffusion parameters.

**Transconductance Parameter:**
```
β = (W_eff/L_eff) × KP
```
where `KP` is the transconductance parameter, calculated from physical parameters:
```
KP = μ₀·C_ox = μ₀·(ε_ox/t_ox)
```
with `ε_ox = 3.9·ε₀ = 3.9 × 8.854e-12 F/m`.

### 1.3 Drain Current Equations by Region

**Region Detection Logic:**
```
V_gst = V_gs - V_th
mode = { CUTOFF   if V_gst ≤ 0
       { LINEAR   if 0 < V_gst and V_ds ≤ V_gst
       { SATURATION if 0 < V_gst and V_ds > V_gst
```

**Cutoff Region (V_gst ≤ 0):**
```
I_d = 0
g_m = ∂I_d/∂V_gs = 0
g_ds = ∂I_d/∂V_ds = 0
g_mb = ∂I_d/∂V_bs = 0
```

**Linear/Triode Region (V_ds ≤ V_gst):**
```
I_d = β·[(V_gst)·V_ds - V_ds²/2]·(1 + λ·V_ds)
g_m = β·V_ds·(1 + λ·V_ds)
g_ds = β·[(V_gst - V_ds)·(1 + λ·V_ds)] + λ·I_d
g_mb = γ·β·V_ds/[2√(2φ + V_sb)]·(1 + λ·V_ds)
```

**Saturation Region (V_ds > V_gst):**
```
I_d = (β/2)·V_gst²·(1 + λ·V_ds)
g_m = β·V_gst·(1 + λ·V_ds)
g_ds = (λ·β/2)·V_gst²
g_mb = γ·β·V_gst/[2√(2φ + V_sb)]·(1 + λ·V_ds)
```

### 1.4 Junction Diode Equations

**Bulk-Source and Bulk-Drain Diodes:**
```
I_bs = IS·[exp(V_bs/(n·V_T)) - 1]
I_bd = IS·[exp(V_bd/(n·V_T)) - 1]
```
where:
- `IS` = saturation current (model parameter)
- `n` = emission coefficient (typically 1.0)
- `V_T = kT/q` = thermal voltage (~25.85mV at 300K)

**Junction Capacitance Model:**
```
C_j(V) = { C_j0/(1 - V/PB)^MJ          for V < FC·PB
         { C_j0·[1 - FC·(1 + MJ) + MJ·V/PB]/(1 - FC)^(1+MJ) for V ≥ FC·PB
```
where:
- `C_j0` = zero-bias capacitance (CBD or CBS)
- `PB` = built-in potential
- `MJ` = grading coefficient
- `FC` = forward bias coefficient (typically 0.5)

**Total Junction Capacitance:**
```
C_bd = CBD·AD·C_j(V_bd) + CJSW·PD·C_jsw(V_bd)
C_bs = CBS·AS·C_j(V_bs) + CJSW·PS·C_jsw(V_bs)
```
where `CJSW` is sidewall capacitance per unit perimeter.

### 1.5 Meyer Capacitance Model

**Gate Capacitance Partitioning:**
The Meyer model divides gate capacitance into three components based on region:

**Cutoff Region (V_gst ≤ 0):**
```
C_gs = C_gso·W_eff
C_gd = C_gdo·W_eff
C_gb = C_ox·W_eff·L_eff
```

**Linear Region (0 < V_gst, V_ds ≤ V_gst):**
```
C_gs = C_ox·W_eff·L_eff·[2/3 - (V_gst - V_ds/2)/(2·V_gst - V_ds)]
C_gd = C_ox·W_eff·L_eff·[2/3 - (V_gst + V_ds/2)/(2·V_gst - V_ds)]
C_gb = 0
```

**Saturation Region (V_ds > V_gst):**
```
C_gs = (2/3)·C_ox·W_eff·L_eff
C_gd = 0
C_gb = 0
```

**Overlap Capacitances (Fixed):**
```
C_gso = CGSO·W_eff
C_gdo = CGDO·W_eff
C_gbo = CGBO·L_eff
```

### 1.6 Small-Signal AC Model

**Complete Y-Parameter Matrix:**
The 4×4 admittance matrix for D, G, S, B nodes at frequency ω:
```
Y(ω) = G + jωC
```
where `G` is the conductance matrix from DC derivatives and `C` is the capacitance matrix.

**Matrix Elements:**
```
Y_dd = g_ds + jω(C_bd + C_gd_tot)
Y_ds = -(g_ds + g_m + g_mb)
Y_dg = g_m - jω·C_gd_tot
Y_db = g_mb - jω·C_bd

Y_sd = -g_ds
Y_ss = g_ds + g_m + g_mb + jω(C_bs + C_gs_tot)
Y_sg = -g_m + jω·C_gs_tot
Y_sb = -g_mb + jω·C_bs

Y_gd = -jω·C_gd_tot
Y_gs = -jω·C_gs_tot
Y_gg = jω(C_gs_tot + C_gd_tot + C_gb_tot)
Y_gb = -jω·C_gb_tot

Y_bd = -g_mb + jω·C_bd
Y_bs = g_mb - jω·C_bs
Y_bg = -jω·C_gb_tot
Y_bb = jω(C_bd + C_bs + C_gb_tot)
```

### 1.7 Noise Models

**Channel Thermal Noise:**
```
S_id(f) = 4kT·γ·g_m0
```
where:
- `γ = 2/3` for long-channel devices
- `g_m0` is zero-V_ds transconductance
- `k` = Boltzmann constant (1.3806503e-23 J/K)
- `T` = absolute temperature (K)

**Flicker (1/f) Noise:**
```
S_if(f) = K_F·|I_d|^A_F/(C_ox·W·L·f)
```
where:
- `K_F` = flicker noise coefficient
- `A_F` = flicker noise exponent (typically ~1)
- `f` = frequency

**Shot Noise in Junction Diodes:**
```
S_I(f) = 2qI
```
for both bulk-source and bulk-drain diodes.

### 1.8 Temperature Scaling Equations

**Threshold Voltage:**
```
VTO(T) = VTO(T_NOM)·(T/T_NOM)
```

**Mobility Degradation:**
```
μ(T) = μ(T_NOM)·(T/T_NOM)^(-1.5)
KP(T) = KP(T_NOM)·(T/T_NOM)^(-1.5)
```

**Junction Parameters:**
```
IS(T) = IS(T_NOM)·exp[(E_g/q·V_T)·(T/T_NOM - 1)]
PB(T) = PB(T_NOM)·(T/T_NOM)
C_j0(T) = C_j0(T_NOM)·√(T/T_NOM)
```

**Surface Potential:**
```
φ(T) = φ(T_NOM)·(T/T_NOM)
```

### 1.9 Charge Conservation Formulation

**State Variables for Charge Storage:**
```
Q_gs = ∫ C_gs·dV_gs
Q_gd = ∫ C_gd·dV_gd
Q_gb = ∫ C_gb·dV_gb
Q_bs = ∫ C_bs·dV_bs
Q_bd = ∫ C_bd·dV_bd
```

**Discrete-Time Implementation (Trapezoidal Rule):**
```
Q(t+Δt) = Q(t) + (Δt/2)·[I(t) + I(t+Δt)]
```
where `I = dQ/dt` is displacement current.

**Charge-Based LTE Calculation:**
```
LTE_Q = |Q_n - Q_{n-1} - (Δt/2)·(I_n + I_{n-1})|
```

### 1.10 Pole-Zero Analysis Formulation

**Complex Frequency Domain Admittance:**
```
Y(s) = G + sC + 1/(sL)  (for general devices)
```
For MOSFETs, primarily:
```
Y_mos(s) = G + sC
```
where `s = σ + jω` is the complex frequency variable.

**Pole Location Estimation:**
Dominant pole for gate node:
```
p₁ ≈ -g_m/(C_gs + C_gd)
```

**Zero Location from Feedforward:**
```
z₁ ≈ +g_m/C_gd  (right-half-plane zero)
```

## 2. Convergence Analysis

### 2.1 Newton-Raphson Iteration for MOSFET Equations

**Nonlinear System Formulation:**
The MOSFET equations form a nonlinear system:
```
F(V) = I(V) - J·V = 0
```
where:
- `F(V)` = residual vector
- `I(V)` = nonlinear current vector from MOSFET equations
- `J` = linear circuit matrix

**Jacobian Matrix Construction:**
```
J = ∂F/∂V = [ ∂I_d/∂V_d   ∂I_d/∂V_g   ∂I_d/∂V_s   ∂I_d/∂V_b ]
            [ ∂I_g/∂V_d   ∂I_g/∂V_g   ∂I_g/∂V_s   ∂I_g/∂V_b ]
            [ ∂I_s/∂V_d   ∂I_s/∂V_g   ∂I_s/∂V_s   ∂I_s/∂V_b ]
            [ ∂I_b/∂V_d   ∂I_b/∂V_g   ∂I_b/∂V_s   ∂I_b/∂V_b ]
```

**Newton Iteration:**
```
V^{k+1} = V^k - J^{-1}(V^k)·F(V^k)
```

### 2.2 Convergence Criteria

**Voltage Convergence:**
```
|ΔV_ij| ≤ RELTOL·|V_ij| + VNTOL
```
where:
- `RELTOL` = relative tolerance (typically 1e-3)
- `VNTOL` = absolute voltage tolerance (typically 1e-6)

**Current Convergence:**
```
|ΔI_i| ≤ RELTOL·|I_i| + ABSTOL
```
where `ABSTOL` = absolute current tolerance (typically 1e-12)

**Charge Conservation Check:**
```
|ΣQ_nodes| ≤ CHGTOL·max(|Q_i|)
```
where `CHGTOL` = charge tolerance (typically 1e-14)

### 2.3 Numerical Challenges and Solutions

**Discontinuous Derivatives at Region Boundaries:**
The `V_gst = 0` boundary between cutoff and active regions causes discontinuous ∂I_d/∂V_gs.

**Solution - Smoothing Function:**
```
V_gst_smooth = V_T·ln[1 + exp((V_gs - V_th)/V_T)]
```
This provides continuous transition with derivative:
```
∂V_gst_smooth/∂V_gs = 1/[1 + exp(-(V_gs - V_th)/V_T)]
```

**Exponential Overflow Protection:**
```
exp_safe(x) = { exp(MAX_EXP) if x > MAX_EXP
              { exp(x)       if |x| ≤ MAX_EXP
              { exp(MIN_EXP) if x < MIN_EXP
```
where `MAX_EXP ≈ 80`, `MIN_EXP ≈ -80`.

### 2.4 Local Truncation Error (LTE) Analysis

**Charge-Based LTE Estimation:**
```
LTE_Q = (Δt²/12)·|d²Q/dt²|_max
```
From Taylor expansion of trapezoidal integration:
```
Q(t+Δt) = Q(t) + Δt·Q'(t) + (Δt²/2)·Q''(t) + (Δt³/6)·Q'''(ξ)
```
LTE = `(Δt³/12)·|Q'''|` for trapezoidal rule.

**Voltage-Based LTE:**
```
LTE_V = (Δt²/12)·|d²V/dt²|_max
```
where `d²V/dt²` estimated from past values:
```
V''_n ≈ (V_n - 2V_{n-1} + V_{n-2})/Δt²
```

**Adaptive Time-Step Control:**
```
Δt_{new} = Δt_{old}·√(TOL/LTE)
```
where `TOL` is user-specified error tolerance.

### 2.5 Convergence Acceleration Techniques

**Damping for Newton Iteration:**
```
V^{k+1} = V^k - α·J^{-1}·F(V^k)
```
where `α ∈ (0,1]` is damping factor, reduced when `||F(V^{k+1})|| > ||F(V^k)||`.

**GMIN Stepping:**
Add small conductance `G_min` across pn junctions:
```
G_min = 1e-12 to 1e-9 S
```
Gradually reduce `G_min` during Newton iterations.

**Source Stepping:**
Scale independent sources by `λ ∈ [0,1]`:
```
I_source(λ) = λ·I_source
V_source(λ) = λ·V_source
```
Increment `λ` from 0 to 1 after each successful convergence.

### 2.6 Matrix Conditioning Analysis

**Ill-Conditioning from Large Capacitance Ratios:**
```
cond(J) ≈ max(C)/min(C) ≈ C_ox/C_j ≈ 1000
```
where `C_ox ≈ 1e-3 F/m²`, `C_j ≈ 1e-6 F/m²`.

**Solution - Diagonal Pivoting:**
Reorder matrix to place large diagonal elements first:
```
P·J·P^T·(P·V) = P·F
```
where `P` is permutation matrix.

### 2.7 Pole-Zero Convergence Analysis

**Complex Matrix Solving:**
For `s = σ + jω`, solve:
```
[G + σC - ω²L]·x = b
```
where `L` represents inductive terms.

**Convergence Criterion for Complex Equations:**
```
|Δx| ≤ RELTOL·|x| + ABSTOL
```
applied separately to real and imaginary parts.

### 2.8 Statistical Convergence for Monte Carlo

**Sample Size Determination:**
For normal distribution with mean μ, variance σ²:
```
N_samples ≥ (z_α·σ/ε)²
```
where:
- `z_α` = confidence coefficient (1.96 for 95% confidence)
- `ε` = desired error margin

**Variance Reduction Techniques:**
- Antithetic variates: use `u` and `1-u` pairs
- Control variates: correlate with known solution
- Importance sampling: bias toward important regions

### 2.9 Memory and State Management

**State Vector Allocation:**
Each MOSFET instance requires 11 state variables:
```
states[0] = V_gs
states[1] = V_ds
states[2] = V_bs
states[3] = I_d
states[4] = I_bs
states[5] = I_bd
states[6] = Q_gs
states[7] = Q_gd
states[8] = Q_gb
states[9] = Q_bd
states[10] = Q_bs
```

**History Management for LTE:**
Store past values for derivative estimation:
```
V_n, V_{n-1}, V_{n-2} for 2nd order LTE
Q_n, Q_{n-1}, Q_{n-2}, Q_{n-3} for 3rd order LTE
```

### 2.10 Breakpoint Generation for Transient Analysis

**Voltage Breakpoints:**
```
t_break = t + ΔV_max/|dV/dt|
```
where `ΔV_max` is maximum allowed voltage change between time points.

**Current Breakpoints:**
```
t_break = t + ΔI_max/|dI/dt|
```
where `ΔI_max` is maximum allowed current change.

**Region Change Detection:**
Monitor `sign(V_gst)·sign(V_gst_prev)` for zero crossings.

### 2.11 Stability Analysis

**Numerical Stability Condition:**
For explicit integration:
```
Δt ≤ 2/|λ_max|
```
where `λ_max` is largest eigenvalue of `J·C⁻¹`.

**Trapezoidal Rule Stability:**
Unconditionally stable for linear systems, but for nonlinear:
```
Δt ≤ min(τ_local) where τ_local = C/G_local
```

**Oscillation Detection:**
```
if sign(ΔV_n) ≠ sign(ΔV_{n-1}) for N_cycles
    then reduce Δt by factor 2
```

This mathematical formulation and convergence analysis provides the complete theoretical foundation for the Ngspice MOS1 implementation, directly mapping to the C code structures and algorithms described in the implementation section.

----------

# C Implementation: MOS1 Device Model in Ngspice

## 1. Core Data Structures and Memory Management

### 1.1 Model and Instance Structures (`mos1defs.h`)

The MOS1 implementation uses a hierarchical data structure system that separates model parameters from instance-specific data:

```c
typedef struct sMOS1model {       /* Level 1 MOSFET model structure */
    int MOS1type;                 /* N-type (1) or P-type (-1) */
    double MOS1vt0;               /* Threshold voltage VTO */
    double MOS1kp;                /* Transconductance parameter KP */
    double MOS1gamma;             /* Body-effect parameter GAMMA */
    double MOS1phi;               /* Surface potential PHI */
    double MOS1lambda;            /* Channel-length modulation LAMBDA */
    /* ... additional model parameters ... */
    struct sMOS1model *MOS1nextModel;     /* Next model in linked list */
    sMOS1instance *MOS1instances;         /* Pointer to instance list */
} MOS1model;

typedef struct sMOS1instance {    /* MOSFET instance structure */
    char *MOS1name;               /* Instance name string */
    int MOS1dNode;                /* Drain node index in matrix */
    int MOS1gNode;                /* Gate node index in matrix */
    int MOS1sNode;                /* Source node index in matrix */
    int MOS1bNode;                /* Bulk node index in matrix */
    double MOS1l;                 /* Drawn channel length L */
    double MOS1w;                 /* Drawn channel width W */
    /* ... additional instance parameters ... */
    
    /* State variables */
    double MOS1vds;               /* Drain-source voltage */
    double MOS1vgs;               /* Gate-source voltage */
    double MOS1vbs;               /* Bulk-source voltage */
    double MOS1cd;                /* Drain current */
    
    /* Matrix pointers for 4x4 conductance matrix */
    double *MOS1drainDrainPtr;    /* Gdd = ∂Id/∂Vd */
    double *MOS1drainGatePtr;     /* Gdg = ∂Id/∂Vg */
    double *MOS1drainSourcePtr;   /* Gds = ∂Id/∂Vs */
    double *MOS1drainBulkPtr;     /* Gdb = ∂Id/∂Vb */
    /* ... 12 more matrix pointers ... */
    
    /* State vector indices for Newton-Raphson iteration */
    int MOS1qgs;                  /* Gate-source charge state index */
    int MOS1qgd;                  /* Gate-drain charge state index */
    int MOS1qgb;                  /* Gate-bulk charge state index */
    /* ... additional state indices ... */
    
    struct sMOS1instance *MOS1nextInstance;   /* Next instance in list */
    MOS1model *MOS1modPtr;                    /* Pointer to parent model */
} MOS1instance;
```

**Mathematical Mapping**: The structure directly implements the mathematical model where:
- `MOS1vt0`, `MOS1kp`, `MOS1gamma`, `MOS1phi`, `MOS1lambda` correspond to VTO, KP, γ, φ, λ parameters
- `MOS1vgs`, `MOS1vds`, `MOS1vbs` store the terminal voltages for Newton-Raphson iteration
- Matrix pointers (`MOS1drainDrainPtr`, etc.) map to the 4×4 Jacobian matrix ∂I/∂V

### 1.2 SPICEdev API Binding (`mos1init.c`)

The device integrates with Ngspice through the SPICEdev interface structure:

```c
SPICEdev MOS1info = {
    .DEVpublic = {
        .name = "mos1",
        .description = "Level 1 MOSFET model",
        .terms = 4,                /* D, G, S, B terminals */
        .numNames = 2,             /* M (instance), MOS1 (model) */
        .termNames = {"d", "g", "s", "b"},
        .numInstanceParms = 12,    /* L, W, AD, AS, PD, PS, etc. */
        .numModelParms = 20,       /* VTO, KP, GAMMA, PHI, etc. */
    },
    .DEVmodParam = MOS1mPTable,    /* Model parameter table */
    .DEVinstParam = MOS1pTable,    /* Instance parameter table */
    .DEVload = MOS1load,           /* Load function for DC/transient */
    .DEVsetup = MOS1setup,         /* Setup function */
    .DEVunsetup = MOS1unsetup,     /* Unsetup function */
    .DEVpzSetup = MOS1pzSetup,     /* Pole-zero setup */
    .DEVtemperature = MOS1temp,    /* Temperature update */
    .DEVtrunc = MOS1trunc,         /* Truncation error calculation */
    .DEVacLoad = MOS1acLoad,       /* AC analysis load */
    .DEVdestroy = MOS1destroy,     /* Destruction function */
    .DEVmodDelete = MOS1mDelete,   /* Model deletion */
    .DEVinstDelete = MOS1delete,   /* Instance deletion */
    .DEVask = MOS1ask,             /* Parameter query */
    .DEVmodAsk = MOS1mAsk,         /* Model parameter query */
    .DEVpzLoad = MOS1pzLoad,       /* Pole-zero load */
    .DEVconvTest = MOS1convTest,   /* Convergence test */
    .DEVnoise = MOS1noise,         /* Noise analysis */
    .DEVinstSize = sizeof(sMOS1instance),
    .DEVmodSize = sizeof(sMOS1model),
};
```

**Implementation Significance**: This structure defines the complete lifecycle interface for the MOS1 device, from setup through analysis to destruction.

### 1.3 Memory Destruction Logic (`mos1dest.c`)

Proper memory management is critical for SPICE simulation stability:

```c
void MOS1destroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    MOS1model *model = (MOS1model*)mod;
    MOS1instance *inst, *nextInst;
    
    /* Traverse model list */
    while(model) {
        MOS1model *nextModel = model->MOS1nextModel;
        
        /* Traverse instance list for this model */
        inst = model->MOS1instances;
        while(inst) {
            nextInst = inst->MOS1nextInstance;
            
            /* Free dynamically allocated strings */
            if(inst->MOS1name)
                FREE(inst->MOS1name);
            
            /* Free instance structure */
            FREE(inst);
            inst = nextInst;
        }
        
        /* Free model structure */
        FREE(model);
        model = nextModel;
    }
    *inModel = NULL;
}
```

**Memory Lifecycle**: The function recursively traverses the linked lists of models and instances, freeing all allocated memory including instance names.

## 2. Parameter Binding and Setup

### 2.1 Parameter Tables (`mos1mpar.c`)

The parameter binding system maps SPICE deck parameters to C structure fields:

```c
static IFparm MOS1mPTable[] = {
    IOP("vto",     MOS1_VTO,    IF_REAL, "Threshold voltage"),
    IOP("kp",      MOS1_KP,     IF_REAL, "Transconductance parameter"),
    IOP("gamma",   MOS1_GAMMA,  IF_REAL, "Body-effect parameter"),
    IOP("phi",     MOS1_PHI,    IF_REAL, "Surface potential"),
    IOP("lambda",  MOS1_LAMBDA, IF_REAL, "Channel-length modulation"),
    IOP("rd",      MOS1_RD,     IF_REAL, "Drain resistance"),
    IOP("rs",      MOS1_RS,     IF_REAL, "Source resistance"),
    IOP("cbd",     MOS1_CBD,    IF_REAL, "Bulk-drain capacitance"),
    IOP("cbs",     MOS1_CBS,    IF_REAL, "Bulk-source capacitance"),
    IOP("is",      MOS1_IS,     IF_REAL, "Bulk junction saturation current"),
    IOP("pb",      MOS1_PB,     IF_REAL, "Bulk junction potential"),
    /* ... 15 additional parameters ... */
};
```

**Mathematical Mapping**: Each `IOP` macro binds a SPICE parameter name (e.g., "vto") to a mathematical parameter (VTO) with a specific data type and description.

### 2.2 Setup Routine (`mos1set.c`)

The setup function initializes all data structures and allocates matrix pointers:

```c
int MOS1setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    MOS1model *model;
    MOS1instance *inst;
    
    for(model = (MOS1model *)inModel; model != NULL; 
        model = model->MOS1nextModel) {
        
        /* Default model parameters if not specified */
        if(!model->MOS1vt0Given)    model->MOS1vt0 = 0.0;
        if(!model->MOS1kpGiven)     model->MOS1kp = 2e-5;
        if(!model->MOS1gammaGiven)  model->MOS1gamma = 0.0;
        if(!model->MOS1phiGiven)    model->MOS1phi = 0.6;
        if(!model->MOS1lambdaGiven) model->MOS1lambda = 0.0;
        
        /* Setup each instance */
        for(inst = model->MOS1instances; inst != NULL; 
            inst = inst->MOS1nextInstance) {
            
            /* Default instance parameters */
            if(!inst->MOS1lGiven) inst->MOS1l = 100e-6;
            if(!inst->MOS1wGiven) inst->MOS1w = 100e-6;
            
            /* Calculate effective dimensions */
            inst->MOS1effL = inst->MOS1l - 2 * model->MOS1ld;
            inst->MOS1effW = inst->MOS1w - 2 * model->MOS1wd;
            
            /* Ensure positive dimensions */
            if(inst->MOS1effL <= 0.0) inst->MOS1effL = 1e-12;
            if(inst->MOS1effW <= 0.0) inst->MOS1effW = 1e-12;
            
            /* Calculate beta = (W_eff/L_eff) * KP */
            inst->MOS1beta = (inst->MOS1effW / inst->MOS1effL) * model->MOS1kp;
            
            /* Allocate Sparse Matrix Pointers (SMP) for 4x4 matrix */
            inst->MOS1drainDrainPtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1dNode);
            inst->MOS1gateGatePtr = SMPmakeElt(matrix, inst->MOS1gNode, inst->MOS1gNode);
            inst->MOS1sourceSourcePtr = SMPmakeElt(matrix, inst->MOS1sNode, inst->MOS1sNode);
            inst->MOS1bulkBulkPtr = SMPmakeElt(matrix, inst->MOS1bNode, inst->MOS1bNode);
            
            /* Allocate off-diagonal elements (12 total) */
            inst->MOS1drainSourcePtr = SMPmakeElt(matrix, inst->MOS1dNode, inst->MOS1sNode);
            /* ... 11 more allocations ... */
            
            /* Allocate state vector entries for Newton-Raphson */
            inst->MOS1vgs = *states; (*states)++;
            inst->MOS1vds = *states; (*states)++;
            inst->MOS1vbs = *states; (*states)++;
            inst->MOS1cd = *states; (*states)++;
            /* ... additional state allocations ... */
            
            /* Initialize state variables */
            ckt->CKTstate0[inst->MOS1vgs] = 0.0;
            ckt->CKTstate0[inst->MOS1vds] = 0.0;
            ckt->CKTstate0[inst->MOS1vbs] = 0.0;
            ckt->CKTstate0[inst->MOS1cd] = 0.0;
        }
    }
    return OK;
}
```

**Mathematical Implementation**: The setup function:
1. Applies default values for unspecified parameters
2. Calculates derived parameters like `MOS1beta = (W_eff/L_eff) * KP`
3. Allocates the 4×4 Jacobian matrix structure for Modified Nodal Analysis
4. Initializes state variables for Newton-Raphson iteration

## 3. DC and Transient Analysis Implementation

### 3.1 DC Load Function (`mos1load.c`)

The core DC analysis implements the Shichman-Hodges equations:

```c
int MOS1load(GENmodel *inModel, CKTcircuit *ckt) {
    MOS1model *model;
    MOS1instance *inst;
    
    for(model = (MOS1model *)inModel; model != NULL; 
        model = model->MOS1nextModel) {
        
        for(inst = model->MOS1instances; inst != NULL; 
            inst = inst->MOS1nextInstance) {
            
            /* Get terminal voltages */
            double vgs = Vg - Vs;
            double vds = Vd - Vs;
            double vbs = Vs - Vb;
            
            /* Calculate threshold voltage: Vth = VTO + γ*(√(2φ+Vsb)-√(2φ)) */
            double vth = model->MOS1vt0 + model->MOS1gamma * 
                (sqrt(2*model->MOS1phi + vbs) - sqrt(2*model->MOS1phi));
            
            /* Determine operating region */
            double vgst = vgs - vth;
            double beta = inst->MOS1beta;
            
            if(vgst <= 0.0) {
                /* Cutoff region: Id = 0, gm = 0, gds = 0, gmb = 0 */
                inst->MOS1cd = 0.0;
                inst->MOS1gm = 0.0;