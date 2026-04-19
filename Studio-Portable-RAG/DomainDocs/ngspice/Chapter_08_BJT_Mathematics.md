# Bipolar Junction Transistor (BJT) Implementation

_Generated 2026-04-11 14:02 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/include/ngspice/devdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjttemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtload.c`

# Chapter: Bipolar Junction Transistor (BJT) Implementation

## Introduction

The Ngspice simulation engine implements the industry-standard Gummel-Poon model for bipolar junction transistors through a sophisticated C architecture that separates device definition, temperature scaling, and nonlinear load operations. The device definition in `devdefs.h` establishes the hierarchical structure for BJT models and instances, mapping physical parameters to C data structures. The temperature dependence module in `bjttemp.c` implements the complex temperature scaling relationships for all semiconductor parameters, including the exponential temperature dependence of saturation currents, power-law scaling of betas, and voltage-dependent capacitance adjustments. The core load routine in `bjtload.c` implements the full Gummel-Poon integral charge control model, computing transport currents, base charge modulation, depletion and diffusion capacitances, and generating the complete Jacobian matrix stamp for Newton-Raphson iteration. Together, these modules transform the mathematical Gummel-Poon equations into an efficient, numerically stable implementation that handles the strong exponential nonlinearities, temperature variations, and charge storage effects characteristic of bipolar transistors.

## Mathematical Formulation

### 1. Gummel-Poon Integral Charge Control Model

#### 1.1 Core Transport Equations

The Gummel-Poon model in SPICE implements the integral charge control relationship through normalized base charge. The fundamental transport current is given by:

```
I_CC = (I_S / q_b) × [exp(v_be/(N_F·V_T)) - exp(v_bc/(N_R·V_T))]
```

Where:
- `I_CC`: Collector transport current
- `I_S`: Transport saturation current
- `q_b`: Normalized base charge
- `v_be`: Base-emitter voltage
- `v_bc`: Base-collector voltage
- `N_F`: Forward current emission coefficient
- `N_R`: Reverse current emission coefficient
- `V_T = kT/q`: Thermal voltage (≈ 25.85 mV at 300K)

#### 1.2 Base Charge Formulation

The normalized base charge `q_b` accounts for base-width modulation and high-level injection effects:

```
q_b = q_1 + q_2
```

Where the Early effect component is:
```
q_1 = 1 / (1 - v_be/V_AF - v_bc/V_AR)
```

And the high-level injection component is:
```
q_2 = (I_S/V_T) × [exp(v_be/(N_F·V_T)) - 1]/I_KF + 
      (I_S/V_T) × [exp(v_bc/(N_R·V_T)) - 1]/I_KR
