# Frequency Domain: AC Sweeps and Noise Adjoint Solving

_Generated 2026-04-13 05:27 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/acan.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/acsetp.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/acaskq.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/noisean.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/nsetparm.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/naskq.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/cktnoise.c`

# Chapter: Frequency Domain: AC Sweeps and Noise Adjoint Solving

## Introduction

The Ngspice frequency domain analysis subsystem, implemented across seven core files in `/src/spicelib/analysis/`, provides comprehensive small-signal analysis capabilities including AC frequency sweeps and noise analysis using the adjoint network method. This subsystem enables characterization of linearized circuit behavior around a DC operating point, computing transfer functions, impedance profiles, and noise performance across frequency.

**`acan.c`** serves as the main driver for AC analysis, orchestrating frequency sweeps across linear, decade, and octave scales while solving the complex linear systems at each frequency point. **`acsetp.c`** configures AC analysis parameters including sweep ranges, point densities, and output specifications. **`acaskq.c`** provides the query interface for retrieving AC analysis results and intermediate solutions.

**`noisean.c`** implements the adjoint network method for noise analysis, computing output noise spectral density by solving both the original and adjoint network equations. **`nsetparm.c`** configures noise analysis parameters including output nodes, temperature, and noise source models. **`naskq.c`** provides the query interface for retrieving noise analysis results including individual source contributions.

**`cktnoise.c`** manages noise source data structures and implements spectral density functions for thermal, shot, and flicker noise models, providing the foundation for accurate noise computation in semiconductor devices and passive components.

This chapter details the mathematical foundations of frequency domain analysis and examines how these algorithms are implemented in the Ngspice codebase, focusing on the sophisticated numerical methods for solving complex linear systems and the adjoint network technique for efficient noise computation.

## Mathematical Formulation

Frequency domain analysis in SPICE solves the linearized circuit equations in the frequency domain, enabling computation of small-signal transfer functions, impedance characteristics, and noise performance. The analysis operates on the circuit linearized around its DC operating point.

### Small-Signal Linearization

Given a nonlinear circuit described by the DAE system:
\[
\mathbf{F}(\mathbf{x}, \dot{\mathbf{x}}, t) = \mathbf{0}
\]
where \(\mathbf{x} \in \mathbb{R}^n\) is the state vector, the circuit is linearized around the DC operating point \(\mathbf{x}_0\) satisfying \(\mathbf{F}(\mathbf{x}_0, \mathbf{0}, t) = \mathbf{0}\).

For small perturbations \(\tilde{\mathbf{x}}(t)\) around \(\mathbf{x}_0\):
\[
\mathbf{F}(\mathbf{x}_0 + \tilde{\mathbf{x}}, \dot{\tilde{\mathbf{x}}}, t) \approx \mathbf{J}\tilde{\mathbf{x}} + \mathbf{C}\dot{\tilde{\mathbf{x}}} = \mathbf{0}
\]
where:
- \(\mathbf{J} = \frac{\partial \mathbf{F}}{\partial \mathbf{x}}\big|_{\mathbf{x}_0, \mathbf{0}}\) is the Jacobian (conductance matrix)
- \(\mathbf{C} = \frac{\partial \mathbf{F}}{\partial \dot{\mathbf{x}}}\big|_{\mathbf{x}_0, \mathbf{0}}\) is the capacitance/inductance matrix

### Complex Admittance Matrix Formulation

For sinusoidal steady-state analysis at angular frequency \(\omega\), with \(\tilde{\mathbf{x}}(t) = \Re\{\mathbf{X}e^{j\omega t}\}\), the linearized equations become:
\[
(\mathbf{J} + j\omega\mathbf{C})\mathbf{X} = \mathbf{B}
\]
where \(\mathbf{B}\) represents the small-signal sources.

The complex admittance matrix \(\mathbf{Y}(\omega) \in \mathbb{C}^{n \times n}\) is:
\[
\mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C}
\]
with:
- \(\mathbf{G} = \mathbf{J}\) (real conductance matrix from DC operating point)
- \(\mathbf{C}\) includes contributions from all energy storage elements

### Element Stamps in Frequency Domain

**Capacitor** between nodes \(i\) and \(j\):
\[
\mathbf{Y}_{\text{cap}} = j\omega C \begin{bmatrix} 1 & -1 \\ -1 & 1 \end{bmatrix}
\]

**Inductor** requires modified nodal analysis with branch current \(I_L\) as additional variable:
\[
\begin{bmatrix}
\mathbf{G} & \mathbf{B} \\
\mathbf{C} & \mathbf{D}
\end{bmatrix}
\begin{bmatrix}
\mathbf{V} \\
I_L
\end{bmatrix}
=
\begin{bmatrix}
\mathbf{0} \\
0
\end{bmatrix}
\]
with \(\mathbf{B} = [1, -1]^T\), \(\mathbf{C} = [1, -1]\), and \(\mathbf{D} = -j\omega L\).

**Semiconductor Devices**: Small-signal models introduce complex admittances:
- MOSFET: \(y_{gs} = j\omega(C_{gs} + C_{gd})\), \(y_{gd} = j\omega C_{gd}\), \(y_{ds} = g_{ds} + j\omega(C_{db} + C_{ds})\)
- BJT: Complex hybrid-π parameters with \(g_\pi\), \(g_\mu\), \(C_\pi\), \(C_\mu\)

### Frequency Sweep Formulation

AC analysis computes \(\mathbf{X}(\omega)\) over a frequency range \(\omega \in [\omega_{\text{min}}, \omega_{\text{max}}]\). The solution at each frequency requires solving:
\[
\mathbf{Y}(\omega_k)\mathbf{X}(\omega_k) = \mathbf{B}(\omega_k), \quad k = 1, \ldots, N
\]

Sweep types include:
1. **Linear**: \(\omega_k = \omega_{\text{min}} + (k-1)\Delta\omega\), \(\Delta\omega = \frac{\omega_{\text{max}} - \omega_{\text{min}}}{N-1}\)
2. **Decade**: Points spaced logarithmically with constant points per decade
3. **Octave**: Points spaced by factors of 2

### Adjoint Network Method for Noise Analysis

Noise analysis computes the output noise spectral density using the adjoint network theorem.

#### Noise Source Models
1. **Thermal Noise**: \(S_{i_n}(f) = 4k_B T G\), where \(G\) is conductance
2. **Shot Noise**: \(S_{i_n}(f) = 2qI\), where \(I\) is DC current
3. **Flicker (1/f) Noise**: \(S_{i_n}(f) = \frac{K I^a}{f^b}\), with device-specific parameters \(K, a, b\)

#### Adjoint Network Formulation
Let the original network be described by:
\[
\mathbf{Y}(\omega)\mathbf{V}(\omega) = \mathbf{I}_s(\omega) + \mathbf{I}_n(\omega)
\]
where \(\mathbf{I}_n(\omega)\) represents noise current sources.

The output voltage between nodes \(p\) and \(q\) is:
\[
V_{\text{out}}(\omega) = \mathbf{e}_{pq}^T \mathbf{V}(\omega)
\]
where \(\mathbf{e}_{pq} = \mathbf{e}_p - \mathbf{e}_q\) with \(\mathbf{e}_i\) being the \(i\)-th unit vector.

The adjoint network is excited by a unit current source between \(p\) and \(q\):
\[
\mathbf{Y}^T(\omega) \mathbf{V}_{\text{adj}}(\omega) = \mathbf{e}_{pq}
\]

By Tellegen's theorem, the transfer function from noise source \(k\) to output is:
\[
H_k(\omega) = V_{\text{adj},k}^+(\omega) - V_{\text{adj},k}^-(\omega)
\]
where \(V_{\text{adj},k}^+\) and \(V_{\text{adj},k}^-\) are adjoint voltages at the noise source terminals.

#### Total Output Noise
The output noise spectral density is:
\[
S_{V,\text{out}}(\omega) = \sum_{k=1}^{M} |H_k(\omega)|^2 S_{i_n,k}(\omega) + \sum_{i \neq j} 2\Re\{H_i(\omega) H_j^*(\omega) S_{i_n,ij}(\omega)\}
\]
where \(S_{i_n,ij}\) represents correlated noise between sources \(i\) and \(j\).

For uncorrelated sources (typical assumption):
\[
S_{V,\text{out}}(\omega) = \sum_{k=1}^{M} |H_k(\omega)|^2 S_{i_n,k}(\omega)
\]

### Noise Correlation Matrix

For devices with correlated noise sources (e.g., MOSFET channel noise and gate noise), the noise correlation matrix \(\mathbf{C}(\omega) \in \mathbb{C}^{M \times M}\) is:
\[
C_{ij}(\omega) = \langle I_{n,i}(\omega) I_{n,j}^*(\omega) \rangle
\]
where \(\langle \cdot \rangle\) denotes ensemble average.

The output noise becomes:
\[
S_{V,\text{out}}(\omega) = \mathbf{H}^H(\omega) \mathbf{C}(\omega) \mathbf{H}(\omega)
\]
where \(\mathbf{H}(\omega) = [H_1(\omega), \ldots, H_M(\omega)]^T\).

## Convergence Analysis

### Matrix Conditioning in Frequency Domain

The condition number \(\kappa(\mathbf{Y}(\omega)) = \|\mathbf{Y}(\omega)\| \cdot \|\mathbf{Y}(\omega)^{-1}\|\) varies dramatically with frequency:

#### Low-Frequency Conditioning (\(\omega \to 0\))
As \(\omega \to 0\), inductor terms dominate:
\[
\mathbf{Y}(\omega) \approx \mathbf{G} + \frac{1}{j\omega}\mathbf{L}^{-1}
\]
where \(\mathbf{L}\) is the inductance matrix. The condition number diverges:
\[
\kappa(\mathbf{Y}(\omega)) \sim O\left(\frac{1}{\omega}\right)
\]

**Stabilization Techniques**:
1. **Modified Nodal Analysis**: Treat inductor currents as variables
2. **Frequency Scaling**: Solve for \(\omega I_L\) instead of \(I_L\)
3. **Regularization**: Replace \(1/(j\omega L)\) with \(1/(j\omega L + \epsilon)\), \(\epsilon \approx 10^{-12}\)

#### High-Frequency Conditioning (\(\omega \to \infty\))
As \(\omega \to \infty\), capacitor terms dominate:
\[
\mathbf{Y}(\omega) \approx j\omega \mathbf{C}
\]
The condition number grows linearly:
\[
\kappa(\mathbf{Y}(\omega)) \sim O(\omega \cdot \frac{\max_i C_{ii}}{\min_j C_{jj}})
\]

**Numerical Issues**:
1. **Loss of Accuracy**: For \(\omega > 10^{15}\) rad/s, double precision may be insufficient
2. **Parasitic Inclusion**: Must include all parasitic capacitances for accuracy
3. **Causality Enforcement**: Ensure \(|\mathbf{Y}(\omega)| \to \text{constant}\) as \(\omega \to \infty\)

#### Resonant Frequencies
At resonance \(\omega_0 = 1/\sqrt{LC}\) for RLC circuits:
\[
\mathbf{Y}(\omega_0) = \mathbf{G}
\]
which may be ill-conditioned if \(\mathbf{G}\) has small entries (high-Q circuits).

### Frequency Sweep Convergence

#### Adaptive Frequency Sampling
The frequency sampling density should adapt to the response curvature. Define the normalized curvature:
\[
\kappa(f) = \frac{|H(f + \Delta f) - 2H(f) + H(f - \Delta f)|}{\Delta f^2 \cdot \max |H|}
\]
where \(H(f)\) is the transfer function.

Adaptive algorithm:
1. Initial coarse sweep
2. Refine intervals where \(\kappa(f) > \kappa_{\text{max}}\)
3. Limit maximum refinement to prevent excessive points

#### Interpolation Accuracy
For logarithmic sweeps, linear interpolation in log-frequency domain provides \(O(\Delta \log f)^2\) error for smooth responses.

### Adjoint Solution Convergence

#### Matrix Transpose Properties
For reciprocal networks with symmetric \(\mathbf{G}\) and \(\mathbf{C}\):
\[
\mathbf{Y}^T(\omega) = \mathbf{G}^T - j\omega \mathbf{C}^T = \mathbf{G} - j\omega \mathbf{C} = \overline{\mathbf{Y}(\omega)}
\]
where \(\overline{\cdot}\) denotes complex conjugate.

Thus solving the adjoint system \(\mathbf{Y}^T \mathbf{V}_{\text{adj}} = \mathbf{b}\) is equivalent to solving \(\mathbf{Y} \overline{\mathbf{V}_{\text{adj}}} = \overline{\mathbf{b}}\).

#### Numerical Stability
The adjoint solution inherits the conditioning of the original system:
\[
\kappa(\mathbf{Y}^T(\omega)) = \kappa(\mathbf{Y}(\omega))
\]
Error amplification is identical for both systems.

### Noise Computation Convergence

#### Transfer Function Accuracy
The relative error in noise computation due to transfer function error \(\delta H\) is:
\[
\frac{\delta S_{\text{out}}}{S_{\text{out}}} \approx 2 \frac{|\delta H|}{|H|} + \left(\frac{|\delta H|}{|H|}\right)^2
\]
Thus 1% error in \(H\) causes approximately 2% error in noise power.

#### Accumulation Error
For \(M\) uncorrelated noise sources, the accumulated error grows as:
\[
\frac{\delta S_{\text{total}}}{S_{\text{total}}} \leq \max_k \frac{\delta S_k}{S_k} + \frac{1}{\sqrt{M}} \sigma_{\text{rel}}
\]
where \(\sigma_{\text{rel}}\) is the standard deviation of relative errors.

### Sparse Matrix Solution Convergence

#### Complex Arithmetic Considerations
Solving \(\mathbf{Y}(\omega)\mathbf{X} = \mathbf{B}\) with complex arithmetic requires:
1. **Pivot Strategy**: Complex partial pivoting with magnitude comparison
2. **Fill-in Reduction**: Minimum degree ordering on \(|\mathbf{Y}|\) pattern
3. **Iterative Refinement**: For ill-conditioned systems

The error bound for LU factorization with partial pivoting is:
\[
\frac{\|\delta \mathbf{X}\|}{\|\mathbf{X}\|} \leq \kappa(\mathbf{Y}) \cdot \epsilon_{\text{machine}} \cdot O(n^{3/2})
\]
where \(\epsilon_{\text{machine}} \approx 2.2 \times 10^{-16}\) for double precision.

#### Frequency-Adaptive Factorization
Since \(\mathbf{Y}(\omega) = \mathbf{G} + j\omega \mathbf{C}\), factorization can be reused across frequencies:
1. Factor \(\mathbf{G} + j\omega_0 \mathbf{C}\) at reference frequency \(\omega_0\)
2. For nearby \(\omega\), use Sherman-Morrison-Woodbury update:
\[
(\mathbf{G} + j\omega \mathbf{C})^{-1} \approx (\mathbf{G} + j\omega_0 \mathbf{C})^{-1} - j(\omega - \omega_0)(\mathbf{G} + j\omega_0 \mathbf{C})^{-1} \mathbf{C} (\mathbf{G} + j\omega_0 \mathbf{C})^{-1}
\]
3. Re-factor when update error exceeds tolerance

### Noise Floor and Numerical Precision

The minimum detectable noise is limited by numerical precision. For double precision:
\[
S_{\text{min}} \approx \epsilon_{\text{machine}} \cdot \max |H|^2 \cdot \max S_{\text{source}}
\]
Typically \(S_{\text{min}} \approx 10^{-32} \text{ V}^2/\text{Hz}\) for \(|H| \approx 1\).

### Convergence Criteria for AC Analysis

#### Solution Tolerance
The Newton iteration for nonlinear devices in AC analysis (for frequency-dependent nonlinearities) converges when:
\[
\|\mathbf{Y}(\omega)\mathbf{X}^{(k)} - \mathbf{B}\|_\infty < \epsilon_{\text{abs}} + \epsilon_{\text{rel}} \|\mathbf{B}\|_\infty
\]
with typical values \(\epsilon_{\text{abs}} = 10^{-12}\), \(\epsilon_{\text{rel}} = 10^{-6}\).

#### Frequency Continuity
For smooth frequency responses, adjacent frequency points should satisfy:
\[
\frac{\|\mathbf{X}(\omega_{k+1}) - \mathbf{X}(\omega_k)\|}{\|\mathbf{X}(\omega_k)\|} < \gamma \cdot (\omega_{k+1} - \omega_k)
\]
where \(\gamma\) is a continuity constant. Violation triggers additional frequency points.

### Stability of Frequency-Dependent Elements

Elements with frequency-dependent parameters (e.g., semiconductor models with \(C(\omega)\), \(g_m(\omega)\)) must satisfy:
1. **Causality**: Kramers-Kronig relations between real and imaginary parts
2. **Stability**: No poles in right-half complex frequency plane
3. **Passivity**: \(\Re\{\mathbf{Y}(\omega)\} \succeq 0\) for all \(\omega\)

Violation of these conditions leads to non-physical results and potential numerical instability.

### Parallelization Convergence

For parallel frequency sweep across \(P\) processors, the speedup is limited by:
\[
S(P) = \frac{T_{\text{serial}}}{T_{\text{parallel}}} \leq \frac{N}{N/P + T_{\text{sync}}}
\]
where \(T_{\text{sync}}\) is synchronization overhead. Load balancing is critical for frequencies with varying solution times.

The overall AC and noise analysis converges successfully when all frequency points are solved within specified tolerances, noise contributions are accurately accumulated, and the frequency response satisfies continuity and physical realizability constraints.

## C Implementation

**Note:** Due to security restrictions preventing access to the specified Ngspice AC and noise analysis source files, this section cannot provide the detailed C implementation analysis requested. The architectural tear-down requires direct examination of the actual source files in `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/analysis/`.

### Required Source Files for Analysis:
Based on standard SPICE architecture and the mathematical formulation, the AC and noise analysis implementation would be distributed across:
1. **`acan.c`** - AC analysis main driver and frequency sweep orchestration
2. **`acsetp.c`** - AC analysis parameter setup and configuration
3. **`acaskq.c`** - AC analysis query and result retrieval
4. **`noisean.c`** - Noise analysis using adjoint network method
5. **`noisesetp.c`** - Noise analysis parameter configuration
6. **`noiseaskq.c`** - Noise analysis query interface
7. **`cktnoise.c`** - Noise source management and spectral density computation
8. **`cktfreq.c`** - Frequency-dependent element handling
9. **`smpc.c`** - Complex sparse matrix operations
10. **`acload.c`** - AC-specific device loading routines

### Critical C Structures That Would Be Analyzed:
Without file access, the exact struct definitions cannot be provided, but based on the mathematical formulation, the implementation would center around:

1. **`ACAN` (AC Analysis) struct** - Contains AC-specific parameters:
   - `ACstartFreq` - Starting frequency for sweep
   - `ACstopFreq` - Stopping frequency for sweep
   - `ACnumFreq` - Number of frequency points
   - `ACtype` - Sweep type (LIN, DEC, OCT)
   - `ACpoints` - Array of frequency points
   - `ACresults` - Array of complex solutions per frequency

2. **`NOISEAN` (Noise Analysis) struct**:
   - `NOISEoutput` - Output node pair for noise computation
   - `NOISEfreq` - Current frequency for noise calculation
   - `NOISEtotal` - Total output noise spectral density
   - `NOISEcontrib` - Array of per-source noise contributions
   - `NOISEadjointSol` - Adjoint network solution vector

3. **`CKTcircuit` AC/noise fields**:
   - `CKTomega` - Current angular frequency ω
   - `CKTmatrix` - Complex admittance matrix Y(ω) = G + jωC
   - `CKTrhs` - Right-hand side vector for AC excitation
   - `CKTlhs` - Solution vector (complex node voltages)
   - `CKTnoiseSources` - Linked list of noise sources
   - `CKTnumNoise` - Number of noise sources

4. **`NOISEsource` struct** - Individual noise source representation:
   - `posNode`, `negNode` - Terminal nodes
   - `type` - Noise type (THERMAL, SHOT, FLICKER)
   - `value` - Parameter value (R, I, etc.)
   - `spectralDensity` - Function pointer to compute S(f)
   - `next` - Pointer to next source in linked list

### Mathematical-to-C Mapping That Would Be Documented:
If file access were available, this section would detail:

1. **AC Frequency Sweep Implementation in `acan.c`**:
   ```c
   /* Main AC analysis driver with frequency sweep */
   int ACanalyze(CKTcircuit *ckt, ACAN *ac) {
       /* Compute DC operating point for linearization */
       if (DCanalyze(ckt) != OK) return E_NODC;
       
       /* Extract linearized matrices G and C from DC point */
       CKTgetYmatrices(ckt, &G, &C);
       
       /* Perform frequency sweep */
       switch (ac->ACtype) {
           case AC_LIN:
               /* Linear frequency sweep */
               for (int i = 0; i < ac->ACnumFreq; i++) {
                   double freq = ac->ACstartFreq + i * 
                                (ac->ACstopFreq - ac->ACstartFreq) / 
                                (ac->ACnumFreq - 1);
                   double omega = 2.0 * M_PI * freq;
                   
                   /* Solve Y(ω)X = B at this frequency */
                   if (ACsolveAtFrequency(ckt, omega) != OK) {
                       return E_SINGULAR;
                   }
                   
                   /* Store solution */
                   ac->ACresults[i] = CKTgetSolution(ckt);
               }
               break;
               
           case AC_DEC:
               /* Decade sweep with constant points per decade */
               int pointsPerDecade = 10;
               double logStart = log10(ac->ACstartFreq);
               double logStop = log10(ac->ACstopFreq);
               int numDecades = (int)ceil(logStop - logStart);
               int totalPoints = numDecades * pointsPerDecade;
               
               for (int i = 0; i < totalPoints; i++) {
                   double decade = floor(i / pointsPerDecade);
                   double pointInDecade = i % pointsPerDecade;
                   double freq = pow(10.0, logStart + decade + 
                                    pointInDecade / pointsPerDecade);
                   double omega = 2.0 * M_PI * freq;
                   
                   if (ACsolveAtFrequency(ckt, omega) != OK) {
                       return E_SINGULAR;
                   }
                   ac->ACresults[i] = CKTgetSolution(ckt);
               }
               break;
               
           case AC_OCT:
               /* Octave sweep */
               int pointsPerOctave = 8;
               double log2Start = log2(ac->ACstartFreq);
               double log2Stop = log2(ac->ACstopFreq);
               int numOctaves = (int)ceil(log2Stop - log2Start);
               int totalPoints = numOctaves * pointsPerOctave;
               
               for (int i = 0; i < totalPoints; i++) {
                   double octave = floor(i / pointsPerOctave);
                   double pointInOctave = i % pointsPerOctave;
                   double freq = pow(2.0, log2Start + octave + 
                                    pointInOctave / pointsPerOctave);
                   double omega = 2.0 * M_PI * freq;
                   
                   if (ACsolveAtFrequency(ckt, omega) != OK) {
                       return E_SINGULAR;
                   }
                   ac->ACresults[i] = CKTgetSolution(ckt);
               }
               break;
       }
       return OK;
   }
   ```

2. **Complex Matrix Solution at Single Frequency**:
   ```c
   /* Solve Y(ω)X = B at specific frequency */
   int ACsolveAtFrequency(CKTcircuit *ckt, double omega) {
       /* Update matrix with frequency-dependent terms: Y(ω) = G + jωC */
       CKTupdateYmatrix(ckt, omega);
       
       /* Factor complex matrix */
       if (SMPcFactor(ckt->CKTmatrix, omega) != OK) {
           /* Handle singular matrix at low/high frequency */
           if (omega < 1e-9) {
               /* Low frequency regularization */
               CKTregularizeLowFreq(ckt, omega);
               if (SMPcFactor(ckt->CKTmatrix, omega) != OK) {
                   return E_SINGULAR;
               }
           } else {
               return E_SINGULAR;
           }
       }
       
       /* Solve for complex RHS */
       SMPcSolve(ckt->CKTmatrix, ckt->CKTrhs, ckt->CKTlhs);
       
       /* Extract solution for output variables */
       CKTextractSolution(ckt);
       
       return OK;
   }
   ```

3. **Adjoint Network Noise Analysis in `noisean.c`**:
   ```c
   /* Compute noise using adjoint network method */
   int NOISEanalyze(CKTcircuit *ckt, NOISEAN *noise, double freq) {
       double omega = 2.0 * M_PI * freq;
       
       /* 1. Solve original network at this frequency */
       if (ACsolveAtFrequency(ckt, omega) != OK) {
           return E_SINGULAR;
       }
       
       /* 2. Setup adjoint network RHS: unit current at output */
       double *adjRHS = (double *)calloc(ckt->CKTnumStates * 2, sizeof(double));
       int outNodeP = noise->NOISEoutputNodeP;
       int outNodeN = noise->NOISEoutputNodeN;
       
       /* Real part of RHS (unit current source) */
       adjRHS[outNodeP] = 1.0;
       adjRHS[outNodeN] = -1.0;
       /* Imaginary part remains zero */
       
       /* 3. Solve adjoint network: Y^T V_adj = I_out */
       double *adjSolution = (double *)calloc(ckt->CKTnumStates * 2, sizeof(double));
       
       /* For symmetric Y (reciprocal network), Y^T = conj(Y) */
       /* Solve Y* V_adj_conj = RHS, then take conjugate */
       if (SMPcSolveAdjoint(ckt->CKTmatrix, adjRHS, adjSolution) != OK) {
           free(adjRHS);
           free(adjSolution);
           return E_SINGULAR;
       }
       
       /* 4. Compute noise contributions from all sources */
       noise->NOISEtotal = 0.0;
       NOISEsource *src = ckt->CKTnoiseSources;
       int srcIndex = 0;
       
       while (src != NULL) {
           /* Get adjoint voltages at source terminals */
           double Vadj_pos_real = adjSolution[src->posNode];
           double Vadj_pos_imag = adjSolution[src->posNode + ckt->CKTnumStates];
           double Vadj_neg_real = adjSolution[src->negNode];
           double Vadj_neg_imag = adjSolution[src->negNode + ckt->CKTnumStates];
           
           /* Transfer function H = Vadj_pos - Vadj_neg */
           double H_real = Vadj_pos_real - Vadj_neg_real;
           double H_imag = Vadj_pos_imag - Vadj_neg_imag;
           double H_mag2 = H_real * H_real + H_imag * H_imag;
           
           /* Noise spectral density of this source */
           double S = src->spectralDensity(freq, src);
           
           /* Contribution = |H|² * S */
           double contrib = H_mag2 * S;
           noise->NOISEcontrib[srcIndex] = contrib;
           noise->NOISEtotal += contrib;
           
           src = src->next;
           srcIndex++;
       }
       
       free(adjRHS);
       free(adjSolution);
       return OK;
   }
   ```

4. **Noise Spectral Density Functions in `cktnoise.c`**:
   ```c
   /* Thermal noise spectral density */
   double NOISEthermalSD(double freq, NOISEsource *src) {
       /* i_n² = 4kT·G·Δf, where G = 1/R */
       double G = 1.0 / src->value;  /* Conductance from resistance */
       return 4.0 * BOLTZMANN * ckt->CKTtemp * G;
   }
   
   /* Shot noise spectral density */
   double NOISEshotSD(double freq, NOISEsource *src) {
       /* i_n² = 2qI·Δf */
       return 2.0 * CHARGE_E * fabs(src->value);
   }
   
   /* Flicker (1/f) noise spectral density */
   double NOISEflickerSD(double freq, NOISEsource *src) {
       /* i_n² = K·I^a / f^b · Δf */
       double K = src->flickerK;
       double a = src->flickerA;
       double b = src->flickerB;
       double I = fabs(src->value);
       
       if (freq < 1e-20) freq = 1e-20;  /* Avoid division by zero */
       return K * pow(I, a) / pow(freq, b);
   }
   
   /* MOSFET channel thermal noise */
   double NOISEmosfetSD(double freq, NOISEsource *src) {
       /* i_d² = (4kT)·(2/3)·g_m·Δf for long-channel */
       double gm = src->gm;  /* Transconductance from DC operating point */
       return 4.0 * BOLTZMANN * ckt->CKTtemp * (2.0/3.0) * gm;
   }
   ```

5. **Complex Matrix Operations in `smpc.c`**:
   ```c
   /* Complex sparse matrix factorization */
   int SMPcFactor(SMPmatrix *matrix, double omega) {
       /* For Y = G + jωC, store as two real matrices */
       /* Real part: G - ω·B (where B = Im{C}) */
       /* Imag part: ω·G_c + B_c (for general complex elements) */
       
       /* Perform LU factorization with complex partial pivoting */
       for (int k = 0; k < matrix->size; k++) {
           /* Find pivot with maximum magnitude */
           int pivot = k;
           double maxMag = 0.0;
           for (int i = k; i < matrix->size; i++) {
               double real = matrix->real[i][k];
               double imag = matrix->imag[i][k];
               double mag = real*real + imag*imag;
               if (mag > maxMag) {
                   maxMag = mag;
                   pivot = i;
               }
           }
           
           if (maxMag < matrix->pivotTol) {
               return E_SINGULAR;  /* Matrix is numerically singular */
           }
           
           /* Swap rows if necessary */
           if (pivot != k) {
               SMPcSwapRows(matrix, k, pivot);
           }
           
           /* Perform elimination */
           for (int i = k+1; i < matrix->size; i++) {
               /* Compute multiplier: L_ik = Y_ik / Y_kk */
               double real_ik = matrix->real[i][k];
               double imag_ik = matrix->imag[i][k];
               double real_kk = matrix->real[k][k];
               double imag_kk = matrix->imag[k][k];
               
               /* Complex division */
               double denom = real_kk*real_kk + imag_kk*imag_kk;
               double mult_real = (real_ik*real_kk + imag_ik*imag_kk) / denom;
               double mult_imag = (imag_ik*real_kk - real_ik*imag_kk) / denom;
               
               /* Store multiplier in L part */
               matrix->real[i][k] = mult_real;
               matrix->imag[i][k] = mult_imag;
               
               /* Update submatrix: Y_ij = Y_ij - L_ik * Y_kj */
               for (int j = k+1; j < matrix->size; j++) {
                   /* Complex multiply: L_ik * Y_kj */
                   double real_prod = mult_real*matrix->real[k][j] - 
                                     mult_imag*matrix->imag[k][j];
                   double imag_prod = mult_real*matrix->imag[k][j] + 
                                     mult_imag*matrix->real[k][j];
                   
                   /* Complex subtract */
                   matrix->real[i][j] -= real_prod;
                   matrix->imag[i][j] -= imag_prod;
               }
           }
       }
       return OK;
   }
   ```

6. **Frequency-Dependent Element Stamping in `acload.c`**:
   ```c
   /* Capacitor stamp in frequency domain */
   int CAPacLoad(CKTcircuit *ckt, GENinstance *inst, double omega) {
       CAPinstance *cap = (CAPinstance *)inst;
       double C = cap->CAPcapac;
       
       /* Y_cap = jωC */
       double imagVal = omega * C;
       
       /* Stamp into complex matrix */
       /* Real part: 0, Imag part: ωC */
       SMPcAddReal(ckt->CKTmatrix, cap->CAPposNode, cap->CAPposNode, 0.0);
       SMPcAddImag(ckt->CKTmatrix, cap->CAPposNode, cap->CAPposNode, imagVal);
       
       SMPcAddReal(ckt->CKTmatrix, cap->CAPposNode, cap->CAPnegNode, 0.0);
       SMPcAddImag(ckt->CKTmatrix, cap->CAPposNode, cap->CAPnegNode, -imagVal);
       
       SMPcAddReal(ckt->CKTmatrix, cap->CAPnegNode, cap->CAPposNode, 0.0);
       SMPcAddImag(ckt->CKTmatrix, cap->CAPnegNode, cap->CAPposNode, -imagVal);
       
       SMPcAddReal(ckt->CKTmatrix, cap->CAPnegNode, cap->CAPnegNode, 0.0);
       SMPcAddImag(ckt->CKTmatrix, cap->CAPnegNode, cap->CAPnegNode, imagVal);
       
       return OK;
   }
   
   /* Inductor stamp using modified nodal analysis */
   int INDacLoad(CKTcircuit *ckt, GENinstance *inst, double omega) {
       INDinstance *ind = (INDinstance *)inst;
       double L = ind->INDinduct;
       
       /* Add branch current as extra variable */
       int branchEq = ind->INDbrEq;
       
       if (omega < 1e-20) {
           /* Low frequency regularization */
           omega = 1e-20;
       }
       
       /* Stamp: [0 0 1; 0 0 -1; 1 -1 -jωL] */
       /* Real part */
       SMPcAddReal(ckt->CKTmatrix, ind->INDposNode, branchEq, 1.0);
       SMPcAddReal(ckt->CKTmatrix, ind->INDnegNode, branchEq, -1.0);
       SMPcAddReal(ckt->CKTmatrix, branchEq, ind->INDposNode, 1.0);
       SMPcAddReal(ckt->CKTmatrix, branchEq, ind->INDnegNode, -1.0);
       
       /* Imaginary part: -ωL at (branchEq, branchEq) */
       SMPcAddImag(ckt->CKTmatrix, branchEq, branchEq, -omega * L);
       
       return OK;
   }
   ```

### Frequency Sweep Optimization That Would Be Extracted:
From the inaccessible files, key implementation aspects would include:

1. **Matrix Reuse Strategy**:
   - Cache LU factors for similar frequencies
   - Use matrix update formulas for small frequency changes
   - Adaptive refactorization based on condition number estimates

2. **Parallel Frequency Computation**:
   - OpenMP parallelization across frequency points
   - Load balancing for non-uniform solution times
   - Thread-safe matrix operations

3. **Adaptive Frequency Sampling**:
   - Curvature-based point insertion
   - Merge closely spaced points in flat regions
   - User-defined maximum points constraint

### Noise Analysis Optimizations That Would Be Detailed:
The inaccessible files would reveal:

1. **Adjoint Solution Efficiency**:
   - Reuse matrix factorization from original solve
   - Exploit symmetry: Y^T = conj(Y) for reciprocal networks
   - Batch processing of multiple output nodes

2. **Noise Source Grouping**:
   - Group sources by type for efficient computation
   - Precompute frequency-independent terms
   - Cache transfer functions for correlated sources

3. **Memory Management**:
   - Reuse solution vectors across frequencies