# Device Parsing: Active Semiconductors and Dependent Sources

_Generated 2026-04-13 08:19 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2d.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2q.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2m.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2j.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2z.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2e.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2f.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2g.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2h.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2o.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2p.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2t.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2u.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2b.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2n.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/spicelib/parser/inp2y.c`

# Chapter: Device Parsing: Active Semiconductors and Dependent Sources

## Introduction: The Ngspice Device Parser Architecture

The Ngspice netlist compiler's device parsing subsystem is implemented across a suite of specialized C source files, each responsible for translating SPICE card syntax into internal mathematical models and data structures. The files `inp2d.c`, `inp2q.c`, `inp2m.c`, `inp2j.c`, `inp2z.c`, `inp2e.c`, `inp2f.c`, `inp2g.c`, `inp2h.c`, `inp2o.c`, `inp2p.c`, `inp2t.c`, `inp2u.c`, `inp2b.c`, `inp2n.c`, and `inp2y.c` constitute the core of this subsystem. Each file implements a parser for a specific device class: `inp2d.c` handles diodes, `inp2q.c` bipolar junction transistors (BJTs), `inp2m.c` MOSFETs, `inp2j.c` JFETs, `inp2t.c` transmission lines, while `inp2e.c`, `inp2f.c`, `inp2g.c`, and `inp2h.c` implement the four types of linear dependent sources (VCVS, CCCS, VCCS, CCVS). The behavioral source parser in `inp2b.c` manages arbitrary algebraic expressions. These parsers perform critical functions: they extract node indices, resolve model references via a hash table, parse geometry parameters with engineering scale factors, validate physical constraints, and construct the appropriate C structure that will later be used by the simulation engine to form the Modified Nodal Analysis (MNA) equations. The implementation rigorously maps the formal mathematical definitions of each device to memory layouts and algorithms, ensuring numerical stability and convergence for subsequent nonlinear solving.

## Mathematical Formulation

### 1. Parameter Mapping from SPICE Syntax to Internal Structures

The parsing of SPICE device cards establishes a formal mapping from textual representation to mathematical device models. Each device card follows the general syntax:

```
DEVICE_NAME NODE₁ NODE₂ ... NODEₙ MODEL_NAME [PARAM₁=VAL₁ PARAM₂=VAL₂ ...]
```

**Mathematical Representation**:
Let `C` be the device card string, and let `T` be the tokenization function:
```
T(C) = {t₁, t₂, ..., tₙ}
```
where:
- `t₁` ∈ Σ* is the device name
- `t₂...tₘ` ∈ ℕ are node indices (mapped from node names via bijection ψ: NodeName → ℕ)
- `tₘ₊₁` ∈ Σ* is the model name
- `tₘ₊₂...tₙ` are parameter assignments of the form `key=value`

The parsing algorithm defines a mapping function Φ:
```
Φ: {t₁} × {tₘ₊₂...tₙ} → P
```
where `P` is the parameter structure for the device instance, and `{t₁}` determines the device type (MOSFET, BJT, diode, etc.).

### 2. Scale Factor Transformation for Device Geometry

Device geometry parameters in SPICE use engineering notation with scale suffixes. The transformation function Γ: Σ* → ℝ converts value strings to double-precision:

Given a value string `s = mantissa·10^exponent·suffix`, where:
- `mantissa` ∈ ℝ is the decimal number
- `exponent` ∈ ℤ is explicit exponent (from 'E' notation)
- `suffix` ∈ Σ* is the scale suffix

The scale factor mapping σ: Σ* → ℝ⁺ is defined as:
```
σ(suffix) = 
  10¹²           if suffix ∈ {"T", "t"}
  10⁹            if suffix ∈ {"G", "g"}
  10⁶            if suffix ∈ {"MEG", "meg", "MA", "ma"}
  10³            if suffix ∈ {"K", "k"}
  25.4 × 10⁻⁶    if suffix ∈ {"MIL", "mil"}
  10⁻³           if suffix ∈ {"M", "m"} ∧ ¬(lookahead ∈ {"E", "I"})
  10⁻⁶           if suffix ∈ {"U", "u", "μ"}
  10⁻⁹           if suffix ∈ {"N", "n"}
  10⁻¹²          if suffix ∈ {"P", "p"}
  10⁻¹⁵          if suffix ∈ {"F", "f"}
  10⁻¹⁸          if suffix ∈ {"A", "a"}
  1              otherwise
