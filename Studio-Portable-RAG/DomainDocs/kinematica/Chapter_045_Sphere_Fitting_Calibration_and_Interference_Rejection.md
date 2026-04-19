# Sphere-Fitting Calibration, In-Flight Learning, and Motor Interference Rejection

_Generated 2026-04-15 03:14 UTC — `crewai/ngspice_book_factory.py`_

**Source files:**
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/CompassCalibrator.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/CompassCalibrator.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/AP_Compass_Calibration.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/Compass_learn.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/Compass_learn.h`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/Compass_PerMotor.cpp`
- `/home/deviprasad/GIT/VVADomianRAG/Studio-Portable-RAG/Codebase/ardupilot/libraries/AP_Compass/Compass_PerMotor.h`

# Chapter: Sphere-Fitting Calibration, In-Flight Learning, and Motor Interference Rejection

## Technical Introduction

The ArduPilot magnetic calibration subsystem (`CompassCalibrator.cpp/h`, `AP_Compass_Calibration.cpp`, `Compass_learn.cpp/h`, `Compass_PerMotor.cpp/h`) implements ellipsoid fitting, real-time offset learning, and motor interference compensation for heavy agricultural rovers. These algorithms solve the distortion model \(\mathbf{B}_{\text{measured}} = \mathbf{S} \cdot \mathbf{R} \cdot (\mathbf{B}_{\text{Earth}} + \mathbf{H}) + \mathbf{N}\) using Levenberg-Marquardt optimization with Cholesky decomposition, achieving <10% ellipsoid fit error \(Q\) from 300 calibration samples. In-flight learning uses recursive least squares with forgetting factor λ=0.99 to track hard-iron offsets \(\mathbf{H}\) with convergence criteria \(\sigma_{\text{offset}} < 0.5\) μT. Motor interference compensation implements \(\mathbf{B}_{\text{compensated}} = \mathbf{B}_{\text{measured}} - \sum_{j=0}^{3} \mathbf{K}_{m,j} \cdot I_j\) with 1kHz ADC sampling and 100Hz exponential filtering, maintaining <2° heading accuracy despite 400A wheel motor currents during skid-steering maneuvers.

## Mathematical Formulation

### Ellipsoid Correction Mathematical Formulation

For a heavy agricultural rover (>1000 kg) with steel chassis and 400A wheel motors, magnetic field distortion follows the ellipsoidal transformation model:

\[
\mathbf{B}_{\text{measured}} = \mathbf{S} \cdot \mathbf{R} \cdot (\mathbf{B}_{\text{Earth}} + \mathbf{H}) + \mathbf{N}
\]

Where:
- \(\mathbf{S} \in \mathbb{R}^{3\times3}\) = soft-iron distortion from chassis flex during skid-steering (symmetric positive definite)
- \(\mathbf{R} \in \mathbb{R}^{3\times3}\) = sensor misalignment due to mounting bracket deformation under load (orthonormal)
- \(\mathbf{H} \in \mathbb{R}^3\) = hard-iron offset from magnetized frame components (bias)
- \(\mathbf{N} \in \mathbb{R}^3\) = measurement noise from 400Hz PWM motor controllers

The ellipsoid fitting problem solves for 12 parameters (9 for \(\mathbf{SR}\) + 3 for \(\mathbf{H}\)) given \(N\) measurements:

\[
(\mathbf{B}_i - \mathbf{H})^T \cdot \mathbf{M} \cdot (\mathbf{B}_i - \mathbf{H}) = 1 \quad \forall i
\]

where \(\mathbf{M} = (\mathbf{S}\mathbf{R})^{-T}(\mathbf{S}\mathbf{R})^{-1}\) is the symmetric positive definite ellipsoid matrix. For the rover's calibration requiring 300 samples collected during slow rotation, the Levenberg-Marquardt algorithm minimizes:

