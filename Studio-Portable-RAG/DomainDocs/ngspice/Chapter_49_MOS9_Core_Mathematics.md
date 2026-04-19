# MOSFET Level 9 (Philips): Core Mathematics and Smooth Transitions

_Generated 2026-04-12 07:39 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/include/ngspice/devdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos9/mos9load.c`

# MOSFET Level 9 (Philips): Core Mathematics and Smooth Transitions

## Technical Introduction

Within the Ngspice EDA codebase, the MOS9 (Level 9) Philips MOSFET model represents a sophisticated implementation of the NXP semiconductor physics with particular emphasis on mathematical smoothness and numerical robustness. The model's implementation is distributed across several key C files that work in concert to deliver accurate circuit simulation with guaranteed convergence properties.

**`devdefs.h`** serves as the architectural foundation, defining the core data structures `sMOS9model` and `sMOS9instance` that encapsulate all mathematical parameters, operating point variables, and SPICE integration elements. This header file establishes the complete interface between the MOS9 device model and the Ngspice simulation engine, mapping every physical parameter to its corresponding C structure field.

**`mos9par.c`** implements the parameter parsing and validation system, translating SPICE netlist parameters into the internal model representation. This file handles the binding of user-supplied parameters (VTO, KP, GAMMA, etc.) to the model structure, applying default values where necessary and validating parameter ranges to ensure physical plausibility before simulation begins.

**`mos9temp.c`** contains the comprehensive temperature scaling algorithms that adjust all physical parameters based on operating temperature. This implementation includes the bandgap energy temperature dependence, mobility degradation with temperature, junction potential scaling, and capacitance temperature coefficients—all critical for accurate simulation across temperature ranges.

**`mos9load.c`** is the computational heart of the MOS9 model, implementing the core device equations with sophisticated smoothing functions. This file calculates the drain current using the Philips formulation with hyperbolic tangent smoothing for region transitions, computes all partial derivatives for the Newton-Raphson Jacobian matrix, and stamps the 7×7 conductance matrix into the SPICE circuit system. The implementation emphasizes C¹ continuity through careful mathematical smoothing at all operating region boundaries.

Together, these files implement a physically accurate MOSFET model that maintains numerical stability through extensive smoothing functions, ensuring robust convergence in SPICE simulations while preserving the accuracy of the Philips semiconductor physics.

---

## Mathematical Formulation

The MOS9 (Level 9) model in Ngspice implements the Philips (NXP) MOSFET formulation with comprehensive physical effects and smooth mathematical transitions for robust SPICE simulation. The model's mathematical structure is designed to provide physical accuracy while ensuring numerical stability through continuous derivatives across all operating regions.

### 1. Threshold Voltage with Advanced Physical Effects

The MOS9 threshold voltage calculation incorporates multiple physical effects with smooth blending:

**Core Threshold Equation:**
```
V_th = VTO + γ·[√(φ - V_bs) - √φ] + η·V_ds + ΔV_w
```

**Component Breakdown:**
- **VTO**: Zero-bias threshold voltage (`model->MOS9vto`)
- **Body Effect**: `γ·[√(φ - V_bs) - √φ]` where `γ = model->MOS9gamma`, `φ = model->MOS9phi`
- **DIBL (Drain-Induced Barrier Lowering)**: `η·V_ds` where `η = model->MOS9eta`
- **Narrow Width Effect**: `ΔV_w = δ·(π·ε_si/(4·C_ox·W_eff))·(φ - V_bs)` where `δ = model->MOS9delta`

**SPICE Implementation Smoothing:**
```c
/* Continuous square root for body effect */
if (φ - V_bs < 0) {
    sqrt_term = sqrt(φ) * (1.0 - 0.5*(V_bs/φ) - 0.125*pow(V_bs/φ, 2));
} else {
    sqrt_term = sqrt(φ - V_bs);
}
```

### 2. Mobility Degradation with Multiple Field Dependencies

The effective mobility model captures vertical and lateral field effects:

**Mobility Degradation Equation:**
```
μ_eff = μ₀ / [1 + θ·(V_gs - V_th) + μ₁·V_ds/L_eff + μ₂/(V_gs - V_th + μ₀_param)]
```

**Parameter Mapping:**
- `μ₀` = `model->MOS9u0` (low-field mobility)
- `θ` = `model->MOS9theta` (vertical field mobility reduction)
- `μ₁` = `model->MOS9mu1` (lateral field coefficient)
- `μ₂` = `model->MOS9mu2` (saturation velocity coefficient)
- `μ₀_param` = `model->MOS9mu0` (mobility reference parameter)

**SPICE Numerical Protection:**
```c
Vgst = V_gs - V_th;
if (fabs(Vgst) < 1e-10) {
    Vgst = (Vgst >= 0) ? 1e-10 : -1e-10;
}
mobility_denom = 1.0 + model->MOS9theta * Vgst + 
                 model->MOS9mu1 * V_ds / L_eff + 
                 model->MOS9mu2 / (Vgst + model->MOS9mu0);
