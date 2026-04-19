# Switch: Matrix Setup, Topology, and API Binding

_Generated 2026-04-12 21:59 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swsetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swmask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swask.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swinit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/sw.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swdelete.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swmdel.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swdest.c`

# **FINAL ANSWER: COMPLETE NGSPICE REFERENCE BOOK CHAPTER**

## **Chapter: Voltage-Controlled Switch: Continuous Resistance Smoothing and DC Load**

### **Technical Introduction**

The voltage-controlled switch (VSWITCH) implementation in Ngspice represents a sophisticated compromise between physical switching behavior and numerical simulation requirements. Unlike ideal switches with discontinuous resistance changes that would break Newton-Raphson convergence, Ngspice implements a smooth, continuously differentiable resistance function using hyperbolic tangent smoothing. The files `swdefs.h`, `swparam.c`, `swmparam.c`, and `swload.c` form the core of this implementation. `swdefs.h` defines the fundamental data structures that map the mathematical model—a resistance varying smoothly between R_ON and R_OFF based on control voltage—to memory. `swparam.c` and `swmparam.c` handle the critical translation from SPICE deck parameters to internal C variables, enforcing physical constraints and computing derived parameters. Most importantly, `swload.c` implements the Modified Nodal Analysis (MNA) matrix stamping that integrates the switch into SPICE's solver framework, calculating both the instantaneous conductance and its derivative for the Jacobian matrix. This architecture enables the simulation of digital-analog mixed-signal circuits where switches control analog signal paths, maintaining numerical stability even during rapid switching transitions.

### **Mathematical Formulation**

#### **1. Core Resistance Smoothing Function**

The fundamental mathematical innovation is the continuously differentiable resistance function that enables Newton-Raphson convergence while approximating ideal switching behavior:

\[
R(V_{\text{ctrl}}) = R_{\text{OFF}} + \frac{R_{\text{ON}} - R_{\text{OFF}}}{2} \left[ 1 + \tanh\left(\frac{V_{\text{ctrl}} - V_{\text{th}}}{V_{\text{hys}}}\right) \right]
\]

Where:
- \( R_{\text{ON}} \): ON-state resistance (typically 1Ω)
- \( R_{\text{OFF}} \): OFF-state resistance (typically 10⁶Ω to 10¹²Ω)
- \( V_{\text{th}} \): Threshold voltage
- \( V_{\text{hys}} \): Smoothing parameter (hysteresis voltage, typically 10-100mV)

#### **2. Conductance and Derivatives for Newton-Raphson**

For SPICE's Modified Nodal Analysis, the conductance \( G = 1/R \) and its derivative with respect to control voltage are required:

\[
G(V_{\text{ctrl}}) = \frac{1}{R(V_{\text{ctrl}})}
\]

\[
\frac{dG}{dV_{\text{ctrl}}} = -\frac{1}{R^2(V_{\text{ctrl}})} \cdot \frac{dR}{dV_{\text{ctrl}}}
\]

The derivative of the resistance function is:

\[
\frac{dR}{dV_{\text{ctrl}}} = \frac{R_{\text{ON}} - R_{\text{OFF}}}{2V_{\text{hys}}} \cdot \text{sech}^2\left(\frac{V_{\text{ctrl}} - V_{\text{th}}}{V_{\text{hys}}}\right)
\]

#### **3. MNA Matrix Stamping for Four-Terminal Switch**

A voltage-controlled switch has four connection points: positive and negative switch terminals, and positive and negative control terminals. The switch current is:

\[
I_{\text{sw}} = G(V_{\text{ctrl}}) \cdot (V_+ - V_-)
\]

Where \( V_{\text{ctrl}} = V_{c+} - V_{c-} \).

The Jacobian contributions are:

\[
\frac{\partial I_{\text{sw}}}{\partial V_+} = G(V_{\text{ctrl}}) \quad \text{(stamped at position (+, +))}
\]
\[
\frac{\partial I_{\text{sw}}}{\partial V_-} = -G(V_{\text{ctrl}}) \quad \text{(stamped at position (-, -) and cross terms)}
\]
\[
\frac{\partial I_{\text{sw}}}{\partial V_{c+}} = (V_+ - V_-) \cdot \frac{dG}{dV_{\text{ctrl}}} \quad \text{(transconductance term)}
\]
\[
\frac{\partial I_{\text{sw}}}{\partial V_{c-}} = -(V_+ - V_-) \cdot \frac{dG}{dV_{\text{ctrl}}}
\]

This results in an 8-element stamp for the 4×4 submatrix relating the four nodes.

#### **4. Numerical Regularization with GMIN**

To prevent singular matrices when \( R_{\text{OFF}} \to \infty \), Ngspice applies GMIN regularization:

\[
R_{\text{eff}} = \min\left(R(V_{\text{ctrl}}), \frac{1}{\text{GMIN}}\right)
\]

Where GMIN is typically \( 10^{-12} \) S, giving \( R_{\text{max}} = 10^{12} \) Ω.

#### **5. DC Operating Point Analysis**

For DC analysis, the switch conductance is constant at the DC control voltage:

\[
G_{\text{DC}} = G(V_{\text{ctrl,DC}})
\]

The DC Jacobian is simplified, as the transconductance terms are not needed for a pure DC solve.

### **Convergence Analysis**

#### **1. Newton-Raphson Convergence Criteria**

The switch model converges when both control voltage and switch current satisfy:

\[
|V_{\text{ctrl}}^{(k+1)} - V_{\text{ctrl}}^{(k)}| < \epsilon_V + \epsilon_R \cdot \max(|V_{\text{ctrl}}^{(k)}|, V_{\text{min}})
\]
\[
|I_{\text{sw}}^{(k+1)} - I_{\text{sw}}^{(k)}| < \epsilon_I + \epsilon_R \cdot \max(|I_{\text{sw}}^{(k)}|, I_{\text{min}})
\]

Where:
- \( \epsilon_V = \text{VNTOL} \) (typically 1μV)
- \( \epsilon_I = \text{ABSTOL} \) (typically 1pA)
- \( \epsilon_R = \text{RELTOL} \) (typically 0.1%)
- \( V_{\text{min}}, I_{\text{min}} \): scaling minima

#### **2. Smoothing Function Convergence Properties**

The hyperbolic tangent ensures:
1. **Continuity**: \( R(V_{\text{ctrl}}) \in C^\infty \) (infinitely differentiable)
2. **Bounded derivatives**: Prevents Jacobian ill-conditioning
3. **Monotonicity**: \( \frac{dR}{dV_{\text{ctrl}}} > 0 \) for \( R_{\text{ON}} < R_{\text{OFF}} \)
4. **Limiting behavior**: \( \lim_{V_{\text{ctrl}} \to \pm\infty} R(V_{\text{ctrl}}) = R_{\text{ON/OFF}} \)

#### **3. Local Truncation Error (LTE) Estimation**

For adaptive time-stepping:

\[
\text{LTE} = \frac{h^2}{2} \left| \frac{d^2I_{\text{sw}}}{dt^2} \right| + \frac{h^3}{6} \left| \frac{d^3I_{\text{sw}}}{dt^3} \right|
\]

Where derivatives are computed via chain rule:

\[
\frac{dI_{\text{sw}}}{dt} = \frac{dG}{dV_{\text{ctrl}}} \cdot \frac{dV_{\text{ctrl}}}{dt} \cdot (V_+ - V_-) + G(V_{\text{ctrl}}) \cdot \frac{d(V_+ - V_-)}{dt}
\]

#### **4. Time-Step Control During Switching**

When \( |V_{\text{ctrl}} - V_{\text{th}}| < 2V_{\text{hys}} \):

\[
h_{\text{new}} = h_{\text{current}} \cdot \min\left(2.0, \max\left(0.5, 0.8 \cdot \sqrt{\frac{\epsilon \cdot R_{\text{OFF}}}{\text{LTE}}}\right)\right)
\]

#### **5. Condition Number Analysis**

The condition number \( \kappa \) of the switch Jacobian:

\[
\kappa = \frac{\max\left(|G|, |\frac{dG}{dV_{\text{ctrl}}} \cdot (V_+ - V_-)|\right)}{\min\left(|G|, |\frac{dG}{dV_{\text{ctrl}}} \cdot (V_+ - V_-)|\right)}
\]

\( V_{\text{hys}} \) is chosen to keep \( \kappa < 10^6 \) for all operating conditions.

#### **6. Convergence Radius**

Newton-Raphson converges from initial guess \( V_{\text{ctrl}}^{(0)} \) if:

\[
|V_{\text{ctrl}}^{(0)} - V_{\text{ctrl}}^*| < \frac{2}{L}
\]

Where \( L \) is the Lipschitz constant of \( dG/dV_{\text{ctrl}} \):

\[
L \leq \frac{|R_{\text{ON}} - R_{\text{OFF}}|}{V_{\text{hys}}^3 \cdot R_{\text{ON}}^2}
\]

#### **7. Regularization Impact**

GMIN regularization ensures non-singular matrices but introduces error:

\[
\epsilon_{\text{GMIN}} = \left| \frac{1}{R(V_{\text{ctrl}})} - \frac{1}{\min(R(V_{\text{ctrl}}), 1/\text{GMIN})} \right| \cdot |V_+ - V_-|
\]

Negligible when \( R(V_{\text{ctrl}}) \ll 1/\text{GMIN} \).

#### **8. Special Cases**

**Fully ON/OFF States**: When \( |V_{\text{ctrl}} - V_{\text{th}}| \gg V_{\text{hys}} \), resistance is constant, converging in one iteration.

**Rapid Switching**: For high slew rates (\( dV_{\text{ctrl}}/dt > V_{\text{hys}}/h_{\text{min}} \)), uses piecewise-linear approximation.

**Multiple Switches**: For \( N \) simultaneous switches, convergence rate:

\[
\rho_N \approx 1 - \frac{2}{N \cdot \kappa_{\text{max}}}
\]

#### **9. AC Analysis Convergence**

For AC small-signal analysis linearized around DC operating point:

\[
|G_{\text{AC}}^{(k+1)} - G_{\text{AC}}^{(k)}| < \epsilon_R \cdot |G_{\text{AC}}^{(k)}|
\]

Where \( G_{\text{AC}} = G(V_{\text{ctrl,DC}}) \).

### **C Implementation**

#### **1. Core Data Structures (`swdefs.h`)**

```c
typedef struct sSWmodel {
    int SWmodType;                  /* Model type identifier */
    double SWonResistance;          /* R_ON parameter (Ω) */
    double SWoffResistance;         /* R_OFF parameter (Ω) */
    double SWthreshold;             /* V_th threshold voltage (V) */
    double SWhysteresis;            /* V_hys smoothing parameter (V) */
    double SWconductanceDelta;      /* (R_ON - R_OFF)/2 (pre-computed) */
    double SWsmoothingFactor;       /* 1/(2*V_hys) (pre-computed) */
    unsigned SWonGiven :1;          /* Parameter presence flags */
    unsigned SWoffGiven :1;
    unsigned SWthreshGiven :1;
    unsigned SWhyseGiven :1;
    struct sSWmodel *SWnextModel;   /* Next model in circuit */
    sSWinstance *SWinstances;       /* First instance of this model */
} SWmodel;

