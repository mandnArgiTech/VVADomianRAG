# BSIM4v6: Layout-Dependent Effects, Geometry, and Setup

_Generated 2026-04-12 15:17 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6ask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6check.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v6/b4v6geo.c`

# Chapter: BSIM4v6: Layout-Dependent Effects, Geometry, and Setup

## Technical Introduction

The BSIM4v6 model implementation in Ngspice represents the state-of-the-art in nanometer-scale MOSFET simulation, incorporating sophisticated layout-dependent effects critical for accurate deep-submicron circuit design. This chapter examines the core implementation files that handle geometry scaling, parameter management, and device setup: `b4v6set.c`, `b4v6mpar.c`, `b4v6mask.c`, `b4v6ask.c`, `b4v6check.c`, and `b4v6geo.c`. These files collectively implement the mathematical formulations for layout-dependent effects including Shallow Trench Isolation (STI) stress, Well Proximity Effect (WPE), and advanced geometry binning. The `b4v6geo.c` file computes effective device dimensions and stress modifications, while `b4v6set.c` manages parameter binning and temperature scaling. The `b4v6mpar.c` defines the complete parameter table for SPICE netlist parsing, and `b4v6ask.c` provides the query interface for simulation output. Together, these files establish the geometric and parametric foundation upon which the BSIM4v6 DC, AC, and transient analyses are built, ensuring accurate representation of modern CMOS technologies with layout-dependent performance variations.

## Mathematical Formulation

### 3.1 Effective Geometry Calculations and Layout-Dependent Effects

The BSIM4v6 model in Ngspice implements advanced geometry scaling and layout-dependent effects critical for nanometer CMOS simulation. The effective dimensions are computed in `b4v6geo.c` as:

```
Leff = Ldrawn - 2·dl
Weff = Wdrawn - 2·dw
```

where `dl` and `dw` are length and width reduction parameters. These effective dimensions directly scale all current and capacitance equations in the SPICE simulation.

#### STI Stress Effects
Shallow Trench Isolation (STI) stress modifies both mobility and threshold voltage:

```
μ_stress = μ0·[1 + SA·(Weff/Wref - 1) + SB·(L/Leff_ref - 1)]
```

```
ΔVth_STI = STI_K·(1/SA + 1/SB + 1/SD)
```

where `SA`, `SB`, `SD` are instance parameters from the `BSIM4v6instance` structure (`bsim4v6sa`, `bsim4v6sb`, `bsim4v6sd`). These stress effects are stamped into the DC operating point calculation, affecting the linearized conductance matrix `G`.

#### Well Proximity Effect (WPE)
WPE introduces threshold voltage shift based on distance from well edge:

```
ΔVth_WPE = WPE0 + WPE1·d^(-WPE2)
```

where `d` is the distance stored in instance parameters. This effect is computed during the setup phase in `b4v6set.c` and modifies the `bsim4v6vth0` parameter before Newton-Raphson iteration begins.

### 3.2 Composite Threshold Voltage Model

The complete threshold voltage formulation for SPICE DC analysis is:

```
Vth = Vth0 + ΔVth_STI + ΔVth_WPE + ΔVth_DIBL + ΔVth_SCE
```

#### Drain-Induced Barrier Lowering (DIBL)
```
ΔVth_DIBL = -(DVT0 + DVT1·Vbs)·[1 + 2·exp(-DVT2·Vds/φ_t)]
```

where `φ_t = kT/q` is the thermal voltage. The exponential term ensures smooth transition with drain bias, critical for Newton-Raphson convergence.

#### Short-Channel Effect (SCE)
```
ΔVth_SCE = -θ_SCE·(φ_si - Vbs - γ·√(φ_si))
θ_SCE = 0.5·[exp(-L/2λ) + exp(-L/λ)]
λ = √(ε_si·Tox·Xdep/ε_ox)
```

The characteristic length `λ` determines the severity of SCE and is computed from oxide thickness `Tox` and depletion width `Xdep`.

### 3.3 Mobility Degradation with Vertical Field

The effective mobility for SPICE current calculation incorporates vertical field degradation:

```
μ_eff = μ_stress / [1 + (UA + UC·Vbs)·(Vgs - Vth)/Tox 
                   + UB·(Vgs - Vth)²/Tox²]