μ_eff = model->MOS9u0 / MAX(mobility_denom, 1e-3);
```

### 3. Drain Current with Smooth Region Transitions

The drain current formulation uses hyperbolic smoothing functions for C¹ continuity:

**Transconductance Parameter:**
```
β = (W_eff/L_eff) · KP · (μ_eff/μ₀)
where KP = μ₀ · C_ox = model->MOS9kp
```

**Critical Field and Saturation Voltage:**
```
E_c = 2 · V_MAX / μ_eff
V_dsat = (V_gs - V_th) / (1 + (V_gs - V_th)/(E_c·L_eff))
```

**Triode Region Current (V_ds ≤ V_dsat):**
```
I_ds_tri = β · [(V_gs - V_th - 0.5·α·V_ds) · V_ds]
where α = 1 + γ/(2√(φ - V_bs))
```

**Saturation Region Current (V_ds > V_dsat):**
```
I_ds_sat = β · (V_gs - V_th)² · (1 + κ·V_ds) / [2·(1 + (V_gs - V_th)/(E_c·L_eff))]
where κ = model->MOS9kappa
```

**Hyperbolic Smoothing Function:**
```c
/* Smooth transition parameter */
δ = 0.01 * V_dsat;

/* Effective V_ds with smoothing */
if (V_ds < V_dsat) {
    V_ds_eff = V_dsat - 0.5 * (sqrt(pow(V_ds - V_dsat, 2) + δ*δ) + V_ds - V_dsat);
} else {
    V_ds_eff = V_ds;
}

/* Blend function using tanh for smooth transition */
λ = 0.5 * (1.0 + tanh(10.0 * (V_ds - V_dsat) / V_dsat));

