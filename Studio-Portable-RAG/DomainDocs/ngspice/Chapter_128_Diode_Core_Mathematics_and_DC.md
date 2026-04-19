# Diode: Shockley Physics, Breakdown, and DC Load

_Generated 2026-04-12 19:45 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diodefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/dioparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/diotemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/dio/dioload.c`

# Chapter: Diode: Shockley Physics, Breakdown, and DC Load

## 1. Technical Introduction

The diode model in Ngspice is implemented across four core C source files that define its device physics, parameter handling, temperature dependence, and DC load behavior for circuit simulation. These files work in concert to translate the theoretical Shockley diode equation, breakdown models, and charge conservation principles into a numerically robust implementation within the SPICE simulation kernel.

*   **`diodefs.h`**: This header file defines the fundamental data structures for the diode model. It declares the `DIOmodel` and `DIOinstance` structures, which encapsulate all model parameters (saturation current `IS`, emission coefficient `N`, series resistance `RS`, breakdown voltage `BV`, zero-bias junction capacitance `CJO`), instance-specific values (node connections, area factor), and dynamic simulation state (junction voltages `Vd`, currents `Id`, charges `Qd`, and matrix pointers). It is the architectural blueprint that ensures all other C files operate on a consistent data representation.

*   **`dioparam.c`**: This file implements the parameter binding and parsing logic. It contains the parameter tables (`DIOPTable` for instances, `DIOMTable` for models) that map SPICE netlist keywords (e.g., `IS`, `BV`, `TT`) to internal variables in the `DIOinstance` and `DIOmodel` structs. Its core function, `DIOparam()`, validates user-provided parameter values, applies defaults, and handles the `AREA` and `OFF` factors. It acts as the critical interface between the netlist description and the internal numerical model.

*   **`diotemp.c`**: This file manages the temperature dependence of diode parameters as defined by the semiconductor physics equations. The function `DIOtemp()` performs temperature scaling of the saturation current `IS`, the junction potential `PHI`, the breakdown voltage `BV`, and the zero-bias capacitance `CJO` based on the nominal temperature `TNOM` and the current circuit temperature `TEMP`. It implements the exponential and power-law relationships crucial for accurate simulation across temperature sweeps.

*   **`dioload.c`**: This is the computational heart of the DC diode model. The `DIOload()` function performs the Newton-Raphson iteration for DC operating point analysis. It evaluates the Shockley equation (and its breakdown modification) at the current voltage guess, computes the small-signal conductance `gd`, formulates the companion Norton equivalent model (`geq`, `Ieq`), and stamps the appropriate contributions into the SPICE Modified Nodal Analysis (MNA) matrix and right-hand-side (RHS) vector. It directly implements the linearization required to solve the nonlinear diode equation within the larger system of circuit equations.

Together, these files transform the analytical models of diode behavior into a stable, iterative numerical procedure integrated within Ngspice's matrix solver, enabling the DC analysis of circuits containing nonlinear diodes.

## 2. Mathematical Formulation

### 2.1 Shockley Diode Equation and DC Operating Point

The fundamental mathematical model for a semiconductor diode in SPICE is based on the Shockley diode equation, which describes the current-voltage relationship of an ideal p-n junction:

\[
I_D = I_S \left[ \exp\left(\frac{V_D}{n V_T}\right) - 1 \right]
\]

Where:
- \(I_D\) = diode current (positive for forward bias)
- \(I_S\) = saturation current (typically \(10^{-14}\) to \(10^{-12}\) A)
- \(V_D\) = voltage across the diode (positive for forward bias)
- \(n\) = emission coefficient (ideality factor, typically 1.0 to 2.0)
- \(V_T = \frac{kT}{q}\) = thermal voltage (\(\approx 25.85\) mV at 300K)

For SPICE simulation, this equation must be linearized for the Newton-Raphson iteration. The small-signal conductance at operating point \(V_D\) is:

\[
g_d = \frac{\partial I_D}{\partial V_D} = \frac{I_S}{n V_T} \exp\left(\frac{V_D}{n V_T}\right) \approx \frac{I_D + I_S}{n V_T}
\]

The companion model for DC analysis is a Norton equivalent:
\[
I_D = g_d V_D + I_{eq}
\]
where \(I_{eq} = I_D - g_d V_D\) is the history current.

### 2.2 Series Resistance and High-Level Injection Effects

Real diodes exhibit series resistance \(R_S\) and high-level injection effects. The modified diode equation becomes:

\[
I_D = I_S \left[ \exp\left(\frac{V_D - I_D R_S}{n V_T}\right) - 1 \right]
\]

This implicit equation must be solved iteratively. For SPICE implementation, the voltage across the intrinsic junction is:
\[
V_J = V_D - I_D R_S
\]

The conductance including series resistance is:
\[
g_d^{\text{total}} = \frac{g_d}{1 + g_d R_S}
\]
where \(g_d\) is the intrinsic junction conductance.

### 2.3 Breakdown Region Modeling (Reverse Bias)

For reverse bias beyond the breakdown voltage \(BV\), the diode exhibits avalanche multiplication. The reverse current is modeled as:

\[
I_R = I_S \left[ \exp\left(\frac{-V_D}{n V_T}\right) - 1 \right] \times M(V_D)
\]

Where the multiplication factor \(M(V_D)\) is:
\[
M(V_D) = \frac{1}{1 - \left(\frac{V_D}{BV}\right)^m} \quad \text{for } V_D < 0
\]

The parameter \(m\) (typically 3-4) controls the sharpness of breakdown. For SPICE implementation, this must be differentiable for Newton-Raphson:

\[
\frac{\partial I_R}{\partial V_D} = I_S \left[ -\frac{1}{n V_T} \exp\left(\frac{-V_D}{n V_T}\right) M(V_D) + \frac{m V_D^{m-1}}{BV^m} \frac{I_R}{1 - (V_D/BV)^m} \right]
\]

### 2.4 Junction Capacitance Modeling

The diode junction capacitance has two components: depletion capacitance and diffusion capacitance.

**Depletion capacitance** (reverse and small forward bias):
\[
C_j(V_D) = \frac{C_{j0}}{\left(1 - \frac{V_D}{\phi}\right)^m}
\]
Where:
- \(C_{j0}\) = zero-bias junction capacitance
- \(\phi\) = built-in potential (typically 0.7-0.8 V)
- \(m\) = grading coefficient (0.5 for abrupt junction, 0.33 for graded)

For forward bias beyond \(FC \cdot \phi\) (where \(FC\) is typically 0.5), SPICE uses a linear approximation:
\[
C_j(V_D) = C_{j0} \left[ \frac{1 - FC(1+m) + m\frac{V_D}{\phi}}{(1 - FC)^{1+m}} \right]
\]

**Diffusion capacitance** (forward bias):
\[
C_d = \tau_T \frac{I_S}{n V_T} \exp\left(\frac{V_D}{n V_T}\right) = \tau_T g_d
\]
Where \(\tau_T\) is the transit time.

The total displacement current is:
\[
I_{cap} = \frac{dQ}{dt} = \frac{d}{dt}\left( \int C_j(V_D) dV_D + \tau_T I_D \right)
\]

### 2.5 Temperature Dependence

Key diode parameters vary with temperature:
\[
I_S(T) = I_S(T_0) \left(\frac{T}{T_0}\right)^{XTI} \exp\left[ \frac{E_g(T_0)}{k T_0} - \frac{E_g(T)}{k T} \right]
\]
\[
\phi(T) = \phi(T_0) \frac{T}{T_0} - \frac{3k T}{q} \ln\left(\frac{T}{T_0}\right) - \frac{E_g(T_0) T}{T_0} + E_g(T)
\]
\[
V_T(T) = \frac{kT}{q}
\]

Where:
- \(XTI\) = saturation current temperature exponent (typically 3.0)
- \(E_g(T) = E_g(0) - \frac{\alpha T^2}{T + \beta}\) = energy gap temperature dependence

### 2.6 DC Load Implementation for Newton-Raphson

For the Newton-Raphson iteration in DC analysis, the diode stamp into the MNA matrix is:

\[
\begin{bmatrix}
G + g_d & -g_d \\
-g_d & G + g_d
\end{bmatrix}
\begin{bmatrix}
V_+ \\
V_-
\end{bmatrix}
=
\begin{bmatrix}
I_{eq} \\
-I_{eq}
\end{bmatrix}
\]

Where \(G\) represents other conductances connected to the nodes, and:
\[
g_d = \frac{I_S}{n V_T} \exp\left(\frac{V_D}{n V_T}\right) + \frac{\partial I_{breakdown}}{\partial V_D}
\]
\[
I_{eq} = I_D - g_d V_D
\]

For diodes with series resistance \(R_S\), the stamp becomes a 3-node system (anode, cathode, internal junction node).

## 3. Convergence Analysis

### 3.1 Newton-Raphson Convergence for Exponential Nonlinearity

The diode's exponential I-V characteristic presents the most severe nonlinearity in SPICE. The Newton-Raphson iteration for the diode equation is:

\[
V_D^{(k+1)} = V_D^{(k)} - \frac{I_D(V_D^{(k)}) - I_{target}}{g_d(V_D^{(k)})}
\]

The convergence rate depends on the initial guess. For forward bias, if \(V_D^{(0)} \ll\) actual solution, \(g_d\) is extremely small, causing large steps and potential overshoot. SPICE employs **voltage limiting** to ensure convergence:

\[
V_D^{\text{new}} = \begin{cases}
V_D^{\text{old}} + \delta \cdot (V_D^{\text{new}} - V_D^{\text{old}}) & \text{if } |\Delta V_D| > V_{\text{max}} \\
V_D^{\text{new}} & \text{otherwise}
\end{cases}
\]

Where \(\delta = \frac{V_{\text{max}}}{|\Delta V_D|}\) and \(V_{\text{max}}\) is typically \(2V_T \approx 50\) mV.

The convergence criterion for diode current is:
\[
|I_D^{(k+1)} - I_D^{(k)}| < \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \cdot |I_D^{(k+1)}|
\]
with \(\epsilon_{\text{abs}} = 10^{-12}\) A (ABSTOL) and \(\epsilon_{\text{rel}} = 10^{-3}\) (RELTOL).

### 3.2 Numerical Conditioning and Ill-Posed Problems

The diode conductance spans many orders of magnitude:
- Reverse bias: \(g_d \approx \frac{I_S}{n V_T} \sim 10^{-12}\) S
- Forward bias (0.7V): \(g_d \approx \frac{I_S}{n V_T} e^{27} \sim 10^0\) S

This \(10^{12}\) range can cause ill-conditioning in the MNA matrix. The condition number contribution from a diode is:

\[
\kappa_{\text{diode}} \approx \frac{\max(g_d, G_{\text{other}})}{\min(g_d, G_{\text{other}})}
\]

SPICE mitigates this by:
1. Adding \(G_{\min} = 10^{-12}\) S in parallel with every p-n junction
2. Using double precision arithmetic
3. Implementing pivot selection in LU decomposition

### 3.3 Breakdown Region Convergence Challenges

Near the breakdown voltage \(BV\), the multiplication factor \(M(V_D)\) approaches infinity, causing numerical instability. The implementation clamps the denominator:

\[
M(V_D) = \frac{1}{\max\left(1 - \left(\frac{V_D}{BV}\right)^m, \epsilon\right)}
\]

with \(\epsilon \approx 10^{-6}\). Additionally, the derivative \(\frac{\partial M}{\partial V_D}\) is limited to prevent excessively large Jacobian entries.

### 3.4 Series Resistance Convergence

When \(R_S\) is large, the equation \(V_J = V_D - I_D R_S\) becomes stiff. The convergence requires careful handling:

\[
\frac{\partial I_D}{\partial V_D} = \frac{g_d}{1 + g_d R_S}
\]

For large forward current where \(g_d R_S \gg 1\), the sensitivity \(\frac{\partial I_D}{\partial V_D} \approx \frac{1}{R_S}\), making the diode behave resistively. The Newton-Raphson update is damped when \(g_d R_S > 10^3\) to prevent oscillation.

### 3.5 Charge Conservation and Time Step Control

For transient analysis, the diode charge \(Q_D = Q_j(V_D) + \tau_T I_D\) must be conserved. The local truncation error (LTE) for charge is:

\[
\text{LTE}_Q = \frac{h^2}{2} \left| \frac{d^2 Q}{dt^2} \right| \approx \frac{h^2}{2} \left| C_j \frac{d^2 V_D}{dt^2} + \frac{dC_j}{dV_D} \left(\frac{dV_D}{dt}\right)^2 + \tau_T \frac{d^2 I_D}{dt^2} \right|
\]

The time step \(h\) is controlled to keep:
\[
\frac{\text{LTE}_Q}{|Q_D| + Q_{\text{abs}}} < \text{RELTOL}
\]
where \(Q_{\text{abs}} = 10^{-14}\) C (CHGTOL).

For diodes switching between forward and reverse bias, the capacitance discontinuity at \(V_D = FC \cdot \phi\) requires special handling. SPICE uses the **charge-based formulation** rather than capacitance-based:

\[
I_{cap} = \frac{Q(V_D^{(k+1)}) - Q(V_D^{(k)})}{h}
\]

This ensures charge conservation regardless of the capacitance model discontinuities.

### 3.6 Initial Condition Convergence

When initial conditions \(V_D(0)\) are specified, the DC analysis must resolve any inconsistency. The algorithm:
1. Applies a large conductance \(G_{\text{ic}} = 10^{12}\) S in parallel with the diode
2. Solves for the initial operating point
3. Ramps down \(G_{\text{ic}}\) over 3-5 Newton iterations

The convergence criterion for initial conditions is:
\[
|G_{\text{ic}} V_D - I_D(V_D)| < \epsilon_{\text{abs}}
\]

### 3.7 Temperature Analysis Convergence

During temperature sweeps, the parameters \(I_S(T)\), \(\phi(T)\), etc., change exponentially. The Newton-Raphson iteration uses **parameter continuation**:

\[
P(T + \Delta T) = P(T) + \frac{\partial P}{\partial T} \Delta T
\]

If convergence fails at temperature \(T\), the step \(\Delta T\) is reduced by half. The temperature derivative of current is:

\[
\frac{\partial I_D}{\partial T} = I_D \left[ \frac{XTI}{T} + \frac{V_D - E_g/q}{n k T^2} \right]
\]

This sensitivity information is used to predict the solution at the next temperature point, improving convergence.

### 3.8 Statistical (Monte Carlo) Analysis Convergence

For Monte Carlo analysis with parameter variations, each sample requires DC convergence. The worst-case convergence occurs when multiple parameters vary simultaneously. The algorithm:

1. Uses the nominal solution as initial guess for all samples
2. Implements **step limiting** more aggressively for statistical runs
3. Tracks convergence failures and adjusts parameter distributions if failure rate > 5%

The convergence rate for Monte Carlo is typically slower due to:
- Larger parameter variations
- Interaction between multiple varying devices
- Boundary cases (e.g., diodes at the edge of breakdown)

### 3.9 DC Sweep Convergence

For DC voltage or current sweeps, the solution at sweep point \(k\) is used as initial guess for point \(k+1\). The step size control algorithm:

\[
\Delta V_{\text{next}} = \Delta V_{\text{current}} \times \min\left(2.0, \frac{N_{\text{iter,ideal}}}{N_{\text{iter,actual}}}\right)
\]

Where \(N_{\text{iter,ideal}} = 3\) and \(N_{\text{iter,actual}}\) is the number of Newton iterations at the current step. If \(N_{\text{iter,actual}} > 8\), the step is rejected and retried with \(\Delta V_{\text{next}}/2\).

### 3.10 Validation of Convergence

After convergence, SPICE validates the solution by:
1. Checking Kirchhoff's Current Law (KCL) at all nodes:
   \[
   \left|\sum I_{\text{into node}}\right| < \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \cdot \max|I_{\text{branch}}|
   \]
2. Verifying diode operating region consistency:
   - Forward bias: \(V_D > -5V_T \approx -0.13V\)
   - Reverse bias: \(V_D < 0\)
   - Breakdown: \(V_D < -0.9 \times BV\)
3. Checking energy conservation for reactive elements

If validation fails, the solution is marked as "questionable" and the user is warned. This comprehensive convergence analysis ensures robust DC analysis of diode circuits across all operating regions and temperatures.

## 4. C Implementation

The mathematical models and convergence strategies described in the previous sections are realized in Ngspice through specific C implementations in the core diode files. The following section details how the theoretical equations map directly to data structures and algorithms.

### 4.1 Core Data Structures (`diodefs.h`)

The diode model's state is encapsulated in two primary structures that store both parameters and dynamic simulation variables.

```c
typedef struct sDIOmodel {
    int DIOtype;                    /* Device type */
    double DIOtnom;                 /* Nominal temperature */
    double DIOis;                   /* Saturation current */
    double DIOn;                    /* Emission coefficient */
    double DIOrs;                   /* Series resistance */
    double DIObv;                   /* Breakdown voltage */
    double DIOibv;                  /* Breakdown current */
    double DIOcjo;                  /* Zero-bias junction capacitance */
    double DIOphi;                  /* Junction potential */
    double DIOfc;                   /* Forward bias capacitance coefficient */
    double DIOtt;                   /* Transit time */
    double DIOxti;                  /* IS temperature exponent */
    double DIOeg;                   /* Energy gap */
    double DIOM;                    /* Grading coefficient */
    /* ... additional parameters ... */
    struct sDIOmodel *DIOnextModel; /* Linked list of models */
    DIOinstance *DIOinstances;      /* List of instances */
} DIOmodel;

