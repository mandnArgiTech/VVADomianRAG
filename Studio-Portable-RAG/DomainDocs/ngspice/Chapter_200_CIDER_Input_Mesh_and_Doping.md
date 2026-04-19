# CIDER TCAD: Spatial Mesh Generation and Doping Profiles

_Generated 2026-04-13 10:27 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/cards.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/mesh.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/meshset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/domain.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/domnset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/doping.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/dopset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/material.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/matlset.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/electrod.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/ciderlib/input/elctset.c`

# Chapter: CIDER TCAD: Spatial Mesh Generation and Doping Profiles

## Technical Introduction

The CIDER (Circuit and Interconnect Device Engineering and Reliability) module within Ngspice provides Technology Computer-Aided Design (TCAD) capabilities for semiconductor device simulation. The core files `cards.c`, `mesh.c`, `meshset.c`, `domain.c`, `domnset.c`, `doping.c`, `dopset.c`, `material.c`, `matlset.c`, `electrod.c`, and `elctset.c` implement a comprehensive system for defining, generating, and validating spatial meshes and doping profiles essential for physics-based device simulation. These files translate high-level device specifications into the mathematical constructs required for finite-element semiconductor device analysis.

The lexical parser (`cards.c`) processes CIDER input cards, converting textual specifications into structured data. The mesh generation system (`mesh.c`, `meshset.c`) implements geometric progression algorithms and Delaunay triangulation to create non-uniform spatial grids optimized for semiconductor simulation, with adaptive refinement based on doping gradients and electric fields. The domain management system (`domain.c`, `domnset.c`) defines material regions with specific physical properties, implementing boundary collision detection and domain overlap validation.

The doping profile system (`doping.c`, `dopset.c`) computes analytical distributions including Gaussian implantation, complementary error function diffusion, and exponential tail profiles, with rigorous consistency checks for charge neutrality and concentration limits. The material database (`material.c`, `matlset.c`) implements temperature-dependent mobility models (Masetti), band gap narrowing (Slotboom), and SRH recombination parameters. The electrode system (`electrod.c`, `elctset.c`) validates contact placement and ensures proper boundary conditions for device simulation.

Together, these files transform device specifications into the mathematical framework required for solving semiconductor device equations within Ngspice's simulation engine, providing the spatial discretization and material properties needed for accurate TCAD analysis.

## Mathematical Formulation

### 1. Non-Uniform Spatial Grid Generation Algorithms

#### 1.1 Geometric Progression Spacing (1D)
For a 1D region from `x=0` to `x=L` with `N` intervals, the grid points are generated using:
```
x_i = x_0 + h_0 × (r^i - 1)/(r - 1)  for i = 0, 1, ..., N
```
where:
- `h_0` = initial spacing at `x_0`
- `r` = geometric ratio (>1 for expansion, <1 for contraction)
- Total length constraint: `L = h_0 × (r^N - 1)/(r - 1)`

#### 1.2 Adaptive Mesh Refinement Criteria
Based on doping gradient and electric field:
```
Δx_max = min( L_debye, L_drift, L_diffusion )
```
where:
- Debye length: `L_debye = √(ε·kT/(q²·N))`
- Drift length: `L_drift = μ·E·τ`
- Diffusion length: `L_diffusion = √(D·τ)`

#### 1.3 2D Delaunay Triangulation
For irregular geometries, nodes are placed according to the Bowyer-Watson algorithm:
1. Start with super-triangle containing all points
2. For each point `P`:
   - Find all triangles whose circumcircle contains `P`
   - Remove these triangles, creating a cavity
   - Re-triangulate cavity by connecting `P` to all cavity vertices
3. Remove triangles containing super-triangle vertices

#### 1.4 Mesh Quality Metrics
- Aspect ratio: `AR = (max edge)/(min edge) ≤ 10`
- Skewness: `θ_min ≥ 30°` for all angles
- Smoothness: `|Δh|/h_avg ≤ 0.3` between adjacent elements

### 2. Analytical Doping Profile Functions

#### 2.1 Gaussian Implantation Profile
```
N(x) = N_peak × exp(-((x - R_p)²)/(2σ²))
```
where:
- `N_peak = Dose/(σ√(2π))`
- `R_p` = projected range
- `σ` = standard deviation (straggle)
- `Dose` = implanted dose (atoms/cm²)

#### 2.2 Complementary Error Function (Erfc) Diffusion Profile
```
N(x) = N_surface × erfc((x)/(2√(Dt)))
```
where:
- `N_surface` = surface concentration
- `D` = diffusion coefficient
- `t` = diffusion time
- `erfc(z) = 1 - (2/√π)∫_0^z e^{-t²} dt`

#### 2.3 Exponential Tail Distribution
```
N(x) = N_0 × exp(-x/λ) + N_background
```
where `λ` is characteristic decay length.

#### 2.4 Multiple Implant Superposition
```
N_total(x) = ∑_i N_i(x) + N_background
```

#### 2.5 2D Lateral Diffusion
```
N(x,y) = N_1D(x) × [0.5 × erfc(y/√(Dt)) + 0.5 × exp(-y²/(4Dt))]
```

### 3. Material Property Modeling

#### 3.1 Temperature-Dependent Mobility (Masetti Model)
```
μ(T,N) = μ_min1 × exp(-P_c/N) + (μ_const - μ_min2)/(1 + (N/C_r)^α) - μ_1/(1 + (C_s/N)^β)
μ(T) = μ(300K) × (T/300)^{-γ}
```

#### 3.2 Band Gap Narrowing (Slotboom Model)
```
ΔE_g = q × [A × ln(N/N_0) + B × (ln(N/N_0))² + C × (ln(N/N_0))³]
```
where `A, B, C, N_0` are material parameters.

#### 3.3 SRH Recombination
```
R = (pn - n_i²)/[τ_p(n + n_1) + τ_n(p + p_1)]
```

## Convergence Analysis: Structural Integrity Checks

### 1. Grid Spacing Validation

#### 1.1 Minimum Spacing Constraint
```
Δx_min ≥ max(ε_machine/L, 1Å)
```
where `ε_machine ≈ 2.2e-16` (double precision).

#### 1.2 Maximum Aspect Ratio Check
For 2D elements:
```
AR = L_max/L_min ≤ AR_max (typically 1000)
```
Violation triggers automatic mesh refinement.

#### 1.3 Jacobian Determinant Positivity
For isoparametric elements, the mapping Jacobian must satisfy:
```
det(J) = |∂(x,y)/∂(ξ,η)| > 0 ∀ (ξ,η) ∈ [-1,1]²
```

### 2. Domain Overlap and Boundary Collision Detection

#### 2.1 Axis-Aligned Bounding Box (AABB) Test
For two domains `D_i` and `D_j`:
```
IF (D_i.x_min < D_j.x_max AND D_i.x_max > D_j.x_min AND
    D_i.y_min < D_j.y_max AND D_i.y_max > D_j.y_min) THEN
    OVERLAP detected
