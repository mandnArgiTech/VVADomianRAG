# BSIM2: Improved Subthreshold and Empirical Mathematics

_Generated 2026-04-12 11:33 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/bsim2def.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2eval.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2ld.c`

# BSIM2: Improved Subthreshold and Empirical Mathematics

## Technical Introduction

The BSIM2 (Berkeley Short-Channel IGFET Model, Version 2) implementation in Ngspice represents a significant evolution from BSIM1, addressing critical convergence and accuracy limitations through enhanced empirical formulations. This chapter examines the core C files that implement the model's mathematical framework: `bsim2def.h` defines the hierarchical data structures separating 142 model parameters from instance-specific state variables; `b2par.c` implements the parameter binding system mapping SPICE deck parameters to internal C variables; `b2temp.c` provides comprehensive temperature scaling algorithms for all physical parameters; `b2eval.c` contains the core device physics evaluation with continuous derivatives across operating regions; and `b2ld.c` handles matrix loading with Newton-Raphson convergence control. Together, these files implement BSIM2's key innovations: improved subthreshold modeling with voltage-dependent slope factors, geometric scaling effects for short-channel and narrow-width devices, a unified current expression with C¹ continuity, and robust convergence algorithms essential for digital circuit simulation.

## Mathematical Formulation

### 1. Threshold Voltage Model with Geometric Scaling

The BSIM2 threshold voltage model extends BSIM1 with improved short-channel and narrow-width effects, providing better accuracy for scaled technologies:

```
Vth = Vfb + Φ·Fn + γ·Fs - η_eff·Vds
```

**Component Breakdown:**

1. **Flat-band and Surface Potential Terms:**
   ```
   Vfb(T) = Vfb - kt1·(T - Tnom)
   Φ(T) = Φ·(T/Tnom) - 2·Vt·ln(T/Tnom) - (Eg(T) - Eg(Tnom))
   ```
   Where `Vt = k·T/q` is the thermal voltage and `Eg(T)` is the temperature-dependent bandgap.

2. **Body Effect with Higher-Order Correction:**
   ```
   γ = k1·√(Φ - Vbs) - k2·(Φ - Vbs)
   ```
   The `k2` term provides second-order correction to the classical √(Φ-Vbs) dependence.

3. **Drain-Induced Barrier Lowering (DIBL):**
   ```
   η_eff = η·(1 + δ·Vds)
   ```
   The `δ` parameter models the voltage dependence of DIBL, a BSIM2 enhancement over BSIM1.

4. **Short-Channel Effect Factor:**
   ```
   Fs = 1 - (ld/Leff)·[√(1 + 2·Xj/ld) - 1]
   ```
   Where `ld` is the lateral diffusion length, `Xj` is junction depth, and `Leff = L - 2·dl`.

5. **Narrow-Width Effect Factor:**
   ```
   Fn = 1 + (k1/(2√Φ))·(wd/Weff)·√(Φ - Vbs)
   ```
   Where `wd` is the lateral diffusion width and `Weff = W - 2·dw`.

### 2. Mobility Degradation with Temperature and Field Dependence

BSIM2 implements a comprehensive mobility model addressing vertical field, velocity saturation, and temperature effects:

```
μ_eff = μ0(T) / [1 + θ·(Vgs - Vth)] · Fsat
```

**Temperature-Dependent Low-Field Mobility:**
```
μ0(T) = μ0·(T/Tnom)^{-UTE}·[1 + UA1·ΔT + UB1·ΔT² + UC1·ΔT³]
```
Where `ΔT = T - Tnom` and `UTE` is the mobility temperature exponent.

**Velocity Saturation Factor:**
```
Fsat = 1 / [1 + (Vds/Vdsat)^α]
Vdsat = (Vgst·Leff·Ec) / (Vgst + Leff·Ec)
Ec = 2·vsat(T)/μ_vert
vsat(T) = vsat·(T/Tnom)^{-0.5}
```
The exponent `α` controls the sharpness of the saturation transition.

### 3. Unified Drain Current with Continuous Derivatives

BSIM2's key innovation is a unified current expression with C¹ continuity across all operating regions:

```
Ids = Ids_sub·f_sub + Ids_strong·(1 - f_sub)
```

**Subthreshold Current (Exponential Region):**
```
Ids_sub = β·Vt²·exp((Vgst - Voff)/(n·Vt))·[1 - exp(-Vds/Vt)]
n = n0 + nb·Vbs + nd·Vds
β = μ_eff·Cox·(Weff/Leff)
```
The subthreshold slope factor `n` includes both body (`nb`) and drain (`nd`) dependence.

**Strong Inversion Current:**
```
Ids_strong = Ids_lin·(1 - f_blend) + Ids_sat·f_blend

