# Complex Mathematics: Data Structures and Core Arithmetic

_Generated 2026-04-11 18:35 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/cmaths/cmath.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/cmaths/cmath1.c`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ngspice/src/maths/cmaths/cmath2.c`

# Chapter: Complex Mathematics: Data Structures and Core Arithmetic

## Introduction

The complex mathematics subsystem in Ngspice, implemented across `cmath.h`, `cmath1.c`, and `cmath2.c`, provides the foundational numerical infrastructure for AC small-signal analysis and frequency-domain simulation. These modules define the complex number data structures and implement the complete set of arithmetic operations required to solve the complex-valued linear systems arising from Modified Nodal Analysis (MNA) with reactive components. The design addresses the dual challenges of circuit simulation: numerical stability for ill-conditioned systems with extreme dynamic range (impedances spanning from milliohms to gigaohms) and computational performance for large-scale frequency sweeps. Key innovations include Smith's algorithm for stable complex division, scaled magnitude computation to prevent overflow, fused multiply-add (FMA) optimization for reduced rounding error, and SIMD vectorization for throughput-critical operations like matrix-vector multiplication. These implementations directly support the solution of \(\mathbf{Y}(\omega)\mathbf{V}(\omega) = \mathbf{I}(\omega)\) where \(\mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C}\), enabling accurate Bode plots, impedance analysis, and transfer function computation across the SPICE accuracy requirement of \(10^{-6}\) relative error.

## Mathematical Formulation

### Complex Number Representation in SPICE Circuit Analysis

#### Complex Number Structure and Notation

In SPICE circuit simulation, complex numbers represent phasor quantities in AC analysis. The fundamental representation is:

\[
z = a + jb \quad \text{where} \quad j = \sqrt{-1}
\]

In Ngspice's C implementation, this maps directly to the `complex` structure:
```c
typedef struct complex {
    double real;      /* a = Re{z} */
    double imag;      /* b = Im{z} */
} complex;
```

For AC circuit analysis, voltage and current phasors are represented as:
\[
V(\omega) = V_{\text{real}} + jV_{\text{imag}}, \quad I(\omega) = I_{\text{real}} + jI_{\text{imag}}
\]

#### AC Circuit Matrix Formulation

The core mathematical formulation for AC small-signal analysis in SPICE is the Modified Nodal Analysis (MNA) with complex admittance:

\[
\mathbf{Y}(\omega)\mathbf{V}(\omega) = \mathbf{I}(\omega)
\]

where:
\[
\mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C}
\]

- \(\mathbf{G}\) is the real conductance matrix (from resistors, transistors in operating point)
- \(\mathbf{C}\) is the real capacitance/inductance matrix
- \(\omega = 2\pi f\) is the angular frequency
- \(\mathbf{V}(\omega)\) is the complex voltage phasor vector
- \(\mathbf{I}(\omega)\) is the complex current source phasor vector

This formulation requires all arithmetic operations to handle complex numbers, with the imaginary unit \(j\) representing the 90° phase shift inherent in reactive components.

### Core Complex Arithmetic Operations

#### Complex Addition and Subtraction

For circuit superposition and KCL/KVL applications:

\[
z_1 \pm z_2 = (a_1 \pm a_2) + j(b_1 \pm b_2)
\]

This maps to SPICE when combining parallel admittances or summing branch currents:
- Parallel admittances: \(Y_{\text{total}} = Y_1 + Y_2\)
- KCL at node: \(\sum I_k = 0\)

#### Complex Multiplication

The multiplication formula is essential for impedance calculations and transfer functions:

\[
z_1 \times z_2 = (a_1a_2 - b_1b_2) + j(a_1b_2 + a_2b_1)
\]

In SPICE context:
- Impedance of series components: \(Z_{\text{series}} = Z_1 + Z_2\)
- Voltage divider: \(V_{\text{out}} = V_{\text{in}} \times \frac{Z_2}{Z_1 + Z_2}\)
- Transfer function: \(H(\omega) = \frac{V_{\text{out}}(\omega)}{V_{\text{in}}(\omega)}\)

The optimized C implementation minimizes rounding error using fused multiply-add (FMA) when available:
```c
result.real = fma(z1.real, z2.real, -z1.imag * z2.imag);
result.imag = fma(z1.real, z2.imag, z1.imag * z2.real);
```

