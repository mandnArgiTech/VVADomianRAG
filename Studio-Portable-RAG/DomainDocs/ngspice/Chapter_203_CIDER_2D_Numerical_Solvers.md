# CIDER TCAD: 2D Box Integration and Coupled Solvers

_Generated 2026-04-13 11:07 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twomesh.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twosetup.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twosetbc.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twopoiss.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twocond.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twocont.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twosolve.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twoaval.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twoadmit.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twodopng.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twoproj.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/twod/twomobil.c`

# Chapter: CIDER TCAD: 2D Box Integration and Coupled Solvers

## Technical Introduction

The CIDER 2D device solver module implements a comprehensive finite-volume numerical engine for simulating semiconductor devices in two spatial dimensions within Ngspice's mixed-mode simulation framework. The files `twomesh.c`, `twosetup.c`, `twosetbc.c`, `twopoiss.c`, `twocond.c`, `twocont.c`, `twosolve.c`, `twoaval.c`, `twoadmit.c`, `twodopng.c`, `twoproj.c`, and `twomobil.c` collectively provide a complete 2D box integration solver for the coupled Poisson and carrier continuity equations. This system transforms the continuum 2D semiconductor physics equations into a discrete nonlinear algebraic system compatible with SPICE's Newton-Raphson solver, enabling self-consistent simulation of complex 2D TCAD devices within circuit contexts.

The solver employs the box integration method (finite-volume) with Scharfetter-Gummel stabilization for current densities, ensuring charge conservation and numerical stability across high potential gradients in 2D geometries. The module implements both Gummel's decoupled iteration and fully-coupled Newton methods with Bank-Rose damping for solving the nonlinear system, along with advanced physics models including field-dependent mobility (Lombardi model), avalanche generation with impact ionization, and small-signal admittance computation for AC analysis. The 2D discretization produces sparse matrices that interface directly with SPICE's matrix formulation through the device load function, allowing detailed 2D TCAD devices to participate in all SPICE analyses alongside compact models.

## Mathematical Formulation

### 1. Governing Partial Differential Equations

The 2D simulator solves the coupled nonlinear system of Poisson's equation and continuity equations that extend SPICE's DAE framework to spatially distributed devices:

**Poisson's Equation** (Electrostatics in 2D):
\[
\nabla \cdot (\epsilon \nabla \psi) = -q(p - n + N_D^+ - N_A^-) - \rho_{fixed}
\]
where:
- \(\psi(x,y)\): Electrostatic potential (V) - corresponds to 2D extension of SPICE node voltages
- \(\epsilon(x,y)\): Permittivity tensor (F/cm) - material property affecting capacitance stamps
- \(n(x,y), p(x,y)\): Electron and hole concentrations (cm⁻³) - internal state variables
- \(N_D^+, N_A^-\): Ionized doping concentrations (cm⁻³) - from 2D doping profiles

**Electron Continuity Equation** (Charge Conservation in 2D):
\[
\frac{\partial n}{\partial t} = \frac{1}{q} \nabla \cdot \mathbf{J}_n - R_n + G_n
\]
with current density given by drift-diffusion:
\[
\mathbf{J}_n = q\mu_n n \nabla \phi_n + qD_n \nabla n
\]

**Hole Continuity Equation**:
\[
\frac{\partial p}{\partial t} = -\frac{1}{q} \nabla \cdot \mathbf{J}_p - R_p + G_p
\]
with:
\[
\mathbf{J}_p = q\mu_p p \nabla \phi_p - qD_p \nabla p
\]

where:
- \(\phi_n, \phi_p\): Quasi-Fermi potentials (V) - alternative state variables for improved Newton convergence
- \(\mu_n, \mu_p\): Field-dependent mobilities (cm²/V·s) - from Lombardi or other 2D models
- \(D_n, D_p\): Diffusion coefficients (\(D = \mu kT/q\)) via Einstein relation
- \(R_n, R_p\): Recombination rates (SRH, Auger, surface) - device physics extensions
- \(G_n, G_p\): Generation rates (optical, avalanche) - for photodetectors and breakdown

### 2. Box Integration Method (Finite-Volume) Discretization for SPICE Compatibility

The 2D domain is partitioned into rectangular control volumes surrounding each grid point. For control volume \(V_i\) with surface \(\partial V_i\):

**Poisson Flux Integral** (Gauss's Law discretization):
\[
\int_{V_i} \nabla \cdot (\epsilon \nabla \psi) dV = \oint_{\partial V_i} \epsilon \nabla \psi \cdot \mathbf{n} dS = \sum_{j \in neighbors} \epsilon_{ij} \frac{\psi_i - \psi_j}{d_{ij}} A_{ij}
\]
where \(A_{ij}\) is the interface area between volumes \(i\) and \(j\), and \(d_{ij}\) is the distance between nodes. This conservative discretization ensures charge conservation analogous to KCL in SPICE.

**Charge Integral** (Net charge in control volume):
\[
\int_{V_i} \rho dV = q \int_{V_i} (p - n + N_D - N_A) dV \approx q(p_i - n_i + N_{D,i} - N_{A,i}) V_i
\]
where \(V_i\) is the control volume area. This maps to the charge contribution in SPICE's device stamps.

**Current Continuity Flux** with Scharfetter-Gummel stabilization (2D extension):
\[
J_{n,ij} = q\mu_n V_t \left[ n_i B\left(\frac{\psi_i - \psi_j}{V_t}\right) - n_j B\left(\frac{\psi_j - \psi_i}{V_t}\right) \right] \frac{A_{ij}}{d_{ij}}
\]
where \(B(x) = x/(e^x - 1)\) is the Bernoulli function. The 2D area factor \(A_{ij}\) accounts for the interface geometry.

### 3. 2D Avalanche Generation Model for Breakdown Simulation

**Impact Ionization Integral** in 2D:
\[
G_{av}(x,y) = \alpha_n(|\mathbf{E}|) |\mathbf{J}_n| + \alpha_p(|\mathbf{E}|) |\mathbf{J}_p|
\]
with field-dependent ionization coefficients (Chynoweth model):
\[
\alpha_n(E) = A_n \exp\left[-\left(\frac{B_n}{|E|}\right)^{m_n}\right]
\]
\[
\alpha_p(E) = A_p \exp\left[-\left(\frac{B_p}{|E|}\right)^{m_p}\right]
\]

**2D Electric Field Computation** (gradient of potential):
\[
\mathbf{E} = -\nabla \psi = -\left(\frac{\partial \psi}{\partial x} \hat{i} + \frac{\partial \psi}{\partial y} \hat{j}\right)
\]
Discretized using central differences for SPICE compatibility:
\[
E_x(i,j) = -\frac{\psi_{i+1,j} - \psi_{i-1,j}}{x_{i+1} - x_{i-1}}
\]
\[
E_y(i,j) = -\frac{\psi_{i,j+1} - \psi_{i,j-1}}{y_{j+1} - y_{j-1}}
\]
The field magnitude \(|\mathbf{E}| = \sqrt{E_x^2 + E_y^2}\) determines impact ionization rates.

### 4. Advanced 2D Mobility Models for Accurate Current Calculation

**Lombardi Model** (for MOSFET surface mobility in 2D):
\[
\frac{1}{\mu_{eff}} = \frac{1}{\mu_{bulk}} + \frac{1}{\mu_{ac}} + \frac{1}{\mu_{sr}}
\]
where:
- \(\mu_{ac} = A/E_\perp\) (acoustic phonon scattering)
- \(\mu_{sr} = B/E_\perp^2\) (surface roughness scattering)
- \(E_\perp\): Perpendicular electric field component normal to Si-SiO₂ interface

**High-Field Velocity Saturation** in 2D:
\[
v_d(|\mathbf{E}|) = \frac{\mu_0 |\mathbf{E}|}{\left[1 + \left(\frac{\mu_0 |\mathbf{E}|}{v_{sat}}\right)^\beta\right]^{1/\beta}}
\]
with \(\beta = 2\) for electrons, \(\beta = 1\) for holes typically. The field magnitude \(|\mathbf{E}|\) determines saturation.

### 5. 2D Boundary Condition Mathematics for Device Simulation

**Ohmic Contact** (Dirichlet boundary):
\[
\psi = V_{applied} + V_t \ln\left(\frac{n}{n_i}\right)
\]
\[
n = n_i \exp\left(\frac{\psi - \phi_n}{V_t}\right)
\]
\[
p = n_i \exp\left(\frac{\phi_p - \psi}{V_t}\right)
\]
These provide fixed potential conditions analogous to SPICE voltage sources.

**Schottky Contact** (current boundary condition):
\[
J_n = qv_{th,n}(n - n_0)
\]
\[
J_p = qv_{th,p}(p - p_0)
\]
with thermionic emission velocities \(v_{th,n}, v_{th,p}\).

**Insulating Boundary** (Neumann / symmetry):
\[
\nabla \psi \cdot \mathbf{n} = 0
\]
\[
\mathbf{J}_n \cdot \mathbf{n} = \mathbf{J}_p \cdot \mathbf{n} = 0
\]
These implement zero normal derivative conditions for device symmetry planes.

## Convergence Analysis: 2D Nonlinear Solver Algorithms

### 1. Coupled Newton-Raphson Iteration for 2D Systems

The discretized 2D system forms \(F(\mathbf{x}) = 0\) where \(\mathbf{x} = [\psi, n, p]^T\) at all \(N\) grid points (total \(3N\) variables), matching SPICE's DAE formulation \(F(x, ẋ, t) = 0\).

**Newton Update** (SPICE's core algorithm extended to 2D):
\[
J(\mathbf{x}^{(k)}) \Delta \mathbf{x}^{(k)} = -F(\mathbf{x}^{(k)})
\]
where \(J_{ij} = \partial F_i / \partial x_j\) is the Jacobian matrix of size \(3N \times 3N\).

**Jacobian Structure** (block sparse from 2D discretization):
\[
J = \begin{bmatrix}
\frac{\partial F_\psi}{\partial \psi} & \frac{\partial F_\psi}{\partial n} & \frac{\partial F_\psi}{\partial p} \\
\frac{\partial F_n}{\partial \psi} & \frac{\partial F_n}{\partial n} & \frac{\partial F_n}{\partial p} \\
\frac{\partial F_p}{\partial \psi} & \frac{\partial F_p}{\partial n} & \frac{\partial F_p}{\partial p}
\end{bmatrix}
\]
Each block is sparse with 5-point stencil structure in 2D (each node connects to at most 4 neighbors).

### 2. Preconditioned Iterative Linear Solvers for 2D Systems

**For Poisson Block** (symmetric positive definite from box integration):
Use Incomplete Cholesky Conjugate Gradient (ICCG):
\[
M^{-1} J \Delta \mathbf{x} = -M^{-1} F
\]
where \(M = L L^T \approx J\) (incomplete Cholesky factorization). The condition number scales as \(\kappa(J_{Poisson}) = O(1/h_{min}^2)\) where \(h_{min} = \min(h_x, h_y)\).

**For Continuity Blocks** (nonsymmetric from drift-diffusion):
Use Incomplete LU Bi-Conjugate Gradient (ILU-BiCGSTAB):
\[
M^{-1} J \Delta \mathbf{x} = -M^{-1} F
\]
where \(M = L U \approx J\) (incomplete LU with threshold dropping).

### 3. Bank-Rose Damping Algorithm for 2D Convergence

**Adaptive Damping Factor** for Newton updates:
\[
\lambda^{(k)} = \min\left(1.0, \frac{\|F(\mathbf{x}^{(k)})\|}{\|F(\mathbf{x}^{(k)} + \Delta \mathbf{x}^{(k)})\|}\right)
\]
Update: \(\mathbf{x}^{(k+1)} = \mathbf{x}^{(k)} + \lambda^{(k)} \Delta \mathbf{x}^{(k)}\)

**Divergence Detection and Recovery**:
If \(\|F(\mathbf{x}^{(k+1)})\| > (1 + \alpha) \|F(\mathbf{x}^{(k)})\|\), reduce \(\lambda\) by factor \(\beta = 0.5\). This implements SPICE's convergence aids at the device level.

### 4. Gummel Iteration for Initial Guess in 2D

**Sequential Solution** (decouples 2D equations):
1. Solve 2D Poisson with frozen \(n, p\)
2. Solve 2D electron continuity with frozen \(\psi, p\)
3. Solve 2D hole continuity with frozen \(\psi, n\)
4. Repeat until convergence

**Convergence Criterion** for 2D Gummel:
\[
\max\left(\frac{\|\Delta \psi\|_\infty}{\|\psi\|_\infty}, \frac{\|\Delta n\|_\infty}{\|n\|_\infty}, \frac{\|\Delta p\|_\infty}{\|p\|_\infty}\right) < \epsilon_{Gummel}
\]
where \(\|\cdot\|_\infty\) is the maximum norm over all grid points.

### 5. Matrix Conditioning Analysis for 2D Discretization

**Condition Number Estimation** for 2D Laplacian:
\[
\kappa(J_{Poisson}) = \frac{\sigma_{max}(J)}{\sigma_{min}(J)} \approx \frac{\lambda_{max}}{\lambda_{min}} = O\left(\frac{1}{h_{min}^2}\right)
\]
where \(h_{min} = \min(h_x, h_y)\) is the minimum grid spacing.

**Stability Condition for Scharfetter-Gummel in 2D**:
Require \(|\Delta \psi| < 10 V_t\) between adjacent nodes for linearization stability. Larger potential differences trigger damping.

### 6. Avalanche Convergence Issues and Stabilization

**Generation Rate Clamping** to prevent numerical overflow:
\[
G_{av,clamped} = \min(G_{av}, G_{max})
\]
where \(G_{max} = \frac{n}{\tau_{impact}}\) prevents runaway avalanche multiplication.

**Impact Ionization Linearization** for Jacobian:
\[
\frac{\partial G_{av}}{\partial E} = \frac{m \alpha(E) B}{E} \left(\frac{B}{E}\right)^{m-1}
\]
must be bounded to maintain Jacobian diagonal dominance. Clamp derivatives when \(E \to 0\).

### 7. Time-Step Control for 2D Transient Analysis

**Local Truncation Error (LTE)** estimation in 2D:
\[
\tau_{LTE} = \frac{\Delta t^2}{12} \left\|\frac{\partial^2 \mathbf{x}}{\partial t^2}\right\|_\infty
\]
where the norm is taken over all grid points and variables.

**Adaptive Time-Stepping** for 2D transient:
\[
\Delta t_{new} = \Delta t_{old} \cdot \min\left(2.0, \max\left(0.5, 0.8 \sqrt{\frac{\epsilon}{\tau_{LTE}}}\right)\right)
\]
This matches SPICE's TRTOL and CHGTOL controls for transient accuracy.

### 8. Convergence Monitoring and Diagnostics for 2D Simulation

**Residual Norms** for convergence checking:
- Absolute residual: \(\|F(\mathbf{x})\|_2 < \epsilon_{abs}\) (SPICE's ABSTOL)
- Relative residual: \(\|F(\mathbf{x})\|_2 / \|F(\mathbf{x}_0)\|_2 < \epsilon_{rel}\) (SPICE's RELTOL)
- Maximum update: \(\|\Delta \mathbf{x}\|_\infty < \epsilon_{update}\)

**Charge Conservation Check** in 2D (KCL verification):
\[
\left|\sum_{\text{boundary}} \mathbf{J} \cdot \mathbf{n} A - \int_V (R - G) dV\right| < \epsilon_{charge}
\]
where the sum is over all boundary segments with area \(A\).

### 9. Performance Optimization for 2D Circuit Simulation

**Jacobian Reuse Condition** in 2D:
\[
\|\Delta \mathbf{x}\|_2 / \|\mathbf{x}\|_2 < \epsilon_{reuse} \quad \text{AND} \quad \max|\Delta \psi| < 0.1V_T
\]
Reuse Jacobian factorization when solution changes are small, reducing computational cost.

**Selective Update for Quasi-Neutral Regions** in 2D:
```
IF |ψ - φ_n| < 0.1V_T AND |ψ - φ_p| < 0.1V_T over region Ω THEN
    // Region in equilibrium
    Solve only Poisson in Ω, update n,p analytically
    Skip continuity equation solves in Ω
