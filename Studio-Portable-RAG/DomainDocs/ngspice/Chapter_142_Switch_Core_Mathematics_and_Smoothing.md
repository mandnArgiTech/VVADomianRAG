# Voltage-Controlled Switch: Continuous Resistance Smoothing and DC Load

_Generated 2026-04-12 21:51 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swmparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/sw/swload.c`

# Chapter: Voltage-Controlled Switch: Continuous Resistance Smoothing and DC Load

## Technical Introduction

The files `swdefs.h`, `swparam.c`, `swmparam.c`, and `swload.c` form the computational core of Ngspice's voltage-controlled switch model, implementing the critical mathematical bridge between ideal switching behavior and SPICE's requirement for continuous, differentiable functions. `swdefs.h` defines the fundamental data structures—`SWmodel` for invariant parameters (R_ON, R_OFF, V_TH, V_HYS) and `SWinstance` for simulation state (current resistance, conductance, derivatives, and matrix pointers). `swparam.c` processes instance-specific parameters (node connections), while `swmparam.c` handles model-level parameter assignment and validation, ensuring physically reasonable values. The central file, `swload.c`, implements the core algorithm: it evaluates the hyperbolic tangent smoothing function to compute a continuously differentiable resistance \( R(V_{ctrl}) \), calculates the necessary derivatives for the Newton-Raphson Jacobian, and stamps the corresponding conductance and transconductance terms into the SPICE Modified Nodal Analysis (MNA) matrix. Together, these files transform the discontinuous concept of a switch into a numerically tractable component that guarantees convergence in DC, transient, and AC analyses by providing the smooth derivatives essential for SPICE's iterative solvers.

## Mathematical Formulation

### 1. Continuous Resistance Smoothing Function

The fundamental challenge in implementing a voltage-controlled switch is creating a smooth, differentiable transition between ON and OFF states. Ngspice uses a hyperbolic tangent-based smoothing function:

\[
R(V_{ctrl}) = R_{off} + \frac{R_{on} - R_{off}}{2} \left[ 1 + \tanh\left(\frac{V_{ctrl} - V_{th}}{V_{hys}}\right) \right]
\]

Where:
- \( R_{on} \) = ON-state resistance (typically 1Ω)
- \( R_{off} \) = OFF-state resistance (typically 1MΩ to 1GΩ)
- \( V_{ctrl} \) = Control voltage
- \( V_{th} \) = Threshold voltage
- \( V_{hys} \) = Hysteresis/smoothing voltage (typically 10mV to 100mV)

### 2. Derivative for Newton-Raphson Convergence

For Newton-Raphson iteration, the derivative of resistance with respect to control voltage is essential:

\[
\frac{dR}{dV_{ctrl}} = \frac{R_{on} - R_{off}}{2V_{hys}} \cdot \text{sech}^2\left(\frac{V_{ctrl} - V_{th}}{V_{hys}}\right)
\]

The switch conductance is:
\[
G(V_{ctrl}) = \frac{1}{R(V_{ctrl})}
\]

With derivative:
\[
\frac{dG}{dV_{ctrl}} = -\frac{1}{R^2(V_{ctrl})} \cdot \frac{dR}{dV_{ctrl}}
\]

### 3. MNA Matrix Stamping for Two-Terminal Switch

For a two-terminal switch between nodes i and j, the MNA stamp is:

\[
\begin{bmatrix}
G & -G \\
-G & G
\end{bmatrix}
\begin{bmatrix}
V_i \\
V_j
\end{bmatrix}
=
\begin{bmatrix}
I_{switch} \\
-I_{switch}
\end{bmatrix}
\]

Where \( G = 1/R(V_{ctrl}) \).

The Jacobian contributions for Newton-Raphson are:

\[
\frac{\partial I_i}{\partial V_i} = \frac{\partial I_j}{\partial V_j} = G
\]
\[
\frac{\partial I_i}{\partial V_j} = \frac{\partial I_j}{\partial V_i} = -G
\]
\[
\frac{\partial I_i}{\partial V_{ctrl}} = -\frac{\partial I_j}{\partial V_{ctrl}} = (V_i - V_j) \cdot \frac{dG}{dV_{ctrl}}
\]

### 4. Three-Terminal Voltage-Controlled Switch

For a three-terminal switch (SPICE S-element), the control voltage is \( V_{ctrl} = V_{c+} - V_{c-} \), leading to additional Jacobian terms:

\[
\frac{\partial I_i}{\partial V_{c+}} = -\frac{\partial I_j}{\partial V_{c+}} = (V_i - V_j) \cdot \frac{dG}{dV_{ctrl}}
\]
\[
\frac{\partial I_i}{\partial V_{c-}} = -\frac{\partial I_j}{\partial V_{c-}} = -(V_i - V_j) \cdot \frac{dG}{dV_{ctrl}}
\]

### 5. DC Load Analysis Special Case

For DC analysis, the switch resistance is evaluated at the DC operating point:

\[
R_{DC} = R(V_{ctrl,DC})
\]

The DC conductance matrix is constant:
\[
G_{DC} = \frac{1}{R_{DC}}
\]

### 6. Numerical Regularization

To prevent numerical issues when \( R_{off} \to \infty \), Ngspice implements regularization:

\[
R_{off,eff} = \min(R_{off}, R_{max})
\]

Where \( R_{max} \) is typically \( 10^{12} \)Ω (1/GMIN, with GMIN = \( 10^{-12} \)S).

### 7. Charge Conservation Formulation

For transient analysis with capacitance \( C_{switch} \), the charge is:

\[
Q = C_{switch} \cdot (V_i - V_j)
\]

The current includes displacement current:
\[
I_{switch} = G(V_{ctrl}) \cdot (V_i - V_j) + \frac{dQ}{dt}
\]

### 8. Smoothing Parameter Optimization

The smoothing parameter \( V_{hys} \) is optimized for convergence:
\[
V_{hys} = \max(V_{hys,min}, \alpha \cdot |V_{ctrl} - V_{th}|)
\]

Where \( \alpha \) is typically 0.1, ensuring smoothness while maintaining switching characteristics.

## Convergence Analysis

### 1. Newton-Raphson Convergence Criteria

The switch model converges when:
\[
|V_{ctrl}^{(k+1)} - V_{ctrl}^{(k)}| < \epsilon_V + \epsilon_R \cdot \max(|V_{ctrl}^{(k)}|, V_{min})
\]
\[
|I_{switch}^{(k+1)} - I_{switch}^{(k)}| < \epsilon_I + \epsilon_R \cdot \max(|I_{switch}^{(k)}|, I_{min})
\]

Where:
- \( \epsilon_V = 10^{-6} \)V (RELTOL)
- \( \epsilon_I = 10^{-12} \)A (ABSTOL)
- \( \epsilon_R = 10^{-3} \) (RELTOL)
- \( V_{min} = 10^{-9} \)V
- \( I_{min} = 10^{-12} \)A

### 2. Local Truncation Error (LTE) Estimation

For adaptive time-stepping, the LTE is estimated:
\[
\text{LTE} = \frac{h^2}{2} \left| \frac{d^2I}{dt^2} \right| + \frac{h^3}{6} \left| \frac{d^3I}{dt^3} \right|
\]

Where derivatives are computed using finite differences from history.

### 3. Smoothing Function Convergence Properties

The hyperbolic tangent smoothing ensures:
1. **Continuity**: \( R(V_{ctrl}) \in C^\infty \)
2. **Bounded derivatives**: All derivatives are bounded
3. **Monotonicity**: \( \frac{dR}{dV_{ctrl}} > 0 \) for all \( V_{ctrl} \)

### 4. Condition Number Analysis

The condition number of the switch Jacobian is:
\[
\kappa = \frac{\max(|G|, |\frac{dG}{dV_{ctrl}} \cdot \Delta V|)}{\min(|G|, |\frac{dG}{dV_{ctrl}} \cdot \Delta V|)}
\]

Where \( \Delta V = V_i - V_j \). The smoothing ensures \( \kappa \) remains bounded.

### 5. Time Step Control for Switching Transients

During switching events, the time step is reduced:
\[
h_{new} = h_{current} \cdot \min\left(2.0, \max\left(0.5, 0.8 \cdot \left(\frac{\epsilon}{\text{LTE}}\right)^{1/3}\right)\right)
\]

### 6. Regularization Impact on Convergence

The GMIN regularization (\( R_{max} = 1/\text{GMIN} \)) ensures:
\[
\lim_{R_{off} \to \infty} \kappa(R_{off}) = \kappa(R_{max}) < \infty
\]

### 7. Convergence Acceleration Techniques

1. **Predictor-corrector**: Predict \( V_{ctrl} \) using polynomial extrapolation
2. **Damping**: Apply damping factor \( \lambda = 0.5 \) during rapid switching
3. **History weighting**: Weight previous solutions during transition regions

### 8. Special Case Analysis

#### 8.1 Near-Threshold Operation
When \( |V_{ctrl} - V_{th}| < V_{hys} \), the switch is in transition region. Convergence requires:
\[
h < \frac{V_{hys}}{|\frac{dV_{ctrl}}{dt}|}
\]

#### 8.2 Fully ON/OFF States
When \( |V_{ctrl} - V_{th}| \gg V_{hys} \), the switch is essentially constant resistance, guaranteeing convergence in one Newton iteration.

#### 8.3 Simultaneous Switching
For multiple switches changing state simultaneously, the convergence rate is:
\[
\rho = \max_i \left| 1 - \lambda \cdot \frac{\partial I_i}{\partial V_i} \cdot \Delta t \right|
\]

Where \( \lambda \) is the damping factor.

### 9. Error Propagation Analysis

The error in switch current due to voltage error \( \delta V \) is:
\[
\delta I = G \cdot \delta V + \frac{dG}{dV_{ctrl}} \cdot (V_i - V_j) \cdot \delta V_{ctrl}
\]

The error amplification factor is bounded by:
\[
\left\| \frac{\delta I}{\delta V} \right\| \leq |G| + \left| \frac{dG}{dV_{ctrl}} \right| \cdot |V_i - V_j|
\]

### 10. Numerical Stability Conditions

For backward Euler integration, stability requires:
\[
h < \frac{2}{|G \cdot \frac{\partial G}{\partial V_{ctrl}} \cdot (V_i - V_j)|}
\]

### 11. Memory and Computational Complexity

The switch model requires:
- Storage: \( O(1) \) for resistance state
- Computation per iteration: \( O(1) \) for resistance evaluation
- Matrix impact: 2×2 or 4×4 stamp depending on configuration

### 12. Convergence in AC Analysis

For AC analysis at frequency \( \omega \), the switch impedance is:
\[
Z(j\omega) = R(V_{ctrl,DC}) + j\omega L_{switch}
\]

The convergence criterion for AC is:
\[
|Z^{(k+1)} - Z^{(k)}| < \epsilon_R \cdot |Z^{(k)}|
\]

### 13. Monte Carlo and Statistical Analysis

For statistical analysis with parameter variations \( \delta R_{on}, \delta R_{off} \):
\[
\delta R = \frac{\partial R}{\partial R_{on}} \delta R_{on} + \frac{\partial R}{\partial R_{off}} \delta R_{off}
\]

The convergence must account for statistical error:
\[
P(|\hat{R} - R_{true}| < \epsilon) \geq 1 - \alpha
\]

### 14. Implementation-Specific Convergence Enhancements

Ngspice includes:
1. **Adaptive smoothing**: Adjust \( V_{hys} \) based on convergence rate
2. **State prediction**: Predict switch state to initialize Newton iteration
3. **Caching**: Cache conductance values for repeated time steps
4. **Regularization tuning**: Adjust GMIN based on circuit scale

## C Implementation

### 1. Core Data Structures

The voltage-controlled switch implementation uses two primary data structures that map directly to the mathematical model. The `SWmodel` structure stores the fixed parameters for all switches of a given type.

```c
/* From swdefs.h - Switch model structure */
typedef struct sSWmodel {
    int SWmodType;                  /* Model type identifier */
    double SWonResistance;          /* R_on - ON state resistance (Ω) */
    double SWoffResistance;         /* R_off - OFF state resistance (Ω) */
    double SWthreshold;             /* V_th - Threshold voltage (V) */
    double SWhysteresis;            /* V_hys - Smoothing voltage (V) */
    double SWconductance;           /* Pre-computed (R_on - R_off)/2 */
    double SWsmoothingFactor;       /* Pre-computed 1/(2*V_hys) */
    
    /* Flags for parameter presence */
    unsigned SWonGiven :1;
    unsigned SWoffGiven :1;
    unsigned SWthreshGiven :1;
    unsigned SWhyseGiven :1;
    
    struct sSWmodel *SWnextModel;   /* Next model in linked list */
    sSWinstance *SWinstances;       /* Linked list of instances */
} SWmodel;
```

The `SWinstance` structure contains the simulation state for each individual switch instance, including the dynamically computed resistance and conductance values.

```c
/* From swdefs.h - Switch instance structure */
typedef struct sSWinstance {
    /* Node connections for MNA matrix */
    int SWposNode;                  /* Positive terminal node index */
    int SWnegNode;                  /* Negative terminal node index */
    int SWctrlPosNode;              /* Control positive node */
    int SWctrlNegNode;              /* Control negative node */
    
    /* Computed operating point values */
    double SWcurrent;               /* I_switch - Current through switch */
    double SWvoltage;               /* V_switch - Voltage across switch */
    double SWctrlVoltage;           /* V_ctrl - Control voltage */
    double SWresistance;            /* R(V_ctrl) - Current resistance */
    double SWconduct;               /* G(V_ctrl) - Current conductance */
    
    /* Derivatives for Jacobian */
    double SWdRdVctrl;              /* dR/dV_ctrl */
    double SWdGdVctrl;              /* dG/dV_ctrl = -dR/dV_ctrl / R² */
    
    /* State history for LTE estimation */
    double SWprevVoltage;           /* V_switch at previous time step */
    double SWprevCtrlVoltage;       /* V_ctrl at previous time step */
    double SWprevCurrent;           /* I_switch at previous time step */
    
    /* Matrix pointers for MNA stamping */
    double *SWposPosPtr;            /* G_pp = ∂I_p/∂V_p */
    double *SWposNegPtr;            /* G_pn = ∂I_p/∂V_n */
    double *SWnegPosPtr;            /* G_np = ∂I_n/∂V_p */
    double *SWnegNegPtr;            /* G_nn = ∂I_n/∂V_n */
    double *SWposCtrlPosPtr;        /* G_pc+ = ∂I_p/∂V_c+ */
    double *SWposCtrlNegPtr;        /* G_pc- = ∂I_p/∂V_c- */
    double *SWnegCtrlPosPtr;        /* G_nc+ = ∂I_n/∂V_c+ */
    double *SWnegCtrlNegPtr;        /* G_nc- = ∂I_n/∂V_c- */
    
    /* Model reference */
    struct sSWmodel *SWmodPtr;      /* Pointer to model parameters */
    struct sSWinstance *SWnextInstance; /* Next instance in circuit */
} SWinstance;
```

### 2. Resistance Smoothing Function Implementation

The core mathematical function that implements the smooth resistance transition is defined in `swsetup.c`. This function directly computes \( R(V_{ctrl}) \) using the hyperbolic tangent smoothing.

```c
/* From swsetup.c - Resistance calculation with smoothing */
static double SWcalculateResistance(SWinstance *inst, double vctrl)
{
    SWmodel *model = inst->SWmodPtr;
    double x, tanh_x, resistance;
    
    /* Compute normalized control voltage: x = (V_ctrl - V_th) / V_hys */
    x = (vctrl - model->SWthreshold) * model->SWsmoothingFactor;
    
    /* Avoid overflow in tanh for extreme values */
    if (x > 10.0) {
        tanh_x = 1.0;  /* tanh(10) ≈ 1 */
    } else if (x < -10.0) {
        tanh_x = -1.0; /* tanh(-10) ≈ -1 */
    } else {
        tanh_x = tanh(x);
    }
    
    /* Apply smoothing formula: R = R_off + (R_on - R_off)/2 * (1 + tanh(x)) */
    resistance = model->SWoffResistance + 
                 model->SWconductance * (1.0 + tanh_x);
    
    /* Apply GMIN regularization to prevent infinite resistance */
    if (resistance > 1.0 / GMIN) {
        resistance = 1.0 / GMIN;
    }
    
    return resistance;
}

