# MOS1: Transient Control and Convergence Checking

_Generated 2026-04-12 04:04 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1trun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1conv.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos1/mos1ic.c`

# MOS1: Transient Control and Convergence Checking

## Technical Introduction

The MOS1 device model in Ngspice implements a robust, charge-conservative transient analysis framework, ensuring numerical stability and accuracy during time-domain simulation. This framework is distributed across three core C source files, each responsible for a distinct phase of the simulation control loop:

*   **`mos1trun.c`**: Implements the **Local Truncation Error (LTE)** calculation for the device's five internal charge state variables. Using a third-derivative estimation from backward differences, it computes the error incurred by the trapezoidal integration method at each time step. This error metric is the primary driver for Ngspice's adaptive time-step control algorithm, determining when to reduce the step size for accuracy or increase it for efficiency.

*   **`mos1conv.c`**: Houses the **Newton-Raphson convergence testing** logic for the MOS1 device. After each iteration within a time point, this function checks whether changes in terminal voltages, the drain current, and the internal charges have fallen below specified relative and absolute tolerances. It flags convergence failures, which can trigger damping of the Newton updates or, in persistent cases, initiate source-stepping to aid the solver.

*   **`mos1ic.c`**: Manages **initial condition** computation for the device at the start of a transient analysis (`t=0`). It processes three possible data sources: user-specified `.IC` parameters in the netlist, the `OFF` flag, or the DC operating point solution. It determines the initial operating region (cutoff, triode, or saturation), calculates the threshold voltage with body effect, and initializes the charge states using the Meyer capacitance model for the gate and the depletion approximation for the junctions.

Together, these files form the control system for MOS1 transient simulation, bridging the device's nonlinear physics with the numerical solver's requirements for stability, accuracy, and robust convergence.

## Mathematical Formulation

### 1. Local Truncation Error (LTE) for Charge-Conservative Formulation

The MOS1 model uses a charge-conservative formulation where the state variables are charges rather than voltages. For trapezoidal integration with time step \( h \), the local truncation error \( \text{LTE}_q \) for a charge state \( q(t) \) is bounded by:
\[
\text{LTE}_q = \left| \frac{h^3}{12} \cdot q'''(\tau) \right|, \quad \tau \in [t-h, t+h]
\]
where \( q''' \) is the third derivative of charge with respect to time.

Since \( q'''(\tau) \) is not directly available, it is estimated numerically using backward differences on stored charge history at times \( t \), \( t-h \), and \( t-2h \):
1.  Approximate second derivative at \( t \) and \( t-h \):
    \[
    q''(t) \approx \frac{q(t) - 2q(t-h) + q(t-2h)}{h^2}
    \]
    \[
    q''(t-h) \approx \frac{q(t-h) - 2q(t-2h) + q(t-3h)}{h^2}
    \]
2.  Estimate third derivative at \( t \):
    \[
    q'''(t) \approx \frac{q''(t) - 2q''(t-h) + q''(t-2h)}{h}
    \]
    where \( q''(t-2h) \) uses earlier history.

The normalized error ratio for time-step control is:
\[
\varepsilon_q = \frac{\text{LTE}_q}{|q(t)| + \varepsilon_{\text{abs}}}, \quad \varepsilon_{\text{abs}} = 10^{-12}
\]
The overall device error is the maximum across the five charge states \( q_{gs}, q_{gd}, q_{gb}, q_{bd}, q_{bs} \):
\[
\varepsilon = \max(\varepsilon_{q_{gs}}, \varepsilon_{q_{gd}}, \varepsilon_{q_{gb}}, \varepsilon_{q_{bd}}, \varepsilon_{q_{bs}})
\]

### 2. Time-Step Control Algorithm

Given a user-specified transient error tolerance \( \tau_q \) (often derived from `CKTtrtol`), the time step is adapted as follows:
- If \( \varepsilon > \tau_q \): The step fails. The new step is:
  \[
  h_{\text{new}} = 0.9 \cdot h_{\text{current}} \cdot \sqrt{\frac{\tau_q}{\varepsilon}}
  \]
  The factor 0.9 is a safety margin. The step is retried with \( h_{\text{new}} \).
- If \( \varepsilon \leq \tau_q \): The step is accepted. The step for the next point may be increased:
  \[
  h_{\text{next}} = \min\left(2 \cdot h_{\text{current}}, \ 0.9 \cdot h_{\text{current}} \cdot \sqrt{\frac{\tau_q}{\varepsilon}}\right)
  \]
  The factor 2 prevents excessive growth.

A minimum step is enforced to prevent infinite loops:
\[
h_{\min} = 10 \cdot \epsilon_{\text{machine}} \cdot \max(|t|, h_{\text{current}}), \quad \epsilon_{\text{machine}} \approx 2.2 \times 10^{-16}
\]

### 3. Newton-Raphson Convergence Criteria

Convergence is tested simultaneously for voltages, currents, and charges against SPICE tolerances:
- **Voltage Convergence** (for nodes D, G, S, B):
  \[
  |\Delta V| < \text{reltol} \cdot \max(|V|, \text{vntol}) + \text{abstol}_{\text{volt}}
  \]
  where typical defaults are \( \text{reltol} = 0.001 \), \( \text{vntol} = 10^{-6} \), \( \text{abstol}_{\text{volt}} = 10^{-6} \).
- **Current Convergence** (drain current \( I_d \)):
  \[
  |\Delta I_d| < \text{reltol} \cdot \max(|I_d|, \text{abstol}_{\text{current}}) + \text{abstol}_{\text{current}}
  \]
  where \( \text{abstol}_{\text{current}} = 10^{-12} \).
- **Charge Convergence** (for each of the five charges):
  \[
  |\Delta q| < \text{reltol} \cdot \max(|q|, \text{abstol}_{\text{charge}}) + \text{abstol}_{\text{charge}}
  \]
  where \( \text{abstol}_{\text{charge}} = 10^{-12} \).

All criteria must be satisfied for the device to be considered converged.

### 4. Initial Condition Computation

The initial state at \( t=0 \) is determined from one of three sources, in order of priority:
1.  **User-Specified (`IC`)**:
    \[
    V_{DS}(0) = \text{MOS1icVDS}, \quad V_{GS}(0) = \text{MOS1icVGS}, \quad V_{BS}(0) = \text{MOS1icVBS}
    \]
2.  **OFF Flag**: If `MOS1off = 1`, all terminal voltages are set to zero, forcing cutoff mode.
3.  **Circuit DC Solution**: Voltages are taken from `ckt->CKTrhs[]` at the device nodes.

**Operating Region Determination**:
1.  Compute threshold voltage with body effect (for \( V_{SB} \leq 0 \)):
    \[
    V_{th} = \text{VTO} + \gamma \cdot \left( \sqrt{2\phi + V_{SB}} - \sqrt{2\phi} \right)
    \]
    where \( \gamma \) is `MOS1gamma` and \( \phi \) is `MOS1phi`.
2.  Define \( V_{GST} = V_{GS} - V_{th} \).
3.  Determine region:
    - **Cutoff**: If \( V_{GST} \leq 0 \). Set \( I_d = 0 \), \( g_m = g_{ds} = g_{mb} = 0 \).
    - **Saturation**: If \( V_{GST} > 0 \) and \( V_{DS} \geq V_{GST} \).
    - **Triode**: If \( V_{GST} > 0 \) and \( 0 < V_{DS} < V_{GST} \).

**Initial Charge Calculation**:
- **Gate Charges** (Meyer model):
  - **Cutoff**: \( Q_G = C_{ox} \cdot V_{GS} \), partitioned as \( Q_{GS} = Q_G \), \( Q_{GD} = Q_{GB} = 0 \).
  - **Saturation**: \( Q_G = C_{ox} \cdot (V_{GS} - V_{th}) \), partitioned as \( Q_{GS} = \frac{2}{3} Q_G \), \( Q_{GD} = 0 \), \( Q_{GB} = C_{GBO} \cdot L_{eff} \cdot V_{GB} \).
  - **Triode**: \( Q_G = C_{ox} \cdot \left[ V_{GS} - V_{th} - \frac{V_{DS}}{2} \right] \), partitioned equally: \( Q_{GS} = Q_{GD} = \frac{1}{2} Q_G \), \( Q_{GB} = C_{GBO} \cdot L_{eff} \cdot V_{GB} \).
  Overlap capacitances are added: \( Q_{GS} += C_{GSO} \cdot W_{eff} \cdot V_{GS} \), \( Q_{GD} += C_{GDO} \cdot W_{eff} \cdot V_{GD} \).
- **Junction Charges** (Depletion approximation):
  For each junction (BD, BS), with area \( A \), perimeter \( P \), zero-bias capacitance \( C_j \), grading coefficient \( M_j \), and built-in potential \( PB \):
  \[
  Q_j = \begin{cases}
  A \cdot C_j \cdot \frac{PB}{1 - M_j} \left[ 1 - \left(1 - \frac{V}{PB}\right)^{1-M_j} \right] + P \cdot C_{JSW} \cdot \frac{PB_{SW}}{1 - M_{JSW}} \left[ 1 - \left(1 - \frac{V}{PB_{SW}}\right)^{1-M_{JSW}} \right], & V < FC \cdot PB \\
  A \cdot C_j \cdot \left( \frac{1 - (1 - FC)^{1-M_j}}{1 - M_j} + \frac{(1 - FC)^{-M_j}}{PB} \left[ V - FC \cdot PB + \frac{M_j}{2 \cdot PB}(V - FC \cdot PB)^2 \right] \right) + \text{(similar for SW)}, & V \geq FC \cdot PB
  \end{cases}
  \]
  This ensures \( C^1 \) continuity at \( V = FC \cdot PB \).

### 5. Convergence Acceleration and Failure Handling

- **Damping**: On convergence failure, Newton updates are damped: \( \Delta V_{\text{new}} = \alpha \cdot \Delta V \), with \( \alpha \) typically reduced from 1.0 to 0.5, then 0.25.
- **Source Stepping**: For persistent DC convergence failures, the circuit's independent sources are scaled from zero to their full value over several steps.
- **Boundary Smoothing**: A small hysteresis band (\( \sim 0.1 \cdot |V_{GST}| \)) is applied around the \( V_{DS} = V_{GST} \) boundary to prevent oscillating between triode and saturation regions.

## C Implementation

### 1. Local Truncation Error Calculation (`mos1trun.c`)

The `MOS1trunc()` function implements the LTE calculation for adaptive time-step control.

**Key Data Structures and Variables**:
- `CKTcircuit *ckt`: Contains `CKTdelta` (time step \( h \)), `CKTstates[]` (array storing charge history), `CKTstateSize` (stride between time points in the states array).
- `MOS1instance *inst`: Contains state variable indices (`MOS1qgs`, `MOS1qgd`, `MOS1qgb`, `MOS1qbd`, `MOS1qbs`) and the `MOS1trnErr` field to store the calculated error ratio.

**Core Algorithm Implementation**:
```c
int MOS1trunc(GENmodel *inModel, CKTcircuit *ckt, double *timeStep)
{
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    double h = ckt->CKTdelta; // Current time step
    double tol = ckt->CKTtrtol * ckt->CKTabstol + ckt->CKTreltol;
    double maxError = 0.0;

    for (; model != NULL; model = model->MOS1nextModel) {
        for (inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            // Pointers to charge history for q_gs
            double *qgs_hist = ckt->CKTstates + inst->MOS1qgs * ckt->CKTstateSize;
            double qgs_t0 = qgs_hist[0]; // q(t)
            double qgs_t1 = qgs_hist[1]; // q(t-h)
            double qgs_t2 = qgs_hist[2]; // q(t-2h)
            double qgs_t3 = qgs_hist[3]; // q(t-3h)

            // Estimate second derivative at t and t-h
            double qgs_ddot_t0 = (qgs_t0 - 2*qgs_t1 + qgs_t2) / (h*h);
            double qgs_ddot_t1 = (qgs_t1 - 2*qgs_t2 + qgs_t3) / (h*h);

            // Estimate third derivative at t (using q'' at t, t-h, t-2h)
            double qgs_ddot_t2 = (qgs_t2 - 2*qgs_t3 + qgs_hist[4]) / (h*h);
            double qgs_ddot_t = (qgs_ddot_t0 - 2*qgs_ddot_t1 + qgs_ddot_t2) / h;

            // Calculate LTE for q_gs
            double lte_qgs = fabs((h*h*h/12.0) * qgs_ddot_t);
            double err_qgs = lte_qgs / (fabs(qgs_t0) + 1e-12);

            // Repeat for q_gd, q_gb, q_bd, q_bs...
            double err_qgd = ...;
            double err_qgb = ...;
            double err_qbd = ...;
            double err_qbs = ...;

            // Find maximum error for this instance
            double instErr = MAX(err_qgs, MAX(err_qgd, MAX(err_qgb, MAX(err_qbd, err_qbs))));
            inst->MOS1trnErr = instErr;
            maxError = MAX(maxError, instErr);
        }
    }

    // Time-step control logic
    if (maxError > tol) {
        // Step failed, calculate reduction factor
        double factor = 0.9 * sqrt(tol / maxError);
        *timeStep = h * factor;
        // Enforce minimum step
        double minStep = 10.0 * DBL_EPSILON * MAX(fabs(ckt->CKTtime), h);
        if (*timeStep < minStep) *timeStep = minStep;
        return(E_LOCALTRUNC);
    } else {
        // Step accepted, suggest increase for next step
        double factor = 0.9 * sqrt(tol / MAX(maxError, DBL_EPSILON));
        *timeStep = MIN(2.0 * h, h * factor);
        return(OK);
    }
}
```

### 2. Convergence Testing (`mos1conv.c`)

The `MOS1convTest()` function checks if the Newton-Raphson iteration has converged for the MOS1 device.

**Key Variables**:
- `ckt->CKTrhs[]`: Array of node voltages from the current iteration.
- `ckt->CKTdelta[]`: Array of Newton corrections (\( \Delta V \)) for each node.
- `inst->MOS1cd`: Drain current from the current iteration.
- `inst->MOS1cd_prev`: Drain current from the previous iteration.
- `inst->MOS1converged`: Boolean flag indicating if this instance has converged.

**Implementation Logic**:
```c
int MOS1convTest(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;
    double reltol = ckt->CKTreltol;
    double vntol = ckt->CKTvoltTol;
    double abstol_volt = 1e-6;
    double abstol_current = 1e-12;
    double abstol_charge = 1e-12;
    int converged = 1; // Assume convergence unless proven otherwise

    for (; model != NULL; model = model->MOS1nextModel) {
        for (inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            int nodeD = inst->MOS1dNode;
            int nodeS = inst->MOS1sNode;
            int nodeG = inst->MOS1gNode;
            int nodeB = inst->MOS1bNode;

            // Check voltage convergence at Drain node
            double vD = ckt->CKTrhs[nodeD];
            double deltaVD = ckt->CKTdelta[nodeD];
            double tolVD = reltol * MAX(fabs(vD), vntol) + abstol_volt;
            if (fabs(deltaVD) > tolVD) {
                inst->MOS1converged = 0;
                converged = 0;
                continue; // Skip further checks for this instance
            }

            // Repeat for Source, Gate, Bulk nodes...
            // ...

            // Check drain current convergence
            double deltaId = inst->MOS1cd - inst->MOS1cd_prev;
            double tolId = reltol * MAX(fabs(inst->MOS1cd), abstol_current) + abstol_current;
            if (fabs(deltaId) > tolId) {
                inst->MOS1converged = 0;
                converged = 0;
                continue;
            }

            // Check charge convergence (example for q_gs)
            double *qgs_hist = ckt->CKTstates + inst->MOS1qgs * ckt->CKTstateSize;
            double qgs_t0 = qgs_hist[0]; // Current charge
            double qgs_t1 = qgs_hist[1]; // Previous charge
            double deltaQgs = qgs_t0 - qgs_t1;
            double tolQgs = reltol * MAX(fabs(qgs_t0), abstol_charge) + abstol_charge;
            if (fabs(deltaQgs) > tolQgs) {
                inst->MOS1converged = 0;
                converged = 0;
                continue;
            }

            // Repeat for q_gd, q_gb, q_bd, q_bs...

            // If all checks passed
            inst->MOS1converged = 1;
            inst->MOS1cd_prev = inst->MOS1cd; // Update previous current
        }
    }

    if (!converged) {
        ckt->CKTnoncon++; // Increment global non-convergence counter
        // If too many failures, trigger damping or source-stepping
        if (ckt->CKTnoncon > ckt->CKTmaxNoncon) {
            ckt->CKTmode |= MODEDAMPING;
        }
    }
    return(OK);
}
```

### 3. Initial Condition Computation (`mos1ic.c`)

The `MOS1ic()` function sets up the initial state for transient analysis.

**Key Instance Parameters**:
- `MOS1icGiven`: Boolean indicating if user ICs are provided.
- `MOS1icVDS`, `MOS1icVGS`, `MOS1icVBS`: User-specified initial voltages.
- `MOS1off`: Flag to force the device off.
- `MOS1mode`: Operating mode (0=cutoff, 1=triode, 2=saturation).

**Core Implementation**:
```c
int MOS1ic(GENmodel *inModel, CKTcircuit *ckt)
{
    MOS1model *model = (MOS1model*)inModel;
    MOS1instance *inst;

    for (; model != NULL; model = model->MOS1nextModel) {
        for (inst = model->MOS1instances; inst != NULL; inst = inst->MOS1nextInstance) {
            double vds, vgs, vbs;

            // --- Determine Initial Voltages ---
            if (inst->MOS1off) {
                // Case 1: OFF flag set
                vds = vgs = vbs = 0.0;
                inst->MOS1mode = 0; // Cutoff
            } else if (inst->MOS1icGiven) {
                // Case 2: User ICs provided
                vds = inst->MOS1icVDS;
                vgs = inst->MOS1icVGS;
                vbs = inst->MOS1icVBS;
            } else {
                // Case 3: Use circuit DC solution
                int nodeD = inst->MOS1dNode;
                int nodeS = inst->MOS1sNode;
                int nodeG = inst->MOS1gNode;
                int nodeB = inst->MOS1bNode;
                vds = ckt->CKTrhs[nodeD] - ckt->CKTrhs[nodeS];
                vgs = ckt->CKTrhs[nodeG] - ckt->CKTrhs[nodeS];
                vbs = ckt->CKTrhs[nodeB] - ckt->CKTrhs[nodeS];
            }

            // --- Compute Threshold Voltage ---
            double phi = model->MOS1phi;
            double gamma = model->MOS1gamma;
            double vto = model->MOS1vt0;
            double vsb = -vbs; // Source-to-bulk voltage
            double sqrtPhi = sqrt(2.0 * phi);
            double sqrtTerm;
            if ((2.0 * phi + vsb) < 1e-12) {
                sqrtTerm = sqrt(1e-12); // Numerical guard
            } else {
                sqrtTerm = sqrt(2.0 * phi + vsb);
            }
            double vth = vto + gamma * (sqrtTerm - sqrtPhi);

            // --- Determine Operating Region ---
            double vgst = vgs - vth;
            if (vgst <= 0.0) {
                inst->MOS1mode = 0; // Cutoff
                inst->MOS1cd = 0.0;
                inst->MOS1gm = 0.0;
                inst->MOS1gds = 0.0;
                inst->MOS1gmb = 0.0;
            } else if (vds >= vgst) {
                inst->MOS1mode = 2; // Saturation
                // Calculate Id, gm, gds, gmb using saturation formulas...
            } else {
                inst->MOS1mode = 1; // Triode
                // Calculate Id, gm, gds, gmb using triode formulas...
            }

            // --- Initialize Charge States (Meyer Model) ---
            double cox = model->MOS1cox;
            double weff = inst->MOS1effW;
            double leff = inst->MOS1effL;
            double cgso = model->MOS1cgso;
            double cgdo = model->MOS1cgdo;
            double cgbo = model->MOS1cgbo;

            double qgs, qgd, qgb;
            if (inst->MOS1mode == 0) {
                // Cutoff
                qgs = cox * vgs;
                qgd = 0.0;
                qgb = 0.0;
            } else if (inst->MOS1mode == 2) {
                // Saturation
                double qg = cox * vgst;
                qgs = (2.0/3.0) * qg;
                qgd = 0.0;
                qgb = cgbo * leff * (vgs - vbs); // Overlap
            } else {
                // Triode
                double qg = cox * (vgst - vds/2.0);
                qgs = qg / 2.0;
                qgd = qg / 2.0;
                qgb = cgbo * leff * (vgs - vbs); // Overlap
            }
            // Add overlap capacitances
            qgs += cgso * weff * vgs;
            qgd += cgdo * weff * (vgs - vds);

            // Store initial charges in state vector
            double *states = ckt->CKTstate0; // Initial state array
            states[inst->MOS1qgs] = qgs;
            states[inst->MOS1qgd] = qgd;
            states[inst->MOS1qgb] = qgb;

            // Initialize junction charges (q_bd, q_bs) using depletion approximation...
            // ...

            // Copy initial state to current state
            ckt->CKTstates[inst->MOS1qgs] = qgs;
            ckt->CKTstates[inst->MOS1qgd] = qgd;
            // ... etc.
        }
    }
    return(OK);
}
```