ENDIF
```

**Domain Decomposition** for parallel solution:
Partition 2D grid into subdomains with ghost layers, solve independently with interface matching conditions.

### 10. Interface with SPICE Matrix Formulation

**Terminal Current Stamping** from 2D device:
Device terminal currents \(I_k\) contribute to SPICE's RHS vector \(b\):
\[
b[\text{node}_k] += I_k = \oint_{\partial \Omega_k} (\mathbf{J}_n + \mathbf{J}_p) \cdot \mathbf{n} dS
\]
where the integral is over the contact boundary \(\partial \Omega_k\).

**Conductance Stamping** (small-signal):
Device differential conductance \(\partial I_k/\partial V_j\) stamps into SPICE's \(G\) matrix:
\[
G[\text{node}_k, \text{node}_j] += \frac{\partial I_k}{\partial V_j}
\]

**Capacitance Stamping** from 2D charge storage:
Device charge derivatives \(\partial Q_k/\partial V_j\) stamp into SPICE's \(C\) matrix:
\[
C[\text{node}_k, \text{node}_j] += \frac{\partial Q_k}{\partial V_j}
\]
where \(Q_k = \int_{\Omega_k} \rho dV\) is the charge in region \(\Omega_k\).

### 11. Small-Signal Admittance Computation for AC Analysis

**2D Small-Signal Formulation**:
For frequency \(\omega\), solve linearized system:
\[
[J + j\omega C] \tilde{\mathbf{x}} = \tilde{\mathbf{b}}
\]
where \(J\) is the DC Jacobian, \(C\) is the capacitance matrix from charge storage, \(\tilde{\mathbf{x}}\) is the small-signal solution, and \(\tilde{\mathbf{b}}\) is the small-signal excitation.

**Port Admittance Matrix**:
\[
Y_{ij}(\omega) = \frac{\tilde{I}_i}{\tilde{V}_j} = G_{ij} + j\omega C_{ij}
\]
where \(\tilde{I}_i\) is the small-signal current at port \(i\) due to voltage \(\tilde{V}_j\) at port \(j\).

### 12. Validation Metrics for SPICE Consistency

**Kirchhoff's Current Law Verification** for 2D device:
\[
\sum_{\text{terminals}} I_k = 0 \quad \text{within } \epsilon_{KCL}
\]
where \(\epsilon_{KCL} = 1e-12 \cdot \max|I_k|\) (SPICE's current tolerance).

**Energy Conservation** in transient simulation:
\[
\left|\int_{t_0}^{t_1} (P_{in} - P_{diss}) dt\right| / \left|\int_{t_0}^{t_1} P_{in} dt\right| < \epsilon_{energy}
\]
where \(\epsilon_{energy} = 1e-6\) (SPICE's energy tolerance).

**Small-Signal Consistency Check**:
\[
\text{Im}(Y_{ij}(\omega))/\omega = C_{ij}(\omega) \quad \text{(capacitance from admittance)}
\]
\[
\text{Re}(Y_{ij}(\omega)) = G_{ij}(\omega) \quad \text{(conductance from admittance)}
\]
Verify frequency dependence matches 2D device physics.

This mathematical formulation ensures that the CIDER 2D solver produces device characteristics that are numerically consistent with SPICE's solution algorithms while handling the complexities of 2D spatial discretization. The convergence analysis provides the robustness needed for automated circuit simulation with detailed 2D TCAD devices across diverse operating conditions, device geometries, and analysis types (DC, AC, transient).

## C Implementation

The mathematical formulations described above are implemented in Ngspice's CIDER 2D module through a carefully structured C codebase. The implementation maps each mathematical concept directly to specific data structures, algorithms, and functions across the twelve core files, ensuring numerical stability while maintaining compatibility with SPICE's simulation engine.

### 1. Core Data Structures for 2D Simulation

**Mesh Data Structure (`twomesh.h`):**
```c
typedef struct sTWOnode {
    double x, y;                    // Spatial coordinates
    double psi;                     // Electrostatic potential
    double n, p;                    // Carrier concentrations
    double phi_n, phi_p;            // Quasi-Fermi potentials
    double Nd, Na;                  // Doping concentrations
    int    material_id;             // Material identifier
    int    boundary_type;           // Boundary condition type
    double area;                    // Control volume area
    struct sTWOnode *east, *west;   // Neighbor pointers
    struct sTWOnode *north, *south;
} TWOnode;