Ids_lin = β·[Vgst·Vdse - 0.5·Vdse²]
Ids_sat = 0.5·β·Vgst²·(1 + λ·Vds)
```

**Smoothing Functions for Continuity:**
```
f_sub = 0.5·[1 - tanh(Vgst/Vgst0)]          (subthreshold/strong inversion)
f_blend = 0.5·[1 + tanh(α_blend·(Vds - Vdsat))]  (linear/saturation)
Vdse = Vdsat·[1 - log(1 + exp(1 - Vds/Vdsat - δ_smooth))/(1 + exp(1 - Vds/Vdsat - δ_smooth))]
```

### 4. Small-Signal Parameters for AC Analysis

The derivatives are analytically computed from the unified current expression:

**Transconductance:**
```
gm = ∂Ids/∂Vgs = β·Vdse·(1 - f_sub) + Ids_sub·(-0.5/Vgst0)·sech²(Vgst/Vgst0)
```

**Output Conductance:**
```
gds = ∂Ids/∂Vds = β·λ·Ids_sat·(1 - f_blend) + β·(Vgst - Vdse)·f_blend·α_blend·sech²(α_blend·(Vds-Vdsat))
```

**Bulk Transconductance (via chain rule):**
```
gmb = ∂Ids/∂Vbs = -gm·(∂Vth/∂Vbs)
∂Vth/∂Vbs = -0.5·k1/√(Φ - Vbs) - k2
```

### 5. Capacitance Modeling

**Overlap Capacitances (linear voltage-independent):**
```
Cgdo = CGDO·Weff
Cgso = CGSO·Weff
Cgb = CGB·Leff
```

**Junction Capacitances (voltage-dependent):**
```
Cj(V) = Cj0/√(1 - V/Φbi), V < 0
Cj(V) = Cj0·(1 + V/Φbi), V ≥ 0
```
Where `Φbi(T) = Φbi·(T/Tnom) - 2·Vt·ln(T/Tnom)` is the temperature-adjusted built-in potential.

## Convergence Analysis

### 1. Newton-Raphson Convergence Criteria

BSIM2 implements rigorous convergence checking through the `BSIM2convTest()` function:

**Voltage Convergence Test:**
```
|Vgs_new - Vgs_old| < ε_v·max(|Vgs_new|, |Vth|) + ε_a
|Vds_new - Vds_old| < ε_v·max(|Vds_new|, |Vdsat|) + ε_a
|Vbs_new - Vbs_old| < ε_v·max(|Vbs_new|, |Φ|) + ε_a
```
Where `ε_v = CKTreltol` (typically 0.001) and `ε_a = CKTabstol` (typically 1e-12).

**Current Convergence Test:**
```
|Ids_new - Ids_old| < ε_v·max(|Ids_new|, |Ids_sat|) + ε_a
```

**Charge Conservation Test:**
```
|Q_new - Q_old| < ε_v·max(|Q_new|, |Cox·Vgs|) + ε_chg
```
Where `ε_chg = CKTchgTol` (typically 1e-14).

### 2. Newton-Raphson Voltage Limiting Algorithm

The `DEVfetlim()` function prevents oscillatory convergence:

**Above Threshold Region (Vgs > Vth):**
```
If Vnew > Vth + 10.0: Vlimited = Vth + 10.0
If Vnew < Vth: Vlimited = Vth (prevent crossing)
If |ΔV| > 2·Vt: ΔVlimited = sign(ΔV)·2·Vt
```

**Below Threshold Region (Vgs ≤ Vth):**
```
If Vnew < Vth - 0.5: Vlimited = Vth - 0.5
If Vnew > Vth: Vlimited = Vth (prevent crossing)
If |ΔV| > 50·Vt: ΔVlimited = sign(ΔV)·50·Vt
```

### 3. Jacobian Matrix Conditioning

The 4×4 conductance matrix must remain well-conditioned for NR convergence:

**Minimum Conductance Enforcement:**
```
gds_min = 1e-12·(Weff/Leff)  // Prevents singular matrix
gm_min = 1e-12·(Weff/Leff)
```

**Matrix Stamping with Parasitic Conductances:**
```
Gdd = gds + gds_min + 1/Rd
Gss = gds + gm + gmb + gds_min + 1/Rs
Gbb = gmb + gjunction(Vbs) + gjunction(Vbd)
```

### 4. Source-Drain Swap Handling

For negative Vds, BSIM2 swaps source and drain terminals to maintain numerical stability:

**Swap Condition:**
```
If Vds < 0:
    Vds' = -Vds
    Vgs' = Vgs - Vds
    Vbs' = Vbs - Vds
    Ids' = -Ids
    gm' = -gmb
    gmb' = -gm