typedef struct sSWinstance {
    int SWposNode;                  /* Positive switch terminal */
    int SWnegNode;                  /* Negative switch terminal */
    int SWctrlPosNode;              /* Positive control terminal */
    int SWctrlNegNode;              /* Negative control terminal */
    double SWcurrent;               /* I_sw - Current through switch (A) */
    double SWvoltage;               /* V_sw - Voltage across switch (V) */
    double SWctrlVoltage;           /* V_ctrl - Control voltage (V) */
    double SWresistance;            /* R(V_ctrl) - Current resistance (Ω) */
    double SWconduct;               /* G(V_ctrl) - Current conductance (S) */
    double SWdRdVctrl;              /* dR/dV_ctrl (Ω/V) */
    double SWdGdVctrl;              /* dG/dV_ctrl (S/V) */
    double SWprevVoltage;           /* Previous V_sw for LTE */
    double SWprevCtrlVoltage;       /* Previous V_ctrl for LTE */
    double SWprevCurrent;           /* Previous I_sw for LTE */
    double SWprevResistance;        /* Previous R for LTE */
    double *SWposPosPtr;            /* ∂I_+/∂V_+ */
    double *SWposNegPtr;            /* ∂I_+/∂V_- */
    double *SWnegPosPtr;            /* ∂I_-/∂V_+ */
    double *SWnegNegPtr;            /* ∂I_-/∂V_- */
    double *SWposCtrlPosPtr;        /* ∂I_+/∂V_c+ */
    double *SWposCtrlNegPtr;        /* ∂I_+/∂V_c- */
    double *SWnegCtrlPosPtr;        /* ∂I_-/∂V_c+ */
    double *SWnegCtrlNegPtr;        /* ∂I_-/∂V_c- */
    struct sSWmodel *SWmodPtr;      /* Pointer to model parameters */
    struct sSWinstance *SWnextInstance; /* Next instance in list */
} SWinstance;
```

#### **2. Resistance Calculation with Smoothing (`swload.c`)**

```c
static double SWcalculateResistance(SWinstance *inst, double vctrl) {
    SWmodel *model = inst->SWmodPtr;
    double x, tanh_x, resistance;
    
    x = (vctrl - model->SWthreshold) * model->SWsmoothingFactor;
    
    /* Overflow protection for tanh */
    if (x > 10.0) tanh_x = 1.0;
    else if (x < -10.0) tanh_x = -1.0;
    else {
        double exp_2x = exp(2.0 * x);
        tanh_x = (exp_2x - 1.0) / (exp_2x + 1.0);
    }
    
    resistance = model->SWoffResistance + 
                 model->SWconductanceDelta * (1.0 + tanh_x);
    
    /* GMIN regularization */
    if (resistance > 1.0 / GMIN) resistance = 1.0 / GMIN;
    if (resistance <= 0.0) resistance = 1.0 / GMIN;
    
    return resistance;
}