typedef struct sTWOmesh {
    TWOnode **grid;                 // 2D array of nodes
    int      nx, ny;                // Grid dimensions
    double   dx_min, dy_min;        // Minimum spacing
    double   dx_max, dy_max;        // Maximum spacing
    double   x_min, x_max;          // Domain boundaries
    double   y_min, y_max;
    int      total_nodes;           // Total grid points
    int      active_nodes;          // Non-boundary nodes
} TWOmesh;
```

**Boundary Condition Structure (`twosetbc.h`):**
```c
typedef struct sTWOboundary {
    int    type;                    // BC_TYPE_OHMIC, BC_TYPE_SCHOTTKY, etc.
    double potential;               // Applied potential for Dirichlet
    double current_density;         // For current boundary conditions
    double surface_recomb;          // Surface recombination velocity
    int    *node_indices;           // Array of boundary node indices
    int    num_nodes;               // Number of boundary nodes
    double length;                  // Boundary segment length
    int    terminal_id;             // SPICE terminal connection
} TWOboundary;
```

**Newton Solver Context (`twosolve.h`):**
```c
typedef struct sTWOnewton {
    double **J;                     // Jacobian matrix (block sparse)
    double  *F;                     // Residual vector
    double  *dx;                    // Solution update
    double  *x;                     // Current solution vector
    int      size;                  // Total system size (3 * active_nodes)
    int      max_iter;              // Maximum Newton iterations
    double   tolerance;             // Convergence tolerance
    double   damping_factor;        // Bank-Rose damping parameter
    int      iter_count;            // Current iteration
    double   residual_norm;         // Current residual norm
    int      jacobian_reuse;        // Flag for Jacobian reuse
    double   last_update_norm;      // For reuse condition checking
} TWOnewton;
```

### 2. Mesh Generation and Setup (`twomesh.c`, `twosetup.c`)

**Geometric Progression Mesh Generation:**
```c
int TWOgenerateMesh(TWOmesh *mesh, double Lx, double Ly, 
                    int nx, int ny, double ratio) {
    // Generate non-uniform grid with geometric progression
    double dx0 = Lx * (1 - ratio) / (1 - pow(ratio, nx/2));
    double dy0 = Ly * (1 - ratio) / (1 - pow(ratio, ny/2));
    
    for (int i = 0; i < nx; i++) {
        if (i < nx/2) {
            mesh->grid[i][0].x = dx0 * (1 - pow(ratio, i)) / (1 - ratio);
        } else {
            mesh->grid[i][0].x = Lx - dx0 * (1 - pow(ratio, nx-i-1)) / (1 - ratio);
        }
    }
    
    // Similar for y-direction
    // ...
    
    // Store minimum and maximum spacing
    mesh->dx_min = dx0;
    mesh->dx_max = dx0 * pow(ratio, nx/2 - 1);
    mesh->total_nodes = nx * ny;
    
    return OK;
}
```

**Adaptive Mesh Refinement Based on Doping Gradient:**
```c
void TWOrefineMeshNearJunction(TWOmesh *mesh, double doping_threshold) {
    // Refine mesh where doping gradient is high
    for (int i = 1; i < mesh->nx - 1; i++) {
        for (int j = 1; j < mesh->ny - 1; j++) {
            double grad_nd = fabs(mesh->grid[i+1][j].Nd - mesh->grid[i-1][j].Nd) 
                           / (2 * (mesh->grid[i+1][j].x - mesh->grid[i-1][j].x));
            double grad_na = fabs(mesh->grid[i][j+1].Na - mesh->grid[i][j-1].Na)
                           / (2 * (mesh->grid[i][j+1].y - mesh->grid[i][j-1].y));
            
            if (grad_nd > doping_threshold || grad_na > doping_threshold) {
                // Insert new nodes or adjust spacing
                TWOinsertNode(mesh, i, j);
            }
        }
    }
}
```

### 3. Boundary Condition Setup (`twosetbc.c`)

**Ohmic Contact Implementation:**
```c
void TWOsetOhmicBoundary(TWOboundary *bc, TWOmesh *mesh, 
                         double voltage, int terminal_id) {
    bc->type = BC_TYPE_OHMIC;
    bc->potential = voltage;
    bc->terminal_id = terminal_id;
    
    // For each boundary node, set Dirichlet conditions
    for (int n = 0; n < bc->num_nodes; n++) {
        int idx = bc->node_indices[n];
        TWOnode *node = mesh->grid[idx];
        
        // Set potential (includes built-in potential)
        node->psi = voltage + Vt * log(node->Nd / ni);
        
        // Set carrier concentrations assuming equilibrium
        node->n = ni * exp((node->psi - node->phi_n) / Vt);
        node->p = ni * exp((node->phi_p - node->psi) / Vt);
        
        // Mark as boundary node
        node->boundary_type = BC_TYPE_OHMIC;
    }
}
```

**Schottky Contact with Thermionic Emission:**
```c
void TWOsetSchottkyBoundary(TWOboundary *bc, TWOmesh *mesh,
                           double barrier_height, double voltage) {
    bc->type = BC_TYPE_SCHOTTKY;
    bc->potential = voltage;
    
    // Richardson constant for thermionic emission
    double A_star = 120.0; // A/(cm²·K²) for n-Si
    
    for (int n = 0; n < bc->num_nodes; n++) {
        int idx = bc->node_indices[n];
        TWOnode *node = mesh->grid[idx];
        
        // Schottky barrier lowering
        double delta_phi = sqrt(q * E_max / (4 * PI * epsilon)) / (2 * epsilon);
        double effective_barrier = barrier_height - delta_phi;
        
        // Thermionic emission current density
        double J_s = A_star * T * T * exp(-effective_barrier / (k_B * T / q));
        bc->current_density = J_s * (exp(voltage / Vt) - 1);
        
        // Set boundary conditions for continuity equations
        node->boundary_type = BC_TYPE_SCHOTTKY;
    }
}
```

### 4. Poisson Equation Assembly (`twopoiss.c`)

**Box Integration Matrix Assembly:**
```c
void TWOassemblePoisson(TWOnewton *newton, TWOmesh *mesh, 
                        double epsilon, double Vt) {
    int idx = 0;
    
    for (int i = 0; i < mesh->nx; i++) {
        for (int j = 0; j < mesh->ny; j++) {
            TWOnode *node = &mesh->grid[i][j];
            
            if (node->boundary_type == BC_TYPE_OHMIC) {
                // Dirichlet boundary: fixed potential
                int row = 3 * idx;  // ψ equation index
                newton->J[row][row] = 1.0;  // Diagonal = 1
                newton->F[row] = node->psi - newton->x[row];
                continue;
            }
            
            // Interior node: assemble flux integrals
            double diag_coeff = 0.0;
            double rhs_charge = -q * (node->p - node->n + node->Nd - node->Na) * node->area;
            
            // East neighbor
            if (i < mesh->nx - 1) {
                TWOnode *east = &mesh->grid[i+1][j];
                double dx = east->x - node->x;
                double interface_area = (node->y_max - node->y_min);  // Assuming rectangular
                double coeff = epsilon * interface_area / dx;
                
                int col = 3 * (idx + 1);  // ψ at east neighbor
                newton->J[row][col] = -coeff;
                diag_coeff += coeff;
            }
            
            // Similar for west, north, south neighbors
            // ...
            
            // Diagonal entry
            newton->J[row][row] = diag_coeff;
            
            // Right-hand side: charge in control volume
            newton->F[row] = rhs_charge;
            
            // Derivatives with respect to n and p
            newton->J[row][row+1] = q * node->area;  // ∂F_ψ/∂n
            newton->J[row][row+2] = -q * node->area; // ∂F_ψ/∂p
            
            idx++;
        }
    }
}
```

### 5. Continuity Equation Assembly (`twocont.c`)

**Scharfetter-Gummel Discretization Implementation:**
```c
double TWObernoulli(double u) {
    // Stable Bernoulli function implementation
    if (fabs(u) < 1e-6) {
        // Taylor expansion for small arguments
        return 1.0 - u/2.0 + u*u/12.0 - u*u*u*u/720.0;
    } else if (u > 30.0) {
        // Avoid overflow for large positive u
        return 0.0;
    } else if (u < -30.0) {
        // Avoid underflow for large negative u
        return -u;
    } else {
        return u / (exp(u) - 1.0);
    }
}