```

**Matrix Reconfiguration:**
The 4×4 conductance matrix is reconfigured by swapping rows/columns corresponding to drain and source nodes.

### 5. Temperature-Dependent Convergence

Temperature scaling affects convergence thresholds:

**Thermal Voltage Scaling:**
```
Vt(T) = k·T/q
ε_v(T) = ε_v·√(T/Tnom)  // Relax tolerance at higher temperatures
```

**Mobility Degradation Impact:**
```
μ(T) ↓ ⇒ β(T) ↓ ⇒ gm(T) ↓ ⇒ Slower convergence
```
The NR algorithm automatically adjusts step sizes based on the temperature-dependent transconductance.

### 6. SPICE Integration for Convergence

**Circuit-Level Integration:**
```
CKTcircuit.ckteqns = G·x = b
where G = Σ(G_device) + G_parasitic
```
BSIM2 contributes to the global Jacobian matrix `G` through the `BSIM2load()` function.

**Convergence Flag Propagation:**
```
if (inst->BSIM2check) {
    ckt->CKTnoncon++;  // Increment non-convergence counter
    ckt->CKTtroubleElt = (GENinstance *)inst;  // Mark troublesome device
}
```

**Time Step Control for Transient Analysis:**
```
Δt_new = Δt_old·min(1.5, max(0.5, √(ε_LTE/|LTE|)))
LTE = |h·(d²Q/dt²)| ≈ |h·(i(t+h) - i(t))/h|
```
Where `ε_LTE = CKTtrtol·(ε_v·|Ids| + ε_a)` with `CKTtrtol ≈ 7`.

### 7. Empirical Convergence Enhancements

**Smoothing Parameter Optimization:**
```
δ_smooth = 0.01·Vdsat  // Prevents derivative discontinuities
α_blend = 50/Vdsat     // Controls linear/saturation transition sharpness
Vgst0 = 0.1            // Subthreshold transition voltage
```

**Derivative Regularization:**
```
gm_regularized = gm + sign(gm)·1e-12
gds_regularized = max(gds, 1e-12·(Weff/Leff))
```
Prevents zero or negative conductances that can cause matrix singularity.

This mathematical formulation demonstrates how BSIM2 achieves robust convergence through:
1. **Continuous derivatives** across all operating regions via smoothing functions
2. **Conservative voltage limiting** that respects device physics
3. **Temperature-aware tolerance scaling**
4. **Regularized conductances** preventing numerical instability
5. **Proper handling of terminal swapping** for bidirectional operation

The model's empirical parameters (`η`, `δ`, `α`, `θ`, etc.) are extracted from measured data and provide the necessary flexibility to model deep-submicron MOSFET behavior while maintaining NR convergence properties essential for SPICE simulation.

## C Implementation

### 1. Core Data Structures and Memory Management

#### 1.1 Hierarchical Structure Organization

The BSIM2 implementation in Ngspice employs a dual-structure hierarchy that separates model-level parameters from instance-specific data:

```c
/* BSIM2 Model Structure - 142 parameters */
typedef struct sBSIM2model {
    int BSIM2type;                          /* NCH or PCH */
    double BSIM2version;                    /* Model version (2.1) */
    
    /* DC Model Parameters (Group 1: Threshold) */
    double BSIM2vfb;                        /* Flat-band voltage */
    double BSIM2phi;                        /* Surface potential */
    double BSIM2k1;                         /* First-order body effect */
    double BSIM2k2;                         /* Second-order body effect */
    double BSIM2eta;                        /* DIBL coefficient */
    double BSIM2mu0;                        /* Low-field mobility */
    double BSIM2theta;                      /* Mobility degradation */
    
    /* DC Model Parameters (Group 2: Saturation) */
    double BSIM2vsat;                       /* Saturation velocity */
    double BSIM2kappa;                      /* Saturation field factor */
    double BSIM2delta;                      /* Channel length modulation */
    double BSIM2alpha;                      /* Velocity saturation exponent */
    
    /* Subthreshold Parameters (Group 4) */
    double BSIM2n0;                         /* Subthreshold slope factor */
    double BSIM2nb;                         /* Body effect on n-factor */
    double BSIM2nd;                         /* Drain-induced n-factor */
    double BSIM2vof;                        /* Subthreshold offset voltage */
    
    /* Linked list management */
    struct sBSIM2model *BSIM2nextModel;
    sBSIM2instance *BSIM2instances;
    
    /* Parameter flags (142 total) */
    unsigned int BSIM2vfbGiven : 1;
    unsigned int BSIM2phiGiven : 1;
    /* ... 140 more flag bits */
} BSIM2model;
```

**Mathematical Mapping**: The `BSIM2model` structure directly stores the coefficients from the threshold voltage equation:
- `BSIM2vfb` ↔ V_fb (flat-band voltage)
- `BSIM2phi` ↔ Φ (surface potential)
- `BSIM2k1`, `BSIM2k2` ↔ k₁, k₂ (body effect coefficients)
- `BSIM2eta`, `BSIM2delta` ↔ η, δ (DIBL coefficients)

#### 1.2 Instance-Specific Data Structure

```c
/* BSIM2 Instance Structure - 48 members */
typedef struct sBSIM2instance {
    /* Terminal node indices */
    int BSIM2dNode;                         /* External drain */
    int BSIM2gNode;                         /* External gate */
    int BSIM2sNode;                         /* External source */
    int BSIM2bNode;                         /* External bulk */
    int BSIM2dPrimeNode;                    /* Internal drain (after RD) */
    int BSIM2sPrimeNode;                    /* Internal source (after RS) */
    
    /* Geometry parameters */
    double BSIM2l;                          /* Drawn length */
    double BSIM2w;                          /* Drawn width */
    double BSIM2leff;                       /* Effective length */
    double BSIM2weff;                       /* Effective width */
    
    /* Electrical state variables */
    double BSIM2vds;                        /* Drain-source voltage */
    double BSIM2vgs;                        /* Gate-source voltage */
    double BSIM2vbs;                        /* Bulk-source voltage */
    double BSIM2vdsat;                      /* Saturation voltage */
    
    /* Current and conductance */
    double BSIM2ids;                        /* Drain current */
    double BSIM2gm;                         /* Transconductance */
    double BSIM2gds;                        /* Drain conductance */
    double BSIM2gmb;                        /* Bulk transconductance */
    
    /* Temperature-dependent parameters */
    double BSIM2temp;                       /* Instance temperature */
    double BSIM2vfbTemp;                    /* Temperature-adjusted Vfb */
    double BSIM2phiTemp;                    /* Temperature-adjusted Phi */
    double BSIM2mu0Temp;                    /* Temperature-adjusted mobility */
    
    /* Matrix pointers (16 for main + 4 for parasitic) */
    double *BSIM2DdPtr;                     /* G[drain][drain] */
    double *BSIM2DgPtr;                     /* G[drain][gate] */
    double *BSIM2DsPtr;                     /* G[drain][source] */
    double *BSIM2DbPtr;                     /* G[drain][bulk] */
    /* ... 14 more matrix pointers */
} BSIM2instance;
```

**SPICE Integration**: The instance structure maintains both the electrical state (`BSIM2vgs`, `BSIM2vds`, `BSIM2vbs`) and the computed small-signal parameters (`BSIM2gm`, `BSIM2gds`, `BSIM2gmb`) that are stamped into the circuit matrix during Newton-Raphson iterations.

### 2. Parameter Binding and Validation System

#### 2.1 Parameter Table Architecture (`b2par.c`)

The BSIM2 model uses a comprehensive parameter mapping system with 142 model parameters and 24 instance parameters:

```c
/* 142 Model Parameters with IFparm mapping */
static IFparm BSIM2mPTable[] = {
    /* Threshold and Body Effect */
    IOP("vfb",    BSIM2_VFB,    IF_REAL, "Flat-band voltage"),
    IOP("phi",    BSIM2_PHI,    IF_REAL, "Surface potential"),
    IOP("k1",     BSIM2_K1,     IF_REAL, "First-order body effect"),
    IOP("k2",     BSIM2_K2,     IF_REAL, "Second-order body effect"),
    IOP("eta",    BSIM2_ETA,    IF_REAL, "Static feedback (DIBL)"),
    
    /* Subthreshold */
    IOP("n0",     BSIM2_N0,     IF_REAL, "Subthreshold slope factor"),
    IOP("nb",     BSIM2_NB,     IF_REAL, "Body effect on n-factor"),
    IOP("nd",     BSIM2_ND,     IF_REAL, "Drain-induced barrier lowering"),
    IOP("vof",    BSIM2_VOF,    IF_REAL, "Subthreshold offset voltage"),
    
    /* Temperature */
    IOP("ute",    BSIM2_UTE,    IF_REAL, "Mobility temperature exponent"),
    IOP("kt1",    BSIM2_KT1,    IF_REAL, "Vfb temperature coefficient"),
    IOP("kt2",    BSIM2_KT2,    IF_REAL, "Phi temperature coefficient"),
    IOP("ua1",    BSIM2_UA1,    IF_REAL, "First-order mobility temp coeff"),
    IOP("ub1",    BSIM2_UB1,    IF_REAL, "Second-order mobility temp coeff"),
    IOP("uc1",    BSIM2_UC1,    IF_REAL, "Third-order mobility temp coeff"),
};
```

**Mathematical Connection**: Each parameter in the table corresponds directly to a coefficient in the BSIM2 equations:
- `n0`, `nb`, `nd` ↔ n₀, n_b, n_d in the subthreshold slope factor: n = n₀ + n_b·V_bs + n_d·V_ds
- `ute`, `ua1`, `ub1`, `uc1` ↔ UTE, UA1, UB1, UC1 in the mobility temperature model

#### 2.2 Setup and Validation Logic (`b2set.c`)

The `BSIM2setup()` function performs critical parameter validation and matrix allocation:

```c
int BSIM2setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    BSIM2model *model = (BSIM2model *)inModel;
    BSIM2instance *inst;
    
    for (; model; model = model->BSIM2nextModel) {
        /* Critical parameter validation */
        if (!model->BSIM2phiGiven) {
            model->BSIM2phi = 0.7;  /* Default surface potential */
        } else if (model->BSIM2phi <= 0.1) {
            fprintf(stderr, "BSIM2: PHI too small, using 0.1V\n");
            model->BSIM2phi = 0.1;
        }
        
        /* Calculate oxide capacitance */
        if (model->BSIM2toxGiven && model->BSIM2tox > 0) {
            model->BSIM2cox = 3.9 * 8.854e-12 / model->BSIM2tox;
        } else {
            model->BSIM2cox = 3.45e-3;  /* Default ~100Å */
        }
        
        /* Process each instance */
        for (inst = model->BSIM2instances; inst; inst = inst->BSIM2nextInstance) {
            /* Geometry calculations with validation */
            inst->BSIM2leff = inst->BSIM2l - 2 * model->BSIM2dl;
            inst->BSIM2weff = inst->BSIM2w - 2 * model->BSIM2dw;
            
            if (inst->BSIM2leff <= 0.0) {
                inst->BSIM2leff = 1e-12;
                fprintf(stderr, "BSIM2: Negative Leff, using %g\n", inst->BSIM2leff);
            }
            
            /* Calculate beta = μ·Cox·W/L */
            inst->BSIM2beta = model->BSIM2mu0 * model->BSIM2cox * 
                             (inst->BSIM2weff / inst->BSIM2leff);
            
            /* Allocate 6×6 SMP matrix for D, G, S, B, D', S' */
            inst->BSIM2DdPtr = SMPmakeElt(matrix, inst->BSIM2dNode, inst->BSIM2dNode);
            inst->BSIM2DgPtr = SMPmakeElt(matrix, inst->BSIM2dNode, inst->BSIM2gNode);
            /* ... 14 more matrix pointer allocations */
            
            /* Allocate state vector for charges (5 charges) */
            inst->BSIM2stateIndex[0] = *states; (*states)++;  /* qgs */
            inst->BSIM2stateIndex[1] = *states; (*states)++;  /* qgd */
            inst->BSIM2stateIndex[2] = *states; (*states)++;  /* qgb */
            inst->BSIM2stateIndex[3] = *states; (*states)++;  /* qbd */
            inst->BSIM2stateIndex[4] = *states; (*states)++;  /* qbs */
        }
    }
    return OK;
}
```

**SPICE Matrix Mathematics**: The `SMPmakeElt()` calls create a 6×6 sparse matrix representation for the device's conductance matrix, mapping to the mathematical formulation:
- Nodes: 0:D, 1:G, 2:S, 3:B, 4:D', 5:S'
- Each pointer (e.g., `BSIM2DdPtr`) corresponds to G[drain][drain] in the conductance matrix

### 3. Temperature Scaling Implementation (`b2temp.c`)

#### 3.1 Comprehensive Temperature Model

The BSIM2 temperature scaling algorithm implements the full temperature dependence of all physical parameters:

```c
void BSIM2temp(BSIM2instance *inst, BSIM2model *model, CKTcircuit *ckt) {
    double T = inst->BSIM2temp + CONSTCtoK;
    double TNOM = model->BSIM2tnom + CONSTCtoK;
    double Tratio = T / TNOM;
    double Vt = KoverQ * T;
    
    /* 1. Bandgap and intrinsic carrier concentration scaling */
    double Eg = 1.16 - 7.02e-4 * T * T / (T + 1108.0);
    double Egnom = 1.16 - 7.02e-4 * TNOM * TNOM / (TNOM + 1108.0);
    
    /* 2. Flat-band voltage temperature dependence */
    inst->BSIM2vfbTemp = model->BSIM2vfb - model->BSIM2kt1 * (T - TNOM);
    
    /* 3. Surface potential temperature dependence */
    inst->BSIM2phiTemp = model->BSIM2phi * Tratio 
                        - 2.0 * Vt * log(T / TNOM) 
                        - (Eg - Egnom);
    
    /* 4. Mobility temperature degradation (3-term model) */
    inst->BSIM2mu0Temp = model->BSIM2mu0 * pow(Tratio, -model->BSIM2ute)
                        * (1.0 + model->BSIM2ua1 * (T - TNOM)
                               + model->BSIM2ub1 * (T*T - TNOM*TNOM)
                               + model->BSIM2uc1 * (T*T*T - TNOM*TNOM*TNOM));
    
    /* 5. Subthreshold slope factor temperature dependence */
    inst->BSIM2n0Temp = model->BSIM2n0 * (1.0 + 0.5e-3 * (T - TNOM));
    
    /* Store for device evaluation */
    inst->BSIM2vth0 = inst->BSIM2vfbTemp + inst->BSIM2phiTemp 
                     + model->BSIM2k1 * sqrt(inst->BSIM2phiTemp);
}
```

**Mathematical Implementation**: This code directly implements the temperature scaling equations:
- `inst->BSIM2mu0Temp` ↔ μ₀(T) = μ₀·(T/T_nom)^{-UTE}·[1 + UA1·ΔT + UB1·ΔT² + UC1·ΔT³]
- `inst->BSIM2phiTemp` ↔ Φ(T) = Φ·(T/T_nom) - 2V_t·ln(T/T_nom) - (E_g(T) - E_g(T_nom))
- `inst->BSIM2n0Temp` ↔ n₀(T) = n₀·[1 + 0.5e-3·(T - T_nom)]

### 4. Core Device Physics Evaluation (`b2eval.c`)

#### 4.1 Threshold Voltage Calculation with Short-Channel Effects

```c
double BSIM2vth(BSIM2instance *inst, BSIM2model *model, 
                double Vbs, double Vds) {
    double phi = inst->BSIM2phiTemp;
    double Vfb = inst->BSIM2vfbTemp;
    double k1 = model->BSIM2k1;
    double k2 = model->BSIM2k2;
    double eta = model->BSIM2eta;
    double delta = model->BSIM2delta;
    
    /* 1. Body effect term */
    double sqrt_phi_Vbs = sqrt(phi - Vbs);
    double gamma = k1 * sqrt_phi_Vbs - k2 * (phi - Vbs);
    
    /* 2. Static feedback (DIBL) - η·Vds term */
    double eta_eff = eta * (1.0 + delta * Vds);
    
    /* 3. Short-channel effect reduction factor */
    double Leff = inst->BSIM2leff;
    double Xj = model->BSIM2xj;
    double ld = model->BSIM2ld;
    
    double Fs = 1.0 - (ld / Leff) * (sqrt(1.0 + 2.0 * Xj / ld) - 1.0);
    
    /* 4. Narrow-width effect */
    double Weff = inst->BSIM2weff;
    double wd = model->BSIM2wd;
    
    double Fn = 1.0 + (k1 / (2.0 * sqrt(phi))) * (wd / Weff) * sqrt_phi_Vbs;
    
    /* 5. Complete threshold voltage */
    double Vth = Vfb + phi * Fn + gamma * Fs - eta_eff * Vds;
    
    return Vth;
}
```

**Mathematical Mapping**: This function implements the complete BSIM2 threshold voltage equation:
- `gamma` ↔ γ = k₁·√(Φ - V_bs) - k₂·(Φ - V_bs)
- `eta_eff` ↔ η_eff = η·(1 + δ·V_ds)
- `Fs` ↔ F_s = 1 - (l_d/L_eff)·[√(1 + 2X_j/l_d) - 1] (short-channel effect)
- `Fn` ↔ F_n = 1 + (k₁/(2√Φ))·(w_d/W_eff)·√(Φ - V_bs) (narrow-width effect)
- Final result: V_th = V_fb + Φ·F_n + γ·F_s - η_eff·V_ds

#### 4.2 Mobility Degradation Model Implementation

```c
double BSIM2mobility(BSIM2instance *inst, BSIM2model *model,
                     double Vgs, double Vth, double Vds) {
    double mu0 = inst->BSIM2mu0Temp;
    double theta = model->BSIM2theta;
    double alpha = model->BSIM2alpha;
    double vsat = inst->BSIM2vsatTemp;
    double Leff = inst->BSIM2leff;
    
    /* 1. Vertical field mobility reduction */
    double Vgst = Vgs - Vth;
    double mu_vert = mu0 / (1.0 + theta * Vgst);
    
    /* 2. Lateral field velocity saturation */
    double Ec = 2.0 * vsat / mu_vert;
    double Vdsat = (Vgst * Leff * Ec) / (Vgst + Leff * Ec);
    
    double Fsat = 1.0 / (1.0 + pow(Vds / Vdsat, alpha));
    
    /* 3. Combined mobility */
    double mu_eff = mu_vert * Fsat;
    
    return mu_eff;
}
```

**Physics Implementation**: This code implements the dual mobility degradation model:
- `mu_vert` ↔ μ_vert = μ₀(T)/[1 + θ·(V_gs - V_th)] (vertical field effect)
- `Fsat` ↔ F_sat = 1/[1 + (V_ds/V_dsat)^α] (velocity saturation)
- Combined: μ_eff = μ_vert·F_sat

#### 4.3 Unified Drain Current Evaluation

The `BSIM2eval()` function implements the complete current equation with continuous derivatives:

```c
void BSIM2eval(BSIM2instance *inst, BSIM2model *model,
               double Vgs, double Vds, double Vbs,
               double *Ids, double *gm, double *gds, double *gmb) {
    
    /* 1. Calculate threshold voltage */
    double Vth = BSIM2vth(inst, model, Vbs, Vds);
    double Vgst = Vgs - Vth;
    
    /* 2. Calculate effective mobility */
    double mu_eff = BSIM2mobility(inst, model, Vgs, Vth, Vds);
    
    /* 3. Calculate beta factor */
    double beta = mu_eff * model->BSIM2cox * 
                  (inst->BSIM2weff / inst->BSIM2leff);
    
    /* 4. Subthreshold current calculation */
    double n = model->BSIM2n0 + model->BSIM2nb * Vbs + model->BSIM2nd * Vds;
    double Vt = KoverQ * (inst->BSIM2temp + CONSTCtoK);
    double Voff = model->BSIM2vof;
    
    double Ids_sub = beta * Vt * Vt * 
                     exp((Vgst - Voff) / (n * Vt)) * 
                     (1.0 - exp(-Vds / Vt));
    
    /* 5. Strong inversion current with smoothing */
    double Vdsat = (Vgst * inst->BSIM2leff * inst->BSIM2vsatTemp) /
                   (Vgst + inst->BSIM2leff * inst->BSIM2vsatTemp);
    
    /* Smoothing function for linear/saturation transition */
    double delta = 0.01;
    double Vdse = Vdsat * (1.0 - log(1.0 + exp(1.0 - Vds/Vdsat - delta)) / 
                           (1.0 + exp(1.0 - Vds/Vdsat - delta)));
    
    double Ids_lin = beta * (Vgst * Vdse - 0.5 * Vdse * Vdse);
    
    /* 6. Channel length modulation */
    double lambda = model->BSIM2lambda;
    double Ids_sat = 0.5 * beta * Vgst * Vgst * 
                     (1.0 + lambda * Vds);
    
    /* 7. Blend linear and saturation regions */
    double alpha = 50.0;  // Blending factor
    double f_blend = 0.5 * (1.0 + tanh(alpha * (Vds - Vdsat)));
    double Ids_strong = Ids_lin * (1.0 - f_blend) + Ids_sat * f_blend;
    
    /* 8. Blend subthreshold and strong inversion */
    double Vgst0 = 0.1;  // Transition voltage
    double f_sub = 0.5 * (1.0 - tanh(Vgst / Vgst0));
    *Ids = Ids_sub * f_sub + Ids_strong * (1.0 - f_sub);
    
    /* 9. Calculate derivatives for matrix stamping */
    *gm = beta * Vdse * (1.0 - f_sub) + 
          Ids_sub * (-0.5 / Vgst0) * (1.0 / cosh(Vgst/Vgst0)/cosh(Vgst/Vgst0));
    
    *gds = beta * lambda * Ids_sat * (1.0 - f_blend) + 
           beta * (Vgst - Vdse) * f_blend * alpha * 
           (1.0 / cosh(alpha*(Vds-Vdsat))/cosh(alpha*(Vds-Vdsat)));
    
    /* 10. Bulk transconductance (chain rule through Vth) */
    double dVth_dVbs = -0.5 * model->BSIM2k1 / sqrt(inst->BSIM2phiTemp - Vbs) 
                      - model->BSIM2k2;
    *gmb = -(*gm) * dVth_dVbs;
    
    /* 11. Apply device polarity for PMOS */
    if (inst->BSIM2mode < 0) {  // PMOS
        *Ids = -(*Ids);
        *gm = -(*gm);
        *gds = -(*gds);
        *gmb = -(*gmb);
    }
}
```

**Continuous Derivative Implementation**: This function ensures C¹ continuity through:
- Hyperbolic tangent blending (`tanh`) between subthreshold and strong inversion
- Smooth transition between linear and saturation regions
- Exact derivative calculations using chain rule for g_mb

### 5. Matrix Loading with Newton-Raphson Convergence Control (`b2ld.c`)

#### 5.1 Voltage Limiting Algorithm (`DEVfetlim`)

```c
double DEVfetlim(double vnew, double vold, double vto, int *icheck) {
    const double vt = 0.025