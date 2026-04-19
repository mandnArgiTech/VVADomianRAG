# Independent Voltage Source: Time-Domain Functions and MNA Branch Matrix

_Generated 2026-04-12 22:59 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vsrc/vsrcdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vsrc/vsrcpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vsrc/vsrctemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vsrc/vsrcfbr.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/vsrc/vsrcload.c`

# Chapter: Independent Voltage Source: Time-Domain Functions and MNA Branch Matrix

## Technical Introduction

The independent voltage source implementation in Ngspice is architected across five core files that collectively define its mathematical behavior, parameter handling, and integration into the simulation engine. `vsrcdefs.h` establishes the fundamental C data structures—`VSRCinstance` and `VSRCmodel`—that encapsulate the device's state, including terminal nodes, branch equation indices, and the complete parameter set for all supported time-domain waveforms (DC, SIN, PULSE, EXP, SFFM, PWL). `vsrcpar.c` implements the parameter binding system, parsing netlist entries and populating these structures while enforcing physical validity. Temperature scaling of source values, governed by quadratic coefficients TC1 and TC2, is handled by `vsrctemp.c`, ensuring model accuracy across operating conditions. The critical Modified Nodal Analysis (MNA) formulation is managed by `vsrcfbr.c` and `vsrcload.c`: `vsrcfbr.c` (or its equivalent) allocates the sparse matrix entries for the branch current equation required by ideal voltage sources, while `vsrcload.c` performs the actual matrix stamping. This stamping implements the mathematical constraint `V_pos - V_neg = V_s(t)` by loading the `[G B; BT 0]` matrix block and the right-hand-side vector `[I; V_s]` during each Newton-Raphson iteration. Together, these files transform the abstract constitutive equations and transient function definitions into a numerically robust component within the SPICE solver.

## 1. Mathematical Formulation

### 1.1 Fundamental Constitutive Equation

The independent voltage source (VSRC) in SPICE is defined by its terminal voltage relationship:

```
V_pos - V_neg = V_s(t)
```

Where:
- `V_pos`, `V_neg` are the voltages at positive and negative terminals
- `V_s(t)` is the time-dependent source voltage function

### 1.2 Modified Nodal Analysis (MNA) Formulation

Unlike current sources that only affect the RHS vector, voltage sources require branch equations in MNA. For a voltage source between nodes `i` (positive) and `j` (negative) with branch current `I_v`:

```
[G   B] [V]   [I]
[BT  0] [I_v] = [V_s]
```

Where the submatrices are:
- `G`: n×n conductance matrix (unaffected by ideal voltage source)
- `B`: n×1 incidence vector for the branch current
- `BT`: 1×n transpose of B
- `V_s`: source voltage value

The specific stamp for a voltage source at row/column indices `i, j, m` (where `m` is the branch equation index) is:

```
Row i: G[i][m] += 1
Row j: G[j][m] -= 1
Row m: G[m][i] += 1, G[m][j] -= 1, RHS[m] = V_s(t)
```

### 1.3 Time-Domain Function Definitions

#### 1.3.1 DC Source
```
V_s(t) = V_dc
```

#### 1.3.2 SIN (Sinusoidal) Source
```
V_s(t) = V_off + V_amp * sin(2π * freq * (t - t_delay)) * exp(-(t - t_delay) * theta)
```
for `t ≥ t_delay`, otherwise `V_s(t) = V_off`

Where:
- `V_off`: DC offset voltage
- `V_amp`: amplitude
- `freq`: frequency (Hz)
- `t_delay`: delay time
- `theta`: damping factor (1/seconds)

#### 1.3.3 PULSE Source
```
Parameters: V1 (initial), V2 (pulsed), t_delay, t_rise, t_fall, t_width, t_period