void TWOscharfetterGummel(TWOnewton *newton, TWOmesh *mesh, 
                          int node_idx, int neighbor_idx, 
                          double mu, double D, double A_interface) {
    TWOnode *node = mesh->grid[node_idx];
    TWOnode *neighbor = mesh->grid[neighbor_idx];
    
    double dx = fabs(neighbor->x - node->x);
    double dpsi = node->psi - neighbor->psi;
    double u = dpsi / Vt;
    
    // Bernoulli functions
    double B_u = TWObernoulli(u);
    double B_minus_u = TWObernoulli(-u);
    
    // Electron current density
    double Jn = q * mu * Vt * (node->n * B_u - neighbor->n * B_minus_u) / dx;
    
    // Assembly into continuity equation
    int row_n = 3 * node_idx + 1;  // Electron continuity equation index
    
    // Derivatives with respect to ψ
    double dJn_dpsi = q * mu * (node->n * dB_du(u) + neighbor->n * dB_du(-u)) / (dx * Vt);
    newton->J[row_n][3*node_idx] += dJn_dpsi * A_interface;
    
    // Derivatives with respect to n
    newton->J[row_n][row_n] += q * mu * Vt * B_u / dx * A_interface;
    newton->J[row_n][3*neighbor_idx+1] += -q * mu * Vt * B_minus_u / dx * A_interface;
    
    // Right-hand side: current flux
    newton->F[row_n] += Jn * A_interface;
}
```

**Recombination Models Implementation:**
```c
double TWOcomputeSRHRecombination(TWOnode *node, double tau_n, double tau_p) {
    // Shockley-Read-Hall recombination
    double numerator = node->n * node->p - ni * ni;
    double denominator = tau_p * (node->n + n1) + tau_n * (node->p + p1);
    
    if (denominator < 1e-30) return 0.0;
    return numerator / denominator;
}

