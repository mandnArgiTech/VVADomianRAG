# MOS2: Transient Control and Convergence Checking

_Generated 2026-04-12 05:10 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2trun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2conv.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2ic.c`

# MOS2: Transient Control and Convergence Checking

## Introduction

Within the Ngspice circuit simulator, the transient analysis of the MOS2 (Level 2 MOSFET) device model requires sophisticated numerical control to ensure accuracy, stability, and efficiency. This critical functionality is distributed across three dedicated C source files: `mos2trun.c`, `mos2conv.c`, and `mos2ic.c`. Together, they implement the algorithms that manage time-step adaptation, verify solution convergence, and establish consistent starting conditions for time-domain simulation.

*   **`mos2trun.c`** implements the Local Truncation Error (LTE) calculation and adaptive time-step control. It estimates the numerical integration error for the device's five state charges (`q_gs`, `q_gd`, `q_gb`, `q_bd`, `q_bs`) using a predictor-corrector method with polynomial extrapolation. Based on the maximum error relative to SPICE tolerances, it recommends a new time step to the global transient analysis engine, dynamically balancing simulation speed with numerical accuracy.
*   **`mos2conv.c`** houses the Newton-Raphson convergence test function (`MOS2convTest`). After each iteration during the DC or transient operating point solution, this function checks whether the changes in terminal voltages (`V_gs`, `V_ds`, `V_bs`), the drain current (`I_ds`), and the state charges have fallen below composite relative and absolute tolerances. A positive convergence flag for all devices allows the simulation to proceed to the next time point.
*   **`mos2ic.c`** is responsible for establishing the initial operating point (`MOS2ic` function). It resolves the priority of initial condition sources—user-specified `.IC` vectors, the `OFF` flag, or the DC operating point—determines the initial region of operation (cutoff, linear, or saturation) via the threshold voltage calculation, and initializes the charge state variables using the piecewise Meyer capacitance model.

Collectively, these modules form the numerical backbone for the MOS2 model's dynamic simulation, managing the complex interplay between time discretization, nonlinear equation solving, and consistent initialization within the SPICE framework.

## Mathematical Formulation

The transient analysis of the MOS2 model in SPICE requires robust numerical methods to solve the time-dependent semiconductor equations while maintaining charge conservation and numerical stability. This involves three core mathematical components: numerical integration of nonlinear charges, local truncation error estimation for adaptive time stepping, and convergence criteria for the Newton-Raphson iteration.

### 1. Numerical Integration of Meyer Capacitance Charges

The MOS2 model uses the Meyer capacitance model, which defines voltage-dependent charges \( Q_{gs}(V_{gs}, V_{gd}, V_{gb}) \), \( Q_{gd}(V_{gs}, V_{gd}, V_{gb}) \), and \( Q_{gb}(V_{gs}, V_{gd}, V_{gb}) \) partitioned between gate terminals. The displacement currents are computed as time derivatives of these charges:

\[
I_{gs}(t) = \frac{dQ_{gs}}{dt}, \quad I_{gd}(t) = \frac{dQ_{gd}}{dt}, \quad I_{gb}(t) = \frac{dQ_{gb}}{dt}
\]

SPICE employs numerical integration methods (trapezoidal or Gear) to approximate these derivatives. For trapezoidal integration (default in SPICE):

\[
I_c(t) = \frac{dQ}{dt} \approx \frac{Q(t) - Q(t-\Delta t)}{\Delta t} + \frac{1}{2}\left[\frac{dQ}{dt}(t-\Delta t) + \frac{dQ}{dt}(t)\right]
\]

The charge functions are piecewise-defined based on operating region:

**Accumulation/Depletion (\(V_{gs} \leq \phi\)):**
\[
Q_{gs} = C_{ox} \cdot V_{gs}, \quad C_{ox} = \frac{\epsilon_{ox}}{t_{ox}} \cdot W_{eff} \cdot L_{eff}
\]

**Inversion (\( \phi < V_{gs} \leq V_{gb} - \phi \)):**
\[
Q_{gs} = C_{ox} \cdot \left[ \phi + \frac{V_{gs} - \phi}{2} \right]
\]

**Strong Inversion (\(V_{gs} > V_{gb} - \phi\)):**
\[
Q_{gs} = C_{ox} \cdot \left[ \phi + \frac{V_{gb} - \phi}{2} \right]
\]

Junction charges for bulk-drain and bulk-source diodes use the depletion approximation:
\[
Q_{bd} = C_{BD0} \cdot \left( \sqrt{PB \cdot V_{bd} + \epsilon} - 1 \right), \quad Q_{bs} = C_{BS0} \cdot \left( \sqrt{PB \cdot V_{bs} + \epsilon} - 1 \right)
\]
where \( \epsilon = 10^{-12} \) provides numerical regularization near \(V = 0\).

### 2. Local Truncation Error (LTE) for Adaptive Time Step Control

LTE estimates the error introduced by the numerical integration scheme, enabling adaptive time step control. For a state variable \(x(t)\) (charge or voltage), a predictor-corrector method is used:

**Polynomial Extrapolation Predictor:**
\[
x_{pred}(t+\Delta t) = 2.5 \cdot x(t) - 2.0 \cdot x(t-\Delta t) + 0.5 \cdot x(t-2\Delta t)
\]

**Local Truncation Error:**
\[
\text{LTE}_x = \frac{|x_{pred}(t+\Delta t) - x_{corrected}(t+\Delta t)|}{|x_{corrected}| + 1}
\]
The denominator term "+1" prevents division by zero for small \(x\).

**Time Step Adjustment:**
Given relative tolerance \(RTOL\) (typically 0.001), the new time step is:
\[
\Delta t_{new} = 0.75 \cdot \Delta t_{old} \cdot \sqrt{\frac{RTOL}{\text{LTE} + \epsilon}}, \quad \epsilon = 10^{-12}
\]
This formula reduces the step when LTE is large and cautiously increases it when LTE is small.

LTE is computed for five charges (\(Q_{gs}, Q_{gd}, Q_{gb}, Q_{bd}, Q_{bs}\)) and key voltages/currents (\(V_{gs}, I_{ds}\)). The maximum LTE determines the step adjustment.

### 3. Newton-Raphson Convergence Criteria

During each time point, SPICE solves the nonlinear circuit equations using Newton-Raphson iteration. Convergence is checked using mixed absolute-relative tolerances:

**Voltage Convergence:**
\[
|\Delta V| \leq \text{VREL\_TOL} \cdot \max(|V|, \text{VABS\_TOL}) + \text{VABS\_TOL}
\]
where \(\text{VREL\_TOL} = 0.001\) and \(\text{VABS\_TOL} = 10^{-6} \text{V}\).

**Current Convergence:**
\[
|\Delta I| \leq \text{IREL\_TOL} \cdot \max(|I|, \text{IABS\_TOL}) + \text{IABS\_TOL}
\]
where \(\text{IREL\_TOL} = 0.001\) and \(\text{IABS\_TOL} = 10^{-12} \text{A}\).

**Charge Convergence:**
\[
|\Delta Q| \leq \text{QREL\_TOL} \cdot \max(|Q|, \text{QABS\_TOL}) + \text{QABS\_TOL}
\]
where \(\text{QREL\_TOL} = 0.001\) and \(\text{QABS\_TOL} = 10^{-15} \text{C}\).

Convergence must be satisfied simultaneously for all three variable types: terminal voltages (\(V_{gs}, V_{ds}, V_{bs}\)), drain current (\(I_{ds}\)), and state charges (\(Q_{gs}, Q_{gd}, Q_{gb}\)).

### 4. Initial Condition Computation

Initial conditions establish the starting point for transient analysis. Three sources are considered in priority order:

1. **User-specified `.IC` values:** Directly set \(V_{DS}, V_{GS}, V_{BS}\)
2. **`OFF` flag:** Forces device into cutoff with \(I_{ds} = 0\)
3. **DC operating point:** Uses the solution from preceding DC analysis

The initial operating region is determined via threshold voltage:
\[
V_{th} = VTO + \gamma \cdot \left( \sqrt{\phi - V_{bs}} - \sqrt{\phi} \right)
\]
\[
\text{Mode} = 
\begin{cases}
0 & \text{if } V_{gs} \leq V_{th} \quad \text{(cutoff)} \\
1 & \text{if } V_{gs} > V_{th} \text{ and } V_{ds} \leq V_{gs} - V_{th} \quad \text{(linear)} \\
2 & \text{if } V_{gs} > V_{th} \text{ and } V_{ds} > V_{gs} - V_{th} \quad \text{(saturation)}
\end{cases}
\]

Initial charges are computed using the Meyer model formulas above, and initial \(I_{ds}\) is calculated using the appropriate regional current equation.

## Convergence Analysis

The convergence analysis for MOS2 transient simulation focuses on ensuring numerical stability of the time integration, reliability of the Newton-Raphson solver, and consistency of charge conservation.

### 1. Newton-Raphson Iteration Convergence

The nonlinear device equations are solved iteratively using Newton's method. Convergence behavior depends on the initial guess and device operating point.

**Region Transition Handling:**
Near the boundary between cutoff, linear, and saturation regions, the device equations have discontinuous second derivatives. The Newton-Raphson method can oscillate or diverge here. SPICE employs the `DEVfetlim()` function to limit voltage changes between iterations:
\[
V_{new} = \text{DEVfetlim}(V_{new}, V_{old}, V_{th})
\]
This algorithm prevents large jumps across region boundaries, particularly when \(V_{gs}\) crosses \(V_{th}\) or \(V_{ds}\) crosses \(V_{dsat}\).

**Damping for Persistent Non-convergence:**
If Newton iteration fails to converge after a specified number of steps (typically 10-20), SPICE applies damping:
\[
\Delta V_{damped} = \lambda \cdot \Delta V, \quad \lambda \in [0.1, 0.5]
\]
Reducing the step size \(\lambda\) improves convergence at the cost of more iterations.

**Source Stepping for Difficult Initial Conditions:**
When starting from poor initial guesses (e.g., all nodes at 0V), SPICE may use source stepping: gradually ramping independent sources from zero to their full values while solving intermediate DC points.

### 2. Time Step Control Stability

Adaptive time stepping based on LTE must balance accuracy with simulation speed.

**LTE Estimation Reliability:**
The predictor-corrector LTE estimation assumes smooth variation of state variables. During rapid switching events, the polynomial extrapolation may become inaccurate. SPICE implements safeguards:
- Minimum time step: \(\Delta t_{min} \approx 10^{-15}\) s prevents excessive refinement
- Maximum time step growth factor: Typically 2.0, preventing too-rapid expansion
- Step rejection and retry: If Newton fails to converge at a proposed time point, the step is halved and retried

**Charge Conservation Verification:**
The Meyer model, while computationally efficient, is not strictly charge-conserving. SPICE monitors charge error accumulation:
\[
\text{Charge Error} = \left| \sum_{\text{terminals}} \int I(t) dt \right|
\]
If this exceeds a tolerance (e.g., \(10^{-10} \cdot \max|Q|\)), a warning may be issued, though the simulation continues.

### 3. Numerical Integration Stability

The choice of integration method affects stability and accuracy:

**Trapezoidal Rule Stability:**
The trapezoidal method is A-stable but can produce numerical ringing (overshoot) on sharp transitions. For MOS2 switching, this manifests as damped oscillations in computed node voltages after fast edges. The numerical damping factor is:
\[
\zeta = \frac{2 - \alpha}{2 + \alpha}, \quad \alpha = \frac{\Delta t}{\tau}
\]
where \(\tau\) is the circuit time constant. For small \(\Delta t \ll \tau\), \(\zeta \approx 1\) (no damping); for large \(\Delta t\), numerical damping increases.

**Gear Method Alternative:**
SPICE offers Gear integration (order 2-6) as an alternative. Gear methods are L-stable and suppress numerical ringing but introduce more damping. The trade-off is between accuracy (trapezoidal) and stability (Gear).

### 4. Initial Condition Consistency

The initial state must satisfy Kirchhoff's laws and device equations simultaneously.

**DC-IC Continuity:**
When `.IC` directives specify voltages different from the DC solution, SPICE must reconcile these. The algorithm:
1. Applies IC voltages as constraints
2. Solves for remaining node voltages
3. Computes consistent initial currents and charges
This ensures the transient simulation starts from a physically consistent state.

**Operating Point Continuity:**
If the initial DC point places the device at a region boundary (e.g., \(V_{gs} = V_{th}\)), small numerical errors can cause oscillation between regions in early time steps. SPICE adds a small hysteresis margin (\(\approx 10^{-6}\) V) to region detection logic during the first few iterations.

### 5. Error Propagation and Accumulation

Long transient simulations can accumulate numerical error.

**Global Error Control:**
While LTE controls local error per step, global error accumulates as:
\[
E_{global} \approx \sum_{n=1}^{N} \text{LTE}_n \cdot e^{\lambda (t_N - t_n)}
\]
where \(\lambda\) is the Lipschitz constant of the system. SPICE does not directly control global error but relies on keeping LTE sufficiently small at each step.

**Round-off Error Management:**
For ill-conditioned matrices (e.g., when \(R_D\) or \(R_S\) is very small), round-off error in the LU decomposition can affect convergence. SPICE uses partial pivoting and iterative refinement to mitigate this.

### 6. Convergence Monitoring and Diagnostics

SPICE provides diagnostics for convergence difficulties:

**Iteration Count Tracking:**
If Newton iteration consistently requires many steps (>10) at multiple time points, SPICE may warn about possible convergence issues.

**Matrix Condition Number Estimation:**
During linear solves, approximate condition numbers are monitored. If \(\kappa(\mathbf{J}) > 10^{12}\), where \(\mathbf{J}\) is the Jacobian, accuracy may be compromised.

**Charge Imbalance Reporting:**
At the end of transient analysis, total charge imbalance is reported, helping identify non-conservative formulations or integration errors.

### 7. PMOS and Inverse Mode Convergence

For PMOS devices or when \(V_{ds} < 0\) (inverse mode), internal source-drain swapping ensures the mathematical formulation always operates with \(V_{ds} \geq 0\). This swapping must be consistent across all analyses (DC, transient, AC) to avoid convergence issues from inconsistent terminal assignments.

The convergence of MOS2 transient analysis thus relies on a careful interplay of robust numerical integration, adaptive step control, Newton-Raphson stabilization techniques, and consistency enforcement across the simulation workflow. These mechanisms ensure reliable simulation of MOS2 devices across all operating regions and time scales within the SPICE framework.

## C Implementation

### 1. Core Data Structures for Transient Analysis

The MOS2 model's transient analysis relies on the `MOS2instance` structure defined in `mos2defs.h`, which contains specialized fields for tracking time-domain state variables and convergence history. These fields map directly to the mathematical variables required for numerical integration and error control.

#### 1.1 State Tracking Structure
The `MOS2instance` struct includes comprehensive state tracking for voltages, currents, and charges across multiple time points:

```c
typedef struct sMOS2instance {
    /* Time-domain state variables - current values */
    double MOS2vgs;      /* Gate-source voltage V_gs(t) */
    double MOS2vds;      /* Drain-source voltage V_ds(t) */
    double MOS2vbs;      /* Bulk-source voltage V_bs(t) */
    
    /* History for polynomial extrapolation (t-Δt, t-2Δt) */
    double MOS2vgs_old;  /* V_gs(t-Δt) */
    double MOS2vds_old;  /* V_ds(t-Δt) */
    double MOS2vbs_old;  /* V_bs(t-Δt) */
    double MOS2vgs_old2; /* V_gs(t-2Δt) */
    double MOS2vds_old2; /* V_ds(t-2Δt) */
    double MOS2vbs_old2; /* V_bs(t-2Δt) */
    
    /* Drain current tracking */
    double MOS2ids;      /* I_ds(t) */
    double MOS2ids_old;  /* I_ds(t-Δt) */
    double MOS2ids_old2; /* I_ds(t-2Δt) */
    
    /* State vector indices for charge storage */
    double MOS2qgs;      /* Index for Q_gs in state vector */
    double MOS2qgd;      /* Index for Q_gd in state vector */
    double MOS2qgb;      /* Index for Q_gb in state vector */
    double MOS2qbd;      /* Index for Q_bd in state vector */
    double MOS2qbs;      /* Index for Q_bs in state vector */
    
    /* Previous iteration values for convergence testing */
    double MOS2vgs_prev; /* V_gs from previous NR iteration */
    double MOS2vds_prev; /* V_ds from previous NR iteration */
    double MOS2vbs_prev; /* V_bs from previous NR iteration */
    double MOS2ids_prev; /* I_ds from previous NR iteration */
    double MOS2qgs_prev; /* Q_gs from previous NR iteration */
    double MOS2qgd_prev; /* Q_gd from previous NR iteration */
    double MOS2qgb_prev; /* Q_gb from previous NR iteration */
    
    /* Charge derivative history for trapezoidal integration */
    double MOS2dqgsdt_old; /* dQ_gs/dt at t-Δt */
    double MOS2dqgddt_old; /* dQ_gd/dt at t-Δt */
    double MOS2dqgbdt_old; /* dQ_gb/dt at t-Δt */
    
    /* Operating region flag */
    int MOS2mode;        /* 0=cutoff, 1=linear/triode, 2=saturation */
    
    /* Initial condition control */
    int MOS2icVDSgiven;  /* Flag: user specified initial V_DS */
    int MOS2icVGSgiven;  /* Flag: user specified initial V_GS */
    int MOS2icVBSgiven;  /* Flag: user specified initial V_BS */
    double MOS2icVDS;    /* User-specified initial V_DS value */
    double MOS2icVGS;    /* User-specified initial V_GS value */
    double MOS2icVBS;    /* User-specified initial V_BS value */
    
    /* Additional device parameters... */
} MOS2instance;
```

This structure implements the mathematical state tracking requirements: `x(t)`, `x(t-Δt)`, and `x(t-2Δt)` for each state variable `x ∈ {V_gs, V_ds, V_bs, I_ds}`. The charge state indices (`MOS2qgs`, etc.) point to locations in the global state vector `ckt->CKTstates[]` where the actual charge values are stored.

### 2. Local Truncation Error Calculation (`mos2trun.c`)

The `MOS2trunc()` function implements the mathematical Local Truncation Error (LTE) estimation and adaptive time step control algorithm. This function is called by Ngspice's transient analysis engine to determine if the current time step meets accuracy requirements.

#### 2.1 Polynomial Extrapolation for LTE Estimation
The mathematical predictor formula `x_pred = 2.5·x_n - 2.0·x_{n-1} + 0.5·x_{n-2}` is implemented for both charges and voltages:

```c
int MOS2trunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep) {
    MOS2model *model;
    MOS2instance *inst;
    
    for(model = (MOS2model *)inModel; model != NULL; model = model->MOS2nextModel) {
        for(inst = model->MOS2instances; inst != NULL; inst = inst->MOS2nextInstance) {
            /* Retrieve charge history from state vector */
            double qgs_t   = *(ckt->CKTrhs + inst->MOS2qgs);    /* Q_gs(t) */
            double qgs_tm1 = *(ckt->CKTrhsOld + inst->MOS2qgs); /* Q_gs(t-Δt) */
            double qgs_tm2 = *(ckt->CKTstate0 + inst->MOS2qgs); /* Q_gs(t-2Δt) */
            
            /* Implement: Q_pred = 2.5·Q_n - 2.0·Q_{n-1} + 0.5·Q_{n-2} */
            double qgs_pred = 2.5 * qgs_t - 2.0 * qgs_tm1 + 0.5 * qgs_tm2;
            
            /* Calculate LTE for gate-source charge: LTE = |Q_pred - Q| / (|Q| + 1) */
            double lte_qgs = fabs(qgs_pred - qgs_t) / (fabs(qgs_t) + 1.0);
            
            /* Repeat for other charges: Q_gd, Q_gb, Q_bd, Q_bs */
            double qgd_t = *(ckt->CKTrhs + inst->MOS2qgd);
            double qgd_tm1 = *(ckt->CKTrhsOld + inst->MOS2qgd);
            double qgd_tm2 = *(ckt->CKTstate0 + inst->MOS2qgd);
            double qgd_pred = 2.5 * qgd_t - 2.0 * qgd_tm1 + 0.5 * qgd_tm2;
            double lte_qgd = fabs(qgd_pred - qgd_t) / (fabs(qgd_t) + 1.0);
            
            /* Voltage LTE using stored history in instance struct */
            /* V_gs_pred = 2.5·V_gs(t) - 2.0·V_gs(t-Δt) + 0.5·V_gs(t-2Δt) */
            double vgs_pred = 2.5 * inst->MOS2vgs - 2.0 * inst->MOS2vgs_old 
                            + 0.5 * inst->MOS2vgs_old2;
            
            /* Voltage LTE with mixed relative-absolute tolerance */
            double vgs_tol = ckt->CKTreltol * MAX(fabs(inst->MOS2vgs), ckt->CKTvoltTol) 
                           + ckt->CKTabstol;
            double lte_vgs = fabs(vgs_pred - inst->MOS2vgs) / vgs_tol;
            
            /* Current LTE for drain current */
            double ids_pred = 2.5 * inst->MOS2ids - 2.0 * inst->MOS2ids_old 
                            + 0.5 * inst->MOS2ids_old2;
            double ids_tol = ckt->CKTreltol * MAX(fabs(inst->MOS2ids), ckt->CKTcurTol) 
                           + ckt->CKTabstol;
            double lte_ids = fabs(ids_pred - inst->MOS2ids) / ids_tol;
            
            /* Find maximum LTE across all variables */
            double lte_total = MAX(MAX(lte_qgs, lte_qgd), 
                                  MAX(MAX(lte_vgs, lte_ids), 
                                      ckt->CKTtrtol * ckt->CKTdeltaOld));
            
            /* Time step adjustment: Δt_new = 0.75·Δt_old · √(RTOL / (LTE + ε)) */
            if(lte_total > ckt->CKTrtol) {
                double deltaNew = 0.75 * ckt->CKTdeltaOld * 
                                 sqrt(ckt->CKTrtol / (lte_total + 1e-12));
                *timeStep = MIN(*timeStep, deltaNew);
            }
            
            /* Update history for next time step */
            inst->MOS2vgs_old2 = inst->MOS2vgs_old;  /* t-2Δt ← t-Δt */
            inst->MOS2vgs_old = inst->MOS2vgs;       /* t-Δt ← t */
            inst->MOS2ids_old2 = inst->MOS2ids_old;
            inst->MOS2ids_old = inst->MOS2ids;
        }
    }
    return OK;
}
```

This C code directly implements the mathematical LTE estimation algorithm:
1. **Polynomial Extrapolation**: `x_pred = 2.5·x_n - 2.0·x_{n-1} + 0.5·x_{n-2}`
2. **Error Calculation**: `LTE = |x_pred - x_actual| / tolerance(x_actual)`
3. **Time Step Control**: `Δt_new = 0.75·Δt_old · √(RTOL / LTE)`

The tolerance function `tolerance(x)` implements the SPICE mixed relative-absolute criterion: `tolerance(x) = reltol·max(|x|, abstol) + abstol`.

#### 2.2 Charge Calculation for Transient Analysis
The `MOS2trunc()` function also computes the nonlinear Meyer capacitances for transient analysis:

```c
/* Within MOS2trunc() iteration loop */
double vgs = ckt->CKTrhs[inst->MOS2gNode] - ckt->CKTrhs[inst->MOS2sNode];
double vgd = ckt->CKTrhs[inst->MOS2gNode] - ckt->CKTrhs[inst->MOS2dNode];
double vgb = ckt->CKTrhs[inst->MOS2gNode] - ckt->CKTrhs[inst->MOS2bNode];

