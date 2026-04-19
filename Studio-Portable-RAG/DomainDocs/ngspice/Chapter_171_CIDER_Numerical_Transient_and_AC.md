# CIDER Numerical Models: AC Solvers and Transient Time-Stepping

_Generated 2026-04-13 03:18 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjttrun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjttemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2trun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdtrun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdtemp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2trun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2temp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummtrun.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummtemp.c`

# Chapter: CIDER Numerical Models: AC Solvers and Transient Time-Stepping

## Technical Introduction

The CIDER (Circuit and Interconnect Device Emulation and Reliability) numerical models represent Ngspice's most advanced capability for simulating semiconductor devices by directly solving the fundamental physics equations. Unlike compact models that use empirical equations, CIDER models discretize and solve the Poisson and continuity (drift-diffusion) equations on a 1D or 2D mesh, providing detailed insight into internal device behavior while maintaining full compatibility with SPICE circuit simulation.

The implementation is organized across several device-specific file families, each handling distinct aspects of the numerical solution:

**Transient Time-Step Control (`*trun.c` files)**: These files implement the Local Truncation Error (LTE) calculation and adaptive time-stepping algorithms. `nbjttrun.c`, `nbt2trun.c`, `numdtrun.c`, `nud2trun.c`, and `nummtrun.c` contain device-specific implementations of the `DEVtrunc()` function, which monitors the rate of change of internal state variables (electrostatic potential ψ, electron concentration n, hole concentration p) and adjusts the simulation time step to maintain specified error tolerances. They implement the mathematical LTE criteria using Richardson extrapolation and charge conservation verification.

**AC Small-Signal Analysis (`*acld.c` files)**: The files `nbjtacld.c`, `nbt2acld.c`, `numdacld.c`, `nud2acld.c`, and `nummacld.c` implement the `DEVacLoad()` function for frequency-domain analysis. These routines compute the small-signal admittance matrix Y(ω) by linearizing the device equations around the DC operating point using a perturbation method. They handle the complex-valued matrix stamping for the Modified Nodal Analysis (MNA) system, including both conductance (real) and capacitance/susceptance (imaginary) components.

**Temperature Scaling and Parameter Update (`*temp.c` files)**: `nbjttemp.c`, `nbt2temp.c`, `numdtemp.c`, `nud2temp.c`, and `nummtemp.c` implement the `DEVtemperature()` function, which updates all temperature-dependent parameters according to semiconductor physics models. This includes mobility degradation, bandgap narrowing, intrinsic carrier concentration variation, and thermal voltage scaling. These routines ensure accurate simulation across temperature sweeps and self-heating effects.

Collectively, these thirteen files implement the complete AC and transient analysis capability for CIDER numerical devices within Ngspice's SPICE framework. They bridge the gap between detailed semiconductor physics and circuit simulation by providing numerically robust implementations of the discretized PDEs, adaptive time-stepping for stiff systems, and efficient small-signal analysis for frequency-domain characterization.

## 1. Mathematical Formulation

The CIDER numerical models extend Ngspice's capability by solving the fundamental semiconductor device equations directly, coupling them to the circuit via Modified Nodal Analysis (MNA). The mathematical formulation for AC and transient analysis builds upon the DC drift-diffusion framework.

### 1.1 Governing Equations for Time-Domain Analysis

The time-dependent drift-diffusion equations form the core of the transient model:

**Poisson's Equation (Time-Dependent):**
\[
\nabla \cdot (\epsilon \nabla \psi) = -q(p - n + N_d^+ - N_a^-) - \rho_{trapped}
\]
Where \(\psi\) is the electrostatic potential, \(\epsilon\) is the permittivity, \(q\) is electron charge, \(n\) and \(p\) are electron and hole concentrations, \(N_d^+\) and \(N_a^-\) are ionized donor and acceptor concentrations, and \(\rho_{trapped}\) accounts for trapped charges.

**Electron Continuity Equation:**
\[
\frac{\partial n}{\partial t} = \frac{1}{q} \nabla \cdot \mathbf{J}_n - R_n + G_n
\]
with current density:
\[
\mathbf{J}_n = q\mu_n n \mathbf{E} + qD_n \nabla n
\]

**Hole Continuity Equation:**
\[
\frac{\partial p}{\partial t} = -\frac{1}{q} \nabla \cdot \mathbf{J}_p - R_p + G_p
\]
with current density:
\[
\mathbf{J}_p = q\mu_p p \mathbf{E} - qD_p \nabla p
\]

### 1.2 Discretization for Transient Analysis

The finite-difference discretization in time uses backward Euler or trapezoidal methods:

**Backward Euler Discretization:**
\[
\frac{n^{t+\Delta t} - n^t}{\Delta t} = \frac{1}{q} \nabla \cdot \mathbf{J}_n^{t+\Delta t} - R_n^{t+\Delta t} + G_n^{t+\Delta t}
\]

**Trapezoidal (Gear-2) Discretization:**
\[
\frac{1.5n^{t+\Delta t} - 2n^t + 0.5n^{t-\Delta t}}{\Delta t} = \frac{1}{q} \nabla \cdot \mathbf{J}_n^{t+\Delta t} - R_n^{t+\Delta t} + G_n^{t+\Delta t}
\]

### 1.3 Small-Signal AC Formulation

For AC analysis, the system is linearized around the DC operating point. The small-signal equations are derived by perturbing each variable \(x = X_{DC} + \tilde{x}e^{j\omega t}\):

**Linearized Poisson Equation:**
\[
\nabla \cdot (\epsilon \nabla \tilde{\psi}) = -q(\tilde{p} - \tilde{n} + \tilde{N}_d^+ - \tilde{N}_a^-) - j\omega \tilde{\rho}_{capacitive}
\]

**Linearized Continuity Equations:**
\[
j\omega \tilde{n} = \frac{1}{q} \nabla \cdot \tilde{\mathbf{J}}_n - \frac{\partial R_n}{\partial n}\tilde{n} - \frac{\partial R_n}{\partial p}\tilde{p} + \frac{\partial G_n}{\partial \psi}\tilde{\psi}
\]
\[
j\omega \tilde{p} = -\frac{1}{q} \nabla \cdot \tilde{\mathbf{J}}_p - \frac{\partial R_p}{\partial n}\tilde{n} - \frac{\partial R_p}{\partial p}\tilde{p} + \frac{\partial G_p}{\partial \psi}\tilde{\psi}
\]

### 1.4 MNA Coupling Formulation

The device equations are coupled to the circuit through terminal currents. For a device with \(m\) terminals, the terminal current \(I_k\) is computed by integrating the current density over the contact area \(A_k\):

\[
I_k = \int_{A_k} (\mathbf{J}_n + \mathbf{J}_p - \epsilon \frac{\partial \mathbf{E}}{\partial t}) \cdot d\mathbf{A}
\]

The linearized terminal currents for AC analysis become:

\[
\tilde{I}_k = \sum_{l=1}^m Y_{kl}(\omega) \tilde{V}_l
\]

Where \(Y_{kl}(\omega)\) is the small-signal admittance matrix computed from the linearized device equations.

### 1.5 State Vector Representation

The complete system state for transient analysis includes:
- Electrostatic potential \(\psi_i\) at each mesh point \(i\)
- Electron concentration \(n_i\) at each mesh point \(i\)
- Hole concentration \(p_i\) at each mesh point \(i\)
- Terminal voltages \(V_k\)

The state vector for a device with \(N\) mesh points and \(m\) terminals is:

\[
\mathbf{x} = [\psi_1, \ldots, \psi_N, n_1, \ldots, n_N, p_1, \ldots, p_N, V_1, \ldots, V_m]^T
\]

### 1.6 Time Integration Methods

**Trapezoidal Rule (Default):**
\[
\mathbf{x}^{t+\Delta t} = \mathbf{x}^t + \frac{\Delta t}{2} \left( \mathbf{f}(\mathbf{x}^t) + \mathbf{f}(\mathbf{x}^{t+\Delta t}) \right)
\]

**Backward Euler (Stable but less accurate):**
\[
\mathbf{x}^{t+\Delta t} = \mathbf{x}^t + \Delta t \cdot \mathbf{f}(\mathbf{x}^{t+\Delta t})
\]

**Gear Methods (Order 2-6 available):**
\[
\mathbf{x}^{t+\Delta t} = \sum_{k=1}^q \alpha_k \mathbf{x}^{t-(k-1)\Delta t} + \beta_0 \Delta t \mathbf{f}(\mathbf{x}^{t+\Delta t})
\]

## 2. Convergence Analysis

### 2.1 Newton-Raphson Iteration for Transient Analysis

The discretized time-dependent equations form a nonlinear system:

\[
\mathbf{F}(\mathbf{x}^{t+\Delta t}) = \mathbf{A}(\mathbf{x}^{t+\Delta t} - \mathbf{x}^t) - \Delta t \cdot \mathbf{f}(\mathbf{x}^{t+\Delta t}) = 0
\]

The Newton-Raphson iteration at step \(k+1\) is:

\[
\mathbf{J}^{(k)} \Delta \mathbf{x}^{(k)} = -\mathbf{F}(\mathbf{x}^{(k)})
\]
\[
\mathbf{x}^{(k+1)} = \mathbf{x}^{(k)} + \lambda^{(k)} \Delta \mathbf{x}^{(k)}
\]

Where \(\mathbf{J} = \partial \mathbf{F}/\partial \mathbf{x}\) is the Jacobian matrix and \(\lambda^{(k)}\) is a damping factor (typically 0.1-1.0).

### 2.2 Jacobian Matrix Structure

The Jacobian for the coupled system has block structure:

\[
\mathbf{J} = \begin{bmatrix}
\mathbf{J}_{\psi\psi} & \mathbf{J}_{\psi n} & \mathbf{J}_{\psi p} & \mathbf{J}_{\psi V} \\
\mathbf{J}_{n\psi} & \mathbf{J}_{nn} & \mathbf{J}_{np} & \mathbf{J}_{nV} \\
\mathbf{J}_{p\psi} & \mathbf{J}_{pn} & \mathbf{J}_{pp} & \mathbf{J}_{pV} \\
\mathbf{J}_{V\psi} & \mathbf{J}_{Vn} & \mathbf{J}_{Vp} & \mathbf{J}_{VV}
\end{bmatrix}
\]

Where:
- \(\mathbf{J}_{\psi\psi}\): Poisson equation sensitivity to potential
- \(\mathbf{J}_{nn}, \mathbf{J}_{pp}\): Continuity equation self-terms (including \(j\omega\) for AC)
- \(\mathbf{J}_{\psi n}, \mathbf{J}_{\psi p}\): Poisson coupling to carrier concentrations
- \(\mathbf{J}_{n\psi}, \mathbf{J}_{p\psi}\): Continuity equation dependence on potential
- \(\mathbf{J}_{\psi V}, \mathbf{J}_{nV}, \mathbf{J}_{pV}\): Coupling to terminal voltages
- \(\mathbf{J}_{VV}\): Terminal admittance matrix

### 2.3 Convergence Criteria

**Voltage Convergence:**
\[
|\Delta V_k^{(k)}| < \epsilon_V = \text{VNTOL} + \text{RELTOL} \cdot \max(|V_k^{(k)}|, |V_k^{(k-1)}|)
\]
Where VNTOL = \(10^{-6}\) V, RELTOL = \(10^{-3}\).

**Carrier Concentration Convergence:**
\[
|\Delta n_i^{(k)}| < \epsilon_n = \text{ABSTOL} + \text{RELTOL} \cdot \max(|n_i^{(k)}|, |n_i^{(k-1)}|)
\]
\[
|\Delta p_i^{(k)}| < \epsilon_p = \text{ABSTOL} + \text{RELTOL} \cdot \max(|p_i^{(k)}|, |p_i^{(k-1)}|)
\]
Where ABSTOL = \(10^{-12}\) for concentrations.

**Charge Conservation Check:**
\[
\left| \frac{\partial \rho}{\partial t} + \nabla \cdot \mathbf{J} \right| < \text{CHGTOL} = 10^{-14}
\]

### 2.4 Local Truncation Error (LTE) Control

The LTE for the trapezoidal rule is estimated using Richardson extrapolation:

\[
\text{LTE} = \frac{1}{3} |\mathbf{x}_{\Delta t} - \mathbf{x}_{\Delta t/2}|
\]

For each state variable \(x_i\), the normalized error is:

\[
e_i = \frac{\text{LTE}_i}{\text{RELTOL} \cdot |x_i| + \text{ABSTOL}_i}
\]

The time step is adjusted to maintain \(e_i < 1\) for all \(i\):

\[
\Delta t_{\text{new}} = \Delta t_{\text{old}} \cdot \min\left(0.9 \cdot \max_i(e_i)^{-1/2}, 2.0\right)
\]

### 2.5 AC Analysis Convergence

For frequency-domain analysis, convergence is monitored through:

**Admittance Matrix Convergence:**
\[
\| \mathbf{Y}^{(k)}(\omega) - \mathbf{Y}^{(k-1)}(\omega) \|_F < \epsilon_Y \cdot \| \mathbf{Y}^{(k)}(\omega) \|_F
\]
Where \(\epsilon_Y = 10^{-4}\) and \(\|\cdot\|_F\) is the Frobenius norm.

**Phase Accuracy Criterion:**
\[
|\angle Y_{kl}^{(k)}(\omega) - \angle Y_{kl}^{(k-1)}(\omega)| < 0.1^\circ
\]

### 2.6 Numerical Stability Conditions

**Dielectric Relaxation Time Limit:**
\[
\Delta t < \tau_d = \frac{\epsilon}{\sigma} = \frac{\epsilon}{q(\mu_n n + \mu_p p)}
\]

**Carrier Diffusion Time Limit:**
\[
\Delta t < \tau_{\text{diff}} = \frac{(\Delta x)^2}{2D_{\max}}
\]
Where \(D_{\max} = \max(\mu_n, \mu_p) \cdot V_t\) and \(\Delta x\) is the minimum mesh spacing.

**Debye Length Resolution:**
\[
\Delta x < L_D = \sqrt{\frac{\epsilon V_t}{q \max(|n-p+N_d-N_a|)}}
\]

### 2.7 Gummel-Scharfetter Iteration Scheme

For highly nonlinear problems, the decoupled Gummel iteration is used:

1. **Poisson Step:** Solve \(\nabla \cdot (\epsilon \nabla \psi) = -q(p^{(k)} - n^{(k)} + N_d - N_a)\)
2. **Electron Continuity:** Solve \(\frac{\partial n}{\partial t} = \frac{1}{q} \nabla \cdot \mathbf{J}_n(\psi^{(k+1)}, n^{(k+1)}, p^{(k)}) - R + G\)
3. **Hole Continuity:** Solve \(\frac{\partial p}{\partial t} = -\frac{1}{q} \nabla \cdot \mathbf{J}_p(\psi^{(k+1)}, n^{(k+1)}, p^{(k+1)}) - R + G\)

Convergence criterion for Gummel iteration:
\[
\max\left( \frac{\|\psi^{(k+1)} - \psi^{(k)}\|}{\|\psi^{(k)}\|}, \frac{\|n^{(k+1)} - n^{(k)}\|}{\|n^{(k)}\|}, \frac{\|p^{(k+1)} - p^{(k)}\|}{\|p^{(k)}\|} \right) < 10^{-4}
\]

### 2.8 SPICE-Specific Integration

The CIDER models integrate with SPICE through:

**Companion Model for Capacitances:**
\[
I_C = \frac{C}{\Delta t} (V^{t+\Delta t} - V^t) + I_{\text{history}}
\]

**Norton Equivalent for Linearized Device:**
\[
I_k = \sum_{l=1}^m g_{kl} V_l + I_{k,\text{eq}}
\]
Where \(g_{kl} = \partial I_k / \partial V_l\) and \(I_{k,\text{eq}} = I_k - \sum_{l=1}^m g_{kl} V_l\).

**State Vector Management:** The CIDER internal states (\(\psi_i, n_i, p_i\)) are stored in the SPICE state vector at indices allocated during setup, enabling proper time integration and charge conservation.

### 2.9 Breakpoint Generation

Time step control includes breakpoint generation for:
- Rapid changes in terminal voltages (\(|dV/dt| > \text{VNTOL}/\Delta t\))
- Impact ionization onset
- Avalanche breakdown
- MOS inversion layer formation

The breakpoint detection algorithm:
\[
\left| \frac{d^2V}{dt^2} \right| \cdot \Delta t^2 > \text{VNTOL}
\]

### 2.10 Error Recovery Strategies

When convergence fails:
1. **Time Step Reduction:** \(\Delta t \leftarrow 0.5 \Delta t\)
2. **Damping Factor Reduction:** \(\lambda \leftarrow 0.5 \lambda\)
3. **GMIN Stepping:** Increase GMIN from \(10^{-12}\) to \(10^{-6}\) S
4. **Source Stepping:** Gradually ramp sources to final values
5. **Fallback to Backward Euler:** More stable but less accurate

This mathematical formulation demonstrates how CIDER numerical models implement rigorous semiconductor physics within Ngspice's SPICE framework, maintaining compatibility with circuit simulation while providing detailed device internal behavior for AC and transient analysis.

## 3. C Implementation

### 3.1 Core Data Structures and SPICEdev API Binding

#### 3.1.1 CIDER Superclass Architecture

The CIDER numerical models implement a hierarchical architecture with a common superclass structure that manages mesh data and numerical solver state:

```c
/* From CARDcore.h - Base class for all CIDER numerical devices */
typedef struct sCARDmodel {
    int CARDmodType;                    /* Device type: NBJT, NUMD, NUMOS, etc. */
    double CARDtnom;                    /* Nominal temperature */
    double CARDeps;                     /* Silicon permittivity */
    double CARDeg;                      /* Bandgap energy */
    double CARDni;                      /* Intrinsic carrier concentration */
    
    /* Mesh control parameters */
    int CARDmaxMeshPoints;              /* Maximum mesh points */
    double CARDmeshRatio;               /* Mesh grading ratio */
    int CARDadaptiveMesh;               /* Adaptive mesh refinement flag */
    
    struct sCARDmodel *CARDnextModel;   /* Next model in linked list */
    sCARDinstance *CARDinstances;       /* Pointer to instance list */
} CARDmodel;