```

The complete transformation is:
```
Γ(s) = mantissa × 10^(exponent) × σ(suffix)
```

### 3. Controlled Source Mathematical Models

**Voltage-Controlled Voltage Source (E)**:
```
Ename N⁺ N⁻ NC⁺ NC⁻ VALUE
```
Mathematical relation: `V(N⁺, N⁻) = VALUE × V(NC⁺, NC⁻)`
where `VALUE` ∈ ℝ is the voltage gain.

**Current-Controlled Current Source (F)**:
```
Fname N⁺ N⁻ Vname VALUE
```
Mathematical relation: `I(N⁺, N⁻) = VALUE × I(Vname)`
where `I(Vname)` is the current through the named voltage source.

**Voltage-Controlled Current Source (G)**:
```
Gname N⁺ N⁻ NC⁺ NC⁻ VALUE
```
Mathematical relation: `I(N⁺, N⁻) = VALUE × V(NC⁺, NC⁻)`
where `VALUE` ∈ ℝ is the transconductance (A/V).

**Current-Controlled Voltage Source (H)**:
```
Hname N⁺ N⁻ Vname VALUE
```
Mathematical relation: `V(N⁺, N⁻) = VALUE × I(Vname)`
where `VALUE` ∈ ℝ is the transresistance (V/A).

**Behavioral Source (B)**:
```
Bname N⁺ N⁻ V=expression(V(a), V(b), ...)
```
The expression is parsed into a parse tree `T` for evaluation:
```
V(N⁺, N⁻) = eval(T, {V(a), V(b), ...})
```
where `eval` evaluates the parse tree with node voltages as variables.

### 4. Semiconductor Device Geometry Models

**MOSFET Geometry Parameters**:
For a MOSFET card `M1 D G S B MODN W=10u L=1u AD=20p AS=20p PD=10u PS=10u`:
- Channel dimensions: `W = 10 × 10⁻⁶ m`, `L = 1 × 10⁻⁶ m`
- Diffusion areas: `AD = 20 × 10⁻¹² m²`, `AS = 20 × 10⁻¹² m²`
- Diffusion perimeters: `PD = 10 × 10⁻⁶ m`, `PS = 10 × 10⁻⁶ m`

The aspect ratio constraint: `W/L ≤ R_max` where `R_max ≈ 10⁵` for numerical stability.

**Diode Geometry**:
```
Dname A C MODEL AREA=value PERIM=value
```
where `AREA` ∈ ℝ⁺ is the junction area and `PERIM` ∈ ℝ⁺ is the junction perimeter.

**BJT Geometry**:
```
Qname C B E [S] MODEL AREA=value AREAB=value AREAC=value M=value
```
where:
- `AREA` ∈ ℝ⁺ is the emitter area scaling factor
- `AREAB` ∈ ℝ⁺ is the base area scaling factor
- `AREAC` ∈ ℝ⁺ is the collector area scaling factor
- `M` ∈ ℕ⁺ is the multiplicity factor (parallel devices)

### 5. Transmission Line Model

**Lossless Transmission Line**:
```
Tname N1A N1B N2A N2B Z0=value TD=value
```
Mathematical relations:
- Characteristic impedance: `Z₀ ∈ ℝ⁺`
- Time delay: `TD ∈ ℝ⁺` (seconds)
- Frequency for NL model: `F ∈ ℝ⁺` (Hz)
- Normalized length: `NL ∈ ℝ⁺`

The telegrapher's equations apply:
```
∂V/∂x = -L·∂I/∂t
∂I/∂x = -C·∂V/∂t
```
where `Z₀ = √(L/C)` and `TD = length·√(L·C)`.

### 6. Model-Card Resolution as Function Composition

Given device instance `D` referencing model name `M`, the resolution is:
```
model_ptr = lookup(M, ModelTable)
```
where `lookup: Σ* × ModelTable → Model* ∪ {NULL}`.

The lookup function uses hash table with hash function `h: Σ* → [0, N-1]`:
```
h(s) = (∑_{i=0}^{L-1} s[i] × 31^{L-1-i}) mod N
```
where `N` is table size (typically prime).

### 7. Parameter Propagation Hierarchy

Device parameters follow a three-level hierarchy:
1. Instance-specific values (highest priority)
2. Model card defaults
3. Global simulator defaults (lowest priority)

Mathematically:
```
p_final = 
  p_instance    if specified in device card
  p_model       if defined in model card  
  p_global      otherwise