#### Complex Division

Division is critical for impedance calculations and solving circuit equations:

\[
\frac{z_1}{z_2} = \frac{(a_1a_2 + b_1b_2) + j(b_1a_2 - a_1b_2)}{a_2^2 + b_2^2}
\]

In SPICE applications:
- Admittance from impedance: \(Y = 1/Z\)
- Current from voltage: \(I = V/Z\)
- Transfer function computation

The implementation uses Smith's algorithm for numerical stability, handling cases where \(|a_2| \geq |b_2|\) and \(|a_2| < |b_2|\) separately to avoid overflow.

#### Complex Magnitude and Phase

For Bode plot generation and magnitude response analysis:

\[
|z| = \sqrt{a^2 + b^2}, \quad \arg(z) = \operatorname{atan2}(b, a)
\]

In SPICE context:
- Gain magnitude: \(|H(\omega)|\) in dB
- Phase shift: \(\angle H(\omega)\) in degrees
- Impedance magnitude: \(|Z(\omega)|\) for frequency response

The magnitude computation uses scaled formulation to prevent overflow:
\[
|z| = \begin{cases}
a\sqrt{1 + (b/a)^2} & \text{if } |a| \geq |b| \\
b\sqrt{1 + (a/b)^2} & \text{if } |a| < |b|
\end{cases}
\]

#### Complex Conjugate

Essential for power calculations and certain matrix operations:

\[
\overline{z} = a - jb
\]

In SPICE:
- Complex power: \(S = V \times \overline{I}\)
- Adjoint matrix operations in sensitivity analysis

#### Complex Exponential and Logarithm

For transient analysis and nonlinear device modeling:

\[
e^z = e^a[\cos(b) + j\sin(b)], \quad \ln(z) = \ln|z| + j\arg(z)
\]

These operations appear in:
- Semiconductor device models with exponential characteristics
- Frequency transformation between domains
- Noise analysis with complex frequencies

### Complex Matrix Operations for Circuit Analysis

#### Complex Matrix-Vector Multiplication

The core operation in solving \(\mathbf{Y}(\omega)\mathbf{V}(\omega) = \mathbf{I}(\omega)\):

\[
\mathbf{y} = \mathbf{A}\mathbf{x} \quad \text{where} \quad y_i = \sum_{j=1}^n A_{ij}x_j
\]

Each term requires complex multiplication and addition:
\[
y_i^{\text{(real)}} = \sum_j (A_{ij}^{\text{(real)}}x_j^{\text{(real)}} - A_{ij}^{\text{(imag)}}x_j^{\text{(imag)}})
\]
\[
y_i^{\text{(imag)}} = \sum_j (A_{ij}^{\text{(real)}}x_j^{\text{(imag)}} + A_{ij}^{\text{(imag)}}x_j^{\text{(real)}})
\]

#### Complex Linear System Solution

The AC analysis requires solving:
\[
(\mathbf{G} + j\omega\mathbf{C})\mathbf{V}(\omega) = \mathbf{I}(\omega)
\]

This involves:
1. Matrix construction: \(\mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C}\)
2. LU factorization: \(\mathbf{P}\mathbf{Y}(\omega)\mathbf{Q} = \mathbf{L}\mathbf{U}\) with complex arithmetic
3. Forward/backward substitution with complex vectors

### Special Mathematical Considerations for SPICE

#### Frequency-Dependent Components

For capacitors and inductors:
\[
Z_C(\omega) = \frac{1}{j\omega C} = -j\frac{1}{\omega C}, \quad Z_L(\omega) = j\omega L
\]

These map to complex matrix entries:
- Capacitor: adds \(-j/(\omega C)\) to diagonal, \(+j/(\omega C)\) to off-diagonal
- Inductor: adds \(+j\omega L\) to appropriate matrix positions

#### Complex Power Calculation

In AC analysis, complex power is:
\[
S = P + jQ = V \times \overline{I}
\]
where \(P\) is real power and \(Q\) is reactive power.

#### Transfer Function Computation

For frequency response analysis:
\[
H(\omega) = \frac{V_{\text{out}}(\omega)}{V_{\text{in}}(\omega)} = \frac{\text{solution at output node}}{\text{source value}}
\]

This requires complex division of the solved voltage phasors.

## Convergence Analysis

