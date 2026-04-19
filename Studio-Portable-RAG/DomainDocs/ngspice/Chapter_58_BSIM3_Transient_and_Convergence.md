# BSIM3: Transient Control and Charge Conservation

_Generated 2026-04-12 10:05 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3trunc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3cvtest.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bsim3/b3getic.c`

# **BSIM3: Transient Control and Charge Conservation**

## **Introduction**

This chapter details the implementation of transient analysis and charge conservation for the BSIM3 deep-submicron MOSFET model within the Ngspice simulation framework. The focus is on three critical C source files that govern the device's behavior during time-domain simulation: `b3trunc.c`, `b3cvtest.c`, and `b3getic.c`. These files implement the core algorithms that ensure numerical stability, convergence, and physical accuracy when simulating the dynamic response of BSIM3 transistors.

*   **`b3trunc.c` (Local Truncation Error Control)**: This file contains the `B3trunc()` function, which is central to SPICE's adaptive time-stepping algorithm. It calculates the Local Truncation Error (LTE) for the device's stored charges (`Qgs`, `Qgd`, `Qgb`, `Qbd`, `Qbs`). By estimating the error introduced by the numerical integration method (e.g., trapezoidal or Gear), it provides a recommended maximum time step (`tiStep`) to the SPICE kernel, ensuring simulation accuracy while maximizing efficiency.

*   **`b3cvtest.c` (Convergence Testing)**: This file implements the `B3convTest()` function, a critical component of the Newton-Raphson iterative solver. After each iteration during DC or transient analysis, this function checks whether the device's terminal voltages (`Vgs`, `Vds`, `Vbs`), terminal currents (`Id`), and associated charges have changed by an amount less than the SPICE-defined tolerances (`CKTreltol`, `CKTabstol`, `CKTvoltTol`). It returns a convergence flag, signaling to the solver whether another iteration is required or if the solution has been found.

*   **`b3getic.c` (Initial Condition Calculation)**: This file provides the `B3getic()` function, which establishes the initial state of the transistor at the beginning of a transient analysis (`UIC` option) or during the DC operating point calculation. It processes user-specified initial conditions (`IC=VGS, VDS, VBS`), calculates the corresponding threshold voltage (`Vth`), determines the initial operating region (cutoff, linear, saturation), and computes the initial drain current and stored charges. This provides a consistent and physically correct starting point for the time-domain simulation, preventing convergence issues at `t=0`.

Together, these modules form the backbone of the BSIM3 model's time-domain simulation capability, enforcing charge conservation, controlling numerical error, and guaranteeing the robustness of the Newton-Raphson algorithm across all bias conditions and complex input waveforms.

---

## **Mathematical Formulation**

This section details the mathematical models implemented in Ngspice's BSIM3v3 for transient analysis, focusing on charge conservation, local truncation error (LTE) control, and the convergence criteria for the Newton-Raphson iteration. All formulations are explicitly tied to SPICE's time-domain simulation framework.

### **1. Charge Conservation Formulation**

The BSIM3 model uses a charge-based approach for transient analysis to guarantee charge conservation, a critical requirement for numerical stability. Terminal charges are computed as functions of terminal voltages, and currents are derived from their time derivatives.

#### **1.1 Terminal Charge Definitions**

The model defines five independent charge states stored in the SPICE state vector:
*   **Gate-Source Charge:** `Q_gs = f_qgs(V_gs, V_ds, V_bs)`
*   **Gate-Drain Charge:** `Q_gd = f_qgd(V_gs, V_ds, V_bs)`
*   **Gate-Bulk Charge:** `Q_gb = f_qgb(V_gs, V_ds, V_bs)`
*   **Bulk-Drain Diode Charge:** `Q_bd = f_qbd(V_bd)`
*   **Bulk-Source Diode Charge:** `Q_bs = f_qbs(V_bs)`

The total gate charge is: `Q_G = Q_gs + Q_gd + Q_gb`.
The charge conservation law is enforced: `Q_G + Q_D + Q_S + Q_B = 0`, where `Q_D`, `Q_S`, `Q_B` are the charges supplied by the drain, source, and bulk terminals, respectively.

#### **1.2 Current Calculation from Charge**

The terminal currents in transient analysis are the sum of the conductive current (from the DC model) and the displacement current:
```
I_G(t) = dQ_G/dt
I_D(t) = I_ds(V_gs, V_ds, V_bs) + dQ_D/dt
I_S(t) = -I_ds(V_gs, V_ds, V_bs) + dQ_S/dt
I_B(t) = I_bs(V_bs) + I_bd(V_bd) + dQ_B/dt
```
Where `I_ds` is the DC drain current from the BSIM3 core equations, and `I_bs`, `I_bd` are the diode currents.

#### **1.3 Capacitance Calculation**

The transcapacitances are defined as the derivatives of charge with respect to voltage, ensuring a symmetric and reciprocal capacitance matrix for energy conservation:
```
C_ij = ∂Q_i/∂V_j,  with i, j ∈ {G, D, S, B}
```
For example:
*   `C_gs = ∂Q_gs/∂V_gs + ∂Q_gd/∂V_gs + ∂Q_gb/∂V_gs`
*   `C_gd = ∂Q_gs/∂V_ds + ∂Q_gd/∂V_ds + ∂Q_gb/∂V_ds`

The implementation ensures `C_ij = C_ji`, which is a necessary condition for charge conservation.

### **2. Local Truncation Error (LTE) Control**

SPICE uses variable time-step integration to balance accuracy and speed. The LTE is estimated for each charge state to determine if the time step `h` is acceptable.

#### **2.1 Numerical Integration Methods**

SPICE typically uses the Trapezoidal or Gear integration methods. The charge derivative is approximated as:
*   **Trapezoidal Rule:** `(Q_n - Q_{n-1})/h = 0.5 * (dQ/dt|_n + dQ/dt|_{n-1})`
*   **Gear Method (2nd order):** `(3Q_n - 4Q_{n-1} + Q_{n-2})/(2h) = dQ/dt|_n`

Where `h` is the time step, and `n` denotes the current time point.

#### **2.2 LTE Estimation Formula**

The local truncation error for a charge `Q` integrated with a method of order `p` is:
```
LTE_Q = |h^{p+1}/(p+1)! * d^{p+1}Q/dt^{p+1} + O(h^{p+2})|
```
For the trapezoidal rule (`p=2`), the leading error term is:
```
LTE_Q ≈ |h³/12 * d³Q/dt³|
```
The implementation in `b3trunc.c` estimates the third derivative using finite differences on stored charge history:
```
ddcharge = (diff1 - diff2) / (0.5 * (h_old + h_older))
dddcharge = (ddcharge - ddcharge_old) / h_old
LTE = fabs(h_old³ * dddcharge / 12.0)
```
Where `diff1 = (Q_n - Q_{n-1})/h_old`, `diff2 = (Q_{n-1} - Q_{n-2})/h_older`.

#### **2.3 Normalized LTE and Time-Step Control**

The raw LTE is normalized by a tolerance to decide if the step is acceptable:
```
LTE_norm = LTE / (TOL * max(|Q|, Q_min) + EPS)
```
Where `TOL = ckt->CKTtrtol` (typically 7.0), `Q_min` is a minimum charge (e.g., `inst->B3cgsteff`), and `EPS = ckt->CKTvoltTol`. If `LTE_norm > 1`, the step is rejected. The function suggests a new step:
```
h_new = h_old / (LTE_norm)^{1/(p+1)}
```
For `p=2`, `h_new = h_old / sqrt(sqrt(LTE_norm))`.

### **3. Voltage Limiting for Newton-Raphson Convergence**

To ensure convergence of the Newton-Raphson iteration during transient analysis, voltage changes between iterations are limited using the `DEVfetlim` function (called from the load function in `b3ld.c`).

#### **3.1 Voltage Limiting Algorithm**

For each critical voltage `V_new` (e.g., `V_gs`, `V_ds`), the limited voltage `V_lim` is computed based on the previous iteration's value `V_old` and a threshold `V_to`:
```
DEVfetlim(V_new, V_old, V_to):
    if (V_old > V_to):
        if (V_new > V_old):
            V_lim = V_old + (V_new - V_old) / (1 + (V_new - V_old)/(V_dd - V_old))
        else if (V_new > V_to):
            V_lim = V_new
        else:
            delta = V_to - V_new
            V_lim = V_to - delta / (1 + delta/(V_old - V_to))
    else:
        ... (symmetric case for V_old < V_to) ...
