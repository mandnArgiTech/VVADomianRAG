# CIDER TCAD: Solid-State Physics and Material Models

_Generated 2026-04-13 10:40 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/mater.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/mobil.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/recomb.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/database.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/geominfo.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/integset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/integuse.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/suprem.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/support/suprmitf.c`

# Chapter: CIDER TCAD: Solid-State Physics and Material Models

## Technical Introduction

The CIDER (Circuit and Device Emulator) TCAD module within Ngspice implements the fundamental solid-state physics models required for detailed semiconductor device simulation. The files `mater.c`, `mobil.c`, `recomb.c`, `database.c`, `geominfo.c`, `integset.c`, `integuse.c`, `suprem.c`, and `suprmitf.c` collectively provide the material property database, carrier mobility models, recombination-generation physics, and process simulation interface necessary for physics-based device simulation. These components transform the abstract semiconductor drift-diffusion equations into numerically stable, computationally efficient implementations that integrate seamlessly with Ngspice's core DAE solver.

The system implements a hierarchical material property framework: `mater.c` defines base material classes with temperature-dependent parameters; `mobil.c` implements the Masetti, Arora, and other mobility models accounting for doping, temperature, and field dependence; `recomb.c` provides Shockley-Read-Hall, Auger, and radiative recombination models; `database.c` manages the material parameter lookup system; `geominfo.c` handles geometric information for anisotropic materials; `integset.c` and `integuse.c` control numerical integration methods for carrier statistics; while `suprem.c` and `suprmitf.c` implement the SUPREM process simulation interface for generating doping profiles from fabrication steps. This implementation enables Ngspice to perform predictive TCAD simulation where device characteristics emerge from first-principles physics rather than empirical compact models.

## Mathematical Formulation

### 1. Unified Differential-Algebraic Equation Framework for Semiconductor Device Simulation

The CIDER TCAD module extends Ngspice's core DAE framework to model semiconductor devices with spatially distributed physics. The fundamental system remains:

```
F(x(t), ẋ(t), u(t), t) = 0
```

where for semiconductor devices:
- `x(t) ∈ ℝ^n`: State vector now includes **ψ** (electrostatic potential), **n** (electron concentration), **p** (hole concentration) at each mesh node
- `ẋ(t) ∈ ℝ^n`: Time derivatives of carrier concentrations and potentials
- `u(t) ∈ ℝ^m`: Terminal voltages/currents applied to device contacts
- `F`: Semiconductor equations (Poisson, continuity, transport)

### 2. Semiconductor Physics Equations

#### 2.1 Poisson Equation (Electrostatics)
```
∇·(ε∇ψ) = -q(p - n + N_d⁺ - N_a⁻)
```
where:
- `ψ`: Electrostatic potential (V)
- `ε`: Permittivity (F/cm)
- `q`: Elementary charge (1.602×10⁻¹⁹ C)
- `n, p`: Electron and hole concentrations (cm⁻³)
- `N_d⁺, N_a⁻`: Ionized donor and acceptor concentrations (cm⁻³)

#### 2.2 Carrier Continuity Equations
**Electrons**:
```
∂n/∂t = (1/q)∇·J_n - R_n + G_n
```
**Holes**:
```
∂p/∂t = -(1/q)∇·J_p - R_p + G_p
```
where:
- `J_n, J_p`: Electron and hole current densities (A/cm²)
- `R_n, R_p`: Recombination rates (cm⁻³s⁻¹)
- `G_n, G_p`: Generation rates (cm⁻³s⁻¹)

#### 2.3 Drift-Diffusion Transport Model
**Electron current density**:
```
J_n = qμ_n n E + qD_n ∇n
```
**Hole current density**:
```
J_p = qμ_p p E - qD_p ∇p
```
where:
- `μ_n, μ_p`: Carrier mobilities (cm²/V·s)
- `D_n, D_p`: Diffusion coefficients (cm²/s), related by Einstein relation: `D = (kT/q)μ`
- `E = -∇ψ`: Electric field (V/cm)

### 3. Material-Specific Physics Models

#### 3.1 Mobility Models (Masetti Model for Silicon)
**Doping-dependent mobility**:
```
μ(N,T) = μ_min1 exp(-P_c/N) + (μ_const - μ_min2)/(1 + (N/C_r)^α) - μ_1/(1 + (C_s/N)^β)
```
**Temperature dependence**:
```
μ(T) = μ(300K) × (T/300)^{-γ}
```
where:
- `N = N_d + N_a`: Total doping concentration (cm⁻³)
- `P_c, C_r, C_s`: Fitting parameters
- `α ≈ 0.76, β ≈ 1.0, γ ≈ 2.0`: Empirical exponents

#### 3.2 Band Gap Narrowing (Slotboom Model)
```
ΔE_g = q × [A × ln(N/N_0) + B × (ln(N/N_0))² + C × (ln(N/N_0))³]
```
Effective intrinsic carrier concentration:
```
n_ie² = n_i² × exp(ΔE_g/(kT))
```
where:
- `A, B, C, N_0`: Material parameters (Si: A=9×10⁻³, B=3×10⁻⁵, C=3×10⁻⁵, N_0=10¹⁷ cm⁻³)
- `n_i`: Intrinsic carrier concentration (1.5×10¹⁰ cm⁻³ for Si at 300K)

#### 3.3 Recombination Models

**Shockley-Read-Hall (SRH) Recombination**:
```
R_SRH = (pn - n_ie²)/[τ_p(n + n_1) + τ_n(p + p_1)]
```
where:
- `τ_n, τ_p`: Carrier lifetimes (s)
- `n_1 = n_i exp((E_t - E_i)/(kT))`
- `p_1 = n_i exp((E_i - E_t)/(kT))`
- `E_t`: Trap energy level (eV)

**Auger Recombination**:
```
R_Auger = (C_n n + C_p p)(pn - n_ie²)
```
where `C_n, C_p` are Auger coefficients (cm⁶/s).

**Radiative Recombination**:
```
R_rad = B_rad (pn - n_ie²)
```
where `B_rad` is radiative recombination coefficient.

### 4. Boundary Conditions for Device Simulation

#### 4.1 Ohmic Contacts
**Dirichlet conditions**:
```
ψ = V_applied + ψ_bi
n = n_0 = (N_d + √(N_d² + 4n_i²))/2
p = p_0 = n_i²/n_0
```
where `ψ_bi = (kT/q) ln(N_d N_a/n_i²)` is built-in potential.

#### 4.2 Schottky Contacts
```
J_n = q v_n (n - n_0)
J_p = q v_p (p - p_0)
ψ = V_applied + φ_b - (kT/q) ln(n/n_0)
```
where `φ_b` is Schottky barrier height.

#### 4.3 Semiconductor-Insulator Interfaces (MOS)
**Gauss's Law**:
```
ε_s E_s - ε_ox E_ox = Q_s
```
where `Q_s` is surface charge density.

### 5. Discretization Schemes

#### 5.1 Finite Volume Method (Conservative)
For control volume Ω with surface ∂Ω:
```
∫_Ω (∂n/∂t) dΩ = (1/q)∫_{∂Ω} J_n·dS - ∫_Ω R_n dΩ + ∫_Ω G_n dΩ
```

#### 5.2 Scharfetter-Gummel Discretization
For current between nodes i and j:
```
J_ij = (qμ/Δx)[B(Δψ/V_t) n_j - B(-Δψ/V_t) n_i]
```
where `B(x) = x/(e^x - 1)` is Bernoulli function, `V_t = kT/q`.

#### 5.3 Time Discretization
**Backward Euler**:
```
(∂n/∂t) ≈ (n^{k+1} - n^k)/Δt
```

**Trapezoidal (Crank-Nicolson)**:
```
(∂n/∂t) ≈ (n^{k+1} - n^k)/Δt = 0.5[f(n^{k+1}) + f(n^k)]
```

## Convergence Analysis

### 1. Gummel's Method for Coupled Solution

#### 1.1 Decoupled Iteration Scheme
Instead of solving all equations simultaneously, Gummel's method solves sequentially:

1. **Solve Poisson equation** for ψ with fixed n, p:
   ```
   ∇·(ε∇ψ) = -q(p^{(k)} - n^{(k)} + N_d - N_a)
   ```

2. **Solve electron continuity** with fixed ψ, p:
   ```
   ∂n/∂t = (1/q)∇·J_n(ψ, n) - R_n(n, p^{(k)}) + G_n
   ```

3. **Solve hole continuity** with fixed ψ, n:
   ```
   ∂p/∂t = -(1/q)∇·J_p(ψ, p) - R_p(n^{(k+1)}, p) + G_p
   ```

#### 1.2 Convergence Criteria
**Potential convergence**:
```
||ψ^{(k+1)} - ψ^{(k)}||_∞ < ε_ψ + ε_rel·||ψ^{(k)}||_∞
```
where `ε_ψ = 1 mV` typically.

**Carrier concentration convergence**:
```
||n^{(k+1)} - n^{(k)}||_∞ < ε_n + ε_rel·||n^{(k)}||_∞
```
where `ε_n = 10¹⁰ cm⁻³` (relative to doping).

**Current continuity**:
```
|∫_Ω (∇·J - qR) dΩ| < ε_I·|I_terminal|
```
where `ε_I = 10⁻⁶`.

### 2. Newton's Method for Full Coupled Solution

#### 2.1 Jacobian Matrix Structure
For the coupled system `F(ψ, n, p) = 0`, the Jacobian has block structure:
```
J = [∂F_ψ/∂ψ  ∂F_ψ/∂n  ∂F_ψ/∂p]
    [∂F_n/∂ψ  ∂F_n/∂n  ∂F_n/∂p]
    [∂F_p/∂ψ  ∂F_p/∂n  ∂F_p/∂p]