```

Parameters `UA`, `UB`, `UC` are stored in the `BSIM4v6model` structure. This formulation ensures the transconductance `gm = ∂Id/∂Vgs` remains continuous for Newton-Raphson convergence.

### 3.4 Unified Drain Current Model

The drain current model provides C¹ continuity from subthreshold to strong inversion, essential for SPICE convergence.

#### Subthreshold Region (Vgst < 0)
```
n = 1 + (C_dep + CIT)/C_ox + NFACTOR·exp(-Vds/φ_t)
I_sub = I_0·exp(Vgst/(n·φ_t))·[1 - exp(-Vds/φ_t)]
I_0 = μ_eff·C_ox·(Weff/Leff)·φ_t²
```

The subthreshold slope factor `n` includes interface trap capacitance `CIT` from model parameters.

#### Strong Inversion Linear Region (Vds ≤ Vdsat)
```
I_lin = μ_eff·C_ox·(Weff/Leff)·[(Vgst - 0.5·α·Vds)·Vds]
α = 1 + (GAMMA/(2·√(PHI + Vbs)))
```

The bulk charge factor `α` accounts for body effect through `GAMMA` parameter.

#### Strong Inversion Saturation Region (Vds > Vdsat)
```
I_sat = I_lin(Vdsat)·(1 + λ·Vds)
λ = PCLM/Leff + PDIBLCB·Vbs + DROUT·Vds
```

Channel length modulation parameter `λ` includes components for CLM (`PCLM`), DIBL (`PDIBLCB`), and output resistance degradation (`DROUT`).

#### Saturation Voltage
```
Vdsat = VSAT·Leff/μ_eff
```

The saturation velocity `VSAT` is a key model parameter affecting high-field transport.

### 3.5 Gate Tunneling Currents

For nanometer technologies, gate tunneling currents become significant:

#### Gate-to-Channel Tunneling
```
I_gc = AIGC·(Tox/TOXREF)^BIGC·exp(CIGC·Vox/TOXREF)·Weff·Leff
```

#### Gate-to-Source/Drain Overlap Tunneling
```
I_gs = AIGS·(Tox/TOXREF)^BIGS·exp(CIGS·Vgs/TOXREF)·Weff·DLC
I_gd = AIGD·(Tox/TOXREF)^BIGD·exp(CIGD·Vgd/TOXREF)·Weff·DLC
```

These currents are added to the terminal currents in the `b4v6ld.c` load function and contribute to the Jacobian matrix derivatives.

### 3.6 Capacitance and Charge Models

The charge conservation formulation for SPICE transient analysis uses:

```
Q_g = Q_gs + Q_gd + Q_gb
Q_b = Q_bs + Q_bd
```

where the individual charges are computed from surface potential formulation. The capacitances for AC analysis are:

```
C_gs = ∂Q_gs/∂Vgs, C_gd = ∂Q_gd/∂Vgd, C_gb = ∂Q_gb/∂Vgb
```

These derivatives form the capacitance matrix `C` in the complex admittance `Y = G + jωC` for AC analysis.

### 3.7 Matrix Stamping for Modified Nodal Analysis

The 7×7 conductance matrix includes external nodes (D, G, S, B) and internal nodes (D', S'):

```
Node indices: 0:D, 1:G, 2:S, 3:B, 4:D', 5:S'

