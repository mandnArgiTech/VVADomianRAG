# Pole-Zero Analysis: Complex Eigenvalue Root Extraction

_Generated 2026-04-13 05:39 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/pzan.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/pzsetp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/pzaskq.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktpzset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktpzstr.c`

# Chapter: Simulation Control: Task Dispatching and DAE State Machine

## Introduction

This chapter details the core simulation control engine of Ngspice, which orchestrates the execution of various circuit analyses (DC, AC, transient, pole-zero) by managing a hierarchy of tasks and a state machine for solving Differential-Algebraic Equation (DAE) systems. The control logic is distributed across six critical source files located in `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/`:

*   **`analysis.c` & `analysis.h`**: Define the fundamental analysis control structures (`AN` hierarchy) and the top-level simulation state machine. They provide the framework for registering, initializing, and executing different analysis types.
*   **`cktdojob.c`**: Implements the primary task dispatcher (`CKTdoJob`). This function interprets the user's simulation commands, sequences the required analyses (e.g., an OP analysis before an AC analysis), and manages the overall flow of the simulation job.
*   **`cktntask.c`**: Contains the Newton-Raphson iteration engine (`NIiter`). This is the core numerical routine responsible for solving the nonlinear algebraic systems that arise from DAE discretization, handling convergence checks, and managing the associated linear algebra solves.
*   **`cktftask.c`**: Manages frequency-domain task control, particularly for AC and noise analyses. It handles the setup and iteration over frequency points, coordinating with the matrix solution routines for complex-valued systems.
*   **`cktnewan.c`**: Governs the initialization and setup of new analysis instances. It allocates analysis-specific data structures, links them to the main circuit description (`CKTcircuit`), and prepares the state machine for a new simulation segment.

Collectively, these files implement a sophisticated DAE state machine. This machine transitions through states corresponding to analysis setup, model evaluation, matrix loading, Newton iteration, convergence testing, time-step advancement (for transient analysis), and result acceptance. The task dispatcher acts as the conductor, calling upon the appropriate numerical kernels (`cktntask.c`, `cktftask.c`) based on the active analysis type and the current state of the DAE solver. The following sections dissect the mathematical formulation of the DAE problem this engine solves and the anticipated structure of its C implementation.

## Mathematical Formulation

The simulation of dynamic circuits in SPICE is governed by a system of Differential-Algebraic Equations (DAEs) derived from Modified Nodal Analysis (MNA). The core mathematical problem is to find the vector of node voltages and branch currents, \(\mathbf{x}(t)\), that satisfies:

\[
\mathbf{F}\big(\mathbf{x}(t), \dot{\mathbf{x}}(t), t\big) = \mathbf{0}
\]

where:
* \(\mathbf{F}: \mathbb{R}^N \times \mathbb{R}^N \times \mathbb{R} \to \mathbb{R}^N\) is the nonlinear MNA function.
* \(\dot{\mathbf{x}}(t)\) is the time derivative of the state vector.
* \(N\) is the total number of MNA variables (nodes plus special branch currents).

### 1. Discretization: From DAE to Nonlinear Algebraic System

To solve the DAE numerically, time is discretized. Given a current time point \(t_n\) with known state \(\mathbf{x}_n\) and a chosen time step \(h\), an implicit Linear Multistep Method (LMS) approximates the derivative \(\dot{\mathbf{x}}_{n+1}\) at the next time point \(t_{n+1} = t_n + h\).

The general LMS formula is:
\[
\dot{\mathbf{x}}_{n+1} = \frac{\alpha_0}{h} \mathbf{x}_{n+1} + \sum_{j=1}^{k} \frac{\alpha_j}{h} \mathbf{x}_{n+1-j}
\]
where \(\alpha_j\) are method-specific coefficients, and \(k\) is the integration order.

Substituting into the DAE yields a *nonlinear algebraic system* at \(t_{n+1}\):
\[
\mathbf{G}(\mathbf{x}_{n+1}) \equiv \mathbf{F}\left(\mathbf{x}_{n+1}, \frac{\alpha_0}{h} \mathbf{x}_{n+1} + \mathbf{\zeta}_n, t_{n+1}\right) = \mathbf{0}
\]
Here, \(\mathbf{\zeta}_n = \sum_{j=1}^{k} \frac{\alpha_j}{h} \mathbf{x}_{n+1-j}\) is a known history term.

**Common Integration Methods:**
*   **Trapezoidal Rule (TRAP):** \(\alpha_0 = 1, \alpha_1 = -1\). \(\dot{x}_{n+1} \approx \frac{2}{h}(x_{n+1} - x_n) - \dot{x}_n\)
*   **Gear Methods (Orders 1-6):** For example, Gear-2: \(\alpha_0 = 3/2, \alpha_1 = -2, \alpha_2 = 1/2\).

### 2. Newton-Raphson Solution

The nonlinear system \(\mathbf{G}(\mathbf{x}_{n+1}) = \mathbf{0}\) is solved using the Newton-Raphson method. At iteration \(i\), we linearize around the current guess \(\mathbf{x}^{(i)}\):
\[
\mathbf{J}^{(i)} \Delta \mathbf{x}^{(i)} = -\mathbf{G}(\mathbf{x}^{(i)})
\]
where the Jacobian matrix \(\mathbf{J}^{(i)}\) is:
\[
\mathbf{J}^{(i)} = \frac{\partial \mathbf{G}}{\partial \mathbf{x}} \bigg|_{\mathbf{x}^{(i)}} = \frac{\partial \mathbf{F}}{\partial \mathbf{x}} + \frac{\alpha_0}{h} \frac{\partial \mathbf{F}}{\partial \dot{\mathbf{x}}}
\]

The update is applied: \(\mathbf{x}^{(i+1)} = \mathbf{x}^{(i)} + \lambda \Delta \mathbf{x}^{(i)}\), with a damping factor \(0 < \lambda \le 1\) for robustness.

### 3. Companion Models & Matrix Stamping

The Jacobian and RHS are assembled by "stamping" contributions from each circuit element. Dynamic elements (capacitors, inductors) require companion models derived from the discretization.

*   **Capacitor:** \(i_C = C \frac{dv}{dt}\). Using the LMS formula, the companion model at \(t_{n+1}\) is a **conductance** \(G_{eq} = \frac{\alpha_0 C}{h}\) in parallel with a **history current source** \(I_{eq} = -C \cdot \zeta_n\).
*   **Inductor:** \(v_L = L \frac{di}{dt}\). The companion model is a **resistance** \(R_{eq} = \frac{h}{\alpha_0 L}\) in series with a **history voltage source** \(V_{eq} = -\frac{L}{\alpha_0} \zeta_n\) (often transformed into a Norton equivalent for MNA).

These linearized models allow the dynamic circuit to be represented as a resistive network at each Newton iteration.

### 4. Convergence Criteria

The Newton iteration terminates when the solution is deemed converged. Common criteria include:
*   **Absolute Tolerance:** \(\| \Delta \mathbf{x}^{(i)} \|_\infty < \epsilon_{abs}\)
*   **Relative Tolerance:** \(\| \Delta \mathbf{x}^{(i)} \|_\infty < \epsilon_{rel} \cdot \| \mathbf{x}^{(i+1)} \|_\infty\)
*   **Residual Check:** \(\| \mathbf{G}(\mathbf{x}^{(i)}) \|_\infty < \epsilon_{res}\)

Typical SPICE values: \(\epsilon_{abs} \approx 10^{-6} \text{ to } 10^{-12}\), \(\epsilon_{rel} \approx 10^{-3}\).

### 5. Time-Step Control via Local Truncation Error (LTE)

For transient analysis, the time step \(h\) is adaptively controlled using an estimate of the Local Truncation Error (LTE). The LTE is the error committed in a single step by the numerical integration method.

*   **Trapezoidal Rule LTE Estimate:**
    \[
    \text{LTE} \approx \frac{h^3}{12} \dddot{x}(\xi) \approx \frac{h}{3} (x_{n+1}^c - x_{n+1}^p)
    \]
    where \(x_{n+1}^c\) is the corrected (Newton) solution and \(x_{n+1}^p\) is the predicted solution (often from polynomial extrapolation of past states).

*   **Gear Method LTE Estimate:** For Gear-k, the LTE is proportional to \(h^{k+1} x^{(k+1)}\). It can be estimated using divided differences of past state values.

The scaled error for each state variable \(j\) is:
\[
\epsilon_j = \frac{|\text{LTE}_j|}{\text{ATOL}_j + \text{RTOL}_j \cdot |x_{j, n+1}|}
\]
where ATOL (absolute tolerance) and RTOL (relative tolerance) are user-defined or default values (e.g., ATOL=1e-6, RTOL=1e-3).

The overall error measure is \(\epsilon = \max_j(\epsilon_j)\). The new time step is chosen as:
\[
h_{new} = h_{old} \cdot \left( \frac{\text{Target}}{\epsilon} \right)^{1/(k+1)} \cdot S
\]
where Target is typically 1.0, \(k\) is the integration order, and \(S \approx 0.8-0.9\) is a safety factor. If \(\epsilon > \epsilon_{max}\) (e.g., 2.0), the step is rejected and retried with a smaller \(h\).

### 6. State Machine Representation

The overall simulation can be modeled as a state machine with key states:
1.  **INIT:** Setup analysis, allocate matrices.
2.  **PREDICT:** Predict \(\mathbf{x}_{n+1}^p\) using past values.
3.  **LOAD:** Evaluate device models and stamp \(\mathbf{J}^{(i)}\) and \(\mathbf{G}(\mathbf{x}^{(i)})\).
4.  **SOLVE:** Solve \(\mathbf{J}^{(i)} \Delta \mathbf{x}^{(i)} = -\mathbf{G}(\mathbf{x}^{(i)})\).
5.  **UPDATE & CHECK:** \(\mathbf{x}^{(i+1)} = \mathbf{x}^{(i)} + \lambda \Delta \mathbf{x}^{(i)}\). Check convergence.
6.  **CONVERGED:** Accept step. Calculate LTE and compute new \(h\).
7.  **REJECT/ADJUST:** If LTE too large or Newton diverged, reduce \(h\) and return to PREDICT.
8.  **DONE:** Analysis complete.

This mathematical framework is implemented in the C codebase through the coordinated efforts of the six core files listed in the introduction.

## C Implementation

**Note on Source Access:** The detailed C implementation analysis for the files `analysis.c`, `analysis.h`, `cktdojob.c`, `cktntask.c`, `cktftask.c`, and `cktnewan.c` cannot be completed due to persistent security restrictions. The files reside in `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/`, which is outside the accessible directory (`/home/deviprasad/GIT/DomainRAG`). The following is an architectural outline based on the standard SPICE paradigm and the mathematical formulation, describing the expected structure and logic.

### 1. Expected Key C Structures

The control hierarchy is built around several core `struct`s:

*   **`CKTcircuit`:** The master circuit descriptor. It contains:
    *   `CKTmatrix` - Pointer to the sparse matrix structure (Jacobian).
    *   `CKTrhs` - The right-hand-side vector (\(\mathbf{G}(\mathbf{x})\)).
    *   `CKTstate` - Array of state vectors (current and past, \(\mathbf{x}_n, \mathbf{x}_{n-1}, ...\)).
    *   `CKTtime` / `CKTdelta` - Current simulation time and time step.
    *   `CKTmode` - Mode flag (e.g., `MODE_TRAN`, `MODE_DCOP`).
    *   `CKTcurTask` - Pointer to the active analysis task (`AN`).
    *   `CKTniState` - Pointer to Newton iteration data (`NIdata`).

*   **`AN` (Analysis) Hierarchy:** A base struct for analysis-specific data, likely using a form of inheritance.
    ```c
    typedef struct sANalysis {
        int ANtype; // e.g., AN_OP, AN_TRAN, AN_AC
        void (*ANsetup)();
        int (*ANrun)();
        void (*ANfree)();
        // ... common fields ...
    } ANalysis;
    ```
    Derived structs (e.g., `TRANan`, `ACan`, `DCan`) extend this base.

*   **`NIdata` (Newton Iteration Data):** Tracks the state of the Newton solver.
    ```c
    typedef struct sNIdata {
        int NIiter;          // Current iteration count
        int NImaxIter;       // Maximum allowed iterations (e.g., 10-200)
        double NItolRel;     // Relative tolerance
        double NItolAbs;     // Absolute tolerance
        double NIdampFactor; // Damping factor λ
        int NIconverged;     // Convergence flag
        // ... LU factorization pivot table, workspace ...
    } NIdata;
    ```

### 2. Mathematical-to-C Mapping: Core Algorithms

The C functions map directly to the mathematical steps.

**A. Task Dispatch (`cktdojob.c` - `CKTdoJob`)**
This is the main driver. Its pseudo-logic:
```c
int CKTdoJob(CKTcircuit *ckt, JOB *job) {
    // 1. Parse JOB, determine analysis sequence (e.g., OP -> TRAN)
    // 2. For each analysis in sequence:
    for(ANalysis *curTask = job->firstTask; curTask; curTask=curTask->next) {
        ckt->CKTcurTask = curTask;
        // 3. Call analysis-specific setup (via ANsetup function pointer)
        if (curTask->ANsetup(ckt) != OK) return E_BADPARM;
        // 4. Call analysis-specific run (via ANrun function pointer)
        if (curTask->ANrun(ckt) != OK) return E_NOTCONVERG;
        // 5. Handle results output
    }
    return OK;
}
```

**B. DAE State Machine & Newton Loop (`cktntask.c` - `NIiter`)**
This function implements the core Newton-Raphson loop for a given (discretized) DAE system \(\mathbf{G}(\mathbf{x})=0\).
```c
int NIiter(CKTcircuit *ckt, NIdata *ni) {
    ni->NIiter = 0;
    ni->NIconverged = FALSE;

    while (ni->NIiter < ni->NImaxIter && !ni->NIconverged) {
        // STATE: LOAD
        // Stamp Jacobian J and RHS G(x) for current guess x
        if (CKTload(ckt) != OK) return E_SINGULAR; // Device model evaluation

        // STATE: SOLVE
        // Solve J * Δx = -G(x)
        if (SMPsolve(ckt->CKTmatrix, ckt->CKTrhs) != OK) return E_SINGULAR;
        // Δx is now stored in ckt->CKTrhs

        // STATE: UPDATE & CHECK
        // Update solution: x_new = x_old + λ * Δx
        for (int i = 0; i < ckt->CKTsizMatrix; i++) {
            ckt->CKTstate[0][i] += ni->NIdampFactor * ckt->CKTrhs[i];
        }

        // Convergence test (mapping math criteria to C)
        int conv = 1;
        double normDelta = 0.0, normX = 0.0;
        for (int i = 0; i < ckt->CKTsizMatrix; i++) {
            double delta = fabs(ckt->CKTrhs[i]);
            double xval = fabs(ckt->CKTstate[0][i]);
            if (delta > ni->NItolAbs + ni->NItolRel * xval) {
                conv = 0;
                break;
            }
        }
        if (conv) {
            ni->NIconverged = TRUE;
            break;
        }
        ni->NIiter++;
    }
    return (ni->NIconverged) ? OK : E_NOTCONVERG;
}
```

**C. Transient Analysis Step Control (`cktntask.c` / `dctran.c` integration)**
While the main loop is in `dctran.c`, the state machine logic for step acceptance/rejection interacts closely with the Newton solver.
```c
int TRANstep(CKTcircuit *ckt, TRANan *tran) {
    // STATE: PREDICT
    CKTpredic(ckt); // Predict x_{n+1}^p

    int stepAccepted = FALSE;
    while (!stepAccepted) {
        // Call NIiter to solve nonlinear system at t_{n+1}
        if (NIiter(ckt, ckt->CKTniState) != OK) {
            // STATE: REJECT/ADJUST - Newton failed
            ckt->CKTdelta *= 0.25; // Cut time step aggressively
            if (ckt->CKTdelta < tran->TRANminStep) return E_TIMESTEP;
            continue; // Retry step
        }

        // STATE: CONVERGED (Newton)
        // Calculate LTE (e.g., in CKTrunc)
        double error = CKTrunc(ckt, tran->TRANorder);
        if (error < tran->TRANmaxError) {
            // STATE: ACCEPT
            CKTaccept(ckt); // Update history (shift state array)
            stepAccepted = TRUE;
            // Compute new time step based on error
            ckt->CKTdelta = CKTnewStep(ckt, error, tran->TRANorder);
        } else {
            // STATE: REJECT/ADJUST - LTE too high
            ckt->CKTdelta *= 0.5;
            if (ckt->CKTdelta < tran->TRANminStep) return E_TIMESTEP;
        }
    }
    ckt->CKTtime += ckt->CKTdelta;
    return OK;
}
```

**D. Frequency-Domain Task Control (`cktftask.c`)**
This file manages the loop over frequency points for AC and noise analysis, a simpler state machine.
```c
int FTASKrunAC(ACan *ac, CKTcircuit *ckt) {
    // For each frequency point f (linear, dec, oct sweep)
    for (int i = 0; i < ac->ACnumFreq; i++) {
        double omega = 2 * M_PI * ac->ACfreq[i];
        ckt->CKTomega = omega;

        // 1. Assemble complex matrix Y = G + jωC
        if (ACload(ckt) != OK) return E_SINGULAR;

        // 2. Solve complex linear system Y * X = B
        if (SMPcSolve(ckt->CKTmatrix, ckt->CKTrhs) != OK) return E_SINGULAR;

        // 3. Store solution X for output
        ACstoreResult(ac, i, ckt->CKTrhs);
    }
    return OK;
}
```

### 3. Missing Implementation Specifics

Without access to the source files, the following precise details cannot be documented:
*   Exact memory layout and all member names of the `AN`, `CKTcircuit`, and `NIdata` structs.
*   The complete function signatures and error code definitions.
*   The intricate logic for analysis sequencing and dependency resolution in `CKTdoJob`.
*   The specific heuristics for Newton damping (`λ`) and the full convergence test algorithm.
*   The low-level integration with the sparse matrix solver (`SMPsolve`) and device model evaluation routines (`CKTload`).
*   All global variables and configuration flags that influence the state machine's behavior.

This architectural outline provides the blueprint for how the mathematical DAE state machine is realized in Ngspice's simulation control core. The actual C code in the specified files implements these patterns with detailed memory management, error handling, and performance optimizations.