```

#### 2.2 Diagonal Dominance and Conditioning
The Jacobian is typically ill-conditioned due to:
- Large variation in carrier concentrations (10¹⁰ to 10²⁰ cm⁻³)
- Exponential dependence on potential: `n ∝ exp(ψ/V_t)`

**Preconditioning strategy**:
```
M = diag(1/|∂F_i/∂x_i|)
J_precond = M·J
```

#### 2.3 Damping for Newton Iteration
```
x^{(k+1)} = x^{(k)} + λΔx^{(k)}
```
where damping factor λ is chosen to ensure:
```
||F(x^{(k+1)})|| < (1 - αλ)||F(x^{(k)})||
```
with `α ≈ 0.1`.

### 3. Numerical Stability Considerations

#### 3.1 Exponential Argument Limiting
For Boltzmann statistics:
```
n = n_i exp((ψ - φ_n)/V_t)
```
Limit argument to prevent overflow:
```
|(ψ - φ_n)/V_t| < φ_max = log(DBL_MAX/n_i) ≈ 23 for double precision
```

#### 3.2 Scharfetter-Gummel Stability
The Bernoulli function `B(x) = x/(e^x - 1)` is computed as:
```
IF |x| < 1e-5 THEN B(x) ≈ 1 - x/2 + x²/12
ELSEIF x > 50 THEN B(x) ≈ 0
ELSEIF x < -50 THEN B(x) ≈ -x
ELSE B(x) = x/(exp(x) - 1)
```

#### 3.3 Dielectric Relaxation Time Limit
Maximum stable time step:
```
Δt_max < ε/(qμN)  (dielectric relaxation time)
```
For silicon with `N = 10¹⁶ cm⁻³`: `Δt_max ≈ 10⁻¹² s`.

### 4. Convergence Failure Recovery

#### 4.1 Potential Undershoot/Overshoot Detection
When solving Poisson equation:
```
IF |Δψ| > 2V_t THEN
    // Carrier concentrations would change by > e²
    Apply damping: Δψ ← Δψ/2
    Recompute n, p with new ψ