G[4][4] = 1/Rd + gds + gbd      /* Gd'd' */
G[5][5] = 1/Rs + gds + gbs + gm + gmb  /* Gs's' */
G[4][5] = -gds                   /* Gd's' */
G[5][4] = -gds                   /* Gs'd' */
G[0][4] = -1/Rd                  /* Gdd' */
G[4][0] = -1/Rd                  /* Gd'd */
G[2][5] = -1/Rs                  /* Gss' */
G[5][2] = -1/Rs                  /* Gs's */
```

where:
- `gds = ∂Id/∂Vds` (output conductance)
- `gm = ∂Id/∂Vgs` (transconductance)
- `gmb = ∂Id/∂Vbs` (body transconductance)
- `gbd = ∂Ibd/∂Vbd`, `gbs = ∂Ibs/∂Vbs` (junction conductances)

This matrix is stamped in `b4v6ld.c` using the sparse matrix pointers in `BSIM4v6instance`.

## Convergence Analysis

### 7.1 Newton-Raphson Convergence Criteria

The convergence test in `b4v6cvtest.c` implements SPICE-standard tolerance checking:

#### Voltage Convergence
```
ΔV = V_new - V_old
converged_V = (|ΔV| < VNTOL + RELTOL·MAX(|V_new|, |V_old|))
```

Default values: `VNTOL = 1e-6 V`, `RELTOL = 0.001`

#### Charge Convergence
```
ΔQ = Q_new - Q_old
converged_Q = (|ΔQ| < CHGTOL)
```

Default: `CHGTOL = 1e-14 C`

#### Current Convergence
```
ΔI = I_new - I_old
converged_I = (|ΔI| < ABSTOL + RELTOL·MAX(|I_new|, |I_old|))
```

Default: `ABSTOL = 1e-12 A`

The overall convergence requires all three conditions: `converged = converged_V && converged_Q && converged_I`

### 7.2 Local Truncation Error (LTE) for Time-Step Control

The LTE calculation in `b4v6trunc.c` enables adaptive time-step control in transient analysis:

#### Charge-Based LTE
```
ε_charge = |q(t_{n+1}) - q_pred(t_{n+1})|/(ABS_TOL + REL_TOL·MAX(|q(t_n)|, |q(t_{n+1})|))
```

where predicted charge uses second-order polynomial extrapolation:
```
q_pred(t_{n+1}) = q(t_n) + h·dq/dt(t_n) + h²/2·d²q/dt²(t_n)
```

#### Current-Based LTE
```
ε_current = |i(t_{n+1}) - i_pred(t_{n+1})|/(ABS_TOL + REL_TOL·MAX(|i(t_n)|, |i(t_{n+1})|))
```

#### Time-Step Adjustment
```
if (MAX(ε_charge, ε_current) > TRTOL) then
    h_new = h_old·0.5  /* Reduce time step */
else if (MAX(ε_charge, ε_current) < TRTOL/10) then
    h_new = h_old·1.5  /* Increase time step */
```

Default: `TRTOL = 7` (SPICE default truncation error tolerance)

### 7.3 Gmin Stepping for DC Convergence

When DC analysis fails to converge, BSIM4v6 implements Gmin stepping algorithm:

```
for (gmin_factor = 1e-12 to 1e-3 in decade steps) do
    Gmin = gmin_factor·GMIN_DEFAULT
    Add Gmin conductance from each node to ground
    Attempt Newton-Raphson solution
    if (converged) then
        Reduce Gmin gradually to zero
        return SUCCESS
```

This helps overcome numerical difficulties near cutoff region.

### 7.4 Source-Drain Symmetry Handling

For convergence with swapped source-drain terminals:

```
if (Vds < 0) then
    swap(D, S)
    swap(D', S')
    Vds = -Vds
    Vgs = Vgs - Vds
    Vbs = Vbs - Vds
```

All derivatives are recomputed with swapped terminals to maintain symmetry.

### 7.5 Voltage Limiting (DEVfetlim)

The voltage limiting function prevents Newton-Raphson oscillation:

```
Vnew_limited = Vold + δ·(Vnew - Vold)
where δ = min(1, 2·VMAX/|Vnew - Vold|)
```

`VMAX` is typically `2.0` volts for MOSFETs. This limiting is applied to `Vgs`, `Vds`, and `Vbs` during iteration.

### 7.6 Matrix Condition Number Monitoring

The 7×7 conductance matrix condition number is monitored:

```
cond(G) = ||G||·||G⁻¹||
if (cond(G) > 1e12) then
    /* Matrix is ill-conditioned */
    Add GMIN to diagonal elements
    Issue convergence warning