```
This hyperbolic limiting function prevents the Newton iteration from jumping over regions of high nonlinearity (e.g., the subthreshold to strong inversion boundary).

#### **3.2 Source-Drain Symmetry Handling**

For physical consistency and better convergence, if `V_ds < 0`, the device terminals are swapped:
```
if (V_ds < 0.0):
    SWAP(D_node, S_node)
    SWAP(D'_node, S'_node)
    V_ds = -V_ds
    V_gs = V_gd
    V_bs = V_bd
    SWAP(g_m, -g_mbs)
    SWAP(g_ds, g_bd)
```
This ensures the internal equations always see `V_ds ≥ 0`, simplifying the model evaluation.

### **4. State Vector Management**

The BSIM3 instance uses the SPICE state vector (accessed via `ckt->CKTstate`) to store charge history for LTE calculation and integration.

#### **4.1 State Indices**

The `B3setup()` function allocates state indices for each charge:
```
inst->B3stateQgs = *states; (*states)++;
inst->B3stateQgd = *states; (*states)++;
inst->B3stateQgb = *states; (*states)++;
inst->B3stateQbd = *states; (*states)++;
inst->B3stateQbs = *states; (*states)++;
```

#### **4.2 State Vector Access**

During simulation, charge values are stored and retrieved:
```
/* Store charge at time t_n */
*(ckt->CKTstate0 + inst->B3stateQgs) = Q_gs_n;

