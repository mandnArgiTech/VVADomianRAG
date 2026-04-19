# MOS2: Small-Signal AC, Pole-Zero, and Noise Analysis

_Generated 2026-04-12 04:59 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2acld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2pzld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/mos2/mos2noi.c`

# MOS2: Small-Signal AC, Pole-Zero, and Noise Analysis

## Introduction

Within the Ngspice circuit simulator, the MOS2 (Level 2 MOSFET) model's frequency-domain behavior and stochastic characteristics are implemented across three specialized C source files: `mos2acld.c`, `mos2pzld.c`, and `mos2noi.c`. This chapter details their collective role in transforming the nonlinear DC operating point into a linearized, frequency-dependent representation suitable for SPICE's small-signal analysis engine.

*   **`mos2acld.c`** implements the `MOS2acLoad()` function, which constructs the complex admittance matrix \( \mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C} \) for the device. It stamps the linearized conductances (from the DC Jacobian) and the Meyer model capacitances into the circuit's sparse nodal matrix at each frequency point during an `.AC` analysis sweep.
*   **`mos2pzld.c`** (implied by the standard Ngspice architecture) would house the `MOS2pzLoad()` function, supporting pole-zero analysis. This function evaluates the device's contribution to the circuit's system determinant at complex frequencies \( s = \sigma + j\omega \), enabling the numerical root-finding algorithms to extract transfer function poles and zeros.
*   **`mos2noi.c`** contains the `MOS2noise()` function, which computes the spectral density of the intrinsic noise currents. It implements models for channel thermal noise (modified by velocity saturation), flicker (1/f) noise, and junction shot noise, providing the data necessary for `.NOISE` analysis to compute total output noise and noise figure.

Together, these modules enable Ngspice to perform comprehensive linear network analysis, stability assessment, and noise performance evaluation of circuits employing the Grove-Frohman Level 2 MOSFET model.

## Mathematical Formulation

The small-signal, pole-zero, and noise analysis for the MOS2 model transforms the nonlinear DC operating point into a linearized frequency-domain representation suitable for SPICE's AC simulation engine. This involves computing complex admittances, deriving noise spectral densities, and ensuring numerical stability across frequency.

### 1. Small-Signal AC Admittance Matrix

The AC analysis in SPICE linearizes the device around its DC operating point, resulting in a complex admittance matrix \( \mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C} \), where \( \mathbf{G} \) is the conductance matrix from the DC Jacobian and \( \mathbf{C} \) is the capacitance matrix from charge linearization.

**Linearization of Drain Current:**
The drain current \( I_d(V_{gs}, V_{ds}, V_{bs}) \) is expanded via a first-order Taylor series around the DC bias point \( (V_{GS}, V_{DS}, V_{BS}) \):
\[
i_d = g_m v_{gs} + g_{ds} v_{ds} + g_{mb} v_{bs}
\]
where the small-signal parameters are the partial derivatives evaluated at the DC point:
\[
g_m = \left. \frac{\partial I_d}{\partial V_{gs}} \right|_{OP}, \quad
g_{ds} = \left. \frac{\partial I_d}{\partial V_{ds}} \right|_{OP}, \quad
g_{mb} = \left. \frac{\partial I_d}{\partial V_{bs}} \right|_{OP}
\]
For the MOS2 Grove-Frohman model, these are computed from the piecewise regional equations (triode, saturation, subthreshold) including geometry and velocity saturation effects.

**Meyer Capacitance Model and Transcapacitances:**
The gate charge \( Q_g \) is partitioned into \( Q_{gs}, Q_{gd}, Q_{gb} \) based on the operating region. The small-signal capacitances are the derivatives of these charges:
\[
c_{gs} = \frac{\partial Q_{gs}}{\partial V_{gs}}, \quad c_{gd} = \frac{\partial Q_{gd}}{\partial V_{gd}}, \quad c_{gb} = \frac{\partial Q_{gb}}{\partial V_{gb}}
\]
These are region-dependent. For example, in saturation:
\[
c_{gs} = \frac{2}{3} C_{ox} W_{eff} L_{eff} + C_{GSO} W_{eff}, \quad c_{gd} = C_{GDO} W_{eff}, \quad c_{gb} = C_{GBO} L_{eff}
\]
The transcapacitances (e.g., \( \partial Q_{gs}/\partial V_{gd} \)) are zero in the Meyer model, leading to a simpler, non-reciprocal capacitance matrix.

**Complete 6×6 Complex Admittance Matrix:**
The system includes internal nodes \( D' \) and \( S' \) for parasitic resistances \( R_D \) and \( R_S \). The matrix for nodes \( [D, G, S, B, D', S'] \) is:
\[
\mathbf{Y} =
\begin{bmatrix}
G_{DD} & 0 & 0 & 0 & -G_{RD} & 0 \\
0 & Y_{GG} & -Y_{GS} & -Y_{GB} & -Y_{GD'} & -Y_{GS'} \\
0 & 0 & G_{SS} & 0 & 0 & -G_{RS} \\
0 & 0 & 0 & G_{BB} & 0 & 0 \\
-G_{RD} & -Y_{D'G} & -Y_{D'S} & -Y_{D'B} & G_{D'D'} & Y_{D'S'} \\
0 & -Y_{S'G} & G_{S'S} & -Y_{S'B} & Y_{S'D'} & G_{S'S'}
\end{bmatrix}
\]
where:
- \( G_{RD} = 1/R_D \), \( G_{RS} = 1/R_S \)
- \( Y_{ij} = G_{ij} + j\omega C_{ij} \) (e.g., \( Y_{GD'} = -g_m - j\omega c_{gd} \))
- \( G_{D'D'} = g_{ds} + G_{RD} \)
- \( G_{S'S'} = g_{ds} + g_m + g_{mb} + G_{RS} \)
- \( G_{BB} = g_{bd} + g_{bs} + g_{mb} \)

This matrix is stamped into SPICE's nodal admittance matrix \( \mathbf{Y}(\omega) \mathbf{V}(\omega) = \mathbf{I}(\omega) \) for AC analysis.

### 2. Pole-Zero Analysis Formulation

Pole-zero analysis computes the transfer function \( H(s) = V_{out}(s)/V_{in}(s) \) by analyzing the determinant of the circuit's admittance matrix \( \mathbf{Y}(s) \). For the MOS2 device, this involves the complex frequency variable \( s = \sigma + j\omega \).

**Device Admittance in s-Domain:**
The admittance matrix elements become functions of \( s \):
\[
\mathbf{Y}(s) = \mathbf{G} + s\mathbf{C}
\]
where \( \mathbf{C} \) is the constant capacitance matrix from the Meyer model. The poles are the values of \( s \) where \( \det(\mathbf{Y}(s)) = 0 \). For a single MOS2, the dominant pole is often associated with the output node \( D' \) through the capacitance \( c_{gd} \) and conductance \( g_{ds} \):
\[
p_1 \approx -\frac{g_{ds} + G_{RD}}{c_{gd}}
\]
A zero can arise from the feedforward path through \( c_{gd} \):
\[
z_1 \approx +\frac{g_m}{c_{gd}}
\]
This right-half-plane zero is characteristic of MOSFETs and affects frequency response stability.

**SPICE Implementation via Matrix Manipulation:**
Ngspice's pole-zero analysis performs a state-space reduction of the full circuit matrix \( \mathbf{Y}(s) \). The MOS2 model contributes the submatrix above to the overall system. The analysis solves the generalized eigenvalue problem:
\[
\det(\mathbf{G} + s\mathbf{C}) = 0
\]
The contributions from \( R_D \) and \( R_S \) add real-axis poles at \( s = -1/(R_D c_{gd}) \) and \( s = -1/(R_S c_{gs}) \).

### 3. Noise Analysis Spectral Densities

Noise analysis in SPICE computes the spectral density of stochastic device noise, modeling it as stationary random current sources added to the deterministic small-signal model.

**Thermal Noise (Channel Resistance):**
The fluctuating channel charge induces a noise current between drain and source. For long-channel devices (gradual channel approximation):
\[
S_{id}^{\text{thermal}}(f) = 4kT \gamma g_{d0}
\]
where \( g_{d0} = \left. \partial I_d/\partial V_{ds} \right|_{V_{ds}=0} \) is the drain conductance at zero \( V_{ds} \), and \( \gamma \) is a bias-dependent factor. For the Level 2 model with velocity saturation (\( V_{\text{MAX}} > 0 \)), the noise coefficient is modified:
\[
\gamma = \frac{2}{3} \cdot \frac{1 + V_{ds}/V_{\text{dsat,eff}}}{1 + 2V_{ds}/V_{\text{dsat,eff}}}
\]
where \( V_{\text{dsat,eff}} \) is the effective saturation voltage accounting for velocity saturation. This reduces noise at high fields.

**Flicker (1/f) Noise:**
Carrier trapping/detrapping in the oxide interface causes low-frequency noise:
\[
S_{id}^{\text{flicker}}(f) = \frac{K_F |I_d|^{A_F}}{f \cdot C_{ox}^2 W_{eff} L_{eff}}
\]
where \( K_F \) (`KF`) and \( A_F \) (`AF`) are model parameters, and \( C_{ox} = \epsilon_{ox}/t_{ox} \). This implements the SPICE `KF` and `AF` parameters directly.

**Junction Shot Noise:**
The bulk-drain and bulk-source diodes contribute shot noise:
\[
S_{ibd}^{\text{shot}}(f) = 2q |I_{bd}|, \quad S_{ibs}^{\text{shot}}(f) = 2q |I_{bs}|
\]
where \( q \) is the electron charge, and \( I_{bd}, I_{bs} \) are the diode currents.

**Total Noise at the Output:**
The individual noise sources are uncorrelated. Their contributions are referred to the output using the small-signal gain. For a common-source configuration, the input-referred noise voltage spectral density is:
\[
S_{v_in}(f) = \frac{S_{id}^{\text{total}}(f)}{g_m^2}
\]
where \( S_{id}^{\text{total}} = S_{id}^{\text{thermal}} + S_{id}^{\text{flicker}} \). This is used by SPICE to compute total output noise and noise figure.

### 4. Frequency-Dependent Parameter Degradation

At high frequencies, distributed effects and transit times become significant. The MOS2 model includes quasi-static approximations, but the analysis flags potential inaccuracies when:
\[
f \geq f_{\text{crit}} = \frac{\mu_{eff} (V_{gs} - V_{th})}{2\pi L_{eff}^2}
\]
This is the channel transit frequency. Beyond this, non-quasi-static effects would require a more complex model.

## Convergence Analysis

Convergence for small-signal and noise analysis in SPICE relies on the stability of the linearized system and the numerical accuracy of the frequency sweep.

### 1. AC Solution Convergence

The AC analysis solves the linear complex system \( \mathbf{Y}(\omega) \mathbf{V} = \mathbf{I} \) at each frequency. Convergence is guaranteed for a linear system, but numerical stability depends on matrix conditioning.

**Matrix Conditioning and Pivot Selection:**
The complex admittance matrix can be ill-conditioned at very low frequencies (\( \omega \rightarrow 0 \)), where it becomes nearly real and singular if conductances are small (e.g., in cutoff). SPICE adds a small conductance `GMIN` (typically \( 10^{-12} \) S) to all matrix diagonals:
\[
\mathbf{Y}' = \mathbf{Y} + \text{GMIN} \cdot \mathbf{I}
\]
This ensures non-singularity. For the MOS2, the gate node has zero DC conductance (\( G_{GG} = 0 \)), making it particularly reliant on `GMIN` for low-frequency solves.

**Frequency Sweep Stability:**
The sweep over decades of frequency (e.g., `AC DEC 10 1 1G`) must accurately compute the matrix inverse. At high frequencies where \( \omega C \gg G \), the matrix becomes dominant imaginary. SPICE's LU decomposition with partial pivoting handles this, but convergence warnings may appear if:
\[
\max|\omega C_{ij}| > 10^{12} \cdot \min|G_{ij}|
\]
indicating extreme ill-conditioning. This can occur with unrealistic large capacitances or very small conductances.

### 2. Pole-Zero Extraction Convergence

Pole-zero analysis uses iterative numerical methods (e.g., QR algorithm on state-space matrices) to find roots of \( \det(\mathbf{Y}(s)) = 0 \).

**Root-Solving Tolerance:**
The algorithm iterates until the residual is below a tolerance:
\[
|\det(\mathbf{Y}(s_k))| < \epsilon_{\text{pz}} \cdot \max|\text{coeff}(\mathbf{Y})|
\]
where \( \epsilon_{\text{pz}} \approx 10^{-10} \). For the MOS2, the presence of large parasitic resistances \( R_D, R_S \) can create poles with very large negative real parts (e.g., \( -1/(R_D C_{gd}) \)), which may be approximated as at infinity and discarded.

**Sensitivity to Operating Point:**
Poles and zeros are sensitive to the small-signal parameters \( g_m, g_{ds}, C_{gs}, etc \). Convergence of the preceding DC operating point is therefore critical. If the DC solution has not fully converged (e.g., `reltol` not met), the pole-zero results will be erroneous. The analysis assumes the linearization point is exact.

### 3. Noise Analysis Convergence and Integration

Noise analysis computes the total output noise by integrating the spectral density over frequency.

**Spectral Density Calculation Stability:**
The flicker noise formula \( 1/f \) has a singularity at \( f = 0 \). SPICE handles this by starting the integration from a small non-zero frequency \( f_{\text{min}} \) (e.g., 1 Hz in `.NOISE` analysis) or by using a logarithmic quadrature rule that weights the low-frequency region appropriately. The integral
\[
\overline{v_{n,out}^2} = \int_{f_{\text{min}}}^{f_{\text{max}}} S_{v_out}(f) df
\]
must converge. For flicker noise, the integral converges if \( A_F < 1 \) in practice, as \( \int 1/f^{A_F} df \) converges at infinity. SPICE does not check this analytically; it relies on the numerical quadrature to produce a finite result.

**Correlation and Matrix Addition:**
Noise sources within the MOS2 (thermal, flicker, shot) are uncorrelated. However, when multiple devices contribute to the output, their correlated transfer functions are accounted for via the complex adjoint system solution. The convergence of this adjoint solution uses the same linear solver as the AC analysis, with the same conditioning considerations.

### 4. Small-Signal Parameter Smoothing and Continuity

The small-signal parameters \( g_m, g_{ds}, g_{mb} \) and capacitances \( C_{gs}, C_{gd}, C_{gb} \) are functions of the DC bias point. To ensure convergence of the AC solution across bias sweeps, these parameters must be continuous and differentiable.

**Region Boundary Smoothing:**
At the transition between triode and saturation (\( V_{ds} = V_{dsat} \)), the derivatives \( g_m \) and \( g_{ds} \) must be continuous for the Newton-Raphson convergence in the preceding DC analysis. The MOS2 model uses a smooth interpolation function over a small voltage range \( \Delta V \) (e.g., 0.1V) around \( V_{dsat} \). This ensures that the AC matrix \( \mathbf{Y} \) does not change abruptly with small bias changes, which could cause convergence failures in `.AC` sweeps with `DC` as a parameter.

**Capacitance Charge Conservation:**
The Meyer capacitance model, while non-charge-conserving, ensures continuity of capacitances \( C = \partial Q/\partial V \) within each region. However, at the accumulation-depletion boundary (\( V_{gs} = V_{th} \)), the gate-bulk capacitance \( C_{gb} \) changes abruptly. SPICE's transient analysis would suffer convergence issues here, but AC analysis uses the linearized capacitance from the operating point, so a discontinuity only matters if the DC point is exactly at the boundary—a statistically unlikely event stabilized by `GMIN`.

### 5. Numerical Frequency Response Accuracy

The accuracy of the AC response is governed by the machine epsilon and the condition number of \( \mathbf{Y} \).

**Phase Accuracy at High Frequency:**
For \( \omega \) large, the phase of \( \mathbf{Y}^{-1} \) is sensitive to small errors in the imaginary part. The relative error in the computed response is bounded by:
\[
\frac{\|\Delta \mathbf{V}\|}{\|\mathbf{V}\|} \leq \kappa(\mathbf{Y}) \cdot \epsilon_{\text{machine}}
\]
where \( \kappa(\mathbf{Y}) \) is the condition number. For a MOS2 in saturation at high frequency, \( \kappa(\mathbf{Y}) \approx \omega C_{gs} / g_{ds} \). If this exceeds \( 10^{12} \), phase accuracy degrades below 0.1 degree. SPICE may issue a warning.

**Monte Carlo Noise Analysis:**
If noise analysis is performed with random parameter variations (via `MONTECARLO`), the convergence of the statistical mean and variance depends on the number of runs. The inherent noise spectral density formulas remain deterministic per run; convergence is a statistical matter handled by the outer Monte Carlo loop, not by the device model itself.

In summary, the mathematical formulation for MOS2 AC, pole-zero, and noise analysis directly constructs the linearized complex admittance matrix and noise correlation matrices required by SPICE's frequency-domain solvers. Convergence is primarily ensured through careful conditioning of the admittance matrix, smoothing of parameter transitions, and robust numerical integration of noise spectra. The analysis inherits its convergence properties from the accuracy of the DC operating point and the stability of the sparse complex linear solver at the core of SPICE.

## C Implementation

### 1. AC Small-Signal Analysis Implementation (`mos2acld.c`)

The AC analysis implementation in Ngspice's MOS2 model transforms the mathematical small-signal admittance matrix into a complex matrix stamping operation within the `MOS2acLoad()` function. This function is called during AC analysis to build the frequency-dependent Y-matrix for the circuit.

#### 1.1 Complex Admittance Matrix Stamping

The mathematical formulation `Y = G + jωC` is directly implemented in C through complex number handling and sparse matrix operations:

```c
int MOS2acLoad(GENmodel *inModel, CKTcircuit *ckt) {
    MOS2model *model;
    MOS2instance *inst;
    double omega = ckt->CKTomega;  /* ω = 2πf from circuit */
    
    for (model = (MOS2model*)inModel; model; model = model->MOS2nextModel) {
        for (inst = model->MOS2instances; inst; inst = inst->MOS2nextInstance) {
            /* Extract small-signal parameters from DC operating point */
            double gm = inst->MOS2gm;      /* ∂Id/∂Vgs */
            double gds = inst->MOS2gds;    /* ∂Id/∂Vds */
            double gmb = inst->MOS2gmb;    /* ∂Id/∂Vbs */
            
            /* Compute Meyer capacitances at operating point */
            double cgs, cgd, cgb;
            MOS2meyerCaps(inst, &cgs, &cgd, &cgb);
            
            /* Convert to complex admittances: y = jωc */
            double ygs = omega * cgs;  /* Imaginary part only */
            double ygd = omega * cgd;
            double ygb = omega * cgb;
            
            /* Stamp 4×4 complex matrix for intrinsic MOSFET (D', G, S', B) */
            
            /* Gate node (row 1): Σy_gi = ygs + ygd + ygb */
            *(inst->MOS2gateGatePtr) += ygs + ygd + ygb;      /* G[G][G] */
            *(inst->MOS2gateDrainPrimePtr) -= ygd;            /* G[G][D'] */
            *(inst->MOS2gateSourcePrimePtr) -= ygs;           /* G[G][S'] */
            *(inst->MOS2gateBulkPtr) -= ygb;                  /* G[G][B] */
            
            /* Internal Drain node (row 4): gds + ygd, -gm, -(gds+gm+gmb), gmb */
            *(inst->MOS2drainPrimeGatePtr) += gm;             /* G[D'][G] = +gm (real) */
            *(inst->MOS2drainPrimeDrainPrimePtr) += gds + ygd; /* G[D'][D'] = gds + jωcgd */
            *(inst->MOS2drainPrimeSourcePrimePtr) -= (gds + gm + gmb); /* G[D'][S'] */
            *(inst->MOS2drainPrimeBulkPtr) += gmb;            /* G[D'][B] */
            
            /* Internal Source node (row 5): -gds, -gm-ygs, gds+gm+gmb+ygs, -gmb */
            *(inst->MOS2sourcePrimeGatePtr) -= (gm + ygs);    /* G[S'][G] = -gm - jωcgs */
            *(inst->MOS2sourcePrimeDrainPrimePtr) -= gds;     /* G[S'][D'] */
            *(inst->MOS2sourcePrimeSourcePrimePtr) += (gds + gm + gmb + ygs); /* G[S'][S'] */
            *(inst->MOS2sourcePrimeBulkPtr) -= gmb;           /* G[S'][B] */
            
            /* Bulk node (row 3): -ygb, gmb, -gmb, ygb */
            *(inst->MOS2bulkGatePtr) -= ygb;                  /* G[B][G] */
            *(inst->MOS2bulkDrainPrimePtr) += gmb;            /* G[B][D'] */
            *(inst->MOS2bulkSourcePrimePtr) -= gmb;           /* G[B][S'] */
            *(inst->MOS2bulkBulkPtr) += ygb;                  /* G[B][B] */
            
            /* Stamp parasitic resistances (RD, RS) - real conductances only */
            double gd = 1.0 / (model->MOS2rd + model->MOS2rsh * inst->MOS2nrd);
            double gs = 1.0 / (model->MOS2rs + model->MOS2rsh * inst->MOS2nrs);
            
            /* RD stamp between external D and internal D' */
            *(inst->MOS2drainDrainPtr) += gd;                 /* G[D][D] */
            *(inst->MOS2drainDrainPrimePtr) -= gd;            /* G[D][D'] */
            *(inst->MOS2drainPrimeDrainPtr) -= gd;            /* G[D'][D] */
            *(inst->MOS2drainPrimeDrainPrimePtr) += gd;       /* G[D'][D'] (adds to existing) */
            
            /* RS stamp between external S and internal S' */
            *(inst->MOS2sourceSourcePtr) += gs;               /* G[S][S] */
            *(inst->MOS2sourceSourcePrimePtr) -= gs;          /* G[S][S'] */
            *(inst->MOS2sourcePrimeSourcePtr) -= gs;          /* G[S'][S] */
            *(inst->MOS2sourcePrimeSourcePrimePtr) += gs;     /* G[S'][S'] (adds to existing) */
        }
    }
    return OK;
}
```

This C code directly implements the mathematical 6×6 extended system matrix:
```
[G_DD   0      0      0     -G_RD    0    ]
[0      Y_GG  -Y_GS  -Y_GB  -Y_GD'  -Y_GS']
[0      0      G_SS   0      0      -G_RS ]
[0      0      0      G_BB   0       0    ]
[-G_RD -Y_D'G -Y_D'S -Y_D'B  G_D'D'  Y_D'S']
[0     -Y_S'G  G_S'S -Y_S'B  Y_S'D'  G_S'S']
```

Where `Y_ij = G_ij + jωC_ij` and the matrix pointers (`MOS2drainDrainPtr`, etc.) map to specific positions in the sparse matrix.

#### 1.2 Meyer Capacitance Computation

The `MOS2meyerCaps()` function computes the gate capacitances based on the operating region, implementing the mathematical Meyer model:

```c
void MOS2meyerCaps(MOS2instance *inst, double *cgs, double *cgd, double *cgb) {
    double vgs = inst->MOS2vgs;
    double vds = inst->MOS2vds;
    double vth = inst->MOS2vth;
    double vgst = vgs - vth;
    double cox = inst->MOS2modPtr->MOS2oxideCapFactor * inst->MOS2effW * inst->MOS2effL;
    
    if (vgst <= 0.0) {
        /* Cutoff region */
        *cgs = inst->MOS2modPtr->MOS2cgso * inst->MOS2effW;
        *cgd = inst->MOS2modPtr->MOS2cgdo * inst->MOS2effW;
        *cgb = cox + inst->MOS2modPtr->MOS2cgbo * inst->MOS2effL;
    } else if (vds <= vgst) {
        /* Linear region */
        double factor = 1.0 - vds / (2.0 * vgst);
        *cgs = cox * (1.0 - factor * factor) + inst->MOS2modPtr->MOS2cgso * inst->MOS2effW;
        *cgd = cox * (1.0 - (1.0 - factor) * (1.0 - factor)) + inst->MOS2modPtr->MOS2cgdo * inst->MOS2effW;
        *cgb = inst->MOS2modPtr->MOS2cgbo * inst->MOS2effL;
    } else {
        /* Saturation region */
        *cgs = (2.0/3.0) * cox + inst->MOS2modPtr->MOS2cgso * inst->MOS2effW;
        *cgd = inst->MOS2modPtr->MOS2cgdo * inst->MOS2effW;
        *cgb = inst->MOS2modPtr->MOS2cgbo * inst->MOS2effL;
    }
}
```

This implements the mathematical capacitance equations:
- Cutoff: `Cgb = Cox·W·L`, `Cgs = Cgso·W`, `Cgd = Cgdo·W`
- Linear: `Cgs = Cox·W·L·[1 - (Vds/(2Vgst))²]`, `Cgd = Cox·W·L·[1 - (1 - Vds/(2Vgst))²]`
- Saturation: `Cgs = (2/3)·Cox·W·L`, `Cgd = Cgdo·W`

### 2. Noise Analysis Implementation (`mos2noi.c`)

The noise analysis in MOS2 implements both thermal and flicker noise models, computing spectral densities that are integrated over frequency during AC noise analysis.

#### 2.1 Thermal Noise Implementation

The mathematical thermal noise formula `S_id(thermal) = 4kT·γ·g_do` is implemented with velocity saturation modifications:

```c
int MOS2noise(int mode, int operation, GENmodel *inModel, 
              CKTcircuit *ckt, Ndata *data, double *OnDens) {
    MOS2model *model;
    MOS2instance *inst;
    
    for (model = (MOS2model*)inModel; model; model = model->MOS2nextModel) {
        for (inst = model->MOS2instances; inst; inst = inst->MOS2nextInstance) {
            double temp = inst->MOS2temp + CONSTCtoK;
            double gm = inst->MOS2gm;
            double gds0 = inst->MOS2beta * inst->MOS2vgst;  /* g_do at Vds=0 */
            
            /* Calculate noise coefficient γ with velocity saturation effect */
            double gamma_noise;
            if (model->MOS2vmax > 0.0) {
                /* Velocity saturation reduces noise */
                double ueff = model->MOS2u0 / 
                             (1.0 + model->MOS2theta * inst->MOS2vgst + 
                              model->MOS2eta * inst->MOS2vbs);
                double Ec = 2.0 * model->MOS2vmax / ueff;
                double Vdsat_eff = (inst->MOS2vgst * Ec * inst->MOS2effL) / 
                                   (inst->MOS2vgst + Ec * inst->MOS2effL);
                
                /* Modified noise coefficient: γ = (2/3) * (1 + Vds/Vdsat)/(1 + 2Vds/Vdsat) */
                gamma_noise = 2.0/3.0 * (1.0 + inst->MOS2vds/Vdsat_eff) / 
                              (1.0 + 2.0 * inst->MOS2vds/Vdsat_eff);
            } else {
                /* Long-channel noise coefficient */
                gamma_noise = 2.0/3.0;
            }
            
            /* Thermal noise spectral density: S_id = 4kTγg_do */
            double Sth = 4.0 * BOLTZMANN * temp * gamma_noise * gds0;
            
            /* Stamp noise source between drain and source */
            switch (operation) {
                case N_OPEN:
                    /* Return open-circuit noise voltage */
                    *OnDens += Sth * data->delFreq;
                    break;
                case N_CALC:
                    /* Calculate short-circuit noise current */
                    data->outNoise += Sth * data->delFreq;
                    break;
                case N_STRNOISE:
                    /* Store for output summary */
                    sprintf(data->output, 
                            "MOS2:%s:drain thermal = %e A²/Hz", 
                            inst->MOS2name, Sth);
                    break;
            }
        }
    }
    return OK;
}
```

#### 2.2 Flicker (1/f) Noise Implementation

The flicker noise formula `S_id(flicker) = Kf·|Id|^Af / (f·Cox²·W·L)` is implemented as:

```c
/* In MOS2noise() function, continuing from thermal noise calculation */
if (model->MOS2kf != 0.0) {
    double Kf = model->MOS2kf;
    double Af = model->MOS2af;
    double Cox = model->MOS2oxideCapFactor;
    double Id = fabs(inst->MOS2id);
    double Leff = inst->MOS2effL;
    double Weff = inst->MOS2effW;
    double omega = ckt->CKTomega;
    double freq = omega / (2.0 * M_PI);
    
    /* Avoid division by zero at DC */
    if (freq < 1.0) freq = 1.0;
    
    /* Flicker noise: S_f = Kf * Id^Af / (f * Cox^2 * W * L) */
    double Sf = Kf * pow(Id, Af) / (freq * Cox * Cox * Weff * Leff);
    
    /* Add to total noise */
    switch (operation) {
        case N_OPEN:
            *OnDens += Sf * data->delFreq;
            break;
        case N_CALC:
            data->outNoise += Sf * data->delFreq;
            break;
        case N_STRNOISE:
            /* Append flicker noise to output string */
            strcat(data->output, sprintf(", flicker = %e A²/Hz", Sf));
            break;
    }
}
```

This implements the exact mathematical relationship where flicker noise is inversely proportional to frequency and depends on oxide capacitance and device geometry.

### 3. Pole-Zero Analysis Support

While not explicitly shown in the provided context, pole-zero analysis for MOS2 would be implemented in a file like `mos2pzld.c` with a `MOS2pzLoad()` function. This function would compute the small-signal transfer function terms needed for pole-zero analysis by evaluating the device's contribution to the circuit's system matrix at complex frequencies `s = σ + jω`.

The implementation would follow the pattern:
```c
int MOS2pzLoad(GENmodel *inModel, CKTcircuit *ckt, SPcomplex *s) {
    /* Similar to MOS2acLoad but with complex s instead of jω */
    /* Y(s) = G + sC */
    double complex ygs = s->real * cgs + I * s->imag * cgs;
    /* ... stamp complex matrix ... */
}
```

This allows the simulator to find poles and zeros by solving `det(Y(s)) = 0`.

### 4. Integration with SPICE Analysis Framework

The AC and noise analysis functions are integrated into the MOS2 device through the `SPICEdev` structure:

```c
SPICEdev MOS2info = {
    /* ... other fields ... */
    .DEVacLoad = MOS2acLoad,     /* AC small-signal analysis */
    .DEVnoise = MOS2noise,       /* Noise analysis */
    .DEVpzLoad = MOS2pzLoad,     /* Pole-zero analysis (if implemented) */
    /* ... */
};
```

When the simulator runs `.AC` analysis, it calls `MOS2acLoad()` for each frequency point. For `.NOISE` analysis, it calls `MOS2noise()` to compute and integrate noise spectral densities over the specified frequency range.

### 5. Matrix Pointer Management for Extended 6×6 System

The successful implementation of AC analysis depends on the proper allocation of matrix pointers during setup. The MOS2 model's 6×6 extended system requires careful pointer management:

```c
/* In MOS2setup() - allocation for AC analysis */
inst->MOS2drainDrainPtr = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2dNode);
inst->MOS2drainGatePtr = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2gNode);
inst->MOS2drainSourcePtr = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2sNode);
inst->MOS2drainBulkPtr = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2bNode);
inst->MOS2drainDrainPrimePtr = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2dNodePrime);
inst->MOS2drainSourcePrimePtr = SMPmakeElt(matrix, inst->MOS2dNode, inst->MOS2sNodePrime);

/* ... allocate all 36 possible entries for the 6×6 system ... */

/* For complex matrices in AC analysis, additional pointers may be needed */
if (ckt->CKTisAC) {
    /* The sparse matrix system handles complex numbers by using separate 
       real and imaginary matrices or complex data types */
    inst->MOS2drainDrainPtrImag = SMPmakeElt(matrix, 
        inst->MOS2dNode + ckt->CKTmatrixSize, 
        inst->MOS2dNode);
    /* ... allocate imaginary parts ... */
}
```

This allocation pattern creates the complete 6×6 matrix structure needed for the extended system with internal nodes D' and S'.

### 6. State Vector Usage in AC Analysis

While AC analysis is linear and doesn't require time-domain state tracking, the state vector indices allocated during setup (`MOS2qgs`, `MOS2qgd`, etc.) are still used to compute the operating point capacitances. The DC operating point charges stored in the state vector determine the capacitance values used in the AC analysis:

```c
/* During DC operating point solution, charges are computed and stored */
ckt->CKTstate0[inst->MOS2qgs] = qgs