```

Parameters:
- `V_AF`: Forward Early voltage
- `V_AR`: Reverse Early voltage
- `I_KF`: Forward knee current
- `I_KR`: Reverse knee current

#### 1.3 Terminal Current Decomposition

The complete terminal currents include recombination and leakage components:

**Base-Emitter Recombination Current:**
```
I_BE = I_SE × [exp(v_be/(N_E·V_T)) - 1]
```

**Base-Collector Recombination Current:**
```
I_BC = I_SC × [exp(v_bc/(N_C·V_T)) - 1]
```

**Complete Terminal Currents:**
```
I_C = I_CC - I_BC - dQ_BC/dt - dQ_BX/dt
I_B = I_BE + I_BC + dQ_BE/dt + dQ_BC/dt + dQ_BX/dt
I_E = -I_C - I_B
```

Where:
- `I_SE`: B-E leakage saturation current
- `I_SC`: B-C leakage saturation current
- `N_E`: B-E leakage emission coefficient
- `N_C`: B-C leakage emission coefficient
- `Q_BE`, `Q_BC`, `Q_BX`: Charge storage terms

#### 1.4 Series Resistance Modeling

The model includes ohmic resistances in series with each terminal:

**Current-Dependent Base Resistance:**
```
R_B(I_B) = R_BM + 3 × (R_B - R_BM) × [arctan(π·I_B/(2·I_RB))/π - arctan(π·I_BM/(2·I_RB))/π]
```

**Constant Resistances:**
- `R_C`: Collector series resistance
- `R_E`: Emitter series resistance

### 2. Temperature Dependence Formulation

#### 2.1 Thermal Voltage Scaling

The thermal voltage varies linearly with absolute temperature:
```
V_T(T) = k·T/q = 8.617333262145 × 10⁻⁵ × T (V)
```
Where `T` is in Kelvin.

#### 2.2 Saturation Current Temperature Dependence

The transport saturation current scales with temperature as:
```
I_S(T) = I_S(T_NOM) × (T/T_NOM)^(XTI/N_F) × exp[-(E_G/q)/V_T × (T/T_NOM - 1)]
```

Where:
- `XTI`: Temperature exponent for IS (default = 3.0)
- `E_G`: Energy gap (1.11 eV for silicon at 300K)
- `T_NOM`: Nominal temperature (typically 300K)

The energy gap itself has temperature dependence:
```
E_G(T) = 1.16 - (7.02 × 10⁻⁴ × T²)/(T + 1108) (eV)
```

#### 2.3 Beta Temperature Dependence

Forward and reverse betas scale with temperature as:
```
β_F(T) = β_F(T_NOM) × (T/T_NOM)^(XTB)
β_R(T) = β_R(T_NOM) × (T/T_NOM)^(XTB)
```

Where `XTB` is the beta temperature exponent.

#### 2.4 Junction Potential Temperature Dependence

The built-in junction potential varies as:
```
V_J(T) = V_J(T_NOM) × (T/T_NOM) - 3·V_T·ln(T/T_NOM) - E_G(T) + (T/T_NOM)·E_G(T_NOM)
```

This accounts for both linear thermal expansion and the temperature dependence of the energy gap.

#### 2.5 Junction Capacitance Temperature Dependence

Zero-bias depletion capacitance scales as:
```
C_J0(T) = C_J0(T_NOM) × [1 + M_J × (4.0 × 10⁻⁴ × (T - T_NOM) - (V_J(T) - V_J(T_NOM))/V_J(T_NOM))]
```

Where `M_J` is the junction grading coefficient.

#### 2.6 Resistance Temperature Dependence

Series resistances scale with a power law:
```
R(T) = R(T_NOM) × (T/T_NOM)^(T_R)
```

Where `T_R` is the resistance temperature exponent.

### 3. Charge Storage Model

#### 3.1 Depletion Capacitance Model

The voltage-dependent depletion capacitance follows:

**Reverse Bias (v ≤ F_C·V_J):**
```
C_J(v) = C_J0 × (1 - v/V_J)^(-M_J)
```

**Forward Bias (v > F_C·V_J):**
```
C_J(v) = C_J0 × (1 - F_C)^(-M_J) × [1 - F_C × (1 + M_J) + M_J × v/V_J]
```

Where `F_C` is the forward bias depletion capacitance coefficient (typically 0.5).

#### 3.2 Diffusion Capacitance

Diffusion charge storage is modeled through transit times:

**Forward Diffusion Capacitance:**
```
C_DE = τ_F × ∂I_CC/∂v_be
```

**Reverse Diffusion Capacitance:**
```
C_DC = τ_R × ∂I_CC/∂v_bc
```

Where:
- `τ_F`: Forward transit time
- `τ_R`: Reverse transit time

#### 3.3 Base Charge Partitioning

The base-collector capacitance is partitioned between intrinsic and extrinsic components:
```
C_BC,total = C_BCi + C_BCx
C_BCx = X_CJC × C_JC0
C_BCi = (1 - X_CJC) × C_JC0
```

Where `X_CJC` is the fraction of base-collector capacitance connected to the base node.

### 4. Modified Nodal Analysis Formulation

#### 4.1 Complete Terminal Equations

For an NPN transistor with nodes C (collector), B (base), E (emitter), and optional S (substrate):

**Collector Node Equation:**
```
I_C + I_RC + I_CS + dQ_BC/dt + dQ_BX/dt = 0
```

**Base Node Equation:**
```
I_B + I_RB - I_BE - I_BC - dQ_BE/dt - dQ_BC/dt - dQ_BX/dt = 0
```

**Emitter Node Equation:**
```
I_E + I_RE = 0
```

Where `I_RC`, `I_RB`, `I_RE` are currents through series resistances.

#### 4.2 Jacobian Matrix Elements

The small-signal conductances for the Newton-Raphson iteration are:

**Collector Current Derivatives:**
```
∂I_C/∂v_be = ∂I_CC/∂v_be
∂I_C/∂v_bc = ∂I_CC/∂v_bc - ∂I_BC/∂v_bc
∂I_C/∂v_cs = 1/R_CS  (if substrate present)
```

**Base Current Derivatives:**
```
∂I_B/∂v_be = ∂I_BE/∂v_be
∂I_B/∂v_bc = ∂I_BC/∂v_bc
```

**Emitter Current Derivatives:**
```
∂I_E/∂v_be = -∂I_C/∂v_be - ∂I_B/∂v_be
∂I_E/∂v_bc = -∂I_C/∂v_bc - ∂I_B/∂v_bc
```

#### 4.3 Base Charge Derivatives

The derivatives of normalized base charge are critical for convergence:

```
∂q_b/∂v_be = q_1²/V_AF + (I_S/(V_T·I_KF·N_F)) × exp(v_be/(N_F·V_T))
∂q_b/∂v_bc = q_1²/V_AR + (I_S/(V_T·I_KR·N_R)) × exp(v_bc/(N_R·V_T))
```

#### 4.4 Transport Current Derivatives

```
∂I_CC/∂v_be = (I_S/(q_b·N_F·V_T)) × exp(v_be/(N_F·V_T)) - (I_CC/q_b) × ∂q_b/∂v_be
∂I_CC/∂v_bc = -(I_S/(q_b·N_R·V_T)) × exp(v_bc/(N_R·V_T)) - (I_CC/q_b) × ∂q_b/∂v_bc
```

## Convergence Analysis

### 1. Newton-Raphson Convergence Properties

#### 1.1 Exponential Nonlinearity

The Gummel-Poon model contains strong exponential nonlinearities from the diode-like junctions:

```
I ∝ exp(v/(N·V_T))
```

This creates a Jacobian with entries that vary exponentially with voltage, leading to potential convergence issues when voltages change significantly between iterations.

#### 1.2 Convergence Criteria

The Newton iteration converges when both current and voltage changes satisfy:

**Current Convergence:**
```
|ΔI| < I_abs_tol + I_rel_tol × |I|
```

**Voltage Convergence:**
```
|ΔV| < V_abs_tol + V_rel_tol × |V|
```

Typical SPICE tolerances:
- `I_abs_tol = 1 pA` to `1 nA`
- `V_abs_tol = 1 µV` to `1 mV`
- `I_rel_tol = 0.001` (0.1%)
- `V_rel_tol = 0.001` (0.1%)

#### 1.3 Damping for Large Voltage Steps

When `|ΔV| > 10·V_T ≈ 0.25V`, the Newton step is damped to prevent overshoot:
```
λ = min(1.0, 0.5·V_T/|ΔV|)
V_new = V_old + λ·ΔV
```

This damping factor `λ` ensures the iteration remains in the region where the exponential approximation is valid.

### 2. Numerical Stability Considerations

#### 2.1 Exponential Argument Limiting

To prevent floating-point overflow, exponential arguments are limited:
```
if (v/(N·V_T) > MAX_EXP) then exp = exp(MAX_EXP)
if (v/(N·V_T) < -MAX_EXP) then exp = exp(-MAX_EXP)
```

Where `MAX_EXP` is typically 80-100, corresponding to `exp(MAX_EXP)` near the maximum representable double-precision number.

#### 2.2 Base Charge Regularization

The base charge denominator requires regularization to prevent division by zero:
```
q_1 = 1 / max(ε, 1 - v_be/V_AF - v_bc/V_AR)
```

Where `ε` is typically `1e-12` to `1e-16`.

#### 2.3 Capacitance Model Regularization

The depletion capacitance model requires care near `v = V_J`:
```
arg = max(MIN_CAP_ARG, 1 - v/V_J)
C_J = C_J0 × arg^(-M_J)
```

Where `MIN_CAP_ARG` is typically `1e-6` to prevent unrealistic capacitance values.

### 3. Temperature Scaling Convergence

#### 3.1 Exponential Temperature Terms

The temperature scaling contains terms of the form:
```
exp[-E_G/(k·T)]
```

For `T → 0`, this term can underflow. The implementation uses:
```
if (T < MIN_TEMP) T = MIN_TEMP
```
Where `MIN_TEMP` is typically 1K.

#### 3.2 Power Law Regularization

The power law terms `(T/T_NOM)^p` require:
```
if (T/T_NOM < MIN_RATIO) ratio = MIN_RATIO
if (T/T_NOM > MAX_RATIO) ratio = MAX_RATIO
```

Where `MIN_RATIO ≈ 0.01` and `MAX_RATIO ≈ 100`.

### 4. Charge Conservation and Time Integration

#### 4.1 Charge Conservation Property

The Gummel-Poon model with depletion and diffusion charges should satisfy:
```
Q_total = Q_BE + Q_BC + Q_BX
dQ_total/dt = I_B + I_C + I_E - (I_RB + I_RC + I_RE)
```

Numerical integration must preserve this relationship to prevent charge accumulation errors.

#### 4.2 Time Integration Stability

For backward Euler integration with time step `h`:

**Capacitance Companion Model:**
```
I_cap = C·(v_n - v_{n-1})/h
g_eq = C/h
i_eq = C·v_{n-1}/h
```

The effective conductance `g_eq` can become very large for small `h`, potentially causing ill-conditioning in the MNA matrix when:
```
h < C·R_min
```
Where `R_min` is the smallest resistance in parallel with the capacitance.

#### 4.3 Local Truncation Error (LTE)

For charge-based integration, the LTE is estimated as:
```
LTE ≈ |(h²/2)·d²Q/dt²|
```

The time step is adjusted to keep LTE below user-specified tolerance `τ`:
```
if LTE > τ: h_new = h·√(τ/LTE)
if LTE < τ/10: h_new = h·min(2, √(τ/LTE))
```

### 5. Matrix Conditioning Analysis

#### 5.1 Ill-Conditioning Sources

The BJT Jacobian matrix can become ill-conditioned due to:

**Large Conductance Ratios:**
```
κ ≈ max(g_be, g_bc)/min(g_rc, g_re, g_rb)
```

Where `g_be, g_bc` can exceed `1e6 S` in strong forward bias, while series conductances `g_rc, g_re, g_rb` may be as small as `1e-12 S`.

**Exponential Scaling:**
```
g_be ∝ exp(v_be/(N_F·V_T))/V_T
```

For `v_be > 0.7V`, `g_be` can exceed `1e10 S`, causing condition numbers `κ > 1e22`.

#### 5.2 Pivoting Requirements

The sparse LU decomposition requires careful pivoting to handle:
1. Zero or very small diagonal elements from floating nodes
2. Large off-diagonal elements from transconductance `g_m`
3. Wide dynamic range from series resistances vs. junction conductances

#### 5.3 Regularization Techniques

To improve conditioning:
1. **Gmin Stepping**: Add small conductance `G_min ≈ 1e-12 S` from every node to ground
2. **Source Stepping**: Gradually ramp voltage sources from zero to final values
3. **Pseudo-Transient**: Use artificially large capacitors to slow down circuit dynamics

### 6. Convergence Acceleration Techniques

#### 6.1 Continuation Methods

For difficult DC convergence, homotopy methods are used:

**Source Stepping:**
```
V_source(α) = α·V_final, α ∈ [0,1]
```

**Gmin Stepping:**
```
G_min(α) = (1-α)·G_max + α·G_min_final
```

#### 6.2 Predictor-Corrector Methods

In transient analysis, predictor values provide good initial guesses:
```
v_be_pred = v_be_old + h·dv_be/dt_old
```

The predictor reduces the number of Newton iterations required per time step.

#### 6.3 Limiting for Physical Consistency

Voltages and currents are limited to physically reasonable values:

**Junction Voltage Limiting:**
```
-5·V_T < v_be < V_J + 10·V_T
-5·V_T < v_bc < V_J + 10·V_T
```

**Current Limiting:**
```
|I_C| < I_max = 10·I_S·exp(MAX_EXP)
|I_B| < I_max/β_min
```

### 7. Error Propagation Analysis

#### 7.1 Parameter Sensitivity

The model exhibits high sensitivity to certain parameters:

**Saturation Current:**
```
∂I_C/∂I_S ≈ I_C/I_S (for v_be > 3·V_T)
```

A 1% error in `I_S` causes approximately 1% error in `I_C`.

**Thermal Voltage:**
```
∂I_C/∂V_T ≈ -I_C·v_be/(N_F·V_T²)
```

At `v_be = 0.7V`, `V_T = 0.02585V`, this gives sensitivity ≈ `-I_C·1000`.

#### 7.2 Numerical Error Accumulation

The dominant numerical errors come from:

**Exponential Evaluation:**
```
Relative error ≈ ε_machine·exp(v/(N·V_T))/exp(v/(N·V_T)) ≈ ε_machine
```
But absolute error grows with current magnitude.

**Logarithmic Evaluation (for V_J calculation):**
```
Error in ln(T/T_NOM) ≈ ε_machine/(T/T_NOM)
```

#### 7.3 Temperature Calculation Errors

The temperature scaling calculations involve differences of large terms:
```
V_J(T) = V_J(T_NOM)·(T/T_NOM) - 3·V_T·ln(T/T_NOM) - E_G(T) + (T/T_NOM)·E_G(T_NOM)
```

Cancellation errors can occur when `T ≈ T_NOM`. The implementation uses series expansion for `|T-T_NOM|/T_NOM < 0.01`.

### 8. Model Limitations and Workarounds

#### 8.1 High-Injection Regime

The Gummel-Poon model assumes `q_2 ≪ q_1` for accuracy. When `q_2 ≈ q_1` (high injection), the model can become inaccurate. Ngspice implements:

**Current Limiting:**
```
if (q_2 > 0.9·q_1) then I_CC = I_CC·(q_1/(q_1+q_2))
```

#### 8.2 Reverse Bias Breakdown

The model does not include avalanche breakdown. For `v_bc < -BV_CBO`, the simulation may fail to converge. Workaround:

**Voltage Limiting:**
```
if (v_bc < -BV_CBO) then v_bc = -BV_CBO
```

#### 8.3 Subthreshold Region

For `v_be < 3·V_T`, the exponential approximation becomes inaccurate. Ngspice uses:

**Linear Extrapolation:**
```
if (v_be < V_T) then I_CC = I_S·v_be/(N_F·V_T)
```

This mathematical formulation and convergence analysis provides the complete theoretical foundation for Ngspice's implementation of the Gummel-Poon BJT model, directly mapping to the algorithms in `bjttemp.c` and `bjtload.c`.

## C Implementation

### 1. BJT Device Structure Implementation

#### 1.1 Core Data Structures

The Gummel-Poon mathematical model maps to the `BJTmodel` and `BJTinstance` structures:

```c
typedef struct sBJTmodel {
    int BJTmodType;                /* NPN or PNP */
    double BJTtnom;                /* Nominal temperature T_NOM */
    
    /* Gummel-Poon model parameters - mathematical symbols in comments */
    double BJTis;                  /* I_S: Transport saturation current */
    double BJTbf;                  /* β_F: Ideal forward beta */
    double BJTnf;                  /* N_F: Forward current emission coefficient */
    double BJTvaf;                 /* V_AF: Forward Early voltage */
    double BJTikf;                 /* I_KF: Forward knee current */
    double BJTise;                 /* I_SE: B-E leakage saturation current */
    double BJTne;                  /* N_E: B-E leakage emission coefficient */
    double BJTbr;                  /* β_R: Ideal reverse beta */
    double BJTnr;                  /* N_R: Reverse current emission coefficient */
    double BJTvar;                 /* V_AR: Reverse Early voltage */
    double BJTikr;                 /* I_KR: Reverse knee current */
    double BJTisc;                 /* I_SC: B-C leakage saturation current */
    double BJTnc;                  /* N_C: B-C leakage emission coefficient */
    double BJTrb;                  /* R_B: Zero-bias base resistance */
    double BJTrbm;                 /* R_BM: Minimum base resistance */
    double BJTirb;                 /* I_RB: Current for base resistance fall */
    double BJTrc;                  /* R_C: Collector resistance */
    double BJTre;                  /* R_E: Emitter resistance */
    double BJTcje;                 /* C_JE0: B-E zero-bias depletion capacitance */
    double BJTvje;                 /* V_JE: B-E built-in potential */
    double BJTmje;                 /* M_JE: B-E junction grading coefficient */
    double BJTcjc;                 /* C_JC0: B-C zero-bias depletion capacitance */
    double BJTvjc;                 /* V_JC: B-C built-in potential */
    double BJTmjc;                 /* M_JC: B-C junction grading coefficient */
    double BJTxcjc;                /* X_CJC: Fraction of B-C cap connected to base */
    double BJTfc;                  /* F_C: Forward bias depletion cap coefficient */
    double BJTxtb;                 /* X_TB: Temperature exponent for beta */
    double BJTeg;                  /* E_G: Energy gap for IS temperature dependence */
    double BJTxti;                 /* X_TI: Temperature exponent for IS */
    double BJTtf;                  /* τ_F: Ideal forward transit time */
    double BJTtr;                  /* τ_R: Ideal reverse transit time */
    
    struct sBJTmodel *BJTnextModel;
    BJTinstance *BJTinstances;
} BJTmodel;