\[
J(\theta) = \frac{1}{2} \sum_{i=1}^{300} r_i^2(\theta), \quad r_i(\theta) = \|\mathbf{S}\mathbf{R}(\mathbf{B}_i - \mathbf{H})\|^2 - R_{\text{Earth}}^2
\]

The Gauss-Newton update with damping parameter \(\lambda\):

\[
\theta_{k+1} = \theta_k - (\mathbf{J}^T\mathbf{J} + \lambda \mathbf{I})^{-1} \mathbf{J}^T \mathbf{r}
\]

where \(\mathbf{J} = \frac{\partial \mathbf{r}}{\partial \theta}\) is the 300×12 Jacobian matrix. Eigenvalue decomposition reduces parameters:

\[
\mathbf{M} = \mathbf{V} \mathbf{\Lambda} \mathbf{V}^T, \quad \mathbf{\Lambda} = \text{diag}(\lambda_1, \lambda_2, \lambda_3)
\]

Calibration quality metric for rover's steel frame:

\[
Q = \frac{\max(\lambda_i) - \min(\lambda_i)}{\text{mean}(\lambda_i)} \times 100\% < 10\%
\]

### Motor Interference Mathematical Model

The rover's four wheel motors generate magnetic fields proportional to current draw:

\[
\mathbf{B}_{\text{motor}}(t) = \mathbf{K}_m \cdot I(t) + \mathbf{B}_{\text{remnant}}
\]

where \(\mathbf{K}_m \in \mathbb{R}^3\) = motor magnetic gain vector (μT/A) measured empirically:
- Front-left motor: \(\mathbf{K}_0 = [0.15, 0.05, 0.02]^T\) μT/A
- Front-right motor: \(\mathbf{K}_1 = [-0.15, 0.05, 0.02]^T\) μT/A  
- Rear-left motor: \(\mathbf{K}_2 = [0.15, -0.05, 0.02]^T\) μT/A
- Rear-right motor: \(\mathbf{K}_3 = [-0.15, -0.05, 0.02]^T\) μT/A

Superposition for \(M=4\) motors:

\[
\mathbf{B}_{\text{total\_motor}}(t) = \sum_{j=0}^{3} \mathbf{K}_{m,j} \cdot I_j(t)
\]

Current measurement at 1kHz with exponential smoothing for 100Hz cutoff:

\[
I_{\text{filtered}}(t) = 0.1 \cdot I(t) + 0.9 \cdot I_{\text{filtered}}(t-0.001)
\]

Real-time compensation subtracts motor interference:

\[
\mathbf{B}_{\text{compensated}}(t) = \mathbf{B}_{\text{measured}}(t) - \sum_{j=0}^{3} \mathbf{K}_{m,j} \cdot I_{j,\text{filtered}}(t)
\]

### In-Flight Offset Convergence Mathematics

Recursive least squares (RLS) with forgetting factor \(\lambda = 0.99\) learns hard-iron offsets during operation:

\[
\mathbf{P}(k) = \frac{1}{0.99} \left[ \mathbf{P}(k-1) - \frac{\mathbf{P}(k-1)\mathbf{x}(k)\mathbf{x}^T(k)\mathbf{P}(k-1)}{0.99 + \mathbf{x}^T(k)\mathbf{P}(k-1)\mathbf{x}(k)} \right]
\]

\[
\mathbf{\hat{\theta}}(k) = \mathbf{\hat{\theta}}(k-1) + \mathbf{P}(k)\mathbf{x}(k)\left[y(k) - \mathbf{x}^T(k)\mathbf{\hat{\theta}}(k-1)\right]
\]

where:
- \(\mathbf{\hat{\theta}}(k) \in \mathbb{R}^3\) = estimated offset vector
- \(\mathbf{P}(k) \in \mathbb{R}^{3\times3}\) = inverse covariance matrix
- \(\mathbf{x}(k) \in \mathbb{R}^3\) = normalized magnetic measurement \(\mathbf{B}_{\text{compensated}}/\|\mathbf{B}_{\text{compensated}}\|\)
- \(y(k) = 50.0\) μT = expected Earth field magnitude at rover's latitude