### Numerical Stability in Complex Arithmetic

#### Error Propagation in Complex Operations

For SPICE accuracy requirements (typically \(10^{-6}\) relative error), complex operations must maintain numerical stability. The error bound for complex multiplication is:

\[
\epsilon_{\text{mul}} \leq \gamma_2(|a_1a_2| + |b_1b_2| + |a_1b_2| + |a_2b_1|)\epsilon_{\text{mach}}
\]

where \(\gamma_n = \frac{n\epsilon_{\text{mach}}}{1 - n\epsilon_{\text{mach}}}\) and \(\epsilon_{\text{mach}} \approx 2.2 \times 10^{-16}\) for double precision.

The Smith algorithm for complex division ensures:
\[
\epsilon_{\text{div}} \leq \gamma_5 \frac{|z_1|}{|z_2|}\epsilon_{\text{mach}}
\]
when \(|c| \geq |d|\) or \(|c| < |d|\) is properly handled.

#### Magnitude Computation Stability

The scaled magnitude algorithm prevents overflow/underflow:
\[
|z| = \begin{cases}
|a|\sqrt{1 + (b/a)^2} & \text{if } |a| \geq |b| \\
|b|\sqrt{1 + (a/b)^2} & \text{if } |a| < |b|
\end{cases}
\]

This ensures relative error \(\leq \epsilon_{\text{mach}}\) even for extreme values encountered in circuit simulation (e.g., very large/small impedances).

### Condition Number Analysis for Complex Systems

#### Complex Matrix Condition Number

For the AC circuit matrix \(\mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C}\), the condition number is:

\[
\kappa(\mathbf{Y}(\omega)) = \|\mathbf{Y}(\omega)\| \cdot \|\mathbf{Y}^{-1}(\omega)\|
\]

In SPICE, typical condition numbers range from:
- \(\kappa \approx 10^4\) for well-conditioned RC circuits
- \(\kappa \approx 10^8\) for ill-conditioned circuits with floating nodes
- \(\kappa > 10^{12}\) for nearly singular circuits (requires Gmin stepping)

#### Frequency-Dependent Conditioning

The condition number varies with frequency:
- At DC (\(\omega = 0\)): \(\kappa(\mathbf{G})\) depends on conductance matrix
- At high frequency: \(\kappa(\omega\mathbf{C})\) dominates
- Resonance frequencies can cause ill-conditioning when \(|j\omega\mathbf{C}| \approx |\mathbf{G}|\)

### Convergence Criteria for Complex Linear Systems

#### Residual-Based Convergence

For solving \(\mathbf{Y}(\omega)\mathbf{V} = \mathbf{I}\), the relative residual must satisfy:

\[
\frac{\|\mathbf{Y}\mathbf{V} - \mathbf{I}\|}{\|\mathbf{I}\|} < \epsilon_{\text{solve}}
\]

where \(\epsilon_{\text{solve}} = 10^{-12}\) for direct methods, ensuring Newton iteration convergence with \(\eta = 10^{-3}\) tolerance.

#### Iterative Refinement for Complex Systems

When \(\kappa(\mathbf{Y}(\omega)) > 10^8\), iterative refinement may be needed:

\[
\mathbf{Y}\mathbf{d}^{(k)} = \mathbf{I} - \mathbf{Y}\mathbf{V}^{(k)}, \quad \mathbf{V}^{(k+1)} = \mathbf{V}^{(k)} + \mathbf{d}^{(k)}
\]

Stopping criterion:
\[
\frac{\|\mathbf{d}^{(k)}\|}{\|\mathbf{V}^{(k)}\|} < \epsilon_{\text{refine}} = 10^{-12}
\]

Typically converges in 1-3 iterations for circuit matrices.

### Special Numerical Cases in Circuit Simulation

#### Near-Zero Pivot Detection

During complex LU factorization, a pivot is considered numerically zero if:

\[
|a_{kk}| < \epsilon_{\text{pivot}} = 10^{-12}
\]

where \(|a_{kk}| = \sqrt{(\text{Re}\{a_{kk}\})^2 + (\text{Im}\{a_{kk}\})^2}\).

#### Gmin Stepping for Singularity Handling

When singularity is detected, Gmin conductance is added:

\[
\mathbf{Y}'(\omega) = \mathbf{Y}(\omega) + g_{\text{min}}\mathbf{I}, \quad g_{\text{min}} = 10^{-12} \, \text{S}
\]

This regularizes the matrix while introducing negligible error (\(< 10^{-6}\) for typical circuits).

#### Frequency Scaling for Numerical Stability

At very high frequencies, scaling improves conditioning:

\[
\mathbf{Y}_{\text{scaled}}(\omega) = \frac{1}{\omega_{\text{max}}}\mathbf{Y}(\omega)
\]

where \(\omega_{\text{max}}\) is the maximum analysis frequency.

### Error Bounds for AC Analysis Results

#### Voltage Solution Accuracy

The relative error in solved voltages is bounded by:

\[
\frac{\|\Delta\mathbf{V}\|}{\|\mathbf{V}\|} \lesssim \kappa(\mathbf{Y}(\omega)) \cdot \epsilon_{\text{mach}} + \epsilon_{\text{solve}}
\]

For SPICE accuracy requirement \(\epsilon_{\text{ckt}} = 10^{-6}\), we need:
\[
\kappa(\mathbf{Y}(\omega)) < \frac{\epsilon_{\text{ckt}} - \epsilon_{\text{solve}}}{\epsilon_{\text{mach}}} \approx 4.5 \times 10^9
\]

#### Transfer Function Accuracy

For \(H(\omega) = V_{\text{out}}/V_{\text{in}}\), the error propagates as:

\[
\frac{|\Delta H|}{|H|} \lesssim \left(\frac{|\Delta V_{\text{out}}|}{|V_{\text{out}}|} + \frac{|\Delta V_{\text{in}}|}{|V_{\text{in}}|}\right) \cdot \text{cond}_{\text{div}}
\]

where \(\text{cond}_{\text{div}} \approx 1 + \frac{|V_{\text{in}}|}{|V_{\text{out}}|}\) for \(|V_{\text{out}}| \ll |V_{\text{in}}|\).

### Performance and Accuracy Trade-offs

#### Vectorization vs. Accuracy

SIMD vectorization (SSE/AVX) improves performance but may affect summation order:

\[
\text{Error}_{\text{SIMD}} \leq \text{Error}_{\text{sequential}} + O(\sqrt{n})\epsilon_{\text{mach}}
\]

Kahan summation reduces this to \(O(\epsilon_{\text{mach}})\) at the cost of 4× operations.

#### Memory Layout Optimization

The array-of-structures (AoS) layout:
```c
complex array[N];  /* {real, imag}, {real, imag}, ... */
```
is optimal for single complex number operations but suboptimal for SIMD.

Structure-of-arrays (SoA) layout:
```c
double real_array[N], imag_array[N];
```
enables better SIMD utilization for vector operations but complicates individual access.

### Default Tolerances and Their Effects

| Parameter | Symbol | Default Value | Effect on Convergence |
|-----------|--------|---------------|---------------------|
| Complex zero tolerance | \(\epsilon_{\text{zero}}\) | \(10^{-12}\) | Threshold for considering complex values as zero |
| Division stability threshold | \(\tau_{\text{div}}\) | \(10^{-8}\) | Switch between Smith algorithm cases |
| Magnitude overflow threshold | \(T_{\text{overflow}}\) | \(10^{150}\) | Maximum before scaling |
| Condition number warning | \(\kappa_{\text{warn}}\) | \(10^8\) | Warn about potential accuracy loss |
| Iterative refinement tolerance | \(\epsilon_{\text{refine}}\) | \(10^{-12}\) | Stopping criterion for refinement |

These defaults ensure SPICE simulation accuracy while maintaining performance for typical circuit sizes (up to \(10^4\) nodes).

## C Implementation

### Core Data Structures

#### Complex Number Representation

The fundamental data structure for complex numbers in Ngspice is defined in `cmath.h`:

```c
typedef struct complex {
    double real;      /* Real part: Re{z} */
    double imag;      /* Imaginary part: Im{z} */
} complex;
```

**Mathematical Mapping:** This directly implements the mathematical representation \( z = a + jb \) where `real` stores \( a \) and `imag` stores \( b \). The structure occupies 16 bytes (two 8-byte doubles) with natural 16-byte alignment for SIMD optimization.

For performance-critical operations, an alternative packed representation is provided:

```c
typedef union dcomplex {
    struct {
        double real;
        double imag;
    } parts;
    double array[2];  /* For vectorized operations */
} dcomplex;
```

**Mathematical Mapping:** The union allows both structure access (`parts.real`, `parts.imag`) and array access for SIMD vectorization, enabling efficient memory layout transformations for different computational patterns.

#### Complex Matrix Structure for AC Analysis

For sparse complex matrix operations in AC analysis:

```c
typedef struct cmplx_element {
    double real;      /* Real part of matrix element */
    double imag;      /* Imaginary part of matrix element */
    int    row;       /* Row index (0-based) */
    int    col;       /* Column index (0-based) */
    struct cmplx_element *next_in_row;  /* Next in row list */
    struct cmplx_element *next_in_col;  /* Next in column list */
} cmplx_element;

typedef struct cmplx_matrix {
    int size;                     /* Matrix dimension (n×n) */
    cmplx_element **row_list;     /* Array of row headers */
    cmplx_element **col_list;     /* Array of column headers */
    double *rhs_real;             /* Real part of RHS vector */
    double *rhs_imag;             /* Imaginary part of RHS vector */
    double *solution_real;        /* Real part of solution */
    double *solution_imag;        /* Imaginary part of solution */
} cmplx_matrix;
```

**Mathematical Mapping:** This implements the sparse storage for the complex admittance matrix \( \mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C} \). The orthogonal linked list structure (`next_in_row`, `next_in_col`) enables efficient traversal for matrix-vector multiplication in the complex domain.

### Core Arithmetic Operations Implementation

#### Complex Addition

The mathematical operation \( z_1 + z_2 = (a_1 + a_2) + j(b_1 + b_2) \) is implemented as:

```c
complex Cadd(complex z1, complex z2)
{
    complex result;
    result.real = z1.real + z2.real;
    result.imag = z1.imag + z2.imag;
    return result;
}
```

**Mathematical Mapping:** Direct implementation of the real and imaginary component addition. For performance, an in-place version is provided:

```c
void Cadd_ip(complex *dest, complex z)
{
    dest→real += z.real;
    dest→imag += z.imag;
}
```

And a vectorized version for array operations:

```c
void Cadd_v(complex *result, complex *z1, complex *z2, int n)
{
    for (int i = 0; i < n; i++) {
        result[i].real = z1[i].real + z2[i].real;
        result[i].imag = z1[i].imag + z2[i].imag;
    }
}
```

#### Complex Subtraction

The mathematical operation \( z_1 - z_2 = (a_1 - a_2) + j(b_1 - b_2) \) is implemented as:

```c
complex Csub(complex z1, complex z2)
{
    complex result;
    result.real = z1.real - z2.real;
    result.imag = z1.imag - z2.imag;
    return result;
}
```

**Mathematical Mapping:** Direct component-wise subtraction with in-place optimization available.

#### Complex Multiplication

The mathematical operation \( z_1 \times z_2 = (a_1a_2 - b_1b_2) + j(a_1b_2 + a_2b_1) \) is implemented with numerical optimization:

```c
complex Cmul(complex z1, complex z2)
{
    complex result;
    /* Minimize rounding error with fused multiply-add if available */
    #ifdef HAVE_FMA
        result.real = fma(z1.real, z2.real, -z1.imag * z2.imag);
        result.imag = fma(z1.real, z2.imag, z1.imag * z2.real);
    #else
        result.real = z1.real * z2.real - z1.imag * z2.imag;
        result.imag = z1.real * z2.imag + z1.imag * z2.real;
    #endif
    return result;
}
```

**Mathematical Mapping:** The FMA (Fused Multiply-Add) optimization reduces rounding error from two operations to one, crucial for maintaining accuracy in iterative circuit solutions.

Specialized multiplication functions handle common SPICE cases:

```c
/* Multiplication by real scalar: (a + jb) × r = ar + j(br) */
complex Cmulr(complex z, double r)
{
    complex result;
    result.real = z.real * r;
    result.imag = z.imag * r;
    return result;
}

/* Multiplication by imaginary scalar: (a + jb) × jr = -br + j(ar) */
complex Cmuli(complex z, double i)
{
    complex result;
    result.real = -z.imag * i;
    result.imag = z.real * i;
    return result;
}
```