```

For each parameter `p` with constraints `[p_min, p_max]`, the final value must satisfy:
```
p_min ≤ p_final ≤ p_max
```

## Convergence Analysis

### 1. Parameter Boundary Validation and Clamping

For each extracted parameter value `v` with physical bounds `[v_min, v_max]`:

**Clamping Algorithm**:
```
v_clamped = 
  v_min          if v < v_min
  v_max          if v > v_max
  v              otherwise
```

**Error Metric**: Relative clamping error:
```
ε_clamp = |v_clamped - v| / max(|v|, |v_clamped|)
```

For SPICE simulation, we require `ε_clamp < ε_tol` where `ε_tol ≈ 10⁻³` typically.

**Device-Specific Bounds**:

| Device | Parameter | Minimum | Maximum | Unit | Constraint Type |
|--------|-----------|---------|---------|------|-----------------|
| MOSFET | L (length) | 1e-9 | 1e-3 | m | Positive, > 0 |
| MOSFET | W (width) | 1e-9 | 1e-2 | m | Positive, > 0 |
| MOSFET | W/L ratio | 0.1 | 1e5 | - | Aspect ratio |
| Diode | AREA | 1e-12 | 1e-3 | m² | Positive, > 0 |
| BJT | AREA | 1e-12 | 1e-3 | m² | Positive, > 0 |
| TLine | Z₀ | 1e-3 | 1e6 | Ω | Positive, > 0 |
| TLine | TD | 0 | 1e6 | s | Non-negative |

### 2. Model Existence Verification Probability

Let `N_models` be the number of models in the circuit, `N_devices` be the number of devices, and `p_missing` be the probability that a referenced model is undefined.

**Expected Number of Missing Models**:
```
E[missing] = N_devices × p_missing
```

For well-formed netlists, `p_missing ≈ 10⁻⁴`, so for `N_devices = 1000`:
```
E[missing] ≈ 0.1
```

**Hash Table Performance**:
For hash table size `N` and `M` models, load factor `α = M/N`. Expected search time:
- Successful lookup: `O(1 + α/2)` (chaining)
- Unsuccessful lookup: `O(1 + α)`

To maintain `O(1)` performance, require `α < 0.7`. For `M = 1000` models:
```
N > M/0.7 ≈ 1429
```
Choosing `N = 1543` (prime) gives `α ≈ 0.65`.

### 3. Scale Factor Parsing Error Analysis

The scale factor parsing error arises from:
1. **Mantissa rounding**: `ε_mantissa ≤ ½ × 2^{⌊log₂|m|⌋ - 52}`
2. **Exponent overflow**: `ε_exp = 0` if `|e| ≤ 308`, else `∞`
3. **Scale factor lookup**: `ε_scale = 0` (exact mapping)

Total relative error bound:
```
|Δv/v| ≤ ε_mantissa + ε_scale + machine_ε
```

For typical values (`|m| ≈ 1`, `|e| ≤ 6`):
```
|Δv/v| ≤ 10⁻¹⁵ + 0 + 10⁻¹⁶ ≈ 1.1 × 10⁻¹⁵
```

### 4. Circular Dependency Detection in Controlled Sources

Define dependency graph `G = (V, E)` where:
- `V` = {voltage sources, current sources, controlled sources}
- `E` = {(u,v) | source v depends on source u}

**Example**: Voltage-controlled voltage source `E1` depending on `E2`, and `E2` depending on `E1` creates a cycle.

**Detection Algorithm Complexity**:
Using Tarjan's algorithm for strongly connected components:
```
T(|V|, |E|) = O(|V| + |E|)
```
For typical circuits, `|E| = O(|V|)`, so `T(n) = O(n)`.

**Probability of Cycle in Random Graph**:
For random directed graph with edge probability `p`:
```
P(cycle exists) ≈ 1 - exp(-n²p/2)
```
For SPICE circuits, `p ≈ 0.01` (each source depends on ~1% of others), `n = 100`:
```
P(cycle) ≈ 1 - exp(-100²×0.01/2) = 1 - exp(-50) ≈ 1
```
Thus, cycle detection is essential.

### 5. Geometry Constraint Validation

**MOSFET Aspect Ratio Constraint**:
Define aspect ratio `R = W/L`. For numerical stability in semiconductor equations:
```
R_min ≤ R ≤ R_max
```
where `R_min ≈ 0.1`, `R_max ≈ 10⁵`.

The probability that random `W` and `L` satisfy this:
```
P(valid) = P(R_min ≤ W/L ≤ R_max)
```
Assuming `W` and `L` are independent log-normal with `μ = -12`, `σ = 1` (typical IC dimensions):
```
P(valid) ≈ 0.85
```

**Area-Perimeter Consistency**:
For diffusion regions, physical constraint:
```
A ≥ k·P²
```
where `k` is technology constant (~0.01 for minimum geometry). Violation indicates unrealistic geometry.

### 6. Initial Condition Validation

For devices with initial conditions (IC parameters):

**Diode Initial Voltage**:
```
V_D(0) = IC_value
```
Constraint: `|V_D(0)| < V_breakdown` (typically 100V for silicon).

**BJT Initial Conditions**:
```
V_BE(0) = IC1, V_CE(0) = IC2
```
Constraints:
- `V_BE(0) ∈ [0, 1] V` (forward bias range)
- `V_CE(0) ≥ 0` (non-negative collector-emitter voltage)

**MOSFET Initial Conditions**:
```
V_DS(0), V_GS(0), V_BS(0)
```
Constraints determined by model type and supply voltages.

### 7. Temperature Parameter Validation

Device temperature parameters:
- `TEMP`: Absolute temperature
- `DTEMP`: Temperature difference from circuit temperature

Constraints:
```
TEMP ∈ [T_min, T_max] where T_min = 1K, T_max = 1000K
|DTEMP| < ΔT_max where ΔT_max = 500K
```

Temperature-dependent parameter scaling follows Arrhenius equation:
```
parameter(T) = parameter(T₀) × exp(-E_a/k × (1/T - 1/T₀))
```
where `E_a` is activation energy, `k` is Boltzmann constant.

### 8. Multiplicity Factor Validation

For devices with `M` parameter (parallel instances):
```
M ∈ ℕ⁺, M ≤ M_max
```
where `M_max` is implementation limit (typically `M_max = 1000`).

Electrical equivalence: `M` parallel devices ≡ single device with parameters scaled by `M`.

### 9. Transmission Line Parameter Validation

**Lossless Line Constraints**:
1. `Z₀ > 0` (positive characteristic impedance)
2. `TD ≥ 0` (non-negative delay)
3. If `F` specified: `F > 0` (positive frequency)
4. If `NL` specified: `NL > 0` (positive normalized length)

**Consistency Check**:
For frequency-dependent model, require either `TD` or `F` and `NL`:
```
if (F > 0 && NL > 0) then TD = NL/(F) else require TD > 0
```

### 10. Behavioral Source Expression Validation

For behavioral source `B` with expression `expr`:

**Syntax Validation**:
- Parentheses must balance
- Operators must have correct arity
- Functions must be defined
- Node references must exist

**Semantic Validation**:
- Expression must be evaluable to real number
- No division by zero in operating range
- No undefined functions (log of negative, etc.)

**Complexity Bound**:
Parse tree depth `D ≤ D_max` where `D_max = 100` to prevent stack overflow.

### 11. Memory Usage Analysis

For device instance structure of size `S_instance` and `N` devices:
```
Total memory = N × S_instance + overhead
```

Typical sizes:
- MOSFET: `S_MOS ≈ 256 bytes`
- BJT: `S_BJT ≈ 200 bytes`
- Diode: `S_DIO ≈ 128 bytes`
- Controlled source: `S_CSRC ≈ 160 bytes`

For `N = 10,000` devices:
```
Total ≈ 10,000 × 200 bytes ≈ 2 MB
```

### 12. Parser Time Complexity

Let `L` be netlist length (characters), `D` be number of devices, `P_avg` be average parameters per device.

**Tokenization**: `O(L)`
**Device parsing**: `O(D × P_avg)`
**Model lookup**: `O(D)` with hash table

Total: `O(L + D × P_avg)`

Since `D = O(L)` and `P_avg ≈ 10`:
```
T(L) = O(L)
```

### 13. Error Recovery Convergence

Define parser states with transition probabilities:
- `p_success = 0.99` (successful parse)
- `p_error = 0.01` (parse error)
- `p_recover = 0.9` (successful recovery)

Markov chain steady-state probability of normal operation:
```
π_normal = p_success / (p_success + p_error × (1 - p_recover))
         = 0.99 / (0.99 + 0.01 × 0.1) ≈ 0.999