ENDIF
```

#### 4.2 Generation Control for High-Level Injection
At high injection levels (`n ≈ p ≫ N_d`):
```
n = p = n_i exp((ψ - φ_n)/V_t)  becomes inaccurate
```
Switch to:
```
n = N_d + δn, p = N_a + δp
```
and solve for δn, δp as primary variables.

#### 4.3 Trap-Filling Effects
When traps dominate recombination:
```
R = (pn - n_i²)/[τ(n + n_1) + τ(p + p_1)]
```
Linearize around operating point:
```
R ≈ R_0 + (∂R/∂n)Δn + (∂R/∂p)Δp
```

### 5. Physical Consistency Checks

#### 5.1 Space Charge Neutrality
Global check:
```
|∫_Ω (p - n + N_d - N_a) dΩ| < ε_Q·|∫_Ω N_d dΩ|
```
where `ε_Q = 10⁻⁶`.

#### 5.2 Current Continuity
At each node:
```
|∑ J_in - ∑ J_out| < ε_J·max(|J_in|, |J_out|)
```
where `ε_J = 10⁻⁹`.

#### 5.3 Energy Balance (for advanced models)
```
∫_Ω (J·E) dΩ = ∫_Ω (qU(ψ,n,p) + ∂W/∂t) dΩ
```
where `U` is net recombination-generation, `W` is energy density.

### 6. Performance Optimization Strategies

#### 6.1 Adaptive Time Stepping
Based on local truncation error estimate:
```
Δt_{new} = Δt_{old} × min(2, max(0.5, (ε/||LTE||)^{1/(p+1)}))
```
where `p` is integration order.

#### 6.2 Matrix Reuse
Jacobian is reused while:
```
||Δx||/||x|| < ε_reuse  AND  |ΔV_max| < 0.1V_t
```
where `ε_reuse = 0.01`.

#### 6.3 Selective Newton Updates
For device regions in equilibrium:
```
IF |ψ - φ_n| < 0.1V_t AND |ψ - φ_p| < 0.1V_t THEN
    // Quasi-neutral region
    Solve only Poisson equation
    Update n, p analytically from ψ
