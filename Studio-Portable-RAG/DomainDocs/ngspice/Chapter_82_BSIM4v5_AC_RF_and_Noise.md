# BSIM4v5: RF Modeling, Capacitance, and Noise Analysis

_Generated 2026-04-12 14:19 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim4v5/b4v5noi.c`

# Chapter: BSIM4v5: RF Modeling, Capacitance, and Noise Analysis

## Technical Introduction

The BSIM4v5 model in Ngspice extends the industry-standard BSIM4 framework with enhanced radio-frequency (RF), capacitance, and noise modeling capabilities essential for modern sub-100nm CMOS design. This chapter details the implementation of three critical analysis modes within the Ngspice simulation kernel. The `b4v5acld.c` file implements small-signal AC analysis by constructing the complex admittance matrix **Y(ω) = G + jωC** that represents the linearized MOSFET behavior around a DC operating point, including gate resistance effects and substrate network parasitics. For stability and frequency response analysis, `b4v5pzld.c` provides pole-zero extraction by stamping the **G + sC** matrix into the circuit's system determinant for s-domain root finding. The comprehensive noise analysis in `b4v5noi.c` implements configurable thermal, flicker, and induced gate noise models with full correlation handling, supporting both traditional BSIM4 formulations and BSIM4v5-specific enhancements like geometry-scaled thermal noise and unified flicker models. Together, these files enable Ngspice to perform complete RF characterization of advanced CMOS devices, from S-parameter extraction to noise figure calculation, while maintaining compatibility with the broader SPICE simulation infrastructure.

## Mathematical Formulation

### 1. SMALL-SIGNAL AC MATRIX STAMPING (`b4v5acld.c`)

#### 1.1 Core Complex Admittance Formulation

The BSIM4v5 small-signal model generates a 4×4 complex admittance matrix **Y(ω) = G + jωC** where:

```
Y(ω) = 
[Ydd Ydg Yds Ydb]
[Ygd Ygg Ygs Ygb]
[Ysd Ysg Yss Ysb]
[Ybd Ybg Ybs Ybb]
```

**Intrinsic Device Stamp (Without Parasitics):**

For the intrinsic MOSFET (nodes: G', D', S', B'), the admittance elements are:

```
Yd'd' = gds + jω(Cgd + Cbd + Cds)
Yd'g' = gm - jωCgd
Yd's' = -(gds + gm + gmb) - jω(Cgs + Cds + Cbs)
Yd'b' = gmb - jωCbd

Yg'd' = -jωCgd
Yg'g' = jω(Cgs + Cgd + Cgb)
Yg's' = -jωCgs
Yg'b' = -jωCgb

Ys'd' = -gds - jωCds
Ys'g' = -gm - jωCgs
Ys's' = gds + gm + gmb + jω(Cgs + Cds + Cbs)
Ys'b' = -gmb - jωCbs

Yb'd' = -gmb - jωCbd
Yb'g' = -jωCgb
Yb's' = gmb - jωCbs
Yb'b' = jω(Cbd + Cbs + Cgb)
```

#### 1.2 Gate Resistance Implementation

BSIM4v5 implements gate resistance **Rg** as a series element between external gate node G and internal gate node G'. The stamp adds:

```
External Gate Resistance Stamp:
Ygg += 1/Rg
Ygg' = -1/Rg
Yg'g = -1/Rg
Yg'g' += 1/Rg
```

#### 1.3 Substrate Network Implementation

BSIM4v5 includes a comprehensive substrate network with **Rsub**, **Csub** elements:

```
Substrate Network Stamp (5-node model):
Ybb_int += 1/Rb + jωCb
Ybb_ext += 1/Rb + jωCb
Ybb_int_ext = -1/Rb
Ybb_ext_int = -1/Rb
```

### 2. POLE-ZERO ANALYSIS (`b4v5pzld.c`)

#### 2.1 Small-Signal Transfer Function Extraction

The pole-zero load function computes the linearized system for **s-domain** analysis:

```
H(s) = [C·s + G]^{-1}·B
```

### 3. NOISE ANALYSIS (`b4v5noi.c`)

#### 3.1 Noise Model Selector Architecture

BSIM4v5 implements configurable noise models through **tnoimod** and **fnoimod** parameters:

```c
/* Noise model selector variables */
typedef enum {
    B4V5_TNOIMOD_BSIM4 = 0,     /* Standard BSIM4 thermal noise */
    B4V5_TNOIMOD_BSIM4v5 = 1,   /* Enhanced v5 thermal noise */
    B4V5_TNOIMOD_IGNOISE = 2,   /* Include induced gate noise */
    B4V5_TNOIMOD_HOTCARRIER = 3 /* Hot carrier noise */
} B4v5TnoiMod;