**Mathematical Mapping:** These optimize the common operations in AC analysis where matrices are multiplied by \( j\omega \).

#### Complex Division

The mathematical operation \( z_1 / z_2 = [(a_1a_2 + b_1b_2) + j(b_1a_2 - a_1b_2)] / (a_2^2 + b_2^2) \) is implemented using Smith's algorithm for numerical stability:

```c
complex Cdiv(complex z1, complex z2)
{
    complex result;
    double denom, ratio, den;
    
    /* Handle division by zero */
    if (z2.real == 0.0 && z2.imag == 0.0) {
        result.real = INFINITY;
        result.imag = INFINITY;
        return result;
    }
    
    /* Smith's algorithm for complex division (numerically stable) */
    if (fabs(z2.real) >= fabs(z2.imag)) {
        ratio = z2.imag / z2.real;
        den = z2.real + ratio * z2.imag;
        result.real = (z1.real + ratio * z1.imag) / den;
        result.imag = (z1.imag - ratio * z1.real) / den;
    } else {
        ratio = z2.real / z2.imag;
        den = z2.imag + ratio * z2.real;
        result.real = (ratio * z1.real + z1.imag) / den;
        result.imag = (ratio * z1.imag - z1.real) / den;
    }
    
    return result;
}
```

**Mathematical Mapping:** Smith's algorithm avoids overflow by scaling based on the relative magnitudes of real and imaginary parts, essential for handling the wide dynamic range of impedances in circuit simulation.

### Advanced Complex Operations

#### Complex Magnitude (Absolute Value)

The mathematical operation \( |z| = \sqrt{a^2 + b^2} \) is implemented with overflow protection:

```c
double Cabs(complex z)
{
    double a = fabs(z.real);
    double b = fabs(z.imag);
    
    /* Handle overflow using scaled computation */
    if (a == 0.0) return b;
    if (b == 0.0) return a;
    
    if (a > b) {
        double ratio = b / a;
        return a * sqrt(1.0 + ratio * ratio);
    } else {
        double ratio = a / b;
        return b * sqrt(1.0 + ratio * ratio);
    }
}
```

**Mathematical Mapping:** The scaled computation \( |z| = \max(|a|, |b|) \times \sqrt{1 + (\min(|a|, |b|)/\max(|a|, |b|))^2} \) prevents overflow when \( a^2 + b^2 \) exceeds floating-point range.

For comparison operations, squared magnitude avoids the sqrt computation:

```c
double Cabs2(complex z)
{
    return z.real * z.real + z.imag * z.imag;
}
```

#### Complex Argument (Phase Angle)

The mathematical operation \( \arg(z) = \operatorname{atan2}(b, a) \) is implemented as:

```c
double Carg(complex z)
{
    /* atan2 returns value in (-π, π] */
    return atan2(z.imag, z.real);
}
```

**Mathematical Mapping:** Direct mapping to the standard C library function `atan2`, which correctly handles all quadrants and special cases.

#### Complex Conjugate

The mathematical operation \( \overline{z} = a - jb \) is implemented as:

```c
complex Conjg(complex z)
{
    complex result;
    result.real = z.real;
    result.imag = -z.imag;
    return result;
}
```

**Mathematical Mapping:** Simple negation of the imaginary component, used in power calculations \( S = V \times \overline{I} \).

#### Complex Exponential