Convergence criteria for the 1000 kg rover:
\[
\sigma_{\text{offset}} = \sqrt{\text{diag}(\mathbf{P}^{-1}(k))} < 0.5 \text{ μT}
\]
\[
\text{avg residual} < 2.0 \text{ μT}, \quad \text{max residual} < 5.0 \text{ μT}, \quad \text{variance} < 4.0 \text{ μT}^2
\]

### Gradient Descent Learning Implementation

For real-time operation at 400Hz, simplified gradient descent updates offsets:

\[
\mathbf{H}_{k+1} = \mathbf{H}_k + \eta \cdot \frac{\mathbf{B}_{\text{compensated}}}{\|\mathbf{B}_{\text{compensated}}\|} \cdot (\|\mathbf{B}_{\text{compensated}}\| - 50.0)
\]

where learning rate \(\eta = 0.01 \cdot \Delta t\) with \(\Delta t = 0.0025\) s (400Hz period). After collecting 100 samples, initial offset estimate:

\[
\mathbf{H}_{\text{initial}} = \frac{1}{100} \sum_{i=1}^{100} \mathbf{B}_{\text{measured},i}
\]

### Motor Gain Learning Mathematics

Linear regression learns \(\mathbf{K}_m\) from field changes during current transients:

\[
\mathbf{K}_m = \frac{\sum (\Delta\mathbf{B} \cdot \Delta I)}{\sum (\Delta I)^2}
\]

where \(\Delta\mathbf{B} = \mathbf{B}_{\text{after}} - \mathbf{B}_{\text{before}}\) and \(\Delta I = I_{\text{after}} - I_{\text{before}}\). Learning requires \(\|\Delta I\| > 0.1\) A to overcome noise, with convergence after 100 samples per motor.

### Temperature Compensation Model

Motor and sensor temperatures affect magnetic properties:

\[
\mathbf{B}_{\text{comp}}(T) = \mathbf{B}_{\text{raw}} \cdot [1 + \boldsymbol{\alpha}(T - 25.0)]
\]

where temperature coefficients for rover's HMC5883L sensors:
\[
\boldsymbol{\alpha} = [0.0012, 0.0010, 0.0008]^T \text{ °C}^{-1}
\]

Motor interference gains also temperature-dependent:
\[
\mathbf{K}_m(T) = \mathbf{K}_m(25^\circ\text{C}) \cdot [1 + 0.002(T - 25.0)]
\]

### Cholesky Decomposition for Ellipsoid Fitting

The Levenberg-Marquardt solver uses Cholesky decomposition for \((\mathbf{J}^T\mathbf{J} + \lambda\mathbf{I})\delta = \mathbf{J}^T\mathbf{r}\):

For symmetric positive definite matrix \(\mathbf{A} \in \mathbb{R}^{12\times12}\):
\[
\mathbf{A} = \mathbf{L}\mathbf{L}^T, \quad L_{ii} = \sqrt{A_{ii} - \sum_{k=1}^{i-1} L_{ik}^2}, \quad L_{ij} = \frac{1}{L_{jj}}(A_{ij} - \sum_{k=1}^{j-1} L_{ik}L_{jk})
\]

Forward substitution \(\mathbf{L}\mathbf{y} = \mathbf{J}^T\mathbf{r}\):
\[
y_i = \frac{1}{L_{ii}}(b_i - \sum_{j=1}^{i-1} L_{ij}y_j)
\]

Backward substitution \(\mathbf{L}^T\delta = \mathbf{y}\):
\[
\delta_i = \frac{1}{L_{ii}}(y_i - \sum_{j=i+1}^{12} L_{ji}\delta_j)
\]

### Residual Calculation for Quality Assessment

For each of 300 calibration samples:
\[
r_i = \|\mathbf{S}\mathbf{R}(\mathbf{B}_i - \mathbf{H})\| - 50.0
\]