typedef enum {
    B4V5_FNOIMOD_BSIM4 = 0,     /* Standard flicker noise */
    B4V5_FNOIMOD_BSIM4v5 = 1,   /* Enhanced v5 flicker noise */
    B4V5_FNOIMOD_UNIFIED = 2    /* Unified flicker/thermal */
} B4v5FnoiMod;
```

#### 3.2 Thermal Noise Formulation

**Channel Thermal Noise Power Spectral Density:**

```
S_id(f) = 4kT·γ·gds0·Δf
```

where the **γ factor** is bias-dependent:

```
γ = 
{ 
    (gds/gds0) for Vds = 0 (linear)
    (2/3)·α for saturation (α = 1 + Vds·λ)
}
```

**BSIM4v5 Specific Enhancement:**
```
γ_v5 = γ_bsim4 · [1 + (Leff/L0)^β · (Vds/Vdsat)^δ]
```

#### 3.3 Induced Gate Noise (IGN) Implementation

**Induced Gate Noise Power Spectral Density:**

```
S_ig(f) = 4kT·δ·(ω²Cgg²)/(5gds0)·Δf
```

**Correlation with Channel Noise:**
```
ρ = j·κ·(ωCgg/gds0)
```

where:
```
δ = n·(1 + β·(Vds/Vdsat))
κ = √(δ/5γ)
```

#### 3.4 Flicker (1/f) Noise Implementation

**Unified Flicker Noise Model (fnoimod = 2):**

```
S_id_flicker(f) = (KF·Id^AF)/(Cox·Leff·Weff·f^EF)·Δf
                + (NOIA·kT·gm²)/(Cox·Leff·Weff·f)·Δf
```

#### 3.5 Noise Source Stamping Matrix

**Correlated Noise Source Representation:**

Two correlated noise sources between drain and source:

```
i_nd = √(S_id)·w1 + √(S_corr)·w2
i_ng = √(S_ig)·w2
```

where w1, w2 are uncorrelated white noise sources.

**Stamp into Noise Correlation Matrix:**

```
C = [S_id     S_cross]
    [S_cross* S_ig   ]
```

#### 3.6 Gate/Substrate Resistance Noise

**Gate Resistance Thermal Noise:**
```
S_vg = 4kTRg·Δf
```

**Substrate Resistance Noise Network:**
```
S_vb = 4kTRb·Δf
S_vsub = 4kTRsub·Δf
```

### 4. MATHEMATICAL DERIVATIONS

#### 4.1 Induced Gate Noise Correlation Proof

The correlation between channel noise **i_nd** and gate noise **i_ng** is derived from the impedance field method:

```
ρ = ⟨i_nd·i_ng*⟩ / √(⟨|i_nd|²⟩·⟨|i_ng|²⟩)
  = ∫₀ᴸ (∂Q/∂x)·(∂V/∂x) dx / [√(∫₀ᴸ (∂Q/∂x)² dx · ∫₀ᴸ (∂V/∂x)² dx)]
