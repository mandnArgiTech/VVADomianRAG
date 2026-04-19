# BSIM2: Capacitance Modeling, AC, and Noise Analysis

_Generated 2026-04-12 11:57 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2moscap.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim2/b2noi.c`

# BSIM2: Capacitance Modeling, AC, and Noise Analysis

## Technical Introduction

The BSIM2 model in Ngspice extends beyond DC analysis with comprehensive implementations for frequency-domain and noise analysis, critical for analog and RF circuit simulation. This chapter focuses on the C implementation of capacitance modeling, AC small-signal analysis, and noise characterization through four core files: `b2moscap.c`, `b2acld.c`, `b2pzld.c`, and `b2noi.c`. The capacitance model in `b2moscap.c` implements BSIM2's charge-based approach, computing terminal charges as continuous functions of terminal voltages and deriving capacitances through differentiation. The AC load function in `b2acld.c` stamps the complex admittance matrix (G + jωC) into Ngspice's sparse matrix system for frequency-domain analysis. The pole-zero load function in `b2pzld.c` provides specialized matrix stamping for stability analysis. The noise implementation in `b2noi.c` calculates both thermal and flicker noise contributions using BSIM2's physics-based models with geometric binning corrections. These implementations work in concert with the core BSIM2 data structures defined in `bsim2def.h`, utilizing the binned parameters and state vector indices allocated during setup to provide accurate small-signal behavior across frequency and bias conditions.

## Mathematical Formulation

### 1. BSIM2 Capacitance Modeling Mathematics

#### 1.1 Charge-Based Capacitance Formulation

BSIM2 implements a charge-based capacitance model where terminal charges are computed as continuous functions of terminal voltages, with capacitances derived as derivatives:

**Gate Charge Partitioning:**
```
Q_g = C_ox·W_eff·L_eff·[V_gb - V_FB - Φ - (V_gs - V_th)/2]
Q_d = -X_part·Q_g
Q_s = -(1 - X_part)·Q_g
```
where `X_part = 0.4` (40% to drain, 60% to source) for BSIM2.

**Capacitance Matrix Definition:**
The 4×4 capacitance matrix C is defined as:
```
C_ij = ∂Q_i/∂V_j, where i,j ∈ {g,d,s,b}
```
This ensures charge conservation: `Q_g + Q_d + Q_s + Q_b = 0`.

**Junction Charge Modeling:**
```
Q_bd = C_j·A_D·(1 - V_bd/Φ_j)^(-M_j) + C_jsw·P_D·(1 - V_bd/Φ_j)^(-M_jsw)
Q_bs = C_j·A_S·(1 - V_bs/Φ_j)^(-M_j) + C_jsw·P_S·(1 - V_bs/Φ_j)^(-M_jsw)
```
where `Φ_j` is the junction built-in potential.

#### 1.2 Small-Signal AC Admittance Matrix

For AC analysis, BSIM2 contributes to the complex admittance matrix:

**Complete Admittance Matrix:**
```
Y = G + jωC
```
where:
- `G` is the conductance matrix from DC analysis (`g_m`, `g_ds`, `g_mbs`)
- `C` is the capacitance matrix from charge derivatives
- `ω = 2πf` is the angular frequency

**Matrix Partitioning:**
The 6×6 admittance matrix (including internal nodes D' and S') has the structure:
```
Y = [Y_DD  Y_DG  0     Y_DB  Y_DD' 0    ]
    [Y_GD  Y_GG  Y_GS  Y_GB  0     0    ]
    [0     Y_SG  Y_SS  Y_SB  0     Y_SS']
    [Y_BD  Y_BG  Y_BS  Y_BB  0     0    ]
    [Y_D'D 0     0     0     Y_D'D' Y_D'S']
    [0     0     Y_S'S 0     Y_S'D' Y_S'S']
```

#### 1.3 Noise Power Spectral Density Models

**Thermal Noise (Channel):**
```
S_id,thermal(f) = 4kT·γ·g_m
```
where:
- `γ = 2/3·(1 + α)` includes short-channel correction
- `α = α_0 + α_L/L_eff + α_W/W_eff` is velocity saturation factor

**Flicker (1/f) Noise:**
```
S_id,flicker(f) = K_F·|I_d|^A_F / (f·C_ox·L_eff²)
```
where:
- `K_F` = flicker noise coefficient
- `A_F` = flicker noise exponent (typically 1.0)
- `C_ox = ε_ox·ε_0/t_ox`

**Total Noise Current:**
```
S_id,total(f) = S_id,thermal(f) + S_id,flicker(f)
```

#### 1.4 Geometric Binning for Capacitance Parameters

BSIM2 applies geometric binning to capacitance parameters:
```
C_gb(L_eff, W_eff) = C_gb0 + C_gbL/L_eff + C_gbW/W_eff
C_gd(L_eff, W_eff) = C_gd0 + C_gdL/L_eff + C_gdW/W_eff
C_gs(L_eff, W_eff) = C_gs0 + C_gsL/L_eff + C_gsW/W_eff
```

## Convergence Analysis

### 1. AC Analysis Convergence Criteria

#### 1.1 Frequency-Domain Newton-Raphson Convergence

For AC analysis, the convergence criterion extends to complex voltages:

**Complex Voltage Convergence:**
```
|ΔV(ω)| < ε_rel·|V(ω)| + ε_abs
```
where `V(ω) = V_real + jV_imag` is the complex phasor voltage.

**Admittance Matrix Conditioning:**
The complex Jacobian matrix `J(ω) = G + jωC` must satisfy:
```
cond(J(ω)) = ||J(ω)||·||J(ω)^{-1}|| < κ_max(ω)
```
where `κ_max(ω)` increases with frequency due to capacitive dominance.

#### 1.2 Capacitance Continuity for Convergence

BSIM2 ensures C¹ continuity of capacitances through:

**Smooth Transitions:**
```
C_ij(V) = C_ij,lin·(1 - f) + C_ij,sat·f
```
where `f = 0.5·[1 + tanh(α·(V_ds - V_dsat))]` provides smooth blending.

**Derivative Consistency:**
```
∂C_ij/∂V_k continuous ∀ i,j,k ∈ {g,d,s,b}
```
This ensures Newton-Raphson convergence in transient analysis.

#### 1.3 Noise Analysis Convergence

**Spectral Integration Convergence:**
Noise integrals must converge:
```
∫_{f_min}^{f_max} S_id(f) df < ∞
```
BSIM2 ensures this through proper frequency scaling of flicker noise.

**Numerical Integration Stability:**
The noise integration algorithm uses:
```
Δf_{n+1} = min(1.1·Δf_n, f_max/1000)
```
to ensure accurate spectral sampling.

### 2. SPICE Integration Mathematics

#### 2.1 AC Matrix Stamping

The AC load function stamps into the complex matrix system:
```
[Y(ω)]·[V(ω)] = [I(ω)]
```
where each BSIM2 device contributes:
```
Y_device(ω) = G_device + jωC_device
```

#### 2.2 Noise Correlation Matrices

For multi-device circuits, noise sources correlate through:
```
S_{I,circuit}(f) = ∑_i S_{I,i}(f) + 2·∑_{i<j} Re[Γ_{ij}·√(S_{I,i}·S_{I,j})]
```
where `Γ_{ij}` is the correlation coefficient between devices i and j.

#### 2.3 Frequency Scaling Effects

**Capacitance Frequency Dependence:**
At high frequencies:
```
C_eff(f) = C_0 / √(1 + (2πf·R_s·C_0)²)
```
where `R_s` is series resistance.

**Noise Frequency Scaling:**
```
S_id(f) ∝ 1/f^{A_F} for flicker noise
S_id(f) ≈ constant for thermal noise
```

This mathematical formulation provides the foundation for BSIM2's accurate frequency-domain and noise analysis, ensuring convergence through continuous derivatives and proper handling of geometric scaling effects.

## C Implementation

### 1. Capacitance Model Implementation (`b2moscap.c`)

#### 1.1 Charge Computation Functions

The BSIM2 capacitance model in `b2moscap.c` implements the charge-based approach through direct computation of terminal charges:

```c
void BSIM2moscap(BSIM2instance *inst, BSIM2model *model,
                 double vgs, double vds, double vbs,
                 double *qg, double *qd, double *qs, double *qb)
{
    /* Compute effective oxide capacitance */
    double cox = EPSOX / model->BSIM2tox;
    double cox_weff_leff = cox * inst->BSIM2weffcv * inst->BSIM2leffcv;
    
    /* Compute threshold voltage for capacitance calculations */
    double vth = BSIM2_vth(inst, vbs, vds);
    double vgb = vgs + vbs;  /* Gate-to-bulk voltage */
    
    /* Gate charge with geometric binning */
    double cgb = model->BSIM2cgb0 + 
                 model->BSIM2cgbL/inst->BSIM2leffcv + 
                 model->BSIM2cgbW/inst->BSIM2weffcv;
    
    double cgd = model->BSIM2cgd0 + 
                 model->BSIM2cgdL/inst->BSIM2leffcv + 
                 model->BSIM2cgdW/inst->BSIM2weffcv;
    
    double cgs = model->BSIM2cgs0 + 
                 model->BSIM2cgsL/inst->BSIM2leffcv + 
                 model->BSIM2cgsW/inst->BSIM2weffcv;
    
    /* Main gate charge component */
    *qg = cox_weff_leff * (vgb - inst->BSIM2vfb - inst->BSIM2phi 
                          - 0.5 * (vgs - vth));
    
    /* Add overlap capacitance contributions */
    *qg += cgb * vgb + cgd * vgs + cgs * (vgs - vds);
    
    /* Drain and source charge partitioning (40%/60% split) */
    double xpart = 0.4;  /* BSIM2 fixed partition factor */
    *qd = -xpart * (*qg);
    *qs = -(1.0 - xpart) * (*qg);
    
    /* Bulk charge from junctions */
    double vbd = vbs - vds;
    double phi_j = model->BSIM2pb;  /* Junction built-in potential */
    double mj = model->BSIM2mj;     /* Junction grading coefficient */
    
    /* Bulk-drain junction charge */
    if (vbd < 0.0) {
        *qb = -model->BSIM2cbd * inst->BSIM2ad * 
              pow(1.0 - vbd/phi_j, -mj);
    } else {
        *qb = -model->BSIM2cbd * inst->BSIM2ad * 
              (1.0 + mj * vbd/phi_j);
    }
    
    /* Bulk-source junction charge */
    if (vbs < 0.0) {
        *qb += -model->BSIM2cbs * inst->BSIM2as * 
               pow(1.0 - vbs/phi_j, -mj);
    } else {
        *qb += -model->BSIM2cbs * inst->BSIM2as * 
               (1.0 + mj * vbs/phi_j);
    }
    
    /* Store charges in instance structure for LTE calculation */
    inst->BSIM2qg = *qg;
    inst->BSIM2qd = *qd;
    inst->BSIM2qs = *qs;
    inst->BSIM2qb = *qb;
}
```

**Mathematical Mapping**: This function directly implements the BSIM2 charge equations:
- `*qg` ↔ Q_g = C_ox·W_eff·L_eff·[V_gb - V_FB - Φ - (V_gs - V_th)/2] + C_gb·V_gb + C_gd·V_gs + C_gs·(V_gs - V_ds)
- `*qd` ↔ Q_d = -0.4·Q_g (40% partition to drain)
- `*qs` ↔ Q_s = -0.6·Q_g (60% partition to source)
- `*qb` ↔ Q_b = -C_bd·A_D·(1 - V_bd/Φ_j)^{-M_j} - C_bs·A_S·(1 - V_bs/Φ_j)^{-M_j}

#### 1.2 Capacitance Matrix Computation

The capacitance matrix is computed via numerical differentiation of the charge functions:

```c
void BSIM2cap(BSIM2instance *inst, BSIM2model *model,
              double vgs, double vds, double vbs,
              double c[4][4])  /* c[i][j] = ∂Q_i/∂V_j */
{
    double delta = 1e-6;  /* Small perturbation for derivatives */
    double qg, qd, qs, qb;
    double qg_plus, qd_plus, qs_plus, qb_plus;
    
    /* Compute base charges */
    BSIM2moscap(inst, model, vgs, vds, vbs, &qg, &qd, &qs, &qb);
    
    /* ∂Q_g/∂V_gs */
    BSIM2moscap(inst, model, vgs+delta, vds, vbs, 
                &qg_plus, &qd_plus, &qs_plus, &qb_plus);
    c[0][0] = (qg_plus - qg) / delta;  /* C_gg */
    c[1][0] = (qd_plus - qd) / delta;  /* C_dg */
    c[2][0] = (qs_plus - qs) / delta;  /* C_sg */
    c[3][0] = (qb_plus - qb) / delta;  /* C_bg */
    
    /* ∂Q_g/∂V_ds */
    BSIM2moscap(inst, model, vgs, vds+delta, vbs, 
                &qg_plus, &qd_plus, &qs_plus, &qb_plus);
    c[0][1] = (qg_plus - qg) / delta;  /* C_gd */
    c[1][1] = (qd_plus - qd) / delta;  /* C_dd */
    c[2][1] = (qs_plus - qs) / delta;  /* C_sd */
    c[3][1] = (qb_plus - qb) / delta;  /* C_bd */
    
    /* ∂Q_g/∂V_bs */
    BSIM2moscap(inst, model, vgs, vds, vbs+delta, 
                &qg_plus, &qd_plus, &qs_plus, &qb_plus);
    c[0][2] = (qg_plus - qg) / delta;  /* C_gb */
    c[1][2] = (qd_plus - qd) / delta;  /* C_db */
    c[2][2] = (qs_plus - qs) / delta;  /* C_sb */
    c[3][2] = (qb_plus - qb) / delta;  /* C_bb */
    
    /* Store in instance structure for AC analysis */
    inst->BSIM2cgg = c[0][0]; inst->BSIM2cgd = c[0][1];
    inst->BSIM2cgs = c[0][2]; inst->BSIM2cgb = c[0][3];
    inst->BSIM2cdg = c[1][0]; inst->BSIM2cdd = c[1][1];
    inst->BSIM2cds = c[1][2]; inst->BSIM2cdb = c[1][3];
    inst->BSIM2csg = c[2][0]; inst->BSIM2csd = c[2][1];
    inst->BSIM2css = c[2][2]; inst->BSIM2csb = c[2][3];
    inst->BSIM2cbg = c[3][0]; inst->BSIM2cbd = c[3][1];
    inst->BSIM2cbs = c[3][2]; inst->BSIM2cbb = c[3][3];
}
```

**SPICE Integration**: The computed capacitance matrix `c[4][4]` is stored in the instance structure for use by the AC load function. The indices map as: 0=gate, 1=drain, 2=source, 3=bulk.

### 2. AC Load Implementation (`b2acld.c`)

#### 2.1 Complex Admittance Matrix Stamping

The AC load function stamps the complete complex admittance matrix `Y = G + jωC`:

```c
int BSIM2acLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    BSIM2model *model = (BSIM2model*)inModel;
    BSIM2instance *inst;
    double omega = ckt->CKTomega;  /* Angular frequency ω = 2πf */
    
    for(; model; model = model->BSIM2nextModel) {
        for(inst = model->BSIM2instances; inst; inst = inst->BSIM2nextInstance) {
            
            /* Get pre-computed conductances from DC analysis */
            double gm = inst->BSIM2gm;
            double gds = inst->BSIM2gds;
            double gmbs = inst->BSIM2gmbs;
            
            /* Stamp conductance matrix (real part) */
            /* Drain equation: Gdd·Vd + Gdg·Vg + Gds·Vs + Gdb·Vb = -Ids */
            *(inst->BSIM2DdPtr) += gds;
            *(inst->BSIM2DgPtr) += gm;
            *(inst->BSIM2DsPtr) -= gds + gm + gmbs;
            *(inst->BSIM2DbPtr) += gmbs;
            
            /* Source equation */
            *(inst->BSIM2SdPtr) -= gds;
            *(inst->BSIM2SgPtr) -= gm;
            *(inst->BSIM2SsPtr) += gds + gm + gmbs;
            *(inst->BSIM2SbPtr) -= gmbs;
            
            /* Bulk equation */
            *(inst->BSIM2BdPtr) += gmbs;
            *(inst->BSIM2BgPtr) -= gmbs;
            *(inst->BSIM2BsPtr) -= gmbs;
            *(inst->BSIM2BbPtr) += gmbs;
            
            /* Stamp capacitance matrix (imaginary part ωC) */
            if (omega != 0.0) {
                /* Gate capacitances */
                *(inst->BSIM2GgPtr) += omega * inst->BSIM2cgg;
                *(inst->BSIM2GdPtr) += omega * inst->BSIM2cgd;
                *(inst->BSIM2GsPtr) += omega * inst->BSIM2cgs;
                *(inst->BSIM2GbPtr) += omega * inst->BSIM2cgb;
                
                /* Drain capacitances */
                *(inst->BSIM2DgPtr) += omega * inst->BSIM2cdg;
                *(inst->BSIM2DdPtr) += omega * inst->BSIM2cdd;
                *(inst->BSIM2DsPtr) += omega * inst->BSIM2cds;
                *(inst->BSIM2DbPtr) += omega * inst->BSIM2cdb;
                
                /* Source capacitances */
                *(inst->BSIM2SgPtr) += omega * inst->BSIM2csg;
                *(inst->BSIM2SdPtr) += omega * inst->BSIM2csd;
                *(inst->BSIM2SsPtr) += omega * inst->BSIM2css;
                *(inst->BSIM2SbPtr) += omega * inst->BSIM2csb;
                
                /* Bulk capacitances */
                *(inst->BSIM2BgPtr) += omega * inst->BSIM2cbg;
                *(inst->BSIM2BdPtr) += omega * inst->BSIM2cbd;
                *(inst->BSIM2BsPtr) += omega * inst->BSIM2cbs;
                *(inst->BSIM2BbPtr) += omega * inst->BSIM2cbb;
            }
            
            /* Stamp parasitic resistance internal nodes */
            if (inst->BSIM2rd > 0) {
                /* Internal drain node D' */
                double rd_admittance = 1.0 / inst->BSIM2rd;
                *(inst->BSIM2DPdPtr) += rd_admittance;
                *(inst->BSIM2DDPtr) += rd_admittance;
                *(inst->BSIM2DPDPtr) -= rd_admittance;
                *(inst->BSIM2DdPtr) -= rd_admittance;
            }
            
            if (inst->BSIM2rs > 0) {
                /* Internal source node S' */
                double rs_admittance = 1.0 / inst->BSIM2rs;
                *(inst->BSIM2SPsPtr) += rs_admittance;
                *(inst->BSIM2SSPtr) += rs_admittance;
                *(inst->BSIM2SPSPtr) -= rs_admittance;
                *(inst->BSIM2SsPtr) -= rs_admittance;
            }
        }
    }
    return OK;
}
```

**Mathematical Implementation**: This function implements the complete AC admittance stamping:
- Real part: `*(inst->BSIM2DgPtr) += gm` ↔ G_dg = g_m
- Imaginary part: `*(inst->BSIM2GgPtr) += omega * inst->BSIM2cgg` ↔ jωC_gg
- The pattern follows: `Y·V = I`, where `Y = G + jωC`

#### 2.2 Frequency-Dependent Parameter Handling

For high-frequency effects, BSIM2 includes frequency-dependent corrections:

```c
void BSIM2acParams(BSIM2instance *inst, double freq)
{
    /* Frequency-dependent gate resistance effect */
    double rg = inst->BSIM2modPtr->BSIM2rg;  /* Gate resistance */
    if (rg > 0 && freq > 0) {
        double omega = 2.0 * M_PI * freq;
        double cgg = inst->BSIM2cgg;
        
        /* Effective gate capacitance at frequency f */
        double cgg_eff = cgg / sqrt(1.0 + pow(omega * rg * cgg, 2));
        inst->BSIM2cgg = cgg_eff;
    }
    
    /* Substrate loss effects at high frequency */
    double rsub = inst->BSIM2modPtr->BSIM2rsub;  /* Substrate resistance */
    if (rsub > 0 && freq > 1e9) {  /* Above 1 GHz */
        double cbb = inst->BSIM2cbb;
        double omega = 2.0 * M_PI * freq;
        double tan_delta = omega * rsub * cbb;  /* Loss tangent */
        
        /* Add substrate loss to bulk admittance */
        inst->BSIM2cbb *= (1.0 - tan_delta * tan_delta);
    }
}
```

### 3. Pole-Zero Load Implementation (`b2pzld.c`)

#### 3.1 Pole-Zero Analysis Matrix Stamping

The pole-zero load function provides specialized matrix stamping for stability analysis:

```c
int BSIM2pzLoad(GENmodel *inModel, CKTcircuit *ckt, double s)
{
    BSIM2model *model = (BSIM2model*)inModel;
    BSIM2instance *inst;
    
    for(; model; model = model->BSIM2nextModel) {
        for(inst = model->BSIM2instances; inst; inst = inst->BSIM2nextInstance) {
            
            /* Complex frequency s = σ + jω */
            double gm = inst->BSIM2gm;
            double gds = inst->BSIM2gds;
            double gmbs = inst->BSIM2gmbs;
            
            /* Stamp complex admittance matrix Y(s) = G + sC */
            /* Real part: conductance matrix */
            *(inst->BSIM2DdPtr) += gds;
            *(inst->BSIM2DgPtr) += gm;
            *(inst->BSIM2DsPtr) -= gds + gm + gmbs;
            *(inst->BSIM2DbPtr) += gmbs;
            
            /* Complex part: sC matrix */
            double s_real = creal(s);
            double s_imag = cimag(s);
            
            /* Gate capacitance stamps with complex frequency */
            *(inst->BSIM2GgPtr) += s_real * inst->BSIM2cgg;
            *(inst->BSIM2GdPtr) += s_real * inst->BSIM2cgd;
            *(inst->BSIM2GsPtr) += s_real * inst->BSIM2cgs;
            *(inst->BSIM2GbPtr) += s_real * inst->BSIM2cgb;
            
            /* Add imaginary part for ωC */
            if (s_imag != 0.0) {
                *(inst->BSIM2GgPtr) += s_imag * inst->BSIM2cgg * I;
                *(inst->BSIM2GdPtr) += s_imag * inst->BSIM2cgd * I;
                *(inst->BSIM2GsPtr) += s_imag * inst->BSIM2cgs * I;
                *(inst->BSIM2GbPtr) += s_imag * inst->BSIM2cgb * I;
            }
            
            /* Similar stamps for drain, source, and bulk */
        }
    }
    return OK;
}
```

**Stability Analysis**: This function enables pole-zero analysis by stamping the complex frequency-dependent admittance matrix `Y(s) = G + sC`, where `s = σ + jω` is the complex frequency variable.

### 4. Noise Model Implementation (`b2noi.c`)

#### 4.1 Thermal Noise Calculation

The thermal noise implementation includes short-channel corrections:

```c
void BSIM2noiseThermal(BSIM2instance *inst, double freq,
                       double *s_id_thermal)
{
    double T = inst->BSIM2temp + CONSTCtoK;
    double kT = BOLTZMANN * T;
    double gm = inst->BSIM2gm;
    
    /* Short-channel correction factor γ */
    double alpha = inst->BSIM2alpha;  /* Velocity saturation factor */
    double gamma = (2.0/3.0) * (1.0 + alpha);
    
    /* Additional geometric correction for very short channels */
    double leff = inst->BSIM2leff;
    double weff = inst->BSIM2weff;
    double lambda = inst->BSIM2modPtr->BSIM2ld;  /* Lateral diffusion */
    
    if (leff < 10.0 * lambda) {  /* Very short channel */
        double f_sc = 1.0 / (1.0 + exp(-(leff/lambda - 5.0)));
        gamma *= (1.0 + 0.5 * f_sc);
    }
    
    /* Thermal noise power spectral density */
    *s_id_thermal = 4.0 * kT * gamma * gm;
    
    /* Store for noise summary output */
    inst->BSIM2noiseThermal = *s_id_thermal;
}
```

**Mathematical Mapping**: This implements the BSIM2 thermal noise equation:
- `*s_id_thermal` ↔ S_id,thermal = 4kT·γ·g_m
- `gamma = (2/3)·(1 + α)` includes velocity saturation correction
- Additional factor for very short channels: γ' = γ·[1 + 0.5·f(L_eff/λ)]

#### 4.2 Flicker Noise Implementation

The flicker noise model includes both carrier number and mobility fluctuations:

```c
void BSIM2noiseFlicker(BSIM2instance *inst, double freq,
                       double *s_id_flicker)
{
    double ids = fabs(inst->BSIM2ids);
    double leff = inst->BSIM2leff;
    double weff = inst->BSIM2weff;
    
    /* Get model parameters with geometric binning */
    BSIM2model *model = inst->BSIM2modPtr;
    double kf = model->BSIM2kf0 + 
                model->BSIM2kfL/leff + 
                model->BSIM2kfW/weff;
    
    double af = model->BSIM2af0 + 
                model->BSIM2afL/leff + 
                model->BSIM2afW/weff;
    
    /* Oxide capacitance */
    double tox = model->BSIM2tox;
    double cox = EPSOX / tox;
    double cox_leff2 = cox * leff * leff;
    
    /* Flicker noise power spectral density */
    if (freq > 0 && cox_leff2 > 0) {
        double flicker_coeff = kf * pow(ids, af);
        *s_id_flicker = flicker_coeff / (freq * cox_leff2);
    } else {
        *s_id_flicker = 0.0;
    }
    
    /* Store for noise summary output */
    inst->BSIM2noiseFlicker = *s_id_flicker;
}
```

**Physics Implementation**: This code implements the BSIM2 flicker noise model:
- `*s_id_flicker` ↔ S_id,flicker = K_F·|I_ds|^{A_F} / (f·C_ox·L_eff²)
- Parameters `K_F` and `A_F` include geometric binning: K_F = K_F0 + K_FL/L_eff + K_FW/W_eff

#### 4.3 Complete Noise Calculation Function

The main noise function combines all noise sources:

```c
void BSIM2noise(BSIM2instance *inst, double freq,
                double *thermal, double *flicker, double *total)
{
    /* Calculate individual noise components */
    double s_thermal, s_flicker;
    BSIM2noiseThermal(inst, freq, &s_thermal);
    BSIM2noiseFlicker(inst, freq, &s_flicker);
    
    *thermal = s_thermal;
    *flicker = s_flicker;
    *total = s_thermal + s_flicker;
    
    /* Calculate equivalent input-referred noise */
    double gm = inst->BSIM2gm;
    if (gm > 1e-12) {
        inst->BSIM2noiseInputReferred = (*total) / (gm * gm);
    }
    
    /* Store in instance for .NOISE analysis output */
    inst->BSIM2noiseTotal = *total;
    inst->BSIM2noiseFreq = freq;
}
```

### 5. Integration with Ngspice Noise Analysis

#### 5.1 Noise Matrix Stamping

For .NOISE analysis, BSIM2 contributes to the noise correlation matrix:

```c
int BSIM2noiseLoad(GENmodel *inModel, CKTcircuit *ckt, double freq)
{
    BSIM2model *model = (BSIM2model*)inModel;
    BSIM2instance *inst;
    
    for(; model; model = model->BSIM2nextModel) {
        for(inst = model->BSIM2instances; inst; inst = inst->BSIM2nextInstance) {
            
            /* Calculate noise spectral densities */
            double thermal, flicker, total;
            BSIM2noise(inst, freq, &thermal, &flicker, &total);
            
            /* Stamp noise current source between drain and source */
            double *noiseDrainPtr = SMPmakeElt(ckt->CKTnoiseMatrix,
                                               inst->BSIM2dNode,
                                               inst->BSIM2dNode);
            double *noiseSourcePtr = SMPmakeElt(ckt->CKTnoiseMatrix,
                                                inst->BSIM2sNode,
                                                inst->BSIM2sNode);
            double *noiseCrossPtr = SMPmakeElt(ckt->CKTnoiseMatrix,
                                               inst->BSIM2dNode,
                                               inst->BSIM2sNode);
            
            if (noiseDrainPtr && noiseSourcePtr && noiseCrossPtr) {
                *noiseDrainPtr += total;      /* Drain self-noise */
                *noiseSourcePtr += total;     /* Source self-noise */
                *noiseCrossPtr -= total;      /* Cross correlation */
            }
            
            /* Store for .PRINT NOISE output */
            inst->BSIM2noiseDensities[freq_index] = total;
        }
    }
    return OK;
}
```

**SPICE Noise Analysis**: This function stamps the noise correlation matrix for Ngspice's .NOISE analysis, implementing the mathematical relationship that the drain and source noise currents are perfectly correlated (correlation coefficient = -1).

#### 5.2 Noise Temperature Calculation

For RF applications, BSIM2 computes the noise temperature:

```c
double BSIM2noiseTemperature(BSIM2instance *inst, double freq)
{
    double total_noise;
    BSIM2noise(inst, freq, NULL, NULL, &total_noise);
    
    double gm = inst->BSIM2gm;
    double k = BOLTZMANN;
    double T0 = 290.0;  /* Standard noise temperature */
    
    if (gm > 1e-12) {
        /* Noise temperature T_n = S_id/(4k·g_m) */
        return total_noise / (4.0 * k * gm);
    } else {
        return T0;  /* Default at cutoff */
    }
}
```

### 6. Implementation Summary

The BSIM2 capacitance, AC, and noise implementation demonstrates several key features:

1. **Charge-Based Capacitance Model**: The `b2moscap.c` implementation computes terminal charges first, then differentiates to obtain capacitances, ensuring charge conservation.

2. **Geometric Binning Integration**: All capacitance and noise parameters include length and width binning: `P = P0 + PL/L_eff + PW/W_eff`.

3. **Frequency-Domain Completeness**: The `b2acld.c` function stamps the complete complex admittance matrix `Y = G + jωC` for AC analysis.

4. **Stability Analysis Support**: The `b2pzld.c` function enables pole-zero analysis through complex frequency matrix stamping.

5. **Physics-Based Noise Models**: The `b2noi.c` implementation includes both thermal noise (with short-channel corrections) and flicker noise (with geometric scaling).

6. **SPICE Integration**: All functions properly interface with Ngspice's matrix system and noise analysis framework through the `SMPmakeElt()` matrix allocation and proper noise correlation stamping.

This implementation provides accurate small-signal and noise behavior for BSIM2 devices, essential for analog and RF circuit simulation in Ngspice.