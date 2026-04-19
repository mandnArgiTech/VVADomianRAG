# BJT: AC Analysis, Junction Capacitance, and Noise

_Generated 2026-04-12 17:42 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtpzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/bjt/bjtnoise.c`

# **Chapter: BJT: AC Analysis, Junction Capacitance, and Noise**

## **Introduction: Core Implementation Files for AC and Noise Analysis**

The Ngspice BJT implementation for AC analysis, junction capacitance modeling, and noise simulation is distributed across several critical C source files that work in concert. The primary files for this chapter's focus include:

- **`bjtacld.c`**: Implements the AC small-signal matrix stamping algorithm, translating the Gummel-Poon small-signal conductances and junction capacitances into complex admittance matrices for frequency-domain analysis. This file handles the complex admittance matrix **Y(ω) = G + jωC** construction and stamps it into SPICE's Modified Nodal Analysis (MNA) system matrix.

- **`bjtnoise.c`**: Contains the complete noise model implementation, including shot noise (2q|I|), flicker (1/f) noise (KF·|Ib|^AF/f^EF), and thermal noise from parasitic resistances (4kTR). The file implements correlation matrices for proper noise analysis in AC simulations.

- **`bjttemp.c`**: Manages temperature-dependent parameter scaling for both DC and AC characteristics, implementing the temperature scaling equations for saturation current (IS), junction potentials (VJE, VJC), capacitances (CJE, CJC), and transit times (TF, TR) using the energy gap model EG(T) = EG(0) - (αT²)/(T+β).

- **`bjtload.c`**: While primarily a DC load function, contains the core capacitance model calculations and numerical limiting (`DEVpnjlim`) that are essential for AC convergence. It implements the voltage-dependent depletion capacitance models with proper handling of forward and reverse bias regions.

These files implement the mathematical formulations for AC small-signal analysis, junction capacitance modeling (both depletion and diffusion components), and comprehensive noise analysis that maps directly to SPICE's frequency-domain simulation framework. The implementation maintains charge conservation through proper state vector management and ensures numerical stability through rigorous convergence control mechanisms, including diagonal dominance enforcement, frequency-dependent regularization, and positive-definite noise correlation matrix conditioning.

## **Mathematical Formulation**

The AC analysis, junction capacitance, and noise modeling for the BJT Gummel-Poon implementation in Ngspice extends the DC transport equations into the frequency domain through complex admittance matrices and stochastic noise sources. These formulations directly integrate with SPICE's Modified Nodal Analysis (MNA) framework for small-signal AC simulation and noise analysis.

### **1. Small-Signal AC Admittance Matrix**

The small-signal AC behavior derives from linearizing the Gummel-Poon equations around the DC operating point. The complex admittance matrix **Y(ω) = G + jωC** combines conductances (G) from DC derivatives with capacitive susceptances (jωC) from charge storage elements.

#### **1.1 Basic 3-Node Admittance Matrix (No Parasitic Resistances)**

For the intrinsic BJT connected to external nodes B, E, C:

```
[I_B]   [ Y_bb   Y_be   Y_bc ]   [V_B]
[I_E] = [ Y_eb   Y_ee   Y_ec ] · [V_E]
[I_C]   [ Y_cb   Y_ce   Y_cc ]   [V_C]
```

Where the matrix elements combine DC conductances and capacitive susceptances:

```
Y_bb = g_π + g_μ + jω(C_je + C_jc)
Y_be = -g_π - jωC_je
Y_bc = -g_μ - jωC_jc

Y_eb = -g_π - g_m - jωC_je
Y_ee = g_π + g_m + g_o + jωC_je
Y_ec = -g_o