```

This prevents numerical instability in matrix solution.

### 7.7 Iteration Count Limiting

SPICE limits Newton-Raphson iterations per time point:

```
if (iteration_count > ITL_MAX) then
    /* Convergence failure */
    Reduce time step by factor of 8
    Reset iteration count
```

Default: `ITL_MAX = 100` for transient analysis, `ITL1 = 40` for DC analysis.

### 7.8 Charge Conservation Enforcement

For transient analysis, charge conservation is enforced via:

```
I_cap(t_{n+1}) = (Q(t_{n+1}) - Q(t_n))/h + α·I_cap(t_n)
```

where `α = 0` for Backward Euler, `α = -1` for Trapezoidal rule. This ensures `ΣI_cap = dQ/dt` exactly.

### 7.9 Noise Analysis Convergence

For noise analysis in `b4v6noi.c`, the noise correlation matrix is checked for positive definiteness:

```
if (det(S) < 0) then
    /* Non-physical noise correlation */
    Adjust correlation coefficient c
    Recompute noise matrix
```

where `S` is the 2×2 noise spectral density matrix for drain and gate noise.

### 7.10 Parameter Binning Continuity

Parameter binning in `b4v6set.c` ensures C⁰ continuity across bin boundaries:

```
P_effective = P0 + PL/Leff + PW/Weff + PWL/(Leff·Weff)
```

The derivatives `∂P/∂Leff` and `∂P/∂Weff` are computed to ensure smooth transitions in device characteristics across geometry bins, preventing convergence issues at bin boundaries.

This comprehensive convergence analysis ensures robust SPICE simulation for BSIM4v6 devices across all operating regions and analysis types.

## C Implementation

### 1. Core Data Structures and Memory Architecture

The BSIM4v6 model in Ngspice is implemented through two primary C structures defined in `bsim4v6def.h`, which encapsulate all model parameters, instance variables, and simulation state.

#### 1.1 Model Structure (`sBSIM4v6model`)

The model structure stores process-specific parameters that are shared across all instances of a given MOSFET model. This structure implements the mathematical parameter binning system through explicit coefficient fields:

```c
typedef struct sBSIM4v6model {
    /* Basic device type */
    int bsim4v6type;                    /* N/PMOS type */
    
    /* Threshold voltage parameters */
    double bsim4v6vth0;                 /* Threshold voltage */
    double bsim4v6k1;                    /* First-order body effect */
    double bsim4v6k2;                    /* Second-order body effect */
    double bsim4v6k3;                    /* Narrow width effect */
    double bsim4v6k3b;                   /* Body bias coefficient for k3 */
    
    /* DIBL coefficients */
    double bsim4v6dvt0;                  /* First coefficient of DIBL */
    double bsim4v6dvt1;                  /* Second coefficient of DIBL */
    double bsim4v6dvt2;                  /* Body-bias coefficient of DIBL */
    double bsim4v6dvt0w;                 /* DIBL for narrow width */
    double bsim4v6dvt1w;                 /* Body bias effect for DIBL narrow width */
    double bsim4v6dvt2w;                 /* Drain-bias effect for DIBL narrow width */
    
    /* Mobility parameters */
    double bsim4v6u0;                    /* Low-field mobility */
    double bsim4v6ua;                    /* First-order mobility degradation */
    double bsim4v6ub;                    /* Second-order mobility degradation */
    double bsim4v6uc;                    /* Body-bias mobility degradation */
    
    /* STI Stress and WPE parameters */
    double bsim4v6sa;                     /* STI stress coefficient for mobility */
    double bsim4v6sb;                     /* STI stress coefficient for Vth */
    double bsim4v6sd;                     /* STI stress coefficient for DIBL */
    double bsim4v6weffcj;                 /* Effective width for STI stress */
    double bsim4v6wpe;                    /* Well Proximity Effect coefficient */
    double bsim4v6wpe0;                   /* WPE zero-order coefficient */
    double bsim4v6wpe1;                   /* WPE first-order coefficient */
    double bsim4v6wpe2;                   /* WPE second-order coefficient */
    
    /* Noise model selectors */
    int bsim4v6tnoimod;                   /* Thermal noise model selector */
    int bsim4v6fnoimod;                   /* Flicker noise model selector */
    
    /* Linked list pointers */
    struct sBSIM4v6model *bsim4v6nextModel;
    sBSIM4v6instance *bsim4v6instances;
} BSIM4v6model;
```

**Mathematical Mapping**: Each field corresponds directly to a coefficient in the BSIM4v6 equations. For example, `bsim4v6dvt0`, `bsim4v6dvt1`, and `bsim4v6dvt2` implement the DIBL term: `ΔVth_DIBL = -(DVT0 + DVT1·Vbs)·[1 + 2·exp(-DVT2·Vds/φ_t)]`.

#### 1.2 Instance Structure (`sBSIM4v6instance`)

The instance structure stores layout-specific parameters and dynamic simulation state for each individual MOSFET:

```c
typedef struct sBSIM4v6instance {
    /* Node indices for SPICE Modified Nodal Analysis */
    int bsim4v6dNode;                     /* External drain node */
    int bsim4v6gNode;                     /* External gate node */
    int bsim4v6sNode;                     /* External source node */
    int bsim4v6bNode;                     /* External bulk node */
    int bsim4v6dNodePrime;                /* Internal drain node (after Rds) */
    int bsim4v6sNodePrime;                /* Internal source node (after Rss) */
    
    /* Layout parameters */
    double bsim4v6l;                       /* Drawn length */
    double bsim4v6w;                       /* Drawn width */
    double bsim4v6nf;                      /* Number of fingers */
    
    /* STI stress geometry */
    double bsim4v6sa;                      /* STI stress active area */
    double bsim4v6sb;                      /* STI stress space */
    double bsim4v6sd;                      /* STI stress distance */
    
    /* Effective dimensions (calculated in b4v6geo.c) */
    double bsim4v6weff;                    /* Effective width */
    double bsim4v6leff;                    /* Effective length */
    
    /* Bias voltages */
    double bsim4v6vbs;                     /* Bulk-source voltage */
    double bsim4v6vbd;                     /* Bulk-drain voltage */
    double bsim4v6vgs;                     /* Gate-source voltage */
    double bsim4v6vds;                     /* Drain-source voltage */
    
    /* State variables for charges */
    double bsim4v6qgs;                     /* Gate-source charge */
    double bsim4v6qgd;                     /* Gate-drain charge */
    double bsim4v6qgb;                     /* Gate-bulk charge */
    
    /* State vector indices for SPICE state management */
    int bsim4v6qgsState;
    int bsim4v6qgdState;
    int bsim4v6qgbState;
    
    /* Matrix pointers for 7×7 conductance matrix stamping */
    double *bsim4v6dDPrimePtr;            /* [d', d'] */
    double *bsim4v6gGPrimePtr;            /* [g, g] */
    double *bsim4v6sSPrimePtr;            /* [s', s'] */
    double *bsim4v6bBPtr;                 /* [b, b] */
    double *bsim4v6dPrimeSPtr;            /* [d', s'] */
    double *bsim4v6dPrimeGPtr;            /* [d', g] */
    double *bsim4v6dPrimeBPtr;            /* [d', b] */
    
    /* Linked list pointer */
    struct sBSIM4v6instance *bsim4v6nextInstance;
    BSIM4v6model *bsim4v6modPtr;
} BSIM4v6instance;
```

**SPICE Integration**: The `bsim4v6qgsState`, `bsim4v6qgdState`, and `bsim4v6qgbState` indices map to positions in the global `CKTstate` array, enabling charge conservation through numerical integration.

### 2. Geometry and Layout-Dependent Effects (`b4v6geo.c`)

#### 2.1 Effective Dimension Calculation

The `b4v6geo.c` file implements the effective geometry calculations with STI stress effects:

```c
/* Pseudo-code for effective dimension calculation */
void BSIM4v6calculateGeometry(BSIM4v6instance *inst, BSIM4v6model *model)
{
    /* Basic effective dimensions */
    inst->bsim4v6leff = inst->bsim4v6l - 2.0 * model->bsim4v6dl;
    inst->bsim4v6weff = inst->bsim4v6w - 2.0 * model->bsim4v6dw;
    
    /* STI stress effect on mobility (μ_stress = μ0·[1 + SA·(Weff/Wref - 1) + SB·(L/Leff_ref - 1)]) */
    double mu_stress = model->bsim4v6u0;
    mu_stress *= (1.0 + model->bsim4v6sa * (inst->bsim4v6weff/WREF - 1.0));
    mu_stress *= (1.0 + model->bsim4v6sb * (inst->bsim4v6l/LEFF_REF - 1.0));
    
    /* STI stress effect on threshold voltage (ΔVth_STI = STI_K·(1/SA + 1/SB + 1/SD)) */
    double vth_sti = STI_K * (1.0/inst->bsim4v6sa + 1.0/inst->bsim4v6sb + 1.0/inst->bsim4v6sd);
    
    /* Well Proximity Effect (ΔVth_WPE = WPE0 + WPE1·d^(-WPE2)) */
    double d = calculateDistanceToWellEdge(inst);
    double vth_wpe = model->bsim4v6wpe0 + model->bsim4v6wpe1 * pow(d, -model->bsim4v6wpe2);
    
    /* Store calculated values */
    inst->bsim4v6mu_stress = mu_stress;
    inst->bsim4v6vth_sti = vth_sti;
    inst->bsim4v6vth_wpe = vth_wpe;
}
```

**Mathematical Mapping**: This code directly implements the equations:
- `Leff = Ldrawn - 2·dl`
- `Weff = Wdrawn - 2·dw`
- `μ_stress = μ0·[1 + SA·(Weff/Wref - 1) + SB·(L/Leff_ref - 1)]`
- `ΔVth_STI = STI_K·(1/SA + 1/SB + 1/SD)`
- `ΔVth_WPE = WPE0 + WPE1·d^(-WPE2)`

### 3. Parameter Setup and Binning (`b4v6set.c`)

#### 3.1 Parameter Binning Implementation

The `b4v6set.c` file handles parameter binning with continuous scaling:

```c
/* Pseudo-code for parameter binning */
double BSIM4v6binParameter(double P0, double PL, double PW, double PWL,
                           double Leff, double Weff)
{
    /* P_effective = P0 + PL/Leff + PW/Weff + PWL/(Leff·Weff) */
    double P_eff = P0;
    P_eff += PL / Leff;
    P_eff += PW / Weff;
    P_eff += PWL / (Leff * Weff);
    
    return P_eff;
}