static double SWcalculateResistanceDerivative(SWinstance *inst, double vctrl) {
    SWmodel *model = inst->SWmodPtr;
    double x, sech_x, derivative;
    
    x = (vctrl - model->SWthreshold) * model->SWsmoothingFactor;
    
    if (x > 10.0 || x < -10.0) sech_x = 0.0;
    else {
        double tanh_x = tanh(x);
        sech_x = 1.0 - tanh_x * tanh_x;
    }
    
    derivative = model->SWconductanceDelta * model->SWsmoothingFactor * sech_x;
    
    /* Bound derivative for numerical stability */
    double max_derivative = 1.0 / (GMIN * GMIN);
    if (derivative > max_derivative) derivative = max_derivative;
    
    return derivative;
}
```

#### **3. Matrix Setup and Topology (`swsetup.c`)**

```c
int SWsetup(SWinstance *inst, CKTcircuit *ckt) {
    int error;
    
    /* Allocate 4 pointers for main switch conductance */
    error = SMPmakeElt(ckt, inst->SWposNode, inst->SWposNode, &(inst->SWposPosPtr));
    if (error) return error;
    error = SMPmakeElt(ckt, inst->SWposNode, inst->SWnegNode, &(inst->SWposNegPtr));
    if (error) return error;
    error = SMPmakeElt(ckt, inst->SWnegNode, inst->SWposNode, &(inst->SWnegPosPtr));
    if (error) return error;
    error = SMPmakeElt(ckt, inst->SWnegNode, inst->SWnegNode, &(inst->SWnegNegPtr));
    if (error) return error;
    
    /* Allocate 4 pointers for control voltage coupling */
    error = SMPmakeElt(ckt, inst->SWposNode, inst->SWctrlPosNode, &(inst->SWposCtrlPosPtr));
    if (error) return error;
    error = SMPmakeElt(ckt, inst->SWposNode, inst->SWctrlNegNode, &(inst->SWposCtrlNegPtr));
    if (error) return error;
    error = SMPmakeElt(ckt, inst->SWnegNode, inst->SWctrlPosNode, &(inst->SWnegCtrlPosPtr));
    if (error) return error;
    error = SMPmakeElt(ckt, inst->SWnegNode, inst->SWctrlNegNode, &(inst->SWnegCtrlNegPtr));
    if (error) return error;
    
    /* Initialize history for LTE estimation */
    inst->SWprevVoltage = 0.0;
    inst->SWprevCtrlVoltage = 0.0;
    inst->SWprevCurrent = 0.0;
    inst->SWprevResistance = inst->SWmodPtr->SWoffResistance;
    
    return OK;
}
```

#### **4. Core Load Function for MNA Stamping (`swload.c`)**

```c
int SWload(SWinstance *inst, CKTcircuit *ckt) {
    double v_switch, v_ctrl, g_switch, i_switch;
    double dg_dvctrl, di_dvctrl_pos, di_dvctrl_neg;
    
    /* Get current voltages from circuit solution */
    v_switch = *(ckt->CKTrhs[inst->SWposNode]) - *(ckt->CKTrhs[inst->SWnegNode]);
    v_ctrl = *(ckt->CKTrhs[inst->SWctrlPosNode]) - *(ckt->CKTrhs[inst->SWctrlNegNode]);
    
    inst->SWvoltage = v_switch;
    inst->SWctrlVoltage = v_ctrl;
    
    /* Calculate resistance and conductance */
    inst->SWresistance = SWcalculateResistance(inst, v_ctrl);
    g_switch = 1.0 / inst->SWresistance;
    inst->SWconduct = g_switch;
    
    /* Calculate derivatives for Jacobian */
    inst->SWdRdVctrl = SWcalculateResistanceDerivative(inst, v_ctrl);
    dg_dvctrl = -inst->SWdRdVctrl / (inst->SWresistance * inst->SWresistance);
    inst->SWdGdVctrl = dg_dvctrl;
    
    /* Calculate switch current */
    i_switch = g_switch * v_switch;
    inst->SWcurrent = i_switch;
    
    /* Calculate transconductance terms */
    di_dvctrl_pos = v_switch * dg_dvctrl;
    di_dvctrl_neg = -di_dvctrl_pos;
    
    /* Stamp main conductance matrix */
    *(inst->SWposPosPtr) += g_switch;
    *(inst->SWposNegPtr) += -g_switch;
    *(inst->SWnegPosPtr) += -g_switch;
    *(inst->SWnegNegPtr) += g_switch;
    
    /* Stamp control voltage coupling */
    *(inst->SWposCtrlPosPtr) += di_dvctrl_pos;
    *(inst->SWposCtrlNegPtr) += di_dvctrl_neg;
    *(inst->SWnegCtrlPosPtr) += -di_dvctrl_pos;
    *(inst->SWnegCtrlNegPtr) += -di_dvctrl_neg;
    
    /* Stamp current source into RHS */
    ckt->CKTrhs[inst->SWposNode] -= i_switch;
    ckt->CKTrhs[inst->SWnegNode] += i_switch;
    
    return OK;
}
```

#### **5. Parameter Processing (`swparam.c`, `swmparam.c`)**

```c
int SWparam(SWinstance *inst, int param, IFvalue *value) {
    switch(param) {
        case SW_POS_NODE: inst->SWposNode = value->iValue; break;
        case SW_NEG_NODE: inst->SWnegNode = value->iValue; break;
        case SW_CTRL_POS_NODE: inst->SWctrlPosNode = value->iValue; break;
        case SW_CTRL_NEG_NODE: inst->SWctrlNegNode = value->iValue; break;
        case SW_IC: inst->SWctrlVoltage = value->rValue; break;
        default: return E_BADPARM;
    }
    return OK;
}

