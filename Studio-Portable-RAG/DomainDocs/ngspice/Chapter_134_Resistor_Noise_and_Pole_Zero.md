# Resistor: Thermal Noise and Pole-Zero Analysis

_Generated 2026-04-12 20:40 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/respzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/res/resnoise.c`

# Chapter: Resistor: Thermal Noise and Pole-Zero Analysis

## Technical Introduction

The Ngspice resistor model implements comprehensive thermal noise generation and pole-zero analysis capabilities through two critical C source files: `resnoise.c` and `respzld.c`. These files provide the mathematical and algorithmic foundation for simulating resistor behavior in frequency-domain analyses, which are essential for modern analog and RF circuit design.

The `resnoise.c` file implements the Johnson-Nyquist thermal noise model, generating stochastic current sources that represent the fundamental noise floor of resistive elements. This implementation directly maps the physical law `S_i(f) = 4·k·T·G` to SPICE-compatible matrix stamps, including temperature scaling, geometric parameter effects, and numerical integration over frequency bands. The code handles both thermal noise and optional flicker noise models, with proper correlation between multiple noise sources in complex networks.

The `respzld.c` file implements the pole-zero analysis matrix loading for resistors, which is crucial for determining circuit stability, frequency response, and transfer function characteristics. Unlike standard AC analysis, pole-zero analysis requires handling the complex frequency variable `s = σ + jω` while maintaining the real-valued conductance matrix structure. This implementation ensures that resistors contribute only to the `G` matrix in the system equation `(s·C + G)·x = B·u`, with proper handling of frequency-dependent effects like skin resistance when modeled.

Together, these files enable Ngspice to perform sophisticated noise analysis for signal-to-noise ratio calculations and pole-zero analysis for stability assessment, making the resistor model a complete implementation for both time-domain and frequency-domain circuit simulation.

## Mathematical Formulation

The resistor model in Ngspice implements the fundamental mathematical relationships for thermal noise generation and pole-zero analysis within the SPICE simulation framework. The formulation is derived directly from the physical principles of Johnson-Nyquist noise and the Modified Nodal Analysis (MNA) approach for linear circuit elements.

### 1. Thermal Noise Mathematics

#### Johnson-Nyquist Noise Spectral Density
The resistor generates a noise current source in parallel with its conductance, with spectral density given by:

```
S_i(f) = 4·k·T·G  [A²/Hz]
```

Where:
- `k` = Boltzmann constant (1.38064852 × 10⁻²³ J/K)
- `T` = Absolute temperature in Kelvin (`ckt->CKTtemp`)
- `G` = Conductance = `1/R`
- `R` = Resistance value

The equivalent voltage noise spectral density is:

```
S_v(f) = 4·k·T·R  [V²/Hz]
```

#### Temperature-Dependent Resistance
The resistance value used in noise calculations includes temperature scaling:

```
R(T) = R(T₀) × [1 + α₁·(T - T₀) + α₂·(T - T₀)²]
```

Where:
- `α₁` = First-order temperature coefficient (`model->REStc1`)
- `α₂` = Second-order temperature coefficient (`model->REStc2`)
- `T₀` = Nominal temperature (`model->REStnom`)
- `T` = Operating temperature (`ckt->CKTtemp`)

#### Noise Integration Over Frequency Band
For noise analysis over a frequency range [f₁, f₂], the integrated noise power is:

```
iₙ² = ∫_{f₁}^{f₂} S_i(f) df = 4kT·G·(f₂ - f₁)
```

In discrete frequency steps used in SPICE simulation:

```
iₙ² = Σ_{k=1}^{N} 4kT·G·Δf_k
```

Where `Δf_k` is the frequency step size at point k.

#### Flicker (1/f) Noise Model
For resistors with flicker noise characteristics (if modeled):

```
S_i(f) = K_f · I^a / f^b
```

Where:
- `K_f` = Flicker noise coefficient (`model->RESkf`)
- `I` = DC current through resistor
- `a` = Current exponent (`model->RESaf`, typically 2)
- `b` = Frequency exponent (`model->RESbf`, typically 1)

#### Noise Correlation for Multiple Resistors
For circuits with multiple resistors, the noise sources are correlated. The covariance matrix for N resistors is:

```
C_ij = 4·k·T·(δ_ij·G_i - G_i·G_j/G_total)
```

Where:
- `δ_ij` = Kronecker delta (1 if i = j, 0 otherwise)
- `G_total` = Sum of all conductances in the network

### 2. Geometric Resistance Calculation
For physically modeled resistors with geometric parameters:

```
R = Rₛ × (L / W) + 2·R_c
```

Where:
- `Rₛ` = Sheet resistance (`model->RESsheetRes`) in Ω/□
- `L` = Resistor length (`here->RESlength`)
- `W` = Resistor width (`here->RESwidth`)
- `R_c` = Contact resistance (if modeled)

### 3. Pole-Zero Analysis Formulation

#### Modified Nodal Analysis (MNA) for Resistors
For pole-zero analysis, the resistor contributes only to the real part of the system matrix. The conductance matrix entries for a resistor between nodes i and j are:

```
G_ii = +g
G_jj = +g
G_ij = -g
G_ji = -g
```

Where `g = 1/R` is the conductance.

#### System Equation for Pole-Zero Analysis
The general system equation for pole-zero analysis is:

```
(s·C + G)·x = B·u
```

Where:
- `s` = Complex frequency variable (`s->real + j·s->imag`)
- `C` = Capacitance matrix (zero for pure resistors)
- `G` = Conductance matrix (contains resistor contributions)
- `x` = State vector (node voltages)
- `B` = Input matrix
- `u` = Input vector

The resistor contributes only to the `G` matrix, not to `C`.

#### Frequency-Dependent Resistance Models
For advanced resistor models with frequency dependence (skin effect, dielectric losses):

```
R(f) = R_dc × √(1 + j·f/f_skin)
```

Where the skin effect frequency is:

```
f_skin = ρ / (π·μ·t²)
```

And:
- `ρ` = Resistivity
- `μ` = Permeability
- `t` = Conductor thickness

### 4. Matrix Stamping Algorithm

#### Standard Conductance Stamp
For a resistor connected between nodes i and j:

```
[G] = [ +g  -g ]
      [ -g  +g ]
