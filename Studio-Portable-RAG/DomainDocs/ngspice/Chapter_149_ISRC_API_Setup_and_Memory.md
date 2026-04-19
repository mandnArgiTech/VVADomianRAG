# Independent Current Source: Parameter Binding and API Lifecycle

_Generated 2026-04-12 22:52 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrcask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrcext.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrcinit.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrcitf.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrcinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrcdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrcmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/isrc/isrcdest.c`

# Chapter: Independent Current Source: Parameter Binding and API Lifecycle

## 1. Technical Introduction

The independent current source (ISRC) in Ngspice implements a versatile current source supporting DC, AC, and transient waveforms through a comprehensive parameter binding system and well-defined API lifecycle. The source files `isrcask.c`, `isrcext.h`, `isrcinit.h`, `isrcitf.h`, `isrcinit.c`, `isrc.c`, `isrcdel.c`, `isrcmdel.c`, and `isrcdest.c` collectively manage the entire device lifecycle from netlist parsing to simulation cleanup. `isrcinit.c` binds the device to Ngspice's core via the `SPICEdev` structure, registering function pointers for matrix loading, parameter query, and memory management. `isrcask.c` implements the parameter query interface, allowing simulation scripts to retrieve instance parameters. The header files (`isrcext.h`, `isrcinit.h`, `isrcitf.h`) define the external API and internal structures. `isrc.c` contains the core implementation of waveform evaluation and matrix stamping. Memory management is handled by `isrcdel.c` (instance deletion), `isrcmdel.c` (model deletion), and `isrcdest.c` (destruction cleanup). This architecture ensures the current source integrates seamlessly with Ngspice's Modified Nodal Analysis (MNA) solver while supporting complex transient functions with numerical stability.

## 2. Mathematical Formulation

### 2.1 Fundamental Constitutive Equation
The independent current source is defined by the time-domain equation:
\[
I(t) = f(t)
\]
where \(f(t)\) represents the waveform function, which can be DC, sinusoidal, pulsed, exponential, single-frequency FM, or piecewise linear.

### 2.2 Modified Nodal Analysis (MNA) Formulation
In SPICE's Modified Nodal Analysis, the current source contributes only to the right-hand side (RHS) vector:
\[
\begin{aligned}
\text{RHS}[pos] &-= I(t) \\
\text{RHS}[neg] &+= I(t)
\end{aligned}
\]
where \(pos\) and \(neg\) are the node indices for the positive and negative terminals. The Jacobian matrix receives no entries since \(\partial I/\partial V = 0\).

### 2.3 Waveform-Specific Mathematical Functions

#### 2.3.1 SIN (Sinusoidal)
\[
I(t) = 
\begin{cases}
\text{DC} & \text{if } t < \text{TD} \\
\text{DC} + \text{AMPL} \cdot \exp(-\text{THETA} \cdot (t - \text{TD})) \cdot \sin(2\pi \cdot \text{FREQ} \cdot (t - \text{TD}) + \text{PHASE}) & \text{if } t \geq \text{TD}
\end{cases}
\]

#### 2.3.2 PULSE
\[
I(t) = 
\begin{cases}
\text{V1} & \text{if } t < \text{TD} \\
\text{V1} + (\text{V2} - \text{V1}) \cdot \frac{t - \text{TD}}{\text{TR}} & \text{if } \text{TD} \leq t < \text{TD} + \text{TR} \\
\text{V2} & \text{if } \text{TD} + \text{TR} \leq t < \text{TD} + \text{TR} + \text{PW} \\
\text{V2} - (\text{V2} - \text{V1}) \cdot \frac{t - (\text{TD} + \text{TR} + \text{PW})}{\text{TF}} & \text{if } \text{TD} + \text{TR} + \text{PW} \leq t < \text{TD} + \text{TR} + \text{PW} + \text{TF} \\
\text{V1} & \text{if } t \geq \text{TD} + \text{TR} + \text{PW} + \text{TF} + \text{PER} \cdot n
\end{cases}
\]

#### 2.3.3 EXP (Exponential)
\[
I(t) =
\begin{cases}
\text{V1} & t < \text{TD1} \\
\text{V1} + (\text{V2} - \text{V1}) \cdot (1 - \exp(-(t - \text{TD1})/\text{TAU1})) & \text{TD1} \leq t < \text{TD2} \\
\text{V1} + (\text{V2} - \text{V1}) \cdot (1 - \exp(-(t - \text{TD1})/\text{TAU1})) + (\text{V1} - \text{V2}) \cdot (1 - \exp(-(t - \text{TD2})/\text{TAU2})) & t \geq \text{TD2}
\end{cases}
\]

#### 2.3.4 SFFM (Single-Frequency FM)
\[
I(t) = \text{DC} + \text{AMPL} \cdot \sin(2\pi \cdot \text{FC} \cdot t + \text{MOD} \cdot \sin(2\pi \cdot \text{FM} \cdot t))
\]

#### 2.3.5 PWL (Piecewise Linear)
\[
I(t) = \text{V}_i + \frac{\text{V}_{i+1} - \text{V}_i}{t_{i+1} - t_i} \cdot (t - t_i) \quad \text{for } t_i \leq t < t_{i+1}
\]

### 2.4 Complex Frequency Domain Representation
For AC analysis, the source becomes a complex phasor:
\[
I(\omega) = \text{MAG} \cdot \exp(j \cdot \text{PHASE})
\]
where \(j = \sqrt{-1}\), MAG is the AC magnitude, and PHASE is the phase in radians.

### 2.5 Temperature Scaling
The DC value scales with temperature according to:
\[
I(T) = I(T_0) \cdot [1 + \text{TC1} \cdot (T - T_0) + \text{TC2} \cdot (T - T_0)^2]
\]
where TC1 and TC2 are temperature coefficients.

### 2.6 Breakpoint Generation
For waveforms with discontinuities (PULSE, PWL edges), breakpoints are generated at times \(t_i\) where \(I(t)\) or its derivative is discontinuous. These breakpoints ensure the transient analysis time-step aligns with waveform changes.

### 2.7 Local Truncation Error (LTE) Formulation
The time-step control uses the second derivative:
\[
\text{LTE} = \frac{1}{2} h^2 \cdot |I''(t)|
\]
where \(h\) is the time-step. The simulator adjusts \(h\) to keep LTE below \(\text{trtol} \cdot \max(|I(t)|, \text{abstol})\).

### 2.8 Convergence Analysis
The independent current source exhibits trivial Newton-Raphson convergence since \(\partial I/\partial V = 0\). The convergence criteria are:
1. **Discontinuity Handling**: Breakpoints force time-step reduction to exact discontinuity times.
2. **LTE Control**: Time-step is adapted to bound integration error.
3. **Charge Conservation**: For piecewise linear segments, the integrated charge over each segment matches the analytical integral.
4. **Numerical Stability**: The explicit dependence on time only (not voltage) eliminates convergence oscillations.

## 3. C Implementation

### 3.1 Core Data Structures and SPICEdev API Binding

```c
/* From isrcdefs.h */
typedef struct sISRCinstance {
    struct sISRCmodel *ISRCmodPtr;    /* Pointer to model */
    struct sISRCinstance *ISRCnextInstance; /* Linked list */
    char *ISRCname;                   /* Instance name */
    
    /* Node connections */
    int ISRCposNode;                  /* Positive node */
    int ISRCnegNode;                  /* Negative node */
    
    /* Parameters */
    int ISRCfuncType;                 /* Waveform type: ISRC_DC, ISRC_SIN, etc. */
    double ISRCdcValue;               /* DC value */
    double ISRCacMag;                 /* AC magnitude */
    double ISRCacPhase;               /* AC phase (degrees) */
    
    /* Transient waveform coefficients (union) */
    union {
        struct {
            double amplitude, freq, td, theta, phase;
        } sin;
        struct {
            double v1, v2, td, tr, tf, pw, per;
        } pulse;
        struct {
            double v1, v2, td1, tau1, td2, tau2;
        } exp;
        struct {
            double vo, va, fc, mdi, fs;
        } sffm;
        struct {
            double *times, *values;
            int count;
        } pwl;
    } ISRCcoeffs;
    
    /* State variables */
    double ISRCprevValue;             /* Previous time-step value */
    double ISRCbreakTime;             /* Next breakpoint time */
} ISRCinstance;