/* Meyer capacitance model - piecewise voltage-dependent charges */
double qgs_new, qgd_new, qgb_new;

if(vgs <= model->MOS2phi) {
    /* Accumulation/Depletion region: Q_gs = C_ox·V_gs */
    qgs_new = model->MOS2cox * vgs;
} else if(vgs <= vgb - model->MOS2phi) {
    /* Inversion region: Q_gs = C_ox·[φ + (V_gs - φ)/2] */
    qgs_new = model->MOS2cox * (model->MOS2phi + (vgs - model->MOS2phi)/2);
} else {
    /* Strong inversion: Q_gs = C_ox·[φ + (V_gb - φ)/2] */
    qgs_new = model->MOS2cox * (model->MOS2phi + (vgb - model->MOS2phi)/2);
}

/* Store computed charges in state vector */
*(ckt->CKTrhs + inst->MOS2qgs) = qgs_new;
*(ckt->CKTrhs + inst->MOS2qgd) = qgd_new;
*(ckt->CKTrhs + inst->MOS2qgb) = qgb_new;

/* Junction charges with numerical protection for sqrt() */
double vbd = ckt->CKTrhs[inst->MOS2bNode] - ckt->CKTrhs[inst->MOS2dNode];
double vbs = ckt->CKTrhs[inst->MOS2bNode] - ckt->CKTrhs[inst->MOS2sNode];
double qbd_new = model->MOS2cbd * (sqrt(model->MOS2pb * vbd + 1e-12) - 1);
double qbs_new = model->MOS2cbs * (sqrt(model->MOS2pb * vbs + 1e-12) - 1);