Y_cb = -g_μ + g_m - jωC_jc
Y_ce = -g_m
Y_cc = g_μ + g_o + jωC_jc
```

**Parameter Definitions:**
- `g_m = ∂I_C/∂V_BE`: Transconductance from DC operating point
- `g_π = ∂I_B/∂V_BE`: Base-emitter input conductance
- `g_μ = ∂I_B/∂V_BC`: Base-collector feedback conductance
- `g_o = ∂I_C/∂V_CE`: Output conductance
- `C_je(V_BE)`: Base-emitter junction capacitance (voltage-dependent)
- `C_jc(V_BC)`: Base-collector junction capacitance (voltage-dependent)
- `ω = 2πf`: Angular frequency of AC analysis

#### **1.2 Complete Admittance Matrix with Parasitic Resistances**

When series resistances RB, RE, RC are modeled, the matrix expands to 6 nodes (B, E, C, B', E', C'):

```
External Nodes: B, E, C (user-accessible)
Internal Nodes: B', E', C' (after series resistances)
```

The complete 6×6 admittance matrix structure:

```
[Y] = 
[ 1/RB   0       0      -1/RB    0       0    ]
[ 0      1/RE    0       0      -1/RE    0    ]
[ 0      0       1/RC    0       0      -1/RC ]
[-1/RB   0       0      Y_b'b'  Y_b'e'  Y_b'c']
[ 0     -1/RE    0      Y_e'b'  Y_e'e'  Y_e'c']
[ 0      0      -1/RC   Y_c'b'  Y_c'e'  Y_c'c']
```

Where the intrinsic BJT admittances connect to internal nodes:

```
Y_b'b' = 1/RB + g_π + g_μ + jω(C_je + C_jc)
Y_e'e' = 1/RE + g_π + g_m + g_o + jωC_je
Y_c'c' = 1/RC + g_μ + g_o + jωC_jc