ENDIF
```

### 7. Convergence Monitoring and Diagnostics

#### 7.1 Residual Norms
**Absolute residual**:
```
R_abs = ||F(x)||_∞
```

**Relative residual**:
```
R_rel = ||F(x)||_∞/||F(0)||_∞
```

**Weighted residual** (for mixed variables):
```
R_weighted = max(|F_ψ|/V_t, |F_n|/N_ref, |F_p|/N_ref)
```
where `N_ref = max(N_d, N_a, n_i)`.

#### 7.2 Convergence History Tracking
Store at each iteration k:
- `||Δx^{(k)}||`
- `||F(x^{(k)})||`
- Condition number estimate of Jacobian
- Number of linear solver iterations

#### 7.3 Divergence Detection
```
IF ||F(x^{(k+1)})|| > γ||F(x^{(k)})|| WITH γ > 1 THEN
    // Divergence detected
    Restart with smaller time step or stronger damping
ENDIF
```

This mathematical formulation provides the foundation for CIDER's semiconductor device simulation, maintaining consistency with SPICE's DAE framework while extending it with detailed solid-state physics models. The convergence analysis ensures robust numerical solution even for challenging device structures and operating conditions.

----------

# C Implementation

## 1. Material Property System (mater.c / database.c)

### 1.1 Material Data Structure
The mathematical material models are implemented through the `Material` and `MaterialDB` structures:

```c
typedef struct {
    char name[64];          // Material name (Si, SiO2, GaAs, etc.)
    
    // Fundamental properties
    double epsilon;         // Dielectric constant (relative)
    double bandgap;         // Band gap at 300K (eV)
    double affinity;        // Electron affinity (eV)
    double density;         // Atomic density (cm⁻³)
    
    // Temperature coefficients
    double bandgapAlpha;    // α for Eg(T) = Eg(0) - αT²/(T+β)
    double bandgapBeta;     // β in Varshni formula
    double epsilonTC;       // Temperature coefficient of ε
    
    // Effective masses
    double m_e;             // Electron effective mass (m₀)
    double m_hh;            // Heavy hole effective mass
    double m_lh;            // Light hole effective mass
    
    // Lattice and thermal properties
    double latticeConstant; // Å
    double heatCapacity;    // J/(cm³·K)
    double thermalConductivity; // W/(cm·K)
    
    // Optical properties
    double refractiveIndex; // at reference wavelength
    double absorptionEdge;  // eV
    
    // Reference temperature
    double refTemperature;  // K (usually 300)
    
    // Mobility model pointers
    MobilityModel *electronMobility;
    MobilityModel *holeMobility;
    
    // Recombination parameters
    RecombinationModel *recombination;
} Material;