```

For a MOSFET in saturation:

```
ρ ≈ j·(ωCgg/gds0)·√(n/(5γ))·(1 + β·Vds/Vdsat)
```

#### 4.2 Frequency-Dependent Noise Integration

The total output noise voltage at frequency **f**:

```
Vn_out²(f) = ∫ |H(jω)|²·S_id(f) df
            + ∫ |H_g(jω)|²·S_ig(f) df
            + 2·Re[∫ H(jω)·H_g*(jω)·S_cross(f) df]
```

where **H(jω)** is the transfer function from noise source to output.

### 5. COMPUTATIONAL ALGORITHMS

#### 5.1 AC Matrix Construction Algorithm

```
Algorithm: BSIM4v5_AC_Matrix_Stamp
Input: Model pointer, circuit, frequency ω
Output: Stamped complex admittance matrix Y(ω)

1. FOR each model in linked list
2.   FOR each instance in model
3.     Compute small-signal parameters at DC op point
4.     Calculate transcapacitances Cgg, Cgd, Cgs, Cgb
5.     IF gate resistance enabled
6.       Stamp external gate node conductance 1/Rg
7.       Stamp internal gate node admittance jω(Cgg+Cgd+Cgs+Cgb)
8.       Stamp coupling terms -1/Rg
9.     ELSE
10.      Stamp gate node admittance directly
11.    ENDIF
12.    Stamp drain node: gds + jω(Cgd+Cbd+Cds)
13.    Stamp source node: -(gds+gm+gmb) - jω(Cgs+Cds+Cbs)
14.    Stamp bulk node: jω(Cgb+Cbd+Cbs) + gbulk
15.    Stamp cross terms with appropriate signs
16.  ENDFOR
17. ENDFOR
```

#### 5.2 Noise Spectral Density Computation Algorithm

```
Algorithm: BSIM4v5_Noise_Computation
Input: Instance, temperature T, frequency f, bias voltages
Output: Sid, Sig, ρ

