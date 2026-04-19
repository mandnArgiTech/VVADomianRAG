# BSIM4v5: Nanometer Physics Revision and DC Load

_Generated 2026-04-12 13:47 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/bsim4v5def.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5par.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5ld.c`

# Chapter: BSIM4v5: Nanometer Physics Revision and DC Load

## Technical Introduction

The BSIM4v5 model in Ngspice represents a significant evolution of the BSIM4 framework, incorporating advanced nanometer-scale physics essential for accurate simulation of sub-100nm CMOS technologies. The implementation centers on the DC load function (`b4v5ld.c`), which integrates complex mathematical formulations for quantum mechanical tunneling, layout-dependent effects (STI stress, WPE), pocket/halo implants, and enhanced mobility degradation. This chapter details the C implementation that maps these physics to SPICE's numerical engine, focusing on the data structures in `bsim4v5def.h`, parameter transformations in `b4v5set.c` and `b4v5temp.c`, and the core load algorithm in `b4v5ld.c`. The implementation maintains backward compatibility while adding BSIM4v5-specific enhancements for improved accuracy in deep-submicron simulation.

---

## Mathematical Formulation

### 1. Threshold Voltage with Advanced Nanometer Effects

The BSIM4v5 threshold voltage model extends BSIM4 with additional physical effects critical for nanometer-scale SPICE simulation:

**Composite Vth Equation:**
```
Vth = Vth0 + ΔVth_SCE + ΔVth_DIBL + ΔVth_NWE + ΔVth_WPE + ΔVth_pocket
```

**Component Breakdown:**

*   **Short-Channel Effect (SCE):**
    ```
    ΔVth_SCE = -dvt0·exp(-dvt1·Leff/(2·lto))·(2·exp(-dvt2·Vbs) + 1)
    ```
    Models Vth roll-off with decreasing channel length, where `lto` is the characteristic length.

*   **Drain-Induced Barrier Lowering (DIBL):**
    ```
    ΔVth_DIBL = -(η0 + ηb·Vbs)·Vds
    ```
    Accounts for threshold reduction due to drain voltage, with body-bias dependence.

*   **Narrow-Width Effect (NWE):**
    ```
    ΔVth_NWE = k3·(φ - Vbs - Vbm) / (Weff·w0)^wint
    ```
    Models increased Vth in narrow devices due to fringing fields.

*   **Well Proximity Effect (WPE):**
    ```
    ΔVth_WPE = warc / sd^1.5
    ```
    Additional Vth shift from well-edge proximity, where `sd` is the distance to well edge.

*   **Pocket/Halo Implant Effect:**
    ```
    ΔVth_pocket = dvtshft·(1 + dvtshfttemp·(T/Tnom - 1))
    ```
    Models additional Vth shift from pocket implants with temperature dependence.

**SPICE Integration:** This composite `Vth` is computed in `BSIM4v5load()` and directly affects the gate overdrive voltage `Vgst = Vgs - Vth` used in all current equations. The derivatives `∂Vth/∂Vds` and `∂Vth/∂Vbs` contribute to the output conductance (`gds`) and body transconductance (`gmbs`) stamped into the SPICE Jacobian matrix.

### 2. Advanced Mobility Degradation Model

BSIM4v5 implements a comprehensive mobility model incorporating multiple degradation mechanisms:

**Effective Mobility Calculation:**
```
μ_eff = μ_base × f_vsat × f_pocket × f_STI × f_WPE
```

**Component Functions:**

*   **Vertical Field Degradation:**
    ```
    μ_base = μ0 / [1 + ua·E_eff + ub·E_eff²]
    where E_eff = (Vgs - Vth)/(6·Tox) [MV/cm]
    ```

*   **Velocity Saturation:**
    ```
    f_vsat = 1 / [1 + (E_eff/E_sat)^β]^(1/β)
    where E_sat = 2·v_sat/μ_base
    ```

*   **Pocket/Halo Implant Effect:**
    ```
    f_pocket = 1 + phigh/Leff - plow/Leff
    ```
    Models mobility enhancement from pocket implants.

*   **STI Stress Effect:**
    ```
    f_STI = 1 + sar/sa + sbr/sb + sdr/sd
    ```
    Accounts for mobility modulation from shallow trench isolation stress.

*   **WPE Mobility Effect:**
    ```
    f_WPE = 1 + wbrc/sd^1.5
    ```
    Mobility shift from well proximity.

**SPICE Integration:** The final `μ_eff` is stored in `BSIM4v5ueff` and used in the current gain factor `β = μ_eff·Cox·Weff/Leff` for drain current calculation in `BSIM4v5load()`.

### 3. Quantum Mechanical Tunneling Currents

BSIM4v5 implements separate tunneling models for different gate leakage mechanisms:

**Gate-to-Channel Tunneling (Inversion):**
```
Igc = aigbinv·(Tox·V_ox)^bigbinv·exp(-cigbinv·Tox)·Weff·Leff
where V_ox = Vgs - Vth
```

**Gate-to-S/D Overlap Tunneling:**
```
Igd = aigsd·(V_gd)^bigsd·exp(-cigsd·Tox)·Weff·dlc
Igs = aigsd·(V_gs)^bigsd·exp(-cigsd·Tox)·Weff·dlc
```

**Gate-to-Bulk Tunneling (Accumulation):**
```
Igb = aigbacc·(V_gb)^bigbacc·exp(-cigbacc·Tox)·Weff·Leff
```

**SPICE Integration:** These currents are computed in `BSIM4v5load()` when corresponding model flags are active. They add to the terminal current vector (`CKTrhs`) and contribute conductances `g_eltd = ∂Ig/∂Vg` to the SPICE matrix. Separate state variables (`BSIM4v5states[5-8]`) track tunneling charges for transient analysis.

### 4. Continuous Current Equations with Smooth Transitions

BSIM4v5 implements C¹-continuous current equations for robust Newton-Raphson convergence:

**Subthreshold Current:**
```
Ids_sub = I_sub·exp((Vgs - Vth)/(n·Vt))·(1 - exp(-Vds/Vt))
where n = 1 + nfactor + cdsc·exp(-Vds/voff)/Cox
```

**Strong Inversion Current:**
```
Ids_si = β·[(Vgs - Vth)·Vds - 0.5·Vds²]/(1 + Vds/(v_max·Leff))
```

**Saturation Voltage:**
```
Vdsat = (Vgs - Vth)/κ
```

**Smooth Blending Function:**
```
Vds_eff = 0.5·[Vds + Vdsat - √((Vds - Vdsat)² + 4δ²)]
Ids = [Ids_lin·(1 - Vds_eff/Vdsat) + Ids_sat·(Vds_eff/Vdsat)]/(1 + Vds_eff/(v_max·Leff))
```

**Final Continuous Current:**
```
α = 0.5·[1 + tanh((Vgs - Vth)/(δ·Vt))]
Ids_final = α·Ids + (1 - α)·Ids_sub
```

**SPICE Integration:** The hyperbolic tangent blending ensures smooth transitions between operating regions, essential for Newton-Raphson convergence. The parameter `δ` controls the smoothness width, typically `0.1·Vt`.

### 5. Effective Geometry with Quantum Corrections

BSIM4v5 modifies effective dimensions to account for quantum mechanical and processing effects:

**Effective Length:**
```
Leff = L_drawn - 2·dlc + dlc·exp(-L_drawn/llc)
```

**Effective Width:**
```
Weff = W_drawn - 2·dwc + dwc·exp(-W_drawn/wwc)
```

**SPICE Integration:** These corrected dimensions are computed in `BSIM4v5setup()` and stored in `BSIM4v5leff` and `BSIM4v5weff`. The exponential terms model the asymptotic approach to fully depleted behavior at very small dimensions.

### 6. Temperature Scaling Formulations

BSIM4v5 enhances temperature dependence with geometry-aware scaling:

**Mobility Temperature Dependence:**
```
μ(T) = μ0·(T/Tnom)^(-ute)
```

**Threshold Voltage Temperature Scaling:**
```
ΔVth_temp = kt1·(T/Tnom - 1) + kt1l/Leff·(T/Tnom - 1)
Vth(T) = Vth0 - ΔVth_temp
```

**Saturation Velocity Temperature Dependence:**
```
v_sat(T) = v_sat - at·(T/Tnom - 1)
```

**SPICE Integration:** Temperature scaling is implemented in `BSIM4v5temp()` and applied before each DC operating point calculation. The `kt1l` term provides length-dependent Vth temperature coefficient.

### 7. Matrix Stamping for 8-Node Model with Parasitics

BSIM4v5 implements an 8×8 matrix stamp to include parasitic resistances:

**Matrix Structure:**
```
[G]·[V] = [I]
```

**Conductance Matrix Blocks:**
```
G = [ G_ext    G_coup ]
    [ G_coupᵀ  G_int  ]
