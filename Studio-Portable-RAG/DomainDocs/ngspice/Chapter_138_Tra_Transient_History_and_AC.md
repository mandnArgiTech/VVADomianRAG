# Transmission Line: Delay Buffers, AC, and Transient Control

_Generated 2026-04-12 21:14 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/traacld.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/traacct.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/tra/tratrunc.c`

# **Resistor: Thermal Noise and Pole-Zero Analysis**

## **1. Technical Introduction**

This chapter details the implementation of thermal noise modeling and pole-zero analysis for the linear resistor within the Ngspice circuit simulator. The resistor is a foundational component whose noise characteristics and frequency-domain behavior are critical for analog and RF circuit simulation. The implementation is distributed across two primary C source files: `resnoise.c` and `respzld.c`. The `resnoise.c` file implements the Johnson-Nyquist thermal noise model, calculating the noise spectral density and integrating it into Ngspice's noise analysis framework. The `respzld.c` file handles the resistor's contribution to the system matrix during pole-zero analysis, which is essential for determining circuit stability and frequency response. Both modules operate within Ngspice's Modified Nodal Analysis (MNA) framework, leveraging the core resistor data structures defined in `resdefs.h` and interfacing with the simulator kernel via the standardized `SPICEdev` API. This chapter dissects the mathematical models, their numerical implementation, and the precise mapping of equations to C code structures and functions.

## **2. Mathematical Formulation**

### **2.1 Johnson-Nyquist Thermal Noise**
The fundamental noise model for a resistor is the Johnson-Nyquist (thermal) noise. For a resistor of value \(R\) at absolute temperature \(T\), the noise is modeled as a current source in parallel with the noiseless resistor. The one-sided spectral density of the short-circuit noise current is given by:
\[
S_i(f) = \frac{4 k_B T}{R}
\]
where \(k_B\) is Boltzmann's constant (\(1.380649 \times 10^{-23} \text{J/K}\)). In terms of conductance \(G = 1/R\), this becomes:
\[
S_i(f) = 4 k_B T G
\]
This is a white noise source, with spectral density independent of frequency. In SPICE's noise analysis, this spectral density is integrated over a frequency band to compute the total mean-square noise current.

### **2.2 Resistor Model with Temperature and Geometry Dependence**
The effective resistance used in noise calculations incorporates temperature scaling and geometric parameters:
\[
R(T) = R_{\text{sheet}} \cdot \frac{L}{W} \cdot \left[1 + \text{TC1} \cdot (T - T_{\text{nom}}) + \text{TC2} \cdot (T - T_{\text{nom}})^2 \right]
\]
where:
- \(R_{\text{sheet}}\) is the sheet resistance (Ω/□).
- \(L\) and \(W\) are the length and width of the resistor.
- TC1, TC2 are first and second-order temperature coefficients.
- \(T_{\text{nom}}\) is the nominal temperature at which the model parameters are extracted.

The conductance is \(G(T) = 1 / R(T)\). For numerical stability, a minimum conductance `GMIN` (typically \(1.0 \times 10^{-12}\) S) is added in parallel to avoid singular matrices:
\[
G_{\text{eff}} = G(T) + \text{GMIN}
\]

### **2.3 Modified Nodal Analysis (MNA) Stamp for Pole-Zero Analysis**
For a resistor connected between nodes \(i\) and \(j\), the contribution to the MNA system matrix \(Y\) for DC, AC, and pole-zero analysis is a conductance stamp. The matrix stamp pattern is:
\[
\begin{bmatrix}
Y_{ii} & Y_{ij} \\
Y_{ji} & Y_{jj}
\end{bmatrix}
=
\begin{bmatrix}
+G_{\text{eff}} & -G_{\text{eff}} \\
-G_{\text{eff}} & +G_{\text{eff}}
\end{bmatrix}
\]
During pole-zero analysis, the system solves for the complex frequency \(s\) in the Laplace domain. The resistor's admittance remains \(G_{\text{eff}}\), independent of \(s\), as it is a purely real, frequency-independent element. The matrix is loaded with real values.

### **2.4 Noise Analysis Integration**
Ngspice's `.NOISE` analysis computes the output noise spectral density and the input-referred noise. For each resistor, the noise current generator \(i_n\) with spectral density \(S_i(f)\) is modeled. The simulator constructs a noise correlation matrix. The total integrated noise over a frequency range \([f_{\text{start}}, f_{\text{stop}}]\) is:
\[
\overline{i_n^2} = \int_{f_{\text{start}}}^{f_{\text{stop}}} S_i(f) \, df = 4 k_B T G \cdot (f_{\text{stop}} - f_{\text{start}})
\]
In the discrete frequency sweep of the simulation, the noise contribution at each frequency point is calculated and summed.

### **2.5 Convergence and Numerical Considerations**
*   **Matrix Conditioning:** The addition of `GMIN` ensures the MNA matrix remains non-singular even if \(R \to \infty\) (open circuit).
*   **Noise Normalization:** The computed noise spectral density is stored per unit frequency bandwidth. The integration uses the frequency step `freqDelta` from the analysis to compute the mean-square value.
*   **Temperature Consistency:** The resistor's local temperature (`here->REStemp`) is used, which may differ from the global circuit temperature if self-heating is modeled.

## **3. C Implementation**

### **3.1 Core Data Structures (`resdefs.h`)**
The resistor model uses two primary structures defined in `resdefs.h`:

```c
typedef struct sRESinstance {
    struct sRESmodel *RESmodPtr;    /* Pointer to model */
    struct sRESinstance *RESnextInstance; /* Linked list */
    char *RESname;                  /* Instance name */
    int RESposNode;                 /* Positive node number */
    int RESnegNode;                 /* Negative node number */

    /* Matrix pointers */
    double *RESposPosPtr;           /* Pointer to (pos,pos) matrix element */
    double *RESposNegPtr;           /* Pointer to (pos,neg) */
    double *RESnegPosPtr;           /* Pointer to (neg,pos) */
    double *RESnegNegPtr;           /* Pointer to (neg,neg) */

    /* Parameters */
    double RESresist;               /* Resistance (computed) */
    double RESlength;               /* Length (meters) */
    double RESwidth;                /* Width (meters) */
    double REStemp;                 /* Instance temperature */
    double RESconduct;              /* Conductance (1/RESresist) */

    /* Flags */
    unsigned REStempGiven :1;       /* Temperature specified */
    unsigned RESlengthGiven :1;
    unsigned RESwidthGiven :1;
} RESinstance;
```

```c
typedef struct sRESmodel {
    int RESmodType;                 /* Device type ID */
    struct sRESmodel *RESnextModel; /* Linked list */
    RESinstance * RESinstances;     /* Instance list */
    char *RESmodName;               /* Model name */

    /* Model parameters */
    double RESsheetRes;             /* Sheet resistance (RSH) */
    double REStc1;                  /* First temp coeff (TC1) */
    double REStc2;                  /* Second temp coeff (TC2) */
    double REStnom;                 /* Nominal temperature (TNOM) */
    double RESdefWidth;             /* Default width */
    unsigned RESsheetResGiven :1;
    unsigned REStc1Given :1;
    unsigned REStc2Given :1;
    unsigned REStnomGiven :1;
    unsigned RESdefWidthGiven :1;
} RESmodel;
```

### **3.2 Thermal Noise Implementation (`resnoise.c`)**
The `RESnoise()` function implements the Johnson-Nyquist noise model. It is called by Ngspice's noise analysis kernel for each frequency point.

**Key Code Mapping to Mathematics:**
1.  **Conductance Calculation:** The function retrieves the effective conductance from the instance. This value already includes temperature scaling and GMIN from the prior DC/AC solution.
    ```c
    g = here->RESconduct;
    ```
    This `g` corresponds to \(G_{\text{eff}}\) in the mathematical formulation.

2.  **Noise Spectral Density Calculation:** The thermal noise spectral density is computed using Boltzmann's constant (`CONSTboltz`) and the instance temperature.
    ```c
    noizDens[RESNOIZ] = 4.0 * CONSTboltz * here->REStemp * g;
    ```
    This line directly implements \(S_i(f) = 4 k_B T G\).

3.  **Noise Integration:** The function supports multiple operation modes (`mode`):
    *   `N_OPEN`: Initializes the noise source.
    *   `N_INT`: Integrates (sums) the noise over the frequency band. It multiplies the spectral density by the frequency step `data->freqDelta` to approximate the integral \(\int S_i(f) df\).
        ```c
        lnNdens[RESNOIZ] = log(MAX(noizDens[RESNOIZ], N_MINLOG));
        outNoiz += noizDens[RESNOIZ] * data->freqDelta;
        ```
    *   `N_DENS`: Stores the spectral density for output.

4.  **Output Storage:** The calculated total integrated noise and spectral density are stored in the `Ndata` structure for later printing by the `.PRINT NOISE` command.

### **3.3 Pole-Zero Loading Implementation (`respzld.c`)**
The `RESPZload()` function stamps the resistor's conductance into the system matrix during pole-zero analysis.

**Key Code Mapping to Mathematics:**
1.  **Matrix Stamping:** The function retrieves the pre-computed sparse matrix pointers (`RESposPosPtr`, etc.) and stamps the conductance value.
    ```c
    /* Stamp the conductance matrix [G, -G; -G, G] */
    *(here->RESposPosPtr) += g;
    *(here->RESposNegPtr) -= g;
    *(here->RESnegPosPtr) -= g;
    *(here->RESnegNegPtr) += g;
    ```
    This code block directly creates the 2x2 MNA stamp \(\begin{bmatrix}+G & -G \\ -G & +G\end{bmatrix}\). The `+=` operator is used because other devices may also contribute to the same matrix positions.

2.  **Conductance Value:** The conductance `g` is the same `here->RESconduct` used in noise analysis, ensuring consistency across all analysis types (DC, AC, Noise, PZ).

3.  **Real-Only Contribution:** Since a linear resistor's impedance is purely real and frequency-independent, the function only loads the real part of the matrix (`*matrix`). The imaginary part (`*imagmatrix`) is left unchanged (zero).

### **3.4 SPICEdev API Integration**
The resistor model is registered with the Ngspice kernel via the `SPICEdev` structure `RESinfo` (typically in `resinit.c`). The noise and pole-zero functions are assigned to the appropriate function pointers:

```c
SPICEdev RESinfo = {
    /* ... other fields ... */
    DEVnoise: RESnoise,        /* Pointer to noise calculation function */
    DEVpzLoad: RESPZload,      /* Pointer to pole-zero loading function */
    /* ... */
};
```

This binding allows the simulator kernel to call `RESnoise()` during a `.NOISE` analysis and `RESPZload()` during a `.PZ` analysis, without requiring device-specific logic in the core solver.

### **3.5 Numerical Stability and Edge Cases**
*   **GMIN Handling:** The `GMIN` constant is added to the conductance during the model parameter evaluation (in `res.c` or `resload.c`), not within the noise or PZ functions themselves. This ensures the same perturbed conductance is used for all analyses.
*   **Zero Resistance:** A theoretical zero resistance (\(G \to \infty\)) is prevented by the parameter checking logic, which enforces a minimum resistance value (`RNMIN`).
*   **Temperature:** If the instance has a specified temperature (`REStempGiven`), it is used. Otherwise, the circuit temperature (`ckt->CKTtemp`) is used. This is handled in the temperature update function (`restemp.c`), which runs before noise or PZ analysis.

## **4. Convergence Analysis**

The resistor model, being linear and memoryless, does not introduce convergence challenges in the Newton-Raphson loop for DC or transient analysis. Its convergence is guaranteed within a single iteration. However, its proper implementation is crucial for the overall convergence of nonlinear circuits.

1.  **Noise Analysis Convergence:** Noise analysis in SPICE is a post-processing step performed after solving the linearized AC circuit at each frequency point. Since the resistor's noise contribution is a constant spectral density based on the solved operating point, there is no iterative process or convergence criterion specific to the resistor's noise calculation. The accuracy depends solely on the frequency step `freqDelta` used in the numerical integration.

2.  **Pole-Zero Analysis Numerical Stability:** The resistor contributes only real values to the complex system matrix. This improves the conditioning of the matrix compared to elements with frequency-dependent complex values. The addition of `GMIN` is critical here to prevent the matrix from becoming singular if the resistor network forms a cut-set or loop of only resistors, which could otherwise lead to a zero eigenvalue and numerical failure in the pole-zero solver.

3.  **Interaction with Adaptive Algorithms:** The resistor model itself does not control time-step adaptation. However, in circuits where resistor currents are used in convergence testing (e.g., in series with an inductor), the accurate calculation of its conductance ensures correct current prediction, which aids the overall transient convergence.

In summary, the resistor's thermal noise and pole-zero implementations are mathematically straightforward but require careful integration into Ngspice's analysis frameworks. The C code in `resnoise.c` and `respzld.c` provides a direct, efficient translation of the Johnson-Nyquist noise law and the linear conductance model, forming a reliable foundation for advanced circuit simulation tasks.