typedef struct sCARDinstance {
    char *CARDname;                     /* Instance name */
    int CARDcNode;                      /* Collector/Anode node */
    int CARDbNode;                      /* Base/Gate node */
    int CARDeNode;                      /* Emitter/Cathode node */
    
    /* Mesh arrays */
    double *CARDx;                      /* Spatial coordinates (1D/2D) */
    double *CARDpsi;                    /* Electrostatic potential */
    double *CARDn;                      /* Electron concentration */
    double *CARDP;                      /* Hole concentration */
    double *CARDjn;                     /* Electron current density */
    double *CARDjp;                     /* Hole current density */
    double *CARDEfield;                 /* Electric field */
    double *CARDNd;                     /* Donor doping */
    double *CARDNa;                     /* Acceptor doping */
    
    /* Terminal currents */
    double CARDic;                      /* Collector/Anode current */
    double CARDib;                      /* Base/Gate current */
    double CARDie;                      /* Emitter/Cathode current */
    
    /* State vector indices */
    int CARDpsiState;                   /* Potential state index */
    int CARDnState;                     /* Electron concentration state */
    int CARDpState;                     /* Hole concentration state */
    
    /* Matrix pointers for 3-terminal device */
    double *CARDccPtr;                  /* Collector-collector */
    double *CARDcbPtr;                  /* Collector-base */
    double *CARDcePtr;                  /* Collector-emitter */
    double *CARDbcPtr;                  /* Base-collector */
    double *CARDbbPtr;                  /* Base-base */
    double *CARDbePtr;                  /* Base-emitter */
    double *CARDecPtr;                  /* Emitter-collector */
    double *CARDebPtr;                  /* Emitter-base */
    double *CARDeePtr;                  /* Emitter-emitter */
    
    struct sCARDinstance *CARDnextInstance;
    CARDmodel *CARDmodPtr;
} CARDinstance;
```

#### 3.1.2 Device-Specific Structures

Each CIDER device extends the base CARD structure with device-specific parameters:

```c
/* From nbjtdefs.h - Numerical BJT */
typedef struct sNBJTmodel {
    CARDmodel CARD;                     /* Inherit base class */
    
    /* BJT-specific parameters */
    double NBJTarea;                    /* Cross-sectional area */
    double NBJTtbe;                     /* Base-emitter transit time */
    double NBJTtbc;                     /* Base-collector transit time */
    double NBJTvaf;                     /* Early voltage */
    double NBJTvak;                     /* Knee voltage */
    
    unsigned int NBJTareaGiven :1;
    unsigned int NBJTtbeGiven  :1;
    unsigned int NBJTtbcGiven  :1;
} NBJTmodel;