```

**External Block (4×4):**
```
G_ext = [ Ydd  0   Yds  0 ]
        [ 0   Ygg  0    0 ]
        [ Ysd  0   Yss  0 ]
        [ 0    0   0   Ybb ]
```

**Coupling Block (4×4):**
```
G_coup = [ -1/Rd  0     0     0    ]
         [ 0    -1/Rg   0     0    ]
         [ 0     0    -1/Rs   0    ]
         [ 0     0     0    -1/Rb  ]
```

**Internal Block (4×4):**
```
G_int = [ 1/Rd+Yd'd' Yd'g'   Yd's'   Yd'b' ]
        [ Yg'd'      1/Rg+Yg'g' Yg's'   Yg'b' ]
        [ Ys'd'      Ys'g'   1/Rs+Ys's' Ys'b' ]
        [ Yb'd'      Yb'g'    Yb's'   1/Rb+Yb'b' ]
```

**SPICE Integration:** This stamp is implemented in `BSIM4v5load()` using the 16 matrix pointers in `BSIM4v5instance`. The `Yij` terms are the standard MOSFET conductances `gm`, `gds`, `gmbs`.

---

## C Implementation

### 1. Core Data Structures for Nanometer Physics

The BSIM4v5 implementation centers on two primary data structures that encapsulate both traditional MOSFET parameters and BSIM4v5-specific nanometer-scale effects.

#### 1.1 The `sBSIM4v5model` Structure

Defined in `bsim4v5def.h`, this structure stores all model-level parameters including BSIM4v5-specific enhancements:

```c
typedef struct sBSIM4v5model {
    /* Device type and version */
    int BSIM4v5type;                    /* NMOS=1, PMOS=-1 - determines polarity */
    double BSIM4v5version;              /* 4.5.0 or 4.6.0 - version tracking */
    
    /* Quantum Mechanical Tunneling Parameters */
    double BSIM4v5aigbacc;              /* A in Igb = A·(Vgb)^B·exp(-C·Tox) */
    double BSIM4v5bigbacc;              /* B exponent for gate-bulk tunneling */
    double BSIM4v5cigbacc;              /* C in exponential for temperature dependence */
    double BSIM4v5aigbinv;              /* Separate parameters for inversion region */
    double BSIM4v5bigbinv;
    double BSIM4v5cigbinv;
    double BSIM4v5aigsd;                /* Gate-to-S/D overlap tunneling */
    double BSIM4v5bigsd;
    double BSIM4v5cigsd;
    
    /* Pocket/Halo Implant Parameters */
    double BSIM4v5dvtshft;              /* Additional Vth shift: ΔVth_pocket = dvtshft */
    double BSIM4v5dvtshfttemp;          /* Temperature coefficient: ×(1 + dtemp·(T/Tnom-1)) */
    double BSIM4v5phigh;                /* phigh in f_pocket = 1 + phigh/Leff - plow/Leff */
    double BSIM4v5plow;                 /* plow in pocket factor calculation */
    
    /* STI Stress Parameters */
    double BSIM4v5sar;                  /* sar in f_STI = 1 + sar/sa + sbr/sb + sdr/sd */
    double BSIM4v5sbr;                  /* Length-direction stress coefficient */
    double BSIM4v5sdr;                  /* Well-edge proximity stress */
    
    /* WPE (Well Proximity Effect) Parameters */
    double BSIM4v5warc;                 /* warc in ΔVth_WPE = warc/sd^1.5 */
    double BSIM4v5wbrc;                 /* wbrc in f_WPE = 1 + wbrc/sd^1.5 */
    
    /* Memory management links */
    struct sBSIM4v5model *BSIM4v5nextModel;  /* Linked list for multiple models */
    sBSIM4v5instance *BSIM4v5instances;      /* Pointer to instance list */
    
    /* Traditional BSIM4 parameters (400+ additional parameters) */
    double BSIM4v5vth0;                 /* Zero-bias threshold voltage */
    double BSIM4v5tox;                  /* Oxide thickness */
    double BSIM4v5u0;                   /* Low-field mobility */
    double BSIM4v5vsat;                 /* Saturation velocity */
    double BSIM4v5dvt0, BSIM4v5dvt1, BSIM4v5dvt2;  /* DIBL coefficients */
    double BSIM4v5eta0, BSIM4v5etab;    /* DIBL voltage coefficients */
    double BSIM4v5k3;                   /* Narrow width coefficient */
    /* ... plus 400+ additional parameters ... */
} BSIM4v5model;
```

#### 1.2 The `sBSIM4v5instance` Structure

This per-device structure contains instance-specific data, state information, and matrix pointers:

```c
typedef struct sBSIM4v5instance {
    /* Terminal Nodes - External (connect to circuit) */
    int BSIM4v5dNode;                   /* Drain node index in SPICE matrix */
    int BSIM4v5gNode;                   /* Gate node index */
    int BSIM4v5sNode;                   /* Source node index */
    int BSIM4v5bNode;                   /* Bulk node index */
    
    /* Internal Parasitic Nodes */
    int BSIM4v5dNodePrime;              /* Internal drain (after Rd) */
    int BSIM4v5sNodePrime;              /* Internal source (after Rs) */
    int BSIM4v5bNodePrime;              /* Internal bulk (after Rbody) */
    int BSIM4v5gNodePrime;              /* Internal gate (after Rgate) */
    
    /* State Vector Allocation - indices into CKTstate arrays */
    int BSIM4v5states[10];              /* Maps mathematical states to SPICE state vectors */
    /* 0: qgs - gate-source charge (∫ig·dt) */
    /* 1: qgd - gate-drain charge */
    /* 2: qgb - gate-bulk charge */
    /* 3: qbd - bulk-drain charge */
    /* 4: qbs - bulk-source charge */
    /* 5: igc - gate-channel tunneling current state */
    /* 6: igd - gate-drain tunneling current */
    /* 7: igs - gate-source tunneling current */
    /* 8: igb - gate-bulk tunneling current */
    /* 9: mode - operating region flag */
    
    /* Voltage/Charge States for Convergence Testing */
    double BSIM4v5vgs_old;              /* Vgs from previous Newton iteration */
    double BSIM4v5vds_old;              /* Vds from previous iteration */
    double BSIM4v5vbs_old;              /* Vbs from previous iteration */
    double BSIM4v5qgs_old;              /* qgs from previous time point */
    double BSIM4v5qgd_old;              /* qgd from previous time point */
    double BSIM4v5qgb_old;              /* qgb from previous time point */
    
    /* SMP Matrix Pointers (16 total for 4×4 conductance matrix) */
    double *BSIM4v5DdPtr;               /* G[dd] = ∂Id/∂Vd - drain self-conductance */
    double *BSIM4v5DgPtr;               /* G[dg] = ∂Id/∂Vg = gm */
    double *BSIM4v5DsPtr;               /* G[ds] = ∂Id/∂Vs = -gds */
    double *BSIM4v5DbPtr;               /* G[db] = ∂Id/∂Vb = gmbs */
    double *BSIM4v5GdPtr;               /* G[gd] = ∂Ig/∂Vd */
    double *BSIM4v5GgPtr;               /* G[gg] = ∂Ig/∂Vg */
    double *BSIM4v5GsPtr;               /* G[gs] = ∂Ig/∂Vs */
    double *BSIM4v5GbPtr;               /* G[gb] = ∂Ig/∂Vb */
    double *BSIM4v5SdPtr;               /* G[sd] = ∂Is/∂Vd = -gds */
    double *BSIM4v5SgPtr;               /* G[sg] = ∂Is/∂Vg = -gm */
    double *BSIM4v5SsPtr;               /* G[ss] = ∂Is/∂Vs */
    double *BSIM4v5SbPtr;               /* G[sb] = ∂Is/∂Vb = -gmbs */
    double *BSIM4v5BdPtr;               /* G[bd] = ∂Ib/∂Vd */
    double *BSIM4v5BgPtr;               /* G[bg] = ∂Ib/∂Vg */
    double *BSIM4v5BsPtr;               /* G[bs] = ∂Ib/∂Vs */
    double *BSIM4v5BbPtr;               /* G[bb] = ∂Ib/∂Vb */
    
    /* Linked list and parent model pointer */
    struct sBSIM4v5instance *BSIM4v5nextInstance;  /* Next instance in model */
    BSIM4v5model *BSIM4v5modPtr;                   /* Pointer to parent model */
    
    /* Operating point variables */
    double BSIM4v5vgs;                  /* Gate-source voltage */
    double BSIM4v5vds;                  /* Drain-source voltage */
    double BSIM4v5vbs;                  /* Bulk-source voltage */
    double BSIM4v5vth;                  /* Calculated threshold voltage */
    double BSIM4v5ids;                  /* Drain current */
    double BSIM4v5ueff;                 /* Effective mobility */
    double BSIM4v5leff;                 /* Effective channel length */
    double BSIM4v5weff;                 /* Effective channel width */
    /* ... additional instance variables ... */
} BSIM4v5instance;
```

### 2. Parameter Binding and Mathematical Transformations

#### 2.1 Parameter Table Definition (`b4v5par.c`)

The parameter binding system maps SPICE input parameters to C structure fields:

```c
/* Layout-Dependent Effects - BSIM4v5 specific */
IOP("sar",    BSIM4v5_SAR,    IF_REAL, "STI stress mobility coefficient"),
IOP("sbr",    BSIM4v5_SBR,    IF_REAL, "Length-direction STI stress"),
IOP("sdr",    BSIM4v5_SDR,    IF_REAL, "Well-edge proximity stress"),
IOP("warc",   BSIM4v5_WARC,   IF_REAL, "WPE Vth shift coefficient"),
IOP("wbrc",   BSIM4v5_WBRC,   IF_REAL, "WPE mobility coefficient"),