typedef struct sISRCmodel {
    int ISRCmodType;                  /* Model type */
    struct sISRCmodel *ISRCnextModel; /* Linked list */
    ISRCinstance *ISRCinstances;      /* Instance list */
    double ISRCtnom;                  /* Nominal temperature */
} ISRCmodel;

/* SPICEdev structure binding */
SPICEdev ISRCinfo = {
    .DEVpublic = {
        .name = "I",
        .description = "Independent current source",
        .terms = 2,
        .numNames = 1,
        .termNames = (char *[]){"+", "-"},
        .numInstanceParms = 20,
        .instanceParms = ISRCpTable,
        .numModelParms = 0,
        .modelParms = NULL
    },
    .DEVparam = ISRCparam,
    .DEVmodParam = NULL,
    .DEVload = ISRCload,
    .DEVsetup = ISRCsetup,
    .DEVunsetup = NULL,
    .DEVpzSetup = NULL,
    .DEVtemperature = ISRCtemp,
    .DEVtrunc = ISRCtrunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = ISRCacLoad,
    .DEVaccept = ISRCaccept,
    .DEVdestroy = ISRCdestroy,
    .DEVmodDelete = ISRCmDelete,
    .DEVdelete = ISRCdelete,
    .DEVsetic = NULL,
    .DEVask = ISRCask,
    .DEVmodAsk = NULL,
    .DEVpzLoad = NULL,
    .DEVconvTest = NULL,
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVdisto = NULL,
    .DEVnoise = NULL,
    .DEVsoaCheck = NULL
};
```

### 3.2 Parameter Binding and Validation System

```c
/* From isrcpar.c */
int ISRCparam(int param, IFvalue *value, GENinstance *genInstance, IFvalue *select) {
    ISRCinstance *instance = (ISRCinstance *)genInstance;
    
    switch(param) {
        case ISRC_DC:
            instance->ISRCdcValue = value->rValue;
            instance->ISRCfuncType = ISRC_DC;
            break;
        case ISRC_AC:
            instance->ISRCacMag = value->rValue;
            instance->ISRCacPhase = value->rValue2;
            break;
        case ISRC_SIN:
            instance->ISRCfuncType = ISRC_SIN;
            instance->ISRCcoeffs.sin.amplitude = value->v.vec.rVec[0];
            instance->ISRCcoeffs.sin.freq = value->v.vec.rVec[1];
            instance->ISRCcoeffs.sin.td = value->v.vec.rVec[2];
            instance->ISRCcoeffs.sin.theta = value->v.vec.rVec[3];
            instance->ISRCcoeffs.sin.phase = value->v.vec.rVec[4];
            break;
        /* Similar cases for PULSE, EXP, SFFM, PWL */
    }
    return OK;
}
```

### 3.3 Matrix Setup and RHS Loading Implementation

```c
/* From isrcload.c */
int ISRCload(GENmodel *genModel, CKTcircuit *ckt) {
    ISRCmodel *model = (ISRCmodel *)genModel;
    ISRCinstance *instance;
    
    for(; model != NULL; model = model->ISRCnextModel) {
        for(instance = model->ISRCinstances; instance != NULL; 
            instance = instance->ISRCnextInstance) {
            
            double current;
            
            /* Evaluate waveform based on type */
            switch(instance->ISRCfuncType) {
                case ISRC_DC:
                    current = instance->ISRCdcValue;
                    break;
                case ISRC_SIN:
                    current = ISRCsineEvaluate(ckt->CKTtime, &instance->ISRCcoeffs.sin);
                    break;
                case ISRC_PULSE:
                    current = ISRCpulseEvaluate(ckt->CKTtime, &instance->ISRCcoeffs.pulse);
                    break;
                /* Other waveform types */
            }
            
            /* Apply temperature scaling */
            if(ckt->CKTtemp != model->ISRCtnom) {
                double deltaT = ckt->CKTtemp - model->ISRCtnom;
                current *= (1.0 + instance->ISRCtc1 * deltaT + 
                           instance->ISRCtc2 * deltaT * deltaT);
            }
            
            /* Stamp into RHS vector (mathematical mapping: RHS[pos] -= I, RHS[neg] += I) */
            ckt->CKTrhs[instance->ISRCposNode] -= current;
            ckt->CKTrhs[instance->ISRCnegNode] += current;
            
            instance->ISRCprevValue = current;
        }
    }
    return OK;
}
```

### 3.4 AC Analysis Complex Phasor Implementation

```c
/* From isrcacld.c */
int ISRCacLoad(GENmodel *genModel, CKTcircuit *ckt) {
    ISRCmodel *model = (ISRCmodel *)genModel;
    ISRCinstance *instance;
    
    for(; model != NULL; model = model->ISRCnextModel) {
        for(instance = model->ISRCinstances; instance != NULL;
            instance = instance->ISRCnextInstance) {
            
            if(ckt->CKTmode & MODEAC) {
                /* Convert magnitude/phase to complex phasor */
                double mag = instance->ISRCacMag;
                double phase = instance->ISRCacPhase * M_PI / 180.0;
                double real = mag * cos(phase);
                double imag = mag * sin(phase);
                
                /* Stamp complex current into RHS */
                ckt->CKTrhs[instance->ISRCposNode] -= real;
                ckt->CKTirhs[instance->ISRCposNode] -= imag;
                ckt->CKTrhs[instance->ISRCnegNode] += real;
                ckt->CKTirhs[instance->ISRCnegNode] += imag;
            }
        }
    }
    return OK;
}
```

### 3.5 Breakpoint Generation for Discontinuities

```c
/* From isrcacct.c */
int ISRCaccept(GENmodel *genModel, CKTcircuit *ckt) {
    ISRCmodel *model = (ISRCmodel *)genModel;
    ISRCinstance *instance;
    
    for(; model != NULL; model = model->ISRCnextModel) {
        for(instance = model->ISRCinstances; instance != NULL;
            instance = instance->ISRCnextInstance) {
            
            double nextBreak = INFINITY;
            
            /* Calculate next discontinuity based on waveform type */
            switch(instance->ISRCfuncType) {
                case ISRC_PULSE:
                    nextBreak = calculatePulseBreakpoint(ckt->CKTtime, 
                                                        &instance->ISRCcoeffs.pulse);
                    break;
                case ISRC_PWL:
                    nextBreak = findNextPWLBreaKpoint(ckt->CKTtime,
                                                     instance->ISRCcoeffs.pwl.times,
                                                     instance->ISRCcoeffs.pwl.count);
                    break;
            }
            
            if(nextBreak < INFINITY) {
                /* Register breakpoint with simulator */
                CKTbreak(ckt, nextBreak);
                instance->ISRCbreakTime = nextBreak;
            }
        }
    }
    return OK;
}
```

### 3.6 Time-Step Control via Local Truncation Error

```c
/* From isrctrunc.c */
int ISRCtrunc(GENmodel *genModel, CKTcircuit *ckt, double *timeStep) {
    ISRCmodel *model = (ISRCmodel *)genModel;
    ISRCinstance *instance;
    double newTimeStep = *timeStep;
    
    for(; model != NULL; model = model->ISRCnextModel) {
        for(instance = model->ISRCinstances; instance != NULL;
            instance = instance->ISRCnextInstance) {
            
            /* Calculate second derivative for LTE (mathematical mapping: LTE = ½h²|I''|) */
            double secondDeriv = calculateSecondDerivative(ckt->CKTtime,
                                                          instance->ISRCfuncType,
                                                          &instance->ISRCcoeffs);
            double lte = 0.5 * (*timeStep) * (*timeStep) * fabs(secondDeriv);
            double maxCurrent = fmax(fabs(instance->ISRCprevValue), ckt->CKTabstol);
            double allowedError = ckt->CKTtrtol * maxCurrent;
            
            if(lte > allowedError) {
                /* Reduce time-step (mathematical stability criterion) */
                double factor = sqrt(allowedError / (lte + 1e-30));
                newTimeStep = fmin(newTimeStep, (*timeStep) * factor);
            }
        }
    }
    
    *timeStep = newTimeStep;
    return OK;
}
```

### 3.7 Temperature Scaling Implementation

```c
/* From isrctemp.c */
int ISRCtemp(GENmodel *genModel, CKTcircuit *ckt) {
    ISRCmodel *model = (ISRCmodel *)genModel;
    
    for(; model != NULL; model = model->ISRCnextModel) {
        /* Update all instance DC values based on temperature */
        ISRCinstance *instance;
        for(instance = model->ISRCinstances; instance != NULL;
            instance = instance->ISRCnextInstance) {
            
            if(instance->ISRCtc1 != 0.0 || instance->ISRCtc2 != 0.0) {
                double deltaT = ckt->CKTtemp - model->ISRCtnom;
                double scale = 1.0 + instance->ISRCtc1 * deltaT + 
                              instance->ISRCtc2 * deltaT * deltaT;
                
                /* Scale DC value (mathematical mapping: I(T) = I(T₀)·[1 + TC1·ΔT + TC2·ΔT²]) */
                instance->ISRCdcValue *= scale;
            }
        }
    }
    return OK;
}
```

### 3.8 Memory Management and Lifecycle Functions

```c
/* From isrcdest.c */
int ISRCdestroy(GENmodel **genModel) {
    ISRCmodel *model = (ISRCmodel *)*genModel;
    ISRCinstance *instance, *nextInstance;
    
    while(model) {
        ISRCmodel *nextModel = model->ISRCnextModel;
        
        /* Free all instances */
        for(instance = model->ISRCinstances; instance != NULL; instance = nextInstance) {
            nextInstance = instance->ISRCnextInstance;
            
            /* Free PWL arrays if allocated */
            if(instance->ISRCfuncType == ISRC_PWL) {
                FREE(instance->ISRCcoeffs.pwl.times);
                FREE(instance->ISRCcoeffs.pwl.values);
            }
            
            FREE(instance->ISRCname);
            FREE(instance);
        }
        
        FREE(model);
        model = nextModel;
    }
    
    *genModel = NULL;
    return OK;
}
```

### 3.9 Parameter Query Interface

```c
/* From isrcask.c */
int ISRCask(const CKTcircuit *ckt, const GENinstance *genInstance, int param, IFvalue *value) {
    const ISRCinstance *instance = (const ISRCinstance *)genInstance;
    
    switch(param) {
        case ISRC_DC:
            value->rValue = instance->ISRCdcValue;
            break;
        case ISRC_AC_MAG:
            value->rValue = instance->ISRCacMag;
            break;
        case ISRC_AC_PHASE:
            value->rValue = instance->ISRCacPhase;
            break;
        case ISRC_POS_NODE:
            value->iValue = instance->ISRCposNode;
            break;
        case ISRC_NEG_NODE:
            value->iValue = instance->ISRCnegNode;
            break;
        /* Other parameters */
        default:
            return E_BADPARM;
    }
    return OK;
}
```

### 3.10 Implementation Summary: Mathematics-to-Code Mapping

The C implementation directly maps mathematical formulations to Ngspice's simulation framework:

1. **Waveform Equations** → `ISRCsineEvaluate()`, `ISRCpulseEvaluate()`, etc.
2. **MNA RHS Stamping** → `ISRCload()` with `CKTrhs[]` updates
3. **Complex Phasor** → `ISRCacLoad()` with real/imaginary components
4. **Temperature Scaling** → `ISRCtemp()` applying quadratic formula
5. **LTE Calculation** → `ISRCtrunc()` computing second derivatives
6. **Discontinuity Handling** → `ISRCaccept()` generating breakpoints
7. **Parameter Binding** → `ISRCparam()` validating and storing coefficients
8. **API Lifecycle** → `ISRCinfo` structure with function pointers

The implementation ensures numerical stability through proper breakpoint generation, LTE-based time-step control, and exact mathematical evaluation of waveform functions. The zero Jacobian contribution guarantees single-iteration convergence in Newton-Raphson solves, making the independent current source computationally efficient within SPICE's nonlinear solver framework.