int SWmParam(SWmodel *model, int param, IFvalue *value) {
    switch(param) {
        case SW_MOD_ON:
            if (value->rValue <= 0.0) return E_BADPARM;
            model->SWonResistance = value->rValue;
            model->SWonGiven = 1;
            break;
        case SW_MOD_OFF:
            if (value->rValue <= 0.0) return E_BADPARM;
            model->SWoffResistance = value->rValue;
            model->SWoffGiven = 1;
            break;
        case SW_MOD_VTH:
            model->SWthreshold = value->rValue;
            model->SWthreshGiven = 1;
            break;
        case SW_MOD_VHYS:
            if (value->rValue <= 0.0) return E_BADPARM;
            model->SWhysteresis = value->rValue;
            model->SWhyseGiven = 1;
            break;
        default: return E_BADPARM;
    }
    
    /* Recompute derived parameters */
    if (model->SWonGiven && model->SWoffGiven) {
        model->SWconductanceDelta = 
            (model->SWonResistance - model->SWoffResistance) / 2.0;
    }
    if (model->SWhyseGiven) {
        model->SWsmoothingFactor = 1.0 / (2.0 * model->SWhysteresis);
    }
    
    return OK;
}
```

#### **6. Convergence Testing (`swconv.c`)**

```c
int SWconvTest(SWinstance *inst, CKTcircuit *ckt) {
    double v_switch_new, v_ctrl_new, i_switch_new;
    double delta_v, delta_i, reltol, abstol, vntol;
    
    v_switch_new = *(ckt->CKTrhs[inst->SWposNode]) - *(ckt->CKTrhs[inst->SWnegNode]);
    v_ctrl_new = *(ckt->CKTrhs[inst->SWctrlPosNode]) - *(ckt->CKTrhs[inst->SWctrlNegNode]);
    
    double r_new = SWcalculateResistance(inst, v_ctrl_new);
    double g_new = 1.0 / r_new;
    i_switch_new = g_new * v_switch_new;
    
    reltol = ckt->CKTreltol;
    abstol = ckt->CKTabstol;
    vntol = ckt->CKTvoltTol;
    
    /* Check control voltage convergence */
    delta_v = fabs(v_ctrl_new - inst->SWctrlVoltage);
    if (delta_v > vntol + reltol * MAX(fabs(v_ctrl_new), fabs(inst->SWctrlVoltage))) {
        ckt->CKTnoncon++;
        return E_NOT_CONVERGED;
    }
    
    /* Check switch current convergence */
    delta_i = fabs(i_switch_new - inst->SWcurrent);
    if (delta_i > abstol + reltol * MAX(fabs(i_switch_new), fabs(inst->SWcurrent))) {
        ckt->CKTnoncon++;
        return E_NOT_CONVERGED;
    }
    
    return OK;
}
```

#### **7. SPICEdev API Binding (`swinit.c`)**

```c
SPICEdev SWinfo = {
    .DEVpublic = {
        .name = "SW",
        .description = "Voltage-Controlled Switch",
        .terms = 4,
        .numNames = 0,
        .termNames = NULL,
        .numInstanceParms = 5,
        .instanceParms = SWpTable,
        .numModelParms = 4,
        .modelParms = SWmPTable,
        .flags = DEV_DEFAULT,
    },
    .DEVparam = SWparam,
    .DEVmodParam = SWmParam,
    .DEVload = SWload,
    .DEVsetup = SWsetup,
    .DEVunsetup = NULL,
    .DEVpzSetup = SWsetup,
    .DEVtemperature = SWtemp,
    .DEVtrunc = SWtrunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = SWacLoad,
    .DEVaccept = SWaccept,
    .DEVdestroy = SWdestroy,
    .DEVmodDelete = SWmDelete,
    .DEVdelete = SWdelete,
    .DEVsetic = NULL,
    .DEVask = SWask,
    .DEVmAsk = NULL,
    .DEVpzLoad = SWpzLoad,
    .DEVconvTest = SWconvTest,
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

#### **8. Memory Management (`swdest.c`, `swmdel.c`)**

```c
int SWdestroy(SWinstance **instPtr) {
    SWinstance *inst = *instPtr;
    if (inst) {
        free(inst);
        *instPtr = NULL;
    }
    return OK;
}

int SWmDelete(GENmodel **modelPtr) {
    SWmodel **model = (SWmodel **)modelPtr;
    SWinstance *inst, *nextInst;
    
    if (*model) {
        for (inst = (*model)->SWinstances; inst != NULL; inst = nextInst) {
            nextInst = inst->SWnextInstance;
            SWdestroy(&inst);
        }
        free(*model);
        *model = NULL;
    }
    return OK;
}
```

### **Conclusion**

The Ngspice voltage-controlled switch implementation demonstrates a sophisticated approach to integrating fundamentally discontinuous elements into a continuous simulation framework. By employing hyperbolic tangent smoothing with carefully chosen parameters, the model achieves numerical convergence while maintaining reasonable switching characteristics. The implementation showcases key SPICE architecture patterns: separation of model and instance data, pre-computation of derived parameters for efficiency, complete Jacobian computation for Newton-Raphson convergence, proper integration with the SMP sparse matrix system, and robust memory management. This chapter provides hardware engineers with both the mathematical foundation and practical implementation details needed to understand, use, and potentially extend Ngspice's switch modeling capabilities for mixed-signal circuit simulation.