/* Quantum Tunneling Parameters */
IOP("aigbacc", BSIM4v5_AIGBACC, IF_REAL, "Gate accumulation tunneling prefactor"),
IOP("bigbacc", BSIM4v5_BIGBACC, IF_REAL, "Gate accumulation tunneling exponent"),
IOP("cigbacc", BSIM4v5_CIGBACC, IF_REAL, "Gate accumulation tunneling temp coeff"),
IOP("aigbinv", BSIM4v5_AIGBINV, IF_REAL, "Gate inversion tunneling prefactor"),
IOP("bigbinv", BSIM4v5_BIGBINV, IF_REAL, "Gate inversion tunneling exponent"),
IOP("cigbinv", BSIM4v5_CIGBINV, IF_REAL, "Gate inversion tunneling temp coeff"),
IOP("aigsd",   BSIM4v5_AIGSD,   IF_REAL, "Gate-S/D overlap tunneling prefactor"),
IOP("bigsd",   BSIM4v5_BIGSD,   IF_REAL, "Gate-S/D overlap tunneling exponent"),
IOP("cigsd",   BSIM4v5_CIGSD,   IF_REAL, "Gate-S/D overlap tunneling temp coeff"),

/* Pocket/Halo Implant Parameters */
IOP("dvtshft", BSIM4v5_DVTSHFT, IF_REAL, "Pocket implant Vth shift"),
IOP("dvtshfttemp", BSIM4v5_DVTSHFTTEMP, IF_REAL, "Pocket Vth temp coefficient"),
IOP("phigh",   BSIM4v5_PHIGH,   IF_REAL, "Peak pocket concentration"),
IOP("plow",    BSIM4v5_PLOW,    IF_REAL, "Background concentration"),
```

#### 2.2 Effective Geometry Calculations (`b4v5set.c`)

The setup function computes effective dimensions and applies layout-dependent effects:

```c
int BSIM4v5setup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states)
{
    BSIM4v5model *model = (BSIM4v5model *)inModel;
    BSIM4v5instance *here;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (here = model->BSIM4v5instances; here != NULL; 
             here = here->BSIM4v5nextInstance) {
            
            /* STI Stress Effect on Mobility */
            double stress_factor = 1.0;
            if (model->BSIM4v5sarGiven && model->BSIM4v5sbrGiven && 
                model->BSIM4v5sdrGiven) {
                /* f_STI = 1 + sar/sa + sbr/sb + sdr/sd */
                stress_factor = 1.0 + model->BSIM4v5sar/MAX(here->BSIM4v5sa, 1e-9)
                                    + model->BSIM4v5sbr/MAX(here->BSIM4v5sb, 1e-9)
                                    + model->BSIM4v5sdr/MAX(here->BSIM4v5sd, 1e-9);
                here->BSIM4v5u0eff = model->BSIM4v5u0 * stress_factor;
            }
            
            /* WPE Effect on Threshold Voltage */
            double wpe_vth_shift = 0.0;
            if (model->BSIM4v5warcGiven) {
                /* ΔVth_WPE = warc / sd^1.5 */
                wpe_vth_shift = model->BSIM4v5warc / pow(here->BSIM4v5sd, 1.5);
                here->BSIM4v5vth0 = model->BSIM4v5vth0 + wpe_vth_shift;
            }
            
            /* Effective Dimensions with Quantum Correction */
            /* Leff = L - 2·dlc + dlc·exp(-L/llc) */
            here->BSIM4v5leff = here->BSIM4v5l - 2.0 * model->BSIM4v5dlc
                               + model->BSIM4v5dlc * exp(-here->BSIM4v5l/model->BSIM4v5llc);
            
            /* Weff = W - 2·dwc + dwc·exp(-W/wwc) */
            here->BSIM4v5weff = here->BSIM4v5w - 2.0 * model->BSIM4v5dwc
                               + model->BSIM4v5dwc * exp(-here->BSIM4v5w/model->BSIM4v5wwc);
            
            /* Allocate state vector indices for charges */
            here->BSIM4v5states[0] = *states; (*states)++;  /* qgs */
            here->BSIM4v5states[1] = *states; (*states)++;  /* qgd */
            here->BSIM4v5states[2] = *states; (*states)++;  /* qgb */
            here->BSIM4v5states[3] = *states; (*states)++;  /* qbd */
            here->BSIM4v5states[4] = *states; (*states)++;  /* qbs */
            
            /* Allocate matrix pointers for 8×8 stamp */
            BSIM4v5setupMatrix(matrix, here);
        }
    }
    return OK;
}
```

#### 2.3 Temperature Scaling (`b4v5temp.c`)

Temperature effects are computed separately for reusability:

```c
int BSIM4v5temperature(GENmodel *inModel, CKTcircuit *ckt)
{
    BSIM4v5model *model = (BSIM4v5model *)inModel;
    BSIM4v5instance *here;
    
    for (; model != NULL; model = model->BSIM4v5nextModel) {
        for (here = model->BSIM4v5instances; here != NULL; 
             here = here->BSIM4v5nextInstance) {
            
            /* Convert to Kelvin */
            double T = here->BSIM4v5temp + CONSTCtoK;
            double TNOM = model->BSIM4v5tnom + CONSTCtoK;
            double Tratio = T / TNOM;
            
            /* Mobility Temperature Dependence: μ(T) = μ0·(T/Tnom)^(-ute) */
            here->BSIM4v5u0temp = model->BSIM4v5u0 * pow(Tratio, -model->BSIM4v5ute);
            
            /* Threshold Voltage Temperature Scaling */
            /* ΔVth_temp = kt1·(T/Tnom - 1) + kt1l/Leff·(T/Tnom - 1) */
            double dVth_temp = model->BSIM4v5kt1 * (Tratio - 1.0)
                             + model->BSIM4v5kt1l / here->BSIM4v5leff * (Tratio - 1.0);
            here->BSIM4v5vth0temp = model->BSIM4v5vth0 - dVth_temp;
            
            /* Saturation Velocity Temperature Dependence */
            /* v_sat(T) = v_sat - at·(T/Tnom - 1) */
            here->BSIM4v5vsattemp = model->BSIM4v5vsat - model->BSIM4v5at * (Tratio - 1.0);
            
            /* Pocket implant temperature dependence */
            if (model->BSIM4v5dvtshfttempGiven) {
                here->BSIM4v5dvtshfttemp = model->BSIM4v5dvtshft 
                                         * (1.0 + model->BSIM4v5dvtshfttemp * (Tratio - 1.0));
            }
        }
    }
    return OK;
}
```

### 3. Quantum Mechanical Tunneling Implementation

#### 3.1 Gate Leakage Current Calculation

The tunneling currents are computed in the load function:

```c
/* In BSIM4v5load() function in b4v5ld.c */
if (model->BSIM4v5igcMod) {
    /* Gate-to-Channel Tunneling (Inversion) */
    /* Igc = aigbinv·(Tox·V_ox)^bigbinv·exp(-cigbinv·Tox)·Weff·Leff */
    double Vox_inv = model->BSIM4v5tox * (vgs - vth);
    double Igc = model->BSIM4v5aigbinv 
                 * pow(Vox_inv, model->BSIM4v5bigbinv)
                 * exp(-model->BSIM4v5cigbinv * model->BSIM4v5tox)
                 * here->BSIM4v5weff * here->BSIM4v5leff;
    
    /* Gate-to-S/D Overlap Tunneling */
    double Vgd_ov = MAX(vgd, 0.1);  /* Prevent singularity */
    double Igd = model->BSIM4v5aigsd
                 * pow(Vgd_ov, model->BSIM4v5bigsd)
                 * exp(-model->BSIM4v5cigsd * model->BSIM4v5tox)
                 * here->BSIM4v5weff * model->BSIM4v5dlc;
    
    /* Gate-to-Bulk Tunneling (Accumulation) */
    double Vgb_acc = MAX(vgb, 0.1);
    double Igb = model->BSIM4v5aigbacc
                 * pow(Vgb_acc, model->BSIM4v5bigbacc)
                 * exp(-model->BSIM4v5cigbacc * model->BSIM4v5tox)
                 * here->BSIM4v5weff * here->BSIM4v5leff;
    
    /* Store currents in instance */
    here->BSIM4v5igc = Igc;
    here->BSIM4v5igd = Igd;
    here->BSIM4v5igb = Igb;
    
    /* Add to RHS vector */
    ckt->CKTrhs[here->BSIM4v5gNode] -= (Igc + Igd + Igb);
    ckt->CKTrhs[here->BSIM4v5dNode] += Igd;
    ckt->CKTrhs[here->BSIM4v5bNode] += Igb;
    
    /* Stamp conductances to matrix */
    double g_eltd = model->BSIM4v5aigbinv * model->BSIM4v5bigbinv 
                    * pow(Vox_inv, model->BSIM4v5bigbinv - 1.0)
                    * exp(-model->BSIM4v5cigbinv * model->BSIM4v5tox)
                    * here->BSIM4v5weff * here->BSIM4v5leff;
    *(here->BSIM4v5GgPtr) += g_eltd;
}
```

### 4. Advanced Mobility Degradation Implementation

#### 4.1 Mobility Calculation in Load Function

```c
/* In BSIM4v5load() function */
/* Base Mobility with Vertical Field */
/* μ_base = μ0 / [1 + ua·E_eff + ub·E_eff²] */
double Eeff = (vgs - vth) / (model->BSIM4v5tox * 1e9);  /* MV/cm */
double mu_base = model->BSIM4v5u0 
                 / (1.0 + model->BSIM4v5ua * Eeff 
                        + model->BSIM4v5ub * Eeff * Eeff);

