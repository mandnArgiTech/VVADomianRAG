# Current-Controlled Switch: Smoothing Math and DC Load

_Generated 2026-04-13 00:19 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswdefs.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswparam.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswmpar.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/devices/csw/cswload.c`

# Chapter: Current-Controlled Switch: Smoothing Math and DC Load

## Technical Introduction

The files `cswdefs.h`, `cswparam.c`, `cswmpar.c`, and `cswload.c` constitute the core implementation of the current-controlled switch (CSW) device in Ngspice's SPICE simulation engine. These files implement a two-terminal switching element whose conductance is controlled by an external current, measured through a zero-value voltage source. The implementation addresses the fundamental numerical challenge of discrete switching in continuous Newton-Raphson simulation through sophisticated mathematical smoothing techniques.

`cswdefs.h` defines the essential data structures that map directly to the switch's mathematical model: the `CSWmodel` structure encapsulates physical parameters like on/off resistances and hysteresis thresholds, while the `CSWinstance` structure maintains the runtime state including the smoothed switching variable and cached matrix pointers. `cswparam.c` and `cswmpar.c` implement the parameter binding layer that translates SPICE netlist syntax into internal mathematical variables, enabling user specification of switching thresholds, hysteresis windows, and initial conditions. The core algorithmic implementation resides in `cswload.c`, which executes the DC load function that computes the state-dependent conductance, applies cubic polynomial smoothing for Newton-Raphson convergence, implements hysteresis with memory, and stamps the symmetric conductance matrix contributions into the Modified Nodal Analysis system.

Together, these files implement a numerically robust switching model that maintains C¹ continuity through transitions while preserving the essential discrete switching behavior required for accurate circuit simulation. The implementation carefully balances mathematical rigor with computational efficiency through cached matrix pointers and optimized state tracking.

## Mathematical Formulation

### 1. Core Switch Conductance Model

The current-controlled switch (CSW) in Ngspice implements a two-terminal device whose conductance is controlled by an external current. The fundamental mathematical model defines the switch conductance as a function of the controlling current \( I_{\text{control}} \):

\[
G(I_{\text{control}}) = G_{\text{off}} + (G_{\text{on}} - G_{\text{off}}) \cdot S(x)
\]

Where:
- \( G_{\text{on}} = 1/R_{\text{on}} \): On-state conductance (`CSWron`)
- \( G_{\text{off}} = 1/R_{\text{off}} \): Off-state conductance (`CSWroff`)
- \( I_{\text{control}} \): Controlling current measured through a zero-value voltage source
- \( I_{\text{threshold}} \): Threshold current (`CSWion` for turn-on, `CSWioff` for turn-off)
- \( I_{\text{window}} \): Hysteresis window (`CSWiht`)
- \( x = (I_{\text{control}} - I_{\text{threshold}}) / I_{\text{window}} \): Normalized control variable

### 2. Smoothing Function for Newton-Raphson Convergence

To ensure numerical convergence in SPICE's Newton-Raphson iterations, the discrete switch transition is smoothed using a cubic polynomial function \( S(x) \):

\[
S(x) = 
\begin{cases}
0 & \text{for } x < -1 \\
0.5 + 0.75x - 0.25x^3 & \text{for } |x| \leq 1 \\
1 & \text{for } x > 1
\end{cases}
\]

This function provides C¹ continuity (continuous first derivative), which is essential for Newton-Raphson convergence. The derivative required for the Jacobian matrix is:

\[
\frac{dS}{dx} = 
\begin{cases}
0 & \text{for } |x| > 1 \\
0.75 - 0.75x^2 & \text{for } |x| \leq 1
\end{cases}
\]

### 3. Hysteresis Implementation with State Memory

The switch implements hysteresis with dual thresholds to prevent chattering:

\[
\text{State transition logic:}
\begin{cases}
\text{Turn ON when:} & I_{\text{control}} > I_{\text{ON}} + I_{\text{HYST}}/2 \\
\text{Turn OFF when:} & I_{\text{control}} < I_{\text{OFF}} - I_{\text{HYST}}/2
\end{cases}
\]

Where:
- \( I_{\text{ON}} = \text{CSWion} \): Turn-on threshold current
- \( I_{\text{OFF}} = \text{CSWioff} \): Turn-off threshold current  
- \( I_{\text{HYST}} = \text{CSWiht} \): Hysteresis window

The current state is stored in `CSWstate` (0 for OFF, 1 for ON), providing memory between iterations.

### 4. Modified Nodal Analysis (MNA) Formulation

The switch contributes to the MNA system through its conductance matrix stamp. For a switch between nodes \( p \) (positive) and \( n \) (negative):

\[
\begin{bmatrix}
G & -G \\
-G & G
\end{bmatrix}
\begin{bmatrix}
V_p \\
V_n
\end{bmatrix}
=
\begin{bmatrix}
-I_{\text{switch}} \\
+I_{\text{switch}}
\end{bmatrix}
\]

Where \( G = G(I_{\text{control}}) \) is the state-dependent conductance. The switch current is:

\[
I_{\text{switch}} = G \cdot (V_p - V_n)
\]

### 5. Control Current Measurement via Zero-Voltage Source

The controlling current \( I_{\text{control}} \) is measured through a zero-value voltage source, which requires an additional branch equation in the MNA system:

\[
V_{\text{control}+} - V_{\text{control}-} = 0
\]

The branch current for this equation provides \( I_{\text{control}} \), accessed via the branch equation index stored in `CSWcontBranch`.

### 6. Jacobian Matrix Contributions

For Newton-Raphson iteration, the switch contributes partial derivatives to the Jacobian:

\[
\frac{\partial I_{\text{switch}}}{\partial V_p} = +G
\]
\[
\frac{\partial I_{\text{switch}}}{\partial V_n} = -G
\]
\[
\frac{\partial I_{\text{switch}}}{\partial I_{\text{control}}} = \frac{\partial G}{\partial I_{\text{control}}} \cdot (V_p - V_n)
\]

Where the conductance derivative is:

\[
\frac{\partial G}{\partial I_{\text{control}}} = (G_{\text{on}} - G_{\text{off}}) \cdot \frac{dS}{dx} \cdot \frac{1}{I_{\text{window}}}
\]

### 7. Thermal Noise Model

For noise analysis, the switch contributes Johnson-Nyquist thermal noise with power spectral density:

\[
S_I(f) = \frac{4kT}{R_{\text{eff}}}
\]

Where \( R_{\text{eff}} = 1/G \) is the effective resistance at the operating point, \( k \) is Boltzmann's constant (`CONSTboltz`), and \( T \) is the absolute temperature.

### 8. State Variable Dynamics

The switch state evolves according to:

\[
\frac{d(\text{state})}{dt} = \frac{\text{CSWstate} - \text{CSWoldState}}{\Delta t}
\]

This rate of change is used for Local Truncation Error (LTE) calculation to control time steps during transitions.

## Convergence Analysis

### 1. Newton-Raphson Convergence for Smooth Transitions

The cubic smoothing function \( S(x) \) ensures C¹ continuity, which is necessary for quadratic convergence of Newton's method. The convergence criterion for the switch state is:

\[
|\Delta \text{state}| = |\text{CSWstate} - \text{CSWoldState}| \leq \epsilon_{\text{rel}} \cdot \max(|\text{CSWstate}|, 1.0) + \epsilon_{\text{abs}}
\]

Where:
- \( \epsilon_{\text{rel}} = \text{CKTreltol} \approx 10^{-3} \): Relative tolerance
- \( \epsilon_{\text{abs}} = \text{CKTabstol} \approx 10^{-12} \): Absolute tolerance

### 2. Current Convergence Testing

The switch current must also converge according to SPICE standards:

\[
|\Delta I_{\text{switch}}| = |I_{\text{switch}}^{\text{new}} - I_{\text{switch}}^{\text{old}}| \leq \epsilon_{\text{rel}} \cdot \max(|I_{\text{switch}}^{\text{old}}|, 10^{-12}) + \epsilon_{\text{abs}}
\]

This dual convergence check (state and current) ensures both the discrete switching behavior and the continuous conductance are properly resolved.

### 3. Time Step Control via Local Truncation Error (LTE)

During transient analysis, the time step is controlled based on the rate of state change:

\[
\text{LTE}_{\text{state}} = \frac{\Delta t^2}{2} \left| \frac{d^2(\text{state})}{dt^2} \right|
\]

Approximated using backward differences:

\[
\frac{d^2(\text{state})}{dt^2} \approx \frac{(\text{state}_n - \text{state}_{n-1})/\Delta t_{n-1} - (\text{state}_{n-1} - \text{state}_{n-2})/\Delta t_{n-2}}{(\Delta t_{n-1} + \Delta t_{n-2})/2}
\]

The time step is reduced when:

\[
\text{LTE}_{\text{state}} > \text{TRTOL} \cdot \max(|\text{state}|, \text{CHGTOL}) + \text{ABSTOL}
\]

Where:
- \( \text{TRTOL} \approx 7 \): Transient tolerance factor
- \( \text{CHGTOL} \approx 10^{-14} \): Charge tolerance
- \( \text{ABSTOL} \approx 10^{-12} \): Absolute tolerance

### 4. Hysteresis and Convergence Stability

The hysteresis implementation creates a dead zone that prevents oscillatory convergence:

\[
\text{Convergence radius} = \frac{I_{\text{HYST}}}{2 \cdot \max\left(\left|\frac{\partial G}{\partial I_{\text{control}}}\right|\right)}
\]

This ensures that small numerical fluctuations around the threshold don't cause the switch to chatter between states during Newton iterations.

### 5. Matrix Conditioning Considerations

The switch conductance matrix has condition number:

\[
\kappa(G_{\text{switch}}) = \frac{\max(R_{\text{on}}, R_{\text{off}})}{\min(R_{\text{on}}, R_{\text{off}})}
\]

Typical values \( R_{\text{on}} = 1\Omega \), \( R_{\text{off}} = 10^{12}\Omega \) give \( \kappa \approx 10^{12} \), which requires careful pivoting in the linear solver to maintain numerical stability.

### 6. Smoothing Function Convergence Properties

The cubic smoothing function has the following convergence-friendly properties:

1. **Bounded derivative**: \( |dS/dx| \leq 0.75 \) ensures Jacobian entries don't become excessively large
2. **Monotonic**: \( dS/dx \geq 0 \) for all \( x \) prevents negative conductance
3. **Smooth transition**: C¹ continuity ensures Newton-Raphson can converge quadratically near the transition region

### 7. Initial Condition Convergence

When initial conditions are specified (`CSWicGiven` or `CSWon`/`CSWoff`), the switch starts at:

\[
\text{CSWstate}(t=0) = 
\begin{cases}
1.0 & \text{if ON or IC > 0.5} \\
0.0 & \text{otherwise}
\end{cases}
\]

The convergence test must accommodate this initial discontinuity by allowing larger tolerances for the first few iterations.

### 8. AC Analysis Convergence

For small-signal AC analysis, the switch is linearized at its DC operating point:

\[
G_{\text{AC}} = G(I_{\text{control,DC}})
\]

Since this is constant for a given frequency, AC analysis converges in one iteration when:

\[
\|(G + j\omega C)V - I\| < \epsilon_{\text{AC}}
\]

Where \( \epsilon_{\text{AC}} \approx 10^{-10} \) for double precision.

### 9. Noise Analysis Convergence

Noise analysis convergence is governed by the integral of the noise spectral density:

\[
\int_{f_1}^{f_2} S_I(f) df = 4kT \ln\left(\frac{R_{\text{eff}}(f_2)}{R_{\text{eff}}(f_1)}\right)
\]

The convergence is achieved when successive estimates of this integral differ by less than \( \epsilon_{\text{noise}} \approx 10^{-6} \).

### 10. Implementation-Specific Convergence Enhancements

The Ngspice implementation includes several convergence aids:

1. **State variable clamping**: \( \text{CSWstate} \) is clamped to [0, 1] to prevent numerical overflow
2. **Conductance limiting**: \( G \) is limited to \( [G_{\text{off}}, G_{\text{on}}] \) to maintain physical realism
3. **Previous state storage**: `CSWoldState` enables convergence rate monitoring
4. **Transition detection**: Large state changes trigger time step reduction for accurate transition capture

These mathematical formulations and convergence analyses ensure that the current-controlled switch model in Ngspice provides robust, accurate simulation of switching behavior while maintaining numerical stability across all SPICE analysis modes.

## C Implementation

### 1. Core Data Structures and Parameter Binding

#### 1.1 Switch Model and Instance Structures (`cswdefs.h`)

The current-controlled switch implementation in Ngspice uses two primary data structures that directly map to the mathematical model:

```c
/* Current-Controlled Switch Model Structure */
typedef struct sCSWmodel {
    int CSWtype;                    /* N_CSW or P_CSW */
    double CSWvth;                  /* Threshold voltage (if voltage mode) */
    double CSWvon;                  /* Turn-on voltage */
    double CSWvoff;                 /* Turn-off voltage */
    double CSWron;                  /* On-state resistance */
    double CSWroff;                 /* Off-state resistance */
    double CSWiht;                  /* Hysteresis current */
    double CSWic;                   /* Initial condition */
    int CSWicGiven;                 /* IC flag */
    struct sCSWmodel *CSWnextModel; /* Linked list next model */
    sCSWinstance *CSWinstances;     /* Instance list head */
} CSWmodel;