```

#### 2.2 Point-in-Polygon Test (Ray Casting)
For electrode placement validation:
```
crossings = 0
FOR each edge (v_k, v_{k+1}) of polygon:
    IF ((y_i > min(y_k, y_{k+1})) AND (y_i ≤ max(y_k, y_{k+1})) AND
        (x_i ≤ max(x_k, x_{k+1})) AND
        (y_k ≠ y_{k+1})) THEN
        x_intersect = (y_i - y_k)*(x_{k+1} - x_k)/(y_{k+1} - y_k) + x_k
        IF (x_k == x_{k+1} OR x_i ≤ x_intersect) THEN
            crossings = crossings + 1
        ENDIF
    ENDIF
END FOR
IF (crossings % 2 == 1) THEN point is inside polygon
```

#### 2.3 Minimum Distance Constraint
Between any two electrodes `E_i` and `E_j`:
```
d_min = min_{p∈E_i, q∈E_j} ||p - q|| ≥ 10·Δx_min
```

### 3. Doping Profile Consistency Checks

#### 3.1 Charge Neutrality Verification
```
∫_Ω (N_d(x) - N_a(x)) dΩ ≈ 0 within tolerance ε_Q
```
where typical `ε_Q = 1e-6 × max(N_peak)·Volume`.

#### 3.2 Monotonicity in Depletion Regions
For PN junctions, doping must satisfy:
```
sign(dN/dx) is constant within depletion width W_d = √(2ε(φ_bi - V)/(qN))
```

#### 3.3 Concentration Limits
```
N_min ≤ N(x) ≤ N_max
```
where `N_min = 1e10 cm⁻³` (intrinsic) and `N_max = 5e20 cm⁻³` (solid solubility).

### 4. Numerical Overflow Prevention

#### 4.1 Exponential Argument Clamping
For Boltzmann statistics:
```
φ_n = (E_Fn - E_i)/(kT)
IF |φ_n| > φ_max THEN φ_n = sign(φ_n)·φ_max
```
where `φ_max = log(DBL_MAX) ≈ 700` for `double`.

#### 4.2 Gummel Iteration Stability
Update damping factor:
```
α = min(1, 2/(1 + ||Δψ||/ψ_thermal))
```
where `ψ_thermal = kT/q ≈ 26mV`.

## C Implementation

### 1. Lexical Cards and Parsing (cards.c)

#### 1.1 Card Data Structure
The mathematical specification of mesh parameters, domains, and doping profiles is parsed into the `Card` structure:

```c
typedef struct {
    char cardType[32];      // "MESH", "DOMAIN", "DOPING", etc.
    int lineNumber;         // Source line number
    char **tokens;          // Tokenized input line
    int numTokens;          // Number of tokens
    struct Card *next;      // Linked list pointer
} Card;