Piecewise definition:
t < t_delay: V_s(t) = V1
t_delay ≤ t < t_delay + t_rise: linear ramp from V1 to V2
t_delay + t_rise ≤ t < t_delay + t_rise + t_width: V_s(t) = V2
t_delay + t_rise + t_width ≤ t < t_delay + t_rise + t_width + t_fall: linear ramp from V2 to V1
For subsequent periods: repeat pattern with period t_period
```

#### 1.3.4 EXP (Exponential) Source
```
Parameters: V1 (initial), V2 (final), t_delay1, tau1, t_delay2, tau2

For t_delay1 ≤ t < t_delay2:
V_s(t) = V1 + (V2 - V1) * (1 - exp(-(t - t_delay1)/tau1))

For t ≥ t_delay2:
V_s(t) = V1 + (V2 - V1) * (1 - exp(-(t_delay2 - t_delay1)/tau1)) * exp(-(t - t_delay2)/tau2)
```

#### 1.3.5 SFFM (Single-Frequency FM) Source
```
V_s(t) = V_off + V_amp * sin(2π * fc * t + MDI * sin(2π * fs * t))
```
Where:
- `fc`: carrier frequency
- `fs`: signal frequency
- `MDI`: modulation index

#### 1.3.6 PWL (Piecewise Linear) Source
```
Given breakpoints (t_k, V_k) for k = 0...N:
V_s(t) = V_k + (V_{k+1} - V_k) * (t - t_k) / (t_{k+1} - t_k)
for t_k ≤ t < t_{k+1}
```

### 1.4 AC Small-Signal Analysis

For AC analysis, the voltage source contributes a complex phasor:
```
V_s(ω) = V_ac * exp(j * phase)
```
Where `V_ac` is the AC magnitude and `phase` is the phase angle in radians.

The MNA stamp for AC analysis uses the same matrix structure but with:
```
RHS[m] = V_s(ω)  (complex value)
```

### 1.5 Temperature Dependence

Voltage source parameters may scale with temperature:
```
V_dc(T) = V_dc(T_nom) * [1 + TC1 * (T - T_nom) + TC2 * (T - T_nom)²]
```
Where:
- `T_nom`: nominal temperature
- `TC1`, `TC2`: first and second-order temperature coefficients

### 1.6 Numerical Derivatives for Time-Step Control

The local truncation error (LTE) calculation requires second derivatives:
```
For LTE control: d²V_s/dt²
```
For PWL sources at breakpoints:
```
dV_s/dt discontinuous → requires breakpoint generation
```

## 2. Convergence Analysis

### 2.1 Newton-Raphson Convergence Properties

The ideal voltage source is a linear element in the MNA formulation. The Jacobian entries are constant:

```
∂F_i/∂V_m = 1, ∂F_j/∂V_m = -1, ∂F_m/∂V_i = 1, ∂F_m/∂V_j = -1
∂F_m/∂I_v = 0
```

Since these derivatives are constant (not voltage-dependent), the Newton-Raphson iteration converges in a single step for pure DC analysis involving only voltage sources and linear elements.

### 2.2 Convergence Testing

For the branch equation (row `m`), the convergence test checks:
```
|V_pos - V_neg - V_s(t)| < ε_v
```
Where `ε_v = max(VNTOL, RELTOL * max(|V_pos|, |V_neg|, |V_s|))`

Typical SPICE tolerances:
- `VNTOL = 1e-6` (voltage tolerance)
- `RELTOL = 1e-3` (relative tolerance)

### 2.3 Local Truncation Error (LTE) Control

For time-domain analysis, the LTE for a voltage source is estimated from its time variation:

```
LTE_V = (h²/12) * |d²V_s/dt²|
```
Where `h` is the time step.

The time-step control algorithm ensures:
```
LTE_V < TRTOL * max(|V_s|, VNTOL)
```
Where `TRTOL` is typically `1e-3`.

For piecewise linear sources, additional breakpoints are generated at discontinuities in `dV_s/dt` to maintain accuracy.

### 2.4 Breakpoint Generation Algorithm

For transient functions with discontinuities (PULSE, PWL), breakpoints are generated at:

1. `t_delay` (start time)
2. `t_delay + t_rise` (end of rise)
3. `t_delay + t_rise + t_width` (start of fall)
4. `t_delay + t_rise + t_width + t_fall` (end of pulse)
5. All PWL breakpoint times `t_k`

At each breakpoint, the time step is reduced to exactly hit the discontinuity, preventing numerical errors from finite difference approximations across sudden changes.

### 2.5 AC Analysis Convergence

For frequency-domain analysis, the voltage source contributes a constant complex value to the RHS vector. The convergence of the linear system:
```
(J + jωC) * ΔX = B
```
depends on the overall circuit, but the voltage source contribution `B[m] = V_s(ω)` is exact and doesn't introduce convergence issues.

### 2.6 Numerical Stability Considerations

#### 2.6.1 Matrix Conditioning
The MNA formulation for voltage sources creates a zero on the diagonal at position `[m][m]` (since `∂F_m/∂I_v = 0`). This necessitates careful pivoting during LU decomposition to avoid numerical instability.

#### 2.6.2 Time-Step Control Stability
For rapidly changing sources (e.g., high-frequency SIN or sharp PULSE edges), the time step must satisfy:
```
h < 0.1 * min(t_rise, t_fall)  (for PULSE sources)
h < 0.1 / freq  (for SIN sources)
```
to accurately capture the waveform.

#### 2.6.3 Charge Conservation
Although voltage sources don't store charge, they affect charge conservation in capacitive circuits through their constraint on node voltages. The trapezoidal integration rule ensures charge conservation when combined with capacitor companion models.

### 2.7 Statistical Convergence (Monte Carlo Analysis)

For statistical analysis with parameter variations, the voltage source value may be modeled as:
```
V_s = V_nom + ΔV
```
Where `ΔV` follows a specified distribution (Gaussian, uniform, etc.).

Convergence in Monte Carlo analysis requires sufficient samples to achieve the desired confidence interval for the output statistics.

### 2.8 Implementation-Specific Convergence Enhancements

#### 2.8.1 Source Stepping
For circuits with multiple voltage sources, source stepping may be employed:
```
V_s(λ) = λ * V_s
```
Where `λ` goes from 0 to 1 gradually to improve convergence in strongly nonlinear circuits.

#### 2.8.2 Gmin Stepping
A small conductance `GMIN` (typically 1e-12 S) may be added in parallel with voltage sources to improve matrix conditioning:
```
I_leak = GMIN * (V_pos - V_neg)
```
This creates a small diagonal entry `GMIN` at position `[m][m]` without significantly affecting circuit behavior.

### 2.9 Error Metrics and Validation

The numerical accuracy of voltage source implementation is validated using:

1. **DC Accuracy**: `|V_measured - V_specified| < 1e-9`
2. **Transient Accuracy**: RMS error < 0.1% of amplitude for sinusoidal sources
3. **Breakpoint Accuracy**: Time alignment within `1e-12 * max(t_k)` for PWL sources
4. **AC Accuracy**: Magnitude error < 0.01dB, phase error < 0.1° for frequency domain

These convergence criteria ensure the voltage source model maintains the precision required for professional circuit simulation while providing robust numerical performance across all analysis types.

----------

# C Implementation

## 1. Core Data Structures and SPICEdev API Binding

The independent voltage source implementation follows Ngspice's standardized device architecture pattern. The core data structures and API binding implement the mathematical formulations for time-domain functions and MNA branch matrix stamping.

### 1.1 Device Instance Structure

```c
/* Based on the generic GENinstance pattern from section 1.1 */
typedef struct sVSRCinstance {
    struct sVSRCinstance *VSRCnextInstance;  /* Linked list pointer */
    VSRCmodel *VSRCmodPtr;                   /* Pointer to parent model */
    int VSRCposNode;                         /* Positive node index */
    int VSRCnegNode;                         /* Negative node index */
    double VSRCdcValue;                      /* DC voltage value */
    int VSRCbranch;                          /* Branch equation index for MNA */
    double *VSRCstate0;                      /* State vector at time t */
    double *VSRCstate1;                      /* State vector at time t-h */
    unsigned VSRCstates:8;                   /* Number of state variables */
    
    /* Time-domain function parameters */
    int VSRCfuncType;                        /* SIN, PULSE, EXP, SFFM, PWL */
    union {
        struct {                             /* SIN wave parameters */
            double amplitude;
            double frequency;
            double delay;
            double theta;
        } sine;
        struct {                             /* PULSE parameters */
            double v1;
            double v2;
            double td;
            double tr;
            double tf;
            double pw;
            double per;
        } pulse;
        /* Similar unions for EXP, SFFM, PWL functions */
    } VSRCwave;
    
    /* AC analysis parameters */
    double VSRCacMag;                        /* AC magnitude */
    double VSRCacPhase;                      /* AC phase (radians) */
    
    /* Previous values for LTE calculation */
    double VSRCprevValue;                    /* Previous time step value */
    double VSRCprevDeriv;                    /* Previous derivative */
} VSRCinstance;
```

### 1.2 Device Model Structure

```c
/* Based on the generic GENmodel pattern from section 1.1 */
typedef struct sVSRCmodel {
    int VSRCmodType;                         /* Model type identifier */
    struct sVSRCmodel *VSRCnextModel;        /* Linked list pointer */
    VSRCinstance *VSRCinstances;             /* List of instances */
    
    /* Model parameters for temperature scaling */
    double VSRCtc1;                          /* First order temp coefficient */
    double VSRCtc2;                          /* Second order temp coefficient */
    double VSRCtnom;                         /* Nominal temperature */
} VSRCmodel;
```

### 1.3 SPICEdev API Registration

```c
/* Following the SPICEdev binding pattern from section 1.2 */
SPICEdev VSRCinfo = {
    .DEVpublic = {
        .name = "vsource",
        .description = "Independent voltage source",
        .terms = 2,                          /* Positive and negative terminals */
        .numNames = 2,                       /* Instance and model names */
        .termNames = {"p", "n"},             /* Terminal names */
        .numInstanceParms = 15,              /* DC value + waveform parameters */
        .numModelParms = 3,                  /* Temperature coefficients */
    },
    .DEVmodParam = VSRC_mPTable,             /* Model parameter table */
    .DEVinstParam = VSRC_pTable,             /* Instance parameter table */
    .DEVload = VSRCload,                     /* DC/transient load function */
    .DEVsetup = VSRCsetup,                   /* Matrix setup function */
    .DEVunsetup = NULL,
    .DEVpzSetup = NULL,
    .DEVtemperature = VSRCtemp,              /* Temperature scaling */
    .DEVtrunc = VSRCtrunc,                   /* Truncation error calculation */
    .DEVfindBranch = VSRCfindBranch,
    .DEVacLoad = VSRCacLoad,                 /* AC load function */
    .DEVaccept = VSRCaccept,                 /* Breakpoint acceptance */
    .DEVdestroy = VSRCdestroy,               /* Destruction function */
    .DEVmodDelete = VSRCmDelete,
    .DEVinstDelete = VSRCdelete,
    .DEVask = VSRCask,                       /* Parameter query */
    .DEVmodAsk = VSRCmAsk,
    .DEVpzLoad = NULL,
    .DEVconvTest = VSRCconvTest,             /* Convergence test */
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVsenTrunc = NULL,
    .DEVdisto = NULL,
    .DEVnoise = NULL,
    .DEVsoaCheck = NULL,
    .DEVinstSize = sizeof(VSRCinstance),
    .DEVmodSize = sizeof(VSRCmodel),
};
```

## 2. Sparse Matrix Setup Implementation

The matrix setup function implements the MNA branch matrix allocation pattern described in section 2.2, creating the necessary sparse matrix entries for the voltage source's branch equation.

```c
/* Implementation following the DEVICEsetup pattern from section 2.2 */
int VSRCsetup(SMPmatrix *matrix, VSRCmodel *inModel, CKTcircuit *ckt, int *states) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst;
    
    for(; model; model = model->VSRCnextModel) {
        for(inst = model->VSRCinstances; inst; inst = inst->VSRCnextInstance) {
            /* Allocate matrix entries for the 3x3 MNA stamp:
             * [G   B] [V]   [I]
             * [BT  0] [I_x] = [V_s]
             * 
             * Where B is the branch incidence matrix for the source current
             */
            
            /* Diagonal entries for node equations */
            inst->VSRCposPosPtr = SMPmakeElt(matrix, inst->VSRCposNode, inst->VSRCposNode);
            inst->VSRCnegNegPtr = SMPmakeElt(matrix, inst->VSRCnegNode, inst->VSRCnegNode);
            
            /* Off-diagonal entries */
            inst->VSRCposNegPtr = SMPmakeElt(matrix, inst->VSRCposNode, inst->VSRCnegNode);
            inst->VSRCnegPosPtr = SMPmakeElt(matrix, inst->VSRCnegNode, inst->VSRCposNode);
            
            /* Branch equation entries (B matrix) */
            inst->VSRCibrPosPtr = SMPmakeElt(matrix, ckt->CKTnumStates + inst->VSRCbranch, 
                                            inst->VSRCposNode);
            inst->VSRCibrNegPtr = SMPmakeElt(matrix, ckt->CKTnumStates + inst->VSRCbranch,
                                            inst->VSRCnegNode);
            
            /* Transpose entries (BT matrix) */
            inst->VSRCposIbrPtr = SMPmakeElt(matrix, inst->VSRCposNode,
                                            ckt->CKTnumStates + inst->VSRCbranch);
            inst->VSRCnegIbrPtr = SMPmakeElt(matrix, inst->VSRCnegNode,
                                            ckt->CKTnumStates + inst->VSRCbranch);
            
            /* Branch equation diagonal (0 in the lower-right block) */
            inst->VSRCibrIbrPtr = SMPmakeElt(matrix, ckt->CKTnumStates + inst->VSRCbranch,
                                            ckt->CKTnumStates + inst->VSRCbranch);
            
            /* Allocate state variables for time-domain functions */
            inst->VSRCstate = *states;
            (*states) += 2;  /* Need states for value and derivative */
            
            /* Initialize states */
            ckt->CKTrhsOld[inst->VSRCstate] = 0.0;
            ckt->CKTrhsOld[inst->VSRCstate + 1] = 0.0;
        }
    }
    return OK;
}
```

## 3. Matrix Loading for Time-Domain Functions

The load function implements the MNA branch matrix stamping pattern from section 2.1, mapping the mathematical voltage source equations to the circuit matrix.

```c
/* DC and transient analysis load function */
int VSRCload(GENmodel *inModel, CKTcircuit *ckt) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst;
    double vs;  /* Source voltage value */
    
    for(; model; model = model->VSRCnextModel) {
        for(inst = model->VSRCinstances; inst; inst = inst->VSRCnextInstance) {
            /* Calculate voltage based on function type and time */
            switch(inst->VSRCfuncType) {
                case VSRC_DC:
                    vs = inst->VSRCdcValue;
                    break;
                    
                case VSRC_SIN:
                    /* Implement sine wave: V(t) = Vdc + ampl*sin(2π*freq*(t-delay)) */
                    vs = inst->VSRCdcValue;
                    if(ckt->CKTtime >= inst->VSRCwave.sine.delay) {
                        double t = ckt->CKTtime - inst->VSRCwave.sine.delay;
                        double arg = 2.0 * M_PI * inst->VSRCwave.sine.frequency * t;
                        vs += inst->VSRCwave.sine.amplitude * sin(arg) * 
                              exp(-inst->VSRCwave.sine.theta * t);
                    }
                    break;
                    
                case VSRC_PULSE:
                    /* Implement pulse waveform with rise/fall times */
                    vs = VSRCpulseEvaluate(ckt->CKTtime, &inst->VSRCwave.pulse);
                    break;
                    
                /* Similar cases for EXP, SFFM, PWL functions */
            }
            
            /* Apply temperature scaling if needed */
            if(model->VSRCtc1 != 0.0 || model->VSRCtc2 != 0.0) {
                double deltaT = ckt->CKTtemp - model->VSRCtnom;
                vs *= (1.0 + model->VSRCtc1 * deltaT + model->VSRCtc2 * deltaT * deltaT);
            }
            
            /* Store current value for next iteration */
            inst->VSRCprevValue = vs;
            
            /* Stamp the MNA matrix following the pattern from section 2.1:
             * [G   B] [V]   [I]
             * [BT  0] [I_x] = [V_s]
             * 
             * For voltage source between nodes i and j with branch current I_br:
             * 
             * Equation i: I_br enters node i
             * Equation j: -I_br enters node j  
             * Branch eq: V_i - V_j = V_s
             */
            
            /* B matrix entries: +1 at (branch, i), -1 at (branch, j) */
            *(inst->VSRCibrPosPtr) += 1.0;
            *(inst->VSRCibrNegPtr) += -1.0;
            
            /* BT matrix entries: +1 at (i, branch), -1 at (j, branch) */
            *(inst->VSRCposIbrPtr) += 1.0;
            *(inst->VSRCnegIbrPtr) += -1.0;
            
            /* Right-hand side vector: V_s in branch equation */
            ckt->CKTrhs[ckt->CKTnumStates + inst->VSRCbranch] += vs;
        }
    }
    return OK;
}
```

## 4. AC Analysis Implementation

The AC load function implements the frequency-domain formulation from section 5.1, converting the mathematical phasor representation to complex matrix entries.

```c
/* AC analysis load function */
int VSRCacLoad(GENmodel *inModel, CKTcircuit *ckt) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst;
    
    for(; model; model = model->VSRCnextModel) {
        for(inst = model->VSRCinstances; inst; inst = inst->VSRCnextInstance) {
            /* Convert magnitude/phase to complex voltage */
            double realPart = inst->VSRCacMag * cos(inst->VSRCacPhase);
            double imagPart = inst->VSRCacMag * sin(inst->VSRCacPhase);
            
            /* Following the linearized system from section 5.1:
             * (J + jωC) * ΔX = B
             * 
             * For voltage source, Jacobian entries are the same as DC,
             * and the excitation B contains the complex source voltage.
             */
            
            /* Stamp B matrix entries (same pattern as DC) */
            *(inst->VSRCibrPosPtr) += 1.0;
            *(inst->VSRCibrNegPtr) += -1.0;
            
            /* Stamp BT matrix entries */
            *(inst->VSRCposIbrPtr) += 1.0;
            *(inst->VSRCnegIbrPtr) += -1.0;
            
            /* Complex RHS vector for AC analysis */
            ckt->CKTirhs[ckt->CKTnumStates + inst->VSRCbranch] += realPart;
            ckt->CKTirhs[ckt->CKTnumStates + inst->VSRCbranch] += imagPart;
        }
    }
    return OK;
}
```

## 5. Time-Step Control and Truncation Error

The truncation function implements the LTE control mathematics from section 4.2, calculating the second derivative for adaptive time-step control.

```c
/* Truncation error calculation following section 4.2 */
int VSRCtrunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst;
    double newDelta, diff;
    
    for(; model; model = model->VSRCnextModel) {
        for(inst = model->VSRCinstances; inst; inst = inst->VSRCnextInstance) {
            /* Calculate second derivative for LTE estimation
             * LTE = (h²/12) * |d²V/dt²|  (from section 4.2)
             */
            double deriv = 0.0;
            
            switch(inst->VSRCfuncType) {
                case VSRC_SIN:
                    /* d²/dt²[sin(ωt)] = -ω² sin(ωt) */
                    if(ckt->CKTtime >= inst->VSRCwave.sine.delay) {
                        double t = ckt->CKTtime - inst->VSRCwave.sine.delay;
                        double arg = 2.0 * M_PI * inst->VSRCwave.sine.frequency * t;
                        double omega = 2.0 * M_PI * inst->VSRCwave.sine.frequency;
                        deriv = -omega * omega * inst->VSRCwave.sine.amplitude * 
                                sin(arg) * exp(-inst->VSRCwave.sine.theta * t);
                    }
                    break;
                    
                /* Similar calculations for other waveform types */
            }
            
            /* Store derivative for next step */
            double prevDeriv = inst->VSRCprevDeriv;
            inst->VSRCprevDeriv = deriv;
            
            /* Estimate LTE and adjust time step */
            double lte = (*timeStep) * (*timeStep) * fabs(deriv - prevDeriv) / 12.0;
            
            if(lte > ckt->CKTtrtol * fabs(inst->VSRCprevValue)) {
                /* Reduce time step following: h_new = h_old * √(RELtol * |V| / LTE) */
                newDelta = *timeStep * sqrt(ckt->CKTreltol * fabs(inst->VSRCprevValue) / lte);
                newDelta = MAX(newDelta, *timeStep * 0.1);  /* Don't reduce too much */
                newDelta = MIN(newDelta, *timeStep * 0.5);  /* Conservative reduction */
                
                if(newDelta < *timeStep) {
                    *timeStep = newDelta;
                }
            }
        }
    }
    return OK;
}
```

## 6. Convergence Testing

The convergence test implements the tolerance checking mathematics from section 4.3, ensuring Newton-Raphson iteration convergence.

```c
/* Convergence test following section 4.3 */
int VSRCconvTest(GENmodel *inModel, CKTcircuit *ckt) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst;
    int converged = 1;
    
    for(; model; model = model->VSRCnextModel) {
        for(inst = model->VSRCinstances; inst; inst = inst->VSRCnextInstance) {
            /* Check branch current convergence */
            double oldIbr = ckt->CKTstate0[inst->VSRCstate];
            double newIbr = ckt->CKTrhs[ckt->CKTnumStates + inst->VSRCbranch];
            double deltaIbr = newIbr - oldIbr;
            
            /* Apply convergence criteria from section 4.3:
             * |Δx| < ABSTOL OR |Δx| < RELTOL * max(|x|, |x_old|)
             */
            double absTol = ckt->CKTabstol;
            double relTol = ckt->CKTreltol;
            
            if(fabs(deltaIbr) > absTol) {
                double maxCurrent = MAX(fabs(newIbr), fabs(oldIbr));
                if(fabs(deltaIbr) > relTol * maxCurrent) {
                    converged = 0;
                    break;
                }
            }
            
            /* Update state for next iteration */
            ckt->CKTstate0[inst->VSRCstate] = newIbr;
        }
        if(!converged) break;
    }
    
    return converged ? OK : E_NOT_CONVERGED;
}
```

## 7. Temperature Scaling Implementation

The temperature function implements the scaling mathematics from section 10.1, adjusting parameters based on circuit temperature.

```c
/* Temperature scaling following section 10.1 */
int VSRCtemp(GENmodel *inModel, CKTcircuit *ckt) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst;
    
    for(; model; model = model->VSRCnextModel) {
        /* Apply temperature scaling to model parameters */
        double deltaT = ckt->CKTtemp - model->VSRCtnom;
        
        for(inst = model->VSRCinstances; inst; inst = inst->VSRCnextInstance) {
            /* Scale DC value using quadratic formula from section 10.1:
             * P(T) = P(Tnom) * (1 + TC1*ΔT + TC2*ΔT²)
             */
            double scaleFactor = 1.0 + model->VSRCtc1 * deltaT + 
                                 model->VSRCtc2 * deltaT * deltaT;
            
            inst->VSRCdcValue *= scaleFactor;
            
            /* Scale waveform amplitudes */
            switch(inst->VSRCfuncType) {
                case VSRC_SIN:
                    inst->VSRCwave.sine.amplitude *= scaleFactor;
                    break;
                case VSRC_PULSE:
                    inst->VSRCwave.pulse.v1 *= scaleFactor;
                    inst->VSRCwave.pulse.v2 *= scaleFactor;
                    break;
                /* Similar scaling for other waveform types */
            }
        }
    }
    return OK;
}
```

## 8. Memory Management and Cleanup

The destruction functions implement the memory management pattern from section 6.2, ensuring proper cleanup of allocated resources.

```c
/* Instance deletion */
int VSRCdelete(GENmodel *inModel, GENinstance *inInst) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst = (VSRCinstance *)inInst;
    VSRCinstance *prev = NULL;
    
    /* Find and remove instance from linked list */
    for(VSRCinstance *iter = model->VSRCinstances; iter; iter = iter->VSRCnextInstance) {
        if(iter == inst) {
            if(prev) {
                prev->VSRCnextInstance = inst->VSRCnextInstance;
            } else {
                model->VSRCinstances = inst->VSRCnextInstance;
            }
            break;
        }
        prev = iter;
    }
    
    /* Free instance memory */
    FREE(inst);
    return OK;
}

