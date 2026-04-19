# BSIM4: Transient Control and Charge Conservation

_Generated 2026-04-12 13:15 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4/b4trunc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4/b4cvtest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4/b4getic.c`

# Chapter: BSIM4: Transient Control and Charge Conservation

## Technical Introduction

Within Ngspice's transient analysis framework for deep-submicron MOSFETs, the BSIM4 model implements sophisticated algorithms for time-step control, Newton-Raphson convergence monitoring, and charge-conserving numerical integration. The files `b4trunc.c`, `b4cvtest.c`, and `b4getic.c` form the computational core of this functionality. `b4trunc.c` implements a charge-based Local Truncation Error (LTE) estimator using Gear's second-order backward differentiation formula (BDF2), providing adaptive time-step control that accounts for BSIM4's advanced charge models including gate tunneling effects. `b4cvtest.c` performs dual voltage and charge convergence testing, essential for maintaining charge conservation with BSIM4's non-reciprocal capacitance matrix, while also checking gate leakage current convergence when tunneling models are active. `b4getic.c` handles initial condition specification and solution, supporting user-defined initial voltages while ensuring consistency with BSIM4's complex current-voltage relationships. Together, these routines enable numerically stable simulation of nanometer-scale MOSFETs with gate leakage, quantum effects, and temperature-dependent behavior during transient analysis.

---

## Mathematical Formulation

### 1. Local Truncation Error (LTE) Computation

The BSIM4 model uses a charge-based LTE estimation with Gear's method for adaptive time-step control:

**Gear's BDF2 Formula:**
```
LTE_q = |C₀·q(tₙ) + C₁·q(tₙ₋₁) + C₂·q(tₙ₋₂)|
```

For second-order Gear (BDF2) with coefficients C₀ = 1/3, C₁ = -4/3, C₂ = 1:
```
LTE = |(1/3)q(tₙ) - (4/3)q(tₙ₋₁) + q(tₙ₋₂)|
```

**Time-Step Adjustment:**
```
Δt_new = 0.9·Δt_old·[ε/(LTE_q + δ)]¹ᐟ³
```
where the error bound ε combines relative and absolute tolerances:
```
ε = RELTOL·|q| + ABSTOL
```
with default SPICE values: `RELTOL = 1e-3`, `ABSTOL = 1e-12`, and transient tolerance multiplier `TRTOL = 7.0`.

**BSIM4-Specific Extension:**
For gate tunneling models, additional LTE terms are computed for tunneling charges:
```
LTE_gbd = |(1/3)q_gbd(tₙ) - (4/3)q_gbd(tₙ₋₁) + q_gbd(tₙ₋₂)|
```
where `q_gbd` represents gate-to-drain tunneling charge.

### 2. Convergence Testing Criteria

BSIM4 implements dual convergence tests for both voltages and charges:

**Voltage Convergence:**
```
ΔV = |Vₖ - Vₖ₋₁| < ε_V = RELTOL·max(|Vₖ|, |Vₖ₋₁|) + VNTOL
```
Applied separately to `Vgs`, `Vds`, and `Vbs` with `VNTOL = 1e-6` (default).

**Charge Convergence:**
```
ΔQ = |Qₖ - Qₖ₋₁| < ε_Q = RELTOL·max(|Qₖ|, |Qₖ₋₁|) + CHGTOL
```
Applied to gate charge `Qg` with `CHGTOL = 1e-14` (default). This is critical for BSIM4's charge conservation.

**Gate Leakage Current Convergence (BSIM4-specific):**
```
ΔI_gc = |I_gcₖ - I_gcₖ₋₁| < ε_I = RELTOL·max(|I_gcₖ|, |I_gcₖ₋₁|) + CURTOL
```
where `I_gc` is gate-channel tunneling current, checked when `igcMod ≠ 0`.

### 3. Initial Condition Formulation

The initial condition problem solves:
```
f(Vgs, Vds, Vbs) = Ids(Vgs, Vds, Vbs) - I_specified = 0
```

**User-Specified Initial Conditions:**
If provided, these take precedence:
```
Vds(t₀) = IC_VDS (if given), else 0
Vgs(t₀) = IC_VGS (if given), else Vth with appropriate polarity
Vbs(t₀) = IC_VBS (if given), else 0
```

**State Vector Initialization:**
For charge conservation, all history states are initialized identically:
```
q(t₀) = q(t₋₁) = q(t₋₂) = Q_calculated(Vgs(t₀), Vds(t₀), Vbs(t₀))
```
This ensures zero initial LTE.

### 4. Numerical Integration of Advanced Charge Model

BSIM4 uses a non-reciprocal capacitance matrix with trapezoidal integration:

**Charge Conservation Equations:**
```
Q_g = ∫ C_gg dV_g + ∫ C_gd dV_d + ∫ C_gs dV_s + ∫ C_gb dV_b
Q_d = ∫ C_dg dV_g + ∫ C_dd dV_d + ∫ C_ds dV_s + ∫ C_db dV_b
Q_s = ∫ C_sg dV_g + ∫ C_sd dV_d + ∫ C_ss dV_s + ∫ C_sb dV_b
Q_b = ∫ C_bg dV_g + ∫ C_bd dV_d + ∫ C_bs dV_s + ∫ C_bb dV_b
```

**Trapezoidal Integration Rule:**
```
i_cap(tₙ) = (2/Δt)[Q(tₙ) - Q(tₙ₋₁)] - i_cap(tₙ₋₁)
```

**Companion Model for Capacitances:**
```
G_eq = (2/Δt)·C
I_eq = (2/Δt)·C·V(tₙ₋₁) + i_cap(tₙ₋₁)
```
where `C` is the 4×4 capacitance matrix.

### 5. BSIM4-Specific Enhancements

**Temperature-Dependent Tolerances:**
```
ε_V(T) = ε_V(300K)·[1 + α_T·(T - 300)]
ε_Q(T) = ε_Q(300K)·[1 + β_T·(T - 300)]
```
where `α_T` and `β_T` are temperature coefficients from BSIM4 parameters.

**Quantum Charge Correction:**
When quantum models are active (`qmMod ≠ 0`):
```
Q_inv_quantum = Q_inv_classical·qfactor
C_quantum = C_classical·qfactor
```
with `qfactor` typically 0.7-0.8 for inversion layer quantization.

---

## C Implementation

### 1. Core Data Structures for State Management

The BSIM4 model's transient behavior is governed by two primary data structures defined in `bsim4def.h`: `sB4model` and `sB4instance`. These structs store all parameters, state variables, and matrix pointers required for time-domain simulation.

#### 1.1 The `B4instance` Structure

The `B4instance` struct contains all time-varying state information for a single MOSFET device:

```c
typedef struct sB4instance {
    /* Terminal voltage states */
    double B4vds;       /* Drain-source voltage at current iteration */
    double B4vgs;       /* Gate-source voltage */
    double B4vbs;       /* Bulk-source voltage */
    double B4vds_old;   /* Previous iteration values for convergence test */
    double B4vgs_old;
    double B4vbs_old;
    
    /* Terminal charge states */
    double B4qg;        /* Gate charge */
    double B4qd;        /* Drain charge */
    double B4qs;        /* Source charge */
    double B4qb;        /* Bulk charge */
    double B4qg_old;    /* Previous charges for convergence test */
    
    /* State vector indices - critical for LTE calculation */
    int B4qGate;        /* Index for gate charge in CKTstate arrays */
    int B4qDrain;       /* Index for drain charge */
    int B4qSource;      /* Index for source charge */
    int B4qBulk;        /* Index for bulk charge */
    int B4qGbd;         /* Index for gate-drain tunneling charge (BSIM4 specific) */
    int B4qGbs;         /* Index for gate-source tunneling charge */
    
    /* Initial condition control */
    int B4icVDSgiven;   /* Flag for user-specified VDS initial condition */
    double B4icVDS;     /* User-specified initial VDS value */
    int B4icVGSgiven;
    double B4icVGS;
    int B4icVBSgiven;
    double B4icVBS;
    
    /* Integration history for trapezoidal rule */
    double B4ig_cap_old;  /* Previous capacitive gate current */
    double B4id_cap_old;  /* Previous capacitive drain current */
    double B4is_cap_old;  /* Previous capacitive source current */
    double B4ib_cap_old;  /* Previous capacitive bulk current */
    
    /* Gate leakage currents (BSIM4 nanometer effects) */
    double B4igc;         /* Gate-channel tunneling current */
    double B4igc_old;     /* Previous gate leakage for convergence */
    
    /* Non-reciprocal capacitance matrix elements */
    double B4cgg, B4cgd, B4cgs, B4cgb;
    double B4cdg, B4cdd, B4cds, B4cdb;
    double B4csg, B4csd, B4css, B4csb;
    double B4cbg, B4cbd, B4cbs, B4cbb;
    
    struct sB4instance *B4nextInstance;  /* Linked list pointer */
} B4instance;
```

#### 1.2 The `B4model` Structure

The `B4model` struct contains model-level parameters and flags that control transient behavior:

```c
typedef struct sB4model {
    /* Physical parameters affecting transient response */
    double B4vth0;       /* Threshold voltage - affects initial conditions */
    double B4u0;         /* Low-field mobility - affects current calculation */
    double B4vsat;       /* Saturation velocity */
    
    /* Gate leakage model control */
    int B4igcMod;        /* Gate current model selector (0=off, 1=on) */
    int B4igbMod;        /* Gate-bulk tunneling model selector */
    double B4aigbacc;    /* Gate tunneling parameters */
    double B4bigbacc;
    double B4cigbacc;
    
    /* Temperature parameters for temperature-dependent tolerances */
    double B4tnom;       /* Nominal temperature */
    double B4ute;        /* Temperature exponent for mobility */
    double B4kt1;        /* Temperature coefficient for Vth */
    
    struct sB4model *B4nextModel;  /* Linked list pointer */
    B4instance *B4instances;       /* Pointer to instance list */
} B4model;
```

#### 1.3 Circuit State Management Structures

The `CKTcircuit` structure from Ngspice's core provides the framework for state management:

```c
/* Key members for transient control */
typedef struct sCKTcircuit {
    double *CKTstate0;    /* State vector at time tₙ (current) */
    double *CKTstate1;    /* State vector at time tₙ₋₁ (previous) */
    double *CKTstate2;    /* State vector at time tₙ₋₂ (two steps back) */
    double CKTdelta;      /* Current time step Δt */
    double *CKTrhs;       /* Right-hand side vector (nodal currents) */
    
    /* Convergence tolerances */
    double CKTreltol;     /* Relative tolerance (typically 1e-3) */
    double CKTabstol;     /* Absolute tolerance for currents (typically 1e-12) */
    double CKTvoltTol;    /* Voltage tolerance (typically 1e-6) */
    double CKTchargeTol;  /* Charge tolerance (typically 1e-14) */
    double CKTtrtol;      /* Transient tolerance multiplier (typically 7.0) */
    double CKTcurTol;     /* Current tolerance for leakage currents */
} CKTcircuit;
```

### 2. Local Truncation Error Computation (`b4trunc.c`)

The `B4trunc()` function implements the mathematical LTE calculation using Gear's second-order backward differentiation formula (BDF2).

#### 2.1 Mathematical-to-Code Mapping

The mathematical formulation for LTE:
```
LTE = |(1/3)q(tₙ) - (4/3)q(tₙ₋₁) + q(tₙ₋₂)|
```

Maps directly to the C implementation:

```c
int B4trunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep)
{
    B4model *model = (B4model *)inModel;
    B4instance *here;
    
    /* State vector access - maps to q(tₙ), q(tₙ₋₁), q(tₙ₋₂) */
    double *state0 = ckt->CKTstate0;  /* q(tₙ) */
    double *state1 = ckt->CKTstate1;  /* q(tₙ₋₁) */
    double *state2 = ckt->CKTstate2;  /* q(tₙ₋₂) */
    
    for (; model != NULL; model = model->B4nextModel) {
        for (here = model->B4instances; here != NULL; 
             here = here->B4nextInstance) {
            
            /* Get charge states using pre-computed indices */
            double qstate0 = *(state0 + here->B4qGate);  /* q(tₙ) */
            double qstate1 = *(state1 + here->B4qGate);  /* q(tₙ₋₁) */
            double qstate2 = *(state2 + here->B4qGate);  /* q(tₙ₋₂) */
            
            /* Compute differences approximating derivatives */
            double diff1 = qstate0 - qstate1;      /* First difference */
            double diff2 = qstate1 - qstate2;      /* First difference at tₙ₋₁ */
            double diff3 = diff1 - diff2;          /* Second difference */
            
            /* LTE calculation using Gear coefficients */
            double delta = ckt->CKTdelta;
            /* chargeTol = trtol * |q̈| ≈ trtol * |diff3|/Δt² */
            double chargeTol = ckt->CKTtrtol * fabs(diff3) / (delta * delta);
            
            /* Error bound: ε = reltol * |q| + abstol */
            double qmax = MAX(fabs(qstate0), fabs(qstate1));
            double allowedError = ckt->CKTreltol * qmax + ckt->CKTabstol;
            
            /* Time step reduction with cubic root scaling */
            if (chargeTol > allowedError) {
                /* Δt_new = 0.9 * Δt_old * [ε/(LTE + δ)]^(1/3) */
                double newTimeStep = 0.9 * delta * 
                    pow(allowedError / (chargeTol + 1e-30), 1.0/3.0);
                
                if (newTimeStep < *timeStep) {
                    *timeStep = newTimeStep;
                }
            }
            
            /* BSIM4-specific: Check gate leakage charge states */
            if (model->B4igcMod) {
                /* Additional LTE check for tunneling charges */
                double qgstate0 = *(state0 + here->B4qGbd);
                double qgstate1 = *(state1 + here->B4qGbd);
                double qgstate2 = *(state2 + here->B4qGbd);
                /* Same LTE calculation applied to gate leakage charges */
            }
        }
    }
    return OK;
}
```

#### 2.2 Key Implementation Details

1. **State Vector Access**: The `B4qGate`, `B4qDrain`, etc., indices provide direct access to charge values in the circuit's state history arrays.

2. **Second Difference Calculation**: The code computes `diff3 = (q₀ - q₁) - (q₁ - q₂) = q₀ - 2q₁ + q₂`, which approximates the second derivative `q̈Δt²`.

3. **Cubic Root Scaling**: The time step reduction uses `pow(error_ratio, 1/3)` because LTE for BDF2 is `O(Δt³)`.

4. **BSIM4-Specific Extensions**: When gate leakage models are active (`B4igcMod != 0`), additional LTE checks are performed on tunneling charge states.

### 3. Convergence Testing (`b4cvtest.c`)

The `B4convTest()` function implements the dual voltage and charge convergence criteria required for BSIM4's charge-conserving model.

#### 3.1 Voltage Convergence Implementation

Mathematical criterion:
```
ΔV = |Vₖ - Vₖ₋₁| < ε_V = RELTOL·max(|Vₖ|, |Vₖ₋₁|) + VNTOL
```

C implementation:

```c
int B4convTest(GENmodel *inModel, CKTcircuit *ckt)
{
    B4model *model;
    B4instance *here;
    
    /* Extract tolerances from circuit */
    double vntol = ckt->CKTvoltTol;
    double chgtol = ckt->CKTchargeTol;
    double reltol = ckt->CKTreltol;
    
    for (model = (B4model *)inModel; model != NULL; 
         model = model->B4nextModel) {
        
        for (here = model->B4instances; here != NULL; 
             here = here->B4nextInstance) {
            
            /* Voltage convergence test */
            double delVgs = fabs(here->B4vgs - here->B4vgs_old);
            double delVds = fabs(here->B4vds - here->B4vds_old);
            double delVbs = fabs(here->B4vbs - here->B4vbs_old);
            
            /* Compute maximum values for relative tolerance */
            double vgs_max = MAX(fabs(here->B4vgs), fabs(here->B4vgs_old));
            double tolVgs = reltol * vgs_max + vntol;
            
            if (delVgs > tolVgs) {
                ckt->CKTnoncon++;  /* Increment non-convergence counter */
                return E_NOTCONVERGED;
            }
            
            /* Repeat for Vds and Vbs */
            
            /* Charge convergence test - CRITICAL for BSIM4 */
            double delQg = fabs(here->B4qg - here->B4qg_old);
            double qg_max = MAX(fabs(here->B4qg), fabs(here->B4qg_old));
            double tolQg = reltol * qg_max + chgtol;
            
            if (delQg > tolQg) {
                ckt->CKTnoncon++;
                return E_NOTCONVERGED;
            }
            
            /* BSIM4-specific: Gate leakage current convergence */
            if (model->B4igcMod) {
                double delIgc = fabs(here->B4igc - here->B4igc_old);
                double igc_max = MAX(fabs(here->B4igc), fabs(here->B4igc_old));
                double tolIgc = reltol * igc_max + ckt->CKTcurTol;
                
                if (delIgc > tolIgc) {
                    ckt->CKTnoncon++;
                    return E_NOTCONVERGED;
                }
            }
            
            /* Update old values for next iteration */
            here->B4vgs_old = here->B4vgs;
            here->B4vds_old = here->B4vds;
            here->B4vbs_old = here->B4vbs;
            here->B4qg_old = here->B4qg;
            
            if (model->B4igcMod) {
                here->B4igc_old = here->B4igc;
            }
        }
    }
    
    return OK;
}
```

#### 3.2 BSIM4-Specific Convergence Enhancements

1. **Dual Convergence Test**: Unlike simpler models, BSIM4 tests both voltage AND charge convergence, essential for charge conservation.

2. **Gate Leakage Monitoring**: When `B4igcMod` is active, the gate tunneling current `B4igc` must also converge, using current tolerance `CKTcurTol`.

3. **State Preservation**: The `_old` variables (`B4vgs_old`, `B4qg_old`, etc.) preserve the previous Newton iteration values for difference calculation.

### 4. Initial Condition Handling (`b4getic.c`)

The `B4getic()` function solves the initial condition problem for BSIM4 devices.

#### 4.1 Mathematical Problem Mapping

The initial condition problem:
```
f(Vgs, Vds, Vbs) = Ids - I_specified = 0
```

is implemented with user override capability:

```c
int B4getic(GENmodel *inModel, CKTcircuit *ckt)
{
    B4model *model;
    B4instance *here;
    
    for (model = (B4model *)inModel; model != NULL; 
         model = model->B4nextModel) {
        
        for (here = model->B4instances; here != NULL; 
             here = here->B4nextInstance) {
            
            /* User-specified initial conditions take precedence */
            double vds_init, vgs_init, vbs_init;
            
            if (here->B4icVDSgiven) {
                vds_init = here->B4icVDS;  /* User specified */
            } else {
                vds_init = 0.0;  /* Default: device off */
            }
            
            if (here->B4icVGSgiven) {
                vgs_init = here->B4icVGS;
            } else {
                /* Default: threshold voltage with correct polarity */
                vgs_init = (model->B4type > 0) ? 
                          model->B4vth0 : -model->B4vth0;
            }
            
            /* Apply initial voltages to device instance */
            here->B4vds = vds_init;
            here->B4vgs = vgs_init;
            here->B4vbs = vbs_init;
            
            /* Compute initial charges based on voltages */
            B4calcCapacitances(here, model, vgs_init, vds_init, vbs_init);
            
            /* Initialize state vectors for charge history */
            int qstate = here->B4qGate;
            *(ckt->CKTstate0 + qstate) = here->B4qg;  /* q(t₀) */
            *(ckt->CKTstate1 + qstate) = here->B4qg;  /* q(t₋₁) - same for startup */
            *(ckt->CKTstate2 + qstate) = here->B4qg;  /* q(t₋₂) - same for startup */
            
            /* Initialize gate leakage states if model active */
            if (model->B4igcMod) {
                int qgstate = here->B4qGbd;
                *(ckt->CKTstate0 + qgstate) = 0.0;  /* Zero initial tunneling charge */
                *(ckt->CKTstate1 + qgstate) = 0.0;
                *(ckt->CKTstate2 + qgstate) = 0.0;
            }
            
            /* Compute initial drain current and stamp into RHS */
            double ids = B4calcIds(here, model, vgs_init, vds_init, vbs_init);
            ckt->CKTrhs[here->B4dNode] -= ids;  /* Current leaving drain */
            ckt->CKTrhs[here->B4sNode] += ids;  /* Current entering source */
            
            /* Initialize history variables for convergence testing */
            here->B4vds_old = here->B4vds;
            here->B4vgs_old = here->B4vgs;
            here->B4vbs_old = here->B4vbs;
            here->B4qg_old = here->B4qg;
        }
    }
    
    return OK;
}
```

#### 4.2 Initialization Strategy

1. **User Override**: The `B4icVDSgiven`, `B4icVGSgiven`, `B4icVBSgiven` flags and corresponding values allow users to specify exact initial conditions.

2. **Default Strategy**: Without user specification, defaults to `Vds = 0`, `Vgs = Vth` (with correct polarity for NMOS/PMOS), `Vbs = 0`.

3. **State Vector Initialization**: All three state vectors (`CKTstate0`, `CKTstate1`, `CKTstate2`) are initialized with the same charge values, ensuring zero initial LTE.

4. **RHS Initialization**: The initial drain current is computed and stamped into the right-hand side vector, providing the Newton solver with a good starting point.

### 5. Numerical Integration of Advanced Charge Model

The BSIM4 model implements a non-reciprocal capacitance matrix integrated using the trapezoidal rule.

#### 5.1 Mathematical Formulation to Code Mapping

The charge conservation equations:
```
Q_g = ∫ C_gg dV_g + ∫ C_gd dV_d + ∫ C_gs dV_s + ∫ C_gb dV_b
```

and trapezoidal integration:
```
i_cap(tₙ) = (2/Δt)[Q(tₙ) - Q(tₙ₋₁)] - i_cap(tₙ₋₁)
```

are implemented in the load function:

```c
void B4loadCapacitances(B4instance *here, B4model *model, 
                       CKTcircuit *ckt, double *gequiv, double *cequiv)
{
    /* Get current voltages */
    double vgs = here->B4vgs;
    double vds = here->B4vds;
    double vbs = here->B4vbs;
    double delta = ckt->CKTdelta;
    
    /* Compute terminal charges using BSIM4's advanced model */
    B4calcTerminalCharges(here, model, vgs, vds, vbs,
                         &here->B4qg, &here->B4qd, 
                         &here->B4qs, &here->B4qb);
    
    /* Retrieve previous charges from state vector */
    double qg_old = *(ckt->CKTstate0 + here->B4qGate);
    double qd_old = *(ckt->CKTstate0 + here->B4qDrain);
    double qs_old = *(ckt->CKTstate0 + here->B4qSource);
    double qb_old = *(ckt->CKTstate0 + here->B4qBulk);
    
    /* Trapezoidal integration for capacitive currents */
    /* i_cap(tₙ) = (2/Δt)[Q(tₙ) - Q(tₙ₋₁)] - i_cap(tₙ₋₁) */
    double ig_cap = (2.0/delta) * (here->B4qg - qg_old) - here->B4ig_cap_old;
    double id_cap = (2.0/delta) * (here->B4qd - qd_old) - here->B4id_cap_old;
    double is_cap = (2.0/delta) * (here->B4qs - qs_old) - here->B4is_cap_old;
    double ib_cap = (2.0/delta) * (here->B4qb - qb_old) - here->B4ib_cap_old;
    
    /* Store currents for next time step */
    here->B4ig_cap_old = ig_cap;
    here->B4id_cap_old = id_cap;
    here->B4is_cap_old = is_cap;
    here->B4ib_cap_old = ib_cap;
    
    /* Add gate leakage currents if model active */
    if (model->B4igcMod) {
        /* Gate tunneling current adds to capacitive current */
        ig_cap += B4calcGateCurrent(here, model, vgs, vds, vbs);
    }
    
    /* Stamp companion model conductances into matrix */
    /* G_eq = (2/Δt)·C + ∂i/∂v */
    gequiv[here->B4gNode] += (2.0/delta) * here->B4cgg;  /* G_gg */
    gequiv[here->B4dNode] += (2.0/delta) * here->B4cdd;  /* G_dd */
    /* ... stamp all 16 capacitance matrix elements ... */
    
    /* Stamp capacitive currents into RHS vector */
    ckt->CKTrhs[here->B4gNode] -= ig_cap;
    ckt->CKTrhs[here->B4dNode] -= id_cap;
    ckt->CKTrhs[here->B4sNode] -= is_cap;
    ckt->CKTrhs[here->B4bNode] -= ib_cap;
}
```

#### 5.2 BSIM4-Specific Implementation Details

1. **Non-Reciprocal Capacitance**: The full 4×4 matrix (`B4cgg`, `B4cgd`, ..., `B4cbb`) captures charge conservation for asymmetric device behavior.

2. **Companion Model**: The trapezoidal rule creates equivalent conductances `G_eq = (2/Δt)·C` that are stamped into the circuit matrix alongside the device conductances.

3. **History Preservation**: The `_cap_old` variables (`B4ig_cap_old`, etc.) store the previous capacitive currents required by the trapezoidal recurrence relation.

4. **Gate Leakage Integration**: When `B4igcMod` is active, the gate tunneling current is computed separately and added to the capacitive current.

### 6. SPICE Integration and Matrix Stamping

The BSIM4 transient implementation integrates with Ngspice's matrix solver through carefully managed sparse matrix pointers.

#### 6.1 Matrix Pointer Allocation

During setup (`B4setup`), pointers are allocated for the 4×4 conductance matrix plus internal nodes:

```c
/* In B4setup() function */
int B4setup(GENmodel *inModel, CKTcircuit *ckt)
{
    B4model *model = (B4model *)inModel;
    B4instance *here;
    
    for (; model != NULL; model = model->B4nextModel) {
        for (here = model->B4instances; here != NULL; 
             here = here->B4nextInstance) {
            
            /* Allocate matrix pointers for 4-terminal device */
            SMPmakeElt(ckt, here->B4dNode, here->B4dNode, 
                      &here->B4dDrainPtr);      /* G_dd */
            SMPmakeElt(ckt, here->B4dNode, here->B4gNode, 
                      &here->B4dGatePtr);       /* G_dg */
            SMPmakeElt(ckt, here->B4dNode, here->B4sNode, 
                      &here->B4dSourcePtr);     /* G_ds */
            SMPmakeElt(ckt, here->B4dNode, here->B4bNode, 
                      &here->B4dBulkPtr);       /* G_db */
            
            /* Repeat for all 16 matrix positions */
            
            /* Internal nodes for parasitic resistances */
            SMPmakeElt(ckt, here->B4dNodePrime, here->B4dNodePrime, 
                      &here->B4dpDpPtr);        /* G_dpdp */
            SMPmakeElt(ckt, here->B4sNodePrime, here->B4sNodePrime, 
                      &here->B4spSpPtr);        /* G_spsp */
            
            /* Allocate state vector indices for charges */
            here->B4qGate = ckt->CKTnumStates++;
            here->B4qDrain = ckt->CKTnumStates++;
            here->B4qSource = ckt->CKTnumStates++;
            here->B4qBulk = ckt->CKTnumStates++;
            
            /* BSIM4-specific: tunneling charge states */
            if (model->B4igcMod) {
                here->B4qGbd = ckt->CKTnumStates++;
                here->B4qGbs = ckt->CKTnumStates++;
            }
        }
    }
    
    return OK;
}
```

#### 6.2 Transient Matrix Stamping Pattern

During the load phase, the matrix is stamped with both conductive and capacitive terms:

```c
/* In B4load() function - simplified version */
int B4load(GENmodel *inModel, CKTcircuit *ckt)
{
    B4model *model = (B4model *)inModel;
    B4instance *here;
    
    for (; model != NULL; model = model->B4nextModel) {
        for (here = model->B4instances; here != NULL; 
             here = here->B4nextInstance) {
            
            /* Compute conductances (gm, gds, gmbs) */
            B4evalDerivatives(here, model, ckt);
            
            /* Stamp conductive terms */
            *(here->B4dDrainPtr) += here->B4gds + here->B4gd;  /* G_dd */
            *(here->B4dGatePtr) += here->B4gm;                 /* G_dg */
            *(here->B4dSourcePtr) -= here->B4gds;              /* G_ds */
            *(here->B4dBulkPtr) += here->B4gmbs;               /* G_db */
            
            /* Stamp capacitive terms from trapezoidal rule */
            double delta = ckt->CKTdelta;
            *(here->B4dDrainPtr) += (2.0/delta) * here->B4cdd;  /* (2/Δt)C_dd */
            *(here->B4dGatePtr) += (2.0/delta) * here->B4cdg;   /* (2/Δt)C_dg */
            /* ... stamp all capacitive terms ... */
            
            /* Stamp current contributions to RHS */
            ckt->CKTrhs[here->B4dNode] -= here->B4ids;  /* Drain current */
            ckt->CKTrhs[here->B4sNode] += here->B4ids;  /* Source current */
            
            /* Add capacitive currents from trapezoidal integration */
            ckt->CKTrhs[here->B4dNode] -= here->B4id_cap;
            ckt->CKTrhs[here->B4sNode] -= here->B4is_cap;
            ckt->CKTrhs[here->B4gNode] -= here->B4ig_cap;
            ckt->CKTrhs[here->B4bNode] -= here->B4ib_cap;
        }
    }
    
    return OK;
}
```

### 7. BSIM4-Specific Transient Enhancements

#### 7.1 Gate Leakage Charge Tracking

BSIM4 models gate tunneling by tracking separate charge states:

```c
/* Special handling for gate leakage in LTE calculation */
if (model->B4igcMod) {
    /* Gate-drain tunneling charge */
    double qgbd0 = *(ckt->CKTstate0 + here->B4qGbd);
    double qgbd1 = *(ckt->CKTstate1 + here->B4qGbd);
    double qgbd2 = *(ckt->CKTstate2 + here->B4qGbd);
    
    /* LTE for tunneling charge - uses same Gear formula */
    double diff_gbd1 = qgbd0 - qgbd1;
    double diff_gbd2 = qgbd1 - qgbd2;
    double diff_gbd3 = diff_gbd1 - diff_gbd2;
    
    double lte_gbd = ckt->CKTtrtol * fabs(diff_g