double TWOcomputeAugerRecombination(TWOnode *node, double Cn, double Cp) {
    // Auger recombination
    return Cn * (node->n * node->n * node->p - ni*ni*node->n) +
           Cp * (node->p * node->p * node->n - ni*ni*node->p);
}
```

### 6. Mobility Model Implementation (`twomobil.c`)

**Lombardi Mobility Model:**
```c
double TWOcomputeLombardiMobility(TWOnode *node, double E_perp, 
                                  Material *material) {
    // Lombardi (CVT) mobility model for MOSFETs
    double mu_bulk = material->mu_bulk;
    
    // Acoustic phonon scattering
    double mu_ac = material->A_ac / E_perp;
    if (mu_ac < 0) mu_ac = 1e10;  // Avoid negative mobility
    
    // Surface roughness scattering
    double mu_sr = material->B_sr / (E_perp * E_perp);
    
    // Combined mobility
    double inv_mu = 1.0/mu_bulk + 1.0/mu_ac + 1.0/mu_sr;
    double mu_eff = 1.0 / inv_mu;
    
    // High-field saturation
    double E_parallel = sqrt(node->Ex*node->Ex + node->Ey*node->Ey);
    double mu_sat = material->v_sat / E_parallel;
    
    return 1.0 / (1.0/mu_eff + 1.0/mu_sat);
}
```

**Field-Dependent Mobility with Velocity Saturation:**
```c
double TWOcomputeHighFieldMobility(TWOnode *node, double mu0, 
                                   double vsat, double beta) {
    double E_mag = sqrt(node->Ex*node->Ex + node->Ey*node->Ey);
    
    if (E_mag < 1e-30) return mu0;
    
    // Caughey-Thomas formula
    double numerator = mu0 * E_mag;
    double denominator = pow(1.0 + pow(mu0 * E_mag / vsat, beta), 1.0/beta);
    
    return numerator / denominator;
}
```

### 7. Avalanche Generation Computation (`twoaval.c`)

**Impact Ionization Model:**
```c
void TWOcomputeAvalanche(TWOmesh *mesh, double *G_av) {
    // Compute avalanche generation rate at each node
    for (int i = 0; i < mesh->nx; i++) {
        for (int j = 0; j < mesh->ny; j++) {
            TWOnode *node = &mesh->grid[i][j];
            
            // Electric field magnitude
            double Ex = -(mesh->grid[i+1][j].psi - mesh->grid[i-1][j].psi) 
                       / (mesh->grid[i+1][j].x - mesh->grid[i-1][j].x);
            double Ey = -(mesh->grid[i][j+1].psi - mesh->grid[i][j-1].psi)
                       / (mesh->grid[i][j+1].y - mesh->grid[i][j-1].y);
            double E_mag = sqrt(Ex*Ex +