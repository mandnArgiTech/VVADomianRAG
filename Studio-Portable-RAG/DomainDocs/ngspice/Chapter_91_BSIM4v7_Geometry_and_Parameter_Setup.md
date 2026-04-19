# BSIM4v7: Layout-Dependent Effects, Geometry, and Setup

_Generated 2026-04-12 16:26 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7mpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7mask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7ask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7check.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v7/b4v7geo.c`

# BSIM4v7: Layout-Dependent Effects, Geometry, and Setup

## Technical Introduction

This chapter details the implementation of layout-dependent effects and geometry parameterization in the BSIM4v7 model within the Ngspice EDA framework. The core functionality is distributed across six specialized C source files that work in concert to translate physical layout dimensions and process variations into precise electrical parameters for SPICE simulation.

The file `b4v7set.c` serves as the central setup routine, orchestrating the initialization of the 6×6 conductance matrix structure, allocating sparse matrix pointers for the Newton-Raphson solver, and calculating effective device dimensions with all layout corrections applied. It implements the parameter binning equations `P_effective = P0 + PL/Leff + PW/Weff + PWL/(Leff·Weff)` that scale electrical parameters based on geometry.

The geometry engine `b4v7geo.c` implements the mathematical models for Shallow Trench Isolation (STI) stress and Well Proximity Effect (WPE), calculating mechanical strain `σ_sti` using exponential decay models and distance-dependent WPE factors that modify threshold voltage and mobility parameters. This file ensures all geometry calculations maintain C¹ continuity for Newton-Raphson convergence.

Parameter management is handled through three complementary files: `b4v7mpar.c` defines the extended parameter table that adds BSIM4v7-specific layout parameters to the base MOS1 structure; `b4v7mask.c` implements the parameter masking logic that determines which parameters are instance-specific versus model-wide; and `b4v7ask.c` provides the query interface for simulation output, allowing access to calculated geometry values like effective length `Leff`, effective width `Weff`, and mechanical strain.

Finally, `b4v7check.c` performs validation of all geometry and layout parameters, ensuring physical consistency (e.g., positive dimensions, valid stress coefficients) before simulation begins. Together, these six files implement the complete pipeline from layout specifications in the SPICE netlist to the fully initialized device model ready for DC, AC, and transient analysis.

## Mathematical Formulation

The BSIM4v7 model's layout-dependent effects and geometry scaling are mathematically formulated to translate physical layout dimensions and process variations into precise electrical parameters for SPICE simulation. These formulations are implemented in the C code to ensure continuity and differentiability required for Newton-Raphson convergence.

### 1. Effective Geometry Calculation with Stress Effects

**Drawn to Effective Dimension Transformation:**
```
Leff = Ldrawn - 2·DL - ΔL_stress
Weff = Wdrawn - 2·DW - ΔW_stress
```
Where `DL` and `DW` are model parameters for lateral diffusion, and `ΔL_stress`, `ΔW_stress` are stress-induced dimensional changes computed in `b4v7geo.c`.

**Shallow Trench Isolation (STI) Stress Model:**
The mechanical stress from STI is computed as a function of distance to isolation edges:
```
σ_sti(L) = SA·exp(-SB·(L - SC)) + SD·exp(-SE·(W - SF))
```
Where `SA`, `SB`, `SC`, `SD`, `SE`, `SF` are model parameters stored in `BSIM4v7model` structure as `BSIM4v7sa`, `BSIM4v7sb`, etc.

**Stress-Induced Mobility Change:**
```
μ_stress = μ0 · [1 + MUSTRESS·σ_sti/(1 + STRESSREF·σ_sti)]
```
This modifies the base mobility parameter `BSIM4v7u0` in the instance structure before drain current calculation.

**Stress-Induced Threshold Voltage Shift:**
```
ΔVth_sti = VTHSTRESS·σ_sti·tanh(STRESSEXP·L)
```
This term is added to the composite threshold voltage calculation in the DC load function.

### 2. Well Proximity Effect (WPE) Model

**Distance-Dependent WPE Factor:**
```
WPE_factor = WPEA/(sca + WPEB) + WPEC/(scb + WPED) + WPEE/(scc + WPEF)
```
Where `sca`, `scb`, `scc` are distances to the three nearest well edges, and `WPEA` through `WPEF` are model parameters.

**Parameter Modification via WPE:**
```
Vth0_wpe = BSIM4v7vth0 · (1 + WPEVTH·WPE_factor)
U0_wpe = BSIM4v7u0 · (1 + WPEU0·WPE_factor)
KP_wpe = U0_wpe · Cox
```
These modified values replace the nominal parameters in the instance calculations.

### 3. Composite Threshold Voltage with Layout Effects

The total threshold voltage used in SPICE matrix stamping combines multiple effects:
```
Vth = Vth0_wpe + ΔVth_SCE + ΔVth_DIBL + ΔVth_NWE + ΔVth_TEMP + ΔVth_sti
```

**Short-Channel Effect (SCE):**
```
ΔVth_SCE = -DVT0·exp(-DVT1·Leff/(2·lt)) / (1 + DVT2·Vbs)
```
Where `lt = √(ε_si·tox·Xdep/ε_ox)` is the natural length, computed from `BSIM4v7tox` and doping parameters.

**Drain-Induced Barrier Lowering (DIBL):**
```
ΔVth_DIBL = (ETA0 + ETAB·Vbs)·Vds·exp(-DSUB·Leff/lt0) / (1 + CIT·(Vgs - Vth))
```
This term creates the `gmb` (body transconductance) contribution in the conductance matrix.

**Narrow-Width Effect (NWE):**
```
ΔVth_NWE = K3·Φs·W0/Weff·(1 + K3B·Vbs)
```
Where `Φs = 2·φ_B` is the surface potential from `BSIM4v7phi`.

### 4. Geometry-Dependent Parameter Scaling

**Binning Equations for SPICE Parameters:**
```
P_effective = P0 + PL/Leff + PW/Weff + PWL/(Leff·Weff)
```
Where `P` represents any scalable parameter like `U0`, `VTH0`, etc. This is implemented in `b4v7set.c` during model setup.

**Junction Capacitance Scaling:**
```
Cj = CJ·AD·(1 + MJ·Vbd/PB)^{-MJ} + CJSW·PD·(1 + MJSW·Vbd/PB)^{-MJSW}
```
The areas `AD`, `AS` and perimeters `PD`, `PS` from the instance structure scale the junction capacitances stamped into the AC matrix.

### 5. Temperature Scaling with Geometry Dependence

**Temperature-Dependent Mobility:**
```
μ(T) = U0_wpe · (T/Tnom)^{-UTE} · (1 + UA·Eeff + UB·Eeff²)^{-1}
```
Where `Eeff = (Vgs + Vth)/(6·tox)` is the effective vertical field, and `UTE` is the temperature exponent from the model structure.

**Threshold Voltage Temperature Scaling:**
```
ΔVth_TEMP = (KT1 + KT1L/Leff)·(T/Tnom - 1) + KT2·(T/Tnom - 1)²
```
The `KT1L/Leff` term introduces geometry dependence into the temperature scaling.

## Convergence Analysis

Convergence in BSIM4v7 with layout-dependent effects requires special handling of geometry scaling discontinuities and stress model singularities within the SPICE Newton-Raphson iteration framework.

### 1. Geometry Scaling Continuity Enforcement

**Minimum Dimension Clamping:**
The C code in `b4v7geo.c` enforces:
```
if (Leff <= 0.0) Leff = 1e-12;
if (Weff <= 0.0) Weff = 1e-12;
```
This prevents division by zero in parameter binning equations `PL/Leff` and `PW/Weff`, ensuring the Jacobian matrix remains non-singular.

**Stress Effect Smoothing:**
The STI stress model uses exponential decay:
```
σ_sti(L) = SA·exp(-SB·(L - SC))
```
For `L < SC`, the argument becomes positive, causing exponential growth. The code clamps `L - SC` to a minimum value to prevent overflow and maintain derivative continuity for Newton-Raphson.

### 2. Parameter Binning Continuity

**Derivative Consistency in Binning Equations:**
For Newton-Raphson convergence, the derivatives of binned parameters must be continuous:
```
∂P_effective/∂Leff = -PL/Leff² - PWL/(Weff·Leff²)
∂P_effective/∂Weff = -PW/Weff² - PWL/(Leff·Weff²)
```
These derivatives are computed analytically in the code and contribute to the complete Jacobian through chain rule:
```
∂Id/∂V = (∂Id/∂P_effective)·(∂P_effective/∂Leff)·(∂Leff/∂V) + ...
```
Discontinuities in these derivatives would cause convergence failure.

### 3. WPE Distance Model Regularization

**Distance Parameter Smoothing:**
The WPE factor denominator `(sca + WPEB)` is regularized to prevent singularity:
```
if (sca < 1e-12) sca = 1e-12;
```
This ensures the WPE factor and its derivatives remain finite for all layout configurations.

**WPE Transition Smoothing:**
When transistors are far from well edges (`sca → ∞`), the WPE factor should approach zero smoothly. The implementation uses:
```
WPE_factor = WPEA/(sca + WPEB)  // Natural decay to zero as sca increases
```
This provides continuous derivatives with respect to layout position.

### 4. Stress-Induced Parameter Gradient Management

**Mobility Stress Effect Limiting:**
The mobility enhancement factor is bounded:
```
μ_enhancement = 1 + MUSTRESS·σ_sti/(1 + STRESSREF·σ_sti)
if (μ_enhancement > μ_max) μ_enhancement = μ_max;
if (μ_enhancement < μ_min) μ_enhancement = μ_min;
```
This prevents unrealistic mobility values that could cause convergence oscillations.

**Threshold Voltage Stress Effect Smoothing:**
The `tanh(STRESSEXP·L)` function in `ΔVth_sti` provides smooth saturation:
```
tanh(x) ≈ x for small x, tanh(x) → ±1 for large x
```
This ensures the stress effect has bounded influence and continuous derivatives across all channel lengths.

### 5. Setup Phase Convergence Guarantees

**Parameter Initialization in `b4v7set.c`:**
The setup function ensures all geometry-dependent parameters have valid initial values:
```c
/* Default values for missing parameters */
if (!model->BSIM4v7dlGiven) model->BSIM4v7dl = 0.0;
if (!model->BSIM4v7dwGiven) model->BSIM4v7dw = 0.0;
if (!inst->BSIM4v7lGiven) inst->BSIM4v7l = 100e-6;
if (!inst->BSIM4v7wGiven) inst->BSIM4v7w = 100e-6;
```
This prevents uninitialized variables from causing matrix singularities.

**State Vector Allocation Continuity:**
The charge state indices are allocated contiguously:
```c
inst->BSIM4v7states[0] = (*states)++;  /* qgs */
inst->BSIM4v7states[1] = (*states)++;  /* qgd */
/* ... etc. */
```
This ensures the state vector in `ckt->CKTstate0/1/2` has consistent indexing for all instances, required for convergence testing in `b4v7cvtest.c`.

### 6. Layout-Dependent Convergence Testing

**Geometry-Aware Voltage Convergence:**
The convergence test in `b4v7cvtest.c` uses geometry-scaled tolerances:
```
tol_V = CKTreltol * MAX(|V|, CKTvoltTol) + CKTvoltTol * (1 + |ΔL_stress|/Lnom)
```
The stress-induced dimension change `ΔL_stress` slightly relaxes the voltage tolerance for highly stressed devices, recognizing their parameter uncertainty.

**Stress-Dependent Current Convergence:**
For devices under high stress (`σ_sti > σ_critical`), the current tolerance is adjusted:
```
tol_I = CKTreltol * MAX(|I|, CKTabstol) + CKTabstol * (1 + σ_sti/σ_ref)
```
This accounts for increased numerical sensitivity in stressed devices.

### 7. Matrix Conditioning with Layout Effects

**Diagonal Dominance Enforcement:**
The 6x6 conductance matrix includes geometry-dependent diagonal terms:
```
Gd'd' = 1/Rd + gds + g_stress
Gs's' = 1/Rs + gds + g_stress
```
Where `g_stress` is an additional conductance proportional to `|∂μ_stress/∂V|`, ensuring the matrix remains diagonally dominant even with strong stress effects.

**Stress-Induced Capacitance Regularization:**
The capacitance matrix includes stress-dependent terms:
```
Cgg_stress = Cgg_nominal · (1 + CSTRESS·σ_sti)
```
The derivative `∂Cgg_stress/∂V` is bounded to prevent ill-conditioning of the `G + jωC` matrix in AC analysis.

### 8. Time-Step Control with Geometry Dependence

**Layout-Aware LTE Calculation:**
In `b4v7trunc.c`, the Local Truncation Error calculation includes geometry factors:
```
error = |Δt * i| / (CKTabstol + CKTreltol * MAX(|q|, CKTchgTol) * (1 + |ΔW_stress|/Wnom))
```
Wider devices (`Wnom` larger) or those with significant stress-induced width changes get slightly relaxed charge error tolerances.

**Stress-Dependent Time-Step Limiting:**
For devices with `σ_sti > σ_warning`, the maximum time-step is reduced:
```
Δt_max_stress = Δt_max_nominal / (1 + σ_sti/σ_safe)
```
This prevents numerical instability from rapid stress-induced parameter variations.

This convergence analysis demonstrates how BSIM4v7's layout-dependent effects are numerically stabilized within SPICE's simulation framework, ensuring robust convergence while maintaining physical accuracy across all layout configurations and stress conditions.

----------

# C Implementation

The BSIM4v7 layout-dependent effects, geometry calculations, and device setup are implemented through a coordinated system of C source files that map directly to the mathematical formulations. This implementation extends the foundational MOS1 architecture with nanometer-scale physical effects while maintaining the same SPICE integration patterns.

## 1. Core Data Structures for Layout-Dependent Effects

### 1.1 Extended Model Structure (`bsim4v7def.h`)

The BSIM4v7 model structure extends the basic MOS1 model with parameters for advanced layout effects:

```c
typedef struct sBSIM4v7model {
    /* Inherited MOS1 parameters */
    int BSIM4v7type;
    double BSIM4v7vth0;
    double BSIM4v7kp;
    double BSIM4v7gamma;
    double BSIM4v7phi;
    double BSIM4v7lambda;
    
    /* Layout-dependent effect parameters */
    double BSIM4v7sa;        /* STI stress coefficient SA */
    double BSIM4v7sb;        /* STI stress coefficient SB */
    double BSIM4v7sd;        /* STI stress coefficient SD */
    double BSIM4v7wpe;       /* Well Proximity Effect coefficient */
    double BSIM4v7fpitch;    /* Field pitch for stress calculation */
    
    /* Advanced geometry scaling */
    double BSIM4v7dl;        /* Length reduction DL */
    double BSIM4v7dw;        /* Width reduction DW */
    double BSIM4v7dwl;       /* Length reduction for narrow width */
    double BSIM4v7dww;       /* Width reduction for short channel */
    
    /* Stress effect coefficients */
    double BSIM4v7mustress;  /* Mobility stress coefficient */
    double BSIM4v7vthstress; /* Vth stress coefficient */
    double BSIM4v7stressexp; /* Stress exponential factor */
    
    /* Flags for parameter presence */
    int BSIM4v7saGiven, BSIM4v7sbGiven, BSIM4v7sdGiven;
    int BSIM4v7wpeGiven, BSIM4v7fpitchGiven;
    
    struct sBSIM4v7model *BSIM4v7nextModel;
    sBSIM4v7instance *BSIM4v7instances;
} BSIM4v7model;
```

### 1.2 Extended Instance Structure

The instance structure stores calculated geometry and stress effects:

```c
typedef struct sBSIM4v7instance {
    /* Basic geometry from netlist */
    double BSIM4v7l;        /* Drawn length L */
    double BSIM4v7w;        /* Drawn width W */
    double BSIM4v7ad;       /* Drain area AD */
    double BSIM4v7as;       /* Source area AS */
    
    /* Calculated effective dimensions */
    double BSIM4v7leff;     /* Effective channel length Leff */
    double BSIM4v7weff;     /* Effective channel width Weff */
    
    /* Stress effect calculations */
    double BSIM4v7strain;   /* Mechanical strain σ_sti */
    double BSIM4v7deltaw;   /* Width change due to stress ΔW */
    double BSIM4v7deltal;   /* Length change due to stress ΔL */
    
    /* Well proximity distances */
    double BSIM4v7sca;      /* Distance to well edge A */
    double BSIM4v7scb;      /* Distance to well edge B */
    double BSIM4v7scc;      /* Distance to well edge C */
    
    /* Modified parameters due to layout effects */
    double BSIM4v7vth0_eff; /* Effective Vth0 after WPE */
    double BSIM4v7u0_eff;   /* Effective mobility after stress */
    
    /* State variables for convergence */
    double BSIM4v7leff_old; /* Previous Leff for convergence test */
    double BSIM4v7weff_old; /* Previous Weff for convergence test */
    
    /* Sparse matrix pointers (inherited pattern) */
    double *BSIM4v7dDrainPtr;
    double *BSIM4v7dGatePtr;
    /* ... 16 total pointers as in MOS1 */
    
    struct sBSIM4v7instance *BSIM4v7nextInstance;
    BSIM4v7model *BSIM4v7modPtr;
} BSIM4v7instance;
```

## 2. Geometry Calculation Implementation (`b4v7geo.c`)

### 2.1 Effective Dimension Calculation

The `BSIM4v7calcGeometry()` function implements the mathematical formulations for effective dimensions with layout corrections:

```c
void BSIM4v7calcGeometry(BSIM4v7instance *inst, BSIM4v7model *model)
{
    /* Base effective dimensions */
    inst->BSIM4v7leff = inst->BSIM4v7l - 2 * model->BSIM4v7dl;
    inst->BSIM4v7weff = inst->BSIM4v7w - 2 * model->BSIM4v7dw;
    
    /* Narrow width correction */
    if (inst->BSIM4v7weff < model->BSIM4v7wmin) {
        inst->BSIM4v7leff += model->BSIM4v7dwl * 
                            (model->BSIM4v7wmin - inst->BSIM4v7weff);
    }
    
    /* Short channel correction */
    if (inst->BSIM4v7leff < model->BSIM4v7lmin) {
        inst->BSIM4v7weff += model->BSIM4v7dww * 
                            (model->BSIM4v7lmin - inst->BSIM4v7leff);
    }
    
    /* Ensure positive dimensions */
    if (inst->BSIM4v7leff <= 0.0) inst->BSIM4v7leff = 1e-12;
    if (inst->BSIM4v7weff <= 0.0) inst->BSIM4v7weff = 1e-12;
}
```

### 2.2 STI Stress Calculation

The Shallow Trench Isolation stress calculation maps directly to the exponential decay formulation:

```c
void BSIM4v7calcSTIStress(BSIM4v7instance *inst, BSIM4v7model *model)
{
    /* Calculate mechanical strain using exponential decay model */
    double L = inst->BSIM4v7l;
    double W = inst->BSIM4v7w;
    
    /* σ_sti = SA·exp(-SB·(L - SC)) + SD·exp(-SE·(W - SF)) */
    inst->BSIM4v7strain = model->BSIM4v7sa * 
                         exp(-model->BSIM4v7sb * (L - model->BSIM4v7sc)) +
                         model->BSIM4v7sd * 
                         exp(-model->BSIM4v7se * (W - model->BSIM4v7sf));
    
    /* Calculate dimension changes due to stress */
    inst->BSIM4v7deltal = inst->BSIM4v7strain * model->BSIM4v7poisson * L;
    inst->BSIM4v7deltaw = inst->BSIM4v7strain * model->BSIM4v7poisson * W;
    
    /* Apply stress corrections to effective dimensions */
    inst->BSIM4v7leff += inst->BSIM4v7deltal;
    inst->BSIM4v7weff += inst->BSIM4v7deltaw;
}
```

### 2.3 Well Proximity Effect Calculation

The WPE calculation implements the distance-dependent formulation:

```c
void BSIM4v7calcWPE(BSIM4v7instance *inst, BSIM4v7model *model)
{
    /* WPE_factor = WPEA/(sca + WPEB) + WPEC/(scb + WPED) + WPEE/(scc + WPEF) */
    double wpe_factor = 0.0;
    
    if (inst->BSIM4v7sca > 0.0) {
        wpe_factor += model->BSIM4v7wpea / 
                     (inst->BSIM4v7sca + model->BSIM4v7wpeb);
    }
    
    if (inst->BSIM4v7scb > 0.0) {
        wpe_factor += model->BSIM4v7wpec / 
                     (inst->BSIM4v7scb + model->BSIM4v7wped);
    }
    
    if (inst->BSIM4v7scc > 0.0) {
        wpe_factor += model->BSIM4v7wpee / 
                     (inst->BSIM4v7scc + model->BSIM4v7wpef);
    }
    
    /* Modify parameters based on WPE factor */
    inst->BSIM4v7vth0_eff = model->BSIM4v7vth0 * 
                           (1.0 + model->BSIM4v7wpevth * wpe_factor);
    inst->BSIM4v7u0_eff = model->BSIM4v7u0 * 
                         (1.0 + model->BSIM4v7wpeu0 * wpe_factor);
}
```

## 3. Parameter Setup and Binding (`b4v7set.c`)

### 3.1 Setup Function for Geometry Parameters

The `BSIM4v7setup()` function initializes all geometry-related parameters:

```c
int BSIM4v7setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    BSIM4v7model *model = (BSIM4v7model*)inModel;
    BSIM4v7instance *inst;
    
    for (; model; model = model->BSIM4v7nextModel) {
        /* Set default values for layout parameters if not given */
        if (!model->BSIM4v7saGiven) model->BSIM4v7sa = 0.0;
        if (!model->BSIM4v7sbGiven) model->BSIM4v7sb = 1.0;
        if (!model->BSIM4v7sdGiven) model->BSIM4v7sd = 0.0;
        if (!model->BSIM4v7wpeGiven) model->BSIM4v7wpe = 0.0;
        
        /* Calculate stress reference values */
        model->BSIM4v7stressref = 1.0 / (1.0 + model->BSIM4v7stressexp);
        
        for (inst = model->BSIM4v7instances; inst; inst = inst->BSIM4v7nextInstance) {
            /* Calculate effective geometry with all corrections */
            BSIM4v7calcGeometry(inst, model);
            
            /* Apply STI stress effects if enabled */
            if (model->BSIM4v7sa != 0.0 || model->BSIM4v7sd != 0.0) {
                BSIM4v7calcSTIStress(inst, model);
            }
            
            /* Apply Well Proximity Effect if enabled */
            if (model->BSIM4v7wpe != 0.0) {
                BSIM4v7calcWPE(inst, model);
            }
            
            /* Calculate beta with stress-corrected parameters */
            double u0_effective = (model->BSIM4v7wpe != 0.0) ? 
                                 inst->BSIM4v7u0_eff : model->BSIM4v7u0;
            
            /* Mobility change due to stress: Δμ/μ0 = MUSTRESS·σ_sti/(1 + STRESSREF·σ_sti) */
            if (inst->BSIM4v7strain != 0.0) {
                double mobility_factor = model->BSIM4v7mustress * inst->BSIM4v7strain /
                                       (1.0 + model->BSIM4v7stressref * inst->BSIM4v7strain);
                u0_effective *= (1.0 + mobility_factor);
            }
            
            /* Calculate oxide capacitance */
            model->BSIM4v7cox = 3.9 * 8.854e-12 / model->BSIM4v7tox;
            
            /* Calculate beta with all corrections */
            inst->BSIM4v7beta = (inst->BSIM4v7weff / inst->BSIM4v7leff) * 
                               u0_effective * model->BSIM4v7cox;
            
            /* Allocate sparse matrix pointers (inherits MOS1 pattern) */
            inst->BSIM4v7dDrainPtr = SMPmakeElt(matrix, 
                                               inst->BSIM4v7dNode, 
                                               inst->BSIM4v7dNode);
            /* ... allocate all 16 pointers as in MOS1 setup */
            
            /* Allocate state vector entries */
            inst->BSIM4v7leffState = (*states)++;
            inst->BSIM4v7weffState = (*states)++;
            
            /* Initialize geometry states */
            *(ckt->CKTrhsOld + inst->BSIM4v7leffState) = inst->BSIM4v7leff;
            *(ckt->CKTrhsOld + inst->BSIM4v7weffState) = inst->BSIM4v7weff;
        }
    }
    return OK;
}
```

## 4. Parameter Binding and Query Functions

### 4.1 Parameter Table for Layout Effects (`b4v7mpar.c`)

The parameter table extends the MOS1 table with BSIM4v7-specific layout parameters:

```c
static IFparm BSIM4v7mPTable[] = {
    /* Inherited MOS1 parameters */
    IOP("vto",    BSIM4v7_VTO,    IF_REAL, "Threshold voltage"),
    IOP("kp",     BSIM4v7_KP,     IF_REAL, "Transconductance parameter"),
    
    /* BSIM4v7 layout-dependent parameters */
    IOP("sa",     BSIM4v7_SA,     IF_REAL, "STI stress coefficient SA"),
    IOP("sb",     BSIM4v7_SB,     IF_REAL, "STI stress coefficient SB"),
    IOP("sd",     BSIM4v7_SD,     IF_REAL, "STI stress coefficient SD"),
    IOP("wpe",    BSIM4v7_WPE,    IF_REAL, "Well Proximity Effect coefficient"),
    IOP("fpitch", BSIM4v7_FPITCH, IF_REAL, "Field pitch for stress"),
    
    IOP("dl",     BSIM4v7_DL,     IF_REAL, "Length reduction"),
    IOP("dw",     BSIM4v7_DW,     IF_REAL, "Width reduction"),
    IOP("dwl",    BSIM4v7_DWL,    IF_REAL, "Length reduction for narrow width"),
    IOP("dww",    BSIM4v7_DWW,    IF_REAL, "Width reduction for short channel"),
    
    IOP("mustress", BSIM4v7_MUSTRESS, IF_REAL, "Mobility stress coefficient"),
    IOP("vthstress", BSIM4v7_VTHSTRESS, IF_REAL, "Vth stress coefficient"),
    IOP("stressexp", BSIM4v7_STRESSEXP, IF_REAL, "Stress exponential factor"),
    
    /* Output parameters for query */
    OP("leff",    BSIM4v7_LEFF,   IF_REAL, "Effective channel length"),
    OP("weff",    BSIM4v7_WEFF,   IF_REAL, "Effective channel width"),
    OP("strain",  BSIM4v7_STRAIN, IF_REAL, "Mechanical strain"),
};
```

### 4.2 Parameter Query Function (`b4v7ask.c`)

The `BSIM4v7ask()` function allows querying calculated geometry parameters:

```c
int BSIM4v7ask(CKTcircuit *ckt, GENinstance *inInst, int which, IFvalue *value)
{
    BSIM4v7instance *inst = (BSIM4v7instance*)inInst;
    
    switch (which) {
        case BSIM4v7_LEFF:
            value->rValue = inst->BSIM4v7leff;
            break;
            
        case BSIM4v7_WEFF:
            value->rValue = inst->BSIM4v7weff;
            break;
            
        case BSIM4v7_STRAIN:
            value->rValue = inst->BSIM4v7strain;
            break;
            
        case BSIM4v7_DELTAL:
            value->rValue = inst->BSIM4v7deltal;
            break;
            
        case BSIM4v7_DELTAW:
            value->rValue = inst->BSIM4v7deltaw;
            break;
            
        default:
            /* Delegate to base MOS1 ask function for inherited parameters */
            return MOS1ask(ckt, inInst, which, value);
    }
    
    return OK;
}
```

## 5. Convergence Testing for Geometry Parameters (`b4v7cvtest.c`)

### 5.1 Geometry Convergence Test

The convergence test extends to include geometry parameter changes:

```c
int BSIM4v7convTest(GENmodel *inModel, CKTcircuit *ckt)
{
    BSIM4v7model *model = (BSIM4v7model*)inModel;
    BSIM4v7instance *inst;
    
    /* First, call base MOS1 convergence test */
    int result = MOS1convTest(inModel, ckt);
    if (result != OK) return result;
    
    for (; model; model = model->BSIM4v7nextModel) {
        for (inst = model->BSIM4v7instances; inst; inst = inst->BSIM4v7nextInstance) {
            
            /* Check geometry parameter convergence */
            double leff_new = inst->BSIM4v7leff;
            double leff_old = inst->BSIM4v7leff_old;
            double weff_new = inst->BSIM4v7weff;
            double weff_old = inst->BSIM4v7weff_old;
            
            /* Geometry tolerance: relative change in dimensions */
            double leff_tol = ckt->CKTreltol * MAX(fabs(leff_new), fabs(leff_old)) + 
                             ckt->CKTgeomTol;
            double weff_tol = ckt->CKTreltol * MAX(fabs(weff_new), fabs(weff_old)) + 
                             ckt->CKTgeomTol;
            
            if (fabs(leff_new - leff_old) > leff_tol ||
                fabs(weff_new - weff_old) > weff_tol) {
                ckt->CKTnoncon++;
                return OK; /* Not converged yet */
            }
            
            /* Update old values for next iteration */
            inst->BSIM4v7leff_old = leff_new;
            inst->BSIM4v7weff_old = weff_new;
        }
    }
    
    return OK; /* All geometry parameters converged */
}
```

## 6. Temperature Scaling with Layout Effects (`b4v7temp.c`)

### 6.1 Temperature-Dependent Layout Effects

The temperature scaling function incorporates layout-dependent temperature coefficients:

```c
void BSIM4v7temp(BSIM4v7model *model, BSIM4v7instance *inst, double temp)
{
    /* Call base MOS1 temperature scaling */
    MOS1temp((MOS1model*)model, (MOS1instance*)inst, temp);
    
    /* Temperature scaling for stress coefficients */
    double T = temp + 273.15;
    double Tnom = model->BSIM4v7tnom + 273.15;
    double Tratio = T / Tnom;
    
    /* Stress coefficients may have temperature dependence */
    if (model->BSIM4v7sa != 0.0) {
        model->BSIM4v7sa *= pow(Tratio, model->BSIM4v7satc);
    }
    
    if (model->BSIM4v7sd != 0.0) {
        model->BSIM4v7sd *= pow(Tratio, model->BSIM4v7sdtc);
    }
    
    /* Recalculate geometry with temperature-adjusted parameters */
    BSIM4v7calcGeometry(inst, model);
    
    if (model->BSIM4v7sa != 0.0 || model->BSIM4v7sd != 0.0) {
        BSIM4v7calcSTIStress(inst, model);
    }
    
    /* Temperature affects thermal expansion, modifying stress */
    double alpha = model->BSIM4v7cte; /* Coefficient of thermal expansion */
    double deltaT = T - Tnom;
    
    inst->BSIM4v7leff *= (1.0 + alpha * deltaT);
    inst->BSIM4v7weff *= (1.0 + alpha * deltaT);
}
```

## 7. SPICE Device Integration

### 7.1 Device Structure Binding (`bsim4v7init.c`)

The BSIM4v7 device integrates with Ngspice using the same pattern as MOS1:

```c
SPICEdev BSIM4v7info = {
    .DEVpublic = {
        .name = "BSIM4v7",
        .description = "BSIM4 Version 7 with Layout-Dependent Effects",
        .terms = 4,
        .numNames = 2,
        .termNames = {"d", "g", "s", "b"},
        .numInstanceParms = 20,  /* Extended for layout parameters */
        .numModelParms = 40,     /* Extended for layout parameters */
    },
    .DEVmodParam = BSIM4v7mPTable,
    .DEVinstParam = BSIM4v7pTable,
    .DEVload = BSIM4v7load,
    .DEVsetup = BSIM4v7setup,      /* Extended setup for geometry */
    .DEVunsetup = BSIM4v7unsetup,
    .DEVtemperature = BSIM4v7temp, /* Extended temperature scaling */
    .DEVtrunc = BSIM