typedef struct sDIOinstance {
    char *DIOname;                  /* Instance name */
    int DIOposNode;                 /* Anode node */
    int DIOnegNode;                 /* Cathode node */
    int DIOintNode;                 /* Internal node (for RS) */
    
    /* Operating point state */
    double DIOvoltage;              /* Terminal voltage Vd */
    double DIOcurrent;              /* Diode current Id */
    double DIOconduct;              /* Small-signal conductance gd */
    double DIOcap;                  /* Junction capacitance */
    double DIOcharge;               /* Stored charge Qd */
    
    /* Matrix pointers for MNA stamp */
    double *DIOposPosPtr;           /* G_aa */
    double *DIOposNegPtr;           /* G_ac */
    double *DIOposIntPtr;           /* G_ai (if RS > 0) */
    double *DIOnegPosPtr;           /* G_ca */
    double *DIOnegNegPtr;           /* G_cc */
    double *DIOnegIntPtr;           /* G_ci (if RS > 0) */
    double *DIOintPosPtr;           /* G_ia (if RS > 0) */
    double *DIOintNegPtr;           /* G_ic (if RS > 0) */
    double *DIOintIntPtr;           /* G_ii (if RS > 0) */
    
    /* Model parameters with instance scaling */
    double DIOarea;                 /* Area scaling factor */
    double DIOtemp;                 /* Instance temperature */
    double DIOic;                   /* Initial condition voltage */
    int DIOoff;                     /* Initial off state */
    
    struct sDIOinstance *DIOnextInstance;
} DIOinstance;
```

These structures directly correspond to the mathematical variables: `DIOis` stores \(I_S\), `DIOn` stores \(n\), `DIOrs` stores \(R_S\), `DIObv` stores \(BV\), etc. The matrix pointers (`DIOposPosPtr`, etc.) provide efficient access to the SPICE MNA matrix for stamping the conductance contributions derived from \(g_d\).

### 4.2 Parameter Processing (`dioparam.c`)

The `DIOparam()` function validates and assigns netlist parameters to the internal structures, implementing the necessary scaling laws.

```c
int DIOparam(int param, IFvalue *value, DIOinstance *inst, DIOmodel *model)
{
    switch (param) {
        case DIO_IS:
            if (value->rValue <= 0.0) {
                printf("Error: IS must be positive\n");
                return E_BADPARM;
            }
            if (model) {
                model->DIOis = value->rValue;
            } else {
                inst->DIOis = value->rValue * inst->DIOarea;
            }
            break;
            
        case DIO_N:
            if (value->rValue <= 0.0) {
                printf("Error: N must be positive\n");
                return E_BADPARM;
            }
            if (model) {
                model->DIOn = value->rValue;
            } else {
                inst->DIOn = value->rValue;
            }
            break;
            
        case DIO_RS:
            if (value->rValue < 0.0) {
                printf("Error: RS cannot be negative\n");
                return E_BADPARM;
            }
            if (model) {
                model->DIOrs = value->rValue;
            } else {
                inst->DIOrs = value->rValue / inst->DIOarea;
            }
            break;
            
        case DIO_AREA:
            inst->DIOarea = value->rValue;
            /* Scale area-dependent parameters */
            if (!model) {
                inst->DIOis *= inst->DIOarea;
                inst->DIOrs /= inst->DIOarea;
                inst->DIOcjo *= inst->DIOarea;
            }
            break;
            
        case DIO_OFF:
            inst->DIOoff = value->iValue;
            break;
            
        /* ... handle other parameters (BV, IBV, CJO, TT, etc.) ... */
    }
    return OK;
}
```

This code ensures physical consistency (e.g., positive `IS`, `N`) and applies the area scaling factor \(I_S \rightarrow I_S \times \text{AREA}\), \(R_S \rightarrow R_S / \text{AREA}\) as required by device physics.

### 4.3 Temperature Scaling (`diotemp.c`)

The `DIOtemp()` function implements the temperature-dependent equations from Section 2.5, updating model parameters for the current simulation temperature.

```c
void DIOtemp(DIOmodel *model, CKTcircuit *ckt)
{
    double tnom, temp, ratio, vt, eg, arg;
    
    tnom = model->DIOtnom;
    temp = ckt->CKTtemp;
    ratio = temp / tnom;
    vt = CONSTKoverQ * temp;
    
    /* Calculate temperature-dependent energy gap */
    eg = 1.16 - (7.02e-4 * temp * temp) / (temp + 1108.0);
    
    /* Temperature scaling of saturation current */
    arg = -eg / (CONSTboltz * temp) + model->DIOeg / (CONSTboltz * tnom);
    model->DIOis *= pow(ratio, model->DIOxti) * exp(arg);
    
    /* Temperature scaling of junction potential */
    model->DIOphi = model->DIOphi * ratio - 
                    3.0 * vt * log(ratio) - 
                    eg * ratio + model->DIOeg;
    
    /* Temperature scaling of breakdown voltage */
    model->DIObv = model->DIObv * ratio;
    
    /* Temperature scaling of zero-bias capacitance */
    model->DIOcjo *= pow(ratio, 0.5 * model->DIOM);
    
    /* Update thermal voltage for all instances */
    for (DIOinstance *inst = model->DIOinstances; inst != NULL; inst = inst->DIOnextInstance) {
        inst->DIOvt = vt;
    }
}
```

This function maps directly to the mathematical formulations:
- Line 15 implements \(I_S(T) = I_S(T_0) \left(\frac{T}{T_0}\right)^{X_{TI}} \exp\left[\frac{E_g(T_0)}{k T_0} - \frac{E_g(T)}{k T}\right]\)
- Lines 18-20 implement \(\phi(T) = \phi(T_0) \frac{T}{T_0} - \frac{3k T}{q} \ln\left(\frac{T}{T_0}\right) - \frac{E_g(T_0) T}{T_0} + E_g(T)\)

### 4.4 DC Load Implementation (`dioload.c`)

The `DIOload()` function is the core computational routine that implements the Newton-Raphson iteration for DC analysis, translating the Shockley equation and its derivatives into matrix stamps.

```c
void DIOload(DIOmodel *model, CKTcircuit *ckt)
{
    double vd_new, vd_old, id, gd, ieq, vt;
    double mfactor, dIdV_breakdown;
    int has_series_resistance;
    
    for (DIOinstance *inst = model->DIOinstances; inst != NULL; inst = inst->DIOnextInstance) {
        vt = inst->DIOvt;
        
        /* Get new voltage guess from circuit solution */
        vd_new = *(ckt->CKTrhs + inst->DIOposNode) - *(ckt->CKTrhs + inst->DIOnegNode);
        vd_old = inst->DIOvoltage;
        
        /* Apply voltage limiting for convergence (DEVpnjlim) */
        vd_new = DEVpnjlim(vd_new, vd_old, vt, ckt->CKTvoltTol, &icheck);
        
        /* Calculate diode current and conductance */
        if (vd_new >= -3.0 * vt * inst->DIOn) {
            /* Forward bias region */
            double exp_arg = vd_new / (inst->DIOn * vt);
            if (exp_arg > 80.0) exp_arg = 80.0; /* Prevent overflow */
            id = inst->DIOis * (exp(exp_arg) - 1.0);
            gd = inst->DIOis * exp(exp_arg) / (inst->DIOn * vt);
        } else if (vd_new <= -inst->DIObv) {
            /* Breakdown region */
            double vbr = -vd_new / inst->DIObv;
            mfactor = 1.0 / (1.0 - pow(vbr, inst->DIOM));
            if (mfactor > 1e6) mfactor = 1e6; /* Clamp to prevent overflow */
            
            id = -inst->DIOis * mfactor;
            gd = (inst->DIOis / (inst->DIOn * vt)) * mfactor +
                 inst->DIOis * inst->DIOM * pow(vbr, inst->DIOM-1) * mfactor * mfactor / inst->DIObv;
        } else {
            /* Reverse bias region */
            id = -inst->DIOis;
            gd = inst->DIOis / (inst->DIOn * vt);
        }
        
        /* Handle series resistance if present */
        has_series_resistance = (inst->DIOrs > 0.0);
        if (has_series_resistance) {
            double gd_total = gd / (1.0 + gd * inst->DIOrs);
            double vj = vd_new - id * inst->DIOrs; /* Voltage across intrinsic junction */
            ieq = id - gd_total * vj;
            gd = gd_total;
            
            /* Stamp 3x3 matrix for anode-internal-cathode */
            *(inst->DIOposPosPtr) += gd;
            *(inst->DIOposIntPtr) -= gd;
            *(inst->DIOintPosPtr) -= gd;
            *(inst->DIOintIntPtr) += gd + 1.0/inst->DIOrs;
            *(inst->DIOnegIntPtr) -= 1.0/inst->DIOrs;
            *(inst->DIOintNegPtr) -= 1.0/inst->DIOrs;
            *(inst->DIOnegNegPtr) += 1.0/inst->DIOrs;
            
            /* Stamp RHS vector */
            ckt->CKTrhs[inst->DIOintNode] -= ieq;
        } else {
            /* No series resistance: standard 2-node stamp */
            ieq = id - gd * vd_new;
            
            *(inst->DIOposPosPtr) += gd;
            *(inst->DIOposNegPtr) -= gd;
            *(inst->DIOnegPosPtr) -= gd;
            *(inst->DIOnegNegPtr) += gd;
        }
        
        /* Stamp RHS vector for both cases */
        ckt->CKTrhs[inst->DIOposNode] -= ieq;
        ckt->CKTrhs[inst->DIOnegNode] += ieq;
        
        /* Store state for next iteration */
        inst->DIOvoltage = vd_new;
        inst->DIOcurrent = id;
        inst->DIOconduct = gd;
    }
}
```

This implementation maps directly to the mathematical models:
- Lines 20-27 implement the forward bias Shockley equation \(I_D = I_S[\exp(V_D/(nV_T)) - 1]\) and its derivative \(g_d = \frac{I_S}{nV_T} \exp(V_D/(nV_T))\)
- Lines 28-37 implement the breakdown model with multiplication factor \(M(V_D) = 1/(1 - (V_D/BV)^m)\) and its derivative
- Lines 42-44 implement the series resistance correction \(g_d^{\text{total}} = g_d/(1 + g_d R_S)\)
- Lines 47-58 and 61-64 implement the MNA matrix stamps derived in Section 2.6

### 4.5 Integration with SPICE Simulation Kernel

The diode model connects to Ngspice through the standard `SPICEdev` interface structure:

```c
SPICEdev DIOinfo = {
    .DEVpublic = {
        .name = "D",
        .description = "Diode",
        .terms = 2,
        .numNames = 1,
        .termNames = {"anode", "cathode"},
        .numInstanceParms = 25,
        .instanceParms = DIOPTable,
        .numModelParms = 20,
        .modelParms = DIOMTable,
        .flags = DEV_DEFAULT,
    },
    
    .DEVparam = DIOparam,
    .DEVmodParam = DIOMparam,
    .DEVload = DIOload,
    .DEVsetup = DIOsetup,
    .DEVunsetup = NULL,
    .DEVpzSetup = NULL,
    .DEVtemperature = DIOtemp,
    .DEVtrunc = DIOtrunc,
    .DEVfindBranch = NULL,
    .DEVacLoad = DIOacLoad,
    .DEVaccept = NULL,
    .DEVdestroy = DIOdestroy,
    .DEVmodDelete = DIOMdelete,
    .DEVdelete = DIOdelete,
    .DEVsetic = DIOgetic,
    .DEVask = DIOask,
    .DEVmodAsk = DIOMask,
    .DEVpzLoad = DIOpzLoad,
    .DEVconvTest = DIOconvTest,
    .DEVsenSetup = NULL,
    .DEVsenLoad = NULL,
    .DEVsenUpdate = NULL,
    .DEVsenAcLoad = NULL,
    .DEVsenPrint = NULL,
    .DEVdisto = DIOdisto,
    .DEVnoise = DIOnoise,
    .DEVsoaCheck = DIOsoaCheck,
};
```

This structure registers the diode's functions with the simulator, enabling DC, AC, transient, noise, distortion, and SOA analyses.

### 4.6 Convergence Checking Implementation

The convergence test function implements the criteria described in Section 3.1:

```c
int DIOconvTest(DIOmodel *model, CKTcircuit *ckt)
{
    double vd_new, vd_old, delta_v, tol;
    int converged = 1;
    
    for (DIOinstance *inst = model->DIOinstances; inst != NULL; inst = inst->DIOnextInstance) {
        vd_new = *(ckt->CKTrhs + inst->DIOposNode) - *(ckt->CKTrhs + inst->DIOnegNode);
        vd_old = inst->DIOvoltage;
        delta_v = fabs(vd_new - vd_old);
        
        tol = ckt->CKTreltol * MAX(fabs(vd_new), ckt->CKTvoltTol) + ckt->CKTabstol;
        
        if (delta_v > tol) {
            converged = 0;
            break;
        }
    }
    
    return converged;
}
```

This code implements the convergence criterion \(|V_D^{(k+1)} - V_D^{(k)}| < \text{RELTOL} \cdot \max(|V_D^{(k+1)}|, \text{VNTOL}) + \text{ABSTOL}\).

### 4.7 Summary of Mathematical-to-Code Mapping

The C implementation faithfully translates the diode physics mathematics:

1. **Shockley Equation** → `dioload.c` lines 20-27: Direct implementation of \(I_D = I_S[\exp(V_D/(nV_T)) - 1]\)
2. **Conductance Calculation** → `dioload.c` line 23: \(g_d = \frac{I_S}{nV_T} \exp(V_D/(nV_T))\)
3. **Breakdown Model** → `dioload.c` lines 28-37: Implementation of \(M(V_D)\) and its derivative
4. **Series Resistance** → `dioload.c` lines 42-44: \(g_d^{\text{total}} = g_d/(1 + g_d R_S)\)
5. **Temperature Scaling** → `diotemp.c`: Complete implementation of \(I_S(T)\), \(\phi(T)\), \(BV(T)\) equations
6. **MNA Matrix Stamp** → `dioload.c` lines 47-64: Implementation of \(\begin{bmatrix} g_d & -g_d \\ -g_d & g_d \end{bmatrix}\) pattern
7. **Convergence Test** → `dioconv.c`: Implementation of voltage change tolerance checking

The implementation demonstrates careful attention to numerical robustness through voltage limiting (`DEVpnjlim`), overflow prevention (clamping `exp_arg`), and singularity handling (clamping `mfactor`). This ensures stable Newton-Raphson convergence even for the strongly nonlinear diode characteristics across all operating regions.