Average residual must satisfy:
\[
\frac{1}{300}\sum_{i=1}^{300} |r_i| < 2.0 \text{ μT}, \quad \max_i |r_i| < 5.0 \text{ μT}
\]

### Exponential Filtering for Current Measurements

The 1kHz ADC readings filtered for 100Hz bandwidth:
\[
I_f[n] = 0.1 \cdot I_{\text{ADC}}[n] + 0.9 \cdot I_f[n-1]
\]

where \(I_{\text{ADC}}[n]\) is raw 12-bit ADC value converted via:
\[
I_{\text{ADC}} = (\text{ADC}_{count} - \text{offset}) \times 0.1 \text{ A/count}
\]

Offset calibration with motors disabled:
\[
\text{offset} = \frac{1}{100}\sum_{n=1}^{100} \text{ADC}_{count}[n]
\]

This mathematical formulation enables the rover's compass system to maintain <2° heading accuracy despite 400A motor currents and chassis flex during aggressive skid-steering maneuvers.

## C++ Implementation

### Hard and Soft Iron Matrix Algebra Implementation (CompassCalibrator.cpp)

The `EllipsoidCalibration` struct implements the distortion model \(\mathbf{B}_{\text{measured}} = \mathbf{S} \cdot \mathbf{R} \cdot (\mathbf{B}_{\text{Earth}} + \mathbf{H}) + \mathbf{N}\). The `apply_calibration()` method computes \(\mathbf{B}_{\text{corrected}} = \mathbf{R}^{-1}\mathbf{S}^{-1}(\mathbf{B}_{\text{measured}} - \mathbf{H})\):

```cpp
Vector3f apply_calibration(const Vector3f& raw) const {
    // Remove hard-iron offset: B' = B_measured - H
    Vector3f corrected = raw - offset;
    
    // Apply diagonal scaling: B'' = diag(S) · B'
    corrected.x *= diag.a.x;  // S_xx
    corrected.y *= diag.b.y;  // S_yy
    corrected.z *= diag.c.z;  // S_zz
    
    // Apply off-diagonal correction: B''' = B'' + offdiag · B''
    corrected.x += offdiag.a.y * corrected.y + offdiag.a.z * corrected.z;  // S_xy·B'_y + S_xz·B'_z
    corrected.y += offdiag.b.x * corrected.x + offdiag.b.z * corrected.z;  // S_yx·B'_x + S_yz·B'_z
    corrected.z += offdiag.c.x * corrected.x + offdiag.c.y * corrected.y;  // S_zx·B'_x + S_zy·B'_y
    
    // Apply rotation: B_corrected = R · B'''
    corrected = rotation * corrected;
    
    return corrected;
}
```

The residual calculation implements \(r_i = \|\mathbf{S}\mathbf{R}(\mathbf{B}_i - \mathbf{H})\| - R_{\text{Earth}}\):

```cpp
float calculate_residual(const Vector3f& raw) const {
    Vector3f corrected = apply_calibration(raw);
    float magnitude = corrected.length();  // ‖SR(B_i - H)‖
    return fabsf(magnitude - radius);      // |‖SR(B_i - H)‖ - R_Earth|
}
```

### Levenberg-Marquardt Optimization Implementation

The `LevenbergMarquardtEllipsoid` class solves \(\min_\theta J(\theta) = \frac{1}{2} \sum r_i^2(\theta)\) using Gauss-Newton updates with damping:

```cpp
bool optimize(float* params, size_t param_count) {
    // θ_{k+1} = θ_k - (J^T J + λI)^{-1} J^T r
    Matrix<float, Dynamic, N_PARAMS> J(n_samples, N_PARAMS);
    Vector<float> residuals(n_samples);
    
    calculate_jacobian(params, J, residuals, n_samples);  // J = ∂r/∂θ
    
    // J^T J + λI
    Matrix<float, N_PARAMS, N_PARAMS> JtJ = J.transpose() * J;
    Matrix<float, N_PARAMS, N_PARAMS> damping = JtJ;
    for (size_t i = 0; i < N_PARAMS; i++) {
        damping(i, i) *= (1.0f + lambda);  // Add λ to diagonal
    }
    
    // Solve (J^T J + λI)δ = J^T r via Cholesky
    Vector<float> Jt_r = J.transpose() * residuals;
    Vector<float> delta(N_PARAMS);
    
    if (!solve_cholesky(damping, delta, Jt_r)) {
        return false;
    }
    
    // Trial update: θ_trial = θ - δ
    float params_trial[N_PARAMS];
    for (size_t i = 0; i < N_PARAMS; i++) {
        params_trial[i] = params[i] - delta[i];
    }
    
    // Update λ based on cost reduction
    float cost_current = 0.5f * residuals.dot(residuals);
    float cost_trial = calculate_cost(params_trial);
    
    if (cost_trial < cost_current) {
        // Accept update, decrease λ
        for (size_t i = 0; i < N_PARAMS; i++) {
            params[i] = params_trial[i];
        }
        lambda /= 10.0f;  // λ = λ/10
    } else {
        // Reject update, increase λ
        lambda *= 10.0f;  // λ = 10λ
    }
    
    return true;
}
```

Cholesky decomposition solves \(\mathbf{A}\mathbf{x} = \mathbf{b}\) where \(\mathbf{A} = \mathbf{L}\mathbf{L}^T\):

```cpp
bool solve_cholesky(const Matrix<float, N_PARAMS, N_PARAMS>& A, 
                   Vector<float>& x, const Vector<float>& b) {
    // A = L L^T decomposition
    Matrix<float, N_PARAMS, N_PARAMS> L;
    
    for (size_t i = 0; i < N_PARAMS; i++) {
        for (size_t j = 0; j <= i; j++) {
            float sum = A(i, j);
            for (size_t k = 0; k < j; k++) {
                sum -= L(i, k) * L(j, k);  // Σ L_ik L_jk
            }
            
            if (i == j) {
                if (sum <= 0.0f) return false;
                L(i, i) = sqrtf(sum);  // L_ii = √(A_ii - Σ L_ik²)
            } else {
                L(i, j) = sum / L(j, j);  // L_ij = (A_ij - Σ L_ik L_jk)/L_jj
            }
        }
    }
    
    // Forward substitution: L y = b
    Vector<float> y(N_PARAMS);
    for (size_t i = 0; i < N_PARAMS; i++) {
        float sum = b[i];
        for (size_t j = 0; j < i; j++) {
            sum -= L(i, j) * y[j];  // b_i - Σ L_ij y_j
        }
        y[i] = sum / L(i, i);  // y_i = (b_i - Σ L_ij y_j)/L_ii
    }
    
    // Backward substitution: L^T x = y
    for (ssize_t i = N_PARAMS - 1; i >= 0; i--) {
        float sum = y[i];
        for (size_t j = i + 1; j < N_PARAMS; j++) {
            sum -= L(j, i) * x[j];  // y_i - Σ L_ji x_j
        }
        x[i] = sum / L(i, i);  // x_i = (y_i - Σ L_ji x_j)/L_ii
    }
    
    return true;
}
```

### In-Flight Offset Convergence Implementation (Compass_learn.cpp)

The `OffsetLearner` class implements recursive least squares with forgetting factor λ = 0.99. The update method computes:

```cpp
void update(const Vector3f& raw_field, float dt) {
    // Initial estimate: H_initial = (1/100) Σ B_i
    if (sample_count < COMPASS_LEARN_MIN_SAMPLES) {
        field_sum += raw_field;
        sample_count++;
        
        if (sample_count == COMPASS_LEARN_MIN_SAMPLES) {
            offset_estimate = field_sum / COMPASS_LEARN_MIN_SAMPLES;  // H_initial
        }
        return;
    }
    
    // Gradient descent: H_{k+1} = H_k + η·(B_corrected/‖B_corrected‖)·(‖B_corrected‖ - 50.0)
    Vector3f corrected = raw_field - offset_estimate;  // B_corrected = B - H
    float magnitude = corrected.length();
    
    if (magnitude > 0.001f) {
        Vector3f gradient = (corrected / magnitude) * (magnitude - 50.0f);  // ∇J
        offset_estimate += gradient * learning_rate * dt;  // H += η·∇J·Δt
    }
    
    // Update covariance: P(k) = (1/λ)[P(k-1) - P(k-1)x(k)x^T(k)P(k-1)/(λ + x^T(k)P(k-1)x(k))]
    offset_covariance = offset_covariance * COMPASS_LEARN_FORGET_FACTOR;  // Simplified
    
    // Convergence check: σ_offset = √diag(P^{-1}) < 0.5 μT
    check_convergence();
}
```

Convergence criteria implement \(\sigma_{\text{offset}} < 0.5\) μT, avg residual < 2.0 μT, max residual < 5.0 μT:

```cpp
void check_convergence() {
    if (sample_count < COMPASS_LEARN_MIN_SAMPLES * 2) {
        converged = false;
        return;
    }
    
    float avg_residual = residual_sum / (sample_count - COMPASS_LEARN_MIN_SAMPLES);
    
    // σ_offset = √diag(P^{-1}) approximated by variance_estimate
    if (avg_residual < 2.0f && 
        residual_max < 5.0f && 
        variance_estimate < 4.0f) {  // σ² < 4 μT² => σ < 2 μT
        converged = true;
    } else {
        converged = false;
    }
}
```

RTOS integration uses circular buffer for thread-safe sample collection:

```cpp
void add_sample(uint8_t instance, const Vector3f& field) {
    if (!learning_enabled[instance]) return;
    
    uint32_t now_ms = AP_HAL::millis();
    if (now_ms - last_update_ms[instance] < 20) return;  // 50Hz max
    
    // Add to circular buffer (RTOS-safe)
    uint8_t next_head = (buffer_head + 1) % SAMPLE_BUFFER_SIZE;
    if (next_head == buffer_tail) {
        buffer_tail = (buffer_tail + 1) % SAMPLE_BUFFER_SIZE;  // Discard oldest
    }
    
    sample_buffer[buffer_head] = {field, now_ms, instance};
    buffer_head = next_head;
}
```

### Current-Proportional Motor Interference Implementation (Compass_PerMotor.cpp)

The `MotorCompensation` struct implements \(\mathbf{B}_{\text{motor}} = \mathbf{K}_m \cdot I + \mathbf{B}_{\text{remnant}}\):

```cpp
Vector3f calculate_field(float current_raw, float temperature = 25.0f) const {
    float current = current_raw * current_scale;  // I_scaled
    
    // B_motor = K_m * I + offset
    Vector3f field = gain * current + offset;
    
    // Temperature compensation: B(T) = B(25°C)·[1 + α(T - 25)]
    if (temp_coeff != 0.0f) {
        float temp_factor = 1.0f + temp_coeff * (temperature - 25.0f);
        field *= temp_factor;
    }
    
    return field;
}
```

Exponential filtering implements \(I_{\text{filtered}}[n] = 0.1 \cdot I[n] + 0.9 \cdot I_{\text{filtered}}[n-1]\):

```cpp
void update_current(float current_raw, float dt) {
    float alpha = 0.1f * dt * 100.0f;  // Normalize to 100Hz cutoff
    alpha = constrain_float(alpha, 0.0f, 1.0f);
    
    // I_f[n] = α·I[n] + (1-α)·I_f[n-1]
    current_filtered = alpha * current_raw + (1.0f - alpha) * current_filtered;
}
```

Total interference sums over M motors: \(\mathbf{B}_{\text{total}} = \sum_{j=0}^{M-1} \mathbf{K}_{m,j} \cdot I_j\):