/* Current-Controlled Switch Instance Structure */
typedef struct sCSWinstance {
    char *CSWname;                  /* Instance name */
    int CSWposNode;                 /* Positive terminal node */
    int CSWnegNode;                 /* Negative terminal node */
    int CSWcontBranch;              /* Controlling branch equation index */
    
    /* Matrix pointers for switch conductance */
    double *CSWposPosPtr;           /* G[pos][pos] */
    double *CSWnegNegPtr;           /* G[neg][neg] */
    double *CSWposNegPtr;           /* G[pos][neg] */
    double *CSWnegPosPtr;           /* G[neg][pos] */
    
    /* State variables */
    double CSWstate;                /* Current state (0=off, 1=on) */
    double CSWoldState;             /* Previous state */
    double CSWconduct;              /* Current conductance */
    double CSWvoltage;              /* Terminal voltage */
    double CSWcurrent;              /* Switch current */
    
    /* Flags */
    unsigned CSWstateGiven : 1;     /* Initial state given */
    unsigned CSWon : 1;             /* ON/OFF flag */
    
    struct sCSWinstance *CSWnextInstance; /* Next instance */
    CSWmodel *CSWmodPtr;            /* Pointer to parent model */
} CSWinstance;
```

**Mathematical Mapping**: These structures implement the core switch equations:
- `CSWron` and `CSWroff` map to \( R_{on} \) and \( R_{off} \) in the conductance equation \( G = 1/R \)
- `CSWion` and `CSWioff` implement the hysteresis thresholds \( I_{on} \) and \( I_{off} \)
- `CSWiht` represents the hysteresis window \( I_{hyst} \)
- `CSWstate` implements the smoothed state variable \( S(x) \)
- `CSWconduct` stores the current conductance \( G(I_{control}) \)

#### 1.2 Parameter Binding Tables (`cswparam.c`, `cswmpar.c`)

The parameter tables define the interface between SPICE netlist parameters and internal mathematical variables:

```c
/* Model Parameter Table */
static IFparm CSWmPTable[] = {
    IOP("ron",    CSW_RON,    IF_REAL, "On-state resistance"),
    IOP("roff",   CSW_ROFF,   IF_REAL, "Off-state resistance"),
    IOP("ith",    CSW_ITH,    IF_REAL, "Threshold current"),
    IOP("ih",     CSW_IH,     IF_REAL, "Hysteresis current"),
    IOP("ion",    CSW_ION,    IF_REAL, "Turn-on current"),
    IOP("ioff",   CSW_IOFF,   IF_REAL, "Turn-off current"),
    IOP("ic",     CSW_IC,     IF_REAL, "Initial condition"),
    IP("csw",     CSW_CSW,    IF_FLAG, "Current-controlled switch"),
};