/* Final blended current */
I_ds = (1.0 - λ) * I_ds_tri(V_ds_eff) + λ * I_ds_sat;
```

### 4. Channel Length Modulation with Logarithmic Form

**CLM Equation:**
```
ΔL = λ₁ · ln(1 + V_ds - V_dsat) + λ₂ · (V_ds - V_dsat)
where λ₁ = model->MOS9lambda1, λ₂ = model->MOS9lambda2
```

**SPICE Implementation with Protection:**
```c
V_diff = V_ds - V_dsat;
if (V_diff > 0) {
    /* Logarithmic term with protection */
    if (V_diff < 1e-6) {
        log_term = V_diff - 0.5 * V_diff * V_diff;  /* Series expansion */
    } else {
        log_term = log(1.0 + V_diff);
    }
    deltaL = model->MOS9lambda1 * log_term + model->MOS9lambda2 * V_diff;
    I_ds *= (1.0 + deltaL / L_eff);
}
```

### 5. Subthreshold Conduction with Exponential Smoothing

**Subthreshold Slope Factor:**
```
n = 1 + γ/(2√(φ - V_bs)) + n₀ + n_b·V_bs + n_d·V_ds
where n₀ = model->MOS9n0, n_b = model->MOS9nb, n_d = model->MOS9nd
```

**Thermal Voltage:**
```
V_t = k·T/q = 8.617333262145e-5 * (temp + 273.15)
```

**Effective Gate-Source Voltage (Smooth Transition):**
```
V_gsteff = 2·n·V_t · ln(1 + exp((V_gs - V_th)/(2·n·V_t)))
```

**Subthreshold Current:**
```
I_ds_sub = β · (n·V_t)² · exp((V_gs - V_th)/(n·V_t)) · (1 - exp(-V_ds/V_t))
```

**Blending with Above-Threshold Current:**
```c
blend_factor = 1.0 - exp(-V_gsteff/(n * V_t));
I_ds_total = I_ds_sub + blend_factor * I_ds_above;
```

### 6. Capacitance Models with Continuous Derivatives

**Meyer Capacitance Model with Smooth Region Transitions:**

**Accumulation Region (V_gs < V_fb):**
```
Q_g = C_ox · (V_gs - V_fb)
where V_fb = model->MOS9vfb
```

**Saturation Region (V_ds > V_gs - V_th):**
```
Q_g = (2/3) · C_ox · (V_gs - V_th)
Q_s = (2/3) · Q_g
Q_d = (1/3) · Q_g
```

**Linear Region (V_ds ≤ V_gs - V_th):**
```
Q_g = C_ox · [(V_gs - V_th) - (1/2)V_ds]
Q_s = Q_d = (1/2) · Q_g
```

**Smoothing Implementation:**
```c
/* Smooth transition between regions */
V_gt = V_gs - V_th;
if (V_gt < 0) {
    /* Accumulation */
    Q_g = model->MOS9cox * W_eff * L_eff * (V_gs - model->MOS9vfb);
} else {
    /* Smooth transition parameter */
    ε = 0.1 * V_gt;
    
    /* Determine if in saturation */
    sat_factor = 0.5 * (1.0 + tanh((V_ds - V_gt)/ε));
    
    /* Linear region charge */
    Q_g_lin = model->MOS9cox * W_eff * L_eff * (V_gt - 0.5 * V_ds);
    
    /* Saturation region charge */
    Q_g_sat = (2.0/3.0) * model->MOS9cox * W_eff * L_eff * V_gt;
    
    /* Blended charge */
    Q_g = (1.0 - sat_factor) * Q_g_lin + sat_factor * Q_g_sat;
}
```

### 7. Junction Capacitance with Voltage Smoothing

**Bottom Junction Capacitance:**
```
C_j0 = C_J · A_diff + C_JSW · P_diff
```

**Reverse Bias (V_j < FC·PB):**
```
C_j = C_j0 · (1 - V_j/PB)^(-MJ)
```

**Forward Bias (V_j ≥ FC·PB):**
```
C_j = C_j0 · (1 - FC)^(-MJ) · [1 - MJ·(V_j - FC·PB)/(PB·(1 - FC))]
```

**Smoothing Around V_j = 0:**
```c
/* Continuous derivative at V_j = 0 */
if (fabs(V_j) < 0.1) {
    /* Use smooth approximation */
    C_j = C_j0 / sqrt(1.0 + pow(V_j/PB, 2));
} else if (V_j < model->MOS9fc * model->MOS9pb) {
    /* Standard reverse bias formula */
    C_j = C_j0 * pow(1.0 - V_j/model->MOS9pb, -model->MOS9mj);
} else {
    /* Forward bias linear approximation */
    C_j = C_j0 * pow(1.0 - model->MOS9fc, -model->MOS9mj) *
          (1.0 - model->MOS9mj * (V_j - model->MOS9fc * model->MOS9pb) /
          (model->MOS9pb * (1.0 - model->MOS9fc)));
}
```

### 8. Temperature Scaling Equations

**Threshold Voltage Temperature Dependence:**
```
VTO(T) = VTO(T_nom) + (KT1 + KT1L/L_eff + KT2·V_bs) · (T/T_nom - 1)
```

**Mobility Temperature Degradation:**
```
μ₀(T) = μ₀(T_nom) · (T/T_nom)^UTE
```

**Bandgap Energy Temperature Dependence:**
```
E_g(T) = 1.16 - 7.02×10⁻⁴ · T²/(T + 1108)
```

**Junction Potential Scaling:**
```
PB(T) = PB(T_nom) · T/T_nom - 2·(k·T/q)·ln(T/T_nom) - E_g(T_nom)·T/T_nom + E_g(T)
```

**SPICE Implementation:**
```c
/* Temperature ratio */
tratio = (inst->MOS9temp + CONSTCtoK) / (model->MOS9tnom + CONSTCtoK);