/* Velocity Saturation Effect */
/* f_vsat = 1 / [1 + (E_eff/E_sat)^β]^(1/β) */
double Esat = 2.0 * model->BSIM4v5vsat / mu_base;
double mu_vsat = mu_base / pow(1.0 + pow(Eeff/Esat, model->BSIM4v5beta), 
                               1.0/model->BSIM4v5beta);

/* Pocket/Halo Implant Effect */
/* f_pocket = 1 + phigh/Leff - plow/Leff */
double pocket_factor = 1.0 + model->BSIM4v5phigh/here->BSIM4v5leff
                         - model->BSIM4v5plow/here->BSIM4v5leff;
double mu_pocket = mu_vsat * pocket_factor;

/* Final Effective Mobility (includes STI stress from setup) */
here->BSIM4v5ueff = mu_pocket * stress_factor;  /* stress_factor from setup */
```

### 5. Continuous Current Implementation

#### 5.1 Current Calculation with Smooth Transitions

```c
/* In BSIM4v5load() function */
/* Subthreshold Current */
/* Ids_sub = I_sub·exp((Vgs - Vth)/(n·Vt))·(1 - exp(-Vds/Vt)) */
double n = 1.0 + model->BSIM4v5nfactor 
           + model->BSIM4v5cdsc * exp(-vds/model->BSIM4v5voff)
           / model->BSIM4v5cox;