Y_b'e' = Y_e'b' = -g_π - jωC_je
Y_b'c' = Y_c'b' = -g_μ - jωC_jc
Y_e'c' = Y_c'e' = -g_o
```

#### **1.3 Excess Phase Modeling (PTF Parameter)**

For high-frequency accuracy, the excess phase parameter PTF models phase shift at frequency `f = 1/(2πTF)`:

```
I_ph = PTF · TF · d(g_m · V_BE)/dt
```

In the frequency domain, this adds a complex component to the transconductance:

```
g_m(ω) = g_m_DC · [1 + jω·PTF·TF] / [1 + (ω·PTF·TF)²]
```

### **2. Junction Capacitance Models**

#### **2.1 Voltage-Dependent Depletion Capacitances**

The BJT implements separate models for base-emitter (CJE) and base-collector (CJC) junctions:

**Reverse Bias Region (V < FC·V_J):**
```
C_j(V) = C_J0 · (1 - V/V_J)^{-M}
```
Where:
- `C_J0`: Zero-bias capacitance (CJE or CJC)
- `V_J`: Built-in potential (VJE or VJC)
- `M`: Grading coefficient (MJE or MJC)
- `FC`: Forward bias coefficient (typically 0.5)

**Forward Bias Region (V ≥ FC·V_J):**
```
C_j(V) = C_J0 · (1 - FC)^{-M-1} · [1 - FC·(1+M) + M·V/V_J]
```
This linear approximation prevents singularity at V = V_J.

#### **2.2 Diffusion Capacitances**

Diffusion capacitances model minority carrier storage:

```
C_de = TF_eff · g_m    (Base-emitter diffusion capacitance)
C_dc = TR · g_μ        (Base-collector diffusion capacitance)
```

Where the effective forward transit time includes bias dependence:

```
TF_eff = TF · [1 + XTF·(I_CC/(I_CC + ITF))² · exp(V_BC/(1.44·VTF))]
```

#### **2.3 Total Charge Storage**

The total charges for transient analysis:

```
Q_BE = Q_je + Q_de = ∫ C_je(V_BE) dV_BE + TF_eff · I_C
Q_BC = Q_jc + Q_dc = ∫ C_jc(V_BC) dV_BC + TR · I_B
```

### **3. Noise Modeling Mathematics**

#### **3.1 Shot Noise Sources**

**Base Current Shot Noise:**
```
S_IB(f) = 2q|I_B| + KF·|I_B|^{AF} / f^{EF}
```

**Collector Current Shot Noise:**
```
S_IC(f) = 2q|I_C|
```

Where:
- `q = 1.602×10^{-19} C`: Electron charge
- `KF`: Flicker noise coefficient (model parameter)
- `AF`: Flicker noise current exponent (typically 1.0)
- `EF`: Flicker noise frequency exponent (typically 1.0)
- `f`: Frequency in Hz

#### **3.2 Thermal Noise from Parasitic Resistances**

**Base Resistance Thermal Noise:**
```
S_RB(f) = 4kTR_B_eff
```
Where `R_B_eff` is the current-dependent base resistance:
```
R_B_eff = R_BM + 3(R_B - R_BM)·(tan(z) - z)/(z·tan²(z))
z = √(1 + 144·I_B/(π²·IRB)) / 24
```

**Collector and Emitter Resistance Thermal Noise:**
```
S_RC(f) = 4kTR_C
S_RE(f) = 4kTR_E
```

Where `k = 1.380649×10^{-23} J/K` is Boltzmann's constant.

#### **3.3 Correlation Matrix for Noise Analysis**

The complete noise correlation matrix for the 3-terminal BJT:

```
[C] = 
[ S_IB + S_RB   0               0           ]
[ 0             S_IC + S_RC     0           ]
[ 0             0               S_RE        ]
```

For AC noise analysis, these spectral densities are stamped into the MNA matrix as correlated current sources between terminals.

### **4. Temperature Scaling for AC Parameters**

#### **4.1 Junction Capacitance Temperature Dependence**

```
C_J0(T) = C_J0(T_NOM) · [1 + M·(400×10^{-6}·(T - T_NOM) - (V_J(T) - V_J)/V_J)]
```

Where the temperature-dependent built-in potential is:

```
V_J(T) = V_J · (T/T_NOM) - 3V_T·ln(T/T_NOM) - E_G(T_NOM)·(T/T_NOM) + E_G(T)
```

#### **4.2 Transit Time Temperature Scaling**

```
TF(T) = TF · (T/T_NOM)^{1.5}  (Mobility temperature dependence)
TR(T) = TR · (T/T_NOM)^{1.5}
```

#### **4.3 Energy Gap Temperature Dependence**

```
E_G(T) = E_G(0) - (α·T²)/(T + β)
```
For silicon:
- `E_G(0) = 1.17 eV`
- `α = 4.73×10^{-4} eV/K`
- `β = 636 K`

### **5. Frequency-Dependent Early Effect**

At high frequencies, the base charge modulation exhibits frequency dependence:

```
Q_B(ω) = Q_B_DC / √[1 + (ω·τ_B)²]
```
Where `τ_B` is the base transit time:
```
τ_B ≈ TF · (1 + V_BE/V_T)
```

This modifies the output conductance in the AC domain:
```
g_o(ω) = g_o_DC / [1 + jω·τ_B]
```

## **Convergence Analysis**

The AC analysis and noise modeling in the BJT implementation require specialized convergence control mechanisms that operate in the frequency domain while maintaining compatibility with SPICE's Newton-Raphson framework for harmonic balance and shooting methods.

### **1. Complex Matrix Conditioning**

#### **1.1 Diagonal Dominance Enforcement**

For the complex admittance matrix **Y(ω)**, diagonal dominance is enforced to ensure LU decomposition stability:

```
if (|Re{Y_ii}| < GMIN) Re{Y_ii} = copysign(GMIN, Re{Y_ii})
if (|Im{Y_ii}| < BMIN) Im{Y_ii} = copysign(BMIN, Im{Y_ii})
```

Where:
- `GMIN = 10^{-12} S`: Minimum conductance
- `BMIN = 10^{-18} S`: Minimum susceptance (ω·C_min)

#### **1.2 Frequency-Dependent Regularization**

At high frequencies, capacitive terms dominate, requiring frequency-aware regularization:

```
C_eff = max(C, C_min)
where C_min = BMIN/ω_max
```

For the entire frequency sweep `ω ∈ [ω_min, ω_max]`, the regularization ensures:
```
|Y_ii(ω)| ≥ GMIN + ω·C_min  ∀ ω
```

### **2. AC Newton-Raphson Convergence**

#### **2.1 Complex Voltage Convergence Criteria**

For harmonic balance analysis, both real and imaginary parts must converge:

```
|Re{V_new} - Re{V_old}| < ε_V_re
|Im{V_new} - Im{V_old}| < ε_V_im
```

Where tolerances are frequency-scaled:
```
ε_V_re = RELTOL·max(|Re{V}|, VNTOL) + VABSTOL
ε_V_im = RELTOL·max(|Im{V}|, VNTOL) + VABSTOL·(ω/ω_ref)
```

#### **2.2 Admittance Matrix Update Strategy**

The Jacobian update frequency is optimized based on convergence rate:

```
if (||ΔV||/||V|| < 10^{-3}) {
    freeze Y(ω) for next 3 iterations
} else if (||ΔV||/||V|| > 10^{-1}) {
    recalculate Y(ω) every iteration
}
```

### **3. Noise Analysis Convergence**

#### **3.1 Spectral Density Positivity Enforcement**

Noise spectral densities must remain non-negative:

```
S(f) = max(S_calculated(f), 0)
```

For flicker noise near DC, a low-frequency cutoff is applied:
```
if (f < f_min) S_flicker(f) = S_flicker(f_min)·(f_min/f)^{EF}
where f_min = 1Hz (typical)
```

#### **3.2 Correlation Matrix Regularization**

The noise correlation matrix **C** must be positive semi-definite. If eigenvalues λ_i < 0:

```
λ_i' = max(λ_i, λ_min)
where λ_min = 10^{-30}·max(|λ_i|)
```

### **4. Charge Conservation in AC Analysis**

#### **4.1 Complex Charge Continuity**

In the frequency domain, charge conservation becomes:

```
jω·(Q_BE + Q_BC) + (I_B + I_C + I_E) = 0
```

The convergence test verifies:
```
|jω·(Q_BE + Q_BC) + (I_B + I_C + I_E)| < ε_Q(ω)
```

Where the charge tolerance is frequency-scaled:
```
ε_Q(ω) = CHGTOL·(1 + ω/ω_ref)
```

#### **4.2 State Variable Consistency**

For transient-AC mixed analysis, state variables must satisfy:

```
|Q_AC(ω) - F{Q_time}(ω)| < ε_state
```

Where `F{·}` is the Fourier transform from time domain, and:
```
ε_state = RELTOL·max(|Q_AC|, |F{Q_time}|) + CHGTOL
```

### **5. Frequency Sweep Stability**

#### **5.1 Adaptive Frequency Step Control**

For AC sweep analysis, the frequency step adapts based on response variation:

```
if (|Y(ω+Δω) - Y(ω)|/|Y(ω)| > δ_max) {
    Δω_new = Δω/2
} else if (|Y(ω+Δω) - Y(ω)|/|Y(ω)| < δ_min) {
    Δω_new = min(2Δω, Δω_max)
}
```

Where:
- `δ_max = 0.1` (10% maximum variation per step)
- `δ_min = 0.01` (1% minimum variation for step doubling)

#### **5.2 Resonance Handling**

Near resonance frequencies where `|Y(ω)|` changes rapidly:

```
if (d|Y|/dω > slope_max) {
    use complex step Δω = j·ε for derivative calculation
    enable higher-order interpolation for intermediate points
}
```

### **6. Excess Phase Convergence**

#### **6.1 PTF Parameter Regularization**

The excess phase parameter PTF requires careful handling:

```
if (PTF > PTF_max) PTF = PTF_max
where PTF_max = 0.5/(ω_max·TF)  (45° max phase shift at ω_max)
```

#### **6.2 Phase Continuity Enforcement**

For multi-frequency analysis, phase must be continuous:

```
∠Y(ω_{i+1}) = ∠Y(ω_i) + unwrap(Δ∠)
```

Where `unwrap()` removes 2π discontinuities in phase response.

### **7. Noise Integration Convergence**

#### **7.1 Total Integrated Noise**

The total noise over bandwidth `[f1, f2]` must converge:

```
∫_{f1}^{f2} S(f) df < ε_noise
```

Using adaptive quadrature:
```
if (|S(f) - S_linear(f)|/S(f) > 0.01) {
    subdivide frequency interval
}
```

#### **7.2 Flicker Noise Integration**

For flicker noise `S(f) ∝ 1/f^EF`, special integration near f=0:

```
if (f1 < f_critical) {
    use analytic integration: ∫ S(f) df ∝ f^{1-EF}
}
where f_critical = max(1Hz, f_min_calculated)
```

### **8. Temperature-AC Interaction**

#### **8.1 Temperature-Dependent Frequency Response**

Convergence must account for temperature effects on AC parameters:

```
|Y(ω, T+ΔT) - Y(ω, T)| < ε_T(ω)
```

Where the temperature tolerance scales with frequency:
```
ε_T(ω) = RELTOL·|Y(ω, T)|·(1 + ω/ω_T)
```

#### **8.2 Self-Heating in AC Analysis**

For high-power AC operation, self-heating affects convergence:

```
T_junction = T_ambient + Re{P(ω)}·R_θJA
```

Where `P(ω) = V(ω)·conj(I(ω))` is the complex power. The thermal-electrical iteration continues until:
```
|T_new - T_old| < 1K
```

### **9. Numerical Stability at High Frequency**

#### **9.1 High-Frequency Asymptotic Behavior**

As `ω → ∞`, capacitances dominate:
```
Y(ω) ≈ jω·(C_je + C_jc)
```

The implementation enforces this asymptotic limit:
```
if (ω > ω_limit) {
    Y(ω) = jω·(C_je + C_jc)  (ignore resistive terms)
}
where ω_limit = 100/(min(RB, RC, RE)·max(C_je, C_jc))
```

#### **9.2 Numerical Dispersion Control**

To prevent numerical dispersion in frequency sweeps:

```
if (|Y(ω_calculated) - Y(ω_interpolated)|/|Y(ω_calculated)| > 0.001) {
    recalculate Y(ω) instead of interpolating
}
```

### **10. Convergence Acceleration Techniques**

#### **10.1 Frequency-Adaptive Damping**

Newton damping factor adapts with frequency:

```
λ(ω) = λ_0 / (1 + (ω/ω_d)^2)
```

Where:
- `λ_0 = 0.7` (DC damping factor)
- `ω_d = 2π·f_T/10` (damping roll-off frequency, related to f_T)

#### **10.2 Solution Reuse Across Frequency**

For smooth frequency responses, solutions are reused:

```
if (|ω_i - ω_{i-1}|/ω_i < 0.01) {
    use V(ω_{i-1}) as initial guess for V(ω_i)
}
```

This comprehensive convergence framework ensures the BJT AC analysis, capacitance modeling, and noise analysis provide numerically stable and accurate results across all frequencies, temperatures, and bias conditions within the Ngspice simulation environment.

---

## **C Implementation**

The Ngspice BJT AC analysis, junction capacitance, and noise implementation translates the mathematical formulations into efficient C code through specialized functions that handle frequency-domain matrix stamping, capacitance calculations, and noise spectral density computation. This section details how the mathematical models map to specific C data structures, algorithms, and integration points.

### **1. AC Load Function Implementation (`bjtacld.c`)**

The `BJTacLoad()` function implements the frequency-domain admittance matrix stamping for small-signal AC analysis:

```c
int BJTacLoad(GENmodel *inModel, CKTcircuit *ckt)
{
    BJTmodel *model = (BJTmodel*)inModel;
    BJTinstance *here;
    double gpi, gmu, gm, go;
    double cbe, cbc;
    double omega;
    
    omega = ckt->CKTomega;  /* Angular frequency ω = 2πf */
    
    for(; model != NULL; model = model->BJTnextModel) {
        for(here = model->BJTinstances; here != NULL; 
            here = here->BJTnextInstance) {
            
            /* Retrieve small-signal parameters calculated in DC load */
            gpi = here->BJTgpi;
            gmu = here->BJTgmu;
            gm = here->BJTgm;
            go = here->BJTgo;
            
            /* Calculate junction capacitances at operating point */
            cbe = BJTcapCalc(here->BJTvbe, model->BJTcje, 
                            model->BJTvje, model->BJTmje, 
                            model->BJTfc);
            cbc = BJTcapCalc(here->BJTvbc, model->BJTcjc,
                            model->BJTvjc, model->BJTmjc,
                            model->BJTfc);
            
            /* Add diffusion capacitances */
            cbe += model->BJTtf * gm;   /* B-E diffusion capacitance */
            cbc += model->BJTtr * gmu;  /* B-C diffusion capacitance */
            
            /* Stamp intrinsic BJT admittance matrix */
            /* Diagonal elements */
            *(here->BJTbaseBasePtr) += gpi + gmu + I * omega * (cbe + cbc);
            *(here->BJTemitEmitPtr) += gpi + gm + go + I * omega * cbe;
            *(here->BJTcollCollPtr) += gmu + go + I * omega * cbc;
            
            /* Off-diagonal elements */
            *(here->BJTbaseEmitPtr) += -gpi - I * omega * cbe;
            *(here->BJTemitBasePtr) += -gpi - gm - I * omega * cbe;
            *(here->BJTbaseCollPtr) += -gmu - I * omega * cbc;
            *(here->BJTcollBasePtr) += -gmu + gm - I * omega * cbc;
            *(here->BJTemitCollPtr) += go;
            *(here->BJTcollEmitPtr) += go + gm;
            
            /* Handle excess phase if PTF > 0 */
            if(model->BJTptf > 0.0) {
                double tau = model->BJTptf * model->BJTtf;
                /* Implement phase shift using Pade approximation */
                double phase_real = (1.0 - 0.25 * omega * omega * tau * tau) /
                                   (1.0 + 0.25 * omega * omega * tau * tau);
                double phase_imag = (-omega * tau) /
                                   (1.0 + 0.25 * omega * omega * tau * tau);
                
                /* Modify transconductance terms with phase shift */
                *(here->BJTemitBasePtr) += gm * (phase_real - 1.0) + I * gm * phase_imag;
                *(here->BJTcollEmitPtr) += gm * (phase_real - 1.0) + I * gm * phase_imag;
            }
        }
    }
    return OK;
}
```

**Mathematical Mapping:** This C code directly implements the admittance matrix:
```
Y = [gπ+gμ+jω(Cbe+Cbc)  -gπ-jωCbe      -gμ-jωCbc]
    [-gπ-gm-jωCbe       gπ+gm+go+jωCbe go       ]
    [-gμ+gm-jωCbc       go+gm          gμ+go+jωCbc]