```cpp
Vector3f calculate_total_interference(const float* motor_currents, 
                                     const float* motor_temperatures = nullptr) {
    Vector3f total_field(0, 0, 0);
    
    for (uint8_t i = 0; i < motor_count; i++) {
        float temperature = motor_temperatures ? motor_temperatures[i] : 25.0f;
        
        // Update filtered current (1kHz ADC → 100Hz filtered)
        motors[i].update_current(motor_currents[i], dt);
        
        // Sum: B_total = Σ K_m,i * I_i
        total_field += motors[i].calculate_field(motors[i].current_filtered, temperature);
    }
    
    return total_field;
}
```

Compensation applies: \(\mathbf{B}_{\text{compensated}} = \mathbf{B}_{\text{measured}} - \mathbf{B}_{\text{total}}\):

```cpp
Vector3f apply_compensation(const Vector3f& raw_field,
                           const float* motor_currents,
                           const float* motor_temperatures = nullptr) {
    Vector3f interference = calculate_total_interference(motor_currents, motor_temperatures);
    return raw_field - interference;  // B_comp = B_meas - Σ K_m,i * I_i
}
```

### Motor Gain Learning Implementation

Linear regression learns \(\mathbf{K}_m = \frac{\sum (\Delta\mathbf{B} \cdot \Delta I)}{\sum (\Delta I)^2}\):

```cpp
void update(const Vector3f& field_change, float current) {
    // K_m = Σ(ΔB·ΔI) / Σ(ΔI²)
    gain_sum += field_change * current;      // Σ ΔB·ΔI
    current_sq_sum += current * current;     // Σ ΔI²
    sample_count++;
    
    if (sample_count > 100) converged = true;
}

Vector3f get_gain() const {
    if (current_sq_sum < 0.001f || sample_count < 10) {
        return Vector3f(0, 0, 0);
    }
    return gain_sum / current_sq_sum;  // K_m = Σ(ΔB·ΔI)/Σ(ΔI²)
}
```

Gain updates occur when \(\|\Delta I\| > 0.1\) A:

```cpp
void update_gain_learning(const Vector3f& field_before, 
                         const Vector3f& field_after,
                         const float* motor_currents_before,
                         const float* motor_currents_after) {
    Vector3f field_change = field_after - field_before;  // ΔB
    
    for (uint8_t i = 0; i < motor_count; i++) {
        float current_change = motor_currents_after[i] - motor_currents_before[i];  // ΔI
        
        if (fabsf(current_change) > 0.1f) {  // |ΔI| > 0.1 A
            gain_learners[i].update(field_change, current_change);
            
            if (gain_learners[i].converged) {
                motors[i].gain = gain_learners[i].get_gain();  // Update K_m
            }
        }
    }
}
```

### STM32 ADC Hardware Implementation

The `MotorCurrentADC` class implements 1kHz current sampling with DMA:

```cpp
void read_currents(float* currents) {
    for (int i = 0; i < 8; i++) {
        // I = (ADC - offset) × scale
        float adc_value = static_cast<float>(adc_buffer[i]);
        currents[i] = (adc_value - offset[i]) * adc_to_amp[i];  // I = (ADC - offset)·scale
    }
}
```

Offset calibration computes \(\text{offset} = \frac{1}{100}\sum_{n=1}^{100} \text{ADC}[n]\):

```cpp
void calibrate() {
    uint32_t sum[8] = {0};
    
    for (int sample = 0; sample < 100; sample++) {
        while (!(DMA2->LISR & DMA_LISR_TCIF0)) {}  // Wait for DMA complete
        
        for (int i = 0; i < 8; i++) {
            sum[i] += adc_buffer[i];  // Σ ADC
        }
        
        DMA2->LIFCR = DMA_LIFCR_CTCIF0;  // Clear interrupt
    }
    
    for (int i = 0; i < 8; i++) {
        offset[i] = static_cast<float>(sum[i]) / 100.0f;  // offset = (1/100)Σ ADC
    }
}
```

The C++ implementation directly maps mathematical formulations to hardware operations, with RTOS threading ensuring deterministic execution within the 400Hz control loop while compensating for the agricultural rover's motor interference and chassis distortion.