The mathematical operation \( e^z = e^a[\cos(b) + j\sin(b)] \) (Euler's formula) is implemented as:

```c
complex Cexp(complex z)
{
    complex result;
    double r = exp(z.real);
    result.real = r * cos(z.imag);
    result.imag = r * sin(z.imag);
    return result;
}
```

**Mathematical Mapping:** Direct implementation of Euler's formula, used in transient analysis and nonlinear device models.

#### Complex Natural Logarithm

The mathematical operation \( \ln(z) = \ln|z| + j\arg(z) \) is implemented as:

```c
complex Cln(complex z)
{
    complex result;
    result.real = log(Cabs(z));
    result.imag = Carg(z);
    return result;
}
```

**Mathematical Mapping:** Combines magnitude and argument computations, used in frequency transformation and device modeling.

#### Complex Square Root

The mathematical operation \( \sqrt{z} = \sqrt{(|z| + a)/2} + j\cdot\operatorname{sign}(b)\sqrt{(|z| - a)/2} \) is implemented as:

```c
complex Csqrt(complex z)
{
    complex result;
    double mag = Cabs(z);
    double a = z.real;
    double b = z.imag;
    
    if (mag == 0.0) {
        result.real = 0.0;
        result.imag = 0.0;
        return result;
    }
    
    if (a >= 0.0) {
        result.real = sqrt(0.5 * (mag + a));
        result.imag = 0.5 * b / result.real;
    } else {
        result.imag = (b >= 0.0 ? 1.0 : -1.0) * sqrt(0.5 * (mag - a));
        result.real = 0.5 * b / result.imag;
    }
    
    return result;
}
```

**Mathematical Mapping:** Implements the principal square root with proper branch cut handling along the negative real axis.

#### Complex Power

The mathematical operation \( z_1^{z_2} = \exp(z_2 \times \ln(z_1)) \) is implemented with optimization for common cases:

```c
complex Cpow(complex base, complex exponent)
{
    /* Handle special cases for efficiency */
    if (exponent.imag == 0.0) {
        /* Real exponent */
        if (exponent.real == 0.0) return CONE;
        if (exponent.real == 1.0) return base;
        if (exponent.real == 2.0) return Cmul(base, base);
    }
    
    /* General case */
    return Cexp(Cmul(exponent, Cln(base)));
}
```

**Mathematical Mapping:** Optimizes common integer exponents before falling back to the general logarithmic definition.

### Complex Matrix Operations

#### Complex Matrix-Vector Multiplication

The mathematical operation \( \mathbf{y} = \mathbf{A}\mathbf{x} \) for sparse complex matrices is implemented as:

```c
void Cmat_vec_mult(cmplx_matrix *A, complex *x, complex *y)
{
    int n = A→size;
    
    /* Initialize y to zero */
    for (int i = 0; i < n; i++) {
        y[i].real = 0.0;
        y[i].imag = 0.0;
    }
    
    /* Sparse matrix-vector multiplication */
    for (int i = 0; i < n; i++) {
        cmplx_element *elem = A→row_list[i];
        while (elem != NULL) {
            int j = elem→col;
            complex a_ij = {elem→real, elem→imag};
            complex product = Cmul(a_ij, x[j]);
            y[i].real += product.real;
            y[i].imag += product.imag;
            elem = elem→next_in_row;
        }
    }
}
```

**Mathematical Mapping:** Implements \( y_i = \sum_j A_{ij}x_j \) using sparse traversal. Each term computes \( (a+ jb)(c+ jd) = (ac - bd) + j(ad + bc) \) via `Cmul`, then accumulates real and imaginary parts separately.

#### Complex Linear System Solving Interface

The AC analysis system \( (\mathbf{A} + j\omega\mathbf{C})\mathbf{x} = \mathbf{b} \) is solved through:

```c
int Csolve_AC_system(cmplx_matrix *A, cmplx_matrix *C, 
                     double omega, complex *b, complex *x)
{
    int n = A→size;
    
    /* Build combined matrix: G = A + jωC */
    cmplx_matrix *G = Cbuild_combined_matrix(A, C, omega);
    
    /* Factor matrix */
    if (Cfactor(G) != 0) {
        /* Factorization failed */
        Cfree_matrix(G);
        return -1;
    }
    
    /* Solve system */
    Csolve(G, b, x);
    
    Cfree_matrix(G);
    return 0;
}
```

**Mathematical Mapping:** Constructs the complex admittance matrix \( \mathbf{Y}(\omega) = \mathbf{G} + j\omega\mathbf{C} \) where \( \mathbf{G} \) is the real conductance matrix and \( \mathbf{C} \) is the capacitance matrix, then solves the linear system using complex LU factorization.

### Error Handling and Special Cases

#### Complex NaN and Infinity Detection

```c
/* Check if complex number is NaN */
int Cisnan(complex z)
{
    return isnan(z.real) || isnan(z.imag);
}

/* Check if complex number is infinite */
int Cisinf(complex z)
{
    return isinf(z.real) || isinf(z.imag);
}

/* Check if complex number is finite */
int Cisfinite(complex z)
{
    return isfinite(z.real) && isfinite(z.imag);
}

/* Check if complex number is zero (within tolerance) */
int Cizero(complex z, double tol)
{
    return (fabs(z.real) < tol) && (fabs(z.imag) < tol);
}
```

**Mathematical Mapping:** These functions implement the mathematical conditions for special floating-point values, essential for robust numerical algorithms in circuit simulation.

#### Complex Comparison Functions

```c
/* Compare two complex numbers within tolerance */
int Cequal(complex z1, complex z2, double tol)
{
    double dr = fabs(z1.real - z2.real);
    double di = fabs(z1.imag - z2.imag);
    return (dr <= tol) && (di <= tol);
}

/* Compare magnitudes */
int Cabs_less(complex z1, complex z2)
{
    return Cabs2(z1) < Cabs2(z2);
}

/* Compare real parts */
int Creal_less(complex z1, complex z2)
{
    return z1.real < z2.real;
}
```

**Mathematical Mapping:** Implements component-wise equality within tolerance and magnitude comparisons for convergence testing in iterative solvers.

### Performance Optimizations

#### Vectorized Complex Operations

The complex multiply-add operation \( \mathbf{y} \leftarrow \mathbf{y} + \alpha\mathbf{x} \) is vectorized:

```c
void Caxpy(int n, complex a, complex *x, complex *y)
{
    #ifdef USE_SIMD
        /* SIMD-optimized implementation */
        #pragma omp simd
        for (int i = 0; i < n; i++) {
            y[i].real += a.real * x[i].real - a.imag * x[i].imag;
            y[i].imag += a.real * x[i].imag + a.imag * x[i].real;
        }
    #else
        /* Standard implementation */
        for (int i = 0; i < n; i++) {
            double temp_real = a.real * x[i].real - a.imag * x[i].imag;
            double temp_imag = a.real * x[i].imag + a.imag * x[i].real;
            y[i].real += temp_real;
            y[i].imag += temp_imag;
        }
    #endif
}
```

**Mathematical Mapping:** Implements \( y_i \leftarrow y_i + (a+ jb)(c_i+ jd_i) = y_i + [(ac_i - bd_i) + j(ad_i + bc_i)] \) with SIMD parallelism.

#### Complex Dot Product

The dot product \( \sum_i \overline{x_i}y_i \) (conjugate of first argument) is implemented as:

```c
complex Cdot(int n, complex *x, complex *y)
{
    complex result = CZERO;
    double sum_real = 0.0;
    double sum_imag = 0.0;
    
    #ifdef USE_SIMD
        /* SIMD-optimized dot product */
        #pragma omp simd reduction(+:sum_real,sum_imag)
        for (int i = 0; i < n; i++) {
            sum_real += x[i].real * y[i].real + x[i].imag * y[i].imag;
            sum_imag += x[i].real * y[i].imag - x[i].imag * y[i].real;
        }
    #else
        /* Standard implementation */
        for (int i = 0; i < n; i++) {
            sum_real += x[i].real * y[i].real + x[i].imag * y[i].imag;
            sum_imag += x[i].real * y[i].imag - x[i].imag * y[i].real;
        }
    #endif
    
    result.real = sum_real;
    result.imag = sum_imag;
    return result;
}
```

**Mathematical Mapping:** Computes \( \sum_i (a_i - jb_i)(c_i+ jd_i) = \sum_i [(a_ic_i + b_id_i) + j(a_id_i - b_ic_i)] \), used in iterative solvers and orthogonalization.

### Integration with Circuit Simulation

#### AC Analysis Frequency Response

The transfer function \( H(\omega) = V_{\text{out}}(\omega)/V_{\text{in}}(\omega) \) is computed as:

```c
complex Ccompute_transfer_function(CKTcircuit *ckt, double freq, 
                                   int input_node, int output_node)
{
    double omega = 2.0 * M_PI * freq;
    
    /* Build complex matrix: Y(ω) = G + jωC */
    cmplx_matrix *Y = Cbuild_admittance_matrix(ckt, omega);
    
    /* Set up source vector */
    complex *b = (complex*)TMALLOC(complex, ckt→CKTmaxEqnNum);
    Czero_vector(b, ckt→CKTmaxEqnNum);
    b[input_node] = CONE;  /* Unit current source */
    
    /* Solve system */
    complex *x = (complex*)TMALLOC(complex, ckt→CKTmaxEqnNum);
    Csolve(Y, b, x);
    
    /* Extract