/* Threshold voltage scaling */
vto_temp = model->MOS9vto + 
           (model->MOS9kt1 + model->MOS9kt1l/inst->MOS9l + 
            model->MOS9kt2 * vbs) * (tratio - 1.0);

/* Mobility scaling */
if (model->MOS9ute != 0.0) {
    u0_temp = model->MOS9u0 * pow(tratio, model->MOS9ute);
} else {
    u0_temp = model->MOS9u0;
}
```

### 9. Matrix Stamping for Newton-Raphson

**7-Node Matrix Structure:**
Nodes: [D, G, S, B, D', S', internal]

**Conductance Definitions:**
```
g_m = ∂I_ds/∂V_gs
g_ds = ∂I_ds/∂V_ds
g_mbs = ∂I_ds/∂V_bs
g_bd = ∂I_bd/∂V_bd
g_bs = ∂I_bs/∂V_bs
```

**Matrix Stamp Pattern:**
```
[ G_dd+G_dpdp   0         0         0        -G_dpdp       0       ] [V_d]   [I_d]
[ 0             0         0         0         0            0       ] [V_g]   [0]
[ 0             0         G_ss+G_ssp 0        0           -G_ssp   ] [V_s] = [I_s]
[ 0             0         0         G_bb      0            0       ] [V_b]   [I_b]
[-G_dpdp        0         0         0        G_dpdp+g_dsp -g_dsp   ] [V_d']  [0]
[ 0             0        -G_ssp     0        -g_dsp       G_ssp+g_dsp] [V_s']  [0]
```

**SPICE Implementation:**
```c
/* Stamp intrinsic MOSFET conductances */
*(inst->MOS9drainDrainPrimePtr) += g_ds;
*(inst->MOS9drainPrimeDrainPtr) += g_ds;
*(inst->MOS9drainPrimeDrainPrimePtr) += g_ds + g_m + g_mbs;
*(inst->MOS9drainPrimeGatePtr) += g_m;
*(inst->MOS9drainPrimeBulkPtr) += g_mbs;
*(inst->MOS9drainPrimeSourcePrimePtr) += -g_ds - g_m - g_mbs;

/* Stamp parasitic resistances */
g_rd = 1.0 / MAX(model->MOS9rd, 1e-12);
*(inst->MOS9drainDrainPtr) += g_rd;
*(inst->MOS9drainDrainPrimePtr) += -g_rd;
*(inst->MOS9drainPrimeDrainPtr) += -g_rd;
*(inst->MOS9drainPrimeDrainPrimePtr) += g_rd;
```

## Convergence Analysis

### 1. Newton-Raphson Voltage Limiting Algorithm

The MOS9 model employs the `DEVfetlim()` function to ensure Newton-Raphson convergence by preventing excessive voltage changes between iterations:

**Limiting Algorithm:**
```c
void DEVfetlim(double *vnew, double vold, double vto, double vcrit) {
    double vt;
    
    if (vold > vto) {
        /* Above threshold region */
        vt = vcrit;
        if (*vnew > vt) {
            if (fabs(*vnew - vold) > 2.0 * vt) {
                if (vold > vt) {
                    *vnew = vt + (*vnew - vt) / 10.0;  /* Damped update */
                } else {
                    *vnew = vt;  /* Clamp to critical voltage */
                }
            }
        }
    } else {
        /* Below threshold region */
        vt = -0.5;
        if (*vnew < vt) {
            if (fabs(*vnew - vold) > 0.5) {
                if (vold < vt) {
                    *vnew = vt + (*vnew - vt) / 10.0;  /* Damped update */
                } else {
                    *vnew = vt;  /* Clamp to lower limit */
                }
            }
        }
    }
}
```

**Application in MOS9:**
```c
/* Critical voltage calculation */
vcrit = MAX(0.5, 2.0 * fabs(vgs_old - von));

/* Apply limiting to terminal voltages */
DEVfetlim(&vgs, vgs_old, von, vcrit);
DEVfetlim(&vds, vds_old, vdsat, vcrit);
DEVfetlim(&vbs, vbs_old, 0.0, 0.5);
```

**Convergence Impact:** This algorithm prevents oscillation between strong inversion and cutoff regions, which have dramatically different derivatives, ensuring the Newton-Raphson solver remains stable.

### 2. Smooth Region Transitions for Derivative Continuity

The MOS9 model ensures C¹ continuity through mathematical smoothing functions:

**Subthreshold to Above-Threshold Transition:**
```c
/* Smooth blending factor */
Vgst = V_gs - V_th;
if (fabs(Vgst) < 1e-6) {
    /* Use series expansion for numerical stability */
    exp_arg = Vgst / (n * V_t);
    if (fabs(exp_arg) < 1e-3) {
        exp_term = 1.0 + exp_arg + 0.5 * exp_arg * exp_arg;
    } else {
        exp_term = exp(exp_arg);
    }
    V_gsteff = 2.0 * n * V_t * log(1.0 + exp_term);
} else if (Vgst > 0) {
    /* Above threshold approximation */
    V_gsteff = Vgst + 2.0 * n * V_t * log(1.0 + exp(-Vgst/(2.0 * n * V_t)));
} else {
    /* Subthreshold approximation */
    V_gsteff = 2.0 * n * V_t * exp(Vgst/(n * V_t));
}

/* Continuous derivative */
dV_gsteff_dVgs = 1.0 / (1.0 + exp(-Vgst/(2.0 * n * V_t)));
```

**Linear to Saturation Region Transition:**
```c
/* Hyperbolic tangent smoothing */
delta = 0.01 * V_dsat;
lambda = 0.5 * (1.0 + tanh(10.0 * (V_ds - V_dsat) / V_dsat));

/* Continuous first derivative */
dlambda_dVds = 5.0 / V_dsat * pow(1.0 / cosh(5.0 * (V_ds - V_dsat) / V_dsat), 2);
```

**Convergence Benefit:** Continuous derivatives across region boundaries eliminate discontinuities in the Jacobian matrix, preventing Newton-Raphson divergence at operating point transitions.

### 3. Source-Drain Swap Mechanics for Symmetric Convergence

**Swap Conditions:**
1. PMOS devices (`model->MOS9type < 0`)
2. Negative V_ds for any device type

**Voltage Transformations:**
```c
if (model->MOS9type < 0) {
    /* PMOS polarity inversion */
    vgs = -vgs;
    vds = -vds;
    vbs = -vbs;
    mode = -1;
} else {
    mode = 1;
}

/* Source-drain swap for negative Vds */
if (vds < 0.0) {
    /* Swap terminal voltages */
    double tmp_v;
    tmp_v = vd; vd = vs; vs = tmp_v;
    
    /* Swap node indices */
    int tmp_node = inst->MOS9dNode;
    inst->MOS9dNode = inst->MOS9sNode;
    inst->MOS9sNode = tmp_node;
    
    /* Swap internal nodes */
    tmp_node = inst->MOS9dNodePrime;
    inst->MOS9dNodePrime = inst->MOS9sNodePrime;
    inst->MOS9sNodePrime = tmp_node;
    
    /* Invert Vds after swap */
    vds = -vds;
    mode *= -1;
}

inst->MOS9mode = mode;
```

**Convergence Symmetry:** This ensures identical convergence properties for forward and reverse operation, and for NMOS/PMOS devices, reducing special-case handling in the solver.

### 4. Numerical Stability Protections

**Small Value Clipping:**
```c
#define CLIP(x, min, max) ((x) < (min) ? (min) : ((x) > (max) ? (max) : (x)))

/* Terminal voltage bounds */
vds = CLIP(vds, -10.0, 10.0);
vgs = CLIP(vgs, -10.0, 10.0);
vbs = CLIP(vbs, -10.0, 0.5);

/* Effective dimension protection */
Leff = MAX(inst->MOS9l - 2.0 * model->MOS9ld, 1e-12);
Weff = MAX(inst->MOS9w - 2.0 * model->MOS9wd, 1e-12);
```

**Power Function Protection:**
```c
/* Safe power function for Vgst^exponent */
if (Vgst > 0.0) {
    if (Vgst < 1e-6) {
        /* Series expansion for small values */
        pow_term = 1.0 + exponent * log(Vgst) + 
                   0.5 * exponent * (exponent - 1.0) * log(Vgst) * log(Vgst);
    } else {
        pow_term = pow(Vgst, exponent);
    }
} else {
    pow_term = 0.0;  /* Avoid pow() with negative base */
}
```

**Logarithm Protection:**
```c
/* Safe logarithm for CLM calculation */
V_diff = V_ds - V_dsat;
if (V_diff < 1e-6) {
    /* Series expansion: ln(1+x) ≈ x - x²/2 + x³/3 - ... */
    log_term = V_diff - 0.5 * V_diff * V_diff + 
               (1.0/3.0) * V_diff * V_diff * V_diff;
} else {
    log_term = log(1.0 + V_diff);
}
```

### 5. Matrix Conditioning for Non-Singular Jacobian

**Minimum Conductance Addition:**
```c
GMIN = ckt->CKTgmin;  /* Default: 1e-12 Ʊ */

/* Add to all diagonal entries */
*(inst->MOS9drainDrainPtr) += GMIN;
*(inst->MOS9gateGatePtr) += GMIN;
*(inst->MOS9sourceSourcePtr) += GMIN;
*(inst->MOS9bulkBulkPtr) += GMIN;
*(inst->MOS9drainPrimeDrainPrimePtr) += GMIN;
*(inst->MOS9sourcePrimeSourcePrimePtr) += GMIN;
```

**Parasitic Resistance Lower Bounds:**
```c
R_d = MAX(model->MOS9rd, 1e-12);
R_s = MAX(model->MOS9rs, 1e-12);
R_sh = MAX(model->MOS9rsh, 1e-12);

/* Calculate diffusion resistances */
R_d_diff = R_sh * inst->MOS9nrd / MAX(inst->MOS9w, 1e-12);
R_s_diff = R_sh * inst->MOS9nrs / MAX(inst->MOS9w, 1e-12);

R_d_total = R_d + R_d_diff;
R_s_total = R_s + R_s_diff;
```

**Capacitance Floor:**
```c
C_min = 1e-18;  /* Minimum capacitance */

C_gs = MAX(inst->MOS9cgs, C_min);
C_gd = MAX(inst->MOS9cgd, C_min);
C_gb = MAX(inst->MOS9cgb, C_min);
C_bd = MAX(inst->MOS9capbd, C_min);
C_bs = MAX(inst->MOS9capbs, C_min);
```

### 6. Convergence Testing Criteria

**Voltage Convergence Test:**
```c
reltol = ckt->CKTreltol;  /* Default: 0.001 */
vntol = ckt->CKTvoltTol;  /* Default: 1e-6 */

/* For each terminal voltage */
delVgs = fabs(vgs - inst->MOS9vgs_old);
delVds = fabs(vds - inst->MOS9vds_old);
delVbs = fabs(vbs - inst->MOS9vbs_old);

converged = (delVgs <= reltol * MAX(fabs(vgs), fabs(inst->MOS9vgs_old)) + vntol) &&
            (delVds <= reltol * MAX(fabs(vds), fabs(inst->MOS9vds_old)) + vntol) &&
            (delVbs <= reltol * MAX(fabs(vbs), fabs(inst->MOS9vbs_old)) + vntol);
```

**Current Convergence Test:**
```c
abstol = ckt->CKTabstol;  /* Default: 1e-12 */

delIds = fabs(ids - inst->MOS9ids_old);
current_converged = (delIds <= reltol * MAX(fabs(ids), fabs(inst->MOS9ids_old)) + abstol);
```

**Charge Conservation Test (Transient Analysis):**
```c
chgtol = ckt->CKTchgtol;  /* Default: 1e-14 */

/* Charge difference */
delQ = fabs(qgs_new - qgs_old) + fabs(qgd_new - qgd_old) + 
       fabs(qgb_new - qgb_old) + fabs(qbd_new - qbd_old) + 
       fabs(qbs_new - qbs_old);

charge_converged = (delQ <= chgtol);
```

### 7. Temperature Consistency Enforcement

**Simultaneous Parameter Updates:**
```c
if (inst->MOS9temp != ckt->CKTtemp) {
    /* Update all temperature-dependent parameters together */
    MOS9temperature(model, inst, ckt);
    
    /* Recompute derived parameters */
    inst->MOS9beta = (inst->MOS9weff / inst->MOS9leff) * 
                     model->MOS9kp * (inst->MOS9ueff / model->MOS9u0);
    inst->MOS9von = model->MOS9vto + 
                    model->MOS9gamma * (sqrt(model->MOS9phi - vbs) - sqrt(model->MOS9phi));
}
```

**Consistency Check:**
```c
/* Verify parameter consistency */
if (fabs(inst->MOS9vgs - inst->MOS9vgs_old) > 0.1 && 
    fabs(inst->MOS9temp - ckt->CKTtemp) > 1.0) {
    /* Temperature change detected with significant voltage change */
    ckt->CKTnoncon++;  /* Increment non-convergence counter */
    return E_SINGULAR; /* Trigger matrix re-evaluation */
}
```

### 8. Fallback Strategies for Difficult Convergence

**GMIN Stepping:**
```c
if (ckt->CKTnoncon > 5) {
    /* Increase GMIN to improve matrix conditioning */
    double gmin_original = ckt->CKTgmin;
    for (int step = 0; step < 5; step++) {
        ckt->CKTgmin = gmin_original * pow(10.0, step);
        if (MOS9load(model, ckt) == OK) {
            break;  /* Convergence achieved */
        }
    }
    /* Restore original GMIN after convergence */
    ckt->CKTgmin = gmin_original;
}
```

**Source Stepping:**
```c
if (ckt->CKTmode & MODEINITTRAN) {
    /* Gradually ramp source voltages */
    double ramp_factor = ckt->CKTtime / ckt->CKTfinalTime;
    ramp_factor = MIN(MAX(ramp_factor, 0.0), 1.0);
    
    vgs *= ramp_factor;
    vds *= ramp_factor;
    vbs *= ramp_factor;
}
```

**Damped Newton Updates:**
```c
if (ckt->CKTnoncon > 3) {
    /* Apply damping to Newton updates */
    double alpha = 0.5;  /* Damping factor */
    
    vgs = inst->MOS9vgs_old + alpha * (vgs - inst->MOS9vgs_old);
    vds = inst->MOS9vds_old + alpha * (vds - inst->MOS9vds_old);
    vbs = inst->MOS9vbs_old + alpha * (vbs - inst->MOS9vbs_old);
}
```

### 9. State Vector Management for Charge Conservation

**Charge State Allocation:**
```c
inst->MOS9states = *states;
inst->MOS9qgs = (*states)++;   /* State 0: Gate-source charge */
inst->MOS9qgd = (*states)++;   /* State 1: Gate-drain charge */
inst->MOS9qgb = (*states)++;   /* State 2: Gate-bulk charge */
inst->MOS9qbd = (*states)++;   /* State 3: Bulk-drain charge */
inst->MOS9qbs = (*states)++;   /* State 4: Bulk-source charge */
```

**Charge Conservation Enforcement:**
```c
/* Previous charge values */
qgs_old = ckt->CKTstate1[inst->MOS9qgs];
qgd_old = ckt->CKTstate1[inst->MOS9qgd];
qgb_old = ckt->CKTstate1[inst->MOS9qgb];
qbd_old = ckt->CKTstate1[inst->MOS9qbd];
qbs_old = ckt->CKTstate1[inst->MOS9qbs];

/* New charge values */
qgs_new = C_gs * vgs;
qgd_new = C_gd * vgd;
qgb_new = C_gb * vgb;
qbd_new = C_bd * vbd;
qbs_new = C_bs * vbs;

/* Store for next iteration */
ckt->CKTstate0[inst->MOS9qgs] = qgs_new;
ckt->CKTstate0[inst->MOS9qgd] = qgd_new;
ckt->CKTstate0[inst->MOS9qgb] = qgb_new;
ckt->CKTstate0[inst->MOS9qbd] = qbd_new;
ckt->CKTstate0[inst->MOS9qbs] = qbs_new;

/* Transient currents from charge difference */
I_gs = (qgs_new - qgs_old) / ckt->CKTdelta;
I_gd = (qgd_new - qgd_old) / ckt->CKTdelta;
I_gb = (qgb_new - qgb_old) / ckt->CKTdelta;
I_bd = (qbd_new - qbd_old) / ckt->CKTdelta;
I_bs = (qbs_new - qbs_old) / ckt->CKTdelta;
```

### 10. Convergence Monitoring and Diagnostics

**Device-Specific Convergence Tracking:**
```c
/* Store previous iteration values */
inst->MOS9vgs_old = vgs;
inst->MOS9vds_old = vds;
inst->MOS9vbs_old = vbs;
inst->MOS9ids_old = ids;

/* Convergence statistics */
if (ckt->CKTnoncon > 0) {
    inst->MOS9convergence_failures++;
}

/* Debug output for difficult convergence */
if (ckt->CKTnoncon > 10) {
    printf("MOS9 convergence difficulty: Vgs=%g, Vds=%g, Vbs=%g, Ids=%g\n",
           vgs, vds, vbs, ids);
    printf("  Previous: Vgs=%g, Vds=%g, Vbs=%g, Ids=%g\n",
           inst->MOS9vgs_old, inst->MOS9vds_old, inst->MOS9vbs_old, inst->MOS9ids_old);
}
```

**Algorithmic Convergence Summary:**

The MOS9 model ensures robust SPICE convergence through:
1. **Mathematical Smoothing**: Hyperbolic tangent and exponential functions provide C¹ continuity across all region boundaries
2. **Voltage Limiting**: `DEVfetlim()` prevents excessive Newton-Raphson steps
3. **Numerical Protection**: Clipping, series expansions, and minimum values prevent numerical singularities
4. **Matrix Conditioning**: GMIN addition and resistance bounds ensure non-singular Jacobian matrices
5. **Temperature Consistency**: All temperature-dependent parameters updated simultaneously
6. **Source-Drain Symmetry**: Identical convergence for forward/reverse operation
7. **Fallback Strategies**: GMIN stepping, source stepping, and damping for difficult cases
8. **Charge Conservation**: Proper state vector management for transient analysis
9. **Continuous Monitoring**: Device-specific tracking of convergence failures
10. **Physical Accuracy**: Maintains Philips model accuracy while ensuring numerical robustness

These mechanisms make the MOS9 model suitable for both digital and analog circuit simulation, providing physical accuracy with guaranteed convergence through comprehensive mathematical smoothing and numerical protection strategies.

---

## C Implementation

The MOS9 (Philips) model implementation in Ngspice translates the sophisticated mathematical formulations into efficient C code with careful attention to numerical stability and SPICE integration. The implementation spans multiple files that handle different aspects of the device simulation.

### Core Data Structures

#### Model Structure (`sMOS9model`)

The `sMOS9model` structure in `mos9defs.h` encapsulates all mathematical parameters:

```c
typedef struct sMOS9model {
    int MOS9type;                     /* Device type: NMF (>0) or PMF (<0) */
    double MOS9vto;                   /* VTO: Zero-bias threshold voltage (V) */
    double MOS9kp;                    /* KP: Transconductance parameter (A/V²) */
    double MOS9gamma;                 /* GAMMA: Body effect parameter (√V) */
    double MOS9phi;                   /* PHI: Surface potential (V) */
    double MOS9lambda;                /* LAMBDA: Channel-length modulation (1/V) */
    double MOS9rd;                    /* RD: Drain ohmic resistance (Ω) */
    double MOS9rs;                    /* RS: Source ohmic resistance (Ω) */
    double MOS9cbd;                   /* CBD: Zero-bias B-D junction capacitance (F) */
    double MOS9cbs;                   /* CBS: Zero-bias B-S junction capacitance (F) */
    double MOS9is;                    /* IS: Junction saturation current (A) */
    double MOS9pb;                    /* PB: Junction potential (V) */
    double MOS9cgso;                  /* CGSO: Gate-source overlap capacitance per width (F/m) */
    double MOS9cgdo;                  /* CGDO: Gate-drain overlap capacitance per width (F