1. Compute zero-bias conductance gds0
2. SWITCH tnoimod
3.   CASE BSIM4:
4.     γ = γ0 (constant)
5.     Sid = 4kTγgds0
6.   CASE BSIM4v5:
7.     Compute Leff/L0 scaling factor
8.     Compute Vds/Vdsat ratio
9.     γ = γ0·[1 + (Leff/L0)^β·(Vds/Vdsat)^δ]
10.    Sid = 4kTγgds0
11.  CASE IGNOISE:
12.    Compute Sid as above
13.    Compute gate capacitance Cgg
14.    Compute δ = n·(1 + β·Vds/Vdsat)
15.    Sig = 4kTδ·(ω²Cgg²)/(5gds0)
16.    Compute κ = √(δ/(5γ))
17.    ρ = j·κ·(ωCgg/gds0)
18. ENDSWITCH
19. Add flicker noise: Sid += KF·Id^AF/(Cox·Leff·Weff·f^EF)
20. RETURN Sid, Sig, ρ
```

## C Implementation

This section details the Ngspice C implementation of the BSIM4v5 model's frequency-domain and noise analysis, mapping the mathematical formulations directly to the source code structures and algorithms.

### 1. Core Data Structures for RF and Noise Analysis

The BSIM4v5 implementation uses two primary data structures defined in `bsim4v5def.h` that store all parameters necessary for AC and noise computations.

#### 1.1 Instance Structure (`sB4v5instance`)

The instance structure contains both operating point data and matrix pointers for circuit stamping:

```c
typedef struct sB4v5instance {
    /* Circuit Node Indices */
    int B4v5dNode;          /* External drain node */
    int B4v5gNode;          /* External gate node */
    int B4v5sNode;          /* External source node */
    int B4v5bNode;          /* External bulk node */
    int B4v5dPrimeNode;     /* Internal drain node (after Rd) */
    int B4v5gPrimeNode;     /* Internal gate node (after Rg) */
    int B4v5sPrimeNode;     /* Internal source node (after Rs) */
    int B4v5bPrimeNode;     /* Internal bulk node (after Rb) */
    
    /* AC Matrix Pointers - Map to Y(ω) matrix elements */
    double *B4v5DdPtr;      /* Ydd: [D,D] position */
    double *B4v5DgPtr;      /* Ydg: [D,G] position */
    double *B4v5DsPtr;      /* Yds: [D,S] position */
    double *B4v5DbPtr;      /* Ydb: [D,B] position */
    double *B4v5GgExtPtr;   /* Ygg_ext: External gate self-term */
    double *B4v5GgIntPtr;   /* Ygg_int: Internal gate self-term */
    double *B4v5GgIntExtPtr;/* Yg_int_g_ext: Coupling term */
    double *B4v5GdIntPtr;   /* Yg_int_d: Internal gate to drain */
    double *B4v5GsIntPtr;   /* Yg_int_s: Internal gate to source */
    double *B4v5GbIntPtr;   /* Yg_int_b: Internal gate to bulk */
    
    /* Small-Signal Parameters (computed during DC) */
    double B4v5gm;          /* Transconductance gm = ∂Id/∂Vgs */
    double B4v5gds;         /* Drain conductance gds = ∂Id/∂Vds */
    double B4v5gmb;         /* Bulk transconductance gmb = ∂Id/∂Vbs */
    double B4v5cgg;         /* Gate capacitance Cgg */
    double B4v5cgd;         /* Gate-drain capacitance Cgd */
    double B4v5cgs;         /* Gate-source capacitance Cgs */
    double B4v5cgb;         /* Gate-bulk capacitance Cgb */
    
    /* Noise-Specific Parameters */
    double B4v5gamma0;      /* Thermal noise coefficient γ₀ */
    double B4v5npart;       /* Gate noise partition factor n */
    double B4v5npartbeta;   /* Gate noise bias dependence β */
    double B4v5corrcoeff;   /* Noise correlation coefficient ρ */
    
    /* Model Selector Flags */
    int B4v5tnoimod;        /* Thermal noise model selector */
    int B4v5fnoimod;        /* Flicker noise model selector */
    int B4v5rgateMod;       /* Gate resistance model (0=off, 1=on) */
    
    /* Physical Geometry Parameters */
    double B4v5leff;        /* Effective channel length */
    double B4v5weff;        /* Effective channel width */
    double B4v5cox;         /* Oxide capacitance per unit area */
    double B4v5ueff;        /* Effective carrier mobility */
    double B4v5vdsat;       /* Saturation voltage Vdsat */
    
    /* Parasitic Resistances */
    double B4v5rgate;       /* Gate resistance Rg */
    double B4v5rbulk;       /* Bulk resistance Rb */
    double B4v5rsub;        /* Substrate resistance Rsub */
    
    /* Noise Matrix Offsets */
    int B4v5dOffset;        /* Drain noise source in correlation matrix */
    int B4v5gOffset;        /* Gate noise source in correlation matrix */
    int B4v5corrOffset;     /* Correlation term offset */
    
    /* Linked list pointers */
    struct sB4v5instance *B4v5nextInstance;
    B4v5model *B4v5modPtr;
} B4v5instance;
```

#### 1.2 Model Structure (`sB4v5model`)

The model structure contains process parameters that are shared across all instances:

```c
typedef struct sB4v5model {
    /* Process Technology Parameters */
    double B4v5tox;         /* Gate oxide thickness */
    double B4v5xj;          /* Junction depth */
    double B4v5nch;         /* Channel doping concentration */
    double B4v5vth0;        /* Zero-bias threshold voltage */
    
    /* Flicker Noise Parameters */
    double B4v5noia;        /* Unified flicker noise parameter A */
    double B4v5noib;        /* Unified flicker noise parameter B */
    double B4v5noic;        /* Unified flicker noise parameter C */
    double B4v5kf;          /* Traditional flicker coefficient */
    double B4v5af;          /* Drain current exponent */
    double B4v5ef;          /* Frequency exponent */
    
    /* Thermal Noise Enhancement Parameters */
    double B4v5l0;          /* Reference length for γ scaling */
    double B4v5beta;        /* Length scaling exponent */
    double B4v5delta;       /* Vds scaling exponent */
    
    /* Geometry Scaling Parameters */
    double B4v5dl;          /* Length reduction for Leff */
    double B4v5dw;          /* Width reduction for Weff */
    double B4v5ll;          /* Length scaling parameter */
    double B4v5lw;          /* Width scaling parameter */
    
    /* Linked list structure */
    struct sB4v5model *B4v5nextModel;
    B4v5instance *B4v5instances;
} B4v5model;
```

### 2. AC Matrix Stamping Implementation (`b4v5acld.c`)

The `B4v5acLoad()` function implements the complex admittance matrix **Y(ω) = G + jωC** stamping for small-signal AC analysis.

#### 2.1 Core Stamping Algorithm

```c
int B4v5acLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    B4v5model *model;
    B4v5instance *here;
    
    for(model = (B4v5model*)inModel; model != NULL; 
        model = model->B4v5nextModel) {
        
        for(here = model->B4v5instances; here != NULL;
            here = here->B4v5nextInstance) {
            
            /* Extract pre-computed small-signal parameters */
            double gdrain = *(here->B4v5drainConductance);
            double gsource = *(here->B4v5sourceConductance);
            double gbulk = *(here->B4v5bulkConductance);
            
            /* Get transcapacitances from DC operating point */
            double cggb = here->B4v5cggb;
            double cgdb = here->B4v5cgdb;
            double cgsb = here->B4v5cgsb;
            
            /* Compute jωC terms */
            double omega = ckt->CKTomega;
            double xgs = omega * cgsb;  /* jωCgs */
            double xgd = omega * cgdb;  /* jωCgd */
            double xgb = omega * cggb;  /* jωCgb */
            
            /* Stamp Intrinsic Y-Matrix Elements */
            
            /* Drain Row: Ydd = gds + jω(Cgd + Cbd + Cds) */
            *(here->B4v5DdPtr) += gdrain + xgd + omega * here->B4v5cddb;
            
            /* Ydg = gm - jωCgd */
            *(here->B4v5DgPtr) += here->B4v5gm - xgd;
            
            /* Yds = -(gds + gm + gmb) - jω(Cgs + Cds + Cbs) */
            *(here->B4v5DsPtr) += -(gdrain + here->B4v5gm + here->B4v5gmb) 
                                 - xgd - omega * here->B4v5cdsb;
            
            /* Ydb = gmb - jωCbd */
            *(here->B4v5DbPtr) += here->B4v5gmb - omega * here->B4v5cbdb;
            
            /* Gate Resistance Handling */
            if(here->B4v5rgateMod == 1) {
                /* External gate node: Ygg_ext += 1/Rg */
                *(here->B4v5GgExtPtr) += 1.0 / here->B4v5rgate;
                
                /* Internal gate node: Ygg_int += 1/Rg + jω(Cgg + Cgd + Cgs + Cgb) */
                *(here->B4v5GgIntPtr) += -1.0 / here->B4v5rgate 
                                        + xgs + xgd + xgb;
                
                /* Coupling terms: Yg_int_g_ext = Yg_ext_g_int = -1/Rg */
                *(here->B4v5GgIntExtPtr) += -1.0 / here->B4v5rgate;
                
                /* Internal gate to other nodes */
                *(here->B4v5GdIntPtr) += -xgd;      /* Yg_int_d = -jωCgd */
                *(here->B4v5GsIntPtr) += -xgs;      /* Yg_int_s = -jωCgs */
                *(here->B4v5GbIntPtr) += -xgb;      /* Yg_int_b = -jωCgb */
            } else {
                /* No gate resistance: stamp directly to external gate */
                *(here->B4v5GgPtr) += xgs + xgd + xgb;
                *(here->B4v5GdPtr) += -xgd;
                *(here->B4v5GsPtr) += -xgs;
                *(here->B4v5GbPtr) += -xgb;
            }
            
            /* Complete remaining matrix stamps for source and bulk rows */
            /* ... */
        }
    }
    return OK;
}
```

#### 2.2 Mathematical Mapping to Code

The C implementation directly maps to the mathematical formulation:

1. **Conductance Matrix G**: Stored in `here->B4v5gm`, `here->B4v5gds`, `here->B4v5gmb`
2. **Capacitance Matrix C**: Stored in `here->B4v5cgg`, `here->B4v5cgd`, etc.
3. **Frequency Scaling**: `ckt->CKTomega` provides ω for jωC terms
4. **Matrix Stamp Locations**: Each pointer (`B4v5DdPtr`, `B4v5DgPtr`, etc.) corresponds to a specific position in the circuit matrix

### 3. Pole-Zero Analysis Implementation (`b4v5pzld.c`)

The pole-zero load function handles s-domain analysis by stamping **G + sC** matrices.

#### 3.1 s-Domain Matrix Stamping

```c
int B4v5pzLoad(GENmodel *inModel, CKTcircuit *ckt, SPcomplex *s)
{
    B4v5model *model;
    B4v5instance *here;
    
    for(model = (B4v5model*)inModel; model != NULL; 
        model = model->B4v5nextModel) {
        
        for(here = model->B4v5instances; here != NULL;
            here = here->B4v5nextInstance) {
            
            /* Stamp conductance matrix G */
            *(here->B4v5DdPtr) += here->B4v5gd;      /* gds */
            *(here->B4v5DgPtr) += here->B4v5gm;      /* gm */
            *(here->B4v5DsPtr) += -(here->B4v5gd + here->B4v5gm + here->B4v5gmb);
            *(here->B4v5DbPtr) += here->B4v5gmb;     /* gmb */
            
            /* Stamp sC matrix (s = σ + jω) */
            double s_real = s->real;
            double s_imag = s->imag;
            
            /* Drain self-term: s·Cdd */
            *(here->B4v5DdPtr) += s_real * here->B4v5cdd;
            *(here->B4v5DdPtr) += s_imag * here->B4v5cdd;
            
            /* Drain-Gate coupling: s·Cdg */
            *(here->B4v5DgPtr) += s_real * here->B4v5cdg;
            *(here->B4v5DgPtr) += s_imag * here->B4v5cdg;
            
            /* Gate resistance in s-domain */
            if(here->B4v5rgateMod == 1) {
                /* Real part: 1/Rg */
                *(here->B4v5GgExtPtr) += 1.0 / here->B4v5rgate;
                *(here->B4v5GgIntPtr) += -1.0 / here->B4v5rgate;
                *(here->B4v5GgIntExtPtr) += -1.0 / here->B4v5rgate;
                
                /* Complex part: s·Cgg */
                *(here->B4v5GgIntPtr) += s_real * (here->B4v5cgg + here->B4v5cgtot);
                *(here->B4v5GgIntPtr) += s_imag * (here->B4v5cgg + here->B4v5cgtot);
            }
        }
    }
    return OK;
}
```

### 4. Noise Analysis Implementation (`b4v5noi.c`)

The noise implementation uses configurable models selected via `tnoimod` and `fnoimod` parameters.

#### 4.1 Thermal Noise Computation

```c
void B4v5thermalNoise(B4v5instance *here, double temp, 
                      double *Sid, double *Sig, double *rho)
{
    double gds0 = here->B4v5gds0;  /* Zero-bias drain conductance */
    
    switch(here->B4v5tnoimod) {
        case B4V5_TNOIMOD_BSIM4:
            /* Standard BSIM4: S_id(f) = 4kT·γ₀·gds0 */
            *Sid = 4.0 * CONSTboltz * temp * here->B4v5gamma0 * gds0;
            break;
            
        case B4V5_TNOIMOD_BSIM4v5:
            /* Enhanced BSIM4v5 with geometry scaling */
            double T0 = here->B4v5ueff * here->B4v5leff;
            double T1 = here->B4v5vds / here->B4v5vdsat;
            double T2 = pow(here->B4v5leff / here->B4v5l0, here->B4v5beta);
            
            /* γ = γ₀·[1 + (Leff/L₀)^β·(Vds/Vdsat)^δ] */
            double gamma = here->B4v5gamma0 * 
                          (1.0 + T2 * pow(T1, here->B4v5delta));
            
            *Sid = 4.0 * CONSTboltz * temp * gamma * gds0;
            break;
            
        case B4V5_TNOIMOD_IGNOISE:
            /* Include induced gate noise */
            *Sid = 4.0 * CONSTboltz * temp * here->B4v5gamma0 * gds0;
            
            /* Compute induced gate noise: S_ig(f) = 4kT·δ·(ω²Cgg²)/(5gds0) */
            double npart = here->B4v5npart;
            double npartbeta = here->B4v5npartbeta;
            double delta = npart * (1.0 + npartbeta * T1);
            
            /* Note: ω is provided by caller for frequency-dependent calculation */
            *Sig = 4.0 * CONSTboltz * temp * delta * 
                   (omega * omega * here->B4v5cgg * here->B4v5cgg) / 
                   (5.0 * gds0);
            
            /* Correlation coefficient: ρ = j·κ·(ωCgg/gds0) */
            double kappa = sqrt(delta / (5.0 * here->B4v5gamma0));
            *rho = kappa * (omega * here->B4v5cgg / gds0);
            break;
    }
}
```

#### 4.2 Flicker Noise Implementation

```c
void B4v5flickerNoise(B4v5instance *here, double freq, 
                      double *Sid_flicker)
{
    double id = here->B4v5id;
    double gm = here->B4v5gm;
    double cox = here->B4v5cox;
    double area = here->B4v5leff * here->B4v5weff;
    
    switch(here->B4v5fnoimod) {
        case B4V5_FNOIMOD_BSIM4:
            /* Traditional: S_id = KF·Id^AF/(Cox·Leff·Weff·f^EF) */
            *Sid_flicker = here->B4v5kf * pow(fabs(id), here->B4v5af) /
                          (cox * area * pow(freq, here->B4v5ef));
            break;
            
        case B4V5_FNOIMOD_BSIM4v5:
            /* Unified model: S_id = (NOIA·kT·gm² + NOIB·Id·gm + NOIC·Id²)/(Cox·area·f) */
            double noia = here->B4v5noia;
            double noib = here->B4v5noib;
            double noic = here->B4v5noic;
            
            double T2 = noia * CONSTboltz * here->B4v5temp * gm * gm;
            double T3 = noib * id * gm;
            
            *Sid_flicker = (T2 + T3 + noic * id * id) / 
                          (cox * area * freq);
            break;
            
        case B4V5_FNOIMOD_UNIFIED:
            /* Combine traditional and unified models */
            double traditional = here->B4v5kf * pow(fabs(id), here->B4v5af) /
                                (cox * area * pow(freq, here->B4v5ef));
            
            double unified = here->B4v5noia * CONSTboltz * 
                            here->B4v5temp * gm * gm / 
                            (cox * area * freq);
            
            *Sid_flicker = traditional + unified;
            break;
    }
}
```

#### 4.3 Noise Matrix Stamping

```c
int B4v5noise(int mode, int operation, GENmodel *inModel, 
              CKTcircuit *ckt, Ndata *data, double *OnDens)
{
    B4v5model *model;
    B4v5instance *here;
    
    for(model = (B4v5model*)inModel; model != NULL;
        model = model->B4v5nextModel) {
        
        for(here = model->B4v5instances; here != NULL;
            here = here->B4v5nextInstance) {
            
            /* Calculate all noise components */
            double sid_thermal, sig_thermal, rho;
            B4v5thermalNoise(here, ckt->CKTtemp, &sid_thermal, &sig_thermal, &rho);
            
            double sid_flicker;
            double freq = ckt->CKTomega / (2.0 * M_PI);
            B4v5flickerNoise(here, freq, &sid_flicker);
            
            /* Total drain current noise */
            double sid_total = sid_thermal + sid_flicker;
            
            /* Calculate correlated gate noise if enabled */
            double sig_total = sig_thermal;
            double sfg = 0.0;  /* Cross-correlation term */
            
            if(here->B4v5tnoimod == B4V5_TNOIMOD_IGNOISE) {
                /* Compute complex correlation */
                double corr_real, corr_imag;
                B4v5inducedGateNoise(here, freq, &sig_thermal, 
                                    &corr_real, &corr_imag);
                
                sig_total += sig_thermal;
                sfg = rho * sqrt(sid_total * sig_total) + 
                      corr_imag * sqrt(sid_total * sig_thermal);
            }
            
            /* Stamp into noise correlation matrix */
            switch(operation) {
                case N_OPEN:
                    /* Allocate positions in noise matrix */
                    data->Dnoise[here->B4v5dOffset] = sid_total;
                    data->Dnoise[here->B4v5gOffset] = sig_total;
                    data->Dnoise[here->B4v5corrOffset] = sfg;
                    data->Dnoise[here->B4v5corrOffset + 1] = conj(sfg);
                    break;
                    
                case N_CALC:
                    /* Compute output noise using transfer functions */
                    *(data->DoutNoise) += 
                        sid_total * norm(data->Dtransfer[here->B4v5dOffset]) +
                        sig_total * norm(data->Dtransfer[here->B4v5gOffset]) +
                        2.0 * real(data->Dtransfer[here->B4v5dOffset] *
                                  conj(data->Dtransfer[here->B4v5gOffset]) * sfg);
                    break;
            }
        }
    }
    return OK;
}
```

### 5. Parasitic Resistance Noise Implementation

```c
void B4v5parasiticNoise(B4v5instance *here, double temp,
                        double *Svg, double *Svb, double *Svsub)
{
    /* Gate resistance thermal noise: S_vg = 4kTRg */
    if(here->B4v5rgateMod == 1) {
        *Svg = 4.0 * CONSTboltz * temp * here->B4v5rgate;
    } else {
        *Svg = 0.0;
    }
    
    /* Bulk resistance noise: S_vb = 4kTRb */
    *Svb = 4.0 * CONSTboltz * temp * here->B4v5rbulk;
    
    /* Substrate resistance noise: S_vsub = 4kTRsub */
    *Svsub = 4.0 * CONSTboltz * temp * here->B4v5rsub;
}
```

### 6. SPICE Integration and Matrix Pointer Architecture

#### 6.1 Matrix Pointer Initialization

During device setup, matrix pointers are assigned to specific positions in the circuit matrix:

```c
/* In b4v5set.c setup function */
here->B4v5DdPtr = CKTfndMatElt(ckt, here->B4v5dNode, here->B4v5dNode);
here->B4v5DgPtr = CKTfndMatElt(ckt, here->B4v5dNode, here->B4v5gNode);
here->B4v5DsPtr = CKTfndMatElt(ckt, here->B4v5dNode, here->B4v5sNode);
here->B4v5DbPtr = CKTfndMatElt(ckt, here->B4v5dNode, here->B4v5bNode);

/* For gate resistance model */
if(here->B4v5rgateMod == 1) {
    here->B4v5GgExtPtr = CKTfndMatElt(ckt, here->B4v5gNode, here->B4v5gNode);
    here->B4v5GgInt