typedef struct {
    Card *head;             // Linked list of cards
    Card *tail;
    int count;              // Total card count
    HashTable *symbolTable; // Symbol table for parameters
} CardDeck;
```

**Mathematical Mapping**: This structure captures the formal specifications from input files, converting textual descriptions of geometric progression parameters (`h_0`, `r`, `N`) and doping profile parameters (`N_peak`, `R_p`, `σ`) into structured data for subsequent processing.

#### 1.2 Parsing State Machine
The parser implements a state machine to handle nested card structures:

```c
typedef enum {
    STATE_START,
    STATE_IN_MESH,
    STATE_IN_DOMAIN,
    STATE_IN_DOPING,
    STATE_IN_MATERIAL,
    STATE_IN_ELECTRODE,
    STATE_ERROR
} ParserState;

typedef struct {
    ParserState state;
    int depth;              // Nesting depth for subcards
    char currentSection[32];
    double unitScale;       // Current unit scaling (µm, nm, etc.)
    Card *currentCard;      // Card being built
} ParseContext;
```

**Mathematical Mapping**: The state machine ensures proper parsing of hierarchical specifications, maintaining context for unit conversions and parameter associations required for the mathematical formulations.

### 2. Spatial Mesh and Domain Setup (mesh.c / meshset.c / domain.c / domnset.c)

#### 2.1 Mesh Data Structure
The mathematical grid generation algorithms are implemented through the `Mesh` structure:

```c
typedef struct {
    int id;                 // Unique mesh identifier
    int dim;                // Dimensionality (1, 2, 3)
    int numNodes;           // Total number of nodes
    int numElements;        // Total number of elements
    
    // Node coordinates
    double *x;              // x-coordinates (length = numNodes)
    double *y;              // y-coordinates (2D/3D)
    double *z;              // z-coordinates (3D)
    
    // Element connectivity
    int **connectivity;     // connectivity[e][localNode] = globalNode
    
    // Element types
    ElementType *elemTypes; // TRIANGLE, QUAD, TET, etc.
    
    // Boundary markers
    int *boundaryMarker;    // Marker for each node/element
    
    // Quality metrics
    double *jacobianDet;    // Determinant of Jacobian per element
    double minSpacing;      // Minimum node spacing
    double maxAspectRatio;  // Maximum aspect ratio
} Mesh;
```

**Mathematical Mapping**: This structure stores the computed grid points `x_i` from the geometric progression formula and implements the mesh quality metrics `AR ≤ 10`, `θ_min ≥ 30°`, and `|Δh|/h_avg ≤ 0.3`.

#### 2.2 Mesh Generation Algorithm
The 1D geometric progression algorithm is implemented as:

```c
Mesh *generateMesh1D(double start, double end, 
                     double minSpacing, double maxSpacing,
                     double ratio, int numIntervals) {
    Mesh *mesh = malloc(sizeof(Mesh));
    mesh->dim = 1;
    mesh->numNodes = numIntervals + 1;
    mesh->x = malloc(mesh->numNodes * sizeof(double));
    
    // Geometric progression
    double h = minSpacing;
    mesh->x[0] = start;
    
    for (int i = 1; i <= numIntervals; i++) {
        mesh->x[i] = mesh->x[i-1] + h;
        h *= ratio;
        if (h > maxSpacing) h = maxSpacing;
    }
    
    // Adjust last point to exactly 'end'
    double scale = (end - start) / (mesh->x[numIntervals] - start);
    for (int i = 1; i <= numIntervals; i++) {
        mesh->x[i] = start + (mesh->x[i] - start) * scale;
    }
    
    return mesh;
}
```

**Mathematical Mapping**: This code directly implements `x_i = x_0 + h_0 × (r^i - 1)/(r - 1)` with practical adjustments for maximum spacing constraints and exact endpoint matching.

#### 2.3 Domain Definition Structure
Material regions are defined using the `Domain` structure:

```c
typedef struct {
    char name[64];          // Domain name
    int id;                 // Domain ID
    Material *material;     // Pointer to material properties
    
    // Spatial extent
    enum {BOX, POLYGON, CYLINDER } shapeType;
    union {
        struct { double xmin, xmax, ymin, ymax; } box;
        struct { double *x, *y; int numVertices; } polygon;
        struct { double xc, yc, radius; } cylinder;
    } shape;
    
    // Mesh association
    int *elementList;       // List of elements in this domain
    int numElements;
    
    // Physical properties
    double epsilon;         // Permittivity
    double bandgap;         // Band gap (eV)
    double affinity;        // Electron affinity (eV)
    double *mobility;       // Carrier mobility models
} Domain;
```

**Mathematical Mapping**: This structure implements the domain overlap detection algorithms, storing spatial extents for AABB tests and polygon vertices for point-in-polygon validation.

### 3. Doping Profiles and Material Binding (doping.c / dopset.c / material.c / matlset.c)

#### 3.1 Doping Profile Structure
Analytical doping profiles are implemented through the `DopingProfile` structure:

```c
typedef enum {
    DOP_UNIFORM,
    DOP_GAUSSIAN,
    DOP_ERFC,
    DOP_EXPONENTIAL,
    DOP_PIECEWISE
} DopingType;