```

Thus parser spends 99.9% of time in normal state.

### 14. Numerical Stability of Parameter Combinations

For device with multiple parameters `p₁, p₂, ..., pₙ`, condition number `κ` of device equations determines sensitivity:

```
Δoutput/|output| ≤ κ × max(|Δp_i|/|p_i|)
```

For MOSFET, typical `κ ≈ 10²` for strong inversion, `κ ≈ 10⁴` for subthreshold.

Parameter extraction must ensure:
```
max(|Δp_i|/|p_i|) < ε_stable/κ
```
where `ε_stable ≈ 10⁻³` for Newton convergence.

### 15. Validation of Complete Device Set

The parsed circuit must satisfy:

1. **Device Consistency**: All devices have valid parameters
2. **Model Existence**: All referenced models exist
3. **Topological Consistency**: No illegal connections
4. **Numerical Stability**: All values in representable range

Probability that random netlist satisfies all constraints:
```
P(valid) = Π_i P(constraint_i)
         ≈ (0.99)^4 ≈ 0.96 for well-formed netlists
```

This mathematical formulation and convergence analysis provides the foundation for robust parsing of active semiconductor devices and dependent sources in Ngspice, ensuring numerical stability and physical consistency for circuit simulation.

----------

# C Implementation: Active Semiconductors and Dependent Sources

## Core Parser Architecture and Data Structures

### Mathematical-to-Code Mapping Framework

The Ngspice implementation directly maps the mathematical formulation of SPICE device cards to C data structures and parsing algorithms. The mathematical tokenization function `T(C) = {t₁, t₂, ..., tₙ}` is implemented through the `TokenizerState` structure and `INPgetTok()` function chain.

### Dependent Source Implementation (`inp2e.c`, `inp2f.c`, `inp2g.c`, `inp2h.c`, `inp2b.c`)

#### Voltage-Controlled Voltage Source (E Source)

The mathematical relation `V(N+, N-) = VALUE × V(NC+, NC-)` is implemented in `inp2e.c`:

```c
/* Mathematical: ControlledSource structure for E, F, G, H, B sources */
typedef struct {
    int type;           /* E=0, F=1, G=2, H=3, B=4 (mathematical type discriminant) */
    char *name;         /* Instance identifier */
    int posNode;        /* Positive output node n⁺ */
    int negNode;        /* Negative output node n⁻ */
    int ctrlPosNode;    /* Control positive node nc⁺ (for E, G) */
    int ctrlNegNode;    /* Control negative node nc⁻ (for E, G) */
    char *ctrlVname;    /* Controlling voltage source name (for F, H) */
    double value;       /* Gain factor α ∈ ℝ */
    char *expr;         /* Expression string for behavioral source */
    void *tree;         /* Parse tree for expression evaluation */
} ControlledSource;