/* Model deletion */
int VSRCmDelete(GENmodel **inModel) {
    VSRCmodel **model = (VSRCmodel **)inModel;
    
    if(*model) {
        /* Delete all instances first */
        VSRCinstance *inst = (*model)->VSRCinstances;
        while(inst) {
            VSRCinstance *next = inst->VSRCnextInstance;
            FREE(inst);
            inst = next;
        }
        
        /* Free model */
        FREE(*model);
        *model = NULL;
    }
    return OK;
}

/* Complete destruction following pattern from section 6.2 */
void VSRCdestroy(GENmodel **inModel) {
    GENmodel *mod = *inModel;
    VSRCmodel *model = (VSRCmodel *)mod;
    VSRCinstance *inst, *nextInst;
    
    while(model) {
        VSRCmodel *nextModel = model->VSRCnextModel;
        
        inst = model->VSRCinstances;
        while(inst) {
            nextInst = inst->VSRCnextInstance;
            
            /* Free state vectors */
            if(inst->VSRCstate0) FREE(inst->VSRCstate0);
            if(inst->VSRCstate1) FREE(inst->VSRCstate1);
            
            FREE(inst);
            inst = nextInst;
        }
        
        FREE(model);
        model = nextModel;
    }
    *inModel = NULL;
}
```

## 9. Parameter Query Interface

The ask function provides access to internal parameters, mapping C structure members to user-accessible values.

```c
/* Parameter query interface */
int VSRCask(GENmodel *inModel, GENinstance *inInst, int which, IFvalue *value) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst = (VSRCinstance *)inInst;
    
    switch(which) {
        case VSRC_DC:
            value->rValue = inst->VSRCdcValue;
            break;
        case VSRC_AC_MAG:
            value->rValue = inst->VSRCacMag;
            break;
        case VSRC_AC_PHASE:
            value->rValue = inst->VSRCacPhase;
            break;
        case VSRC_POS_NODE:
            value->iValue = inst->VSRCposNode;
            break;
        case VSRC_NEG_NODE:
            value->iValue = inst->VSRCnegNode;
            break;
        case VSRC_BRANCH:
            value->iValue = inst->VSRCbranch;
            break;
        /* Additional cases for waveform parameters */
        default:
            return E_BADPARM;
    }
    return OK;
}
```

## 10. Breakpoint Generation for Discontinuous Functions

The accept function implements breakpoint handling for waveform discontinuities, ensuring accurate simulation of piecewise functions.

```c
/* Breakpoint acceptance for PWL and PULSE functions */
int VSRCaccept(GENmodel *inModel, CKTcircuit *ckt) {
    VSRCmodel *model = (VSRCmodel *)inModel;
    VSRCinstance *inst;
    
    for(; model; model = model->VSRCnextModel) {
        for(inst = model->VSRCinstances; inst; inst = inst->VSRCnextInstance) {
            if(inst->VSRCfuncType == VSRC_PWL || inst->VSRCfuncType == VSRC_PULSE) {
                /* Calculate next discontinuity time */
                double next