double Vt = model->BSIM4v5vtm;  /* Thermal voltage */
double Ids_sub = model->BSIM4v5isub 
                 * exp((vgs - vth)/(n * Vt))
                 * (1.0 - exp(-vds/Vt));

/* Strong Inversion Current */
/* β = μ_eff·Cox·Weff/Leff */
double beta = here->BSIM4v5ueff * model->BSIM4v5cox 
              * here->BSIM4v5weff / here->BSIM4v5leff;
double Vdsat = (vgs - vth) / model->BSIM4v5kappa;
double Ids_lin = beta * ((vgs - vth) * vds - 0.5 * vds * vds);
double Ids_sat = 0.5 * beta * pow(vgs - vth, 2.0) 
                 * (1.0 + model->BSIM4v5lambda * vds);

/* Smooth Blending Function */
double delta = 0.1;  /* Smoothing parameter */
double Vds_eff = 0.5 * (vds + Vdsat 
                       - sqrt(pow(vds - Vdsat, 2.0) + 4.0 * delta * delta));
double Ids = (Ids_lin * (1.0 - Vds_eff/Vdsat) 
             + Ids_sat * (Vds_eff/Vdsat)) 
             / (1.0 + Vds_eff/model->BSIM4v5vmax/here->BSIM4v5leff);

/* Final Continuous Current with tanh blending */
/* α = 0.5·[1 + tanh((Vgs - Vth)/(δ·Vt))] */
double alpha = 0.5 * (1.0 + tanh((vgs - vth)/(delta * Vt)));
here->BSIM4v5ids = alpha * Ids + (1.0 - alpha) * Ids_sub;
```

### 6. Newton-Raphson Limiting and Source/Drain Swap

#### 6.1 Voltage Limiting Implementation

```c
/* DEVfetlim function used in BSIM4v5load() */
double DEVfetlim(double vnew, double vold, double vcrit) {
    double delta = vnew - vold;
    
    if ((vnew >= 0) && (vold >= 0)) {
        if