/* Temperature scaling implementation */
double BSIM4v6scaleTemperature(double P_Tnom, double TP1, double TP2,
                               double T, double Tnom)
{
    /* P(T) = P(Tnom)·[1 + TP1·(T - Tnom) + TP2·(T - Tnom)²] */
    double delta_T = T - Tnom;
    double scale_factor = 1.0 + TP1 * delta_T + TP2 * delta_T * delta_T;
    
    return P_Tnom * scale_factor;
}
```

**SPICE Integration**: These functions are called during device setup (`BSIM4v6setup`) to compute effective parameters for each instance based on its geometry and temperature.

### 4. Matrix Stamping Implementation (`b4v6ld.c`)

#### 4.1 7×7 Conductance Matrix Stamping

The DC load function in `b4v6ld.c` implements the complete 7×7 matrix stamping:

```c
/* Pseudo-code for matrix stamping */
int BSIM4v6load(GENmodel *genmodel, CKTcircuit *ckt)
{
    BSIM4v6model *model = (BSIM4v6model *)genmodel;
    BSIM4v6instance *inst;
    
    for (inst = model->bsim4v6instances; inst != NULL; inst = inst->bsim4v6nextInstance) {
        /* Calculate conductances from mathematical model */
        double gds = calculateGds(inst);  /* ∂Id/∂Vds */
        double gm = calculateGm(inst);    /* ∂Id/∂Vgs */
        double gmb = calculateGmb(inst);  /* ∂Id/∂Vbs */
        double gbd = calculateGbd(inst);  /* ∂Ibd/∂Vbd */
        double gbs = calculateGbs(inst);  /* ∂Ibs/∂Vbs */
        
        /* Stamp internal node conductances */
        /* Gd'd' = 1/Rd + gds + gbd */
        double GdPrimeDPrime = 1.0/inst->bsim4v6rd + gds + gbd;
        *(inst->bsim4v6dDPrimePtr) += GdPrimeDPrime;
        
        /* Gs's' = 1/Rs + gds + gbs + gm + gmb */
        double GsPrimeSPrime = 1.0/inst->bsim4v6rs + gds + gbs + gm + gmb;
        *(inst->bsim4v6sSPrimePtr) += GsPrimeSPrime;
        
        /* Cross terms */
        /* Gd's' = -gds */
        *(inst->bsim4v6dPrimeSPtr) += -gds;
        *(inst->bsim4v6sPrimeDPtr) += -gds;
        
        /* Stamp external to internal connections */
        /* Gdd' = -1/Rd */
        int dNode = inst->bsim4v6dNode;
        int dPrimeNode = inst->bsim4v6dNodePrime;
        CKTaddToMatrixElement(ckt, dNode, dPrimeNode, -1.0/inst->bsim4v6rd);
        CKTaddToMatrixElement(ckt, dPrimeNode, dNode, -1.0/inst->bsim4v6rd);
        
        /* Gss' = -1/Rs */
        int sNode = inst->bsim4v6sNode;
        int sPrimeNode = inst->bsim4v6sNodePrime;
        CKTaddToMatrixElement(ckt, sNode, sPrimeNode, -1.0/inst->bsim4v6rs);
        CKTaddToMatrixElement(ckt, sPrimeNode, sNode, -1.0/inst->bsim4v6rs);
        
        /* Stamp RHS (right-hand side) current vector */
        double Id = calculateDrainCurrent(inst);
        CKTaddToRHSVector(ckt, dPrimeNode, -Id);
        CKTaddToRHSVector(ckt, sPrimeNode, Id);
    }
    
    return OK;
}
```

**Mathematical Mapping**: This implements the exact 7×7 matrix structure:
```
[Gdd   Gdg   Gds   Gdb   Gdd'  Gds'  0]
[Ggd   Ggg   Ggs   Ggb   Ggd'  Ggs'  0]
[Gsd   Gsg   Gss   Gsb   Gsd'  Gss'  0]
[Gbd   Bbg   Gbs   Gbb   Gbd'  Gbs'  0]
[Gd'd  Gd'g  Gd's  Gd'b  Gd'd' Gd's' 0]
[Gs'd  Gs'g  Gs's  Gs'b  Gs'd' Gs's' 0]
[0     0     0     0     0     0     0]
```

### 5. Convergence and Error Checking (`b4v6cvtest.c`, `b4v6trunc.c`)

#### 5.1 Newton-Raphson Convergence Test

The `b4v6cvtest.c` file implements the convergence checking:

```c
/* Pseudo-code for convergence test */
int BSIM4v6convTest(BSIM4v6instance *inst, CKTcircuit *ckt)
{
    int converged = 1;
    
    /* Voltage convergence: |ΔV| < VNTOL + RELTOL·MAX(|V_new|, |V_old|) */
    double vgs_old = getStateValue(ckt, inst->bsim4v6vgsState, ckt->CKTstate0);
    double vgs_new = getStateValue(ckt, inst->bsim4v6vgsState, ckt->CKTstate1);
    double delta_vgs = vgs_new - vgs_old;
    double vgs_max = MAX(fabs(vgs_new), fabs(vgs_old));
    
    if (fabs(delta_vgs) > (ckt->CKTvoltTol + ckt->CKTreltol * vgs_max)) {
        converged = 0;
    }
    
    /* Charge convergence: |ΔQ| < CHGTOL */
    double qgs_old = getStateValue(ckt, inst->bsim4v6qgsState, ckt->CKTstate0);
    double qgs_new = getStateValue(ckt, inst->bsim4v6qgsState, ckt->CKTstate1);
    double delta_qgs = qgs_new - qgs_old;
    
    if (fabs(delta_qgs) > ckt->CKTchargeTol) {
        converged = 0;
    }
    
    /* Current convergence: |ΔI| < ABSTOL + RELTOL·MAX(|I_new|, |I_old|) */
    double Id_old = calculateCurrentFromState(ckt, inst, ckt->CKTstate0);
    double Id_new = calculateCurrentFromState(ckt, inst, ckt->CKTstate1);
    double delta_Id = Id_new - Id_old;
    double Id_max = MAX(fabs(Id_new), fabs(Id_old));
    
    if (fabs(delta_Id) > (ckt->CKTabstol + ckt->CKTreltol * Id_max)) {
        converged = 0;
    }
    
    return converged;
}
```

#### 5.2 Local Truncation Error Calculation

The `b4v6trunc.c` file implements LTE for adaptive time-step control:

```c
/* Pseudo-code for LTE calculation */
double BSIM4v6trunc(BSIM4v6instance *inst, CKTcircuit *ckt, double *timeStep)
{
    /* Get charge states at three time points */
    double q_n1 = getStateValue(ckt, inst->bsim4v6qgsState, ckt->CKTstate[2]); /* t_{n-1} */
    double q_n = getStateValue(ckt, inst->bsim4v6qgsState, ckt->CKTstate[1]);   /* t_n */
    double q_np1 = getStateValue(ckt, inst->bsim4v6qgsState, ckt->CKTstate[0]); /* t_{n+1} */
    
    /* Calculate derivatives for polynomial extrapolation */
    double h = ckt->CKTdelta;  /* Current time step */
    double dq_dt = (q_n - q_n1) / h;  /* First derivative at t_n */
    double d2q_dt2 = (q_n - 2.0*q_n1 + getStateValue(ckt, inst->bsim4v6qgsState, ckt->CKTstate[3])) / (h*h);
    
    /* Predicted charge: q_pred = q_n + h·dq/dt + h²/2·d²q/dt² */
    double q_pred = q_n + h * dq_dt + (h*h)/2.0 * d2q_dt2;
    
    /* Charge-based LTE: ε_charge = |q - q_pred|/(ABS_TOL + REL_TOL·MAX(|q_n|, |q_np1|)) */
    double q_max = MAX(fabs(q_n), fabs(q_np1));
    double epsilon_charge = fabs(q_np1 - q_pred) / (ckt->CKTabstol + ckt->CKTreltol * q_max);
    
    /* Similar calculation for current-based LTE */
    double I_n = calculateCurrent(inst, ckt->CKTstate[1]);
    double I_np1 = calculateCurrent(inst, ckt->CKTstate[0]);
    double dI_dt = (I_n - calculateCurrent(inst, ckt->CKTstate[2])) / h;
    double I_pred = I_n + h * dI_dt;
    double I_max = MAX(fabs(I_n), fabs(I_np1));
    double epsilon_current = fabs(I_np1 - I_pred) / (ckt->CKTabstol + ckt->CKTreltol * I_max);
    
    /* Overall LTE = MAX(ε_charge, ε_current) */
    double LTE = MAX(epsilon_charge, epsilon_current);
    
    /* Time step control: adjust if LTE > TOL or LTE < TOL/10 */
    if (LTE > ckt->CKTtrtol) {
        *timeStep = h * 0.5;  /* Reduce time step */
    } else if (LTE < ckt->CKTtrtol / 10.0) {
        *timeStep = h * 2.0;  /* Increase time step */
    }
    
    return LTE;
}
```

**Mathematical Mapping**: This implements the exact LTE formulas:
- `q_pred(t_{n+1}) = q(t_n) + h·dq/dt(t_n) + h²/2·d²q/dt²(t_n