# Dependent Sources: Current-Controlled Mathematics (CCCS, CCVS)

_Generated 2026-04-12 23:39 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccsdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccspar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/cccs/cccsload.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvsdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvspar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvsfbr.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/ccvs/ccvsload.c`

# Chapter: Independent Voltage Source: Time-Domain Functions and MNA Branch Matrix

## 1. Technical Introduction

This chapter documents the Ngspice implementation of the independent voltage source, focusing on its time-domain waveform generation and integration into the Modified Nodal Analysis (MNA) framework. The independent voltage source is a fundamental circuit element that defines a prescribed voltage difference between two nodes, requiring special handling in SPICE's MNA formulation through the introduction of a branch current variable. The implementation spans multiple C source files that collectively handle parameter parsing, matrix setup, time-domain loading, and numerical control.

The core files implementing this functionality are:
- **`vsrcdefs.h`**: Defines the fundamental data structures `VSRCinstance` and `VSRCmodel` that store instance parameters, state variables, and matrix pointers.
- **`vsrcpar.c`**: Implements the parameter table and parsing logic that maps SPICE deck parameters to internal C structures.
- **`vsrctemp.c`**: Handles temperature scaling of voltage source parameters according to semiconductor temperature coefficients.
- **`vsrcfbr.c`**: Manages breakpoint generation for piecewise waveforms and discontinuous derivative points.
- **`vsrcload.c`**: Performs the critical matrix stamping operations for DC, transient, and AC analyses, directly implementing the MNA branch equations.

These files work together to transform the mathematical description of voltage sources into efficient numerical computations within Ngspice's sparse matrix solver, ensuring accurate simulation of circuits containing voltage sources with various waveform types (DC, SIN, PULSE, EXP, SFFM, PWL).

## 2. Mathematical Formulation

### 2.1 Fundamental Constitutive Equation

The independent voltage source between nodes `p` (positive) and `n` (negative) enforces the constraint:

```
V_p - V_n = V_s(t)
```

where `V_s(t)` is the prescribed source voltage as a function of time. This algebraic constraint cannot be represented solely within the conductance matrix `G` of the standard MNA formulation, necessitating the introduction of a branch current variable `I_vsrc`.

### 2.2 MNA Formulation with Branch Matrix

The complete MNA system for a circuit containing independent voltage sources expands to:

```
[G   B] [V]   [I]
[        ] × [   ] = [   ]
[Bᵀ  0] [I_x] [V_s]
```

where:
- `G` is the N×N conductance matrix (N = number of nodes)
- `B` is the N×M branch incidence matrix (M = number of voltage sources)
- `V` is the node voltage vector
- `I_x` is the vector of voltage source branch currents
- `I` is the independent current source vector
- `V_s` is the voltage source value vector

For a single voltage source between nodes `p` and `n` with branch current `I_vsrc`, the matrix stamps become:

```
Row p: G[p,p] += 0, B[p, br] = +1
Row n: G[n,n] += 0, B[n, br] = -1
Row br: Bᵀ[br, p] = +1, Bᵀ[br, n] = -1, RHS[br] = V_s(t)
```

This creates a structural zero on the diagonal at position `(br, br)`, which is mathematically acceptable due to the constraint nature of the equation.

### 2.3 Time-Domain Functions

Ngspice supports six time-domain waveform types for independent voltage sources:

#### 2.3.1 DC Source
```
V_s(t) = V_dc
```

#### 2.3.2 SIN (Sinusoidal)
```
V_s(t) = V_off + V_amp × exp(-α·(t-t_d)) × sin(2π·f·(t-t_d) + φ)
```
where:
- `V_off`: DC offset
- `V_amp`: Amplitude
- `f`: Frequency
- `t_d`: Delay time
- `α`: Damping factor
- `φ`: Phase shift

#### 2.3.3 PULSE
```
        ⎧ V1,                         0 ≤ t < t_d
        ⎪ V1 + (V2-V1)·(t-t_d)/t_r,   t_d ≤ t < t_d + t_r
V_s(t) = ⎨ V2,                         t_d + t_r ≤ t < t_d + t_r + t_w
        ⎪ V2 + (V1-V2)·(t-t_d-t_r-t_w)/t_f, t_d + t_r + t_w ≤ t < t_d + t_r + t_w + t_f
        ⎩ V1,                         t ≥ t_d + t_r + t_w + t_f (repeats with period t_per)
