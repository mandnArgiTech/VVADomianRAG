# CIDER Numerical Models: 1D/2D Mesh and Material Parameters

_Generated 2026-04-13 02:47 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtparm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt/nbjtset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbjt2def.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2parm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/nbjt2/nbt2set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numddefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdparm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd/numdset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/numd2def.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2parm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numd2/nud2set.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/numosdef.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummparm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/numos/nummset.c`

# Chapter: CIDER Numerical Models: 1D/2D Mesh and Material Parameters

## Technical Introduction

This chapter documents the implementation of CIDER (Circuit and Device Emulation and Research) numerical models within the Ngspice EDA codebase. CIDER extends traditional SPICE simulation by incorporating advanced numerical techniques for semiconductor device modeling, including 1D and 2D finite-element/finite-difference meshing, material parameter databases, and coupled electro-thermal-physical simulation. The implementation spans fifteen core C source files that define the architecture for mesh-based device simulation within Ngspice's Modified Nodal Analysis (MNA) framework.

The files `nbjtdefs.h`, `nbjt2def.h`, `numddefs.h`, `numd2def.h`, and `numosdef.h` contain the fundamental C structure definitions for numerical BJT, diode, and MOSFET models, respectively. These structures extend Ngspice's generic device architecture with mesh management systems, material property storage, and state variables for distributed device physics. The parameter processing files `nbjtparm.c`, `nbt2parm.c`, `numdparm.c`, `nud2parm.c`, and `nummparm.c` implement the binding logic between SPICE netlist parameters and the internal C struct fields, handling complex material parameter interpolation and mesh generation specifications. The setup files `nbjtset.c`, `nbt2set.c`, `numdset.c`, `nud2set.c`, and `nummset.c` perform critical initialization tasks: memory allocation for mesh data structures, construction of finite-element/finite-difference discretization matrices, material database loading, and sparse matrix pointer allocation for the extended MNA system.

Together, these files implement a sophisticated multi-physics simulation layer that bridges circuit-level analysis with detailed device physics. The CIDER models solve the coupled drift-diffusion-Poisson equations on structured or unstructured grids, enabling simulation of advanced semiconductor devices with internal potential and carrier distributions, temperature gradients, and complex material behavior—all while maintaining integration with Ngspice's traditional circuit simulation workflow through carefully designed interface functions and state management systems.

## Mathematical Formulation

The CIDER numerical models implement a comprehensive framework for semiconductor device simulation based on the drift-diffusion equations coupled with Poisson's equation. The mathematical formulation bridges continuum device physics with discrete circuit simulation through spatial discretization and material parameter interpolation.

### 1.1 Fundamental Semiconductor Equations

The core equations governing semiconductor device behavior are:

**Poisson's Equation:**
\[
\nabla \cdot (\epsilon \nabla \psi) = -q(p - n + N_D^+ - N_A^-)
\]
where:
- \(\psi\) = electrostatic potential
- \(\epsilon\) = permittivity tensor
- \(q\) = elementary charge
- \(p, n\) = hole and electron concentrations
- \(N_D^+, N_A^-\) = ionized donor and acceptor concentrations

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

### 1.2 1D/2D Spatial Discretization

#### 1.2.1 Finite Difference Method (1D)

For 1D simulations along the x-direction, the discretization uses central differences:

**Poisson Equation Discretization:**
\[
\epsilon_{i+\frac{1}{2}} \frac{\psi_{i+1} - \psi_i}{\Delta x^2} - \epsilon_{i-\frac{1}{2}} \frac{\psi_i - \psi_{i-1}}{\Delta x^2} = -q(p_i - n_i + N_{D,i}^+ - N_{A,i}^-)
\]

**Current Density Discretization (Scharfetter-Gummel scheme):**
\[
J_{n,i+\frac{1}{2}} = q\mu_n \frac{kT}{q} \frac{n_{i+1}B(\psi_{i+1} - \psi_i) - n_i B(\psi_i - \psi_{i+1})}{\Delta x}
\]
where \(B(x) = \frac{x}{e^x - 1}\) is the Bernoulli function.

#### 1.2.2 Finite Element Method (2D)

For 2D simulations, the domain \(\Omega\) is discretized into triangular elements:

**Weak Form of Poisson's Equation:**
\[
\int_\Omega \epsilon \nabla \psi \cdot \nabla v \, d\Omega = \int_\Omega q(p - n + N_D^+ - N_A^-)v \, d\Omega
\]
for all test functions \(v\) in the finite element space.

**Element Stiffness Matrix:**
For linear triangular elements with nodes \(i, j, k\):
\[
K_{ij} = \frac{\epsilon}{4A} (b_i b_j + c_i c_j)
\]
where \(A\) is element area, and \(b_i, c_i\) are geometric coefficients from:
\[
\psi(x,y) = \sum_{i=1}^3 N_i(x,y)\psi_i
\]
with linear shape functions \(N_i\).

### 1.3 Material Parameter Models

Material parameters are modeled as functions of doping, temperature, and electric field:

**Mobility Models:**
\[
\mu(E, N, T) = \frac{\mu_0(T)}{1 + \left(\frac{\mu_0 E}{v_{sat}}\right)^\beta}
\]
with low-field mobility:
\[
\mu_0(T, N) = \mu_{min} + \frac{\mu_{max} - \mu_{min}}{1 + \left(\frac{N}{N_{ref}}\right)^\alpha}
\]

**Recombination Models:**
Shockley-Read-Hall recombination:
\[
R_{SRH} = \frac{pn - n_i^2}{\tau_p(n + n_1) + \tau_n(p + p_1)}
\]
Auger recombination:
\[
R_{Auger} = (C_n n + C_p p)(pn - n_i^2)
\]

### 1.4 Coupling to Circuit Equations

The device equations are coupled to circuit equations through terminal currents:

**Terminal Current Calculation:**
\[
I_k = \int_{\Gamma_k} \mathbf{J} \cdot \mathbf{n} \, d\Gamma + \frac{d}{dt} \int_{\Omega_k} q(p - n) \, d\Omega
\]
where \(\Gamma_k\) is the contact area for terminal \(k\).

**Modified Nodal Analysis Extension:**
The coupled system becomes:
\[
\begin{bmatrix}
\mathbf{G} & \mathbf{B} \\
\mathbf{C} & \mathbf{D}(\mathbf{x})
\end{bmatrix}
\begin{bmatrix}
\mathbf{v} \\
\mathbf{x}
\end{bmatrix}
=
\begin{bmatrix}
\mathbf{i} \\
\mathbf{f}(\mathbf{x})
\end{bmatrix}
\]
where:
- \(\mathbf{x}\) = internal device states (ψ, n, p at all mesh points)
- \(\mathbf{D}(\mathbf{x})\) = device Jacobian from discretized semiconductor equations
- \(\mathbf{B}, \mathbf{C}\) = coupling matrices between circuit and device variables

### 1.5 Discretized System Formulation

The fully discretized system for transient simulation using backward Euler is:

**Nonlinear System at Time Step \(t_{n+1}\):**
\[
\mathbf{F}(\mathbf{x}^{n+1}) = 
\begin{bmatrix}
\mathbf{A}_\psi(\psi^{n+1}, n^{n+1}, p^{n+1}) \\
\frac{n^{n+1} - n^n}{\Delta t} - \mathbf{A}_n(\psi^{n+1}, n^{n+1}) \\
\frac{p^{n+1} - p^n}{\Delta t} - \mathbf{A}_p(\psi^{n+1}, p^{n+1})
\end{bmatrix}
= \mathbf{0}
\]

**Newton-Raphson Linearization:**
\[
\mathbf{J}(\mathbf{x}^{(k)}) \Delta \mathbf{x}^{(k)} = -\mathbf{F}(\mathbf{x}^{(k)})
\]
with block-structured Jacobian:
\[
\mathbf{J} = 
\begin{bmatrix}
\frac{\partial \mathbf{A}_\psi}{\partial \psi} & \frac{\partial \mathbf{A}_\psi}{\partial n} & \frac{\partial \mathbf{A}_\psi}{\partial p} \\
\frac{\partial \mathbf{A}_n}{\partial \psi} & \frac{\partial \mathbf{A}_n}{\partial n} & \mathbf{0} \\
\frac{\partial \mathbf{A}_p}{\partial \psi} & \mathbf{0} & \frac{\partial \mathbf{A}_p}{\partial p}
\end{bmatrix}
+ \frac{1}{\Delta t}
\begin{bmatrix}
\mathbf{0} & \mathbf{0} & \mathbf{0} \\
\mathbf{0} & \mathbf{I} & \mathbf{0} \\
\mathbf{0} & \mathbf{0} & \mathbf{I}
\end{bmatrix}
\]

### 1.6 Mesh Generation and Adaptation

#### 1.6.1 Structured Mesh Generation
For rectangular domains, tensor-product grids:
\[
x_{i,j} = x_{min} + (i-1)\Delta x_j, \quad y_{i,j} = y_{min} + (j-1)\Delta y_i
\]
with adaptive spacing based on doping gradients:
\[
\Delta x_{i+1} = \Delta x_i \cdot \min\left(1.2, 1 + \alpha \frac{|\nabla N|}{N}\right)
\]

#### 1.6.2 Unstructured Mesh Generation
Delaunay triangulation with quality constraints:
\[
Q_{triangle} = \frac{4\sqrt{3}A}{l_1^2 + l_2^2 + l_3^2} \geq Q_{min}
\]
where \(A\) is area and \(l_i\) are side lengths.

#### 1.6.3 Adaptive Mesh Refinement
Based on error estimator:
\[
\eta_K = h_K \| \nabla \psi_h - \nabla \psi_{ref} \|_{L^2(K)}
\]
Elements with \(\eta_K > \theta \max_K \eta_K\) are refined.

### 1.7 Material Database Interpolation

Material parameters are stored in multi-dimensional tables and interpolated:

**Multi-linear Interpolation:**
For parameter \(P(T, N, E)\):
\[
P = \sum_{i,j,k} w_{ijk} P_{ijk}
\]
with weights:
\[
w_{ijk} = \prod_{d=1}^3 (1 - |x_d - x_{d,i}| / \Delta x_d)
\]
for normalized coordinates \(x_d\) in each dimension.

### 1.8 Boundary Conditions

#### 1.8.1 Ohmic Contacts:
\[
\psi = V_{applied} + \frac{kT}{q} \ln\left(\frac{n}{n_i}\right)
\]
\[
pn = n_i^2
\]

#### 1.8.2 Schottky Contacts:
\[
J_n = qv_n(n - n_0)
\]
with surface recombination velocity \(v_n\).

#### 1.8.3 Insulating Boundaries:
\[
\nabla \psi \cdot \mathbf{n} = 0, \quad \mathbf{J} \cdot \mathbf{n} = 0
\]

### 1.9 Thermal Modeling

Coupled electro-thermal simulation includes heat equation:
\[
\rho c_p \frac{\partial T}{\partial t} = \nabla \cdot (\kappa \nabla T) + Q
\]
with Joule heating source:
\[
Q = \mathbf{J} \cdot \mathbf{E}
\]

Temperature-dependent material parameters:
\[
\mu(T) = \mu_0 \left(\frac{T}{T_0}\right)^{-\alpha_\mu}
\]
\[
n_i(T) = n_{i0} \left(\frac{T}{T_0}\right)^{3/2} \exp\left[-\frac{E_g}{2k}\left(\frac{1}{T} - \frac{1}{T_0}\right)\right]
\]

### 1.10 Numerical Solution Strategy

The coupled nonlinear system is solved using:

**Gummel Iteration (Decoupled Approach):**
1. Solve Poisson: \(A_\psi(\psi, n, p) = 0\) with fixed \(n, p\)
2. Solve electron continuity: \(A_n(\psi, n) = 0\) with fixed \(\psi, p\)
3. Solve hole continuity: \(A_p(\psi, p) = 0\) with fixed \(\psi, n\)
4. Repeat until convergence

**Full Newton (Coupled Approach):**
Solve all equations simultaneously using the block-structured Jacobian.

**Preconditioning:**
Block-diagonal preconditioner:
\[
\mathbf{P} = 
\begin{bmatrix}
\mathbf{J}_{\psi\psi} & \mathbf{0} & \mathbf{0} \\
\mathbf{0} & \mathbf{J}_{nn} & \mathbf{0} \\
\mathbf{0} & \mathbf{0} & \mathbf{J}_{pp}
\end{bmatrix}
\]

This mathematical formulation provides the foundation for CIDER's implementation of advanced semiconductor device simulation within Ngspice, enabling detailed physics-based modeling while maintaining integration with traditional circuit simulation techniques.

## Convergence Analysis

The CIDER numerical models present significant convergence challenges due to the coupled nonlinear nature of the semiconductor equations, the stiffness introduced by widely varying time scales, and the large sparse systems resulting from spatial discretization. Convergence analysis focuses on the interplay between Newton-Raphson iteration for nonlinear systems, time integration stability, and mesh adaptation criteria.

### 2.1 Newton-Raphson Convergence for Coupled Systems

The coupled drift-diffusion-Poisson system is solved using Newton's method:

**Residual Definition:**
\[
\mathbf{F}(\mathbf{x}) = 
\begin{bmatrix}
\mathbf{A}_\psi(\psi, n, p) \\
\mathbf{A}_n(\psi, n) \\
\mathbf{A}_p(\psi, p)
\end{bmatrix}
= \mathbf{0}
\]
where \(\mathbf{x} = [\psi, n, p]^T\) contains all discrete variables.

**Newton Update:**
\[
\mathbf{J}^{(k)} \Delta \mathbf{x}^{(k)} = -\mathbf{F}(\mathbf{x}^{(k)})
\]
with block Jacobian:
\[
\mathbf{J} = 
\begin{bmatrix}
\frac{\partial \mathbf{A}_\psi}{\partial \psi} & \frac{\partial \mathbf{A}_\psi}{\partial n} & \frac{\partial \mathbf{A}_\psi}{\partial p} \\
\frac{\partial \mathbf{A}_n}{\partial \psi} & \frac{\partial \mathbf{A}_n}{\partial n} & \mathbf{0} \\
\frac{\partial \mathbf{A}_p}{\partial \psi} & \mathbf{0} & \frac{\partial \mathbf{A}_p}{\partial p}
\end{bmatrix}
\]

**Convergence Criteria:**
1. **Absolute residual norm:** \(\|\mathbf{F}(\mathbf{x}^{(k)})\|_2 < \epsilon_{abs}\)
2. **Relative residual reduction:** \(\frac{\|\mathbf{F}(\mathbf{x}^{(k)})\|_2}{\|\mathbf{F}(\mathbf{x}^{(0)})\|_2} < \epsilon_{rel}\)
3. **Update norm:** \(\|\Delta \mathbf{x}^{(k)}\|_2 < \epsilon_{update}\)

Typical values: \(\epsilon_{abs} = 10^{-10}\), \(\epsilon_{rel} = 10^{-6}\), \(\epsilon_{update} = 10^{-8}\).

### 2.2 Gummel Iteration Convergence

For decoupled solution, the Gummel iteration convergence rate is:

**Contraction Mapping Analysis:**
The iteration \(\mathbf{x}^{(k+1)} = G(\mathbf{x}^{(k)})\) converges if:
\[
\|G(\mathbf{x}) - G(\mathbf{y})\| \leq L \|\mathbf{x} - \mathbf{y}\|
\]
with Lipschitz constant \(L < 1\).

**Gummel Convergence Rate:**
\[
\|\mathbf{x}^{(k+1)} - \mathbf{x}^*\| \leq \frac{L}{1-L} \|\mathbf{x}^{(k)} - \mathbf{x}^{(k-1)}\|
\]

The method converges linearly with rate \(L\), which depends on the coupling strength between equations.

### 2.3 Time Integration Stability

#### 2.3.1 Backward Euler Stability
The backward Euler method is A-stable but introduces numerical diffusion:

**Local Truncation Error:**
\[
\tau_n = \frac{\Delta t}{2} \frac{d^2\mathbf{x}}{dt^2}(t_n) + O(\Delta t^2)
\]

**Stability Condition:**
For linear test equation \(y' = \lambda y\), backward Euler is stable for all \(\Re(\lambda) \leq 0\).

#### 2.3.2 TR-BDF2 Method
The TR-BDF2 method combines trapezoidal rule and BDF2:

**Algorithm:**
1. Trapezoidal from \(t_n\) to \(t_{n+\gamma}\): 
   \[
   \mathbf{x}_{n+\gamma} - \mathbf{x}_n = \frac{\gamma \Delta t}{2} [\mathbf{f}(\mathbf{x}_{n+\gamma}) + \mathbf{f}(\mathbf{x}_n)]
   \]
2. BDF2 from \(t_{n+\gamma}\) to \(t_{n+1}\):
   \[
   \mathbf{x}_{n+1} - \frac{1}{\gamma(2-\gamma)} \mathbf{x}_{n+\gamma} + \frac{(1-\gamma)^2}{\gamma(2-\gamma)} \mathbf{x}_n = \frac{1-\gamma}{2-\gamma} \Delta t \mathbf{f}(\mathbf{x}_{n+1})
   \]
   with \(\gamma = 2 - \sqrt{2}\) for L-stability.

### 2.4 Local Truncation Error (LTE) Control

#### 2.4.1 Charge Conservation LTE
For charge-based integration:
\[
\text{LTE}_Q = \frac{\Delta t^2}{12} \left| \frac{d^3 Q}{dt^3} \right|
\]
where \(Q = \int_\Omega q(p-n) d\Omega\) is total charge.

#### 2.4.2 Richardson Extrapolation
Using solutions at different time steps:
\[
\mathbf{x}_{\Delta t}(t_{n+1}) = \mathbf{x}^*(t_{n+1}) + C \Delta t^p + O(\Delta t^{p+1})
\]
\[
\mathbf{x}_{\Delta t/2}(t_{n+1}) = \mathbf{x}^*(t_{n+1}) + C \left(\frac{\Delta t}{2}\right)^p + O(\Delta t^{p+1})
\]
Error estimate:
\[
\epsilon = \frac{\|\mathbf{x}_{\Delta t} - \mathbf{x}_{\Delta t/2}\|}{2^p - 1}
\]

#### 2.4.3 Adaptive Time Step Control
Time step adjustment based on LTE:
\[
\Delta t_{new} = \Delta t_{old} \cdot \min\left(2.0, \max\left(0.5, \rho \left(\frac{\epsilon_{tol}}{\epsilon}\right)^{1/(p+1)}\right)\right)
\]
with safety factor \(\rho = 0.9\) and order \(p = 1\) for backward Euler, \(p = 2\) for trapezoidal rule.

### 2.5 Mesh Convergence Analysis

#### 2.5.1 A Priori Error Estimates
For linear finite elements:
\[
\|\psi - \psi_h\|_{H^1} \leq C h \|\psi\|_{H^2}
\]
\[
\|n - n_h\|_{L^2} \leq C h^2 \|n\|_{H^2}
\]
where \(h\) is maximum element diameter.

#### 2.5.2 A Posteriori Error Estimation
Element-wise error estimator:
\[
\eta_K^2 = h_K^2 \|R_K\|_{L^2(K)}^2 + \sum_{e \subset \partial K} h_e \|J_e\|_{L^2(e)}^2
\]
where:
- \(R_K\) = element residual
- \(J_e\) = flux jump across edge \(e\)

#### 2.5.3 Adaptive Mesh Refinement Criterion
Refine elements where:
\[
\eta_K > \theta \max_{K' \in \mathcal{T}_h} \eta_{K'}
\]
with \(\theta = 0.7\) typically.

### 2.6 Nonlinear Solver Convergence Enhancement

#### 2.6.1 Damping (Under-relaxation)
Damped Newton update:
\[
\mathbf{x}^{(k+1)} = \mathbf{x}^{(k)} + \omega^{(k)} \Delta \mathbf{x}^{(k)}
\]
with damping factor:
\[
\omega^{(k)} = \min\left(1.0, \frac{2}{1 + \|\Delta \mathbf{x}^{(k)}\|}\right)
\]

#### 2.6.2 Continuation Methods
Parameter continuation for difficult bias points:
\[
\mathbf{F}(\mathbf{x}, \lambda) = \mathbf{0}, \quad \lambda \in [0,1]
\]
with \(\lambda = 0\) for easy problem, \(\lambda = 1\) for target problem.

#### 2.6.3 Gmin Stepping
Add artificial conductance to improve conditioning:
\[
\mathbf{J}' = \mathbf{J} + g_{min} \mathbf{I}
\]
with \(g_{min}\) gradually reduced from \(10^{-3}\) to \(10^{-12}\) S.

### 2.7 Linear Solver Convergence

#### 2.7.1 Condition Number Analysis
The Jacobian condition number grows with:
\[
\kappa(\mathbf{J}) = O\left(\frac{1}{h^2}\right) \quad \text{for Poisson equation}
\]
\[
\kappa(\mathbf{J}) = O\left(\frac{1}{\Delta t}\right) \quad \text{for transient terms}
\]

#### 2.7.2 Preconditioning Strategies
1. **Block-diagonal preconditioner:**
   \[
   \mathbf{P} = \text{diag}(\mathbf{J}_{\psi\psi}, \mathbf{J}_{nn}, \mathbf{J}_{pp})
   \]

2. **Incomplete LU factorization:**
   \[
   \mathbf{P} = \tilde{\mathbf{L}} \tilde{\mathbf{U}} \approx \mathbf{J}
   \]
   with drop tolerance \(\tau = 10^{-4}\).

3. **Multigrid preconditioner** for mesh hierarchies.

#### 2.7.3 Krylov Subspace Methods
GMRES with restart parameter \(m = 30\):
\[
\min_{\mathbf{y} \in \mathcal{K}_m} \|\mathbf{J}\mathbf{y} + \mathbf{F}\|
\]
where \(\mathcal{K}_m = \text{span}\{\mathbf{r}_0, \mathbf{J}\mathbf{r}_0, \ldots, \mathbf{J}^{m-1}\mathbf{r}_0\}\).

### 2.8 Material Parameter Convergence

#### 2.8.1 Interpolation Error
For material parameter \(P(T, N)\) with bilinear interpolation:
\[
|P - P_h| \leq C h^2 \max\left(\left|\frac{\partial^2 P}{\partial T^2}\right|, \left|\frac{\partial^2 P}{\partial N^2}\right|\right)
\]

#### 2.8.2 Self-consistent Iteration
For temperature-dependent parameters:
1. Solve with initial \(T^{(0)}\)
2. Update \(T^{(k+1)}\) from heat equation
3. Update material parameters \(\mu(T^{(k+1)})\), \(n_i(T^{(k+1)})\)
4. Repeat until \(\|T^{(k+1)} - T^{(k)}\| < \epsilon_T\)

### 2.9 Convergence Monitoring and Diagnostics

#### 2.9.1 Convergence History Tracking
Monitor:
- Newton iteration count
- Linear solver iteration count
- Residual norm reduction
- Update norm

#### 2.9.2 Divergence Detection
Divergence indicated by:
1. Residual norm increasing: \(\|\mathbf{F}^{(k+1)}\| > 2 \|\mathbf{F}^{(k)}\|\)
2. Oscillation: \(\text{sign}(\Delta x_i^{(k)}) \neq \text{sign}(\Delta x_i^{(k-1)})\) for many components
3. NaN or Inf in solution

#### 2.9.3 Recovery Strategies
Upon divergence:
1. Reduce time step: \(\Delta t \leftarrow 0.5 \Delta t\)
2. Increase damping: \(\omega \leftarrow 0.5 \omega\)
3. Revert to previous solution and restart
4. Switch to more robust solver (Gummel instead of full Newton)

### 2.10 Performance-Optimized Convergence

#### 2.10.1 Selective Newton Updates
Only update components where:
\[
|\Delta x_i| > \epsilon_{update} \cdot \max(1, |x_i|)
\]

#### 2.10.2 Dynamic Tolerance Adjustment
Adjust solver tolerances based on Newton progress:
\[
\epsilon_{linear} = \min\left(10^{-6}, 0.1 \frac{\|\mathbf{F}^{(k)}\|}{\|\mathbf{F}^{(k-1)}\|}\right)
\]

#### 2.10.3 Cache-aware Mesh Traversal
Optimize memory access patterns for better convergence of iterative solvers.

### 2.11 Theoretical Convergence Guarantees

#### 2.11.1 Newton-Kantorovich Theorem
If:
1. \(\mathbf{F}\) is Fréchet differentiable
2. \(\|\mathbf{J}(\mathbf{x}_0)^{-1}\| \leq \beta\)
3. \(\|\mathbf{J}(\mathbf{x}) - \mathbf{J}(\mathbf{y})\| \leq \gamma \|\mathbf{x} - \mathbf{y}\|\)
4. \(\beta \gamma \|\mathbf{F}(\mathbf{x}_0)\| \leq \frac{1}{2}\)

Then Newton's method converges quadratically.

#### 2.11.2 Mesh Independence Principle
For sufficiently fine meshes, the Newton iteration count becomes independent of \(h\).

This convergence analysis demonstrates that the CIDER numerical models implement sophisticated algorithms for managing the complex interplay between nonlinear device physics, spatial discretization, and time integration. The combination of adaptive strategies, robust linear algebra, and careful error control enables reliable simulation of advanced semiconductor devices within the SPICE framework.

## C Implementation

### 1. Core Data Structures for Mesh-Based Simulation

The CIDER implementation extends Ngspice's standard device architecture with specialized structures for mesh management and material parameter storage. The core data structures map directly to the mathematical formulation of discretized semiconductor equations.

#### 1.1 Mesh Data Structure (`ciderMesh`)

```c
typedef struct sCiderMesh {
    /* Mesh topology and geometry */
    int numNodes;                  /* Total number of mesh nodes */
    int numElements;               /* Total number of mesh elements */
    int numBoundaries;             /* Number of boundary segments */
    
    /* Node coordinates - maps to spatial discretization points */
    double *nodeX;                 /* x-coordinates for all nodes */
    double *nodeY;                 /* y-coordinates for all nodes (2D) */
    double *nodeZ;                 /* z-coordinates for all nodes (3D) */
    
    /* Element connectivity - implements finite element discretization */
    int *elementNodes;             /* Node indices for each element */
    int *elementType;              /* Element type: 1=line, 2=triangle, 3=quad */
    double *elementArea;           /* Area/volume of each element */
    
    /* Boundary conditions - maps to ψ, n, p boundary conditions */
    int *boundaryNodes;            /* Nodes on boundaries */
    int *boundaryType;             /* BC type: 1=Dirichlet, 2=Neumann, 3=Mixed */
    double *boundaryValue;         /* Boundary values for Dirichlet BCs */
    
    /* Material assignment - maps material models to spatial regions */
    int *nodeMaterial;             /* Material index for each node */
    int *elementMaterial;          /* Material index for each element */
    
    /* Solution vectors - store ψ, n, p at all mesh points */
    double *psi;                   /* Electrostatic potential ψ(x,y) */
    double *electronConc;          /* Electron concentration n(x,y) */
    double *holeConc;              /* Hole concentration p(x,y) */
    double *temperature;           /* Temperature T(x,y) for electro-thermal */
    
    /* Time derivatives for transient simulation */
    double *dpsi_dt;               /* ∂ψ/∂t for displacement current */
    double *dn_dt;                 /* ∂n/∂t for continuity equations */
    double *dp_dt;                 /* ∂p/∂t for continuity equations */
    
    /* Jacobian matrix storage - sparse format for ∇²ψ, ∇·J terms */
    int *jacRowPtr;                /* Row pointers for CSR format */
    int *jacColIdx;                /* Column indices for CSR format */
    double *jacValues;             /* Matrix values for CSR format */
    int jacNNZ;                    /* Number of non-zero entries */
    
    /* Preconditioner data */
    void *preconditioner;          /* ILU, SSOR, or multigrid preconditioner */
    int precondType;               /* Preconditioner type identifier */
    
    /* Adaptive mesh refinement data */
    double *errorIndicator;        /* η_K for each element */
    int *refinementFlag;           /* Flag for element refinement */
    struct sCiderMesh *parentMesh; /* Pointer to coarser mesh (multigrid) */
    struct sCiderMesh *childMesh;  /* Pointer to finer mesh (multigrid) */
} CiderMesh;
```

#### 1.2 Material Parameter Structure (`ciderMaterial`)

```c
typedef struct sCiderMaterial {
    /* Basic material properties */
    char materialName[32];         /* Material identifier: "Si", "GaAs", etc. */
    double permittivity;           /* ε = ε_rε_0 for Poisson equation */
    double bandgap;                /* E_g for intrinsic concentration */
    double affinity;               /* Electron affinity χ */
    
    /* Mobility models - maps to μ(E,N,T) functions */
    double mu0_e;                  /* Low-field electron mobility */
    double mu0_h;                  /* Low-field hole mobility */
    double vsat_e;                 /* Electron saturation velocity */
    double vsat_h;                 /* Hole saturation velocity */
    double beta_e;                 /* Exponent for field-dependent mobility */
    double beta_h;
    
    /* Doping-dependent mobility parameters */
    double Nref_e;                 /* Reference doping for μ(N) */
    double Nref_h;
    double alpha_e;                /* Exponent for μ(N) */
    double alpha_h;
    
    /* Recombination parameters */
    double tau_n;                  /* Electron lifetime τ_n for SRH */
    double tau_p;                  /* Hole lifetime τ_p for SRH */
    double Cn;                     /* Electron Auger coefficient */
    double Cp;                     /* Hole Auger coefficient */
    
    /* Thermal properties */
    double thermalCond;            /* κ for heat equation */
    double heatCapacity;           /* ρc_p for heat equation */
    double density;                /* ρ for thermal calculations */
    
    /* Temperature coefficients */
    double Eg_Tcoeff;              /* dE_g/dT for temperature dependence */
    double mu_Tcoeff_e;            /* Temperature exponent for μ_e */
    double mu_Tcoeff_h;            /* Temperature exponent for μ_h */
    
    /* Parameter tables for interpolation */
    double *dopingTable;           /* N_dop values for table lookup */
    double *temperatureTable;      /* T values for table lookup */
    double *fieldTable;            /* E values for table lookup */
    double *mobilityTable;         /* μ(N,T,E) 3D table */
    double *niTable;               /* n_i(T) table */
    
    /* Function pointers for material models */
    double (*mobilityFunc)(struct sCiderMaterial*, double, double, double);
    double (*recombinationFunc)(struct sCiderMaterial*, double, double, double);
    double (*niFunc)(struct sCiderMaterial*, double);
} CiderMaterial;
```

#### 1.3 Device Instance Structure (`sCIDERinstance`)

```c
typedef struct sCIDERinstance {
    GENinstance gen;               /* Base Ngspice device structure */
    
    /* Terminal connections - maps to circuit nodes */
    int anodeNode;                 /* Anode terminal node */
    int cathodeNode;               /* Cathode terminal node */
    int substrateNode;             /* Substrate/body terminal node */
    int thermalNode;               /* Thermal terminal for electro-thermal */
    
    /* Device geometry - maps to spatial domain Ω */
    double length;                 /* Device length in x-direction */
    double width;                  /* Device width in y-direction */
    double depth;                  /* Device depth in z-direction */
    double area;                   /* Cross-sectional area */
    
    /* Mesh data - implements spatial discretization */
    CiderMesh *mesh;               /* Primary computational mesh */
    CiderMesh *coarseMesh;         /* Coarse mesh for multigrid */
    CiderMesh *fineMesh;           /* Fine mesh for solution transfer */
    
    /* Material database */
    CiderMaterial **materials;     /* Array of material definitions */
    int numMaterials;              /* Number of materials in device */
    
    /* Doping profiles - maps to N_D(x,y), N_A(x,y) */
    double *dopingDonor;           /* Donor concentration at nodes */
    double *dopingAcceptor;        /* Acceptor concentration at nodes */
    int dopingProfileType;         /* 1=constant, 2=gaussian, 3=erfc, 4=file */
    
    /* Solution state vectors */
    double *solution;              /* Combined [ψ, n, p] vector */
    double *solutionOld;           /* Solution at previous time step */
    double *solutionPred;          /* Predicted solution for BDF */
    double *residual;              /* Nonlinear residual F(x) */
    double *jacobian;              /* Jacobian matrix in sparse format */
    
    /* Terminal currents - maps to I_k = ∫J·n dΓ */
    double Ianode;                 /* Anode current */
    double Icathode;               /* Cathode current */
    double Isubstrate;             /* Substrate current */
    double powerDissipated;        /* P_diss = V·I for thermal */
    
    /* Small-signal parameters */
    double conductance;            /* Small-signal conductance dI/dV */
    double capacitance;            /* Small-signal capacitance dQ/dV */
    double transconductance;       /* For multi-terminal devices */
    
    /* State management for Ngspice */
    int stateIndexPsi;             /* State vector index for ψ */
    int stateIndexN;               /* State vector index for n */
    int stateIndexP;               /* State vector index for p */
    int stateIndexT;               /* State vector index for temperature */
    
    /* Matrix pointers for MNA stamping */
    double *ptrAnodeAnode;         /* G[anode, anode] */
    double *ptrAnodeCathode;       /* G[anode, cathode] */
    double *ptrCathodeAnode;       /* G[cathode, anode] */
    double *ptrCathodeCathode;     /* G[cathode, cathode] */
    double *ptrThermalThermal;     /* G[thermal, thermal] for heat flow */
    
    /* Convergence control */
    double newtonTolerance;        /* ε for Newton convergence */
    double linearTolerance;        /* ε for linear solver */
    int maxNewtonIterations;       /* Maximum Newton iterations */
    int maxLinearIterations;       /* Maximum linear iterations */
    int newtonIterationCount;      /* Actual Newton iterations used */
    int linearIterationCount;      /* Actual linear iterations used */
    
    /* Time step control */
    double currentTimeStep;        /* Current Δt */
    double minTimeStep;            /* Minimum allowed Δt */
    double maxTimeStep;            /* Maximum allowed Δt */
    double LTE;                    /* Local truncation error estimate */
    int timeStepReductions;        /* Count of time step reductions */
    
    /* Work arrays for numerical methods */
    double *work1;                 /* Work array size numNodes */
    double *work2;                 /* Work array size numNodes */
    double *work3;                 /* Work array size numNodes */
    double *workMatrix;            /* Work array for matrix operations */
    
    /* Statistics and diagnostics */
    double setupTime;              /* Time spent in setup */
    double solutionTime;           /* Time spent in nonlinear solve */
    double linearSolveTime;        /* Time spent in linear solves */
    double residualNormHistory[10]; /* Last 10 residual norms */
    int convergenceFailures;       /* Count of convergence failures */
} CIDERinstance;
```

#### 1.4 Device Model Structure (`sCIDERmodel`)

```c
typedef struct sCIDERmodel {
    GENmodel gen;                  /* Base Ngspice model structure */
    
    /* Model-level parameters */