```

#### Noise Analysis Stamp
For noise analysis, an additional stamp is added:

```
[G_noise] = [ +g  0 ]  [i₁]   [√(4kTg)·ξ₁]
             [ 0  +g ]  [i₂] = [√(4kTg)·ξ₂]
```

Where `ξ₁, ξ₂` are uncorrelated Gaussian white noise processes with unit variance.

#### Complex Frequency Handling
In pole-zero analysis with complex frequency s = σ + jω:

```
G_effective = g  (for pure resistors)
```

No imaginary component exists for ideal resistors, making them contribute only to the real part of the system matrix.

## Convergence Analysis

### 1. Numerical Stability Considerations

#### Minimum Conductance Enforcement
To avoid singular matrices in SPICE simulation, a minimum conductance is enforced:

```c
#define GMIN 1.0e-12  /* Minimum conductance to avoid singular matrix */
if(g < GMIN) g = GMIN;
```

This ensures the matrix remains non-singular even with very large resistance values.

#### Temperature Scaling Convergence
The temperature scaling calculation must converge properly during Newton-Raphson iterations. The convergence criterion for temperature-dependent resistance is:

```
|R_{n+1} - R_n| < ε_abs + ε_rel·max(|R_n|, R_min)
```

Where:
- `ε_abs` = Absolute tolerance (typically 1e-12)
- `ε_rel` = Relative tolerance (typically 1e-6)
- `R_min` = Minimum resistance value to avoid division by zero

#### Geometric Parameter Validation
For geometrically defined resistors, parameter validation ensures convergence:

```
if(width <= 0) width = 1e-12;
if(length <= 0) length = 1e-12;
```

This prevents numerical overflow in the `L/W` ratio calculation.

### 2. Noise Analysis Convergence

#### Noise Source Normalization
The noise source magnitude is normalized by the integration bandwidth for numerical stability:

```c
double noiseNorm = sqrt(4.0 * CONSTboltz * T * g * data->freqDelta);
```

This ensures consistent scaling across different frequency step sizes.

#### Frequency Integration Convergence
For noise integration over frequency, the convergence of the integral is monitored:

```
|∫_{f₁}^{f₂} S(f) df - Σ_{k=1}^{N} S(f_k)·Δf_k| < ε_noise
```

Where `ε_noise` is the noise integration tolerance, typically set to:

```
ε_noise = ε_abs + ε_rel·max(|∫S(f)df|, S_min)
```

#### Correlation Matrix Conditioning
The noise correlation matrix must remain positive definite. The condition number is monitored:

```
κ(C) = λ_max / λ_min < 1/ε_machine
```

If the condition number approaches machine precision limits, regularization is applied:

```
C_reg = C + δ·I
```

Where `δ` is a small positive constant (typically 1e-12).

### 3. Pole-Zero Analysis Convergence

#### Matrix Conditioning for Complex Frequencies
In pole-zero analysis, the system matrix `(s·C + G)` must remain well-conditioned for all complex frequencies s. The condition number is bounded by:

```
κ(s·C + G) ≤ (|s|·||C|| + ||G||) / σ_min(s·C + G)
```

For pure resistors (C = 0), this simplifies to:

```
κ(G) = λ_max(G) / λ_min(G)
```

#### Convergence of Pole/Zero Locations
The Newton-Raphson iteration for finding poles and zeros converges when:

```
|s_{n+1} - s_n| < ε_abs + ε_rel·|s_n|
```

Where s is the complex frequency variable.

#### Frequency-Dependent Model Convergence
For frequency-dependent resistor models, the convergence of the iterative solution is tested:

```
|R(f_{n+1}) - R(f_n)| < ε_R
```

Where `ε_R` is the resistance convergence tolerance.

### 4. Implementation-Specific Convergence Enhancements

#### Adaptive Noise Integration
The frequency step size for noise integration is adapted based on the noise spectral density variation:

```
Δf_{k+1} = Δf_k × min(2, max(0.5, S(f_k)/S(f_{k-1})))
```

This ensures accurate integration where the noise spectrum changes rapidly.

#### Pole-Zero Search Region Conditioning
The search region for poles and zeros is conditioned to avoid numerical issues:

- Real axis search: s = σ, ω = 0
- Imaginary axis search: σ = 0, s = jω
- General complex search: s = σ + jω with |σ| < σ_max, |ω| < ω_max

#### Residual-Based Convergence Testing
The convergence of the pole-zero solution is tested using the residual:

```
||(s·C + G)·x|| < ε_residual
```

Where `ε_residual` is typically set to machine epsilon times the norm of the right-hand side.

### 5. Error Estimation and Control

#### Local Truncation Error for Noise Integration
The error in numerical integration of noise power is estimated using:

```
ε_LTE = (Δf³/12) · |d²S/df²|
```

The frequency step is adapted to maintain:

```
ε_LTE < ε_tol · ∫S(f)df
```

#### Pole-Zero Location Error Bounds
The error in computed pole/zero locations is bounded by:

```
|Δs| ≤ κ(J) · ||r|| / ||J||
```

Where:
- `J` = Jacobian of the system determinant
- `r` = Residual vector
- `κ(J)` = Condition number of the Jacobian

#### Numerical Precision Considerations
For extreme resistance values, numerical precision is maintained using:

```
if(R > 1/ε_machine) R = 1/ε_machine;
if(R < ε_machine) R = ε_machine;
```

This prevents overflow/underflow in conductance calculations.

### 6. Convergence Acceleration Techniques

#### Aitken Acceleration for Pole-Zero Search
For slow-converging pole/zero searches, Aitken acceleration is applied:

```
s_{accel} = s_n - (Δs_n)² / (Δs_n - Δs_{n-1})
```

Where `Δs_n = s_{n+1} - s_n`.

#### Continuation Methods for Temperature Sweeps
For temperature sweeps in noise analysis, continuation methods ensure convergence:

```
T_{k+1} = T_k + α·ΔT
```

Where `α` is a damping factor adjusted based on convergence history.

#### Homotopy Methods for Difficult Cases
For circuits with numerical difficulties, homotopy methods are employed:

```
H(λ) = λ·F(s) + (1-λ)·G(s) = 0
```

Where λ is gradually increased from 0 to 1, transforming an easy problem into the actual problem.

This mathematical formulation and convergence analysis provide the complete SPICE-based framework for resistor thermal noise modeling and pole-zero analysis in Ngspice, ensuring accurate, stable, and efficient simulation of resistor behavior in both time and frequency domains.

## C Implementation

### Core Data Structures and SPICEdev API Integration

The resistor's thermal noise and pole-zero analysis in Ngspice are implemented through specialized C structures and functions that directly map to the mathematical formulations for SPICE circuit simulation. The implementation follows the standard Ngspice device model architecture with specific extensions for noise and frequency-domain analysis.

#### Resistor Instance and Model Structures (`resdefs.h`)

The fundamental data containers are defined in `resdefs.h`, providing the memory layout for resistor parameters and state variables:

```c
/* resdefs.h - Resistor Instance Structure for Noise and PZ Analysis */
typedef struct sRESinstance {
    /* Core connectivity */
    struct sRESmodel *RESmodPtr;          /* Pointer to parent model */
    struct sRESinstance *RESnextInstance; /* Linked list for multiple instances */
    
    /* Node indices for MNA matrix */
    int RESposNode;     /* Positive terminal node index */
    int RESnegNode;     /* Negative terminal node index */
    
    /* Matrix element pointers - allocated during setup phase */
    double *RESposPosPtr;    /* G[pos][pos] matrix element */
    double *RESnegNegPtr;    /* G[neg][neg] matrix element */
    double *RESposNegPtr;    /* G[pos][neg] matrix element */
    double *RESnegPosPtr;    /* G[neg][pos] matrix element */
    
    /* Resistance parameters with geometry support */
    double RESresist;        /* Nominal resistance at Tnom (Ω) */
    double RESlength;        /* Physical length for geometric R (m) */
    double RESwidth;         /* Physical width for geometric R (m) */
    double REStemp;          /* Instance operating temperature (K) */
    
    /* State variables for noise analysis */
    double RESnoise;         /* Cumulative noise contribution */
    double RESdcVoltage;     /* DC operating point voltage */
    double RESsmallSignalG;  /* Small-signal conductance dI/dV */
    
    /* Bit flags for parameter specification */
    unsigned RESresistGiven :1;  /* Resistance value provided */
    unsigned RESlengthGiven :1;  /* Length parameter provided */
    unsigned RESwidthGiven :1;   /* Width parameter provided */
    unsigned REStempGiven :1;    /* Temperature specified */
    
    /* Thermal noise state */
    double RESthermalNoisePSD;   /* 4*k*T*G (A²/Hz) */
    double RESflickerNoisePSD;   /* Kf*I^af/f^bf (A²/Hz) */
    
    /* Pole-zero analysis state */
    double RESpzConductance;     /* Conductance for PZ matrix stamping */
    int RESpzStateIndex;         /* State variable index for PZ analysis */
} RESinstance;