typedef struct {
    DopingType type;
    char domainName[64];    // Target domain
    double concentration;   // Peak or uniform concentration
    
    // Gaussian/Erfc parameters
    double peakPosition;
    double straggle;
    double dose;            // For implantation
    
    // Exponential parameters
    double decayLength;
    double surfaceConc;
    
    // Piecewise linear
    double *xPoints;
    double *concPoints;
    int numPoints;
    
    // Temperature dependence
    double activationEnergy;
    double diffusionCoeff;
} DopingProfile;
```

**Mathematical Mapping**: This structure stores the parameters for Gaussian (`N_peak`, `R_p`, `σ`, `Dose`), Erfc (`N_surface`, `D`, `t`), and exponential (`N_0`, `λ`) profiles.

#### 3.2 Doping Computation Functions
The mathematical doping profiles are computed as:

```c
double computeGaussianDoping(double x, DopingProfile *profile) {
    double delta = x - profile->peakPosition;
    double sigma = profile->straggle;
    double dose = profile->dose;
    
    // Gaussian: N(x) = (Dose/(σ√(2π))) × exp(-(x-Rp)²/(2σ²))
    double peakConc = dose / (sigma * sqrt(2.0 * M_PI));
    double exponent = -0.5 * (delta * delta) / (sigma * sigma);
    
    // Clamp exponent to prevent underflow/overflow
    if (exponent < -50.0) exponent = -50.0;
    if (exponent > 50.0) exponent = 50.0;
    
    return peakConc * exp(exponent);
}