/* Retrieve charge at previous time t_{n-1} */
Q_gs_old = *(ckt->CKTstate1 + inst->B3stateQgs);
```
Where `CKTstate0` is the current state vector and `CKTstate1`, `CKTstate2`, etc., are past states for multi-step integration methods.

### **5. Convergence Analysis**

This section analyzes the numerical properties of the BSIM3 transient implementation, focusing on stability and compatibility with SPICE's time-domain solver.

#### **5.1 Charge Conservation and Numerical Stability**

The charge-based formulation is fundamental to numerical stability in transient simulation.

*   **Conservation Law:** By computing terminal charges `Q_i` and defining currents as `I_i = dQ_i/dt + I_cond,i`, the model inherently satisfies Kirchhoff's Current Law (KCL) in integral form: `∫(∑I_i)dt = ∑Q_i = 0`. This prevents the accumulation of numerical charge error, a common issue in capacitance-based models.
*   **Reciprocal Capacitance Matrix:** The computation of capacitances as `C_ij = ∂Q_i/∂V_j` guarantees `C_ij = C_ji`. This symmetry is a consequence of charge conservation and ensures the capacitance matrix is positive semi-definite, leading to a stable numerical integration.
*   **Smooth Charge Functions:** The functions `f_qgs()`, `f_qgd()`, etc., are designed with smooth derivatives across all operating regions (accumulation, depletion, inversion, linear, saturation). This continuity in `∂Q/∂V` ensures the capacitance values don't jump between Newton iterations, promoting convergence.

#### **5.2 Local Truncation Error and Time-Step Control**

The LTE estimation algorithm ensures the simulation maintains a user-defined accuracy bound.

*   **Error Bound:** The LTE calculation `LTE ≈ |h³/12 * d³Q/dt³|` provides an estimate of the local error per step for the trapezoidal rule. SPICE's `CKTtrtol` parameter (default 7) sets the acceptable error tolerance. The normalization `LTE_norm = LTE/(TOL*|Q| + EPS)` creates a relative error measure.
*   **Adaptive Time-Stepping:** The step control logic `h_new = h_old / (LTE_norm)^{1/4}` reduces the step aggressively when error is large (since `LTE ∝ h³`). This adaptive control allows large steps during slowly changing regions and small steps during fast transients, optimizing simulation speed while maintaining accuracy.
*   **Charge History Management:** The LTE calculation requires charge values from two previous time points (`Q_{n-1}`, `Q_{n-2}`). The state vector mechanism (`CKTstate1`, `CKTstate2`) reliably maintains this history even when the time step changes or steps are rejected.

#### **5.3 Newton-Raphson Convergence in Transient Analysis**

Each time step in transient analysis requires solving a nonlinear algebraic equation via Newton-Raphson (NR) iteration. The BSIM3 implementation includes specific features to ensure NR convergence.

*   **Voltage Limiting (`DEVfetlim`):** The hyperbolic limiting function prevents the NR update from making excessively large voltage jumps. This is crucial when crossing between regions with very different derivatives (e.g., from subthreshold to strong inversion where `g_m` changes by orders of magnitude). By controlling the voltage step, the algorithm remains in the region where the linearization is valid.
*   **Continuous Derivatives:** The BSIM3 core equations for current and charge are designed with smooth blending functions (using `tanh` or smooth polynomials) to ensure `C¹` continuity (continuous first derivatives). This means the Jacobian matrix (containing `g_m`, `g_ds`, `C_ij`) changes continuously with voltage, satisfying the fundamental requirement for Newton's method to converge quadratically.
*   **Source-Drain Symmetry Handling:** The terminal swapping for `V_ds < 0` ensures the internal device equations always see positive `V_ds`. This maintains the continuity of model evaluation and prevents derivative discontinuities that would occur at `V_ds = 0` if separate equations were used for positive and negative drain bias.

#### **5.4 Initial Condition Consistency**

The initial condition calculation in `B3getic()` ensures the transient simulation starts from a consistent state.

*   **DC Consistency:** The initial currents and charges are computed from the initial voltages using the same core equations as the DC model. This guarantees that at `t=0`, the device is in a valid DC operating point, preventing initial convergence problems.
*   **Charge Initialization:** The initial charges `Q_gs(0)`, `Q_gd(0)`, etc., are computed and stored in the state vector. This provides proper initial history for the integration method, avoiding startup transients caused by assuming zero initial charge.
*   **Operating Region Detection:** The function determines if the device starts in cutoff, linear, or saturation based on `V_gs` and `V_ds`. This ensures the appropriate set of smooth blending functions is activated from the first time step.

#### **5.5 Integration with SPICE's Solver Framework**

The BSIM3 transient implementation follows SPICE's standard device interface, ensuring proper interaction with the overall simulation kernel.

*   **State Vector Allocation:** The `B3setup()` function requests the correct number of state entries (5 for charges) via the `states` pointer. This allows SPICE to manage memory for the device's history transparently.
*   **Matrix Stamp for Transient Analysis:** During transient analysis, the load function (in `b3ld.c`) stamps both conductive (`g_m`, `g_ds`) and capacitive (`C_ij/h`) terms into the circuit matrix. The capacitive terms arise from the discretization of `I = dQ/dt`. For the trapezoidal rule, the companion model for a capacitor `C` is a conductance `2C/h` in parallel with a current source.
*   **Error Control Integration:** The `B3trunc()` function returns a suggested time step to SPICE's global time-step controller. The controller takes the minimum step across all devices and nonlinearities in the circuit, ensuring global accuracy.

#### **5.6 Numerical Safeguards and Robustness**

Several numerical safeguards are implemented to handle edge cases and ensure robust simulation.

*   **Minimum Charge in LTE:** The LTE normalization uses `max(|Q|, Q_min)` where `Q_min` might be `inst->B3cgsteff` (effective gate capacitance). This prevents division by zero when charges are very small (e.g., in cutoff).
*   **Time Step Bounds:** The suggested step `h_new` is constrained by SPICE's minimum and maximum time-step limits (`CKTminStep`, `CKTmaxStep`).
*   **Convergence Test Tolerances:** The `B3convTest()` function uses SPICE's standard relative and absolute tolerances (`CKTreltol`, `CKTabstol`). The voltage test uses `|ΔV| < reltol*max(|V|, vntol) + abstol`, which provides appropriate scaling for both large and small signals.

In summary, the BSIM3 transient implementation provides a numerically robust, charge-conserving model that integrates seamlessly with SPICE's adaptive time-step control and Newton-Raphson solver. The use of smooth functions, voltage limiting, and proper initial condition handling ensures reliable convergence across all operating conditions, from deep subthreshold to strong inversion, and from linear to saturation regions.

---

## **C Implementation**

### **1. Core Data Structures for Transient Analysis**

The BSIM3 implementation extends its core data structures to support transient analysis through charge storage and state management.

#### **Transient-Specific Instance Fields**
```c
/* From bsim3def.h - Extended B3instance structure */
typedef struct sB3instance {
    /* ... DC and AC fields omitted for brevity ... */
    
    /* Charge storage for transient analysis */
    double B3qgs;               /* Gate-source charge (C) */
    double B3qgd;               /* Gate-drain charge (C) */
    double B3qgb;               /* Gate-bulk charge (C) */
    double B3qbd;               /* Bulk-drain charge (C) */
    double B3qbs;               /* Bulk-source charge (C) */
    
    /* Historical charge values for LTE calculation */
    double B3qgs_old;           /* Qgs at previous time point */
    double B3qgs_older;         /* Qgs at time point before previous */
    double B3qgd_old;           /* Qgd at previous time point */
    double B3qgd_older;         /* Qgd at time point before previous */
    double B3ddq_old;           /* Second derivative of charge */
    
    /* State vector indices for SPICE's state management */
    int B3stateQgs;             /* Index for Qgs in CKTstate array */
    int B3stateQgd;             /* Index for Qgd in CKTstate array */
    int B3stateQgb;             /* Index for Qgb in CKTstate array */
    int B3stateQbd;             /* Index for Qbd in CKTstate array */
    int B3stateQbs;             /* Index for Qbs in CKTstate array */
    
    /* Historical voltage values for convergence testing */
    double B3vgs_old;           /* Vgs at previous Newton iteration */
    double B3vds_old;           /* Vds at previous Newton iteration */
    double B3vbs_old;           /* Vbs at previous Newton iteration */
    double B3id_old;            /* Id at previous Newton iteration */
    
    /* Initial condition flags */
    int B3icVGSgiven;           /* TRUE if initial VGS specified */
    int B3icVDSgiven;           /* TRUE if initial VDS specified */
    int B3icVBSgiven;           /* TRUE if initial VBS specified */
    double B3icVGS;             /* Specified initial VGS */
    double B3icVDS;             /* Specified initial VDS */
    double B3icVBS;             /* Specified initial VBS */
} B3instance;
```

**Mathematical Mapping:** The `B3qgs`, `B3qgd`, `B3qgb`, `B3qbd`, and `B3qbs` fields store the terminal charges \(Q_{gs}\), \(Q_{gd}\), \(Q_{gb}\), \(Q_{bd}\), and \(Q_{bs}\) calculated from the BSIM3 charge model. These charges are used to compute displacement currents \(I = dQ/dt\) during transient analysis.

### **2. Local Truncation Error Calculation (`b3trunc.c`)**

The `B3trunc()` function implements the LTE estimation algorithm that controls adaptive time-stepping in SPICE.

#### **LTE Calculation Implementation**
```c
double B3trunc(GENmodel *genmodel, CKTcircuit *ckt, double *tiStep) {
    B3model *model = (B3model *)genmodel;
    B3instance *inst;
    double charge, dcharge, ddcharge, dddcharge;
    double LTE, LTEnew, minStep, tol;
    
    minStep = ckt->CKTmaxStep;
    tol = ckt->CKTtrtol;
    
    for (; model != NULL; model = model->B3nextModel) {
        for (inst = model->B3instances; inst != NULL; 
             inst = inst->B3nextInstance) {
            
            /* Calculate total gate charge */
            charge = *(ckt->CKTrhsOld + inst->B3stateQgs)
                   + *(ckt->CKTrhsOld + inst->B3stateQgd)
                   + *(ckt->CKTrhsOld + inst->B3stateQgb);
            
            /* First derivative (current) using backward difference */
            dcharge = (charge - inst->B3qgs_old) / ckt->CKTdeltaOld[0];
            
            /* Second derivative using three-point formula */
            double diff1 = (charge - inst->B3qgs_old) / ckt->CKTdeltaOld[0];
            double diff2 = (inst->B3qgs_old - inst->B3qgs_older) / ckt->CKTdeltaOld[1];
            ddcharge = (diff1 - diff2) / (0.5 * (ckt->CKTdeltaOld[0] 
                                               + ckt->CKTdeltaOld[1]));
            
            /* Third derivative estimate */
            dddcharge = (ddcharge - inst->B3ddq_old) / ckt->CKTdeltaOld[0];
            
            /* LTE formula for backward Euler: LTE = (h²/2) * d²q/dt² */
            /* For Gear method: LTE = (h³/12) * d³q/dt³ */
            LTE = fabs(ckt->CKTdeltaOld[0] * ckt->CKTdeltaOld[0] 
                     * ckt->CKTdeltaOld[0] * dddcharge / 12.0);
            
            /* Normalize by charge tolerance */
            double chargetol = tol * MAX(fabs(charge), inst->B3cgsteff) 
                             + ckt->CKTvoltTol;
            LTEnew = LTE / chargetol;
            
            /* Adjust time step if LTE exceeds tolerance */
            if (LTEnew > 1.0) {
                /* Reduce step by square root of error ratio */
                double reduction = sqrt(sqrt(LTEnew));
                minStep = MIN(minStep, ckt->CKTdeltaOld[0] / reduction);
            }
            
            /* Store historical values for next LTE calculation */
            inst->B3qgs_older = inst->B3qgs_old;
            inst->B3qgs_old = charge;
            inst->B3ddq_old = ddcharge;
            
            /* Repeat LTE calculation for other charges */
        }
    }
    
    *tiStep = MIN(minStep, ckt->CKTmaxStep);
    return OK;
}
```

**Mathematical Mapping:** This implements the LTE formulas:
- Backward Euler: \(\epsilon_{LTE} = \frac{h^2}{2} \cdot \frac{d^2q}{dt^2}\)
- Gear method (2nd order): \(\epsilon_{LTE} = \frac{h^3}{12} \cdot \frac{d^3q}{dt^3}\)
- Time-step control: \(h_{new} = h_{old} / \sqrt[4]{\epsilon_{LTE}/TOL}\)

### **3. Convergence Testing (`b3cvtest.c`)**

The `B3convTest()` function checks if the Newton-Raphson iteration has converged for the BSIM3 device.

#### **Convergence Test Implementation**
```c
int B3convTest(GENmodel *genmodel, CKTcircuit *ckt) {
    B3model *model = (B3model *)genmodel;
    B3instance *inst;
    double vgs, vds, vbs, vgd, vbd;
    double delvgs, delvds, delvbs, delvgd, delvbd;
    double cgs, cgd, cgb, cbd, cbs;
    double tolV, tolC, tolI, reltol, abstol, vntol;
    int converged;
    
    reltol = ckt->CKTreltol;      /* Relative tolerance (typically 0.001) */
    abstol = ckt->CKTabstol;      /* Absolute tolerance (typically 1e-12) */
    vntol = ckt->CKTvoltTol;      /* Voltage noise floor (typically 1e-6) */
    
    converged = 1;  /* Assume convergence until proven otherwise */
    
    for (; model != NULL; model = model->B3nextModel) {
        for (inst = model->B3instances; inst != NULL; 
             inst = inst->B3nextInstance) {
            
            /* Get current terminal voltages */
            vgs = ckt->CKTrhs[inst->B3gNode] - ckt->CKTrhs[inst->B3sNode];
            vds = ckt->CKTrhs[inst->B3dNode] - ckt->CKTrhs[inst->B3sNode];
            vbs = ckt->CKTrhs[inst->B3bNode] - ckt->CKTrhs[inst->B3sNode];
            vgd = vgs - vds;
            vbd = vbs - vds;
            
            /* Calculate voltage changes from previous iteration */
            delvgs = vgs - inst->B3vgs_old;
            delvds = vds - inst->B3vds_old;
            delvbs = vbs - inst->B3vbs_old;
            delvgd = delvgs - delvds;
            delvbd = delvbs - delvds;
            
            /* Voltage convergence test */
            tolV = reltol * MAX(fabs(vgs), vntol) + abstol;
            if (fabs(delvgs) > tolV) {
                converged = 0;
                /* Optional: store which variable failed */
                inst->B3convFail = 1;
            }
            
            tolV = reltol * MAX(fabs(vds), vntol) + abstol;
            if (fabs(delvds) > tolV) {
                converged = 0;
                inst->B3convFail = 2;
            }
            
            tolV = reltol * MAX(fabs(vbs), vntol) + abstol;
            if (fabs(delvbs) > tolV) {
                converged = 0;
                inst->B3convFail = 3;
            }
            
            /* Charge convergence test */
            cgs = inst->B3cgs;
            cgd = inst->B3cgd;
            cgb = inst->B3cgb;
            cbd = inst->B3cbd;
            cbs = inst->B3cbs;
            
            /* Charge change = capacitance * voltage change */
            tolC = reltol * cgs * MAX(fabs(vgs), vntol) + abstol;
            if (fabs(delvgs * cgs) > tolC) {
                converged = 0;
                inst->B3convFail = 4;
            }
            
            tolC = reltol * cgd * MAX(fabs(vgd), vntol) + abstol;
            if (fabs(delvgd * cgd) > tolC) {
                converged = 0;
                inst->B3convFail = 5;
            }
            
            /* Current convergence test */
            double Id = inst->B3id;
            double delId = Id - inst->B3id_old;
            
            tolI = reltol * MAX(fabs(Id), abstol) + abstol;
            if (fabs(delId) > tolI) {
                converged = 0;
                inst->B3convFail = 6;
            }
            
            /* Store current values for next convergence test */
            inst->B3vgs_old = vgs;
            inst->B3vds_old = vds;
            inst->B3vbs_old = vbs;
            inst->B3id_old = Id;
            
            /* Reset convergence failure flag if converged */
            if (converged) {
                inst->B3convFail = 0;
            }
        }
    }
    
    return converged;
}
```

**Mathematical Mapping:** This implements SPICE's convergence criteria:
- Voltage: \(|\Delta V| < \epsilon_{rel} \cdot \max(|V|, V_{ntol}) + \epsilon_{abs}\)
- Charge: \(|\Delta Q| = |C \cdot \Delta V| < \epsilon_{rel} \cdot C \cdot \max(|V|, V_{ntol}) + \epsilon_{abs}\)
- Current: \(|\Delta I| < \epsilon_{rel} \cdot \max(|I|, \epsilon_{abs}) + \epsilon_{abs}\)

### **4. Initial Condition Calculation (`b3getic.c`)**

The `B3getic()` function sets up initial conditions for transient analysis.

#### **Initial Condition Implementation**
```c
void B3getic(GENmodel *genmodel, CKTcircuit *ckt) {
    B3model *model = (B3model *)genmodel;
    B3instance *inst;
    double vgs, vds, vbs, vth, vgst, vdssat;
    
    for (; model != NULL; model = model->B3nextModel) {
        for (inst = model->B3instances; inst != NULL; 
             inst = inst->B3nextInstance) {
            
            /* Use specified IC values or node voltages */
            if (inst->B3icVGSgiven) {
                vgs = inst->B3icVGS;
            } else {
                vgs = ckt->CKTrhs[inst->B3gNode] 
                    - ckt->CKTrhs[inst->B3sNode];
            }
            
            if (inst->B3icVDSgiven) {
                vds = inst->B3icVDS;
            } else {
                vds = ckt->CKTrhs[inst->B3dNode] 
                    - ckt->CKTrhs[inst->B3sNode];
            }
            
            if (inst->B3icVBSgiven) {
                vbs = inst->B3icVBS;
            } else {
                vbs = ckt->CKTrhs[inst->B3bNode] 
                    - ckt->CKTrhs[inst->B3sNode];
            }
            
            /* Calculate threshold voltage */
            vth = B3vthCalc(model, inst, vbs, vds, model->B3phi);
            vgst = vgs - vth;
            
            /* Determine initial operating region */
            if (vgst <= 0.0) {
                /* Cutoff region */
                inst->B3mode = 0;
                inst->B3id = 0.0;
                inst->B3gm = 0.0;
                inst->B3gds = 0.0;
                inst->B3gmbs = 0.0;
            } else {
                /* Calculate saturation voltage */
                double Abulk = model->B3a0 / (1.0 + model->B3ags * vgst);
                vdssat = vgst / Abulk;
                
                if (vds < vdssat) {
                    /* Linear region */
                    inst->B3mode = 1;
                } else {
                    /* Saturation region */
                    inst->B3mode = 2;
                }
                
                /* Calculate initial drain current */
                inst->B3id = B3IdCalc(model, inst, vgs, vds, vbs);
                
                /* Calculate small-signal parameters */
                B3calcSmallSignal(model, inst, vgs, vds, vbs);
            }
            
            /* Calculate initial charges */
            inst->B3qgs = B3qgsCalc(model, inst, vgs, vds, vbs);
            inst->B3qgd = B3qgdCalc(model, inst, vgs, vds, vbs);
            inst->B3qgb = B3qgbCalc(model, inst, vgs, vds, vbs);
            inst->B3qbd = B3qbdCalc(model, inst, vbs, vds);
            inst->B3qbs = B3qbsCalc(model, inst, vbs);
            
            /* Store in SPICE's state vector */
            if (inst->B3stateQgs >= 0) {
                *(ckt->CKTrhsOld + inst->B3stateQgs) = inst->B3qgs;
            }
            if (inst->B3stateQgd >= 0) {
                *(ckt->CKTrhsOld + inst->B3stateQgd) = inst->B3qgd;
            }
            if (inst->B3stateQgb >= 0) {
                *(ckt->CKTrhsOld + inst->B3stateQgb) = inst->B3qgb;
            }
            if (inst->B3stateQbd >= 0) {
                *(ckt->CKTrhsOld + inst->B3stateQbd) = inst->B3qbd;
            }
            if (inst->B3stateQbs >= 0) {
                *(ckt->CKTrhsOld + inst->B3stateQbs) = inst->B3qbs;
            }
            
            /* Initialize historical values */
            inst->B3qgs_old = inst->B3qgs;
            inst->B3qgd_old = inst->B3qgd;
            inst->B3qgb_old = inst->B3qgb;
            inst->B3qbd_old = inst->B3qbd;
            inst->B3qbs_old = inst->B3qbs;
            
            inst->B3qgs_older = inst->B3qgs;
            inst->B3qgd_older = inst->B3qgd;
            
            inst->B3vgs_old = vgs;
            inst->B3vds_old = vds;
            inst->B3vbs_old = vbs;
            inst->B3id_old = inst->B3id;
            
            inst->B3ddq_old = 0.0;
        }
    }
}
```

**Mathematical Mapping:** This sets up the initial conditions for:
- Terminal voltages: \(V_{GS}(t=0)\), \(V_{DS}(t=0)\), \(V_{BS}(t=0)\)
- Operating region: cutoff, linear, or saturation
- Initial current: \(I_D(t=0)\) from BSIM3 equations
- Initial charges: \(Q_{gs}(t=0)\), \(Q_{gd}(t=0)\), etc.

### **5. Integration with SPICE Transient Analysis**

The BSIM3 model integrates with Ngspice's transient analysis through the device operations structure.

#### **Device Operations for Transient Analysis**
```c
SPICEdev B3info = {
    .DEVpublic = {
        .name = "BSIM3",
        .description