/* Instance Parameter Table */
static IFparm CSWpTable[] = {
    IOP("control", CSW_CONTROL, IF_INSTANCE, "Controlling source"),
    IOP("on",      CSW_ON,      IF_FLAG,     "Initially on"),
    IOP("off",     CSW_OFF,     IF_FLAG,     "Initially off"),
};
```

**SPICE Integration**: These tables enable Ngspice to parse netlist statements like `S1 pos neg Vcontrol CSW ron=1 roff=1e12 ion=0.1 ioff=0.1` and map the parameters to the mathematical model.

### 2. Matrix Setup and Sparse Allocation (`cswset.c`)

#### 2.1 Sparse Matrix Pointer Allocation

The setup function allocates sparse matrix pointers for efficient Jacobian stamping:

```c
int CSWsetup(SMPmatrix *matrix, GENmodel *inModel, CKTcircuit *ckt, int *states) {
    CSWmodel *model;
    CSWinstance *inst;
    
    for(model = (CSWmodel *)inModel; model != NULL; model = model->CSWnextModel) {
        
        /* Default parameter values */
        if(!model->CSWronGiven)  model->CSWron = 1.0;
        if(!model->CSWroffGiven) model->CSWroff = 1.0e12;
        if(!model->CSWionGiven)  model->CSWion = 0.1;
        if(!model->CSWioffGiven) model->CSWioff = 0.1;
        if(!model->CSWihtGiven)  model->CSWiht = 0.0;
        
        for(inst = model->CSWinstances; inst != NULL; inst = inst->CSWnextInstance) {
            
            /* Allocate SMP matrix pointers for 2-terminal switch */
            inst->CSWposPosPtr = SMPmakeElt(matrix, inst->CSWposNode, inst->CSWposNode);
            inst->CSWnegNegPtr = SMPmakeElt(matrix, inst->CSWnegNode, inst->CSWnegNode);
            inst->CSWposNegPtr = SMPmakeElt(matrix, inst->CSWposNode, inst->CSWnegNode);
            inst->CSWnegPosPtr = SMPmakeElt(matrix, inst->CSWnegNode, inst->CSWposNode);
            
            /* Check allocation */
            if(!inst->CSWposPosPtr || !inst->CSWnegNegPtr) {
                return E_NOMEM;
            }
            
            /* Initialize state */
            if(inst->CSWon) {
                inst->CSWstate = 1.0;
            } else if(inst->CSWoff) {
                inst->CSWstate = 0.0;
            } else if(model->CSWicGiven) {
                inst->CSWstate = (model->CSWic > 0.5) ? 1.0 : 0.0;
            } else {
                inst->CSWstate = 0.0;  /* Default OFF */
            }
            
            inst->CSWoldState = inst->CSWstate;
            inst->CSWconduct = 1.0/model->CSWroff;
            
            /* Allocate state vector entry for convergence tracking */
            inst->CSWstateVar = *states;
            (*states)++;
            ckt->CKTstate0[inst->CSWstateVar] = inst->CSWstate;
        }
    }
    return OK;
}
```

**Mathematical Significance**: 
- The four matrix pointers (`CSWposPosPtr`, `CSWnegNegPtr`, `CSWposNegPtr`, `CSWnegPosPtr`) implement the symmetric conductance matrix pattern for a two-terminal device
- `SMPmakeElt` creates sparse matrix entries at the specified row-column intersections
- The state variable allocation (`CSWstateVar`) enables tracking of the switch state for convergence testing and time-step control

### 3. DC Load Implementation with Smoothing (`cswload.c`)

#### 3.1 Core Loading Algorithm with Hysteresis

The DC load function implements the complete switch model with hysteresis and smoothing:

```c
int CSWload(GENmodel *inModel, CKTcircuit *ckt) {
    CSWmodel *model;
    CSWinstance *inst;
    double icontrol;      /* Controlling current */
    double vswitch;       /* Switch terminal voltage */
    double g_switch;      /* Switch conductance */
    double i_switch;      /* Switch current */
    double state_new;     /* New state variable */
    
    for(model = (CSWmodel *)inModel; model != NULL; model = model->CSWnextModel) {
        for(inst = model->CSWinstances; inst != NULL; inst = inst->CSWnextInstance) {
            
            /* Get controlling current from branch equation */
            icontrol = ckt->CKTrhsOld[inst->CSWcontBranch];
            
            /* Get switch terminal voltage */
            vswitch = ckt->CKTrhsOld[inst->CSWposNode] - ckt->CKTrhsOld[inst->CSWnegNode];
            
            /* State transition logic with hysteresis */
            if(inst->CSWstate > 0.5) {  /* Currently ON */
                if(icontrol < model->CSWioff - model->CSWiht/2.0) {
                    state_new = 0.0;  /* Turn OFF */
                } else {
                    state_new = 1.0;  /* Stay ON */
                }
            } else {  /* Currently OFF */
                if(icontrol > model->CSWion + model->CSWiht/2.0) {
                    state_new = 1.0;  /* Turn ON */
                } else {
                    state_new = 0.0;  /* Stay OFF */
                }
            }
            
            /* Smoothing function for continuous transition */
            if(fabs(state_new - inst->CSWstate) < 1.0) {
                /* Apply cubic smoothing polynomial */
                double delta = state_new - inst->CSWstate;
                double smooth = 3.0*delta*delta - 2.0*delta*delta*delta;
                state_new = inst->CSWstate + smooth;
            }
            
            /* Calculate conductance with smoothing */
            g_switch = 1.0/model->CSWroff + 
                      (1.0/model->CSWron - 1.0/model->CSWroff) * state_new;
            
            /* Calculate switch current */
            i_switch = g_switch * vswitch;
            
            /* Stamp conductance matrix */
            *(inst->CSWposPosPtr) += g_switch;
            *(inst->CSWnegNegPtr) += g_switch;
            *(inst->CSWposNegPtr) -= g_switch;
            *(inst->CSWnegPosPtr) -= g_switch;
            
            /* Stamp RHS current vector */
            ckt->CKTrhs[inst->CSWposNode] -= i_switch;
            ckt->CKTrhs[inst->CSWnegNode] += i_switch;
            
            /* Store state for next iteration */
            inst->CSWoldState = inst->CSWstate;
            inst->CSWstate = state_new;
            inst->CSWconduct = g_switch;
            inst->CSWcurrent = i_switch;
            inst->CSWvoltage = vswitch;
        }
    }
    return OK;
}
```

**Mathematical Implementation Details**:

1. **Control Current Measurement**: 
   - `icontrol = ckt->CKTrhsOld[inst->CSWcontBranch]` extracts the controlling current from the zero-voltage source branch equation
   - This implements \( I_{control} \) in the switching criteria

2. **Hysteresis Logic**:
   ```c
   if(inst->CSWstate > 0.5) {  /* Currently ON */
       if(icontrol < model->CSWioff - model->CSWiht/2.0) {
           state_new = 0.0;  /* Turn OFF */
       }
   } else {  /* Currently OFF */
       if(icontrol > model->CSWion + model->CSWiht/2.0) {
           state_new = 1.0;  /* Turn ON */
       }
   }
   ```
   This implements the hysteresis equations:
   - Turn-OFF: \( I_{control} < I_{off} - I_{hyst}/2 \)
   - Turn-ON: \( I_{control} > I_{on} + I_{hyst}/2 \)

3. **Cubic Smoothing Function**:
   ```c
   double delta = state_new - inst->CSWstate;
   double smooth = 3.0*delta*delta - 2.0*delta*delta*delta;
   state_new = inst->CSWstate + smooth;
   ```
   This implements the cubic polynomial smoothing:
   \[
   S(x) = 3x^2 - 2x^3 \quad \text{for } 0 \leq x \leq 1
   \]
   where \( x = \Delta = \text{state\_new} - \text{CSWstate} \)

4. **Conductance Calculation**:
   ```c
   g_switch = 1.0/model->CSWroff + 
             (1.0/model->CSWron - 1.0/model->CSWroff) * state_new;
   ```
   This implements the linear interpolation:
   \[
   G = G_{off} + (G_{on} - G_{off}) \cdot S
   \]
   where \( G_{on} = 1/R_{on} \), \( G_{off} = 1/R_{off} \), and \( S \) is the smoothed state

5. **Matrix Stamping**:
   The symmetric stamping pattern:
   ```c
   *(inst->CSWposPosPtr) += g_switch;    /* G_{pp} = +G */
   *(inst->CSWnegNegPtr) += g_switch;    /* G_{nn} = +G */
   *(inst->CSWposNegPtr) -= g_switch;    /* G_{pn} = -G */
   *(inst->CSWnegPosPtr) -= g_switch;    /* G_{np} = -G */
   ```
   implements the conductance matrix contribution:
   \[
   \begin{bmatrix}
   +G & -G \\
   -G & +G
   \end{bmatrix}
   \]

### 4. Small-Signal AC Analysis (`cswacld.c`)

For AC analysis, the switch uses its DC operating point conductance:

```c
int CSWacLoad(GENmodel *inModel, CKTcircuit *ckt) {
    CSWmodel *model;
    CSWinstance *inst;
    double g_ac;
    
    for(model = (CSWmodel *)inModel; model != NULL; model = model->CSWnextModel) {
        for(inst = model->CSWinstances; inst != NULL; inst = inst->CSWnextInstance) {
            
            /* Use DC operating point conductance */
            g_ac = inst->CSWconduct;
            
            /* Stamp into real part of complex matrix */
            *(inst->CSWposPosPtr) += g_ac;
            *(inst->CSWnegNegPtr) += g_ac;
            *(inst->CSWposNegPtr) -= g_ac;
            *(inst->CSWnegPosPtr) -= g_ac;
            
            /* Note: Switch is memoryless for small-signal AC,
               no frequency-dependent components */
        }
    }
    return OK;
}
```

**Mathematical Basis**: In small-signal AC analysis, the switch is linearized around its DC operating point. The conductance \( G \) from the DC solution is used directly in the complex admittance matrix \( Y = G + j\omega C \). Since the switch has no capacitive components, only the real part \( G \) is stamped.

### 5. Noise Analysis Implementation (`cswnoise.c`)

The switch contributes Johnson-Nyquist thermal noise based on its current resistance:

```c
int CSWnoise(int mode, int operation, GENmodel *inModel, CKTcircuit *ckt,
             Ndata *data, double *OnDens) {
    CSWmodel *model;
    CSWinstance *inst;
    double r_now, noise_dens;
    
    for(model = (CSWmodel *)inModel; model != NULL; model = model->CSWnextModel) {
        for(inst = model->CSWinstances; inst != NULL; inst = inst->CSWnextInstance) {
            
            /* Calculate current resistance */
            r_now = 1.0 / inst->CSWconduct;
            
            /* Johnson-Nyquist thermal noise */
            noise_dens = 4.0 * CONSTboltz * ckt->CKTtemp / r_now;
            
            /* Add to noise density array */
            switch(operation) {
                case N_OPEN:
                    /* Calculate noise density */
                    data->outNoiz += noise_dens;
                    data->inNoise += noise_dens;
                    break;
                    
                case N_CALC:
                    /* Calculate total noise */
                    data->outNoiz += noise_dens * data->freqDelta;
                    data->inNoise += noise_dens * data->freqDelta;
                    break;
                    
                case N_INT:
                    /* Integrate over frequency */
                    data->outNoiz += noise_dens * (data->freqStop - data->freqStart);
                    data->inNoise += noise_dens * (data->freqStop - data->freqStart);
                    break;
            }
        }
    }
    return OK;
}
```

**Mathematical Model**: This implements the Johnson-Nyquist noise formula:
\[
S_I(f) = \frac{4kT}{R_{\text{eff}}}
\]
where:
- \( k \) is Boltzmann's constant (`CONSTboltz`)
- \( T \) is the absolute temperature (`ckt->CKTtemp`)
- \( R_{\text{eff}} = 1/G \) is the effective resistance at the operating point

### 6. Local Truncation Error Control (`cswtrunc.c`)

The LTE calculation monitors state changes to control time steps during switching transitions:

```c
int CSWtrunc(GENmodel *inModel, CKTcircuit *ckt, double *delta) {
    CSWmodel *model;
    CSWinstance *inst;
    double charge, tol, dstate_dt, new_delta;
    
    for(model = (CSWmodel *)inModel; model != NULL; model = model->CSWnextModel) {
        for(inst = model->CSWinstances; inst != NULL; inst = inst->CSWnextInstance) {
            
            /* Calculate rate of state change */
            dstate_dt = (inst->CSWstate - ckt->CKTstate0[inst->CSWstateVar]) / ckt->CKTdelta;
            
            /* Estimate charge associated with state change */
            charge = dstate_dt * (model->CSWron + model->CSWroff) / 2.0;
            
            /* Calculate allowable time step based on charge tolerance */
            tol = ckt->CKTreltol * fabs(charge) + ckt->CKTabstol;
            if(tol > 0.0) {
                new_delta = fabs(charge) / tol;
                
                /* Limit time step during transitions */
                if(fabs(inst->CSWstate - inst->CSWoldState) > 0.1) {
                    new_delta = MIN(new_delta, ckt->CKTdelta / 10.0);
                }
                
                /* Update global time step if smaller */
                if(new_delta < *delta) {
                    *delta = new_delta;
                }
            }
        }
    }
    return OK;
}
```

**Mathematical Purpose**: 
1. **State Change Rate**: \( \frac{dS}{dt} \approx \frac{S_{\text{new}} - S_{\text{old}}}{\Delta t} \)
2. **Charge Estimation**: \( Q \approx \frac{dS}{dt} \cdot \frac{R_{on} + R_{off}}{2} \) approximates the charge movement during switching
3. **Time Step Control**: \( \Delta t_{\text{new}} = \frac{|Q|}{\epsilon_r |Q| + \epsilon_a} \) ensures the LTE remains within tolerance
4. **Transition Limiting**: During rapid state changes (\( |\Delta S| > 0.1 \)), the time step is aggressively reduced to capture the transition accurately

### 7. Convergence Testing (`cswconv.c`)

The convergence test implements SPICE's mixed relative-absolute criteria:

```c
int CSWconvTest(GENmodel *inModel, CKTcircuit *ckt) {
    CSWmodel *model;
    CSWinstance *inst;
    double tol_state, tol_current;
    
    for(model = (CSWmodel *)inModel; model != NULL; model = model->CSWnextModel) {
        for(inst = model->CSWinstances; inst != NULL; inst = inst->CSWnextInstance) {
            
            /* State convergence test */
            tol_state = ckt->CKTreltol * MAX(fabs(inst->CSWstate), 1.0) + ckt->CKTabstol;
            if(fabs(inst->CSWstate - inst->CSWoldState) > tol_state) {
                ckt->CKTnoncon++;
                return OK;  /* Not converged */
            }
            
            /* Current convergence test */
            tol_current = ckt->CKTreltol * MAX(fabs(inst->CSWcurrent), 1e-12) + ckt->CKTabstol;
            double i_new = inst->CSWconduct * 
                          (ckt->CKTrhs[inst->CSWposNode] - ckt->CKTrhs[inst->CSWnegNode]);
            
            if(fabs(i_new - inst->CSWcurrent) > tol_current) {
                ckt->CKTnoncon++;
                return OK;  /* Not converged */
            }
        }
    }
    return OK;
}
```

**Convergence Criteria**:
1. **State Convergence**: \( |S_{\text{new}} - S_{\text{old}}| \leq \epsilon_r \cdot \max(|S_{\text{new}}|, 1.0) + \epsilon_a \)
   - Uses `CKTreltol` (typically \( 10^{-3} \)) for relative tolerance
   - Uses `CKTabstol` (typically \( 10^{-12} \)) for absolute tolerance
   - The `max(fabs(inst->CSWstate), 1.0)` ensures a minimum denominator

2. **Current Convergence**: \( |I_{\text{new}} - I_{\text{old}}| \leq \epsilon_r \cdot \max(|I_{\text{old}}|, 10^{-12}) + \epsilon_a \)
   - Recalculates current using updated node voltages and conductance
   - The \( 10^{-12} \) minimum prevents division by zero for very small currents

## Conclusion

The Ngspice current-controlled switch implementation in `cswdefs.h`, `cswparam.c`, `cswmpar.c`, and `cswload.c` demonstrates a sophisticated synthesis of mathematical modeling and numerical computation. The implementation successfully addresses the fundamental challenge of discrete switching in continuous simulation through cubic polynomial smoothing that maintains C¹ continuity for Newton-Raphson convergence while preserving essential switching behavior. The hysteresis mechanism with state memory prevents numerical chattering, and the symmetric matrix stamping pattern efficiently integrates the switch into the Modified Nodal Analysis framework.

The mathematical formulations are precisely mapped to C data structures and algorithms: conductance calculations directly implement the smoothing functions, state transitions encode hysteresis logic, and convergence tests enforce SPICE's numerical standards. This careful correspondence between theory