*(ckt->CKTrhs + inst->MOS2qbd) = qbd_new;
*(ckt->CKTrhs + inst->MOS2qbs) = qbs_new;
```

This implements the mathematical Meyer capacitance model with piecewise voltage-dependent charge calculations and includes numerical protection `sqrt(x + 1e-12)` to prevent domain errors.

### 3. Convergence Testing Implementation (`mos2conv.c`)

The `MOS2convTest()` function implements the mathematical convergence criteria for Newton-Raphson iteration during transient analysis. It checks whether changes in voltages, currents, and charges have fallen below specified tolerances.

#### 3.1 Voltage Convergence Check
The mathematical criterion `|ΔV| ≤ reltol·max(|V|, vntol) + vntol` is implemented as:

```c
int MOS2convTest(GENmodel *inModel, CKTcircuit *ckt) {
    MOS2model *model;
    MOS2instance *inst;
    
    for(model = (MOS2model *)inModel; model != NULL; model = model->MOS2nextModel) {
        for(inst = model->MOS2instances; inst != NULL; inst = inst->MOS2nextInstance) {
            /* Get current voltages from circuit RHS vector */
            double vgs = ckt->CKTrhs[inst->MOS2gNode] - ckt->CKTrhs[inst->MOS2sNode];
            double vds = ckt->CKTrhs[inst->MOS2dNode] - ckt->CKTrhs[inst->MOS2sNode];
            double vbs = ckt->CKTrhs[inst->MOS2bNode] - ckt->CKTrhs[inst->MOS2sNode];
            
            /* Calculate changes from previous iteration */
            double del_vgs = vgs - inst->MOS2vgs_prev;
            double del_vds = vds - inst->MOS2vds_prev;
            double del_vbs = vbs - inst->MOS2vbs_prev;
            
            /* Voltage tolerance: tol_v = reltol·max(|V|, vntol) + vntol */
            double tol_v = ckt->CKTreltol * MAX(fabs(vgs), ckt->CKTvoltTol) 
                         + ckt->CKTvoltTol;
            
            /* Check convergence: |ΔV| ≤ tol_v */
            if(fabs(del_vgs) > tol_v) {
                return NONCONVERGENT;
            }
            
            tol_v = ckt->CKTreltol * MAX(fabs(vds), ckt->CKTvoltTol) 
                  + ckt->CKTvoltTol;
            if(fabs(del_vds) > tol_v) {
                return NONCONVERGENT;
            }
            
            tol_v = ckt->CKTreltol * MAX(fabs(vbs), ckt->CKTvoltTol) 
                  + ckt->CKTvoltTol;
            if(fabs(del_vbs) > tol_v) {
                return NONCONVERGENT;
            }
```

#### 3.2 Current and Charge Convergence Checks
The function also implements convergence checks for drain current and charges using similar mixed relative-absolute criteria:

```c
            /* Current convergence: |ΔI_ds| ≤ reltol·max(|I_ds|, abstol) + abstol */
            double del_ids = inst->MOS2ids - inst->MOS2ids_prev;
            double ids_mag = MAX(fabs(inst->MOS2ids), ckt->CKTabstol);
            double ids_tol = ckt->CKTreltol * ids_mag + ckt->CKTabstol;
            
            if(fabs(del_ids) > ids_tol) {
                return NONCONVERGENT;
            }
            
            /* Charge convergence check */
            double qgs = *(ckt->CKTrhs + inst->MOS2qgs);
            double qgd = *(ckt->CKTrhs + inst->MOS2qgd);
            double qgb = *(ckt->CKTrhs + inst->MOS2qgb);
            
            double del_qgs = qgs - inst->MOS2qgs_prev;
            double del_qgd = qgd - inst->MOS2qgd_prev;
            double del_qgb = qgb - inst->MOS2qgb_prev;
            
            /* Charge tolerance: typically CHGTOL = 1e-14 */
            double tol_c = ckt->CKTreltol * MAX(fabs(qgs), ckt->CKTchargeTol) 
                         + ckt->CKTchargeTol;
            
            if(fabs(del_qgs) > tol_c) {
                return NONCONVERGENT;
            }
            
            tol_c = ckt->CKTreltol * MAX(fabs(qgd), ckt->CKTchargeTol) 
                  + ckt->CKTchargeTol;
            if(fabs(del_qgd) > tol_c) {
                return NONCONVERGENT;
            }
            
            tol_c = ckt->CKTreltol * MAX(fabs(qgb), ckt->CKTchargeTol) 
                  + ckt->CKTchargeTol;
            if(fabs(del_qgb) > tol_c) {
                return NONCONVERGENT;
            }
            
            /* Store current values as previous for next iteration */
            inst->MOS2vgs_prev = vgs;
            inst->MOS2vds_prev = vds;
            inst->MOS2vbs_prev = vbs;
            inst->MOS2ids_prev = inst->MOS2ids;
            inst->MOS2qgs_prev = qgs;
            inst->MOS2qgd_prev = qgd;
            inst->MOS2qgb_prev = qgb;
        }
    }
    return CONVERGENT;
}
```

This implementation enforces the mathematical convergence criteria for all three variable classes:
- **Voltages**: `|ΔV| ≤ reltol·max(|V|, vntol) + vntol`
- **Currents**: `|ΔI| ≤ reltol·max(|I|, abstol) + abstol`
- **Charges**: `|ΔQ| ≤ reltol·max(|Q|, chgtol) + chgtol`

All checks must pass for the device to be considered converged.

### 4. Initial Condition Setup (`mos2ic.c`)

The `MOS2ic()` function implements the mathematical initial condition computation, setting up the device state at time t=0 based on user specifications or DC operating point.

#### 4.1 User-Specified Initial Conditions
The function applies user-specified `.IC` values from the SPICE netlist:

```c
int MOS2ic(GENmodel *inModel, CKTcircuit *ckt) {
    MOS2model *model;
    MOS2instance *inst;
    
    for(model = (MOS2model *)inModel; model != NULL; model = model->MOS2nextModel) {
        for(inst = model->MOS2instances; inst != NULL; inst = inst->MOS2nextInstance) {
            /* Apply user-specified V_DS initial condition */
            if(inst->MOS2icVDSgiven) {
                double vds_ic = inst->MOS2icVDS;
                /* Distribute voltage equally between drain and source nodes */
                ckt->CKTrhs[inst->MOS2dNode] -= vds_ic * 0.5;
                ckt->CKTrhs[inst->MOS2sNode] += vds_ic * 0.5;
                inst->MOS2vds = vds_ic;
            }
            
            /* Apply user-specified V_GS initial condition */
            if(inst->MOS2icVGSgiven) {
                double vgs_ic = inst->MOS2icVGS;
                ckt->CKTrhs[inst->MOS2gNode] -= vgs_ic * 0.5;
                ckt->CKTrhs[inst->MOS2sNode] += vgs_ic * 0.5;
                inst->MOS2vgs = vgs_ic;
            }
            
            /* Apply user-specified V_BS initial condition */
            if(inst->MOS2icVBSgiven) {
                double vbs_ic = inst->MOS2icVBS;
                ckt->CKTrhs[inst->MOS2bNode] -= vbs_ic * 0.5;
                ckt->CKTrhs[inst->MOS2sNode] += vbs_ic * 0.5;
                inst->MOS2vbs = vbs_ic;
            }
```

#### 4.2 Initial Charge Computation
Based on the initial voltages, the function computes the corresponding charges using the Meyer model:

```c
            /* Compute initial charges based on IC voltages */
            double vgs = inst->MOS2vgs;
            double vds = inst->MOS2vds;
            double vbs = inst->MOS2vbs;
            double vgd