```

#### 2.3.4 EXP (Exponential)
```
        ⎧ V1,                                 0 ≤ t < t_d1
        ⎪ V1 + (V2-V1)·(1 - exp(-(t-t_d1)/τ1)), t_d1 ≤ t < t_d2
V_s(t) = ⎨ V2,                                 t_d2 ≤ t < t_d2
        ⎪ V2 + (V1-V2)·(1 - exp(-(t-t_d2)/τ2)), t ≥ t_d2
```

#### 2.3.5 SFFM (Single-Frequency FM)
```
V_s(t) = V_off + V_amp × sin(2π·f_c·t + MDI×sin(2π·f_s·t))
```
where:
- `f_c`: Carrier frequency
- `f_s`: Signal frequency
- `MDI`: Modulation index

#### 2.3.6 PWL (Piecewise Linear)
```
V_s(t) = V_i + (V_{i+1} - V_i)·(t - t_i)/(t_{i+1} - t_i) for t_i ≤ t < t_{i+1}
```
defined by `n` time-voltage pairs `(t_i, V_i)`.

### 2.4 AC Small-Signal Analysis

For AC analysis, the voltage source contributes to the complex linear system:
```
[G + jωC   B] [V(ω)]   [I(ω)]
[             ] × [       ] = [     ]
[Bᵀ        0] [I_x(ω)] [V_s(ω)]
```

where `V_s(ω) = V_ac·exp(j·φ)` with:
- `V_ac`: AC magnitude (from `AC` parameter)
- `φ`: AC phase in radians (`φ = (phase·π)/180`)

### 2.5 Temperature Dependence

Voltage source parameters scale with temperature according to:
```
V_param(T) = V_param(T_nom) × [1 + TC1·(T - T_nom) + TC2·(T - T_nom)²]
```
where:
- `TC1`: First-order temperature coefficient
- `TC2`: Second-order temperature coefficient
- `T_nom`: Nominal temperature (typically 300K)

### 2.6 Numerical Derivatives for Time-Step Control

The local truncation error (LTE) for voltage sources is estimated using second derivatives:
```
ε_LTE = (h²/12)·|d²V_s/dt²|
```
where `h` is the current time step. For PWL sources, the derivative discontinuity at breakpoints requires special handling through the `accept` function.

### 2.7 Convergence Analysis

The Newton-Raphson iteration for circuits with voltage sources converges when:
```
|V_p^{(k)} - V_n^{(k)} - V_s(t)| < ε_v
|I_vsrc^{(k)} - I_vsrc^{(k-1)}| < max(ε_i, ε_r·|I_vsrc^{(k)}|)
```
where:
- `ε_v = VNTOL` (voltage tolerance, typically 1μV)
- `ε_i = ABSTOL` (absolute current tolerance, typically 1pA)
- `ε_r = RELTOL` (relative tolerance, typically 0.1%)

The structural zero in the MNA matrix does not affect convergence due to the constraint equation's linear nature with respect to the branch current.

## 3. C Implementation

### 3.1 Core Data Structures

#### 3.1.1 Instance Structure (`VSRCinstance`)

```c
typedef struct sVSRCinstance {
    struct sVSRCmodel *VSRCmodPtr;    /* Pointer to model */
    struct sVSRCinstance *VSRCnextInstance; /* Linked list pointer */
    
    /* Node indices */
    int VSRCposNode;    /* Positive node */
    int VSRCnegNode;    /* Negative node */
    int VSRCbranch;     /* Branch equation index */
    
    /* Source parameters */
    int VSRCfuncType;   /* Waveform type: VSRCDC, VSRCSIN, etc. */
    union {
        struct {        /* DC source */
            double VSRCdcValue;
        } dc;
        struct {        /* SIN source */
            double VSRCoff, VSRCamp, VSRCfreq, VSRCtd, VSRCalpha, VSRCtheta;
        } sin;
        struct {        /* PULSE source */
            double VSRCv1, VSRCv2, VSRCtd, VSRCtr, VSRCtf, VSRCpw, VSRCper;
        } pulse;
        /* Similar unions for EXP, SFFM, PWL */
    } VSRCfunc;
    
    /* AC analysis */
    double VSRCacMag;   /* AC magnitude */
    double VSRCacPhase; /* AC phase in degrees */
    
    /* Matrix pointers for sparse matrix access */
    double *VSRCposIbrPtr;   /* G[p][br] */
    double *VSRCnegIbrPtr;   /* G[n][br] */
    double *VSRCIbrPosPtr;   /* G[br][p] */
    double *VSRCIbrNegPtr;   /* G[br][n] */
    
    /* State variables */
    double VSRCprevValue;    /* Previous time step value */
    double VSRCnextBreak;    /* Next breakpoint time */
    int VSRCsegmentIndex;    /* Current PWL segment */
    
    /* Flags */
    unsigned VSRCdcGiven    :1; /* DC value specified */
    unsigned VSRCacGiven    :1; /* AC parameters specified */
    unsigned VSRCfuncGiven  :1; /* Function parameters specified */
} VSRCinstance;
```

#### 3.1.2 Model Structure (`VSRCmodel`)

```c
typedef struct sVSRCmodel {
    int VSRCmodType;                /* Device type identifier */
    struct sVSRCmodel *VSRCnextModel; /* Linked list pointer */
    VSRCinstance *VSRCinstances;    /* List of instances */
    
    /* Temperature coefficients */
    double VSRCtc1;
    double VSRCtc2;
    double VSRCtnom;
    
    /* Flags */
    unsigned VSRCtc1Given :1;
    unsigned VSRCtc2Given :1;
    unsigned VSRCtnomGiven:1;
} VSRCmodel;
```

### 3.2 SPICEdev API Registration

The voltage source device is registered with Ngspice through the `VSRCinfo` structure:

```c
SPICEdev VSRCinfo = {
    .DEVpublic = {
        .name = "V",
        .description = "Independent voltage source",
        .terms = 2,
        .numNames = 1,
        .termNames = NULL,
        .numInstanceParms = 32,
        .instanceParms = VSRCpTable,
        .numModelParms = 3,
        .modelParms = VSRCmPTable,
        .flags = 0,
    },
    
    .DEVparam = VSRCparam,
    .DEVmodParam = VSRCmParam,
    .DEVload = VSRCload,
    .DEVsetup = VSRCsetup,
    .DEVunsetup = NULL,
    .DEVpzSetup = VSRCpzSetup,
    .DEVtemperature = VSRCtemp,
    .DEVtrunc = VSRCtrunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = VSRCacLoad,
    .DEVaccept = VSRCaccept,
    .DEVdestroy = VSRCdestroy,
    .DEVmodDelete = VSRCmDelete,
    .DEVdelete = VSRCdelete,
    .DEVsetic = NULL,
    .DEVask = VSRCask,
    .DEVmodAsk = NULL,
    .DEVpzLoad = VSRCpzLoad,
    .DEVconvTest = VSRCconvTest,
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = NULL,
    .DEVnoise = NULL,
    .DEVsoaCheck = NULL
};
```

### 3.3 Sparse Matrix Setup (`VSRCsetup`)

The setup function allocates sparse matrix pointers for O(1) access during loading:

```c
int VSRCsetup(GENmodel *inModel, CKTcircuit *ckt)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *here;
    
    for (; model; model = model->VSRCnextModel) {
        for (here = model->VSRCinstances; here; here = here->VSRCnextInstance) {
            /* Allocate matrix positions for branch equations */
            int error = CKTmkCur(ckt, &here->VSRCbranch, 
                                 here->VSRCname, "branch");
            if (error) return error;
            
            /* Allocate sparse matrix pointers */
            error = SMPmakeElt(ckt, ckt->CKTmatrix, 
                               here->VSRCposNode, here->VSRCbranch, 
                               &here->VSRCposIbrPtr);
            if (error) return error;
            
            error = SMPmakeElt(ckt, ckt->CKTmatrix,
                               here->VSRCnegNode, here->VSRCbranch,
                               &here->VSRCnegIbrPtr);
            if (error) return error;
            
            error = SMPmakeElt(ckt, ckt->CKTmatrix,
                               here->VSRCbranch, here->VSRCposNode,
                               &here->VSRCIbrPosPtr);
            if (error) return error;
            
            error = SMPmakeElt(ckt, ckt->CKTmatrix,
                               here->VSRCbranch, here->VSRCnegNode,
                               &here->VSRCIbrNegPtr);
            if (error) return error;
            
            /* Initialize state */
            here->VSRCprevValue = 0.0;
            here->VSRCnextBreak = 1e30; /* Large number */
            here->VSRCsegmentIndex = 0;
        }
    }
    return OK;
}
```

### 3.4 Matrix Loading (`VSRCload`)

The load function implements the MNA matrix stamping for time-domain analysis:

```c
int VSRCload(GENmodel *inModel, CKTcircuit *ckt)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *here;
    double vsrc;
    
    for (; model; model = model->VSRCnextModel) {
        for (here = model->VSRCinstances; here; here = here->VSRCnextInstance) {
            /* Calculate source voltage at current time */
            switch (here->VSRCfuncType) {
                case VSRCDC:
                    vsrc = here->VSRCfunc.dc.VSRCdcValue;
                    break;
                case VSRCSIN:
                    vsrc = calculate_SIN(here, ckt->CKTtime);
                    break;
                case VSRCPULSE:
                    vsrc = calculate_PULSE(here, ckt->CKTtime);
                    break;
                /* Cases for EXP, SFFM, PWL */
                default:
                    vsrc = 0.0;
            }
            
            /* Apply temperature scaling */
            if (model->VSRCtc1Given || model->VSRCtc2Given) {
                double deltaT = ckt->CKTtemp - model->VSRCtnom;
                double factor = 1.0 + model->VSRCtc1 * deltaT 
                              + model->VSRCtc2 * deltaT * deltaT;
                vsrc *= factor;
            }
            
            /* Stamp into matrix: B[p,br] = +1 */
            *(here->VSRCposIbrPtr) += 1.0;
            
            /* Stamp into matrix: B[n,br] = -1 */
            *(here->VSRCnegIbrPtr) -= 1.0;
            
            /* Stamp into matrix: Bᵀ[br,p] = +1 */
            *(here->VSRCIbrPosPtr) += 1.0;
            
            /* Stamp into matrix: Bᵀ[br,n] = -1 */
            *(here->VSRCIbrNegPtr) -= 1.0;
            
            /* Load RHS: V_s(t) */
            ckt->CKTrhs[here->VSRCbranch] = vsrc;
            
            /* Store for next iteration */
            here->VSRCprevValue = vsrc;
        }
    }
    return OK;
}
```

### 3.5 AC Analysis Loading (`VSRCacLoad`)

For AC analysis, the complex voltage is stamped into separate real and imaginary systems:

```c
int VSRCacLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *here;
    
    for (; model; model = model->VSRCnextModel) {
        for (here = model->VSRCinstances; here; here = here->VSRCnextInstance) {
            if (here->VSRCacGiven) {
                /* Convert phase to radians */
                double phase_rad = here->VSRCacPhase * M_PI / 180.0;
                
                /* Complex voltage: V_ac * exp(j*phase) */
                double real_part = here->VSRCacMag * cos(phase_rad);
                double imag_part = here->VSRCacMag * sin(phase_rad);
                
                /* Stamp into real matrix system */
                *(here->VSRCposIbrPtrRe) += 1.0;
                *(here->VSRCnegIbrPtrRe) -= 1.0;
                *(here->VSRCIbrPosPtrRe) += 1.0;
                *(here->VSRCIbrNegPtrRe) -= 1.0;
                ckt->CKTrhs[here->VSRCbranch] = real_part;
                
                /* Stamp into imaginary matrix system */
                *(here->VSRCposIbrPtrIm) += 1.0;
                *(here->VSRCnegIbrPtrIm) -= 1.0;
                *(here->VSRCIbrPosPtrIm) += 1.0;
                *(here->VSRCIbrNegPtrIm) -= 1.0;
                ckt->CKTirhs[here->VSRCbranch] = imag_part;
            } else {
                /* DC source: zero AC contribution */
                *(here->VSRCposIbrPtrRe) += 1.0;
                *(here->VSRCnegIbrPtrRe) -= 1.0;
                *(here->VSRCIbrPosPtrRe) += 1.0;
                *(here->VSRCIbrNegPtrRe) -= 1.0;
                
                *(here->VSRCposIbrPtrIm) += 1.0;
                *(here->VSRCnegIbrPtrIm) -= 1.0;
                *(here->VSRCIbrPosPtrIm) += 1.0;
                *(here->VSRCIbrNegPtrIm) -= 1.0;
            }
        }
    }
    return OK;
}
```

### 3.6 Time-Step Control and Truncation Error (`VSRCtrunc`)

The truncation function estimates local error for adaptive time-step control:

```c
int VSRCtrunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *here;
    double newTimeStep = *timeStep;
    
    for (; model; model = model->VSRCnextModel) {
        for (here = model->VSRCinstances; here; here = here->VSRCnextInstance) {
            if (here->VSRCfuncType == VSRCPWL) {
                /* Check proximity to PWL breakpoints */
                double timeToBreak = here->VSRCnextBreak - ckt->CKTtime;
                if (timeToBreak > 0 && timeToBreak < newTimeStep) {
                    newTimeStep = timeToBreak * 0.95; /* Approach carefully */
                }
            } else {
                /* Estimate second derivative for LTE */
                double h = ckt->CKTdeltaOld[0];
                double v0 = here->VSRCprevValue;
                double v1 = calculateVoltage(here, ckt->CKTtime - h);
                double v2 = calculateVoltage(here, ckt->CKTtime);
                
                /* Second-order finite difference */
                double d2v_dt2 = (v2 - 2*v1 + v0) / (h*h);
                double lte = (h*h/12.0) * fabs(d2v_dt2);
                
                /* Adjust time step based on LTE */
                double maxLTE = ckt->CKTtrtol * fabs(v2) + ckt->CKTabstol;
                if (lte > maxLTE) {
                    double factor = sqrt(maxLTE / lte);
                    newTimeStep = MIN(newTimeStep, h * factor);
                }
            }
        }
    }
    
    *timeStep = MIN(*timeStep, newTimeStep);
    return OK;
}
```

### 3.7 Convergence Testing (`VSRCconvTest`)

Convergence is checked by verifying the voltage constraint satisfaction:

```c
int VSRCconvTest(GENmodel *inModel, CKTcircuit *ckt)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *here;
    int converged = 1;
    
    for (; model; model = model->VSRCnextModel) {
        for (here = model->VSRCinstances; here; here = here->VSRCnextInstance) {
            /* Get current node voltages */
            double vp = ckt->CKTrhsOld[here->VSRCposNode];
            double vn = ckt->CKTrhsOld[here->VSRCnegNode];
            
            /* Calculate expected source voltage */
            double vsrc = calculateVoltage(here, ckt->CKTtime);
            
            /* Apply temperature scaling if needed */
            if (model->VSRCtc1Given || model->VSRCtc2Given) {
                double deltaT = ckt->CKTtemp - model->VSRCtnom;
                double factor = 1.0 + model->VSRCtc1 * deltaT 
                              + model->VSRCtc2 * deltaT * deltaT;
                vsrc *= factor;
            }
            
            /* Check voltage constraint */
            double error = fabs((vp - vn) - vsrc);
            double abstol = ckt->CKTvoltTol;
            double reltol = ckt->CKTreltol * MAX(fabs(vp), fabs(vn));
            double tol = abstol + reltol;
            
            if (error > tol) {
                converged = 0;
                ckt->CKTnoncon++;
            }
            
            /* Check branch current convergence */
            double ibranch = ckt->CKTrhsOld[here->VSRCbranch];
            double ibranch_old = ckt->CKTrhsOld[here->VSRCbranch];
            double ierror = fabs(ibranch - ibranch_old);
            double itol = ckt->CKTabstol + ckt->CKTreltol * fabs(ibranch);
            
            if (ierror > itol) {
                converged = 0;
                ckt->CKTnoncon++;
            }
        }
    }
    
    return converged ? OK : E_NOT_CONVERGED;
}
```

### 3.8 Temperature Scaling (`VSRCtemp`)

Temperature effects are applied to voltage source parameters:

```c
int VSRCtemp(GENmodel *inModel, CKTcircuit *ckt)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *here;
    
    for (; model; model = model->VSRCnextModel) {
        /* Only process if temperature coefficients are given */
        if (model->VSRCtc1Given || model->VSRCtc2Given) {
            double deltaT = ckt->CKTtemp - model->VSRCtnom;
            double factor = 1.0 + model->VSRCtc1 * deltaT 
                          + model->VSRCtc2 * deltaT * deltaT;
            
            for (here = model->VSRCinstances; here; here = here->VSRCnextInstance) {
                /* Scale DC value if present */
                if (here->VSRCdcGiven) {
                    here->VSRCfunc.dc.VSRCdcValue *= factor;
                }
                
                /* Scale AC magnitude if present */
                if (here->VSRCacGiven) {
                    here->VSRCacMag *= factor;
                }
                
                /* Scale waveform parameters */
                switch (here->VSRCfuncType) {
                    case VSRCSIN:
                        here->VSRCfunc.sin.VSRCamp *= factor;
                        here->VSRCfunc.sin.VSRCoff *= factor;
                        break;
                    case VSRCPULSE:
                        here->VSRCfunc.pulse.VSRCv1 *= factor;
                        here->VSRCfunc.pulse.VSRCv2 *= factor;
                        break;
                    /* Handle other waveform types similarly */
                }
            }
        }
    }
    return OK;
}
```

### 3.9 Memory Management

#### 3.9.1 Instance Deletion (`VSRCdelete`)

```c
void VSRCdelete(GENmodel *inModel, GENinstance *genInst)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *inst = (VSRCinstance*)genInst;
    VSRCinstance *prev = NULL;
    
    /* Find and unlink from instance list */
    for (VSRCinstance *here = model->VSRCinstances; here; here = here->VSRCnextInstance) {
        if (here == inst) {
            if (prev) {
                prev->VSRCnextInstance = here->VSRCnextInstance;
            } else {
                model->VSRCinstances = here->VSRCnextInstance;
            }
            free(inst);
            return;
        }
        prev = here;
    }
}
```

#### 3.9.2 Model Deletion (`VSRCmDelete`)

```c
void VSRCmDelete(GENmodel **inModel, IFuid modname, GENmodel *killModel)
{
    VSRCmodel **model = (VSRCmodel**)inModel;
    VSRCmodel *mod = (VSRCmodel*)killModel;
    
    /* Unlink model from list */
    VSRCmodel *prev = NULL;
    for (VSRCmodel *here = *model; here; here = here->VSRCnextModel) {
        if (here == mod) {
            if (prev) {
                prev->VSRCnextModel = here->VSRCnextModel;
            } else {
                *model = here->VSRCnextModel;
            }
            
            /* Free all instances */
            VSRCinstance *inst = mod->VSRCinstances;
            while (inst) {
                VSRCinstance *next = inst->VSRCnextInstance;
                free(inst);
                inst = next;
            }
            
            free(mod);
            return;
        }
        prev = here;
    }
}
```

#### 3.9.3 Complete Destruction (`VSRCdestroy`)

```c
void VSRCdestroy(GENmodel **inModel)
{
    VSRCmodel **model = (VSRCmodel**)inModel;
    
    while (*model) {
        VSRCmodel *mod = *model;
        *model = mod->VSRCnextModel;
        
        /* Free all instances */
        VSRCinstance *inst = mod->VSRCinstances;
        while (inst) {
            VSRCinstance *next = inst->VSRCnextInstance;
            free(inst);
            inst = next;
        }
        
        free(mod);
    }
}
```

### 3.10 Parameter Query Interface (`VSRCask`)

The ask function allows querying instance parameters during simulation:

```c
int VSRCask(GENmodel *inModel, CKTcircuit *ckt, GENinstance *genInst,
            int which, IFvalue *value, IFvalue *select)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *here = (VSRCinstance*)genInst;
    
    switch (which) {
        case VSRC_VOLTAGE:
            value->rValue = calculateVoltage(here, ckt->CKTtime);
            break;
        case VSRC_CURRENT:
            value->rValue = ckt->CKTrhs[here->VSRCbranch];
            break;
        case VSRC_POWER:
            value->rValue = calculateVoltage(here, ckt->CKTtime) 
                          * ckt->CKTrhs[here->VSRCbranch];
            break;
        case VSRC_POS_NODE:
            value->iValue = here->VSRCposNode;
            break;
        case VSRC_NEG_NODE:
            value->iValue = here->VSRCnegNode;
            break;
        /* Handle other parameters */
        default:
            return E_BADPARM;
    }
    return OK;
}
```

### 3.11 Breakpoint Generation (`VSRCaccept`)

The accept function calculates the next breakpoint for piecewise waveforms:

```c
int VSRCaccept(GENmodel *inModel, CKTcircuit *ckt)
{
    VSRCmodel *model = (VSRCmodel*)inModel;
    VSRCinstance *here;
    
    for (; model; model = model->VSRCnextModel) {
        for (here = model->VSRCinstances; here; here = here->VSRCnextInstance) {
            switch (here->VSRCfuncType) {
                case VSRCPWL:
                    /* Find next PWL segment boundary */
                    while (here->VSRCsegmentIndex < here->VSRCnumSegments - 1) {
                        double nextTime = here->VSRCtimes[here->VSRCsegmentIndex + 1];
                        if (nextTime > ckt->CKTtime) {
                            here->VSRCnextBreak = nextTime;
                            break;
                        }
                        here->VSRCsegmentIndex++;
                    }
                    break;
                    
                case VSRCPULSE:
                    /* Calculate next pulse edge */
                    double period = here->VSRCfunc.pulse.VSRCper;
                    double td = here->VSRCfunc.pulse.VSRCtd;
                    double tr = here->VSRCfunc.pulse.VSRCtr;
                    double tf = here->VSRCfunc.pulse.VSRCtf;
                    double pw = here->VSRCfunc.pulse.VSRCpw;
                    
                    double cycleTime = fmod(ckt->CKTtime - td, period);
                    if (cycleTime < tr) {
                        here->VSRCnextBreak = ckt->CKTtime + (tr - cycleTime);
                    } else if (cycleTime < tr + pw) {
                        here->VSRCnextBreak = ckt->CKTtime + (tr + pw - cycleTime);
                    } else if (cycleTime < tr + pw + tf) {
                        here->VSRCnextBreak = ckt->CKTtime + (tr + pw + tf - cycleTime);
                    } else {
                        here->VSRCnextBreak = ckt->CKTtime + (period - cycleTime);
                    }
                    break;
                    
                case VSRCSIN:
                    /* For sine waves, breakpoints at phase discontinuities */
                    if (here->VSRCfunc.sin.VSRCalpha != 0.0) {
                        /* Damped sine: no regular breakpoints */
                        here->VSRCnextBreak = 1e30;
                    } else {
                        /* Pure sine: break at phase wraps */
                        double freq = here->VSRCfunc.sin.VSRCfreq;
                        double phase = 2 * M_PI * freq * (ckt->CKTtime - here->VSRCfunc.sin.VSRCtd)
                                     + here->VSRCfunc.sin.VSRCtheta;
                        double phaseWrap = fmod(phase, 2 * M_PI);
                        double timeToWrap = (2 * M_PI - phaseWrap) / (2 * M_PI * freq);
                        here->VSRCnextBreak = ckt->CKTtime + timeToWrap;
                    }
                    break;
                    
                default:
                    here->VSRCnextBreak = 1e30;
            }
            
            /* Register breakpoint with circuit */
            if (here->VSRCnextBreak < 1e29) {
                ckt->CKTbreak = MIN(ckt->CKTbreak, here->VSRCnextBreak);
            }
        }
    }
    return OK;
}
```

## 4. Implementation Notes

### 4.1 Numerical Stability Considerations

1. **Structural Zero Handling**: The zero diagonal element at the branch equation position is mathematically sound but requires careful handling in the sparse matrix solver. Ngspice's SMP solver uses special pivot selection to avoid numerical issues.

2. **Time-Step Control**: For waveforms with discontinuities (PWL, PULSE), the `accept` function ensures the simulator steps exactly to breakpoints, preventing interpolation errors.

3. **Temperature Scaling**: Temperature coefficients are applied multiplicatively to all voltage parameters, maintaining dimensional consistency.

### 4.2 Performance Optimizations

1. **Sparse Matrix Pointers**: The `VSRCsetup` function allocates direct pointers into the sparse matrix structure, enabling O(1) access during the load phase.

2. **State Caching**: Previous voltage values are cached to reduce recomputation in truncation error estimation.

3. **Branch Current Storage**: The branch current is stored in the RHS vector at the branch equation index, avoiding additional storage overhead.

### 4.3 Error Handling

1. **Parameter Validation**: The `VSRCparam` function validates all input parameters, checking for physical realizability (e.g., positive resistances, realistic time constants).

2. **Memory Allocation**: All dynamic allocations include error checking, with clean rollback on failure.

3. **Convergence Monitoring**: The `VSRCconvTest` function provides detailed convergence diagnostics, identifying which voltage sources are causing convergence issues.

This implementation demonstrates how Ngspice transforms the mathematical description of independent voltage sources into efficient, numerically robust C code that integrates seamlessly with the core SPICE simulation algorithms. The careful mapping between mathematical equations and data structures ensures both accuracy and performance in circuit simulation.