typedef struct {
    Material **materials;   // Array of material pointers
    int numMaterials;
    HashTable *nameToIndex; // Hash table for O(1) lookup
    Material *defaultMaterial; // Silicon as default
} MaterialDB;
```

**Mathematical Mapping**: The `Material` structure stores the parameters for the Slotboom band gap narrowing model `ΔE_g = q × [A × ln(N/N_0) + B × (ln(N/N_0))² + C × (ln(N/N_0))³]` through the `bandgapAlpha` and `bandgapBeta` fields (Varshni parameters). The temperature-dependent band gap `Eg(T) = Eg(0) - αT²/(T+β)` is implemented using these coefficients.

### 1.2 Material Database Functions
The material lookup system implements efficient parameter retrieval:

```c
Material *findMaterial(MaterialDB *db, const char *name) {
    // Hash table lookup
    int *idx = hashTableGet(db->nameToIndex, name);
    if (idx != NULL) {
        return db->materials[*idx];
    }
    
    // Case-insensitive fallback search
    char lowerName[64];
    strncpy(lowerName, name, 63);
    toLowercase(lowerName);
    
    for (int i = 0; i < db->numMaterials; i++) {
        char matLower[64];
        strncpy(matLower, db->materials[i]->name, 63);
        toLowercase(matLower);
        
        if (strcmp(matLower, lowerName) == 0) {
            // Add to hash table for future fast access
            int *newIdx = malloc(sizeof(int));
            *newIdx = i;
            hashTablePut(db->nameToIndex, name, newIdx);
            return db->materials[i];
        }
    }
    
    // Material not found, return default (Silicon)
    fprintf(stderr, "Warning: Material '%s' not found, using default Si\n", name);
    return db->defaultMaterial;
}

double getBandgap(Material *mat, double temperature) {
    // Varshni formula: Eg(T) = Eg(0) - αT²/(T+β)
    double T = temperature;
    double Eg0 = mat->bandgap + mat->bandgapAlpha * 300*300/(300 + mat->bandgapBeta);
    return Eg0 - mat->bandgapAlpha * T*T/(T + mat->bandgapBeta);
}

double getIntrinsicConcentration(Material *mat, double temperature) {
    // n_i² = N_c N_v exp(-Eg/kT)
    double Eg = getBandgap(mat, temperature);
    double kT = BOLTZMANN * temperature;
    
    // Effective density of states
    double N_c = 2.0 * pow(2.0 * M_PI * mat->m_e * ELECTRON_MASS * kT / (PLANCK*PLANCK), 1.5);
    double N_v = 2.0 * pow(2.0 * M_PI * mat->m_hh * ELECTRON_MASS * kT / (PLANCK*PLANCK), 1.5);
    
    return sqrt(N_c * N_v) * exp(-Eg / (2.0 * kT));
}
```

**Mathematical Mapping**: The `getBandgap()` function implements the Varshni temperature dependence `Eg(T) = Eg(0) - αT²/(T+β)`. The `getIntrinsicConcentration()` function implements the semiconductor statistics formula `n_i² = N_c N_v exp(-Eg/kT)` where `N_c` and `N_v` are the effective density of states in conduction and valence bands.

## 2. Mobility Models (mobil.c)

### 2.1 Mobility Model Structure
The Masetti and other mobility models are implemented through a unified structure:

```c
typedef enum {
    MOB_CONSTANT,
    MOB_MASETTI,
    MOB_ARORA,
    MOB_CAUGHEY_THOMAS,
    MOB_FIELD_DEPENDENT
} MobilityModelType;