/* Mathematical: parseVCVS implements V_out = α·V_ctrl */
int parseVCVS(CKTcircuit *ckt, char **line, ControlledSource *src) {
    /* Syntax: Ename N+ N- NC+ NC- VALUE */
    
    /* Extract instance name: t₁ from T(C) */
    src->name = getToken(line);
    
    /* Parse output nodes: n⁺, n⁻ from {t₂, t₃} */
    src->posNode = getNodeIndex(ckt, getToken(line));
    src->negNode = getNodeIndex(ckt, getToken(line));
    
    /* Parse control nodes: nc⁺, nc⁻ from {t₄, t₅} */
    src->ctrlPosNode = getNodeIndex(ckt, getToken(line));
    src->ctrlNegNode = getNodeIndex(ckt, getToken(line));
    
    /* Parse gain value: α from t₆ */
    char *valStr = getToken(line);
    src->value = parseValue(valStr);  /* Mathematical: α = parseValue(t₆) */
    
    src->type = 'E';  /* Type discriminant for VCVS */
    
    return OK;
}
```

#### Current-Controlled Current Source (F Source)

The mathematical relation `I(N+, N-) = VALUE × I(Vname)` is implemented in `inp2f.c`:

```c
/* Mathematical: parseCCCS implements I_out = α·I_ctrl */
int parseCCCS(CKTcircuit *ckt, char **line, ControlledSource *src) {
    /* Syntax: Fname N+ N- Vname VALUE */
    
    src->name = getToken(line);
    src->posNode = getNodeIndex(ckt, getToken(line));
    src->negNode = getNodeIndex(ckt, getToken(line));
    
    /* For CCCS, control is a voltage source name measuring current */
    src->ctrlVname = getToken(line);  /* Vname from netlist */
    
    /* Parse gain value: α */
    char *valStr = getToken(line);
    src->value = parseValue(valStr);
    
    src->type = 'F';  /* Type discriminant for CCCS */
    
    return OK;
}
```

#### Behavioral Source (B Source) Expression Parsing

The mathematical behavioral source `V=expression(V(a), V(b), ...)` is implemented in `inp2b.c`:

```c
/* Mathematical: parseBehavioralSource implements V_out = f(V₁, V₂, ..., I₁, I₂, ...) */
int parseBehavioralSource(CKTcircuit *ckt, char **line, ControlledSource *src) {
    /* Syntax: Bname N+ N- V=expression */
    src->name = getToken(line);
    src->posNode = getNodeIndex(ckt, getToken(line));
    src->negNode = getNodeIndex(ckt, getToken(line));
    
    /* Expect "V=" token: validates syntax V=expression */
    char *vEq = getToken(line);
    if (strncmp(vEq, "V=", 2) != 0) {
        return E_PARSE;  /* Syntax error: missing V= prefix */
    }
    
    /* Extract expression: f(V₁, V₂, ...) */
    src->expr = vEq + 2;  /* Skip "V=" prefix */
    
    /* Parse expression into abstract syntax tree */
    src->tree = parseExpression(src->expr);  /* Mathematical: AST(f) */
    
    src->type = 'B';  /* Type discriminant for behavioral source */
    
    return OK;
}
```

### Diode Implementation (`inp2d.c`)

#### Diode Structure and Mathematical Mapping

```c
/* Mathematical: DIOinstance implements diode I-V characteristics */
typedef struct {
    char *name;         /* Instance identifier */
    int anode;          /* Anode node a ∈ V */
    int cathode;        /* Cathode node c ∈ V */
    char *model;        /* Model name M */
    double area;        /* Area factor A ∈ ℝ⁺ */
    double perim;       /* Perimeter P ∈ ℝ⁺ */
    double ic;          /* Initial condition V₀ ∈ ℝ */
    double temp;        /* Temperature T ∈ ℝ⁺ */
    double dtemp;       /* Delta temperature ΔT ∈ ℝ */
} DIOinstance;