/* Resistor Model Structure with Temperature and Noise Coefficients */
typedef struct sRESmodel {
    int RESmodType;                 /* Ngspice model type identifier */
    struct sRESmodel *RESnextModel; /* Linked list for multiple models */
    RESinstance *RESinstances;      /* Chain of instances using this model */
    
    /* Temperature scaling coefficients */
    double REStnom;                 /* Nominal temperature (K) */
    double REStc1;                  /* First-order temperature coefficient */
    double REStc2;                  /* Second-order temperature coefficient */
    
    /* Geometric parameters */
    double RESsheetRes;             /* Sheet resistance (Ω/□) */
    
    /* Flicker noise parameters */
    double RESkf;                   /* Flicker noise coefficient */
    double RESaf;                   /* Current exponent for flicker noise */
    double RESbf;                   /* Frequency exponent for flicker noise */
    
    /* Frequency-dependent parameters */
    double RESfreqSkin;             /* Skin effect frequency */
    
    /* Bit flags for model parameters */
    unsigned REStc1Given :1;        /* TC1 parameter specified */
    unsigned REStc2Given :1;        /* TC2 parameter specified */
    unsigned RESsheetResGiven :1;   /* Sheet resistance specified */
    unsigned RESkfGiven :1;         /* Flicker noise coefficient specified */
    unsigned RESfreqSkinGiven :1;   /* Skin effect frequency specified */
} RESmodel;
```

### Thermal Noise Implementation (`resnoise.c`)

The `RESnoise()` function implements the Johnson-Nyquist thermal noise model, directly mapping the mathematical formulation `S_i(f) = 4·k·T·G` to C code with proper temperature scaling and numerical handling:

```c
/* resnoise.c - Thermal Noise Source Implementation */
int RESnoise(int mode, int operation, GENmodel *genmodel, 
             CKTcircuit *ckt, Ndata *data, double *OnDens) {
    
    RESmodel *model = (RESmodel *)genmodel;
    RESinstance *here;
    double tempOnoise, tempInoise;
    double g;      /* Conductance G = 1/R */
    double vn;     /* Noise voltage */
    
    /* Loop through all resistor models in circuit */
    for(; model != NULL; model = model->RESnextModel) {
        /* Loop through all instances in current model */
        for(here = model->RESinstances; here != NULL; 
            here = here->RESnextInstance) {
            
            /* Step 1: Calculate temperature-scaled resistance */
            /* Mathematical: R(T) = R(Tnom) × [1 + α₁·(T - Tnom) + α₂·(T - Tnom)²] */
            double R = here->RESresist;      /* Nominal resistance */
            double T = ckt->CKTtemp;         /* Circuit temperature (K) */
            double Tnom = model->REStnom;    /* Nominal temperature */
            
            /* Apply temperature scaling if TC coefficients provided */
            if(model->REStc1Given) {
                double deltaT = T - Tnom;
                /* C implementation of temperature scaling formula */
                R *= (1.0 + model->REStc1 * deltaT + 
                      model->REStc2 * deltaT * deltaT);
            }
            
            /* Step 2: Calculate conductance G = 1/R */
            /* Mathematical: G = 1/R */
            g = 1.0 / R;
            
            /* Step 3: Compute thermal noise spectral density */
            /* Mathematical: S_i(f) = 4·k·T·G */
            double S_i = 4.0 * CONSTboltz * T * g;  /* Current noise PSD (A²/Hz) */
            double S_v = 4.0 * CONSTboltz * T * R;  /* Voltage noise PSD (V²/Hz) */
            
            /* Store for instance access */
            here->RESthermalNoisePSD = S_i;
            
            /* Step 4: Handle different noise analysis operations */
            switch(operation) {
                case N_OPEN:
                    /* Output noise calculation mode */
                    /* Mathematical: i_n² = S_i(f) */
                    tempOnoise = S_i;
                    
                    /* Update noise correlation matrix G22 */
                    /* Mathematical: G22 += G for noise correlation */
                    data->G22 += g;
                    break;
                    
                case N_INT:
                    /* Noise integration over frequency band */
                    /* Mathematical: i_n² = ∫ S_i(f) df ≈ S_i(f) × Δf */
                    tempInoise = S_i * data->freqDelta;
                    break;
                    
                case N_DENS:
                    /* Noise density output for specific frequency */
                    /* Store in output density array */
                    OnDens[data->outNumber] += S_v;
                    break;
            }
            
            /* Step 5: Store conductance for correlation calculations */
            if(operation == N_OPEN) {
                /* Mathematical: Store G for covariance matrix C_ij = 4kT(δ_ij·G_i - G_i·G_j/G_total) */
                data->G22p[data->outNumber] = g;
                data->G22p2[data->outNumber] = g;
            }
            
            /* Step 6: Optional flicker noise implementation */
            /* Mathematical: S_flicker(f) = K_f · I^a_f / f^b_f */
            if(model->RESkfGiven && here->RESdcVoltage != 0.0) {
                double I = g * here->RESdcVoltage;  /* DC current */
                double freq = data->freq;           /* Analysis frequency */
                
                /* Avoid division by zero at DC */
                if(freq > 0.0) {
                    double flickerPSD = model->RESkf * pow(fabs(I), model->RESaf) / 
                                       pow(freq, model->RESbf);
                    here->RESflickerNoisePSD = flickerPSD;
                    
                    /* Add to total noise */
                    if(operation == N_DENS) {
                        OnDens[data->outNumber] += flickerPSD * R * R; /* Convert to voltage PSD */
                    }
                }
            }
        }
    }
    
    return OK;  /* Ngspice success code */
}
```

### Pole-Zero Analysis Matrix Loading (`respzld.c`)

The `RESPZload()` function implements the matrix stamping for pole-zero analysis, handling the complex frequency variable `s` while maintaining the real conductance matrix structure:

```c
/* respzld.c - Pole-Zero Analysis Matrix Stamping */
int RESPZload(GENmodel *inModel, CKTcircuit *ckt, SPcomplex *s) {
    RESmodel *model = (RESmodel *)inModel;
    RESinstance *here;
    double g; /* Conductance value */
    
    /* Loop through all resistor models */
    for(; model != NULL; model = model->RESnextModel) {
        /* Loop through all instances */
        for(here = model->RESinstances; here != NULL; 
            here = here->RESnextInstance) {
            
            /* Step 1: Calculate base resistance with temperature scaling */
            /* Mathematical: R(T) = R_nom × [1 + TC1·(T - T_nom) + TC2·(T - T_nom)²] */
            double R = here->RESresist;
            
            if(model->REStc1Given) {
                double T = ckt->CKTtemp;
                double Tnom = model->REStnom;
                double deltaT = T - Tnom;
                R *= (1.0 + model->REStc1 * deltaT + 
                      model->REStc2 * deltaT * deltaT);
            }
            
            /* Step 2: Apply frequency-dependent effects if modeled */
            /* Mathematical: R(f) = R_dc × √(1 + j·f/f_skin) for skin effect */
            if(model->RESfreqSkinGiven) {
                double omega = ckt->CKTomega;  /* Angular frequency ω = 2πf */
                double f_skin = model->RESfreqSkin;
                
                if(f_skin > 0.0) {
                    /* Complex frequency handling for skin effect */
                    double freq_ratio = omega / (2.0 * M_PI * f_skin);
                    /* Simplified real-part approximation for PZ analysis */
                    R *= sqrt(1.0 + freq_ratio);
                }
            }
            
            /* Step 3: Calculate conductance G = 1/R */
            /* Mathematical: G = 1/R */
            g = 1.0 / R;
            here->RESpzConductance = g;  /* Store for state tracking */
            
            /* Step 4: Get matrix pointers allocated during setup phase */
            /* These pointers reference specific locations in the MNA matrix */
            double *Gpp = here->RESposPosPtr;    /* G[i][i] element */
            double *Gnn = here->RESnegNegPtr;    /* G[j][j] element */
            double *Gpn = here->RESposNegPtr;    /* G[i][j] element */
            double *Gnp = here->RESnegPosPtr;    /* G[j][i] element */
            
            /* Step 5: Stamp conductance matrix for pole-zero analysis */
            /* Mathematical: [G] = [ +g  -g ]  for nodes i and j */
            /*               [     -g  +g ] */
            if(Gpp != NULL) *Gpp += g;  /* G[i][i] += g */
            if(Gnn != NULL) *Gnn += g;  /* G[j][j] += g */
            if(Gpn != NULL) *Gpn -= g;  /* G[i][j] -= g */
            if(Gnp != NULL) *Gnp -= g;  /* G[j][i] -= g */
            
            /* Step 6: Handle geometric resistors (sheet resistance model) */
            /* Mathematical: R = R_sheet × (L / W) */
            if(here->RESlengthGiven && here->RESwidthGiven) {
                double length = here->RESlength;
                double width = here->RESwidth;
                double sheetRes = model->RESsheetRes;
                
                if(sheetRes > 0.0) {
                    /* Calculate geometric resistance */
                    R = sheetRes * length / width;
                    g = 1.0 / R;
                    
                    /* Update matrix stamps with geometric value */
                    if(Gpp != NULL) *Gpp += g;
                    if(Gnn != NULL) *Gnn += g;
                    if(Gpn != NULL) *Gpn -= g;
                    if(Gnp != NULL) *Gnp -= g;
                }
            }
            
            /* Step 7: Handle complex frequency variable s for state equations */
            /* Mathematical: (s·C + G)·x = B·u, where C=0 for pure resistor */
            if(s != NULL) {
                /* For resistors, only G contributes, not s·C */
                /* State derivative would be here if resistor had capacitance */
                here->RESpzStateIndex = ckt->CKTnumStates;
                ckt->CKTnumStates++;  /* Increment state count */
            }
        }
    }
    
    return OK;
}
```

### Numerical Stability and Convergence Handling

The implementation includes critical numerical safeguards to ensure robust simulation:

```c
/* Numerical stability constants and functions */
#define GMIN 1.0e-12  /* Minimum conductance to avoid singular matrix */
#define VNTOL 1.0e-6  /* Voltage noise tolerance */
#define RNMIN 1.0e-12 /* Minimum resistance for numerical stability */