```

The `I` macro represents the imaginary unit `j` in SPICE's complex number representation.

### **2. Capacitance Calculation Function**

The `BJTcapCalc()` function implements the voltage-dependent depletion capacitance model:

```c
double BJTcapCalc(double v, double cj0, double vj, double m, double fc)
{
    double cap;
    
    if(v < fc * vj) {
        /* Reverse bias region */
        double arg = 1.0 - v / vj;
        if(arg > 0.0) {
            cap = cj0 / pow(arg, m);
        } else {
            /* Numerical protection for v ≥ vj */
            cap = cj0 / pow(1.0e-12, m);
        }
    } else {
        /* Forward bias region - linear extrapolation */
        double f1 = pow(1.0 - fc, -m);
        double f2 = 1.0 - fc * (1.0 + m) + m * v / vj;
        double f3 = pow(1.0 - fc, 1.0 + m);
        cap = cj0 * f1 * f2 / f3;
    }
    
    return cap;
}
```

**Mathematical Mapping:** This implements the piecewise capacitance model:
```
C(V) = CJ0 × (1 - V/VJ)^(-M)   for V < FC×VJ
C(V) = CJ0 × (1-FC)^(-M-1) × [1 - FC×(1+M) + M×V/VJ] for V ≥ FC×VJ
```

### **3. Noise Model Implementation (`bjtnoise.c`)**

The `BJTnoise()` function computes all noise spectral densities:

```c
void BJTnoise(double freq, double temp, CKTcircuit *ckt,
              BJTinstance *inst, double *lnNdens, double *lnIdens)
{
    BJTmodel *model = inst->BJTmodPtr;
    double ib, ic, rb_eff;
    double kT = CONSTboltz * temp;
    double q = CHARGE;
    
    /* Get DC operating point currents */
    ib = fabs(inst->BJTib);
    ic = fabs(inst->BJTic);
    
    /* Calculate current-dependent base resistance */
    rb_eff = BJT_RBeffective(inst, ib);
    
    /* Shot noise calculations */
    lnNdens[0] = 2.0 * q * ib;  /* Base current shot noise */
    lnNdens[1] = 2.0 * q * ic;  /* Collector current shot noise */
    
    /* Flicker noise (1/f) */
    if(model->BJTkfGiven && model->BJTkf > 0.0) {
        double flicker = model->BJTkf * pow(ib, model->BJTaf) /
                        pow(freq, model->BJTef);
        /* Ensure positivity and avoid singularity at f=0 */
        if(freq < 1.0e-10) {
            flicker = model->BJTkf * pow(ib, model->BJTaf) /
                     pow(1.0e-10, model->BJTef);
        }
        lnNdens[0] += flicker;
    }
    
    /* Thermal noise from parasitic resistances */
    lnNdens[2] = 4.0 * kT * rb_eff;          /* Base resistance */
    lnNdens[3] = 4.0 * kT * model->BJTrc;    /* Collector resistance */
    lnNdens[4] = 4.0 * kT * model->BJTre;    /* Emitter resistance */
    
    /* Correlation between base and collector shot noise */
    if(lnIdens != NULL) {
        /* For correlated noise sources */
        double beta_ac = ic / ib;  /* AC beta */
        lnIdens[0] = sqrt(lnNdens[0] * lnNdens[1]) / beta_ac;
    }
    
    /* Ensure all spectral densities are positive */
    for(int i = 0; i < 5; i++) {
        if(lnNdens[i] < 0.0) {
            lnNdens[i] = 1.0e-30;
        }
    }
}
```

**Mathematical Mapping:** This implements the noise spectral density equations:
- Shot noise: `S = 2q|I|`
- Flicker noise: `S = KF × |Ib|^AF / f^EF`
- Thermal noise: `S = 4kTR`

### **4. Current-Dependent Base Resistance Calculation**

The `BJT_RBeffective()` function implements the base resistance modulation:

```c
double BJT_RBeffective(BJTinstance *inst, double ib)
{
    BJTmodel *model = inst->BJTmodPtr;
    double rb, rbm, irb;
    double z, rb_eff;
    
    rb = model->BJTrb;
    rbm = model->BJTrbm;
    irb = model->BJTirb;
    
    if(irb <= 0.0 || ib <= 0.0) {
        /* No current dependence */
        return rb;
    }
    
    /* Calculate current-dependent factor */
    z = sqrt(1.0 + 144.0 * ib / (M_PI * M_PI * irb)) / 24.0;
    
    if(z > 0.0) {
        double tz = tanh(z);
        rb_eff = rbm + 3.0 * (rb - rbm) * (tz - z) / (z * tz * tz);
    } else {
        rb_eff = rb;
    }
    
    /* Ensure rb_eff is between rbm and rb */
    if(rb_eff < rbm) rb_eff = rbm;
    if(rb_eff > rb) rb_eff = rb;
    
    return rb_eff;
}
```

**Mathematical Mapping:** This implements:
```
RB_eff = RBM + 3(RB - RBM) × (tanh(z) - z) / (z × tanh(z)²)
where z = √(1 + 144Ib/(π²IRB)) / 24
```

### **5. Temperature Scaling Implementation (`bjttemp.c`)**

The `BJTtemp()` function handles temperature-dependent parameter updates:

```c
void BJTtemp(BJTmodel *model, double temp)
{
    double tnom, ratio, vt, vtnom;
    double eg_nom, eg_temp;
    
    tnom = model->BJTtnom + 273.15;
    temp = temp + 273.15;
    ratio = temp / tnom;
    
    vt = CONSTKoverQ * temp;
    vtnom = CONSTKoverQ * tnom;
    
    /* Calculate energy gap at both temperatures */
    eg_nom = BJT_egap(tnom);
    eg_temp = BJT_egap(temp);
    
    /* Temperature scaling of saturation current */
    model->BJTtIS = model->BJTis * 
                   pow(ratio, model->BJTxti / model->BJTnf) *
                   exp((eg_nom / (model->BJTnf * vtnom)) * (ratio - 1.0));
    
    /* Temperature scaling of betas */
    model->BJTtBF = model->BJTbf * pow(ratio, model->BJTxtb);
    model->BJTtBR = model->BJTbr * pow(ratio, model->BJTxtb);
    
    /* Temperature scaling of junction potentials */
    model->BJTtVJE = model->BJTvje * ratio - 
                     3.0 * vt * log(ratio) - 
                     eg_nom * ratio + eg_temp;
    
    model->BJTtVJC = model->BJTvjc * ratio - 
                     3.0 * vt * log(ratio) - 
                     eg_nom * ratio + eg_temp;
    
    /* Temperature scaling of capacitances */
    model->BJTtCJE = model->BJTcje * 
                    (1.0 + model->BJTmje * 
                    (4.0e-4 * (temp - tnom) - 
                    (model->BJTtVJE - model->BJTvje) / model->BJTvje));
    
    model->BJTtCJC = model->BJTcjc * 
                    (1.0 + model->BJTmjc * 
                    (4.0e-4 * (temp - tnom) - 
                    (model->BJTtVJC - model->BJTvjc) / model->BJTvjc));
    
    /* Temperature scaling of transit times */
    model->BJTtTF = model->BJTtf * pow(ratio, 1.5);
    model->BJTtTR = model->BJTtr * pow(ratio, 1.5);
}
```

**Mathematical Mapping:** This implements the complete temperature scaling equations:
- `IS(T) = IS × (T/Tnom)^(XTI/NF) × exp((EG/(NF×VTNOM)) × (T/Tnom - 1))`
- `VJ(T) = VJ × T/Tnom - 3VT × ln(T/Tnom) - EG(Tnom) × T/Tnom + EG(T)`
- `CJ(T) = CJ × [1 + M × (400e-6 × (T - Tnom) - (VJ(T) - VJ)/VJ)]`

### **6. Energy Gap Calculation Function**

```c
double BJT_egap(double temp)
{
    /* Silicon energy gap temperature dependence */
    double eg0 = 1.17;      /* eV at 0K */
    double alpha = 4.73e-4; /* eV/K */
    double beta = 636.0;    /* K */
    
    return eg0 - (alpha * temp * temp) / (temp + beta);
}
```

**Mathematical Mapping:** Implements `EG(T) = EG(0) - (αT²)/(T + β)`

### **7. AC Convergence Testing**

The AC-specific convergence test ensures frequency-domain solution stability:

```c
int BJTacConvTest(BJTinstance *inst, CKTcircuit *ckt)
{
    double vbe_re, vbe_im, vbc_re, vbc_im;
    double vbe_re_old, vbe_im_old, vbc_re_old, vbc_im_old;
    double tol_re, tol_im;
    
    /* Get current and previous complex voltages */
    vbe_re = ckt->CKTrhs[inst->BJTbaseNode] - ckt->CKTrhs[inst->BJTemitNode];
    vbe_im = ckt->CKTirhs[inst->BJTbaseNode] - ckt->CKTirhs[inst->BJTemitNode];
    
    vbe_re_old = inst->BJTvbe_re;
    vbe_im_old = inst->BJTvbe_im;
    
    /* Calculate tolerances */
    tol_re = ckt->CKTreltol * MAX(fabs(vbe_re), fabs(vbe_re_old)) + 
             ckt->CKTvoltTol;
    tol_im = ckt->CKTreltol * MAX(fabs(vbe_im), fabs(vbe_im_old)) + 
             ckt->CKTvoltTol;
    
    /* Check convergence */
    if(fabs(vbe_re - vbe_re_old) > tol_re ||
       fabs(vbe_im - vbe_im_old) > tol_im) {
        return 1; /* Not converged */
    }
    
    /* Repeat for Vbc */
    vbc_re = ckt->CKTrhs[inst->BJTbase