typedef struct sBJTinstance {
    /* Node connections - indices in MNA vector */
    int BJTcolNode;                /* Collector node index */
    int BJTbaseNode;               /* Base node index */
    int BJTemitNode;               /* Emitter node index */
    int BJTsubstNode;              /* Substrate node index (optional) */
    
    /* Temperature parameters */
    double BJTtemp;                /* Instance temperature T */
    double BJTdtemp;               /* ΔT = T - T_NOM */
    
    /* Temperature-adjusted parameters (precomputed in BJTtemp) */
    double BJTtIS;                 /* I_S(T): Temperature-adjusted IS */
    double BJTtBF;                 /* β_F(T): Temperature-adjusted BF */
    double BJTtVAF;                /* V_AF(T): Temperature-adjusted VAF */
    double BJTtIKF;                /* I_KF(T): Temperature-adjusted IKF */
    double BJTtISE;                /* I_SE(T): Temperature-adjusted ISE */
    double BJTtBR;                 /* β_R(T): Temperature-adjusted BR */
    double BJTtVAR;                /* V_AR(T): Temperature-adjusted VAR */
    double BJTtIKR;                /* I_KR(T): Temperature-adjusted IKR */
    double BJTtISC;                /* I_SC(T): Temperature-adjusted ISC */
    double BJTtRB;                 /* R_B(T): Temperature-adjusted RB */
    double BJTtRBM;                /* R_BM(T): Temperature-adjusted RBM */
    double BJTtIRB;                /* I_RB(T): Temperature-adjusted IRB */
    double BJTtRC;                 /* R_C(T): Temperature-adjusted RC */
    double BJTtRE;                 /* R_E(T): Temperature-adjusted RE */
    double BJTtCJE;                /* C_JE0(T): Temperature-adjusted CJE */
    double BJTtVJE;                /* V_JE(T): Temperature-adjusted VJE */
    double BJTtCJC;                /* C_JC0(T): Temperature-adjusted CJC */
    double BJTtVJC;                /* V_JC(T): Temperature-adjusted VJC */
    double BJTvt;                  /* V_T(T) = kT/q: Thermal voltage */
    
    /* State variables (updated each iteration) */
    double BJTvbe;                 /* v_BE: Base-emitter voltage */
    double BJTvbc;                 /* v_BC: Base-collector voltage */
    double BJTvcs;                 /* v_CS: Collector-substrate voltage */
    
    /* Conductances (Jacobian elements) */
    double BJTgbe;                 /* g_BE = ∂I_B/∂v_BE */
    double BJTgbc;                 /* g_BC = ∂I_B/∂v_BC */
    double BJTgm;                  /* g_m = ∂I_C/∂v_BE (transconductance) */
    double BJTgo;                  /* g_o = ∂I_C/∂v_BC (output conductance) */
    
    /* Charge storage variables */
    double BJTcbe;                 /* C_BE: Total B-E capacitance */
    double BJTcbc;                 /* C_BC: Total B-C capacitance */
    double BJTcde;                 /* C_DE: B-E diffusion capacitance */
    double BJTcdc;                 /* C_DC: B-C diffusion capacitance */
    
    /* Terminal currents */
    double BJTic;                  /* I_C: Collector current */
    double BJTib;                  /* I_B: Base current */
    double BJTie;                  /* I_E: Emitter current */
    
    /* Matrix pointers for sparse stamping */
    double *BJTcolColPtr;          /* G[col][col] */
    double *BJTcolBasePtr;         /* G[col][base] */
    double *BJTcolEmitPtr;         /* G[col][emit] */
    double *BJTbaseColPtr;         /* G[base][col] */
    double *BJTbaseBasePtr;        /* G[base][base] */
    double *BJTbaseEmitPtr;        /* G[base][emit] */
    double *BJTEmitColPtr;         /* G[emit][col] */
    double *BJTEmitBasePtr;        /* G[emit][base] */
    double *BJTEmitEmitPtr;        /* G[emit][emit] */
    
    struct sBJTinstance *BJTnextInstance;
} BJTinstance;
```

### 2. Temperature Dependence Implementation (`bjttemp.c`)

#### 2.1 Temperature Adjustment Function

The mathematical temperature scaling formulas are implemented in `BJTtemp()`:

```c
void BJTtemp(BJTinstance *here, BJTmodel *model, CKTcircuit *ckt) {
    double tnom = model->BJTtnom;
    double temp = here->BJTtemp;
    double dtemp = here->BJTdtemp;
    
    /* Convert to Kelvin: T_K = T_C + 273.15 */
    double tempk = temp + CONSTCtoK;
    double tnomk = tnom + CONSTCtoK;
    
    /* Ratio for power laws: T/T_NOM */
    double ratio = tempk / tnomk;
    double ratio1 = ratio - 1.0;
    
    /* Thermal voltage: V_T = kT/q */
    double vt = tempk * CONSTKoverQ;
    here->BJTvt = vt;  /* Store for use in load routine */
    
    /* Energy gap temperature dependence: E_G(T) = 1.16 - (7.02e-4·T²)/(T + 1108) */
    double egfet = 1.16 - (7.02e-4 * tempk * tempk) / (tempk + 1108.0);
    double egfet_nom = 1.16 - (7.02e-4 * tnomk * tnomk) / (tnomk + 1108.0);
    
    /* Saturation current temperature adjustment */
    /* I_S(T) = I_S(T_NOM) × (T/T_NOM)^(XTI/N_F) × exp[-(E_G/q)/V_T × (T/T_NOM - 1)] */
    double arg = -egfet / (2.0 * CONSTboltz * tempk) + 
                 model->BJTeg / (2.0 * CONSTboltz * tnomk);
    double pbfact = -2.0 * vt * (1.5 * log(ratio) + CONSTQ * arg);
    
    here->BJTtIS = model->BJTis * exp(pbfact / vt);
    here->BJTtIS *= pow(ratio, model->BJTxti / model->BJTnf);
    
    /* Leakage saturation currents */
    /* I_SE(T) = I_SE(T_NOM) × exp[pbfact/(N_E·V_T)] */
    here->BJTtISE = model->BJTise * exp(pbfact / (model->BJTne * vt));
    
    /* I_SC(T) = I_SC(T_NOM) × exp[pbfact/(N_C·V_T)] */
    here->BJTtISC = model->BJTisc * exp(pbfact / (model->BJTnc * vt));
    
    /* Beta temperature adjustment: β(T) = β(T_NOM) × (T/T_NOM)^(XTB) */
    here->BJTtBF = model->BJTbf * pow(ratio, model->BJTxtb);
    here->BJTtBR = model->BJTbr * pow(ratio, model->BJTxtb);
    
    /* Early voltage temperature adjustment: V_AF(T) = V_AF(T_NOM) × (T/T_NOM) */
    here->BJTtVAF = model->BJTvaf * ratio;
    here->BJTtVAR = model->BJTvar * ratio;
    
    /* Knee current temperature adjustment */
    here->BJTtIKF = model->BJTikf * pow(ratio, 1.5);
    here->BJTtIKR = model->BJTikr * pow(ratio, 1.5);
    
    /* Junction potential temperature adjustment */
    /* V_J(T) = V_J(T_NOM) × (T/T_NOM) - 3V_T ln(T/T_NOM) - E_G(T) + (T/T_NOM)E_G(T_NOM) */
    here->BJTtVJE = model->BJTvje * ratio - 
                   3.0 * vt * log(ratio) - 
                   egfet + egfet_nom * ratio;
    
    here->BJTtVJC = model->BJTvjc * ratio - 
                   3.0 * vt * log(ratio) - 
                   egfet + egfet_nom * ratio;
    
    /* Junction capacitance temperature adjustment */
    /* C_J0(T) = C_J0(T_NOM) × [1 + M_J × (4e-4(T - T_NOM) - (V_J(T) - V_J(T_NOM))/V_J(T_NOM))] */
    double fact1 = 1.0 + model->BJTmje * 
                  (4.0e-4 * (temp - tnom) - 
                   (here->BJTtVJE - model->BJTvje) / model->BJTvje);
    here->BJTtCJE = model->BJTcje * fact1;
    
    double fact2 = 1.0 + model->BJTmjc * 
                  (4.0e-4 * (temp - tnom) - 
                   (here->BJTtVJC - model->BJTvjc) / model->BJTvjc);
    here->BJTtCJC = model->BJTcjc * fact2;
    
    /* Resistance temperature adjustment: R(T) = R(T_NOM) × (T/T_NOM)^(T_R) */
    here->BJTtRB = model->BJTrb * pow(ratio, model->BJTtrb1);
    here->BJTtRBM = model->BJTrbm * pow(ratio, model->BJTtrb1);
    here->BJTtIRB = model->BJTirb * pow(ratio, model->BJTtrb1);
    here->BJTtRC = model->BJTrc * pow(ratio, model->BJTtrc1);
    here->BJTtRE = model->BJTre * pow(ratio, model->BJTtre1);
    
    /* Transit time temperature adjustment */
    here->BJTtTF = model->BJTtf * (1.0 + model->BJTxtf * ratio1);
    here->BJTtTR = model->BJTtr * (1.0 + model->BJTxtr * ratio1);
}
```

### 3. BJT Load Routine Implementation (`bjtload.c`)

#### 3.1 Main Load Function

The mathematical Gummel-Poon equations are implemented in `BJTload()`:

```c
int BJTload(GENmodel *inModel, CKTcircuit *ckt) {
    BJTmodel *model = (BJTmodel*)inModel;
    BJTinstance *here;
    
    for (; model != NULL; model = BJTnextModel(model)) {
        for (here = BJTinstances(model); here != NULL;
             here = BJTnextInstance(here)) {
            
            /* Get junction voltages from circuit solution vector */
            /* v_BE = V_B - V_E, v_BC = V_B - V_C */
            double vbe = ckt->CKTrhsOld[here->BJTbaseNode] - 
                         ckt->CKTrhsOld[here->BJTemitNode];
            double vbc = ckt->CKTrhsOld[here->BJTbaseNode] - 
                         ckt->CKTrhsOld[here->BJTcolNode];
            
            /* Store for capacitance calculations */
            here->BJTvbe = vbe;
            here->BJTvbc = vbc;
            
            /* Thermal voltage */
            double vt = here->BJTvt;
            
            /* Normalized junction voltages for exponentials */
            /* v_BE,norm = v_BE/(N_F·V_T), v_BC,norm = v_BC/(N_R·V_T) */
            double vben = vbe / (model->BJTnf * vt);
            double vbcn = vbc / (model->BJTnr * vt);
            
            /* Exponential terms with limiting to prevent overflow */
            /* expbe = exp(v_BE/(N_F·V_T)), expbc = exp(v_BC/(N_R·V_T)) */
            double expbe, expbc;
            
            if (vben > BJT_MAX_EXP) {
                expbe = exp(BJT_MAX_EXP);  /* Limit to exp(80) ≈ 5.5e34 */
            } else if (vben < -BJT_MAX_EXP) {
                expbe = exp(-BJT_MAX_EXP); /* Limit to exp(-80) ≈ 1.4e-35 */
            } else {
                expbe = exp(vben);
            }