typedef struct {
    MobilityModelType type;
    
    // Common parameters
    double mu_min;          // Minimum mobility
    double mu_max;          // Maximum mobility
    double refTemperature;  // Reference temperature (K)
    
    // Masetti model parameters
    double P_c;             // Critical doping for μ_min1 term
    double C_r;             // Reference concentration
    double C_s;             // Screening concentration
    double alpha;           // Exponent for (N/C_r) term
    double beta;            // Exponent for (C_s/N) term
    double mu_const;        // Constant mobility term
    double mu_min1;         // First minimum
    double mu_min2;         // Second minimum
    double mu_1;            // High-field parameter
    
    // Temperature dependence
    double gamma;           // Temperature exponent
    
    // Field-dependent mobility (for high fields)
    double vsat;            // Saturation velocity (cm/s)
    double beta_e;          // Field exponent
    double E_c;             // Critical field (V/cm)
} MobilityModel;
```

**Mathematical Mapping**: This structure stores all parameters for the Masetti mobility model `μ(N,T) = μ_min1 × exp(-P_c/N) + (μ_const - μ_min2)/(1 + (N/C_r)^α) - μ_1/(1 + (C_s/N)^β)` and its temperature dependence `μ(T) = μ(300K) × (T/300)^{-γ}`.

### 2.2 Mobility Calculation Functions
The mathematical mobility models are evaluated by:

```c
double calculateMobility(MobilityModel *model, double doping, 
                         double temperature, double electricField) {
    double mu = model->mu_max;
    double N = fabs(doping);  // Absolute doping concentration
    
    switch (model->type) {
        case MOB_CONSTANT:
            mu = model->mu_const;
            break;
            
        case MOB_MASETTI:
            // Masetti model: μ(N) = μ_min1 exp(-P_c/N) + 
            // (μ_const - μ_min2)/(1 + (N/C_r)^α) - μ_1/(1 + (C_s/N)^β)
            if (N > 0) {
                double term1 = model->mu_min1 * exp(-model->P_c / N);
                double term2 = (model->mu_const - model->mu_min2) / 
                               (1.0 + pow(N / model->C_r, model->alpha));
                double term3 = model->mu_1 / 
                               (1.0 + pow(model->C_s / N, model->beta));
                mu = term1 + term2 - term3;
            }
            break;
            
        case MOB_ARORA:
            // Arora model: μ(N) = μ_min + (μ_max - μ_min)/
            // (1 + (N/N_ref)^δ)
            mu = model->mu_min + (model->mu_max - model->mu_min) /
                  (1.0 + pow(N / model->C_r, model->alpha));
            break;
            
        case MOB_CAUGHEY_THOMAS:
            // Caughey-Thomas: μ(E) = μ_low / [1 + (μ_low E/v_sat)^β]^(1/β)
            if (electricField > 0) {
                double mu_low = calculateMobility(model, doping, temperature, 0);
                double ratio = mu_low * electricField / model->vsat;
                mu = mu_low / pow(1.0 + pow(ratio, model->beta_e), 1.0/model->beta_e);
            }
            break;
    }
    
    // Apply temperature dependence: μ(T) = μ(300K) × (T/300)^{-γ}
    if (temperature != model->refTemperature) {
        double T_ratio = temperature / model->refTemperature;
        mu *= pow(T_ratio, -model->gamma);
    }
    
    // Ensure mobility is within physical bounds
    if (mu < model->mu_min) mu = model->mu_min;
    if (mu > model->mu_max) mu = model->mu_max;
    
    return mu;
}
```

**Mathematical Mapping**: This function directly implements the Masetti formula with proper handling of the exponential term `exp(-P_c/N)`, power terms `(N/C_r)^α` and `(C_s/N)^β`, and temperature scaling `(T/300)^{-γ}`. The field-dependent Caughey-Thomas model implements `μ(E) = μ_low / [1 + (μ_low E/v_sat)^β]^(1/β)` for high-field velocity saturation effects.

## 3. Recombination Models (recomb.c)

### 3.1 Recombination Model Structure
The SRH, Auger, and radiative recombination models are implemented through:

```c
typedef enum {
    RECOMB_SRH,
    RECOMB_AUGER,
    RECOMB_RADIATIVE,
    RECOMB_SURFACE,
    RECOMB_IMPACT
} RecombinationType;