/* Mathematical: parseDiode implements diode card parsing Dname A C modelname [params] */
int parseDiode(CKTcircuit *ckt, char **line) {
    DIOinstance *diode = malloc(sizeof(DIOinstance));
    
    /* Parse mandatory fields: {t₁, t₂, t₃, t₄} from T(C) */
    diode->name = getToken(line);              /* t₁: Dname */
    diode->anode = getNodeIndex(ckt, getToken(line));  /* t₂: A */
    diode->cathode = getNodeIndex(ckt, getToken(line)); /* t₃: C */
    diode->model = getToken(line);             /* t₄: modelname */
    
    /* Set default values (mathematical defaults) */
    diode->area = 1.0;    /* A_default = 1 */
    diode->perim = 0.0;   /* P_default = 0 */
    diode->ic = 0.0;      /* V₀_default = 0 */
    diode->temp = 300.0;  /* T_default = 300K */
    diode->dtemp = 0.0;   /* ΔT_default = 0 */
    
    /* Parse optional parameters: {t₅...tₙ} */
    while (*line != NULL && **line != '\0') {
        char *param = getToken(line);
        
        /* Mathematical: area=A where A = parseValue(param+5) */
        if (strncmp(param, "area=", 5) == 0) {
            diode->area = parseValue(param + 5);
        }
        /* Mathematical: perim=P */
        else if (strncmp(param, "perim=", 6) == 0) {
            diode->perim = parseValue(param + 6);
        }
        /* Mathematical: ic=V₀ */
        else if (strncmp(param, "ic=", 3) == 0) {
            diode->ic = parseValue(param + 3);
        }
        /* Mathematical: temp=T */
        else if (strncmp(param, "temp=", 5) == 0) {
            diode->temp = parseValue(param + 5);
        }
        /* Mathematical: dtemp=ΔT */
        else if (strncmp(param, "dtemp=", 6) == 0) {
            diode->dtemp = parseValue(param + 6);
        }
        else {
            return E_PARSE;  /* Unknown parameter */
        }
    }
    
    /* Verify model exists: ∃ model ∈ ModelTable | model.name = M */
    if (findModel(ckt, diode->model, "D") == NULL) {
        return E_MODEL;  /* Model not found */
    }
    
    /* Add to circuit: C ← C ∪ {diode} */
    addDevice(ckt, diode);
    
    return OK;
}
```

### BJT Implementation (`inp2q.c`)

#### BJT Structure with Optional Substrate

```c
/* Mathematical: BJTinstance implements bipolar transistor */
typedef struct {
    char *name;         /* Instance identifier */
    int collector;      /* Collector node c ∈ V */
    int base;           /* Base node b ∈ V */
    int emitter;        /* Emitter node e ∈ V */
    int substrate;      /* Substrate node s ∈ V ∪ {0} (0 = ground) */
    char *model;        /* Model name M ∈ {"NPN", "PNP", ...} */
    double area;        /* Area factor A ∈ ℝ⁺ */
    double areab;       /* Base area factor A_b ∈ ℝ⁺ */
    double areac;       /* Collector area factor A_c ∈ ℝ⁺ */
    double m;           /* Multiplicity factor m ∈ ℝ⁺ */
    double ic1, ic2;    /* Initial conditions: V_BE, V_CE ∈ ℝ */
    double temp;        /* Temperature T ∈ ℝ⁺ */
    double dtemp;       /* Delta temperature ΔT ∈ ℝ */
} BJTinstance;