typedef struct sNBJTinstance {
    CARDinstance CARD;                  /* Inherit base instance */
    
    /* BJT-specific instance data */
    double NBJTicVBE;                   /* Initial VBE */
    double NBJTicVCE;                   /* Initial VCE */
    double NBJTicVBC;                   /* Initial VBC */
    
    /* Small-signal parameters */
    double NBJTgm;                      /* Transconductance */
    double NBJTgo;                      /* Output conductance */
    double NBJTgpi;                     /* Base-emitter conductance */
    double NBJTgmu;                     /* Base-collector conductance */
    
    unsigned int NBJToff :1;            /* Device initially off */
} NBJTinstance;
```

#### 3.1.3 SPICEdev API Registration

Each CIDER device registers with Ngspice through the SPICEdev interface:

```c
/* From nbjtinit.c - Numerical BJT initialization */
SPICEdev NBJTinfo = {
    .DEVpublic = {
        .name = "nbjt",
        .description = "Numerical Bipolar Junction Transistor",
        .terms = 3,
        .numNames = 3,
        .termNames = {"c", "b", "e"},
        .numInstanceParms = 15,
        .numModelParms = 25,
    },
    .DEVmodParam = NBJTmPTable,
    .DEVinstParam = NBJTpTable,
    .DEVload = NBJTload,
    .DEVsetup = NBJTsetup,
    .DEVunsetup = NBJTunsetup,
    .DEVtemperature = NBJTtemp,
    .DEVtrunc = NBJTtrunc,
    .DEVacLoad = NBJTacLoad,
    .DEVaccept = NULL,
    .DEVdestroy = NBJTdestroy,
    .DEVconvTest = NBJTconvTest,
    .DEVsoaCheck = NBJTsoaCheck,
    .DEVinstSize = sizeof(NBJTinstance),
    .DEVmodSize = sizeof(NBJTmodel),
};
```

### 3.2 Mesh Generation and Setup Implementation

#### 3.2.1 Non-Uniform Mesh Generation

The mesh generation algorithm implements the mathematical formulation for graded meshing near junctions:

```c
/* From nbjtset.c - Numerical BJT setup */
int NBJTsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    NBJTmodel *model = (NBJTmodel *)inModel;
    NBJTinstance *inst;
    int i;
    
    for(; model != NULL; model = model->CARD.CARDnextModel) {
        for(inst = model->CARD.CARDinstances; inst != NULL; inst = inst->CARD.CARDnextInstance) {
            /* Calculate Debye length for mesh scaling */
            double maxDoping = 0.0;
            for(i = 0; i < inst->CARD.CARDnumPoints; i++) {
                double doping = fabs(inst->CARD.CARDNd[i] - inst->CARD.CARDNa[i]);
                if(doping > maxDoping) maxDoping = doping;
            }
            if(maxDoping < 1e10) maxDoping = 1e10;
            
            double Vt = 0.0258563 * (ckt->CKTtemp + 273.15) / 300.0;
            double LD = sqrt(model->CARD.CARDeps * Vt / (1.602e-19 * maxDoping));
            
            /* Generate non-uniform mesh with hyperbolic tangent grading */
            inst->CARD.CARDx = TMALLOC(double, inst->CARD.CARDnumPoints);
            double L = inst->NBJTlength;  /* Device length */
            
            for(i = 0; i < inst->CARD.CARDnumPoints; i++) {
                double xi = (double)i / (inst->CARD.CARDnumPoints - 1);
                /* Mathematical mapping: x = L * [ξ + α·tanh(β·(ξ-ξ₁)) - α·tanh(β·(ξ-ξ₂))] */
                double alpha = 0.1;  /* Mesh distortion amplitude */
                double beta = 10.0;  /* Transition sharpness */
                double xi1 = 0.3;    /* First junction position */
                double xi2 = 0.7;    /* Second junction position */
                
                inst->CARD.CARDx[i] = L * (xi + alpha * tanh(beta * (xi - xi1)) 
                                          - alpha * tanh(beta * (xi - xi2)));
            }
            
            /* Allocate state vector entries */
            inst->CARD.CARDpsiState = *states; (*states) += inst->CARD.CARDnumPoints;
            inst->CARD.CARDnState = *states; (*states) += inst->CARD.CARDnumPoints;
            inst->CARD.CARDpState = *states; (*states) += inst->CARD.CARDnumPoints;
            
            /* Initialize state variables */
            for(i = 0; i < inst->CARD.CARDnumPoints; i++) {
                ckt->CKTstate0[inst->CARD.CARDpsiState + i] = 0.0;
                ckt->CKTstate0[inst->CARD.CARDnState + i] = model->CARD.CARDni;
                ckt->CKTstate0[inst->CARD.CARDpState + i] = model->CARD.CARDni;
            }
            
            /* Allocate matrix pointers for 3-terminal device */
            inst->CARD.CARDccPtr = SMPmakeElt(matrix, inst->CARD.CARDcNode, inst->CARD.CARDcNode);
            inst->CARD.CARDcbPtr = SMPmakeElt(matrix, inst->CARD.CARDcNode, inst->CARD.CARDbNode);
            inst->CARD.CARDcePtr = SMPmakeElt(matrix, inst->CARD.CARDcNode, inst->CARD.CARDeNode);
            /* ... allocate all 9 matrix positions ... */
        }
    }
    return OK;
}
```

### 3.3 DC Load Implementation with Gummel's Method

#### 3.3.1 Poisson Equation Solver

The Poisson equation solver implements the finite difference discretization:

```c
/* From nbjtload.c - Core numerical solver */
static int solvePoisson1D(NBJTinstance *inst, CKTcircuit *ckt) {
    int n = inst->CARD.CARDnumPoints;
    double *a = inst->CARD.CARDwork1;  /* Lower diagonal */
    double *b = inst->CARD.CARDwork2;  /* Main diagonal */
    double *c = inst->CARD.CARDwork3;  /* Upper diagonal */
    double *r = inst->CARD.CARDwork4;  /* Right-hand side */
    
    /* Set up tridiagonal system: a[i]·ψ[i-1] + b[i]·ψ[i] + c[i]·ψ[i+1] = r[i] */
    for(int i = 1; i < n-1; i++) {
        double dx_prev = inst->CARD.CARDx[i] - inst->CARD.CARDx[i-1];
        double dx_next = inst->CARD.CARDx[i+1] - inst->CARD.CARDx[i];
        double dx_avg = 0.5 * (dx_prev + dx_next);
        
        /* Mathematical coefficients from finite difference discretization */
        a[i] = model->CARD.CARDeps / (dx_prev * dx_avg);
        c[i] = model->CARD.CARDeps / (dx_next * dx_avg);
        b[i] = -(a[i] + c[i]);
        
        /* Charge density: ρ = q·(p - n + Nₐ⁻ - Nₐ⁺) */
        double rho = 1.602e-19 * (inst->CARD.CARDP[i] - inst->CARD.CARDn[i] 
                                 + inst->CARD.CARDNa[i] - inst->CARD.CARDNd[i]);
        r[i] = -rho / model->CARD.CARDeps;
    }
    
    /* Boundary conditions: Dirichlet at contacts */
    b[0] = 1.0; c[0] = 0.0; r[0] = ckt->CKTrhs[inst->CARD.CARDeNode];  /* Emitter */
    a[n-1] = 0.0; b[n-1] = 1.0; r[n-1] = ckt->CKTrhs[inst->CARD.CARDcNode];  /* Collector */
    
    /* Solve tridiagonal system using Thomas algorithm */
    return solveTridiagonal(a, b, c, r, inst->CARD.CARDpsi, n);
}
```

#### 3.3.2 Continuity Equation Solver with Scharfetter-Gummel Discretization

The continuity equations implement the Scharfetter-Gummel scheme for numerical stability:

```c
static int solveElectronContinuity1D(NBJTinstance *inst, CKTcircuit *ckt) {
    int n = inst->CARD.CARDnumPoints;
    double Vt = 0.0258563 * (ckt->CKTtemp + 273.15) / 300.0;
    
    for(int i = 1; i < n-1; i++) {
        double dx = inst->CARD.CARDx[i] - inst->CARD.CARDx[i-1];
        double psi_diff = inst->CARD.CARDpsi[i] - inst->CARD.CARDpsi[i-1];
        
        /* Bernoulli function for Scharfetter-Gummel scheme */
        double B = 0.0;
        if(fabs(psi_diff) < 1e-10) {
            B = 1.0 - psi_diff/(2.0*Vt);  /* Taylor expansion for small potential */
        } else {
            B = psi_diff/Vt / (exp(psi_diff/Vt) - 1.0);
        }
        
        /* Electron current density: Jₙ = q·μₙ·n·E + q·Dₙ·dn/dx */
        double mu_n = calculateMobility(inst, i, ckt->CKTtemp);
        double D_n = mu_n * Vt;  /* Einstein relation */
        
        /* Discretized current density */
        inst->CARD.CARDjn[i] = 1.602e-19 * mu_n * Vt * 
                              (inst->CARD.CARDn[i] * B * exp(psi_diff/Vt) 
                               - inst->CARD.CARDn[i-1] * B);
        
        /* Set up continuity equation: ∂n/∂t = (1/q)∇·Jₙ - Rₙ + Gₙ */
        double R = calculateRecombination(inst, i);
        double G = calculateGeneration(inst, i);
        
        /* Time derivative using backward Euler */
        double dndt = (inst->CARD.CARDjn[i] - inst->CARD.CARDjn[i-1])/dx / 1.602e-19
                     - R + G;
        
        /* Update electron concentration */
        inst->CARD.CARDn[i] += ckt->CKTdelta * dndt;
    }
    
    return OK;
}
```

#### 3.3.3 Terminal Current Calculation

Terminal currents are computed by integrating current densities across the device:

```c
static void calculateTerminalCurrents(NBJTinstance *inst, CKTcircuit *ckt) {
    double area = inst->NBJTarea;
    int n = inst->CARD.CARDnumPoints;
    
    /* Emitter current: integral of total current at x=0 */
    double J_total_emitter = inst->CARD.CARDjn[0] + inst->CARD.CARDjp[0];
    inst->CARDie = area * J_total_emitter;  /* Emitter current */
    
    /* Collector current: integral of total current at x=L */
    double J_total_collector = inst->CARD.CARDjn[n-1] + inst->CARD.CARDjp[n-1];
    inst->CARD.CARDic = area * J_total_collector;  /* Collector current */
    
    /* Base current: conservation law I_B = I_E - I_C */
    inst->CARD.CARDib = inst->CARDie - inst->CARD.CARDic;
    
    /* Store for RHS vector stamping */
    ckt->CKTrhs[inst->CARD.CARDeNode] -= inst->CARDie;
    ckt->CKTrhs[inst->CARD.CARDcNode] -= inst->CARD.CARDic;
    ckt->CKTrhs[inst->CARD.CARDbNode] -= inst->CARD.CARDib;
}
```

### 3.4 AC Small-Signal Analysis Implementation

#### 3.4.1 AC Load Function with Perturbation Method

The AC analysis uses a perturbation method to compute derivatives for the MNA matrix:

```c
/* From nbjtacld.c - AC small-signal analysis */
int NBJTacLoad(GENmodel *inModel, CKTcircuit *ckt) {
    NBJTmodel *model = (NBJTmodel *)inModel;
    NBJTinstance *inst;
    
    for(; model != NULL; model = model->CARD.CARDnextModel) {
        for(inst = model->CARD.CARDinstances; inst != NULL; inst = inst->CARD.CARDnextInstance) {
            /* Store original operating point */
            double *psi_orig = TMALLOC(double, inst->CARD.CARDnumPoints);
            double *n_orig = TMALLOC(double, inst->CARD.CARDnumPoints);
            double *p_orig = TMALLOC(double, inst->CARD.CARDnumPoints);
            memcpy(psi_orig, inst->CARD.CARDpsi, inst->CARD.CARDnumPoints * sizeof(double));
            memcpy(n_orig, inst->CARD.CARDn, inst->CARD.CARDnumPoints * sizeof(double));
            memcpy(p_orig, inst->CARD.CARDP, inst->CARD.CARDnumPoints * sizeof(double));
            
            double Ie_orig = inst->CARDie;
            double Ic_orig = inst->CARD.CARDic;
            double Ib_orig = inst->CARD.CARDib;
            
            /* Perturb emitter voltage and re-solve */
            double epsilon = 1e-6;  /* Small perturbation */
            ckt->CKTrhs[inst->CARD.CARDeNode] += epsilon;
            
            /* Re-solve device equations at perturbed bias */
            solvePoisson1D(inst, ckt);
            solveElectronContinuity1D(inst, ckt);
            solveHoleContinuity1D(inst, ckt);
            calculateTerminalCurrents(inst, ckt);
            
            /* Compute derivatives using finite differences */
            double g11 = (inst->CARDie - Ie_orig) / epsilon;  /* ∂I_E/∂V_E */
            double g21 = (inst->CARD.CARDib - Ib_orig) / epsilon;  /* ∂I_B/∂V_E */
            double g31 = (inst->CARD.CARDic - Ic_orig) / epsilon;  /* ∂I_C/∂V_E */
            
            /* Restore original state */
            memcpy(inst->CARD.CARDpsi, psi_orig, inst->CARD.CARDnumPoints * sizeof(double));
            memcpy(inst->CARD.CARDn, n_orig, inst->CARD.CARDnumPoints * sizeof(double