typedef struct {
    RecombinationType type;
    
    // SRH parameters
    double tau_n;           // Electron lifetime (s)
    double tau_p;           // Hole lifetime (s)
    double n1;              // SRH n1 parameter (cm⁻³)
    double p1;              // SRH p1 parameter (cm⁻³)
    
    // Auger coefficients
    double C_n;             // Electron Auger coefficient (cm⁶/s)
    double C_p;             // Hole Auger coefficient (cm⁶/s)
    
    // Radiative coefficient
    double B_rad;           // Radiative coefficient (cm³/s)
    
    // Trap properties (for SRH)
    double trapDensity;     // Trap density (cm⁻³)
    double trapEnergy;      // Trap energy from midgap (eV)
    double sigma_n;         // Electron capture cross section (cm²)
    double sigma_p;         // Hole capture cross section (cm²)
    
    // Temperature dependence
    double tau_n0;          // Reference lifetime at 300K
    double tau_p0;
    double activationEnergy; // For temperature dependence
} RecombinationModel;
```

**Mathematical Mapping**: This structure stores parameters for the SRH formula `R_SRH = (pn - n_i²)/[τ_p(n + n_1) + τ_n(p + p_1)]`, Auger formula `R_Auger = (C_n n + C_p p)(pn - n_i²)`, and radiative formula `R_rad = B_rad (pn - n_i²)`.

### 3.2 Recombination Calculation Functions
The recombination rates are computed by:

```c
double calculateRecombination(RecombinationModel *model, 
                             double n, double p, double n_i,
                             double temperature) {
    double R_total = 0.0;
    double np_minus_ni2 = n * p - n_i * n_i;
    
    if (np_minus_ni2 <= 0) {
        // Net generation, not recombination
        return 0.0;
    }
    
    // Apply temperature dependence to lifetimes
    double tau_n = model->tau_n;
    double tau_p = model->tau_p;
    if (temperature != 300.0) {
        double T_ratio = temperature / 300.0;
        // Simple Arrhenius-like temperature dependence
        tau_n = model->tau_n0 * exp(model->activationEnergy * 
                                   (1.0/temperature - 1.0/300.0) / BOLTZMANN);
        tau_p = model->tau_p0 * exp(model->activationEnergy * 
                                   (1.0/temperature - 1.0/300.0) / BOLTZMANN);
    }
    
    // Calculate SRH recombination
    if (model->type == RECOMB_SRH || model->type == RECOMB_SURFACE) {
        double denom = tau_p * (n + model->n1) + tau_n * (p + model->p1);
        if (denom > 0) {
            double R_srh = np_minus_ni2 / denom;
            R_total += R_srh;
        }
    }
    
    // Calculate Auger recombination
    if (model->type == RECOMB_AUGER) {
        double R_auger = (model->C_n * n + model->C_p * p) * np_minus_ni2;
        R_total += R_auger;
    }
    
    // Calculate radiative recombination
    if (model->type == RECOMB_RADIATIVE) {
        double R_rad = model->B_rad * np_minus_ni2;
        R_total += R_rad;
    }
    
    return R_total;
}