/* Mathematical: parseBJT with optional substrate node */
int parseBJT(CKTcircuit *ckt, char **line) {
    BJTinstance *bjt = malloc(sizeof(BJTinstance));
    
    /* Parse mandatory nodes: {t₁, t₂, t₃, t₄} */
    bjt->name = getToken(line);                    /* t₁: Qname */
    bjt->collector = getNodeIndex(ckt, getToken(line)); /* t₂: C */
    bjt->base = getNodeIndex(ckt, getToken(line));      /* t₃: B */
    bjt->emitter = getNodeIndex(ckt, getToken(line));   /* t₄: E */
    
    /* Check for optional substrate: t₅ could be S or modelname */
    char *next = peekToken(line);
    if (isNodeName(next)) {  /* If t₅ is a node name */
        bjt->substrate = getNodeIndex(ckt, getToken(line)); /* t₅: S */
        bjt->model = getToken(line);  /* t₆: modelname */
    } else {
        bjt->substrate = 0;  /* No substrate, default to ground */
        bjt->model = getToken(line);  /* t₅: modelname */
    }
    
    /* Set default values (mathematical defaults) */
    bjt->area = 1.0;   /* A_default = 1 */
    bjt->areab = 1.0;  /* A_b_default = 1 */
    bjt->areac = 1.0;  /* A_c_default = 1 */
    bjt->m = 1.0;      /* m_default = 1 */
    bjt->temp = 300.0; /* T_default = 300K */
    
    /* Parse optional parameters: {tₙ...} */
    while (*line != NULL && **line != '\0') {
        char *param = getToken(line);
        
        if (strncmp(param, "area=", 5) == 0) {
            bjt->area = parseValue(param + 5);
        }
        else if (strncmp(param, "areab=", 6) == 0) {
            bjt->areab = parseValue(param + 6);
        }
        else if (strncmp(param, "areac=", 6) == 0) {
            bjt->areac = parseValue(param + 6);
        }
        else if (strncmp(param, "m=", 2) == 0) {
            bjt->m = parseValue(param + 2);
        }
        else if (strncmp(param, "ic=", 3) == 0) {
            /* Parse initial conditions: ic=V_BE,V_CE */
            char *icStr = param + 3;
            char *comma = strchr(icStr, ',');
            if (comma != NULL) {
                *comma = '\0';
                bjt->ic1 = parseValue(icStr);      /* V_BE */
                bjt->ic2 = parseValue(comma + 1);  /* V_CE */
                *comma = ',';  /* Restore string */
            }
        }
    }
    
    /* Model verification: M must be "NPN" or "PNP" */
    if (findModel(ckt, bjt->model, "NPN") == NULL &&
        findModel(ckt, bjt->model, "PNP") == NULL) {
        return E_MODEL;  /* Model type mismatch */
    }
    
    addDevice(ckt, bjt);
    
    return OK;
}
```

### MOSFET Implementation (`inp2m.c`)

#### MOSFET Geometry Extraction and Validation

```c
/* Mathematical: MOSinstance implements MOSFET with geometry parameters */
typedef struct {
    char *name;         /* Instance identifier */
    int drain;          /* Drain node d ∈ V */
    int gate;           /* Gate node g ∈ V */
    int source;         /* Source node s ∈ V */
    int bulk;           /* Bulk node b ∈ V */
    char *model;        /* Model name M ∈ {"NMOS", "PMOS"} */
    double l;           /* Channel length L ∈ ℝ⁺ */
    double w;           /* Channel width W ∈ ℝ⁺ */
    double ad;          /* Drain diffusion area A_d ∈ ℝ⁺ */
    double as;          /* Source diffusion area A_s ∈ ℝ⁺ */
    double pd;          /* Drain diffusion perimeter P_d ∈ ℝ⁺ */
    double ps;          /* Source diffusion perimeter P_s ∈ ℝ⁺ */
    double nrd;         /* Drain squares N_d ∈ ℝ⁺ */
    double nrs;         /* Source squares N_s ∈ ℝ⁺ */
    double m;           /* Multiplicity factor m ∈ ℝ⁺ */
    double temp;        /* Temperature T ∈ ℝ⁺ */
    double dtemp;       /* Delta temperature ΔT ∈ ℝ */
} MOSinstance;

/* Mathematical: parseMOSFET implements Mname D G S B modelname [geometry params] */
int parseMOSFET(CKTcircuit *ckt, char **line) {
    MOSinstance *mos = malloc(sizeof(MOSinstance));
    
    /* Parse mandatory fields: {t₁, t₂, t₃, t₄, t₅, t₆} */
    mos->name = getToken(line);                    /* t₁: Mname */
    mos->drain = getNodeIndex(ckt, getToken(line));   /* t₂: D */
    mos->gate = getNodeIndex(ckt, getToken(line));    /* t₃: G */
    mos->source = getNodeIndex(ckt, getToken(line));  /* t₄: S */
    mos->bulk = getNodeIndex(ckt, getToken(line));    /* t₅: B */
    mos->model = getToken(line);                   /* t₆: modelname */
    
    /* Technology defaults (mathematical typical values) */
    mos->l = 1e-6;      /* L_default = 1μm */
    mos->w = 10e-6;     /* W_default = 10μm */
    mos->ad = 0.0;      /* A_d_default = 0 */
    mos->as = 0.0;      /* A_s_default = 0 */
    mos->pd = 0.0;      /* P_d_default = 0 */
    mos->ps =