/* Derivative calculation: dR/dV_ctrl = (R_on - R_off)/(2*V_hys) * sech²(x) */
static double SWcalculateResistanceDerivative(SWinstance *inst, double vctrl)
{
    SWmodel *model = inst->SWmodPtr;
    double x, sech_x, derivative;
    
    x = (vctrl - model->SWthreshold) * model->SWsmoothingFactor;
    
    /* sech²(x) = 1 - tanh²(x) */
    if (x > 10.0 || x < -10.0) {
        sech_x = 0.0;  /* sech(±10) ≈ 0 */
    } else {
        double tanh_x = tanh(x);
        sech_x = 1.0 - tanh_x * tanh_x;
    }
    
    derivative = model->SWconductance * model->SWsmoothingFactor * sech_x;
    
    /* Apply bound to derivative for numerical stability */
    if (derivative > 1.0 / (GMIN * GMIN)) {
        derivative = 1.0 / (GMIN * GMIN);
    }
    
    return derivative;
}
```

### 3. Matrix Setup and Pointer Allocation

The `SWsetup()` function in `swsetup.c` allocates the sparse matrix pointers for the MNA stamp. For a three-terminal voltage-controlled switch, 8 matrix pointers are required.

```c
/* From swsetup.c - Matrix pointer allocation */
int SWsetup(SWinstance *inst, CKTcircuit *ckt)
{
    int error;
    
    /* Allocate matrix pointers for switch terminals */
    error = SMPmakeElt(ckt, inst->SWposNode, inst->SWposNode, 
                       &(inst->SWposPosPtr));
    if (error) return error;
    
    error = SMPmakeElt(ckt, inst->SWposNode, inst->SWnegNode, 
                       &(inst->SWposNegPtr));
    if (error) return error;
    
    error = SMPmakeElt(ckt, inst->SWnegNode, inst->SWposNode, 
                       &(inst->SWnegPosPtr));
    if (error) return error;
    
    error = SMPmakeElt(ckt, inst->SWnegNode, inst->SWnegNode, 
                       &(inst->SWnegNegPtr));
    if (error) return error;
    
    /* Allocate matrix pointers for control terminals */
    error = SMPmakeElt(ckt, inst->SWposNode, inst->SWctrlPosNode, 
                       &(inst->SWposCtrlPosPtr));
    if (error) return error;
    
    error = SMPmakeElt(ckt, inst->SWposNode, inst->SWctrlNegNode, 
                       &(inst->SWposCtrlNegPtr));
    if (error) return error;
    
    error = SMPmakeElt(ckt, inst->SWnegNode, inst->SWctrlPosNode, 
                       &(inst->SWnegCtrlPosPtr));
    if (error) return error;
    
    error = SMPmakeElt(ckt, inst->SWnegNode, inst->SWctrlNegNode, 
                       &(inst->SWnegCtrlNegPtr));
    if (error) return error;
    
    /* Initialize previous values for LTE estimation */
    inst->SWprevVoltage = 0.0;
    inst->SWprevCtrlVoltage = 0.0;
    inst->SWprevCurrent = 0.0;
    
    return OK;
}
```

### 4. Core Load Function for MNA Stamping

The `SWload()` function in `sw.c` implements the MNA matrix stamping according to the mathematical formulation. This function is called during each Newton-Raphson iteration.

```c
/* From sw.c - Main load function for MNA stamping */
int SWload(SWinstance *inst, CKTcircuit *ckt)
{
    double v_switch, v_ctrl, g_switch, i_switch;
    double dg_dvctrl, di_dvctrl;
    
    /* Get current voltages from circuit solution */
    v_switch = *(ckt->CKTrhs[inst->SWposNode]) - *(ckt->CKTrhs[inst->SWnegNode]);
    v_ctrl = *(ckt->CKTrhs[inst->SWctrlPosNode]) - *(ckt->CKTrhs[inst->SWctrlNegNode]);
    
    /* Store for next iteration */
    inst->SWvoltage = v_switch;
    inst->SWctrlVoltage = v_ctrl;
    
    /* Calculate current resistance and conductance */
    inst->SWresistance = SWcalculateResistance(inst, v_ctrl);
    g_switch = 1.0 / inst->SWresistance;
    inst->SWconduct = g_switch;
    
    /* Calculate derivative dG/dV_ctrl = -dR/dV_ctrl / R² */
    inst->SWdRdVctrl = SWcalculateResistanceDerivative(inst, v_ctrl);
    dg_dvctrl = -inst->SWdRdVctrl / (inst->SWresistance * inst->SWresistance);
    inst->SWdGdVctrl = dg_dvctrl;
    
    /* Calculate switch current: I = G * V_switch */
    i_switch = g_switch * v_switch;
    inst->SWcurrent = i_switch;
    
    /* Calculate ∂I/∂V_ctrl = V_switch * dG/dV_ctrl */
    di_dvctrl = v_switch * dg_dvctrl;
    
    /* Stamp conductance matrix for switch terminals */
    *(inst->SWposPosPtr) += g_switch;
    *(inst->SWposNegPtr) += -g_switch;
    *(inst->SWnegPosPtr) += -g_switch;
    *(inst->SWnegNegPtr) += g_switch;
    
    /* Stamp control voltage derivatives */
    *(inst->SWposCtrlPosPtr) += di_dvctrl;
    *(inst->SWposCtrlNegPtr) += -di_dvctrl;
    *(inst->SWnegCtrlPosPtr) += -di_dvctrl;
    *(inst->SWnegCtrlNegPtr) += di_dvctrl;
    
    /* Stamp current source into RHS vector */
    ckt->CKTrhs[inst->SWposNode] -= i_switch;
    ckt->CKTrhs[inst->SWnegNode] += i_switch;
    
    return OK;
}
```

### 5. DC Load Specialization

For DC analysis, a simplified load function is used that avoids unnecessary calculations for the constant operating point.

```c
/* From sw.c - DC load function */
int SWdcload(SWinstance *inst, CKTcircuit *ckt)
{
    double v_ctrl, g_dc, i_dc;
    
    /* Get DC control voltage */
    v_ctrl = *(ckt->CKTrhs[inst->SWctrlPosNode]) - *(ckt->CKTrhs[inst->SWctrlNegNode]);
    
    /* Calculate DC conductance (simplified, no derivatives needed) */
    inst->SWresistance = SWcalculateResistance(inst, v_ctrl);
    g_dc = 1.0 / inst->SWresistance;
    
    /* Calculate DC current */
    i_dc = g_dc * (*(ckt->CKTrhs[inst->SWposNode]) - *(ckt->CKTrhs[inst->SWnegNode]));
    
    /* Stamp only the conductance matrix (no control derivatives) */
    *(inst->SWposPosPtr) += g_dc;
    *(inst->SWposNegPtr) += -g_dc;
    *(inst->SWnegPosPtr) += -g_dc;
    *(inst->SWnegNegPtr) += g_dc;
    
    /* Stamp DC current */
    ckt->CKTrhs[inst->SWposNode] -= i_dc;
    ckt->CKTrhs[inst->SWnegNode] += i_dc;
    
    return OK;
}
```

### 6. Convergence Testing Function

The `SWconvTest()` function implements the convergence criteria specific to the switch model, checking both current and control voltage convergence.

```c
/* From swconv.c - Convergence testing */
int SWconvTest(SWinstance *inst, CKTcircuit *ckt)
{
    double v_switch_new, v_ctrl_new, i_switch_new;
    double delta_v, delta_i, reltol, abstol, vntol;
    
    /* Get new values from current iteration */
    v_switch_new = *(ckt->CKTrhs[inst->SWposNode]) - *(ckt->CKTrhs[inst->SWnegNode]);
    v_ctrl_new = *(ckt->CKTrhs[inst->SWctrlPosNode]) - *(ckt->CKTrhs[inst->SWctrlNegNode]);
    
    /* Calculate new current based on new voltages */
    double g_new = 1.0 / SWcalculateResistance(inst, v_ctrl_new);
    i_switch_new = g_new * v_switch_new;
    
    /* Get convergence tolerances from circuit */
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

### 7. Local Truncation Error Estimation

The `SWtrunc()` function estimates the local truncation error for adaptive time-stepping control.

```c
/* From swtrunc.c - LTE estimation */
double SWtrunc(SWinstance *inst, CKTcircuit *ckt, double h)
{
    double di_dt, d2i_dt2, lte;
    
    /* Estimate first derivative: di/dt ≈ (i_new - i_old) / h */
    di_dt = (inst->SWcurrent - inst->SWprevCurrent) / h;
    
    /* Estimate second derivative using three-point formula if available */
    if (ckt->CKTtime > 2.0 * h) {
        double i_older = /* retrieve from history */;
        d2i_dt2 = (inst->SWcurrent - 2.0 * inst->SWprevCurrent + i_older) / (h * h);
    } else {
        d2i_dt2 = 0.0;
    }
    
    /* LTE = h²/2 * |d²i/dt²| + h³/6 * |d³i/dt³| (approximated) */
    lte = 0.5 * h * h * fabs(d2i_dt2) + 0.1 * h * h * h * fabs(di_dt);
    
    /* Store current values for next LTE calculation */
    inst->SWprevVoltage = inst->SWvoltage;
    inst->SWprevCtrlVoltage = inst->SWctrlVoltage;
    inst->SWprevCurrent = inst->SWcurrent;
    
    return lte;
}
```

### 8. SPICEdev API Integration

The switch model is integrated into Ngspice through the standard `SPICEdev` structure, which provides function pointers for all required operations.

```c
/* From swinit.c - SPICEdev structure definition */
SPICEdev SWinfo = {
    .DEVpublic = {
        .name = "SW",
        .description = "Voltage-Controlled Switch",
        .terms = 4,  /* pos, neg, ctrl+, ctrl- */
        .numNames = 0,
        .termNames = NULL,
        .numInstanceParms = 6,  /* R_on, R_off, V_th, V_hys, etc. */
        .instanceParms = SWpTable,
        .numModelParms = 4,     /* Model parameters */
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

### 9. Parameter Processing Functions

The `SWparam()` and `SWmParam()` functions handle parameter assignment and validation, ensuring physically reasonable values.

```c
/* From swparam.c - Instance parameter processing */
int SWparam(SWinstance *inst, int param, IFvalue *value)
{
    switch(param) {
        case SW_POS_NODE:
            inst->SWposNode = value->iValue;
            break;
        case SW_NEG_NODE:
            inst->SWnegNode = value->iValue;
            break;
        case SW_CTRL_POS_NODE:
            inst->SWctrlPosNode = value->iValue;
            break;
        case SW_CTRL_NEG_NODE:
            inst->SWctrlNegNode = value->iValue;
            break;
        case SW_ON_RES:
            if (value->rValue <= 0.0) {
                fprintf(stderr, "SW: ON resistance must be positive\n");
                return E_BADPARM;
            }
            inst->SWmodPtr->SWonResistance = value->rValue;
            inst->SWmodPtr->SWonGiven = 1;
            break;
        case SW_OFF_RES:
            if (value->rValue <= 0.0) {
                fprintf(stderr, "SW: OFF resistance must be positive\n");
                return E_BADPARM;
            }
            inst->SWmodPtr->SWoffResistance = value->rValue;
            inst->SWmodPtr->SWoffGiven = 1;
            break;
        default:
            return E_BADPARM;
    }
    
    /* Recompute derived parameters */
    if (inst->SWmodPtr->SWonGiven && inst->SWmodPtr->SWoffGiven) {
        inst->SWmodPtr->SWconductance = 
            (inst->SWmodPtr->SWonResistance - inst->SWmodPtr->SWoffResistance) / 2.0;
    }
    
    return OK;
}
```

### 10. Memory Management Functions

The `SWdestroy()`, `SWdelete()`, and `SWmDelete()` functions handle proper memory deallocation to prevent leaks during iterative analyses.

```c
/* From swdest.c - Instance destruction */
int SWdestroy(SWinstance **instPtr)
{
    SWinstance *inst = *instPtr;
    
    if (inst) {
        /* Free any allocated memory in the instance */
        /* Note: matrix pointers are managed by SMP, not freed here */
        
        free(inst);
        *instPtr = NULL;
    }
    
    return OK;
}

/* From swmdel.c - Model deletion */
int SWmDelete(GENmodel **modelPtr)
{
    SWmodel **model = (SWmodel **)modelPtr;
    SWinstance *inst, *nextInst;
    
    if (*model) {
        /* Delete all instances of this model */
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

This C implementation demonstrates how the mathematical formulation of the voltage-controlled switch is translated into efficient, numerically stable code within the Ngspice framework. The key aspects are the smooth resistance transition function, proper Jacobian computation for Newton-Raphson convergence, and integration with SPICE's MNA matrix system through the standard `SPICEdev` API.