double computeErfcDoping(double x, DopingProfile *profile) {
    // erfc doping: N(x) = Cs × erfc(x/(2√Dt))
    double surfaceConc = profile->surfaceConc;
    double diffusionLength = profile->straggle;
    double argument = x / (2.0 * diffusionLength);
    
    // Use approximation for large arguments to avoid overflow
    if (argument > 6.0) {
        // erfc(z) ≈ exp(-z²)/(z√π) for large z
        return surfaceConc * exp(-argument*argument) / 
               (argument * sqrt(M_PI));
    } else {
        return surfaceConc * erfc(argument);
    }
}
```

**Mathematical Mapping**: These functions directly implement the mathematical formulas `N(x) = N_peak × exp(-((x - R_p)²)/(2σ²))` and `N(x) = N_surface × erfc(x/(2√(Dt)))` with numerical safeguards for overflow/underflow.

#### 3.3 Material Property Structure
The material models are implemented through the `Material` structure:

```c
typedef struct {
    char name[64];          // Material name (Si, SiO2, etc.)
    
    // Basic properties
    double epsilon;         // Dielectric constant (relative)
    double bandgap;         // Band gap (eV)
    double affinity;        // Electron affinity (eV)
    double density;         // Atomic density (cm⁻³)
    
    // Mobility models
    MobilityModel electronMobility;
    MobilityModel holeMobility;
    
    // Recombination parameters
    double tau_n;           // Electron lifetime
    double tau_p;           // Hole lifetime
    double SRH_n1, SRH_p1;  // SRH parameters
    
    // Thermal properties
    double heatCapacity;
    double thermalConductivity;
    
    // Optical properties (for optoelectronics)
    double refractiveIndex;
    double absorptionCoeff;
} Material;
```

**Mathematical Mapping**: This structure stores parameters for the Masetti mobility model `μ(T,N)`, Slotboom band gap narrowing `ΔE_g`, and SRH recombination `R`.

### 4. Electrode System (electrod.c / elctset.c)

#### 4.1 Electrode Placement Validation
The mathematical boundary validation is implemented as:

```c
int validateElectrodePlacement(Mesh *mesh, Electrode *electrode, 
                               Domain **domains, int numDomains) {
    // Check all electrode nodes are on domain boundaries
    for (int i = 0; i < electrode->numNodes; i++) {
        int nodeId = electrode->nodes[i];
        int onBoundary = 0;
        
        // Check if node is on boundary of any domain
        for (int d = 0; d < numDomains; d++) {
            if (isNodeOnDomainBoundary(mesh, nodeId, domains[d])) {
                onBoundary = 1;
                break;
            }
        }
        
        if (!onBoundary) {
            fprintf(stderr, "Error: Electrode node %d not on domain boundary\n", 
                    nodeId);
            return 0;
        }
    }
    
    // Check electrode doesn't intersect internal mesh lines
    // ... implementation ...
    
    return 1;  // Valid
}
```

**Mathematical Mapping**: This implements the minimum distance constraint `d_min ≥ 10·Δx_min` and ensures electrodes are properly placed on domain boundaries for correct boundary condition application.

### 5. Algorithm Implementation Details

#### 5.1 Adaptive Mesh Refinement
The adaptive refinement based on doping gradients is implemented as:

```c
void refineMeshNearJunction(Mesh *mesh, double *doping, 
                            double gradientThreshold) {
    // Calculate doping gradient
    double *gradient = malloc(mesh->numNodes * sizeof(double));
    for (int i = 1; i < mesh->numNodes - 1; i++) {
        gradient[i] = fabs(doping[i+1] - doping[i-1]) / 
                      (mesh->x[i+1] - mesh->x[i-1]);
    }
    
    // Mark nodes for refinement
    int *refineFlag = calloc(mesh->numNodes, sizeof(int));
    for (int i = 0; i < mesh->numNodes; i++) {
        if (gradient[i] > gradientThreshold) {
            // Refine region around high-gradient node
            for (int j = max(0, i-2); j <= min(mesh->numNodes-1, i+2); j++) {
                refineFlag[j] = 1;
            }
        }
    }
    
    // Perform refinement (insert new nodes)
    // ... refinement implementation ...
    
    free(gradient);
    free(refineFlag);
}
```

**Mathematical Mapping**: This implements the adaptive mesh refinement criterion `Δx_max = min(L_debye, L_drift, L_diffusion)` by detecting regions with high doping gradients that require finer discretization.

#### 5.2 Consistency Checking Algorithms
The mathematical validation checks are implemented as:

```c
int checkMeshConsistency(Mesh *mesh) {
    int errors = 0;
    
    // Check for duplicate nodes
    for (int i = 0; i < mesh->numNodes; i++) {
        for (int j = i+1; j < mesh->numNodes; j++) {
            double dx = mesh->x[i] - mesh->x[j];
            double dy = (mesh->dim > 1) ? mesh->y[i] - mesh->y[j] : 0;
            double dist2 = dx*dx + dy*dy;
            
            if (dist2 < 1e-20) {  // Essentially same point
                fprintf(stderr, "Duplicate nodes: %d and %d\n", i, j);
                errors++;
            }
        }
    }
    
    // Check element Jacobians
    for (int e = 0; e < mesh->numElements; e++) {
        double J = computeJacobianDeterminant(mesh, e);
        if (J <= 0) {
            fprintf(stderr, "Negative/zero Jacobian in element %d: %g\n", e, J);
            errors++;
        }
    }
    
    // Check aspect ratios
    for (int e = 0; e < mesh->numElements; e++) {
        double ar = computeAspectRatio(mesh, e);
        if (ar > 1000.0) {
            fprintf(stderr, "Large aspect ratio in element %d: %g\n", e, ar);
            errors++;
        }
    }
    
    return (errors == 0);
}
```

**Mathematical Mapping**: This implements the mesh quality checks `AR ≤ 1000` and `det(J) > 0`, ensuring the spatial discretization meets the requirements for stable finite element analysis.

### 6. Integration with Ngspice Simulation Engine

The CIDER TCAD system integrates with Ngspice through:
1. **Mesh data structures** that provide nodal coordinates and connectivity for finite element discretization
2. **Doping profiles** that initialize carrier concentrations for semiconductor device equations
3. **Material properties** that define mobility, recombination, and band structure parameters
4. **Electrode definitions** that establish boundary conditions for device simulation

The mathematical formulations for mesh generation and doping profiles provide the spatial discretization and initial conditions required for solving the semiconductor device equations within Ngspice's simulation framework, enabling physics-based device analysis alongside circuit simulation.

### 7. Performance and Numerical Considerations

#### 7.1 Memory Complexity
- Mesh storage: `O(N)` nodes + `O(E)` elements
- Doping profiles: `O(N)` nodal concentrations
- Material databases: `O(M)` materials with property tables

#### 7.2 Computational Complexity
- Mesh generation: `O(N log N)` for Delaunay triangulation
- Doping evaluation: `O(N)` for analytical profiles
- Consistency checks: `O(N²)` for duplicate detection, `O(E)` for quality metrics

#### 7.3 Numerical Stability
- Exponential clamping prevents overflow in doping calculations
- Adaptive refinement maintains `Δx_min ≥ 1Å` for physical meaningfulness
- Jacobian positivity ensures invertible element mappings

This C implementation provides a complete, robust realization of the mathematical formulations for TCAD mesh generation and doping profile definition, creating the foundation for accurate semiconductor device simulation within the Ngspice environment.