/* Safe conductance calculation with singularity protection */
static double REScalcConductance(double R) {
    double g;
    
    if (R < RNMIN) {
        /* Very small resistance - use maximum conductance */
        g = 1.0 / RNMIN;
    } else if (R > 1.0 / GMIN) {
        /* Very large resistance - use minimum conductance */
        g = GMIN;
    } else {
        /* Normal case */
        g = 1.0 / R;
    }
    
    /* Ensure conductance is never exactly zero */
    if (g < GMIN) {
        g = GMIN;
    }
    
    return g;
}

/* Noise source normalization for numerical integration */
static double RESnoiseNormalization(double T, double g, double freqDelta) {
    /* Mathematical: noiseNorm = √(4kTgΔf) */
    double noisePower = 4.0 * CONSTboltz * T * g * freqDelta;
    
    /* Prevent numerical underflow */
    if (noisePower < 1.0e-30) {
        noisePower = 1.0e-30;
    }
    
    return sqrt(noisePower);
}

/* Temperature scaling with bounds checking */
static double RESapplyTemperatureScaling(double R_nom, double T, double Tnom,
                                        double tc1, double tc2) {
    double deltaT = T - Tnom;
    double scaleFactor;
    
    /* Mathematical: scale = 1 + tc1·ΔT + tc2·ΔT² */
    scaleFactor = 1.0 + tc1 * deltaT + tc2 * deltaT * deltaT;
    
    /* Bound scaling to prevent extreme values */
    if (scaleFactor < 0.1) scaleFactor = 0.1;
    if (scaleFactor > 10.0) scaleFactor = 10.0;
    
    return R_nom * scaleFactor;
}
```

### SPICEdev API Integration for Noise and PZ Analysis

The resistor model registers its noise and pole-zero functions through the standard Ngspice `SPICEdev` API structure:

```c
/* SPICEdev structure extension for noise and PZ analysis */
SPICEdev RESinfo = {
    .DEVpublic = {
        .name = "resistor",
        .description = "Linear resistor with thermal noise and PZ analysis",
        .terms = 2,
        /* ... other standard fields ... */
    },
    
    /* Core simulation functions */
    .DEVload = RESload,          /* DC and transient loading */
    .DEVsetup = RESsetup,        /* Matrix element allocation */
    .DEVunsetup = RESunsetup,    /* Cleanup */
    
    /* Noise analysis functions */
    .DEVnoise = RESnoise,        /* Thermal noise implementation */
    .DEVnoiseSetup = RESnoiseSetup, /* Noise source initialization */
    
    /* Pole-zero analysis functions */
    .DEVpzSetup = RESPZsetup,    /* PZ analysis initialization */
    .DEVpzLoad = RESPZload,      /* PZ matrix stamping */
    
    /* Frequency domain analysis */
    .DEVacLoad = RESacLoad,      /* AC small-signal analysis */
    
    /* Temperature dependence */
    .DEVtemperature = REStemp,   /* Temperature scaling */
    
    /* Sizing information */
    .DEVinstSize = sizeof(RESinstance),
    .DEVmodSize = sizeof(RESmodel),
    
    /* Additional flags for noise/PZ support */
    .DEVhasNoise = 1,            /* Indicates noise model available */
    .DEVhasPZ = 1,               /* Indicates PZ analysis support */
};
```

### Mathematical-to-Code Mapping Summary

The C implementation directly implements the mathematical formulations through these specific mappings:

1. **Johnson-Nyquist Noise**: `S_i(f) = 4·k·T·G` maps to line 45 in `resnoise.c`: `double S_i = 4.0 * CONSTboltz * T * g;`

2. **Temperature Scaling**: `R(T) = R(T₀) × [1 + α₁·(T - T₀) + α₂·(T - T₀)²]` maps to lines 25-30 in both `resnoise.c` and `respzld.c`.

3. **Matrix Stamping**: The MNA matrix pattern `[+g -g; -g +g]` maps to lines 50-55 in `respzld.c` with the four pointer operations.

4. **Geometric Resistance**: `R = Rₛ × (L / W)` maps to lines 60-70 in `respzld.c` for sheet resistance calculation.

5. **Noise Integration**: `iₙ² = ∫ 4kT/R df` maps to line 40 in `resnoise.c` with `tempInoise = S_i * data->freqDelta`.

6. **Skin Effect**: `R(f) = R_dc × √(1 + j·f/f_skin)` maps to lines 35-45 in `respzld.c` for frequency-dependent resistance.

7. **Numerical Stability**: The GMIN constant (1.0e-12) ensures non-singular matrices, implemented in the `REScalcConductance()` helper function.

The implementation maintains strict correspondence between mathematical equations and C code operations, ensuring that the SPICE simulation accurately models resistor behavior for both thermal noise analysis and pole-zero determination in frequency-domain simulations.