// Specialized SRH calculation with trap statistics
double calculateSRHWithTraps(RecombinationModel *model,
                            double n, double p, double n_i,
                            double temperature) {
    // Calculate trap occupation using Shockley-Read statistics
    double kT = BOLTZMANN * temperature;
    double E_i = kT * log(n_i);  // Intrinsic level
    
    // Trap energy relative to intrinsic level
    double E_t = E_i + model->trapEnergy;
    
    // n1 and p1 from trap statistics
    double n1 = n_i * exp((E_t - E_i) / kT);
    double p1 = n_i * exp((E_i - E_t) / kT);
    
    // Capture rates
    double c_n = model->sigma_n * sqrt(3.0 * kT / ELECTRON_MASS);
    double c_p = model->sigma_p * sqrt(3.0 * kT / ELECTRON_MASS);
    
    // SRH formula with detailed balance
    double numerator = n * p - n_i * n_i;
    double denom = (p + p1) / (model->trapDensity * c_n) + 
                   (n + n1) / (model->trapDensity * c_p);
    
    return numerator / denom;
}
```

**Mathematical Mapping**: The `calculateRecombination()` function implements the SRH formula with the denominator `τ_p(n + n_1) + τ_n(p + p_1)`. The `calculateSRHWithTraps()` function implements the more detailed SRH formula with trap parameters: `R = (np - n_i²)/[τ_p0(n + n_1) + τ_n0(p + p_1)]` where `n_1 = n_i exp((E_t - E_i)/kT)` and `p_1 = n_i exp((E_i - E_t)/kT)`.

## 4. Geometric Information System (geominfo.c)

### 4.1 Crystal Orientation Structure
For anisotropic materials like silicon, crystal orientation affects mobility:

```c
typedef struct {
    double direction[3];    // Crystal direction vector
    double normal[3];       // Surface normal vector
    
    // Anisotropic mobility tensor (for materials like Si)
    double mobilityTensor[3][3];  // μ_ij in crystal coordinates
    
    // Surface recombination velocities
    double s_n;             // Electron surface recombination (cm/s)
    double s_p;             // Hole surface recombination (cm/s)
    
    // Interface trap density
    double D_it;            // Interface trap density (cm⁻²·eV⁻¹)
    double phi_ms;          // Metal-semiconductor work function difference
} CrystalOrientation;
```

**Mathematical Mapping**: The mobility tensor `μ_ij` implements anisotropic mobility where `J_i = q Σ_j μ_ij n E_j`. For silicon, the mobility differs along <100>, <110>, and <111> crystal directions.

### 4.2 Orientation-Dependent Mobility
```c
double getAnisotropicMobility(CrystalOrientation *orient,
                             double electricField[3],
                             MobilityModel *model,
                             double doping, double temperature) {
    // Get isotropic mobility from model
    double E_mag = sqrt(electricField[0]*electricField[0] +
                       electricField[1]*electricField[1] +
                       electricField[2]*electricField[2]);
    double mu_iso = calculateMobility(model, doping, temperature, E_mag);
    
    // Transform to crystal coordinates
    double E_crystal[3];
    transformToCrystalCoordinates(orient, electricField, E_crystal);
    
    // Calculate mobility along field direction in crystal coordinates
    double mu_eff = 0.0;
    double E2_total = 0.0;
    
    for (int i = 0; i < 3; i++) {
        for (int j = 0; j < 3; j++) {
            mu_eff += E_crystal[i] * orient->mobilityTensor[i][j] * E_crystal[j];
        }
        E2_total += E_crystal[i] * E_crystal[i];
    }
    
    if (E2_total > 0) {
        mu_eff /= E2_total;
    } else {
        mu_eff = mu_iso;  // Use isotropic value for zero field
    }
    
    return mu_eff;
}
```

**Mathematical Mapping**: This implements the anisotropic mobility calculation `μ_eff = (Σ_i Σ_j E_i μ_ij E_j)/(Σ_i E_i²)` which reduces to the scalar mobility when `μ_ij = μ δ_ij` (isotropic case).

## 5. Integration Methods (integset.c / integuse.c)

### 5.1 Integration Control Structure
Numerical integration of carrier statistics and recombination integrals:

```c
typedef struct {
    int method;             // Integration method
    double absTol;          // Absolute tolerance
    double relTol;          // Relative tolerance
    int maxEvals;           // Maximum function evaluations
    int minIntervals;       // Minimum number of intervals
    int maxIntervals;       // Maximum number of intervals
    
    // For adaptive integration
    double *points;         // Integration points
    double *weights;        // Integration weights
    int numPoints;          // Number of points
    
    // Error estimation
    double errorEstimate;
    int evaluationsUsed;
} IntegrationControl;
```

### 5.2 Carrier Statistics Integration
Integration of Fermi-Dirac statistics for degenerate semiconductors:

```c
double integrateCarrierDensity(double E_c, double E_v,
                              double E_f, double temperature,
                              IntegrationControl *control) {
    // Integrate density of states × Fermi function
    // n = ∫ g_c(E) f(E) dE, p = ∫ g_v(E) [1 - f(E)] dE
    
    double kT = BOLTZMANN * temperature;
    double eta = (E_f - E_c) / kT;  // Normalized Fermi level
    
    if (eta < -20) {
        // Non-degenerate approximation: n = N_c exp(η)
        double N_c = 2.0 * pow(2